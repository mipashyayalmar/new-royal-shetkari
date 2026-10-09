"""SearchIndexingMiddleware: only the welcome page on the main site
(CANONICAL_HOST) and the guest menu on a restaurant's own subdomain may be
indexed by search engines. pos.example.com stands in for a real main site.
"""
from django.test import TestCase, override_settings

MAIN = "pos.example.com"


@override_settings(ALLOWED_HOSTS=["testserver", MAIN, "." + MAIN], CANONICAL_HOST=MAIN)
class SearchIndexingTest(TestCase):

    def get(self, path, host):
        return self.client.get(path, HTTP_HOST=host)

    def test_welcome_page_on_the_main_site_can_be_indexed(self):
        response = self.get("/", MAIN)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("X-Robots-Tag", response)

    def test_login_page_is_kept_out_of_search(self):
        response = self.get("/login/", MAIN)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["X-Robots-Tag"], "noindex")

    def test_www_moves_to_the_main_site(self):
        response = self.get("/?ref=x", "www." + MAIN)
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response["Location"], f"https://{MAIN}/?ref=x")

    def test_home_page_copy_on_a_subdomain_is_kept_out_of_search(self):
        # Staff still open their own subdomain; it just is not a search result.
        response = self.get("/", "spice." + MAIN)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["X-Robots-Tag"], "noindex")

    def test_login_on_a_subdomain_is_kept_out_of_search(self):
        response = self.get("/login/", "spice." + MAIN)
        self.assertEqual(response["X-Robots-Tag"], "noindex")

    def test_robots_and_sitemap_are_left_alone(self):
        for path in ("/robots.txt", "/sitemap.xml"):
            response = self.get(path, MAIN)
            self.assertEqual(response.status_code, 200, path)
            self.assertNotIn("X-Robots-Tag", response, path)
            self.assertIn(f"//{MAIN}/", response.content.decode(), path)

    def test_form_posts_on_a_subdomain_are_not_redirected(self):
        # A redirect would drop the posted form, so only GET and HEAD move.
        response = self.client.post("/", HTTP_HOST="www." + MAIN)
        self.assertNotEqual(response.status_code, 301)


@override_settings(CANONICAL_HOST="")
class NoMainSiteTest(TestCase):
    """With no main site configured nothing is indexable and nothing redirects."""

    def test_nothing_is_indexable(self):
        from core.middleware import SearchIndexingMiddleware
        self.assertFalse(SearchIndexingMiddleware.indexable("anything.example", "/"))
        response = self.client.get("/login/")
        self.assertEqual(response["X-Robots-Tag"], "noindex")


class GuestMenuIndexingTest(TestCase):
    """The guest menu on a restaurant's own subdomain stays indexable."""

    @override_settings(CANONICAL_HOST=MAIN)
    def test_guest_menu_paths_are_indexable_on_a_subdomain(self):
        from core.middleware import SearchIndexingMiddleware
        for path in ("/menu/digital-menu/", "/menu/qr/"):
            self.assertTrue(SearchIndexingMiddleware.indexable("spice." + MAIN, path), path)
        self.assertFalse(SearchIndexingMiddleware.indexable("spice." + MAIN, "/menu/"))
        self.assertFalse(SearchIndexingMiddleware.indexable(MAIN, "/menu/digital-menu/"))
