"""
Circuit Diagram Renderer.
Uses schemdraw for circuit layout; falls back to svgwrite if schemdraw unavailable.
Supports: resistor networks, capacitor networks, basic DC circuits.
"""
from __future__ import annotations

import io
import math
from typing import Any, Dict, List, Optional

import svgwrite
import matplotlib
matplotlib.use("Agg")

# ── schemdraw (optional) ───────────────────────────────────────────────────────
try:
    import schemdraw
    import schemdraw.elements as elm
    SCHEMDRAW_AVAILABLE = True
except ImportError:
    SCHEMDRAW_AVAILABLE = False

from diagrams.schemas.circuits import (
    ResistorNetworkSchema, CapacitorNetworkSchema, BasicDCCircuitSchema,
    ComponentType,
)

STROKE = "black"
FONT_SZ = 13
FONT = "Arial, sans-serif"


def _text(dwg, txt, x, y, anchor="middle", size=FONT_SZ):
    dwg.add(dwg.text(txt, insert=(x, y), font_size=size, font_family=FONT,
                     text_anchor=anchor))


def _base_drawing(canvas_w=800, canvas_h=600):
    dwg = svgwrite.Drawing(size=(f"{canvas_w}px", f"{canvas_h}px"),
                           viewBox=f"0 0 {canvas_w} {canvas_h}")
    dwg.add(dwg.rect(insert=(0, 0), size=(f"{canvas_w}px", f"{canvas_h}px"), fill="white"))
    return dwg


def _fig_to_svg(fig) -> str:
    import io
    buf = io.BytesIO()
    fig.savefig(buf, format="svg", bbox_inches="tight", facecolor="white", dpi=100)
    buf.seek(0)
    svg = buf.getvalue().decode("utf-8")
    import matplotlib.pyplot as plt
    plt.close(fig)
    return svg


# ── schemdraw helpers ─────────────────────────────────────────────────────────

def _schemdraw_to_svg(drawing) -> str:
    """Export a schemdraw Drawing to SVG string (compatible with schemdraw ≥ 0.19)."""
    # _repr_svg_() is the reliable cross-version method
    svg = drawing._repr_svg_()
    if isinstance(svg, bytes):
        return svg.decode("utf-8")
    return svg


def _parse_value(val_str: str) -> str:
    """Strip unit prefix for display, return as-is."""
    return val_str or ""


# ── 1. Resistor Network ───────────────────────────────────────────────────────

