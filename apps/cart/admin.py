from django.contrib import admin

from .models import PromotionCode


@admin.register(PromotionCode)
class PromotionCodeAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "description",
        "discount_type",
        "discount_value",
        "is_active",
        "valid_from",
        "valid_until",
        "usage_limit",
        "used_count",
    )
    list_filter = ("is_active", "discount_type", "valid_from", "valid_until")
    search_fields = ("code", "description")
    readonly_fields = ("used_count", "created_at", "updated_at")
    list_editable = ("is_active",)
    ordering = ("-created_at",)
