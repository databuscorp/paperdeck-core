"""
Unit tests for the third batch of circuit renderers: the electromagnetic machine
(AC/DC generator, DC motor), combinational logic building blocks (half/full adder,
half subtractor, 2:1 mux, SR latch, general netlist), the Zener voltage regulator,
the transistor switch, and the cathode-ray oscilloscope.

Every one of these prints a *derived* fact into a real exam paper — a truth table
computed from a gate netlist, a slip-ring-vs-commutator distinction, a clamped
regulator output, a Lissajous lobe count. The assertions below are on those
computed values and on the drawn structure, never on byte counts: a byte count
cannot tell a split ring from slip rings, nor a forward-biased Zener from a
reverse-biased one.
"""
import re

from django.test import SimpleTestCase

from diagrams.schemas.circuits import (
    CombinationalCircuit, EMMachineType, LogicCombinationalSchema, ScreenWaveform,
)
from diagrams.service.circuits.renderer import (
    render_circuits,
    CIRCUIT_RENDERERS,
    em_ring_type, em_is_motor, em_waveform,
    _combinational_netlist, combinational_truth_table, sr_latch_truth_table,
    zener_clamp,
    switch_operating_points,
    lissajous_curve, lissajous_lobes, _parse_ratio,
)


def _is_valid_svg(content: str) -> bool:
    return bool(content and "<svg" in content and "</svg>" in content)


def _svg_text(svg: str) -> str:
    return " ".join(re.findall(r">([^<>]+)<", svg))


def _table_for(circuit):
    schema = LogicCombinationalSchema(circuit=circuit)
    inputs, gates, conns, outputs = _combinational_netlist(schema)
    return combinational_truth_table(inputs, gates, conns, outputs)


# ── em_machine ────────────────────────────────────────────────────────────────

class TestEMMachineRingType(SimpleTestCase):
    def test_ac_generator_uses_slip_rings(self):
        """The slip-ring-vs-commutator choice IS the exam question. An AC generator
        must tap the coil through two full slip rings; drawing a split ring instead
        would silently turn it into a DC machine and rectify a sinusoid."""
        self.assertEqual(em_ring_type(EMMachineType.AC_GENERATOR), "slip_rings")

    def test_dc_generator_and_motor_use_a_split_ring(self):
        """A DC generator and a DC motor both need a split-ring commutator: the
        split is what reverses the external connection each half turn. Slip rings
        here would un-rectify the generator and stall the motor's torque."""
        self.assertEqual(em_ring_type(EMMachineType.DC_GENERATOR), "split_ring")
        self.assertEqual(em_ring_type(EMMachineType.DC_MOTOR), "split_ring")

    def test_ring_type_is_drawn_as_computed(self):
        """The label the reader sees must match the ring the code chose, so the
        picture and the physics agree."""
        ac = _svg_text(render_circuits("em_machine", {"machine": "ac_generator"}))
        self.assertIn("two slip rings", ac)
        self.assertNotIn("split-ring commutator", ac)
        dc = _svg_text(render_circuits("em_machine", {"machine": "dc_generator"}))
        self.assertIn("split-ring commutator", dc)
        self.assertNotIn("two slip rings", dc)

    def test_only_the_motor_is_driven(self):
        """A generator is turned to induce an EMF; a motor is fed a current to make
        a torque. Confusing the two inverts the whole energy-conversion story."""
        self.assertTrue(em_is_motor(EMMachineType.DC_MOTOR))
        self.assertFalse(em_is_motor(EMMachineType.AC_GENERATOR))
        self.assertFalse(em_is_motor(EMMachineType.DC_GENERATOR))
        motor = _svg_text(render_circuits("em_machine", {"machine": "dc_motor"}))
        self.assertIn("current is driven IN", motor)


class TestEMMachineWaveform(SimpleTestCase):
    def test_ac_generator_output_is_bipolar_sinusoid(self):
        """An AC generator's EMF must swing negative. A trace that never dips below
        zero is a rectified (DC) output — the wrong machine."""
        w = em_waveform(EMMachineType.AC_GENERATOR)
        self.assertLess(min(w), -0.9)
        self.assertGreater(max(w), 0.9)

    def test_dc_generator_output_is_rectified_humps(self):
        """The split ring flips every negative half-cycle up, so a DC generator's
        output is |sin| — strictly non-negative. A negative sample means the split
        ring was drawn (or modelled) as slip rings."""
        w = em_waveform(EMMachineType.DC_GENERATOR)
        self.assertGreaterEqual(min(w), 0.0)
        self.assertGreater(max(w), 0.9)

    def test_all_three_machines_render(self):
        for m in ("ac_generator", "dc_generator", "dc_motor"):
            svg = render_circuits("em_machine", {
                "machine": m, "show_flux": True, "show_brushes": True,
                "show_force_directions": True, "show_output_waveform": True})
            self.assertTrue(_is_valid_svg(svg), m)


