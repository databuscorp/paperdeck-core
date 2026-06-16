"""
Mathematics Diagram Renderer using matplotlib + sympy.
All geometry/calculus computed deterministically.
Exam-style: clean black-and-white output.
"""
from __future__ import annotations

import io
import math
from typing import Any, Dict, List, Optional, Tuple

import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["svg.fonttype"] = "none"   # real <text> nodes in SVG output
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import Arc, FancyArrowPatch
import numpy as np

# sympy for safe expression evaluation
import sympy as sp
from sympy import symbols, lambdify, sympify

from diagrams.schemas.mathematics import (
    FunctionGraphSchema, GeometryTriangleSchema, GeometryCircleSchema,
    CoordinateGeometrySchema, CalculusGraphSchema,
    ConicSectionSchema, VennDiagramSchema, NumberLineSchema,
    BarChartSchema, ScatterPlotSchema, Vector3DSchema,
)

x_sym = symbols("x")

# ── Exam-style matplotlib settings ────────────────────────────────────────────

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
})

AXIS_COLOR = "black"
GRID_COLOR = "#dddddd"
PLOT_COLOR = "black"


def _fig_to_svg(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="svg", bbox_inches="tight", facecolor="white", dpi=100)
    buf.seek(0)
    svg = buf.getvalue().decode("utf-8")
    plt.close(fig)
    return svg


def _safe_eval(expr_str: str, x_vals: np.ndarray) -> Optional[np.ndarray]:
    """Safely evaluate a mathematical expression string over x values."""
    try:
        expr = sympify(expr_str, locals={"x": x_sym})
        f = lambdify(x_sym, expr, modules=["numpy"])
        y = f(x_vals)
        if np.isscalar(y):
            y = np.full_like(x_vals, y, dtype=float)
        return np.asarray(y, dtype=float)
    except Exception as e:
        raise ValueError(f"Invalid expression '{expr_str}': {e}")


def _setup_axes(ax, x_range, y_range=None, x_label="x", y_label="y",
                grid=True, title="", x_ticks=None, x_tick_labels=None):
    """Configure axis with arrows, labels, and optional custom ticks."""
    pad_x = (x_range[1] - x_range[0]) * 0.06
    ax.set_xlim(x_range[0] - pad_x, x_range[1] + pad_x)
    if y_range:
        pad_y = (y_range[1] - y_range[0]) * 0.08
        ax.set_ylim(y_range[0] - pad_y, y_range[1] + pad_y)
    ax.spines["left"].set_position("zero")
    ax.spines["bottom"].set_position("zero")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.xaxis.set_ticks_position("bottom")
    ax.yaxis.set_ticks_position("left")
    if x_label:
        ax.set_xlabel(x_label, fontsize=12, labelpad=2)
    if y_label:
        ax.set_ylabel(y_label, fontsize=12, labelpad=2)
    if title:
        ax.set_title(title, fontsize=13, pad=8)
    if grid:
        ax.grid(True, color=GRID_COLOR, linewidth=0.7, linestyle="--", alpha=0.6)
    # Custom x-ticks with labels
    if x_ticks is not None:
        ax.set_xticks(x_ticks)
        if x_tick_labels is not None:
            ax.set_xticklabels(x_tick_labels, fontsize=11)
    # Arrow tips on axes
    ax.plot(1, 0, ">k", transform=ax.get_yaxis_transform(), clip_on=False, markersize=5)
    ax.plot(0, 1, "^k", transform=ax.get_xaxis_transform(), clip_on=False, markersize=5)


# ── π-axis utilities ──────────────────────────────────────────────────────────

_PI_FRACS = [
    (1, 1), (1, 2), (1, 3), (1, 4), (1, 6),
    (2, 3), (3, 4), (5, 6), (5, 4), (3, 2),
    (7, 4), (2, 1),
]

def _is_pi_multiple(val: float, tol: float = 0.05) -> bool:
    """Return True if val is within tol of any nice π-fraction multiple."""
    if abs(val) < tol:
        return True
    for num, den in _PI_FRACS:
        for sign in (1, -1):
            if abs(val - sign * num * math.pi / den) < tol:
                return True
    return False


def _snap_to_pi(val: float, tol: float = 0.05) -> float:
    """Snap a value to the nearest π-fraction if close enough."""
    if abs(val) < tol:
        return 0.0
    for num, den in _PI_FRACS:
        for sign in (1, -1):
            target = sign * num * math.pi / den
            if abs(val - target) < tol:
                return target
    return val


def _pi_label(val: float, tol: float = 0.05) -> str:
    """Format a value as a π-fraction string, e.g. π/4, -3π/4, π, -π."""
    if abs(val) < tol:
        return "0"
    for num, den in _PI_FRACS:
        for sign in (1, -1):
            if abs(val - sign * num * math.pi / den) < tol:
                prefix = "-" if sign < 0 else ""
                if num == 1 and den == 1:
                    return f"{prefix}π"
                if num == 1:
                    return f"{prefix}π/{den}"
                if den == 1:
                    return f"{prefix}{num}π"
                return f"{prefix}{num}π/{den}"
    return f"{val:.3g}"


def _build_pi_ticks(x_min: float, x_max: float):
    """
    Return (tick_positions, tick_labels) with auto-selected π spacing.
    Uses π/4 for narrow ranges (≤ 2π span) and π/2 for wider ranges (> 2π span).
    Snaps endpoints to exact π multiples first.
    """
    x_min_s = _snap_to_pi(x_min)
    x_max_s = _snap_to_pi(x_max)
    span = x_max_s - x_min_s
    # Choose step: π/4 for spans ≤ 2π, π/2 for spans in (2π, 4π], π for wider
    if span <= 2 * math.pi + 0.01:
        step = math.pi / 4
    elif span <= 4 * math.pi + 0.01:
        step = math.pi / 2
    else:
        step = math.pi
    start_k = math.floor(x_min_s / step + 1e-9)
    end_k = math.ceil(x_max_s / step - 1e-9)
    ticks = []
    for k in range(int(start_k), int(end_k) + 1):
        t = k * step
        if x_min_s - 0.01 <= t <= x_max_s + 0.01:
            ticks.append(t)
    labels = [_pi_label(t) for t in ticks]
    return ticks, labels


def _detect_pi_range(x_min: float, x_max: float) -> bool:
    """Return True if the x-range looks like it's in π-units."""
    return _is_pi_multiple(x_min) and _is_pi_multiple(x_max)


# ── Intersection detection ────────────────────────────────────────────────────

