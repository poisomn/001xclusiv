from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from .models import Order, OrderItem

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    raw_id_fields = ['product']
    extra = 0
    autocomplete_fields = ['variant']

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'full_name',
        'email',
        'city',
        'order_total',
        'is_paid',
        'status',
        'created_at',
        'receipt_link',
    ]
    list_filter = ['is_paid', 'created_at', 'updated_at', 'status', 'city']
    search_fields = ['id', 'full_name', 'email']
    list_editable = ['status', 'is_paid']
    readonly_fields = ['created_at', 'updated_at', 'order_total']
    save_on_top = True
    inlines = [OrderItemInline]
    fieldsets = (
        ('Cliente', {
            'fields': ('user', 'full_name', 'email'),
        }),
        ('Despacho', {
            'fields': ('address', 'city', 'postal_code'),
        }),
        ('Estado de orden', {
            'fields': ('status', 'is_paid', 'order_total'),
        }),
        ('Trazabilidad', {
            'fields': ('created_at', 'updated_at'),
        }),
    )

    @admin.display(description='Total')
    def order_total(self, obj):
        return f"${int(obj.get_total_cost())}"

    @admin.display(description='Comprobante')
    def receipt_link(self, obj):
        if not obj.user_id:
            return 'Sin cuenta'
        url = reverse('accounts:order_receipt', args=[obj.id])
        return format_html('<a href="{}" target="_blank">Ver comprobante</a>', url)
