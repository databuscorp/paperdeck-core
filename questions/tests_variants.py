"""Parametric variant generation — "give me N variants of this question".

Two things are pinned here:

  * generate_variants drives the SAME tool-use → validate → verify pipeline a normal
    batch does, so a variant is held to the same standard. Exercised with a FAKE client
    so no network is touched.
  * the /api/questions/variants/ endpoint gates on the wallet BEFORE generating and
    charges from real token usage AFTER — billing is server-side, never the client's job.
"""
import json
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase
from rest_framework_simplejwt.tokens import AccessToken

from papers.service.aigeneratorservice import AIGeneratorService


# ── Fakes (no network) ────────────────────────────────────────────────────────
class _FakeUsage:
    def __init__(self, **kw):
        self.input_tokens = kw.get('input_tokens', 0)
        self.output_tokens = kw.get('output_tokens', 0)
        self.cache_creation_input_tokens = kw.get('cache_creation_input_tokens', 0)
        self.cache_read_input_tokens = kw.get('cache_read_input_tokens', 0)


class _FakeToolBlock:
    type = "tool_use"

    def __init__(self, questions):
        # Matches the shape _extract_tool_questions reads: block.input['questions'].
        self.input = {"questions": questions}


class _FakeMessage:
    stop_reason = "tool_use"

    def __init__(self, questions, **usage):
        self.content = [_FakeToolBlock(list(questions))]
        self.usage = _FakeUsage(**usage)


class _CannedClient:
    """messages.create always returns the same canned tool-use reply."""

    def __init__(self, reply):
        self._reply = reply
        self.calls = []
        self.messages = self

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self._reply


def _svc(client):
    svc = AIGeneratorService.__new__(AIGeneratorService)
    svc._client = client
    svc._reset_usage()
    return svc


def _variant(text, correct_index=0):
    """A schema-valid MCQ variant (survives validate_batch)."""
    return {
        "text": text,
        "difficulty": "Medium",
        "bloom": "Apply",
        "marks": 4,
        "explanation": "Because.",
        "solution": "Step 1. Step 2. Step 3.",
        "options": [
            {"text": f"opt {i}", "correct": (i == correct_index),
             "rationale": "ok" if i == correct_index else "slip"}
            for i in range(4)
        ],
    }


class GenerateVariantsUnitTests(SimpleTestCase):

    def _run(self, original, canned, **usage):
        client = _CannedClient(_FakeMessage(canned, **usage))
        svc = _svc(client)
        # verify_answers would drive the blind-solver against the fake client (and
        # noisily log). It is tested elsewhere; here we isolate generate_variants' own
        # pipeline, so stub it to identity.
        with patch.object(AIGeneratorService, 'verify_answers',
                          side_effect=lambda q, **kw: q):
            variants = svc.generate_variants(original, count=3, language='English')
        return svc, client, variants

    def test_returns_n_variants_that_differ_from_the_original(self):
        original = {"q_type": "MCQ", "text": "A car covers 100 m in 5 s. Find its speed.",
                    "subject": "Physics", "topic": "Kinematics", "exam": "NEET",
                    "difficulty": "Medium", "marks": 4,
                    "options": [{"text": "20 m/s", "correct": True}]}
        canned = [
            _variant("A car covers 240 m in 6 s. Find its speed.", 1),
            _variant("A car covers 90 m in 3 s. Find its speed.", 2),
            _variant("A car covers 150 m in 10 s. Find its speed.", 0),
        ]
        svc, client, variants = self._run(original, canned,
                                          input_tokens=800, output_tokens=1200)

        self.assertEqual(len(variants), 3)
        # None reproduce the original stem — the whole point of a variant.
        for v in variants:
            self.assertNotEqual(v["text"], original["text"])
        # The tool was forced (injection-safe path).
        call = client.calls[0]
        self.assertEqual(call["tool_choice"], {"type": "tool", "name": "emit_questions"})

    def test_usage_accrues_from_the_model_call(self):
        original = {"q_type": "MCQ", "text": "Q?", "subject": "Physics"}
        canned = [_variant("V1"), _variant("V2"), _variant("V3")]
        svc, _client, variants = self._run(original, canned,
                                           input_tokens=800, output_tokens=1200)
        self.assertEqual(svc.last_usage['input_tokens'], 800)
        self.assertEqual(svc.last_usage['output_tokens'], 1200)
        self.assertIn('generation', svc.usage_by_phase)

    def test_count_trims_overproduction(self):
        original = {"q_type": "MCQ", "text": "Q?", "subject": "Physics"}
        canned = [_variant(f"V{i}") for i in range(6)]   # model over-produced
        _svc_, _client, variants = self._run(original, canned)
        self.assertEqual(len(variants), 3)

    def test_no_client_returns_empty(self):
        svc = _svc(None)
        self.assertEqual(svc.generate_variants({"q_type": "MCQ", "text": "Q?"}, count=3), [])


