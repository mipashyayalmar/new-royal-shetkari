"""
WhatsApp receipt by click-to-chat.

Builds the text of a bill receipt and a https://wa.me/ link that opens WhatsApp
with that text, addressed to the guest. Staff check the message and press Send
in WhatsApp themselves: nothing is sent from the server, and no WhatsApp
Business account is needed. (notifications/services/whatsapp_service.py is the
automatic Meta/Twilio path, which needs paid API credentials.)
"""
import re
from decimal import Decimal
from urllib.parse import quote

from django.db.models import Sum
from django.utils import timezone

METHOD_LABELS = {"cash": "Cash", "upi": "UPI", "card": "Card", "swiggy": "Swiggy", "zomato": "Zomato"}


def wa_phone(raw, default_country="91"):
    """Digits WhatsApp expects (country code, no +). '' if it can't be a phone."""
    digits = re.sub(r"\D", "", raw or "")
    if digits.startswith("00"):
        digits = digits[2:]
    if len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    if len(digits) == 10:
        digits = default_country + digits
    return digits if 11 <= len(digits) <= 15 else ""


def _money(value):
    value = Decimal(value or 0).quantize(Decimal("0.01"))
    text = f"{value:,.2f}"
    return "₹" + (text[:-3] if text.endswith(".00") else text)


def receipt_text(order, bill_link=""):
    """Plain-text receipt for WhatsApp (*bold* is WhatsApp formatting)."""
    outlet = order.outlet
    name = outlet.tenant.name if getattr(outlet, "tenant", None) else outlet.name
    when = timezone.localtime(order.closed_at or order.created_at)
    lines = [f"*{name}*"]
    if outlet.address:
        lines.append(outlet.address.strip())
    lines.append("")
    lines.append(f"Bill: *{order.display_number}*")
    lines.append(f"Date: {when:%d %b %Y, %I:%M %p}")
    if order.table:
        lines.append(f"Table: {order.table.name}")
    lines.append("")
    for item in order.items.exclude(status="voided").select_related("menu_item"):
        price = "Free" if item.is_complimentary else _money(item.total_price)
        lines.append(f"{item.quantity} x {item.menu_item.name}  {price}")
    lines.append("")
    lines.append(f"*Total: {_money(order.grand_total)}*")

    payments = order.payments.exclude(method="refund")
    paid = payments.aggregate(total=Sum("amount"))["total"] or Decimal("0")
    if paid:
        methods = sorted({METHOD_LABELS.get(p.method, p.method.title()) for p in payments})
        lines.append(f"Paid: {_money(paid)} ({', '.join(methods)})")
    due = order.grand_total - paid
    if due > 0:
        lines.append(f"Balance due: {_money(due)}")
    elif paid:
        lines.append("Status: PAID. Thank you!")
    if bill_link:
        lines.append("")
        lines.append(f"View your bill: {bill_link}")
    lines.append("")
    footer = "Thank you for visiting us."
    if outlet.whatsapp_no:
        footer += f" WhatsApp us: {outlet.whatsapp_no}"
    lines.append(footer)
    return "\n".join(lines)


def whatsapp_link(phone, text):
    """wa.me link; with no phone WhatsApp asks which chat to send it to."""
    number = wa_phone(phone)
    return f"https://wa.me/{number}?text={quote(text)}" if number else f"https://wa.me/?text={quote(text)}"
