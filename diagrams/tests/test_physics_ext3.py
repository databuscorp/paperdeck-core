"""
Unit tests for WAVE-3 of the physics renderer extension: the twenty subtypes that
close the half-covered optics gaps and add atomic, thermal, EM, oscillation and
solid-state figures.

Two kinds of test, as in test_physics_ext2.py:

  * render tests — every subtype and every enum value produces valid SVG.
  * invariant tests — the physics the diagram *asserts* is checked against the
    values the renderer COMPUTES (not the SVG bytes). A concave lens can render
    perfectly and still be drawn converging; a prism can split light with violet
    on the wrong side; a fridge can quote a COP above the Carnot limit. Those are
    the regressions worth catching, so each test's docstring says what breaks if
    it fails.

SimpleTestCase: none of this touches the database. Run with unittest directly;
do NOT invoke manage.py test.
"""
import math

import numpy as np
from django.test import SimpleTestCase


def _is_valid_svg(content: str) -> bool:
    return bool(content and "<svg" in content and "</svg>" in content)


def _render(subtype, params):
    from diagrams.service.physics.renderer import render_physics
    return render_physics(subtype, params)


_BANNED_GLYPHS = ["→", "⇒", "∝", "⟂", "⇌"]  # -> => prop perp harpoon


# ── Optics: Concave (diverging) lens ──────────────────────────────────────────

class TestConcaveLens(SimpleTestCase):
    def test_renders(self):
        self.assertTrue(_is_valid_svg(_render("optics_concave_lens", {})))

    def test_toggles(self):
        svg = _render("optics_concave_lens",
                      {"show_rays": False, "show_image": False,
                       "show_focal_points": False})
        self.assertTrue(_is_valid_svg(svg))

    def test_positive_focal_length_rejected(self):
        """A concave lens is diverging: f must be negative. A positive f would draw
        a converging lens under a diverging label."""
        with self.assertRaises(Exception):
            _render("optics_concave_lens", {"focal_length": 100.0})

    def test_forms_virtual_erect_diminished_image(self):
        """1/v − 1/u = 1/f with f<0 and a real object (u<0) must give a VIRTUAL
        (v<0, same side as object), ERECT (m>0) and DIMINISHED (|m|<1) image — the
        defining behaviour of a diverging lens for every real object. If any of
        these flips, the figure teaches the opposite of the physics."""
        from diagrams.service.physics.renderer import _thin_lens_image
        for f, u in ((-120.0, -200.0), (-90.0, -50.0), (-300.0, -600.0)):
            v, m = _thin_lens_image(f, u)
            self.assertLess(v, 0.0)              # virtual, same side
            self.assertGreater(m, 0.0)           # erect
            self.assertLess(m, 1.0)              # diminished
            # image is nearer the lens than the object
            self.assertLess(abs(v), abs(u))


# ── Optics: Convex (diverging) mirror ─────────────────────────────────────────

class TestConvexMirror(SimpleTestCase):
    def test_renders(self):
        self.assertTrue(_is_valid_svg(_render("optics_convex_mirror", {})))

    def test_forms_virtual_erect_diminished_image_behind(self):
        """Mirror eq 1/v + 1/u = 1/f with a convex mirror (f>0) and real object
        (u<0) must give v>0 (behind the mirror ⇒ virtual), m>0 (erect), |m|<1
        (diminished). A convex mirror can do nothing else — that is why it is used
        as a car wing mirror."""
        from diagrams.service.physics.renderer import _spherical_mirror_image
        for f, u in ((120.0, -220.0), (100.0, -50.0), (200.0, -1000.0)):
            v, m = _spherical_mirror_image(f, u)
            self.assertGreater(v, 0.0)           # behind the mirror, virtual
            self.assertGreater(m, 0.0)           # erect
            self.assertLess(m, 1.0)              # diminished
            self.assertLess(abs(v), abs(u))      # image between pole and focus


# ── Optical instruments ───────────────────────────────────────────────────────

