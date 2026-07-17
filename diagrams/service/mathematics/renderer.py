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
matplotlib.rcParams["svg.hashsalt"] = "paperdeck"   # deterministic element ids
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import Arc, FancyArrowPatch
from matplotlib.ticker import FuncFormatter
import numpy as np

# sympy for safe expression evaluation
import sympy as sp
from sympy import symbols, lambdify, sympify

from diagrams.service.safeexpr import UnsafeExpression, parse_safe
from diagrams.service.shared.xygraph import render_annotated_xy_graph
from sympy.parsing.sympy_parser import (
    convert_xor, implicit_multiplication_application, parse_expr,
    standard_transformations,
)

from diagrams.schemas.mathematics import (
    FunctionGraphSchema, GeometryTriangleSchema, GeometryCircleSchema,
    CoordinateGeometrySchema, CalculusGraphSchema,
    ConicSectionSchema, VennDiagramSchema, NumberLineSchema,
    BarChartSchema, ScatterPlotSchema, Vector3DSchema,
    PieChartSchema, LineChartSchema, Solid3DSchema,
    ArgandDiagramSchema, ArgandPoint,
    LinearProgrammingSchema, LPConstraint, LPObjective,
    HistogramSchema, ProbabilityTreeSchema,
    HeightDistanceSchema, HDObject,
    CombinedSolidSchema, SolidComponent, _cs_face, _cs_flipped,
    PlaneLine3DSchema, Plane3D, Line3D,
    DistributionCurveSchema,
    PiecewiseGraphSchema, CircleTheoremSchema, SimilarTrianglesSchema,
    GeometricConstructionSchema, SolidOfRevolutionSchema,
    GraphTransformationSchema, BoxPlotSchema,
)

x_sym = symbols("x")
y_sym = symbols("y")

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
    fig.savefig(buf, format="svg", bbox_inches="tight", facecolor="white", dpi=100,
                metadata={"Date": None})   # no timestamp → deterministic output
    buf.seek(0)
    svg = buf.getvalue().decode("utf-8")
    plt.close(fig)
    return svg


def _safe_eval(expr_str: str, x_vals: np.ndarray) -> Optional[np.ndarray]:
    """Evaluate a model-supplied expression over x values.

    Goes through parse_safe, not sympify: sympify eval()s the string, so it will happily run
    `__import__('os').system(...)` handed to it by the model. See diagrams/service/safeexpr.py.
    """
    try:
        expr = parse_safe(expr_str, ("x",))
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
        expr = parse_safe(schema.function, ("x",))
        deriv_expr = sp.diff(expr, x_sym)
        deriv_fn = lambdify(x_sym, deriv_expr, modules=["numpy"])
        dy = np.asarray(deriv_fn(x_vals), dtype=float)
        dy_clipped = np.where(np.abs(dy) > 1e4, np.nan, dy)
        ax.plot(x_vals, dy_clipped, "k--", linewidth=1.5, alpha=0.7, label="f'(x)")

    # Tangent line at point
    if schema.show_tangent_at is not None:
        xt = schema.show_tangent_at
        yt = _safe_eval(schema.function, np.array([xt]))[0]
        expr = parse_safe(schema.function, ("x",))
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


# ── Pie Chart ─────────────────────────────────────────────────────────────────

def render_pie_chart(data: Dict[str, Any], canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = PieChartSchema(**data)

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))

    values = [s.value for s in schema.slices]
    labels = [s.label for s in schema.slices]
    total = sum(values)

    palette = ["#3498DB", "#E74C3C", "#2ECC71", "#F39C12",
               "#9B59B6", "#1ABC9C", "#E67E22", "#34495E"]
    colors = [
        s.color if s.color else palette[i % len(palette)]
        for i, s in enumerate(schema.slices)
    ]

    # Exploded slice (pull one wedge out by label)
    explode = [
        0.08 if (schema.explode_slice and s.label == schema.explode_slice) else 0.0
        for s in schema.slices
    ]

    # Per-slice wedge text: percentage (from proper angle math on values)
    # and/or raw value.
    wedge_texts: List[str] = []
    for v in values:
        parts = []
        if schema.show_percentages:
            parts.append(f"{v / total * 100:.1f}%")
        if schema.show_values:
            parts.append(f"({v:g})")
        wedge_texts.append("\n".join(parts))

    autopct = None
    if schema.show_percentages or schema.show_values:
        text_iter = iter(wedge_texts)
        autopct = lambda pct: next(text_iter)   # noqa: E731  (deterministic wedge order)

    wedges, *_ = ax.pie(
        values,
        labels=None if schema.show_legend else labels,
        colors=colors,
        explode=explode,
        autopct=autopct,
        pctdistance=0.68,
        startangle=90,
        counterclock=False,
        wedgeprops=dict(edgecolor="white", linewidth=1.2),
        textprops=dict(fontsize=10, color="black"),
    )

    if schema.show_legend:
        ax.legend(wedges, labels, fontsize=10, loc="center left",
                  bbox_to_anchor=(1.0, 0.5), framealpha=0.9)

    ax.set_aspect("equal")
    title = schema.title or "Pie Chart"
    ax.set_title(title, fontsize=13, fontweight="bold")
    fig.tight_layout()
    return _fig_to_svg(fig)


# ── Line Chart (data-interpretation / time-series) ────────────────────────────

def render_line_chart(data: Dict[str, Any], canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = LineChartSchema(**data)

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))

    _LS_MAP = {"solid": "-", "dashed": "--"}
    palette = ["#2980B9", "#C0392B", "#27AE60", "#8E44AD",
               "#D68910", "#16A085", "#7F8C8D", "#2C3E50"]
    markers = ["o", "s", "^", "D", "v", "P"]

    for i, series in enumerate(schema.series):
        xs = [p.x for p in series.points]
        ys = [p.y for p in series.points]
        color = series.color if series.color else palette[i % len(palette)]
        ls = _LS_MAP.get(series.line_style, "-")
        marker = markers[i % len(markers)] if series.marker else None
        ax.plot(xs, ys, linestyle=ls, color=color, linewidth=2.0,
                marker=marker, markersize=6, markerfacecolor=color,
                markeredgecolor="white", markeredgewidth=0.8,
                label=series.label or f"Series {i + 1}", zorder=3)

    ax.margins(x=0.06, y=0.10)   # autoscale with breathing room
    # Integer x-ticks when all x values are whole numbers (years, months, …)
    all_x = [p.x for s in schema.series for p in s.points]
    if all(float(v).is_integer() for v in all_x):
        from matplotlib.ticker import MaxNLocator
        ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.set_xlabel(schema.x_label, fontsize=11)
    ax.set_ylabel(schema.y_label, fontsize=11)
    if schema.show_grid:
        ax.grid(True, color=GRID_COLOR, linewidth=0.7, linestyle="--", alpha=0.7)
        ax.set_axisbelow(True)
    if schema.show_legend and (len(schema.series) > 1 or any(s.label for s in schema.series)):
        ax.legend(fontsize=10, loc="best", framealpha=0.9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    title = schema.title or "Line Chart"
    ax.set_title(title, fontsize=13, fontweight="bold")
    fig.tight_layout()
    return _fig_to_svg(fig)


# ── 3D Solid (mensuration figure, 2D oblique projection) ─────────────────────

_SOLID_EDGE = dict(color="black", linewidth=1.8, solid_capstyle="round")
_HIDDEN_EDGE = dict(color="black", linewidth=1.1, linestyle=(0, (5, 4)))
_DIM_FONT = dict(fontsize=11, style="italic")
_ELLIPSE_RATIO = 0.32   # perspective foreshortening of circular faces
_OBLIQUE_DX = 0.42      # depth direction (cabinet projection)
_OBLIQUE_DY = 0.30


def _dim(name: str, value: float, unit: str) -> str:
    return f"{name} = {value:g} {unit}".strip()


def _ellipse_halves(cx: float, cy: float, rx: float, ry: float):
    """Return (front_x, front_y, back_x, back_y) point arrays for a horizontal
    ellipse seen in perspective: front = lower half, back = upper half."""
    t_front = np.linspace(np.pi, 2 * np.pi, 100)
    t_back = np.linspace(0, np.pi, 100)
    return (cx + rx * np.cos(t_front), cy + ry * np.sin(t_front),
            cx + rx * np.cos(t_back), cy + ry * np.sin(t_back))


def _draw_base_ellipse(ax, cx, cy, rx, ry, show_hidden: bool):
    """Circular face seen edge-on: solid front (lower) half, dashed back half."""
    fx, fy, bx, by = _ellipse_halves(cx, cy, rx, ry)
    ax.plot(fx, fy, **_SOLID_EDGE)
    if show_hidden:
        ax.plot(bx, by, **_HIDDEN_EDGE)
    else:
        ax.plot(bx, by, **_SOLID_EDGE)


def _draw_full_ellipse(ax, cx, cy, rx, ry):
    t = np.linspace(0, 2 * np.pi, 200)
    ax.plot(cx + rx * np.cos(t), cy + ry * np.sin(t), **_SOLID_EDGE)


def _draw_box(ax, schema, l: float, w: float, h: float,
              dim_labels: List[Tuple[str, float]]):
    """Oblique (cabinet) projection of a cuboid.
    dim_labels = [(name, value)] for (length, width, height) — cube passes one."""
    scale = 3.2 / max(l, w, h)
    L, W, H = l * scale, w * scale, h * scale
    dx, dy = W * _OBLIQUE_DX, W * _OBLIQUE_DY

    # Front face A,B,C,D (counterclockwise from bottom-left); back face A2..D2
    A, B, C, D = (0, 0), (L, 0), (L, H), (0, H)
    A2, B2, C2, D2 = (dx, dy), (L + dx, dy), (L + dx, H + dy), (dx, H + dy)

    visible = [(A, B), (B, C), (C, D), (D, A),          # front face
               (D, D2), (C, C2), (B, B2),               # receding edges
               (D2, C2), (C2, B2)]                      # back top + back right
    hidden = [(A, A2), (A2, B2), (A2, D2)]              # meet at hidden vertex A2

    for p, q in visible:
        ax.plot([p[0], q[0]], [p[1], q[1]], **_SOLID_EDGE)
    for p, q in hidden:
        style = _HIDDEN_EDGE if schema.show_hidden_edges else _SOLID_EDGE
        ax.plot([p[0], q[0]], [p[1], q[1]], **style)

    if schema.show_dimensions:
        names = [n for n, _ in dim_labels]
        if len(dim_labels) == 1:   # cube: label one edge
            name, val = dim_labels[0]
            ax.text(L / 2, -0.28, _dim(name, val, schema.unit),
                    ha="center", va="top", **_DIM_FONT)
        else:                      # cuboid: length, width, height
            ax.text(L / 2, -0.28, _dim(names[0], dim_labels[0][1], schema.unit),
                    ha="center", va="top", **_DIM_FONT)
            ax.text(L + dx / 2 + 0.15, dy / 2 - 0.22,
                    _dim(names[1], dim_labels[1][1], schema.unit),
                    ha="left", va="center", **_DIM_FONT)
            ax.text(L + dx + 0.18, dy + H / 2,
                    _dim(names[2], dim_labels[2][1], schema.unit),
                    ha="left", va="center", **_DIM_FONT)

    if schema.label_faces:
        verts = {"A": A, "B": B, "C": C, "D": D,
                 "E": A2, "F": B2, "G": C2, "H": D2}
        offsets = {"A": (-0.15, -0.12), "B": (0.15, -0.12), "C": (0.24, -0.10),
                   "D": (-0.15, 0.12), "E": (-0.15, 0.12), "F": (0.18, 0.0),
                   "G": (0.15, 0.15), "H": (-0.05, 0.18)}
        for name, (px, py) in verts.items():
            ox, oy = offsets[name]
            ax.text(px + ox, py + oy, name, fontsize=11, fontweight="bold",
                    ha="center", va="center")

    ax.set_xlim(-1.0, L + dx + 1.6)
    ax.set_ylim(-0.9, H + dy + 0.7)


def _draw_cone(ax, schema):
    r, hgt = schema.radius, schema.height
    scale = 3.2 / max(2 * r, hgt)
    R, H = r * scale, hgt * scale
    ry = R * _ELLIPSE_RATIO

    # Base ellipse + slant edges to apex
    _draw_base_ellipse(ax, 0, 0, R, ry, schema.show_hidden_edges)
    ax.plot([-R, 0], [0, H], **_SOLID_EDGE)
    ax.plot([R, 0], [0, H], **_SOLID_EDGE)

    # Axis (height) and radius construction lines
    style = _HIDDEN_EDGE if schema.show_hidden_edges else dict(color="black", linewidth=1.1)
    ax.plot([0, 0], [0, H], **style)
    ax.plot([0, R], [0, 0], color="black", linewidth=1.1)
    ax.plot(0, 0, "ko", markersize=3)

    if schema.show_dimensions:
        ax.text(0.12, H / 2, _dim("h", schema.height, schema.unit),
                ha="left", va="center", **_DIM_FONT)
        ax.text(R / 2, -ry - 0.22, _dim("r", schema.radius, schema.unit),
                ha="center", va="top", **_DIM_FONT)
        if schema.slant_height is not None:
            ax.text(-R / 2 - 0.15, H / 2 + 0.1,
                    _dim("l", schema.slant_height, schema.unit),
                    ha="right", va="center", **_DIM_FONT)

    ax.set_xlim(-R - 1.4, R + 1.4)
    ax.set_ylim(-ry - 0.9, H + 0.6)


def _draw_cylinder(ax, schema):
    r, hgt = schema.radius, schema.height
    scale = 3.2 / max(2 * r, hgt)
    R, H = r * scale, hgt * scale
    ry = R * _ELLIPSE_RATIO

    _draw_base_ellipse(ax, 0, 0, R, ry, schema.show_hidden_edges)   # bottom
    _draw_full_ellipse(ax, 0, H, R, ry)                             # top (fully visible)
    ax.plot([-R, -R], [0, H], **_SOLID_EDGE)
    ax.plot([R, R], [0, H], **_SOLID_EDGE)

    # Radius on top face; axis for height
    ax.plot([0, R], [H, H], color="black", linewidth=1.1)
    ax.plot(0, H, "ko", markersize=3)

    if schema.show_dimensions:
        ax.text(R / 2, H + 0.14, _dim("r", schema.radius, schema.unit),
                ha="center", va="bottom", **_DIM_FONT)
        ax.text(R + 0.18, H / 2, _dim("h", schema.height, schema.unit),
                ha="left", va="center", **_DIM_FONT)

    ax.set_xlim(-R - 1.2, R + 1.8)
    ax.set_ylim(-ry - 0.7, H + ry + 0.7)


def _draw_sphere(ax, schema):
    R = 1.8   # normalized display radius
    circle = plt.Circle((0, 0), R, fill=False, edgecolor="black", linewidth=1.8)
    ax.add_patch(circle)
    # Equator ellipse seen in perspective
    ry = R * _ELLIPSE_RATIO
    fx, fy, bx, by = _ellipse_halves(0, 0, R, ry)
    ax.plot(fx, fy, color="black", linewidth=1.2)
    style = _HIDDEN_EDGE if schema.show_hidden_edges else dict(color="black", linewidth=1.2)
    ax.plot(bx, by, **style)
    # Center + radius
    ax.plot(0, 0, "ko", markersize=3.5)
    ax.text(-0.12, 0.14, "O", fontsize=11, ha="right", va="bottom")
    ax.plot([0, R], [0, 0], color="black", linewidth=1.2)

    if schema.show_dimensions:
        ax.text(R / 2, 0.14, _dim("r", schema.radius, schema.unit),
                ha="center", va="bottom", **_DIM_FONT)

    ax.set_xlim(-R - 0.8, R + 0.8)
    ax.set_ylim(-R - 0.7, R + 0.7)


def _draw_hemisphere(ax, schema):
    R = 1.9
    ry = R * _ELLIPSE_RATIO
    # Dome (upper semicircle)
    t = np.linspace(0, np.pi, 150)
    ax.plot(R * np.cos(t), R * np.sin(t), **_SOLID_EDGE)
    # Flat base rim: front visible, back hidden behind the dome
    _draw_base_ellipse(ax, 0, 0, R, ry, schema.show_hidden_edges)
    # Center + radius
    ax.plot(0, 0, "ko", markersize=3.5)
    ax.text(-0.12, 0.14, "O", fontsize=11, ha="right", va="bottom")
    ax.plot([0, R], [0, 0], color="black", linewidth=1.2)

    if schema.show_dimensions:
        ax.text(R / 2, 0.14, _dim("r", schema.radius, schema.unit),
                ha="center", va="bottom", **_DIM_FONT)

    ax.set_xlim(-R - 0.8, R + 0.8)
    ax.set_ylim(-ry - 0.7, R + 0.6)


def _draw_pyramid(ax, schema):
    s, hgt = schema.side, schema.height
    scale = 3.0 / max(s, hgt)
    S, H = s * scale, hgt * scale
    dx, dy = S * _OBLIQUE_DX, S * _OBLIQUE_DY

    # Square base as oblique parallelogram: A front-left, B front-right,
    # C back-right, D back-left
    A, B = (0, 0), (S, 0)
    C, D = (S + dx, dy), (dx, dy)
    center = ((S + dx) / 2, dy / 2)
    apex = (center[0], center[1] + H)

    hidden_style = _HIDDEN_EDGE if schema.show_hidden_edges else _SOLID_EDGE
    # Base: front + right receding visible; back + left receding hidden
    for p, q in [(A, B), (B, C)]:
        ax.plot([p[0], q[0]], [p[1], q[1]], **_SOLID_EDGE)
    for p, q in [(C, D), (D, A)]:
        ax.plot([p[0], q[0]], [p[1], q[1]], **hidden_style)
    # Lateral edges: apex-D passes behind the solid
    for v in (A, B, C):
        ax.plot([apex[0], v[0]], [apex[1], v[1]], **_SOLID_EDGE)
    ax.plot([apex[0], D[0]], [apex[1], D[1]], **hidden_style)

    # Height: dashed axis from apex to base center
    ax.plot([apex[0], center[0]], [apex[1], center[1]],
            **(_HIDDEN_EDGE if schema.show_hidden_edges
               else dict(color="black", linewidth=1.1)))
    ax.plot(center[0], center[1], "ko", markersize=3)

    if schema.show_dimensions:
        ax.text(S / 2, -0.28, _dim("a", schema.side, schema.unit),
                ha="center", va="top", **_DIM_FONT)
        ax.text(center[0] + 0.14, center[1] + H / 2,
                _dim("h", schema.height, schema.unit),
                ha="left", va="center", **_DIM_FONT)
        if schema.slant_height is not None:
            mx = (apex[0] + B[0]) / 2
            my = (apex[1] + B[1]) / 2
            ax.text(mx + 0.30, my - 0.35, _dim("l", schema.slant_height, schema.unit),
                    ha="left", va="center", **_DIM_FONT)

    if schema.label_faces:
        verts = {"A": A, "B": B, "C": C, "D": D, "P": apex}
        offsets = {"A": (-0.18, -0.12), "B": (0.18, -0.12), "C": (0.18, 0.10),
                   "D": (-0.18, 0.10), "P": (0.0, 0.20)}
        for name, (px, py) in verts.items():
            ox, oy = offsets[name]
            ax.text(px + ox, py + oy, name, fontsize=11, fontweight="bold",
                    ha="center", va="center")

    ax.set_xlim(-1.0, S + dx + 1.4)
    ax.set_ylim(-0.9, dy / 2 + H + 0.7)


def _draw_frustum(ax, schema):
    rt, rb, hgt = schema.radius_top, schema.radius_bottom, schema.height
    scale = 3.2 / max(2 * rb, 2 * rt, hgt)
    RT, RB, H = rt * scale, rb * scale, hgt * scale
    ry_t = RT * _ELLIPSE_RATIO
    ry_b = RB * _ELLIPSE_RATIO

    _draw_base_ellipse(ax, 0, 0, RB, ry_b, schema.show_hidden_edges)   # bottom
    _draw_full_ellipse(ax, 0, H, RT, ry_t)                             # top
    ax.plot([-RB, -RT], [0, H], **_SOLID_EDGE)
    ax.plot([RB, RT], [0, H], **_SOLID_EDGE)

    # Axis + radii construction lines
    ax.plot([0, 0], [0, H],
            **(_HIDDEN_EDGE if schema.show_hidden_edges
               else dict(color="black", linewidth=1.1)))
    ax.plot([0, RT], [H, H], color="black", linewidth=1.1)
    ax.plot([0, RB], [0, 0], color="black", linewidth=1.1)
    ax.plot(0, H, "ko", markersize=3)
    ax.plot(0, 0, "ko", markersize=3)

    if schema.show_dimensions:
        ax.text(RT / 2, H + ry_t + 0.15, _dim("r", schema.radius_top, schema.unit),
                ha="center", va="bottom", **_DIM_FONT)
        ax.text(RB / 2, -ry_b - 0.22, _dim("R", schema.radius_bottom, schema.unit),
                ha="center", va="top", **_DIM_FONT)
        ax.text(0.14, H / 2, _dim("h", schema.height, schema.unit),
                ha="left", va="center", **_DIM_FONT)
        if schema.slant_height is not None:
            mx = (RB + RT) / 2
            ax.text(mx + 0.22, H / 2, _dim("l", schema.slant_height, schema.unit),
                    ha="left", va="center", **_DIM_FONT)

    lim = max(RB, RT)
    ax.set_xlim(-lim - 1.2, lim + 1.6)
    ax.set_ylim(-ry_b - 0.8, H + ry_t + 0.7)


def render_solid_3d(data: Dict[str, Any], canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = Solid3DSchema(**data)

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))
    ax.set_aspect("equal")
    ax.axis("off")

    st = schema.solid_type
    if st == "cube":
        _draw_box(ax, schema, schema.side, schema.side, schema.side,
                  [("a", schema.side)])
    elif st == "cuboid":
        _draw_box(ax, schema, schema.length, schema.width, schema.height,
                  [("l", schema.length), ("b", schema.width), ("h", schema.height)])
    elif st == "cone":
        _draw_cone(ax, schema)
    elif st == "cylinder":
        _draw_cylinder(ax, schema)
    elif st == "sphere":
        _draw_sphere(ax, schema)
    elif st == "hemisphere":
        _draw_hemisphere(ax, schema)
    elif st == "pyramid":
        _draw_pyramid(ax, schema)
    elif st == "frustum":
        _draw_frustum(ax, schema)

    if schema.title:
        ax.set_title(schema.title, fontsize=13, fontweight="bold", pad=8)

    fig.tight_layout(pad=0.5)
    return _fig_to_svg(fig)


