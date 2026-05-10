from django.contrib import admin

from .models import CommunityImage


@admin.register(CommunityImage)
class CommunityImageAdmin(admin.ModelAdmin):
    list_display = ("instagram_handle", "caption", "is_active", "ordering", "created_at")
    list_filter = ("is_active",)
    search_fields = ("instagram_handle", "caption", "image_url")
    list_editable = ("is_active", "ordering")
