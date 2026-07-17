"""
Unit tests for the four extended Mathematics diagram types:
argand_diagram, linear_programming, histogram, probability_tree.

These diagrams carry the ANSWER to the question they illustrate (the optimal LP vertex,
the leaf probability, the median read off an ogive), so the tests assert on the values the
engine COMPUTES, not merely that an SVG came back. Uses SimpleTestCase — no database.
"""
from django.test import SimpleTestCase

from diagrams.schemas.mathematics import HistogramSchema, ProbabilityTreeSchema
from diagrams.service.mathematics.renderer import (
    _class_boundaries, _class_midpoints, _histogram_median, _histogram_mode,
    _less_than_ogive, _more_than_ogive, _parse_lp_expression, _tree_leaf_paths,
    render_mathematics, solve_linear_program,
)


def _is_valid_svg(content: str) -> bool:
    """Basic SVG validity check."""
    return bool(content and "<svg" in content and "</svg>" in content)


def _svg_text(svg: str) -> str:
    """Visible text nodes of the SVG — matplotlib silently drops text drawn outside the
    axes limits, so 'the value is in the params' does not mean it reached the page."""
    import re
    return " ".join(re.findall(r">([^<>]+)<", svg))


# Standard grouped-frequency table (NCERT-style): N = 30, modal class 40–60.
_CLASS_INTERVALS = [
    {"lower": 0, "upper": 20, "frequency": 4},
    {"lower": 20, "upper": 40, "frequency": 6},
    {"lower": 40, "upper": 60, "frequency": 10},
    {"lower": 60, "upper": 80, "frequency": 6},
    {"lower": 80, "upper": 100, "frequency": 4},
]


