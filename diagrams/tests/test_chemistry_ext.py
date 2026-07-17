"""
Unit tests for the extended Chemistry renderers (Solid State, VSEPR, MO, phase,
sugar projections, lab apparatus).

These cover both "does it render" and the chemistry itself: a diagram that renders
cleanly but states the wrong packing efficiency, the wrong MO ordering or a
positively-sloped water fusion curve is worse than no diagram at all, so the facts
are asserted directly on the computed data rather than only on the SVG bytes.

SimpleTestCase: none of this touches the database.
"""
from django.test import SimpleTestCase

from diagrams.service.chemistry.renderer import (
    render_chemistry, _LATTICE_INFO, _lattice_sites, _VSEPR_INFO, _vsepr_frame,
    _build_mo_diagram, _phase_curves, _haworth_layout, _APPARATUS_LABELS,
)
from diagrams.schemas.chemistry import MoDiagramSchema


def _is_valid_svg(content: str) -> bool:
    """Basic SVG validity check."""
    return bool(content and "<svg" in content and "</svg>" in content)


UNIT_CELLS = ["simple_cubic", "bcc", "fcc", "end_centred", "hcp"]
GEOMETRIES = [
    "linear", "bent", "trigonal_planar", "trigonal_pyramidal", "tetrahedral",
    "trigonal_bipyramidal", "see_saw", "t_shaped", "linear_3",
    "octahedral", "square_planar", "square_pyramidal",
]
SETUPS = [
    "simple_distillation", "fractional_distillation", "filtration", "titration",
    "reflux", "steam_distillation", "sublimation", "separating_funnel",
    "chromatography",
]


class TestCrystalLattice(SimpleTestCase):
    def _render(self, params):
        return render_chemistry("crystal_lattice", params)

    def test_every_unit_cell_renders(self):
        """A missing unit cell means the whole Solid State chapter loses its diagrams."""
        for cell in UNIT_CELLS:
            with self.subTest(unit_cell=cell):
                self.assertTrue(_is_valid_svg(self._render({"unit_cell": cell})))

    def test_atoms_drawn_sum_to_z(self):
        """The atoms actually drawn must add up to the Z we print. If this fails the
        picture and the caption disagree and a student counting atoms gets it wrong."""
        for cell in UNIT_CELLS:
            with self.subTest(unit_cell=cell):
                drawn = sum(share for _pos, _role, share in _lattice_sites(cell))
                self.assertAlmostEqual(drawn, _LATTICE_INFO[cell]["z"], places=6)

    def test_fcc_has_four_atoms_and_74_percent_packing(self):
        """FCC: 8 corners (⅛) + 6 faces (½) = Z 4, CN 12, 74 % packing. These three
        numbers are the answer to most FCC questions ever set."""
        info = _LATTICE_INFO["fcc"]
        self.assertEqual(info["z"], 4)
        self.assertEqual(info["cn"], 12)
        self.assertEqual(info["packing"], 74.0)
        sites = _lattice_sites("fcc")
        self.assertEqual(sum(1 for _p, role, _s in sites if role == "corner"), 8)
        self.assertEqual(sum(1 for _p, role, _s in sites if role == "face"), 6)

    def test_bcc_has_one_body_centre_and_68_percent_packing(self):
        """BCC: Z 2, CN 8, 68 %. A body atom drawn anywhere but (½,½,½) is not BCC."""
        self.assertEqual(_LATTICE_INFO["bcc"]["z"], 2)
        self.assertEqual(_LATTICE_INFO["bcc"]["packing"], 68.0)
        body = [p for p, role, _s in _lattice_sites("bcc") if role == "body"]
        self.assertEqual(body, [(0.5, 0.5, 0.5)])

    def test_simple_cubic_is_eight_corners_only(self):
        """Simple cubic: Z 1, CN 6, 52.4 %. Any extra atom turns it into another cell."""
        sites = _lattice_sites("simple_cubic")
        self.assertEqual(len(sites), 8)
        self.assertTrue(all(role == "corner" for _p, role, _s in sites))
        self.assertEqual(_LATTICE_INFO["simple_cubic"]["packing"], 52.4)

    def test_end_centred_has_two_opposite_face_centres(self):
        """End-centred: Z 2, from 8 corners + exactly 2 centres on OPPOSITE faces.
        Adjacent faces would make it a different (non-existent) lattice."""
        faces = [p for p, role, _s in _lattice_sites("end_centred") if role == "face"]
        self.assertEqual(len(faces), 2)
        self.assertEqual(faces, [(0.5, 0.5, 0.0), (0.5, 0.5, 1.0)])
        self.assertEqual(_LATTICE_INFO["end_centred"]["z"], 2)

    def test_hcp_has_three_interior_atoms(self):
        """HCP: 12 corners (⅙) + 2 face centres (½) + 3 wholly-interior atoms = Z 6.
        Dropping the middle layer is the classic way to get Z wrong."""
        sites = _lattice_sites("hcp")
        self.assertEqual(sum(1 for _p, role, _s in sites if role == "corner"), 12)
        self.assertEqual(sum(1 for _p, role, _s in sites if role == "body"), 3)
        self.assertEqual(_LATTICE_INFO["hcp"]["z"], 6)
        self.assertEqual(_LATTICE_INFO["hcp"]["cn"], 12)

    def test_annotations_reach_the_svg(self):
        """matplotlib silently drops text drawn outside the axes: if Z / CN / packing
        stop appearing in the SVG the diagram answers nothing."""
        svg = self._render({"unit_cell": "fcc", "show_atoms_per_cell": True,
                            "show_coordination_number": True,
                            "show_packing_efficiency": True})
        self.assertIn("Z = 4", svg)
        self.assertIn("Coordination number = 12", svg)
        self.assertIn("74%", svg)

    def test_atom_label_and_toggles(self):
        svg = self._render({"unit_cell": "bcc", "atom_label": "Fe",
                            "show_edges": False, "show_unit_cell_box": False,
                            "show_atoms_per_cell": False})
        self.assertTrue(_is_valid_svg(svg))

    def test_unknown_unit_cell_rejected(self):
        with self.assertRaises(Exception):
            self._render({"unit_cell": "hexagonal_cubic"})


