"""
Public business website: home, about, menu and prices, POS software plan,
contact, and the policy pages a payment gateway (Razorpay) checks before
it activates an account.

Served by Django rather than WhiteNoise (public/), so it works on the
PythonAnywhere copy too, which runs with LOCAL_INSTALL=True. Turned on by
settings.PUBLIC_WEBSITE; when it is off, "/" goes straight to the login
page as before (see core.views.landing) and these pages still exist.

Business details live in BUSINESS below: change them here, not in the
templates, so every page and policy stays consistent.
"""
from django.shortcuts import render

BUSINESS = {
    "name": "Royal Shetkari",
    # The name on the Razorpay/KYC documents. Change it if the business is
    # registered under a different (legal) name.
    "legal_name": "Royal Shetkari",
    "tagline": "Authentic Maharashtrian food, and the restaurant POS we built to run it.",
    "city": "Pune",
    "address": "Pune, Maharashtra 411001, India",
    "phone": "+91 91723 53945",
    "phone_link": "+919172353945",
    "whatsapp_link": "https://wa.me/919172353945",
    "email": "yalmarprasad123@gmail.com",
    "jurisdiction": "Pune, Maharashtra",
    "policy_updated": "16 October 2026",
}

POS_PLAN = {
    "name": "Royal Shetkari POS",
    "price": 1499,
    "period": "month",
    "unit": "per outlet",
    "trial_days": 14,
    "features": [
        "Floor plan, table orders and KOT printing",
        "Kitchen display for chefs",
        "Billing with GST, split bills, discounts and UPI QR",
        "QSR token counter and QR table ordering",
        "Inventory, recipes and stock alerts",
        "Sales reports, shift close and Z-report",
        "Customer CRM and WhatsApp bill receipts",
        "Unlimited staff logins with role-based access",
        "Installable app for Android tablets and phones",
        "Setup help and support on WhatsApp",
    ],
}

# Top-of-page navigation and footer links: (url name, label)
NAV = [
    ("site_home", "Home"),
    ("site_menu", "Menu & Prices"),
    ("site_pos", "POS Software"),
    ("site_about", "About"),
    ("site_contact", "Contact"),
]
POLICIES = [
    ("site_terms", "Terms & Conditions"),
    ("site_privacy", "Privacy Policy"),
    ("site_refund", "Cancellation & Refund Policy"),
    ("site_shipping", "Shipping & Delivery Policy"),
]

# Every public path, for the sitemap and SearchIndexingMiddleware.
PATHS = [
    "/", "/about/", "/our-menu/", "/pos-software/", "/contact/",
    "/terms/", "/privacy-policy/", "/refund-policy/", "/shipping-policy/",
]


def _render(request, template, **extra):
    context = {"biz": BUSINESS, "plan": POS_PLAN, "nav": NAV, "policies": POLICIES}
    context.update(extra)
    return render(request, f"website/{template}", context)


def _menu():
    """The restaurant's menu as [(category, [(name, description, price, is_veg)])]."""
    from royal_shetkari.seed.menu_data import MENU
    return [
        (category, [(d[0], d[1], d[2], d[3]) for d in dishes])
        for category, _station, dishes in MENU
    ]


def home(request):
    menu = _menu()
    highlights = [dish for _cat, dishes in menu[:4] for dish in dishes[:2]]
    prices = [dish[2] for _cat, dishes in menu for dish in dishes]
    return _render(request, "home.html", highlights=highlights,
                   price_min=min(prices), price_max=max(prices))


def about(request):
    return _render(request, "about.html")


def menu(request):
    return _render(request, "menu.html", menu=_menu())


def pos_software(request):
    return _render(request, "pos.html")


def contact(request):
    return _render(request, "contact.html")


def terms(request):
    return _render(request, "terms.html")


def privacy(request):
    return _render(request, "privacy.html")


def refund(request):
    return _render(request, "refund.html")


def shipping(request):
    return _render(request, "shipping.html")
