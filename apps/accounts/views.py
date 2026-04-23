from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Count, IntegerField, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View

from apps.catalog.forms import ProductForm, ProductImageFormSet, ProductVariantFormSet
from apps.catalog.models import Brand, Category, Product
from apps.orders.models import Order

from .forms import BrandManagementForm, CategoryManagementForm, OrderManagementForm, UserRegistrationForm


User = get_user_model()


def build_backoffice_context(active_section):
    return {
        "backoffice_section": active_section,
        "backoffice_nav": [
            {"label": "Resumen", "icon": "bi-grid-1x2", "url_name": "accounts:backoffice_dashboard", "key": "dashboard"},
            {"label": "Productos", "icon": "bi-bag", "url_name": "accounts:backoffice_products", "key": "products"},
            {"label": "Pedidos", "icon": "bi-receipt", "url_name": "accounts:backoffice_orders", "key": "orders"},
            {"label": "Marcas y categorias", "icon": "bi-tags", "url_name": "accounts:backoffice_taxonomy", "key": "taxonomy"},
            {"label": "Usuarios", "icon": "bi-people", "url_name": "accounts:backoffice_users", "key": "users"},
        ],
        "backoffice_metrics": {
            "products": Product.objects.count(),
            "orders": Order.objects.count(),
            "pending_orders": Order.objects.filter(status="pending").count(),
            "users": User.objects.count(),
        },
    }


def get_order_for_request(request, order_id):
    queryset = Order.objects.prefetch_related("items__product", "items__variant")
    if request.user.is_staff or request.user.is_superuser:
        return get_object_or_404(queryset, id=order_id)
    return get_object_or_404(queryset.filter(user=request.user), id=order_id)


class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        messages.error(self.request, "Esta seccion es solo para administradores.")
        return redirect("core:home")

class RegisterView(View):
    def get(self, request):
        form = UserRegistrationForm()
        return render(request, 'accounts/register.html', {'form': form})

    def post(self, request):
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('core:home')
        return render(request, 'accounts/register.html', {'form': form})

class ProfileView(LoginRequiredMixin, View):
    def get(self, request):
        orders = request.user.orders.prefetch_related('items__product', 'items__variant')
        return render(request, 'accounts/profile.html', {'orders': orders})


class OrderDetailView(LoginRequiredMixin, View):
    def get(self, request, order_id):
        order = get_order_for_request(request, order_id)
        return render(request, 'accounts/order_detail.html', {'order': order})


class OrderReceiptView(LoginRequiredMixin, View):
    def get(self, request, order_id):
        order = get_order_for_request(request, order_id)
        return render(request, 'accounts/order_receipt.html', {'order': order})


class BackofficeDashboardView(StaffRequiredMixin, View):
    def get(self, request):
        low_stock_products = (
            Product.objects.select_related("brand")
            .prefetch_related("images")
            .annotate(total_stock=Coalesce(Sum("variants__stock"), Value(0), output_field=IntegerField()))
            .filter(is_active=True, total_stock__lte=5)
            .order_by("total_stock", "name")[:6]
        )
        recent_orders = Order.objects.select_related("user").prefetch_related("items")[:6]
        top_customers = (
            User.objects.annotate(order_count=Count("orders"))
            .filter(order_count__gt=0)
            .order_by("-order_count", "username")[:6]
        )
        context = {
            **build_backoffice_context("dashboard"),
            "stats": {
                "published_products": Product.objects.filter(is_active=True).count(),
                "featured_products": Product.objects.filter(is_featured=True).count(),
                "pending_orders": Order.objects.filter(status="pending").count(),
                "paid_orders": Order.objects.filter(is_paid=True).count(),
                "brands": Brand.objects.count(),
                "categories": Category.objects.count(),
            },
            "recent_orders": recent_orders,
            "low_stock_products": low_stock_products,
            "top_customers": top_customers,
        }
        return render(request, "accounts/backoffice_dashboard.html", context)


class BackofficeProductListView(StaffRequiredMixin, View):
    def get(self, request):
        query = request.GET.get("q", "").strip()
        product_filter = request.GET.get("filter", "").strip()
        products = (
            Product.objects.select_related("brand")
            .prefetch_related("images", "categories")
            .annotate(total_stock=Coalesce(Sum("variants__stock"), Value(0), output_field=IntegerField()))
            .order_by("-created_at")
        )
        if query:
            products = products.filter(name__icontains=query)
        if product_filter == "active":
            products = products.filter(is_active=True)
        elif product_filter == "inactive":
            products = products.filter(is_active=False)
        elif product_filter == "featured":
            products = products.filter(is_featured=True)
        elif product_filter == "low_stock":
            products = products.filter(total_stock__gt=0, total_stock__lte=5)
        elif product_filter == "out_of_stock":
            products = products.filter(total_stock__lte=0)

        context = {
            **build_backoffice_context("products"),
            "products": products,
            "query": query,
            "active_filter": product_filter,
            "product_filters": [
                ("", "Todos"),
                ("active", "Publicados"),
                ("inactive", "Ocultos"),
                ("featured", "Destacados"),
                ("low_stock", "Stock bajo"),
                ("out_of_stock", "Sin stock"),
            ],
        }
        return render(request, "accounts/backoffice_products.html", context)


