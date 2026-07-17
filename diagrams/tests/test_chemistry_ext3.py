"""
Unit tests for the THIRD wave of extended Chemistry renderers:
electrolytic_cell, ionic_lattice, solid_defects, complex_isomerism,
polymer_structure, metallurgy_flowchart, industrial_process, protein_structure,
hydrogen_bonding, resonance_structures, free_radical_mechanism.

As with the earlier waves, a diagram that renders cleanly but states the WRONG
chemistry (a radius ratio of 0.95 drawn as 6-coordinate NaCl, a Frenkel defect
claiming the density drops, a tetrahedral MA2B2 with "cis"/"trans" labels, the
Haber catalyst printed as Pt) is worse than no diagram at all. So the chemistry
is asserted on the values the helpers COMPUTE / ENCODE, and the SVG is only
smoke-tested so every enum value is known to render.

SimpleTestCase: none of this touches the database. Run with plain unittest
(NOT manage.py test): after `django.setup()`,
    unittest ... diagrams.tests.test_chemistry_ext3
"""
from django.test import SimpleTestCase

from diagrams.service.chemistry.renderer import (
    render_chemistry, CHEMISTRY_RENDERERS,
    _radius_ratio_geometry, _ionic_lattice_build,
    _defect_density, _DEFECT_INFO,
    _cis_trans_isomers, _fac_mer_isomers,
    _INDUSTRIAL_DB, _ellingham_crossover, _ellingham_dg,
    _electrolysis_facts, _POLYMER_DB,
)
from diagrams.schemas.chemistry import IonicLatticeSchema, ElectrolyticCellSchema


def _is_valid_svg(content: str) -> bool:
    return bool(content and "<svg" in content and "</svg>" in content)


# ── every enum value, mirrored next to its schema ────────────────────────────
ELECTROLYTES = ["molten NaCl", "aqueous NaCl", "aqueous CuSO₄",
                "molten Al₂O₃", "acidified water"]
IONIC_LATTICES = ["nacl", "cscl", "zns_blende", "zns_wurtzite", "fluorite",
                  "antifluorite"]
DEFECTS = ["schottky", "frenkel", "interstitial", "substitutional", "f_centre"]
ISOMERISMS = ["cis_trans", "fac_mer", "optical", "linkage", "ionisation",
              "coordination"]
ISOMER_GEOMETRIES = ["octahedral", "square_planar", "tetrahedral"]
POLYMERS = ["polythene", "pvc", "nylon-6,6", "terylene", "bakelite",
            "natural_rubber"]
METALLURGY = ["froth_flotation", "roasting", "calcination", "smelting",
              "refining", "full_extraction"]
INDUSTRIAL = ["haber", "contact", "ostwald", "solvay", "chlor_alkali"]
PROTEIN_LEVELS = ["primary", "secondary_helix", "secondary_sheet", "tertiary",
                  "peptide_bond"]
HBOND_SUBSTANCES = ["water", "ice", "hf", "ammonia", "dna_base_pair", "ethanol"]
RESONANCE_SPECIES = ["benzene", "carbonate", "nitrate", "ozone"]
FREE_RADICAL = ["methane_chlorination", "methane_bromination",
                "ethane_chlorination", "chlorination_of_alkane"]

NEW_SUBTYPES = [
    "electrolytic_cell", "ionic_lattice", "solid_defects", "complex_isomerism",
    "polymer_structure", "metallurgy_flowchart", "industrial_process",
    "protein_structure", "hydrogen_bonding", "resonance_structures",
    "free_radical_mechanism",
]


# ── 1. Electrolytic Cell ──────────────────────────────────────────────────────

