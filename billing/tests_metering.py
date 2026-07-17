"""Server-side metering tests.

Billing used to be trust-the-client: the generation endpoints handed the browser a token
`usage` blob and the browser was expected to POST /api/billing/charge/ itself. A client
that simply never made that call was never billed, and nothing checked the wallet before
running the generation, so an org with zero credits could generate forever.

These tests pin the fix: work is refused when the org can't pay, and it is charged
server-side, exactly once, without ever overdrafting the wallet.

No real Anthropic calls are made — the generator is faked throughout.
"""
import json

from django.test import TestCase
from rest_framework_simplejwt.tokens import AccessToken

import papers.service.aigeneratorservice as ai
from billing.models import CreditTxn, Subscription, Wallet
from billing.service.billingservice import (
    BillingService, compute_credits_from_tokens, estimate_credits,
)
from papers.models import GenerationJob, Paper
from papers.service import jobservice
from papers.service.paperservice import PaperService
from users.models import Organization, User
from utility.utilityobj import ErrorResponse


class _FakeGenerator:
    """Stands in for AIGeneratorService: produces a tiny paper / question set and
    reports token usage, without ever touching the network."""

    #  Bumped by every instance that actually generates, so a test can assert the AI was
    #  never called when the pre-flight gate refused the request.
    calls = 0
    usage = {'input_tokens': 20_000, 'output_tokens': 20_000}

    def __init__(self):
        self.last_usage = {'input_tokens': 0, 'output_tokens': 0}

    def _spend(self):
        type(self).calls += 1
        self.last_usage = dict(type(self).usage)

    # **kw so a new generator option (language, …) doesn't break every billing test.
    def generate_paper(self, exam_type='', subjects=None, difficulty='medium',
                       total_marks=0, blueprint=None, progress=None, verify=True, **kw):
        self._spend()
        return {
            'exam_type': exam_type,
            'total_marks': total_marks,
            'sections': [{
                'subject': 'Physics',
                'questions': [{
                    'text': 'A body of mass m moves with velocity v. Find its momentum.',
                    'marks': 4, 'correct_answer': 'A',
                    'options': ['A) mv', 'B) mv^2', 'C) m/v', 'D) v/m'],
                }],
            }],
        }

    def generate_questions(self, exam='', subject='', topic='', q_type='MCQ',
                           difficulty='Mixed', bloom='Mixed', count=1, **kw):
        self._spend()
        return [{'text': f'Q{i}', 'options': ['A) x', 'B) y'], 'correct_answer': 'A',
                 'marks': 4} for i in range(count)]


class _Req:
    """The paper-generation request object PaperService.generate_paper consumes."""

    def __init__(self, **kw):
        self.title = kw.get('title', 'Mock Test')
        self.exam_type = kw.get('exam_type', 'JEE Mains')
        self.subjects = kw.get('subjects', ['Physics'])
        self.difficulty = kw.get('difficulty', 'medium')
        self.total_marks = kw.get('total_marks', 120)
        self.duration_minutes = kw.get('duration_minutes', 180)
        self.instructions = kw.get('instructions', '')
        self.course_id = kw.get('course_id')
        self.blueprint_id = kw.get('blueprint_id')


class MeteringTestCase(TestCase):
    """Shared fixtures: an org with a wallet, a user, and a faked generator."""

    def setUp(self):
        _FakeGenerator.calls = 0
        _FakeGenerator.usage = {'input_tokens': 20_000, 'output_tokens': 20_000}

        self.org = Organization.objects.create(name='Acme Coaching')
        self.user = User.objects.create(username='t@example.com', email='t@example.com',
                                        org=self.org)
        Subscription.objects.create(org=self.org, status='active')
        self.wallet = Wallet.objects.create(org=self.org, balance=0)

        # Every construction of AIGeneratorService yields the fake instead. Each consumer
        # is patched by the name IT imported at module load — patching only the defining
        # module would leave these bindings on the real client and the tests would make
        # live Anthropic calls. `aigeneratorservice` itself is deliberately left alone, so
        # the pre-flight estimate still goes through the real (pure, network-free) planner.
        import papers.service.paperservice as ps
        import questions.controller.questioncontroller as qc
        self._patched = [ps, qc, jobservice]
        self._originals = [m.AIGeneratorService for m in self._patched]
        for m in self._patched:
            m.AIGeneratorService = _FakeGenerator

    def tearDown(self):
        for m, original in zip(self._patched, self._originals):
            m.AIGeneratorService = original

    def _fund(self, credits):
        Wallet.objects.filter(org=self.org).update(balance=credits)
        self.wallet.refresh_from_db()

    def _balance(self):
        self.wallet.refresh_from_db()
        return self.wallet.balance

    def _auth(self):
        return {'HTTP_AUTHORIZATION': f'Bearer {AccessToken.for_user(self.user)}'}

    def _scope(self):
        return {'scope': 'default', 'user_id': self.user.id, 'org_id': self.org.id, 'role': 1}

    def _job(self, kind=GenerationJob.KIND_PAPER, paper=None):
        return GenerationJob.objects.create(
            owner=self.user, org=self.org, paper=paper, kind=kind,
            params={'exam_type': 'JEE Mains', 'subjects': ['Physics'], 'difficulty': 'medium',
                    'total_marks': 120, 'title': 'Mock Test', 'count': 5},
            status=GenerationJob.STATUS_QUEUED)


