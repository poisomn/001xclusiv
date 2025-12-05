from django.urls import path
from . import views

app_name = "catalog"

urlpatterns = [
    path("create/", views.product_create, name="create"),
    path("wishlist/", views.WishlistListView.as_view(), name="wishlist"),
    path("wishlist/toggle/<int:product_id>/", views.toggle_wishlist, name="toggle_wishlist"),
    path("", views.ProductListView.as_view(), name="list"),
    path("<slug:slug>/", views.ProductDetailView.as_view(), name="detail"),
]
