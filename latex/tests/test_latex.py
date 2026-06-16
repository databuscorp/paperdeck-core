"""
Tests for the LaTeX rendering service and API endpoints.
"""
import json

from django.test import TestCase, RequestFactory
from django.urls import reverse


# ── Service unit tests ────────────────────────────────────────────────────────

class TestLatexParser(TestCase):
    """Test parse_segments — no rendering, just structural correctness."""

    def _parse(self, text):
        from latex.service.latexservice import parse_segments
        return parse_segments(text)

    def test_plain_text_only(self):
        segs = self._parse("No math here.")
        self.assertEqual(len(segs), 1)
        self.assertEqual(segs[0].type, "text")
        self.assertEqual(segs[0].content, "No math here.")

    def test_inline_math_only(self):
        segs = self._parse("$E = mc^2$")
        self.assertEqual(len(segs), 1)
        self.assertEqual(segs[0].type, "math_inline")
        self.assertEqual(segs[0].content, "E = mc^2")

    def test_inline_math_surrounded_by_text(self):
        segs = self._parse("Find $x$ if $x^2 = 4$.")
        types = [s.type for s in segs]
        self.assertEqual(types, ["text", "math_inline", "text", "math_inline", "text"])
        self.assertEqual(segs[1].content, "x")
        self.assertEqual(segs[3].content, "x^2 = 4")

    def test_display_math_block(self):
        segs = self._parse("The answer is: $$\\int_0^1 x\\,dx = \\frac{1}{2}$$")
        types = [s.type for s in segs]
        self.assertIn("math_block", types)
        block = next(s for s in segs if s.type == "math_block")
        self.assertIn("int_0^1", block.content)

    def test_mixed_inline_and_block(self):
        text = "For $f(x) = x^2$:\n$$\\int_0^1 f(x)\\,dx = \\frac{1}{3}$$"
        segs = self._parse(text)
        types = [s.type for s in segs]
        self.assertIn("math_inline", types)
        self.assertIn("math_block", types)

    def test_multiple_inline_math(self):
        segs = self._parse("$\\alpha + \\beta = \\gamma$, so $\\gamma > 0$")
        inline = [s for s in segs if s.type == "math_inline"]
        self.assertEqual(len(inline), 2)

    def test_empty_string(self):
        segs = self._parse("")
        self.assertEqual(len(segs), 1)
        self.assertEqual(segs[0].type, "text")

    def test_no_false_positive_single_dollar(self):
        # A price: "$100" — should NOT be treated as math
        segs = self._parse("Price is $100")
        # Only one $ without matching close → no math_inline expected
        types = [s.type for s in segs]
        # The regex requires $content$ — unclosed dollar is plain text
        self.assertNotIn("math_inline", types)

    def test_jee_style_question(self):
        text = (
            "A block of mass $m = 2\\text{ kg}$ is placed on a frictionless surface. "
            "A force $F = 10\\text{ N}$ acts on it. Find the acceleration $a$."
        )
        segs = self._parse(text)
        inline = [s for s in segs if s.type == "math_inline"]
        self.assertEqual(len(inline), 3)

    def test_options_with_fractions(self):
        segs = self._parse("$\\frac{1}{2}mv^2$")
        self.assertEqual(len(segs), 1)
        self.assertEqual(segs[0].type, "math_inline")
        self.assertIn("frac", segs[0].content)


class TestHasMath(TestCase):
    def _has(self, text):
        from latex.service.latexservice import has_math
        return has_math(text)

    def test_detects_inline(self):
        self.assertTrue(self._has("Find $x$"))

    def test_detects_block(self):
        self.assertTrue(self._has("$$E=mc^2$$"))

    def test_no_math(self):
        self.assertFalse(self._has("A plain English sentence."))

    def test_empty(self):
        self.assertFalse(self._has(""))

    def test_none_string(self):
        self.assertFalse(self._has(None))

    def test_options_list(self):
        from latex.service.latexservice import has_math
        self.assertTrue(has_math("$x^2 = 4$"))

    def test_jee_chemistry_plain(self):
        # Chemical formulas should NOT trigger has_math
        self.assertFalse(self._has("The compound H₂SO₄ reacts with NaOH."))


