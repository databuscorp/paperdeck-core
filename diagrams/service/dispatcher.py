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

import io
import os
import time
import traceback
import uuid
from typing import Any, Dict, Optional, Tuple

from django.conf import settings

from diagrams.validators.schema_validator import validate_diagram, ValidationResult
from diagrams.service.physics.renderer import render_physics
from diagrams.service.chemistry.renderer import render_chemistry
from diagrams.service.mathematics.renderer import render_mathematics
from diagrams.service.circuits.renderer import render_circuits
from diagrams.service.biology.renderer import render_biology

# ── Optional PNG conversion ───────────────────────────────────────────────────
try:
    import cairosvg
    CAIROSVG_AVAILABLE = True
except ImportError:
    CAIROSVG_AVAILABLE = False

try:
    from PIL import Image as PILImage
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


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
    Save SVG (and optionally PNG) to media/rendered/{diagram_type}/.
    Returns (relative_svg_path, relative_png_path).
    """
    media_root = getattr(settings, "MEDIA_ROOT", "/tmp/media")
    render_dir = os.path.join(media_root, "rendered", diagram_type)
    os.makedirs(render_dir, exist_ok=True)

    svg_filename = f"{diagram_id}.svg"
    svg_abs_path = os.path.join(render_dir, svg_filename)
    with open(svg_abs_path, "w", encoding="utf-8") as f:
        f.write(svg_content)
    svg_rel_path = os.path.join("rendered", diagram_type, svg_filename)

    # PNG conversion
    png_rel_path = ""
    png_filename = f"{diagram_id}.png"
    png_abs_path = os.path.join(render_dir, png_filename)
    try:
        if CAIROSVG_AVAILABLE:
            cairosvg.svg2png(
                bytestring=svg_content.encode("utf-8"),
                write_to=png_abs_path,
                output_width=800,
            )
            png_rel_path = os.path.join("rendered", diagram_type, png_filename)
        elif PIL_AVAILABLE:
            # Minimal: save a blank PNG as placeholder (no real SVG→PNG without cairosvg)
            img = PILImage.new("RGB", (800, 600), color=(255, 255, 255))
            img.save(png_abs_path)
            png_rel_path = os.path.join("rendered", diagram_type, png_filename)
    except Exception:
        pass  # PNG is optional; SVG is always saved

    return svg_rel_path, png_rel_path


def validate_only(data: Dict[str, Any]) -> ValidationResult:
    """Run validation without rendering."""
    return validate_diagram(data)
