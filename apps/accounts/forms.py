from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from apps.catalog.models import Brand, Category
from apps.core.models import CommunityImage
from apps.orders.models import Order

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control'}))

    class Meta:
        model = User
        fields = ['username', 'email']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
        }


class CategoryManagementForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "slug", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ej. Jordan"}),
            "slug": forms.TextInput(attrs={"class": "form-control", "placeholder": "jordan"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class BrandManagementForm(forms.ModelForm):
    class Meta:
        model = Brand
        fields = ["name", "slug", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ej. Nike"}),
            "slug": forms.TextInput(attrs={"class": "form-control", "placeholder": "nike"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class OrderManagementForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ["status", "payment_status", "payment_id", "is_paid"]
        widgets = {
            "status": forms.Select(attrs={"class": "form-select"}),
            "payment_status": forms.Select(attrs={"class": "form-select"}),
            "payment_id": forms.TextInput(attrs={"class": "form-control", "placeholder": "ID de pago"}),
            "is_paid": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class CommunityImageForm(forms.ModelForm):
    class Meta:
        model = CommunityImage
        fields = ["image_url", "instagram_handle", "caption", "is_active", "ordering"]
        widgets = {
            "image_url": forms.URLInput(attrs={"class": "form-control", "placeholder": "https://..."}),
            "instagram_handle": forms.TextInput(attrs={"class": "form-control", "placeholder": "@001xclusiv"}),
            "caption": forms.TextInput(attrs={"class": "form-control", "placeholder": "Look real de la comunidad"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "ordering": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
        }
