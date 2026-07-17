"""
Chemistry Diagram Renderer.
Uses RDKit for organic structures (SMILES), matplotlib for orbital/reaction
coordinate diagrams, and svgwrite fallback for inorganic structures.
"""
from __future__ import annotations

import io
import math
from typing import Any, Dict, List, Optional, Tuple

import svgwrite

# ── RDKit (optional) ──────────────────────────────────────────────────────────
try:
    from rdkit import Chem
    from rdkit.Chem import AllChem
    from rdkit.Chem.Draw import rdMolDraw2D
    RDKIT_AVAILABLE = True
except ImportError:
    RDKIT_AVAILABLE = False

# ── matplotlib (used for graphs) ──────────────────────────────────────────────
import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["svg.fonttype"] = "none"   # embed text as <text> nodes, not paths
matplotlib.rcParams["svg.hashsalt"] = "paperdeck"   # deterministic element ids
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

from diagrams.service.svgtext import fold, make_text, tspan_markup
from diagrams.service.shared.xygraph import render_annotated_xy_graph
from diagrams.schemas.chemistry import (
    OrganicStructureSchema, InorganicStructureSchema,
    OrbitalDiagramSchema, ReactionCoordinateSchema,
    ElectrochemicalCellSchema, EquilibriumGraphSchema, TitrationCurveSchema,
    SN1SN2MechanismSchema, NewmanProjectionSchema, ConformationalIsomersSchema,
    CrystalLatticeSchema, VseprShapeSchema, MoDiagramSchema,
    PhaseDiagramSchema, HaworthFischerSchema, LabApparatusSchema,
    ReactionSchemeSchema, ReactionSpecies, CrystalFieldSplittingSchema,
    KineticsGraphSchema, ColligativeGraphSchema, OrganicMechanismSchema,
    HybridisationOverlapSchema, AdsorptionIsothermSchema,
    ElectrolyticCellSchema, IonicLatticeSchema, SolidDefectsSchema,
    ComplexIsomerismSchema, PolymerStructureSchema, MetallurgyFlowchartSchema,
    IndustrialProcessSchema, ProteinStructureSchema, HydrogenBondingSchema,
    ResonanceStructuresSchema, FreeRadicalMechanismSchema,
)

STROKE = "black"
FONT_SZ = 14
FONT = "Arial, sans-serif"

# Shared palette for the 3D / schematic renderers below
C_CORNER = "#2980B9"    # corner lattice points
C_FACE = "#27AE60"      # face-centred lattice points
C_BODY = "#E74C3C"      # body-centre / interior lattice points
C_BOND = "#34495E"
C_LONE_PAIR = "#8E44AD"
C_GLASS = "#2C3E50"
C_LIQUID = "#AED6F1"
C_WATER = "#3498DB"
C_HEAT = "#E67E22"
C_ANNOT = "#566573"


def _text(dwg, txt, x, y, anchor="middle", size=FONT_SZ, bold=False, fill="black"):
    weight = "bold" if bold else "normal"
    dwg.add(make_text(dwg, txt, (x, y), font_size=size, font_family=FONT,
                      text_anchor=anchor, font_weight=weight, fill=fill))


def _fig_to_svg(fig, bbox: Optional[str] = "tight") -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="svg", bbox_inches=bbox, facecolor="white", dpi=100,
                metadata={"Date": None})   # no timestamp → deterministic output
    buf.seek(0)
    svg = buf.getvalue().decode("utf-8")
    plt.close(fig)
    return svg


# ── 1. Organic Structure ──────────────────────────────────────────────────────

