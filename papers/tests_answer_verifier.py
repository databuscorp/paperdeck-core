"""Tests for AnswerVerifier — focused on the Numerical path (blind-solve by value).

Hermetic: the Anthropic client is a scripted fake that returns queued responses in call
order (blind-solve first, then adjudication), so no network and no DB.
"""
import json
from types import SimpleNamespace

from django.test import SimpleTestCase

from papers.service.verificationservice import (
    AnswerVerifier, CORRECTED, FLAGGED, SKIPPED, VERIFIED,
)


def _msg(text):
    return SimpleNamespace(
        content=[SimpleNamespace(text=text)],
        usage=SimpleNamespace(input_tokens=10, output_tokens=5,
                              cache_creation_input_tokens=0, cache_read_input_tokens=0),
    )


class _ScriptedClient:
    """Returns queued response bodies (strings) in call order."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = 0
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        self.calls += 1
        body = self._responses.pop(0) if self._responses else "[]"
        return _msg(body)


def _numeric_q(text="Compute g.", answer=9.8, unit="m/s^2"):
    return {"text": text, "q_type": "Numerical", "numeric_answer": answer, "unit": unit}


def _verifier(client):
    return AnswerVerifier(client, solver_model="s", adjudicator_model="a")


class NumericVerificationTests(SimpleTestCase):

    def test_solver_agrees_is_verified_without_adjudication(self):
        client = _ScriptedClient([json.dumps([{"index": 0, "value": 9.8, "confidence": "high"}])])
        q = _numeric_q(answer=9.8)
        _verifier(client).verify([q])
        self.assertEqual(q["verification"], VERIFIED)
        self.assertEqual(client.calls, 1)  # no adjudication call

    def test_numeric_tolerance_allows_small_rounding(self):
        client = _ScriptedClient([json.dumps([{"index": 0, "value": 9.81}])])
        q = _numeric_q(answer=9.8)
        _verifier(client).verify([q])
        self.assertEqual(q["verification"], VERIFIED)

    def test_key_corrected_when_two_solves_agree_against_it(self):
        client = _ScriptedClient([
            json.dumps([{"index": 0, "value": 10}]),                 # blind solve
            json.dumps({"value": 10, "flawed": False, "reason": "F=ma gives 10"}),  # adjudicate
        ])
        q = _numeric_q(answer=5)
        _verifier(client).verify([q])
        self.assertEqual(q["verification"], CORRECTED)
        self.assertEqual(q["numeric_answer"], 10)      # tidied to int
        self.assertIn("corrected", q["verification_note"])

    def test_key_stands_when_adjudicator_backs_it(self):
        client = _ScriptedClient([
            json.dumps([{"index": 0, "value": 10}]),                 # blind solve disagrees
            json.dumps({"value": 5, "flawed": False, "reason": "key is right"}),   # adjudicate backs key
        ])
        q = _numeric_q(answer=5)
        _verifier(client).verify([q])
        self.assertEqual(q["verification"], VERIFIED)
        self.assertEqual(q["numeric_answer"], 5)       # unchanged

    def test_flawed_question_is_flagged(self):
        client = _ScriptedClient([
            json.dumps([{"index": 0, "value": 10}]),
            json.dumps({"value": None, "flawed": True, "reason": "missing data"}),
        ])
        q = _numeric_q(answer=5)
        _verifier(client).verify([q])
        self.assertEqual(q["verification"], FLAGGED)
        self.assertIn("flawed", q["verification_note"].lower())

    def test_three_way_disagreement_is_flagged(self):
        client = _ScriptedClient([
            json.dumps([{"index": 0, "value": 10}]),
            json.dumps({"value": 7, "flawed": False, "reason": "I get 7"}),
        ])
        q = _numeric_q(answer=5)
        _verifier(client).verify([q])
        self.assertEqual(q["verification"], FLAGGED)
        self.assertEqual(q["numeric_answer"], 5)       # not changed on an unresolved dispute

    def test_solver_silence_is_flagged(self):
        client = _ScriptedClient([json.dumps([])])     # solver returned nothing for index 0
        q = _numeric_q(answer=5)
        _verifier(client).verify([q])
        self.assertEqual(q["verification"], FLAGGED)

    def test_non_numeric_non_mcq_is_skipped(self):
        client = _ScriptedClient([])
        q = {"text": "Explain diffusion.", "q_type": "Long Answer"}
        _verifier(client).verify([q])
        self.assertEqual(q["verification"], SKIPPED)
        self.assertEqual(client.calls, 0)

    def test_mixed_batch_routes_each_question(self):
        # One MCQ (index-based) + one numeric, both correct on first solve.
        client = _ScriptedClient([
            # MCQ blind solve (grouped call) — solver picks option 1
            json.dumps([{"index": 0, "option_index": 1, "final_answer": "", "confidence": "high"}]),
            # numeric blind solve
            json.dumps([{"index": 0, "value": 9.8}]),
        ])
        mcq = {"text": "Pick", "options": [{"text": "a"}, {"text": "b", "correct": True}]}
        num = _numeric_q(answer=9.8)
        _verifier(client).verify([mcq, num])
        self.assertEqual(mcq["verification"], VERIFIED)
        self.assertEqual(num["verification"], VERIFIED)
