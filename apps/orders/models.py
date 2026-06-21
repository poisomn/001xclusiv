from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.catalog.models import Product, ProductVariant
from apps.cart.tax import calculate_tax_breakdown


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
    SHIPPING_STATUS_CHOICES = (
        ("not_started", "Aún no preparado"),
        ("preparing", "Preparando pedido"),
        ("packed", "Pedido empaquetado"),
        ("ready_to_ship", "Listo para despacho"),
        ("shipped", "Despachado"),
        ("in_transit", "En tránsito"),
        ("out_for_delivery", "En reparto"),
        ("delivered", "Entregado"),
        ("delayed", "Con demora"),
        ("failed_delivery", "Entrega fallida"),
        ("returned", "Devuelto"),
        ("cancelled", "Envío cancelado"),
    )

    SHIPPING_PROGRESS_STATUSES = {
        "not_started": 0,
        "preparing": 1,
        "packed": 1,
        "ready_to_ship": 2,
        "shipped": 3,
        "in_transit": 3,
        "out_for_delivery": 3,
        "delivered": 4,
    }

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
    subtotal_amount = models.DecimalField("Subtotal", max_digits=12, decimal_places=2, default=0)
    discount_amount = models.DecimalField("Descuento", max_digits=12, decimal_places=2, default=0)
    promo_code = models.CharField("Codigo promocional", max_length=40, blank=True)
    net_amount = models.DecimalField("Neto", max_digits=12, decimal_places=2, default=0)
    tax_amount = models.DecimalField("IVA", max_digits=12, decimal_places=2, default=0)
    tax_rate = models.DecimalField("Tasa IVA", max_digits=5, decimal_places=2, default=19)
    total_amount = models.DecimalField("Total", max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    payment_id = models.CharField("Payment ID", max_length=120, blank=True)
    payment_token = models.CharField("Payment Token", max_length=255, blank=True, db_index=True)
    payment_status = models.CharField(
        "Estado de pago",
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default="pending",
    )
    is_paid = models.BooleanField(default=False)
    shipping_status = models.CharField(
        "Estado de envío",
        max_length=20,
        choices=SHIPPING_STATUS_CHOICES,
        default="not_started",
    )
    carrier_name = models.CharField("Transportista", max_length=100, blank=True)
    tracking_number = models.CharField("Número de seguimiento", max_length=100, blank=True)
    estimated_delivery_date = models.DateField("Fecha estimada de entrega", null=True, blank=True)
    shipped_at = models.DateTimeField("Fecha de despacho", null=True, blank=True)
    delivered_at = models.DateTimeField("Fecha de entrega", null=True, blank=True)
    order_created_email_sent = models.BooleanField(default=False)
    payment_confirmed_email_sent = models.BooleanField(default=False)
    order_cancelled_email_sent = models.BooleanField(default=False)
    admin_new_order_email_sent = models.BooleanField(default=False)
    stock_committed = models.BooleanField(default=False)
    promotion_committed = models.BooleanField(default=False)

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
        if not self.subtotal_amount:
            self.subtotal_amount = sum(item.get_cost() for item in self.items.all())
        self.total_amount = max(self.subtotal_amount - self.discount_amount, 0)
        tax = calculate_tax_breakdown(self.total_amount)
        self.net_amount = tax["net"]
        self.tax_amount = tax["tax"]
        self.tax_rate = 19
        if save:
            self.save(update_fields=[
                "subtotal_amount",
                "discount_amount",
                "net_amount",
                "tax_amount",
                "tax_rate",
                "total_amount",
                "updated_at",
            ])
        return self.total_amount

    def get_net_amount(self):
        if self.net_amount:
            return self.net_amount
        return calculate_tax_breakdown(self.get_total_cost())["net"]

    def get_tax_amount(self):
        if self.tax_amount:
            return self.tax_amount
        return calculate_tax_breakdown(self.get_total_cost())["tax"]

    @property
    def shipping_status_tone(self):
        if self.shipping_status == "delivered":
            return "success"
        if self.shipping_status in {"delayed", "failed_delivery", "returned", "cancelled"}:
            return "alert"
        if self.shipping_status in {"shipped", "in_transit", "out_for_delivery"}:
            return "moving"
        return "pending"

    def get_shipping_progress_steps(self):
        current_step = self.SHIPPING_PROGRESS_STATUSES.get(self.shipping_status, 0)
        steps = (
            ("received", "Pedido recibido"),
            ("preparing", "En preparación"),
            ("ready_to_ship", "Listo para despacho"),
            ("in_transit", "En tránsito"),
            ("delivered", "Entregado"),
        )
        return [
            {
                "key": key,
                "label": label,
                "state": "complete" if index < current_step else "active" if index == current_step else "pending",
            }
            for index, (key, label) in enumerate(steps)
        ]

    def record_shipping_event(self, message="", occurred_at=None):
        occurred_at = occurred_at or timezone.now()
        event = OrderShippingEvent.objects.create(
            order=self,
            status=self.shipping_status,
            message=message.strip(),
            occurred_at=occurred_at,
        )

        update_fields = []
        if self.shipping_status in {"shipped", "in_transit", "out_for_delivery", "delivered"} and not self.shipped_at:
            self.shipped_at = occurred_at
            update_fields.append("shipped_at")
        if self.shipping_status == "delivered" and not self.delivered_at:
            self.delivered_at = occurred_at
            update_fields.append("delivered_at")
        if update_fields:
            update_fields.append("updated_at")
            self.save(update_fields=update_fields)
        return event


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


class OrderShippingEvent(models.Model):
    order = models.ForeignKey(Order, related_name="shipping_events", on_delete=models.CASCADE)
    status = models.CharField("Estado de envío", max_length=20, choices=Order.SHIPPING_STATUS_CHOICES)
    message = models.TextField("Mensaje para cliente", max_length=500, blank=True)
    occurred_at = models.DateTimeField("Fecha del evento", default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("occurred_at", "id")
        verbose_name = "Evento de envío"
        verbose_name_plural = "Eventos de envío"

    def __str__(self):
        return f"Pedido #{self.order_id} - {self.get_status_display()}"
