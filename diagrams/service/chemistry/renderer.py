"""
Chemistry Diagram Renderer.
Uses RDKit for organic structures (SMILES), matplotlib for orbital/reaction
coordinate diagrams, and svgwrite fallback for inorganic structures.
"""
from __future__ import annotations

import io
import math
from typing import Any, Dict, List

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
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

from diagrams.schemas.chemistry import (
    OrganicStructureSchema, InorganicStructureSchema,
    OrbitalDiagramSchema, ReactionCoordinateSchema,
    ElectrochemicalCellSchema, EquilibriumGraphSchema, TitrationCurveSchema,
    SN1SN2MechanismSchema, NewmanProjectionSchema, ConformationalIsomersSchema,
)

STROKE = "black"
FONT_SZ = 14
FONT = "Arial, sans-serif"


def _text(dwg, txt, x, y, anchor="middle", size=FONT_SZ, bold=False):
    weight = "bold" if bold else "normal"
    dwg.add(dwg.text(txt, insert=(x, y), font_size=size, font_family=FONT,
                     text_anchor=anchor, font_weight=weight))


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
        # Inject name label at bottom
        label = f'<text x="{canvas_w // 2}" y="{canvas_h - 12}" ' \
                f'font-size="14" font-family="Arial" text-anchor="middle">{name}</text>'
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
    fig.savefig(buf, format="svg", bbox_inches="tight", facecolor="white", pad_inches=0.25)
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

    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="svg", bbox_inches="tight", facecolor="white")
    buf.seek(0)
    svg_content = buf.getvalue().decode("utf-8")
    plt.close(fig)
    return svg_content


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

    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="svg", bbox_inches="tight", facecolor="white")
    buf.seek(0)
    svg_content = buf.getvalue().decode("utf-8")
    plt.close(fig)
    return svg_content


# ── 5. Electrochemical Cell ───────────────────────────────────────────────────

