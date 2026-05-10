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
    mask_secret,
)


def _payment_id_from_status(status):
    return str(status.get("flowOrder") or "")


def _flow_status_code(status):
    if not status:
        return None
    try:
        return int(status.get("status"))
    except (TypeError, ValueError):
        return status.get("status")


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

    payment_status = _flow_status_code(status)
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
    if not (request.GET.get("token") or request.POST.get("token")):
        order_id = request.GET.get("order_id") or request.POST.get("order_id")
        if order_id:
            return redirect("checkout:success", order_id=order_id)
    return payment_return(request)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def payment_return(request):
    print("PAYMENT RETURN START")
    print("USER AUTH:", request.user.is_authenticated)

    token = request.GET.get("token") or request.POST.get("token")
    print("TOKEN PRESENT:", bool(token))
    print("TOKEN LENGTH:", len(token) if token else 0)
    print("TOKEN MASKED:", mask_secret(token))
    if not token:
        return render(request, "payments/error.html", {"message": "Flow no envi\u00f3 token de pago."})

    try:
        status = get_payment_status(token)
    except Exception as e:
        print("FLOW RETURN ERROR:", e.__class__.__name__)
        return render(request, "payments/error.html", {"message": "Error confirmando el pago"})

    order = _apply_flow_status(status, token=token)
    status_code = _flow_status_code(status)
    print("FLOW STATUS CODE:", status_code if status else "NO_STATUS")
    print("FLOW ORDER:", status.get("flowOrder") if status else "NO_FLOW_ORDER")
    print("COMMERCE ORDER:", status.get("commerceOrder") if status else "NO_COMMERCE_ORDER")
    print("ORDER ID:", order.id if order else "NONE")
    print("ORDER PAYMENT STATUS:", order.payment_status if order else "NONE")

    if order is None:
        return render(request, "payments/error.html", {"message": "No encontramos la orden asociada al pago."})

    if status_code == FLOW_PAID:
        mark_order_paid(order)
        Cart(request).clear()
        clear_checkout_order_session(request)
        return render(request, "checkout/success.html", {"order": order})
    elif status_code in FLOW_CANCELLED_STATUSES:
        clear_checkout_order_session(request)
        return render(request, "payments/cancel.html", {"order": order})
    else:
        return render(request, "payments/processing.html", {"order": order})


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
    print("PAYMENT WEBHOOK START")
    if request.content_type == "application/json":
        import json
        params = json.loads(request.body.decode("utf-8"))
    else:
        params = request.POST.dict()

    token = params.get("token")
    print("TOKEN PRESENT:", bool(token))
    print("TOKEN LENGTH:", len(token) if token else 0)
    print("TOKEN MASKED:", mask_secret(token))
    if not token:
        return JsonResponse({"error": "token required"}, status=400)

    try:
        status = get_payment_status(token)
    except Exception as error:
        return JsonResponse({"error": str(error)}, status=400)

    order = _apply_flow_status(status, token=token)
    status_code = _flow_status_code(status)
    print("FLOW STATUS CODE:", status_code if status else "NO_STATUS")
    print("ORDER ID:", order.id if order else "NONE")
    if order is None:
        return JsonResponse({"error": "order not found"}, status=404)

    # evitar reprocesamiento
    if order.payment_status in {"paid", "cancelled"}:
        return JsonResponse({"ok": True})

    if status_code == FLOW_PAID:
        mark_order_paid(order)

    return JsonResponse({"ok": True})
