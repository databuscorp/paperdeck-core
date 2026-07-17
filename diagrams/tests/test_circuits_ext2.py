"""
Unit tests for the second batch of circuit renderers: mesh (multi-loop Kirchhoff)
networks, BJT amplifiers, transformers, RC charge/discharge, and galvanometer
conversion.

Every one of these subtypes prints a *derived* number or a *derived* topology into
a real exam paper — a shunt resistance, a turns ratio, a time constant, a phase
inversion, a junction dot. The assertions below are on the computed values and on
the drawn structure, never on byte counts, because a byte count cannot tell a
shunt in parallel from a shunt in series.
"""
import re

from django.test import SimpleTestCase

from diagrams.schemas.circuits import (
    AmplifierConfiguration, MeshCircuitSchema, RCGraphQuantity, RCMode,
    TransformerKind,
)
from diagrams.service.circuits.renderer import (
    render_circuits,
    _mesh_node_pixels,
    amplifier_phase_shift_deg,
    ammeter_shunt,
    rc_curve,
    rc_time_constant,
    rc_value,
    transformer_solve,
    voltmeter_series_resistance,
)


def _is_valid_svg(content: str) -> bool:
    return bool(content and "<svg" in content and "</svg>" in content)


def _svg_text(svg: str) -> str:
    return " ".join(re.findall(r">([^<>]+)<", svg))


def _junction_dots(svg: str):
    """Centres of the filled r=3.5 circles — the junction dots of a mesh."""
    out = []
    for tag in re.findall(r"<circle[^>]*/>", svg):
        if 'r="3.5"' in tag and 'fill="black"' in tag:
            cx = float(re.search(r'cx="([-\d.]+)"', tag).group(1))
            cy = float(re.search(r'cy="([-\d.]+)"', tag).group(1))
            out.append((cx, cy))
    return out


# ── fixtures ──────────────────────────────────────────────────────────────────

TWO_LOOP = {
    "nodes": [
        {"id": "A", "x": 0, "y": 0}, {"id": "B", "x": 1, "y": 0}, {"id": "C", "x": 2, "y": 0},
        {"id": "D", "x": 2, "y": 1}, {"id": "E", "x": 1, "y": 1}, {"id": "F", "x": 0, "y": 1},
    ],
    "branches": [
        {"from_node": "A", "to_node": "B",
         "components": [{"type": "resistor", "label": "R1", "value": "10Ω"}],
         "current_label": "I1"},
        {"from_node": "B", "to_node": "C",
         "components": [{"type": "resistor", "label": "R2", "value": "20Ω"}],
         "current_label": "I2"},
        {"from_node": "C", "to_node": "D",
         "components": [{"type": "battery", "label": "E2", "value": "6V",
                         "polarity": "reverse"}]},
        {"from_node": "D", "to_node": "E", "components": []},
        {"from_node": "E", "to_node": "F", "components": []},
        {"from_node": "F", "to_node": "A",
         "components": [{"type": "battery", "label": "E1", "value": "12V"}]},
        {"from_node": "B", "to_node": "E",
         "components": [{"type": "resistor", "label": "R3", "value": "30Ω"}],
         "current_label": "I3", "current_direction": "forward"},
    ],
    "loops": [
        {"node_ids": ["A", "B", "E", "F"], "label": "Loop 1", "direction": "cw"},
        {"node_ids": ["B", "C", "D", "E"], "label": "Loop 2", "direction": "ccw"},
    ],
}

# Bridged ladder: the P–Q link runs straight across the B–E rung. The two wires
# cross and are NOT connected.
CROSSING = {
    "nodes": [
        {"id": "A", "x": 0, "y": 0}, {"id": "B", "x": 1, "y": 0}, {"id": "C", "x": 2, "y": 0},
        {"id": "P", "x": 0, "y": 1}, {"id": "Q", "x": 2, "y": 1},
        {"id": "D", "x": 0, "y": 2}, {"id": "E", "x": 1, "y": 2}, {"id": "F", "x": 2, "y": 2},
    ],
    "branches": [
        {"from_node": "A", "to_node": "B", "components": [{"type": "resistor", "label": "R1"}]},
        {"from_node": "B", "to_node": "C", "components": [{"type": "resistor", "label": "R2"}]},
        {"from_node": "A", "to_node": "P", "components": []},
        {"from_node": "P", "to_node": "D",
         "components": [{"type": "battery", "label": "E", "value": "9V"}]},
        {"from_node": "C", "to_node": "Q", "components": []},
        {"from_node": "Q", "to_node": "F", "components": [{"type": "resistor", "label": "R6"}]},
        {"from_node": "D", "to_node": "E", "components": [{"type": "resistor", "label": "R4"}]},
        {"from_node": "E", "to_node": "F", "components": [{"type": "resistor", "label": "R5"}]},
        {"from_node": "B", "to_node": "E", "components": [{"type": "resistor", "label": "R3"}]},
        {"from_node": "P", "to_node": "Q", "components": [{"type": "ammeter", "label": "A"}]},
    ],
}

