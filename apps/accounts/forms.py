import logging

from django import forms
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.template.loader import render_to_string
from django.utils.html import escape

from apps.catalog.models import Brand, Category
from apps.core.models import CommunityImage
from apps.notifications.gmail_service import gmail_credentials_available, send_gmail_message
from apps.orders.models import Order

logger = logging.getLogger(__name__)


class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control'}))

    class Meta:
        model = User
        fields = ['username', 'email']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
        }


class GmailPasswordResetForm(PasswordResetForm):
    def send_mail(
        self,
        subject_template_name,
        email_template_name,
        context,
        from_email,
        to_email,
        html_email_template_name=None,
    ):
        if not gmail_credentials_available():
            logger.warning("Password reset email skipped for %s: Gmail API is not configured.", to_email)
            return False

        try:
            subject = render_to_string(subject_template_name, context)
            subject = "".join(subject.splitlines())
            text_body = render_to_string(email_template_name, context)
            if html_email_template_name:
                html_body = render_to_string(html_email_template_name, context)
            else:
                html_body = "<br>".join(escape(text_body).splitlines())

            return send_gmail_message(
                to=to_email,
                subject=subject,
                html_body=html_body,
                text_body=text_body,
            )
        except Exception:
            logger.exception("Could not send password reset email to %s", to_email)
            return False


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
