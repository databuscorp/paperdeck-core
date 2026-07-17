import logging
import math
import os
from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from django.db.models import Sum, Count
from django.db.models.functions import TruncMonth

from billing.models import Subscription, Wallet, CreditTxn
from staff.models import Staff
from utility.dbservice import DBService
from utility.utilityobj import ErrorResponse

logger = logging.getLogger(__name__)

# AI credit packs: name -> (credits, price ₹)
PACKS = {
    'starter':    {'credits': 100,  'price': 199},
    'growth':     {'credits': 500,  'price': 899},
    'school':     {'credits': 1000, 'price': 1599},
    'enterprise': {'credits': 5000, 'price': 6999},
}

CREDIT_VALIDITY_DAYS = 365  # 12-month validity

# ── Token-based credit pricing ────────────────────────────────────────────────
# Credits are derived from ACTUAL Claude token usage so a 1-question generation
# costs a fraction of a full paper. All values are env-overridable.
USD_INR              = float(os.environ.get('USD_INR', '85'))
AI_INPUT_USD_PER_M   = float(os.environ.get('AI_INPUT_USD_PER_M', '1.0'))   # Haiku 4.5 input  ($/M tokens)
AI_OUTPUT_USD_PER_M  = float(os.environ.get('AI_OUTPUT_USD_PER_M', '5.0'))  # Haiku 4.5 output ($/M tokens)
# ₹ of raw AI cost represented by ONE credit (the cost basis). Packs sell credits
# at ₹1.40–2.00, so margin = pack_price / CREDIT_VALUE_INR. At 0.70 even the
# cheapest pack (₹1.40/credit) clears ~2×. Lower → more credits charged per ₹.
CREDIT_VALUE_INR     = float(os.environ.get('CREDIT_VALUE_INR', '0.7'))
# Extra margin multiplier applied on top, at the point of charging (1.0 = none).
# Use this to bake a buffer into every generation, independent of pack pricing.
CREDIT_MARKUP        = float(os.environ.get('CREDIT_MARKUP', '1.0'))


# Prompt caching (papers/service/aigeneratorservice.py) makes a prompt's tokens land in
# THREE buckets, not one, and they are priced very differently:
#
#   input_tokens                 the uncached remainder — full price
#   cache_read_input_tokens      served from cache      — ~0.1x input
#   cache_creation_input_tokens  written to cache       — ~1.25x input (5-minute TTL)
#
# `input_tokens` EXCLUDES the cached ones, so pricing on it alone bills a cached
# prompt as if most of it were free. It isn't — a cache read is cheap, but a cache
# WRITE costs MORE than an ordinary input token, and image-based generation writes a
# ~6.5k-token prefix. Ignoring both buckets quietly under-recovers cost on exactly the
# question type that is most expensive to produce.
CACHE_READ_MULTIPLIER  = float(os.environ.get('CACHE_READ_MULTIPLIER', '0.1'))
CACHE_WRITE_MULTIPLIER = float(os.environ.get('CACHE_WRITE_MULTIPLIER', '1.25'))


def token_cost_inr(input_tokens, output_tokens,
                   cache_read_tokens=0, cache_write_tokens=0):
    """Raw ₹ AI cost for the given Claude token usage, cache buckets included."""
    billable_input = (
        int(input_tokens or 0)
        + int(cache_read_tokens or 0) * CACHE_READ_MULTIPLIER
        + int(cache_write_tokens or 0) * CACHE_WRITE_MULTIPLIER
    )
    return ((billable_input / 1_000_000) * AI_INPUT_USD_PER_M
            + (int(output_tokens or 0) / 1_000_000) * AI_OUTPUT_USD_PER_M) * USD_INR


def compute_credits_from_tokens(input_tokens, output_tokens,
                                cache_read_tokens=0, cache_write_tokens=0):
    """Credits for a generation, prorated from real token cost (min 1 if any spend)."""
    cost = token_cost_inr(input_tokens, output_tokens,
                          cache_read_tokens, cache_write_tokens) * CREDIT_MARKUP
    if cost <= 0:
        return 0
    return max(1, math.ceil(cost / CREDIT_VALUE_INR))


