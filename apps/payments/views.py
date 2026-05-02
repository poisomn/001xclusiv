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
    print("USER AUTH:", request.user.is_authenticated)
    print("SESSION KEY:", request.session.session_key)

    token = request.GET.get("token") or request.POST.get("token")
    if not token:
        return render(request, "payments/error.html", {"message": "Flow no envi\u00f3 token de pago."})

    try:
        status = get_payment_status(token)
        print("FLOW STATUS:", status)
    except Exception as e:
        print("FLOW RETURN ERROR:", str(e))
        return render(request, "payments/error.html", {"message": "Error confirmando el pago"})

    order = _apply_flow_status(status, token=token)
    print("ORDER:", order.id if order else "NONE")

    if order is None:
        return render(request, "payments/error.html", {"message": "No encontramos la orden asociada al pago."})

    print("FLOW RETURN STATUS:", status.get("status"))
    print("ORDER DB STATUS:", order.payment_status)

    if status.get("status") == FLOW_PAID:
        mark_order_paid(order)
        Cart(request).clear()
        clear_checkout_order_session(request)
        return render(request, "checkout/success.html", {"order": order})
    elif status.get("status") in FLOW_CANCELLED_STATUSES:
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
    except Exception as error:
        return JsonResponse({"error": str(error)}, status=400)

    order = _apply_flow_status(status, token=token)
    if order is None:
        return JsonResponse({"error": "order not found"}, status=404)

    # evitar reprocesamiento
    if order.payment_status in {"paid", "cancelled"}:
        return JsonResponse({"ok": True})

    if status.get("status") == FLOW_PAID:
        mark_order_paid(order)

    return JsonResponse({"ok": True})


