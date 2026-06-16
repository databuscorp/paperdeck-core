"""
Integration tests for the Diagram API endpoints.
Uses Django TestClient — no authentication required (AllowAny permission).
"""
import json
from django.test import TestCase, Client
from django.urls import reverse


class TestRenderAPI(TestCase):
    def setUp(self):
        self.client = Client()

    def _post(self, url, data):
        return self.client.post(
            url,
            data=json.dumps(data),
            content_type="application/json",
        )

    # ── /api/diagrams/render/ ────────────────────────────────────────────────

    def test_render_inclined_plane(self):
        resp = self._post("/api/diagrams/render/", {
            "diagram_type": "physics",
            "subtype": "inclined_plane",
            "params": {"angle": 37, "forces": ["mg", "N", "f"]},
        })
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(body["success"])
        self.assertIn("<svg", body["svg_content"])
        self.assertIn("diagram_id", body)
        self.assertIn("render_time_ms", body)

    def test_render_function_graph(self):
        resp = self._post("/api/diagrams/render/", {
            "diagram_type": "mathematics",
            "subtype": "function_graph",
            "params": {
                "functions": [{"expression": "x**2", "x_range": [-4, 4]}],
            },
        })
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["success"])

    def test_render_reaction_coordinate(self):
        resp = self._post("/api/diagrams/render/", {
            "diagram_type": "chemistry",
            "subtype": "reaction_coordinate_graph",
            "params": {
                "reactant_energy": 0,
                "product_energy": -50,
                "activation_energy": 100,
            },
        })
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["success"])

    def test_render_resistor_network(self):
        resp = self._post("/api/diagrams/render/", {
            "diagram_type": "circuits",
            "subtype": "resistor_network",
            "params": {
                "topology": "series",
                "resistors": ["2Ω", "3Ω"],
            },
        })
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["success"])

    def test_render_invalid_type_returns_422(self):
        resp = self._post("/api/diagrams/render/", {
            "diagram_type": "aliens",
            "subtype": "flying_saucer",
            "params": {},
        })
        self.assertEqual(resp.status_code, 422)
        self.assertFalse(resp.json()["success"])

    def test_render_invalid_param_returns_422(self):
        resp = self._post("/api/diagrams/render/", {
            "diagram_type": "physics",
            "subtype": "inclined_plane",
            "params": {"angle": -10},   # invalid
        })
        self.assertEqual(resp.status_code, 422)

    def test_render_saves_db_record(self):
        from diagrams.models import RenderedDiagram
        count_before = RenderedDiagram.objects.count()
        self._post("/api/diagrams/render/", {
            "diagram_type": "physics",
            "subtype": "wave_diagram",
            "params": {"amplitude": 80, "num_cycles": 2},
        })
        self.assertEqual(RenderedDiagram.objects.count(), count_before + 1)

    def test_render_missing_diagram_type(self):
        resp = self._post("/api/diagrams/render/", {"subtype": "inclined_plane"})
        # Will fail validation or be caught as missing required field
        self.assertIn(resp.status_code, [400, 422])

    # ── /api/diagrams/validate/ ──────────────────────────────────────────────

    def test_validate_valid_schema(self):
        resp = self._post("/api/diagrams/validate/", {
            "diagram_type": "physics",
            "subtype": "projectile_motion",
            "params": {"launch_angle": 45, "initial_velocity": 20},
        })
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(body["valid"])
        self.assertEqual(body["errors"], [])

    def test_validate_invalid_schema(self):
        resp = self._post("/api/diagrams/validate/", {
            "diagram_type": "physics",
            "subtype": "inclined_plane",
            "params": {"angle": 95},   # max is 89
        })
        self.assertEqual(resp.status_code, 422)
        body = resp.json()
        self.assertFalse(body["valid"])
        self.assertGreater(len(body["errors"]), 0)

    # ── /api/diagrams/types/ ─────────────────────────────────────────────────

    def test_list_types(self):
        resp = self.client.get("/api/diagrams/types/")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn("supported_types", body)
        types = body["supported_types"]
        self.assertIn("physics", types)
        self.assertIn("mathematics", types)
        self.assertIn("chemistry", types)
        self.assertIn("circuits", types)
        self.assertIn("inclined_plane", types["physics"])

    # ── /api/health/ ─────────────────────────────────────────────────────────

    def test_health_check(self):
        resp = self.client.get("/api/health/")
        self.assertIn(resp.status_code, [200, 503])
        body = resp.json()
        self.assertIn("status", body)
        self.assertIn("checks", body)
        self.assertIn("database", body["checks"])


class TestPDFAPI(TestCase):
    def setUp(self):
        self.client = Client()

    def test_generate_paper_pdf(self):
        resp = self.client.post(
            "/api/diagrams/pdf/",
            data=json.dumps({
                "title": "JEE Mock Test",
                "exam_name": "JEE Mains",
                "duration_minutes": 180,
                "total_marks": 300,
                "instructions": [
                    "Read all questions carefully.",
                    "Each question carries 4 marks.",
                    "There is a negative marking of -1 for wrong answers.",
                ],
                "sections": [
                    {
                        "name": "Section A - Physics",
                        "questions": [
                            {
                                "number": 1,
                                "text": "A block of mass 2 kg is placed on a frictionless incline at 30°. Find the acceleration.",
                                "options": [
                                    {"text": "4.9 m/s²", "correct": True},
                                    {"text": "9.8 m/s²", "correct": False},
                                    {"text": "2.5 m/s²", "correct": False},
                                    {"text": "1.2 m/s²", "correct": False},
                                ],
                                "marks": 4,
                                "negative_marks": -1,
                            }
                        ]
                    }
                ]
            }),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "application/pdf")
        self.assertGreater(len(resp.content), 100)   # non-empty PDF
