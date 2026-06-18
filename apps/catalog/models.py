from types import SimpleNamespace

from django.conf import settings
from django.db import models
from django.urls import reverse


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Category(TimeStampedModel):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True)
    image_url = models.URLField("Imagen categoria URL", blank=True)
    image_path = models.CharField(
        "Imagen categoria static",
        max_length=255,
        blank=True,
        help_text="Ruta dentro de static, por ejemplo home/ropa.jpg.",
    )
    image_alt_text = models.CharField("Texto alternativo", max_length=160, blank=True)
    visual_eyebrow = models.CharField("Etiqueta visual", max_length=80, blank=True)
    size_options = models.ManyToManyField(
        "SizeOption",
        related_name="categories",
        blank=True,
        verbose_name="Tallas disponibles",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def visual_image_url(self):
        if self.image_url:
            return self.image_url
        if self.image_path:
            return f"{settings.STATIC_URL}{self.image_path.lstrip('/')}"
        return ""

    @property
    def visual_alt_text(self):
        return self.image_alt_text or self.name


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
    short_description = models.CharField("Descripción corta", max_length=255, blank=True)
    description = models.TextField("Descripción larga", blank=True)
    image_url = models.URLField("Imagen principal", blank=True)

    brand = models.ForeignKey(
        Brand,
        on_delete=models.PROTECT,
        related_name="products",
        null=True,
        blank=True,
    )
    categories = models.ManyToManyField(Category, related_name="products", blank=True)

    price = models.DecimalField("Precio base", max_digits=10, decimal_places=0)
    discount_price = models.DecimalField(
        "Precio oferta",
        max_digits=10,
        decimal_places=0,
        null=True,
        blank=True,
    )

    is_active = models.BooleanField("Publicado", default=True)
    is_featured = models.BooleanField("Destacado", default=False)
    show_in_new_arrivals = models.BooleanField("Mostrar en Recien llegados", default=False)
    new_arrival_order = models.PositiveIntegerField("Orden en Recien llegados", default=0)

    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("catalog:detail", kwargs={"slug": self.slug})

    @property
    def final_price(self):
        return self.discount_price or self.price

    @property
    def placeholder_image_url(self):
        return settings.PRODUCT_IMAGE_PLACEHOLDER_URL

    @property
    def primary_product_image(self):
        return self.images.filter(is_main=True).first() or self.images.order_by("ordering", "id").first()

    @property
    def primary_image_url(self):
        main_image = self.primary_product_image
        if main_image and main_image.image_url:
            return main_image.image_url
        if self.image_url:
            return self.image_url
        return self.placeholder_image_url

    @property
    def secondary_image_url(self):
        ordered_images = list(self.images.order_by("ordering", "id")[:2])
        if len(ordered_images) > 1 and ordered_images[1].image_url:
            return ordered_images[1].image_url
        return ""

    @property
    def gallery_images(self):
        images = list(self.images.order_by("ordering", "id"))
        if images:
            return images
        if self.image_url:
            return [
                SimpleNamespace(
                    image_url=self.image_url,
                    alt_text=self.name,
                    is_main=True,
                    ordering=0,
                    display_url=self.image_url,
                    image=SimpleNamespace(url=self.image_url),
                )
            ]
        return []

    @property
    def purchasable_variants(self):
        return [variant for variant in self.variants.all() if variant.is_active and variant.stock > 0]

    @property
    def single_purchasable_variant(self):
        variants = self.purchasable_variants
        return variants[0] if len(variants) == 1 else None


class ProductImage(TimeStampedModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image_url = models.URLField("URL de imagen")
    alt_text = models.CharField("Texto alternativo", max_length=255, blank=True)
    is_main = models.BooleanField("Imagen principal", default=False)
    ordering = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Imagen de producto"
        verbose_name_plural = "Imágenes de producto"
        ordering = ["ordering"]

    def __str__(self):
        return f"Imagen de {self.product.name}"

    @property
    def display_url(self):
        return self.image_url or self.product.placeholder_image_url

    @property
    def image(self):
        return SimpleNamespace(url=self.display_url)


class SizeOption(TimeStampedModel):
    TYPE_CLOTHING = "clothing"
    TYPE_SHOES = "shoes"
    TYPE_ACCESSORY = "accessory"
    TYPE_OTHER = "other"

    SIZE_TYPE_CHOICES = [
        (TYPE_CLOTHING, "Ropa"),
        (TYPE_SHOES, "Calzado"),
        (TYPE_ACCESSORY, "Accesorio"),
        (TYPE_OTHER, "Otro"),
    ]

    name = models.CharField("Nombre visible", max_length=40)
    code = models.CharField("Codigo", max_length=20, unique=True)
    size_type = models.CharField("Tipo", max_length=20, choices=SIZE_TYPE_CHOICES, default=TYPE_OTHER)
    ordering = models.PositiveIntegerField("Orden", default=0)
    is_active = models.BooleanField("Activa", default=True)

    class Meta:
        verbose_name = "Talla"
        verbose_name_plural = "Tallas"
        ordering = ["size_type", "ordering", "name"]

    def __str__(self):
        return self.name


class ProductVariant(TimeStampedModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    size = models.CharField("Talla", max_length=20)
    stock = models.PositiveIntegerField("Stock", default=0)
    is_active = models.BooleanField("Disponible", default=True)

    class Meta:
        verbose_name = "Variante (talla)"
        verbose_name_plural = "Variantes (tallas)"
        unique_together = ("product", "size")
        ordering = ["product", "size"]

    def __str__(self):
        return f"{self.product.name} - Talla {self.size_display}"

    @property
    def size_display(self):
        if not self.size:
            return ""
        option = SizeOption.objects.filter(code=self.size).only("name").first()
        return option.name if option else self.size


class Wishlist(TimeStampedModel):
    user = models.ForeignKey("auth.User", on_delete=models.CASCADE, related_name="wishlist")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="wishlisted_by")

    class Meta:
        verbose_name = "Lista de deseados"
        verbose_name_plural = "Listas de deseados"
        unique_together = ("user", "product")

    def __str__(self):
        return f"{self.user.username} - {self.product.name}"
