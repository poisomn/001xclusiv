from django.contrib import messages
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
        "subtotal": float(cart.get_subtotal_price()),
        "subtotal_formatted": _format_clp(cart.get_total_price()),
        "raw_subtotal_formatted": _format_clp(cart.get_subtotal_price()),
        "discount_amount": float(cart.get_discount_amount()),
        "discount_amount_formatted": _format_clp(cart.get_discount_amount()),
        "promo_code": cart.get_promo_code(),
        "total": float(cart.get_total_price()),
        "total_formatted": _format_clp(cart.get_total_price()),
        "is_empty": len(items) == 0,
    }


def _is_ajax(request):
    return request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json'


def _cart_error_response(request, message, redirect_to="cart:cart_detail"):
    if _is_ajax(request):
        return JsonResponse({"success": False, "message": message}, status=400)
    messages.error(request, message)
    return redirect(redirect_to)


def _parse_quantity(value, default=1):
    try:
        return max(1, int(value))
    except (TypeError, ValueError):
        return default


def _get_cart_key(product, variant=None):
    return f"{product.id}-{variant.id}" if variant else str(product.id)


def _validate_product_variant(product, variant_id):
    active_variants = product.variants.filter(is_active=True)
    if active_variants.exists() and not variant_id:
        return None, "Selecciona una talla disponible."
    if not variant_id:
        return None, ""
    try:
        variant = ProductVariant.objects.get(id=variant_id, product=product)
    except ProductVariant.DoesNotExist:
        return None, "La talla seleccionada no es valida."
    if not variant.is_active:
        return None, "Esta talla no esta disponible."
    if variant.stock <= 0:
        return None, "Esta talla esta sin stock."
    return variant, ""


def _validate_stock_for_cart(cart, product, variant, quantity, update_quantity=False):
    if not variant:
        return ""
    cart_key = _get_cart_key(product, variant)
    current_quantity = cart.cart.get(cart_key, {}).get("quantity", 0)
    requested_quantity = quantity if update_quantity else current_quantity + quantity
    if requested_quantity > variant.stock:
        return f"Solo quedan {variant.stock} unidades disponibles."
    return ""

@require_POST
def cart_add(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    
    # Check if it's a JSON request (AJAX)
    if request.content_type == 'application/json':
        data = json.loads(request.body)
        variant_id = data.get('variant')
        quantity = _parse_quantity(data.get('quantity', 1))
    else:
        variant_id = request.POST.get('variant')
        quantity = _parse_quantity(request.POST.get('quantity', 1))

    variant, variant_error = _validate_product_variant(product, variant_id)
    if variant_error:
        return _cart_error_response(request, variant_error)
    stock_error = _validate_stock_for_cart(cart, product, variant, quantity)
    if stock_error:
        return _cart_error_response(request, stock_error)

    cart.add(product=product, quantity=quantity, variant=variant)
    
    if _is_ajax(request):
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
    quantity = _parse_quantity(request.POST.get('quantity', 1))
    product = get_object_or_404(Product, id=product_id)
    variant, variant_error = _validate_product_variant(product, variant_id)
    if variant_error:
        return _cart_error_response(request, variant_error)
    stock_error = _validate_stock_for_cart(cart, product, variant, quantity, update_quantity=True)
    if stock_error:
        return _cart_error_response(request, stock_error)

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


@require_POST
def cart_apply_promo(request):
    cart = Cart(request)
    code = request.POST.get("code", "")
    success, message = cart.apply_promo_code(code)
    if _is_ajax(request):
        status = 200 if success else 400
        return JsonResponse({"success": success, "message": message, **_serialize_cart(cart)}, status=status)
    if success:
        messages.success(request, message)
    else:
        messages.error(request, message)
    return redirect("cart:cart_detail")


@require_POST
def cart_remove_promo(request):
    cart = Cart(request)
    cart.remove_promo_code()
    message = "Codigo promocional quitado."
    if _is_ajax(request):
        return JsonResponse({"success": True, "message": message, **_serialize_cart(cart)})
    messages.success(request, message)
    return redirect("cart:cart_detail")
