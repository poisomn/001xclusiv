import hashlib
import hmac
import json
import logging
from decimal import Decimal, ROUND_HALF_UP
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.urls import reverse


FLOW_PRODUCTION_URL = "https://www.flow.cl/api"
FLOW_SANDBOX_URL = "https://sandbox.flow.cl/api"
FLOW_PAYMENT_CREATE_PATH = "/payment/create"
FLOW_PAYMENT_STATUS_PATH = "/payment/getStatus"

FLOW_PAID = 2
FLOW_CANCELLED_STATUSES = {3, 4}

logger = logging.getLogger(__name__)


class FlowAPIError(Exception):
    pass


def _base_url():
    configured_url = getattr(settings, "FLOW_API_URL", "").strip()
    if configured_url:
        return configured_url.rstrip("/")
    if getattr(settings, "FLOW_USE_SANDBOX", True):
        return FLOW_SANDBOX_URL
    return FLOW_PRODUCTION_URL


def _public_base_url(request=None):
    configured_url = getattr(settings, "SITE_URL", "").strip()
    if configured_url:
        return configured_url.rstrip("/")
    if request is not None:
        return request.build_absolute_uri("/").rstrip("/")
    raise FlowAPIError("SITE_URL is required to create Flow callback URLs.")


def _amount(value):
    decimal_value = Decimal(value).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return str(int(decimal_value))


def _clean_params(params):
    return {
        key: str(value)
        for key, value in params.items()
        if value is not None and value != "" and key != "s"
    }


def sign_params(params):
    clean_params = _clean_params(params)
    to_sign = "".join(f"{key}{clean_params[key]}" for key in sorted(clean_params))
    return hmac.new(
        settings.FLOW_SECRET_KEY.encode("utf-8"),
        to_sign.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def validate_signature(params):
    received_signature = params.get("s")
    if not received_signature:
        return False
    return hmac.compare_digest(received_signature, sign_params(params))


def _signed_params(params):
    signed = _clean_params(params)
    signed["s"] = sign_params(signed)
    return signed


def _request_json(path, method, params):
    url = f"{_base_url()}{path}"
    signed_params = _signed_params(params)

    if method == "GET":
        request = Request(f"{url}?{urlencode(signed_params)}", method="GET")
    else:
        body = urlencode(signed_params).encode("utf-8")
        request = Request(
            url,
            data=body,
            method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    try:
        with urlopen(request, timeout=settings.FLOW_API_TIMEOUT) as response:
            payload = response.read().decode("utf-8")
    except HTTPError as error:
        payload = error.read().decode("utf-8")
        raise FlowAPIError(payload) from error
    except URLError as error:
        raise FlowAPIError(str(error)) from error

    try:
        data = json.loads(payload)
    except json.JSONDecodeError as error:
        raise FlowAPIError(payload) from error

    if isinstance(data, dict) and data.get("code") is not None and data.get("message"):
        raise FlowAPIError(data["message"])
    return data


def build_payment_url(pay_response):
    return f"{pay_response['url']}?{urlencode({'token': pay_response['token']})}"


def build_payment_create_params(order, request=None):
    base_url = _public_base_url(request)
    return {
        "apiKey": settings.FLOW_API_KEY,
        "commerceOrder": str(order.id),
        "subject": f"Orden {order.id}",
        "currency": "CLP",
        "amount": _amount(order.get_total_cost()),
        "email": order.email,
        "urlConfirmation": f"{base_url}{reverse('payments:confirm')}",
        "urlReturn": f"{base_url}{reverse('payments:return')}",
    }


def create_payment(order, request=None):
    params = build_payment_create_params(order, request=request)
    logger.info("Flow create payment amount order_id=%s amount=%s", order.id, params["amount"])
    response = _request_json(
        FLOW_PAYMENT_CREATE_PATH,
        "POST",
        params,
    )
    flow_order = response.get("flowOrder")
    token = response.get("token")
    order.payment_id = str(flow_order or "")
    order.payment_token = str(token or "")
    order.payment_status = "pending"
    order.save(update_fields=["payment_id", "payment_token", "payment_status", "updated_at"])
    return response


def get_payment_status(token):
    return _request_json(
        FLOW_PAYMENT_STATUS_PATH,
        "GET",
        {
            "apiKey": settings.FLOW_API_KEY,
            "token": token,
        },
    )