class TestOpticalInstrument(SimpleTestCase):
    def test_every_instrument_renders(self):
        for inst, extra in (("compound_microscope", {}),
                            ("simple_microscope", {}),
                            ("astronomical_telescope",
                             {"objective_focal_length": 100, "eyepiece_focal_length": 5}),
                            ("terrestrial_telescope",
                             {"objective_focal_length": 80, "eyepiece_focal_length": 4})):
            with self.subTest(instrument=inst):
                self.assertTrue(_is_valid_svg(
                    _render("optical_instrument", {"instrument": inst, **extra})))

    def test_bad_instrument_rejected(self):
        with self.assertRaises(Exception):
            _render("optical_instrument", {"instrument": "kaleidoscope"})

    def test_magnifying_powers_are_textbook(self):
        """Microscope M=(L/f_o)(D/f_e), telescope M=f_o/f_e, simple magnifier
        M=1+D/f_e. These printed numbers are the answer to the question, so they
        are computed, never trusted from the caller."""
        from diagrams.service.physics.renderer import (
            _compound_microscope_M, _telescope_M, _simple_microscope_M)
        self.assertAlmostEqual(_compound_microscope_M(16.0, 1.5, 25.0, 5.0),
                               (16.0 / 1.5) * (25.0 / 5.0), places=6)
        self.assertAlmostEqual(_telescope_M(100.0, 5.0), 20.0, places=6)
        self.assertAlmostEqual(_simple_microscope_M(25.0, 5.0), 6.0, places=6)


# ── Prism dispersion ──────────────────────────────────────────────────────────

class TestPrismDispersion(SimpleTestCase):
    def test_renders(self):
        self.assertTrue(_is_valid_svg(_render("prism_dispersion", {"show_angles": True})))

    def test_spectrum_toggle(self):
        self.assertTrue(_is_valid_svg(
            _render("prism_dispersion", {"show_spectrum": False})))

    def test_violet_below_red_index_rejected(self):
        with self.assertRaises(Exception):
            _render("prism_dispersion", {"n_red": 1.53, "n_violet": 1.50})

    def test_violet_deviates_more_than_red(self):
        """Normal dispersion: n_violet > n_red ⇒ δ_violet > δ_red. If this inverts,
        the emergent spectrum is drawn upside-down (red at the bottom)."""
        from diagrams.service.physics.renderer import _prism_deviation
        dev_red, _ = _prism_deviation(60.0, 50.0, 1.513)
        dev_violet, _ = _prism_deviation(60.0, 50.0, 1.532)
        self.assertGreater(dev_violet, dev_red)


# ── Energy level diagram ──────────────────────────────────────────────────────

class TestEnergyLevelDiagram(SimpleTestCase):
    def test_renders_with_series(self):
        self.assertTrue(_is_valid_svg(_render(
            "energy_level_diagram", {"show_series": ["lyman", "balmer", "paschen"]})))

    def test_renders_with_transitions(self):
        self.assertTrue(_is_valid_svg(_render("energy_level_diagram", {
            "transitions": [{"from_n": 3, "to_n": 2}, {"from_n": 4, "to_n": 1}]})))

    def test_bad_series_rejected(self):
        with self.assertRaises(Exception):
            _render("energy_level_diagram", {"show_series": ["balmer", "humphreys"]})

    def test_hydrogen_levels_are_minus_13_6_over_n_squared(self):
        """E_n = −13.6/n²: E₁=−13.6, E₂=−3.4, E₃≈−1.51 eV. These fix the whole
        diagram and every transition energy."""
        from diagrams.service.physics.renderer import _h_energy_level
        self.assertAlmostEqual(_h_energy_level(1), -13.6, delta=0.02)
        self.assertAlmostEqual(_h_energy_level(2), -3.4, delta=0.01)
        self.assertAlmostEqual(_h_energy_level(3), -1.511, delta=0.01)

    def test_balmer_alpha_is_656_nm(self):
        """The Balmer-α line (n=3→2) is the red 656 nm line every student measures.
        A wrong constant would move it out of the visible."""
        from diagrams.service.physics.renderer import _transition_wavelength_nm
        self.assertAlmostEqual(_transition_wavelength_nm(3, 2), 656.3, delta=1.5)

    def test_lyman_series_lands_on_n1_and_is_ultraviolet(self):
        """Every Lyman transition ends on n=1 and lies in the UV (< 122 nm); the
        Lyman limit (∞→1) is 91.2 nm. Landing Lyman on the wrong level is the
        classic series mix-up."""
        from diagrams.schemas.physics import _SERIES_LANDING
        from diagrams.service.physics.renderer import _transition_wavelength_nm
        self.assertEqual(_SERIES_LANDING["lyman"], 1)
        for hi in (2, 3, 4, 5):
            self.assertLess(_transition_wavelength_nm(hi, 1), 122.0)

    def test_series_landing_levels(self):
        """Lyman→1, Balmer→2, Paschen→3, Brackett→4, Pfund→5."""
        from diagrams.schemas.physics import _SERIES_LANDING
        self.assertEqual(
            [_SERIES_LANDING[s] for s in ("lyman", "balmer", "paschen", "brackett", "pfund")],
            [1, 2, 3, 4, 5])