# ── Argand Diagram (complex plane) ────────────────────────────────────────────

_SUBSCRIPT_DIGITS = "₀₁₂₃₄₅₆₇₈₉"
_ZERO = 1e-9


def _subscript(n: int) -> str:
    return "".join(_SUBSCRIPT_DIGITS[int(d)] for d in str(n))


def _complex_text(re_: float, im_: float) -> str:
    """Format a + bi the way a paper prints it: '3 + 4i', '-i', '2', '1 - 0.5i'."""
    if abs(im_) < _ZERO:
        return f"{re_:g}"
    mag = abs(im_)
    mag_txt = "" if abs(mag - 1) < _ZERO else f"{mag:g}"
    if abs(re_) < _ZERO:
        return f"{'-' if im_ < 0 else ''}{mag_txt}i"
    return f"{re_:g} {'+' if im_ > 0 else '-'} {mag_txt}i"


def _arg_text(theta: float) -> str:
    """Principal argument as a π-fraction where it is one, else in degrees."""
    t = _pi_label(theta, tol=1e-6)
    if "π" in t or t == "0":
        return t
    return f"{math.degrees(theta):.4g}°"


def _circle_locus_label(circ) -> str:
    """|z| = r, |z - 2| = 3, |z - (2 + 3i)| = 3 — brackets only when the centre is complex."""
    cr, ci = circ.centre_real, circ.centre_imag
    if abs(cr) < _ZERO and abs(ci) < _ZERO:
        return f"|z| = {circ.radius:g}"
    centre = _complex_text(cr, ci)
    if abs(cr) > _ZERO and abs(ci) > _ZERO:
        centre = f"({centre})"
    elif abs(ci) > _ZERO:          # purely imaginary centre: |z - 3i| = r
        return f"|z - {centre}| = {circ.radius:g}"
    sign = "-" if cr > 0 else "+"
    return f"|z {sign} {abs(cr):g}| = {circ.radius:g}" if abs(ci) < _ZERO \
        else f"|z - {centre}| = {circ.radius:g}"


def _roots_of_unity_points(n: int) -> List[ArgandPoint]:
    """The n solutions of zⁿ = 1 — generated here so the geometry cannot be mis-supplied."""
    pts = []
    for k in range(n):
        theta = 2 * math.pi * k / n
        pts.append(ArgandPoint(
            real=math.cos(theta), imag=math.sin(theta),
            label=f"z{_subscript(k)}", show_value=False,
            show_vector=True, show_argument=True,
        ))
    return pts


def _argand_region_mask(region, RE, IM):
    dr = RE - region.centre_real
    di = IM - region.centre_imag
    mod = np.hypot(dr, di)
    if region.region_type == "disc":
        return mod <= region.radius
    if region.region_type == "annulus":
        return (mod >= region.inner_radius) & (mod <= region.outer_radius)
    if region.region_type == "wedge":
        # arg is measured from the centre, wrapped into [start, start + sweep]
        ang = np.arctan2(di, dr)
        start = math.radians(region.start_angle)
        sweep = (math.radians(region.end_angle) - start) % (2 * math.pi)
        rel = (ang - start) % (2 * math.pi)
        return rel <= sweep
    axis_vals = RE if region.axis == "real" else IM
    return axis_vals >= region.value if region.op == ">=" else axis_vals <= region.value


def render_argand_diagram(data: Dict[str, Any], canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = ArgandDiagramSchema(**data)

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))
    ax.set_aspect("equal")

    points = list(schema.points)
    show_unit_circle = schema.show_unit_circle
    if schema.roots_of_unity:
        points = _roots_of_unity_points(schema.roots_of_unity) + points
        show_unit_circle = True

    # ── Plot window (every label must land inside it or matplotlib drops it) ──
    extents = [1.0]
    for p in points:
        extents.append(abs(p.real))
        extents.append(abs(p.imag))
    for c in schema.circles:
        extents.append(abs(c.centre_real) + c.radius)
        extents.append(abs(c.centre_imag) + c.radius)
    for r in schema.regions:
        span = r.radius or r.outer_radius or 0.0
        extents.append(abs(r.centre_real) + span)
        extents.append(abs(r.centre_imag) + span)
        if r.region_type == "half_plane":
            extents.append(abs(r.value) + 1.0)
    if not show_unit_circle and max(extents) <= 1.0:
        extents.append(2.0)
    lim = max(extents) * 1.45

    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)

    # ── Shaded loci ──────────────────────────────────────────────────────────
    if schema.regions:
        grid = np.linspace(-lim, lim, 500)
        RE, IM = np.meshgrid(grid, grid)
        for region in schema.regions:
            mask = _argand_region_mask(region, RE, IM)
            ax.contourf(RE, IM, mask.astype(float), levels=[0.5, 1.5],
                        colors=["#3498DB"], alpha=0.20, zorder=1)
            if region.label:
                ax.text(0.02, 0.03, region.label, transform=ax.transAxes,
                        fontsize=11, color="#1B4F72", zorder=8,
                        bbox=dict(boxstyle="round,pad=0.25", fc="white",
                                  ec="#3498DB", alpha=0.85))

    # ── Circles (|z - c| = r loci) and the unit circle ───────────────────────
    if show_unit_circle:
        ax.add_patch(plt.Circle((0, 0), 1.0, fill=False, edgecolor="#7F8C8D",
                                linestyle="--", linewidth=1.2, zorder=2))
    for circ in schema.circles:
        ax.add_patch(plt.Circle((circ.centre_real, circ.centre_imag), circ.radius,
                                fill=False, edgecolor="#C0392B", linewidth=1.8, zorder=3))
        ax.plot(circ.centre_real, circ.centre_imag, "x", color="#C0392B",
                markersize=6, zorder=4)
        label = circ.label or _circle_locus_label(circ)
        ax.annotate(label,
                    (circ.centre_real, circ.centre_imag + circ.radius),
                    textcoords="offset points", xytext=(6, 6),
                    fontsize=10, color="#C0392B", zorder=8)

    # ── Points, vectors, moduli, argument arcs ───────────────────────────────
    many = len(points) > 4
    for i, p in enumerate(points):
        modulus = math.hypot(p.real, p.imag)
        argument = math.atan2(p.imag, p.real)

        if p.show_vector and modulus > _ZERO:
            ax.annotate("", xy=(p.real, p.imag), xytext=(0, 0),
                        arrowprops=dict(arrowstyle="-|>", color="black", lw=1.5,
                                        mutation_scale=13, shrinkA=0, shrinkB=0),
                        zorder=5)
        ax.plot(p.real, p.imag, "o", color="black", markersize=6, zorder=6)

        parts = []
        if p.label:
            parts.append(p.label)
        if p.show_value:
            value = _complex_text(p.real, p.imag)
            parts.append(f"= {value}" if p.label else value)
        if parts:
            ax.annotate(" ".join(parts), (p.real, p.imag),
                        textcoords="offset points", xytext=(9, 7),
                        fontsize=10 if many else 11, zorder=7,
                        bbox=dict(boxstyle="round,pad=0.15", fc="white",
                                  ec="none", alpha=0.8))

        if (p.show_modulus or schema.show_modulus_argument) and modulus > _ZERO:
            mx, my = p.real / 2, p.imag / 2
            ax.annotate(f"|{p.label or 'z'}| = {modulus:g}", (mx, my),
                        textcoords="offset points",
                        xytext=(-p.imag / modulus * 16, p.real / modulus * 16),
                        fontsize=9, style="italic", ha="center", va="center", zorder=7)

        # arg 0 has no arc to draw — a degenerate Arc renders as a stray dot
        if (p.show_argument or schema.show_modulus_argument) and modulus > _ZERO \
                and abs(argument) > 1e-6:
            # Stagger arc radii so several points on the unit circle don't overprint.
            r_arc = lim * (0.14 + 0.075 * (i % 8)) if many else min(modulus * 0.45, lim * 0.3)
            deg = math.degrees(argument)
            ax.add_patch(Arc((0, 0), 2 * r_arc, 2 * r_arc, angle=0,
                             theta1=min(0.0, deg), theta2=max(0.0, deg),
                             color="#8E44AD", linewidth=1.1, zorder=4))
            mid = math.radians(deg / 2)
            ax.text((r_arc + lim * 0.05) * math.cos(mid),
                    (r_arc + lim * 0.05) * math.sin(mid),
                    _arg_text(argument), fontsize=8 if many else 10,
                    color="#8E44AD", ha="center", va="center", zorder=8,
                    bbox=dict(boxstyle="round,pad=0.1", fc="white", ec="none", alpha=0.75))

    # Axis labels belong at the tips of Re/Im, not stacked on the origin like x/y would be.
    _setup_axes(ax, (-lim, lim), (-lim, lim), "", "", schema.show_grid, schema.title)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: "" if abs(v) < _ZERO else f"{v:g}"))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: "" if abs(v) < _ZERO else f"{v:g}"))
    if schema.show_axes_labels:
        ax.text(lim * 0.99, lim * 0.03, "Re", fontsize=12, style="italic",
                ha="right", va="bottom", zorder=9)
        ax.text(lim * 0.03, lim * 0.98, "Im", fontsize=12, style="italic",
                ha="left", va="top", zorder=9)
    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)

    fig.tight_layout(pad=0.8)
    return _fig_to_svg(fig)


# ── Linear Programming ────────────────────────────────────────────────────────

_LP_TRANSFORMS = standard_transformations + (implicit_multiplication_application, convert_xor)
_LP_TOL = 1e-7
_LP_OP_TEXT = {"<=": "≤", ">=": "≥", "=": "="}


def _parse_lp_expression(text: str) -> Tuple[float, float, str, float]:
    """Parse '2x + 3y <= 12' → (a, b, op, c) meaning a·x + b·y op c."""
    s = text.replace("≤", "<=").replace("≥", ">=").replace("−", "-").strip()
    for op in ("<=", ">=", "==", "=", "<", ">"):
        if op in s:
            lhs_txt, rhs_txt = s.split(op, 1)
            break
    else:
        raise ValueError(f"Constraint '{text}' has no relational operator (<=, >=, =)")

    try:
        lhs = parse_safe(lhs_txt, ("x", "y"))
        rhs = parse_safe(rhs_txt, ("x", "y"))
        expr = sp.expand(lhs - rhs)
        if sp.Poly(expr, x_sym, y_sym).total_degree() > 1:
            raise ValueError("constraint is not linear in x and y")
        a = float(expr.coeff(x_sym))
        b = float(expr.coeff(y_sym))
        c = -float(expr.subs({x_sym: 0, y_sym: 0}))
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Invalid constraint '{text}': {e}")

    if abs(a) < 1e-12 and abs(b) < 1e-12:
        raise ValueError(f"Constraint '{text}' involves neither x nor y")
    return a, b, {"<": "<=", ">": ">=", "==": "="}.get(op, op), c


def _lp_label(a: float, b: float, op: str, c: float) -> str:
    terms = []
    if abs(a) > 1e-12:
        terms.append("x" if abs(a - 1) < 1e-12 else f"{a:g}x")
    if abs(b) > 1e-12:
        sign = " + " if b > 0 or not terms else " - "
        coef = abs(b)
        term = "y" if abs(coef - 1) < 1e-12 else f"{coef:g}y"
        terms.append(f"{sign if terms else ('' if b > 0 else '-')}{term}")
    return f"{''.join(terms)} {_LP_OP_TEXT.get(op, op)} {c:g}"


def _lp_constraints(constraints: List[LPConstraint], non_negative: bool):
    """Normalise to (a, b, op, c, label); x ≥ 0 and y ≥ 0 are appended when implied."""
    out = []
    for con in constraints:
        if con.expression:
            a, b, op, c = _parse_lp_expression(con.expression)
        else:
            a, b, c = float(con.a), float(con.b), float(con.c)
            op = {"<": "<=", ">": ">=", "==": "="}.get(con.op, con.op)
        out.append((a, b, op, c, con.label or _lp_label(a, b, op, c)))
    if non_negative:
        out.append((1.0, 0.0, ">=", 0.0, "x ≥ 0"))
        out.append((0.0, 1.0, ">=", 0.0, "y ≥ 0"))
    return out


def _lp_halfplanes(cons) -> List[Tuple[float, float, float]]:
    """Every constraint as a ≤ row (a, b, c): a·x + b·y ≤ c. '=' becomes two rows."""
    rows = []
    for a, b, op, c, _ in cons:
        if op == "<=":
            rows.append((a, b, c))
        elif op == ">=":
            rows.append((-a, -b, -c))
        else:
            rows.append((a, b, c))
            rows.append((-a, -b, -c))
    return rows


def _lp_feasible(point, rows) -> bool:
    px, py = point
    return all(a * px + b * py <= c + _LP_TOL for a, b, c in rows)


def _lp_corner_points(cons, rows) -> List[Tuple[float, float]]:
    """
    Intersect every pair of constraint boundaries and keep the intersections that satisfy
    ALL constraints — that set is exactly the vertex set of the feasible region.
    """
    pts = []
    for i in range(len(cons)):
        for j in range(i + 1, len(cons)):
            a1, b1, _, c1, _ = cons[i]
            a2, b2, _, c2, _ = cons[j]
            det = a1 * b2 - a2 * b1
            if abs(det) < 1e-12:
                continue   # parallel boundaries never meet in a vertex
            px = (c1 * b2 - c2 * b1) / det
            py = (a1 * c2 - a2 * c1) / det
            if _lp_feasible((px, py), rows):
                pts.append((round(px, 9) + 0.0, round(py, 9) + 0.0))
    uniq: List[Tuple[float, float]] = []
    for p in sorted(set(pts)):
        if not any(math.hypot(p[0] - q[0], p[1] - q[1]) < 1e-7 for q in uniq):
            uniq.append(p)
    return uniq


def _lp_recession_rays(rows) -> List[Tuple[float, float]]:
    """
    Directions you can travel forever without leaving the region. Empty ⇒ bounded.
    Every extreme ray of the recession cone lies along some constraint boundary, so the
    two directions perpendicular to each row's normal are the only candidates to test.
    """
    rays: List[Tuple[float, float]] = []
    for a, b, _ in rows:
        for dx, dy in ((b, -a), (-b, a)):
            n = math.hypot(dx, dy)
            if n < 1e-12:
                continue
            d = (dx / n, dy / n)
            if all(ra * d[0] + rb * d[1] <= 1e-9 for ra, rb, _ in rows):
                if not any(abs(d[0] - ex) < 1e-9 and abs(d[1] - ey) < 1e-9 for ex, ey in rays):
                    rays.append(d)
    return rays


def _lp_any_feasible(rows) -> bool:
    """Coarse sweep: is the region non-empty even though it has no vertices (a strip)?"""
    grid = np.linspace(-1000.0, 1000.0, 81)
    return any(_lp_feasible((px, py), rows) for px in grid for py in grid)


def solve_linear_program(constraints, objective=None, maximise: bool = True,
                         non_negative: bool = True) -> Dict[str, Any]:
    """
    Corner points and the optimal vertex, derived from the constraints alone —
    nothing about the answer is taken from the params.
    """
    cons_models = [c if isinstance(c, LPConstraint) else LPConstraint(**c) for c in constraints]
    cons = _lp_constraints(cons_models, non_negative)
    rows = _lp_halfplanes(cons)
    corners = _lp_corner_points(cons, rows)
    rays = _lp_recession_rays(rows)

    result: Dict[str, Any] = {
        "constraints": cons,
        "rows": rows,
        "corners": corners,
        "bounded": not rays,
        "empty": not corners and not _lp_any_feasible(rows),
        "unbounded_objective": False,
        "corner_values": [],
        "optimum_point": None,
        "optimum_value": None,
    }

    obj = None
    if objective is not None:
        obj = objective if isinstance(objective, LPObjective) else LPObjective(**objective)
    result["objective"] = obj
    if obj is None or result["empty"] or not corners:
        return result

    # An unbounded region only destroys the optimum if Z improves along a recession ray.
    sense = 1.0 if maximise else -1.0
    if any(sense * (obj.a * dx + obj.b * dy) > 1e-9 for dx, dy in rays):
        result["unbounded_objective"] = True
        return result

    values = [(p, obj.a * p[0] + obj.b * p[1]) for p in corners]
    result["corner_values"] = values
    best = max(v for _, v in values) if maximise else min(v for _, v in values)
    for p, v in values:   # corners are lexicographically sorted → ties resolve deterministically
        if abs(v - best) < 1e-9:
            result["optimum_point"] = p
            result["optimum_value"] = best
            break
    return result


