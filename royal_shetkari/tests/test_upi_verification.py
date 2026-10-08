"""
Scan-and-pay QR (payments/upi_service.py): a bill paid by the restaurant's
static UPI QR stays unpaid until a cashier, manager or owner confirms the
money arrived and records the transaction reference.

Run: python manage.py test royal_shetkari
"""
import hashlib
import json
import tempfile
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings

from accounts.models import User
from menu.models import MenuCategory, MenuItem
from orders.models import Order, OrderItem, Payment, Table
from orders.views.public_views import make_public_bill_token
from payments.models import UpiPaymentRequest
from royal_shetkari.seed.seeder import QR_FILE
from setup.models import PaymentConfig
from shifts.models import CashSession
from tenants.models import Outlet, Tenant


def make_restaurant(name):
    tenant = Tenant.objects.create(name=name)
    outlet = Outlet.objects.create(tenant=tenant, name=f"{name} Main")
    users = {role: User.objects.create_user(username=f"{name[:4].lower()}_{role}", password="pw-12345",
                                            tenant=tenant, outlet=outlet, role=role)
             for role in ("owner", "manager", "cashier", "captain", "waiter")}
    cat = MenuCategory.objects.create(tenant=tenant, outlet=outlet, name="Mains")
    dish = MenuItem.objects.create(tenant=tenant, outlet=outlet, category=cat, name="Misal Pav",
                                   price=Decimal("250"), gst_percentage=Decimal("5"))
    table = Table.objects.create(tenant=tenant, outlet=outlet, name="T1")
    order = Order.objects.create(tenant=tenant, outlet=outlet, table=table, created_by=users["waiter"], status="billing")
    OrderItem.objects.create(order=order, menu_item=dish, quantity=2, price=dish.price,
                             gst_percentage=dish.gst_percentage, total_price=dish.price * 2, status="served")
    order.recalculate_totals()
    PaymentConfig.objects.create(tenant=tenant, outlet=outlet, cash_enabled=True, upi_enabled=True,
                                 upi_id="shop@ybl", upi_payee_name="SHOP OWNER")
    CashSession.objects.create(tenant=tenant, outlet=outlet, opened_by=users["cashier"], status="open")
    return tenant, outlet, users, order


TEMP_MEDIA = tempfile.mkdtemp(prefix="rs_test_media_")


def client_for(user):
    c = Client()
    c.force_login(user)
    return c


def post(client, url, body):
    return client.post(url, data=json.dumps(body), content_type="application/json")


