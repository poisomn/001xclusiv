from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from apps.cart.cart import Cart
from apps.orders.models import Order
from apps.orders.services import (
    clear_checkout_order_session,
    get_checkout_order_for_request,
    mark_order_cancelled,
    mark_order_paid,
)
from apps.payments.flow_service import (
    FLOW_CANCELLED_STATUSES,
    FLOW_PAID,
    FlowAPIError,
    get_payment_status,
    validate_signature,
)


def _payment_id_from_status(status):
    return str(status.get("flowOrder") or "")


def _order_from_token(token):
    if not token:
        return None
    try:
        return Order.objects.prefetch_related("items__product", "items__variant").get(
            payment_token=token
        )
    except Order.DoesNotExist:
        return None


def _order_from_status(status, token=None):
    commerce_order = status.get("commerceOrder")
    if commerce_order:
        try:
            return Order.objects.prefetch_related("items__product", "items__variant").get(
                id=commerce_order
            )
        except (Order.DoesNotExist, ValueError, TypeError):
            pass

    flow_order = status.get("flowOrder")
    if flow_order:
        try:
            return Order.objects.prefetch_related("items__product", "items__variant").get(
                payment_id=str(flow_order)
            )
        except Order.DoesNotExist:
            return None
    return _order_from_token(token)


def _apply_flow_status(status, token=None):
    order = _order_from_status(status, token=token)
    if order is None:
        return None

    payment_status = status.get("status")
    payment_id = _payment_id_from_status(status)

    if payment_status == FLOW_PAID:
        if order.payment_status != "paid":
            mark_order_paid(order, payment_id=payment_id)
    elif payment_status in FLOW_CANCELLED_STATUSES:
        if order.payment_status != "cancelled":
            mark_order_cancelled(order, payment_id=payment_id)
    elif payment_id and order.payment_id != payment_id:
        order.payment_id = payment_id
        order.save(update_fields=["payment_id", "updated_at"])
    elif payment_status not in {FLOW_PAID, *FLOW_CANCELLED_STATUSES} and order.payment_status != "pending":
        order.status = "pending"
        order.payment_status = "pending"
        order.is_paid = False
        order.save(update_fields=["status", "payment_status", "is_paid", "updated_at"])

    return order


def payment_success(request):
    return payment_return(request)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def payment_return(request):
    token = request.GET.get("token")
    if not token:
        messages.error(request, "Flow no envio token de pago.")
        return redirect("accounts:profile" if request.user.is_authenticated else "core:home")

    try:
        status = get_payment_status(token)
        print("FLOW STATUS RESPONSE:", status)
        print("FLOW STATUS CODE:", status.get("status"))
    except FlowAPIError:
        messages.error(request, "No pudimos confirmar el estado del pago.")
        return redirect("accounts:profile" if request.user.is_authenticated else "core:home")

    order = _apply_flow_status(status, token=token)
    if order is None:
        messages.error(request, "No encontramos la orden asociada al pago.")
        return redirect("accounts:profile" if request.user.is_authenticated else "core:home")

    if order.payment_status == "paid":
        Cart(request).clear()
        clear_checkout_order_session(request)
        return render(request, "checkout/success.html", {"order": order})
    else:
        clear_checkout_order_session(request)
        return render(request, "payments/cancel.html", {"order": order})


def payment_cancel(request):
    order = None
    token = request.GET.get("token")
    if token:
        try:
            status = get_payment_status(token)
        except FlowAPIError:
            status = None
        if status:
            order = _apply_flow_status(status, token=token)
    if order is None:
        order = get_checkout_order_for_request(request)
    clear_checkout_order_session(request)
    return render(request, "payments/cancel.html", {"order": order})


@csrf_exempt
@require_http_methods(["POST"])
def payment_webhook(request):
    # Log raw request body
    print("FLOW WEBHOOK RAW BODY:", request.body)
    # Parse parameters based on content type
    if request.content_type == "application/json":
        import json
        params = json.loads(request.body.decode("utf-8"))
    else:
        params = request.POST.dict()
    print("FLOW WEBHOOK PARAMS:", params)
    # signature validation removed (debug)



    token = params.get("token")
    if not token:
        return JsonResponse({"error": "token required"}, status=400)

    try:
        status = get_payment_status(token)
    except FlowAPIError as error:
        return JsonResponse({"error": str(error)}, status=400)

    order = _apply_flow_status(status, token=token)
    if order is None:
        return JsonResponse({"error": "order not found"}, status=404)

    # Ensure order is marked as paid when Flow indicates payment
    if status.get("status") == FLOW_PAID:
        order.payment_status = "paid"
        order.status = "paid"
        order.is_paid = True
        order.save(update_fields=["payment_status", "status", "is_paid"])

    return JsonResponse({"ok": True})


