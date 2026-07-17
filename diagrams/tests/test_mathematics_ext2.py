"""
Unit tests for the four further Mathematics diagram types:
height_distance, combined_solid, plane_line_3d, distribution_curve.

Every one of these figures carries the ANSWER to the question it illustrates — the height of the
tower, the surface area of the toy, the distance to the plane, the shaded probability — so the
tests assert on the values the engine COMPUTES from the geometry, not merely that an SVG came
back. A figure that renders beautifully and states 20 m where the trigonometry says 17.32 m is
worse than no figure at all. Uses SimpleTestCase — no database.
"""
import math

from django.test import SimpleTestCase

from diagrams.schemas.mathematics import (
    CombinedSolidSchema, DistributionCurveSchema, HDObject, Line3D, Plane3D,
)
from diagrams.service.mathematics.renderer import (
    MATHEMATICS_RENDERERS, angle_between_lines, angle_between_planes, angle_line_plane,
    combined_solid_metrics, distribution_area, line_plane_intersection,
    plane_plane_intersection, point_plane_distance, render_mathematics, solve_height_distance,
    _norm_cdf, _pi_multiple_text, _t_cdf,
)

PI = math.pi


def _is_valid_svg(content: str) -> bool:
    return bool(content and "<svg" in content and "</svg>" in content)


def _svg_text(svg: str) -> str:
    """Visible text nodes of the SVG — matplotlib silently drops text drawn outside the axes
    limits, so 'the value was computed' does not mean it reached the page."""
    import re
    return " ".join(re.findall(r">([^<>]+)<", svg))


# ── Height & Distance ─────────────────────────────────────────────────────────

