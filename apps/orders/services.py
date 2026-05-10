from apps.cart.cart import Cart
from apps.notifications.services import (
    send_admin_new_order_email,
    send_order_cancelled_email,
    send_order_created_email,
    send_payment_confirmed_email,
)

from .models import Order, OrderItem


def store_checkout_order_session(request, order):
    request.session["pending_order_id"] = order.id
    request.session["last_order_id"] = order.id
    request.session.modified = True


def clear_checkout_order_session(request):
    request.session.pop("pending_order_id", None)
    request.session.pop("last_order_id", None)
    request.session.modified = True


def build_order_from_cart(request, form):
    cart = Cart(request)
    order = form.save(commit=False)
    if request.user.is_authenticated:
        order.user = request.user
    order.status = "pending"
    order.payment_status = "pending"
    order.is_paid = False
    order.total_amount = cart.get_total_price()
    order.save()

    order_items = []
    for item in cart:
        order_items.append(
            OrderItem(
                order=order,
                product=item["product"],
                variant=item["variant"],
                price=item["price"],
                quantity=item["quantity"],
            )
        )
    OrderItem.objects.bulk_create(order_items)
    order.recalculate_total_amount()
    store_checkout_order_session(request, order)
    send_order_created_email(order)
    send_admin_new_order_email(order)
    return order


def get_checkout_order_for_request(request):
    order_id = (
        request.GET.get("order_id")
        or request.POST.get("order_id")
        or request.session.get("pending_order_id")
        or request.session.get("last_order_id")
    )
    if not order_id:
        return None
    try:
        return Order.objects.prefetch_related("items__product", "items__variant").get(id=order_id)
    except Order.DoesNotExist:
        return None


def mark_order_paid(order, payment_id=""):
    update_fields = ["status", "payment_status", "is_paid", "updated_at"]
    order.status = "paid"
    order.payment_status = "paid"
    order.is_paid = True
    if payment_id:
        order.payment_id = payment_id
        update_fields.append("payment_id")
    order.save(update_fields=update_fields)
    send_payment_confirmed_email(order)
    return order


def mark_order_cancelled(order, payment_id=""):
    update_fields = ["status", "payment_status", "is_paid", "updated_at"]
    order.status = "cancelled"
    order.payment_status = "cancelled"
    order.is_paid = False
    if payment_id:
        order.payment_id = payment_id
        update_fields.append("payment_id")
    order.save(update_fields=update_fields)
    send_order_cancelled_email(order)
    return order


def send_order_paid_email(order):
    return send_payment_confirmed_email(order)