def render_linear_programming(data: Dict[str, Any], canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = LinearProgrammingSchema(**data)

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))

    sol = solve_linear_program(schema.constraints, schema.objective,
                               schema.maximise, schema.non_negative)
    cons, rows, corners = sol["constraints"], sol["rows"], sol["corners"]
    obj = sol["objective"]

    # ── Plot window: must contain every computed corner, else its label vanishes ──
    xs = [p[0] for p in corners]
    ys = [p[1] for p in corners]
    for a, b, _, c, _ in cons:
        if abs(a) > 1e-12 and abs(c / a) < 1e4:
            xs.append(c / a)
        if abs(b) > 1e-12 and abs(c / b) < 1e4:
            ys.append(c / b)
    lo_x, hi_x = min(xs + [0.0]), max(xs + [1.0])
    lo_y, hi_y = min(ys + [0.0]), max(ys + [1.0])
    pad_x = max((hi_x - lo_x) * 0.30, 1.0)
    pad_y = max((hi_y - lo_y) * 0.30, 1.0)
    x_range = schema.x_range or (lo_x - pad_x * 0.15, hi_x + pad_x)
    y_range = schema.y_range or (lo_y - pad_y * 0.15, hi_y + pad_y)

    _setup_axes(ax, x_range, y_range, schema.x_label, schema.y_label,
                schema.show_grid, schema.title)
    xlim, ylim = ax.get_xlim(), ax.get_ylim()

    # ── Feasible region (grid mask handles bounded and unbounded alike) ──────
    if schema.show_feasible_region and not sol["empty"]:
        gx = np.linspace(xlim[0], xlim[1], 500)
        gy = np.linspace(ylim[0], ylim[1], 500)
        GX, GY = np.meshgrid(gx, gy)
        mask = np.ones_like(GX, dtype=bool)
        for a, b, c in rows:
            mask &= (a * GX + b * GY <= c + _LP_TOL)
        if mask.any():
            ax.contourf(GX, GY, mask.astype(float), levels=[0.5, 1.5],
                        colors=["#3498DB"], alpha=0.22, zorder=1)

    # ── Constraint boundaries (the implicit x ≥ 0 / y ≥ 0 lie on the axes) ───
    palette = ["#2980B9", "#C0392B", "#27AE60", "#8E44AD", "#D68910", "#16A085"]
    x_line = np.linspace(xlim[0], xlim[1], 400)
    for i, (a, b, op, c, label) in enumerate(cons[:len(schema.constraints)]):
        color = palette[i % len(palette)]
        if abs(b) < 1e-12:
            ax.axvline(c / a, color=color, linewidth=1.7, label=label, zorder=3)
        else:
            ax.plot(x_line, (c - a * x_line) / b, color=color, linewidth=1.7,
                    label=label, zorder=3)

    # ── Corner points ────────────────────────────────────────────────────────
    if schema.show_corner_points:
        for px, py in corners:
            ax.plot(px, py, "o", color="black", markersize=6, zorder=6)
            ax.annotate(f"({px:g}, {py:g})", (px, py), textcoords="offset points",
                        xytext=(8, 7), fontsize=10, zorder=7,
                        bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.85))

    # ── Objective: iso-profit line through the optimal vertex ────────────────
    opt = sol["optimum_point"]
    if obj and schema.show_objective_line and opt is not None:
        z = sol["optimum_value"]
        if abs(obj.b) > 1e-12:
            ax.plot(x_line, (z - obj.a * x_line) / obj.b, color="#E67E22",
                    linestyle="--", linewidth=1.8, zorder=4,
                    label=f"{obj.label} = {z:g}")
        elif abs(obj.a) > 1e-12:
            ax.axvline(z / obj.a, color="#E67E22", linestyle="--", linewidth=1.8,
                       zorder=4, label=f"{obj.label} = {z:g}")
        ax.plot(opt[0], opt[1], "*", color="#E67E22", markersize=18,
                markeredgecolor="black", markeredgewidth=0.6, zorder=8)

    # ── Verdict (drawn in axes coordinates so it can never fall off-canvas) ──
    if sol["empty"]:
        note = "Feasible region is EMPTY — no solution"
    elif sol["unbounded_objective"]:
        note = f"Feasible region is UNBOUNDED — {obj.label} has no {'maximum' if schema.maximise else 'minimum'}"
    elif obj and opt is not None:
        word = "Max" if schema.maximise else "Min"
        note = f"{word} {obj.label} = {sol['optimum_value']:g} at ({opt[0]:g}, {opt[1]:g})"
        if not sol["bounded"]:
            note += "  (region unbounded)"
    elif not sol["bounded"]:
        note = "Feasible region is UNBOUNDED"
    else:
        note = ""
    if note:
        ax.text(0.02, 0.98, note, transform=ax.transAxes, va="top", ha="left",
                fontsize=11, zorder=9,
                bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#34495E", alpha=0.9))

    ax.set_xlim(xlim)
    ax.set_ylim(ylim)
    ax.legend(fontsize=9, loc="upper right", framealpha=0.9)
    fig.tight_layout(pad=0.8)
    return _fig_to_svg(fig)


# ── Histogram / Ogive (grouped-frequency statistics) ──────────────────────────

def _class_boundaries(intervals, correction: bool) -> List[Tuple[float, float]]:
    """
    True class boundaries. Inclusive classes (10–19, 20–29) leave a gap, and every plotted
    position — bar edge, midpoint, ogive x — must sit on the gap-midpoint boundary (19.5),
    not on the stated limit, or the bars stand apart and the ogive reads half a gap early.
    """
    n = len(intervals)
    bounds = []
    for i, ci in enumerate(intervals):
        gap_before = (ci.lower - intervals[i - 1].upper) if i > 0 else 0.0
        gap_after = (intervals[i + 1].lower - ci.upper) if i < n - 1 else 0.0
        if not correction:
            gap_before = gap_after = 0.0
        if i == 0:
            gap_before = gap_after      # first/last class mirror their only neighbouring gap
        if i == n - 1:
            gap_after = gap_before
        bounds.append((ci.lower - gap_before / 2.0, ci.upper + gap_after / 2.0))
    return bounds


def _class_midpoints(bounds) -> List[float]:
    """The frequency polygon joins MIDPOINTS, never class limits."""
    return [(lo + hi) / 2.0 for lo, hi in bounds]


def _less_than_ogive(intervals, bounds) -> List[Tuple[float, float]]:
    """
    Cumulative frequency plotted at the UPPER boundary: 'less than 20' is only true once the
    whole 10–20 class is counted, so the point belongs at 20 — never at the midpoint.
    """
    pts, cum = [], 0.0
    for ci, (_, hi) in zip(intervals, bounds):
        cum += ci.frequency
        pts.append((hi, cum))
    return pts


def _more_than_ogive(intervals, bounds) -> List[Tuple[float, float]]:
    """Mirror image: 'more than 20' is read at the LOWER boundary, starting from the total."""
    total = sum(ci.frequency for ci in intervals)
    pts, cum = [], 0.0
    for ci, (lo, _) in zip(intervals, bounds):
        pts.append((lo, total - cum))
        cum += ci.frequency
    return pts


def _modal_class_index(intervals) -> int:
    freqs = [ci.frequency for ci in intervals]
    return max(range(len(freqs)), key=lambda i: freqs[i])   # first maximum wins → deterministic


def _histogram_mode(intervals, bounds) -> Optional[float]:
    """
    Where the two diagonals drawn inside the modal class cross. Solving that intersection
    gives exactly l + h(f₁ - f₀)/(2f₁ - f₀ - f₂), so the picture and the formula agree.
    """
    i = _modal_class_index(intervals)
    f1 = intervals[i].frequency
    f0 = intervals[i - 1].frequency if i > 0 else 0.0
    f2 = intervals[i + 1].frequency if i < len(intervals) - 1 else 0.0
    lo, hi = bounds[i]
    denom = 2 * f1 - f0 - f2
    if abs(denom) < 1e-12:
        return None
    return lo + (hi - lo) * (f1 - f0) / denom


def _histogram_median(intervals, bounds) -> Optional[float]:
    """x at which the less-than ogive reaches N/2 — i.e. l + h(N/2 - cf)/f."""
    total = sum(ci.frequency for ci in intervals)
    half = total / 2.0
    cum = 0.0
    for ci, (lo, hi) in zip(intervals, bounds):
        prev = cum
        cum += ci.frequency
        if cum >= half - 1e-12:
            if ci.frequency <= 0:
                return None
            return lo + (hi - lo) * (half - prev) / ci.frequency
    return None


def render_histogram(data: Dict[str, Any], canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = HistogramSchema(**data)

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))

    intervals = schema.class_intervals
    bounds = _class_boundaries(intervals, schema.continuity_correction)
    freqs = [ci.frequency for ci in intervals]
    mids = _class_midpoints(bounds)
    total = sum(freqs)

    # ── Bars ─────────────────────────────────────────────────────────────────
    for (lo, hi), f in zip(bounds, freqs):
        ax.bar(lo, f, width=hi - lo, align="edge", color="#AED6F1",
               edgecolor="#1B4F72", linewidth=1.0, zorder=2)
    if schema.show_values:
        for (lo, hi), f in zip(bounds, freqs):
            ax.text((lo + hi) / 2, f + max(freqs) * 0.015, f"{f:g}",
                    ha="center", va="bottom", fontsize=9, zorder=6)

    handles: List[Any] = []
    need_lt = schema.overlay in ("ogive_less_than", "both_ogives") or schema.show_median_from_ogive
    need_mt = schema.overlay in ("ogive_more_than", "both_ogives")

    # ── Frequency polygon (joins class MIDPOINTS, closed onto the x-axis) ────
    if schema.overlay == "frequency_polygon":
        width_first = bounds[0][1] - bounds[0][0]
        width_last = bounds[-1][1] - bounds[-1][0]
        poly_x = [mids[0] - width_first] + mids + [mids[-1] + width_last]
        poly_y = [0.0] + freqs + [0.0]
        line, = ax.plot(poly_x, poly_y, "o-", color="#C0392B", linewidth=1.8,
                        markersize=5, zorder=5, label="Frequency polygon")
        handles.append(line)

    # ── Ogives on their own cumulative-frequency axis ────────────────────────
    ax2 = None
    if need_lt or need_mt:
        ax2 = ax.twinx()
        ax2.set_ylabel("Cumulative frequency", fontsize=11)
        ax2.set_ylim(0, total * 1.12)
        ax2.spines["top"].set_visible(False)

        if need_lt:
            lt = _less_than_ogive(intervals, bounds)
            # anchored at the lower boundary of the first class, where the cumulative count is 0
            xs = [bounds[0][0]] + [p[0] for p in lt]
            ys = [0.0] + [p[1] for p in lt]
            line, = ax2.plot(xs, ys, "s-", color="#27AE60", linewidth=1.8,
                             markersize=5, zorder=5, label="Less-than ogive")
            handles.append(line)

        if need_mt:
            mt = _more_than_ogive(intervals, bounds)
            xs = [p[0] for p in mt] + [bounds[-1][1]]
            ys = [p[1] for p in mt] + [0.0]
            line, = ax2.plot(xs, ys, "^-", color="#8E44AD", linewidth=1.8,
                             markersize=5, zorder=5, label="More-than ogive")
            handles.append(line)

    # ── Graphical mode: the two diagonals inside the modal class ─────────────
    if schema.show_mode_construction:
        i = _modal_class_index(intervals)
        lo, hi = bounds[i]
        f1 = freqs[i]
        f0 = freqs[i - 1] if i > 0 else 0.0
        f2 = freqs[i + 1] if i < len(freqs) - 1 else 0.0
        ax.plot([lo, hi], [f1, f2], color="#E67E22", linewidth=1.4, zorder=6)
        ax.plot([hi, lo], [f1, f0], color="#E67E22", linewidth=1.4, zorder=6)
        mode = _histogram_mode(intervals, bounds)
        if mode is not None:
            y_cross = f1 + (f2 - f1) * (mode - lo) / (hi - lo)
            ax.plot([mode, mode], [0, y_cross], color="#E67E22",
                    linestyle="--", linewidth=1.4, zorder=6)
            ax.plot(mode, y_cross, "o", color="#E67E22", markersize=6, zorder=7)
            ax.annotate(f"Mode = {mode:.4g}", (mode, y_cross),
                        textcoords="offset points", xytext=(8, 6), fontsize=10,
                        color="#B9770E", zorder=8)

    # ── Median read off the less-than ogive (perpendicular from N/2) ─────────
    if schema.show_median_from_ogive and ax2 is not None:
        median = _histogram_median(intervals, bounds)
        if median is not None:
            half = total / 2.0
            ax2.plot([bounds[0][0], median], [half, half], color="#34495E",
                     linestyle=":", linewidth=1.5, zorder=6)
            ax2.plot([median, median], [half, 0], color="#34495E",
                     linestyle=":", linewidth=1.5, zorder=6)
            ax2.plot(median, half, "o", color="#34495E", markersize=6, zorder=7)
            ax2.annotate(f"Median = {median:.4g}", (median, half),
                         textcoords="offset points", xytext=(8, 8), fontsize=10,
                         color="#34495E", zorder=8,
                         bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.85))
            ax2.annotate(f"N/2 = {half:g}", (bounds[0][0], half),
                         textcoords="offset points", xytext=(4, 5), fontsize=9,
                         color="#34495E", zorder=8)

    ax.set_xticks([b[0] for b in bounds] + [bounds[-1][1]])
    ax.set_xlabel(schema.x_label, fontsize=11)
    ax.set_ylabel(schema.y_label, fontsize=11)
    ax.set_ylim(0, max(freqs) * 1.30)
    ax.set_xlim(bounds[0][0] - (bounds[0][1] - bounds[0][0]) * 0.6,
                bounds[-1][1] + (bounds[-1][1] - bounds[-1][0]) * 0.6)
    if schema.show_grid:
        ax.yaxis.grid(True, color=GRID_COLOR, linewidth=0.7, linestyle="--", alpha=0.7)
        ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    if handles:
        ax.legend(handles=handles, fontsize=9, loc="upper left", framealpha=0.9)
    ax.set_title(schema.title or "Histogram", fontsize=13, fontweight="bold")

    fig.tight_layout(pad=0.8)
    return _fig_to_svg(fig)


# ── Probability Tree ──────────────────────────────────────────────────────────

def _prob_text(p: float) -> str:
    """Short decimals stay decimal; 1/3 and friends print as fractions, not 0.3333."""
    if abs(p * 1000 - round(p * 1000)) < 1e-9:
        return f"{p:g}"
    frac = sp.Rational(p).limit_denominator(1000)
    if abs(float(frac) - p) < 1e-9:
        return f"{frac.p}/{frac.q}"
    return f"{p:.4g}"


def _tree_leaf_paths(branches, _prefix=None, _prob: float = 1.0, _depth: int = 1) -> List[Dict[str, Any]]:
    """Every root-to-leaf path, with its probability = the product of the edges along it."""
    out: List[Dict[str, Any]] = []
    for b in branches:
        path = (_prefix or []) + [b.label]
        prob = _prob * b.probability
        if b.children:
            out.extend(_tree_leaf_paths(b.children, path, prob, _depth + 1))
        else:
            out.append({
                "path": path,
                "probability": prob,
                "outcome": b.outcome or "".join(path),
                "depth": _depth,
            })
    return out


def _tree_nodes(branches) -> List[Dict[str, Any]]:
    """Flatten to nodes carrying depth, parent, path and the running path probability."""
    nodes: List[Dict[str, Any]] = []
    leaf_slot = [0]

    def visit(branch, depth: int, parent: Optional[int], path: List[str], prob: float) -> float:
        idx = len(nodes)
        nodes.append({
            "depth": depth, "parent": parent, "label": branch.label,
            "probability": branch.probability, "path": path,
            "cum_probability": prob, "outcome": branch.outcome,
            "is_leaf": not branch.children, "y": 0.0,
        })
        if branch.children:
            ys = [visit(ch, depth + 1, idx, path + [ch.label], prob * ch.probability)
                  for ch in branch.children]
            nodes[idx]["y"] = sum(ys) / len(ys)
        else:
            nodes[idx]["y"] = float(leaf_slot[0])
            leaf_slot[0] += 1
        return nodes[idx]["y"]

    for br in branches:
        visit(br, 1, None, [br.label], br.probability)
    return nodes


