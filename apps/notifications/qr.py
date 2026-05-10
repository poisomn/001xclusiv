from io import BytesIO

import qrcode
from django.conf import settings
from django.urls import NoReverseMatch, reverse


def get_order_absolute_url(order):
    site_url = getattr(settings, "SITE_URL", "").rstrip("/")
    if not site_url:
        return "/"

    route_candidates = (
        ("accounts:order_detail", [order.id]),
        ("accounts:order_receipt", [order.id]),
        ("accounts:backoffice_order_detail", [order.id]),
    )
    for route_name, args in route_candidates:
        try:
            return f"{site_url}{reverse(route_name, args=args)}"
        except NoReverseMatch:
            continue
    return f"{site_url}/"


def generate_order_qr(order):
    qr = qrcode.QRCode(version=1, box_size=8, border=2)
    qr.add_data(get_order_absolute_url(order))
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()
