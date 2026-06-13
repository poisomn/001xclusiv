from decimal import Decimal
from django.conf import settings
from apps.catalog.models import Product, ProductVariant
from .models import PromotionCode

class Cart:
    def __init__(self, request):
        """
        Initialize the cart.
        """
        self.session = request.session
        cart = self.session.get(settings.CART_SESSION_ID)
        if not cart:
            # save an empty cart in the session
            cart = self.session[settings.CART_SESSION_ID] = {}
        self.cart = cart
        self.promo_session_key = "cart_promo_code"

    def add(self, product, quantity=1, variant=None, update_quantity=False):
        """
        Add a product to the cart or update its quantity.
        """
        product_id = str(product.id)
        # If we have variants, we might want to store them differently.
        # For simplicity in this MVP, let's key by "product_id-variant_id" if variant exists,
        # or just product_id if not.
        
        if variant:
            cart_key = f"{product_id}-{variant.id}"
        else:
            cart_key = product_id

        if cart_key not in self.cart:
            self.cart[cart_key] = {
                'quantity': 0,
                'price': str(product.final_price),
                'product_id': product.id,
                'variant_id': variant.id if variant else None
            }
        
        if update_quantity:
            self.cart[cart_key]['quantity'] = quantity
        else:
            self.cart[cart_key]['quantity'] += quantity
        
        self.save()

    def save(self):
        # mark the session as "modified" to make sure it gets saved
        self.session.modified = True

    def remove(self, product_id, variant_id=None):
        """
        Remove a product from the cart.
        """
        if variant_id:
            cart_key = f"{product_id}-{variant_id}"
        else:
            cart_key = str(product_id)

        if cart_key in self.cart:
            del self.cart[cart_key]
            self.save()

    def __iter__(self):
        """
        Iterate over the items in the cart and get the products from the database.
        """
        for _, raw_item in self.cart.items():
            item = raw_item.copy()
            item['price'] = Decimal(item['price'])
            item['total_price'] = item['price'] * item['quantity']

            try:
                item['product'] = Product.objects.get(id=item['product_id'])
            except Product.DoesNotExist:
                continue

            if item['variant_id']:
                try:
                    item['variant'] = ProductVariant.objects.get(id=item['variant_id'])
                except ProductVariant.DoesNotExist:
                    item['variant'] = None
            else:
                item['variant'] = None

            yield item

    def __len__(self):
        """
        Count all items in the cart.
        """
        return sum(item['quantity'] for item in self.cart.values())

    def get_total_price(self):
        total = self.get_subtotal_price() - self.get_discount_amount()
        return max(total, Decimal("0"))

    def get_subtotal_price(self):
        return sum(Decimal(item['price']) * item['quantity'] for item in self.cart.values())

    def apply_promo_code(self, code):
        code = (code or "").strip().upper()
        if not code:
            return False, "Ingresa un codigo promocional."
        try:
            promotion = PromotionCode.objects.get(code=code)
        except PromotionCode.DoesNotExist:
            return False, "Codigo promocional no encontrado."

        subtotal = self.get_subtotal_price()
        if not promotion.can_apply_to_amount(subtotal):
            return False, promotion.get_rejection_message(subtotal) or "Este codigo no se puede aplicar."

        self.session[self.promo_session_key] = promotion.code
        self.save()
        return True, f"Codigo aplicado: {promotion.code}"

    def remove_promo_code(self):
        if self.promo_session_key in self.session:
            del self.session[self.promo_session_key]
            self.save()

    def get_promo_code(self):
        return self.session.get(self.promo_session_key, "")

    def get_promotion(self):
        code = self.get_promo_code()
        if not code:
            return None
        try:
            return PromotionCode.objects.get(code=code)
        except PromotionCode.DoesNotExist:
            self.remove_promo_code()
            return None

    def get_discount_amount(self):
        promotion = self.get_promotion()
        if promotion is None:
            return Decimal("0")
        subtotal = self.get_subtotal_price()
        if not promotion.can_apply_to_amount(subtotal):
            return Decimal("0")
        return promotion.calculate_discount(subtotal)

    def clear(self):
        # remove cart from session
        if settings.CART_SESSION_ID in self.session:
            del self.session[settings.CART_SESSION_ID]
        self.remove_promo_code()
        self.save()
