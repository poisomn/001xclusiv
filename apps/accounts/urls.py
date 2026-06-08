from django.urls import path
from django.urls import reverse_lazy
from django.contrib.auth import views as auth_views
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(template_name='accounts/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='core:home'), name='logout'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path(
        'password-reset/',
        auth_views.PasswordResetView.as_view(
            template_name='accounts/password_reset_form.html',
            email_template_name='accounts/password_reset_email.txt',
            subject_template_name='accounts/password_reset_subject.txt',
            success_url=reverse_lazy('accounts:password_reset_done'),
        ),
        name='password_reset',
    ),
    path(
        'password-reset/done/',
        auth_views.PasswordResetDoneView.as_view(template_name='accounts/password_reset_done.html'),
        name='password_reset_done',
    ),
    path(
        'reset/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='accounts/password_reset_confirm.html',
            success_url=reverse_lazy('accounts:password_reset_complete'),
        ),
        name='password_reset_confirm',
    ),
    path(
        'reset/done/',
        auth_views.PasswordResetCompleteView.as_view(template_name='accounts/password_reset_complete.html'),
        name='password_reset_complete',
    ),
    path('backoffice/', views.BackofficeDashboardView.as_view(), name='backoffice_dashboard'),
    path('backoffice/products/', views.BackofficeProductListView.as_view(), name='backoffice_products'),
    path('backoffice/products/autosave/', views.backoffice_product_autosave, name='backoffice_product_autosave'),
    path('backoffice/products/<int:product_id>/action/', views.BackofficeProductActionView.as_view(), name='backoffice_product_action'),
    path('backoffice/products/new/', views.BackofficeProductFormView.as_view(), name='backoffice_product_create'),
    path('backoffice/products/<int:product_id>/edit/', views.BackofficeProductFormView.as_view(), name='backoffice_product_edit'),
    path('backoffice/orders/', views.BackofficeOrderListView.as_view(), name='backoffice_orders'),
    path('backoffice/orders/<int:order_id>/action/', views.BackofficeOrderActionView.as_view(), name='backoffice_order_action'),
    path('backoffice/orders/<int:order_id>/', views.BackofficeOrderDetailView.as_view(), name='backoffice_order_detail'),
    path('backoffice/community/', views.BackofficeCommunityListView.as_view(), name='backoffice_community'),
    path('backoffice/community/new/', views.BackofficeCommunityFormView.as_view(), name='backoffice_community_create'),
    path('backoffice/community/<int:image_id>/edit/', views.BackofficeCommunityFormView.as_view(), name='backoffice_community_edit'),
    path('backoffice/community/<int:image_id>/action/', views.BackofficeCommunityActionView.as_view(), name='backoffice_community_action'),
    path('backoffice/messages/', views.BackofficeMessagesView.as_view(), name='backoffice_messages'),
    path('backoffice/taxonomy/', views.BackofficeTaxonomyView.as_view(), name='backoffice_taxonomy'),
    path('backoffice/categories/<int:category_id>/edit/', views.BackofficeCategoryEditView.as_view(), name='backoffice_category_edit'),
    path('backoffice/brands/<int:brand_id>/edit/', views.BackofficeBrandEditView.as_view(), name='backoffice_brand_edit'),
    path('backoffice/users/', views.BackofficeUserListView.as_view(), name='backoffice_users'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('orders/', views.ProfileView.as_view(), name='my_orders'),
    path('profile/orders/<int:order_id>/', views.OrderDetailView.as_view(), name='order_detail'),
    path('profile/orders/<int:order_id>/receipt/', views.OrderReceiptView.as_view(), name='order_receipt'),
]
