"""
Unit tests for the shared annotated_xy_graph renderer.

The seven figures below are the regression suite for the generality claim: each is a real
exam figure (stress-strain, heating curve, blackbody, Maxwell-Boltzmann, radioactive decay,
first-order kinetics, Arrhenius) expressed through AnnotatedXYGraphSchema alone, with no
bespoke code. If one of them stops being expressible, the schema has regressed.

The physics is asserted, not just the byte count: Wien's law must actually move the
blackbody peak to shorter wavelength, a derived half-life must land on the curve, and an
under_curve fill must follow the curve rather than a rectangle. Uses SimpleTestCase — no
database.
"""
import copy
import re

import numpy as np
from django.test import SimpleTestCase
from pydantic import ValidationError

from diagrams.schemas.shared import AnnotatedXYGraphSchema, CurveSpec
from diagrams.service.shared.xygraph import _Curve, render_annotated_xy_graph


def _is_valid_svg(content: str) -> bool:
    return bool(content and "<svg" in content and "</svg>" in content)


def _svg_text(svg: str) -> str:
    """Visible text nodes — matplotlib silently drops text drawn outside the axes limits,
    so 'the label is in the params' does not mean it reached the page."""
    return " ".join(re.findall(r">([^<>]+)<", svg))


def _fill_vertices(svg: str, colour: str) -> int:
    """Number of line segments in the filled path of the given colour."""
    total = 0
    for m in re.finditer(r"<path([^>]*?)/>", svg):
        attrs = m.group(1)
        if colour.lower() in attrs.lower():
            d = re.search(r'd="([^"]+)"', attrs)
            if d:
                total += d.group(1).count("L")
    return total


def _sample(expression: str, x_range, n=4000):
    """Sample a curve the way the renderer does, to assert on peaks."""
    spec = CurveSpec(expression=expression, x_range=x_range)
    return _Curve(spec, 0, x_range, log_x=False)


# ── The seven figures ─────────────────────────────────────────────────────────

STRESS_STRAIN = {
    "title": "Stress-strain curve for a ductile metal",
    "x_label": "Strain (%)",
    "y_label": "Stress (MPa)",
    "x_range": [0, 13.5],
    "curves": [{
        "points": [
            {"x": 0, "y": 0}, {"x": 1, "y": 120}, {"x": 2, "y": 240}, {"x": 3, "y": 360},
            {"x": 3.5, "y": 400}, {"x": 4, "y": 420}, {"x": 4.5, "y": 425},
            {"x": 5, "y": 430}, {"x": 6, "y": 472}, {"x": 7, "y": 512},
            {"x": 8, "y": 542}, {"x": 9, "y": 562}, {"x": 9.5, "y": 565},
            {"x": 10.5, "y": 540}, {"x": 11.5, "y": 500}, {"x": 12, "y": 470}
        ],
        "colour": "#1f77b4", "line_width": 2.4
    }],
    "regions": [
        {"x_from": 0, "x_to": 4, "label": "Elastic region", "colour": "#93C5FD"},
        {"x_from": 4, "x_to": 12, "label": "Plastic region", "colour": "#FCA5A5"}
    ],
    "marked_points": [
        {"x": 3, "label": "P (proportional limit)", "show_dropline": True,
         "label_offset": [24, -56]},
        {"x": 3.5, "label": "E (elastic limit)", "label_offset": [-40, 26]},
        {"x": 4, "label": "Y (yield point)", "label_offset": [10, -22]},
        {"x": 9.5, "label": "U (ultimate strength)", "annotation_style": "crosshair",
         "show_dropline": True, "label_offset": [-30, 14]},
        {"x": 12, "label": "F (fracture)", "annotation_style": "arrow",
         "label_offset": [-28, -40]}
    ],
    "show_legend": False,
}