def credits_for_usage(usage: dict) -> int:
    """Credits for a `last_usage` dict straight off AIGeneratorService.

    One place that knows the key names, so a caller can't quietly drop a cache bucket
    (and under-bill) just by forgetting to forward it.
    """
    usage = usage or {}
    return compute_credits_from_tokens(
        usage.get('input_tokens', 0),
        usage.get('output_tokens', 0),
        usage.get('cache_read_input_tokens', 0),
        usage.get('cache_creation_input_tokens', 0),
    )


def usage_summary(org_id=None, days=30, top_reasons=8):
    """Roll up recorded AI spend from the CreditTxn ledger for cost visibility.

    Aggregates `consume` transactions over the last `days` into per-org totals: credits
    consumed, input/output tokens, an INR cost estimate (from the persisted token counts;
    cache buckets aren't stored per-txn so this is a floor), and a breakdown by reason.
    `token_cost_inr` is linear in the token counts, so summing totals equals summing rows.

    Returns {"days", "since", "orgs": [{org_id, credits, input_tokens, output_tokens,
    inr_estimate, generations, by_reason: [{reason, credits, generations}]}]}.
    """
    since = timezone.now() - timedelta(days=days)
    qs = CreditTxn.objects.filter(kind='consume', created_at__gte=since)
    if org_id:
        qs = qs.filter(org_id=org_id)

    orgs = {}
    per_org_totals = (
        qs.values('org_id')
          .annotate(credits=Sum('delta'), input_tokens=Sum('input_tokens'),
                    output_tokens=Sum('output_tokens'), generations=Count('id'))
    )
    for row in per_org_totals:
        inp, out = int(row['input_tokens'] or 0), int(row['output_tokens'] or 0)
        orgs[row['org_id']] = {
            'org_id': row['org_id'],
            'credits': -int(row['credits'] or 0),          # delta is negative on consume
            'input_tokens': inp,
            'output_tokens': out,
            'inr_estimate': round(token_cost_inr(inp, out), 2),
            'generations': int(row['generations'] or 0),
            'by_reason': [],
        }

    # Reason breakdown, capped to the biggest few per org so the report stays readable.
    per_reason = (
        qs.values('org_id', 'reason')
          .annotate(credits=Sum('delta'), generations=Count('id'))
          .order_by('org_id', 'credits')                   # most-negative (most spend) first
    )
    for row in per_reason:
        org = orgs.get(row['org_id'])
        if org is None or len(org['by_reason']) >= top_reasons:
            continue
        org['by_reason'].append({
            'reason': row['reason'] or '(none)',
            'credits': -int(row['credits'] or 0),
            'generations': int(row['generations'] or 0),
        })

    ordered = sorted(orgs.values(), key=lambda o: o['credits'], reverse=True)
    return {'days': days, 'since': since.isoformat(), 'orgs': ordered}


def compute_credits(question_count, with_answer_key=False, versions=1):
    """Legacy tier fallback — used only when no token usage is supplied."""
    q = int(question_count or 0)
    if q <= 0:
        base = 0
    elif q <= 15:
        base = 5
    elif q <= 40:
        base = 10
    elif q <= 80:
        base = 20
    else:
        base = 20 + 10 * math.ceil((q - 80) / 40)
    extra = (5 if with_answer_key else 0) + 5 * max(0, int(versions or 1) - 1)
    return base + extra


# ── Pre-flight estimation ─────────────────────────────────────────────────────
# The real charge is ALWAYS metered after the fact, from the token usage the model
# actually reported (`compute_credits_from_tokens`). These two constants exist only
# to answer one question BEFORE any AI call is made: "can this org plausibly pay for
# what it just asked for?" — so that an org with an empty wallet is turned away
# instead of being handed free generations it can never be billed for.
#
# They are ESTIMATES, derived from how usage actually accrues: questions are produced
# in batches of ~10 per API call, so each question carries its share of the amortised
# prompt/schema/avoid-list (input) plus its own JSON body and its share of the
# answer-verification pass (output). Deliberately rounded up a little: an estimate
# that runs low lets work through that the wallet cannot cover, and the overdraft is
# then unrecoverable (see `charge_usage`).
_EST_INPUT_TOKENS_PER_QUESTION  = 350
_EST_OUTPUT_TOKENS_PER_QUESTION = 450

