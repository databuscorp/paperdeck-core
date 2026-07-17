"""
Circuit Diagram Renderer.
Uses schemdraw for circuit layout; falls back to svgwrite if schemdraw unavailable.
Supports: resistor networks, capacitor networks, basic DC circuits.
"""
from __future__ import annotations

import io
import math
import re
from typing import Any, Dict, List, Optional, Tuple

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
    LogicGatesSchema, GateType,
    ACPhasorSchema, ACCircuitType,
    WheatstoneBridgeSchema, BridgeVariant,
    RectifierSchema, RectifierType,
    RLCCircuitSchema, RLCTopology, RLCComponentType,
    MeshCircuitSchema, MeshComponentType, Polarity, CurrentDirection, LoopDirection,
    TransistorAmplifierSchema, AmplifierConfiguration, TransistorType,
    TransformerSchema, TransformerKind,
    RCCircuitSchema, RCMode, RCGraphQuantity,
    GalvanometerConversionSchema, GalvanometerConversionType,
    EMMachineSchema, EMMachineType, RotationSense,
    LogicCombinationalSchema, CombinationalCircuit, LogicOutput,
    ZenerRegulatorSchema,
    TransistorSwitchSchema, SwitchState, SwitchLoadType,
    CROSchema, ScreenWaveform,
)

STROKE = "black"
FONT_SZ = 13
FONT = "Arial, sans-serif"


# Arial has no U+2080-2089: a subscript digit rasterises to a tofu box in the
# PDF pipeline, so labels like "V₀" are folded to "V0" on the way out.
_SUBSCRIPTS = str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")


def _text(dwg, txt, x, y, anchor="middle", size=FONT_SZ):
    dwg.add(dwg.text(str(txt).translate(_SUBSCRIPTS), insert=(x, y),
                     font_size=size, font_family=FONT, text_anchor=anchor))


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


# ── 4. Logic Gates ────────────────────────────────────────────────────────────

GATE_H = 40          # nominal gate body height
_PIN_SPACING = 16    # vertical spacing between input pins on a gate


def _gate_eval(gate_type: GateType, vals: List[int]) -> int:
    """Evaluate one gate. XOR/XNOR generalise to odd/even parity for >2 inputs."""
    if gate_type == GateType.AND:
        return int(all(vals))
    if gate_type == GateType.OR:
        return int(any(vals))
    if gate_type == GateType.NOT:
        return int(not vals[0])
    if gate_type == GateType.NAND:
        return int(not all(vals))
    if gate_type == GateType.NOR:
        return int(not any(vals))
    if gate_type == GateType.XOR:
        return int(sum(vals) % 2 == 1)
    if gate_type == GateType.XNOR:
        return int(sum(vals) % 2 == 0)
    raise ValueError(f"Unknown gate type: {gate_type}")


def _logic_topology(schema: LogicGatesSchema):
    """Return (incoming, order, output_gate_id).

    incoming[gate_id] -> ordered list of connections feeding that gate
    (sorted by to_input_index, unindexed ones appended in declaration order).
    order -> gate ids in topological evaluation order.
    """
    gate_ids = [g.id for g in schema.gates]
    gate_id_set = set(gate_ids)

    incoming = {gid: [] for gid in gate_ids}
    for c in schema.connections:
        incoming[c.to_id].append(c)
    for gid in gate_ids:
        indexed = [c for c in incoming[gid] if c.to_input_index is not None]
        rest = [c for c in incoming[gid] if c.to_input_index is None]
        incoming[gid] = sorted(indexed, key=lambda c: c.to_input_index) + rest

    # Kahn topological order over gate->gate dependencies
    deps = {gid: {c.from_id for c in incoming[gid] if c.from_id in gate_id_set}
            for gid in gate_ids}
    resolved = {i.id for i in schema.inputs}
    order: List[str] = []
    remaining = list(gate_ids)
    while remaining:
        ready = [g for g in remaining if deps[g] <= resolved]
        if not ready:
            raise ValueError("Gate network contains a cycle")
        for g in ready:
            order.append(g)
            resolved.add(g)
            remaining.remove(g)

    # Output gate: first gate whose output feeds no other gate
    feeders = {c.from_id for c in schema.connections}
    sinks = [gid for gid in gate_ids if gid not in feeders]
    output_gate = sinks[0] if sinks else gate_ids[-1]
    return incoming, order, output_gate


def _evaluate_logic_network(schema: LogicGatesSchema, assignment: Dict[str, int],
                            incoming, order) -> Dict[str, int]:
    """Evaluate every gate for a given input assignment {input_id: 0|1}."""
    gate_type_by_id = {g.id: g.gate_type for g in schema.gates}
    vals = dict(assignment)
    for gid in order:
        in_vals = [vals[c.from_id] for c in incoming[gid]]
        vals[gid] = _gate_eval(gate_type_by_id[gid], in_vals)
    return vals


def _compute_truth_table(schema: LogicGatesSchema, incoming, order, output_gate):
    """Compute the full truth table by evaluating the network for every combo."""
    input_ids = [i.id for i in schema.inputs]
    n = len(input_ids)
    headers = [i.label for i in schema.inputs] + [schema.output_label]
    rows = []
    for combo in range(2 ** n):
        bits = [(combo >> (n - 1 - k)) & 1 for k in range(n)]
        assignment = dict(zip(input_ids, bits))
        vals = _evaluate_logic_network(schema, assignment, incoming, order)
        rows.append(bits + [vals[output_gate]])
    return headers, rows


def _or_back_inset(pin_y: float, cy: float) -> float:
    """Horizontal inset of the concave OR-family back curve at a pin height.

    Back curve is the quadratic from (0, cy-20) to (0, cy+20) with control
    (14, cy); at parameter t the x offset is 2*t*(1-t)*14.
    """
    t = (pin_y - (cy - GATE_H / 2)) / GATE_H
    t = max(0.0, min(1.0, t))
    return 2 * t * (1 - t) * 14


def _draw_logic_gate(dwg, gate_type: GateType, x: float, cy: float,
                     n_in: int, label: Optional[str] = None):
    """Draw an IEEE/ANSI gate with left edge at x, centred vertically at cy.

    Returns (input_points, output_point).
    """
    h2 = GATE_H / 2
    or_family = gate_type in (GateType.OR, GateType.NOR,
                              GateType.XOR, GateType.XNOR)
    body_x = x + 8 if gate_type in (GateType.XOR, GateType.XNOR) else x

    if gate_type in (GateType.XOR, GateType.XNOR):
        # Extra input curve of XOR/XNOR, offset left of the body
        dwg.add(dwg.path(
            d=f"M {x:.1f},{cy - h2:.1f} Q {x + 14:.1f},{cy:.1f} {x:.1f},{cy + h2:.1f}",
            stroke=STROKE, fill="none", stroke_width=2))

    if gate_type in (GateType.AND, GateType.NAND):
        # D-shape: flat back, straight top/bottom, semicircular nose
        dwg.add(dwg.path(
            d=(f"M {body_x:.1f},{cy - h2:.1f} L {body_x + 33:.1f},{cy - h2:.1f} "
               f"A {h2:.1f},{h2:.1f} 0 0 1 {body_x + 33:.1f},{cy + h2:.1f} "
               f"L {body_x:.1f},{cy + h2:.1f} Z"),
            stroke=STROKE, fill="white", stroke_width=2))
        tip_x = body_x + 33 + h2
    elif or_family:
        # Curved back, swept top/bottom meeting at a pointed nose
        dwg.add(dwg.path(
            d=(f"M {body_x:.1f},{cy - h2:.1f} "
               f"Q {body_x + 38:.1f},{cy - h2:.1f} {body_x + 55:.1f},{cy:.1f} "
               f"Q {body_x + 38:.1f},{cy + h2:.1f} {body_x:.1f},{cy + h2:.1f} "
               f"Q {body_x + 14:.1f},{cy:.1f} {body_x:.1f},{cy - h2:.1f} Z"),
            stroke=STROKE, fill="white", stroke_width=2))
        tip_x = body_x + 55
    else:  # NOT — triangle
        dwg.add(dwg.polygon(
            points=[(body_x, cy - 16), (body_x + 34, cy), (body_x, cy + 16)],
            stroke=STROKE, fill="white", stroke_width=2))
        tip_x = body_x + 34

    # Inversion bubble
    if gate_type in (GateType.NOT, GateType.NAND, GateType.NOR, GateType.XNOR):
        dwg.add(dwg.circle(center=(tip_x + 5, cy), r=5,
                           stroke=STROKE, fill="white", stroke_width=2))
        out_pt = (tip_x + 10, cy)
    else:
        out_pt = (tip_x, cy)

    # Input pin points along the left edge (on the back curve for OR family)
    in_pts = []
    for k in range(max(1, n_in)):
        py = cy + (k - (n_in - 1) / 2) * _PIN_SPACING
        px = x + (_or_back_inset(py, cy) if or_family else 0)
        in_pts.append((px, py))

    if label:
        _text(dwg, label, body_x + 24, cy + h2 + 15, size=10)
    return in_pts, out_pt


def _draw_truth_table(dwg, headers, rows, x, y):
    """Draw a bordered truth table with header row at (x, y)."""
    col_w = max(40, 12 + 9 * max(len(h) for h in headers))
    row_h = 22
    n_cols = len(headers)
    total_w = col_w * n_cols
    total_h = row_h * (len(rows) + 1)

    dwg.add(dwg.rect(insert=(x, y), size=(total_w, total_h),
                     stroke=STROKE, stroke_width=1.5, fill="white"))
    # Header separator + vertical rule before the output column
    dwg.add(dwg.line(start=(x, y + row_h), end=(x + total_w, y + row_h),
                     stroke=STROKE, stroke_width=1.5))
    dwg.add(dwg.line(start=(x + col_w * (n_cols - 1), y),
                     end=(x + col_w * (n_cols - 1), y + total_h),
                     stroke=STROKE, stroke_width=1))

    for j, h in enumerate(headers):
        dwg.add(dwg.text(h, insert=(x + col_w * j + col_w / 2, y + row_h - 7),
                         font_size=12, font_family=FONT, font_weight="bold",
                         text_anchor="middle"))
    for i, row in enumerate(rows):
        ry = y + row_h * (i + 1) + row_h - 7
        for j, val in enumerate(row):
            _text(dwg, str(val), x + col_w * j + col_w / 2, ry, size=12)


