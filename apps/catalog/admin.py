from django.contrib import admin
from .models import Category, Brand, Product, ProductImage, ProductVariant


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "brand",
        "price",
        "discount_price",
        "is_active",
        "is_featured",
        "created_at",
    )
    list_filter = ("is_active", "is_featured", "brand", "categories")
    search_fields = ("name", "sku")
    prepopulated_fields = {"slug": ("name",)}
    filter_horizontal = ("categories",)
    inlines = [ProductImageInline, ProductVariantInline]


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ("product", "is_main", "ordering", "created_at")
    list_filter = ("is_main",)
    search_fields = ("product__name",)


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ("product", "size", "stock", "is_active")
    list_filter = ("is_active", "size")
    search_fields = ("product__name",)
