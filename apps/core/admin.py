from django.contrib import admin

from .models import CommunityImage, NewsletterSubscriber


@admin.register(CommunityImage)
class CommunityImageAdmin(admin.ModelAdmin):
    list_display = ("instagram_handle", "caption", "is_active", "ordering", "created_at")
    list_filter = ("is_active",)
    search_fields = ("instagram_handle", "caption", "image_url")
    list_editable = ("is_active", "ordering")


@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = ("email", "discount_code", "is_active", "welcome_email_sent", "created_at")
    list_filter = ("is_active", "welcome_email_sent", "created_at")
    search_fields = ("email", "discount_code")
    readonly_fields = ("created_at", "updated_at")
    list_editable = ("is_active",)