HEATING_CURVE = {
    "title": "Heating curve of water",
    "x_label": "Heat added (arbitrary units)",
    "y_label": "Temperature (°C)",
    "x_range": [0, 10],
    "y_range": [-30, 155],
    "curves": [{
        "points": [
            {"x": 0, "y": -20}, {"x": 1, "y": 0}, {"x": 3, "y": 0},
            {"x": 5, "y": 100}, {"x": 9, "y": 100}, {"x": 10, "y": 120}
        ],
        "colour": "#d62728", "line_width": 2.4
    }],
    "regions": [
        {"x_from": 0, "x_to": 1, "label": "Solid", "colour": "#93C5FD"},
        {"x_from": 3, "x_to": 5, "label": "Liquid", "colour": "#86EFAC"},
        {"x_from": 9, "x_to": 10, "label": "Gas", "colour": "#FDE68A"}
    ],
    "reference_lines": [
        {"orientation": "horizontal", "value": 0, "label": "Melting point, 0 °C"},
        {"orientation": "horizontal", "value": 100, "label": "Boiling point, 100 °C"}
    ],
    "annotations": [
        {"text": "Melting\n(latent heat of fusion)", "x": 2, "y": 45,
         "target_x": 2, "target_y": 0},
        {"text": "Boiling\n(latent heat of vaporisation)", "x": 6.6, "y": 55,
         "target_x": 7, "target_y": 100}
    ],
    "show_legend": False,
}

BLACKBODY = {
    "title": "Blackbody radiation spectrum at three temperatures",
    "x_label": "Wavelength λ (μm)",
    "y_label": "Spectral radiance (arb. units)",
    "x_range": [0.1, 3.0],
    "curve_family": {
        "name": "Temperature",
        "members": [
            {"expression": "100/(x**5*(exp(14387.77/(3000*x)) - 1))", "label": "T = 3000 K"},
            {"expression": "100/(x**5*(exp(14387.77/(4000*x)) - 1))", "label": "T = 4000 K"},
            {"expression": "100/(x**5*(exp(14387.77/(5000*x)) - 1))", "label": "T = 5000 K"}
        ]
    },
    "marked_points": [
        {"x": 0.966, "curve": "T = 3000 K", "label": "λ_max", "show_dropline": True,
         "label_offset": [6, 6]},
        {"x": 0.7245, "curve": "T = 4000 K", "label": "λ_max", "label_offset": [6, 6]},
        {"x": 0.5796, "curve": "T = 5000 K", "label": "λ_max", "label_offset": [-8, 10]}
    ],
    "annotations": [
        {"text": "Wien's law: λ_max shifts to shorter\nwavelength as T rises",
         "x": 1.95, "y": 8.9, "target_x": 0.62, "target_y": 9.9}
    ],
    "legend_loc": "center right",
}

MAXWELL = {
    "title": "Maxwell-Boltzmann speed distribution (N₂)",
    "x_label": "Molecular speed v (m s⁻¹)",
    "y_label": "Fraction of molecules f(v)  (×10⁻³ s m⁻¹)",
    "x_range": [0, 1800],
    "curve_family": {
        "name": "Temperature",
        "members": [
            {"expression": "3.00132e-5*x**2*exp(-5.6133e-6*x**2)", "label": "T = 300 K"},
            {"expression": "1.06113e-5*x**2*exp(-2.80665e-6*x**2)", "label": "T = 600 K"},
            {"expression": "3.75165e-6*x**2*exp(-1.40333e-6*x**2)", "label": "T = 1200 K"}
        ]
    },
    "marked_points": [
        {"x": 422, "curve": "T = 300 K", "label": "v_mp", "show_dropline": True,
         "label_offset": [-34, 6]},
        {"x": 597, "curve": "T = 600 K", "label": "v_mp", "label_offset": [4, 8]},
        {"x": 844, "curve": "T = 1200 K", "label": "v_mp", "label_offset": [4, 8]}
    ],
    "annotations": [
        {"text": "distribution broadens and flattens,\npeak shifts to higher speed as T rises",
         "x": 1230, "y": 1.5, "target_x": 900, "target_y": 0.95}
    ],
    "legend_loc": "upper right",
}

