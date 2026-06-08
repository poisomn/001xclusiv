from django.core.management.base import BaseCommand, CommandError

from apps.orders.models import Order
from apps.payments.flow_service import (
    FlowAPIError,
    get_payment_status,
    get_payment_status_extended,
    mask_secret,
)
from apps.payments.views import _flow_error_info, _flow_status_code


class Command(BaseCommand):
    help = "Inspect a Flow payment status safely without printing full tokens or secrets."

    def add_arguments(self, parser):
        parser.add_argument("--order-id", type=int, help="Local order ID with a stored Flow token.")
        parser.add_argument("--token", help="Flow token to inspect directly.")

    def handle(self, *args, **options):
        order_id = options.get("order_id")
        token = options.get("token")

        if order_id:
            try:
                order = Order.objects.get(id=order_id)
            except Order.DoesNotExist as error:
                raise CommandError(f"Order {order_id} does not exist.") from error
            token = order.payment_token
            self.stdout.write(f"ORDER ID: {order.id}")
            self.stdout.write(f"ORDER PAYMENT STATUS: {order.payment_status}")
            self.stdout.write(f"FLOW ORDER: {order.payment_id or 'NONE'}")

        if not token:
            raise CommandError("Provide --order-id for an order with payment_token or pass --token.")

        self.stdout.write(f"TOKEN PRESENT: {bool(token)}")
        self.stdout.write(f"TOKEN LENGTH: {len(token)}")
        self.stdout.write(f"TOKEN MASKED: {mask_secret(token)}")

        try:
            status = get_payment_status(token)
        except FlowAPIError as error:
            raise CommandError(f"Flow status request failed: {error}") from error

        status_code = _flow_status_code(status)
        self.stdout.write(f"FLOW STATUS CODE: {status_code if status else 'NO_STATUS'}")
        self.stdout.write(f"FLOW ORDER STATUS: {status.get('flowOrder') if status else 'NO_FLOW_ORDER'}")
        self.stdout.write(f"COMMERCE ORDER: {status.get('commerceOrder') if status else 'NO_COMMERCE_ORDER'}")

        try:
            extended_status = get_payment_status_extended(token)
        except FlowAPIError as error:
            self.stdout.write(f"FLOW EXTENDED ERROR: {error.__class__.__name__}")
            return

        error_code, error_message = _flow_error_info(extended_status)
        self.stdout.write(f"FLOW EXTENDED STATUS CODE: {_flow_status_code(extended_status)}")
        self.stdout.write(f"FLOW REJECT CODE: {error_code}")
        self.stdout.write(f"FLOW REJECT MESSAGE: {error_message}")