def _find_intersections(x_vals: np.ndarray, y1: np.ndarray, y2: np.ndarray,
                        tol: float = 1e-8) -> List[Tuple[float, float]]:
    """
    Find (x, y) intersection points between two curves via sign-change detection
    followed by bisection refinement.
    """
    diff = y1 - y2
    # Mask NaN
    valid = ~(np.isnan(diff))
    diff_clean = np.where(valid, diff, 0.0)
    sign_changes = np.where(np.diff(np.sign(diff_clean)))[0]

    intersections = []
    for idx in sign_changes:
        xa, xb = x_vals[idx], x_vals[idx + 1]
        fa, fb = diff_clean[idx], diff_clean[idx + 1]
        if fa == fb:
            continue
        # Bisection
        for _ in range(50):
            xm = (xa + xb) / 2
            fm = fa + (xm - xa) / (xb - xa) * (fb - fa)
            if abs(fm) < tol or (xb - xa) < tol:
                break
            if fa * fm < 0:
                xb, fb = xm, fm
            else:
                xa, fa = xm, fm
        xi = (xa + xb) / 2
        yi = float(np.interp(xi, x_vals, y1))
        # De-duplicate (avoid reporting same crossing twice)
        if not any(abs(xi - px) < 1e-4 for px, _ in intersections):
            intersections.append((xi, yi))
    return intersections


# ── 1. Function Graph ──────────────────────────────────────────────────────────

# Auto line-style rotation for black-and-white exam diagrams.
# Index 0 = solid (primary function), 1 = dashed, 2 = dash-dot, 3 = dotted.
_AUTO_LINE_STYLES = ["-", "--", "-.", ":"]
_AUTO_LINE_WIDTHS = [2.2, 2.0, 1.8, 1.8]   # slightly thinner for secondary curves

def render_function_graph(data: Dict[str, Any], canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = FunctionGraphSchema(**data)

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))

    x_min_raw, x_max_raw = schema.x_range
    # Snap to exact π values if close
    x_min = _snap_to_pi(x_min_raw)
    x_max = _snap_to_pi(x_max_raw)

    # High-resolution evaluation (4000 pts for smooth trig curves)
    x_vals = np.linspace(x_min, x_max, 4000)

    # ── Plot each function ────────────────────────────────────────────────────
    all_y_arrays: List[np.ndarray] = []
    all_y_flat: List[float] = []

    _LS_MAP = {"solid": "-", "dashed": "--", "dotted": ":", "dashdot": "-."}

    for i, fn in enumerate(schema.functions):
        fn_range = fn.x_range or (x_min, x_max)
        fn_xmin = _snap_to_pi(fn_range[0])
        fn_xmax = _snap_to_pi(fn_range[1])
        fn_x = np.linspace(fn_xmin, fn_xmax, 4000)
        y = _safe_eval(fn.expression, fn_x)
        y = np.where(np.abs(y) > 1e4, np.nan, y)
        all_y_arrays.append((fn_x, y))

        # Line style: use explicit value if set, otherwise auto-rotate by index
        if fn.line_style is not None:
            ls = _LS_MAP.get(fn.line_style, _AUTO_LINE_STYLES[i % len(_AUTO_LINE_STYLES)])
        else:
            ls = _AUTO_LINE_STYLES[i % len(_AUTO_LINE_STYLES)]

        lw = fn.line_width if fn.line_width != 2.0 else _AUTO_LINE_WIDTHS[i % len(_AUTO_LINE_WIDTHS)]
        label = fn.label or f"f(x) = {fn.expression}"
        ax.plot(fn_x, y, ls, color=PLOT_COLOR, linewidth=lw, label=label, zorder=3)
        all_y_flat.extend(y[~np.isnan(y)].tolist())

    # ── Intersection points ───────────────────────────────────────────────────
    if schema.show_intersections and len(all_y_arrays) >= 2:
        # Compare every pair of functions on their common x-domain
        for i in range(len(all_y_arrays)):
            for j in range(i + 1, len(all_y_arrays)):
                xi_arr, yi_arr = all_y_arrays[i]
                xj_arr, yj_arr = all_y_arrays[j]
                # Interpolate both onto a shared dense grid
                x_common = np.linspace(
                    max(xi_arr[0], xj_arr[0]),
                    min(xi_arr[-1], xj_arr[-1]),
                    8000,
                )
                yi_c = np.interp(x_common, xi_arr, np.nan_to_num(yi_arr, nan=np.inf))
                yj_c = np.interp(x_common, xj_arr, np.nan_to_num(yj_arr, nan=np.inf))
                crossings = _find_intersections(x_common, yi_c, yj_c)

                for cx, cy in crossings:
                    # Snap intersection x to nice π-fraction if possible
                    cx_snapped = _snap_to_pi(cx, tol=0.02)
                    # Draw dashed drop lines to axes
                    ax.plot([cx_snapped, cx_snapped], [0, cy], "k--",
                            linewidth=0.8, alpha=0.55, zorder=2)
                    ax.plot([0, cx_snapped], [cy, cy], "k--",
                            linewidth=0.8, alpha=0.55, zorder=2)
                    # Intersection dot
                    ax.plot(cx_snapped, cy, "ko", markersize=6, zorder=5)
                    # Label
                    if schema.intersection_labels:
                        x_lbl = _pi_label(cx_snapped) if _is_pi_multiple(cx_snapped, tol=0.03) \
                                 else f"{cx_snapped:.3g}"
                        y_lbl = f"{cy:.3g}"
                        ax.annotate(
                            f"({x_lbl}, {y_lbl})",
                            (cx_snapped, cy),
                            textcoords="offset points",
                            xytext=(8, 8),
                            fontsize=10,
                            zorder=6,
                        )

    # ── Explicit special points ───────────────────────────────────────────────
    for pt in schema.special_points:
        sx, sy = pt.get("x", 0), pt.get("y", 0)
        ax.plot(sx, sy, "ko", markersize=5, zorder=5)
        if pt.get("label"):
            ax.annotate(pt["label"], (sx, sy), textcoords="offset points",
                        xytext=(6, 6), fontsize=11)

    # ── Legend ────────────────────────────────────────────────────────────────
    if len(schema.functions) > 1:
        ax.legend(fontsize=11, loc="upper right", framealpha=0.9)

    # ── y-range ───────────────────────────────────────────────────────────────
    y_range = schema.y_range
    if y_range is None and all_y_flat:
        lo, hi = min(all_y_flat), max(all_y_flat)
        margin = max((hi - lo) * 0.18, 0.5)
        y_range = (lo - margin, hi + margin)

    # ── Axis formatting ───────────────────────────────────────────────────────
    use_pi = schema.pi_axis or _detect_pi_range(x_min, x_max)
    x_ticks, x_tick_labels = None, None
    if use_pi:
        x_ticks, x_tick_labels = _build_pi_ticks(x_min, x_max)
    elif schema.x_ticks:
        x_ticks = schema.x_ticks
        x_tick_labels = [str(t) for t in x_ticks]

    _setup_axes(ax, (x_min, x_max), y_range, schema.x_label, schema.y_label,
                schema.grid, schema.title,
                x_ticks=x_ticks, x_tick_labels=x_tick_labels)

    fig.tight_layout(pad=0.8)
    return _fig_to_svg(fig)