def render_organic_structure(data: Dict[str, Any], canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = OrganicStructureSchema(**data)
    name = schema.name or ""

    if RDKIT_AVAILABLE:
        return _render_smiles_rdkit(schema.smiles, name, canvas_w, canvas_h)
    else:
        return _render_smiles_fallback(
            schema.smiles, name, canvas_w, canvas_h,
            show_eas=schema.show_eas_positions,
            activated=schema.activated_positions or [],
        )


def _render_smiles_rdkit(smiles: str, name: str, canvas_w: int, canvas_h: int) -> str:
    """Render SMILES using RDKit MolDraw2DSVG."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"Invalid SMILES string: '{smiles}'")
    # Compute 2D coordinates
    AllChem.Compute2DCoords(mol)
    drawer = rdMolDraw2D.MolDraw2DSVG(canvas_w, canvas_h)
    drawer.drawOptions().addBondIndices = False
    drawer.drawOptions().addAtomIndices = False
    drawer.drawOptions().useBWAtomPalette()
    drawer.DrawMolecule(mol)
    drawer.FinishDrawing()
    svg = drawer.GetDrawingText()
    if name:
        # Inject name label at bottom. Compound names carry subscripts (H₂SO₄), which Arial
        # cannot render and cairosvg will not substitute — see diagrams/service/svgtext.py.
        label = f'<text x="{canvas_w // 2}" y="{canvas_h - 12}" ' \
                f'font-size="14" font-family="{FONT}" text-anchor="middle">' \
                f'{tspan_markup(name, 14)}</text>'
        svg = svg.replace("</svg>", label + "\n</svg>")
    return svg


# ─── Substituent chain database ───────────────────────────────────────────────
# Each entry: SMILES fragment (as it appears before OR after c1ccccc1) →
#   list of (atom_label, bond_from_previous, branches)
#   branches = list of (branch_label, bond_order)
_SUB_CHAINS: Dict[str, List] = {
    # ── simple atoms ──────────────────────────────────────────────────────────
    "O":              [("OH",    1, [])],
    "N":              [("NH₂",   1, [])],
    "Cl":             [("Cl",    1, [])],
    "Br":             [("Br",    1, [])],
    "F":              [("F",     1, [])],
    "I":              [("I",     1, [])],
    # ── alkyl ────────────────────────────────────────────────────────────────
    "C":              [("CH₃",   1, [])],
    "CC":             [("CH₂",   1, []), ("CH₃",   1, [])],
    "CCC":            [("CH₂",   1, []), ("CH₂",   1, []), ("CH₃", 1, [])],
    # ── nitro ────────────────────────────────────────────────────────────────
    "[N+](=O)[O-]":   [("NO₂",   1, [])],
    "N(=O)=O":        [("N",     1, [("O", 2), ("O", 2)])],
    # ── carboxylic acid  (suffix: C(=O)O  / prefix: OC(=O) both → COOH) ────
    "C(=O)O":         [("C",     1, [("O", 2)]), ("OH",   1, [])],
    "C(=O)OH":        [("C",     1, [("O", 2)]), ("OH",   1, [])],
    # OC(=O) prefix form (e.g. OC(=O)c1ccccc1 = benzoic acid)
    # ring→C(=O)→OH  so from ring outward: C[=O branch], OH
    "OC(=O)":         [("C",     1, [("O", 2)]), ("OH",   1, [])],
    # ── aldehyde ─────────────────────────────────────────────────────────────
    "C=O":            [("CHO",   1, [])],
    "C(=O)":          [("CHO",   1, [])],
    # ── ether / ester ────────────────────────────────────────────────────────
    "OC":             [("O",     1, []), ("CH₃",   1, [])],
    "OCC":            [("O",     1, []), ("CH₂",   1, []), ("CH₃", 1, [])],
    # Phenyl acetate:  CC(=O)Oc1ccccc1 → prefix CC(=O)O → ring outward: O–C(=O)–CH₃
    "CC(=O)O":        [("O",     1, []), ("C",     1, [("O", 2)]), ("CH₃", 1, [])],
    # ── ketone ───────────────────────────────────────────────────────────────
    "C(=O)C":         [("C",     1, [("O", 2)]), ("CH₃",  1, [])],
    # ── amide (acetanilide)  NC(=O)Cc1ccccc1 ─────────────────────────────────
    "NC(=O)C":        [("NH",    1, []), ("C",     1, [("O", 2)]), ("CH₃", 1, [])],
    # ── cyano ────────────────────────────────────────────────────────────────
    "C#N":            [("C",     1, []), ("N",     3, [])],
    # ── sulfonic acid ────────────────────────────────────────────────────────
    "S(=O)(=O)O":     [("S",     1, [("O", 2), ("O", 2)]), ("OH", 1, [])],
    # ── amide ─────────────────────────────────────────────────────────────────
    "C(=O)N":         [("C",     1, [("O", 2)]), ("NH₂",  1, [])],
    # ── hydroxyl variants ────────────────────────────────────────────────────
    "[OH]":           [("OH",    1, [])],
}


def _parse_benzene_smiles(smiles: str) -> dict:
    """Return dict with has_benzene, substituent_smiles, is_prefix."""
    import re
    info: dict = {"has_benzene": False, "substituent_smiles": None, "is_prefix": True}
    m = re.match(r"^(.*?)c1ccccc1(.*)$", smiles, re.DOTALL)
    if not m:
        return info
    info["has_benzene"] = True
    prefix, suffix = m.group(1).strip(), m.group(2).strip("()")
    if prefix:
        info["substituent_smiles"] = prefix
        info["is_prefix"] = True
    elif suffix:
        info["substituent_smiles"] = suffix
        info["is_prefix"] = False
    return info


def _chain_for(fragment: str) -> list:
    """Look up chain spec; fall back to plain text label."""
    if fragment in _SUB_CHAINS:
        return _SUB_CHAINS[fragment]
    clean = fragment.strip("()")
    if clean in _SUB_CHAINS:
        return _SUB_CHAINS[clean]
    return [(fragment, 1, [])]   # unknown → show as-is


def _draw_benzene_ring_mpl(ax, cx: float, cy: float, r: float,
                           eas_positions: bool = False,
                           activated: List[str] | None = None):
    """Draw Kekulé benzene (flat-top hexagon) on a matplotlib Axes."""
    activated = activated or []
    n = 6
    # Flat-top: vertex 0 at angle 0 (rightmost), going CCW
    angles = [k * math.pi / 3 for k in range(n)]   # 0°,60°,120°,180°,240°,300°
    verts = [(cx + r * math.cos(a), cy + r * math.sin(a)) for a in angles]

    # Outer hexagon edges
    xs = [v[0] for v in verts] + [verts[0][0]]
    ys = [v[1] for v in verts] + [verts[0][1]]
    ax.plot(xs, ys, "k-", linewidth=2.1, solid_capstyle="round", zorder=2)

    # Inner double-bond lines on alternating edges 0→1, 2→3, 4→5
    db_inset = 0.105 * r
    db_shrink = 0.20
    for i in (0, 2, 4):
        x1, y1 = verts[i]
        x2, y2 = verts[(i + 1) % n]
        dx, dy = x2 - x1, y2 - y1
        length = math.hypot(dx, dy)
        ux, uy = dx / length, dy / length
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        nx, ny = cx - mx, cy - my
        nn = math.hypot(nx, ny) or 1
        nx, ny = nx / nn, ny / nn
        ox, oy = nx * db_inset, ny * db_inset
        s = db_shrink * length
        ax.plot([x1 + ox + ux * s, x2 + ox - ux * s],
                [y1 + oy + uy * s, y2 + oy - uy * s],
                "k-", linewidth=1.7, solid_capstyle="round", zorder=2)

    # EAS position labels (ortho=vertices 1,5; meta=vertices 2,4; para=vertex 3)
    if eas_positions:
        eas_map = {1: "o", 2: "m", 3: "p", 4: "m", 5: "o"}
        for vi, tag in eas_map.items():
            vx, vy = verts[vi]
            outward_x = (vx - cx) / r * 0.32 * r
            outward_y = (vy - cy) / r * 0.32 * r
            lx, ly = vx + outward_x, vy + outward_y
            color = "#cc0000" if tag in activated else "#555555"
            fs = 10 if tag not in activated else 11
            fw = "bold" if tag in activated else "normal"
            ax.text(lx, ly, tag, ha="center", va="center", fontsize=fs,
                    fontweight=fw, color=color, zorder=5)

    return verts, angles


def _draw_bond_mpl(ax, x1, y1, x2, y2, bond_order: int):
    """Draw a single/double/triple bond line."""
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy)
    if length < 0.01:
        return
    ux, uy = dx / length, dy / length
    px, py = -uy, ux   # perpendicular

    lw = 1.6
    if bond_order == 1:
        ax.plot([x1, x2], [y1, y2], "k-", linewidth=lw, zorder=1)
    elif bond_order == 2:
        off = 0.055
        ax.plot([x1 + px*off, x2 + px*off], [y1 + py*off, y2 + py*off], "k-", linewidth=1.4, zorder=1)
        ax.plot([x1 - px*off, x2 - px*off], [y1 - py*off, y2 - py*off], "k-", linewidth=1.4, zorder=1)
    elif bond_order == 3:
        off = 0.07
        ax.plot([x1, x2], [y1, y2], "k-", linewidth=1.4, zorder=1)
        ax.plot([x1 + px*off, x2 + px*off], [y1 + py*off, y2 + py*off], "k-", linewidth=1.3, zorder=1)
        ax.plot([x1 - px*off, x2 - px*off], [y1 - py*off, y2 - py*off], "k-", linewidth=1.3, zorder=1)


def _draw_chain_from(ax, start_x: float, start_y: float, chain: list,
                     direction: float = 0.0, step: float = 0.82):
    """Draw a substituent chain extending in `direction` (radians) from start."""
    cur_x, cur_y = start_x, start_y
    dir_x, dir_y = math.cos(direction), math.sin(direction)
    perp_x, perp_y = -dir_y, dir_x   # perpendicular for branch direction
    b_step = step * 0.70

    for atom_label, bond_from_prev, branches in chain:
        nx = cur_x + dir_x * step
        ny = cur_y + dir_y * step

        _draw_bond_mpl(ax, cur_x, cur_y, nx, ny, bond_from_prev)

        # Branches (alternating up/down perpendicular to chain)
        bd = 1
        for b_label, b_bond in branches:
            bx = nx + perp_x * b_step * bd
            by = ny + perp_y * b_step * bd
            _draw_bond_mpl(ax, nx, ny, bx, by, b_bond)
            ax.text(bx, by, b_label, ha="center", va="center", fontsize=10,
                    zorder=4,
                    bbox=dict(boxstyle="round,pad=0.1", fc="white", ec="none"))
            bd = -bd

        ax.text(nx, ny, atom_label, ha="center", va="center", fontsize=11,
                zorder=4,
                bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none"))

        cur_x, cur_y = nx, ny


def _render_smiles_fallback(smiles: str, name: str, canvas_w: int, canvas_h: int,
                             show_eas: bool = False,
                             activated: List[str] | None = None) -> str:
    """Render a proper organic structural diagram using matplotlib (no RDKit)."""
    info = _parse_benzene_smiles(smiles)

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100), dpi=100)
    ax.set_aspect("equal")
    ax.axis("off")

    if info["has_benzene"]:
        chain: list = []
        sub = info["substituent_smiles"]
        if sub:
            chain = _chain_for(sub)

        ring_r = 1.0
        chain_len = len(chain)
        sub_w = chain_len * 0.85 + 0.3 if chain else 0.0
        total_w = ring_r * 2 + sub_w + 0.6
        ring_cx = -sub_w / 2
        ring_cy = 0.0

        half_w = total_w / 2 + 0.5
        half_h = ring_r + 1.2 + (0.6 if name else 0.3)
        ax.set_xlim(-half_w, half_w)
        ax.set_ylim(-half_h, half_h)

        verts, angles = _draw_benzene_ring_mpl(
            ax, ring_cx, ring_cy, ring_r,
            eas_positions=show_eas,
            activated=activated,
        )

        if chain:
            # Attach substituent at rightmost vertex (vertex 0, angle 0°)
            vx, vy = verts[0]
            _draw_chain_from(ax, vx, vy, chain, direction=0.0, step=0.82)

        if name:
            ax.text(ring_cx, -half_h + 0.25, name,
                    ha="center", va="bottom", fontsize=11, style="italic")
    else:
        # Non-benzene: show SMILES + name as plain text
        ax.set_xlim(-3, 3)
        ax.set_ylim(-2, 2)
        ax.text(0, 0.3, smiles, ha="center", va="center", fontsize=11,
                fontfamily="monospace")
        if name:
            ax.text(0, -0.4, name, ha="center", va="center", fontsize=11, style="italic")

    buf = io.BytesIO()
    fig.savefig(buf, format="svg", bbox_inches="tight", facecolor="white", pad_inches=0.25,
                metadata={"Date": None})   # no timestamp → deterministic output
    buf.seek(0)
    svg = buf.getvalue().decode("utf-8")
    plt.close(fig)
    return svg


# ── 2. Inorganic Structure ────────────────────────────────────────────────────

def render_inorganic_structure(data: Dict[str, Any], canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = InorganicStructureSchema(**data)
    dwg = svgwrite.Drawing(size=(f"{canvas_w}px", f"{canvas_h}px"),
                           viewBox=f"0 0 {canvas_w} {canvas_h}")
    dwg.add(dwg.rect(insert=(0, 0), size=(f"{canvas_w}px", f"{canvas_h}px"), fill="white"))

    atoms = schema.atoms
    bonds = schema.bonds
    n = len(atoms)
    cx, cy = canvas_w / 2, canvas_h / 2
    arm = min(canvas_w, canvas_h) * 0.24   # bond arm length

    # ── Smart layout ──────────────────────────────────────────────────────────
    # Identify the central atom (most bonds). Put it at center; arrange others around it.
    bond_count = [0] * n
    for b in bonds:
        if b.from_atom < n:
            bond_count[b.from_atom] += 1
        if b.to_atom < n:
            bond_count[b.to_atom] += 1

    atom_positions = [None] * n

    # Use explicit coordinates if provided
    explicit = all(a.x is not None and a.y is not None for a in atoms)
    if explicit:
        for i, atom in enumerate(atoms):
            atom_positions[i] = (cx + float(atom.x) * arm / 2,
                                 cy - float(atom.y) * arm / 2)
    else:
        # Find central atom (highest bond count); break ties by first occurrence
        center_idx = max(range(n), key=lambda i: bond_count[i])
        atom_positions[center_idx] = (cx, cy)

        # Place ligands evenly around center in angular order
        ligands = [i for i in range(n) if i != center_idx]
        n_lig = len(ligands)
        if n_lig == 0:
            pass   # single atom
        elif n_lig == 1:
            atom_positions[ligands[0]] = (cx + arm, cy)
        elif n_lig == 2:
            # Bent molecule (e.g. H₂O ~104°) or linear (CO₂ 180°)
            # Use 120° spacing by default (looks clean; actual angle not encoded)
            for k, lig_i in enumerate(ligands):
                angle = math.pi / 6 + k * math.pi * 2 / 3   # 30°, 150°
                atom_positions[lig_i] = (cx + arm * math.cos(angle),
                                         cy - arm * math.sin(angle))
        else:
            # Spread evenly
            for k, lig_i in enumerate(ligands):
                angle = -math.pi / 2 + k * 2 * math.pi / n_lig
                atom_positions[lig_i] = (cx + arm * math.cos(angle),
                                         cy - arm * math.sin(angle))

        # Any atom still unpositioned (multiple centers) → fall back to ring
        for i in range(n):
            if atom_positions[i] is None:
                angle = 2 * math.pi * i / n - math.pi / 2
                atom_positions[i] = (cx + arm * math.cos(angle),
                                     cy - arm * math.sin(angle))

    # ── Draw bonds ────────────────────────────────────────────────────────────
    for bond in bonds:
        if bond.from_atom < n and bond.to_atom < n:
            x1, y1 = atom_positions[bond.from_atom]
            x2, y2 = atom_positions[bond.to_atom]
            _draw_bond(dwg, x1, y1, x2, y2, bond.bond_type)

    # ── Draw atoms ────────────────────────────────────────────────────────────
    for i, (atom, pos) in enumerate(zip(atoms, atom_positions)):
        ax, ay = pos
        label = atom.label or atom.symbol
        r_circle = max(16, len(label) * 6 + 4)   # scale circle to label length
        dwg.add(dwg.circle(center=(ax, ay), r=r_circle,
                           fill="white", stroke=STROKE, stroke_width=1.5))
        _text(dwg, label, ax, ay + 5, size=15, bold=True)
        if atom.charge:
            _text(dwg, atom.charge, ax + r_circle - 2, ay - r_circle + 6, size=10)

    # ── Title ─────────────────────────────────────────────────────────────────
    if schema.title:
        _text(dwg, schema.title, canvas_w / 2, 30, size=16, bold=True)

    return dwg.tostring()


def _draw_bond(dwg, x1, y1, x2, y2, bond_type):
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy)
    if length < 1:
        return
    # Shorten to not overlap atom circles
    shrink = 22
    ux, uy = dx / length, dy / length
    sx1, sy1 = x1 + ux * shrink, y1 + uy * shrink
    sx2, sy2 = x2 - ux * shrink, y2 - uy * shrink
    px, py = -uy * 4, ux * 4  # perpendicular offset for double/triple bonds

    if bond_type == "single":
        dwg.add(dwg.line(start=(sx1, sy1), end=(sx2, sy2),
                         stroke=STROKE, stroke_width=2))
    elif bond_type == "double":
        dwg.add(dwg.line(start=(sx1 + px, sy1 + py), end=(sx2 + px, sy2 + py),
                         stroke=STROKE, stroke_width=2))
        dwg.add(dwg.line(start=(sx1 - px, sy1 - py), end=(sx2 - px, sy2 - py),
                         stroke=STROKE, stroke_width=2))
    elif bond_type == "triple":
        dwg.add(dwg.line(start=(sx1, sy1), end=(sx2, sy2),
                         stroke=STROKE, stroke_width=2))
        for sign in (1, -1):
            dwg.add(dwg.line(start=(sx1 + sign * px * 2, sy1 + sign * py * 2),
                             end=(sx2 + sign * px * 2, sy2 + sign * py * 2),
                             stroke=STROKE, stroke_width=2))
    elif bond_type == "dative":
        # dashed arrow bond
        dwg.add(dwg.line(start=(sx1, sy1), end=(sx2, sy2),
                         stroke=STROKE, stroke_width=2, stroke_dasharray="5,3"))


# ── 3. Orbital Diagram ────────────────────────────────────────────────────────

def render_orbital_diagram(data: Dict[str, Any], canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = OrbitalDiagramSchema(**data)

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100), dpi=100)
    ax.set_xlim(0, 10)
    ax.set_ylim(-0.5, len(schema.electron_config) + 0.5)
    ax.axis("off")
    ax.set_title(f"Orbital Diagram: {schema.element}", fontsize=14, pad=10)

    box_w, box_h = 0.6, 0.35
    for row_idx, shell in enumerate(schema.electron_config):
        y = row_idx
        n_boxes = shell.sublevel_count
        x_start = 1.5
        # Shell label
        ax.text(0.5, y, shell.shell, va="center", ha="center", fontsize=12, fontweight="bold")
        # Draw orbital boxes
        electrons_placed = 0
        for box_i in range(n_boxes):
            bx = x_start + box_i * (box_w + 0.15)
            rect = mpatches.FancyBboxPatch((bx, y - box_h / 2), box_w, box_h,
                                           boxstyle="square,pad=0",
                                           linewidth=1.5, edgecolor="black", facecolor="white")
            ax.add_patch(rect)
            # Electrons (Hund's rule: fill once each box, then pair)
            # First pass: one electron per box (spin-up ↑)
            if electrons_placed < shell.electrons:
                ax.annotate("↑", xy=(bx + box_w * 0.3, y),
                            fontsize=14, ha="center", va="center")
                electrons_placed += 1
        # Second pass: pair electrons (spin-down ↓)
        electrons_placed_p2 = shell.sublevel_count  # already placed 1 each
        for box_i in range(n_boxes):
            if electrons_placed_p2 < shell.electrons:
                bx = x_start + box_i * (box_w + 0.15)
                ax.annotate("↓", xy=(bx + box_w * 0.7, y),
                            fontsize=14, ha="center", va="center")
                electrons_placed_p2 += 1

    fig.tight_layout()
    return _fig_to_svg(fig)


# ── 4. Reaction Coordinate Graph ──────────────────────────────────────────────

def render_reaction_coordinate_graph(data: Dict[str, Any], canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = ReactionCoordinateSchema(**data)

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100), dpi=100)

    # Points on the reaction coordinate curve
    E_react = schema.reactant_energy
    E_prod = schema.product_energy
    E_ts = E_react + schema.activation_energy   # transition state energy

    x = np.linspace(0, 10, 500)

    # Build smooth curve using a cubic Bezier-like profile
    # Divide into 3 segments: reactant plateau → peak → product plateau
    def curve(t):
        # Normalized t ∈ [0, 1]
        # Use sigmoid-like transitions
        if t < 0.1:
            return E_react
        elif t < 0.5:
            s = (t - 0.1) / 0.4
            return E_react + (E_ts - E_react) * (3 * s ** 2 - 2 * s ** 3)
        elif t < 0.9:
            s = (t - 0.5) / 0.4
            return E_ts + (E_prod - E_ts) * (3 * s ** 2 - 2 * s ** 3)
        else:
            return E_prod

    x_norm = x / 10
    y = np.array([curve(t) for t in x_norm])

    ax.plot(x, y, "k-", linewidth=2.5)

    # Reactant & product horizontal dashed lines
    ax.axhline(y=E_react, xmin=0, xmax=0.15, color="black", linestyle="--", linewidth=1)
    ax.axhline(y=E_prod, xmin=0.85, xmax=1.0, color="black", linestyle="--", linewidth=1)

    # Labels
    ax.text(0.3, E_react, schema.reactant_label, fontsize=11, ha="center",
            va="bottom" if E_react < E_ts else "top")
    ax.text(9.7, E_prod, schema.product_label, fontsize=11, ha="center",
            va="bottom" if E_prod < E_ts else "top")
    ax.text(5.0, E_ts + (abs(E_ts) * 0.03 + 3), schema.transition_state_label,
            fontsize=10, ha="center")
    ax.plot(5.0, E_ts, "ko", markersize=5)  # TS point

    # ΔH arrow
    if schema.label_delta_h:
        dH = E_prod - E_react
        ax.annotate("", xy=(8.5, E_prod), xytext=(8.5, E_react),
                    arrowprops=dict(arrowstyle="<->", color="black"))
        label = f"ΔH = {dH:+.0f} kJ/mol"
        ax.text(9.0, (E_react + E_prod) / 2, label, fontsize=10, va="center")

    # Ea arrow
    if schema.label_ea:
        ax.annotate("", xy=(4.0, E_ts), xytext=(4.0, E_react),
                    arrowprops=dict(arrowstyle="<->", color="black"))
        ax.text(3.5, (E_react + E_ts) / 2, f"Ea = {schema.activation_energy:.0f} kJ/mol",
                fontsize=10, va="center", ha="right")

    ax.set_xlabel("Reaction Coordinate", fontsize=12)
    ax.set_ylabel("Potential Energy (kJ/mol)", fontsize=12)
    ax.set_title("Reaction Energy Profile", fontsize=14)
    ax.grid(False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    fig.tight_layout()
    return _fig_to_svg(fig)


# ── 5. Electrochemical Cell ───────────────────────────────────────────────────

def _ion_charge(ion_label: str) -> int:
    """Electrons transferred, read off the ion's own charge: Zn²⁺ → 2, Ag⁺ → 1.
    The half-equation has to balance, and 'Zn → Zn²⁺ + e⁻' does not."""
    digits = "".join(fold(ch) for ch in ion_label if ch in "⁰¹²³⁴⁵⁶⁷⁸⁹")
    n = int(digits) if digits else 1
    return max(n, 1)


def _electrons(n: int) -> str:
    return "e⁻" if n == 1 else f"{n}e⁻"


def render_electrochemical_cell(data: Dict[str, Any],
                                 canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = ElectrochemicalCellSchema(**data)

    fig, ax = plt.subplots(figsize=(10, 6.4))
    ax.set_xlim(-0.4, 10.4)
    ax.set_ylim(0, 6.4)
    ax.set_aspect("equal")
    ax.axis("off")

    B_W, B_H, B_Y = 2.6, 2.7, 0.80         # beaker width / height / floor
    ROD_TOP, WIRE_Y = 4.30, 5.40
    liquid_top = B_Y + B_H

    def _beaker(x0, solution_label, ion_label, electrode_label, is_anode):
        ax.add_patch(mpatches.FancyBboxPatch(
            (x0, B_Y), B_W, B_H, boxstyle="square,pad=0", edgecolor="black",
            facecolor="#d0e8ff", linewidth=1.8, zorder=2))
        ex = x0 + B_W / 2
        ax.plot([ex, ex], [B_Y + 0.25, ROD_TOP], color="#555555", linewidth=5,
                solid_capstyle="round", zorder=3)
        # Label OUTWARD from the rod: the rod and the wire above it both sit on ex, so
        # anything centred there is drawn straight through.
        ax.text(ex - 0.25 if is_anode else ex + 0.25, 4.72, electrode_label,
                ha="right" if is_anode else "left", va="center", fontsize=11,
                fontweight="bold", color="red" if is_anode else "blue")
        # Solution and ion flank the rod rather than sitting under it.
        ax.text(x0 + B_W * 0.27, B_Y + B_H * 0.62, solution_label, ha="center",
                va="center", fontsize=11, color="#003399")
        ax.text(x0 + B_W * 0.75, B_Y + B_H * 0.62, ion_label, ha="center",
                va="center", fontsize=11, color="#003399")
        return ex

    rod_l = _beaker(0.5, schema.anode_solution, schema.anode_ion,
                    f"{schema.anode_material} (Anode −)", True)
    rod_r = _beaker(6.9, schema.cathode_solution, schema.cathode_ion,
                    f"{schema.cathode_material} (Cathode +)", False)

    # ── external circuit: both verticals land on their own electrode ──────────
    ax.plot([rod_l, rod_l], [ROD_TOP, WIRE_Y], color="black", lw=2, zorder=3)
    ax.plot([rod_r, rod_r], [ROD_TOP, WIRE_Y], color="black", lw=2, zorder=3)
    ax.plot([rod_l, rod_r], [WIRE_Y, WIRE_Y], color="black", lw=2, zorder=3)

    if schema.show_current:
        # Electrons leave the anode and travel through the wire to the cathode: left → right.
        ax.annotate("", xy=(5.9, WIRE_Y), xytext=(4.1, WIRE_Y),
                    arrowprops=dict(arrowstyle="-|>", color="#E67E22", lw=2.2))
        ax.text(5.0, WIRE_Y + 0.16, "e⁻ flow", ha="center", va="bottom",
                fontsize=11, color="#E67E22", fontweight="bold")

    if schema.show_salt_bridge:
        # Inverted-U tube whose legs actually dip into both solutions.
        rail_y, dip_y = 3.95, liquid_top - 0.55
        lx, rx = 2.90, 7.10
        path_x, path_y = [lx, lx, rx, rx], [dip_y, rail_y, rail_y, dip_y]
        ax.plot(path_x, path_y, color="black", linewidth=11,
                solid_joinstyle="round", zorder=4)
        ax.plot(path_x, path_y, color="#ffffcc", linewidth=8,
                solid_joinstyle="round", zorder=5)
        # Label sits clear ABOVE the rail: the tube is far too thin to print text inside.
        ax.text((lx + rx) / 2, rail_y + 0.16, "Salt Bridge", ha="center", va="bottom",
                fontsize=10, zorder=6)

    if schema.emf is not None:
        # Hangs in the empty middle of the circuit. Sharing the title's y is what made
        # the two illegible.
        ax.text(5.0, 4.85, f"E°cell = {schema.emf:.2f} V", ha="center", va="center",
                fontsize=12, color="darkgreen", fontweight="bold", zorder=6,
                bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                          edgecolor="darkgreen", linewidth=1.2))

    if schema.show_half_reactions:
        n_a = _ion_charge(schema.anode_ion)
        n_c = _ion_charge(schema.cathode_ion)
        ax.text(1.8, 0.62,
                f"Anode: {schema.anode_material} → {schema.anode_ion} + {_electrons(n_a)}",
                ha="center", va="top", fontsize=9.5, color="darkred")
        ax.text(8.2, 0.62,
                f"Cathode: {schema.cathode_ion} + {_electrons(n_c)} → {schema.cathode_material}",
                ha="center", va="top", fontsize=9.5, color="darkblue")

    ax.set_title(schema.cell_name, fontsize=14, fontweight="bold", pad=8)
    fig.tight_layout()
    return _fig_to_svg(fig)


# ── 6. Equilibrium Concentration Graph ───────────────────────────────────────

def render_equilibrium_graph(data: Dict[str, Any],
                              canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = EquilibriumGraphSchema(**data)

    fig, ax = plt.subplots(figsize=(7, 4.5))

    t = np.linspace(0, 1, 400)
    teq = schema.equilibrium_time

    # Sigmoid-style approach: reactants decrease, products increase, then plateau
    def _sig(t_arr, t_eq, v0, v_eq):
        """Smooth logistic transition from v0 → v_eq centred at t_eq."""
        k = 20.0
        return v_eq + (v0 - v_eq) / (1 + np.exp(k * (t_arr - t_eq)))

    colors_r = ["#d62728", "#ff7f0e", "#9467bd"]
    colors_p = ["#1f77b4", "#2ca02c", "#8c564b"]

    # reactants start high (1.0), drop to some lower value
    for i, lbl in enumerate(schema.reactant_labels):
        v_eq = 0.3 + 0.1 * i
        y = _sig(t, teq, 1.0, v_eq)
        ax.plot(t, y, color=colors_r[i % len(colors_r)], lw=2, label=lbl)

    # products start low (0.0), rise to some higher value
    for i, lbl in enumerate(schema.product_labels):
        v_eq = 0.55 + 0.1 * i
        y = _sig(t, teq, 0.0, v_eq)
        ax.plot(t, y, color=colors_p[i % len(colors_p)], lw=2,
                linestyle="--", label=lbl)

    # equilibrium vertical dashed line
    ax.axvline(teq, color="gray", linestyle=":", lw=1.5)
    ax.text(teq + 0.02, 0.95, "Equilibrium", fontsize=10, va="top", color="gray")

    if schema.show_kc_marker:
        ax.text(teq + 0.04, 0.05, "Kc established", fontsize=9,
                color="#444444", style="italic")

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1.1)
    ax.set_xlabel(schema.x_label, fontsize=11)
    ax.set_ylabel(schema.y_label, fontsize=11)
    if schema.title:
        ax.set_title(schema.title, fontsize=13, fontweight="bold")
    ax.legend(fontsize=10, loc="center right")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    # remove numeric x-ticks (time is qualitative)
    ax.set_xticks([0, teq, 1.0])
    ax.set_xticklabels(["0", "t_eq", "∞"])
    ax.set_yticks([])

    fig.tight_layout()
    return _fig_to_svg(fig)


# ── 7. Titration Curve ────────────────────────────────────────────────────────

def render_titration_curve(data: Dict[str, Any],
                            canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = TitrationCurveSchema(**data)

    fig, ax = plt.subplots(figsize=(7, 5))

    # volume axis (0 → 1.5 × equivalence point)
    v = np.linspace(0, 1.5, 600)
    veq = 1.0   # normalised equivalence point volume

    ph_start = schema.initial_ph
    ph_end   = schema.final_ph
    ph_eq    = schema.equivalence_ph

    if schema.acid_type == "weak" or schema.base_type == "weak":
        # Buffer region: shallow rise before eq, steep jump at eq
        def _ph_weak(v_arr):
            ph = np.empty_like(v_arr)
            pre  = v_arr < veq
            post = v_arr >= veq
            # buffer zone: slow rise from ph_start to ~ph_eq-1
            ph[pre] = ph_start + (ph_eq - 1.0 - ph_start) * (v_arr[pre] / veq) ** 0.4
            # after equivalence: logistic jump
            k = 25.0
            x_post = (v_arr[post] - veq) / (0.5 * veq + 1e-9)
            ph[post] = ph_eq + (ph_end - ph_eq) / (1 + np.exp(-k * x_post + 3))
            return ph
        ph_vals = _ph_weak(v)
    else:
        # Strong acid–strong base: sharp sigmoid
        k = 30.0
        ph_vals = ph_start + (ph_end - ph_start) / (1 + np.exp(-k * (v - veq)))

    ax.plot(v, ph_vals, color="#1f77b4", lw=2.5)

    # equivalence point
    if schema.show_equivalence_point:
        ax.axvline(veq, color="gray", linestyle="--", lw=1.3)
        ax.axhline(ph_eq, color="gray", linestyle="--", lw=1.3)
        ax.plot(veq, ph_eq, "ko", markersize=7, zorder=5)
        ax.annotate(f"Eq. pt\npH = {ph_eq:.1f}", xy=(veq, ph_eq),
                    xytext=(veq + 0.06, ph_eq - 1.5),
                    fontsize=9,
                    arrowprops=dict(arrowstyle="->", color="black", lw=1))

    # half-equivalence point (weak acid: pKa marker)
    if schema.show_half_equivalence:
        v_half = veq / 2.0
        ph_half = float(np.interp(v_half, v, ph_vals))
        ax.plot(v_half, ph_half, "rs", markersize=7, zorder=5)
        ax.annotate(f"½ Eq. pt\npKa ≈ {ph_half:.1f}", xy=(v_half, ph_half),
                    xytext=(v_half + 0.06, ph_half + 0.8),
                    fontsize=9, color="red",
                    arrowprops=dict(arrowstyle="->", color="red", lw=1))

    ax.set_xlim(0, 1.5)
    ax.set_ylim(0, 14)
    ax.set_xlabel(f"Volume of {schema.titrant_label} added →", fontsize=11)
    ax.set_ylabel("pH", fontsize=12)
    title = schema.title or f"Titration of {schema.analyte_label} with {schema.titrant_label}"
    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.set_yticks(range(0, 15, 2))
    # remove x numeric ticks (volume is relative)
    ax.set_xticks([0, veq, 1.5])
    ax.set_xticklabels(["0", "Veq", "1.5Veq"])
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    fig.tight_layout()
    return _fig_to_svg(fig)


# ── SN1 / SN2 Mechanism ───────────────────────────────────────────────────────

def render_sn1_sn2_mechanism(data: Dict[str, Any],
                              canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = SN1SN2MechanismSchema(**data)
    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.axis("off")

    mech = schema.mechanism_type.upper()

    if mech == "SN2":
        # One-step concerted: Nu → [C] → LG on one row
        entities = [
            (1.2, 3.0, schema.nucleophile, "#2980B9"),
            (5.0, 3.0, f"[{schema.substrate}]‡", "#7D3C98"),
            (8.8, 3.0, schema.product, "#27AE60"),
        ]
        for ex, ey, label, color in entities:
            ax.text(ex, ey, label, ha="center", va="center", fontsize=11,
                    fontweight="bold", color=color,
                    bbox=dict(boxstyle="round,pad=0.4", facecolor="white",
                              edgecolor=color, linewidth=1.5))

        # Curved arrows: nucleophile attacks C, leaving group departs
        if schema.show_curved_arrows:
            _curved_arrow(ax, (2.0, 3.0), (3.6, 3.0), -0.35, "#2980B9")
            _curved_arrow(ax, (6.3, 3.0), (7.2, 3.0), -0.35, "#E74C3C")

        # LG product
        ax.text(8.8, 1.8, schema.leaving_group, ha="center", fontsize=10,
                color="#E74C3C",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="#FDEBD0",
                          edgecolor="#E74C3C", linewidth=1.2))

        ax.text(5.0, 5.2, "SN2 — Bimolecular Nucleophilic Substitution",
                ha="center", fontsize=10, fontweight="bold", color="#1A252F")
        ax.text(5.0, 4.6, "Concerted: inversion of configuration (Walden inversion)",
                ha="center", fontsize=8, color="gray")

        if schema.show_stereochemistry:
            ax.text(5.0, 1.0, "Configuration: INVERTED (backside attack)",
                    ha="center", fontsize=9, color="#7D3C98",
                    bbox=dict(boxstyle="round,pad=0.3", facecolor="#F5EEF8", alpha=0.9))

    else:  # SN1
        # Two steps: substrate → carbocation + LG → product + Nu
        ax.text(5.0, 5.3, "SN1 — Unimolecular Nucleophilic Substitution",
                ha="center", fontsize=10, fontweight="bold", color="#1A252F")
        ax.text(5.0, 4.8, "Stepwise: racemisation possible",
                ha="center", fontsize=8, color="gray")

        # Step 1
        ax.text(1.5, 3.5, schema.substrate, ha="center", fontsize=11,
                fontweight="bold", color="#1A5276",
                bbox=dict(boxstyle="round,pad=0.4", facecolor="white",
                          edgecolor="#1A5276", linewidth=1.5))
        ax.annotate("", xy=(3.8, 3.5), xytext=(2.7, 3.5),
                    arrowprops=dict(arrowstyle="-|>", color="black", lw=1.5))
        ax.text(3.4, 3.9, "Step 1\nionisation", ha="center", fontsize=7, color="gray")

        # Carbocation intermediate
        inter = schema.intermediate or "carbocation"
        ax.text(5.0, 3.5, inter, ha="center", fontsize=11,
                fontweight="bold", color="#E74C3C",
                bbox=dict(boxstyle="round,pad=0.4", facecolor="#FDEBD0",
                          edgecolor="#E74C3C", linewidth=1.5))
        ax.text(5.0, 2.9, "+  " + schema.leaving_group, ha="center",
                fontsize=10, color="#E74C3C")

        ax.annotate("", xy=(7.3, 3.5), xytext=(6.2, 3.5),
                    arrowprops=dict(arrowstyle="-|>", color="black", lw=1.5))
        ax.text(6.7, 3.9, "Step 2\n" + schema.nucleophile, ha="center", fontsize=7, color="gray")

        # Product
        ax.text(8.5, 3.5, schema.product, ha="center", fontsize=11,
                fontweight="bold", color="#27AE60",
                bbox=dict(boxstyle="round,pad=0.4", facecolor="white",
                          edgecolor="#27AE60", linewidth=1.5))

        if schema.show_stereochemistry:
            ax.text(5.0, 1.5, "Configuration: RACEMIC mixture (planar carbocation)",
                    ha="center", fontsize=9, color="#7D3C98",
                    bbox=dict(boxstyle="round,pad=0.3", facecolor="#F5EEF8", alpha=0.9))

    title = schema.title or f"{mech} Reaction Mechanism"
    ax.set_title(title, fontsize=12, fontweight="bold", y=0.97)
    fig.tight_layout()
    return _fig_to_svg(fig)


# ── Newman Projection ─────────────────────────────────────────────────────────

def render_newman_projection(data: Dict[str, Any],
                              canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = NewmanProjectionSchema(**data)
    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))
    ax.set_aspect("equal")
    ax.set_xlim(-4, 4)
    ax.set_ylim(-4, 4)
    ax.axis("off")

    cx, cy = 0.0, 0.0
    R_outer = 1.5     # back carbon bond length
    R_sub = 2.2       # substituent label distance
    dihedral = math.radians(schema.dihedral_angle)

    # Front carbon: filled circle
    front_circle = plt.Circle((cx, cy), 0.45, color="#2980B9", zorder=5)
    ax.add_patch(front_circle)
    ax.text(cx, cy, schema.front_carbon, ha="center", va="center",
            fontsize=7, color="white", fontweight="bold", zorder=6)

    # Back carbon: ring
    back_ring = plt.Circle((cx, cy), R_outer, fill=False,
                            edgecolor="#E74C3C", linewidth=2.5, zorder=4)
    ax.add_patch(back_ring)

    # Front substituents (3, at 90°, 210°, 330° — i.e. 120° apart)
    front_angles = [np.pi / 2 + i * 2 * np.pi / 3 for i in range(3)]
    for i, angle in enumerate(front_angles):
        # Line from front carbon edge to substituent
        edge_x = 0.45 * np.cos(angle)
        edge_y = 0.45 * np.sin(angle)
        sub_x = R_sub * np.cos(angle)
        sub_y = R_sub * np.sin(angle)
        ax.plot([edge_x, sub_x * 0.9], [edge_y, sub_y * 0.9],
                color="#2980B9", linewidth=2, zorder=3)
        label = schema.front_substituents[i] if i < len(schema.front_substituents) else "H"
        ax.text(sub_x, sub_y, label, ha="center", va="center", fontsize=10,
                fontweight="bold", color="#1A5276")

    # Back substituents (offset by dihedral_angle)
    back_angles = [np.pi / 2 + dihedral + i * 2 * np.pi / 3 for i in range(3)]
    for i, angle in enumerate(back_angles):
        # Lines start at the outer ring
        ring_x = R_outer * np.cos(angle)
        ring_y = R_outer * np.sin(angle)
        sub_x = (R_outer + 0.7) * np.cos(angle)
        sub_y = (R_outer + 0.7) * np.sin(angle)
        ax.plot([ring_x, sub_x], [ring_y, sub_y],
                color="#E74C3C", linewidth=2, zorder=3)
        label = schema.back_substituents[i] if i < len(schema.back_substituents) else "H"
        ax.text(sub_x + 0.2 * np.cos(angle), sub_y + 0.2 * np.sin(angle),
                label, ha="center", va="center", fontsize=10,
                fontweight="bold", color="#922B21")

    # Dihedral angle annotation
    if schema.show_dihedral_annotation:
        ax.text(2.5, -3.2,
                f"Dihedral: {schema.dihedral_angle:.0f}°",
                ha="center", fontsize=9, color="#566573",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="#F2F3F4", alpha=0.8))

    if schema.conformation_label:
        ax.text(0, -3.5, schema.conformation_label, ha="center", fontsize=11,
                fontweight="bold", color="#1A252F")

    # Legend
    ax.text(-3.5, 3.5, "● = front C", fontsize=8, color="#2980B9")
    ax.text(-3.5, 3.0, "○ = back C", fontsize=8, color="#E74C3C")

    title = schema.title or f"Newman Projection: {schema.front_carbon}–{schema.back_carbon}"
    ax.set_title(title, fontsize=11, fontweight="bold")
    fig.tight_layout()
    return _fig_to_svg(fig)


# ── Conformational Isomers ────────────────────────────────────────────────────

def render_conformational_isomers(data: Dict[str, Any],
                                   canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = ConformationalIsomersSchema(**data)
    conformations = schema.conformations or (
        ["chair", "boat"] if schema.molecule_type == "cyclohexane" else ["staggered", "eclipsed"])
    n_conf = len(conformations)
    fig, axes = plt.subplots(1, n_conf, figsize=(canvas_w / 100, canvas_h / 100))
    if n_conf == 1:
        axes = [axes]

    def draw_chair(ax, substituents=None):
        """Draw a schematic chair conformation of cyclohexane."""
        # Chair: 6 carbons in zig-zag
        chair_pts = np.array([
            [0.0, 0.0], [1.0, 0.6], [2.0, 0.0], [3.0, 0.6],
            [2.5, 1.4], [0.5, 1.4],
        ])
        # Close ring
        xs = list(chair_pts[:, 0]) + [chair_pts[0, 0]]
        ys = list(chair_pts[:, 1]) + [chair_pts[0, 1]]
        ax.plot(xs, ys, "k-", linewidth=2.5)
        # Axial / equatorial bonds (simplified)
        if schema.show_axial_equatorial:
            for i, (px, py) in enumerate(chair_pts):
                if i % 2 == 0:
                    ax.plot([px, px], [py, py + 0.7], "b-", linewidth=1.5, alpha=0.7)
                    ax.plot([px, px + 0.3], [py, py - 0.5], "r-", linewidth=1.5, alpha=0.7)
                else:
                    ax.plot([px, px], [py, py - 0.7], "b-", linewidth=1.5, alpha=0.7)
                    ax.plot([px, px - 0.3], [py, py + 0.5], "r-", linewidth=1.5, alpha=0.7)
            # Legend
            ax.plot([], [], "b-", label="axial")
            ax.plot([], [], "r-", label="equatorial")
            ax.legend(fontsize=6, loc="lower right")
        ax.set_xlim(-0.5, 3.5)
        ax.set_ylim(-1, 2.5)

    def draw_boat(ax):
        """Draw a schematic boat conformation."""
        boat_pts = np.array([
            [0.0, 0.4], [1.0, 0.0], [2.0, 0.0], [3.0, 0.4],
            [2.5, 1.4], [0.5, 1.4],
        ])
        xs = list(boat_pts[:, 0]) + [boat_pts[0, 0]]
        ys = list(boat_pts[:, 1]) + [boat_pts[0, 1]]
        ax.plot(xs, ys, "k-", linewidth=2.5)
        ax.set_xlim(-0.5, 3.5)
        ax.set_ylim(-0.5, 2.2)

    def draw_staggered(ax):
        """Newman-like view of staggered ethane."""
        cx, cy = 1.5, 1.2
        angles_front = [np.pi / 2 + i * 2 * np.pi / 3 for i in range(3)]
        angles_back = [np.pi / 2 + np.pi / 3 + i * 2 * np.pi / 3 for i in range(3)]
        circle = plt.Circle((cx, cy), 0.6, fill=False, edgecolor="gray", linewidth=2)
        ax.add_patch(circle)
        dot = plt.Circle((cx, cy), 0.15, color="#2980B9")
        ax.add_patch(dot)
        for a in angles_front:
            ax.plot([cx + 0.15 * np.cos(a), cx + 0.9 * np.cos(a)],
                    [cy + 0.15 * np.sin(a), cy + 0.9 * np.sin(a)],
                    color="#2980B9", linewidth=2.5)
            ax.text(cx + 1.1 * np.cos(a), cy + 1.1 * np.sin(a), "H",
                    ha="center", va="center", fontsize=9, fontweight="bold")
        for a in angles_back:
            ax.plot([cx + 0.6 * np.cos(a), cx + 0.95 * np.cos(a)],
                    [cy + 0.6 * np.sin(a), cy + 0.95 * np.sin(a)],
                    color="#E74C3C", linewidth=2.5)
            ax.text(cx + 1.15 * np.cos(a), cy + 1.15 * np.sin(a), "H",
                    ha="center", va="center", fontsize=9, fontweight="bold", color="#922B21")
        ax.set_xlim(0, 3)
        ax.set_ylim(0, 2.5)

    def draw_eclipsed(ax):
        """Newman-like view of eclipsed ethane."""
        cx, cy = 1.5, 1.2
        angles = [np.pi / 2 + i * 2 * np.pi / 3 for i in range(3)]
        circle = plt.Circle((cx, cy), 0.6, fill=False, edgecolor="gray", linewidth=2)
        ax.add_patch(circle)
        dot = plt.Circle((cx, cy), 0.15, color="#2980B9")
        ax.add_patch(dot)
        for a in angles:
            ax.plot([cx + 0.15 * np.cos(a), cx + 0.9 * np.cos(a)],
                    [cy + 0.15 * np.sin(a), cy + 0.9 * np.sin(a)],
                    color="#2980B9", linewidth=2.5)
            ax.text(cx + 1.1 * np.cos(a), cy + 1.1 * np.sin(a), "H",
                    ha="center", va="center", fontsize=9, fontweight="bold")
            # Back bonds (slightly offset)
            ao = a + 0.08
            ax.plot([cx + 0.6 * np.cos(ao), cx + 0.95 * np.cos(ao)],
                    [cy + 0.6 * np.sin(ao), cy + 0.95 * np.sin(ao)],
                    color="#E74C3C", linewidth=2, alpha=0.6)
        ax.set_xlim(0, 3)
        ax.set_ylim(0, 2.5)

    draw_fn_map = {
        "chair": draw_chair,
        "boat": draw_boat,
        "staggered": draw_staggered,
        "eclipsed": draw_eclipsed,
    }

    for ax, conf in zip(axes, conformations):
        fn = draw_fn_map.get(conf.lower())
        if fn:
            fn(ax)
        ax.axis("off")
        ax.set_title(conf.replace("_", " ").title(), fontsize=10, fontweight="bold")

    title = schema.title or f"Conformational Isomers: {schema.molecule_type.title()}"
    fig.suptitle(title, fontsize=12, fontweight="bold")
    fig.tight_layout()
    return _fig_to_svg(fig)


# ── Crystal Lattice (Solid State) ─────────────────────────────────────────────

# z = atoms per unit cell, cn = coordination number, packing = % of space filled.
# End-centred cubic is only ever examined on Z, so cn/packing stay unset rather
# than being invented.
_LATTICE_INFO: Dict[str, Dict[str, Any]] = {
    "simple_cubic": {"name": "Simple Cubic", "z": 1, "cn": 6, "packing": 52.4},
    "bcc": {"name": "Body-Centred Cubic (BCC)", "z": 2, "cn": 8, "packing": 68.0},
    "fcc": {"name": "Face-Centred Cubic (FCC)", "z": 4, "cn": 12, "packing": 74.0},
    "end_centred": {"name": "End-Centred Cubic", "z": 2, "cn": None, "packing": None},
    "hcp": {"name": "Hexagonal Close-Packed (HCP)", "z": 6, "cn": 12, "packing": 74.0},
}

_HCP_C_OVER_A = math.sqrt(8.0 / 3.0)   # ideal close-packed axial ratio

_ROLE_COLOR = {"corner": C_CORNER, "face": C_FACE, "body": C_BODY}
_ROLE_NAME = {"corner": "Corner", "face": "Face centre", "body": "Body/interior"}


def _hcp_hexagon(a: float = 1.0) -> List[Tuple[float, float]]:
    return [(a * math.cos(math.radians(60 * k)), a * math.sin(math.radians(60 * k)))
            for k in range(6)]


def _lattice_sites(unit_cell: str) -> List[Tuple[Tuple[float, float, float], str, float]]:
    """(position, role, share) per drawn atom; share = fraction of the atom owned by
    this cell. sum(share) == Z, so the picture and the quoted Z cannot drift apart."""
    if unit_cell == "hcp":
        c = _HCP_C_OVER_A
        sites: List[Tuple[Tuple[float, float, float], str, float]] = []
        for z in (0.0, c):
            for hx, hy in _hcp_hexagon():
                sites.append(((hx, hy, z), "corner", 1.0 / 6.0))
            sites.append(((0.0, 0.0, z), "face", 0.5))
        # middle layer: 3 atoms sitting in alternate trigonal voids, wholly inside the cell
        r_mid = 1.0 / math.sqrt(3.0)
        for ang in (30.0, 150.0, 270.0):
            sites.append(((r_mid * math.cos(math.radians(ang)),
                           r_mid * math.sin(math.radians(ang)), c / 2.0), "body", 1.0))
        return sites

    sites = [((x, y, z), "corner", 0.125)
             for x in (0.0, 1.0) for y in (0.0, 1.0) for z in (0.0, 1.0)]
    if unit_cell == "bcc":
        sites.append(((0.5, 0.5, 0.5), "body", 1.0))
    elif unit_cell == "fcc":
        for face in [(0.5, 0.5, 0.0), (0.5, 0.5, 1.0), (0.5, 0.0, 0.5),
                     (0.5, 1.0, 0.5), (0.0, 0.5, 0.5), (1.0, 0.5, 0.5)]:
            sites.append((face, "face", 0.5))
    elif unit_cell == "end_centred":
        for face in [(0.5, 0.5, 0.0), (0.5, 0.5, 1.0)]:   # one pair of opposite faces only
            sites.append((face, "face", 0.5))
    return sites


def _lattice_edges(unit_cell: str) -> List[Tuple[Tuple[float, float, float],
                                                 Tuple[float, float, float]]]:
    if unit_cell == "hcp":
        c = _HCP_C_OVER_A
        hexagon = _hcp_hexagon()
        edges = []
        for z in (0.0, c):
            for k in range(6):
                hx, hy = hexagon[k]
                qx, qy = hexagon[(k + 1) % 6]
                edges.append(((hx, hy, z), (qx, qy, z)))
        for hx, hy in hexagon:
            edges.append(((hx, hy, 0.0), (hx, hy, c)))
        return edges

    corners = [(x, y, z) for x in (0.0, 1.0) for y in (0.0, 1.0) for z in (0.0, 1.0)]
    edges = []
    for i, p in enumerate(corners):
        for q in corners[i + 1:]:
            if sum(1 for k in range(3) if p[k] != q[k]) == 1:
                edges.append((p, q))
    return edges


def render_crystal_lattice(data: Dict[str, Any],
                           canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = CrystalLatticeSchema(**data)
    from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
    from matplotlib.lines import Line2D

    info = _LATTICE_INFO[schema.unit_cell]
    sites = _lattice_sites(schema.unit_cell)
    is_hcp = schema.unit_cell == "hcp"

    fig = plt.figure(figsize=(canvas_w / 100, canvas_h / 100))
    ax = fig.add_subplot(111, projection="3d")
    ax.set_proj_type("ortho")
    ax.view_init(elev=18, azim=-58)
    ax.set_axis_off()

    if is_hcp:
        ax.set_xlim(-1.2, 1.2)
        ax.set_ylim(-1.2, 1.2)
        ax.set_zlim(-0.15, _HCP_C_OVER_A + 0.15)
        ax.set_box_aspect((2.4, 2.4, _HCP_C_OVER_A + 0.3))
    else:
        ax.set_xlim(-0.12, 1.12)
        ax.set_ylim(-0.12, 1.12)
        ax.set_zlim(-0.12, 1.12)
        ax.set_box_aspect((1, 1, 1))

    if schema.show_edges or schema.show_unit_cell_box:
        for p, q in _lattice_edges(schema.unit_cell):
            ax.plot([p[0], q[0]], [p[1], q[1]], [p[2], q[2]],
                    color="#7F8C8D", linewidth=1.2, zorder=1)

    counts: Dict[str, int] = {}
    if schema.show_atoms:
        for role in ("corner", "face", "body"):
            pts = [p for p, r, _ in sites if r == role]
            if not pts:
                continue
            counts[role] = len(pts)
            xs, ys, zs = zip(*pts)
            ax.scatter(xs, ys, zs, s=190 if role == "corner" else 210,
                       c=_ROLE_COLOR[role], edgecolors="black", linewidths=0.6,
                       depthshade=False, zorder=3)

    if schema.atom_label:
        px, py, pz = sites[0][0]
        ax.text(px, py, pz + 0.12, schema.atom_label, fontsize=10,
                fontweight="bold", color="#1A5276", ha="center")

    if schema.show_atoms and counts:
        share_by_role = {r: s for _, r, s in sites}
        handles = [
            Line2D([0], [0], marker="o", linestyle="none", markersize=8,
                   markerfacecolor=_ROLE_COLOR[r], markeredgecolor="black",
                   label=f"{_ROLE_NAME[r]} × {counts[r]}  ({_frac_label(share_by_role[r])} each)")
            for r in ("corner", "face", "body") if r in counts
        ]
        ax.legend(handles=handles, loc="lower left", fontsize=8, framealpha=0.9)

    lines = []
    if schema.show_atoms_per_cell:
        lines.append(f"Atoms per unit cell, Z = {info['z']}")
    if schema.show_coordination_number and info["cn"] is not None:
        lines.append(f"Coordination number = {info['cn']}")
    if schema.show_packing_efficiency and info["packing"] is not None:
        lines.append(f"Packing efficiency = {info['packing']:g}%")
    for i, line in enumerate(lines):
        ax.text2D(0.01, 0.97 - 0.055 * i, line, transform=ax.transAxes,
                  fontsize=10, fontweight="bold", color="#1A252F", va="top")

    title = schema.title or f"Unit Cell: {info['name']}"
    ax.set_title(title, fontsize=13, fontweight="bold", pad=4)
    return _fig_to_svg(fig)


def _frac_label(share: float) -> str:
    for value, glyph in ((0.125, "⅛"), (1.0 / 6.0, "⅙"), (0.5, "½"), (1.0, "1")):
        if abs(share - value) < 1e-6:
            return glyph
    return f"{share:g}"


# ── VSEPR Shape ───────────────────────────────────────────────────────────────

# n = bonding pairs, lp = lone pairs on the central atom, angle = the value the
# question actually asks for.
_VSEPR_INFO: Dict[str, Dict[str, Any]] = {
    "linear": {"name": "Linear", "n": 2, "lp": 0, "hyb": "sp", "angle": "180°"},
    "bent": {"name": "Bent (Angular)", "n": 2, "lp": 2, "hyb": "sp³", "angle": "≈ 104.5°"},
    "trigonal_planar": {"name": "Trigonal Planar", "n": 3, "lp": 0, "hyb": "sp²", "angle": "120°"},
    "trigonal_pyramidal": {"name": "Trigonal Pyramidal", "n": 3, "lp": 1, "hyb": "sp³",
                           "angle": "≈ 107°"},
    "tetrahedral": {"name": "Tetrahedral", "n": 4, "lp": 0, "hyb": "sp³", "angle": "109.5°"},
    "trigonal_bipyramidal": {"name": "Trigonal Bipyramidal", "n": 5, "lp": 0, "hyb": "sp³d",
                             "angle": "90° (ax–eq), 120° (eq–eq)"},
    "see_saw": {"name": "See-Saw", "n": 4, "lp": 1, "hyb": "sp³d",
                "angle": "< 90° / < 120° (lone pair in equatorial position)"},
    "t_shaped": {"name": "T-Shaped", "n": 3, "lp": 2, "hyb": "sp³d", "angle": "≈ 87.5°"},
    "linear_3": {"name": "Linear (AX₂E₃)", "n": 2, "lp": 3, "hyb": "sp³d", "angle": "180°"},
    "octahedral": {"name": "Octahedral", "n": 6, "lp": 0, "hyb": "sp³d²", "angle": "90°"},
    "square_planar": {"name": "Square Planar", "n": 4, "lp": 2, "hyb": "sp³d²", "angle": "90°"},
    "square_pyramidal": {"name": "Square Pyramidal", "n": 5, "lp": 1, "hyb": "sp³d²",
                         "angle": "< 90° (distorted by the lone pair)"},
}

# Geometries built on the trigonal-bipyramidal frame: axial ≠ equatorial, and the
# lone pairs always take equatorial slots (least 90° repulsion). Labelling ax/eq
# is the whole point of the diagram for these.
_TBP_FAMILY = ("trigonal_bipyramidal", "see_saw", "t_shaped", "linear_3")

_AXIAL_UP = (0.0, 0.0, 1.0)
_AXIAL_DOWN = (0.0, 0.0, -1.0)


def _equatorial(az_deg: float) -> Tuple[float, float, float]:
    a = math.radians(az_deg)
    return (math.cos(a), math.sin(a), 0.0)


def _pyramid_dirs(bond_angle_deg: float) -> List[Tuple[float, float, float]]:
    """Three directions, mutually `bond_angle` apart, arranged about the −z axis."""
    cos_a = math.cos(math.radians(bond_angle_deg))
    c = -math.sqrt(max((cos_a + 0.5) / 1.5, 0.0))    # z-component (below the xy plane)
    s = math.sqrt(max(1.0 - c * c, 0.0))
    return [(s * math.cos(math.radians(az)), s * math.sin(math.radians(az)), c)
            for az in (90.0, 210.0, 330.0)]


def _vsepr_frame(geometry: str, bond_angle: Optional[float]
                 ) -> Tuple[List[Tuple[Tuple[float, float, float], str]],
                            List[Tuple[float, float, float]]]:
    """(bond directions with an axial/equatorial tag, lone-pair directions)."""
    g = geometry
    if g == "linear":
        return [(_AXIAL_UP, ""), (_AXIAL_DOWN, "")], []
    if g == "bent":
        half = math.radians((bond_angle or 104.5) / 2.0)
        bonds = [((math.sin(half), 0.0, math.cos(half)), ""),
                 ((-math.sin(half), 0.0, math.cos(half)), "")]
        lp_half = math.radians(109.5 / 2.0)
        lps = [(0.0, math.sin(lp_half), -math.cos(lp_half)),
               (0.0, -math.sin(lp_half), -math.cos(lp_half))]
        return bonds, lps
    if g == "trigonal_planar":
        return [(_equatorial(az), "") for az in (90.0, 210.0, 330.0)], []
    if g == "trigonal_pyramidal":
        bonds = [(d, "") for d in _pyramid_dirs(bond_angle or 107.0)]
        return bonds, [_AXIAL_UP]
    if g == "tetrahedral":
        bonds = [(_AXIAL_UP, "")] + [(d, "") for d in _pyramid_dirs(bond_angle or 109.47)]
        return bonds, []
    if g == "trigonal_bipyramidal":
        return ([(_AXIAL_UP, "ax"), (_AXIAL_DOWN, "ax")]
                + [(_equatorial(az), "eq") for az in (90.0, 210.0, 330.0)], [])
    if g == "see_saw":
        return ([(_AXIAL_UP, "ax"), (_AXIAL_DOWN, "ax")]
                + [(_equatorial(az), "eq") for az in (210.0, 330.0)],
                [_equatorial(90.0)])
    if g == "t_shaped":
        return ([(_AXIAL_UP, "ax"), (_AXIAL_DOWN, "ax"), (_equatorial(90.0), "eq")],
                [_equatorial(210.0), _equatorial(330.0)])
    if g == "linear_3":
        return ([(_AXIAL_UP, "ax"), (_AXIAL_DOWN, "ax")],
                [_equatorial(az) for az in (90.0, 210.0, 330.0)])
    if g == "octahedral":
        return [((1.0, 0.0, 0.0), ""), ((-1.0, 0.0, 0.0), ""),
                ((0.0, 1.0, 0.0), ""), ((0.0, -1.0, 0.0), ""),
                (_AXIAL_UP, ""), (_AXIAL_DOWN, "")], []
    if g == "square_planar":
        return ([((1.0, 0.0, 0.0), ""), ((0.0, 1.0, 0.0), ""),
                 ((-1.0, 0.0, 0.0), ""), ((0.0, -1.0, 0.0), "")],
                [_AXIAL_UP, _AXIAL_DOWN])
    # square_pyramidal
    return ([((1.0, 0.0, 0.0), "basal"), ((0.0, 1.0, 0.0), "basal"),
             ((-1.0, 0.0, 0.0), "basal"), ((0.0, -1.0, 0.0), "basal"),
             (_AXIAL_UP, "apical")],
            [_AXIAL_DOWN])


def render_vsepr_shape(data: Dict[str, Any],
                       canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = VseprShapeSchema(**data)
    from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

    info = _VSEPR_INFO[schema.geometry]
    bonds, lp_dirs = _vsepr_frame(schema.geometry, schema.bond_angle)

    ligands = list(schema.ligand_atoms) or ["X"]
    while len(ligands) < len(bonds):
        ligands.append(ligands[-1])

    n_lp = info["lp"] if schema.lone_pairs is None else schema.lone_pairs
    n_lp = min(n_lp, len(lp_dirs))

    fig = plt.figure(figsize=(canvas_w / 100, canvas_h / 100))
    ax = fig.add_subplot(111, projection="3d")
    ax.set_proj_type("ortho")
    ax.view_init(elev=16, azim=-64)
    ax.set_axis_off()
    # Depth-based zorder would bury each ligand's label under its own sphere; take
    # manual control so bonds < spheres < labels always holds.
    ax.computed_zorder = False
    ax.set_xlim(-1.45, 1.45)
    ax.set_ylim(-1.45, 1.45)
    ax.set_zlim(-1.45, 1.45)
    ax.set_box_aspect((1, 1, 1))

    R = 1.05   # bond length in plot units
    for d, _tag in bonds:
        ax.plot([0, d[0] * R], [0, d[1] * R], [0, d[2] * R],
                color=C_BOND, linewidth=2.2, zorder=2)

    if schema.show_lone_pairs and n_lp:
        for d in lp_dirs[:n_lp]:
            _draw_lone_pair_3d(ax, d, R * 0.72)

    ax.scatter([0], [0], [0], s=430, c="#F39C12", edgecolors="black",
               linewidths=0.8, depthshade=False, zorder=4)
    for d, _tag in bonds:
        ax.scatter([d[0] * R], [d[1] * R], [d[2] * R], s=290, c="#5DADE2",
                   edgecolors="black", linewidths=0.7, depthshade=False, zorder=5)

    ax.text(0, 0, 0.0, schema.central_atom, fontsize=11, fontweight="bold",
            ha="center", va="center", zorder=8)
    for i, (d, tag) in enumerate(bonds):
        ex, ey, ez = d[0] * R, d[1] * R, d[2] * R
        ax.text(ex, ey, ez, ligands[i], fontsize=10, fontweight="bold",
                ha="center", va="center", zorder=8)
        if tag:
            ax.text(ex * 1.36, ey * 1.36, ez * 1.36, tag, fontsize=8,
                    color=C_ANNOT, ha="center", va="center", zorder=8)

    facts = [f"Shape: {info['name']}",
             f"Hybridisation: {schema.hybridisation or info['hyb']}",
             f"Bond angle: {f'{schema.bond_angle:g}°' if schema.bond_angle else info['angle']}",
             f"Bond pairs: {len(bonds)}   Lone pairs: {n_lp}"]
    for i, line in enumerate(facts):
        ax.text2D(0.01, 0.98 - 0.055 * i, line, transform=ax.transAxes,
                  fontsize=9.5, color="#1A252F", va="top",
                  fontweight="bold" if i == 0 else "normal")

    title = schema.title or f"VSEPR: {info['name']}"
    ax.set_title(title, fontsize=13, fontweight="bold", pad=4)
    return _fig_to_svg(fig)


def _draw_lone_pair_3d(ax, direction: Tuple[float, float, float], dist: float):
    """Lone pair drawn as the conventional pair of dots, offset ⟂ to its axis."""
    d = np.array(direction, dtype=float)
    d /= np.linalg.norm(d)
    ref = np.array([0.0, 0.0, 1.0]) if abs(d[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    perp = np.cross(d, ref)
    perp /= np.linalg.norm(perp)
    centre = d * dist
    for sign in (1.0, -1.0):
        p = centre + perp * 0.13 * sign
        ax.scatter([p[0]], [p[1]], [p[2]], s=48, c=C_LONE_PAIR,
                   depthshade=False, zorder=6)
    tip = d * (dist + 0.30)
    ax.text(tip[0], tip[1], tip[2], "lp", fontsize=8, color=C_LONE_PAIR,
            fontweight="bold", ha="center", va="center", zorder=8)


# ── Molecular Orbital Diagram ─────────────────────────────────────────────────

_PERIODIC: Dict[str, Tuple[int, int]] = {   # symbol → (atomic number, valence e⁻)
    "H": (1, 1), "He": (2, 2), "Li": (3, 1), "Be": (4, 2), "B": (5, 3),
    "C": (6, 4), "N": (7, 5), "O": (8, 6), "F": (9, 7), "Ne": (10, 8),
}

_MO_MOLECULES: Dict[str, Tuple[str, str]] = {
    "H2": ("H", "H"), "HE2": ("He", "He"), "LI2": ("Li", "Li"), "BE2": ("Be", "Be"),
    "B2": ("B", "B"), "C2": ("C", "C"), "N2": ("N", "N"), "O2": ("O", "O"),
    "F2": ("F", "F"), "NE2": ("Ne", "Ne"), "CO": ("C", "O"), "NO": ("N", "O"),
    "CN": ("C", "N"), "BN": ("B", "N"),
}

# Energy ladders (relative units). For B₂/C₂/N₂ the 2s–2pz interaction (s–p mixing)
# pushes σ2pz ABOVE the π2p pair; from O₂ onwards the 2s–2p gap is too large for
# mixing and σ2pz drops below π2p. Swapping these two orderings is the single most
# common error in this diagram, so the ladders are kept as explicit data.
_MO_LADDER_N2 = [
    ("σ2s", "bonding", 1.0, 1), ("σ*2s", "antibonding", 2.2, 1),
    ("π2p", "bonding", 3.5, 2), ("σ2pz", "bonding", 4.5, 1),
    ("π*2p", "antibonding", 5.8, 2), ("σ*2pz", "antibonding", 7.0, 1),
]
_MO_LADDER_O2 = [
    ("σ2s", "bonding", 1.0, 1), ("σ*2s", "antibonding", 2.2, 1),
    ("σ2pz", "bonding", 3.4, 1), ("π2p", "bonding", 4.3, 2),
    ("π*2p", "antibonding", 5.8, 2), ("σ*2pz", "antibonding", 7.0, 1),
]
_MO_LADDER_1S = [
    ("σ1s", "bonding", 2.0, 1), ("σ*1s", "antibonding", 5.0, 1),
]


def _fill_hund(n_orbitals: int, electrons: int) -> List[int]:
    """Singly occupy every degenerate orbital before pairing (Hund's rule)."""
    occ = [0] * n_orbitals
    for i in range(min(electrons, n_orbitals)):
        occ[i] = 1
    left = electrons - min(electrons, n_orbitals)
    for i in range(n_orbitals):
        if left <= 0:
            break
        occ[i] = 2
        left -= 1
    return occ


def _build_mo_diagram(schema: MoDiagramSchema) -> Dict[str, Any]:
    """Levels (bottom-up) + bond order + magnetic behaviour."""
    if schema.orbitals:
        levels = [{"label": o.label, "type": o.orbital_type, "energy": o.energy,
                   "occ": [o.electrons]}
                  for o in sorted(schema.orbitals, key=lambda o: o.energy)]
        left = right = None
        ladder_name = "explicit"
    else:
        key = (schema.molecule or "").upper().replace("₂", "2").replace("₃", "3").strip()
        pair = _MO_MOLECULES.get(key)
        left = schema.atom_left or (pair[0] if pair else None)
        right = schema.atom_right or (pair[1] if pair else None)
        if left not in _PERIODIC or right not in _PERIODIC:
            raise ValueError(
                f"Unknown MO molecule '{schema.molecule}'. Give atom_left/atom_right "
                f"from {list(_PERIODIC)} or supply an explicit `orbitals` list.")
        z_l, v_l = _PERIODIC[left]
        z_r, v_r = _PERIODIC[right]
        v_l = schema.electrons_left if schema.electrons_left is not None else v_l
        v_r = schema.electrons_right if schema.electrons_right is not None else v_r
        valence = v_l + v_r

        if max(z_l, z_r) <= 2:
            ladder, ladder_name = _MO_LADDER_1S, "1s"
        elif schema.orbital_order == "n2_type":
            ladder, ladder_name = _MO_LADDER_N2, "n2_type"
        elif schema.orbital_order == "o2_type":
            ladder, ladder_name = _MO_LADDER_O2, "o2_type"
        elif (z_l + z_r) <= 14:      # up to N₂ / CO → s–p mixing operates
            ladder, ladder_name = _MO_LADDER_N2, "n2_type"
        else:
            ladder, ladder_name = _MO_LADDER_O2, "o2_type"

        levels = []
        remaining = valence
        for label, otype, energy, n_orb in ladder:
            take = min(remaining, 2 * n_orb)
            levels.append({"label": label, "type": otype, "energy": energy,
                           "occ": _fill_hund(n_orb, take)})
            remaining -= take

    bonding = sum(sum(lv["occ"]) for lv in levels if lv["type"] == "bonding")
    anti = sum(sum(lv["occ"]) for lv in levels if lv["type"] == "antibonding")
    unpaired = sum(1 for lv in levels for e in lv["occ"] if e == 1)
    bond_order = (bonding - anti) / 2.0
    return {
        "levels": levels, "atom_left": left, "atom_right": right,
        "bond_order": bond_order, "unpaired": unpaired,
        "magnetism": "Paramagnetic" if unpaired else "Diamagnetic",
        "ladder": ladder_name,
    }


def _ao_levels(symbol: str, electrons: int, y_shift: float) -> List[Dict[str, Any]]:
    z, _ = _PERIODIC[symbol]
    if z <= 2:
        return [{"label": "1s", "energy": 3.5 + y_shift, "occ": _fill_hund(1, min(electrons, 2))}]
    s_e = min(electrons, 2)
    p_e = max(electrons - 2, 0)
    return [
        {"label": "2s", "energy": 1.6 + y_shift, "occ": _fill_hund(1, s_e)},
        {"label": "2p", "energy": 4.8 + y_shift, "occ": _fill_hund(3, p_e)},
    ]


def _draw_mo_boxes(ax, x_centre: float, y: float, occ: List[int], color: str):
    bw, gap = 0.44, 0.10
    total = len(occ) * bw + (len(occ) - 1) * gap
    x0 = x_centre - total / 2
    for i, e in enumerate(occ):
        bx = x0 + i * (bw + gap)
        ax.add_patch(mpatches.Rectangle((bx, y - 0.11), bw, 0.22, linewidth=1.4,
                                        edgecolor=color, facecolor="white", zorder=3))
        if e >= 1:
            _spin_arrow(ax, bx + bw * 0.30, y, up=True)
        if e == 2:
            _spin_arrow(ax, bx + bw * 0.70, y, up=False)
    return x0, x0 + total


def _spin_arrow(ax, x: float, y: float, up: bool, h: float = 0.19):
    y0, y1 = (y - h / 2, y + h / 2) if up else (y + h / 2, y - h / 2)
    ax.annotate("", xy=(x, y1), xytext=(x, y0), zorder=5,
                arrowprops=dict(arrowstyle="-|>", color="black", lw=1.1,
                                shrinkA=0, shrinkB=0, mutation_scale=9))


def render_mo_diagram(data: Dict[str, Any],
                      canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = MoDiagramSchema(**data)
    built = _build_mo_diagram(schema)
    levels = built["levels"]

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))
    ax.set_xlim(0, 10)
    ax.set_ylim(-1.3, 8.6)
    ax.axis("off")

    x_left, x_mid, x_right = 2.0, 5.0, 8.0
    ax.annotate("", xy=(0.35, 7.6), xytext=(0.35, 0.6),
                arrowprops=dict(arrowstyle="-|>", color="black", lw=1.2))
    ax.text(0.18, 4.1, "Energy →", rotation=90, va="center", ha="center", fontsize=10)

    left, right = built["atom_left"], built["atom_right"]
    ao_map: Dict[str, List[Dict[str, Any]]] = {}
    if left and right:
        # In a heteronuclear pair the more electronegative atom's AOs lie lower.
        z_l, z_r = _PERIODIC[left][0], _PERIODIC[right][0]
        v_l = schema.electrons_left if schema.electrons_left is not None else _PERIODIC[left][1]
        v_r = schema.electrons_right if schema.electrons_right is not None else _PERIODIC[right][1]
        shift_l = -0.6 if z_l > z_r else 0.0
        shift_r = -0.6 if z_r > z_l else 0.0
        for x, sym, ve, shift in ((x_left, left, v_l, shift_l), (x_right, right, v_r, shift_r)):
            aos = _ao_levels(sym, ve, shift)
            ao_map[sym if x == x_left else sym + "_r"] = aos
            for ao in aos:
                bx0, bx1 = _draw_mo_boxes(ax, x, ao["energy"], ao["occ"], "#7F8C8D")
                ax.text(bx0 - 0.22 if x == x_left else bx1 + 0.22, ao["energy"], ao["label"],
                        fontsize=10, ha="right" if x == x_left else "left",
                        va="center", color="#566573")
        ax.text(x_left, 8.15, left, fontsize=13, fontweight="bold", ha="center")
        ax.text(x_right, 8.15, right, fontsize=13, fontweight="bold", ha="center")

    for lv in levels:
        color = {"bonding": "#1E8449", "antibonding": "#C0392B"}.get(lv["type"], "#566573")
        bx0, bx1 = _draw_mo_boxes(ax, x_mid, lv["energy"], lv["occ"], color)
        ax.text(bx1 + 0.18, lv["energy"], lv["label"], fontsize=10, va="center",
                ha="left", color=color, fontweight="bold")
        # correlation lines back to the parent AOs
        if ao_map:
            parent = "1s" if "1s" in lv["label"] else ("2s" if "2s" in lv["label"] else "2p")
            for key, aos in ao_map.items():
                x_ao = x_left if not key.endswith("_r") else x_right
                for ao in aos:
                    if ao["label"] != parent:
                        continue
                    ax.plot([x_ao + (0.45 if x_ao == x_left else -0.45), bx0 if x_ao == x_left else bx1],
                            [ao["energy"], lv["energy"]],
                            linestyle="--", color="#B3B6B7", linewidth=0.9, zorder=1)

    ax.text(x_mid, 8.15, "Molecular Orbitals", fontsize=11, fontweight="bold", ha="center")

    facts = []
    if schema.show_bond_order:
        facts.append(f"Bond order = {built['bond_order']:g}")
    if schema.show_magnetic_behaviour:
        facts.append(f"{built['magnetism']} ({built['unpaired']} unpaired e⁻)")
    if facts:
        ax.text(x_mid, -0.15, "     ".join(facts), fontsize=11, ha="center",
                va="top", color="#1A252F", fontweight="bold")
    note = {"n2_type": "s–p mixing: σ2pz lies ABOVE π2p",
            "o2_type": "No s–p mixing: σ2pz lies BELOW π2p"}.get(built["ladder"])
    if note:
        ax.text(x_mid, -0.75, note, fontsize=9.5, ha="center", va="top", color=C_ANNOT)

    title = schema.title or f"Molecular Orbital Diagram: {schema.molecule}"
    ax.set_title(title, fontsize=13, fontweight="bold")
    fig.tight_layout()
    return _fig_to_svg(fig)


# ── Phase Diagram ─────────────────────────────────────────────────────────────

_R_GAS = 8.314   # J mol⁻¹ K⁻¹

# fusion_slope = dT/dP of the solid–liquid boundary in °C/atm. Water's is NEGATIVE
# (ice is less dense than liquid water, so ΔV_fusion < 0 and by Clapeyron
# dP/dT < 0): applying pressure MELTS ice. Every other common substance, CO₂
# included, expands on melting and so has a positive slope. Getting this sign
# wrong inverts the entire meaning of the water phase diagram.
_PHASE_DATA: Dict[str, Dict[str, Any]] = {
    "water": {
        "name": "H₂O", "t_triple": 0.01, "p_triple": 0.006, "t_crit": 374.0,
        "p_crit": 218.0, "t_boil": 100.0, "fusion_slope": -0.0075, "dh_sub": 51000.0,
        "t_range": (-40.0, 400.0), "p_range": (1e-4, 1e3),
        "regions": {"Solid": (-25.0, 30.0), "Liquid": (150.0, 60.0), "Gas": (250.0, 0.01)},
    },
    "co2": {
        "name": "CO₂", "t_triple": -56.6, "p_triple": 5.11, "t_crit": 31.1,
        "p_crit": 72.9, "t_boil": None, "fusion_slope": 0.030, "dh_sub": 25200.0,
        "t_range": (-100.0, 60.0), "p_range": (0.1, 1e3),
        "regions": {"Solid": (-85.0, 30.0), "Liquid": (-20.0, 250.0), "Gas": (10.0, 0.3)},
    },
    "generic": {
        "name": "Substance", "t_triple": -10.0, "p_triple": 0.2, "t_crit": 200.0,
        "p_crit": 80.0, "t_boil": 60.0, "fusion_slope": 0.020, "dh_sub": 45000.0,
        "t_range": (-50.0, 250.0), "p_range": (1e-3, 1e3),
        "regions": {"Solid": (-35.0, 30.0), "Liquid": (110.0, 60.0), "Gas": (180.0, 0.02)},
    },
}

_TRANSITION_ALIASES = {
    "sublimation": "sublimation", "deposition": "sublimation",
    "vaporisation": "vaporisation", "vaporization": "vaporisation",
    "vapourisation": "vaporisation", "boiling": "vaporisation",
    "condensation": "vaporisation", "evaporation": "vaporisation",
    "fusion": "fusion", "melting": "fusion", "freezing": "fusion",
}


def _clausius_curve(anchors: List[Tuple[float, float]],
                    t_from: float, t_to: float, n: int = 240):
    """ln P as a polynomial in 1/T through the given (T °C, P atm) anchors."""
    tk = np.array([a[0] for a in anchors]) + 273.15
    lnp = np.log(np.array([a[1] for a in anchors]))
    coeff = np.polyfit(1.0 / tk, lnp, min(len(anchors) - 1, 2))
    t = np.linspace(t_from, t_to, n)
    return t, np.exp(np.polyval(coeff, 1.0 / (t + 273.15)))


def _phase_curves(substance: str) -> Dict[str, Any]:
    d = _PHASE_DATA[substance]
    t_tp, p_tp = d["t_triple"], d["p_triple"]
    p_max = d["p_range"][1]

    # Solid–liquid: T = T_tp + (dT/dP)(P − P_tp). Sign of fusion_slope is the physics.
    p_fus = np.geomspace(p_tp, p_max, 200)
    t_fus = t_tp + d["fusion_slope"] * (p_fus - p_tp)

    # Solid–vapour: Clausius–Clapeyron anchored on the triple point + ΔH_sublimation.
    t_sub = np.linspace(d["t_range"][0], t_tp, 240)
    p_sub = p_tp * np.exp(-(d["dh_sub"] / _R_GAS)
                          * (1.0 / (t_sub + 273.15) - 1.0 / (t_tp + 273.15)))

    # Liquid–vapour: triple point → critical point, pinned through the normal
    # boiling point (1 atm) where the substance has one.
    anchors = [(t_tp, p_tp), (d["t_crit"], d["p_crit"])]
    if d["t_boil"] is not None:
        anchors.insert(1, (d["t_boil"], 1.0))
    t_vap, p_vap = _clausius_curve(anchors, t_tp, d["t_crit"])

    return {
        "data": d,
        "fusion": (t_fus, p_fus),
        "sublimation": (t_sub, p_sub),
        "vaporisation": (t_vap, p_vap),
        "triple": (t_tp, p_tp),
        "critical": (d["t_crit"], d["p_crit"]),
    }


def render_phase_diagram(data: Dict[str, Any],
                         canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = PhaseDiagramSchema(**data)
    curves = _phase_curves(schema.substance)
    d = curves["data"]
    highlight = _TRANSITION_ALIASES.get((schema.highlight_transition or "").strip().lower())

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))
    ax.set_yscale("log")
    ax.set_xlim(*d["t_range"])
    ax.set_ylim(*d["p_range"])

    for name, color in (("sublimation", "#7D3C98"), ("fusion", "#2874A6"),
                        ("vaporisation", "#CA6F1E")):
        t, p = curves[name]
        hot = (highlight == name)
        ax.plot(t, p, color=color, linewidth=3.4 if hot else 2.2,
                zorder=4 if hot else 3,
                label=name.capitalize() if hot else None)

    t_tp, p_tp = curves["triple"]
    t_c, p_c = curves["critical"]

    if schema.show_triple_point:
        ax.plot(t_tp, p_tp, "ko", markersize=7, zorder=6)
        ax.annotate(f"Triple point\n({t_tp:g} °C, {p_tp:g} atm)", xy=(t_tp, p_tp),
                    xytext=(18, -34), textcoords="offset points", fontsize=9,
                    arrowprops=dict(arrowstyle="->", color="black", lw=1))
    if schema.show_critical_point:
        ax.plot(t_c, p_c, "s", color="#B03A2E", markersize=7, zorder=6)
        ax.annotate(f"Critical point\n({t_c:g} °C, {p_c:g} atm)", xy=(t_c, p_c),
                    xytext=(-96, 14), textcoords="offset points", fontsize=9,
                    arrowprops=dict(arrowstyle="->", color="#B03A2E", lw=1))

    if schema.show_regions:
        for label, (tx, py) in d["regions"].items():
            ax.text(tx, py, label, fontsize=13, fontweight="bold", color="#5D6D7E",
                    ha="center", va="center")

    # 1 atm reference line — the line every "what happens at atmospheric pressure"
    # question is really about.
    ax.axhline(1.0, color="#909497", linestyle=":", linewidth=1.2, zorder=2)
    ax.text(d["t_range"][1], 1.15, "1 atm", fontsize=9, color="#616A6B",
            ha="right", va="bottom")

    if schema.substance == "water":
        ax.plot([0.0, 100.0], [1.0, 1.0], "k.", markersize=6, zorder=6)
        ax.annotate("m.p. 0 °C", xy=(0.0, 1.0), xytext=(-6, 26),
                    textcoords="offset points", fontsize=8, color="#1A5276")
        ax.annotate("b.p. 100 °C", xy=(100.0, 1.0), xytext=(-10, 26),
                    textcoords="offset points", fontsize=8, color="#1A5276")
        ax.text(0.02, 0.03,
                "Fusion curve slopes ← (negative dP/dT): ice melts under pressure",
                transform=ax.transAxes, fontsize=9, color="#2874A6",
                fontweight="bold", va="bottom")
    elif schema.substance == "co2":
        ax.plot(-78.5, 1.0, "k.", markersize=7, zorder=6)
        ax.annotate("sublimes at −78.5 °C", xy=(-78.5, 1.0), xytext=(6, 20),
                    textcoords="offset points", fontsize=8, color="#7D3C98")
        ax.text(0.02, 0.03,
                "Triple point (5.11 atm) lies ABOVE 1 atm → solid CO₂ sublimes; "
                "no liquid CO₂ at 1 atm",
                transform=ax.transAxes, fontsize=9, color="#7D3C98",
                fontweight="bold", va="bottom")

    if highlight:
        ax.legend(fontsize=9, loc="upper left")

    ax.set_xlabel("Temperature (°C) →", fontsize=11)
    ax.set_ylabel("Pressure (atm, log scale)", fontsize=11)
    ax.set_title(schema.title or f"Phase Diagram: {d['name']}",
                 fontsize=13, fontweight="bold")
    ax.grid(True, which="major", linestyle=":", linewidth=0.5, color="#D5D8DC")
    fig.tight_layout()
    return _fig_to_svg(fig)


