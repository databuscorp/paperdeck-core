"""The config-defined biology template layer (labeled_schematic)."""
from django.test import SimpleTestCase

from diagrams.service.dispatcher import dispatch_render
from diagrams.service.biology.templates import BIOLOGY_TEMPLATES


def _render(params):
    return dispatch_render(
        {"diagram_type": "biology", "subtype": "labeled_schematic", "params": params},
        save_files=False)


class LabeledSchematicTests(SimpleTestCase):

    def test_every_named_template_validates_and_renders(self):
        for name in BIOLOGY_TEMPLATES:
            val, res = _render({"template": name})
            self.assertTrue(val.valid, f"{name} failed validation: {val.errors}")
            self.assertTrue(res.success, f"{name} failed to render: {res.error}")
            # Every template's labels must reach the SVG as real <text> nodes.
            for lbl in BIOLOGY_TEMPLATES[name]["labels"]:
                self.assertIn(lbl["text"], res.svg_content, f"{name} missing label {lbl['text']!r}")

    def test_inline_shapes_render_without_a_template(self):
        val, res = _render({
            "title": "Custom",
            "shapes": [{"kind": "circle", "cx": 50, "cy": 50, "r": 20, "fill": "#eee"}],
            "labels": [{"text": "Blob", "x": 80, "y": 30, "target": [55, 45]}],
        })
        self.assertTrue(val.valid)
        self.assertTrue(res.success)
        self.assertIn("Blob", res.svg_content)

    def test_label_override_replaces_template_labels(self):
        # A blank diagram for students: same artwork, labels swapped for A/B/C.
        val, res = _render({
            "template": "plant_cell",
            "labels": [{"text": "A", "x": 90, "y": 20, "target": [72, 20]}],
        })
        self.assertTrue(res.success)
        self.assertIn(">A<", res.svg_content)
        self.assertNotIn("Chloroplast", res.svg_content)   # template's own labels are gone

    def test_unknown_template_fails_cleanly(self):
        val, res = _render({"template": "warp_core"})
        # Schema is valid (template is a free string); the renderer rejects the unknown name.
        self.assertFalse(res.success)
        self.assertIn("template", (res.error or "").lower())

    def test_empty_schema_is_rejected_by_validation(self):
        val, res = _render({})   # no template, no shapes
        self.assertFalse(val.valid)