def render_logic_gates(data: Dict[str, Any], canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = LogicGatesSchema(**data)
    dwg = _base_drawing(canvas_w, canvas_h)

    if schema.title:
        _text(dwg, schema.title, canvas_w / 2, 28, size=16)

    incoming, order, output_gate = _logic_topology(schema)
    n_inputs = len(schema.inputs)

    table = None
    if schema.show_truth_table and n_inputs <= 4:
        table = _compute_truth_table(schema, incoming, order, output_gate)

    circuit_right = canvas_w * 0.60 if table else canvas_w - 40

    # ── Topological levels (left-to-right) ──
    level: Dict[str, int] = {inp.id: 0 for inp in schema.inputs}
    for gid in order:
        level[gid] = 1 + max(level[c.from_id] for c in incoming[gid])
    max_level = max(level[gid] for gid in order)

    left_x = 95                       # x of input source points
    gate_full_w = 82                  # widest gate incl. XOR offset + bubble
    spacing = (circuit_right - left_x - gate_full_w - 45) / max_level
    spacing = max(105.0, min(170.0, spacing))

    top = 60 if schema.title else 45
    bottom = canvas_h - 55
    region_h = bottom - top

    # ── Vertical positions: inputs evenly spaced, gates at barycentre ──
    pos_y: Dict[str, float] = {}
    for i, inp in enumerate(schema.inputs):
        pos_y[inp.id] = top + region_h * (i + 1) / (n_inputs + 1)

    gates_by_level: Dict[int, list] = {}
    for g in schema.gates:
        gates_by_level.setdefault(level[g.id], []).append(g)
    for lv in sorted(gates_by_level):
        glist = gates_by_level[lv]
        for g in glist:
            src_ys = [pos_y[c.from_id] for c in incoming[g.id]]
            pos_y[g.id] = sum(src_ys) / len(src_ys)
        glist.sort(key=lambda g: pos_y[g.id])
        # Enforce a minimum vertical gap within the level
        min_gap = GATE_H + 34
        for j in range(1, len(glist)):
            if pos_y[glist[j].id] - pos_y[glist[j - 1].id] < min_gap:
                pos_y[glist[j].id] = pos_y[glist[j - 1].id] + min_gap
        # Keep the column inside the drawing region
        overflow = pos_y[glist[-1].id] - (bottom - GATE_H / 2)
        if overflow > 0:
            for g in glist:
                pos_y[g.id] -= overflow

    # ── Draw inputs ──
    out_pt: Dict[str, tuple] = {}
    for inp in schema.inputs:
        y = pos_y[inp.id]
        _text(dwg, inp.label, left_x - 48, y + 5, anchor="end", size=14)
        dwg.add(dwg.line(start=(left_x - 42, y), end=(left_x, y),
                         stroke=STROKE, stroke_width=2))
        out_pt[inp.id] = (left_x, y)

    # ── Draw gates (record pin geometry) ──
    in_pts: Dict[str, list] = {}
    for g in schema.gates:
        gx = left_x + level[g.id] * spacing - 10
        pins, o = _draw_logic_gate(dwg, g.gate_type, gx, pos_y[g.id],
                                   len(incoming[g.id]), g.label)
        in_pts[g.id] = pins
        out_pt[g.id] = o

    # ── Wires (orthogonal: H, V, H) ──
    fanout: Dict[str, int] = {}
    for c in schema.connections:
        fanout[c.from_id] = fanout.get(c.from_id, 0) + 1
    for gid in [g.id for g in schema.gates]:
        for k, conn in enumerate(incoming[gid]):
            sx, sy = out_pt[conn.from_id]
            tx, ty = in_pts[gid][k]
            mx = sx + (tx - sx) * 0.45
            dwg.add(dwg.polyline(
                points=[(sx, sy), (mx, sy), (mx, ty), (tx, ty)],
                stroke=STROKE, fill="none", stroke_width=2))
            if fanout.get(conn.from_id, 0) > 1:
                dwg.add(dwg.circle(center=(sx, sy), r=3, fill=STROKE))

    # ── Output stub + label ──
    ox, oy = out_pt[output_gate]
    dwg.add(dwg.line(start=(ox, oy), end=(ox + 35, oy),
                     stroke=STROKE, stroke_width=2))
    _text(dwg, schema.output_label, ox + 44, oy + 5, anchor="start", size=14)

    # ── Truth table ──
    if table:
        headers, rows = table
        col_w = max(40, 12 + 9 * max(len(h) for h in headers))
        tbl_w = col_w * len(headers)
        tbl_h = 22 * (len(rows) + 1)
        tx = circuit_right + (canvas_w - 30 - circuit_right - tbl_w) / 2
        ty = max(top, (canvas_h - tbl_h) / 2)
        _draw_truth_table(dwg, headers, rows, tx, ty)

    return dwg.tostring()


# ── 5. AC Phasor Diagram ──────────────────────────────────────────────────────

def _phasor_resultant(phasors) -> tuple:
    """Vector sum of phasors -> (magnitude, angle_deg)."""
    rx = sum(p.magnitude * math.cos(math.radians(p.angle_deg)) for p in phasors)
    ry = sum(p.magnitude * math.sin(math.radians(p.angle_deg)) for p in phasors)
    return math.hypot(rx, ry), math.degrees(math.atan2(ry, rx))


def _draw_mini_resistor(dwg, cx, cy, w=30):
    """Small zig-zag resistor centred at (cx, cy) on a horizontal wire."""
    n_zig = 6
    step = w / n_zig
    pts = [(cx - w / 2, cy)]
    for i in range(n_zig):
        px = cx - w / 2 + step * (i + 0.5)
        py = cy - 6 if i % 2 == 0 else cy + 6
        pts.append((px, py))
    pts.append((cx + w / 2, cy))
    dwg.add(dwg.polyline(points=pts, stroke=STROKE, fill="none", stroke_width=1.5))


def _draw_mini_inductor(dwg, cx, cy, w=30):
    """Small 3-hump inductor centred at (cx, cy) on a horizontal wire."""
    hump = w / 3
    x = cx - w / 2
    d = f"M {x:.1f},{cy:.1f}"
    for _ in range(3):
        d += f" A {hump / 2:.1f},{hump / 2 + 2:.1f} 0 0 1 {x + hump:.1f},{cy:.1f}"
        x += hump
    dwg.add(dwg.path(d=d, stroke=STROKE, fill="none", stroke_width=1.5))


def _draw_mini_capacitor(dwg, cx, cy, w=30):
    """Small capacitor (two plates) centred at (cx, cy) on a horizontal wire."""
    gap = 6
    dwg.add(dwg.line(start=(cx - w / 2, cy), end=(cx - gap / 2, cy),
                     stroke=STROKE, stroke_width=1.5))
    dwg.add(dwg.line(start=(cx + gap / 2, cy), end=(cx + w / 2, cy),
                     stroke=STROKE, stroke_width=1.5))
    for px in (cx - gap / 2, cx + gap / 2):
        dwg.add(dwg.line(start=(px, cy - 8), end=(px, cy + 8),
                         stroke=STROKE, stroke_width=2))


def _draw_companion_circuit(dwg, circuit_type: ACCircuitType, x: float, y: float):
    """Small series AC circuit sketch with source ~ and R/L/C on the top rail."""
    comps = {
        ACCircuitType.SERIES_RLC: ["R", "L", "C"],
        ACCircuitType.RC: ["R", "C"],
        ACCircuitType.RL: ["R", "L"],
        ACCircuitType.LC: ["L", "C"],
    }[circuit_type]

    w, h = 60 * len(comps) + 30, 78
    lw = 1.5
    # Bottom and side rails
    dwg.add(dwg.line(start=(x, y), end=(x, y + h / 2 - 11),
                     stroke=STROKE, stroke_width=lw))
    dwg.add(dwg.line(start=(x, y + h / 2 + 11), end=(x, y + h),
                     stroke=STROKE, stroke_width=lw))
    dwg.add(dwg.line(start=(x, y + h), end=(x + w, y + h),
                     stroke=STROKE, stroke_width=lw))
    dwg.add(dwg.line(start=(x + w, y + h), end=(x + w, y),
                     stroke=STROKE, stroke_width=lw))
    # AC source on the left rail
    dwg.add(dwg.circle(center=(x, y + h / 2), r=11,
                       stroke=STROKE, fill="white", stroke_width=lw))
    _text(dwg, "~", x, y + h / 2 + 5, size=15)

    # Components along the top rail
    slot = w / len(comps)
    prev_x = x
    for i, c in enumerate(comps):
        cx = x + slot * (i + 0.5)
        dwg.add(dwg.line(start=(prev_x, y), end=(cx - 15, y),
                         stroke=STROKE, stroke_width=lw))
        if c == "R":
            _draw_mini_resistor(dwg, cx, y)
        elif c == "L":
            _draw_mini_inductor(dwg, cx, y)
        else:
            _draw_mini_capacitor(dwg, cx, y)
        _text(dwg, c, cx, y - 14, size=12)
        prev_x = cx + 15
    dwg.add(dwg.line(start=(prev_x, y), end=(x + w, y),
                     stroke=STROKE, stroke_width=lw))


def render_ac_phasor(data: Dict[str, Any], canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = ACPhasorSchema(**data)
    dwg = _base_drawing(canvas_w, canvas_h)

    if schema.title:
        _text(dwg, schema.title, canvas_w / 2, 28, size=16)

    # Arrowhead markers (component + resultant)
    marker = dwg.marker(id="ph_arrow", insert=(9, 4), size=(10, 8),
                        orient="auto", markerUnits="userSpaceOnUse")
    marker.add(dwg.polygon(points=[(0, 0), (10, 4), (0, 8)], fill=STROKE))
    dwg.defs.add(marker)
    marker_r = dwg.marker(id="ph_arrow_r", insert=(11, 5), size=(13, 10),
                          orient="auto", markerUnits="userSpaceOnUse")
    marker_r.add(dwg.polygon(points=[(0, 0), (13, 5), (0, 10)], fill=STROKE))
    dwg.defs.add(marker_r)

    r_mag, r_ang = _phasor_resultant(schema.phasors)
    draw_resultant = schema.show_resultant and r_mag > 1e-9

    ox = canvas_w * 0.42 if schema.circuit_type else canvas_w * 0.5
    oy = canvas_h * 0.55
    max_len_px = min(canvas_w, canvas_h) * 0.33
    max_mag = max([p.magnitude for p in schema.phasors] +
                  ([r_mag] if draw_resultant else []))
    scale = max_len_px / max_mag

    # ── Reference axes (dashed) ──
    axis_r = max_len_px + 35
    for (x1, y1, x2, y2) in [(ox - axis_r, oy, ox + axis_r, oy),
                             (ox, oy - axis_r, ox, oy + axis_r)]:
        dwg.add(dwg.line(start=(x1, y1), end=(x2, y2), stroke=STROKE,
                         stroke_width=1, stroke_dasharray="5,4"))
    ref = schema.reference_label or "Reference"
    _text(dwg, ref, ox + axis_r + 6, oy + 4, anchor="start", size=12)
    dwg.add(dwg.circle(center=(ox, oy), r=2.5, fill=STROKE))

    # ── Component phasors ──
    for p in schema.phasors:
        ang = math.radians(p.angle_deg)
        length = p.magnitude * scale
        ex = ox + length * math.cos(ang)
        ey = oy - length * math.sin(ang)
        dwg.add(dwg.line(start=(ox, oy), end=(ex, ey), stroke=STROKE,
                         stroke_width=2, marker_end="url(#ph_arrow)"))
        lx = ox + (length + 20) * math.cos(ang)
        ly = oy - (length + 20) * math.sin(ang) + 4
        if abs(math.sin(ang)) < 0.35:
            ly -= 14          # near-horizontal: lift label off the dashed axis
        lbl = p.label
        if schema.show_angle_labels:
            lbl += f" ({p.angle_deg:g}°)"
        _text(dwg, lbl, lx, ly, size=13)

    # ── Resultant (vector sum) ──
    if draw_resultant:
        ang = math.radians(r_ang)
        length = r_mag * scale
        ex = ox + length * math.cos(ang)
        ey = oy - length * math.sin(ang)
        dwg.add(dwg.line(start=(ox, oy), end=(ex, ey), stroke=STROKE,
                         stroke_width=3.5, marker_end="url(#ph_arrow_r)"))
        lx = ox + (length + 30) * math.cos(ang)
        ly = oy - (length + 30) * math.sin(ang) + 4
        _text(dwg, "Resultant", lx, ly, size=13)

        # Phase-angle arc from the +x reference axis to the resultant
        if abs(r_ang) > 1.0:
            arc_r = 34
            sweep = 0 if r_ang > 0 else 1          # CCW (math +) sweeps up on screen
            large = 1 if abs(r_ang) > 180 else 0
            ax2 = ox + arc_r * math.cos(ang)
            ay2 = oy - arc_r * math.sin(ang)
            dwg.add(dwg.path(
                d=f"M {ox + arc_r:.1f},{oy:.1f} "
                  f"A {arc_r},{arc_r} 0 {large} {sweep} {ax2:.1f},{ay2:.1f}",
                stroke=STROKE, fill="none", stroke_width=1.2))
            if schema.show_angle_labels:
                mid = math.radians(r_ang / 2)
                _text(dwg, f"φ = {r_ang:.1f}°",
                      ox + 58 * math.cos(mid), oy - 58 * math.sin(mid) + 4,
                      size=12)

    # ── Companion circuit sketch ──
    if schema.circuit_type:
        n_comp = {"series_rlc": 3}.get(schema.circuit_type.value, 2)
        cc_w = 60 * n_comp + 30
        _draw_companion_circuit(dwg, schema.circuit_type,
                                canvas_w - cc_w - 35, 55)

    return dwg.tostring()


# ── Shared electrical helpers ─────────────────────────────────────────────────
#
# Everything derivable (balance condition, unknown resistance, resonant
# frequency) is computed here from the raw values. Nothing that a question is
# marked on is ever read back from the params.

_SI_PREFIX = {
    "": 1.0, "p": 1e-12, "n": 1e-9,
    "u": 1e-6, "µ": 1e-6, "μ": 1e-6,        # both Unicode micro signs occur in the wild
    "m": 1e-3, "c": 1e-2, "k": 1e3, "K": 1e3, "M": 1e6, "G": 1e9,
}
_UNITS = ("ohms", "ohm", "Ω", "Hz", "H", "F", "V", "A")
_NUM_RE = re.compile(r"^\s*([+-]?\d*\.?\d+(?:[eE][+-]?\d+)?)\s*(.*)$")


def _parse_quantity(value: Any) -> Optional[float]:
    """Value of '1 mH' / '4.7µF' / '10Ω' / 220 in base SI units. None if unparseable.

    Prefix lookup is case-sensitive: 'm' is milli, 'M' is mega.
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    m = _NUM_RE.match(str(value))
    if not m:
        return None
    num = float(m.group(1))
    rest = m.group(2).strip()
    for unit in _UNITS:
        if rest.endswith(unit):
            rest = rest[:len(rest) - len(unit)]
            break
    prefix = rest.strip()
    if prefix in _SI_PREFIX:
        return num * _SI_PREFIX[prefix]
    return num          # unrecognised suffix: take the number as already-SI


def _fmt_ohm(r: float) -> str:
    return f"{r:.0f} Ω" if abs(r - round(r)) < 1e-9 else f"{r:.2f} Ω"


def _fmt_freq(f: float) -> str:
    if f >= 1e6:
        return f"{f / 1e6:.2f} MHz"
    if f >= 1e3:
        return f"{f / 1e3:.2f} kHz"
    return f"{f:.2f} Hz"


def metre_bridge_unknown(known_ohm: float, balance_len_cm: float,
                         wire_len_cm: float = 100.0) -> float:
    """Unknown resistance from the null point: X = R·l/(L − l)."""
    if balance_len_cm <= 0 or balance_len_cm >= wire_len_cm:
        raise ValueError("balance length must satisfy 0 < l < wire length")
    return known_ohm * balance_len_cm / (wire_len_cm - balance_len_cm)


def wheatstone_missing_arm(arms: List[Optional[float]]) -> Optional[Tuple[int, float]]:
    """Solve the one unknown arm from P·S = Q·R. arms = [P, Q, R, S].

    Returns (index, value), or None when the arms are not exactly-one-unknown.
    """
    if len(arms) != 4 or sum(a is None for a in arms) != 1:
        return None
    p, q, r, s = arms
    idx = arms.index(None)
    known = [a for a in arms if a is not None]
    if any(a <= 0 for a in known):
        return None
    if idx == 0:
        return 0, q * r / s
    if idx == 1:
        return 1, p * s / r
    if idx == 2:
        return 2, p * s / q
    return 3, q * r / p


def wheatstone_is_balanced(arms: List[Optional[float]], tol: float = 1e-6) -> Optional[bool]:
    """True when P/Q = R/S. None if any arm value is missing."""
    if any(a is None for a in arms):
        return None
    p, q, r, s = arms
    if q <= 0 or s <= 0:
        return None
    return abs(p / q - r / s) <= tol * max(1.0, p / q)


def resonant_frequency(l_henry: Optional[float], c_farad: Optional[float]) -> Optional[float]:
    """f₀ = 1/(2π√(LC)). None unless both L and C are known and positive."""
    if not l_henry or not c_farad or l_henry <= 0 or c_farad <= 0:
        return None
    return 1.0 / (2.0 * math.pi * math.sqrt(l_henry * c_farad))


def rectifier_waveform(rectifier_type: RectifierType, cycles: float = 2.0,
                       n: int = 480, filtered: bool = False,
                       tau_periods: float = 2.0) -> Tuple[List[float], List[float], List[float]]:
    """Sampled (t, v_in, v_out) for one rectifier, v normalised to a unit peak.

    v_out is derived from rectifier_type — half-wave passes only the positive
    half-cycles, both full-wave topologies invert the negative ones. The filter
    follows the diode: the capacitor holds its charge (exponential decay) until
    the rectified source rises above it again, so a filtered output never
    reaches zero.
    """
    ts, v_in, v_out = [], [], []
    v_c = 0.0
    dt = cycles / n
    for i in range(n + 1):
        t = cycles * i / n
        vi = math.sin(2.0 * math.pi * t)
        vr = max(vi, 0.0) if rectifier_type == RectifierType.HALF_WAVE else abs(vi)
        if filtered:
            v_c = max(vr, v_c * math.exp(-dt / tau_periods))
            vo = v_c
        else:
            vo = vr
        ts.append(t)
        v_in.append(vi)
        v_out.append(vo)
    return ts, v_in, v_out


# ── Drawing primitives shared by the bridge / rectifier / RLC renderers ───────

def _arrow_marker(dwg, ident: str = "c_arrow"):
    m = dwg.marker(id=ident, insert=(9, 4), size=(10, 8),
                   orient="auto", markerUnits="userSpaceOnUse")
    m.add(dwg.polygon(points=[(0, 0), (10, 4), (0, 8)], fill=STROKE))
    dwg.defs.add(m)
    return f"url(#{ident})"


def _wire(dwg, pts, width=2):
    dwg.add(dwg.polyline(points=pts, stroke=STROKE, fill="none", stroke_width=width))


def _dot(dwg, x, y, r=3.5):
    dwg.add(dwg.circle(center=(x, y), r=r, fill=STROKE))


def _draw_meter(dwg, cx, cy, letter, r=18):
    """Galvanometer / ammeter / voltmeter: a lettered circle."""
    dwg.add(dwg.circle(center=(cx, cy), r=r, stroke=STROKE, fill="white", stroke_width=2))
    _text(dwg, letter, cx, cy + 5, size=13)


def _draw_ac_source(dwg, cx, cy, r=24, label=None, label_anchor="end", label_dx=-34):
    """AC source: one sine period inside a circle (never a battery)."""
    dwg.add(dwg.circle(center=(cx, cy), r=r, stroke=STROKE, fill="white", stroke_width=2))
    pts = [(cx - r * 0.62 + i * (1.24 * r) / 24,
            cy - (r * 0.42) * math.sin(2 * math.pi * i / 24)) for i in range(25)]
    dwg.add(dwg.polyline(points=pts, stroke=STROKE, fill="none", stroke_width=1.8))
    if label:
        _text(dwg, label, cx + label_dx, cy + 5, anchor=label_anchor, size=13)


def _draw_cell_h(dwg, cx, cy, label=None, gap=12):
    """Cell on a horizontal wire: long plate = +, on the left."""
    dwg.add(dwg.line(start=(cx - gap / 2, cy - 16), end=(cx - gap / 2, cy + 16),
                     stroke=STROKE, stroke_width=3))
    dwg.add(dwg.line(start=(cx + gap / 2, cy - 9), end=(cx + gap / 2, cy + 9),
                     stroke=STROKE, stroke_width=2))
    _text(dwg, "+", cx - gap / 2 - 10, cy - 20, size=11)
    _text(dwg, "−", cx + gap / 2 + 10, cy - 20, size=11)
    if label:
        _text(dwg, label, cx, cy + 32, size=13)


def _draw_key(dwg, cx, cy, label=None, w=32):
    """Plug key / switch: two contacts and an open lever."""
    dwg.add(dwg.line(start=(cx - w / 2 - 6, cy), end=(cx - w / 2, cy),
                     stroke=STROKE, stroke_width=2))
    dwg.add(dwg.line(start=(cx + w / 2, cy), end=(cx + w / 2 + 6, cy),
                     stroke=STROKE, stroke_width=2))
    _dot(dwg, cx - w / 2, cy, 3)
    _dot(dwg, cx + w / 2, cy, 3)
    dwg.add(dwg.line(start=(cx - w / 2, cy), end=(cx + w / 2 - 4, cy - 14),
                     stroke=STROKE, stroke_width=2))
    if label:
        _text(dwg, label, cx, cy + 22, size=12)


def _draw_resistor_v(dwg, cx, y1, y2, label, w=34):
    """Resistor box on a vertical wire, label to the right."""
    dwg.add(dwg.rect(insert=(cx - w / 2, y1), size=(w, y2 - y1),
                     stroke=STROKE, stroke_width=2, fill="white"))
    _text(dwg, label, cx + w / 2 + 8, (y1 + y2) / 2 + 5, anchor="start", size=13)


def _draw_capacitor_v(dwg, cx, cy, label=None, plate_w=26, gap=9):
    """Capacitor plates on a vertical wire (plates horizontal)."""
    for dy in (-gap / 2, gap / 2):
        dwg.add(dwg.line(start=(cx - plate_w / 2, cy + dy), end=(cx + plate_w / 2, cy + dy),
                         stroke=STROKE, stroke_width=3))
    if label:
        _text(dwg, label, cx - plate_w / 2 - 8, cy + 5, anchor="end", size=12)


def _draw_arm_resistor(dwg, x1, y1, x2, y2, label, box_l=52, box_h=20,
                       label_off=32, label_side=1):
    """Resistor box centred on the arm (x1,y1)-(x2,y2) and rotated onto it.

    The label stays upright, pushed off the arm along its normal.
    """
    ang = math.degrees(math.atan2(y2 - y1, x2 - x1))
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    dx, dy = x2 - x1, y2 - y1
    ln = math.hypot(dx, dy) or 1.0
    ux, uy = dx / ln, dy / ln
    _wire(dwg, [(x1, y1), (mx - ux * box_l / 2, my - uy * box_l / 2)])
    _wire(dwg, [(mx + ux * box_l / 2, my + uy * box_l / 2), (x2, y2)])
    g = dwg.g(transform=f"rotate({ang:.2f},{mx:.2f},{my:.2f})")
    g.add(dwg.rect(insert=(mx - box_l / 2, my - box_h / 2), size=(box_l, box_h),
                   stroke=STROKE, stroke_width=2, fill="white"))
    dwg.add(g)
    nx, ny = -uy * label_side, ux * label_side
    _text(dwg, label, mx + nx * label_off, my + ny * label_off + 4, size=13)


def _draw_diode(dwg, x1, y1, x2, y2, label=None, size=14, label_off=18, label_side=1):
    """Diode on the wire (x1,y1)→(x2,y2): triangle points x1→x2, bar (cathode) at the tip.

    Conventional current can only flow x1 (anode) → x2 (cathode).
    """
    dx, dy = x2 - x1, y2 - y1
    ln = math.hypot(dx, dy) or 1.0
    ux, uy = dx / ln, dy / ln
    nx, ny = -uy, ux
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    bx, by = mx - ux * size / 2, my - uy * size / 2          # triangle base centre
    tx, ty = mx + ux * size / 2, my + uy * size / 2          # tip = cathode
    _wire(dwg, [(x1, y1), (bx, by)])
    _wire(dwg, [(tx, ty), (x2, y2)])
    h = size * 0.58
    dwg.add(dwg.polygon(
        points=[(bx + nx * h, by + ny * h), (bx - nx * h, by - ny * h), (tx, ty)],
        stroke=STROKE, fill=STROKE, stroke_width=1))
    b = size * 0.62
    dwg.add(dwg.line(start=(tx + nx * b, ty + ny * b), end=(tx - nx * b, ty - ny * b),
                     stroke=STROKE, stroke_width=2.6))
    if label:
        _text(dwg, label, mx + nx * label_off * label_side,
              my + ny * label_off * label_side + 4, size=12)


def _draw_coil_v(dwg, x, y1, y2, n=4, bulge=1):
    """Transformer winding: n semicircular humps down a vertical line, bulging ±x."""
    h = (y2 - y1) / n
    d = f"M {x:.1f},{y1:.1f}"
    for i in range(n):
        sweep = 1 if bulge > 0 else 0
        d += f" A {h / 2:.1f},{h / 2:.1f} 0 0 {sweep} {x:.1f},{y1 + h * (i + 1):.1f}"
    dwg.add(dwg.path(d=d, stroke=STROKE, fill="none", stroke_width=2))


def _hop_line_h(dwg, x1, x2, y, hops=(), r=7):
    """Horizontal wire that hops (semicircle) over crossing verticals — no false junction."""
    xs = sorted(h for h in hops if min(x1, x2) + r < h < max(x1, x2) - r)
    if x1 > x2:
        xs = xs[::-1]
    d = f"M {x1:.1f},{y:.1f}"
    for hx in xs:
        step = r if x2 > x1 else -r
        d += f" L {hx - step:.1f},{y:.1f}"
        sweep = 1 if x2 > x1 else 0
        d += f" A {r},{r} 0 0 {sweep} {hx + step:.1f},{y:.1f}"
    d += f" L {x2:.1f},{y:.1f}"
    dwg.add(dwg.path(d=d, stroke=STROKE, fill="none", stroke_width=2))


def _draw_scale(dwg, x0, x1, y, length_cm, major=10):
    """Metre scale under a resistance wire: ticks every `major` cm, 0…length."""
    h = 26
    dwg.add(dwg.rect(insert=(x0, y), size=(x1 - x0, h),
                     stroke=STROKE, stroke_width=1.2, fill="white"))
    n = int(round(length_cm / major))
    for i in range(n + 1):
        tx = x0 + (x1 - x0) * i / n
        dwg.add(dwg.line(start=(tx, y), end=(tx, y + 9), stroke=STROKE, stroke_width=1))
        _text(dwg, f"{int(i * major)}", tx, y + 21, size=10)


def _draw_jockey(dwg, x, y_wire, label=None, dashed=False):
    """Sliding jockey resting on the wire at x."""
    style = {"stroke_dasharray": "5,4"} if dashed else {}
    dwg.add(dwg.line(start=(x, y_wire - 26), end=(x, y_wire - 8),
                     stroke=STROKE, stroke_width=2, **style))
    dwg.add(dwg.polygon(points=[(x - 7, y_wire - 9), (x + 7, y_wire - 9), (x, y_wire)],
                        stroke=STROKE, fill="white" if dashed else STROKE, stroke_width=1.5))
    if label:
        _text(dwg, label, x, y_wire - 32, size=12)


# ── 6. Wheatstone Bridge (wheatstone | metre_bridge | potentiometer) ──────────

def render_wheatstone_bridge(data: Dict[str, Any], canvas_w: int = 800,
                             canvas_h: int = 600) -> str:
    schema = WheatstoneBridgeSchema(**data)
    dwg = _base_drawing(canvas_w, canvas_h)

    if schema.title:
        _text(dwg, schema.title, canvas_w / 2, 28, size=16)

    if schema.variant == BridgeVariant.METRE_BRIDGE:
        _draw_metre_bridge(dwg, schema, canvas_w, canvas_h)
    elif schema.variant == BridgeVariant.POTENTIOMETER:
        _draw_potentiometer(dwg, schema, canvas_w, canvas_h)
    else:
        _draw_wheatstone_diamond(dwg, schema, canvas_w, canvas_h)

    return dwg.tostring()


def _arm_label(label: str, value: Optional[str]) -> str:
    return f"{label} = {value}" if value else label


def _draw_wheatstone_diamond(dwg, schema, canvas_w, canvas_h):
    arrow = _arrow_marker(dwg, "wb_arrow")

    cx, cy = canvas_w * 0.47, 265
    hw, hh = 155, 112
    A = (cx - hw, cy)          # cell +   (left)
    B = (cx, cy - hh)          # galvo    (top)
    C = (cx + hw, cy)          # cell −   (right)
    D = (cx, cy + hh)          # galvo    (bottom)

    labels = schema.resistor_labels
    values = list(schema.resistor_values) + [None] * (4 - len(schema.resistor_values))
    # Arm order is fixed by the balance condition P/Q = R/S:
    # P = A→B, Q = B→C (upper arms); R = A→D, S = D→C (lower arms).
    arms = [(A, B, 0, -1), (B, C, 1, -1), (A, D, 2, 1), (D, C, 3, 1)]
    for (p1, p2, i, side) in arms:
        _draw_arm_resistor(dwg, p1[0], p1[1], p2[0], p2[1],
                           _arm_label(labels[i], values[i]), label_side=side)

    # Galvanometer on the B–D diagonal
    gx, gy = cx, cy
    _wire(dwg, [B, (gx, gy - 18)])
    _wire(dwg, [(gx, gy + 18), D])
    _draw_meter(dwg, gx, gy, schema.galvanometer_label)

    # Cell across the A–C diagonal, routed under the diamond
    y_cell = cy + hh + 105
    x_l, x_r = A[0] - 55, C[0] + 55
    _wire(dwg, [A, (x_l, cy), (x_l, y_cell), (cx - 90, y_cell)])
    _wire(dwg, [(cx + 90, y_cell), (x_r, y_cell), (x_r, cy), C])
    _draw_cell_h(dwg, cx - 30, y_cell, schema.cell_label)
    _draw_key(dwg, cx + 45, y_cell, "K")

    for (px, py) in (A, B, C, D):
        _dot(dwg, px, py)
    _text(dwg, "A", A[0] - 14, A[1] + 5, size=13)
    _text(dwg, "B", B[0], B[1] - 12, size=13)
    _text(dwg, "C", C[0] + 14, C[1] + 5, size=13)
    _text(dwg, "D", D[0], D[1] + 20, size=13)

    if schema.show_current_arrows:
        for (p1, p2) in ((A, B), (A, D), (B, C), (D, C)):
            dx, dy = p2[0] - p1[0], p2[1] - p1[1]
            ln = math.hypot(dx, dy)
            ux, uy = dx / ln, dy / ln
            nx, ny = -uy * 11, ux * 11
            dwg.add(dwg.line(start=(p1[0] + ux * ln * 0.10 + nx, p1[1] + uy * ln * 0.10 + ny),
                             end=(p1[0] + ux * ln * 0.26 + nx, p1[1] + uy * ln * 0.26 + ny),
                             stroke=STROKE, stroke_width=1.5, marker_end=arrow))
        _text(dwg, "I", A[0] + 4, y_cell - 12, size=12)
        dwg.add(dwg.line(start=(x_l + 30, y_cell - 26), end=(x_l + 80, y_cell - 26),
                         stroke=STROKE, stroke_width=1.5, marker_end=arrow))

    if schema.show_balance_condition:
        P, Q, R, S = labels
        _text(dwg, f"At balance (I_{schema.galvanometer_label} = 0):  "
                   f"{P}/{Q} = {R}/{S}", canvas_w / 2, canvas_h - 48, size=15)

        vals = [_parse_quantity(v) if v else None for v in values]
        solved = wheatstone_missing_arm(vals)
        if solved:
            i, val = solved
            num = [labels[1], labels[2]] if i == 0 else \
                  [labels[0], labels[3]] if i == 1 else \
                  [labels[0], labels[3]] if i == 2 else [labels[1], labels[2]]
            den = labels[3] if i == 0 else labels[2] if i == 1 else \
                labels[1] if i == 2 else labels[0]
            _text(dwg, f"{labels[i]} = ({num[0]} × {num[1]}) / {den} = {_fmt_ohm(val)}",
                  canvas_w / 2, canvas_h - 22, size=14)
        else:
            balanced = wheatstone_is_balanced(vals)
            if balanced is True:
                _text(dwg, f"{vals[0]:g}/{vals[1]:g} = {vals[2]:g}/{vals[3]:g} "
                           f"→ bridge is balanced", canvas_w / 2, canvas_h - 22, size=14)
            elif balanced is False:
                _text(dwg, f"{vals[0]:g}/{vals[1]:g} ≠ {vals[2]:g}/{vals[3]:g} "
                           f"→ bridge is NOT balanced", canvas_w / 2, canvas_h - 22, size=14)


def _draw_metre_bridge(dwg, schema, canvas_w, canvas_h):
    x0, x1 = 140, 680
    y_top, y_w = 180, 340
    L = schema.wire_length_cm
    l = schema.balance_length_cm
    x_j = x0 + (x1 - x0) * l / L
    x_b = (x0 + x1) / 2

    # Top rail: unknown in the left gap, known resistance box in the right gap
    _wire(dwg, [(x0, y_top), (190, y_top)])
    _draw_resistor_svg(dwg, 190, y_top, 120, 34, schema.unknown_label)
    _wire(dwg, [(310, y_top), (x_b, y_top)])
    _wire(dwg, [(x_b, y_top), (470, y_top)])
    _draw_resistor_svg(dwg, 470, y_top, 120, 34,
                       f"R = {schema.known_resistance}")
    _wire(dwg, [(590, y_top), (x1, y_top)])
    _text(dwg, "left gap", 250, y_top - 26, size=11)
    _text(dwg, "right gap", 530, y_top - 26, size=11)

    _wire(dwg, [(x0, y_top), (x0, y_w)])
    _wire(dwg, [(x1, y_top), (x1, y_w)])

    # The resistance wire itself + the metre scale under it
    dwg.add(dwg.line(start=(x0, y_w), end=(x1, y_w), stroke=STROKE, stroke_width=4))
    _draw_scale(dwg, x0, x1, y_w + 6, L)
    _text(dwg, f"{L:g} cm resistance wire", (x0 + x1) / 2, y_w + 50, size=11)

    # Galvanometer from B down to the jockey
    _wire(dwg, [(x_b, y_top), (x_b, 240)])
    _draw_meter(dwg, x_b, 258, schema.galvanometer_label)
    _wire(dwg, [(x_b, 276), (x_b, 300), (x_j, 300), (x_j, y_w - 24)])
    _draw_jockey(dwg, x_j, y_w)
    _dot(dwg, x_b, y_top)
    _text(dwg, "B", x_b + 10, y_top - 10, size=13)
    _text(dwg, "A", x0 - 12, y_top - 10, size=13)
    _text(dwg, "C", x1 + 12, y_top - 10, size=13)
    _text(dwg, f"l = {l:g} cm", x_j + 10, y_w - 46, anchor="start", size=12)

    # Cell + key across the ends of the wire
    y_cell = 470
    _wire(dwg, [(x0, y_w), (x0, y_cell), (300, y_cell)])
    _wire(dwg, [(360, y_cell), (440, y_cell)])
    _wire(dwg, [(500, y_cell), (x1, y_cell), (x1, y_w)])
    _draw_cell_h(dwg, 330, y_cell, schema.cell_label)
    _draw_key(dwg, 470, y_cell, "K")

    x_val = metre_bridge_unknown(_parse_quantity(schema.known_resistance), l, L)
    r_val = _parse_quantity(schema.known_resistance)
    _text(dwg, f"At balance:  {schema.unknown_label}/R = l/({L:g} − l)",
          canvas_w / 2, canvas_h - 48, size=15)
    _text(dwg, f"{schema.unknown_label} = R·l/({L:g} − l) = {r_val:g} × {l:g}/{L - l:g} "
               f"= {_fmt_ohm(x_val)}",
          canvas_w / 2, canvas_h - 22, size=14)


def _draw_potentiometer(dwg, schema, canvas_w, canvas_h):
    x0, x1 = 140, 680
    y_w = 300                       # the potentiometer wire
    y_drv = 170                     # driver (auxiliary) circuit above it
    L = schema.wire_length_cm
    l1 = schema.balance_length_cm
    l2 = schema.balance_length_2_cm
    two_cells = l2 is not None
    x_j1 = x0 + (x1 - x0) * l1 / L
    x_j2 = x0 + (x1 - x0) * l2 / L if two_cells else None

    dwg.add(dwg.line(start=(x0, y_w), end=(x1, y_w), stroke=STROKE, stroke_width=4))
    _draw_scale(dwg, x0, x1, y_w + 6, L)
    _text(dwg, "A", x0 - 14, y_w + 5, anchor="end", size=13)
    _text(dwg, "B", x1 + 14, y_w + 5, anchor="start", size=13)

    # Driver cell + rheostat: sets the potential gradient along AB
    if schema.show_driver_cell:
        _wire(dwg, [(x0, y_w), (x0, y_drv), (260, y_drv)])
        _draw_cell_h(dwg, 300, y_drv, "E (driver)")
        _wire(dwg, [(340, y_drv), (400, y_drv)])
        _draw_key(dwg, 440, y_drv, "K")
        _wire(dwg, [(480, y_drv), (530, y_drv)])
        _draw_resistor_svg(dwg, 530, y_drv, 70, 26, "Rh")
        _wire(dwg, [(600, y_drv), (x1, y_drv), (x1, y_w)])

    # Cell(s) under test: like poles to A, through the galvanometer to the jockey
    y_b1, y_b2 = 375, 465
    y_g = 360
    x_k = 430
    _wire(dwg, [(x0, y_w), (x0, y_b2 if two_cells else y_b1)])
    _wire(dwg, [(x0, y_b1), (215, y_b1)])
    _draw_cell_h(dwg, 255, y_b1, schema.emf_labels[0])
    _wire(dwg, [(295, y_b1), (340, y_b1)])
    _draw_key(dwg, 375, y_b1)
    _wire(dwg, [(410, y_b1), (x_k, y_b1), (x_k, 420)])
    _dot(dwg, x0, y_b1)
    if two_cells:
        _wire(dwg, [(x0, y_b2), (215, y_b2)])
        _draw_cell_h(dwg, 255, y_b2, schema.emf_labels[1])
        _wire(dwg, [(295, y_b2), (340, y_b2)])
        _draw_key(dwg, 375, y_b2)
        _wire(dwg, [(410, y_b2), (x_k, y_b2), (x_k, 420)])
        _dot(dwg, x0, y_b2)
        _text(dwg, "two-way key", 375, y_b2 + 42, size=11)

    _dot(dwg, x_k, 420)
    _wire(dwg, [(x_k, 420), (500, 420)])
    _draw_meter(dwg, 520, 420, schema.galvanometer_label)
    _wire(dwg, [(538, 420), (620, 420), (620, y_g), (x_j1, y_g), (x_j1, y_w - 24)])
    _draw_jockey(dwg, x_j1, y_w, f"l1 = {l1:g} cm" if two_cells else f"l = {l1:g} cm")
    if two_cells:
        _draw_jockey(dwg, x_j2, y_w, f"l2 = {l2:g} cm", dashed=True)

    if two_cells:
        _text(dwg, "At balance:  E1/E2 = l1/l2", canvas_w / 2, canvas_h - 48, size=15)
        _text(dwg, f"E1/E2 = {l1:g}/{l2:g} = {l1 / l2:.3f}",
              canvas_w / 2, canvas_h - 22, size=14)
    else:
        _text(dwg, "At balance:  E = k·l   (k = potential gradient of the wire, V/cm)",
              canvas_w / 2, canvas_h - 48, size=15)
        _text(dwg, f"l = {l1:g} cm of {L:g} cm  →  E = ({l1:g}/{L:g})·V_AB",
              canvas_w / 2, canvas_h - 22, size=14)


# ── 7. Rectifier (half-wave | full-wave centre-tap | full-wave bridge) ────────

def render_rectifier(data: Dict[str, Any], canvas_w: int = 800,
                     canvas_h: int = 600) -> str:
    schema = RectifierSchema(**data)
    dwg = _base_drawing(canvas_w, canvas_h)

    if schema.title:
        _text(dwg, schema.title, canvas_w / 2, 28, size=16)

    if schema.rectifier_type == RectifierType.HALF_WAVE:
        bottom = _draw_half_wave(dwg, schema)
    elif schema.rectifier_type == RectifierType.FULL_WAVE_CENTRE_TAP:
        bottom = _draw_centre_tap(dwg, schema)
    else:
        bottom = _draw_bridge_rectifier(dwg, schema)

    panels = int(schema.show_input_waveform) + int(schema.show_output_waveform)
    if panels:
        _, v_in, v_out = rectifier_waveform(schema.rectifier_type,
                                            filtered=schema.show_filter_capacitor)
        x, pw = 150, canvas_w - 190
        gap = 40
        ph = (canvas_h - bottom - 30 - gap * panels) / panels
        y = bottom + gap
        if schema.show_input_waveform:
            _draw_waveform_panel(dwg, x, y, pw, ph, v_in, "Input (AC)", bipolar=True)
            y += ph + gap
        if schema.show_output_waveform:
            cap = " (with filter C)" if schema.show_filter_capacitor else ""
            _draw_waveform_panel(dwg, x, y, pw, ph, v_out,
                                 f"Output across {schema.load_label}{cap}", bipolar=False)
    return dwg.tostring()


def _draw_transformer(dwg, schema, x_p, x_s, y_t, y_b, centre_tap=False):
    """Step-down transformer with the AC mains on the primary. Returns the secondary nodes."""
    _draw_coil_v(dwg, x_p, y_t, y_b, 4, bulge=-1)
    _draw_coil_v(dwg, x_s, y_t, y_b, 4, bulge=1)
    for x in (x_p + 12, x_p + 22):
        dwg.add(dwg.line(start=(x, y_t - 8), end=(x, y_b + 8),
                         stroke=STROKE, stroke_width=1.5))
    _draw_ac_source(dwg, x_p - 60, (y_t + y_b) / 2, 22)
    _text(dwg, schema.input_label, x_p - 60, y_b + 30, size=11)
    _wire(dwg, [(x_p - 60, (y_t + y_b) / 2 - 22), (x_p - 60, y_t), (x_p, y_t)])
    _wire(dwg, [(x_p - 60, (y_t + y_b) / 2 + 22), (x_p - 60, y_b), (x_p, y_b)])
    if centre_tap:
        _dot(dwg, x_s, (y_t + y_b) / 2)
        _text(dwg, "centre tap", x_s + 48, (y_t + y_b) / 2 - 10, size=10)


def _draw_half_wave(dwg, schema):
    x_s, y_t, y_b = 175, 110, 240
    x_load, x_cap = 700, 610
    if schema.show_transformer:
        _draw_transformer(dwg, schema, 110, x_s, y_t, y_b)
    else:
        _draw_ac_source(dwg, x_s - 60, (y_t + y_b) / 2, 22, schema.input_label)
        _wire(dwg, [(x_s - 60, (y_t + y_b) / 2 - 22), (x_s - 60, y_t), (x_s, y_t)])
        _wire(dwg, [(x_s - 60, (y_t + y_b) / 2 + 22), (x_s - 60, y_b), (x_s, y_b)])

    # A single diode: it blocks the negative half-cycle entirely.
    if schema.show_diodes:
        _wire(dwg, [(x_s, y_t), (330, y_t)])
        _draw_diode(dwg, 330, y_t, 430, y_t, "D", size=18, label_side=-1)
        _wire(dwg, [(430, y_t), (x_load, y_t)])
    else:
        _wire(dwg, [(x_s, y_t), (x_load, y_t)])
    _wire(dwg, [(x_s, y_b), (x_load, y_b)])
    _draw_resistor_v(dwg, x_load, y_t + 30, y_b - 30, schema.load_label)
    _wire(dwg, [(x_load, y_t), (x_load, y_t + 30)])
    _wire(dwg, [(x_load, y_b - 30), (x_load, y_b)])
    _text(dwg, "+", x_load - 14, y_t + 18, size=13)
    _text(dwg, "−", x_load - 14, y_b - 8, size=13)

    if schema.show_filter_capacitor:
        _wire(dwg, [(x_cap, y_t), (x_cap, (y_t + y_b) / 2 - 5)])
        _wire(dwg, [(x_cap, (y_t + y_b) / 2 + 5), (x_cap, y_b)])
        _draw_capacitor_v(dwg, x_cap, (y_t + y_b) / 2, schema.filter_capacitor_label)
        _dot(dwg, x_cap, y_t)
        _dot(dwg, x_cap, y_b)
    return y_b + 34


def _draw_centre_tap(dwg, schema):
    x_s, y_t, y_b = 175, 100, 220
    y_m = (y_t + y_b) / 2
    x_bus, x_load, x_drop, y_ret, x_cap = 600, 700, 245, 290, 650
    _draw_transformer(dwg, schema, 110, x_s, y_t, y_b, centre_tap=True)

    # Both diodes point at the bus: whichever secondary half is positive, the bus
    # is the + terminal and the centre tap the −, so the load current never reverses.
    if schema.show_diodes:
        _wire(dwg, [(x_s, y_t), (340, y_t)])
        _draw_diode(dwg, 340, y_t, 420, y_t, "D1", size=18, label_side=-1)
        _wire(dwg, [(420, y_t), (x_bus, y_t)])
        _hop_line_h(dwg, x_s, 340, y_b, hops=(x_drop,))
        _draw_diode(dwg, 340, y_b, 420, y_b, "D2", size=18, label_side=1)
        _wire(dwg, [(420, y_b), (x_bus, y_b)])
    else:
        _wire(dwg, [(x_s, y_t), (x_bus, y_t)])
        _hop_line_h(dwg, x_s, x_bus, y_b, hops=(x_drop,))
    _wire(dwg, [(x_bus, y_t), (x_bus, y_b)])
    _dot(dwg, x_bus, y_m)
    _wire(dwg, [(x_bus, y_m), (x_load, y_m)])

    _wire(dwg, [(x_s, y_m), (x_drop, y_m), (x_drop, y_ret), (x_load, y_ret)])
    _draw_resistor_v(dwg, x_load, y_m + 26, y_ret - 26, schema.load_label)
    _wire(dwg, [(x_load, y_m), (x_load, y_m + 26)])
    _wire(dwg, [(x_load, y_ret - 26), (x_load, y_ret)])
    _text(dwg, "+", x_load - 14, y_m + 18, size=13)
    _text(dwg, "−", x_load - 14, y_ret - 8, size=13)

    if schema.show_filter_capacitor:
        _wire(dwg, [(x_cap, y_m), (x_cap, (y_m + y_ret) / 2 - 5)])
        _wire(dwg, [(x_cap, (y_m + y_ret) / 2 + 5), (x_cap, y_ret)])
        _draw_capacitor_v(dwg, x_cap, (y_m + y_ret) / 2, schema.filter_capacitor_label)
        _dot(dwg, x_cap, y_m)
        _dot(dwg, x_cap, y_ret)
    return y_ret + 16


def _draw_bridge_rectifier(dwg, schema):
    x_s, y_t, y_b = 175, 90, 210
    # Diamond: L and R are the AC nodes, T is the + output, B the − output.
    Lx, Ly = 340, 150
    Tx, Ty = 430, 85
    Rx, Ry = 520, 150
    Bx, By = 430, 215
    y_out, y_ret, y_low = 50, 255, 295
    x_load, x_right, x_cap, y_cap_tie = 700, 620, 660, 110

    if schema.show_transformer:
        _draw_transformer(dwg, schema, 110, x_s, y_t, y_b)
    else:
        _draw_ac_source(dwg, x_s - 60, (y_t + y_b) / 2, 22, schema.input_label)
        _wire(dwg, [(x_s - 60, (y_t + y_b) / 2 - 22), (x_s - 60, y_t), (x_s, y_t)])
        _wire(dwg, [(x_s - 60, (y_t + y_b) / 2 + 22), (x_s - 60, y_b), (x_s, y_b)])

    # Secondary → the two AC nodes of the diamond.
    _wire(dwg, [(x_s, y_t), (240, y_t), (240, Ly), (Lx, Ly)])
    _wire(dwg, [(x_s, y_b), (x_s, y_low), (x_right, y_low), (x_right, Ly), (Rx, Ry)])

    # Every diode points toward T and away from B, so current through the load
    # runs T → load → B in BOTH half-cycles. Reversing any one of these four
    # shorts the secondary on one half-cycle and un-rectifies the output.
    if schema.show_diodes:
        _draw_diode(dwg, Lx, Ly, Tx, Ty, "D1", size=18, label_side=-1)
        _draw_diode(dwg, Rx, Ry, Tx, Ty, "D2", size=18, label_side=1)
        _draw_diode(dwg, Bx, By, Lx, Ly, "D3", size=18, label_side=1)
        _draw_diode(dwg, Bx, By, Rx, Ry, "D4", size=18, label_side=-1)
    else:
        for (p1, p2) in (((Lx, Ly), (Tx, Ty)), ((Rx, Ry), (Tx, Ty)),
                         ((Bx, By), (Lx, Ly)), ((Bx, By), (Rx, Ry))):
            _wire(dwg, [p1, p2])
    for (px, py) in ((Lx, Ly), (Tx, Ty), (Rx, Ry), (Bx, By)):
        _dot(dwg, px, py)

    # + from T over the top, − from B along a rail that hops the secondary's return leg
    _wire(dwg, [(Tx, Ty), (Tx, y_out), (x_load, y_out), (x_load, Ly)])
    _wire(dwg, [(Bx, By), (Bx, y_ret)])
    _hop_line_h(dwg, Bx, x_load, y_ret, hops=(x_right,))
    _draw_resistor_v(dwg, x_load, Ly + 26, y_ret - 26, schema.load_label)
    _wire(dwg, [(x_load, Ly), (x_load, Ly + 26)])
    _wire(dwg, [(x_load, y_ret - 26), (x_load, y_ret)])
    _text(dwg, "+", x_load - 14, Ly + 18, size=13)
    _text(dwg, "−", x_load - 14, y_ret - 8, size=13)

    if schema.show_filter_capacitor:
        # Tie to the + rail above the diamond: a tie at Ly would look collinear
        # with the AC-node wire at that height.
        _wire(dwg, [(x_cap, y_cap_tie), (x_load, y_cap_tie)])
        _wire(dwg, [(x_cap, y_cap_tie), (x_cap, (y_cap_tie + y_ret) / 2 - 5)])
        _wire(dwg, [(x_cap, (y_cap_tie + y_ret) / 2 + 5), (x_cap, y_ret)])
        _draw_capacitor_v(dwg, x_cap, (y_cap_tie + y_ret) / 2, schema.filter_capacitor_label)
        _dot(dwg, x_load, y_cap_tie)
        _dot(dwg, x_cap, y_ret)
    return y_low + 16


def _draw_waveform_panel(dwg, x, y, w, h, samples, title, bipolar):
    """One oscilloscope panel; y is the top of the plot area, samples have unit peak."""
    base = y + h / 2 if bipolar else y + h
    amp = (h / 2 - 6) if bipolar else (h - 8)
    _text(dwg, title, x, y - 8, anchor="start", size=12)
    dwg.add(dwg.line(start=(x, base), end=(x + w, base), stroke=STROKE, stroke_width=1.2))
    dwg.add(dwg.line(start=(x, y), end=(x, y + h), stroke=STROKE, stroke_width=1.2))
    _text(dwg, "V", x - 8, y + 8, anchor="end", size=11)
    _text(dwg, "t", x + w + 10, base + 4, anchor="start", size=11)
    n = len(samples) - 1
    pts = [(x + w * i / n, base - amp * v) for i, v in enumerate(samples)]
    dwg.add(dwg.polyline(points=pts, stroke=STROKE, fill="none", stroke_width=2))


# ── 8. Series / Parallel RLC (AC) ─────────────────────────────────────────────

_RLC_ORDER = [RLCComponentType.RESISTOR, RLCComponentType.INDUCTOR,
              RLCComponentType.CAPACITOR]
_RLC_SYMBOL = {RLCComponentType.RESISTOR: "R", RLCComponentType.INDUCTOR: "L",
               RLCComponentType.CAPACITOR: "C"}


def _impedance_formula(topology: RLCTopology, present) -> str:
    has_r = RLCComponentType.RESISTOR in present
    has_l = RLCComponentType.INDUCTOR in present
    has_c = RLCComponentType.CAPACITOR in present
    if topology == RLCTopology.SERIES:
        if has_r and has_l and has_c:
            return "Z = √(R² + (X_L − X_C)²),   X_L = ωL,  X_C = 1/ωC"
        if has_r and has_l:
            return "Z = √(R² + X_L²),   X_L = ωL"
        if has_r and has_c:
            return "Z = √(R² + X_C²),   X_C = 1/ωC"
        if has_l and has_c:
            return "Z = |X_L − X_C|,   X_L = ωL,  X_C = 1/ωC"
        if has_r:
            return "Z = R"
        return "Z = X_L = ωL" if has_l else "Z = X_C = 1/ωC"
    if has_r and has_l and has_c:
        return "1/Z = √((1/R)² + (1/X_L − 1/X_C)²),   X_L = ωL,  X_C = 1/ωC"
    if has_r and has_l:
        return "1/Z = √((1/R)² + (1/X_L)²),   X_L = ωL"
    if has_r and has_c:
        return "1/Z = √((1/R)² + (1/X_C)²),   X_C = 1/ωC"
    if has_l and has_c:
        return "1/Z = |1/X_L − 1/X_C|,   X_L = ωL,  X_C = 1/ωC"
    if has_r:
        return "Z = R"
    return "Z = X_L = ωL" if has_l else "Z = X_C = 1/ωC"


def _rlc_component_label(comp) -> str:
    base = comp.label or _RLC_SYMBOL[comp.type]
    return f"{base} = {comp.value}" if comp.value else base


def _draw_rlc_component(dwg, comp, cx, cy, w=44):
    if comp.type == RLCComponentType.RESISTOR:
        _draw_mini_resistor(dwg, cx, cy, w)
    elif comp.type == RLCComponentType.INDUCTOR:
        _draw_mini_inductor(dwg, cx, cy, w)
    else:
        _draw_mini_capacitor(dwg, cx, cy, w)


def render_rlc_circuit(data: Dict[str, Any], canvas_w: int = 800,
                       canvas_h: int = 600) -> str:
    schema = RLCCircuitSchema(**data)
    dwg = _base_drawing(canvas_w, canvas_h)
    arrow = _arrow_marker(dwg, "rlc_arrow")

    if schema.title:
        _text(dwg, schema.title, canvas_w / 2, 28, size=16)

    by_type = {c.type: c for c in schema.components}
    comps = [by_type[t] for t in _RLC_ORDER if t in by_type]

    if schema.topology == RLCTopology.SERIES:
        _draw_series_rlc(dwg, schema, comps, arrow, canvas_w)
    else:
        _draw_parallel_rlc(dwg, schema, comps, arrow, canvas_w)

    y = canvas_h - 74
    if schema.show_impedance_formula:
        _text(dwg, _impedance_formula(schema.topology, set(by_type)),
              canvas_w / 2, y, size=14)
        y += 26

    if schema.show_resonance:
        l_val = _parse_quantity(by_type[RLCComponentType.INDUCTOR].value) \
            if RLCComponentType.INDUCTOR in by_type else None
        c_val = _parse_quantity(by_type[RLCComponentType.CAPACITOR].value) \
            if RLCComponentType.CAPACITOR in by_type else None
        f0 = resonant_frequency(l_val, c_val)
        if f0 is not None:
            tail = ("Z is minimum (= R), I is maximum"
                    if schema.topology == RLCTopology.SERIES
                    else "Z is maximum, I is minimum")
            _text(dwg, f"Resonance:  f0 = 1/(2π√(LC)) = {_fmt_freq(f0)}   →   {tail}",
                  canvas_w / 2, y, size=14)
        else:
            _text(dwg, "Resonance:  f0 = 1/(2π√(LC))   (X_L = X_C)",
                  canvas_w / 2, y, size=14)

    return dwg.tostring()


def _draw_series_rlc(dwg, schema, comps, arrow, canvas_w):
    x_l, x_r = 150, 690
    y_t, y_b = 175, 405
    cy = (y_t + y_b) / 2

    _draw_ac_source(dwg, x_l, cy, 26,
                    schema.source_label if schema.show_ac_source else None)
    _wire(dwg, [(x_l, cy - 26), (x_l, y_t)])
    _wire(dwg, [(x_l, y_b), (x_l, cy + 26)])
    _wire(dwg, [(x_l, y_b), (x_r, y_b)])
    _wire(dwg, [(x_r, y_b), (x_r, y_t)])

    n = len(comps)
    span = x_r - x_l
    prev = x_l
    for i, comp in enumerate(comps):
        cx = x_l + span * (i + 1) / (n + 1)
        _wire(dwg, [(prev, y_t), (cx - 22, y_t)])
        _draw_rlc_component(dwg, comp, cx, y_t)
        _text(dwg, _rlc_component_label(comp), cx, y_t - 22, size=13)
        prev = cx + 22
    _wire(dwg, [(prev, y_t), (x_r, y_t)])

    if schema.show_current_direction:
        dwg.add(dwg.line(start=(x_l + 16, y_t - 34), end=(x_l + 66, y_t - 34),
                         stroke=STROKE, stroke_width=1.5, marker_end=arrow))
        _text(dwg, "I", x_l + 78, y_t - 30, anchor="start", size=13)


def _draw_parallel_rlc(dwg, schema, comps, arrow, canvas_w):
    x_src, x_a, x_b = 130, 300, 640
    y_top, y_bot = 130, 470          # source rails, clear of the bus ends
    n = len(comps)
    ys = [230 + i * 90 for i in range(n)]
    cy = (y_top + y_bot) / 2

    _draw_ac_source(dwg, x_src, cy, 26,
                    schema.source_label if schema.show_ac_source else None)
    # The source sits across the two buses: over the top to the right bus, under
    # the bottom back to the left bus. Each bus stops at its last branch node —
    # a bus overhanging past it would read as a dangling wire.
    _wire(dwg, [(x_src, cy - 26), (x_src, y_top), (x_b, y_top), (x_b, ys[-1])])
    _wire(dwg, [(x_src, cy + 26), (x_src, y_bot), (x_a, y_bot), (x_a, ys[0])])

    for comp, y in zip(comps, ys):
        cxm = (x_a + x_b) / 2
        _wire(dwg, [(x_a, y), (cxm - 22, y)])
        _draw_rlc_component(dwg, comp, cxm, y)
        _wire(dwg, [(cxm + 22, y), (x_b, y)])
        _text(dwg, _rlc_component_label(comp), cxm, y - 18, size=13)
        _dot(dwg, x_a, y)
        _dot(dwg, x_b, y)

    if schema.show_current_direction:
        dwg.add(dwg.line(start=(x_src + 40, y_top - 22), end=(x_src + 100, y_top - 22),
                         stroke=STROKE, stroke_width=1.5, marker_end=arrow))
        _text(dwg, "I", x_src + 112, y_top - 18, anchor="start", size=13)


# ── Orthogonal wiring + orientable component symbols ──────────────────────────
#
# Shared by the mesh network and the RC circuit: a component sits ON a wire, so
# the wire is drawn with a gap exactly where the symbol goes rather than being
# drawn under it.

_COMP_GAP = {
    "resistor": 46.0,
    "inductor": 44.0,
    "battery": 12.0,       # the wires end on the plates themselves
    "capacitor": 9.0,
    "ammeter": 36.0,
    "voltmeter": 36.0,
    "galvanometer": 36.0,
    "switch": 34.0,
}
_COMP_LABEL_OFF = {
    "resistor": 24.0, "inductor": 22.0, "battery": 30.0, "capacitor": 24.0,
    "ammeter": 26.0, "voltmeter": 26.0, "galvanometer": 26.0, "switch": 24.0,
}
_METER_LETTER = {"ammeter": "A", "voltmeter": "V", "galvanometer": "G"}


def _ctype(t) -> str:
    return getattr(t, "value", t)


def _place_label(dwg, label, cx, cy, nx, ny, off, size=13):
    """Put an upright label off the wire along its normal (nx, ny)."""
    if not label:
        return
    if abs(nx) > 0.5:
        _text(dwg, label, cx + nx * off, cy + 5,
              anchor="start" if nx > 0 else "end", size=size)
    else:
        _text(dwg, label, cx, cy + ny * off + (5 if ny > 0 else -3), size=size)


def _draw_oriented(dwg, ctype, cx, cy, ux, uy, label=None, reverse=False,
                   label_side=1, scale=1.0):
    """Draw one component symbol centred at (cx, cy) along the unit vector (ux, uy).

    The symbol body is rotated onto the wire; the label stays upright.
    """
    t = _ctype(ctype)
    gap = _COMP_GAP[t] * scale
    ang = math.degrees(math.atan2(uy, ux))
    nx, ny = uy, -ux                       # normal: "up" for a rightward wire
    lx, ly = nx * label_side, ny * label_side
    off = _COMP_LABEL_OFF[t]

    if t == "resistor":
        g = dwg.g(transform=f"rotate({ang:.2f},{cx:.2f},{cy:.2f})")
        g.add(dwg.rect(insert=(cx - gap / 2, cy - 9), size=(gap, 18),
                       stroke=STROKE, stroke_width=2, fill="white"))
        dwg.add(g)
    elif t == "inductor":
        g = dwg.g(transform=f"rotate({ang:.2f},{cx:.2f},{cy:.2f})")
        hump = gap / 4
        x = cx - gap / 2
        d = f"M {x:.1f},{cy:.1f}"
        for _ in range(4):
            d += f" A {hump / 2:.1f},{hump / 2 + 3:.1f} 0 0 1 {x + hump:.1f},{cy:.1f}"
            x += hump
        g.add(dwg.path(d=d, stroke=STROKE, fill="none", stroke_width=2))
        dwg.add(g)
    elif t == "capacitor":
        half = 13.0
        for s in (-1, 1):
            px, py = cx + ux * s * gap / 2, cy + uy * s * gap / 2
            dwg.add(dwg.line(start=(px - nx * half, py - ny * half),
                             end=(px + nx * half, py + ny * half),
                             stroke=STROKE, stroke_width=3))
    elif t == "battery":
        s_pos = -1 if reverse else 1       # + plate faces the "to" end unless reversed
        for (s, half, w) in ((s_pos, 16.0, 3), (-s_pos, 9.0, 2.4)):
            px, py = cx + ux * s * gap / 2, cy + uy * s * gap / 2
            dwg.add(dwg.line(start=(px - nx * half, py - ny * half),
                             end=(px + nx * half, py + ny * half),
                             stroke=STROKE, stroke_width=w))
        mx, my = -lx, -ly                  # polarity marks opposite the label
        for (s, sym) in ((s_pos, "+"), (-s_pos, "−")):
            _text(dwg, sym, cx + ux * s * 17 + mx * 13,
                  cy + uy * s * 17 + my * 13 + 4, size=12)
    elif t in _METER_LETTER:
        dwg.add(dwg.circle(center=(cx, cy), r=gap / 2, stroke=STROKE,
                           fill="white", stroke_width=2))
        _text(dwg, _METER_LETTER[t], cx, cy + 5, size=13)
        if label and label.strip() == _METER_LETTER[t]:
            label = None                   # the letter is already inside the circle
    elif t == "switch":
        for s in (-1, 1):
            _dot(dwg, cx + ux * s * gap / 2, cy + uy * s * gap / 2, 3)
        # open lever, hinged on the "from" contact
        hx, hy = cx - ux * gap / 2, cy - uy * gap / 2
        tipx = cx + ux * gap * 0.36 + nx * 14
        tipy = cy + uy * gap * 0.36 + ny * 14
        dwg.add(dwg.line(start=(hx, hy), end=(tipx, tipy),
                         stroke=STROKE, stroke_width=2))
    else:
        raise ValueError(f"Unknown component type: {t}")

    _place_label(dwg, label, cx, cy, lx, ly, off)


# ── Polyline arithmetic (arc-length parametrised) ─────────────────────────────

def _branch_segments(pts):
    segs, s = [], 0.0
    for p, q in zip(pts, pts[1:]):
        ln = math.hypot(q[0] - p[0], q[1] - p[1])
        if ln < 1e-6:
            continue
        segs.append({"s0": s, "s1": s + ln, "len": ln, "p": p, "q": q,
                     "ux": (q[0] - p[0]) / ln, "uy": (q[1] - p[1]) / ln})
        s += ln
    return segs, s


def _point_on(segs, s):
    for seg in segs:
        if s <= seg["s1"] + 1e-9:
            t = max(0.0, s - seg["s0"])
            return (seg["p"][0] + seg["ux"] * t, seg["p"][1] + seg["uy"] * t,
                    seg["ux"], seg["uy"])
    seg = segs[-1]
    return (seg["q"][0], seg["q"][1], seg["ux"], seg["uy"])


def _sub_polyline(segs, a, b):
    pts = [_point_on(segs, a)[:2]]
    for seg in segs:
        if a + 1e-6 < seg["s1"] < b - 1e-6:
            pts.append(seg["q"])
    pts.append(_point_on(segs, b)[:2])
    out = [pts[0]]
    for p in pts[1:]:
        if math.hypot(p[0] - out[-1][0], p[1] - out[-1][1]) > 1e-6:
            out.append(p)
    return out


def _emit_hop_path(dwg, pts, crossings=(), width=2, r=7.0):
    """Polyline; horizontal runs arc OVER any crossing listed in `crossings`.

    A hop, not a dot: two wires that merely cross are not connected, and drawing
    a junction dot there would describe a different circuit.
    """
    if len(pts) < 2:
        return
    d = f"M {pts[0][0]:.1f},{pts[0][1]:.1f}"
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        if abs(y1 - y2) < 0.5 and abs(x1 - x2) > 0.5:
            hops = [hx for (hx, hy) in crossings
                    if abs(hy - y1) < 0.5
                    and min(x1, x2) + r + 1 < hx < max(x1, x2) - r - 1]
            hops.sort(reverse=(x2 < x1))
            step = r if x2 > x1 else -r
            sweep = 1 if x2 > x1 else 0
            for hx in hops:
                d += f" L {hx - step:.1f},{y1:.1f}"
                d += f" A {r:.1f},{r:.1f} 0 0 {sweep} {hx + step:.1f},{y1:.1f}"
        d += f" L {x2:.1f},{y2:.1f}"
    dwg.add(dwg.path(d=d, stroke=STROKE, fill="none", stroke_width=width))


def _wire_with_gaps(dwg, pts, cuts, crossings=(), width=2):
    segs, total = _branch_segments(pts)
    if not segs:
        return
    keep, cur = [], 0.0
    for (a, b) in sorted(cuts):
        a, b = max(0.0, min(total, a)), max(0.0, min(total, b))
        if a > cur:
            keep.append((cur, a))
        cur = max(cur, b)
    if cur < total:
        keep.append((cur, total))
    for (a, b) in keep:
        if b - a < 0.6:
            continue
        _emit_hop_path(dwg, _sub_polyline(segs, a, b), crossings, width)
    return keep


def _allocate_components(slots, gaps, scale):
    """Give every component a slot it fully fits inside. None if impossible."""
    need = [g * scale + 8.0 for g in gaps]
    free = [s["len"] - 12.0 for s in slots]     # stay clear of the nodes/corners
    assign = [None] * len(gaps)
    for i in sorted(range(len(gaps)), key=lambda k: -need[k]):
        best, best_free = -1, -1.0
        for j, f in enumerate(free):
            if f >= need[i] and f > best_free:
                best, best_free = j, f
        if best < 0:
            return None
        assign[i] = best
        free[best] -= need[i]
    return assign


def _placement_slots(segs, avoid):
    """The straight runs of a branch, minus any stretch a component must not sit on."""
    slots = []
    for seg in segs:
        pieces = [(seg["s0"], seg["s1"])]
        for (a0, a1) in avoid:
            nxt = []
            for (p0, p1) in pieces:
                if a1 <= p0 or a0 >= p1:
                    nxt.append((p0, p1))
                    continue
                if a0 > p0:
                    nxt.append((p0, a0))
                if a1 < p1:
                    nxt.append((a1, p1))
            pieces = nxt
        for (p0, p1) in pieces:
            if p1 - p0 > 1e-6:
                slots.append({"s0": p0, "s1": p1, "len": p1 - p0,
                              "ux": seg["ux"], "uy": seg["uy"]})
    return slots


def _place_components(pts, ctypes, avoid=()):
    """Lay components out along a polyline: [(cx, cy, ux, uy, s0, s1, scale)]."""
    segs, _total = _branch_segments(pts)
    if not segs or not ctypes:
        return []
    gaps = [_COMP_GAP[_ctype(t)] for t in ctypes]
    slots = _placement_slots(segs, avoid) or _placement_slots(segs, ())

    assign, scale = None, 1.0
    for scale in (1.0, 0.85, 0.7, 0.55, 0.42):
        assign = _allocate_components(slots, gaps, scale)
        if assign is not None:
            break
    if assign is None:                          # branch too short: stack them anyway
        scale = 0.42
        longest = max(range(len(slots)), key=lambda j: slots[j]["len"])
        assign = [longest] * len(ctypes)

    out = [None] * len(ctypes)
    for j, slot in enumerate(slots):
        idxs = [i for i in range(len(ctypes)) if assign[i] == j]
        if not idxs:
            continue
        a, b = slot["s0"] + 6.0, slot["s1"] - 6.0
        used = sum(gaps[i] * scale for i in idxs)
        pad = max(0.0, (b - a) - used) / (len(idxs) + 1)
        cur = a + pad
        for i in idxs:
            g = gaps[i] * scale
            s = cur + g / 2
            x, y, ux, uy = _point_on(segs, s)
            out[i] = (x, y, ux, uy, s - g / 2, s + g / 2, scale)
            cur += g + pad
    return [o for o in out if o]


def _crossing_arclengths(pts, crossings, margin=36.0):
    """Arc-length stretches of this route that sit over a crossing.

    A component parked on a crossing straddles the other branch's wire, which
    reads as the two branches being connected there. They are not."""
    segs, _ = _branch_segments(pts)
    out = []
    for (cx, cy) in crossings:
        for seg in segs:
            (ax, ay), (bx, by) = seg["p"], seg["q"]
            if min(ax, bx) - 1 <= cx <= max(ax, bx) + 1 and \
               min(ay, by) - 1 <= cy <= max(ay, by) + 1:
                s = seg["s0"] + math.hypot(cx - ax, cy - ay)
                out.append((s - margin, s + margin))
    return out


# ── 9. Mesh circuit (general multi-loop / Kirchhoff network) ──────────────────

def _mesh_route(p, q, others, taken, centre):
    """Manhattan route p→q that avoids other nodes and never runs collinearly on
    top of a wire already drawn — two branches sharing a stretch of wire would be
    one branch, and the picture would state a circuit nobody asked for.

    Of the two elbows, the one whose corner falls furthest from the middle of the
    network is taken: that turns a diamond of nodes into a clean rectangle instead
    of folding every branch through the centre where the other branches already are.
    """
    (x1, y1), (x2, y2) = p, q
    if abs(x1 - x2) < 1.0 or abs(y1 - y2) < 1.0:
        return [p, q]

    elbows = [[p, (x2, y1), q], [p, (x1, y2), q]]
    elbows.sort(key=lambda c: -math.hypot(c[1][0] - centre[0], c[1][1] - centre[1]))
    cands = list(elbows)
    for f in (0.5, 0.35, 0.65, 0.25, 0.75):
        mx = x1 + (x2 - x1) * f
        my = y1 + (y2 - y1) * f
        cands.append([p, (mx, y1), (mx, y2), q])
        cands.append([p, (x1, my), (x2, my), q])

    clean = [c for c in cands if not _route_hits_node(c, others)]
    for c in clean:
        if not any(_routes_overlap(c, t) for t in taken):
            return c
    return clean[0] if clean else cands[0]


def _route_hits_node(pts, others):
    for (nx, ny) in others:
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            if min(ax, bx) - 1 <= nx <= max(ax, bx) + 1 and \
               min(ay, by) - 1 <= ny <= max(ay, by) + 1:
                # distance from the node to the (axis-aligned) segment
                if abs(ax - bx) < 1.0 and abs(nx - ax) < 2.0:
                    return True
                if abs(ay - by) < 1.0 and abs(ny - ay) < 2.0:
                    return True
    return False


def _axis_segments(pts):
    """[(orientation, fixed_coord, lo, hi)] for the axis-aligned runs of a route."""
    out = []
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        if abs(ay - by) < 0.5 and abs(ax - bx) > 0.5:
            out.append(("h", ay, min(ax, bx), max(ax, bx)))
        elif abs(ax - bx) < 0.5 and abs(ay - by) > 0.5:
            out.append(("v", ax, min(ay, by), max(ay, by)))
    return out


def _routes_overlap(a_pts, b_pts):
    for (o1, c1, s1, e1) in _axis_segments(a_pts):
        for (o2, c2, s2, e2) in _axis_segments(b_pts):
            if o1 == o2 and abs(c1 - c2) < 2.0 and \
                    min(e1, e2) - max(s1, s2) > 3.0:
                return True
    return False


def _mesh_crossings(routes):
    """Points where a horizontal run of one branch crosses a vertical run of
    another. These are NOT electrical junctions."""
    hs, vs = [], []
    for bi, pts in enumerate(routes):
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            if abs(ay - by) < 0.5 and abs(ax - bx) > 0.5:
                hs.append((bi, min(ax, bx), max(ax, bx), ay))
            elif abs(ax - bx) < 0.5 and abs(ay - by) > 0.5:
                vs.append((bi, ax, min(ay, by), max(ay, by)))
    out = []
    for (bi, x0, x1, y) in hs:
        for (bj, vx, y0, y1) in vs:
            if bi == bj:
                continue
            if x0 + 1 < vx < x1 - 1 and y0 + 1 < y < y1 - 1:
                out.append((vx, y))
    return sorted(set(out))


def _mesh_node_pixels(schema, canvas_w, canvas_h, pad=0.0):
    xs = [n.x for n in schema.nodes]
    ys = [n.y for n in schema.nodes]
    # `pad` reserves room for bowed parallel branches, which are drawn outside
    # the straight line joining their two nodes.
    left, right = 140.0 + pad, canvas_w - 140.0 - pad
    top = (110.0 if schema.title else 85.0) + pad
    bottom = canvas_h - 90.0 - pad
    span_x, span_y = max(xs) - min(xs), max(ys) - min(ys)
    px = {}
    for n in schema.nodes:
        x = (left + right) / 2 if span_x < 1e-9 else \
            left + (right - left) * (n.x - min(xs)) / span_x
        y = (top + bottom) / 2 if span_y < 1e-9 else \
            top + (bottom - top) * (n.y - min(ys)) / span_y
        px[n.id] = (round(x, 2), round(y, 2))
    return px


def render_mesh_circuit(data: Dict[str, Any], canvas_w: int = 800,
                        canvas_h: int = 600) -> str:
    schema = MeshCircuitSchema(**data)
    dwg = _base_drawing(canvas_w, canvas_h)
    arrow = _arrow_marker(dwg, "mesh_arrow")

    if schema.title:
        _text(dwg, schema.title, canvas_w / 2, 28, size=16)

    # Parallel branches between the same node pair must be bowed apart, or they
    # would be drawn on top of each other and read as one branch.
    by_pair: Dict[tuple, List[int]] = {}
    for i, b in enumerate(schema.branches):
        by_pair.setdefault(tuple(sorted((b.from_node, b.to_node))), []).append(i)
    rank = {}
    for idxs in by_pair.values():
        for k, i in enumerate(idxs):
            rank[i] = (k, len(idxs))

    max_par = max(len(v) for v in by_pair.values())
    pos = _mesh_node_pixels(schema, canvas_w, canvas_h,
                            pad=78.0 * (max_par - 1) / 2 + (14.0 if max_par > 1 else 0.0))

    centre = (sum(v[0] for v in pos.values()) / len(pos),
              sum(v[1] for v in pos.values()) / len(pos))
    routes: List[List[tuple]] = [None] * len(schema.branches)
    sides: List[int] = [1] * len(schema.branches)
    taken: List[List[tuple]] = []
    for i, b in enumerate(schema.branches):
        p, q = pos[b.from_node], pos[b.to_node]
        others = [v for nid, v in pos.items()
                  if nid not in (b.from_node, b.to_node)]
        k, cnt = rank[i]
        off = (k - (cnt - 1) / 2) * 78.0
        if cnt == 1 or abs(off) < 1e-6:
            routes[i] = _mesh_route(p, q, others, taken, centre)
        else:
            dx, dy = q[0] - p[0], q[1] - p[1]
            ln = math.hypot(dx, dy) or 1.0
            nx, ny = -dy / ln, dx / ln
            routes[i] = [p, (p[0] + nx * off, p[1] + ny * off),
                         (q[0] + nx * off, q[1] + ny * off), q]
            # Labels belong on the outside of the bow, away from the sibling branch.
            sides[i] = -1 if off > 0 else 1
        taken.append(routes[i])

    crossings = _mesh_crossings(routes)

    degree = {n.id: 0 for n in schema.nodes}
    leaving: Dict[str, List[tuple]] = {n.id: [] for n in schema.nodes}
    for i, b in enumerate(schema.branches):
        degree[b.from_node] += 1
        degree[b.to_node] += 1
        pts = routes[i]
        segs, _ = _branch_segments(pts)
        if segs:
            leaving[b.from_node].append((segs[0]["ux"], segs[0]["uy"]))
            leaving[b.to_node].append((-segs[-1]["ux"], -segs[-1]["uy"]))

    for i, b in enumerate(schema.branches):
        pts = routes[i]
        placed = _place_components(pts, [c.type for c in b.components],
                                   avoid=_crossing_arclengths(pts, crossings))
        cuts = [(p[4], p[5]) for p in placed]
        keep = _wire_with_gaps(dwg, pts, cuts, crossings)

        for comp, (cx, cy, ux, uy, _s0, _s1, sc) in zip(b.components, placed):
            lbl = comp.label or ""
            if comp.value:
                lbl = f"{lbl} = {comp.value}" if lbl else comp.value
            _draw_oriented(dwg, comp.type, cx, cy, ux, uy, lbl,
                           reverse=(comp.polarity == Polarity.REVERSE),
                           label_side=sides[i], scale=sc)

        if schema.show_currents and b.current_label and keep:
            _mesh_current_arrow(dwg, pts, keep, b, arrow, sides[i])

    for n in schema.nodes:
        px, py = pos[n.id]
        # Three or more branches meeting is a junction (dot). Exactly two is a
        # bend in a single wire and must NOT get one.
        if degree[n.id] >= 3:
            _dot(dwg, px, py)
        if schema.show_node_labels:
            _mesh_node_label(dwg, n.label or n.id, px, py, leaving[n.id])

    if schema.show_kvl_loops:
        for loop in schema.loops:
            _mesh_loop_arrow(dwg, loop, pos, arrow)

    return dwg.tostring()


def _mesh_node_label(dwg, label, px, py, dirs):
    """Put the label in the widest angular gap between the branches leaving the
    node — the mean direction points into a wire whenever the node has 3+."""
    if not dirs:
        _text(dwg, label, px, py - 14, size=13)
        return
    angs = sorted(math.atan2(d[1], d[0]) for d in dirs)
    if len(angs) == 1:
        mid = angs[0] + math.pi
    else:
        best, mid = -1.0, angs[0] + math.pi
        for i, a0 in enumerate(angs):
            a1 = angs[(i + 1) % len(angs)] + (2 * math.pi if i == len(angs) - 1 else 0)
            if a1 - a0 > best:
                best, mid = a1 - a0, (a0 + a1) / 2
    _text(dwg, label, px + 22 * math.cos(mid), py + 22 * math.sin(mid) + 5, size=13)


def _mesh_current_arrow(dwg, pts, keep, branch, arrow, side=1):
    """Arrow on the longest bare stretch of the branch, offset off the wire."""
    segs, _ = _branch_segments(pts)
    a, b = max(keep, key=lambda kv: kv[1] - kv[0])
    mid = (a + b) / 2
    x, y, ux, uy = _point_on(segs, mid)
    if branch.current_direction == CurrentDirection.REVERSE:
        ux, uy = -ux, -uy
    half = min(15.0, max(7.0, (b - a) / 3))
    nx, ny = uy * side, -ux * side
    ox, oy = nx * 13, ny * 13
    dwg.add(dwg.line(start=(x - ux * half + ox, y - uy * half + oy),
                     end=(x + ux * half + ox, y + uy * half + oy),
                     stroke=STROKE, stroke_width=1.5, marker_end=arrow))
    _place_label(dwg, branch.current_label, x + ox, y + oy, nx, ny, 16, size=12)


def _mesh_loop_arrow(dwg, loop, pos, arrow):
    ptsl = [pos[i] for i in loop.node_ids]
    if len(ptsl) == 2:
        # A two-node mesh is a pair of parallel branches; their components sit at
        # the halfway point, so the arrow goes between them but off to one side.
        (ax, ay), (bx, by) = ptsl
        cx, cy, r = ax + (bx - ax) * 0.28, ay + (by - ay) * 0.28, 30.0
    else:
        cx = sum(p[0] for p in ptsl) / len(ptsl)
        cy = sum(p[1] for p in ptsl) / len(ptsl)
        dmin = min(math.hypot(p[0] - cx, p[1] - cy) for p in ptsl)
        # Kept small: the arrow lives in the middle of the mesh, where the
        # component labels of the surrounding branches also reach.
        r = max(20.0, min(34.0, dmin * 0.35))

    th0 = math.radians(105.0)
    sweep_deg = 280.0
    sgn = 1.0 if loop.direction == LoopDirection.CW else -1.0   # screen y is down
    th1 = th0 + sgn * math.radians(sweep_deg)
    x0, y0 = cx + r * math.cos(th0), cy + r * math.sin(th0)
    x1, y1 = cx + r * math.cos(th1), cy + r * math.sin(th1)
    dwg.add(dwg.path(
        d=f"M {x0:.1f},{y0:.1f} A {r:.1f},{r:.1f} 0 1 "
          f"{1 if sgn > 0 else 0} {x1:.1f},{y1:.1f}",
        stroke=STROKE, fill="none", stroke_width=1.6, marker_end=arrow))
    _text(dwg, loop.label, cx, cy + 5, size=13)


# ── 10. Transistor amplifier ──────────────────────────────────────────────────

def amplifier_phase_shift_deg(configuration: AmplifierConfiguration) -> int:
    """Only the common-emitter stage inverts the signal. This 180° is the exam
    question; a CB or CC stage that claims inversion is simply wrong."""
    return 180 if configuration == AmplifierConfiguration.COMMON_EMITTER else 0


def amplifier_summary(configuration: AmplifierConfiguration) -> Dict[str, str]:
    return {
        AmplifierConfiguration.COMMON_EMITTER: {
            "input": "base", "output": "collector",
            "gain": "high voltage gain and high current gain",
        },
        AmplifierConfiguration.COMMON_BASE: {
            "input": "emitter", "output": "collector",
            "gain": "voltage gain > 1, current gain < 1",
        },
        AmplifierConfiguration.COMMON_COLLECTOR: {
            "input": "base", "output": "emitter",
            "gain": "voltage gain ≈ 1, high current gain (emitter follower)",
        },
    }[configuration]


def _draw_bjt(dwg, cx, cy, npn=True, r=27.0):
    """BJT symbol. Returns (base, collector, emitter) terminal points."""
    dwg.add(dwg.circle(center=(cx, cy), r=r, stroke=STROKE, fill="white",
                       stroke_width=2))
    bx = cx - 9
    dwg.add(dwg.line(start=(bx, cy - 15), end=(bx, cy + 15),
                     stroke=STROKE, stroke_width=3))
    base = (cx - r - 16, cy)
    dwg.add(dwg.line(start=(bx, cy), end=base, stroke=STROKE, stroke_width=2))

    lead_x = cx + 15
    dwg.add(dwg.line(start=(bx, cy - 10), end=(lead_x, cy - 22),
                     stroke=STROKE, stroke_width=2))
    coll = (lead_x, cy - r - 16)
    dwg.add(dwg.line(start=(lead_x, cy - 22), end=coll, stroke=STROKE, stroke_width=2))

    e1, e2 = (bx, cy + 10), (lead_x, cy + 22)
    dwg.add(dwg.line(start=e1, end=e2, stroke=STROKE, stroke_width=2))
    emit = (lead_x, cy + r + 16)
    dwg.add(dwg.line(start=e2, end=emit, stroke=STROKE, stroke_width=2))

    # NPN = Not Pointing iN: the emitter arrow points OUT of the device. A PNP
    # points back at the base. Flipping this arrow changes which device it is.
    dx, dy = e2[0] - e1[0], e2[1] - e1[1]
    ln = math.hypot(dx, dy)
    ux, uy = (dx / ln, dy / ln) if npn else (-dx / ln, -dy / ln)
    tx, ty = (e1[0] + dx * 0.80, e1[1] + dy * 0.80) if npn else \
             (e1[0] + dx * 0.24, e1[1] + dy * 0.24)
    nx, ny = -uy, ux
    dwg.add(dwg.polygon(points=[(tx, ty),
                                (tx - ux * 13 + nx * 5.2, ty - uy * 13 + ny * 5.2),
                                (tx - ux * 13 - nx * 5.2, ty - uy * 13 - ny * 5.2)],
                        fill=STROKE, stroke=STROKE, stroke_width=1))
    return base, coll, emit


def _draw_ground_symbol(dwg, x, y):
    for j in range(3):
        hw = 17 - j * 5
        dwg.add(dwg.line(start=(x - hw, y + 3 + j * 7), end=(x + hw, y + 3 + j * 7),
                         stroke=STROKE, stroke_width=2))


def _open_terminal(dwg, x, y):
    dwg.add(dwg.circle(center=(x, y), r=4.5, stroke=STROKE, fill="white",
                       stroke_width=2))


def render_transistor_amplifier(data: Dict[str, Any], canvas_w: int = 800,
                                canvas_h: int = 600) -> str:
    schema = TransistorAmplifierSchema(**data)
    dwg = _base_drawing(canvas_w, canvas_h)

    if schema.title:
        _text(dwg, schema.title, canvas_w / 2, 28, size=16)

    npn = schema.transistor_type == TransistorType.NPN
    cfg = schema.configuration
    y_vcc, y_gnd = 95.0, 465.0
    tx, ty = 430.0, 285.0
    base, coll, emit = _draw_bjt(dwg, tx, ty, npn)
    _text(dwg, "B", base[0] - 4, base[1] - 10, anchor="end", size=12)
    _text(dwg, "C", coll[0] + 10, coll[1] + 16, anchor="start", size=12)
    _text(dwg, "E", emit[0] + 10, emit[1] - 8, anchor="start", size=12)
    _text(dwg, "NPN" if npn else "PNP", tx + 78, ty + 5, anchor="start", size=12)

    bias = schema.show_biasing_resistors
    caps = schema.show_coupling_capacitors
    x_rb = 355.0
    x_c, x_e = coll[0], emit[0]
    taps = []                                   # x positions tapping the Vcc rail

    # ── Collector side ──
    if cfg == AmplifierConfiguration.COMMON_COLLECTOR:
        _wire(dwg, [(x_c, coll[1]), (x_c, y_vcc)])
        taps.append(x_c)
    elif bias:
        _draw_resistor_v(dwg, x_c, 135, 190, "RC")
        _wire(dwg, [(x_c, y_vcc), (x_c, 135)])
        _wire(dwg, [(x_c, 190), (x_c, coll[1])])
        taps.append(x_c)
    else:
        _wire(dwg, [(x_c, coll[1]), (x_c, y_vcc)])
        taps.append(x_c)

    # ── Base side ──
    if cfg == AmplifierConfiguration.COMMON_BASE:
        # RB biases the base off Vcc; the base is held at *signal* ground by C_B.
        # Tying the base straight to ground while RB feeds it from Vcc would pin
        # V_B at 0 and cut the transistor off — a picture of a dead amplifier.
        cb_bias = bias and caps
        _wire(dwg, [base, (x_rb, base[1])])
        if cb_bias:
            _draw_resistor_v(dwg, x_rb, 135, 190, "RB")
            _wire(dwg, [(x_rb, y_vcc), (x_rb, 135)])
            _wire(dwg, [(x_rb, 190), (x_rb, base[1])])
            taps.append(x_rb)
            _dot(dwg, x_rb, base[1])
            _wire(dwg, [(x_rb, base[1]), (x_rb, 430.5)])
            _draw_oriented(dwg, "capacitor", x_rb, 435, 0, 1, "C_B")
            _wire(dwg, [(x_rb, 439.5), (x_rb, y_gnd)])
        else:
            _wire(dwg, [(x_rb, base[1]), (x_rb, y_gnd)])
    else:
        _wire(dwg, [base, (325, base[1])])
        if bias:
            _draw_resistor_v(dwg, x_rb, 135, 190, "RB")
            _wire(dwg, [(x_rb, y_vcc), (x_rb, 135)])
            _wire(dwg, [(x_rb, 190), (x_rb, base[1])])
            taps.append(x_rb)
            _dot(dwg, x_rb, base[1])

    # ── Emitter side ──
    y_out_cc = 342.0
    if cfg == AmplifierConfiguration.COMMON_BASE:
        y_in = 390.0
        _wire(dwg, [(x_e, emit[1]), (x_e, y_in)])
        if bias:
            _draw_resistor_v(dwg, 290, 405, 445, "RE")
            _wire(dwg, [(290, y_in), (290, 405)])
            _wire(dwg, [(290, 445), (290, y_gnd)])
            _dot(dwg, 290, y_in)
            _dot(dwg, 290, y_gnd)
    elif cfg == AmplifierConfiguration.COMMON_COLLECTOR:
        if bias:
            _draw_resistor_v(dwg, x_e, 360, 415, "RE")
            _wire(dwg, [(x_e, emit[1]), (x_e, 360)])
            _wire(dwg, [(x_e, 415), (x_e, y_gnd)])
        else:
            _wire(dwg, [(x_e, emit[1]), (x_e, y_gnd)])
        _dot(dwg, x_e, y_gnd)
        _dot(dwg, x_e, y_out_cc)
    else:                                        # common emitter
        if bias:
            _draw_resistor_v(dwg, x_e, 360, 415, "RE")
            _wire(dwg, [(x_e, emit[1]), (x_e, 360)])
            _wire(dwg, [(x_e, 415), (x_e, y_gnd)])
            if caps:
                # CE bypass: shorts RE to signal frequencies, which is what gives
                # the stage its large voltage gain.
                _wire(dwg, [(x_e, 345), (530, 345), (530, 383)])
                _wire(dwg, [(530, 401), (530, 440), (x_e, 440)])
                _draw_oriented(dwg, "capacitor", 530, 392, 0, 1, "CE")
                _dot(dwg, x_e, 345)
                _dot(dwg, x_e, 440)
        else:
            _wire(dwg, [(x_e, emit[1]), (x_e, y_gnd)])
        _dot(dwg, x_e, y_gnd)

    # ── Vcc rail ──
    x_rail_l = min(taps) if taps else x_c
    x_rail_r = 660.0
    _wire(dwg, [(x_rail_l, y_vcc), (x_rail_r, y_vcc)])
    if len(taps) > 1:
        _dot(dwg, max(taps), y_vcc)
    if schema.show_supply:
        _open_terminal(dwg, x_rail_r, y_vcc)
        _text(dwg, f"+{schema.supply_label}", x_rail_r + 12, y_vcc + 5,
              anchor="start", size=13)

    # ── Ground rail ──
    _wire(dwg, [(200, y_gnd), (690, y_gnd)])
    _draw_ground_symbol(dwg, 600 if cfg == AmplifierConfiguration.COMMON_BASE else 330,
                        y_gnd)

    # ── Input / output ──
    if cfg == AmplifierConfiguration.COMMON_BASE:
        y_in = 390.0
        x_c1 = 245.0
        if caps:
            _hop_line_h(dwg, x_e, x_c1 + 4.5, y_in, hops=(x_rb,))
            _draw_oriented(dwg, "capacitor", x_c1, y_in, 1, 0, "C1")
            _wire(dwg, [(x_c1 - 4.5, y_in), (200, y_in)])
        else:
            _hop_line_h(dwg, x_e, 200, y_in, hops=(x_rb,))
        if schema.show_input_output:
            _draw_ac_source(dwg, 200, 428, 24, "Vin", label_dx=-32)
            _wire(dwg, [(200, y_in), (200, 404)])
            _wire(dwg, [(200, 452), (200, y_gnd)])
    else:
        x_c1 = 305.0
        if caps:
            _draw_oriented(dwg, "capacitor", x_c1, base[1], 1, 0, "C1")
            _wire(dwg, [(x_c1 + 4.5, base[1]), (325, base[1])])
            _wire(dwg, [(x_c1 - 4.5, base[1]), (215, base[1])])
        else:
            _wire(dwg, [(325, base[1]), (215, base[1])])
        if schema.show_input_output:
            _draw_ac_source(dwg, 215, 375, 24, "Vin", label_dx=-32)
            _wire(dwg, [(215, base[1]), (215, 351)])
            _wire(dwg, [(215, 399), (215, y_gnd)])

    y_out = y_out_cc if cfg == AmplifierConfiguration.COMMON_COLLECTOR else 215.0
    x_out_src = x_e if cfg == AmplifierConfiguration.COMMON_COLLECTOR else x_c
    if cfg != AmplifierConfiguration.COMMON_COLLECTOR:
        _dot(dwg, x_c, y_out)
    if caps:
        _wire(dwg, [(x_out_src, y_out), (555, y_out)])
        _draw_oriented(dwg, "capacitor", 560, y_out, 1, 0, "C2")
        _wire(dwg, [(564.5, y_out), (690, y_out)])
    else:
        _wire(dwg, [(x_out_src, y_out), (690, y_out)])
    if schema.show_input_output:
        _open_terminal(dwg, 690, y_out)
        _open_terminal(dwg, 690, y_gnd)
        _text(dwg, "Vout", 702, y_out + 5, anchor="start", size=13)

    # ── Phase relation (derived from the configuration, never from the params) ──
    phase = amplifier_phase_shift_deg(cfg)
    if schema.show_waveforms:
        n = 240
        v_in = [math.sin(2 * math.pi * 2 * i / n) for i in range(n + 1)]
        sign = -1.0 if phase == 180 else 1.0
        v_out = [sign * v for v in v_in]
        _draw_waveform_panel(dwg, 90, 505, 290, 66, v_in, "Vin", bipolar=True)
        _draw_waveform_panel(dwg, 430, 505, 290, 66, v_out,
                             f"Vout — {'inverted, 180° out of phase' if phase else 'in phase'}",
                             bipolar=True)
    elif schema.show_input_output:
        info = amplifier_summary(cfg)
        _text(dwg, f"{cfg.value.replace('_', '-')}: in at the {info['input']}, "
                   f"out at the {info['output']}", canvas_w / 2, canvas_h - 40, size=13)
        _text(dwg, f"Vout is {phase}° out of phase with Vin"
                   if phase else "Vout is in phase with Vin (no inversion)",
              canvas_w / 2, canvas_h - 16, size=14)

    return dwg.tostring()


# ── 11. Transformer ───────────────────────────────────────────────────────────

def transformer_solve(primary_turns=None, secondary_turns=None,
                      primary_voltage=None, secondary_voltage=None,
                      primary_current=None, secondary_current=None,
                      efficiency=None) -> Dict[str, Any]:
    """Ns/Np = Vs/Vp = Ip/Is. Returns the completed, self-consistent set.

    The turns ratio wins: if the supplied voltages disagree with the turns, the
    voltages are recomputed. An LLM that hands us Np=100, Ns=500, Vp=220, Vs=44
    has produced an impossible transformer, and printing its numbers would teach
    the mistake.
    """
    npr, nsec = primary_turns, secondary_turns
    vp = _parse_quantity(primary_voltage)
    vs = _parse_quantity(secondary_voltage)
    ip = _parse_quantity(primary_current)
    is_ = _parse_quantity(secondary_current)
    eta = None if efficiency is None else efficiency / 100.0

    ratio = None                                     # k = Ns/Np
    source = None
    if npr and nsec and npr > 0:
        ratio, source = nsec / npr, "turns"
    elif vp and vs and vp > 0:
        ratio, source = vs / vp, "voltages"
    elif ip and is_ and is_ > 0:
        ratio, source = ip / is_, "currents"

    recomputed = False
    if ratio:
        if vp and vs and abs(vs - vp * ratio) > 1e-6 * max(1.0, abs(vs)) \
                and source == "turns":
            vs, recomputed = vp * ratio, True
        elif vp and not vs:
            vs = vp * ratio
        elif vs and not vp:
            vp = vs / ratio
        if npr and not nsec:
            nsec = npr * ratio
        elif nsec and not npr:
            npr = nsec / ratio

        # Power: ideal Vp·Ip = Vs·Is; with efficiency, Vs·Is = η·Vp·Ip.
        k = eta if eta is not None else 1.0
        if ip and not is_:
            is_ = k * ip / ratio
        elif is_ and not ip:
            ip = is_ * ratio / k
        elif ip and is_:
            is_ = k * ip / ratio
            recomputed = True

    if ratio is None:
        kind = None
    elif ratio > 1.0 + 1e-9:
        kind = TransformerKind.STEP_UP
    elif ratio < 1.0 - 1e-9:
        kind = TransformerKind.STEP_DOWN
    else:
        kind = None                                  # 1:1 isolation transformer

    return {"primary_turns": npr, "secondary_turns": nsec,
            "primary_voltage": vp, "secondary_voltage": vs,
            "primary_current": ip, "secondary_current": is_,
            "ratio": ratio, "ratio_source": source, "kind": kind,
            "efficiency": eta, "recomputed": recomputed}


def _coil_humps(ratio: Optional[float]) -> Tuple[int, int]:
    """Turn counts for the drawing: the secondary must visibly have more turns on
    a step-up and fewer on a step-down, whatever the label claims."""
    if not ratio:
        return 5, 5
    if ratio > 1:
        return 4, int(max(5, min(9, round(4 * ratio))))
    return int(max(5, min(9, round(4 / ratio)))), 4


def _fmt_volt(v: float) -> str:
    return f"{v:.4g} V"


def _fmt_current(i: float) -> str:
    a = abs(i)
    if a >= 1:
        return f"{i:.4g} A"
    if a >= 1e-3:
        return f"{i * 1e3:.4g} mA"
    return f"{i * 1e6:.4g} µA"


def _fmt_turns(n: float) -> str:
    return f"{n:.0f}" if abs(n - round(n)) < 1e-9 else f"{n:.1f}"


def render_transformer(data: Dict[str, Any], canvas_w: int = 800,
                       canvas_h: int = 600) -> str:
    schema = TransformerSchema(**data)
    dwg = _base_drawing(canvas_w, canvas_h)
    arrow = _arrow_marker(dwg, "tf_arrow")

    if schema.title:
        _text(dwg, schema.title, canvas_w / 2, 28, size=16)

    sol = transformer_solve(schema.primary_turns, schema.secondary_turns,
                            schema.primary_voltage, schema.secondary_voltage,
                            schema.primary_current, schema.secondary_current,
                            schema.efficiency)
    kind = sol["kind"] or schema.transformer_type
    n_p, n_s = _coil_humps(sol["ratio"])

    x_l, x_r = 290.0, 510.0
    y_t, y_b = 140.0, 400.0
    limb = 28.0
    y_c1, y_c2 = 175.0, 365.0

    if schema.show_core:
        for (ix, iy, iw, ih) in ((x_l, y_t, x_r - x_l, y_b - y_t),
                                 (x_l + limb, y_t + limb,
                                  x_r - x_l - 2 * limb, y_b - y_t - 2 * limb)):
            dwg.add(dwg.rect(insert=(ix, iy), size=(iw, ih),
                             stroke=STROKE, fill="none", stroke_width=2))
        # laminations
        for k in (1, 2):
            dx = x_l + limb * k / 3
            dwg.add(dwg.line(start=(dx, y_t), end=(dx, y_b),
                             stroke=STROKE, stroke_width=0.8))
            dx = x_r - limb * k / 3
            dwg.add(dwg.line(start=(dx, y_t), end=(dx, y_b),
                             stroke=STROKE, stroke_width=0.8))
            dy = y_t + limb * k / 3
            dwg.add(dwg.line(start=(x_l, dy), end=(x_r, dy),
                             stroke=STROKE, stroke_width=0.8))
            dy = y_b - limb * k / 3
            dwg.add(dwg.line(start=(x_l, dy), end=(x_r, dy),
                             stroke=STROKE, stroke_width=0.8))
        _text(dwg, "laminated iron core", (x_l + x_r) / 2, y_b + 26, size=11)

    _draw_coil_v(dwg, x_l, y_c1, y_c2, n_p, bulge=-1)
    _draw_coil_v(dwg, x_r, y_c1, y_c2, n_s, bulge=1)

    # Primary: AC source. Secondary: load.
    _draw_ac_source(dwg, 155, 270, 26,
                    "Vp = " + (_fmt_volt(sol["primary_voltage"])
                               if sol["primary_voltage"] else "Vp"),
                    label_dx=-34)
    _wire(dwg, [(x_l, y_c1), (155, y_c1), (155, 244)])
    _wire(dwg, [(155, 296), (155, y_c2), (x_l, y_c2)])

    _draw_resistor_v(dwg, 660, 240, 300, "Load")
    _wire(dwg, [(x_r, y_c1), (660, y_c1), (660, 240)])
    _wire(dwg, [(660, 300), (660, y_c2), (x_r, y_c2)])
    _text(dwg, "Vs = " + (_fmt_volt(sol["secondary_voltage"])
                          if sol["secondary_voltage"] else "Vs"),
          628, 274, anchor="end", size=13)

    _text(dwg, "Np" + (f" = {_fmt_turns(sol['primary_turns'])}"
                       if sol["primary_turns"] else ""), 232, 425, size=13)
    _text(dwg, "Ns" + (f" = {_fmt_turns(sol['secondary_turns'])}"
                       if sol["secondary_turns"] else ""), 568, 425, size=13)
    if sol["primary_current"]:
        _text(dwg, f"Ip = {_fmt_current(sol['primary_current'])}",
              121, 322, anchor="end", size=12)
    if sol["secondary_current"]:
        _text(dwg, f"Is = {_fmt_current(sol['secondary_current'])}",
              628, 300, anchor="end", size=12)

    if schema.show_flux_direction and schema.show_core:
        y_mid_t, y_mid_b = y_t + limb / 2, y_b - limb / 2
        dwg.add(dwg.line(start=(370, y_mid_t), end=(432, y_mid_t), stroke=STROKE,
                         stroke_width=1.6, marker_end=arrow))
        dwg.add(dwg.line(start=(432, y_mid_b), end=(370, y_mid_b), stroke=STROKE,
                         stroke_width=1.6, marker_end=arrow))
        _text(dwg, "Φ", 452, y_mid_t + 4, size=13)
        _text(dwg, "Φ", 350, y_mid_b + 4, size=13)

    y = canvas_h - 130
    if schema.show_turns_ratio:
        if sol["ratio"]:
            label = ("STEP-UP" if kind == TransformerKind.STEP_UP else
                     "STEP-DOWN" if kind == TransformerKind.STEP_DOWN else
                     "1:1 (isolation)")
            _text(dwg, f"Turns ratio  Ns/Np = {sol['ratio']:.4g}   →   "
                       f"{label} transformer", canvas_w / 2, y, size=15)
        else:
            _text(dwg, "Turns ratio  Ns/Np = Vs/Vp = Ip/Is",
                  canvas_w / 2, y, size=15)
        y += 26

    if schema.show_equations:
        _text(dwg, "Vs/Vp = Ns/Np = Ip/Is", canvas_w / 2, y, size=14)
        y += 24
        if sol["ratio"] and sol["primary_voltage"] and sol["secondary_voltage"]:
            _text(dwg, f"Vs = Vp × (Ns/Np) = {_fmt_volt(sol['primary_voltage'])}"
                       f" × {sol['ratio']:.4g} = {_fmt_volt(sol['secondary_voltage'])}",
                  canvas_w / 2, y, size=14)
            y += 24

    if sol["efficiency"] is not None:
        pin = (sol["primary_voltage"] or 0) * (sol["primary_current"] or 0)
        tail = ""
        if pin:
            tail = (f":  P_in = {pin:.4g} W,  "
                    f"P_out = {sol['efficiency'] * pin:.4g} W")
        _text(dwg, f"η = P_out/P_in = {schema.efficiency:.4g}%{tail}",
              canvas_w / 2, y, size=14)

    return dwg.tostring()


# ── 12. RC circuit (charging / discharging) ───────────────────────────────────

def rc_time_constant(r_ohm: float, c_farad: float) -> float:
    """τ = RC, in seconds."""
    if not r_ohm or not c_farad or r_ohm <= 0 or c_farad <= 0:
        raise ValueError("R and C must both be positive to define a time constant")
    return r_ohm * c_farad


def rc_value(mode: RCMode, quantity: RCGraphQuantity, x: float) -> float:
    """Normalised value at t = x·τ.

    The CURRENT decays exponentially while charging *and* while discharging —
    this is the step students reliably get wrong. Only V and Q rise on charge.
    """
    if quantity == RCGraphQuantity.CURRENT:
        return math.exp(-x)
    if mode == RCMode.DISCHARGING:
        return math.exp(-x)
    return 1.0 - math.exp(-x)


def rc_curve(mode: RCMode, quantity: RCGraphQuantity, n: int = 300,
             span: float = 5.0) -> Tuple[List[float], List[float]]:
    """(x = t/τ, normalised value). For mode=both the key is thrown at t = 5τ."""
    if mode != RCMode.BOTH:
        xs = [span * i / n for i in range(n + 1)]
        return xs, [rc_value(mode, quantity, x) for x in xs]

    xs, ys = [], []
    v_end = rc_value(RCMode.CHARGING, quantity, span)
    for i in range(n + 1):
        x = 2 * span * i / n
        if x <= span:
            ys.append(rc_value(RCMode.CHARGING, quantity, x))
        elif quantity == RCGraphQuantity.CURRENT:
            # The discharge current runs the other way round the loop.
            ys.append(-math.exp(-(x - span)))
        else:
            ys.append(v_end * math.exp(-(x - span)))
        xs.append(x)
    return xs, ys


def _fmt_time(t: float) -> str:
    if t >= 1.0:
        return f"{t:.4g} s"
    if t >= 1e-3:
        return f"{t * 1e3:.4g} ms"
    if t >= 1e-6:
        return f"{t * 1e6:.4g} µs"
    return f"{t:.3g} s"


_RC_SYMBOL = {RCGraphQuantity.VOLTAGE: ("V", "V0"),
              RCGraphQuantity.CHARGE: ("Q", "Q0"),
              RCGraphQuantity.CURRENT: ("I", "I0")}


def _rc_equation(mode: RCMode, q: RCGraphQuantity) -> str:
    sym, sym0 = _RC_SYMBOL[q]
    if q == RCGraphQuantity.CURRENT:
        return f"{sym} = {sym0} e^(−t/RC)      (decays while charging AND discharging)"
    if mode == RCMode.DISCHARGING:
        return f"{sym} = {sym0} e^(−t/RC)"
    if mode == RCMode.BOTH:
        return (f"charge: {sym} = {sym0}(1 − e^(−t/RC))     "
                f"discharge: {sym} = {sym0} e^(−t/RC)")
    return f"{sym} = {sym0}(1 − e^(−t/RC))"


def render_rc_circuit(data: Dict[str, Any], canvas_w: int = 800,
                      canvas_h: int = 600) -> str:
    schema = RCCircuitSchema(**data)
    dwg = _base_drawing(canvas_w, canvas_h)

    if schema.title:
        _text(dwg, schema.title, canvas_w / 2, 28, size=16)

    r_val = _parse_quantity(schema.resistance)
    c_val = _parse_quantity(schema.capacitance)
    e_val = _parse_quantity(schema.emf)
    tau = None
    if r_val and c_val and r_val > 0 and c_val > 0:
        tau = rc_time_constant(r_val, c_val)

    x_l, x_r = 170.0, 600.0
    y_t, y_b = 110.0, 280.0
    x_bypass = 95.0
    both = schema.mode == RCMode.BOTH

    r_lbl = f"R = {schema.resistance}" if schema.resistance else "R"
    c_lbl = f"C = {schema.capacitance}" if schema.capacitance else "C"

    # Top rail with R
    _wire(dwg, [(x_l, y_t), (362, y_t)])
    _draw_oriented(dwg, "resistor", 385, y_t, 1, 0, r_lbl)
    _wire(dwg, [(408, y_t), (x_r, y_t)])

    # Right rail with C
    _wire(dwg, [(x_r, y_t), (x_r, 190.5)])
    _draw_oriented(dwg, "capacitor", x_r, 195, 0, 1, c_lbl)
    _wire(dwg, [(x_r, 199.5), (x_r, y_b)])

    _wire(dwg, [(x_r, y_b), (x_l, y_b)])

    # Left rail: emf (unless we are only discharging) and the key
    has_cell = schema.mode != RCMode.DISCHARGING
    e_lbl = f"E = {schema.emf}" if schema.emf else "E"
    if has_cell:
        _wire(dwg, [(x_l, y_b), (x_l, 236)])
        if schema.show_switch:
            _draw_oriented(dwg, "switch", x_l, 219, 0, -1,
                           "K1" if both else "K", label_side=1)
            _wire(dwg, [(x_l, 202), (x_l, 166)])
        else:
            _wire(dwg, [(x_l, 236), (x_l, 166)])
        _draw_oriented(dwg, "battery", x_l, 160, 0, -1, e_lbl, label_side=-1)
        _wire(dwg, [(x_l, 154), (x_l, y_t)])
    else:
        if schema.show_switch:
            _wire(dwg, [(x_l, y_b), (x_l, 212)])
            _draw_oriented(dwg, "switch", x_l, 195, 0, -1, "K", label_side=1)
            _wire(dwg, [(x_l, 178), (x_l, y_t)])
        else:
            _wire(dwg, [(x_l, y_b), (x_l, y_t)])

    if both:
        # Second key shorts the source out: closing it discharges C through R.
        _wire(dwg, [(x_l, y_t), (x_bypass, y_t), (x_bypass, 178)])
        _draw_oriented(dwg, "switch", x_bypass, 195, 0, 1, "K2", label_side=-1)
        _wire(dwg, [(x_bypass, 212), (x_bypass, y_b), (x_l, y_b)])
        _dot(dwg, x_l, y_t)
        _dot(dwg, x_l, y_b)

    if schema.mode == RCMode.DISCHARGING:
        _text(dwg, "+Q", x_r - 22, 187, anchor="end", size=12)
        _text(dwg, "−Q", x_r - 22, 210, anchor="end", size=12)

    y = 318.0
    if schema.show_time_constant:
        if tau:
            _text(dwg, f"Time constant  τ = RC = {schema.resistance} × "
                       f"{schema.capacitance} = {_fmt_time(tau)}",
                  canvas_w / 2, y, size=14)
        else:
            _text(dwg, "Time constant  τ = RC", canvas_w / 2, y, size=14)
        y += 22

    if schema.mode == RCMode.DISCHARGING and e_val:
        _text(dwg, f"C is initially charged to V0 = {_fmt_volt(e_val)}",
              canvas_w / 2, y, size=13)

    if schema.show_graph:
        _draw_rc_graph(dwg, schema, canvas_w, canvas_h)

    return dwg.tostring()


def _draw_rc_graph(dwg, schema, canvas_w, canvas_h):
    q = schema.graph_quantity
    mode = schema.mode
    sym, sym0 = _RC_SYMBOL[q]
    bipolar = (mode == RCMode.BOTH and q == RCGraphQuantity.CURRENT)

    gx0, gx1 = 190.0, 720.0
    gy0, gy1 = 386.0, 560.0
    base = (gy0 + gy1) / 2 if bipolar else gy1
    amp = (gy1 - gy0) / 2 - 8 if bipolar else (gy1 - gy0) - 10

    _text(dwg, _rc_equation(mode, q), (gx0 + gx1) / 2, gy0 - 16, size=13)

    dwg.add(dwg.line(start=(gx0, gy0 - 4), end=(gx0, gy1 + 4),
                     stroke=STROKE, stroke_width=1.4))
    dwg.add(dwg.line(start=(gx0, base), end=(gx1 + 8, base),
                     stroke=STROKE, stroke_width=1.4))
    _text(dwg, sym, gx0 - 8, gy0 - 8, anchor="end", size=13)
    _text(dwg, "t", gx1 + 16, base + 5, anchor="start", size=13)

    xs, ys = rc_curve(mode, q)
    x_max = xs[-1]
    px = lambda x: gx0 + (gx1 - gx0) * x / x_max
    py = lambda v: base - amp * v

    # Asymptote / initial value
    dwg.add(dwg.line(start=(gx0, py(1.0)), end=(gx1, py(1.0)), stroke=STROKE,
                     stroke_width=1, stroke_dasharray="5,4"))
    _text(dwg, sym0, gx0 - 12, py(1.0) + 5, anchor="end", size=12)

    dwg.add(dwg.polyline(points=[(px(x), py(v)) for x, v in zip(xs, ys)],
                         stroke=STROKE, fill="none", stroke_width=2.2))

    n_tau = int(round(x_max))
    for k in range(1, n_tau + 1):
        tx = px(k)
        dwg.add(dwg.line(start=(tx, base - 4), end=(tx, base + 4),
                         stroke=STROKE, stroke_width=1.2))
        _text(dwg, "τ" if k == 1 else f"{k}τ", tx, base + 19, size=11)

    if schema.mark_time_constants:
        for k in (1, 2, 3):
            v = rc_value(RCMode.CHARGING if mode == RCMode.BOTH else mode, q, float(k))
            tx, tyv = px(k), py(v)
            dwg.add(dwg.line(start=(tx, base), end=(tx, tyv), stroke=STROKE,
                             stroke_width=1, stroke_dasharray="4,3"))
            dwg.add(dwg.line(start=(gx0, tyv), end=(tx, tyv), stroke=STROKE,
                             stroke_width=1, stroke_dasharray="4,3"))
            _dot(dwg, tx, tyv, 3)
            _text(dwg, f"{v * 100:.1f}%", tx + 8, tyv - 10, anchor="start", size=11)


# ── 13. Galvanometer conversion (ammeter / voltmeter) ─────────────────────────

def ammeter_shunt(g_ohm: float, ig_amp: float, i_amp: float) -> float:
    """Shunt in PARALLEL: S = Ig·G/(I − Ig)."""
    if g_ohm <= 0 or ig_amp <= 0:
        raise ValueError("G and Ig must be positive")
    if i_amp <= ig_amp:
        raise ValueError(
            f"target range {i_amp} A must exceed the full-scale current {ig_amp} A; "
            "a shunt cannot lower the range")
    return ig_amp * g_ohm / (i_amp - ig_amp)


def voltmeter_series_resistance(g_ohm: float, ig_amp: float, v_volt: float) -> float:
    """Multiplier in SERIES: R = V/Ig − G."""
    if g_ohm <= 0 or ig_amp <= 0:
        raise ValueError("G and Ig must be positive")
    r = v_volt / ig_amp - g_ohm
    if r <= 0:
        raise ValueError(
            f"target range {v_volt} V is not above Ig·G = {ig_amp * g_ohm} V; "
            "no series resistance can extend the range downwards")
    return r


def render_galvanometer_conversion(data: Dict[str, Any], canvas_w: int = 800,
                                   canvas_h: int = 600) -> str:
    schema = GalvanometerConversionSchema(**data)
    dwg = _base_drawing(canvas_w, canvas_h)
    arrow = _arrow_marker(dwg, "gc_arrow")

    if schema.title:
        _text(dwg, schema.title, canvas_w / 2, 28, size=16)

    g = _parse_quantity(schema.galvanometer_resistance)
    ig = _parse_quantity(schema.full_scale_current)
    target = _parse_quantity(schema.target_range)

    cy = 250.0
    x0, x1 = 120.0, 690.0

    if schema.conversion == GalvanometerConversionType.TO_AMMETER:
        _draw_gc_ammeter(dwg, schema, g, ig, target, cy, x0, x1, arrow, canvas_w)
    elif schema.conversion == GalvanometerConversionType.TO_VOLTMETER:
        _draw_gc_voltmeter(dwg, schema, g, ig, target, cy, x0, x1, arrow, canvas_w)
    else:
        _draw_gc_plain(dwg, schema, g, ig, cy, x0, x1, arrow, canvas_w)

    return dwg.tostring()


def _g_label(g: Optional[float]) -> str:
    return f"G = {_fmt_ohm(g)}" if g else "G"


def _draw_gc_plain(dwg, schema, g, ig, cy, x0, x1, arrow, canvas_w):
    _wire(dwg, [(x0, cy), (382, cy)])
    _draw_meter(dwg, 400, cy, "G", r=26)
    _wire(dwg, [(418, cy), (x1, cy)])
    _open_terminal(dwg, x0, cy)
    _open_terminal(dwg, x1, cy)
    _text(dwg, _g_label(g), 400, cy + 48, size=13)
    if ig:
        _text(dwg, f"Ig = {_fmt_current(ig)} (full-scale deflection)",
              400, cy - 44, size=13)
    dwg.add(dwg.line(start=(150, cy - 22), end=(210, cy - 22), stroke=STROKE,
                     stroke_width=1.5, marker_end=arrow))
    _text(dwg, "I", 180, cy - 30, size=12)
    if schema.show_formula:
        _text(dwg, "A galvanometer alone: it deflects full-scale at Ig and has "
                   "resistance G.", canvas_w / 2, 470, size=14)
        _text(dwg, "Shunt S in PARALLEL → ammeter.   High R in SERIES → voltmeter.",
              canvas_w / 2, 500, size=14)


def _draw_gc_ammeter(dwg, schema, g, ig, target, cy, x0, x1, arrow, canvas_w):
    s_val = ammeter_shunt(g, ig, target) if (g and ig and target) else None

    xa, xb = 250.0, 550.0
    y_g, y_s = 180.0, 330.0

    _wire(dwg, [(x0, cy), (xa, cy)])
    _wire(dwg, [(xb, cy), (x1, cy)])
    _open_terminal(dwg, x0, cy)
    _open_terminal(dwg, x1, cy)

    # Galvanometer branch (upper) and shunt branch (lower), in PARALLEL: the two
    # branches share both end nodes. In series the meter would read nothing like
    # the full current — the whole conversion depends on this being parallel.
    _wire(dwg, [(xa, cy), (xa, y_g), (374, y_g)])
    _draw_meter(dwg, 400, y_g, "G", r=26)
    _wire(dwg, [(426, y_g), (xb, y_g), (xb, cy)])
    _text(dwg, _g_label(g), 400, y_g - 38, size=13)

    if schema.show_shunt:
        _wire(dwg, [(xa, cy), (xa, y_s), (377, y_s)])
        _draw_oriented(dwg, "resistor", 400, y_s, 1, 0,
                       f"S = {_fmt_ohm(s_val)}" if s_val else "S (shunt)",
                       label_side=-1)
        _wire(dwg, [(423, y_s), (xb, y_s), (xb, cy)])
        _text(dwg, "shunt (low resistance, in parallel)", 400, y_s + 46, size=11)

    _dot(dwg, xa, cy)
    _dot(dwg, xb, cy)

    dwg.add(dwg.line(start=(150, cy - 18), end=(210, cy - 18), stroke=STROKE,
                     stroke_width=1.5, marker_end=arrow))
    _text(dwg, f"I = {_fmt_current(target)}" if target else "I", 180, cy - 26, size=12)
    if ig:
        _text(dwg, f"Ig = {_fmt_current(ig)}", 310, y_g - 8, size=12)
    if ig and target:
        _text(dwg, f"I − Ig = {_fmt_current(target - ig)}", 300, y_s - 14, size=12)

    if schema.show_formula:
        _text(dwg, "Shunt S is in PARALLEL with G:   S = Ig·G / (I − Ig)",
              canvas_w / 2, 440, size=15)
        if s_val is not None:
            _text(dwg, f"S = ({ig:.6g} × {g:.6g}) / ({target:.6g} − {ig:.6g}) "
                       f"= {_fmt_ohm(s_val)}", canvas_w / 2, 468, size=14)
            r_a = g * s_val / (g + s_val)
            _text(dwg, f"Resistance of the ammeter  R_A = G·S/(G + S) = {_fmt_ohm(r_a)}"
                       f"   (very small, so it barely disturbs the circuit)",
                  canvas_w / 2, 494, size=13)


def _draw_gc_voltmeter(dwg, schema, g, ig, target, cy, x0, x1, arrow, canvas_w):
    r_val = voltmeter_series_resistance(g, ig, target) if (g and ig and target) else None

    _wire(dwg, [(x0, cy), (274, cy)])
    _draw_meter(dwg, 300, cy, "G", r=26)
    _text(dwg, _g_label(g), 300, cy - 40, size=13)

    if schema.show_series_resistance:
        # In SERIES with G: the same Ig flows through both, so the pair reads V
        # across whatever it is connected across. In parallel it would be a shunt.
        _wire(dwg, [(326, cy), (447, cy)])
        _draw_oriented(dwg, "resistor", 470, cy, 1, 0,
                       f"R = {_fmt_ohm(r_val)}" if r_val else "R (series)")
        _wire(dwg, [(493, cy), (x1, cy)])
        _text(dwg, "high resistance, in series", 470, cy + 34, size=11)
    else:
        _wire(dwg, [(326, cy), (x1, cy)])

    _open_terminal(dwg, x0, cy)
    _open_terminal(dwg, x1, cy)
    dwg.add(dwg.line(start=(150, cy - 18), end=(210, cy - 18), stroke=STROKE,
                     stroke_width=1.5, marker_end=arrow))
    if ig:
        _text(dwg, f"Ig = {_fmt_current(ig)}", 180, cy - 26, size=12)
    if target:
        dwg.add(dwg.line(start=(x0, cy + 90), end=(x1, cy + 90), stroke=STROKE,
                         stroke_width=1, stroke_dasharray="5,4"))
        _wire(dwg, [(x0, cy), (x0, cy + 90)], width=1)
        _wire(dwg, [(x1, cy), (x1, cy + 90)], width=1)
        _text(dwg, f"V = {_fmt_volt(target)} (full-scale)",
              (x0 + x1) / 2, cy + 110, size=13)

    if schema.show_formula:
        _text(dwg, "R is in SERIES with G:   R = V/Ig − G",
              canvas_w / 2, 460, size=15)
        if r_val is not None:
            _text(dwg, f"R = {target:.6g}/{ig:.6g} − {g:.6g} = {_fmt_ohm(r_val)}",
                  canvas_w / 2, 488, size=14)
            _text(dwg, f"Resistance of the voltmeter  R_V = G + R = {_fmt_ohm(g + r_val)}"
                       f"   (very large, so it draws almost no current)",
                  canvas_w / 2, 514, size=13)


# ── 14. Electromagnetic machine (generator / motor) ──────────────────────────

def em_ring_type(machine: EMMachineType) -> str:
    """The commutation hardware is fixed by the machine, not by the params.

    An AC generator taps the coil through two full SLIP RINGS (the connection to
    the external circuit never breaks, so the sinusoidal EMF reaches the load with
    its sign intact). A DC generator and a DC motor use a SPLIT-RING commutator:
    the single ring is split in two, and the halves swap brushes every half turn —
    that reversal is exactly what rectifies a DC generator's output and what keeps
    a DC motor's torque one-directional.
    """
    return "slip_rings" if machine == EMMachineType.AC_GENERATOR else "split_ring"


def em_is_motor(machine: EMMachineType) -> bool:
    return machine == EMMachineType.DC_MOTOR


def em_waveform(machine: EMMachineType, cycles: float = 2.0,
                n: int = 360) -> List[float]:
    """Trace shown under a GENERATOR: a pure sinusoid for the AC generator, the
    same sinusoid full-wave rectified (|sin|) for the DC generator, because the
    split ring flips every negative half-cycle up. A motor has no output trace."""
    out = []
    for i in range(n + 1):
        v = math.sin(2.0 * math.pi * cycles * i / n)
        out.append(v if machine == EMMachineType.AC_GENERATOR else abs(v))
    return out


def _draw_slip_rings(dwg, cx, cy):
    """Two complete rings side by side on the shaft — the AC-generator tap.

    Returns (brush_left_terminal, brush_right_terminal)."""
    r = 26.0
    ring1x, ring2x = cx - 34, cx + 34
    for rx in (ring1x, ring2x):
        dwg.add(dwg.ellipse(center=(rx, cy), r=(13, r),
                            stroke=STROKE, fill="white", stroke_width=2))
    # Brushes press on the outer edge of each ring.
    b_l = (ring1x - 13, cy)
    b_r = (ring2x + 13, cy)
    for (bx, by, sgn) in ((b_l[0], b_l[1], -1), (b_r[0], b_r[1], 1)):
        dwg.add(dwg.rect(insert=(bx + (0 if sgn > 0 else -12), by - 7),
                         size=(12, 14), stroke=STROKE, fill="#555", stroke_width=1))
    _text(dwg, "two slip rings", cx, cy + r + 20, size=11)
    return (b_l[0] - 12, cy), (b_r[0] + 12, cy)


def _draw_split_ring(dwg, cx, cy):
    """One ring split into two half-segments by a diametral gap — the commutator.

    Returns (brush_left_terminal, brush_right_terminal)."""
    r = 30.0
    gap = 5.0
    # Two half-rings (left segment and right segment) separated by a vertical gap.
    dwg.add(dwg.path(
        d=f"M {cx - gap:.1f},{cy - r:.1f} A {r:.1f},{r:.1f} 0 0 0 "
          f"{cx - gap:.1f},{cy + r:.1f} L {cx - gap:.1f},{cy - r:.1f} Z",
        stroke=STROKE, fill="white", stroke_width=2))
    dwg.add(dwg.path(
        d=f"M {cx + gap:.1f},{cy - r:.1f} A {r:.1f},{r:.1f} 0 0 1 "
          f"{cx + gap:.1f},{cy + r:.1f} L {cx + gap:.1f},{cy - r:.1f} Z",
        stroke=STROKE, fill="white", stroke_width=2))
    # The two brushes contact the segments at the sides.
    for sgn in (-1, 1):
        bx = cx + sgn * r
        dwg.add(dwg.rect(insert=(bx + (0 if sgn > 0 else -12), cy - 7),
                         size=(12, 14), stroke=STROKE, fill="#555", stroke_width=1))
    _text(dwg, "split-ring commutator", cx, cy + r + 18, size=11)
    return (cx - r - 12, cy), (cx + r + 12, cy)


def render_em_machine(data: Dict[str, Any], canvas_w: int = 800,
                      canvas_h: int = 600) -> str:
    schema = EMMachineSchema(**data)
    dwg = _base_drawing(canvas_w, canvas_h)
    arrow = _arrow_marker(dwg, "em_arrow")

    if schema.title:
        _text(dwg, schema.title, canvas_w / 2, 28, size=16)

    machine = schema.machine
    motor = em_is_motor(machine)
    ring = em_ring_type(machine)

    # ── Magnet poles ──
    pole_y0, pole_y1 = 120.0, 300.0
    n_x, s_x = 110.0, 490.0
    pole_w = 46.0
    dwg.add(dwg.rect(insert=(n_x - pole_w, pole_y0), size=(pole_w, pole_y1 - pole_y0),
                     stroke=STROKE, fill="#eee", stroke_width=2))
    dwg.add(dwg.rect(insert=(s_x, pole_y0), size=(pole_w, pole_y1 - pole_y0),
                     stroke=STROKE, fill="#eee", stroke_width=2))
    _text(dwg, "N", n_x - pole_w / 2, (pole_y0 + pole_y1) / 2 + 6, size=20)
    _text(dwg, "S", s_x + pole_w / 2, (pole_y0 + pole_y1) / 2 + 6, size=20)

    # ── Magnetic field N → S ──
    if schema.show_flux:
        for k in range(4):
            fy = pole_y0 + 26 + k * (pole_y1 - pole_y0 - 52) / 3
            dwg.add(dwg.line(start=(n_x + 6, fy), end=(s_x - 8, fy),
                             stroke="#3366aa", stroke_width=1.4, marker_end=arrow))
        _text(dwg, "B (field)", s_x - 6, pole_y0 + 12, anchor="end", size=12)

    # ── Rectangular coil ABCD in the field ──
    cx0, cx1 = 250.0, 350.0
    cy0, cy1 = 150.0, 270.0
    _wire(dwg, [(cx0, cy0), (cx1, cy0), (cx1, cy1), (cx0, cy1), (cx0, cy0)], width=2.6)
    _text(dwg, "A", cx0 - 12, cy0 - 4, size=12)
    _text(dwg, "B", cx1 + 12, cy0 - 4, size=12)
    _text(dwg, "C", cx1 + 12, cy1 + 14, size=12)
    _text(dwg, "D", cx0 - 12, cy1 + 14, size=12)
    _text(dwg, "armature coil", (cx0 + cx1) / 2, cy1 + 20, size=11)

    # ── Force / EMF direction on the two active (vertical) arms ──
    if schema.show_force_directions:
        # AD arm (left) and BC arm (right) carry current across the field; the
        # forces on them are opposite, producing the couple that turns a motor
        # (or, for a generator, the arm motion that induces the EMF).
        dwg.add(dwg.line(start=(cx0, (cy0 + cy1) / 2 + 22),
                         end=(cx0, (cy0 + cy1) / 2 - 22),
                         stroke="#b30000", stroke_width=2, marker_end=arrow))
        dwg.add(dwg.line(start=(cx1, (cy0 + cy1) / 2 - 22),
                         end=(cx1, (cy0 + cy1) / 2 + 22),
                         stroke="#b30000", stroke_width=2, marker_end=arrow))
        _text(dwg, "F", cx0 - 12, (cy0 + cy1) / 2 - 24, size=12)
        _text(dwg, "F", cx1 + 12, (cy0 + cy1) / 2 + 30, size=12)
        rule = ("Fleming's LEFT-hand rule (force on the coil)" if motor
                else "Fleming's RIGHT-hand rule (induced current)")
        _text(dwg, rule, (cx0 + cx1) / 2, 118, size=11)

    # ── Shaft from the coil down to the ring assembly ──
    ring_cx, ring_cy = 300.0, 390.0
    _wire(dwg, [(cx0, cy1), (cx0, 360), (ring_cx - 20, 360), (ring_cx - 20, ring_cy)])
    _wire(dwg, [(cx1, cy1), (cx1, 345), (ring_cx + 20, 345), (ring_cx + 20, ring_cy)])

    if ring == "slip_rings":
        b_l, b_r = _draw_slip_rings(dwg, ring_cx, ring_cy)
    else:
        b_l, b_r = _draw_split_ring(dwg, ring_cx, ring_cy)

    # ── External circuit through the brushes ──
    y_ext = 500.0
    if schema.show_brushes:
        _wire(dwg, [b_l, (b_l[0], y_ext)])
        _wire(dwg, [b_r, (b_r[0], y_ext)])
        if motor:
            # A MOTOR is DRIVEN: a battery pushes current in, and the coil turns.
            _wire(dwg, [(b_l[0], y_ext), (250, y_ext)])
            _draw_cell_h(dwg, 300, y_ext, "supply")
            _wire(dwg, [(345, y_ext), (b_r[0], y_ext)])
            dwg.add(dwg.line(start=(220, y_ext + 24), end=(280, y_ext + 24),
                             stroke=STROKE, stroke_width=1.5, marker_end=arrow))
            _text(dwg, "I (driven in)", 250, y_ext + 40, size=11)
        else:
            # A GENERATOR is TURNED: the coil is rotated and an EMF is induced,
            # driving current through the external load.
            _wire(dwg, [(b_l[0], y_ext), (240, y_ext)])
            _draw_meter(dwg, 300, y_ext, "G")
            _wire(dwg, [(320, y_ext), (b_r[0], y_ext)])
            _text(dwg, "external load", 300, y_ext + 34, size=11)

    # ── Role caption ──
    role = ("DC MOTOR — current is driven IN; the coil feels a torque and rotates"
            if machine == EMMachineType.DC_MOTOR else
            "AC GENERATOR — the coil is turned; a sinusoidal EMF is induced"
            if machine == EMMachineType.AC_GENERATOR else
            "DC GENERATOR — the coil is turned; the split ring rectifies the EMF")
    _text(dwg, role, canvas_w / 2, 78, size=13)

    # rotation sense marker (ASCII only — arrow glyphs tofu in the PDF pipeline)
    _text(dwg, f"rotation: {schema.rotation.value}", 640, 360, size=11)

    # ── Output waveform (generators only) ──
    if schema.show_output_waveform and not motor:
        samples = em_waveform(machine)
        bip = (machine == EMMachineType.AC_GENERATOR)
        title = ("Induced EMF (sinusoidal)" if bip
                 else "Output EMF (rectified humps — split ring)")
        _draw_waveform_panel(dwg, 560, 150, 200, 120, samples, title, bipolar=bip)

    return dwg.tostring()


# ── 15. Combinational logic (multi-gate, multi-output) ────────────────────────

def _combinational_netlist(schema: LogicCombinationalSchema):
    """Return (inputs, gates, conns, outputs) for a named block or the netlist.

    inputs  : [(id, label)]
    gates   : [(id, GateType)]
    conns   : [(from_id, to_id, index)]
    outputs : [(label, source_gate_id)]
    """
    c = schema.circuit
    G = GateType
    if c == CombinationalCircuit.NETLIST:
        inputs = [(i.id, i.label) for i in schema.inputs]
        gates = [(g.id, g.gate_type) for g in schema.gates]
        conns = [(cn.from_id, cn.to_id, cn.to_input_index) for cn in schema.connections]
        outputs = [(o.label, o.id) for o in schema.outputs]
        return inputs, gates, conns, outputs

    if c == CombinationalCircuit.HALF_ADDER:
        inputs = [("A", "A"), ("B", "B")]
        gates = [("XOR1", G.XOR), ("AND1", G.AND)]
        conns = [("A", "XOR1", 0), ("B", "XOR1", 1),
                 ("A", "AND1", 0), ("B", "AND1", 1)]
        outputs = [("Sum", "XOR1"), ("Carry", "AND1")]
    elif c == CombinationalCircuit.FULL_ADDER:
        inputs = [("A", "A"), ("B", "B"), ("Cin", "Cin")]
        gates = [("XOR1", G.XOR), ("AND1", G.AND),
                 ("XOR2", G.XOR), ("AND2", G.AND), ("OR1", G.OR)]
        conns = [("A", "XOR1", 0), ("B", "XOR1", 1),
                 ("A", "AND1", 0), ("B", "AND1", 1),
                 ("XOR1", "XOR2", 0), ("Cin", "XOR2", 1),
                 ("XOR1", "AND2", 0), ("Cin", "AND2", 1),
                 ("AND1", "OR1", 0), ("AND2", "OR1", 1)]
        outputs = [("Sum", "XOR2"), ("Carry", "OR1")]
    elif c == CombinationalCircuit.HALF_SUBTRACTOR:
        inputs = [("A", "A"), ("B", "B")]
        gates = [("XOR1", G.XOR), ("NOT1", G.NOT), ("AND1", G.AND)]
        # Borrow = A'·B
        conns = [("A", "XOR1", 0), ("B", "XOR1", 1),
                 ("A", "NOT1", 0),
                 ("NOT1", "AND1", 0), ("B", "AND1", 1)]
        outputs = [("Diff", "XOR1"), ("Borrow", "AND1")]
    elif c == CombinationalCircuit.MUX_2TO1:
        inputs = [("I0", "I0"), ("I1", "I1"), ("S", "S")]
        gates = [("NOT1", G.NOT), ("AND1", G.AND), ("AND2", G.AND), ("OR1", G.OR)]
        # Y = I0·S' + I1·S
        conns = [("S", "NOT1", 0),
                 ("I0", "AND1", 0), ("NOT1", "AND1", 1),
                 ("I1", "AND2", 0), ("S", "AND2", 1),
                 ("AND1", "OR1", 0), ("AND2", "OR1", 1)]
        outputs = [("Y", "OR1")]
    else:
        raise ValueError(f"no builtin netlist for {c}")

    if schema.output_labels:
        outputs = [(schema.output_labels[i] if i < len(schema.output_labels)
                    else outputs[i][0], outputs[i][1])
                   for i in range(len(outputs))]
    return inputs, gates, conns, outputs


def _eval_gate_netlist(input_ids, gates, conns, assignment):
    """Evaluate an acyclic gate netlist. Returns (values, incoming, order)."""
    gate_type = dict(gates)
    incoming = {gid: [] for gid, _ in gates}
    for (f, t, idx) in conns:
        incoming[t].append((f, idx))
    for gid in incoming:
        idxed = sorted((c for c in incoming[gid] if c[1] is not None),
                       key=lambda c: c[1])
        rest = [c for c in incoming[gid] if c[1] is None]
        incoming[gid] = idxed + rest
    gate_ids = [gid for gid, _ in gates]
    resolved = set(input_ids)
    order, remaining = [], list(gate_ids)
    while remaining:
        ready = [g for g in remaining
                 if all(f in resolved for (f, _) in incoming[g])]
        if not ready:
            raise ValueError("combinational netlist contains a cycle")
        for g in ready:
            order.append(g)
            resolved.add(g)
            remaining.remove(g)
    vals = dict(assignment)
    for gid in order:
        vals[gid] = _gate_eval(gate_type[gid], [vals[f] for (f, _) in incoming[gid]])
    return vals, incoming, order


def combinational_truth_table(inputs, gates, conns, outputs):
    """The truth table, computed by evaluating the netlist for every input row."""
    input_ids = [i[0] for i in inputs]
    n = len(input_ids)
    headers = [lbl for _, lbl in inputs] + [lbl for lbl, _ in outputs]
    rows = []
    for combo in range(2 ** n):
        bits = [(combo >> (n - 1 - k)) & 1 for k in range(n)]
        vals, _, _ = _eval_gate_netlist(input_ids, gates, conns, dict(zip(input_ids, bits)))
        rows.append(bits + [vals[src] for _, src in outputs])
    return headers, rows


def sr_latch_truth_table():
    """SR (NOR) latch table, found by settling Q = NOR(R, Q'), Q' = NOR(S, Q) from
    both possible initial states. A determinate input drives both start states to
    the same steady state; S=R=0 leaves two stable states (HOLD); S=R=1 forces
    Q=Q'=0 (FORBIDDEN). Nothing here is hand-written — it is simulated."""
    headers = ["S", "R", "Q", "Q'"]
    rows, notes = [], []
    for S in (0, 1):
        for R in (0, 1):
            states = set()
            for q0 in (0, 1):
                q, qb = q0, 1 - q0
                for _ in range(20):
                    q = int(not (R or qb))
                    qb = int(not (S or q))
                states.add((q, qb))
            if len(states) > 1:
                rows.append([S, R, "Q0", "Q0'"])
                notes.append("hold")
            else:
                q, qb = next(iter(states))
                rows.append([S, R, q, qb])
                notes.append("forbidden" if q == qb else "set" if q else "reset")
    return headers, rows, notes


def _draw_combinational_netlist(dwg, inputs, gates, conns, outputs,
                                canvas_w, canvas_h, table):
    """Layout: inputs left, gates in topological columns, outputs right."""
    _, incoming, order = _eval_gate_netlist(
        [i[0] for i in inputs], gates, conns,
        {i[0]: 0 for i in inputs})

    circuit_right = canvas_w * 0.55 if table else canvas_w - 60

    level = {iid: 0 for iid, _ in inputs}
    for gid in order:
        level[gid] = 1 + max((level[f] for (f, _) in incoming[gid]), default=0)
    max_level = max((level[g] for g, _ in gates), default=1)

    left_x = 95.0
    x_out_col = circuit_right - 24            # every output ends on this column
    spacing = (x_out_col - left_x - 80) / max(1, max_level)
    spacing = max(80.0, min(160.0, spacing))

    top, bottom = 60.0, canvas_h - 55.0
    region_h = bottom - top
    n_in = len(inputs)

    pos_y = {}
    for i, (iid, _) in enumerate(inputs):
        pos_y[iid] = top + region_h * (i + 1) / (n_in + 1)

    by_level = {}
    for gid, _ in gates:
        by_level.setdefault(level[gid], []).append(gid)
    for lv in sorted(by_level):
        glist = by_level[lv]
        for gid in glist:
            src = [pos_y[f] for (f, _) in incoming[gid]]
            pos_y[gid] = sum(src) / len(src) if src else region_h / 2
        glist.sort(key=lambda g: pos_y[g])
        min_gap = GATE_H + 34
        for j in range(1, len(glist)):
            if pos_y[glist[j]] - pos_y[glist[j - 1]] < min_gap:
                pos_y[glist[j]] = pos_y[glist[j - 1]] + min_gap
        overflow = pos_y[glist[-1]] - (bottom - GATE_H / 2)
        if overflow > 0:
            for gid in glist:
                pos_y[gid] -= overflow

    out_pt = {}
    for iid, label in inputs:
        y = pos_y[iid]
        _text(dwg, label, left_x - 48, y + 5, anchor="end", size=14)
        dwg.add(dwg.line(start=(left_x - 42, y), end=(left_x, y),
                         stroke=STROKE, stroke_width=2))
        out_pt[iid] = (left_x, y)

    gate_type = dict(gates)
    in_pts = {}
    for gid, _ in gates:
        gx = left_x + level[gid] * spacing - 10
        pins, o = _draw_logic_gate(dwg, gate_type[gid], gx, pos_y[gid],
                                   len(incoming[gid]), None)
        in_pts[gid] = pins
        out_pt[gid] = o

    fanout = {}
    for (f, t, idx) in conns:
        fanout[f] = fanout.get(f, 0) + 1
    for gid, _ in gates:
        for k, (f, _idx) in enumerate(incoming[gid]):
            sx, sy = out_pt[f]
            tx, ty = in_pts[gid][k]
            mx = sx + (tx - sx) * 0.45
            dwg.add(dwg.polyline(points=[(sx, sy), (mx, sy), (mx, ty), (tx, ty)],
                                 stroke=STROKE, fill="none", stroke_width=2))
            if fanout.get(f, 0) > 1:
                _dot(dwg, sx, sy, 3)

    # Route every output to a common right column, spreading the label heights so
    # two outputs at the same gate height do not print on top of each other.
    info = sorted(([label, out_pt[src][0], out_pt[src][1]] for (label, src) in outputs),
                  key=lambda r: r[2])
    tys = [r[2] for r in info]
    for i in range(1, len(tys)):
        if tys[i] - tys[i - 1] < 30:
            tys[i] = tys[i - 1] + 30
    for (label, ox, oy), ty in zip(info, tys):
        dwg.add(dwg.line(start=(ox, oy), end=(x_out_col, oy),
                         stroke=STROKE, stroke_width=2))
        if abs(ty - oy) > 0.5:
            dwg.add(dwg.line(start=(x_out_col, oy), end=(x_out_col, ty),
                             stroke=STROKE, stroke_width=2))
        _text(dwg, label, x_out_col + 8, ty + 5, anchor="start", size=14)

    if table:
        headers, rows = table
        col_w = max(40, 12 + 9 * max(len(str(h)) for h in headers))
        tbl_w = col_w * len(headers)
        tbl_h = 22 * (len(rows) + 1)
        region_l = circuit_right + 40
        tx = region_l + max(0.0, (canvas_w - 24 - region_l - tbl_w) / 2)
        ty = max(top, (canvas_h - tbl_h) / 2)
        _draw_truth_table(dwg, headers, rows, tx, ty)


def _draw_sr_latch(dwg, schema, canvas_w, canvas_h):
    """Cross-coupled NOR latch drawn by hand (it has feedback, so no topo layout).

    NOR1: inputs R and Q' (feedback) → Q.   NOR2: inputs S and Q (feedback) → Q'."""
    y1, y2 = 220.0, 340.0
    gx = 300.0
    pins1, o1 = _draw_logic_gate(dwg, GateType.NOR, gx, y1, 2, None)  # -> Q
    pins2, o2 = _draw_logic_gate(dwg, GateType.NOR, gx, y2, 2, None)  # -> Q'

    # External inputs: R to the top of NOR1, S to the bottom of NOR2.
    _text(dwg, "R", 150, pins1[0][1] + 5, anchor="end", size=14)
    _wire(dwg, [(158, pins1[0][1]), pins1[0]])
    _text(dwg, "S", 150, pins2[1][1] + 5, anchor="end", size=14)
    _wire(dwg, [(158, pins2[1][1]), pins2[1]])

    # Outputs.
    _wire(dwg, [o1, (o1[0] + 150, o1[1])])
    _text(dwg, "Q", o1[0] + 158, o1[1] + 5, anchor="start", size=14)
    _wire(dwg, [o2, (o2[0] + 150, o2[1])])
    _text(dwg, "Q'", o2[0] + 158, o2[1] + 5, anchor="start", size=14)

    # Cross-coupling: Q (o1) feeds NOR2's upper input; Q' (o2) feeds NOR1's lower.
    x_fb1 = o1[0] + 110          # Q tap
    x_fb2 = o2[0] + 130          # Q' tap
    _dot(dwg, x_fb1, o1[1])
    _dot(dwg, x_fb2, o2[1])
    _wire(dwg, [(x_fb1, o1[1]), (x_fb1, 285), (250, 285), (250, pins2[0][1]),
                pins2[0]])
    _wire(dwg, [(x_fb2, o2[1]), (x_fb2, 400), (235, 400), (235, pins1[1][1]),
                pins1[1]])

    _text(dwg, "SR latch (cross-coupled NOR gates)", canvas_w / 2, canvas_h - 130,
          size=12)

    if schema.show_truth_table:
        headers, rows, notes = sr_latch_truth_table()
        _draw_truth_table(dwg, headers, rows, 560, 175)
        _text(dwg, "Q0 = no change (hold)", 620, 320, size=10)
        _text(dwg, "S=R=1 forbidden (Q=Q'=0)", 620, 338, size=10)


def render_logic_combinational(data: Dict[str, Any], canvas_w: int = 800,
                               canvas_h: int = 600) -> str:
    schema = LogicCombinationalSchema(**data)
    dwg = _base_drawing(canvas_w, canvas_h)

    title = schema.title or {
        CombinationalCircuit.HALF_ADDER: "Half Adder",
        CombinationalCircuit.FULL_ADDER: "Full Adder",
        CombinationalCircuit.HALF_SUBTRACTOR: "Half Subtractor",
        CombinationalCircuit.MUX_2TO1: "2-to-1 Multiplexer",
        CombinationalCircuit.SR_LATCH: "SR Latch",
        CombinationalCircuit.NETLIST: "",
    }[schema.circuit]
    if title:
        _text(dwg, title, canvas_w / 2, 28, size=16)

    if schema.circuit == CombinationalCircuit.SR_LATCH:
        _draw_sr_latch(dwg, schema, canvas_w, canvas_h)
        return dwg.tostring()

    inputs, gates, conns, outputs = _combinational_netlist(schema)
    table = (combinational_truth_table(inputs, gates, conns, outputs)
             if schema.show_truth_table and len(inputs) <= 4 else None)
    _draw_combinational_netlist(dwg, inputs, gates, conns, outputs,
                                canvas_w, canvas_h, table)
    return dwg.tostring()


# ── 16. Zener voltage regulator ───────────────────────────────────────────────

def zener_clamp(vin_samples: List[float], vz: float) -> List[float]:
    """Regulated output: clamped to Vz whenever the input exceeds it, otherwise it
    just follows the input (the Zener is out of breakdown and does nothing)."""
    return [min(v, vz) for v in vin_samples]


def _draw_zener_v(dwg, cx, y_top, y_bot, label=None):
    """Zener diode on a vertical wire, cathode (bent bar) UP, anode (triangle) DOWN.

    Reverse bias in a regulator = cathode positive: the + rail feeds the top, so
    the cathode sits at the higher potential and the diode conducts in breakdown.
    """
    my = (y_top + y_bot) / 2
    tri = 13.0
    # Anode lead up to the triangle base, triangle apex points UP to the cathode.
    _wire(dwg, [(cx, y_bot), (cx, my + tri / 2)])
    dwg.add(dwg.polygon(
        points=[(cx - tri * 0.72, my + tri / 2), (cx + tri * 0.72, my + tri / 2),
                (cx, my - tri / 2)],
        stroke=STROKE, fill=STROKE, stroke_width=1))
    # Bent-cathode bar just above the apex.
    bar_y = my - tri / 2
    b = tri * 0.72
    dwg.add(dwg.line(start=(cx - b, bar_y), end=(cx + b, bar_y),
                     stroke=STROKE, stroke_width=2.6))
    # The two Z-bends that distinguish a Zener from an ordinary diode.
    dwg.add(dwg.line(start=(cx - b, bar_y), end=(cx - b, bar_y + 6),
                     stroke=STROKE, stroke_width=2.6))
    dwg.add(dwg.line(start=(cx + b, bar_y), end=(cx + b, bar_y - 6),
                     stroke=STROKE, stroke_width=2.6))
    _wire(dwg, [(cx, y_top), (cx, bar_y)])
    if label:
        _text(dwg, label, cx - b - 10, my + 4, anchor="end", size=13)


def render_zener_regulator(data: Dict[str, Any], canvas_w: int = 800,
                           canvas_h: int = 600) -> str:
    schema = ZenerRegulatorSchema(**data)
    dwg = _base_drawing(canvas_w, canvas_h)
    arrow = _arrow_marker(dwg, "zr_arrow")

    if schema.title:
        _text(dwg, schema.title, canvas_w / 2, 28, size=16)

    vz = _parse_quantity(schema.zener_voltage)
    vin = _parse_quantity(schema.input_voltage)

    x_in, x_z, x_load = 150.0, 430.0, 620.0
    y_t, y_b = 130.0, 380.0

    # Unregulated source on the left.
    _draw_cell_h(dwg, x_in, (y_t + y_b) / 2, None)
    _text(dwg, "Vin = " + (schema.input_voltage or "Vin") + " (unregulated)",
          x_in, (y_t + y_b) / 2 - 34, size=12)
    _wire(dwg, [(x_in, (y_t + y_b) / 2 - 16), (x_in, y_t)])
    _wire(dwg, [(x_in, (y_t + y_b) / 2 + 16), (x_in, y_b)])
    _text(dwg, "+", x_in - 14, y_t + 22, size=12)
    _text(dwg, "−", x_in - 14, y_b - 10, size=12)

    # Series resistor Rs on the top rail.
    _wire(dwg, [(x_in, y_t), (262, y_t)])
    _draw_oriented(dwg, "resistor", 300, y_t, 1, 0, f"Rs = {schema.series_resistance}")
    _wire(dwg, [(338, y_t), (x_z, y_t)])

    # Zener in reverse across the rails.
    _draw_zener_v(dwg, x_z, y_t, y_b, f"Dz (Vz = {schema.zener_voltage})")
    _dot(dwg, x_z, y_t)
    _dot(dwg, x_z, y_b)

    # Load across the output (in parallel with the Zener).
    if schema.show_load:
        _wire(dwg, [(x_z, y_t), (x_load, y_t)])
        _draw_resistor_v(dwg, x_load, y_t + 26, y_b - 26, schema.load_label)
        _wire(dwg, [(x_load, y_t), (x_load, y_t + 26)])
        _wire(dwg, [(x_load, y_b - 26), (x_load, y_b)])
        _text(dwg, "+", x_load - 14, y_t + 20, size=12)
        _text(dwg, "−", x_load - 14, y_b - 8, size=12)
    # Bottom rail.
    _wire(dwg, [(x_in, y_b), ((x_load if schema.show_load else x_z), y_b)])
    _text(dwg, "Vout = Vz (regulated)", (x_z + (x_load if schema.show_load else x_z)) / 2,
          y_b + 26, size=12)

    if schema.show_current_labels:
        dwg.add(dwg.line(start=(190, y_t - 16), end=(240, y_t - 16),
                         stroke=STROKE, stroke_width=1.5, marker_end=arrow))
        _text(dwg, "Is", 215, y_t - 22, size=12)
        dwg.add(dwg.line(start=(x_z, 175), end=(x_z, 220),
                         stroke=STROKE, stroke_width=1.5, marker_end=arrow))
        _text(dwg, "Iz", x_z + 12, 200, anchor="start", size=12)
        if schema.show_load:
            dwg.add(dwg.line(start=(x_load, 175), end=(x_load, 220),
                             stroke=STROKE, stroke_width=1.5, marker_end=arrow))
            _text(dwg, "IL", x_load + 12, 200, anchor="start", size=12)
        _text(dwg, "Is = Iz + IL", canvas_w / 2, y_b + 52, size=13)

    if schema.show_waveforms and vz:
        _draw_zener_waveforms(dwg, schema, vz, vin, canvas_w, canvas_h)

    return dwg.tostring()


def _draw_zener_waveforms(dwg, schema, vz, vin, canvas_w, canvas_h):
    """A varying (rippling) Vin and the flat regulated Vout = Vz on one panel.

    The input ripple is a deterministic sum of sines (no randomness), and the
    output is zener_clamp(Vin, Vz): the clamp to a flat Vz IS the point."""
    gx0, gx1 = 120.0, 720.0
    gy0, gy1 = 445.0, 565.0
    base = gy1
    n = 300
    mean = vin if vin else vz * 1.8
    peak = max(mean * 1.6, vz * 1.3)
    scale = (gy1 - gy0 - 10) / peak

    vin_s, vout_s = [], []
    for i in range(n + 1):
        t = 2 * math.pi * i / n
        v = mean + 0.35 * mean * math.sin(3 * t) + 0.12 * mean * math.sin(7 * t + 1)
        vin_s.append(v)
    vout_s = zener_clamp(vin_s, vz)

    dwg.add(dwg.line(start=(gx0, base), end=(gx1 + 8, base),
                     stroke=STROKE, stroke_width=1.4))
    dwg.add(dwg.line(start=(gx0, gy0 - 6), end=(gx0, base + 4),
                     stroke=STROKE, stroke_width=1.4))
    _text(dwg, "V", gx0 - 8, gy0 - 2, anchor="end", size=11)
    _text(dwg, "t", gx1 + 14, base + 4, anchor="start", size=11)

    # Vz reference line.
    vz_y = base - vz * scale
    dwg.add(dwg.line(start=(gx0, vz_y), end=(gx1, vz_y), stroke=STROKE,
                     stroke_width=1, stroke_dasharray="5,4"))
    _text(dwg, f"Vz = {schema.zener_voltage}", gx1 + 12, vz_y + 4, anchor="start", size=11)

    px = lambda i: gx0 + (gx1 - gx0) * i / n
    dwg.add(dwg.polyline(points=[(px(i), base - v * scale) for i, v in enumerate(vin_s)],
                         stroke="#888", fill="none", stroke_width=1.6,
                         stroke_dasharray="4,3"))
    dwg.add(dwg.polyline(points=[(px(i), base - v * scale) for i, v in enumerate(vout_s)],
                         stroke=STROKE, fill="none", stroke_width=2.4))
    _text(dwg, "Vin (unregulated, rippling)", gx0 + 6, gy0 + 4, anchor="start", size=10)
    _text(dwg, "Vout = Vz (clamped flat)", gx0 + 6, vz_y - 6, anchor="start", size=10)


# ── 17. Transistor switch (cutoff / saturation) ───────────────────────────────

def switch_operating_points(vcc: float, r_load: float):
    """The two ends of the load line, computed — not asserted.

    OFF (cutoff): the transistor is open, no collector current, so Vce = Vcc.
    ON  (saturation): Vce ≈ 0, so the load drops the whole supply and
    Ic(sat) = Vcc / R_load.
    """
    ic_sat = vcc / r_load if r_load > 0 else 0.0
    return {"cutoff": (vcc, 0.0), "saturation": (0.0, ic_sat)}


def _draw_switch_load(dwg, load_type, cx, y_top, y_bot, on):
    """Collector load. `on` decides whether a lamp/LED glows (drawn filled)."""
    my = (y_top + y_bot) / 2
    if load_type == SwitchLoadType.LAMP:
        r = 18.0
        dwg.add(dwg.circle(center=(cx, my), r=r, stroke=STROKE,
                           fill="#ffe680" if on else "white", stroke_width=2))
        for (dx, dy) in ((0.7, 0.7), (0.7, -0.7)):
            dwg.add(dwg.line(start=(cx - r * dx, my - r * dy),
                             end=(cx + r * dx, my + r * dy),
                             stroke=STROKE, stroke_width=1.5))
        _wire(dwg, [(cx, y_top), (cx, my - r)])
        _wire(dwg, [(cx, my + r), (cx, y_bot)])
        _text(dwg, "lamp", cx + r + 8, my + 4, anchor="start", size=11)
    elif load_type == SwitchLoadType.LED:
        _draw_diode(dwg, cx, y_top + 6, cx, y_bot - 6, None, size=18)
        # emission arrows
        for k in (0, 1):
            ax = cx + 16
            ay = my - 6 + k * 10
            dwg.add(dwg.line(start=(ax, ay), end=(ax + 12, ay - 12),
                             stroke=STROKE, stroke_width=1.4,
                             marker_end=_arrow_marker(dwg, f"led_a{k}")))
        _text(dwg, "LED" + (" (lit)" if on else ""), cx + 30, my + 4,
              anchor="start", size=11)
        _wire(dwg, [(cx, y_top), (cx, y_top + 6)])
        _wire(dwg, [(cx, y_bot - 6), (cx, y_bot)])
    elif load_type == SwitchLoadType.RELAY:
        _draw_oriented(dwg, "inductor", cx, my, 0, 1, None)
        dwg.add(dwg.rect(insert=(cx - 12, my - 22), size=(24, 44),
                         stroke=STROKE, fill="none", stroke_width=1))
        _wire(dwg, [(cx, y_top), (cx, my - 22)])
        _wire(dwg, [(cx, my + 22), (cx, y_bot)])
        _text(dwg, "relay coil" + (" (energised)" if on else ""), cx + 20, my + 4,
              anchor="start", size=11)
    else:   # MOTOR
        r = 18.0
        dwg.add(dwg.circle(center=(cx, my), r=r, stroke=STROKE, fill="white",
                           stroke_width=2))
        _text(dwg, "M", cx, my + 5, size=14)
        _wire(dwg, [(cx, y_top), (cx, my - r)])
        _wire(dwg, [(cx, my + r), (cx, y_bot)])
        _text(dwg, "motor" + (" (running)" if on else ""), cx + r + 8, my + 4,
              anchor="start", size=11)


def _draw_switch_stage(dwg, schema, x0, on, label):
    """One transistor-switch panel centred around x0."""
    npn = schema.transistor_type == TransistorType.NPN
    y_vcc, y_gnd = 95.0, 445.0
    tx, ty = x0, 300.0
    base, coll, emit = _draw_bjt(dwg, tx, ty, npn)

    # Load between Vcc and the collector.
    _draw_switch_load(dwg, schema.load_type, coll[0], y_vcc, coll[1], on)

    # Vcc rail.
    _open_terminal(dwg, coll[0], y_vcc)
    _text(dwg, f"+{schema.supply_label}", coll[0] + 10, y_vcc - 6,
          anchor="start", size=12)

    # Emitter to ground (NPN) — the emitter arrow already points OUT of the device.
    _wire(dwg, [emit, (emit[0], y_gnd)])
    _draw_ground_symbol(dwg, emit[0], y_gnd)

    # Base drive through RB.
    x_drive = x0 - 120
    _draw_oriented(dwg, "resistor", (base[0] + x_drive) / 2 - 6, base[1], -1, 0,
                   schema.base_resistor_label, label_side=1)
    _wire(dwg, [base, (base[0] - 24, base[1])])
    _wire(dwg, [((base[0] + x_drive) / 2 - 29, base[1]), (x_drive, base[1])])
    # A control switch selects the base drive: to +Vin (ON) or to ground (OFF).
    if on:
        _wire(dwg, [(x_drive, base[1]), (x_drive, 180)])
        _open_terminal(dwg, x_drive, 180)
        _text(dwg, "Vin = HIGH", x_drive, 168, size=11)
        _text(dwg, "base driven → saturation", x0, y_gnd + 26, size=11)
    else:
        _wire(dwg, [(x_drive, base[1]), (x_drive, y_gnd)])
        _draw_ground_symbol(dwg, x_drive, y_gnd)
        _text(dwg, "Vin = 0", x_drive, base[1] - 14, size=11)
        _text(dwg, "base at 0 → cutoff", x0, y_gnd + 26, size=11)

    _text(dwg, label, x0, 70, size=13)
    _text(dwg, "NPN" if npn else "PNP", tx + 40, ty + 5, anchor="start", size=11)


def _draw_load_line(dwg, vcc, r_load, x, y, w, h):
    """IC–VCE load line with the cutoff and saturation operating points marked."""
    pts = switch_operating_points(vcc, r_load)
    ic_sat = pts["saturation"][1]
    dwg.add(dwg.line(start=(x, y), end=(x, y + h), stroke=STROKE, stroke_width=1.4))
    dwg.add(dwg.line(start=(x, y + h), end=(x + w, y + h), stroke=STROKE, stroke_width=1.4))
    _text(dwg, "Ic", x - 6, y - 2, anchor="end", size=11)
    _text(dwg, "Vce", x + w + 6, y + h + 4, anchor="start", size=11)
    # load line from (Vcc, 0) to (0, Ic_sat)
    p_cut = (x + w, y + h)                       # cutoff: Vce=Vcc, Ic=0
    p_sat = (x, y + h - h * 0.82)                # saturation: Vce=0, Ic=Ic_sat
    dwg.add(dwg.line(start=p_cut, end=p_sat, stroke=STROKE, stroke_width=2))
    _dot(dwg, *p_cut, 3.5)
    _dot(dwg, *p_sat, 3.5)
    _text(dwg, "cutoff (OFF)", p_cut[0] - 6, p_cut[1] - 8, anchor="end", size=10)
    _text(dwg, "saturation (ON)", p_sat[0] + 8, p_sat[1] - 4, anchor="start", size=10)
    _text(dwg, f"Ic(sat) = Vcc/R = {_fmt_current(ic_sat)}"
               if ic_sat else "Ic(sat) = Vcc/R",
          x + w / 2, y + h + 22, size=11)


def render_transistor_switch(data: Dict[str, Any], canvas_w: int = 800,
                             canvas_h: int = 600) -> str:
    schema = TransistorSwitchSchema(**data)
    dwg = _base_drawing(canvas_w, canvas_h)

    if schema.title:
        _text(dwg, schema.title, canvas_w / 2, 28, size=16)

    if schema.state == SwitchState.BOTH:
        _draw_switch_stage(dwg, schema, 250.0, on=False, label="OFF  (cutoff)")
        _draw_switch_stage(dwg, schema, 620.0, on=True, label="ON  (saturation)")
    else:
        on = schema.state == SwitchState.ON
        _draw_switch_stage(dwg, schema, 340.0, on=on,
                           label="ON  (saturation)" if on else "OFF  (cutoff)")
        if schema.show_regions:
            _draw_load_line(dwg, 5.0, 100.0, 560, 480, 180, 90)

    if schema.show_regions and schema.state == SwitchState.BOTH:
        _text(dwg, "Switch: at cutoff Vce ≈ Vcc (load OFF); "
                   "at saturation Vce ≈ 0, Ic ≈ Vcc/R_load (load ON)",
              canvas_w / 2, canvas_h - 20, size=12)
    return dwg.tostring()


# ── 18. Cathode-ray oscilloscope (CRO) ────────────────────────────────────────

def _parse_ratio(text: str) -> Tuple[int, int]:
    """'1:2' -> (1, 2). Falls back to (1, 1) on anything unparseable."""
    m = re.match(r"\s*(\d+)\s*[:/]\s*(\d+)\s*", text or "")
    if not m:
        return 1, 1
    fx, fy = int(m.group(1)), int(m.group(2))
    return max(1, fx), max(1, fy)


def lissajous_curve(fx: int, fy: int, phase_deg: float = 90.0,
                    n: int = 400) -> List[Tuple[float, float]]:
    """Closed Lissajous figure: x = sin(fx·t + φ), y = sin(fy·t), t ∈ [0, 2π]."""
    ph = math.radians(phase_deg)
    return [(math.sin(fx * (2 * math.pi * i / n) + ph),
             math.sin(fy * (2 * math.pi * i / n)))
            for i in range(n + 1)]


def lissajous_lobes(fx: int, fy: int, phase_deg: float = 90.0) -> Tuple[int, int]:
    """(ny, nx) counted from the generated curve, where

      ny = number of times the trace touches the top edge (local maxima of y) = fy
      nx = number of times it touches the side edge  (local maxima of x) = fx

    so the standard reading fx : fy = nx : ny drops straight out. Counted from the
    sampled points, so the figure and the numbers can never disagree.
    """
    pts = lissajous_curve(fx, fy, phase_deg, n=720)
    ys = [p[1] for p in pts[:-1]]
    xs = [p[0] for p in pts[:-1]]

    def _peaks(vals):
        m = len(vals)
        c = 0
        for i in range(m):
            a, b, cc = vals[(i - 1) % m], vals[i], vals[(i + 1) % m]
            if b > a + 1e-9 and b >= cc - 1e-9:
                c += 1
        return c
    return _peaks(ys), _peaks(xs)


def render_cro(data: Dict[str, Any], canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = CROSchema(**data)
    dwg = _base_drawing(canvas_w, canvas_h)
    arrow = _arrow_marker(dwg, "cro_arrow")

    if schema.title:
        _text(dwg, schema.title, canvas_w / 2, 28, size=16)

    y_axis = 300.0
    lab = schema.show_labels

    # ── Electron gun (left) ──
    x_cath = 90.0
    # filament / cathode
    dwg.add(dwg.rect(insert=(x_cath - 14, y_axis - 20), size=(14, 40),
                     stroke=STROKE, fill="#eee", stroke_width=2))
    if lab:
        _text(dwg, "cathode", x_cath - 7, y_axis - 30, size=10)
        _text(dwg, "(electron gun)", x_cath + 30, y_axis - 48, size=10)
    # control grid
    x_grid = 130.0
    dwg.add(dwg.rect(insert=(x_grid, y_axis - 30), size=(8, 60),
                     stroke=STROKE, fill="white", stroke_width=2))
    if lab:
        _text(dwg, "grid", x_grid + 4, y_axis + 48, size=10)
    # accelerating anodes
    for k, ax in enumerate((175.0, 215.0)):
        dwg.add(dwg.rect(insert=(ax, y_axis - 26), size=(10, 52),
                         stroke=STROKE, fill="white", stroke_width=2))
        if lab:
            _text(dwg, f"A{k + 1}", ax + 5, y_axis - 34, size=10)

    x_gun_out = 245.0
    _wire(dwg, [(x_cath, y_axis), (x_grid, y_axis)])
    _wire(dwg, [(x_grid + 8, y_axis), (175.0, y_axis)])
    _wire(dwg, [(185.0, y_axis), (215.0, y_axis)])
    _wire(dwg, [(225.0, y_axis), (x_gun_out, y_axis)])

    # ── Deflection plates: Y pair (horizontal plates) then X pair (vertical) ──
    x_yp, x_xp = 300.0, 400.0
    # Y plates: one above, one below the axis → vertical deflection.
    dwg.add(dwg.line(start=(x_yp - 22, y_axis - 34), end=(x_yp + 22, y_axis - 34),
                     stroke=STROKE, stroke_width=3))
    dwg.add(dwg.line(start=(x_yp - 22, y_axis + 34), end=(x_yp + 22, y_axis + 34),
                     stroke=STROKE, stroke_width=3))
    if lab:
        _text(dwg, "Y-plates", x_yp, y_axis - 44, size=10)
    # X plates: one left, one right of the axis → horizontal deflection.
    dwg.add(dwg.line(start=(x_xp - 20, y_axis - 30), end=(x_xp - 20, y_axis + 30),
                     stroke=STROKE, stroke_width=3))
    dwg.add(dwg.line(start=(x_xp + 20, y_axis - 30), end=(x_xp + 20, y_axis + 30),
                     stroke=STROKE, stroke_width=3))
    if lab:
        _text(dwg, "X-plates", x_xp, y_axis + 52, size=10)

    # ── Screen (fluorescent) on the right ──
    scr_x, scr_w, scr_h = 560.0, 190.0, 190.0
    scr_cx, scr_cy = scr_x + scr_w / 2, y_axis
    dwg.add(dwg.rect(insert=(scr_x, y_axis - scr_h / 2), size=(scr_w, scr_h),
                     stroke=STROKE, fill="#f4fff4", stroke_width=2, rx=8))
    if lab:
        _text(dwg, "fluorescent screen", scr_cx, y_axis + scr_h / 2 + 18, size=11)

    # ── Electron beam from gun to screen centre ──
    if schema.show_electron_beam:
        dwg.add(dwg.line(start=(x_gun_out, y_axis), end=(scr_x, scr_cy),
                         stroke="#1a7a1a", stroke_width=1.6,
                         stroke_dasharray="6,4", marker_end=arrow))
        _text(dwg, "electron beam", (x_gun_out + scr_x) / 2, y_axis - 10, size=10)

    # ── Trace on the screen (computed) ──
    _draw_cro_trace(dwg, schema, scr_x + 12, y_axis - scr_h / 2 + 12,
                    scr_w - 24, scr_h - 24)

    if schema.timebase and schema.screen_waveform != ScreenWaveform.LISSAJOUS:
        _text(dwg, "X-plates: time base (sawtooth sweep)", canvas_w / 2,
              canvas_h - 40, size=12)
        _text(dwg, "Y-plates: input signal", canvas_w / 2, canvas_h - 20, size=12)
    elif schema.screen_waveform == ScreenWaveform.LISSAJOUS:
        fx, fy = _parse_ratio(schema.lissajous_ratio)
        ny, nx = lissajous_lobes(fx, fy, schema.lissajous_phase_deg)
        _text(dwg, f"Lissajous fx:fy = {fx}:{fy}  →  touches the side edge {nx}×, "
                   f"the top edge {ny}×   (fx:fy = {nx}:{ny})",
              canvas_w / 2, canvas_h - 24, size=12)

    return dwg.tostring()


def _draw_cro_trace(dwg, schema, x, y, w, h):
    """Draw the computed trace inside the screen area (x, y, w, h)."""
    cy = y + h / 2
    wf = schema.screen_waveform
    if wf == ScreenWaveform.LISSAJOUS:
        fx, fy = _parse_ratio(schema.lissajous_ratio)
        pts = lissajous_curve(fx, fy, schema.lissajous_phase_deg)
        sc = min(w, h) / 2 - 6
        cx = x + w / 2
        dwg.add(dwg.polyline(
            points=[(cx + px * sc, cy - py * sc) for (px, py) in pts],
            stroke="#0a7a0a", fill="none", stroke_width=2))
        return
    n = 200
    amp = h / 2 - 8
    if wf == ScreenWaveform.DC:
        yy = cy - amp * 0.45
        dwg.add(dwg.line(start=(x, yy), end=(x + w, yy),
                         stroke="#0a7a0a", stroke_width=2))
        return
    if wf == ScreenWaveform.SQUARE:
        samples = [1.0 if math.sin(2 * math.pi * 2 * i / n) >= 0 else -1.0
                   for i in range(n + 1)]
    else:  # SINE
        samples = [math.sin(2 * math.pi * 2 * i / n) for i in range(n + 1)]
    pts = [(x + w * i / n, cy - amp * v) for i, v in enumerate(samples)]
    dwg.add(dwg.polyline(points=pts, stroke="#0a7a0a", fill="none", stroke_width=2))


# ── Dispatcher ────────────────────────────────────────────────────────────────

CIRCUIT_RENDERERS = {
    "resistor_network": render_resistor_network,
    "capacitor_network": render_capacitor_network,
    "basic_dc_circuit": render_basic_dc_circuit,
    "logic_gates": render_logic_gates,
    "ac_phasor": render_ac_phasor,
    "wheatstone_bridge": render_wheatstone_bridge,
    "rectifier": render_rectifier,
    "rlc_circuit": render_rlc_circuit,
    "mesh_circuit": render_mesh_circuit,
    "transistor_amplifier": render_transistor_amplifier,
    "transformer": render_transformer,
    "rc_circuit": render_rc_circuit,
    "galvanometer_conversion": render_galvanometer_conversion,
    "em_machine": render_em_machine,
    "logic_combinational": render_logic_combinational,
    "zener_regulator": render_zener_regulator,
    "transistor_switch": render_transistor_switch,
    "cro": render_cro,
}


def render_circuits(subtype: str, params: Dict[str, Any],
                    canvas_w: int = 800, canvas_h: int = 600) -> str:
    renderer = CIRCUIT_RENDERERS.get(subtype)
    if not renderer:
        raise ValueError(f"Unknown circuit subtype: '{subtype}'. "
                         f"Supported: {list(CIRCUIT_RENDERERS.keys())}")
    return renderer(params, canvas_w=canvas_w, canvas_h=canvas_h)
