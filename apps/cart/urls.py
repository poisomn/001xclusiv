from django.urls import path
from . import views

app_name = 'cart'

urlpatterns = [
    path('', views.cart_detail, name='cart_detail'),
    path('summary/', views.cart_summary, name='cart_summary'),
    path('promo/apply/', views.cart_apply_promo, name='cart_apply_promo'),
    path('promo/remove/', views.cart_remove_promo, name='cart_remove_promo'),
    path('add/<int:product_id>/', views.cart_add, name='cart_add'),
    path('update/<int:product_id>/', views.cart_update, name='cart_update'),
    path('remove/<int:product_id>/', views.cart_remove, name='cart_remove'),
]
