import logging

from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from apps.cart.cart import Cart
from apps.orders.models import Order
from apps.orders.services import build_order_from_cart
from apps.payments.flow_service import FlowAPIError, build_payment_url, create_payment
from .forms import CheckoutForm

logger = logging.getLogger(__name__)

CHECKOUT_REASSURANCE = [
    {
        "icon": "bi-truck",
        "title": "Envio gratis",
        "text": "Despacho sin costo adicional en este flujo MVP para mantener la decision simple.",
    },
    {
        "icon": "bi-shield-lock",
        "title": "Datos protegidos",
        "text": "Usamos tu informacion solo para procesar el pedido y mantenerte al tanto de la entrega.",
    },
    {
        "icon": "bi-arrow-repeat",
        "title": "Post-compra claro",
        "text": "Confirmacion, soporte y una ruta mas simple si necesitas resolver talla o seguimiento.",
    },
]


class CheckoutView(View):
    def get_context(self, cart, form):
        return {
            'cart': cart,
            'form': form,
            'checkout_steps': [
                "Informacion de contacto",
                "Direccion de despacho",
                "Revision final",
            ],
            'checkout_reassurance': CHECKOUT_REASSURANCE,
            'seo_title': "Checkout seguro - 001xclusiv",
            'seo_description': "Finaliza tu compra en 001xclusiv con un checkout mas claro, resumen final y confirmacion de pedido.",
            "checkout_total": cart.get_total_price(),
        }

    def get(self, request):
        cart = Cart(request)
        if len(cart) == 0:
            return redirect('cart:cart_detail')

        initial = {}
        if request.user.is_authenticated:
            full_name = " ".join(
                part for part in [request.user.first_name, request.user.last_name] if part
            ).strip()
            initial = {
                "full_name": full_name,
                "email": request.user.email,
            }

        form = CheckoutForm(initial=initial)
        return render(request, 'checkout/checkout.html', self.get_context(cart, form))

    def post(self, request):
        if request.method == "POST":
            logger.info("Checkout POST received user_authenticated=%s", request.user.is_authenticated)
            cart = Cart(request)
            if len(cart) == 0:
                return redirect('cart:cart_detail')

            form = CheckoutForm(request.POST)
            if form.is_valid():
                order = build_order_from_cart(request, form)
                logger.info("Checkout order created order_id=%s", order.id)
                if order.get_total_cost() <= 0:
                    messages.error(request, "El total del pedido es cero o negativo. No se puede proceder al pago.")
                    return render(request, 'checkout/checkout.html', self.get_context(cart, form))
                logger.info("Flow checkout cart total order_id=%s total=%s", order.id, order.get_total_cost())
                try:
                    response = create_payment(order, request)
                    logger.info(
                        "Flow checkout payment response order_id=%s flowOrder=%s",
                        order.id,
                        response.get("flowOrder"),
                    )
                    payment_url = build_payment_url(response)
                    logger.info("Redirecting to Flow payment order_id=%s", order.id)
                    return redirect(payment_url)
                except FlowAPIError as error:
                    logger.warning("Flow payment creation rejected order_id=%s error=%s", order.id, error)
                    messages.error(request, str(error))
                    return render(request, 'checkout/checkout.html', self.get_context(cart, form))
                except Exception:
                    logger.exception("Flow payment creation failed order_id=%s", order.id)
                    messages.error(request, "No pudimos iniciar el pago. Intenta nuevamente.")
                    return render(request, 'checkout/checkout.html', self.get_context(cart, form))
            else:
                logger.info("Checkout form invalid user_authenticated=%s", request.user.is_authenticated)
        # Fallback render if not POST or any other issue
        return render(request, 'checkout/checkout.html', self.get_context(Cart(request), CheckoutForm()))

def checkout_success(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'checkout/success.html', {'order': order})
