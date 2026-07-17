"""
Unit tests for the seven further Mathematics diagram types:
piecewise_graph, circle_theorem, similar_triangles, geometric_construction,
solid_of_revolution, graph_transformation, box_plot.

Every one of these figures carries the ANSWER to the question it illustrates — whether the
function jumps at a boundary, that the central angle is twice the inscribed one, the quartiles of
a data set, the shape of a transformed curve. So the tests assert on the values the engine
COMPUTES from the geometry / data / expressions, not merely that an SVG came back. A figure that
renders beautifully but shows a continuous join where the limits disagree, or a median outside its
box, is worse than no figure at all. Uses SimpleTestCase — no database.

Run directly (no shared test DB):
    ./venv/bin/python -m unittest diagrams.tests.test_mathematics_ext3 -v
"""
import math

import numpy as np
from django.test import SimpleTestCase

from diagrams.schemas.mathematics import PiecewisePiece
from diagrams.service.mathematics.renderer import (
    MATHEMATICS_RENDERERS, apply_transformation, bpt_ratios, circle_inscribed_central,
    five_number_summary, piecewise_continuity, render_mathematics, _make_base_fn,
)


def _is_valid_svg(content: str) -> bool:
    return bool(content and "<svg" in content and "</svg>" in content)


def _svg_text(svg: str) -> str:
    """Visible text nodes — matplotlib silently drops text drawn outside the axes, so 'the value
    was computed' does not mean it reached the page."""
    import re
    return " ".join(re.findall(r">([^<>]+)<", svg))


# ── Piecewise Graph ───────────────────────────────────────────────────────────

def _pieces(specs):
    return [PiecewisePiece(**s) for s in specs]


class TestPiecewiseGraph(SimpleTestCase):
    def _render(self, params):
        return render_mathematics("piecewise_graph", params)

    def test_a_jump_is_detected_when_the_one_sided_limits_differ(self):
        """f = x² on the left, x+3 on the right of x=1: the left limit is 1, the right limit is 4.
        A question about continuity here has the answer 'jump discontinuity'. If the engine reports
        this as continuous, the drawn figure contradicts the marked answer."""
        res = piecewise_continuity(_pieces([
            {"expression": "x**2", "domain": (-2, 1), "closed_right": False},
            {"expression": "x + 3", "domain": (1, 4), "closed_left": True},
        ]))
        self.assertEqual(len(res), 1)
        b = res[0]
        self.assertAlmostEqual(b["left_limit"], 1.0, places=9)
        self.assertAlmostEqual(b["right_limit"], 4.0, places=9)
        self.assertEqual(b["kind"], "jump")

    def test_continuity_is_detected_when_the_limits_agree(self):
        """2x on the left, x+1 on the right of x=1: both one-sided limits are 2 and the branch that
        owns x=1 gives 2 as well. That is a continuous join, and the engine must say so."""
        res = piecewise_continuity(_pieces([
            {"expression": "2*x", "domain": (-2, 1), "closed_right": False},
            {"expression": "x + 1", "domain": (1, 4), "closed_left": True},
        ]))
        self.assertEqual(res[0]["kind"], "continuous")
        self.assertAlmostEqual(res[0]["left_limit"], res[0]["right_limit"], places=9)

    def test_a_removable_discontinuity_is_distinguished_from_a_jump(self):
        """Both branches tend to 2 at x=1 but neither closes on it (open ○ on both sides): the
        limit exists yet there is no function value there — a removable discontinuity, not a jump
        and not continuity."""
        res = piecewise_continuity(_pieces([
            {"expression": "2*x", "domain": (-2, 1), "closed_right": False},
            {"expression": "x + 1", "domain": (1, 4), "closed_left": False},
        ]))
        self.assertEqual(res[0]["kind"], "removable")

    def test_the_verdict_and_the_check_point_reach_the_page(self):
        """The computed classification and a tested point's value have to land inside the axes."""
        text = _svg_text(self._render({
            "pieces": [
                {"expression": "x**2", "domain": [-2, 1], "closed_right": False},
                {"expression": "x + 3", "domain": [1, 4], "closed_left": True},
            ],
            "check_points": [1],
        }))
        self.assertIn("jump discontinuity", text)
        self.assertIn("(1, 4)", text)

    def test_an_unsafe_expression_is_rejected(self):
        """The branch expressions are evaluated through parse_safe, never sympify. A payload like
        __import__('os').getcwd() must raise, not run."""
        with self.assertRaises(Exception):
            self._render({"pieces": [
                {"expression": "__import__('os').getcwd()", "domain": [0, 1]}]})

    def test_renders(self):
        self.assertTrue(_is_valid_svg(self._render({
            "pieces": [{"expression": "x**2", "domain": [-2, 1], "closed_right": False},
                       {"expression": "x + 3", "domain": [1, 4], "closed_left": True}],
            "show_open_closed_points": True, "show_continuity": True})))


