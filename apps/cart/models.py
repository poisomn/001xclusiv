from decimal import Decimal

from django.db import models
from django.utils import timezone


class PromotionCode(models.Model):
    DISCOUNT_PERCENT = "percent"
    DISCOUNT_FIXED = "fixed"
    DISCOUNT_TYPE_CHOICES = (
        (DISCOUNT_PERCENT, "Porcentaje"),
        (DISCOUNT_FIXED, "Monto fijo"),
    )

    code = models.CharField(max_length=40, unique=True)
    description = models.CharField(max_length=180, blank=True)
    discount_type = models.CharField(
        max_length=20,
        choices=DISCOUNT_TYPE_CHOICES,
        default=DISCOUNT_PERCENT,
    )
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_until = models.DateTimeField(null=True, blank=True)
    minimum_order_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    max_discount_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    usage_limit = models.PositiveIntegerField(null=True, blank=True)
    used_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Codigo promocional"
        verbose_name_plural = "Codigos promocionales"
        ordering = ["code"]

    def __str__(self):
        return self.code

    def save(self, *args, **kwargs):
        self.code = (self.code or "").strip().upper()
        super().save(*args, **kwargs)

    def is_valid_now(self):
        now = timezone.now()
        if not self.is_active:
            return False
        if self.valid_from and self.valid_from > now:
            return False
        if self.valid_until and self.valid_until < now:
            return False
        if self.usage_limit is not None and self.used_count >= self.usage_limit:
            return False
        return True

    def can_apply_to_amount(self, subtotal):
        subtotal = Decimal(subtotal)
        return self.is_valid_now() and subtotal >= self.minimum_order_amount

    def get_rejection_message(self, subtotal):
        subtotal = Decimal(subtotal)
        now = timezone.now()
        if not self.is_active:
            return "Este codigo promocional no esta activo."
        if self.valid_from and self.valid_from > now:
            return "Este codigo promocional aun no esta disponible."
        if self.valid_until and self.valid_until < now:
            return "Este codigo promocional expiro."
        if self.usage_limit is not None and self.used_count >= self.usage_limit:
            return "Este codigo promocional alcanzo su limite de uso."
        if subtotal < self.minimum_order_amount:
            return f"Este codigo requiere un minimo de ${int(self.minimum_order_amount):,} CLP.".replace(",", ".")
        return ""

    def calculate_discount(self, subtotal):
        subtotal = Decimal(subtotal)
        if subtotal <= 0 or not self.can_apply_to_amount(subtotal):
            return Decimal("0")
        if self.discount_type == self.DISCOUNT_PERCENT:
            discount = subtotal * self.discount_value / Decimal("100")
        else:
            discount = self.discount_value
        if self.max_discount_amount is not None:
            discount = min(discount, self.max_discount_amount)
        return min(discount, subtotal)

    def mark_used(self):
        type(self).objects.filter(pk=self.pk).update(
            used_count=models.F("used_count") + 1,
            updated_at=timezone.now(),
        )
        self.refresh_from_db(fields=["used_count", "updated_at"])
