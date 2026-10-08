"""
python manage.py seed_royal_shetkari [options]

Creates the Royal Shetkari restaurant with a full sample menu and 90 days of
sample trading. Safe to run again: it only adds what is missing and never
changes or deletes anything it did not create (see royal_shetkari.DemoRecord).

  (no options)              set up the restaurant; add sample history if none yet
  --no-history              set up the restaurant, menu, staff and stock items only
  --reset-demo              delete the sample history and build it again
  --remove-demo-history     delete the sample history only (before going live);
                            keeps the restaurant, menu, staff, tables and stock items
  --remove-demo             delete the whole sample restaurant (refused if it holds
                            any real order)
  --reset-demo-passwords    give every sample staff login a new password
  --make-owner USERNAME     make an existing login the owner of Royal Shetkari
  --days N / --random-seed N  size and shape of the sample history
"""
from django.core.management.base import BaseCommand, CommandError

from royal_shetkari.seed.seeder import SeedError, Seeder


class Command(BaseCommand):
    help = "Create (or refresh) the Royal Shetkari restaurant and its clearly marked sample data."

    def add_arguments(self, parser):
        parser.add_argument("--no-history", action="store_true")
        parser.add_argument("--reset-demo", action="store_true")
        parser.add_argument("--remove-demo-history", action="store_true")
        parser.add_argument("--remove-demo", action="store_true")
        parser.add_argument("--reset-demo-passwords", action="store_true")
        parser.add_argument("--make-owner", metavar="USERNAME")
        parser.add_argument("--use-existing-restaurant", action="store_true")
        parser.add_argument("--days", type=int, default=90)
        parser.add_argument("--random-seed", type=int, default=2026)
        parser.add_argument("--credentials-file", default=None)

    def handle(self, *args, **opts):
        if not 14 <= opts["days"] <= 365:
            raise CommandError("--days must be between 14 and 365.")
        seeder = Seeder(self.stdout.write, rng_seed=opts["random_seed"], days=opts["days"],
                        credentials_path=opts["credentials_file"],
                        allow_existing_tenant=opts["use_existing_restaurant"])
        try:
            if opts["remove_demo"]:
                removed = seeder.remove_everything()
                self._report("Removed the sample restaurant", removed)
                return
            if opts["remove_demo_history"]:
                removed = seeder.remove_history()
                self._report("Removed sample history (restaurant, menu, staff and stock items kept)", removed)
                return

            tenant, outlet = seeder.run_setup()
            seeder._write_credentials()
            self.stdout.write(self.style.SUCCESS(f"Restaurant ready: {tenant.name} / {outlet.name}"))

            if opts["make_owner"]:
                self._make_owner(opts["make_owner"], tenant, outlet)
            if opts["reset_demo_passwords"]:
                seeder.reset_demo_passwords()
                self.stdout.write(self.style.SUCCESS(f"New demo passwords written to {seeder.credentials_path}"))

            if opts["reset_demo"]:
                removed = seeder.remove_history()
                self._report("Removed old sample history", removed)
            if not opts["no_history"]:
                self.stdout.write(f"Writing {opts['days']} days of sample history (takes a few minutes)...")
                if seeder.run_history():
                    self.stdout.write(self.style.SUCCESS("Sample history added."))
        except SeedError as e:
            raise CommandError(str(e))

        created = {k: v for k, v in seeder.counts.items() if not k.startswith("_") and v}
        if created:
            self._report("Created", created)
        if seeder.created_logins:
            self.stdout.write(self.style.WARNING(
                f"Demo logins (with passwords) were saved to {seeder.credentials_path}. Keep that file private."))
        if hasattr(seeder, "payment_config"):
            ok = seeder.verify_qr_bytes()
            self.stdout.write(("PhonePe QR stored byte-for-byte: yes" if ok else
                               "PhonePe QR: not the supplied file (replaced by the owner, or missing)"))

    def _make_owner(self, username, tenant, outlet):
        from accounts.models import User
        user = User.objects.filter(username=username).first()
        if not user:
            raise CommandError(f"No login called '{username}'.")
        if user.tenant_id and user.tenant_id != tenant.id:
            raise CommandError(f"'{username}' already belongs to another restaurant; not changed.")
        user.tenant, user.outlet, user.role = tenant, outlet, "owner"
        user.save(update_fields=["tenant", "outlet", "role"])
        self.stdout.write(self.style.SUCCESS(f"'{username}' is now the owner of {tenant.name}."))

    def _report(self, title, counts):
        self.stdout.write(title + ":")
        for name, n in sorted(counts.items()):
            if n:
                self.stdout.write(f"  {name}: {n}")
