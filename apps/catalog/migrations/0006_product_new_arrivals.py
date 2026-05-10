from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0005_alter_productimage_image_url"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="new_arrival_order",
            field=models.PositiveIntegerField(default=0, verbose_name="Orden en Recien llegados"),
        ),
        migrations.AddField(
            model_name="product",
            name="show_in_new_arrivals",
            field=models.BooleanField(default=False, verbose_name="Mostrar en Recien llegados"),
        ),
    ]
