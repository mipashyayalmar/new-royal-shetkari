"""
Builds the Royal Shetkari demo restaurant. Used by
`python manage.py seed_royal_shetkari` (royal_shetkari/management/commands).

Two parts:

* setup   - restaurant and outlet profile, staff logins, kitchen stations,
            payment settings (PhonePe QR), 12 menu categories x 20 dishes with
            photos and recipes, tables, stock items, suppliers, promos,
            offers, shift templates and pay rates.
* history - 90 days of trading made through the app's own services, so
            every total, KOT, stock movement and report is what the real
            screens would have produced: orders (dine-in, takeaway, Zomato
            and Swiggy), KOTs and kitchen status, bills, cash/UPI/card and
            split payments, discounts, promos, cancellations, refunds,
            loyalty, purchases, cash sessions, shifts, reservations,
            expenses and feedback.

Everything the seed creates is listed in royal_shetkari.DemoRecord. Running
the seed again only adds what is missing; it never edits or deletes a row
that is not on that list, so the restaurant's real data is never touched.
All sample payments are marked is_demo and carry DEMO references; no money
moved and no message was sent to anyone.
"""
import hashlib
import math
import random
import secrets
import string
from collections import defaultdict
from datetime import datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from unittest import mock

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction
from django.db.models import Max, Q, Sum
from django.utils import timezone

from royal_shetkari.models import DemoRecord
from royal_shetkari.seed import inventory_data, menu_data, people

TENANT_NAME = "Royal Shetkari"
TENANT_SLUG = "royal-shetkari"
OUTLET_NAME = "Royal Shetkari - Main Restaurant"

UPI_ID = "9172353945-2@ybl"          # as given by the owner
UPI_PAYEE = "PRASAD GANESH YELMAR"   # name printed on the QR
ASSETS = Path(__file__).resolve().parent.parent / "assets"
QR_FILE = ASSETS / "payment" / "phonepe_qr.jpg"
IMAGES = ASSETS / "menu_images"

TABLE_LAYOUT = [("Family Hall", "F", 10, 4), ("AC Dining", "A", 8, 4), ("Garden", "G", 6, 6)]

POPULAR = {
    "Puneri Misal Pav": 6, "Kolhapuri Misal Pav": 4, "Vada Pav": 6, "Pav Bhaji": 4,
    "Chicken Dum Biryani": 6, "Mutton Dum Biryani": 4, "Butter Chicken": 5, "Kolhapuri Mutton": 4,
    "Paneer Butter Masala": 5, "Dal Tadka": 3, "Butter Naan": 6, "Tandoori Roti": 6,
    "Jeera Rice": 4, "Masala Chai": 5, "Sweet Lassi": 3, "Masala Taak": 3, "Sol Kadhi": 3,
    "Chicken Tikka": 4, "Paneer Tikka": 4, "Surmai Fry": 3, "Gulab Jamun (2 pcs)": 3,
    "Maharashtrian Veg Thali": 4, "Malvani Fish Thali": 3, "Kombdi Vade": 3, "Chicken 65": 3,
}

D = Decimal
TWO = D("0.01")


def q2(x):
    return D(x).quantize(TWO, rounding=ROUND_HALF_UP)


class SeedError(Exception):
    pass


class Clock:
    """Stands in for django.utils.timezone.now while history is written, so
    every auto timestamp (created_at, paid_at, KOT time, stock movement...)
    lands on the simulated moment instead of today."""

    def __init__(self):
        self.t = None
        self._real = timezone.now

    def __call__(self):
        return self.t if self.t is not None else self._real()