@override_settings(RATELIMIT_ENABLE=False, MEDIA_ROOT=TEMP_MEDIA)
class UpiVerificationTests(TestCase):
    def setUp(self):
        self.tenant, self.outlet, self.users, self.order = make_restaurant("Royal")
        self.total = self.order.grand_total   # 500.00: no GSTIN, so no GST
        self.cashier = client_for(self.users["cashier"])

    def start(self, client=None, amount=None):
        return post(client or self.cashier, f"/upi/start/{self.order.id}/", {"amount": str(amount or self.total)})

    def pay(self, client, request_id, reference="427812345678", confirm=True):
        return post(client, f"/pay/{self.order.id}/", {
            "method": "upi", "amount": str(self.total), "upi_request_id": request_id,
            "reference": reference, "confirm_received": confirm,
        })

    def assertUnpaid(self):
        self.order.refresh_from_db()
        self.assertIn(self.order.status, ("open", "billing"))
        self.assertFalse(Payment.objects.filter(order=self.order).exists())

    def test_showing_the_qr_records_nothing(self):
        r = self.start()
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["request"]["status"], "pending")
        self.assertEqual(Decimal(data["request"]["amount"]), self.total)
        self.assertEqual(data["request"]["order_number"], self.order.display_number)
        self.assertTrue(data["can_verify"])
        self.assertUnpaid()

    def test_upi_without_verification_is_refused(self):
        r = post(self.cashier, f"/pay/{self.order.id}/", {"method": "upi", "amount": str(self.total)})
        self.assertEqual(r.status_code, 400)
        self.assertUnpaid()

    def test_guest_saying_paid_does_not_pay(self):
        req_id = self.start().json()["request"]["id"]
        token = make_public_bill_token(self.order.id)
        r = Client().post(f"/bill/public/{token}/upi-claim/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("stays unpaid", r.json()["message"])
        req = UpiPaymentRequest.objects.get(id=req_id)
        self.assertIsNotNone(req.customer_claimed_at)
        self.assertEqual(req.status, "pending")
        self.assertUnpaid()

    def test_public_bill_shows_qr_while_unpaid(self):
        cfg = PaymentConfig.objects.get(outlet=self.outlet)
        cfg.upi_qr_image = SimpleUploadedFile("qr.jpg", QR_FILE.read_bytes(), content_type="image/jpeg")
        cfg.save()
        token = make_public_bill_token(self.order.id)
        page = Client().get(f"/bill/public/{token}/")
        self.assertContains(page, cfg.upi_qr_image.url)
        self.assertContains(page, "I have paid")
        self.assertUnpaid()

    def test_waiter_and_captain_cannot_confirm(self):
        req_id = self.start().json()["request"]["id"]
        for role in ("waiter", "captain"):
            r = self.pay(client_for(self.users[role]), req_id)
            self.assertEqual(r.status_code, 403, role)
        self.assertUnpaid()

    def test_confirmation_tick_and_valid_reference_required(self):
        req_id = self.start().json()["request"]["id"]
        self.assertEqual(self.pay(self.cashier, req_id, confirm=False).status_code, 400)
        self.assertEqual(self.pay(self.cashier, req_id, reference="12").status_code, 400)
        self.assertEqual(self.pay(self.cashier, req_id, reference="ABC 12;DROP").status_code, 400)
        self.assertUnpaid()

    def test_cashier_verification_records_payment_with_reference_and_verifier(self):
        req_id = self.start().json()["request"]["id"]
        r = self.pay(self.cashier, req_id, reference="4278 1234 5678")
        self.assertEqual(r.status_code, 200, r.content)
        payment = Payment.objects.get(order=self.order)
        self.assertEqual(payment.method, "upi")
        self.assertEqual(payment.amount, self.total)
        self.assertEqual(payment.reference, "427812345678")
        self.assertEqual(payment.verified_by, self.users["cashier"])
        self.assertIsNotNone(payment.verified_at)
        self.assertFalse(payment.is_demo)
        req = UpiPaymentRequest.objects.get(id=req_id)
        self.assertEqual((req.status, req.payment_id, req.verified_by_id), ("verified", payment.id, self.users["cashier"].id))
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "closed")
        event = self.order.events.filter(event_type="payment_added").latest("id")
        self.assertTrue(event.metadata["upi_verified"])

    def test_reference_cannot_be_used_twice(self):
        _, _, _, other_order = make_restaurant("Second")
        Payment.objects.create(order=other_order, method="upi", amount=Decimal("10"), reference="427812345678")
        req_id = self.start().json()["request"]["id"]
        r = self.pay(self.cashier, req_id)
        self.assertEqual(r.status_code, 400)
        self.assertIn("already recorded", r.json()["error"])
        self.assertUnpaid()

    def test_partial_qr_payment_then_cash(self):
        req_id = self.start(amount="200.00").json()["request"]["id"]
        r = post(self.cashier, f"/pay/{self.order.id}/", {
            "method": "upi", "amount": "999", "upi_request_id": req_id,
            "reference": "T2410081234567890", "confirm_received": True})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["remaining"], float(self.total - 200))
        self.assertEqual(Payment.objects.get(order=self.order).amount, Decimal("200.00"))
        r = post(self.cashier, f"/pay/{self.order.id}/", {"method": "cash", "amount": str(self.total - 200)})
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "closed")

    def test_amount_above_balance_refused(self):
        r = self.start(amount=self.total + 1)
        self.assertEqual(r.status_code, 400)

    def test_split_pay_by_upi_refused(self):
        r = post(self.cashier, f"/split-pay/{self.order.id}/", {"people": 2, "method": "upi"})
        self.assertEqual(r.status_code, 400)
        self.assertUnpaid()

    def test_other_restaurant_cannot_see_or_verify(self):
        _, _, other_users, _ = make_restaurant("Other")
        req_id = self.start().json()["request"]["id"]
        intruder = client_for(other_users["cashier"])
        self.assertEqual(intruder.get(f"/upi/request/{req_id}/").status_code, 404)
        self.assertEqual(post(intruder, f"/upi/start/{self.order.id}/", {"amount": "10"}).status_code, 404)
        self.assertEqual(post(intruder, f"/upi/request/{req_id}/cancel/", {}).status_code, 404)
        self.assertEqual(self.pay(intruder, req_id).status_code, 404)
        self.assertUnpaid()

    def test_cancelled_request_cannot_be_confirmed(self):
        req_id = self.start().json()["request"]["id"]
        self.assertEqual(post(self.cashier, f"/upi/request/{req_id}/cancel/", {}).status_code, 200)
        self.assertEqual(self.pay(self.cashier, req_id).status_code, 400)
        self.assertUnpaid()

    def test_pending_list_page(self):
        cancelled = self.start(amount="100.00").json()["request"]["id"]
        post(self.cashier, f"/upi/request/{cancelled}/cancel/", {})
        verified = self.start(amount="50.00").json()["request"]["id"]
        post(self.cashier, f"/pay/{self.order.id}/", {"method": "upi", "amount": "50", "upi_request_id": verified,
                                                      "reference": "427811112222", "confirm_received": True})
        self.start(amount=self.total - 50)
        page = self.cashier.get("/upi/pending/")
        self.assertContains(page, self.order.display_number)
        self.assertContains(page, "427811112222")
        self.assertContains(page, "(cancelled)")
        self.assertEqual(client_for(self.users["waiter"]).get("/upi/pending/").status_code, 403)