DECAY = {
    "title": "Radioactive decay: N = N₀e^(-λt),  t₁/₂ = 8 days",
    "x_label": "Time t (days)",
    "y_label": "Number of undecayed nuclei N (%)",
    "x_range": [0, 34],
    "y_range": [0, 118],
    "curves": [{
        "expression": "100*exp(-0.0866434*x)", "label": "N = N₀e^(-λt)",
        "colour": "#1f77b4", "line_width": 2.4
    }],
    "marked_points": [
        {"x": 8, "label": "t₁/₂", "show_dropline": True, "show_coordinates": True,
         "label_offset": [8, 8]},
        {"x": 16, "label": "2t₁/₂", "show_dropline": True, "show_coordinates": True,
         "label_offset": [8, 8]},
        {"x": 24, "label": "3t₁/₂", "show_dropline": True, "show_coordinates": True,
         "label_offset": [8, 8]}
    ],
    "reference_lines": [
        {"orientation": "horizontal", "value": 50, "label": "N₀/2"},
        {"orientation": "horizontal", "value": 25, "label": "N₀/4"}
    ],
    "asymptotes": [
        {"orientation": "horizontal", "value": 0, "label": "N tends to 0",
         "line_style": "dashed"}
    ],
    "shaded_regions": [
        {"x_from": 0, "x_to": 8, "under_curve": True, "colour": "#93C5FD", "alpha": 0.35,
         "label": "one half-life"}
    ],
    "legend_loc": "upper right",
}

FIRST_ORDER = {
    "title": "First-order kinetics: [A] against t on a log axis",
    "x_label": "Time t (s)",
    "y_label": "[A] (mol L⁻¹)",
    "x_range": [0, 20],
    "log_y": True,
    "curves": [
        {"expression": "0.1*exp(-0.35*x)", "label": "[A] = [A]₀e^(-kt)",
         "colour": "#1f77b4", "line_width": 2.2},
        {"points": [
            {"x": 0, "y": 0.1}, {"x": 4, "y": 0.0247}, {"x": 8, "y": 0.00608},
            {"x": 12, "y": 0.0015}, {"x": 16, "y": 0.00037}, {"x": 20, "y": 0.0000912}
        ], "label": "experimental points", "colour": "#d62728", "line_style": "dotted",
         "show_marker": True, "line_width": 1.2}
    ],
    "annotations": [
        {"text": "straight line on a log axis:\nfirst order,  slope = -k/2.303",
         "x": 13.5, "y": 0.05, "target_x": 8, "target_y": 0.00608}
    ],
    "legend_loc": "lower left",
}

ARRHENIUS = {
    "title": "Arrhenius plot: ln k against 1/T",
    "x_label": "1/T  (10⁻³ K⁻¹)",
    "y_label": "ln k",
    "x_range": [2.4, 3.6],
    "curves": [
        {"expression": "25 - 6.014*x", "label": "ln k = ln A − Ea/RT",
         "colour": "#1f77b4", "line_width": 2.2},
        {"points": [
            {"x": 2.5, "y": 9.99}, {"x": 2.75, "y": 8.45}, {"x": 3.0, "y": 6.97},
            {"x": 3.25, "y": 5.47}, {"x": 3.5, "y": 3.94}
        ], "label": "measured rate constants", "colour": "#d62728",
         "line_style": "dotted", "show_marker": True, "line_width": 1.0}
    ],
    "marked_points": [
        {"x": 2.5, "show_coordinates": True, "annotation_style": "crosshair",
         "label_offset": [8, 6]},
        {"x": 3.5, "show_coordinates": True, "annotation_style": "crosshair",
         "label_offset": [-30, 12]}
    ],
    "annotations": [
        {"text": "slope = −Ea/R", "x": 3.05, "y": 8.6, "target_x": 2.9, "target_y": 7.56}
    ],
    "legend_loc": "lower left",
}


