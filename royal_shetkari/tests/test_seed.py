"""
seed_royal_shetkari: complete, repeatable, and never touches real data.

Uses a 14-day history to keep the test quick; the command's default is 90.
Run: python manage.py test royal_shetkari
"""
import tempfile
from decimal import Decimal
from io import StringIO
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TransactionTestCase, override_settings

from inventory.models import InventoryItem
from menu.models import MenuCategory, MenuItem
from orders.models import Order, OrderItem, Payment
from royal_shetkari.models import DemoRecord
from royal_shetkari.seed.seeder import TENANT_SLUG
from tenants.models import Tenant

TEMP = tempfile.mkdtemp(prefix="rs_seed_test_")


@override_settings(MEDIA_ROOT=TEMP)
class SeedCommandTests(TransactionTestCase):
    def seed(self, *args):
        out = StringIO()
        call_command("seed_royal_shetkari", "--days", "14", "--credentials-file", str(Path(TEMP) / "logins.txt"),
                     *args, stdout=out)
        return out.getvalue()

    def snapshot(self, tenant):
        return {
            "categories": MenuCategory.objects.filter(tenant=tenant).count(),
            "items": MenuItem.objects.filter(tenant=tenant).count(),
            "orders": Order.objects.filter(tenant=tenant).count(),
            "payments": Payment.objects.filter(order__tenant=tenant).count(),
            "stock": {i.name: i.stock for i in InventoryItem.objects.filter(tenant=tenant)},
        }

    def test_seed_is_complete_repeatable_and_safe(self):
        out = self.seed()
        tenant = Tenant.objects.get(slug=TENANT_SLUG)
        self.assertIn("PhonePe QR stored byte-for-byte: yes", out)

        # Menu: 12 categories, 20+ dishes each, every dish complete.
        cats = MenuCategory.objects.filter(tenant=tenant)
        self.assertEqual(cats.count(), 12)
        for cat in cats:
            self.assertGreaterEqual(cat.items.count(), 20, cat.name)
        self.assertFalse(MenuItem.objects.filter(tenant=tenant, recipes__isnull=True).exists())
        self.assertTrue(Payment.objects.filter(order__tenant=tenant).exists())
        self.assertFalse(Payment.objects.filter(order__tenant=tenant, is_demo=False).exists())
        self.assertTrue((Path(TEMP) / "logins.txt").exists())

        # The consistency report passes (its picture check needs every photo downloaded).
        if self._images_complete():
            call_command("check_royal_shetkari", stdout=StringIO())

        # Running again adds nothing.
        before = self.snapshot(tenant)
        out = self.seed()
        self.assertIn("already present", out)
        self.assertEqual(self.snapshot(tenant), before)

        # A real order taken on the restaurant's own data survives a reset.
        outlet = tenant.outlets.first()
        dish = MenuItem.objects.get(tenant=tenant, name="Vada Pav")
        real = Order.objects.create(tenant=tenant, outlet=outlet, status="open", source="takeaway")
        OrderItem.objects.create(order=real, menu_item=dish, quantity=1, price=dish.price,
                                 gst_percentage=dish.gst_percentage, total_price=dish.price)
        renamed = MenuItem.objects.get(tenant=tenant, name="Pav Bhaji")
        renamed.price = Decimal("175.00")
        renamed.save(update_fields=["price"])

        self.seed("--reset-demo")
        self.assertTrue(Order.objects.filter(id=real.id).exists())
        renamed.refresh_from_db()
        self.assertEqual(renamed.price, Decimal("175.00"))   # owner's edit kept
        self.assertEqual(MenuItem.objects.filter(tenant=tenant).count(), before["items"])

        # Removing the sample history keeps the restaurant and the real order.
        self.seed("--remove-demo-history")
        self.assertEqual(list(Order.objects.filter(tenant=tenant).values_list("id", flat=True)), [real.id])
        self.assertFalse(DemoRecord.objects.filter(kind="history").exists())
        self.assertEqual(MenuItem.objects.filter(tenant=tenant).count(), before["items"])
        for item in InventoryItem.objects.filter(tenant=tenant):
            self.assertEqual(item.stock, Decimal("0"), item.name)   # only demo movements existed

        # The whole restaurant cannot be removed while it holds a real order.
        with self.assertRaises(CommandError):
            self.seed("--remove-demo")
        real.delete()
        self.seed("--remove-demo")
        self.assertFalse(Tenant.objects.filter(slug=TENANT_SLUG).exists())

    def test_existing_restaurant_not_touched_without_flag(self):
        Tenant.objects.create(name="Royal Shetkari", slug=TENANT_SLUG)
        with self.assertRaises(CommandError):
            self.seed("--no-history")
        self.assertFalse(MenuItem.objects.exists())

    @staticmethod
    def _images_complete():
        from royal_shetkari.seed.menu_data import all_dishes
        from royal_shetkari.seed.seeder import IMAGES
        return all((IMAGES / f"{d['image_slug']}.jpg").exists() for d in all_dishes())