# ── Rutherford alpha scattering ───────────────────────────────────────────────

class TestAlphaScattering(SimpleTestCase):
    def test_renders(self):
        self.assertTrue(_is_valid_svg(_render("alpha_scattering", {})))

    def test_toggles(self):
        self.assertTrue(_is_valid_svg(_render(
            "alpha_scattering", {"show_nucleus": False, "show_impact_parameter": False,
                                 "num_particles": 5})))

    def test_small_impact_parameter_scatters_more(self):
        """tan(θ/2)=k/b: a small impact parameter gives a LARGE scattering angle
        (near-180° backscatter), a large b a small one. This monotonic relation is
        the entire argument for a tiny dense nucleus."""
        from diagrams.service.physics.renderer import _rutherford_angle
        theta_close = _rutherford_angle(0.1, 0.45)
        theta_far = _rutherford_angle(3.0, 0.45)
        self.assertGreater(theta_close, theta_far)
        self.assertGreater(theta_close, 120.0)   # near backscatter
        self.assertLess(theta_far, 30.0)         # barely deflected

    def test_trajectory_focus_is_the_nucleus(self):
        """The hyperbola's incoming asymptote must sit at the impact parameter b
        from the nucleus (origin), so every path genuinely bends around the SAME
        nucleus rather than around thin air."""
        from diagrams.service.physics.renderer import _rutherford_trajectory
        px, py = _rutherford_trajectory(1.5, 0.45)
        self.assertAlmostEqual(abs(py[0]), 1.5, delta=0.05)


# ── Heat engine / refrigerator / heat pump ────────────────────────────────────