class TestHeightDistance(SimpleTestCase):
    def _render(self, params):
        return render_mathematics("height_distance", params)

    def test_tower_at_30_degrees_from_30m_is_17_32m(self):
        """THE Class-10 trigonometry figure: tan 30° = h / 30, so h = 30·tan 30° = 17.32 m.
        If this fails the drawn triangle does not satisfy the tan θ the question is about, and
        every student who measures the figure gets a different answer from the one marked."""
        s = solve_height_distance(0.0, HDObject(distance=30, angle_of_elevation=30))
        self.assertAlmostEqual(s["height"], 30 * math.tan(math.radians(30)), places=9)
        self.assertAlmostEqual(s["height"], 17.3205, places=4)
        self.assertAlmostEqual(s["distance"], 30.0, places=9)

    def test_height_is_derived_not_taken_from_the_params(self):
        """A supplied height that contradicts the angle and the distance is a broken question.
        Silently drawing it would put a triangle on the page where tan 30° ≠ opposite/adjacent."""
        with self.assertRaises(ValueError):
            solve_height_distance(
                0.0, HDObject(height=25, distance=30, angle_of_elevation=30))

    def test_a_rounded_supplied_height_is_accepted_and_snapped(self):
        """17.32 is the rounded truth, not a contradiction: it must not be rejected, and the
        exact value must still be what gets drawn."""
        s = solve_height_distance(0.0, HDObject(height=17.32, distance=30,
                                                angle_of_elevation=30))
        self.assertAlmostEqual(s["height"], 30 * math.tan(math.radians(30)), places=9)

    def test_angle_is_derived_from_height_and_distance(self):
        """Given the two legs, the angle is arctan(60/60) = 45°. An angle taken from the params
        here could disagree with the triangle it is drawn on."""
        s = solve_height_distance(0.0, HDObject(height=60, distance=60))
        self.assertAlmostEqual(s["elevation"], 45.0, places=9)
        self.assertIsNone(s["depression"])

    def test_distance_is_derived_from_height_and_angle(self):
        """h = 17.3205 at 30° must put the observer 30 m away, not anywhere else."""
        s = solve_height_distance(0.0, HDObject(height=30 * math.tan(math.radians(30)),
                                                angle_of_elevation=30))
        self.assertAlmostEqual(s["distance"], 30.0, places=6)

    def test_depression_to_a_point_on_the_ground(self):
        """From a 75 m lighthouse the ship at 30° depression is 75/tan 30° = 129.9 m out. The
        ship sits ON the ground: giving it a height would move the whole triangle."""
        s = solve_height_distance(75.0, HDObject(angle_of_depression=30))
        self.assertAlmostEqual(s["distance"], 75 / math.tan(math.radians(30)), places=9)
        self.assertAlmostEqual(s["height"], 0.0, places=9)

    def test_depression_to_the_top_of_a_shorter_building(self):
        """From 60 m, looking down 30° at something 40 m away, the target's top is at
        60 − 40·tan 30° = 36.9 m. The OPPOSITE side is the drop from the eye, not the height."""
        s = solve_height_distance(60.0, HDObject(distance=40, angle_of_depression=30))
        self.assertAlmostEqual(s["height"], 60 - 40 * math.tan(math.radians(30)), places=9)

    def test_both_angles_from_an_elevated_observer(self):
        """The canonical two-angle problem: from a 20 m building, the foot of a tower is at 30°
        depression and its top at 60° elevation. The DEPRESSION fixes the distance
        (20/tan 30° = 34.64) and the elevation then fixes the height (20 + 34.64·tan 60° = 80).
        Solving these in the wrong order gives a tower of the wrong height."""
        s = solve_height_distance(20.0, HDObject(angle_of_elevation=60, angle_of_depression=30))
        self.assertAlmostEqual(s["distance"], 20 / math.tan(math.radians(30)), places=9)
        self.assertAlmostEqual(s["height"], 80.0, places=6)

    def test_tower_and_building_scenario(self):
        """From the top of a 15 m building, a tower 20 m away at 45° elevation rises to
        15 + 20 = 35 m — the elevation is measured from the EYE, so the observer's own height
        is part of the answer. Forgetting it under-reports the tower by 15 m."""
        s = solve_height_distance(15.0, HDObject(distance=20, angle_of_elevation=45))
        self.assertAlmostEqual(s["height"], 35.0, places=9)

    def test_looking_up_at_something_below_the_eye_is_rejected(self):
        """An angle of elevation to a target beneath you is not a figure, it is a contradiction."""
        with self.assertRaises(ValueError):
            solve_height_distance(50.0, HDObject(height=10, angle_of_elevation=30))

    def test_a_single_measurement_cannot_fix_a_triangle(self):
        with self.assertRaises(Exception):
            self._render({"objects": [{"label": "Tower", "angle_of_elevation": 30}]})

    def test_depression_needs_an_elevated_observer(self):
        with self.assertRaises(Exception):
            self._render({"scenario": "depression", "observer": {"height": 0},
                          "objects": [{"angle_of_depression": 30}]})

    def test_unknown_scenario_rejected(self):
        with self.assertRaises(Exception):
            self._render({"scenario": "sideways",
                          "objects": [{"distance": 10, "angle_of_elevation": 30}]})

    def test_computed_values_reach_the_page(self):
        """The derived height, the distance and the angle must all be drawn INSIDE the axes.
        Matplotlib drops text outside them without raising, so a correct computation can still
        end up on a figure that shows nothing."""
        text = _svg_text(self._render({
            "objects": [{"label": "Tower", "distance": 30, "angle_of_elevation": 30}],
            "ground_label": "Ground", "unit": "m",
        }))
        self.assertIn("17.32 m", text)
        self.assertIn("30 m", text)
        self.assertIn("30°", text)
        self.assertIn("Tower", text)
        self.assertIn("Ground", text)

    def test_scenario_elevation_renders(self):
        self.assertTrue(_is_valid_svg(self._render({
            "scenario": "elevation",
            "objects": [{"label": "Tower", "distance": 30, "angle_of_elevation": 30}],
        })))

    def test_scenario_depression_renders(self):
        self.assertTrue(_is_valid_svg(self._render({
            "scenario": "depression", "observer": {"label": "Lighthouse", "height": 75},
            "objects": [{"label": "Ship", "angle_of_depression": 30}],
        })))

    def test_scenario_both_renders(self):
        self.assertTrue(_is_valid_svg(self._render({
            "scenario": "both", "observer": {"label": "Building", "height": 20},
            "objects": [{"label": "Tower", "angle_of_elevation": 60,
                         "angle_of_depression": 30}],
        })))

    def test_scenario_tower_and_building_renders(self):
        self.assertTrue(_is_valid_svg(self._render({
            "scenario": "tower_and_building", "observer": {"label": "Building", "height": 15},
            "objects": [{"label": "Tower", "distance": 20, "angle_of_elevation": 45}],
        })))

    def test_two_objects_render(self):
        self.assertTrue(_is_valid_svg(self._render({
            "objects": [{"label": "Pole", "height": 10, "angle_of_elevation": 45},
                        {"label": "Tower", "distance": 30, "angle_of_elevation": 60}],
        })))


# ── Combined Solid ────────────────────────────────────────────────────────────

def _metrics(components, arrangement="stacked_vertical"):
    schema = CombinedSolidSchema(components=components, arrangement=arrangement)
    return combined_solid_metrics(schema.components, schema.arrangement)


