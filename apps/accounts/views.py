from decimal import Decimal, InvalidOperation
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import LoginView
from django.db import transaction
from django.db.models import Avg, Count, DecimalField, IntegerField, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.text import slugify
from django.views import View
from django.views.decorators.http import require_POST
from django.db.models.functions import TruncDate
from uuid import uuid4

from apps.catalog.forms import ProductForm, ProductImageFormSet, ProductVariantFormSet
from apps.cart.models import PromotionCode
from apps.catalog.models import Brand, Category, Product, SizeOption
from apps.core.models import CommunityImage
from apps.notifications.services import send_welcome_email
from apps.orders.models import Order
from apps.orders.services import mark_order_cancelled, mark_order_paid

from .forms import (
    BrandManagementForm,
    CategoryManagementForm,
    CommunityImageForm,
    OrderManagementForm,
    PromotionCodeForm,
    ShippingUpdateForm,
    SizeOptionManagementForm,
    UserRegistrationForm,
)


User = get_user_model()


def user_can_access_backoffice(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)


def unique_product_value(field_name, raw_value, fallback, product=None):
    max_length = Product._meta.get_field(field_name).max_length
    base = (raw_value or fallback or "").strip()
    if field_name == "slug":
        base = slugify(base)
    if not base:
        base = fallback
    base = str(base)[:max_length].strip("-") or fallback
    candidate = base
    counter = 2
    queryset = Product.objects.all()
    if product and product.pk:
        queryset = queryset.exclude(pk=product.pk)
    while queryset.filter(**{field_name: candidate}).exists():
        suffix = f"-{counter}" if field_name == "slug" else f"-{counter}"
        candidate = f"{base[:max_length - len(suffix)]}{suffix}"
        counter += 1
    return candidate


def normalize_product_autosave_data(post_data, product):
    data = post_data.copy()
    draft_token = uuid4().hex[:8]
    fallback_name = product.name or "Borrador sin titulo"
    data["name"] = data.get("name") or fallback_name
    data["slug"] = unique_product_value(
        "slug",
        data.get("slug") or data.get("name"),
        product.slug or f"borrador-{draft_token}",
        product,
    )
    data["sku"] = unique_product_value(
        "sku",
        data.get("sku"),
        product.sku or f"DRAFT-{draft_token}",
        product,
    )
    data["price"] = clean_autosave_price(data.get("price"), product.price or 0)
    return data


def clean_autosave_price(value, fallback=0):
    if value in (None, ""):
        return fallback
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return fallback


