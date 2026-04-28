import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create or update the default Render superuser."

    def handle(self, *args, **options):
        user_model = get_user_model()
        username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "admin")
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "Admin123!")
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "admin@example.com")

        user, created = user_model.objects.get_or_create(
            username=username,
            defaults={
                "email": email,
                "is_staff": True,
                "is_superuser": True,
            },
        )

        updated_fields = []

        if user.email != email:
            user.email = email
            updated_fields.append("email")
        if not user.is_staff:
            user.is_staff = True
            updated_fields.append("is_staff")
        if not user.is_superuser:
            user.is_superuser = True
            updated_fields.append("is_superuser")

        user.set_password(password)
        updated_fields.append("password")

        if created:
            user.save()
            self.stdout.write(self.style.SUCCESS(f"Superuser '{username}' created."))
            return

        user.save(update_fields=updated_fields)
        self.stdout.write(self.style.SUCCESS(f"Superuser '{username}' updated."))