class TestCombinedSolid(SimpleTestCase):
    def _render(self, params):
        return render_mathematics("combined_solid", params)

    def test_cone_on_hemisphere_surface_area_is_33_pi(self):
        """A cone (r=3, h=4) on a hemisphere (r=3): TSA = πrl + 2πr² = 15π + 18π = 33π ≈ 103.67.
        The joining circle is INTERNAL and belongs to neither surface. This is the single
        subtlety the question exists to test, and the answer it must not get wrong."""
        m = _metrics([{"solid_type": "hemisphere", "radius": 3},
                      {"solid_type": "cone", "radius": 3, "height": 4}])
        self.assertAlmostEqual(m["surface_area"], 33 * PI, places=9)
        self.assertAlmostEqual(m["surface_area"], 103.6726, places=3)

    def test_the_joining_circle_is_excluded_not_counted_twice(self):
        """Summing the two solids' own total surface areas gives 33π + 18π = 51π: it counts the
        joining circle once from the cone's base and once from the hemisphere's flat face. Both
        are buried inside the toy. If a diagram ever prints 160.22 for this, it is lying."""
        m = _metrics([{"solid_type": "hemisphere", "radius": 3},
                      {"solid_type": "cone", "radius": 3, "height": 4}])
        sum_of_parts = (PI * 3 * 5 + PI * 9) + (2 * PI * 9 + PI * 9)   # 51π
        self.assertAlmostEqual(sum_of_parts - m["surface_area"], 2 * PI * 9, places=9)
        self.assertNotAlmostEqual(m["surface_area"], sum_of_parts, places=3)

    def test_slant_height_is_recomputed_not_trusted(self):
        """l = √(3² + 4²) = 5. A slant height carried in the params is the value the model gets
        wrong, and πrl with the wrong l is a wrong surface area that still looks plausible."""
        m = _metrics([{"solid_type": "hemisphere", "radius": 3},
                      {"solid_type": "cone", "radius": 3, "height": 4, "slant_height": 99}])
        self.assertAlmostEqual(m["per_component"][1]["slant"], 5.0, places=9)
        self.assertAlmostEqual(m["surface_area"], 33 * PI, places=9)

    def test_cone_on_hemisphere_volume_is_30_pi(self):
        """V = ⅔πr³ + ⅓πr²h = 18π + 12π = 30π. Volumes DO add — unlike surfaces — because
        nothing is buried when you fill the solid."""
        m = _metrics([{"solid_type": "hemisphere", "radius": 3},
                      {"solid_type": "cone", "radius": 3, "height": 4}])
        self.assertAlmostEqual(m["volume"], 30 * PI, places=9)

    def test_cone_on_cylinder_tent(self):
        """A tent (cylinder r=7 h=10, cone r=7 h=24, so l=25): TSA = 2πrh + πrl + πr² (the base)
        = 140π + 175π + 49π = 364π. The circle where the cone meets the cylinder is gone."""
        m = _metrics([{"solid_type": "cylinder", "radius": 7, "height": 10},
                      {"solid_type": "cone", "radius": 7, "height": 24}])
        self.assertAlmostEqual(m["surface_area"], 364 * PI, places=6)
        self.assertAlmostEqual(m["volume"], (PI * 49 * 10) + (PI * 49 * 24 / 3), places=6)

    def test_hemisphere_on_a_cube_keeps_the_annulus(self):
        """A dome (r=3.5) on a cube (a=7): the dome hides only πr² of the cube's top face, so
        TSA = 6a² − πr² + 2πr². The two joining faces have DIFFERENT areas here, and the part of
        the larger one left proud of the smaller stays on the outside."""
        m = _metrics([{"solid_type": "cube", "side": 7},
                      {"solid_type": "hemisphere", "radius": 3.5}])
        self.assertAlmostEqual(m["surface_area"],
                               6 * 49 - PI * 3.5 ** 2 + 2 * PI * 3.5 ** 2, places=9)

    def test_capsule_has_two_hemispherical_ends(self):
        """Cylinder capped both ends: TSA = 2πrh + 4πr². Both joining circles vanish; if either
        survived the answer would be out by πr²."""
        m = _metrics([{"solid_type": "hemisphere", "radius": 3.5},
                      {"solid_type": "cylinder", "radius": 3.5, "height": 10},
                      {"solid_type": "hemisphere", "radius": 3.5}])
        self.assertAlmostEqual(m["surface_area"],
                               2 * PI * 3.5 * 10 + 4 * PI * 3.5 ** 2, places=9)

    def test_a_sphere_resting_on_a_cylinder_hides_nothing(self):
        """A sphere touches a flat face at ONE POINT: it hides no area at all, so the cylinder's
        top circle stays fully exposed. Treating the contact as a glued face would wrongly
        subtract πr² twice."""
        m = _metrics([{"solid_type": "cylinder", "radius": 3, "height": 8},
                      {"solid_type": "sphere", "radius": 3}])
        expected = (2 * PI * 3 * 8) + (PI * 9) + (PI * 9) + (4 * PI * 9)
        self.assertAlmostEqual(m["surface_area"], expected, places=9)

    def test_side_by_side_solids_keep_their_whole_surfaces(self):
        """Nothing is joined, so nothing is hidden: the total IS the sum of the two totals.
        Applying the stacked rule here would delete a face that is plainly visible."""
        m = _metrics([{"solid_type": "cylinder", "radius": 3, "height": 8},
                      {"solid_type": "sphere", "radius": 3}], "side_by_side")
        self.assertAlmostEqual(
            m["surface_area"], (2 * PI * 3 * 8 + 2 * PI * 9) + 4 * PI * 9, places=9)
        self.assertAlmostEqual(m["volume"], PI * 9 * 8 + 4 * PI * 27 / 3, places=9)

    def test_conical_cavity_carved_out_of_a_cylinder(self):
        """The NCERT hollow: TSA = 2πrh (wall) + πr² (base) + πrl (the cavity's inner wall).
        The cylinder's top face is entirely eaten by the cavity's mouth — a hole is not a
        surface — and the cone's base is not one either."""
        r, h = 3.5, 10.0
        l = math.hypot(r, h)
        m = _metrics([{"solid_type": "cylinder", "radius": r, "height": h},
                      {"solid_type": "cone", "radius": r, "height": h}], "hollowed_out")
        self.assertAlmostEqual(
            m["surface_area"], 2 * PI * r * h + PI * r ** 2 + PI * r * l, places=9)

    def test_hollowed_volume_is_the_difference(self):
        """Carving a cone out of a cylinder of the same r and h leaves ⅔πr²h — two thirds, not
        the whole and not a third."""
        m = _metrics([{"solid_type": "cylinder", "radius": 3.5, "height": 10},
                      {"solid_type": "cone", "radius": 3.5, "height": 10}], "hollowed_out")
        self.assertAlmostEqual(m["volume"], 2 / 3 * PI * 3.5 ** 2 * 10, places=9)

    def test_hemispherical_depression_in_a_cube(self):
        """Scooping a dome out of a block and sticking one on top come to the SAME surface area,
        6a² − πr² + 2πr² — a fact worth not breaking."""
        scooped = _metrics([{"solid_type": "cube", "side": 7},
                            {"solid_type": "hemisphere", "radius": 3.5}], "hollowed_out")
        surmounted = _metrics([{"solid_type": "cube", "side": 7},
                               {"solid_type": "hemisphere", "radius": 3.5}])
        self.assertAlmostEqual(scooped["surface_area"], surmounted["surface_area"], places=9)
        self.assertAlmostEqual(scooped["volume"], 343 - 2 / 3 * PI * 3.5 ** 3, places=9)

    def test_inscribed_sphere_leaves_the_corners(self):
        """The largest sphere in a cube of side 10 has r = 5; the wood left over is
        1000 − (4/3)π·125 = 476.40 cm³. The visible surface is still the cube's 600 cm²."""
        m = _metrics([{"solid_type": "cube", "side": 10},
                      {"solid_type": "sphere", "radius": 5}], "inscribed")
        self.assertAlmostEqual(m["remaining_volume"], 1000 - 4 / 3 * PI * 125, places=9)
        self.assertAlmostEqual(m["surface_area"], 600.0, places=9)

    def test_frustum_slant_uses_the_radius_difference(self):
        """A frustum's slant is √(h² + (R−r)²) = √(81 + 16) = √97, NOT √(h² + R²). Using the
        cone formula here inflates the curved surface area of every bucket question."""
        m = _metrics([{"solid_type": "frustum", "radius_bottom": 8, "radius_top": 4,
                       "height": 9},
                      {"solid_type": "cylinder", "radius": 4, "height": 5}])
        self.assertAlmostEqual(m["per_component"][0]["slant"], math.sqrt(97), places=9)
        self.assertAlmostEqual(
            m["per_component"][0]["volume"],
            PI * 9 * (64 + 16 + 32) / 3, places=9)

    def test_mismatched_joining_radius_is_rejected(self):
        """A cone of radius 3 cannot sit flush on a cylinder of radius 5 — it would float on a
        rim it does not reach. A figure like that is broken and its surface area is fiction."""
        with self.assertRaises(Exception):
            CombinedSolidSchema(components=[
                {"solid_type": "cylinder", "radius": 5, "height": 8},
                {"solid_type": "cone", "radius": 3, "height": 4}])

    def test_an_overhanging_dome_is_rejected(self):
        """A hemisphere of radius 6 does not fit on a 7 × 7 face."""
        with self.assertRaises(Exception):
            CombinedSolidSchema(components=[
                {"solid_type": "cube", "side": 7},
                {"solid_type": "hemisphere", "radius": 6}])

    def test_a_cavity_bigger_than_its_block_is_rejected(self):
        with self.assertRaises(ValueError):
            _metrics([{"solid_type": "cylinder", "radius": 3, "height": 4},
                      {"solid_type": "cylinder", "radius": 3, "height": 4}], "hollowed_out")

    def test_single_component_is_rejected(self):
        """One solid is a solid_3d, not a combined_solid."""
        with self.assertRaises(Exception):
            CombinedSolidSchema(components=[{"solid_type": "cone", "radius": 3, "height": 4}])

    def test_unknown_arrangement_rejected(self):
        with self.assertRaises(Exception):
            self._render({"components": [{"solid_type": "cone", "radius": 3, "height": 4},
                                         {"solid_type": "hemisphere", "radius": 3}],
                          "arrangement": "welded"})

    def test_pi_form_is_only_used_when_the_value_really_is_a_pi_multiple(self):
        """33π must print as 33π. A cube's volume of 1000 must NOT print as '167431π/526' — an
        unbounded rational search will 'find' a π-multiple in any number at all."""
        self.assertEqual(_pi_multiple_text(33 * PI), "33π")
        self.assertEqual(_pi_multiple_text(245 * PI / 3), "245π/3")
        self.assertIsNone(_pi_multiple_text(1000.0))
        self.assertIsNone(_pi_multiple_text(600.0))

    def test_computed_area_and_volume_reach_the_page(self):
        text = _svg_text(self._render({
            "components": [{"solid_type": "hemisphere", "radius": 3, "label": "hemisphere"},
                           {"solid_type": "cone", "radius": 3, "height": 4, "label": "cone"}],
            "show_total_surface_area": True, "show_volume": True, "unit": "cm",
        }))
        self.assertIn("33π", text)
        self.assertIn("103.67", text)
        self.assertIn("30π", text)
        self.assertIn("l = 5 cm", text)      # the slant height the engine derived
        self.assertIn("r = 3 cm", text)

    def test_every_arrangement_renders(self):
        for params in (
            {"components": [{"solid_type": "hemisphere", "radius": 3},
                            {"solid_type": "cone", "radius": 3, "height": 4}],
             "arrangement": "stacked_vertical"},
            {"components": [{"solid_type": "cylinder", "radius": 3, "height": 8},
                            {"solid_type": "sphere", "radius": 3}],
             "arrangement": "side_by_side"},
            {"components": [{"solid_type": "cube", "side": 10},
                            {"solid_type": "sphere", "radius": 5}],
             "arrangement": "inscribed"},
            {"components": [{"solid_type": "cylinder", "radius": 3.5, "height": 10},
                            {"solid_type": "cone", "radius": 3.5, "height": 10}],
             "arrangement": "hollowed_out"},
        ):
            self.assertTrue(_is_valid_svg(self._render(dict(
                params, show_total_surface_area=True, show_volume=True))))

    def test_every_solid_type_renders(self):
        for comp in ({"solid_type": "cylinder", "radius": 3, "height": 6},
                     {"solid_type": "cone", "radius": 3, "height": 4},
                     {"solid_type": "hemisphere", "radius": 3},
                     {"solid_type": "sphere", "radius": 3},
                     {"solid_type": "cube", "side": 6},
                     {"solid_type": "cuboid", "length": 6, "width": 4, "height": 5},
                     {"solid_type": "frustum", "radius_bottom": 6, "radius_top": 3,
                      "height": 4}):
            svg = self._render({
                "components": [comp, {"solid_type": "sphere", "radius": 2}],
                "arrangement": "side_by_side", "show_volume": True,
            })
            self.assertTrue(_is_valid_svg(svg), comp["solid_type"])