# A client from before server-side metering may still POST the deprecated charge
# endpoint with usage the server has already billed. A consume txn for the same org
# with the *identical* token counts inside this window is that same generation, not a
# second one — see `charge`.
_LEGACY_DUPLICATE_WINDOW = timedelta(minutes=60)


def estimated_question_count(kind, params=None):
    """How many questions a generation request will produce, for costing purposes."""
    params = params or {}
    if kind == 'questions':
        return max(0, int(params.get('count') or 0))

    # A paper's size is decided by the planner (blueprint sections when given, else the
    # exam config, else a per-subject default) — ask it rather than re-deriving the same
    # rules here and drifting out of sync with them.
    try:
        from papers.service.aigeneratorservice import AIGeneratorService
        # __new__, not __init__: planning is pure and needs no Anthropic client/API key.
        planner = AIGeneratorService.__new__(AIGeneratorService)
        plans = planner.plan_paper(
            params.get('exam_type') or '',
            params.get('subjects') or [],
            params.get('difficulty') or 'medium',
            params.get('blueprint'),
        )
        return sum(max(0, int(p.get('count') or 0)) for p in plans)
    except Exception:
        logger.exception('Could not plan paper for pre-flight estimate; assuming unknown size')
        return 0


def estimate_credits(kind, params=None, count=None):
    """Estimated credits for a generation, for the PRE-FLIGHT GUARD ONLY.

    Never used to bill: the wallet is debited from real token usage once the work is
    done. Returns 0 only when there is nothing to generate.
    """
    n = int(count) if count is not None else estimated_question_count(kind, params)
    if n <= 0:
        return 0
    return compute_credits_from_tokens(n * _EST_INPUT_TOKENS_PER_QUESTION,
                                       n * _EST_OUTPUT_TOKENS_PER_QUESTION)


def cost_rules():
    return {
        'mode': 'token-based',
        'credit_value_inr': CREDIT_VALUE_INR,
        'note': 'AI credits are charged on actual usage per generation (a short quiz costs far less than a full paper).',
    }


