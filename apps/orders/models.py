from django.conf import settings
from django.db import models

from apps.catalog.models import Product, ProductVariant


class Order(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pendiente"),
        ("paid", "Pagado"),
        ("cancelled", "Cancelado"),
    )
    PAYMENT_STATUS_CHOICES = (
        ("pending", "Pendiente"),
        ("paid", "Pagado"),
        ("cancelled", "Cancelado"),
        ("failed", "Fallido"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="orders",
        null=True,
        blank=True,
    )
    full_name = models.CharField("Nombre completo", max_length=100)
    email = models.EmailField("Email")
    address = models.CharField("Dirección", max_length=250)
    city = models.CharField("Ciudad", max_length=100)
    postal_code = models.CharField("Código Postal", max_length=20)
    total_amount = models.DecimalField("Total", max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    payment_id = models.CharField("Payment ID", max_length=120, blank=True)
    payment_status = models.CharField(
        "Estado de pago",
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default="pending",
    )
    is_paid = models.BooleanField(default=False)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Orden"
        verbose_name_plural = "Ordenes"

    def __str__(self):
        return f"Orden {self.id}"

    def get_total_cost(self):
        if self.total_amount:
            return self.total_amount
        return sum(item.get_cost() for item in self.items.all())

    def recalculate_total_amount(self, save=True):
        self.total_amount = sum(item.get_cost() for item in self.items.all())
        if save:
            self.save(update_fields=["total_amount", "updated_at"])
        return self.total_amount


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name="order_items", on_delete=models.CASCADE)
    variant = models.ForeignKey(
        ProductVariant,
        related_name="order_items",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return str(self.id)

    def get_cost(self):
        return self.price * self.quantity
