from decimal import Decimal

from django.db import migrations


def seed_xclusiv15(apps, schema_editor):
    PromotionCode = apps.get_model("cart", "PromotionCode")
    PromotionCode.objects.update_or_create(
        code="XCLUSIV15",
        defaults={
            "description": "15% OFF newsletter",
            "discount_type": "percent",
            "discount_value": Decimal("15"),
            "is_active": True,
        },
    )


def unseed_xclusiv15(apps, schema_editor):
    PromotionCode = apps.get_model("cart", "PromotionCode")
    PromotionCode.objects.filter(code="XCLUSIV15", used_count=0).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("cart", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_xclusiv15, unseed_xclusiv15),
    ]