@override_settings(RATELIMIT_ENABLE=False, MEDIA_ROOT=TEMP_MEDIA)
class QrSettingsTests(TestCase):
    def setUp(self):
        self.tenant, self.outlet, self.users, self.order = make_restaurant("Qrset")

    def upload(self, user, content, name="qr.jpg", extra=None):
        data = {"methods": ["cash", "upi"], "upi_id": "shop@ybl", "upi_payee_name": "PRASAD GANESH YELMAR",
                "upi_qr_image": SimpleUploadedFile(name, content, content_type="image/jpeg")}
        data.update(extra or {})
        return client_for(user).post("/setup/payment-methods/", data)

    def test_owner_upload_keeps_exact_bytes(self):
        raw = QR_FILE.read_bytes()
        self.upload(self.users["owner"], raw)
        cfg = PaymentConfig.objects.get(outlet=self.outlet)
        with cfg.upi_qr_image.open("rb") as fh:
            self.assertEqual(hashlib.sha256(fh.read()).hexdigest(), hashlib.sha256(raw).hexdigest())
        self.assertEqual(cfg.upi_payee_name, "PRASAD GANESH YELMAR")

    def test_owner_can_replace_and_remove(self):
        self.upload(self.users["owner"], QR_FILE.read_bytes())
        first = PaymentConfig.objects.get(outlet=self.outlet).upi_qr_image.name
        self.upload(self.users["owner"], QR_FILE.read_bytes(), name="new.jpg")
        cfg = PaymentConfig.objects.get(outlet=self.outlet)
        self.assertNotEqual(cfg.upi_qr_image.name, first)
        client_for(self.users["owner"]).post("/setup/payment-methods/", {"methods": ["upi"], "remove_upi_qr": "on"})
        self.assertFalse(PaymentConfig.objects.get(outlet=self.outlet).upi_qr_image)

    def test_non_image_rejected(self):
        self.upload(self.users["owner"], b"<script>alert(1)</script>", name="qr.jpg")
        self.assertFalse(PaymentConfig.objects.get(outlet=self.outlet).upi_qr_image)

    def test_cashier_cannot_change_qr(self):
        self.upload(self.users["cashier"], QR_FILE.read_bytes())
        self.assertFalse(PaymentConfig.objects.get(outlet=self.outlet).upi_qr_image)
