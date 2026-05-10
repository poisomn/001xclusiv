import logging
import base64
from email import encoders
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

from django.conf import settings

logger = logging.getLogger(__name__)

GMAIL_SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"


def gmail_credentials_available():
    required_settings = (
        "GOOGLE_CLIENT_ID",
        "GOOGLE_CLIENT_SECRET",
        "GOOGLE_REFRESH_TOKEN",
        "GMAIL_SENDER_EMAIL",
    )
    return all(bool(getattr(settings, name, None)) for name in required_settings)


def get_gmail_service():
    if not gmail_credentials_available():
        logger.warning("Gmail API is not configured; email delivery skipped.")
        return None

    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds = Credentials(
        token=None,
        refresh_token=settings.GOOGLE_REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        scopes=[GMAIL_SEND_SCOPE],
    )
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def _attach_inline_image(message, content_id, image):
    content = image.get("content") if isinstance(image, dict) else image
    mime_type = image.get("mime_type", "image/png") if isinstance(image, dict) else "image/png"
    filename = image.get("filename", f"{content_id}.png") if isinstance(image, dict) else f"{content_id}.png"

    maintype, _, subtype = mime_type.partition("/")
    if maintype == "image" and subtype != "webp":
        part = MIMEImage(content, _subtype=subtype or None)
    else:
        part = MIMEBase(maintype or "application", subtype or "octet-stream")
        part.set_payload(content)
        encoders.encode_base64(part)

    part.add_header("Content-ID", f"<{content_id}>")
    part.add_header("Content-Disposition", "inline", filename=filename)
    message.attach(part)


def build_mime_message(to, subject, html_body, text_body=None, inline_images=None):
    root = MIMEMultipart("related")
    root["From"] = formataddr((settings.GMAIL_SENDER_NAME, settings.GMAIL_SENDER_EMAIL))
    root["To"] = to
    root["Subject"] = subject

    alternative = MIMEMultipart("alternative")
    alternative.attach(MIMEText(text_body or "", "plain", "utf-8"))
    alternative.attach(MIMEText(html_body, "html", "utf-8"))
    root.attach(alternative)

    for content_id, image in (inline_images or {}).items():
        if image:
            _attach_inline_image(root, content_id, image)

    return root


def send_gmail_message(to, subject, html_body, text_body=None, inline_images=None):
    try:
        service = get_gmail_service()
        if service is None:
            return False

        message = build_mime_message(
            to=to,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
            inline_images=inline_images,
        )
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        service.users().messages().send(userId="me", body={"raw": raw}).execute()
        return True
    except Exception:
        logger.exception("Gmail API failed while sending email to %s", to)
        return False