class TestElectrolyticCell(SimpleTestCase):
    def test_every_electrolyte_renders(self):
        """Each electrolyte is a separate electrolysis question; one that will not
        render deletes that scenario."""
        for e in ELECTROLYTES:
            with self.subTest(electrolyte=e):
                self.assertTrue(_is_valid_svg(render_chemistry(
                    "electrolytic_cell", {"electrolyte": e})))

    def test_brine_gives_hydrogen_and_chlorine_not_sodium(self):
        """Aqueous NaCl (brine) discharges H₂ at the cathode and Cl₂ at the anode
        (over-potential), NOT sodium metal. If this drifts to 'Na', the electrolysis
        answer is chemically wrong."""
        f = _electrolysis_facts(ElectrolyticCellSchema(electrolyte="aqueous NaCl"))
        self.assertIn("H₂", f["cathode_product"])
        self.assertIn("Cl₂", f["anode_product"])
        self.assertNotIn("Na", f["cathode_product"])

    def test_molten_nacl_gives_sodium_metal(self):
        """With no water present, molten NaCl DOES deposit Na at the cathode — the
        contrast with brine is the whole point."""
        f = _electrolysis_facts(ElectrolyticCellSchema(electrolyte="molten NaCl"))
        self.assertIn("Na", f["cathode_product"])
        self.assertIn("Cl₂", f["anode_product"])

    def test_overrides_win_over_database(self):
        """Explicit params must override the built-in electrolyte chemistry, so an
        unusual cell can still be drawn correctly."""
        f = _electrolysis_facts(ElectrolyticCellSchema(
            electrolyte="molten NaCl", cathode_product="X", anode_product="Y"))
        self.assertEqual(f["cathode_product"], "X")
        self.assertEqual(f["anode_product"], "Y")


# ── 2. Ionic Lattice + radius-ratio rule ──────────────────────────────────────

class TestIonicLattice(SimpleTestCase):
    def test_every_lattice_renders(self):
        """Each lattice type is a distinct solid-state question."""
        for lt in IONIC_LATTICES:
            with self.subTest(lattice=lt):
                self.assertTrue(_is_valid_svg(render_chemistry(
                    "ionic_lattice", {"lattice_type": lt})))

    def test_radius_ratio_0_52_predicts_six_coordinate_nacl(self):
        """r₊/r₋ = 0.52 lies in 0.414–0.732 → 6-coordinate octahedral (NaCl-type).
        This IS the standard radius-ratio question; a wrong band gives a wrong C.N."""
        g = _radius_ratio_geometry(0.52)
        self.assertEqual(g["cn"], 6)
        self.assertEqual(g["lattice_hint"], "nacl")

    def test_radius_ratio_0_95_predicts_eight_coordinate_cscl(self):
        """r₊/r₋ = 0.95 (> 0.732) → 8-coordinate cubic (CsCl-type). The mirror of the
        NaCl case."""
        g = _radius_ratio_geometry(0.95)
        self.assertEqual(g["cn"], 8)
        self.assertEqual(g["lattice_hint"], "cscl")

    def test_radius_ratio_band_boundaries(self):
        """The 0.225 / 0.414 / 0.732 thresholds separate 4-, 6- and 8-coordination.
        A shifted boundary silently reclassifies borderline ionic solids."""
        self.assertEqual(_radius_ratio_geometry(0.30)["cn"], 4)   # 0.225–0.414
        self.assertEqual(_radius_ratio_geometry(0.732)["cn"], 8)  # exactly at boundary
        self.assertEqual(_radius_ratio_geometry(0.414)["cn"], 6)

    def test_build_flags_consistency_with_lattice(self):
        """A supplied ratio is checked against the drawn lattice's cation C.N.; 0.52 is
        consistent with NaCl (C.N. 6) but NOT with CsCl (C.N. 8). If this flag is
        wrong the diagram would endorse an impossible structure."""
        b_ok = _ionic_lattice_build(IonicLatticeSchema(lattice_type="nacl",
                                                       radius_ratio=0.52))
        self.assertTrue(b_ok["radius_ratio_matches"])
        self.assertEqual(b_ok["cation_cn"], 6)
        b_bad = _ionic_lattice_build(IonicLatticeSchema(lattice_type="cscl",
                                                        radius_ratio=0.52))
        self.assertFalse(b_bad["radius_ratio_matches"])

    def test_coordination_numbers_are_encoded_correctly(self):
        """Rock-salt 6:6, CsCl 8:8, blende 4:4, fluorite 8:4, antifluorite 4:8 — the
        canonical coordination facts every question relies on."""
        cases = {"nacl": (6, 6), "cscl": (8, 8), "zns_blende": (4, 4),
                 "fluorite": (8, 4), "antifluorite": (4, 8)}
        for lt, (c_cn, a_cn) in cases.items():
            with self.subTest(lattice=lt):
                b = _ionic_lattice_build(IonicLatticeSchema(lattice_type=lt))
                self.assertEqual(b["cation_cn"], c_cn)
                self.assertEqual(b["anion_cn"], a_cn)

    def test_alias_normalisation(self):
        """The LLM may say 'rock_salt' or 'zinc_blende'; the schema must map them."""
        self.assertEqual(IonicLatticeSchema(lattice_type="rock salt").lattice_type,
                         "nacl")
        self.assertEqual(IonicLatticeSchema(lattice_type="zinc blende").lattice_type,
                         "zns_blende")


