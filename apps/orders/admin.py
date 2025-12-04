from django.contrib import admin
from .models import Order, OrderItem

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    raw_id_fields = ['product']

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'full_name', 'email', 'city', 'is_paid', 'status', 'created_at']
    list_filter = ['is_paid', 'created_at', 'updated_at', 'status']
    inlines = [OrderItemInline]
