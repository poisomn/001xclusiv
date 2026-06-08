from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from unittest.mock import patch

from apps.orders.models import Order


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

    def test_user_cannot_access_other_user_order_detail(self):
        self.client.login(username="other", password="pass12345")
        response = self.client.get(reverse("accounts:order_detail", args=[self.order.id]))
        self.assertEqual(response.status_code, 404)

    def test_user_can_access_own_order_receipt(self):
        self.client.login(username="owner", password="pass12345")
        response = self.client.get(reverse("accounts:order_receipt", args=[self.order.id]))
        self.assertEqual(response.status_code, 200)

    def test_user_cannot_access_other_user_order_receipt(self):
        self.client.login(username="other", password="pass12345")
        response = self.client.get(reverse("accounts:order_receipt", args=[self.order.id]))
        self.assertEqual(response.status_code, 404)


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

    def test_admin_can_access_backoffice_dashboard(self):
        self.client.login(username="admin", password="pass12345")
        response = self.client.get(reverse("accounts:backoffice_dashboard"))
        self.assertEqual(response.status_code, 200)

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
