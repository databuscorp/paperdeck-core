"""
Generic annotated x-y graph renderer, shared by physics, chemistry and mathematics.

One renderer for the whole tail of "an annotated curve with regions and marked points"
exam figures: stress-strain, heating curve, blackbody spectra, Maxwell-Boltzmann,
radioactive decay, reaction kinetics, Arrhenius, conductivity vs concentration,
population growth, resonance curves.

Everything derivable is COMPUTED here and never trusted from params: a marked point given
only an x has its y evaluated on the curve, an under_curve fill follows the sampled curve
rather than a supplied polygon, and band labels are placed clear of the plotted data.
"""
from __future__ import annotations

import io
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["svg.fonttype"] = "none"      # real <text> nodes in SVG output
matplotlib.rcParams["svg.hashsalt"] = "paperdeck"  # deterministic element ids
import matplotlib.pyplot as plt
import numpy as np

import sympy as sp
from sympy import lambdify, symbols
from sympy.core.function import AppliedUndef
from sympy.parsing.sympy_parser import (
    convert_xor, implicit_multiplication, parse_expr, standard_transformations,
)

from diagrams.schemas.shared import AnnotatedXYGraphSchema, CurveSpec

x_sym = symbols("x")

# implicit_multiplication ("2x" → 2*x) but deliberately NOT the bundled
# implicit_multiplication_application: that pulls in split_symbols, which shreds any
# multi-letter name into a product of single letters. "N0*exp(-k*x)" would become N*0*... = 0
# — a flat zero line silently drawn instead of an error the repair loop could act on.
_TRANSFORMS = standard_transformations + (implicit_multiplication, convert_xor)

# The parse namespace is a whitelist, not sympy's full namespace: unrestricted, "N0" resolves
# to N(0), sympy's evalf function. Any name not listed here becomes a free symbol / undefined
# function and is rejected below.
_ALLOWED_NAMES = (
    "exp", "log", "ln", "sqrt", "Abs", "sign", "floor", "ceiling",
    "sin", "cos", "tan", "asin", "acos", "atan", "atan2",
    "sinh", "cosh", "tanh", "erf", "Min", "Max", "factorial",
)
_GLOBAL_DICT = {name: getattr(sp, name) for name in _ALLOWED_NAMES}
_GLOBAL_DICT.update({
    "pi": sp.pi, "E": sp.E,
    # the parser's own transformations emit these constructors
    "Symbol": sp.Symbol, "Integer": sp.Integer, "Float": sp.Float, "Rational": sp.Rational,
    "Number": sp.Number, "Function": sp.Function,
})

_SAMPLES = 3000        # dense enough that a Planck / Maxwell peak is not visibly flattened
_FILL_SAMPLES = 600

_LS_MAP = {"solid": "-", "dashed": "--", "dotted": ":", "dashdot": "-."}
_AUTO_LS = ["-", "--", "-.", ":"]

# Distinct in colour and in shape, so the figure survives a black-and-white print.
PALETTE = ["#1f77b4", "#d62728", "#2ca02c", "#9467bd", "#ff7f0e", "#17becf", "#8c564b"]
BAND_PALETTE = ["#93C5FD", "#FCA5A5", "#86EFAC", "#FDE68A", "#C4B5FD", "#A5F3FC"]
GRID_COLOR = "#dddddd"
GUIDE_COLOR = "#555555"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "figure.facecolor": "white",
    "axes.facecolor": "white",
})


def _fig_to_svg(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="svg", bbox_inches="tight", facecolor="white", dpi=100,
                metadata={"Date": None})   # no timestamp → deterministic output
    buf.seek(0)
    svg = buf.getvalue().decode("utf-8")
    plt.close(fig)
    return svg


# ── Safe expression handling ──────────────────────────────────────────────────

