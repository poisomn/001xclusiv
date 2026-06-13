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
        "subtotal_amount",
        "discount_amount",
        "net_amount",
        "tax_amount",
        "total_amount",
        "promo_code",
        "status",
        "payment_status",
        "created_at",
        "receipt_link",
    ]
    list_filter = ["status", "payment_status", "is_paid", "created_at"]
    search_fields = ["id", "full_name", "email", "payment_id", "payment_token", "promo_code"]
    list_editable = ["status", "payment_status"]
    readonly_fields = [
        "created_at",
        "updated_at",
        "subtotal_amount",
        "discount_amount",
        "net_amount",
        "tax_amount",
        "tax_rate",
        "total_amount",
        "stock_committed",
        "promotion_committed",
    ]
    save_on_top = True
    inlines = [OrderItemInline]
    fieldsets = (
        ("Cliente", {"fields": ("user", "full_name", "email")}),
        ("Despacho", {"fields": ("address", "city", "postal_code")}),
        (
            "Pago",
            {
                "fields": (
                    "total_amount",
                    "subtotal_amount",
                    "discount_amount",
                    "net_amount",
                    "tax_amount",
                    "tax_rate",
                    "promo_code",
                    "status",
                    "payment_status",
                    "payment_id",
                    "payment_token",
                    "is_paid",
                    "order_created_email_sent",
                    "payment_confirmed_email_sent",
                    "order_cancelled_email_sent",
                    "admin_new_order_email_sent",
                    "stock_committed",
                    "promotion_committed",
                )
            },
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
