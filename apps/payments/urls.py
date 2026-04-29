from django.urls import path

from . import views


app_name = "payments"

urlpatterns = [
    path("success/", views.payment_success, name="success"),
    path("return/", views.payment_return, name="return"),
    path("cancel/", views.payment_cancel, name="cancel"),
    path("confirm/", views.payment_webhook, name="confirm"),
    path("webhook/", views.payment_webhook, name="webhook"),
]