class TestLatexRenderer(TestCase):
    """Test that SVG rendering produces valid output — no exceptions."""

    def _render(self, text):
        from latex.service.latexservice import render_text
        return render_text(text)

    def _is_valid_svg(self, svg_str: str) -> bool:
        return bool(svg_str and "<svg" in svg_str and "</svg>" in svg_str)

    def test_renders_simple_fraction(self):
        segs = self._render("$\\frac{1}{2}$")
        self.assertEqual(len(segs), 1)
        self.assertIsNotNone(segs[0].svg)
        self.assertTrue(self._is_valid_svg(segs[0].svg))

    def test_renders_integral(self):
        segs = self._render("$$\\int_0^{\\pi} \\sin x\\, dx$$")
        math_segs = [s for s in segs if s.svg]
        self.assertTrue(len(math_segs) >= 1)
        self.assertTrue(self._is_valid_svg(math_segs[0].svg))

    def test_renders_vector_notation(self):
        segs = self._render("The force $\\vec{F} = m\\vec{a}$")
        math_segs = [s for s in segs if s.type == "math_inline"]
        self.assertEqual(len(math_segs), 1)
        self.assertIsNotNone(math_segs[0].svg)

    def test_renders_greek_letters(self):
        segs = self._render("$\\alpha + \\beta = \\theta$")
        self.assertIsNotNone(segs[0].svg)

    def test_plain_text_segment_has_no_svg(self):
        segs = self._render("Just text, no math.")
        for seg in segs:
            if seg.type == "text":
                self.assertIsNone(seg.svg)

    def test_mixed_text_and_math_segments(self):
        segs = self._render("Value is $x = 5$ m/s")
        types = [s.type for s in segs]
        self.assertIn("text", types)
        self.assertIn("math_inline", types)
        # Math segment has SVG
        math_seg = next(s for s in segs if s.type == "math_inline")
        self.assertIsNotNone(math_seg.svg)

    def test_renders_exponent(self):
        segs = self._render("$E = mc^2$")
        self.assertIsNotNone(segs[0].svg)

    def test_renders_derivative(self):
        segs = self._render("$\\frac{d}{dx}(x^n) = nx^{n-1}$")
        self.assertIsNotNone(segs[0].svg)

    def test_renders_subscript(self):
        segs = self._render("velocity $v_0 = 10\\text{ m/s}$")
        math_seg = next(s for s in segs if s.type == "math_inline")
        self.assertIsNotNone(math_seg.svg)

    def test_renders_sqrt(self):
        segs = self._render("$\\sqrt{2}$ and $\\sqrt[3]{8} = 2$")
        math_segs = [s for s in segs if s.type == "math_inline"]
        self.assertEqual(len(math_segs), 2)
        for ms in math_segs:
            self.assertIsNotNone(ms.svg)


class TestValidateExpression(TestCase):
    def _validate(self, expr):
        from latex.service.latexservice import validate_expression
        return validate_expression(expr)

    def test_valid_fraction(self):
        ok, err = self._validate("\\frac{1}{2}")
        self.assertTrue(ok)
        self.assertIsNone(err)

    def test_valid_simple(self):
        ok, err = self._validate("E = mc^2")
        self.assertTrue(ok)

    def test_valid_greek(self):
        ok, err = self._validate("\\alpha + \\beta")
        self.assertTrue(ok)

    def test_valid_trig(self):
        ok, err = self._validate("\\sin\\theta + \\cos\\theta")
        self.assertTrue(ok)


# ── API endpoint tests ────────────────────────────────────────────────────────