class TestVseprShape(SimpleTestCase):
    def _render(self, params):
        return render_chemistry("vsepr_shape", params)

    def test_every_geometry_renders(self):
        """One un-renderable geometry silently removes a whole family of VSEPR questions."""
        for geom in GEOMETRIES:
            with self.subTest(geometry=geom):
                svg = self._render({"geometry": geom, "central_atom": "X",
                                    "ligand_atoms": ["F"]})
                self.assertTrue(_is_valid_svg(svg))
                self.assertIn(_VSEPR_INFO[geom]["name"], svg)

    def test_bond_count_matches_geometry(self):
        """Drawing 5 bonds on an octahedron (or 4 on a see-saw) makes the shape a lie."""
        for geom in GEOMETRIES:
            with self.subTest(geometry=geom):
                bonds, _lps = _vsepr_frame(geom, None)
                self.assertEqual(len(bonds), _VSEPR_INFO[geom]["n"])

    def test_tetrahedral_bond_angles_are_109_5(self):
        """Tetrahedral must be a real tetrahedron: every pair of bonds 109.47° apart."""
        import numpy as np
        bonds, _ = _vsepr_frame("tetrahedral", None)
        vecs = [np.array(d) / np.linalg.norm(d) for d, _tag in bonds]
        for i in range(len(vecs)):
            for j in range(i + 1, len(vecs)):
                angle = np.degrees(np.arccos(np.clip(vecs[i] @ vecs[j], -1, 1)))
                self.assertAlmostEqual(angle, 109.47, delta=0.1)

    def test_trigonal_bipyramidal_has_two_axial_three_equatorial(self):
        """Axial vs equatorial IS the JEE question for the TBP family — if the tags go,
        the diagram can no longer be asked about."""
        bonds, _ = _vsepr_frame("trigonal_bipyramidal", None)
        tags = [tag for _d, tag in bonds]
        self.assertEqual(tags.count("ax"), 2)
        self.assertEqual(tags.count("eq"), 3)
        svg = self._render({"geometry": "trigonal_bipyramidal", "central_atom": "P",
                            "ligand_atoms": ["Cl"] * 5})
        self.assertIn(">ax<", svg)
        self.assertIn(">eq<", svg)

    def test_lone_pairs_take_equatorial_slots_in_tbp_family(self):
        """In see-saw / T-shaped / linear (AX₂E₃) the lone pairs sit EQUATORIAL (they
        suffer fewer 90° repulsions). A lone pair placed axially gives the wrong shape."""
        for geom, n_lp in (("see_saw", 1), ("t_shaped", 2), ("linear_3", 3)):
            with self.subTest(geometry=geom):
                _bonds, lps = _vsepr_frame(geom, None)
                self.assertEqual(len(lps), n_lp)
                for lp in lps:
                    self.assertAlmostEqual(lp[2], 0.0, places=6)   # z = 0 → equatorial

    def test_bent_uses_the_supplied_angle(self):
        """H₂O's 104.5° is the whole point of the bent geometry."""
        svg = self._render({"geometry": "bent", "central_atom": "O",
                            "ligand_atoms": ["H", "H"], "bond_angle": 104.5,
                            "lone_pairs": 2})
        self.assertIn("104.5", svg)

    def test_hybridisation_and_lone_pair_toggles(self):
        svg = self._render({"geometry": "octahedral", "central_atom": "S",
                            "ligand_atoms": ["F"] * 6, "hybridisation": "sp³d²",
                            "show_lone_pairs": False})
        self.assertTrue(_is_valid_svg(svg))
        self.assertIn("sp³d²", svg)

    def test_unknown_geometry_rejected(self):
        with self.assertRaises(Exception):
            self._render({"geometry": "pentagonal_planar"})


