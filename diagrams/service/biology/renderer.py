"""
Biology Diagram Renderer (NEET-focused).
All diagrams are drawn deterministically with matplotlib.
Covers 9 diagram types across cell biology, genetics, anatomy, and ecology.
"""
from __future__ import annotations

import io
import math
from typing import Any, Dict, List, Optional, Tuple

import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["svg.fonttype"] = "none"   # real <text> nodes, not paths
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import (
    Arc, FancyArrowPatch, FancyBboxPatch, Ellipse, Circle, Rectangle,
    PathPatch,
)
from matplotlib.path import Path
import numpy as np

from diagrams.schemas.biology import (
    CellDiagramSchema, DNAStructureSchema, CellDivisionSchema,
    HeartDiagramSchema, NephronDiagramSchema, NeuronDiagramSchema,
    FoodWebSchema, FoodChainSchema, EcologicalPyramidSchema,
)

# ── Shared palette ────────────────────────────────────────────────────────────
C = {
    "cell_membrane":    "#e53935",
    "cell_wall":        "#388e3c",
    "nucleus":          "#5c35b5",
    "nucleolus":        "#7e57c2",
    "mitochondria":     "#ef6c00",
    "er_rough":         "#6d4c41",
    "er_smooth":        "#a1887f",
    "golgi":            "#f57f17",
    "lysosome":         "#d32f2f",
    "vacuole":          "#1565c0",
    "chloroplast":      "#2e7d32",
    "ribosome":         "#795548",
    "centriole":        "#455a64",
    "dna_strand1":      "#1565c0",
    "dna_strand2":      "#c62828",
    "at_pair":          "#ff8f00",
    "gc_pair":          "#2e7d32",
    "chromosome":       "#6a1b9a",
    "spindle":          "#0277bd",
    "heart_oxy":        "#c62828",
    "heart_deoxy":      "#1565c0",
    "nephron_tubule":   "#1565c0",
    "nephron_blood":    "#c62828",
    "neuron_soma":      "#f57c00",
    "neuron_axon":      "#1b5e20",
    "neuron_myelin":    "#fff9c4",
    "neuron_dendrite":  "#4a148c",
    "producer":         "#2e7d32",
    "primary":          "#f57c00",
    "secondary":        "#1565c0",
    "tertiary":         "#ad1457",
    "quaternary":       "#4a148c",
    "quinary":          "#37474f",
}

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "figure.facecolor": "white",
    "axes.facecolor": "white",
})


def _fig_to_svg(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="svg", bbox_inches="tight", facecolor="white", dpi=110)
    buf.seek(0)
    svg = buf.getvalue().decode("utf-8")
    plt.close(fig)
    return svg


