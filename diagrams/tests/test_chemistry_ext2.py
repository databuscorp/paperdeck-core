"""
Unit tests for the SECOND wave of extended Chemistry renderers:
reaction_scheme, crystal_field_splitting, kinetics_graph, colligative_graph,
organic_mechanism, hybridisation_overlap, adsorption_isotherm.

As with test_chemistry_ext, a diagram that renders cleanly but states the wrong
chemistry (a d5 low-spin complex drawn with 5 unpaired electrons, a "first-order"
plot that is actually a parabola, an Arrhenius slope that is not -Ea/R) is worse
than no diagram at all. So the chemistry is asserted directly on the values the
helper functions COMPUTE, not on the SVG bytes; the SVG is only smoke-tested so
that every enum value is known to render.

SimpleTestCase: none of this touches the database. Run with plain unittest
(NOT manage.py test): after `django.setup()`,
    unittest ... diagrams.tests.test_chemistry_ext2
"""
import numpy as np
from django.test import SimpleTestCase

from diagrams.service.chemistry.renderer import (
    render_chemistry, CHEMISTRY_RENDERERS,
    _cfs_build, _delta_t, _CFS_SETS,
    _conc_profile, _time_span, _half_life, _r_squared, _arrhenius_series, _R_KJ,
    _bond_angle,
)
from diagrams.schemas.chemistry import (
    CrystalFieldSplittingSchema, KineticsGraphSchema,
)


def _is_valid_svg(content: str) -> bool:
    return bool(content and "<svg" in content and "</svg>" in content)


# ── every enum value, kept next to the schema it mirrors ──────────────────────
SCHEME_LAYOUTS = ["horizontal", "grid", "branched"]
ARROW_TYPES = ["forward", "reversible", "equilibrium"]
CFS_GEOMETRIES = ["octahedral", "tetrahedral", "square_planar"]
CFS_FIELDS = ["strong", "weak"]
KINETICS_PLOTS = [
    "concentration_time", "ln_concentration_time", "inverse_concentration_time",
    "rate_vs_concentration", "arrhenius", "half_life",
]
KINETICS_ORDERS = [0, 1, 2]
COLLIGATIVE_PROPERTIES = [
    "vapour_pressure_lowering", "boiling_point_elevation",
    "freezing_point_depression", "osmotic_pressure",
    "raoult_ideal", "raoult_deviation",
]
COLLIGATIVE_DEVIATIONS = ["none", "positive", "negative"]
MECHANISMS = [
    "e1", "e2", "electrophilic_aromatic_substitution", "markovnikov_addition",
    "anti_markovnikov", "aldol", "cannizzaro", "esterification",
    "free_radical_substitution",
]
HYBRIDISATIONS = ["sp", "sp2", "sp3", "sp3d", "sp3d2"]
BOND_TYPES = ["sigma", "pi", "both"]
ISOTHERMS = ["freundlich", "langmuir", "bet"]


# ── 1. Reaction Scheme ────────────────────────────────────────────────────────