def render_resistor_network(data: Dict[str, Any], canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = ResistorNetworkSchema(**data)

    if SCHEMDRAW_AVAILABLE:
        return _schemdraw_resistor_network(schema, canvas_w, canvas_h)
    else:
        return _fallback_resistor_network(schema, canvas_w, canvas_h)


def _schemdraw_resistor_network(schema, canvas_w, canvas_h) -> str:
    resistors = schema.resistors
    topology = schema.topology
    vs = schema.voltage_source or ""

    try:
        with schemdraw.Drawing(show=False) as d:
            d.config(fontsize=11)

            if topology == "series":
                d += elm.Battery().up().label(vs, loc="left").reverse()
                d += elm.Line().right(1)
                for i, r in enumerate(resistors):
                    d += elm.Resistor().right().label(r or f"R{i+1}")
                d += elm.Line().down()
                d += elm.Line().left(len(resistors) * 3 + 3)

            elif topology == "parallel":
                n = len(resistors)
                d += elm.Battery().up().label(vs, loc="left").reverse()
                d += elm.Line().right(1)
                branch_w = 3
                # Top junction
                j_top = d.add(elm.Dot())
                for i, r in enumerate(resistors):
                    lbl = r or f"R{i+1}"
                    top_start = d.add(elm.Line().right(branch_w).at(j_top.end)) if i > 0 else j_top
                    d.add(elm.Resistor().down().label(lbl, loc="right").at(
                        top_start.end if i > 0 else j_top.end))
                # Bottom bus
                d += elm.Line().left(n * branch_w)
                d += elm.Line().up()

            elif topology == "series_parallel":
                # First half parallel, second half parallel, groups in series
                mid = max(1, len(resistors) // 2)
                g1, g2 = resistors[:mid] or ["R1"], resistors[mid:] or ["R2"]
                d += elm.Battery().up().label(vs, loc="left").reverse()
                d += elm.Line().right(1)
                for grp in [g1, g2]:
                    j = d.add(elm.Dot())
                    for k, r in enumerate(grp):
                        lbl = r or f"R{k+1}"
                        if k > 0:
                            d.add(elm.Line().right(2.5).at(j.end))
                        d.add(elm.Resistor().down().label(lbl, loc="right").at(j.end))
                    d.add(elm.Dot())
                    d += elm.Line().right(1)
                d += elm.Line().down()
                d += elm.Line().left(8)

            else:
                # fallback to series
                for i, r in enumerate(resistors):
                    d += elm.Resistor().right().label(r or f"R{i+1}")

            return _schemdraw_to_svg(d)
    except Exception:
        return _fallback_resistor_network(schema, canvas_w, canvas_h)


def _fallback_resistor_network(schema, canvas_w, canvas_h) -> str:
    """SVG fallback when schemdraw is not available."""
    dwg = _base_drawing(canvas_w, canvas_h)
    resistors = schema.resistors
    n = len(resistors)
    topology = schema.topology
    vs = schema.voltage_source

    if topology == "series":
        # Draw resistors in a horizontal line
        total_w = canvas_w - 160
        r_w = min(80, total_w / n - 20)
        r_h = 30
        spacing = total_w / n
        cy = canvas_h / 2
        start_x = 80

        # Battery on left
        if vs:
            _draw_battery_svg(dwg, 20, cy - 50, 20, cy + 50, vs)
            dwg.add(dwg.line(start=(20, cy - 50), end=(start_x, cy - 50),
                             stroke=STROKE, stroke_width=2))
            dwg.add(dwg.line(start=(20, cy + 50), end=(canvas_w - 20, cy + 50),
                             stroke=STROKE, stroke_width=2))
            dwg.add(dwg.line(start=(canvas_w - 20, cy - 50), end=(canvas_w - 20, cy + 50),
                             stroke=STROKE, stroke_width=2))
        else:
            # Simple top wire
            dwg.add(dwg.line(start=(start_x, cy - 50), end=(canvas_w - 80, cy - 50),
                             stroke=STROKE, stroke_width=2))

        y = cy - 50
        x = start_x
        for i, r in enumerate(resistors):
            lbl = r or f"R{i + 1}"
            # Wire before resistor
            dwg.add(dwg.line(start=(x, y), end=(x + spacing * 0.15, y),
                             stroke=STROKE, stroke_width=2))
            # Resistor box
            rx = x + spacing * 0.15
            _draw_resistor_svg(dwg, rx, y, r_w, r_h, lbl)
            # Wire after resistor
            dwg.add(dwg.line(start=(rx + r_w, y),
                             end=(x + spacing, y),
                             stroke=STROKE, stroke_width=2))
            x += spacing

    elif topology == "parallel":
        # Draw resistors in parallel vertical arrangement
        cy = canvas_h / 2
        bus_x1, bus_x2 = 120, canvas_w - 120
        r_h, r_w = 32, 90

        if vs:
            _draw_battery_svg(dwg, 40, cy - 60, 40, cy + 60, vs)
            dwg.add(dwg.line(start=(40, cy - 60), end=(bus_x1, cy - 60),
                             stroke=STROKE, stroke_width=2))
            dwg.add(dwg.line(start=(40, cy + 60), end=(bus_x1, cy + 60),
                             stroke=STROKE, stroke_width=2))

        # Vertical bus lines
        top_y = cy - (n - 1) * 55 / 2 - 30
        bot_y = cy + (n - 1) * 55 / 2 + 30
        dwg.add(dwg.line(start=(bus_x1, top_y), end=(bus_x1, bot_y),
                         stroke=STROKE, stroke_width=2))
        dwg.add(dwg.line(start=(bus_x2, top_y), end=(bus_x2, bot_y),
                         stroke=STROKE, stroke_width=2))
        # Top & bottom bus
        dwg.add(dwg.line(start=(bus_x1, top_y), end=(bus_x2, top_y),
                         stroke=STROKE, stroke_width=2))
        dwg.add(dwg.line(start=(bus_x1, bot_y), end=(bus_x2, bot_y),
                         stroke=STROKE, stroke_width=2))

        # Resistors
        for i, r in enumerate(resistors):
            lbl = r or f"R{i + 1}"
            ry = top_y + (i + 1) * (bot_y - top_y) / (n + 1)
            _draw_resistor_svg(dwg, (bus_x1 + bus_x2) / 2 - r_w / 2, ry - r_h / 2,
                               r_w, r_h, lbl)
            dwg.add(dwg.line(start=(bus_x1, ry), end=((bus_x1 + bus_x2) / 2 - r_w / 2, ry),
                             stroke=STROKE, stroke_width=2))
            dwg.add(dwg.line(start=((bus_x1 + bus_x2) / 2 + r_w / 2, ry), end=(bus_x2, ry),
                             stroke=STROKE, stroke_width=2))

    # Equivalent resistance annotation
    if schema.equivalent_label and n > 0:
        try:
            vals = []
            for r in resistors:
                num_part = "".join(c for c in r if c.isdigit() or c == ".")
                if num_part:
                    vals.append(float(num_part))
            if vals:
                if topology == "series":
                    req = sum(vals)
                    label = f"R_eq = {req:.1f} Ω"
                elif topology == "parallel":
                    req = 1 / sum(1 / v for v in vals)
                    label = f"R_eq = {req:.2f} Ω"
                else:
                    label = ""
                if label:
                    _text(dwg, label, canvas_w / 2, canvas_h - 30, size=14)
        except Exception:
            pass

    return dwg.tostring()


def _draw_resistor_svg(dwg, x, y, w, h, label):
    """Draw a resistor rectangle with label."""
    dwg.add(dwg.rect(insert=(x, y - h / 2), size=(w, h),
                     stroke=STROKE, stroke_width=2, fill="white"))
    _text(dwg, label, x + w / 2, y + 5)


def _draw_battery_svg(dwg, x1, y1, x2, y2, label):
    """Draw a vertical battery symbol."""
    mx = (x1 + x2) / 2
    my = (y1 + y2) / 2
    # Long plate (positive)
    dwg.add(dwg.line(start=(mx - 14, my - 10), end=(mx + 14, my - 10),
                     stroke=STROKE, stroke_width=3))
    # Short plate (negative)
    dwg.add(dwg.line(start=(mx - 8, my + 10), end=(mx + 8, my + 10),
                     stroke=STROKE, stroke_width=2))
    dwg.add(dwg.line(start=(x1, y1), end=(mx, my - 10),
                     stroke=STROKE, stroke_width=2))
    dwg.add(dwg.line(start=(x2, y2), end=(mx, my + 10),
                     stroke=STROKE, stroke_width=2))
    _text(dwg, label, mx + 22, my + 5, anchor="start")
    _text(dwg, "+", mx, my - 22, size=11)
    _text(dwg, "−", mx, my + 24, size=11)


# ── 2. Capacitor Network ──────────────────────────────────────────────────────

def render_capacitor_network(data: Dict[str, Any], canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = CapacitorNetworkSchema(**data)

    if SCHEMDRAW_AVAILABLE:
        return _schemdraw_capacitor_network(schema, canvas_w, canvas_h)
    return _fallback_capacitor_network(schema, canvas_w, canvas_h)


def _schemdraw_capacitor_network(schema, canvas_w, canvas_h) -> str:
    try:
        caps = schema.capacitors
        topology = schema.topology
        vs = schema.voltage_source or ""
        n = len(caps)

        with schemdraw.Drawing(show=False) as d:
            d.config(fontsize=11)

            if topology == "series":
                d += elm.Battery().up().label(vs, loc="left").reverse()
                d += elm.Line().right(1)
                for i, c in enumerate(caps):
                    d += elm.Capacitor().right().label(c or f"C{i+1}")
                d += elm.Line().down()
                d += elm.Line().left(n * 3 + 3)

            else:  # parallel
                d += elm.Battery().up().label(vs, loc="left").reverse()
                d += elm.Line().right(1)
                branch_w = 3
                j_top = d.add(elm.Dot())
                for i, c in enumerate(caps):
                    lbl = c or f"C{i+1}"
                    top_pt = d.add(elm.Line().right(branch_w).at(j_top.end)) if i > 0 else j_top
                    d.add(elm.Capacitor().down().label(lbl, loc="right").at(
                        top_pt.end if i > 0 else j_top.end))
                d += elm.Line().left(n * branch_w)
                d += elm.Line().up()

            return _schemdraw_to_svg(d)
    except Exception:
        return _fallback_capacitor_network(schema, canvas_w, canvas_h)


def _fallback_capacitor_network(schema, canvas_w, canvas_h) -> str:
    dwg = _base_drawing(canvas_w, canvas_h)
    caps = schema.capacitors
    n = len(caps)
    topology = schema.topology
    vs = schema.voltage_source
    cy = canvas_h / 2

    if topology == "series":
        spacing = (canvas_w - 160) / n
        y = cy
        x = 80
        if vs:
            _draw_battery_svg(dwg, 20, cy - 50, 20, cy + 50, vs)
            dwg.add(dwg.line(start=(20, cy - 50), end=(x, cy - 50),
                             stroke=STROKE, stroke_width=2))
            y = cy - 50
        for i, c in enumerate(caps):
            lbl = c or f"C{i + 1}"
            dwg.add(dwg.line(start=(x, y), end=(x + spacing * 0.2, y),
                             stroke=STROKE, stroke_width=2))
            _draw_capacitor_svg(dwg, x + spacing * 0.2, y, spacing * 0.6, 40, lbl)
            dwg.add(dwg.line(start=(x + spacing * 0.8, y), end=(x + spacing, y),
                             stroke=STROKE, stroke_width=2))
            x += spacing
        if vs:
            dwg.add(dwg.line(start=(20, cy + 50), end=(canvas_w - 20, cy + 50),
                             stroke=STROKE, stroke_width=2))
            dwg.add(dwg.line(start=(canvas_w - 20, cy - 50), end=(canvas_w - 20, cy + 50),
                             stroke=STROKE, stroke_width=2))

    elif topology == "parallel":
        bus_x1, bus_x2 = 120, canvas_w - 120
        cap_w, cap_h = 20, 50
        if vs:
            _draw_battery_svg(dwg, 40, cy - 60, 40, cy + 60, vs)
            dwg.add(dwg.line(start=(40, cy - 60), end=(bus_x1, cy - 60),
                             stroke=STROKE, stroke_width=2))
            dwg.add(dwg.line(start=(40, cy + 60), end=(bus_x1, cy + 60),
                             stroke=STROKE, stroke_width=2))
        top_y, bot_y = cy - 80, cy + 80
        dwg.add(dwg.line(start=(bus_x1, top_y), end=(bus_x1, bot_y),
                         stroke=STROKE, stroke_width=2))
        dwg.add(dwg.line(start=(bus_x2, top_y), end=(bus_x2, bot_y),
                         stroke=STROKE, stroke_width=2))
        for i, c in enumerate(caps):
            lbl = c or f"C{i + 1}"
            cx_cap = bus_x1 + (bus_x2 - bus_x1) * (i + 1) / (n + 1)
            ry = (top_y + bot_y) / 2
            dwg.add(dwg.line(start=(cx_cap, top_y), end=(cx_cap, ry - cap_h / 2 - 5),
                             stroke=STROKE, stroke_width=2))
            _draw_capacitor_svg(dwg, cx_cap, ry, cap_w, cap_h, lbl, vertical=True)
            dwg.add(dwg.line(start=(cx_cap, ry + cap_h / 2 + 5), end=(cx_cap, bot_y),
                             stroke=STROKE, stroke_width=2))
        dwg.add(dwg.line(start=(bus_x1, top_y), end=(bus_x2, top_y),
                         stroke=STROKE, stroke_width=2))
        dwg.add(dwg.line(start=(bus_x1, bot_y), end=(bus_x2, bot_y),
                         stroke=STROKE, stroke_width=2))

    # Equivalent capacitance
    if schema.show_charge:
        try:
            vals = []
            for c in caps:
                num = "".join(ch for ch in c if ch.isdigit() or ch == ".")
                if num:
                    vals.append(float(num))
            if vals:
                if topology == "series":
                    ceq = 1 / sum(1 / v for v in vals)
                else:
                    ceq = sum(vals)
                _text(dwg, f"C_eq = {ceq:.2f} F", canvas_w / 2, canvas_h - 30, size=14)
        except Exception:
            pass

    return dwg.tostring()


def _draw_capacitor_svg(dwg, cx, cy, w, h, label, vertical=False):
    """Draw a capacitor symbol (two parallel lines)."""
    gap = 8
    if vertical:
        # Two horizontal lines
        dwg.add(dwg.line(start=(cx - w / 2, cy - gap / 2), end=(cx + w / 2, cy - gap / 2),
                         stroke=STROKE, stroke_width=3))
        dwg.add(dwg.line(start=(cx - w / 2, cy + gap / 2), end=(cx + w / 2, cy + gap / 2),
                         stroke=STROKE, stroke_width=3))
        _text(dwg, label, cx + w / 2 + 20, cy + 5, anchor="start", size=12)
    else:
        # Two vertical lines
        plate_h = h
        dwg.add(dwg.line(start=(cx - gap / 2, cy - plate_h / 2),
                         end=(cx - gap / 2, cy + plate_h / 2),
                         stroke=STROKE, stroke_width=3))
        dwg.add(dwg.line(start=(cx + gap / 2, cy - plate_h / 2),
                         end=(cx + gap / 2, cy + plate_h / 2),
                         stroke=STROKE, stroke_width=3))
        _text(dwg, label, cx, cy - plate_h / 2 - 10, size=12)


# ── 3. Basic DC Circuit ───────────────────────────────────────────────────────

def render_basic_dc_circuit(data: Dict[str, Any], canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = BasicDCCircuitSchema(**data)

    if SCHEMDRAW_AVAILABLE:
        return _schemdraw_dc_circuit(schema, canvas_w, canvas_h)
    return _fallback_dc_circuit(schema, canvas_w, canvas_h)


def _schemdraw_dc_circuit(schema, canvas_w, canvas_h) -> str:
    """Build a schematic DC circuit with schemdraw (compatible with 0.19+)."""
    try:
        with schemdraw.Drawing(show=False) as d:
            d.config(fontsize=11)
            components = schema.components

            _DIR = {"right": "right", "left": "left", "up": "up", "down": "down"}

            def _make(element_cls, comp, **kw):
                direction = _DIR.get(comp.direction, "right")
                label = comp.label or ""
                value = comp.value or ""
                full = f"{label} {value}".strip()
                e = getattr(element_cls(), direction)(**kw)
                if full:
                    e = e.label(full)
                return e

            for comp in components:
                if comp.type == ComponentType.RESISTOR:
                    d += _make(elm.Resistor, comp)
                elif comp.type == ComponentType.CAPACITOR:
                    d += _make(elm.Capacitor, comp)
                elif comp.type == ComponentType.INDUCTOR:
                    d += _make(elm.Inductor, comp)
                elif comp.type == ComponentType.BATTERY:
                    direction = _DIR.get(comp.direction, "up")
                    lbl = (comp.label or "") + " " + (comp.value or "")
                    e = getattr(elm.Battery(), direction)()
                    if comp.reverse:
                        e = e.reverse()
                    if lbl.strip():
                        e = e.label(lbl.strip(), loc="left")
                    d += e
                elif comp.type == ComponentType.SWITCH:
                    d += _make(elm.Switch, comp)
                elif comp.type == ComponentType.GROUND:
                    d += elm.Ground()
                elif comp.type == ComponentType.AMMETER:
                    d += _make(elm.MeterA, comp)
                elif comp.type == ComponentType.VOLTMETER:
                    d += _make(elm.MeterV, comp)
                elif comp.type == ComponentType.WIRE:
                    direction = _DIR.get(comp.direction, "right")
                    length = getattr(comp, "length", 3) or 3
                    d += getattr(elm.Line(), direction)(length)
                else:
                    direction = _DIR.get(comp.direction, "right")
                    d += getattr(elm.Line(), direction)()

            return _schemdraw_to_svg(d)
    except Exception:
        return _fallback_dc_circuit(schema, canvas_w, canvas_h)


def _fallback_dc_circuit(schema, canvas_w, canvas_h) -> str:
    """Simple loop circuit drawn with svgwrite."""
    dwg = _base_drawing(canvas_w, canvas_h)
    components = schema.components
    n = len(components)

    if schema.title:
        _text(dwg, schema.title, canvas_w / 2, 30, size=16)

    # Draw a rectangular loop: top rail = components
    margin = 80
    top_y = canvas_h * 0.3
    bot_y = canvas_h * 0.7
    left_x = margin
    right_x = canvas_w - margin

    # Top wire: distribute components horizontally
    total_top_w = right_x - left_x
    x = left_x
    comp_w = 80

    for i, comp in enumerate(components):
        lbl = comp.value or comp.label or comp.type
        spacing = total_top_w / n
        seg_start = left_x + i * spacing
        seg_end = seg_start + spacing
        # Wire before component
        comp_x = seg_start + (seg_end - seg_start - comp_w) / 2
        dwg.add(dwg.line(start=(seg_start, top_y), end=(comp_x, top_y),
                         stroke=STROKE, stroke_width=2))
        # Component
        if comp.type == ComponentType.RESISTOR:
            _draw_resistor_svg(dwg, comp_x, top_y, comp_w, 28, lbl)
        elif comp.type == ComponentType.CAPACITOR:
            _draw_capacitor_svg(dwg, comp_x + comp_w / 2, top_y, comp_w, 34, lbl)
        elif comp.type == ComponentType.BATTERY:
            _draw_battery_svg(dwg, comp_x, top_y - 20, comp_x, top_y + 20, lbl)
        else:
            dwg.add(dwg.rect(insert=(comp_x, top_y - 14), size=(comp_w, 28),
                             stroke=STROKE, stroke_width=1.5, fill="white"))
            _text(dwg, str(lbl)[:6], comp_x + comp_w / 2, top_y + 5, size=11)
        dwg.add(dwg.line(start=(comp_x + comp_w, top_y), end=(seg_end, top_y),
                         stroke=STROKE, stroke_width=2))

    # Side wires and bottom wire
    dwg.add(dwg.line(start=(left_x, top_y), end=(left_x, bot_y),
                     stroke=STROKE, stroke_width=2))
    dwg.add(dwg.line(start=(right_x, top_y), end=(right_x, bot_y),
                     stroke=STROKE, stroke_width=2))
    dwg.add(dwg.line(start=(left_x, bot_y), end=(right_x, bot_y),
                     stroke=STROKE, stroke_width=2))

    # Ground symbol at bottom-left
    gx, gy = left_x, bot_y
    for j in range(3):
        hw = 18 - j * 5
        dwg.add(dwg.line(start=(gx - hw, gy + j * 8 + 2), end=(gx + hw, gy + j * 8 + 2),
                         stroke=STROKE, stroke_width=2))

    # Current direction arrow
    if schema.show_current_direction:
        mid_top = (left_x + right_x) / 2
        from diagrams.service.physics.renderer import _arrow as _phys_arrow
        # Add arrowhead marker
        marker = dwg.marker(id="arrowhead2", insert=(10, 4), size=(10, 8),
                            orient="auto", markerUnits="userSpaceOnUse")
        marker.add(dwg.polygon(points=[(0, 0), (10, 4), (0, 8)], fill=STROKE))
        dwg.defs.add(marker)
        # Arrow on bottom wire showing conventional current direction
        arr = dwg.line(start=(left_x + 40, bot_y + 20), end=(left_x + 100, bot_y + 20),
                       stroke=STROKE, stroke_width=1.5,
                       marker_end="url(#arrowhead2)")
        dwg.add(arr)
        _text(dwg, "I", left_x + 70, bot_y + 36, size=12)

    return dwg.tostring()


# ── Dispatcher ────────────────────────────────────────────────────────────────

CIRCUIT_RENDERERS = {
    "resistor_network": render_resistor_network,
    "capacitor_network": render_capacitor_network,
    "basic_dc_circuit": render_basic_dc_circuit,
}


def render_circuits(subtype: str, params: Dict[str, Any],
                    canvas_w: int = 800, canvas_h: int = 600) -> str:
    renderer = CIRCUIT_RENDERERS.get(subtype)
    if not renderer:
        raise ValueError(f"Unknown circuit subtype: '{subtype}'. "
                         f"Supported: {list(CIRCUIT_RENDERERS.keys())}")
    return renderer(params, canvas_w=canvas_w, canvas_h=canvas_h)
