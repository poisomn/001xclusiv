from django.urls import path

from . import views


app_name = "payments"

urlpatterns = [
    path("success/", views.payment_success, name="success"),
    path("cancel/", views.payment_cancel, name="cancel"),
    path("webhook/", views.payment_webhook_placeholder, name="webhook"),
]
