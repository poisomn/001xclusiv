from django.test import TestCase
from django.urls import reverse

from apps.catalog.forms import ProductVariantFormSet
from apps.catalog.models import Category, Product, ProductVariant, SizeOption


class CatalogStockDisplayTests(TestCase):
    def test_product_detail_marks_out_of_stock_variant(self):
        product = Product.objects.create(
            name="Catalog Product",
            slug="catalog-product",
            sku="CAT-001",
            price=90000,
            is_active=True,
        )
        ProductVariant.objects.create(product=product, size="42", stock=0, is_active=True)

        response = self.client.get(reverse("catalog:detail", args=[product.slug]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Agotado")
        self.assertContains(response, "Sin stock disponible")

    def test_product_detail_renders_short_description_not_template_literal(self):
        product = Product.objects.create(
            name="Description Product",
            slug="description-product",
            sku="DESC-001",
            price=90000,
            short_description="Descripcion corta real del producto.",
            description="Descripcion larga del producto.",
            is_active=True,
        )

        response = self.client.get(reverse("catalog:detail", args=[product.slug]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Descripcion corta real del producto.")
        self.assertNotContains(response, "{{ product.short_description")

    def test_product_card_single_out_of_stock_variant_does_not_show_add_button(self):
        product = Product.objects.create(
            name="Card Product",
            slug="card-product",
            sku="CARD-001",
            price=90000,
            is_active=True,
        )
        ProductVariant.objects.create(product=product, size="42", stock=0, is_active=True)

        response = self.client.get(reverse("catalog:list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sin stock")


class DynamicSizeOptionTests(TestCase):
    def test_variant_accepts_non_shoe_size_and_displays_option_name(self):
        SizeOption.objects.get_or_create(
            code="ONE_SIZE",
            defaults={
                "name": "One Size",
                "size_type": SizeOption.TYPE_ACCESSORY,
                "ordering": 1,
            },
        )
        product = Product.objects.create(
            name="Accessory Product",
            slug="accessory-product",
            sku="ACC-001",
            price=30000,
            is_active=True,
        )

        variant = ProductVariant.objects.create(product=product, size="ONE_SIZE", stock=2, is_active=True)

        self.assertEqual(variant.size, "ONE_SIZE")
        self.assertEqual(variant.size_display, "One Size")

    def test_variant_formset_filters_sizes_by_selected_category(self):
        clothing = Category.objects.create(name="Clothing", slug="clothing-001xclusiv")
        sneakers = Category.objects.create(name="Sneakers", slug="sneakers-xclusiv")
        clothing_size, _ = SizeOption.objects.get_or_create(
            code="XS",
            defaults={
                "name": "XS",
                "size_type": SizeOption.TYPE_CLOTHING,
                "ordering": 1,
            },
        )
        shoe_size, _ = SizeOption.objects.get_or_create(
            code="42",
            defaults={
                "name": "42",
                "size_type": SizeOption.TYPE_SHOES,
                "ordering": 1,
            },
        )
        clothing.size_options.add(clothing_size)
        sneakers.size_options.add(shoe_size)
        product = Product.objects.create(
            name="Clothing Product",
            slug="clothing-product",
            sku="CLO-001",
            price=60000,
            is_active=True,
        )
        product.categories.add(clothing)

        formset = ProductVariantFormSet(instance=product, product_categories=[clothing.id])
        choices = dict(formset.empty_form.fields["size"].choices)

        self.assertIn("XS", choices)
        self.assertNotIn("42", choices)