class TestMoDiagram(SimpleTestCase):
    def _render(self, params):
        return render_chemistry("mo_diagram", params)

    def _built(self, molecule):
        return _build_mo_diagram(MoDiagramSchema(molecule=molecule))

    def _energy(self, built, label):
        return next(lv["energy"] for lv in built["levels"] if lv["label"] == label)

    def test_o2_is_bond_order_two_and_paramagnetic(self):
        """The classic. O₂ has 2 unpaired electrons in π*2p → bond order 2, paramagnetic.
        If this ever reports diamagnetic the diagram contradicts the textbook."""
        built = self._built("O₂")
        self.assertEqual(built["bond_order"], 2.0)
        self.assertEqual(built["unpaired"], 2)
        self.assertEqual(built["magnetism"], "Paramagnetic")
        svg = self._render({"molecule": "O₂"})
        self.assertIn("Bond order = 2", svg)
        self.assertIn("Paramagnetic", svg)

    def test_n2_is_bond_order_three_and_diamagnetic(self):
        """N₂: triple bond, all electrons paired."""
        built = self._built("N₂")
        self.assertEqual(built["bond_order"], 3.0)
        self.assertEqual(built["unpaired"], 0)
        self.assertEqual(built["magnetism"], "Diamagnetic")
        svg = self._render({"molecule": "N₂"})
        self.assertIn("Bond order = 3", svg)
        self.assertIn("Diamagnetic", svg)

    def test_n2_puts_sigma_2pz_above_pi_2p(self):
        """s–p mixing in B₂/C₂/N₂ raises σ2pz ABOVE the π2p pair. Getting this ordering
        wrong is the single most common error in the MO diagram — and it changes the
        predicted magnetic behaviour of B₂ and C₂."""
        n2 = self._built("N₂")
        self.assertGreater(self._energy(n2, "σ2pz"), self._energy(n2, "π2p"))
        self.assertEqual(n2["ladder"], "n2_type")

    def test_o2_puts_sigma_2pz_below_pi_2p(self):
        """From O₂ onwards the 2s–2p gap is too wide for mixing: σ2pz drops below π2p."""
        o2 = self._built("O₂")
        self.assertLess(self._energy(o2, "σ2pz"), self._energy(o2, "π2p"))
        self.assertEqual(o2["ladder"], "o2_type")

    def test_b2_is_paramagnetic_because_of_s_p_mixing(self):
        """B₂ is paramagnetic ONLY because π2p lies below σ2pz — the two π electrons go
        unpaired into the degenerate π. Use the O₂ ladder and B₂ comes out diamagnetic,
        which is wrong. This is the sharpest test of the ordering rule."""
        b2 = self._built("B₂")
        self.assertEqual(b2["magnetism"], "Paramagnetic")
        self.assertEqual(b2["unpaired"], 2)
        self.assertEqual(b2["bond_order"], 1.0)

    def test_c2_is_diamagnetic_with_bond_order_two(self):
        c2 = self._built("C₂")
        self.assertEqual(c2["bond_order"], 2.0)
        self.assertEqual(c2["magnetism"], "Diamagnetic")

    def test_f2_and_he2_bond_orders(self):
        """F₂ single bond; He₂ bond order 0 — which is WHY He₂ does not exist."""
        self.assertEqual(self._built("F₂")["bond_order"], 1.0)
        self.assertEqual(self._built("He₂")["bond_order"], 0.0)

    def test_heteronuclear_co_and_no(self):
        """CO (14 e⁻) keeps the N₂ ordering; NO (15 e⁻) uses the O₂ ordering and comes
        out with the half bond order 2.5 and one unpaired electron in π*."""
        co = self._built("CO")
        self.assertEqual(co["bond_order"], 3.0)
        self.assertEqual(co["ladder"], "n2_type")
        no = self._built("NO")
        self.assertEqual(no["bond_order"], 2.5)
        self.assertEqual(no["unpaired"], 1)
        self.assertEqual(no["magnetism"], "Paramagnetic")
        self.assertEqual(no["ladder"], "o2_type")

    def test_every_builtin_molecule_renders(self):
        for mol in ("H₂", "He₂", "B₂", "C₂", "N₂", "O₂", "F₂", "CO", "NO"):
            with self.subTest(molecule=mol):
                self.assertTrue(_is_valid_svg(self._render({"molecule": mol})))

    def test_explicit_orbitals_override(self):
        svg = self._render({"molecule": "custom", "orbitals": [
            {"label": "σ", "energy": 1.0, "electrons": 2, "orbital_type": "bonding"},
            {"label": "σ*", "energy": 3.0, "electrons": 1, "orbital_type": "antibonding"},
        ]})
        self.assertIn("Bond order = 0.5", svg)
        self.assertIn("Paramagnetic", svg)

    def test_forced_orbital_order(self):
        """The escape hatch must actually move σ2pz, or a teacher can't correct us."""
        forced = _build_mo_diagram(MoDiagramSchema(molecule="O₂", orbital_order="n2_type"))
        self.assertGreater(self._energy(forced, "σ2pz"), self._energy(forced, "π2p"))

    def test_unknown_molecule_rejected(self):
        with self.assertRaises(ValueError):
            self._render({"molecule": "XeF₆"})


