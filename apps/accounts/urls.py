from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(template_name='accounts/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='core:home'), name='logout'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('backoffice/', views.BackofficeDashboardView.as_view(), name='backoffice_dashboard'),
    path('backoffice/products/', views.BackofficeProductListView.as_view(), name='backoffice_products'),
    path('backoffice/products/<int:product_id>/action/', views.BackofficeProductActionView.as_view(), name='backoffice_product_action'),
    path('backoffice/products/new/', views.BackofficeProductFormView.as_view(), name='backoffice_product_create'),
    path('backoffice/products/<int:product_id>/edit/', views.BackofficeProductFormView.as_view(), name='backoffice_product_edit'),
    path('backoffice/orders/', views.BackofficeOrderListView.as_view(), name='backoffice_orders'),
    path('backoffice/orders/<int:order_id>/action/', views.BackofficeOrderActionView.as_view(), name='backoffice_order_action'),
    path('backoffice/orders/<int:order_id>/', views.BackofficeOrderDetailView.as_view(), name='backoffice_order_detail'),
    path('backoffice/taxonomy/', views.BackofficeTaxonomyView.as_view(), name='backoffice_taxonomy'),
    path('backoffice/categories/<int:category_id>/edit/', views.BackofficeCategoryEditView.as_view(), name='backoffice_category_edit'),
    path('backoffice/brands/<int:brand_id>/edit/', views.BackofficeBrandEditView.as_view(), name='backoffice_brand_edit'),
    path('backoffice/users/', views.BackofficeUserListView.as_view(), name='backoffice_users'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('orders/', views.ProfileView.as_view(), name='my_orders'),
    path('profile/orders/<int:order_id>/', views.OrderDetailView.as_view(), name='order_detail'),
    path('profile/orders/<int:order_id>/receipt/', views.OrderReceiptView.as_view(), name='order_receipt'),
]
