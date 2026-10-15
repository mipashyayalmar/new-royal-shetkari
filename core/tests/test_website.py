"""Public business website (core/website.py): the pages a payment gateway
such as Razorpay checks before activating an account must load without a
login, show prices and contact details, and link to every policy."""
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from core import website

MAIN = "pos.example.com"


@override_settings(PUBLIC_WEBSITE=True)
class PublicWebsiteTest(TestCase):

    def test_every_page_loads_without_login(self):
        for path in website.PATHS:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, path)

    def test_every_page_shows_contact_details_and_policy_links(self):
        for path in website.PATHS:
            html = self.client.get(path).content.decode()
            self.assertIn(website.BUSINESS["email"], html, path)
            self.assertIn(website.BUSINESS["phone"], html, path)
            for policy in ("/terms/", "/privacy-policy/", "/refund-policy/", "/shipping-policy/"):
                self.assertIn(f'href="{policy}"', html, f"{path} links {policy}")

    def test_menu_and_software_pages_show_prices(self):
        self.assertContains(self.client.get("/our-menu/"), "Puneri Misal Pav")
        self.assertContains(self.client.get("/our-menu/"), "&#8377;140")
        self.assertContains(self.client.get("/pos-software/"), "&#8377;1,499")

    def test_signed_in_staff_still_go_to_the_dashboard(self):
        user = get_user_model().objects.create_user(username="w", password="x")
        self.client.force_login(user)
        response = self.client.get("/")
        self.assertRedirects(response, "/dashboard/", fetch_redirect_response=False)

    @override_settings(ALLOWED_HOSTS=[MAIN], CANONICAL_HOST=MAIN)
    def test_pages_are_indexable_on_the_main_site(self):
        for path in website.PATHS:
            response = self.client.get(path, HTTP_HOST=MAIN)
            self.assertNotIn("X-Robots-Tag", response, path)

    def test_sitemap_lists_every_page(self):
        xml = self.client.get("/sitemap.xml").content.decode()
        for path in website.PATHS:
            self.assertIn(f"{path}</loc>", xml, path)


@override_settings(PUBLIC_WEBSITE=False)
class RestaurantPcTest(TestCase):
    """The restaurant's own PC opens on the login page."""

    def test_home_goes_to_login(self):
        response = self.client.get("/")
        self.assertRedirects(response, "/login/", fetch_redirect_response=False)

    def test_policy_pages_still_load(self):
        self.assertEqual(self.client.get("/refund-policy/").status_code, 200)
