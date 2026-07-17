"""Prompt caching on the generation calls.

Every failure mode here is SILENT. The API does not complain when a cache never
forms — it just bills you full price and reports `cache_creation_input_tokens: 0`,
which nobody is reading. So the things that would quietly break caching are pinned
here instead:

  * frozen text drifting back into the per-call user message (kills the prefix),
  * the `cache_control` breakpoint disappearing,
  * the diagram catalog being trimmed below the model's minimum cacheable prefix.

Caching is a prefix match over tools → system → messages, and on claude-haiku-4-5 a
prefix under 4096 tokens does not cache at all. Only the image-based prompts clear
that floor (6796 tokens, measured); MCQ and friends sit at ~1.3k and deliberately
carry no breakpoint.
"""
from unittest.mock import patch

from django.test import SimpleTestCase

from papers.service.aigeneratorservice import (
    _CACHE_CONTROL,
    _DIAGRAM_SCHEMA_HINT,
    _LATEX_MATH_HINT,
    _MIN_CACHEABLE_TOKENS,
    AIGeneratorService,
    _generation_system,
)


class _FakeUsage:
    def __init__(self, **kw):
        self.input_tokens = kw.get('input_tokens', 0)
        self.output_tokens = kw.get('output_tokens', 0)
        self.cache_creation_input_tokens = kw.get('cache_creation_input_tokens', 0)
        self.cache_read_input_tokens = kw.get('cache_read_input_tokens', 0)


class _FakeBlock:
    type = "tool_use"

    def __init__(self, questions):
        self.input = {"questions": questions}


class _FakeMessage:
    stop_reason = "tool_use"

    def __init__(self, questions=(), **usage):
        self.content = [_FakeBlock(list(questions))]
        self.usage = _FakeUsage(**usage)


class _CapturingClient:
    """Records the kwargs of every messages.create call."""

    def __init__(self, reply=None):
        self.calls = []
        self._reply = reply or _FakeMessage()
        self.messages = self

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self._reply


def _svc(client):
    svc = AIGeneratorService.__new__(AIGeneratorService)
    svc._client = client
    svc._reset_usage()          # sets last_usage AND usage_by_phase
    return svc


class GenerationSystemBlocksTests(SimpleTestCase):

    def test_image_based_prompt_has_a_breakpoint_on_the_last_block(self):
        """The breakpoint must be on the LAST system block — that is what pulls the
        tools and every block above it into the same cache entry."""
        blocks = _generation_system("Image Based")
        self.assertGreaterEqual(len(blocks), 2)
        self.assertEqual(blocks[-1].get("cache_control"), _CACHE_CONTROL)
        self.assertIn(_DIAGRAM_SCHEMA_HINT, blocks[-1]["text"])

    def test_cheap_question_types_carry_no_breakpoint(self):
        """MCQ/Numerical prompts are ~1.3k tokens — under the 4096-token floor, so a
        cache can never form. Asking for one anyway would look, in the code and in the
        usage numbers, exactly like caching that works."""
        for q_type in ("MCQ", "Numerical", "Assertion Reason", "Multiple Correct"):
            blocks = _generation_system(q_type)
            self.assertFalse(
                any("cache_control" in b for b in blocks),
                f"{q_type} asks for a cache it is too short to get",
            )

    def test_diagram_catalog_is_still_long_enough_to_cache(self):
        """A canary on the silent failure: trim the catalog and image-based caching
        stops working with no error anywhere.

        This is an offline proxy for a token count. The catalog measures 5346 tokens at
        15808 chars — 2.96 chars/token, because it is dense JSON. Even at a pessimistic
        3.5 chars/token it must stay above the floor. If this fails, re-measure for real:
            client.messages.count_tokens(model=HAIKU_MODEL, system=..., messages=...)
        """
        pessimistic_chars_per_token = 3.5
        floor_chars = _MIN_CACHEABLE_TOKENS * pessimistic_chars_per_token
        self.assertGreater(
            len(_DIAGRAM_SCHEMA_HINT), floor_chars,
            "diagram catalog shrank below the minimum cacheable prefix — image-based "
            "prompt caching has silently stopped working",
        )


