"""
Unit tests for rendering engines.
Tests that each renderer produces valid SVG without exceptions.
"""
from django.test import TestCase


def _is_valid_svg(content: str) -> bool:
    """Basic SVG validity check."""
    return bool(content and "<svg" in content and "</svg>" in content)


class TestPhysicsRenderer(TestCase):
    def _render(self, subtype, params):
        from diagrams.service.physics.renderer import render_physics
        return render_physics(subtype, params)

    def test_inclined_plane_30deg(self):
        svg = self._render("inclined_plane", {"angle": 30, "forces": ["mg", "N", "f"]})
        self.assertTrue(_is_valid_svg(svg))

    def test_inclined_plane_45deg(self):
        svg = self._render("inclined_plane", {"angle": 45})
        self.assertTrue(_is_valid_svg(svg))

    def test_inclined_plane_60deg(self):
        svg = self._render("inclined_plane", {"angle": 60})
        self.assertTrue(_is_valid_svg(svg))

    def test_free_body_diagram_square(self):
        svg = self._render("free_body_diagram", {
            "object": {"shape": "square", "label": "m"},
            "forces": [
                {"label": "mg", "direction_deg": 270, "magnitude": 50},
                {"label": "N", "direction_deg": 90},
                {"label": "f", "direction_deg": 0},
            ]
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_free_body_diagram_circle(self):
        svg = self._render("free_body_diagram", {
            "object": {"shape": "circle", "label": "m"},
            "forces": [{"label": "W", "direction_deg": 270}]
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_pulley_system(self):
        svg = self._render("pulley_system", {
            "pulley_count": 1,
            "masses": [{"label": "m₁", "side": "left"}, {"label": "m₂", "side": "right"}]
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_projectile_motion_45(self):
        svg = self._render("projectile_motion", {
            "initial_velocity": 20, "launch_angle": 45,
            "show_components": True, "show_trajectory": True
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_projectile_motion_30(self):
        svg = self._render("projectile_motion", {"initial_velocity": 15, "launch_angle": 30})
        self.assertTrue(_is_valid_svg(svg))

    def test_spring_block_horizontal(self):
        svg = self._render("spring_block", {"orientation": "horizontal", "block_label": "m"})
        self.assertTrue(_is_valid_svg(svg))

    def test_spring_block_vertical(self):
        svg = self._render("spring_block", {"orientation": "vertical", "block_label": "M"})
        self.assertTrue(_is_valid_svg(svg))

    def test_optics_convex_lens(self):
        svg = self._render("optics_convex_lens", {"focal_length": 100, "show_rays": True})
        self.assertTrue(_is_valid_svg(svg))

    def test_optics_concave_mirror(self):
        svg = self._render("optics_concave_mirror", {"focal_length": 110, "show_rays": True})
        self.assertTrue(_is_valid_svg(svg))

    def test_wave_diagram_default(self):
        svg = self._render("wave_diagram", {"amplitude": 80, "num_cycles": 2.5})
        self.assertTrue(_is_valid_svg(svg))

    def test_wave_diagram_1_cycle(self):
        svg = self._render("wave_diagram", {"amplitude": 60, "num_cycles": 1.0})
        self.assertTrue(_is_valid_svg(svg))

    def test_unknown_subtype_raises(self):
        from diagrams.service.physics.renderer import render_physics
        with self.assertRaises(ValueError):
            render_physics("unknown_physics_type", {})

    # ── New physics types ──────────────────────────────────────────────────────

    def test_thermodynamics_pv_carnot_cycle(self):
        svg = self._render("thermodynamics_pv", {
            "states": [
                {"label": "A", "volume": 1.0, "pressure": 10.0},
                {"label": "B", "volume": 3.0, "pressure": 10.0},
                {"label": "C", "volume": 3.0, "pressure": 4.0},
                {"label": "D", "volume": 1.0, "pressure": 4.0},
            ],
            "processes": [
                {"from_state": "A", "to_state": "B", "process_type": "isobaric", "label": "AB"},
                {"from_state": "B", "to_state": "C", "process_type": "isochoric", "label": "BC"},
                {"from_state": "C", "to_state": "D", "process_type": "isobaric", "label": "CD"},
                {"from_state": "D", "to_state": "A", "process_type": "isochoric", "label": "DA"},
            ],
            "title": "P-V Diagram",
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_thermodynamics_pv_isothermal(self):
        svg = self._render("thermodynamics_pv", {
            "states": [
                {"label": "A", "volume": 1.0, "pressure": 8.0},
                {"label": "B", "volume": 4.0, "pressure": 2.0},
            ],
            "processes": [{"from_state": "A", "to_state": "B", "process_type": "isothermal"}],
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_ray_optics_prism_default(self):
        svg = self._render("ray_optics_prism", {
            "prism_angle": 60.0,
            "incident_angle": 45.0,
            "refractive_index": 1.5,
            "show_normals": True,
            "show_angles": True,
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_ray_optics_prism_glass(self):
        svg = self._render("ray_optics_prism", {
            "prism_angle": 45.0,
            "incident_angle": 40.0,
            "refractive_index": 1.6,
            "label_deviation": True,
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_electric_field_dipole(self):
        svg = self._render("electric_field_lines", {
            "field_type": "point_charges",
            "charges": [
                {"x": -1.0, "y": 0.0, "charge": 1.0, "label": "+q"},
                {"x":  1.0, "y": 0.0, "charge": -1.0, "label": "-q"},
            ],
            "num_lines": 8,
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_electric_field_uniform(self):
        svg = self._render("electric_field_lines", {
            "field_type": "uniform",
            "charges": [],
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_magnetic_field_bar_magnet(self):
        svg = self._render("magnetic_field_lines", {
            "source_type": "bar_magnet",
            "label_poles": True,
            "num_field_lines": 8,
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_magnetic_field_solenoid(self):
        svg = self._render("magnetic_field_lines", {
            "source_type": "solenoid",
            "label_poles": True,
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_magnetic_field_straight_wire(self):
        svg = self._render("magnetic_field_lines", {
            "source_type": "straight_wire",
            "current_direction": "out",
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_circular_motion_default(self):
        svg = self._render("circular_motion", {
            "show_velocity": True,
            "show_centripetal": True,
            "object_angle_deg": 45.0,
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_circular_motion_with_omega(self):
        svg = self._render("circular_motion", {
            "show_velocity": True,
            "show_centripetal": True,
            "show_angular_velocity": True,
            "object_angle_deg": 90.0,
        })
        self.assertTrue(_is_valid_svg(svg))


class TestChemistryRenderer(TestCase):
    def _render(self, subtype, params):
        from diagrams.service.chemistry.renderer import render_chemistry
        return render_chemistry(subtype, params)

    def test_organic_ethanol_fallback(self):
        # Works with or without RDKit
        svg = self._render("organic_structure", {"smiles": "CCO", "name": "Ethanol"})
        self.assertTrue(_is_valid_svg(svg))

    def test_organic_benzene(self):
        svg = self._render("organic_structure", {"smiles": "c1ccccc1", "name": "Benzene"})
        self.assertTrue(_is_valid_svg(svg))

    def test_inorganic_h2o(self):
        svg = self._render("inorganic_structure", {
            "atoms": [
                {"symbol": "O", "label": "O"},
                {"symbol": "H", "label": "H"},
                {"symbol": "H", "label": "H"},
            ],
            "bonds": [
                {"from_atom": 0, "to_atom": 1, "bond_type": "single"},
                {"from_atom": 0, "to_atom": 2, "bond_type": "single"},
            ],
            "title": "Water (H₂O)",
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_inorganic_double_bond(self):
        svg = self._render("inorganic_structure", {
            "atoms": [
                {"symbol": "C", "label": "C"},
                {"symbol": "O", "label": "O"},
            ],
            "bonds": [{"from_atom": 0, "to_atom": 1, "bond_type": "double"}],
            "title": "CO",
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_reaction_coordinate_exothermic(self):
        svg = self._render("reaction_coordinate_graph", {
            "reactant_energy": 0,
            "product_energy": -40,
            "activation_energy": 80,
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_reaction_coordinate_endothermic(self):
        svg = self._render("reaction_coordinate_graph", {
            "reactant_energy": 0,
            "product_energy": 30,
            "activation_energy": 60,
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_orbital_diagram_carbon(self):
        svg = self._render("orbital_diagram", {
            "element": "Carbon",
            "electron_config": [
                {"shell": "1s", "electrons": 2, "max_electrons": 2, "sublevel_count": 1},
                {"shell": "2s", "electrons": 2, "max_electrons": 2, "sublevel_count": 1},
                {"shell": "2p", "electrons": 2, "max_electrons": 6, "sublevel_count": 3},
            ],
        })
        self.assertTrue(_is_valid_svg(svg))


class TestMathematicsRenderer(TestCase):
    def _render(self, subtype, params):
        from diagrams.service.mathematics.renderer import render_mathematics
        return render_mathematics(subtype, params)

    def test_function_graph_parabola(self):
        svg = self._render("function_graph", {
            "functions": [{"expression": "x**2", "label": "y = x²", "x_range": [-4, 4]}],
            "x_range": [-4, 4],
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_function_graph_sine(self):
        svg = self._render("function_graph", {
            "functions": [{"expression": "sin(x)", "label": "sin(x)", "x_range": [-6.28, 6.28]}],
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_function_graph_multiple(self):
        svg = self._render("function_graph", {
            "functions": [
                {"expression": "x**2", "label": "f(x)=x²", "x_range": [-3, 3]},
                {"expression": "2*x + 1", "label": "g(x)=2x+1", "x_range": [-3, 3]},
            ],
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_geometry_triangle(self):
        svg = self._render("geometry_triangle", {
            "vertices": [
                {"label": "A", "x": 0.0, "y": 0.0},
                {"label": "B", "x": 4.0, "y": 0.0},
                {"label": "C", "x": 2.0, "y": 3.0},
            ],
            "sides": [
                {"label": "a", "length": 4},
                {"label": "b"},
                {"label": "c"},
            ],
            "angles": [60, 60, 60],
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_geometry_circle(self):
        svg = self._render("geometry_circle", {
            "show_radius": True,
            "show_diameter": True,
            "arc_angle": 90,
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_coordinate_geometry_line(self):
        svg = self._render("coordinate_geometry", {
            "lines": [{"slope": 2, "intercept": -1, "label": "y=2x-1"}],
            "points": [{"x": 0, "y": -1, "label": "(0,-1)"}],
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_calculus_graph_shaded(self):
        svg = self._render("calculus_graph", {
            "function": "x**2 - 4",
            "x_range": [-3, 3],
            "shaded_regions": [{"x_from": -2, "x_to": 2, "label": "∫", "color": "lightblue"}],
            "label_zeros": True,
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_calculus_with_derivative(self):
        svg = self._render("calculus_graph", {
            "function": "x**3 - 3*x",
            "show_derivative": True,
            "label_extrema": True,
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_calculus_with_tangent(self):
        svg = self._render("calculus_graph", {
            "function": "x**2",
            "show_tangent_at": 1.0,
        })
        self.assertTrue(_is_valid_svg(svg))

    # ── New mathematics types ──────────────────────────────────────────────────

    def test_conic_section_ellipse(self):
        svg = self._render("conic_section", {
            "conic_type": "ellipse",
            "a": 5.0, "b": 3.0,
            "orientation": "horizontal",
            "show_foci": True,
            "show_vertices": True,
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_conic_section_parabola(self):
        svg = self._render("conic_section", {
            "conic_type": "parabola",
            "a": 2.0,
            "orientation": "horizontal",
            "show_foci": True,
            "show_directrix": True,
            "title": "y² = 8x",
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_conic_section_hyperbola(self):
        svg = self._render("conic_section", {
            "conic_type": "hyperbola",
            "a": 3.0, "b": 4.0,
            "orientation": "horizontal",
            "show_asymptotes": True,
            "show_foci": True,
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_conic_section_circle(self):
        svg = self._render("conic_section", {
            "conic_type": "circle",
            "a": 4.0,
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_venn_diagram_two_sets(self):
        svg = self._render("venn_diagram", {
            "sets": [
                {"label": "A", "region_value": "5"},
                {"label": "B", "region_value": "7"},
            ],
            "intersection_labels": ["3"],
            "universal_set_label": "U",
            "title": "Sets A and B",
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_venn_diagram_three_sets(self):
        svg = self._render("venn_diagram", {
            "sets": [
                {"label": "P", "region_value": "2"},
                {"label": "Q", "region_value": "4"},
                {"label": "R", "region_value": "1"},
            ],
            "intersection_labels": ["a", "b", "c", "d"],
            "title": "Three-Set Venn",
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_number_line_points(self):
        svg = self._render("number_line", {
            "x_min": -3.0,
            "x_max": 5.0,
            "points": [
                {"value": -1.0, "label": "-1", "filled": False},
                {"value": 3.0,  "label": "3",  "filled": True},
            ],
            "title": "Solution set",
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_number_line_interval(self):
        svg = self._render("number_line", {
            "x_min": -5.0,
            "x_max": 5.0,
            "intervals": [
                {"start": -2.0, "end": 3.0, "filled_start": False, "filled_end": True, "color": "blue"},
            ],
        })
        self.assertTrue(_is_valid_svg(svg))


class TestChemistryNewRenderers(TestCase):
    def _render(self, subtype, params):
        from diagrams.service.chemistry.renderer import render_chemistry
        return render_chemistry(subtype, params)

    def test_electrochemical_cell_daniell(self):
        svg = self._render("electrochemical_cell", {
            "anode_material": "Zn",
            "anode_ion": "Zn²⁺",
            "anode_solution": "ZnSO₄",
            "cathode_material": "Cu",
            "cathode_ion": "Cu²⁺",
            "cathode_solution": "CuSO₄",
            "cell_name": "Daniell Cell",
            "emf": 1.10,
            "show_salt_bridge": True,
            "show_current": True,
            "show_half_reactions": True,
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_electrochemical_cell_no_emf(self):
        svg = self._render("electrochemical_cell", {
            "cell_name": "Generic Cell",
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_equilibrium_graph_basic(self):
        svg = self._render("equilibrium_graph", {
            "reactant_labels": ["[A]", "[B]"],
            "product_labels": ["[C]"],
            "equilibrium_time": 0.5,
            "show_kc_marker": True,
            "title": "Equilibrium Graph",
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_equilibrium_graph_single_product(self):
        svg = self._render("equilibrium_graph", {
            "reactant_labels": ["[N₂]", "[H₂]"],
            "product_labels": ["[NH₃]"],
            "equilibrium_time": 0.4,
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_titration_strong_strong(self):
        svg = self._render("titration_curve", {
            "acid_type": "strong",
            "base_type": "strong",
            "initial_ph": 1.0,
            "equivalence_ph": 7.0,
            "final_ph": 13.0,
            "titrant_label": "NaOH",
            "analyte_label": "HCl",
            "show_equivalence_point": True,
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_titration_weak_acid(self):
        svg = self._render("titration_curve", {
            "acid_type": "weak",
            "base_type": "strong",
            "initial_ph": 3.0,
            "equivalence_ph": 8.7,
            "final_ph": 13.0,
            "titrant_label": "NaOH",
            "analyte_label": "CH₃COOH",
            "show_equivalence_point": True,
            "show_half_equivalence": True,
        })
        self.assertTrue(_is_valid_svg(svg))


class TestCircuitRenderer(TestCase):
    def _render(self, subtype, params):
        from diagrams.service.circuits.renderer import render_circuits
        return render_circuits(subtype, params)

    def test_resistor_series(self):
        svg = self._render("resistor_network", {
            "topology": "series",
            "resistors": ["R1=2Ω", "R2=3Ω", "R3=5Ω"],
            "voltage_source": "12V",
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_resistor_parallel(self):
        svg = self._render("resistor_network", {
            "topology": "parallel",
            "resistors": ["4Ω", "6Ω"],
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_capacitor_series(self):
        svg = self._render("capacitor_network", {
            "topology": "series",
            "capacitors": ["C1=10μF", "C2=20μF"],
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_capacitor_parallel(self):
        svg = self._render("capacitor_network", {
            "topology": "parallel",
            "capacitors": ["5μF", "10μF", "15μF"],
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_dc_circuit(self):
        svg = self._render("basic_dc_circuit", {
            "components": [
                {"type": "battery", "value": "9V", "direction": "right"},
                {"type": "resistor", "label": "R1", "value": "100Ω", "direction": "right"},
                {"type": "resistor", "label": "R2", "value": "200Ω", "direction": "right"},
            ],
            "title": "Simple DC Circuit",
        })
        self.assertTrue(_is_valid_svg(svg))


class TestBiologyRenderer(TestCase):
    def _render(self, subtype, params):
        from diagrams.service.biology.renderer import render_biology
        return render_biology(subtype, params)

    # ── Cell diagram ──────────────────────────────────────────────────────────
    def test_animal_cell_all_organelles(self):
        svg = self._render("cell_diagram", {
            "cell_type": "animal",
            "labeled": True,
            "show_nucleus": True,
            "show_mitochondria": True,
            "show_er": True,
            "show_golgi": True,
            "show_ribosome": True,
            "show_lysosome": True,
            "show_vacuole": True,
            "show_centriole": True,
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_animal_cell_highlight_mitochondria(self):
        svg = self._render("cell_diagram", {
            "cell_type": "animal",
            "labeled": True,
            "highlight_organelle": "mitochondria",
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_plant_cell_all_organelles(self):
        svg = self._render("cell_diagram", {
            "cell_type": "plant",
            "labeled": True,
            "show_chloroplast": True,
            "show_cell_wall": True,
            "show_vacuole": True,
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_plant_cell_highlight_chloroplast(self):
        svg = self._render("cell_diagram", {
            "cell_type": "plant",
            "labeled": True,
            "highlight_organelle": "chloroplast",
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_cell_diagram_no_labels(self):
        svg = self._render("cell_diagram", {"cell_type": "animal", "labeled": False})
        self.assertTrue(_is_valid_svg(svg))

    # ── DNA structure ─────────────────────────────────────────────────────────
    def test_dna_double_helix_default(self):
        svg = self._render("dna_structure", {
            "structure_type": "double_helix",
            "num_base_pairs": 10,
            "show_base_labels": True,
            "show_labels": True,
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_dna_double_helix_no_labels(self):
        svg = self._render("dna_structure", {
            "structure_type": "double_helix",
            "num_base_pairs": 8,
            "show_base_labels": False,
            "show_labels": False,
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_dna_replication_fork(self):
        svg = self._render("dna_structure", {
            "structure_type": "replication_fork",
            "num_base_pairs": 12,
            "show_labels": True,
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_dna_replication_fork_no_labels(self):
        svg = self._render("dna_structure", {
            "structure_type": "replication_fork",
            "num_base_pairs": 10,
            "show_labels": False,
        })
        self.assertTrue(_is_valid_svg(svg))

    # ── Cell division ─────────────────────────────────────────────────────────
    def test_mitosis_prophase(self):
        svg = self._render("cell_division", {
            "division_type": "mitosis", "stage": "prophase",
            "num_chromosome_pairs": 2, "show_spindle": True,
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_mitosis_metaphase(self):
        svg = self._render("cell_division", {
            "division_type": "mitosis", "stage": "metaphase",
            "num_chromosome_pairs": 3, "show_spindle": True,
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_mitosis_anaphase(self):
        svg = self._render("cell_division", {
            "division_type": "mitosis", "stage": "anaphase",
            "num_chromosome_pairs": 2, "show_spindle": True,
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_mitosis_telophase(self):
        svg = self._render("cell_division", {
            "division_type": "mitosis", "stage": "telophase",
            "num_chromosome_pairs": 2,
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_mitosis_cytokinesis(self):
        svg = self._render("cell_division", {
            "division_type": "mitosis", "stage": "cytokinesis",
            "num_chromosome_pairs": 2,
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_meiosis_prophase_1(self):
        svg = self._render("cell_division", {
            "division_type": "meiosis", "stage": "prophase_1",
            "num_chromosome_pairs": 2, "show_labels": True,
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_meiosis_metaphase_1(self):
        svg = self._render("cell_division", {
            "division_type": "meiosis", "stage": "metaphase_1",
            "num_chromosome_pairs": 3,
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_meiosis_anaphase_1(self):
        svg = self._render("cell_division", {
            "division_type": "meiosis", "stage": "anaphase_1",
            "num_chromosome_pairs": 2,
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_meiosis_metaphase_2(self):
        svg = self._render("cell_division", {
            "division_type": "meiosis", "stage": "metaphase_2",
            "num_chromosome_pairs": 2,
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_meiosis_anaphase_2(self):
        svg = self._render("cell_division", {
            "division_type": "meiosis", "stage": "anaphase_2",
            "num_chromosome_pairs": 2,
        })
        self.assertTrue(_is_valid_svg(svg))

    # ── Anatomy diagrams ──────────────────────────────────────────────────────
    def test_heart_diagram_full(self):
        svg = self._render("heart_diagram", {
            "show_labels": True,
            "show_blood_flow": True,
            "show_valves": True,
            "title": "Human Heart",
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_heart_diagram_no_valves(self):
        svg = self._render("heart_diagram", {"show_valves": False})
        self.assertTrue(_is_valid_svg(svg))

    def test_nephron_full(self):
        svg = self._render("nephron_diagram", {
            "show_labels": True,
            "show_blood_vessels": True,
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_nephron_highlight_loop(self):
        svg = self._render("nephron_diagram", {
            "show_labels": True,
            "highlight_region": "loop_of_henle",
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_nephron_highlight_pct(self):
        svg = self._render("nephron_diagram", {
            "highlight_region": "pct",
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_neuron_myelinated(self):
        svg = self._render("neuron_diagram", {
            "neuron_type": "myelinated",
            "show_labels": True,
            "show_impulse_direction": True,
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_neuron_unmyelinated(self):
        svg = self._render("neuron_diagram", {
            "neuron_type": "unmyelinated",
            "show_labels": True,
        })
        self.assertTrue(_is_valid_svg(svg))

    # ── Ecology diagrams ──────────────────────────────────────────────────────
    def test_food_web_grassland(self):
        svg = self._render("food_web", {
            "nodes": [
                {"id": "grass",    "label": "Grass",       "trophic_level": 1},
                {"id": "rabbit",   "label": "Rabbit",      "trophic_level": 2},
                {"id": "deer",     "label": "Deer",        "trophic_level": 2},
                {"id": "fox",      "label": "Fox",         "trophic_level": 3},
                {"id": "eagle",    "label": "Eagle",       "trophic_level": 4},
            ],
            "edges": [
                {"from_id": "grass",  "to_id": "rabbit"},
                {"from_id": "grass",  "to_id": "deer"},
                {"from_id": "rabbit", "to_id": "fox"},
                {"from_id": "deer",   "to_id": "fox"},
                {"from_id": "fox",    "to_id": "eagle"},
            ],
            "title": "Grassland Food Web",
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_food_web_minimal(self):
        svg = self._render("food_web", {
            "nodes": [
                {"id": "a", "label": "Plant", "trophic_level": 1},
                {"id": "b", "label": "Deer",  "trophic_level": 2},
            ],
            "edges": [{"from_id": "a", "to_id": "b"}],
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_food_chain_5_level(self):
        svg = self._render("food_chain", {
            "organisms": ["Grass", "Grasshopper", "Frog", "Snake", "Eagle"],
            "title": "Grassland Food Chain",
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_food_chain_2_level(self):
        svg = self._render("food_chain", {
            "organisms": ["Phytoplankton", "Zooplankton"],
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_ecological_pyramid_biomass(self):
        svg = self._render("ecological_pyramid", {
            "pyramid_type": "biomass",
            "levels": [
                {"label": "Producers",        "value": 10000, "unit": "kg/ha"},
                {"label": "Primary Consumers", "value": 1000,  "unit": "kg/ha"},
                {"label": "Secondary Consumers","value": 100,  "unit": "kg/ha"},
                {"label": "Tertiary Consumers","value": 10,   "unit": "kg/ha"},
            ],
            "title": "Pyramid of Biomass",
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_ecological_pyramid_energy(self):
        svg = self._render("ecological_pyramid", {
            "pyramid_type": "energy",
            "levels": [
                {"label": "Producers",  "value": 20000, "unit": "kcal"},
                {"label": "Herbivores", "value": 2000,  "unit": "kcal"},
                {"label": "Carnivores", "value": 200,   "unit": "kcal"},
            ],
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_ecological_pyramid_numbers(self):
        svg = self._render("ecological_pyramid", {
            "pyramid_type": "numbers",
            "levels": [
                {"label": "Trees (Producers)",   "value": 10},
                {"label": "Insects (Herbivores)", "value": 1000},
                {"label": "Birds (Carnivores)",  "value": 50},
            ],
            "title": "Inverted Pyramid of Numbers",
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_unknown_subtype_raises(self):
        from diagrams.service.biology.renderer import render_biology
        with self.assertRaises(ValueError):
            render_biology("unknown_bio_type", {})

    # ── Full pipeline via dispatcher ──────────────────────────────────────────
    def test_dispatcher_biology(self):
        from diagrams.service.dispatcher import dispatch_render
        data = {
            "diagram_type": "biology",
            "subtype": "food_chain",
            "params": {"organisms": ["Grass", "Rabbit", "Fox"]},
        }
        validation, result = dispatch_render(data, save_files=False)
        self.assertTrue(validation.valid, validation.errors)
        self.assertTrue(result.success, result.error)
        self.assertTrue(_is_valid_svg(result.svg_content))


class TestDispatcher(TestCase):
    def test_full_pipeline_physics(self):
        from diagrams.service.dispatcher import dispatch_render
        data = {
            "diagram_type": "physics",
            "subtype": "inclined_plane",
            "params": {"angle": 37, "forces": ["mg", "N"]},
        }
        validation, result = dispatch_render(data, save_files=False)
        self.assertTrue(validation.valid)
        self.assertTrue(result.success)
        self.assertTrue(_is_valid_svg(result.svg_content))

    def test_pipeline_validation_failure(self):
        from diagrams.service.dispatcher import dispatch_render
        data = {"diagram_type": "physics", "subtype": "inclined_plane",
                "params": {"angle": -5}}
        validation, result = dispatch_render(data, save_files=False)
        self.assertFalse(result.success)


# ══════════════════════════════════════════════════════════════════════════════
# New Physics Diagrams (5)
# ══════════════════════════════════════════════════════════════════════════════

class TestPhysicsNewDiagrams(TestCase):
    def _render(self, subtype, params):
        from diagrams.service.physics.renderer import render_physics
        return render_physics(subtype, params)

    # ── Doppler Effect ────────────────────────────────────────────────────────
    def test_doppler_effect_default(self):
        svg = self._render("doppler_effect", {})
        self.assertTrue(_is_valid_svg(svg))

    def test_doppler_effect_fast_source(self):
        svg = self._render("doppler_effect", {
            "source_velocity": 0.8,
            "direction": "right",
            "observer_side": "right",
            "num_wavefronts": 8,
            "title": "Fast Doppler",
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_doppler_effect_source_moving_left(self):
        svg = self._render("doppler_effect", {
            "source_velocity": 0.4,
            "direction": "left",
            "observer_side": "left",
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_doppler_effect_no_observer(self):
        svg = self._render("doppler_effect", {"show_observer": False})
        self.assertTrue(_is_valid_svg(svg))

    # ── Interference Pattern ──────────────────────────────────────────────────
    def test_interference_double_slit(self):
        svg = self._render("interference_pattern", {
            "pattern_type": "double_slit",
            "slit_separation": 3.0,
            "wavelength": 550.0,
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_interference_single_slit(self):
        svg = self._render("interference_pattern", {
            "pattern_type": "single_slit",
            "num_maxima": 4,
            "wavelength": 650.0,
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_interference_no_intensity_curve(self):
        svg = self._render("interference_pattern", {
            "pattern_type": "double_slit",
            "show_intensity_curve": False,
        })
        self.assertTrue(_is_valid_svg(svg))

    # ── Bohr Atom ─────────────────────────────────────────────────────────────
    def test_bohr_atom_hydrogen(self):
        svg = self._render("bohr_atom", {
            "element": "H",
            "num_shells": 3,
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_bohr_atom_with_transitions(self):
        svg = self._render("bohr_atom", {
            "element": "H",
            "num_shells": 5,
            "transitions": [
                {"from_shell": 3, "to_shell": 1, "label": "Lyman α", "color": "purple"},
                {"from_shell": 3, "to_shell": 2, "label": "Hα", "color": "red"},
            ],
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_bohr_atom_custom_electrons(self):
        svg = self._render("bohr_atom", {
            "element": "Na",
            "num_shells": 3,
            "electrons_per_shell": [2, 8, 1],
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_bohr_atom_no_energy_levels(self):
        svg = self._render("bohr_atom", {"show_energy_levels": False})
        self.assertTrue(_is_valid_svg(svg))

    # ── Capacitor with Dielectric ─────────────────────────────────────────────
    def test_capacitor_dielectric_default(self):
        svg = self._render("capacitor_dielectric", {})
        self.assertTrue(_is_valid_svg(svg))

    def test_capacitor_dielectric_custom(self):
        svg = self._render("capacitor_dielectric", {
            "dielectric_label": "Glass (ε_r = 6)",
            "num_field_lines": 8,
            "show_induced_charges": True,
            "voltage_label": "12 V",
            "title": "Capacitor: Glass Dielectric",
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_capacitor_dielectric_no_induced(self):
        svg = self._render("capacitor_dielectric", {
            "show_induced_charges": False,
            "show_field_lines": False,
        })
        self.assertTrue(_is_valid_svg(svg))

    # ── LC Oscillation ────────────────────────────────────────────────────────
    def test_lc_oscillation_default(self):
        svg = self._render("lc_oscillation", {})
        self.assertTrue(_is_valid_svg(svg))

    def test_lc_oscillation_circuit_only(self):
        svg = self._render("lc_oscillation", {
            "show_circuit": True,
            "show_graphs": False,
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_lc_oscillation_graphs_only(self):
        svg = self._render("lc_oscillation", {
            "show_circuit": False,
            "show_graphs": True,
            "num_cycles": 3.0,
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_lc_oscillation_discharged_initial(self):
        svg = self._render("lc_oscillation", {
            "initial_state": "discharged",
            "show_energy_labels": False,
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_unknown_physics_subtype_raises(self):
        from diagrams.service.physics.renderer import render_physics
        with self.assertRaises(ValueError):
            render_physics("unknown_new_phys", {})


# ══════════════════════════════════════════════════════════════════════════════
# New Chemistry Diagrams (3)
# ══════════════════════════════════════════════════════════════════════════════

class TestChemistryNewMechanisms(TestCase):
    def _render(self, subtype, params):
        from diagrams.service.chemistry.renderer import render_chemistry
        return render_chemistry(subtype, params)

    # ── SN1/SN2 Mechanism ─────────────────────────────────────────────────────
    def test_sn2_default(self):
        svg = self._render("sn1_sn2_mechanism", {
            "mechanism_type": "sn2",
            "substrate": "CH₃Br",
            "nucleophile": "OH⁻",
            "leaving_group": "Br⁻",
            "product": "CH₃OH",
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_sn1_with_intermediate(self):
        svg = self._render("sn1_sn2_mechanism", {
            "mechanism_type": "sn1",
            "substrate": "(CH₃)₃CBr",
            "nucleophile": "H₂O",
            "leaving_group": "Br⁻",
            "product": "(CH₃)₃COH",
            "intermediate": "(CH₃)₃C⁺",
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_sn2_no_arrows(self):
        svg = self._render("sn1_sn2_mechanism", {
            "mechanism_type": "sn2",
            "show_curved_arrows": False,
            "show_stereochemistry": False,
        })
        self.assertTrue(_is_valid_svg(svg))

    # ── Newman Projection ─────────────────────────────────────────────────────
    def test_newman_anti_conformation(self):
        svg = self._render("newman_projection", {
            "front_carbon": "C1",
            "back_carbon": "C2",
            "front_substituents": ["H", "CH₃", "H"],
            "back_substituents": ["H", "H", "CH₃"],
            "dihedral_angle": 180.0,
            "conformation_label": "Anti",
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_newman_gauche(self):
        svg = self._render("newman_projection", {
            "dihedral_angle": 60.0,
            "conformation_label": "Gauche",
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_newman_eclipsed(self):
        svg = self._render("newman_projection", {
            "dihedral_angle": 0.0,
            "conformation_label": "Eclipsed",
            "show_dihedral_annotation": False,
        })
        self.assertTrue(_is_valid_svg(svg))

    # ── Conformational Isomers ────────────────────────────────────────────────
    def test_conformational_cyclohexane_chair_boat(self):
        svg = self._render("conformational_isomers", {
            "molecule_type": "cyclohexane",
            "conformations": ["chair", "boat"],
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_conformational_cyclohexane_chair_only(self):
        svg = self._render("conformational_isomers", {
            "molecule_type": "cyclohexane",
            "conformations": ["chair"],
            "show_axial_equatorial": True,
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_conformational_ethane_staggered_eclipsed(self):
        svg = self._render("conformational_isomers", {
            "molecule_type": "ethane",
            "conformations": ["staggered", "eclipsed"],
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_unknown_chemistry_subtype_raises(self):
        from diagrams.service.chemistry.renderer import render_chemistry
        with self.assertRaises(ValueError):
            render_chemistry("unknown_chem_type", {})


# ══════════════════════════════════════════════════════════════════════════════
# New Mathematics Diagrams (3)
# ══════════════════════════════════════════════════════════════════════════════

class TestMathematicsNewDiagrams(TestCase):
    def _render(self, subtype, params):
        from diagrams.service.mathematics.renderer import render_mathematics
        return render_mathematics(subtype, params)

    # ── Bar Chart ─────────────────────────────────────────────────────────────
    def test_bar_chart_basic(self):
        svg = self._render("bar_chart", {
            "bars": [
                {"label": "Jan", "value": 120},
                {"label": "Feb", "value": 95},
                {"label": "Mar", "value": 145},
            ],
            "title": "Monthly Data",
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_bar_chart_with_labels_and_grid(self):
        svg = self._render("bar_chart", {
            "bars": [
                {"label": "A", "value": 30, "color": "#E74C3C"},
                {"label": "B", "value": 50, "color": "#2980B9"},
                {"label": "C", "value": 40, "color": "#27AE60"},
                {"label": "D", "value": 25, "color": "#F39C12"},
            ],
            "x_label": "Category",
            "y_label": "Frequency",
            "show_values": True,
            "show_grid": True,
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_histogram_blue_scheme(self):
        svg = self._render("bar_chart", {
            "bars": [
                {"label": "0–10", "value": 5},
                {"label": "10–20", "value": 15},
                {"label": "20–30", "value": 25},
                {"label": "30–40", "value": 18},
                {"label": "40–50", "value": 7},
            ],
            "chart_type": "histogram",
            "color_scheme": "blue",
            "title": "Score Distribution",
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_bar_chart_rainbow_scheme(self):
        svg = self._render("bar_chart", {
            "bars": [{"label": str(i), "value": i * 10} for i in range(1, 5)],
            "color_scheme": "rainbow",
        })
        self.assertTrue(_is_valid_svg(svg))

    # ── Scatter Plot ──────────────────────────────────────────────────────────
    def test_scatter_plot_basic_linear_regression(self):
        svg = self._render("scatter_plot", {
            "points": [
                {"x": 1, "y": 2.1},
                {"x": 2, "y": 3.9},
                {"x": 3, "y": 6.2},
                {"x": 4, "y": 7.8},
                {"x": 5, "y": 10.1},
            ],
            "show_regression_line": True,
            "show_r_squared": True,
            "title": "Linear Regression",
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_scatter_plot_quadratic_fit(self):
        svg = self._render("scatter_plot", {
            "points": [
                {"x": -2, "y": 4.1},
                {"x": -1, "y": 1.0},
                {"x": 0, "y": 0.1},
                {"x": 1, "y": 0.9},
                {"x": 2, "y": 4.2},
            ],
            "regression_degree": 2,
            "title": "Quadratic Fit",
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_scatter_plot_with_point_labels(self):
        svg = self._render("scatter_plot", {
            "points": [
                {"x": 1, "y": 3, "label": "P1"},
                {"x": 3, "y": 7, "label": "P2"},
                {"x": 5, "y": 12, "label": "P3"},
            ],
            "show_regression_line": True,
            "x_label": "Time (s)",
            "y_label": "Distance (m)",
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_scatter_plot_no_regression(self):
        svg = self._render("scatter_plot", {
            "points": [{"x": i, "y": i * 2} for i in range(5)],
            "show_regression_line": False,
        })
        self.assertTrue(_is_valid_svg(svg))

    # ── 3D Vector ─────────────────────────────────────────────────────────────
    def test_vector_3d_single(self):
        svg = self._render("vector_3d", {
            "vectors": [{"x": 1, "y": 2, "z": 3, "label": "v", "color": "blue"}],
            "title": "Single 3D Vector",
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_vector_3d_multiple(self):
        svg = self._render("vector_3d", {
            "vectors": [
                {"x": 2, "y": 0, "z": 0, "label": "i", "color": "red"},
                {"x": 0, "y": 2, "z": 0, "label": "j", "color": "green"},
                {"x": 0, "y": 0, "z": 2, "label": "k", "color": "blue"},
            ],
            "show_axes": True,
            "axis_labels": ["x", "y", "z"],
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_vector_3d_with_projections(self):
        svg = self._render("vector_3d", {
            "vectors": [{"x": 3, "y": 4, "z": 5, "label": "F", "color": "purple"}],
            "show_projections": True,
            "title": "3D Force Vector",
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_vector_3d_angle_between(self):
        svg = self._render("vector_3d", {
            "vectors": [
                {"x": 1, "y": 0, "z": 0, "label": "a"},
                {"x": 0, "y": 1, "z": 0, "label": "b"},
            ],
            "show_angle_between": True,
            "title": "Angle Between Vectors",
        })
        self.assertTrue(_is_valid_svg(svg))

    def test_unknown_mathematics_subtype_raises(self):
        from diagrams.service.mathematics.renderer import render_mathematics
        with self.assertRaises(ValueError):
            render_mathematics("unknown_math_type", {})


# ── Full pipeline tests for new diagram types ─────────────────────────────────

class TestNewDiagramPipeline(TestCase):
    def _dispatch(self, diagram_type, subtype, params):
        from diagrams.service.dispatcher import dispatch_render
        data = {
            "diagram_type": diagram_type,
            "subtype": subtype,
            "params": params,
        }
        return dispatch_render(data, save_files=False)

    def test_doppler_pipeline(self):
        v, r = self._dispatch("physics", "doppler_effect",
                               {"source_velocity": 0.5})
        self.assertTrue(v.valid, v.errors)
        self.assertTrue(r.success, r.error)
        self.assertTrue(_is_valid_svg(r.svg_content))

    def test_bohr_atom_pipeline(self):
        v, r = self._dispatch("physics", "bohr_atom",
                               {"element": "He", "num_shells": 2})
        self.assertTrue(v.valid, v.errors)
        self.assertTrue(r.success, r.error)
        self.assertTrue(_is_valid_svg(r.svg_content))

    def test_sn2_pipeline(self):
        v, r = self._dispatch("chemistry", "sn1_sn2_mechanism",
                               {"mechanism_type": "sn2"})
        self.assertTrue(v.valid, v.errors)
        self.assertTrue(r.success, r.error)
        self.assertTrue(_is_valid_svg(r.svg_content))

    def test_bar_chart_pipeline(self):
        v, r = self._dispatch("mathematics", "bar_chart",
                               {"bars": [{"label": "X", "value": 10}]})
        self.assertTrue(v.valid, v.errors)
        self.assertTrue(r.success, r.error)
        self.assertTrue(_is_valid_svg(r.svg_content))

    def test_scatter_plot_pipeline(self):
        v, r = self._dispatch("mathematics", "scatter_plot",
                               {"points": [{"x": 0, "y": 0}, {"x": 1, "y": 1}]})
        self.assertTrue(v.valid, v.errors)
        self.assertTrue(r.success, r.error)
        self.assertTrue(_is_valid_svg(r.svg_content))

    def test_vector_3d_pipeline(self):
        v, r = self._dispatch("mathematics", "vector_3d",
                               {"vectors": [{"x": 1, "y": 1, "z": 1, "label": "v"}]})
        self.assertTrue(v.valid, v.errors)
        self.assertTrue(r.success, r.error)
        self.assertTrue(_is_valid_svg(r.svg_content))