# ── 2. Geometry: Triangle ──────────────────────────────────────────────────────

def render_geometry_triangle(data: Dict[str, Any], canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = GeometryTriangleSchema(**data)

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))
    ax.set_aspect("equal")
    ax.axis("off")

    verts = schema.vertices
    xs = [v.x for v in verts]
    ys = [v.y for v in verts]

    # Draw triangle
    triangle = plt.Polygon(list(zip(xs, ys)),
                           fill=schema.fill_color != "none",
                           facecolor=schema.fill_color if schema.fill_color != "none" else "none",
                           edgecolor=schema.stroke_color, linewidth=2)
    ax.add_patch(triangle)

    # Vertex labels (offset outward from centroid)
    cx, cy = sum(xs) / 3, sum(ys) / 3
    for v in verts:
        dx, dy = v.x - cx, v.y - cy
        norm = math.hypot(dx, dy) or 1
        lx = v.x + dx / norm * 0.25
        ly = v.y + dy / norm * 0.25
        ax.text(lx, ly, v.label, fontsize=13, ha="center", va="center", fontweight="bold")

    # Side labels (midpoints)
    for i, side in enumerate(schema.sides[:3]):
        if side.label:
            j = (i + 1) % 3
            mx = (xs[i] + xs[j]) / 2
            my = (ys[i] + ys[j]) / 2
            # Offset perpendicular outward
            dx, dy = xs[j] - xs[i], ys[j] - ys[i]
            length = math.hypot(dx, dy) or 1
            px, py = -dy / length * 0.18, dx / length * 0.18
            toward_centroid = (cx - mx, cy - my)
            dot = toward_centroid[0] * px + toward_centroid[1] * py
            if dot > 0:
                px, py = -px, -py
            ax.text(mx + px, my + py, side.label, fontsize=11, ha="center", va="center",
                    style="italic")

    # Angle arcs
    if schema.show_angle_arcs:
        for i, (v, angle) in enumerate(zip(verts, schema.angles[:3] if schema.angles else [])):
            if angle is not None:
                j = (i + 1) % 3
                k = (i + 2) % 3
                # Draw arc
                a1 = math.degrees(math.atan2(ys[j] - v.y, xs[j] - v.x))
                a2 = math.degrees(math.atan2(ys[k] - v.y, xs[k] - v.x))
                arc = Arc((v.x, v.y), 0.3, 0.3, angle=0,
                          theta1=min(a1, a2), theta2=max(a1, a2),
                          color="black", linewidth=1)
                ax.add_patch(arc)
                # Label
                mid_a = math.radians((a1 + a2) / 2)
                ax.text(v.x + 0.25 * math.cos(mid_a),
                        v.y + 0.25 * math.sin(mid_a),
                        f"{angle:.0f}°", fontsize=9, ha="center", va="center")

    # Right angle mark
    if schema.show_right_angle:
        # Find the right angle vertex (90° in schema.angles)
        for i, a in enumerate(schema.angles[:3] if schema.angles else []):
            if a and abs(a - 90) < 1:
                j = (i + 1) % 3
                k = (i + 2) % 3
                v = verts[i]
                d1x, d1y = xs[j] - v.x, ys[j] - v.y
                d2x, d2y = xs[k] - v.x, ys[k] - v.y
                n1 = math.hypot(d1x, d1y)
                n2 = math.hypot(d2x, d2y)
                s = 0.12
                if n1 > 0 and n2 > 0:
                    p1 = (v.x + d1x / n1 * s, v.y + d1y / n1 * s)
                    p2 = (v.x + d2x / n2 * s, v.y + d2y / n2 * s)
                    pc = (p1[0] + p2[0] - v.x, p1[1] + p2[1] - v.y)
                    sq = plt.Polygon([p1, pc, p2, (v.x, v.y)], fill=False,
                                     edgecolor="black", linewidth=1)
                    ax.add_patch(sq)

    margin = 0.5
    ax.set_xlim(min(xs) - margin, max(xs) + margin)
    ax.set_ylim(min(ys) - margin, max(ys) + margin)
    if schema.title:
        ax.set_title(schema.title, fontsize=13)

    return _fig_to_svg(fig)


# ── 3. Geometry: Circle ────────────────────────────────────────────────────────

def render_geometry_circle(data: Dict[str, Any], canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = GeometryCircleSchema(**data)

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))
    ax.set_aspect("equal")
    ax.axis("off")

    r = 2.5   # radius in data units
    cx, cy = 0.0, 0.0

    # Circle
    circle = plt.Circle((cx, cy), r, fill=False, edgecolor="black", linewidth=2)
    ax.add_patch(circle)

    # Center dot and label
    ax.plot(cx, cy, "ko", markersize=4)
    ax.text(cx - 0.15, cy - 0.22, schema.center_label, fontsize=13, fontweight="bold")

    # Radius
    if schema.show_radius:
        ax.annotate("", xy=(cx + r, cy), xytext=(cx, cy),
                    arrowprops=dict(arrowstyle="-", color="black", lw=1.5))
        ax.text((cx + cx + r) / 2, cy + 0.15, schema.radius_label,
                fontsize=12, ha="center", style="italic")

    # Diameter
    if schema.show_diameter:
        ax.plot([cx - r, cx + r], [cy, cy], "k-", linewidth=1.5)
        ax.text(cx, cy - 0.3, "2r", fontsize=11, ha="center")

    # Chord
    if schema.show_chord:
        chord_y = r * 0.6
        chord_x1 = -math.sqrt(r ** 2 - chord_y ** 2)
        chord_x2 = math.sqrt(r ** 2 - chord_y ** 2)
        ax.plot([chord_x1, chord_x2], [chord_y, chord_y], "k-", linewidth=1.5)
        if schema.chord_label:
            ax.text((chord_x1 + chord_x2) / 2, chord_y + 0.2, schema.chord_label,
                    fontsize=11, ha="center")

    # Tangent
    if schema.show_tangent:
        tx = r * math.cos(math.radians(60))
        ty = r * math.sin(math.radians(60))
        # Tangent is perpendicular to radius at touch point
        normal = math.radians(60)
        tang_len = r * 1.2
        t_dx = -math.sin(normal) * tang_len
        t_dy = math.cos(normal) * tang_len
        ax.plot([tx - t_dx, tx + t_dx], [ty - t_dy, ty + t_dy], "k--", linewidth=1.5)
        ax.plot(tx, ty, "ko", markersize=4)
        if schema.tangent_point_label:
            ax.text(tx + 0.18, ty + 0.18, schema.tangent_point_label, fontsize=11)
        # Radius to tangent point
        ax.plot([cx, tx], [cy, ty], "k-", linewidth=1)

    # Arc sector
    if schema.arc_angle is not None:
        sector = mpatches.Wedge((cx, cy), r, 0, schema.arc_angle,
                                facecolor="lightgray", edgecolor="black",
                                linewidth=1, alpha=0.5)
        ax.add_patch(sector)
        mid_a = math.radians(schema.arc_angle / 2)
        ax.text(cx + r * 0.6 * math.cos(mid_a),
                cy + r * 0.6 * math.sin(mid_a),
                f"{schema.arc_angle:.0f}°", fontsize=11, ha="center")

    margin = r * 0.35
    ax.set_xlim(-r - margin, r + margin)
    ax.set_ylim(-r - margin, r + margin)

    return _fig_to_svg(fig)


