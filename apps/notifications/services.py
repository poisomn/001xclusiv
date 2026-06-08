import logging

from django.conf import settings
from django.contrib.staticfiles import finders
from django.template.loader import render_to_string

from .gmail_service import gmail_credentials_available, send_gmail_message
from .qr import generate_order_qr, get_order_absolute_url

logger = logging.getLogger(__name__)


def _order_context(order):
    return {
        "order": order,
        "order_url": get_order_absolute_url(order),
        "brand_name": getattr(settings, "GMAIL_SENDER_NAME", "001xclusiv"),
    }


def _site_context():
    return {
        "brand_name": getattr(settings, "GMAIL_SENDER_NAME", "001xclusiv"),
        "site_url": getattr(settings, "SITE_URL", "").rstrip("/"),
    }


def _load_logo_inline():
    logo_path = finders.find("home/logoByN.webp")
    if not logo_path:
        return None
    try:
        with open(logo_path, "rb") as logo_file:
            return {
                "content": logo_file.read(),
                "mime_type": "image/webp",
                "filename": "001xclusiv-logo.webp",
            }
    except OSError:
        logger.exception("Could not read inline email logo at %s", logo_path)
        return None


def _inline_images(order):
    images = {
        "qr": {
            "content": generate_order_qr(order),
            "mime_type": "image/png",
            "filename": f"order-{order.id}-qr.png",
        }
    }
    logo = _load_logo_inline()
    if logo:
        images["logo"] = logo
    return images


def _mark_email_sent(order, field_name):
    if hasattr(order, field_name):
        setattr(order, field_name, True)
        order.save(update_fields=[field_name, "updated_at"])


def _already_sent(order, field_name):
    return bool(getattr(order, field_name, False))


def _send_order_email(order, *, to, subject, template_name, sent_field):
    if _already_sent(order, sent_field):
        return True

    if not to:
        logger.warning("Email delivery skipped for order %s: empty recipient.", order.id)
        return False

    if not gmail_credentials_available():
        logger.warning("Email delivery skipped for order %s: Gmail API is not configured.", order.id)
        return False

    try:
        inline_images = _inline_images(order)
        context = {
            **_order_context(order),
            "has_logo": "logo" in inline_images,
            "has_qr": "qr" in inline_images,
        }
        html_body = render_to_string(template_name, context)
        text_body = (
            f"{subject}\n\n"
            f"Orden #{order.id}\n"
            f"Estado: {order.get_status_display()}\n"
            f"Total: ${order.get_total_cost()} CLP\n"
            f"Ver pedido: {context['order_url']}\n\n"
            "Gracias por comprar en 001xclusiv."
        )
        sent = send_gmail_message(
            to=to,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
            inline_images=inline_images,
        )
        if sent:
            _mark_email_sent(order, sent_field)
        return sent
    except Exception:
        logger.exception("Could not send notification email for order %s", order.id)
        return False


def send_order_created_email(order):
    return _send_order_email(
        order,
        to=order.email,
        subject=f"Tu pedido #{order.id} fue creado",
        template_name="emails/order_created.html",
        sent_field="order_created_email_sent",
    )


def send_payment_confirmed_email(order):
    return _send_order_email(
        order,
        to=order.email,
        subject=f"Pago confirmado para tu pedido #{order.id}",
        template_name="emails/payment_confirmed.html",
        sent_field="payment_confirmed_email_sent",
    )


def send_order_cancelled_email(order):
    return _send_order_email(
        order,
        to=order.email,
        subject=f"Pedido #{order.id} cancelado",
        template_name="emails/order_cancelled.html",
        sent_field="order_cancelled_email_sent",
    )


def send_admin_new_order_email(order):
    return _send_order_email(
        order,
        to=getattr(settings, "ADMIN_NOTIFICATION_EMAIL", None),
        subject=f"Nuevo pedido #{order.id} en 001xclusiv",
        template_name="emails/admin_new_order.html",
        sent_field="admin_new_order_email_sent",
    )


def send_welcome_email(user):
    if not getattr(user, "email", None):
        logger.warning("Welcome email skipped for user %s: empty recipient.", user.pk)
        return False

    if not gmail_credentials_available():
        logger.warning("Welcome email skipped for user %s: Gmail API is not configured.", user.pk)
        return False

    try:
        context = {
            **_site_context(),
            "user": user,
        }
        html_body = render_to_string("emails/welcome.html", context)
        site_url = context["site_url"] or "https://001xclusiv.cl"
        text_body = (
            "Bienvenido a 001xclusiv\n\n"
            "Tu cuenta ya esta lista. Ahora puedes guardar favoritos, revisar pedidos "
            "y estar atento a nuevos drops.\n\n"
            f"Visita la tienda: {site_url}"
        )
        return send_gmail_message(
            to=user.email,
            subject="Bienvenido a 001xclusiv",
            html_body=html_body,
            text_body=text_body,
        )
    except Exception:
        logger.exception("Could not send welcome email for user %s", user.pk)
        return False


def send_newsletter_discount_email(subscriber):
    if subscriber.welcome_email_sent:
        return True

    if not subscriber.email:
        logger.warning("Newsletter email skipped for subscriber %s: empty recipient.", subscriber.pk)
        return False

    if not gmail_credentials_available():
        logger.warning(
            "Newsletter email skipped for subscriber %s: Gmail API is not configured.",
            subscriber.pk,
        )
        return False

    try:
        context = {
            **_site_context(),
            "subscriber": subscriber,
            "discount_code": subscriber.discount_code,
        }
        html_body = render_to_string("emails/newsletter_discount.html", context)
        site_url = context["site_url"] or "https://001xclusiv.cl"
        text_body = (
            "Tu 15% OFF en 001xclusiv\n\n"
            f"Codigo: {subscriber.discount_code}\n"
            "Gracias por registrarte en novedades. Recibiras lanzamientos, descuentos "
            "y acceso temprano a nuevos drops.\n\n"
            f"Visita la tienda: {site_url}"
        )
        sent = send_gmail_message(
            to=subscriber.email,
            subject="Tu 15% OFF en 001xclusiv",
            html_body=html_body,
            text_body=text_body,
        )
        if sent:
            subscriber.welcome_email_sent = True
            subscriber.save(update_fields=["welcome_email_sent", "updated_at"])
        return sent
    except Exception:
        logger.exception("Could not send newsletter discount email to %s", subscriber.email)
        return False
