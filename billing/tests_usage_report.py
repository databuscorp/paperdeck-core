"""Tests for the AI-spend rollup (usage_summary) and the per-phase usage split."""
from datetime import timedelta
from types import SimpleNamespace

from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from billing.models import CreditTxn, Wallet
from billing.service.billingservice import usage_summary
from papers.service.aigeneratorservice import AIGeneratorService
from users.models import Organization


def _msg(inp, out):
    return SimpleNamespace(usage=SimpleNamespace(
        input_tokens=inp, output_tokens=out,
        cache_creation_input_tokens=0, cache_read_input_tokens=0))


class UsageByPhaseTests(SimpleTestCase):

    def test_add_usage_splits_by_phase_and_totals(self):
        g = AIGeneratorService()
        g._add_usage(_msg(100, 50))                            # default: generation
        g._add_usage(_msg(20, 10), phase='answer_verify')
        g._add_usage(_msg(5, 2), phase='diagram_verify')
        self.assertEqual(g.last_usage['input_tokens'], 125)    # total
        self.assertEqual(g.last_usage['output_tokens'], 62)
        self.assertEqual(g.usage_by_phase['generation']['input_tokens'], 100)
        self.assertEqual(g.usage_by_phase['answer_verify']['output_tokens'], 10)
        self.assertEqual(g.usage_by_phase['diagram_verify']['input_tokens'], 5)

    def test_reset_clears_phase_buckets(self):
        g = AIGeneratorService()
        g._add_usage(_msg(1, 1), phase='answer_verify')
        g._reset_usage()
        self.assertEqual(g.usage_by_phase, {})
        self.assertEqual(g.last_usage['input_tokens'], 0)


class UsageSummaryTests(TestCase):

    def setUp(self):
        self.org = Organization.objects.create(name='Acme Coaching')
        Wallet.objects.create(org=self.org, balance=1000)

    def _consume(self, credits, inp, out, reason):
        CreditTxn.objects.create(
            org=self.org, delta=-credits, kind='consume', reason=reason,
            balance_after=0, input_tokens=inp, output_tokens=out)

    def test_rolls_up_per_org_totals(self):
        self._consume(10, 50_000, 10_000, 'Question generation: 5 × MCQ (Physics)')
        self._consume(6, 30_000, 6_000, 'Paper generation')
        summary = usage_summary(days=30)
        org = next(o for o in summary['orgs'] if o['org_id'] == self.org.id)
        self.assertEqual(org['credits'], 16)
        self.assertEqual(org['input_tokens'], 80_000)
        self.assertEqual(org['output_tokens'], 16_000)
        self.assertEqual(org['generations'], 2)
        self.assertGreater(org['inr_estimate'], 0)

    def test_reason_breakdown_present(self):
        self._consume(10, 1, 1, 'Question generation')
        self._consume(3, 1, 1, 'Paper generation')
        summary = usage_summary(org_id=self.org.id, days=30)
        reasons = {r['reason'] for r in summary['orgs'][0]['by_reason']}
        self.assertIn('Question generation', reasons)
        self.assertIn('Paper generation', reasons)

    def test_window_excludes_old_txns(self):
        self._consume(10, 1, 1, 'old')
        CreditTxn.objects.filter(org=self.org).update(
            created_at=timezone.now() - timedelta(days=90))
        summary = usage_summary(days=30)
        self.assertEqual(summary['orgs'], [])
