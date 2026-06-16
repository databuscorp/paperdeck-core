"""
LaTeX Rendering Service.

Parses text containing $...$ (inline) and $$...$$ (display) math delimiters,
renders each math segment to SVG using matplotlib's mathtext engine
(no LaTeX installation required — uses Py-side TeX parser).

Public API
----------
parse_segments(text)          → List[Segment]   – split text into text/math parts
render_segments(segments)     → List[SegmentDict]  – add SVG to math segments
render_text(text)             → List[SegmentDict]  – convenience: parse + render
validate_expression(expr)     → (bool, str|None)   – check if expr renders OK
has_math(text)                → bool
"""
from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams.update({
    "svg.fonttype": "none",
    "figure.facecolor": "none",   # transparent background for inline math
    "axes.facecolor": "none",
})
import matplotlib.pyplot as plt


# ── Segment types ─────────────────────────────────────────────────────────────

SEGMENT_TEXT         = "text"
SEGMENT_MATH_INLINE  = "math_inline"   # $...$
SEGMENT_MATH_BLOCK   = "math_block"    # $$...$$


@dataclass
class Segment:
    type:    str            # SEGMENT_TEXT | SEGMENT_MATH_INLINE | SEGMENT_MATH_BLOCK
    content: str            # raw text OR raw LaTeX expression (no delimiters)
    svg:     Optional[str] = field(default=None, repr=False)
    error:   Optional[str] = None


# ── Parser ────────────────────────────────────────────────────────────────────

# Matches $$ before $, non-greedy, with DOTALL so expressions can span lines.
# Groups: ($$-content$$) | ($-content$)
_MATH_RE = re.compile(
    r'\$\$(.+?)\$\$'   # display math  $$...$$
    r'|\$(.+?)\$',     # inline math   $...$
    re.DOTALL,
)


def parse_segments(text: str) -> List[Segment]:
    """Split *text* into alternating text / math Segment objects."""
    if not text:
        return [Segment(type=SEGMENT_TEXT, content="")]

    segments: List[Segment] = []
    cursor = 0

    for match in _MATH_RE.finditer(text):
        start, end = match.span()

        # Plain text before this match
        if start > cursor:
            segments.append(Segment(type=SEGMENT_TEXT, content=text[cursor:start]))

        if match.group(1) is not None:            # $$...$$
            segments.append(Segment(
                type=SEGMENT_MATH_BLOCK,
                content=match.group(1).strip(),
            ))
        else:                                     # $...$
            segments.append(Segment(
                type=SEGMENT_MATH_INLINE,
                content=match.group(2).strip(),
            ))

        cursor = end

    # Remaining text after last match
    if cursor < len(text):
        segments.append(Segment(type=SEGMENT_TEXT, content=text[cursor:]))

    return segments or [Segment(type=SEGMENT_TEXT, content=text)]


def has_math(text: str) -> bool:
    """Return True if *text* contains any $...$ or $$...$$ delimiters."""
    return bool(_MATH_RE.search(text or ""))


# ── Renderer ──────────────────────────────────────────────────────────────────

# Font sizes for inline vs. display math (in points)
_INLINE_FONTSIZE  = 13
_BLOCK_FONTSIZE   = 15


def _expr_to_svg(expr: str, fontsize: int, color: str = "black") -> Tuple[str, Optional[str]]:
    """
    Render a single LaTeX math expression to an SVG string.

    Returns (svg_string, None) on success, ("", error_message) on failure.
    Uses matplotlib mathtext — covers the full exam math vocabulary:
    fractions, integrals, derivatives, Greek letters, vectors, etc.
    """
    # Wrap in $...$ so matplotlib knows it's math mode
    math_text = f"${expr}$"

    try:
        # Create a tiny throwaway figure — we only want the text bbox
        fig = plt.figure(figsize=(0.01, 0.01))
        text_obj = fig.text(
            0.5, 0.5, math_text,
            fontsize=fontsize,
            ha="center", va="center",
            color=color,
            usetex=False,   # use matplotlib's own mathtext parser
        )

        # Render once to get the actual bounding box
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        bbox = text_obj.get_window_extent(renderer=renderer)

        dpi = fig.get_dpi()
        pad_px = 4
        w_in = (bbox.width  + pad_px) / dpi
        h_in = (bbox.height + pad_px) / dpi
        # Guard against degenerate sizes
        w_in = max(w_in, 0.05)
        h_in = max(h_in, 0.05)

        fig.set_size_inches(w_in, h_in)

        buf = io.BytesIO()
        fig.savefig(buf, format="svg", bbox_inches="tight",
                    transparent=True, pad_inches=0.02)
        buf.seek(0)
        svg = buf.getvalue().decode("utf-8")
        plt.close(fig)
        return svg, None

    except Exception as exc:
        plt.close("all")
        return "", str(exc)


def render_segments(segments: List[Segment], color: str = "black") -> List[Segment]:
    """
    Mutate *segments* in-place: fill `.svg` for every math segment.
    Returns the same list (mutated) for chaining.
    """
    for seg in segments:
        if seg.type == SEGMENT_MATH_INLINE:
            svg, err = _expr_to_svg(seg.content, _INLINE_FONTSIZE, color)
            seg.svg   = svg or None
            seg.error = err
        elif seg.type == SEGMENT_MATH_BLOCK:
            svg, err = _expr_to_svg(seg.content, _BLOCK_FONTSIZE, color)
            seg.svg   = svg or None
            seg.error = err
    return segments


def render_text(text: str, color: str = "black") -> List[Segment]:
    """Parse *text* and render all math segments. Convenience wrapper."""
    return render_segments(parse_segments(text), color=color)


# ── Validation ────────────────────────────────────────────────────────────────

def validate_expression(expr: str) -> Tuple[bool, Optional[str]]:
    """
    Try to render *expr* (without delimiters) via matplotlib mathtext.
    Returns (True, None) if valid, (False, error_message) if not.
    """
    _, err = _expr_to_svg(expr, _INLINE_FONTSIZE)
    return (err is None, err)


# ── Segment → dict serialisation ─────────────────────────────────────────────

def segment_to_dict(seg: Segment) -> dict:
    d: dict = {"type": seg.type, "content": seg.content}
    if seg.svg is not None:
        d["svg"] = seg.svg
    if seg.error is not None:
        d["error"] = seg.error
    return d