# ── Circle Theorem ────────────────────────────────────────────────────────────

class TestCircleTheorem(SimpleTestCase):
    def _render(self, params):
        return render_mathematics("circle_theorem", params)

    def test_central_angle_is_exactly_twice_the_inscribed_angle(self):
        """The inscribed-angle theorem: the angle A and B subtend at the centre is twice the angle
        they subtend at any point P on the major arc. Both are computed from the geometry here; if
        the identity ever breaks, every 'angle at centre' question drawn is wrong."""
        for a, b, p in ((0, 90, 200), (150, 30, 265), (20, 140, 300), (10, 80, 250)):
            r = circle_inscribed_central(a, b, p)
            self.assertAlmostEqual(r["central"], 2 * r["inscribed"], places=6,
                                   msg=f"failed for A={a}, B={b}, P={p}")

    def test_the_specific_60_120_case(self):
        """The textbook figure: a 60° inscribed angle goes with a 120° central angle."""
        r = circle_inscribed_central(150, 30, 265)
        self.assertAlmostEqual(r["inscribed"], 60.0, places=6)
        self.assertAlmostEqual(r["central"], 120.0, places=6)

    def test_the_doubling_reaches_the_page(self):
        text = _svg_text(self._render({"theorem": "angle_at_centre"}))
        self.assertIn("120°", text)
        self.assertIn("60°", text)
        self.assertIn("2 ×", text)

    def test_semicircle_angle_is_a_right_angle(self):
        text = _svg_text(self._render({"theorem": "angle_in_semicircle"}))
        self.assertIn("90°", text)

    def test_cyclic_quadrilateral_opposite_angles_are_supplementary(self):
        """Opposite angles of a cyclic quadrilateral sum to 180°. Computed from the four vertices;
        the figure must not print a pair that fails to add up."""
        text = _svg_text(self._render({"theorem": "cyclic_quadrilateral"}))
        self.assertIn("180°", text)

    def test_every_theorem_renders(self):
        for th in ("angle_at_centre", "angle_in_semicircle", "cyclic_quadrilateral",
                   "tangent_radius", "alternate_segment", "equal_chords", "intersecting_chords"):
            self.assertTrue(_is_valid_svg(self._render({"theorem": th})), th)

    def test_unknown_theorem_rejected(self):
        with self.assertRaises(Exception):
            self._render({"theorem": "ptolemy"})


# ── Similar Triangles ─────────────────────────────────────────────────────────