# ── 3. Solid Defects (density is the exam answer) ─────────────────────────────

class TestSolidDefects(SimpleTestCase):
    def test_every_defect_renders(self):
        for d in DEFECTS:
            with self.subTest(defect=d):
                self.assertTrue(_is_valid_svg(render_chemistry(
                    "solid_defects", {"defect": d})))

    def test_schottky_decreases_density_frenkel_unchanged(self):
        """Schottky removes a matched cation+anion PAIR → density DECREASES; Frenkel
        merely relocates a cation to an interstitial → density UNCHANGED. This exact
        contrast is the most-asked solid-state question."""
        self.assertEqual(_defect_density("schottky"), "decreases")
        self.assertEqual(_defect_density("frenkel"), "unchanged")

    def test_interstitial_increases_density(self):
        """An extra interstitial atom adds mass at constant volume → density UP."""
        self.assertEqual(_defect_density("interstitial"), "increases")

    def test_f_centre_decreases_density_and_is_a_colour_centre(self):
        """An F-centre is an anion vacancy holding a trapped electron: density drops
        slightly and, crucially, the crystal becomes COLOURED."""
        self.assertEqual(_defect_density("f_centre"), "decreases")
        self.assertIn("COLOUR", _DEFECT_INFO["f_centre"]["note"].upper())


# ── 4. Complex Isomerism (geometry decides which isomers exist) ───────────────

class TestComplexIsomerism(SimpleTestCase):
    def test_every_isomerism_and_geometry_renders(self):
        for iso in ISOMERISMS:
            for g in ISOMER_GEOMETRIES:
                with self.subTest(isomerism=iso, geometry=g):
                    self.assertTrue(_is_valid_svg(render_chemistry(
                        "complex_isomerism", {"isomerism": iso, "geometry": g})))

    def test_octahedral_MA4B2_has_cis_and_trans(self):
        """An octahedral MA₄B₂ (e.g. [Co(NH₃)₄Cl₂]⁺) has two geometric isomers, cis
        and trans. Losing either makes the classic count wrong."""
        self.assertEqual(_cis_trans_isomers("octahedral"), ["cis", "trans"])

    def test_square_planar_MA2B2_has_cis_and_trans(self):
        """Square-planar MA₂B₂ (cisplatin/transplatin) also shows cis and trans."""
        self.assertEqual(_cis_trans_isomers("square_planar"), ["cis", "trans"])

    def test_tetrahedral_MA2B2_has_no_cis_trans(self):
        """A tetrahedral MA₂B₂ has NO cis/trans — all four vertices are mutually
        adjacent. Drawing 'cis'/'trans' for a tetrahedron would assert isomers that
        do not exist."""
        self.assertEqual(_cis_trans_isomers("tetrahedral"), [])

    def test_fac_mer_only_for_octahedral(self):
        """fac/mer isomerism requires an octahedral MA₃B₃; square-planar and
        tetrahedral have none."""
        self.assertEqual(_fac_mer_isomers("octahedral"), ["fac", "mer"])
        self.assertEqual(_fac_mer_isomers("square_planar"), [])
        self.assertEqual(_fac_mer_isomers("tetrahedral"), [])


# ── 5. Polymer Structure ──────────────────────────────────────────────────────

class TestPolymerStructure(SimpleTestCase):
    def test_every_polymer_renders(self):
        for pol in POLYMERS:
            with self.subTest(polymer=pol):
                self.assertTrue(_is_valid_svg(render_chemistry(
                    "polymer_structure", {"polymer": pol})))

    def test_addition_vs_condensation_classification(self):
        """Polythene/PVC/rubber are ADDITION polymers; nylon/terylene/bakelite are
        CONDENSATION. Mis-classifying flips the answer to 'name the type of
        polymerisation'."""
        for pol in ("polythene", "pvc", "natural_rubber"):
            self.assertEqual(_POLYMER_DB[pol]["classification"], "addition")
        for pol in ("nylon-6,6", "terylene", "bakelite"):
            self.assertEqual(_POLYMER_DB[pol]["classification"], "condensation")

    def test_condensation_linkages_are_correct(self):
        """Nylon = amide linkage, Terylene = ester linkage. The linkage name is the
        exam fact for the condensation polymers."""
        self.assertIn("amide", _POLYMER_DB["nylon-6,6"]["linkage"])
        self.assertIn("ester", _POLYMER_DB["terylene"]["linkage"])