# ── 4. Coordinate Geometry ────────────────────────────────────────────────────

def _line_intersection(l1, l2):
    """
    Compute the intersection of two CoordLine objects.
    Returns (x, y) or None if parallel / coincident.
    """
    # Resolve slope/intercept for both lines
    def _slope_intercept(line):
        if line.slope is not None:
            return line.slope, line.intercept or 0.0
        if all(v is not None for v in [line.x1, line.y1, line.x2, line.y2]):
            dx = line.x2 - line.x1
            if abs(dx) < 1e-12:
                return None, line.x1   # vertical line: store x as intercept
            m = (line.y2 - line.y1) / dx
            b = line.y1 - m * line.x1
            return m, b
        return None, None

    m1, b1 = _slope_intercept(l1)
    m2, b2 = _slope_intercept(l2)

    # Both have finite slope
    if m1 is not None and m2 is not None:
        if abs(m1 - m2) < 1e-12:
            return None   # parallel
        x = (b2 - b1) / (m1 - m2)
        y = m1 * x + b1
        return x, y

    # One vertical
    if m1 is None and m2 is not None:   # l1 is vertical: x = b1
        x = b1
        y = m2 * x + b2
        return x, y
    if m2 is None and m1 is not None:   # l2 is vertical: x = b2
        x = b2
        y = m1 * x + b1
        return x, y

    return None   # both vertical — no unique intersection


def render_coordinate_geometry(data: Dict[str, Any], canvas_w: int = 800, canvas_h: int = 600) -> str:
    from diagrams.schemas.mathematics import CoordVector as CoordVec
    schema = CoordinateGeometrySchema(**data)

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))

    x_min, x_max = schema.x_range
    y_min, y_max = schema.y_range
    x_line = np.linspace(x_min, x_max, 800)

    _LS_MAP = {"solid": "-", "dashed": "--", "dotted": ":", "dashdot": "-."}

    # ── 1. Draw lines ─────────────────────────────────────────────────────────
    for li, line in enumerate(schema.lines):
        ls = _LS_MAP.get(line.line_style, "-")
        if line.slope is not None:
            y_line = line.slope * x_line + (line.intercept or 0.0)
            y_line = np.clip(y_line, y_min - 10, y_max + 10)
            ax.plot(x_line, y_line, ls, color=PLOT_COLOR, linewidth=1.8,
                    label=line.label or f"L{li + 1}", zorder=2)
        elif all(v is not None for v in [line.x1, line.y1, line.x2, line.y2]):
            dx = line.x2 - line.x1
            if abs(dx) < 1e-12:
                ax.axvline(x=line.x1, color=PLOT_COLOR, linestyle=ls, linewidth=1.8,
                           label=line.label or f"L{li + 1}", zorder=2)
            else:
                m = (line.y2 - line.y1) / dx
                b = line.y1 - m * line.x1
                y_line = m * x_line + b
                y_line = np.clip(y_line, y_min - 10, y_max + 10)
                ax.plot(x_line, y_line, ls, color=PLOT_COLOR, linewidth=1.8,
                        label=line.label or f"L{li + 1}", zorder=2)

    # ── 2. Auto-compute line-line intersections ───────────────────────────────
    computed_intersections: List[Tuple[float, float]] = []
    if schema.show_line_intersections and len(schema.lines) >= 2:
        for i in range(len(schema.lines)):
            for j in range(i + 1, len(schema.lines)):
                pt = _line_intersection(schema.lines[i], schema.lines[j])
                if pt is not None:
                    ix, iy = pt
                    if x_min <= ix <= x_max and y_min <= iy <= y_max:
                        computed_intersections.append((ix, iy))

    # ── 3. Build the merged point list ───────────────────────────────────────
    # Check if any user-specified point coincides with a computed intersection.
    # If so, merge labels: e.g. "A" at (1,3) merges with "P" → "P=A(1,3)"
    COIN_TOL = 1e-6
    plotted_points = {}   # (x,y) → label string  (de-duplicated)

    for ix, iy in computed_intersections:
        key = (round(ix, 8), round(iy, 8))
        # Is there a user point at this exact location?
        coincident_labels = [
            pt.label for pt in schema.points
            if abs(pt.x - ix) < COIN_TOL and abs(pt.y - iy) < COIN_TOL and pt.label
        ]
        if coincident_labels and schema.merge_coincident_labels:
            # Merge: "P=A(ix, iy)"
            base = schema.intersection_label
            extra = "=".join(coincident_labels)
            merged = f"{base}={extra}\n({ix:.4g}, {iy:.4g})"
        else:
            merged = f"{schema.intersection_label}({ix:.4g}, {iy:.4g})"
        plotted_points[key] = merged

    for pt in schema.points:
        key = (round(pt.x, 8), round(pt.y, 8))
        if key in plotted_points:
            # Already represented by the intersection dot — skip separate dot
            if not schema.merge_coincident_labels:
                pass  # still plot it separately if merge is disabled
            else:
                continue
        if pt.show_dot:
            lbl = pt.label
            if not any(abs(pt.x - ix) < COIN_TOL and abs(pt.y - iy) < COIN_TOL
                       for ix, iy in computed_intersections):
                plotted_points[key] = lbl

    # Draw all de-duplicated points
    for (px, py), lbl in plotted_points.items():
        # Use a star marker for the intersection point P, circle for others
        is_intersect = any(abs(px - ix) < COIN_TOL and abs(py - iy) < COIN_TOL
                           for ix, iy in computed_intersections)
        marker = "*" if is_intersect else "o"
        ms = 10 if is_intersect else 6
        ax.plot(px, py, marker, color="black", markersize=ms, zorder=6)
        if lbl:
            ax.annotate(lbl, (px, py), textcoords="offset points",
                        xytext=(8, 6), fontsize=11, zorder=7,
                        bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.8))

    # ── 4. Draw vectors (arrows from one point to another) ────────────────────
    for vec in schema.vectors:
        dx = vec.to_x - vec.from_x
        dy = vec.to_y - vec.from_y
        ax.annotate(
            "",
            xy=(vec.to_x, vec.to_y),
            xytext=(vec.from_x, vec.from_y),
            arrowprops=dict(
                arrowstyle="-|>",
                color="black",
                lw=1.6,
                mutation_scale=14,
            ),
            zorder=5,
        )
        if vec.label:
            if vec.label_position == "end":
                lx, ly = vec.to_x, vec.to_y
                offset = (8, 4)
            elif vec.label_position == "start":
                lx, ly = vec.from_x, vec.from_y
                offset = (-20, -14)
            else:   # middle
                lx = (vec.from_x + vec.to_x) / 2
                ly = (vec.from_y + vec.to_y) / 2
                # Offset perpendicular to arrow so it doesn't overlap
                length = math.hypot(dx, dy) or 1
                offset = (-dy / length * 14, dx / length * 14)
            ax.annotate(
                vec.label,
                (lx, ly),
                textcoords="offset points",
                xytext=offset,
                fontsize=11,
                fontstyle="italic",
                zorder=7,
            )

    # ── 5. Axis setup ─────────────────────────────────────────────────────────
    _setup_axes(ax, schema.x_range, schema.y_range, "x", "y",
                schema.grid, schema.title)
    if any(ln.label for ln in schema.lines):
        ax.legend(fontsize=10, loc="upper right", framealpha=0.9)

    fig.tight_layout(pad=0.8)
    return _fig_to_svg(fig)