class PreflightGateTests(MeteringTestCase):
    """An org that can't pay must be turned away BEFORE any AI spend."""

    def test_estimate_scales_with_question_count(self):
        small = estimate_credits('questions', count=5)
        large = estimate_credits('questions', count=180)
        self.assertGreaterEqual(small, 1)
        self.assertGreater(large, small)
        self.assertEqual(estimate_credits('questions', count=0), 0)

    def test_paper_estimate_comes_from_the_planner(self):
        """The paper's size is whatever the planner will actually generate, so the guard
        must price a 30-question JEE Physics paper well above the 1-credit floor."""
        est = estimate_credits('paper', {'exam_type': 'JEE Mains', 'subjects': ['Physics'],
                                         'difficulty': 'medium'})
        self.assertGreater(est, 1)

    def test_partially_funded_wallet_is_still_refused(self):
        """Not just the empty-wallet case: a wallet that can't cover the estimate is a 402,
        which is what proves the guard is pricing the request rather than waving it through."""
        est = estimate_credits('paper', {'exam_type': 'JEE Mains', 'subjects': ['Physics'],
                                         'difficulty': 'medium'})
        self._fund(est - 1)
        resp = PaperService(self._scope()).generate_paper(_Req(), self.user.id, org_id=self.org.id)
        self.assertIsInstance(resp, ErrorResponse)
        self.assertEqual(resp.status, 402)
        self.assertEqual(_FakeGenerator.calls, 0)

    def test_paper_generation_rejected_with_402_before_any_ai_call(self):
        self._fund(0)
        resp = PaperService(self._scope()).generate_paper(_Req(), self.user.id, org_id=self.org.id)

        self.assertIsInstance(resp, ErrorResponse)
        self.assertEqual(resp.status, 402)
        self.assertIn('credit', resp.message.lower())
        # The whole point: the model was never called, and no draft was left behind.
        self.assertEqual(_FakeGenerator.calls, 0)
        self.assertEqual(Paper.objects.count(), 0)
        self.assertEqual(CreditTxn.objects.count(), 0)

    def test_async_paper_generation_rejected_before_enqueue(self):
        self._fund(0)
        resp = PaperService(self._scope()).generate_paper_async(_Req(), self.user.id,
                                                                org_id=self.org.id)
        self.assertIsInstance(resp, ErrorResponse)
        self.assertEqual(resp.status, 402)
        self.assertEqual(GenerationJob.objects.count(), 0)
        self.assertEqual(Paper.objects.count(), 0)
        self.assertEqual(_FakeGenerator.calls, 0)

    def test_question_generation_endpoint_returns_402(self):
        self._fund(0)
        resp = self.client.post(
            '/api/questions/generate/',
            data=json.dumps({'exam': 'JEE Mains', 'subject': 'Physics', 'topic': 'Optics',
                             'q_type': 'MCQ', 'difficulty': 'Hard', 'bloom': 'Apply',
                             'count': 10}),
            content_type='application/json', **self._auth())

        self.assertEqual(resp.status_code, 402)
        self.assertEqual(_FakeGenerator.calls, 0)

    def test_funded_org_is_allowed_through(self):
        self._fund(500)
        resp = PaperService(self._scope()).generate_paper(_Req(), self.user.id, org_id=self.org.id)
        self.assertNotIsInstance(resp, ErrorResponse)
        self.assertEqual(_FakeGenerator.calls, 1)

    def test_inactive_subscription_is_refused(self):
        self._fund(500)
        Subscription.objects.filter(org=self.org).update(status='inactive')
        resp = PaperService(self._scope()).generate_paper(_Req(), self.user.id, org_id=self.org.id)
        self.assertIsInstance(resp, ErrorResponse)
        self.assertEqual(resp.status, 403)
        self.assertEqual(_FakeGenerator.calls, 0)

    def test_can_afford(self):
        svc = BillingService(self._scope())
        self._fund(10)
        self.assertTrue(svc.can_afford(self.org.id, 10))
        self.assertFalse(svc.can_afford(self.org.id, 11))
        # No org → no wallet → nothing to meter (legacy single-user accounts).
        self.assertTrue(svc.can_afford(None, 9999))


