from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from unittest.mock import patch

from apps.cart.models import PromotionCode
from apps.orders.models import Order, OrderShippingEvent


User = get_user_model()


class AccountOrderViewsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="owner", password="pass12345")
        self.other_user = User.objects.create_user(username="other", password="pass12345")
        self.order = Order.objects.create(
            user=self.user,
            full_name="Owner User",
            email="owner@example.com",
            address="Calle 123",
            city="Santiago",
            postal_code="7500000",
        )

    def test_order_detail_requires_login(self):
        response = self.client.get(reverse("accounts:order_detail", args=[self.order.id]))
        self.assertEqual(response.status_code, 302)

    def test_user_can_access_own_order_detail(self):
        self.client.login(username="owner", password="pass12345")
        response = self.client.get(reverse("accounts:order_detail", args=[self.order.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Aún sin asignar")

    def test_user_cannot_access_other_user_order_detail(self):
        self.client.login(username="other", password="pass12345")
        response = self.client.get(reverse("accounts:order_detail", args=[self.order.id]))
        self.assertEqual(response.status_code, 404)

    def test_order_detail_shows_customer_shipping_timeline(self):
        self.order.shipping_status = "in_transit"
        self.order.carrier_name = "Chilexpress"
        self.order.tracking_number = "TRACK-001"
        self.order.save()
        OrderShippingEvent.objects.create(
            order=self.order,
            status="in_transit",
            message="Tu pedido va camino a Santiago.",
        )

        self.client.login(username="owner", password="pass12345")
        response = self.client.get(reverse("accounts:order_detail", args=[self.order.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Estado de tu envío")
        self.assertContains(response, "Chilexpress")
        self.assertContains(response, "TRACK-001")
        self.assertContains(response, "Tu pedido va camino a Santiago.")

    def test_user_can_access_own_order_receipt(self):
        self.client.login(username="owner", password="pass12345")
        response = self.client.get(reverse("accounts:order_receipt", args=[self.order.id]))
        self.assertEqual(response.status_code, 200)

    def test_user_cannot_access_other_user_order_receipt(self):
        self.client.login(username="other", password="pass12345")
        response = self.client.get(reverse("accounts:order_receipt", args=[self.order.id]))
        self.assertEqual(response.status_code, 404)


class BackofficeShippingTrackingTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(username="staff", password="pass12345", is_staff=True)
        self.order = Order.objects.create(
            full_name="Shipping Owner",
            email="shipping-owner@example.com",
            address="Calle 123",
            city="Santiago",
            postal_code="7500000",
        )

    def test_staff_sees_shipping_controls_in_order_backoffice(self):
        self.client.login(username="staff", password="pass12345")

        response = self.client.get(reverse("accounts:backoffice_order_detail", args=[self.order.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Seguimiento del envío")
        self.assertContains(response, "Mensaje para cliente")

    def test_staff_can_add_a_customer_visible_shipping_update(self):
        self.client.login(username="staff", password="pass12345")
        occurred_at = timezone.localtime().strftime("%Y-%m-%dT%H:%M")

        response = self.client.post(
            reverse("accounts:backoffice_order_shipping_update", args=[self.order.id]),
            {
                "shipping_status": "in_transit",
                "carrier_name": "Chilexpress",
                "tracking_number": "TRACK-001",
                "estimated_delivery_date": "2026-06-25",
                "event_message": "Tu pedido va en tránsito hacia tu ciudad.",
                "event_occurred_at": occurred_at,
            },
        )

        self.assertRedirects(response, reverse("accounts:backoffice_order_detail", args=[self.order.id]))
        self.order.refresh_from_db()
        self.assertEqual(self.order.shipping_status, "in_transit")
        self.assertEqual(self.order.tracking_number, "TRACK-001")
        self.assertTrue(self.order.shipped_at)
        event = OrderShippingEvent.objects.get(order=self.order)
        self.assertEqual(event.message, "Tu pedido va en tránsito hacia tu ciudad.")


class AccountAuthFlowTests(TestCase):
    def test_login_wrong_password_shows_friendly_error_and_reset_link(self):
        User.objects.create_user(username="loginuser", password="pass12345")

        response = self.client.post(
            reverse("accounts:login"),
            {"username": "loginuser", "password": "wrong-pass"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Usuario o contraseña incorrectos")
        self.assertContains(response, reverse("accounts:password_reset"))

    @patch("apps.accounts.views.send_welcome_email", return_value=False)
    def test_register_redirects_even_when_welcome_email_fails(self, mocked_send):
        response = self.client.post(
            reverse("accounts:register"),
            {
                "username": "newuser",
                "email": "newuser@example.com",
                "password1": "StrongPass12345",
                "password2": "StrongPass12345",
            },
        )

        self.assertRedirects(response, reverse("core:home"))
        self.assertTrue(User.objects.filter(username="newuser").exists())
        mocked_send.assert_called_once()

    @patch("apps.accounts.forms.send_gmail_message", return_value=True)
    @patch("apps.accounts.forms.gmail_credentials_available", return_value=True)
    def test_password_reset_uses_gmail_api(self, mocked_credentials, mocked_send):
        User.objects.create_user(
            username="resetuser",
            email="reset@example.com",
            password="pass12345",
        )

        response = self.client.post(
            reverse("accounts:password_reset"),
            {"email": "reset@example.com"},
        )

        self.assertRedirects(response, reverse("accounts:password_reset_done"))
        mocked_credentials.assert_called_once()
        mocked_send.assert_called_once()
        self.assertEqual(mocked_send.call_args.kwargs["to"], "reset@example.com")


class BackofficeAccessTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username="admin",
            password="pass12345",
            is_staff=True,
            is_superuser=True,
        )
        self.user = User.objects.create_user(username="shopper", password="pass12345")
        self.order = Order.objects.create(
            user=self.user,
            full_name="Shopper User",
            email="shopper@example.com",
            address="Calle 123",
            city="Santiago",
            postal_code="7500000",
        )

    def test_backoffice_requires_admin(self):
        self.client.login(username="shopper", password="pass12345")
        response = self.client.get(reverse("accounts:backoffice_dashboard"))
        self.assertEqual(response.status_code, 302)

    def test_backoffice_promotions_requires_admin(self):
        self.client.login(username="shopper", password="pass12345")
        response = self.client.get(reverse("accounts:backoffice_promotions"))
        self.assertEqual(response.status_code, 302)

    def test_admin_can_access_backoffice_dashboard(self):
        self.client.login(username="admin", password="pass12345")
        response = self.client.get(reverse("accounts:backoffice_dashboard"))
        self.assertEqual(response.status_code, 200)

    def test_admin_can_access_backoffice_promotions(self):
        self.client.login(username="admin", password="pass12345")
        response = self.client.get(reverse("accounts:backoffice_promotions"))
        self.assertEqual(response.status_code, 200)

    def test_admin_can_create_promotion_and_code_is_normalized(self):
        self.client.login(username="admin", password="pass12345")
        response = self.client.post(
            reverse("accounts:backoffice_promotion_create"),
            {
                "code": " drop 10 ",
                "description": "Drop 10",
                "discount_type": PromotionCode.DISCOUNT_PERCENT,
                "discount_value": "10",
                "is_active": "on",
                "minimum_order_amount": "0",
                "max_discount_amount": "",
                "usage_limit": "",
                "notes": "Campana interna",
            },
        )

        promotion = PromotionCode.objects.get(code="DROP10")
        self.assertRedirects(response, reverse("accounts:backoffice_promotion_edit", args=[promotion.id]))
        self.assertEqual(promotion.created_by, self.staff)
        self.assertTrue(promotion.is_active)

    def test_admin_can_access_receipt_from_other_user(self):
        self.client.login(username="admin", password="pass12345")
        response = self.client.get(reverse("accounts:order_receipt", args=[self.order.id]))
        self.assertEqual(response.status_code, 200)

    def test_admin_can_toggle_product_featured_from_backoffice(self):
        from apps.catalog.models import Product

        brandless_product = Product.objects.create(
            name="Jordan Test",
            slug="jordan-test",
            sku="SKU-001",
            price=100000,
        )
        self.client.login(username="admin", password="pass12345")
        response = self.client.post(
            reverse("accounts:backoffice_product_action", args=[brandless_product.id]),
            {"action": "toggle_featured", "next_url": reverse("accounts:backoffice_products")},
        )
        brandless_product.refresh_from_db()
        self.assertRedirects(response, reverse("accounts:backoffice_products"))
        self.assertTrue(brandless_product.is_featured)

    def test_admin_can_mark_order_shipped_from_backoffice(self):
        self.client.login(username="admin", password="pass12345")
        response = self.client.post(
            reverse("accounts:backoffice_order_action", args=[self.order.id]),
            {"action": "mark_paid", "next_url": reverse("accounts:backoffice_orders")},
        )
        self.order.refresh_from_db()
        self.assertRedirects(response, reverse("accounts:backoffice_orders"))
        self.assertEqual(self.order.status, "paid")