# ── logic_combinational ───────────────────────────────────────────────────────

class TestCombinationalTruthTables(SimpleTestCase):
    def test_half_adder_is_sum_xor_and_carry_and(self):
        """The half adder's whole reason to exist: Sum = A⊕B, Carry = A·B. If the
        table is hand-written and drifts from the XOR/AND netlist, the drawing and
        the answer key contradict each other."""
        headers, rows = _table_for(CombinationalCircuit.HALF_ADDER)
        self.assertEqual(headers, ["A", "B", "Sum", "Carry"])
        for a, b, s, c in rows:
            self.assertEqual(s, a ^ b, f"Sum wrong at A={a} B={b}")
            self.assertEqual(c, a & b, f"Carry wrong at A={a} B={b}")

    def test_full_adder_sum_is_odd_parity_and_carry_is_majority(self):
        """A full adder's Sum is 1 for exactly the odd-parity input rows and its
        Carry for the majority. These are computed by chaining two half-adders and
        an OR — get the wiring wrong and both columns are wrong."""
        headers, rows = _table_for(CombinationalCircuit.FULL_ADDER)
        self.assertEqual(headers, ["A", "B", "Cin", "Sum", "Carry"])
        for a, b, cin, s, c in rows:
            self.assertEqual(s, (a + b + cin) % 2, f"Sum wrong at {a}{b}{cin}")
            self.assertEqual(c, 1 if (a + b + cin) >= 2 else 0,
                             f"Carry wrong at {a}{b}{cin}")

    def test_half_subtractor_diff_and_borrow(self):
        """Half subtractor: Diff = A⊕B, Borrow = A'·B (you borrow only when A=0,
        B=1). A borrow drawn as A·B' subtracts the wrong way."""
        headers, rows = _table_for(CombinationalCircuit.HALF_SUBTRACTOR)
        self.assertEqual(headers, ["A", "B", "Diff", "Borrow"])
        for a, b, d, br in rows:
            self.assertEqual(d, a ^ b)
            self.assertEqual(br, (1 - a) & b)

    def test_mux_selects_i0_when_s_is_0_and_i1_when_s_is_1(self):
        """A 2:1 mux must pass I0 while S=0 and I1 while S=1. A swapped select line
        routes the wrong input on every row."""
        headers, rows = _table_for(CombinationalCircuit.MUX_2TO1)
        self.assertEqual(headers, ["I0", "I1", "S", "Y"])
        for i0, i1, s, y in rows:
            self.assertEqual(y, i1 if s else i0, f"mux wrong at I0={i0} I1={i1} S={s}")

    def test_sr_latch_set_reset_hold_and_forbidden(self):
        """The SR (NOR) latch table, settled from the actual cross-coupled
        equations: S=1,R=0 sets Q=1; S=0,R=1 resets Q=0; S=R=0 holds (Q0); S=R=1 is
        forbidden with Q=Q'=0. Mislabelling the forbidden state teaches a race."""
        headers, rows, notes = sr_latch_truth_table()
        self.assertEqual(headers, ["S", "R", "Q", "Q'"])
        table = {(r[0], r[1]): (r[2], r[3], n) for r, n in zip(rows, notes)}
        self.assertEqual(table[(1, 0)][:2], (1, 0))          # set
        self.assertEqual(table[(0, 1)][:2], (0, 1))          # reset
        self.assertEqual(table[(0, 0)][2], "hold")           # no change
        self.assertEqual(table[(1, 1)][:2], (0, 0))          # forbidden
        self.assertEqual(table[(1, 1)][2], "forbidden")

    def test_general_netlist_truth_table_matches_the_gates(self):
        """A user-supplied netlist must have its table evaluated from those exact
        gates. Here a lone NAND must give Y = (A·B)'."""
        params = {
            "circuit": "netlist",
            "inputs": [{"id": "A", "label": "A"}, {"id": "B", "label": "B"}],
            "gates": [{"id": "g1", "gate_type": "NAND"}],
            "connections": [{"from_id": "A", "to_id": "g1", "to_input_index": 0},
                            {"from_id": "B", "to_id": "g1", "to_input_index": 1}],
            "outputs": [{"id": "g1", "label": "Y"}],
        }
        schema = LogicCombinationalSchema(**params)
        inputs, gates, conns, outputs = _combinational_netlist(schema)
        headers, rows = combinational_truth_table(inputs, gates, conns, outputs)
        self.assertEqual(headers, ["A", "B", "Y"])
        for a, b, y in rows:
            self.assertEqual(y, 1 - (a & b))
        self.assertTrue(_is_valid_svg(render_circuits("logic_combinational", params)))

    def test_netlist_output_naming_unknown_gate_is_rejected(self):
        """An output that names a gate that does not exist has nothing to draw or
        compute; accepting it would print a phantom column."""
        with self.assertRaises(Exception):
            render_circuits("logic_combinational", {
                "circuit": "netlist",
                "inputs": [{"id": "A", "label": "A"}],
                "gates": [{"id": "g1", "gate_type": "NOT"}],
                "connections": [{"from_id": "A", "to_id": "g1"}],
                "outputs": [{"id": "ghost", "label": "Y"}]})

    def test_every_named_circuit_renders(self):
        for c in ("half_adder", "full_adder", "half_subtractor",
                  "mux_2to1", "sr_latch"):
            svg = render_circuits("logic_combinational", {"circuit": c})
            self.assertTrue(_is_valid_svg(svg), c)

    def test_output_labels_override_is_honoured(self):
        svg = _svg_text(render_circuits("logic_combinational", {
            "circuit": "half_adder", "output_labels": ["S", "Cout"]}))
        self.assertIn("S", svg)
        self.assertIn("Cout", svg)


