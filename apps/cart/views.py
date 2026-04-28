from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from apps.catalog.models import Product, ProductVariant
from .cart import Cart

from django.http import JsonResponse
import json


def _format_clp(value):
    return f"${int(value):,} CLP".replace(",", ".")


def _serialize_cart(cart):
    items = []
    for item in cart:
        items.append(
            {
                "product_id": item["product"].id,
                "product_name": item["product"].name,
                "product_slug": item["product"].slug,
                "product_image": item["product"].primary_image_url,
                "variant": item["variant"].size if item["variant"] else None,
                "variant_id": item["variant"].id if item["variant"] else None,
                "quantity": item["quantity"],
                "price": float(item["price"]),
                "price_formatted": _format_clp(item["price"]),
                "total_price": float(item["total_price"]),
                "total_price_formatted": _format_clp(item["total_price"]),
                "remove_url": f"/cart/remove/{item['product'].id}/" + (
                    f"?variant_id={item['variant'].id}" if item["variant"] else ""
                ),
            }
        )

    return {
        "items": items,
        "cart_count": len(cart),
        "subtotal": float(cart.get_total_price()),
        "subtotal_formatted": _format_clp(cart.get_total_price()),
        "is_empty": len(items) == 0,
    }

@require_POST
def cart_add(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    
    # Check if it's a JSON request (AJAX)
    if request.content_type == 'application/json':
        data = json.loads(request.body)
        variant_id = data.get('variant')
        quantity = int(data.get('quantity', 1))
    else:
        variant_id = request.POST.get('variant')
        quantity = int(request.POST.get('quantity', 1))

    variant = None
    if variant_id:
        variant = get_object_or_404(ProductVariant, id=variant_id)

    cart.add(product=product, quantity=quantity, variant=variant)
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json':
        cart_data = _serialize_cart(cart)
        return JsonResponse({
            'success': True,
            'product_name': product.name,
            'product_image': product.primary_image_url,
            'price': float(product.discount_price if product.discount_price else product.price),
            'variant': variant.size if variant else None,
            'quantity': quantity,
            **cart_data,
        })

    return redirect('cart:cart_detail')

def cart_remove(request, product_id):
    cart = Cart(request)
    variant_id = request.GET.get('variant_id')
    
    cart.remove(product_id, variant_id)

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            **_serialize_cart(cart),
        })

    return redirect('cart:cart_detail')


@require_POST
def cart_update(request, product_id):
    cart = Cart(request)
    variant_id = request.POST.get('variant_id')
    quantity = max(1, int(request.POST.get('quantity', 1)))
    product = get_object_or_404(Product, id=product_id)
    variant = None

    if variant_id:
        variant = get_object_or_404(ProductVariant, id=variant_id)

    cart.add(product=product, quantity=quantity, variant=variant, update_quantity=True)

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            **_serialize_cart(cart),
        })

    return redirect('cart:cart_detail')


def cart_summary(request):
    cart = Cart(request)
    return JsonResponse({
        'success': True,
        **_serialize_cart(cart),
    })

def cart_detail(request):
    cart = Cart(request)
    return render(request, 'cart/detail.html', {'cart': cart})
