"""Deploy-time guard: the deployment font must carry the glyphs diagrams print.

The print/PDF path rasterises SVG with cairosvg, which draws each <text> glyph from the
font fontconfig resolves for the family name — NOT from any font matplotlib bundles. In the
container that must be DejaVu Sans (fonts-dejavu-core), which carries the arrows, Greek,
subscripts, °, × that the renderers emit. If that package is missing, fontconfig silently
falls back to some other installed font and every one of those glyphs prints as a tofu box
(□) on real student papers — while looking fine in a browser, because browsers do per-glyph
fallback and cairosvg does not.

This is a `deploy`-tagged check so it runs under `manage.py check --deploy` (the production
gate) and stays quiet during ordinary local development — a dev machine without DejaVu
installed resolves to a system font (e.g. Hiragino), which is a known, harmless local
artifact, not a production defect.
"""
import os
import shutil
import subprocess

from django.core.checks import Warning as CheckWarning, register


@register("diagrams", deploy=True)
def dejavu_font_present(app_configs, **kwargs):
    """Warn if fontconfig does not resolve 'DejaVu Sans' to an actual DejaVu font file."""
    fc_match = shutil.which("fc-match")
    if not fc_match:
        # No fontconfig CLI to introspect — cannot assert either way, so stay silent
        # rather than raise a false alarm.
        return []

    try:
        resolved = subprocess.run(
            [fc_match, "-f", "%{file}", "DejaVu Sans"],
            capture_output=True, text=True, timeout=5,
        ).stdout.strip()
    except Exception:
        return []

    basename = os.path.basename(resolved)
    if "dejavu" in basename.lower():
        return []

    return [CheckWarning(
        "fontconfig resolves 'DejaVu Sans' to %r, not a DejaVu font. cairosvg will "
        "rasterise diagram text with that font, so arrows, Greek letters, subscripts, "
        "degree and times signs may print as tofu boxes on the paper." % (resolved or "nothing"),
        hint="Install the DejaVu font in the deployment image (Debian: "
             "`apt-get install -y fonts-dejavu-core`).",
        id="diagrams.W001",
    )]
