"""Unit tests for the vision diagram verifier.

These are hermetic — no live API and no DB. The Anthropic client is faked so the tests
exercise verdict parsing, the skip/degrade paths, and the env gate without a network call.
"""
from types import SimpleNamespace
from unittest import mock

from django.test import SimpleTestCase

from papers.service import diagramverifier as dv
from papers.service.aigeneratorservice import _vlm_verify_enabled


def _tool_use_message(payload):
    """A fake Anthropic message carrying a single tool_use block + usage."""
    return SimpleNamespace(
        content=[SimpleNamespace(type="tool_use", name=dv._VERDICT_TOOL["name"], input=payload)],
        usage=SimpleNamespace(input_tokens=100, output_tokens=20,
                              cache_creation_input_tokens=0, cache_read_input_tokens=0),
    )


class _FakeClient:
    """Minimal stand-in for anthropic.Anthropic — records the last create() call."""

    def __init__(self, message):
        self._message = message
        self.last_kwargs = None
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        self.last_kwargs = kwargs
        return self._message


_Q = {"image_svg": "<svg/>", "text": "A ray diagram of a converging lens.",
      "options": [{"text": "real"}, {"text": "virtual"}]}


class DiagramVerifierTests(SimpleTestCase):

    def setUp(self):
        # Never rasterise for real in unit tests — the point is the verdict logic.
        self._patch = mock.patch.object(dv, "_svg_to_png_b64", return_value="ZmFrZQ==")
        self._patch.start()

    def tearDown(self):
        self._patch.stop()

    def test_clean_verdict_is_parsed(self):
        client = _FakeClient(_tool_use_message(
            {"severity": "clean", "defects": [], "fix_hint": ""}))
        verdict = dv.DiagramVerifier(client, "m").verify(_Q)
        self.assertEqual(verdict["severity"], "clean")
        self.assertEqual(verdict["defects"], [])

    def test_major_verdict_carries_defects_and_hint(self):
        client = _FakeClient(_tool_use_message(
            {"severity": "major", "defects": ["arrow points the wrong way"],
             "fix_hint": "reverse the ray"}))
        verdict = dv.DiagramVerifier(client, "m").verify(_Q)
        self.assertEqual(verdict["severity"], "major")
        self.assertIn("arrow points the wrong way", verdict["defects"])
        self.assertEqual(verdict["fix_hint"], "reverse the ray")

    def test_usage_sink_receives_the_message(self):
        client = _FakeClient(_tool_use_message(
            {"severity": "clean", "defects": []}))
        seen = []
        dv.DiagramVerifier(client, "m", usage_sink=seen.append).verify(_Q)
        self.assertEqual(len(seen), 1)
        self.assertEqual(seen[0].usage.input_tokens, 100)

    def test_sends_an_image_block(self):
        client = _FakeClient(_tool_use_message({"severity": "clean", "defects": []}))
        dv.DiagramVerifier(client, "m").verify(_Q)
        content = client.last_kwargs["messages"][0]["content"]
        self.assertTrue(any(b.get("type") == "image" for b in content))
        # The question stem and options must reach the model.
        text = next(b["text"] for b in content if b.get("type") == "text")
        self.assertIn("converging lens", text)
        self.assertIn("real", text)

    def test_no_client_skips(self):
        verdict = dv.DiagramVerifier(None, "m").verify(_Q)
        self.assertEqual(verdict["severity"], dv.SKIPPED)

    def test_no_svg_skips(self):
        client = _FakeClient(_tool_use_message({"severity": "clean", "defects": []}))
        verdict = dv.DiagramVerifier(client, "m").verify({"text": "no figure"})
        self.assertEqual(verdict["severity"], dv.SKIPPED)

    def test_rasterisation_failure_degrades_to_skipped(self):
        self._patch.stop()  # let the real _svg_to_png_b64 run against unusable input
        try:
            with mock.patch.object(dv, "_svg_to_png_b64", return_value=None):
                client = _FakeClient(_tool_use_message({"severity": "clean", "defects": []}))
                verdict = dv.DiagramVerifier(client, "m").verify(_Q)
                self.assertEqual(verdict["severity"], dv.SKIPPED)
        finally:
            self._patch.start()

    def test_api_error_degrades_to_skipped(self):
        class Boom:
            messages = SimpleNamespace(create=mock.Mock(side_effect=RuntimeError("boom")))
        verdict = dv.DiagramVerifier(Boom(), "m").verify(_Q)
        self.assertEqual(verdict["severity"], dv.SKIPPED)

    def test_garbage_verdict_degrades_to_skipped(self):
        client = _FakeClient(_tool_use_message({"severity": "not-a-level", "defects": []}))
        verdict = dv.DiagramVerifier(client, "m").verify(_Q)
        self.assertEqual(verdict["severity"], dv.SKIPPED)


