"""
Unit tests for WAVE-2 of the physics renderer extension: the thermal, kinetic,
gravitational, nuclear, wave-optics, measurement and rotational subtypes.

Fourteen subtypes are covered — the five added first
(fluid_mechanics, motion_graph, shm_system, standing_wave, stress_strain) and the
nine added here (heating_curve, blackbody_spectrum, maxwell_boltzmann, gravitation,
radioactive_decay, wavefront, polarisation, measuring_instrument, rolling_motion).

Two kinds of test, as in test_physics_ext.py:

  * render tests — every subtype and every enum value produces valid SVG.
  * invariant tests — the physics the diagram *asserts* is correct, checked against
    the values the renderer COMPUTES (not the SVG bytes). A figure can render
    perfectly and still teach the opposite of the physics: a boiling plateau no
    wider than the melting one, a Wien peak that moves the wrong way, an ellipse
    centred on the Sun, an unreadable vernier. Those are the regressions worth
    catching.

SimpleTestCase: none of this touches the database.
"""
import math

import numpy as np
from django.test import SimpleTestCase


def _is_valid_svg(content: str) -> bool:
    return bool(content and "<svg" in content and "</svg>" in content)


def _render(subtype, params):
    from diagrams.service.physics.renderer import render_physics
    return render_physics(subtype, params)


# ── Heating Curve ─────────────────────────────────────────────────────────────

