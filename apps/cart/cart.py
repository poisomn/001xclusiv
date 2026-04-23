from decimal import Decimal
from django.conf import settings
from apps.catalog.models import Product, ProductVariant

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
        return sum(Decimal(item['price']) * item['quantity'] for item in self.cart.values())

    def clear(self):
        # remove cart from session
        del self.session[settings.CART_SESSION_ID]
        self.save()
