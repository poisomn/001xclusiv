from django.urls import path
from . import views

app_name = 'checkout'

urlpatterns = [
    path('', views.CheckoutView.as_view(), name='index'),
    path('success/<int:order_id>/', views.checkout_success, name='success'),
]