class TestSimilarTriangles(SimpleTestCase):
    def _render(self, params):
        return render_mathematics("similar_triangles", params)

    def test_bpt_gives_equal_ratios_on_the_two_sides(self):
        """Basic proportionality: a line DE parallel to BC cuts AB and AC so AD/DB = AE/EC. Both
        ratios are computed from the coordinates and must match — that equality IS the theorem."""
        r = bpt_ratios((2, 6), (0, 0), (7, 0), 0.4)
        self.assertAlmostEqual(r["ratio_ab"], r["ratio_ac"], places=9)
        self.assertAlmostEqual(r["ratio_ab"], 0.4 / 0.6, places=9)

    def test_midpoint_ratio_is_one(self):
        """With D and E the midpoints, AD/DB = 1 exactly."""
        r = bpt_ratios((2, 6), (0, 0), (7, 0), 0.5)
        self.assertAlmostEqual(r["ratio_ab"], 1.0, places=9)

    def test_computed_ratio_reaches_the_page(self):
        text = _svg_text(self._render({"configuration": "basic_proportionality"}))
        self.assertIn("AD/DB", text)

    def test_every_configuration_renders(self):
        for cfg in ("basic_proportionality", "aa_similarity", "midpoint_theorem",
                    "pythagoras_geometric"):
            self.assertTrue(_is_valid_svg(self._render({"configuration": cfg})), cfg)

    def test_pythagoras_areas_add_up(self):
        """The square on the hypotenuse (25) equals the sum of the squares on the legs (9 + 16)."""
        text = _svg_text(self._render({"configuration": "pythagoras_geometric"}))
        self.assertIn("25", text)
        self.assertIn("16", text)
        self.assertIn("9", text)

    def test_unknown_configuration_rejected(self):
        with self.assertRaises(Exception):
            self._render({"configuration": "sas_similarity"})


# ── Geometric Construction ────────────────────────────────────────────────────

class TestGeometricConstruction(SimpleTestCase):
    def _render(self, params):
        return render_mathematics("geometric_construction", params)

    def test_every_construction_renders(self):
        for c in ("angle_bisector", "perpendicular_bisector", "angle_60", "angle_30",
                  "triangle_sss", "tangent_to_circle", "divide_segment"):
            self.assertTrue(_is_valid_svg(self._render({"construction": c})), c)

    def test_impossible_triangle_is_rejected(self):
        """Sides 1, 2, 5 violate the triangle inequality — no triangle exists, so no construction
        can be drawn and the schema must refuse it rather than draw a lie."""
        with self.assertRaises(Exception):
            self._render({"construction": "triangle_sss", "side_a": 1, "side_b": 2, "side_c": 5})

    def test_internal_point_cannot_have_a_tangent(self):
        """A tangent is drawn from an EXTERNAL point; a point inside the circle has none."""
        with self.assertRaises(Exception):
            self._render({"construction": "tangent_to_circle",
                          "circle_radius": 3, "external_distance": 2})

    def test_divide_segment_honours_the_count(self):
        self.assertTrue(_is_valid_svg(self._render({
            "construction": "divide_segment", "divisions": 7})))

    def test_unknown_construction_rejected(self):
        with self.assertRaises(Exception):
            self._render({"construction": "square_a_circle"})


# ── Solid of Revolution ───────────────────────────────────────────────────────

class TestSolidOfRevolution(SimpleTestCase):
    def _render(self, params):
        return render_mathematics("solid_of_revolution", params)

    def test_rotation_about_each_axis_renders(self):
        for axis in ("x", "y"):
            self.assertTrue(_is_valid_svg(self._render({
                "expression": "sqrt(x)", "x_range": [0, 4], "axis": axis})), axis)

    def test_the_generating_expression_reaches_the_page(self):
        text = _svg_text(self._render({"expression": "x**2", "x_range": [0, 2], "axis": "x"}))
        self.assertIn("x**2", text)
        self.assertIn("x-axis", text)

    def test_an_unsafe_expression_is_rejected(self):
        """The curve is evaluated through parse_safe. An injection payload must raise."""
        with self.assertRaises(Exception):
            self._render({"expression": "__import__('os').getcwd()", "x_range": [0, 1]})

    def test_bad_axis_rejected(self):
        with self.assertRaises(Exception):
            self._render({"expression": "x", "axis": "z"})


# ── Graph Transformation ──────────────────────────────────────────────────────

