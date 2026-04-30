from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.orders.models import Order
from apps.payments.flow_service import (
    build_payment_create_params,
    build_payment_url,
    create_payment,
    sign_params,
    validate_signature,
)


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

    @patch("apps.payments.views.get_payment_status")
    def test_payment_return_marks_order_paid(self, get_payment_status):
        self.order.payment_token = "FLOW-TOKEN"
        self.order.save(update_fields=["payment_token"])
        get_payment_status.return_value = {
            "flowOrder": 123456,
            "commerceOrder": str(self.order.id),
            "status": 2,
        }
        session = self.client.session
        session["pending_order_id"] = self.order.id
        session["last_order_id"] = self.order.id
        session["cart"] = {"1": {"quantity": 1, "price": "100000", "product_id": 999, "variant_id": None}}
        session.save()

        response = self.client.get(reverse("payments:return"), {"token": "FLOW-TOKEN"})

        self.order.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.order.status, "paid")
        self.assertEqual(self.order.payment_status, "paid")
        self.assertTrue(self.order.is_paid)

    @patch("apps.payments.views.get_payment_status")
    def test_payment_return_marks_order_cancelled(self, get_payment_status):
        self.order.payment_token = "FLOW-TOKEN"
        self.order.save(update_fields=["payment_token"])
        get_payment_status.return_value = {
            "flowOrder": 123456,
            "commerceOrder": str(self.order.id),
            "status": 3,
        }
        session = self.client.session
        session["pending_order_id"] = self.order.id
        session["last_order_id"] = self.order.id
        session.save()

        response = self.client.get(reverse("payments:return"), {"token": "FLOW-TOKEN"})

        self.order.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.order.status, "cancelled")
        self.assertEqual(self.order.payment_status, "cancelled")

    @patch("apps.payments.views.get_payment_status")
    def test_payment_return_keeps_order_pending(self, get_payment_status):
        get_payment_status.return_value = {
            "flowOrder": 123456,
            "commerceOrder": str(self.order.id),
            "status": 1,
        }

        response = self.client.get(reverse("payments:return"), {"token": "FLOW-TOKEN"})

        self.order.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.order.status, "pending")
        self.assertEqual(self.order.payment_status, "pending")

    def test_payment_success_without_token_does_not_mark_paid(self):
        response = self.client.get(reverse("payments:success"), {"order_id": self.order.id})

        self.order.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.order.status, "pending")

    def test_payment_cancel_without_token_does_not_mark_cancelled(self):
        response = self.client.get(reverse("payments:cancel"))

        self.order.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.order.status, "pending")

    def test_webhook_rejects_invalid_signature(self):
        response = self.client.post(reverse("payments:confirm"), {"token": "FLOW-TOKEN"})

        self.assertEqual(response.status_code, 400)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "pending")

    @override_settings(FLOW_SECRET_KEY="secret-key")
    @patch("apps.payments.views.get_payment_status")
    def test_webhook_updates_order_with_valid_signature(self, get_payment_status):
        self.order.payment_token = "FLOW-TOKEN"
        self.order.save(update_fields=["payment_token"])
        get_payment_status.return_value = {
            "flowOrder": 123456,
            "commerceOrder": str(self.order.id),
            "status": 2,
        }
        payload = {"token": "FLOW-TOKEN"}
        payload["s"] = sign_params(payload)

        response = self.client.post(reverse("payments:confirm"), payload)

        self.order.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.order.payment_status, "paid")


@override_settings(
    FLOW_API_KEY="api-key",
    FLOW_SECRET_KEY="secret-key",
    SITE_URL="https://shop.example.com",
)
class FlowServiceTests(TestCase):
    def setUp(self):
        self.order = Order.objects.create(
            full_name="Shopper",
            email="shopper@example.com",
            address="Calle 123",
            city="Santiago",
            postal_code="7500000",
            total_amount=100000,
        )

    def test_sign_params_uses_alphabetical_concatenation_without_s(self):
        params = {"apiKey": "XXXX", "currency": "CLP", "amount": "5000"}

        signature = sign_params(params)

        self.assertEqual(
            signature,
            "4b2e503d6861d58963c1370b6e4d505d2b0083d34114eea408f1fd48952bb88e",
        )

    def test_validate_signature(self):
        params = {"apiKey": "api-key", "token": "FLOW-TOKEN"}
        params["s"] = sign_params(params)

        self.assertTrue(validate_signature(params))

    def test_build_payment_create_params_matches_flow_required_schema(self):
        params = build_payment_create_params(self.order)

        self.assertEqual(
            set(params),
            {
                "apiKey",
                "commerceOrder",
                "subject",
                "currency",
                "amount",
                "email",
                "urlConfirmation",
                "urlReturn",
            },
        )
        self.assertEqual(params["apiKey"], "api-key")
        self.assertEqual(params["commerceOrder"], str(self.order.id))
        self.assertEqual(params["subject"], f"Orden {self.order.id}")
        self.assertEqual(params["currency"], "CLP")
        self.assertEqual(params["amount"], "100000")
        self.assertEqual(params["email"], "shopper@example.com")
        self.assertEqual(params["urlConfirmation"], "https://shop.example.com/payment/confirm/")
        self.assertEqual(params["urlReturn"], "https://shop.example.com/payment/return/")

    def test_build_payment_url(self):
        self.assertEqual(
            build_payment_url({"url": "https://flow.example/pay", "token": "abc 123"}),
            "https://flow.example/pay?token=abc+123",
        )

    @patch("apps.payments.flow_service._request_json")
    def test_create_payment_persists_flow_payment_data(self, request_json):
        request_json.return_value = {
            "url": "https://flow.example/pay",
            "token": "FLOW-TOKEN",
            "flowOrder": 123456,
        }

        create_payment(self.order)

        self.order.refresh_from_db()
        self.assertEqual(request_json.call_args.args[2]["amount"], "100000")
        self.assertEqual(self.order.payment_id, "123456")
        self.assertEqual(self.order.payment_token, "FLOW-TOKEN")
        self.assertEqual(self.order.payment_status, "pending")
