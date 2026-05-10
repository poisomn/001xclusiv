from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="CommunityImage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("image_url", models.CharField(max_length=500, verbose_name="URL de imagen")),
                ("instagram_handle", models.CharField(blank=True, max_length=80, verbose_name="Instagram")),
                ("caption", models.CharField(blank=True, max_length=180, verbose_name="Caption")),
                ("is_active", models.BooleanField(default=True, verbose_name="Activa")),
                ("ordering", models.PositiveIntegerField(default=0, verbose_name="Orden")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "Imagen de comunidad",
                "verbose_name_plural": "Imagenes de comunidad",
                "ordering": ["ordering", "-created_at"],
            },
        ),
    ]
