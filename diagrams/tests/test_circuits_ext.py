"""
Unit tests for the extended circuit renderers: Wheatstone bridge family,
rectifiers, and series/parallel RLC.

These subtypes carry *derived* physics — a balance condition, an unknown
resistance, a resonant frequency, an output waveform. The derivation is what a
student is marked on, so the assertions here are on the computed values and on
the text that actually reaches the SVG, not on byte counts.
"""
import re

from django.test import SimpleTestCase

from diagrams.service.circuits.renderer import (
    render_circuits,
    _parse_quantity,
    metre_bridge_unknown,
    wheatstone_missing_arm,
    wheatstone_is_balanced,
    resonant_frequency,
    rectifier_waveform,
)
from diagrams.schemas.circuits import RectifierType


def _is_valid_svg(content: str) -> bool:
    """Basic SVG validity check."""
    return bool(content and "<svg" in content and "</svg>" in content)


def _svg_text(svg: str) -> str:
    """All text nodes of the SVG, joined.

    matplotlib/svgwrite happily emit text that never renders; asserting on the
    text nodes is the only way to know an annotation really shipped.
    """
    return " ".join(re.findall(r">([^<>]+)<", svg))


def _longest_zero_run(samples, tol=1e-9):
    best = run = 0
    for v in samples:
        run = run + 1 if abs(v) <= tol else 0
        best = max(best, run)
    return best


class TestWheatstoneBridgeHelpers(SimpleTestCase):
    def test_metre_bridge_unknown_from_balance_length(self):
        """X = R·l/(100 − l). If this drifts, every metre-bridge answer key is wrong."""
        self.assertAlmostEqual(metre_bridge_unknown(10.0, 40.0), 6.6666667, places=5)
        self.assertAlmostEqual(metre_bridge_unknown(10.0, 50.0), 10.0, places=6)
        self.assertAlmostEqual(metre_bridge_unknown(5.0, 75.0), 15.0, places=6)

    def test_metre_bridge_rejects_off_wire_balance_length(self):
        """A null point at or past 100 cm is not a measurement; it must not silently divide."""
        with self.assertRaises(ValueError):
            metre_bridge_unknown(10.0, 100.0)
        with self.assertRaises(ValueError):
            metre_bridge_unknown(10.0, 0.0)

    def test_wheatstone_missing_arm_solves_from_balance(self):
        """P/Q = R/S. A wrong rearrangement here prints a wrong resistance on the paper."""
        self.assertEqual(wheatstone_missing_arm([10.0, 20.0, 30.0, None]), (3, 60.0))
        self.assertEqual(wheatstone_missing_arm([None, 20.0, 30.0, 60.0]), (0, 10.0))
        self.assertEqual(wheatstone_missing_arm([10.0, None, 30.0, 60.0]), (1, 20.0))
        self.assertEqual(wheatstone_missing_arm([10.0, 20.0, None, 60.0]), (2, 30.0))

    def test_wheatstone_missing_arm_needs_exactly_one_unknown(self):
        """With 0 or 2+ unknowns the bridge is not solvable; returning a number would be a lie."""
        self.assertIsNone(wheatstone_missing_arm([10.0, 20.0, 30.0, 60.0]))
        self.assertIsNone(wheatstone_missing_arm([10.0, None, None, 60.0]))

    def test_wheatstone_balance_detection(self):
        """A balanced bridge reads zero on the galvanometer; an unbalanced one does not."""
        self.assertIs(wheatstone_is_balanced([10.0, 20.0, 15.0, 30.0]), True)
        self.assertIs(wheatstone_is_balanced([10.0, 20.0, 15.0, 31.0]), False)
        self.assertIsNone(wheatstone_is_balanced([10.0, 20.0, None, 30.0]))