class TestReactionScheme(SimpleTestCase):
    def _render(self, params):
        return render_chemistry("reaction_scheme", params)

    def test_every_layout_renders(self):
        """A roadmap that will not lay out loses the entire 'identify A → B → C'
        question family; each layout is a separate drawing path."""
        base = {"steps": [{"from_label": "A", "to_label": "B", "reagent": "Br₂"},
                          {"from_label": "A", "to_label": "C", "reagent": "HNO₃"}],
                "species": [{"label": "A"}, {"label": "B"}, {"label": "C"}]}
        for layout in SCHEME_LAYOUTS:
            with self.subTest(layout=layout):
                self.assertTrue(_is_valid_svg(self._render({**base, "layout": layout})))

    def test_every_arrow_type_renders(self):
        """forward / reversible / equilibrium arrows are drawn differently; a missing
        head style silently turns an equilibrium into a one-way reaction."""
        for arrow in ARROW_TYPES:
            with self.subTest(arrow_type=arrow):
                svg = self._render({
                    "steps": [{"from_label": "A", "to_label": "B", "arrow_type": arrow}],
                    "species": [{"label": "A"}, {"label": "B"}]})
                self.assertTrue(_is_valid_svg(svg))

    def test_unknown_species_and_smiles_render(self):
        """The boxed '?' unknown and a real SMILES structure are the two ways a species
        is drawn; both must survive."""
        svg = self._render({
            "steps": [{"from_label": "A", "to_label": "B", "reagent": "conc. H₂SO₄",
                       "conditions": "443 K"}],
            "species": [{"label": "A", "smiles": "CCO", "name": "ethanol"},
                        {"label": "B", "is_unknown": True}]})
        self.assertTrue(_is_valid_svg(svg))

    def test_empty_steps_rejected(self):
        with self.assertRaises(Exception):
            self._render({"steps": [], "species": [{"label": "A"}]})

    def test_unknown_layout_rejected(self):
        with self.assertRaises(Exception):
            self._render({"steps": [{"from_label": "A", "to_label": "B"}],
                          "layout": "spiral"})


# ── 2. Crystal Field Splitting ────────────────────────────────────────────────

class TestCrystalFieldSplitting(SimpleTestCase):
    def _render(self, params):
        return render_chemistry("crystal_field_splitting", params)

    def _build(self, **kw):
        return _cfs_build(CrystalFieldSplittingSchema(**kw))

    def test_every_geometry_and_field_renders(self):
        """Each geometry × field is a distinct exam scenario; one un-renderable pair
        removes a whole class of coordination-chemistry questions."""
        for geom in CFS_GEOMETRIES:
            for field in CFS_FIELDS:
                with self.subTest(geometry=geom, ligand_field=field):
                    svg = self._render({"geometry": geom, "ligand_field": field,
                                        "d_electrons": 6})
                    self.assertTrue(_is_valid_svg(svg))

    def test_strong_field_d5_octahedral_is_low_spin_one_unpaired(self):
        """[Fe(CN)₆]³⁻ (d5, strong field, octahedral) is the textbook low-spin case:
        t₂g⁵ eg⁰ → exactly 1 unpaired electron and CFSE = -2.0·Δo. If this drifts,
        the paper's answer to 'spin-only moment of [Fe(CN)₆]³⁻' is wrong."""
        b = self._build(geometry="octahedral", metal_ion="[Fe(CN)₆]³⁻",
                        ligand_field="strong", d_electrons=5)
        self.assertTrue(b["low_spin"])
        self.assertEqual(b["unpaired"], 1)
        self.assertAlmostEqual(b["cfse"], -2.0, places=6)   # -2.0·Δo

    def test_weak_field_d5_octahedral_is_high_spin_five_unpaired_zero_cfse(self):
        """The SAME d5 in a WEAK field ([FeF₆]³⁻) is high-spin: one electron in each of
        the five d orbitals → 5 unpaired and CFSE = 0 (3·(-0.4)+2·(+0.6)). Contrast
        with the strong-field case is the whole point of the question."""
        b = self._build(geometry="octahedral", ligand_field="weak", d_electrons=5)
        self.assertFalse(b["low_spin"])
        self.assertEqual(b["unpaired"], 5)
        self.assertAlmostEqual(b["cfse"], 0.0, places=6)

    def test_tetrahedral_is_forced_high_spin_even_when_asked_for_low_spin(self):
        """Δt ≈ (4/9)Δo is always smaller than the pairing energy, so NO tetrahedral
        complex is ever low-spin. Params requesting a strong (low-spin) field must be
        overruled — otherwise the diagram would assert a species that cannot exist."""
        b = self._build(geometry="tetrahedral", ligand_field="strong", d_electrons=6)
        self.assertTrue(b["forced_high_spin"])
        self.assertFalse(b["low_spin"])
        self.assertEqual(b["spin_state"], "High-spin")

    def test_tetrahedral_e_level_sits_below_t2(self):
        """In a tetrahedral field the e set is stabilised and t₂ destabilised: e must be
        drawn BELOW t₂. Flipping them inverts the whole splitting diagram."""
        b = self._build(geometry="tetrahedral", ligand_field="weak", d_electrons=4)
        e_set, t2_set = b["sets"][0], b["sets"][1]
        self.assertEqual(e_set["label"], "e")
        self.assertEqual(t2_set["label"], "t₂")
        self.assertLess(e_set["energy"], t2_set["energy"])
        # ...and the raw geometry table agrees, so the drawing can't disagree with it.
        labels = [lbl for lbl, _n, _e in _CFS_SETS["tetrahedral"]]
        self.assertEqual(labels, ["e", "t₂"])

    def test_delta_t_is_four_ninths_of_delta_o(self):
        """Δt = (4/9)·Δo — four ligands, none on an axis. Any other factor makes every
        tetrahedral CFSE and every 'why are tetrahedral complexes high-spin' answer
        wrong."""
        self.assertAlmostEqual(_delta_t(1.0), 4.0 / 9.0, places=12)
        self.assertAlmostEqual(_delta_t(0.9), 0.9 * 4.0 / 9.0, places=12)

    def test_unknown_geometry_rejected(self):
        with self.assertRaises(Exception):
            self._render({"geometry": "trigonal_prismatic"})