# ── Plane & Line in 3D ────────────────────────────────────────────────────────

class TestPlaneLine3D(SimpleTestCase):
    def _render(self, params):
        return render_mathematics("plane_line_3d", params)

    def test_distance_from_point_to_plane(self):
        """|1 + 4 + 6 − 6| / √(1 + 4 + 4) = 5/3. Forgetting to divide by |n| — or forgetting the
        −d — is the classic slip, and both produce a plausible-looking wrong number."""
        d = point_plane_distance((1, 2, 3), Plane3D(a=1, b=2, c=2, d=6))
        self.assertAlmostEqual(d, 5 / 3, places=12)

    def test_distance_is_zero_for_a_point_on_the_plane(self):
        self.assertAlmostEqual(
            point_plane_distance((6, 0, 0), Plane3D(a=1, b=2, c=2, d=6)), 0.0, places=12)

    def test_angle_between_two_planes(self):
        """cos θ = |n₁·n₂| / (|n₁||n₂|) = 1/2, so θ = 60°. The ACUTE angle: dropping the modulus
        would report 120° for the same pair of planes."""
        self.assertAlmostEqual(
            angle_between_planes(Plane3D(a=1, b=1, c=0, d=2), Plane3D(a=0, b=1, c=1, d=3)),
            60.0, places=9)

    def test_parallel_planes_are_at_zero_degrees_and_never_meet(self):
        """x+y+z=3 and 2x+2y+2z=10 have parallel normals: there is no line of intersection to
        draw, and inventing one would be inventing a solution to an inconsistent system."""
        p1, p2 = Plane3D(a=1, b=1, c=1, d=3), Plane3D(a=2, b=2, c=2, d=10)
        self.assertAlmostEqual(angle_between_planes(p1, p2), 0.0, places=9)
        self.assertIsNone(plane_plane_intersection(p1, p2))

    def test_plane_plane_intersection_lies_in_both_planes(self):
        """The computed line must satisfy BOTH plane equations — its point on each plane, and
        its direction perpendicular to each normal. If it doesn't, the line drawn is not the
        intersection of anything."""
        p1, p2 = Plane3D(a=1, b=1, c=0, d=2), Plane3D(a=0, b=1, c=1, d=3)
        point, direction = plane_plane_intersection(p1, p2)
        self.assertAlmostEqual(point[0] + point[1], 2.0, places=9)
        self.assertAlmostEqual(point[1] + point[2], 3.0, places=9)
        self.assertAlmostEqual(direction[0] + direction[1], 0.0, places=9)
        self.assertAlmostEqual(direction[1] + direction[2], 0.0, places=9)
        self.assertAlmostEqual(float(sum(c ** 2 for c in direction)), 1.0, places=9)

    def test_line_pierces_plane_at_a_point_on_both(self):
        """r = (1,0,0) + λ(1,2,3) meets x+y+z=5 at λ = 2/3, i.e. (5/3, 4/3, 2). The point must
        lie on the line AND satisfy the plane equation."""
        hit = line_plane_intersection(
            Line3D(point=(1, 0, 0), direction=(1, 2, 3)), Plane3D(a=1, b=1, c=1, d=5))
        self.assertAlmostEqual(float(hit[0] + hit[1] + hit[2]), 5.0, places=9)
        self.assertAlmostEqual(float(hit[0]), 1 + 2 / 3, places=9)
        self.assertAlmostEqual(float(hit[1]), 4 / 3, places=9)
        self.assertAlmostEqual(float(hit[2]), 2.0, places=9)

    def test_a_line_parallel_to_a_plane_never_pierces_it(self):
        """n·b = 0 means the line runs along the plane: there is no intersection point, and
        marking one would be marking a point that does not exist."""
        self.assertIsNone(line_plane_intersection(
            Line3D(point=(0, 0, 0), direction=(1, -1, 0)), Plane3D(a=1, b=1, c=0, d=5)))

    def test_angle_between_line_and_plane_is_an_arcsin(self):
        """A line along the z-axis meets the plane z = 1 at 90°, not 0°: the angle with the
        PLANE is the complement of the angle with the normal. Using arccos here reports every
        line-plane angle as its complement."""
        self.assertAlmostEqual(
            angle_line_plane(Line3D(point=(0, 0, 0), direction=(0, 0, 1)),
                             Plane3D(a=0, b=0, c=1, d=1)), 90.0, places=9)
        self.assertAlmostEqual(
            angle_line_plane(Line3D(point=(0, 0, 0), direction=(1, 0, 0)),
                             Plane3D(a=0, b=0, c=1, d=1)), 0.0, places=9)

    def test_angle_between_lines(self):
        self.assertAlmostEqual(
            angle_between_lines(Line3D(point=(0, 0, 0), direction=(1, 0, 0)),
                                Line3D(point=(0, 0, 0), direction=(0, 1, 1))),
            90.0, places=9)

    def test_a_zero_normal_is_rejected(self):
        with self.assertRaises(Exception):
            Plane3D(a=0, b=0, c=0, d=5)

    def test_a_zero_direction_is_rejected(self):
        with self.assertRaises(Exception):
            Line3D(point=(1, 1, 1), direction=(0, 0, 0))

    def test_empty_diagram_rejected(self):
        with self.assertRaises(Exception):
            self._render({})

    def test_computed_distance_reaches_the_page(self):
        text = _svg_text(self._render({
            "planes": [{"a": 1, "b": 2, "c": 2, "d": 6}],
            "points": [{"x": 1, "y": 2, "z": 3, "label": "P"}],
            "show_distance": True, "show_normals": True,
        }))
        self.assertIn("1.667", text)          # 5/3
        self.assertIn("x + 2y + 2z = 6", text)

    def test_computed_angle_and_intersection_reach_the_page(self):
        text = _svg_text(self._render({
            "planes": [{"a": 1, "b": 1, "c": 0, "d": 2}, {"a": 0, "b": 1, "c": 1, "d": 3}],
            "show_intersection": True, "show_angle": True, "show_normals": True,
        }))
        self.assertIn("60.00°", text)
        self.assertIn("x + y = 2", text)
        self.assertIn("y + z = 3", text)

    def test_line_and_points_only_renders(self):
        self.assertTrue(_is_valid_svg(self._render({
            "lines": [{"point": [0, 0, 0], "direction": [1, 0, 0], "label": "L1"},
                      {"point": [0, 0, 0], "direction": [0, 1, 1], "label": "L2"}],
            "points": [{"x": 1, "y": 1, "z": 1, "label": "A"}],
            "show_angle": True,
        })))

    def test_line_and_plane_renders(self):
        self.assertTrue(_is_valid_svg(self._render({
            "planes": [{"a": 1, "b": 1, "c": 1, "d": 5}],
            "lines": [{"point": [1, 0, 0], "direction": [1, 2, 3], "label": "L"}],
            "show_intersection": True, "show_angle": True,
        })))