SQUARE = {
    "nodes": [{"id": "A", "x": 0, "y": 0}, {"id": "B", "x": 1, "y": 0},
              {"id": "C", "x": 1, "y": 1}, {"id": "D", "x": 0, "y": 1}],
    "branches": [
        {"from_node": "A", "to_node": "B", "components": [{"type": "resistor", "label": "R"}]},
        {"from_node": "B", "to_node": "C", "components": []},
        {"from_node": "C", "to_node": "D",
         "components": [{"type": "battery", "label": "E", "value": "6V"}]},
        {"from_node": "D", "to_node": "A", "components": []},
    ],
}


# ── mesh_circuit ──────────────────────────────────────────────────────────────

class TestMeshCircuitValidation(SimpleTestCase):
    def test_branch_to_unknown_node_is_rejected(self):
        """A branch wired to a node that does not exist has no defined geometry;
        drawing it anyway would invent a connection the question never had."""
        bad = dict(SQUARE, branches=SQUARE["branches"] + [
            {"from_node": "A", "to_node": "Z", "components": []}])
        with self.assertRaises(ValueError):
            render_circuits("mesh_circuit", bad)

    def test_declared_loop_that_is_not_a_cycle_is_rejected(self):
        """A→B→C is not closed (there is no C–A branch). Drawing a KVL arrow round
        it would tell the student to sum EMFs round a path that is not a loop."""
        bad = dict(SQUARE, loops=[{"node_ids": ["A", "B", "C"], "label": "Loop 1"}])
        with self.assertRaises(ValueError):
            render_circuits("mesh_circuit", bad)

    def test_genuine_cycle_is_accepted(self):
        """The same check must not reject a real mesh, or no KVL question can be drawn."""
        ok = dict(SQUARE, loops=[{"node_ids": ["A", "B", "C", "D"], "label": "Loop 1"}])
        self.assertTrue(_is_valid_svg(render_circuits("mesh_circuit", ok)))

    def test_two_node_loop_needs_two_parallel_branches(self):
        """Two nodes close a mesh only when two distinct branches join them; with a
        single branch there is nothing to go round."""
        one = dict(SQUARE, loops=[{"node_ids": ["A", "B"], "label": "Loop 1"}])
        with self.assertRaises(ValueError):
            render_circuits("mesh_circuit", one)

        two = {
            "nodes": SQUARE["nodes"],
            "branches": SQUARE["branches"] + [
                {"from_node": "A", "to_node": "B",
                 "components": [{"type": "resistor", "label": "R2"}]}],
            "loops": [{"node_ids": ["A", "B"], "label": "Loop 1", "direction": "ccw"}],
        }
        self.assertTrue(_is_valid_svg(render_circuits("mesh_circuit", two)))

    def test_dangling_node_is_rejected(self):
        """A node with one branch is a dead end — no current can flow through it."""
        bad = {
            "nodes": SQUARE["nodes"] + [{"id": "X", "x": 2, "y": 0}],
            "branches": SQUARE["branches"] + [
                {"from_node": "B", "to_node": "X", "components": []}],
        }
        with self.assertRaises(ValueError):
            render_circuits("mesh_circuit", bad)

    def test_branch_from_a_node_to_itself_is_rejected(self):
        """A self-loop is a short circuit, not a branch."""
        bad = dict(SQUARE, branches=SQUARE["branches"] + [
            {"from_node": "A", "to_node": "A", "components": []}])
        with self.assertRaises(ValueError):
            render_circuits("mesh_circuit", bad)

    def test_duplicate_node_ids_are_rejected(self):
        bad = dict(SQUARE, nodes=SQUARE["nodes"] + [{"id": "A", "x": 5, "y": 5}])
        with self.assertRaises(ValueError):
            render_circuits("mesh_circuit", bad)