def _annotate(ax, text, xy, xytext, color="black", fontsize=9, highlight=False):
    """Arrow annotation pointing from xytext label to xy target."""
    fc = "#fff176" if highlight else "white"
    ax.annotate(
        text, xy=xy, xytext=xytext,
        fontsize=fontsize, color=color,
        ha="center", va="center",
        bbox=dict(boxstyle="round,pad=0.25", fc=fc, ec=color, lw=0.8),
        arrowprops=dict(arrowstyle="-|>", color=color, lw=1.0,
                        connectionstyle="arc3,rad=0.1"),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Cell Organelle Diagram
# ═══════════════════════════════════════════════════════════════════════════════

def render_cell_diagram(data: Dict[str, Any],
                        canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = CellDiagramSchema(**data)

    # plant cells auto-enable wall + chloroplast
    is_plant = schema.cell_type.lower() == "plant"
    show_wall       = is_plant or schema.show_cell_wall
    show_chloro     = is_plant or schema.show_chloroplast
    show_lysosome   = schema.show_lysosome and not is_plant
    show_centriole  = schema.show_centriole and not is_plant
    hl = (schema.highlight_organelle or "").lower().replace(" ", "_")

    fig, ax = plt.subplots(figsize=(10, 8))
    ax.set_xlim(0, 10); ax.set_ylim(0, 8)
    ax.set_aspect("equal"); ax.axis("off")

    if is_plant:
        _draw_plant_cell(ax, schema, show_wall, show_chloro, hl)
    else:
        _draw_animal_cell(ax, schema, show_lysosome, show_centriole, hl)

    title = schema.title or f"{'Plant' if is_plant else 'Animal'} Cell"
    ax.set_title(title, fontsize=14, fontweight="bold", pad=6)
    fig.tight_layout(pad=0.4)
    return _fig_to_svg(fig)


def _draw_animal_cell(ax, schema, show_lysosome, show_centriole, hl):
    # ── Cell membrane ─────────────────────────────────────────────────────────
    cell = Ellipse((5, 4), 9.0, 7.2, fc="#fff8e1", ec=C["cell_membrane"], lw=2.5, zorder=1)
    ax.add_patch(cell)
    if schema.labeled:
        _annotate(ax, "Cell membrane", (1.0, 5.0), (0.4, 6.5),
                  C["cell_membrane"], highlight=(hl == "cell_membrane"))

    # ── Nucleus ───────────────────────────────────────────────────────────────
    if schema.show_nucleus:
        # Nuclear envelope (double membrane — two concentric ellipses)
        nuc_outer = Ellipse((4.2, 4.6), 2.4, 1.9, fc="#ede7f6",
                            ec=C["nucleus"], lw=2.0, zorder=3)
        nuc_inner = Ellipse((4.2, 4.6), 2.05, 1.6, fc="none",
                            ec=C["nucleus"], lw=0.8, ls="--", zorder=4)
        ax.add_patch(nuc_outer)
        ax.add_patch(nuc_inner)
        # Nucleolus
        nucl = Ellipse((4.0, 4.8), 0.65, 0.55, fc=C["nucleolus"],
                       ec="none", zorder=5)
        ax.add_patch(nucl)
        if schema.labeled:
            _annotate(ax, "Nucleus", (4.2, 4.6), (2.2, 6.2),
                      C["nucleus"], highlight=(hl == "nucleus"))
            _annotate(ax, "Nucleolus", (4.0, 4.8), (2.0, 5.0),
                      C["nucleolus"], highlight=(hl == "nucleolus"))

    # ── Mitochondria ──────────────────────────────────────────────────────────
    if schema.show_mitochondria:
        mito_positions = [(7.2, 5.8, 25), (7.8, 3.2, -15), (2.8, 2.4, 10)]
        for mx, my, ang in mito_positions:
            outer = Ellipse((mx, my), 1.1, 0.55, angle=ang,
                            fc="#ffe0b2", ec=C["mitochondria"], lw=1.5, zorder=3)
            inner = Ellipse((mx, my), 0.7, 0.3, angle=ang,
                            fc="none", ec=C["mitochondria"], lw=0.8,
                            ls="dotted", zorder=4)
            ax.add_patch(outer)
            ax.add_patch(inner)
        if schema.labeled:
            _annotate(ax, "Mitochondria", (7.2, 5.8), (8.5, 7.0),
                      C["mitochondria"], highlight=(hl in ("mitochondria", "mitochondrion")))

    # ── Rough ER ──────────────────────────────────────────────────────────────
    if schema.show_er:
        # Rough ER: wavy stack of lines near nucleus
        for i, dy in enumerate([-0.15, 0, 0.15]):
            xs = np.linspace(5.2, 7.4, 50)
            ys = 4.6 + dy + 0.12 * np.sin(6 * np.pi * (xs - 5.2) / 2.2)
            ax.plot(xs, ys, color=C["er_rough"], lw=1.5, zorder=3)
        # ribosome dots on rough ER
        if schema.show_ribosome:
            for xi in np.arange(5.3, 7.4, 0.35):
                ax.plot(xi, 4.75, "o", color=C["ribosome"],
                        markersize=3, zorder=5)
        # Smooth ER: smoother curves below
        for dy in [-0.1, 0.05]:
            xs = np.linspace(5.5, 7.0, 40)
            ys = 3.5 + dy + 0.09 * np.sin(4 * np.pi * (xs - 5.5) / 1.5)
            ax.plot(xs, ys, color=C["er_smooth"], lw=1.5, zorder=3)
        if schema.labeled:
            _annotate(ax, "Rough ER", (6.4, 4.75), (8.0, 5.5),
                      C["er_rough"], highlight=(hl in ("er", "rough_er", "endoplasmic_reticulum")))
            _annotate(ax, "Smooth ER", (6.2, 3.5), (8.0, 2.8),
                      C["er_smooth"], highlight=(hl == "smooth_er"))

    # ── Golgi apparatus ───────────────────────────────────────────────────────
    if schema.show_golgi:
        golgi_cx, golgi_cy = 6.7, 2.2
        for i, (rx, ry) in enumerate([(0.7, 0.18), (0.6, 0.16), (0.5, 0.14),
                                       (0.4, 0.12), (0.3, 0.10)]):
            arc = Arc((golgi_cx, golgi_cy + i * 0.22), rx * 2, ry * 2,
                      angle=0, theta1=200, theta2=340,
                      color=C["golgi"], lw=1.8, zorder=3)
            ax.add_patch(arc)
        # Vesicles budding off
        for vx, vy in [(7.5, 2.1), (7.3, 2.4)]:
            ax.add_patch(Circle((vx, vy), 0.12, fc=C["golgi"],
                                ec=C["golgi"], lw=1, zorder=4))
        if schema.labeled:
            _annotate(ax, "Golgi apparatus", (golgi_cx, golgi_cy + 0.4),
                      (8.8, 3.0), C["golgi"],
                      highlight=(hl in ("golgi", "golgi_apparatus")))

    # ── Lysosome ──────────────────────────────────────────────────────────────
    if show_lysosome:
        ax.add_patch(Circle((8.0, 1.6), 0.28, fc="#ffcdd2",
                             ec=C["lysosome"], lw=1.5, zorder=4))
        ax.text(8.0, 1.6, "L", ha="center", va="center",
                fontsize=7, color=C["lysosome"], fontweight="bold", zorder=5)
        if schema.labeled:
            _annotate(ax, "Lysosome", (8.0, 1.6), (9.2, 1.0),
                      C["lysosome"], highlight=(hl == "lysosome"))

    # ── Vacuole ───────────────────────────────────────────────────────────────
    if schema.show_vacuole:
        for vx, vy, vr in [(2.0, 5.8, 0.35), (2.8, 2.8, 0.25)]:
            ax.add_patch(Circle((vx, vy), vr, fc="#e3f2fd",
                                 ec=C["vacuole"], lw=1.2, zorder=3))
        if schema.labeled:
            _annotate(ax, "Vacuole", (2.0, 5.8), (0.8, 7.0),
                      C["vacuole"], highlight=(hl == "vacuole"))

    # ── Centriole ─────────────────────────────────────────────────────────────
    if show_centriole:
        cx_c, cy_c = 5.2, 5.7
        # Two perpendicular small rectangles
        ax.add_patch(FancyBboxPatch((cx_c - 0.28, cy_c - 0.1), 0.56, 0.2,
                                    boxstyle="round,pad=0.02",
                                    fc="#b0bec5", ec=C["centriole"], lw=1.2, zorder=4))
        ax.add_patch(FancyBboxPatch((cx_c - 0.1, cy_c - 0.28), 0.2, 0.56,
                                    boxstyle="round,pad=0.02",
                                    fc="#b0bec5", ec=C["centriole"], lw=1.2, zorder=4))
        if schema.labeled:
            _annotate(ax, "Centriole", (cx_c, cy_c), (5.8, 7.0),
                      C["centriole"], highlight=(hl == "centriole"))

    # ── Ribosome label ────────────────────────────────────────────────────────
    if schema.show_ribosome and schema.labeled:
        _annotate(ax, "Ribosomes", (5.65, 4.75), (5.5, 6.5),
                  C["ribosome"], highlight=(hl == "ribosome"))


def _draw_plant_cell(ax, schema, show_wall, show_chloro, hl):
    # ── Cell wall ─────────────────────────────────────────────────────────────
    if show_wall:
        wall = FancyBboxPatch((0.2, 0.3), 9.6, 7.4,
                               boxstyle="square,pad=0",
                               fc="#e8f5e9", ec=C["cell_wall"], lw=4, zorder=1)
        ax.add_patch(wall)
        if schema.labeled:
            _annotate(ax, "Cell wall", (0.2, 4.0), (0.8, 7.5),
                      C["cell_wall"], highlight=(hl == "cell_wall"))

    # ── Cell membrane ─────────────────────────────────────────────────────────
    membrane = FancyBboxPatch((0.55, 0.65), 8.9, 6.7,
                               boxstyle="square,pad=0",
                               fc="#f9fbe7", ec=C["cell_membrane"], lw=1.5, zorder=2)
    ax.add_patch(membrane)

    # ── Central vacuole ───────────────────────────────────────────────────────
    if schema.show_vacuole:
        vac = Ellipse((5.5, 3.8), 5.6, 4.4, fc="#e3f2fd",
                      ec=C["vacuole"], lw=2, zorder=3)
        ax.add_patch(vac)
        if schema.labeled:
            _annotate(ax, "Central\nVacuole", (5.5, 3.8), (5.5, 1.8),
                      C["vacuole"], fontsize=10, highlight=(hl == "vacuole"))

    # ── Nucleus ───────────────────────────────────────────────────────────────
    if schema.show_nucleus:
        nuc_o = Ellipse((2.4, 6.0), 2.2, 1.6, fc="#ede7f6",
                        ec=C["nucleus"], lw=2, zorder=4)
        nuc_i = Ellipse((2.4, 6.0), 1.9, 1.35, fc="none",
                        ec=C["nucleus"], lw=0.8, ls="--", zorder=5)
        ax.add_patch(nuc_o); ax.add_patch(nuc_i)
        ax.add_patch(Ellipse((2.3, 6.1), 0.6, 0.5, fc=C["nucleolus"],
                              ec="none", zorder=6))
        if schema.labeled:
            _annotate(ax, "Nucleus", (2.4, 6.0), (0.9, 7.4),
                      C["nucleus"], highlight=(hl == "nucleus"))

    # ── Chloroplasts ──────────────────────────────────────────────────────────
    if show_chloro:
        chloro_pos = [(1.5, 4.6, 15), (1.5, 3.0, -10),
                      (1.5, 1.5, 20), (8.5, 5.5, -20), (8.6, 1.8, 10)]
        for cx, cy, ang in chloro_pos:
            outer = Ellipse((cx, cy), 1.3, 0.65, angle=ang,
                            fc="#c8e6c9", ec=C["chloroplast"], lw=1.5, zorder=4)
            inner = Ellipse((cx, cy), 0.9, 0.38, angle=ang,
                            fc="#a5d6a7", ec=C["chloroplast"], lw=0.8, zorder=5)
            ax.add_patch(outer); ax.add_patch(inner)
        if schema.labeled:
            _annotate(ax, "Chloroplast", (1.5, 4.6), (0.6, 6.0),
                      C["chloroplast"], highlight=(hl == "chloroplast"))

    # ── Mitochondria ──────────────────────────────────────────────────────────
    if schema.show_mitochondria:
        for mx, my, ang in [(3.5, 1.2, 5), (4.2, 7.3, -10)]:
            ax.add_patch(Ellipse((mx, my), 1.0, 0.5, angle=ang,
                                  fc="#ffe0b2", ec=C["mitochondria"], lw=1.5, zorder=4))
        if schema.labeled:
            _annotate(ax, "Mitochondria", (3.5, 1.2), (5.0, 0.6),
                      C["mitochondria"], highlight=(hl in ("mitochondria", "mitochondrion")))

    # ── Golgi apparatus ───────────────────────────────────────────────────────
    if schema.show_golgi:
        gx, gy = 8.0, 3.5
        for i, rx in enumerate([0.65, 0.55, 0.45, 0.35]):
            ax.add_patch(Arc((gx, gy + i * 0.22), rx * 2, 0.28,
                              theta1=200, theta2=340,
                              color=C["golgi"], lw=1.8, zorder=4))
        if schema.labeled:
            _annotate(ax, "Golgi body", (gx, gy + 0.4), (9.5, 4.2),
                      C["golgi"], highlight=(hl in ("golgi", "golgi_apparatus")))

    # ── Cell wall label ───────────────────────────────────────────────────────
    if schema.labeled and show_wall:
        ax.text(0.38, 7.9, "Plasmodesmata", fontsize=7, color=C["cell_wall"],
                ha="left", va="center", style="italic")


# ═══════════════════════════════════════════════════════════════════════════════
# 2. DNA Structure
# ═══════════════════════════════════════════════════════════════════════════════

# Fixed sequence for deterministic base-pair labeling
_BASES_FIXED = "ATCGATCGATCGATCGATCG"
_COMPLEMENT  = {"A": "T", "T": "A", "G": "C", "C": "G"}
_PAIR_COLOR  = {"A": C["at_pair"], "T": C["at_pair"],
                "G": C["gc_pair"],  "C": C["gc_pair"]}


def render_dna_structure(data: Dict[str, Any],
                          canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = DNAStructureSchema(**data)

    if schema.structure_type.lower() == "replication_fork":
        return _draw_replication_fork(schema)
    return _draw_double_helix(schema)


def _draw_double_helix(schema: DNAStructureSchema) -> str:
    n = schema.num_base_pairs
    turns = max(1, n / 5)          # ~5 bp per turn
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.set_xlim(-0.5, n + 0.5)
    ax.set_ylim(-2.0, 2.5)
    ax.axis("off")

    t = np.linspace(0, n, 600)
    amp = 1.2
    freq = turns * 2 * np.pi / n

    y1 = amp * np.sin(freq * t)
    y2 = -amp * np.sin(freq * t)   # complementary strand

    # ── Rungs (base pairs) ────────────────────────────────────────────────────
    for i in range(n):
        xi = i + 0.5
        v1 = amp * math.sin(freq * xi)
        v2 = -v1
        base = _BASES_FIXED[i % len(_BASES_FIXED)]
        comp = _COMPLEMENT[base]
        clr  = _PAIR_COLOR[base]
        # rung
        ax.plot([xi, xi], [v2 + 0.08, v1 - 0.08], color=clr,
                lw=1.8, alpha=0.85, zorder=2)
        # base labels
        if schema.show_base_labels:
            ax.text(xi, v1 - 0.28, base, ha="center", va="center",
                    fontsize=7, color=clr, fontweight="bold", zorder=4)
            ax.text(xi, v2 + 0.28, comp, ha="center", va="center",
                    fontsize=7, color=clr, fontweight="bold", zorder=4)

    # ── Backbone strands ──────────────────────────────────────────────────────
    ax.plot(t, y1, color=C["dna_strand1"], lw=2.8, solid_capstyle="round",
            label="5′→3′ strand", zorder=3)
    ax.plot(t, y2, color=C["dna_strand2"], lw=2.8, solid_capstyle="round",
            label="3′→5′ strand", zorder=3)

    # ── Labels ────────────────────────────────────────────────────────────────
    if schema.show_labels:
        ax.text(-0.3, amp + 0.2, "5′", ha="right", fontsize=11,
                color=C["dna_strand1"], fontweight="bold")
        ax.text(n + 0.3, amp + 0.2, "3′", ha="left", fontsize=11,
                color=C["dna_strand1"], fontweight="bold")
        ax.text(-0.3, -amp - 0.2, "3′", ha="right", fontsize=11,
                color=C["dna_strand2"], fontweight="bold")
        ax.text(n + 0.3, -amp - 0.2, "5′", ha="left", fontsize=11,
                color=C["dna_strand2"], fontweight="bold")
        # Sugar-phosphate backbone labels
        mid = n / 2
        ax.annotate("Sugar-phosphate\nbackbone",
                    xy=(mid, amp), xytext=(mid, 1.85),
                    fontsize=8, ha="center", color=C["dna_strand1"],
                    arrowprops=dict(arrowstyle="-|>", lw=0.8,
                                   color=C["dna_strand1"]))
        # Hydrogen bonds label
        xi_h = int(n * 0.3) + 0.5
        v1_h = amp * math.sin(freq * xi_h)
        v2_h = -v1_h
        mid_h = (v1_h + v2_h) / 2
        ax.annotate("H-bonds",
                    xy=(xi_h, mid_h), xytext=(xi_h - 2.5, -1.6),
                    fontsize=8, ha="center", color="#555555",
                    arrowprops=dict(arrowstyle="-|>", lw=0.8, color="#555555"))

        # A-T / G-C key
        ax.text(n * 0.7, -1.7, "─── A-T pair", fontsize=8, color=C["at_pair"])
        ax.text(n * 0.7, -1.95, "─── G-C pair", fontsize=8, color=C["gc_pair"])

    title = schema.title or "DNA Double Helix"
    ax.set_title(title, fontsize=13, fontweight="bold", pad=4)
    ax.legend(loc="upper right", fontsize=8)
    fig.tight_layout(pad=0.5)
    return _fig_to_svg(fig)


def _draw_replication_fork(schema: DNAStructureSchema) -> str:
    fig, ax = plt.subplots(figsize=(10, 6.5))
    ax.set_xlim(-1, 11)
    ax.set_ylim(-3.5, 3.5)
    ax.axis("off")
    ax.set_title(schema.title or "DNA Replication Fork",
                 fontsize=13, fontweight="bold", pad=4)

    n = schema.num_base_pairs

    # ── Left: intact double-stranded DNA (template) ───────────────────────────
    t_left = np.linspace(0, 4, 200)
    amp, freq = 0.9, 2 * np.pi / 4
    y1_l = amp * np.sin(freq * t_left)
    y2_l = -amp * np.sin(freq * t_left)
    ax.plot(t_left, y1_l, color=C["dna_strand1"], lw=2.5, zorder=3)
    ax.plot(t_left, y2_l, color=C["dna_strand2"], lw=2.5, zorder=3)
    # rungs on intact region
    for xi in np.arange(0.5, 4, 0.5):
        v1 = amp * math.sin(freq * xi)
        ax.plot([xi, xi], [-v1 + 0.07, v1 - 0.07],
                color=C["at_pair"], lw=1.5, alpha=0.7, zorder=2)

    # ── Helicase at fork (x=4) ────────────────────────────────────────────────
    helicase = Circle((4.0, 0), 0.45, fc="#80cbc4", ec="#00796b", lw=1.8, zorder=5)
    ax.add_patch(helicase)
    ax.text(4.0, 0, "He", ha="center", va="center", fontsize=8,
            color="#004d40", fontweight="bold", zorder=6)
    if schema.show_labels:
        ax.annotate("Helicase", xy=(4.0, 0), xytext=(3.2, 1.8),
                    fontsize=8, color="#00796b",
                    arrowprops=dict(arrowstyle="-|>", color="#00796b", lw=0.9))

    # ── Leading strand (top arm of fork, rightward) ───────────────────────────
    t_lead = np.linspace(4.4, 10, 200)
    y_lead_template = amp * np.sin(freq * t_lead)
    y_lead_new = y_lead_template + 0.25   # new strand slightly above
    ax.plot(t_lead, y_lead_template, color=C["dna_strand1"],
            lw=2.5, zorder=3)
    ax.plot(t_lead, y_lead_new, color="#43a047",
            lw=2.0, ls="-", zorder=3)
    # Continuous synthesis arrow
    ax.annotate("", xy=(10, y_lead_new[-1]), xytext=(5.5, y_lead_new[50]),
                arrowprops=dict(arrowstyle="-|>", color="#43a047", lw=1.5))
    if schema.show_labels:
        ax.text(10.2, y_lead_new[-1], "Leading\nstrand\n(continuous)",
                fontsize=7.5, color="#43a047", va="center")
    # DNA Pol on leading strand
    ax.add_patch(Circle((8, y_lead_new[100]), 0.35, fc="#ffe082",
                         ec="#f57c00", lw=1.5, zorder=5))
    ax.text(8, y_lead_new[100], "Pol", ha="center", va="center",
            fontsize=7, color="#bf360c", fontweight="bold", zorder=6)

    # ── Lagging strand (bottom arm, synthesised in fragments) ─────────────────
    y_lag_template = -amp * np.sin(freq * t_lead)
    y_lag_new = y_lag_template - 0.25
    ax.plot(t_lead, y_lag_template, color=C["dna_strand2"],
            lw=2.5, zorder=3)
    # Okazaki fragments (3 segments, rightward)
    frag_starts = [4.6, 6.3, 8.0]
    for i, fs in enumerate(frag_starts):
        fe = min(fs + 1.5, 10)
        t_frag = np.linspace(fs, fe, 60)
        y_frag = -amp * np.sin(freq * t_frag) - 0.25
        ax.plot(t_frag, y_frag, color="#e57373", lw=2.0, zorder=3)
        # small arrow showing synthesis direction (right→left on lagging)
        mid_t = (fs + fe) / 2
        mid_y = float(np.interp(mid_t, t_frag, y_frag))
        ax.annotate("", xy=(fs + 0.2, mid_y), xytext=(fe - 0.2, mid_y),
                    arrowprops=dict(arrowstyle="-|>", color="#e57373", lw=1.2))
        if i == 1 and schema.show_labels:
            ax.text(mid_t, mid_y - 0.45, "Okazaki\nfragment",
                    ha="center", fontsize=7.5, color="#e57373")

    if schema.show_labels:
        ax.text(10.2, y_lag_new[-1] + 0.1, "Lagging\nstrand\n(fragments)",
                fontsize=7.5, color="#e57373", va="center")
        # Primase label
        ax.annotate("Primase/\nPrimer", xy=(4.7, y_lag_template[10]),
                    xytext=(3.5, -2.8), fontsize=7.5, color="#7b1fa2",
                    arrowprops=dict(arrowstyle="-|>", color="#7b1fa2", lw=0.9))

    # ── 5' / 3' labels ────────────────────────────────────────────────────────
    if schema.show_labels:
        ax.text(-0.8, amp + 0.1, "5′", fontsize=10, color=C["dna_strand1"],
                fontweight="bold")
        ax.text(-0.8, -amp - 0.1, "3′", fontsize=10, color=C["dna_strand2"],
                fontweight="bold")

    fig.tight_layout(pad=0.5)
    return _fig_to_svg(fig)


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Cell Division
# ═══════════════════════════════════════════════════════════════════════════════

def render_cell_division(data: Dict[str, Any],
                          canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = CellDivisionSchema(**data)
    stage  = schema.stage
    is_meiosis = schema.division_type.lower() == "meiosis"

    fig, ax = plt.subplots(figsize=(7, 7))
    ax.set_xlim(-5, 5); ax.set_ylim(-5, 5)
    ax.set_aspect("equal"); ax.axis("off")

    n_pairs = schema.num_chromosome_pairs

    if is_meiosis:
        _draw_meiosis_stage(ax, stage, n_pairs, schema.show_spindle, schema.show_labels)
    else:
        _draw_mitosis_stage(ax, stage, n_pairs, schema.show_spindle, schema.show_labels)

    div_name = "Meiosis" if is_meiosis else "Mitosis"
    stage_name = stage.replace("_", " ").title()
    title = schema.title or f"{div_name} — {stage_name}"
    ax.set_title(title, fontsize=14, fontweight="bold", pad=6)
    fig.tight_layout(pad=0.3)
    return _fig_to_svg(fig)


def _chromosome(ax, cx, cy, size=0.4, angle=0.0, color=C["chromosome"],
                condensed=True):
    """Draw a chromosome as an X-shape (two sister chromatids)."""
    r = math.radians(angle)
    cos_r, sin_r = math.cos(r), math.sin(r)
    # Two arms
    for sign in [1, -1]:
        for arm in [1, -1]:
            dx = size * (arm * cos_r - sign * 0.25 * sin_r)
            dy = size * (arm * sin_r + sign * 0.25 * cos_r)
            ax.plot([cx, cx + dx], [cy, cy + dy],
                    color=color, lw=3.5 if condensed else 1.5,
                    solid_capstyle="round", zorder=4)
    # Centromere dot
    ax.plot(cx, cy, "o", color=color, markersize=6, zorder=5)


def _draw_mitosis_stage(ax, stage, n_pairs, show_spindle, show_labels):
    # Cell outline
    cell_w, cell_h = 4.2, 4.2
    angle_stage = {"anaphase": (3.0, 4.8), "telophase": (2.8, 5.0),
                   "cytokinesis": (2.5, 5.2)}.get(stage, (cell_w, cell_h))

    cell = Ellipse((0, 0), angle_stage[0] * 2, angle_stage[1] * 2,
                   fc="#fffde7", ec=C["cell_membrane"], lw=2.5, zorder=1)
    ax.add_patch(cell)

    if stage in ("prophase",):
        # Nuclear envelope (dissolving)
        nuc = Ellipse((0, 0), 2.6, 2.0, fc="#ede7f6",
                      ec=C["nucleus"], lw=1.5, ls="--", zorder=2)
        ax.add_patch(nuc)
        if show_labels:
            ax.text(0, -1.3, "Nuclear envelope\n(dissolving)", ha="center",
                    fontsize=8, color=C["nucleus"], style="italic")
        # Chromosomes: condensing, scattered
        positions = [(-1.0, 0.5, 30), (0.0, 0.8, -20), (1.0, 0.3, 60),
                     (-0.5, -0.5, 10), (0.5, -0.7, -40)][:n_pairs * 2]
        for cx, cy, ang in positions:
            _chromosome(ax, cx, cy, size=0.38, angle=ang)
        if show_labels:
            ax.text(0, 3.5, "Condensing chromosomes", ha="center",
                    fontsize=9, color=C["chromosome"])

    elif stage == "metaphase":
        # Chromosomes at equatorial plate
        if show_spindle:
            for sign in [-1, 1]:
                for xi in np.linspace(-2.5, 2.5, n_pairs * 2 + 1):
                    ax.plot([xi * 0.3, sign * 3.8],
                            [0, sign * 3.8 * 0.05], color=C["spindle"],
                            lw=0.8, alpha=0.6, zorder=2)
            ax.plot([-4, 4], [0, 0], color=C["spindle"],
                    lw=0.5, ls="--", alpha=0.4)
            if show_labels:
                ax.text(-4.5, 0, "Spindle", ha="right", fontsize=8,
                        color=C["spindle"])
                ax.text(0, -0.5, "Metaphase plate", ha="center", fontsize=8,
                        color="#555555", style="italic")

        xs = np.linspace(-1.5 * (n_pairs - 1) / 2, 1.5 * (n_pairs - 1) / 2,
                         n_pairs)
        for i, xi in enumerate(xs):
            _chromosome(ax, xi, 0, size=0.42, angle=90)

    elif stage == "anaphase":
        # Chromosomes moving to poles
        for sign in [-1, 1]:
            xs = np.linspace(-1.2 * (n_pairs - 1) / 2,
                              1.2 * (n_pairs - 1) / 2, n_pairs)
            for xi in xs:
                _chromosome(ax, xi * 0.6, sign * 2.0,
                             size=0.35, angle=90 + sign * 15)
        if show_spindle:
            for sign in [-1, 1]:
                ax.annotate("", xy=(0, sign * 3.8), xytext=(0, 0),
                            arrowprops=dict(arrowstyle="-|>",
                                           color=C["spindle"], lw=1.0))
        if show_labels:
            for sign, lbl in [(-1, "To poles →"), (1, "← To poles")]:
                ax.text(0, sign * 3.0, lbl, ha="center", fontsize=8,
                        color="#555555")

    elif stage == "telophase":
        # Two nuclear envelopes re-forming
        for sign in [-1, 1]:
            nuc_t = Ellipse((0, sign * 2.0), 2.4, 1.4,
                             fc="#ede7f6", ec=C["nucleus"],
                             lw=1.5, ls="--", zorder=2)
            ax.add_patch(nuc_t)
            xs = np.linspace(-0.8, 0.8, n_pairs)
            for xi in xs:
                _chromosome(ax, xi, sign * 2.0, size=0.28, angle=0,
                             condensed=False)
        if show_labels:
            ax.text(0, 0, "Cleavage\nfurrow", ha="center",
                    fontsize=9, color=C["cell_membrane"])
            ax.plot([-3.0, 3.0], [0, 0],
                    color=C["cell_membrane"], lw=2, ls="--", zorder=3)

    elif stage == "cytokinesis":
        # Two daughter cells
        for sign in [-1, 1]:
            daughter = Ellipse((0, sign * 2.4), 3.8, 2.6,
                                fc="#fffde7", ec=C["cell_membrane"],
                                lw=2.5, zorder=2)
            ax.add_patch(daughter)
            nuc_d = Ellipse((0, sign * 2.4), 1.2, 0.9,
                             fc="#ede7f6", ec=C["nucleus"], lw=1.5, zorder=3)
            ax.add_patch(nuc_d)
        # Remove original outer cell patch visibility
        cell.set_visible(False)
        if show_labels:
            for sign, lbl in [(-1, "Daughter cell 1"), (1, "Daughter cell 2")]:
                ax.text(0, sign * 3.8, lbl, ha="center",
                        fontsize=9, color=C["cell_membrane"])

    else:
        # Generic fallback — show label
        ax.text(0, 0, f"Stage: {stage}", ha="center", va="center",
                fontsize=12, color="#555555")


def _draw_meiosis_stage(ax, stage, n_pairs, show_spindle, show_labels):
    """Draw a meiosis stage — key NEET-relevant stages."""
    cell = Ellipse((0, 0), 8.5, 8.5, fc="#f3e5f5",
                   ec=C["nucleus"], lw=2.5, zorder=1)
    ax.add_patch(cell)

    if stage in ("prophase_1", "prophase1"):
        # Homologous chromosomes pairing (synapsis)
        for i in range(n_pairs):
            angle = (i / n_pairs) * 2 * math.pi
            cx = 2.0 * math.cos(angle)
            cy = 2.0 * math.sin(angle)
            # Pair of homologs side by side with chiasma
            for sign, clr in [(-0.25, C["chromosome"]),
                               (0.25, "#e57373")]:
                ax.plot([cx + sign, cx + sign],
                        [cy - 0.5, cy + 0.5],
                        color=clr, lw=4, solid_capstyle="round", zorder=4)
            # Chiasma (X)
            ax.plot(cx, cy, "x", color="#ad1457",
                    markersize=8, markeredgewidth=2, zorder=5)
        if show_labels:
            ax.text(0, -4.5, "Synapsis / Bivalents / Chiasma",
                    ha="center", fontsize=9, color=C["chromosome"])
            ax.text(0, -4.0, "(Crossing over occurs)", ha="center",
                    fontsize=8, color="#ad1457", style="italic")

    elif stage in ("metaphase_1", "metaphase1"):
        # Bivalents at equator
        if show_spindle:
            ax.plot([-4, 4], [0, 0], color=C["spindle"],
                    lw=0.8, ls="--", alpha=0.5)
        for i in range(n_pairs):
            xi = (i - (n_pairs - 1) / 2.0) * 1.4
            for sign, clr in [(-0.25, C["chromosome"]),
                               (0.25, "#e57373")]:
                ax.plot([xi + sign, xi + sign],
                        [-0.5, 0.5], color=clr,
                        lw=4, solid_capstyle="round", zorder=4)
        if show_labels:
            ax.text(0, -1.0, "Bivalents at equatorial plate",
                    ha="center", fontsize=9, color="#555555", style="italic")

    elif stage in ("anaphase_1", "anaphase1"):
        # Homologs moving to opposite poles
        for i in range(n_pairs):
            xi = (i - (n_pairs - 1) / 2.0) * 1.4
            for sign_y, clr in [(-2.5, C["chromosome"]),
                                  (2.5, "#e57373")]:
                ax.plot([xi, xi], [sign_y - 0.4, sign_y + 0.4],
                        color=clr, lw=4, solid_capstyle="round", zorder=4)
        if show_labels:
            ax.text(0, 0, "Homologs separate\n(sister chromatids together)",
                    ha="center", fontsize=9, color="#555555")

    elif stage in ("metaphase_2", "metaphase2"):
        # Individual chromosomes at equator (no bivalents)
        if show_spindle:
            ax.plot([-4, 4], [0, 0], color=C["spindle"],
                    lw=0.8, ls="--", alpha=0.5)
        for i in range(n_pairs * 2):
            xi = (i - n_pairs + 0.5) * 0.9
            _chromosome(ax, xi, 0, size=0.38, angle=90)
        if show_labels:
            ax.text(0, -1.5, "Sister chromatids at equator",
                    ha="center", fontsize=9, color="#555555", style="italic")

    elif stage in ("anaphase_2", "anaphase2"):
        # Sister chromatids separating
        for i in range(n_pairs * 2):
            xi = (i - n_pairs + 0.5) * 0.8
            for sign_y in [-2.0, 2.0]:
                ax.plot([xi, xi], [sign_y - 0.3, sign_y + 0.3],
                        color=C["chromosome"], lw=3.5,
                        solid_capstyle="round", zorder=4)
        if show_labels:
            ax.text(0, 0, "Sister chromatids separate",
                    ha="center", fontsize=9, color="#555555")

    else:
        ax.text(0, 0, f"Meiosis\n{stage.replace('_', ' ').title()}",
                ha="center", va="center", fontsize=13, color=C["nucleus"])


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Heart Diagram
# ═══════════════════════════════════════════════════════════════════════════════

def render_heart_diagram(data: Dict[str, Any],
                          canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = HeartDiagramSchema(**data)

    fig, ax = plt.subplots(figsize=(9, 8))
    ax.set_xlim(0, 10); ax.set_ylim(0, 10)
    ax.set_aspect("equal"); ax.axis("off")

    # ── Outer heart shape (pericardium) ───────────────────────────────────────
    heart_bg = Ellipse((5, 4.5), 8.5, 7.5, fc="#fce4ec",
                        ec="#e91e63", lw=3, zorder=1, alpha=0.35)
    ax.add_patch(heart_bg)

    # ── Four chambers ─────────────────────────────────────────────────────────
    # Anatomical note: viewer's LEFT = patient's RIGHT
    # Right side of diagram = patient's left (systemic circuit = oxygenated)
    # Left side of diagram  = patient's right (pulmonary circuit = deoxygenated)

    # Right Atrium (viewer's left side, deoxygenated blood from body)
    RA = FancyBboxPatch((1.0, 5.5), 2.8, 2.2, boxstyle="round,pad=0.3",
                         fc="#bbdefb", ec=C["heart_deoxy"], lw=2, zorder=3)
    ax.add_patch(RA)
    ax.text(2.4, 6.6, "Right\nAtrium", ha="center", va="center",
            fontsize=10, fontweight="bold", color=C["heart_deoxy"])

    # Left Atrium (viewer's right, oxygenated blood from lungs)
    LA = FancyBboxPatch((6.2, 5.5), 2.8, 2.2, boxstyle="round,pad=0.3",
                         fc="#ffcdd2", ec=C["heart_oxy"], lw=2, zorder=3)
    ax.add_patch(LA)
    ax.text(7.6, 6.6, "Left\nAtrium", ha="center", va="center",
            fontsize=10, fontweight="bold", color=C["heart_oxy"])

    # Interatrial septum
    ax.plot([3.8, 6.2], [5.5, 5.5], color="#555555", lw=2, zorder=4)
    ax.plot([3.8, 6.2], [7.7, 7.7], color="#555555", lw=2, zorder=4)
    ax.plot([3.8, 3.8], [5.5, 7.7], color="#555555", lw=1.5, zorder=4)
    ax.plot([6.2, 6.2], [5.5, 7.7], color="#555555", lw=1.5, zorder=4)

    # Right Ventricle
    RV_pts = np.array([[1.0, 5.5], [1.0, 2.0], [4.5, 1.0],
                        [3.8, 5.5], [1.0, 5.5]])
    ax.fill(RV_pts[:, 0], RV_pts[:, 1], fc="#bbdefb",
            ec=C["heart_deoxy"], lw=2, zorder=3)
    ax.text(2.2, 3.5, "Right\nVentricle", ha="center", va="center",
            fontsize=10, fontweight="bold", color=C["heart_deoxy"])

    # Left Ventricle (larger, thicker wall)
    LV_pts = np.array([[6.2, 5.5], [5.5, 1.0], [9.0, 2.0],
                        [9.0, 5.5], [6.2, 5.5]])
    ax.fill(LV_pts[:, 0], LV_pts[:, 1], fc="#ffcdd2",
            ec=C["heart_oxy"], lw=2.5, zorder=3)
    ax.text(7.5, 3.5, "Left\nVentricle", ha="center", va="center",
            fontsize=10, fontweight="bold", color=C["heart_oxy"])

    # Interventricular septum
    ax.plot([3.8, 5.5], [5.5, 1.0], color="#555555", lw=2.5, zorder=4)

    # ── Valves ────────────────────────────────────────────────────────────────
    if schema.show_valves:
        # Tricuspid (RA→RV) — between right chambers
        ax.text(2.4, 5.4, "Tricuspid", ha="center", va="top",
                fontsize=7.5, color=C["heart_deoxy"],
                bbox=dict(fc="#bbdefb", ec=C["heart_deoxy"], lw=0.8, pad=1.5))
        # Bicuspid/Mitral (LA→LV)
        ax.text(7.6, 5.4, "Bicuspid\n(Mitral)", ha="center", va="top",
                fontsize=7.5, color=C["heart_oxy"],
                bbox=dict(fc="#ffcdd2", ec=C["heart_oxy"], lw=0.8, pad=1.5))
        # Pulmonary semilunar (RV→PA)
        ax.text(2.0, 8.0, "Pulmonary\nvalve", ha="center",
                fontsize=7.0, color=C["heart_deoxy"])
        # Aortic semilunar (LV→Aorta)
        ax.text(8.0, 8.0, "Aortic\nvalve", ha="center",
                fontsize=7.0, color=C["heart_oxy"])

    # ── Major vessels ─────────────────────────────────────────────────────────
    # Superior Vena Cava (→ RA, from top)
    ax.annotate("", xy=(2.0, 7.7), xytext=(2.0, 9.5),
                arrowprops=dict(arrowstyle="-|>", color=C["heart_deoxy"], lw=2.5))
    ax.text(1.0, 9.6, "Superior\nVena Cava", ha="center", fontsize=8.5,
            color=C["heart_deoxy"], fontweight="bold")

    # Inferior Vena Cava (→ RA, from bottom)
    ax.annotate("", xy=(1.8, 5.5), xytext=(1.0, 3.8),
                arrowprops=dict(arrowstyle="-|>", color=C["heart_deoxy"], lw=2.0))
    ax.text(0.2, 3.5, "Inferior\nVena Cava", ha="center", fontsize=8,
            color=C["heart_deoxy"], fontweight="bold")

    # Pulmonary Artery (← RV, to lungs)
    ax.annotate("", xy=(2.8, 9.5), xytext=(2.8, 7.7),
                arrowprops=dict(arrowstyle="-|>", color=C["heart_deoxy"], lw=2.5))
    ax.text(3.2, 9.8, "Pulmonary\nArtery\n(to lungs)", ha="center", fontsize=8.5,
            color=C["heart_deoxy"], fontweight="bold")

    # Pulmonary Veins (→ LA, from lungs)
    ax.annotate("", xy=(7.0, 7.7), xytext=(7.0, 9.5),
                arrowprops=dict(arrowstyle="-|>", color=C["heart_oxy"], lw=2.5))
    ax.text(6.5, 9.8, "Pulmonary\nVeins\n(from lungs)", ha="center", fontsize=8.5,
            color=C["heart_oxy"], fontweight="bold")

    # Aorta (← LV, to body)
    ax.annotate("", xy=(8.5, 9.5), xytext=(8.5, 7.7),
                arrowprops=dict(arrowstyle="-|>", color=C["heart_oxy"], lw=2.5))
    ax.text(9.5, 9.8, "Aorta\n(to body)", ha="center", fontsize=8.5,
            color=C["heart_oxy"], fontweight="bold")

    # ── Blood flow annotations ────────────────────────────────────────────────
    if schema.show_blood_flow:
        ax.text(0.1, 1.5, "Deoxygenated\nblood (blue)",
                fontsize=8, color=C["heart_deoxy"],
                bbox=dict(fc="#e3f2fd", ec=C["heart_deoxy"], lw=1, pad=2))
        ax.text(6.5, 0.3, "Oxygenated\nblood (red)",
                fontsize=8, color=C["heart_oxy"],
                bbox=dict(fc="#ffebee", ec=C["heart_oxy"], lw=1, pad=2))

    ax.set_title(schema.title or "Human Heart (Schematic)",
                 fontsize=14, fontweight="bold", pad=6)
    fig.tight_layout(pad=0.4)
    return _fig_to_svg(fig)


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Nephron Diagram
# ═══════════════════════════════════════════════════════════════════════════════

def render_nephron_diagram(data: Dict[str, Any],
                            canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = NephronDiagramSchema(**data)
    hl = (schema.highlight_region or "").lower().replace(" ", "_")

    fig, ax = plt.subplots(figsize=(9, 9))
    ax.set_xlim(0, 10); ax.set_ylim(0, 11)
    ax.set_aspect("equal"); ax.axis("off")

    def _tubule_color(region):
        if hl and hl in region:
            return "#ffeb3b"     # highlighted yellow
        return "#e3f2fd"        # default light blue

    lw_t = 2.5   # tubule line width

    # ── Bowman's capsule + Glomerulus ─────────────────────────────────────────
    # Outer capsule
    cap_outer = Circle((5, 9.5), 0.85, fc=_tubule_color("bowman"),
                        ec=C["nephron_tubule"], lw=lw_t, zorder=3)
    ax.add_patch(cap_outer)
    # Glomerular tuft (tangled capillaries — drawn as small coiled circle)
    cap_inner = Circle((5, 9.5), 0.55, fc="#ffcdd2",
                        ec=C["nephron_blood"], lw=1.5, zorder=4)
    ax.add_patch(cap_inner)
    ax.text(5, 9.5, "Glomerulus", ha="center", va="center",
            fontsize=7, fontweight="bold", color=C["nephron_blood"], zorder=5)
    if schema.show_labels:
        _annotate(ax, "Bowman's\nCapsule", (5, 9.5), (2.8, 9.5),
                  C["nephron_tubule"], fontsize=8.5,
                  highlight=bool(hl and "bowman" in hl))

    # Afferent arteriole (→ glomerulus)
    if schema.show_blood_vessels:
        ax.annotate("", xy=(4.55, 9.8), xytext=(3.2, 10.5),
                    arrowprops=dict(arrowstyle="-|>",
                                   color=C["nephron_blood"], lw=2))
        ax.text(2.9, 10.7, "Afferent\narteriole", ha="center",
                fontsize=8, color=C["nephron_blood"])
        ax.annotate("", xy=(3.2, 9.2), xytext=(4.45, 9.2),
                    arrowprops=dict(arrowstyle="-|>",
                                   color="#c0392b", lw=2))
        ax.text(2.6, 9.0, "Efferent\narteriole", ha="center",
                fontsize=8, color="#c0392b")

    # ── Proximal Convoluted Tubule (PCT) ──────────────────────────────────────
    t_pct = np.linspace(0, 4 * np.pi, 200)
    x_pct = 5.4 + 1.6 * np.sin(t_pct) + 0.15 * t_pct
    y_pct = 8.65 - 0.35 * t_pct / (4 * np.pi)
    ax.plot(x_pct, y_pct, color=C["nephron_tubule"], lw=lw_t,
            solid_capstyle="round", zorder=3)
    if schema.show_labels:
        _annotate(ax, "PCT\n(Proximal Convoluted\nTubule)",
                  (x_pct[80], y_pct[80]), (8.5, 8.0),
                  C["nephron_tubule"], fontsize=8,
                  highlight=bool(hl and "pct" in hl))

    # ── Loop of Henle ─────────────────────────────────────────────────────────
    # Descending limb
    x_desc = np.linspace(6.5, 6.5, 50)
    y_desc = np.linspace(8.1, 3.0, 50)
    ax.plot(x_desc, y_desc, color=C["nephron_tubule"], lw=lw_t, zorder=3)
    # Bend at bottom
    theta_bend = np.linspace(np.pi, 0, 50)
    x_bend = 5.5 + 1.0 * np.cos(theta_bend)
    y_bend = 3.0 + 0.6 * np.sin(theta_bend)
    ax.plot(x_bend, y_bend, color=C["nephron_tubule"], lw=lw_t, zorder=3)
    # Ascending limb
    x_asc = np.linspace(4.5, 4.5, 50)
    y_asc = np.linspace(3.0, 7.8, 50)
    ax.plot(x_asc, y_asc, color=C["nephron_tubule"], lw=lw_t, zorder=3)
    if schema.show_labels:
        _annotate(ax, "Loop of Henle\n(Descending limb)",
                  (6.5, 5.5), (8.2, 5.5), C["nephron_tubule"], fontsize=8,
                  highlight=bool(hl and "loop" in hl))
        _annotate(ax, "Ascending\nlimb",
                  (4.5, 5.5), (2.5, 5.0), C["nephron_tubule"], fontsize=8,
                  highlight=bool(hl and "loop" in hl))

    # ── Distal Convoluted Tubule (DCT) ────────────────────────────────────────
    t_dct = np.linspace(0, 3 * np.pi, 150)
    x_dct = 4.0 - 1.4 * np.sin(t_dct) - 0.08 * t_dct
    y_dct = 7.8 + 0.28 * t_dct / (3 * np.pi)
    ax.plot(x_dct, y_dct, color=C["nephron_tubule"], lw=lw_t,
            solid_capstyle="round", zorder=3)
    if schema.show_labels:
        _annotate(ax, "DCT\n(Distal Convoluted\nTubule)",
                  (x_dct[60], y_dct[60]), (1.5, 8.5),
                  C["nephron_tubule"], fontsize=8,
                  highlight=bool(hl and "dct" in hl))

    # ── Collecting Duct ───────────────────────────────────────────────────────
    cd_x = [3.0, 3.0]
    cd_y = [8.1, 1.0]
    ax.plot(cd_x, cd_y, color=C["nephron_tubule"], lw=lw_t + 0.5,
            solid_capstyle="butt", zorder=3)
    # Funnel at bottom → pelvis
    ax.annotate("", xy=(5, 0.5), xytext=(3.0, 1.0),
                arrowprops=dict(arrowstyle="-|>", color=C["nephron_tubule"], lw=2))
    ax.text(5.5, 0.4, "Renal pelvis", fontsize=8, color=C["nephron_tubule"])
    if schema.show_labels:
        _annotate(ax, "Collecting\nDuct",
                  (3.0, 5.0), (1.2, 4.0), C["nephron_tubule"], fontsize=8,
                  highlight=bool(hl and "collecting" in hl))

    # ── Peritubular capillaries ────────────────────────────────────────────────
    if schema.show_blood_vessels:
        # Simple representation: dotted red lines alongside tubules
        ax.plot([6.8, 6.8], [8.0, 3.2], color="#ef9a9a",
                lw=1.8, ls="dotted", zorder=2)
        ax.plot([4.2, 4.2], [3.2, 7.8], color="#ef9a9a",
                lw=1.8, ls="dotted", zorder=2)
        ax.text(7.1, 5.5, "Peritubular\ncapillaries",
                fontsize=7.5, color=C["nephron_blood"], rotation=90,
                ha="center", va="center")

    ax.set_title(schema.title or "Nephron Structure",
                 fontsize=14, fontweight="bold", pad=6)
    fig.tight_layout(pad=0.4)
    return _fig_to_svg(fig)


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Neuron Diagram
# ═══════════════════════════════════════════════════════════════════════════════

def render_neuron_diagram(data: Dict[str, Any],
                           canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = NeuronDiagramSchema(**data)

    fig, ax = plt.subplots(figsize=(12, 4.5))
    ax.set_xlim(-1, 14); ax.set_ylim(-2.5, 3.5)
    ax.set_aspect("equal"); ax.axis("off")

    # ── Dendrites (branching from soma) ───────────────────────────────────────
    soma_x = 1.5
    dendrite_tips = [(-0.5, 2.0), (-0.8, 0.5), (-0.5, -1.2),
                      (0.2, 2.4), (0.8, -1.8)]
    for dx, dy in dendrite_tips:
        ax.plot([soma_x + dx * 0.7, soma_x - 0.4],
                [dy * 0.7, 0], color=C["neuron_dendrite"],
                lw=2.0, solid_capstyle="round", zorder=3)
        # Secondary branches
        mid_x = (soma_x + dx * 0.7 + soma_x - 0.4) / 2
        mid_y = (dy * 0.7 + 0) / 2
        ax.plot([mid_x, mid_x + 0.3 * dy * 0.2],
                [mid_y, mid_y + 0.4], color=C["neuron_dendrite"],
                lw=1.2, solid_capstyle="round", zorder=3)

    if schema.show_labels:
        _annotate(ax, "Dendrites", (-0.5, 1.5), (-1.0, 2.8),
                  C["neuron_dendrite"], fontsize=9)

    # ── Cell body (soma) ──────────────────────────────────────────────────────
    soma = Circle((soma_x, 0), 0.85, fc="#ffe0b2",
                   ec=C["neuron_soma"], lw=2.5, zorder=5)
    ax.add_patch(soma)
    # Nucleus inside soma
    nuc = Circle((soma_x, 0.1), 0.38, fc="#e8eaf6",
                  ec=C["nucleus"], lw=1.5, zorder=6)
    ax.add_patch(nuc)
    ax.text(soma_x, 0.1, "N", ha="center", va="center",
            fontsize=8, fontweight="bold", color=C["nucleus"], zorder=7)
    if schema.show_labels:
        _annotate(ax, "Cell body\n(Soma)", (soma_x, -0.85), (0.5, -2.0),
                  C["neuron_soma"], fontsize=9)
        ax.text(soma_x + 0.05, 0.1, "", ha="center")   # nucleus already marked
        _annotate(ax, "Nucleus", (soma_x, 0.1), (soma_x - 0.8, 1.5),
                  C["nucleus"], fontsize=8)

    # ── Axon hillock ──────────────────────────────────────────────────────────
    ax.annotate("", xy=(2.8, 0), xytext=(soma_x + 0.85, 0),
                arrowprops=dict(arrowstyle="-", color=C["neuron_axon"], lw=2.5))
    if schema.show_labels:
        ax.text(2.4, 0.35, "Axon\nhillock", ha="center",
                fontsize=8, color="#555555")

    # ── Axon with myelin sheath and nodes of Ranvier ──────────────────────────
    axon_start = 2.8
    axon_end   = 11.5
    ax.plot([axon_start, axon_end], [0, 0],
            color=C["neuron_axon"], lw=2.5, zorder=3)

    if schema.neuron_type == "myelinated":
        # Myelin sheath segments (rectangles) with gaps (nodes of Ranvier)
        node_positions = np.arange(3.2, axon_end - 0.5, 2.0)
        for nx in node_positions:
            sheath = FancyBboxPatch((nx, -0.35), 1.6, 0.7,
                                    boxstyle="round,pad=0.05",
                                    fc=C["neuron_myelin"],
                                    ec="#f9a825", lw=1.5, zorder=4)
            ax.add_patch(sheath)
            # Node of Ranvier (gap between sheaths)
            ax.plot(nx - 0.05, 0, "o", color=C["neuron_axon"],
                    markersize=5, zorder=5)

        if schema.show_labels:
            _annotate(ax, "Myelin sheath\n(Schwann cell)",
                      (5.0, 0.35), (5.0, 1.8), "#f9a825", fontsize=9)
            _annotate(ax, "Node of\nRanvier",
                      (5.1, 0), (6.2, -1.5), "#795548", fontsize=9)

    # ── Impulse direction arrow ────────────────────────────────────────────────
    if schema.show_impulse_direction:
        ax.annotate("", xy=(8.5, 0.85), xytext=(5.0, 0.85),
                    arrowprops=dict(arrowstyle="-|>", color="#e53935", lw=1.5))
        ax.text(6.8, 1.1, "Impulse →", ha="center",
                fontsize=8.5, color="#e53935", fontweight="bold")

    # ── Axon terminal / end bulbs ─────────────────────────────────────────────
    terminal_x = axon_end
    for dy, offset_x in [(0.0, 0.5), (0.6, 0.6), (-0.6, 0.6)]:
        tx = terminal_x + offset_x
        ty = dy
        ax.plot([terminal_x, tx], [0, ty],
                color=C["neuron_axon"], lw=2, solid_capstyle="round", zorder=3)
        ax.add_patch(Circle((tx + 0.25, ty), 0.3, fc="#e8f5e9",
                             ec=C["neuron_axon"], lw=1.5, zorder=4))
    if schema.show_labels:
        _annotate(ax, "Axon terminal\n(End bulbs / Synaptic knobs)",
                  (terminal_x + 0.5, 0), (terminal_x + 0.5, 2.0),
                  C["neuron_axon"], fontsize=9)

    if schema.show_labels:
        _annotate(ax, "Axon", (7.0, 0), (7.0, -2.0),
                  C["neuron_axon"], fontsize=9)

    ax.set_title(schema.title or f"Neuron ({schema.neuron_type.capitalize()})",
                 fontsize=13, fontweight="bold", pad=6)
    fig.tight_layout(pad=0.3)
    return _fig_to_svg(fig)


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Food Web
# ═══════════════════════════════════════════════════════════════════════════════

def render_food_web(data: Dict[str, Any],
                    canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = FoodWebSchema(**data)

    fig, ax = plt.subplots(figsize=(10, 7))
    ax.set_aspect("equal"); ax.axis("off")

    # Position nodes by trophic level (y) and spread evenly (x)
    levels: Dict[int, list] = {}
    for node in schema.nodes:
        levels.setdefault(node.trophic_level, []).append(node)

    max_level = max(levels.keys())
    pos: Dict[str, Tuple[float, float]] = {}
    ax.set_xlim(-1, 11); ax.set_ylim(-0.5, max_level + 0.5)

    level_colors = [C["producer"], C["primary"], C["secondary"],
                    C["tertiary"], C["quaternary"]]
    level_names  = ["Producer", "Primary Consumer", "Secondary Consumer",
                    "Tertiary Consumer", "Quaternary Consumer"]

    for lvl, nodes_at_level in sorted(levels.items()):
        n = len(nodes_at_level)
        xs = np.linspace(1.0, 9.0, n)
        for i, node in enumerate(nodes_at_level):
            y = lvl - 0.5
            pos[node.id] = (xs[i], y)
            clr = level_colors[min(lvl - 1, len(level_colors) - 1)]
            box = FancyBboxPatch((xs[i] - 0.7, y - 0.3), 1.4, 0.6,
                                  boxstyle="round,pad=0.1",
                                  fc=clr, ec="white", lw=1.5,
                                  alpha=0.85, zorder=3)
            ax.add_patch(box)
            ax.text(xs[i], y, node.label, ha="center", va="center",
                    fontsize=9, color="white", fontweight="bold", zorder=4)

    # ── Arrows (energy flow: prey → predator) ────────────────────────────────
    for edge in schema.edges:
        if edge.from_id in pos and edge.to_id in pos:
            x1, y1 = pos[edge.from_id]
            x2, y2 = pos[edge.to_id]
            ax.annotate("", xy=(x2, y2 - 0.3), xytext=(x1, y1 + 0.3),
                        arrowprops=dict(arrowstyle="-|>", color="#555555",
                                       lw=1.5, connectionstyle="arc3,rad=0.1"),
                        zorder=2)

    # ── Trophic level labels on y-axis ────────────────────────────────────────
    for lvl in sorted(levels.keys()):
        name = level_names[min(lvl - 1, len(level_names) - 1)]
        ax.text(-0.8, lvl - 0.5, f"T{lvl}\n{name}", ha="right",
                va="center", fontsize=8, color="#555555")

    ax.set_title(schema.title or "Food Web", fontsize=14,
                 fontweight="bold", pad=6)
    fig.tight_layout(pad=0.4)
    return _fig_to_svg(fig)


# ═══════════════════════════════════════════════════════════════════════════════
# 8. Food Chain
# ═══════════════════════════════════════════════════════════════════════════════

def render_food_chain(data: Dict[str, Any],
                       canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = FoodChainSchema(**data)
    organisms = schema.organisms
    n = len(organisms)

    fig, ax = plt.subplots(figsize=(max(8, n * 1.8), 3.5))
    ax.set_xlim(-0.5, n); ax.set_ylim(-0.8, 1.5)
    ax.set_aspect("equal"); ax.axis("off")

    level_colors = [C["producer"], C["primary"], C["secondary"],
                    C["tertiary"], C["quaternary"], C["quinary"],
                    "#37474f", "#263238"]
    trophic_names = ["Producer", "1° Consumer", "2° Consumer",
                     "3° Consumer", "4° Consumer", "5° Consumer", "", ""]

    for i, name in enumerate(organisms):
        xi = i
        clr = level_colors[min(i, len(level_colors) - 1)]
        box = FancyBboxPatch((xi - 0.42, -0.22), 0.84, 0.44,
                              boxstyle="round,pad=0.08",
                              fc=clr, ec="white", lw=1.8, zorder=3)
        ax.add_patch(box)
        ax.text(xi, 0, name, ha="center", va="center",
                fontsize=10, color="white", fontweight="bold", zorder=4)
        # Trophic level label below
        tname = trophic_names[min(i, len(trophic_names) - 1)]
        ax.text(xi, -0.52, tname, ha="center", va="center",
                fontsize=7.5, color="#555555")
        # Arrow to next
        if i < n - 1:
            ax.annotate("", xy=(xi + 0.48, 0), xytext=(xi + 0.44, 0),
                        arrowprops=dict(arrowstyle="-|>", color="#333333",
                                       lw=1.8, mutation_scale=16))

    ax.set_title(schema.title or "Food Chain", fontsize=13,
                 fontweight="bold", pad=6)
    ax.text(n / 2 - 0.5, 1.1,
            "Energy flow direction →",
            ha="center", fontsize=9, color="#555555", style="italic")
    fig.tight_layout(pad=0.3)
    return _fig_to_svg(fig)


# ═══════════════════════════════════════════════════════════════════════════════
# 9. Ecological Pyramid
# ═══════════════════════════════════════════════════════════════════════════════

def render_ecological_pyramid(data: Dict[str, Any],
                               canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = EcologicalPyramidSchema(**data)
    levels = schema.levels
    n = len(levels)

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.set_xlim(-0.5, 10.5); ax.set_ylim(-0.5, n + 0.5)
    ax.set_aspect("equal"); ax.axis("off")

    level_colors = [C["producer"], C["primary"], C["secondary"],
                    C["tertiary"], C["quaternary"], C["quinary"]]

    max_half_width = 4.5
    row_height = 0.8
    row_gap    = 0.12

    for i, lvl in enumerate(levels):
        # Widest at bottom (i=0), narrowest at top (i=n-1)
        frac = 1.0 - (i / (n - 0.5)) * 0.88
        hw = max_half_width * frac
        cx = 5.0
        y_bottom = i * (row_height + row_gap)
        y_top    = y_bottom + row_height

        clr = level_colors[min(i, len(level_colors) - 1)]
        # Trapezoid vertices (bottom wider, top narrower for next level)
        next_frac = 1.0 - ((i + 1) / (n - 0.5)) * 0.88 if i < n - 1 else frac * 0.3
        nhw = max_half_width * next_frac
        trap = plt.Polygon(
            [[cx - hw, y_bottom], [cx + hw, y_bottom],
             [cx + nhw, y_top],   [cx - nhw, y_top]],
            fc=clr, ec="white", lw=1.5, zorder=3, alpha=0.88,
        )
        ax.add_patch(trap)

        # Label inside
        label = lvl.label
        ax.text(cx, y_bottom + row_height / 2, label,
                ha="center", va="center",
                fontsize=9.5, color="white", fontweight="bold", zorder=4)

        # Value on right side
        if lvl.value is not None:
            val_str = f"{lvl.value:g} {lvl.unit}".strip()
            ax.text(cx + hw + 0.2, y_bottom + row_height / 2,
                    val_str, ha="left", va="center",
                    fontsize=8.5, color=clr)

    # ── Pyramid type label ────────────────────────────────────────────────────
    ptype = schema.pyramid_type.capitalize()
    ax.set_title(schema.title or f"Ecological Pyramid of {ptype}",
                 fontsize=13, fontweight="bold", pad=6)
    # Y-axis label
    ax.text(-0.3, n / 2, "Trophic Levels →",
            ha="center", va="center", rotation=90,
            fontsize=9, color="#555555")

    fig.tight_layout(pad=0.4)
    return _fig_to_svg(fig)


# ═══════════════════════════════════════════════════════════════════════════════
# Dispatcher
# ═══════════════════════════════════════════════════════════════════════════════

BIOLOGY_RENDERERS = {
    "cell_diagram":         render_cell_diagram,
    "dna_structure":        render_dna_structure,
    "cell_division":        render_cell_division,
    "heart_diagram":        render_heart_diagram,
    "nephron_diagram":      render_nephron_diagram,
    "neuron_diagram":       render_neuron_diagram,
    "food_web":             render_food_web,
    "food_chain":           render_food_chain,
    "ecological_pyramid":   render_ecological_pyramid,
}


def render_biology(subtype: str, params: Dict[str, Any],
                   canvas_w: int = 800, canvas_h: int = 600) -> str:
    renderer = BIOLOGY_RENDERERS.get(subtype)
    if not renderer:
        raise ValueError(
            f"Unknown biology subtype: '{subtype}'. "
            f"Supported: {list(BIOLOGY_RENDERERS.keys())}"
        )
    return renderer(params, canvas_w=canvas_w, canvas_h=canvas_h)