# ── 3. Kinetics Graph ─────────────────────────────────────────────────────────

class TestKineticsGraph(SimpleTestCase):
    def _render(self, params):
        return render_chemistry("kinetics_graph", params)

    def test_every_plot_and_order_renders(self):
        """Each (plot, order) pair is a separate graph a question can be built on; one
        that will not render silently deletes that question."""
        for plot in KINETICS_PLOTS:
            for order in KINETICS_ORDERS:
                with self.subTest(plot=plot, order=order):
                    svg = self._render({"plot": plot, "order": order,
                                        "rate_constant": 0.05})
                    self.assertTrue(_is_valid_svg(svg))

    def test_first_order_is_linear_on_ln_conc_but_not_on_conc(self):
        """A first-order reaction gives a STRAIGHT line on ln[A] vs t (R² ≈ 1) and a
        CURVE on [A] vs t. That contrast is exactly how the order is read off a graph;
        if ln[A] stops being linear the diagram teaches the wrong method."""
        k, a0, order = 0.05, 1.0, 1
        t = np.linspace(0.0, _time_span(order, k, a0), 200)
        conc = _conc_profile(order, k, a0, t)
        self.assertAlmostEqual(_r_squared(t, np.log(conc)), 1.0, places=6)
        self.assertLess(_r_squared(t, conc), 0.99)          # [A] vs t is not a line

    def test_zero_order_is_linear_on_conc_not_on_ln_conc(self):
        """The mirror check: a zero-order reaction is the LINEAR one on [A] vs t, and
        it is ln[A] vs t that curves. Keeps the linearises-which-order mapping honest."""
        k, a0, order = 0.05, 1.0, 0
        t = np.linspace(0.0, _time_span(order, k, a0), 200)
        conc = _conc_profile(order, k, a0, t)
        self.assertAlmostEqual(_r_squared(t, conc), 1.0, places=6)
        self.assertLess(_r_squared(t, np.log(conc)), 0.99)

    def test_first_order_half_life_is_independent_of_initial_concentration(self):
        """t½ = ln2/k for first order — the same number whatever [A]₀ is. This
        independence IS the standard first-order question."""
        k = 0.05
        halves = [_half_life(1, k, a0) for a0 in (0.25, 1.0, 4.0)]
        for h in halves[1:]:
            self.assertAlmostEqual(h, halves[0], places=9)
        self.assertAlmostEqual(halves[0], np.log(2.0) / k, places=9)

    def test_zero_order_half_life_scales_with_initial_concentration(self):
        """t½ = [A]₀/2k for zero order — PROPORTIONAL to [A]₀. If this came out constant
        the diagram would contradict the zero-order rate law it prints."""
        k = 0.05
        h_lo = _half_life(0, k, 1.0)
        h_hi = _half_life(0, k, 2.0)
        self.assertNotAlmostEqual(h_hi, h_lo, places=6)
        self.assertAlmostEqual(h_hi, 2.0 * h_lo, places=9)   # doubles with [A]₀

    def test_arrhenius_slope_is_minus_ea_over_r(self):
        """An Arrhenius plot (ln k vs 1/T) is a straight line of slope −Ea/R. That slope
        is how Ea is extracted; a wrong slope gives a wrong activation energy."""
        ea = 52.0                                             # kJ/mol
        inv_t, ln_k = _arrhenius_series(ea, (300.0, 400.0))
        slope = float(np.polyfit(inv_t, ln_k, 1)[0])
        self.assertAlmostEqual(slope, -ea / _R_KJ, delta=abs(slope) * 1e-6)

    def test_unknown_plot_rejected(self):
        with self.assertRaises(Exception):
            self._render({"plot": "concentration_squared_time"})


