from django import forms

from apps.orders.models import Order


class CheckoutForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        placeholders = {
            "full_name": "Nombre y apellido",
            "email": "correo@ejemplo.com",
            "address": "Calle, numero, depto o referencia",
            "city": "Ciudad o comuna",
            "postal_code": "Codigo postal",
        }
        autocomplete = {
            "full_name": "name",
            "email": "email",
            "address": "street-address",
            "city": "address-level2",
            "postal_code": "postal-code",
        }

        for name, field in self.fields.items():
            field.widget.attrs.update(
                {
                    "class": "form-control checkout-input",
                    "placeholder": placeholders[name],
                    "autocomplete": autocomplete[name],
                }
            )

    def clean_full_name(self):
        full_name = self.cleaned_data["full_name"].strip()
        if len(full_name.split()) < 2:
            raise forms.ValidationError("Ingresa nombre y apellido para el despacho.")
        return full_name

    def clean_address(self):
        address = self.cleaned_data["address"].strip()
        if len(address) < 8:
            raise forms.ValidationError("Ingresa una direccion mas completa.")
        return address

    def clean_city(self):
        return self.cleaned_data["city"].strip()

    def clean_postal_code(self):
        return self.cleaned_data["postal_code"].strip()

    class Meta:
        model = Order
        fields = ["full_name", "email", "address", "city", "postal_code"]
        widgets = {
            "full_name": forms.TextInput(),
            "email": forms.EmailInput(),
            "address": forms.TextInput(),
            "city": forms.TextInput(),
            "postal_code": forms.TextInput(),
        }
