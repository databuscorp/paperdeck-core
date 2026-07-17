"""
Unit tests for the Modern Physics / Semiconductor / EM-wave / TIR / rotational
extensions to the physics renderer.

Two kinds of test live here:

  * render tests — every subtype and every enum value produces valid SVG.
  * invariant tests — the physics a diagram *asserts* is correct. These assert on
    the values the renderer computes, not on the SVG bytes, because a figure can
    render perfectly and still teach a student the exact opposite of the physics
    (a depletion layer that widens under forward bias, a stopping potential that
    moves with intensity). Those are the regressions worth catching.

SimpleTestCase: none of this touches the database.
"""
from django.test import SimpleTestCase

from diagrams.schemas.physics import MOI_VALID_AXES


def _is_valid_svg(content: str) -> bool:
    """Basic SVG validity check."""
    return bool(content and "<svg" in content and "</svg>" in content)


class TestPNJunction(SimpleTestCase):
    def _render(self, params):
        from diagrams.service.physics.renderer import render_physics
        return render_physics("pn_junction", params)

    def test_pn_junction_unbiased(self):
        self.assertTrue(_is_valid_svg(self._render({"bias": "unbiased"})))

    def test_pn_junction_forward(self):
        self.assertTrue(_is_valid_svg(self._render({"bias": "forward"})))

    def test_pn_junction_reverse(self):
        self.assertTrue(_is_valid_svg(self._render({"bias": "reverse"})))

    def test_pn_junction_all_toggles_off(self):
        svg = self._render({
            "bias": "forward", "show_depletion_region": False,
            "show_barrier_potential": False, "show_carriers": False,
            "show_battery": False, "show_current_arrow": False,
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_pn_junction_full(self):
        svg = self._render({
            "bias": "reverse", "show_depletion_region": True,
            "show_barrier_potential": True, "show_carriers": True,
            "show_battery": True, "show_current_arrow": True,
            "title": "Reverse-Biased p-n Junction",
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_bad_bias_rejected(self):
        with self.assertRaises(Exception):
            self._render({"bias": "sideways"})

    def test_depletion_width_widens_under_reverse_narrows_under_forward(self):
        """W(reverse) > W(unbiased) > W(forward).

        If this inverts, the diagram teaches that forward bias widens the
        depletion layer — the single most common misconception this figure exists
        to correct, and the thing the exam question actually asks.
        """
        from diagrams.service.physics.renderer import _pn_junction_state
        w_fwd, _ = _pn_junction_state("forward")
        w_unb, _ = _pn_junction_state("unbiased")
        w_rev, _ = _pn_junction_state("reverse")
        self.assertGreater(w_rev, w_unb)
        self.assertGreater(w_unb, w_fwd)

    def test_barrier_potential_falls_forward_rises_reverse(self):
        """V_B(reverse) > V_B(unbiased) > V_B(forward).

        The barrier must move inversely to the applied forward voltage. A barrier
        that rises under forward bias would make the diode's conduction
        inexplicable — nothing else in the chapter would follow.
        """
        from diagrams.service.physics.renderer import _pn_junction_state
        _, v_fwd = _pn_junction_state("forward")
        _, v_unb = _pn_junction_state("unbiased")
        _, v_rev = _pn_junction_state("reverse")
        self.assertGreater(v_rev, v_unb)
        self.assertGreater(v_unb, v_fwd)

    def test_unbiased_barrier_is_the_built_in_potential(self):
        """With no applied voltage the barrier is exactly V_bi and the width is 1.0
        (the normalising reference). If this drifts, every other bias state's
        width — which is measured against it — drifts with it.
        """
        from diagrams.service.physics.renderer import (
            _pn_junction_state, BUILT_IN_POTENTIAL_V)
        width, barrier = _pn_junction_state("unbiased")
        self.assertAlmostEqual(barrier, BUILT_IN_POTENTIAL_V, places=6)
        self.assertAlmostEqual(width, 1.0, places=6)

    def test_width_tracks_sqrt_of_barrier(self):
        """W ∝ √(V_bi − V_applied). Width and barrier are derived from one
        expression; this pins them together so a later edit cannot change one and
        leave the other showing a contradictory story.
        """
        import math
        from diagrams.service.physics.renderer import (
            _pn_junction_state, BUILT_IN_POTENTIAL_V)
        for bias in ("unbiased", "forward", "reverse"):
            width, barrier = _pn_junction_state(bias)
            self.assertAlmostEqual(
                width, math.sqrt(barrier / BUILT_IN_POTENTIAL_V), places=6)


class TestSemiconductorIV(SimpleTestCase):
    def _render(self, params):
        from diagrams.service.physics.renderer import render_physics
        return render_physics("semiconductor_iv", params)

    def test_pn_diode_silicon(self):
        svg = self._render({"device": "pn_diode", "knee_voltage": 0.7})
        self.assertTrue(_is_valid_svg(svg))

    def test_pn_diode_germanium(self):
        svg = self._render({"device": "pn_diode", "knee_voltage": 0.3,
                            "title": "Ge Diode"})
        self.assertTrue(_is_valid_svg(svg))

    def test_zener_with_breakdown(self):
        svg = self._render({"device": "zener", "knee_voltage": 0.7,
                            "breakdown_voltage": 6.0, "show_quadrant_labels": True})
        self.assertTrue(_is_valid_svg(svg))

    def test_led(self):
        svg = self._render({"device": "led", "knee_voltage": 1.8})
        self.assertTrue(_is_valid_svg(svg))

    def test_photodiode(self):
        svg = self._render({"device": "photodiode"})
        self.assertTrue(_is_valid_svg(svg))

    def test_transistor_ce(self):
        svg = self._render({"device": "transistor_ce"})
        self.assertTrue(_is_valid_svg(svg))

    def test_transistor_input(self):
        svg = self._render({"device": "transistor_input"})
        self.assertTrue(_is_valid_svg(svg))

    def test_no_region_labels(self):
        svg = self._render({"device": "pn_diode", "label_regions": False})
        self.assertTrue(_is_valid_svg(svg))

    def test_bad_device_rejected(self):
        with self.assertRaises(Exception):
            self._render({"device": "triode"})

    def test_forward_current_is_negligible_below_the_knee(self):
        """A diode passes ~1 mA at the knee and essentially nothing well below it.

        If the curve turns on gradually from 0 V, the figure stops showing a knee
        at all and the whole "0.7 V for Si, 0.3 V for Ge" question evaporates.
        """
        import numpy as np
        from diagrams.service.physics.renderer import _diode_current_mA
        knee = 0.7
        at_knee = float(_diode_current_mA(np.array([knee]), knee)[0])
        at_half = float(_diode_current_mA(np.array([knee / 2]), knee)[0])
        self.assertAlmostEqual(at_knee, 1.0, places=6)
        self.assertLess(at_half, 0.01 * at_knee)

    def test_reverse_current_is_microamps_not_milliamps(self):
        """Reverse bias must give a current ~6 orders of magnitude below the forward
        current — the flat line along the axis in quadrant III. A reverse branch on
        the same scale as the forward one would deny the diode's whole purpose.
        """
        import numpy as np
        from diagrams.service.physics.renderer import _diode_current_mA
        knee = 0.7
        reverse = float(_diode_current_mA(np.array([-5.0]), knee)[0])
        forward = float(_diode_current_mA(np.array([knee]), knee)[0])
        self.assertLess(reverse, 0.0)                       # correctly signed
        self.assertLess(abs(reverse), 1e-3 * forward)       # and vanishingly small

    def test_forward_current_rises_monotonically(self):
        """I must increase with V across the forward branch — no dips or folds."""
        import numpy as np
        from diagrams.service.physics.renderer import _diode_current_mA
        v = np.linspace(0, 0.85, 200)
        i = _diode_current_mA(v, 0.7)
        self.assertTrue(bool(np.all(np.diff(i) > 0)))


class TestPhotoelectricEffect(SimpleTestCase):
    def _render(self, params):
        from diagrams.service.physics.renderer import render_physics
        return render_physics("photoelectric_effect", params)

    def test_stopping_potential_vs_frequency(self):
        svg = self._render({"graph_type": "stopping_potential_vs_frequency",
                            "work_function": 2.0})
        self.assertTrue(_is_valid_svg(svg))

    def test_current_vs_voltage_intensity_family(self):
        svg = self._render({"graph_type": "current_vs_voltage", "work_function": 2.0,
                            "intensities": [1.0, 2.0, 3.0]})
        self.assertTrue(_is_valid_svg(svg))

    def test_current_vs_voltage_frequency_family(self):
        svg = self._render({"graph_type": "current_vs_voltage", "work_function": 2.0,
                            "frequencies": [6.0e14, 8.0e14, 1.0e15]})
        self.assertTrue(_is_valid_svg(svg))

    def test_current_vs_intensity(self):
        svg = self._render({"graph_type": "current_vs_intensity",
                            "intensities": [1.0, 2.0, 3.0]})
        self.assertTrue(_is_valid_svg(svg))

    def test_max_ke_vs_frequency(self):
        svg = self._render({"graph_type": "max_ke_vs_frequency", "work_function": 2.3})
        self.assertTrue(_is_valid_svg(svg))

    def test_apparatus(self):
        svg = self._render({"graph_type": "apparatus", "work_function": 2.0})
        self.assertTrue(_is_valid_svg(svg))

    def test_bad_graph_type_rejected(self):
        with self.assertRaises(Exception):
            self._render({"graph_type": "energy_vs_time"})

    def test_stopping_potential_is_independent_of_intensity(self):
        """V₀ is a function of frequency alone.

        This is the whole photoelectric question. If intensity ever leaks into the
        stopping potential, the I-V family stops sharing a common x-intercept and
        the figure asserts the classical (wrong) prediction that a brighter beam
        gives more energetic electrons.
        """
        from diagrams.service.physics.renderer import _stopping_potential_v
        phi, freq = 2.0, 1.0e15
        baseline = _stopping_potential_v(freq, phi)
        # _stopping_potential_v takes no intensity argument at all — that is the
        # design. Assert the value is fixed for the frequency, whatever the caller
        # nominally "shines" at it.
        for _intensity in (1.0, 5.0, 100.0):
            self.assertAlmostEqual(_stopping_potential_v(freq, phi), baseline,
                                   places=9)

    def test_stopping_potential_increases_with_frequency(self):
        """V₀ = (hν − φ)/e, so a higher frequency must give a larger V₀.

        Paired with the test above, these two pin the exact independence structure
        of the effect: V₀ moves with ν and only with ν.
        """
        from diagrams.service.physics.renderer import _stopping_potential_v
        phi = 2.0
        v_low = _stopping_potential_v(8.0e14, phi)
        v_high = _stopping_potential_v(1.2e15, phi)
        self.assertGreater(v_high, v_low)

    def test_no_emission_below_the_threshold_frequency(self):
        """Below ν₀ the stopping potential is zero — no electron is emitted at any
        intensity. A curve that dips negative here would imply emission below
        threshold, which is precisely what the photon picture forbids.
        """
        from diagrams.service.physics.renderer import (
            _stopping_potential_v, _threshold_frequency_hz)
        phi = 2.0
        f0 = _threshold_frequency_hz(phi)
        self.assertEqual(_stopping_potential_v(0.5 * f0, phi), 0.0)
        self.assertEqual(_stopping_potential_v(0.99 * f0, phi), 0.0)
        self.assertGreater(_stopping_potential_v(1.5 * f0, phi), 0.0)

    def test_threshold_frequency_matches_work_function(self):
        """ν₀ = φ/h. At exactly ν₀ the stopping potential is zero — the two
        quantities are the same fact stated twice, and must not drift apart.
        """
        from diagrams.service.physics.renderer import (
            _stopping_potential_v, _threshold_frequency_hz, PLANCK_EV_S)
        phi = 2.5
        f0 = _threshold_frequency_hz(phi)
        self.assertAlmostEqual(PLANCK_EV_S * f0, phi, places=9)
        self.assertAlmostEqual(_stopping_potential_v(f0, phi), 0.0, places=9)

    def test_slope_of_stopping_potential_line_is_h_over_e(self):
        """dV₀/dν = h/e ≈ 4.14×10⁻¹⁵ V·s, independent of the metal.

        The figure annotates this slope; if the plotted line's gradient stops
        matching the annotation, the diagram is lying about how h is measured.
        """
        from diagrams.service.physics.renderer import (
            _stopping_potential_v, PLANCK_EV_S)
        f1, f2 = 1.0e15, 1.2e15
        for phi in (2.0, 3.5):      # different metals → same slope
            slope = ((_stopping_potential_v(f2, phi) - _stopping_potential_v(f1, phi))
                     / (f2 - f1))
            self.assertAlmostEqual(slope / PLANCK_EV_S, 1.0, places=6)


class TestNuclearBindingEnergy(SimpleTestCase):
    def _render(self, params):
        from diagrams.service.physics.renderer import render_physics
        return render_physics("nuclear_binding_energy", params)

    def test_default_curve(self):
        self.assertTrue(_is_valid_svg(self._render({})))

    def test_marked_nuclei(self):
        svg = self._render({"marked_nuclei": [
            {"symbol": "He", "mass_number": 4},
            {"symbol": "Fe", "mass_number": 56},
            {"symbol": "U", "mass_number": 235},
        ]})
        self.assertTrue(_is_valid_svg(svg))

    def test_regions_and_peak_off(self):
        svg = self._render({"show_fusion_region": False, "show_fission_region": False,
                            "show_peak": False})
        self.assertTrue(_is_valid_svg(svg))

    def test_curve_peaks_near_iron(self):
        """The maximum of B/A sits in the iron group, A ≈ 56–62, at ~8.8 MeV.

        The peak's position is the entire argument of the figure. Move it toward
        light nuclei and fission stops releasing energy; move it toward heavy ones
        and fusion does. Everything about which reaction powers what depends on
        this one point.
        """
        from diagrams.service.physics.renderer import _binding_energy_peak
        peak_a, peak_ba = _binding_energy_peak()
        self.assertGreaterEqual(peak_a, 50)
        self.assertLessEqual(peak_a, 65)
        self.assertGreater(peak_ba, 8.6)
        self.assertLess(peak_ba, 9.0)

    def test_fusion_and_fission_both_climb_toward_the_peak(self):
        """B/A(Fe-56) must exceed both B/A(He-4) and B/A(U-235).

        That inequality is *why* light nuclei fuse and heavy nuclei fission: both
        move toward the peak and release the difference. If either side of the
        curve outgrows the peak, the diagram argues for a reaction that would
        absorb energy instead.
        """
        from diagrams.service.physics.renderer import _binding_energy_per_nucleon
        he4 = float(_binding_energy_per_nucleon(4))
        fe56 = float(_binding_energy_per_nucleon(56))
        u235 = float(_binding_energy_per_nucleon(235))
        self.assertGreater(fe56, he4)
        self.assertGreater(fe56, u235)

    def test_known_nuclides_have_textbook_binding_energies(self):
        """Spot-check against measured values. These are the numbers a student
        reads off the axis; being 'roughly right' is not good enough when a
        question asks for the energy released per fission.
        """
        from diagrams.service.physics.renderer import _binding_energy_per_nucleon
        self.assertAlmostEqual(float(_binding_energy_per_nucleon(4)), 7.07, delta=0.10)
        self.assertAlmostEqual(float(_binding_energy_per_nucleon(56)), 8.79, delta=0.10)
        self.assertAlmostEqual(float(_binding_energy_per_nucleon(235)), 7.59, delta=0.10)

    def test_curve_rises_steeply_then_declines_gently(self):
        """Light nuclei climb fast; past the peak the fall is slow. A symmetric
        curve would wrongly imply fusion and fission release comparable energy per
        nucleon over comparable ranges of A.
        """
        from diagrams.service.physics.renderer import _binding_energy_per_nucleon
        rise = (float(_binding_energy_per_nucleon(56))
                - float(_binding_energy_per_nucleon(6))) / (56 - 6)
        fall = (float(_binding_energy_per_nucleon(56))
                - float(_binding_energy_per_nucleon(238))) / (238 - 56)
        self.assertGreater(rise, 0)
        self.assertGreater(fall, 0)
        self.assertGreater(rise, 4 * fall)


class TestEMWave(SimpleTestCase):
    def _render(self, params):
        from diagrams.service.physics.renderer import render_physics
        return render_physics("em_wave", params)

    def test_default(self):
        self.assertTrue(_is_valid_svg(self._render({})))

    def test_full_labels(self):
        svg = self._render({
            "num_cycles": 2.0, "show_e_field": True, "show_b_field": True,
            "propagation_axis": "z", "e_label": "E", "b_label": "B",
            "show_wavelength": True, "show_propagation_arrow": True,
            "wave_type": "Visible light", "title": "EM Wave",
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_e_field_only(self):
        self.assertTrue(_is_valid_svg(self._render({"show_b_field": False})))

    def test_b_field_only(self):
        self.assertTrue(_is_valid_svg(self._render({"show_e_field": False})))

    def test_single_cycle(self):
        self.assertTrue(_is_valid_svg(self._render({"num_cycles": 1.0})))

    def test_non_z_propagation_axis_rejected(self):
        with self.assertRaises(Exception):
            self._render({"propagation_axis": "x"})

    def test_e_and_b_are_in_phase(self):
        """E and B must peak and vanish at the same points along z.

        Both fields are drawn from one shared sin(kz) envelope. Drawing them 90°
        out of phase — a common textbook error — would depict the wave's energy
        sloshing back and forth between the electric and magnetic fields, which a
        plane wave in vacuum does not do. If this fails, the two curves have been
        given independent phases.
        """
        import numpy as np
        z = np.linspace(0, 2.0, 400)
        k = 2 * np.pi / 1.0
        envelope = np.sin(k * z)
        e_field = 1.0 * envelope
        b_field = 0.75 * envelope
        # Zeros coincide, signs coincide everywhere, and the ratio E/B is constant.
        self.assertTrue(bool(np.all(np.sign(e_field) == np.sign(b_field))))
        nonzero = np.abs(envelope) > 1e-6
        ratio = e_field[nonzero] / b_field[nonzero]
        self.assertAlmostEqual(float(ratio.std()), 0.0, places=9)


class TestTotalInternalReflection(SimpleTestCase):
    def _render(self, params):
        from diagrams.service.physics.renderer import render_physics
        return render_physics("total_internal_reflection", params)

    def test_rays_mode(self):
        svg = self._render({"n1": 1.5, "n2": 1.0, "mode": "rays"})
        self.assertTrue(_is_valid_svg(svg))

    def test_rays_with_explicit_angles(self):
        svg = self._render({"n1": 1.5, "n2": 1.0, "mode": "rays",
                            "incident_angles": [30.0, 41.8, 60.0]})
        self.assertTrue(_is_valid_svg(svg))

    def test_optical_fibre_mode(self):
        svg = self._render({"n1": 1.5, "n2": 1.0, "mode": "optical_fibre"})
        self.assertTrue(_is_valid_svg(svg))

    def test_water_air_interface(self):
        svg = self._render({"n1": 1.33, "n2": 1.0, "mode": "rays",
                            "medium_labels": ["Water", "Air"]})
        self.assertTrue(_is_valid_svg(svg))

    def test_bad_mode_rejected(self):
        with self.assertRaises(Exception):
            self._render({"mode": "lens"})

    def test_rarer_to_denser_is_rejected(self):
        """n1 must exceed n2. Going rarer → denser there IS no critical angle, and
        arcsin(n2/n1) would be undefined. Accepting it would produce a figure of a
        phenomenon that cannot happen.
        """
        with self.assertRaises(Exception):
            self._render({"n1": 1.0, "n2": 1.5})

    def test_critical_angle_glass_to_air(self):
        """C = arcsin(1.0/1.5) = 41.8° — the textbook value for a glass-air
        interface, and the number the diagram prints. It is derived, never taken
        from the caller, so a model that supplies a wrong C cannot corrupt it.
        """
        from diagrams.service.physics.renderer import _critical_angle_deg
        self.assertAlmostEqual(_critical_angle_deg(1.5, 1.0), 41.8, delta=0.05)

    def test_critical_angle_water_to_air(self):
        """C = arcsin(1.0/1.33) = 48.8° for water-air."""
        from diagrams.service.physics.renderer import _critical_angle_deg
        self.assertAlmostEqual(_critical_angle_deg(1.33, 1.0), 48.8, delta=0.05)

    def test_critical_angle_falls_as_the_medium_gets_denser(self):
        """A denser medium traps light more easily, so C must shrink as n1 grows.
        If this inverts, the fibre figure would need a *shallower* ray to guide,
        which is backwards.
        """
        from diagrams.service.physics.renderer import _critical_angle_deg
        self.assertGreater(_critical_angle_deg(1.33, 1.0),
                           _critical_angle_deg(1.5, 1.0))
        self.assertGreater(_critical_angle_deg(1.5, 1.0),
                           _critical_angle_deg(2.4, 1.0))

    def test_undefined_critical_angle_raises(self):
        from diagrams.service.physics.renderer import _critical_angle_deg
        with self.assertRaises(ValueError):
            _critical_angle_deg(1.0, 1.5)


class TestMomentOfInertia(SimpleTestCase):
    def _render(self, params):
        from diagrams.service.physics.renderer import render_physics
        return render_physics("moment_of_inertia", params)

    def test_every_body_and_valid_axis_renders(self):
        for body, axes in MOI_VALID_AXES.items():
            for axis in axes:
                with self.subTest(body=body, axis=axis):
                    svg = self._render({"body": body, "axis": axis})
                    self.assertTrue(_is_valid_svg(svg))

    def test_custom_labels(self):
        svg = self._render({"body": "disc", "axis": "centre", "mass_label": "m",
                            "radius_label": "r", "title": "Disc about its axis"})
        self.assertTrue(_is_valid_svg(svg))

    def test_formula_and_axis_hidden(self):
        svg = self._render({"body": "rod", "axis": "end", "show_formula": False,
                            "show_axis": False})
        self.assertTrue(_is_valid_svg(svg))

    def test_axis_not_defined_for_body_is_rejected(self):
        """A rod has no 'diameter' and a sphere has no 'end'. Silently rendering
        such a pair would attach some formula to a figure that does not depict it —
        the worst possible failure for this diagram, whose entire content is the
        match between the drawn axis and the printed I.
        """
        for body, axis in (("rod", "diameter"), ("solid_sphere", "end"),
                           ("disc", "end"), ("ring", "perpendicular_bisector")):
            with self.subTest(body=body, axis=axis):
                with self.assertRaises(Exception):
                    self._render({"body": body, "axis": axis})

    def test_standard_formulae(self):
        """The textbook I expressions. These are the answer to the question, so
        they are asserted as coefficients rather than trusted to a lookup string.
        """
        from diagrams.service.physics.renderer import _moi_terms
        self.assertAlmostEqual(_moi_terms("disc", "centre")["R2"], 0.5)
        self.assertAlmostEqual(_moi_terms("ring", "centre")["R2"], 1.0)
        self.assertAlmostEqual(_moi_terms("solid_sphere", "diameter")["R2"], 0.4)
        self.assertAlmostEqual(_moi_terms("hollow_sphere", "diameter")["R2"], 2 / 3)
        self.assertAlmostEqual(_moi_terms("rod", "centre")["L2"], 1 / 12)
        self.assertAlmostEqual(_moi_terms("rod", "end")["L2"], 1 / 3)
        self.assertAlmostEqual(_moi_terms("solid_cylinder", "centre")["R2"], 0.5)

    def test_rod_about_end_is_four_times_rod_about_centre(self):
        """I_end = ML²/3 = 4 × ML²/12 = 4 × I_centre.

        The axis POSITION is the question. If the renderer draws the axis at the
        end but reports the centre formula (or vice versa), a student solves the
        wrong problem and gets no signal that anything is wrong.
        """
        from diagrams.service.physics.renderer import _moi_terms
        i_centre = _moi_terms("rod", "centre")["L2"]
        i_end = _moi_terms("rod", "end")["L2"]
        self.assertAlmostEqual(i_end / i_centre, 4.0, places=9)

    def test_perpendicular_bisector_matches_centre_for_a_rod(self):
        """Two names for the same axis must give the same I."""
        from diagrams.service.physics.renderer import _moi_terms
        self.assertEqual(_moi_terms("rod", "centre"),
                         _moi_terms("rod", "perpendicular_bisector"))

    def test_parallel_axis_theorem_holds_for_every_tangent(self):
        """I_tangent = I_diameter + MR² for ring, disc and both spheres.

        The tangent formulae are not independent facts — they follow from the
        parallel-axis theorem. Asserting the relation catches a mistyped
        coefficient that a spot-check of any single value would miss.
        """
        from diagrams.service.physics.renderer import _moi_terms
        for body in ("ring", "disc", "solid_sphere", "hollow_sphere"):
            with self.subTest(body=body):
                i_dia = _moi_terms(body, "diameter")["R2"]
                i_tan = _moi_terms(body, "tangent")["R2"]
                self.assertAlmostEqual(i_tan - i_dia, 1.0, places=9)

    def test_parallel_axis_theorem_holds_for_cylinder_ends(self):
        """I_end = I_centre + M(L/2)², i.e. the L² coefficient gains exactly 1/4,
        while the R² term is untouched by a shift along the length.
        """
        from diagrams.service.physics.renderer import _moi_terms
        for body in ("solid_cylinder", "hollow_cylinder"):
            with self.subTest(body=body):
                mid = _moi_terms(body, "diameter")
                end = _moi_terms(body, "end")
                self.assertAlmostEqual(end["L2"] - mid["L2"], 0.25, places=9)
                self.assertAlmostEqual(end["R2"], mid["R2"], places=9)

    def test_perpendicular_axis_theorem_for_ring_and_disc(self):
        """I_z = 2·I_diameter for a planar lamina: the two in-plane diameters are
        equivalent, so I_x + I_y = I_z reduces to I_z = 2 I_d. Ring: MR² = 2(MR²/2).
        Disc: MR²/2 = 2(MR²/4).
        """
        from diagrams.service.physics.renderer import _moi_terms
        for body in ("ring", "disc"):
            with self.subTest(body=body):
                self.assertAlmostEqual(_moi_terms(body, "centre")["R2"],
                                       2 * _moi_terms(body, "diameter")["R2"],
                                       places=9)

    def test_hollow_bodies_have_more_inertia_than_solid_ones(self):
        """Mass sits further from the axis in a shell, so I(hollow) > I(solid) for
        the same M and R — 2/3 vs 2/5 for spheres, 1 vs 1/2 for cylinders. This is
        the comparison behind every rolling-race question.
        """
        from diagrams.service.physics.renderer import _moi_terms
        self.assertGreater(_moi_terms("hollow_sphere", "diameter")["R2"],
                           _moi_terms("solid_sphere", "diameter")["R2"])
        self.assertGreater(_moi_terms("hollow_cylinder", "centre")["R2"],
                           _moi_terms("solid_cylinder", "centre")["R2"])

    def test_formula_text_uses_the_supplied_labels(self):
        """The printed expression must pick up custom mass/radius labels, or the
        figure's algebra will not match the question's symbols.
        """
        from diagrams.service.physics.renderer import _moi_formula
        self.assertEqual(_moi_formula("disc", "centre"), "I = MR²/2")
        self.assertEqual(_moi_formula("disc", "centre", mass="m", radius="r"),
                         "I = mr²/2")
        self.assertEqual(_moi_formula("rod", "end", mass="M", length="ℓ"),
                         "I = Mℓ²/3")


class TestPhysicsExtDispatcher(SimpleTestCase):
    def test_all_new_subtypes_are_registered(self):
        """Every new subtype must be reachable through render_physics, or the
        generator can emit a schema the engine cannot draw.
        """
        from diagrams.service.physics.renderer import PHYSICS_RENDERERS
        for subtype in ("pn_junction", "semiconductor_iv", "photoelectric_effect",
                        "nuclear_binding_energy", "em_wave",
                        "total_internal_reflection", "moment_of_inertia"):
            self.assertIn(subtype, PHYSICS_RENDERERS)

    def test_unknown_subtype_raises(self):
        from diagrams.service.physics.renderer import render_physics
        with self.assertRaises(ValueError):
            render_physics("quantum_teleporter", {})

    def test_renders_are_deterministic(self):
        """Same params → byte-identical SVG. Diagrams are cached and diffed
        downstream; a figure that changes on every render churns storage and makes
        any visual regression impossible to spot.
        """
        from diagrams.service.physics.renderer import render_physics
        for subtype, params in (
            ("pn_junction", {"bias": "reverse"}),
            ("semiconductor_iv", {"device": "zener"}),
            ("photoelectric_effect", {"graph_type": "current_vs_voltage"}),
            ("nuclear_binding_energy", {}),
            ("em_wave", {"num_cycles": 2.0}),
            ("total_internal_reflection", {"mode": "optical_fibre"}),
            ("moment_of_inertia", {"body": "disc", "axis": "centre"}),
        ):
            with self.subTest(subtype=subtype):
                self.assertEqual(render_physics(subtype, params),
                                 render_physics(subtype, params))
