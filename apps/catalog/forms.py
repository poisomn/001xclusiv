from django import forms
from django.forms.models import BaseInlineFormSet
from django.forms import inlineformset_factory
from .models import Product, ProductImage, ProductVariant, SizeOption


def _clean_category_ids(category_ids):
    clean_ids = []
    for category_id in category_ids or []:
        try:
            clean_ids.append(int(category_id))
        except (TypeError, ValueError):
            continue
    return clean_ids


def get_size_choices_for_product(product=None, category_ids=None, include_values=None):
    include_values = [value for value in (include_values or []) if value]
    active_sizes = SizeOption.objects.filter(is_active=True)
    selected_category_ids = _clean_category_ids(category_ids)

    if selected_category_ids:
        category_sizes = active_sizes.filter(categories__id__in=selected_category_ids).distinct()
        if category_sizes.exists():
            active_sizes = category_sizes
    elif product and product.pk:
        category_sizes = active_sizes.filter(categories__products=product).distinct()
        if category_sizes.exists():
            active_sizes = category_sizes

    choices = [(option.code, option.name) for option in active_sizes.order_by("ordering", "name")]
    known_values = {value for value, _ in choices}
    for value in include_values:
        if value not in known_values:
            choices.append((value, value))
            known_values.add(value)
    return [("", "Selecciona talla")] + choices

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'name', 'slug', 'sku', 'brand', 'categories',
            'price', 'discount_price', 'short_description', 'description', 'image_url',
            'is_active', 'is_featured', 'show_in_new_arrivals', 'new_arrival_order'
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
            'show_in_new_arrivals': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'new_arrival_order': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
        }


class ProductVariantForm(forms.ModelForm):
    size = forms.ChoiceField(label="Talla", required=True, choices=[])

    class Meta:
        model = ProductVariant
        fields = ["size", "stock", "is_active"]
        widgets = {
            "stock": forms.NumberInput(attrs={"class": "form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, size_choices=None, **kwargs):
        super().__init__(*args, **kwargs)
        include_values = [self.instance.size] if self.instance and self.instance.pk else []
        self.fields["size"].choices = size_choices or get_size_choices_for_product(
            product=getattr(self.instance, "product", None),
            include_values=include_values,
        )
        self.fields["size"].widget.attrs.update({"class": "form-select"})


class BaseProductVariantFormSet(BaseInlineFormSet):
    def __init__(self, *args, product_categories=None, **kwargs):
        self.product_categories = product_categories
        super().__init__(*args, **kwargs)

    def _choices_for_form(self, form=None):
        include_values = []
        if form and form.instance and form.instance.pk:
            include_values.append(form.instance.size)
        return get_size_choices_for_product(
            product=self.instance,
            category_ids=self.product_categories,
            include_values=include_values,
        )

    def _construct_form(self, i, **kwargs):
        form = super()._construct_form(i, **kwargs)
        form.fields["size"].choices = self._choices_for_form(form)
        return form

    @property
    def empty_form(self):
        form = super().empty_form
        form.fields["size"].choices = self._choices_for_form()
        return form

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
    form=ProductVariantForm,
    formset=BaseProductVariantFormSet,
    fields=['size', 'stock', 'is_active'],
    extra=1,
    can_delete=True,
)
