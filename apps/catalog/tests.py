from django.test import TestCase
from django.urls import reverse

from apps.catalog.models import Product, ProductVariant


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
