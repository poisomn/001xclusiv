from django import forms
from apps.orders.models import Order

class CheckoutForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['full_name', 'email', 'address', 'city', 'postal_code']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tu nombre completo'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'tu@email.com'}),
            'address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Calle 123'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ciudad'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Código Postal'}),
        }