# ── 4. Colligative Graph ──────────────────────────────────────────────────────

class TestColligativeGraph(SimpleTestCase):
    def _render(self, params):
        return render_chemistry("colligative_graph", params)

    def test_every_property_renders(self):
        """Each colligative property is its own graph; losing one loses that topic."""
        for prop in COLLIGATIVE_PROPERTIES:
            with self.subTest(property=prop):
                self.assertTrue(_is_valid_svg(self._render({"property": prop})))

    def test_every_deviation_renders_with_azeotrope(self):
        """none / positive / negative Raoult deviations, each with the azeotrope marked,
        are three distinct diagrams."""
        for dev in COLLIGATIVE_DEVIATIONS:
            with self.subTest(deviation=dev):
                svg = self._render({"property": "raoult_deviation", "deviation": dev,
                                    "show_azeotrope": True})
                self.assertTrue(_is_valid_svg(svg))

    def test_unknown_property_rejected(self):
        with self.assertRaises(Exception):
            self._render({"property": "ebullioscopy"})


# ── 5. Organic Mechanism ──────────────────────────────────────────────────────

class TestOrganicMechanism(SimpleTestCase):
    def _render(self, params):
        return render_chemistry("organic_mechanism", params)

    def test_every_mechanism_renders(self):
        """All nine named mechanisms must render — each is a separate NCERT reaction the
        AI pipeline may ask for."""
        for mech in MECHANISMS:
            with self.subTest(mechanism=mech):
                self.assertTrue(_is_valid_svg(self._render({"mechanism": mech})))

    def test_mechanism_aliases_are_accepted(self):
        """The schema normalises 'eas', 'markovnikov', 'anti-markovnikov', 'free_radical'
        so the LLM can use the common name without breaking the renderer."""
        for alias in ("eas", "markovnikov", "anti-markovnikov", "free radical"):
            with self.subTest(alias=alias):
                self.assertTrue(_is_valid_svg(self._render({"mechanism": alias})))

    def test_unknown_mechanism_rejected(self):
        with self.assertRaises(Exception):
            self._render({"mechanism": "pericyclic"})


# ── 6. Hybridisation / Orbital Overlap ────────────────────────────────────────