class TestArgandDiagram(SimpleTestCase):
    def _render(self, params):
        return render_mathematics("argand_diagram", params)

    def test_single_point_with_modulus_and_argument(self):
        """|3 + 4i| must print as 5. If this fails the engine is drawing a complex number
        whose stated modulus contradicts its own position on the plane."""
        svg = self._render({
            "points": [{"real": 3, "imag": 4, "label": "z",
                        "show_modulus": True, "show_argument": True}],
            "show_modulus_argument": True,
        })
        self.assertTrue(_is_valid_svg(svg))
        text = _svg_text(svg)
        self.assertIn("3 + 4i", text)
        self.assertIn("|z| = 5", text)

    def test_conjugate_has_negative_imaginary_part(self):
        """3 - 4i must not be rendered as 3 + 4i — the conjugate is a different number."""
        text = _svg_text(self._render({
            "points": [{"real": 3, "imag": -4, "label": "z̄", "show_argument": True}]
        }))
        self.assertIn("3 - 4i", text)

    def test_roots_of_unity_are_generated_evenly_spaced(self):
        """The nth roots of unity are computed in the renderer, not supplied. All n labels
        must appear; a missing z_k means a root was dropped off the canvas."""
        svg = self._render({"roots_of_unity": 8, "title": "Eighth roots of unity"})
        self.assertTrue(_is_valid_svg(svg))
        text = _svg_text(svg)
        for k in "₀₁₂₃₄₅₆₇":
            self.assertIn(f"z{k}", text)

    def test_roots_of_unity_arguments_are_pi_fractions(self):
        """The 6th roots sit at arg = kπ/3. Printing them as decimals (1.047) instead of
        π/3 is the kind of thing that makes a paper look machine-generated."""
        text = _svg_text(self._render({"roots_of_unity": 6, "show_modulus_argument": True}))
        self.assertIn("π/3", text)

    def test_axes_are_labelled_re_and_im(self):
        """An Argand plane labelled x/y is not an Argand plane."""
        text = _svg_text(self._render({"points": [{"real": 1, "imag": 1}]}))
        self.assertIn("Re", text)
        self.assertIn("Im", text)

    def test_circle_locus(self):
        svg = self._render({
            "circles": [{"centre_real": 2, "centre_imag": 0, "radius": 3}],
        })
        self.assertTrue(_is_valid_svg(svg))
        self.assertIn("|z - 2| = 3", _svg_text(svg))

    def test_region_disc(self):
        svg = self._render({
            "regions": [{"region_type": "disc", "radius": 2, "label": "|z| ≤ 2"}],
        })
        self.assertTrue(_is_valid_svg(svg))
        self.assertIn("|z| ≤ 2", _svg_text(svg))

    def test_region_annulus(self):
        svg = self._render({"regions": [
            {"region_type": "annulus", "inner_radius": 1, "outer_radius": 3},
        ]})
        self.assertTrue(_is_valid_svg(svg))

    def test_region_argument_wedge(self):
        svg = self._render({
            "regions": [{"region_type": "wedge", "start_angle": 0, "end_angle": 60}],
            "show_unit_circle": True,
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_region_half_plane(self):
        svg = self._render({"regions": [
            {"region_type": "half_plane", "axis": "real", "op": ">=", "value": 1},
        ]})
        self.assertTrue(_is_valid_svg(svg))

    def test_empty_params_rejected(self):
        """A blank Argand plane illustrates nothing and must not silently render."""
        with self.assertRaises(Exception):
            self._render({})

    def test_unknown_region_type_rejected(self):
        with self.assertRaises(Exception):
            self._render({"regions": [{"region_type": "banana", "radius": 1}]})


class TestLinearProgramming(SimpleTestCase):
    def _render(self, params):
        return render_mathematics("linear_programming", params)

    def test_standard_maximum_is_16_at_0_4(self):
        """THE canonical LP: maximise Z = 3x + 4y subject to x + y ≤ 4, x ≥ 0, y ≥ 0.
        The corners are (0,0), (0,4), (4,0) and the optimum is 16 at (0,4). If this fails,
        the diagram is asserting a wrong answer to the question it illustrates."""
        sol = solve_linear_program(
            [{"expression": "x + y <= 4"}], {"a": 3, "b": 4}, maximise=True)
        self.assertEqual(sol["corners"], [(0.0, 0.0), (0.0, 4.0), (4.0, 0.0)])
        self.assertEqual(sol["optimum_point"], (0.0, 4.0))
        self.assertAlmostEqual(sol["optimum_value"], 16.0)
        self.assertTrue(sol["bounded"])
        self.assertFalse(sol["empty"])

    def test_optimum_appears_in_the_rendered_svg(self):
        """The computed optimum must actually reach the page, not fall outside the axes."""
        text = _svg_text(self._render({
            "constraints": [{"expression": "x + y <= 4"}],
            "objective": {"a": 3, "b": 4, "label": "Z"},
        }))
        self.assertIn("Max Z = 16 at (0, 4)", text)
        self.assertIn("(0, 4)", text)
        self.assertIn("(4, 0)", text)

    def test_corner_points_are_computed_not_supplied(self):
        """Corners come from intersecting every pair of boundaries and keeping those that
        satisfy ALL constraints. Two constraints + x,y ≥ 0 give a 4-vertex region."""
        sol = solve_linear_program(
            [{"expression": "3x + 5y <= 15"}, {"expression": "5x + 2y <= 10"}],
            {"a": 5, "b": 3}, maximise=True)
        self.assertEqual(len(sol["corners"]), 4)
        self.assertIn((0.0, 0.0), sol["corners"])
        self.assertIn((0.0, 3.0), sol["corners"])
        self.assertIn((2.0, 0.0), sol["corners"])
        # boundaries cross at (20/19, 45/19); Z there is 235/19 = 12.368…
        opt_x, opt_y = sol["optimum_point"]
        self.assertAlmostEqual(opt_x, 20 / 19, places=6)
        self.assertAlmostEqual(opt_y, 45 / 19, places=6)
        self.assertAlmostEqual(sol["optimum_value"], 235 / 19, places=6)

    def test_infeasible_intersections_are_not_corners(self):
        """A pair of boundaries crossing outside the region is NOT a vertex. x+y≤4 and
        x+y≥1 with x,y ≥ 0: the corner (4,0) is feasible but (0,0) violates x+y≥1."""
        sol = solve_linear_program(
            [{"expression": "x + y <= 4"}, {"expression": "x + y >= 1"}],
            {"a": 1, "b": 1}, maximise=True)
        self.assertNotIn((0.0, 0.0), sol["corners"])
        for px, py in sol["corners"]:
            self.assertGreaterEqual(px + py, 1.0 - 1e-7)
            self.assertLessEqual(px + py, 4.0 + 1e-7)

    def test_minimum_on_an_unbounded_region_still_exists(self):
        """min Z = x + y over x+2y ≥ 10, 3x+4y ≥ 24 is 6 at (0,6): the region is unbounded
        but the MINIMUM is still attained at a corner. Refusing to answer here would be
        just as wrong as inventing an answer."""
        sol = solve_linear_program(
            [{"expression": "x + 2y >= 10"}, {"expression": "3x + 4y >= 24"}],
            {"a": 1, "b": 1}, maximise=False)
        self.assertFalse(sol["bounded"])
        self.assertFalse(sol["unbounded_objective"])
        self.assertEqual(sol["optimum_point"], (0.0, 6.0))
        self.assertAlmostEqual(sol["optimum_value"], 6.0)

    def test_unbounded_objective_has_no_maximum(self):
        """Maximising x + y over x + 2y ≥ 10 runs off to infinity. Naming any corner as
        'the maximum' here would be a fabricated answer."""
        sol = solve_linear_program(
            [{"expression": "x + 2y >= 10"}], {"a": 1, "b": 1}, maximise=True)
        self.assertTrue(sol["unbounded_objective"])
        self.assertIsNone(sol["optimum_point"])
        self.assertIn("UNBOUNDED", _svg_text(self._render({
            "constraints": [{"expression": "x + 2y >= 10"}],
            "objective": {"a": 1, "b": 1},
        })))

    def test_empty_feasible_region_is_labelled_not_crashed(self):
        """x + y ≤ 1 and x + y ≥ 3 cannot both hold. The renderer must say so rather than
        throw, and must not report a corner."""
        sol = solve_linear_program(
            [{"expression": "x + y <= 1"}, {"expression": "x + y >= 3"}], {"a": 1, "b": 1})
        self.assertTrue(sol["empty"])
        self.assertEqual(sol["corners"], [])
        self.assertIsNone(sol["optimum_point"])
        svg = self._render({
            "constraints": [{"expression": "x + y <= 1"}, {"expression": "x + y >= 3"}],
            "objective": {"a": 1, "b": 1},
        })
        self.assertTrue(_is_valid_svg(svg))
        self.assertIn("EMPTY", _svg_text(svg))

    def test_non_negativity_is_implicit(self):
        """x ≥ 0 and y ≥ 0 are assumed. Without them x + y ≤ 4 has no vertices at all."""
        with_nn = solve_linear_program([{"expression": "x + y <= 4"}], {"a": 1, "b": 1})
        without_nn = solve_linear_program(
            [{"expression": "x + y <= 4"}], {"a": 1, "b": 1}, non_negative=False)
        self.assertEqual(len(with_nn["corners"]), 3)
        self.assertEqual(without_nn["corners"], [])

    def test_parse_expression_forms(self):
        """'y >= 2x + 3' must normalise to -2x + y >= 3. Getting the sign wrong here
        silently shades the wrong side of the line."""
        self.assertEqual(_parse_lp_expression("2x + 3y <= 12"), (2.0, 3.0, "<=", 12.0))
        self.assertEqual(_parse_lp_expression("y >= 2x + 3"), (-2.0, 1.0, ">=", 3.0))
        self.assertEqual(_parse_lp_expression("x - y = 1"), (1.0, -1.0, "=", 1.0))

    def test_ab_op_c_constraint_form(self):
        svg = self._render({
            "constraints": [{"a": 2, "b": 3, "op": "<=", "c": 12},
                            {"a": 1, "b": 1, "op": "<=", "c": 5}],
            "objective": {"a": 4, "b": 5},
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_renders_without_objective(self):
        svg = self._render({
            "constraints": [{"expression": "x + 2y <= 8"}, {"expression": "3x + 2y <= 12"}],
            "show_objective_line": False,
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_nonlinear_constraint_rejected(self):
        """x·y ≤ 4 is not a linear constraint and must not be smuggled into an LP."""
        with self.assertRaises(ValueError):
            self._render({"constraints": [{"expression": "x*y <= 4"}]})


class TestHistogram(SimpleTestCase):
    def _render(self, params):
        return render_mathematics("histogram", params)

    def _schema(self, **kw):
        return HistogramSchema(class_intervals=_CLASS_INTERVALS, **kw)

    def test_less_than_ogive_plots_at_upper_boundaries(self):
        """A less-than ogive is plotted at the UPPER class boundary — 'less than 20' is only
        true once the whole 0–20 class is counted. Plotting it at the midpoint or the lower
        boundary is THE classic error and would teach it to students."""
        s = self._schema()
        bounds = _class_boundaries(s.class_intervals, True)
        pts = _less_than_ogive(s.class_intervals, bounds)
        self.assertEqual([p[0] for p in pts], [20.0, 40.0, 60.0, 80.0, 100.0])
        self.assertEqual([p[1] for p in pts], [4.0, 10.0, 20.0, 26.0, 30.0])

    def test_less_than_ogive_ends_at_total_frequency(self):
        """The final cumulative value must be N. If it isn't, a class was dropped."""
        s = self._schema()
        bounds = _class_boundaries(s.class_intervals, True)
        pts = _less_than_ogive(s.class_intervals, bounds)
        total = sum(ci.frequency for ci in s.class_intervals)
        self.assertEqual(total, 30.0)
        self.assertEqual(pts[-1][1], total)

    def test_more_than_ogive_plots_at_lower_boundaries(self):
        """A more-than ogive is plotted at the LOWER boundary and starts from the total.
        Swapping it with the less-than ogive mirrors the curve and inverts every reading."""
        s = self._schema()
        bounds = _class_boundaries(s.class_intervals, True)
        pts = _more_than_ogive(s.class_intervals, bounds)
        self.assertEqual([p[0] for p in pts], [0.0, 20.0, 40.0, 60.0, 80.0])
        self.assertEqual([p[1] for p in pts], [30.0, 26.0, 20.0, 10.0, 4.0])
        self.assertEqual(pts[0][1], 30.0)

    def test_frequency_polygon_uses_class_midpoints(self):
        """The frequency polygon joins MIDPOINTS, not class limits."""
        s = self._schema()
        bounds = _class_boundaries(s.class_intervals, True)
        self.assertEqual(_class_midpoints(bounds), [10.0, 30.0, 50.0, 70.0, 90.0])

    def test_median_from_ogive(self):
        """Median = l + h(N/2 - cf)/f = 40 + 20(15 - 10)/10 = 50. This is the x at which the
        less-than ogive crosses N/2, so the drawn perpendicular and the formula must agree."""
        s = self._schema()
        bounds = _class_boundaries(s.class_intervals, True)
        self.assertAlmostEqual(_histogram_median(s.class_intervals, bounds), 50.0)

    def test_mode_from_construction(self):
        """Mode = l + h(f₁-f₀)/(2f₁-f₀-f₂) = 40 + 20(10-6)/(20-6-6) = 50 — which is exactly
        where the two diagonals drawn inside the modal class cross. Picture and formula must
        not disagree, or the graphical answer contradicts the arithmetic one."""
        s = self._schema()
        bounds = _class_boundaries(s.class_intervals, True)
        self.assertAlmostEqual(_histogram_mode(s.class_intervals, bounds), 50.0)

    def test_continuity_correction_on_inclusive_classes(self):
        """Inclusive classes 10–19, 20–29 have true boundaries 9.5–19.5, 19.5–29.5. Without
        the correction the bars stand apart and every ogive x-value is half a gap early."""
        s = HistogramSchema(class_intervals=[
            {"lower": 10, "upper": 19, "frequency": 3},
            {"lower": 20, "upper": 29, "frequency": 8},
            {"lower": 30, "upper": 39, "frequency": 5},
        ])
        bounds = _class_boundaries(s.class_intervals, True)
        self.assertEqual(bounds, [(9.5, 19.5), (19.5, 29.5), (29.5, 39.5)])
        pts = _less_than_ogive(s.class_intervals, bounds)
        self.assertEqual([p[0] for p in pts], [19.5, 29.5, 39.5])

    def test_raw_data_is_binned_without_losing_observations(self):
        """Every observation must land in exactly one bin — the top bin is closed so the
        maximum value is not silently dropped."""
        s = HistogramSchema(data=[1, 2, 2, 3, 5, 5, 5, 8, 9, 10], bins=5)
        self.assertEqual(sum(ci.frequency for ci in s.class_intervals), 10)

    def test_overlay_none(self):
        svg = self._render({"class_intervals": _CLASS_INTERVALS, "overlay": "none",
                            "show_values": True})
        self.assertTrue(_is_valid_svg(svg))

    def test_overlay_frequency_polygon(self):
        svg = self._render({"class_intervals": _CLASS_INTERVALS,
                            "overlay": "frequency_polygon"})
        self.assertTrue(_is_valid_svg(svg))
        self.assertIn("Frequency polygon", _svg_text(svg))

    def test_overlay_ogive_less_than(self):
        svg = self._render({"class_intervals": _CLASS_INTERVALS,
                            "overlay": "ogive_less_than"})
        self.assertTrue(_is_valid_svg(svg))
        self.assertIn("Less-than ogive", _svg_text(svg))

    def test_overlay_ogive_more_than(self):
        svg = self._render({"class_intervals": _CLASS_INTERVALS,
                            "overlay": "ogive_more_than"})
        self.assertTrue(_is_valid_svg(svg))
        self.assertIn("More-than ogive", _svg_text(svg))

    def test_overlay_both_ogives_with_median(self):
        """Both ogives cross AT the median — that intersection is the whole point of the
        board-exam question, so the drawn median must land there."""
        svg = self._render({"class_intervals": _CLASS_INTERVALS, "overlay": "both_ogives",
                            "show_median_from_ogive": True})
        self.assertTrue(_is_valid_svg(svg))
        text = _svg_text(svg)
        self.assertIn("Less-than ogive", text)
        self.assertIn("More-than ogive", text)
        self.assertIn("Median = 50", text)
        self.assertIn("N/2 = 15", text)

    def test_mode_construction_renders(self):
        svg = self._render({"class_intervals": _CLASS_INTERVALS,
                            "show_mode_construction": True})
        self.assertTrue(_is_valid_svg(svg))
        self.assertIn("Mode = 50", _svg_text(svg))

    def test_unequal_class_widths(self):
        svg = self._render({
            "class_intervals": [{"lower": 0, "upper": 10, "frequency": 5},
                                {"lower": 10, "upper": 30, "frequency": 12},
                                {"lower": 30, "upper": 40, "frequency": 3}],
            "overlay": "frequency_polygon",
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_unknown_overlay_rejected(self):
        with self.assertRaises(Exception):
            self._render({"class_intervals": _CLASS_INTERVALS, "overlay": "wobble"})

    def test_overlapping_classes_rejected(self):
        """Overlapping classes double-count observations and make every cumulative
        frequency wrong."""
        with self.assertRaises(Exception):
            self._render({"class_intervals": [
                {"lower": 0, "upper": 20, "frequency": 4},
                {"lower": 10, "upper": 30, "frequency": 6},
            ]})

    def test_no_data_rejected(self):
        with self.assertRaises(Exception):
            self._render({})


class TestProbabilityTree(SimpleTestCase):
    def _render(self, params):
        return render_mathematics("probability_tree", params)

    def test_leaf_probability_is_the_product_along_the_path(self):
        """P(R then R) = 0.6 × 0.5 = 0.30. A leaf that shows anything other than the product
        of its own edges is a wrong answer printed on an exam paper."""
        schema = ProbabilityTreeSchema(branches=[
            {"label": "R", "probability": 0.6, "children": [
                {"label": "R", "probability": 0.5}, {"label": "B", "probability": 0.5}]},
            {"label": "B", "probability": 0.4, "children": [
                {"label": "R", "probability": 0.75}, {"label": "B", "probability": 0.25}]},
        ])
        leaves = _tree_leaf_paths(schema.branches)
        by_path = {"".join(lf["path"]): lf["probability"] for lf in leaves}
        self.assertAlmostEqual(by_path["RR"], 0.30)
        self.assertAlmostEqual(by_path["RB"], 0.30)
        self.assertAlmostEqual(by_path["BR"], 0.30)
        self.assertAlmostEqual(by_path["BB"], 0.10)

    def test_leaf_probabilities_sum_to_one(self):
        """The leaves partition the sample space. If they don't sum to 1, the tree is lying."""
        schema = ProbabilityTreeSchema(branches=[
            {"label": "A", "probability": 0.3, "children": [
                {"label": "X", "probability": 0.2}, {"label": "Y", "probability": 0.8}]},
            {"label": "B", "probability": 0.7, "children": [
                {"label": "X", "probability": 0.5}, {"label": "Y", "probability": 0.5}]},
        ])
        leaves = _tree_leaf_paths(schema.branches)
        self.assertAlmostEqual(sum(lf["probability"] for lf in leaves), 1.0)

    def test_siblings_summing_to_point_nine_are_rejected(self):
        """Branches out of a node must sum to 1. A tree summing to 0.9 is a broken question
        and must be refused loudly, not drawn."""
        with self.assertRaises(Exception):
            ProbabilityTreeSchema(branches=[
                {"label": "A", "probability": 0.5},
                {"label": "B", "probability": 0.4},
            ])

    def test_nested_siblings_summing_wrong_are_rejected(self):
        """The sum rule applies at EVERY node, not just the root."""
        with self.assertRaises(Exception):
            self._render({"branches": [
                {"label": "A", "probability": 1.0, "children": [
                    {"label": "B", "probability": 0.5},
                    {"label": "C", "probability": 0.2}]},
            ]})

    def test_depth_beyond_four_is_rejected(self):
        """Depth is capped at 4 — deeper trees are unreadable at exam-paper size."""
        deep = {"label": "a", "probability": 1.0}
        node = deep
        for _ in range(4):
            node["children"] = [{"label": "a", "probability": 1.0}]
            node = node["children"][0]
        with self.assertRaises(Exception):
            self._render({"branches": [deep]})

    def test_two_level_tree_renders_with_products(self):
        svg = self._render({
            "branches": [
                {"label": "H", "probability": 0.5, "children": [
                    {"label": "H", "probability": 0.5}, {"label": "T", "probability": 0.5}]},
                {"label": "T", "probability": 0.5, "children": [
                    {"label": "H", "probability": 0.5}, {"label": "T", "probability": 0.5}]},
            ],
            "title": "Two tosses",
        })
        self.assertTrue(_is_valid_svg(svg))
        text = _svg_text(svg)
        self.assertIn("HH", text)
        self.assertIn("P = 0.25", text)

    def test_three_level_tree_renders(self):
        """A 3-stage tree has 8 leaves each of probability 0.125."""
        stage3 = [{"label": "C", "probability": 0.5}, {"label": "D", "probability": 0.5}]
        svg = self._render({"branches": [
            {"label": "A", "probability": 0.5, "children": [
                {"label": "B", "probability": 0.5, "children": stage3},
                {"label": "E", "probability": 0.5, "children": stage3}]},
            {"label": "F", "probability": 0.5, "children": [
                {"label": "B", "probability": 0.5, "children": stage3},
                {"label": "E", "probability": 0.5, "children": stage3}]},
        ]})
        self.assertTrue(_is_valid_svg(svg))
        text = _svg_text(svg)
        self.assertIn("P = 0.125", text)
        self.assertIn("ABC", text)

    def test_fractional_probabilities_print_as_fractions(self):
        """1/3 × 1/3 = 1/9, not 0.1111. Exam papers print fractions."""
        third = 1 / 3
        svg = self._render({"branches": [
            {"label": "X", "probability": third, "children": [
                {"label": "Y", "probability": third},
                {"label": "N", "probability": 1 - third}]},
            {"label": "Z", "probability": 1 - third, "children": [
                {"label": "Y", "probability": third},
                {"label": "N", "probability": 1 - third}]},
        ]})
        text = _svg_text(svg)
        self.assertIn("1/3", text)
        self.assertIn("1/9", text)

    def test_highlight_paths(self):
        svg = self._render({
            "branches": [
                {"label": "R", "probability": 0.6, "children": [
                    {"label": "R", "probability": 0.5}, {"label": "B", "probability": 0.5}]},
                {"label": "B", "probability": 0.4, "children": [
                    {"label": "R", "probability": 0.75}, {"label": "B", "probability": 0.25}]},
            ],
            "highlight_paths": [["R", "R"]],
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_single_level_tree(self):
        svg = self._render({"branches": [
            {"label": "1", "probability": 0.2},
            {"label": "2", "probability": 0.3},
            {"label": "3", "probability": 0.5},
        ]})
        self.assertTrue(_is_valid_svg(svg))


class TestMathematicsExtDispatcher(SimpleTestCase):
    def test_all_four_subtypes_are_registered(self):
        from diagrams.service.mathematics.renderer import MATHEMATICS_RENDERERS
        for subtype in ("argand_diagram", "linear_programming", "histogram", "probability_tree"):
            self.assertIn(subtype, MATHEMATICS_RENDERERS)

    def test_unknown_subtype_raises(self):
        with self.assertRaises(ValueError):
            render_mathematics("not_a_real_math_diagram", {})

    def test_renders_are_deterministic(self):
        """Same params must give byte-identical SVG — a paper regenerated for a reprint
        must not silently differ from the one students already sat."""
        params = {"class_intervals": _CLASS_INTERVALS, "overlay": "both_ogives"}
        self.assertEqual(render_mathematics("histogram", params),
                         render_mathematics("histogram", params))