class SevenExamFiguresTests(SimpleTestCase):
    """One schema, seven textbook figures, no bespoke code."""

    def test_1_stress_strain_curve(self):
        svg = render_annotated_xy_graph(STRESS_STRAIN)
        self.assertTrue(_is_valid_svg(svg))
        text = _svg_text(svg)
        for label in ["Elastic region", "Plastic region", "P (proportional limit)",
                      "E (elastic limit)", "Y (yield point)", "U (ultimate strength)",
                      "F (fracture)"]:
            self.assertIn(label, text)

    def test_1_stress_strain_marked_points_sit_on_the_curve(self):
        # y is never supplied for these points — it is interpolated on the explicit curve
        curve = _Curve(CurveSpec(**STRESS_STRAIN["curves"][0]), 0, (0, 13.5), log_x=False)
        self.assertAlmostEqual(curve.y_at(3), 360.0)      # proportional limit
        self.assertAlmostEqual(curve.y_at(4), 420.0)      # yield point
        self.assertAlmostEqual(curve.y_at(9.5), 565.0)    # ultimate strength
        self.assertAlmostEqual(curve.y_at(12), 470.0)     # fracture
        self.assertAlmostEqual(curve.y_at(1.5), 180.0)    # between two given points

    def test_2_heating_curve(self):
        svg = render_annotated_xy_graph(HEATING_CURVE)
        self.assertTrue(_is_valid_svg(svg))
        text = _svg_text(svg)
        for label in ["Solid", "Liquid", "Gas", "Melting point, 0 °C",
                      "Boiling point, 100 °C"]:
            self.assertIn(label, text)

    def test_2_heating_curve_has_two_flat_plateaus(self):
        curve = _Curve(CurveSpec(**HEATING_CURVE["curves"][0]), 0, (0, 10), log_x=False)
        for x in (1.5, 2.0, 2.5):          # melting plateau
            self.assertAlmostEqual(curve.y_at(x), 0.0)
        for x in (6.0, 7.0, 8.0):          # boiling plateau
            self.assertAlmostEqual(curve.y_at(x), 100.0)

    def test_3_blackbody_family(self):
        svg = render_annotated_xy_graph(BLACKBODY)
        self.assertTrue(_is_valid_svg(svg))
        text = _svg_text(svg)
        for label in ["T = 3000 K", "T = 4000 K", "T = 5000 K", "Temperature"]:
            self.assertIn(label, text)

    def test_3_blackbody_peak_obeys_wiens_law(self):
        """The peak MUST move to shorter wavelength as T rises, and the renderer must
        sample densely enough that the peak is not flattened."""
        peaks = []
        for member in BLACKBODY["curve_family"]["members"]:
            curve = _sample(member["expression"], (0.1, 3.0))
            peaks.append(float(curve.x[int(np.nanargmax(curve.y))]))
        self.assertGreater(peaks[0], peaks[1])       # 3000 K peaks redder than 4000 K
        self.assertGreater(peaks[1], peaks[2])       # 4000 K peaks redder than 5000 K
        for peak, T in zip(peaks, (3000, 4000, 5000)):
            self.assertAlmostEqual(peak, 2898.0 / T, delta=0.01)   # Wien displacement

    def test_4_maxwell_boltzmann_family(self):
        svg = render_annotated_xy_graph(MAXWELL)
        self.assertTrue(_is_valid_svg(svg))
        self.assertIn("T = 1200 K", _svg_text(svg))

    def test_4_maxwell_boltzmann_broadens_and_shifts_right(self):
        peaks, heights = [], []
        for member in MAXWELL["curve_family"]["members"]:
            curve = _sample(member["expression"], (0, 1800))
            idx = int(np.nanargmax(curve.y))
            peaks.append(float(curve.x[idx]))
            heights.append(float(curve.y[idx]))
        self.assertLess(peaks[0], peaks[1])          # peak shifts to higher speed with T
        self.assertLess(peaks[1], peaks[2])
        self.assertGreater(heights[0], heights[1])   # and flattens
        self.assertGreater(heights[1], heights[2])
        self.assertAlmostEqual(peaks[0], 422.0, delta=2.0)   # v_mp = sqrt(2kT/m)

    def test_5_radioactive_decay_half_lives_are_derived(self):
        svg = render_annotated_xy_graph(DECAY)
        self.assertTrue(_is_valid_svg(svg))
        text = _svg_text(svg)
        # The y values were never supplied — they were evaluated on the curve
        self.assertIn("t₁/₂ (8, 50)", text)
        self.assertIn("2t₁/₂ (16, 25)", text)
        self.assertIn("3t₁/₂ (24, 12.5)", text)

    def test_6_first_order_kinetics_is_straight_on_a_log_axis(self):
        svg = render_annotated_xy_graph(FIRST_ORDER)
        self.assertTrue(_is_valid_svg(svg))
        curve = _sample("0.1*exp(-0.35*x)", (0, 20))
        ln_a = np.log(curve.y)
        # a first-order plot is a straight line in ln[A]: constant gradient == -k
        gradient = np.gradient(ln_a, curve.x)
        self.assertTrue(np.allclose(gradient, -0.35, atol=1e-6))

    def test_7_arrhenius_plot(self):
        svg = render_annotated_xy_graph(ARRHENIUS)
        self.assertTrue(_is_valid_svg(svg))
        self.assertIn("ln k", _svg_text(svg))
        curve = _sample("25 - 6.014*x", (2.4, 3.6))
        # slope = -Ea/R, read straight off the line the renderer drew
        slope = (curve.y[-1] - curve.y[0]) / (curve.x[-1] - curve.x[0])
        self.assertAlmostEqual(slope, -6.014, places=6)
        self.assertAlmostEqual(curve.y_at(2.5), 9.965, places=6)