class TestHeatEngine(SimpleTestCase):
    def test_every_mode_renders(self):
        for mode in ("engine", "refrigerator", "heat_pump"):
            with self.subTest(mode=mode):
                self.assertTrue(_is_valid_svg(_render("heat_engine", {"mode": mode})))

    def test_bad_mode_rejected(self):
        with self.assertRaises(Exception):
            _render("heat_engine", {"mode": "perpetual"})

    def test_equal_temperatures_rejected(self):
        with self.assertRaises(Exception):
            _render("heat_engine", {"t_hot": 300, "t_cold": 300})

    def test_engine_efficiency_and_energy_conservation(self):
        """η = 1 − Q2/Q1 = W/Q1, and Q1 = W + Q2 EXACTLY. A figure with Q1 ≠ W+Q2
        would be drawing energy from nowhere."""
        from diagrams.service.physics.renderer import _heat_engine_energetics
        en = _heat_engine_energetics("engine", 1000.0, 600.0, None)
        self.assertAlmostEqual(en["work"], 400.0, places=6)
        self.assertAlmostEqual(en["q_hot"], en["work"] + en["q_cold"], places=6)
        self.assertAlmostEqual(en["metric_value"], 1.0 - 600.0 / 1000.0, places=6)

    def test_fridge_cop_and_conservation(self):
        """Refrigerator COP = Q2/W, with Q1 = W + Q2. The default fridge must be a
        POSSIBLE machine: its COP stays below the Carnot COP T2/(T1−T2)."""
        from diagrams.service.physics.renderer import _heat_engine_energetics
        en = _heat_engine_energetics("refrigerator", None, None, 250.0)
        self.assertAlmostEqual(en["q_hot"], en["work"] + en["q_cold"], places=6)
        self.assertAlmostEqual(en["metric_value"], en["q_cold"] / en["work"], places=6)
        carnot = 300.0 / (500.0 - 300.0)         # default temps
        self.assertLessEqual(en["metric_value"], carnot)

    def test_heat_pump_cop_is_one_more_than_fridge(self):
        """Heat pump COP = Q1/W = 1 + Q2/W. For the same W and Q2 it is exactly the
        fridge COP plus one."""
        from diagrams.service.physics.renderer import _heat_engine_energetics
        pump = _heat_engine_energetics("heat_pump", None, 300.0, 250.0)
        self.assertAlmostEqual(pump["metric_value"], pump["q_hot"] / pump["work"], places=6)
        self.assertAlmostEqual(pump["metric_value"], 300.0 / 250.0 + 1.0, places=6)


# ── Thermal conduction ────────────────────────────────────────────────────────

class TestThermalConduction(SimpleTestCase):
    def test_every_arrangement_renders(self):
        for arr in ("series", "parallel", "single"):
            with self.subTest(arrangement=arr):
                self.assertTrue(_is_valid_svg(
                    _render("thermal_conduction", {"arrangement": arr})))

    def test_reversed_temperatures_rejected(self):
        with self.assertRaises(Exception):
            _render("thermal_conduction", {"t_hot": 0.0, "t_cold": 100.0})

    def test_series_interface_temperature_from_equal_heat_current(self):
        """In series the SAME H flows through every slab, so the drop across each is
        H·Rᵢ. For the default two-slab wall (k=50,L=0.1 then k=10,L=0.2, A=1) the
        interface sits at ≈90.9 °C, and the ends are exactly the boundary temps."""
        from diagrams.schemas.physics import ConductionLayer
        from diagrams.service.physics.renderer import _series_interface_temps
        layers = [ConductionLayer(length=0.1, thermal_conductivity=50.0, area=1.0),
                  ConductionLayer(length=0.2, thermal_conductivity=10.0, area=1.0)]
        H, temps, R = _series_interface_temps(layers, 100.0, 0.0)
        self.assertAlmostEqual(temps[0], 100.0, places=6)
        self.assertAlmostEqual(temps[-1], 0.0, places=6)
        self.assertAlmostEqual(temps[1], 90.909, delta=0.05)
        # equal H means the drop across each slab is H·R
        self.assertAlmostEqual(temps[0] - temps[1], H * R[0], places=6)
        self.assertAlmostEqual(temps[1] - temps[2], H * R[1], places=6)


# ── Gauss surface ─────────────────────────────────────────────────────────────

class TestGaussSurface(SimpleTestCase):
    def test_every_charge_type_renders(self):
        for ct in ("point", "line", "plane", "shell"):
            with self.subTest(charge_type=ct):
                self.assertTrue(_is_valid_svg(
                    _render("gauss_surface", {"charge_type": ct})))

    def test_surface_variants_render(self):
        for sf in ("sphere", "cylinder", "pillbox"):
            with self.subTest(surface=sf):
                self.assertTrue(_is_valid_svg(
                    _render("gauss_surface", {"surface": sf})))

    def test_bad_charge_type_rejected(self):
        with self.assertRaises(Exception):
            _render("gauss_surface", {"charge_type": "quadrupole"})


# ── Equipotential ─────────────────────────────────────────────────────────────

