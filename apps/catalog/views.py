from datetime import timedelta

from django.views.generic import ListView, DetailView
from django.db.models import Q, DecimalField
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test, login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.http import JsonResponse
from django.db.models.functions import Coalesce
from django.utils import timezone
from .models import Product, Category, Brand, Wishlist
from .forms import ProductForm, ProductImageFormSet, ProductVariantFormSet

CATALOG_REASSURANCE = [
    {
        "icon": "bi-truck",
        "title": "Envio claro",
        "text": "Despacho con seguimiento y tiempos mas faciles de leer desde la compra.",
    },
    {
        "icon": "bi-shield-check",
        "title": "Compra protegida",
        "text": "Checkout simple, carrito estable y soporte real si algo no sale como esperabas.",
    },
    {
        "icon": "bi-arrow-repeat",
        "title": "Cambios simples",
        "text": "Politica clara para resolver talla o ajuste sin friccion innecesaria.",
    },
]


def build_product_reassurance(product, has_in_stock_variants):
    stock_text = (
        "Tallas activas listas para compra y despacho una vez confirmado el pedido."
        if has_in_stock_variants or not product.variants.filter(is_active=True).exists()
        else "Las variantes activas estan agotadas por ahora, pero puedes guardarlo y seguirlo en favoritos."
    )
    return [
        {
            "icon": "bi-patch-check",
            "title": "Curado 001xclusiv",
            "text": "Seleccion revisada para mantener consistencia visual, presencia y calidad percibida.",
        },
        {
            "icon": "bi-box-seam",
            "title": "Stock visible",
            "text": stock_text,
        },
        {
            "icon": "bi-arrow-repeat",
            "title": "Cambios claros",
            "text": "Si la talla no te acompana como esperabas, dejamos el proceso mas directo y entendible.",
        },
        {
            "icon": "bi-shield-lock",
            "title": "Compra segura",
            "text": "Tus datos y tu pedido se procesan con un flujo claro, sin pasos confusos ni sobrecarga.",
        },
    ]


def enrich_product_cards(products):
    fresh_threshold = timezone.now() - timedelta(days=21)
    for product in products:
        active_variants = [variant for variant in product.variants.all() if variant.is_active]
        stock_total = sum(variant.stock for variant in active_variants)
        in_stock_sizes = sum(1 for variant in active_variants if variant.stock > 0)

        product.stock_total = stock_total
        product.in_stock_sizes = in_stock_sizes
        product.is_new_drop = product.created_at >= fresh_threshold

        if product.is_new_drop:
            product.commercial_tag = "Nuevo drop"
            product.commercial_note = "Recien incorporado al catalogo curado."
        elif 0 < stock_total <= 3:
            product.commercial_tag = "Pocas unidades"
            product.commercial_note = "Quedan pocas unidades activas en este drop."
        elif in_stock_sizes > 1:
            product.commercial_tag = "Varias tallas"
            product.commercial_note = f"{in_stock_sizes} tallas activas para compra inmediata."
        else:
            product.commercial_tag = "Seleccion curada"
            product.commercial_note = "Disponible con despacho y soporte posterior."


def build_catalog_seo(active_filters, results_count):
    category = active_filters.get("category")
    brand = active_filters.get("brand")
    query = active_filters.get("q")

    title_bits = ["Catalogo"]
    if category:
        title_bits.append(category)
    if brand:
        title_bits.append(brand)

    seo_title = " | ".join(title_bits) + " - 001xclusiv"

    if query:
        seo_description = (
            f"Resultados para '{query}' en 001xclusiv. {results_count} producto"
            f"{'' if results_count == 1 else 's'} entre sneakers, ropa y accesorios curados."
        )
    elif category and brand:
        seo_description = (
            f"Explora {category} de {brand} en 001xclusiv. Seleccion visual, filtros MVP y compra mas clara."
        )
    elif category:
        seo_description = (
            f"Explora {category} en 001xclusiv. Productos curados, lectura clara de stock y una experiencia mas premium."
        )
    else:
        seo_description = (
            "Catalogo 001xclusiv con sneakers, streetwear y accesorios curados. Filtra, compara y descubre drops con mas contexto."
        )

    return seo_title, seo_description


