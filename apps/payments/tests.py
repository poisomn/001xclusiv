from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.orders.models import Order


User = get_user_model()


class PaymentViewsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="shopper", password="pass12345")
        self.order = Order.objects.create(
            user=self.user,
            full_name="Shopper",
            email="shopper@example.com",
            address="Calle 123",
            city="Santiago",
            postal_code="7500000",
            total_amount=100000,
        )

    def test_payment_success_marks_order_paid(self):
        session = self.client.session
        session["pending_order_id"] = self.order.id
        session["last_order_id"] = self.order.id
        session["cart"] = {"1": {"quantity": 1, "price": "100000", "product_id": 999, "variant_id": None}}
        session.save()

        response = self.client.get(reverse("payments:success"))

        self.order.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.order.status, "paid")
        self.assertEqual(self.order.payment_status, "paid")
        self.assertTrue(self.order.is_paid)

    def test_payment_cancel_marks_order_cancelled(self):
        session = self.client.session
        session["pending_order_id"] = self.order.id
        session["last_order_id"] = self.order.id
        session.save()

        response = self.client.get(reverse("payments:cancel"))

        self.order.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.order.status, "cancelled")
        self.assertEqual(self.order.payment_status, "cancelled")

    def test_payment_success_accepts_order_id_in_querystring(self):
        response = self.client.get(reverse("payments:success"), {"order_id": self.order.id})

        self.order.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.order.status, "paid")
