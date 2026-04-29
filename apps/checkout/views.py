from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from apps.cart.cart import Cart
from apps.orders.models import Order
from apps.orders.services import build_order_from_cart
from apps.payments.flow_service import FlowAPIError, build_payment_url, create_payment
from .forms import CheckoutForm

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
        cart = Cart(request)
        if len(cart) == 0:
            return redirect('cart:cart_detail')

        form = CheckoutForm(request.POST)

        if form.is_valid():
            order = build_order_from_cart(request, form)
            try:
                payment = create_payment(order, request=request)
            except FlowAPIError:
                messages.error(request, "No pudimos iniciar el pago. Intenta nuevamente.")
                return render(request, 'checkout/checkout.html', self.get_context(cart, form))
            return redirect(build_payment_url(payment))

        return render(request, 'checkout/checkout.html', self.get_context(cart, form))

def checkout_success(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'checkout/success.html', {'order': order})