# ── 6. Metallurgy Flowchart + Ellingham ───────────────────────────────────────

class TestMetallurgyFlowchart(SimpleTestCase):
    def test_every_process_renders(self):
        for pr in METALLURGY:
            with self.subTest(process=pr):
                self.assertTrue(_is_valid_svg(render_chemistry(
                    "metallurgy_flowchart", {"process": pr})))

    def test_ellingham_renders(self):
        """The Ellingham branch is a separate drawing path."""
        self.assertTrue(_is_valid_svg(render_chemistry(
            "metallurgy_flowchart", {"process": "smelting", "ellingham": True})))

    def test_carbon_reduces_zinc_oxide_only_above_the_crossover(self):
        """The 2C+O₂→2CO line (positive ΔS ⇒ falling ΔG°) crosses the ZnO line near
        1200–1300 K; ONLY above that temperature does carbon become the better
        reductant for ZnO. A wrong sign/slope would put the crossover in the wrong
        place and teach that C reduces ZnO at room temperature."""
        c_dh, c_ds = -221.0, 0.179
        zn_dh, zn_ds = -697.0, -0.201
        t_cross = _ellingham_crossover(c_dh, c_ds, zn_dh, zn_ds)
        self.assertTrue(1100.0 < t_cross < 1400.0)
        # below crossover ZnO is the more stable (lower ΔG°); above, C→CO is lower.
        self.assertLess(_ellingham_dg(zn_dh, zn_ds, t_cross - 300),
                        _ellingham_dg(c_dh, c_ds, t_cross - 300))
        self.assertLess(_ellingham_dg(c_dh, c_ds, t_cross + 300),
                        _ellingham_dg(zn_dh, zn_ds, t_cross + 300))

    def test_carbon_monoxide_line_slopes_downward(self):
        """2C+O₂→2CO has POSITIVE ΔS, so its ΔG° must fall as T rises — the feature
        that makes carbon a universal high-temperature reductant."""
        self.assertGreater(_ellingham_dg(-221.0, 0.179, 400.0),
                           _ellingham_dg(-221.0, 0.179, 1800.0))


# ── 7. Industrial Process (catalyst + conditions are the facts) ───────────────

class TestIndustrialProcess(SimpleTestCase):
    def test_every_process_renders(self):
        for pr in INDUSTRIAL:
            with self.subTest(process=pr):
                self.assertTrue(_is_valid_svg(render_chemistry(
                    "industrial_process", {"process": pr})))

    def test_haber_catalyst_and_conditions(self):
        """Haber: Fe catalyst, 450 °C, 200 atm, N₂ + 3H₂ ⇌ 2NH₃. These four facts are
        exactly what the question asks for."""
        d = _INDUSTRIAL_DB["haber"]
        self.assertTrue(d["catalyst"].startswith("Fe"))
        self.assertEqual(d["temperature"], "450 °C")
        self.assertEqual(d["pressure"], "200 atm")
        self.assertIn("N₂ + 3H₂", d["reaction"])

    def test_contact_uses_vanadium_pentoxide(self):
        """Contact process: V₂O₅ catalyst for 2SO₂ + O₂ ⇌ 2SO₃. Not platinum."""
        d = _INDUSTRIAL_DB["contact"]
        self.assertTrue(d["catalyst"].startswith("V₂O₅"))
        self.assertIn("2SO₂ + O₂", d["reaction"])

    def test_ostwald_uses_platinum(self):
        """Ostwald process: Pt/Rh gauze oxidises NH₃ to NO. The catalyst is Pt-based."""
        d = _INDUSTRIAL_DB["ostwald"]
        self.assertTrue(d["catalyst"].startswith("Pt"))
        self.assertIn("4NH₃ + 5O₂", d["reaction"])

    def test_catalysts_are_all_distinct(self):
        """Fe vs V₂O₅ vs Pt must never be confused between the three processes."""
        cats = {p: _INDUSTRIAL_DB[p]["catalyst"] for p in ("haber", "contact", "ostwald")}
        self.assertEqual(len(set(cats.values())), 3)


