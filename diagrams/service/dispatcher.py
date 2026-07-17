"""
Diagram Dispatcher Service.
Routes validated diagram schemas to the correct rendering engine.
This is the single entry point for all rendering operations.

Pipeline:
  validate_diagram(data) → ValidationResult
      → dispatch_render(data) → SVG string
          → save_to_file(svg, diagram_id) → (svg_path, png_path)
"""
from __future__ import annotations

import logging
import os
import time
import traceback
import uuid
from typing import Any, Dict, Optional, Tuple

from django.conf import settings

logger = logging.getLogger(__name__)

from diagrams.validators.schema_validator import validate_diagram, ValidationResult
from diagrams.service.physics.renderer import render_physics
from diagrams.service.chemistry.renderer import render_chemistry
from diagrams.service.mathematics.renderer import render_mathematics
from diagrams.service.circuits.renderer import render_circuits
from diagrams.service.biology.renderer import render_biology

# ── PNG conversion ────────────────────────────────────────────────────────────
# Without cairosvg we simply don't write a PNG. (There used to be a PIL fallback that
# wrote a blank white image — see _save_diagram_files for why that was worse than none.)
#
# NOTE the broad except: when the cairosvg package is installed but the *native* cairo
# library isn't findable, cairocffi raises OSError, not ImportError. Catching only
# ImportError here would let that OSError escape and take down the whole app at import.
try:
    import cairosvg
    CAIROSVG_AVAILABLE = True
except Exception:   # ImportError (not installed) | OSError (native libcairo missing)
    CAIROSVG_AVAILABLE = False


RENDER_FN_MAP = {
    "physics": render_physics,
    "chemistry": render_chemistry,
    "mathematics": render_mathematics,
    "circuits": render_circuits,
    "biology": render_biology,
}


class RenderResult:
    """Result object returned by dispatch_render."""

    def __init__(self, *, success: bool, svg_content: str = "",
                 svg_path: str = "", png_path: str = "",
                 error: str = "", render_time_ms: int = 0):
        self.success = success
        self.svg_content = svg_content
        self.svg_path = svg_path
        self.png_path = png_path
        self.error = error
        self.render_time_ms = render_time_ms

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "svg_content": self.svg_content,
            "svg_path": self.svg_path,
            "png_path": self.png_path,
            "error": self.error,
            "render_time_ms": self.render_time_ms,
        }


def dispatch_render(data: Dict[str, Any],
                    save_files: bool = True,
                    diagram_id: Optional[str] = None) -> Tuple[ValidationResult, RenderResult]:
    """
    Full pipeline: validate → render → (optionally) save.

    Returns:
        (ValidationResult, RenderResult)
    """
    # ── 1. Validate ───────────────────────────────────────────────────────────
    validation = validate_diagram(data)
    if not validation.valid:
        return validation, RenderResult(success=False,
                                        error="Validation failed: " + "; ".join(
                                            e["message"] for e in validation.errors))

    diagram_type = data["diagram_type"]
    subtype = data["subtype"]
    canvas = data.get("canvas", {})
    canvas_w = canvas.get("width", 800)
    canvas_h = canvas.get("height", 600)

    # params: prefer data["params"], else first element of data["objects"]
    params = data.get("params") or (data.get("objects") or [{}])[0]

    # ── 2. Render ─────────────────────────────────────────────────────────────
    render_fn = RENDER_FN_MAP.get(diagram_type)
    if not render_fn:
        return validation, RenderResult(success=False,
                                        error=f"No renderer for diagram_type '{diagram_type}'")

    start_ms = int(time.time() * 1000)
    try:
        svg_content = render_fn(subtype, params, canvas_w=canvas_w, canvas_h=canvas_h)
    except Exception as exc:
        tb = traceback.format_exc()
        return validation, RenderResult(success=False, error=str(exc) + "\n" + tb)
    render_time_ms = int(time.time() * 1000) - start_ms

    # ── 3. Optionally save files ──────────────────────────────────────────────
    svg_path, png_path = "", ""
    if save_files:
        svg_path, png_path = _save_diagram_files(
            svg_content, diagram_type, diagram_id or str(uuid.uuid4())
        )

    return validation, RenderResult(
        success=True,
        svg_content=svg_content,
        svg_path=svg_path,
        png_path=png_path,
        render_time_ms=render_time_ms,
    )


def _save_diagram_files(svg_content: str, diagram_type: str,
                        diagram_id: str) -> Tuple[str, str]:
    """
    Save SVG (and optionally PNG) to media under rendered/{diagram_type}/.

    Writes through Django's configured default storage, so the same code lands files on
    the local filesystem in development and in Azure Blob Storage in production (see
    settings.STORAGES). Returns (svg_name, png_name) — storage keys, resolved to real
    URLs via `default_storage.url(...)`; png_name is "" when no PNG was written.
    """
    from django.core.files.base import ContentFile
    from django.core.files.storage import default_storage

    # Forward slashes: these are storage keys, not OS paths — Azure blob names use "/" and
    # FileSystemStorage normalises them per-platform on its own.
    svg_name = default_storage.save(
        f"rendered/{diagram_type}/{diagram_id}.svg",
        ContentFile(svg_content.encode("utf-8")),
    )

    # PNG conversion. If cairosvg isn't available we return NO png path rather than a
    # blank placeholder: a blank white image is indistinguishable from a successful
    # render to every downstream consumer, so it silently prints an empty figure in a
    # student's exam paper. No PNG is a visible, debuggable absence; a blank one isn't.
    png_name = ""
    if CAIROSVG_AVAILABLE:
        try:
            # write_to=None → cairosvg returns the PNG bytes, which we hand to storage
            # (rather than a local path) so it works with a remote backend too.
            png_bytes = cairosvg.svg2png(
                bytestring=svg_content.encode("utf-8"),
                output_width=800,
            )
            png_name = default_storage.save(
                f"rendered/{diagram_type}/{diagram_id}.png",
                ContentFile(png_bytes),
            )
        except Exception:
            logger.exception("SVG→PNG conversion failed for %s; SVG is still saved", diagram_id)
    else:
        logger.warning(
            "cairosvg unavailable — no PNG written for %s (SVG saved). "
            "Install cairosvg + the native cairo library to enable PNG/PDF export.",
            diagram_id,
        )

    return svg_name, png_name


def validate_only(data: Dict[str, Any]) -> ValidationResult:
    """Run validation without rendering."""
    return validate_diagram(data)