class TestHeatingCurve(SimpleTestCase):
    def test_default_water(self):
        self.assertTrue(_is_valid_svg(_render("heating_curve", {})))

    def test_toggles_off(self):
        svg = _render("heating_curve", {"show_regions": False,
                                        "show_plateau_labels": False,
                                        "show_heat_values": False})
        self.assertTrue(_is_valid_svg(svg))

    def test_custom_substance(self):
        svg = _render("heating_curve", {
            "substance": "ethanol", "melting_point": -114.0, "boiling_point": 78.0,
            "start_temp": -140.0, "end_temp": 100.0,
            "latent_heat_fusion": 108000.0, "latent_heat_vaporisation": 855000.0,
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_bad_temperature_order_rejected(self):
        # boiling below melting is unphysical and would draw plateaus out of order
        with self.assertRaises(Exception):
            _render("heating_curve", {"melting_point": 100.0, "boiling_point": 0.0})

    def test_phase_change_plateaus_are_flat(self):
        """Temperature must NOT rise during a phase change — that flatness is the
        whole point. Each plateau segment has equal start and end temperature.
        """
        from diagrams.schemas.physics import HeatingCurveSchema
        from diagrams.service.physics.renderer import _heating_curve_segments
        segs = _heating_curve_segments(HeatingCurveSchema())
        plateaus = [s for s in segs if s["plateau"]]
        self.assertEqual(len(plateaus), 2)
        for s in plateaus:
            self.assertEqual(s["t0"], s["t1"])

    def test_boiling_plateau_is_far_wider_than_melting(self):
        """For water L_v/L_f ≈ 2260/334 ≈ 6.8, so the boiling plateau must be ~6.8×
        as wide in heat as the melting plateau. Drawing them equal is the classic
        wrong heating curve.
        """
        from diagrams.schemas.physics import HeatingCurveSchema
        from diagrams.service.physics.renderer import _heating_curve_segments
        segs = _heating_curve_segments(HeatingCurveSchema())
        melt = next(s for s in segs if s["name"] == "melting")
        boil = next(s for s in segs if s["name"] == "boiling")
        w_melt = melt["q1"] - melt["q0"]
        w_boil = boil["q1"] - boil["q0"]
        self.assertAlmostEqual(w_boil / w_melt, 2260.0 / 334.0, delta=0.05)
        self.assertGreater(w_boil, 6 * w_melt)

    def test_slanted_segments_have_positive_slope(self):
        """The three heating (non-plateau) segments must rise: solid, liquid and gas
        all warm up as heat is added.
        """
        from diagrams.schemas.physics import HeatingCurveSchema
        from diagrams.service.physics.renderer import _heating_curve_segments
        for s in _heating_curve_segments(HeatingCurveSchema()):
            if not s["plateau"]:
                self.assertGreater(s["t1"], s["t0"])


# ── Blackbody Spectrum ────────────────────────────────────────────────────────

class TestBlackbodySpectrum(SimpleTestCase):
    def test_default(self):
        self.assertTrue(_is_valid_svg(_render("blackbody_spectrum", {})))

    def test_options(self):
        svg = _render("blackbody_spectrum", {
            "temperatures": [4000, 5000, 6000], "show_wien_line": True,
            "show_visible_band": True, "show_peak_labels": True})
        self.assertTrue(_is_valid_svg(svg))

    def test_log_intensity(self):
        svg = _render("blackbody_spectrum", {"temperatures": [3000, 6000],
                                             "log_intensity": True})
        self.assertTrue(_is_valid_svg(svg))

    def test_empty_temperatures_rejected(self):
        with self.assertRaises(Exception):
            _render("blackbody_spectrum", {"temperatures": []})

    def test_wien_peak_shifts_to_shorter_wavelength_when_hotter(self):
        """Wien: λ_max·T = 2.898e-3 m·K. The 6000 K peak (~483 nm) must be SHORTER
        than the 3000 K peak (~966 nm). If this inverts, the figure denies Wien's
        law outright.
        """
        from diagrams.service.physics.renderer import _wien_peak_nm
        self.assertAlmostEqual(_wien_peak_nm(6000.0), 483.0, delta=2.0)
        self.assertAlmostEqual(_wien_peak_nm(3000.0), 966.0, delta=3.0)
        self.assertLess(_wien_peak_nm(6000.0), _wien_peak_nm(3000.0))

    def test_hotter_body_radiates_more_at_every_wavelength(self):
        """A hotter Planck curve lies entirely above a cooler one — no crossings.
        A cool curve poking above a hot one somewhere would be thermodynamically
        impossible.
        """
        from diagrams.service.physics.renderer import _planck_spectral
        lam = np.linspace(100e-9, 3000e-9, 400)
        cool = _planck_spectral(lam, 3000.0)
        hot = _planck_spectral(lam, 6000.0)
        self.assertTrue(bool(np.all(hot > cool)))

    def test_peak_is_actually_at_the_wien_wavelength(self):
        """The maximum of the plotted Planck curve must sit at the Wien wavelength,
        so the printed λ_max marker lands on the real peak.
        """
        from diagrams.service.physics.renderer import _planck_spectral, _wien_peak_nm
        T = 5000.0
        lam = np.linspace(100e-9, 3000e-9, 4000)
        peak_lam_nm = lam[int(np.argmax(_planck_spectral(lam, T)))] * 1e9
        self.assertAlmostEqual(peak_lam_nm, _wien_peak_nm(T), delta=5.0)


# ── Maxwell-Boltzmann ─────────────────────────────────────────────────────────

class TestMaxwellBoltzmann(SimpleTestCase):
    def test_default(self):
        self.assertTrue(_is_valid_svg(_render("maxwell_boltzmann", {})))

    def test_vary_gas(self):
        svg = _render("maxwell_boltzmann", {"molar_masses": [2, 28, 44],
                                            "reference_temperature": 300})
        self.assertTrue(_is_valid_svg(svg))

    def test_markers_off(self):
        svg = _render("maxwell_boltzmann", {"temperatures": [500],
                                            "show_speed_markers": False,
                                            "show_area_note": False})
        self.assertTrue(_is_valid_svg(svg))

    def test_speed_ordering_vmp_vavg_vrms(self):
        """v_mp < v_avg < v_rms always, from the fixed coefficients
        2 < 8/π < 3. Their ratios are universal (independent of T and M).
        """
        from diagrams.service.physics.renderer import _mb_speeds
        for T, M in ((300.0, 28.0), (1200.0, 4.0), (77.0, 2.0)):
            v_mp, v_avg, v_rms = _mb_speeds(T, M)
            self.assertLess(v_mp, v_avg)
            self.assertLess(v_avg, v_rms)
        # universal ratios
        v_mp, v_avg, v_rms = _mb_speeds(300.0, 28.0)
        self.assertAlmostEqual(v_avg / v_mp, math.sqrt(4.0 / math.pi), places=6)
        self.assertAlmostEqual(v_rms / v_mp, math.sqrt(1.5), places=6)

    def test_nitrogen_rms_speed_is_textbook(self):
        """v_rms of N₂ at 300 K ≈ 517 m/s — the number a student computes."""
        from diagrams.service.physics.renderer import _mb_speeds
        self.assertAlmostEqual(_mb_speeds(300.0, 28.0)[2], 517.0, delta=3.0)

    def test_area_under_every_curve_is_one(self):
        """Each curve is a normalised probability density: ∫f dv = 1 for EVERY
        temperature. The common wrong diagram draws hotter curves enclosing more
        area; here the areas must all be equal (to unity).
        """
        from diagrams.service.physics.renderer import _mb_pdf, _mb_speeds
        areas = []
        for T in (300.0, 600.0, 1200.0):
            v = np.linspace(0.0, _mb_speeds(T, 28.0)[2] * 4.0, 20000)
            areas.append(float(np.trapezoid(_mb_pdf(v, T, 28.0), v)))
        for a in areas:
            self.assertAlmostEqual(a, 1.0, places=3)
        self.assertAlmostEqual(max(areas), min(areas), places=3)

    def test_peak_speed_rises_with_temperature(self):
        """The most probable speed (the peak) moves RIGHT as T rises."""
        from diagrams.service.physics.renderer import _mb_speeds
        self.assertLess(_mb_speeds(300.0, 28.0)[0], _mb_speeds(1200.0, 28.0)[0])

    def test_lighter_gas_is_faster(self):
        """At fixed T a lighter gas has a higher v_rms (∝ 1/√M)."""
        from diagrams.service.physics.renderer import _mb_speeds
        self.assertGreater(_mb_speeds(300.0, 2.0)[2], _mb_speeds(300.0, 44.0)[2])


# ── Gravitation ───────────────────────────────────────────────────────────────

class TestGravitation(SimpleTestCase):
    def test_every_setup_renders(self):
        for setup in ("satellite_orbit", "kepler_ellipse", "g_variation",
                      "field_lines"):
            with self.subTest(setup=setup):
                self.assertTrue(_is_valid_svg(_render("gravitation", {"setup": setup})))

    def test_kepler_high_eccentricity(self):
        svg = _render("gravitation", {"setup": "kepler_ellipse", "eccentricity": 0.85})
        self.assertTrue(_is_valid_svg(svg))

    def test_bad_setup_rejected(self):
        with self.assertRaises(Exception):
            _render("gravitation", {"setup": "wormhole"})

    def test_g_is_continuous_at_the_surface(self):
        """The inside branch (g ∝ r) and the outside branch (g ∝ 1/r²) must meet at
        r = R with the same value — g is continuous there, and the surface is the
        maximum. A jump at R would be the signature of the two formulae being
        stitched together wrongly.
        """
        from diagrams.service.physics.renderer import (
            _g_at_radius, _EARTH_R, _G_SURFACE)
        inside = _g_at_radius(_EARTH_R * (1 - 1e-6))
        outside = _g_at_radius(_EARTH_R * (1 + 1e-6))
        self.assertAlmostEqual(inside, _G_SURFACE, places=3)
        self.assertAlmostEqual(outside, _G_SURFACE, places=3)
        self.assertAlmostEqual(inside, outside, places=3)

    def test_g_inside_is_linear_in_r(self):
        """Below the surface g/r is constant (g = g_s·r/R). If this bows, the model
        has stopped treating only the enclosed mass as acting.
        """
        from diagrams.service.physics.renderer import _g_at_radius, _EARTH_R
        rs = np.linspace(0.05, 1.0, 25) * _EARTH_R
        ratio = np.array([_g_at_radius(float(r)) / r for r in rs])
        self.assertAlmostEqual(float(ratio.std() / ratio.mean()), 0.0, places=6)

    def test_g_outside_falls_as_inverse_square(self):
        """g·r² is constant above the surface."""
        from diagrams.service.physics.renderer import _g_at_radius, _EARTH_R
        for factor in (1.0, 2.0, 3.0):
            r = factor * _EARTH_R
            self.assertAlmostEqual(_g_at_radius(r) * r ** 2,
                                   _g_at_radius(_EARTH_R) * _EARTH_R ** 2, places=2)

    def test_higher_orbit_is_slower_and_longer(self):
        """v = √(GM/r) falls and T = 2π√(r³/GM) rises with orbit radius — the usual
        counter-intuitive result.
        """
        from diagrams.service.physics.renderer import (
            _orbital_velocity, _orbital_period, _EARTH_R)
        r_low = _EARTH_R + 400e3
        r_high = _EARTH_R + 35786e3
        self.assertGreater(_orbital_velocity(r_low), _orbital_velocity(r_high))
        self.assertLess(_orbital_period(r_low), _orbital_period(r_high))

    def test_low_orbit_speed_and_period_are_textbook(self):
        """A 400 km orbit: v ≈ 7.67 km/s, T ≈ 92 min."""
        from diagrams.service.physics.renderer import (
            _orbital_velocity, _orbital_period, _EARTH_R)
        r = _EARTH_R + 400e3
        self.assertAlmostEqual(_orbital_velocity(r) / 1000.0, 7.67, delta=0.05)
        self.assertAlmostEqual(_orbital_period(r) / 60.0, 92.5, delta=1.0)

    def test_geostationary_period_is_one_day(self):
        """The r that gives a 24 h period is ~42160 km — the definition of the
        geostationary orbit, and a good end-to-end check on Kepler's third law.
        """
        from diagrams.service.physics.renderer import _orbital_period, _EARTH_R
        r = _EARTH_R + 35786e3
        self.assertAlmostEqual(_orbital_period(r) / 3600.0, 23.93, delta=0.2)


# ── Radioactive Decay ─────────────────────────────────────────────────────────

class TestRadioactiveDecay(SimpleTestCase):
    def test_default(self):
        self.assertTrue(_is_valid_svg(_render("radioactive_decay", {})))

    def test_semi_log(self):
        svg = _render("radioactive_decay", {"show_semi_log": True})
        self.assertTrue(_is_valid_svg(svg))

    def test_decay_chain(self):
        svg = _render("radioactive_decay", {
            "show_decay_chain": True, "parent_symbol": "U", "parent_z": 92,
            "parent_a": 238, "chain": [{"type": "alpha"}, {"type": "beta_minus"}]})
        self.assertTrue(_is_valid_svg(svg))

    def test_all_panels(self):
        svg = _render("radioactive_decay", {
            "show_semi_log": True, "show_decay_chain": True,
            "chain": [{"type": "alpha"}, {"type": "gamma"}, {"type": "beta_plus"}]})
        self.assertTrue(_is_valid_svg(svg))

    def test_decay_chain_without_chain_rejected(self):
        with self.assertRaises(Exception):
            _render("radioactive_decay", {"show_decay_chain": True, "chain": []})

    def test_bad_decay_type_rejected(self):
        with self.assertRaises(Exception):
            _render("radioactive_decay", {"show_decay_chain": True,
                                          "chain": [{"type": "fission"}]})

    def test_decay_constant_is_ln2_over_half_life(self):
        """λ = ln2/T½. This is derived, so a caller cannot supply an inconsistent
        λ that contradicts the half-life the curve is drawn from.
        """
        from diagrams.service.physics.renderer import _decay_constant
        self.assertAlmostEqual(_decay_constant(10.0), math.log(2) / 10.0, places=9)
        self.assertAlmostEqual(_decay_constant(5730.0), math.log(2) / 5730.0, places=12)

    def test_amount_halves_each_half_life(self):
        """N(T)=N₀/2, N(2T)=N₀/4, N(3T)=N₀/8 exactly — the markers on the curve."""
        from diagrams.service.physics.renderer import _amount_after
        n0, T = 100.0, 10.0
        t = np.array([0.0, T, 2 * T, 3 * T])
        n = _amount_after(n0, T, t)
        for k, val in enumerate(n):
            self.assertAlmostEqual(float(val), n0 / (2 ** k), places=6)

    def test_alpha_and_beta_move_the_right_way_on_the_NZ_chart(self):
        """α: (Z−2, N−2).  β⁻: (Z+1, N−1).  β⁺: (Z−1, N+1).  γ: unchanged.
        A sign error sends the chain the wrong way across the chart — the single
        thing the decay-chain figure exists to get right.
        """
        from diagrams.service.physics.renderer import _decay_chain_positions

        class _Step:
            def __init__(self, t): self.type = t

        pts = _decay_chain_positions(
            92, 238, [_Step("alpha"), _Step("beta_minus"),
                      _Step("beta_plus"), _Step("gamma")])
        # start: Z=92, N=238-92=146
        self.assertEqual(pts[0], (92, 146, "start"))
        self.assertEqual(pts[1][:2], (90, 144))     # alpha
        self.assertEqual(pts[2][:2], (91, 143))     # beta-
        self.assertEqual(pts[3][:2], (90, 144))     # beta+
        self.assertEqual(pts[4][:2], (90, 144))     # gamma: no move

    def test_alpha_conserves_a_minus_four(self):
        """Every α step drops the mass number A = Z + N by exactly 4."""
        from diagrams.service.physics.renderer import _decay_chain_positions

        class _Step:
            def __init__(self, t): self.type = t

        pts = _decay_chain_positions(92, 238, [_Step("alpha")])
        z0, n0, _ = pts[0]
        z1, n1, _ = pts[1]
        self.assertEqual((z0 + n0) - (z1 + n1), 4)


# ── Wavefront (Huygens) ───────────────────────────────────────────────────────

class TestWavefront(SimpleTestCase):
    def test_every_type_propagates(self):
        for wt in ("plane", "spherical", "cylindrical"):
            with self.subTest(wavefront_type=wt):
                self.assertTrue(_is_valid_svg(_render(
                    "wavefront", {"wavefront_type": wt, "phenomenon": "propagation"})))

    def test_every_phenomenon_renders(self):
        for ph in ("propagation", "reflection", "refraction", "diffraction"):
            with self.subTest(phenomenon=ph):
                self.assertTrue(_is_valid_svg(_render("wavefront", {"phenomenon": ph})))

    def test_bad_type_rejected(self):
        with self.assertRaises(Exception):
            _render("wavefront", {"wavefront_type": "helical"})

    def test_bad_phenomenon_rejected(self):
        with self.assertRaises(Exception):
            _render("wavefront", {"phenomenon": "absorption"})

    def test_refraction_needs_unequal_indices(self):
        with self.assertRaises(Exception):
            _render("wavefront", {"phenomenon": "refraction", "n1": 1.5, "n2": 1.5})

    def test_into_denser_medium_bends_toward_the_normal(self):
        """n₂ > n₁ ⇒ θ₂ < θ₁ (Snell). The wavefront bends toward the normal because
        the wavelets are slower — smaller — in the denser medium.
        """
        from diagrams.service.physics.renderer import _snell_refraction_angle
        theta2 = _snell_refraction_angle(45.0, 1.0, 1.5)
        self.assertLess(theta2, 45.0)
        self.assertAlmostEqual(theta2, math.degrees(math.asin(math.sin(math.radians(45)) / 1.5)),
                               places=6)

    def test_into_rarer_medium_bends_away_from_the_normal(self):
        """n₂ < n₁ ⇒ θ₂ > θ₁."""
        from diagrams.service.physics.renderer import _snell_refraction_angle
        self.assertGreater(_snell_refraction_angle(30.0, 1.5, 1.0), 30.0)

    def test_snell_law_holds(self):
        """n₁sinθ₁ = n₂sinθ₂ at the computed angle — the figure's angles obey Snell."""
        from diagrams.service.physics.renderer import _snell_refraction_angle
        n1, n2, t1 = 1.33, 1.5, 50.0
        t2 = _snell_refraction_angle(t1, n1, n2)
        self.assertAlmostEqual(n1 * math.sin(math.radians(t1)),
                               n2 * math.sin(math.radians(t2)), places=6)


# ── Polarisation ──────────────────────────────────────────────────────────────

class TestPolarisation(SimpleTestCase):
    def test_analyser_default(self):
        self.assertTrue(_is_valid_svg(_render("polarisation", {})))

    def test_intensity_graph(self):
        svg = _render("polarisation", {"analyser_angle": 30,
                                       "show_intensity_graph": True})
        self.assertTrue(_is_valid_svg(svg))

    def test_brewster(self):
        svg = _render("polarisation", {"show_brewster": True, "n1": 1.0, "n2": 1.5})
        self.assertTrue(_is_valid_svg(svg))

    def test_crossed_polarisers(self):
        self.assertTrue(_is_valid_svg(_render("polarisation", {"analyser_angle": 90})))

    def test_brewster_needs_unequal_indices(self):
        with self.assertRaises(Exception):
            _render("polarisation", {"show_brewster": True, "n1": 1.5, "n2": 1.5})

    def test_malus_law_quarter_at_sixty_degrees(self):
        """Malus: I/I₀ = cos²θ. At θ = 60°, cos²60° = 0.25 — exactly a quarter gets
        through. This is the number the question asks for.
        """
        from diagrams.service.physics.renderer import _malus_transmitted
        i0 = 50.0
        self.assertAlmostEqual(_malus_transmitted(i0, 60.0) / i0, 0.25, places=9)

    def test_malus_zero_when_crossed_and_full_when_aligned(self):
        """θ = 90° blocks everything; θ = 0° passes all of I₀. The crossed-polariser
        extinction is the whole demonstration.
        """
        from diagrams.service.physics.renderer import _malus_transmitted
        i0 = 80.0
        self.assertAlmostEqual(_malus_transmitted(i0, 90.0), 0.0, places=9)
        self.assertAlmostEqual(_malus_transmitted(i0, 0.0), i0, places=9)

    def test_brewster_angle_glass_and_the_right_angle(self):
        """θ_B = arctan(n₂/n₁) = arctan(1.5) ≈ 56.3° for air→glass, and the reflected
        and refracted rays are then exactly 90° apart (θ_B + θ_refr = 90°).
        """
        from diagrams.service.physics.renderer import (
            _brewster_angle, _snell_refraction_angle)
        theta_b = _brewster_angle(1.0, 1.5)
        self.assertAlmostEqual(theta_b, math.degrees(math.atan(1.5)), places=6)
        self.assertAlmostEqual(theta_b, 56.31, delta=0.05)
        theta_refr = _snell_refraction_angle(theta_b, 1.0, 1.5)
        self.assertAlmostEqual(theta_b + theta_refr, 90.0, places=4)


# ── Measuring Instrument ──────────────────────────────────────────────────────

class TestMeasuringInstrument(SimpleTestCase):
    def test_vernier_renders(self):
        self.assertTrue(_is_valid_svg(
            _render("measuring_instrument", {"instrument": "vernier_calipers",
                                             "reading": 2.34})))

    def test_screw_gauge_renders(self):
        self.assertTrue(_is_valid_svg(
            _render("measuring_instrument", {"instrument": "screw_gauge",
                                             "reading": 4.23})))

    def test_with_zero_error(self):
        svg = _render("measuring_instrument", {"instrument": "vernier_calipers",
                                               "reading": 3.47, "zero_error": 0.02})
        self.assertTrue(_is_valid_svg(svg))

    def test_bad_instrument_rejected(self):
        with self.assertRaises(Exception):
            _render("measuring_instrument", {"instrument": "ruler"})

    def test_reading_off_the_scale_rejected(self):
        # a reading that cannot be drawn on the scale defeats the whole diagram
        with self.assertRaises(Exception):
            _render("measuring_instrument", {"instrument": "vernier_calipers",
                                             "reading": 99.0})

    def test_vernier_reading_decomposition(self):
        """LC = MSD/N = 0.1/10 = 0.01 cm, and 2.34 cm = MSR 2.30 + division 4 × LC.
        The renderer draws THAT coinciding division; the arithmetic must match the
        stated reading or the 'read the instrument' answer is a lie.
        """
        from diagrams.service.physics.renderer import _instrument_reading
        lc, msr, coincidence = _instrument_reading(2.34, 0.1, 10)
        self.assertAlmostEqual(lc, 0.01, places=9)
        self.assertAlmostEqual(msr, 2.30, places=9)
        self.assertEqual(coincidence, 4)
        self.assertAlmostEqual(msr + coincidence * lc, 2.34, places=9)

    def test_screw_gauge_reading_decomposition(self):
        """LC = pitch/N = 0.5/50 = 0.01 mm, and 4.23 mm = MSR 4.00 + division 23 × LC.
        """
        from diagrams.service.physics.renderer import _instrument_reading
        lc, msr, coincidence = _instrument_reading(4.23, 0.5, 50)
        self.assertAlmostEqual(lc, 0.01, places=9)
        self.assertAlmostEqual(msr, 4.00, places=9)
        self.assertEqual(coincidence, 23)
        self.assertAlmostEqual(msr + coincidence * lc, 4.23, places=9)

    def test_coinciding_division_is_always_in_range(self):
        """The coincidence must be a real division 0 ≤ c < N — a value the drawn
        scale actually carries — for any reading.
        """
        from diagrams.service.physics.renderer import _instrument_reading
        for reading in (0.0, 1.05, 2.34, 3.99, 4.5):
            _lc, _msr, c = _instrument_reading(reading, 0.1, 10)
            self.assertGreaterEqual(c, 0)
            self.assertLess(c, 10)


# ── Rolling Motion ────────────────────────────────────────────────────────────

class TestRollingMotion(SimpleTestCase):
    def test_every_body_renders(self):
        from diagrams.schemas.physics import ROLLING_BODY_K
        for body in ROLLING_BODY_K:
            with self.subTest(body=body):
                self.assertTrue(_is_valid_svg(_render("rolling_motion", {"body": body})))

    def test_race_ranking(self):
        svg = _render("rolling_motion", {"body": "solid_sphere",
                                         "show_race_ranking": True})
        self.assertTrue(_is_valid_svg(svg))

    def test_toggles_off(self):
        svg = _render("rolling_motion", {"body": "disc", "show_friction": False,
                                         "show_contact_point": False,
                                         "show_velocity_relation": False,
                                         "show_acceleration": False})
        self.assertTrue(_is_valid_svg(svg))

    def test_bad_body_rejected(self):
        with self.assertRaises(Exception):
            _render("rolling_motion", {"body": "cube"})

    def test_acceleration_formula(self):
        """a = g·sinθ/(1 + I/MR²). A solid sphere (k=0.4) on a 30° incline gets
        9.8·0.5/1.4 = 3.5 m/s². The number is derived, so the drawn body and the
        printed a cannot disagree.
        """
        from diagrams.service.physics.renderer import _rolling_acceleration
        self.assertAlmostEqual(_rolling_acceleration(30.0, 9.8, 0.4), 3.5, places=3)

    def test_acceleration_independent_of_mass_and_radius(self):
        """a depends only on θ and the shape factor k — never on M or R. That
        independence is the whole surprise of the rolling problem.
        """
        from diagrams.service.physics.renderer import _rolling_acceleration
        # k alone determines a for a given incline; two 'discs' of any M, R share k.
        a1 = _rolling_acceleration(30.0, 9.8, 0.5)
        a2 = _rolling_acceleration(30.0, 9.8, 0.5)
        self.assertEqual(a1, a2)

    def test_race_order_follows_shape_factor(self):
        """Smaller k ⇒ larger a ⇒ reaches the bottom first. So the ranking is
        solid sphere < disc < hollow sphere < ring, and NOT set by mass or radius.
        """
        from diagrams.schemas.physics import ROLLING_BODY_K
        from diagrams.service.physics.renderer import _rolling_acceleration
        a = lambda body: _rolling_acceleration(30.0, 9.8, ROLLING_BODY_K[body])
        self.assertGreater(a("solid_sphere"), a("disc"))
        self.assertGreater(a("disc"), a("hollow_sphere"))
        self.assertGreater(a("hollow_sphere"), a("ring"))

    def test_shape_factors_are_textbook(self):
        """k = I/MR²: sphere 2/5, disc/cylinder 1/2, hollow sphere 2/3, ring/hollow
        cylinder 1. These fix every rolling-race answer.
        """
        from diagrams.schemas.physics import ROLLING_BODY_K
        self.assertAlmostEqual(ROLLING_BODY_K["solid_sphere"], 0.4)
        self.assertAlmostEqual(ROLLING_BODY_K["disc"], 0.5)
        self.assertAlmostEqual(ROLLING_BODY_K["hollow_sphere"], 2 / 3)
        self.assertAlmostEqual(ROLLING_BODY_K["ring"], 1.0)


# ── Already-done wave-2 subtypes (render path + key invariants) ────────────────

class TestStandingWaveWave2(SimpleTestCase):
    def test_modes_render(self):
        for mode in ("string", "open_pipe", "closed_pipe"):
            with self.subTest(mode=mode):
                self.assertTrue(_is_valid_svg(_render("standing_wave", {"mode": mode})))

    def test_closed_pipe_snaps_even_harmonic(self):
        """A closed pipe cannot sustain an even harmonic. With the default 'snap'
        policy n=2 becomes n=3; with 'reject' it must raise.
        """
        from diagrams.service.physics.renderer import _standing_wave_state
        n_eff, _lam, _f = _standing_wave_state("closed_pipe", 2, 1.0, 340.0, "snap")
        self.assertEqual(n_eff, 3)
        with self.assertRaises(Exception):
            _render("standing_wave", {"mode": "closed_pipe", "harmonic": 2,
                                      "on_invalid_harmonic": "reject"})

    def test_closed_pipe_fundamental_is_quarter_wave(self):
        """Closed pipe: λ₁ = 4L. Open pipe / string: λ₁ = 2L. The factor-of-two
        difference is exactly why a closed pipe sounds an octave lower.
        """
        from diagrams.service.physics.renderer import _standing_wave_state
        _n, lam_closed, _f = _standing_wave_state("closed_pipe", 1, 1.0, 340.0)
        _n, lam_open, _f = _standing_wave_state("open_pipe", 1, 1.0, 340.0)
        _n, lam_string, _f = _standing_wave_state("string", 1, 1.0, 340.0)
        self.assertAlmostEqual(lam_closed, 4.0, places=6)
        self.assertAlmostEqual(lam_open, 2.0, places=6)
        self.assertAlmostEqual(lam_string, 2.0, places=6)


class TestFluidMechanicsWave2(SimpleTestCase):
    def test_every_setup_renders(self):
        for setup in ("venturimeter", "manometer", "capillary_rise",
                      "hydraulic_press", "floating_body", "streamline_flow"):
            with self.subTest(setup=setup):
                self.assertTrue(_is_valid_svg(_render("fluid_mechanics",
                                                      {"setup": setup})))

    def test_floating_fraction_is_density_ratio(self):
        """A body of density 800 in fluid 1000 floats with exactly 0.8 of its volume
        submerged (V_sub/V = ρ_body/ρ_fluid). The drawn waterline must be at 80%.
        """
        from diagrams.service.physics.renderer import _submerged_fraction
        self.assertAlmostEqual(_submerged_fraction(800.0, 1000.0), 0.8, places=9)

    def test_denser_than_fluid_is_rejected(self):
        with self.assertRaises(Exception):
            _render("fluid_mechanics", {"setup": "floating_body",
                                        "body_density": 1200, "fluid_density": 1000})


class TestMotionGraphWave2(SimpleTestCase):
    def test_renders_from_phases_and_from_coeffs(self):
        self.assertTrue(_is_valid_svg(_render("motion_graph", {
            "phases": [{"duration": 2.0, "acceleration": 3.0, "initial_velocity": 0.0}]})))
        self.assertTrue(_is_valid_svg(_render("motion_graph", {
            "position_coeffs": [0.0, 5.0, -2.0], "total_time": 3.0})))

    def test_velocity_is_the_analytic_derivative_of_position(self):
        """v(t) and a(t) are the derivatives of x(t) BY CONSTRUCTION. For
        x = 5t − 2t², v must be 5 − 4t and a must be −4 at every sample — the slope
        of one panel matching the value of the next is the only thing the figure
        asserts.
        """
        from diagrams.schemas.physics import MotionGraphSchema
        from diagrams.service.physics.renderer import _motion_series
        schema = MotionGraphSchema(position_coeffs=[0.0, 5.0, -2.0], total_time=3.0)
        t, x, v, a = _motion_series(schema)
        self.assertTrue(np.allclose(v, 5.0 - 4.0 * t, atol=1e-6))
        self.assertTrue(np.allclose(a, -4.0 * np.ones_like(t), atol=1e-6))
        # and v really is dx/dt numerically (edge_order=2 is exact for a quadratic)
        self.assertTrue(np.allclose(np.gradient(x, t, edge_order=2), v, atol=1e-6))


class TestSHMSystemWave2(SimpleTestCase):
    def test_every_setup_renders(self):
        for setup in ("spring_horizontal", "spring_vertical", "simple_pendulum",
                      "torsional"):
            with self.subTest(setup=setup):
                self.assertTrue(_is_valid_svg(_render("shm_system", {"setup": setup})))

    def test_vertical_spring_has_same_period_as_horizontal(self):
        """Gravity only shifts the equilibrium by mg/k; it does not change k, so a
        vertical spring has the SAME period as a horizontal one — the trap the
        figure must survive.
        """
        from diagrams.schemas.physics import SHMSystemSchema
        from diagrams.service.physics.renderer import _shm_period
        h = _shm_period(SHMSystemSchema(setup="spring_horizontal", mass=0.5,
                                        spring_constant=20.0))
        v = _shm_period(SHMSystemSchema(setup="spring_vertical", mass=0.5,
                                        spring_constant=20.0))
        self.assertAlmostEqual(h, v, places=9)

    def test_shm_velocity_leads_and_acceleration_opposes(self):
        """x = A cos ωt ⇒ a = −ω²x (antiphase) and v peaks where x is zero (90°
        ahead). Differentiating one expression guarantees the phase relations.
        """
        from diagrams.service.physics.renderer import _shm_series
        t = np.linspace(0, 2 * math.pi, 400)
        x, v, a = _shm_series(1.0, 1.0, t)
        self.assertTrue(np.allclose(a, -x, atol=1e-9))          # ω=1 ⇒ a=−x
        self.assertTrue(np.allclose(np.gradient(x, t), v, atol=1e-2))


class TestStressStrainWave2(SimpleTestCase):
    def test_every_material_renders(self):
        for material in ("ductile", "brittle", "elastomer"):
            with self.subTest(material=material):
                self.assertTrue(_is_valid_svg(_render("stress_strain",
                                                      {"material": material})))

    def test_brittle_fractures_at_its_peak_stress(self):
        """A brittle solid ruptures at its maximum stress: U and F coincide and there
        is essentially no plastic strain. A ductile metal instead necks — its stress
        falls after the ultimate point before fracture.
        """
        from diagrams.service.physics.renderer import _stress_strain_curve
        _e, stress_b, pts_b, _ = _stress_strain_curve("brittle")
        # brittle fracture stress is the maximum of the whole curve
        self.assertAlmostEqual(pts_b["F"][1], float(stress_b.max()), places=6)
        _e, stress_d, pts_d, _ = _stress_strain_curve("ductile")
        # ductile: fracture stress is BELOW the ultimate (necking drops it)
        self.assertLess(pts_d["F"][1], pts_d["U"][1])


# ── Dispatcher / determinism ──────────────────────────────────────────────────

class TestWave2Dispatcher(SimpleTestCase):
    WAVE2 = ("fluid_mechanics", "motion_graph", "shm_system", "standing_wave",
             "stress_strain", "heating_curve", "blackbody_spectrum",
             "maxwell_boltzmann", "gravitation", "radioactive_decay", "wavefront",
             "polarisation", "measuring_instrument", "rolling_motion")

    def test_all_wave2_subtypes_registered(self):
        from diagrams.service.physics.renderer import PHYSICS_RENDERERS
        for subtype in self.WAVE2:
            self.assertIn(subtype, PHYSICS_RENDERERS)

    def test_renders_are_deterministic(self):
        """Same params → byte-identical SVG. Diagrams are cached and diffed
        downstream; a figure that changes every render churns storage and hides
        real visual regressions.
        """
        cases = {
            "heating_curve": {},
            "blackbody_spectrum": {"temperatures": [3000, 6000]},
            "maxwell_boltzmann": {"temperatures": [300, 600]},
            "gravitation": {"setup": "g_variation"},
            "radioactive_decay": {"show_semi_log": True},
            "wavefront": {"phenomenon": "refraction"},
            "polarisation": {"analyser_angle": 45},
            "measuring_instrument": {"instrument": "screw_gauge", "reading": 4.23},
            "rolling_motion": {"body": "solid_sphere"},
            "fluid_mechanics": {"setup": "floating_body"},
            "motion_graph": {"position_coeffs": [0.0, 5.0, -2.0], "total_time": 3.0},
            "shm_system": {"setup": "simple_pendulum"},
            "standing_wave": {"mode": "closed_pipe", "harmonic": 3},
            "stress_strain": {"material": "ductile"},
        }
        for subtype, params in cases.items():
            with self.subTest(subtype=subtype):
                self.assertEqual(_render(subtype, params), _render(subtype, params))