class TestMeshCircuitRenderer(SimpleTestCase):
    def test_two_loop_kvl_network(self):
        svg = render_circuits("mesh_circuit", dict(TWO_LOOP, title="KVL"))
        self.assertTrue(_is_valid_svg(svg))
        text = _svg_text(svg)
        for label in ("R1 = 10Ω", "R2 = 20Ω", "R3 = 30Ω", "E1 = 12V", "E2 = 6V",
                      "Loop 1", "Loop 2", "I1", "I2", "I3"):
            self.assertIn(label, text)

    def test_junction_dot_exactly_where_three_branches_meet(self):
        """A dot is a connection. One drawn at a two-branch bend is noise; one
        missing at a three-branch node hides a junction the whole question turns on."""
        svg = render_circuits("mesh_circuit", TWO_LOOP)
        # B and E carry three branches each; A, C, D, F carry two.
        self.assertEqual(len(_junction_dots(svg)), 2)

    def test_crossing_wires_get_a_hop_and_no_junction_dot(self):
        """Two wires that merely cross are not connected. A junction dot at the
        crossing describes a completely different circuit — a hard error."""
        svg = render_circuits("mesh_circuit", CROSSING)
        schema = MeshCircuitSchema(**CROSSING)
        pos = _mesh_node_pixels(schema, 800, 600)
        crossing = (pos["B"][0], pos["P"][1])       # B–E rung × P–Q link

        dots = _junction_dots(svg)
        self.assertEqual(len(dots), 4)              # B, E, P, Q only
        for (dx, dy) in dots:
            self.assertGreater(abs(dx - crossing[0]) + abs(dy - crossing[1]), 5.0,
                               "a junction dot was drawn on a crossing")
        # ...and the horizontal wire arcs over the vertical one instead.
        self.assertIn("A 7.0,7.0", svg)

    def test_every_component_type_renders_on_a_branch(self):
        for ctype in ("resistor", "battery", "capacitor", "inductor", "ammeter",
                      "voltmeter", "galvanometer", "switch"):
            params = {
                "nodes": SQUARE["nodes"],
                "branches": [
                    {"from_node": "A", "to_node": "B",
                     "components": [{"type": ctype, "label": "X", "value": "1"}]},
                    {"from_node": "B", "to_node": "C", "components": []},
                    {"from_node": "C", "to_node": "D", "components": []},
                    {"from_node": "D", "to_node": "A", "components": []},
                ],
            }
            self.assertTrue(_is_valid_svg(render_circuits("mesh_circuit", params)), ctype)

    def test_polarity_reverse_flips_the_cell(self):
        """The + plate must face the node the params say it faces: a reversed cell
        changes the sign of every EMF term in the KVL equation."""
        fwd = render_circuits("mesh_circuit", SQUARE)
        rev_branches = [dict(b) for b in SQUARE["branches"]]
        rev_branches[2] = dict(rev_branches[2], components=[
            {"type": "battery", "label": "E", "value": "6V", "polarity": "reverse"}])
        rev = render_circuits("mesh_circuit", dict(SQUARE, branches=rev_branches))
        self.assertNotEqual(fwd, rev)

    def test_current_direction_reverse_flips_the_arrow(self):
        base = [dict(b) for b in SQUARE["branches"]]
        base[0] = dict(base[0], current_label="I")
        fwd = render_circuits("mesh_circuit", dict(SQUARE, branches=base))
        base_r = [dict(b) for b in base]
        base_r[0] = dict(base_r[0], current_direction="reverse")
        rev = render_circuits("mesh_circuit", dict(SQUARE, branches=base_r))
        self.assertNotEqual(fwd, rev)

    def test_loop_direction_cw_and_ccw_differ(self):
        cw = render_circuits("mesh_circuit", dict(
            SQUARE, loops=[{"node_ids": ["A", "B", "C", "D"], "direction": "cw"}]))
        ccw = render_circuits("mesh_circuit", dict(
            SQUARE, loops=[{"node_ids": ["A", "B", "C", "D"], "direction": "ccw"}]))
        self.assertNotEqual(cw, ccw)

    def test_display_toggles(self):
        for key in ("show_node_labels", "show_currents", "show_kvl_loops"):
            svg = render_circuits("mesh_circuit", dict(TWO_LOOP, **{key: False}))
            self.assertTrue(_is_valid_svg(svg), key)
        self.assertNotIn("Loop 1", _svg_text(
            render_circuits("mesh_circuit", dict(TWO_LOOP, show_kvl_loops=False))))