def _parse_expression(expr_str: str):
    """Restricted sympy parse — never eval. Only the free symbol x may appear."""
    try:
        expr = parse_expr(expr_str, transformations=_TRANSFORMS,
                          local_dict={"x": x_sym}, global_dict=_GLOBAL_DICT)
    except Exception as e:
        raise ValueError(f"Invalid expression '{expr_str}': {e}")
    unknown_fns = sorted({f.func.__name__ for f in expr.atoms(AppliedUndef)})
    if unknown_fns:
        raise ValueError(
            f"Expression '{expr_str}' calls unknown function(s) {unknown_fns}. "
            f"Supported: {sorted(_ALLOWED_NAMES)}"
        )
    unknown = sorted(str(s) for s in expr.free_symbols - {x_sym})
    if unknown:
        raise ValueError(
            f"Expression '{expr_str}' uses undefined symbol(s) {unknown}; "
            f"the only variable allowed is 'x' — substitute numeric values for constants"
        )
    return expr


def _eval_expression(expr_str: str, x_vals: np.ndarray) -> np.ndarray:
    expr = _parse_expression(expr_str)
    try:
        f = lambdify(x_sym, expr, modules=["numpy"])
        with np.errstate(all="ignore"):
            y = f(x_vals)
    except Exception as e:
        raise ValueError(f"Expression '{expr_str}' could not be evaluated: {e}")

    if np.isscalar(y) or np.ndim(y) == 0:
        y = np.full(x_vals.shape, y)
    y = np.asarray(y)

    if np.iscomplexobj(y):
        if np.all(np.abs(y.imag) < 1e-9):
            y = y.real
        else:
            raise ValueError(
                f"Expression '{expr_str}' is complex-valued over the given x_range "
                f"(e.g. a square root or log of a negative number) — narrow the x_range"
            )
    y = y.astype(float)
    if not np.any(np.isfinite(y)):
        raise ValueError(
            f"Expression '{expr_str}' has no finite values over the given x_range"
        )
    return y


# ── Resolved curves ───────────────────────────────────────────────────────────

class _Curve:
    """A curve after sampling: x/y arrays plus how it should be drawn."""

    def __init__(self, spec: CurveSpec, index: int, x_range: Tuple[float, float],
                 log_x: bool):
        self.expression = spec.expression
        self.label = spec.label
        self.colour = spec.colour or PALETTE[index % len(PALETTE)]
        self.ls = _LS_MAP[spec.line_style] if spec.line_style else _AUTO_LS[index % len(_AUTO_LS)]
        self.lw = spec.line_width
        self.show_marker = spec.show_marker

        if spec.points:
            self.x = np.array([p.x for p in spec.points], dtype=float)
            self.y = np.array([p.y for p in spec.points], dtype=float)
        else:
            lo, hi = spec.x_range or x_range
            if log_x and lo > 0:
                self.x = np.geomspace(lo, hi, _SAMPLES)
            else:
                self.x = np.linspace(lo, hi, _SAMPLES)
            self.y = _eval_expression(spec.expression, self.x)

        order = np.argsort(self.x, kind="stable")
        self._sx = self.x[order]
        self._sy = self.y[order]

    def y_on(self, xs: np.ndarray) -> np.ndarray:
        """The curve's y at arbitrary x — evaluated for an expression, interpolated for a
        point list (which is why the point list is kept x-sorted separately from its
        drawing order)."""
        if self.expression is not None:
            return _eval_expression(self.expression, xs)
        return np.interp(xs, self._sx, self._sy, left=np.nan, right=np.nan)

    def y_at(self, x: float) -> float:
        if self.expression is None and not (self._sx[0] - 1e-9 <= x <= self._sx[-1] + 1e-9):
            raise ValueError(
                f"x = {x:g} lies outside the data range of curve "
                f"'{self.label or '(unlabelled)'}' [{self._sx[0]:g}, {self._sx[-1]:g}] — "
                f"y cannot be derived there"
            )
        val = float(self.y_on(np.array([float(x)], dtype=float))[0])
        if not np.isfinite(val):
            raise ValueError(
                f"Curve '{self.label or '(unlabelled)'}' is not defined at x = {x:g}"
            )
        return val