class BackofficeProductActionView(StaffRequiredMixin, View):
    def post(self, request, product_id):
        product = get_object_or_404(Product, id=product_id)
        action = request.POST.get("action")
        next_url = request.POST.get("next_url") or reverse("accounts:backoffice_products")

        if action == "toggle_active":
            product.is_active = not product.is_active
            product.save(update_fields=["is_active"])
            messages.success(
                request,
                f"{product.name}: {'publicado' if product.is_active else 'ocultado'} correctamente.",
            )
        elif action == "toggle_featured":
            product.is_featured = not product.is_featured
            product.save(update_fields=["is_featured"])
            messages.success(
                request,
                f"{product.name}: {'marcado como destacado' if product.is_featured else 'quitado de destacados'}.",
            )
        else:
            messages.error(request, "Accion de producto no valida.")

        return redirect(next_url)


class BackofficeProductFormView(StaffRequiredMixin, View):
    template_name = "accounts/backoffice_product_form.html"
    product = None

    def get_product(self, product_id):
        if product_id is None:
            return None
        return get_object_or_404(Product.objects.prefetch_related("images", "variants", "categories"), id=product_id)

    def build_forms(self, request, product=None):
        product_instance = product or Product()
        if request.method == "POST":
            form = ProductForm(request.POST, instance=product_instance)
            image_formset = ProductImageFormSet(request.POST, request.FILES, instance=product_instance)
            variant_formset = ProductVariantFormSet(request.POST, instance=product_instance)
        else:
            form = ProductForm(instance=product_instance)
            image_formset = ProductImageFormSet(instance=product_instance)
            variant_formset = ProductVariantFormSet(instance=product_instance)
        return form, image_formset, variant_formset

    def render_form(self, request, form, image_formset, variant_formset, product=None):
        context = {
            **build_backoffice_context("products"),
            "form": form,
            "image_formset": image_formset,
            "variant_formset": variant_formset,
            "product": product,
            "is_editing": product is not None,
        }
        return render(request, self.template_name, context)

    def get(self, request, product_id=None):
        product = self.get_product(product_id)
        form, image_formset, variant_formset = self.build_forms(request, product)
        return self.render_form(request, form, image_formset, variant_formset, product)

    def post(self, request, product_id=None):
        product = self.get_product(product_id)
        form, image_formset, variant_formset = self.build_forms(request, product)
        if form.is_valid() and image_formset.is_valid() and variant_formset.is_valid():
            saved_product = form.save()
            image_formset.instance = saved_product
            variant_formset.instance = saved_product
            image_formset.save()
            variant_formset.save()
            messages.success(
                request,
                f"Producto {'actualizado' if product else 'creado'} correctamente.",
            )
            return redirect("accounts:backoffice_product_edit", product_id=saved_product.id)
        return self.render_form(request, form, image_formset, variant_formset, product)


class BackofficeOrderListView(StaffRequiredMixin, View):
    def get(self, request):
        status = request.GET.get("status", "").strip()
        query = request.GET.get("q", "").strip()
        orders = Order.objects.select_related("user").prefetch_related("items").order_by("-created_at")

        if status:
            orders = orders.filter(status=status)
        if query:
            orders = orders.filter(Q(full_name__icontains=query) | Q(email__icontains=query))

        context = {
            **build_backoffice_context("orders"),
            "orders": orders,
            "active_status": status,
            "query": query,
            "status_choices": Order.STATUS_CHOICES,
        }
        return render(request, "accounts/backoffice_orders.html", context)


class BackofficeOrderActionView(StaffRequiredMixin, View):
    def post(self, request, order_id):
        order = get_object_or_404(Order, id=order_id)
        action = request.POST.get("action")
        next_url = request.POST.get("next_url") or reverse("accounts:backoffice_orders")

        if action == "mark_processing":
            order.status = "processing"
            order.save(update_fields=["status"])
            messages.success(request, f"Pedido #{order.id} marcado como procesando.")
        elif action == "mark_shipped":
            order.status = "shipped"
            order.save(update_fields=["status"])
            messages.success(request, f"Pedido #{order.id} marcado como enviado.")
        elif action == "mark_delivered":
            order.status = "delivered"
            order.save(update_fields=["status"])
            messages.success(request, f"Pedido #{order.id} marcado como entregado.")
        elif action == "toggle_paid":
            order.is_paid = not order.is_paid
            order.save(update_fields=["is_paid"])
            messages.success(
                request,
                f"Pedido #{order.id}: {'pago confirmado' if order.is_paid else 'marcado como pendiente de pago'}.",
            )
        else:
            messages.error(request, "Accion de pedido no valida.")

        return redirect(next_url)