# ── Haworth / Fischer Projection ──────────────────────────────────────────────

# Fischer: (carbon label, substituent, side) — side=None for the terminal groups.
# Haworth: (carbon label, substituent, up/down) for the non-anomeric ring carbons,
# obtained by the standard rule "right in Fischer → down in Haworth, left → up",
# with the terminal CH₂OH of a D-sugar pointing up.
_SUGARS: Dict[str, Dict[str, Any]] = {
    "glucose": {
        "name": "D-Glucose", "ring": "pyranose", "anomeric": "C1", "anomeric_extra": None,
        "fischer": [("C1", "CHO", None), ("C2", "OH", "right"), ("C3", "OH", "left"),
                    ("C4", "OH", "right"), ("C5", "OH", "right"), ("C6", "CH₂OH", None)],
        "haworth": [("C2", "OH", "down"), ("C3", "OH", "up"),
                    ("C4", "OH", "down"), ("C5", "CH₂OH", "up")],
    },
    "galactose": {
        "name": "D-Galactose", "ring": "pyranose", "anomeric": "C1", "anomeric_extra": None,
        "fischer": [("C1", "CHO", None), ("C2", "OH", "right"), ("C3", "OH", "left"),
                    ("C4", "OH", "left"), ("C5", "OH", "right"), ("C6", "CH₂OH", None)],
        # C4 epimer of glucose → its C4-OH is the one that flips (up, not down)
        "haworth": [("C2", "OH", "down"), ("C3", "OH", "up"),
                    ("C4", "OH", "up"), ("C5", "CH₂OH", "up")],
    },
    "fructose": {
        "name": "D-Fructose", "ring": "furanose", "anomeric": "C2", "anomeric_extra": "CH₂OH",
        "fischer": [("C1", "CH₂OH", None), ("C2", "C=O", None), ("C3", "OH", "left"),
                    ("C4", "OH", "right"), ("C5", "OH", "right"), ("C6", "CH₂OH", None)],
        "haworth": [("C3", "OH", "up"), ("C4", "OH", "down"), ("C5", "CH₂OH", "up")],
    },
    "ribose": {
        "name": "D-Ribose", "ring": "furanose", "anomeric": "C1", "anomeric_extra": None,
        "fischer": [("C1", "CHO", None), ("C2", "OH", "right"), ("C3", "OH", "right"),
                    ("C4", "OH", "right"), ("C5", "CH₂OH", None)],
        "haworth": [("C2", "OH", "down"), ("C3", "OH", "down"), ("C4", "CH₂OH", "up")],
    },
    "generic": {
        "name": "D-Aldohexose", "ring": "pyranose", "anomeric": "C1", "anomeric_extra": None,
        "fischer": [("C1", "CHO", None), ("C2", "OH", "right"), ("C3", "OH", "right"),
                    ("C4", "OH", "right"), ("C5", "OH", "right"), ("C6", "CH₂OH", None)],
        "haworth": [("C2", "OH", "down"), ("C3", "OH", "down"),
                    ("C4", "OH", "down"), ("C5", "CH₂OH", "up")],
    },
}

# Ring skeletons in Haworth perspective; the first entry is the anomeric carbon and
# the O closes the ring. Front edges are drawn thick (that IS the perspective cue).
# No two vertices share an x-coordinate: the substituent bonds are vertical, so a
# shared x would draw one carbon's bond straight through another's.
_HAWORTH_RING = {
    "pyranose": {
        "vertices": [(1.55, 0.10), (1.05, -0.32), (-0.15, -0.32),
                     (-0.65, 0.10), (0.05, 0.42), (0.85, 0.42)],
        "front": [(0, 1), (1, 2), (2, 3)],
    },
    "furanose": {
        "vertices": [(1.15, 0.05), (0.72, -0.35), (-0.32, -0.35),
                     (-0.75, 0.05), (0.30, 0.45)],
        "front": [(0, 1), (1, 2), (2, 3)],
    },
}


def _anomeric_direction(anomer: str) -> Optional[str]:
    """α-D → anomeric OH BELOW the ring plane; β-D → ABOVE. This is the question."""
    return {"alpha": "down", "beta": "up"}.get(anomer)


def _haworth_layout(molecule: str, ring_size: Optional[str], anomer: str) -> Dict[str, Any]:
    """Ring geometry + every exocyclic group with its up/down assignment."""
    sugar = _SUGARS.get(molecule, _SUGARS["generic"])
    ring = ring_size if ring_size in _HAWORTH_RING else sugar["ring"]
    if len(sugar["haworth"]) + 2 > len(_HAWORTH_RING[ring]["vertices"]):
        ring = sugar["ring"]      # requested ring can't hold this sugar's carbons
    skel = _HAWORTH_RING[ring]
    verts = skel["vertices"]

    groups = []
    anom_dir = _anomeric_direction(anomer)
    if anom_dir:
        groups.append({"carbon": sugar["anomeric"], "group": "OH",
                       "direction": anom_dir, "vertex": 0, "anomeric": True})
        groups.append({"carbon": sugar["anomeric"],
                       "group": sugar["anomeric_extra"] or "H",
                       "direction": "up" if anom_dir == "down" else "down",
                       "vertex": 0, "anomeric": False})
    for i, (carbon, group, direction) in enumerate(sugar["haworth"], start=1):
        groups.append({"carbon": carbon, "group": group, "direction": direction,
                       "vertex": i, "anomeric": False})
    return {"sugar": sugar, "ring": ring, "vertices": verts,
            "front": skel["front"], "groups": groups}


def _render_fischer(ax, schema: HaworthFischerSchema, sugar: Dict[str, Any]):
    chain = sugar["fischer"]
    if schema.substituents:
        chain = [(c, schema.substituents[i] if i < len(schema.substituents) else g, s)
                 for i, (c, g, s) in enumerate(chain)]
    n = len(chain)
    step = 1.0
    ys = [(n - 1 - i) * step for i in range(n)]

    ax.plot([0, 0], [ys[-1], ys[0]], color="black", linewidth=1.8, zorder=1)
    for i, ((carbon, group, side), y) in enumerate(zip(chain, ys)):
        if side is None:      # terminal / carbonyl carbon: group sits on the chain
            ax.text(0, y, group, ha="center", va="center", fontsize=12,
                    fontweight="bold", zorder=4,
                    bbox=dict(boxstyle="round,pad=0.22", fc="white", ec="none"))
        else:
            ax.plot([-0.95, 0.95], [y, y], color="black", linewidth=1.6, zorder=1)
            ox = 1.15 if side == "right" else -1.15
            hx = -1.15 if side == "right" else 1.15
            ax.text(ox, y, group, ha="center", va="center", fontsize=12,
                    fontweight="bold", color="#C0392B", zorder=4)
            ax.text(hx, y, "H", ha="center", va="center", fontsize=12, zorder=4)
        if schema.show_carbon_numbers:
            ax.text(-2.15, y, carbon, ha="center", va="center", fontsize=9,
                    color=C_ANNOT)

    ax.set_xlim(-2.7, 2.3)
    ax.set_ylim(-0.9, ys[0] + 0.9)
    ax.text(0, -0.65, "Horizontal bonds point TOWARDS the viewer",
            ha="center", fontsize=8.5, color=C_ANNOT, style="italic")


def _render_haworth(ax, schema: HaworthFischerSchema, layout: Dict[str, Any]):
    verts = layout["vertices"]
    n = len(verts)
    front = set(layout["front"])

    for i in range(n):
        j = (i + 1) % n
        thick = (i, j) in front
        ax.plot([verts[i][0], verts[j][0]], [verts[i][1], verts[j][1]],
                color="black", linewidth=3.6 if thick else 1.5,
                solid_capstyle="round", zorder=2)

    ox, oy = verts[-1]        # ring oxygen closes the ring (drawn at the back)
    ax.text(ox, oy, "O", ha="center", va="center", fontsize=13, fontweight="bold",
            color="#C0392B", zorder=5,
            bbox=dict(boxstyle="circle,pad=0.16", fc="white", ec="none"))

    # Substituent bonds are long enough that every label clears the ring silhouette.
    overrides = list(schema.substituents)
    for k, g in enumerate(layout["groups"]):
        vx, vy = verts[g["vertex"]]
        label = overrides[k] if k < len(overrides) else g["group"]
        sign = 1.0 if g["direction"] == "up" else -1.0
        ax.plot([vx, vx], [vy, vy + sign * 0.75], color="black", linewidth=1.5, zorder=2)
        ax.text(vx, vy + sign * 1.00, label, ha="center", va="center", fontsize=10,
                fontweight="bold" if g["anomeric"] else "normal",
                color="#C0392B" if g["anomeric"] else "#1A252F", zorder=5,
                bbox=dict(boxstyle="round,pad=0.14", fc="white", ec="none"))
        if g["anomeric"]:
            ax.annotate(f"anomeric OH ({g['direction'].upper()})",
                        xy=(vx, vy + sign * 1.00), xytext=(0.70, 0.94 if sign > 0 else 0.06),
                        textcoords="axes fraction", fontsize=9, color="#C0392B",
                        fontweight="bold",
                        arrowprops=dict(arrowstyle="->", color="#C0392B", lw=1))

    if schema.show_carbon_numbers:
        cx = sum(v[0] for v in verts) / n
        cy = sum(v[1] for v in verts) / n
        seen = set()
        for g in layout["groups"]:
            if g["vertex"] in seen:
                continue
            seen.add(g["vertex"])
            vx, vy = verts[g["vertex"]]
            dx, dy = cx - vx, cy - vy
            norm = math.hypot(dx, dy) or 1.0
            ax.text(vx + 0.26 * dx / norm, vy + 0.26 * dy / norm, g["carbon"],
                    fontsize=8, color=C_ANNOT, ha="center", va="center", zorder=5)

    ax.set_xlim(-1.9, 2.5)
    ax.set_ylim(-1.8, 1.8)


def render_haworth_fischer(data: Dict[str, Any],
                           canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = HaworthFischerSchema(**data)
    sugar = _SUGARS.get(schema.molecule, _SUGARS["generic"])

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))
    ax.set_aspect("equal")
    ax.axis("off")

    if schema.projection == "fischer":
        _render_fischer(ax, schema, sugar)
        title = schema.title or f"Fischer Projection: {sugar['name']}"
    else:
        layout = _haworth_layout(schema.molecule, schema.ring_size, schema.anomer)
        _render_haworth(ax, schema, layout)
        prefix = {"alpha": "α-", "beta": "β-", "none": ""}[schema.anomer]
        stem = sugar["name"][:-2] if sugar["name"].endswith("se") else sugar["name"]
        title = schema.title or f"Haworth Projection: {prefix}{stem}{layout['ring']}"

    ax.set_title(title, fontsize=13, fontweight="bold", pad=8)
    fig.tight_layout()
    return _fig_to_svg(fig)


# ── Lab Apparatus ─────────────────────────────────────────────────────────────

_GLASS = dict(color=C_GLASS, linewidth=1.8, solid_capstyle="round", zorder=3)

_APPARATUS_LABELS: Dict[str, Dict[str, str]] = {
    "simple_distillation": {
        "flask": "Round-bottom flask", "thermometer": "Thermometer",
        "condenser": "Liebig condenser", "receiver": "Receiver (distillate)",
        "heat": "Heat", "bulb": "Thermometer BULB level with the side-arm",
        "note": "Separates liquids whose boiling points differ by more than ~25 K",
    },
    "fractional_distillation": {
        "flask": "Round-bottom flask", "column": "Fractionating column",
        "thermometer": "Thermometer", "condenser": "Liebig condenser",
        "receiver": "Receiver", "heat": "Heat",
        "bulb": "Thermometer BULB level with the side-arm",
        "note": "Column gives repeated condensation–vaporisation cycles",
    },
    "filtration": {
        "funnel": "Filter funnel", "paper": "Filter paper (folded cone)",
        "residue": "Residue", "flask": "Conical flask", "filtrate": "Filtrate",
        "rod": "Stirring rod", "note": "Residue stays on the paper; filtrate passes through",
    },
    "titration": {
        "burette": "Burette (titrant)", "stopcock": "Stopcock",
        "flask": "Conical flask (analyte)", "tile": "White tile",
        "stand": "Burette stand", "note": "Swirl the flask; read the lower meniscus",
    },
    "reflux": {
        "flask": "Round-bottom flask", "condenser": "Vertical (reflux) condenser",
        "heat": "Heating mantle",
        "note": "Vapour condenses and returns — nothing is collected",
    },
    "steam_distillation": {
        "generator": "Steam generator", "safety": "Safety tube",
        "flask": "Flask with the mixture", "condenser": "Condenser",
        "receiver": "Receiver", "heat": "Heat",
        "note": "For steam-volatile, water-immiscible liquids",
    },
    "sublimation": {
        "dish": "China dish (impure solid)", "funnel": "Inverted funnel",
        "cotton": "Cotton plug", "sublimate": "Sublimate on the funnel walls",
        "heat": "Heat",
        "note": "Separates a sublimable solid from a non-sublimable impurity",
    },
    "separating_funnel": {
        "funnel": "Separating funnel", "upper": "Lighter layer",
        "lower": "Denser layer", "stopcock": "Stopcock", "beaker": "Beaker",
        "note": "Run off the lower layer first",
    },
    "chromatography": {
        "jar": "Chromatography jar", "paper": "Chromatography paper",
        "baseline": "Baseline (pencil)", "spot": "Spot", "front": "Solvent front",
        "solvent": "Solvent", "note": "Rf = distance moved by solute / by solvent",
    },
}


def _lab_text(ax, x, y, key, labels, show, **kw):
    if not show:
        return
    ax.text(x, y, labels[key], fontsize=8.5, color="#1B2631", zorder=6, **kw)


def _rbf(ax, cx, cy, r, neck_h=0.75, neck_w=0.22, liquid=True):
    """Round-bottom flask centred at (cx, cy) with a vertical neck."""
    th = np.linspace(0, 2 * np.pi, 200)
    ax.plot(cx + r * np.cos(th), cy + r * np.sin(th), **_GLASS)
    top = cy + math.sqrt(max(r * r - neck_w * neck_w, 0.0))
    for sx in (-1, 1):
        ax.plot([cx + sx * neck_w, cx + sx * neck_w], [top, cy + r + neck_h], **_GLASS)
    if liquid:
        mask = np.linspace(np.pi, 2 * np.pi, 120)
        ax.fill_between(cx + r * np.cos(mask), cy + r * np.sin(mask), cy - r * 0.05,
                        color=C_LIQUID, zorder=2)
    return cx, cy + r + neck_h


def _heat(ax, cx, y, labels=None, show=False, key="heat"):
    for dx in (-0.22, 0.0, 0.22):
        ax.annotate("", xy=(cx + dx, y + 0.30), xytext=(cx + dx, y),
                    arrowprops=dict(arrowstyle="-|>", color=C_HEAT, lw=1.6))
    ax.plot([cx - 0.45, cx + 0.45], [y - 0.06, y - 0.06], color=C_HEAT, lw=2.4, zorder=3)
    if show and labels:
        ax.text(cx, y - 0.28, labels[key], fontsize=8.5, color=C_HEAT, ha="center", zorder=6)


def _condenser(ax, x0, y0, x1, y1, labels, show, key="condenser"):
    """Liebig condenser: jacket + inner tube + counter-current water arrows.
    Water enters at the LOWER end and leaves at the UPPER end — counter-current."""
    dx, dy = x1 - x0, y1 - y0
    length = math.hypot(dx, dy)
    ux, uy = dx / length, dy / length
    px, py = -uy, ux
    for off in (0.28, -0.28):
        ax.plot([x0 + px * off, x1 + px * off], [y0 + py * off, y1 + py * off], **_GLASS)
    for off in (0.11, -0.11):
        ax.plot([x0 + px * off, x1 + px * off], [y0 + py * off, y1 + py * off],
                color=C_GLASS, linewidth=1.1, zorder=3)
    for t in (0.0, 1.0):        # jacket end caps
        bx, by = x0 + dx * t, y0 + dy * t
        ax.plot([bx + px * 0.11, bx + px * 0.28], [by + py * 0.11, by + py * 0.28], **_GLASS)
        ax.plot([bx - px * 0.11, bx - px * 0.28], [by - py * 0.11, by - py * 0.28], **_GLASS)

    # Counter-current: cooling water always enters at the geometrically LOWER end and
    # leaves at the upper one, whichever way round the caller passed the endpoints.
    t_in, t_out = (0.86, 0.14) if y1 < y0 else (0.14, 0.86)
    inlet = (x0 + dx * t_in, y0 + dy * t_in)
    outlet = (x0 + dx * t_out, y0 + dy * t_out)
    ax.annotate("", xy=(inlet[0] - px * 0.28, inlet[1] - py * 0.28),
                xytext=(inlet[0] - px * 0.80, inlet[1] - py * 0.80),
                arrowprops=dict(arrowstyle="-|>", color=C_WATER, lw=1.6))
    ax.annotate("", xy=(outlet[0] + px * 0.80, outlet[1] + py * 0.80),
                xytext=(outlet[0] + px * 0.28, outlet[1] + py * 0.28),
                arrowprops=dict(arrowstyle="-|>", color=C_WATER, lw=1.6))
    if show:
        ax.text(inlet[0] - px * 0.88, inlet[1] - py * 0.88, "water in", fontsize=8,
                color=C_WATER, ha="right" if px > 0 else "left", va="center", zorder=6)
        ax.text(outlet[0] + px * 0.88, outlet[1] + py * 0.88, "water out", fontsize=8,
                color=C_WATER, ha="left" if px > 0 else "right", va="center", zorder=6)
        if abs(dy) > abs(dx):     # upright (reflux) condenser → label alongside it
            ax.text(x0 + 0.42, (y0 + y1) / 2, labels[key], fontsize=8.5,
                    color="#1B2631", ha="left", va="center", zorder=6)
        else:
            ax.text((x0 + x1) / 2 - px * 0.75, (y0 + y1) / 2 - py * 0.75, labels[key],
                    fontsize=8.5, color="#1B2631", ha="center", va="top", zorder=6)


def _thermometer(ax, x, y_bulb, height=1.1):
    ax.plot([x, x], [y_bulb, y_bulb + height], color="#7B241C", linewidth=2.2, zorder=4)
    ax.plot(x, y_bulb, "o", color="#C0392B", markersize=6, zorder=5)


def _conical_flask(ax, cx, base_y, w=0.72, h=0.95, liquid=True):
    neck = w * 0.30
    ax.plot([cx - w, cx + w], [base_y, base_y], **_GLASS)
    ax.plot([cx - w, cx - neck], [base_y, base_y + h], **_GLASS)
    ax.plot([cx + w, cx + neck], [base_y, base_y + h], **_GLASS)
    ax.plot([cx - neck, cx - neck], [base_y + h, base_y + h + 0.20], **_GLASS)
    ax.plot([cx + neck, cx + neck], [base_y + h, base_y + h + 0.20], **_GLASS)
    if liquid:
        lvl = 0.45
        xw = w - (w - neck) * lvl / h
        ax.fill([cx - w, cx + w, cx + xw, cx - xw],
                [base_y, base_y, base_y + lvl, base_y + lvl], color=C_LIQUID, zorder=2)
    return base_y + h + 0.20


def _stand(ax, x, y0, y1):
    ax.plot([x, x], [y0, y1], color="#5D6D7E", linewidth=3, zorder=1)
    ax.plot([x - 0.5, x + 0.5], [y0, y0], color="#5D6D7E", linewidth=5, zorder=1)