def _resolve_curve(curves: List[_Curve], ref: Optional[Union[int, str]]) -> _Curve:
    if ref is None:
        return curves[0]
    if isinstance(ref, int) and not isinstance(ref, bool):
        if 0 <= ref < len(curves):
            return curves[ref]
        raise ValueError(f"curve index {ref} out of range (0..{len(curves) - 1})")
    for c in curves:
        if c.label == ref:
            return c
    raise ValueError(
        f"No curve labelled '{ref}'. Available: {[c.label for c in curves]}"
    )


def _data_x_range(schema: AnnotatedXYGraphSchema) -> Tuple[float, float]:
    """x limits must be known before an expression curve can be sampled."""
    if schema.x_range:
        return schema.x_range
    lo: List[float] = []
    hi: List[float] = []
    specs: List[CurveSpec] = list(schema.curves)
    if schema.curve_family:
        specs.extend(schema.curve_family.members)
    for spec in specs:
        if spec.x_range:
            lo.append(spec.x_range[0])
            hi.append(spec.x_range[1])
        elif spec.points:
            lo.append(min(p.x for p in spec.points))
            hi.append(max(p.x for p in spec.points))
    if not lo:
        raise ValueError(
            "x_range is required: no curve supplies points or its own x_range, so the "
            "domain of the expression curve(s) is unknown"
        )
    return min(lo), max(hi)


def _to_frac(y: float, y0: float, y1: float, log_y: bool) -> float:
    """Position of y within the axes, 0 at the bottom and 1 at the top."""
    if log_y:
        if y <= 0 or y0 <= 0 or y1 <= 0:
            return 0.5
        return (np.log10(y) - np.log10(y0)) / (np.log10(y1) - np.log10(y0))
    return (y - y0) / (y1 - y0)


# ── Renderer ──────────────────────────────────────────────────────────────────