# ── transistor_amplifier ──────────────────────────────────────────────────────

class TestTransistorAmplifier(SimpleTestCase):
    def test_only_the_common_emitter_inverts(self):
        """The 180° inversion of a CE stage IS the exam question. A CB or CC stage
        that claims inversion, or a CE stage that does not, teaches the opposite."""
        self.assertEqual(
            amplifier_phase_shift_deg(AmplifierConfiguration.COMMON_EMITTER), 180)
        self.assertEqual(
            amplifier_phase_shift_deg(AmplifierConfiguration.COMMON_BASE), 0)
        self.assertEqual(
            amplifier_phase_shift_deg(AmplifierConfiguration.COMMON_COLLECTOR), 0)

    def test_every_configuration_and_type_renders(self):
        for cfg in ("common_emitter", "common_base", "common_collector"):
            for ttype in ("npn", "pnp"):
                svg = render_circuits("transistor_amplifier",
                                      {"configuration": cfg, "transistor_type": ttype})
                self.assertTrue(_is_valid_svg(svg), f"{cfg}/{ttype}")
                self.assertIn(ttype.upper(), _svg_text(svg))

    def test_phase_annotation_matches_the_configuration(self):
        """The caption is generated from the configuration, so the drawing and the
        words can never contradict each other."""
        ce = _svg_text(render_circuits("transistor_amplifier",
                                       {"configuration": "common_emitter"}))
        self.assertIn("180° out of phase", ce)
        for cfg in ("common_base", "common_collector"):
            txt = _svg_text(render_circuits("transistor_amplifier",
                                            {"configuration": cfg}))
            self.assertIn("in phase with Vin", txt)
            self.assertNotIn("180°", txt)

    def test_npn_and_pnp_emitter_arrows_point_opposite_ways(self):
        """NPN = Not Pointing iN. Flipping the emitter arrow changes the device."""
        npn = render_circuits("transistor_amplifier", {"transistor_type": "npn"})
        pnp = render_circuits("transistor_amplifier", {"transistor_type": "pnp"})
        self.assertNotEqual(npn, pnp)
        npn_tri = re.findall(r'<polygon[^>]*fill="black"[^>]*/>', npn)
        pnp_tri = re.findall(r'<polygon[^>]*fill="black"[^>]*/>', pnp)
        self.assertEqual(len(npn_tri), 1)
        self.assertEqual(len(pnp_tri), 1)
        self.assertNotEqual(npn_tri[0], pnp_tri[0])

    def test_waveform_panel_states_the_inversion(self):
        ce = _svg_text(render_circuits("transistor_amplifier",
                                       {"configuration": "common_emitter",
                                        "show_waveforms": True}))
        self.assertIn("Vout — inverted, 180° out of phase", ce)
        cc = _svg_text(render_circuits("transistor_amplifier",
                                       {"configuration": "common_collector",
                                        "show_waveforms": True}))
        self.assertIn("Vout — in phase", cc)

    def test_display_toggles_all_render(self):
        for key in ("show_biasing_resistors", "show_coupling_capacitors",
                    "show_supply", "show_input_output"):
            for cfg in ("common_emitter", "common_base", "common_collector"):
                svg = render_circuits("transistor_amplifier",
                                      {"configuration": cfg, key: False})
                self.assertTrue(_is_valid_svg(svg), f"{cfg}/{key}")


# ── transformer ───────────────────────────────────────────────────────────────

