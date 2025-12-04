from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from apps.catalog.models import Product, ProductVariant
from .cart import Cart

@require_POST
def cart_add(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    
    variant_id = request.POST.get('variant')
    variant = None
    if variant_id:
        variant = get_object_or_404(ProductVariant, id=variant_id)

    # Simple logic: always add 1 for now, or read from POST
    quantity = int(request.POST.get('quantity', 1))
    
    cart.add(product=product, quantity=quantity, variant=variant)
    
    return redirect('cart:cart_detail')

def cart_remove(request, product_id):
    cart = Cart(request)
    # We might need to handle variant removal too.
    # For now, let's assume we remove by product_id, but the Cart.remove method
    # supports variant_id. If we want to remove a specific variant, we'd need
    # to pass it in the URL or query param.
    # Let's check query param for variant_id
    variant_id = request.GET.get('variant_id')
    
    cart.remove(product_id, variant_id)
    return redirect('cart:cart_detail')

def cart_detail(request):
    cart = Cart(request)
    return render(request, 'cart/detail.html', {'cart': cart})