# ── zener_regulator ───────────────────────────────────────────────────────────

class TestZenerRegulator(SimpleTestCase):
    def test_output_is_clamped_to_vz_while_vin_exceeds_vz(self):
        """The regulator's entire job: hold Vout = Vz whenever Vin > Vz. If the
        clamp leaks, the 'regulated' rail is not regulated and the question is void."""
        vz = 5.1
        vin = [7.0, 8.5, 6.0, 9.9, 5.2]
        out = zener_clamp(vin, vz)
        self.assertTrue(all(abs(v - vz) < 1e-9 for v in out), out)

    def test_below_vz_the_zener_stops_regulating(self):
        """When Vin dips below Vz the Zener leaves breakdown and the output simply
        follows the input — it cannot hold a rail higher than its source."""
        vz = 5.1
        vin = [3.0, 4.0, 5.0]
        self.assertEqual(zener_clamp(vin, vz), vin)

    def test_drawing_states_the_regulated_output_and_current_law(self):
        text = _svg_text(render_circuits("zener_regulator", {
            "zener_voltage": "5.1V", "input_voltage": "10V"}))
        self.assertIn("Vout = Vz (regulated)", text)
        self.assertIn("Is = Iz + IL", text)

    def test_renders_with_and_without_load_and_waveforms(self):
        for params in ({"show_load": True, "show_waveforms": True},
                       {"show_load": False, "show_waveforms": False},
                       {"show_current_labels": False}):
            self.assertTrue(_is_valid_svg(
                render_circuits("zener_regulator", params)), params)


# ── transistor_switch ─────────────────────────────────────────────────────────

class TestTransistorSwitch(SimpleTestCase):
    def test_operating_points_are_the_two_ends_of_the_load_line(self):
        """Cutoff sits at (Vce=Vcc, Ic=0) and saturation at (Vce≈0, Ic=Vcc/R).
        These endpoints are the answer to 'what current flows when the switch is
        ON?'; a hand-picked Ic would misstate the load current."""
        pts = switch_operating_points(5.0, 100.0)
        self.assertEqual(pts["cutoff"], (5.0, 0.0))
        self.assertAlmostEqual(pts["saturation"][0], 0.0)
        self.assertAlmostEqual(pts["saturation"][1], 0.05)     # 5 V / 100 Ω

    def test_npn_and_pnp_emitter_arrows_differ(self):
        """NPN = Not Pointing iN: the emitter arrow points out. Flipping it changes
        the device, and a switch drawn with the wrong arrow is the wrong transistor."""
        npn = render_circuits("transistor_switch", {"transistor_type": "npn", "state": "on"})
        pnp = render_circuits("transistor_switch", {"transistor_type": "pnp", "state": "on"})
        self.assertNotEqual(npn, pnp)

    def test_load_glows_only_at_saturation(self):
        """A lamp/LED is drawn energised only when the transistor saturates. A load
        shown lit at cutoff teaches that the switch conducts when it is off."""
        on = render_circuits("transistor_switch",
                             {"state": "on", "load_type": "lamp"})
        off = render_circuits("transistor_switch",
                              {"state": "off", "load_type": "lamp"})
        self.assertIn("#ffe680", on)         # filled (glowing) lamp
        self.assertNotIn("#ffe680", off)

    def test_every_state_and_load_type_renders(self):
        for state in ("on", "off", "both"):
            for load in ("lamp", "led", "relay", "motor"):
                svg = render_circuits("transistor_switch",
                                      {"state": state, "load_type": load})
                self.assertTrue(_is_valid_svg(svg), f"{state}/{load}")