class TestPhaseDiagram(SimpleTestCase):
    def _render(self, params):
        return render_chemistry("phase_diagram", params)

    def test_every_substance_renders(self):
        for sub in ("water", "co2", "generic"):
            with self.subTest(substance=sub):
                self.assertTrue(_is_valid_svg(self._render({"substance": sub})))

    def test_water_fusion_curve_has_negative_slope(self):
        """Ice is less dense than liquid water, so ΔV_fusion < 0 and dP/dT < 0: raising
        the pressure LOWERS the melting point. A left-leaning fusion line is the entire
        content of the water phase diagram — if this flips, the diagram is a lie."""
        t, p = _phase_curves("water")["fusion"]
        self.assertGreater(p[-1], p[0])          # pressure increases along the curve
        self.assertLess(t[-1], t[0])             # …while temperature falls
        slope = (p[-1] - p[0]) / (t[-1] - t[0])
        self.assertLess(slope, 0)

    def test_co2_fusion_curve_has_positive_slope(self):
        """CO₂ (like nearly everything else) expands on melting → dP/dT > 0. The contrast
        with water is exactly what the question tests."""
        t, p = _phase_curves("co2")["fusion"]
        self.assertGreater(p[-1], p[0])
        self.assertGreater(t[-1], t[0])
        slope = (p[-1] - p[0]) / (t[-1] - t[0])
        self.assertGreater(slope, 0)

    def test_generic_fusion_slope_is_positive(self):
        t, _p = _phase_curves("generic")["fusion"]
        self.assertGreater(t[-1], t[0])

    def test_co2_triple_point_is_above_one_atmosphere(self):
        """CO₂'s triple point is at 5.11 atm, so at 1 atm the solid goes straight to gas:
        dry ice sublimes and liquid CO₂ cannot exist at atmospheric pressure."""
        t_tp, p_tp = _phase_curves("co2")["triple"]
        self.assertGreater(p_tp, 1.0)
        self.assertAlmostEqual(p_tp, 5.11, places=2)
        self.assertIn("sublimes", self._render({"substance": "co2"}))

    def test_water_triple_point_is_below_one_atmosphere(self):
        """Water's triple point sits below 1 atm, which is why ice melts (rather than
        subliming) at atmospheric pressure."""
        _t_tp, p_tp = _phase_curves("water")["triple"]
        self.assertLess(p_tp, 1.0)

    def test_co2_sublimation_curve_passes_through_minus_78_5_at_one_atm(self):
        """Dry ice sublimes at −78.5 °C at 1 atm — the number students are asked for."""
        import numpy as np
        t, p = _phase_curves("co2")["sublimation"]
        t_at_1atm = float(np.interp(1.0, p, t))
        self.assertAlmostEqual(t_at_1atm, -78.5, delta=1.5)

    def test_water_vaporisation_curve_passes_through_100c_at_one_atm(self):
        """The normal boiling point must land on the 1 atm line, or the curve is decorative."""
        import numpy as np
        t, p = _phase_curves("water")["vaporisation"]
        t_at_1atm = float(np.interp(1.0, p, t))
        self.assertAlmostEqual(t_at_1atm, 100.0, delta=1.0)

    def test_highlight_transition_aliases(self):
        for transition in ("sublimation", "vaporisation", "boiling", "fusion", "melting"):
            with self.subTest(transition=transition):
                svg = self._render({"substance": "water",
                                    "highlight_transition": transition})
                self.assertTrue(_is_valid_svg(svg))

    def test_region_labels_reach_the_svg(self):
        svg = self._render({"substance": "water", "show_regions": True})
        for region in ("Solid", "Liquid", "Gas"):
            self.assertIn(region, svg)

    def test_point_toggles(self):
        svg = self._render({"substance": "water", "show_triple_point": False,
                            "show_critical_point": False, "show_regions": False})
        self.assertTrue(_is_valid_svg(svg))

    def test_unknown_substance_rejected(self):
        with self.assertRaises(Exception):
            self._render({"substance": "ammonia"})


