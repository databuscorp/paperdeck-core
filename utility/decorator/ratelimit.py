"""Rate limiting for the AI generation endpoints.

Why this exists even though there is already a credit wallet: the wallet caps what an
org can SPEND, not how fast it can ask. Those are different failures.

  * A buggy frontend retry loop, or a script, can fire hundreds of generations in
    seconds. Each one is individually affordable, so billing waves them all through —
    and the org's wallet is drained in a minute by work nobody wanted.
  * Every one of those requests is a live Anthropic call. Our API key has an
    org-wide rate limit shared by every tenant, so one runaway caller degrades
    generation for every other coaching institute on the platform. Billing cannot see
    that at all.

So: the wallet answers "can they afford it", this answers "are they asking too fast",
and both have to pass.

The counter lives in Postgres (see billing.models.RateLimitCounter) because the app runs
several gunicorn workers and can scale out — an in-process counter would give each worker
its own allowance and quietly multiply every limit below by the worker count.
"""
import logging
from datetime import datetime, timedelta
from functools import wraps

from django.db import IntegrityError, transaction
from django.db.models import F
from django.http import JsonResponse
from django.utils import timezone

logger = logging.getLogger(__name__)


def _window_start(now, window_seconds: int):
    """Floor `now` to the current fixed window."""
    epoch = int(now.timestamp())
    return datetime.fromtimestamp(
        epoch - (epoch % window_seconds), tz=timezone.get_current_timezone(),
    )


def _hit(key: str, window_seconds: int) -> int:
    """Count this request against `key` and return the new count for the window.

    Must be atomic. A read-then-write would let two concurrent requests both read the
    same count, both decide they are under the limit, and both proceed — which is
    exactly the burst this is here to stop. The UPDATE ... SET count = count + 1 is done
    by the database, so increments cannot be lost.
    """
    from billing.models import RateLimitCounter

    start = _window_start(timezone.now(), window_seconds)

    # Fast path: the row for this window already exists.
    updated = (RateLimitCounter.objects
               .filter(key=key, window_start=start)
               .update(count=F('count') + 1))
    if not updated:
        try:
            # First request of the window. Several workers can reach here at once; the
            # unique constraint on (key, window_start) means exactly one INSERT wins.
            # atomic() so a losing INSERT does not poison the caller's transaction.
            with transaction.atomic():
                RateLimitCounter.objects.create(key=key, window_start=start, count=1)
            return 1
        except IntegrityError:
            RateLimitCounter.objects.filter(key=key, window_start=start).update(
                count=F('count') + 1)

    row = RateLimitCounter.objects.filter(key=key, window_start=start).values('count').first()
    return (row or {}).get('count', 1)


def _retry_after(window_seconds: int) -> int:
    now = timezone.now()
    start = _window_start(now, window_seconds)
    return max(1, int(window_seconds - (now - start).total_seconds()))


def rate_limit(name: str, limit: int, window_seconds: int, per: str = 'org'):
    """Refuse a request with 429 once `limit` is exceeded in the current window.

    `per='org'` limits the whole coaching institute (this is what protects the shared
    Anthropic key and the org's wallet). `per='user'` limits one staff member. Stack the
    decorator to apply both.

    Fails OPEN. If the counter itself errors — the table is missing, the DB is briefly
    unreachable — we log and let the request through. A rate limiter that takes the
    product down when its bookkeeping breaks has caused a worse outage than the abuse it
    was defending against.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            scope = getattr(request, 'scope', None) or {}
            subject = scope.get('org_id') if per == 'org' else scope.get('user_id')
            if not subject:
                # Orgless legacy accounts have nothing to key on; the same carve-out
                # billing makes. Nothing to limit against, so don't.
                return view_func(request, *args, **kwargs)

            key = f'{name}:{per}:{subject}'
            try:
                count = _hit(key, window_seconds)
            except Exception:
                logger.exception('Rate-limit counter failed for %s — allowing request', key)
                return view_func(request, *args, **kwargs)

            if count > limit:
                retry_after = _retry_after(window_seconds)
                logger.warning('Rate limit hit: %s (%d/%d in %ds)',
                               key, count, limit, window_seconds)
                response = JsonResponse(
                    {'status': 429,
                     'message': (f'Too many AI generation requests — the limit is {limit} '
                                 f'per {_human(window_seconds)}. Try again in {retry_after}s.')},
                    status=429,
                )
                # Tells a well-behaved client exactly how long to back off, instead of
                # leaving it to hammer us in a retry loop.
                response['Retry-After'] = str(retry_after)
                return response

            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator


def _human(seconds: int) -> str:
    if seconds % 3600 == 0:
        n = seconds // 3600
        return 'hour' if n == 1 else f'{n} hours'
    if seconds % 60 == 0:
        n = seconds // 60
        return 'minute' if n == 1 else f'{n} minutes'
    return f'{seconds} seconds'


def purge_old_counters(older_than_seconds: int = 24 * 3600) -> int:
    """Drop counter rows for windows that have long closed.

    Without this the table grows one row per key per window forever. Called from the
    same place stale jobs are reaped, so it needs no scheduler.
    """
    from billing.models import RateLimitCounter

    cutoff = timezone.now() - timedelta(seconds=older_than_seconds)
    deleted, _ = RateLimitCounter.objects.filter(window_start__lt=cutoff).delete()
    return deleted