def render_probability_tree(data: Dict[str, Any], canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = ProbabilityTreeSchema(**data)   # rejects sibling probabilities that don't sum to 1

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))
    ax.axis("off")

    nodes = _tree_nodes(schema.branches)
    max_depth = max(n["depth"] for n in nodes)
    n_leaves = sum(1 for n in nodes if n["is_leaf"])

    dx = 1.0
    root_y = sum(n["y"] for n in nodes if n["depth"] == 1) / max(
        1, sum(1 for n in nodes if n["depth"] == 1))

    def pos(node) -> Tuple[float, float]:
        return node["depth"] * dx, -node["y"]

    highlighted = [list(p) for p in schema.highlight_paths]

    def is_highlighted(path: List[str]) -> bool:
        return any(hp[:len(path)] == path for hp in highlighted)

    # ── Edges ────────────────────────────────────────────────────────────────
    for node in nodes:
        px, py = (0.0, -root_y) if node["parent"] is None else pos(nodes[node["parent"]])
        nx_, ny_ = pos(node)
        hot = is_highlighted(node["path"])
        ax.plot([px, nx_], [py, ny_],
                color="#C0392B" if hot else "black",
                linewidth=2.2 if hot else 1.3, zorder=3)
        if schema.show_probabilities:
            ax.text((px + nx_) / 2, (py + ny_) / 2 + 0.10,
                    _prob_text(node["probability"]),
                    fontsize=10, ha="center", va="bottom",
                    color="#C0392B" if hot else "#1B4F72", zorder=5,
                    bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none", alpha=0.85))
        ax.plot(nx_, ny_, "o", color="black", markersize=5, zorder=4)
        if node["label"] and not node["is_leaf"]:
            ax.text(nx_, ny_ + 0.13, node["label"], fontsize=11, ha="center",
                    va="bottom", fontweight="bold", zorder=5)

    ax.plot(0.0, -root_y, "o", color="black", markersize=6, zorder=4)

    # ── Leaves: outcome + the product along the path, computed here ──────────
    leaves = _tree_leaf_paths(schema.branches)
    leaf_nodes = [n for n in nodes if n["is_leaf"]]
    for node, leaf in zip(leaf_nodes, leaves):
        nx_, ny_ = pos(node)
        hot = is_highlighted(node["path"])
        parts = []
        if schema.show_outcomes:
            parts.append(leaf["outcome"])
        if schema.show_outcome_probabilities:
            parts.append(f"P = {_prob_text(leaf['probability'])}")
        if parts:
            ax.text(nx_ + 0.12, ny_, "   ".join(parts), fontsize=10,
                    ha="left", va="center", zorder=6,
                    color="#C0392B" if hot else "black",
                    fontweight="bold" if hot else "normal")

    ax.set_xlim(-0.35, max_depth * dx + 1.35)
    ax.set_ylim(-(n_leaves - 1) - 0.7, 0.9)
    if schema.title:
        ax.set_title(schema.title, fontsize=13, fontweight="bold")

    fig.tight_layout(pad=0.5)
    return _fig_to_svg(fig)


# ── Height & Distance (angle of elevation / depression) ───────────────────────

_HD_TOL = 0.01               # 1 % — absorbs a rounded param, catches a wrong one
_HD_SIGHT = dict(color="#C0392B", linewidth=1.6)
_HD_ARC = "#8E44AD"
_HD_DIM = "#1B4F72"


def _hd_agree(name: str, derived: float, supplied: Optional[float], who: str) -> float:
    """
    The derived value always wins. A supplied value that contradicts it is not a rounding slip
    but a broken question: drawing it would put a triangle on the page that does not satisfy the
    tan θ the whole question is about.
    """
    if supplied is not None and abs(supplied - derived) > _HD_TOL * max(abs(derived), 1e-9):
        raise ValueError(
            f"height_distance: {who} {name} = {supplied:g} contradicts the geometry — "
            f"tan θ = opposite / adjacent gives {derived:.4g}"
        )
    return derived


def solve_height_distance(observer_height: float, obj: HDObject) -> Dict[str, Any]:
    """Rebuild the right triangle from whichever two of (height, distance, angle) were given."""
    oh = float(observer_height)
    elev, dep = obj.angle_of_elevation, obj.angle_of_depression
    height, distance = obj.height, obj.distance
    who = f"'{obj.label}'" if obj.label else "object"

    if elev is not None and dep is not None:
        # Looking down at the foot fixes the distance; looking up at the top then fixes the height.
        distance = _hd_agree("distance", oh / math.tan(math.radians(dep)), distance, who)
        height = _hd_agree("height", oh + distance * math.tan(math.radians(elev)), height, who)

    elif elev is not None:
        t = math.tan(math.radians(elev))
        if distance is not None:
            height = _hd_agree("height", oh + distance * t, height, who)
        else:
            if height <= oh:
                raise ValueError(
                    f"height_distance: {who} rises to {height:g} but the eye is already at "
                    f"{oh:g} — there is nothing to look UP at"
                )
            distance = (height - oh) / t

    elif dep is not None:
        t = math.tan(math.radians(dep))
        if distance is not None:
            derived = oh - distance * t
            if derived < -1e-9:
                raise ValueError(
                    f"height_distance: a {dep:g}° line of sight from {oh:g} reaches the ground "
                    f"before it travels {distance:g} — the figure cannot close"
                )
            height = _hd_agree("height", max(derived, 0.0), height, who)
        else:
            target = height if height is not None else 0.0   # a car/boat is a point on the ground
            if oh - target <= 0:
                raise ValueError(
                    f"height_distance: an angle of depression needs {who} BELOW the eye at {oh:g}"
                )
            distance = (oh - target) / t
            height = target

    else:
        rise = height - oh
        if abs(rise) < 1e-9:
            raise ValueError(
                f"height_distance: {who} is level with the eye — the line of sight is horizontal "
                f"and there is no angle to mark"
            )
        angle = math.degrees(math.atan2(abs(rise), distance))
        if rise > 0:
            elev = angle
        else:
            dep = angle

    return {"distance": float(distance), "height": float(height),
            "elevation": elev, "depression": dep, "observer_height": oh}


def _hd_right_angle(ax, corner, d1, d2, size: float):
    """Small square at `corner` spanning the two unit directions d1, d2."""
    p1 = (corner[0] + d1[0] * size, corner[1] + d1[1] * size)
    pc = (p1[0] + d2[0] * size, p1[1] + d2[1] * size)
    p2 = (corner[0] + d2[0] * size, corner[1] + d2[1] * size)
    ax.plot([p1[0], pc[0], p2[0]], [p1[1], pc[1], p2[1]],
            color="black", linewidth=1.0, zorder=6)


def _hd_dim(ax, p, q, text: str, offset: Tuple[float, float], rotation: float = 0.0):
    ax.annotate("", xy=q, xytext=p,
                arrowprops=dict(arrowstyle="<|-|>", color=_HD_DIM, lw=1.0,
                                shrinkA=0, shrinkB=0, mutation_scale=9), zorder=4)
    ax.annotate(text, ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2),
                textcoords="offset points", xytext=offset, fontsize=10, color=_HD_DIM,
                ha="center", va="center", rotation=rotation, zorder=7,
                bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none", alpha=0.85))


def render_height_distance(data: Dict[str, Any], canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = HeightDistanceSchema(**data)

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))
    ax.set_aspect("equal")   # a 30° arc must subtend 30° on the page, so the axes cannot be scaled
    ax.axis("off")

    oh = schema.observer.height
    solved = [solve_height_distance(oh, ob) for ob in schema.objects]
    unit = schema.unit

    d_max = max(s["distance"] for s in solved)
    h_max = max([s["height"] for s in solved] + [oh])
    span = max(d_max, h_max)
    tick = span * 0.028              # right-angle square size
    eye = (0.0, oh)
    ow = d_max * 0.09 if oh > 0 else 0.0    # the observer's tower/cliff/building

    # ── Ground ───────────────────────────────────────────────────────────────
    g_lo, g_hi = -ow - span * 0.10, d_max + span * 0.12
    ax.plot([g_lo, g_hi], [0, 0], color="black", linewidth=1.6, zorder=3)
    if schema.ground_label:
        ax.text((g_lo + g_hi) / 2, -span * 0.045, schema.ground_label,
                fontsize=10, ha="center", va="top", style="italic")

    # ── Observer ─────────────────────────────────────────────────────────────
    if oh > 0:
        ax.add_patch(mpatches.Rectangle((-ow, 0), ow, oh, fill=False,
                                        edgecolor="black", linewidth=1.8, zorder=3))
        if schema.show_right_angles:
            _hd_right_angle(ax, (0.0, 0.0), (-1, 0), (0, 1), tick)
    ax.plot(*eye, "o", color="black", markersize=5, zorder=6)
    if schema.observer.label:
        ax.annotate(schema.observer.label, eye, textcoords="offset points",
                    xytext=(-8, 8), fontsize=11, ha="right", va="bottom",
                    fontweight="bold", zorder=7)

    # ── Horizontal line of reference through the eye (every angle is measured off it) ──
    if schema.show_angles:
        ax.plot([0, d_max * 1.06], [oh, oh], color="#7F8C8D", linestyle=(0, (6, 4)),
                linewidth=1.1, zorder=2)

    # ── Objects, sight lines, angle arcs ─────────────────────────────────────
    for i, (ob, s) in enumerate(zip(schema.objects, solved)):
        d, h = s["distance"], s["height"]
        # Each arc is sized by its OWN triangle: a shared radius either escapes past a near
        # object or shrinks until two angle labels print on top of each other.
        r_arc = min(d * 0.30, span * 0.25)

        if h > 0:
            ax.plot([d, d], [0, h], color="black", linewidth=2.2, zorder=4)
            if ob.label:
                ax.annotate(ob.label, (d, h), textcoords="offset points", xytext=(0, 9),
                            fontsize=11, ha="center", va="bottom", fontweight="bold", zorder=7)
        else:
            ax.plot(d, 0, "s", color="black", markersize=7, zorder=5)
            if ob.label:
                ax.annotate(ob.label, (d, 0), textcoords="offset points", xytext=(0, 10),
                            fontsize=11, ha="center", va="bottom", fontweight="bold", zorder=7)
        ax.plot(d, 0, "o", color="black", markersize=3.5, zorder=5)
        if schema.show_right_angles and h > 0:
            _hd_right_angle(ax, (d, 0.0), (-1, 0), (0, 1), tick)

        # The depression is read to the FOOT when the elevation already claims the top.
        sights = []
        if s["elevation"] is not None:
            sights.append((h, s["elevation"]))
        if s["depression"] is not None:
            sights.append((0.0 if s["elevation"] is not None else h, s["depression"]))

        for target_y, angle in sights:
            ax.plot([0, d], [oh, target_y], **_HD_SIGHT, zorder=4)
            if schema.show_angles:
                deg = math.degrees(math.atan2(target_y - oh, d))
                ax.add_patch(Arc(eye, 2 * r_arc, 2 * r_arc, angle=0,
                                 theta1=min(0.0, deg), theta2=max(0.0, deg),
                                 color=_HD_ARC, linewidth=1.3, zorder=5))
                mid = math.radians(deg / 2)
                ax.text(r_arc * 1.16 * math.cos(mid), oh + r_arc * 1.16 * math.sin(mid),
                        f"{angle:g}°", fontsize=11, color=_HD_ARC,
                        ha="center", va="center", zorder=8,
                        bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none", alpha=0.85))

        # ── Dimensions ───────────────────────────────────────────────────────
        if schema.show_dimensions:
            y_dim = -span * (0.10 + 0.085 * i)
            ax.plot([0, 0], [0, y_dim], color=_HD_DIM, linewidth=0.7,
                    linestyle=":", zorder=3)
            ax.plot([d, d], [0, y_dim], color=_HD_DIM, linewidth=0.7,
                    linestyle=":", zorder=3)
            _hd_dim(ax, (0, y_dim), (d, y_dim), f"{d:.4g} {unit}", (0, -9))
            if h > 0:
                x_dim = d + span * 0.055
                _hd_dim(ax, (x_dim, 0), (x_dim, h), f"{h:.4g} {unit}", (14, 0), rotation=90)

    if schema.show_dimensions and oh > 0:
        x_dim = -ow - span * 0.055
        _hd_dim(ax, (x_dim, 0), (x_dim, oh), f"{oh:.4g} {unit}", (-14, 0), rotation=90)

    y_lo = -span * (0.10 + 0.085 * max(0, len(solved) - 1)) - span * 0.10
    ax.set_xlim(-ow - span * 0.24, d_max + span * 0.24)
    ax.set_ylim(min(y_lo, -span * 0.14), h_max + span * 0.16)
    if schema.title:
        ax.set_title(schema.title, fontsize=13, fontweight="bold", pad=8)

    fig.tight_layout(pad=0.6)
    return _fig_to_svg(fig)


# ── Combined Solid (two or more solids joined) ────────────────────────────────

_CS_EDGE = dict(color="black", linewidth=1.8, solid_capstyle="round")
_CS_HIDDEN = dict(color="black", linewidth=1.1, linestyle=(0, (5, 4)))
_CS_GHOST = dict(color="#7F8C8D", linewidth=1.3, linestyle=(0, (4, 3)))
_CS_DIM_COLOR = "#1B4F72"


def _pi_multiple_text(value: float) -> Optional[str]:
    """
    '33π' when the value really is 33π — a mensuration answer is written in π, not 103.67.
    The denominator is capped low: allowed a big one, limit_denominator will "find" a π-multiple
    for any number at all and print a cube's volume of 1000 as 167431π/526.
    """
    if abs(value) < 1e-12:
        return "0"
    frac = sp.Rational(value / math.pi).limit_denominator(12)
    if abs(float(frac) * math.pi - value) > 1e-9 * max(1.0, abs(value)):
        return None
    if frac.q == 1:
        return "π" if frac.p == 1 else f"{frac.p}π"
    return f"{frac.p}π/{frac.q}"


def _cs_value_text(name: str, value: float, unit: str, power: str) -> str:
    exact = _pi_multiple_text(value)
    body = f"{exact} ≈ {value:.2f}" if exact else f"{value:.2f}"
    return f"{name} = {body} {unit}{power}".strip()


def _cs_slant(c: SolidComponent) -> Optional[float]:
    """l is recomputed from r and h. πrl is only the curved surface area for the RIGHT l."""
    if c.solid_type == "cone":
        return math.hypot(c.radius, c.height)
    if c.solid_type == "frustum":
        return math.hypot(c.height, c.radius_bottom - c.radius_top)
    return None


def _cs_extent(c: SolidComponent) -> Tuple[float, float]:
    """(half-width, vertical height) the component occupies in the figure."""
    st = c.solid_type
    if st == "cylinder" or st == "cone":
        return c.radius, c.height
    if st == "frustum":
        return c.radius_bottom, c.height
    if st == "hemisphere":
        return c.radius, c.radius
    if st == "sphere":
        return c.radius, 2 * c.radius
    if st == "cube":
        return c.side / 2, c.side
    return c.length / 2, c.height     # cuboid


def _solid_metrics(c: SolidComponent, flipped: bool) -> Dict[str, Any]:
    st = c.solid_type
    pi = math.pi
    if st == "cylinder":
        curved, volume = 2 * pi * c.radius * c.height, pi * c.radius ** 2 * c.height
    elif st == "cone":
        curved = pi * c.radius * _cs_slant(c)
        volume = pi * c.radius ** 2 * c.height / 3
    elif st == "hemisphere":
        curved, volume = 2 * pi * c.radius ** 2, 2 * pi * c.radius ** 3 / 3
    elif st == "sphere":
        curved, volume = 4 * pi * c.radius ** 2, 4 * pi * c.radius ** 3 / 3
    elif st == "cube":
        curved, volume = 4 * c.side ** 2, c.side ** 3     # the four upright faces
    elif st == "cuboid":
        curved = 2 * c.height * (c.length + c.width)
        volume = c.length * c.width * c.height
    else:   # frustum
        curved = pi * (c.radius_bottom + c.radius_top) * _cs_slant(c)
        volume = pi * c.height * (c.radius_bottom ** 2 + c.radius_top ** 2
                                  + c.radius_bottom * c.radius_top) / 3
    top = _cs_face(c, "top", flipped)
    bottom = _cs_face(c, "bottom", flipped)
    return {
        "component": c, "flipped": flipped, "curved": curved, "volume": volume,
        "top": top, "bottom": bottom, "slant": _cs_slant(c),
        "tsa": curved + (top["area"] if top else 0.0) + (bottom["area"] if bottom else 0.0),
    }


def combined_solid_metrics(components: List[SolidComponent], arrangement: str) -> Dict[str, Any]:
    """
    The combined surface area is NOT the sum of the parts' surface areas — that is the whole
    point of the question. Every value here is derived from the dimensions alone.
    """
    n = len(components)
    flips = [_cs_flipped(i, n, c.solid_type, arrangement) for i, c in enumerate(components)]
    per = [_solid_metrics(c, f) for c, f in zip(components, flips)]
    out: Dict[str, Any] = {"per_component": per, "flips": flips, "arrangement": arrangement}

    if arrangement == "side_by_side":
        out["surface_area"] = sum(m["tsa"] for m in per)
        out["volume"] = sum(m["volume"] for m in per)
        out["area_label"] = "Total surface area"
        out["volume_label"] = "Total volume"
        return out

    if arrangement == "stacked_vertical":
        area = sum(m["curved"] for m in per)
        if per[0]["bottom"]:
            area += per[0]["bottom"]["area"]      # the base the whole solid stands on
        if per[-1]["top"]:
            area += per[-1]["top"]["area"]
        # At a joint the two faces are pressed together: BOTH are internal and neither counts.
        # Only the rim the larger face leaves proud of the smaller one survives, |A_top − A_bot|.
        # This is why a cone on a hemisphere is πrl + 2πr² and not that plus two joining circles.
        for i in range(n - 1):
            a_top = per[i]["top"]["area"] if per[i]["top"] else 0.0
            a_bot = per[i + 1]["bottom"]["area"] if per[i + 1]["bottom"] else 0.0
            area += abs(a_top - a_bot)
        out["surface_area"] = area
        out["volume"] = sum(m["volume"] for m in per)
        out["area_label"] = "Total surface area"
        out["volume_label"] = "Volume"
        return out

    outer, inner = per[0], per[1]
    if inner["volume"] >= outer["volume"] - 1e-12:
        raise ValueError(
            f"combined_solid: the inner {inner['component'].solid_type} "
            f"({inner['volume']:.4g}) does not fit inside the outer "
            f"{outer['component'].solid_type} ({outer['volume']:.4g})"
        )

    if arrangement == "inscribed":
        # The inner solid is buried: what you can touch is still the outer solid's own surface.
        out["surface_area"] = outer["tsa"]
        out["volume"] = outer["volume"]
        out["area_label"] = "Total surface area (outer)"
        out["volume_label"] = "Volume (outer)"
        out["inner_volume"] = inner["volume"]
        out["remaining_volume"] = outer["volume"] - inner["volume"]
        return out

    # hollowed_out: the cavity's mouth removes that much of the block's top face and replaces
    # it with the cavity's curved wall — the mouth itself is a hole, not a surface.
    mouth = _cs_face(inner["component"], "bottom", False)
    if mouth is None:
        raise ValueError(
            f"combined_solid: a {inner['component'].solid_type} has no flat face and so cannot "
            f"be carved out from the surface — it would be a sealed void"
        )
    block_top = _cs_face(outer["component"], "top", False)
    if block_top is None or mouth["area"] > block_top["area"] + 1e-9:
        raise ValueError(
            "combined_solid: the cavity's mouth does not fit on the face it is carved into"
        )
    out["surface_area"] = outer["tsa"] - mouth["area"] + inner["curved"]
    out["volume"] = outer["volume"] - inner["volume"]
    out["area_label"] = "Surface area of the remaining solid"
    out["volume_label"] = "Volume of the remaining solid"
    out["inner_volume"] = inner["volume"]
    out["removed_volume"] = inner["volume"]
    return out


def _cs_face_ellipse(ax, cx: float, cy: float, r: float, edge, hidden, full: bool):
    """A circular face: a rim nothing sits on is fully visible; every other rim has its back
    half hidden by the solid standing on it."""
    ry = r * _ELLIPSE_RATIO
    if full:
        t = np.linspace(0, 2 * np.pi, 200)
        ax.plot(cx + r * np.cos(t), cy + ry * np.sin(t), **edge)
    else:
        fx, fy, bx, by = _ellipse_halves(cx, cy, r, ry)
        ax.plot(fx, fy, **edge)
        ax.plot(bx, by, **hidden)


def _cs_draw(ax, c: SolidComponent, cx: float, y0: float, flipped: bool,
             top_open: bool, edge, hidden) -> Dict[str, Any]:
    """Draw one component with its underside at y0. Returns where the next solid attaches."""
    st = c.solid_type
    geom: Dict[str, Any] = {"cx": cx, "y0": y0, "flipped": flipped, "solid_type": st}

    if st == "cylinder":
        r, h = c.radius, c.height
        ry = r * _ELLIPSE_RATIO
        _cs_face_ellipse(ax, cx, y0, r, edge, hidden, full=False)
        _cs_face_ellipse(ax, cx, y0 + h, r, edge, hidden, full=top_open)
        ax.plot([cx - r, cx - r], [y0, y0 + h], **edge)
        ax.plot([cx + r, cx + r], [y0, y0 + h], **edge)
        geom.update(next=(cx, y0 + h), bbox=(cx - r, cx + r, y0 - ry, y0 + h + ry),
                    r=r, h=h, r_face_y=y0 + h)

    elif st == "cone":
        r, h = c.radius, c.height
        ry = r * _ELLIPSE_RATIO
        if flipped:      # apex down: an ice-cream cone, its base glued to the solid above
            _cs_face_ellipse(ax, cx, y0 + h, r, edge, hidden, full=top_open)
            ax.plot([cx, cx - r], [y0, y0 + h], **edge)
            ax.plot([cx, cx + r], [y0, y0 + h], **edge)
            geom.update(next=(cx, y0 + h), bbox=(cx - r, cx + r, y0, y0 + h + ry),
                        r=r, h=h, r_face_y=y0 + h)
        else:
            _cs_face_ellipse(ax, cx, y0, r, edge, hidden, full=False)
            ax.plot([cx - r, cx], [y0, y0 + h], **edge)
            ax.plot([cx + r, cx], [y0, y0 + h], **edge)
            geom.update(next=(cx, y0 + h), bbox=(cx - r, cx + r, y0 - ry, y0 + h),
                        r=r, h=h, r_face_y=y0)

    elif st == "hemisphere":
        r = c.radius
        ry = r * _ELLIPSE_RATIO
        if flipped:      # dome down: the bowl a cone stands in
            t = np.linspace(np.pi, 2 * np.pi, 150)
            ax.plot(cx + r * np.cos(t), (y0 + r) + r * np.sin(t), **edge)
            _cs_face_ellipse(ax, cx, y0 + r, r, edge, hidden, full=top_open)
            geom.update(next=(cx, y0 + r), bbox=(cx - r, cx + r, y0, y0 + r + ry),
                        r=r, h=r, r_face_y=y0 + r)
        else:
            t = np.linspace(0, np.pi, 150)
            ax.plot(cx + r * np.cos(t), y0 + r * np.sin(t), **edge)
            _cs_face_ellipse(ax, cx, y0, r, edge, hidden, full=False)
            geom.update(next=(cx, y0 + r), bbox=(cx - r, cx + r, y0 - ry, y0 + r),
                        r=r, h=r, r_face_y=y0)

    elif st == "sphere":
        r = c.radius
        cy = y0 + r
        t = np.linspace(0, 2 * np.pi, 300)
        ax.plot(cx + r * np.cos(t), cy + r * np.sin(t), **edge)
        _cs_face_ellipse(ax, cx, cy, r, dict(edge, linewidth=1.2), hidden, full=False)
        geom.update(next=(cx, y0 + 2 * r), bbox=(cx - r, cx + r, y0, y0 + 2 * r),
                    r=r, h=2 * r, r_face_y=cy)

    elif st == "frustum":
        rb, rt, h = c.radius_bottom, c.radius_top, c.height
        _cs_face_ellipse(ax, cx, y0, rb, edge, hidden, full=False)
        _cs_face_ellipse(ax, cx, y0 + h, rt, edge, hidden, full=top_open)
        ax.plot([cx - rb, cx - rt], [y0, y0 + h], **edge)
        ax.plot([cx + rb, cx + rt], [y0, y0 + h], **edge)
        geom.update(next=(cx, y0 + h), r=rt, h=h, r_face_y=y0 + h,
                    bbox=(cx - rb, cx + rb, y0 - rb * _ELLIPSE_RATIO,
                          y0 + h + rt * _ELLIPSE_RATIO))

    else:   # cube | cuboid — oblique (cabinet) projection
        L = c.side if st == "cube" else c.length
        H = c.side if st == "cube" else c.height
        D = c.side if st == "cube" else c.width
        dx, dy = D * _OBLIQUE_DX, D * _OBLIQUE_DY
        x0 = cx - L / 2
        A, B = (x0, y0), (x0 + L, y0)
        C, Dv = (x0 + L, y0 + H), (x0, y0 + H)
        A2, B2 = (A[0] + dx, A[1] + dy), (B[0] + dx, B[1] + dy)
        C2, D2 = (C[0] + dx, C[1] + dy), (Dv[0] + dx, Dv[1] + dy)
        for p, q in [(A, B), (B, C), (C, Dv), (Dv, A), (Dv, D2), (C, C2), (B, B2),
                     (D2, C2), (C2, B2)]:
            ax.plot([p[0], q[0]], [p[1], q[1]], **edge)
        for p, q in [(A, A2), (A2, B2), (A2, D2)]:
            ax.plot([p[0], q[0]], [p[1], q[1]], **hidden)
        geom.update(next=(cx + dx / 2, y0 + H + dy / 2), r=None, h=H,
                    bbox=(x0, x0 + L + dx, y0, y0 + H + dy),
                    box=(L, H, D, dx, dy, x0))
    return geom


_CS_DIM_BOX = dict(boxstyle="round,pad=0.12", fc="white", ec="none", alpha=0.9)


def _cs_dim(name: str, value: float, unit: str) -> str:
    """A derived slant height is 10.594810050208546; an exam figure says 10.59."""
    txt = f"{value:.2f}".rstrip("0").rstrip(".")
    return f"{name} = {txt} {unit}".strip()


def _cs_label(ax, c: SolidComponent, g: Dict[str, Any], unit: str, pad: float,
              show_dims: bool, labelled_faces: set,
              label_frac: float = 0.5, mirror: bool = False,
              label_x: Optional[float] = None):
    """`mirror` puts the dimensions on the far side — a cavity and the block it is carved from
    occupy the same column, so their labels have to be pushed apart or they print on top of
    each other."""
    st = c.solid_type
    x_lo, x_hi, y_lo, y_hi = g["bbox"]
    if c.label:
        ax.text(label_x if label_x is not None else x_lo - pad * 0.45,
                y_lo + label_frac * (y_hi - y_lo), c.label,
                fontsize=11, fontweight="bold", ha="right", va="center", zorder=8)
    if not show_dims:
        return

    if st in ("cube", "cuboid"):
        L, H, D, dx, dy, x0 = g["box"]
        y0 = g["y0"]
        names = ("a", "a", "a") if st == "cube" else ("l", "b", "h")
        ax.text(x0 + L / 2, y0 - pad * 0.18, _cs_dim(names[0], L, unit), zorder=8,
                ha="center", va="top", bbox=_CS_DIM_BOX, **_DIM_FONT)
        if st == "cuboid":
            ax.text(x0 + L + dx / 2 + pad * 0.10, y0 + dy / 2 - pad * 0.12,
                    _cs_dim(names[1], D, unit), zorder=8,
                    ha="left", va="center", bbox=_CS_DIM_BOX, **_DIM_FONT)
            ax.text(x0 + L + dx + pad * 0.12, y0 + dy + H / 2, _cs_dim(names[2], H, unit),
                    zorder=8, ha="left", va="center", bbox=_CS_DIM_BOX, **_DIM_FONT)
        return

    cx, r = g["cx"], g["r"]
    # The radius belongs on the face it measures. Two solids that meet share that circle, so
    # it is only ever drawn and labelled once.
    y_face = g["r_face_y"]
    face_key = (round(cx, 6), round(y_face, 6), round(r, 6))
    if face_key not in labelled_faces:
        labelled_faces.add(face_key)
        ax.plot([cx, cx + r], [y_face, y_face], color="black", linewidth=1.0, zorder=5)
        ax.plot(cx, y_face, "ko", markersize=3, zorder=5)
        ax.text(cx + r / 2, y_face + pad * 0.10, _cs_dim("r", r, unit), zorder=8,
                ha="center", va="bottom", bbox=_CS_DIM_BOX, **_DIM_FONT)

    if st == "frustum":
        rb = c.radius_bottom
        ax.plot([cx, cx + rb], [g["y0"], g["y0"]], color="black", linewidth=1.0, zorder=5)
        ax.text(cx + rb / 2, g["y0"] - pad * 0.16, _cs_dim("R", rb, unit), zorder=8,
                ha="center", va="top", bbox=_CS_DIM_BOX, **_DIM_FONT)

    if st in ("cylinder", "cone", "frustum"):
        x_h = (x_lo - pad * 1.5) if mirror else (x_hi + pad * 0.16)
        y0 = g["y0"]
        ax.annotate("", xy=(x_h, y0 + c.height), xytext=(x_h, y0),
                    arrowprops=dict(arrowstyle="<|-|>", color=_CS_DIM_COLOR, lw=1.0,
                                    shrinkA=0, shrinkB=0, mutation_scale=9), zorder=5)
        ax.text(x_h + pad * (-0.10 if mirror else 0.10), y0 + c.height / 2,
                _cs_dim("h", c.height, unit), zorder=8,
                ha="right" if mirror else "left", va="center", bbox=_CS_DIM_BOX, **_DIM_FONT)

    slant = _cs_slant(c)
    if slant is not None:
        # Printed against the slant edge itself — an "l" floating beside the solid is just a
        # number, an "l" on the sloping side is the length the question means. A cavity's l
        # goes on the inside of that edge, where the solid has been hollowed away.
        r_top = c.radius_top if st == "frustum" else (0.0 if not g["flipped"] else c.radius)
        r_bot = c.radius_bottom if st == "frustum" else (c.radius if not g["flipped"] else 0.0)
        mid = (cx - (r_bot + r_top) / 2, g["y0"] + c.height / 2)
        ax.annotate(_cs_dim("l", slant, unit), mid, textcoords="offset points",
                    xytext=(14 if mirror else -14, 7), fontsize=11, style="italic",
                    ha="left" if mirror else "right", va="center", zorder=8,
                    bbox=_CS_DIM_BOX)


def render_combined_solid(data: Dict[str, Any], canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = CombinedSolidSchema(**data)
    metrics = combined_solid_metrics(schema.components, schema.arrangement)

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))
    ax.set_aspect("equal")
    ax.axis("off")

    comps = schema.components
    flips = metrics["flips"]
    hidden = _CS_HIDDEN if schema.show_hidden_edges else _CS_EDGE
    geoms: List[Dict[str, Any]] = []
    pad = max(max(_cs_extent(c)) for c in comps) * 0.42

    if schema.arrangement == "stacked_vertical":
        cx, y = 0.0, 0.0
        for i, c in enumerate(comps):
            g = _cs_draw(ax, c, cx, y, flips[i], top_open=(i == len(comps) - 1),
                         edge=_CS_EDGE, hidden=hidden)
            geoms.append(g)
            cx, y = g["next"]

    elif schema.arrangement == "side_by_side":
        cx = 0.0
        for c in comps:
            half, _ = _cs_extent(c)
            g = _cs_draw(ax, c, cx + half, 0.0, False, top_open=True,
                         edge=_CS_EDGE, hidden=hidden)
            geoms.append(g)
            cx = g["bbox"][1] + pad * 1.5
        ax.plot([geoms[0]["bbox"][0] - pad * 0.3, geoms[-1]["bbox"][1] + pad * 0.3], [0, 0],
                color="#7F8C8D", linewidth=1.0, zorder=1)

    else:   # inscribed | hollowed_out — outer first, cavity/inner ghosted inside it
        outer, inner = comps
        g_out = _cs_draw(ax, outer, 0.0, 0.0, False, top_open=True,
                         edge=_CS_EDGE, hidden=hidden)
        geoms.append(g_out)
        x_lo, x_hi, y_lo, y_hi = g_out["bbox"]
        _, inner_h = _cs_extent(inner)
        if schema.arrangement == "inscribed":
            g_in = _cs_draw(ax, inner, g_out["next"][0], (y_lo + y_hi) / 2 - inner_h / 2,
                            False, top_open=True, edge=_CS_GHOST, hidden=_CS_GHOST)
        else:
            top_cx, top_y = g_out["next"]
            g_in = _cs_draw(ax, inner, top_cx, top_y - inner_h,
                            flipped=inner.solid_type in ("cone", "hemisphere"),
                            top_open=True, edge=_CS_GHOST, hidden=_CS_GHOST)
            # A cavity as wide as the block's face has no mouth of its own to draw: the mouth
            # IS that rim, so the rim is restored over the ghosted outline.
            face = _cs_face(outer, "top", False)
            mouth = _cs_face(inner, "bottom", False)
            if (face and mouth and face["kind"] == "circle" and mouth["kind"] == "circle"
                    and abs(face["r"] - mouth["r"]) < 1e-9):
                _cs_face_ellipse(ax, top_cx, top_y, face["r"], _CS_EDGE, hidden, full=True)
        geoms.append(g_in)

    nested = schema.arrangement in ("inscribed", "hollowed_out")
    outer_x_lo = min(g["bbox"][0] for g in geoms)
    labelled_faces: set = set()
    for i, (c, g) in enumerate(zip(comps, geoms)):
        # Nested solids share a column: their labels are pushed to opposite ends of it and out
        # past the OUTER silhouette, or the inner one prints across the block containing it.
        frac = 0.5 if not nested else (0.74 if i == 0 else 0.26)
        _cs_label(ax, c, g, schema.unit, pad, schema.show_dimensions, labelled_faces,
                  label_frac=frac, mirror=nested and i == 1,
                  label_x=(outer_x_lo - pad * 0.45) if nested else None)

    x_lo = min(g["bbox"][0] for g in geoms) - pad * (2.6 if nested else 1.3)
    x_hi = max(g["bbox"][1] for g in geoms) + pad * 1.3
    y_lo = min(g["bbox"][2] for g in geoms) - pad * 0.6
    y_hi = max(g["bbox"][3] for g in geoms) + pad * 0.5

    # ── Computed values (axes coordinates, so they can never fall off the canvas) ──
    notes: List[str] = []
    if schema.show_total_surface_area:
        notes.append(_cs_value_text(metrics["area_label"], metrics["surface_area"],
                                    schema.unit, "²"))
    if schema.show_volume:
        notes.append(_cs_value_text(metrics["volume_label"], metrics["volume"],
                                    schema.unit, "³"))
        if "remaining_volume" in metrics:
            notes.append(_cs_value_text("Volume outside the inner solid",
                                        metrics["remaining_volume"], schema.unit, "³"))
    if notes:
        y_lo -= (y_hi - y_lo) * 0.06 * len(notes)
        ax.text(0.02, 0.02, "\n".join(notes), transform=ax.transAxes,
                fontsize=11, ha="left", va="bottom", zorder=9,
                bbox=dict(boxstyle="round,pad=0.35", fc="white", ec="#34495E", alpha=0.92))

    ax.set_xlim(x_lo, x_hi)
    ax.set_ylim(y_lo, y_hi)
    if schema.title:
        ax.set_title(schema.title, fontsize=13, fontweight="bold", pad=8)

    fig.tight_layout(pad=0.6)
    return _fig_to_svg(fig)