class TestHaworthFischer(SimpleTestCase):
    def _render(self, params):
        return render_chemistry("haworth_fischer", params)

    def test_every_molecule_and_projection_renders(self):
        for mol in ("glucose", "fructose", "ribose", "galactose", "generic"):
            for proj in ("fischer", "haworth"):
                with self.subTest(molecule=mol, projection=proj):
                    self.assertTrue(_is_valid_svg(
                        self._render({"projection": proj, "molecule": mol})))

    def test_alpha_and_beta_put_the_anomeric_oh_on_opposite_sides(self):
        """α-D → anomeric OH BELOW the ring plane, β-D → ABOVE. This one bond direction
        is the difference between the two anomers and is what the question asks."""
        alpha = _haworth_layout("glucose", None, "alpha")
        beta = _haworth_layout("glucose", None, "beta")
        a_dir = next(g["direction"] for g in alpha["groups"] if g["anomeric"])
        b_dir = next(g["direction"] for g in beta["groups"] if g["anomeric"])
        self.assertEqual(a_dir, "down")
        self.assertEqual(b_dir, "up")
        self.assertNotEqual(a_dir, b_dir)

    def test_anomeric_direction_is_annotated_in_the_svg(self):
        alpha = self._render({"projection": "haworth", "molecule": "glucose",
                              "anomer": "alpha"})
        beta = self._render({"projection": "haworth", "molecule": "glucose",
                             "anomer": "beta"})
        self.assertIn("anomeric OH (DOWN)", alpha)
        self.assertIn("anomeric OH (UP)", beta)
        self.assertNotEqual(alpha, beta)

    def test_anomeric_h_is_opposite_to_the_anomeric_oh(self):
        """The anomeric carbon carries OH and H on opposite faces; drawing both on the
        same side would be a pentavalent carbon."""
        for anomer in ("alpha", "beta"):
            with self.subTest(anomer=anomer):
                groups = [g for g in _haworth_layout("glucose", None, anomer)["groups"]
                          if g["vertex"] == 0]
                self.assertEqual(len(groups), 2)
                self.assertNotEqual(groups[0]["direction"], groups[1]["direction"])

    def test_glucose_haworth_substituent_pattern(self):
        """From the Fischer → Haworth rule (right → down, left → up): glucose is
        C2 down, C3 up, C4 down, with the D-sugar's CH₂OH up at C5."""
        groups = {g["carbon"]: g["direction"]
                  for g in _haworth_layout("glucose", None, "beta")["groups"]
                  if not g["anomeric"] and g["vertex"] != 0}
        self.assertEqual(groups["C2"], "down")
        self.assertEqual(groups["C3"], "up")
        self.assertEqual(groups["C4"], "down")
        self.assertEqual(groups["C5"], "up")

    def test_galactose_differs_from_glucose_at_c4_only(self):
        """Galactose is the C4 epimer of glucose: exactly one OH flips. If more than one
        differs, one of the two sugars is drawn wrong."""
        def pattern(mol):
            return {g["carbon"]: g["direction"]
                    for g in _haworth_layout(mol, None, "beta")["groups"]
                    if not g["anomeric"] and g["vertex"] != 0}
        glu, gal = pattern("glucose"), pattern("galactose")
        differing = [c for c in glu if glu[c] != gal[c]]
        self.assertEqual(differing, ["C4"])
        self.assertEqual(gal["C4"], "up")

    def test_fructose_and_ribose_use_furanose_rings(self):
        """Fructose and ribose cyclise to 5-membered rings; drawing them as pyranoses
        puts the ring oxygen on the wrong carbon."""
        for mol in ("fructose", "ribose"):
            with self.subTest(molecule=mol):
                self.assertEqual(_haworth_layout(mol, None, "alpha")["ring"], "furanose")
        self.assertEqual(_haworth_layout("glucose", None, "alpha")["ring"], "pyranose")

    def test_fischer_shows_the_open_chain_carbonyl(self):
        """Fischer = open chain: an aldose must show CHO at the top, a ketose CH₂OH."""
        svg = self._render({"projection": "fischer", "molecule": "glucose"})
        self.assertIn("CHO", svg)
        self.assertIn("CH₂OH", svg)

    def test_ring_size_override_and_no_anomer(self):
        svg = self._render({"projection": "haworth", "molecule": "ribose",
                            "ring_size": "furanose", "anomer": "none",
                            "show_carbon_numbers": False})
        self.assertTrue(_is_valid_svg(svg))

    def test_explicit_substituent_override(self):
        svg = self._render({"projection": "haworth", "molecule": "glucose",
                            "anomer": "beta",
                            "substituents": ["OMe", "H", "OH", "OH", "OH", "CH₂OH"]})
        self.assertIn("OMe", svg)

    def test_unknown_projection_rejected(self):
        with self.assertRaises(Exception):
            self._render({"projection": "chair"})


