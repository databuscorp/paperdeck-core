"""Bilingual generation.

NEET and JEE Main are set in English and Hindi, so a generator that can only write
English is unusable for a large share of Indian coaching institutes.

The dangerous failure is not a clumsy translation — it is a MISALIGNED one. The answer
key is an index into the options list. If the translated options don't line up with the
English ones, the Hindi paper marks a different option correct than the English paper
does, and nothing downstream can detect it. So the alignment rule is pinned hard here.
"""
from django.test import SimpleTestCase

from papers.service.aigeneratorservice import (
    DEFAULT_LANGUAGE,
    AIGeneratorService,
    _generation_system,
    _language_spec,
    _questions_tool,
)


def _q(**over):
    q = {
        "text": "A block of mass $m$ slides down.",
        "options": [
            {"text": "10 m/s", "correct": False},
            {"text": "20 m/s", "correct": True},
            {"text": "30 m/s", "correct": False},
            {"text": "40 m/s", "correct": False},
        ],
    }
    q.update(over)
    return q


class LanguageSpecTests(SimpleTestCase):

    def test_english_asks_for_no_translation(self):
        self.assertIsNone(_language_spec("English"))
        self.assertIsNone(_language_spec(None))
        self.assertNotIn("translation", _questions_tool("MCQ", "English")
                         ["input_schema"]["properties"]["questions"]["items"]["properties"])

    def test_a_translation_language_is_required_in_the_schema(self):
        """Optional means the model skips it — that is exactly what happened with the
        distractor rationale. The schema is the only thing that compels output."""
        item = (_questions_tool("MCQ", "Hindi")
                ["input_schema"]["properties"]["questions"]["items"])
        self.assertIn("translation", item["properties"])
        self.assertIn("translation", item["required"])

    def test_language_is_case_and_whitespace_tolerant(self):
        self.assertEqual(_language_spec(" hindi ")[0], "hi")

    def test_an_unknown_language_falls_back_to_english_only(self):
        """An unrecognised language must not silently produce an empty translation
        instruction — it must produce no translation at all."""
        self.assertIsNone(_language_spec("Klingon"))

    def test_the_translation_instruction_reaches_the_cached_system_block(self):
        system = "".join(b["text"] for b in _generation_system("MCQ", "Hindi"))
        self.assertIn("Hindi", system)
        self.assertIn("same order", system.lower())
        # English prompts must not carry it — that would be dead tokens on every call.
        self.assertNotIn("Hindi", "".join(
            b["text"] for b in _generation_system("MCQ", DEFAULT_LANGUAGE)))


class TranslationNormalizationTests(SimpleTestCase):

    def test_translation_is_folded_under_its_iso_code(self):
        qs = [_q(translation={
            "text": "द्रव्यमान $m$ का एक ब्लॉक नीचे फिसलता है।",
            "solution": "हल: $v = u + at$",
            "options": [{"text": "१० मी/से"}, {"text": "२० मी/से"},
                        {"text": "३० मी/से"}, {"text": "४० मी/से"}],
        })]
        AIGeneratorService._normalize_translations(qs, "Hindi")

        hi = qs[0]["translations"]["hi"]
        self.assertIn("ब्लॉक", hi["text"])
        self.assertEqual(len(hi["options"]), 4)
        self.assertIn("solution", hi)
        # The raw key is consumed, not left lying around next to the folded one.
        self.assertNotIn("translation", qs[0])

    def test_the_answer_key_is_never_taken_from_the_translation(self):
        """A mistranslated distractor must not be able to become a second correct answer.
        The translated options carry TEXT ONLY; `correct` stays owned by the English list."""
        qs = [_q(translation={
            "text": "प्रश्न",
            "options": [{"text": "a", "correct": True}, {"text": "b", "correct": True},
                        {"text": "c", "correct": True}, {"text": "d", "correct": True}],
        })]
        AIGeneratorService._normalize_translations(qs, "Hindi")

        for opt in qs[0]["translations"]["hi"]["options"]:
            self.assertNotIn("correct", opt)
        # The English key is untouched: still exactly one correct, still index 1.
        english = qs[0]["options"]
        self.assertEqual(sum(1 for o in english if o["correct"]), 1)
        self.assertTrue(english[1]["correct"])

    def test_a_misaligned_translation_is_dropped_not_stored(self):
        """THE guard. Three Hindi options against four English ones cannot be aligned by
        index, so the Hindi paper would mark the wrong option correct. An English-only
        question is merely limited; a misaligned bilingual one is a wrong answer key on a
        real exam. Drop it."""
        qs = [_q(translation={
            "text": "प्रश्न",
            "options": [{"text": "a"}, {"text": "b"}, {"text": "c"}],   # 3 vs 4
        })]
        AIGeneratorService._normalize_translations(qs, "Hindi")

        self.assertNotIn("translations", qs[0])
        self.assertNotIn("translation", qs[0])
        # The question itself survives, in English.
        self.assertTrue(qs[0]["text"])
        self.assertEqual(len(qs[0]["options"]), 4)

    def test_an_empty_or_missing_translation_is_dropped(self):
        for block in (None, {}, {"text": "   "}):
            qs = [_q(translation=block)]
            AIGeneratorService._normalize_translations(qs, "Hindi")
            self.assertNotIn("translations", qs[0])

    def test_english_strips_any_stray_translation_block(self):
        qs = [_q(translation={"text": "should not be here"})]
        AIGeneratorService._normalize_translations(qs, "English")
        self.assertNotIn("translation", qs[0])
        self.assertNotIn("translations", qs[0])

    def test_numerical_questions_translate_without_options(self):
        """No options to align, so the alignment guard must not reject it."""
        qs = [{"text": "Find $v$.", "numeric_answer": 20.0,
               "translation": {"text": "$v$ ज्ञात कीजिए।", "solution": "हल"}}]
        AIGeneratorService._normalize_translations(qs, "Hindi")
        self.assertEqual(qs[0]["translations"]["hi"]["text"], "$v$ ज्ञात कीजिए।")
