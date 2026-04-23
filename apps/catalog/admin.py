from django.contrib import admin
from django.db.models import Sum
from django.urls import reverse
from django.utils.html import format_html

from .models import Brand, Category, Product, ProductImage, ProductVariant


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ("image", "alt_text", "is_main", "ordering")


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    fields = ("size", "stock", "is_active")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "cover_preview",
        "name",
        "brand",
        "effective_price_display",
        "stock_summary",
        "is_active",
        "is_featured",
        "created_at",
    )
    list_filter = ("is_active", "is_featured", "brand", "categories")
    search_fields = ("name", "sku")
    prepopulated_fields = {"slug": ("name",)}
    filter_horizontal = ("categories",)
    inlines = [ProductImageInline, ProductVariantInline]
    list_editable = ("is_active", "is_featured")
    readonly_fields = ("created_at", "updated_at", "cover_preview_large")
    list_per_page = 25
    save_on_top = True
    ordering = ("-created_at",)
    actions = (
        "mark_as_featured",
        "remove_from_featured",
        "publish_products",
        "unpublish_products",
    )
    fieldsets = (
        ("Identidad", {
            "fields": ("name", "slug", "sku", "brand", "categories"),
        }),
        ("Precio y contenido", {
            "fields": ("price", "discount_price", "short_description", "description"),
        }),
        ("Estado", {
            "fields": ("is_active", "is_featured"),
        }),
        ("Vista previa", {
            "fields": ("cover_preview_large",),
        }),
        ("Trazabilidad", {
            "fields": ("created_at", "updated_at"),
        }),
    )

    @admin.display(description="Imagen")
    def cover_preview(self, obj):
        main_image = obj.images.filter(is_main=True).first() or obj.images.order_by("ordering", "id").first()
        if not main_image:
            return "Sin imagen"
        return format_html(
            '<img src="{}" alt="{}" style="width:52px;height:52px;object-fit:cover;border-radius:12px;border:1px solid rgba(17,17,17,.08);" />',
            main_image.image.url,
            obj.name,
        )

    @admin.display(description="Vista previa")
    def cover_preview_large(self, obj):
        if not obj.pk:
            return "Guarda el producto para cargar imagenes."
        main_image = obj.images.filter(is_main=True).first() or obj.images.order_by("ordering", "id").first()
        if not main_image:
            return "Sin imagen principal."
        return format_html(
            '<img src="{}" alt="{}" style="width:140px;height:140px;object-fit:cover;border-radius:20px;border:1px solid rgba(17,17,17,.08);" />',
            main_image.image.url,
            obj.name,
        )

    @admin.display(description="Precio final", ordering="discount_price")
    def effective_price_display(self, obj):
        if obj.discount_price:
            return format_html(
                '<strong>${}</strong><br><span style="color:#666;">Base: ${}</span>',
                int(obj.discount_price),
                int(obj.price),
            )
        return f"${int(obj.price)}"

    @admin.display(description="Stock total")
    def stock_summary(self, obj):
        total_stock = obj.variants.aggregate(total=Sum("stock")).get("total") or 0
        active_variants = obj.variants.filter(is_active=True).count()
        if total_stock <= 0:
            return format_html('<span style="color:#b42318;font-weight:600;">Sin stock</span>')
        if total_stock <= 5:
            return format_html(
                '<span style="color:#b54708;font-weight:600;">Bajo ({})</span><br><span style="color:#666;">{} tallas activas</span>',
                total_stock,
                active_variants,
            )
        return format_html(
            '<span style="font-weight:600;">{}</span><br><span style="color:#666;">{} tallas activas</span>',
            total_stock,
            active_variants,
        )

    @admin.action(description="Marcar seleccionados como destacados")
    def mark_as_featured(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(request, f"{updated} producto(s) marcados como destacados.")

    @admin.action(description="Quitar destacados de la seleccion")
    def remove_from_featured(self, request, queryset):
        updated = queryset.update(is_featured=False)
        self.message_user(request, f"{updated} producto(s) ya no estan destacados.")

    @admin.action(description="Publicar productos seleccionados")
    def publish_products(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} producto(s) publicados.")

    @admin.action(description="Despublicar productos seleccionados")
    def unpublish_products(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} producto(s) despublicados.")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}
    list_editable = ("is_active",)


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}
    list_editable = ("is_active",)


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ("preview", "product", "is_main", "ordering", "created_at")
    list_filter = ("is_main",)
    search_fields = ("product__name",)
    list_editable = ("is_main", "ordering")

    @admin.display(description="Imagen")
    def preview(self, obj):
        return format_html(
            '<img src="{}" alt="{}" style="width:52px;height:52px;object-fit:cover;border-radius:12px;border:1px solid rgba(17,17,17,.08);" />',
            obj.image.url,
            obj.alt_text or obj.product.name,
        )


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ("product", "size", "stock", "is_active")
    list_filter = ("is_active", "size")
    search_fields = ("product__name",)
    list_editable = ("stock", "is_active")