class TestWheatstoneBridgeRenderer(SimpleTestCase):
    def _render(self, params):
        return render_circuits("wheatstone_bridge", params)

    def test_wheatstone_diamond(self):
        svg = self._render({"variant": "wheatstone",
                            "resistor_values": ["10Ω", "20Ω", "30Ω", "60Ω"],
                            "show_current_arrows": True})
        self.assertTrue(_is_valid_svg(svg))

    def test_wheatstone_annotates_balance_condition(self):
        """The condition P/Q = R/S is the question; if it vanishes the diagram is useless."""
        svg = self._render({"variant": "wheatstone",
                            "resistor_values": ["10Ω", "20Ω", "30Ω", "60Ω"]})
        self.assertIn("P/Q = R/S", _svg_text(svg))

    def test_wheatstone_solves_and_prints_the_unknown_arm(self):
        """S = QR/P = 20×30/10 = 60Ω must be computed, never taken from the params."""
        svg = self._render({"variant": "wheatstone",
                            "resistor_values": ["10Ω", "20Ω", "30Ω", None]})
        self.assertIn("60 Ω", _svg_text(svg))

    def test_metre_bridge(self):
        svg = self._render({"variant": "metre_bridge", "balance_length_cm": 40,
                            "known_resistance": "10Ω"})
        self.assertTrue(_is_valid_svg(svg))

    def test_metre_bridge_prints_computed_unknown(self):
        """R=10Ω balanced at 40cm ⇒ X = 6.67Ω. A wrong number here is a wrong answer key."""
        svg = self._render({"variant": "metre_bridge", "balance_length_cm": 40,
                            "known_resistance": "10Ω"})
        text = _svg_text(svg)
        self.assertIn("6.67 Ω", text)
        self.assertIn("l/(100 − l)", text)

    def test_metre_bridge_requires_known_resistance(self):
        """Without R in the right gap there is nothing to compare X against."""
        with self.assertRaises(ValueError):
            self._render({"variant": "metre_bridge", "balance_length_cm": 40})

    def test_metre_bridge_rejects_balance_length_off_the_wire(self):
        """A jockey at 120 cm on a 100 cm wire is physically impossible."""
        with self.assertRaises(ValueError):
            self._render({"variant": "metre_bridge", "balance_length_cm": 120,
                          "known_resistance": "10Ω"})

    def test_potentiometer_single_length(self):
        svg = self._render({"variant": "potentiometer", "balance_length_cm": 75})
        self.assertTrue(_is_valid_svg(svg))
        self.assertIn("E = k·l", _svg_text(svg))

    def test_potentiometer_compares_two_emfs(self):
        """Two null points compare EMFs: E1/E2 = l1/l2 = 40/60 = 0.667."""
        svg = self._render({"variant": "potentiometer", "balance_length_cm": 40,
                            "balance_length_2_cm": 60})
        text = _svg_text(svg)
        self.assertIn("E1/E2 = l1/l2", text)
        self.assertIn("0.667", text)

    def test_potentiometer_requires_a_balance_length(self):
        """No null point means no measurement was made."""
        with self.assertRaises(ValueError):
            self._render({"variant": "potentiometer"})


