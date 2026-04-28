from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.catalog.models import Product
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

    def test_checkout_creates_pending_order_and_redirects_to_flow(self):
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
        self.assertRedirects(response, "https://www.flow.cl/uri/8A0Kc6cbd", fetch_redirect_response=False)