class TestEquipotential(SimpleTestCase):
    def test_every_configuration_renders(self):
        for cfg in ("point_charge", "dipole", "parallel_plates", "two_like_charges"):
            with self.subTest(configuration=cfg):
                self.assertTrue(_is_valid_svg(
                    _render("equipotential", {"configuration": cfg})))

    def test_bad_configuration_rejected(self):
        with self.assertRaises(Exception):
            _render("equipotential", {"configuration": "octupole"})

    def test_field_is_perpendicular_to_equipotentials(self):
        """E = −∇V, so the field (∝ ∇V) is parallel to the potential gradient and
        therefore PERPENDICULAR to the equipotential (a level curve, tangent ⟂ to
        ∇V). Sampling the numeric field and the numeric gradient of V and taking
        their cross product must give ~0 everywhere — the right angle the figure is
        built to show."""
        from diagrams.service.physics.renderer import _potential_field
        xs = np.linspace(-3, 3, 200)
        ys = np.linspace(-2.4, 2.4, 200)
        X, Y = np.meshgrid(xs, ys)
        V, Ex, Ey, _ = _potential_field("dipole", X, Y)
        gy, gx = np.gradient(V, ys, xs)          # ∇V
        # unit field and unit gradient; |E × ∇V| ≈ 0 where both are well-defined
        mag_e = np.hypot(Ex, Ey)
        mag_g = np.hypot(gx, gy)
        good = (mag_e > 1e-3) & (mag_g > 1e-3)
        cross = np.abs(Ex * gy - Ey * gx) / (mag_e * mag_g + 1e-12)
        # E ∝ −∇V so the sine of the angle between them is ~0
        self.assertLess(float(np.nanmedian(cross[good])), 0.02)


# ── Cyclotron ─────────────────────────────────────────────────────────────────

class TestCyclotron(SimpleTestCase):
    def test_renders(self):
        self.assertTrue(_is_valid_svg(_render("cyclotron", {})))

    def test_toggles(self):
        self.assertTrue(_is_valid_svg(_render(
            "cyclotron", {"show_spiral": False, "show_dees": False,
                          "show_magnetic_field": False})))

    def test_spiral_radius_grows(self):
        """The particle gains energy at every gap crossing, so successive half-turns
        have GROWING radii (r ∝ √k). A spiral of constant radius would deny the
        acceleration that is the whole point of the machine."""
        from diagrams.service.physics.renderer import _cyclotron_spiral
        pts = _cyclotron_spiral(8, r0=0.5)
        # radius from the centre at the bulge of the first vs the last arc
        r_first = np.max(np.abs(pts[:40, 0]))
        r_last = np.max(np.abs(pts[-40:, 0]))
        self.assertGreater(r_last, r_first)


# ── Velocity selector / mass spectrometer ─────────────────────────────────────

class TestVelocitySelector(SimpleTestCase):
    def test_both_modes_render(self):
        for mode in ("velocity_selector", "mass_spectrometer"):
            with self.subTest(mode=mode):
                self.assertTrue(_is_valid_svg(
                    _render("velocity_selector", {"mode": mode})))

    def test_bad_mode_rejected(self):
        with self.assertRaises(Exception):
            _render("velocity_selector", {"mode": "cyclotron"})

    def test_selected_velocity_is_E_over_B(self):
        """Only charges with v = E/B pass undeflected: qE and qvB cancel there,
        independent of charge and mass. E=1e5 V/m, B=0.2 T ⇒ v=5e5 m/s."""
        from diagrams.service.physics.renderer import _velocity_selector_v
        self.assertAlmostEqual(_velocity_selector_v(1.0e5, 0.2), 5.0e5, places=3)

    def test_analyser_radius_grows_with_mass(self):
        """In the analyser r = mv/(qB): a heavier ion swings on a WIDER semicircle.
        This mass-to-radius map is how the spectrometer separates isotopes."""
        from diagrams.service.physics.renderer import _spectrometer_radius
        r_light = _spectrometer_radius(1.0e-26, 5.0e5, 1.6e-19, 0.2)
        r_heavy = _spectrometer_radius(2.0e-26, 5.0e5, 1.6e-19, 0.2)
        self.assertAlmostEqual(r_heavy / r_light, 2.0, places=6)