class Seeder:
    def __init__(self, out=print, *, rng_seed=2026, days=90, credentials_path=None, allow_existing_tenant=False):
        self.out = out
        self.rng = random.Random(rng_seed)
        self.days = days
        self.credentials_path = Path(credentials_path or (settings.BASE_DIR / "DEMO_LOGINS.txt"))
        self.allow_existing_tenant = allow_existing_tenant
        self._ct = {}
        self._first = {}
        self.created_logins = []
        self.counts = defaultdict(int)
        # Runs as a management command: no request tenant is set, so the
        # TenantManager returns every row and the explicit tenant filters
        # below do the scoping. Refuse to run inside a scoped context.
        from core.tenant_context import get_current_tenant_id
        if get_current_tenant_id() is not None:
            raise SeedError("The Royal Shetkari seed must run as a management command, not inside a request.")

    # ------------------------------------------------------------------
    # demo registry
    # ------------------------------------------------------------------
    def ct(self, model):
        if model not in self._ct:
            self._ct[model] = ContentType.objects.get_for_model(model)
        return self._ct[model]

    def mark(self, obj, kind="setup"):
        DemoRecord.objects.get_or_create(content_type=self.ct(type(obj)), object_id=str(obj.pk),
                                         defaults={"kind": kind})

    def mark_ids(self, model, ids, kind="history"):
        ct = self.ct(model)
        DemoRecord.objects.bulk_create(
            [DemoRecord(content_type=ct, object_id=str(i), kind=kind) for i in ids], ignore_conflicts=True,
        )

    def is_demo(self, obj):
        return DemoRecord.objects.filter(content_type=self.ct(type(obj)), object_id=str(obj.pk)).exists()

    def demo_ids(self, model, kind=None):
        return DemoRecord.ids_for(model, kind)

    def first_time(self, model):
        """True until the seed has created at least one row of this model.
        After that a re-run only reads, so a dish, table or account the owner
        renamed or deleted is never brought back."""
        if model not in self._first:
            self._first[model] = not DemoRecord.objects.filter(content_type=self.ct(model)).exists()
        return self._first[model]

    def get_or_create(self, model, lookup, defaults=None, kind="setup"):
        obj = model.objects.filter(**lookup).first()
        if obj:
            return obj, False
        if not self.first_time(model):
            return None, False
        obj = model.objects.create(**lookup, **(defaults or {}))
        self.mark(obj, kind)
        self.counts[model.__name__] += 1
        return obj, True

    # ------------------------------------------------------------------
    # SETUP
    # ------------------------------------------------------------------
    def find_tenant(self):
        from tenants.models import Tenant
        return Tenant.objects.filter(slug=TENANT_SLUG).first()

    @transaction.atomic
    def run_setup(self):
        from tenants.models import Outlet, Tenant

        tenant = self.find_tenant()
        if tenant and not self.is_demo(tenant) and not self.allow_existing_tenant:
            raise SeedError(
                f"A restaurant with the address '{TENANT_SLUG}' already exists and was not made by this seed. "
                "Nothing was changed. Use --use-existing-restaurant to add the sample data to it anyway."
            )
        if not tenant:
            tenant = Tenant.objects.create(
                name=TENANT_NAME, slug=TENANT_SLUG, tenant_type="fine_dining",
                subscription_status="active", subscription_start_date=timezone.localdate(),
            )
            self.mark(tenant)
        outlet = Outlet.objects.filter(tenant=tenant).order_by("id").first()
        if outlet is None:
            self._first[Outlet] = True
        outlet = outlet or self.get_or_create(Outlet, {"tenant": tenant, "name": OUTLET_NAME}, {
            "address": "SAMPLE ADDRESS - Shetkari Chowk, Pune 411001 (update in Setup > Outlet Settings)",
            "phone": "+91 90000 00000",
            "email": "hello@royalshetkari.example.com",
            "bill_code": "RS",
            "opening_time": time(11, 0), "closing_time": time(23, 30),
            "parcel_charge_amount": D("20.00"), "parcel_charge_per_item": False,
            "staff_discount_limit_pct": D("10.00"),
        })[0]
        self.tenant, self.outlet = tenant, outlet
        self._features(tenant)
        self.staff = self._staff(tenant, outlet)
        self.stations = self._stations(tenant, outlet)
        self._payment_config(tenant, outlet)
        self._aggregator_config(tenant, outlet)
        self.items = self._menu(tenant, outlet)
        self.tables = self._tables(tenant, outlet)
        self.suppliers = self._suppliers(tenant, outlet)
        self.ingredients = self._ingredients(tenant, outlet)
        self._recipes()
        self.promos = self._promos(tenant, outlet)
        self.offers = self._offers(tenant, outlet)
        self.templates = self._shift_templates(tenant, outlet)
        self._pay_rates(tenant)
        return tenant, outlet

    def _features(self, tenant):
        from tenants.models import TenantFeatureOverride
        wanted = {
            "offers": True, "multi_kitchen": True, "loyalty_points": True, "guest_feedback": True,
            "advanced_reports": True, "gstr_export": True, "reservations": True, "crm": True,
            # Off: needs a Google API key / sends real messages / needs live gateway keys.
            "ai_menu_import": False, "ai_recipe_import": False, "whatsapp_receipts": False,
            "razorpay_gateway": False,
        }
        for feature, enabled in wanted.items():
            self.get_or_create(TenantFeatureOverride, {"tenant": tenant, "feature": feature},
                               {"enabled": enabled, "notes": "Royal Shetkari setup (seed_royal_shetkari)"})

    def _staff(self, tenant, outlet):
        from accounts.models import User
        staff = {}
        for username, role, first, last, _salary in people.STAFF:
            user = User.objects.filter(username=username).first()
            if user and user.tenant_id != tenant.id:
                raise SeedError(f"The username '{username}' is already used by another account. Nothing was changed.")
            if not user and not self.first_time(User):
                continue
            if not user:
                password = self._password()
                user = User.objects.create_user(
                    username=username, password=password, role=role, tenant=tenant, outlet=outlet,
                    first_name=first, last_name=last, email=f"{username}@royalshetkari.example.com",
                )
                self.mark(user)
                self.created_logins.append((username, role, password))
                self.counts["User"] += 1
            staff[username] = user
        self._first[User] = False
        g = staff.get
        self.owner, self.manager = g("rs_owner"), g("rs_manager")
        self.cashiers = [u for u in (g("rs_cashier1"), g("rs_cashier2")) if u]
        self.waiters = [u for u in (g("rs_waiter1"), g("rs_waiter2"), g("rs_waiter3"), g("rs_captain")) if u]
        self.chefs = [u for u in (g("rs_chef1"), g("rs_chef2")) if u]
        return staff

    @staticmethod
    def _password():
        alphabet = string.ascii_letters + string.digits
        while True:
            pw = "".join(secrets.choice(alphabet) for _ in range(12))
            if any(c.isdigit() for c in pw) and any(c.isupper() for c in pw) and any(c.islower() for c in pw):
                return pw

    def reset_demo_passwords(self):
        from accounts.models import User
        ids = self.demo_ids(User)
        for user in User.objects.filter(id__in=ids).order_by("username"):
            password = self._password()
            user.set_password(password)
            user.save(update_fields=["password"])
            self.created_logins.append((user.username, user.role, password))
        self._write_credentials(replace=True)

    def _write_credentials(self, replace=False):
        if not self.created_logins:
            return
        existing = ""
        if self.credentials_path.exists() and not replace:
            existing = self.credentials_path.read_text(encoding="utf-8")
        lines = [] if existing else [
            "ROYAL SHETKARI - DEMO LOGINS (generated on this PC by seed_royal_shetkari)",
            "Keep this file private. Change or remove these accounts before taking real orders:",
            "  python manage.py seed_royal_shetkari --reset-demo-passwords   (new passwords)",
            "  Setup > Staff (owner/manager) to change passwords or deactivate accounts.",
            "",
            "Open http://127.0.0.1:8000/login/ on this PC.",
            "",
            f"{'USERNAME':<14} {'ROLE':<10} PASSWORD",
        ]
        for username, role, password in self.created_logins:
            lines.append(f"{username:<14} {role:<10} {password}")
        with open(self.credentials_path, "w" if not existing else "a", encoding="utf-8") as fh:
            if existing:
                fh.write(f"\n# Added {timezone.localtime():%Y-%m-%d %H:%M}\n")
            fh.write("\n".join(lines) + "\n")

    def _stations(self, tenant, outlet):
        from setup.models import KitchenStation
        stations = {}
        for key, name in menu_data.STATIONS.items():
            st, _ = self.get_or_create(KitchenStation, {"tenant": tenant, "outlet": outlet, "name": name},
                                       {"is_default": key == menu_data.DEFAULT_STATION and not KitchenStation.objects.filter(
                                           tenant=tenant, outlet=outlet, is_default=True).exists()})
            if st:
                stations[key] = st
        return stations

    def _payment_config(self, tenant, outlet):
        from setup.models import PaymentConfig
        config, created = PaymentConfig.for_outlet(outlet, tenant)
        self.payment_config = config
        if self.is_demo(config):
            return   # filled on an earlier run; the owner's later edits stay
        self.mark(config)
        changed = []
        # Only fill what is still empty, so an owner's later edits survive a re-run.
        if not config.upi_id:
            config.upi_id = UPI_ID; changed.append("upi_id")
        if not config.upi_payee_name:
            config.upi_payee_name = UPI_PAYEE; changed.append("upi_payee_name")
        if not config.upi_qr_image and QR_FILE.exists():
            raw = QR_FILE.read_bytes()
            config.upi_qr_image.save("royal_shetkari_phonepe_qr.jpg", ContentFile(raw), save=False)
            changed.append("upi_qr_image")
        if created or not (config.cash_enabled or config.upi_enabled or config.card_enabled):
            config.cash_enabled = config.upi_enabled = config.card_enabled = True
            config.upi_label = "UPI / PhonePe"
            changed += ["cash_enabled", "upi_enabled", "card_enabled", "upi_label"]
        if changed:
            config.save(update_fields=list(dict.fromkeys(changed)))

    def verify_qr_bytes(self):
        """True when the stored QR is byte-for-byte the supplied image."""
        cfg = self.payment_config
        if not cfg.upi_qr_image:
            return False
        with cfg.upi_qr_image.open("rb") as fh:
            stored = hashlib.sha256(fh.read()).hexdigest()
        return stored == hashlib.sha256(QR_FILE.read_bytes()).hexdigest()

    def _aggregator_config(self, tenant, outlet):
        from setup.models import AggregatorConfig
        config, created = AggregatorConfig.for_outlet(outlet, tenant)
        if created and self.first_time(AggregatorConfig):
            config.zomato_enabled = config.swiggy_enabled = True
            config.auto_accept_orders = True
            config.save()
            self.mark(config)

    def _menu(self, tenant, outlet):
        from menu.models import MenuCategory, MenuItem
        items = {}
        for order_idx, (cat_name, _station, _dishes) in enumerate(menu_data.MENU):
            self.get_or_create(MenuCategory, {"tenant": tenant, "outlet": outlet, "name": cat_name},
                               {"display_order": order_idx})
        cats = {c.name: c for c in MenuCategory.objects.filter(tenant=tenant, outlet=outlet)}
        position = defaultdict(int)
        for dish in menu_data.all_dishes():
            position[dish["category"]] += 1
            item, created = self.get_or_create(MenuItem, {"tenant": tenant, "outlet": outlet, "name": dish["name"]}, {
                "category": cats.get(dish["category"]),
                "station": self.stations[dish["station"]],
                "description": dish["description"],
                "price": D(dish["price"]),
                "gst_percentage": D("5.00"),
                "is_veg": dish["is_veg"],
                "estimated_prep_time": dish["prep"],
                "display_order": position[dish["category"]],
                "is_available": True,
            })
            if item is None:
                continue
            if not item.image and self.is_demo(item):
                self._attach_image(item, dish["image_slug"])
            items[dish["name"]] = item
        self.dish_meta = {d["name"]: d for d in menu_data.all_dishes()}
        return items

    def _attach_image(self, item, slug):
        src = IMAGES / f"{slug}.jpg"
        if not src.exists():
            return
        name = f"menu_items/royal_shetkari/{slug}.jpg"
        raw = src.read_bytes()
        if default_storage.exists(name):
            with default_storage.open(name, "rb") as fh:
                same = fh.read() == raw
            if not same:   # the seed's own copy is out of date: replace it
                default_storage.delete(name)
        if not default_storage.exists(name):
            name = default_storage.save(name, ContentFile(raw))
        type(item).objects.filter(pk=item.pk).update(image=name)
        item.image.name = name

    def _tables(self, tenant, outlet):
        from orders.models import Table
        tables = []
        for section, prefix, count, _seats in TABLE_LAYOUT:
            for i in range(1, count + 1):
                t, _ = self.get_or_create(Table, {"tenant": tenant, "outlet": outlet, "name": f"{prefix}{i}"},
                                          {"section": section})
                if t:
                    tables.append(t)
        return tables

    def _suppliers(self, tenant, outlet):
        from inventory.models import Supplier
        out = {}
        for key, name, contact, phone, email, area in inventory_data.SUPPLIERS:
            s, _ = self.get_or_create(Supplier, {"tenant": tenant, "outlet": outlet, "name": name}, {
                "contact_person": contact, "phone": phone, "email": email, "address": f"{area} (sample address)",
            })
            if s:
                out[key] = s
        return out

    def _ingredients(self, tenant, outlet):
        from inventory.models import InventoryItem
        out = {}
        for name, category, unit, cost, supplier, threshold, reorder in inventory_data.INGREDIENTS:
            item, _ = self.get_or_create(InventoryItem, {"tenant": tenant, "outlet": outlet, "name": name}, {
                "category": category, "unit": unit, "stock": D("0"),
                "low_stock_threshold": D(threshold), "reorder_quantity": D(reorder),
                "cost_price": D(cost), "preferred_supplier": self.suppliers.get(supplier),
            })
            if item:
                out[name] = item
        return out

    def _recipes(self):
        from inventory.models import Recipe
        first = self.first_time(Recipe)
        for dish in menu_data.all_dishes():
            item = self.items.get(dish["name"])
            if not first or item is None or not self.is_demo(item) or item.recipes.exists():
                continue
            for ing, qty, unit in inventory_data.recipe_for(dish):
                if ing not in self.ingredients:
                    continue
                Recipe.objects.create(menu_item=item, inventory_item=self.ingredients[ing],
                                      quantity_required=D(str(qty)), unit=unit)
                self.counts["Recipe"] += 1
        if first and self.counts["Recipe"]:
            # One marker row, so later runs know the recipes were written once.
            self.mark(Recipe.objects.filter(menu_item__tenant=self.tenant).first())

    def _promos(self, tenant, outlet):
        from promos.models import Promo
        today = timezone.localdate()
        specs = [
            ("SHETKARI10", "Welcome 10% (Sample)", "percentage", D("10"), D("500"), None, today - timedelta(days=120), today + timedelta(days=60)),
            ("FAMILY150", "Family Feast Rs.150 off (Sample)", "amount", D("150"), D("1500"), 300, today - timedelta(days=100), today + timedelta(days=30)),
            ("MONSOON15", "Monsoon Special 15% (Sample)", "percentage", D("15"), D("800"), 150, today - timedelta(days=95), today - timedelta(days=5)),
            ("STAFFMEAL", "Staff Meal 25% (Sample)", "percentage", D("25"), D("0"), None, today - timedelta(days=120), None),
        ]
        out = {}
        for code, name, kind, value, minimum, max_uses, start, end in specs:
            p, _ = self.get_or_create(Promo, {"tenant": tenant, "code": code}, {
                "outlet": outlet, "name": name, "discount_type": kind, "discount_value": value,
                "min_order_value": minimum, "max_uses": max_uses, "valid_from": start, "valid_until": end,
                "description": "Sample promotion for the demo. Review before use.",
            })
            if p:
                out[code] = p
        return out

    def _offers(self, tenant, outlet):
        from menu.models import MenuCategory
        from offers.engine import BUY_GET_FREE, PERCENT_OFF
        from offers.models import Offer, OfferTarget, OfferWindow
        today = timezone.localdate()
        out = {}
        chai, created = self.get_or_create(Offer, {"tenant": tenant, "outlet": outlet, "name": "Chai-Time 20% off drinks (Sample)"}, {
            "kind": PERCENT_OFF, "percent": D("20"), "priority": 1,
            "valid_from": today - timedelta(days=self.days + 5), "created_by": self.owner,
        })
        if created and chai:
            OfferTarget.objects.create(offer=chai, category=MenuCategory.objects.get(tenant=tenant, outlet=outlet, name="Beverages"))
            OfferWindow.objects.create(offer=chai, days="01234", start_time=time(15, 0), end_time=time(18, 0))
        out["chai"] = chai
        vada, created = self.get_or_create(Offer, {"tenant": tenant, "outlet": outlet, "name": "Buy 2 Vada Pav, get 1 free (Sample)"}, {
            "kind": BUY_GET_FREE, "buy_qty": 2, "free_qty": 1, "priority": 2,
            "valid_from": today - timedelta(days=self.days + 5), "created_by": self.owner,
        })
        if created and vada and "Vada Pav" in self.items:
            OfferTarget.objects.create(offer=vada, menu_item=self.items["Vada Pav"])
        out["vada"] = vada
        return out

    def _shift_templates(self, tenant, outlet):
        from shifts.models import ShiftTemplate
        out = {}
        for key, name, start, end, pay in [
            ("morning", "Morning (10:00-17:00)", time(10, 0), time(17, 0), D("600")),
            ("evening", "Evening (16:30-23:45)", time(16, 30), time(23, 45), D("650")),
            ("full", "Full Day (10:30-23:30)", time(10, 30), time(23, 30), D("1000")),
        ]:
            t, _ = self.get_or_create(ShiftTemplate, {"tenant": tenant, "outlet": outlet, "name": name},
                                      {"start_time": start, "end_time": end, "base_pay": pay})
            if t:
                out[key] = t
        return out

    def _pay_rates(self, tenant):
        from shifts.models import StaffPayRate
        for username, _role, _f, _l, salary in people.STAFF:
            if salary and username in self.staff:
                self.get_or_create(StaffPayRate, {"staff": self.staff[username]}, {
                    "tenant": tenant, "pay_type": "monthly", "monthly_salary": D(salary), "updated_by": self.owner,
                })

    # ------------------------------------------------------------------
    # HISTORY
    # ------------------------------------------------------------------
    def history_exists(self):
        from orders.models import Order
        return Order.objects.filter(id__in=self.demo_ids(Order)).exists()

    def run_history(self):
        if self.history_exists():
            self.out("Sample history already present: nothing added (use --reset-demo to rebuild it).")
            return False
        from crm.feedback_models import GuestFeedback
        from crm.models import Guest, LoyaltyTransaction, Reservation
        from finance.models import Expense
        from inventory.models import InventoryTransaction, PurchaseOrder
        from notifications.models import Notification
        from orders.models import Order, Payment
        from payments.models import Refund, UpiPaymentRequest
        from shifts.models import CashSession, Shift, StaffSchedule
        from waiter.models import WaiterCall

        tracked = [Order, Payment, Refund, InventoryTransaction, PurchaseOrder, Notification, Guest,
                   LoyaltyTransaction, GuestFeedback, Reservation, Expense, CashSession, Shift, StaffSchedule,
                   UpiPaymentRequest, WaiterCall]
        before = {m: m.objects.aggregate(m=Max("id"))["m"] or 0
                  for m in tracked}

        self._check_history_inputs()
        self.clock = Clock()
        self.now = timezone.now()
        self.today = timezone.localdate()
        with transaction.atomic():
            with mock.patch("django.utils.timezone.now", self.clock):
                self._history()
            self.clock.t = None

        # Register everything this run created for the demo tenant.
        t = self.tenant
        scope = {
            Order: Q(tenant=t), Payment: Q(order__tenant=t), Refund: Q(order__tenant=t),
            InventoryTransaction: Q(tenant=t), PurchaseOrder: Q(tenant=t), Notification: Q(tenant=t),
            Guest: Q(tenant=t), LoyaltyTransaction: Q(guest__tenant=t), GuestFeedback: Q(tenant=t),
            Reservation: Q(tenant=t), Expense: Q(tenant=t), CashSession: Q(tenant=t), Shift: Q(tenant=t),
            StaffSchedule: Q(tenant=t), UpiPaymentRequest: Q(tenant=t), WaiterCall: Q(tenant=t),
        }
        for model in tracked:
            manager = model.objects
            ids = list(manager.filter(scope[model], id__gt=before[model]).values_list("id", flat=True))
            self.mark_ids(model, ids, "history")
            self.counts[model.__name__] += len(ids)
        return True

    def _check_history_inputs(self):
        missing = [d["name"] for d in menu_data.all_dishes() if d["name"] not in self.items]
        missing += [n for n, *_ in inventory_data.INGREDIENTS if n not in self.ingredients]
        missing += [u for u, *_ in people.STAFF if u not in self.staff]
        if len(self.tables) < 10 or not self.stations:
            missing.append("tables/kitchen stations")
        if missing:
            raise SeedError(
                "The sample history needs the original sample menu, stock items, staff and tables, "
                f"but {len(missing)} are missing or renamed (e.g. {', '.join(missing[:5])}). Nothing was added.")

    # --- the simulation ------------------------------------------------
    def at(self, dt):
        self.clock.t = dt
        return dt

    def _local(self, day, hh, mm=0):
        naive = datetime.combine(day, time(hh, mm))
        return timezone.make_aware(naive, timezone.get_current_timezone())

    def _history(self):
        start_day = self.today - timedelta(days=self.days - 1)
        # Dishes switched off (by the owner, or by an earlier run) are never ordered.
        self.unavailable = {name for name, item in self.items.items()
                            if not type(item).objects.filter(pk=item.pk, is_available=True).exists()}
        self.guests = self._guests()
        plan = self._plan_orders(start_day)
        self._plan_stock(plan, start_day)

        self._opening_stock(start_day)
        deliveries = self._deliveries_by_day
        sessions = {}
        for offset in range(self.days):
            day = start_day + timedelta(days=offset)
            if day in deliveries:
                self._receive_deliveries(day, deliveries[day])
            sessions[day] = self._open_session(day)
            self._shifts_for_day(day)
            for order_plan in plan.get(day, []):
                self._execute(order_plan)
            self._daily_extras(day)
            self._close_session(day, sessions[day])
        self._live_floor()
        self._pending_purchases()
        self._reservations(start_day)
        self._expenses(start_day)
        self._schedules()
        self._finish_kitchen_state()
        self._final_menu_touches()

    # --- customers -------------------------------------------------------
    def _guests(self):
        from crm.models import Guest
        out = []
        for name, phone, email in people.customers(110, self.rng):
            self.at(self.now - timedelta(days=self.days + self.rng.randint(1, 200)))
            g = Guest.objects.create(tenant=self.tenant, phone=phone, name=name, email=email)
            out.append(g)
        self.at(None)
        return out

    # --- planning --------------------------------------------------------
    def _pick(self, names, k=1, exclude=()):
        pool = [n for n in names if n not in exclude and n not in self.unavailable]
        weights = [POPULAR.get(n, 1) for n in pool]
        picked = []
        for _ in range(min(k, len(pool))):
            choice = self.rng.choices(pool, weights=weights)[0]
            i = pool.index(choice)
            pool.pop(i)
            weights.pop(i)
            picked.append(choice)
        return picked

    def _cat(self, category, veg_only=False):
        return [d["name"] for d in menu_data.all_dishes()
                if d["category"] == category and (d["is_veg"] or not veg_only)]

    def _basket(self, source, party):
        rng = self.rng
        veg = rng.random() < 0.42
        lines = []

        def add(names, qty_range=(1, 1), k=1):
            for n in self._pick(names, k, exclude={x for x, _ in lines}):
                lines.append((n, rng.randint(*qty_range)))

        if source == "dine_in":
            style = rng.random()
            if style < 0.25:   # Maharashtrian breakfast/snack visit
                add(self._cat("Maharashtrian Dishes", veg), (1, max(1, party // 2)), k=rng.randint(1, 2))
                if rng.random() < 0.6:
                    add(["Masala Chai", "Cutting Chai", "Masala Taak", "Filter Coffee", "Kokum Sharbat"], (1, party))
            elif style < 0.4:  # thali
                add(["Maharashtrian Veg Thali"] if veg else ["Maharashtrian Veg Thali", "Malvani Fish Thali", "Tambda Pandhra Rassa Thali", "Kombdi Vade"], (1, max(1, party - 1)))
                add(["Sol Kadhi", "Masala Taak", "Sweet Lassi"], (1, party))
            else:              # full meal
                if rng.random() < 0.55:
                    add(self._cat("Vegetarian Starters") if veg else self._cat("Non-Vegetarian Starters") + self._cat("Vegetarian Starters"), (1, 1), k=1 if party < 4 else 2)
                mains = self._cat("Vegetarian Main Course") if veg else (
                    self._cat("Chicken Main Course") + self._cat("Mutton Main Course") + self._cat("Fish and Seafood") + self._cat("Vegetarian Main Course"))
                add(mains, (1, 1), k=max(1, math.ceil(party / 2)))
                add(["Butter Naan", "Tandoori Roti", "Butter Tandoori Roti", "Garlic Naan", "Laccha Paratha", "Jowar Bhakri", "Ghadichi Poli", "Phulka"],
                    (2, max(2, party + 1)), k=rng.randint(1, 2))
                if rng.random() < 0.6:
                    add(self._cat("Biryani and Rice", veg), (1, 1))
                if rng.random() < 0.5:
                    add(self._cat("Beverages"), (1, max(1, party // 2)), k=rng.randint(1, 2))
                if rng.random() < 0.35:
                    add(self._cat("Desserts"), (1, max(1, party // 2)))
        else:
            style = rng.random()
            if style < 0.35:
                add(self._cat("Biryani and Rice", veg)[:10], (1, 2))
                if rng.random() < 0.5:
                    add(["Masala Taak", "Sol Kadhi", "Gulab Jamun (2 pcs)", "Soft Drink (300 ml)"], (1, 2))
            elif style < 0.6:
                add(self._cat("Snacks and Fast Food", veg), (1, 3), k=rng.randint(1, 3))
                if rng.random() < 0.4:
                    add(["Masala Chai", "Cold Coffee", "Fresh Lime Soda"], (1, 2))
            else:
                mains = self._cat("Vegetarian Main Course") if veg else self._cat("Chicken Main Course") + self._cat("Mutton Main Course")
                add(mains, (1, 1), k=rng.randint(1, 2))
                add(["Butter Naan", "Tandoori Roti", "Laccha Paratha", "Jeera Rice", "Steamed Rice"], (2, 4), k=1)
        return lines or [(self._pick(self._cat("Snacks and Fast Food"))[0], 2)]

    def _plan_orders(self, start_day):
        rng = self.rng
        plan = defaultdict(list)
        guest_cycle = list(self.guests)
        rng.shuffle(guest_cycle)
        for offset in range(self.days):
            day = start_day + timedelta(days=offset)
            weekend = day.weekday() >= 5
            n = rng.choice([5, 6, 6, 7] if weekend else [3, 4, 4, 5])
            for _ in range(n):
                slot = rng.random()
                if slot < 0.18:
                    hh, mm = rng.randint(11, 12), rng.randint(0, 59)
                elif slot < 0.55:
                    hh, mm = rng.randint(12, 15), rng.randint(0, 59)
                elif slot < 0.62:
                    hh, mm = rng.randint(16, 18), rng.randint(0, 59)
                else:
                    hh, mm = rng.randint(19, 22), rng.randint(0, 59)
                when = self._local(day, hh, mm)
                if day == self.today and when > self.now - timedelta(hours=2):
                    continue   # today's later trade is the live floor (_live_floor)
                r = rng.random()
                source = "dine_in" if r < 0.58 else "takeaway" if r < 0.82 else "zomato" if r < 0.91 else "swiggy"
                party = rng.choice([1, 2, 2, 2, 3, 4, 4, 5, 6]) if source == "dine_in" else 1
                guest = None
                if source in ("dine_in", "takeaway") and (guest_cycle or rng.random() < 0.5):
                    guest = guest_cycle.pop() if guest_cycle else rng.choice(self.guests)
                o = rng.random()
                outcome = ("paid" if o < 0.90 else "cancel_before_kot" if o < 0.925 else
                           "cancel_after_kot" if o < 0.945 else "void_line" if o < 0.975 else "refund")
                if source in ("zomato", "swiggy"):
                    outcome = "paid"
                plan[day].append({
                    "when": when, "source": source, "party": party, "guest": guest,
                    "lines": self._basket(source, party), "outcome": outcome,
                    "second_round": source == "dine_in" and rng.random() < 0.18,
                    "discount": self._plan_discount(),
                    "payment": self._plan_payment(source),
                })
        for day in plan:
            plan[day].sort(key=lambda p: p["when"])
        # Every customer gets at least one order: guests not reached yet take
        # over orders held by a repeat guest; any still left over (a short
        # history) are not kept.
        if guest_cycle:
            seen = set()
            repeats = []
            for day in sorted(plan):
                for p in plan[day]:
                    if p["guest"] is not None:
                        if p["guest"].id in seen:
                            repeats.append(p)
                        seen.add(p["guest"].id)
            for p, g in zip(repeats, list(guest_cycle)):
                p["guest"] = g
                guest_cycle.remove(g)
            for g in guest_cycle:
                self.guests.remove(g)
                g.delete()
        # A handful of refund cases with other end states.
        refunds = [p for day in sorted(plan) for p in plan[day] if p["outcome"] == "refund"]
        for p, kind in zip(refunds[-3:], ["refund_pending", "refund_pending", "refund_rejected"]):
            p["outcome"] = kind
        return plan

    def _plan_discount(self):
        r = self.rng.random()
        if r < 0.07:
            return ("manual",)
        if r < 0.13:
            return ("promo", self.rng.choice(["SHETKARI10", "FAMILY150", "MONSOON15", "STAFFMEAL"]))
        return None

    def _plan_payment(self, source):
        if source in ("zomato", "swiggy"):
            return [source]
        r = self.rng.random()
        if r < 0.08:
            return ["split"]
        if r < 0.45:
            return ["cash"]
        if r < 0.88:
            return ["upi"]
        return ["card"]

    # --- stock planning ---------------------------------------------------
    def _consumption(self, lines):
        from inventory.unit_conversion import convert_quantity
        need = defaultdict(D)
        for name, qty in lines:
            for recipe in self.items[name].recipes.all():
                inv = recipe.inventory_item
                need[inv.id] += convert_quantity(recipe.quantity_required * qty, recipe.unit, inv.unit)
        return need

    def _plan_stock(self, plan, start_day):
        """Opening stock and weekly deliveries sized from the planned sales,
        so stock never runs out and ends where the demo wants it: most items
        comfortably stocked, a few below their low-stock level."""
        rng = self.rng
        daily = defaultdict(lambda: defaultdict(D))
        for day, orders in plan.items():
            for p in orders:
                lines = list(p["lines"])
                if p["second_round"]:
                    lines += [("Butter Naan", 2), ("Masala Chai", 1)]
                for inv_id, qty in self._consumption(lines).items():
                    daily[inv_id][day] += qty
        # Live floor and today's extras: generous allowance.
        for inv in self.ingredients.values():
            daily[inv.id][self.today] += D("0")
        week_starts = [start_day + timedelta(days=7 * k) for k in range(0, self.days // 7 + 1)]
        week_starts = [w for w in week_starts if w <= self.today]
        names = list(self.ingredients)
        self.low_items = set(rng.sample([n for n in names if self.ingredients[n].unit != "g"], 7))
        self.opening = {}
        self._deliveries_by_day = defaultdict(list)
        for name, inv in self.ingredients.items():
            per_day = daily[inv.id]
            week_use = []
            for k, ws in enumerate(week_starts):
                we = week_starts[k + 1] if k + 1 < len(week_starts) else self.today + timedelta(days=1)
                week_use.append(sum((per_day.get(ws + timedelta(days=i), D(0)) for i in range((we - ws).days)), D(0)))
            avg_week = (sum(week_use, D(0)) / max(1, len(week_use))) or D("1")
            threshold = inv.low_stock_threshold
            if name in self.low_items:
                final = q2(threshold * D("0.45"))
            else:
                final = q2(max(threshold * D(rng.choice(["1.6", "2", "2.5", "3"])), avg_week * D("0.6")))
            # Opening covers week 0 plus the final level plus a live-floor buffer.
            buffer = q2(avg_week * D("0.15"))
            self.opening[name] = q2(week_use[0] + final + buffer) if week_use else q2(final + buffer)
            for k in range(1, len(week_use)):
                qty = week_use[k]
                if name not in self.low_items:
                    qty = qty * D(rng.choice(["1.00", "1.03", "1.06", "1.10"]))
                    qty = D(math.ceil(qty)) if inv.unit in ("kg", "l", "pcs") and qty > 3 else q2(qty)
                else:
                    qty = q2(qty)
                if qty > 0:
                    self._deliveries_by_day[week_starts[k]].append((name, qty))
            if self.opening[name] <= 0:
                self.opening[name] = q2(final + D("1"))

    def _opening_stock(self, start_day):
        self.at(self._local(start_day, 9, 30))
        for name, inv in self.ingredients.items():
            inv.add_stock(self.opening[name], reference="Opening stock count (DEMO)")

    def _receive_deliveries(self, day, lines):
        from inventory.models import PurchaseOrder, PurchaseOrderItem, generate_po_number
        by_supplier = defaultdict(list)
        for name, qty in lines:
            by_supplier[self.ingredients[name].preferred_supplier_id].append((name, qty))
        for supplier_id, items in by_supplier.items():
            self.at(self._local(day - timedelta(days=1), 18, self.rng.randint(0, 50)))
            # An auto-created draft for this supplier (low stock) is folded in.
            po = PurchaseOrder.objects.filter(tenant=self.tenant, outlet=self.outlet, supplier_id=supplier_id, status="draft").first()
            if po is None:
                po = PurchaseOrder.objects.create(tenant=self.tenant, outlet=self.outlet, supplier_id=supplier_id,
                                                  status="draft", notes="Weekly order (DEMO)")
            if not po.po_number:
                po.po_number = generate_po_number(self.tenant, self.outlet)
            PurchaseOrderItem.objects.filter(purchase_order=po).delete()
            total = D(0)
            for name, qty in items:
                inv = self.ingredients[name]
                price = q2(inv.cost_price * D(self.rng.choice(["0.97", "1.00", "1.00", "1.04"])))
                PurchaseOrderItem.objects.create(purchase_order=po, item=inv, quantity=qty, unit_price=price)
                total += qty * price
            po.status, po.ordered_at, po.total_amount = "ordered", self.clock.t, q2(total)
            po.save()
            self.at(self._local(day, 9, self.rng.randint(0, 50)))
            receipts = {}
            if self.rng.random() < 0.15:
                # The vendor charged a little more for one line.
                first = po.items.first()
                receipts[first.item_id] = {"quantity_received": first.quantity,
                                           "invoiced_price": q2(first.unit_price * D("1.05"))}
            po.receive_order(receipts)

    # --- cash sessions and shifts ----------------------------------------------
    def _open_session(self, day):
        from shifts.models import CashSession
        opened = self._local(day, 10, 45)
        if day == self.today and opened > self.now:
            opened = self.now - timedelta(minutes=30)
        self.at(opened)
        return CashSession.objects.create(tenant=self.tenant, outlet=self.outlet, date=day,
                                          opened_by=self.cashiers[day.toordinal() % 2],
                                          opening_balance=D("2000.00"), status="open")

    def _close_session(self, day, session):
        """Same arithmetic as shifts.views.close_cash_session."""
        from orders.models import Payment
        from payments.models import Refund
        if day == self.today:
            return
        close = self._local(day, 23, 45)
        self.at(close)
        pays = Payment.objects.filter(order__tenant=self.tenant, order__outlet=self.outlet,
                                      paid_at__gte=session.opened_at, paid_at__lte=close)
        cash = pays.filter(method="cash").aggregate(t=Sum("amount"))["t"] or D(0)
        refs = [r.split("REFUND-")[1] for r in pays.filter(method="refund").values_list("reference", flat=True)
                if r and r.startswith("REFUND-")]
        cash_refunds = Refund.objects.filter(id__in=refs, payment__method="cash").aggregate(t=Sum("amount"))["t"] or D(0)
        digital = pays.filter(method__in=["upi", "card"]).aggregate(t=Sum("amount"))["t"] or D(0)
        expected = session.opening_balance + cash - cash_refunds
        actual = expected
        r = self.rng.random()
        if r < 0.12:
            actual = expected - D(self.rng.choice([10, 20, 50, 100]))
        elif r < 0.17:
            actual = expected + D(self.rng.choice([10, 20]))
        session.closed_at, session.closed_by = close, self.manager
        session.expected_cash, session.actual_cash = expected, actual
        session.discrepancy = actual - expected
        session.total_digital_payments, session.total_sales = digital, cash + digital
        session.status = "closed"
        session.notes = "" if actual == expected else "Counted at close (DEMO)"
        session.save()

    def _shifts_for_day(self, day):
        from shifts.models import Shift
        if (self.today - day).days > 30:
            return
        for idx, user in enumerate(self.waiters + self.cashiers + self.chefs + [self.manager]):
            if (day.toordinal() + idx) % 7 == 0:
                continue   # weekly off
            evening = idx % 2 == 1
            start = self._local(day, 16 if evening else 10, self.rng.randint(15, 45) if evening else self.rng.randint(0, 35))
            end = self._local(day, 23 if evening else 17, self.rng.randint(30, 59) if evening else self.rng.randint(0, 40))
            if day == self.today:
                if start > self.now:
                    continue
                end = None
            self.at(start)
            Shift.objects.create(tenant=self.tenant, outlet=self.outlet, staff=user, clocked_in_at=start,
                                 clocked_out_at=end,
                                 tips=D(self.rng.choice([0, 50, 100, 150, 200])) if user.role in ("waiter", "captain") and end else D(0),
                                 notes="" if end else "On shift now")

    def _schedules(self):
        from shifts.models import StaffSchedule
        people_ = self.waiters + self.cashiers + self.chefs + [self.manager]
        for d in range(-14, 8):
            day = self.today + timedelta(days=d)
            for idx, user in enumerate(people_):
                if (day.toordinal() + idx) % 7 == 0:
                    continue
                self.at(self._local(self.today, 9, 0) - timedelta(days=15))
                StaffSchedule.objects.create(tenant=self.tenant, outlet=self.outlet, staff=user, date=day,
                                             template=self.templates["evening" if idx % 2 else "morning"])

    # --- one order --------------------------------------------------------
    def _execute(self, p):
        from orders.services.order_service import add_items_to_order, get_or_create_open_order
        rng = self.rng
        t0 = p["when"]
        source = p["source"]
        cashier = rng.choice(self.cashiers)
        taker = rng.choice(self.waiters) if source == "dine_in" else cashier
        if source in ("zomato", "swiggy"):
            return self._aggregator_order(p)

        self.at(t0)
        table = self._free_table() if source == "dine_in" else None
        if source == "dine_in" and table is None:
            source = p["source"] = "takeaway"
        if table:
            order = get_or_create_open_order(taker, table)
        else:
            from orders.models import Order
            from orders.services.event_service import log_event
            order = Order.objects.create(tenant=self.tenant, outlet=self.outlet, created_by=taker,
                                         status="open", source="takeaway")
            log_event(order, "order_created", taker, {"table": "takeaway"})
        cart = [{"id": self.items[name].id, "quantity": qty} for name, qty in p["lines"]]
        order = add_items_to_order(taker, order, cart)
        if p["guest"]:
            order.customer_name, order.customer_phone = p["guest"].name, p["guest"].phone
            order.save(update_fields=["customer_name", "customer_phone"])

        if p["outcome"] == "cancel_before_kot":
            self.at(t0 + timedelta(minutes=rng.randint(3, 10)))
            self._cancel(order, "Guest left before the order was sent to the kitchen", include_made=False)
            return
        # KOT and kitchen
        self.at(t0 + timedelta(minutes=rng.randint(1, 3)))
        self._kot(order, taker)
        ready_at = self._cook(order, self.clock.t, serve=source == "dine_in")
        if p["outcome"] == "cancel_after_kot":
            self.at(self.clock.t + timedelta(minutes=rng.randint(2, 15)))
            self._cancel(order, "Guest had to leave urgently; cooked food wasted", include_made=True)
            return
        if p["second_round"]:
            self.at(ready_at + timedelta(minutes=rng.randint(8, 20)))
            order = add_items_to_order(taker, order, [{"id": self.items["Butter Naan"].id, "quantity": 2},
                                                      {"id": self.items["Masala Chai"].id, "quantity": 1}])
            self._kot(order, taker)
            ready_at = self._cook(order, self.clock.t, serve=source == "dine_in")
        if p["outcome"] == "void_line" and order.items.exclude(status="voided").count() > 1:
            self.at(ready_at + timedelta(minutes=2))
            line = order.items.exclude(status="voided").order_by("-id").first()
            from orders.services.void_service import void_order_item
            void_order_item(self.manager, line.id, rng.choice(["Wrong dish entered by waiter", "Guest did not like the taste", "Dish delayed, guest cancelled it"]))
            order.refresh_from_db()
        if source == "takeaway":
            self._parcel(order)

        # Bill
        bill_at = ready_at + timedelta(minutes=rng.randint(20, 45) if source == "dine_in" else rng.randint(1, 4))
        self.at(bill_at)
        self._discount(order, p)
        order.refresh_from_db()
        order.status = "billing"
        order.save(update_fields=["status"])
        order.recalculate_totals()
        if order.table:
            order.table.state = "billing"
            order.table.save(update_fields=["state"])
        if p["guest"] and order.discount_type is None and p["guest"].total_points >= 150 and rng.random() < 0.3:
            self._redeem_points(order, p["guest"])
        # Payment
        self.at(bill_at + timedelta(minutes=rng.randint(2, 8)))
        self._pay(order, p["payment"][0], cashier)
        order.refresh_from_db()
        if p["guest"]:
            self._loyalty(order, p["guest"])
            if rng.random() < 0.2:
                self._feedback(order, p["guest"])
        if p["outcome"].startswith("refund"):
            self._refund(order, p["outcome"])

    def _free_table(self):
        from orders.models import Order
        busy = set(Order.objects.filter(tenant=self.tenant, outlet=self.outlet, status__in=["open", "billing"])
                   .values_list("table_id", flat=True))
        free = [t for t in self.tables if t.id not in busy]
        return self.rng.choice(free) if free else None

    def _kot(self, order, user):
        from kitchen.services.kot_service import create_kot
        if order.items.filter(status="pending").exists():
            create_kot(user, order, print_on_create=False)

    def _cook(self, order, sent_at, serve=True, stop_at=None):
        """Moves the order's sent dishes through preparing -> ready (-> served)
        with the kitchen services. Returns when the last dish was ready."""
        from kitchen.services.kitchen_service import set_item_preparing, set_item_ready, set_item_served
        chef = self.rng.choice(self.chefs)
        last = sent_at
        for item in order.items.filter(status="sent").select_related("menu_item"):
            start = sent_at + timedelta(minutes=self.rng.randint(1, 4))
            if stop_at and start > stop_at:
                continue
            self.at(start)
            set_item_preparing(chef, item.id)
            done = start + timedelta(minutes=max(3, item.menu_item.estimated_prep_time + self.rng.randint(-3, 6)))
            if stop_at and done > stop_at:
                continue
            self.at(done)
            set_item_ready(chef, item.id)
            last = max(last, done)
            if serve:
                self.at(done + timedelta(minutes=self.rng.randint(1, 4)))
                set_item_served(self.rng.choice(self.waiters), item.id)
        return last

    def _cancel(self, order, reason, include_made):
        from orders.services.void_service import cancel_whole_order
        cancel_whole_order(self.manager, order.id, reason=reason, include_made=include_made)

    def _parcel(self, order):
        order.refresh_from_db()
        order.parcel_gst_rate = self.outlet.parcel_gst_rate
        order.parcel_surcharge = q2(self.outlet.parcel_charge_amount)
        order.save(update_fields=["parcel_surcharge", "parcel_gst_rate"])
        order.recalculate_totals()

    def _discount(self, order, p):
        from orders.models import OrderEvent
        from promos.models import Promo
        from promos.services import attach_promo
        spec = p["discount"]
        if not spec:
            return
        order.refresh_from_db()
        if spec[0] == "promo":
            promo = Promo.objects.get(tenant=self.tenant, code=spec[1])
            ok, _err = attach_promo(order, promo)
            if not ok:
                return
            order.discount_type, order.discount_value = promo.discount_type, promo.discount_value
            details = {"via": "promo", "promo_id": promo.id, "promo_name": promo.name, "promo_code": promo.code}
        else:
            kind, value, reason = self.rng.choice([
                ("percentage", D("5"), "Regular guest"), ("percentage", D("10"), "Birthday celebration"),
                ("amount", D("50"), "Food served late"), ("amount", D("100"), "Bulk family order"),
            ])
            order.discount_type, order.discount_value = kind, value
            details = {"via": "manual", "reason": reason}
        order.save(update_fields=["discount_type", "discount_value", "promo", "promo_name"])
        order.recalculate_totals()
        OrderEvent.objects.create(tenant=order.tenant, outlet=order.outlet, order=order, event_type="discount_applied",
                                  metadata={"action": "discount_applied", "type": order.discount_type,
                                            "value": str(order.discount_value), **details},
                                  created_by=self.manager)

    def _redeem_points(self, order, guest):
        from crm.models import Guest, LoyaltyTransaction
        from django.db.models import F
        from orders.models import OrderEvent
        guest.refresh_from_db()
        points = min(guest.total_points, 100)
        order.discount_type, order.discount_value = "amount", D(points)
        order.save(update_fields=["discount_type", "discount_value"])
        order.recalculate_totals()
        LoyaltyTransaction.objects.create(guest=guest, order=order, transaction_type="redeem", points=-points,
                                          description=f"Redeemed on bill {order.display_number} (Rs.1 per point)")
        Guest.objects.filter(pk=guest.pk).update(total_points=F("total_points") - points)
        OrderEvent.objects.create(tenant=order.tenant, outlet=order.outlet, order=order, event_type="discount_applied",
                                  metadata={"action": "discount_applied", "type": "amount", "value": str(points),
                                            "via": "manual", "reason": f"Loyalty: {points} points redeemed"},
                                  created_by=self.manager)

    def _pay(self, order, method, cashier):
        from orders.models import OrderEvent, Payment
        from orders.services.payment_service import process_payment
        from payments.models import UpiPaymentRequest
        order.refresh_from_db()
        due = order.grand_total
        if due <= 0:
            order.status, order.closed_at = "closed", self.clock.t
            order.save(update_fields=["status", "closed_at"])
            return
        parts = []
        if method == "split" and due >= 300:
            cash_part = q2(max(D(100), (due * D("0.4")).quantize(D("100"))))
            parts = [("cash", min(cash_part, due - 1)), ("upi", None)]
        else:
            parts = [("upi" if method == "split" else method, None)]
        for i, (m, amount) in enumerate(parts):
            if i:
                self.at(self.clock.t + timedelta(minutes=1))
            order.refresh_from_db()
            paid = order.payments.exclude(method="refund").aggregate(t=Sum("amount"))["t"] or D(0)
            amount = amount if amount is not None else order.grand_total - paid
            reference = None
            if m == "upi":
                self.counts["_upi_ref"] += 1
                reference = f"DEMOUPI{self.today:%y%m}{self.counts['_upi_ref']:06d}"
                req = UpiPaymentRequest.objects.create(tenant=self.tenant, outlet=self.outlet, order=order,
                                                       amount=amount, requested_by=cashier, is_demo=True)
            elif m == "card":
                self.counts["_card_ref"] += 1
                reference = f"DEMOCARD{self.counts['_card_ref']:06d}"
            result = process_payment(order, m, amount, cashier, reference=reference)
            pay = result["payment"]
            updates = {"is_demo": True}
            if m == "upi":
                updates.update(verified_by=cashier, verified_at=self.clock.t)
                req.status, req.reference, req.payment = "verified", reference, pay
                req.verified_by, req.verified_at = cashier, self.clock.t
                if self.rng.random() < 0.3:
                    req.customer_claimed_at = self.clock.t - timedelta(minutes=1)
                req.save()
            Payment.objects.filter(pk=pay.pk).update(**updates)
            OrderEvent.objects.create(tenant=order.tenant, outlet=order.outlet, order=order, event_type="payment_added",
                                      amount=amount, created_by=cashier,
                                      metadata={"method": m, "amount": str(amount), "change_due": "0.00", "demo": True,
                                                **({"reference": reference, "upi_verified": True} if m == "upi" else {})})
        order.refresh_from_db()
        if order.table and order.status == "closed":
            order.table.state = "free"
            order.table.save(update_fields=["state"])

    def _aggregator_order(self, p):
        from orders.models import Order, OrderItem, Payment
        from orders.services.tax_service import tax_snapshot_for
        from kitchen.services.kot_service import create_kot
        source = p["source"]
        self.at(p["when"])
        self.counts["_agg"] += 1
        agg_id = f"DEMO-{source[:3].upper()}-{self.counts['_agg']:05d}"
        order = Order.objects.create(tenant=self.tenant, outlet=self.outlet, source=source,
                                     aggregator_order_id=agg_id, status="paid")
        for name, qty in p["lines"]:
            mi = self.items[name]
            OrderItem.objects.create(order=order, menu_item=mi, quantity=qty, price=mi.price,
                                     **tax_snapshot_for(mi, self.tenant), total_price=mi.price * qty, status="pending")
        order.recalculate_totals()
        Payment.objects.create(order=order, method=source, amount=order.grand_total, reference=agg_id,
                               created_by=None, is_demo=True)
        create_kot(None, order, print_on_create=False)
        ready = self._cook(order, self.clock.t, serve=True)
        self.at(ready + timedelta(minutes=self.rng.randint(5, 12)))
        Order.objects.filter(pk=order.pk).update(status="closed", closed_at=self.clock.t)

    def _loyalty(self, order, guest):
        from crm.models import Guest, LoyaltyTransaction
        from django.db.models import F
        earned = int(float(order.grand_total) * 0.1)
        if earned > 0:
            LoyaltyTransaction.objects.create(guest=guest, order=order, transaction_type="earn", points=earned,
                                              description=f"Bill {order.display_number}")
        Guest.objects.filter(pk=guest.pk).update(total_points=F("total_points") + earned,
                                                 total_spent=F("total_spent") + order.grand_total,
                                                 visit_count=F("visit_count") + 1)
        guest.refresh_from_db()

    def _feedback(self, order, guest):
        from crm.feedback_models import GuestFeedback
        rating = self.rng.choices([5, 4, 3, 2], weights=[50, 32, 13, 5])[0]
        self.at(self.clock.t + timedelta(minutes=self.rng.randint(10, 300)))
        GuestFeedback.objects.create(tenant=self.tenant, outlet=self.outlet, order=order, guest_name=guest.name,
                                     rating=rating, comment=self.rng.choice(people.FEEDBACK_COMMENTS[rating]))

    def _refund(self, order, outcome):
        from payments.refund_service import approve_refund, process_refund, reject_refund
        payment = order.payments.exclude(method="refund").order_by("id").first()
        if not payment:
            return
        self.at(self.clock.t + timedelta(minutes=self.rng.randint(15, 90)))
        partial = self.rng.random() < 0.7
        amount = q2(min(payment.amount, max(D(50), payment.amount * D("0.3")))) if partial else payment.amount
        refund = process_refund(order, payment.id, amount, self.manager,
                                reason="Dish quality complaint, refunded (DEMO)" if partial else "Order mix-up, full refund (DEMO)",
                                customer_complaint=self.rng.choice(["Biryani was too salty", "Wrong dish packed for takeaway",
                                                                    "Found the curry cold", "Charged twice by mistake"]))
        if outcome == "refund":
            self.at(self.clock.t + timedelta(minutes=self.rng.randint(10, 60)))
            approve_refund(refund.id, self.owner, self.tenant, self.outlet)
            from orders.models import Payment
            Payment.objects.filter(order=order, method="refund").update(is_demo=True)
        elif outcome == "refund_rejected":
            self.at(self.clock.t + timedelta(minutes=30))
            reject_refund(refund.id, self.owner, self.tenant, self.outlet, reason="Guest finished the meal; offered dessert instead")

    def _daily_extras(self, day):
        """Occasional wastage and a monthly stock count adjustment, kept small
        enough never to touch the planned stock floor."""
        from waiter.models import WaiterCall
        if self.rng.random() < 0.12:
            name = self.rng.choice([n for n in self.ingredients if n not in self.low_items and self.ingredients[n].unit in ("kg", "l")])
            inv = self.ingredients[name]
            inv.refresh_from_db()
            qty = q2(min(inv.stock * D("0.03"), D("0.5")))
            if qty > 0:
                self.at(self._local(day, 23, 20))
                inv.record_wastage(qty, reference=self.rng.choice(["Spoiled in storage (DEMO)", "Spilled during prep (DEMO)"]))
        if day.day == 1:
            name = self.rng.choice([n for n in self.ingredients if n not in self.low_items and self.ingredients[n].unit == "kg"])
            inv = self.ingredients[name]
            inv.refresh_from_db()
            delta = q2(-min(inv.stock * D("0.02"), D("0.4")))
            if delta < 0:
                self.at(self._local(day, 10, 15))
                inv.adjust_stock(delta, "Monthly physical stock count (DEMO)")
        if self.rng.random() < 0.3 and day != self.today:
            self.at(self._local(day, self.rng.randint(13, 21), self.rng.randint(0, 59)))
            WaiterCall.objects.create(tenant=self.tenant, outlet=self.outlet, table=self.rng.choice(self.tables), is_resolved=True)

    # --- today's live floor ---------------------------------------------------
    def _live_floor(self):
        """Tables in every state right now, for a lively floor plan and kitchen."""
        from kitchen.models import KitchenMessage
        from orders.services.order_service import add_items_to_order, get_or_create_open_order
        from payments.models import UpiPaymentRequest
        from waiter.models import WaiterCall
        now = self.now
        rng = self.rng
        by_name = {t.name: t for t in self.tables}

        def open_at(table_name, minutes_ago, lines, waiter, guest=None):
            self.at(now - timedelta(minutes=minutes_ago))
            table = by_name[table_name]
            order = get_or_create_open_order(waiter, table)
            order = add_items_to_order(waiter, order, [{"id": self.items[n].id, "quantity": q} for n, q in lines])
            if guest:
                order.customer_name, order.customer_phone = guest.name, guest.phone
                order.save(update_fields=["customer_name", "customer_phone"])
            return order

        w = self.waiters
        # F2: just ordering, nothing sent yet
        open_at("F2", 4, [("Puneri Misal Pav", 2), ("Masala Chai", 2)], w[0])
        # F4: KOT sent, kitchen not started
        o = open_at("F4", 9, [("Chicken Dum Biryani", 1), ("Butter Chicken", 1), ("Butter Naan", 3)], w[1])
        self.at(now - timedelta(minutes=8)); self._kot(o, w[1])
        # A3: preparing
        o = open_at("A3", 18, [("Paneer Tikka", 1), ("Kadai Paneer", 1), ("Garlic Naan", 2), ("Jeera Rice", 1)], w[2])
        self.at(now - timedelta(minutes=16)); self._kot(o, w[2])
        self._cook(o, now - timedelta(minutes=16), serve=False, stop_at=now - timedelta(minutes=10))
        # A5: some dishes ready, waiting to be served
        o = open_at("A5", 30, [("Kolhapuri Mutton", 1), ("Jowar Bhakri", 4), ("Sol Kadhi", 2), ("Tandoori Roti", 2)], w[0])
        self.at(now - timedelta(minutes=28)); self._kot(o, w[0])
        self._cook(o, now - timedelta(minutes=28), serve=False, stop_at=now - timedelta(minutes=2))
        # G2: eaten, bill printed, part paid in cash, rest by QR waiting for the cashier to check
        guest = rng.choice(self.guests)
        o = open_at("G2", 75, [("Malvani Fish Thali", 2), ("Surmai Fry", 1), ("Sol Kadhi", 2), ("Ukadiche Modak (2 pcs)", 2)], w[3], guest)
        self.at(now - timedelta(minutes=73)); self._kot(o, w[3])
        self._cook(o, now - timedelta(minutes=73), serve=True)
        self.at(now - timedelta(minutes=12))
        o.refresh_from_db(); o.status = "billing"; o.save(update_fields=["status"]); o.recalculate_totals()
        o.table.state = "billing"; o.table.save(update_fields=["state"])
        self.at(now - timedelta(minutes=8))
        from orders.models import Payment
        from orders.services.payment_service import process_payment
        res = process_payment(o, "cash", D("500.00"), self.cashiers[0])
        Payment.objects.filter(pk=res["payment"].pk).update(is_demo=True)
        self.at(now - timedelta(minutes=6))
        req = UpiPaymentRequest.objects.create(tenant=self.tenant, outlet=self.outlet, order=o,
                                               amount=res["remaining"], requested_by=self.cashiers[0], is_demo=True)
        self.at(now - timedelta(minutes=3))
        req.customer_claimed_at = self.clock.t
        req.save(update_fields=["customer_claimed_at"])
        # F7: served, bill printed, nothing paid yet
        o = open_at("F7", 55, [("Chicken Kolhapuri", 1), ("Bhindi Masala", 1), ("Butter Naan", 4), ("Veg Pulao", 1), ("Gulab Jamun (2 pcs)", 2)], w[1])
        self.at(now - timedelta(minutes=53)); self._kot(o, w[1])
        self._cook(o, now - timedelta(minutes=53), serve=True)
        self.at(now - timedelta(minutes=5))
        o.refresh_from_db(); o.status = "billing"; o.save(update_fields=["status"]); o.recalculate_totals()
        o.table.state = "billing"; o.table.save(update_fields=["state"])
        # A takeaway being cooked
        from orders.models import Order
        self.at(now - timedelta(minutes=7))
        o = Order.objects.create(tenant=self.tenant, outlet=self.outlet, created_by=self.cashiers[1], status="open", source="takeaway")
        o = add_items_to_order(self.cashiers[1], o, [{"id": self.items["Mutton Dum Biryani"].id, "quantity": 2},
                                                     {"id": self.items["Masala Taak"].id, "quantity": 2}])
        o.customer_name, o.customer_phone = "Walk-in (Sample)", ""
        o.save(update_fields=["customer_name", "customer_phone"])
        self._kot(o, self.cashiers[1])
        self._parcel(o)
        # A Swiggy order in the kitchen
        self.counts["_agg"] += 1
        p = {"source": "swiggy", "when": now - timedelta(minutes=11),
             "lines": [("Chicken Tikka Biryani", 1), ("Gulab Jamun (2 pcs)", 1)]}
        from orders.models import OrderItem, Payment as Pay
        from orders.services.tax_service import tax_snapshot_for
        from kitchen.services.kot_service import create_kot
        self.at(p["when"])
        agg = f"DEMO-SWI-{self.counts['_agg']:05d}"
        o = Order.objects.create(tenant=self.tenant, outlet=self.outlet, source="swiggy", aggregator_order_id=agg, status="paid")
        for name, qty in p["lines"]:
            mi = self.items[name]
            OrderItem.objects.create(order=o, menu_item=mi, quantity=qty, price=mi.price,
                                     **tax_snapshot_for(mi, self.tenant), total_price=mi.price * qty, status="pending")
        o.recalculate_totals()
        Pay.objects.create(order=o, method="swiggy", amount=o.grand_total, reference=agg, is_demo=True)
        create_kot(None, o, print_on_create=False)
        self._cook(o, self.clock.t, serve=False, stop_at=now - timedelta(minutes=1))
        # Waiter calls and a kitchen note
        self.at(now - timedelta(minutes=2))
        WaiterCall.objects.create(tenant=self.tenant, outlet=self.outlet, table=by_name["A5"], is_resolved=False)
        WaiterCall.objects.create(tenant=self.tenant, outlet=self.outlet, table=by_name["F7"], is_resolved=False)
        KitchenMessage.objects.filter(tenant=self.tenant, created_at__lt=now - timedelta(minutes=30)).update(is_resolved=True)

    def _pending_purchases(self):
        """This week's order for the items running low: placed, not delivered yet."""
        from inventory.models import PurchaseOrder, PurchaseOrderItem, generate_po_number
        by_supplier = defaultdict(list)
        for name in sorted(self.low_items):
            by_supplier[self.ingredients[name].preferred_supplier_id].append(name)
        for supplier_id, names in by_supplier.items():
            self.at(self.now - timedelta(hours=3))
            po = PurchaseOrder.objects.filter(tenant=self.tenant, outlet=self.outlet, supplier_id=supplier_id, status="draft").first()
            if po is None:
                po = PurchaseOrder.objects.create(tenant=self.tenant, outlet=self.outlet, supplier_id=supplier_id, status="draft",
                                                  notes="Low stock - delivery expected tomorrow (DEMO)")
            if not po.po_number:
                po.po_number = generate_po_number(self.tenant, self.outlet)
            total = D(0)
            for name in names:
                inv = self.ingredients[name]
                line, _ = PurchaseOrderItem.objects.get_or_create(purchase_order=po, item=inv, defaults={
                    "quantity": inv.reorder_quantity, "unit_price": inv.cost_price})
                total += line.quantity * line.unit_price
            po.status, po.ordered_at, po.total_amount = "ordered", self.clock.t, q2(total)
            po.save()

    def _reservations(self, start_day):
        from crm.models import Reservation
        rng = self.rng
        used = set()
        for i in range(45):
            if i < 33:
                day = start_day + timedelta(days=rng.randint(0, self.days - 2))
                status = rng.choices(["seated", "no_show", "cancelled"], weights=[25, 4, 4])[0]
            else:
                day = self.today + timedelta(days=rng.randint(0, 10))
                status = rng.choice(["confirmed", "confirmed", "pending"])
            when = self._local(day, rng.choice([13, 14, 20, 21]), rng.choice([0, 30]))
            table = rng.choice(self.tables)
            if (table.id, when) in used or (status in ("confirmed", "pending") and when < self.now):
                continue
            used.add((table.id, when))
            self.at(when - timedelta(days=rng.randint(1, 5)))
            Reservation.objects.create(tenant=self.tenant, outlet=self.outlet, guest=rng.choice(self.guests),
                                       table=table, reservation_time=when, number_of_guests=rng.randint(2, 8),
                                       status=status, created_by=self.manager,
                                       notes=rng.choice(["", "Birthday - arrange a candle", "Prefers garden seating",
                                                         "Jain food for one guest", "Anniversary dinner"]))

    def _expenses(self, start_day):
        from finance.models import Expense
        rng = self.rng
        salaries = sum(D(s) for *_x, s in people.STAFF if s)
        day = start_day
        while day <= self.today:
            self.at(self._local(day, 11, 0))
            if day.day == 1:
                Expense.objects.create(tenant=self.tenant, outlet=self.outlet, category="rent", amount=D("85000"),
                                       is_recurring=True, expense_date=day, notes="Monthly rent (SAMPLE)", created_by=self.owner)
                Expense.objects.create(tenant=self.tenant, outlet=self.outlet, category="salaries", amount=salaries,
                                       is_recurring=True, expense_date=day, notes="Staff salaries (SAMPLE)", created_by=self.owner)
                Expense.objects.create(tenant=self.tenant, outlet=self.outlet, category="utilities", amount=D("1199"),
                                       is_recurring=True, expense_date=day, notes="Internet (SAMPLE)", created_by=self.manager)
            if day.day == 10:
                Expense.objects.create(tenant=self.tenant, outlet=self.outlet, category="utilities",
                                       amount=D(rng.randint(16000, 22000)), expense_date=day,
                                       notes="Electricity bill (SAMPLE)", created_by=self.manager)
            if day.weekday() == 2:
                Expense.objects.create(tenant=self.tenant, outlet=self.outlet, category="supplies",
                                       amount=D(rng.choice([4400, 4600, 4800])), expense_date=day,
                                       notes="Commercial LPG cylinders x2 (SAMPLE)", created_by=self.manager)
            if day.day in (5, 20) and rng.random() < 0.8:
                Expense.objects.create(tenant=self.tenant, outlet=self.outlet, category=rng.choice(["maintenance", "marketing", "other"]),
                                       amount=D(rng.choice([1500, 2500, 3200, 6000])), expense_date=day,
                                       notes=rng.choice(["AC servicing (SAMPLE)", "Pamphlets and banner (SAMPLE)",
                                                         "Pest control (SAMPLE)", "Kitchen exhaust cleaning (SAMPLE)"]),
                                       created_by=self.manager)
            day += timedelta(days=1)

    def _finish_kitchen_state(self):
        from kitchen.models import KOTBatch
        KOTBatch.objects.filter(tenant=self.tenant, order__status__in=["closed", "paid", "cancelled"]).update(status="ready")
        KOTBatch.objects.filter(tenant=self.tenant, order__status__in=["open", "billing"],
                                items__status="preparing").update(status="preparing")

    def _final_menu_touches(self):
        """A few dishes switched off, as a real menu would have."""
        from menu.models import MenuItem
        for name in ("Crab Masala", "Sugarcane Juice", "Mutton Nalli Nihari"):
            item = self.items[name]
            if self.is_demo(item):
                MenuItem.objects.filter(pk=item.pk).update(is_available=False)
        for name in ("Roti Basket", "Maharashtrian Veg Thali", "Malvani Fish Thali", "Tambda Pandhra Rassa Thali"):
            item = self.items[name]
            if self.is_demo(item):
                MenuItem.objects.filter(pk=item.pk).update(available_zomato=False, available_swiggy=False)

    # ------------------------------------------------------------------
    # REMOVAL (demo records only)
    # ------------------------------------------------------------------
    @transaction.atomic
    def remove_history(self):
        """Delete every demo *history* row, and undo its effect on stock and
        counters. Rows not listed in DemoRecord are never touched."""
        from crm.feedback_models import GuestFeedback
        from crm.models import Guest, LoyaltyTransaction, Reservation
        from finance.models import Expense
        from inventory.models import InventoryItem, InventoryTransaction, PurchaseOrder
        from kitchen.models import DailyKOTCounter
        from notifications.models import Notification
        from orders.models import BillSeries, DailyOrderCounter, Order, Payment, Table
        from payments.models import Refund, UpiPaymentRequest
        from promos.models import Promo
        from shifts.models import CashSession, Shift, StaffSchedule
        from waiter.models import WaiterCall

        tenant = self.find_tenant()
        order_ids = self.demo_ids(Order, "history")
        removed = {}

        def drop(model, ids, label=None, manager=None):
            manager = manager or (model.objects)
            n = manager.filter(id__in=ids).delete()[0] if ids else 0
            removed[label or model.__name__] = n

        drop(Refund, list(Refund.objects.filter(order_id__in=order_ids).values_list("id", flat=True)))
        drop(UpiPaymentRequest, self.demo_ids(UpiPaymentRequest))
        drop(Payment, list(Payment.objects.filter(order_id__in=order_ids).values_list("id", flat=True)))
        drop(LoyaltyTransaction, self.demo_ids(LoyaltyTransaction))
        drop(GuestFeedback, self.demo_ids(GuestFeedback))

        # Stock: reverse each demo movement, then delete it.
        txn_ids = self.demo_ids(InventoryTransaction)
        effect = (InventoryTransaction.objects.filter(id__in=txn_ids)
                  .values("item_id").annotate(total=Sum("quantity")))
        for row in effect:
            item = InventoryItem.objects.get(id=row["item_id"])
            item.stock = max(D(0), item.stock - row["total"])
            item.save(update_fields=["stock"])
        drop(InventoryTransaction, txn_ids)

        drop(Order, order_ids)
        drop(PurchaseOrder, self.demo_ids(PurchaseOrder))
        for model in (Reservation, Expense, CashSession, Shift, StaffSchedule, Notification, WaiterCall):
            drop(model, self.demo_ids(model))
        # Guests: only those no real bill has since used.
        guest_ids = [g for g in self.demo_ids(Guest)
                     if not LoyaltyTransaction.objects.filter(guest_id=g).exists()
                     and not Reservation.objects.filter(guest_id=g).exists()]
        drop(Guest, guest_ids)

        if tenant:
            outlet_ids = list(tenant.outlets.values_list("id", flat=True))
            remaining = Order.objects.filter(outlet_id__in=outlet_ids)
            if not remaining.exists():
                DailyOrderCounter.objects.filter(outlet_id__in=outlet_ids).delete()
                DailyKOTCounter.objects.filter(outlet_id__in=outlet_ids).delete()
            if not remaining.exclude(bill_number__isnull=True).exists():
                BillSeries.objects.filter(outlet_id__in=outlet_ids).delete()
            for promo in Promo.objects.filter(id__in=self.demo_ids(Promo)):
                promo.usage_count = Order.objects.filter(promo=promo).exclude(status="cancelled").count()
                promo.save(update_fields=["usage_count"])
            busy = set(remaining.filter(status__in=["open", "billing"]).values_list("table_id", flat=True))
            Table.objects.filter(tenant=tenant).exclude(id__in=busy).update(state="free")

        DemoRecord.objects.filter(kind="history").delete()
        return removed

    @transaction.atomic
    def remove_everything(self):
        """Delete the whole demo restaurant: only when it holds nothing real."""
        from orders.models import Order, Payment
        tenant = self.find_tenant()
        if tenant is None:
            return {}
        if not self.is_demo(tenant):
            raise SeedError("The Royal Shetkari restaurant was not created by this seed; it is left untouched.")
        demo_orders = set(self.demo_ids(Order))
        real_orders = Order.objects.filter(tenant=tenant).exclude(id__in=demo_orders)
        if real_orders.exists():
            raise SeedError(
                f"The restaurant has {real_orders.count()} real orders, so it was not deleted. "
                "Use --remove-demo-history to remove only the sample history.")
        removed = self.remove_history()
        Payment.objects.filter(order__tenant=tenant).delete()
        tenant.delete()
        DemoRecord.objects.all().delete()
        removed["Tenant"] = 1
        return removed