class TestTransformerSolve(SimpleTestCase):
    def test_secondary_voltage_from_the_turns_ratio(self):
        """Np=100, Ns=500, Vp=220 ⇒ Vs = 1100 V. This number is the answer key; it
        must be computed, never echoed from the params."""
        sol = transformer_solve(primary_turns=100, secondary_turns=500,
                                primary_voltage="220V")
        self.assertAlmostEqual(sol["ratio"], 5.0)
        self.assertAlmostEqual(sol["secondary_voltage"], 1100.0)
        self.assertEqual(sol["kind"], TransformerKind.STEP_UP)

    def test_step_up_is_classified_from_the_ratio_not_the_label(self):
        """An LLM that labels a 1:5 transformer 'step_down' must not make the paper
        say step-down."""
        sol = transformer_solve(primary_turns=100, secondary_turns=500,
                                primary_voltage="220V")
        self.assertEqual(sol["kind"], TransformerKind.STEP_UP)
        svg = _svg_text(render_circuits("transformer", {
            "transformer_type": "step_down",       # deliberately wrong
            "primary_turns": 100, "secondary_turns": 500,
            "primary_voltage": "220V"}))
        self.assertIn("STEP-UP transformer", svg)
        self.assertNotIn("STEP-DOWN", svg)

    def test_inconsistent_voltages_are_recomputed_from_the_turns(self):
        """Np=100, Ns=500, Vp=220, Vs=44 is an impossible transformer. The turns
        ratio wins and Vs is recomputed to 1100 V."""
        sol = transformer_solve(primary_turns=100, secondary_turns=500,
                                primary_voltage="220V", secondary_voltage="44V")
        self.assertTrue(sol["recomputed"])
        self.assertAlmostEqual(sol["secondary_voltage"], 1100.0)
        self.assertIn("1100 V", _svg_text(render_circuits("transformer", {
            "primary_turns": 100, "secondary_turns": 500,
            "primary_voltage": "220V", "secondary_voltage": "44V"})))

    def test_step_down_ratio(self):
        sol = transformer_solve(primary_turns=1000, secondary_turns=50,
                                primary_voltage="230V")
        self.assertAlmostEqual(sol["ratio"], 0.05)
        self.assertAlmostEqual(sol["secondary_voltage"], 11.5)
        self.assertEqual(sol["kind"], TransformerKind.STEP_DOWN)

    def test_ratio_falls_back_to_the_voltages_when_turns_are_absent(self):
        sol = transformer_solve(primary_voltage="220V", secondary_voltage="22V")
        self.assertAlmostEqual(sol["ratio"], 0.1)
        self.assertEqual(sol["kind"], TransformerKind.STEP_DOWN)
        self.assertEqual(sol["ratio_source"], "voltages")

    def test_ideal_currents_obey_ip_over_is_equals_ns_over_np(self):
        """Power in = power out for an ideal transformer: stepping the voltage up by
        5 steps the current down by 5."""
        sol = transformer_solve(primary_turns=100, secondary_turns=500,
                                primary_voltage="220V", primary_current="2A")
        self.assertAlmostEqual(sol["secondary_current"], 0.4)

    def test_efficiency_reduces_the_secondary_current(self):
        """With η = 90%, Vs·Is = 0.9·Vp·Ip — a 100%-efficient answer is wrong here."""
        sol = transformer_solve(primary_turns=1000, secondary_turns=50,
                                primary_voltage="230V", primary_current="1A",
                                efficiency=90)
        self.assertAlmostEqual(sol["secondary_current"], 18.0)   # 0.9 × 1 / 0.05

    def test_no_ratio_prints_no_number(self):
        """With nothing to derive the ratio from, inventing one would be fabrication."""
        sol = transformer_solve()
        self.assertIsNone(sol["ratio"])
        self.assertIsNone(sol["kind"])
        text = _svg_text(render_circuits("transformer",
                                         {"transformer_type": "step_up"}))
        self.assertIn("Ns/Np = Vs/Vp = Ip/Is", text)
        self.assertNotIn("STEP-UP transformer", text)

    def test_both_enum_variants_render_with_all_toggles(self):
        for kind in ("step_up", "step_down"):
            svg = render_circuits("transformer", {
                "transformer_type": kind,
                "primary_turns": 200, "secondary_turns": 400,
                "primary_voltage": "110V", "primary_current": "3A",
                "efficiency": 95, "show_core": True, "show_flux_direction": True,
                "show_equations": True, "show_turns_ratio": True})
            self.assertTrue(_is_valid_svg(svg), kind)
        self.assertTrue(_is_valid_svg(render_circuits("transformer", {
            "primary_turns": 200, "secondary_turns": 100,
            "show_core": False, "show_turns_ratio": False})))


