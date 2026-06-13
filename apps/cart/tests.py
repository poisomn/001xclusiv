from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.cart.models import PromotionCode
from apps.catalog.models import Product, ProductVariant


class CartPromotionTests(TestCase):
    def setUp(self):
        self.product = Product.objects.create(
            name="Promo Product",
            slug="promo-product",
            sku="PROMO-001",
            price=100000,
        )
        self.promo, _ = PromotionCode.objects.update_or_create(
            code="XCLUSIV15",
            defaults={
                "description": "15% OFF newsletter",
                "discount_type": PromotionCode.DISCOUNT_PERCENT,
                "discount_value": 15,
                "is_active": True,
                "valid_until": None,
                "minimum_order_amount": 0,
            },
        )
        session = self.client.session
        session["cart"] = {
            str(self.product.id): {
                "quantity": 1,
                "price": "100000",
                "product_id": self.product.id,
                "variant_id": None,
            }
        }
        session.save()

    def test_apply_xclusiv15_discount(self):
        response = self.client.post(reverse("cart:cart_apply_promo"), {"code": " xclusiv15 "})

        self.assertRedirects(response, reverse("cart:cart_detail"))
        summary = self.client.get(reverse("cart:cart_summary")).json()
        self.assertEqual(summary["subtotal"], 100000.0)
        self.assertEqual(summary["discount_amount"], 15000.0)
        self.assertEqual(summary["total"], 85000.0)
        self.assertEqual(summary["promo_code"], "XCLUSIV15")

    def test_unknown_code_returns_error(self):
        response = self.client.post(
            reverse("cart:cart_apply_promo"),
            {"code": "NOPE"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["success"])

    def test_inactive_code_returns_error(self):
        self.promo.is_active = False
        self.promo.save(update_fields=["is_active"])

        response = self.client.post(
            reverse("cart:cart_apply_promo"),
            {"code": "XCLUSIV15"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("no esta activo", response.json()["message"])

    def test_minimum_amount_code_returns_error(self):
        self.promo.minimum_order_amount = 150000
        self.promo.save(update_fields=["minimum_order_amount"])

        response = self.client.post(
            reverse("cart:cart_apply_promo"),
            {"code": "XCLUSIV15"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("minimo", response.json()["message"])

    def test_expired_code_returns_error(self):
        self.promo.valid_until = timezone.now() - timezone.timedelta(days=1)
        self.promo.save(update_fields=["valid_until"])

        response = self.client.post(
            reverse("cart:cart_apply_promo"),
            {"code": "XCLUSIV15"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("expiro", response.json()["message"])

    def test_remove_code_restores_total(self):
        self.client.post(reverse("cart:cart_apply_promo"), {"code": "XCLUSIV15"})
        response = self.client.post(reverse("cart:cart_remove_promo"))

        self.assertRedirects(response, reverse("cart:cart_detail"))
        summary = self.client.get(reverse("cart:cart_summary")).json()
        self.assertEqual(summary["discount_amount"], 0.0)
        self.assertEqual(summary["total"], 100000.0)


class CartStockTests(TestCase):
    def setUp(self):
        self.product = Product.objects.create(
            name="Stock Product",
            slug="stock-product",
            sku="STOCK-001",
            price=50000,
        )

    def test_cannot_add_variant_without_stock(self):
        variant = ProductVariant.objects.create(product=self.product, size="42", stock=0, is_active=True)

        response = self.client.post(
            reverse("cart:cart_add", args=[self.product.id]),
            {"variant": variant.id, "quantity": 1},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["success"])

    def test_cannot_add_more_than_stock(self):
        variant = ProductVariant.objects.create(product=self.product, size="42", stock=1, is_active=True)

        response = self.client.post(
            reverse("cart:cart_add", args=[self.product.id]),
            {"variant": variant.id, "quantity": 2},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Solo quedan 1", response.json()["message"])

    def test_existing_cart_quantity_counts_against_stock(self):
        variant = ProductVariant.objects.create(product=self.product, size="42", stock=2, is_active=True)
        self.client.post(reverse("cart:cart_add", args=[self.product.id]), {"variant": variant.id, "quantity": 1})

        response = self.client.post(
            reverse("cart:cart_add", args=[self.product.id]),
            {"variant": variant.id, "quantity": 2},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Solo quedan 2", response.json()["message"])

    def test_update_quantity_cannot_exceed_stock(self):
        variant = ProductVariant.objects.create(product=self.product, size="42", stock=2, is_active=True)
        self.client.post(reverse("cart:cart_add", args=[self.product.id]), {"variant": variant.id, "quantity": 1})

        response = self.client.post(
            reverse("cart:cart_update", args=[self.product.id]),
            {"variant_id": variant.id, "quantity": 3},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Solo quedan 2", response.json()["message"])
