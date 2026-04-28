from django.contrib import admin
from django.urls import path, include
from apps.accounts.views import BackofficeDashboardView

urlpatterns = [
    path("admin/dashboard/", BackofficeDashboardView.as_view(), name="admin_dashboard"),
    path("payment/", include("apps.payments.urls")),
    path("admin/", admin.site.urls),
    path("", include("apps.core.urls")),
    path("catalogo/", include("apps.catalog.urls")),
    path("cart/", include("apps.cart.urls")),
    path("checkout/", include("apps.checkout.urls")),
    path("accounts/", include("apps.accounts.urls")),
]