# ── rc_circuit ────────────────────────────────────────────────────────────────

class TestRCHelpers(SimpleTestCase):
    def test_time_constant_is_rc(self):
        """R = 1 kΩ with C = 100 µF gives τ = 0.1 s. Every timing answer hangs on it."""
        self.assertAlmostEqual(rc_time_constant(1000.0, 100e-6), 0.1)
        self.assertAlmostEqual(rc_time_constant(2000.0, 50e-6), 0.1)

    def test_time_constant_rejects_non_positive_values(self):
        with self.assertRaises(ValueError):
            rc_time_constant(0.0, 100e-6)
        with self.assertRaises(ValueError):
            rc_time_constant(1000.0, 0.0)

    def test_charging_curve_reaches_63_2_percent_at_one_tau(self):
        """1 − e⁻¹ = 0.632. If this drifts, the 63.2%/86.5%/95% markings on every
        charging graph are wrong."""
        self.assertAlmostEqual(
            rc_value(RCMode.CHARGING, RCGraphQuantity.VOLTAGE, 1.0), 0.6321, places=4)
        self.assertAlmostEqual(
            rc_value(RCMode.CHARGING, RCGraphQuantity.VOLTAGE, 2.0), 0.8647, places=4)
        self.assertAlmostEqual(
            rc_value(RCMode.CHARGING, RCGraphQuantity.VOLTAGE, 3.0), 0.9502, places=4)

    def test_discharging_curve_falls_to_36_8_percent_at_one_tau(self):
        self.assertAlmostEqual(
            rc_value(RCMode.DISCHARGING, RCGraphQuantity.VOLTAGE, 1.0), 0.3679, places=4)

    def test_current_decays_while_charging_as_well_as_discharging(self):
        """The classic student error: the charging *current* does not rise with the
        voltage, it decays from V0/R to zero. Drawing it rising is wrong physics."""
        for mode in (RCMode.CHARGING, RCMode.DISCHARGING):
            _, ys = rc_curve(mode, RCGraphQuantity.CURRENT, n=200)
            self.assertAlmostEqual(ys[0], 1.0, places=6, msg=str(mode))
            self.assertLess(ys[-1], 0.01, msg=str(mode))
            for a, b in zip(ys, ys[1:]):
                self.assertLessEqual(b, a + 1e-12, msg=str(mode))

    def test_charge_and_voltage_rise_while_charging(self):
        for q in (RCGraphQuantity.VOLTAGE, RCGraphQuantity.CHARGE):
            _, ys = rc_curve(RCMode.CHARGING, q, n=200)
            self.assertAlmostEqual(ys[0], 0.0, places=6)
            self.assertGreater(ys[-1], 0.99)

    def test_both_mode_reverses_the_discharge_current(self):
        """When the key is thrown the capacitor drives current the other way round
        the loop, so the trace must cross to the negative side."""
        xs, ys = rc_curve(RCMode.BOTH, RCGraphQuantity.CURRENT, n=300)
        self.assertAlmostEqual(xs[-1], 10.0, places=6)
        self.assertGreater(max(ys), 0.99)
        self.assertLess(min(ys), -0.9)

    def test_both_mode_charge_rises_then_falls_and_never_goes_negative(self):
        xs, ys = rc_curve(RCMode.BOTH, RCGraphQuantity.CHARGE, n=300)
        peak = max(range(len(ys)), key=lambda i: ys[i])
        self.assertGreater(xs[peak], 4.5)
        self.assertLess(xs[peak], 5.5)
        self.assertGreaterEqual(min(ys), 0.0)
        self.assertLess(ys[-1], 0.02)