def _draw_simple_distillation(ax, labels, show, fractionating=False):
    fx, fy, fr = 1.5, 1.35, 0.72
    neck_h = 1.55 if fractionating else 0.55
    _rbf(ax, fx, fy, fr, neck_h=neck_h)
    _heat(ax, fx, 0.30, labels, show)
    _lab_text(ax, fx - 1.05, fy, "flask", labels, show, ha="right", va="center")

    if fractionating:
        # packed column between the flask and the still head
        for y in np.arange(fy + fr + 0.15, fy + fr + neck_h - 0.1, 0.18):
            ax.plot([fx - 0.16, fx + 0.16], [y, y + 0.09], color="#95A5A6",
                    linewidth=1.2, zorder=4)
        _lab_text(ax, fx - 0.35, fy + fr + neck_h * 0.6, "column", labels, show,
                  ha="right", va="center")

    head_y = fy + fr + neck_h            # still head / side-arm take-off level
    ax.plot([fx - 0.22, fx - 0.22], [head_y, head_y + 0.85], **_GLASS)
    ax.plot([fx + 0.22, fx + 0.22], [head_y, head_y + 0.85], **_GLASS)
    ax.plot([fx - 0.22, fx + 0.22], [head_y + 0.85, head_y + 0.85], **_GLASS)

    # THE exam trap: the bulb must sit level with the side-arm, so the thermometer
    # reads the temperature of the vapour actually leaving the flask.
    _thermometer(ax, fx, head_y, height=1.35)
    _lab_text(ax, fx + 0.12, head_y + 1.30, "thermometer", labels, show,
              ha="left", va="center")

    ax.plot([fx + 0.22, 2.95], [head_y, head_y], **_GLASS)        # side-arm
    ax.plot([fx + 0.22, 2.95], [head_y - 0.24, head_y - 0.24], **_GLASS)
    ax.annotate("", xy=(fx + 0.60, head_y - 0.12), xytext=(fx + 0.28, head_y - 0.12),
                arrowprops=dict(arrowstyle="-|>", color="#7F8C8D", lw=1.1))
    ax.plot([fx - 0.55, fx + 0.55], [head_y, head_y], color="#B03A2E",
            linestyle=":", linewidth=1.2, zorder=5)
    if show:
        ax.text(fx - 0.60, head_y + 0.06, labels["bulb"], fontsize=8,
                color="#B03A2E", ha="right", va="bottom", zorder=6)

    _condenser(ax, 3.0, head_y - 0.12, 6.1, head_y - 1.25, labels, show)
    ax.plot([6.15, 6.55], [head_y - 1.30, head_y - 1.75], **_GLASS)   # adapter
    top = _conical_flask(ax, 6.9, 0.55, liquid=True)
    ax.plot([6.55, 6.85], [head_y - 1.75, top], **_GLASS)
    _lab_text(ax, 6.9, 0.30, "receiver", labels, show, ha="center", va="top")
    if show:
        ax.text(4.1, -0.45, labels["note"], fontsize=8, color=C_ANNOT, ha="center")

    ax.set_xlim(-0.4, 8.6)
    ax.set_ylim(-0.7, head_y + 2.0)


def _draw_filtration(ax, labels, show):
    top = _conical_flask(ax, 2.4, 0.4, w=0.85, h=1.15, liquid=True)
    _lab_text(ax, 3.4, 0.75, "flask", labels, show, ha="left", va="center")
    _lab_text(ax, 3.4, 0.40, "filtrate", labels, show, ha="left", va="center")

    fy = top + 0.10
    ax.plot([1.55, 2.4], [fy + 1.0, fy], **_GLASS)      # funnel cone
    ax.plot([3.25, 2.4], [fy + 1.0, fy], **_GLASS)
    ax.plot([2.4, 2.4], [fy, fy - 0.35], **_GLASS)      # stem
    ax.plot([1.55, 3.25], [fy + 1.0, fy + 1.0], **_GLASS)
    ax.fill([1.75, 3.05, 2.4], [fy + 0.92, fy + 0.92, fy + 0.12],
            color="#FDEBD0", zorder=2)                   # filter paper
    ax.plot([1.75, 2.4, 3.05], [fy + 0.92, fy + 0.12, fy + 0.92],
            color="#B9770E", linewidth=1.2, zorder=3)
    ax.fill([2.05, 2.75, 2.4], [fy + 0.62, fy + 0.62, fy + 0.20],
            color="#A6ACAF", zorder=3)                   # residue
    _lab_text(ax, 1.45, fy + 1.05, "funnel", labels, show, ha="right", va="center")
    _lab_text(ax, 3.35, fy + 1.05, "paper", labels, show, ha="left", va="center")
    _lab_text(ax, 3.35, fy + 0.55, "residue", labels, show, ha="left", va="center")

    ax.plot([1.15, 1.75], [fy + 1.9, fy + 0.95], color="#7F8C8D", linewidth=2.4, zorder=3)
    _lab_text(ax, 1.05, fy + 1.95, "rod", labels, show, ha="right", va="center")
    if show:
        ax.text(2.4, 0.1, labels["note"], fontsize=8, color=C_ANNOT, ha="center")

    ax.set_xlim(-1.6, 6.4)
    ax.set_ylim(0.0, fy + 2.4)


def _draw_titration(ax, labels, show):
    bx, b_bot, b_top = 3.0, 2.05, 5.35
    _stand(ax, 1.4, 0.3, 5.6)
    ax.plot([1.4, bx], [4.9, 4.9], color="#5D6D7E", linewidth=3, zorder=1)
    for sx in (-0.14, 0.14):
        ax.plot([bx + sx, bx + sx], [b_bot, b_top], **_GLASS)
    ax.plot([bx - 0.14, bx + 0.14], [b_top, b_top], **_GLASS)
    ax.fill_between([bx - 0.14, bx + 0.14], b_bot + 0.15, b_top - 0.55,
                    color=C_LIQUID, zorder=2)
    for y in np.arange(b_bot + 0.3, b_top - 0.1, 0.32):       # graduations
        ax.plot([bx + 0.14, bx + 0.26], [y, y], color="#7F8C8D", linewidth=0.8, zorder=3)
    ax.plot(bx, b_bot, "o", color="#7F8C8D", markersize=7, zorder=5)   # stopcock
    ax.plot([bx, bx], [b_bot - 0.35, b_bot], **_GLASS)                 # jet
    ax.annotate("", xy=(bx, 1.72), xytext=(bx, b_bot - 0.32),
                arrowprops=dict(arrowstyle="-|>", color=C_WATER, lw=1.2))
    _lab_text(ax, bx + 0.35, (b_bot + b_top) / 2 + 0.6, "burette", labels, show,
              ha="left", va="center")
    _lab_text(ax, bx + 0.35, b_bot, "stopcock", labels, show, ha="left", va="center")

    _conical_flask(ax, bx, 0.55, w=0.80, h=1.05, liquid=True)
    ax.add_patch(mpatches.Rectangle((bx - 1.1, 0.35), 2.2, 0.2, facecolor="white",
                                    edgecolor=C_GLASS, linewidth=1.2, zorder=1))
    _lab_text(ax, bx + 0.95, 0.95, "flask", labels, show, ha="left", va="center")
    _lab_text(ax, bx + 1.2, 0.42, "tile", labels, show, ha="left", va="center")
    _lab_text(ax, 1.3, 5.7, "stand", labels, show, ha="center", va="bottom")
    if show:
        ax.text(bx, 0.05, labels["note"], fontsize=8, color=C_ANNOT, ha="center")

    ax.set_xlim(-0.4, 7.2)
    ax.set_ylim(-0.1, 6.2)


def _draw_reflux(ax, labels, show):
    fx, fy, fr = 2.6, 1.25, 0.75
    _rbf(ax, fx, fy, fr, neck_h=0.5)
    _heat(ax, fx, 0.18, labels, show)
    _lab_text(ax, fx - 1.05, fy, "flask", labels, show, ha="right", va="center")
    _condenser(ax, fx, fy + fr + 0.5, fx, fy + fr + 3.4, labels, show)
    if show:
        ax.text(fx, -0.55, labels["note"], fontsize=8, color=C_ANNOT, ha="center")
    ax.set_xlim(-0.6, 6.4)
    ax.set_ylim(-0.9, fy + fr + 4.2)


def _draw_steam_distillation(ax, labels, show):
    gx, gy, gr = 1.2, 1.2, 0.68
    _rbf(ax, gx, gy, gr, neck_h=0.55)
    _heat(ax, gx, 0.20, labels, show)
    ax.plot([gx - 0.42, gx - 0.42], [gy + gr + 0.55, gy + gr + 1.7], **_GLASS)   # safety tube
    ax.plot([gx - 0.52, gx - 0.32], [gy + gr + 1.7, gy + gr + 1.7], **_GLASS)
    _lab_text(ax, gx - 0.62, gy + gr + 1.6, "safety", labels, show, ha="right", va="center")
    _lab_text(ax, gx, -0.55, "generator", labels, show, ha="center", va="top")

    mx, my, mr = 3.7, 1.2, 0.70
    top = gy + gr + 0.55
    drop_x = mx - 0.11                                   # inside the neck of the flask
    ax.plot([gx + 0.22, drop_x], [top, top], **_GLASS)   # steam delivery tube
    ax.annotate("", xy=(2.5, top + 0.16), xytext=(1.7, top + 0.16),
                arrowprops=dict(arrowstyle="-|>", color="#7F8C8D", lw=1.2))
    ax.text(2.1, top + 0.26, "steam", fontsize=8, color="#7F8C8D", ha="center", zorder=6)

    _rbf(ax, mx, my, mr, neck_h=0.55)
    ax.plot([drop_x, drop_x], [top, my + 0.2], **_GLASS)  # dips into the mixture
    _lab_text(ax, mx, -0.55, "flask", labels, show, ha="center", va="top")

    head_y = my + mr + 0.55
    ax.plot([mx + 0.22, 5.0], [head_y, head_y], **_GLASS)
    _condenser(ax, 5.05, head_y, 7.4, head_y - 1.0, labels, show)
    tp = _conical_flask(ax, 8.0, 0.5, liquid=True)
    ax.plot([7.45, 7.95], [head_y - 1.05, tp], **_GLASS)
    _lab_text(ax, 8.0, 0.25, "receiver", labels, show, ha="center", va="top")
    if show:
        ax.text(4.2, -1.15, labels["note"], fontsize=8, color=C_ANNOT, ha="center")

    ax.set_xlim(-0.6, 9.6)
    ax.set_ylim(-1.5, head_y + 1.6)


def _draw_sublimation(ax, labels, show):
    dx, dy = 2.4, 0.9
    ax.plot([dx - 0.95, dx + 0.95], [dy, dy], **_GLASS)          # china dish
    th = np.linspace(math.pi, 2 * math.pi, 80)
    ax.plot(dx + 0.95 * np.cos(th), dy + 0.35 * np.sin(th), **_GLASS)
    ax.fill(dx + 0.85 * np.cos(th), dy + 0.30 * np.sin(th), color="#A6ACAF", zorder=2)
    _heat(ax, dx, 0.05, labels, show)
    _lab_text(ax, dx - 1.05, dy - 0.1, "dish", labels, show, ha="right", va="center")

    ax.plot([dx - 1.05, dx], [dy + 0.15, dy + 1.75], **_GLASS)   # inverted funnel
    ax.plot([dx + 1.05, dx], [dy + 0.15, dy + 1.75], **_GLASS)
    ax.plot([dx - 0.11, dx - 0.11], [dy + 1.75, dy + 2.45], **_GLASS)   # stem
    ax.plot([dx + 0.11, dx + 0.11], [dy + 1.75, dy + 2.45], **_GLASS)
    ax.add_patch(mpatches.Ellipse((dx, dy + 2.35), 0.30, 0.22, facecolor="#F7DC6F",
                                  edgecolor="#B7950B", linewidth=1, zorder=4))
    _lab_text(ax, dx + 0.22, dy + 2.35, "cotton", labels, show, ha="left", va="center")
    _lab_text(ax, dx + 1.15, dy + 0.30, "funnel", labels, show, ha="left", va="center")

    for t, s in ((0.35, -1), (0.55, -1), (0.45, 1), (0.65, 1)):   # sublimate deposits
        ax.plot(dx + s * (1.05 - 1.05 * t), dy + 0.15 + 1.60 * t, "o",
                color="#5B2C6F", markersize=3.5, zorder=5)
    for arr_x in (dx - 0.3, dx, dx + 0.3):
        ax.annotate("", xy=(arr_x, dy + 1.2), xytext=(arr_x, dy + 0.45),
                    arrowprops=dict(arrowstyle="-|>", color="#8E44AD", lw=1.0))
    _lab_text(ax, dx - 1.2, dy + 1.55, "sublimate", labels, show, ha="right", va="center")
    if show:
        ax.text(dx, -0.5, labels["note"], fontsize=8, color=C_ANNOT, ha="center")

    ax.set_xlim(-1.4, 6.2)
    ax.set_ylim(-0.9, dy + 3.1)


def _draw_separating_funnel(ax, labels, show):
    cx, top_y, bot_y = 2.6, 4.7, 2.35
    _stand(ax, 1.0, 0.3, 5.4)
    ax.plot([1.0, cx - 0.55], [3.4, 3.4], color="#5D6D7E", linewidth=3, zorder=1)
    ax.plot([cx - 0.85, cx - 0.85], [top_y, 3.55], **_GLASS)     # pear-shaped body
    ax.plot([cx + 0.85, cx + 0.85], [top_y, 3.55], **_GLASS)
    ax.plot([cx - 0.85, cx], [3.55, bot_y], **_GLASS)
    ax.plot([cx + 0.85, cx], [3.55, bot_y], **_GLASS)
    ax.plot([cx - 0.85, cx + 0.85], [top_y, top_y], **_GLASS)
    ax.plot([cx - 0.20, cx + 0.20], [top_y + 0.30, top_y + 0.30], **_GLASS)   # stopper
    ax.plot([cx - 0.20, cx - 0.20], [top_y, top_y + 0.30], **_GLASS)
    ax.plot([cx + 0.20, cx + 0.20], [top_y, top_y + 0.30], **_GLASS)

    iface = 4.05
    ax.fill([cx - 0.85, cx + 0.85, cx + 0.85, cx - 0.85],
            [iface, iface, top_y - 0.35, top_y - 0.35], color="#F9E79F", zorder=2)
    ax.fill([cx - 0.85, cx + 0.85, cx, cx],
            [iface, iface, bot_y, bot_y], color="#AED6F1", zorder=2)
    ax.plot([cx - 0.85, cx + 0.85], [iface, iface], color="#34495E",
            linewidth=1.2, linestyle="--", zorder=4)
    _lab_text(ax, cx + 0.95, (iface + top_y) / 2, "upper", labels, show,
              ha="left", va="center")
    _lab_text(ax, cx + 0.95, (iface + bot_y) / 2 + 0.15, "lower", labels, show,
              ha="left", va="center")
    _lab_text(ax, cx - 0.95, top_y - 0.1, "funnel", labels, show, ha="right", va="center")

    ax.plot(cx, bot_y - 0.12, "o", color="#7F8C8D", markersize=8, zorder=5)
    ax.plot([cx, cx], [bot_y - 0.55, bot_y - 0.12], **_GLASS)
    _lab_text(ax, cx + 0.25, bot_y - 0.12, "stopcock", labels, show, ha="left", va="center")

    ax.add_patch(mpatches.Rectangle((cx - 0.75, 0.4), 1.5, 1.15, facecolor="white",
                                    edgecolor=C_GLASS, linewidth=1.6, zorder=3))
    ax.add_patch(mpatches.Rectangle((cx - 0.72, 0.43), 1.44, 0.45, facecolor=C_LIQUID,
                                    edgecolor="none", zorder=2))
    _lab_text(ax, cx + 0.85, 0.9, "beaker", labels, show, ha="left", va="center")
    if show:
        ax.text(cx, 0.05, labels["note"], fontsize=8, color=C_ANNOT, ha="center")

    ax.set_xlim(-0.4, 7.0)
    ax.set_ylim(-0.1, 6.0)


def _draw_chromatography(ax, labels, show):
    jx0, jx1, jy0, jy1 = 1.4, 4.2, 0.5, 4.9
    ax.plot([jx0, jx0, jx1, jx1], [jy1, jy0, jy0, jy1], **_GLASS)
    ax.plot([jx0 - 0.12, jx1 + 0.12], [jy1, jy1], **_GLASS)      # lid
    ax.add_patch(mpatches.Rectangle((jx0, jy0), jx1 - jx0, 0.45, facecolor=C_LIQUID,
                                    edgecolor="none", zorder=2))
    _lab_text(ax, jx1 + 0.2, jy1 - 0.2, "jar", labels, show, ha="left", va="center")
    _lab_text(ax, jx0 - 0.2, jy0 + 0.2, "solvent", labels, show, ha="right", va="center")

    px = (jx0 + jx1) / 2
    ax.add_patch(mpatches.Rectangle((px - 0.55, jy0 + 0.15), 1.1, 4.05, facecolor="white",
                                    edgecolor=C_GLASS, linewidth=1.2, zorder=3))
    base_y, front_y = jy0 + 0.75, jy0 + 3.35
    ax.plot([px - 0.55, px + 0.55], [base_y, base_y], color="#566573",
            linewidth=1.0, linestyle="--", zorder=4)
    ax.plot([px - 0.55, px + 0.55], [front_y, front_y], color="#566573",
            linewidth=1.0, linestyle="--", zorder=4)
    for dx, sy, col in ((-0.25, 1.05, "#C0392B"), (0.0, 1.85, "#2471A3"),
                        (0.25, 2.55, "#1E8449")):
        ax.plot(px + dx, base_y + sy, "o", color=col, markersize=7, zorder=5)
    ax.plot(px - 0.25, base_y, "o", color="#7F8C8D", markersize=6, zorder=5)
    _lab_text(ax, px + 0.65, base_y, "baseline", labels, show, ha="left", va="center")
    _lab_text(ax, px + 0.65, front_y, "front", labels, show, ha="left", va="center")
    _lab_text(ax, px - 0.65, jy1 - 0.4, "paper", labels, show, ha="right", va="center")
    ax.annotate("", xy=(px + 0.95, front_y), xytext=(px + 0.95, base_y),
                arrowprops=dict(arrowstyle="<->", color=C_ANNOT, lw=1))
    if show:
        ax.text(px, jy0 - 0.35, labels["note"], fontsize=8.5, color=C_ANNOT, ha="center")

    ax.set_xlim(0.0, 8.2)
    ax.set_ylim(-0.6, 5.5)


def render_lab_apparatus(data: Dict[str, Any],
                         canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = LabApparatusSchema(**data)
    labels = dict(_APPARATUS_LABELS[schema.setup])
    labels.update(schema.labels)
    show = schema.show_labels

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))
    ax.set_aspect("equal")
    ax.axis("off")

    if schema.setup == "simple_distillation":
        _draw_simple_distillation(ax, labels, show, fractionating=False)
    elif schema.setup == "fractional_distillation":
        _draw_simple_distillation(ax, labels, show, fractionating=True)
    elif schema.setup == "filtration":
        _draw_filtration(ax, labels, show)
    elif schema.setup == "titration":
        _draw_titration(ax, labels, show)
    elif schema.setup == "reflux":
        _draw_reflux(ax, labels, show)
    elif schema.setup == "steam_distillation":
        _draw_steam_distillation(ax, labels, show)
    elif schema.setup == "sublimation":
        _draw_sublimation(ax, labels, show)
    elif schema.setup == "separating_funnel":
        _draw_separating_funnel(ax, labels, show)
    else:
        _draw_chromatography(ax, labels, show)

    title = schema.title or schema.setup.replace("_", " ").title()
    ax.set_title(title, fontsize=13, fontweight="bold", pad=6)
    fig.tight_layout()
    return _fig_to_svg(fig)


# ── Reaction Scheme (multi-step organic roadmap) ──────────────────────────────

# Structures come from RDKit as their own <svg>, spliced into the matplotlib output at
# a computed offset. Text stays on the matplotlib path: svgwrite's make_text() emits one
# <tspan> per sub/superscript run, and cairosvg — the print rasterizer — mis-advances
# those under text-anchor middle/end, which would shred every "conc. H₂SO₄" on the page.
DPI = 100
_MPL_UNITS_PER_PX = 72.0 / DPI     # matplotlib writes SVG user units in points

C_UNKNOWN = "#B03A2E"
C_REAGENT = "#1A252F"
C_CONDITION = "#566573"

CELL_W, CELL_H = 150.0, 150.0
STRUCT_W, STRUCT_H = 134.0, 104.0
SCHEME_MARGIN = 34.0
SCHEME_GUTTER = 130.0       # room for a wrap elbow AND its reagent/conditions


def _mol_fragment(smiles: str, w: float, h: float) -> str:
    if not RDKIT_AVAILABLE:
        raise ValueError("RDKit is required to draw a structure from SMILES")
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"Invalid SMILES string: '{smiles}'")
    AllChem.Compute2DCoords(mol)
    drawer = rdMolDraw2D.MolDraw2DSVG(max(int(round(w)), 20), max(int(round(h)), 20))
    drawer.drawOptions().useBWAtomPalette()
    drawer.drawOptions().clearBackground = False    # sit on the canvas, not on a white tile
    drawer.DrawMolecule(mol)
    drawer.FinishDrawing()
    svg = drawer.GetDrawingText()
    return svg[svg.index("<svg"):]


def _splice_structures(svg: str, fig, ax, boxes: List[Tuple[float, float, float, float, str]]) -> str:
    """Drop each SMILES into its data-coordinate box (x_left, y_top, w, h)."""
    if not boxes:
        return svg
    h_px = fig.get_figheight() * DPI
    parts = []
    for x0, y_top, w, h, smiles in boxes:
        px0, py0 = ax.transData.transform((x0, y_top))
        px1, py1 = ax.transData.transform((x0 + w, y_top - h))
        sx, sy = px0 * _MPL_UNITS_PER_PX, (h_px - py0) * _MPL_UNITS_PER_PX
        sw, sh = (px1 - px0) * _MPL_UNITS_PER_PX, (py0 - py1) * _MPL_UNITS_PER_PX
        parts.append(f'<g transform="translate({sx:.2f},{sy:.2f})">'
                     f'{_mol_fragment(smiles, sw, sh)}</g>')
    return svg.replace("</svg>", "".join(parts) + "</svg>")


def _harpoon(ax, tip, u, perp, length: float):
    """One half-headed arrow: the barb sits on ONE side only."""
    tail = (tip[0] - u[0] * length, tip[1] - u[1] * length)
    ax.plot([tail[0], tip[0]], [tail[1], tip[1]], color="black", linewidth=1.5,
            solid_capstyle="butt", zorder=3)
    barb = (tip[0] - u[0] * 9.0 + perp[0] * 4.5, tip[1] - u[1] * 9.0 + perp[1] * 4.5)
    ax.plot([tip[0], barb[0]], [tip[1], barb[1]], color="black", linewidth=1.5,
            solid_capstyle="round", zorder=3)


def _reaction_arrow(ax, p0, p1, arrow_type: str):
    """Works along any axis, so the wrap elbow and the branch arrow get the same
    treatment as a plain horizontal step."""
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    length = math.hypot(dx, dy)
    if length < 1e-6:
        return
    if arrow_type == "forward":
        ax.annotate("", xy=p1, xytext=p0,
                    arrowprops=dict(arrowstyle="-|>", color="black", lw=1.6,
                                    shrinkA=0, shrinkB=0, mutation_scale=14))
        return
    # reversible / equilibrium both draw ⇌ — two opposed harpoons. A double-HEADED
    # arrow (↔) is the resonance symbol and must never stand in for reversibility.
    ux, uy = dx / length, dy / length
    px, py = -uy, ux
    off = 3.4
    _harpoon(ax, (p1[0] + px * off, p1[1] + py * off), (ux, uy), (px, py), length)
    _harpoon(ax, (p0[0] - px * off, p0[1] - py * off), (-ux, -uy), (-px, -py), length)


def _step_text(ax, xc: float, y: float, reagent: str, conditions: str):
    """Reagent ABOVE the arrow, conditions BELOW it. This convention is not decorative —
    it is how every exam paper prints a reaction step."""
    if reagent:
        ax.text(xc, y + 11.0, reagent, ha="center", va="bottom", fontsize=10,
                color=C_REAGENT, zorder=5)
    if conditions:
        ax.text(xc, y - 12.0, conditions, ha="center", va="top", fontsize=9,
                color=C_CONDITION, zorder=5)


def _scheme_species(schema: ReactionSchemeSchema) -> Dict[str, ReactionSpecies]:
    known = {sp.label: sp for sp in schema.species}
    for st in schema.steps:
        for lb in (st.from_label, st.to_label):
            known.setdefault(lb, ReactionSpecies(label=lb))
    return known


def _scheme_chain(schema: ReactionSchemeSchema) -> Tuple[List[str], List, List]:
    """(main chain, steps along it, steps that branch off an earlier node)."""
    chain = [schema.steps[0].from_label]
    main, branches = [], []
    for st in schema.steps:
        if st.from_label == chain[-1]:
            main.append(st)
            chain.append(st.to_label)
        else:
            branches.append(st)
    return chain, main, branches


def _arrow_length(schema: ReactionSchemeSchema) -> float:
    """Long enough that the reagent and the conditions clear the structures either side."""
    longest = 0
    for st in schema.steps:
        longest = max(longest, len(st.reagent), len(st.conditions))
    return float(min(max(118.0, 6.8 * longest), 250.0))


def _draw_species_cell(ax, sp: ReactionSpecies, cx: float, cy: float,
                       show_structures: bool, boxes: list):
    """cy is the vertical centre of the structure area."""
    ax.text(cx, cy + STRUCT_H / 2 + 22.0, sp.label, ha="center", va="center",
            fontsize=13, fontweight="bold", color="#1A5276", zorder=6,
            bbox=dict(boxstyle="circle,pad=0.30", facecolor="#EAF2F8",
                      edgecolor="#1A5276", linewidth=1.3))

    if sp.is_unknown:
        # The question is "identify B" — the box has to read as a blank to be filled in.
        ax.add_patch(mpatches.FancyBboxPatch(
            (cx - STRUCT_W / 2 + 12, cy - STRUCT_H / 2 + 6), STRUCT_W - 24, STRUCT_H - 12,
            boxstyle="round,pad=4", facecolor="#FDF2E9", edgecolor=C_UNKNOWN,
            linewidth=2.4, linestyle="--", zorder=3))
        ax.text(cx, cy, "?", ha="center", va="center", fontsize=44, fontweight="bold",
                color=C_UNKNOWN, zorder=5)
    elif show_structures and sp.smiles:
        boxes.append((cx - STRUCT_W / 2, cy + STRUCT_H / 2, STRUCT_W, STRUCT_H, sp.smiles))
    else:
        ax.text(cx, cy, sp.formula or sp.name or sp.label, ha="center", va="center",
                fontsize=13, fontweight="bold", color="#1A252F", zorder=5)

    caption = sp.name if (sp.name and not sp.is_unknown) else (
        sp.formula if (sp.formula and show_structures and sp.smiles) else "")
    if caption:
        ax.text(cx, cy - STRUCT_H / 2 - 12.0, caption, ha="center", va="top",
                fontsize=9, color=C_CONDITION, zorder=5)


