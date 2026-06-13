from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.cart.models import PromotionCode
from apps.catalog.models import Product, ProductVariant
from apps.orders.models import Order


User = get_user_model()


class CheckoutFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="checkout-user", password="pass12345", email="checkout@example.com")
        self.product = Product.objects.create(
            name="Producto checkout",
            slug="producto-checkout",
            sku="CHECKOUT-001",
            price=150000,
        )

    @patch("apps.checkout.views.create_payment")
    def test_checkout_creates_pending_order_and_redirects_to_flow(self, create_payment):
        create_payment.return_value = {
            "url": "https://sandbox.flow.cl/app/web/pay.php",
            "token": "FLOW-TOKEN",
            "flowOrder": 123456,
        }
        self.client.login(username="checkout-user", password="pass12345")
        session = self.client.session
        session["cart"] = {
            str(self.product.id): {
                "quantity": 2,
                "price": "150000",
                "product_id": self.product.id,
                "variant_id": None,
            }
        }
        session.save()

        response = self.client.post(
            reverse("checkout:index"),
            {
                "full_name": "Checkout User",
                "email": "checkout@example.com",
                "address": "Calle Checkout 123",
                "city": "Santiago",
                "postal_code": "7500000",
                "confirm_checkout": "on",
            },
        )

        order = Order.objects.get()
        self.assertEqual(order.status, "pending")
        self.assertEqual(order.total_amount, 300000)
        self.assertEqual(order.items.count(), 1)
        create_payment.assert_called_once()
        self.assertRedirects(
            response,
            "https://sandbox.flow.cl/app/web/pay.php?token=FLOW-TOKEN",
            fetch_redirect_response=False,
        )

    @patch("apps.checkout.views.create_payment")
    def test_checkout_order_uses_discounted_total(self, create_payment):
        create_payment.return_value = {
            "url": "https://sandbox.flow.cl/app/web/pay.php",
            "token": "FLOW-TOKEN",
            "flowOrder": 123456,
        }
        PromotionCode.objects.update_or_create(
            code="XCLUSIV15",
            defaults={
                "discount_type": PromotionCode.DISCOUNT_PERCENT,
                "discount_value": 15,
                "is_active": True,
            },
        )
        self.client.login(username="checkout-user", password="pass12345")
        session = self.client.session
        session["cart"] = {
            str(self.product.id): {
                "quantity": 1,
                "price": "100000",
                "product_id": self.product.id,
                "variant_id": None,
            }
        }
        session["cart_promo_code"] = "XCLUSIV15"
        session.save()

        response = self.client.post(
            reverse("checkout:index"),
            {
                "full_name": "Checkout User",
                "email": "checkout@example.com",
                "address": "Calle Checkout 123",
                "city": "Santiago",
                "postal_code": "7500000",
                "confirm_checkout": "on",
            },
        )

        order = Order.objects.get()
        self.assertEqual(order.subtotal_amount, 100000)
        self.assertEqual(order.discount_amount, 15000)
        self.assertEqual(order.total_amount, 85000)
        self.assertEqual(order.promo_code, "XCLUSIV15")
        self.assertEqual(create_payment.call_args.args[0].total_amount, 85000)
        self.assertRedirects(
            response,
            "https://sandbox.flow.cl/app/web/pay.php?token=FLOW-TOKEN",
            fetch_redirect_response=False,
        )

    @patch("apps.checkout.views.create_payment")
    def test_checkout_fails_if_stock_changed(self, create_payment):
        variant = ProductVariant.objects.create(product=self.product, size="42", stock=1, is_active=True)
        self.client.login(username="checkout-user", password="pass12345")
        session = self.client.session
        session["cart"] = {
            f"{self.product.id}-{variant.id}": {
                "quantity": 2,
                "price": "150000",
                "product_id": self.product.id,
                "variant_id": variant.id,
            }
        }
        session.save()

        response = self.client.post(
            reverse("checkout:index"),
            {
                "full_name": "Checkout User",
                "email": "checkout@example.com",
                "address": "Calle Checkout 123",
                "city": "Santiago",
                "postal_code": "7500000",
                "confirm_checkout": "on",
            },
        )

        self.assertRedirects(response, reverse("cart:cart_detail"))
        self.assertEqual(Order.objects.count(), 0)
        create_payment.assert_not_called()
