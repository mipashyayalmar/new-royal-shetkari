# payments/urls.py
from django.urls import path

from . import razorpay_views, refund_views, upi_views

urlpatterns = [
    # Paths unchanged from their old orders/urls.py location -- confirmed
    # every template reference (bill.html, order_history.html) and
    # setup/views/core_views.py's reverse('razorpay-webhook') call use
    # {% url %}/reverse() by name, not hardcoded paths, so this move is
    # transparent to the front end.
    path("refunds/pending/", refund_views.pending_refunds_view, name="pending-refunds"),
    path("refund/approve/<int:refund_id>/", refund_views.approve_refund_view, name="approve-refund"),
    path("refund/reject/<int:refund_id>/", refund_views.reject_refund_view, name="reject-refund"),

    path("razorpay/create-qr/<int:order_id>/", razorpay_views.create_razorpay_qr, name="razorpay-create-qr"),
    path("razorpay/qr-status/<str:qr_code_id>/", razorpay_views.razorpay_qr_status, name="razorpay-qr-status"),
    path("api/razorpay/webhook/", razorpay_views.razorpay_webhook, name="razorpay-webhook"),

    # Scan-and-pay with the restaurant's own UPI QR: showing the QR opens a
    # pending request; only a cashier's verified reference records payment
    # (through pay-order). See payments/upi_service.py.
    path("upi/start/<int:order_id>/", upi_views.start_upi_request, name="upi-start"),
    path("upi/request/<int:request_id>/", upi_views.upi_request_status, name="upi-request-status"),
    path("upi/request/<int:request_id>/cancel/", upi_views.cancel_upi_request, name="upi-request-cancel"),
    path("upi/pending/", upi_views.pending_upi_requests, name="upi-pending"),
    path("bill/public/<str:signed_token>/upi-claim/", upi_views.public_upi_claim, name="public-upi-claim"),
]
