from django.db import models


class Subscription(models.Model):
    """Per-staff platform subscription (₹/staff/month). Separate from AI credits."""
    org            = models.OneToOneField('users.Organization', on_delete=models.CASCADE, related_name='subscription')
    per_staff_rate = models.IntegerField(default=100)            # ₹ per staff per month
    status         = models.CharField(max_length=20, default='active')  # active | inactive
    created_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'pd_subscriptions'


class Wallet(models.Model):
    """Org-level AI credit wallet, shared by all staff."""
    org        = models.OneToOneField('users.Organization', on_delete=models.CASCADE, related_name='wallet')
    balance    = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'pd_wallets'


class CreditTxn(models.Model):
    """Append-only ledger of credit movements."""
    org           = models.ForeignKey('users.Organization', on_delete=models.CASCADE, related_name='credit_txns')
    delta         = models.IntegerField()                       # +purchase, -consume
    kind          = models.CharField(max_length=20)             # purchase | consume | adjust
    reason        = models.CharField(max_length=255, blank=True, default='')
    balance_after = models.IntegerField(default=0)
    expires_at    = models.DateTimeField(null=True, blank=True)  # for purchase lots (12-month validity)
    created_at    = models.DateTimeField(auto_now_add=True)

    # Idempotency key for a metered charge, e.g. "job:123" / "paper:45". A unit of AI
    # work is charged AT MOST ONCE: the debit is keyed on this, so a retried background
    # job — or a legacy client still POSTing /api/billing/charge/ for work the server
    # already metered — cannot double-debit the wallet. NULL for purchases and for
    # legacy client-driven charges; Postgres treats every NULL as distinct, so the
    # unique constraint does not collide across them.
    ref           = models.CharField(max_length=64, unique=True, null=True, blank=True, default=None)
    # The raw Claude usage this charge was metered from — audit trail, and what lets the
    # deprecated client endpoint recognise a charge it would otherwise duplicate.
    input_tokens  = models.IntegerField(default=0)
    output_tokens = models.IntegerField(default=0)

    class Meta:
        db_table = 'pd_credit_txns'
        ordering = ['-created_at']


class RateLimitCounter(models.Model):
    """A fixed-window request counter, in Postgres rather than in memory.

    An in-process counter (Django's default LocMemCache, a module-level dict) would be
    worthless here: generation runs under multiple gunicorn workers and the App Service
    plan can scale out, so each process would keep its own count and the effective limit
    would silently multiply by the number of workers. The counter has to be shared, and
    Postgres is already the shared thing this deployment has — the same reason
    GenerationJob lives there.

    Fixed window, not a sliding one: a client can burst up to 2x the limit across a
    window boundary. That is a deliberate trade. This exists to stop a runaway loop or a
    scripted abuser from draining an org's wallet and our rate limit at Anthropic, and a
    fixed window does that with one indexed upsert per request. Precision at the
    boundary is not worth a sorted-set structure we would have to add Redis for.
    """
    key          = models.CharField(max_length=200)   # e.g. "paper_generate:org:12"
    window_start = models.DateTimeField()
    count        = models.IntegerField(default=0)

    class Meta:
        db_table = 'pd_rate_limit_counters'
        # The upsert relies on this: concurrent first-requests in the same window race to
        # INSERT, and exactly one wins while the rest fall through to an atomic UPDATE.
        unique_together = ('key', 'window_start')
        indexes = [models.Index(fields=['window_start'])]

    def __str__(self):
        return f'{self.key}@{self.window_start:%Y-%m-%d %H:%M} = {self.count}'
