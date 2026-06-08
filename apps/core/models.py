from django.db import models


class CommunityImage(models.Model):
    image_url = models.CharField("URL de imagen", max_length=500)
    instagram_handle = models.CharField("Instagram", max_length=80, blank=True)
    caption = models.CharField("Caption", max_length=180, blank=True)
    is_active = models.BooleanField("Activa", default=True)
    ordering = models.PositiveIntegerField("Orden", default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Imagen de comunidad"
        verbose_name_plural = "Imagenes de comunidad"
        ordering = ["ordering", "-created_at"]

    def __str__(self):
        return self.instagram_handle or self.caption or f"Comunidad #{self.pk}"


class NewsletterSubscriber(models.Model):
    email = models.EmailField(unique=True)
    discount_code = models.CharField(max_length=40, default="XCLUSIV15")
    is_active = models.BooleanField(default=True)
    welcome_email_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Suscriptor newsletter"
        verbose_name_plural = "Suscriptores newsletter"
        ordering = ["-created_at"]

    def __str__(self):
        return self.email