# ── Endpoint smoke test ───────────────────────────────────────────────────────
class _FakeGenerator:
    """Stands in for AIGeneratorService in the view — no network, reports usage."""
    usage_by_phase = {}

    def __init__(self):
        self.last_usage = {'input_tokens': 0, 'output_tokens': 0}

    def generate_variants(self, question, count, language='English', **kw):
        self.last_usage = {'input_tokens': 5_000, 'output_tokens': 5_000}
        return [_variant(f"Variant {i}") for i in range(count)]


class VariantEndpointTests(TestCase):

    def setUp(self):
        from users.models import Organization, User
        from billing.models import Subscription, Wallet
        self.org = Organization.objects.create(name='Acme Coaching')
        self.user = User.objects.create(username='t@example.com', email='t@example.com',
                                        org=self.org)
        Subscription.objects.create(org=self.org, status='active')
        self.wallet = Wallet.objects.create(org=self.org, balance=500)

        import questions.controller.questioncontroller as qc
        self._qc = qc
        self._orig = qc.AIGeneratorService
        qc.AIGeneratorService = _FakeGenerator

    def tearDown(self):
        self._qc.AIGeneratorService = self._orig

    def _auth(self):
        return {'HTTP_AUTHORIZATION': f'Bearer {AccessToken.for_user(self.user)}'}

    def test_inline_question_charges_and_returns_variants(self):
        from billing.models import CreditTxn
        from billing.service.billingservice import compute_credits_from_tokens
        resp = self.client.post(
            '/api/questions/variants/',
            data=json.dumps({'count': 4, 'question': {
                'q_type': 'MCQ', 'text': 'A body of mass m has velocity v.',
                'subject': 'Physics', 'topic': 'Kinematics', 'exam': 'NEET'}}),
            content_type='application/json', **self._auth())

        self.assertEqual(resp.status_code, 200)
        body = json.loads(resp.content)
        self.assertEqual(len(body['variants']), 4)
        expected = compute_credits_from_tokens(5_000, 5_000)
        self.assertEqual(body['charged'], expected)
        self.assertEqual(CreditTxn.objects.filter(org=self.org, kind='consume').count(), 1)

    def test_missing_source_is_400(self):
        resp = self.client.post(
            '/api/questions/variants/', data=json.dumps({'count': 3}),
            content_type='application/json', **self._auth())
        self.assertEqual(resp.status_code, 400)

    def test_empty_wallet_is_refused_before_any_generation(self):
        from billing.models import Wallet
        Wallet.objects.filter(org=self.org).update(balance=0)
        resp = self.client.post(
            '/api/questions/variants/',
            data=json.dumps({'count': 4, 'question': {'q_type': 'MCQ', 'text': 'Q?'}}),
            content_type='application/json', **self._auth())
        self.assertEqual(resp.status_code, 402)