class VlmGateTests(SimpleTestCase):

    def test_env_off_disables(self):
        for val in ("0", "false", "no", "off", "OFF"):
            with mock.patch.dict("os.environ", {"DIAGRAM_VLM_VERIFY": val}):
                self.assertFalse(_vlm_verify_enabled())

    def test_env_on_enables(self):
        with mock.patch.dict("os.environ", {"DIAGRAM_VLM_VERIFY": "1"}):
            self.assertTrue(_vlm_verify_enabled())

    def test_default_is_on(self):
        with mock.patch.dict("os.environ", {}, clear=False):
            import os
            os.environ.pop("DIAGRAM_VLM_VERIFY", None)
            self.assertTrue(_vlm_verify_enabled())


class VerifyDiagramsWiringTests(SimpleTestCase):
    """The glue in AIGeneratorService._verify_diagrams: repair, flag, or ship each verdict."""

    def _gen(self):
        from papers.service.aigeneratorservice import AIGeneratorService
        g = AIGeneratorService()
        g._client = object()  # truthy client; the fake verifier never uses it
        return g

    def _run(self, questions, verify_side_effect, repair_return):
        fake = mock.Mock()
        fake.verify.side_effect = verify_side_effect
        g = self._gen()
        with mock.patch("papers.service.diagramverifier.DiagramVerifier", return_value=fake), \
             mock.patch.object(type(g), "_repair_diagram_visually", return_value=repair_return), \
             mock.patch.dict("os.environ", {"DIAGRAM_VLM_VERIFY": "1"}):
            g._verify_diagrams(questions, "NEET", "Physics")
        return fake

    def test_disabled_gate_is_a_noop(self):
        q = {"image_svg": "<svg/>", "diagram_schema": {}}
        with mock.patch.dict("os.environ", {"DIAGRAM_VLM_VERIFY": "0"}):
            self._gen()._verify_diagrams([q], "NEET", "Physics")
        self.assertNotIn("diagram_review", q)
        self.assertNotIn("diagram_failed", q)

    def test_clean_ships_untouched(self):
        q = {"image_svg": "<svg/>", "diagram_schema": {}}
        self._run([q], [{"severity": "clean", "defects": [], "fix_hint": ""}], None)
        self.assertNotIn("diagram_failed", q)

    def test_minor_records_review_but_ships(self):
        q = {"image_svg": "<svg/>", "diagram_schema": {}}
        self._run([q], [{"severity": "minor", "defects": ["tight spacing"], "fix_hint": ""}], None)
        self.assertNotIn("diagram_failed", q)
        self.assertEqual(q["diagram_review"]["severity"], "minor")

    def test_major_unrepairable_is_flagged_for_regeneration(self):
        q = {"image_svg": "<svg/>", "diagram_schema": {}}
        self._run([q], [{"severity": "major", "defects": ["wrong object"], "fix_hint": "x"}], None)
        self.assertTrue(q["diagram_failed"])

    def test_major_repaired_clears_the_flag_and_swaps_svg(self):
        q = {"image_svg": "<svg-old/>", "diagram_schema": {}}
        # first verdict major → repair succeeds → re-verify clean.
        fake = self._run(
            [q],
            [{"severity": "major", "defects": ["x"], "fix_hint": "y"},
             {"severity": "clean", "defects": [], "fix_hint": ""}],
            "<svg-new/>",
        )
        self.assertNotIn("diagram_failed", q)
        self.assertEqual(q["image_svg"], "<svg-new/>")
        self.assertEqual(fake.verify.call_count, 2)  # verified, repaired, re-verified

    def test_major_repaired_but_still_major_is_flagged(self):
        q = {"image_svg": "<svg/>", "diagram_schema": {}}
        self._run(
            [q],
            [{"severity": "major", "defects": ["x"], "fix_hint": "y"},
             {"severity": "major", "defects": ["still wrong"], "fix_hint": "z"}],
            "<svg-new/>",
        )
        self.assertTrue(q["diagram_failed"])
