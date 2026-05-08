import base64
import json
import logging
from email.message import EmailMessage

from django.conf import settings

logger = logging.getLogger(__name__)


def _get_gmail_service():
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    credentials_payload = getattr(settings, "GMAIL_SERVICE_ACCOUNT_JSON", "").strip()
    delegated_user = getattr(settings, "GMAIL_DELEGATED_USER", "").strip()

    if not credentials_payload or not delegated_user:
        return None

    creds_info = json.loads(credentials_payload)
    credentials = service_account.Credentials.from_service_account_info(
        creds_info,
        scopes=["https://www.googleapis.com/auth/gmail.send"],
    )
    delegated_credentials = credentials.with_subject(delegated_user)
    return build("gmail", "v1", credentials=delegated_credentials, cache_discovery=False)


def send_gmail_message(subject, message, recipient):
    service = _get_gmail_service()
    if service is None:
        return False

    email_message = EmailMessage()
    email_message["To"] = recipient
    email_message["From"] = settings.DEFAULT_FROM_EMAIL
    email_message["Subject"] = subject
    email_message.set_content(message)

    encoded_message = base64.urlsafe_b64encode(email_message.as_bytes()).decode()
    body = {"raw": encoded_message}

    try:
        service.users().messages().send(userId="me", body=body).execute()
        return True
    except Exception:
        logger.exception("No se pudo enviar email por Gmail API")
        return False
