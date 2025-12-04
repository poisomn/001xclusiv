from django.db import models


class TimeStampedModel(models.Model):
    """Base con fechas de creación / actualización."""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Category(TimeStampedModel):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Brand(TimeStampedModel):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Marca"
        verbose_name_plural = "Marcas"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Product(TimeStampedModel):
    name = models.CharField("Nombre", max_length=150)
    slug = models.SlugField(max_length=180, unique=True)
    sku = models.CharField("SKU", max_length=30, unique=True)
    short_description = models.CharField(
        "Descripción corta",
        max_length=255,
        blank=True,
    )
    description = models.TextField("Descripción larga", blank=True)

    brand = models.ForeignKey(
        Brand,
        on_delete=models.PROTECT,
        related_name="products",
        null=True,
        blank=True,
    )
    categories = models.ManyToManyField(
        Category,
        related_name="products",
        blank=True,
    )

    price = models.DecimalField("Precio base", max_digits=10, decimal_places=2)
    discount_price = models.DecimalField(
        "Precio oferta",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )

    is_active = models.BooleanField("Publicado", default=True)
    is_featured = models.BooleanField("Destacado", default=False)

    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def final_price(self):
        """Retorna precio con descuento si existe, si no el normal."""
        return self.discount_price or self.price


class ProductImage(TimeStampedModel):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="images",
    )
    image = models.ImageField(upload_to="products/")
    alt_text = models.CharField("Texto alternativo", max_length=255, blank=True)
    is_main = models.BooleanField("Imagen principal", default=False)
    ordering = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Imagen de producto"
        verbose_name_plural = "Imágenes de producto"
        ordering = ["ordering"]

    def __str__(self):
        return f"Imagen de {self.product.name}"


SHOE_SIZE_CHOICES = [
    ("36", "36"),
    ("37", "37"),
    ("38", "38"),
    ("39", "39"),
    ("40", "40"),
    ("41", "41"),
    ("42", "42"),
    ("43", "43"),
    ("44", "44"),
    ("45", "45"),
    ("46", "46"),
]


class ProductVariant(TimeStampedModel):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="variants",
    )
    size = models.CharField("Talla", max_length=5, choices=SHOE_SIZE_CHOICES)
    stock = models.PositiveIntegerField("Stock", default=0)
    is_active = models.BooleanField("Disponible", default=True)

    class Meta:
        verbose_name = "Variante (talla)"
        verbose_name_plural = "Variantes (tallas)"
        unique_together = ("product", "size")
        ordering = ["product", "size"]

    def __str__(self):
        return f"{self.product.name} - Talla {self.size}"
