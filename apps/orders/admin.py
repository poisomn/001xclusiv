from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    raw_id_fields = ["product"]
    autocomplete_fields = ["variant"]
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "user",
        "full_name",
        "total_amount",
        "status",
        "payment_status",
        "created_at",
        "receipt_link",
    ]
    list_filter = ["status", "payment_status", "is_paid", "created_at"]
    search_fields = ["id", "full_name", "email", "payment_id"]
    list_editable = ["status", "payment_status"]
    readonly_fields = ["created_at", "updated_at", "total_amount"]
    save_on_top = True
    inlines = [OrderItemInline]
    fieldsets = (
        ("Cliente", {"fields": ("user", "full_name", "email")}),
        ("Despacho", {"fields": ("address", "city", "postal_code")}),
        (
            "Pago",
            {"fields": ("total_amount", "status", "payment_status", "payment_id", "is_paid")},
        ),
        ("Trazabilidad", {"fields": ("created_at", "updated_at")}),
    )

    @admin.display(description="Comprobante")
    def receipt_link(self, obj):
        if not obj.user_id:
            return "Sin cuenta"
        url = reverse("accounts:order_receipt", args=[obj.id])
        return format_html('<a href="{}" target="_blank">Ver comprobante</a>', url)


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ["id", "order", "product", "quantity", "price"]
    search_fields = ["order__id", "product__name"]