class BackofficeOrderDetailView(StaffRequiredMixin, View):
    def get_order(self, order_id):
        return get_object_or_404(
            Order.objects.select_related("user").prefetch_related("items__product", "items__variant"),
            id=order_id,
        )

    def get(self, request, order_id):
        order = self.get_order(order_id)
        form = OrderManagementForm(instance=order)
        context = {
            **build_backoffice_context("orders"),
            "order": order,
            "form": form,
        }
        return render(request, "accounts/backoffice_order_detail.html", context)

    def post(self, request, order_id):
        order = self.get_order(order_id)
        form = OrderManagementForm(request.POST, instance=order)
        if form.is_valid():
            form.save()
            messages.success(request, f"Pedido #{order.id} actualizado.")
            return redirect("accounts:backoffice_order_detail", order_id=order.id)
        context = {
            **build_backoffice_context("orders"),
            "order": order,
            "form": form,
        }
        return render(request, "accounts/backoffice_order_detail.html", context)


class BackofficeTaxonomyView(StaffRequiredMixin, View):
    def get(self, request):
        context = {
            **build_backoffice_context("taxonomy"),
            "category_form": CategoryManagementForm(prefix="category"),
            "brand_form": BrandManagementForm(prefix="brand"),
            "categories": Category.objects.order_by("name"),
            "brands": Brand.objects.order_by("name"),
        }
        return render(request, "accounts/backoffice_taxonomy.html", context)

    def post(self, request):
        form_type = request.POST.get("form_type")
        category_form = CategoryManagementForm(prefix="category")
        brand_form = BrandManagementForm(prefix="brand")

        if form_type == "category":
            category_form = CategoryManagementForm(request.POST, prefix="category")
            if category_form.is_valid():
                category_form.save()
                messages.success(request, "Categoria creada correctamente.")
                return redirect("accounts:backoffice_taxonomy")
        elif form_type == "brand":
            brand_form = BrandManagementForm(request.POST, prefix="brand")
            if brand_form.is_valid():
                brand_form.save()
                messages.success(request, "Marca creada correctamente.")
                return redirect("accounts:backoffice_taxonomy")

        context = {
            **build_backoffice_context("taxonomy"),
            "category_form": category_form,
            "brand_form": brand_form,
            "categories": Category.objects.order_by("name"),
            "brands": Brand.objects.order_by("name"),
        }
        return render(request, "accounts/backoffice_taxonomy.html", context)


class BackofficeCategoryEditView(StaffRequiredMixin, View):
    def get(self, request, category_id):
        category = get_object_or_404(Category, id=category_id)
        form = CategoryManagementForm(instance=category)
        context = {
            **build_backoffice_context("taxonomy"),
            "form": form,
            "object_label": "categoria",
            "title": f"Editar categoria: {category.name}",
        }
        return render(request, "accounts/backoffice_taxonomy_form.html", context)

    def post(self, request, category_id):
        category = get_object_or_404(Category, id=category_id)
        form = CategoryManagementForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, "Categoria actualizada.")
            return redirect("accounts:backoffice_taxonomy")
        context = {
            **build_backoffice_context("taxonomy"),
            "form": form,
            "object_label": "categoria",
            "title": f"Editar categoria: {category.name}",
        }
        return render(request, "accounts/backoffice_taxonomy_form.html", context)


class BackofficeBrandEditView(StaffRequiredMixin, View):
    def get(self, request, brand_id):
        brand = get_object_or_404(Brand, id=brand_id)
        form = BrandManagementForm(instance=brand)
        context = {
            **build_backoffice_context("taxonomy"),
            "form": form,
            "object_label": "marca",
            "title": f"Editar marca: {brand.name}",
        }
        return render(request, "accounts/backoffice_taxonomy_form.html", context)

    def post(self, request, brand_id):
        brand = get_object_or_404(Brand, id=brand_id)
        form = BrandManagementForm(request.POST, instance=brand)
        if form.is_valid():
            form.save()
            messages.success(request, "Marca actualizada.")
            return redirect("accounts:backoffice_taxonomy")
        context = {
            **build_backoffice_context("taxonomy"),
            "form": form,
            "object_label": "marca",
            "title": f"Editar marca: {brand.name}",
        }
        return render(request, "accounts/backoffice_taxonomy_form.html", context)


class BackofficeUserListView(StaffRequiredMixin, View):
    def get(self, request):
        users = (
            User.objects.annotate(order_count=Count("orders"))
            .order_by("-is_staff", "-is_superuser", "username")
        )
        context = {
            **build_backoffice_context("users"),
            "users": users,
        }
        return render(request, "accounts/backoffice_users.html", context)
