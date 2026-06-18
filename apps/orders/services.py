import logging

from django.db import transaction
from django.db.models import F

from apps.cart.cart import Cart
from apps.cart.models import PromotionCode
from apps.cart.tax import calculate_tax_breakdown
from apps.catalog.models import ProductVariant
from apps.notifications.services import (
    send_admin_new_order_email,
    send_order_cancelled_email,
    send_order_created_email,
    send_payment_confirmed_email,
)

from .models import Order, OrderItem

logger = logging.getLogger(__name__)


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
    order.subtotal_amount = cart.get_subtotal_price()
    order.discount_amount = cart.get_discount_amount()
    order.promo_code = cart.get_promo_code() or ""
    order.total_amount = cart.get_total_price()
    tax = calculate_tax_breakdown(order.total_amount)
    order.net_amount = tax["net"]
    order.tax_amount = tax["tax"]
    order.tax_rate = 19
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
    with transaction.atomic():
        order = Order.objects.select_for_update().prefetch_related("items__variant").get(pk=order.pk)
        update_fields = ["status", "payment_status", "is_paid", "updated_at"]
        order.status = "paid"
        order.payment_status = "paid"
        order.is_paid = True
        if payment_id:
            order.payment_id = payment_id
            update_fields.append("payment_id")
        order.save(update_fields=update_fields)
        commit_order_stock(order)
        commit_order_promotion(order)
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


def validate_cart_stock(cart):
    errors = []
    for item in cart:
        product = item["product"]
        variant = item["variant"]
        quantity = item["quantity"]
        active_variants_exist = product.variants.filter(is_active=True).exists()
        if active_variants_exist and variant is None:
            errors.append(f"{product.name}: selecciona una talla disponible.")
            continue
        if variant is None:
            continue
        if not variant.is_active:
            errors.append(f"{product.name} talla {variant.size_display}: esta talla no esta disponible.")
        elif variant.stock <= 0:
            errors.append(f"{product.name} talla {variant.size_display}: esta talla esta sin stock.")
        elif quantity > variant.stock:
            errors.append(f"{product.name} talla {variant.size_display}: solo quedan {variant.stock} unidades disponibles.")
    return errors


def commit_order_stock(order):
    if order.stock_committed:
        return order

    items = list(order.items.select_related("variant", "product"))
    variant_ids = [item.variant_id for item in items if item.variant_id]
    locked_variants = {
        variant.id: variant
        for variant in ProductVariant.objects.select_for_update().filter(id__in=variant_ids)
    }

    for item in items:
        if not item.variant_id:
            continue
        variant = locked_variants.get(item.variant_id)
        if variant is None:
            raise ValueError(f"Variante no encontrada para item {item.id}.")
        if variant.stock < item.quantity:
            logger.error(
                "Insufficient stock while committing order %s variant %s requested=%s available=%s",
                order.id,
                variant.id,
                item.quantity,
                variant.stock,
            )
            raise ValueError(f"Stock insuficiente para {item.product.name} talla {variant.size_display}.")

    for item in items:
        if item.variant_id:
            ProductVariant.objects.filter(id=item.variant_id).update(stock=F("stock") - item.quantity)

    order.stock_committed = True
    order.save(update_fields=["stock_committed", "updated_at"])
    return order


def commit_order_promotion(order):
    if order.promotion_committed or not order.promo_code:
        return order

    promotion = PromotionCode.objects.select_for_update().filter(code=order.promo_code).first()
    if promotion:
        PromotionCode.objects.filter(pk=promotion.pk).update(used_count=F("used_count") + 1)
    order.promotion_committed = True
    order.save(update_fields=["promotion_committed", "updated_at"])
    return order
