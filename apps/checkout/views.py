from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from apps.cart.cart import Cart
from apps.orders.models import Order, OrderItem
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
            order = form.save(commit=False)
            if request.user.is_authenticated:
                order.user = request.user
            order.save()

            for item in cart:
                OrderItem.objects.create(
                    order=order,
                    product=item['product'],
                    variant=item['variant'],
                    price=item['price'],
                    quantity=item['quantity']
                )

            cart.clear()
            return redirect('checkout:success', order_id=order.id)

        return render(request, 'checkout/checkout.html', self.get_context(cart, form))

def checkout_success(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'checkout/success.html', {'order': order})
