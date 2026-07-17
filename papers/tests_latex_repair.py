r"""LaTeX survival across the tool-use boundary.

The model writes maths with single backslashes ($\frac{a}{b}$). Tool-use input is JSON,
and the Anthropic API parses it SERVER-SIDE — so JSON's escape rules fire before we ever
see the data. Crucially, only FIVE escapes are both valid JSON and the start of common
LaTeX commands, and those are the silent killers:

    \f  →  FORMFEED   \frac, \forall        $\frac{a}{b}$  renders as  "rac{a}{b}"
    \t  →  TAB        \text, \times, \theta, \tan
    \n  →  NEWLINE    \nabla, \neq
    \r  →  CR         \rho, \right
    \b  →  BACKSPACE  \beta, \binom

No exception, no warning — just broken maths on a printed exam paper. (An invalid escape
like \alpha or \int is a different story: JSON rejects it outright rather than mangling
it, so it cannot corrupt silently and is not what this guards.)

`_loads_lenient` protects the plain-text path from exactly this. Tool-use bypasses it,
because we never do the parsing.
"""
import json

from django.test import SimpleTestCase

from papers.service.aigeneratorservice import _repair_latex_deep, _repair_latex_escapes

# What the API hands us after it has parsed the model's single-backslash JSON.
CORRUPTED = {
    r"$\frac{a}{b}$":  "$\frac{a}{b}$",
    r"$4\text{ kg}$":  "$4\text{ kg}$",
    r"$\times$":       "$\times$",
    r"$\theta$":       "$\theta$",
    r"$\nabla$":       "$\nabla$",
    r"$\rho$":         "$\rho$",
    r"$\beta$":        "$\beta$",
    r"$\tan\theta$":   "$\tan\theta$",
}


class PremiseTests(SimpleTestCase):
    """If JSON ever stops eating these, the repair is dead code and should be removed.
    While it does, the repair is load-bearing."""

    def test_json_really_does_eat_single_backslash_frac(self):
        corrupted = json.loads(r'{"v": "$\frac{a}{b}$"}')["v"]
        self.assertNotIn("\\frac", corrupted)
        self.assertIn("\f", corrupted)        # form feed — and "rac{a}{b}" is what shows
        self.assertEqual(corrupted, CORRUPTED[r"$\frac{a}{b}$"])


class RepairTests(SimpleTestCase):

    def test_every_silently_corruptible_command_is_restored(self):
        for original, corrupted in CORRUPTED.items():
            with self.subTest(original=original):
                self.assertNotEqual(corrupted, original)          # it really was broken
                self.assertEqual(_repair_latex_escapes(corrupted), original)

    def test_display_maths_is_repaired_too(self):
        self.assertEqual(
            _repair_latex_escapes("$$\frac{dy}{dx} = \theta$$"),
            r"$$\frac{dy}{dx} = \theta$$",
        )

    def test_real_line_breaks_outside_maths_are_preserved(self):
        """Assertion-Reason questions are built from real newlines. Repairing outside
        maths would turn every one of them into a literal backslash-n."""
        s = "Assertion (A): foo\nReason (R): bar"
        self.assertEqual(_repair_latex_escapes(s), s)
        self.assertIn("\n", _repair_latex_escapes(s))

    def test_prose_break_survives_while_maths_beside_it_is_repaired(self):
        repaired = _repair_latex_escapes("Line one\nThen: $\nabla \\cdot E$")
        self.assertIn("\n", repaired)          # the prose break stays a real break
        self.assertIn(r"\nabla", repaired)     # the maths command is restored

    def test_clean_text_is_untouched(self):
        for s in ("no maths here", r"$x^2 + y^2 = r^2$", "", "tabs\tin\tprose"):
            self.assertEqual(_repair_latex_escapes(s), s)


class DeepRepairTests(SimpleTestCase):
    """Every string in the question, not just the stem. A field added later (a solution,
    a rationale, a translation) must be covered without anyone remembering to wire it
    up — which is precisely how this class of bug keeps coming back."""

    def test_repair_reaches_every_nested_string(self):
        q = {
            "text": "Find $\frac{dy}{dx}$",
            "solution": "$\frac{dy}{dx} = 2x$",
            "explanation": "Differentiate $4\text{ kg}$ first",
            "options": [
                {"text": "$2x$", "rationale": "forgot the $\frac{1}{2}$"},
                {"text": "$x^2$", "rationale": "no maths here"},
            ],
            "translations": {"hi": {"text": "$\frac{dy}{dx}$ ज्ञात कीजिए"}},
        }

        fixed = _repair_latex_deep(q)

        self.assertIn(r"\frac", fixed["text"])
        self.assertIn(r"\frac", fixed["solution"])
        self.assertIn(r"\text", fixed["explanation"])
        self.assertIn(r"\frac", fixed["options"][0]["rationale"])
        self.assertIn(r"\frac", fixed["translations"]["hi"]["text"])
        # Untouched where there is no maths.
        self.assertEqual(fixed["options"][1]["rationale"], "no maths here")

    def test_non_strings_pass_through_unharmed(self):
        q = {"marks": 4, "correct": True, "numeric_answer": 9.8, "diagram_schema": None}
        self.assertEqual(_repair_latex_deep(q), q)
