from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from apps.cart.cart import Cart
from apps.orders.services import (
    clear_checkout_order_session,
    get_checkout_order_for_request,
    mark_order_cancelled,
    mark_order_paid,
)


def payment_success(request):
    order = get_checkout_order_for_request(request)
    if order is None:
        messages.error(request, "No encontramos un pedido pendiente para confirmar.")
        return redirect("accounts:profile" if request.user.is_authenticated else "core:home")

    if order.status != "paid":
        mark_order_paid(order, payment_id=request.GET.get("payment_id", ""))
    Cart(request).clear()
    clear_checkout_order_session(request)
    return render(request, "checkout/success.html", {"order": order})


def payment_cancel(request):
    order = get_checkout_order_for_request(request)
    if order is not None and order.status == "pending":
        mark_order_cancelled(order, payment_id=request.GET.get("payment_id", ""))
    clear_checkout_order_session(request)
    return render(request, "payments/cancel.html", {"order": order})


@csrf_exempt
@require_http_methods(["POST"])
def payment_webhook_placeholder(request):
    return JsonResponse(
        {
            "ready": True,
            "message": "Webhook placeholder listo para integrar API de pagos.",
        },
        status=202,
    )
