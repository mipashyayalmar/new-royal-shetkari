# Royal Shetkari POS on Windows

This folder is the Royal Shetkari restaurant billing software (built on the Rasova POS
project). It runs on one Windows PC in the restaurant. Other phones, tablets or PCs on the
restaurant Wi-Fi can use it through their web browser.

It is **not** a standalone `.exe`: it is a Python web application that `setup.bat` installs
into its own folder and `start.bat` runs.

---

## 1. What you need

| Need | Notes |
|---|---|
| Windows 10 or 11 PC | 4 GB RAM or more. Keep it on while the restaurant is open. |
| Python 3.12 or newer | From <https://www.python.org/downloads/windows/>. In the installer, tick **"Add python.exe to PATH"**. |
| Internet | Only for the first `setup.bat` (it downloads about 200 MB of Python packages). Daily use works without internet. |
| A browser | Chrome or Edge. |

Nothing else is required: the database is a single file (`db.sqlite3`) in this folder, and
no database server, Redis or Docker is needed.

## 2. First-time setup

1. Copy this folder somewhere permanent, for example `C:\RoyalShetkari\`.
   (Avoid a folder that OneDrive is syncing: a database file that keeps being synced can be slow.)
2. Double-click **`setup.bat`**. It will:
   - check Python, create a private Python environment in `.venv\` and install the packages;
   - create `.env` with **new random secret keys for this PC**;
   - back up the database to `backups\`, then apply database updates;
   - load the Royal Shetkari menu and sample data (only if they are not there yet);
   - write the sample staff logins to **`DEMO_LOGINS.txt`**;
   - run the data check (`check_royal_shetkari`) and show the result.
3. Answer **Y** to start the POS. Your browser opens <http://127.0.0.1:8000/login/>.

`setup.bat` is safe to run again; it never deletes data.

## 3. Everyday use

- Double-click **`start.bat`**. It backs up the database (keeps the last 20 backups in
  `backups\`), applies any updates, starts the POS and opens the login page.
- Keep the black window open while the restaurant is working. Close it to stop the POS.

### Using tablets and phones (optional)

1. Open `.env` in Notepad and change `HOST=127.0.0.1` to `HOST=0.0.0.0`. Save.
2. Run `start.bat`. The window shows an address like `http://192.168.1.20:8000/login/`.
3. When Windows Firewall asks, allow **Private networks** only.
4. Open that address on the tablet's browser (same Wi-Fi).

### Temporary online link for testing (optional)

For a quick remote test only, not for daily use. Uses Cloudflare's free "quick tunnel"
(no account needed); the link works only while this PC and both windows stay open, and
changes every time.

1. Download `cloudflared-windows-amd64.exe` from
   https://github.com/cloudflare/cloudflared/releases and save it as `cloudflared.exe`.
2. In a Command Prompt: `cloudflared.exe tunnel --url http://127.0.0.1:8000`. It prints an
   address like `https://some-words.trycloudflare.com`.
3. Open `.env`, add `CSRF_TRUSTED_ORIGINS=https://some-words.trycloudflare.com` (the address
   from step 2), save, then run `start.bat`. Without this line logins fail with
   "Session Needs a Refresh".
4. Share the address only with testers: anyone who has it reaches the login page.
   Remove the line from `.env` when you stop testing.

## 4. Logins

`DEMO_LOGINS.txt` lists the sample accounts and their passwords (generated on this PC):

| Username | Role | Lands on |
|---|---|---|
| rs_owner | Owner | Dashboard, reports, setup, refunds approval |
| rs_manager | Manager | Dashboard, discounts, cancellations, refund requests |
| rs_cashier1, rs_cashier2 | Cashier | Billing, payments, UPI verification |
| rs_captain | Captain | Floor plan, orders (cannot confirm UPI payments) |
| rs_waiter1-3 | Waiter | Floor plan, orders, serving |
| rs_chef1-2 | Chef | Kitchen display |

- New passwords for all sample accounts: `.venv\Scripts\python manage.py seed_royal_shetkari --reset-demo-passwords`
- Make your own existing login the owner: `.venv\Scripts\python manage.py seed_royal_shetkari --make-owner YOURNAME`
- Owners and managers can add staff, change passwords and deactivate accounts in **Setup > Staff**.
- The login `prasad` that already existed in the database was kept unchanged (it is a
  superuser for the `/superuser/` panel and `/admin/`, not attached to a restaurant).

Too many wrong passwords lock a login for one hour (brute-force protection).

## 5. Taking a payment by PhonePe / UPI QR

The restaurant's own PhonePe QR (payee **PRASAD GANESH YELMAR**) is stored exactly as
supplied and shown on the bill screen, the printed bill (while money is due) and the
guest's bill link.

A static QR does not tell the POS when someone pays. So the bill stays **unpaid** until a
cashier, manager or owner checks the money arrived:

1. On the bill, press **UPI / PhonePe**. A panel shows the QR, the order number, the exact
   amount and instructions. A *pending* QR request is recorded; nothing is paid.
2. The guest scans and pays. (A guest pressing "I have paid" on their bill link only tells
   the cashier; it does not pay the bill.)