class DerivationTests(SimpleTestCase):
    """Anything derivable is computed, never trusted from params."""

    def test_marked_point_without_y_derives_it_from_an_expression_curve(self):
        params = {
            "curves": [{"expression": "100*exp(-0.0866434*x)"}],
            "x_range": [0, 30],
            "marked_points": [{"x": 8, "show_coordinates": True}],
        }
        svg = render_annotated_xy_graph(params)
        self.assertIn("(8, 50)", _svg_text(svg))

    def test_marked_point_without_y_derives_it_from_a_point_list_curve(self):
        params = {
            "curves": [{"points": [{"x": 0, "y": 0}, {"x": 2, "y": 10}, {"x": 4, "y": 30}]}],
            "marked_points": [{"x": 3, "show_coordinates": True}],
        }
        svg = render_annotated_xy_graph(params)
        self.assertIn("(3, 20)", _svg_text(svg))     # interpolated, not supplied

    def test_marked_point_selects_the_named_curve(self):
        params = {
            "curves": [
                {"expression": "x", "label": "linear"},
                {"expression": "x**2", "label": "quadratic"},
            ],
            "x_range": [0, 5],
            "marked_points": [{"x": 3, "curve": "quadratic", "show_coordinates": True}],
        }
        self.assertIn("(3, 9)", _svg_text(render_annotated_xy_graph(params)))

    def test_marked_point_off_the_end_of_a_point_curve_is_an_error(self):
        params = {
            "curves": [{"points": [{"x": 0, "y": 0}, {"x": 4, "y": 30}]}],
            "marked_points": [{"x": 99}],
        }
        with self.assertRaises(ValueError):
            render_annotated_xy_graph(params)

    def test_under_curve_region_follows_the_curve_not_a_rectangle(self):
        curved = render_annotated_xy_graph(DECAY)
        rect_params = copy.deepcopy(DECAY)
        rect_params["shaded_regions"][0]["under_curve"] = False
        rect_params["shaded_regions"][0]["y_to"] = 100
        rect = render_annotated_xy_graph(rect_params)

        self.assertNotEqual(curved, rect)
        # the fill under the curve is sampled against the curve; a rectangle has 4 corners
        self.assertGreater(_fill_vertices(curved, "#93c5fd"), 100)
        self.assertLessEqual(_fill_vertices(rect, "#93c5fd"), 8)

    def test_expression_curve_is_sampled_densely_enough_to_keep_its_peak(self):
        curve = _sample("100/(x**5*(exp(14387.77/(5000*x)) - 1))", (0.1, 3.0))
        self.assertAlmostEqual(float(np.nanmax(curve.y)), 10.77, delta=0.05)