def render_reaction_scheme(data: Dict[str, Any],
                           canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = ReactionSchemeSchema(**data)
    species = _scheme_species(schema)
    chain, main_steps, branch_steps = _scheme_chain(schema)

    arrow_len = _arrow_length(schema)
    if schema.layout == "branched":
        per_row = len(chain)
    elif schema.layout == "grid":
        per_row = min(3, len(chain))
    else:
        usable = canvas_w - 2 * SCHEME_MARGIN
        per_row = int((usable + arrow_len) // (CELL_W + arrow_len))
        per_row = max(1, min(per_row, len(chain)))

    rows = max(1, math.ceil(len(chain) / per_row))
    n_branch_rows = 1 if (schema.layout == "branched" and branch_steps) else 0

    W = float(canvas_w)
    if schema.layout == "branched":
        row_w = per_row * CELL_W + (per_row - 1) * arrow_len
        W = max(W, row_w + 2 * SCHEME_MARGIN)

    title_h = 42.0
    H = (title_h + rows * CELL_H + (rows - 1) * SCHEME_GUTTER
         + n_branch_rows * (CELL_H + SCHEME_GUTTER) + 2 * SCHEME_MARGIN)

    fig, ax = plt.subplots(figsize=(W / DPI, H / DPI), dpi=DPI)
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.set_aspect("equal")
    ax.axis("off")

    def row_centre_y(r: int) -> float:
        return H - title_h - SCHEME_MARGIN - CELL_H / 2 - r * (CELL_H + SCHEME_GUTTER)

    pos: Dict[str, Tuple[float, float]] = {}
    for i, label in enumerate(chain):
        r, c = divmod(i, per_row)
        in_row = min(per_row, len(chain) - r * per_row)
        row_w = in_row * CELL_W + (in_row - 1) * arrow_len
        x0 = (W - row_w) / 2
        pos[label] = (x0 + c * (CELL_W + arrow_len) + CELL_W / 2, row_centre_y(r))

    boxes: List[Tuple[float, float, float, float, str]] = []
    for label in chain:
        cx, cy = pos[label]
        _draw_species_cell(ax, species[label], cx, cy, schema.show_structures, boxes)

    for st in main_steps:
        (x_from, y_from), (x_to, y_to) = pos[st.from_label], pos[st.to_label]
        if abs(y_from - y_to) < 1e-6:
            a0, a1 = x_from + CELL_W / 2, x_to - CELL_W / 2
            _reaction_arrow(ax, (a0, y_from), (a1, y_from), st.arrow_type)
            _step_text(ax, (a0 + a1) / 2, y_from, st.reagent, st.conditions)
        else:
            # Row wrap: out of the right edge, back across the gutter, into the left edge
            # of the next row. The head goes where the arrow ARRIVES; a reversible step
            # gets a second head back into its source. Harpoons are not used here — a ⇌
            # only reads correctly on a straight run, not around an elbow.
            mid_y = (y_from - CELL_H / 2 + y_to + CELL_H / 2) / 2
            rx, lx = x_from + CELL_W / 2 + 16, x_to - CELL_W / 2 - 16
            ax.plot([x_from + CELL_W / 2, rx, rx, lx, lx, x_to - CELL_W / 2],
                    [y_from, y_from, mid_y, mid_y, y_to, y_to],
                    color="black", linewidth=1.6, solid_joinstyle="round", zorder=3)
            _reaction_arrow(ax, (lx, y_to), (x_to - CELL_W / 2, y_to), "forward")
            if st.arrow_type != "forward":
                _reaction_arrow(ax, (rx, y_from), (x_from + CELL_W / 2, y_from), "forward")
            _step_text(ax, (rx + lx) / 2, mid_y, st.reagent, st.conditions)

    for st in branch_steps:
        if st.from_label not in pos:
            continue
        px, py = pos[st.from_label]
        by = py - (CELL_H + SCHEME_GUTTER)
        pos[st.to_label] = (px, by)
        _draw_species_cell(ax, species[st.to_label], px, by, schema.show_structures, boxes)
        a0, a1 = py - CELL_H / 2 - 16, by + CELL_H / 2 + 40   # clear the caption and the chip
        _reaction_arrow(ax, (px, a0), (px, a1), st.arrow_type)
        # A vertical arrow has no "above"/"below": reagent right, conditions left.
        if st.reagent:
            ax.text(px + 12, (a0 + a1) / 2, st.reagent, ha="left", va="center",
                    fontsize=10, color=C_REAGENT, zorder=5)
        if st.conditions:
            ax.text(px - 12, (a0 + a1) / 2, st.conditions, ha="right", va="center",
                    fontsize=9, color=C_CONDITION, zorder=5)

    if any(species[lb].is_unknown for lb in pos):
        ax.text(W / 2, SCHEME_MARGIN * 0.5, "Identify the boxed species",
                ha="center", va="center", fontsize=10, color=C_UNKNOWN,
                fontweight="bold", zorder=5)

    ax.text(W / 2, H - title_h / 2, schema.title or "Reaction Scheme",
            ha="center", va="center", fontsize=14, fontweight="bold", zorder=5)

    svg = _fig_to_svg(fig, bbox=None)   # fixed viewport → the splice offsets stay valid
    return _splice_structures(svg, fig, ax, boxes)


# ── Crystal Field Splitting ───────────────────────────────────────────────────

# Orbital sets, ascending in energy, with each set's energy in units of the splitting Δ.
# The e/t2 order INVERTS between octahedral and tetrahedral: with the ligands pointing
# between the axes, it is the t2 set (dxy, dyz, dxz) that is destabilised, so e lies
# BELOW t2. Square-planar energies are the standard Huheey set and sum to zero about
# the barycentre.
_CFS_SETS: Dict[str, List[Tuple[str, int, float]]] = {
    "octahedral": [("t₂g", 3, -0.4), ("eg", 2, 0.6)],
    "tetrahedral": [("e", 2, -0.6), ("t₂", 3, 0.4)],
    "square_planar": [("dxz, dyz", 2, -0.514), ("dz²", 1, -0.428),
                      ("dxy", 1, 0.228), ("dx²−y²", 1, 1.228)],
}

_CFS_NAME = {"octahedral": "Octahedral", "tetrahedral": "Tetrahedral",
             "square_planar": "Square Planar"}

_DELTA_T_FACTOR = 4.0 / 9.0     # Δt = (4/9)·Δo — four ligands, none on an axis


def _delta_t(delta_o: float = 1.0) -> float:
    return _DELTA_T_FACTOR * delta_o


def _cfs_fill(sets: List[Tuple[str, int, float]], d_electrons: int,
              low_spin: bool) -> List[int]:
    """Occupancy per orbital, orbitals listed in ascending energy."""
    energies = [e for _lbl, n, e in sets for _ in range(n)]
    occ = [0] * len(energies)
    if low_spin:
        # Pairing costs less than the gap: fill each set right up (Hund still applies
        # WITHIN a degenerate set) before touching the next one.
        base, left = 0, d_electrons
        for _lbl, n, _e in sets:
            take = min(left, 2 * n)
            for k in range(min(take, n)):
                occ[base + k] = 1
            for k in range(take - min(take, n)):
                occ[base + k] = 2
            left -= take
            base += n
    else:
        # The gap costs more than pairing: singly occupy every orbital before any pairs.
        singles = min(d_electrons, len(energies))
        for k in range(singles):
            occ[k] = 1
        left = d_electrons - singles
        for k in range(len(energies)):
            if left <= 0:
                break
            occ[k] = 2
            left -= 1
    return occ


def _cfs_build(schema: CrystalFieldSplittingSchema) -> Dict[str, Any]:
    sets = _CFS_SETS[schema.geometry]
    # Δt is only ~4/9 of Δo and is always smaller than the pairing energy, so no
    # tetrahedral complex is ever low-spin. Params claiming otherwise are overruled.
    forced = schema.geometry == "tetrahedral" and schema.ligand_field == "strong"
    low_spin = (schema.ligand_field == "strong") and schema.geometry != "tetrahedral"

    occ = _cfs_fill(sets, schema.d_electrons, low_spin)
    energies = [e for _lbl, n, e in sets for _ in range(n)]
    # −1.2 + 1.2 is not 0 in binary, and "CFSE = +1.11e-16·Δo" on an exam paper is a bug.
    cfse = round(sum(o * e for o, e in zip(occ, energies)), 6) + 0.0
    unpaired = sum(1 for o in occ if o == 1)
    pairs = sum(1 for o in occ if o == 2)

    per_set, base = [], 0
    for lbl, n, e in sets:
        per_set.append({"label": lbl, "energy": e, "occ": occ[base:base + n]})
        base += n

    return {
        "sets": per_set, "occ": occ, "cfse": cfse, "unpaired": unpaired, "pairs": pairs,
        "low_spin": low_spin, "forced_high_spin": forced,
        "spin_state": "Low-spin" if low_spin else "High-spin",
        "delta_symbol": "Δt" if schema.geometry == "tetrahedral" else "Δo",
        "magnetism": "Paramagnetic" if unpaired else "Diamagnetic",
        "mu": math.sqrt(unpaired * (unpaired + 2.0)),
        "name": _CFS_NAME[schema.geometry],
    }


def render_crystal_field_splitting(data: Dict[str, Any],
                                   canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = CrystalFieldSplittingSchema(**data)
    built = _cfs_build(schema)
    sets = built["sets"]
    sym = built["delta_symbol"]

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))
    ax.set_xlim(0, 10)
    ax.set_ylim(-1.05, 1.45)
    ax.axis("off")

    BOX_H, ARROW_H = 0.11, 0.085     # the arrow has to sit INSIDE its orbital box
    bw, gap = 0.44, 0.10

    ax.axhline(0.0, xmin=0.14, xmax=0.86, color="#7F8C8D", linestyle="--", linewidth=1.1)
    ax.text(1.20, 0.0, "barycentre\n(spherical field)", ha="right", va="center",
            fontsize=8.5, color=C_ANNOT)

    n_sets = len(sets)
    x_centres = ([3.9, 6.5] if n_sets == 2
                 else [2.9 + i * (4.4 / max(n_sets - 1, 1)) for i in range(n_sets)])

    right_edge = {}
    for xc, s in zip(x_centres, sets):
        y = s["energy"]
        total = len(s["occ"]) * bw + (len(s["occ"]) - 1) * gap
        x0 = xc - total / 2
        right_edge[id(s)] = x0 + total
        for i, e in enumerate(s["occ"]):
            bx = x0 + i * (bw + gap)
            ax.add_patch(mpatches.Rectangle((bx, y - BOX_H / 2), bw, BOX_H, linewidth=1.5,
                                            edgecolor="#1A5276", facecolor="#EAF2F8",
                                            zorder=3))
            if schema.show_electron_filling:
                if e >= 1:
                    _spin_arrow(ax, bx + bw * 0.30, y, up=True, h=ARROW_H)
                if e == 2:
                    _spin_arrow(ax, bx + bw * 0.70, y, up=False, h=ARROW_H)
        # White bbox: the barycentre line runs the full width and would otherwise be
        # struck straight through any label that happens to sit near zero.
        ax.text(xc, y - BOX_H / 2 - 0.09, s["label"], ha="center", va="top", fontsize=11,
                fontweight="bold", color="#1A5276", zorder=5,
                bbox=dict(boxstyle="round,pad=0.12", facecolor="white", edgecolor="none"))

    if schema.show_splitting_energy and n_sets == 2:
        y_lo, y_hi = sets[0]["energy"], sets[1]["energy"]
        xa = 8.7
        ax.annotate("", xy=(xa, y_hi), xytext=(xa, y_lo),
                    arrowprops=dict(arrowstyle="<->", color="#B03A2E", lw=1.6))
        for s, yy in ((sets[0], y_lo), (sets[1], y_hi)):
            ax.plot([right_edge[id(s)] + 0.08, xa], [yy, yy], color="#B03A2E",
                    linestyle=":", linewidth=0.9)
        ax.text(xa + 0.15, (y_lo + y_hi) / 2, sym, ha="left", va="center", fontsize=13,
                fontweight="bold", color="#B03A2E")
        if schema.geometry == "tetrahedral":
            ax.text(xa + 0.15, (y_lo + y_hi) / 2 - 0.20, "= (4/9)·Δo", ha="left",
                    va="center", fontsize=9, color="#B03A2E")

    facts = [f"{schema.metal_ion}   d{schema.d_electrons}   {built['name']}   "
             f"— {built['spin_state']} ({schema.ligand_field} field)"]
    if schema.show_cfse:
        facts.append(f"CFSE = {built['cfse']:g}·{sym}")
    if schema.show_magnetic_behaviour:
        facts.append(f"{built['magnetism']} — {built['unpaired']} unpaired e⁻ "
                     f"(μ = {built['mu']:.2f} BM)")
    if schema.show_pairing_energy:
        rel = ("P > " + sym) if not built["low_spin"] else ("P < " + sym)
        facts.append(f"Pairing energy P: {rel} → {built['spin_state'].lower()}")
    if built["forced_high_spin"]:
        facts.append("Δt is far smaller than the pairing energy — a tetrahedral "
                     "complex is ALWAYS high-spin")

    # Footer, not an overlay: the eg / dx²−y² box sits high enough to collide with a
    # top-left panel.
    for i, line in enumerate(facts):
        red = built["forced_high_spin"] and i == len(facts) - 1
        ax.text(0.0, -0.02 - 0.058 * i, line, transform=ax.transAxes, fontsize=10,
                va="top", ha="left", color="#B03A2E" if red else "#1A252F",
                fontweight="bold" if (i == 0 or red) else "normal")

    title = schema.title or f"Crystal Field Splitting: {built['name']} {schema.metal_ion}"
    ax.set_title(title, fontsize=13, fontweight="bold")
    fig.tight_layout()
    return _fig_to_svg(fig)


# ── Chemical Kinetics Graph ───────────────────────────────────────────────────

_R_KJ = 8.314e-3      # kJ mol⁻¹ K⁻¹ — Ea is quoted in kJ/mol


def _conc_profile(order: int, k: float, a0: float, t: np.ndarray) -> np.ndarray:
    """[A] at time t, DERIVED from the order. Never a supplied shape."""
    if order == 0:
        return np.maximum(a0 - k * t, 1e-9)
    if order == 1:
        return a0 * np.exp(-k * t)
    return a0 / (1.0 + k * a0 * t)


def _time_span(order: int, k: float, a0: float) -> float:
    """Long enough to show the shape, short enough that [A] stays positive (ln needs it)."""
    if order == 0:
        return 0.9 * a0 / k
    if order == 1:
        return 3.0 / k
    return 9.0 / (k * a0)


def _half_life(order: int, k: float, a0: float) -> float:
    if order == 0:
        return a0 / (2.0 * k)
    if order == 1:
        return math.log(2.0) / k          # independent of a0 — that IS the question
    return 1.0 / (k * a0)


def _r_squared(x: np.ndarray, y: np.ndarray) -> float:
    """Coefficient of determination of the best straight line through (x, y)."""
    slope, intercept = np.polyfit(x, y, 1)
    resid = y - (slope * x + intercept)
    ss_res = float(np.sum(resid ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    # A constant y (first-order t½ against [A]₀) is a perfect horizontal line, but its
    # ss_tot is pure float dust — dividing by it prints R² = −2.5 on a flat graph.
    scale = float(np.mean(np.abs(y))) ** 2 * len(y)
    if ss_tot <= 1e-18 * max(scale, 1.0):
        return 1.0
    return 1.0 - ss_res / ss_tot


def _arrhenius_series(activation_energy: float, t_range: Tuple[float, float],
                      pre_exponential: float = 1e10):
    """ln k against 1/T. The slope is −Ea/R and nothing else."""
    t = np.linspace(t_range[0], t_range[1], 60)
    inv_t = 1.0 / t
    ln_k = math.log(pre_exponential) - activation_energy / (_R_KJ * t)
    return inv_t, ln_k


def _kinetics_series(schema: KineticsGraphSchema):
    """(x, y, x_label, y_label, linear_for_this_order)."""
    order, k, a0 = schema.order, schema.rate_constant, schema.initial_concentration
    plot = schema.plot

    if plot == "arrhenius":
        x, y = _arrhenius_series(schema.activation_energy, schema.temperature_range)
        return x, y, "1/T  (K⁻¹)", "ln k", True

    if plot == "rate_vs_concentration":
        a = np.linspace(0.0, a0, 200)
        rate = k * a ** order
        return a, rate, "[A]  (mol L⁻¹)", "Rate  (mol L⁻¹ s⁻¹)", order in (0, 1)

    if plot == "half_life":
        a = np.linspace(0.2 * a0, 2.0 * a0, 200)
        t_half = np.array([_half_life(order, k, float(c)) for c in a])
        return a, t_half, "[A]₀  (mol L⁻¹)", "t½  (s)", order in (0, 1)

    t = np.linspace(0.0, _time_span(order, k, a0), 200)
    conc = _conc_profile(order, k, a0, t)
    if plot == "concentration_time":
        return t, conc, "Time  (s)", "[A]  (mol L⁻¹)", order == 0
    if plot == "ln_concentration_time":
        return t, np.log(conc), "Time  (s)", "ln [A]", order == 1
    return t, 1.0 / conc, "Time  (s)", "1/[A]  (L mol⁻¹)", order == 2


_LINEARISES = {0: "[A] vs t", 1: "ln [A] vs t", 2: "1/[A] vs t"}


def render_kinetics_graph(data: Dict[str, Any],
                          canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = KineticsGraphSchema(**data)
    x, y, x_label, y_label, is_linear = _kinetics_series(schema)

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))
    ax.plot(x, y, color="#1F77B4", linewidth=2.4, zorder=3)

    slope, intercept = np.polyfit(x, y, 1)
    r2 = _r_squared(x, y)

    # The slope is only worth annotating where it HAS a name. Printing "slope = −4e−15"
    # under a flat first-order t½ plot teaches nothing.
    meaning = None
    if schema.plot == "arrhenius":
        meaning = (f"slope = −Ea/R = {slope:,.0f} K\n"
                   f"Ea = {schema.activation_energy:g} kJ/mol")
    elif schema.plot == "ln_concentration_time" and schema.order == 1:
        meaning = f"slope = −k = {slope:.4g} s⁻¹"
    elif schema.plot == "inverse_concentration_time" and schema.order == 2:
        meaning = f"slope = +k = {slope:.4g} L mol⁻¹ s⁻¹"
    elif schema.plot == "concentration_time" and schema.order == 0:
        meaning = f"slope = −k = {slope:.4g} mol L⁻¹ s⁻¹"
    elif schema.plot == "rate_vs_concentration" and schema.order == 1:
        meaning = f"slope = k = {slope:.4g} s⁻¹"

    if schema.show_slope and is_linear and meaning:
        ax.plot(x, slope * x + intercept, color="#B03A2E", linestyle="--",
                linewidth=1.2, zorder=2)
        ax.text(0.03, 0.06, meaning, transform=ax.transAxes, fontsize=10,
                color="#B03A2E", fontweight="bold", va="bottom",
                bbox=dict(boxstyle="round,pad=0.35", facecolor="white",
                          edgecolor="#B03A2E", alpha=0.92))

    if schema.show_half_life and schema.plot == "concentration_time":
        t_half = _half_life(schema.order, schema.rate_constant,
                            schema.initial_concentration)
        if t_half <= x[-1]:
            half_c = schema.initial_concentration / 2.0
            ax.plot([t_half, t_half], [0, half_c], color="#7D3C98", linestyle=":", lw=1.3)
            ax.plot([0, t_half], [half_c, half_c], color="#7D3C98", linestyle=":", lw=1.3)
            ax.plot(t_half, half_c, "o", color="#7D3C98", markersize=7, zorder=5)
            ax.annotate(f"t½ = {t_half:.3g} s", xy=(t_half, half_c),
                        xytext=(14, 16), textcoords="offset points", fontsize=9.5,
                        color="#7D3C98", fontweight="bold",
                        arrowprops=dict(arrowstyle="->", color="#7D3C98", lw=1))

    if schema.show_linearity_note:
        # Which plot linearises which order is THE question — but only for the three
        # concentration-against-time axes. On a t½ or Arrhenius plot the claim is a
        # non-sequitur.
        note = None
        if schema.plot in ("concentration_time", "ln_concentration_time",
                           "inverse_concentration_time"):
            if is_linear:
                note = (f"Straight line (R² = {r2:.3f}) → order {schema.order}. "
                        f"Only {_LINEARISES[schema.order]} linearises this order.")
            else:
                note = (f"Curved (R² = {r2:.3f}) → NOT order {schema.order} on these "
                        f"axes. Order {schema.order} is linear on "
                        f"{_LINEARISES[schema.order]}.")
        elif schema.plot == "arrhenius":
            note = "ln k against 1/T is a straight line of slope −Ea/R for every order."
        elif schema.plot == "rate_vs_concentration":
            shape = {0: "horizontal — rate is independent of [A]",
                     1: "a straight line through the origin, slope k",
                     2: "a parabola (rate ∝ [A]²)"}[schema.order]
            note = f"rate = k[A]^{schema.order} → {shape}."
        if note:
            ax.text(0.5, -0.16, note, transform=ax.transAxes, fontsize=9.5, ha="center",
                    va="top", color="#1A252F" if is_linear else C_ANNOT)

    if schema.plot == "half_life":
        # The rule IS the plot — never gate it behind show_half_life.
        rule = {0: "t½ = [A]₀/2k — PROPORTIONAL to [A]₀",
                1: "t½ = ln2/k — INDEPENDENT of [A]₀",
                2: "t½ = 1/(k[A]₀) — INVERSELY proportional to [A]₀"}[schema.order]
        # Footer slot — the linearity note is suppressed on this plot, and anywhere
        # inside the axes would sit on one of the three curves.
        ax.text(0.5, -0.16, rule, transform=ax.transAxes, fontsize=10.5, ha="center",
                va="top", color="#7D3C98", fontweight="bold")

    ax.set_xlabel(x_label, fontsize=11)
    ax.set_ylabel(y_label, fontsize=11)
    ax.set_title(schema.title or f"Order {schema.order}: {schema.plot.replace('_', ' ')}",
                 fontsize=13, fontweight="bold")
    ax.grid(True, linestyle=":", linewidth=0.5, color="#D5D8DC")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return _fig_to_svg(fig)


# ── Colligative Properties Graph ──────────────────────────────────────────────

_DH_VAP = 40700.0                  # J/mol, water
_DH_FUS = 6010.0                   # J/mol, ice → water
# Hess: sublimation = fusion + vaporisation. Inventing ΔH_sub independently makes the
# implied ΔH_fus wrong, and the ΔTf read off the graph then contradicts Kf·m in the
# caption (Kf = R·Tf²·M / 1000·ΔH_fus is fixed by ΔH_fus alone).
_DH_SUB = _DH_VAP + _DH_FUS
_T_BOIL = 373.15
_T_FREEZE = 273.15


def _vp_liquid(t_k: np.ndarray) -> np.ndarray:
    """Vapour pressure of the pure solvent (atm), Clausius–Clapeyron about the b.p."""
    return np.exp(-(_DH_VAP / _R_GAS) * (1.0 / t_k - 1.0 / _T_BOIL))


def _vp_solid(t_k: np.ndarray) -> np.ndarray:
    p_triple = float(np.exp(-(_DH_VAP / _R_GAS) * (1.0 / _T_FREEZE - 1.0 / _T_BOIL)))
    return p_triple * np.exp(-(_DH_SUB / _R_GAS) * (1.0 / t_k - 1.0 / _T_FREEZE))


def _cross(t: np.ndarray, curve: np.ndarray, target: float) -> float:
    """Temperature at which a monotonically rising curve reaches `target`."""
    return float(np.interp(target, curve, t))


def _zero_crossing(t: np.ndarray, f: np.ndarray) -> float:
    """Where f changes sign. np.interp needs an INCREASING x, and (solution − solid)
    decreases through the freezing point, so interpolating it directly returns nonsense
    and throws the whole figure off its axes."""
    sign = np.sign(f)
    idx = np.flatnonzero(sign[:-1] * sign[1:] < 0)
    if not len(idx):
        return float(t[int(np.argmin(np.abs(f)))])
    i = int(idx[0])
    f0, f1 = float(f[i]), float(f[i + 1])
    w = f0 / (f0 - f1) if f0 != f1 else 0.0
    return float(t[i] + w * (t[i + 1] - t[i]))


_M_SOLVENT = 18.0      # g/mol, water


def _mole_fraction_from_molality(molality: float) -> float:
    """x(solute) for a molal solution — 1 kg of solvent is 1000/M moles of it. The graph
    has to be built from the SAME solution the Kb·m caption describes, or the ΔTb read
    off the picture contradicts the equation printed under it."""
    n_solvent = 1000.0 / _M_SOLVENT
    return molality / (molality + n_solvent)


def _colligative_facts(schema: ColligativeGraphSchema) -> Dict[str, Any]:
    """ΔTb and ΔTf read off the geometry, cross-checked against Kb·m / Kf·m."""
    x_solute = _mole_fraction_from_molality(schema.molality)
    x_solvent = 1.0 - x_solute
    t = np.linspace(_T_FREEZE - 15.0, _T_BOIL + 15.0, 6000)
    pure = _vp_liquid(t)
    soln = x_solvent * pure                    # Raoult: the solution's curve lies BELOW
    solid = _vp_solid(t)

    tb_pure = _cross(t, pure, 1.0)
    tb_soln = _cross(t, soln, 1.0)
    # Freezing point = where the SOLUTION's liquid curve meets the solid curve.
    tf_soln = _zero_crossing(t, soln - solid)
    tf_pure = _zero_crossing(t, pure - solid)

    return {
        "t": t, "pure": pure, "soln": soln, "solid": solid,
        "x_solute": x_solute, "x_solvent": x_solvent,
        "tb_pure": tb_pure, "tb_soln": tb_soln, "delta_tb_graph": tb_soln - tb_pure,
        "tf_pure": tf_pure, "tf_soln": tf_soln, "delta_tf_graph": tf_pure - tf_soln,
        "delta_tb_law": schema.kb * schema.molality,
        "delta_tf_law": schema.kf * schema.molality,
    }


def _draw_vp_temperature(ax, schema: ColligativeGraphSchema, facts: Dict[str, Any],
                         freezing: bool):
    t, pure, soln, solid = facts["t"], facts["pure"], facts["soln"], facts["solid"]
    # Window scaled to the shift being measured, so ΔT is a readable fraction of the
    # axis instead of a hairline at any molality.
    if freezing:
        d = max(facts["delta_tf_graph"], 0.2)
        lo, hi = facts["tf_soln"] - 4.0 * d, facts["tf_pure"] + 4.0 * d
    else:
        d = max(facts["delta_tb_graph"], 0.2)
        lo, hi = facts["tb_pure"] - 5.0 * d, facts["tb_soln"] + 4.0 * d
    m = (t >= lo) & (t <= hi)

    ax.plot(t[m], pure[m], color="#1F77B4", lw=2.3, label=f"pure {schema.solvent_label}")
    ax.plot(t[m], soln[m], color="#B03A2E", lw=2.3, label="solution")
    if freezing:
        ax.plot(t[m], solid[m], color="#7D3C98", lw=2.3, label="solid (ice)")

    if freezing:
        tf_p, tf_s = facts["tf_pure"], facts["tf_soln"]
        p_at = float(np.interp(tf_p, t, pure))
        top = float(np.interp(hi, t, pure)) * 1.10
        for tx, col in ((tf_p, "#1F77B4"), (tf_s, "#B03A2E")):
            ax.plot([tx, tx], [0, float(np.interp(tx, t, solid))], color=col,
                    linestyle=":", lw=1.2)
        y_arrow = p_at * 0.55
        ax.annotate("", xy=(tf_p, y_arrow), xytext=(tf_s, y_arrow),
                    arrowprops=dict(arrowstyle="<->", color="#1A252F", lw=1.5))
        ax.text((tf_p + tf_s) / 2, y_arrow * 1.06,
                f"ΔTf = {facts['delta_tf_graph']:.2f} K", ha="center", va="bottom",
                fontsize=10, fontweight="bold")
        ax.annotate("solution freezes where its curve meets the SOLID curve",
                    xy=(tf_s, float(np.interp(tf_s, t, solid))),
                    xytext=(0.04, 0.80), textcoords="axes fraction", fontsize=9,
                    color="#7D3C98",
                    arrowprops=dict(arrowstyle="->", color="#7D3C98", lw=1))
        ax.set_xlim(lo, hi)
        ax.set_ylim(0, top)
    else:
        tb_p, tb_s = facts["tb_pure"], facts["tb_soln"]
        ax.axhline(1.0, color="#7F8C8D", linestyle="--", lw=1.2)
        ax.text(lo + 0.4, 1.02, "1 atm", fontsize=9, color="#616A6B", va="bottom")
        for tx, col in ((tb_p, "#1F77B4"), (tb_s, "#B03A2E")):
            ax.plot([tx, tx], [0, 1.0], color=col, linestyle=":", lw=1.2)
        y_lo = float(np.interp(lo, t, soln)) * 0.98
        y_arrow = y_lo + 0.35 * (1.0 - y_lo)
        ax.annotate("", xy=(tb_s, y_arrow), xytext=(tb_p, y_arrow),
                    arrowprops=dict(arrowstyle="<->", color="#1A252F", lw=1.5))
        ax.text((tb_p + tb_s) / 2, y_arrow + 0.012,
                f"ΔTb = {facts['delta_tb_graph']:.2f} K",
                ha="center", va="bottom", fontsize=10, fontweight="bold")
        ax.set_xlim(lo, hi)
        ax.set_ylim(y_lo, float(np.interp(hi, t, pure)) * 1.02)

    ax.set_xlabel("Temperature (K) →", fontsize=11)
    ax.set_ylabel("Vapour pressure (atm)", fontsize=11)
    ax.legend(fontsize=9, loc="upper left")


def _draw_raoult(ax, schema: ColligativeGraphSchema):
    """Total vapour pressure against mole fraction. A POSITIVE deviation bows ABOVE
    the ideal line (weaker A–B attraction ⇒ easier escape ⇒ higher P)."""
    # The two pure vapour pressures must be close enough that the bow can actually turn
    # the total curve over; with p° far apart the extremum lands on the boundary and the
    # "azeotrope" gets marked at x = 1, which is not an azeotrope at all.
    p_a, p_b = 0.85, 1.0           # pure component vapour pressures (arbitrary atm)
    lo, hi = schema.mole_fraction_range
    x = np.linspace(lo, hi, 300)   # x = mole fraction of B (the more volatile one)

    pa = p_a * (1.0 - x)
    pb = p_b * x
    ideal = pa + pb

    dev = schema.deviation if schema.property == "raoult_deviation" else "none"
    bow = 0.50 * x * (1.0 - x)
    if dev == "positive":
        total = ideal + bow
    elif dev == "negative":
        total = ideal - bow
    else:
        total = ideal

    if schema.show_ideal_line:
        ax.plot(x, ideal, color="#7F8C8D", linestyle="--", lw=1.6,
                label="ideal (Raoult)")
    ax.plot(x, pa, color="#1F77B4", lw=1.5, linestyle=":", label="p(solvent)")
    ax.plot(x, pb, color="#B03A2E", lw=1.5, linestyle=":", label="p(solute)")
    ax.plot(x, total, color="#1A252F", lw=2.6,
            label="total" + (f" — {dev} deviation" if dev != "none" else ""))

    if schema.show_azeotrope and dev != "none":
        # Positive deviation → maximum P → MINIMUM-boiling azeotrope, and vice versa.
        i = int(np.argmax(total)) if dev == "positive" else int(np.argmin(total))
        kind = "minimum-boiling" if dev == "positive" else "maximum-boiling"
        ax.plot(x[i], total[i], "o", color="#7D3C98", markersize=8, zorder=6)
        ax.annotate(f"azeotrope\n({kind})", xy=(x[i], total[i]),
                    xytext=(0, 26 if dev == "positive" else -42),
                    textcoords="offset points", ha="center", fontsize=9,
                    color="#7D3C98", fontweight="bold",
                    arrowprops=dict(arrowstyle="->", color="#7D3C98", lw=1))

    if schema.property == "vapour_pressure_lowering":
        xs = schema.mole_fraction
        p_solv = p_a * (1.0 - xs)
        ax.plot([xs, xs], [p_solv, p_a], color="#7D3C98", lw=1.6)
        ax.annotate("", xy=(xs, p_solv), xytext=(xs, p_a),
                    arrowprops=dict(arrowstyle="<->", color="#7D3C98", lw=1.5))
        ax.text(xs + 0.02, (p_solv + p_a) / 2,
                f"Δp = x(solute)·p° = {p_a * xs:.3f}", fontsize=9.5, va="center",
                color="#7D3C98", fontweight="bold")

    ax.set_xlim(lo, hi)
    ax.set_ylim(0, 1.5)
    ax.set_xlabel(f"Mole fraction of {schema.solute_label} →", fontsize=11)
    ax.set_ylabel("Vapour pressure (atm)", fontsize=11)
    ax.legend(fontsize=8.5, loc="upper center", ncol=2)


def _draw_osmotic(ax, schema: ColligativeGraphSchema):
    c = np.linspace(0.0, 0.5, 200)
    t_k = 298.0
    r_l_atm = 0.0821
    pi = c * r_l_atm * t_k                   # van 't Hoff: π = CRT
    ax.plot(c, pi, color="#1F77B4", lw=2.4)
    ax.text(0.05, 0.88, f"π = CRT   (slope = RT = {r_l_atm * t_k:.2f} L atm mol⁻¹)",
            transform=ax.transAxes, fontsize=10, color="#B03A2E", fontweight="bold")
    ax.set_xlabel("Concentration C (mol L⁻¹) →", fontsize=11)
    ax.set_ylabel("Osmotic pressure π (atm)", fontsize=11)
    ax.grid(True, linestyle=":", linewidth=0.5, color="#D5D8DC")


def render_colligative_graph(data: Dict[str, Any],
                             canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = ColligativeGraphSchema(**data)
    facts = _colligative_facts(schema)

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))

    if schema.property == "boiling_point_elevation":
        _draw_vp_temperature(ax, schema, facts, freezing=False)
        eq = f"ΔTb = Kb·m = {schema.kb:g} × {schema.molality:g} = {facts['delta_tb_law']:.2f} K"
    elif schema.property == "freezing_point_depression":
        _draw_vp_temperature(ax, schema, facts, freezing=True)
        eq = f"ΔTf = Kf·m = {schema.kf:g} × {schema.molality:g} = {facts['delta_tf_law']:.2f} K"
    elif schema.property == "osmotic_pressure":
        _draw_osmotic(ax, schema)
        eq = "π = CRT = (n/V)RT   (i·CRT for an electrolyte)"
    else:
        _draw_raoult(ax, schema)
        eq = "p(total) = p°(A)·x(A) + p°(B)·x(B)"

    if schema.show_equations:
        ax.text(0.5, -0.17, eq, transform=ax.transAxes, ha="center", va="top",
                fontsize=10, color="#1A252F", fontweight="bold")

    default = schema.property.replace("_", " ").title()
    ax.set_title(schema.title or default, fontsize=13, fontweight="bold")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return _fig_to_svg(fig)


# ── Organic Reaction Mechanism ────────────────────────────────────────────────

# arrows: (from_idx, to_idx, caption, kind). idx 0=substrate 1=intermediate 2=product.
# kind "full" = a pair of electrons; "half" = a single electron (a fishhook), which is
# what a radical mechanism moves and the only thing that may be drawn with a half head.
_MECHANISM_INFO: Dict[str, Dict[str, Any]] = {
    "e1": {
        "name": "E1 — Unimolecular Elimination",
        "substrate": "(CH₃)₃C–Br", "reagent": "H₂O / Δ (weak base)",
        "intermediate": "(CH₃)₃C⁺", "intermediate_kind": "carbocation (3°)",
        "product": "(CH₃)₂C=CH₂",
        "arrows": [(0, 1, "C–Br bond breaks: e⁻ pair leaves with Br⁻", "full"),
                   (1, 2, "β C–H bond e⁻ form the π bond", "full")],
        "rule": "Saytzeff: the MORE substituted alkene predominates. "
                "Rate = k[substrate] — first order, the base is not in the rate law.",
        "byproduct": "+ Br⁻",
    },
    "e2": {
        "name": "E2 — Bimolecular Elimination",
        "substrate": "CH₃CH₂CH₂–Br", "reagent": "conc. alc. KOH",
        "intermediate": "[anti-periplanar TS]‡", "intermediate_kind": "transition state",
        "product": "CH₃CH=CH₂",
        "arrows": [(0, 1, "base attacks the β-H", "full"),
                   (1, 2, "C–Br breaks as the π bond forms", "full")],
        "rule": "Concerted, ONE step: no intermediate, only a transition state. "
                "H and the leaving group must be ANTI-PERIPLANAR. Rate = k[substrate][base].",
        "byproduct": "+ KBr + H₂O",
    },
    "electrophilic_aromatic_substitution": {
        "name": "Electrophilic Aromatic Substitution",
        "substrate": "C₆H₆", "reagent": "E⁺  (e.g. NO₂⁺)",
        "intermediate": "arenium ion", "intermediate_kind": "σ-complex (Wheland)",
        "product": "C₆H₅–E",
        "arrows": [(0, 1, "π e⁻ of the ring attack E⁺", "full"),
                   (1, 2, "C–H e⁻ restore aromaticity", "full")],
        "rule": "The arenium ion is NOT aromatic — losing H⁺ (not adding a nucleophile) "
                "is what restores the aromatic sextet. Substitution, never addition.",
        "byproduct": "+ H⁺",
    },
    "markovnikov_addition": {
        "name": "Markovnikov Addition",
        "substrate": "CH₃–CH=CH₂", "reagent": "HBr",
        "intermediate": "CH₃–C⁺H–CH₃", "intermediate_kind": "carbocation (2°, more stable)",
        "product": "CH₃–CHBr–CH₃",
        "arrows": [(0, 1, "π e⁻ attack the H of HBr", "full"),
                   (1, 2, "Br⁻ lone pair attacks C⁺", "full")],
        "rule": "H adds to the carbon with MORE hydrogens, because that route goes "
                "through the more stable carbocation. Product: 2-bromopropane.",
        "byproduct": "",
    },
    "anti_markovnikov": {
        "name": "Anti-Markovnikov (Kharasch / peroxide effect)",
        "substrate": "CH₃–CH=CH₂", "reagent": "HBr / R–O–O–R, hν",
        "intermediate": "CH₃–ĊH–CH₂Br", "intermediate_kind": "free radical (2°)",
        "product": "CH₃–CH₂–CH₂Br",
        "arrows": [(0, 1, "Br• adds to the terminal C (1 e⁻ each)", "half"),
                   (1, 2, "the radical abstracts H from HBr", "half")],
        "rule": "Peroxide switches the mechanism to RADICALS, so Br adds to the carbon "
                "with MORE hydrogens — the reverse of Markovnikov. Only ever with HBr.",
        "byproduct": "",
    },
    "aldol": {
        "name": "Aldol Condensation",
        "substrate": "2 CH₃CHO", "reagent": "dil. NaOH",
        "intermediate": "⁻CH₂CHO", "intermediate_kind": "enolate (carbanion)",
        "product": "CH₃CH(OH)CH₂CHO",
        "arrows": [(0, 1, "base removes the acidic α-H", "full"),
                   (1, 2, "carbanion attacks the C=O carbon", "full")],
        "rule": "Needs an α-hydrogen. On heating the aldol loses water to give the "
                "α,β-unsaturated carbonyl (CH₃CH=CH–CHO).",
        "byproduct": "+ H₂O",
    },
    "cannizzaro": {
        "name": "Cannizzaro Reaction (disproportionation)",
        "substrate": "2 HCHO", "reagent": "conc. NaOH",
        "intermediate": "tetrahedral alkoxide", "intermediate_kind": "alkoxide intermediate",
        "product": "CH₃OH + HCOO⁻Na⁺",
        "arrows": [(0, 1, "OH⁻ adds to the carbonyl carbon", "full"),
                   (1, 2, "hydride (H⁻) transfers to the 2nd molecule", "full")],
        "rule": "Only for aldehydes with NO α-hydrogen. One molecule is oxidised to the "
                "acid salt, the other reduced to the alcohol — a disproportionation.",
        "byproduct": "",
    },
    "esterification": {
        "name": "Fischer Esterification",
        "substrate": "CH₃COOH + C₂H₅OH", "reagent": "conc. H₂SO₄",
        "intermediate": "tetrahedral intermediate",
        "intermediate_kind": "protonated tetrahedral adduct",
        "product": "CH₃COOC₂H₅",
        "arrows": [(0, 1, "alcohol O lone pair attacks the C=O carbon", "full"),
                   (1, 2, "loss of H₂O regenerates the C=O", "full")],
        "rule": "Reversible — nucleophilic acyl substitution. Drive it right by removing "
                "water or using excess alcohol (Le Chatelier).",
        "byproduct": "+ H₂O",
    },
    "free_radical_substitution": {
        "name": "Free Radical Substitution (chlorination)",
        "substrate": "CH₄", "reagent": "Cl₂ / hν (UV light)",
        "intermediate": "•CH₃", "intermediate_kind": "methyl free radical",
        "product": "CH₃Cl",
        "arrows": [(0, 1, "Cl• abstracts H — homolysis, 1 e⁻ each", "half"),
                   (1, 2, "•CH₃ attacks Cl₂", "half")],
        "rule": "Three phases: initiation (Cl₂ → 2Cl• by homolysis), propagation "
                "(the two steps shown), termination (two radicals combine).",
        "byproduct": "+ HCl",
    },
}


def _curved_arrow(ax, p_from, p_to, rad: float, color: str, half: bool = False):
    """Electron flow. The tail sits on the bond or lone pair the electrons come FROM and
    the head where they GO — that direction is the mark scheme. A half head (fishhook)
    moves ONE electron and belongs only to radical mechanisms."""
    ax.annotate("", xy=p_to, xytext=p_from,
                arrowprops=dict(arrowstyle="->" if half else "-|>",
                                connectionstyle=f"arc3,rad={rad}",
                                color=color, lw=1.6, shrinkA=2, shrinkB=2,
                                mutation_scale=15))


def render_organic_mechanism(data: Dict[str, Any],
                             canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = OrganicMechanismSchema(**data)
    info = _MECHANISM_INFO[schema.mechanism]

    substrate = schema.substrate or info["substrate"]
    reagent = schema.reagent or info["reagent"]
    intermediate = schema.intermediate or info["intermediate"]
    product = schema.product or info["product"]

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.axis("off")

    show_mid = schema.show_intermediate
    y = 3.5
    xs = [1.55, 5.0, 8.45] if show_mid else [2.2, 5.0, 7.8]

    ax.text(xs[0], y, substrate, ha="center", va="center", fontsize=11.5,
            fontweight="bold", color="#1A5276", zorder=5,
            bbox=dict(boxstyle="round,pad=0.42", facecolor="white",
                      edgecolor="#1A5276", linewidth=1.5))
    ax.text(xs[2], y, product, ha="center", va="center", fontsize=11.5,
            fontweight="bold", color="#1E8449", zorder=5,
            bbox=dict(boxstyle="round,pad=0.42", facecolor="white",
                      edgecolor="#1E8449", linewidth=1.5))

    if show_mid:
        # The intermediate is what the question asks for, so it is drawn, named and
        # visually distinct rather than implied by an arrow.
        ax.text(xs[1], y, intermediate, ha="center", va="center", fontsize=11.5,
                fontweight="bold", color="#B03A2E", zorder=5,
                bbox=dict(boxstyle="round,pad=0.42", facecolor="#FDEBD0",
                          edgecolor="#B03A2E", linewidth=1.8))
        ax.text(xs[1], y - 0.62, info["intermediate_kind"], ha="center", va="top",
                fontsize=9, color="#B03A2E", style="italic")

    for i in (0, 1):
        a0, a1 = xs[i] + 0.95, xs[i + 1] - 0.95
        if a1 <= a0:
            continue
        ax.annotate("", xy=(a1, y), xytext=(a0, y),
                    arrowprops=dict(arrowstyle="-|>", color="black", lw=1.5,
                                    shrinkA=0, shrinkB=0, mutation_scale=13))
        ax.text((a0 + a1) / 2, y + 0.16, f"Step {i + 1}", ha="center", va="bottom",
                fontsize=8.5, color=C_ANNOT)
    ax.text(xs[0] + (xs[1] - xs[0]) / 2, y - 0.30, reagent, ha="center", va="top",
            fontsize=9.5, color="#1A252F")

    if schema.show_curved_arrows:
        half = any(kind == "half" for *_rest, kind in info["arrows"])
        for k, (src, dst, caption, kind) in enumerate(info["arrows"]):
            if not show_mid and dst == 1:
                continue
            x_from, x_to = xs[min(src, 2)], xs[min(dst, 2)]
            colour = "#2980B9" if k == 0 else "#7D3C98"
            _curved_arrow(ax, (x_from + 0.55, y + 0.30), (x_to - 0.55, y + 0.30),
                          -0.45, colour, half=(kind == "half"))
            ax.text((x_from + x_to) / 2, y + 1.30 + 0.42 * k, caption, ha="center",
                    va="bottom", fontsize=8.5, color=colour)
        legend = ("↷ fishhook = ONE electron (radical)" if half
                  else "↷ curved arrow = a PAIR of electrons")
        ax.text(0.02, 0.03, legend, transform=ax.transAxes, fontsize=8.5,
                color=C_ANNOT, va="bottom")

    if info["byproduct"]:
        ax.text(xs[2], y - 0.70, info["byproduct"], ha="center", va="top", fontsize=9.5,
                color="#1E8449")

    if schema.show_rule:
        ax.text(5.0, 0.85, info["rule"], ha="center", va="center", fontsize=9.5,
                color="#1A252F", wrap=True,
                bbox=dict(boxstyle="round,pad=0.45", facecolor="#F4F6F7",
                          edgecolor="#AEB6BF", linewidth=1))

    ax.set_title(schema.title or info["name"], fontsize=13, fontweight="bold")
    fig.tight_layout()
    return _fig_to_svg(fig)


# ── Hybridisation / Orbital Overlap ───────────────────────────────────────────

# p_used = how many of the three p orbitals the hybrid consumes, so the number of
# UNHYBRIDISED p orbitals left to form π bonds is 3 − p_used. That count is what decides
# whether a π bond is even possible, and it is derived, never taken from the params.
_HYB_INFO: Dict[str, Dict[str, Any]] = {
    "sp":    {"name": "sp", "n": 2, "p_used": 1, "angle": 180.0, "geometry": "Linear",
              "example": "C₂H₂ (ethyne)", "angle_text": "180°"},
    "sp2":   {"name": "sp²", "n": 3, "p_used": 2, "angle": 120.0,
              "geometry": "Trigonal planar", "example": "C₂H₄ (ethene)",
              "angle_text": "120°"},
    "sp3":   {"name": "sp³", "n": 4, "p_used": 3, "angle": 109.5,
              "geometry": "Tetrahedral", "example": "CH₄ (methane)",
              "angle_text": "109.5°"},
    "sp3d":  {"name": "sp³d", "n": 5, "p_used": 3, "angle": 90.0,
              "geometry": "Trigonal bipyramidal", "example": "PCl₅",
              "angle_text": "90° (ax–eq), 120° (eq–eq)"},
    "sp3d2": {"name": "sp³d²", "n": 6, "p_used": 3, "angle": 90.0,
              "geometry": "Octahedral", "example": "SF₆", "angle_text": "90°"},
}

# In-plane directions used to draw the lobes. sp3/sp3d/sp3d2 are 3-D, so they are shown
# in the conventional flattened projection rather than pretending to be planar.
_HYB_LOBE_ANGLES = {
    "sp": [0.0, 180.0],
    "sp2": [90.0, 210.0, 330.0],
    "sp3": [90.0, 200.0, 340.0, 270.0],
    "sp3d": [90.0, 270.0, 0.0, 150.0, 210.0],
    "sp3d2": [0.0, 60.0, 120.0, 180.0, 240.0, 300.0],
}


def _unhybridised_p(hybridisation: str) -> int:
    return 3 - _HYB_INFO[hybridisation]["p_used"]


def _bond_angle(hybridisation: str) -> float:
    return _HYB_INFO[hybridisation]["angle"]


def _lobe(ax, cx, cy, angle_deg, length=1.0, width=0.42, color="#5DADE2", alpha=0.85,
          zorder=3):
    ax.add_patch(mpatches.Ellipse((cx + 0.5 * length * math.cos(math.radians(angle_deg)),
                                   cy + 0.5 * length * math.sin(math.radians(angle_deg))),
                                  length, width, angle=angle_deg, facecolor=color,
                                  edgecolor="#1A5276", linewidth=1.0, alpha=alpha,
                                  zorder=zorder))


def render_hybridisation_overlap(data: Dict[str, Any],
                                 canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = HybridisationOverlapSchema(**data)
    info = _HYB_INFO[schema.hybridisation]
    n_p = _unhybridised_p(schema.hybridisation)

    # A π bond is the sideways overlap of UNHYBRIDISED p orbitals. With none left (sp³,
    # and both expanded-octet sets) there is nothing to overlap sideways, so a π bond is
    # impossible however the params are set.
    wants_pi = schema.bond_type in ("pi", "both")
    pi_possible = n_p > 0
    show_pi = wants_pi and pi_possible
    show_sigma = schema.bond_type in ("sigma", "both") or not show_pi

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))
    ax.set_xlim(-4.6, 4.6)
    ax.set_ylim(-3.2, 3.4)
    ax.set_aspect("equal")
    ax.axis("off")

    two_atom = show_pi or schema.bond_type in ("sigma", "both")
    xa, xb = (-1.45, 1.45) if two_atom else (0.0, 0.0)

    if schema.show_orbital_lobes:
        for ang in _HYB_LOBE_ANGLES[schema.hybridisation]:
            _lobe(ax, xa, 0.0, ang, length=1.35, width=0.52)
            if two_atom:
                _lobe(ax, xb, 0.0, ang, length=1.35, width=0.52)

    for x in ((xa, xb) if two_atom else (xa,)):
        ax.plot(x, 0.0, "o", color="#F39C12", markersize=13, markeredgecolor="black",
                zorder=6)

    if show_sigma and two_atom:
        # σ: head-on, along the internuclear axis, with the overlap ON the axis.
        ax.add_patch(mpatches.Ellipse(((xa + xb) / 2, 0.0), abs(xb - xa) * 0.55, 0.60,
                                      facecolor="#F9E79F", edgecolor="#B7950B",
                                      linewidth=1.3, alpha=0.95, zorder=5))
        ax.text((xa + xb) / 2, 0.0, "σ", ha="center", va="center", fontsize=15,
                fontweight="bold", color="#7D6608", zorder=7)
        ax.annotate("σ bond: HEAD-ON overlap along the internuclear axis",
                    xy=((xa + xb) / 2, -0.36), xytext=(0, -1.95),
                    textcoords="offset points" if False else "data",
                    ha="center", va="top", fontsize=9.5, color="#7D6608",
                    arrowprops=dict(arrowstyle="->", color="#7D6608", lw=1))

    if schema.show_unhybridised_p and n_p:
        for x in ((xa, xb) if two_atom else (xa,)):
            for sign in (1, -1):
                _lobe(ax, x, 0.0, 90.0 if sign > 0 else 270.0, length=1.5, width=0.50,
                      color="#D7BDE2", alpha=0.9, zorder=2)

    if show_pi and two_atom:
        # π: sideways overlap ABOVE and BELOW the axis — never through it.
        for sign in (1, -1):
            ax.add_patch(mpatches.Ellipse(((xa + xb) / 2, sign * 0.80),
                                          abs(xb - xa) * 0.95, 0.62,
                                          facecolor="#D2B4DE", edgecolor="#6C3483",
                                          linewidth=1.3, alpha=0.75, zorder=4))
            ax.text((xa + xb) / 2, sign * 0.80, "π", ha="center", va="center",
                    fontsize=14, fontweight="bold", color="#4A235A", zorder=7)
        ax.text(0.0, 2.30, "π bond: SIDEWAYS overlap of the unhybridised p orbitals",
                ha="center", va="bottom", fontsize=9.5, color="#4A235A")

    if wants_pi and not pi_possible:
        ax.text(0.0, 2.30,
                f"{info['name']} uses all three p orbitals — no unhybridised p is left, "
                f"so it cannot form a π bond",
                ha="center", va="bottom", fontsize=9.5, color="#B03A2E",
                fontweight="bold")

    facts = [f"Hybridisation: {info['name']}   ({info['n']} hybrid orbitals)",
             f"Geometry: {info['geometry']}",
             f"Unhybridised p orbitals: {n_p}"]
    if schema.show_bond_angle:
        facts.insert(2, f"Bond angle: {info['angle_text']}")
    example = schema.molecule_example or info["example"]
    facts.append(f"Example: {example}")
    for i, line in enumerate(facts):
        ax.text(0.01, 0.98 - 0.058 * i, line, transform=ax.transAxes, fontsize=9.5,
                va="top", color="#1A252F", fontweight="bold" if i == 0 else "normal")

    if schema.show_bond_angle and schema.hybridisation in ("sp", "sp2", "sp3"):
        ax.text(xa, -2.55, f"{info['angle_text']} between the hybrid orbitals",
                ha="center", va="center", fontsize=9.5, color="#1A5276",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="#EAF2F8",
                          edgecolor="#1A5276", linewidth=1))

    ax.set_title(schema.title or f"{info['name']} hybridisation — {example}",
                 fontsize=13, fontweight="bold")
    fig.tight_layout()
    return _fig_to_svg(fig)