3. Open the PhonePe Business app / bank SMS and find the payment for that amount.
4. Type the **UPI transaction reference** (12-digit UTR, or the app's transaction ID), tick
   "money received", and press **Confirm payment received**.
5. The payment is recorded with the reference, who confirmed it and when. The same
   reference can never be used twice.

Waiters and captains can show the QR but cannot confirm it. QR payments still waiting are
listed at **/upi/pending/** ("QR payments to verify").

To replace the QR: owner or manager, **Setup > Payment Methods**, upload the new image
(JPG/PNG), and save. You can also change the payee name, UPI ID and instructions there.

> **Please check:** the supplied QR image encodes the UPI ID **`9172353945-2@ibl`**, while
> the UPI ID given in writing was **`9172353945-2@ybl`** (both are PhonePe handles). The QR
> was kept exactly as supplied and the typed ID is shown as text. Make one ₹1 test payment
> to each, or change the UPI ID in Setup > Payment Methods so both match.

Automatic confirmation (no manual reference) needs a payment gateway that reports payments
to the server. The project supports Razorpay dynamic QR for that: it needs the restaurant's
own Razorpay account keys and a public HTTPS address for the webhook, which a PC on a
local network does not have. It is switched off.

## 6. The sample data

Everything sample is fictional and marked:

- **Menu:** 12 categories x 20 dishes = 240 dishes, with descriptions, sample INR prices,
  veg/non-veg, availability, preparation times, kitchen stations, 5% GST rate and a recipe.
  **Prices and tax settings are samples for the owner to review.**
- **Photos:** one per dish, stored in `royal_shetkari/assets/menu_images/` and copied into
  `media/`. Sources, authors and licences: `royal_shetkari/IMAGE_CREDITS.md`.
- **Tax:** no GSTIN or FSSAI number was invented, so bills currently carry **no GST**. Enter
  the real GSTIN and FSSAI number in **Setup > Outlet Settings** and new bills will charge
  the dishes' GST rates.
- **Trading history:** about 400 orders over 90 days (dine-in, takeaway, Zomato, Swiggy), KOTs,
  kitchen times, payments (cash, UPI, card, split), discounts, promos, offers, refunds,
  cancellations, loyalty, reservations, purchases, stock movements, expenses, shifts and
  daily cash sessions. All sample payments are flagged DEMO with DEMO references.
  No money moved and no message was sent to anyone (WhatsApp/SMS are off).
- **Customers:** 110 fictional guests with numbers in the 90001xxxxx block and
  `@example.com` emails. Suppliers and addresses are fictional too.

### Commands (run in this folder)

```bat
.venv\Scripts\python manage.py seed_royal_shetkari                    & rem add what is missing (safe to repeat)
.venv\Scripts\python manage.py seed_royal_shetkari --reset-demo       & rem rebuild sample history up to today
.venv\Scripts\python manage.py seed_royal_shetkari --remove-demo-history & rem before going live
.venv\Scripts\python manage.py check_royal_shetkari                   & rem counts and consistency report
```

The seed keeps a list of every record it created. Re-running never duplicates anything and
never changes or deletes records it did not create (your real orders, or dishes you edited).
`--remove-demo` deletes the whole sample restaurant and refuses if it holds any real order.

## 7. Before taking real orders (go-live checklist)

1. `seed_royal_shetkari --remove-demo-history` (removes sample orders, payments, guests,
   purchases, shifts, cash sessions and their stock movements; bill numbers restart).
2. Setup > Outlet Settings: real address, phone, GSTIN, FSSAI, bill code.
3. Review menu prices, GST rates and availability (Setup > Menu).
4. Set real stock counts and low-stock levels (Inventory).
5. Change or deactivate the sample staff logins; delete `DEMO_LOGINS.txt`.
6. Check the PhonePe QR and UPI ID (section 5).
7. Set up the printer (Setup > Printer). Browser printing works with any installed printer.

## 8. Backups

- `start.bat` copies the database to `backups\` every time it starts (last 20 kept).
- `backups\db_before_royal_shetkari_*.sqlite3` is the database exactly as it was before
  this update.
- Copy `backups\` and `media\` to a USB drive or cloud storage regularly.
- To restore: stop the POS, copy a backup over `db.sqlite3`, start again.

## 9. If something goes wrong

| Problem | Fix |
|---|---|
| "Python 3.12 or newer was not found" | Install Python (section 1) with "Add to PATH", then run `setup.bat` again. |
| Package installation fails | Check internet; run `setup.bat` again. Behind a proxy, set `HTTPS_PROXY` first. |
| Browser shows "can't reach this page" | Is the black `start.bat` window open? Wait a few seconds and refresh. |
| "already running on port 8000" | The POS is already open in another window; use that one. |
| Login locked | Wait one hour, or ask the owner to reset the password. |
| Tablet cannot connect | `HOST=0.0.0.0` in `.env`, same Wi-Fi, allow the app in Windows Firewall (Private). |
| Download PDF bill fails | PDF export needs the GTK runtime (WeasyPrint) on Windows. Use Print instead. |
| Anything else | Look in `logs\errors.log`. |

## 10. What was verified, and what was not

Verified on this PC (local demo): installation into `.venv`, database updates, the sample
data command and its re-run/reset/remove safety, the data consistency report, all pages
opening for every role without server errors, and the full flow over HTTP (login, table,
order, KOT per station, stock deduction, kitchen status, bill, discount, part cash, QR
pending/refused/verified, receipt, history, reports, refund, cancellation, permissions).
See `ROYAL_SHETKARI_CHANGES.md` for the full list.

Not verified for live use: real thermal printers, real PhonePe settlement against the
references, a real GSTIN invoice series, multi-day operation on the restaurant's PC, and
tablets on the restaurant network. A temporary trycloudflare.com link was tested (login,
dashboard, photos) but is not a hosting solution. Optional services stay off: Razorpay, WhatsApp, Gemini
AI menu import, Redis/Celery, PostgreSQL, cloud media storage.