# ── X-ray spectrum ────────────────────────────────────────────────────────────

class TestXraySpectrum(SimpleTestCase):
    def test_renders(self):
        self.assertTrue(_is_valid_svg(_render("xray_spectrum", {})))

    def test_low_voltage_target_renders(self):
        self.assertTrue(_is_valid_svg(_render(
            "xray_spectrum", {"target_element": "Mo", "target_z": 42,
                              "tube_voltage": 30})))

    def test_duane_hunt_cutoff(self):
        """The short-wavelength cutoff λ_min = hc/(eV) depends ONLY on the tube
        voltage, not the target: 1239.84/V(kV) pm. At 50 kV, λ_min ≈ 24.8 pm; the
        cutoff halves when the voltage doubles."""
        from diagrams.service.physics.renderer import _xray_lambda_min_pm
        self.assertAlmostEqual(_xray_lambda_min_pm(50.0), 24.8, delta=0.1)
        self.assertAlmostEqual(_xray_lambda_min_pm(100.0),
                               _xray_lambda_min_pm(50.0) / 2.0, places=4)

    def test_k_beta_is_shorter_wavelength_than_k_alpha(self):
        """Kβ (n=3→1) is a bigger energy jump than Kα (n=2→1), so it sits at a
        SHORTER wavelength. Swapping them mislabels the characteristic lines."""
        from diagrams.service.physics.renderer import _moseley_k_pm
        self.assertLess(_moseley_k_pm(74, "beta"), _moseley_k_pm(74, "alpha"))


# ── Beats ─────────────────────────────────────────────────────────────────────

class TestBeats(SimpleTestCase):
    def test_renders(self):
        self.assertTrue(_is_valid_svg(_render("beats", {})))

    def test_beat_frequency_is_difference(self):
        """The beat frequency is |f₁ − f₂| — the number of loudness swells per
        second. The envelope drawn in the figure has exactly this period, so an
        error here draws the wrong number of beats."""
        from diagrams.service.physics.renderer import _beat_frequency
        self.assertAlmostEqual(_beat_frequency(256.0, 260.0), 4.0, places=6)
        self.assertAlmostEqual(_beat_frequency(10.0, 12.0), 2.0, places=6)
        self.assertEqual(_beat_frequency(300.0, 300.0), 0.0)


# ── Damped / forced oscillation ───────────────────────────────────────────────

class TestDampedOscillation(SimpleTestCase):
    def test_every_damping_type_renders(self):
        for dt in ("under", "critical", "over"):
            with self.subTest(damping_type=dt):
                self.assertTrue(_is_valid_svg(
                    _render("damped_oscillation", {"damping_type": dt})))

    def test_forced_mode_renders(self):
        self.assertTrue(_is_valid_svg(
            _render("damped_oscillation", {"mode": "forced_resonance"})))

    def test_bad_mode_rejected(self):
        with self.assertRaises(Exception):
            _render("damped_oscillation", {"mode": "driven"})

    def test_bad_damping_type_rejected(self):
        with self.assertRaises(Exception):
            _render("damped_oscillation", {"damping_type": "slightly"})


# ── Collision ─────────────────────────────────────────────────────────────────