# ── Adsorption Isotherm ───────────────────────────────────────────────────────

def _freundlich(p: np.ndarray, k: float, n: float) -> np.ndarray:
    """x/m = k·p^(1/n), n > 1. Has NO saturation — it rises without limit."""
    return k * np.power(np.maximum(p, 0.0), 1.0 / n)


def _langmuir(p: np.ndarray, x_m: float, k: float) -> np.ndarray:
    """x/m = x_m·k·p/(1 + k·p) → plateaus at x_m: a complete MONOLAYER."""
    return x_m * k * p / (1.0 + k * p)


def _bet(p: np.ndarray, p0: float, x_m: float, c: float) -> np.ndarray:
    """Multilayer: rises without limit as p → p0 (Type II sigmoid)."""
    x = np.clip(p / p0, 0.0, 0.97)
    return x_m * c * x / ((1.0 - x) * (1.0 - x + c * x))


def render_adsorption_isotherm(data: Dict[str, Any],
                               canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = AdsorptionIsothermSchema(**data)
    lo, hi = schema.pressure_range
    p = np.linspace(max(lo, 1e-3), hi, 300)

    panels = 1 + int(schema.show_linearised_form) + int(schema.show_physisorption_chemisorption)
    fig, axes = plt.subplots(1, panels, figsize=(canvas_w / 100, canvas_h / 100))
    axes = [axes] if panels == 1 else list(axes)
    ax = axes[0]

    if schema.isotherm == "freundlich":
        y = _freundlich(p, schema.k, schema.n)
        ax.plot(p, y, color="#1F77B4", lw=2.4)
        if schema.show_saturation:
            ax.text(0.04, 0.92, "No saturation: x/m keeps rising with p",
                    transform=ax.transAxes, fontsize=9.5, color="#B03A2E",
                    fontweight="bold", va="top")
        ax.text(0.04, 0.05, f"x/m = k·p^(1/n)   (k = {schema.k:g}, n = {schema.n:g})",
                transform=ax.transAxes, fontsize=10, va="bottom")
    elif schema.isotherm == "langmuir":
        y = _langmuir(p, schema.monolayer_capacity, schema.k)
        ax.plot(p, y, color="#1F77B4", lw=2.4)
        if schema.show_saturation:
            ax.axhline(schema.monolayer_capacity, color="#B03A2E", linestyle="--", lw=1.3)
            ax.text(hi, schema.monolayer_capacity * 1.02,
                    f"saturation: monolayer complete (x/m → {schema.monolayer_capacity:g})",
                    ha="right", va="bottom", fontsize=9.5, color="#B03A2E",
                    fontweight="bold")
        ax.set_ylim(0, schema.monolayer_capacity * 1.30)
        ax.text(0.04, 0.05, "x/m = x·k·p / (1 + k·p)", transform=ax.transAxes,
                fontsize=10, va="bottom")
    else:
        y = _bet(p, hi, schema.monolayer_capacity, schema.bet_c)
        ax.plot(p, y, color="#1F77B4", lw=2.4)
        if schema.show_saturation:
            ax.axhline(schema.monolayer_capacity, color="#7F8C8D", linestyle=":", lw=1.2)
            ax.text(lo + 0.03 * (hi - lo), schema.monolayer_capacity * 1.05,
                    "monolayer (knee)", fontsize=9, color="#566573")
            ax.text(0.04, 0.92, "MULTILAYER: no plateau — x/m diverges as p → p₀",
                    transform=ax.transAxes, fontsize=9.5, color="#B03A2E",
                    fontweight="bold", va="top")
        ax.set_ylim(0, schema.monolayer_capacity * 4.0)
        ax.text(0.04, 0.05, "BET (Type II)", transform=ax.transAxes, fontsize=10,
                va="bottom")

    ax.set_xlabel("Pressure p (atm) →", fontsize=10.5)
    ax.set_ylabel("x/m  (mass adsorbed per gram)", fontsize=10.5)
    ax.set_title(schema.isotherm.capitalize() + " isotherm", fontsize=11,
                 fontweight="bold")
    ax.grid(True, linestyle=":", linewidth=0.5, color="#D5D8DC")

    idx = 1
    if schema.show_linearised_form:
        lax = axes[idx]
        idx += 1
        if schema.isotherm == "freundlich":
            # log(x/m) = log k + (1/n)·log p — a straight line of slope 1/n.
            lx, ly = np.log10(p), np.log10(_freundlich(p, schema.k, schema.n))
            lax.plot(lx, ly, color="#1E8449", lw=2.2)
            slope = float(np.polyfit(lx, ly, 1)[0])
            lax.set_xlabel("log p", fontsize=10.5)
            lax.set_ylabel("log (x/m)", fontsize=10.5)
            lax.text(0.05, 0.90, f"slope = 1/n = {slope:.3f}\nintercept = log k",
                     transform=lax.transAxes, fontsize=9.5, va="top", color="#1E8449",
                     fontweight="bold")
        elif schema.isotherm == "langmuir":
            ly = p / _langmuir(p, schema.monolayer_capacity, schema.k)
            lax.plot(p, ly, color="#1E8449", lw=2.2)
            lax.set_xlabel("p", fontsize=10.5)
            lax.set_ylabel("p / (x/m)", fontsize=10.5)
            lax.text(0.05, 0.90, "p/(x/m) = 1/(x·k) + p/x\nstraight line", fontsize=9.5,
                     transform=lax.transAxes, va="top", color="#1E8449", fontweight="bold")
        else:
            x = np.clip(p / hi, 1e-3, 0.35)
            v = _bet(x * hi, hi, schema.monolayer_capacity, schema.bet_c)
            lax.plot(x, x / (v * (1.0 - x)), color="#1E8449", lw=2.2)
            lax.set_xlabel("p/p₀", fontsize=10.5)
            lax.set_ylabel("(p/p₀) / [v(1 − p/p₀)]", fontsize=10.5)
            lax.text(0.05, 0.90, "BET linear form\n(valid for p/p₀ ≈ 0.05–0.35)",
                     fontsize=9.5, transform=lax.transAxes, va="top", color="#1E8449",
                     fontweight="bold")
        lax.set_title("Linearised form", fontsize=11, fontweight="bold")
        lax.grid(True, linestyle=":", linewidth=0.5, color="#D5D8DC")

    if schema.show_physisorption_chemisorption:
        tax = axes[idx]
        t = np.linspace(100.0, 600.0, 300)
        # Physisorption falls away monotonically with temperature (van der Waals forces
        # are easily overcome). Chemisorption first RISES — it needs activation energy —
        # then falls, giving the characteristic maximum.
        phys = 5.0 * np.exp(-(t - 100.0) / 130.0)
        chem = 4.6 * np.exp(-((t - 330.0) / 95.0) ** 2)
        tax.plot(t, phys, color="#2980B9", lw=2.2, label="physisorption")
        tax.plot(t, chem, color="#B03A2E", lw=2.2, label="chemisorption")
        tax.set_xlabel("Temperature (K) →", fontsize=10.5)
        tax.set_ylabel("Extent of adsorption", fontsize=10.5)
        tax.set_title("Temperature dependence", fontsize=11, fontweight="bold")
        tax.legend(fontsize=9)
        tax.text(0.5, -0.20, "physisorption decreases with T; chemisorption "
                             "rises then falls (needs Ea)",
                 transform=tax.transAxes, ha="center", va="top", fontsize=9,
                 color=C_ANNOT)
        tax.grid(True, linestyle=":", linewidth=0.5, color="#D5D8DC")

    if schema.title:
        fig.suptitle(schema.title, fontsize=13, fontweight="bold")
    fig.tight_layout()
    return _fig_to_svg(fig)


# ══════════════════════════════════════════════════════════════════════════════
# THIRD WAVE renderers
# ══════════════════════════════════════════════════════════════════════════════

# Fold sub/superscript digits to ASCII so "aqueous CuSO₄" and "aqueous CuSO4" hit
# the same database key.
_SUBSUP_TO_ASCII = str.maketrans("₀₁₂₃₄₅₆₇₈₉⁰¹²³⁴⁵⁶⁷⁸⁹",
                                 "01234567890123456789")


def _norm_key(s: str) -> str:
    return s.strip().lower().translate(_SUBSUP_TO_ASCII)


# ── 1. Electrolytic Cell (electrolysis) ───────────────────────────────────────

# Products are the electrolysis FACTS (over-potential included where it matters:
# brine gives H₂ + Cl₂, not Na; aqueous CuSO₄ with inert electrodes gives Cu + O₂).
_ELECTROLYSIS_DB: Dict[str, Dict[str, str]] = {
    "molten nacl": {
        "cation": "Na⁺", "anion": "Cl⁻",
        "cathode_product": "Na (l)", "anode_product": "Cl₂ (g)",
        "cathode_half": "Na⁺ + e⁻ → Na",
        "anode_half": "2Cl⁻ → Cl₂ + 2e⁻",
    },
    "aqueous nacl": {
        "cation": "Na⁺ / H⁺", "anion": "Cl⁻ / OH⁻",
        "cathode_product": "H₂ (g)", "anode_product": "Cl₂ (g)",
        "cathode_half": "2H₂O + 2e⁻ → H₂ + 2OH⁻",
        "anode_half": "2Cl⁻ → Cl₂ + 2e⁻",
    },
    "molten al2o3": {
        "cation": "Al³⁺", "anion": "O²⁻",
        "cathode_product": "Al (l)", "anode_product": "O₂ / CO₂ (g)",
        "cathode_half": "Al³⁺ + 3e⁻ → Al",
        "anode_half": "2O²⁻ → O₂ + 4e⁻",
    },
    "aqueous cuso4": {
        "cation": "Cu²⁺ / H⁺", "anion": "SO₄²⁻ / OH⁻",
        "cathode_product": "Cu (s)", "anode_product": "O₂ (g)",
        "cathode_half": "Cu²⁺ + 2e⁻ → Cu",
        "anode_half": "2H₂O → O₂ + 4H⁺ + 4e⁻",
    },
    "acidified water": {
        "cation": "H⁺", "anion": "OH⁻",
        "cathode_product": "H₂ (g)", "anode_product": "O₂ (g)",
        "cathode_half": "2H⁺ + 2e⁻ → H₂",
        "anode_half": "2H₂O → O₂ + 4H⁺ + 4e⁻",
    },
    "water": {
        "cation": "H⁺", "anion": "OH⁻",
        "cathode_product": "H₂ (g)", "anode_product": "O₂ (g)",
        "cathode_half": "2H⁺ + 2e⁻ → H₂",
        "anode_half": "2H₂O → O₂ + 4H⁺ + 4e⁻",
    },
}


def _electrolysis_facts(schema: ElectrolyticCellSchema) -> Dict[str, str]:
    """Merge the known electrolyte chemistry with any explicit overrides."""
    base = _ELECTROLYSIS_DB.get(_norm_key(schema.electrolyte), {
        "cation": "cation⁺", "anion": "anion⁻",
        "cathode_product": "reduced species", "anode_product": "oxidised species",
        "cathode_half": "cation + n e⁻ → product",
        "anode_half": "anion → product + n e⁻",
    })
    return {
        "cation": schema.cation or base["cation"],
        "anion": schema.anion or base["anion"],
        "cathode_product": schema.cathode_product or base["cathode_product"],
        "anode_product": schema.anode_product or base["anode_product"],
        "cathode_half": schema.cathode_half_reaction or base["cathode_half"],
        "anode_half": schema.anode_half_reaction or base["anode_half"],
    }


def render_electrolytic_cell(data: Dict[str, Any],
                             canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = ElectrolyticCellSchema(**data)
    f = _electrolysis_facts(schema)

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 7)
    ax.set_aspect("equal")
    ax.axis("off")

    # electrolyte cell
    liq_x0, liq_w, liq_y0, liq_h = 1.6, 6.8, 0.7, 3.1
    ax.add_patch(mpatches.FancyBboxPatch(
        (liq_x0, liq_y0), liq_w, liq_h, boxstyle="square,pad=0",
        edgecolor="black", facecolor="#d0e8ff", linewidth=1.8, zorder=1))
    ax.text(5.0, liq_y0 + 0.2, schema.electrolyte, ha="center", va="bottom",
            fontsize=10, color="#003399", style="italic")

    liq_top = liq_y0 + liq_h
    rod_top = 5.35
    # LEFT electrode = cathode (−, driven negative by the battery);
    # RIGHT electrode = anode (+). This sign is the INVERSE of a galvanic cell.
    cx, ax_x = 3.2, 6.8
    for ex, is_cathode in ((cx, True), (ax_x, False)):
        ax.plot([ex, ex], [liq_y0 + 0.25, rod_top], color="#555555", linewidth=6,
                solid_capstyle="round", zorder=3)
    ax.text(cx, rod_top + 0.05, f"{schema.electrodes}", ha="center", va="bottom",
            fontsize=7.5, color="#555")

    ax.text(cx, liq_top + 0.02, "Cathode (−)", ha="center", va="bottom",
            fontsize=11, fontweight="bold", color="#C0392B")
    ax.text(ax_x, liq_top + 0.02, "Anode (+)", ha="center", va="bottom",
            fontsize=11, fontweight="bold", color="#1A5276")

    # ── battery / external EMF driving the cell ──────────────────────────────
    if schema.show_battery:
        wire_y = 6.4
        ax.plot([cx, cx], [rod_top, wire_y], color="black", lw=2, zorder=3)
        ax.plot([ax_x, ax_x], [rod_top, wire_y], color="black", lw=2, zorder=3)
        ax.plot([cx, 4.35], [wire_y, wire_y], color="black", lw=2, zorder=3)
        ax.plot([5.65, ax_x], [wire_y, wire_y], color="black", lw=2, zorder=3)
        # cell symbol: long plate = +, short plate = −. The − plate wires to the
        # cathode, the + plate to the anode.
        ax.plot([4.75, 4.75], [wire_y - 0.28, wire_y + 0.28], color="black", lw=1.6)  # short −
        ax.plot([5.25, 5.25], [wire_y - 0.5, wire_y + 0.5], color="black", lw=2.6)    # long +
        ax.plot([4.35, 4.75], [wire_y, wire_y], color="black", lw=2)
        ax.plot([5.25, 5.65], [wire_y, wire_y], color="black", lw=2)
        ax.text(4.55, wire_y + 0.35, "−", ha="center", fontsize=14, fontweight="bold")
        ax.text(5.45, wire_y + 0.35, "+", ha="center", fontsize=14, fontweight="bold")
        ax.text(5.0, wire_y - 0.75, "external EMF (battery)", ha="center",
                va="top", fontsize=9, color="#555")

    # ── ion migration: cations → cathode (−), anions → anode (+) ─────────────
    if schema.show_ion_migration:
        mig_y = liq_top - 0.55
        ax.annotate("", xy=(cx + 0.55, mig_y), xytext=(4.7, mig_y),
                    arrowprops=dict(arrowstyle="-|>", color="#C0392B", lw=2))
        ax.text(4.85, mig_y, f"{f['cation']}", ha="left", va="center",
                fontsize=10, color="#C0392B", fontweight="bold")
        ax.annotate("", xy=(ax_x - 0.55, mig_y - 0.6), xytext=(5.3, mig_y - 0.6),
                    arrowprops=dict(arrowstyle="-|>", color="#1A5276", lw=2))
        ax.text(5.15, mig_y - 0.6, f"{f['anion']}", ha="right", va="center",
                fontsize=10, color="#1A5276", fontweight="bold")
        ax.text(5.0, mig_y - 1.15, "cations → cathode,  anions → anode",
                ha="center", va="center", fontsize=8.5, color="#555", style="italic")

    # products
    ax.text(cx, liq_y0 + liq_h * 0.5, f"→ {f['cathode_product']}", ha="center",
            va="center", fontsize=9.5, color="#7B241C", fontweight="bold")
    ax.text(ax_x, liq_y0 + liq_h * 0.5, f"→ {f['anode_product']}", ha="center",
            va="center", fontsize=9.5, color="#154360", fontweight="bold")

    if schema.show_half_reactions:
        ax.text(2.6, 0.42, f"Cathode (reduction): {f['cathode_half']}",
                ha="center", va="top", fontsize=9, color="#C0392B")
        ax.text(7.4, 0.42, f"Anode (oxidation): {f['anode_half']}",
                ha="center", va="top", fontsize=9, color="#1A5276")

    ax.set_title(schema.title or "Electrolytic Cell (Electrolysis)",
                 fontsize=13, fontweight="bold")
    fig.tight_layout()
    return _fig_to_svg(fig)


# ── 2. Ionic Lattice ──────────────────────────────────────────────────────────

# Radius-ratio rule (r₊/r₋): each threshold is the minimum ratio at which the
# cation can keep that many anions in contact around it. COMPUTED, never guessed.
_RADIUS_RATIO_RULE = [
    (0.732, 8, "cubic (8-coordinate, CsCl-type)", "cscl"),
    (0.414, 6, "octahedral (6-coordinate, NaCl-type)", "nacl"),
    (0.225, 4, "tetrahedral (4-coordinate, ZnS-type)", "zns_blende"),
    (0.155, 3, "trigonal planar (3-coordinate)", None),
    (0.0,   2, "linear (2-coordinate)", None),
]


def _radius_ratio_geometry(ratio: float) -> Dict[str, Any]:
    for lo, cn, geom, hint in _RADIUS_RATIO_RULE:
        if ratio >= lo:
            return {"cn": cn, "geometry": geom, "lattice_hint": hint, "min_ratio": lo}
    return {"cn": 2, "geometry": "linear (2-coordinate)", "lattice_hint": None,
            "min_ratio": 0.0}


_IONIC_LATTICE_INFO: Dict[str, Dict[str, Any]] = {
    "nacl": {"name": "Rock Salt (NaCl)", "cation_cn": 6, "anion_cn": 6, "ratio": "6 : 6"},
    "cscl": {"name": "Caesium Chloride (CsCl)", "cation_cn": 8, "anion_cn": 8, "ratio": "8 : 8"},
    "zns_blende": {"name": "Zinc Blende (ZnS)", "cation_cn": 4, "anion_cn": 4, "ratio": "4 : 4"},
    "zns_wurtzite": {"name": "Wurtzite (ZnS)", "cation_cn": 4, "anion_cn": 4, "ratio": "4 : 4"},
    "fluorite": {"name": "Fluorite (CaF₂)", "cation_cn": 8, "anion_cn": 4, "ratio": "8 : 4"},
    "antifluorite": {"name": "Antifluorite (Na₂O)", "cation_cn": 4, "anion_cn": 8, "ratio": "4 : 8"},
}

_CUBE_CORNERS = [(x, y, z) for x in (0.0, 1.0) for y in (0.0, 1.0) for z in (0.0, 1.0)]
_CUBE_FACES = [(0.5, 0.5, 0.0), (0.5, 0.5, 1.0), (0.5, 0.0, 0.5),
               (0.5, 1.0, 0.5), (0.0, 0.5, 0.5), (1.0, 0.5, 0.5)]


def _cube_edge_centres() -> List[Tuple[float, float, float]]:
    centres = []
    for i, p in enumerate(_CUBE_CORNERS):
        for q in _CUBE_CORNERS[i + 1:]:
            if sum(1 for k in range(3) if p[k] != q[k]) == 1:
                centres.append(tuple((p[k] + q[k]) / 2 for k in range(3)))
    return centres


_TET_HOLES = [(x, y, z) for x in (0.25, 0.75) for y in (0.25, 0.75)
              for z in (0.25, 0.75)]
_TET_HOLES_ALT = [(0.25, 0.25, 0.25), (0.75, 0.75, 0.25),
                  (0.75, 0.25, 0.75), (0.25, 0.75, 0.75)]


def _ionic_lattice_sites(lattice: str
                         ) -> Tuple[List[Tuple[float, float, float]],
                                    List[Tuple[float, float, float]], str]:
    """(anion positions, cation positions, cell_kind). Two interpenetrating
    sublattices whose occupancies encode the coordination numbers directly."""
    fcc = _CUBE_CORNERS + _CUBE_FACES
    if lattice == "nacl":
        return fcc, _cube_edge_centres() + [(0.5, 0.5, 0.5)], "cube"
    if lattice == "cscl":
        return _CUBE_CORNERS, [(0.5, 0.5, 0.5)], "cube"
    if lattice == "zns_blende":
        return fcc, list(_TET_HOLES_ALT), "cube"
    if lattice == "fluorite":       # cation FCC, anion in ALL tetrahedral holes
        return list(_TET_HOLES), fcc, "cube"
    if lattice == "antifluorite":   # anion FCC, cation in ALL tetrahedral holes
        return fcc, list(_TET_HOLES), "cube"
    # wurtzite — hexagonal ABAB; anions HCP, cations shifted up by ~3/8 c
    c = _HCP_C_OVER_A
    hexagon = _hcp_hexagon(1.0)
    anions, cations = [], []
    for z in (0.0, c):
        for hx, hy in hexagon:
            anions.append((hx, hy, z))
        anions.append((0.0, 0.0, z))
    for ax_, ay_, az_ in list(anions):
        cations.append((ax_, ay_, az_ + 0.375 * c))
    return anions, cations, "hex"


def _ionic_lattice_build(schema: IonicLatticeSchema) -> Dict[str, Any]:
    info = _IONIC_LATTICE_INFO[schema.lattice_type]
    out: Dict[str, Any] = {
        "name": info["name"], "cation_cn": info["cation_cn"],
        "anion_cn": info["anion_cn"], "ratio": info["ratio"],
    }
    if schema.radius_ratio is not None:
        pred = _radius_ratio_geometry(schema.radius_ratio)
        out["predicted_cn"] = pred["cn"]
        out["predicted_geometry"] = pred["geometry"]
        out["predicted_lattice"] = pred["lattice_hint"]
        out["radius_ratio_matches"] = (pred["cn"] == info["cation_cn"])
    return out


def render_ionic_lattice(data: Dict[str, Any],
                         canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = IonicLatticeSchema(**data)
    from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
    from matplotlib.lines import Line2D

    built = _ionic_lattice_build(schema)
    anions, cations, kind = _ionic_lattice_sites(schema.lattice_type)

    fig = plt.figure(figsize=(canvas_w / 100, canvas_h / 100))
    ax = fig.add_subplot(111, projection="3d")
    ax.set_proj_type("ortho")
    ax.view_init(elev=18, azim=-58)
    ax.set_axis_off()

    if kind == "hex":
        c = _HCP_C_OVER_A
        ax.set_xlim(-1.2, 1.2); ax.set_ylim(-1.2, 1.2)
        ax.set_zlim(-0.2, c + 0.8)
        ax.set_box_aspect((2.4, 2.4, c + 1.0))
        hexagon = _hcp_hexagon(1.0)
        for z in (0.0, c):
            for k in range(6):
                hx, hy = hexagon[k]; qx, qy = hexagon[(k + 1) % 6]
                ax.plot([hx, qx], [hy, qy], [z, z], color="#7F8C8D", lw=1.0, zorder=1)
        for hx, hy in hexagon:
            ax.plot([hx, hx], [hy, hy], [0.0, c], color="#7F8C8D", lw=1.0, zorder=1)
    else:
        ax.set_xlim(-0.12, 1.12); ax.set_ylim(-0.12, 1.12); ax.set_zlim(-0.12, 1.12)
        ax.set_box_aspect((1, 1, 1))
        for i, p in enumerate(_CUBE_CORNERS):
            for q in _CUBE_CORNERS[i + 1:]:
                if sum(1 for k in range(3) if p[k] != q[k]) == 1:
                    ax.plot([p[0], q[0]], [p[1], q[1]], [p[2], q[2]],
                            color="#7F8C8D", lw=1.1, zorder=1)

    # anion = larger, cool colour; cation = smaller, warm colour.
    axs, ays, azs = zip(*anions)
    ax.scatter(axs, ays, azs, s=230, c="#2980B9", edgecolors="black",
               linewidths=0.6, depthshade=False, zorder=3)
    cxs, cys, czs = zip(*cations)
    ax.scatter(cxs, cys, czs, s=95, c="#E74C3C", edgecolors="black",
               linewidths=0.6, depthshade=False, zorder=4)

    handles = [
        Line2D([0], [0], marker="o", linestyle="none", markersize=11,
               markerfacecolor="#2980B9", markeredgecolor="black",
               label=f"{schema.anion} (anion)"),
        Line2D([0], [0], marker="o", linestyle="none", markersize=7,
               markerfacecolor="#E74C3C", markeredgecolor="black",
               label=f"{schema.cation} (cation)"),
    ]
    ax.legend(handles=handles, loc="lower left", fontsize=9, framealpha=0.9)

    lines = []
    if schema.show_coordination:
        lines.append(f"Coordination (cation:anion) = {built['ratio']}")
    if schema.show_radius_ratio and "predicted_cn" in built:
        lines.append(f"r₊/r₋ = {schema.radius_ratio:.3f} → predicted C.N. "
                     f"{built['predicted_cn']}")
        verdict = "consistent with" if built["radius_ratio_matches"] else "does NOT match"
        lines.append(f"({built['predicted_geometry']})")
        lines.append(f"Rule {verdict} {built['name']}")
    for i, line in enumerate(lines):
        ax.text2D(0.01, 0.99 - 0.05 * i, line, transform=ax.transAxes,
                  fontsize=9.5, fontweight="bold" if i == 0 else "normal",
                  color="#1A252F", va="top")

    ax.set_title(schema.title or f"Ionic Lattice: {built['name']}",
                 fontsize=13, fontweight="bold", pad=4)
    return _fig_to_svg(fig)


# ── 3. Solid-State Point Defects ──────────────────────────────────────────────

# The density consequence is the exam question, so it is stored as data, not left
# to the drawing: Schottky removes matched pairs (density ↓), Frenkel only relocates
# an ion (density unchanged).
_DEFECT_INFO: Dict[str, Dict[str, str]] = {
    "schottky": {
        "name": "Schottky Defect", "density": "decreases",
        "note": "A cation AND an anion are both missing (a matched pair of vacancies). "
                "Mass falls at constant volume, so DENSITY DECREASES. Stoichiometry is "
                "preserved. Seen in high-C.N. ionic solids (NaCl, KCl, CsCl).",
    },
    "frenkel": {
        "name": "Frenkel Defect", "density": "unchanged",
        "note": "A (smaller) cation leaves its site for an interstitial void — it is "
                "still inside the crystal, so mass and volume are unchanged and DENSITY "
                "is UNCHANGED. Seen where ions differ greatly in size (ZnS, AgCl, AgBr).",
    },
    "interstitial": {
        "name": "Interstitial Defect", "density": "increases",
        "note": "An extra atom occupies an interstitial void. Mass rises at constant "
                "volume, so DENSITY INCREASES (e.g. C in the interstices of iron → steel).",
    },
    "substitutional": {
        "name": "Substitutional Defect", "density": "varies",
        "note": "A host ion is replaced by a foreign ion of different mass, so the "
                "density change DEPENDS on the impurity (it may rise or fall).",
    },
    "f_centre": {
        "name": "F-Centre (Colour Centre)", "density": "decreases",
        "note": "An anion vacancy traps an unpaired electron (a metal-excess defect). "
                "The missing anion lowers density slightly and the trapped electron "
                "absorbs light, so the crystal is COLOURED (e.g. NaCl turns yellow).",
    },
}


def _defect_density(defect: str) -> str:
    return _DEFECT_INFO[defect]["density"]


def render_solid_defects(data: Dict[str, Any],
                         canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = SolidDefectsSchema(**data)
    info = _DEFECT_INFO[schema.defect]

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))
    ax.set_aspect("equal")
    ax.axis("off")

    nx, ny = 6, 5
    ax.set_xlim(-0.7, nx - 0.3)
    ax.set_ylim(-1.6, ny - 0.2)

    C_CAT, C_AN = "#E74C3C", "#2980B9"
    r_cat, r_an = 0.20, 0.30

    def ion_at(i, j):
        """Even (i+j) → cation, else anion."""
        return "cat" if (i + j) % 2 == 0 else "an"

    # sites to blank out, and extra ions to draw
    vac_sites = set()          # (i,j) drawn as an empty dashed vacancy
    interstitials = []         # (x, y, kind, label)
    replaced = {}              # (i,j) -> (color, label)
    arrows = []                # ((x0,y0),(x1,y1))

    if schema.defect == "schottky":
        vac_sites = {(2, 2), (3, 2)}     # (i+j) even → cation site, odd → anion site
    elif schema.defect == "frenkel":
        vac_sites = {(2, 2)}             # cation leaves this site …
        interstitials = [(2.5, 2.5, "cat", schema.cation)]   # … lands here
        arrows = [((2.0, 2.0), (2.42, 2.42))]
    elif schema.defect == "interstitial":
        interstitials = [(2.5, 2.5, "small", "X")]
    elif schema.defect == "substitutional":
        replaced = {(2, 2): ("#27AE60", "M")}
    elif schema.defect == "f_centre":
        vac_sites = {(3, 2)}             # anion vacancy …
        interstitials = [(3.0, 2.0, "electron", "e⁻")]   # … holding a trapped e⁻

    # base lattice
    for j in range(ny):
        for i in range(nx):
            if (i, j) in vac_sites:
                kind = ion_at(i, j)
                r = r_cat if kind == "cat" else r_an
                ax.add_patch(plt.Circle((i, j), r, fill=False, edgecolor="#7F8C8D",
                                        linestyle=(0, (2, 2)), linewidth=1.4, zorder=2))
                ax.text(i, j - 0.02, "vacancy", ha="center", va="center",
                        fontsize=5.5, color="#7F8C8D")
                continue
            if (i, j) in replaced:
                col, lbl = replaced[(i, j)]
                ax.add_patch(plt.Circle((i, j), r_an, color=col, zorder=3))
                ax.text(i, j, lbl, ha="center", va="center", fontsize=8,
                        color="white", fontweight="bold", zorder=4)
                continue
            kind = ion_at(i, j)
            col = C_CAT if kind == "cat" else C_AN
            r = r_cat if kind == "cat" else r_an
            lbl = schema.cation if kind == "cat" else schema.anion
            ax.add_patch(plt.Circle((i, j), r, color=col, zorder=3))
            ax.text(i, j, lbl, ha="center", va="center",
                    fontsize=6.5 if kind == "cat" else 7.5,
                    color="white", fontweight="bold", zorder=4)

    for (x, y, k, lbl) in interstitials:
        if k == "electron":
            ax.add_patch(plt.Circle((x, y), 0.26, fill=False, edgecolor="#8E44AD",
                                    linestyle=(0, (2, 2)), linewidth=1.4, zorder=2))
            ax.text(x, y, lbl, ha="center", va="center", fontsize=9,
                    color="#8E44AD", fontweight="bold", zorder=5)
        elif k == "small":
            ax.add_patch(plt.Circle((x, y), 0.13, color="#F39C12",
                                    ec="black", lw=0.6, zorder=5))
            ax.text(x + 0.32, y, "interstitial\natom", ha="left", va="center",
                    fontsize=6, color="#B9770E")
        else:   # relocated cation
            ax.add_patch(plt.Circle((x, y), r_cat, color=C_CAT, ec="black",
                                    lw=0.6, zorder=5))
            ax.text(x, y, lbl, ha="center", va="center", fontsize=6.5,
                    color="white", fontweight="bold", zorder=6)
            ax.text(x + 0.3, y + 0.28, "interstitial site", ha="left", va="center",
                    fontsize=6, color="#7B241C")

    for (p0, p1) in arrows:
        ax.annotate("", xy=p1, xytext=p0,
                    arrowprops=dict(arrowstyle="-|>", color="#7B241C", lw=1.6))

    if schema.show_density_effect:
        sym = {"decreases": "↓", "unchanged": "=", "increases": "↑", "varies": "≈"}
        ax.text((nx - 1) / 2, -0.75,
                f"Density {sym[info['density']]}  ({info['density']})",
                ha="center", va="center", fontsize=12, fontweight="bold",
                color="#1A252F",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="#FCF3CF",
                          edgecolor="#B7950B", linewidth=1.2))
        ax.text((nx - 1) / 2, -1.45, info["note"], ha="center", va="center",
                fontsize=7.2, color="#566573", wrap=True)

    ax.set_title(schema.title or info["name"], fontsize=13, fontweight="bold")
    fig.tight_layout()
    return _fig_to_svg(fig)


