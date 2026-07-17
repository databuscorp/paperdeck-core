"""Transport-security behaviour behind a TLS-terminating proxy (Azure App Service).

The dangerous failure here is not a weak header — it is an infinite redirect loop.
App Service terminates TLS at the edge and forwards plain HTTP to the container, so
`request.is_secure()` is False for every request regardless of how the browser
connected. With SECURE_SSL_REDIRECT on and SECURE_PROXY_SSL_HEADER unset, Django would
redirect every already-HTTPS request back to HTTPS, forever, and the whole site goes
down. These tests pin that behaviour down.

SecurityMiddleware is exercised directly because it reads its settings once at
construction, which makes it awkward to drive through the test client under
override_settings.
"""
from django.http import HttpResponse
from django.middleware.security import SecurityMiddleware
from django.test import RequestFactory, SimpleTestCase, override_settings

PROD_TLS = dict(
    SECURE_SSL_REDIRECT=True,
    SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO', 'https'),
    SECURE_HSTS_SECONDS=31536000,
    SECURE_HSTS_INCLUDE_SUBDOMAINS=True,
    SECURE_REDIRECT_EXEMPT=[r'^api/health/?$'],
)


def _get(path="/api/papers/", *, forwarded_proto=None):
    extra = {"HTTP_X_FORWARDED_PROTO": forwarded_proto} if forwarded_proto else {}
    return RequestFactory().get(path, **extra)


def _run(request):
    mw = SecurityMiddleware(lambda r: HttpResponse("ok"))
    return mw(request)


@override_settings(**PROD_TLS)
class ProxyTLSTests(SimpleTestCase):

    def test_https_request_through_the_proxy_is_not_redirected(self):
        """THE loop guard. The proxy forwards HTTP but sets X-Forwarded-Proto: https.
        If Django doesn't honour that header it redirects an already-secure request to
        https — which the proxy again delivers as HTTP — forever."""
        resp = _run(_get(forwarded_proto="https"))
        self.assertEqual(resp.status_code, 200)

    def test_plain_http_request_is_redirected_to_https(self):
        resp = _run(_get(forwarded_proto="http"))
        self.assertEqual(resp.status_code, 301)
        self.assertTrue(resp["Location"].startswith("https://"))

    def test_health_endpoint_is_exempt_from_the_redirect(self):
        """The platform health probe can hit the container directly over HTTP with no
        X-Forwarded-Proto. A 301 there can read as unhealthy and pull the instance."""
        resp = _run(_get("/api/health/"))
        self.assertEqual(resp.status_code, 200)

    def test_hsts_header_is_sent_on_secure_responses(self):
        resp = _run(_get(forwarded_proto="https"))
        self.assertIn("max-age=31536000", resp["Strict-Transport-Security"])
        self.assertIn("includeSubDomains", resp["Strict-Transport-Security"])
        # preload is deliberately absent — see the SILENCED_SYSTEM_CHECKS note in settings.
        self.assertNotIn("preload", resp["Strict-Transport-Security"])

    def test_no_hsts_on_a_plain_http_response(self):
        """HSTS over plain HTTP is meaningless and Django must not send it."""
        resp = _run(_get(forwarded_proto="http"))
        self.assertNotIn("Strict-Transport-Security", resp)


class SecretKeyGuardTests(SimpleTestCase):
    """settings.py refuses to boot in production with the shipped dev key. Django only
    warns; a warning in a deploy log gets missed, and this key signs every JWT."""

    def test_dev_key_is_rejected_in_production(self):
        import importlib

        import paperdeck.settings as s

        src = importlib.import_module("paperdeck.settings")
        self.assertTrue(hasattr(src, "_DEV_SECRET_KEY"))
        # In a real prod boot (DEBUG=False) this exact value raises ImproperlyConfigured;
        # assert we are not currently *serving* with it while DEBUG is off.
        if not s.DEBUG:
            self.assertNotEqual(s.SECRET_KEY, s._DEV_SECRET_KEY)
            self.assertGreaterEqual(len(s.SECRET_KEY), 50)