class BillingService(DBService):
    def __init__(self, scope):
        super().__init__(scope)

    def _wallet(self, org_id) -> Wallet:
        wallet, _ = Wallet.objects.get_or_create(org_id=org_id)
        return wallet

    def _subscription(self, org_id) -> Subscription:
        sub, _ = Subscription.objects.get_or_create(org_id=org_id)
        return sub

    def _txn_dict(self, t: CreditTxn):
        return {
            'id': t.id, 'delta': t.delta, 'kind': t.kind, 'reason': t.reason,
            'balance_after': t.balance_after,
            'expires_at': t.expires_at.isoformat() if t.expires_at else None,
            'created_at': t.created_at.isoformat(),
        }

    def usage(self, org_id):
        all_txns = CreditTxn.objects.filter(org_id=org_id)
        purchased = all_txns.filter(kind='purchase').aggregate(s=Sum('delta'))['s'] or 0
        consumed = -(all_txns.filter(kind='consume').aggregate(s=Sum('delta'))['s'] or 0)
        generations = all_txns.filter(kind='consume').count()
        monthly = []
        rows = (all_txns.filter(kind='consume')
                .annotate(m=TruncMonth('created_at'))
                .values('m')
                .annotate(c=Sum('delta'), n=Count('id'))
                .order_by('-m')[:6])
        for r in rows:
            monthly.append({
                'month': r['m'].strftime('%b %Y') if r['m'] else '',
                'consumed': -(r['c'] or 0),
                'generations': r['n'],
            })
        return {
            'total_purchased': purchased,
            'total_consumed': consumed,
            'generations': generations,
            'monthly': monthly,  # most-recent first
        }

    def status(self, org_id):
        sub = self._subscription(org_id)
        wallet = self._wallet(org_id)
        staff_count = Staff.objects.filter(org_id=org_id).count()
        txns = CreditTxn.objects.filter(org_id=org_id)[:20]
        return {
            'subscription': {
                'status': sub.status,
                'per_staff_rate': sub.per_staff_rate,
                'staff_count': staff_count,
                'monthly_amount': staff_count * sub.per_staff_rate,
            },
            'wallet': {'balance': wallet.balance},
            'usage': self.usage(org_id),
            'packs': [{'id': k, **v} for k, v in PACKS.items()],
            'cost_rules': cost_rules(),
            'transactions': [self._txn_dict(t) for t in txns],
        }

    def buy(self, org_id, pack, user_id=None):
        spec = PACKS.get((pack or '').lower())
        if not spec:
            return ErrorResponse(status=400, message='Unknown credit pack')
        wallet = self._wallet(org_id)
        wallet.balance += spec['credits']
        wallet.save(update_fields=['balance', 'updated_at'])
        CreditTxn.objects.create(
            org_id=org_id, delta=spec['credits'], kind='purchase',
            reason=f"{pack.title()} pack (₹{spec['price']})",
            balance_after=wallet.balance,
            expires_at=timezone.now() + timedelta(days=CREDIT_VALIDITY_DAYS),
        )
        return {'balance': wallet.balance, 'credits_added': spec['credits']}

    # ── Pre-flight gate ───────────────────────────────────────────────────────
    # AI generation costs real money the moment it runs, so it is gated BEFORE the
    # first token is spent. Previously nothing checked the balance at all and the
    # frontend was trusted to report usage afterwards — an org with an empty wallet
    # (or a client that simply never called the charge endpoint) generated for free.

    def can_afford(self, org_id, estimated_credits) -> bool:
        """True if the org's wallet covers `estimated_credits`."""
        if not org_id:
            # No org → no wallet exists to meter against (legacy single-user accounts).
            # Metering is an org-level concept; nothing to enforce.
            return True
        return self._wallet(org_id).balance >= max(0, int(estimated_credits or 0))

    def preflight(self, org_id, kind, params=None, count=None):
        """Guard a generation before any AI call. Returns an ErrorResponse to refuse
        (402 Payment Required / 403 for an inactive subscription), or None to proceed.

        The number is an ESTIMATE (see `estimate_credits`) — the wallet is debited from
        the real token usage once the work completes.
        """
        if not org_id:
            return None

        sub = self._subscription(org_id)
        if sub.status != 'active':
            return ErrorResponse(
                status=403,
                message='Subscription is not active. Reactivate it to generate with AI.',
            )

        # Any AI generation costs at least one credit, so an empty wallet is refused
        # even when the size of the request can't be planned up front.
        needed = max(1, estimate_credits(kind, params, count))
        wallet = self._wallet(org_id)
        if wallet.balance < needed:
            return ErrorResponse(
                status=402,
                message=(f'Insufficient AI credits — this generation needs about {needed} '
                         f'credit(s) and your wallet has {wallet.balance}. Top up your wallet to continue.'),
            )
        return None

    # ── Metered charge (server-side, authoritative) ───────────────────────────

    def charge_usage(self, org_id, input_tokens=0, output_tokens=0, reason='', ref=None,
                     cache_read_tokens=0, cache_write_tokens=0):
        """Debit the wallet for a COMPLETED generation, from its real token usage.

        This is the only place generations are billed. It is called server-side, right
        where the work finishes, so billing no longer depends on the client choosing to
        report it.

        Idempotent: `ref` (e.g. "job:123") is a unique column on CreditTxn, so a retried
        job — or a legacy client charging the same work again — is a no-op. The wallet row
        is locked FOR UPDATE first, which serialises concurrent charges for the same org
        and makes the "already charged?" check race-safe.

        Never overdrafts: if actual usage exceeds what the wallet holds, we take what is
        there, record the shortfall on the txn, and warn. The AI spend has already
        happened — refusing to record it would only lose the money twice.
        """
        if not org_id:
            return {'charged': 0, 'balance': 0, 'skipped': 'no-org'}

        cost = compute_credits_from_tokens(input_tokens, output_tokens,
                                           cache_read_tokens, cache_write_tokens)

        with transaction.atomic():
            Wallet.objects.get_or_create(org_id=org_id)
            wallet = Wallet.objects.select_for_update().get(org_id=org_id)

            if ref:
                existing = CreditTxn.objects.filter(ref=ref).first()
                if existing:
                    return {'charged': -existing.delta, 'balance': wallet.balance,
                            'already_charged': True}

            if cost <= 0:
                return {'charged': 0, 'balance': wallet.balance}

            deducted = min(cost, max(0, wallet.balance))
            shortfall = cost - deducted
            text = (reason or 'AI generation')
            if shortfall > 0:
                text = f'{text} — {shortfall} credit(s) unbilled (wallet exhausted)'
                logger.warning(
                    'Wallet overdraft avoided for org %s (ref=%s): usage cost %s credits, '
                    'only %s available; %s credit(s) written off.',
                    org_id, ref, cost, deducted, shortfall,
                )

            wallet.balance -= deducted
            wallet.save(update_fields=['balance', 'updated_at'])
            CreditTxn.objects.create(
                org_id=org_id, delta=-deducted, kind='consume',
                reason=text[:255], balance_after=wallet.balance, ref=ref,
                input_tokens=int(input_tokens or 0), output_tokens=int(output_tokens or 0),
            )
            return {'charged': deducted, 'balance': wallet.balance, 'shortfall': shortfall}

    def charge(self, org_id, input_tokens=0, output_tokens=0, question_count=0,
               with_answer_key=False, versions=1, title='', ref=None):
        """DEPRECATED — the client-driven charge.

        Generations are now metered and charged server-side (`charge_usage`), because
        trusting the client to call this was trusting it to bill itself: a client that
        just never made the call was never billed. It is kept only so an older frontend,
        still POSTing /api/billing/charge/ after a generation, keeps working through the
        rollout — and it must NOT double-charge work the server already billed:

          * `ref` given and already charged → no-op.
          * token usage that exactly matches a consume txn recorded for this org in the
            last `_LEGACY_DUPLICATE_WINDOW` → that IS the server-side charge for this same
            generation (identical input+output token counts do not recur by chance), so it
            is a no-op. Erring toward not billing twice is the right way to be wrong.

        Remove once no deployed client calls this.
        """
        sub = self._subscription(org_id)
        if sub.status != 'active':
            return ErrorResponse(status=403, message='Subscription is not active.')

        in_tok, out_tok = int(input_tokens or 0), int(output_tokens or 0)
        token_mode = (in_tok + out_tok) > 0

        if ref and CreditTxn.objects.filter(ref=ref).exists():
            return {'charged': 0, 'balance': self._wallet(org_id).balance,
                    'already_charged': True, 'deprecated': True}

        if token_mode:
            already = CreditTxn.objects.filter(
                org_id=org_id, kind='consume',
                input_tokens=in_tok, output_tokens=out_tok,
                created_at__gte=timezone.now() - _LEGACY_DUPLICATE_WINDOW,
            ).exists()
            if already:
                return {'charged': 0, 'balance': self._wallet(org_id).balance,
                        'already_charged': True, 'deprecated': True}
            # Not metered server-side (e.g. an AI path this endpoint still fronts) — bill it,
            # through the same idempotent, non-overdrafting code path as everything else.
            resp = self.charge_usage(org_id, in_tok, out_tok,
                                     reason=(title or 'AI generation'), ref=ref)
            resp['deprecated'] = True
            return resp

        # Legacy tier fallback: no usage supplied, so price off the question count. This
        # path never ran an AI call through us, so it may still reject up front.
        cost = compute_credits(question_count, with_answer_key, versions)
        wallet = self._wallet(org_id)
        if cost <= 0:
            return {'charged': 0, 'balance': wallet.balance, 'deprecated': True}
        if wallet.balance < cost:
            return ErrorResponse(
                status=402,
                message=f'Insufficient AI credits — need {cost}, you have {wallet.balance}. Top up your wallet.',
            )
        with transaction.atomic():
            wallet = Wallet.objects.select_for_update().get(org_id=org_id)
            deducted = min(cost, max(0, wallet.balance))
            wallet.balance -= deducted
            wallet.save(update_fields=['balance', 'updated_at'])
            CreditTxn.objects.create(
                org_id=org_id, delta=-deducted, kind='consume',
                reason=(title or 'Paper generation')[:255],
                balance_after=wallet.balance, ref=ref,
            )
        return {'charged': deducted, 'balance': wallet.balance, 'deprecated': True}