def clean_autosave_int(value, fallback=0):
    if value in (None, ""):
        return fallback
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def build_backoffice_context(active_section):
    return {
        "backoffice_section": active_section,
        "backoffice_nav": [
            {"label": "Resumen", "icon": "bi-grid-1x2", "url_name": "accounts:backoffice_dashboard", "key": "dashboard"},
            {"label": "Productos", "icon": "bi-bag", "url_name": "accounts:backoffice_products", "key": "products"},
            {"label": "Pedidos", "icon": "bi-receipt", "url_name": "accounts:backoffice_orders", "key": "orders"},
            {"label": "Comunidad", "icon": "bi-images", "url_name": "accounts:backoffice_community", "key": "community"},
            {"label": "Mensajes", "icon": "bi-envelope", "url_name": "accounts:backoffice_messages", "key": "messages"},
            {"label": "Promociones", "icon": "bi-ticket-perforated", "url_name": "accounts:backoffice_promotions", "key": "promotions"},
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
    queryset = Order.objects.prefetch_related("items__product", "items__variant", "shipping_events")
    if request.user.is_staff or request.user.is_superuser:
        return get_object_or_404(queryset, id=order_id)
    return get_object_or_404(queryset.filter(user=request.user), id=order_id)


class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return user_can_access_backoffice(self.request.user)

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        messages.error(self.request, "Esta seccion es solo para administradores.")
        return redirect("core:home")


class AccountLoginView(LoginView):
    template_name = "accounts/login.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.POST.get("remember_me"):
            self.request.session.set_expiry(60 * 60 * 24 * 30)
        else:
            self.request.session.set_expiry(0)
        return response


class RegisterView(View):
    def get(self, request):
        form = UserRegistrationForm()
        return render(request, 'accounts/register.html', {'form': form})

    def post(self, request):
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            send_welcome_email(user)
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
        paid_orders = Order.objects.filter(status="paid")
        sales_by_day = list(
            paid_orders.annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(total=Coalesce(Sum("total_amount"), Value(0), output_field=DecimalField()))
            .order_by("-day")[:7]
        )
        top_customers = (
            User.objects.annotate(order_count=Count("orders"))
            .filter(order_count__gt=0)
            .order_by("-order_count", "username")[:6]
        )
        context = {
            **build_backoffice_context("dashboard"),
            "stats": {
                "total_sales": paid_orders.aggregate(total=Coalesce(Sum("total_amount"), Value(0), output_field=DecimalField()))["total"],
                "order_count": Order.objects.count(),
                "pending_orders": Order.objects.filter(status="pending").count(),
                "paid_orders": paid_orders.count(),
                "average_ticket": paid_orders.aggregate(avg=Coalesce(Avg("total_amount"), Value(0), output_field=DecimalField()))["avg"],
                "unique_customers": paid_orders.values("user").exclude(user=None).distinct().count(),
            },
            "recent_orders": recent_orders,
            "low_stock_products": low_stock_products,
            "top_customers": top_customers,
            "sales_by_day": sales_by_day,
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
        elif product_filter == "new_arrivals":
            products = products.filter(show_in_new_arrivals=True)
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
                ("new_arrivals", "Recien llegados"),
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
        elif action == "toggle_new_arrival":
            product.show_in_new_arrivals = not product.show_in_new_arrivals
            product.save(update_fields=["show_in_new_arrivals", "updated_at"])
            messages.success(
                request,
                f"{product.name}: {'visible en Recien llegados' if product.show_in_new_arrivals else 'quitado de Recien llegados'}.",
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
        product_categories = None
        if request.method == "POST":
            product_categories = request.POST.getlist("categories")
            form = ProductForm(request.POST, instance=product_instance)
            image_formset = ProductImageFormSet(request.POST, request.FILES, instance=product_instance)
            variant_formset = ProductVariantFormSet(
                request.POST,
                instance=product_instance,
                product_categories=product_categories,
            )
        else:
            if product_instance.pk:
                product_categories = list(product_instance.categories.values_list("id", flat=True))
            form = ProductForm(instance=product_instance)
            image_formset = ProductImageFormSet(instance=product_instance)
            variant_formset = ProductVariantFormSet(
                instance=product_instance,
                product_categories=product_categories,
            )
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


@require_POST
def backoffice_product_autosave(request):
    if not user_can_access_backoffice(request.user):
        return JsonResponse({"success": False, "error": "No autorizado"}, status=403)

    product = None
    product_id = request.POST.get("autosave_product_id") or request.POST.get("product_id")
    if product_id:
        product = Product.objects.filter(id=product_id).first()

    with transaction.atomic():
        if product is None:
            draft_token = uuid4().hex[:8]
            product = Product.objects.create(
                name=request.POST.get("name") or "Borrador sin titulo",
                slug=unique_product_value(
                    "slug",
                    request.POST.get("slug") or request.POST.get("name"),
                    f"borrador-{draft_token}",
                ),
                sku=unique_product_value("sku", request.POST.get("sku"), f"DRAFT-{draft_token}"),
                price=clean_autosave_price(request.POST.get("price"), 0),
                is_active=False,
                is_featured=False,
                show_in_new_arrivals=request.POST.get("show_in_new_arrivals") == "on",
                new_arrival_order=clean_autosave_int(request.POST.get("new_arrival_order"), 0),
            )

        data = normalize_product_autosave_data(request.POST, product)
        form = ProductForm(data, instance=product)
        image_formset = ProductImageFormSet(data, request.FILES, instance=product)
        variant_formset = ProductVariantFormSet(
            data,
            instance=product,
            product_categories=data.getlist("categories"),
        )

        form_valid = form.is_valid()
        image_formset_valid = image_formset.is_valid()
        variant_formset_valid = variant_formset.is_valid()

        if form_valid:
            product = form.save()
        else:
            product.name = data["name"]
            product.slug = data["slug"]
            product.sku = data["sku"]
            product.price = data["price"]
            product.is_active = data.get("is_active") == "on"
            product.is_featured = data.get("is_featured") == "on"
            product.show_in_new_arrivals = data.get("show_in_new_arrivals") == "on"
            product.new_arrival_order = clean_autosave_int(data.get("new_arrival_order"), 0)
            product.save()

        if image_formset_valid:
            image_formset.save()
        if variant_formset_valid:
            variant_formset.save()

    return JsonResponse(
        {
            "success": True,
            "product_id": product.id,
            "form_saved": form_valid,
            "image_formset_saved": image_formset_valid,
            "variant_formset_saved": variant_formset_valid,
        }
    )


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

        if action == "mark_paid":
            mark_order_paid(order, payment_id=order.payment_id)
            messages.success(request, f"Pedido #{order.id} marcado como pagado.")
        elif action == "mark_cancelled":
            mark_order_cancelled(order, payment_id=order.payment_id)
            messages.success(request, f"Pedido #{order.id} marcado como cancelado.")
        elif action == "mark_pending":
            order.status = "pending"
            order.payment_status = "pending"
            order.is_paid = False
            order.save(update_fields=["status", "payment_status", "is_paid", "updated_at"])
            messages.success(request, f"Pedido #{order.id} marcado como pendiente.")
        elif action == "toggle_paid":
            order.is_paid = not order.is_paid
            order.status = "paid" if order.is_paid else "pending"
            order.payment_status = "paid" if order.is_paid else "pending"
            order.save(update_fields=["is_paid", "status", "payment_status", "updated_at"])
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
            Order.objects.select_related("user").prefetch_related(
                "items__product", "items__variant", "shipping_events"
            ),
            id=order_id,
        )

    def get(self, request, order_id):
        order = self.get_order(order_id)
        form = OrderManagementForm(instance=order)
        context = {
            **build_backoffice_context("orders"),
            "order": order,
            "form": form,
            "shipment_form": ShippingUpdateForm(instance=order),
        }
        return render(request, "accounts/backoffice_order_detail.html", context)

    def post(self, request, order_id):
        order = self.get_order(order_id)
        previous_payment_status = order.payment_status
        previous_status = order.status
        form = OrderManagementForm(request.POST, instance=order)
        if form.is_valid():
            updated_order = form.save(commit=False)
            if updated_order.status == "paid" or updated_order.payment_status == "paid":
                updated_order.is_paid = True
            elif updated_order.status == "cancelled" or updated_order.payment_status == "cancelled":
                updated_order.is_paid = False
            form.save()
            if (
                previous_payment_status != "paid"
                and updated_order.payment_status == "paid"
            ) or (previous_status != "paid" and updated_order.status == "paid"):
                mark_order_paid(updated_order, payment_id=updated_order.payment_id)
            elif (
                previous_payment_status != "cancelled"
                and updated_order.payment_status == "cancelled"
            ) or (previous_status != "cancelled" and updated_order.status == "cancelled"):
                mark_order_cancelled(updated_order, payment_id=updated_order.payment_id)
            messages.success(request, f"Pedido #{order.id} actualizado.")
            return redirect("accounts:backoffice_order_detail", order_id=order.id)
        context = {
            **build_backoffice_context("orders"),
            "order": order,
            "form": form,
            "shipment_form": ShippingUpdateForm(instance=order),
        }
        return render(request, "accounts/backoffice_order_detail.html", context)


class BackofficeOrderShippingUpdateView(StaffRequiredMixin, View):
    def post(self, request, order_id):
        order = get_object_or_404(
            Order.objects.select_related("user").prefetch_related(
                "items__product", "items__variant", "shipping_events"
            ),
            id=order_id,
        )
        shipment_form = ShippingUpdateForm(request.POST, instance=order)

        if shipment_form.is_valid():
            shipping_fields = set(ShippingUpdateForm.Meta.fields)
            shipping_changed = bool(shipping_fields.intersection(shipment_form.changed_data))
            customer_message = shipment_form.cleaned_data["event_message"]
            occurred_at = shipment_form.cleaned_data["event_occurred_at"]

            with transaction.atomic():
                updated_order = shipment_form.save()
                if shipping_changed or customer_message:
                    if not customer_message:
                        if "estimated_delivery_date" in shipment_form.changed_data:
                            customer_message = "Actualizamos la fecha estimada de entrega."
                        elif {"carrier_name", "tracking_number"}.intersection(shipment_form.changed_data):
                            customer_message = "Actualizamos la información de despacho."
                        else:
                            customer_message = (
                                f"Actualizamos el estado de envío a {updated_order.get_shipping_status_display()}."
                            )
                    updated_order.record_shipping_event(customer_message, occurred_at)

            messages.success(request, f"Seguimiento del pedido #{order.id} actualizado.")
            return redirect("accounts:backoffice_order_detail", order_id=order.id)

        context = {
            **build_backoffice_context("orders"),
            "order": order,
            "form": OrderManagementForm(instance=order),
            "shipment_form": shipment_form,
        }
        return render(request, "accounts/backoffice_order_detail.html", context)


class BackofficeMessagesView(StaffRequiredMixin, View):
    def get(self, request):
        context = {
            **build_backoffice_context("messages"),
        }
        return render(request, "accounts/backoffice_messages.html", context)


class BackofficePromotionListView(StaffRequiredMixin, View):
    def get(self, request):
        query = request.GET.get("q", "").strip()
        status = request.GET.get("status", "").strip()
        promotions = PromotionCode.objects.select_related("created_by").order_by("-created_at")
        if query:
            promotions = promotions.filter(Q(code__icontains=query) | Q(description__icontains=query))
        if status == "active":
            promotions = [promo for promo in promotions if promo.status_key == "active"]
        elif status == "inactive":
            promotions = [promo for promo in promotions if promo.status_key == "inactive"]
        elif status == "expired":
            promotions = [promo for promo in promotions if promo.status_key == "expired"]
        elif status == "limit":
            promotions = [promo for promo in promotions if promo.status_key == "limit"]

        context = {
            **build_backoffice_context("promotions"),
            "promotions": promotions,
            "query": query,
            "active_status": status,
            "status_filters": [
                ("", "Todas"),
                ("active", "Activas"),
                ("inactive", "Inactivas"),
                ("expired", "Vencidas"),
                ("limit", "Limite alcanzado"),
            ],
        }
        return render(request, "accounts/backoffice_promotions.html", context)


class BackofficePromotionFormView(StaffRequiredMixin, View):
    template_name = "accounts/backoffice_promotion_form.html"

    def get_object(self, promotion_id):
        if promotion_id is None:
            return None
        return get_object_or_404(PromotionCode, id=promotion_id)

    def render_form(self, request, form, promotion=None):
        context = {
            **build_backoffice_context("promotions"),
            "form": form,
            "promotion": promotion,
            "is_editing": promotion is not None,
        }
        return render(request, self.template_name, context)

    def get(self, request, promotion_id=None):
        promotion = self.get_object(promotion_id)
        form = PromotionCodeForm(instance=promotion)
        return self.render_form(request, form, promotion)

    def post(self, request, promotion_id=None):
        promotion = self.get_object(promotion_id)
        form = PromotionCodeForm(request.POST, instance=promotion)
        if form.is_valid():
            saved_promotion = form.save(commit=False)
            if saved_promotion.created_by_id is None:
                saved_promotion.created_by = request.user
            saved_promotion.save()
            messages.success(request, f"Promocion {saved_promotion.code} guardada correctamente.")
            return redirect("accounts:backoffice_promotion_edit", promotion_id=saved_promotion.id)
        return self.render_form(request, form, promotion)


class BackofficePromotionActionView(StaffRequiredMixin, View):
    def post(self, request, promotion_id):
        promotion = get_object_or_404(PromotionCode, id=promotion_id)
        action = request.POST.get("action")
        if action == "toggle_active":
            promotion.is_active = not promotion.is_active
            promotion.save(update_fields=["is_active", "updated_at"])
            messages.success(
                request,
                f"{promotion.code}: {'activado' if promotion.is_active else 'desactivado'} correctamente.",
            )
        else:
            messages.error(request, "Accion de promocion no valida.")
        return redirect(request.POST.get("next_url") or reverse("accounts:backoffice_promotions"))


class BackofficeCommunityListView(StaffRequiredMixin, View):
    def get(self, request):
        context = {
            **build_backoffice_context("community"),
            "community_images": CommunityImage.objects.order_by("ordering", "-created_at"),
        }
        return render(request, "accounts/backoffice_community.html", context)


class BackofficeCommunityFormView(StaffRequiredMixin, View):
    template_name = "accounts/backoffice_community_form.html"

    def get_object(self, image_id):
        if image_id is None:
            return None
        return get_object_or_404(CommunityImage, id=image_id)

    def get(self, request, image_id=None):
        community_image = self.get_object(image_id)
        form = CommunityImageForm(instance=community_image)
        context = {
            **build_backoffice_context("community"),
            "form": form,
            "community_image": community_image,
            "is_editing": community_image is not None,
        }
        return render(request, self.template_name, context)

    def post(self, request, image_id=None):
        community_image = self.get_object(image_id)
        form = CommunityImageForm(request.POST, instance=community_image)
        if form.is_valid():
            saved_image = form.save()
            messages.success(request, "Imagen de comunidad guardada correctamente.")
            return redirect("accounts:backoffice_community_edit", image_id=saved_image.id)
        context = {
            **build_backoffice_context("community"),
            "form": form,
            "community_image": community_image,
            "is_editing": community_image is not None,
        }
        return render(request, self.template_name, context)


class BackofficeCommunityActionView(StaffRequiredMixin, View):
    def post(self, request, image_id):
        community_image = get_object_or_404(CommunityImage, id=image_id)
        action = request.POST.get("action")
        if action == "toggle_active":
            community_image.is_active = not community_image.is_active
            community_image.save(update_fields=["is_active"])
            messages.success(
                request,
                f"Imagen {'activada' if community_image.is_active else 'ocultada'} correctamente.",
            )
        elif action == "delete":
            community_image.delete()
            messages.success(request, "Imagen de comunidad eliminada.")
        else:
            messages.error(request, "Accion de comunidad no valida.")
        return redirect(request.POST.get("next_url") or reverse("accounts:backoffice_community"))


class BackofficeTaxonomyView(StaffRequiredMixin, View):
    def get(self, request):
        context = {
            **build_backoffice_context("taxonomy"),
            "category_form": CategoryManagementForm(prefix="category"),
            "brand_form": BrandManagementForm(prefix="brand"),
            "size_form": SizeOptionManagementForm(prefix="size"),
            "categories": Category.objects.order_by("name"),
            "brands": Brand.objects.order_by("name"),
            "size_options": SizeOption.objects.order_by("size_type", "ordering", "name"),
        }
        return render(request, "accounts/backoffice_taxonomy.html", context)

    def post(self, request):
        form_type = request.POST.get("form_type")
        category_form = CategoryManagementForm(prefix="category")
        brand_form = BrandManagementForm(prefix="brand")
        size_form = SizeOptionManagementForm(prefix="size")

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
        elif form_type == "size":
            size_form = SizeOptionManagementForm(request.POST, prefix="size")
            if size_form.is_valid():
                size_form.save()
                messages.success(request, "Talla creada correctamente.")
                return redirect("accounts:backoffice_taxonomy")

        context = {
            **build_backoffice_context("taxonomy"),
            "category_form": category_form,
            "brand_form": brand_form,
            "size_form": size_form,
            "categories": Category.objects.order_by("name"),
            "brands": Brand.objects.order_by("name"),
            "size_options": SizeOption.objects.order_by("size_type", "ordering", "name"),
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


class BackofficeSizeOptionEditView(StaffRequiredMixin, View):
    def get(self, request, size_id):
        size_option = get_object_or_404(SizeOption, id=size_id)
        form = SizeOptionManagementForm(instance=size_option)
        context = {
            **build_backoffice_context("taxonomy"),
            "form": form,
            "object_label": "talla",
            "title": f"Editar talla: {size_option.name}",
        }
        return render(request, "accounts/backoffice_taxonomy_form.html", context)

    def post(self, request, size_id):
        size_option = get_object_or_404(SizeOption, id=size_id)
        form = SizeOptionManagementForm(request.POST, instance=size_option)
        if form.is_valid():
            form.save()
            messages.success(request, "Talla actualizada.")
            return redirect("accounts:backoffice_taxonomy")
        context = {
            **build_backoffice_context("taxonomy"),
            "form": form,
            "object_label": "talla",
            "title": f"Editar talla: {size_option.name}",
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