class PromptSplitTests(SimpleTestCase):
    """The frozen text must live in `system` and NOWHERE else. A copy left behind in the
    user message would not error — it would just double the tokens it was meant to save."""

    def _generate(self, q_type):
        client = _CapturingClient()
        svc = _svc(client)
        with patch.object(AIGeneratorService, "_style_exemplars", return_value=""), \
             patch("papers.service.questionvalidator.validate_batch", side_effect=lambda q, t: q):
            svc._generate_batch("NEET", "Physics", "Optics", q_type, "Medium", "Apply", 5)
        return client.calls[0]

    def test_image_based_catalog_is_sent_once_in_system_not_in_the_user_message(self):
        call = self._generate("Image Based")
        system_text = "".join(b["text"] for b in call["system"])
        user_text = call["messages"][0]["content"]

        self.assertIn(_DIAGRAM_SCHEMA_HINT, system_text)
        self.assertNotIn(_DIAGRAM_SCHEMA_HINT, user_text)
        self.assertIn(_LATEX_MATH_HINT, system_text)
        self.assertNotIn(_LATEX_MATH_HINT, user_text)

    def test_volatile_content_stays_behind_the_breakpoint(self):
        """Count and topic vary per call. If they ever migrate into `system` the prefix
        changes on every request and the cache can never be read back."""
        call = self._generate("MCQ")
        system_text = "".join(b["text"] for b in call["system"])
        user_text = call["messages"][0]["content"]

        self.assertIn("Optics", user_text)
        self.assertNotIn("Optics", system_text)
        self.assertIn("exactly 5", user_text)
        self.assertNotIn("exactly 5", system_text)


class DiagramRepairCacheTests(SimpleTestCase):

    def test_repair_sends_the_catalog_as_a_cached_system_block(self):
        """Repairs are the best cache in the service: the catalog is ~5.3k of the ~5.5k
        tokens in the prompt, and every repair call in the process sends a byte-identical
        prefix, so a paper with several bad diagrams pays for it once."""
        client = _CapturingClient(reply=_FakeMessageText('{"diagram_type":"physics",'
                                                         '"subtype":"inclined_plane","params":{}}'))
        svc = _svc(client)
        svc._repair_diagram_schema({"diagram_type": "physics"}, "bad subtype", "Q text", "Physics")

        call = client.calls[0]
        self.assertEqual(call["system"][-1].get("cache_control"), _CACHE_CONTROL)
        self.assertIn(_DIAGRAM_SCHEMA_HINT, call["system"][-1]["text"])
        self.assertNotIn(_DIAGRAM_SCHEMA_HINT, call["messages"][0]["content"])


class _FakeTextBlock:
    type = "text"

    def __init__(self, text):
        self.text = text


class _FakeMessageText:
    stop_reason = "end_turn"

    def __init__(self, text):
        self.content = [_FakeTextBlock(text)]
        self.usage = _FakeUsage()


class UsageAccountingTests(SimpleTestCase):

    def test_cache_tokens_are_recorded(self):
        """`input_tokens` from the API is the UNCACHED remainder only. Without these
        fields the cached part of a prompt is invisible — both to cost, and to anyone
        asking whether the cache is working at all."""
        svc = _svc(_CapturingClient())
        svc._add_usage(_FakeMessage(input_tokens=100, output_tokens=50,
                                    cache_creation_input_tokens=6796))
        svc._add_usage(_FakeMessage(input_tokens=100, output_tokens=50,
                                    cache_read_input_tokens=6796))

        self.assertEqual(svc.last_usage['input_tokens'], 200)
        self.assertEqual(svc.last_usage['output_tokens'], 100)
        self.assertEqual(svc.last_usage['cache_creation_input_tokens'], 6796)
        self.assertEqual(svc.last_usage['cache_read_input_tokens'], 6796)

    def test_usage_starts_at_zero_for_every_field(self):
        self.assertEqual(
            AIGeneratorService._zero_usage(),
            {'input_tokens': 0, 'output_tokens': 0,
             'cache_creation_input_tokens': 0, 'cache_read_input_tokens': 0},
        )
