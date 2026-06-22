import math
import os
from datetime import timedelta

from django.utils import timezone
from django.db.models import Sum, Count
from django.db.models.functions import TruncMonth

from billing.models import Subscription, Wallet, CreditTxn
from staff.models import Staff
from utility.dbservice import DBService
from utility.utilityobj import ErrorResponse

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


def token_cost_inr(input_tokens, output_tokens):
    """Raw ₹ AI cost for the given Claude token usage."""
    return ((int(input_tokens or 0) / 1_000_000) * AI_INPUT_USD_PER_M
            + (int(output_tokens or 0) / 1_000_000) * AI_OUTPUT_USD_PER_M) * USD_INR


def compute_credits_from_tokens(input_tokens, output_tokens):
    """Credits for a generation, prorated from real token cost (min 1 if any spend)."""
    cost = token_cost_inr(input_tokens, output_tokens) * CREDIT_MARKUP
    if cost <= 0:
        return 0
    return max(1, math.ceil(cost / CREDIT_VALUE_INR))


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

    def charge(self, org_id, input_tokens=0, output_tokens=0, question_count=0,
               with_answer_key=False, versions=1, title=''):
        sub = self._subscription(org_id)
        if sub.status != 'active':
            return ErrorResponse(status=403, message='Subscription is not active.')

        token_mode = (int(input_tokens or 0) + int(output_tokens or 0)) > 0
        cost = (compute_credits_from_tokens(input_tokens, output_tokens) if token_mode
                else compute_credits(question_count, with_answer_key, versions))

        wallet = self._wallet(org_id)
        if cost <= 0:
            return {'charged': 0, 'balance': wallet.balance}

        if token_mode:
            # Generation already happened — never reject; deduct what's available.
            deducted = min(cost, max(0, wallet.balance))
        else:
            if wallet.balance < cost:
                return ErrorResponse(
                    status=402,
                    message=f'Insufficient AI credits — need {cost}, you have {wallet.balance}. Top up your wallet.',
                )
            deducted = cost

        wallet.balance -= deducted
        wallet.save(update_fields=['balance', 'updated_at'])
        CreditTxn.objects.create(
            org_id=org_id, delta=-deducted, kind='consume',
            reason=(title or 'Paper generation')[:255],
            balance_after=wallet.balance,
        )
        return {'charged': deducted, 'balance': wallet.balance}