# ── cro ───────────────────────────────────────────────────────────────────────

class TestCRO(SimpleTestCase):
    def test_1_to_2_lissajous_has_two_vertical_lobes(self):
        """A 1:2 Lissajous is a figure that touches the top edge twice and the side
        once, giving fx:fy = 1:2 straight off the screen. A wrong lobe count reads
        back the wrong frequency ratio — the entire point of the measurement."""
        ny, nx = lissajous_lobes(1, 2)
        self.assertEqual((ny, nx), (2, 1))

    def test_lobe_counts_equal_the_frequencies_for_several_ratios(self):
        """In general ny = fy (top touches) and nx = fx (side touches). If this
        breaks, every Lissajous frequency-ratio question is unanswerable."""
        for fx, fy in [(1, 1), (1, 2), (2, 1), (2, 3), (3, 2), (1, 3)]:
            ny, nx = lissajous_lobes(fx, fy)
            self.assertEqual(ny, fy, f"{fx}:{fy}")
            self.assertEqual(nx, fx, f"{fx}:{fy}")

    def test_lissajous_curve_is_closed(self):
        """A Lissajous with integer frequencies is a closed loop; if the ends do not
        meet, the trace is drawn as an open ribbon that no ratio produces."""
        pts = lissajous_curve(2, 3, 90.0)
        self.assertAlmostEqual(pts[0][0], pts[-1][0], places=6)
        self.assertAlmostEqual(pts[0][1], pts[-1][1], places=6)

    def test_ratio_parser(self):
        self.assertEqual(_parse_ratio("1:2"), (1, 2))
        self.assertEqual(_parse_ratio("3:4"), (3, 4))
        self.assertEqual(_parse_ratio("garbage"), (1, 1))

    def test_every_screen_waveform_renders(self):
        for wf in ("sine", "square", "dc", "lissajous"):
            svg = render_circuits("cro", {"screen_waveform": wf})
            self.assertTrue(_is_valid_svg(svg), wf)

    def test_lissajous_caption_matches_the_computed_ratio(self):
        text = _svg_text(render_circuits("cro", {
            "screen_waveform": "lissajous", "lissajous_ratio": "1:2"}))
        self.assertIn("fx:fy = 1:2", text)


# ── determinism + registration ────────────────────────────────────────────────

class TestBatch3Determinism(SimpleTestCase):
    """Same params → byte-identical SVG: papers are cached, re-rendered, reprinted."""

    CASES = [
        ("em_machine", {"machine": "ac_generator", "show_force_directions": True}),
        ("em_machine", {"machine": "dc_generator"}),
        ("em_machine", {"machine": "dc_motor"}),
        ("logic_combinational", {"circuit": "full_adder"}),
        ("logic_combinational", {"circuit": "sr_latch"}),
        ("zener_regulator", {"zener_voltage": "5.1V", "input_voltage": "10V"}),
        ("transistor_switch", {"state": "both", "load_type": "lamp"}),
        ("cro", {"screen_waveform": "lissajous", "lissajous_ratio": "2:3"}),
    ]

    def test_renders_are_reproducible(self):
        for subtype, params in self.CASES:
            self.assertEqual(render_circuits(subtype, params),
                             render_circuits(subtype, params), subtype)

    def test_all_five_subtypes_are_registered(self):
        for subtype in ("em_machine", "logic_combinational", "zener_regulator",
                        "transistor_switch", "cro"):
            self.assertIn(subtype, CIRCUIT_RENDERERS)