# ── 4. Coordination-Complex Isomerism ─────────────────────────────────────────

# Octahedral vertices in a fixed 2D perspective, M at the origin. Indices:
# 0 top, 1 bottom, 2 right-front, 3 left-front, 4 right-back, 5 left-back.
# Trans (180°) pairs: 0–1, 2–5, 3–4. Everything else is cis (90°). These pairings
# are what make cis/trans and fac/mer geometrically correct.
_OCT_XY = [(0.00, 1.50), (0.00, -1.50), (1.35, -0.45),
           (-1.35, -0.45), (0.72, 0.55), (-0.72, 0.55)]
_OCT_TRANS = {0: 1, 1: 0, 2: 5, 5: 2, 3: 4, 4: 3}

# Square-planar: 0 N, 1 E, 2 S, 3 W.  Trans pairs 0–2, 1–3.
_SQ_XY = [(0.0, 1.35), (1.35, 0.0), (0.0, -1.35), (-1.35, 0.0)]

# Tetrahedral projection (all four vertices are mutually cis → no geometric isomers).
_TET_XY = [(0.0, 1.45), (-1.30, -0.55), (1.30, -0.55), (0.0, -1.45)]

_LIG_A_COLOR = "#2980B9"
_LIG_B_COLOR = "#E74C3C"
_METAL_COLOR = "#F39C12"


def _cis_trans_isomers(geometry: str) -> List[str]:
    """MA₄B₂ (octahedral) and MA₂B₂ (square planar) each show cis AND trans.
    Tetrahedral MA₂B₂ has NONE — all four vertices are mutually adjacent."""
    return [] if geometry == "tetrahedral" else ["cis", "trans"]


def _fac_mer_isomers(geometry: str) -> List[str]:
    """fac/mer only exist for an octahedral MA₃B₃; nothing else."""
    return ["fac", "mer"] if geometry == "octahedral" else []


def _draw_metal_frame(ax, cx: float, cy: float, xy: List[Tuple[float, float]],
                      assign: List[Tuple[str, str]], metal: str, scale: float = 1.0):
    """Draw M at (cx,cy) bonded to each vertex; assign = (label, colour) per vertex."""
    for (dx, dy) in xy:
        ax.plot([cx, cx + dx * scale], [cy, cy + dy * scale],
                color=C_BOND, linewidth=1.8, zorder=2)
    ax.add_patch(plt.Circle((cx, cy), 0.30 * scale, color=_METAL_COLOR,
                            ec="black", lw=1.0, zorder=4))
    ax.text(cx, cy, metal, ha="center", va="center", fontsize=10,
            fontweight="bold", zorder=5)
    for (dx, dy), (lbl, col) in zip(xy, assign):
        vx, vy = cx + dx * scale, cy + dy * scale
        ax.add_patch(plt.Circle((vx, vy), 0.26 * scale, color=col,
                                ec="black", lw=0.8, zorder=4))
        ax.text(vx, vy, lbl, ha="center", va="center", fontsize=9.5,
                color="white", fontweight="bold", zorder=5)


def _oct_assignment(b_positions, la, lb):
    return [(lb, _LIG_B_COLOR) if i in b_positions else (la, _LIG_A_COLOR)
            for i in range(6)]