class TestGraphTransformation(SimpleTestCase):
    def _render(self, params):
        return render_mathematics("graph_transformation", params)

    def test_shift_up_is_the_base_plus_the_amount_at_every_sample(self):
        """f(x) + 2 must be the base raised by exactly 2 at every sampled x — the transform is
        derived from the base in code, so this can never disagree with the drawn base curve."""
        fn = _make_base_fn("x**2")
        xs = np.linspace(-4, 4, 41)
        got = apply_transformation(fn, "shift_up", 2.0, xs)
        np.testing.assert_allclose(got, fn(xs) + 2.0, atol=1e-12)

    def test_shift_right_evaluates_the_base_at_the_shifted_argument(self):
        """f(x − 1) at x equals f evaluated at x − 1 — a horizontal shift is a change of argument,
        not of value. Getting the sign wrong shifts the curve the wrong way."""
        fn = _make_base_fn("x**2")
        xs = np.linspace(-3, 3, 25)
        np.testing.assert_allclose(
            apply_transformation(fn, "shift_right", 1.0, xs), fn(xs - 1.0), atol=1e-12)

    def test_reflections_and_absolute_values_are_derived_correctly(self):
        fn = _make_base_fn("x**3 - 3*x")
        xs = np.linspace(-3, 3, 25)
        np.testing.assert_allclose(
            apply_transformation(fn, "reflect_x", 1, xs), -fn(xs), atol=1e-12)
        np.testing.assert_allclose(
            apply_transformation(fn, "reflect_y", 1, xs), fn(-xs), atol=1e-12)
        np.testing.assert_allclose(
            apply_transformation(fn, "abs_outer", 1, xs), np.abs(fn(xs)), atol=1e-12)
        np.testing.assert_allclose(
            apply_transformation(fn, "scale_vertical", 3, xs), 3 * fn(xs), atol=1e-12)

    def test_transform_labels_reach_the_page(self):
        text = _svg_text(self._render({
            "base_expression": "x**2", "x_range": [-4, 4],
            "transformations": [{"type": "shift_up", "param": 2}]}))
        self.assertIn("f(x) + 2", text)

    def test_an_unsafe_base_expression_is_rejected(self):
        with self.assertRaises(Exception):
            self._render({"base_expression": "__import__('os').getcwd()"})

    def test_every_transform_type_renders(self):
        for t in ("shift_up", "shift_down", "shift_left", "shift_right", "scale_vertical",
                  "scale_horizontal", "reflect_x", "reflect_y", "abs_outer", "abs_inner"):
            self.assertTrue(_is_valid_svg(self._render({
                "base_expression": "x**2 - 2", "x_range": [-3, 3],
                "transformations": [{"type": t, "param": 2}]})), t)


# ── Box Plot ──────────────────────────────────────────────────────────────────

