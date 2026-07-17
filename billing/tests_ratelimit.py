"""Rate limiting on the AI generation endpoints.

The wallet caps what an org can SPEND; this caps how fast it can ASK. A retry loop is
individually affordable on every request and drains the wallet anyway, and every one of
those requests is a live Claude call against an API key shared by every tenant.
"""
import threading
from datetime import timedelta
from unittest.mock import patch

from django.db import connections
from django.http import JsonResponse
from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from billing.models import RateLimitCounter
from utility.decorator.ratelimit import _hit, purge_old_counters, rate_limit


class _Req:
    """Bare request object — the decorator only ever reads `.scope`."""

    def __init__(self, org_id=1, user_id=1):
        self.scope = {'org_id': org_id, 'user_id': user_id}


def _view(request):
    return JsonResponse({'ok': True})


class RateLimitDecoratorTests(TestCase):

    def test_requests_are_allowed_up_to_the_limit_then_refused(self):
        limited = rate_limit('t_basic', limit=3, window_seconds=60)(_view)
        req = _Req(org_id=1)

        for i in range(3):
            self.assertEqual(limited(req).status_code, 200, f'request {i + 1} should pass')

        refused = limited(req)
        self.assertEqual(refused.status_code, 429)
        # A client with no idea how long to wait just hammers us again.
        self.assertIn('Retry-After', refused)
        self.assertGreaterEqual(int(refused['Retry-After']), 1)

    def test_limits_are_per_org_not_global(self):
        """One institute burning its allowance must not lock out every other institute."""
        limited = rate_limit('t_perorg', limit=2, window_seconds=60)(_view)
        for _ in range(3):
            limited(_Req(org_id=1))

        self.assertEqual(limited(_Req(org_id=1)).status_code, 429)
        self.assertEqual(limited(_Req(org_id=2)).status_code, 200)

    def test_orgless_accounts_are_not_limited(self):
        """Legacy single-user accounts have no org to key on — the same carve-out billing
        makes. Keying them all under None would drop every one of them into one bucket."""
        limited = rate_limit('t_orgless', limit=1, window_seconds=60)(_view)
        req = _Req(org_id=None)
        for _ in range(5):
            self.assertEqual(limited(req).status_code, 200)

    def test_a_new_window_restores_the_allowance(self):
        limited = rate_limit('t_window', limit=2, window_seconds=60)(_view)
        req = _Req(org_id=7)
        limited(req)
        limited(req)
        self.assertEqual(limited(req).status_code, 429)

        # Roll the window over by ageing the existing counter row out of it.
        RateLimitCounter.objects.filter(key='t_window:org:7').update(
            window_start=timezone.now() - timedelta(seconds=600))
        self.assertEqual(limited(req).status_code, 200)

    def test_the_limiter_fails_open(self):
        """If the counter itself breaks, let the request through. A rate limiter that
        takes generation down when its own bookkeeping fails has caused a worse outage
        than the abuse it was there to prevent."""
        limited = rate_limit('t_open', limit=1, window_seconds=60)(_view)
        with patch('utility.decorator.ratelimit._hit', side_effect=RuntimeError('db down')):
            self.assertEqual(limited(_Req(org_id=3)).status_code, 200)


class ConcurrentIncrementTests(TransactionTestCase):
    """The whole point of the limiter is that it survives concurrency.

    A read-then-write increment lets two workers read the same count, both conclude they
    are under the limit, and both proceed — exactly the burst this exists to stop. The
    increment is done by the database (UPDATE ... SET count = count + 1), so none can be
    lost. This test fails on the naive implementation.
    """

    def test_concurrent_hits_do_not_lose_increments(self):
        errors = []

        def hit():
            try:
                for _ in range(10):
                    _hit('t_race:org:1', 60)
            except Exception as exc:
                errors.append(exc)
            finally:
                connections.close_all()

        threads = [threading.Thread(target=hit) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(errors, [])
        row = RateLimitCounter.objects.get(key='t_race:org:1')
        # 8 threads x 10 hits. Anything less means an increment was lost to a race.
        self.assertEqual(row.count, 80)


class PurgeTests(TestCase):

    def test_old_windows_are_purged_and_current_ones_kept(self):
        """Unpurged, the table grows one row per key per window, forever."""
        now = timezone.now()
        RateLimitCounter.objects.create(
            key='old', window_start=now - timedelta(days=2), count=5)
        RateLimitCounter.objects.create(key='fresh', window_start=now, count=1)

        deleted = purge_old_counters(older_than_seconds=24 * 3600)

        self.assertEqual(deleted, 1)
        self.assertEqual(
            list(RateLimitCounter.objects.values_list('key', flat=True)), ['fresh'])
