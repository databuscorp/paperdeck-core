"""Every glyph a diagram prints must exist in the deployment font.

The print/PDF path rasterises SVG with cairosvg, which draws each <text> glyph from the font
fontconfig resolves for the family — in the container that is DejaVuSans.ttf (fonts-dejavu-core).
A character absent from that font renders as a tofu box (□) on the printed paper while looking
fine in a browser (browsers do per-glyph fallback; cairosvg does not). `⟂` (U+27C2) is the
canonical offender — it is not in DejaVu Sans.

This test is checked against DejaVu Sans's ACTUAL coverage, NOT against whatever the local
machine's cairosvg happens to resolve. That distinction matters: a dev box without DejaVu
installed falls back to some system font (e.g. Hiragino Sans) whose gaps are irrelevant to
production. The container font is the only source of truth, so that is what we assert against.

If this fails, a renderer is emitting a glyph that will print as a box for real students. Fix by
drawing the symbol as a path/patch (arrows), or substituting one DejaVu carries.
"""
import json
import re

from django.test import SimpleTestCase

from diagrams.service.dispatcher import dispatch_render
from papers.service.aigeneratorservice import _DIAGRAM_SCHEMA_HINT

_TEXT_RE = re.compile(r">([^<>]+)</text>")


def _dejavu_cmap():
    from matplotlib.font_manager import FontProperties, findfont
    from fontTools.ttLib import TTFont
    # DejaVu Sans is bundled with matplotlib and is byte-identical to the container's
    # fonts-dejavu-core DejaVuSans.ttf, so its cmap is exactly production's coverage.
    return set(TTFont(findfont(FontProperties(family="DejaVu Sans"))).getBestCmap())


def _catalog_examples():
    for raw in re.findall(r'^\s*(\{"diagram_type".*\})\s*$', _DIAGRAM_SCHEMA_HINT, re.M):
        yield json.loads(raw)


class GlyphCoverageTests(SimpleTestCase):

    def test_no_diagram_prints_a_glyph_missing_from_the_deployment_font(self):
        cmap = _dejavu_cmap()
        offenders = {}
        for ex in _catalog_examples():
            _, r = dispatch_render(ex, save_files=False)
            if not r.success:
                continue
            missing = {
                ch for text in _TEXT_RE.findall(r.svg_content) for ch in text
                if ord(ch) > 0x7F and ord(ch) not in cmap
            }
            if missing:
                offenders[f"{ex['diagram_type']}/{ex['subtype']}"] = sorted(
                    f"U+{ord(c):04X} {c!r}" for c in missing)
        self.assertFalse(
            offenders,
            "diagrams printing glyphs absent from DejaVu Sans (tofu on paper):\n"
            + "\n".join(f"  {k}: {v}" for k, v in sorted(offenders.items())))