# ── 3D Coordinate Geometry: planes and lines ──────────────────────────────────

_P3_PLANE_COLORS = ["#3498DB", "#E74C3C", "#27AE60"]
_P3_LINE_COLORS = ["#8E44AD", "#D68910", "#16A085"]
_P3_TOL = 1e-9


def _p3_normal(plane: Plane3D) -> np.ndarray:
    return np.array([plane.a, plane.b, plane.c], dtype=float)


def _v3(v) -> str:
    return "(" + ", ".join(f"{float(c):g}" for c in np.round(np.asarray(v, float), 4)) + ")"


def _plane_equation_text(pl: Plane3D) -> str:
    """ax + by + cz = d, printed the way a paper prints it: 'y + z = 3', not '0x + 1y + 1z = 3'."""
    terms = ""
    for coef, var in ((pl.a, "x"), (pl.b, "y"), (pl.c, "z")):
        if abs(coef) < 1e-12:
            continue
        mag = "" if abs(abs(coef) - 1) < 1e-12 else f"{abs(coef):g}"
        if not terms:
            terms = f"{'-' if coef < 0 else ''}{mag}{var}"
        else:
            terms += f" {'+' if coef > 0 else '-'} {mag}{var}"
    return f"{terms} = {pl.d:g}"


def point_plane_distance(point, plane: Plane3D) -> float:
    """|ax + by + cz − d| / √(a² + b² + c²)."""
    n = _p3_normal(plane)
    return abs(float(np.dot(n, np.asarray(point, dtype=float))) - plane.d) / float(
        np.linalg.norm(n))


def plane_plane_intersection(p1: Plane3D, p2: Plane3D):
    """
    The line two planes share: its direction is n₁ × n₂, and a point on it is found by zeroing
    the coordinate whose cross-product component is largest — that keeps the 2×2 solve away
    from a singular matrix.
    """
    n1, n2 = _p3_normal(p1), _p3_normal(p2)
    direction = np.cross(n1, n2)
    if float(np.linalg.norm(direction)) < 1e-9:
        return None     # parallel or coincident: no unique line
    k = int(np.argmax(np.abs(direction)))
    i, j = [t for t in range(3) if t != k]
    mat = np.array([[n1[i], n1[j]], [n2[i], n2[j]]], dtype=float)
    sol = np.linalg.solve(mat, np.array([p1.d, p2.d], dtype=float))
    point = np.zeros(3)
    point[i], point[j] = sol
    return point, direction / float(np.linalg.norm(direction))


def line_plane_intersection(line: Line3D, plane: Plane3D):
    """Where r = a + λb pierces the plane, or None when b lies in the plane."""
    n = _p3_normal(plane)
    a = np.array(line.point, dtype=float)
    b = np.array(line.direction, dtype=float)
    denom = float(np.dot(n, b))
    if abs(denom) < 1e-9:
        return None
    lam = (plane.d - float(np.dot(n, a))) / denom
    return a + lam * b


def angle_between_planes(p1: Plane3D, p2: Plane3D) -> float:
    """The acute angle: cos θ = |n₁·n₂| / (|n₁||n₂|)."""
    n1, n2 = _p3_normal(p1), _p3_normal(p2)
    cos_t = abs(float(np.dot(n1, n2))) / (float(np.linalg.norm(n1)) * float(np.linalg.norm(n2)))
    return math.degrees(math.acos(min(1.0, max(-1.0, cos_t))))


def angle_line_plane(line: Line3D, plane: Plane3D) -> float:
    """sin θ = |n·b| / (|n||b|) — the line's angle with the plane is the COMPLEMENT of its
    angle with the normal, so this is an arcsin and not an arccos."""
    n = _p3_normal(plane)
    b = np.array(line.direction, dtype=float)
    sin_t = abs(float(np.dot(n, b))) / (float(np.linalg.norm(n)) * float(np.linalg.norm(b)))
    return math.degrees(math.asin(min(1.0, max(-1.0, sin_t))))


def angle_between_lines(l1: Line3D, l2: Line3D) -> float:
    b1 = np.array(l1.direction, dtype=float)
    b2 = np.array(l2.direction, dtype=float)
    cos_t = abs(float(np.dot(b1, b2))) / (float(np.linalg.norm(b1)) * float(np.linalg.norm(b2)))
    return math.degrees(math.acos(min(1.0, max(-1.0, cos_t))))


def _p3_plane_surface(ax, plane: Plane3D, lim: float, color: str):
    """Draw the plane over the viewing box, dropping the part that leaves it."""
    n = _p3_normal(plane)
    k = int(np.argmax(np.abs(n)))
    i, j = [t for t in range(3) if t != k]
    grid = np.linspace(-lim, lim, 30)
    U, V = np.meshgrid(grid, grid)
    W = (plane.d - n[i] * U - n[j] * V) / n[k]
    W = np.where(np.abs(W) <= lim, W, np.nan)
    coords = [None, None, None]
    coords[i], coords[j], coords[k] = U, V, W
    ax.plot_surface(coords[0], coords[1], coords[2], color=color, alpha=0.28,
                    linewidth=0, antialiased=True, shade=False, zorder=2)


def _p3_line_points(point, direction, lim: float):
    """Sample the line and keep only what falls inside the viewing box."""
    a = np.asarray(point, dtype=float)
    b = np.asarray(direction, dtype=float)
    b = b / float(np.linalg.norm(b))
    t = np.linspace(-4 * lim, 4 * lim, 800)
    pts = a[None, :] + t[:, None] * b[None, :]
    inside = np.all(np.abs(pts) <= lim, axis=1)
    if not inside.any():
        return None
    pts = np.where(inside[:, None], pts, np.nan)
    return pts


def render_plane_line_3d(data: Dict[str, Any], canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = PlaneLine3DSchema(**data)

    from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

    fig = plt.figure(figsize=(canvas_w / 100, canvas_h / 100))
    ax = fig.add_subplot(111, projection="3d")

    # ── Viewing box: every computed point must land inside it or its label is lost ──
    extents = [1.0]
    for pl in schema.planes:
        n = _p3_normal(pl)
        extents.append(abs(pl.d) / float(np.linalg.norm(n)) + 1.0)
        for comp in (pl.a, pl.b, pl.c):
            if abs(comp) > 1e-9:
                extents.append(abs(pl.d / comp))     # the axis intercepts
    for ln in schema.lines:
        extents.extend(abs(v) + 1.0 for v in ln.point)
    for pt in schema.points:
        extents.extend([abs(pt.x), abs(pt.y), abs(pt.z)])
    lim = float(max(e for e in extents if math.isfinite(e))) * 1.25
    lim = max(min(lim, 40.0), 2.0)

    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)
    ax.set_zlim(-lim, lim)
    if schema.show_axes:
        ax.set_xlabel("x", fontsize=10)
        ax.set_ylabel("y", fontsize=10)
        ax.set_zlabel("z", fontsize=10)
        ax.plot([-lim, lim], [0, 0], [0, 0], color="#7F8C8D", linewidth=0.9, zorder=1)
        ax.plot([0, 0], [-lim, lim], [0, 0], color="#7F8C8D", linewidth=0.9, zorder=1)
        ax.plot([0, 0], [0, 0], [-lim, lim], color="#7F8C8D", linewidth=0.9, zorder=1)

    # The figure carries short tags (π₁, L₁) and the legend carries the equations — an equation
    # printed in the 3D scene lands on top of whatever else is there.
    notes: List[Tuple[str, str]] = []

    # ── Planes, with their normals ───────────────────────────────────────────
    for i, pl in enumerate(schema.planes):
        color = pl.colour or _P3_PLANE_COLORS[i % len(_P3_PLANE_COLORS)]
        _p3_plane_surface(ax, pl, lim, color)
        n = _p3_normal(pl)
        unit_n = n / float(np.linalg.norm(n))
        foot = n * pl.d / float(np.dot(n, n))       # the point of the plane closest to O
        tag = pl.label or f"π{_subscript(i + 1)}"
        notes.append((f"{tag}:  {_plane_equation_text(pl)}", color))
        if schema.show_normals:
            ax.quiver(*foot, *(unit_n * lim * 0.45), color=color, linewidth=2,
                      arrow_length_ratio=0.18, zorder=6)
            ax.text(*(foot + unit_n * lim * 0.52), f"n{_subscript(i + 1)} = {_v3(n)}",
                    fontsize=9, color=color, zorder=8)
        else:
            ax.text(*(foot + unit_n * lim * 0.22), tag, fontsize=12, color=color,
                    fontweight="bold", zorder=8)

    # ── Lines ────────────────────────────────────────────────────────────────
    for i, ln in enumerate(schema.lines):
        color = ln.colour or _P3_LINE_COLORS[i % len(_P3_LINE_COLORS)]
        pts = _p3_line_points(ln.point, ln.direction, lim)
        if pts is not None:
            ax.plot(pts[:, 0], pts[:, 1], pts[:, 2], color=color, linewidth=2.0, zorder=5)
        a = np.asarray(ln.point, dtype=float)
        ax.scatter(*a, color=color, s=26, depthshade=False, zorder=7)
        tag = ln.label or f"L{_subscript(i + 1)}"
        ax.text(*a, f"  {tag}", fontsize=11, color=color, fontweight="bold", zorder=8)
        notes.append((f"{tag}:  r = {_v3(ln.point)} + λ{_v3(ln.direction)}", color))

    # ── Points ───────────────────────────────────────────────────────────────
    for pt in schema.points:
        ax.scatter(pt.x, pt.y, pt.z, color="black", s=38, depthshade=False, zorder=7)
        text = f"{pt.label} {_v3((pt.x, pt.y, pt.z))}" if pt.label else _v3((pt.x, pt.y, pt.z))
        ax.text(pt.x, pt.y, pt.z, f"  {text}", fontsize=10, zorder=8)

    def tag_plane(i: int) -> str:
        return schema.planes[i].label or f"π{_subscript(i + 1)}"

    def tag_line(i: int) -> str:
        return schema.lines[i].label or f"L{_subscript(i + 1)}"

    # ── Intersections (computed, never supplied) ─────────────────────────────
    if schema.show_intersection:
        for i in range(len(schema.planes)):
            for j in range(i + 1, len(schema.planes)):
                hit = plane_plane_intersection(schema.planes[i], schema.planes[j])
                if hit is None:
                    notes.append((f"{tag_plane(i)} and {tag_plane(j)} are parallel — "
                                  f"they never meet", "#C0392B"))
                    continue
                point, direction = hit
                pts = _p3_line_points(point, direction, lim)
                if pts is not None:
                    ax.plot(pts[:, 0], pts[:, 1], pts[:, 2], color="#C0392B",
                            linewidth=2.6, linestyle="--", zorder=6)
                notes.append((f"{tag_plane(i)} meets {tag_plane(j)} in the line  "
                              f"r = {_v3(point)} + λ{_v3(direction)}", "#C0392B"))
        for i, ln in enumerate(schema.lines):
            for j, pl in enumerate(schema.planes):
                hit = line_plane_intersection(ln, pl)
                if hit is None:
                    notes.append((f"{tag_line(i)} is parallel to {tag_plane(j)}", "#C0392B"))
                    continue
                ax.scatter(*hit, color="#C0392B", s=70, marker="*", depthshade=False, zorder=9)
                ax.text(*hit, f"  {_v3(hit)}", fontsize=9, color="#C0392B", zorder=9)
                notes.append((f"{tag_line(i)} pierces {tag_plane(j)} at {_v3(hit)}", "#C0392B"))

    # ── Angles (from the dot product, never from the params) ─────────────────
    if schema.show_angle:
        if len(schema.planes) >= 2:
            notes.append((f"Angle between {tag_plane(0)} and {tag_plane(1)} = "
                          f"{angle_between_planes(schema.planes[0], schema.planes[1]):.2f}°",
                          "black"))
        if schema.lines and schema.planes:
            notes.append((f"Angle between {tag_line(0)} and {tag_plane(0)} = "
                          f"{angle_line_plane(schema.lines[0], schema.planes[0]):.2f}°",
                          "black"))
        if len(schema.lines) >= 2:
            notes.append((f"Angle between {tag_line(0)} and {tag_line(1)} = "
                          f"{angle_between_lines(schema.lines[0], schema.lines[1]):.2f}°",
                          "black"))

    # ── Perpendicular distances ──────────────────────────────────────────────
    if schema.show_distance:
        for pt in schema.points:
            p_vec = np.array([pt.x, pt.y, pt.z], dtype=float)
            for j, pl in enumerate(schema.planes):
                dist = point_plane_distance(p_vec, pl)
                n = _p3_normal(pl)
                foot = p_vec - (float(np.dot(n, p_vec)) - pl.d) / float(np.dot(n, n)) * n
                ax.plot(*zip(p_vec, foot), color="#34495E", linestyle=":", linewidth=1.6,
                        zorder=6)
                ax.scatter(*foot, color="#34495E", s=22, depthshade=False, zorder=7)
                name = pt.label or _v3(p_vec)
                notes.append((f"Distance from {name} to {tag_plane(j)} = {dist:.4g}", "black"))

    for i, (line, color) in enumerate(notes):
        ax.text2D(0.01, 0.985 - i * 0.045, line, transform=ax.transAxes,
                  fontsize=9, va="top", ha="left", color=color, zorder=10,
                  bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="none", alpha=0.85))

    ax.set_title(schema.title or "3D Coordinate Geometry", fontsize=12, fontweight="bold", pad=10)
    fig.tight_layout()
    return _fig_to_svg(fig)


# ── Distribution Curve (probability / statistics) ─────────────────────────────

_SQRT2 = math.sqrt(2.0)
_DC_CURVE = "#1B4F72"
_DC_SHADE = "#3498DB"


def _norm_pdf(x, mean: float, sd: float):
    z = (np.asarray(x, dtype=float) - mean) / sd
    return np.exp(-0.5 * z * z) / (sd * math.sqrt(2 * math.pi))


def _norm_cdf(x: float, mean: float = 0.0, sd: float = 1.0) -> float:
    """scipy is not available; erf gives the exact CDF to machine precision anyway."""
    return 0.5 * (1.0 + math.erf((x - mean) / (sd * _SQRT2)))


def _t_pdf(x, df: float):
    coeff = math.gamma((df + 1) / 2) / (math.sqrt(df * math.pi) * math.gamma(df / 2))
    return coeff * (1.0 + np.asarray(x, dtype=float) ** 2 / df) ** (-(df + 1) / 2)


def _simpson(f, lo: float, hi: float, n: int = 4000) -> float:
    if hi <= lo:
        return 0.0
    n += n % 2
    xs = np.linspace(lo, hi, n + 1)
    ys = np.asarray(f(xs), dtype=float)
    h = (hi - lo) / n
    return float(h / 3 * (ys[0] + ys[-1] + 4 * ys[1:-1:2].sum() + 2 * ys[2:-1:2].sum()))


def _t_cdf(x: float, df: float) -> float:
    """
    x = √ν·tan θ turns the heavy tail into ∫cos^(ν-1)θ dθ over a FINITE θ-interval, so Simpson
    converges even at ν = 1 where the tails only decay like 1/x² and a truncated integral on x
    would silently lose a percent of the probability.
    """
    coeff = math.gamma((df + 1) / 2) / (math.sqrt(df * math.pi) * math.gamma(df / 2))
    upper = math.atan(x / math.sqrt(df))
    area = _simpson(lambda th: np.maximum(np.cos(th), 1e-12) ** (df - 1),
                    -math.pi / 2, upper)
    return float(min(1.0, max(0.0, coeff * math.sqrt(df) * area)))


def _binomial_pmf(k: int, n: int, p: float) -> float:
    return math.comb(n, k) * (p ** k) * ((1.0 - p) ** (n - k))


def _poisson_pmf(k: int, lam: float) -> float:
    return math.exp(-lam + k * math.log(lam) - math.lgamma(k + 1))