class TestRCRenderer(SimpleTestCase):
    def test_every_mode_and_quantity_renders(self):
        for mode in ("charging", "discharging", "both"):
            for q in ("voltage", "charge", "current"):
                svg = render_circuits("rc_circuit", {
                    "mode": mode, "graph_quantity": q, "mark_time_constants": True})
                self.assertTrue(_is_valid_svg(svg), f"{mode}/{q}")

    def test_time_constant_is_computed_and_annotated(self):
        """τ = 1 kΩ × 100 µF = 0.1 s = 100 ms. The number is derived from R and C."""
        text = _svg_text(render_circuits("rc_circuit", {
            "resistance": "1kΩ", "capacitance": "100µF", "show_time_constant": True}))
        self.assertIn("τ = RC", text)
        self.assertIn("100 ms", text)

    def test_time_constant_units_scale_with_the_values(self):
        text = _svg_text(render_circuits("rc_circuit", {
            "resistance": "1MΩ", "capacitance": "2µF"}))
        self.assertIn("2 s", text)

    def test_time_constant_marks_print_the_right_percentages(self):
        """Charging passes 63.2% / 86.5% / 95.0% at τ / 2τ / 3τ; discharging is the
        complement. Printing the charging numbers on a discharge graph is a lie."""
        charge = _svg_text(render_circuits("rc_circuit", {
            "mode": "charging", "graph_quantity": "voltage",
            "mark_time_constants": True}))
        for pct in ("63.2%", "86.5%", "95.0%"):
            self.assertIn(pct, charge)

        discharge = _svg_text(render_circuits("rc_circuit", {
            "mode": "discharging", "graph_quantity": "voltage",
            "mark_time_constants": True}))
        for pct in ("36.8%", "13.5%", "5.0%"):
            self.assertIn(pct, discharge)
        self.assertNotIn("63.2%", discharge)

    def test_graph_equation_matches_the_mode(self):
        charge = _svg_text(render_circuits("rc_circuit", {"mode": "charging"}))
        self.assertIn("V = V0(1 − e^(−t/RC))", charge)
        discharge = _svg_text(render_circuits("rc_circuit", {"mode": "discharging"}))
        self.assertIn("V = V0 e^(−t/RC)", discharge)

    def test_current_equation_says_it_decays_in_both_directions(self):
        text = _svg_text(render_circuits("rc_circuit", {
            "mode": "charging", "graph_quantity": "current"}))
        self.assertIn("decays while charging AND discharging", text)

    def test_graph_and_switch_are_optional(self):
        svg = render_circuits("rc_circuit", {"show_graph": False, "show_switch": False})
        self.assertTrue(_is_valid_svg(svg))
        self.assertNotIn("e^(−t/RC)", _svg_text(svg))


# ── galvanometer_conversion ───────────────────────────────────────────────────

