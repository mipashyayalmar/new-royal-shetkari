# payments/upi_service.py
"""
Scan-and-pay with the restaurant's own static UPI QR (PaymentConfig.upi_qr_image).

A static QR gives the restaurant no signal when a guest pays, so the bill
is never marked paid by showing the QR, by the guest scanning it, or by the
guest pressing "I have paid". The only way a UPI payment is recorded here is
record_verified_upi_payment(): a cashier, manager or owner confirms they saw
the money arrive in the account and types the UPI transaction reference
(UTR / transaction ID). The Payment then carries that reference and who
verified it, when.

Automatic confirmation needs a payment provider that reports payments to
the server (the Razorpay integration in payments/razorpay_views.py, with the
restaurant's own keys and webhook secret); a plain PhonePe merchant QR has
no such callback.
"""
import re
from decimal import Decimal

from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Sum
from django.utils import timezone

from orders.models import Payment
from payments.models import UpiPaymentRequest

# Roles allowed to confirm that money arrived. A waiter or captain can show
# the QR, but not mark it received.
VERIFIER_ROLES = ("cashier", "manager", "owner")

# A UPI reference: the 12-digit UTR/RRN, or an app's transaction ID such as
# PhonePe's "T2410081234567890123456". Letters and digits only.
REFERENCE_RE = re.compile(r"^[A-Za-z0-9]{6,35}$")

DEFAULT_INSTRUCTIONS = (
    "Open PhonePe, Google Pay, Paytm or any UPI app and scan this QR.\n"
    "Enter the exact amount shown and complete the payment.\n"
    "Show the 'payment successful' screen to the cashier.\n"
    "Your bill is marked paid only after the cashier confirms the money has been received."
)


def can_verify(user):
    return bool(user and (user.is_superuser or user.role in VERIFIER_ROLES))


def qr_details(config):
    """What the QR panel shows, from the outlet's PaymentConfig."""
    if config is None:
        return {"has_qr": False}
    return {
        "has_qr": bool(config.upi_qr_image),
        "qr_url": config.upi_qr_image.url if config.upi_qr_image else "",
        "upi_id": config.upi_id,
        "payee_name": config.upi_payee_name,
        "instructions": [line for line in (config.upi_instructions or DEFAULT_INSTRUCTIONS).splitlines() if line.strip()],
    }


def read_reference(raw):
    value = re.sub(r"[\s-]+", "", str(raw or "")).upper()
    if not REFERENCE_RE.fullmatch(value):
        raise ValidationError(
            "Enter the UPI transaction reference from the payment (the 12-digit UTR, "
            "or the transaction ID shown in the app): 6 to 35 letters or digits."
        )
    return value


def amount_due(order):
    paid = order.payments.exclude(method="refund").aggregate(t=Sum("amount"))["t"] or Decimal("0.00")
    return max(Decimal("0.00"), order.grand_total - paid)


def start_request(order, amount, user=None):
    """Open (or reuse) a pending request to collect `amount` by QR. Nothing is paid."""
    if order.status not in ("open", "billing"):
        raise ValidationError("This bill is already settled or cancelled.")
    due = amount_due(order)
    if due <= 0:
        raise ValidationError("Nothing is due on this bill.")
    try:
        amount = Decimal(str(amount)).quantize(Decimal("0.01"))
    except Exception:
        raise ValidationError("Enter a valid amount.")
    if amount <= 0:
        raise ValidationError("The amount must be more than zero.")
    if amount > due:
        raise ValidationError(f"Only Rs.{due} is due on this bill.")

    existing = UpiPaymentRequest.objects.filter(order=order, status="pending", amount=amount).first()
    if existing:
        return existing
    return UpiPaymentRequest.objects.create(
        tenant=order.tenant, outlet=order.outlet, order=order, amount=amount, requested_by=user,
    )


def customer_claim(order):
    """A guest pressed "I have paid" on their bill link. Marks the latest
    pending request (opening one for the full balance if none) as claimed,
    so the cashier sees it. Does NOT record a payment or change the bill."""
    req = UpiPaymentRequest.objects.filter(order=order, status="pending").order_by("-created_at").first()
    if req is None:
        req = start_request(order, amount_due(order), user=None)
    if req.customer_claimed_at is None:
        req.customer_claimed_at = timezone.now()
        req.save(update_fields=["customer_claimed_at"])
    return req


def cancel_request(req, user):
    if req.status != "pending":
        raise ValidationError("Only a pending request can be cancelled.")
    req.status = "cancelled"
    req.cancelled_by = user
    req.cancelled_at = timezone.now()
    req.save(update_fields=["status", "cancelled_by", "cancelled_at"])
    return req


def record_verified_upi_payment(order, user, request_id, reference, confirmed):
    """
    Record a QR payment the cashier has checked. Must run inside the caller's
    transaction with `order` locked (pay_order does both). Returns
    process_payment()'s result dict.
    """
    from orders.services.payment_service import process_payment

    if not can_verify(user):
        raise PermissionDenied("Only a cashier, manager or owner can confirm a UPI payment.")
    if confirmed is not True:
        raise ValidationError("Tick the box to confirm you have checked that the money was received.")
    if not request_id:
        raise ValidationError("Show the QR first, then confirm the payment.")
    try:
        req = UpiPaymentRequest.objects.select_for_update().get(
            pk=int(request_id), order=order, tenant=order.tenant, outlet=order.outlet,
        )
    except (UpiPaymentRequest.DoesNotExist, TypeError, ValueError):
        raise ValidationError("That QR payment request was not found for this bill.")
    if req.status != "pending":
        raise ValidationError(f"That QR payment request is already {req.get_status_display().lower()}.")

    reference = read_reference(reference)
    if Payment.objects.filter(reference__iexact=reference).exists():
        raise ValidationError(f"Reference {reference} is already recorded against another payment. Check it again.")

    result = process_payment(order, "upi", req.amount, user, reference=reference)
    now = timezone.now()
    payment = result["payment"]
    payment.verified_by = user
    payment.verified_at = now
    payment.save(update_fields=["verified_by", "verified_at"])

    req.status = "verified"
    req.reference = reference
    req.payment = payment
    req.verified_by = user
    req.verified_at = now
    req.save(update_fields=["status", "reference", "payment", "verified_by", "verified_at"])
    result["upi_request"] = req
    return result


def request_json(req):
    return {
        "id": req.id,
        "order_id": req.order_id,
        "order_number": req.order.display_number,
        "amount": str(req.amount),
        "status": req.status,
        "customer_claimed_at": timezone.localtime(req.customer_claimed_at).strftime("%H:%M") if req.customer_claimed_at else None,
        "created_at": timezone.localtime(req.created_at).strftime("%d %b %H:%M"),
        "reference": req.reference,
        "verified_by": req.verified_by.get_username() if req.verified_by_id else None,
    }