def _dc_moments(schema: DistributionCurveSchema) -> Tuple[float, float]:
    """(mean, sd) derived from the distribution's own parameters — np and √(npq), not guesses."""
    p = schema.parameters
    dist = schema.distribution
    if dist in ("normal", "standard_normal"):
        return float(p.mean), float(p.std_dev)
    if dist == "binomial":
        return p.n * p.p, math.sqrt(p.n * p.p * (1.0 - p.p))
    if dist == "poisson":
        return float(p.lambda_), math.sqrt(p.lambda_)
    var = p.df / (p.df - 2) if p.df > 2 else float("inf")   # t has no variance below ν = 3
    return 0.0, math.sqrt(var) if math.isfinite(var) else 1.5


def _dc_support(schema: DistributionCurveSchema) -> int:
    """The largest k worth drawing / summing for a discrete distribution."""
    p = schema.parameters
    if schema.distribution == "binomial":
        return int(p.n)
    lam = float(p.lambda_)
    return int(math.ceil(lam + 5 * math.sqrt(lam) + 8))


def distribution_area(schema: DistributionCurveSchema,
                      lo: Optional[float], hi: Optional[float]) -> float:
    """
    The shaded probability, integrated (continuous) or summed (discrete) here. A value carried
    in the params is exactly the number the model guesses wrong, so none is accepted.
    """
    mean, sd = _dc_moments(schema)
    dist = schema.distribution

    if dist in ("normal", "standard_normal"):
        lo_p = 0.0 if lo is None else _norm_cdf(lo, mean, sd)
        hi_p = 1.0 if hi is None else _norm_cdf(hi, mean, sd)
        return max(0.0, hi_p - lo_p)

    if dist == "t":
        df = float(schema.parameters.df)
        lo_p = 0.0 if lo is None else _t_cdf(lo, df)
        hi_p = 1.0 if hi is None else _t_cdf(hi, df)
        return max(0.0, hi_p - lo_p)

    # Discrete: the region covers the whole integers it contains, P(a ≤ X ≤ b) = Σ p(k).
    k_max = _dc_support(schema)
    sum_max = k_max if dist == "binomial" else int(
        math.ceil(schema.parameters.lambda_ + 14 * math.sqrt(schema.parameters.lambda_) + 40))
    k_lo = 0 if lo is None else max(0, math.ceil(lo - 1e-9))
    k_hi = sum_max if hi is None else min(sum_max, math.floor(hi + 1e-9))
    pmf = ((lambda k: _binomial_pmf(k, schema.parameters.n, schema.parameters.p))
           if dist == "binomial" else
           (lambda k: _poisson_pmf(k, schema.parameters.lambda_)))
    return float(sum(pmf(k) for k in range(k_lo, k_hi + 1)))


def _dc_prob_expr(lo: Optional[float], hi: Optional[float], discrete: bool) -> str:
    var = "X"
    fmt = (lambda v: f"{v:g}")
    if lo is None:
        return f"P({var} ≤ {fmt(hi)})"
    if hi is None:
        return f"P({var} ≥ {fmt(lo)})"
    if discrete and abs(hi - lo) < 1e-9:
        return f"P({var} = {fmt(lo)})"
    return f"P({fmt(lo)} ≤ {var} ≤ {fmt(hi)})"


def render_distribution_curve(data: Dict[str, Any],
                              canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = DistributionCurveSchema(**data)

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))

    dist = schema.distribution
    discrete = dist in ("binomial", "poisson")
    mean, sd = _dc_moments(schema)
    notes: List[str] = []

    if discrete:
        # ── Bars: a discrete distribution has no curve to draw ────────────────
        k_max = _dc_support(schema)
        # Bars out at 40σ are invisible zeros that squash the interesting ones — but a bound the
        # question actually asks about is never trimmed away.
        k_from = max(0, int(math.floor(mean - 4.5 * sd)))
        k_to = min(k_max, int(math.ceil(mean + 4.5 * sd)))
        for reg in schema.shaded_regions:
            for v in (reg.from_value, reg.to_value):
                if v is not None:
                    k_from = max(0, min(k_from, int(math.floor(v)) - 1))
                    k_to = min(k_max, max(k_to, int(math.ceil(v)) + 1))
        ks = np.arange(k_from, k_to + 1)
        pmf = ((lambda k: _binomial_pmf(int(k), schema.parameters.n, schema.parameters.p))
               if dist == "binomial" else
               (lambda k: _poisson_pmf(int(k), schema.parameters.lambda_)))
        probs = np.array([pmf(k) for k in ks], dtype=float)

        shaded_mask = np.zeros_like(probs, dtype=bool)
        for reg in schema.shaded_regions:
            lo = -math.inf if reg.from_value is None else reg.from_value - 1e-9
            hi = math.inf if reg.to_value is None else reg.to_value + 1e-9
            shaded_mask |= (ks >= lo) & (ks <= hi)
        colors = [_DC_SHADE if m else "#AED6F1" for m in shaded_mask]
        ax.bar(ks, probs, width=0.86, color=colors, edgecolor="#1B4F72",
               linewidth=0.9, zorder=3)
        x_lo, x_hi = k_from - 0.8, k_to + 0.8
        y_top = float(probs.max())

        if schema.overlay_normal:
            grid = np.linspace(x_lo, x_hi, 600)
            ax.plot(grid, _norm_pdf(grid, mean, sd), color="#C0392B", linewidth=2.0,
                    zorder=5, label=f"N({mean:g}, {sd ** 2:.3g}) approximation")
            ax.legend(fontsize=9, loc="upper right", framealpha=0.9)
            notes.append(f"Normal approximation: μ = {mean:g}, σ = {sd:.4g}")
    else:
        # ── Smooth curve ─────────────────────────────────────────────────────
        bounds = [mean - 4 * sd, mean + 4 * sd]
        for reg in schema.shaded_regions:
            for v in (reg.from_value, reg.to_value):
                if v is not None:
                    bounds += [v - 0.5 * sd, v + 0.5 * sd]
        x_lo, x_hi = min(bounds), max(bounds)
        grid = np.linspace(x_lo, x_hi, 1200)
        pdf = (_norm_pdf(grid, mean, sd) if dist in ("normal", "standard_normal")
               else _t_pdf(grid, schema.parameters.df))
        ax.plot(grid, pdf, color=_DC_CURVE, linewidth=2.2, zorder=4)
        y_top = float(np.max(pdf))

        for reg in schema.shaded_regions:
            lo = x_lo if reg.from_value is None else reg.from_value
            hi = x_hi if reg.to_value is None else reg.to_value
            mask = (grid >= lo) & (grid <= hi)
            ax.fill_between(grid[mask], 0, pdf[mask], color=_DC_SHADE, alpha=0.45, zorder=2)
            ax.plot([lo, lo], [0, float(np.interp(lo, grid, pdf))], color=_DC_CURVE,
                    linewidth=1.0, linestyle="--", zorder=3)
            ax.plot([hi, hi], [0, float(np.interp(hi, grid, pdf))], color=_DC_CURVE,
                    linewidth=1.0, linestyle="--", zorder=3)

    # ── The shaded probability, computed here ────────────────────────────────
    for reg in schema.shaded_regions:
        area = distribution_area(schema, reg.from_value, reg.to_value)
        expr = reg.label or _dc_prob_expr(reg.from_value, reg.to_value, discrete)
        if schema.show_area_value:
            notes.append(f"{expr} = {area:.4f}")
        else:
            notes.append(expr)

    # ── Mean and standard-deviation lines ────────────────────────────────────
    if schema.show_mean_line:
        ax.axvline(mean, color="#C0392B", linestyle="--", linewidth=1.4, zorder=5)
        ax.annotate(f"μ = {mean:g}", (mean, y_top), textcoords="offset points",
                    xytext=(5, 4), fontsize=10, color="#C0392B", zorder=8)

    if schema.show_sd_lines:
        for k in (1, 2, 3):
            for sign in (-1, 1):
                xv = mean + sign * k * sd
                ax.axvline(xv, color="#7F8C8D", linestyle=":", linewidth=1.1, zorder=3)
            pct = distribution_area(schema, mean - k * sd, mean + k * sd) * 100
            y_band = y_top * (1.02 + 0.085 * k)
            ax.annotate("", xy=(mean + k * sd, y_band), xytext=(mean - k * sd, y_band),
                        arrowprops=dict(arrowstyle="<|-|>", color="#7F8C8D", lw=1.0,
                                        shrinkA=0, shrinkB=0, mutation_scale=9), zorder=5)
            ax.text(mean, y_band, f"±{k}σ  {pct:.2f}%", fontsize=9, color="#34495E",
                    ha="center", va="center", zorder=8,
                    bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.9))
        notes.append(f"σ = {sd:g}")
        y_top *= 1.34

    if notes:
        ax.text(0.015, 0.97, "\n".join(notes), transform=ax.transAxes, fontsize=10,
                va="top", ha="left", zorder=9,
                bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#34495E", alpha=0.92))

    ax.set_xlim(x_lo, x_hi)
    ax.set_ylim(0, y_top * 1.22)
    ax.set_xlabel(schema.x_label or ("k" if discrete else "x"), fontsize=11)
    ax.set_ylabel(schema.y_label or ("P(X = k)" if discrete else "f(x)"), fontsize=11)
    if schema.show_grid:
        ax.grid(True, color=GRID_COLOR, linewidth=0.7, linestyle="--", alpha=0.7)
        ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_title(schema.title or dist.replace("_", " ").title() + " distribution",
                 fontsize=13, fontweight="bold")

    fig.tight_layout(pad=0.8)
    return _fig_to_svg(fig)


# ══════════════════════════════════════════════════════════════════════════════
# Extension set 3: piecewise_graph, circle_theorem, similar_triangles,
# geometric_construction, solid_of_revolution, graph_transformation, box_plot.
# ══════════════════════════════════════════════════════════════════════════════

# ── 1. Piecewise Graph (continuity / differentiability) ───────────────────────

_PW_CONT_TOL = 1e-6
_PW_KIND_TEXT = {
    "continuous": "continuous",
    "jump": "jump discontinuity",
    "removable": "removable discontinuity",
}


def _pw_limit(expr_str: str, x0: float) -> float:
    """One-sided value of a branch at x0. Each branch is an elementary, continuous function on
    its own domain, so the limit as x→x0 ALONG that branch is the branch evaluated at x0."""
    return float(_safe_eval(expr_str, np.array([float(x0)]))[0])


def _pw_value_at(pieces, x: float) -> Optional[float]:
    """f(x): the value from whichever branch actually owns x (respecting the closed endpoints)."""
    for p in pieces:
        lo, hi = p.domain
        if lo - _PW_CONT_TOL < x < hi + _PW_CONT_TOL:
            on_lo = abs(x - lo) <= _PW_CONT_TOL
            on_hi = abs(x - hi) <= _PW_CONT_TOL
            if on_lo and not p.closed_left:
                continue
            if on_hi and not p.closed_right:
                continue
            return _pw_limit(p.expression, x)
    return None


def piecewise_continuity(pieces) -> List[Dict[str, Any]]:
    """Classify every interior boundary shared by two consecutive branches.

    For each boundary b (where one branch ends and the next begins) returns
      {x, left_limit, right_limit, value, kind}
    with kind ∈ {'continuous', 'jump', 'removable'}. The two one-sided limits are COMPUTED from
    the branch expressions with parse_safe and compared — nothing is taken from the params.
      • left ≠ right                        → jump
      • left = right but f(b) differs/hole  → removable
      • left = right = f(b)                 → continuous
    """
    ordered = sorted(pieces, key=lambda p: p.domain[0])
    out: List[Dict[str, Any]] = []
    for left, right in zip(ordered, ordered[1:]):
        b = right.domain[0]
        if abs(left.domain[1] - b) > _PW_CONT_TOL:
            continue    # a genuine gap between the branches, not a shared boundary
        ll = _pw_limit(left.expression, b)
        rl = _pw_limit(right.expression, b)
        if right.closed_left:
            value: Optional[float] = rl
        elif left.closed_right:
            value = ll
        else:
            value = None    # a hole: neither branch includes b
        if abs(ll - rl) > _PW_CONT_TOL:
            kind = "jump"
        elif value is None or abs(value - ll) > _PW_CONT_TOL:
            kind = "removable"
        else:
            kind = "continuous"
        out.append({"x": float(b), "left_limit": ll, "right_limit": rl,
                    "value": value, "kind": kind})
    return out


def _pw_marker(ax, x: float, y: float, closed: bool) -> None:
    """● for an included endpoint, ○ for an excluded one — the whole point of these figures."""
    ax.plot(x, y, "o", color="black",
            markerfacecolor="black" if closed else "white",
            markersize=8, markeredgewidth=1.6, zorder=7)


def render_piecewise_graph(data: Dict[str, Any], canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = PiecewiseGraphSchema(**data)

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))

    x_lo = min(p.domain[0] for p in schema.pieces)
    x_hi = max(p.domain[1] for p in schema.pieces)
    all_y: List[float] = []

    for piece in schema.pieces:
        lo, hi = piece.domain
        xs = np.linspace(lo, hi, 400)
        ys = _safe_eval(piece.expression, xs)
        ys = np.where(np.abs(ys) > 1e4, np.nan, ys)
        ax.plot(xs, ys, "-", color=PLOT_COLOR, linewidth=2.3, zorder=3)
        all_y.extend(ys[~np.isnan(ys)].tolist())

    if schema.show_open_closed_points:
        for piece in schema.pieces:
            lo, hi = piece.domain
            ylo, yhi = _pw_limit(piece.expression, lo), _pw_limit(piece.expression, hi)
            _pw_marker(ax, lo, ylo, piece.closed_left)
            _pw_marker(ax, hi, yhi, piece.closed_right)
            all_y.extend([ylo, yhi])

    analysis = piecewise_continuity(schema.pieces) if schema.show_continuity else []
    notes: List[str] = []
    for a in analysis:
        b = a["x"]
        ax.axvline(b, color="#7F8C8D", linestyle=":", linewidth=0.9, zorder=1)
        if a["kind"] == "jump":
            notes.append(f"x = {b:g}: {_PW_KIND_TEXT['jump']} "
                         f"(left {a['left_limit']:g}, right {a['right_limit']:g})")
        elif a["kind"] == "removable":
            notes.append(f"x = {b:g}: removable discontinuity (limit = {a['left_limit']:g})")
        else:
            notes.append(f"x = {b:g}: continuous")

    for cx in schema.check_points:
        val = _pw_value_at(schema.pieces, cx)
        if val is not None:
            ax.plot(cx, val, "o", color="#C0392B", markersize=6, zorder=6)
            ax.annotate(f"({cx:g}, {val:g})", (cx, val), textcoords="offset points",
                        xytext=(7, 8), fontsize=9, color="#C0392B", zorder=8)
            all_y.append(val)

    y_range = None
    if all_y:
        lo, hi = min(all_y), max(all_y)
        margin = max((hi - lo) * 0.15, 0.5)
        y_range = (lo - margin, hi + margin)

    _setup_axes(ax, (x_lo, x_hi), y_range, schema.x_label, schema.y_label,
                schema.grid, schema.title)

    if notes:
        ax.text(0.015, 0.98, "\n".join(notes), transform=ax.transAxes, fontsize=9.5,
                va="top", ha="left", zorder=9,
                bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#34495E", alpha=0.92))

    fig.tight_layout(pad=0.8)
    return _fig_to_svg(fig)


# ── 2. Circle Theorem ─────────────────────────────────────────────────────────

_CT_R = 2.5          # display radius
_CT_CHORD = "#1B4F72"
_CT_ANGLE = "#8E44AD"
_CT_ACCENT = "#C0392B"


def _ct_pt(theta_deg: float, r: float = _CT_R, c: Tuple[float, float] = (0.0, 0.0)):
    t = math.radians(theta_deg)
    return (c[0] + r * math.cos(t), c[1] + r * math.sin(t))


def _angle_at(vertex, p1, p2) -> float:
    """Unsigned angle p1–vertex–p2 in degrees."""
    v1 = (p1[0] - vertex[0], p1[1] - vertex[1])
    v2 = (p2[0] - vertex[0], p2[1] - vertex[1])
    n1, n2 = math.hypot(*v1), math.hypot(*v2)
    if n1 < 1e-12 or n2 < 1e-12:
        return 0.0
    cos_a = (v1[0] * v2[0] + v1[1] * v2[1]) / (n1 * n2)
    return math.degrees(math.acos(max(-1.0, min(1.0, cos_a))))


def circle_inscribed_central(a_deg: float, b_deg: float, p_deg: float) -> Dict[str, Any]:
    """A and B on a circle subtend an inscribed angle at P and a central angle at O.
    Both are COMPUTED from the geometry and, by the inscribed-angle theorem, central = 2·inscribed
    for the arc AB not containing P."""
    A, B, P, O = _ct_pt(a_deg), _ct_pt(b_deg), _ct_pt(p_deg), (0.0, 0.0)
    inscribed = _angle_at(P, A, B)
    d = (b_deg - a_deg) % 360.0
    p_rel = (p_deg - a_deg) % 360.0
    central = (360.0 - d) if p_rel < d else d
    return {"inscribed": inscribed, "central": central, "A": A, "B": B, "P": P, "O": O}


def _draw_angle_arc(ax, vertex, p1, p2, radius, color, label=None, label_r=None):
    """Arc marking the interior (< 180°) angle p1–vertex–p2, optionally labelled."""
    a1 = math.degrees(math.atan2(p1[1] - vertex[1], p1[0] - vertex[0]))
    a2 = math.degrees(math.atan2(p2[1] - vertex[1], p2[0] - vertex[0]))
    diff = (a2 - a1) % 360.0
    if diff > 180.0:
        a1, a2, diff = a2, a1, 360.0 - diff
    ax.add_patch(Arc(vertex, 2 * radius, 2 * radius, angle=0,
                     theta1=a1, theta2=a1 + diff, color=color, linewidth=1.5, zorder=6))
    if label:
        mid = math.radians(a1 + diff / 2)
        lr = label_r if label_r is not None else radius * 1.5
        ax.text(vertex[0] + lr * math.cos(mid), vertex[1] + lr * math.sin(mid), label,
                color=color, fontsize=10, ha="center", va="center", zorder=9,
                bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none", alpha=0.88))


def _seg_intersection(p1, p2, p3, p4):
    """Intersection of the lines through p1p2 and p3p4, or None if parallel."""
    x1, y1 = p1; x2, y2 = p2; x3, y3 = p3; x4, y4 = p4
    den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(den) < 1e-12:
        return None
    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / den
    return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))


def _ct_label_point(ax, pt, name, out=0.28):
    """Letter a point just outside the circle, radially."""
    n = math.hypot(pt[0], pt[1]) or 1.0
    ax.plot(*pt, "ko", markersize=4, zorder=6)
    ax.text(pt[0] + pt[0] / n * out, pt[1] + pt[1] / n * out, name,
            fontsize=12, fontweight="bold", ha="center", va="center", zorder=8)


_CT_DEFAULT_ANGLES = {
    "angle_at_centre": [150.0, 30.0, 265.0],
    "angle_in_semicircle": [180.0, 0.0, 65.0],
    "cyclic_quadrilateral": [65.0, 130.0, 215.0, 315.0],
    "tangent_radius": [55.0],
    "alternate_segment": [270.0, 25.0, 140.0],
    "equal_chords": [140.0, 40.0, 320.0, 220.0],
    "intersecting_chords": [150.0, 350.0, 60.0, 250.0],
}