# ── 5. Calculus Graph ──────────────────────────────────────────────────────────

def render_calculus_graph(data: Dict[str, Any], canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = CalculusGraphSchema(**data)

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))

    x_min, x_max = schema.x_range
    x_vals = np.linspace(x_min, x_max, 1000)
    y = _safe_eval(schema.function, x_vals)
    y_clipped = np.where(np.abs(y) > 1e4, np.nan, y)

    ax.plot(x_vals, y_clipped, "k-", linewidth=2.5, label=f"f(x) = {schema.function}")

    # Compute y_range early so zero labels can use it
    y_range = schema.y_range
    if y_range is None:
        valid_y = y_clipped[~np.isnan(y_clipped)]
        if len(valid_y):
            margin = (valid_y.max() - valid_y.min()) * 0.15 + 1
            y_range = (valid_y.min() - margin, valid_y.max() + margin)

    # Shaded regions (integration areas)
    for region in schema.shaded_regions:
        mask = (x_vals >= region.x_from) & (x_vals <= region.x_to)
        ax.fill_between(x_vals[mask], 0, y_clipped[mask],
                        color=region.color, alpha=region.alpha)
        if region.label:
            mid_x = (region.x_from + region.x_to) / 2
            y_mid = _safe_eval(schema.function, np.array([mid_x]))[0] / 2
            ax.text(mid_x, y_mid, region.label, ha="center", va="center", fontsize=11)

    # Derivative overlay
    if schema.show_derivative:
        expr = sympify(schema.function, locals={"x": x_sym})
        deriv_expr = sp.diff(expr, x_sym)
        deriv_fn = lambdify(x_sym, deriv_expr, modules=["numpy"])
        dy = np.asarray(deriv_fn(x_vals), dtype=float)
        dy_clipped = np.where(np.abs(dy) > 1e4, np.nan, dy)
        ax.plot(x_vals, dy_clipped, "k--", linewidth=1.5, alpha=0.7, label="f'(x)")

    # Tangent line at point
    if schema.show_tangent_at is not None:
        xt = schema.show_tangent_at
        yt = _safe_eval(schema.function, np.array([xt]))[0]
        expr = sympify(schema.function, locals={"x": x_sym})
        slope_fn = lambdify(x_sym, sp.diff(expr, x_sym), modules=["numpy"])
        slope = float(slope_fn(xt))
        tang_x = np.linspace(xt - 2, xt + 2, 100)
        tang_y = slope * (tang_x - xt) + yt
        ax.plot(tang_x, tang_y, "k:", linewidth=1.5)
        ax.plot(xt, yt, "ko", markersize=5)
        ax.text(xt + 0.1, yt + 0.3, f"  slope={slope:.2f}", fontsize=10)

    # Zero crossings
    if schema.label_zeros:
        y_no_nan = np.nan_to_num(y_clipped, nan=0.0)
        sign_changes = np.diff(np.sign(y_no_nan))
        for i in np.where(sign_changes)[0]:
            if not np.isnan(y_clipped[i]) and not np.isnan(y_clipped[i + 1]):
                denom = y_clipped[i + 1] - y_clipped[i]
                if abs(denom) < 1e-12:
                    continue
                zero_x = x_vals[i] - y_clipped[i] * (x_vals[i + 1] - x_vals[i]) / denom
                ax.plot(zero_x, 0, "ko", markersize=4)
                # Offset label below axis (proportional to y_range)
                y_offset = -(abs(y_range[1] - y_range[0]) * 0.06 if y_range else 0.4)
                ax.text(zero_x, y_offset, f"({zero_x:.2g}, 0)", fontsize=9, ha="center")

    # Local extrema
    if schema.label_extrema:
        dy_vals = np.gradient(y_clipped, x_vals)
        extrema = np.where(np.diff(np.sign(dy_vals)))[0]
        for idx in extrema[:6]:   # cap to avoid clutter
            if not np.isnan(y_clipped[idx]):
                ax.plot(x_vals[idx], y_clipped[idx], "ko", markersize=4)
                label = f"({x_vals[idx]:.1f}, {y_clipped[idx]:.1f})"
                ax.annotate(label, (x_vals[idx], y_clipped[idx]),
                            textcoords="offset points", xytext=(4, 8), fontsize=9)

    _setup_axes(ax, schema.x_range, y_range, schema.x_label, schema.y_label,
                schema.grid, schema.title)
    ax.legend(fontsize=10)
    fig.tight_layout(pad=0.8)
    return _fig_to_svg(fig)


# ── 6. Conic Section ──────────────────────────────────────────────────────────

