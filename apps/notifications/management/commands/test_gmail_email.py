from django.core.management.base import BaseCommand, CommandError

from apps.notifications.gmail_service import gmail_credentials_available, send_gmail_message


class Command(BaseCommand):
    help = "Envia un correo de prueba usando Gmail API."

    def add_arguments(self, parser):
        parser.add_argument("--to", required=True, help="Correo destinatario.")

    def handle(self, *args, **options):
        recipient = options["to"]
        if not gmail_credentials_available():
            raise CommandError("Gmail API no esta configurado. Revisa las variables de entorno.")

        html_body = """
        <div style="font-family:Arial,Helvetica,sans-serif;color:#111;">
          <h1 style="font-size:22px;">001xclusiv Gmail API</h1>
          <p>Este es un correo de prueba enviado desde Django usando Gmail API.</p>
        </div>
        """
        sent = send_gmail_message(
            to=recipient,
            subject="Prueba Gmail API - 001xclusiv",
            html_body=html_body,
            text_body="Este es un correo de prueba enviado desde Django usando Gmail API.",
        )
        if not sent:
            raise CommandError("No se pudo enviar el correo de prueba. Revisa los logs.")
        self.stdout.write(self.style.SUCCESS(f"Correo de prueba enviado a {recipient}."))