def render_electrochemical_cell(data: Dict[str, Any],
                                 canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = ElectrochemicalCellSchema(**data)

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.set_aspect("equal")
    ax.axis("off")

    # ── beakers ───────────────────────────────────────────────────────────────
    def _beaker(ax, x0, y0, w=2.5, h=2.8, solution_label="", ion_label="",
                electrode_label="", is_anode=True):
        # beaker walls
        beaker = mpatches.FancyBboxPatch((x0, y0), w, h, boxstyle="square,pad=0",
                                          edgecolor="black", facecolor="#d0e8ff",
                                          linewidth=1.8, zorder=2)
        ax.add_patch(beaker)
        # electrode rod
        ex = x0 + w / 2
        ax.plot([ex, ex], [y0 + h * 0.1, y0 + h + 0.6], color="#555555",
                linewidth=5, solid_capstyle="round", zorder=3)
        # electrode label
        lbl_color = "red" if is_anode else "blue"
        ax.text(ex, y0 + h + 0.85, electrode_label, ha="center", va="bottom",
                fontsize=13, fontweight="bold", color=lbl_color)
        # solution label
        ax.text(x0 + w / 2, y0 + h * 0.45, solution_label, ha="center",
                va="center", fontsize=11, color="#003399")
        # ion label
        ax.text(x0 + w / 2, y0 + h * 0.12, ion_label, ha="center",
                va="bottom", fontsize=11, style="italic", color="#003399")
        return (ex, y0 + h + 0.6)   # top of rod

    # left beaker = anode
    ax_top_l = _beaker(ax, 0.5, 0.8, solution_label=schema.anode_solution,
                       ion_label=schema.anode_ion,
                       electrode_label=f"{schema.anode_material} (Anode −)",
                       is_anode=True)[0]
    # right beaker = cathode
    ax_top_r = _beaker(ax, 7.0, 0.8, solution_label=schema.cathode_solution,
                       ion_label=schema.cathode_ion,
                       electrode_label=f"{schema.cathode_material} (Cathode +)",
                       is_anode=False)[0]

    # ── external wire ─────────────────────────────────────────────────────────
    wire_y = 5.4
    ax.plot([ax_top_l, ax_top_l], [4.0, wire_y], color="black", lw=2)
    ax.plot([ax_top_r + 1.25, ax_top_r + 1.25], [4.0, wire_y], color="black", lw=2)
    ax.plot([ax_top_l, ax_top_r + 1.25], [wire_y, wire_y], color="black", lw=2)

    # ── current arrows ────────────────────────────────────────────────────────
    if schema.show_current:
        mid_x = (ax_top_l + ax_top_r + 1.25) / 2
        ax.annotate("", xy=(ax_top_r + 1.25, wire_y), xytext=(mid_x, wire_y),
                    arrowprops=dict(arrowstyle="->", color="orange", lw=2.0))
        ax.text(mid_x, wire_y + 0.25, "e⁻ flow", ha="center", va="bottom",
                fontsize=11, color="orange")

    # ── salt bridge ───────────────────────────────────────────────────────────
    if schema.show_salt_bridge:
        sb_x0, sb_x1 = 3.0, 7.0
        sb_y = 2.8
        from matplotlib.patches import FancyArrowPatch
        bridge = mpatches.FancyBboxPatch((sb_x0, sb_y - 0.2), sb_x1 - sb_x0, 0.4,
                                          boxstyle="round,pad=0.05",
                                          edgecolor="black", facecolor="#ffffcc",
                                          linewidth=1.5, zorder=4)
        ax.add_patch(bridge)
        ax.text((sb_x0 + sb_x1) / 2, sb_y, "Salt Bridge", ha="center",
                va="center", fontsize=10)

    # ── EMF label ─────────────────────────────────────────────────────────────
    if schema.emf is not None:
        ax.text(5.0, wire_y + 0.55, f"E°cell = {schema.emf:.2f} V",
                ha="center", va="bottom", fontsize=12, color="darkgreen",
                fontweight="bold")

    # ── half reactions ────────────────────────────────────────────────────────
    if schema.show_half_reactions:
        ax.text(1.75, 0.55,
                f"Anode: {schema.anode_material} → {schema.anode_ion} + e⁻",
                ha="center", va="top", fontsize=9, color="darkred")
        ax.text(8.25, 0.55,
                f"Cathode: {schema.cathode_ion} + e⁻ → {schema.cathode_material}",
                ha="center", va="top", fontsize=9, color="darkblue")

    # ── title ─────────────────────────────────────────────────────────────────
    ax.set_title(schema.cell_name, fontsize=14, fontweight="bold", pad=6)

    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="svg", bbox_inches="tight", facecolor="white")
    buf.seek(0)
    svg_out = buf.getvalue().decode("utf-8")
    plt.close(fig)
    return svg_out


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
    buf = io.BytesIO()
    fig.savefig(buf, format="svg", bbox_inches="tight", facecolor="white")
    buf.seek(0)
    svg_out = buf.getvalue().decode("utf-8")
    plt.close(fig)
    return svg_out


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
    buf = io.BytesIO()
    fig.savefig(buf, format="svg", bbox_inches="tight", facecolor="white")
    buf.seek(0)
    svg_out = buf.getvalue().decode("utf-8")
    plt.close(fig)
    return svg_out


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

        # Curved arrows
        if schema.show_curved_arrows:
            # Nu attacks C
            ax.annotate("", xy=(3.6, 3.0), xytext=(2.0, 3.0),
                        arrowprops=dict(
                            arrowstyle="-|>",
                            connectionstyle="arc3,rad=-0.35",
                            color="#2980B9", lw=1.5))
            # LG leaves
            ax.annotate("", xy=(7.2, 3.0), xytext=(6.3, 3.0),
                        arrowprops=dict(
                            arrowstyle="-|>",
                            connectionstyle="arc3,rad=-0.35",
                            color="#E74C3C", lw=1.5))

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
    buf = io.BytesIO()
    fig.savefig(buf, format="svg", bbox_inches="tight", facecolor="white")
    buf.seek(0)
    svg_out = buf.getvalue().decode("utf-8")
    plt.close(fig)
    return svg_out


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
    buf = io.BytesIO()
    fig.savefig(buf, format="svg", bbox_inches="tight", facecolor="white")
    buf.seek(0)
    svg_out = buf.getvalue().decode("utf-8")
    plt.close(fig)
    return svg_out


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
    buf = io.BytesIO()
    fig.savefig(buf, format="svg", bbox_inches="tight", facecolor="white")
    buf.seek(0)
    svg_out = buf.getvalue().decode("utf-8")
    plt.close(fig)
    return svg_out


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
}


def render_chemistry(subtype: str, params: Dict[str, Any],
                     canvas_w: int = 800, canvas_h: int = 600) -> str:
    renderer = CHEMISTRY_RENDERERS.get(subtype)
    if not renderer:
        raise ValueError(f"Unknown chemistry subtype: '{subtype}'. "
                         f"Supported: {list(CHEMISTRY_RENDERERS.keys())}")
    return renderer(params, canvas_w=canvas_w, canvas_h=canvas_h)