def render_circle_theorem(data: Dict[str, Any], canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = CircleTheoremSchema(**data)
    ang = list(schema.point_angles) or list(_CT_DEFAULT_ANGLES[schema.theorem])

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))
    ax.set_aspect("equal")
    ax.axis("off")

    O = (0.0, 0.0)
    ax.add_patch(plt.Circle(O, _CT_R, fill=False, edgecolor="black", linewidth=2, zorder=2))
    ax.plot(*O, "ko", markersize=4, zorder=5)
    ax.text(-0.18, -0.18, schema.center_label, fontsize=12, fontweight="bold", zorder=6)

    th = schema.theorem
    notes: List[str] = []

    if th == "angle_at_centre":
        res = circle_inscribed_central(ang[0], ang[1], ang[2])
        A, B, P = res["A"], res["B"], res["P"]
        for seg in ((O, A), (O, B), (P, A), (P, B)):
            ax.plot([seg[0][0], seg[1][0]], [seg[0][1], seg[1][1]],
                    color=_CT_CHORD, linewidth=1.7, zorder=4)
        _ct_label_point(ax, A, "A"); _ct_label_point(ax, B, "B"); _ct_label_point(ax, P, "P")
        c, ins = res["central"], res["inscribed"]
        _draw_angle_arc(ax, O, A, B, 0.6, _CT_ACCENT,
                        f"{c:g}°" if schema.show_values else None)
        _draw_angle_arc(ax, P, A, B, 0.55, _CT_ANGLE,
                        f"{ins:g}°" if schema.show_values else None)
        notes.append(f"Angle at centre = 2 × angle at circumference:  {c:g}° = 2 × {ins:g}°")

    elif th == "angle_in_semicircle":
        A, B, P = _ct_pt(ang[0]), _ct_pt(ang[1]), _ct_pt(ang[2])
        ax.plot([A[0], B[0]], [A[1], B[1]], color=_CT_CHORD, linewidth=1.7, zorder=4)  # diameter
        ax.plot([P[0], A[0]], [P[1], A[1]], color=_CT_CHORD, linewidth=1.7, zorder=4)
        ax.plot([P[0], B[0]], [P[1], B[1]], color=_CT_CHORD, linewidth=1.7, zorder=4)
        _ct_label_point(ax, A, "A"); _ct_label_point(ax, B, "B"); _ct_label_point(ax, P, "P")
        ang_p = _angle_at(P, A, B)
        _ct_right_angle_box(ax, P, A, B, 0.32)   # the box is the right-angle mark
        if schema.show_values:
            ax.annotate(f"{ang_p:g}°", P, textcoords="offset points", xytext=(0, -26),
                        fontsize=10, color=_CT_ANGLE, ha="center", zorder=9)
        notes.append(f"Angle in a semicircle is a right angle:  angle APB = {ang_p:g}°")

    elif th == "cyclic_quadrilateral":
        pts = [_ct_pt(a) for a in ang[:4]]
        names = ["A", "B", "C", "D"]
        for i in range(4):
            j = (i + 1) % 4
            ax.plot([pts[i][0], pts[j][0]], [pts[i][1], pts[j][1]],
                    color=_CT_CHORD, linewidth=1.7, zorder=4)
        interior = []
        for i in range(4):
            prev_, next_ = pts[(i - 1) % 4], pts[(i + 1) % 4]
            a = _angle_at(pts[i], prev_, next_)
            interior.append(a)
            _draw_angle_arc(ax, pts[i], prev_, next_, 0.45, _CT_ANGLE,
                            f"{a:g}°" if schema.show_values else None)
            _ct_label_point(ax, pts[i], names[i])
        notes.append(f"Opposite angles are supplementary:  "
                     f"A + C = {interior[0]:g}° + {interior[2]:g}° = {interior[0] + interior[2]:g}°")
        notes.append(f"B + D = {interior[1]:g}° + {interior[3]:g}° = {interior[1] + interior[3]:g}°")

    elif th == "tangent_radius":
        T = _ct_pt(ang[0])
        ax.plot([O[0], T[0]], [O[1], T[1]], color=_CT_CHORD, linewidth=1.7, zorder=4)  # radius
        # Tangent perpendicular to OT at T
        tdir = (-T[1], T[0])
        n = math.hypot(*tdir)
        tdir = (tdir[0] / n, tdir[1] / n)
        L = _CT_R * 1.15
        ax.plot([T[0] - tdir[0] * L, T[0] + tdir[0] * L],
                [T[1] - tdir[1] * L, T[1] + tdir[1] * L],
                color=_CT_ACCENT, linewidth=1.7, zorder=4)
        _ct_label_point(ax, T, "T")
        _ct_right_angle_box(ax, T, O, (T[0] + tdir[0], T[1] + tdir[1]), 0.32)
        ax.text((O[0] + T[0]) / 2 + 0.12, (O[1] + T[1]) / 2, "r", fontsize=11,
                style="italic", zorder=8)
        notes.append("Tangent is perpendicular to the radius at the point of contact:  "
                     "angle OTP = 90°")

    elif th == "alternate_segment":
        T, A, B = _ct_pt(ang[0]), _ct_pt(ang[1]), _ct_pt(ang[2])
        tdir = (-T[1], T[0])
        n = math.hypot(*tdir); tdir = (tdir[0] / n, tdir[1] / n)
        L = _CT_R * 1.05
        ax.plot([T[0] - tdir[0] * L, T[0] + tdir[0] * L],
                [T[1] - tdir[1] * L, T[1] + tdir[1] * L],
                color=_CT_ACCENT, linewidth=1.7, zorder=4)          # tangent at T
        ax.plot([T[0], A[0]], [T[1], A[1]], color=_CT_CHORD, linewidth=1.7, zorder=4)  # chord TA
        ax.plot([A[0], B[0]], [A[1], B[1]], color=_CT_CHORD, linewidth=1.5, zorder=4)
        ax.plot([B[0], T[0]], [B[1], T[1]], color=_CT_CHORD, linewidth=1.5, zorder=4)
        _ct_label_point(ax, T, "T"); _ct_label_point(ax, A, "A"); _ct_label_point(ax, B, "B")
        inscribed = _angle_at(B, A, T)   # angle in the alternate segment
        # tangent–chord angle on the side of the alternate segment (equals the inscribed angle)
        tang_end = (T[0] - tdir[0] * L, T[1] - tdir[1] * L)
        tc = _angle_at(T, tang_end, A)
        tc = min(tc, 180.0 - tc) if abs(tc - inscribed) > abs((180 - tc) - inscribed) else tc
        _draw_angle_arc(ax, T, tang_end, A, 0.5, _CT_ANGLE,
                        f"{tc:g}°" if schema.show_values else None)
        _draw_angle_arc(ax, B, A, T, 0.5, _CT_ANGLE,
                        f"{inscribed:g}°" if schema.show_values else None)
        notes.append(f"Alternate segment: tangent-chord angle = angle in the alternate segment:  "
                     f"{tc:g}° = {inscribed:g}°")

    elif th == "equal_chords":
        c1 = (_ct_pt(ang[0]), _ct_pt(ang[1]))
        c2 = (_ct_pt(ang[2]), _ct_pt(ang[3]))
        for (P, Q), nm in ((c1, ("A", "B")), (c2, ("C", "D"))):
            ax.plot([P[0], Q[0]], [P[1], Q[1]], color=_CT_CHORD, linewidth=1.8, zorder=4)
            mid = ((P[0] + Q[0]) / 2, (P[1] + Q[1]) / 2)
            ax.plot([O[0], mid[0]], [O[1], mid[1]], color=_CT_ACCENT,
                    linewidth=1.3, linestyle="--", zorder=4)
            _ct_right_angle_box(ax, mid, O, P, 0.22)
            dist = math.hypot(mid[0], mid[1])
            ax.annotate(f"{dist:.2f}", mid, textcoords="offset points", xytext=(6, 6),
                        fontsize=9, color=_CT_ACCENT, zorder=8)
            _ct_label_point(ax, P, nm[0]); _ct_label_point(ax, Q, nm[1])
        len1 = math.hypot(c1[0][0] - c1[1][0], c1[0][1] - c1[1][1])
        len2 = math.hypot(c2[0][0] - c2[1][0], c2[0][1] - c2[1][1])
        notes.append(f"Equal chords are equidistant from the centre:  "
                     f"AB = {len1:.2f} = CD = {len2:.2f}")

    elif th == "intersecting_chords":
        A, B, C, D = (_ct_pt(a) for a in ang[:4])
        ax.plot([A[0], B[0]], [A[1], B[1]], color=_CT_CHORD, linewidth=1.7, zorder=4)
        ax.plot([C[0], D[0]], [C[1], D[1]], color=_CT_CHORD, linewidth=1.7, zorder=4)
        X = _seg_intersection(A, B, C, D)
        _ct_label_point(ax, A, "A"); _ct_label_point(ax, B, "B")
        _ct_label_point(ax, C, "C"); _ct_label_point(ax, D, "D")
        if X is not None:
            ax.plot(*X, "o", color=_CT_ACCENT, markersize=6, zorder=7)
            ax.annotate("X", X, textcoords="offset points", xytext=(6, -12),
                        fontsize=11, fontweight="bold", color=_CT_ACCENT, zorder=8)
            ax_ = math.hypot(A[0] - X[0], A[1] - X[1]) * math.hypot(B[0] - X[0], B[1] - X[1])
            cx_ = math.hypot(C[0] - X[0], C[1] - X[1]) * math.hypot(D[0] - X[0], D[1] - X[1])
            notes.append(f"Intersecting chords:  AX·XB = {ax_:.2f} = CX·XD = {cx_:.2f}")

    if schema.show_values and notes:
        ax.text(0.5, -0.02, "\n".join(notes), transform=ax.transAxes, fontsize=10,
                va="top", ha="center", zorder=9,
                bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#34495E", alpha=0.92))

    lim = _CT_R * 1.55
    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim * 1.12, lim)
    if schema.title:
        ax.set_title(schema.title, fontsize=13, fontweight="bold", pad=8)
    fig.tight_layout(pad=0.6)
    return _fig_to_svg(fig)


def _ct_right_angle_box(ax, corner, p1, p2, size):
    """Right-angle square at `corner` between the directions to p1 and p2."""
    def unit(p):
        d = (p[0] - corner[0], p[1] - corner[1])
        n = math.hypot(*d) or 1.0
        return (d[0] / n, d[1] / n)
    u1, u2 = unit(p1), unit(p2)
    a = (corner[0] + u1[0] * size, corner[1] + u1[1] * size)
    c = (corner[0] + u2[0] * size, corner[1] + u2[1] * size)
    b = (a[0] + u2[0] * size, a[1] + u2[1] * size)
    ax.plot([a[0], b[0], c[0]], [a[1], b[1], c[1]], color="black", linewidth=1.1, zorder=7)


# ── 3. Similar Triangles ──────────────────────────────────────────────────────

_ST_FILL = "#AED6F1"


def _st_lerp(P, Q, t):
    return (P[0] + t * (Q[0] - P[0]), P[1] + t * (Q[1] - P[1]))


def _st_tick(ax, P, Q, count=1, color="black"):
    """Small tick(s) across the midpoint of PQ marking equal/parallel segments."""
    mx, my = (P[0] + Q[0]) / 2, (P[1] + Q[1]) / 2
    dx, dy = Q[0] - P[0], Q[1] - P[1]
    n = math.hypot(dx, dy) or 1.0
    ux, uy = dx / n, dy / n          # along
    nx, ny = -uy, ux                 # across
    s = 0.12
    for k in range(count):
        off = (k - (count - 1) / 2) * 0.10
        cx, cy = mx + ux * off, my + uy * off
        ax.plot([cx - nx * s, cx + nx * s], [cy - ny * s, cy + ny * s],
                color=color, linewidth=1.3, zorder=6)


def bpt_ratios(A, B, C, t: float) -> Dict[str, Any]:
    """D on AB and E on AC with AD/AB = AE/AC = t give a line DE ∥ BC. Returns the points and the
    equal ratio AD/DB = AE/EC = t/(1−t), all COMPUTED from the coordinates."""
    D = _st_lerp(A, B, t)
    E = _st_lerp(A, C, t)
    AD = math.hypot(D[0] - A[0], D[1] - A[1])
    DB = math.hypot(B[0] - D[0], B[1] - D[1])
    AE = math.hypot(E[0] - A[0], E[1] - A[1])
    EC = math.hypot(C[0] - E[0], C[1] - E[1])
    return {"D": D, "E": E, "AD": AD, "DB": DB, "AE": AE, "EC": EC,
            "ratio_ab": AD / DB, "ratio_ac": AE / EC}


def render_similar_triangles(data: Dict[str, Any], canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = SimilarTrianglesSchema(**data)
    A, B, C = tuple(schema.A), tuple(schema.B), tuple(schema.C)
    cfg = schema.configuration

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))
    ax.set_aspect("equal")
    ax.axis("off")
    notes: List[str] = []

    def draw_tri(p, q, r, lw=2.0):
        ax.add_patch(plt.Polygon([p, q, r], fill=False, edgecolor="black", linewidth=lw))

    def label_vertex(pt, name, ref):
        dx, dy = pt[0] - ref[0], pt[1] - ref[1]
        n = math.hypot(dx, dy) or 1.0
        ax.text(pt[0] + dx / n * 0.35, pt[1] + dy / n * 0.35, name,
                fontsize=12, fontweight="bold", ha="center", va="center")

    if cfg in ("basic_proportionality", "midpoint_theorem"):
        t = 0.5 if cfg == "midpoint_theorem" else schema.division_ratio
        r = bpt_ratios(A, B, C, t)
        D, E = r["D"], r["E"]
        centroid = ((A[0] + B[0] + C[0]) / 3, (A[1] + B[1] + C[1]) / 3)
        draw_tri(A, B, C)
        ax.plot([D[0], E[0]], [D[1], E[1]], color=_CT_ACCENT, linewidth=2.0, zorder=4)
        for pt, nm in ((A, "A"), (B, "B"), (C, "C")):
            label_vertex(pt, nm, centroid)
        ax.annotate("D", D, textcoords="offset points", xytext=(-12, 0), fontsize=11,
                    fontweight="bold")
        ax.annotate("E", E, textcoords="offset points", xytext=(8, 0), fontsize=11,
                    fontweight="bold")
        if schema.show_parallel_marks:
            _st_tick(ax, D, E, 2, _CT_ACCENT)
            _st_tick(ax, B, C, 2, _CT_ACCENT)
        if schema.show_angle_arcs:
            _draw_angle_arc(ax, B, A, C, 0.5, _CT_ANGLE)
            _draw_angle_arc(ax, D, A, E, 0.4, _CT_ANGLE)
        if cfg == "midpoint_theorem":
            de = math.hypot(E[0] - D[0], E[1] - D[1])
            bc = math.hypot(C[0] - B[0], C[1] - B[1])
            _st_tick(ax, A, D, 1); _st_tick(ax, D, B, 1)
            _st_tick(ax, A, E, 2); _st_tick(ax, E, C, 2)
            notes.append(f"Midpoint theorem: DE || BC and DE = ½BC  "
                         f"({de:.2f} = ½ × {bc:.2f})")
        else:
            notes.append(f"Basic proportionality (Thales): DE || BC, so "
                         f"AD/DB = AE/EC = {r['ratio_ab']:.3g}")

    elif cfg == "aa_similarity":
        # Two triangles sharing two equal angles → similar. Small one is the large one scaled.
        centroid = ((A[0] + B[0] + C[0]) / 3, (A[1] + B[1] + C[1]) / 3)
        draw_tri(A, B, C)
        k = 0.55
        A2 = (A[0] + 5.0, A[1])
        B2 = (A2[0] + (B[0] - A[0]) * k, A2[1] + (B[1] - A[1]) * k)
        C2 = (A2[0] + (C[0] - A[0]) * k, A2[1] + (C[1] - A[1]) * k)
        centroid2 = ((A2[0] + B2[0] + C2[0]) / 3, (A2[1] + B2[1] + C2[1]) / 3)
        draw_tri(A2, B2, C2)
        for pt, nm in ((A, "A"), (B, "B"), (C, "C")):
            label_vertex(pt, nm, centroid)
        for pt, nm in ((A2, "P"), (B2, "Q"), (C2, "R")):
            label_vertex(pt, nm, centroid2)
        if schema.show_angle_arcs:
            ang_a = _angle_at(A, B, C)
            ang_b = _angle_at(B, A, C)
            _draw_angle_arc(ax, A, B, C, 0.45, _CT_ANGLE)
            _draw_angle_arc(ax, A2, B2, C2, 0.30, _CT_ANGLE)
            _draw_angle_arc(ax, B, A, C, 0.45, _CT_ACCENT)
            _draw_angle_arc(ax, B2, A2, C2, 0.30, _CT_ACCENT)
            notes.append(f"AA similarity: angle A = angle P = {ang_a:g}°, "
                         f"angle B = angle Q = {ang_b:g}°, so triangle ABC ~ triangle PQR")

    else:  # pythagoras_geometric
        # Right triangle with a square drawn outward on each side; areas add.
        A = (0.0, 3.0); B = (0.0, 0.0); C = (4.0, 0.0)   # right angle at B, 3-4-5
        centroid = ((A[0] + B[0] + C[0]) / 3, (A[1] + B[1] + C[1]) / 3)
        draw_tri(A, B, C, lw=2.2)
        _ct_right_angle_box(ax, B, A, C, 0.4)
        for pt, nm in ((A, "A"), (B, "B"), (C, "C")):
            label_vertex(pt, nm, centroid)
        a2 = _st_square(ax, B, C, centroid, "#D5F5E3")   # on BC (base, length a)
        b2 = _st_square(ax, A, B, centroid, "#FADBD8")   # on AB (height, length b)
        c2 = _st_square(ax, C, A, centroid, "#D6EAF8")   # on CA (hypotenuse)
        ax.text(*_st_square_centre(B, C, centroid), f"{a2:g}", ha="center", va="center",
                fontsize=11, zorder=8)
        ax.text(*_st_square_centre(A, B, centroid), f"{b2:g}", ha="center", va="center",
                fontsize=11, zorder=8)
        ax.text(*_st_square_centre(C, A, centroid), f"{c2:g}", ha="center", va="center",
                fontsize=11, zorder=8)
        notes.append(f"Pythagoras: a² + b² = c²:  {a2:g} + {b2:g} = {c2:g}")

    xs = [A[0], B[0], C[0]]
    ys = [A[1], B[1], C[1]]
    if cfg == "aa_similarity":
        xs += [A[0] + 5 + (C[0] - A[0]) * 0.55 + 1]
    m = 2.2
    ax.set_xlim(min(xs) - m, max(xs) + m)
    ax.set_ylim(min(ys) - m * 1.4, max(ys) + m)
    if schema.show_ratios and notes:
        ax.text(0.5, 0.005, "\n".join(notes), transform=ax.transAxes, fontsize=10,
                va="bottom", ha="center", zorder=9,
                bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#34495E", alpha=0.92))
    if schema.title:
        ax.set_title(schema.title, fontsize=13, fontweight="bold", pad=8)
    fig.tight_layout(pad=0.6)
    return _fig_to_svg(fig)


def _st_square_corners(P, Q, centroid):
    dx, dy = Q[0] - P[0], Q[1] - P[1]
    nx, ny = -dy, dx
    mx, my = (P[0] + Q[0]) / 2, (P[1] + Q[1]) / 2
    if nx * (mx - centroid[0]) + ny * (my - centroid[1]) < 0:
        nx, ny = -nx, -ny
    R = (Q[0] + nx, Q[1] + ny)
    S = (P[0] + nx, P[1] + ny)
    return [P, Q, R, S]


def _st_square(ax, P, Q, centroid, color) -> float:
    """Draw a square outward on side PQ; return its area."""
    corners = _st_square_corners(P, Q, centroid)
    ax.add_patch(plt.Polygon(corners, closed=True, facecolor=color, edgecolor="black",
                             linewidth=1.4, alpha=0.7, zorder=2))
    side = math.hypot(Q[0] - P[0], Q[1] - P[1])
    return round(side * side, 6)


def _st_square_centre(P, Q, centroid):
    corners = _st_square_corners(P, Q, centroid)
    return (sum(c[0] for c in corners) / 4, sum(c[1] for c in corners) / 4)


# ── 4. Geometric Construction (ruler-and-compass) ─────────────────────────────

_GC_LINE = dict(color="black", linewidth=1.6, zorder=4)
_GC_ARC = dict(color="#C0392B", linewidth=1.2, zorder=3)     # the compass marks
_GC_AUX = dict(color="#7F8C8D", linewidth=1.0, linestyle="--", zorder=3)


def _circle_circle_intersect(c1, r1, c2, r2):
    x1, y1 = c1; x2, y2 = c2
    dx, dy = x2 - x1, y2 - y1
    d = math.hypot(dx, dy)
    if d < 1e-12 or d > r1 + r2 + 1e-9 or d < abs(r1 - r2) - 1e-9:
        return None
    a = (r1 * r1 - r2 * r2 + d * d) / (2 * d)
    h = math.sqrt(max(0.0, r1 * r1 - a * a))
    xm, ym = x1 + a * dx / d, y1 + a * dy / d
    return [(xm - h * dy / d, ym + h * dx / d), (xm + h * dy / d, ym - h * dx / d)]


def _gc_arc(ax, centre, radius, a1, a2):
    ax.add_patch(Arc(centre, 2 * radius, 2 * radius, angle=0, theta1=a1, theta2=a2, **_GC_ARC))


def render_geometric_construction(data: Dict[str, Any], canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = GeometricConstructionSchema(**data)
    c = schema.construction

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))
    ax.set_aspect("equal")
    ax.axis("off")
    caption = ""

    def dot(p, name=None, off=(6, 6)):
        ax.plot(*p, "ko", markersize=4, zorder=6)
        if name and schema.show_labels:
            ax.annotate(name, p, textcoords="offset points", xytext=off,
                        fontsize=11, fontweight="bold", zorder=7)

    if c == "angle_bisector":
        V = (0.0, 0.0)
        L = 4.0
        arm1 = (L, 0.0)
        arm2 = (L * math.cos(math.radians(schema.angle)), L * math.sin(math.radians(schema.angle)))
        ax.plot([V[0], arm1[0]], [V[1], arm1[1]], **_GC_LINE)
        ax.plot([V[0], arm2[0]], [V[1], arm2[1]], **_GC_LINE)
        r = 1.6
        P1 = _ct_pt(0, r); P2 = _ct_pt(schema.angle, r)
        if schema.show_construction_arcs:
            _gc_arc(ax, V, r, -5, schema.angle + 5)
            r2 = 1.4
            _gc_arc(ax, P1, r2, 90, 210)
            _gc_arc(ax, P2, r2, schema.angle + 150, schema.angle + 270)
        Q = _circle_circle_intersect(P1, 1.4, P2, 1.4)
        bis_ang = schema.angle / 2
        end = (5.0 * math.cos(math.radians(bis_ang)), 5.0 * math.sin(math.radians(bis_ang)))
        ax.plot([V[0], end[0]], [V[1], end[1]], color="#27AE60", linewidth=1.8,
                linestyle="-", zorder=5)
        dot(V, "O", (-14, -6)); dot(arm1, "A"); dot(arm2, "B", (2, 8))
        caption = f"Bisector of a {schema.angle:g}° angle (each half {schema.angle / 2:g}°)"

    elif c == "perpendicular_bisector":
        half = schema.segment_length / 2
        A = (-half, 0.0); B = (half, 0.0)
        ax.plot([A[0], B[0]], [A[1], B[1]], **_GC_LINE)
        r = schema.segment_length * 0.7
        if schema.show_construction_arcs:
            _gc_arc(ax, A, r, -70, 70)
            _gc_arc(ax, B, r, 110, 250)
        inter = _circle_circle_intersect(A, r, B, r)
        if inter:
            U = max(inter, key=lambda p: p[1])
            D = min(inter, key=lambda p: p[1])
            ax.plot([U[0], D[0]], [U[1], D[1]], color="#27AE60", linewidth=1.8, zorder=5)
            dot(U); dot(D)
        dot(A, "A", (-12, -6)); dot(B, "B", (6, -6))
        dot((0.0, 0.0), "M", (0, -14))
        caption = "Perpendicular bisector of AB"

    elif c in ("angle_60", "angle_30"):
        V = (0.0, 0.0)
        L = 4.5
        ax.plot([V[0], L], [V[1], 0.0], **_GC_LINE)             # base ray
        r = 2.0
        P = (r, 0.0)
        if schema.show_construction_arcs:
            _gc_arc(ax, V, r, -3, 95)
            _gc_arc(ax, P, r, 90, 190)
        Q = (r / 2, r * math.sqrt(3) / 2)                       # 60° point
        ax.plot([V[0], Q[0] * 2.0], [V[1], Q[1] * 2.0], **_GC_LINE)
        dot(V, "O", (-14, -6)); dot(P, "A", (2, -14))
        if c == "angle_60":
            _draw_angle_arc(ax, V, (L, 0), Q, 0.7, "#27AE60", "60°")
            caption = "Construct a 60° angle"
        else:
            if schema.show_construction_arcs:
                r3 = 1.5
                P60 = _ct_pt(60, r3)
                P0 = (r3, 0.0)
                _gc_arc(ax, P0, 1.2, 60, 160)
                _gc_arc(ax, P60, 1.2, 200, 300)
            end = (5.0 * math.cos(math.radians(30)), 5.0 * math.sin(math.radians(30)))
            ax.plot([V[0], end[0]], [V[1], end[1]], color="#27AE60", linewidth=1.8, zorder=5)
            _draw_angle_arc(ax, V, (L, 0), end, 0.9, "#27AE60", "30°")
            caption = "Construct a 30° angle (bisect 60°)"

    elif c == "triangle_sss":
        a, b, cc = schema.side_a, schema.side_b, schema.side_c   # BC, CA, AB
        B = (0.0, 0.0); C = (a, 0.0)
        inter = _circle_circle_intersect(B, cc, C, b)
        A = max(inter, key=lambda p: p[1]) if inter else (a / 2, 1.0)
        ax.plot([B[0], C[0]], [B[1], C[1]], **_GC_LINE)
        ax.plot([B[0], A[0]], [B[1], A[1]], **_GC_LINE)
        ax.plot([C[0], A[0]], [C[1], A[1]], **_GC_LINE)
        if schema.show_construction_arcs:
            _gc_arc(ax, B, cc, 20, 110)
            _gc_arc(ax, C, b, 70, 160)
        dot(B, "B", (-12, -8)); dot(C, "C", (6, -8)); dot(A, "A", (0, 8))
        ax.text((B[0] + C[0]) / 2, -0.3, f"a = {a:g}", ha="center", va="top", fontsize=10)
        ax.text((B[0] + A[0]) / 2 - 0.2, (B[1] + A[1]) / 2, f"c = {cc:g}", ha="right",
                fontsize=10)
        ax.text((C[0] + A[0]) / 2 + 0.2, (C[1] + A[1]) / 2, f"b = {b:g}", ha="left",
                fontsize=10)
        caption = f"Construct triangle ABC with SSS ({a:g}, {b:g}, {cc:g})"

    elif c == "tangent_to_circle":
        O = (0.0, 0.0); r = schema.circle_radius
        P = (schema.external_distance, 0.0)
        M = (P[0] / 2, 0.0)
        rm = math.hypot(M[0] - O[0], M[1] - O[1])
        ax.add_patch(plt.Circle(O, r, fill=False, edgecolor="black", linewidth=1.8, zorder=4))
        if schema.show_construction_arcs:
            ax.add_patch(plt.Circle(M, rm, fill=False, **_GC_AUX))
        Ts = _circle_circle_intersect(O, r, M, rm)
        dot(O, "O", (-14, -6)); dot(P, "P", (6, -6)); dot(M, "M", (0, -14))
        if Ts:
            for T, nm in zip(Ts, ("T₁", "T₂")):
                ax.plot([P[0], T[0]], [P[1], T[1]], color="#27AE60", linewidth=1.7, zorder=5)
                ax.plot([O[0], T[0]], [O[1], T[1]], **_GC_AUX)
                _ct_right_angle_box(ax, T, O, P, 0.28)
                dot(T, nm, (6, 6))
            tl = math.hypot(P[0] - Ts[0][0], P[1] - Ts[0][1])
            caption = f"Tangents from an external point (length PT = {tl:.2f})"

    else:  # divide_segment
        L = schema.segment_length
        n = schema.divisions
        A = (0.0, 0.0); B = (L, 0.0)
        ax.plot([A[0], B[0]], [A[1], B[1]], **_GC_LINE)
        ray_ang = 30.0
        step = 0.7
        ray_pts = [(A[0] + step * k * math.cos(math.radians(ray_ang)),
                    A[1] + step * k * math.sin(math.radians(ray_ang))) for k in range(n + 1)]
        ax.plot([A[0], ray_pts[-1][0]], [A[1], ray_pts[-1][1]], **_GC_LINE)
        if schema.show_construction_arcs:
            for k in range(1, n + 1):
                ax.plot(*ray_pts[k], "o", color="#C0392B", markersize=3.5, zorder=5)
        # join last ray point to B, draw parallels back to the segment
        ax.plot([ray_pts[-1][0], B[0]], [ray_pts[-1][1], B[1]], **_GC_AUX)
        div_pts = []
        for k in range(1, n):
            P = ray_pts[k]
            end = (P[0] + (B[0] - ray_pts[-1][0]), P[1] + (B[1] - ray_pts[-1][1]))
            hit = _seg_intersection(P, end, A, B)
            if hit:
                ax.plot([P[0], hit[0]], [P[1], hit[1]], **_GC_AUX)
                ax.plot(*hit, "o", color="#27AE60", markersize=4, zorder=6)
                div_pts.append(hit)
        dot(A, "A", (-12, -6)); dot(B, "B", (6, -6))
        caption = f"Divide a segment into {n} equal parts"

    ax.autoscale_view()
    ax.margins(0.15)
    if schema.show_labels and caption:
        ax.set_title(schema.title or caption, fontsize=12, fontweight="bold", pad=8)
    elif schema.title:
        ax.set_title(schema.title, fontsize=12, fontweight="bold", pad=8)
    fig.tight_layout(pad=0.6)
    return _fig_to_svg(fig)