def is_staff_or_superuser(user):
    return user.is_staff or user.is_superuser

@user_passes_test(is_staff_or_superuser)
def product_create(request):
    if request.method == 'POST':
        form = ProductForm(request.POST)
        image_formset = ProductImageFormSet(request.POST, request.FILES)
        variant_formset = ProductVariantFormSet(request.POST)
        
        if form.is_valid() and image_formset.is_valid() and variant_formset.is_valid():
            with transaction.atomic():
                product = form.save()
                
                images = image_formset.save(commit=False)
                for image in images:
                    image.product = product
                    image.save()
                image_formset.save_m2m()
                
                variants = variant_formset.save(commit=False)
                for variant in variants:
                    variant.product = product
                    variant.save()
                variant_formset.save_m2m()
                
                return redirect('catalog:detail', slug=product.slug)
    else:
        form = ProductForm()
        image_formset = ProductImageFormSet()
        variant_formset = ProductVariantFormSet()
    
    return render(request, 'catalog/product_form.html', {
        'form': form,
        'image_formset': image_formset,
        'variant_formset': variant_formset
    })

class ProductListView(ListView):
    model = Product
    template_name = "catalog/product_list.html"
    context_object_name = "products"
    paginate_by = 12

    SORT_OPTIONS = {
        "newest": ("-created_at", "-updated_at"),
        "price_asc": ("effective_price", "name"),
        "price_desc": ("-effective_price", "name"),
        "name": ("name",),
    }

    def get_queryset(self):
        qs = (
            Product.objects.filter(is_active=True)
            .select_related("brand")
            .prefetch_related("images", "categories", "variants")
            .annotate(
                effective_price=Coalesce(
                    "discount_price",
                    "price",
                    output_field=DecimalField(max_digits=10, decimal_places=0),
                )
            )
        )

        category_slug = self.request.GET.get("category")
        brand_slug = self.request.GET.get("brand")
        search_query = self.request.GET.get("q", "").strip()
        min_price = self.request.GET.get("min_price", "").strip()
        max_price = self.request.GET.get("max_price", "").strip()
        sort = self.request.GET.get("sort", "newest")

        if category_slug:
            qs = qs.filter(categories__slug=category_slug)

        if brand_slug:
            qs = qs.filter(brand__slug=brand_slug)

        if search_query:
            qs = qs.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(sku__icontains=search_query)
            )

        if min_price.isdigit():
            qs = qs.filter(effective_price__gte=int(min_price))

        if max_price.isdigit():
            qs = qs.filter(effective_price__lte=int(max_price))

        ordering = self.SORT_OPTIONS.get(sort, self.SORT_OPTIONS["newest"])
        return qs.distinct().order_by(*ordering)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        enrich_product_cards(context["products"])
        context["categories"] = Category.objects.filter(is_active=True)
        context["brands"] = Brand.objects.filter(is_active=True)
        context["sort_options"] = [
            ("newest", "Novedades"),
            ("price_asc", "Precio: menor a mayor"),
            ("price_desc", "Precio: mayor a menor"),
            ("name", "Nombre A-Z"),
        ]
        context["active_filters"] = {
            "q": self.request.GET.get("q", "").strip(),
            "category": self.request.GET.get("category", "").strip(),
            "brand": self.request.GET.get("brand", "").strip(),
            "min_price": self.request.GET.get("min_price", "").strip(),
            "max_price": self.request.GET.get("max_price", "").strip(),
            "sort": self.request.GET.get("sort", "newest").strip() or "newest",
        }
        params = self.request.GET.copy()
        params.pop("page", None)
        context["current_query"] = params.urlencode()
        context["results_count"] = self.get_queryset().count()
        context["seo_title"], context["seo_description"] = build_catalog_seo(
            context["active_filters"],
            context["results_count"],
        )
        if self.request.user.is_authenticated:
            context["wishlist_product_ids"] = set(
                Wishlist.objects.filter(user=self.request.user).values_list("product_id", flat=True)
            )
        else:
            context["wishlist_product_ids"] = set()
        context["catalog_reassurance"] = CATALOG_REASSURANCE
        return context


