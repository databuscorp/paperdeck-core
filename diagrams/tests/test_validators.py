"""
Unit tests for the Pydantic schema validation layer.
"""
from django.test import TestCase

from diagrams.validators.schema_validator import validate_diagram, list_supported_subtypes


class TestMasterSchemaValidation(TestCase):
    def test_valid_physics_inclined_plane(self):
        data = {
            "diagram_type": "physics",
            "subtype": "inclined_plane",
            "params": {"angle": 37.0, "forces": ["mg", "N", "f"]},
        }
        result = validate_diagram(data)
        self.assertTrue(result.valid)
        self.assertEqual(result.errors, [])

    def test_invalid_diagram_type(self):
        data = {"diagram_type": "unknown_type", "subtype": "foo"}
        result = validate_diagram(data)
        self.assertFalse(result.valid)
        self.assertTrue(any("diagram_type" in e["field"] for e in result.errors))

    def test_invalid_subtype(self):
        data = {"diagram_type": "physics", "subtype": "flying_pig"}
        result = validate_diagram(data)
        self.assertFalse(result.valid)
        self.assertTrue(any("subtype" in e["field"] for e in result.errors))

    def test_empty_subtype(self):
        data = {"diagram_type": "physics", "subtype": ""}
        result = validate_diagram(data)
        self.assertFalse(result.valid)

    def test_canvas_defaults(self):
        data = {"diagram_type": "mathematics", "subtype": "function_graph",
                "params": {"functions": [{"expression": "x**2", "x_range": [-5, 5]}]}}
        result = validate_diagram(data)
        self.assertTrue(result.valid)

    def test_canvas_out_of_range(self):
        data = {
            "diagram_type": "physics",
            "subtype": "wave_diagram",
            "canvas": {"width": 99999, "height": 600},  # too wide
        }
        result = validate_diagram(data)
        self.assertFalse(result.valid)


class TestPhysicsSchemas(TestCase):
    def test_inclined_plane_angle_bounds(self):
        # angle must be between 1 and 89
        data = {
            "diagram_type": "physics",
            "subtype": "inclined_plane",
            "params": {"angle": 0.0},  # too low
        }
        result = validate_diagram(data)
        self.assertFalse(result.valid)

    def test_inclined_plane_invalid_force(self):
        data = {
            "diagram_type": "physics",
            "subtype": "inclined_plane",
            "params": {"angle": 30, "forces": ["gravity_alien"]},
        }
        result = validate_diagram(data)
        self.assertFalse(result.valid)

    def test_projectile_launch_angle(self):
        data = {
            "diagram_type": "physics",
            "subtype": "projectile_motion",
            "params": {"launch_angle": 90.0},  # boundary, but 89 max
        }
        result = validate_diagram(data)
        self.assertFalse(result.valid)


class TestChemistrySchemas(TestCase):
    def test_organic_smiles_empty(self):
        data = {
            "diagram_type": "chemistry",
            "subtype": "organic_structure",
            "params": {"smiles": ""},
        }
        result = validate_diagram(data)
        self.assertFalse(result.valid)

    def test_organic_valid_smiles(self):
        data = {
            "diagram_type": "chemistry",
            "subtype": "organic_structure",
            "params": {"smiles": "CCO"},
        }
        result = validate_diagram(data)
        self.assertTrue(result.valid)

    def test_reaction_coordinate_positive_ea(self):
        data = {
            "diagram_type": "chemistry",
            "subtype": "reaction_coordinate_graph",
            "params": {"activation_energy": -10},  # invalid
        }
        result = validate_diagram(data)
        self.assertFalse(result.valid)


class TestMathSchemas(TestCase):
    def test_function_graph_no_functions(self):
        data = {
            "diagram_type": "mathematics",
            "subtype": "function_graph",
            "params": {"functions": []},
        }
        result = validate_diagram(data)
        self.assertFalse(result.valid)

    def test_geometry_triangle_needs_3_vertices(self):
        data = {
            "diagram_type": "mathematics",
            "subtype": "geometry_triangle",
            "params": {
                "vertices": [
                    {"label": "A", "x": 0, "y": 0},
                    {"label": "B", "x": 4, "y": 0},
                ]  # only 2 vertices
            },
        }
        result = validate_diagram(data)
        self.assertFalse(result.valid)


class TestCircuitSchemas(TestCase):
    def test_resistor_network_empty(self):
        data = {
            "diagram_type": "circuits",
            "subtype": "resistor_network",
            "params": {"resistors": []},
        }
        result = validate_diagram(data)
        self.assertFalse(result.valid)

    def test_dc_circuit_needs_2_components(self):
        data = {
            "diagram_type": "circuits",
            "subtype": "basic_dc_circuit",
            "params": {
                "components": [{"type": "battery", "value": "12V"}]
            },
        }
        result = validate_diagram(data)
        self.assertFalse(result.valid)


class TestSupportedTypes(TestCase):
    def test_all_types_present(self):
        types = list_supported_subtypes()
        self.assertIn("physics", types)
        self.assertIn("chemistry", types)
        self.assertIn("mathematics", types)
        self.assertIn("circuits", types)

    def test_physics_subtypes(self):
        types = list_supported_subtypes()
        expected = ["inclined_plane", "free_body_diagram", "pulley_system",
                    "projectile_motion", "spring_block", "optics_convex_lens",
                    "optics_concave_mirror", "wave_diagram"]
        for s in expected:
            self.assertIn(s, types["physics"])
