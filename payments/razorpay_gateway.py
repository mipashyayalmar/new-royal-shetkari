# payments/razorpay_gateway.py
"""
Razorpay UPI QR integration — bring-your-own-keys.

Each tenant connects their OWN Razorpay account (own Key ID + Key Secret).
Money settles directly to the restaurant's bank account; Rasova never holds
or routes funds. This keeps Rasova outside RBI's Payment Aggregator
regulatory perimeter — a marketplace/split-payment model is out of scope.

Uses `requests` directly (matches the rest of the app's convention — no SDK
anywhere). The official `razorpay` package's only real value-add, a
webhook-signature helper, is a one-line `hmac.compare_digest` already
replicated here, the same way `orders/api.py`'s aggregator webhook does it.
"""
import hmac
import hashlib
import logging
from datetime import timedelta
from decimal import Decimal

import requests
from django.utils import timezone

logger = logging.getLogger("pos.orders")

RAZORPAY_API_BASE = "https://api.razorpay.com/v1"
QR_EXPIRY_MINUTES = 10
PAYMENT_LINK_EXPIRY_MINUTES = 16


def paise_to_decimal(paise: int) -> Decimal:
    return Decimal(paise) / Decimal(100)


def decimal_to_paise(amount: Decimal) -> int:
    # Never round-trip through float — order.grand_total is already
    # quantized to 2 decimal places, so this is exact.
    return int((amount * 100).to_integral_value())


def create_qr_payment(order, payment_config, requested_amount=None):
    """
    Creates a single-use, fixed-amount UPI QR code for the order.

    Defaults to the order's current remaining balance. Pass requested_amount
    (already validated by the caller against the current remaining balance)
    to quote a smaller amount instead -- e.g. one person's share of a split
    bill. The webhook records whatever Razorpay actually reports as paid for
    this QR, so a smaller quote here correctly results in a partial payment,
    not a full close, of the order.

    Returns the RazorpayQRCode row created to track it.

    Falls back to a Payment Link when the account has no QR Codes API.

    Raises requests.RequestException on network/API failure (a
    RazorpayAPIError when Razorpay itself answered with an error) — callers
    should catch and surface a clean error to the cashier.
    """
    from django.db.models import Sum
    from payments.models import RazorpayQRCode

    paid_total = order.payments.exclude(method="refund").aggregate(
        total=Sum("amount")
    )["total"] or Decimal("0.00")
    remaining = order.grand_total - paid_total
    amount = requested_amount if requested_amount is not None else remaining
    expires_at = timezone.now() + timedelta(minutes=QR_EXPIRY_MINUTES)

    auth = (payment_config.razorpay_key_id, payment_config.razorpay_key_secret)
    notes = {
        "order_id": str(order.id),
        "tenant_id": str(order.tenant_id),
        "outlet_id": str(order.outlet_id),
    }

    response = requests.post(
        f"{RAZORPAY_API_BASE}/payments/qr_codes",
        auth=auth,
        json={
            "type": "upi_qr",
            "usage": "single_use",
            "fixed_amount": True,
            "payment_amount": decimal_to_paise(amount),
            "close_by": int(expires_at.timestamp()),
            "notes": notes,
        },
        timeout=10,
    )
    if _qr_codes_not_enabled(response):
        return _create_payment_link(order, auth, amount, notes)
    raise_for_razorpay_error(response)
    data = response.json()

    return RazorpayQRCode.objects.create(
        tenant=order.tenant,
        outlet=order.outlet,
        order=order,
        qr_code_id=data["id"],
        image_url=data["image_url"],
        quoted_amount=amount,
        status="active",
        expires_at=expires_at,
    )


class RazorpayAPIError(requests.HTTPError):
    """An error Razorpay answered with; str() is Razorpay's own description."""


def raise_for_razorpay_error(response):
    if response.status_code < 400:
        return
    try:
        description = response.json()["error"]["description"]
    except (ValueError, KeyError, TypeError):
        description = f"HTTP {response.status_code}"
    raise RazorpayAPIError(description, response=response)


def _qr_codes_not_enabled(response):
    """
    Razorpay turns the QR Codes API on per account, on request. Until then
    /payments/qr_codes answers 400 "The requested URL was not found on the
    server." -- the same keys still work for Payment Links, which every
    account has, so create_qr_payment falls back to one.
    """
    if response.status_code not in (400, 404):
        return False
    try:
        description = response.json()["error"]["description"]
    except (ValueError, KeyError, TypeError):
        return False
    return "url was not found" in str(description).lower()


def _create_payment_link(order, auth, amount, notes):
    """
    A Razorpay Payment Link for the bill, tracked in the same
    RazorpayQRCode row (qr_code_id holds the plink_ id, image_url the
    short link). The bill screen shows a QR of the link; the guest can pay
    by UPI, card or net banking. Razorpay requires expire_by at least 15
    minutes ahead, so links live a little longer than UPI QRs.
    """
    from payments.models import RazorpayQRCode

    expires_at = timezone.now() + timedelta(minutes=PAYMENT_LINK_EXPIRY_MINUTES)
    response = requests.post(
        f"{RAZORPAY_API_BASE}/payment_links",
        auth=auth,
        json={
            "amount": decimal_to_paise(amount),
            "currency": "INR",
            "accept_partial": False,
            "description": f"{order.tenant.name} bill {order.display_number}"[:255],
            "reference_id": f"o{order.id}-{int(timezone.now().timestamp())}",
            "expire_by": int(expires_at.timestamp()),
            "reminder_enable": False,
            "notes": notes,
        },
        timeout=10,
    )
    raise_for_razorpay_error(response)
    data = response.json()

    return RazorpayQRCode.objects.create(
        tenant=order.tenant,
        outlet=order.outlet,
        order=order,
        qr_code_id=data["id"],
        image_url=data["short_url"],
        quoted_amount=amount,
        status="active",
        expires_at=expires_at,
    )


def is_payment_link(qr):
    return qr.qr_code_id.startswith("plink_")


def qr_image_data_uri(text):
    """A PNG QR of `text` as a data: URI, for the bill screen's <img>."""
    import base64
    import io
    import qrcode

    image = qrcode.make(text, box_size=8, border=2)
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def verify_webhook_signature(body: bytes, signature_header: str, webhook_secret: str) -> bool:
    """
    Mirrors orders/api.py's HMAC verification pattern exactly.
    Razorpay sends the signature in the X-Razorpay-Signature header.
    """
    if not signature_header or not webhook_secret:
        return False
    expected_sig = hmac.new(
        webhook_secret.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected_sig, signature_header)