class ProductDetailView(DetailView):
    model = Product
    template_name = "catalog/product_detail.html"
    context_object_name = "product"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return (
            Product.objects.filter(is_active=True)
            .select_related("brand")
            .prefetch_related("images", "variants", "categories")
            .annotate(
                effective_price=Coalesce(
                    "discount_price",
                    "price",
                    output_field=DecimalField(max_digits=10, decimal_places=0),
                )
            )
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.object

        related_products = (
            Product.objects.filter(is_active=True)
            .select_related("brand")
            .prefetch_related("images", "variants")
            .annotate(
                effective_price=Coalesce(
                    "discount_price",
                    "price",
                    output_field=DecimalField(max_digits=10, decimal_places=0),
                )
            )
            .filter(
                Q(categories__in=product.categories.all()) | Q(brand=product.brand)
            )
            .exclude(id=product.id)
            .distinct()
            .order_by("-is_featured", "-created_at")[:4]
        )
        related_products = list(related_products)
        enrich_product_cards(related_products)

        context["related_products"] = related_products
        context["product_images"] = product.images.all()
        available_variants = list(product.variants.filter(is_active=True))
        has_in_stock_variants = any(variant.stock > 0 for variant in available_variants)
        total_stock = sum(variant.stock for variant in available_variants)
        context["available_variants"] = available_variants
        context["has_in_stock_variants"] = has_in_stock_variants
        context["total_variant_stock"] = total_stock
        context["is_new_drop"] = product.created_at >= timezone.now() - timedelta(days=21)
        if context["is_new_drop"]:
            context["purchase_signal"] = "Nuevo drop incorporado recientemente al catalogo."
        elif 0 < total_stock <= 3:
            context["purchase_signal"] = "Quedan pocas unidades activas entre las tallas disponibles."
        elif has_in_stock_variants:
            context["purchase_signal"] = "Stock activo y tallas visibles para decidir con mas seguridad."
        else:
            context["purchase_signal"] = "Puedes guardarlo en favoritos y volver cuando reingrese stock."
        context["product_reassurance"] = build_product_reassurance(
            product,
            has_in_stock_variants,
        )
        brand_name = product.brand.name if product.brand else "001xclusiv"
        context["seo_title"] = f"{product.name} | {brand_name} - 001xclusiv"
        context["seo_description"] = (
            product.short_description
            or product.description[:155]
            or f"{product.name} en 001xclusiv. Compra con stock visible, guia de tallas y despacho claro."
        )
        if self.request.user.is_authenticated:
            context["is_wishlisted"] = Wishlist.objects.filter(
                user=self.request.user,
                product=product,
            ).exists()
            context["wishlist_product_ids"] = set(
                Wishlist.objects.filter(user=self.request.user).values_list("product_id", flat=True)
            )
        else:
            context["is_wishlisted"] = False
            context["wishlist_product_ids"] = set()
        return context


class WishlistListView(LoginRequiredMixin, ListView):
    model = Wishlist
    template_name = "catalog/wishlist.html"
    context_object_name = "wishlist_items"

    def get_queryset(self):
        return Wishlist.objects.filter(user=self.request.user).select_related("product").prefetch_related("product__images")


@login_required
def toggle_wishlist(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    wishlist_item, created = Wishlist.objects.get_or_create(user=request.user, product=product)

    if not created:
        wishlist_item.delete()
        added = False
    else:
        added = True

    return JsonResponse({
        "added": added,
        "count": Wishlist.objects.filter(user=request.user).count()
    })