def render_conic_section(data: Dict[str, Any],
                          canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = ConicSectionSchema(**data)
    fig, ax = plt.subplots(figsize=(7, 6))

    cx, cy = schema.center_x, schema.center_y
    a, b   = schema.a, schema.b
    ct     = schema.conic_type.lower()
    horiz  = schema.orientation.lower() == "horizontal"

    t = np.linspace(0, 2 * np.pi, 800)

    if ct == "circle":
        r = a
        ax.plot(cx + r * np.cos(t), cy + r * np.sin(t), "k-", lw=2)
        if schema.show_foci and schema.label_foci:
            ax.plot(cx, cy, "ko", markersize=5)
            ax.annotate("O", (cx, cy), textcoords="offset points",
                        xytext=(5, 5), fontsize=10)

    elif ct == "ellipse":
        if horiz:
            xs = cx + a * np.cos(t)
            ys = cy + b * np.sin(t)
        else:
            xs = cx + b * np.cos(t)
            ys = cy + a * np.sin(t)
        ax.plot(xs, ys, "k-", lw=2)
        c_dist = math.sqrt(abs(a**2 - b**2))
        if schema.show_foci:
            if horiz:
                foci = [(cx - c_dist, cy), (cx + c_dist, cy)]
            else:
                foci = [(cx, cy - c_dist), (cx, cy + c_dist)]
            for i, (fx, fy) in enumerate(foci):
                ax.plot(fx, fy, "ko", markersize=5)
                if schema.label_foci:
                    ax.annotate(f"F{i+1}", (fx, fy), textcoords="offset points",
                                xytext=(5, 5), fontsize=10)
        if schema.show_vertices:
            if horiz:
                verts = [(cx - a, cy), (cx + a, cy), (cx, cy - b), (cx, cy + b)]
            else:
                verts = [(cx, cy - a), (cx, cy + a), (cx - b, cy), (cx + b, cy)]
            for vx, vy in verts:
                ax.plot(vx, vy, "ko", markersize=4)

    elif ct == "parabola":
        # y² = 4ax  (horizontal) or x² = 4ay (vertical)
        p = a   # focal parameter
        t_range = np.linspace(-3 * p, 3 * p, 600)
        if horiz:
            xs = cx + t_range**2 / (4 * p)
            ys = cy + t_range
        else:
            xs = cx + t_range
            ys = cy + t_range**2 / (4 * p)
        ax.plot(xs, ys, "k-", lw=2)
        # focus
        if schema.show_foci:
            fx = cx + p if horiz else cx
            fy = cy if horiz else cy + p
            ax.plot(fx, fy, "ko", markersize=5)
            if schema.label_foci:
                ax.annotate("F", (fx, fy), textcoords="offset points",
                            xytext=(5, 5), fontsize=10)
        # directrix
        if schema.show_directrix:
            if horiz:
                ax.axvline(cx - p, color="gray", linestyle="--", lw=1.3)
                ax.text(cx - p - 0.3, cy + 3 * p * 0.8, "directrix",
                        fontsize=9, color="gray", rotation=90, va="top")
            else:
                ax.axhline(cy - p, color="gray", linestyle="--", lw=1.3)
                ax.text(cx + 0.1, cy - p - 0.3, "directrix",
                        fontsize=9, color="gray", ha="left")

    elif ct == "hyperbola":
        c_dist = math.sqrt(a**2 + b**2)
        t_range = np.linspace(-2.5, 2.5, 400)
        if horiz:
            # right branch
            ax.plot(cx + a * np.cosh(t_range), cy + b * np.sinh(t_range), "k-", lw=2)
            # left branch
            ax.plot(cx - a * np.cosh(t_range), cy + b * np.sinh(t_range), "k-", lw=2)
        else:
            ax.plot(cx + b * np.sinh(t_range), cy + a * np.cosh(t_range), "k-", lw=2)
            ax.plot(cx + b * np.sinh(t_range), cy - a * np.cosh(t_range), "k-", lw=2)
        # asymptotes
        if schema.show_asymptotes:
            slope = b / a if horiz else a / b
            x_lim = max(a * 3, b * 3, 8)
            xs_a = np.array([-x_lim + cx, x_lim + cx])
            ax.plot(xs_a, cy + slope * (xs_a - cx), "k--", lw=1, alpha=0.5)
            ax.plot(xs_a, cy - slope * (xs_a - cx), "k--", lw=1, alpha=0.5)
        # foci
        if schema.show_foci:
            if horiz:
                foci = [(cx - c_dist, cy), (cx + c_dist, cy)]
            else:
                foci = [(cx, cy - c_dist), (cx, cy + c_dist)]
            for i, (fx, fy) in enumerate(foci):
                ax.plot(fx, fy, "ko", markersize=5)
                if schema.label_foci:
                    ax.annotate(f"F{i+1}", (fx, fy), textcoords="offset points",
                                xytext=(5, 5), fontsize=10)

    # axes through centre
    pad = max(a, b) * 2.2
    ax.axhline(cy, color="#aaaaaa", lw=0.8, zorder=0)
    ax.axvline(cx, color="#aaaaaa", lw=0.8, zorder=0)
    ax.set_xlim(cx - pad, cx + pad)
    ax.set_ylim(cy - pad, cy + pad)
    ax.set_aspect("equal")
    ax.spines["left"].set_position(("data", cx))
    ax.spines["bottom"].set_position(("data", cy))
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_xlabel("x", fontsize=11)
    ax.set_ylabel("y", fontsize=11)
    title = schema.title or ct.capitalize()
    ax.set_title(title, fontsize=13, fontweight="bold")

    fig.tight_layout(pad=0.8)
    return _fig_to_svg(fig)


# ── 7. Venn Diagram ───────────────────────────────────────────────────────────

def render_venn_diagram(data: Dict[str, Any],
                         canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = VennDiagramSchema(**data)
    n = len(schema.sets)

    fig, ax = plt.subplots(figsize=(7, 5.5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 7)
    ax.set_aspect("equal")
    ax.axis("off")

    # universal set rectangle
    rect = mpatches.FancyBboxPatch((0.3, 0.5), 9.4, 6.0,
                                    boxstyle="square,pad=0",
                                    edgecolor="black", facecolor="white", lw=1.8)
    ax.add_patch(rect)
    if schema.universal_set_label:
        ax.text(0.55, 6.3, schema.universal_set_label, fontsize=12, va="top")

    alpha_fill = 0.22
    circle_colors = ["#1f77b4", "#d62728", "#2ca02c"]

    if n == 2:
        centres = [(3.8, 3.5), (6.2, 3.5)]
        radius  = 1.9
        # draw circles
        for i, (cx, cy) in enumerate(centres):
            circ = plt.Circle((cx, cy), radius, color=circle_colors[i],
                               alpha=alpha_fill, zorder=2)
            ax.add_patch(circ)
            circ_edge = plt.Circle((cx, cy), radius, fill=False,
                                    edgecolor=circle_colors[i], lw=2, zorder=3)
            ax.add_patch(circ_edge)
            # set label (outer region)
            lbl_x = cx + (radius + 0.4) * (-1 if i == 0 else 1)
            ax.text(lbl_x, cy + radius + 0.3, schema.sets[i].label,
                    ha="center", fontsize=13, fontweight="bold",
                    color=circle_colors[i])
            if schema.sets[i].region_value:
                region_x = cx - 0.8 if i == 0 else cx + 0.8
                ax.text(region_x, cy, schema.sets[i].region_value,
                        ha="center", va="center", fontsize=12)
        # intersection label
        if schema.intersection_labels:
            ax.text(5.0, 3.5, schema.intersection_labels[0],
                    ha="center", va="center", fontsize=12)

    elif n == 3:
        # Three overlapping circles — classic trefoil layout
        centres = [(4.5, 4.5), (5.5, 4.5), (5.0, 3.2)]
        radius  = 1.55
        for i, (cx, cy) in enumerate(centres):
            circ = plt.Circle((cx, cy), radius, color=circle_colors[i],
                               alpha=alpha_fill, zorder=2)
            ax.add_patch(circ)
            circ_edge = plt.Circle((cx, cy), radius, fill=False,
                                    edgecolor=circle_colors[i], lw=2, zorder=3)
            ax.add_patch(circ_edge)
            # label outside
            offsets = [(-0.5, 0.5), (0.5, 0.5), (0.0, -0.7)]
            lbl_x = cx + offsets[i][0] * (radius + 0.5)
            lbl_y = cy + offsets[i][1] * (radius + 0.5)
            ax.text(lbl_x, lbl_y, schema.sets[i].label,
                    ha="center", fontsize=12, fontweight="bold",
                    color=circle_colors[i])
            if schema.sets[i].region_value:
                ax.text(cx + offsets[i][0] * 0.5, cy + offsets[i][1] * 0.5,
                        schema.sets[i].region_value,
                        ha="center", va="center", fontsize=11)
        # pairwise intersection labels (up to 3 + centre)
        inter_positions = [(5.0, 4.5), (4.85, 3.85), (5.15, 3.85), (5.0, 4.15)]
        for j, ilbl in enumerate(schema.intersection_labels[:4]):
            px, py = inter_positions[j]
            ax.text(px, py, ilbl, ha="center", va="center", fontsize=11)

    title = schema.title
    if title:
        ax.set_title(title, fontsize=13, fontweight="bold", pad=4)

    fig.tight_layout(pad=0.5)
    return _fig_to_svg(fig)


# ── 8. Number Line ─────────────────────────────────────────────────────────────

def render_number_line(data: Dict[str, Any],
                        canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = NumberLineSchema(**data)

    fig, ax = plt.subplots(figsize=(8, 2.5))

    x_min, x_max = schema.x_min, schema.x_max
    span = x_max - x_min
    pad  = span * 0.08

    # main axis line with arrowheads
    ax.annotate("", xy=(x_max + pad, 0), xytext=(x_min - pad, 0),
                arrowprops=dict(arrowstyle="->, head_width=0.15, head_length=0.2",
                                color="black", lw=1.5))

    # tick marks
    step = max(1.0, span / 10)
    # round step to nice number
    for power in [0.5, 1, 2, 5, 10]:
        if span / power <= 12:
            step = power
            break
    ticks = np.arange(math.ceil(x_min / step) * step,
                      math.floor(x_max / step) * step + step * 0.5,
                      step)
    for t in ticks:
        ax.plot([t, t], [-0.12, 0.12], color="black", lw=1)
        ax.text(t, -0.28, f"{t:g}", ha="center", va="top", fontsize=10)

    # intervals (shaded segments)
    for ivl in schema.intervals:
        seg_x = [ivl.start, ivl.end]
        ax.plot(seg_x, [0, 0], color=ivl.color, lw=5, solid_capstyle="butt",
                alpha=0.6, zorder=2)
        # endpoint circles
        for val, filled in [(ivl.start, ivl.filled_start),
                             (ivl.end,   ivl.filled_end)]:
            fc = ivl.color if filled else "white"
            ax.plot(val, 0, "o", markersize=9, color=ivl.color,
                    markerfacecolor=fc, markeredgewidth=1.8, zorder=3)

    # individual points
    for pt in schema.points:
        fc = "black" if pt.filled else "white"
        ax.plot(pt.value, 0, "o", markersize=10, color="black",
                markerfacecolor=fc, markeredgewidth=2, zorder=4)
        if pt.label:
            ax.text(pt.value, 0.32, pt.label, ha="center", va="bottom",
                    fontsize=11, fontweight="bold")

    # axis label
    ax.text(x_max + pad + 0.3, 0, schema.axis_label, ha="left",
            va="center", fontsize=12, style="italic")

    ax.set_xlim(x_min - pad * 2, x_max + pad * 2)
    ax.set_ylim(-0.7, 0.8)
    ax.axis("off")
    if schema.title:
        ax.set_title(schema.title, fontsize=13, fontweight="bold")

    fig.tight_layout(pad=0.3)
    return _fig_to_svg(fig)


# ── Bar Chart / Histogram ─────────────────────────────────────────────────────

def render_bar_chart(data: Dict[str, Any], canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = BarChartSchema(**data)

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))

    labels = [b.label for b in schema.bars]
    values = [b.value for b in schema.bars]

    # Color scheme
    color_map = {
        "blue": ["#2980B9"] * len(labels),
        "rainbow": plt.cm.Set3(np.linspace(0, 1, len(labels))),
    }
    if schema.color_scheme in color_map:
        colors = color_map[schema.color_scheme]
    else:
        # Use individual colors if specified, else cycle a default palette
        palette = ["#3498DB", "#E74C3C", "#2ECC71", "#F39C12",
                   "#9B59B6", "#1ABC9C", "#E67E22", "#34495E"]
        colors = [
            b.color if b.color else palette[i % len(palette)]
            for i, b in enumerate(schema.bars)
        ]

    x = np.arange(len(labels))
    bars = ax.bar(x, values, color=colors, edgecolor="white", linewidth=0.8,
                  width=0.6)

    if schema.show_values:
        for bar, val in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + max(values) * 0.01,
                    f"{val:g}", ha="center", va="bottom", fontsize=9)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=10)
    if schema.x_label:
        ax.set_xlabel(schema.x_label, fontsize=11)
    ax.set_ylabel(schema.y_label, fontsize=11)
    if schema.show_grid:
        ax.yaxis.grid(True, color=GRID_COLOR, zorder=0)
        ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    title = schema.title or ("Histogram" if schema.chart_type == "histogram" else "Bar Chart")
    ax.set_title(title, fontsize=13, fontweight="bold")
    fig.tight_layout()
    return _fig_to_svg(fig)


# ── Scatter Plot with Regression Line ────────────────────────────────────────

def render_scatter_plot(data: Dict[str, Any], canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = ScatterPlotSchema(**data)

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))

    xs = np.array([p.x for p in schema.points])
    ys = np.array([p.y for p in schema.points])

    ax.scatter(xs, ys, color=schema.point_color, s=50, zorder=5, edgecolors="white", linewidths=0.5)

    # Point labels
    for pt in schema.points:
        if pt.label:
            ax.annotate(pt.label, (pt.x, pt.y),
                        textcoords="offset points", xytext=(5, 5), fontsize=7, color="gray")

    # Regression line
    if schema.show_regression_line and len(xs) >= 2:
        deg = schema.regression_degree
        coeffs = np.polyfit(xs, ys, deg)
        poly = np.poly1d(coeffs)
        x_fit = np.linspace(xs.min(), xs.max(), 300)
        y_fit = poly(x_fit)
        ax.plot(x_fit, y_fit, color=schema.line_color, linewidth=1.8,
                linestyle="--", label=f"Degree-{deg} fit", zorder=4)

        if schema.show_r_squared:
            y_pred = poly(xs)
            ss_res = np.sum((ys - y_pred) ** 2)
            ss_tot = np.sum((ys - np.mean(ys)) ** 2)
            r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 1.0
            ax.text(0.98, 0.05, f"R² = {r2:.3f}",
                    transform=ax.transAxes, ha="right", fontsize=10,
                    color=schema.line_color,
                    bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                              edgecolor=schema.line_color, alpha=0.8))

        ax.legend(fontsize=8, loc="upper left")

    ax.set_xlabel(schema.x_label, fontsize=11)
    ax.set_ylabel(schema.y_label, fontsize=11)
    if schema.show_grid:
        ax.grid(True, color=GRID_COLOR, alpha=0.6)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    title = schema.title or "Scatter Plot"
    ax.set_title(title, fontsize=13, fontweight="bold")
    fig.tight_layout()
    return _fig_to_svg(fig)