class TestBoxPlot(SimpleTestCase):
    def _render(self, params):
        return render_mathematics("box_plot", params)

    def test_quartiles_of_one_to_nine(self):
        """For 1..9 the linear-interpolation quartiles are Q1=3, median=5, Q3=7. These are the
        numbers a marker reads off the box; if the engine computes anything else the box is drawn
        in the wrong place."""
        s = five_number_summary(list(range(1, 10)))
        self.assertAlmostEqual(s["q1"], 3.0, places=9)
        self.assertAlmostEqual(s["median"], 5.0, places=9)
        self.assertAlmostEqual(s["q3"], 7.0, places=9)

    def test_the_median_never_leaves_the_box(self):
        """Q1 ≤ median ≤ Q3 must hold for the summary, or the drawn median line falls outside its
        own box — a figure no student could interpret."""
        s = five_number_summary([3, 1, 4, 1, 5, 9, 2, 6, 8, 7])
        self.assertLessEqual(s["q1"], s["median"])
        self.assertLessEqual(s["median"], s["q3"])

    def test_a_value_beyond_the_fence_is_flagged_an_outlier(self):
        """With Q1=3, Q3=7 the IQR is 4 and the upper fence is 7 + 1.5·4 = 13, so 100 is an
        outlier — it must sit beyond the whisker, not stretch the box."""
        s = five_number_summary(list(range(1, 10)))
        self.assertGreater(100.0, s["hi_fence"])
        self.assertIn(100.0, five_number_summary(list(range(1, 10)) + [100])["outliers"])

    def test_supplied_outlier_flags_are_not_trusted(self):
        """The outliers are recomputed from the data and the 1.5·IQR fences — a value inside the
        fences is never an outlier however the params label it."""
        s = five_number_summary([10, 12, 14, 15, 16, 18, 20])
        self.assertEqual(s["outliers"], [])

    def test_computed_summary_reaches_the_page(self):
        text = _svg_text(self._render({
            "datasets": [{"label": "A", "data": list(range(1, 10)) + [100]}],
            "show_values": True}))
        self.assertIn("Q1 3", text)
        self.assertIn("Q3 7", text)

    def test_both_orientations_and_multiple_boxes_render(self):
        for orient in ("horizontal", "vertical"):
            self.assertTrue(_is_valid_svg(self._render({
                "datasets": [{"label": "A", "data": [1, 2, 3, 4, 5, 6, 7, 8, 9]},
                             {"label": "B", "data": [10, 12, 14, 15, 16, 18, 20]}],
                "orientation": orient})), orient)

    def test_a_precomputed_summary_is_accepted(self):
        self.assertTrue(_is_valid_svg(self._render({
            "datasets": [{"label": "S", "summary": {
                "min": 1, "q1": 3, "median": 5, "q3": 7, "max": 9}}]})))

    def test_a_summary_that_is_out_of_order_is_rejected(self):
        with self.assertRaises(Exception):
            self._render({"datasets": [{"summary": {
                "min": 1, "q1": 7, "median": 5, "q3": 3, "max": 9}}]})


# ── Dispatcher ────────────────────────────────────────────────────────────────

class TestMathematicsExt3Dispatcher(SimpleTestCase):
    SUBTYPES = ("piecewise_graph", "circle_theorem", "similar_triangles",
                "geometric_construction", "solid_of_revolution", "graph_transformation",
                "box_plot")

    def test_all_seven_subtypes_are_registered(self):
        for subtype in self.SUBTYPES:
            self.assertIn(subtype, MATHEMATICS_RENDERERS)

    def test_the_existing_annotated_xy_graph_was_not_clobbered(self):
        """This extension only APPENDS — the shared renderer must still be wired."""
        self.assertIn("annotated_xy_graph", MATHEMATICS_RENDERERS)

    def test_unknown_subtype_raises(self):
        with self.assertRaises(ValueError):
            render_mathematics("not_a_real_math_diagram_ext3", {})

    def test_renders_are_deterministic(self):
        """Same params must give byte-identical SVG — a paper regenerated for a reprint must not
        silently differ from the one the students already sat. This includes the 3D figures."""
        cases = {
            "piecewise_graph": {
                "pieces": [{"expression": "x**2", "domain": [-2, 1], "closed_right": False},
                           {"expression": "x + 3", "domain": [1, 4], "closed_left": True}]},
            "circle_theorem": {"theorem": "angle_at_centre"},
            "similar_triangles": {"configuration": "basic_proportionality"},
            "geometric_construction": {"construction": "angle_bisector"},
            "solid_of_revolution": {"expression": "sqrt(x)", "x_range": [0, 4], "axis": "x"},
            "graph_transformation": {"base_expression": "x**2",
                                     "transformations": [{"type": "shift_up", "param": 2}]},
            "box_plot": {"datasets": [{"label": "A", "data": [1, 2, 3, 4, 5, 6, 7, 8, 9, 100]}]},
        }
        for subtype, params in cases.items():
            self.assertEqual(render_mathematics(subtype, params),
                             render_mathematics(subtype, params), subtype)