class SafetyTests(SimpleTestCase):
    """A bad expression must fail loudly — the caller's repair loop feeds the error back to
    the model. Silently drawing an empty plot is the one unacceptable outcome."""

    def test_syntactically_malformed_expression_raises_value_error(self):
        with self.assertRaises(ValueError):
            render_annotated_xy_graph({"curves": [{"expression": "x**"}],
                                       "x_range": [0, 5]})

    def test_unknown_symbol_raises_value_error(self):
        # sympy's own namespace makes this a trap: parsed unrestricted, "N0" is N(0) — the
        # evalf function — and the expression silently collapses to a flat zero line.
        with self.assertRaises(ValueError) as ctx:
            render_annotated_xy_graph({"curves": [{"expression": "N0*exp(-k*x)"}],
                                       "x_range": [0, 5]})
        self.assertIn("undefined symbol", str(ctx.exception))

    def test_unknown_function_raises_value_error(self):
        with self.assertRaises(ValueError) as ctx:
            render_annotated_xy_graph({"curves": [{"expression": "wibble(x) + 1"}],
                                       "x_range": [0, 5]})
        self.assertIn("wibble", str(ctx.exception))

    def test_multi_letter_name_is_not_silently_shredded_into_a_product(self):
        """split_symbols would turn 'kA' into k*A and 'N0' into N*0 = 0 — a flat zero line
        drawn where the model expected a curve."""
        with self.assertRaises(ValueError):
            render_annotated_xy_graph({"curves": [{"expression": "kA*x"}],
                                       "x_range": [0, 5]})

    def test_expression_with_no_finite_values_raises_value_error(self):
        with self.assertRaises(ValueError) as ctx:
            render_annotated_xy_graph({"curves": [{"expression": "log(-1 - x**2)"}],
                                       "x_range": [1, 5]})
        self.assertRegex(str(ctx.exception), "complex-valued|no finite values")

    def test_curve_needs_exactly_one_of_expression_or_points(self):
        with self.assertRaises(ValidationError):
            AnnotatedXYGraphSchema(curves=[{"expression": "x", "points": [{"x": 0, "y": 0},
                                                                          {"x": 1, "y": 1}]}])
        with self.assertRaises(ValidationError):
            AnnotatedXYGraphSchema(curves=[{"label": "nothing"}])

    def test_graph_needs_a_curve(self):
        with self.assertRaises(ValidationError):
            AnnotatedXYGraphSchema(title="empty")

    def test_expression_curve_without_any_x_range_is_an_error(self):
        with self.assertRaises(ValueError):
            render_annotated_xy_graph({"curves": [{"expression": "x**2"}]})


class RenderContractTests(SimpleTestCase):

    def test_same_params_give_byte_identical_svg(self):
        self.assertEqual(render_annotated_xy_graph(BLACKBODY),
                         render_annotated_xy_graph(BLACKBODY))

    def test_american_spelling_of_colour_is_accepted(self):
        svg = render_annotated_xy_graph({
            "curves": [{"expression": "x", "color": "#d62728"}],
            "x_range": [0, 5],
        })
        self.assertIn("#d62728", svg)

    def test_arrows_is_an_alias_for_annotations(self):
        svg = render_annotated_xy_graph({
            "curves": [{"expression": "x"}],
            "x_range": [0, 5],
            "arrows": [{"text": "note", "x": 2, "y": 3, "target_x": 4, "target_y": 4}],
        })
        self.assertIn("note", _svg_text(svg))