def render_annotated_xy_graph(params: Dict[str, Any],
                              canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = AnnotatedXYGraphSchema(**params)

    x_range = _data_x_range(schema)

    curves: List[_Curve] = []
    for spec in schema.curves:
        curves.append(_Curve(spec, len(curves), x_range, schema.log_x))
    if schema.curve_family:
        for spec in schema.curve_family.members:
            curves.append(_Curve(spec, len(curves), x_range, schema.log_x))

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))
    if schema.log_x:
        ax.set_xscale("log")
    if schema.log_y:
        ax.set_yscale("log")

    # ── Limits (fixed up front so bands, droplines and fills can use them) ─────
    x0, x1 = x_range
    if not schema.x_range:
        pad = (x1 - x0) * 0.03
        x0, x1 = x0 - pad, x1 + pad
    if schema.log_x:
        x0 = max(x0, min(c.x[c.x > 0].min() for c in curves if np.any(c.x > 0)) * 0.9)

    if schema.y_range:
        y0, y1 = schema.y_range
    else:
        finite = np.concatenate([c.y[np.isfinite(c.y)] for c in curves])
        extra = [p.y for p in schema.marked_points if p.y is not None]
        extra += [a.value for a in schema.asymptotes if a.orientation == "horizontal"]
        extra += [r.value for r in schema.reference_lines if r.orientation == "horizontal"]
        lo = float(min([finite.min()] + extra))
        hi = float(max([finite.max()] + extra))
        if schema.log_y:
            positive = finite[finite > 0]
            if positive.size == 0:
                raise ValueError("log_y is set but the curve has no positive values")
            y0, y1 = float(positive.min()) / 2.0, hi * 2.5
        else:
            span = hi - lo or max(abs(hi), 1.0)
            # extra headroom: band labels and annotations live near the top of the axes
            y0, y1 = lo - span * 0.10, hi + span * 0.20
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)

    # ── Bands (behind everything) ─────────────────────────────────────────────
    for i, band in enumerate(schema.regions):
        colour = band.colour or BAND_PALETTE[i % len(BAND_PALETTE)]
        ax.axvspan(band.x_from, band.x_to, facecolor=colour, alpha=band.alpha,
                   edgecolor="none", zorder=0)
        if band.show_boundaries:
            for edge in (band.x_from, band.x_to):
                if x0 < edge < x1:
                    ax.axvline(edge, color="#9ca3af", linestyle="--", linewidth=0.9,
                               alpha=0.8, zorder=1)
        if not band.label:
            continue

        mid_x = (max(band.x_from, x0) + min(band.x_to, x1)) / 2
        pos = band.label_position
        if pos == "auto":
            xs = np.linspace(max(band.x_from, x0), min(band.x_to, x1), 60)
            fracs = []
            for c in curves:
                ys = c.y_on(xs)
                ys = ys[np.isfinite(ys)]
                fracs.extend(_to_frac(float(v), y0, y1, schema.log_y) for v in ys)
            if not fracs:
                pos = "top"
            elif max(fracs) <= 0.84:
                pos = "top"
            elif min(fracs) >= 0.16:
                pos = "bottom"
            else:
                pos = "top"
        y_frac = 0.94 if pos == "top" else 0.04
        ax.text(mid_x, y_frac, band.label,
                transform=ax.get_xaxis_transform(), ha="center",
                va="top" if pos == "top" else "bottom",
                fontsize=10, rotation=band.label_rotation, zorder=4,
                bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="none", alpha=0.75))

    # ── Shaded areas ──────────────────────────────────────────────────────────
    for region in schema.shaded_regions:
        if region.under_curve:
            curve = _resolve_curve(curves, region.curve)
            xs = np.linspace(region.x_from, region.x_to, _FILL_SAMPLES)
            ys = curve.y_on(xs)
            base = region.y_from if region.y_from is not None else (y0 if schema.log_y else 0.0)
            ok = np.isfinite(ys)
            if not np.any(ok):
                raise ValueError(
                    f"Shaded region [{region.x_from:g}, {region.x_to:g}] lies outside the "
                    f"curve it is meant to fill under"
                )
            ax.fill_between(xs[ok], base, ys[ok], facecolor=region.colour,
                            alpha=region.alpha, edgecolor="none", zorder=1)
            label_y = float(np.nanmean(ys[ok])) * 0.55 + base * 0.45
        else:
            ry0 = region.y_from if region.y_from is not None else y0
            ry1 = region.y_to if region.y_to is not None else y1
            ax.fill_between([region.x_from, region.x_to], ry0, ry1,
                            facecolor=region.colour, alpha=region.alpha,
                            edgecolor="none", zorder=1)
            label_y = (ry0 + ry1) / 2
        if region.label:
            ax.text((region.x_from + region.x_to) / 2, label_y, region.label,
                    ha="center", va="center", fontsize=10, zorder=4)

    # ── Asymptotes and reference lines ────────────────────────────────────────
    for line in list(schema.asymptotes) + list(schema.reference_lines):
        colour = line.colour or GUIDE_COLOR
        ls = _LS_MAP[line.line_style]
        if line.orientation == "horizontal":
            ax.axhline(line.value, color=colour, linestyle=ls, linewidth=1.2,
                       alpha=0.9, zorder=2)
            if line.label:
                ax.text(0.995, line.value, line.label,
                        transform=ax.get_yaxis_transform(), ha="right", va="bottom",
                        fontsize=9.5, color=colour, zorder=4,
                        bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.75))
        else:
            ax.axvline(line.value, color=colour, linestyle=ls, linewidth=1.2,
                       alpha=0.9, zorder=2)
            if line.label:
                ax.text(line.value, 0.99, line.label,
                        transform=ax.get_xaxis_transform(), ha="left", va="top",
                        fontsize=9.5, color=colour, rotation=90, zorder=4,
                        bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.75))

    # ── Curves ────────────────────────────────────────────────────────────────
    for curve in curves:
        kwargs: Dict[str, Any] = {}
        if curve.show_marker:
            kwargs["marker"] = "o"
            kwargs["markersize"] = 4.5
            if curve.expression is not None:
                kwargs["markevery"] = max(len(curve.x) // 12, 1)
        ax.plot(curve.x, curve.y, curve.ls, color=curve.colour, linewidth=curve.lw,
                label=curve.label, zorder=3, **kwargs)

    # ── Marked points (y derived from the curve when not supplied) ────────────
    for pt in schema.marked_points:
        if pt.y is None:
            if not curves:
                raise ValueError("A marked_point without y needs a curve to derive it from")
            py = _resolve_curve(curves, pt.curve).y_at(pt.x)
        else:
            py = pt.y

        if pt.show_dropline:
            ax.plot([pt.x, pt.x], [y0, py], color=GUIDE_COLOR, linestyle="--",
                    linewidth=0.9, alpha=0.7, zorder=2)
            ax.plot([x0, pt.x], [py, py], color=GUIDE_COLOR, linestyle="--",
                    linewidth=0.9, alpha=0.7, zorder=2)

        if pt.annotation_style == "crosshair":
            ax.plot(pt.x, py, marker="+", color="black", markersize=13,
                    markeredgewidth=1.8, zorder=5)
        else:
            ax.plot(pt.x, py, marker="o", color="black", markersize=6, zorder=5)

        text = pt.label
        if pt.show_coordinates:
            coords = f"({pt.x:.3g}, {py:.3g})"
            text = f"{text} {coords}".strip() if text else coords
        if not text:
            continue
        if pt.annotation_style == "arrow":
            ax.annotate(text, xy=(pt.x, py),
                        xytext=(pt.label_offset[0], pt.label_offset[1]),
                        textcoords="offset points", fontsize=10, zorder=6,
                        arrowprops=dict(arrowstyle="->", color="black", lw=1.0,
                                        shrinkA=0, shrinkB=4),
                        bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.8))
        else:
            ax.annotate(text, xy=(pt.x, py), xytext=pt.label_offset,
                        textcoords="offset points", fontsize=10, zorder=6,
                        bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.8))

    # ── Free annotations ──────────────────────────────────────────────────────
    for ann in schema.annotations:
        if ann.target_x is not None:
            ax.annotate(ann.text, xy=(ann.target_x, ann.target_y), xytext=(ann.x, ann.y),
                        fontsize=ann.fontsize, ha="center", va="center", zorder=6,
                        arrowprops=dict(arrowstyle="->", color="black", lw=1.1,
                                        shrinkA=2, shrinkB=2),
                        bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#cccccc",
                                  alpha=0.9))
        else:
            ax.text(ann.x, ann.y, ann.text, fontsize=ann.fontsize, ha="center",
                    va="center", zorder=6,
                    bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#cccccc",
                              alpha=0.9))

    # ── Frame ─────────────────────────────────────────────────────────────────
    ax.set_xlabel(schema.x_label, fontsize=12)
    ax.set_ylabel(schema.y_label, fontsize=12)
    if schema.title:
        ax.set_title(schema.title, fontsize=13, fontweight="bold", pad=10)
    if schema.show_grid:
        ax.grid(True, color=GRID_COLOR, linewidth=0.7, linestyle="--", alpha=0.7, zorder=0)
        ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("black")
    ax.spines["bottom"].set_color("black")

    if schema.show_legend and any(c.label for c in curves):
        legend = ax.legend(fontsize=10, loc=schema.legend_loc, framealpha=0.9)
        if schema.curve_family and schema.curve_family.name:
            legend.set_title(schema.curve_family.name, prop={"size": 10})

    fig.tight_layout(pad=0.8)
    return _fig_to_svg(fig)
