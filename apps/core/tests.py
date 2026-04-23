from django.test import TestCase
from django.urls import reverse


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
