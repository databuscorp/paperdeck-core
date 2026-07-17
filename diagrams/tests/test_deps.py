"""Guards against the render dependencies degrading *silently*.

cairosvg and rdkit both fail soft: the chemistry renderer catches ImportError and
falls back to a crude SMILES parser, and PNG export just stops happening. On a
correctly-provisioned host that fallback should never be reached — but nothing in the
app tells you when it is, so a deploy missing a native library produces subtly worse
diagrams (or none) and looks completely healthy.

These tests fail loudly in that situation. They are skipped, not failed, when the
dependency is genuinely absent (local dev), so they don't block anyone — but see
`test_container_declares_native_deps`, which does hard-fail if the Dockerfile stops
installing the native libraries those wheels need.
"""
import pathlib
import unittest
import xml.etree.ElementTree as ET

from django.test import SimpleTestCase

from diagrams.service.dispatcher import CAIROSVG_AVAILABLE, dispatch_render

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

try:
    from rdkit import Chem  # noqa: F401
    RDKIT_AVAILABLE = True
except Exception:
    RDKIT_AVAILABLE = False


class RenderDependencyTests(SimpleTestCase):

    @unittest.skipUnless(RDKIT_AVAILABLE, "rdkit not installed in this environment")
    def test_rdkit_actually_draws_a_molecule(self):
        """rdkit present AND usable — importable but broken is the dangerous state."""
        from rdkit import Chem
        self.assertIsNotNone(Chem.MolFromSmiles("CC(=O)Oc1ccccc1"))

        _, result = dispatch_render({
            "diagram_type": "chemistry", "subtype": "organic_structure",
            "params": {"smiles": "CC(=O)Oc1ccccc1", "name": "Aspirin"},
        }, save_files=False)
        self.assertTrue(result.success, result.error)
        ET.fromstring(result.svg_content)   # well-formed
        # The crude fallback prints the SMILES string as text; a real render draws paths.
        self.assertNotIn("CC(=O)Oc1ccccc1", result.svg_content,
                         "chemistry renderer fell back to the SMILES-text renderer "
                         "even though rdkit is installed")

    @unittest.skipUnless(CAIROSVG_AVAILABLE, "cairosvg/native cairo not available here")
    def test_cairosvg_rasterizes_for_pdf(self):
        from diagrams.service.pdf.composer import svg_to_png_bytes
        _, result = dispatch_render({
            "diagram_type": "physics", "subtype": "inclined_plane",
            "params": {"angle": 30},
        }, save_files=False)
        png = svg_to_png_bytes(result.svg_content, width=400, height=260)
        self.assertEqual(png[:4], bytes([0x89, 0x50, 0x4E, 0x47]))   # PNG magic

    def test_pdf_export_refuses_rather_than_printing_a_blank_figure(self):
        """Without cairosvg the PDF path must raise, not emit a blank placeholder —
        a blank figure in a printed exam is undetectable downstream."""
        from diagrams.service.pdf import composer
        real = composer.CAIROSVG_AVAILABLE
        composer.CAIROSVG_AVAILABLE = False
        try:
            with self.assertRaises(composer.PNGConversionUnavailable):
                composer.svg_to_png_bytes("<svg/>")
        finally:
            composer.CAIROSVG_AVAILABLE = real

    def test_container_declares_native_deps(self):
        """The rdkit wheel vendors boost/cairo but NOT libX11/libXext/libXrender, and
        python:*-slim doesn't ship them. Missing them makes `import rdkit` raise
        ImportError, which the chemistry renderer swallows — molecules silently stop
        being drawn. Keep them in the image."""
        dockerfile = (REPO_ROOT / "Dockerfile").read_text()
        for lib in ("libxrender1", "libxext6", "libx11-6", "libcairo2"):
            self.assertIn(lib, dockerfile,
                          f"Dockerfile must install {lib} or rendering degrades silently")
