import logging

from django import forms
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.template.loader import render_to_string
from django.utils.html import escape
from django.utils import timezone

from apps.catalog.models import Brand, Category, SizeOption
from apps.cart.models import PromotionCode
from apps.core.models import CommunityImage
from apps.notifications.gmail_service import gmail_credentials_available, send_gmail_message
from apps.orders.models import Order

logger = logging.getLogger(__name__)


class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={"class": "form-control auth-input"}))

    class Meta:
        model = User
        fields = ['username', 'email']
        widgets = {
            'username': forms.TextInput(attrs={"class": "form-control auth-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        autocomplete = {
            "username": "username",
            "email": "email",
            "password1": "new-password",
            "password2": "new-password",
        }
        for field_name, field in self.fields.items():
            css_class = field.widget.attrs.get("class", "")
            if "auth-input" not in css_class:
                field.widget.attrs["class"] = f"{css_class} auth-input".strip()
            field.widget.attrs.setdefault("autocomplete", autocomplete.get(field_name, "off"))


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
        fields = [
            "name",
            "slug",
            "image_url",
            "image_path",
            "image_alt_text",
            "visual_eyebrow",
            "size_options",
            "is_active",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ej. Jordan"}),
            "slug": forms.TextInput(attrs={"class": "form-control", "placeholder": "jordan"}),
            "image_url": forms.URLInput(attrs={"class": "form-control", "placeholder": "https://..."}),
            "image_path": forms.TextInput(attrs={"class": "form-control", "placeholder": "home/ropa.jpg"}),
            "image_alt_text": forms.TextInput(attrs={"class": "form-control", "placeholder": "Imagen de categoria"}),
            "visual_eyebrow": forms.TextInput(attrs={"class": "form-control", "placeholder": "Curado para ti"}),
            "size_options": forms.SelectMultiple(attrs={"class": "form-select"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["size_options"].queryset = SizeOption.objects.order_by("size_type", "ordering", "name")


class BrandManagementForm(forms.ModelForm):
    class Meta:
        model = Brand
        fields = ["name", "slug", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ej. Nike"}),
            "slug": forms.TextInput(attrs={"class": "form-control", "placeholder": "nike"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class SizeOptionManagementForm(forms.ModelForm):
    class Meta:
        model = SizeOption
        fields = ["name", "code", "size_type", "ordering", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ej. XS, 42, One Size"}),
            "code": forms.TextInput(attrs={"class": "form-control", "placeholder": "XS, 42, ONE_SIZE"}),
            "size_type": forms.Select(attrs={"class": "form-select"}),
            "ordering": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean_code(self):
        value = self.cleaned_data["code"]
        return "_".join(value.strip().upper().split())


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


class ShippingUpdateForm(forms.ModelForm):
    event_message = forms.CharField(
        label="Mensaje visible para cliente",
        max_length=500,
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Ej. Tu pedido ya fue recibido por el transportista.",
            }
        ),
    )
    event_occurred_at = forms.DateTimeField(
        label="Fecha y hora del evento",
        initial=timezone.now,
        input_formats=["%Y-%m-%dT%H:%M"],
        widget=forms.DateTimeInput(
            attrs={"class": "form-control", "type": "datetime-local"},
            format="%Y-%m-%dT%H:%M",
        ),
    )

    class Meta:
        model = Order
        fields = ["shipping_status", "carrier_name", "tracking_number", "estimated_delivery_date"]
        widgets = {
            "shipping_status": forms.Select(attrs={"class": "form-select"}),
            "carrier_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Ej. Chilexpress"}
            ),
            "tracking_number": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Opcional"}
            ),
            "estimated_delivery_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"},
                format="%Y-%m-%d",
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["event_occurred_at"].initial = timezone.localtime()


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


class PromotionCodeForm(forms.ModelForm):
    class Meta:
        model = PromotionCode
        fields = [
            "code",
            "description",
            "discount_type",
            "discount_value",
            "is_active",
            "valid_from",
            "valid_until",
            "minimum_order_amount",
            "max_discount_amount",
            "usage_limit",
            "notes",
        ]
        widgets = {
            "code": forms.TextInput(attrs={"class": "form-control", "placeholder": "XCLUSIV15"}),
            "description": forms.TextInput(attrs={"class": "form-control", "placeholder": "15% OFF newsletter"}),
            "discount_type": forms.Select(attrs={"class": "form-select"}),
            "discount_value": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "valid_from": forms.DateTimeInput(attrs={"class": "form-control", "type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "valid_until": forms.DateTimeInput(attrs={"class": "form-control", "type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "minimum_order_amount": forms.NumberInput(attrs={"class": "form-control", "step": "1", "min": "0"}),
            "max_discount_amount": forms.NumberInput(attrs={"class": "form-control", "step": "1", "min": "0"}),
            "usage_limit": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ("valid_from", "valid_until"):
            self.fields[field_name].input_formats = ["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S"]

    def clean_code(self):
        return "".join((self.cleaned_data["code"] or "").split()).upper()