class TestGalvanometerConversion(SimpleTestCase):
    def test_ammeter_shunt_value(self):
        """G = 100 Ω, Ig = 1 mA, range 5 A ⇒ S = Ig·G/(I − Ig) ≈ 0.02 Ω. A wrong
        shunt here is a wrong answer key on every conversion question."""
        s = ammeter_shunt(100.0, 1e-3, 5.0)
        self.assertAlmostEqual(s, 1e-3 * 100 / (5 - 1e-3), places=9)
        self.assertAlmostEqual(s, 0.020004, places=5)

    def test_ammeter_shunt_rejects_a_range_below_full_scale(self):
        """A shunt can only *raise* the range. Asking for 0.5 mA on a 1 mA movement
        is impossible, and a negative resistance must never be printed."""
        with self.assertRaises(ValueError):
            ammeter_shunt(100.0, 1e-3, 1e-3)
        with self.assertRaises(ValueError):
            ammeter_shunt(100.0, 1e-3, 5e-4)

    def test_voltmeter_series_resistance_value(self):
        """G = 100 Ω, Ig = 1 mA, range 15 V ⇒ R = V/Ig − G = 15000 − 100 = 14900 Ω."""
        self.assertAlmostEqual(
            voltmeter_series_resistance(100.0, 1e-3, 15.0), 14900.0, places=6)

    def test_voltmeter_rejects_a_range_at_or_below_ig_times_g(self):
        """Below Ig·G no series resistance exists; the movement already reads full
        scale. Printing a negative R would be nonsense."""
        with self.assertRaises(ValueError):
            voltmeter_series_resistance(100.0, 1e-3, 0.1)      # Ig·G = 0.1 V exactly
        with self.assertRaises(ValueError):
            voltmeter_series_resistance(100.0, 1e-3, 0.05)

    def test_ammeter_drawing_says_parallel_and_prints_the_shunt(self):
        """Parallel-vs-series IS the question. A shunt drawn in series is a different
        instrument and would read almost nothing."""
        text = _svg_text(render_circuits("galvanometer_conversion", {
            "conversion": "to_ammeter", "galvanometer_resistance": "100Ω",
            "full_scale_current": "1mA", "target_range": "5A"}))
        self.assertIn("PARALLEL", text)
        self.assertIn("S = Ig·G / (I − Ig)", text)
        self.assertIn("0.02 Ω", text)
        self.assertNotIn("SERIES", text)

    def test_voltmeter_drawing_says_series_and_prints_the_multiplier(self):
        text = _svg_text(render_circuits("galvanometer_conversion", {
            "conversion": "to_voltmeter", "galvanometer_resistance": "100Ω",
            "full_scale_current": "1mA", "target_range": "15V"}))
        self.assertIn("SERIES", text)
        self.assertIn("R = V/Ig − G", text)
        self.assertIn("14900 Ω", text)
        self.assertIn("15000 Ω", text)          # R_V = G + R
        self.assertNotIn("PARALLEL", text)

    def test_ammeter_resistance_is_small_and_voltmeter_resistance_is_large(self):
        """An ideal ammeter has ~zero resistance and an ideal voltmeter ~infinite:
        the computed R_A and R_V must land on the right side of G = 100 Ω."""
        g, ig = 100.0, 1e-3
        s = ammeter_shunt(g, ig, 5.0)
        r = voltmeter_series_resistance(g, ig, 15.0)
        self.assertLess(g * s / (g + s), g)
        self.assertGreater(g + r, g)

    def test_all_three_conversion_variants_render(self):
        cases = [
            {"conversion": "to_ammeter", "galvanometer_resistance": "100Ω",
             "full_scale_current": "1mA", "target_range": "5A"},
            {"conversion": "to_voltmeter", "galvanometer_resistance": "100Ω",
             "full_scale_current": "1mA", "target_range": "15V"},
            {"conversion": "none", "galvanometer_resistance": "100Ω",
             "full_scale_current": "1mA"},
        ]
        for params in cases:
            self.assertTrue(_is_valid_svg(render_circuits(
                "galvanometer_conversion", params)), params["conversion"])
            self.assertTrue(_is_valid_svg(render_circuits(
                "galvanometer_conversion", dict(params, show_formula=False,
                                                show_shunt=False,
                                                show_series_resistance=False))))


# ── determinism ───────────────────────────────────────────────────────────────

class TestBatch2Determinism(SimpleTestCase):
    """Same params → byte-identical SVG: papers are cached, re-rendered and reprinted."""

    CASES = [
        ("mesh_circuit", TWO_LOOP),
        ("mesh_circuit", CROSSING),
        ("transistor_amplifier", {"configuration": "common_emitter",
                                  "show_waveforms": True}),
        ("transistor_amplifier", {"configuration": "common_base",
                                  "transistor_type": "pnp"}),
        ("transformer", {"primary_turns": 100, "secondary_turns": 500,
                         "primary_voltage": "220V", "primary_current": "2A",
                         "show_equations": True, "show_flux_direction": True}),
        ("rc_circuit", {"mode": "both", "graph_quantity": "current"}),
        ("rc_circuit", {"mode": "charging", "mark_time_constants": True}),
        ("galvanometer_conversion", {"conversion": "to_ammeter",
                                     "galvanometer_resistance": "100Ω",
                                     "full_scale_current": "1mA",
                                     "target_range": "5A"}),
        ("galvanometer_conversion", {"conversion": "to_voltmeter",
                                     "galvanometer_resistance": "100Ω",
                                     "full_scale_current": "1mA",
                                     "target_range": "15V"}),
    ]

    def test_renders_are_reproducible(self):
        for subtype, params in self.CASES:
            self.assertEqual(render_circuits(subtype, params),
                             render_circuits(subtype, params), subtype)

    def test_all_five_subtypes_are_registered(self):
        for subtype in ("mesh_circuit", "transistor_amplifier", "transformer",
                        "rc_circuit", "galvanometer_conversion"):
            self.assertIn(subtype, _registered())


def _registered():
    from diagrams.service.circuits.renderer import CIRCUIT_RENDERERS
    return CIRCUIT_RENDERERS
