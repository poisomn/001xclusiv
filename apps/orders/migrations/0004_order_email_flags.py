from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0003_order_payment_token"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="admin_new_order_email_sent",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="order",
            name="order_cancelled_email_sent",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="order",
            name="order_created_email_sent",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="order",
            name="payment_confirmed_email_sent",
            field=models.BooleanField(default=False),
        ),
    ]