class TestLatexRenderEndpoint(TestCase):
    def _post(self, path, data):
        resp = self.client.post(
            path,
            data=json.dumps(data),
            content_type="application/json",
        )
        return resp.status_code, json.loads(resp.content)

    def test_render_plain_text(self):
        status, body = self._post("/api/latex/render/", {"text": "No math here."})
        self.assertEqual(status, 200)
        self.assertFalse(body["has_math"])
        segs = body["segments"]
        self.assertEqual(len(segs), 1)
        self.assertEqual(segs[0]["type"], "text")

    def test_render_inline_math(self):
        status, body = self._post("/api/latex/render/", {"text": "Find $x^2 = 4$."})
        self.assertEqual(status, 200)
        self.assertTrue(body["has_math"])
        types = [s["type"] for s in body["segments"]]
        self.assertIn("math_inline", types)
        math_seg = next(s for s in body["segments"] if s["type"] == "math_inline")
        self.assertIn("svg", math_seg)
        self.assertIn("<svg", math_seg["svg"])

    def test_render_display_math(self):
        status, body = self._post("/api/latex/render/",
                                  {"text": "$$\\int_0^1 x\\,dx = \\frac{1}{2}$$"})
        self.assertEqual(status, 200)
        types = [s["type"] for s in body["segments"]]
        self.assertIn("math_block", types)

    def test_render_jee_question(self):
        text = ("A body of mass $m = 2\\text{ kg}$ moves with acceleration "
                "$a = 5\\text{ m/s}^2$. The net force is $F = ma$.")
        status, body = self._post("/api/latex/render/", {"text": text})
        self.assertEqual(status, 200)
        self.assertTrue(body["has_math"])
        math_segs = [s for s in body["segments"] if s["type"] == "math_inline"]
        self.assertEqual(len(math_segs), 3)

    def test_render_missing_text_field(self):
        status, body = self._post("/api/latex/render/", {"content": "x"})
        self.assertEqual(status, 400)

    def test_render_empty_text(self):
        status, body = self._post("/api/latex/render/", {"text": ""})
        self.assertEqual(status, 200)
        self.assertFalse(body["has_math"])


class TestLatexBatchEndpoint(TestCase):
    def _post(self, data):
        resp = self.client.post(
            "/api/latex/render-batch/",
            data=json.dumps(data),
            content_type="application/json",
        )
        return resp.status_code, json.loads(resp.content)

    def test_batch_single_item(self):
        status, body = self._post({
            "items": [{"id": "q1", "text": "Find $x$ if $x^2 = 9$."}]
        })
        self.assertEqual(status, 200)
        self.assertEqual(len(body["items"]), 1)
        item = body["items"][0]
        self.assertEqual(item["id"], "q1")
        self.assertTrue(item["has_math"])
        self.assertIn("text_segments", item)

    def test_batch_with_options(self):
        status, body = self._post({
            "items": [{
                "id": "q2",
                "text": "Which equals $\\sqrt{4}$?",
                "options": ["$1$", "$2$", "$3$", "$4$"],
            }]
        })
        self.assertEqual(status, 200)
        item = body["items"][0]
        self.assertIsNotNone(item["options_segments"])
        self.assertEqual(len(item["options_segments"]), 4)

    def test_batch_multiple_items(self):
        status, body = self._post({
            "items": [
                {"id": "a", "text": "Plain question."},
                {"id": "b", "text": "Find $\\vec{F}$ for $m = 5$"},
            ]
        })
        self.assertEqual(status, 200)
        self.assertEqual(len(body["items"]), 2)
        self.assertFalse(body["items"][0]["has_math"])
        self.assertTrue(body["items"][1]["has_math"])

    def test_batch_missing_items_key(self):
        status, _ = self._post({"data": []})
        self.assertEqual(status, 400)

    def test_batch_empty_items(self):
        status, body = self._post({"items": []})
        self.assertEqual(status, 200)
        self.assertEqual(body["items"], [])


class TestLatexValidateEndpoint(TestCase):
    def _post(self, data):
        resp = self.client.post(
            "/api/latex/validate/",
            data=json.dumps(data),
            content_type="application/json",
        )
        return resp.status_code, json.loads(resp.content)

    def test_valid_expressions(self):
        status, body = self._post({
            "expressions": ["\\frac{1}{2}", "E = mc^2", "\\alpha + \\beta"]
        })
        self.assertEqual(status, 200)
        for result in body["results"]:
            self.assertTrue(result["valid"])

    def test_mixed_validity(self):
        status, body = self._post({
            "expressions": ["\\frac{d}{dx}", "E = mc^2"]
        })
        self.assertEqual(status, 200)
        self.assertEqual(len(body["results"]), 2)

    def test_empty_expressions_list(self):
        status, body = self._post({"expressions": []})
        self.assertEqual(status, 200)
        self.assertEqual(body["results"], [])

    def test_missing_expressions_key(self):
        status, _ = self._post({"exprs": []})
        self.assertEqual(status, 400)


class TestLatexHealthEndpoint(TestCase):
    def test_health_ok(self):
        resp = self.client.get("/api/latex/health/")
        self.assertEqual(resp.status_code, 200)
        body = json.loads(resp.content)
        self.assertIn(body["status"], ("ok", "degraded"))
        self.assertEqual(body["renderer"], "matplotlib-mathtext")