# ── 3D Vector Diagram ─────────────────────────────────────────────────────────

def render_vector_3d(data: Dict[str, Any], canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = Vector3DSchema(**data)

    from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

    fig = plt.figure(figsize=(canvas_w / 100, canvas_h / 100))
    ax = fig.add_subplot(111, projection="3d")

    # Determine axis limits from vector endpoints
    all_pts = [(v.origin_x + v.x, v.origin_y + v.y, v.origin_z + v.z) for v in schema.vectors]
    all_pts += [(v.origin_x, v.origin_y, v.origin_z) for v in schema.vectors]
    all_xs, all_ys, all_zs = zip(*all_pts)
    pad = 0.5
    lim = max(max(abs(c) for c in all_xs + all_ys + all_zs), 1.0) + pad

    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)
    ax.set_zlim(-lim, lim)

    if schema.show_axes:
        ax.set_xlabel(schema.axis_labels[0] if len(schema.axis_labels) > 0 else "x", fontsize=9)
        ax.set_ylabel(schema.axis_labels[1] if len(schema.axis_labels) > 1 else "y", fontsize=9)
        ax.set_zlabel(schema.axis_labels[2] if len(schema.axis_labels) > 2 else "z", fontsize=9)

    if not schema.show_grid:
        ax.grid(False)

    # Draw vectors as quiver arrows
    for vec in schema.vectors:
        ax.quiver(
            vec.origin_x, vec.origin_y, vec.origin_z,
            vec.x, vec.y, vec.z,
            color=vec.color if vec.color else "blue",
            arrow_length_ratio=0.15,
            linewidth=2,
        )
        # Label at tip
        if vec.label:
            tip_x = vec.origin_x + vec.x
            tip_y = vec.origin_y + vec.y
            tip_z = vec.origin_z + vec.z
            ax.text(tip_x, tip_y, tip_z, f"  {vec.label}", fontsize=9,
                    color=vec.color if vec.color else "blue", fontweight="bold")

    # Projections onto xy-plane
    if schema.show_projections:
        for vec in schema.vectors:
            tip_x = vec.origin_x + vec.x
            tip_y = vec.origin_y + vec.y
            tip_z = vec.origin_z + vec.z
            # Dashed line from tip to xy-plane
            ax.plot([tip_x, tip_x], [tip_y, tip_y], [tip_z, 0],
                    color="gray", linestyle=":", linewidth=1)
            # Projection arrow on xy-plane
            ax.quiver(vec.origin_x, vec.origin_y, 0,
                      vec.x, vec.y, 0,
                      color="gray", alpha=0.4, arrow_length_ratio=0.15)

    # Angle between first two vectors
    if schema.show_angle_between and len(schema.vectors) >= 2:
        v1 = np.array([schema.vectors[0].x, schema.vectors[0].y, schema.vectors[0].z])
        v2 = np.array([schema.vectors[1].x, schema.vectors[1].y, schema.vectors[1].z])
        n1, n2 = np.linalg.norm(v1), np.linalg.norm(v2)
        if n1 > 0 and n2 > 0:
            cos_a = np.clip(np.dot(v1, v2) / (n1 * n2), -1, 1)
            angle_deg = np.degrees(np.arccos(cos_a))
            ax.text2D(0.02, 0.95, f"θ = {angle_deg:.1f}°",
                      transform=ax.transAxes, fontsize=10, color="#8E44AD")

    title = schema.title or "3D Vector Diagram"
    ax.set_title(title, fontsize=12, fontweight="bold", pad=10)
    fig.tight_layout()
    return _fig_to_svg(fig)


# ── Dispatcher ────────────────────────────────────────────────────────────────

MATHEMATICS_RENDERERS = {
    "function_graph": render_function_graph,
    "geometry_triangle": render_geometry_triangle,
    "geometry_circle": render_geometry_circle,
    "coordinate_geometry": render_coordinate_geometry,
    "calculus_graph": render_calculus_graph,
    "conic_section": render_conic_section,
    "venn_diagram": render_venn_diagram,
    "number_line": render_number_line,
    "bar_chart": render_bar_chart,
    "scatter_plot": render_scatter_plot,
    "vector_3d": render_vector_3d,
}


def render_mathematics(subtype: str, params: Dict[str, Any],
                       canvas_w: int = 800, canvas_h: int = 600) -> str:
    renderer = MATHEMATICS_RENDERERS.get(subtype)
    if not renderer:
        raise ValueError(f"Unknown mathematics subtype: '{subtype}'. "
                         f"Supported: {list(MATHEMATICS_RENDERERS.keys())}")
    return renderer(params, canvas_w=canvas_w, canvas_h=canvas_h)