# ── Distribution Curve ────────────────────────────────────────────────────────

def _dist(**kw):
    return DistributionCurveSchema(**kw)


class TestDistributionCurve(SimpleTestCase):
    def _render(self, params):
        return render_mathematics("distribution_curve", params)

    def test_one_sigma_area_is_0_6827(self):
        """The empirical rule: 68.27 % of a normal distribution lies within ±1σ. scipy is not
        available, so this comes from math.erf — if the CDF is wrong, every probability this
        diagram prints is wrong."""
        self.assertAlmostEqual(
            distribution_area(_dist(distribution="standard_normal"), -1, 1), 0.6827, delta=0.001)

    def test_two_and_three_sigma_areas(self):
        """95.45 % and 99.73 %. A figure that annotates the bands with 95 % / 99.7 % but shades
        a different area is teaching the rule wrong."""
        z = _dist(distribution="standard_normal")
        self.assertAlmostEqual(distribution_area(z, -2, 2), 0.9545, delta=0.001)
        self.assertAlmostEqual(distribution_area(z, -3, 3), 0.9973, delta=0.001)

    def test_the_normal_is_symmetric_about_its_mean(self):
        self.assertAlmostEqual(
            distribution_area(_dist(distribution="standard_normal"), None, 0), 0.5, places=12)

    def test_a_scaled_normal_matches_the_standard_one(self):
        """P(X ≥ 130) for N(100, 15²) IS P(Z ≥ 2) = 0.0228. If standardising is broken, only
        the mean-zero case would ever be right."""
        self.assertAlmostEqual(
            distribution_area(_dist(distribution="normal",
                                    parameters={"mean": 100, "std_dev": 15}), 130, None),
            1 - _norm_cdf(2), places=12)

    def test_standard_normal_ignores_a_supplied_mean(self):
        """Z is N(0, 1) by definition. A params blob claiming standard_normal with mean 50 is
        wrong about what the word means, and must not shift the curve."""
        s = _dist(distribution="standard_normal", parameters={"mean": 50, "std_dev": 7})
        self.assertEqual(s.parameters.mean, 0.0)
        self.assertEqual(s.parameters.std_dev, 1.0)

    def test_binomial_probabilities_are_exact(self):
        """B(10, ½): P(X ≥ 7) = (120 + 45 + 10 + 1)/1024 = 176/1024. Discrete regions are SUMMED
        over the integers they contain — integrating a bar chart would give a different answer."""
        b = _dist(distribution="binomial", parameters={"n": 10, "p": 0.5})
        self.assertAlmostEqual(distribution_area(b, 7, None), 176 / 1024, places=12)
        self.assertAlmostEqual(distribution_area(b, 5, 5), 252 / 1024, places=12)
        self.assertAlmostEqual(distribution_area(b, None, None), 1.0, places=12)

    def test_poisson_probabilities_are_exact(self):
        """Poisson(4): P(X ≤ 2) = e⁻⁴(1 + 4 + 8) = 13e⁻⁴ = 0.2381."""
        p = _dist(distribution="poisson", parameters={"lambda": 4})
        self.assertAlmostEqual(distribution_area(p, None, 2), 13 * math.exp(-4), places=12)
        self.assertAlmostEqual(distribution_area(p, None, None), 1.0, places=9)

    def test_poisson_open_tail_sums_far_enough(self):
        """P(X ≥ 1) = 1 − e⁻⁴. Truncating the sum too early quietly loses probability from the
        tail and the two ends stop adding to 1."""
        p = _dist(distribution="poisson", parameters={"lambda": 4})
        self.assertAlmostEqual(distribution_area(p, 1, None), 1 - math.exp(-4), places=9)

    def test_t_distribution_critical_value(self):
        """t(5) has its 5 % upper critical value at 2.015 — the number in every statistics
        table. The CDF is integrated in code (no scipy), so this is the check that it is right."""
        t5 = _dist(distribution="t", parameters={"df": 5})
        self.assertAlmostEqual(distribution_area(t5, 2.015, None), 0.05, delta=0.0005)
        self.assertAlmostEqual(distribution_area(t5, None, None), 1.0, places=9)

    def test_t_with_one_degree_of_freedom_is_cauchy(self):
        """t(1) is the Cauchy distribution, whose CDF is ½ + arctan(x)/π, so P(T ≤ 1) = 0.75.
        Its tails decay like 1/x²: integrating on a truncated x-range silently loses over 1 %
        of the probability, which is why the integral is done in θ."""
        self.assertAlmostEqual(
            distribution_area(_dist(distribution="t", parameters={"df": 1}), None, 1),
            0.75, delta=1e-6)

    def test_t_approaches_the_normal_for_large_df(self):
        """t(200) and Z must agree to 3 decimals; a t that does not converge to the normal is
        not a t."""
        t200 = distribution_area(_dist(distribution="t", parameters={"df": 200}), -1, 1)
        z = distribution_area(_dist(distribution="standard_normal"), -1, 1)
        self.assertAlmostEqual(t200, z, delta=0.005)

    def test_t_cdf_is_symmetric(self):
        self.assertAlmostEqual(_t_cdf(-1.5, 7), 1 - _t_cdf(1.5, 7), places=9)

    def test_normal_approximation_moments_are_computed(self):
        """B(40, 0.3) → μ = np = 12 and σ = √(npq) = √8.4 = 2.898. An overlay drawn with any
        other μ or σ is not the normal approximation to that binomial."""
        text = _svg_text(self._render({
            "distribution": "binomial", "parameters": {"n": 40, "p": 0.3},
            "overlay_normal": True, "shaded_regions": [{"from": 10, "to": 14}],
        }))
        self.assertIn("μ = 12", text)
        self.assertIn("σ = 2.898", text)

    def test_overlay_normal_on_a_continuous_curve_is_rejected(self):
        """The normal approximation approximates a DISCRETE distribution. Overlaying a normal on
        a normal is meaningless and signals a confused question."""
        with self.assertRaises(Exception):
            self._render({"distribution": "normal",
                          "parameters": {"mean": 0, "std_dev": 1}, "overlay_normal": True})

    def test_missing_parameters_are_rejected(self):
        for params in ({"distribution": "normal", "parameters": {"mean": 5}},
                       {"distribution": "binomial", "parameters": {"n": 10}},
                       {"distribution": "poisson", "parameters": {}},
                       {"distribution": "t", "parameters": {}}):
            with self.assertRaises(Exception):
                self._render(params)

    def test_unknown_distribution_rejected(self):
        with self.assertRaises(Exception):
            self._render({"distribution": "gamma", "parameters": {"mean": 1}})

    def test_a_backwards_region_is_rejected(self):
        with self.assertRaises(Exception):
            self._render({"distribution": "standard_normal",
                          "shaded_regions": [{"from": 2, "to": -2}]})

    def test_computed_probability_and_bands_reach_the_page(self):
        """The area is integrated in code and printed; the ±kσ percentages are computed too.
        All of it has to land inside the axes."""
        text = _svg_text(self._render({
            "distribution": "standard_normal",
            "shaded_regions": [{"from": -1, "to": 1}],
            "show_sd_lines": True,
        }))
        self.assertIn("0.6827", text)
        self.assertIn("68.27%", text)
        self.assertIn("95.45%", text)
        self.assertIn("99.73%", text)

    def test_every_distribution_renders(self):
        for params in (
            {"distribution": "standard_normal",
             "shaded_regions": [{"from": -1, "to": 1}], "show_sd_lines": True},
            {"distribution": "normal", "parameters": {"mean": 100, "std_dev": 15},
             "shaded_regions": [{"from": 130}]},
            {"distribution": "binomial", "parameters": {"n": 10, "p": 0.5},
             "shaded_regions": [{"from": 7, "label": "P(X ≥ 7)"}]},
            {"distribution": "poisson", "parameters": {"lambda": 4},
             "shaded_regions": [{"to": 2}]},
            {"distribution": "t", "parameters": {"df": 5},
             "shaded_regions": [{"from": 2.015}]},
        ):
            self.assertTrue(_is_valid_svg(self._render(params)), params["distribution"])