def render_complex_isomerism(data: Dict[str, Any],
                             canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = ComplexIsomerismSchema(**data)
    ligs = list(schema.ligands) or ["A", "B"]
    la = ligs[0]
    lb = ligs[1] if len(ligs) > 1 else "B"
    m = schema.metal
    geom = schema.geometry

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.set_aspect("equal")
    ax.axis("off")

    def panel_title(x, txt, sub=""):
        ax.text(x, 5.3, txt, ha="center", fontsize=12, fontweight="bold",
                color="#1A252F")
        if sub:
            ax.text(x, 4.85, sub, ha="center", fontsize=9, color="#566573")

    note = ""

    if schema.isomerism == "cis_trans":
        if geom == "tetrahedral":
            _draw_metal_frame(ax, 5.0, 2.8, _TET_XY,
                              [(lb, _LIG_B_COLOR), (la, _LIG_A_COLOR),
                               (lb, _LIG_B_COLOR), (la, _LIG_A_COLOR)], m)
            panel_title(5.0, f"Tetrahedral {m}{la}₂{lb}₂")
            note = ("A tetrahedral MA₂B₂ has NO cis/trans isomers — all four vertices "
                    "are mutually adjacent (109.5°), so every arrangement is identical.")
        elif geom == "square_planar":
            _draw_metal_frame(ax, 2.6, 2.9, _SQ_XY,
                              [(lb, _LIG_B_COLOR) if i in (0, 1) else (la, _LIG_A_COLOR)
                               for i in range(4)], m)
            panel_title(2.6, "cis", "the two B ligands adjacent (90°)")
            _draw_metal_frame(ax, 7.4, 2.9, _SQ_XY,
                              [(lb, _LIG_B_COLOR) if i in (0, 2) else (la, _LIG_A_COLOR)
                               for i in range(4)], m)
            panel_title(7.4, "trans", "the two B ligands opposite (180°)")
            note = f"Square-planar {m}{la}₂{lb}₂ (e.g. [Pt(NH₃)₂Cl₂]) shows cis & trans."
        else:  # octahedral MA4B2
            _draw_metal_frame(ax, 2.6, 2.9, _OCT_XY, _oct_assignment({0, 2}, la, lb), m)
            panel_title(2.6, "cis", "B ligands 90° apart (adjacent)")
            _draw_metal_frame(ax, 7.4, 2.9, _OCT_XY, _oct_assignment({0, 1}, la, lb), m)
            panel_title(7.4, "trans", "B ligands 180° apart (axial)")
            note = f"Octahedral {m}{la}₄{lb}₂ shows cis AND trans geometric isomers."

    elif schema.isomerism == "fac_mer":
        _draw_metal_frame(ax, 2.6, 2.9, _OCT_XY, _oct_assignment({0, 2, 3}, la, lb), m)
        panel_title(2.6, "fac (facial)", "3 B on one triangular face, all cis")
        _draw_metal_frame(ax, 7.4, 2.9, _OCT_XY, _oct_assignment({0, 1, 2}, la, lb), m)
        panel_title(7.4, "mer (meridional)", "3 B round a meridian (one trans pair)")
        note = f"Octahedral {m}{la}₃{lb}₃ shows fac and mer isomers."

    elif schema.isomerism == "optical":
        # Tris-chelate propeller drawn as three bidentate bridges over cis pairs,
        # then mirrored: the two are non-superimposable (Δ and Λ enantiomers).
        chelate_pairs = [(0, 2), (3, 1), (5, 4)]
        for cx0, hand in ((2.6, False), (7.4, True)):
            xy = [( -dx if hand else dx, dy) for (dx, dy) in _OCT_XY]
            _draw_metal_frame(ax, cx0, 2.9, xy,
                              [(la, _LIG_A_COLOR)] * 6, m, scale=0.95)
            for i, j in chelate_pairs:
                p = (cx0 + xy[i][0] * 0.95, 2.9 + xy[i][1] * 0.95)
                q = (cx0 + xy[j][0] * 0.95, 2.9 + xy[j][1] * 0.95)
                ax.annotate("", xy=q, xytext=p,
                            arrowprops=dict(arrowstyle="-", color="#1E8449", lw=2.4,
                                            connectionstyle="arc3,rad=0.35"))
        panel_title(2.6, "Δ (left-handed)")
        panel_title(7.4, "Λ (right-handed)")
        ax.plot([5.0, 5.0], [0.9, 4.6], color="#7F8C8D", linestyle=(0, (4, 3)),
                linewidth=1.3)
        ax.text(5.0, 4.7, "mirror", ha="center", fontsize=8, color="#7F8C8D")
        note = (f"[{m}(AA)₃] (AA = bidentate, e.g. en): the two forms are "
                "non-superimposable mirror images — optical isomers (enantiomers).")

    elif schema.isomerism == "linkage":
        # Same ligand, different donor atom: nitro (M–NO₂) vs nitrito (M–ONO).
        def draw_donor(cx0, via_n):
            mx, my = cx0 - 0.9, 2.9
            ax.add_patch(plt.Circle((mx, my), 0.34, color=_METAL_COLOR, ec="black",
                                    lw=1.0, zorder=4))
            ax.text(mx, my, m, ha="center", va="center", fontsize=11,
                    fontweight="bold", zorder=5)
            if via_n:
                ax.plot([mx + 0.34, mx + 1.2], [my, my], color=C_BOND, lw=2)
                ax.text(mx + 1.45, my, "N", ha="center", va="center", fontsize=12,
                        fontweight="bold", color="#7D3C98")
                ax.text(mx + 1.45, my + 0.6, "O", ha="center", fontsize=11)
                ax.text(mx + 1.45, my - 0.6, "O", ha="center", fontsize=11)
                ax.plot([mx + 1.45, mx + 1.45], [my + 0.25, my + 0.42], color=C_BOND, lw=2)
                ax.plot([mx + 1.45, mx + 1.45], [my - 0.25, my - 0.42], color=C_BOND, lw=2)
            else:
                ax.plot([mx + 0.34, mx + 1.1], [my, my], color=C_BOND, lw=2)
                ax.text(mx + 1.3, my, "O", ha="center", va="center", fontsize=12,
                        fontweight="bold", color="#C0392B")
                ax.plot([mx + 1.5, mx + 2.0], [my, my], color=C_BOND, lw=2)
                ax.text(mx + 2.2, my, "N", ha="center", va="center", fontsize=12,
                        fontweight="bold")
                ax.text(mx + 2.2, my + 0.6, "O", ha="center", fontsize=11)
                ax.plot([mx + 2.2, mx + 2.2], [my + 0.25, my + 0.42], color=C_BOND, lw=2)
        draw_donor(2.6, True)
        draw_donor(7.4, False)
        panel_title(2.6, "nitro  (M–NO₂)", "bonded through N")
        panel_title(7.4, "nitrito  (M–ONO)", "bonded through O")
        note = ("Linkage isomers: an ambidentate ligand (NO₂⁻, SCN⁻, CN⁻) binds through "
                "a different donor atom. e.g. [Co(NH₃)₅(NO₂)]²⁺ vs [Co(NH₃)₅(ONO)]²⁺.")

    elif schema.isomerism == "ionisation":
        ax.text(2.6, 3.2, "[Co(NH₃)₅Br]SO₄", ha="center", fontsize=12,
                fontweight="bold", bbox=dict(boxstyle="round,pad=0.4", fc="white",
                                             ec="#1A5276", lw=1.5))
        ax.text(2.6, 2.2, "→ SO₄²⁻ free in solution", ha="center", fontsize=9.5,
                color="#7B241C")
        ax.text(7.4, 3.2, "[Co(NH₃)₅SO₄]Br", ha="center", fontsize=12,
                fontweight="bold", bbox=dict(boxstyle="round,pad=0.4", fc="white",
                                             ec="#1A5276", lw=1.5))
        ax.text(7.4, 2.2, "→ Br⁻ free in solution", ha="center", fontsize=9.5,
                color="#7B241C")
        panel_title(2.6, "gives SO₄²⁻")
        panel_title(7.4, "gives Br⁻")
        note = ("Ionisation isomers exchange a ligand with the counter-ion, so they "
                "release DIFFERENT ions in solution (test: BaCl₂ vs AgNO₃).")

    else:  # coordination
        ax.text(2.6, 3.0, "[Co(NH₃)₆][Cr(CN)₆]", ha="center", fontsize=12,
                fontweight="bold", bbox=dict(boxstyle="round,pad=0.4", fc="white",
                                             ec="#1A5276", lw=1.5))
        ax.text(7.4, 3.0, "[Cr(NH₃)₆][Co(CN)₆]", ha="center", fontsize=12,
                fontweight="bold", bbox=dict(boxstyle="round,pad=0.4", fc="white",
                                             ec="#1A5276", lw=1.5))
        panel_title(2.6, "NH₃ on Co, CN⁻ on Cr")
        panel_title(7.4, "NH₃ on Cr, CN⁻ on Co")
        note = ("Coordination isomers swap the ligand sets between the complex cation "
                "and complex anion (both ions are complexes).")

    if schema.show_labels and note:
        ax.text(5.0, 0.5, note, ha="center", va="center", fontsize=9,
                color="#1A252F", wrap=True,
                bbox=dict(boxstyle="round,pad=0.4", facecolor="#F4F6F7",
                          edgecolor="#AEB6BF", linewidth=1))

    ax.set_title(schema.title or f"{schema.isomerism.replace('_', '/').title()} "
                 f"Isomerism: {schema.complex_formula}",
                 fontsize=13, fontweight="bold")
    fig.tight_layout()
    return _fig_to_svg(fig)


# ── 10. Resonance Structures ──────────────────────────────────────────────────

# Each species: how many equivalent contributing structures, the central atom, the
# peripheral atoms, and the overall charge. The DOUBLE bond rotates over the
# equivalent positions from one structure to the next — that delocalisation is the
# whole point, and the number of forms is a fact (CO₃²⁻ → 3, O₃ → 2).
_RESONANCE_DB: Dict[str, Dict[str, Any]] = {
    "benzene":   {"kind": "ring", "n": 2, "charge": "", "name": "Benzene (C₆H₆)"},
    "carbonate": {"kind": "trigonal", "central": "C", "outer": "O", "n": 3,
                  "charge": "2−", "name": "Carbonate (CO₃²⁻)"},
    "nitrate":   {"kind": "trigonal", "central": "N", "outer": "O", "n": 3,
                  "charge": "−", "name": "Nitrate (NO₃⁻)"},
    "ozone":     {"kind": "bent", "central": "O", "outer": "O", "n": 2,
                  "charge": "", "name": "Ozone (O₃)"},
}


def _draw_double_bond(ax, p, q, color="black", off=0.09):
    (x1, y1), (x2, y2) = p, q
    dx, dy = x2 - x1, y2 - y1
    L = math.hypot(dx, dy) or 1.0
    px, py = -dy / L, dx / L
    for s in (off, -off):
        ax.plot([x1 + px * s, x2 + px * s], [y1 + py * s, y2 + py * s],
                color=color, lw=1.7, zorder=2)


def _draw_trigonal_resonance(ax, cx, cy, central, outer, charge, double_idx, scale=0.85):
    """Central atom, 3 outer atoms at 120°; the atom at `double_idx` gets the C=O."""
    angles = [90, 210, 330]
    pts = [(cx + scale * math.cos(math.radians(a)),
            cy + scale * math.sin(math.radians(a))) for a in angles]
    ax.text(cx, cy, central, ha="center", va="center", fontsize=13,
            fontweight="bold", zorder=5,
            bbox=dict(boxstyle="circle,pad=0.14", fc="white", ec="none"))
    for i, (px, py) in enumerate(pts):
        if i == double_idx:
            _draw_double_bond(ax, (cx, cy), (px, py))
            tag = ""
        else:
            ax.plot([cx, px], [cy, py], color="black", lw=1.7, zorder=2)
            tag = "−"
        ax.text(px, py, outer, ha="center", va="center", fontsize=12,
                fontweight="bold", zorder=5,
                bbox=dict(boxstyle="circle,pad=0.12", fc="white", ec="none"))
        if tag:
            ax.text(px + 0.22, py + 0.22, tag, ha="center", fontsize=9, color="#C0392B")


def render_resonance_structures(data: Dict[str, Any],
                                canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = ResonanceStructuresSchema(**data)
    info = _RESONANCE_DB[schema.species]

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.set_aspect("equal")
    ax.axis("off")

    n = info["n"]
    show_hy = schema.show_hybrid
    n_panels = n + (1 if show_hy else 0)
    xs = [(i + 0.5) * 10.0 / n_panels for i in range(n_panels)]
    cy = 3.4

    if info["kind"] == "ring":
        # Two Kekulé structures: double bonds on alternating edges (0,2,4) vs (1,3,5).
        def hexagon(cx):
            r = 1.05
            verts = [(cx + r * math.cos(math.radians(60 * k + 30)),
                      cy + r * math.sin(math.radians(60 * k + 30))) for k in range(6)]
            return verts

        for panel in range(n):
            cx = xs[panel]
            verts = hexagon(cx)
            for k in range(6):
                p, q = verts[k], verts[(k + 1) % 6]
                ax.plot([p[0], q[0]], [p[1], q[1]], color="black", lw=1.7, zorder=2)
                if k % 2 == panel % 2:
                    # inset double bond
                    mx, my = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
                    nx, ny = cx - mx, cy - my
                    nn = math.hypot(nx, ny) or 1
                    ox, oy = nx / nn * 0.16, ny / nn * 0.16
                    ax.plot([p[0] + ox, q[0] + ox], [p[1] + oy, q[1] + oy],
                            color="black", lw=1.6, zorder=2)
        if show_hy:
            cx = xs[-1]
            verts = hexagon(cx)
            for k in range(6):
                p, q = verts[k], verts[(k + 1) % 6]
                ax.plot([p[0], q[0]], [p[1], q[1]], color="black", lw=1.7, zorder=2)
            ax.add_patch(plt.Circle((cx, cy), 0.55, fill=False, edgecolor="black",
                                    lw=1.6, zorder=2))
    elif info["kind"] == "trigonal":
        for panel in range(n):
            _draw_trigonal_resonance(ax, xs[panel], cy, info["central"],
                                     info["outer"], info["charge"], panel)
        if show_hy:
            cx = xs[-1]
            angles = [90, 210, 330]
            pts = [(cx + 0.85 * math.cos(math.radians(a)),
                    cy + 0.85 * math.sin(math.radians(a))) for a in angles]
            ax.text(cx, cy, info["central"], ha="center", va="center", fontsize=13,
                    fontweight="bold", zorder=5)
            for (px, py) in pts:
                ax.plot([cx, px], [cy, py], color="black", lw=1.7, zorder=2)
                ax.plot([cx + (px - cx) * 0.28, px], [cy + (py - cy) * 0.28, py],
                        color="black", lw=1.7, linestyle=(0, (3, 2)), zorder=2)
                ax.text(px, py, info["outer"], ha="center", va="center", fontsize=12,
                        fontweight="bold", zorder=5,
                        bbox=dict(boxstyle="circle,pad=0.12", fc="white", ec="none"))
    else:  # bent (ozone)
        for panel in range(n):
            cx = xs[panel]
            apex = (cx, cy + 0.7)
            left = (cx - 0.95, cy - 0.4)
            right = (cx + 0.95, cy - 0.4)
            # the π bond sits on the left in structure 0, the right in structure 1
            db_side = left if panel == 0 else right
            sg_side = right if panel == 0 else left
            _draw_double_bond(ax, apex, db_side)
            ax.plot([apex[0], sg_side[0]], [apex[1], sg_side[1]], color="black",
                    lw=1.7, zorder=2)
            for (px, py), lbl in ((apex, info["outer"]), (left, info["outer"]),
                                  (right, info["outer"])):
                ax.text(px, py, lbl, ha="center", va="center", fontsize=12,
                        fontweight="bold", zorder=5,
                        bbox=dict(boxstyle="circle,pad=0.12", fc="white", ec="none"))
            ax.text(sg_side[0] + 0.25, sg_side[1] + 0.2, "−", fontsize=10,
                    color="#C0392B")
            ax.text(apex[0] + 0.28, apex[1], "+", fontsize=10, color="#1A5276")
        if show_hy:
            cx = xs[-1]
            apex = (cx, cy + 0.7); left = (cx - 0.95, cy - 0.4); right = (cx + 0.95, cy - 0.4)
            for side in (left, right):
                ax.plot([apex[0], side[0]], [apex[1], side[1]], color="black", lw=1.7)
                ax.plot([apex[0] + (side[0] - apex[0]) * 0.3, side[0]],
                        [apex[1] + (side[1] - apex[1]) * 0.3, side[1]],
                        color="black", lw=1.6, linestyle=(0, (3, 2)))
            for (px, py) in (apex, left, right):
                ax.text(px, py, info["outer"], ha="center", va="center", fontsize=12,
                        fontweight="bold", zorder=5,
                        bbox=dict(boxstyle="circle,pad=0.12", fc="white", ec="none"))

    # double-headed resonance arrows between panels
    for i in range(n_panels - 1):
        x0, x1 = xs[i] + 0.9, xs[i + 1] - 0.9
        if x1 > x0:
            ax.annotate("", xy=(x1, cy), xytext=(x0, cy),
                        arrowprops=dict(arrowstyle="<->", color="#1A252F", lw=1.8))
            if show_hy and i == n_panels - 2:
                ax.text((x0 + x1) / 2, cy + 0.25, "hybrid", ha="center",
                        fontsize=8, color="#566573")

    # curved arrows on the FIRST structure showing the electron shift
    if schema.show_curved_arrows and info["kind"] in ("ring", "trigonal", "bent"):
        forms = "both forms" if n == 2 else f"all {n} forms"
        ax.text(0.02, 0.03,
                "↷ curved arrows show delocalisation of the π electrons; the real "
                f"species is a single hybrid of {forms}.",
                transform=ax.transAxes, fontsize=8.5, color=C_ANNOT, va="bottom")

    ax.set_title(schema.title or f"Resonance Structures: {info['name']}",
                 fontsize=13, fontweight="bold")
    fig.tight_layout()
    return _fig_to_svg(fig)


# ── 11. Free-Radical Chain Mechanism ──────────────────────────────────────────

# Each reaction as its three phases. The fish-hook (single-barb) arrow moves ONE
# electron — that is what distinguishes a radical step from an ionic one, so the
# initiation homolysis is the anchor of the diagram.
_FREE_RADICAL_DB: Dict[str, Dict[str, Any]] = {
    "methane_chlorination": {
        "name": "Free-Radical Chlorination of Methane",
        "overall": "CH₄ + Cl₂ → CH₃Cl + HCl   (hν, UV light)",
        "homolysis": ("Cl", "Cl"),   # the bond broken in initiation
        "initiation": "Cl₂ →(hν) 2 Cl•",
        "propagation": ["Cl• + CH₄ → •CH₃ + HCl",
                        "•CH₃ + Cl₂ → CH₃Cl + Cl•"],
        "termination": ["Cl• + Cl• → Cl₂",
                        "•CH₃ + Cl• → CH₃Cl",
                        "•CH₃ + •CH₃ → C₂H₆"],
    },
    "methane_bromination": {
        "name": "Free-Radical Bromination of Methane",
        "overall": "CH₄ + Br₂ → CH₃Br + HBr   (hν)",
        "homolysis": ("Br", "Br"),
        "initiation": "Br₂ →(hν) 2 Br•",
        "propagation": ["Br• + CH₄ → •CH₃ + HBr",
                        "•CH₃ + Br₂ → CH₃Br + Br•"],
        "termination": ["Br• + Br• → Br₂",
                        "•CH₃ + Br• → CH₃Br",
                        "•CH₃ + •CH₃ → C₂H₆"],
    },
    "ethane_chlorination": {
        "name": "Free-Radical Chlorination of Ethane",
        "overall": "C₂H₆ + Cl₂ → C₂H₅Cl + HCl   (hν)",
        "homolysis": ("Cl", "Cl"),
        "initiation": "Cl₂ →(hν) 2 Cl•",
        "propagation": ["Cl• + C₂H₆ → •C₂H₅ + HCl",
                        "•C₂H₅ + Cl₂ → C₂H₅Cl + Cl•"],
        "termination": ["Cl• + Cl• → Cl₂",
                        "•C₂H₅ + Cl• → C₂H₅Cl",
                        "•C₂H₅ + •C₂H₅ → C₄H₁₀"],
    },
    "chlorination_of_alkane": {
        "name": "Free-Radical Chlorination of an Alkane",
        "overall": "R–H + Cl₂ → R–Cl + HCl   (hν)",
        "homolysis": ("Cl", "Cl"),
        "initiation": "Cl₂ →(hν) 2 Cl•",
        "propagation": ["Cl• + R–H → R• + HCl",
                        "R• + Cl₂ → R–Cl + Cl•"],
        "termination": ["Cl• + Cl• → Cl₂",
                        "R• + Cl• → R–Cl",
                        "R• + R• → R–R"],
    },
}


def render_free_radical_mechanism(data: Dict[str, Any],
                                  canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = FreeRadicalMechanismSchema(**data)
    info = _FREE_RADICAL_DB[schema.reaction]

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")

    ax.text(5.0, 9.5, info["overall"], ha="center", fontsize=11, fontweight="bold",
            color="#1A252F")

    phases = [("INITIATION", "#C0392B",
               "homolysis — the bond splits, 1 e⁻ to each atom (fish-hooks)"),
              ("PROPAGATION", "#1A5276",
               "chain-carrying steps: a radical is consumed and another made"),
              ("TERMINATION", "#1E8449",
               "two radicals combine — the chain ends")]
    if not schema.show_all_phases:
        phases = phases[:2]

    y = 8.4
    row_h = 2.6
    for label, color, blurb in phases:
        ax.add_patch(mpatches.FancyBboxPatch((0.3, y - 0.55), 2.15, 1.0,
                                             boxstyle="round,pad=0.06",
                                             facecolor=color, edgecolor="none",
                                             zorder=2))
        ax.text(1.37, y, label, ha="center", va="center", fontsize=10.5,
                fontweight="bold", color="white", zorder=3)
        ax.text(1.37, y - 0.85, blurb, ha="center", va="top", fontsize=6.8,
                color="#566573", wrap=True)

        if label == "INITIATION":
            eqn_x = 3.1
            ax.text(eqn_x, y, info["initiation"], ha="left", va="center",
                    fontsize=12, fontweight="bold")
            if schema.show_fish_hook_arrows:
                a, b = info["homolysis"]
                bx, by = eqn_x + 0.18, y - 0.55        # under the X–X bond
                ax.text(bx, by, f"{a}—{b}", ha="left", va="center", fontsize=10,
                        color="#7B241C")
                # two fish-hook (single-barb) half arrows, one to each atom
                _curved_arrow(ax, (bx + 0.28, by - 0.05), (bx + 0.02, by - 0.45),
                              0.4, "#7B241C", half=True)
                _curved_arrow(ax, (bx + 0.55, by - 0.05), (bx + 0.85, by - 0.45),
                              -0.4, "#7B241C", half=True)
                ax.text(bx + 1.15, by - 0.3, "single-electron\nfish-hook arrows",
                        ha="left", va="center", fontsize=7, color="#7B241C")
        else:
            eqns = info["propagation"] if label == "PROPAGATION" else info["termination"]
            for k, eqn in enumerate(eqns):
                ax.text(3.1, y + 0.35 - k * 0.62, eqn, ha="left", va="center",
                        fontsize=10.5, fontweight="bold")
        y -= row_h

    if schema.show_fish_hook_arrows:
        ax.text(0.02, 0.01,
                "↷ fish-hook (half) arrow = ONE electron (radical) — contrast the "
                "double-barb curved arrow that moves a PAIR.",
                transform=ax.transAxes, fontsize=8, color=C_ANNOT, va="bottom")

    ax.set_title(schema.title or info["name"], fontsize=13, fontweight="bold")
    fig.tight_layout()
    return _fig_to_svg(fig)


# ── 5. Polymer Structure ──────────────────────────────────────────────────────

# Repeat units are written with [*] attachment points so RDKit draws the true
# repeating fragment (–CH₂–CHCl– for PVC, the amide/ester link for the condensation
# polymers), not a capped small molecule. classification/linkage are FACTS.
_POLYMER_DB: Dict[str, Dict[str, Any]] = {
    "polythene": {
        "name": "Polythene (Polyethylene)",
        "monomers": [("ethene (ethylene)", "C=C")],
        "repeat": "*CC*", "repeat_text": "–[CH₂–CH₂]–ₙ",
        "classification": "addition", "linkage": "C–C (addition across the C=C)",
    },
    "pvc": {
        "name": "Poly(vinyl chloride), PVC",
        "monomers": [("vinyl chloride", "C=CCl")],
        "repeat": "*CC(Cl)*", "repeat_text": "–[CH₂–CHCl]–ₙ",
        "classification": "addition", "linkage": "C–C (addition across the C=C)",
    },
    "natural_rubber": {
        "name": "Natural Rubber (cis-1,4-polyisoprene)",
        "monomers": [("isoprene (2-methylbuta-1,3-diene)", "C=CC(=C)C")],
        "repeat": "*CC(C)=CC*", "repeat_text": "–[CH₂–C(CH₃)=CH–CH₂]–ₙ",
        "classification": "addition", "linkage": "1,4-addition of a conjugated diene",
    },
    "nylon-6,6": {
        "name": "Nylon-6,6",
        "monomers": [("hexamethylenediamine", "NCCCCCCN"),
                     ("adipic acid", "OC(=O)CCCCC(=O)O")],
        "repeat": "*NCCCCCCNC(=O)CCCCC(=O)*",
        "repeat_text": "–[NH(CH₂)₆NH–CO(CH₂)₄CO]–ₙ",
        "classification": "condensation", "linkage": "amide (–CO–NH–), losing H₂O",
    },
    "terylene": {
        "name": "Terylene (PET / Dacron)",
        "monomers": [("ethylene glycol", "OCCO"),
                     ("terephthalic acid", "OC(=O)c1ccc(cc1)C(=O)O")],
        "repeat": "*OCCOC(=O)c1ccc(cc1)C(=O)*",
        "repeat_text": "–[O–CH₂CH₂–O–CO–C₆H₄–CO]–ₙ",
        "classification": "condensation", "linkage": "ester (–CO–O–), losing H₂O",
    },
    "bakelite": {
        "name": "Bakelite (phenol–formaldehyde)",
        "monomers": [("phenol", "Oc1ccccc1"), ("formaldehyde", "C=O")],
        "repeat": "Oc1ccc(Cc2ccc(O)cc2)cc1",
        "repeat_text": "cross-linked –CH₂– bridges (3-D network)",
        "classification": "condensation",
        "linkage": "methylene (–CH₂–) bridges, losing H₂O (network polymer)",
    },
}


# The strings carry real Unicode sub/superscripts (CH₂, H₂O, ₙ). Emit them directly,
# but under DejaVu Sans — the same font matplotlib uses here, which (unlike Arial)
# cairosvg renders WITH the subscript glyphs instead of tofu boxes.
_SVG_FONT = "DejaVu Sans, Arial, sans-serif"


def _svg_text(x, y, s, size=14, anchor="middle", weight="normal", fill="black"):
    # DejaVu has subscript DIGITS but not subscript-letter ₙ (U+2099) → tofu; the
    # bracket's own large "n" carries the meaning, so fold ₙ down to a plain n.
    s = s.replace("ₙ", "n")
    esc = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return (f'<text x="{x}" y="{y}" font-size="{size}" font-family="{_SVG_FONT}" '
            f'text-anchor="{anchor}" font-weight="{weight}" fill="{fill}">{esc}</text>')


def _rdkit_panel_svg(smiles: str, w: int, h: int, x: int, y: int) -> str:
    """One RDKit structure as a nested <svg> positioned at (x, y)."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return _svg_text(x + w / 2, y + h / 2, smiles, size=12)
    AllChem.Compute2DCoords(mol)
    d = rdMolDraw2D.MolDraw2DSVG(w, h)
    d.drawOptions().useBWAtomPalette()
    d.drawOptions().clearBackground = False
    d.DrawMolecule(mol)
    d.FinishDrawing()
    svg = d.GetDrawingText()
    svg = svg[svg.find("<svg"):]
    return svg.replace("<svg ", f'<svg x="{x}" y="{y}" ', 1)


def _polymer_fallback_svg(schema, info) -> str:
    W, H = 900, 300
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
             f'viewBox="0 0 {W} {H}">', f'<rect width="{W}" height="{H}" fill="white"/>',
             _svg_text(W / 2, 40, schema.title or info["name"], size=16, weight="bold"),
             _svg_text(W / 2, 110, "Monomer(s): "
                       + ", ".join(m for m, _s in info["monomers"]), size=13),
             _svg_text(W / 2, 150, "Repeat unit: " + info["repeat_text"], size=14,
                       weight="bold"),
             _svg_text(W / 2, 200, f"Classification: {info['classification']}", size=12),
             _svg_text(W / 2, 230, f"Linkage: {info['linkage']}", size=12),
             '</svg>']
    return "\n".join(parts)


def render_polymer_structure(data: Dict[str, Any],
                             canvas_w: int = 900, canvas_h: int = 480) -> str:
    schema = PolymerStructureSchema(**data)
    info = _POLYMER_DB[schema.polymer]
    classification = schema.classification or info["classification"]

    if not RDKIT_AVAILABLE:
        return _polymer_fallback_svg(schema, info)

    W, H = 900, 480
    PW, PH = 210, 175
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
             f'viewBox="0 0 {W} {H}">', f'<rect width="{W}" height="{H}" fill="white"/>']
    parts.append(_svg_text(W / 2, 34, schema.title or info["name"], size=17,
                           weight="bold"))

    y_panel = 90
    y_cap = y_panel + PH + 22

    def arrow(x0, x1, y, label=""):
        out = [f'<line x1="{x0}" y1="{y}" x2="{x1 - 10}" y2="{y}" stroke="black" '
               f'stroke-width="2"/>',
               f'<polygon points="{x1},{y} {x1 - 12},{y - 6} {x1 - 12},{y + 6}" '
               f'fill="black"/>']
        if label:
            out.append(_svg_text((x0 + x1) / 2, y - 12, label, size=11, fill="#566573"))
        return out

    monomers = info["monomers"] if schema.show_monomer else []
    x = 20
    if monomers:
        if len(monomers) == 1:
            parts.append(_rdkit_panel_svg(monomers[0][1], PW, PH, x, y_panel))
            parts.append(_svg_text(x + PW / 2, y_cap, monomers[0][0], size=11,
                                   fill="#1A5276"))
            x += PW
        else:
            parts.append(_rdkit_panel_svg(monomers[0][1], PW, PH, x, y_panel))
            parts.append(_svg_text(x + PW / 2, y_cap, monomers[0][0], size=10,
                                   fill="#1A5276"))
            parts.append(_svg_text(x + PW + 12, y_panel + PH / 2, "+", size=22,
                                   weight="bold"))
            x += PW + 26
            parts.append(_rdkit_panel_svg(monomers[1][1], PW, PH, x, y_panel))
            parts.append(_svg_text(x + PW / 2, y_cap, monomers[1][0], size=10,
                                   fill="#1A5276"))
            x += PW
        parts.append(_svg_text((20 + x) / 2, y_panel - 14, "Monomer(s)", size=12,
                               weight="bold", fill="#154360"))

    if schema.show_repeating_unit:
        arrow_x0 = x + 12
        rep_x = x + 120
        parts += arrow(arrow_x0, rep_x - 24, y_panel + PH / 2, "polymerises")
        # bracket [ … ]ₙ around the repeat panel
        bx0, bx1 = rep_x - 14, rep_x + PW + 8
        by0, by1 = y_panel + 6, y_panel + PH - 6
        for bx, tick in ((bx0, 12), (bx1, -12)):
            parts.append(f'<polyline points="{bx + tick},{by0} {bx},{by0} {bx},{by1} '
                         f'{bx + tick},{by1}" fill="none" stroke="black" '
                         f'stroke-width="2.5"/>')
        parts.append(_svg_text(bx1 + 12, by1 + 6, "n", size=18, weight="bold",
                               anchor="start"))
        parts.append(_rdkit_panel_svg(info["repeat"], PW, PH, rep_x, y_panel))
        parts.append(_svg_text(rep_x + PW / 2, y_panel - 14, "Repeating unit", size=12,
                               weight="bold", fill="#154360"))
        parts.append(_svg_text(rep_x + PW / 2, y_cap + 22, info["repeat_text"], size=12,
                               weight="bold", fill="#1A252F"))

    parts.append(_svg_text(W / 2, H - 56,
                           f"Classification: {classification} polymer", size=14,
                           weight="bold", fill="#7D3C98"))
    if schema.show_linkage:
        parts.append(_svg_text(W / 2, H - 28, f"Linkage: {info['linkage']}", size=12,
                               fill="#1A252F"))
    parts.append('</svg>')
    return "\n".join(parts)


# ── 8. Protein Structure ──────────────────────────────────────────────────────

def render_protein_structure(data: Dict[str, Any],
                             canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = ProteinStructureSchema(**data)

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.axis("off")

    R1 = "R₁" if schema.show_r_groups else "H"
    R2 = "R₂" if schema.show_r_groups else "H"

    if schema.level == "peptide_bond":
        # Two amino acids condense; the –CO–NH– bond forms and H₂O is eliminated.
        ax.text(2.3, 4.7, f"H₂N–CH(R₁)–C(=O)–OH", ha="center", fontsize=12,
                fontweight="bold")
        ax.text(2.3, 4.25, "amino acid 1", ha="center", fontsize=9, color="#566573")
        ax.text(7.0, 4.7, f"H–NH–CH(R₂)–C(=O)–OH", ha="center", fontsize=12,
                fontweight="bold")
        ax.text(7.0, 4.25, "amino acid 2", ha="center", fontsize=9, color="#566573")
        # highlight the –OH (acid 1) and –H (amine 2) that leave as water
        ax.add_patch(mpatches.FancyBboxPatch((3.15, 4.5), 0.55, 0.4,
                                             boxstyle="round,pad=0.02", facecolor="#FADBD8",
                                             edgecolor="#C0392B", linewidth=1.2, zorder=1))
        ax.add_patch(mpatches.FancyBboxPatch((5.05, 4.5), 0.55, 0.4,
                                             boxstyle="round,pad=0.02", facecolor="#FADBD8",
                                             edgecolor="#C0392B", linewidth=1.2, zorder=1))
        ax.annotate("", xy=(5.0, 2.9), xytext=(5.0, 3.9),
                    arrowprops=dict(arrowstyle="-|>", color="black", lw=1.8))
        ax.text(5.35, 3.4, "– H₂O (condensation)", ha="left", fontsize=10,
                color="#C0392B")
        # dipeptide with the peptide bond highlighted
        ax.text(5.0, 2.2, "H₂N–CH(R₁)–C(=O)–NH–CH(R₂)–C(=O)–OH", ha="center",
                fontsize=13, fontweight="bold")
        ax.add_patch(mpatches.FancyBboxPatch((4.05, 2.0), 1.55, 0.42,
                                             boxstyle="round,pad=0.03", facecolor="none",
                                             edgecolor="#1E8449", linewidth=2.0, zorder=2))
        ax.text(4.82, 1.6, "peptide bond (amide  –CO–NH–)", ha="center", fontsize=10,
                color="#1E8449", fontweight="bold")
        ax.text(5.0, 0.9, "dipeptide", ha="center", fontsize=10, color="#566573")

    elif schema.level == "primary":
        seq = schema.sequence or ["Gly", "Ala", "Ser", "Val", "Leu"]
        n = len(seq)
        x0, step = 1.0, min(1.7, 8.0 / max(n, 1))
        y = 3.0
        for i, res in enumerate(seq):
            x = x0 + i * step
            ax.add_patch(mpatches.FancyBboxPatch((x - 0.42, y - 0.32), 0.84, 0.64,
                                                 boxstyle="round,pad=0.04",
                                                 facecolor="#D6EAF8", edgecolor="#2471A3",
                                                 linewidth=1.4, zorder=3))
            ax.text(x, y, res, ha="center", va="center", fontsize=10,
                    fontweight="bold", zorder=4)
            if i < n - 1:
                nx = x0 + (i + 1) * step
                ax.plot([x + 0.42, nx - 0.42], [y, y], color="black", lw=1.6, zorder=2)
                ax.text((x + nx) / 2, y + 0.22, "CO–NH", ha="center", fontsize=7,
                        color="#1E8449")
        ax.text(5.0, 4.4, "Primary structure = the sequence of amino-acid residues "
                "joined by peptide bonds", ha="center", fontsize=10, color="#1A252F")

    elif schema.level == "secondary_helix":
        # α-helix drawn as a coil; intra-chain H-bonds run parallel to the axis.
        t = np.linspace(0, 6 * np.pi, 400)
        x = 1.5 + t / (6 * np.pi) * 7.0
        yc = 3.0 + 0.7 * np.sin(t)
        ax.plot(x, yc, color="#2471A3", lw=2.6, zorder=2)
        if schema.show_hydrogen_bonds:
            for tt in np.linspace(0.7 * np.pi, 5.3 * np.pi, 6):
                xa = 1.5 + tt / (6 * np.pi) * 7.0
                xb = 1.5 + (tt + 2 * np.pi) / (6 * np.pi) * 7.0
                if xb > 8.5:
                    break
                ya = 3.0 + 0.7 * np.sin(tt)
                yb = 3.0 + 0.7 * np.sin(tt + 2 * np.pi)
                ax.plot([xa, xb], [ya - 0.75, yb - 0.75], color="#C0392B",
                        linestyle=(0, (2, 2)), lw=1.3, zorder=1)
            ax.text(5.0, 1.7, "···· = intramolecular H-bond (C=O ⋯ H–N, every 4th residue)",
                    ha="center", fontsize=9, color="#C0392B")
        ax.text(5.0, 4.6, "α-Helix (secondary structure)", ha="center", fontsize=12,
                fontweight="bold")

    elif schema.level == "secondary_sheet":
        # antiparallel β-pleated sheet: two zig-zag strands, H-bonds between them.
        for row, (yy, direction) in enumerate([(3.7, 1), (2.3, -1)]):
            xs = np.linspace(1.5, 8.5, 15)
            ys = yy + 0.22 * ((-1) ** np.arange(len(xs)))
            ax.plot(xs, ys, color="#2471A3", lw=2.4, zorder=2)
            hx, hy = (8.5, yy) if direction == 1 else (1.5, yy)
            ax.annotate("", xy=(hx, hy), xytext=(hx - 0.6 * direction, hy),
                        arrowprops=dict(arrowstyle="-|>", color="#2471A3", lw=2))
        if schema.show_hydrogen_bonds:
            for xb in np.linspace(2.0, 8.0, 7):
                ax.plot([xb, xb], [3.5, 2.5], color="#C0392B", linestyle=(0, (2, 2)),
                        lw=1.3, zorder=1)
            ax.text(5.0, 1.5, "···· = interstrand H-bonds (antiparallel strands)",
                    ha="center", fontsize=9, color="#C0392B")
        ax.text(5.0, 4.6, "β-Pleated Sheet (secondary structure)", ha="center",
                fontsize=12, fontweight="bold")

    else:  # tertiary
        tt = np.linspace(0, 2 * np.pi, 500)
        xb = 5.0 + 2.6 * np.sin(tt) + 0.7 * np.sin(3 * tt)
        yb = 3.0 + 1.6 * np.cos(tt) + 0.5 * np.cos(2 * tt)
        ax.plot(xb, yb, color="#B9770E", lw=2.0, zorder=1)
        # an embedded helix coil
        th = np.linspace(0, 4 * np.pi, 120)
        ax.plot(4.0 + 0.35 * np.sin(th) + th / (4 * np.pi) * 1.4, 3.4 + 0.05 * th,
                color="#2471A3", lw=2.4, zorder=3)
        # an embedded sheet arrow
        ax.annotate("", xy=(6.6, 2.2), xytext=(5.6, 2.6),
                    arrowprops=dict(arrowstyle="-|>", color="#1E8449", lw=3))
        ax.text(3.4, 4.6, "helix", fontsize=9, color="#2471A3")
        ax.text(6.6, 1.9, "sheet", fontsize=9, color="#1E8449")
        ax.text(5.0, 5.2, "Tertiary structure = the overall 3-D fold "
                "(helices + sheets packed together)", ha="center", fontsize=10,
                color="#1A252F")

    ax.set_title(schema.title or "Protein Structure", fontsize=13, fontweight="bold")
    fig.tight_layout()
    return _fig_to_svg(fig)


# ── 9. Hydrogen Bonding ───────────────────────────────────────────────────────

def _draw_hbond(ax, p, q, color="#C0392B"):
    ax.plot([p[0], q[0]], [p[1], q[1]], color=color, linestyle=(0, (2, 2)),
            lw=1.5, zorder=1)


def _draw_water_mol(ax, x, y, show_charges=True, o_color="#C0392B"):
    ax.add_patch(plt.Circle((x, y), 0.28, color=o_color, ec="black", lw=0.8, zorder=3))
    ax.text(x, y, "O", ha="center", va="center", fontsize=10, color="white",
            fontweight="bold", zorder=4)
    h_pos = []
    for ang in (55, 125):
        hx = x + 0.55 * math.cos(math.radians(ang))
        hy = y + 0.55 * math.sin(math.radians(ang))
        ax.plot([x, hx], [y, hy], color="black", lw=1.6, zorder=2)
        ax.add_patch(plt.Circle((hx, hy), 0.15, color="#D5DBDB", ec="black",
                                lw=0.6, zorder=3))
        ax.text(hx, hy, "H", ha="center", va="center", fontsize=7, zorder=4)
        h_pos.append((hx, hy))
    if show_charges:
        ax.text(x - 0.34, y - 0.05, "δ⁻", fontsize=8, color="#C0392B")
        ax.text(h_pos[0][0] + 0.14, h_pos[0][1], "δ⁺", fontsize=7, color="#1A5276")
    return h_pos


def render_hydrogen_bonding(data: Dict[str, Any],
                            canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = HydrogenBondingSchema(**data)
    sc = schema.show_partial_charges

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.set_aspect("equal")
    ax.axis("off")

    note = ""
    if schema.substance == "water":
        centres = [(3.0, 4.0), (6.5, 4.2), (4.7, 2.2), (7.8, 2.0)]
        hs = [_draw_water_mol(ax, x, y, sc) for x, y in centres]
        _draw_hbond(ax, hs[0][0], (centres[1][0] - 0.3, centres[1][1]))
        _draw_hbond(ax, hs[0][1], (centres[2][0], centres[2][1] + 0.3))
        _draw_hbond(ax, hs[1][1], (centres[3][0], centres[3][1] + 0.3))
        note = "Each H₂O forms up to 4 H-bonds (2 via its H, 2 via O lone pairs)."

    elif schema.substance == "ice":
        # open hexagonal ring of water molecules → cavities → LOWER density.
        cx, cy, r = 5.0, 3.1, 1.8
        ring = [(cx + r * math.cos(math.radians(60 * k + 30)),
                 cy + r * math.sin(math.radians(60 * k + 30))) for k in range(6)]
        for (x, y) in ring:
            _draw_water_mol(ax, x, y, sc)
        for k in range(6):
            p, q = ring[k], ring[(k + 1) % 6]
            _draw_hbond(ax, p, q)
        note = ("Ice is an OPEN tetrahedral H-bonded lattice with large hexagonal "
                "cavities, so it is LESS dense than liquid water → ice floats.")

    elif schema.substance == "hf":
        y = 3.2
        xs = [1.4, 3.4, 5.4, 7.4]
        for i, x in enumerate(xs):
            ax.add_patch(plt.Circle((x, y), 0.30, color="#27AE60", ec="black",
                                    lw=0.8, zorder=3))
            ax.text(x, y, "F", ha="center", va="center", fontsize=11, color="white",
                    fontweight="bold", zorder=4)
            hx = x + 0.85
            ax.plot([x, hx], [y, y], color="black", lw=1.7, zorder=2)
            ax.add_patch(plt.Circle((hx, hy := y), 0.16, color="#D5DBDB", ec="black",
                                    lw=0.6, zorder=3))
            ax.text(hx, y, "H", ha="center", va="center", fontsize=8, zorder=4)
            if sc:
                ax.text(x - 0.42, y + 0.18, "δ⁻", fontsize=8, color="#C0392B")
                ax.text(hx - 0.02, y + 0.28, "δ⁺", fontsize=7, color="#1A5276")
            if i < len(xs) - 1:
                _draw_hbond(ax, (hx + 0.16, y), (xs[i + 1] - 0.30, y))
        note = "HF forms a zig-zag chain of F–H⋯F–H⋯ hydrogen bonds (strongest H-bond)."

    elif schema.substance == "ammonia":
        centres = [(3.0, 4.0), (6.4, 3.6), (4.8, 2.0)]
        for (x, y) in centres:
            ax.add_patch(plt.Circle((x, y), 0.30, color="#2980B9", ec="black",
                                    lw=0.8, zorder=3))
            ax.text(x, y, "N", ha="center", va="center", fontsize=11, color="white",
                    fontweight="bold", zorder=4)
            for ang in (250, 290, 330):
                hx = x + 0.55 * math.cos(math.radians(ang))
                hy = y + 0.55 * math.sin(math.radians(ang))
                ax.plot([x, hx], [y, hy], color="black", lw=1.5, zorder=2)
                ax.add_patch(plt.Circle((hx, hy), 0.13, color="#D5DBDB", ec="black",
                                        lw=0.5, zorder=3))
            if sc:
                ax.text(x - 0.4, y + 0.2, "δ⁻", fontsize=8, color="#C0392B")
        _draw_hbond(ax, (3.0, 3.7), (6.1, 3.6))
        _draw_hbond(ax, (4.8, 2.3), (5.9, 3.35))
        note = ("NH₃ has only ONE lone pair on N, so it forms fewer H-bonds than H₂O "
                "or HF → lower boiling point than expected but higher than PH₃.")

    elif schema.substance == "dna_base_pair":
        # A=T (2 H-bonds) vs G≡C (3 H-bonds) — the count is the fact.
        def base_block(cx, cy, left_lbl, right_lbl, n_bonds, color):
            ax.add_patch(mpatches.FancyBboxPatch((cx - 2.0, cy - 0.7), 1.5, 1.4,
                                                 boxstyle="round,pad=0.05",
                                                 facecolor=color, edgecolor="black",
                                                 linewidth=1.2, zorder=2))
            ax.text(cx - 1.25, cy, left_lbl, ha="center", va="center", fontsize=13,
                    fontweight="bold", zorder=3)
            ax.add_patch(mpatches.FancyBboxPatch((cx + 0.5, cy - 0.7), 1.5, 1.4,
                                                 boxstyle="round,pad=0.05",
                                                 facecolor=color, edgecolor="black",
                                                 linewidth=1.2, zorder=2))
            ax.text(cx + 1.25, cy, right_lbl, ha="center", va="center", fontsize=13,
                    fontweight="bold", zorder=3)
            offs = np.linspace(-0.35, 0.35, n_bonds)
            for o in offs:
                _draw_hbond(ax, (cx - 0.5, cy + o), (cx + 0.5, cy + o))
            ax.text(cx, cy - 1.05, f"{n_bonds} H-bonds", ha="center", fontsize=9,
                    color="#C0392B", fontweight="bold")
        base_block(3.0, 4.3, "A", "T", 2, "#D6EAF8")
        base_block(3.0, 2.3, "G", "C", 3, "#D5F5E3")
        note = ("Adenine=Thymine share 2 H-bonds; Guanine–Cytosine share 3. The G–C "
                "pair is the stronger, so %G-C sets the DNA melting temperature.")
        ax.set_xlim(0, 6)

    else:  # ethanol
        def ethanol(x, y):
            ax.text(x - 0.6, y, "C₂H₅", ha="center", va="center", fontsize=10,
                    fontweight="bold")
            ax.plot([x - 0.25, x], [y, y], color="black", lw=1.6, zorder=2)
            ax.add_patch(plt.Circle((x, y), 0.26, color="#C0392B", ec="black",
                                    lw=0.8, zorder=3))
            ax.text(x, y, "O", ha="center", va="center", fontsize=9, color="white",
                    fontweight="bold", zorder=4)
            hx = x + 0.5
            ax.plot([x, hx], [y, y], color="black", lw=1.5, zorder=2)
            ax.add_patch(plt.Circle((hx, y), 0.14, color="#D5DBDB", ec="black",
                                    lw=0.5, zorder=3))
            ax.text(hx, y, "H", ha="center", va="center", fontsize=7, zorder=4)
            if sc:
                ax.text(x - 0.05, y + 0.32, "δ⁻", fontsize=7, color="#C0392B")
                ax.text(hx, y + 0.28, "δ⁺", fontsize=7, color="#1A5276")
            return (hx + 0.14, y), (x - 0.26, y)
        a_h, _ = ethanol(2.6, 4.0)
        _, b_o = ethanol(6.0, 3.6)
        _draw_hbond(ax, a_h, b_o)
        ethanol(4.3, 2.0)
        note = "Ethanol molecules H-bond through their –O–H groups (O–H⋯O)."

    if note:
        ax.text(0.5, 0.35, note, ha="left", va="bottom", fontsize=9, color="#1A252F",
                wrap=True, transform=ax.transData)

    ax.set_title(schema.title or f"Hydrogen Bonding: {schema.substance.replace('_', ' ')}",
                 fontsize=13, fontweight="bold")
    fig.tight_layout()
    return _fig_to_svg(fig)


# ── 6. Metallurgy Flowchart ───────────────────────────────────────────────────

# Each process as (box label, reagent-on-the-incoming-arrow). The reagent/condition
# is the exam fact (roasting is IN AIR giving the oxide + SO₂; calcination is in
# LIMITED air giving oxide + CO₂/H₂O).
_METALLURGY_STEPS: Dict[str, List[Tuple[str, str]]] = {
    "froth_flotation": [
        ("Crushed sulphide ore", ""),
        ("Froth flotation", "pine oil + water + air, agitate"),
        ("Concentrated ore\n(sulphide floats)", "gangue is wetted & sinks"),
    ],
    "roasting": [
        ("Concentrated\nsulphide ore", ""),
        ("Roasting", "excess air, below m.p."),
        ("Metal oxide + SO₂", "2ZnS + 3O₂ → 2ZnO + 2SO₂"),
    ],
    "calcination": [
        ("Carbonate /\nhydrated ore", ""),
        ("Calcination", "strong heat, limited air"),
        ("Metal oxide + CO₂/H₂O", "CaCO₃ → CaO + CO₂"),
    ],
    "smelting": [
        ("Metal oxide", ""),
        ("Smelting (reduction)", "coke (C) + flux, heat"),
        ("Molten metal + slag", "ZnO + C → Zn + CO"),
    ],
    "refining": [
        ("Crude (impure) metal", ""),
        ("Refining", "electrolysis / zone refining"),
        ("Pure metal", ""),
    ],
    "full_extraction": [
        ("Ore", ""),
        ("Concentration", "froth flotation"),
        ("Roasting / Calcination", "→ oxide"),
        ("Reduction (smelting)", "coke / Al / electrolysis"),
        ("Crude metal", ""),
        ("Refining", "electrolytic"),
        ("Pure metal", ""),
    ],
}

# ΔH (kJ per mol O₂) and ΔS (kJ mol⁻¹ K⁻¹) of oxide formation, so ΔG° = ΔH − TΔS is
# COMPUTED, never sketched. The 2C+O₂→2CO line has POSITIVE ΔS ⇒ NEGATIVE slope: it
# falls with T and eventually undercuts the metal-oxide lines — the crossover is the
# temperature above which carbon becomes the better reductant.
_ELLINGHAM: List[Tuple[str, float, float, str]] = [
    ("2Mg + O₂ → 2MgO", -1204.0, -0.217, "#8E44AD"),
    ("4/3Al + O₂ → 2/3Al₂O₃", -1117.0, -0.209, "#2980B9"),
    ("2Zn + O₂ → 2ZnO", -697.0, -0.201, "#16A085"),
    ("2Fe + O₂ → 2FeO", -544.0, -0.145, "#C0392B"),
    ("C + O₂ → CO₂", -394.0, -0.001, "#7F8C8D"),
    ("2C + O₂ → 2CO", -221.0, 0.179, "#E67E22"),
]


def _ellingham_dg(dh: float, ds: float, t: float) -> float:
    return dh - t * ds


def _ellingham_crossover(dh1, ds1, dh2, ds2) -> float:
    """T (K) where two ΔG° lines meet: ΔH₁−TΔS₁ = ΔH₂−TΔS₂."""
    return (dh1 - dh2) / (ds1 - ds2)


def _render_ellingham(schema: MetallurgyFlowchartSchema,
                      canvas_w: int, canvas_h: int) -> str:
    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))
    T = np.linspace(300.0, 2000.0, 200)
    for label, dh, ds, color in _ELLINGHAM:
        ax.plot(T, _ellingham_dg(dh, ds, T), color=color, lw=2.0, label=label)

    # crossover of the C→CO line with the ZnO line: above it, C reduces ZnO.
    c_dh, c_ds = -221.0, 0.179
    zn_dh, zn_ds = -697.0, -0.201
    t_cross = _ellingham_crossover(c_dh, c_ds, zn_dh, zn_ds)
    g_cross = _ellingham_dg(c_dh, c_ds, t_cross)
    ax.plot(t_cross, g_cross, "ko", markersize=7, zorder=5)
    ax.annotate(f"C→CO crosses ZnO\nat ≈ {t_cross:.0f} K:\nabove this, C reduces ZnO",
                xy=(t_cross, g_cross), xytext=(t_cross - 60, g_cross + 220),
                fontsize=8.5, ha="right",
                arrowprops=dict(arrowstyle="->", color="black", lw=1))

    ax.set_xlabel("Temperature (K) →", fontsize=11)
    ax.set_ylabel("ΔG° of oxide formation (kJ / mol O₂)", fontsize=11)
    ax.set_title(schema.title or "Ellingham Diagram", fontsize=13, fontweight="bold")
    ax.axhline(0, color="#B3B6B7", lw=0.8)
    ax.legend(fontsize=8, loc="lower left")
    ax.grid(True, linestyle=":", linewidth=0.5, color="#D5D8DC")
    ax.text(0.99, 0.02, "more negative ΔG° = more stable oxide = better reductant",
            transform=ax.transAxes, fontsize=8.5, ha="right", va="bottom",
            color="#566573", style="italic")
    fig.tight_layout()
    return _fig_to_svg(fig)


def render_metallurgy_flowchart(data: Dict[str, Any],
                                canvas_w: int = 900, canvas_h: int = 600) -> str:
    schema = MetallurgyFlowchartSchema(**data)
    if schema.ellingham:
        return _render_ellingham(schema, canvas_w, canvas_h)

    if schema.steps:
        steps = [(s.label, s.reagent) for s in schema.steps]
    else:
        steps = _METALLURGY_STEPS[schema.process]

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 8)
    ax.axis("off")

    per_row = 3 if len(steps) > 4 else min(len(steps), 4)
    bw, bh = 3.0, 1.2
    x_gap = (12.0 - per_row * bw) / (per_row + 1)
    row_ys = [6.0, 3.4, 0.8]

    centres = []
    for i in range(len(steps)):
        row = i // per_row
        col = i % per_row
        # snake: even rows left→right, odd rows right→left
        if row % 2 == 1:
            col = per_row - 1 - col
        cx = x_gap + col * (bw + x_gap) + bw / 2
        cy = row_ys[min(row, len(row_ys) - 1)]
        centres.append((cx, cy))

    for i, ((label, reagent), (cx, cy)) in enumerate(zip(steps, centres)):
        is_terminal = (i == 0 or i == len(steps) - 1)
        ax.add_patch(mpatches.FancyBboxPatch((cx - bw / 2, cy - bh / 2), bw, bh,
                     boxstyle="round,pad=0.05",
                     facecolor="#EBF5FB" if not is_terminal else "#FCF3CF",
                     edgecolor="#1A5276" if not is_terminal else "#B7950B",
                     linewidth=1.8, zorder=3))
        ax.text(cx, cy, label, ha="center", va="center", fontsize=9.5,
                fontweight="bold", zorder=4)

    for i in range(len(steps) - 1):
        (x0, y0), (x1, y1) = centres[i], centres[i + 1]
        reagent = steps[i + 1][1]
        same_row = abs(y0 - y1) < 0.1
        if same_row:
            xa = x0 + bw / 2 if x1 > x0 else x0 - bw / 2
            xb = x1 - bw / 2 if x1 > x0 else x1 + bw / 2
            ax.annotate("", xy=(xb, y1), xytext=(xa, y0),
                        arrowprops=dict(arrowstyle="-|>", color="#34495E", lw=1.8))
            if reagent:
                ax.text((xa + xb) / 2, y0 + 0.18, reagent, ha="center", va="bottom",
                        fontsize=7.5, color="#7B241C")
        else:   # drop down to next row
            ax.annotate("", xy=(x1, y1 + bh / 2), xytext=(x0, y0 - bh / 2),
                        arrowprops=dict(arrowstyle="-|>", color="#34495E", lw=1.8,
                                        connectionstyle="arc3,rad=0.0"))
            if reagent:
                ax.text((x0 + x1) / 2 + 0.2, (y0 + y1) / 2, reagent, ha="left",
                        va="center", fontsize=7.5, color="#7B241C")

    subtitle = f"{schema.metal} from {schema.ore}"
    ax.set_title(schema.title or f"Metallurgy — {schema.process.replace('_', ' ').title()}"
                 f"   ({subtitle})", fontsize=12, fontweight="bold")
    fig.tight_layout()
    return _fig_to_svg(fig)


# ── 7. Industrial Process ─────────────────────────────────────────────────────

# Conditions are the exam facts: Haber Fe/450 °C/200 atm; Contact V₂O₅; Ostwald Pt/Rh.
_INDUSTRIAL_DB: Dict[str, Dict[str, Any]] = {
    "haber": {
        "name": "Haber Process — Ammonia",
        "feedstocks": ["N₂ (from air)", "H₂ (from CH₄ + steam)"],
        "reaction": "N₂ + 3H₂ ⇌ 2NH₃",
        "catalyst": "Fe (+ K₂O / Al₂O₃ promoter)",
        "temperature": "450 °C", "pressure": "200 atm",
        "product": "Ammonia, NH₃",
        "recycle": "unreacted N₂ + H₂ recycled",
    },
    "contact": {
        "name": "Contact Process — Sulphuric Acid",
        "feedstocks": ["SO₂ (from S / FeS₂)", "O₂ (air)"],
        "reaction": "2SO₂ + O₂ ⇌ 2SO₃",
        "catalyst": "V₂O₅ (vanadium(V) oxide)",
        "temperature": "450 °C", "pressure": "1–2 atm",
        "product": "H₂SO₄ (via oleum)",
        "recycle": "SO₃ → oleum (H₂S₂O₇) → H₂SO₄",
    },
    "ostwald": {
        "name": "Ostwald Process — Nitric Acid",
        "feedstocks": ["NH₃", "O₂ (air)"],
        "reaction": "4NH₃ + 5O₂ → 4NO + 6H₂O",
        "catalyst": "Pt / Rh gauze",
        "temperature": "850 °C", "pressure": "1–9 atm",
        "product": "HNO₃",
        "recycle": "2NO + O₂ → 2NO₂; 3NO₂ + H₂O → 2HNO₃ + NO (NO recycled)",
    },
    "solvay": {
        "name": "Solvay Process — Sodium Carbonate",
        "feedstocks": ["NaCl brine + NH₃", "CO₂ (from CaCO₃)"],
        "reaction": "NaCl + NH₃ + CO₂ + H₂O → NaHCO₃ + NH₄Cl",
        "catalyst": "none",
        "temperature": "ambient, then heat", "pressure": "1 atm",
        "product": "Na₂CO₃  (2NaHCO₃ →Δ Na₂CO₃ + H₂O + CO₂)",
        "recycle": "NH₃ recovered (2NH₄Cl + Ca(OH)₂); CO₂ recycled",
    },
    "chlor_alkali": {
        "name": "Chlor-Alkali Process",
        "feedstocks": ["NaCl brine", "electricity"],
        "reaction": "2NaCl + 2H₂O → 2NaOH + Cl₂ + H₂",
        "catalyst": "none (electrolysis)",
        "temperature": "ambient", "pressure": "1 atm",
        "product": "NaOH + Cl₂ + H₂",
        "recycle": "depleted brine re-saturated",
    },
}


def render_industrial_process(data: Dict[str, Any],
                              canvas_w: int = 900, canvas_h: int = 560) -> str:
    schema = IndustrialProcessSchema(**data)
    info = _INDUSTRIAL_DB[schema.process]

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 8)
    ax.axis("off")

    # feedstocks (left, stacked)
    fy = [5.4, 3.2]
    for lbl, y in zip(info["feedstocks"], fy):
        ax.add_patch(mpatches.FancyBboxPatch((0.4, y - 0.55), 2.7, 1.1,
                     boxstyle="round,pad=0.05", facecolor="#FCF3CF",
                     edgecolor="#B7950B", linewidth=1.6, zorder=3))
        ax.text(1.75, y, lbl, ha="center", va="center", fontsize=9.5,
                fontweight="bold", zorder=4)
        ax.annotate("", xy=(4.4, 4.3), xytext=(3.15, y),
                    arrowprops=dict(arrowstyle="-|>", color="#34495E", lw=1.6))

    # reactor / converter (centre)
    ax.add_patch(mpatches.FancyBboxPatch((4.4, 3.0), 3.4, 2.6,
                 boxstyle="round,pad=0.05", facecolor="#D6EAF8",
                 edgecolor="#1A5276", linewidth=2.2, zorder=3))
    ax.text(6.1, 5.15, "Catalytic Reactor", ha="center", fontsize=10.5,
            fontweight="bold", color="#154360", zorder=4)
    ax.text(6.1, 4.55, info["reaction"], ha="center", fontsize=11, fontweight="bold",
            zorder=4)
    if schema.show_conditions:
        ax.text(6.1, 3.95, f"catalyst: {info['catalyst']}", ha="center", fontsize=9,
                color="#7B241C", zorder=4)
        ax.text(6.1, 3.55, f"{info['temperature']}   •   {info['pressure']}",
                ha="center", fontsize=9, color="#7B241C", zorder=4)

    # product (right)
    ax.add_patch(mpatches.FancyBboxPatch((8.9, 3.75), 2.8, 1.1,
                 boxstyle="round,pad=0.05", facecolor="#D5F5E3",
                 edgecolor="#1E8449", linewidth=2.0, zorder=3))
    ax.text(10.3, 4.3, info["product"], ha="center", va="center", fontsize=10,
            fontweight="bold", zorder=4)
    ax.annotate("", xy=(8.85, 4.3), xytext=(7.8, 4.3),
                arrowprops=dict(arrowstyle="-|>", color="#34495E", lw=1.8))

    # recycle loop (product side back to reactor input)
    if schema.show_recycle:
        ax.annotate("", xy=(4.5, 2.9), xytext=(10.3, 2.4),
                    arrowprops=dict(arrowstyle="-|>", color="#CA6F1E", lw=1.6,
                                    connectionstyle="arc3,rad=0.25"))
        ax.text(7.4, 1.6, f"recycle: {info['recycle']}", ha="center", va="center",
                fontsize=8.5, color="#CA6F1E", style="italic")

    ax.text(6.1, 7.4, "feedstocks → catalytic reactor → product",
            ha="center", fontsize=9, color="#566573")
    ax.set_title(schema.title or info["name"], fontsize=13, fontweight="bold")
    fig.tight_layout()
    return _fig_to_svg(fig)


# ── Dispatcher ────────────────────────────────────────────────────────────────

CHEMISTRY_RENDERERS = {
    "organic_structure": render_organic_structure,
    "inorganic_structure": render_inorganic_structure,
    "orbital_diagram": render_orbital_diagram,
    "reaction_coordinate_graph": render_reaction_coordinate_graph,
    "electrochemical_cell": render_electrochemical_cell,
    "equilibrium_graph": render_equilibrium_graph,
    "titration_curve": render_titration_curve,
    "sn1_sn2_mechanism": render_sn1_sn2_mechanism,
    "newman_projection": render_newman_projection,
    "conformational_isomers": render_conformational_isomers,
    "crystal_lattice": render_crystal_lattice,
    "vsepr_shape": render_vsepr_shape,
    "mo_diagram": render_mo_diagram,
    "phase_diagram": render_phase_diagram,
    "haworth_fischer": render_haworth_fischer,
    "lab_apparatus": render_lab_apparatus,
    "reaction_scheme": render_reaction_scheme,
    "crystal_field_splitting": render_crystal_field_splitting,
    "kinetics_graph": render_kinetics_graph,
    "colligative_graph": render_colligative_graph,
    "organic_mechanism": render_organic_mechanism,
    "hybridisation_overlap": render_hybridisation_overlap,
    "adsorption_isotherm": render_adsorption_isotherm,
    "electrolytic_cell": render_electrolytic_cell,
    "ionic_lattice": render_ionic_lattice,
    "solid_defects": render_solid_defects,
    "complex_isomerism": render_complex_isomerism,
    "resonance_structures": render_resonance_structures,
    "free_radical_mechanism": render_free_radical_mechanism,
    "polymer_structure": render_polymer_structure,
    "protein_structure": render_protein_structure,
    "hydrogen_bonding": render_hydrogen_bonding,
    "metallurgy_flowchart": render_metallurgy_flowchart,
    "industrial_process": render_industrial_process,
    # Shared across physics/chemistry/mathematics — see diagrams/service/shared/xygraph.py.
    "annotated_xy_graph": render_annotated_xy_graph,
}


def render_chemistry(subtype: str, params: Dict[str, Any],
                     canvas_w: int = 800, canvas_h: int = 600) -> str:
    renderer = CHEMISTRY_RENDERERS.get(subtype)
    if not renderer:
        raise ValueError(f"Unknown chemistry subtype: '{subtype}'. "
                         f"Supported: {list(CHEMISTRY_RENDERERS.keys())}")
    return renderer(params, canvas_w=canvas_w, canvas_h=canvas_h)
