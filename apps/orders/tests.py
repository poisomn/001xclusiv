from unittest.mock import patch

from django.test import TestCase

from apps.cart.models import PromotionCode
from apps.catalog.models import Product, ProductVariant
from apps.orders.models import Order, OrderItem
from apps.orders.services import mark_order_cancelled, mark_order_paid


class OrderCommitTests(TestCase):
    def setUp(self):
        self.product = Product.objects.create(
            name="Order Product",
            slug="order-product",
            sku="ORDER-001",
            price=100000,
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            size="42",
            stock=5,
            is_active=True,
        )
        self.promo, _ = PromotionCode.objects.update_or_create(
            code="XCLUSIV15",
            defaults={
                "description": "15% OFF newsletter",
                "discount_type": PromotionCode.DISCOUNT_PERCENT,
                "discount_value": 15,
                "is_active": True,
            },
        )
        self.order = Order.objects.create(
            full_name="Order User",
            email="order@example.com",
            address="Calle 123",
            city="Santiago",
            postal_code="7500000",
            subtotal_amount=200000,
            discount_amount=30000,
            promo_code="XCLUSIV15",
            total_amount=170000,
        )
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            variant=self.variant,
            price=100000,
            quantity=2,
        )

    @patch("apps.orders.services.send_payment_confirmed_email", return_value=True)
    def test_mark_order_paid_commits_stock_once(self, mocked_email):
        mark_order_paid(self.order, payment_id="FLOW-1")
        self.variant.refresh_from_db()
        self.order.refresh_from_db()
        self.promo.refresh_from_db()

        self.assertEqual(self.variant.stock, 3)
        self.assertTrue(self.order.stock_committed)
        self.assertTrue(self.order.promotion_committed)
        self.assertEqual(self.promo.used_count, 1)

        mark_order_paid(self.order, payment_id="FLOW-1")
        self.variant.refresh_from_db()
        self.promo.refresh_from_db()

        self.assertEqual(self.variant.stock, 3)
        self.assertEqual(self.promo.used_count, 1)
        self.assertEqual(mocked_email.call_count, 2)

    @patch("apps.orders.services.send_order_cancelled_email", return_value=True)
    def test_cancelled_order_does_not_commit_promotion(self, mocked_email):
        mark_order_cancelled(self.order, payment_id="FLOW-CANCEL")
        self.order.refresh_from_db()
        self.promo.refresh_from_db()

        self.assertEqual(self.order.payment_status, "cancelled")
        self.assertFalse(self.order.promotion_committed)
        self.assertEqual(self.promo.used_count, 0)
