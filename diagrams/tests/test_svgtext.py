"""Sub/superscripts must survive rasterization, not just validation.

The bug this guards against shipped silently for a long time: Arial carries no U+2080-2089,
and cairosvg (the rasterizer behind the PNG/PDF print path) does not fall back per glyph the
way a browser does. So `m₁` rendered as `m□` on the printed paper while looking perfect in
the web UI — and every existing test passed, because they only ever asserted that the output
contained "<svg". The prompt catalog tells the model to emit `m₁`, `R₁`, `Zn²⁺`, so this fired
on the most common physics and chemistry figures.

The invariant: no raw sub/superscript codepoint may reach the SVG. It must be re-created as a
shifted <tspan> carrying an ASCII digit, which every font has.
"""
from django.test import SimpleTestCase

import svgwrite

from diagrams.service.svgtext import fold, has_special, make_text

RAW = "₀₁₂₃₄₅₆₇₈₉⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻"


def _svg_of(txt: str) -> str:
    dwg = svgwrite.Drawing(size=("100px", "100px"))
    dwg.add(make_text(dwg, txt, (10, 10), font_size=14, font_family="Arial, sans-serif"))
    return dwg.tostring()


class SubscriptRasterisationTests(SimpleTestCase):

    def test_no_raw_subscript_codepoint_survives_into_the_svg(self):
        """THE one that matters. A raw ₁ in the SVG is a □ on the printed paper."""
        svg = _svg_of("m₁ and m₂ and Zn²⁺")
        for ch in RAW:
            self.assertNotIn(ch, svg, f"raw {ch!r} reached the SVG — it will print as tofu")

    def test_the_digit_is_preserved_not_dropped(self):
        """Stripping the glyph is only safe if the number survives — m₁ must not become m."""
        svg = _svg_of("m₁")
        self.assertIn("tspan", svg)
        self.assertIn("1", svg)

    def test_subscript_and_superscript_shift_in_opposite_directions(self):
        """If both shifted the same way, H₂O and x² would be indistinguishable."""
        sub = _svg_of("x₂")
        sup = _svg_of("x²")
        self.assertIn('dy="4.2"', sub)     # +0.30 x 14, below the baseline
        self.assertIn('dy="-5.88"', sup)   # -0.42 x 14, above it

    def test_returning_to_the_baseline_undoes_the_shift(self):
        """dy is relative to the previous tspan, so a trailing run must shift back or the
        rest of the label creeps down the page."""
        svg = _svg_of("m₁g")
        self.assertIn('dy="-4.2"', svg)

    def test_plain_text_is_left_alone(self):
        self.assertFalse(has_special("Normal force N"))
        self.assertIn("Normal force N", _svg_of("Normal force N"))

    def test_fold_flattens_to_ascii_for_contexts_that_cannot_carry_tspans(self):
        self.assertEqual(fold("m₁ Zn²⁺ V₀"), "m1 Zn2+ V0")


class RendererIntegrationTests(SimpleTestCase):

    def test_physics_renderer_emits_no_raw_subscripts(self):
        """The catalog literally instructs the model to send masses labelled m₁/m₂."""
        from diagrams.service.physics.renderer import render_physics
        svg = render_physics("pulley_system", {
            "pulley_count": 1,
            "masses": [{"label": "m₁", "side": "left"}, {"label": "m₂", "side": "right"}],
        })
        for ch in RAW:
            self.assertNotIn(ch, svg)
        self.assertIn("tspan", svg)

    def test_physics_render_is_byte_deterministic(self):
        """matplotlib stamps a <dc:date> and salts clip-path ids with a fresh uuid4 per call,
        so 'same params -> same SVG' was quietly false. Caching and diffing both rely on it."""
        from diagrams.service.physics.renderer import render_physics
        params = {"pulley_count": 1, "masses": [{"label": "m₁"}, {"label": "m₂"}]}
        self.assertEqual(render_physics("pulley_system", params),
                         render_physics("pulley_system", params))