class ServerSideChargeTests(MeteringTestCase):
    """The server bills the work; the client is not trusted to do it."""

    def test_completed_job_debits_the_wallet_exactly_once(self):
        self._fund(500)
        paper = Paper.objects.create(owner=self.user, org=self.org, title='Mock Test',
                                     exam_type='JEE Mains', subjects=['Physics'],
                                     total_marks=120, status=Paper.STATUS_DRAFT, source='ai')
        job = self._job(paper=paper)

        jobservice.run_job(job.id)

        job.refresh_from_db()
        self.assertEqual(job.status, GenerationJob.STATUS_DONE)

        expected = compute_credits_from_tokens(20_000, 20_000)
        self.assertGreater(expected, 0)

        txns = CreditTxn.objects.filter(org=self.org, kind='consume')
        self.assertEqual(txns.count(), 1)
        self.assertEqual(txns.first().delta, -expected)
        self.assertEqual(txns.first().ref, f'job:{job.id}')
        self.assertEqual(self._balance(), 500 - expected)

    def test_synchronous_paper_generation_charges_in_request(self):
        self._fund(500)
        PaperService(self._scope()).generate_paper(_Req(), self.user.id, org_id=self.org.id)

        expected = compute_credits_from_tokens(20_000, 20_000)
        txn = CreditTxn.objects.get(org=self.org, kind='consume')
        self.assertEqual(txn.delta, -expected)
        self.assertTrue(txn.ref.startswith('paper:'))
        self.assertEqual(self._balance(), 500 - expected)

    def test_synchronous_question_generation_charges_in_request(self):
        self._fund(500)
        resp = self.client.post(
            '/api/questions/generate/',
            data=json.dumps({'exam': 'JEE Mains', 'subject': 'Physics', 'topic': 'Optics',
                             'q_type': 'MCQ', 'difficulty': 'Hard', 'bloom': 'Apply',
                             'count': 5}),
            content_type='application/json', **self._auth())

        self.assertEqual(resp.status_code, 200)
        expected = compute_credits_from_tokens(20_000, 20_000)
        body = json.loads(resp.content)
        self.assertEqual(body['charged'], expected)
        self.assertEqual(CreditTxn.objects.filter(org=self.org, kind='consume').count(), 1)
        self.assertEqual(self._balance(), 500 - expected)

    def test_charge_is_skipped_when_there_is_no_org(self):
        """Legacy org-less accounts have no wallet to meter — they must not blow up."""
        res = BillingService({}).charge_usage(None, 1000, 1000, ref='job:999')
        self.assertEqual(res['charged'], 0)
        self.assertEqual(CreditTxn.objects.count(), 0)