class TestHybridisationOverlap(SimpleTestCase):
    def _render(self, params):
        return render_chemistry("hybridisation_overlap", params)

    def test_every_hybridisation_and_bond_type_renders(self):
        """Each hybridisation × bond-type is a separate overlap picture; one missing
        combination removes that shape from the question bank."""
        for hyb in HYBRIDISATIONS:
            for bt in BOND_TYPES:
                with self.subTest(hybridisation=hyb, bond_type=bt):
                    svg = self._render({"hybridisation": hyb, "bond_type": bt})
                    self.assertTrue(_is_valid_svg(svg))

    def test_sp2_bond_angle_is_120_degrees(self):
        """sp² hybridisation is trigonal planar → 120°. The angle is COMPUTED, not
        supplied; if it drifts the ethene/BF₃ geometry question is answered wrong."""
        self.assertEqual(_bond_angle("sp2"), 120.0)

    def test_bond_angles_track_the_hybridisation(self):
        """The full ladder: sp 180°, sp² 120°, sp³ 109.5°, and the axial 90° of the
        expanded-octet sets. A single wrong entry mislabels a real molecule."""
        self.assertEqual(_bond_angle("sp"), 180.0)
        self.assertEqual(_bond_angle("sp2"), 120.0)
        self.assertAlmostEqual(_bond_angle("sp3"), 109.5, places=1)
        self.assertEqual(_bond_angle("sp3d"), 90.0)
        self.assertEqual(_bond_angle("sp3d2"), 90.0)

    def test_unknown_hybridisation_rejected(self):
        with self.assertRaises(Exception):
            self._render({"hybridisation": "sp4"})


# ── 7. Adsorption Isotherm ────────────────────────────────────────────────────

class TestAdsorptionIsotherm(SimpleTestCase):
    def _render(self, params):
        return render_chemistry("adsorption_isotherm", params)

    def test_every_isotherm_renders(self):
        """Freundlich, Langmuir and BET are three separate surface-chemistry graphs."""
        for iso in ISOTHERMS:
            with self.subTest(isotherm=iso):
                self.assertTrue(_is_valid_svg(self._render({"isotherm": iso})))

    def test_isotherm_toggles_render(self):
        """The linearised-form and physisorption/chemisorption overlays are extra
        annotations that must not break the base drawing."""
        svg = self._render({"isotherm": "langmuir", "show_linearised_form": True,
                            "show_physisorption_chemisorption": True,
                            "show_saturation": True})
        self.assertTrue(_is_valid_svg(svg))

    def test_unknown_isotherm_rejected(self):
        with self.assertRaises(Exception):
            self._render({"isotherm": "temkin"})


# ── Dispatcher + determinism (shared) ─────────────────────────────────────────

class TestChemistryExt2Dispatcher(SimpleTestCase):
    NEW_SUBTYPES = [
        "reaction_scheme", "crystal_field_splitting", "kinetics_graph",
        "colligative_graph", "organic_mechanism", "hybridisation_overlap",
        "adsorption_isotherm",
    ]

    def test_all_seven_subtypes_are_registered(self):
        """The dispatcher is what the AI pipeline calls; an unregistered subtype means
        the LLM can emit a schema nothing will ever render."""
        for subtype in self.NEW_SUBTYPES:
            with self.subTest(subtype=subtype):
                self.assertIn(subtype, CHEMISTRY_RENDERERS)

    def test_renders_are_deterministic(self):
        """Same params → byte-identical SVG (svg.hashsalt pinned, Date suppressed), so a
        cached paper never silently redraws itself."""
        cases = [
            ("reaction_scheme", {"steps": [{"from_label": "A", "to_label": "B"}],
                                 "species": [{"label": "A"}, {"label": "B"}]}),
            ("crystal_field_splitting", {"geometry": "octahedral",
                                         "ligand_field": "strong", "d_electrons": 6}),
            ("kinetics_graph", {"plot": "ln_concentration_time", "order": 1}),
            ("colligative_graph", {"property": "boiling_point_elevation"}),
            ("organic_mechanism", {"mechanism": "e1"}),
            ("hybridisation_overlap", {"hybridisation": "sp2"}),
            ("adsorption_isotherm", {"isotherm": "freundlich"}),
        ]
        for subtype, params in cases:
            with self.subTest(subtype=subtype):
                self.assertEqual(render_chemistry(subtype, params),
                                 render_chemistry(subtype, params))
