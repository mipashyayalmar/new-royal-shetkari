"""
python manage.py check_royal_shetkari

Read-only report on the Royal Shetkari data: record counts, menu photos, and
consistency checks (bill totals vs payments, stock vs stock ledger, guest
loyalty vs transactions, cash sessions vs payments, demo payment marking,
UPI verification). Exits with an error if any check fails.
"""
from collections import Counter
from decimal import Decimal

from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count, F, Q, Sum

from royal_shetkari.seed.seeder import TENANT_SLUG


class Command(BaseCommand):
    help = "Check counts and consistency of the Royal Shetkari restaurant data (read-only)."

    def handle(self, *args, **opts):
        from crm.models import Guest, LoyaltyTransaction, Reservation
        from finance.models import Expense
        from inventory.models import InventoryItem, InventoryTransaction, PurchaseOrder, Recipe, Supplier
        from menu.models import MenuCategory, MenuItem
        from orders.models import Order, Payment, Table
        from kitchen.models import KOTBatch
        from payments.models import Refund, UpiPaymentRequest
        from setup.models import KitchenStation, PaymentConfig
        from shifts.models import CashSession, Shift
        from accounts.models import User
        from tenants.models import Tenant

        tenant = Tenant.objects.filter(slug=TENANT_SLUG).first()
        if not tenant:
            raise CommandError("Royal Shetkari is not set up. Run: python manage.py seed_royal_shetkari")
        outlet = tenant.outlets.order_by("id").first()
        failures = []

        def check(ok, label, detail=""):
            mark = self.style.SUCCESS("PASS") if ok else self.style.ERROR("FAIL")
            self.stdout.write(f"  [{mark}] {label}{(' - ' + detail) if detail else ''}")
            if not ok:
                failures.append(label)

        U = lambda m: m.objects  # noqa: E731 (management command: no tenant context, so unfiltered)
        orders = U(Order).filter(tenant=tenant)

        self.stdout.write(self.style.MIGRATE_HEADING(f"{tenant.name} / {outlet.name}"))
        self.stdout.write("Counts:")
        cats = U(MenuCategory).filter(tenant=tenant).annotate(n=Count("items"))
        roles = Counter(User.objects.filter(tenant=tenant).values_list("role", flat=True))
        statuses = Counter(orders.values_list("status", flat=True))
        sources = Counter(orders.values_list("source", flat=True))
        methods = Counter(Payment.objects.filter(order__tenant=tenant).values_list("method", flat=True))
        for label, value in [
            ("Menu categories", cats.count()),
            ("Menu items", U(MenuItem).filter(tenant=tenant).count()),
            ("Kitchen stations", U(KitchenStation).filter(tenant=tenant).count()),
            ("Tables / sections", f"{U(Table).filter(tenant=tenant).count()} / "
                                  f"{U(Table).filter(tenant=tenant).values('section').distinct().count()}"),
            ("Staff by role", dict(roles)),
            ("Customers (guests)", U(Guest).filter(tenant=tenant).count()),
            ("Stock items / recipes lines", f"{U(InventoryItem).filter(tenant=tenant).count()} / "
                                            f"{Recipe.objects.filter(menu_item__tenant=tenant).count()}"),
            ("Suppliers / purchase orders", f"{U(Supplier).filter(tenant=tenant).count()} / "
                                            f"{U(PurchaseOrder).filter(tenant=tenant).count()}"),
            ("Orders", f"{orders.count()} {dict(statuses)}"),
            ("Order sources", dict(sources)),
            ("Payments by method", dict(methods)),
            ("KOTs", U(KOTBatch).filter(tenant=tenant).count()),
            ("Refunds", dict(Counter(Refund.objects.filter(order__tenant=tenant).values_list("status", flat=True)))),
            ("Reservations", U(Reservation).filter(tenant=tenant).count()),
            ("Expenses", U(Expense).filter(tenant=tenant).count()),
            ("Cash sessions / staff shifts", f"{U(CashSession).filter(tenant=tenant).count()} / "
                                             f"{U(Shift).filter(tenant=tenant).count()}"),
            ("Loyalty transactions", LoyaltyTransaction.objects.filter(guest__tenant=tenant).count()),
        ]:
            self.stdout.write(f"  {label}: {value}")

        self.stdout.write("Menu:")
        small = [f"{c.name} ({c.n})" for c in cats if c.n < 20]
        check(cats.count() >= 12 and not small, "12 categories with at least 20 dishes each", ", ".join(small))
        items = U(MenuItem).filter(tenant=tenant)
        no_image = [i.name for i in items if not i.image or not default_storage.exists(i.image.name)]
        check(not no_image, "every dish has a stored picture", f"{len(no_image)} missing: {', '.join(no_image[:5])}")
        no_recipe = items.annotate(r=Count("recipes")).filter(r=0)
        check(not no_recipe.exists(), "every dish has a recipe linked to stock items",
              ", ".join(no_recipe.values_list("name", flat=True)[:5]))
        incomplete = items.filter(Q(description="") | Q(station__isnull=True) | Q(price__lte=0))
        check(not incomplete.exists(), "every dish has description, price and kitchen station")

        self.stdout.write("Bills and payments:")
        bad_totals = []
        for o in orders.filter(status__in=["closed", "paid"]).prefetch_related("payments"):
            paid = sum((p.amount for p in o.payments.all() if p.method != "refund"), Decimal("0"))
            if paid != o.grand_total:
                bad_totals.append(o.display_number)
        check(not bad_totals, "every settled bill: payments add up to the bill total", ", ".join(bad_totals[:5]))
        refunds_ok = all(
            Payment.objects.filter(order=r.order, method="refund", amount=-r.amount, reference=f"REFUND-{r.id}").exists()
            for r in Refund.objects.filter(order__tenant=tenant, status="approved"))
        check(refunds_ok, "every approved refund has its negative payment entry")
        cancelled_paid = orders.filter(status="cancelled", payments__isnull=False).distinct().count()
        check(cancelled_paid == 0, "no payment on a cancelled order")
        upi = Payment.objects.filter(order__tenant=tenant, method="upi")
        unverified = upi.filter(Q(verified_by__isnull=True) | Q(reference__isnull=True) | Q(reference=""))
        check(not unverified.exists(), "every UPI payment has a reference and who verified it",
              f"{unverified.count()} without")
        pending = U(UpiPaymentRequest).filter(tenant=tenant, status="pending")
        pending_paid = pending.filter(payment__isnull=False).count()
        check(pending_paid == 0, "pending QR requests have no payment recorded",
              f"{pending.count()} pending, waiting for a cashier")
        demo_orders = orders.filter(Q(payments__is_demo=False) & Q(payments__isnull=False)).distinct()
        self.stdout.write(f"  Sample payments marked DEMO: {Payment.objects.filter(order__tenant=tenant, is_demo=True).count()}"
                          f" of {Payment.objects.filter(order__tenant=tenant).count()} "
                          f"({demo_orders.count()} orders have a non-demo payment, i.e. taken on this PC)")

        self.stdout.write("Stock:")
        drift = []
        for inv in U(InventoryItem).filter(tenant=tenant):
            ledger = U(InventoryTransaction).filter(item=inv).aggregate(t=Sum("quantity"))["t"] or Decimal("0")
            if (ledger - inv.stock).copy_abs() > Decimal("0.001"):
                drift.append(f"{inv.name} stock {inv.stock} ledger {ledger}")
        check(not drift, "stock on hand equals the sum of its stock movements", "; ".join(drift[:3]))
        low = U(InventoryItem).filter(tenant=tenant, stock__lte=F("low_stock_threshold"))
        zero = U(InventoryItem).filter(tenant=tenant, stock__lte=0)
        check(not zero.exists(), "no stock item ran out", ", ".join(zero.values_list("name", flat=True)[:5]))
        self.stdout.write(f"  Below low-stock level now: {', '.join(low.values_list('name', flat=True)) or 'none'}")

        self.stdout.write("Customers and loyalty:")
        bad_guests = []
        for g in U(Guest).filter(tenant=tenant):
            pts = LoyaltyTransaction.objects.filter(guest=g).aggregate(t=Sum("points"))["t"] or 0
            if pts != g.total_points:
                bad_guests.append(g.name)
        check(not bad_guests, "guest points equal their loyalty transactions", ", ".join(bad_guests[:5]))
        phones = set(U(Guest).filter(tenant=tenant).values_list("phone", flat=True))
        with_orders = set(orders.filter(customer_phone__in=phones).values_list("customer_phone", flat=True))
        check(len(with_orders) == len(phones), "every customer has order history",
              f"{len(with_orders)} of {len(phones)}")

        self.stdout.write("Cash sessions:")
        bad_sessions = []
        for s in U(CashSession).filter(tenant=tenant, status="closed"):
            cash = Payment.objects.filter(order__tenant=tenant, method="cash", paid_at__gte=s.opened_at,
                                          paid_at__lte=s.closed_at).aggregate(t=Sum("amount"))["t"] or Decimal("0")
            refs = [r.split("REFUND-")[1] for r in Payment.objects.filter(
                order__tenant=tenant, method="refund", paid_at__gte=s.opened_at, paid_at__lte=s.closed_at
            ).values_list("reference", flat=True) if r and r.startswith("REFUND-")]
            cash_ref = Refund.objects.filter(id__in=refs, payment__method="cash").aggregate(t=Sum("amount"))["t"] or Decimal("0")
            if s.expected_cash != s.opening_balance + cash - cash_ref or s.discrepancy != s.actual_cash - s.expected_cash:
                bad_sessions.append(str(s.date))
        check(not bad_sessions, "closed cash sessions reconcile with cash payments", ", ".join(bad_sessions[:5]))
        open_sessions = U(CashSession).filter(outlet=outlet, status="open").count()
        check(open_sessions <= 1, "at most one open cash session", str(open_sessions))

        self.stdout.write("Payment QR:")
        cfg = PaymentConfig.objects.filter(outlet=outlet).first()
        has_qr = bool(cfg and cfg.upi_qr_image and default_storage.exists(cfg.upi_qr_image.name))
        check(has_qr, "scan-and-pay QR image is stored", cfg.upi_qr_image.name if has_qr else "")
        if cfg:
            self.stdout.write(f"  UPI ID: {cfg.upi_id or '-'}   Payee: {cfg.upi_payee_name or '-'}")

        self.stdout.write("Isolation:")
        other = Order.objects.exclude(tenant=tenant).filter(
            Q(table__tenant=tenant) | Q(outlet__tenant=tenant)).count()
        check(other == 0, "no other restaurant's order points at Royal Shetkari tables/outlets")

        if failures:
            raise CommandError(f"{len(failures)} check(s) failed: {', '.join(failures)}")
        self.stdout.write(self.style.SUCCESS("All checks passed."))

