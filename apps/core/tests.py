from django.test import TestCase
from django.urls import reverse
from unittest.mock import patch

from apps.core.models import NewsletterSubscriber


class CoreInfoPagesTests(TestCase):
    def test_home_page_loads(self):
        response = self.client.get(reverse("core:home"))
        self.assertEqual(response.status_code, 200)

    def test_faq_page_loads(self):
        response = self.client.get(reverse("core:info_page", args=["faq"]))
        self.assertEqual(response.status_code, 200)

    def test_invalid_info_page_returns_404(self):
        response = self.client.get(reverse("core:info_page", args=["missing-page"]))
        self.assertEqual(response.status_code, 404)


class NewsletterSubscribeTests(TestCase):
    def test_invalid_email_returns_400(self):
        response = self.client.post(reverse("core:newsletter_subscribe"), {"email": "correo-malo"})

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["success"])
        self.assertEqual(NewsletterSubscriber.objects.count(), 0)

    @patch("apps.core.views.send_newsletter_discount_email", return_value=False)
    def test_subscribe_saves_email_even_when_email_delivery_fails(self, mocked_send):
        response = self.client.post(reverse("core:newsletter_subscribe"), {"email": " Test@Example.COM "})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        self.assertTrue(NewsletterSubscriber.objects.filter(email="test@example.com").exists())
        mocked_send.assert_called_once()

    @patch("apps.core.views.send_newsletter_discount_email", return_value=True)
    def test_existing_sent_subscriber_is_not_duplicated(self, mocked_send):
        NewsletterSubscriber.objects.create(email="drop@example.com", welcome_email_sent=True)

        response = self.client.post(reverse("core:newsletter_subscribe"), {"email": "drop@example.com"})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        self.assertEqual(NewsletterSubscriber.objects.filter(email="drop@example.com").count(), 1)
        mocked_send.assert_not_called()
