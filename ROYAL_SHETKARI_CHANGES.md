# Royal Shetkari update: what changed

Setup and daily use: see [WINDOWS_SETUP.md](WINDOWS_SETUP.md).

## Repairs to the existing project

| Problem found | Fix |
|---|---|
| No Windows way to run it: `gunicorn` does not run on Windows, and with `DEBUG=False` the app required https-only cookies, a `*.rasova.net` cookie domain, subdomain redirects and PostgreSQL, so a local install could not log in. | New `LOCAL_INSTALL` mode (`core/settings.py`): http cookies on the local network, no subdomain redirect, SQLite allowed, uploaded files served by Django, `/` opens the login page, background tasks run in-process when there is no Redis. Served by `waitress` (added to `requirements.txt`). |
| Background tasks tried to reach a Redis server that a local install does not have. | `CELERY_TASK_ALWAYS_EAGER` in local mode without `REDIS_URL`. |
| The bill's payment list showed blank times (`p.created_at` does not exist on `Payment`). | Uses `paid_at`; also shows the UPI reference and who verified it. |
| The stock warning compared recipe grams with stock kilograms ("need 460 kg" for 460 g). | `check_inventory_availability` converts units like the KOT deduction does. |
| UPI was recorded the moment anyone pressed the UPI button, with no proof of payment. | See "Scan-and-pay QR" below. |

Unchanged: the architecture, every existing app and screen, and every existing record. The
database was backed up to `backups/db_before_royal_shetkari_20261007_235139.sqlite3` before
any change; the existing login `prasad` is untouched.

## Scan-and-pay QR with cashier verification

- `setup.PaymentConfig`: `upi_qr_image` (stored byte-for-byte, never re-encoded),
  `upi_payee_name`, `upi_instructions`. Owner/manager upload, replace or remove it in
  Setup > Payment Methods (`setup/services/payment_qr.py` checks it is a real JPG/PNG/WebP).
- `payments.UpiPaymentRequest`: one "pay this by QR" request per amount: pending,
  verified or cancelled; guest claim time; reference; who verified and when.
- `orders.Payment`: `verified_by`, `verified_at`, `is_demo`.
- `payments/upi_service.py`, `payments/upi_views.py`: `/upi/start/<order>/` shows the QR and
  creates a *pending* request; `/upi/pending/` lists them; `/bill/public/<token>/upi-claim/`
  lets a guest say "I have paid" (notifies only).
- `pay_order` records a UPI payment only with a pending request, a valid UPI reference
  (6 to 35 letters/digits, never used before) and the cashier's "money received" tick, and
  only for cashier, manager or owner. Split-pay by UPI is refused (each share needs its own
  reference). The Razorpay webhook path (server-confirmed) is unchanged.
- Screens: `static/js/upi_verify.js` panel (QR, order number, amount, instructions,
  reference, tick) on the bill page and the QSR quick-pay; QR on the printed receipt and the
  guest bill link while money is due.

## Royal Shetkari data (`royal_shetkari` app)

- `manage.py seed_royal_shetkari`: restaurant, outlet, 10 staff logins (random passwords in
  `DEMO_LOGINS.txt`), 6 kitchen stations, 24 tables in 3 sections, 12 categories x 20 dishes
  with photos and recipes, 97 stock items, 11 suppliers, promos, offers, shift templates,
  pay rates, feature switches, the PhonePe QR; then 90 days of history made through the
  app's own order, KOT, kitchen, payment, discount, cancellation and refund services.
  Options: `--reset-demo`, `--remove-demo-history`, `--remove-demo`, `--no-history`,
  `--reset-demo-passwords`, `--make-owner`, `--days`, `--random-seed`.
- `royal_shetkari.DemoRecord` lists every row the seed created; re-runs and resets touch
  nothing else.
- `manage.py check_royal_shetkari`: read-only counts and consistency report.
- Photos: `royal_shetkari/assets/menu_images/` (240 JPEGs, 640x480), credits in
  `royal_shetkari/IMAGE_CREDITS.md`, fetched by `royal_shetkari/tools/fetch_menu_images.py`.

## Windows files

`setup.bat`, `start.bat`, `scripts/windows/local_setup.py` (creates `.env` with new keys,
backs up the database, migrates, collects static files, seeds), `scripts/windows/serve.py`
(waitress + opens the browser), `WINDOWS_SETUP.md`.

## New migrations

`orders/0068`, `payments/0002`, `setup/0013`, `royal_shetkari/0001`.

## Tests

`royal_shetkari/tests/` (QR verification, permissions, tenant isolation, QR upload, seed
completeness/idempotency/safe reset); `orders/tests/test_financial_flows.py` updated for
the verified UPI flow.

Results on this PC (SQLite, app by app because the full suite has tests that wait forever on
SQLite):

- Pass: royal_shetkari + core (126), accounts, agency, billing, inventory, kitchen, menu,
  notifications, offers, payments, printing, promos, setup, shifts, tablemerge, tenants,
  waiter, crm, and 55 of 57 orders test files (plus the non-threaded classes of the other
  two: 65 tests OK).
- Fail or hang only because of SQLite (they expect PostgreSQL): tests that run many threads
  at once ("database table is locked": orders qr_concurrency_stress, cooked_dish_cancel and
  reduce_quantity concurrency classes, crm ReservationConcurrencyTest, tokens), and tests that
  expect PostgreSQL's decimal text ("400" instead of "400.00": orders close_without_payment,
  reports golden files). agent/test_rasova_agent.py waits on a live service.
- Photos: 206 of the dish itself, 28 representative photos of a close dish, 6 labelled
  placeholders (chilli mushroom, egg chilli, paneer tikka masala, veg handi, veg hakka
  noodles, shrikhand) - see IMAGE_CREDITS.md.

## Still needs an outside service or the owner

- Real GSTIN, FSSAI, address, phone (not invented; bills carry no GST until a GSTIN is saved).
- Automatic UPI confirmation: a gateway with server callbacks (Razorpay keys + public HTTPS).
- QR UPI handle check: the image encodes `9172353945-2@ibl`; the typed ID was `@ybl`.
- Thermal printer setup; PDF bill download on Windows needs the GTK runtime.
- WhatsApp receipts (Meta/Twilio), AI menu import (Google Gemini key): off.
- Live restaurant use was not tested: printers, real payments, tablets, long-running use.