# ── Dispatcher ────────────────────────────────────────────────────────────────

class TestMathematicsExt2Dispatcher(SimpleTestCase):
    SUBTYPES = ("height_distance", "combined_solid", "plane_line_3d", "distribution_curve")

    def test_all_four_subtypes_are_registered(self):
        for subtype in self.SUBTYPES:
            self.assertIn(subtype, MATHEMATICS_RENDERERS)

    def test_unknown_subtype_raises(self):
        with self.assertRaises(ValueError):
            render_mathematics("not_a_real_math_diagram", {})

    def test_renders_are_deterministic(self):
        """Same params must give byte-identical SVG — a paper regenerated for a reprint must not
        silently differ from the one the students already sat."""
        cases = {
            "height_distance": {
                "objects": [{"label": "Tower", "distance": 30, "angle_of_elevation": 30}]},
            "combined_solid": {
                "components": [{"solid_type": "hemisphere", "radius": 3},
                               {"solid_type": "cone", "radius": 3, "height": 4}],
                "show_total_surface_area": True},
            "plane_line_3d": {
                "planes": [{"a": 1, "b": 2, "c": 2, "d": 6}],
                "points": [{"x": 1, "y": 2, "z": 3, "label": "P"}], "show_distance": True},
            "distribution_curve": {
                "distribution": "standard_normal",
                "shaded_regions": [{"from": -1, "to": 1}]},
        }
        for subtype, params in cases.items():
            self.assertEqual(render_mathematics(subtype, params),
                             render_mathematics(subtype, params), subtype)