class TestRectifierWaveform(SimpleTestCase):
    def test_half_wave_output_is_zero_for_half_of_every_cycle(self):
        """A half-wave diode blocks the negative half-cycle: the output must sit flat at
        zero for ~half the trace. If it never reaches zero, the drawing is a full-wave."""
        _, _, v_out = rectifier_waveform(RectifierType.HALF_WAVE, cycles=2.0, n=480)
        zeros = sum(1 for v in v_out if abs(v) <= 1e-9)
        self.assertGreater(zeros / len(v_out), 0.45)
        self.assertLess(zeros / len(v_out), 0.55)
        # ...and the zeros are contiguous gaps, not scattered points
        self.assertGreater(_longest_zero_run(v_out), 100)

    def test_full_wave_output_is_non_negative_with_no_gaps(self):
        """Both full-wave topologies invert the negative half-cycle: every half-cycle
        produces a hump, so the output only touches zero at isolated crossings. A gap
        here means a half-wave trace was drawn under a full-wave circuit."""
        for rtype in (RectifierType.FULL_WAVE_CENTRE_TAP, RectifierType.FULL_WAVE_BRIDGE):
            _, _, v_out = rectifier_waveform(rtype, cycles=2.0, n=480)
            self.assertTrue(all(v >= 0.0 for v in v_out), rtype)
            self.assertLessEqual(_longest_zero_run(v_out), 2, rtype)
            self.assertAlmostEqual(max(v_out), 1.0, places=3)

    def test_full_wave_has_twice_the_humps_of_half_wave(self):
        """Ripple frequency is 2f for full-wave and f for half-wave — a stock exam question."""
        def peaks(v):
            return sum(1 for i in range(1, len(v) - 1)
                       if v[i] > v[i - 1] and v[i] >= v[i + 1] and v[i] > 0.5)
        _, _, half = rectifier_waveform(RectifierType.HALF_WAVE, cycles=2.0, n=480)
        _, _, full = rectifier_waveform(RectifierType.FULL_WAVE_BRIDGE, cycles=2.0, n=480)
        self.assertEqual(peaks(half), 2)
        self.assertEqual(peaks(full), 4)

    def test_filter_capacitor_smooths_and_never_collapses_to_zero(self):
        """With C across the load the output is a ripple that never falls back to zero —
        that is the entire point of the filter."""
        _, _, v_out = rectifier_waveform(RectifierType.FULL_WAVE_BRIDGE, cycles=2.0,
                                         n=480, filtered=True)
        settled = v_out[len(v_out) // 2:]
        self.assertGreater(min(settled), 0.5)
        self.assertLess(max(settled) - min(settled), 0.5)     # ripple, not a raw hump

    def test_half_wave_ripple_is_deeper_than_full_wave(self):
        """The capacitor discharges for a whole period in a half-wave rectifier but only
        half a period in a full-wave one, so half-wave ripple must be the larger."""
        def ripple(rtype):
            _, _, v = rectifier_waveform(rtype, cycles=3.0, n=720, filtered=True)
            tail = v[len(v) // 2:]
            return max(tail) - min(tail)
        self.assertGreater(ripple(RectifierType.HALF_WAVE),
                           ripple(RectifierType.FULL_WAVE_BRIDGE))

    def test_input_waveform_is_a_full_sine(self):
        """The input is AC: it must swing negative, whatever the rectifier does after it."""
        _, v_in, _ = rectifier_waveform(RectifierType.FULL_WAVE_BRIDGE, cycles=2.0, n=480)
        self.assertLess(min(v_in), -0.99)
        self.assertGreater(max(v_in), 0.99)


class TestRectifierRenderer(SimpleTestCase):
    def _render(self, params):
        return render_circuits("rectifier", params)

    def test_half_wave(self):
        svg = self._render({"rectifier_type": "half_wave"})
        self.assertTrue(_is_valid_svg(svg))

    def test_full_wave_centre_tap(self):
        svg = self._render({"rectifier_type": "full_wave_centre_tap"})
        self.assertTrue(_is_valid_svg(svg))
        self.assertIn("centre tap", _svg_text(svg))

    def test_full_wave_bridge(self):
        svg = self._render({"rectifier_type": "full_wave_bridge"})
        self.assertTrue(_is_valid_svg(svg))

    def test_bridge_draws_all_four_diodes(self):
        """A bridge rectifier with fewer than four diodes is not a bridge rectifier."""
        text = _svg_text(self._render({"rectifier_type": "full_wave_bridge"}))
        for d in ("D1", "D2", "D3", "D4"):
            self.assertIn(d, text)

    def test_centre_tap_draws_two_diodes(self):
        text = _svg_text(self._render({"rectifier_type": "full_wave_centre_tap"}))
        self.assertIn("D1", text)
        self.assertIn("D2", text)
        self.assertNotIn("D3", text)

    def test_every_type_renders_with_and_without_the_filter_capacitor(self):
        for rtype in ("half_wave", "full_wave_centre_tap", "full_wave_bridge"):
            for filt in (False, True):
                svg = self._render({"rectifier_type": rtype,
                                    "show_filter_capacitor": filt})
                self.assertTrue(_is_valid_svg(svg), f"{rtype} filter={filt}")

    def test_centre_tap_always_keeps_its_transformer(self):
        """A centre tap is a tapping of the secondary winding; it cannot exist without one."""
        svg = self._render({"rectifier_type": "full_wave_centre_tap",
                            "show_transformer": False})
        self.assertIn("centre tap", _svg_text(svg))

    def test_waveform_panels_are_optional(self):
        svg = self._render({"rectifier_type": "half_wave",
                            "show_input_waveform": False,
                            "show_output_waveform": False})
        self.assertTrue(_is_valid_svg(svg))
        self.assertNotIn("Input (AC)", _svg_text(svg))

    def test_output_panel_is_labelled_with_the_load(self):
        text = _svg_text(self._render({"rectifier_type": "half_wave", "load_label": "R_L"}))
        self.assertIn("Output across R_L", text)


class TestRLCHelpers(SimpleTestCase):
    def test_parse_quantity_handles_si_prefixes(self):
        """'1 mH' is milli and '1 MΩ' is mega. Confusing them moves f0 by 10^9."""
        self.assertAlmostEqual(_parse_quantity("1mH"), 1e-3)
        self.assertAlmostEqual(_parse_quantity("1 mH"), 1e-3)
        self.assertAlmostEqual(_parse_quantity("1µF"), 1e-6)
        self.assertAlmostEqual(_parse_quantity("1uF"), 1e-6)
        self.assertAlmostEqual(_parse_quantity("10 nF"), 1e-8)
        self.assertAlmostEqual(_parse_quantity("4.7 kΩ"), 4700.0)
        self.assertAlmostEqual(_parse_quantity("1 MΩ"), 1e6)
        self.assertAlmostEqual(_parse_quantity("100Ω"), 100.0)
        self.assertAlmostEqual(_parse_quantity(220), 220.0)
        self.assertIsNone(_parse_quantity(None))
        self.assertIsNone(_parse_quantity("large"))

    def test_resonant_frequency(self):
        """f0 = 1/(2π√(LC)): L=1mH, C=1µF ⇒ ~5.03 kHz. This number is the answer key."""
        f0 = resonant_frequency(1e-3, 1e-6)
        self.assertAlmostEqual(f0, 5032.9, places=1)
        self.assertAlmostEqual(resonant_frequency(10e-3, 10e-9), 15915.5, places=1)

    def test_resonant_frequency_needs_both_l_and_c(self):
        """An RL or RC circuit has no resonance; inventing one would be wrong physics."""
        self.assertIsNone(resonant_frequency(1e-3, None))
        self.assertIsNone(resonant_frequency(None, 1e-6))
        self.assertIsNone(resonant_frequency(0.0, 1e-6))


class TestRLCRenderer(SimpleTestCase):
    def _render(self, params):
        return render_circuits("rlc_circuit", params)

    RLC = [{"type": "resistor", "value": "100Ω"},
           {"type": "inductor", "value": "1mH"},
           {"type": "capacitor", "value": "1µF"}]

    def test_series_rlc(self):
        svg = self._render({"topology": "series", "components": self.RLC})
        self.assertTrue(_is_valid_svg(svg))

    def test_parallel_rlc(self):
        svg = self._render({"topology": "parallel", "components": self.RLC})
        self.assertTrue(_is_valid_svg(svg))

    def test_resonant_frequency_is_computed_from_l_and_c(self):
        """L=1mH with C=1µF resonates at 5.03 kHz. The value must be derived from the
        component values, not echoed from the params."""
        for topology in ("series", "parallel"):
            text = _svg_text(self._render({"topology": topology, "components": self.RLC,
                                           "show_resonance": True}))
            self.assertIn("5.03 kHz", text, topology)

    def test_series_and_parallel_resonance_behave_oppositely(self):
        """At resonance a series RLC has minimum impedance and a parallel one maximum;
        swapping these reverses the physics of every resonance question."""
        series = _svg_text(self._render({"topology": "series", "components": self.RLC,
                                         "show_resonance": True}))
        parallel = _svg_text(self._render({"topology": "parallel", "components": self.RLC,
                                           "show_resonance": True}))
        self.assertIn("Z is minimum", series)
        self.assertIn("Z is maximum", parallel)

    def test_impedance_formula_matches_the_topology(self):
        """Series adds impedances, parallel adds admittances (1/Z)."""
        series = _svg_text(self._render({"topology": "series", "components": self.RLC,
                                         "show_impedance_formula": True}))
        parallel = _svg_text(self._render({"topology": "parallel", "components": self.RLC,
                                           "show_impedance_formula": True}))
        self.assertIn("Z = √(R² + (X_L − X_C)²)", series)
        self.assertIn("1/Z", parallel)

    def test_subsets_of_rlc_render(self):
        """RL, RC and LC are all legal AC circuits, not just the full RLC."""
        subsets = [
            [{"type": "resistor", "value": "10Ω"}, {"type": "inductor", "value": "1mH"}],
            [{"type": "resistor", "value": "10Ω"}, {"type": "capacitor", "value": "1µF"}],
            [{"type": "inductor", "value": "1mH"}, {"type": "capacitor", "value": "1µF"}],
            [{"type": "resistor", "value": "10Ω"}],
        ]
        for topology in ("series", "parallel"):
            for comps in subsets:
                svg = self._render({"topology": topology, "components": comps,
                                    "show_impedance_formula": True})
                self.assertTrue(_is_valid_svg(svg))

    def test_resonance_without_l_and_c_falls_back_to_the_formula(self):
        """An RC circuit cannot resonate: no frequency may be printed for it."""
        text = _svg_text(self._render({
            "topology": "series",
            "components": [{"type": "resistor", "value": "10Ω"},
                           {"type": "capacitor", "value": "1µF"}],
            "show_resonance": True}))
        self.assertIn("f0 = 1/(2π√(LC))", text)
        self.assertNotIn("kHz", text)

    def test_resonance_with_unparseable_values_prints_no_number(self):
        """If L and C are symbolic, a numeric f0 would be fabricated."""
        text = _svg_text(self._render({
            "topology": "series",
            "components": [{"type": "inductor", "value": "L"},
                           {"type": "capacitor", "value": "C"}],
            "show_resonance": True}))
        self.assertNotIn("kHz", text)
        self.assertNotIn("Hz =", text)

    def test_duplicate_component_types_are_rejected(self):
        """Two inductors in one 'L' slot make the resonant frequency ambiguous."""
        with self.assertRaises(ValueError):
            self._render({"topology": "series",
                          "components": [{"type": "inductor", "value": "1mH"},
                                         {"type": "inductor", "value": "2mH"}]})

    def test_empty_component_list_is_rejected(self):
        with self.assertRaises(ValueError):
            self._render({"topology": "series", "components": []})


class TestNewCircuitsDeterminism(SimpleTestCase):
    """Same params must give byte-identical SVG: papers are cached and re-printed."""

    CASES = [
        ("wheatstone_bridge", {"variant": "wheatstone",
                               "resistor_values": ["10Ω", "20Ω", "30Ω", None]}),
        ("wheatstone_bridge", {"variant": "metre_bridge", "balance_length_cm": 40,
                               "known_resistance": "10Ω"}),
        ("wheatstone_bridge", {"variant": "potentiometer", "balance_length_cm": 40,
                               "balance_length_2_cm": 60}),
        ("rectifier", {"rectifier_type": "half_wave"}),
        ("rectifier", {"rectifier_type": "full_wave_centre_tap",
                       "show_filter_capacitor": True}),
        ("rectifier", {"rectifier_type": "full_wave_bridge",
                       "show_filter_capacitor": True}),
        ("rlc_circuit", {"topology": "series", "components": TestRLCRenderer.RLC,
                         "show_resonance": True}),
        ("rlc_circuit", {"topology": "parallel", "components": TestRLCRenderer.RLC,
                         "show_resonance": True}),
    ]

    def test_renders_are_reproducible(self):
        for subtype, params in self.CASES:
            self.assertEqual(render_circuits(subtype, params),
                             render_circuits(subtype, params), subtype)

    def test_unknown_subtype_raises(self):
        with self.assertRaises(ValueError):
            render_circuits("wheatstone", {})