# ── 8-11. remaining subtypes: every enum renders ─────────────────────────────

class TestProteinStructure(SimpleTestCase):
    def test_every_level_renders(self):
        for lv in PROTEIN_LEVELS:
            with self.subTest(level=lv):
                self.assertTrue(_is_valid_svg(render_chemistry(
                    "protein_structure", {"level": lv})))


class TestHydrogenBonding(SimpleTestCase):
    def test_every_substance_renders(self):
        for sub in HBOND_SUBSTANCES:
            with self.subTest(substance=sub):
                self.assertTrue(_is_valid_svg(render_chemistry(
                    "hydrogen_bonding", {"substance": sub})))


class TestResonanceStructures(SimpleTestCase):
    def test_every_species_renders(self):
        for sp in RESONANCE_SPECIES:
            with self.subTest(species=sp):
                self.assertTrue(_is_valid_svg(render_chemistry(
                    "resonance_structures", {"species": sp})))

    def test_hybrid_toggle_renders(self):
        """The optional resonance-hybrid panel is an extra drawing path."""
        for sp in RESONANCE_SPECIES:
            self.assertTrue(_is_valid_svg(render_chemistry(
                "resonance_structures", {"species": sp, "show_hybrid": True})))


class TestFreeRadicalMechanism(SimpleTestCase):
    def test_every_reaction_renders(self):
        for r in FREE_RADICAL:
            with self.subTest(reaction=r):
                self.assertTrue(_is_valid_svg(render_chemistry(
                    "free_radical_mechanism", {"reaction": r})))

    def test_two_phases_only_toggle(self):
        """show_all_phases=False must still render (initiation + propagation only)."""
        self.assertTrue(_is_valid_svg(render_chemistry(
            "free_radical_mechanism",
            {"reaction": "methane_chlorination", "show_all_phases": False})))


# ── Dispatcher + determinism (shared) ────────────────────────────────────────

class TestChemistryExt3Dispatcher(SimpleTestCase):
    def test_all_eleven_subtypes_registered(self):
        """The dispatcher is what the AI pipeline calls; an unregistered subtype means
        the LLM can emit a schema nothing will render."""
        for st in NEW_SUBTYPES:
            with self.subTest(subtype=st):
                self.assertIn(st, CHEMISTRY_RENDERERS)

    def test_existing_registry_preserved(self):
        """The third wave only APPENDS; it must not evict earlier work such as the
        shared annotated_xy_graph or the galvanic electrochemical_cell."""
        self.assertIn("annotated_xy_graph", CHEMISTRY_RENDERERS)
        self.assertIn("electrochemical_cell", CHEMISTRY_RENDERERS)

    def test_renders_are_deterministic(self):
        """Same params → byte-identical SVG (svg.hashsalt pinned, Date suppressed),
        including the RDKit polymer path, so a cached paper never silently redraws."""
        cases = [
            ("electrolytic_cell", {"electrolyte": "molten NaCl"}),
            ("ionic_lattice", {"lattice_type": "nacl", "radius_ratio": 0.52}),
            ("solid_defects", {"defect": "frenkel"}),
            ("complex_isomerism", {"isomerism": "fac_mer", "geometry": "octahedral"}),
            ("polymer_structure", {"polymer": "nylon-6,6"}),
            ("metallurgy_flowchart", {"process": "roasting"}),
            ("industrial_process", {"process": "haber"}),
            ("protein_structure", {"level": "peptide_bond"}),
            ("hydrogen_bonding", {"substance": "ice"}),
            ("resonance_structures", {"species": "carbonate"}),
            ("free_radical_mechanism", {"reaction": "methane_chlorination"}),
        ]
        for st, p in cases:
            with self.subTest(subtype=st):
                self.assertEqual(render_chemistry(st, p), render_chemistry(st, p))

    def test_unknown_enums_rejected(self):
        """Bad enum values must raise, not silently draw a blank."""
        with self.assertRaises(Exception):
            render_chemistry("ionic_lattice", {"lattice_type": "perovskite"})
        with self.assertRaises(Exception):
            render_chemistry("industrial_process", {"process": "cracking"})
        with self.assertRaises(Exception):
            render_chemistry("solid_defects", {"defect": "dislocation"})