class TestCollision(SimpleTestCase):
    def test_every_type_renders(self):
        for ct in ("elastic", "perfectly_inelastic", "oblique"):
            with self.subTest(collision_type=ct):
                self.assertTrue(_is_valid_svg(
                    _render("collision", {"collision_type": ct})))

    def test_bad_type_rejected(self):
        with self.assertRaises(Exception):
            _render("collision", {"collision_type": "superelastic"})

    def test_elastic_conserves_momentum_and_kinetic_energy(self):
        """A 1-D elastic collision conserves BOTH momentum and KE. For m1=2,u1=4
        into m2=1 at rest: v1=4/3, v2=16/3. Both invariants must hold to the
        computed velocities, or the 'elastic' label is a lie."""
        from diagrams.service.physics.renderer import _elastic_1d
        m1, m2, u1, u2 = 2.0, 1.0, 4.0, 0.0
        v1, v2 = _elastic_1d(m1, m2, u1, u2)
        self.assertAlmostEqual(v1, 4.0 / 3.0, places=6)
        self.assertAlmostEqual(v2, 16.0 / 3.0, places=6)
        self.assertAlmostEqual(m1 * u1 + m2 * u2, m1 * v1 + m2 * v2, places=6)
        self.assertAlmostEqual(m1 * u1 ** 2 + m2 * u2 ** 2,
                               m1 * v1 ** 2 + m2 * v2 ** 2, places=6)

    def test_inelastic_conserves_momentum_only_and_loses_KE(self):
        """Perfectly inelastic: bodies stick at the centre-of-mass velocity;
        momentum is conserved but KE drops. Conserving KE here would be the classic
        mistake."""
        from diagrams.service.physics.renderer import _inelastic
        m1, m2, u1, u2 = 2.0, 1.0, 4.0, 0.0
        v = _inelastic(m1, m2, u1, u2)
        self.assertAlmostEqual(v, 8.0 / 3.0, places=6)
        self.assertAlmostEqual(m1 * u1 + m2 * u2, (m1 + m2) * v, places=6)
        ke_before = 0.5 * m1 * u1 ** 2
        ke_after = 0.5 * (m1 + m2) * v ** 2
        self.assertLess(ke_after, ke_before)


# ── Banked road ───────────────────────────────────────────────────────────────

class TestBankedRoad(SimpleTestCase):
    def test_renders(self):
        self.assertTrue(_is_valid_svg(_render("banked_road", {})))

    def test_with_friction(self):
        self.assertTrue(_is_valid_svg(
            _render("banked_road", {"friction_coefficient": 0.3})))

    def test_ideal_speed_is_sqrt_rg_tan_theta(self):
        """The frictionless ideal speed is v = √(r·g·tanθ): at this speed the
        horizontal component of the normal force alone supplies the centripetal
        force. r=100, g=9.8, θ=30° ⇒ v≈23.8 m/s. A wrong formula makes every banked
        curve problem wrong."""
        from diagrams.service.physics.renderer import _banked_speed
        v = _banked_speed(100.0, 9.8, 30.0)
        self.assertAlmostEqual(v, math.sqrt(100.0 * 9.8 * math.tan(math.radians(30.0))),
                               places=6)
        self.assertAlmostEqual(v, 23.77, delta=0.1)


# ── Electromagnetic induction ─────────────────────────────────────────────────

class TestEMInduction(SimpleTestCase):
    def test_every_phenomenon_renders(self):
        for ph in ("lenz_law", "motional_emf", "eddy_currents", "flux_change"):
            with self.subTest(phenomenon=ph):
                self.assertTrue(_is_valid_svg(
                    _render("em_induction", {"phenomenon": ph})))

    def test_bad_phenomenon_rejected(self):
        with self.assertRaises(Exception):
            _render("em_induction", {"phenomenon": "self_inductance"})


# ── Nuclear reactor ───────────────────────────────────────────────────────────

class TestNuclearReactor(SimpleTestCase):
    def test_renders(self):
        self.assertTrue(_is_valid_svg(_render("nuclear_reactor", {})))

    def test_toggles(self):
        self.assertTrue(_is_valid_svg(
            _render("nuclear_reactor", {"show_labels": False, "show_turbine": False})))


# ── Band theory ───────────────────────────────────────────────────────────────

class TestBandTheory(SimpleTestCase):
    def test_every_material_renders(self):
        for mat in ("conductor", "semiconductor", "insulator", "n_type", "p_type"):
            with self.subTest(material=mat):
                self.assertTrue(_is_valid_svg(
                    _render("band_theory", {"material": mat})))

    def test_bad_material_rejected(self):
        with self.assertRaises(Exception):
            _render("band_theory", {"material": "superconductor"})


# ── Cross-cutting: dispatcher, glyphs, determinism ────────────────────────────