class TestLabApparatus(SimpleTestCase):
    def _render(self, params):
        return render_chemistry("lab_apparatus", params)

    def test_every_setup_renders(self):
        """Each setup is a distinct practical question; losing one loses that question."""
        for setup in SETUPS:
            with self.subTest(setup=setup):
                self.assertTrue(_is_valid_svg(self._render({"setup": setup})))

    def test_distillation_warns_that_the_bulb_sits_at_the_side_arm(self):
        """The thermometer bulb must be level with the side-arm so it reads the vapour
        leaving the flask. This is a perennial exam trap and the label must survive."""
        for setup in ("simple_distillation", "fractional_distillation"):
            with self.subTest(setup=setup):
                svg = self._render({"setup": setup})
                self.assertIn("BULB level with the side-arm", svg)

    def test_condensers_show_counter_current_water_flow(self):
        """Water in at the lower end, out at the upper end. Both arrows must be drawn or
        the diagram cannot be asked 'which way does the water flow?'."""
        for setup in ("simple_distillation", "fractional_distillation", "reflux",
                      "steam_distillation"):
            with self.subTest(setup=setup):
                svg = self._render({"setup": setup})
                self.assertIn("water in", svg)
                self.assertIn("water out", svg)

    def test_fractional_distillation_shows_the_column(self):
        svg = self._render({"setup": "fractional_distillation"})
        self.assertIn("Fractionating column", svg)

    def test_labels_can_be_overridden(self):
        svg = self._render({"setup": "titration",
                            "labels": {"flask": "Conical flask (25 mL HCl)"}})
        self.assertIn("Conical flask (25 mL HCl)", svg)

    def test_labels_can_be_hidden(self):
        """An unlabelled setup is the "label the apparatus" question — the drawing must
        still render with every caption suppressed."""
        for setup in SETUPS:
            with self.subTest(setup=setup):
                svg = self._render({"setup": setup, "show_labels": False})
                self.assertTrue(_is_valid_svg(svg))
                self.assertNotIn(_APPARATUS_LABELS[setup]["note"], svg)

    def test_custom_title(self):
        svg = self._render({"setup": "reflux", "title": "Refluxing ethanoic acid"})
        self.assertIn("Refluxing ethanoic acid", svg)

    def test_unknown_setup_rejected(self):
        with self.assertRaises(Exception):
            self._render({"setup": "soxhlet"})


class TestChemistryExtDispatcher(SimpleTestCase):
    def test_new_subtypes_are_registered(self):
        """The dispatcher is what the AI pipeline calls; an unregistered subtype means
        the LLM can emit a schema nothing will ever render."""
        from diagrams.service.chemistry.renderer import CHEMISTRY_RENDERERS
        for subtype in ("crystal_lattice", "vsepr_shape", "mo_diagram",
                        "phase_diagram", "haworth_fischer", "lab_apparatus"):
            with self.subTest(subtype=subtype):
                self.assertIn(subtype, CHEMISTRY_RENDERERS)

    def test_renders_are_deterministic(self):
        """Same params → byte-identical SVG, so cached papers never drift."""
        for subtype, params in (
            ("crystal_lattice", {"unit_cell": "fcc"}),
            ("vsepr_shape", {"geometry": "octahedral"}),
            ("mo_diagram", {"molecule": "O₂"}),
            ("phase_diagram", {"substance": "water"}),
            ("haworth_fischer", {"projection": "haworth", "molecule": "glucose"}),
            ("lab_apparatus", {"setup": "titration"}),
        ):
            with self.subTest(subtype=subtype):
                self.assertEqual(render_chemistry(subtype, params),
                                 render_chemistry(subtype, params))
