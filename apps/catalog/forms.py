from django import forms
from django.forms import inlineformset_factory
from .models import Product, ProductImage, ProductVariant

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'name', 'slug', 'sku', 'brand', 'categories',
            'price', 'discount_price', 'short_description', 'description', 'image_url',
            'is_active', 'is_featured'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'slug': forms.TextInput(attrs={'class': 'form-control'}),
            'sku': forms.TextInput(attrs={'class': 'form-control'}),
            'brand': forms.Select(attrs={'class': 'form-select'}),
            'categories': forms.SelectMultiple(attrs={'class': 'form-select'}),
            'price': forms.NumberInput(attrs={'class': 'form-control'}),
            'discount_price': forms.NumberInput(attrs={'class': 'form-control'}),
            'short_description': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'image_url': forms.URLInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

ProductImageFormSet = inlineformset_factory(
    Product,
    ProductImage,
    fields=['image_url', 'alt_text', 'is_main', 'ordering'],
    extra=1,
    can_delete=True,
    widgets={
        'image_url': forms.URLInput(attrs={'class': 'form-control'}),
        'alt_text': forms.TextInput(attrs={'class': 'form-control'}),
        'is_main': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        'ordering': forms.NumberInput(attrs={'class': 'form-control'}),
    }
)

ProductVariantFormSet = inlineformset_factory(
    Product,
    ProductVariant,
    fields=['size', 'stock', 'is_active'],
    extra=1,
    can_delete=True,
    widgets={
        'size': forms.Select(attrs={'class': 'form-select'}),
        'stock': forms.NumberInput(attrs={'class': 'form-control'}),
        'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    }
)