# ── 5. Solid of Revolution ────────────────────────────────────────────────────

def render_solid_of_revolution(data: Dict[str, Any], canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = SolidOfRevolutionSchema(**data)
    from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

    fig = plt.figure(figsize=(canvas_w / 100, canvas_h / 100))
    ax = fig.add_subplot(111, projection="3d")

    lo, hi = schema.x_range
    xs = np.linspace(lo, hi, 80)
    ys = _safe_eval(schema.expression, xs)
    ys = np.where(np.abs(ys) > 1e4, np.nan, ys)
    theta = np.linspace(0, 2 * np.pi, 60)
    T, Xg = np.meshgrid(theta, xs)
    _, Yg = np.meshgrid(theta, ys)
    x0 = schema.disc_at if schema.disc_at is not None else (lo + hi) / 2
    r0 = float(_safe_eval(schema.expression, np.array([x0]))[0])

    if schema.axis == "x":
        Xs, Ys, Zs = Xg, Yg * np.cos(T), Yg * np.sin(T)
        ax.plot_surface(Xs, Ys, Zs, alpha=0.35, color="#5B9BD5",
                        linewidth=0, antialiased=True, zorder=1)
        ax.plot(xs, ys, np.zeros_like(xs), color="black", linewidth=2.6, zorder=5)  # curve
        ax.plot([lo, hi], [0, 0], [0, 0], color="#C0392B", linewidth=1.6,
                linestyle="--", zorder=5)                                            # axis
        if schema.show_disc:
            ph = np.linspace(0, 2 * np.pi, 60)
            ax.plot(np.full_like(ph, x0), abs(r0) * np.cos(ph), abs(r0) * np.sin(ph),
                    color="#E67E22", linewidth=2.0, zorder=6)
            ax.plot([x0, x0], [0, r0], [0, 0], color="#E67E22", linewidth=1.4, zorder=6)
        axis_note = "Rotated about the x-axis"
    else:
        Xs, Ys, Zs = Xg * np.cos(T), Yg, Xg * np.sin(T)
        ax.plot_surface(Xs, Ys, Zs, alpha=0.35, color="#5B9BD5",
                        linewidth=0, antialiased=True, zorder=1)
        ax.plot(xs, ys, np.zeros_like(xs), color="black", linewidth=2.6, zorder=5)
        ax.plot([0, 0], [float(np.nanmin(ys)), float(np.nanmax(ys))], [0, 0],
                color="#C0392B", linewidth=1.6, linestyle="--", zorder=5)
        if schema.show_disc:
            y0 = float(_safe_eval(schema.expression, np.array([x0]))[0])
            ph = np.linspace(0, 2 * np.pi, 60)
            ax.plot(x0 * np.cos(ph), np.full_like(ph, y0), x0 * np.sin(ph),
                    color="#E67E22", linewidth=2.0, zorder=6)
            ax.plot([0, x0], [y0, y0], [0, 0], color="#E67E22", linewidth=1.4, zorder=6)
        axis_note = "Rotated about the y-axis"

    ax.set_xlabel("x", fontsize=10)
    ax.set_ylabel("y", fontsize=10)
    ax.set_zlabel("z", fontsize=10)
    ax.view_init(elev=22, azim=-58)     # fixed view → deterministic
    ax.text2D(0.02, 0.96, f"y = {schema.expression}", transform=ax.transAxes, fontsize=11)
    ax.text2D(0.02, 0.90, axis_note, transform=ax.transAxes, fontsize=10, color="#C0392B")
    ax.set_title(schema.title or "Solid of revolution", fontsize=13, fontweight="bold")
    fig.tight_layout()
    return _fig_to_svg(fig)


# ── 6. Graph Transformation ───────────────────────────────────────────────────

_GT_PALETTE = ["#C0392B", "#27AE60", "#8E44AD", "#D68910", "#16A085", "#2980B9"]


def _make_base_fn(expr_str: str):
    """A callable y = f(x) built from the base expression via parse_safe (never sympify)."""
    expr = parse_safe(expr_str, ("x",))
    f = lambdify(x_sym, expr, modules=["numpy"])

    def fn(arr):
        arr = np.asarray(arr, dtype=float)
        y = f(arr)
        if np.isscalar(y):
            y = np.full_like(arr, float(y))
        return np.asarray(y, dtype=float)

    return fn


def apply_transformation(base_fn, ttype: str, param: float, xs) -> np.ndarray:
    """Derive the transformed curve from the BASE at sampled xs — the base is evaluated at
    whatever argument the transform needs. No transformed expression is ever taken from params."""
    xs = np.asarray(xs, dtype=float)
    if ttype == "shift_up":
        return base_fn(xs) + param
    if ttype == "shift_down":
        return base_fn(xs) - param
    if ttype == "shift_right":
        return base_fn(xs - param)
    if ttype == "shift_left":
        return base_fn(xs + param)
    if ttype == "scale_vertical":
        return param * base_fn(xs)
    if ttype == "scale_horizontal":
        return base_fn(param * xs)
    if ttype == "reflect_x":
        return -base_fn(xs)
    if ttype == "reflect_y":
        return base_fn(-xs)
    if ttype == "abs_outer":
        return np.abs(base_fn(xs))
    if ttype == "abs_inner":
        return base_fn(np.abs(xs))
    raise ValueError(f"unknown transformation '{ttype}'")


_GT_AUTO_LABEL = {
    "shift_up": lambda p: f"f(x) + {p:g}",
    "shift_down": lambda p: f"f(x) − {p:g}",
    "shift_right": lambda p: f"f(x − {p:g})",
    "shift_left": lambda p: f"f(x + {p:g})",
    "scale_vertical": lambda p: f"{p:g}·f(x)",
    "scale_horizontal": lambda p: f"f({p:g}x)",
    "reflect_x": lambda p: "−f(x)",
    "reflect_y": lambda p: "f(−x)",
    "abs_outer": lambda p: "|f(x)|",
    "abs_inner": lambda p: "f(|x|)",
}


def render_graph_transformation(data: Dict[str, Any], canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = GraphTransformationSchema(**data)
    base_fn = _make_base_fn(schema.base_expression)

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))
    x_lo, x_hi = schema.x_range
    xs = np.linspace(x_lo, x_hi, 1000)

    all_y: List[float] = []

    if schema.show_base:
        yb = base_fn(xs)
        yb = np.where(np.abs(yb) > 1e4, np.nan, yb)
        ax.plot(xs, yb, "-", color="black", linewidth=2.4,
                label=f"f(x) = {schema.base_expression}", zorder=4)
        all_y.extend(yb[~np.isnan(yb)].tolist())

    for i, tr in enumerate(schema.transformations):
        yt = apply_transformation(base_fn, tr.type, tr.param, xs)
        yt = np.where(np.abs(yt) > 1e4, np.nan, yt)
        label = tr.label or _GT_AUTO_LABEL[tr.type](tr.param)
        ax.plot(xs, yt, "--", color=_GT_PALETTE[i % len(_GT_PALETTE)], linewidth=2.0,
                label=label, zorder=5)
        all_y.extend(yt[~np.isnan(yt)].tolist())

    y_range = schema.y_range
    if y_range is None and all_y:
        lo, hi = min(all_y), max(all_y)
        margin = max((hi - lo) * 0.12, 0.5)
        y_range = (lo - margin, hi + margin)

    _setup_axes(ax, (x_lo, x_hi), y_range, "x", "y", schema.grid, schema.title)
    ax.legend(fontsize=10, loc="best", framealpha=0.9)
    fig.tight_layout(pad=0.8)
    return _fig_to_svg(fig)


# ── 7. Box Plot (five-number summary) ─────────────────────────────────────────

def _percentile_linear(sorted_vals: List[float], q: float) -> float:
    """numpy 'linear' (R type-7) percentile: position (n−1)q, linearly interpolated."""
    n = len(sorted_vals)
    if n == 1:
        return float(sorted_vals[0])
    pos = (n - 1) * q
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return float(sorted_vals[lo])
    frac = pos - lo
    return float(sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac)


def five_number_summary(data: List[float]) -> Dict[str, Any]:
    """Quartiles by linear interpolation, and the 1.5·IQR fences and outliers COMPUTED from the
    data. Supplied outlier flags are never trusted — the whiskers reach the most extreme value
    inside the fences, and anything beyond is an outlier."""
    vals = sorted(float(v) for v in data)
    q1 = _percentile_linear(vals, 0.25)
    median = _percentile_linear(vals, 0.5)
    q3 = _percentile_linear(vals, 0.75)
    iqr = q3 - q1
    lo_fence, hi_fence = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    outliers = [v for v in vals if v < lo_fence - 1e-9 or v > hi_fence + 1e-9]
    inliers = [v for v in vals if lo_fence - 1e-9 <= v <= hi_fence + 1e-9]
    return {
        "min": vals[0], "q1": q1, "median": median, "q3": q3, "max": vals[-1],
        "iqr": iqr, "lo_fence": lo_fence, "hi_fence": hi_fence, "outliers": outliers,
        "whisker_lo": min(inliers) if inliers else vals[0],
        "whisker_hi": max(inliers) if inliers else vals[-1],
    }


def _boxplot_summary(ds) -> Dict[str, Any]:
    if ds.data:
        return five_number_summary(ds.data)
    s = ds.summary
    return {
        "min": s["min"], "q1": s["q1"], "median": s["median"], "q3": s["q3"], "max": s["max"],
        "iqr": s["q3"] - s["q1"], "lo_fence": s["min"], "hi_fence": s["max"], "outliers": [],
        "whisker_lo": s["min"], "whisker_hi": s["max"],
    }


def render_box_plot(data: Dict[str, Any], canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = BoxPlotSchema(**data)
    horiz = schema.orientation == "horizontal"

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))
    summaries = [_boxplot_summary(ds) for ds in schema.datasets]
    box_w = 0.5
    palette = ["#AED6F1", "#A9DFBF", "#F5CBA7", "#D7BDE2", "#F9E79F", "#A3E4D7"]

    def draw_box(pos, s, color):
        q1, q3, med = s["q1"], s["q3"], s["median"]
        wlo, whi = s["whisker_lo"], s["whisker_hi"]
        if horiz:
            ax.add_patch(mpatches.Rectangle((q1, pos - box_w / 2), q3 - q1, box_w,
                         facecolor=color, edgecolor="black", linewidth=1.4, zorder=3))
            ax.plot([med, med], [pos - box_w / 2, pos + box_w / 2], color="#C0392B",
                    linewidth=2.0, zorder=4)
            ax.plot([wlo, q1], [pos, pos], color="black", linewidth=1.2, zorder=3)
            ax.plot([q3, whi], [pos, pos], color="black", linewidth=1.2, zorder=3)
            for w in (wlo, whi):
                ax.plot([w, w], [pos - box_w / 4, pos + box_w / 4], color="black",
                        linewidth=1.2, zorder=3)
            if schema.show_outliers:
                for o in s["outliers"]:
                    ax.plot(o, pos, "o", color="#C0392B", markersize=5,
                            markerfacecolor="white", zorder=5)
        else:
            ax.add_patch(mpatches.Rectangle((pos - box_w / 2, q1), box_w, q3 - q1,
                         facecolor=color, edgecolor="black", linewidth=1.4, zorder=3))
            ax.plot([pos - box_w / 2, pos + box_w / 2], [med, med], color="#C0392B",
                    linewidth=2.0, zorder=4)
            ax.plot([pos, pos], [wlo, q1], color="black", linewidth=1.2, zorder=3)
            ax.plot([pos, pos], [q3, whi], color="black", linewidth=1.2, zorder=3)
            for w in (wlo, whi):
                ax.plot([pos - box_w / 4, pos + box_w / 4], [w, w], color="black",
                        linewidth=1.2, zorder=3)
            if schema.show_outliers:
                for o in s["outliers"]:
                    ax.plot(pos, o, "o", color="#C0392B", markersize=5,
                            markerfacecolor="white", zorder=5)

    positions = list(range(1, len(schema.datasets) + 1))
    labels = [ds.label or f"Set {i + 1}" for i, ds in enumerate(schema.datasets)]
    for i, (pos, s) in enumerate(zip(positions, summaries)):
        draw_box(pos, s, palette[i % len(palette)])
        if schema.show_values:
            txt = (f"min {s['min']:g}  Q1 {s['q1']:g}  M {s['median']:g}  "
                   f"Q3 {s['q3']:g}  max {s['max']:g}")
            if horiz:
                ax.annotate(txt, (s["median"], pos + box_w / 2), textcoords="offset points",
                            xytext=(0, 6), fontsize=8, ha="center", zorder=6)
            else:
                ax.annotate(txt, (pos + box_w / 2, s["median"]), textcoords="offset points",
                            xytext=(6, 0), fontsize=8, ha="left", va="center", rotation=0,
                            zorder=6)

    if horiz:
        ax.set_yticks(positions)
        ax.set_yticklabels(labels, fontsize=10)
        ax.set_ylim(0.4, len(positions) + 0.9)
        ax.set_xlabel(schema.x_label or "Value", fontsize=11)
        if schema.grid:
            ax.xaxis.grid(True, color=GRID_COLOR, linewidth=0.7, linestyle="--", alpha=0.7)
    else:
        ax.set_xticks(positions)
        ax.set_xticklabels(labels, fontsize=10)
        ax.set_xlim(0.4, len(positions) + 0.9)
        ax.set_ylabel(schema.y_label or "Value", fontsize=11)
        if schema.grid:
            ax.yaxis.grid(True, color=GRID_COLOR, linewidth=0.7, linestyle="--", alpha=0.7)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_title(schema.title or "Box-and-whisker plot", fontsize=13, fontweight="bold")
    fig.tight_layout(pad=0.8)
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
    "pie_chart": render_pie_chart,
    "line_chart": render_line_chart,
    "solid_3d": render_solid_3d,
    "argand_diagram": render_argand_diagram,
    "linear_programming": render_linear_programming,
    "histogram": render_histogram,
    "probability_tree": render_probability_tree,
    "height_distance": render_height_distance,
    "combined_solid": render_combined_solid,
    "plane_line_3d": render_plane_line_3d,
    "distribution_curve": render_distribution_curve,
    "piecewise_graph": render_piecewise_graph,
    "circle_theorem": render_circle_theorem,
    "similar_triangles": render_similar_triangles,
    "geometric_construction": render_geometric_construction,
    "solid_of_revolution": render_solid_of_revolution,
    "graph_transformation": render_graph_transformation,
    "box_plot": render_box_plot,
    # Shared across physics/chemistry/mathematics — see diagrams/service/shared/xygraph.py.
    "annotated_xy_graph": render_annotated_xy_graph,
}


def render_mathematics(subtype: str, params: Dict[str, Any],
                       canvas_w: int = 800, canvas_h: int = 600) -> str:
    renderer = MATHEMATICS_RENDERERS.get(subtype)
    if not renderer:
        raise ValueError(f"Unknown mathematics subtype: '{subtype}'. "
                         f"Supported: {list(MATHEMATICS_RENDERERS.keys())}")
    return renderer(params, canvas_w=canvas_w, canvas_h=canvas_h)
