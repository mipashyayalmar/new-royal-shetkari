# payments/upi_views.py
"""Scan-and-pay QR screens. See payments/upi_service.py for the rules."""
import json
import logging

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET, require_POST
from django_ratelimit.decorators import ratelimit

from core.decorators import role_required, tenant_required
from core.errors import error_response
from orders.models import Order
from payments import upi_service
from payments.models import UpiPaymentRequest
from setup.models import PaymentConfig

logger = logging.getLogger("pos.orders")

STAFF_ROLES = ("owner", "manager", "cashier", "captain", "waiter")


def _config(user):
    return PaymentConfig.objects.filter(tenant=user.tenant, outlet=user.outlet).first()


@login_required
@tenant_required
@require_POST
@role_required(*STAFF_ROLES)
@ratelimit(key="user", rate="30/m", method="POST", block=True)
def start_upi_request(request, order_id):
    """Show the QR for an amount. Creates a pending request; pays nothing."""
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    config = _config(request.user)
    if not config or not config.upi_enabled:
        return JsonResponse({"error": "UPI is not enabled for this outlet."}, status=400)
    try:
        with transaction.atomic():
            order = Order.objects.select_for_update().get(
                id=order_id, tenant=request.user.tenant, outlet=request.user.outlet,
            )
            req = upi_service.start_request(order, data.get("amount"), request.user)
    except Order.DoesNotExist:
        return JsonResponse({"error": "Order not found"}, status=404)
    except ValidationError as e:
        return error_response(e, 400)
    return JsonResponse({
        "success": True,
        "request": upi_service.request_json(req),
        "qr": upi_service.qr_details(config),
        "can_verify": upi_service.can_verify(request.user),
    })


@login_required
@tenant_required
@require_GET
@role_required(*STAFF_ROLES)
def upi_request_status(request, request_id):
    req = get_object_or_404(
        UpiPaymentRequest.objects.select_related("order", "verified_by"),
        id=request_id, tenant=request.user.tenant, outlet=request.user.outlet,
    )
    return JsonResponse({"success": True, "request": upi_service.request_json(req)})


@login_required
@tenant_required
@require_POST
@role_required(*STAFF_ROLES)
def cancel_upi_request(request, request_id):
    with transaction.atomic():
        req = get_object_or_404(
            UpiPaymentRequest.objects.select_for_update(),
            id=request_id, tenant=request.user.tenant, outlet=request.user.outlet,
        )
        try:
            upi_service.cancel_request(req, request.user)
        except ValidationError as e:
            return error_response(e, 400)
    return JsonResponse({"success": True})


@login_required
@tenant_required
@role_required("owner", "manager", "cashier")
def pending_upi_requests(request):
    """Cashier's list of QR payments waiting to be checked, and recent ones."""
    base = (UpiPaymentRequest.objects
            .filter(tenant=request.user.tenant, outlet=request.user.outlet)
            .select_related("order", "order__table", "requested_by", "verified_by", "payment"))
    return render(request, "payments/upi_pending.html", {
        "pending": base.filter(status="pending", order__status__in=["open", "billing"])[:100],
        "recent": base.exclude(status="pending")[:50],
    })


@require_POST
@ratelimit(key="ip", rate="6/m", method="POST", block=True)
def public_upi_claim(request, signed_token):
    """Guest pressed "I have paid" on their bill link: flag it for the cashier.
    Never records a payment."""
    from orders.views.public_views import PUBLIC_BILL_MAX_AGE, PUBLIC_BILL_SALT
    try:
        order_id = TimestampSigner(salt=PUBLIC_BILL_SALT).unsign(signed_token, max_age=PUBLIC_BILL_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return JsonResponse({"error": "This bill link has expired."}, status=400)
    try:
        with transaction.atomic():
            order = Order.objects.select_for_update().get(id=order_id)
            if order.status not in ("open", "billing"):
                return JsonResponse({"success": True, "message": "This bill is already settled."})
            upi_service.customer_claim(order)
    except Order.DoesNotExist:
        return JsonResponse({"error": "Bill not found"}, status=404)
    except ValidationError as e:
        return error_response(e, 400)
    return JsonResponse({
        "success": True,
        "message": "Thank you. The cashier will confirm once the payment shows in the restaurant's account. "
                   "Your bill stays unpaid until then.",
    })