class IdempotencyTests(MeteringTestCase):
    """A unit of work is charged at most once, however many times we're asked."""

    def test_same_ref_charged_twice_debits_once(self):
        self._fund(500)
        svc = BillingService(self._scope())
        cost = compute_credits_from_tokens(20_000, 20_000)

        first = svc.charge_usage(self.org.id, 20_000, 20_000, ref='job:42')
        second = svc.charge_usage(self.org.id, 20_000, 20_000, ref='job:42')

        self.assertEqual(first['charged'], cost)
        self.assertTrue(second.get('already_charged'))
        self.assertEqual(CreditTxn.objects.filter(kind='consume').count(), 1)
        self.assertEqual(self._balance(), 500 - cost)

    def test_rerunning_a_job_does_not_double_debit(self):
        self._fund(500)
        paper = Paper.objects.create(owner=self.user, org=self.org, title='Mock Test',
                                     exam_type='JEE Mains', subjects=['Physics'],
                                     total_marks=120, status=Paper.STATUS_DRAFT, source='ai')
        job = self._job(paper=paper)

        jobservice.run_job(job.id)      # first run
        jobservice.run_job(job.id)      # a retry after, say, a worker restart

        cost = compute_credits_from_tokens(20_000, 20_000)
        self.assertEqual(CreditTxn.objects.filter(kind='consume').count(), 1)
        self.assertEqual(self._balance(), 500 - cost)

    def test_deprecated_client_endpoint_does_not_double_charge_a_server_charged_job(self):
        """The old frontend still POSTs the usage it was handed. It must be a no-op."""
        self._fund(500)
        job = self._job()
        jobservice.run_job(job.id)

        cost = compute_credits_from_tokens(20_000, 20_000)
        after_server_charge = self._balance()
        self.assertEqual(after_server_charge, 500 - cost)

        # (a) a client that knows the job id
        resp = self.client.post(
            '/api/billing/charge/',
            data=json.dumps({'job_id': job.id, 'input_tokens': 20_000,
                             'output_tokens': 20_000, 'title': 'Mock Test'}),
            content_type='application/json', **self._auth())
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(json.loads(resp.content)['charged'], 0)
        self.assertEqual(self._balance(), after_server_charge)

        # (b) the current frontend, which only echoes back the usage blob
        resp = self.client.post(
            '/api/billing/charge/',
            data=json.dumps({'input_tokens': 20_000, 'output_tokens': 20_000,
                             'title': 'Mock Test'}),
            content_type='application/json', **self._auth())
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(json.loads(resp.content)['charged'], 0)
        self.assertEqual(self._balance(), after_server_charge)
        self.assertEqual(CreditTxn.objects.filter(kind='consume').count(), 1)

    def test_deprecated_endpoint_still_bills_work_the_server_did_not_meter(self):
        """Paper import is still fronted by this endpoint — it must keep charging."""
        self._fund(500)
        resp = self.client.post(
            '/api/billing/charge/',
            data=json.dumps({'input_tokens': 9_133, 'output_tokens': 4_271,
                             'title': 'Paper import'}),
            content_type='application/json', **self._auth())

        self.assertEqual(resp.status_code, 200)
        charged = json.loads(resp.content)['charged']
        self.assertEqual(charged, compute_credits_from_tokens(9_133, 4_271))
        self.assertGreater(charged, 0)
        self.assertEqual(self._balance(), 500 - charged)


class OverdraftTests(MeteringTestCase):
    """The wallet must never go negative, even when actual usage beats the estimate."""

    def test_usage_beyond_the_estimate_never_overdrafts(self):
        self._fund(2)   # enough to pass the pre-flight guard for a small job…
        svc = BillingService(self._scope())
        # …but the model burned far more than estimated.
        res = svc.charge_usage(self.org.id, 5_000_000, 5_000_000, reason='Runaway paper',
                               ref='job:77')

        cost = compute_credits_from_tokens(5_000_000, 5_000_000)
        self.assertGreater(cost, 2)
        self.assertEqual(res['charged'], 2)
        self.assertEqual(res['shortfall'], cost - 2)
        self.assertEqual(self._balance(), 0)

        txn = CreditTxn.objects.get(ref='job:77')
        self.assertEqual(txn.delta, -2)
        self.assertEqual(txn.balance_after, 0)
        self.assertIn('unbilled', txn.reason)   # the shortfall is on the record

    def test_charging_an_empty_wallet_leaves_it_at_zero(self):
        self._fund(0)
        BillingService(self._scope()).charge_usage(self.org.id, 100_000, 100_000,
                                                   ref='job:78')
        self.assertEqual(self._balance(), 0)
        self.assertGreaterEqual(self.wallet.balance, 0)

    def test_a_job_that_outruns_its_estimate_drains_no_further_than_zero(self):
        _FakeGenerator.usage = {'input_tokens': 4_000_000, 'output_tokens': 4_000_000}
        self._fund(3)
        job = self._job()

        jobservice.run_job(job.id)

        job.refresh_from_db()
        self.assertEqual(job.status, GenerationJob.STATUS_DONE)  # work is delivered
        self.assertEqual(self._balance(), 0)                     # but never below zero
        self.assertEqual(CreditTxn.objects.get(ref=f'job:{job.id}').delta, -3)