class TestWave3Dispatcher(SimpleTestCase):
    WAVE3 = ("optics_concave_lens", "optics_convex_mirror", "optical_instrument",
             "prism_dispersion", "energy_level_diagram", "alpha_scattering",
             "heat_engine", "thermal_conduction", "gauss_surface", "equipotential",
             "cyclotron", "velocity_selector", "xray_spectrum", "beats",
             "damped_oscillation", "collision", "banked_road", "em_induction",
             "nuclear_reactor", "band_theory")

    def test_all_wave3_subtypes_registered(self):
        from diagrams.service.physics.renderer import PHYSICS_RENDERERS
        for subtype in self.WAVE3:
            self.assertIn(subtype, PHYSICS_RENDERERS)

    def test_pre_existing_subtypes_untouched(self):
        """The two optics gaps we complement must still be present — we appended,
        never replaced."""
        from diagrams.service.physics.renderer import PHYSICS_RENDERERS
        for subtype in ("optics_convex_lens", "optics_concave_mirror",
                        "ray_optics_prism", "bohr_atom", "annotated_xy_graph"):
            self.assertIn(subtype, PHYSICS_RENDERERS)

    def test_no_rendered_svg_contains_a_raw_arrow_or_relation_glyph(self):
        """cairosvg (the print rasteriser) renders → ⇒ ∝ ⟂ ⇌ as tofu boxes — a
        confirmed shipping bug. No text node in any WAVE-3 figure may contain one,
        including the mathtext-heavy panels."""
        cases = {
            "optics_concave_lens": {}, "optics_convex_mirror": {},
            "optical_instrument": {"instrument": "compound_microscope"},
            "prism_dispersion": {"show_angles": True},
            "energy_level_diagram": {"show_series": ["lyman", "balmer", "paschen"]},
            "alpha_scattering": {}, "heat_engine": {"mode": "refrigerator"},
            "thermal_conduction": {"arrangement": "parallel"},
            "gauss_surface": {"charge_type": "line"},
            "equipotential": {"configuration": "parallel_plates"},
            "cyclotron": {}, "velocity_selector": {"mode": "mass_spectrometer"},
            "xray_spectrum": {}, "beats": {},
            "damped_oscillation": {"mode": "forced_resonance"},
            "collision": {"collision_type": "oblique"},
            "banked_road": {"friction_coefficient": 0.2},
            "em_induction": {"phenomenon": "motional_emf"},
            "nuclear_reactor": {}, "band_theory": {"material": "n_type"},
        }
        for subtype, params in cases.items():
            svg = _render(subtype, params)
            for g in _BANNED_GLYPHS:
                self.assertNotIn(g, svg,
                                 f"{subtype} emitted the banned glyph {g!r}")

    def test_renders_are_deterministic(self):
        """Same params → byte-identical SVG. Diagrams are cached and diffed
        downstream; a figure that changes each render churns storage and hides
        real regressions."""
        cases = {
            "optics_concave_lens": {}, "optics_convex_mirror": {},
            "optical_instrument": {"instrument": "astronomical_telescope",
                                   "objective_focal_length": 100,
                                   "eyepiece_focal_length": 5},
            "prism_dispersion": {}, "energy_level_diagram": {"show_series": ["balmer"]},
            "alpha_scattering": {"num_particles": 9},
            "heat_engine": {"mode": "heat_pump"},
            "thermal_conduction": {}, "gauss_surface": {"charge_type": "shell"},
            "equipotential": {"configuration": "dipole"}, "cyclotron": {},
            "velocity_selector": {"mode": "mass_spectrometer"}, "xray_spectrum": {},
            "beats": {}, "damped_oscillation": {"damping_type": "over"},
            "collision": {"collision_type": "elastic"},
            "banked_road": {}, "em_induction": {"phenomenon": "eddy_currents"},
            "nuclear_reactor": {}, "band_theory": {"material": "p_type"},
        }
        for subtype, params in cases.items():
            with self.subTest(subtype=subtype):
                self.assertEqual(_render(subtype, params), _render(subtype, params))
