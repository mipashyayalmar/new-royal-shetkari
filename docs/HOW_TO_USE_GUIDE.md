# "How to Use" help centre

A step-by-step guide built into the POS. Each person sees only the help for what their
role can do, in the features this restaurant has switched on. The owner also gets a
Guide Access page (preview only, see below).

## Opening it

- Sign in with any restaurant account and press **How to Use** at the bottom left of any
  staff screen. On a phone it's the **?** button.
- Or add `?guide=start` to any staff page address, for example
  `http://127.0.0.1:8000/dashboard/?guide=start`. Use a section name to jump to it:
  `?guide=upi`, `?guide=menu`, `?guide=closing`.
- Close it with **Close** or the Esc key. The page underneath doesn't reload.
- Walkthroughs: press **Start walkthrough** in a section. It opens the right screen
  (for example `/billing/?guide_tour=billing`) and highlights the real buttons one at a
  time, with **Back**, **Next**, **Restart** and **Skip**. A walkthrough never presses,
  submits, pays or deletes anything. That was checked: walkthroughs send no POST requests.

It isn't shown on customer pages (QR menu, guest bill link, feedback, token display
board), to signed-out visitors, to the internal `agent` role, or to a platform superuser
who has no restaurant.

## What each role gets

| Role | Sections |
|---|---|
| Owner | 36: everything below plus Online orders (Zomato/Swiggy) and Guide Access |
| Manager | 34: setup, daily operations, billing, refunds, stock, purchasing, customers, bookings, expenses, reports, closing, example day |
| Cashier | 18: register, dine-in, takeaway, live orders, calls, bill and discounts, payments, UPI confirmation, receipts, corrections, history, customers, bookings, closing |
| Captain | 17: as cashier, but no receipts section, and the UPI page says a cashier/manager/owner must confirm |
| Waiter | 12: dine-in, takeaway, live orders and serving, calls, making the bill, showing the QR (not confirming), history, closing |
| Chef, Kitchen Staff | 6: start, login, clock in/out, kitchen screen, closing, problems |

The counts are for Royal Shetkari's current features. A switched-off feature (for example
inventory, reservations, kitchen display) removes its sections, and their links, for
everyone.

## How visibility works (frontend only)

- `templates/core/base.html` includes `templates/help/guide.html` only when the URL has
  `?guide=` or `?guide_tour=`, so normal pages load nothing extra.
- `templates/help/_sections.html` wraps every section in the same role and feature checks
  as the screen it describes (`role in "owner,manager"`, `'inventory' in tenant_features`).
  A section a role can't use is never sent to that person's browser. The contents list,
  search, Previous/Next, walkthroughs and Open Feature links are built from those sections,
  so they follow the same rules.
- Role/feature rules were taken from the views (`role_required`, `feature_required` and
  the role checks inside each view), not from the old manual.

## Guide Access (owner) is preview only

The owner sees a section-by-role matrix with **Save Changes**, **Reset Unsaved Changes**
and a **Show the guide as** role preview.

- Ticks start as "this role can use the feature". A lock means the role has no permission
  for that feature, so the guide can't be shown to them. Guide access never grants
  permissions.
- Unticking a box and choosing a role in the preview hides that section in the owner's
  preview. **Reset Unsaved Changes** undoes the ticks. All of this works.
- **Save Changes is disabled.** There is no existing endpoint or database field that can
  store guide settings, and the brief ruled out Python/model changes. Nothing is
  saved, including to `localStorage`, and staff are unaffected.

### Backend work needed to make saving real

1. Storage: a `GuideAccess` model (tenant, role, section_id, visible) or a JSON field on
   the tenant, plus a migration.
2. An owner-only POST endpoint (`@login_required`, `@tenant_required`,
   `@role_required("owner")`) that accepts `{section_id: {role: bool}}`, rejects section
   IDs that aren't in the guide and roles outside `User.ASSIGNABLE_STAFF_ROLES`, and saves
   for `request.user.tenant` only.
3. A context processor or template tag that gives the template the saved "hidden" set.
   `_sections.html` would then render a section only if the role/feature check passes and
   the owner hasn't hidden it, so the server still decides what each person sees.
4. In `static/js/help_guide.js`, enable the Save button and POST the `allowed` map with the
   CSRF token. Load the initial ticks from the saved settings instead of
   "everything allowed".

## Files

New:

- `templates/help/guide.html`: help window (header, search, contents, breadcrumbs, pager,
  owner preview bar)
- `templates/help/_sections.html`: all help content with role/feature conditions and
  walkthrough steps
- `static/css/help_guide.css`: layout and styling using the existing theme tokens
  (light/dark, desktop, tablet, phone, print)
- `static/js/help_guide.js`: contents list, search, navigation, keyboard handling,
  checklist status, Guide Access preview, walkthroughs
- `docs/HOW_TO_USE_GUIDE.md`: this file

Changed:

- `templates/core/base.html`: the **How to Use** button and the conditional include. No
  other changes.

No Python files, models, migrations, calculations or payment logic were changed. The
beginner checklist reads its live status from the existing `/setup/checklist/` endpoint.

## Verified

On a copy of the database (test server on port 8011) and with the Django test client:

- Each role (owner, manager, cashier, captain, waiter, chef, kitchen) gets exactly the
  sections its permissions allow. Every rendered section's role list contains the viewer.
  The owner has every section any staff role has. All cross-links point to sections that
  role also has.
- Every **Open Feature** link and in-text link opens (HTTP 200) for each role that sees it.
- With inventory, purchase orders, kitchen display, reservations, CRM, floor plan, waiter
  calls, advanced reports and offers switched off, their sections disappear and the
  remaining links still open.
- The guide doesn't appear for signed-out visitors or on the public QR menu.
- In Microsoft Edge (Playwright), 57 of 57 checks passed:
  - opening and closing, including keeping page filters
  - search, highlighting, no-match message, Enter to open
  - breadcrumbs, Previous/Next, keyboard on expandable parts, feature cards, Esc
  - the Guide Access matrix, role preview and Reset; Save disabled; nothing stored
  - 7 walkthroughs (billing, bill page, menu, payment setup, cash register, inventory,
    kitchen) with Back, Next, Restart, Skip, and no POST requests
  - layout on phone (390 px), tablet (820 px) and desktop with no sideways scrolling
  - no JavaScript errors for owner, waiter, cashier or chef

Not verified: screen-reader testing with a real screen reader, every theme other than
the default, and the tours on every possible screen size (a step whose button is hidden
says so instead of pointing at nothing).

## Where the old manual (`docs/USER_MANUAL.md`) doesn't match the code

The guide follows the code. The manual was not changed.

- It describes a **Kitchen Message** button. The server endpoint exists, but no screen
  has the button.
- It says fine-dining staff open the cash register from Shifts → Cash Sessions. That page
  is owner/manager only. Cashiers and captains open the register from the prompt on the
  bill page.
- It says waiters can close the bill themselves and cancel items. Waiters can't take
  payments or cancel items.
- It describes the counter screen (**Checkout**, **Confirm & Print Slip**). That screen
  only appears for counter outlets without a kitchen screen or kitchen printer. Royal
  Shetkari uses **Dispatch** and **Bill**.
- It says a page you can't use sends you back to your dashboard. Many show a "Permission
  denied" or "not available" page instead.
- It has no Captain or Kitchen Staff roles, and still uses the old "Rasova" name.
