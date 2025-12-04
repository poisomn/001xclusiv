from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from apps.cart.cart import Cart
from apps.orders.models import Order, OrderItem
from .forms import CheckoutForm

class CheckoutView(View):
    def get(self, request):
        cart = Cart(request)
        if len(cart) == 0:
            return redirect('cart:cart_detail')
        
        form = CheckoutForm()
        return render(request, 'checkout/checkout.html', {'cart': cart, 'form': form})

    def post(self, request):
        cart = Cart(request)
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
            
        return render(request, 'checkout/checkout.html', {'cart': cart, 'form': form})

def checkout_success(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'checkout/success.html', {'order': order})
