"""
Physics Diagram Renderer using svgwrite.
All coordinates are computed deterministically — no AI geometry.
Exam-style: black-and-white, clean, publication-quality.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

import svgwrite

from diagrams.service.svgtext import make_text
from diagrams.service.shared.xygraph import render_annotated_xy_graph
from diagrams.schemas.physics import (
    InclinedPlaneSchema, FreeBodyDiagramSchema, PulleySystemSchema,
    ProjectileMotionSchema, SpringBlockSchema, ConvexLensSchema,
    ConcaveMirrorSchema, WaveDiagramSchema,
)

# ── SVG helpers ───────────────────────────────────────────────────────────────

STROKE = "black"
STROKE_W = 2
FONT = "Arial, sans-serif"
FONT_SZ = 14
ARROW_SIZE = 8


def _base_drawing(width: int = 800, height: int = 600) -> svgwrite.Drawing:
    dwg = svgwrite.Drawing(size=(f"{width}px", f"{height}px"),
                           viewBox=f"0 0 {width} {height}")
    dwg.add(dwg.rect(insert=(0, 0), size=(f"{width}px", f"{height}px"), fill="white"))
    # Arrow marker
    marker = dwg.marker(id="arrowhead", insert=(10, 4), size=(10, 8),
                        orient="auto", markerUnits="userSpaceOnUse")
    marker.add(dwg.polygon(points=[(0, 0), (10, 4), (0, 8)],
                           fill=STROKE))
    dwg.defs.add(marker)
    return dwg


def _arrow(dwg: svgwrite.Drawing, x1: float, y1: float, x2: float, y2: float,
           label: str = "", offset_x: float = 0, offset_y: float = -8,
           stroke_w: int = STROKE_W, color: str = STROKE):
    """Draw a line with an arrowhead at (x2,y2)."""
    # Shorten line slightly so arrowhead tip is at (x2,y2)
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy)
    if length < 1:
        return
    ux, uy = dx / length, dy / length
    # endpoint pulls back by arrowhead size
    ex, ey = x2 - ux * ARROW_SIZE, y2 - uy * ARROW_SIZE
    line = dwg.line(start=(x1, y1), end=(ex, ey),
                    stroke=color, stroke_width=stroke_w,
                    marker_end="url(#arrowhead)")
    dwg.add(line)
    if label:
        mx = (x1 + x2) / 2 + offset_x
        my = (y1 + y2) / 2 + offset_y
        dwg.add(make_text(dwg, label, (mx, my), font_size=FONT_SZ,
                          font_family=FONT, text_anchor="middle"))


def _text(dwg: svgwrite.Drawing, txt: str, x: float, y: float,
          anchor: str = "middle", size: int = FONT_SZ, bold: bool = False):
    weight = "bold" if bold else "normal"
    dwg.add(make_text(dwg, txt, (x, y), font_size=size, font_family=FONT,
                      text_anchor=anchor, font_weight=weight))


def _deg2rad(deg: float) -> float:
    return deg * math.pi / 180.0


# ── Spring helper ─────────────────────────────────────────────────────────────

def _draw_spring(dwg: svgwrite.Drawing, x1: float, y1: float, x2: float, y2: float,
                 coils: int = 8, amplitude: float = 12):
    """Draw a zigzag spring between two points."""
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy)
    ux, uy = dx / length, dy / length           # unit vector along spring
    px, py = -uy, ux                            # perpendicular unit vector
    # Lead-in and lead-out (straight ends)
    lead = length * 0.1
    points = [(x1, y1), (x1 + ux * lead, y1 + uy * lead)]
    coil_len = length - 2 * lead
    seg = coil_len / (coils * 2)
    for i in range(coils * 2):
        t = lead + seg * (i + 1)
        cx = x1 + ux * t
        cy = y1 + uy * t
        sign = amplitude if i % 2 == 0 else -amplitude
        points.append((cx + px * sign, cy + py * sign))
    points.append((x2 - ux * lead, y2 - uy * lead))
    points.append((x2, y2))
    polyline = dwg.polyline(points=points, stroke=STROKE, stroke_width=STROKE_W, fill="none")
    dwg.add(polyline)


# ── 1. Inclined Plane ─────────────────────────────────────────────────────────

def render_inclined_plane(data: Dict[str, Any], canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = InclinedPlaneSchema(**data)
    dwg = _base_drawing(canvas_w, canvas_h)

    angle_deg = schema.angle
    angle_rad = _deg2rad(angle_deg)

    # Geometry — fixed hypotenuse = 480px, auto-scaled
    hyp = 480
    base = hyp * math.cos(angle_rad)
    height = hyp * math.sin(angle_rad)

    # Canvas origin: bottom-left corner of incline
    ox, oy = (canvas_w - base) / 2, canvas_h - 80

    # Three vertices
    v_bl = (ox, oy)               # bottom-left
    v_br = (ox + base, oy)        # bottom-right
    v_top = (ox, oy - height)     # apex

    # Draw the inclined plane triangle
    triangle = dwg.polygon(points=[v_bl, v_br, v_top],
                            stroke=STROKE, stroke_width=STROKE_W, fill="#f0f0f0")
    dwg.add(triangle)

    # Angle arc and label
    if schema.show_angle_label:
        arc_r = 40
        arc_start_x = ox + arc_r
        arc_start_y = oy
        arc_end_x = ox + arc_r * math.cos(angle_rad)
        arc_end_y = oy - arc_r * math.sin(angle_rad)
        large_arc = 1 if angle_deg > 180 else 0
        path_d = f"M {arc_start_x},{arc_start_y} A {arc_r},{arc_r} 0 {large_arc},0 {arc_end_x},{arc_end_y}"
        dwg.add(dwg.path(d=path_d, fill="none", stroke=STROKE, stroke_width=1))
        label_x = ox + (arc_r + 18) * math.cos(angle_rad / 2)
        label_y = oy - (arc_r + 18) * math.sin(angle_rad / 2)
        _text(dwg, f"{angle_deg:.0f}°", label_x, label_y + 5, anchor="start")

    # Block on incline — parametric position along the incline surface.
    # Incline surface runs from v_top=(ox, oy-height) to v_br=(ox+base, oy).
    # Parameter t=0 → at v_top, t=1 → at v_br (bottom-right).
    # Place block 55% of the way from the TOP (so 45% from the bottom).
    t = 0.55   # 0=apex, 1=base
    mid_x = ox + base * t
    mid_y = (oy - height) + height * t    # = oy - height*(1-t)
    block_size = 44

    # Draw block as a rotated rectangle
    transform = f"rotate({-angle_deg}, {mid_x}, {mid_y})"
    rect = dwg.rect(insert=(mid_x - block_size / 2, mid_y - block_size),
                    size=(block_size, block_size),
                    stroke=STROKE, stroke_width=STROKE_W, fill="white",
                    transform=transform)
    dwg.add(rect)
    _text(dwg, schema.block_label, mid_x, mid_y - block_size / 2 + 5)

    # Force arrows
    arrow_len = 80
    forces = schema.forces

    if "mg" in forces:
        # Weight: straight down
        _arrow(dwg, mid_x, mid_y, mid_x, mid_y + arrow_len, "mg",
               offset_x=14, offset_y=0)

    if "N" in forces:
        # Normal: perpendicular to incline surface (angle_rad + 90° from horizontal)
        nx = mid_x + arrow_len * math.sin(-angle_rad) * (-1)
        ny = mid_y - arrow_len * math.cos(angle_rad)
        # Normal points away from surface (outward)
        n_dx = -math.sin(angle_rad)
        n_dy = -math.cos(angle_rad)
        _arrow(dwg, mid_x, mid_y,
               mid_x + arrow_len * n_dx,
               mid_y + arrow_len * n_dy,
               "N", offset_x=-18, offset_y=0)

    if "f" in forces or "T" in forces:
        label = "f" if "f" in forces else "T"
        # Friction: along the incline surface (upward direction)
        fric_sign = 1 if schema.friction_direction == "up" else -1
        f_dx = fric_sign * math.cos(angle_rad)
        f_dy = fric_sign * (-math.sin(angle_rad))
        _arrow(dwg, mid_x, mid_y,
               mid_x + (arrow_len - 10) * f_dx,
               mid_y + (arrow_len - 10) * f_dy,
               label, offset_x=0, offset_y=-12)

    return dwg.tostring()


# ── 2. Free Body Diagram ──────────────────────────────────────────────────────

def render_free_body_diagram(data: Dict[str, Any], canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = FreeBodyDiagramSchema(**data)
    dwg = _base_drawing(canvas_w, canvas_h)

    cx, cy = canvas_w / 2, canvas_h / 2
    obj = schema.object

    # Draw central object
    obj_size = 60
    if obj.shape == "circle":
        dwg.add(dwg.circle(center=(cx, cy), r=obj_size / 2,
                           stroke=STROKE, stroke_width=STROKE_W, fill="white"))
    elif obj.shape == "point":
        dwg.add(dwg.circle(center=(cx, cy), r=4, fill=STROKE))
    else:  # square (default)
        dwg.add(dwg.rect(insert=(cx - obj_size / 2, cy - obj_size / 2),
                         size=(obj_size, obj_size),
                         stroke=STROKE, stroke_width=STROKE_W, fill="white"))
    _text(dwg, obj.label, cx, cy + 5)

    # Draw force arrows
    arrow_len = 100
    for force in schema.forces:
        theta = _deg2rad(force.direction_deg)
        # 0° = right, 90° = up (flip y because SVG y increases downward)
        fx = cx + arrow_len * math.cos(theta)
        fy = cy - arrow_len * math.sin(theta)  # negative because SVG y
        # Offset label perpendicular to arrow
        perp_x = -math.sin(theta) * 14
        perp_y = -math.cos(theta) * 14
        _arrow(dwg, cx, cy, fx, fy, force.label,
               offset_x=perp_x, offset_y=perp_y - 8)

    return dwg.tostring()


# ── 3. Pulley System ──────────────────────────────────────────────────────────

def render_pulley_system(data: Dict[str, Any], canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = PulleySystemSchema(**data)
    dwg = _base_drawing(canvas_w, canvas_h)

    pulley_r = 36
    cx = canvas_w / 2
    pulley_y = 120

    # Draw ceiling support
    dwg.add(dwg.rect(insert=(0, 0), size=(canvas_w, 20), fill="#888"))
    dwg.add(dwg.line(start=(0, 20), end=(canvas_w, 20), stroke=STROKE, stroke_width=2))

    # Draw pulley(s)
    pulley_xs = []
    count = schema.pulley_count
    spacing = 200
    start_x = cx - (count - 1) * spacing / 2
    for i in range(count):
        px = start_x + i * spacing
        pulley_xs.append(px)
        # Rope from ceiling to pulley
        dwg.add(dwg.line(start=(px, 20), end=(px, pulley_y - pulley_r),
                         stroke=STROKE, stroke_width=2))
        # Pulley circle
        dwg.add(dwg.circle(center=(px, pulley_y), r=pulley_r,
                            stroke=STROKE, stroke_width=STROKE_W, fill="white"))
        # Inner hub
        dwg.add(dwg.circle(center=(px, pulley_y), r=6, fill=STROKE))

    # Masses — default: one on each side of primary pulley
    masses = schema.masses or []
    if not masses:
        masses_data = [
            {"label": "m₁", "side": "left"},
            {"label": "m₂", "side": "right"},
        ]
    else:
        masses_data = [m.model_dump() for m in masses]

    primary_px = pulley_xs[0]
    rope_y_bottom = canvas_h - 80
    rope_drop = rope_y_bottom - (pulley_y + pulley_r)

    left_rope_x = primary_px - pulley_r
    right_rope_x = primary_px + pulley_r

    # Left rope + mass
    if len(masses_data) >= 1:
        m = masses_data[0]
        dwg.add(dwg.line(start=(left_rope_x, pulley_y),
                         end=(left_rope_x, pulley_y + rope_drop),
                         stroke=STROKE, stroke_width=2))
        block_w, block_h = 50, 40
        dwg.add(dwg.rect(insert=(left_rope_x - block_w / 2, pulley_y + rope_drop),
                         size=(block_w, block_h),
                         stroke=STROKE, stroke_width=STROKE_W, fill="white"))
        _text(dwg, m["label"], left_rope_x, pulley_y + rope_drop + block_h / 2 + 5)

    # Right rope + mass
    if len(masses_data) >= 2:
        m = masses_data[1]
        dwg.add(dwg.line(start=(right_rope_x, pulley_y),
                         end=(right_rope_x, pulley_y + rope_drop * 0.7),
                         stroke=STROKE, stroke_width=2))
        block_w, block_h = 50, 40
        dwg.add(dwg.rect(insert=(right_rope_x - block_w / 2, pulley_y + rope_drop * 0.7),
                         size=(block_w, block_h),
                         stroke=STROKE, stroke_width=STROKE_W, fill="white"))
        _text(dwg, m["label"], right_rope_x, pulley_y + rope_drop * 0.7 + block_h / 2 + 5)

    # Rope arc over pulley
    arc_path = (f"M {left_rope_x},{pulley_y} "
                f"A {pulley_r},{pulley_r} 0 0,0 {right_rope_x},{pulley_y}")
    dwg.add(dwg.path(d=arc_path, fill="none", stroke=STROKE, stroke_width=2))

    # Tension label on rope
    _text(dwg, "T", primary_px, pulley_y - pulley_r - 14)

    return dwg.tostring()


# ── 4. Projectile Motion ──────────────────────────────────────────────────────

def render_projectile_motion(data: Dict[str, Any], canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = ProjectileMotionSchema(**data)
    dwg = _base_drawing(canvas_w, canvas_h)

    angle = schema.launch_angle
    angle_rad = _deg2rad(angle)

    # Ground line
    ground_y = canvas_h - 70
    dwg.add(dwg.line(start=(40, ground_y), end=(canvas_w - 40, ground_y),
                     stroke=STROKE, stroke_width=2))
    # Ground hatch
    for gx in range(40, canvas_w - 40, 20):
        dwg.add(dwg.line(start=(gx, ground_y), end=(gx - 10, ground_y + 12),
                         stroke=STROKE, stroke_width=1))

    # Launch point
    launch_x, launch_y = 80, ground_y

    # Trajectory: parametric in canvas units
    # Use normalised physics: max range ~ (canvas_w - 160)
    g = 9.8
    v0 = schema.initial_velocity
    v0x = v0 * math.cos(angle_rad)
    v0y = v0 * math.sin(angle_rad)
    t_flight = 2 * v0y / g
    x_range = v0x * t_flight
    y_max = v0y ** 2 / (2 * g)

    # Scale to canvas
    x_scale = (canvas_w - 160) / x_range
    y_scale = min((ground_y - 80) / y_max, x_scale) if y_max > 0 else x_scale

    # Build trajectory path
    n_pts = 60
    path_pts = []
    for i in range(n_pts + 1):
        t = t_flight * i / n_pts
        px = launch_x + v0x * t * x_scale
        py = ground_y - (v0y * t - 0.5 * g * t ** 2) * y_scale
        path_pts.append((round(px, 2), round(py, 2)))

    path_str = "M " + " L ".join(f"{p[0]},{p[1]}" for p in path_pts)
    dwg.add(dwg.path(d=path_str, fill="none", stroke=STROKE,
                     stroke_width=2, stroke_dasharray="6,3"))

    # Launch point dot
    dwg.add(dwg.circle(center=(launch_x, launch_y), r=4, fill=STROKE))
    _text(dwg, schema.label_points[0] if schema.label_points else "O",
          launch_x - 14, launch_y + 4, anchor="end")

    # Max height point
    t_peak = v0y / g
    peak_x = launch_x + v0x * t_peak * x_scale
    peak_y = ground_y - y_max * y_scale
    dwg.add(dwg.circle(center=(peak_x, peak_y), r=4, fill=STROKE))
    if len(schema.label_points) > 1:
        _text(dwg, schema.label_points[1], peak_x, peak_y - 12)

    # Range point
    range_x = launch_x + x_range * x_scale
    dwg.add(dwg.circle(center=(range_x, ground_y), r=4, fill=STROKE))
    if len(schema.label_points) > 2:
        _text(dwg, schema.label_points[2], range_x + 10, ground_y + 4, anchor="start")

    # Initial velocity arrow
    arrow_scale = 80
    vx_end = launch_x + arrow_scale * math.cos(angle_rad)
    vy_end = launch_y - arrow_scale * math.sin(angle_rad)
    _arrow(dwg, launch_x, launch_y, vx_end, vy_end, "v₀",
           offset_x=0, offset_y=-12)

    # Components
    if schema.show_components:
        comp_len = 70
        # Horizontal component
        _arrow(dwg, launch_x, ground_y - 10,
               launch_x + comp_len * math.cos(angle_rad), ground_y - 10,
               "vₓ", offset_x=0, offset_y=-8, stroke_w=1, color="#555")
        # Vertical component
        _arrow(dwg, launch_x + 12, launch_y,
               launch_x + 12, launch_y - comp_len * math.sin(angle_rad),
               "vᵧ", offset_x=18, offset_y=0, stroke_w=1, color="#555")

    # Max height dashed line
    if schema.show_max_height_line:
        dwg.add(dwg.line(start=(launch_x, peak_y), end=(peak_x, peak_y),
                         stroke=STROKE, stroke_width=1, stroke_dasharray="4,4"))
        dwg.add(dwg.line(start=(peak_x, peak_y), end=(peak_x, ground_y),
                         stroke=STROKE, stroke_width=1, stroke_dasharray="4,4"))
        _text(dwg, "H", launch_x - 22, (peak_y + ground_y) / 2 + 5, anchor="end")
        _text(dwg, "R", (launch_x + range_x) / 2, ground_y + 22)

    # Angle arc
    arc_r = 40
    arc_path = (f"M {launch_x + arc_r},{launch_y} "
                f"A {arc_r},{arc_r} 0 0,0 "
                f"{launch_x + arc_r * math.cos(angle_rad)},{launch_y - arc_r * math.sin(angle_rad)}")
    dwg.add(dwg.path(d=arc_path, fill="none", stroke=STROKE, stroke_width=1))
    _text(dwg, f"{angle:.0f}°",
          launch_x + (arc_r + 16) * math.cos(angle_rad / 2),
          launch_y - (arc_r + 16) * math.sin(angle_rad / 2) + 5,
          anchor="start")

    return dwg.tostring()


# ── 5. Spring Block ───────────────────────────────────────────────────────────

def render_spring_block(data: Dict[str, Any], canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = SpringBlockSchema(**data)
    dwg = _base_drawing(canvas_w, canvas_h)

    cy = canvas_h / 2

    if schema.orientation == "horizontal":
        # Wall (left side)
        wall_x = 80
        dwg.add(dwg.rect(insert=(0, cy - 100), size=(wall_x, 200),
                         fill="#888", stroke=STROKE, stroke_width=1))
        # Hatch marks on wall
        for hy in range(int(cy - 100), int(cy + 100), 20):
            dwg.add(dwg.line(start=(wall_x, hy), end=(wall_x + 15, hy - 15),
                             stroke=STROKE, stroke_width=1))
        dwg.add(dwg.line(start=(wall_x, cy - 100), end=(wall_x, cy + 100),
                         stroke=STROKE, stroke_width=2))

        # Spring
        spring_x1, spring_y = wall_x, cy
        spring_x2 = 420
        _draw_spring(dwg, spring_x1, spring_y, spring_x2, spring_y)

        # Spring label
        _text(dwg, schema.spring_label, (spring_x1 + spring_x2) / 2, spring_y - 36)

        # Block
        block_w, block_h = 100, 90
        block_x = spring_x2
        dwg.add(dwg.rect(insert=(block_x, cy - block_h / 2),
                         size=(block_w, block_h),
                         stroke=STROKE, stroke_width=STROKE_W, fill="white"))
        _text(dwg, schema.block_label, block_x + block_w / 2, cy + 5, bold=True)

        # Floor
        floor_y = cy + block_h / 2 + 2
        dwg.add(dwg.line(start=(wall_x, floor_y), end=(block_x + block_w + 60, floor_y),
                         stroke=STROKE, stroke_width=2))
        for fx in range(int(wall_x), int(block_x + block_w + 60), 20):
            dwg.add(dwg.line(start=(fx, floor_y), end=(fx - 10, floor_y + 12),
                             stroke=STROKE, stroke_width=1))

        # Equilibrium line + displacement arrow (eq_x is always block_x for horizontal)
        eq_x = block_x
        if schema.show_equilibrium:
            dwg.add(dwg.line(start=(eq_x, cy - block_h / 2 - 30),
                             end=(eq_x, cy + block_h / 2 + 30),
                             stroke=STROKE, stroke_width=1, stroke_dasharray="5,4"))
            _text(dwg, "x=0", eq_x, cy - block_h / 2 - 36)

        # Displacement arrow
        if schema.displacement_label:
            disp_y = cy + block_h / 2 + 28
            _arrow(dwg, eq_x, disp_y, eq_x + 80, disp_y,
                   schema.displacement_label, offset_x=0, offset_y=-8)

    else:  # vertical spring
        cx = canvas_w / 2
        ceiling_y = 40
        # Ceiling
        dwg.add(dwg.rect(insert=(0, 0), size=(canvas_w, ceiling_y), fill="#888"))
        dwg.add(dwg.line(start=(0, ceiling_y), end=(canvas_w, ceiling_y),
                         stroke=STROKE, stroke_width=2))
        # Spring
        spring_y1, spring_y2 = ceiling_y, 360
        _draw_spring(dwg, cx, spring_y1, cx, spring_y2)
        _text(dwg, schema.spring_label, cx + 36, (spring_y1 + spring_y2) / 2)
        # Block
        block_w, block_h = 90, 80
        dwg.add(dwg.rect(insert=(cx - block_w / 2, spring_y2),
                         size=(block_w, block_h),
                         stroke=STROKE, stroke_width=STROKE_W, fill="white"))
        _text(dwg, schema.block_label, cx, spring_y2 + block_h / 2 + 5, bold=True)
        # Weight arrow
        _arrow(dwg, cx, spring_y2 + block_h,
               cx, spring_y2 + block_h + 70, "mg",
               offset_x=14, offset_y=0)
        # Tension (spring force) upward
        _arrow(dwg, cx, spring_y2,
               cx, spring_y2 - 70, "F_s",
               offset_x=18, offset_y=0)

    return dwg.tostring()


# ── 6. Optics: Convex Lens ────────────────────────────────────────────────────

def render_optics_convex_lens(data: Dict[str, Any], canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = ConvexLensSchema(**data)
    dwg = _base_drawing(canvas_w, canvas_h)

    cx, cy = canvas_w / 2, canvas_h / 2
    f = 120  # focal length in px (scaled)

    # Principal axis
    dwg.add(dwg.line(start=(20, cy), end=(canvas_w - 20, cy),
                     stroke=STROKE, stroke_width=1, stroke_dasharray="8,4"))

    # Lens (biconvex shape using two arcs)
    lens_h = 200
    lens_w = 30
    # Draw lens as two arcs
    path_d = (
        f"M {cx},{cy - lens_h / 2} "
        f"Q {cx + lens_w},{cy} {cx},{cy + lens_h / 2} "
        f"Q {cx - lens_w},{cy} {cx},{cy - lens_h / 2}"
    )
    dwg.add(dwg.path(d=path_d, stroke=STROKE, stroke_width=2.5, fill="none"))
    # Tick arrows on lens ends
    dwg.add(dwg.line(start=(cx - 12, cy - lens_h / 2), end=(cx + 12, cy - lens_h / 2),
                     stroke=STROKE, stroke_width=2))
    dwg.add(dwg.line(start=(cx - 12, cy + lens_h / 2), end=(cx + 12, cy + lens_h / 2),
                     stroke=STROKE, stroke_width=2))

    # Focal points and 2F points
    fp_r = 4
    if schema.show_focal_points:
        for sign in (-1, 1):
            fx = cx + sign * f
            dwg.add(dwg.circle(center=(fx, cy), r=fp_r, fill=STROKE))
            _text(dwg, f"F{'₁' if sign<0 else '₂'}", fx, cy + 18)
            # 2F
            ffx = cx + sign * 2 * f
            dwg.add(dwg.circle(center=(ffx, cy), r=fp_r, fill=STROKE))
            _text(dwg, f"2F{'₁' if sign<0 else '₂'}", ffx, cy + 18)

    # Object arrow (left side)
    obj_x = cx - int(1.5 * f)   # beyond 2F by default
    obj_h = 90
    _arrow(dwg, obj_x, cy, obj_x, cy - obj_h, "")
    _text(dwg, "O", obj_x - 14, cy - obj_h / 2, anchor="end")

    # Image arrow (right side, real + inverted for object beyond 2F)
    # Using lens formula: 1/v - 1/u = 1/f  (sign convention: u negative for real object)
    u = -(cx - obj_x)  # negative
    v = img_h = 0.0
    has_image = False
    if abs(u) > abs(f):
        v = f * u / (u + f)
        img_x = cx + v
        m = -v / u
        img_h = min(obj_h * abs(m), lens_h * 0.8)
        has_image = True
        if v > 0:
            _arrow(dwg, img_x, cy, img_x, cy + img_h, "")
            _text(dwg, "I", img_x + 10, cy + img_h / 2, anchor="start")
        else:
            _arrow(dwg, img_x, cy, img_x, cy - img_h * 0.6, "")
            _text(dwg, "I (virtual)", img_x - 12, cy - img_h * 0.3, anchor="end")

    # Rays (3 standard rays)
    if schema.show_rays:
        # Ray 1: Parallel to axis → passes through F₂ after lens
        dwg.add(dwg.line(start=(obj_x, cy - obj_h),
                         end=(cx, cy - obj_h),
                         stroke=STROKE, stroke_width=1))
        dwg.add(dwg.line(start=(cx, cy - obj_h),
                         end=(cx + 2 * f, cy),
                         stroke=STROKE, stroke_width=1))
        # Ray 2: Through optical center (straight line through lens)
        if has_image:
            img_tip_x = cx + v
            img_tip_y = cy + img_h if v > 0 else cy - img_h * 0.6
            dwg.add(dwg.line(start=(obj_x, cy - obj_h),
                             end=(img_tip_x, img_tip_y),
                             stroke=STROKE, stroke_width=1, stroke_dasharray="4,3"))
        # Ray 3: Through F₁ → parallel to axis after lens
        f1_x = cx - f
        if abs(obj_x - f1_x) > 1:
            slope = -obj_h / (obj_x - f1_x)
            ray3_end_y = cy - obj_h + slope * (cx - obj_x)
        else:
            ray3_end_y = cy - obj_h
        dwg.add(dwg.line(start=(obj_x, cy - obj_h),
                         end=(cx, ray3_end_y),
                         stroke=STROKE, stroke_width=1))
        dwg.add(dwg.line(start=(cx, ray3_end_y),
                         end=(canvas_w - 20, ray3_end_y),
                         stroke=STROKE, stroke_width=1))

    return dwg.tostring()


# ── 7. Optics: Concave Mirror ─────────────────────────────────────────────────

def render_optics_concave_mirror(data: Dict[str, Any], canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = ConcaveMirrorSchema(**data)
    dwg = _base_drawing(canvas_w, canvas_h)

    cx, cy = int(canvas_w * 0.6), canvas_h / 2
    f = 110  # focal length px

    # Principal axis
    dwg.add(dwg.line(start=(20, cy), end=(canvas_w - 20, cy),
                     stroke=STROKE, stroke_width=1, stroke_dasharray="8,4"))

    # Mirror arc (on right side)
    mirror_h = 220
    radius_of_curvature = 2 * f
    # Simple arc approximation
    arc_path = (f"M {cx},{cy - mirror_h / 2} "
                f"Q {cx + 55},{cy} {cx},{cy + mirror_h / 2}")
    dwg.add(dwg.path(d=arc_path, stroke=STROKE, stroke_width=3, fill="none"))
    # Mirror backing
    arc_path_b = (f"M {cx + 6},{cy - mirror_h / 2} "
                  f"Q {cx + 62},{cy} {cx + 6},{cy + mirror_h / 2}")
    dwg.add(dwg.path(d=arc_path_b, stroke="#aaa", stroke_width=6, fill="none"))

    # Labels
    _text(dwg, "P", cx + 4, cy - mirror_h / 2 - 10)  # pole top
    _text(dwg, "P", cx + 4, cy + mirror_h / 2 + 20)  # pole bottom

    if schema.show_focal_points:
        # Focal point
        dwg.add(dwg.circle(center=(cx - f, cy), r=4, fill=STROKE))
        _text(dwg, "F", cx - f, cy + 20)
        # Centre of curvature
        dwg.add(dwg.circle(center=(cx - 2 * f, cy), r=4, fill=STROKE))
        _text(dwg, "C", cx - 2 * f, cy + 20)

    # Object arrow
    obj_x = cx - int(1.6 * f)
    obj_h = 80
    _arrow(dwg, obj_x, cy, obj_x, cy - obj_h, "")
    _text(dwg, "O", obj_x - 14, cy - obj_h / 2, anchor="end")

    # Image (mirror equation: 1/v + 1/u = 1/f, all distances positive from mirror)
    u = cx - obj_x  # positive distance
    if u != f:
        v = f * u / (u - f)
        img_x = cx - v
        m = -v / u
        img_h_val = obj_h * abs(m)
        img_h_val = min(img_h_val, mirror_h * 0.8)
        if v > 0 and img_x > 20:
            if m < 0:  # inverted real image
                _arrow(dwg, img_x, cy, img_x, cy + img_h_val, "")
            else:
                _arrow(dwg, img_x, cy, img_x, cy - img_h_val, "")
            _text(dwg, "I", img_x + 10, cy + img_h_val / 2)

    # Rays
    if schema.show_rays:
        obj_tip_y = cy - obj_h
        # Ray 1: parallel to axis → reflects through F
        dwg.add(dwg.line(start=(obj_x, obj_tip_y), end=(cx, obj_tip_y),
                         stroke=STROKE, stroke_width=1))
        dwg.add(dwg.line(start=(cx, obj_tip_y),
                         end=(cx - 2 * f, cy),
                         stroke=STROKE, stroke_width=1))
        # Ray 2: Through F → reflects parallel
        ray2_x2 = cx
        if abs(u - f) > 5:
            slope2 = (cy - obj_tip_y) / (cx - f - obj_x) if (cx - f - obj_x) != 0 else 0
            ray2_y_at_mirror = obj_tip_y + slope2 * (cx - obj_x)
            dwg.add(dwg.line(start=(obj_x, obj_tip_y),
                             end=(cx, ray2_y_at_mirror),
                             stroke=STROKE, stroke_width=1))
            dwg.add(dwg.line(start=(cx, ray2_y_at_mirror),
                             end=(20, ray2_y_at_mirror),
                             stroke=STROKE, stroke_width=1))

    return dwg.tostring()


# ── 8. Wave Diagram ───────────────────────────────────────────────────────────

def render_wave_diagram(data: Dict[str, Any], canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = WaveDiagramSchema(**data)
    dwg = _base_drawing(canvas_w, canvas_h)

    cx_start = 60
    cx_end = canvas_w - 60
    cy = canvas_h / 2
    A = schema.amplitude
    lam = schema.wavelength_px
    n = schema.num_cycles

    # Principal axis
    dwg.add(dwg.line(start=(cx_start - 20, cy), end=(cx_end + 20, cy),
                     stroke=STROKE, stroke_width=1))
    # Axis label
    _arrow(dwg, cx_end, cy, cx_end + 20, cy, "x", offset_x=0, offset_y=-12)

    # Wave path: sin(2πx/λ) * A
    total_x = cx_end - cx_start
    n_pts = 200
    path_pts = []
    for i in range(n_pts + 1):
        x_frac = i / n_pts
        x = cx_start + x_frac * total_x
        theta = 2 * math.pi * (x_frac * n)
        y = cy - A * math.sin(theta)
        path_pts.append((round(x, 2), round(y, 2)))

    path_str = "M " + " L ".join(f"{p[0]},{p[1]}" for p in path_pts)
    dwg.add(dwg.path(d=path_str, fill="none", stroke=STROKE, stroke_width=2.5))

    # Amplitude label (vertical dashed line at first crest)
    if schema.label_amplitude:
        first_crest_x = cx_start + lam / 4
        dwg.add(dwg.line(start=(first_crest_x, cy),
                         end=(first_crest_x, cy - A),
                         stroke=STROKE, stroke_width=1, stroke_dasharray="4,3"))
        _arrow(dwg, first_crest_x + 18, cy,
               first_crest_x + 18, cy - A, "A",
               offset_x=14, offset_y=0, stroke_w=1)

    # Wavelength label
    if schema.label_wavelength and lam <= total_x:
        wave_y = cy + A + 28
        wl_x1 = cx_start
        wl_x2 = cx_start + lam
        dwg.add(dwg.line(start=(wl_x1, wave_y), end=(wl_x2, wave_y),
                         stroke=STROKE, stroke_width=1))
        dwg.add(dwg.line(start=(wl_x1, cy + A + 14), end=(wl_x1, wave_y + 10),
                         stroke=STROKE, stroke_width=1))
        dwg.add(dwg.line(start=(wl_x2, cy + A + 14), end=(wl_x2, wave_y + 10),
                         stroke=STROKE, stroke_width=1))
        _text(dwg, "λ", (wl_x1 + wl_x2) / 2, wave_y + 20)

    # Crest/trough labels
    if schema.label_crest:
        crest_x = cx_start + lam / 4
        _text(dwg, "Crest", crest_x, cy - A - 16)
    if schema.label_trough and n >= 1:
        trough_x = cx_start + 3 * lam / 4
        _text(dwg, "Trough", trough_x, cy + A + 22)

    # Y-axis
    dwg.add(dwg.line(start=(cx_start - 20, cy - A - 30),
                     end=(cx_start - 20, cy + A + 30),
                     stroke=STROKE, stroke_width=1))
    _arrow(dwg, cx_start - 20, cy - A - 30,
           cx_start - 20, cy - A - 50, "y",
           offset_x=-14, offset_y=0, stroke_w=1)

    return dwg.tostring()


# ── 9. Thermodynamics P-V Diagram ────────────────────────────────────────────

import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["svg.fonttype"] = "none"
# Without a fixed salt, matplotlib seeds its SVG clip-path ids from a fresh uuid4
# each call, so identical params would render to different bytes.
matplotlib.rcParams["svg.hashsalt"] = "paperdeck"
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import io as _io

def _fig_to_svg_phys(fig) -> str:
    buf = _io.BytesIO()
    # Date=None suppresses matplotlib's <dc:date> stamp; with it, the same params
    # would yield a different SVG on every call.
    fig.savefig(buf, format="svg", bbox_inches="tight", facecolor="white", dpi=100,
                metadata={"Date": None})
    buf.seek(0)
    svg = buf.getvalue().decode("utf-8")
    plt.close(fig)
    return svg


def render_thermodynamics_pv(data: Dict[str, Any], canvas_w: int = 800, canvas_h: int = 600) -> str:
    from diagrams.schemas.physics import ThermoPVSchema
    schema = ThermoPVSchema(**data)

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))

    state_map: Dict[str, Tuple[float, float]] = {s.label: (s.volume, s.pressure) for s in schema.states}
    gamma = schema.gamma

    # Process line styles by type
    _ls = {"isothermal": "-", "isobaric": "--", "isochoric": "-.", "adiabatic": ":", "general": "-"}
    _lbl_offset = {"isothermal": (-0.3, 0.15), "isobaric": (0, 0.15), "isochoric": (0.05, 0),
                   "adiabatic": (0.05, 0.12), "general": (0, 0.1)}

    poly_verts = []  # for work shading

    for proc in schema.processes:
        if proc.from_state not in state_map or proc.to_state not in state_map:
            continue
        v1, p1 = state_map[proc.from_state]
        v2, p2 = state_map[proc.to_state]
        t = proc.process_type
        n_pts = 200

        if t == "isobaric":
            vv = np.linspace(v1, v2, n_pts)
            pp = np.full(n_pts, p1)
        elif t == "isochoric":
            vv = np.full(n_pts, v1)
            pp = np.linspace(p1, p2, n_pts)
        elif t == "isothermal":
            k = p1 * v1
            vv = np.linspace(min(v1, v2), max(v1, v2), n_pts)
            pp = k / vv
            if v2 < v1:
                vv, pp = vv[::-1], pp[::-1]
        elif t == "adiabatic":
            k = p1 * v1 ** gamma
            vv = np.linspace(min(v1, v2), max(v1, v2), n_pts)
            pp = k / vv ** gamma
            if v2 < v1:
                vv, pp = vv[::-1], pp[::-1]
        else:
            vv = np.linspace(v1, v2, n_pts)
            pp = np.linspace(p1, p2, n_pts)

        ls = _ls.get(t, "-")
        lw = 2.5 if t in ("isothermal", "adiabatic") else 2.0
        ax.plot(vv, pp, ls, color="black", linewidth=lw, zorder=3)
        poly_verts.extend(list(zip(vv, pp)))

        # Arrow midpoint to show direction
        mid = n_pts // 2
        ax.annotate("", xy=(vv[mid + 3], pp[mid + 3]), xytext=(vv[mid - 3], pp[mid - 3]),
                    arrowprops=dict(arrowstyle="->", color="black", lw=1.2), zorder=4)

        # Process label
        if proc.label:
            dx, dy = _lbl_offset.get(t, (0, 0.1))
            ax.text(vv[mid] + dx, pp[mid] + dy, proc.label, fontsize=11, ha="center", va="bottom")

    # Shade work area for closed cycle
    if schema.show_work_area and len(poly_verts) >= 3:
        from matplotlib.patches import Polygon as MPoly
        poly = MPoly(poly_verts, closed=True, alpha=0.15, facecolor="blue", edgecolor="none")
        ax.add_patch(poly)
        ax.text(sum(x for x, _ in poly_verts) / len(poly_verts),
                sum(y for _, y in poly_verts) / len(poly_verts),
                "W", fontsize=12, ha="center", color="blue")

    # State points
    for s in schema.states:
        vv, pp = s.volume, s.pressure
        ax.plot(vv, pp, "ko", markersize=7, zorder=5)
        ax.annotate(s.label, (vv, pp), textcoords="offset points",
                    xytext=(6, 6), fontsize=12, fontweight="bold", zorder=6)

    ax.set_xlabel(schema.x_label, fontsize=12)
    ax.set_ylabel(schema.y_label, fontsize=12)
    if schema.title:
        ax.set_title(schema.title, fontsize=13)

    # Clean axes: only bottom + left, starting from origin style
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_position(("outward", 5))
    ax.spines["bottom"].set_position(("outward", 5))
    ax.set_xlim(left=0)
    ax.set_ylim(bottom=0)
    ax.grid(True, color="#eeeeee", linestyle="--", linewidth=0.7)

    fig.tight_layout(pad=0.8)
    return _fig_to_svg_phys(fig)


# ── 10. Ray Optics: Prism ─────────────────────────────────────────────────────

def render_ray_optics_prism(data: Dict[str, Any], canvas_w: int = 800, canvas_h: int = 600) -> str:
    from diagrams.schemas.physics import RayOpticsPrismSchema
    schema = RayOpticsPrismSchema(**data)

    A_deg = schema.prism_angle
    i_deg = schema.incident_angle
    n = schema.refractive_index

    A = math.radians(A_deg)
    i = math.radians(i_deg)

    # Snell's law at surface 1: sin(i) = n * sin(r1)
    sin_r1 = math.sin(i) / n
    if abs(sin_r1) > 1:
        sin_r1 = 0.99
    r1 = math.asin(sin_r1)

    # Angle at surface 2: r2 = A - r1
    r2 = A - r1
    if r2 < 0:
        r2 = abs(r2)

    # Snell at surface 2: n * sin(r2) = sin(e)
    sin_e = n * math.sin(r2)
    if abs(sin_e) > 1:
        sin_e = 0.99
    e = math.asin(sin_e)

    # Angle of deviation
    delta = (i - r1) + (e - r2)

    dwg = _base_drawing(canvas_w, canvas_h)

    # Prism geometry: equilateral-like triangle, apex at top center
    cx, cy = canvas_w / 2, canvas_h * 0.52
    half_base = canvas_w * 0.25
    prism_height = half_base * math.tan(A / 2) * 1.8

    apex = (cx, cy - prism_height * 0.55)
    base_l = (cx - half_base, cy + prism_height * 0.45)
    base_r = (cx + half_base, cy + prism_height * 0.45)

    # Draw prism (filled light blue)
    dwg.add(dwg.polygon(points=[apex, base_l, base_r],
                        stroke=STROKE, stroke_width=2.5, fill="#dceeff"))

    # Left surface normal at incidence point
    # Incidence on left surface, midpoint of left face
    surf_l_vec = (base_l[0] - apex[0], base_l[1] - apex[1])
    surf_l_len = math.hypot(*surf_l_vec)
    surf_l_unit = (surf_l_vec[0] / surf_l_len, surf_l_vec[1] / surf_l_len)
    # Normal to left surface (pointing outward, i.e., rotated 90° CCW)
    norm_l = (surf_l_unit[1], -surf_l_unit[0])

    # Hit point on left surface (40% from apex)
    hit_t = 0.42
    hit1 = (apex[0] + surf_l_vec[0] * hit_t, apex[1] + surf_l_vec[1] * hit_t)

    # Normal line at hit1
    if schema.show_normals:
        norm_len = 60
        n1_out = (hit1[0] - norm_l[0] * norm_len, hit1[1] - norm_l[1] * norm_len)
        n1_in = (hit1[0] + norm_l[0] * norm_len, hit1[1] + norm_l[1] * norm_len)
        dwg.add(dwg.line(start=n1_out, end=n1_in,
                         stroke=STROKE, stroke_width=1, stroke_dasharray="6,3"))

    # Incident ray direction (approaching hit1)
    # The left surface normal is norm_l. Incident angle i from normal.
    # We rotate norm_l by -i to get the incident ray direction (coming toward surface)
    cos_i, sin_i = math.cos(i), math.sin(i)
    # Rotate norm_l by angle i in the correct direction
    inc_dir = (norm_l[0] * cos_i + norm_l[1] * sin_i,
               -norm_l[0] * sin_i + norm_l[1] * cos_i)
    ray_len = 120
    inc_start = (hit1[0] + inc_dir[0] * ray_len, hit1[1] + inc_dir[1] * ray_len)
    _arrow(dwg, inc_start[0], inc_start[1], hit1[0], hit1[1], "", color=STROKE)

    # Refracted ray inside prism: rotated by r1 from normal (inward)
    cos_r1, sin_r1 = math.cos(r1), math.sin(r1)
    ref_dir_in = (-norm_l[0] * cos_r1 - norm_l[1] * sin_r1,
                  norm_l[0] * sin_r1 - norm_l[1] * cos_r1)

    # Find exit point on right surface
    # Right surface: apex → base_r
    surf_r_vec = (base_r[0] - apex[0], base_r[1] - apex[1])
    # Parametric ray from hit1 along ref_dir_in: hit1 + t * ref_dir_in
    # Parametric right surface: apex + s * surf_r_vec
    # Solve: hit1 + t*ref_dir_in = apex + s*surf_r_vec
    # hit1x + t*rdx = apx + s*srx  → t*rdx - s*srx = apx - hit1x
    # hit1y + t*rdy = apy + s*sry  → t*rdy - s*sry = apy - hit1y
    rdx, rdy = ref_dir_in
    srx, sry = surf_r_vec
    apx, apy = apex
    denom = rdx * (-sry) - rdy * (-srx)
    if abs(denom) > 1e-6:
        dx_ = apx - hit1[0]
        dy_ = apy - hit1[1]
        t_val = (dx_ * (-sry) - dy_ * (-srx)) / denom
        s_val = (rdx * dy_ - rdy * dx_) / denom
        s_val = max(0.1, min(0.9, s_val))  # keep on surface
        hit2 = (apx + surf_r_vec[0] * s_val, apy + surf_r_vec[1] * s_val)
        t_val = max(10, t_val)
        hit2_actual = (hit1[0] + ref_dir_in[0] * t_val, hit1[1] + ref_dir_in[1] * t_val)
        # Use parametric s_val hit point on surface
        hit2 = (apx + surf_r_vec[0] * s_val, apy + surf_r_vec[1] * s_val)
    else:
        hit2 = (hit1[0] + ref_dir_in[0] * 100, hit1[1] + ref_dir_in[1] * 100)

    # Draw refracted ray inside prism
    dwg.add(dwg.line(start=hit1, end=hit2,
                     stroke=STROKE, stroke_width=2, stroke_dasharray="none"))

    # Normal at exit surface
    surf_r_unit = (surf_r_vec[0] / math.hypot(*surf_r_vec), surf_r_vec[1] / math.hypot(*surf_r_vec))
    norm_r = (-surf_r_unit[1], surf_r_unit[0])  # outward normal of right surface

    if schema.show_normals:
        norm2_out = (hit2[0] + norm_r[0] * norm_len, hit2[1] + norm_r[1] * norm_len)
        norm2_in = (hit2[0] - norm_r[0] * norm_len, hit2[1] - norm_r[1] * norm_len)
        dwg.add(dwg.line(start=norm2_in, end=norm2_out,
                         stroke=STROKE, stroke_width=1, stroke_dasharray="6,3"))

    # Emergent ray direction: rotate outward normal by e
    cos_e_val, sin_e_val = math.cos(e), math.sin(e)
    em_dir = (norm_r[0] * cos_e_val - norm_r[1] * sin_e_val,
              norm_r[0] * sin_e_val + norm_r[1] * cos_e_val)
    em_end = (hit2[0] + em_dir[0] * ray_len, hit2[1] + em_dir[1] * ray_len)
    _arrow(dwg, hit2[0], hit2[1], em_end[0], em_end[1], "", color=STROKE)

    # Labels
    if schema.show_angles:
        # Angle of incidence label 'i'
        _text(dwg, f"i={i_deg:.0f}°", inc_start[0] - 20, inc_start[1] + 16, size=12)
        # Angle of emergence 'e'
        _text(dwg, f"e={math.degrees(e):.0f}°", em_end[0] + 8, em_end[1] - 8,
              anchor="start", size=12)
        # Prism angle A
        _text(dwg, f"A={A_deg:.0f}°", apex[0], apex[1] - 14, size=12)

    # Angle of deviation δ
    if schema.label_deviation:
        delta_deg = math.degrees(delta)
        _text(dwg, f"δ = {delta_deg:.1f}°",
              canvas_w / 2, base_l[1] + 28, size=13, bold=True)

    if schema.title:
        _text(dwg, schema.title, canvas_w / 2, 28, size=14, bold=True)

    return dwg.tostring()


# ── 11. Electric Field Lines ──────────────────────────────────────────────────

def render_electric_field_lines(data: Dict[str, Any], canvas_w: int = 800, canvas_h: int = 600) -> str:
    from diagrams.schemas.physics import ElectricFieldSchema
    schema = ElectricFieldSchema(**data)

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))
    ax.set_aspect("equal")
    ax.axis("off")

    charges = schema.charges
    if not charges:
        # Default: single positive charge
        from diagrams.schemas.physics import ElectricCharge
        charges = [ElectricCharge(x=0, y=0, charge=1, label="+q")]

    # Data coordinate range
    xpad = 3.0
    xs_c = [c.x for c in charges]
    ys_c = [c.y for c in charges]
    cx_r = (max(xs_c) + min(xs_c)) / 2 if len(xs_c) > 1 else 0
    cy_r = (max(ys_c) + min(ys_c)) / 2 if len(ys_c) > 1 else 0
    span = max(max(xs_c) - min(xs_c), max(ys_c) - min(ys_c), 0.1)
    ext = span / 2 + xpad
    ax.set_xlim(cx_r - ext, cx_r + ext)
    ax.set_ylim(cy_r - ext, cy_r + ext)

    # Compute E field on a grid
    grid_n = 30
    gx = np.linspace(cx_r - ext, cx_r + ext, grid_n)
    gy = np.linspace(cy_r - ext, cy_r + ext, grid_n)
    GX, GY = np.meshgrid(gx, gy)
    EX = np.zeros_like(GX)
    EY = np.zeros_like(GY)

    for c in charges:
        rx = GX - c.x
        ry = GY - c.y
        r2 = rx**2 + ry**2
        r2 = np.where(r2 < 0.04, 0.04, r2)
        r3 = r2 ** 1.5
        EX += c.charge * rx / r3
        EY += c.charge * ry / r3

    # Streamplot for field lines
    magnitude = np.sqrt(EX**2 + EY**2)
    magnitude = np.where(magnitude == 0, 1e-9, magnitude)
    ax.streamplot(GX, GY, EX, EY,
                  color="black", linewidth=1.2,
                  density=schema.num_lines / 8,
                  arrowsize=1.5, arrowstyle="->")

    # Draw charges as colored dots with labels
    for c in charges:
        color = "#cc0000" if c.charge > 0 else "#0044cc"
        ax.plot(c.x, c.y, "o", markersize=18, color=color, zorder=5)
        sign = "+" if c.charge > 0 else "−"
        ax.text(c.x, c.y, sign, color="white", fontsize=14, fontweight="bold",
                ha="center", va="center", zorder=6)
        if c.label:
            ax.text(c.x, c.y - ext * 0.15, c.label,
                    ha="center", va="top", fontsize=11, zorder=6)

    if schema.title:
        ax.set_title(schema.title, fontsize=13)

    fig.tight_layout(pad=0.3)
    return _fig_to_svg_phys(fig)


# ── 12. Magnetic Field Lines ──────────────────────────────────────────────────

def render_magnetic_field_lines(data: Dict[str, Any], canvas_w: int = 800, canvas_h: int = 600) -> str:
    from diagrams.schemas.physics import MagneticFieldSchema
    schema = MagneticFieldSchema(**data)

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))
    ax.set_aspect("equal")
    ax.axis("off")

    src = schema.source_type

    if src == "bar_magnet":
        # Dipole field: m along +x axis (N pole at right)
        L = 2.0   # half-length of magnet
        ax.set_xlim(-6, 6)
        ax.set_ylim(-5, 5)

        # Grid
        gx = np.linspace(-6, 6, 28)
        gy = np.linspace(-5, 5, 26)
        GX, GY = np.meshgrid(gx, gy)

        # Magnetic dipole field: B = (3(m·r̂)r̂ - m) / r³
        # m along x: Bx = (2x²-y²)/r⁵ * m, By = 3xy/r⁵ * m
        r2 = GX**2 + GY**2
        r2 = np.where(r2 < 0.25, 0.25, r2)
        r5 = r2 ** 2.5
        BX = (2 * GX**2 - GY**2) / r5
        BY = 3 * GX * GY / r5

        # Mask inside magnet body
        mask = (np.abs(GX) < L) & (np.abs(GY) < 0.55)
        BX = np.where(mask, 0, BX)
        BY = np.where(mask, 0, BY)

        ax.streamplot(GX, GY, BX, BY, color="black", linewidth=1.2,
                      density=1.2, arrowsize=1.4, arrowstyle="->")

        # Draw bar magnet
        magnet = mpatches.FancyBboxPatch((-L, -0.55), 2*L, 1.1,
                                         boxstyle="round,pad=0.05",
                                         facecolor="lightgray", edgecolor="black", linewidth=2)
        ax.add_patch(magnet)
        # N and S halves
        ax.add_patch(mpatches.FancyBboxPatch((0, -0.55), L, 1.1,
                                             boxstyle="round,pad=0",
                                             facecolor="#ffaaaa", edgecolor="black", linewidth=1.5))
        if schema.label_poles:
            ax.text(-L/2, 0, "S", ha="center", va="center",
                    fontsize=16, fontweight="bold", color="#0044cc")
            ax.text(L/2, 0, "N", ha="center", va="center",
                    fontsize=16, fontweight="bold", color="#cc0000")

    elif src == "straight_wire":
        # Current-carrying infinite wire (field circles)
        ax.set_xlim(-4, 4)
        ax.set_ylim(-4, 4)
        ax.plot(0, 0, "ko", markersize=14, zorder=5)
        direction = schema.current_direction
        dot_or_cross = "•" if direction == "out" else "×"
        ax.text(0, 0, dot_or_cross, ha="center", va="center",
                fontsize=16, fontweight="bold", color="white", zorder=6)
        ax.text(0, -0.55, "I", ha="center", va="top", fontsize=12)
        # Circular field lines
        for r in np.linspace(0.8, 3.2, schema.num_field_lines // 2):
            theta = np.linspace(0, 2 * math.pi, 200)
            ax.plot(r * np.cos(theta), r * np.sin(theta), "k-", linewidth=1.2)
            # Arrow at top of each circle
            arr_ang = math.pi / 2 + (0.08 if direction == "out" else -0.08)
            ax.annotate("", xy=(r * math.cos(arr_ang + 0.1), r * math.sin(arr_ang + 0.1)),
                        xytext=(r * math.cos(arr_ang), r * math.sin(arr_ang)),
                        arrowprops=dict(arrowstyle="->", color="black", lw=1.2))

    elif src == "solenoid":
        ax.set_xlim(-6, 6)
        ax.set_ylim(-5, 5)
        # Solenoid cross-section: rectangle with field inside
        sol_w, sol_h = 5.0, 2.0
        sol_rect = mpatches.Rectangle((-sol_w/2, -sol_h/2), sol_w, sol_h,
                                      facecolor="white", edgecolor="black", linewidth=2)
        ax.add_patch(sol_rect)
        # Coil symbols (dots and crosses on sides)
        for y_pos in np.linspace(-sol_h/2 + 0.3, sol_h/2 - 0.3, 5):
            ax.plot(-sol_w/2 - 0.1, y_pos, "ko", markersize=8)
            ax.text(-sol_w/2 - 0.1, y_pos, "•", ha="center", va="center",
                    fontsize=10, color="white", fontweight="bold")
            ax.plot(sol_w/2 + 0.1, y_pos, "ko", markersize=8)
            ax.text(sol_w/2 + 0.1, y_pos, "×", ha="center", va="center",
                    fontsize=9, color="white", fontweight="bold")
        # Field lines inside: horizontal arrows
        for y_pos in np.linspace(-sol_h/2 + 0.35, sol_h/2 - 0.35, 4):
            ax.annotate("", xy=(sol_w/2 - 0.3, y_pos), xytext=(-sol_w/2 + 0.3, y_pos),
                        arrowprops=dict(arrowstyle="->", color="black", lw=1.4))
        # Field lines outside: curved
        for x_mult in (-1, 1):
            for r in (2.8, 4.2):
                theta = np.linspace(-math.pi/2, math.pi/2, 100)
                ax.plot(x_mult * (sol_w/2 + r * np.abs(np.cos(theta))),
                        r * np.sin(theta), "k-", linewidth=1.0)
        if schema.label_poles:
            ax.text(-sol_w/2 - 0.6, 0, "S", ha="center", va="center",
                    fontsize=14, fontweight="bold", color="#0044cc")
            ax.text(sol_w/2 + 0.6, 0, "N", ha="center", va="center",
                    fontsize=14, fontweight="bold", color="#cc0000")
    else:
        ax.text(0, 0, f"source_type='{src}'\nnot supported", ha="center", va="center", fontsize=12)

    if schema.title:
        ax.set_title(schema.title, fontsize=13)

    fig.tight_layout(pad=0.3)
    return _fig_to_svg_phys(fig)


# ── 13. Circular Motion ───────────────────────────────────────────────────────

def render_circular_motion(data: Dict[str, Any], canvas_w: int = 800, canvas_h: int = 600) -> str:
    from diagrams.schemas.physics import CircularMotionSchema
    schema = CircularMotionSchema(**data)

    dwg = _base_drawing(canvas_w, canvas_h)
    cx, cy = canvas_w / 2, canvas_h / 2
    R = min(canvas_w, canvas_h) * 0.32

    # Draw circular path (dashed)
    dwg.add(dwg.circle(center=(cx, cy), r=R,
                       stroke=STROKE, stroke_width=1.5, fill="none",
                       stroke_dasharray="8,4"))

    # Center dot
    dwg.add(dwg.circle(center=(cx, cy), r=4, fill=STROKE))

    # Object position
    theta = math.radians(schema.object_angle_deg)
    ox = cx + R * math.cos(theta)
    oy = cy - R * math.sin(theta)   # flip y for SVG

    # Object (small filled circle)
    obj_r = 16
    dwg.add(dwg.circle(center=(ox, oy), r=obj_r,
                       fill="white", stroke=STROKE, stroke_width=2))
    _text(dwg, schema.mass_label, ox, oy + 5, size=13, bold=True)

    # Radius label along radius line
    dwg.add(dwg.line(start=(cx, cy), end=(ox, oy), stroke=STROKE, stroke_width=1.5))
    rx_mid = (cx + ox) / 2
    ry_mid = (cy + oy) / 2
    # Perp offset for label
    r_dx = ox - cx
    r_dy = oy - cy
    r_len = math.hypot(r_dx, r_dy) or 1
    perp_x, perp_y = -r_dy / r_len * 14, r_dx / r_len * 14
    _text(dwg, schema.radius_label, rx_mid + perp_x, ry_mid + perp_y, size=12)

    # Velocity arrow: tangent to circle (perpendicular to radius, in direction of motion)
    if schema.show_velocity:
        # Tangent direction (CCW motion): (-sin, -cos) in SVG coords
        vt_x = math.sin(theta)
        vt_y = math.cos(theta)
        v_len = R * 0.55
        v_end_x = ox + vt_x * v_len
        v_end_y = oy + vt_y * v_len
        _arrow(dwg, ox, oy, v_end_x, v_end_y, "",
               offset_x=0, offset_y=0, color=STROKE, stroke_w=2)
        # label v slightly offset
        _text(dwg, schema.velocity_label, v_end_x + vt_x * 12, v_end_y + vt_y * 12, size=13)

    # Centripetal force arrow: toward center
    if schema.show_centripetal:
        fc_len = R * 0.50
        fc_dx = (cx - ox) / R
        fc_dy = (cy - oy) / R
        fc_end_x = ox + fc_dx * fc_len
        fc_end_y = oy + fc_dy * fc_len
        # Start just outside object circle
        fc_start_x = ox + fc_dx * (obj_r + 4)
        fc_start_y = oy + fc_dy * (obj_r + 4)
        _arrow(dwg, fc_start_x, fc_start_y, fc_end_x, fc_end_y, "",
               offset_x=0, offset_y=0, color=STROKE, stroke_w=2)
        # Label Fc perpendicular to radius
        label_x = (fc_start_x + fc_end_x) / 2 - fc_dy * 16
        label_y = (fc_start_y + fc_end_y) / 2 + fc_dx * 16
        _text(dwg, schema.centripetal_label, label_x, label_y, size=12)

    # Angular velocity ω
    if schema.show_angular_velocity:
        arc_r = 30
        arc_path = (f"M {cx + arc_r},{cy} "
                    f"A {arc_r},{arc_r} 0 0,0 {cx},{cy - arc_r}")
        dwg.add(dwg.path(d=arc_path, fill="none", stroke=STROKE, stroke_width=1.5))
        _text(dwg, "ω", cx + arc_r + 14, cy - arc_r / 2, size=13)

    if schema.title:
        _text(dwg, schema.title, canvas_w / 2, 28, size=14, bold=True)

    return dwg.tostring()


# ── Doppler Effect ────────────────────────────────────────────────────────────

def render_doppler_effect(data: Dict[str, Any], canvas_w: int = 800, canvas_h: int = 600) -> str:
    from diagrams.schemas.physics import DopplerEffectSchema
    schema = DopplerEffectSchema(**data)

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))
    ax.set_aspect("equal")
    ax.set_xlim(-5, 5)
    ax.set_ylim(-4, 4)
    ax.axis("off")

    v = schema.source_velocity  # fraction of wave speed
    # Source position (moving to the right)
    sx = -1.0 if schema.direction == "right" else 1.0
    source_color = "#E74C3C"

    # Draw wavefronts: circles centred at previous source positions
    n = schema.num_wavefronts
    wave_color = "#2980B9"
    for i in range(1, n + 1):
        # time since emission: i (arbitrary units); source moved v*i to the right
        t = i
        if schema.direction == "right":
            cx_wf = sx - v * t  # source was further left in the past
        else:
            cx_wf = sx + v * t
        r = t  # radius grows at wave speed = 1 unit/time
        circle = plt.Circle((cx_wf, 0), r, fill=False, color=wave_color,
                             linewidth=1.2, alpha=max(0.3, 1 - i / (n + 2)))
        ax.add_patch(circle)

    # Source
    ax.plot(sx, 0, "o", color=source_color, markersize=14, zorder=5)
    if schema.show_labels:
        ax.text(sx, -0.6, "Source", ha="center", fontsize=9, color=source_color)
        # velocity arrow
        arrow_dx = 1.2 if schema.direction == "right" else -1.2
        ax.annotate("", xy=(sx + arrow_dx, 0), xytext=(sx, 0),
                    arrowprops=dict(arrowstyle="->", color=source_color, lw=1.5))
        ax.text(sx + arrow_dx / 2, 0.35, f"v = {v}c", ha="center", fontsize=8, color=source_color)

    # Observer
    if schema.show_observer:
        obs_x = 4.0 if schema.observer_side == "right" else -4.0
        ax.plot(obs_x, 0, "^", color="#27AE60", markersize=13, zorder=5)
        if schema.show_labels:
            ax.text(obs_x, -0.6, "Observer", ha="center", fontsize=9, color="#27AE60")

    if schema.show_frequency_labels:
        if schema.show_observer and schema.observer_side == "right":
            ax.text(3.0, 2.5, "f' > f\n(compressed)", ha="center", fontsize=8,
                    color="#1A5276",
                    bbox=dict(boxstyle="round,pad=0.3", facecolor="#D6EAF8", alpha=0.8))
        else:
            ax.text(-3.0, 2.5, "f' < f\n(stretched)", ha="center", fontsize=8,
                    color="#784212",
                    bbox=dict(boxstyle="round,pad=0.3", facecolor="#FDEBD0", alpha=0.8))

    if schema.title:
        ax.set_title(schema.title, fontsize=12, fontweight="bold")
    else:
        ax.set_title("Doppler Effect", fontsize=12, fontweight="bold")

    fig.tight_layout()
    return _fig_to_svg_phys(fig)


# ── Interference / Diffraction Pattern ───────────────────────────────────────

def render_interference_pattern(data: Dict[str, Any], canvas_w: int = 800, canvas_h: int = 600) -> str:
    from diagrams.schemas.physics import InterferencePatternSchema
    schema = InterferencePatternSchema(**data)

    fig, (ax_top, ax_bot) = plt.subplots(
        2, 1, figsize=(canvas_w / 100, canvas_h / 100),
        gridspec_kw={"height_ratios": [1, 2]})

    # Map wavelength to an approximate color
    wl = schema.wavelength
    if wl < 380:
        wl_color = "#8B00FF"
    elif wl < 450:
        wl_color = "#6600CC"
    elif wl < 495:
        wl_color = "#0000FF"
    elif wl < 570:
        wl_color = "#00AA00"
    elif wl < 590:
        wl_color = "#CCCC00"
    elif wl < 620:
        wl_color = "#FF8000"
    else:
        wl_color = "#FF0000"

    # Screen pattern (top axes) — schematic bright/dark bands
    n_max = schema.num_maxima
    positions = list(range(-n_max, n_max + 1))  # order m
    ax_top.set_xlim(-n_max - 1, n_max + 1)
    ax_top.set_ylim(0, 1)
    ax_top.axis("off")
    for m in positions:
        brightness = 1.0 if schema.pattern_type == "double_slit" else max(0, 1 - abs(m) * 0.3)
        alpha = brightness
        ax_top.axvspan(m - 0.35, m + 0.35, color=wl_color, alpha=alpha)
        if schema.show_order_labels and abs(m) <= 2:
            lbl = "0" if m == 0 else (f"+{m}" if m > 0 else str(m))
            ax_top.text(m, -0.3, f"m={lbl}", ha="center", fontsize=7)
    ax_top.set_title("Fringe pattern on screen", fontsize=9)

    # Intensity curve (bottom axes)
    if schema.show_intensity_curve:
        theta = np.linspace(-np.pi * 2, np.pi * 2, 2000)
        if schema.pattern_type == "double_slit":
            d = schema.slit_separation
            I = np.cos(d * theta / 2) ** 2
        else:
            I = np.sinc(theta / np.pi) ** 2

        x_pos = theta / np.pi * n_max
        ax_bot.plot(x_pos, I, color=wl_color, linewidth=1.8)
        ax_bot.fill_between(x_pos, 0, I, color=wl_color, alpha=0.25)
        ax_bot.set_xlim(-n_max - 1, n_max + 1)
        ax_bot.set_xlabel("Position on screen →", fontsize=9)
        ax_bot.set_ylabel("Intensity", fontsize=9)
        ax_bot.set_ylim(0, 1.2)
        ax_bot.yaxis.set_ticks([0, 0.5, 1.0])
        ax_bot.tick_params(labelsize=8)
        ax_bot.spines["top"].set_visible(False)
        ax_bot.spines["right"].set_visible(False)
        if schema.show_central_max:
            ax_bot.axvline(0, color="gray", linestyle="--", linewidth=0.8, alpha=0.6)
            ax_bot.text(0.15, 1.05, "Central max", fontsize=7, color="gray")

    title = schema.title or (
        "Double-Slit Interference" if schema.pattern_type == "double_slit"
        else "Single-Slit Diffraction"
    )
    fig.suptitle(title, fontsize=12, fontweight="bold")
    fig.tight_layout()
    return _fig_to_svg_phys(fig)


# ── Bohr Atom Model ───────────────────────────────────────────────────────────

def render_bohr_atom(data: Dict[str, Any], canvas_w: int = 800, canvas_h: int = 600) -> str:
    from diagrams.schemas.physics import BohrAtomSchema
    schema = BohrAtomSchema(**data)

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))
    ax.set_aspect("equal")
    n = schema.num_shells
    r_max = n * 1.0 + 0.5
    ax.set_xlim(-r_max - 0.5, r_max + 1.5)
    ax.set_ylim(-r_max - 0.5, r_max + 0.5)
    ax.axis("off")

    # Default electron configuration if not provided
    default_e = [2, 8, 18, 32, 32, 18, 8]
    electrons = schema.electrons_per_shell if schema.electrons_per_shell else default_e[:n]
    while len(electrons) < n:
        electrons.append(0)

    shell_colors = ["#3498DB", "#E74C3C", "#2ECC71", "#F39C12", "#9B59B6", "#1ABC9C", "#E67E22"]

    # Draw shells
    for i in range(1, n + 1):
        r = i * 1.0
        circle = plt.Circle((0, 0), r, fill=False,
                             color=shell_colors[(i - 1) % len(shell_colors)],
                             linewidth=1.2, linestyle="--", alpha=0.7)
        ax.add_patch(circle)
        # Shell label n=i
        ax.text(r + 0.1, 0.1, f"n={i}", fontsize=7,
                color=shell_colors[(i - 1) % len(shell_colors)])

        # Draw electrons
        ne = electrons[i - 1] if i - 1 < len(electrons) else 0
        for j in range(min(ne, 8)):  # max 8 shown per shell
            angle = 2 * np.pi * j / max(ne, 1)
            ex = r * np.cos(angle)
            ey = r * np.sin(angle)
            ax.plot(ex, ey, "o", color=shell_colors[(i - 1) % len(shell_colors)],
                    markersize=5, zorder=5)

    # Nucleus
    if schema.show_nucleus:
        nucleus = plt.Circle((0, 0), 0.3, color="#E74C3C", zorder=6)
        ax.add_patch(nucleus)
        nuc_label = schema.nucleus_label or schema.element
        ax.text(0, 0, nuc_label, ha="center", va="center", fontsize=8,
                fontweight="bold", color="white", zorder=7)

    # Transitions
    transition_colors = ["red", "blue", "green", "orange", "purple"]
    for idx, tr in enumerate(schema.transitions):
        r1 = tr.from_shell * 1.0
        r2 = tr.to_shell * 1.0
        angle = np.pi * 0.3 + idx * 0.4
        # Arrow from outer to inner (emission) or inner to outer (absorption)
        x1 = r1 * np.cos(angle)
        y1 = r1 * np.sin(angle)
        x2 = r2 * np.cos(angle)
        y2 = r2 * np.sin(angle)
        tc = tr.color if tr.color else transition_colors[idx % len(transition_colors)]
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="->", color=tc, lw=1.5))
        if tr.label:
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            ax.text(mx + 0.15, my, tr.label, fontsize=7, color=tc)

    # Energy level labels on the right
    if schema.show_energy_levels:
        e_levels = [-13.6 / (i ** 2) for i in range(1, n + 1)]
        x_lev = r_max + 0.3
        for i, E in enumerate(e_levels):
            r = (i + 1) * 1.0
            ax.plot([r, x_lev], [0, E / abs(e_levels[0]) * r_max * 0.5],
                    ":", color="gray", linewidth=0.6, alpha=0.5)
            ax.text(x_lev + 0.1, E / abs(e_levels[0]) * r_max * 0.5,
                    f"{E:.1f} eV", fontsize=7, color="gray", va="center")

    title = schema.title or f"Bohr Model: {schema.element}"
    ax.set_title(title, fontsize=12, fontweight="bold")
    fig.tight_layout()
    return _fig_to_svg_phys(fig)


# ── Capacitor with Dielectric ─────────────────────────────────────────────────

def render_capacitor_dielectric(data: Dict[str, Any], canvas_w: int = 800, canvas_h: int = 600) -> str:
    from diagrams.schemas.physics import CapacitorDielectricSchema
    schema = CapacitorDielectricSchema(**data)

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 8)
    ax.axis("off")

    # Plate positions
    plate_x_left = 2.5
    plate_x_right = 7.5
    plate_y_bot = 1.5
    plate_y_top = 6.5
    plate_thick = 0.25

    # Dielectric fill
    ax.add_patch(mpatches.FancyBboxPatch(
        (plate_x_left + plate_thick, plate_y_bot),
        plate_x_right - plate_x_left - 2 * plate_thick,
        plate_y_top - plate_y_bot,
        boxstyle="square,pad=0",
        facecolor="#D5E8D4", edgecolor="#82B366", linewidth=1.5, alpha=0.8))
    # Dielectric label
    ax.text((plate_x_left + plate_x_right) / 2, (plate_y_bot + plate_y_top) / 2,
            schema.dielectric_label, ha="center", va="center",
            fontsize=11, color="#2D7600", fontweight="bold")

    # Plates
    for px, label, charge_labels in [
        (plate_x_left, schema.plate_label_pos, True),
        (plate_x_right - plate_thick, schema.plate_label_neg, False)
    ]:
        ax.add_patch(mpatches.FancyBboxPatch(
            (px, plate_y_bot), plate_thick, plate_y_top - plate_y_bot,
            boxstyle="square,pad=0",
            facecolor="#1B4F72", edgecolor="#1B4F72"))
        charge_x = px - 0.5 if charge_labels else px + plate_thick + 0.2
        for cy in np.linspace(plate_y_bot + 0.5, plate_y_top - 0.5, 5):
            ax.text(charge_x, cy, "+" if charge_labels else "−",
                    ha="center", va="center", fontsize=12,
                    color="#E74C3C" if charge_labels else "#2980B9",
                    fontweight="bold")

    # Induced charges on dielectric surfaces
    if schema.show_induced_charges:
        for cy in np.linspace(plate_y_bot + 0.5, plate_y_top - 0.5, 4):
            ax.text(plate_x_left + plate_thick + 0.2, cy, "−",
                    ha="center", va="center", fontsize=10, color="#2980B9", alpha=0.7)
            ax.text(plate_x_right - plate_thick - 0.2, cy, "+",
                    ha="center", va="center", fontsize=10, color="#E74C3C", alpha=0.7)

    # Field lines (left to right inside dielectric)
    if schema.show_field_lines:
        n_lines = schema.num_field_lines
        for fy in np.linspace(plate_y_bot + 0.6, plate_y_top - 0.6, n_lines):
            ax.annotate("", xy=(plate_x_right - plate_thick - 0.05, fy),
                        xytext=(plate_x_left + plate_thick + 0.05, fy),
                        arrowprops=dict(arrowstyle="->", color="#E74C3C", lw=0.8, alpha=0.6))

    # Voltage label on top
    ax.annotate("", xy=(plate_x_right + 0.1, plate_y_top + 0.8),
                xytext=(plate_x_left - 0.1, plate_y_top + 0.8),
                arrowprops=dict(arrowstyle="<->", color="#8E44AD", lw=1.5))
    ax.text((plate_x_left + plate_x_right) / 2, plate_y_top + 1.1,
            schema.voltage_label, ha="center", fontsize=12, color="#8E44AD", fontweight="bold")

    # Formula
    if schema.show_capacitance_formula:
        ax.text(5.0, 0.5, "C = κε₀A/d", ha="center", fontsize=11,
                color="#17202A",
                bbox=dict(boxstyle="round,pad=0.4", facecolor="#EBF5FB", alpha=0.9))

    title = schema.title or "Capacitor with Dielectric"
    ax.set_title(title, fontsize=13, fontweight="bold", pad=8)
    fig.tight_layout()
    return _fig_to_svg_phys(fig)


# ── LC Circuit Oscillation ────────────────────────────────────────────────────

def render_lc_oscillation(data: Dict[str, Any], canvas_w: int = 800, canvas_h: int = 600) -> str:
    from diagrams.schemas.physics import LCOscillationSchema
    schema = LCOscillationSchema(**data)

    rows = (2 if schema.show_circuit else 0) + (1 if schema.show_graphs else 0)
    if rows == 0:
        rows = 1
    fig = plt.figure(figsize=(canvas_w / 100, canvas_h / 100))

    if schema.show_circuit and schema.show_graphs:
        gs = fig.add_gridspec(2, 1, height_ratios=[1, 2], hspace=0.4)
        ax_circ = fig.add_subplot(gs[0])
        ax_graph = fig.add_subplot(gs[1])
    elif schema.show_circuit:
        ax_circ = fig.add_subplot(111)
        ax_graph = None
    else:
        ax_circ = None
        ax_graph = fig.add_subplot(111)

    # Circuit diagram
    if ax_circ is not None:
        ax_circ.set_xlim(0, 10)
        ax_circ.set_ylim(0, 5)
        ax_circ.axis("off")

        # Rectangle circuit loop
        loop_pts = [(1, 1), (9, 1), (9, 4), (1, 4), (1, 1)]
        xs, ys = zip(*loop_pts)
        ax_circ.plot(xs, ys, "k-", linewidth=2)

        # Inductor on top: wavy line
        L_x = np.linspace(2, 5, 100)
        L_y = 4 + 0.25 * np.sin(L_x * 5)
        ax_circ.plot(L_x, L_y, color="#2980B9", linewidth=2.5)
        ax_circ.text(3.5, 4.45, schema.inductance_label, ha="center", fontsize=10,
                     color="#2980B9", fontweight="bold")

        # Capacitor on bottom: two parallel lines
        cap_cx = 5.0
        ax_circ.plot([cap_cx - 1, cap_cx + 1], [1, 1], "k-", linewidth=2)
        ax_circ.plot([cap_cx - 0.5, cap_cx + 0.5], [1.25, 1.25], color="#E74C3C", linewidth=4)
        ax_circ.plot([cap_cx - 0.5, cap_cx + 0.5], [0.75, 0.75], color="#E74C3C", linewidth=4)
        ax_circ.text(cap_cx, 0.25, schema.capacitance_label, ha="center", fontsize=10,
                     color="#E74C3C", fontweight="bold")

        # Current arrow
        ax_circ.annotate("", xy=(8.5, 2.5), xytext=(7.0, 2.5),
                         arrowprops=dict(arrowstyle="->", color="#27AE60", lw=1.5))
        ax_circ.text(7.75, 2.9, "I", fontsize=10, color="#27AE60", ha="center")

        ax_circ.set_title("LC Oscillation Circuit", fontsize=10, fontweight="bold")

    # Oscillation graphs
    if ax_graph is not None:
        t = np.linspace(0, schema.num_cycles * 2 * np.pi, 500)
        phase = 0 if schema.initial_state == "charged" else np.pi / 2

        Q = np.cos(t + phase)
        I_curr = -np.sin(t + phase)
        U_E = Q ** 2
        U_B = I_curr ** 2

        ax_graph.plot(t / (2 * np.pi), Q, label="Q (charge)", color="#E74C3C", linewidth=1.8)
        ax_graph.plot(t / (2 * np.pi), I_curr, label="I (current)", color="#2980B9",
                      linewidth=1.8, linestyle="--")
        if schema.show_energy_labels:
            ax_graph.plot(t / (2 * np.pi), U_E, label="U_E (electric)", color="#F39C12",
                          linewidth=1.2, linestyle=":")
            ax_graph.plot(t / (2 * np.pi), U_B, label="U_B (magnetic)", color="#27AE60",
                          linewidth=1.2, linestyle="-.")

        ax_graph.set_xlabel("Time (T)", fontsize=9)
        ax_graph.set_ylabel("Amplitude", fontsize=9)
        ax_graph.legend(fontsize=7, loc="upper right", ncol=2)
        ax_graph.axhline(0, color="gray", linewidth=0.5)
        ax_graph.tick_params(labelsize=8)
        ax_graph.spines["top"].set_visible(False)
        ax_graph.spines["right"].set_visible(False)
        ax_graph.set_title("Oscillation vs. Time", fontsize=10)

    title = schema.title or "LC Circuit Oscillation"
    fig.suptitle(title, fontsize=12, fontweight="bold", y=1.01)
    fig.tight_layout()
    return _fig_to_svg_phys(fig)


# ══════════════════════════════════════════════════════════════════════════════
# Modern Physics, Semiconductors, EM Waves, TIR, Rotational Inertia
# ══════════════════════════════════════════════════════════════════════════════

PLANCK_EV_S = 4.135667696e-15     # h in eV·s; h/e = 4.1357e-15 V·s (slope of V₀-ν line)
THERMAL_VOLTAGE_V = 0.026         # kT/q at 300 K
DIODE_IDEALITY = 1.8


# ── p-n Junction physics ──────────────────────────────────────────────────────

BUILT_IN_POTENTIAL_V = 0.70       # V_bi for a silicon junction

# Applied voltage per bias state. Sign convention: positive = p-side held
# positive with respect to the n-side.
_PN_APPLIED_V = {"unbiased": 0.0, "forward": 0.40, "reverse": -1.50}


def _pn_junction_state(bias: str) -> Tuple[float, float]:
    """(depletion_width_normalised, barrier_potential_V) for a bias state.

    The net barrier is V_bi − V_applied and the depletion width goes as
    √(V_bi − V_applied). Forward bias therefore NARROWS the layer and LOWERS the
    barrier; reverse bias widens and raises it. Both come out of one expression
    here precisely so the two can never drift apart into the inverse (and wrong)
    behaviour.
    """
    barrier = BUILT_IN_POTENTIAL_V - _PN_APPLIED_V[bias]
    width = math.sqrt(barrier / BUILT_IN_POTENTIAL_V)
    return width, barrier


def render_pn_junction(data: Dict[str, Any], canvas_w: int = 800, canvas_h: int = 600) -> str:
    from diagrams.schemas.physics import PNJunctionSchema
    schema = PNJunctionSchema(**data)

    bias = schema.bias
    width_norm, barrier_v = _pn_junction_state(bias)

    if schema.show_barrier_potential:
        fig, (ax, ax_v) = plt.subplots(
            2, 1, figsize=(canvas_w / 100, canvas_h / 100),
            gridspec_kw={"height_ratios": [2, 1]})
    else:
        fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))
        ax_v = None

    ax.set_xlim(-5.2, 5.2)
    ax.set_ylim(-2.6, 2.4)
    ax.axis("off")

    bar_bot, bar_top = 0.35, 1.75
    bar_mid = (bar_bot + bar_top) / 2
    x_left, x_right = -3.6, 3.6

    # Half-width of the depletion layer on the drawing; 0.55 at zero bias
    w = 0.55 * width_norm

    ax.add_patch(mpatches.Rectangle((x_left, bar_bot), -x_left, bar_top - bar_bot,
                                    facecolor="#FDEBD0", edgecolor="black", linewidth=1.8))
    ax.add_patch(mpatches.Rectangle((0, bar_bot), x_right, bar_top - bar_bot,
                                    facecolor="#D6EAF8", edgecolor="black", linewidth=1.8))
    ax.text(-2.4, bar_mid, "p", ha="center", va="center", fontsize=20, fontweight="bold")
    ax.text(2.4, bar_mid, "n", ha="center", va="center", fontsize=20, fontweight="bold")

    if schema.show_depletion_region:
        ax.add_patch(mpatches.Rectangle((-w, bar_bot), 2 * w, bar_top - bar_bot,
                                        facecolor="#EAECEE", edgecolor="black",
                                        linewidth=1.2, hatch="///", zorder=3))
        # Immobile ionised dopants left behind: acceptors (−) in p, donors (+) in n
        for yy in (bar_bot + 0.35, bar_top - 0.35):
            ax.text(-w / 2, yy, "−", ha="center", va="center", fontsize=13,
                    color="#1B4F72", fontweight="bold", zorder=4)
            ax.text(w / 2, yy, "+", ha="center", va="center", fontsize=13,
                    color="#922B21", fontweight="bold", zorder=4)
        ax.annotate("", xy=(-w, bar_top + 0.18), xytext=(w, bar_top + 0.18),
                    arrowprops=dict(arrowstyle="<->", color="black", lw=1.2))
        ax.text(0, bar_top + 0.32, f"Depletion region  (W = {width_norm:.2f} W₀)",
                ha="center", va="bottom", fontsize=9)

    if schema.show_carriers:
        # Majority carriers outside the depletion layer: holes ○ in p, electrons ● in n
        for yy in (bar_bot + 0.33, bar_top - 0.33):
            for xx in np.linspace(x_left + 0.35, -w - 0.3, 4):
                ax.plot(xx, yy, "o", markersize=8, markerfacecolor="white",
                        markeredgecolor="black", markeredgewidth=1.2, zorder=4)
            for xx in np.linspace(w + 0.3, x_right - 0.35, 4):
                ax.plot(xx, yy, "o", markersize=8, color="black", zorder=4)
        ax.text(x_left, bar_bot - 0.28, "○ holes", ha="left", va="top", fontsize=9)
        ax.text(x_right, bar_bot - 0.28, "● electrons", ha="right", va="top", fontsize=9)

    if schema.show_battery and bias != "unbiased":
        wire_y = -1.75
        # Forward bias = p-side to the + terminal; reverse = p-side to the −.
        long_plate_x = -0.18 if bias == "forward" else 0.18
        short_plate_x = 0.18 if bias == "forward" else -0.18
        ax.plot([x_left, x_left], [bar_bot, wire_y], "k-", linewidth=1.8)
        ax.plot([x_right, x_right], [bar_bot, wire_y], "k-", linewidth=1.8)
        ax.plot([x_left, -0.18], [wire_y, wire_y], "k-", linewidth=1.8)
        ax.plot([0.18, x_right], [wire_y, wire_y], "k-", linewidth=1.8)
        ax.plot([long_plate_x, long_plate_x], [wire_y - 0.32, wire_y + 0.32],
                "k-", linewidth=2.5)
        ax.plot([short_plate_x, short_plate_x], [wire_y - 0.18, wire_y + 0.18],
                "k-", linewidth=2.5)
        ax.text(long_plate_x - 0.28 * (1 if long_plate_x < 0 else -1), wire_y + 0.5,
                "+", ha="center", va="center", fontsize=14, fontweight="bold")
        ax.text(short_plate_x - 0.28 * (1 if short_plate_x < 0 else -1), wire_y + 0.5,
                "−", ha="center", va="center", fontsize=14, fontweight="bold")
        ax.text(0, wire_y - 0.55, f"{bias.capitalize()} bias",
                ha="center", va="center", fontsize=10, fontweight="bold")

        if schema.show_current_arrow:
            # Conventional current leaves the + plate. Forward: it runs left along
            # the wire, up through p → n. Reverse: the opposite sense, and the
            # magnitude collapses to the µA leakage current.
            if bias == "forward":
                ax.annotate("", xy=(-2.8, wire_y), xytext=(-1.7, wire_y),
                            arrowprops=dict(arrowstyle="-|>", color="#C0392B", lw=2.2))
                ax.text(-2.25, wire_y + 0.22, "I (mA)", ha="center", va="bottom",
                        fontsize=10, color="#C0392B", fontweight="bold")
            else:
                ax.annotate("", xy=(-1.7, wire_y), xytext=(-2.4, wire_y),
                            arrowprops=dict(arrowstyle="-|>", color="#C0392B", lw=1.0))
                ax.text(-2.25, wire_y + 0.22, "I ≈ 0 (µA)", ha="center", va="bottom",
                        fontsize=10, color="#C0392B")

    if ax_v is not None:
        xs = np.linspace(x_left, x_right, 400)
        # Potential climbs from the p-side to the n-side across the depletion layer;
        # the transition is exactly as wide as that layer.
        vs = barrier_v * 0.5 * (1 + np.tanh(xs / (0.55 * w)))
        ax_v.plot(xs, vs, color="#1B4F72", linewidth=2.4)
        ax_v.set_xlim(-5.2, 5.2)
        ax_v.set_ylim(-0.25, 2.75)
        ax_v.axvline(-w, color="gray", linestyle="--", linewidth=0.9)
        ax_v.axvline(w, color="gray", linestyle="--", linewidth=0.9)
        ax_v.plot([x_right, 4.7], [barrier_v, barrier_v], color="#C0392B",
                  linestyle=":", linewidth=0.9)
        if barrier_v >= 0.5:
            # Below ~0.5 V the two arrowheads would collide into an unreadable blob;
            # the dotted level line and the label carry the value on their own.
            ax_v.annotate("", xy=(4.3, barrier_v), xytext=(4.3, 0),
                          arrowprops=dict(arrowstyle="<->", color="#C0392B", lw=1.4))
        ax_v.text(4.3, barrier_v + 0.18, f"V_B = {barrier_v:.2f} V", ha="center",
                  va="bottom", fontsize=11, color="#C0392B", fontweight="bold")
        ax_v.set_ylabel("V (volts)", fontsize=10)
        ax_v.set_xticks([])
        ax_v.tick_params(labelsize=8)
        ax_v.spines["top"].set_visible(False)
        ax_v.spines["right"].set_visible(False)
        ax_v.set_title("Barrier potential", fontsize=10)

    title = schema.title or f"p-n Junction ({bias} bias)"
    fig.suptitle(title, fontsize=13, fontweight="bold")
    fig.tight_layout()
    return _fig_to_svg_phys(fig)


# ── Semiconductor I-V Characteristics ─────────────────────────────────────────

_IV_KNEE_DEFAULT = {"pn_diode": 0.7, "zener": 0.7, "led": 1.8, "photodiode": 0.7,
                    "transistor_ce": 0.7, "transistor_input": 0.7}
_IV_BREAKDOWN_DEFAULT = {"zener": 6.0}

_UA_PER_UNIT = 5.0      # reverse branch is drawn on a magnified µA scale, as in NCERT


def _diode_current_mA(v: "np.ndarray", knee: float) -> "np.ndarray":
    """Shockley equation, with I_s pinned so that I(knee) = 1 mA.

    Deriving the whole curve from one equation is what keeps the reverse branch
    honest: for V < 0 it tends to −I_s (nanoamps), which on a mA scale is the
    flat line along the axis that the exam question turns on.
    """
    scale = DIODE_IDEALITY * THERMAL_VOLTAGE_V
    i_s = 1.0 / (math.exp(knee / scale) - 1.0)
    return i_s * (np.exp(v / scale) - 1.0)


def render_semiconductor_iv(data: Dict[str, Any], canvas_w: int = 800, canvas_h: int = 600) -> str:
    from diagrams.schemas.physics import SemiconductorIVSchema
    schema = SemiconductorIVSchema(**data)

    device = schema.device
    knee = schema.knee_voltage if schema.knee_voltage is not None else _IV_KNEE_DEFAULT[device]
    breakdown = (schema.breakdown_voltage if schema.breakdown_voltage is not None
                 else _IV_BREAKDOWN_DEFAULT.get(device))

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))
    scale = DIODE_IDEALITY * THERMAL_VOLTAGE_V

    if device == "transistor_ce":
        # Output characteristics: I_C vs V_CE, one curve per base current.
        beta = 100
        vce = np.linspace(0, 10, 400)
        for i_b_uA in (10, 20, 30, 40):
            i_c_sat = beta * i_b_uA / 1000.0                       # mA
            # Knee at V_CE ≈ 0.3 V (saturation), then a gentle Early-effect slope
            i_c = i_c_sat * (1 - np.exp(-vce / 0.25)) * (1 + 0.02 * vce)
            ax.plot(vce, i_c, linewidth=2.0)
            ax.text(10.15, i_c[-1], f"I_B = {i_b_uA} µA", fontsize=9, va="center")
        ax.plot(vce, np.full_like(vce, 0.04), "k--", linewidth=1.2)
        ax.text(10.15, 0.04, "I_B = 0", fontsize=9, va="center")
        ax.set_xlim(0, 13.6)
        ax.set_ylim(0, 5.4)
        ax.set_xlabel("V_CE (volts) →", fontsize=11)
        ax.set_ylabel("I_C (mA) →", fontsize=11)
        if schema.label_regions:
            ax.axvspan(0, 0.3, color="#F9E79F", alpha=0.6)
            ax.text(0.45, 5.1, "Saturation", fontsize=9, rotation=90,
                    va="top", ha="left", color="#7D6608")
            ax.text(5.0, 4.9, "Active region", fontsize=10, ha="center", color="#1B4F72")
            ax.text(5.0, 0.28, "Cut-off", fontsize=9, ha="center", color="#7B241C")
        title = schema.title or "Common-Emitter Output Characteristics"

    elif device == "transistor_input":
        # Input characteristics: I_B vs V_BE — a forward-biased base-emitter diode.
        vbe = np.linspace(0, 0.88, 400)
        i_0 = 20.0 / (math.exp(knee / scale) - 1.0)     # 20 µA at the knee
        for vce_val, ls in ((5.0, "-"), (10.0, "--")):
            # A higher V_CE widens the depletion layer and trims I_B slightly
            shift = 0.012 * (vce_val - 5.0) / 5.0
            i_b = i_0 * (np.exp((vbe - shift) / scale) - 1.0)
            ax.plot(vbe, i_b, ls, linewidth=2.0, label=f"V_CE = {vce_val:.0f} V")
        ax.set_xlim(0, 0.9)
        ax.set_ylim(0, 140)
        ax.set_xlabel("V_BE (volts) →", fontsize=11)
        ax.set_ylabel("I_B (µA) →", fontsize=11)
        ax.legend(fontsize=9, loc="upper left")
        if schema.label_regions:
            ax.axvline(knee, color="gray", linestyle=":", linewidth=1.2)
            ax.text(knee - 0.02, 130, f"Knee ≈ {knee:.1f} V", fontsize=9,
                    ha="right", color="#7B241C")
        title = schema.title or "Common-Emitter Input Characteristics"

    elif device == "photodiode":
        # Reverse-biased; the reverse current is set by illumination, not by V.
        v_min = -(breakdown * 1.25) if breakdown else -6.0
        vr = np.linspace(v_min, 0.0, 300)
        for k, i_ph_uA in enumerate((10.0, 20.0, 30.0), start=1):
            i_uA = i_ph_uA * (1 - np.exp(vr / scale))     # → i_ph for V ≪ 0, → 0 at V = 0
            ax.plot(vr, -(i_uA / _UA_PER_UNIT), linewidth=2.0)
            ax.text(v_min + 0.15, -(i_ph_uA / _UA_PER_UNIT) - 0.35,
                    f"I{'₁₂₃'[k - 1]}", fontsize=10, va="top")
        ax.set_xlim(v_min - 0.4, 1.2)
        ax.set_ylim(-8.5, 2.0)
        ax.text(v_min * 0.55, -7.6, "I₁ < I₂ < I₃  (increasing illumination)",
                fontsize=9, ha="center", color="#1B4F72")
        _iv_signed_axes(ax, reverse_only=True)
        title = schema.title or "Photodiode I-V Characteristics"

    else:   # pn_diode | zener | led — two-quadrant characteristic
        i_s = 1.0 / (math.exp(knee / scale) - 1.0)
        v_max = scale * math.log(30.0 / i_s + 1.0)
        v_min = -(breakdown * 1.30) if breakdown else -6.0

        vf = np.linspace(0, v_max, 300)
        ax.plot(vf, _diode_current_mA(vf, knee), color="#1B4F72", linewidth=2.4)

        vr = np.linspace(v_min, 0.0, 600)
        # Reverse saturation current ≈ 1 µA, flat, until breakdown drops it vertically
        i_rev_uA = 1.0 * (1 - np.exp(vr / scale))
        if breakdown:
            i_rev_uA = i_rev_uA + 60.0 * np.exp((np.abs(vr) - breakdown) / 0.06)
            i_rev_uA = np.minimum(i_rev_uA, 60.0)
        ax.plot(vr, -(i_rev_uA / _UA_PER_UNIT), color="#1B4F72", linewidth=2.4)

        ax.set_xlim(v_min - 0.5, v_max + 0.9)
        ax.set_ylim(-13.5, 33)
        _iv_signed_axes(ax)

        if schema.label_regions:
            ax.axvline(knee, color="gray", linestyle=":", linewidth=1.0)
            ax.text(knee - 0.08, 21, f"Knee = {knee:.1f} V", fontsize=9, ha="right",
                    color="#7B241C")
            ax.text(v_max * 0.5, 31, "Forward bias", fontsize=10, ha="center",
                    color="#1B4F72")
            ax.text(v_min * 0.5, 2.4, "Reverse bias  (I ≈ I₀, µA)", fontsize=9,
                    ha="center", color="#1B4F72")
            if breakdown:
                ax.axvline(-breakdown, color="#C0392B", linestyle="--", linewidth=1.0)
                ax.text(-breakdown - 0.25, -8.0, f"Breakdown\nV_Z = {breakdown:.1f} V",
                        fontsize=9, ha="right", va="center", color="#C0392B",
                        fontweight="bold")

        if schema.show_quadrant_labels:
            ax.text(v_max + 0.55, 14, "I", fontsize=13, style="italic", color="gray")
            ax.text(v_min * 0.62, -11.0, "III", fontsize=13, style="italic", color="gray")

        _name = {"pn_diode": "p-n Junction Diode", "zener": "Zener Diode", "led": "LED"}
        title = schema.title or f"{_name[device]} I-V Characteristics"

    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return _fig_to_svg_phys(fig)


def _iv_signed_axes(ax, reverse_only: bool = False):
    """Forward current in mA above the origin, reverse current in µA below it.

    Two scales on one axis is the textbook convention, and it is the only way a
    µA leakage current and a 30 mA forward current fit on one figure — but the
    tick labels must state their own units or the reverse branch reads as mA.
    """
    ax.axhline(0, color="black", linewidth=1.0)
    ax.axvline(0, color="black", linewidth=1.0)
    ax.spines["left"].set_visible(False)
    ax.spines["bottom"].set_visible(False)
    if reverse_only:
        ticks = [-8, -6, -4, -2, 0]
        labels = ["40 µA", "30 µA", "20 µA", "10 µA", "O"]
    else:
        ticks = [-12, -8, -4, 0, 10, 20, 30]
        labels = ["60 µA", "40 µA", "20 µA", "O", "10 mA", "20 mA", "30 mA"]
    ax.set_yticks(ticks)
    ax.set_yticklabels(labels, fontsize=8)
    ax.tick_params(labelsize=8)
    ax.set_xlabel("V (volts) →", fontsize=11)
    ax.set_ylabel("I (mA) ↑   /   I (µA) ↓", fontsize=10)


# ── Photoelectric Effect ──────────────────────────────────────────────────────

def _threshold_frequency_hz(work_function_ev: float) -> float:
    """ν₀ = φ/h — below it, no emission at any intensity."""
    return work_function_ev / PLANCK_EV_S


def _stopping_potential_v(freq_hz: float, work_function_ev: float) -> float:
    """V₀ = (hν − φ)/e — a function of FREQUENCY ONLY.

    Intensity sets how many photoelectrons are emitted (the saturation current),
    never how energetic each one is, so intensity must not appear here. A curve
    family whose stopping potential shifts with intensity is the single most
    common wrong figure in this chapter.
    """
    v = PLANCK_EV_S * freq_hz - work_function_ev
    return v if v > 0 else 0.0


def render_photoelectric_effect(data: Dict[str, Any], canvas_w: int = 800, canvas_h: int = 600) -> str:
    from diagrams.schemas.physics import PhotoelectricEffectSchema
    schema = PhotoelectricEffectSchema(**data)

    phi = schema.work_function
    f0 = schema.threshold_frequency or _threshold_frequency_hz(phi)
    gt = schema.graph_type

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))

    if gt == "apparatus":
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 7.6)
        ax.axis("off")

        # Evacuated glass tube
        ax.add_patch(mpatches.FancyBboxPatch(
            (2.0, 3.4), 5.6, 2.9, boxstyle="round,pad=0.15",
            facecolor="#EBF5FB", edgecolor="black", linewidth=2))
        ax.text(4.8, 6.55, "Evacuated tube", ha="center", fontsize=10)

        # Emitter (photosensitive plate, C) and collector (A)
        ax.add_patch(mpatches.Rectangle((2.6, 3.9), 0.22, 1.9,
                                        facecolor="#5D6D7E", edgecolor="black"))
        ax.text(1.95, 3.2, "C\n(emitter)", ha="center", va="top", fontsize=9)
        ax.add_patch(mpatches.Rectangle((6.8, 3.9), 0.22, 1.9,
                                        facecolor="#5D6D7E", edgecolor="black"))
        ax.text(7.65, 3.2, "A\n(collector)", ha="center", va="top", fontsize=9)

        # Incident light on the emitter
        for yy in (5.5, 5.1, 4.7):
            ax.annotate("", xy=(2.55, yy), xytext=(0.7, yy + 0.55),
                        arrowprops=dict(arrowstyle="-|>", color="#F39C12", lw=1.8))
        ax.text(0.6, 6.1, "Light (ν)", fontsize=11, color="#B9770E", fontweight="bold")

        # Photoelectrons crossing to the collector
        for yy in (5.4, 4.9, 4.4):
            ax.annotate("", xy=(6.6, yy), xytext=(3.1, yy),
                        arrowprops=dict(arrowstyle="-|>", color="#1B4F72", lw=1.2))
        ax.text(4.9, 4.05, "e⁻", fontsize=10, color="#1B4F72", ha="center")

        # External circuit: microammeter + variable DC supply (potentiometer)
        ax.plot([2.7, 2.7, 4.3], [3.9, 2.0, 2.0], "k-", linewidth=1.8)
        ax.plot([5.5, 6.9, 6.9], [2.0, 2.0, 3.9], "k-", linewidth=1.8)
        ax.add_patch(plt.Circle((4.9, 2.0), 0.42, facecolor="white",
                                edgecolor="black", linewidth=1.8))
        ax.text(4.9, 2.0, "µA", ha="center", va="center", fontsize=10, fontweight="bold")
        ax.plot([2.7, 2.7], [2.0, 0.9], "k-", linewidth=1.8)
        ax.plot([6.9, 6.9], [2.0, 0.9], "k-", linewidth=1.8)
        ax.plot([2.7, 6.9], [0.9, 0.9], "k-", linewidth=1.8)
        ax.add_patch(mpatches.Rectangle((4.1, 0.62), 1.6, 0.56,
                                        facecolor="white", edgecolor="black", linewidth=1.8))
        ax.annotate("", xy=(5.5, 1.28), xytext=(4.3, 0.72),
                    arrowprops=dict(arrowstyle="-|>", color="black", lw=1.4))
        ax.text(4.9, 0.25, "Variable DC voltage  (+V / −V)", ha="center",
                fontsize=9)
        ax.text(8.6, 5.0, f"φ = {phi:.2f} eV\nν₀ = {f0 / 1e14:.2f}×10¹⁴ Hz",
                ha="center", va="center", fontsize=10,
                bbox=dict(boxstyle="round,pad=0.4", facecolor="#FEF9E7"))

        title = schema.title or "Photoelectric Effect: Apparatus"

    elif gt == "current_vs_voltage":
        # Family by frequency when several are given (stopping potentials differ,
        # saturation currents match); otherwise by intensity (the reverse).
        by_frequency = len(schema.frequencies) >= 2
        f_single = schema.frequencies[0] if schema.frequencies else 1.6 * f0

        if by_frequency:
            series = [(f, 1.0, f"ν{i + 1}") for i, f in enumerate(schema.frequencies)]
        else:
            series = [(f_single, inten, f"I{i + 1}")
                      for i, inten in enumerate(schema.intensities or [1.0])]

        v_stops = [_stopping_potential_v(f, phi) for f, _, _ in series]
        v_lo = -(max(v_stops) + 1.2)
        v = np.linspace(v_lo, 5.0, 500)

        colors = ["#C0392B", "#1B4F72", "#1E8449", "#7D3C98", "#B9770E"]
        for idx, (f, inten, lbl) in enumerate(series):
            v0 = _stopping_potential_v(f, phi)
            i_sat = 2.0 * inten                # saturation current ∝ intensity ONLY
            cur = np.where(v > -v0, i_sat * (1 - np.exp(-(v + v0) / 0.35)), 0.0)
            c = colors[idx % len(colors)]
            ax.plot(v, cur, color=c, linewidth=2.0)
            ax.text(4.85, i_sat + 0.12, lbl, fontsize=10, color=c, ha="right")
            ax.axhline(i_sat, color=c, linestyle=":", linewidth=0.8)

        for v0, c in zip(sorted(set(round(x, 6) for x in v_stops)), colors):
            ax.plot([-v0], [0], "ko", markersize=5)

        if by_frequency:
            for idx, (f, _, lbl) in enumerate(series):
                v0 = _stopping_potential_v(f, phi)
                ax.axvline(-v0, color=colors[idx % len(colors)],
                           linestyle="--", linewidth=0.9)
            ax.text(v_lo * 0.5, 0.35, "Stopping potential shifts with ν",
                    fontsize=9, ha="center", color="#7B241C")
            note = "Same intensity → same saturation current"
        else:
            v0 = v_stops[0]
            ax.axvline(-v0, color="#7B241C", linestyle="--", linewidth=1.2)
            ax.text(-v0 - 0.12, 0.4, f"−V₀ = −{v0:.2f} V", fontsize=10, ha="right",
                    color="#7B241C", fontweight="bold")
            note = "V₀ is the SAME for all intensities (it depends only on ν)"

        ax.text(0.6, -0.55, note, fontsize=9, color="#7B241C")
        ax.set_xlim(v_lo - 0.3, 5.3)
        ax.set_ylim(-0.75, 2.2 * max(inten for _, inten, _ in series) + 0.9)
        ax.axhline(0, color="black", linewidth=1.0)
        ax.axvline(0, color="black", linewidth=1.0)
        ax.set_xlabel("Collector plate potential (V) →", fontsize=11)
        ax.set_ylabel("Photocurrent (µA) →", fontsize=11)
        ax.spines["left"].set_visible(False)
        ax.spines["bottom"].set_visible(False)
        title = schema.title or "Photocurrent vs Collector Potential"

    elif gt == "current_vs_intensity":
        inten = np.linspace(0, max(schema.intensities or [3.0]) * 1.2, 100)
        ax.plot(inten, 2.0 * inten, color="#1B4F72", linewidth=2.4)
        ax.set_xlim(0, inten[-1] * 1.05)
        ax.set_ylim(0, 2.0 * inten[-1] * 1.15)
        ax.set_xlabel("Intensity of incident light →", fontsize=11)
        ax.set_ylabel("Saturation photocurrent (µA) →", fontsize=11)
        ax.text(inten[-1] * 0.45, 2.0 * inten[-1] * 0.35,
                "I_sat ∝ intensity\n(ν and V held constant)",
                fontsize=10, color="#1B4F72",
                bbox=dict(boxstyle="round,pad=0.4", facecolor="#EBF5FB"))
        title = schema.title or "Saturation Current vs Intensity"

    elif gt == "max_ke_vs_frequency":
        f_max = 2.2 * f0
        f = np.linspace(f0, f_max, 200)
        ke = PLANCK_EV_S * f - phi                       # K_max = hν − φ
        ax.plot(f / 1e14, ke, color="#1B4F72", linewidth=2.4)
        f_below = np.linspace(0, f0, 60)
        ax.plot(f_below / 1e14, PLANCK_EV_S * f_below - phi, color="#1B4F72",
                linestyle="--", linewidth=1.2)
        ax.axhline(0, color="black", linewidth=1.0)
        ax.set_xlim(0, f_max / 1e14 * 1.05)
        ax.set_ylim(-phi * 1.25, (PLANCK_EV_S * f_max - phi) * 1.25)
        if schema.show_threshold:
            ax.plot([f0 / 1e14], [0], "ko", markersize=6)
            ax.text(f0 / 1e14, -phi * 0.18, f"ν₀ = {f0 / 1e14:.2f}×10¹⁴ Hz",
                    fontsize=9, ha="center", va="top")
            ax.plot([0], [-phi], "ko", markersize=6)
            ax.text(0.15, -phi, f"−φ = −{phi:.2f} eV", fontsize=9, va="center")
        if schema.show_slope_h:
            ax.text(f_max / 1e14 * 0.42, (PLANCK_EV_S * f_max - phi) * 0.75,
                    "slope = h", fontsize=11, color="#C0392B", fontweight="bold")
        ax.set_xlabel("Frequency ν (×10¹⁴ Hz) →", fontsize=11)
        ax.set_ylabel("K_max (eV) →", fontsize=11)
        title = schema.title or "Maximum Kinetic Energy vs Frequency"

    else:   # stopping_potential_vs_frequency
        f_max = 2.2 * f0
        f = np.linspace(f0, f_max, 200)
        v0 = PLANCK_EV_S * f - phi                       # eV₀ = hν − φ  ⇒  V₀ = (h/e)ν − φ/e
        ax.plot(f / 1e14, v0, color="#1B4F72", linewidth=2.4)
        f_below = np.linspace(0, f0, 60)
        ax.plot(f_below / 1e14, PLANCK_EV_S * f_below - phi, color="#1B4F72",
                linestyle="--", linewidth=1.2)
        ax.axhline(0, color="black", linewidth=1.0)
        ax.set_xlim(0, f_max / 1e14 * 1.05)
        ax.set_ylim(-phi * 1.3, (PLANCK_EV_S * f_max - phi) * 1.3)
        if schema.show_threshold:
            ax.plot([f0 / 1e14], [0], "ko", markersize=6)
            ax.text(f0 / 1e14, -phi * 0.18, f"ν₀ = {f0 / 1e14:.2f}×10¹⁴ Hz",
                    fontsize=9, ha="center", va="top")
            ax.plot([0], [-phi], "ko", markersize=6)
            ax.text(0.15, -phi, f"−φ/e = −{phi:.2f} V", fontsize=9, va="center")
        if schema.show_slope_h:
            fa, fb = 1.35 * f0, 1.75 * f0
            va, vb = PLANCK_EV_S * fa - phi, PLANCK_EV_S * fb - phi
            ax.plot([fa / 1e14, fb / 1e14, fb / 1e14, fa / 1e14],
                    [va, va, vb, va], color="#C0392B", linewidth=1.2)
            ax.text(fb / 1e14 + 0.25, (va + vb) / 2,
                    "slope = h/e\n= 4.14×10⁻¹⁵ V·s", fontsize=10, color="#C0392B",
                    va="center", fontweight="bold")
        ax.text(f_max / 1e14 * 0.05, (PLANCK_EV_S * f_max - phi) * 1.05,
                "V₀ is independent of intensity", fontsize=9, color="#7B241C")
        ax.set_xlabel("Frequency ν (×10¹⁴ Hz) →", fontsize=11)
        ax.set_ylabel("Stopping potential V₀ (volts) →", fontsize=11)
        title = schema.title or "Stopping Potential vs Frequency"

    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return _fig_to_svg_phys(fig)


# ── Nuclear Binding Energy Curve ──────────────────────────────────────────────

# Measured B/A (MeV) for representative nuclides along the valley of stability.
# The semi-empirical mass formula is NOT used here: it misses ⁴He by ~3 MeV and
# would flatten the light-nucleus structure that the fusion argument rests on.
_BE_A = np.array([
    2, 3, 4, 6, 7, 9, 10, 11, 12, 14, 16, 19, 20, 23, 24, 27, 28, 31, 32, 35,
    40, 45, 48, 51, 52, 55, 56, 58, 62, 63, 64, 70, 75, 80, 85, 90, 100, 110,
    120, 130, 140, 150, 160, 170, 180, 190, 200, 209, 220, 232, 235, 238, 240,
], dtype=float)
_BE_PER_NUCLEON = np.array([
    1.112, 2.573, 7.074, 5.332, 5.606, 6.463, 6.475, 6.928, 7.680, 7.476,
    7.976, 7.779, 8.032, 8.111, 8.261, 8.332, 8.448, 8.481, 8.493, 8.520,
    8.551, 8.619, 8.723, 8.742, 8.776, 8.765, 8.790, 8.732, 8.795, 8.752,
    8.736, 8.722, 8.701, 8.711, 8.697, 8.710, 8.605, 8.551, 8.504, 8.421,
    8.376, 8.250, 8.183, 8.107, 8.023, 7.949, 7.906, 7.848, 7.760, 7.615,
    7.591, 7.570, 7.556,
], dtype=float)


def _binding_energy_per_nucleon(mass_number):
    """B/A in MeV for a mass number (scalar or array), by interpolation."""
    return np.interp(mass_number, _BE_A, _BE_PER_NUCLEON)


def _binding_energy_peak() -> Tuple[float, float]:
    """(A, B/A) at the maximum of the curve — the iron-group peak near A ≈ 56–62.

    Everything downstream hangs off this point: nuclei lighter than it gain
    binding energy by fusing, heavier ones by fissioning. If the peak drifts, the
    figure argues for the wrong reaction.
    """
    grid = np.linspace(2.0, 240.0, 2381)
    vals = _binding_energy_per_nucleon(grid)
    idx = int(np.argmax(vals))
    return float(grid[idx]), float(vals[idx])


def render_nuclear_binding_energy(data: Dict[str, Any], canvas_w: int = 800, canvas_h: int = 600) -> str:
    from diagrams.schemas.physics import NuclearBindingEnergySchema, MarkedNucleus
    schema = NuclearBindingEnergySchema(**data)

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))

    a_grid = np.linspace(2, 240, 600)
    ax.plot(a_grid, _binding_energy_per_nucleon(a_grid), color="#1B4F72", linewidth=2.2)

    ax.set_xlim(0, 250)
    ax.set_ylim(0, 10.2)
    ax.set_xlabel("Mass number A →", fontsize=11)
    ax.set_ylabel("Binding energy per nucleon (MeV) →", fontsize=11)

    peak_a, peak_ba = _binding_energy_peak()

    if schema.show_fusion_region:
        ax.axvspan(0, 20, color="#FDEBD0", alpha=0.8)
        ax.annotate("", xy=(38, 2.0), xytext=(8, 2.0),
                    arrowprops=dict(arrowstyle="-|>", color="#B9770E", lw=2.0))
        ax.text(24, 1.35, "Fusion\n(light nuclei)", ha="center", fontsize=9,
                color="#7D6608")

    if schema.show_fission_region:
        ax.axvspan(150, 250, color="#FADBD8", alpha=0.8)
        ax.annotate("", xy=(160, 2.0), xytext=(235, 2.0),
                    arrowprops=dict(arrowstyle="-|>", color="#C0392B", lw=2.0))
        ax.text(200, 1.35, "Fission\n(heavy nuclei)", ha="center", fontsize=9,
                color="#7B241C")

    if schema.show_peak:
        ax.plot([56], [_binding_energy_per_nucleon(56)], "o", color="#C0392B",
                markersize=8, zorder=5)
        ax.annotate(f"Peak: ⁵⁶Fe ≈ {_binding_energy_per_nucleon(56):.1f} MeV",
                    xy=(56, _binding_energy_per_nucleon(56)),
                    xytext=(80, 9.6), fontsize=10, color="#C0392B", fontweight="bold",
                    arrowprops=dict(arrowstyle="->", color="#C0392B", lw=1.2))
        ax.axhline(peak_ba, color="gray", linestyle=":", linewidth=0.8)

    nuclei = schema.marked_nuclei or [
        MarkedNucleus(symbol="He", mass_number=4),
        MarkedNucleus(symbol="C", mass_number=12),
        MarkedNucleus(symbol="O", mass_number=16),
        MarkedNucleus(symbol="Fe", mass_number=56),
        MarkedNucleus(symbol="U", mass_number=235),
    ]
    for nuc in nuclei:
        ba = float(_binding_energy_per_nucleon(nuc.mass_number))
        ax.plot(nuc.mass_number, ba, "o", color="#1B4F72", markersize=6, zorder=5)
        ax.annotate(f"{nuc.symbol}-{nuc.mass_number}", (nuc.mass_number, ba),
                    textcoords="offset points", xytext=(4, -14), fontsize=9,
                    color="#154360")

    ax.set_title(schema.title or "Binding Energy per Nucleon vs Mass Number",
                 fontsize=13, fontweight="bold")
    ax.grid(True, color="#eeeeee", linestyle="--", linewidth=0.7)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return _fig_to_svg_phys(fig)


# ── Electromagnetic Wave (3D) ─────────────────────────────────────────────────

def render_em_wave(data: Dict[str, Any], canvas_w: int = 800, canvas_h: int = 600) -> str:
    from diagrams.schemas.physics import EMWaveSchema
    schema = EMWaveSchema(**data)

    from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

    fig = plt.figure(figsize=(canvas_w / 100, canvas_h / 100))
    ax = fig.add_subplot(111, projection="3d")

    n = schema.num_cycles
    lam = 1.0                                  # one wavelength = 1 unit along z
    p = np.linspace(0, n * lam, 400)           # distance travelled along z
    k = 2 * np.pi / lam
    # E along x, B along y, both ∝ sin(kz). They are IN PHASE: E and B peak and
    # vanish together. Drawing them 90° apart would make the wave's energy density
    # slosh between the two fields, which a plane wave in vacuum does not do.
    envelope = np.sin(k * p)
    e_amp, b_amp = 1.0, 0.75

    # mplot3d always draws ITS z axis vertically, so the physical propagation axis
    # is mapped onto the plot's x axis (and labelled as z). That recovers the
    # textbook orientation — propagation to the right, E vertical, B into the page.
    zeros = np.zeros_like(p)
    ax.plot(p, zeros, zeros, color="black", linewidth=1.2)

    stem_p = np.linspace(0, n * lam, int(round(n * 12)) + 1)
    stem_env = np.sin(k * stem_p)

    if schema.show_e_field:
        ax.plot(p, zeros, e_amp * envelope, color="#C0392B", linewidth=2.2)
        for pp, ee in zip(stem_p, stem_env):
            ax.plot([pp, pp], [0, 0], [0, e_amp * ee], color="#C0392B", linewidth=0.7)
        ax.text(0.25 * lam, 0, e_amp + 0.22, schema.e_label, color="#C0392B",
                fontsize=14, fontweight="bold")

    if schema.show_b_field:
        ax.plot(p, b_amp * envelope, zeros, color="#1B4F72", linewidth=2.2)
        for pp, ee in zip(stem_p, stem_env):
            ax.plot([pp, pp], [0, b_amp * ee], [0, 0], color="#1B4F72", linewidth=0.7)
        ax.text(0.25 * lam, b_amp + 0.3, 0, schema.b_label, color="#1B4F72",
                fontsize=14, fontweight="bold")

    if schema.show_propagation_arrow:
        ax.quiver(n * lam, 0, 0, 0.6, 0, 0, color="black", linewidth=2.0,
                  arrow_length_ratio=0.35)
        ax.text(n * lam + 0.7, 0, 0.15, f"{schema.propagation_axis} (c)",
                fontsize=12, fontweight="bold")

    if schema.show_wavelength and n >= 1:
        y_off = -1.15
        ax.plot([0, lam], [y_off, y_off], [0, 0], color="#1E8449", linewidth=1.6)
        for pp in (0.0, lam):
            ax.plot([pp, pp], [y_off, y_off], [-0.12, 0.12],
                    color="#1E8449", linewidth=1.6)
        ax.text(lam / 2, y_off, 0.28, "λ", color="#1E8449", fontsize=14,
                fontweight="bold")

    ax.set_xlim(0, n * lam + 0.8)
    ax.set_ylim(-1.3, 1.3)
    ax.set_zlim(-1.3, 1.3)
    ax.set_box_aspect((2.4, 1.0, 1.0))
    ax.set_xlabel(f"{schema.propagation_axis} (propagation)", fontsize=10)
    ax.set_ylabel(f"y  ({schema.b_label})", fontsize=10)
    ax.set_zlabel(f"x  ({schema.e_label})", fontsize=10)
    ax.view_init(elev=20, azim=-62)
    ax.grid(False)

    subtitle = f"E ⊥ B ⊥ {schema.propagation_axis}, E and B in phase"
    if schema.wave_type:
        subtitle = f"{schema.wave_type} — {subtitle}"
    ax.set_title(f"{schema.title or 'Electromagnetic Wave'}\n{subtitle}",
                 fontsize=12, fontweight="bold")
    fig.tight_layout()
    return _fig_to_svg_phys(fig)


# ── Total Internal Reflection ─────────────────────────────────────────────────

def _critical_angle_deg(n1: float, n2: float) -> float:
    """C = arcsin(n₂/n₁), defined only for n₁ > n₂.

    Derived, never taken from the caller: a figure whose labelled C disagrees with
    the drawn rays is worse than no figure at all.
    """
    if n1 <= n2:
        raise ValueError(f"No critical angle: n1 ({n1}) must exceed n2 ({n2}).")
    return math.degrees(math.asin(n2 / n1))


def render_total_internal_reflection(data: Dict[str, Any], canvas_w: int = 800,
                                     canvas_h: int = 600) -> str:
    from diagrams.schemas.physics import TotalInternalReflectionSchema
    schema = TotalInternalReflectionSchema(**data)

    n1, n2 = schema.n1, schema.n2
    crit = _critical_angle_deg(n1, n2)

    denser_lbl = schema.medium_labels[0] if len(schema.medium_labels) > 0 else f"Denser medium (n₁ = {n1})"
    rarer_lbl = schema.medium_labels[1] if len(schema.medium_labels) > 1 else f"Rarer medium (n₂ = {n2})"

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))
    ax.set_aspect("equal")
    ax.axis("off")

    if schema.mode == "optical_fibre":
        core_h, clad_h = 1.0, 0.55
        x_end = 16.0
        ax.set_xlim(-3.0, x_end + 1.6)
        ax.set_ylim(-3.4, 2.9)

        ax.add_patch(mpatches.Rectangle((0, -core_h), x_end, 2 * core_h,
                                        facecolor="#D6EAF8", edgecolor="black", linewidth=1.5))
        for sign in (1, -1):
            ax.add_patch(mpatches.Rectangle((0, sign * core_h), x_end, sign * clad_h,
                                            facecolor="#AEB6BF", edgecolor="black",
                                            linewidth=1.5))
        ax.text(4.5, -0.62, f"Core  (n₁ = {n1})", ha="center", fontsize=10)
        ax.text(x_end / 2, core_h + clad_h / 2, f"Cladding  (n₂ = {n2})",
                ha="center", va="center", fontsize=9)

        # Propagation angle to the fibre axis. The angle at the core-cladding wall
        # is its complement, so keeping phi below (90 − C) guarantees the wall
        # incidence exceeds C and the ray is trapped. Derived, so it holds for any
        # (n1, n2) the caller passes.
        phi = 0.45 * (90.0 - crit)
        wall_incidence = 90.0 - phi
        slope = math.tan(math.radians(phi))

        # Zig-zag by repeated TIR, starting at the axis on the entry face
        pts = [(0.0, 0.0)]
        x, y, direction = 0.0, 0.0, 1.0
        while x < x_end:
            dx = (core_h * direction - y) / (slope * direction)
            x_next = x + dx
            if x_next >= x_end:
                pts.append((x_end, y + slope * direction * (x_end - x)))
                break
            y = core_h * direction
            x = x_next
            pts.append((x, y))
            direction *= -1
        xs, ys = zip(*pts)
        ax.plot(xs, ys, color="#C0392B", linewidth=2.0, zorder=4)
        for px, py in pts[1:-1]:
            ax.plot([px, px], [py, py + 0.5 * (1 if py > 0 else -1)],
                    color="gray", linestyle="--", linewidth=1.0)

        # Entry ray from outside the fibre
        ax.annotate("", xy=(0, 0), xytext=(-2.6, -1.5),
                    arrowprops=dict(arrowstyle="-|>", color="#C0392B", lw=2.0))
        ax.text(-2.8, -1.8, "Incident\nray", fontsize=9, ha="left", va="top")

        bx, by = pts[1]
        ax.annotate(f"i = {wall_incidence:.1f}°  >  C = {crit:.1f}°",
                    xy=(bx, by), xytext=(bx + 0.4, by + 1.15), fontsize=10,
                    color="#7B241C", fontweight="bold",
                    arrowprops=dict(arrowstyle="->", color="#7B241C", lw=1.0))
        ax.text(x_end / 2, -2.7,
                f"Every bounce meets the wall at {wall_incidence:.1f}° > C, "
                f"so the ray is totally internally reflected and stays in the core.",
                ha="center", fontsize=9, color="#1B4F72")
        title = schema.title or "Optical Fibre: Guiding by Total Internal Reflection"

    else:   # rays
        ax.set_xlim(-5.6, 6.4)
        ax.set_ylim(-4.4, 4.2)

        ax.add_patch(mpatches.Rectangle((-5.6, 0), 12.0, 4.2,
                                        facecolor="#EBF5FB", edgecolor="none"))
        ax.add_patch(mpatches.Rectangle((-5.6, -4.4), 12.0, 4.4,
                                        facecolor="#AED6F1", edgecolor="none"))
        ax.axhline(0, color="black", linewidth=2.0)
        ax.text(-5.4, 0.2, rarer_lbl, fontsize=10, va="bottom")
        ax.text(-5.4, -0.2, denser_lbl, fontsize=10, va="top")

        ax.plot([0, 0], [-3.9, 3.9], color="gray", linestyle="--", linewidth=1.2)
        ax.text(0.12, 3.7, "Normal", fontsize=9, color="gray")

        angles = schema.incident_angles or [
            max(5.0, crit - 15.0), crit, min(85.0, crit + 15.0)]
        colors = ["#1E8449", "#B9770E", "#C0392B", "#7D3C98", "#117864"]
        L = 3.6

        for idx, theta_deg in enumerate(angles):
            c = colors[idx % len(colors)]
            th = math.radians(theta_deg)
            # Incident ray arrives from below-left, striking O at theta to the normal
            ax.annotate("", xy=(0, 0), xytext=(-L * math.sin(th), -L * math.cos(th)),
                        arrowprops=dict(arrowstyle="-|>", color=c, lw=1.8))

            if theta_deg < crit - 0.5:
                # Snell: n₁ sin θ = n₂ sin r — refracted ray bends AWAY from the normal
                r = math.asin(min(1.0, n1 * math.sin(th) / n2))
                ax.annotate("", xy=(L * math.sin(r), L * math.cos(r)), xytext=(0, 0),
                            arrowprops=dict(arrowstyle="-|>", color=c, lw=1.8))
                ax.text(L * math.sin(r) + 0.15, L * math.cos(r),
                        f"θ = {theta_deg:.1f}° < C\nrefracted (r = {math.degrees(r):.1f}°)",
                        fontsize=9, color=c, va="center")
                # Partial reflection back into the denser medium
                ax.plot([0, L * 0.5 * math.sin(th)], [0, -L * 0.5 * math.cos(th)],
                        color=c, linestyle=":", linewidth=1.0)
            elif abs(theta_deg - crit) <= 0.5:
                ax.annotate("", xy=(L, 0.0), xytext=(0, 0),
                            arrowprops=dict(arrowstyle="-|>", color=c, lw=1.8))
                ax.text(L + 0.2, 0.45,
                        f"θ = C = {crit:.1f}°\ngrazes the surface (r = 90°)",
                        fontsize=9, color=c, va="bottom")
            else:
                ax.annotate("", xy=(L * math.sin(th), -L * math.cos(th)), xytext=(0, 0),
                            arrowprops=dict(arrowstyle="-|>", color=c, lw=2.2))
                ax.text(L * math.sin(th) + 0.15, -L * math.cos(th),
                        f"θ = {theta_deg:.1f}° > C\ntotal internal reflection",
                        fontsize=9, color=c, va="center")

        ax.plot(0, 0, "ko", markersize=6, zorder=6)
        ax.text(-0.15, -0.3, "O", fontsize=10, ha="right", va="top")

        if schema.show_critical_angle:
            ax.text(-5.4, -4.2,
                    f"C = arcsin(n₂/n₁) = arcsin({n2:.2f}/{n1:.2f}) = {crit:.1f}°",
                    fontsize=11, color="#7B241C", fontweight="bold", va="bottom",
                    bbox=dict(boxstyle="round,pad=0.4", facecolor="#FEF9E7"))

        title = schema.title or "Total Internal Reflection"

    ax.set_title(title, fontsize=13, fontweight="bold")
    fig.tight_layout()
    return _fig_to_svg_phys(fig)


# ── Moment of Inertia ─────────────────────────────────────────────────────────

# I = M·(c_R·R² + c_L·L² + c_b·b²) for each (body, axis). Held as coefficients so
# the printed formula and any downstream numeric check come from one source, and
# so the parallel-axis relations (tangent = diameter + MR²) stay verifiable.
_MOI_TABLE: Dict[Tuple[str, str], Tuple[str, Dict[str, float]]] = {
    ("rod", "centre"): ("I = {M}{L}²/12", {"L2": 1 / 12}),
    ("rod", "perpendicular_bisector"): ("I = {M}{L}²/12", {"L2": 1 / 12}),
    ("rod", "end"): ("I = {M}{L}²/3", {"L2": 1 / 3}),

    ("ring", "centre"): ("I = {M}{R}²", {"R2": 1.0}),
    ("ring", "diameter"): ("I = {M}{R}²/2", {"R2": 1 / 2}),
    ("ring", "tangent"): ("I = 3{M}{R}²/2", {"R2": 3 / 2}),

    ("disc", "centre"): ("I = {M}{R}²/2", {"R2": 1 / 2}),
    ("disc", "diameter"): ("I = {M}{R}²/4", {"R2": 1 / 4}),
    ("disc", "tangent"): ("I = 5{M}{R}²/4", {"R2": 5 / 4}),

    ("solid_sphere", "centre"): ("I = 2{M}{R}²/5", {"R2": 2 / 5}),
    ("solid_sphere", "diameter"): ("I = 2{M}{R}²/5", {"R2": 2 / 5}),
    ("solid_sphere", "tangent"): ("I = 7{M}{R}²/5", {"R2": 7 / 5}),

    ("hollow_sphere", "centre"): ("I = 2{M}{R}²/3", {"R2": 2 / 3}),
    ("hollow_sphere", "diameter"): ("I = 2{M}{R}²/3", {"R2": 2 / 3}),
    ("hollow_sphere", "tangent"): ("I = 5{M}{R}²/3", {"R2": 5 / 3}),

    ("solid_cylinder", "centre"): ("I = {M}{R}²/2", {"R2": 1 / 2}),
    ("solid_cylinder", "diameter"): ("I = {M}({R}²/4 + {L}²/12)", {"R2": 1 / 4, "L2": 1 / 12}),
    ("solid_cylinder", "end"): ("I = {M}({R}²/4 + {L}²/3)", {"R2": 1 / 4, "L2": 1 / 3}),

    ("hollow_cylinder", "centre"): ("I = {M}{R}²", {"R2": 1.0}),
    ("hollow_cylinder", "diameter"): ("I = {M}({R}²/2 + {L}²/12)", {"R2": 1 / 2, "L2": 1 / 12}),
    ("hollow_cylinder", "end"): ("I = {M}({R}²/2 + {L}²/3)", {"R2": 1 / 2, "L2": 1 / 3}),

    ("rectangular_plate", "centre"): ("I = {M}({L}² + {b}²)/12", {"L2": 1 / 12, "b2": 1 / 12}),
    ("rectangular_plate", "perpendicular_bisector"): ("I = {M}{L}²/12", {"L2": 1 / 12}),
    ("rectangular_plate", "end"): ("I = {M}{L}²/3", {"L2": 1 / 3}),
}

_MOI_AXIS_CAPTION = {
    ("rod", "centre"): "Axis ⊥ to the rod, through its centre",
    ("rod", "perpendicular_bisector"): "Axis ⊥ to the rod, through its centre",
    ("rod", "end"): "Axis ⊥ to the rod, through one end",
    ("ring", "centre"): "Axis ⊥ to the plane, through the centre",
    ("ring", "diameter"): "Axis along a diameter",
    ("ring", "tangent"): "Tangent, in the plane of the ring",
    ("disc", "centre"): "Axis ⊥ to the plane, through the centre",
    ("disc", "diameter"): "Axis along a diameter",
    ("disc", "tangent"): "Tangent, in the plane of the disc",
    ("solid_sphere", "centre"): "Axis through the centre (a diameter)",
    ("solid_sphere", "diameter"): "Axis through the centre (a diameter)",
    ("solid_sphere", "tangent"): "Tangent to the surface",
    ("hollow_sphere", "centre"): "Axis through the centre (a diameter)",
    ("hollow_sphere", "diameter"): "Axis through the centre (a diameter)",
    ("hollow_sphere", "tangent"): "Tangent to the surface",
    ("solid_cylinder", "centre"): "Axis of symmetry, through the centre",
    ("solid_cylinder", "diameter"): "Transverse axis through the centre",
    ("solid_cylinder", "end"): "Transverse axis at one end",
    ("hollow_cylinder", "centre"): "Axis of symmetry, through the centre",
    ("hollow_cylinder", "diameter"): "Transverse axis through the centre",
    ("hollow_cylinder", "end"): "Transverse axis at one end",
    ("rectangular_plate", "centre"): "Axis ⊥ to the plate, through the centre",
    ("rectangular_plate", "perpendicular_bisector"): "In-plane axis through the centre",
    ("rectangular_plate", "end"): "In-plane axis along one edge",
}


def _moi_terms(body: str, axis: str) -> Dict[str, float]:
    """Coefficients of I = M(c_R R² + c_L L² + c_b b²) for a (body, axis) pair."""
    return dict(_MOI_TABLE[(body, axis)][1])


def _moi_formula(body: str, axis: str, mass: str = "M", radius: str = "R",
                 length: str = "L", breadth: str = "b") -> str:
    return _MOI_TABLE[(body, axis)][0].format(M=mass, R=radius, L=length, b=breadth)


def _moi_dashdot(ax, x1: float, y1: float, x2: float, y2: float):
    ax.plot([x1, x2], [y1, y2], color="#C0392B", linestyle="-.", linewidth=2.0, zorder=6)


def render_moment_of_inertia(data: Dict[str, Any], canvas_w: int = 800, canvas_h: int = 600) -> str:
    from diagrams.schemas.physics import MomentOfInertiaSchema
    schema = MomentOfInertiaSchema(**data)

    body, axis = schema.body, schema.axis
    M, R, L, b = schema.mass_label, schema.radius_label, schema.length_label, schema.breadth_label

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))
    ax.set_aspect("equal")
    ax.set_xlim(-4.0, 4.0)
    ax.set_ylim(-3.2, 3.0)
    ax.axis("off")

    body_fill = "#D6EAF8"
    edge = "black"

    if body == "rod":
        ax.plot([-2.2, 2.2], [0, 0], color=edge, linewidth=9, solid_capstyle="butt",
                zorder=3)
        ax.annotate("", xy=(2.2, -0.75), xytext=(-2.2, -0.75),
                    arrowprops=dict(arrowstyle="<->", color="black", lw=1.2))
        ax.text(0, -1.05, L, ha="center", va="top", fontsize=12)
        ax.text(0, 0.45, M, ha="center", fontsize=12, fontweight="bold")
        if schema.show_axis:
            ax_x = 0.0 if axis in ("centre", "perpendicular_bisector") else -2.2
            _moi_dashdot(ax, ax_x, -1.9, ax_x, 2.4)

    elif body in ("ring", "disc"):
        filled = body == "disc"
        if axis == "centre":
            # Perspective view: the ⊥ axis reads as a vertical line through the centre
            ell = mpatches.Ellipse((0, 0), 4.4, 1.7, facecolor=body_fill if filled else "none",
                                   edgecolor=edge, linewidth=2.4, zorder=3)
            ax.add_patch(ell)
            ax.annotate("", xy=(2.2, 0), xytext=(0, 0),
                        arrowprops=dict(arrowstyle="-|>", color="black", lw=1.2))
            ax.text(1.1, 0.22, R, fontsize=12, ha="center")
            if schema.show_axis:
                _moi_dashdot(ax, 0, -2.35, 0, 2.6)
        else:
            circ = plt.Circle((0, 0), 1.9, facecolor=body_fill if filled else "none",
                              edgecolor=edge, linewidth=2.4, zorder=3)
            ax.add_patch(circ)
            ax.annotate("", xy=(1.9 * 0.7, 1.9 * 0.7), xytext=(0, 0),
                        arrowprops=dict(arrowstyle="-|>", color="black", lw=1.2))
            ax.text(0.75, 0.95, R, fontsize=12)
            if schema.show_axis:
                if axis == "diameter":
                    _moi_dashdot(ax, -2.8, 0, 2.8, 0)
                else:   # tangent, in the plane, touching the rim
                    _moi_dashdot(ax, 1.9, -2.35, 1.9, 2.6)
                    ax.annotate("", xy=(1.9, -1.15), xytext=(0, -1.15),
                                arrowprops=dict(arrowstyle="<->", color="#7B241C", lw=1.0))
                    ax.text(0.95, -1.42, R, fontsize=10, ha="center", va="top",
                            color="#7B241C")
        # The ⊥-axis case draws a vertical line through x = 0, so M cannot sit there
        if axis == "centre":
            ax.text(-1.7, 1.25, M, ha="center", fontsize=12, fontweight="bold")
        else:
            ax.text(0, 2.25, M, ha="center", fontsize=12, fontweight="bold")

    elif body in ("solid_sphere", "hollow_sphere"):
        solid = body == "solid_sphere"
        ax.add_patch(plt.Circle((0, 0), 1.9, facecolor=body_fill if solid else "white",
                                edgecolor=edge, linewidth=2.4 if solid else 3.2, zorder=3))
        if not solid:
            ax.add_patch(plt.Circle((0, 0), 1.72, facecolor="white", edgecolor=edge,
                                    linewidth=1.0, linestyle="--", zorder=4))
            ax.text(-3.9, 2.75, "thin shell", ha="left", va="top", fontsize=9,
                    color="#5D6D7E")
        ax.add_patch(mpatches.Ellipse((0, 0), 3.8, 1.2, facecolor="none",
                                      edgecolor="#5D6D7E", linewidth=1.0,
                                      linestyle="--", zorder=5))
        ax.annotate("", xy=(1.9 * 0.72, -1.9 * 0.69), xytext=(0, 0),
                    arrowprops=dict(arrowstyle="-|>", color="black", lw=1.2))
        ax.text(0.9, -0.95, R, fontsize=12)
        ax.text(-1.1, 1.35, M, fontsize=12, fontweight="bold")
        if schema.show_axis:
            if axis == "tangent":
                _moi_dashdot(ax, 1.9, -2.35, 1.9, 2.7)
                ax.annotate("", xy=(1.9, 2.25), xytext=(0, 2.25),
                            arrowprops=dict(arrowstyle="<->", color="#7B241C", lw=1.0))
                ax.text(0.95, 2.45, R, fontsize=10, ha="center", color="#7B241C")
            else:
                _moi_dashdot(ax, 0, -2.35, 0, 2.7)

    elif body in ("solid_cylinder", "hollow_cylinder"):
        solid = body == "solid_cylinder"
        cyl_r, cyl_hl = 1.25, 1.8      # radius, half-length (upright: length is vertical)
        ax.add_patch(mpatches.Rectangle((-cyl_r, -cyl_hl), 2 * cyl_r, 2 * cyl_hl,
                                        facecolor=body_fill if solid else "white",
                                        edgecolor=edge, linewidth=2.0, zorder=3))
        ax.add_patch(mpatches.Ellipse((0, cyl_hl), 2 * cyl_r, 0.75,
                                      facecolor="#AED6F1" if solid else "white",
                                      edgecolor=edge, linewidth=2.0, zorder=4))
        ax.add_patch(mpatches.Ellipse((0, -cyl_hl), 2 * cyl_r, 0.75, facecolor="none",
                                      edgecolor=edge, linewidth=1.0, linestyle="--",
                                      zorder=2))
        if not solid:
            ax.add_patch(mpatches.Ellipse((0, cyl_hl), 2 * cyl_r * 0.72, 0.75 * 0.72,
                                          facecolor="white", edgecolor=edge,
                                          linewidth=1.4, zorder=5))
            ax.text(-3.9, 2.75, "thin-walled", ha="left", va="top", fontsize=9,
                    color="#5D6D7E")
        # Radius on the bottom face: the 'end' axis runs along the top one
        ax.annotate("", xy=(cyl_r, -cyl_hl), xytext=(0, -cyl_hl),
                    arrowprops=dict(arrowstyle="-|>", color="black", lw=1.2))
        ax.text(cyl_r * 0.55, -cyl_hl + 0.16, R, fontsize=11, ha="center")
        ax.annotate("", xy=(-1.85, cyl_hl), xytext=(-1.85, -cyl_hl),
                    arrowprops=dict(arrowstyle="<->", color="black", lw=1.2))
        ax.text(-2.05, 0, L, fontsize=12, ha="right", va="center")
        ax.text(1.75, 0, M, fontsize=12, fontweight="bold", va="center")
        if schema.show_axis:
            if axis == "centre":
                _moi_dashdot(ax, 0, -2.35, 0, 2.9)
            elif axis == "diameter":
                _moi_dashdot(ax, -3.4, 0, 3.4, 0)
            else:   # end
                _moi_dashdot(ax, -3.4, cyl_hl, 3.4, cyl_hl)

    else:   # rectangular_plate
        if axis == "centre":
            # Perspective view so that the ⊥ axis is visible as a vertical line
            verts = [(-2.4, -0.9), (1.2, -1.7), (2.4, 0.9), (-1.2, 1.7)]
            ax.add_patch(mpatches.Polygon(verts, closed=True, facecolor=body_fill,
                                          edgecolor=edge, linewidth=2.0, zorder=3))
            ax.text(1.9, -1.35, L, fontsize=12)
            ax.text(-2.25, 1.35, b, fontsize=12)
            if schema.show_axis:
                _moi_dashdot(ax, 0, -2.35, 0, 2.6)
        else:
            ax.add_patch(mpatches.Rectangle((-2.2, -1.3), 4.4, 2.6, facecolor=body_fill,
                                            edgecolor=edge, linewidth=2.0, zorder=3))
            ax.annotate("", xy=(2.2, -1.7), xytext=(-2.2, -1.7),
                        arrowprops=dict(arrowstyle="<->", color="black", lw=1.2))
            ax.text(0, -1.95, L, ha="center", va="top", fontsize=12)
            ax.annotate("", xy=(2.6, 1.3), xytext=(2.6, -1.3),
                        arrowprops=dict(arrowstyle="<->", color="black", lw=1.2))
            ax.text(2.8, 0, b, fontsize=12, va="center")
            if schema.show_axis:
                ax_x = 0.0 if axis == "perpendicular_bisector" else -2.2
                _moi_dashdot(ax, ax_x, -2.35, ax_x, 2.4)
        # Both plate axes are vertical lines, so M is kept off x = 0 and off the edge
        ax.text(1.15, 0.55, M, ha="center", fontsize=12, fontweight="bold")

    if schema.show_axis:
        ax.text(3.9, 2.75, "−·− axis of rotation", fontsize=9, color="#C0392B",
                ha="right", va="top")

    ax.text(0, -2.55, _MOI_AXIS_CAPTION[(body, axis)], ha="center", va="top",
            fontsize=10, color="#1B4F72")

    if schema.show_formula:
        ax.text(0, -3.05, _moi_formula(body, axis, M, R, L, b), ha="center", va="bottom",
                fontsize=15, fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.45", facecolor="#FEF9E7",
                          edgecolor="#B9770E"))

    _body_name = body.replace("_", " ").title()
    ax.set_title(schema.title or f"Moment of Inertia: {_body_name}",
                 fontsize=13, fontweight="bold")
    fig.tight_layout()
    return _fig_to_svg_phys(fig)


# ══════════════════════════════════════════════════════════════════════════════
# Fluids · Kinematics · SHM · Waves · Elasticity
# ══════════════════════════════════════════════════════════════════════════════

# ── Fluid Mechanics ───────────────────────────────────────────────────────────

def _venturi_state(area_wide: float, area_narrow: float, velocity_wide: float,
                   fluid_density: float, gravity: float) -> Tuple[float, float, float]:
    """(v₂, p₁ − p₂, Δh) for a venturimeter, from continuity then Bernoulli.

    A₁v₁ = A₂v₂ fixes v₂, and Bernoulli then fixes p₁ − p₂ = ½ρ(v₂² − v₁²), which
    is POSITIVE for A₂ < A₁. The throat is the fast, low-pressure point, so its
    tapping must stand lower — the whole figure hangs on that sign.
    """
    v2 = area_wide * velocity_wide / area_narrow
    dp = 0.5 * fluid_density * (v2 ** 2 - velocity_wide ** 2)
    dh = dp / (fluid_density * gravity)
    return v2, dp, dh


def _capillary_rise_h(surface_tension: float, contact_angle_deg: float,
                      tube_radius: float, fluid_density: float, gravity: float) -> float:
    """h = 2T·cosθ / (rρg).

    For θ > 90° (mercury on glass) cosθ < 0 and h is NEGATIVE: the liquid is
    depressed, not raised. The sign is carried through rather than clamped.
    """
    return (2.0 * surface_tension * math.cos(math.radians(contact_angle_deg))
            / (tube_radius * fluid_density * gravity))


def _hydraulic_output_force(input_force: float, area_small: float,
                            area_large: float) -> float:
    """F₂ = F₁·A₂/A₁ — Pascal's law, pressure equal on both pistons."""
    return input_force * area_large / area_small


def _submerged_fraction(body_density: float, fluid_density: float) -> float:
    """V_submerged / V_body = ρ_body / ρ_fluid, from ρ_b V g = ρ_f V_sub g."""
    return body_density / fluid_density


def _manometer_height(gauge_pressure: float, manometer_fluid_density: float,
                      gravity: float) -> float:
    """h = p_gauge / (ρ_m g); negative for a suction (below-atmospheric) pressure."""
    return gauge_pressure / (manometer_fluid_density * gravity)


def render_fluid_mechanics(data: Dict[str, Any], canvas_w: int = 800,
                           canvas_h: int = 600) -> str:
    from diagrams.schemas.physics import FluidMechanicsSchema
    schema = FluidMechanicsSchema(**data)

    setup = schema.setup
    rho, g = schema.fluid_density, schema.gravity

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))
    ax.set_aspect("equal")
    ax.axis("off")

    notes: List[str] = []

    if setup in ("venturimeter", "streamline_flow"):
        v2, dp, dh = _venturi_state(schema.area_wide, schema.area_narrow,
                                    schema.velocity_wide, rho, g)
        a1, a2, v1 = schema.area_wide, schema.area_narrow, schema.velocity_wide

        ax.set_xlim(-1.6, 13.0)
        # Only the venturimeter carries pressure tappings above the pipe; without them
        # the extra headroom is just white space.
        ax.set_ylim(-3.2, 7.4 if setup == "venturimeter" else 2.8)

        # Pipe profile: half-height scales with area, so the drawn constriction IS A₂/A₁
        h1 = 1.30
        h2 = h1 * (a2 / a1)
        xs_top = [0.0, 3.4, 5.0, 7.0, 8.6, 12.0]
        ys_top = [h1, h1, h2, h2, h1, h1]
        ys_bot = [-y for y in ys_top]
        ax.plot(xs_top, ys_top, color="black", linewidth=2.2)
        ax.plot(xs_top, ys_bot, color="black", linewidth=2.2)
        ax.fill_between(xs_top, ys_bot, ys_top, color="#D6EAF8", zorder=0)

        # Streamlines crowd where the pipe narrows — same volume, less room
        for frac in (0.28, 0.58, 0.86):
            ys = [frac * y for y in ys_top]
            ax.plot(xs_top, ys, color="#2E86C1", linewidth=1.0, linestyle="-")
            ax.plot(xs_top, [-y for y in ys], color="#2E86C1", linewidth=1.0)
        ax.plot(xs_top, [0.0] * len(xs_top), color="#2E86C1", linewidth=1.0)

        ax.annotate("", xy=(2.7, 0.0), xytext=(1.1, 0.0),
                    arrowprops=dict(arrowstyle="-|>", color="#C0392B", lw=2.0))
        ax.text(1.9, 0.22, f"v₁ = {v1:.2f} m/s", ha="center", fontsize=10,
                color="#C0392B")
        ax.annotate("", xy=(6.7, 0.0), xytext=(5.3, 0.0),
                    arrowprops=dict(arrowstyle="-|>", color="#C0392B", lw=2.6))
        ax.text(6.0, h2 + 0.25, f"v₂ = {v2:.2f} m/s", ha="center", fontsize=10,
                color="#C0392B", fontweight="bold")

        ax.annotate("", xy=(0.7, -h1), xytext=(0.7, h1),
                    arrowprops=dict(arrowstyle="<->", color="black", lw=1.0))
        ax.text(0.55, 0.0, f"A₁ = {a1:.1e} m²", fontsize=9, va="center", ha="right")
        ax.text(6.0, -h2 - 0.55, f"A₂ = {a2:.1e} m²", fontsize=9, ha="center")

        if setup == "venturimeter":
            # Vertical tappings. Column heights differ by Δh = (p₁ − p₂)/ρg, drawn
            # to a common scale so the throat column is visibly the shorter one.
            base = h1 + 0.2
            scale = min(3.6 / max(dh, 1e-9), 3.6)
            col1 = 3.4
            col2 = max(0.5, col1 - dh * scale)
            for x, col, lbl in ((2.0, col1, "p₁"), (6.0, col2, "p₂")):
                ax.add_patch(mpatches.Rectangle((x - 0.16, base), 0.32, 4.0,
                                                facecolor="white", edgecolor="black",
                                                linewidth=1.6, zorder=2))
                ax.add_patch(mpatches.Rectangle((x - 0.16, base), 0.32, col,
                                                facecolor="#5DADE2", edgecolor="none",
                                                zorder=3))
                ax.text(x - 0.35, base + col, lbl, fontsize=10, ha="right",
                        va="center", fontweight="bold")
            ax.plot([2.0, 6.0], [base + col1, base + col1], color="gray",
                    linestyle="--", linewidth=0.9)
            ax.plot([6.0, 7.4], [base + col2, base + col2], color="gray",
                    linestyle="--", linewidth=0.9)
            ax.annotate("", xy=(7.1, base + col1), xytext=(7.1, base + col2),
                        arrowprops=dict(arrowstyle="<->", color="#7B241C", lw=1.6))
            ax.text(7.3, base + (col1 + col2) / 2, f"h = {dh:.3f} m",
                    fontsize=11, color="#7B241C", fontweight="bold", va="center")
            notes = [
                f"Continuity:  A₁v₁ = A₂v₂,  so  v₂ = {a1:.1e}×{v1:.2f}/{a2:.1e} = {v2:.2f} m/s",
                f"Bernoulli:  p₁ − p₂ = ½ρ(v₂² − v₁²) = {dp:.1f} Pa",
                f"Manometer:  h = (p₁ − p₂)/ρg = {dh:.3f} m   (throat pressure is LOWER)",
            ]
            title = schema.title or "Venturimeter"
        else:
            notes = [
                f"Steady streamline flow:  A₁v₁ = A₂v₂  (volume flux is conserved)",
                f"v₂ = A₁v₁/A₂ = {v2:.2f} m/s — the fluid speeds up through the throat",
                f"Bernoulli:  p + ½ρv² + ρgh = constant,  so  p₂ < p₁ wherever v₂ > v₁",
            ]
            title = schema.title or "Streamline Flow through a Constriction"

    elif setup == "manometer":
        h = _manometer_height(schema.gauge_pressure, schema.manometer_fluid_density, g)
        ax.set_xlim(-2.6, 10.0)
        ax.set_ylim(-1.4, 8.6)

        # U-tube: the OPEN limb stands higher by h when the vessel is above
        # atmospheric pressure; the sign of h flips the whole picture, so it is
        # applied rather than assumed.
        xl, xr, wall = 3.2, 6.2, 0.42
        y_bot, y_top = 0.4, 6.6
        for x in (xl, xr):
            ax.add_patch(mpatches.Rectangle((x - wall / 2, y_bot), wall, y_top - y_bot,
                                            facecolor="white", edgecolor="black",
                                            linewidth=1.8, zorder=2))
        ax.add_patch(mpatches.Rectangle((xl - wall / 2, y_bot - 0.42),
                                        (xr - xl) + wall, 0.42,
                                        facecolor="white", edgecolor="black",
                                        linewidth=1.8, zorder=2))

        # The limb levels differ by h. Real h ranges over orders of magnitude (mm of
        # mercury to metres of water), so the DIFFERENCE is drawn at a fixed readable
        # size and its true value is printed; only its SIGN carries physical meaning
        # here (which limb stands higher).
        drawn = 2.2 * (1.0 if h >= 0 else -1.0)
        lvl_l = 2.6 - drawn / 2.0
        lvl_r = 2.6 + drawn / 2.0
        for x, lvl in ((xl, lvl_l), (xr, lvl_r)):
            ax.add_patch(mpatches.Rectangle((x - wall / 2 + 0.03, y_bot), wall - 0.06,
                                            lvl - y_bot, facecolor="#95A5A6",
                                            edgecolor="none", zorder=3))
        ax.add_patch(mpatches.Rectangle((xl - wall / 2 + 0.03, y_bot - 0.36),
                                        (xr - xl) + wall - 0.06, 0.36,
                                        facecolor="#95A5A6", edgecolor="none", zorder=3))

        ax.plot([xl, xr + 1.2], [lvl_l, lvl_l], color="gray", linestyle="--",
                linewidth=0.9, zorder=4)
        ax.plot([xr, xr + 1.2], [lvl_r, lvl_r], color="gray", linestyle="--",
                linewidth=0.9, zorder=4)
        ax.annotate("", xy=(xr + 1.0, lvl_r), xytext=(xr + 1.0, lvl_l),
                    arrowprops=dict(arrowstyle="<->", color="#7B241C", lw=1.6))
        ax.text(xr + 1.15, (lvl_l + lvl_r) / 2, f"h = {abs(h):.3f} m",
                fontsize=11, color="#7B241C", fontweight="bold", va="center")

        # Gas vessel, piped into the TOP of the left limb (that limb is not open to
        # the atmosphere — the right one is).
        ax.add_patch(mpatches.Rectangle((-2.2, 3.9), 3.4, 2.8, facecolor="#FCF3CF",
                                        edgecolor="black", linewidth=1.8))
        ax.text(-0.5, 5.3, "Gas\np", ha="center", va="center", fontsize=12,
                fontweight="bold")
        ax.add_patch(mpatches.Rectangle((1.2, y_top - 0.05), xl - 1.2 + wall / 2, 0.42,
                                        facecolor="white", edgecolor="black",
                                        linewidth=1.8, zorder=4))
        ax.plot([xl - wall / 2 + 0.02, xl + wall / 2 - 0.02], [y_top, y_top],
                color="white", linewidth=2.6, zorder=5)
        ax.annotate("", xy=(xr, y_top + 1.1), xytext=(xr, y_top + 0.15),
                    arrowprops=dict(arrowstyle="-|>", color="#1B4F72", lw=1.6))
        ax.text(xr + 0.15, y_top + 1.15, "open to atmosphere (p₀)", fontsize=9,
                color="#1B4F72", va="bottom")
        ax.text(xl, y_bot - 1.15,
                f"manometric fluid  ρ_m = {schema.manometer_fluid_density:.0f} kg/m³",
                fontsize=9, ha="center")

        sense = "above" if schema.gauge_pressure >= 0 else "below"
        notes = [
            f"p − p₀ = ρ_m·g·h,  so  h = {schema.gauge_pressure:.0f}/"
            f"({schema.manometer_fluid_density:.0f}×{g:.1f}) = {abs(h):.3f} m",
            f"Gauge pressure = {schema.gauge_pressure:.0f} Pa ({sense} atmospheric), "
            f"so the open limb stands {'higher' if h >= 0 else 'lower'}.",
        ]
        title = schema.title or "U-tube Manometer"

    elif setup == "capillary_rise":
        h = _capillary_rise_h(schema.surface_tension, schema.contact_angle,
                              schema.tube_radius, rho, g)
        theta = schema.contact_angle
        ax.set_xlim(-1.0, 11.0)
        ax.set_ylim(-1.6, 9.2)

        # Beaker
        ax.add_patch(mpatches.Rectangle((0.4, 0.0), 8.6, 3.2, facecolor="white",
                                        edgecolor="black", linewidth=2.0))
        ax.add_patch(mpatches.Rectangle((0.45, 0.05), 8.5, 2.15, facecolor="#AED6F1",
                                        edgecolor="none"))
        ax.plot([0.4, 9.0], [2.2, 2.2], color="#1B4F72", linewidth=1.4)

        tube_x, tube_hw = 4.6, 0.34
        ax.plot([tube_x - tube_hw, tube_x - tube_hw], [1.0, 8.4], color="black",
                linewidth=2.0, zorder=4)
        ax.plot([tube_x + tube_hw, tube_x + tube_hw], [1.0, 8.4], color="black",
                linewidth=2.0, zorder=4)

        # A rise of several cm and a mercury depression of ~1 cm cannot share one
        # linear scale and both stay legible, so the drawn offset is fixed and the
        # true h is printed. Its SIGN is the physics: cosθ < 0 pushes the column DOWN.
        drawn = 2.9 if h >= 0 else -0.95
        col_top = 2.2 + drawn
        ax.add_patch(mpatches.Rectangle((tube_x - tube_hw + 0.04, 1.0),
                                        2 * tube_hw - 0.08, max(0.0, col_top - 1.0),
                                        facecolor="#5DADE2", edgecolor="none", zorder=3))

        # Meniscus curvature follows θ: concave (wetting, θ < 90°) lifts the column,
        # convex (non-wetting, θ > 90°) pushes it down.
        mx = np.linspace(tube_x - tube_hw + 0.04, tube_x + tube_hw - 0.04, 40)
        bulge = 0.22 if theta < 90 else -0.22
        my = col_top - bulge * (1 - ((mx - tube_x) / tube_hw) ** 2)
        ax.plot(mx, my, color="#1B4F72", linewidth=1.8, zorder=5)

        ax.plot([tube_x + tube_hw, 9.6], [col_top, col_top], color="gray",
                linestyle="--", linewidth=0.9, zorder=6)
        ax.plot([9.0, 9.6], [2.2, 2.2], color="gray", linestyle="--", linewidth=0.9,
                zorder=6)
        ax.annotate("", xy=(9.4, col_top), xytext=(9.4, 2.2),
                    arrowprops=dict(arrowstyle="<->", color="#7B241C", lw=1.6),
                    zorder=6)
        word = "rise" if h >= 0 else "depression"
        ax.text(9.7, (col_top + 2.2) / 2, f"h = {abs(h) * 100:.2f} cm\n({word})",
                fontsize=10, color="#7B241C", fontweight="bold", va="center", ha="left")

        ax.annotate("", xy=(tube_x - tube_hw, 8.7), xytext=(tube_x + tube_hw, 8.7),
                    arrowprops=dict(arrowstyle="<->", color="black", lw=1.2))
        ax.text(tube_x, 8.85, f"r = {schema.tube_radius * 1e3:.2f} mm", fontsize=9,
                ha="center")
        ax.text(tube_x + 0.9, col_top + 0.55, f"θ = {theta:.0f}°", fontsize=10,
                color="#1B4F72")

        notes = [
            f"h = 2T·cosθ / (rρg)",
            f"  = 2×{schema.surface_tension:.3f}×cos({theta:.0f}°) / "
            f"({schema.tube_radius:.1e}×{rho:.0f}×{g:.1f}) = {h * 100:.2f} cm",
            "h varies as 1/r — halving the tube radius doubles the effect.",
        ]
        title = schema.title or ("Capillary Rise" if h >= 0 else "Capillary Depression")

    elif setup == "hydraulic_press":
        f1, a1, a2 = schema.input_force, schema.piston_area_small, schema.piston_area_large
        f2 = _hydraulic_output_force(f1, a1, a2)
        ax.set_xlim(-1.0, 13.0)
        ax.set_ylim(-2.0, 8.2)

        # Piston widths scale as √A, so the drawn areas hold the true ratio A₂/A₁.
        # w1 is shrunk (never w2 clipped) to keep that ratio exact for any A₂/A₁.
        ratio = math.sqrt(a2 / a1)
        w2 = 4.6
        w1 = w2 / ratio
        if w1 > 1.4:
            w1, w2 = 1.4, 1.4 * ratio
        x1, x2 = 1.6, 9.0
        y_liq = 2.6

        ax.add_patch(mpatches.Rectangle((x1 - w1 / 2, 0.6), w1, 3.4, facecolor="white",
                                        edgecolor="black", linewidth=2.0))
        ax.add_patch(mpatches.Rectangle((x2 - w2 / 2, 0.6), w2, 3.4, facecolor="white",
                                        edgecolor="black", linewidth=2.0))
        ax.add_patch(mpatches.Rectangle((x1 - w1 / 2, 0.2), (x2 - x1) + (w1 + w2) / 2,
                                        0.9, facecolor="white", edgecolor="black",
                                        linewidth=2.0))
        for xc, w in ((x1, w1), (x2, w2)):
            ax.add_patch(mpatches.Rectangle((xc - w / 2 + 0.05, 0.25), w - 0.1,
                                            y_liq - 0.25, facecolor="#5DADE2",
                                            edgecolor="none", zorder=2))
        ax.add_patch(mpatches.Rectangle((x1 - w1 / 2 + 0.05, 0.25),
                                        (x2 - x1) + (w1 + w2) / 2 - 0.1, 0.85,
                                        facecolor="#5DADE2", edgecolor="none", zorder=2))
        for xc, w, lbl in ((x1, w1, "A₁"), (x2, w2, "A₂")):
            ax.add_patch(mpatches.Rectangle((xc - w / 2 + 0.05, y_liq), w - 0.1, 0.38,
                                            facecolor="#5D6D7E", edgecolor="black",
                                            linewidth=1.4, zorder=4))
        ax.annotate("", xy=(x1, y_liq + 0.45), xytext=(x1, y_liq + 2.6),
                    arrowprops=dict(arrowstyle="-|>", color="#C0392B", lw=2.6))
        ax.text(x1, y_liq + 2.8, f"F₁ = {f1:.0f} N", ha="center", fontsize=11,
                color="#C0392B", fontweight="bold")
        ax.annotate("", xy=(x2, y_liq + 2.8), xytext=(x2, y_liq + 0.45),
                    arrowprops=dict(arrowstyle="-|>", color="#1E8449", lw=3.4))
        ax.text(x2, y_liq + 3.0, f"F₂ = {f2:.0f} N", ha="center", fontsize=12,
                color="#1E8449", fontweight="bold")
        ax.text(x1, -0.1, f"A₁ = {a1:g} m²", ha="center", va="top", fontsize=9)
        ax.text(x2, -0.1, f"A₂ = {a2:g} m²", ha="center", va="top", fontsize=9)
        ax.text((x1 + x2) / 2, 7.6, "incompressible fluid — the pressure is the same "
                "everywhere (Pascal)", ha="center", fontsize=9.5, color="#1B4F72",
                zorder=5)

        notes = [
            f"Pascal:  F₁/A₁ = F₂/A₂,  so  F₂ = F₁·A₂/A₁ = {f1:.0f}×{a2:g}/{a1:g} = {f2:.0f} N",
            f"Mechanical advantage = A₂/A₁ = {a2 / a1:.0f}×   "
            f"(the small piston moves {a2 / a1:.0f}× further — work is not multiplied)",
        ]
        title = schema.title or "Hydraulic Press"

    else:   # floating_body
        frac = _submerged_fraction(schema.body_density, rho)
        ax.set_xlim(-1.0, 11.0)
        ax.set_ylim(-1.4, 7.6)

        ax.add_patch(mpatches.Rectangle((0.4, 0.0), 9.2, 4.6, facecolor="#AED6F1",
                                        edgecolor="black", linewidth=2.0))
        ax.plot([0.4, 9.6], [4.6, 4.6], color="#1B4F72", linewidth=2.0)
        ax.text(0.7, 1.0, f"fluid  ρ_f = {rho:.0f} kg/m³", fontsize=10, color="#1B4F72")

        # The block is drawn with EXACTLY frac of its height below the waterline —
        # that fraction is the answer to the question, so it cannot be eyeballed.
        bw, bh = 3.2, 2.4
        bx = 4.4
        sub = frac * bh
        by = 4.6 - sub                        # bottom of the block
        ax.add_patch(mpatches.Rectangle((bx, by), bw, bh, facecolor="#F5B041",
                                        edgecolor="black", linewidth=2.0, zorder=3))
        ax.add_patch(mpatches.Rectangle((bx, by), bw, sub, facecolor="#D68910",
                                        edgecolor="none", zorder=4))
        ax.plot([bx, bx + bw], [4.6, 4.6], color="#1B4F72", linewidth=2.0, zorder=5)
        ax.text(bx + bw + 0.3, by + bh - 0.35, f"ρ_b = {schema.body_density:.0f} kg/m³",
                ha="left", fontsize=10, fontweight="bold", zorder=8,
                bbox=dict(boxstyle="round,pad=0.25", facecolor="white", alpha=0.9,
                          edgecolor="none"))

        cx = bx + bw / 2
        # W acts at the centre of GRAVITY (centre of the whole block); F_B acts at the
        # centre of BUOYANCY — the centroid of the displaced fluid, i.e. of the
        # submerged part only. They are not the same point, and that is why a floating
        # body rights itself.
        y_g = by + bh / 2
        y_b = by + sub / 2
        ax.plot(cx + 0.7, y_g, "o", markersize=6, color="#C0392B", zorder=8)
        ax.text(cx + 0.85, y_g + 0.05, "G", fontsize=10, color="#C0392B",
                fontweight="bold", va="bottom", zorder=8)
        ax.plot(cx - 1.0, y_b, "o", markersize=6, color="#1E8449", zorder=8)
        ax.text(cx - 1.15, y_b + 0.05, "B", fontsize=10, color="#1E8449",
                fontweight="bold", va="bottom", ha="right", zorder=8)

        ax.annotate("", xy=(cx + 0.7, by - 1.5), xytext=(cx + 0.7, y_g),
                    arrowprops=dict(arrowstyle="-|>", color="#C0392B", lw=2.4),
                    zorder=7)
        ax.text(cx + 0.85, by - 1.55, "W = ρ_b·V·g", fontsize=11, color="#C0392B",
                va="center", ha="left", zorder=8)
        ax.annotate("", xy=(cx - 1.0, by + bh + 1.5), xytext=(cx - 1.0, y_b),
                    arrowprops=dict(arrowstyle="-|>", color="#1E8449", lw=2.4),
                    zorder=7)
        ax.text(cx - 1.0, by + bh + 1.65, "F_B = ρ_f·V_sub·g", fontsize=11,
                color="#1E8449", va="bottom", ha="center", zorder=8)

        ax.annotate("", xy=(bx - 0.35, by), xytext=(bx - 0.35, 4.6),
                    arrowprops=dict(arrowstyle="<->", color="#7B241C", lw=1.6))
        ax.text(bx - 0.5, by + sub / 2, f"{frac * 100:.0f}%\nsubmerged", fontsize=10,
                ha="right", va="center", color="#7B241C", fontweight="bold")

        notes = [
            "Floating equilibrium:  W = F_B,  that is  ρ_b·V·g = ρ_f·V_sub·g",
            f"V_sub/V = ρ_b/ρ_f = {schema.body_density:.0f}/{rho:.0f} = {frac:.2f}"
            f"  — exactly {frac * 100:.0f}% of the block is below the surface.",
        ]
        title = schema.title or "Floating Body (Archimedes)"

    if schema.show_derivation and notes:
        ax.text(0.5, -0.02, "\n".join(notes), transform=ax.transAxes, ha="center",
                va="top", fontsize=9.5, color="#1B4F72", linespacing=1.6,
                bbox=dict(boxstyle="round,pad=0.5", facecolor="#FEF9E7",
                          edgecolor="#B9770E"))

    ax.set_title(title, fontsize=13, fontweight="bold")
    fig.tight_layout()
    return _fig_to_svg_phys(fig)


# ── Kinematics: Motion Graphs ─────────────────────────────────────────────────

def _motion_series(schema) -> Tuple["np.ndarray", "np.ndarray", "np.ndarray", "np.ndarray"]:
    """(t, x, v, a) for a MotionGraphSchema — ONE motion, three views of it.

    v is the derivative of x and a the derivative of v, by construction: either the
    polynomial is differentiated analytically, or the piecewise-constant a is
    integrated to v and again to x. Three independently supplied curves would let
    the slope of one disagree with the next, which is the only thing the question
    ever asks about.
    """
    if schema.position_coeffs:
        c = np.array(schema.position_coeffs, dtype=float)
        t = np.linspace(0.0, float(schema.total_time), 600)
        powers = np.arange(len(c))
        x = np.sum(c[None, :] * t[:, None] ** powers[None, :], axis=1)
        dc = c[1:] * powers[1:]                      # d/dt of the polynomial
        v = (np.sum(dc[None, :] * t[:, None] ** np.arange(len(dc))[None, :], axis=1)
             if len(dc) else np.zeros_like(t))
        ddc = dc[1:] * np.arange(1, len(dc)) if len(dc) > 1 else np.array([])
        a = (np.sum(ddc[None, :] * t[:, None] ** np.arange(len(ddc))[None, :], axis=1)
             if len(ddc) else np.zeros_like(t))
        return t, x + schema.initial_position, v, a

    total = sum(p.duration for p in schema.phases)
    t = np.linspace(0.0, total, 600)
    x = np.zeros_like(t)
    v = np.zeros_like(t)
    a = np.zeros_like(t)

    t0 = 0.0
    # v is continuous across a phase boundary (a finite force cannot change it in
    # zero time), so only the first phase may declare an initial velocity.
    v0 = schema.phases[0].initial_velocity or 0.0
    x0 = schema.initial_position

    for i, ph in enumerate(schema.phases):
        t1 = t0 + ph.duration
        if i == len(schema.phases) - 1:
            m = (t >= t0 - 1e-12) & (t <= t1 + 1e-12)
        else:
            m = (t >= t0 - 1e-12) & (t < t1)
        dt = t[m] - t0
        a[m] = ph.acceleration
        v[m] = v0 + ph.acceleration * dt
        x[m] = x0 + v0 * dt + 0.5 * ph.acceleration * dt ** 2
        x0 = x0 + v0 * ph.duration + 0.5 * ph.acceleration * ph.duration ** 2
        v0 = v0 + ph.acceleration * ph.duration
        t0 = t1

    return t, x, v, a


def render_motion_graph(data: Dict[str, Any], canvas_w: int = 800,
                        canvas_h: int = 600) -> str:
    from diagrams.schemas.physics import MotionGraphSchema
    schema = MotionGraphSchema(**data)

    t, x, v, a = _motion_series(schema)
    n = len(schema.graph_types)

    fig, axes = plt.subplots(n, 1, sharex=True,
                             figsize=(canvas_w / 100, canvas_h / 100),
                             squeeze=False)
    axes = [row[0] for row in axes]

    series = {
        "position_time": (x, "x (m)", "#1B4F72", "Position-time"),
        "velocity_time": (v, "v (m/s)", "#C0392B", "Velocity-time"),
        "acceleration_time": (a, "a (m/s²)", "#1E8449", "Acceleration-time"),
    }
    t_slope = schema.slope_at if schema.slope_at is not None else t[-1] / 2.0
    t_slope = float(min(max(t_slope, t[0]), t[-1]))
    i_slope = int(np.argmin(np.abs(t - t_slope)))

    for ax, key in zip(axes, schema.graph_types):
        y, ylabel, color, name = series[key]
        ax.plot(t, y, color=color, linewidth=2.4, zorder=4)
        ax.axhline(0, color="black", linewidth=1.0)
        ax.set_ylabel(ylabel, fontsize=11)
        ax.grid(True, color="#eeeeee", linestyle="--", linewidth=0.7)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.set_title(name, fontsize=10, loc="left", color=color)

        # A constant series (uniform acceleration) has zero span, and padding by a
        # fraction of zero would pin the line to the spine.
        span = float(y.max() - y.min())
        pad = 0.15 * (span if span > 1e-9 else max(abs(float(y.max())), 1.0))
        ax.set_ylim(min(float(y.min()), 0.0) - pad, max(float(y.max()), 0.0) + pad)

        if schema.show_area and key == "velocity_time":
            # ∫v dt is the DISPLACEMENT, not the distance: area below the axis
            # subtracts. Signed fill, and the number comes from x, not from |v|.
            ax.fill_between(t, 0, v, where=(v >= 0), color="#C0392B", alpha=0.18)
            ax.fill_between(t, 0, v, where=(v < 0), color="#7D3C98", alpha=0.18)
            disp = x[-1] - x[0]
            ax.text(0.02, 0.95, f"area = ∫v dt = Δx = {disp:.1f} m",
                    transform=ax.transAxes, ha="left", va="top", fontsize=10,
                    color="#7B241C", fontweight="bold",
                    bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.85))

        if schema.show_slope and key in ("position_time", "velocity_time"):
            # Slope of x-t IS v; slope of v-t IS a. Both read off the same series.
            slope = (v[i_slope] if key == "position_time" else a[i_slope])
            y0 = y[i_slope]
            span = 0.18 * (t[-1] - t[0])
            tt = np.array([t_slope - span, t_slope + span])
            ax.plot(tt, y0 + slope * (tt - t_slope), color="black", linestyle="--",
                    linewidth=1.6, zorder=5)
            ax.plot(t_slope, y0, "ko", markersize=6, zorder=6)
            unit = "m/s" if key == "position_time" else "m/s²"
            sym = "v" if key == "position_time" else "a"
            ax.annotate(f"slope = {sym} = {slope:.1f} {unit}",
                        xy=(t_slope, y0), xytext=(12, 14),
                        textcoords="offset points", fontsize=9.5, color="black",
                        arrowprops=dict(arrowstyle="->", lw=1.0))

    axes[-1].set_xlabel("t (s)", fontsize=11)

    if schema.phases:
        for ax in axes:
            tb = 0.0
            for ph in schema.phases[:-1]:
                tb += ph.duration
                ax.axvline(tb, color="gray", linestyle=":", linewidth=1.0)
        tb = 0.0
        for ph in schema.phases:
            if ph.label:
                axes[0].text(tb + ph.duration / 2, axes[0].get_ylim()[1],
                             ph.label, ha="center", va="top", fontsize=9, color="gray")
            tb += ph.duration

    if schema.annotations:
        fig.text(0.5, 0.005, "   ·   ".join(schema.annotations), ha="center",
                 fontsize=9.5, color="#1B4F72")

    fig.suptitle(schema.title or "Motion Graphs", fontsize=13, fontweight="bold")
    fig.tight_layout(rect=(0, 0.03 if schema.annotations else 0, 1, 0.97))
    return _fig_to_svg_phys(fig)


# ── Simple Harmonic Motion ────────────────────────────────────────────────────

def _shm_period(schema) -> float:
    """T for each SHM setup — computed, never labelled from a param.

    Every one of these is 2π√(inertia/restoring-stiffness); a vertical spring has
    the SAME period as a horizontal one (gravity only shifts the equilibrium, it
    does not change k), which is exactly the trap the figure has to survive.
    """
    if schema.setup in ("spring_horizontal", "spring_vertical"):
        return 2.0 * math.pi * math.sqrt(schema.mass / schema.spring_constant)
    if schema.setup == "simple_pendulum":
        return 2.0 * math.pi * math.sqrt(schema.length / schema.gravity)
    return 2.0 * math.pi * math.sqrt(schema.inertia / schema.torsional_constant)


def _shm_series(amplitude: float, omega: float, t: "np.ndarray"):
    """x = A·cos(ωt), v = dx/dt, a = dv/dt = −ω²x.

    v LEADS x by 90° and a is in ANTIPHASE with x. Differentiating one expression
    is the only way to guarantee it; three hand-written curves drift.
    """
    x = amplitude * np.cos(omega * t)
    v = -amplitude * omega * np.sin(omega * t)
    a = -amplitude * omega ** 2 * np.cos(omega * t)
    return x, v, a


def render_shm_system(data: Dict[str, Any], canvas_w: int = 800,
                      canvas_h: int = 600) -> str:
    from diagrams.schemas.physics import SHMSystemSchema
    schema = SHMSystemSchema(**data)

    setup = schema.setup
    T = _shm_period(schema)
    omega = 2.0 * math.pi / T
    A = schema.amplitude

    if schema.show_graphs:
        fig = plt.figure(figsize=(canvas_w / 100, canvas_h / 100))
        gs = fig.add_gridspec(3, 2, width_ratios=[1.15, 1.25], hspace=0.35, wspace=0.30)
        ax = fig.add_subplot(gs[:, 0])
        gax = [fig.add_subplot(gs[i, 1]) for i in range(3)]
        # datalim, not box: the apparatus must fill the tall panel, because the label
        # font size is fixed in points and a shrunken drawing collides with its labels.
        ax.set_aspect("equal", adjustable="datalim")
    else:
        fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))
        gax = []
        ax.set_aspect("equal")

    ax.axis("off")

    if setup == "spring_horizontal":
        ax.set_xlim(-1.0, 9.0)
        ax.set_ylim(-3.0, 5.0)
        ax.add_patch(mpatches.Rectangle((-0.6, 0.2), 0.5, 3.4, facecolor="#AEB6BF",
                                        edgecolor="black", linewidth=1.6))
        for yy in np.linspace(0.35, 3.45, 7):
            ax.plot([-1.0, -0.6], [yy - 0.3, yy], color="black", linewidth=1.0)
        ax.plot([-0.6, 8.6], [0.2, 0.2], color="black", linewidth=2.0)

        xs = np.linspace(-0.1, 4.2, 200)
        ax.plot(xs, 1.9 + 0.42 * np.sin(2 * np.pi * (xs + 0.1) / 0.62),
                color="black", linewidth=1.8)
        ax.add_patch(mpatches.Rectangle((4.2, 0.9), 2.0, 2.0, facecolor="#F5B041",
                                        edgecolor="black", linewidth=2.0))
        # Symbols only inside the drawing: the numbers live in the caption, because a
        # point-sized label does not shrink with the figure and would sit across the
        # block and the amplitude arrow at small canvas sizes.
        ax.text(5.2, 1.9, "m", ha="center", va="center", fontsize=13,
                fontweight="bold")
        ax.text(2.0, 2.75, "k", ha="center", fontsize=13, fontweight="bold")
        ax.plot([5.2, 5.2], [0.2, 0.75], color="gray", linestyle="--", linewidth=1.2)
        ax.text(5.2, -0.05, "x = 0", ha="center", va="top", fontsize=9, color="gray")
        ax.annotate("", xy=(7.6, 1.9), xytext=(6.3, 1.9),
                    arrowprops=dict(arrowstyle="-|>", color="#C0392B", lw=2.0))
        ax.text(6.95, 2.15, "+A", fontsize=11, color="#C0392B", ha="center",
                fontweight="bold")
        ax.annotate("", xy=(4.1, 3.4), xytext=(6.3, 3.4),
                    arrowprops=dict(arrowstyle="-|>", color="#1B4F72", lw=1.6))
        ax.text(5.2, 3.55, "F = −kx  (restoring)", fontsize=10, color="#1B4F72",
                ha="center")
        params_line = (f"m = {schema.mass:g} kg,   k = {schema.spring_constant:g} N/m,"
                       f"   A = {A:g} m")
        formula = f"T = 2π√(m/k) = {T:.2f} s"

    elif setup == "spring_vertical":
        ax.set_xlim(-2.6, 4.6)
        ax.set_ylim(-1.0, 7.4)
        ax.plot([-1.4, 1.4], [7.0, 7.0], color="black", linewidth=2.4)
        for xx in np.linspace(-1.3, 1.2, 7):
            ax.plot([xx, xx + 0.28], [7.0, 7.3], color="black", linewidth=1.0)
        ys = np.linspace(7.0, 3.6, 200)
        ax.plot(0.42 * np.sin(2 * np.pi * (ys - 7.0) / 0.55), ys, color="black",
                linewidth=1.8)
        ax.add_patch(mpatches.Rectangle((-0.85, 2.2), 1.7, 1.4, facecolor="#F5B041",
                                        edgecolor="black", linewidth=2.0))
        ax.text(0, 2.9, "m", ha="center", va="center", fontsize=13,
                fontweight="bold")
        x0 = schema.mass * schema.gravity / schema.spring_constant
        ax.plot([-2.2, 2.6], [3.6, 3.6], color="gray", linestyle="--", linewidth=1.0)
        ax.plot([-2.2, 2.6], [5.0, 5.0], color="gray", linestyle=":", linewidth=1.0)
        ax.annotate("", xy=(2.2, 3.6), xytext=(2.2, 5.0),
                    arrowprops=dict(arrowstyle="<->", color="#7B241C", lw=1.4))
        ax.text(2.35, 4.3, f"x₀ = mg/k\n= {x0 * 100:.1f} cm", fontsize=9,
                color="#7B241C", va="center")
        ax.text(-2.35, 5.08, "natural length", fontsize=8.5, color="gray", va="bottom")
        ax.text(-2.35, 3.52, "equilibrium", fontsize=8.5, color="gray", va="top")
        ax.annotate("", xy=(0, 1.2), xytext=(0, 2.2),
                    arrowprops=dict(arrowstyle="-|>", color="#C0392B", lw=2.0))
        ax.text(0.12, 1.4, "mg", fontsize=10, color="#C0392B")
        # Gravity only OFFSETS the equilibrium by mg/k; it leaves k, and therefore
        # the period, untouched.
        params_line = (f"m = {schema.mass:g} kg,   k = {schema.spring_constant:g} N/m,"
                       f"   A = {A:g} m")
        formula = f"T = 2π√(m/k) = {T:.2f} s   (unchanged by gravity)"

    elif setup == "simple_pendulum":
        ax.set_xlim(-4.2, 4.2)
        ax.set_ylim(-5.6, 1.4)
        ax.plot([-2.0, 2.0], [0.9, 0.9], color="black", linewidth=2.4)
        for xx in np.linspace(-1.9, 1.7, 8):
            ax.plot([xx, xx + 0.3], [0.9, 1.2], color="black", linewidth=1.0)
        L = 4.4
        th = math.radians(18.0)
        bx, by = L * math.sin(th), 0.9 - L * math.cos(th)
        ax.plot([0, 0], [0.9, 0.9 - L], color="gray", linestyle="--", linewidth=1.2)
        ax.plot([0, bx], [0.9, by], color="black", linewidth=1.8)
        ax.plot(bx, by, "o", markersize=20, color="#F5B041", markeredgecolor="black",
                markeredgewidth=2.0, zorder=4)
        arc = mpatches.Arc((0, 0.9), 2.4, 2.4, angle=270, theta1=0,
                           theta2=math.degrees(th), color="#1B4F72", linewidth=1.4)
        ax.add_patch(arc)
        ax.text(0.35, -0.6, "θ", fontsize=12, color="#1B4F72")
        ax.text(bx / 2 - 0.55, (0.9 + by) / 2, "l", fontsize=13, ha="right",
                fontweight="bold")
        ax.annotate("", xy=(bx, by - 1.1), xytext=(bx, by),
                    arrowprops=dict(arrowstyle="-|>", color="#C0392B", lw=2.0))
        ax.text(bx + 0.12, by - 0.9, "mg", fontsize=10, color="#C0392B")
        ax.annotate("", xy=(bx - 1.15 * math.cos(th), by - 1.15 * math.sin(th)),
                    xytext=(bx, by),
                    arrowprops=dict(arrowstyle="-|>", color="#1E8449", lw=1.8))
        ax.text(bx - 1.5, by - 0.35, "mg sinθ", fontsize=9.5, color="#1E8449",
                ha="right")
        # Small-angle only: sinθ ≈ θ is what makes the restoring torque linear and
        # the motion simple-harmonic at all.
        params_line = (f"l = {schema.length:g} m,   g = {schema.gravity:g} m/s²,"
                       f"   A = {A:g} m")
        formula = f"T = 2π√(l/g) = {T:.2f} s   (small θ: sinθ ≈ θ)"

    else:   # torsional
        ax.set_xlim(-3.4, 3.4)
        ax.set_ylim(-3.8, 4.0)
        ax.plot([-1.6, 1.6], [3.6, 3.6], color="black", linewidth=2.4)
        for xx in np.linspace(-1.5, 1.3, 7):
            ax.plot([xx, xx + 0.28], [3.6, 3.9], color="black", linewidth=1.0)
        ax.plot([0, 0], [3.6, 0.6], color="black", linewidth=2.4)
        ax.text(0.22, 2.2, "wire (C)", fontsize=10, va="center")
        ax.add_patch(mpatches.Circle((0, -0.4), 2.0, facecolor="#D6EAF8",
                                     edgecolor="black", linewidth=2.0))
        ax.plot(0, -0.4, "ko", markersize=5)
        ax.text(0, -1.35, "I", ha="center", fontsize=13, fontweight="bold")
        arc = mpatches.Arc((0, -0.4), 3.2, 3.2, angle=0, theta1=-55, theta2=15,
                           color="#C0392B", linewidth=2.0)
        ax.add_patch(arc)
        ax.annotate("", xy=(1.6 * math.cos(math.radians(-52)) ,
                            -0.4 + 1.6 * math.sin(math.radians(-52))),
                    xytext=(1.6 * math.cos(math.radians(-40)),
                            -0.4 + 1.6 * math.sin(math.radians(-40))),
                    arrowprops=dict(arrowstyle="-|>", color="#C0392B", lw=2.0))
        ax.text(2.15, -1.5, "θ", fontsize=12, color="#C0392B")
        ax.text(0, -2.9, "τ = −Cθ  (restoring torque)", ha="center", fontsize=10,
                color="#1B4F72")
        params_line = (f"I = {schema.inertia:g} kg·m²,   "
                       f"C = {schema.torsional_constant:g} N·m/rad")
        formula = f"T = 2π√(I/C) = {T:.2f} s"

    if schema.show_period:
        box = params_line + "\n" + formula + f"\nω = 2π/T = {omega:.2f} rad/s"
        ax.text(0.5, -0.04, box, transform=ax.transAxes, ha="center", va="top",
                fontsize=10, fontweight="bold", color="#7B241C", linespacing=1.6,
                bbox=dict(boxstyle="round,pad=0.4", facecolor="#FEF9E7",
                          edgecolor="#B9770E"))

    if gax:
        t = np.linspace(0.0, schema.num_cycles * T, 600)
        x, v, a = _shm_series(A, omega, t)
        unit = "rad" if setup == "torsional" else "m"
        panels = [
            (x, f"x ({unit})", "#1B4F72", "x = A cos ωt"),
            (v, f"v ({unit}/s)", "#C0392B", "v = −Aω sin ωt   (leads x by 90°)"),
            (a, f"a ({unit}/s²)", "#1E8449", "a = −Aω² cos ωt = −ω²x   (antiphase)"),
        ]
        for gx, (y, ylabel, color, note) in zip(gax, panels):
            gx.plot(t, y, color=color, linewidth=2.0)
            gx.axhline(0, color="black", linewidth=0.9)
            gx.set_ylabel(ylabel, fontsize=9)
            gx.set_title(note, fontsize=9, loc="left", color=color)
            gx.tick_params(labelsize=8)
            gx.grid(True, color="#eeeeee", linestyle="--", linewidth=0.6)
            gx.spines["top"].set_visible(False)
            gx.spines["right"].set_visible(False)
            for k in range(int(schema.num_cycles) + 1):
                if k * T <= t[-1]:
                    gx.axvline(k * T, color="gray", linestyle=":", linewidth=0.8)
        gax[-1].set_xlabel("t (s)", fontsize=9)
        for gx in gax[:-1]:
            gx.set_xticklabels([])

    if schema.show_phase_note and gax:
        gax[2].text(0.5, -0.62, "v is 90° AHEAD of x;  a is exactly 180° out of phase "
                    "with x", transform=gax[2].transAxes, ha="center", va="top",
                    fontsize=9, color="#7B241C")

    _nm = setup.replace("_", " ").title()
    fig.suptitle(schema.title or f"Simple Harmonic Motion — {_nm}",
                 fontsize=13, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    return _fig_to_svg_phys(fig)


# ── Standing Waves ────────────────────────────────────────────────────────────

def _standing_wave_state(mode: str, harmonic: int, length: float, wave_speed: float,
                         on_invalid: str = "snap") -> Tuple[int, float, float]:
    """(n_effective, wavelength, frequency).

    A closed pipe has a displacement NODE at the closed end and an ANTINODE at the
    open end, so it fits an ODD number of quarter-wavelengths: L = n·λ/4 with
    n = 1, 3, 5 … An even harmonic simply does not exist; it is snapped up to the
    next odd one (or rejected), never drawn.
    """
    n = int(harmonic)
    if mode == "closed_pipe" and n % 2 == 0:
        if on_invalid == "reject":
            raise ValueError(
                f"A closed pipe supports only odd harmonics; n = {n} is impossible.")
        n += 1
    if mode == "closed_pipe":
        wavelength = 4.0 * length / n
    else:                       # string | open_pipe — both fit n half-wavelengths
        wavelength = 2.0 * length / n
    frequency = wave_speed / wavelength
    return n, wavelength, frequency


def _standing_wave_nodes(mode: str, n: int, length: float) -> Tuple[List[float], List[float]]:
    """(node positions, antinode positions) along the length, in metres."""
    if mode == "closed_pipe":
        # u(x) = A sin(nπx/2L): zeros (nodes) at x = 2Lk/n, extrema (antinodes)
        # midway between them. x = 0 (closed) is a node; x = L is an antinode.
        nodes = [2.0 * length * k / n for k in range(0, (n + 1) // 2)]
        antinodes = [2.0 * length * (k + 0.5) / n for k in range(0, (n + 1) // 2)]
    elif mode == "open_pipe":
        # u(x) = A cos(nπx/L): antinodes at both open ends.
        antinodes = [length * k / n for k in range(0, n + 1)]
        nodes = [length * (k + 0.5) / n for k in range(0, n)]
    else:                       # string — fixed ends are nodes
        nodes = [length * k / n for k in range(0, n + 1)]
        antinodes = [length * (k + 0.5) / n for k in range(0, n)]
    return [p for p in nodes if p <= length + 1e-9], \
           [p for p in antinodes if p <= length + 1e-9]


def render_standing_wave(data: Dict[str, Any], canvas_w: int = 800,
                         canvas_h: int = 600) -> str:
    from diagrams.schemas.physics import StandingWaveSchema
    schema = StandingWaveSchema(**data)

    mode, L = schema.mode, schema.length
    n, lam, freq = _standing_wave_state(mode, schema.harmonic, L, schema.wave_speed,
                                        schema.on_invalid_harmonic)
    snapped = (n != schema.harmonic)

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))
    ax.set_xlim(-0.12 * L, 1.16 * L)
    ax.set_ylim(-2.4, 2.5)
    ax.axis("off")

    xs = np.linspace(0.0, L, 600)
    A = 1.0
    if mode == "closed_pipe":
        env = A * np.sin(n * np.pi * xs / (2.0 * L))
    elif mode == "open_pipe":
        env = A * np.cos(n * np.pi * xs / L)
    else:
        env = A * np.sin(n * np.pi * xs / L)

    if mode == "string":
        ax.plot([0, 0], [-1.5, 1.5], color="black", linewidth=3.0)
        ax.plot([L, L], [-1.5, 1.5], color="black", linewidth=3.0)
        ax.plot([-0.1 * L, 1.1 * L], [0, 0], color="gray", linewidth=0.9,
                linestyle="--")
    else:
        # Pipe walls. A closed end is drawn SEALED, an open end left open — the
        # boundary condition is the figure's whole claim.
        ax.plot([0, L], [1.6, 1.6], color="black", linewidth=2.4)
        ax.plot([0, L], [-1.6, -1.6], color="black", linewidth=2.4)
        if mode == "closed_pipe":
            ax.plot([0, 0], [-1.6, 1.6], color="black", linewidth=3.4)
            ax.text(-0.02 * L, 1.85, "closed end (node)", fontsize=9.5, ha="left",
                    color="#7B241C", fontweight="bold")
            ax.text(L, 1.85, "open end (antinode)", fontsize=9.5, ha="right",
                    color="#1E8449", fontweight="bold")
        else:
            ax.text(0, 1.85, "open end (antinode)", fontsize=9.5, ha="left",
                    color="#1E8449", fontweight="bold")
            ax.text(L, 1.85, "open end (antinode)", fontsize=9.5, ha="right",
                    color="#1E8449", fontweight="bold")
        ax.plot([-0.1 * L, 1.1 * L], [0, 0], color="gray", linewidth=0.9,
                linestyle="--")

    ax.plot(xs, env, color="#1B4F72", linewidth=2.6, zorder=4)
    ax.plot(xs, -env, color="#1B4F72", linewidth=2.6, zorder=4)
    ax.fill_between(xs, -np.abs(env), np.abs(env), color="#AED6F1", alpha=0.35,
                    zorder=1)
    for ph in (0.35, 0.7):
        ax.plot(xs, ph * env, color="#5DADE2", linewidth=0.9, linestyle="--", zorder=3)
        ax.plot(xs, -ph * env, color="#5DADE2", linewidth=0.9, linestyle="--", zorder=3)

    nodes, antinodes = _standing_wave_nodes(mode, n, L)
    if schema.show_nodes:
        for p in nodes:
            ax.plot(p, 0.0, "o", markersize=8, color="#C0392B", zorder=6)
            # A node sitting on a boundary would put its letter on top of the wall,
            # so a boundary label is nudged inward instead of being centred on it.
            if p <= 1e-9:
                lx, la = p + 0.035 * L, "left"
            elif p >= L - 1e-9:
                lx, la = p - 0.035 * L, "right"
            else:
                lx, la = p, "center"
            ax.text(lx, 0.16, "N", fontsize=9, color="#C0392B", fontweight="bold",
                    ha=la, va="bottom", zorder=7)
    if schema.show_antinodes:
        for p in antinodes:
            yy = float(np.interp(p, xs, np.abs(env)))
            ax.plot([p, p], [-yy, yy], color="#1E8449", linestyle=":", linewidth=1.2,
                    zorder=5)
            ax.plot(p, yy, "^", markersize=8, color="#1E8449", zorder=6)
            ax.plot(p, -yy, "v", markersize=8, color="#1E8449", zorder=6)
            ax.text(p, yy + 0.12, "A", fontsize=9, color="#1E8449", fontweight="bold",
                    ha="center", va="bottom", zorder=7)

    if schema.show_wavelength:
        # One full λ spans two loops on a string/open pipe; on a closed pipe the first
        # loop is only a quarter-wave. The bar is therefore drawn from the COMPUTED λ,
        # never from a loop count, and it is truncated (with its fraction stated) when
        # a whole wavelength does not fit inside L.
        span = min(lam, L)
        y_arr = -2.05
        ax.annotate("", xy=(span, y_arr), xytext=(0.0, y_arr),
                    arrowprops=dict(arrowstyle="<->", color="#7D3C98", lw=1.6))
        frac = "λ" if span >= lam - 1e-9 else f"{span / lam:.2f}λ"
        ax.text(span / 2, y_arr - 0.08, frac, ha="center", va="top", fontsize=11,
                color="#7D3C98", fontweight="bold")
    ax.annotate("", xy=(L, 2.25), xytext=(0.0, 2.25),
                arrowprops=dict(arrowstyle="<->", color="black", lw=1.2))
    ax.text(L / 2, 2.32, f"L = {L:g} m", ha="center", va="bottom", fontsize=10)

    rel = {"string": "L = n·λ/2", "open_pipe": "L = n·λ/2",
           "closed_pipe": "L = n·λ/4  (n odd)"}[mode]
    fund = schema.wave_speed / (4.0 * L) if mode == "closed_pipe" \
        else schema.wave_speed / (2.0 * L)
    n_n, n_a = len(nodes), len(antinodes)
    lines = [
        f"{rel}   gives   λ = {lam:.3f} m      "
        f"[{n_n} node{'s' if n_n != 1 else ''} (N),  "
        f"{n_a} antinode{'s' if n_a != 1 else ''} (A)]",
        f"f = v/λ = {schema.wave_speed:g}/{lam:.3f} = {freq:.1f} Hz",
    ]
    if schema.show_frequency_relation:
        if mode == "closed_pipe":
            lines.append(f"f_n = n·f₁ with n = 1, 3, 5 …   (f₁ = {fund:.1f} Hz; "
                         f"even harmonics are absent)")
        else:
            lines.append(f"f_n = n·f₁ with n = 1, 2, 3 …   (f₁ = {fund:.1f} Hz)")
    if snapped:
        lines.append(f"n = {schema.harmonic} is even and impossible in a closed pipe "
                     f"— snapped to n = {n}.")
    ax.text(0.5, -0.02, "\n".join(lines), transform=ax.transAxes, ha="center",
            va="top", fontsize=10, color="#1B4F72", linespacing=1.6,
            bbox=dict(boxstyle="round,pad=0.5", facecolor="#FEF9E7",
                      edgecolor="#B9770E"))

    _mn = {"string": "String fixed at both ends", "open_pipe": "Open Pipe",
           "closed_pipe": "Closed Pipe"}[mode]
    ax.set_title(schema.title or f"{_mn} — harmonic n = {n}",
                 fontsize=13, fontweight="bold")
    fig.tight_layout()
    return _fig_to_svg_phys(fig)


# ── Elasticity: Stress-Strain Curve ───────────────────────────────────────────

def _stress_strain_curve(material: str):
    """(strain, stress, marked points) for each material class.

    The SHAPES must differ, not just the labels: a brittle solid fractures within a
    whisker of its proportional limit (no plastic plateau, no necking), while a
    ductile one yields, work-hardens and necks over a strain tens of times larger.
    An elastomer has no straight portion at all — Hooke's law never applies to it.
    """
    pts: Dict[str, Tuple[float, float]] = {}

    if material == "brittle":
        # Fracture arrives within a few per-cent of strain past the proportional
        # limit: no yield plateau, no work-hardening, no necking. The specimen breaks
        # AT its maximum stress, so U and F are the same point.
        e_p, s_p = 0.0022, 1.00
        e_f = 0.0024
        e1 = np.linspace(0.0, e_p, 140)
        s1 = (s_p / e_p) * e1
        e2 = np.linspace(e_p, e_f, 40)
        s2 = s_p + (s_p / e_p) * 0.55 * (e2 - e_p)
        strain = np.concatenate([e1, e2])
        stress = np.concatenate([s1, s2])
        pts["P"] = (e_p, s_p)
        pts["F"] = (e_f, float(s2[-1]))     # = U: it ruptures at its peak stress
        elastic_end = e_p

    elif material == "elastomer":
        # Rubber: J-shaped, no linear region, strains of several hundred per cent. It
        # has no proportional limit and no yield point to mark — only a rupture.
        strain = np.linspace(0.0, 6.0, 400)
        stress = 0.06 * (strain + 0.28 * strain ** 3)
        pts["F"] = (6.0, float(stress[-1]))
        elastic_end = 6.0

    else:   # ductile — mild steel
        e_p, s_p = 0.0020, 1.00           # proportional limit
        e_e, s_e = 0.0028, 1.10           # elastic limit
        e_y, s_y = 0.0060, 1.15           # yield point / plateau
        e_u, s_u = 0.1200, 1.80           # ultimate tensile strength
        e_f, s_f = 0.1900, 1.45           # fracture, after necking
        e1 = np.linspace(0.0, e_p, 80)
        s1 = (s_p / e_p) * e1
        e2 = np.linspace(e_p, e_e, 40)
        s2 = s_p + (s_e - s_p) * ((e2 - e_p) / (e_e - e_p)) ** 0.7
        e3 = np.linspace(e_e, e_y, 40)    # yielding: strain grows at nearly fixed stress
        s3 = s_e + (s_y - s_e) * ((e3 - e_e) / (e_y - e_e))
        e4 = np.linspace(e_y, e_u, 160)   # strain hardening
        s4 = s_y + (s_u - s_y) * np.sin(0.5 * np.pi * (e4 - e_y) / (e_u - e_y))
        e5 = np.linspace(e_u, e_f, 90)    # necking — stress FALLS before it breaks
        s5 = s_u - (s_u - s_f) * ((e5 - e_u) / (e_f - e_u)) ** 1.6
        strain = np.concatenate([e1, e2, e3, e4, e5])
        stress = np.concatenate([s1, s2, s3, s4, s5])
        pts["P"] = (e_p, s_p)
        pts["E"] = (e_e, s_e)
        pts["Y"] = (e_y, s_y)
        pts["U"] = (e_u, s_u)
        pts["F"] = (e_f, s_f)
        elastic_end = e_e

    return strain, stress, pts, elastic_end


_STRESS_STRAIN_NAME = {"ductile": "Mild steel (ductile)",
                       "brittle": "Cast iron / glass (brittle)",
                       "elastomer": "Rubber (elastomer)"}

_STRESS_STRAIN_POINT_LABEL = {
    "P": "P — proportional limit",
    "E": "E — elastic limit",
    "Y": "Y — yield point",
    "U": "U — ultimate tensile strength",
    "F": "F — fracture",
}


def render_stress_strain(data: Dict[str, Any], canvas_w: int = 800,
                         canvas_h: int = 600) -> str:
    from diagrams.schemas.physics import StressStrainSchema
    schema = StressStrainSchema(**data)

    material = schema.material
    strain, stress, pts, elastic_end = _stress_strain_curve(material)

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))
    ax.plot(strain, stress, color="#1B4F72", linewidth=2.6, zorder=5)

    x_max = float(strain[-1]) * 1.18
    y_max = float(stress.max()) * 1.30
    ax.set_xlim(0, x_max)
    ax.set_ylim(0, y_max)

    if schema.show_regions:
        e_end = float(strain[-1])
        ax.axvspan(0, elastic_end, color="#D5F5E3", alpha=0.8, zorder=0)
        ax.axvspan(elastic_end, e_end, color="#FADBD8", alpha=0.7, zorder=0)
        if material == "elastomer":
            # Rubber returns to its original length: the whole curve is elastic, even
            # though none of it is linear. Elastic is not the same as Hookean.
            ax.text(elastic_end / 2, y_max * 0.94, "elastic", ha="center", fontsize=10,
                    color="#196F3D", fontweight="bold")
            ax.text(elastic_end / 2, y_max * 0.86,
                    "(entirely elastic — but NOT linear:\nHooke's law never holds)",
                    ha="center", fontsize=9, color="#196F3D")
        else:
            # Either band can be a sliver — the elastic one for a ductile metal, the
            # plastic one for a brittle solid. A name printed inside a sliver just
            # overprints its neighbour, so a band is only named when it is wide enough
            # to hold the word; the narrow one is called out by a leader instead.
            if elastic_end / x_max > 0.10:
                ax.text(elastic_end / 2, y_max * 0.94, "elastic", ha="center",
                        fontsize=10, color="#196F3D", fontweight="bold")
            if (e_end - elastic_end) / x_max > 0.15:
                ax.text((elastic_end + e_end) / 2, y_max * 0.94, "plastic",
                        ha="center", fontsize=10, color="#943126", fontweight="bold")

    # The elastic region of a ductile metal is well under 5% of its fracture strain.
    # Drawn to scale — which it must be, or the plastic region is a lie — P, E and Y
    # land on top of one another, so they are labelled in a magnified inset instead of
    # being spread out by distorting the axis.
    zoom = None
    if material == "ductile":
        zoom = ax.inset_axes([0.46, 0.09, 0.50, 0.44])
        m = strain <= pts["Y"][0] * 1.8
        zoom.plot(strain[m], stress[m], color="#1B4F72", linewidth=2.2, zorder=5)
        zoom.set_xlim(0, pts["Y"][0] * 1.8)
        zoom.set_ylim(0, pts["Y"][1] * 1.35)
        zoom.set_title("elastic region (magnified)", fontsize=9, color="#196F3D")
        zoom.tick_params(labelsize=7)
        zoom.set_facecolor("white")
        _rect, _conn = ax.indicate_inset_zoom(zoom, edgecolor="#196F3D", alpha=0.9)
        for _line in _conn:
            # The connectors would run diagonally across the whole curve; the
            # highlighted rectangle alone says which slice is magnified.
            _line.set_visible(False)

    lin_ax = zoom if zoom is not None else ax
    if schema.show_hookes_law_region and material != "elastomer":
        e_p, s_p = pts["P"]
        lin_ax.plot([0, e_p], [0, s_p], color="#C0392B", linewidth=3.0, zorder=6)
        lx_max = lin_ax.get_xlim()[1]
        ly_max = lin_ax.get_ylim()[1]
        lin_ax.annotate("Hooke's law region\n(stress is proportional to strain)",
                        xy=(e_p * 0.5, s_p * 0.5),
                        xytext=(lx_max * 0.42, ly_max * 0.16), fontsize=8.5,
                        color="#C0392B",
                        arrowprops=dict(arrowstyle="->", color="#C0392B", lw=1.2))

    if schema.show_young_modulus and material != "elastomer":
        e_p, s_p = pts["P"]
        e_t, s_t = e_p * 0.72, s_p * 0.72
        lin_ax.plot([0, e_t, e_t], [0, 0, s_t], color="#7D3C98", linestyle="--",
                    linewidth=1.4, zorder=6)
        lin_ax.text(e_t * 0.10, s_t * 0.80,
                    f"Y = stress/strain = slope = {s_p / e_p:.0f}",
                    fontsize=8.5, color="#7D3C98", va="center")

    if schema.mark_points:
        # Points on the linear part go in the inset (ductile); the rest stay on the
        # main axes where there is room for them.
        inset_keys = {"P", "E", "Y"} if zoom is not None else set()
        main_offsets = {"P": (-34, 22), "E": (14, 24), "Y": (0, -30),
                        "U": (-14, 22), "F": (14, 12)}
        zoom_offsets = {"P": (14, -22), "E": (10, 18), "Y": (14, 12)}
        for key, (ex, sy) in pts.items():
            target = zoom if key in inset_keys else ax
            offs = zoom_offsets if key in inset_keys else main_offsets
            target.plot(ex, sy, "o", markersize=6, color="black", zorder=7)
            target.annotate(_STRESS_STRAIN_POINT_LABEL[key], xy=(ex, sy),
                            xytext=offs.get(key, (10, 10)), textcoords="offset points",
                            fontsize=8.5 if key in inset_keys else 9,
                            arrowprops=dict(arrowstyle="->", lw=0.9, color="gray"))
        # Fracture: the curve STOPS. An × marks where the specimen breaks.
        fx, fy = pts["F"]
        ax.plot(fx, fy, "X", markersize=13, color="#C0392B", zorder=8)
        if material == "brittle":
            ax.annotate("it fractures at its PEAK stress:\nU and F are the same point",
                        xy=(fx, fy), xytext=(-215, -30), textcoords="offset points",
                        fontsize=8.5, color="#C0392B", ha="left",
                        arrowprops=dict(arrowstyle="->", lw=0.9, color="#C0392B"))
            ax.annotate("plastic region — barely exists", xy=((elastic_end + fx) / 2,
                                                              y_max * 0.30),
                        xytext=(-90, -40), textcoords="offset points", fontsize=8.5,
                        color="#943126",
                        arrowprops=dict(arrowstyle="->", lw=0.9, color="#943126"))
        if material == "ductile":
            e_u = pts["U"][0]
            ax.annotate("necking", xy=((e_u + fx) / 2, float(np.interp((e_u + fx) / 2,
                                                                       strain, stress))),
                        xytext=(2, -36), textcoords="offset points", fontsize=9,
                        color="#943126", ha="center",
                        arrowprops=dict(arrowstyle="->", lw=0.9, color="#943126"))

    ax.set_xlabel("Strain  (ΔL/L)", fontsize=11)
    ax.set_ylabel("Stress  (F/A)", fontsize=11)
    ax.grid(True, color="#eeeeee", linestyle="--", linewidth=0.7, zorder=1)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    name = schema.material_name or _STRESS_STRAIN_NAME[material]
    ax.set_title(schema.title or f"Stress-Strain Curve — {name}",
                 fontsize=13, fontweight="bold")
    fig.tight_layout()
    return _fig_to_svg_phys(fig)


# ── Calorimetry: Heating Curve ────────────────────────────────────────────────

def _heating_curve_segments(schema) -> List[Dict[str, Any]]:
    """The five segments of T vs Q, in ORDER, with cumulative heat in joules.

    A phase change is a HORIZONTAL segment — the temperature does not rise while
    latent heat is being absorbed. The plateau WIDTHS are the latent heats
    themselves (Q = mL), so for water the boiling plateau (L_v = 2.26 MJ/kg) comes
    out ~6.8× wider than the melting plateau (L_f = 0.334 MJ/kg): that ratio is the
    physics, and it is computed, never drawn by eye.
    """
    m = schema.mass
    segs: List[Dict[str, Any]] = []
    q = 0.0

    def _add(dq, t0, t1, name, plateau):
        nonlocal q
        segs.append(dict(q0=q, q1=q + dq, t0=t0, t1=t1, name=name, plateau=plateau))
        q += dq

    _add(m * schema.specific_heat_solid * (schema.melting_point - schema.start_temp),
         schema.start_temp, schema.melting_point, "solid", False)
    _add(m * schema.latent_heat_fusion,
         schema.melting_point, schema.melting_point, "melting", True)
    _add(m * schema.specific_heat_liquid * (schema.boiling_point - schema.melting_point),
         schema.melting_point, schema.boiling_point, "liquid", False)
    _add(m * schema.latent_heat_vaporisation,
         schema.boiling_point, schema.boiling_point, "boiling", True)
    _add(m * schema.specific_heat_gas * (schema.end_temp - schema.boiling_point),
         schema.boiling_point, schema.end_temp, "gas", False)
    return segs


_HEATING_REGION = {
    "solid":   ("#AED6F1", "solid"),
    "melting":  ("#5DADE2", "melting\n(solid + liquid)"),
    "liquid":  ("#A9DFBF", "liquid"),
    "boiling":  ("#F5B041", "boiling\n(liquid + gas)"),
    "gas":     ("#F5B7B1", "gas"),
}


def render_heating_curve(data: Dict[str, Any], canvas_w: int = 800,
                         canvas_h: int = 600) -> str:
    from diagrams.schemas.physics import HeatingCurveSchema
    schema = HeatingCurveSchema(**data)

    segs = _heating_curve_segments(schema)

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))

    q_end = segs[-1]["q1"]
    scale = 1e-3    # J → kJ on the x-axis

    for seg in segs:
        colour, _ = _HEATING_REGION[seg["name"]]
        ax.axvspan(seg["q0"] * scale, seg["q1"] * scale, color=colour, alpha=0.55,
                   zorder=0)
        ax.plot([seg["q0"] * scale, seg["q1"] * scale],
                [seg["t0"], seg["t1"]], color="#1B4F72", linewidth=2.8, zorder=5)

    t_min = schema.start_temp
    t_max = schema.end_temp
    t_pad = 0.14 * (t_max - t_min)
    ax.set_ylim(t_min - t_pad, t_max + t_pad)
    ax.set_xlim(-0.02 * q_end * scale, 1.02 * q_end * scale)

    # Phase-change temperatures as reference lines
    for temp, lbl in ((schema.melting_point, "melting point"),
                      (schema.boiling_point, "boiling point")):
        ax.axhline(temp, color="gray", linestyle="--", linewidth=0.9, zorder=1)
        ax.text(-0.01 * q_end * scale, temp, f"{temp:g}°C",
                fontsize=9, ha="right", va="center", color="#7B241C")

    if schema.show_regions:
        for seg in segs:
            _, name = _HEATING_REGION[seg["name"]]
            xc = 0.5 * (seg["q0"] + seg["q1"]) * scale
            # A plateau region is a thin vertical strip; its label rides above the
            # plot area with a leader rather than being crushed inside the strip.
            if seg["plateau"] and schema.show_plateau_labels:
                ax.annotate(name, xy=(xc, seg["t0"]),
                            xytext=(xc, t_max + t_pad * 0.30),
                            fontsize=9, ha="center", va="bottom", color="#7B241C",
                            fontweight="bold",
                            arrowprops=dict(arrowstyle="->", lw=0.9, color="#7B241C"))
            elif not seg["plateau"]:
                ax.text(xc, 0.5 * (seg["t0"] + seg["t1"]), name, fontsize=10,
                        ha="center", va="center", color="#1B4F72", fontweight="bold",
                        rotation=0)

    if schema.show_heat_values:
        q_fus = schema.mass * schema.latent_heat_fusion
        q_vap = schema.mass * schema.latent_heat_vaporisation
        ratio = q_vap / q_fus
        notes = [
            "Temperature is CONSTANT during a phase change — the heat supplied "
            "becomes latent heat, not kinetic energy.",
            f"Melting plateau  Q = mL_f = {q_fus / 1000:.0f} kJ      "
            f"Boiling plateau  Q = mL_v = {q_vap / 1000:.0f} kJ",
            f"The boiling plateau is L_v/L_f = {ratio:.1f}× as wide as the melting "
            f"plateau — vaporisation costs far more energy than fusion.",
        ]
        ax.text(0.5, -0.16, "\n".join(notes), transform=ax.transAxes, ha="center",
                va="top", fontsize=9.5, color="#1B4F72", linespacing=1.6,
                bbox=dict(boxstyle="round,pad=0.5", facecolor="#FEF9E7",
                          edgecolor="#B9770E"))

    ax.set_xlabel("Heat added  Q (kJ)", fontsize=11)
    ax.set_ylabel("Temperature  T (°C)", fontsize=11)
    ax.grid(True, color="#eeeeee", linestyle="--", linewidth=0.7, zorder=1)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_title(schema.title or f"Heating Curve — {schema.substance}",
                 fontsize=13, fontweight="bold")
    fig.tight_layout(rect=(0, 0.14 if schema.show_heat_values else 0, 1, 1))
    return _fig_to_svg_phys(fig)


# ── Blackbody Radiation Spectrum ──────────────────────────────────────────────

# Planck / Wien constants (SI). Kept local and named so they cannot collide with
# the eV-based constants used by the photoelectric renderer.
_PLANCK_H = 6.62607015e-34      # J·s
_LIGHT_C = 2.99792458e8        # m/s
_BOLTZ_K = 1.380649e-23        # J/K
_WIEN_B = 2.897771955e-3       # m·K


def _wien_peak_nm(temperature: float) -> float:
    """λ_max in nm from Wien's displacement law λ_max·T = b.

    The peak moves to SHORTER wavelength as T rises: 3000 K → 966 nm,
    6000 K → 483 nm. This is the whole content of the figure and is computed, not
    positioned by hand.
    """
    return _WIEN_B / temperature * 1e9


def _planck_spectral(lam_m: "np.ndarray", temperature: float) -> "np.ndarray":
    """Spectral radiance B(λ,T) (arbitrary units) from Planck's law.

    A hotter body radiates MORE at every wavelength (its curve lies entirely above
    a cooler one), and its peak sits at a shorter λ. Both facts fall straight out
    of this expression, so neither is faked.
    """
    x = _PLANCK_H * _LIGHT_C / (lam_m * _BOLTZ_K * temperature)
    return (2.0 * _PLANCK_H * _LIGHT_C ** 2) / (lam_m ** 5 * (np.exp(x) - 1.0))


def render_blackbody_spectrum(data: Dict[str, Any], canvas_w: int = 800,
                              canvas_h: int = 600) -> str:
    from diagrams.schemas.physics import BlackbodySpectrumSchema
    schema = BlackbodySpectrumSchema(**data)

    temps = sorted(schema.temperatures)
    # Plot from just above 0 out to a little past the COOLEST peak, so every
    # curve's maximum is on screen.
    max_peak_nm = _wien_peak_nm(min(temps))
    lam_max_nm = min(max_peak_nm * 2.6, 3000.0)
    lam_nm = np.linspace(20.0, lam_max_nm, 700)
    lam_m = lam_nm * 1e-9

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))

    colours = ["#5DADE2", "#1B4F72", "#E67E22", "#C0392B", "#7D3C98", "#1E8449"]
    peak_pts: List[Tuple[float, float]] = []
    for i, T in enumerate(temps):
        B = _planck_spectral(lam_m, T)
        colour = colours[i % len(colours)]
        ax.plot(lam_nm, B, color=colour, linewidth=2.4, zorder=4,
                label=f"{T:g} K")
        pk_nm = _wien_peak_nm(T)
        pk_B = float(_planck_spectral(np.array([pk_nm * 1e-9]), T)[0])
        peak_pts.append((pk_nm, pk_B))
        if schema.show_peak_labels:
            ax.plot(pk_nm, pk_B, "o", markersize=6, color=colour, zorder=6)
            ax.annotate(f"λ_max = {pk_nm:.0f} nm", xy=(pk_nm, pk_B),
                        xytext=(14, 6), textcoords="offset points", fontsize=8.5,
                        color=colour)

    if schema.log_intensity:
        ax.set_yscale("log")

    if schema.show_wien_line and len(peak_pts) >= 2:
        px = [p[0] for p in peak_pts]
        py = [p[1] for p in peak_pts]
        order = np.argsort(px)
        ax.plot(np.array(px)[order], np.array(py)[order], color="black",
                linestyle="--", linewidth=1.4, zorder=5)
        ax.text(px[int(order[-1])], py[int(order[-1])],
                "  Wien's law\n  (locus of peaks)", fontsize=8.5, color="black",
                va="center")

    if schema.show_visible_band:
        # 380–740 nm — the peak crosses INTO the visible only for hot bodies.
        ax.axvspan(380, 740, color="#F9E79F", alpha=0.35, zorder=0)
        ax.text(560, ax.get_ylim()[1] * 0.96, "visible", fontsize=9, ha="center",
                va="top", color="#7B241C")

    ax.set_xlim(0, lam_max_nm)
    if not schema.log_intensity:
        ax.set_ylim(bottom=0)
    ax.set_xlabel("Wavelength  λ (nm)", fontsize=11)
    ax.set_ylabel("Spectral intensity  (arb. units)", fontsize=11)
    ax.grid(True, color="#eeeeee", linestyle="--", linewidth=0.7, zorder=1)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(fontsize=9, loc="upper right", framealpha=0.9)
    ax.set_title(schema.title or "Black-body Radiation Spectrum",
                 fontsize=13, fontweight="bold")
    fig.tight_layout()
    return _fig_to_svg_phys(fig)


# ── Kinetic Theory: Maxwell-Boltzmann Distribution ────────────────────────────

_GAS_R = 8.314462618           # J/(mol·K)


def _mb_speeds(temperature: float, molar_mass_gmol: float) -> Tuple[float, float, float]:
    """(v_mp, v_avg, v_rms) in m/s — always in this strict order.

    v_mp = √(2RT/M) < v_avg = √(8RT/πM) < v_rms = √(3RT/M): the coefficients
    2 < 8/π ≈ 2.546 < 3 fix the ordering for every gas and temperature. They are
    computed here so the three markers can never be drawn out of order.
    """
    M = molar_mass_gmol / 1000.0   # kg/mol
    v_mp = math.sqrt(2.0 * _GAS_R * temperature / M)
    v_avg = math.sqrt(8.0 * _GAS_R * temperature / (math.pi * M))
    v_rms = math.sqrt(3.0 * _GAS_R * temperature / M)
    return v_mp, v_avg, v_rms


def _mb_pdf(v: "np.ndarray", temperature: float, molar_mass_gmol: float) -> "np.ndarray":
    """Maxwell-Boltzmann speed pdf f(v). ∫f dv = 1 for every T and M.

    Because it is a normalised probability density, the AREA under every curve is
    the same (unity); raising T only broadens and flattens it and slides the peak
    right. A figure whose curves enclose different areas is simply wrong.
    """
    M = molar_mass_gmol / 1000.0
    a = M / (2.0 * _GAS_R * temperature)
    return 4.0 * math.pi * (a / math.pi) ** 1.5 * v ** 2 * np.exp(-a * v ** 2)


def render_maxwell_boltzmann(data: Dict[str, Any], canvas_w: int = 800,
                             canvas_h: int = 600) -> str:
    from diagrams.schemas.physics import MaxwellBoltzmannSchema
    schema = MaxwellBoltzmannSchema(**data)

    # Two ways to make a family of curves: vary T at fixed gas, or vary the gas at
    # fixed T. Either way each curve is a normalised pdf.
    if schema.molar_masses:
        series = [(schema.reference_temperature, M, f"{M:g} g/mol")
                  for M in schema.molar_masses]
        vary = "gas"
    else:
        series = [(T, schema.molar_mass, f"{T:g} K")
                  for T in schema.temperatures]
        vary = "T"

    # Choose the speed axis from the fastest curve (highest T / lightest gas).
    v_rms_max = max(_mb_speeds(T, M)[2] for T, M, _ in series)
    v = np.linspace(0.0, v_rms_max * 2.2, 700)

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))
    colours = ["#5DADE2", "#1B4F72", "#C0392B", "#E67E22", "#7D3C98", "#1E8449"]

    for i, (T, M, lbl) in enumerate(series):
        f = _mb_pdf(v, T, M)
        ax.plot(v, f, color=colours[i % len(colours)], linewidth=2.4, zorder=4,
                label=lbl)

    # Speed markers on the FIRST curve only, to keep the figure readable.
    if schema.show_speed_markers:
        T0, M0, _ = series[0]
        v_mp, v_avg, v_rms = _mb_speeds(T0, M0)
        f_at = lambda vv: float(_mb_pdf(np.array([vv]), T0, M0)[0])
        for vv, name, colour in ((v_mp, "$v_{mp}$", "#1E8449"),
                                 (v_avg, "$v_{avg}$", "#7D3C98"),
                                 (v_rms, "$v_{rms}$", "#C0392B")):
            ax.plot([vv, vv], [0, f_at(vv)], color=colour, linestyle="--",
                    linewidth=1.4, zorder=5)
            ax.text(vv, f_at(vv), name, fontsize=10, color=colour, ha="center",
                    va="bottom")
        ax.annotate(f"$v_{{mp}}$ < $v_{{avg}}$ < $v_{{rms}}$\n"
                    f"({v_mp:.0f} < {v_avg:.0f} < {v_rms:.0f} m/s)",
                    xy=(v_rms, f_at(v_rms)), xytext=(0.52, 0.58),
                    textcoords="axes fraction", fontsize=9.5, color="#7B241C",
                    ha="left")

    if schema.show_area_note:
        note = ("Every curve is normalised: the AREA under it = 1 (the total probability).\n"
                "Raising T broadens and flattens the curve and shifts the peak to higher\n"
                "speed, but the enclosed area is unchanged.")
        if vary == "gas":
            note = ("Every curve is normalised: the AREA under it = 1.\n"
                    "A lighter gas (smaller M) is faster — its peak lies further right —\n"
                    "yet the enclosed area is the same.")
        ax.text(0.5, -0.16, note, transform=ax.transAxes, ha="center", va="top",
                fontsize=9.5, color="#1B4F72", linespacing=1.6,
                bbox=dict(boxstyle="round,pad=0.5", facecolor="#FEF9E7",
                          edgecolor="#B9770E"))

    ax.set_xlim(0, v[-1])
    ax.set_ylim(bottom=0)
    ax.set_xlabel("Molecular speed  v (m/s)", fontsize=11)
    ax.set_ylabel("f(v)  (probability density, s/m)", fontsize=11)
    ax.grid(True, color="#eeeeee", linestyle="--", linewidth=0.7, zorder=1)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(fontsize=9, loc="upper right", title=schema.gas_name if vary == "T" else None,
              framealpha=0.9)
    ax.set_title(schema.title or "Maxwell-Boltzmann Speed Distribution",
                 fontsize=13, fontweight="bold")
    fig.tight_layout(rect=(0, 0.14 if schema.show_area_note else 0, 1, 1))
    return _fig_to_svg_phys(fig)


# ── Gravitation ───────────────────────────────────────────────────────────────

_GRAV_G = 6.67430e-11          # N·m²/kg²
_EARTH_M = 5.972e24           # kg
_EARTH_GM = _GRAV_G * _EARTH_M   # ≈ 3.986e14
_EARTH_R = 6.371e6            # m
_G_SURFACE = _EARTH_GM / _EARTH_R ** 2   # ≈ 9.82 m/s²


def _orbital_velocity(r_m: float) -> float:
    """v = √(GM/r) — a higher orbit is SLOWER, which is the usual surprise."""
    return math.sqrt(_EARTH_GM / r_m)


def _orbital_period(r_m: float) -> float:
    """T = 2π√(r³/GM), Kepler's third law for a circular orbit."""
    return 2.0 * math.pi * math.sqrt(r_m ** 3 / _EARTH_GM)


def _g_at_radius(r_m: float, R_m: float = _EARTH_R,
                 g_surface: float = _G_SURFACE) -> float:
    """g(r): rises LINEARLY inside the Earth, falls as 1/r² outside.

    Both branches meet at r = R with the same value g_surface — the surface is the
    maximum. Inside, only the mass within radius r pulls (g ∝ r); outside, the
    whole mass acts from the centre (g ∝ 1/r²). The continuity at R is the point
    of the graph, so it is enforced by construction, not hoped for.
    """
    if r_m <= R_m:
        return g_surface * r_m / R_m
    return g_surface * R_m ** 2 / r_m ** 2


def _solve_kepler(mean_anomaly: float, e: float) -> float:
    """Eccentric anomaly E from M = E − e·sinE (Newton's method).

    Needed so the orbit can be sampled at EQUAL TIME steps: equal areas are swept
    in equal times only if the points are spaced by equal mean anomaly, never by
    equal angle. Drawing equal-angle sectors is the classic wrong picture.
    """
    E = mean_anomaly if e < 0.8 else math.pi
    for _ in range(60):
        E -= (E - e * math.sin(E) - mean_anomaly) / (1.0 - e * math.cos(E))
    return E


def render_gravitation(data: Dict[str, Any], canvas_w: int = 800,
                       canvas_h: int = 600) -> str:
    from diagrams.schemas.physics import GravitationSchema
    schema = GravitationSchema(**data)
    setup = schema.setup

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))

    if setup == "satellite_orbit":
        ax.set_aspect("equal")
        ax.axis("off")
        r_m = _EARTH_R + schema.orbit_height_km * 1e3
        v = _orbital_velocity(r_m)
        T = _orbital_period(r_m)

        R_draw = 1.0
        orbit_draw = R_draw * r_m / _EARTH_R
        ax.set_xlim(-orbit_draw * 1.4, orbit_draw * 1.4)
        ax.set_ylim(-orbit_draw * 1.35, orbit_draw * 1.45)

        ax.add_patch(mpatches.Circle((0, 0), R_draw, facecolor="#AED6F1",
                                     edgecolor="#1B4F72", linewidth=2.0, zorder=3))
        ax.text(0, 0, "Earth", ha="center", va="center", fontsize=11,
                fontweight="bold", color="#1B4F72", zorder=4)
        ax.add_patch(mpatches.Circle((0, 0), orbit_draw, facecolor="none",
                                     edgecolor="black", linewidth=1.4,
                                     linestyle="--", zorder=2))
        # Satellite on the orbit; velocity is TANGENT (perpendicular to the radius),
        # gravity points along the radius toward Earth — the two are at right angles.
        sat = (0.0, orbit_draw)
        ax.plot(sat[0], sat[1], "o", markersize=12, color="#C0392B", zorder=5)
        ax.annotate("", xy=(sat[0] + 0.9, sat[1]), xytext=sat,
                    arrowprops=dict(arrowstyle="-|>", color="#1E8449", lw=2.2),
                    zorder=6)
        ax.text(sat[0] + 0.95, sat[1] + 0.08, f"v = {v / 1000:.2f} km/s",
                fontsize=10, color="#1E8449", va="bottom")
        ax.annotate("", xy=(0, 0), xytext=sat,
                    arrowprops=dict(arrowstyle="-|>", color="#7B241C", lw=1.8),
                    zorder=4)
        ax.text(0.12, orbit_draw / 2, "F = GMm/r²  (toward Earth)", fontsize=9.5,
                color="#7B241C", va="center")
        notes = []
        if schema.show_orbital_velocity:
            notes.append(f"v = √(GM/r) = {v / 1000:.2f} km/s   (r = R + h = "
                         f"{r_m / 1e3:.0f} km)")
        if schema.show_period:
            notes.append(f"T = 2π√(r³/GM) = {T / 60:.1f} min   — a higher orbit is "
                         f"slower and takes longer.")
        title = schema.title or f"Satellite in Circular Orbit (h = {schema.orbit_height_km:g} km)"

    elif setup == "kepler_ellipse":
        ax.set_aspect("equal")
        ax.axis("off")
        e = schema.eccentricity
        a = 1.0
        b = a * math.sqrt(1.0 - e ** 2)
        c = a * e                                  # centre-to-focus distance

        theta = np.linspace(0, 2 * np.pi, 400)
        ex = a * np.cos(theta)                     # centred at origin
        ey = b * np.sin(theta)
        ax.plot(ex, ey, color="#1B4F72", linewidth=2.2, zorder=3)
        ax.set_xlim(-a * 1.5, a * 1.5)
        ax.set_ylim(-b * 1.9, b * 1.9)

        # The Sun sits at a FOCUS (+c, 0), never at the centre. The empty focus is
        # marked too so the offset is unmistakable.
        sun = (c, 0.0)
        ax.plot(*sun, "o", markersize=16, color="#F39C12",
                markeredgecolor="#B9770E", markeredgewidth=1.5, zorder=6)
        ax.text(sun[0], sun[1] - 0.16, schema.star_name, ha="center", va="top",
                fontsize=11, fontweight="bold", color="#B9770E")
        ax.plot(-c, 0.0, "x", markersize=9, color="gray", zorder=5)
        ax.text(-c, -0.08, "(empty focus)", ha="center", va="top", fontsize=8,
                color="gray")
        ax.plot(0, 0, "+", markersize=10, color="gray", zorder=5)
        ax.text(0, 0.10, "centre", ha="center", va="bottom", fontsize=8, color="gray")

        if schema.show_equal_areas:
            # Two equal-TIME arcs (equal Δ mean-anomaly) — one at perihelion, one at
            # aphelion. Kepler's 2nd law makes the swept areas equal, though the
            # perihelion arc spans a far larger angle: the planet moves faster there.
            dM = 0.55
            for M0, colour in ((0.0, "#C0392B"), (math.pi, "#1E8449")):
                Ms = np.linspace(M0 - dM, M0 + dM, 40)
                Es = np.array([_solve_kepler(float(m), e) for m in Ms])
                px = a * np.cos(Es) - c        # position relative to the Sun-focus
                py = b * np.sin(Es)
                verts_x = np.concatenate([[sun[0]], px + c, [sun[0]]])
                verts_y = np.concatenate([[sun[1]], py, [sun[1]]])
                ax.fill(verts_x, verts_y, facecolor=colour, alpha=0.35,
                        edgecolor=colour, linewidth=1.2, zorder=4)
            ax.text(c + 0.02, -b * 1.35, "equal areas are swept in equal times\n"
                    "(fast at perihelion, slow at aphelion)", ha="center", va="top",
                    fontsize=9.5, color="#7B241C")
            ax.plot([sun[0], a - c], [0, 0], color="#C0392B", linewidth=0.8,
                    linestyle=":", zorder=3)
            ax.text(a - c, 0.12, "perihelion", ha="right", va="bottom", fontsize=8.5,
                    color="#C0392B")
            ax.text(-a, 0.12, "aphelion", ha="left", va="bottom", fontsize=8.5,
                    color="#1E8449")

        notes = [f"Ellipse with the {schema.star_name} at one focus (e = {e:g}).",
                 "The other focus is empty — the orbit is NOT centred on the Sun."]
        title = schema.title or f"Kepler's First & Second Laws — {schema.planet_name}"

    elif setup == "g_variation":
        rf = schema.max_radius_factor
        r = np.linspace(0.0, rf * _EARTH_R, 600)
        g = np.array([_g_at_radius(float(rr)) for rr in r])
        x = r / _EARTH_R                           # in units of R_E
        ax.plot(x[x <= 1.0], g[x <= 1.0], color="#C0392B", linewidth=2.6,
                zorder=5, label="inside:  g = g_s·(r/R)")
        ax.plot(x[x >= 1.0], g[x >= 1.0], color="#1B4F72", linewidth=2.6,
                zorder=5, label="outside: g = g_s·(R/r)²")
        ax.set_xlim(0, rf)
        ax.set_ylim(0, _G_SURFACE * 1.18)

        if schema.show_surface_marker:
            ax.axvline(1.0, color="gray", linestyle="--", linewidth=1.0, zorder=2)
            ax.plot(1.0, _G_SURFACE, "o", markersize=8, color="black", zorder=6)
            ax.annotate(f"surface: g = g_s = {_G_SURFACE:.2f} m/s²  (maximum)",
                        xy=(1.0, _G_SURFACE), xytext=(1.15, _G_SURFACE * 1.02),
                        fontsize=9.5, color="black",
                        arrowprops=dict(arrowstyle="->", lw=1.0))
            ax.text(1.0, -_G_SURFACE * 0.06, "R", ha="center", va="top", fontsize=10,
                    color="gray")
        ax.legend(fontsize=9.5, loc="upper right", framealpha=0.9)
        ax.set_xlabel("Distance from centre  r / R", fontsize=11)
        ax.set_ylabel("g  (m/s²)", fontsize=11)
        ax.grid(True, color="#eeeeee", linestyle="--", linewidth=0.7, zorder=1)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        notes = ["g rises linearly from 0 at the centre to g_s at the surface, then "
                 "falls as 1/r². Both branches meet at r = R — g is continuous there."]
        ax.text(0.5, -0.16, "\n".join(notes), transform=ax.transAxes, ha="center",
                va="top", fontsize=9.5, color="#1B4F72", linespacing=1.6,
                bbox=dict(boxstyle="round,pad=0.5", facecolor="#FEF9E7",
                          edgecolor="#B9770E"))
        ax.set_title(schema.title or "Variation of g with Distance from Earth's Centre",
                     fontsize=13, fontweight="bold")
        fig.tight_layout(rect=(0, 0.12, 1, 1))
        return _fig_to_svg_phys(fig)

    else:   # field_lines
        ax.set_aspect("equal")
        ax.axis("off")
        R_draw = 1.0
        reach = 3.2
        ax.set_xlim(-reach, reach)
        ax.set_ylim(-reach, reach)
        ax.add_patch(mpatches.Circle((0, 0), R_draw, facecolor="#AED6F1",
                                     edgecolor="#1B4F72", linewidth=2.0, zorder=4))
        ax.text(0, 0, "M", ha="center", va="center", fontsize=13, fontweight="bold",
                color="#1B4F72", zorder=5)
        # Gravity is ATTRACTIVE: field lines point radially INWARD, toward the mass.
        for k in range(schema.num_field_lines):
            ang = 2 * math.pi * k / schema.num_field_lines
            ox, oy = math.cos(ang), math.sin(ang)
            ax.annotate("", xy=(ox * (R_draw + 0.08), oy * (R_draw + 0.08)),
                        xytext=(ox * reach * 0.95, oy * reach * 0.95),
                        arrowprops=dict(arrowstyle="-|>", color="#7B241C", lw=1.4),
                        zorder=3)
        if schema.show_equipotentials:
            for rr in (1.6, 2.2, 2.8):
                ax.add_patch(mpatches.Circle((0, 0), rr, facecolor="none",
                                             edgecolor="gray", linewidth=0.9,
                                             linestyle=":", zorder=2))
            ax.text(0, 2.8, "equipotential surfaces (perpendicular to field)",
                    ha="center", va="bottom", fontsize=8.5, color="gray")
        notes = ["Field lines point INWARD — gravity is always attractive.",
                 "They are perpendicular to the equipotential surfaces everywhere."]
        title = schema.title or "Gravitational Field of a Point Mass / Sphere"

    if setup in ("satellite_orbit", "kepler_ellipse", "field_lines"):
        ax.text(0.5, 0.005, "\n".join(notes), transform=fig.transFigure, ha="center",
                va="bottom", fontsize=9.5, color="#1B4F72", linespacing=1.5)
        ax.set_title(title, fontsize=13, fontweight="bold")
        fig.tight_layout(rect=(0, 0.07, 1, 1))
    return _fig_to_svg_phys(fig)


# ── Radioactive Decay ─────────────────────────────────────────────────────────

def _decay_constant(half_life: float) -> float:
    """λ = ln2 / T½ — derived, never taken from a parameter."""
    return math.log(2.0) / half_life


def _amount_after(n0: float, half_life: float, t: "np.ndarray") -> "np.ndarray":
    """N(t) = N₀·e^(−λt) = N₀·(½)^(t/T½). Halves every T½ exactly."""
    return n0 * np.exp(-_decay_constant(half_life) * t)


# On an N-vs-Z chart each decay is a FIXED step. Alpha sheds a ²He nucleus
# (Z−2, N−2); β⁻ turns a neutron into a proton (Z+1, N−1); β⁺ the reverse
# (Z−1, N+1); γ moves nothing. Getting a sign wrong sends the chain the wrong way.
_DECAY_DZ_DN = {
    "alpha": (-2, -2),
    "beta_minus": (+1, -1),
    "beta_plus": (-1, +1),
    "gamma": (0, 0),
}


def _decay_chain_positions(z0: int, a0: int,
                           chain: List[Any]) -> List[Tuple[int, int, str]]:
    """(Z, N, decay-type) after each step, starting from the parent.

    N = A − Z is tracked, not A, because the N-vs-Z chart is what the question is
    drawn on and the α/β directions only look right in those coordinates.
    """
    z, n = z0, a0 - z0
    pts = [(z, n, "start")]
    for step in chain:
        dz, dn = _DECAY_DZ_DN[step.type]
        z, n = z + dz, n + dn
        pts.append((z, n, step.type))
    return pts


def render_radioactive_decay(data: Dict[str, Any], canvas_w: int = 800,
                             canvas_h: int = 600) -> str:
    from diagrams.schemas.physics import RadioactiveDecaySchema
    schema = RadioactiveDecaySchema(**data)

    lam = _decay_constant(schema.half_life)
    Th = schema.half_life
    n0 = schema.initial_amount

    panels = 1 + (1 if schema.show_semi_log else 0) + (1 if schema.show_decay_chain else 0)
    fig, axes = plt.subplots(1, panels, figsize=(canvas_w / 100, canvas_h / 100),
                             squeeze=False)
    axs = list(axes[0])
    ai = 0

    # Panel 1: N vs t
    ax = axs[ai]; ai += 1
    t = np.linspace(0.0, schema.num_half_lives * Th, 600)
    N = _amount_after(n0, Th, t)
    ax.plot(t, N, color="#1B4F72", linewidth=2.6, zorder=5)
    ax.set_xlim(0, t[-1])
    ax.set_ylim(0, n0 * 1.08)
    if schema.show_half_life_markers:
        for k in range(1, schema.num_half_lives + 1):
            tk = k * Th
            nk = n0 / (2 ** k)
            ax.plot([tk, tk], [0, nk], color="gray", linestyle="--", linewidth=0.9,
                    zorder=2)
            ax.plot([0, tk], [nk, nk], color="gray", linestyle="--", linewidth=0.9,
                    zorder=2)
            ax.plot(tk, nk, "o", markersize=6, color="#C0392B", zorder=6)
            frac = "N₀/2" if k == 1 else f"N₀/{2 ** k}"
            ax.annotate(frac, xy=(tk, nk), xytext=(8, 8),
                        textcoords="offset points", fontsize=9, color="#C0392B")
    ax.set_xlabel(f"Time  t ({schema.half_life_unit})", fontsize=11)
    ax.set_ylabel("Number of undecayed nuclei  N", fontsize=11)
    ax.grid(True, color="#eeeeee", linestyle="--", linewidth=0.7, zorder=1)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_title("N = N₀ e^(−λt)", fontsize=11, loc="left", color="#1B4F72")
    if schema.show_decay_constant:
        ax.text(0.96, 0.92, f"λ = ln2/T½ = {lam:.4g} /{schema.half_life_unit}\n"
                f"T½ = {Th:g} {schema.half_life_unit}", transform=ax.transAxes,
                ha="right", va="top", fontsize=9.5, color="#7B241C",
                bbox=dict(boxstyle="round,pad=0.35", facecolor="#FEF9E7",
                          edgecolor="#B9770E"))

    # Panel 2: semi-log (straight line, slope −λ)
    if schema.show_semi_log:
        ax = axs[ai]; ai += 1
        ax.plot(t, np.log(N), color="#1E8449", linewidth=2.6, zorder=5)
        ax.set_xlim(0, t[-1])
        ax.set_xlabel(f"Time  t ({schema.half_life_unit})", fontsize=11)
        ax.set_ylabel("ln N", fontsize=11)
        ax.grid(True, color="#eeeeee", linestyle="--", linewidth=0.7, zorder=1)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.set_title(f"ln N = ln N₀ − λt   (straight line, slope −λ = {-lam:.4g})",
                     fontsize=10, loc="left", color="#1E8449")

    # Panel 3: decay chain on an N-vs-Z chart
    if schema.show_decay_chain:
        ax = axs[ai]; ai += 1
        pts = _decay_chain_positions(schema.parent_z, schema.parent_a, schema.chain)
        zs = [p[0] for p in pts]
        ns = [p[1] for p in pts]
        for i in range(len(pts) - 1):
            z1, n1, _ = pts[i]
            z2, n2, kind = pts[i + 1]
            colour = {"alpha": "#C0392B", "beta_minus": "#1B4F72",
                      "beta_plus": "#7D3C98", "gamma": "gray"}[kind]
            ax.annotate("", xy=(z2, n2), xytext=(z1, n1),
                        arrowprops=dict(arrowstyle="-|>", color=colour, lw=2.0),
                        zorder=4)
            sym = {"alpha": "α", "beta_minus": "β⁻", "beta_plus": "β⁺",
                   "gamma": "γ"}[kind]
            ax.text((z1 + z2) / 2, (n1 + n2) / 2, f" {sym}", fontsize=10,
                    color=colour, fontweight="bold", zorder=5)
        ax.plot(zs, ns, "o", markersize=7, color="black", zorder=6)
        ax.plot(zs[0], ns[0], "o", markersize=9, color="#F39C12", zorder=7)
        ax.text(zs[0], ns[0] + 0.4, f"{schema.parent_a}{schema.parent_symbol}",
                ha="center", va="bottom", fontsize=9, fontweight="bold")
        pad_z = max(2, (max(zs) - min(zs)))
        pad_n = max(2, (max(ns) - min(ns)))
        ax.set_xlim(min(zs) - 1.5, max(zs) + 1.5)
        ax.set_ylim(min(ns) - 1.5, max(ns) + 1.5)
        ax.set_xlabel("Proton number  Z", fontsize=11)
        ax.set_ylabel("Neutron number  N = A − Z", fontsize=11)
        ax.grid(True, color="#eeeeee", linestyle="--", linewidth=0.7, zorder=1)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.set_title("Decay chain:  α : (Z−2, N−2),   β⁻ : (Z+1, N−1)",
                     fontsize=9.5, loc="left", color="#1B4F72")

    fig.suptitle(schema.title or f"Radioactive Decay of {schema.parent_symbol}",
                 fontsize=13, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    return _fig_to_svg_phys(fig)


# ── Wave Optics: Huygens Wavefronts ───────────────────────────────────────────

def _snell_refraction_angle(theta1_deg: float, n1: float, n2: float) -> float:
    """θ₂ from n₁sinθ₁ = n₂sinθ₂ (degrees).

    Into a denser medium (n₂ > n₁) the ray bends TOWARD the normal (θ₂ < θ₁); the
    wavelet radii there are smaller because v = c/n is slower. Clamped at grazing
    for the (rare) rarer-medium case so the figure never asks for arcsin > 1.
    """
    s = n1 * math.sin(math.radians(theta1_deg)) / n2
    s = max(-1.0, min(1.0, s))
    return math.degrees(math.asin(s))


def render_wavefront(data: Dict[str, Any], canvas_w: int = 800,
                     canvas_h: int = 600) -> str:
    from diagrams.schemas.physics import WavefrontSchema
    schema = WavefrontSchema(**data)

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))
    ax.set_aspect("equal")
    ax.axis("off")
    wt = schema.wavefront_type
    ph = schema.phenomenon
    notes: List[str] = []

    if ph == "propagation":
        ax.set_xlim(-1, 11)
        ax.set_ylim(-1, 11)
        if wt == "plane":
            # Parallel straight wavefronts; secondary wavelets on one of them; the
            # NEXT wavefront is the tangent envelope of those wavelets.
            spacing = 1.8
            xs = [1.5 + i * spacing for i in range(schema.num_wavefronts)]
            for x in xs:
                ax.plot([x, x], [1.5, 9.0], color="#1B4F72", linewidth=2.0, zorder=3)
            src_x = xs[-2] if len(xs) >= 2 else xs[0]
            for y in np.linspace(2.2, 8.3, 6):
                ax.add_patch(mpatches.Arc((src_x, y), 2 * spacing, 2 * spacing,
                                          angle=0, theta1=-70, theta2=70,
                                          color="#5DADE2", linewidth=1.0, zorder=2))
                ax.plot(src_x, y, ".", markersize=4, color="#5DADE2", zorder=2)
            ax.text(src_x + spacing, 9.5, "new wavefront = envelope of wavelets",
                    ha="center", fontsize=9, color="#1E8449")
            if schema.show_rays:
                for y in (3.0, 5.5, 8.0):
                    ax.annotate("", xy=(xs[-1] + 1.2, y), xytext=(xs[0] - 0.8, y),
                                arrowprops=dict(arrowstyle="-|>", color="#C0392B",
                                                lw=1.2), zorder=1)
            notes = ["Plane wavefront: each point is a source of secondary wavelets; "
                     "their common tangent is the wavefront an instant later."]
            title = "Huygens' Principle — Plane Wavefront"
        else:
            # spherical / cylindrical: concentric arcs from a source (a point for a
            # sphere, drawn identically in this cross-section for a cylinder).
            src = (1.2, 5.0)
            ax.plot(*src, "o", markersize=9, color="#C0392B", zorder=5)
            ax.text(src[0], src[1] - 0.5, "source", ha="center", va="top",
                    fontsize=9, color="#C0392B")
            radii = [1.6 + i * 1.6 for i in range(schema.num_wavefronts)]
            for r in radii:
                ax.add_patch(mpatches.Arc(src, 2 * r, 2 * r, angle=0,
                                          theta1=-62, theta2=62,
                                          color="#1B4F72", linewidth=2.0, zorder=3))
            r_w = radii[-2] if len(radii) >= 2 else radii[0]
            for ang in np.linspace(-52, 52, 6):
                cx = src[0] + r_w * math.cos(math.radians(ang))
                cy = src[1] + r_w * math.sin(math.radians(ang))
                ax.add_patch(mpatches.Circle((cx, cy), 1.6, facecolor="none",
                                             edgecolor="#5DADE2", linewidth=0.9,
                                             zorder=2))
            if schema.show_rays:
                for ang in (-40, 0, 40):
                    ex = src[0] + (radii[-1] + 1.2) * math.cos(math.radians(ang))
                    ey = src[1] + (radii[-1] + 1.2) * math.sin(math.radians(ang))
                    ax.annotate("", xy=(ex, ey), xytext=src,
                                arrowprops=dict(arrowstyle="-|>", color="#C0392B",
                                                lw=1.0), zorder=1)
            kind = "Spherical" if wt == "spherical" else "Cylindrical"
            notes = [f"{kind} wavefront: far from the source the arcs flatten toward "
                     f"plane wavefronts."]
            title = f"Huygens' Principle — {kind} Wavefront"

    elif ph == "reflection":
        ax.set_xlim(-1, 11)
        ax.set_ylim(-0.5, 9)
        ax.plot([0, 10], [1.0, 1.0], color="black", linewidth=3.0, zorder=4)
        for hx in np.arange(0.3, 10, 0.7):
            ax.plot([hx, hx - 0.4], [1.0, 0.6], color="black", linewidth=0.8, zorder=4)
        ax.text(9.7, 0.7, "mirror", ha="right", va="top", fontsize=9)
        ang = math.radians(schema.incidence_angle)
        # Incident and reflected wavefronts make EQUAL angles with the surface —
        # the wavelet from the first-arriving point has expanded to exactly the
        # distance the far edge still had to travel.
        for off in (0.0, 1.4, 2.8):
            ax.plot([2.0 + off, 4.6 + off], [8.0, 8.0 - 2.6 * math.tan(ang)],
                    color="#1B4F72", linewidth=1.8, zorder=3)
            ax.plot([5.4 + off, 8.0 + off], [8.0 - 2.6 * math.tan(ang), 8.0],
                    color="#1E8449", linewidth=1.8, zorder=3)
        if schema.show_rays:
            ax.annotate("", xy=(5.0, 1.0), xytext=(2.2, 8.4),
                        arrowprops=dict(arrowstyle="-|>", color="#C0392B", lw=1.4))
            ax.annotate("", xy=(7.8, 8.4), xytext=(5.0, 1.0),
                        arrowprops=dict(arrowstyle="-|>", color="#C0392B", lw=1.4))
            ax.plot([5.0, 5.0], [1.0, 5.0], color="gray", linestyle="--",
                    linewidth=1.0)
            ax.text(4.7, 4.6, "normal", ha="right", fontsize=8.5, color="gray")
            ax.text(3.7, 3.0, "i", fontsize=11, color="#C0392B")
            ax.text(6.1, 3.0, "r", fontsize=11, color="#C0392B")
        notes = ["Angle of incidence = angle of reflection: the reflected wavefront "
                 "leaves at the same angle the incident one arrived."]
        title = "Huygens' Construction — Reflection"

    elif ph == "refraction":
        theta1 = schema.incidence_angle
        theta2 = _snell_refraction_angle(theta1, schema.n1, schema.n2)
        denser_below = schema.n2 > schema.n1
        ax.set_xlim(-1, 11)
        ax.set_ylim(-5, 5)
        ax.axhline(0, color="black", linewidth=2.4, zorder=4)
        ax.fill_between([-1, 11], 0, 5, color="#EAF2F8", zorder=0)
        ax.fill_between([-1, 11], -5, 0,
                        color="#AED6F1" if denser_below else "#FEF9E7", zorder=0)
        ax.text(0.2, 4.4, f"medium 1:  n₁ = {schema.n1:g}", fontsize=10,
                color="#1B4F72")
        ax.text(0.2, -4.6, f"medium 2:  n₂ = {schema.n2:g}"
                f"  ({'denser — slower' if denser_below else 'rarer — faster'})",
                fontsize=10, color="#1B4F72", va="bottom")

        t1 = math.radians(theta1)
        t2 = math.radians(theta2)
        hit = (5.0, 0.0)
        # Incident ray toward the normal by θ₁; refracted ray by θ₂ on the far side.
        inc_start = (hit[0] - 4.0 * math.sin(t1), hit[1] + 4.0 * math.cos(t1))
        ax.annotate("", xy=hit, xytext=inc_start,
                    arrowprops=dict(arrowstyle="-|>", color="#C0392B", lw=1.6),
                    zorder=5)
        ref_end = (hit[0] + 4.0 * math.sin(t2), hit[1] - 4.0 * math.cos(t2))
        ax.annotate("", xy=ref_end, xytext=hit,
                    arrowprops=dict(arrowstyle="-|>", color="#C0392B", lw=1.6),
                    zorder=5)
        ax.plot([hit[0], hit[0]], [-3.5, 3.5], color="gray", linestyle="--",
                linewidth=1.0, zorder=3)
        ax.text(hit[0] + 0.1, 3.4, "normal", fontsize=8.5, color="gray")

        # Secondary wavelet in medium 2 has radius ∝ v₂ ∝ 1/n₂ — SMALLER in the
        # denser medium — while the incident edge still travels ∝ 1/n₁. That size
        # difference is exactly what bends the refracted wavefront toward the normal.
        r2 = 1.6 * schema.n1 / schema.n2
        wl_c = (hit[0] - 1.7, 0.0)
        ax.add_patch(mpatches.Arc(wl_c, 2 * r2, 2 * r2, angle=0, theta1=180, theta2=360,
                                  color="#1E8449", linewidth=1.4, zorder=3))
        wl_txt = ("r₂ = v₂t  (smaller,\nas v₂ is slower in medium 2)" if denser_below
                  else "r₂ = v₂t  (larger,\nas v₂ is faster in medium 2)")
        ax.text(wl_c[0], -r2 - 0.35, wl_txt, ha="center", va="top", fontsize=8.5,
                color="#1E8449")
        ax.annotate(f"θ₁ = {theta1:.0f}°", xy=(hit[0] - 1.1, 1.7), fontsize=10,
                    color="#C0392B")
        ax.annotate(f"θ₂ = {theta2:.0f}°", xy=(hit[0] + 0.3, -1.9), fontsize=10,
                    color="#C0392B")
        bend = "toward" if denser_below else "away from"
        notes = [f"Snell:  n₁ sinθ₁ = n₂ sinθ₂  gives  θ₂ = {theta2:.1f}°.  "
                 f"The ray bends {bend} the normal; wavelets are "
                 f"{'smaller' if denser_below else 'larger'} in medium 2."]
        title = "Huygens' Construction — Refraction"

    else:   # diffraction
        ax.set_xlim(-1, 11)
        ax.set_ylim(-1, 11)
        # A barrier with a slit; plane wavefronts arrive from the left, and beyond the
        # slit each slit-point radiates circular wavelets that spread into the shadow.
        slit_x = 4.5
        half = 1.3 / max(schema.slit_width_ratio, 0.4)
        half = min(half, 3.0)
        ax.add_patch(mpatches.Rectangle((slit_x - 0.15, 5.0 + half), 0.3, 5.4,
                                        facecolor="#5D6D7E", edgecolor="black",
                                        zorder=4))
        ax.add_patch(mpatches.Rectangle((slit_x - 0.15, -0.4), 0.3, 5.4 - half,
                                        facecolor="#5D6D7E", edgecolor="black",
                                        zorder=4))
        for x in np.arange(0.6, slit_x - 0.4, 1.1):
            ax.plot([x, x], [1.0, 9.0], color="#1B4F72", linewidth=1.6, zorder=2)
        if schema.show_rays:
            for y in (3.0, 5.0, 7.0):
                ax.annotate("", xy=(slit_x - 0.4, y), xytext=(0.3, y),
                            arrowprops=dict(arrowstyle="-|>", color="#C0392B",
                                            lw=1.0), zorder=1)
        for r in (1.1, 2.2, 3.3, 4.4):
            ax.add_patch(mpatches.Arc((slit_x, 5.0), 2 * r, 2 * r, angle=0,
                                      theta1=-88, theta2=88,
                                      color="#1E8449", linewidth=1.6, zorder=3))
        ax.plot(slit_x, 5.0, "o", markersize=5, color="#1E8449", zorder=5)
        ax.text(slit_x + 0.35, 5.0 + half + 0.2, f"slit width a\n(a/λ = "
                f"{schema.slit_width_ratio:g})", fontsize=8.5, color="black",
                va="bottom")
        notes = ["Every point of the slit is a Huygens source; the emerging wavelets "
                 "spread into the geometric shadow. A narrower slit (smaller a/λ) "
                 "spreads more."]
        title = "Huygens' Principle — Diffraction at a Slit"

    ax.text(0.5, 0.01, "\n".join(notes), transform=fig.transFigure, ha="center",
            va="bottom", fontsize=9.5, color="#1B4F72", linespacing=1.5)
    ax.set_title(schema.title or title, fontsize=13, fontweight="bold")
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    return _fig_to_svg_phys(fig)


# ── Wave Optics: Polarisation ─────────────────────────────────────────────────

def _malus_transmitted(i0_polarised: float, theta_deg: float) -> float:
    """I = I₀·cos²θ — Malus' law.

    I₀ is the intensity of the ALREADY-polarised beam (after the first polariser),
    not the raw unpolarised beam. The ratio I/I₀ = cos²θ, so θ = 60° passes exactly
    a quarter (0.25) and θ = 90° passes nothing — the crossed-polariser result the
    question hinges on.
    """
    return i0_polarised * math.cos(math.radians(theta_deg)) ** 2


def _brewster_angle(n1: float, n2: float) -> float:
    """θ_B = arctan(n₂/n₁) (degrees).

    At this angle the reflected ray is completely polarised, and the reflected and
    refracted rays are exactly 90° apart — that right angle is the whole content of
    the Brewster figure, and it follows from tanθ_B = n₂/n₁ together with Snell.
    """
    return math.degrees(math.atan(n2 / n1))


def render_polarisation(data: Dict[str, Any], canvas_w: int = 800,
                        canvas_h: int = 600) -> str:
    from diagrams.schemas.physics import PolarisationSchema
    schema = PolarisationSchema(**data)

    if schema.show_brewster:
        theta_b = _brewster_angle(schema.n1, schema.n2)
        theta_r = 90.0 - theta_b            # refraction angle: reflected ⟂ refracted
        fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))
        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_xlim(-1, 11)
        ax.set_ylim(-5, 5)
        ax.axhline(0, color="black", linewidth=2.4, zorder=4)
        ax.fill_between([-1, 11], 0, 5, color="#EAF2F8", zorder=0)
        ax.fill_between([-1, 11], -5, 0, color="#AED6F1", zorder=0)
        ax.text(0.2, 4.4, f"medium 1:  n₁ = {schema.n1:g}", fontsize=10, color="#1B4F72")
        ax.text(0.2, -4.6, f"medium 2:  n₂ = {schema.n2:g}", fontsize=10,
                color="#1B4F72", va="bottom")

        hit = (5.0, 0.0)
        tb, tr = math.radians(theta_b), math.radians(theta_r)
        inc_start = (hit[0] - 4.0 * math.sin(tb), hit[1] + 4.0 * math.cos(tb))
        refl_end = (hit[0] + 4.0 * math.sin(tb), hit[1] + 4.0 * math.cos(tb))
        refr_end = (hit[0] + 4.0 * math.sin(tr), hit[1] - 4.0 * math.cos(tr))
        ax.annotate("", xy=hit, xytext=inc_start,
                    arrowprops=dict(arrowstyle="-|>", color="#C0392B", lw=1.8), zorder=5)
        ax.annotate("", xy=refl_end, xytext=hit,
                    arrowprops=dict(arrowstyle="-|>", color="#1E8449", lw=1.8), zorder=5)
        ax.annotate("", xy=refr_end, xytext=hit,
                    arrowprops=dict(arrowstyle="-|>", color="#7D3C98", lw=1.8), zorder=5)
        ax.plot([hit[0], hit[0]], [-3.6, 3.6], color="gray", linestyle="--",
                linewidth=1.0, zorder=3)

        # Dots on the reflected ray = vibrations ⟂ to the page → it is plane
        # polarised. The incident ray carries both (dots and dashes).
        for f in (0.35, 0.55, 0.75):
            rx = hit[0] + f * (refl_end[0] - hit[0])
            ry = hit[1] + f * (refl_end[1] - hit[1])
            ax.plot(rx, ry, "o", markersize=5, color="#1E8449", zorder=6)
        ax.text(refl_end[0] + 0.1, refl_end[1], "reflected\n(fully polarised)",
                fontsize=9, color="#1E8449", va="center")
        ax.text(refr_end[0] + 0.1, refr_end[1], "refracted", fontsize=9,
                color="#7D3C98", va="center")
        ax.text(inc_start[0] - 0.1, inc_start[1], "unpolarised", fontsize=9,
                color="#C0392B", ha="right", va="center")
        # The 90° is the angle BETWEEN the reflected and refracted rays. Reflected
        # ray points at (90−θ_B)°, refracted at (θ_r−90)°; the arc spans exactly 90°.
        a_refl = 90.0 - theta_b
        a_refr = theta_r - 90.0
        ax.add_patch(mpatches.Arc(hit, 2.4, 2.4, angle=0,
                                  theta1=a_refr, theta2=a_refl,
                                  color="black", linewidth=1.4, zorder=6))
        a_mid = math.radians((a_refr + a_refl) / 2.0)
        ax.text(hit[0] + 1.7 * math.cos(a_mid), hit[1] + 1.7 * math.sin(a_mid),
                "90°", fontsize=11, fontweight="bold", zorder=7, ha="center",
                va="center")
        ax.text(hit[0] - 1.5, 1.3, f"θ_B = {theta_b:.1f}°", fontsize=10,
                color="#C0392B")
        notes = [f"Brewster:  θ_B = arctan(n₂/n₁) = arctan({schema.n2:g}/{schema.n1:g}) "
                 f"= {theta_b:.1f}°.",
                 "At θ_B the reflected ray is 100% polarised and is exactly 90° from "
                 "the refracted ray."]
        ax.text(0.5, 0.01, "\n".join(notes), transform=fig.transFigure, ha="center",
                va="bottom", fontsize=9.5, color="#1B4F72", linespacing=1.5)
        ax.set_title(schema.title or "Polarisation by Reflection — Brewster's Angle",
                     fontsize=13, fontweight="bold")
        fig.tight_layout(rect=(0, 0.06, 1, 1))
        return _fig_to_svg_phys(fig)

    # Analyser schematic (+ optional I-vs-θ graph)
    theta = schema.analyser_angle
    i_unpol = schema.incident_intensity
    i_pol = i_unpol / 2.0                       # a polariser passes half of unpolarised
    i_out = _malus_transmitted(i_pol, theta)

    if schema.show_intensity_graph:
        fig = plt.figure(figsize=(canvas_w / 100, canvas_h / 100))
        gs = fig.add_gridspec(1, 2, width_ratios=[1.35, 1.0], wspace=0.28)
        ax = fig.add_subplot(gs[0, 0])
        gax = fig.add_subplot(gs[0, 1])
    else:
        fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))
        gax = None
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_xlim(-0.5, 12)
    ax.set_ylim(-3.5, 3.5)

    # Beam axis with the two polaroids as vertical plates carrying transmission axes.
    ax.annotate("", xy=(11.4, 0), xytext=(-0.3, 0),
                arrowprops=dict(arrowstyle="-|>", color="#888", lw=1.2), zorder=1)
    ax.text(0.4, 1.2, "unpolarised", fontsize=9, color="#C0392B", ha="center")
    # Unpolarised: vibrations in all transverse directions
    for ang in range(0, 180, 30):
        a = math.radians(ang)
        ax.plot([0.4 - 0.5 * math.cos(a), 0.4 + 0.5 * math.cos(a)],
                [-0.5 * math.sin(a), 0.5 * math.sin(a)], color="#C0392B",
                linewidth=1.0, zorder=2)

    def _plate(x, axis_deg, label, colour):
        ax.add_patch(mpatches.Rectangle((x - 0.18, -2.2), 0.36, 4.4,
                                        facecolor="#D6DBDF", edgecolor="black",
                                        linewidth=1.5, zorder=3))
        a = math.radians(axis_deg)
        # transmission-axis line drawn across the plate at its orientation
        ax.plot([x - 1.9 * math.cos(a), x + 1.9 * math.cos(a)],
                [-1.9 * math.sin(a), 1.9 * math.sin(a)], color=colour,
                linewidth=2.2, zorder=5)
        ax.text(x, 2.5, label, ha="center", fontsize=9.5, color=colour,
                fontweight="bold")

    _plate(3.2, 90, "Polariser", "#1B4F72")     # vertical transmission axis
    ax.text(5.6, 1.15, "plane\npolarised", fontsize=9, color="#1B4F72", ha="center")
    ax.plot([5.6, 5.6], [-0.9, 0.9], color="#1B4F72", linewidth=1.6, zorder=2)
    _plate(8.0, 90 - theta, "Analyser", "#C0392B")   # axis at θ to the polariser
    ax.add_patch(mpatches.Arc((8.0, 0), 1.7, 1.7, angle=0, theta1=90 - theta,
                              theta2=90, color="black", linewidth=1.2, zorder=6))
    ax.text(8.0 + 0.5, 1.15, f"θ = {theta:g}°", fontsize=10, zorder=7)
    ax.text(10.6, 0.9, f"I = {i_out:.1f}", fontsize=10, color="#7B241C",
            ha="center", fontweight="bold")

    if schema.show_malus_law:
        notes = [f"Unpolarised I = {i_unpol:g};  after polariser  I₀ = I/2 = {i_pol:g}",
                 f"Malus:  I = I₀ cos²θ = {i_pol:g}·cos²({theta:g}°) = {i_out:.2f}   "
                 f"(I/I₀ = {math.cos(math.radians(theta)) ** 2:.3f})"]
        ax.text(0.5, -0.02, "\n".join(notes), transform=ax.transAxes, ha="center",
                va="top", fontsize=9.5, color="#1B4F72", linespacing=1.6,
                bbox=dict(boxstyle="round,pad=0.5", facecolor="#FEF9E7",
                          edgecolor="#B9770E"))

    if gax is not None:
        th = np.linspace(0, 180, 361)
        gax.plot(th, i_pol * np.cos(np.radians(th)) ** 2, color="#1B4F72",
                 linewidth=2.4, zorder=4)
        gax.plot(theta, i_out, "o", markersize=7, color="#C0392B", zorder=5)
        gax.axvline(theta, color="gray", linestyle="--", linewidth=0.9)
        gax.axvline(90, color="#C0392B", linestyle=":", linewidth=1.0)
        gax.text(90, i_pol * 0.5, "  θ=90°\n  (crossed:\n  I=0)", fontsize=8,
                 color="#C0392B", va="center")
        gax.set_xlim(0, 180)
        gax.set_ylim(0, i_pol * 1.12)
        gax.set_xticks([0, 45, 90, 135, 180])
        gax.set_xlabel("Analyser angle  θ (°)", fontsize=10)
        gax.set_ylabel("Transmitted intensity  I", fontsize=10)
        gax.grid(True, color="#eeeeee", linestyle="--", linewidth=0.7)
        gax.spines["top"].set_visible(False)
        gax.spines["right"].set_visible(False)
        gax.set_title("I = I₀ cos²θ", fontsize=10, loc="left", color="#1B4F72")

    ax.set_title(schema.title or "Polarisation — Polariser & Analyser (Malus' Law)",
                 fontsize=13, fontweight="bold")
    fig.tight_layout()
    return _fig_to_svg_phys(fig)


# ── Measurement: Vernier Calipers / Screw Gauge ───────────────────────────────

def _instrument_reading(reading: float, main_step: float,
                        sub_divisions: int) -> Tuple[float, float, int]:
    """(least_count, main_scale_reading, coinciding_division) from the reading.

    least count = main_step / sub_divisions. The coinciding division is derived
    from the reading, not supplied — the diagram then draws THAT division aligned,
    so the picture and the stated reading cannot disagree (the whole point of a
    'read the instrument' question).
    """
    lc = main_step / sub_divisions
    total = int(round(reading / lc))               # reading in least-count units
    main_ticks = (total // sub_divisions) * sub_divisions
    msr = main_ticks * lc
    coincidence = total - main_ticks               # 0 … sub_divisions−1
    return lc, msr, coincidence


def render_measuring_instrument(data: Dict[str, Any], canvas_w: int = 800,
                                canvas_h: int = 600) -> str:
    from diagrams.schemas.physics import MeasuringInstrumentSchema
    schema = MeasuringInstrumentSchema(**data)

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))
    ax.set_aspect("equal")
    ax.axis("off")

    if schema.instrument == "vernier_calipers":
        msd = schema.main_scale_division              # cm per main division
        vd = schema.vernier_divisions
        lc, msr, c = _instrument_reading(schema.reading, msd, vd)
        unit = "cm"

        # One main division → 1.4 x-units on the page.
        px = 1.4 / msd
        x0 = msr - 2 * msd                            # a little scale before the 0
        vsd = msd - lc                                # n VSD span (n−1) MSD
        v0 = schema.reading                           # vernier zero sits at the reading

        ax.set_xlim((x0 - msd) * px, (v0 + (vd + 1) * vsd) * px)
        ax.set_ylim(-4.6, 3.4)

        # Main scale (fixed jaw)
        ax.plot([x0 * px, (v0 + (vd + 2) * vsd) * px], [0, 0], color="black",
                linewidth=2.0, zorder=3)
        m = 0
        while x0 + m * msd <= v0 + (vd + 1) * vsd:
            xx = (x0 + m * msd)
            ax.plot([xx * px, xx * px], [0, 0.55], color="black", linewidth=1.2,
                    zorder=3)
            # label every division in mm-style (main divisions), cm value under 10s
            val = xx
            if abs(round(val / msd) % 10) < 0.5:
                ax.text(xx * px, 0.72, f"{val:.0f}" if val == int(val) else f"{val:g}",
                        ha="center", fontsize=8, zorder=3)
            m += 1
        ax.text(x0 * px, 1.35, "main scale (cm)", fontsize=9, color="#1B4F72")

        # Vernier scale (sliding jaw), 0 at the reading; division c will line up.
        ax.plot([v0 * px, (v0 + (vd) * vsd) * px], [-0.05, -0.05], color="#1B4F72",
                linewidth=2.4, zorder=4)
        for j in range(vd + 1):
            xx = v0 + j * vsd
            hl = (j == c)
            ax.plot([xx * px, xx * px], [-0.05, -0.75], color="#C0392B" if hl else "#1B4F72",
                    linewidth=2.2 if hl else 1.1, zorder=5)
            if j % 5 == 0 or hl:
                ax.text(xx * px, -0.95, f"{j}", ha="center", fontsize=8,
                        color="#C0392B" if hl else "#1B4F72",
                        fontweight="bold" if hl else "normal", zorder=5)
        ax.text(v0 * px, -1.35, "vernier scale", fontsize=9, color="#1B4F72")

        # Highlight the coincidence: vernier division c aligns with main line (msr_index+c)
        coincide_x = (msr + c * msd)
        ax.plot([coincide_x * px, coincide_x * px], [0.55, -0.75], color="#C0392B",
                linestyle=":", linewidth=1.2, zorder=6)
        ax.annotate(f"division {c} coincides", xy=(coincide_x * px, -0.75),
                    xytext=(coincide_x * px + 0.4, -1.9), fontsize=9, color="#C0392B",
                    arrowprops=dict(arrowstyle="->", color="#C0392B", lw=1.0))

        corrected = schema.reading - schema.zero_error
        notes = [f"Least count = MSD/N = {msd:g}/{vd} = {lc:g} {unit}",
                 f"Reading = MSR + (coinciding div)×LC = {msr:g} + {c}×{lc:g} "
                 f"= {schema.reading:g} {unit}"]
        if schema.zero_error:
            notes.append(f"Corrected = reading − zero error = {schema.reading:g} − "
                         f"({schema.zero_error:g}) = {corrected:g} {unit}")
        title = schema.title or "Vernier Calipers"

    else:   # screw_gauge
        pitch = schema.pitch                          # mm per main division (½ mm)
        cd = schema.circular_divisions
        lc, msr, c = _instrument_reading(schema.reading, pitch, cd)
        unit = "mm"

        ax.set_xlim(-1.5, 12.5)
        ax.set_ylim(-5.0, 5.5)

        # Sleeve (main scale): a horizontal datum line with pitch marks above/below.
        sleeve_x0, sleeve_x1 = 0.0, 7.2
        ax.plot([sleeve_x0, sleeve_x1], [0, 0], color="black", linewidth=1.6, zorder=3)
        n_main = int(round((msr + pitch) / pitch)) + 2
        step_px = 6.0 / max(n_main, 6) * (pitch / pitch)
        # marks: mm above the line, half-mm below (classic screw gauge sleeve)
        sc = 6.0 / (msr + 3 * pitch)
        k = 0
        while k * pitch <= msr + 2 * pitch:
            xx = sleeve_x0 + k * pitch * sc
            up = (round((k * pitch) / (2 * pitch) * 2) % 2 == 0)   # whole mm vs half
            whole = abs((k * pitch) - round(k * pitch)) < 1e-9
            ax.plot([xx, xx], [0, 0.4 if whole else -0.4], color="black",
                    linewidth=1.1, zorder=3)
            if whole:
                ax.text(xx, 0.55, f"{k * pitch:.0f}", ha="center", fontsize=8, zorder=3)
            k += 1
        msr_x = sleeve_x0 + msr * sc
        ax.text(sleeve_x0, 1.4, "main scale / sleeve (mm)", fontsize=9, color="#1B4F72")
        ax.annotate("", xy=(sleeve_x1 + 0.2, 0), xytext=(sleeve_x1 - 0.6, 0),
                    arrowprops=dict(arrowstyle="-|>", color="gray", lw=1.0))
        ax.text(sleeve_x1 + 0.25, -0.35, "reference line", fontsize=8, color="gray",
                va="top")

        # Thimble (circular scale): a vertical window of divisions crossing the
        # reference line; the division AT the line is the coincidence c.
        thimble_x = 8.6
        ax.add_patch(mpatches.Rectangle((thimble_x, -4.0), 2.4, 8.0,
                                        facecolor="#EAECEE", edgecolor="black",
                                        linewidth=1.5, zorder=2))
        win = 6                                       # divisions shown each side
        for d in range(-win, win + 1):
            div = (c + d) % cd
            yy = -d * 0.62                            # increasing division downward
            hl = (d == 0)
            ax.plot([thimble_x, thimble_x + (0.9 if hl else 0.5)], [yy, yy],
                    color="#C0392B" if hl else "black",
                    linewidth=2.0 if hl else 1.0, zorder=4)
            ax.text(thimble_x + 1.15, yy, f"{div}", va="center", fontsize=8,
                    color="#C0392B" if hl else "black",
                    fontweight="bold" if hl else "normal", zorder=4)
        # Reference (index) line from the sleeve straight into the thimble at c.
        ax.plot([msr_x, thimble_x + 1.6], [0, 0], color="#C0392B", linestyle=":",
                linewidth=1.2, zorder=5)
        ax.annotate(f"division {c} on the reference line", xy=(thimble_x, 0),
                    xytext=(thimble_x - 1.0, -4.6), fontsize=9, color="#C0392B",
                    ha="center",
                    arrowprops=dict(arrowstyle="->", color="#C0392B", lw=1.0))
        ax.text(thimble_x + 0.4, 4.3, "circular scale (thimble)", fontsize=9,
                color="#1B4F72")

        corrected = schema.reading - schema.zero_error
        notes = [f"Least count = pitch/N = {pitch:g}/{cd} = {lc:g} {unit}",
                 f"Reading = MSR + (circular div)×LC = {msr:g} + {c}×{lc:g} "
                 f"= {schema.reading:g} {unit}"]
        if schema.zero_error:
            notes.append(f"Corrected = reading − zero error = {schema.reading:g} − "
                         f"({schema.zero_error:g}) = {corrected:g} {unit}")
        title = schema.title or "Screw Gauge (Micrometer)"

    if schema.show_least_count or schema.show_reading_breakdown:
        ax.text(0.5, 0.02, "\n".join(notes), transform=fig.transFigure, ha="center",
                va="bottom", fontsize=9.5, color="#1B4F72", linespacing=1.6,
                bbox=dict(boxstyle="round,pad=0.5", facecolor="#FEF9E7",
                          edgecolor="#B9770E"))
    ax.set_title(title, fontsize=13, fontweight="bold")
    fig.tight_layout(rect=(0, 0.12, 1, 1))
    return _fig_to_svg_phys(fig)


# ── Rolling Motion ────────────────────────────────────────────────────────────

def _rolling_acceleration(incline_deg: float, gravity: float, k: float) -> float:
    """a = g·sinθ / (1 + I/MR²) = g·sinθ / (1 + k).

    The bigger the shape factor k = I/MR², the more of the drive goes into spinning
    the body up rather than accelerating it, so the smaller a is. This one number
    settles every rolling race, so it is computed, never assumed.
    """
    return gravity * math.sin(math.radians(incline_deg)) / (1.0 + k)


_ROLLING_LABEL = {
    "ring": "ring", "hollow_cylinder": "hollow cylinder", "disc": "disc",
    "cylinder": "cylinder", "solid_sphere": "solid sphere", "sphere": "sphere",
    "hollow_sphere": "hollow sphere",
}


def render_rolling_motion(data: Dict[str, Any], canvas_w: int = 800,
                          canvas_h: int = 600) -> str:
    from diagrams.schemas.physics import RollingMotionSchema, ROLLING_BODY_K
    schema = RollingMotionSchema(**data)

    k = ROLLING_BODY_K[schema.body]
    theta = schema.incline_angle
    a = _rolling_acceleration(theta, schema.gravity, k)

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_xlim(-1, 12)
    ax.set_ylim(-2.5, 8.5)

    th = math.radians(theta)
    # Incline: right triangle, hypotenuse rising to the left.
    base = 10.0
    apex = (0.5, 0.6 + base * math.tan(th))
    bl = (0.5, 0.6)
    br = (0.5 + base, 0.6)
    ax.add_patch(mpatches.Polygon([apex, bl, br], closed=True, facecolor="#EAECEE",
                                  edgecolor="black", linewidth=2.0, zorder=1))
    for hx in np.linspace(1.0, base + 0.2, 22):
        ax.plot([0.5 + hx * 0 + hx, 0.5 + hx - 0.35], [0.6, 0.6 - 0.35],
                color="black", linewidth=0.7, zorder=1)
    ax.add_patch(mpatches.Arc(br, 3.0, 3.0, angle=0, theta1=180 - theta, theta2=180,
                              color="#1B4F72", linewidth=1.4, zorder=2))
    ax.text(br[0] - 2.0, br[1] + 0.35, f"θ = {theta:g}°", fontsize=11, color="#1B4F72")

    # Body: a disc rolling on the incline surface. Place its centre a bit up-slope.
    r = 1.1
    # Point on the incline surface at parameter s from the top-right foot.
    s = 5.2
    surf = lambda ss: (br[0] - ss * math.cos(th), br[1] + ss * math.sin(th))
    contact = surf(s)
    nx, ny = math.sin(th), math.cos(th)             # outward normal of the surface
    centre = (contact[0] + nx * r, contact[1] + ny * r)

    # Draw the body according to its type: ring/hollow → annulus, sphere → shaded.
    is_hollow = schema.body in ("ring", "hollow_cylinder", "hollow_sphere")
    ax.add_patch(mpatches.Circle(centre, r, facecolor="#F5B041", edgecolor="black",
                                 linewidth=2.0, zorder=4))
    if is_hollow:
        ax.add_patch(mpatches.Circle(centre, r * 0.62, facecolor="#EAECEE",
                                     edgecolor="black", linewidth=1.6, zorder=5))
    ax.plot(*centre, "o", markersize=4, color="black", zorder=6)
    ax.text(centre[0], centre[1] + r + 0.35, _ROLLING_LABEL[schema.body],
            fontsize=10, ha="center", va="bottom", color="#7B241C")

    # Down-incline unit vector = direction of motion (toward the foot at br).
    dx, dy = math.cos(th), -math.sin(th)
    if schema.show_velocity_relation:
        ax.annotate("", xy=(centre[0] + dx * 2.2, centre[1] + dy * 2.2),
                    xytext=centre,
                    arrowprops=dict(arrowstyle="-|>", color="#C0392B", lw=2.2),
                    zorder=7)
        ax.text(centre[0] + dx * 2.4, centre[1] + dy * 2.2 + 0.35,
                "v = ωR", fontsize=11, color="#C0392B", fontweight="bold", ha="left")
        # Rolling toward the foot (rightward) ⇒ CLOCKWISE spin.
        ax.add_patch(mpatches.Arc(centre, 1.5, 1.5, angle=0, theta1=35, theta2=160,
                                  color="#1B4F72", linewidth=1.6, zorder=6))
        ax.annotate("", xy=(centre[0] + 0.75 * math.cos(math.radians(35)),
                            centre[1] + 0.75 * math.sin(math.radians(35))),
                    xytext=(centre[0] + 0.75 * math.cos(math.radians(52)),
                            centre[1] + 0.75 * math.sin(math.radians(52))),
                    arrowprops=dict(arrowstyle="-|>", color="#1B4F72", lw=1.4),
                    zorder=6)
        ax.text(centre[0] - 0.5, centre[1] + 0.15, "ω", fontsize=12, color="#1B4F72",
                ha="center")

    if schema.show_friction:
        # Static friction acts UP the incline at the contact point — it supplies the
        # torque that makes the body roll instead of slide.
        ax.annotate("", xy=(contact[0] - dx * 1.5, contact[1] - dy * 1.5),
                    xytext=contact,
                    arrowprops=dict(arrowstyle="-|>", color="#1E8449", lw=2.0),
                    zorder=7)
        ax.text(contact[0] - dx * 1.7, contact[1] - dy * 1.5 + 0.1,
                "f (static)", fontsize=10, color="#1E8449", ha="right", va="center")

    if schema.show_contact_point:
        ax.plot(*contact, "o", markersize=8, color="#7D3C98", zorder=8)
        ax.annotate("contact point P:  v_P = 0\n(instantaneous axis of rotation)",
                    xy=contact, xytext=(contact[0] - 3.4, contact[1] - 1.6),
                    fontsize=9.5, color="#7D3C98", ha="left",
                    arrowprops=dict(arrowstyle="->", color="#7D3C98", lw=1.0), zorder=8)

    notes: List[str] = []
    if schema.show_acceleration:
        notes.append(f"Rolling without slipping:  v = ωR.   I = {k:g}·MR²  "
                     f"(k = I/MR² = {k:g}).")
        notes.append(f"a = g·sinθ/(1 + I/MR²) = {schema.gravity:g}·sin{theta:g}°/"
                     f"(1 + {k:g}) = {a:.2f} m/s²  — independent of M and R.")
    if schema.show_race_ranking:
        order = sorted(set(ROLLING_BODY_K.items()), key=lambda kv: kv[1])
        seen = []
        rank = []
        for name, kv in order:
            lbl = _ROLLING_LABEL[name]
            if kv not in [s for _, s in seen]:
                rank.append(f"{lbl} (k={kv:g})")
                seen.append((name, kv))
        notes.append("Race (fastest to slowest):  " + "  <  ".join(rank)
                     + "   — smallest k wins.")

    if notes:
        ax.text(0.5, 0.02, "\n".join(notes), transform=fig.transFigure, ha="center",
                va="bottom", fontsize=9.5, color="#1B4F72", linespacing=1.6,
                bbox=dict(boxstyle="round,pad=0.5", facecolor="#FEF9E7",
                          edgecolor="#B9770E"))
    ax.set_title(schema.title or f"Rolling Without Slipping — {_ROLLING_LABEL[schema.body]}",
                 fontsize=13, fontweight="bold")
    fig.tight_layout(rect=(0, 0.13 if notes else 0, 1, 1))
    return _fig_to_svg_phys(fig)


# ══════════════════════════════════════════════════════════════════════════════
# WAVE-3 EXTENSION — optics gaps, atomic, thermal, EM, oscillations, solids
# ══════════════════════════════════════════════════════════════════════════════

_HC_EV_NM = 1239.841984          # h·c in eV·nm — energy(eV) = _HC_EV_NM / λ(nm)
_H_RYDBERG_EV = 13.605693        # |E₁| of hydrogen


def _thin_lens_image(f: float, u: float) -> Tuple[float, float]:
    """Thin-lens equation 1/v − 1/u = 1/f (Cartesian: real object ⇒ u < 0).

    Returns (v, m) with m = v/u. For a diverging lens (f < 0) and any real
    object this gives v < 0 (same side ⇒ virtual), 0 < m < 1 (erect, diminished).
    """
    inv_v = 1.0 / f + 1.0 / u
    v = math.inf if abs(inv_v) < 1e-12 else 1.0 / inv_v
    m = v / u
    return v, m


def _spherical_mirror_image(f: float, u: float) -> Tuple[float, float]:
    """Mirror equation 1/v + 1/u = 1/f (Cartesian: real object ⇒ u < 0).

    Returns (v, m) with m = −v/u. For a convex mirror (f > 0) and any real object
    this gives v > 0 (behind the mirror ⇒ virtual), 0 < m < 1 (erect, diminished).
    """
    inv_v = 1.0 / f - 1.0 / u
    v = math.inf if abs(inv_v) < 1e-12 else 1.0 / inv_v
    m = -v / u
    return v, m


def _h_energy_level(n: int) -> float:
    """Hydrogen energy level Eₙ = −13.6/n² eV."""
    return -_H_RYDBERG_EV / (n * n)


def _transition_wavelength_nm(n_hi: int, n_lo: int) -> float:
    """Photon wavelength (nm) for a hydrogen transition between two levels.

    λ = hc/ΔE with ΔE = |Eₙ_hi − Eₙ_lo|. Balmer-α (3→2) ⇒ ≈ 656 nm.
    """
    dE = abs(_h_energy_level(n_hi) - _h_energy_level(n_lo))
    return _HC_EV_NM / dE


def _prism_deviation(prism_angle_deg: float, incident_deg: float,
                     n: float) -> Tuple[float, float]:
    """Total deviation δ and emergence angle e for a ray through a prism.

    δ = (i − r₁) + (e − r₂), r₂ = A − r₁, via Snell at both faces. A larger n
    ⇒ larger δ, which is exactly why violet (n_violet > n_red) deviates most.
    """
    A = math.radians(prism_angle_deg)
    i = math.radians(incident_deg)
    sin_r1 = min(1.0, max(-1.0, math.sin(i) / n))
    r1 = math.asin(sin_r1)
    r2 = A - r1
    sin_e = min(1.0, max(-1.0, n * math.sin(r2)))
    e = math.asin(sin_e)
    delta = (i - r1) + (e - r2)
    return math.degrees(delta), math.degrees(e)


def _simple_microscope_M(near_point: float, f: float) -> float:
    """Simple microscope angular magnification, image at the near point: M = 1 + D/f."""
    return 1.0 + near_point / f


def _compound_microscope_M(tube_length: float, fo: float,
                           near_point: float, fe: float) -> float:
    """Compound microscope magnifying power M = (L/f_o)·(D/f_e)."""
    return (tube_length / fo) * (near_point / fe)


def _telescope_M(fo: float, fe: float) -> float:
    """Telescope (astronomical or terrestrial) magnifying power M = f_o/f_e."""
    return fo / fe


# ── Optics: Concave (Diverging) Lens ──────────────────────────────────────────

def render_optics_concave_lens(data: Dict[str, Any], canvas_w: int = 800,
                               canvas_h: int = 600) -> str:
    from diagrams.schemas.physics import ConcaveLensSchema
    schema = ConcaveLensSchema(**data)
    dwg = _base_drawing(canvas_w, canvas_h)

    cx, cy = canvas_w / 2.0, canvas_h / 2.0
    f = schema.focal_length                 # negative
    fmag = abs(f)
    obj_h = schema.object_height

    # Image from the thin-lens equation (real object ⇒ u < 0).
    v, m = _thin_lens_image(f, -schema.object_distance)   # v < 0, 0 < m < 1
    img_h = abs(m) * obj_h

    # Pixel scale: keep the object and both foci on the canvas.
    span = max(schema.object_distance, 2.0 * fmag)
    sc = (cx - 90.0) / span
    obj_x = cx - schema.object_distance * sc
    img_x = cx + v * sc                     # v<0 ⇒ left of the lens (virtual)

    # Principal axis
    dwg.add(dwg.line(start=(20, cy), end=(canvas_w - 20, cy),
                     stroke=STROKE, stroke_width=1, stroke_dasharray="8,4"))

    # Biconcave lens outline (thin centre, thick edges)
    lens_h, lw2, bulge = 210.0, 14.0, 20.0
    ty, by = cy - lens_h / 2, cy + lens_h / 2
    path_d = (
        f"M {cx - lw2},{ty} "
        f"Q {cx - lw2 + bulge},{cy} {cx - lw2},{by} "
        f"L {cx + lw2},{by} "
        f"Q {cx + lw2 - bulge},{cy} {cx + lw2},{ty} Z"
    )
    dwg.add(dwg.path(d=path_d, stroke=STROKE, stroke_width=2.5, fill="#eaf3fb"))
    # Diverging-lens end caps (outward arrows)
    for yy in (ty, by):
        s = 12 if yy == ty else -12
        dwg.add(dwg.line(start=(cx, yy), end=(cx - 10, yy + s),
                         stroke=STROKE, stroke_width=2))
        dwg.add(dwg.line(start=(cx, yy), end=(cx + 10, yy + s),
                         stroke=STROKE, stroke_width=2))

    # Focal points (virtual foci) and 2F
    if schema.show_focal_points:
        for sign in (-1, 1):
            fx = cx + sign * fmag * sc
            dwg.add(dwg.circle(center=(fx, cy), r=4, fill=STROKE))
            _text(dwg, "F", fx, cy + 20)
            ffx = cx + sign * 2 * fmag * sc
            if 24 < ffx < canvas_w - 24:
                dwg.add(dwg.circle(center=(ffx, cy), r=3.5, fill=STROKE))
                _text(dwg, "2F", ffx, cy + 20)

    # Object (solid, erect)
    _arrow(dwg, obj_x, cy, obj_x, cy - obj_h, "")
    _text(dwg, "O", obj_x - 14, cy - obj_h / 2, anchor="end")

    obj_tip = (obj_x, cy - obj_h)
    img_tip = (img_x, cy - img_h)
    f_near = (cx - fmag * sc, cy)           # front (object-side) focal point

    if schema.show_rays:
        # Ray 1 — parallel to axis, then diverges as if from the near focal point.
        m1 = (cx, cy - obj_h)
        dwg.add(dwg.line(start=obj_tip, end=m1, stroke=STROKE, stroke_width=1.4))
        d1 = (m1[0] - f_near[0], m1[1] - f_near[1])
        L1 = math.hypot(*d1)
        far = ((canvas_w - 30) - m1[0]) / d1[0] if d1[0] else 3.0
        dwg.add(dwg.line(start=m1,
                         end=(m1[0] + d1[0] * far, m1[1] + d1[1] * far),
                         stroke=STROKE, stroke_width=1.4))
        # backward (virtual) extension to the image / near focus
        dwg.add(dwg.line(start=m1, end=f_near, stroke=STROKE, stroke_width=1,
                         stroke_dasharray="4,3"))

        # Ray 2 — straight through the optical centre, undeviated.
        d2 = (cx - obj_x, cy - obj_tip[1])
        far2 = ((canvas_w - 30) - obj_x) / d2[0] if d2[0] else 3.0
        dwg.add(dwg.line(start=obj_tip,
                         end=(obj_x + d2[0] * far2, obj_tip[1] + d2[1] * far2),
                         stroke=STROKE, stroke_width=1.4))
        # virtual backward extension of ray 2 to the image tip
        dwg.add(dwg.line(start=obj_tip, end=img_tip, stroke=STROKE,
                         stroke_width=1, stroke_dasharray="4,3"))

    # Virtual, erect, diminished image (dashed arrow, same side as object)
    if schema.show_image:
        _arrow(dwg, img_x, cy, img_x, cy - img_h, "", stroke_w=1)
        dwg.add(dwg.line(start=(img_x, cy), end=(img_x, cy - img_h),
                         stroke=STROKE, stroke_width=1.4, stroke_dasharray="5,3"))
        _text(dwg, "I", img_x - 12, cy - img_h / 2 - 2, anchor="end")

    _text(dwg, schema.title or "Diverging (concave) lens — virtual, erect, diminished image",
          cx, 34, size=15, bold=True)
    return dwg.tostring()


# ── Optics: Convex (Diverging) Mirror ─────────────────────────────────────────

def render_optics_convex_mirror(data: Dict[str, Any], canvas_w: int = 800,
                                canvas_h: int = 600) -> str:
    from diagrams.schemas.physics import ConvexMirrorSchema
    schema = ConvexMirrorSchema(**data)
    dwg = _base_drawing(canvas_w, canvas_h)

    cy = canvas_h / 2.0
    mx = canvas_w * 0.62                      # pole of the mirror
    f = schema.focal_length                   # positive (behind)
    obj_h = schema.object_height

    v, m = _spherical_mirror_image(f, -schema.object_distance)   # v>0 behind, 0<m<1
    img_h = abs(m) * obj_h

    span = max(schema.object_distance, 2.0 * f)
    sc = (mx - 70.0) / span
    obj_x = mx - schema.object_distance * sc
    img_x = mx + v * sc                       # behind mirror (right)
    f_x = mx + f * sc
    c_x = mx + 2 * f * sc

    # Principal axis
    dwg.add(dwg.line(start=(20, cy), end=(canvas_w - 20, cy),
                     stroke=STROKE, stroke_width=1, stroke_dasharray="8,4"))

    # Convex mirror arc (reflecting side faces the object → bulges left)
    mh = 230.0
    arc = (f"M {mx - 46},{cy - mh / 2} Q {mx + 34},{cy} {mx - 46},{cy + mh / 2}")
    dwg.add(dwg.path(d=arc, stroke=STROKE, stroke_width=3, fill="none"))
    arc_b = (f"M {mx - 40},{cy - mh / 2} Q {mx + 40},{cy} {mx - 40},{cy + mh / 2}")
    dwg.add(dwg.path(d=arc_b, stroke="#aaa", stroke_width=6, fill="none"))
    _text(dwg, "P", mx - 52, cy - mh / 2 - 8, anchor="end")

    if schema.show_focal_points:
        for xx, lbl in ((f_x, "F"), (c_x, "C")):
            if xx < canvas_w - 20:
                dwg.add(dwg.circle(center=(xx, cy), r=4, fill=STROKE))
                _text(dwg, lbl, xx, cy + 20)

    # Object
    _arrow(dwg, obj_x, cy, obj_x, cy - obj_h, "")
    _text(dwg, "O", obj_x - 14, cy - obj_h / 2, anchor="end")

    obj_tip = (obj_x, cy - obj_h)
    img_tip = (img_x, cy - img_h)
    pole = (mx - 46, cy)

    if schema.show_rays:
        # Ray 1 — parallel to axis, reflects as if diverging from F (behind).
        m1 = (mx - 46, cy - obj_h)
        dwg.add(dwg.line(start=obj_tip, end=m1, stroke=STROKE, stroke_width=1.4))
        d1 = (m1[0] - f_x, m1[1] - cy)        # direction away from F, back to the left
        far1 = (30 - m1[0]) / d1[0] if d1[0] else 1.0
        dwg.add(dwg.line(start=m1, end=(m1[0] + d1[0] * far1, m1[1] + d1[1] * far1),
                         stroke=STROKE, stroke_width=1.4))
        dwg.add(dwg.line(start=m1, end=(f_x, cy), stroke=STROKE, stroke_width=1,
                         stroke_dasharray="4,3"))     # virtual extension to F

        # Ray 2 — to the pole, reflects symmetrically about the axis.
        dwg.add(dwg.line(start=obj_tip, end=pole, stroke=STROKE, stroke_width=1.4))
        d2 = (pole[0] - obj_tip[0], -(pole[1] - obj_tip[1]))   # reflect: negate dy
        far2 = (30 - pole[0]) / d2[0] if d2[0] else 1.0
        dwg.add(dwg.line(start=pole, end=(pole[0] + d2[0] * far2, pole[1] + d2[1] * far2),
                         stroke=STROKE, stroke_width=1.4))
        dwg.add(dwg.line(start=pole, end=img_tip, stroke=STROKE, stroke_width=1,
                         stroke_dasharray="4,3"))     # virtual extension to image

    if schema.show_image:
        dwg.add(dwg.line(start=(img_x, cy), end=(img_x, cy - img_h),
                         stroke=STROKE, stroke_width=1.6, stroke_dasharray="5,3"))
        _text(dwg, "I", img_x + 10, cy - img_h / 2 - 2, anchor="start")

    _text(dwg, schema.title or "Diverging (convex) mirror — virtual, erect, diminished image",
          canvas_w / 2, 34, size=15, bold=True)
    return dwg.tostring()


# ── Optical Instruments ───────────────────────────────────────────────────────

def _draw_thin_lens_symbol(ax, x: float, half_h: float, color: str = "black"):
    ax.plot([x, x], [-half_h, half_h], color=color, lw=2.0, zorder=4)
    for yy, s in ((half_h, -0.12), (-half_h, 0.12)):
        ax.plot([x - 0.09, x, x + 0.09], [yy + s, yy, yy + s],
                color=color, lw=2.0, zorder=4)


def render_optical_instrument(data: Dict[str, Any], canvas_w: int = 800,
                              canvas_h: int = 600) -> str:
    from diagrams.schemas.physics import OpticalInstrumentSchema
    schema = OpticalInstrumentSchema(**data)

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))
    ax.set_aspect("equal")
    ax.axis("off")

    inst = schema.instrument
    fo, fe = schema.objective_focal_length, schema.eyepiece_focal_length
    D = schema.near_point

    ax.axhline(0, color="#888", lw=1, ls="--", zorder=1)

    if inst == "simple_microscope":
        M = _simple_microscope_M(D, fe)
        lens_x = 3.0
        _draw_thin_lens_symbol(ax, lens_x, 1.5)
        ax.text(lens_x, 1.75, "magnifier", ha="center", fontsize=9)
        # object within f (between lens and F), virtual magnified erect image far left
        obj_x, obj_h = lens_x - 0.9, 0.5
        ax.annotate("", xy=(obj_x, obj_h), xytext=(obj_x, 0),
                    arrowprops=dict(arrowstyle="-|>", color="black", lw=2))
        ax.text(obj_x, -0.25, "object", ha="center", fontsize=8)
        img_x, img_h = lens_x - 3.4, 1.35
        ax.annotate("", xy=(img_x, img_h), xytext=(img_x, 0),
                    arrowprops=dict(arrowstyle="-|>", color="#B03060", lw=2, ls="--"))
        ax.text(img_x, img_h + 0.15, "virtual\nimage", ha="center", fontsize=8,
                color="#B03060")
        for fx in (lens_x - fe, lens_x + fe):
            ax.plot(fx, 0, "ko", ms=4)
            ax.text(fx, -0.28, "F", ha="center", fontsize=8)
        if schema.show_rays:
            ax.plot([obj_x, lens_x, img_x], [obj_h, obj_h, img_h], color="#1f6", lw=1.2)
            ax.plot([obj_x, img_x], [obj_h, img_h], color="#1f6", lw=1.2)
        ax.set_xlim(img_x - 1.0, lens_x + 1.5)
        ax.set_ylim(-1.2, 2.4)
        formula = rf"$M = 1 + \dfrac{{D}}{{f_e}} = 1 + \dfrac{{{D:.0f}}}{{{fe:.1f}}} = {M:.1f}\times$"
        title = "Simple microscope (magnifying glass)"

    elif inst == "compound_microscope":
        M = _compound_microscope_M(schema.tube_length, fo, D, fe)
        xo, xe = 2.0, 6.5              # objective, eyepiece positions
        _draw_thin_lens_symbol(ax, xo, 1.4)
        _draw_thin_lens_symbol(ax, xe, 1.7)
        ax.text(xo, 1.65, "objective\n$f_o$", ha="center", fontsize=8.5)
        ax.text(xe, 1.95, "eyepiece\n$f_e$", ha="center", fontsize=8.5)
        # object just beyond f_o → real inverted magnified intermediate image
        obj_x, obj_h = xo - 0.9, 0.45
        int_x, int_h = 4.6, -1.05      # intermediate real inverted image
        fin_h = -1.75                  # final virtual, inverted, more magnified
        ax.annotate("", xy=(obj_x, obj_h), xytext=(obj_x, 0),
                    arrowprops=dict(arrowstyle="-|>", color="black", lw=2))
        ax.text(obj_x, 0.6, "object", ha="center", fontsize=8)
        ax.annotate("", xy=(int_x, int_h), xytext=(int_x, 0),
                    arrowprops=dict(arrowstyle="-|>", color="#0066B3", lw=1.8))
        ax.text(int_x + 0.15, int_h - 0.2, "intermediate\nimage", ha="left",
                va="top", fontsize=7.5, color="#0066B3")
        ax.annotate("", xy=(9.6, fin_h), xytext=(9.6, 0),
                    arrowprops=dict(arrowstyle="-|>", color="#B03060", lw=2, ls="--"))
        ax.text(9.6, fin_h - 0.2, "final image\n(virtual, inverted)", ha="center",
                va="top", fontsize=7.5, color="#B03060")
        if schema.show_rays:
            # objective forms intermediate image
            ax.plot([obj_x, xo], [obj_h, obj_h], color="#2a2", lw=1)
            ax.plot([xo, int_x], [obj_h, int_h], color="#2a2", lw=1)
            ax.plot([obj_x, xo, int_x], [obj_h, 0, int_h], color="#2a2", lw=1)
            # eyepiece re-images to the eye
            ax.plot([int_x, xe], [int_h, int_h], color="#e77", lw=1)
            ax.plot([xe, 9.6], [int_h, fin_h], color="#e77", lw=1)
        for fx, lbl in ((xo - fo, "F_o"), (xe + fe, "")):
            if fx > -1:
                ax.plot(fx, 0, "ko", ms=3.5)
        ax.set_xlim(-0.5, 10.6)
        ax.set_ylim(-2.6, 2.4)
        formula = (rf"$M = \dfrac{{L}}{{f_o}}\times\dfrac{{D}}{{f_e}} = "
                   rf"\dfrac{{{schema.tube_length:.0f}}}{{{fo:.1f}}}\times"
                   rf"\dfrac{{{D:.0f}}}{{{fe:.1f}}} = {M:.0f}\times$")
        title = "Compound microscope"

    else:   # telescopes
        M = _telescope_M(fo, fe)
        # Fixed visual spacing (a real telescope has f_o >> f_e, which would make
        # the eyepiece section vanish if drawn to scale). The M formula below uses
        # the true focal lengths regardless.
        is_terr = inst == "terrestrial_telescope"
        xo = 0.5
        xi = 5.3                       # common focal plane (intermediate image)
        xe = xi + (2.8 if is_terr else 1.8)     # eyepiece
        _draw_thin_lens_symbol(ax, xo, 1.5)
        _draw_thin_lens_symbol(ax, xe, 1.1)
        ax.text(xo, 1.75, "objective\n$f_o$", ha="center", fontsize=8.5)
        ax.text(xe, 1.35, "eyepiece\n$f_e$", ha="center", fontsize=8.5)
        ax.plot(xi, 0, "ko", ms=4)
        int_h = -0.7
        ax.annotate("", xy=(xi, int_h), xytext=(xi, 0),
                    arrowprops=dict(arrowstyle="-|>", color="#0066B3", lw=1.8))
        # parallel rays from a distant object arrive at an angle
        if schema.show_rays:
            for yy in (0.9, 0.0, -0.9):
                ax.plot([xo - 1.6, xo], [yy + 0.25, yy], color="#2a2", lw=1)
            ax.plot([xo, xi], [0.9, int_h], color="#2a2", lw=1)
            ax.plot([xo, xi], [-0.9, int_h], color="#2a2", lw=1)
            ax.plot([xo, xi], [0.0, int_h], color="#2a2", lw=1)
        erecting = ""
        if is_terr:
            xer = (xi + xe) / 2
            _draw_thin_lens_symbol(ax, xer, 0.8)
            ax.text(xer, -1.1, "erecting\nlens", ha="center", fontsize=7.5)
            erecting = "  (erect final image)"
        if schema.show_rays:
            for yy in (0.5, -0.5):
                ax.plot([xe, xe + 1.8], [int_h, int_h + (yy)], color="#e77", lw=1)
        ax.set_xlim(xo - 2.0, xe + 2.2)
        ax.set_ylim(-1.7, 2.2)
        formula = (rf"$M = \dfrac{{f_o}}{{f_e}} = \dfrac{{{fo:.0f}}}{{{fe:.0f}}} "
                   rf"= {M:.0f}\times$")
        title = ("Astronomical telescope" if inst == "astronomical_telescope"
                 else "Terrestrial telescope") + erecting

    if schema.show_magnification:
        ax.text(0.5, 0.02, formula, transform=ax.transAxes, ha="center", va="bottom",
                fontsize=12, color="#1B4F72",
                bbox=dict(boxstyle="round,pad=0.4", facecolor="#FEF9E7",
                          edgecolor="#B9770E"))
    ax.set_title(schema.title or title, fontsize=13, fontweight="bold")
    fig.tight_layout()
    return _fig_to_svg_phys(fig)


# ── Prism: Dispersion of White Light ──────────────────────────────────────────

_SPECTRUM = [
    ("R", "#E10000"), ("O", "#FF7A00"), ("Y", "#E8C500"), ("G", "#12A012"),
    ("B", "#1030E0"), ("I", "#4B0082"), ("V", "#8A00E0"),
]


def render_prism_dispersion(data: Dict[str, Any], canvas_w: int = 800,
                            canvas_h: int = 600) -> str:
    from diagrams.schemas.physics import PrismDispersionSchema
    schema = PrismDispersionSchema(**data)

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))
    ax.set_aspect("equal")
    ax.axis("off")

    A_deg = schema.prism_angle
    # Prism triangle, apex up.
    apex = np.array([0.0, 2.0])
    half = 1.7
    bl = np.array([-half, -1.4])
    br = np.array([half, -1.4])
    ax.add_patch(mpatches.Polygon([apex, bl, br], closed=True,
                                  facecolor="#dbeeff", edgecolor="black", lw=2))

    # Entry point on the left face, exit region on the right face.
    p1 = apex + 0.55 * (bl - apex)
    p2 = apex + 0.60 * (br - apex)
    # White incident ray (horizontal) to p1
    ax.plot([p1[0] - 3.2, p1[0]], [p1[1], p1[1]], color="#444", lw=2.0)
    ax.text(p1[0] - 3.2, p1[1] + 0.18, "white light", fontsize=9, color="#333")
    # Ray inside the prism (single, gray)
    ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color="#888", lw=1.6)

    # Per-colour deviation: violet (largest n) deviates most.
    n_red, n_viol = schema.n_red, schema.n_violet
    dev_red, _ = _prism_deviation(A_deg, schema.incident_angle, n_red)
    dev_viol, _ = _prism_deviation(A_deg, schema.incident_angle, n_viol)
    ncol = len(_SPECTRUM)
    # The true dispersion (δ_V − δ_R ≈ 1–2°) is too small to see; textbook figures
    # exaggerate the fan. The DRAWN angle is stretched about red's deviation, but
    # the ordering (violet most, red least) and the annotated δ values are exact.
    gain = 9.0
    if schema.show_spectrum:
        for k, (lbl, col) in enumerate(_SPECTRUM):
            n_k = n_red + (n_viol - n_red) * k / (ncol - 1)
            dev, _e = _prism_deviation(A_deg, schema.incident_angle, n_k)
            draw_dev = dev_red + gain * (dev - dev_red)
            ang = -math.radians(draw_dev)        # emergent ray bends downward
            end = p2 + 3.6 * np.array([math.cos(ang), math.sin(ang)])
            ax.plot([p2[0], end[0]], [p2[1], end[1]], color=col, lw=1.8)
            ax.text(end[0] + 0.10, end[1], lbl, color=col, fontsize=9,
                    va="center", fontweight="bold")
    else:
        n_mid = 0.5 * (n_red + n_viol)
        dev, _e = _prism_deviation(A_deg, schema.incident_angle, n_mid)
        ang = -math.radians(dev)
        end = p2 + 3.4 * np.array([math.cos(ang), math.sin(ang)])
        ax.plot([p2[0], end[0]], [p2[1], end[1]], color="#444", lw=2.0)

    ax.text(0, 2.25, f"A = {A_deg:.0f}°", ha="center", fontsize=10)
    if schema.show_angles:
        ax.text(p2[0] + 1.6, p2[1] - 0.35,
                rf"$\delta_V = {dev_viol:.1f}°>\delta_R = {dev_red:.1f}°$",
                fontsize=10, color="#1B4F72")

    ax.set_xlim(-4.6, 4.4)
    ax.set_ylim(-3.4, 2.8)
    ax.set_title(schema.title or "Dispersion of white light by a prism (VIBGYOR)",
                 fontsize=13, fontweight="bold")
    fig.tight_layout()
    return _fig_to_svg_phys(fig)


# ── Atomic Energy Level Diagram ───────────────────────────────────────────────

_SERIES_COLOR = {"lyman": "#7B00B3", "balmer": "#00A0A0", "paschen": "#C0392B",
                 "brackett": "#E67E22", "pfund": "#7F8C8D"}


def render_energy_level_diagram(data: Dict[str, Any], canvas_w: int = 800,
                                canvas_h: int = 600) -> str:
    from diagrams.schemas.physics import (
        EnergyLevelDiagramSchema, _SERIES_LANDING)
    schema = EnergyLevelDiagramSchema(**data)

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))

    # Build the levels (hydrogen derived unless supplied).
    if schema.levels:
        level_n = {}
        for lv in schema.levels:
            level_n[lv.n] = lv.energy if lv.energy is not None else _h_energy_level(lv.n)
    else:
        level_n = {n: _h_energy_level(n) for n in range(1, schema.max_level + 1)}
    max_n = max(level_n)

    x0, x1 = 0.08, 0.92
    for n, E in sorted(level_n.items()):
        ax.hlines(E, x0, x1, color="black", lw=1.6)
        ax.text(x1 + 0.01, E, f"n={n}", va="center", fontsize=9)
        ax.text(x0 - 0.01, E, f"{E:.2f} eV", va="center", ha="right",
                fontsize=8.5, color="#555")

    if schema.show_ionisation:
        ax.hlines(0.0, x0, x1, color="#555", lw=1.2, ls="--")
        ax.text(x1 + 0.01, 0.0, "n=∞ (0 eV)", va="center", fontsize=9, color="#555")
        ax.axhspan(0.0, 1.2, facecolor="#f2f2f2", zorder=0)
        ax.text((x0 + x1) / 2, 0.55, "ionisation / continuum", ha="center",
                fontsize=8.5, color="#888")

    # Assemble transitions: explicit + auto-generated per named series.
    transitions = [(t.from_n, t.to_n, t.series.strip().lower(), t.label)
                   for t in schema.transitions]
    for s in schema.show_series:
        lo = _SERIES_LANDING[s]
        for hi in range(lo + 1, min(max_n, lo + 4) + 1):
            transitions.append((hi, lo, s, ""))

    # spread arrows horizontally so they don't overlap
    slots = np.linspace(x0 + 0.10, x1 - 0.10, max(len(transitions), 1))
    for idx, (hi, lo, series, label) in enumerate(transitions):
        if hi not in level_n or lo not in level_n:
            continue
        e_hi, e_lo = level_n[hi], level_n[lo]
        col = _SERIES_COLOR.get(series, "#333333")
        xx = slots[idx]
        # emission: arrow points DOWN from the higher to the lower level
        y_from, y_to = (e_hi, e_lo) if e_hi > e_lo else (e_lo, e_hi)
        ax.annotate("", xy=(xx, y_to), xytext=(xx, y_from),
                    arrowprops=dict(arrowstyle="-|>", color=col, lw=1.5))
        if schema.show_wavelengths and schema.element.upper() == "H":
            lam = _transition_wavelength_nm(hi, lo)
            ax.text(xx + 0.006, (e_hi + e_lo) / 2, f"{lam:.0f} nm",
                    fontsize=7, color=col, rotation=90, va="center", ha="left")

    if schema.show_series:
        handles = [mpatches.Patch(color=_SERIES_COLOR[s], label=s.capitalize())
                   for s in schema.show_series]
        ax.legend(handles=handles, loc="lower right", fontsize=8, framealpha=0.9)

    ax.set_ylabel("Energy (eV)", fontsize=11)
    ax.set_xlim(0, 1)
    ax.set_xticks([])
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["bottom"].set_visible(False)
    ax.set_title(schema.title or f"Energy level diagram — {schema.element}",
                 fontsize=13, fontweight="bold")
    fig.tight_layout()
    return _fig_to_svg_phys(fig)


# ── Rutherford Alpha-particle Scattering ──────────────────────────────────────

def _rutherford_angle(impact_parameter: float, k: float) -> float:
    """Scattering angle θ (deg) from tan(θ/2) = k/b.

    Small b (near head-on) ⇒ large θ (backscatter); large b ⇒ small θ. This is
    the whole point of the experiment: rare large-angle scatters need a tiny,
    dense, positive nucleus.
    """
    b = max(abs(impact_parameter), 1e-6)
    return math.degrees(2.0 * math.atan2(k, b))


def _rutherford_trajectory(b: float, k: float, x_in: float = -5.5,
                           out_len: float = 5.0, npts: int = 60):
    """Exact repulsive-hyperbola path with the NUCLEUS AT THE FOCUS (origin).

    The orbit r(φ) = p/(e·cosφ − 1) with e = 1/sin(θ/2) is generated, rotated so
    the incoming asymptote is horizontal, and scaled so its perpendicular distance
    from the focus equals the impact parameter b. Every trajectory therefore
    genuinely bends around the same nucleus — the physics the figure must show.
    """
    theta = math.radians(_rutherford_angle(b, k))
    e = 1.0 / math.sin(theta / 2.0)
    phi0 = math.acos(min(1.0, 1.0 / e))
    phis = np.linspace(-phi0 + 0.05, phi0 - 0.05, npts)
    r = 1.0 / (e * np.cos(phis) - 1.0)                # p = 1 (scaled below)
    x, y = r * np.cos(phis), r * np.sin(phis)
    a0 = math.atan2(y[1] - y[0], x[1] - x[0])         # incoming motion direction
    c, s = math.cos(-a0), math.sin(-a0)
    xr, yr = c * x - s * y, s * x + c * y             # rotate so it enters along +x
    y_asym = yr[0]
    scale = abs(b) / abs(y_asym) if abs(y_asym) > 1e-9 else 1.0
    xr, yr = xr * scale, yr * scale
    if (yr[0] >= 0) != (b >= 0):                       # b>0 must enter above the axis
        yr = -yr
    dxo, dyo = xr[-1] - xr[-2], yr[-1] - yr[-2]
    L = math.hypot(dxo, dyo) or 1.0
    mask = xr >= x_in                                  # clip the incoming tail cleanly
    xr, yr = xr[mask], yr[mask]
    px = np.concatenate([[x_in], xr, [xr[-1] + dxo / L * out_len]])
    py = np.concatenate([[yr[0]], yr, [yr[-1] + dyo / L * out_len]])
    return px, py


def render_alpha_scattering(data: Dict[str, Any], canvas_w: int = 800,
                            canvas_h: int = 600) -> str:
    from diagrams.schemas.physics import AlphaScatteringSchema
    schema = AlphaScatteringSchema(**data)

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))
    ax.set_aspect("equal")
    ax.axis("off")

    k = schema.impact_scale
    # Symmetric spread of impact parameters; the central ray is near head-on.
    N = schema.num_particles
    bs = np.linspace(-3.0, 3.0, N)
    bs = np.where(np.abs(bs) < 0.12, np.sign(bs + 1e-9) * 0.12, bs)

    x_in = -5.5
    for b in bs:
        px, py = _rutherford_trajectory(b, k, x_in=x_in)
        ax.plot(px, py, color="#2C3E50", lw=1.1, zorder=3)
        ax.annotate("", xy=(px[-1], py[-1]), xytext=(px[-2], py[-2]),
                    arrowprops=dict(arrowstyle="-|>", color="#2C3E50", lw=1.1),
                    zorder=3)

    if schema.show_nucleus:
        ax.add_patch(plt.Circle((0, 0), 0.28, color="#D4AC0D", zorder=6))
        ax.text(0, -0.55, "gold nucleus\n(+Ze)", ha="center", va="top",
                fontsize=9, color="#7D6608")

    if schema.show_impact_parameter:
        b_demo = 1.2
        ax.plot([x_in, 0], [b_demo, b_demo], color="#888", lw=0.8, ls=":")
        ax.plot([0, 0], [0, b_demo], color="#888", lw=0.8, ls=":")
        ax.annotate("", xy=(0, b_demo), xytext=(0, 0),
                    arrowprops=dict(arrowstyle="<->", color="#888", lw=0.8))
        ax.text(0.12, b_demo / 2, "b", fontsize=10, color="#555", va="center")

    ax.text(x_in - 0.1, 3.3, r"$\alpha$ beam", fontsize=11, color="#2C3E50", ha="left")
    ax.set_xlim(x_in - 0.6, 6.5)
    ax.set_ylim(-4.0, 4.0)
    ax.set_title(schema.title or "Rutherford α-particle scattering",
                 fontsize=13, fontweight="bold")
    fig.tight_layout()
    return _fig_to_svg_phys(fig)


# ── Heat Engine / Refrigerator / Heat Pump ────────────────────────────────────

def _heat_engine_energetics(mode: str, q_hot, q_cold, work) -> Dict[str, Any]:
    """Resolve Q1, Q2, W so that Q1 = W + Q2 holds exactly, then the figure of merit.

    engine:       η   = W/Q1 = 1 − Q2/Q1
    refrigerator: COP = Q2/W
    heat pump:    COP = Q1/W = 1 + Q2/W
    """
    if mode == "engine":
        if q_hot is None:
            q_hot = 1000.0
        if q_cold is None:
            q_cold = (q_hot - work) if work is not None else 0.6 * q_hot
        work = q_hot - q_cold
        metric = ("efficiency", work / q_hot)
    else:
        if work is None:
            work = 250.0
        if q_cold is None:
            # Default to an irreversible machine whose COP stays BELOW the Carnot
            # limit for the default reservoir temperatures (COP_fridge = 1.2 < 1.5).
            q_cold = (q_hot - work) if q_hot is not None else 1.2 * work
        q_hot = q_cold + work
        metric = ("COP", (q_cold / work) if mode == "refrigerator" else (q_hot / work))
    assert abs(q_hot - (work + q_cold)) < 1e-6, "energy not conserved"
    return {"q_hot": q_hot, "q_cold": q_cold, "work": work,
            "metric_name": metric[0], "metric_value": metric[1]}


def render_heat_engine(data: Dict[str, Any], canvas_w: int = 800,
                       canvas_h: int = 600) -> str:
    from diagrams.schemas.physics import HeatEngineSchema
    schema = HeatEngineSchema(**data)
    en = _heat_engine_energetics(schema.mode, schema.q_hot, schema.q_cold, schema.work)

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))
    ax.set_aspect("equal")
    ax.axis("off")

    forward = schema.mode == "engine"    # engine: heat flows hot→cold, extracts W
    # Reservoirs
    ax.add_patch(mpatches.FancyBboxPatch((-2.6, 3.2), 5.2, 1.1,
                 boxstyle="round,pad=0.02", facecolor="#F5B7B1", edgecolor="black"))
    ax.text(0, 3.75, f"Hot reservoir  $T_1$ = {schema.t_hot:.0f} K", ha="center",
            va="center", fontsize=10)
    ax.add_patch(mpatches.FancyBboxPatch((-2.6, -4.3), 5.2, 1.1,
                 boxstyle="round,pad=0.02", facecolor="#AED6F1", edgecolor="black"))
    ax.text(0, -3.75, f"Cold reservoir  $T_2$ = {schema.t_cold:.0f} K", ha="center",
            va="center", fontsize=10)
    # Working device
    label = {"engine": "ENGINE", "refrigerator": "FRIDGE",
             "heat_pump": "HEAT\nPUMP"}[schema.mode]
    ax.add_patch(plt.Circle((0, 0), 1.15, facecolor="#FCF3CF", edgecolor="black", lw=2))
    ax.text(0, 0, label, ha="center", va="center", fontsize=11, fontweight="bold")

    def varrow(y1, y2, x, color):
        ax.annotate("", xy=(x, y2), xytext=(x, y1),
                    arrowprops=dict(arrowstyle="-|>", color=color, lw=2.5))

    if forward:
        varrow(3.2, 1.15, 0, "#C0392B")           # Q1 down into engine
        varrow(-1.15, -3.2, 0, "#2874A6")         # Q2 down into cold
        ax.annotate("", xy=(3.4, 0), xytext=(1.15, 0),
                    arrowprops=dict(arrowstyle="-|>", color="#1E8449", lw=2.5))  # W out
        ax.text(3.5, 0, f"W = {en['work']:.0f} J", ha="left", va="center",
                fontsize=10, color="#1E8449")
    else:
        varrow(1.15, 3.2, 0, "#C0392B")           # Q1 up to hot
        varrow(-3.2, -1.15, 0, "#2874A6")         # Q2 up from cold into device
        ax.annotate("", xy=(1.15, 0), xytext=(3.4, 0),
                    arrowprops=dict(arrowstyle="-|>", color="#1E8449", lw=2.5))  # W in
        ax.text(3.5, 0, f"W = {en['work']:.0f} J", ha="left", va="center",
                fontsize=10, color="#1E8449")

    ax.text(-0.25, 2.2, f"$Q_1$ = {en['q_hot']:.0f} J", ha="right", va="center",
            fontsize=10, color="#C0392B")
    ax.text(-0.25, -2.2, f"$Q_2$ = {en['q_cold']:.0f} J", ha="right", va="center",
            fontsize=10, color="#2874A6")

    # Figure of merit + Carnot limit
    if en["metric_name"] == "efficiency":
        txt = (rf"$\eta = 1 - \dfrac{{Q_2}}{{Q_1}} = "
               rf"{en['metric_value']*100:.0f}\%$")
        carnot = 1.0 - schema.t_cold / schema.t_hot
        climit = rf"Carnot limit  $\eta = 1 - T_2/T_1 = {carnot*100:.0f}\%$"
    else:
        if schema.mode == "refrigerator":
            txt = rf"$COP = \dfrac{{Q_2}}{{W}} = {en['metric_value']:.1f}$"
            carnot = schema.t_cold / (schema.t_hot - schema.t_cold)
        else:
            txt = rf"$COP = \dfrac{{Q_1}}{{W}} = {en['metric_value']:.1f}$"
            carnot = schema.t_hot / (schema.t_hot - schema.t_cold)
        climit = rf"Carnot limit  $COP = {carnot:.1f}$"
    ax.text(-3.7, 0.5, txt, ha="left", va="center", fontsize=12, color="#1B4F72")
    if schema.show_carnot_limit:
        ax.text(-3.7, -0.5, climit, ha="left", va="center", fontsize=9, color="#666")

    ax.set_xlim(-4.0, 5.6)
    ax.set_ylim(-4.6, 4.6)
    ax.set_title(schema.title or f"{schema.mode.replace('_', ' ').title()} "
                 "(energy flow, $Q_1 = W + Q_2$)", fontsize=13, fontweight="bold")
    fig.tight_layout()
    return _fig_to_svg_phys(fig)


# ── Thermal Conduction ────────────────────────────────────────────────────────

def _series_interface_temps(layers, t_hot: float, t_cold: float):
    """Heat current H and the interface temperatures of slabs in SERIES.

    In steady state the SAME H flows through every slab (nothing accumulates), so
    the drop across slab i is H·Rᵢ with Rᵢ = Lᵢ/(kᵢAᵢ). Interface temperatures
    follow from that equal-H condition — the classic composite-slab result.
    """
    R = [lay.length / (lay.thermal_conductivity * lay.area) for lay in layers]
    R_total = sum(R)
    H = (t_hot - t_cold) / R_total
    temps = [t_hot]
    for Ri in R:
        temps.append(temps[-1] - H * Ri)
    return H, temps, R


def render_thermal_conduction(data: Dict[str, Any], canvas_w: int = 800,
                              canvas_h: int = 600) -> str:
    from diagrams.schemas.physics import ThermalConductionSchema, ConductionLayer
    schema = ThermalConductionSchema(**data)
    layers = schema.layers or [
        ConductionLayer(material="A", length=0.1, thermal_conductivity=50.0, area=1.0),
        ConductionLayer(material="B", length=0.2, thermal_conductivity=10.0, area=1.0),
    ]
    if schema.arrangement == "single":
        layers = layers[:1]

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))
    ax.axis("off")

    colors = ["#F5CBA7", "#AED6F1", "#A9DFBF", "#F9E79F", "#D7BDE2"]

    if schema.arrangement == "parallel":
        # Same ΔT across each slab; H_j = k_j A_j ΔT / L_j; total H = Σ H_j.
        dT = schema.t_hot - schema.t_cold
        Hs = [lay.thermal_conductivity * lay.area * dT / lay.length for lay in layers]
        H_total = sum(Hs)
        n = len(layers)
        slab_w = 3.0
        y = 0.0
        band_h = 4.0 / n
        for i, lay in enumerate(layers):
            yy = 4.0 - (i + 1) * band_h
            ax.add_patch(mpatches.Rectangle((0, yy), slab_w, band_h * 0.92,
                         facecolor=colors[i % len(colors)], edgecolor="black"))
            ax.text(slab_w / 2, yy + band_h * 0.46,
                    f"{lay.material or chr(65+i)}: k={lay.thermal_conductivity:g}, "
                    f"H={Hs[i]:.0f} W", ha="center", va="center", fontsize=8.5)
        ax.add_patch(mpatches.Rectangle((-0.5, 0), 0.5, 4.0, facecolor="#F5B7B1",
                     edgecolor="black"))
        ax.add_patch(mpatches.Rectangle((slab_w, 0), 0.5, 4.0, facecolor="#AED6F1",
                     edgecolor="black"))
        ax.text(-0.25, 4.2, f"{schema.t_hot:.0f}°C", ha="center", fontsize=9)
        ax.text(slab_w + 0.25, 4.2, f"{schema.t_cold:.0f}°C", ha="center", fontsize=9)
        ax.text(slab_w / 2, -0.5,
                rf"Parallel: $H = \Sigma H_i = {H_total:.0f}$ W", ha="center",
                fontsize=11, color="#1B4F72")
        ax.set_xlim(-1.2, slab_w + 1.4)
        ax.set_ylim(-1.2, 4.8)
    else:
        # Series (or single): equal H, interface temperatures derived.
        H, temps, R = _series_interface_temps(layers, schema.t_hot, schema.t_cold)
        total_L = sum(lay.length for lay in layers)
        scale = 5.0 / total_L
        x = 0.0
        ax.add_patch(mpatches.Rectangle((-0.5, 0), 0.5, 3.0, facecolor="#F5B7B1",
                     edgecolor="black"))
        ax.text(-0.25, 3.2, f"{schema.t_hot:.0f}°C", ha="center", fontsize=9,
                color="#C0392B")
        for i, lay in enumerate(layers):
            w = lay.length * scale
            ax.add_patch(mpatches.Rectangle((x, 0), w, 3.0,
                         facecolor=colors[i % len(colors)], edgecolor="black"))
            ax.text(x + w / 2, 1.5,
                    f"{lay.material or chr(65+i)}\nk={lay.thermal_conductivity:g}\n"
                    f"L={lay.length:g}", ha="center", va="center", fontsize=8.5)
            x += w
            # interface temperature (normalise −0.0 float noise to 0)
            t_disp = temps[i + 1] if abs(temps[i + 1]) >= 0.05 else 0.0
            ax.text(x, 3.2, f"{t_disp:.0f}°C", ha="center", fontsize=8.5,
                    color="#555")
        ax.add_patch(mpatches.Rectangle((x, 0), 0.5, 3.0, facecolor="#AED6F1",
                     edgecolor="black"))
        ax.annotate("", xy=(x + 1.4, 1.5), xytext=(-0.5, 1.5),
                    arrowprops=dict(arrowstyle="-|>", color="#E67E22", lw=1.5,
                                    alpha=0.35))
        ax.text((x) / 2, -0.6, rf"Series: same $H = {H:.0f}$ W through each slab",
                ha="center", fontsize=11, color="#1B4F72")
        if schema.show_temperature_gradient:
            xt = np.array([0] + list(np.cumsum([lay.length * scale for lay in layers])))
            ax.plot(xt, [3.6 + (t - schema.t_cold) / (schema.t_hot - schema.t_cold) * 1.4
                         for t in temps], "o-", color="#C0392B", lw=1.2, ms=4)
            ax.text(x + 0.6, 4.4, "T profile", fontsize=8, color="#C0392B")
        ax.set_xlim(-1.2, x + 1.6)
        ax.set_ylim(-1.2, 5.4)

    ax.set_title(schema.title or f"Thermal conduction ({schema.arrangement})",
                 fontsize=13, fontweight="bold")
    fig.tight_layout()
    return _fig_to_svg_phys(fig)


# ── Gauss's Law: Gaussian Surface ─────────────────────────────────────────────

def render_gauss_surface(data: Dict[str, Any], canvas_w: int = 800,
                         canvas_h: int = 600) -> str:
    from diagrams.schemas.physics import GaussSurfaceSchema
    schema = GaussSurfaceSchema(**data)

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))
    ax.set_aspect("equal")
    ax.axis("off")

    ct = schema.charge_type
    flux = r"$\Phi_E = q_{enc}/\varepsilon_0$"

    if ct in ("point", "shell"):
        # radial field, spherical Gaussian surface
        Rg = 2.4
        if ct == "shell":
            ax.add_patch(plt.Circle((0, 0), 1.1, fill=False, edgecolor="#C0392B",
                         lw=2))
            for a in np.linspace(0, 2 * np.pi, 20, endpoint=False):
                ax.text(1.1 * math.cos(a), 1.1 * math.sin(a), "+", color="#C0392B",
                        ha="center", va="center", fontsize=8)
            src = "charged shell"
            field = r"$E=\dfrac{q}{4\pi\varepsilon_0 r^2}$ (outside), $E=0$ inside"
        else:
            ax.add_patch(plt.Circle((0, 0), 0.16, color="#C0392B"))
            ax.text(0, -0.35, "+q", ha="center", fontsize=10, color="#C0392B")
            src = "point charge"
            field = r"$E=\dfrac{q}{4\pi\varepsilon_0 r^2}$"
        # Gaussian sphere (dashed)
        ax.add_patch(plt.Circle((0, 0), Rg, fill=False, edgecolor="#1B4F72",
                     lw=1.6, ls="--"))
        ax.text(Rg * 0.72, Rg * 0.72, "Gaussian\nsphere", fontsize=8, color="#1B4F72")
        if schema.show_field_lines:
            # A charged shell has E=0 inside, so its field lines must start at the
            # shell surface, not the centre.
            r_start = 1.15 if ct == "shell" else 0.2
            for a in np.linspace(0, 2 * np.pi, 12, endpoint=False):
                x0, y0 = r_start * math.cos(a), r_start * math.sin(a)
                x1, y1 = 3.1 * math.cos(a), 3.1 * math.sin(a)
                ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                            arrowprops=dict(arrowstyle="-|>", color="#5D6D7E", lw=1))
        ax.set_xlim(-3.4, 3.4)
        ax.set_ylim(-3.4, 3.4)

    elif ct == "line":
        # infinite line charge, coaxial cylinder
        ax.plot([0, 0], [-3, 3], color="#C0392B", lw=3)
        ax.text(0.15, 2.7, r"$\lambda$", color="#C0392B", fontsize=12)
        r = 1.8
        ax.add_patch(mpatches.Ellipse((0, 2.0), 2 * r, 0.7, fill=False,
                     edgecolor="#1B4F72", lw=1.6, ls="--"))
        ax.add_patch(mpatches.Ellipse((0, -2.0), 2 * r, 0.7, fill=False,
                     edgecolor="#1B4F72", lw=1.6, ls="--"))
        for xx in (-r, r):
            ax.plot([xx, xx], [-2.0, 2.0], color="#1B4F72", lw=1.6, ls="--")
        ax.text(r + 0.1, 0, "Gaussian\ncylinder", fontsize=8, color="#1B4F72")
        if schema.show_field_lines:
            for yy in (-1.2, 0, 1.2):
                for sgn in (-1, 1):
                    ax.annotate("", xy=(sgn * 2.9, yy), xytext=(sgn * 0.12, yy),
                                arrowprops=dict(arrowstyle="-|>", color="#5D6D7E", lw=1))
        field = r"$E=\dfrac{\lambda}{2\pi\varepsilon_0 r}$"
        src = "line charge"
        ax.set_xlim(-3.6, 3.6)
        ax.set_ylim(-3.4, 3.4)

    else:   # plane
        ax.add_patch(mpatches.Rectangle((-3, -0.06), 6, 0.12, facecolor="#C0392B",
                     edgecolor="none"))
        for xx in np.linspace(-2.6, 2.6, 12):
            ax.text(xx, 0.28, "+", color="#C0392B", ha="center", fontsize=8)
        ax.text(-2.8, 0.5, r"$\sigma$", color="#C0392B", fontsize=12)
        # pillbox straddling the plane
        ax.add_patch(mpatches.Rectangle((-0.9, -1.3), 1.8, 2.6, fill=False,
                     edgecolor="#1B4F72", lw=1.6, ls="--"))
        ax.text(1.0, 1.1, "pillbox", fontsize=8, color="#1B4F72")
        if schema.show_field_lines:
            for xx in (-1.8, 0, 1.8):
                ax.annotate("", xy=(xx, 2.4), xytext=(xx, 0.1),
                            arrowprops=dict(arrowstyle="-|>", color="#5D6D7E", lw=1))
                ax.annotate("", xy=(xx, -2.4), xytext=(xx, -0.1),
                            arrowprops=dict(arrowstyle="-|>", color="#5D6D7E", lw=1))
        field = r"$E=\dfrac{\sigma}{2\varepsilon_0}$ (uniform)"
        src = "infinite plane"
        ax.set_xlim(-3.4, 3.4)
        ax.set_ylim(-3.0, 3.0)

    parts = [f"Source: {src}"]
    if schema.show_flux:
        parts.append(flux)
    parts.append(field)
    ax.text(0.5, -0.02, "     ".join(parts), transform=ax.transAxes, ha="center",
            va="top", fontsize=10, color="#1B4F72")
    ax.set_title(schema.title or f"Gauss's law — {src} ({schema.surface})",
                 fontsize=13, fontweight="bold")
    fig.tight_layout()
    return _fig_to_svg_phys(fig)


# ── Equipotential Lines ───────────────────────────────────────────────────────

def _potential_field(config: str, X, Y):
    """Potential V and field components (Ex, Ey) on a grid for a charge config.

    Equipotentials are contours of V; field lines are streamlines of (Ex, Ey).
    Because E = −∇V, the two families are ALWAYS mutually perpendicular — drawing
    them from the same V guarantees the right angle the question tests.
    """
    charge_sets = {
        "point_charge": [(0.0, 0.0, 1.0)],
        "dipole": [(-1.0, 0.0, 1.0), (1.0, 0.0, -1.0)],
        "two_like_charges": [(-1.0, 0.0, 1.0), (1.0, 0.0, 1.0)],
    }
    V = np.zeros_like(X)
    Ex = np.zeros_like(X)
    Ey = np.zeros_like(X)
    for cx, cy, q in charge_sets[config]:
        dx, dy = X - cx, Y - cy
        r = np.sqrt(dx * dx + dy * dy) + 1e-9
        V += q / r
        Ex += q * dx / r ** 3
        Ey += q * dy / r ** 3
    return V, Ex, Ey, charge_sets[config]


def render_equipotential(data: Dict[str, Any], canvas_w: int = 800,
                         canvas_h: int = 600) -> str:
    from diagrams.schemas.physics import EquipotentialSchema
    schema = EquipotentialSchema(**data)

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))
    ax.set_aspect("equal")
    ax.axis("off")
    cfg = schema.configuration

    if cfg == "parallel_plates":
        # Uniform field between plates: field lines straight, equipotentials the
        # perpendicular family of straight lines.
        ax.add_patch(mpatches.Rectangle((-2.4, -1.8), 0.12, 3.6, facecolor="#C0392B"))
        ax.add_patch(mpatches.Rectangle((2.28, -1.8), 0.12, 3.6, facecolor="#2874A6"))
        ax.text(-2.34, 2.0, "+", color="#C0392B", fontsize=16, ha="center")
        ax.text(2.34, 2.0, "$-$", color="#2874A6", fontsize=16, ha="center")
        if schema.show_field_lines:
            for yy in np.linspace(-1.5, 1.5, 7):
                ax.annotate("", xy=(2.2, yy), xytext=(-2.2, yy),
                            arrowprops=dict(arrowstyle="-|>", color="#5D6D7E", lw=1.2))
        if schema.show_equipotentials:
            for xx in np.linspace(-1.8, 1.8, 7):
                ax.plot([xx, xx], [-1.7, 1.7], color="#1E8449", lw=1.1, ls="--")
        ax.text(0, -2.3, "field lines (arrows) perpendicular to equipotentials (dashed)",
                ha="center", fontsize=10, color="#555")
        ax.set_xlim(-3.0, 3.0)
        ax.set_ylim(-2.6, 2.4)
    else:
        n = 260
        xs = np.linspace(-3, 3, n)
        ys = np.linspace(-2.4, 2.4, n)
        X, Y = np.meshgrid(xs, ys)
        V, Ex, Ey, charges = _potential_field(cfg, X, Y)
        # equipotential contours at robust (percentile) levels
        if schema.show_equipotentials:
            finite = V[np.isfinite(V)]
            lo, hi = np.percentile(finite, 8), np.percentile(finite, 92)
            levels = np.linspace(lo, hi, 13)
            ax.contour(X, Y, V, levels=levels, colors="#1E8449",
                       linestyles="--", linewidths=0.9)
        if schema.show_field_lines:
            ax.streamplot(X, Y, Ex, Ey, color="#5D6D7E", density=1.2,
                          linewidth=0.8, arrowsize=0.9)
        for cx, cy, q in charges:
            ax.add_patch(plt.Circle((cx, cy), 0.14,
                         color="#C0392B" if q > 0 else "#2874A6", zorder=6))
            ax.text(cx, cy, "+" if q > 0 else "$-$", color="white", ha="center",
                    va="center", fontsize=11, fontweight="bold", zorder=7)
        ax.text(0, -2.75, "field lines perpendicular to equipotentials (dashed) everywhere",
                ha="center", fontsize=10, color="#555")
        ax.set_xlim(-3, 3)
        ax.set_ylim(-3.0, 2.6)

    ax.set_title(schema.title or f"Equipotentials & field lines — "
                 f"{cfg.replace('_', ' ')}", fontsize=13, fontweight="bold")
    fig.tight_layout()
    return _fig_to_svg_phys(fig)


# ── Cyclotron ─────────────────────────────────────────────────────────────────

def _cyclotron_spiral(num_semicircles: int, r0: float = 0.5):
    """Connected semicircles of GROWING radius, alternating dees, centred on origin.

    Radius r ∝ v ∝ √(energy); the particle gains equal energy at each gap crossing,
    so r_k ∝ √k. Consecutive half-turns run in OPPOSITE directions along the gap,
    so the growing radii oscillate about the centre and the path spirals outward
    symmetrically instead of marching off to one side.
    """
    pts = []
    y = 0.0
    for k in range(1, num_semicircles + 1):
        r = r0 * math.sqrt(k)
        side = 1 if k % 2 == 1 else -1          # right dee (odd), left dee (even)
        if k % 2 == 1:                          # travel downward along the gap
            cy, th = y - r, np.linspace(math.pi / 2, -math.pi / 2, 40)
            y_next = y - 2 * r
        else:                                   # travel upward
            cy, th = y + r, np.linspace(-math.pi / 2, math.pi / 2, 40)
            y_next = y + 2 * r
        xs = side * r * np.cos(th)
        ysd = cy + r * np.sin(th)
        pts.append(np.column_stack([xs, ysd]))
        y = y_next
    return np.vstack(pts)


def render_cyclotron(data: Dict[str, Any], canvas_w: int = 800,
                     canvas_h: int = 600) -> str:
    from diagrams.schemas.physics import CyclotronSchema
    schema = CyclotronSchema(**data)

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))
    ax.set_aspect("equal")
    ax.axis("off")

    R = 3.1
    gap = 0.16
    if schema.show_dees:
        ax.add_patch(mpatches.Wedge((-gap, 0), R, 90, 270, facecolor="#D6EAF8",
                     edgecolor="black", lw=2))
        ax.add_patch(mpatches.Wedge((gap, 0), R, -90, 90, facecolor="#D6EAF8",
                     edgecolor="black", lw=2))
        ax.text(-R + 0.5, R - 0.4, "D₁", fontsize=13, fontweight="bold")
        ax.text(R - 0.8, R - 0.4, "D₂", fontsize=13, fontweight="bold")
        # accelerating gap (alternating voltage across the dees)
        ax.annotate("gap (a.c. ~V)", xy=(0, R - 0.15), xytext=(R + 0.7, R - 0.1),
                    fontsize=8, color="#C0392B", ha="left", va="center",
                    arrowprops=dict(arrowstyle="->", color="#C0392B", lw=1))

    if schema.show_magnetic_field:
        # B out of the page: circle-with-dot markers on a light grid
        for gx in np.linspace(-2.4, 2.4, 5):
            for gy in np.linspace(-2.4, 2.4, 5):
                if gx * gx + gy * gy < (R - 0.6) ** 2:
                    ax.add_patch(plt.Circle((gx, gy), 0.08, fill=False,
                                 edgecolor="#7F8C8D", lw=0.8))
                    ax.plot(gx, gy, ".", color="#7F8C8D", ms=2)
        ax.text(0, R + 0.25, "B out of the page", ha="center", fontsize=9,
                color="#7F8C8D")

    if schema.show_spiral:
        pts = _cyclotron_spiral(2 * schema.num_turns, r0=0.6)
        ax.plot(pts[:, 0], pts[:, 1], color="#C0392B", lw=1.6, zorder=5)
        ax.plot(0, 0, "o", color="#C0392B", ms=5, zorder=6)
        # Extraction at the outermost point, tangentially out of the dee.
        itip = int(np.argmax(np.hypot(pts[:, 0], pts[:, 1])))
        tip = pts[itip]
        out = tip * 1.6
        ax.annotate("", xy=(out[0], out[1]), xytext=(tip[0], tip[1]),
                    arrowprops=dict(arrowstyle="-|>", color="#C0392B", lw=1.8))
        ax.text(out[0], out[1] + 0.2, "extracted beam", fontsize=8,
                color="#C0392B", ha="center", va="bottom")

    ax.text(0, -R - 0.75, r"$f = \dfrac{qB}{2\pi m}$  (independent of radius/speed)",
            ha="center", fontsize=12, color="#1B4F72")
    ax.set_xlim(-R - 1.4, R + 2.2)
    ax.set_ylim(-R - 1.3, R + 0.7)
    ax.set_title(schema.title or "Cyclotron", fontsize=13, fontweight="bold")
    fig.tight_layout()
    return _fig_to_svg_phys(fig)


# ── Velocity Selector / Mass Spectrometer ─────────────────────────────────────

def _velocity_selector_v(e_field: float, b_field: float) -> float:
    """Selected (undeflected) speed v = E/B: the electric and magnetic forces
    qE and qvB cancel only at this one speed, whatever the charge or mass."""
    return e_field / b_field


def _spectrometer_radius(mass: float, v: float, charge: float, b_field: float) -> float:
    """Radius in the analyser r = mv/(qB): heavier ions swing wider."""
    return mass * v / (charge * b_field)


def render_velocity_selector(data: Dict[str, Any], canvas_w: int = 800,
                             canvas_h: int = 600) -> str:
    from diagrams.schemas.physics import VelocitySelectorSchema
    schema = VelocitySelectorSchema(**data)
    v_sel = _velocity_selector_v(schema.e_field, schema.b_field)

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))
    ax.set_aspect("equal")
    ax.axis("off")

    # Selector region: crossed E (arrows) and B (dots).
    x0, x1, yb, yt = -6.5, -2.0, -1.6, 1.6
    ax.add_patch(mpatches.Rectangle((x0, yb), x1 - x0, yt - yb, fill=False,
                 edgecolor="black", lw=1.2))
    for xx in np.linspace(x0 + 0.4, x1 - 0.4, 5):
        ax.annotate("", xy=(xx, yb + 0.25), xytext=(xx, yt - 0.25),
                    arrowprops=dict(arrowstyle="-|>", color="#C0392B", lw=1))
    ax.text(x0 + 0.15, yt - 0.3, "E", color="#C0392B", fontsize=11, fontweight="bold")
    for gx in np.linspace(x0 + 0.6, x1 - 0.4, 4):
        for gy in np.linspace(yb + 0.5, yt - 0.5, 3):
            ax.add_patch(plt.Circle((gx, gy), 0.07, fill=False, edgecolor="#5D6D7E",
                         lw=0.8))
            ax.plot(gx, gy, ".", color="#5D6D7E", ms=2)
    ax.text(x1 - 0.5, yb + 0.15, "B (out)", color="#5D6D7E", fontsize=8)

    # Slit + selected (undeflected) beam
    ax.plot([x0 - 1.4, x0], [0, 0], color="#1E8449", lw=1.6)
    ax.annotate("", xy=(x1, 0), xytext=(x0, 0),
                arrowprops=dict(arrowstyle="-|>", color="#1E8449", lw=2))
    if schema.show_selected_velocity:
        # Rejected faster/slower beams deflect oppositely.
        ax.plot([x0, x1], [0, 0.9], color="#aaa", lw=1, ls=":")
        ax.plot([x0, x1], [0, -0.9], color="#aaa", lw=1, ls=":")
        ax.text((x0 + x1) / 2, -2.05,
                rf"selected $v = E/B = {v_sel:.3g}$ m/s", ha="center",
                fontsize=10, color="#1E8449")

    if schema.mode == "mass_spectrometer":
        masses = schema.masses or [1.0e-26, 1.5e-26, 2.0e-26]
        # Analyser: uniform B only; ions turn in semicircles of r = mv/qB.
        ax.add_patch(mpatches.Rectangle((-2.0, -6.5), 8.0, 6.4, fill=False,
                     edgecolor="black", lw=1.0, ls="-"))
        for gx in np.linspace(-1.4, 5.4, 6):
            for gy in np.linspace(-6.0, -0.6, 5):
                ax.plot(gx, gy, ".", color="#5D6D7E", ms=2)
                ax.add_patch(plt.Circle((gx, gy), 0.06, fill=False,
                             edgecolor="#5D6D7E", lw=0.6))
        entry = np.array([-2.0, 0.0])
        colors = ["#C0392B", "#8E44AD", "#2874A6", "#E67E22"]
        rmin = min(masses)
        for i, m in enumerate(masses):
            r = _spectrometer_radius(m, v_sel, schema.charge, schema.b_field)
            r_draw = 1.2 * (m / rmin)             # scaled for display, ∝ m (v,q,B fixed)
            th = np.linspace(0, -math.pi, 80)
            cx, cy = entry[0], entry[1] - r_draw
            xs = cx + r_draw * np.cos(th + math.pi / 2)
            ys = cy + r_draw * np.sin(th + math.pi / 2)
            ax.plot(xs, ys, color=colors[i % 4], lw=1.6)
            ax.plot(xs[-1], ys[-1], "v", color=colors[i % 4], ms=6)
            ax.text(xs[-1], ys[-1] + 0.25, f"m{i+1}", color=colors[i % 4],
                    fontsize=8, ha="center")
        ax.text(2.0, -6.9, r"analyser: $r = \dfrac{mv}{qB}$  (heavier ions swing wider)",
                ha="center", fontsize=10, color="#1B4F72")
        ax.set_xlim(-8.2, 6.6)
        ax.set_ylim(-7.6, 2.2)
    else:
        ax.set_xlim(-8.2, -1.2)
        ax.set_ylim(-2.6, 2.2)

    title = ("Velocity selector" if schema.mode == "velocity_selector"
             else "Mass spectrometer (Bainbridge)")
    ax.set_title(schema.title or title, fontsize=13, fontweight="bold")
    fig.tight_layout()
    return _fig_to_svg_phys(fig)


# ── X-ray Spectrum ────────────────────────────────────────────────────────────

def _xray_lambda_min_pm(tube_kv: float) -> float:
    """Duane–Hunt limit λ_min = hc/(eV). In picometres, λ_min = 1239.84/V(kV).

    This sharp short-wavelength cutoff (set ONLY by the tube voltage, not the
    target) is the quantum signature of the continuous X-ray spectrum.
    """
    return _HC_EV_NM / (tube_kv * 1000.0) * 1000.0    # nm→pm


def _moseley_k_pm(z: int, line: str) -> float:
    """Characteristic Kα (2→1) or Kβ (3→1) wavelength (pm) from Moseley's law."""
    R = 1.0973731568e7          # Rydberg, m⁻¹
    if line == "alpha":
        inv = R * (z - 1) ** 2 * (1.0 - 1.0 / 4.0)
    else:                        # beta
        inv = R * (z - 1) ** 2 * (1.0 - 1.0 / 9.0)
    return (1.0 / inv) * 1e12    # m→pm


def render_xray_spectrum(data: Dict[str, Any], canvas_w: int = 800,
                         canvas_h: int = 600) -> str:
    from diagrams.schemas.physics import XraySpectrumSchema
    schema = XraySpectrumSchema(**data)

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))

    lam_min = _xray_lambda_min_pm(schema.tube_voltage)
    lam = np.linspace(lam_min, lam_min * 8, 500)
    # Kramers' law for the continuous bremsstrahlung background.
    intensity = np.maximum(0.0, (lam / lam_min - 1.0)) / lam ** 2
    intensity = intensity / intensity.max()
    ax.plot(lam, intensity, color="#1B4F72", lw=2, label="bremsstrahlung")
    ax.fill_between(lam, 0, intensity, color="#AED6F1", alpha=0.4)

    if schema.show_lambda_min:
        ax.axvline(lam_min, color="#C0392B", lw=1.2, ls="--")
        ax.text(lam_min, 1.02, rf"$\lambda_{{min}}={lam_min:.1f}$ pm",
                color="#C0392B", fontsize=9, ha="left", va="bottom")

    if schema.show_characteristic:
        # Kβ (3→1) is higher-energy, so it sits at SHORTER wavelength than Kα (2→1).
        for line, lbl, top in (("beta", "K$_\\beta$", 1.03), ("alpha", "K$_\\alpha$", 1.2)):
            lam_c = _moseley_k_pm(schema.target_z, line)
            # A characteristic line appears only if the tube can excite it
            # (its wavelength must be longer than the cutoff).
            if lam_c >= lam_min and lam_c <= lam[-1]:
                base = np.interp(lam_c, lam, intensity)
                ax.plot([lam_c, lam_c], [base, top], color="#C0392B", lw=2.5)
                ax.text(lam_c, top + 0.02, lbl, color="#C0392B", fontsize=10,
                        ha="center", va="bottom")

    ax.set_xlabel("Wavelength λ (pm)", fontsize=11)
    ax.set_ylabel("Intensity", fontsize=11)
    ax.set_ylim(0, 1.35)
    ax.set_xlim(0, lam[-1])
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_title(schema.title or f"X-ray spectrum — {schema.target_element} target "
                 f"at {schema.tube_voltage:.0f} kV", fontsize=13, fontweight="bold")
    fig.tight_layout()
    return _fig_to_svg_phys(fig)


# ── Beats ─────────────────────────────────────────────────────────────────────

def _beat_frequency(f1: float, f2: float) -> float:
    """Beat frequency = |f₁ − f₂|: the number of loudness maxima per second."""
    return abs(f1 - f2)


def render_beats(data: Dict[str, Any], canvas_w: int = 800,
                 canvas_h: int = 600) -> str:
    from diagrams.schemas.physics import BeatsSchema
    schema = BeatsSchema(**data)
    f1, f2, A = schema.frequency1, schema.frequency2, schema.amplitude
    f_beat = _beat_frequency(f1, f2)

    fig, axes = plt.subplots(3, 1, figsize=(canvas_w / 100, canvas_h / 100),
                             sharex=True)
    t = np.linspace(0, schema.duration, 2000)
    y1 = A * np.sin(2 * np.pi * f1 * t)
    y2 = A * np.sin(2 * np.pi * f2 * t)
    ys = y1 + y2

    axes[0].plot(t, y1, color="#2874A6", lw=1)
    axes[0].set_ylabel(f"$f_1$ = {f1:g} Hz", fontsize=9)
    axes[1].plot(t, y2, color="#1E8449", lw=1)
    axes[1].set_ylabel(f"$f_2$ = {f2:g} Hz", fontsize=9)
    axes[2].plot(t, ys, color="#1B4F72", lw=1)
    axes[2].set_ylabel("sum", fontsize=9)

    if schema.show_envelope and f_beat > 0:
        env = 2 * A * np.abs(np.cos(2 * np.pi * (f_beat / 2.0) * t))
        axes[2].plot(t, env, color="#C0392B", lw=1.3, ls="--")
        axes[2].plot(t, -env, color="#C0392B", lw=1.3, ls="--")
        # mark one beat period
        T_beat = 1.0 / f_beat
        if T_beat <= schema.duration:
            axes[2].annotate("", xy=(T_beat, 2.35 * A), xytext=(0, 2.35 * A),
                             arrowprops=dict(arrowstyle="<->", color="#C0392B"))
            axes[2].text(T_beat / 2, 2.5 * A,
                         f"beat period $T$ = 1/{f_beat:g} = {T_beat:.3g} s",
                         ha="center", fontsize=9, color="#C0392B")

    axes[2].set_xlabel("time (s)", fontsize=10)
    for ax in axes:
        ax.axhline(0, color="#ccc", lw=0.6)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
    axes[2].set_ylim(-2.8 * A, 3.0 * A)
    axes[0].set_title(schema.title or f"Beats — $f_{{beat}}=|f_1-f_2|$ = {f_beat:g} Hz",
                      fontsize=13, fontweight="bold")
    fig.tight_layout()
    return _fig_to_svg_phys(fig)


# ── Damped / Forced Oscillation ───────────────────────────────────────────────

def render_damped_oscillation(data: Dict[str, Any], canvas_w: int = 800,
                              canvas_h: int = 600) -> str:
    from diagrams.schemas.physics import DampedOscillationSchema
    schema = DampedOscillationSchema(**data)

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))
    w0 = schema.omega0

    if schema.mode == "damped":
        t = np.linspace(0, schema.duration, 1500)
        gamma = {"under": 0.25 * w0, "critical": w0, "over": 1.8 * w0}[schema.damping_type]
        A = 1.0
        if schema.damping_type == "under":
            wd = math.sqrt(max(w0 * w0 - gamma * gamma, 1e-9))
            x = A * np.exp(-gamma * t) * np.cos(wd * t)
            env = A * np.exp(-gamma * t)
            ax.plot(t, env, color="#C0392B", lw=1.2, ls="--", label="envelope $e^{-\\gamma t}$")
            ax.plot(t, -env, color="#C0392B", lw=1.2, ls="--")
            ax.plot(t, x, color="#1B4F72", lw=1.6, label="underdamped")
        else:
            # critical/over: no oscillation, monotonic return to equilibrium
            if schema.damping_type == "critical":
                x = A * (1 + w0 * t) * np.exp(-w0 * t)
                lbl = "critically damped"
            else:
                r1 = -gamma + math.sqrt(gamma * gamma - w0 * w0)
                r2 = -gamma - math.sqrt(gamma * gamma - w0 * w0)
                c1 = -r2 / (r1 - r2)
                c2 = r1 / (r1 - r2)
                x = A * (c1 * np.exp(r1 * t) + c2 * np.exp(r2 * t))
                lbl = "overdamped"
            ax.plot(t, x, color="#1B4F72", lw=1.6, label=lbl)
        ax.axhline(0, color="#ccc", lw=0.7)
        ax.set_xlabel("time (s)", fontsize=11)
        ax.set_ylabel("displacement", fontsize=11)
        ax.legend(fontsize=9, loc="upper right")
        title = f"Damped oscillation ({schema.damping_type}damped)"
    else:
        # forced_resonance: amplitude vs driving frequency for several dampings
        gammas = schema.damping_values or [0.1 * w0, 0.25 * w0, 0.5 * w0]
        w = np.linspace(0.1 * w0, 2.0 * w0, 600)
        for g in sorted(gammas):
            amp = 1.0 / np.sqrt((w0 ** 2 - w ** 2) ** 2 + (2 * g * w) ** 2)
            ax.plot(w / w0, amp, lw=1.8, label=f"$\\gamma$ = {g/w0:.2f}$\\omega_0$")
        ax.axvline(1.0, color="#888", lw=1, ls=":")
        ax.text(1.0, ax.get_ylim()[1] * 0.02, r" $\omega=\omega_0$", fontsize=9,
                color="#555")
        ax.set_xlabel(r"driving frequency $\omega/\omega_0$", fontsize=11)
        ax.set_ylabel("amplitude", fontsize=11)
        ax.legend(fontsize=9, title="less damping = sharper peak")
        title = "Forced oscillation — resonance"

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_title(schema.title or title, fontsize=13, fontweight="bold")
    fig.tight_layout()
    return _fig_to_svg_phys(fig)


# ── Collision ─────────────────────────────────────────────────────────────────

def _elastic_1d(m1: float, m2: float, u1: float, u2: float) -> Tuple[float, float]:
    """1-D elastic collision — both momentum AND kinetic energy conserved."""
    v1 = ((m1 - m2) * u1 + 2 * m2 * u2) / (m1 + m2)
    v2 = ((m2 - m1) * u2 + 2 * m1 * u1) / (m1 + m2)
    return v1, v2


def _inelastic(m1: float, m2: float, u1: float, u2: float) -> float:
    """Perfectly inelastic: bodies stick, common velocity from momentum alone."""
    return (m1 * u1 + m2 * u2) / (m1 + m2)


def render_collision(data: Dict[str, Any], canvas_w: int = 800,
                     canvas_h: int = 600) -> str:
    from diagrams.schemas.physics import CollisionSchema
    schema = CollisionSchema(**data)
    m1, m2, u1, u2 = schema.m1, schema.m2, schema.u1, schema.u2

    fig, (ax_b, ax_a) = plt.subplots(2, 1, figsize=(canvas_w / 100, canvas_h / 100))
    for ax in (ax_b, ax_a):
        ax.set_aspect("equal")
        ax.axis("off")
        ax.axhline(0, color="#ddd", lw=0.8)
        ax.set_xlim(-6, 6)
        ax.set_ylim(-2.4, 2.4)

    def body(ax, x, y, m, color, lbl):
        R = 0.28 + 0.12 * m
        ax.add_patch(plt.Circle((x, y), R, facecolor=color, edgecolor="black",
                     alpha=0.85))
        ax.text(x, y, lbl, ha="center", va="center", color="white", fontsize=9,
                fontweight="bold")
        return R

    def vec(ax, x, y, vx, vy, color, label):
        if abs(vx) < 1e-6 and abs(vy) < 1e-6:
            ax.text(x, y - 0.5, "at rest", ha="center", fontsize=8, color=color)
            return
        ax.annotate("", xy=(x + vx, y + vy), xytext=(x, y),
                    arrowprops=dict(arrowstyle="-|>", color=color, lw=2))
        ax.text(x + vx + 0.15 * (1 if vx >= 0 else -1), y + vy + 0.2, label,
                fontsize=9, color=color, ha="center")

    sc = 0.5
    if schema.collision_type == "oblique":
        # Equal-mass elastic oblique: the two bodies separate at 90°.
        th1 = math.radians(schema.angle)
        th2 = math.radians(90 - schema.angle)
        v1 = u1 * math.cos(th1)
        v2 = u1 * math.sin(th1)
        body(ax_b, -3, 0, m1, "#2874A6", "1")
        body(ax_b, 3, 0, m2, "#C0392B", "2")
        vec(ax_b, -3, 0, u1 * sc, 0, "#2874A6", f"u₁={u1:g}")
        ax_b.set_title("Before (oblique, equal masses)", fontsize=10)
        body(ax_a, 0, 0, m1, "#2874A6", "1")
        body(ax_a, 0, 0, m2, "#C0392B", "2")
        vec(ax_a, 0, 0, v1 * sc * math.cos(th1), v1 * sc * math.sin(th1),
            "#2874A6", f"v₁={v1:.2f}")
        vec(ax_a, 0, 0, v2 * sc * math.cos(-th2), v2 * sc * math.sin(-th2),
            "#C0392B", f"v₂={v2:.2f}")
        ax_a.set_title(rf"After: bodies separate at 90° "
                       rf"($\theta_1+\theta_2$ = 90°)", fontsize=10)
        note = "equal-mass elastic oblique collision"
    else:
        if schema.collision_type == "elastic":
            v1, v2 = _elastic_1d(m1, m2, u1, u2)
            note = f"elastic: v₁={v1:.2f}, v₂={v2:.2f} m/s (momentum & KE conserved)"
        else:
            v = _inelastic(m1, m2, u1, u2)
            v1 = v2 = v
            note = f"perfectly inelastic: they stick, v={v:.2f} m/s (momentum only)"
        body(ax_b, -3, 0, m1, "#2874A6", "1")
        body(ax_b, 1.5, 0, m2, "#C0392B", "2")
        vec(ax_b, -3, 0, u1 * sc, 0, "#2874A6", f"u₁={u1:g}")
        vec(ax_b, 1.5, 0, u2 * sc, 0, "#C0392B", f"u₂={u2:g}")
        ax_b.set_title("Before", fontsize=10)
        if schema.collision_type == "perfectly_inelastic":
            body(ax_a, 0.5, 0, m1, "#2874A6", "1")
            body(ax_a, 0.5 + 0.45, 0, m2, "#C0392B", "2")
            vec(ax_a, 1.2, 0, v1 * sc, 0, "#6C3483", f"v={v1:.2f}")
        else:
            body(ax_a, -2.5, 0, m1, "#2874A6", "1")
            body(ax_a, 2.5, 0, m2, "#C0392B", "2")
            vec(ax_a, -2.5, 0, v1 * sc, 0, "#2874A6", f"v₁={v1:.2f}")
            vec(ax_a, 2.5, 0, v2 * sc, 0, "#C0392B", f"v₂={v2:.2f}")
        ax_a.set_title("After", fontsize=10)

    fig.text(0.5, 0.02, note, ha="center", fontsize=10, color="#1B4F72")
    fig.suptitle(schema.title or f"{schema.collision_type.replace('_', ' ').title()} "
                 "collision", fontsize=13, fontweight="bold")
    fig.tight_layout(rect=(0, 0.05, 1, 0.96))
    return _fig_to_svg_phys(fig)


# ── Banked Road ───────────────────────────────────────────────────────────────

def _banked_speed(radius: float, gravity: float, angle_deg: float) -> float:
    """Ideal (no-friction) speed on a banked curve: v = √(r·g·tanθ).

    At exactly this speed the horizontal component of the normal force alone
    supplies the centripetal force — no friction is needed.
    """
    return math.sqrt(radius * gravity * math.tan(math.radians(angle_deg)))


def render_banked_road(data: Dict[str, Any], canvas_w: int = 800,
                       canvas_h: int = 600) -> str:
    from diagrams.schemas.physics import BankedRoadSchema
    schema = BankedRoadSchema(**data)
    th = schema.bank_angle
    v_ideal = _banked_speed(schema.radius, schema.gravity, th)

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))
    ax.set_aspect("equal")
    ax.axis("off")

    thr = math.radians(th)
    # Banked wedge
    base = 6.0
    h = base * math.tan(thr)
    bl, br, tl = (-base / 2, 0), (base / 2, 0), (-base / 2, h)
    ax.add_patch(mpatches.Polygon([bl, br, tl], closed=True, facecolor="#EBDEF0",
                 edgecolor="black", lw=2))
    # angle arc
    ax.add_patch(mpatches.Arc(br, 1.8, 1.8, angle=0, theta1=180 - th, theta2=180,
                 color="black"))
    ax.text(br[0] - 1.3, 0.22, f"θ={th:g}°", fontsize=10)

    # Car on the incline surface
    px = 0.15
    car = (bl[0] + (br[0] - bl[0]) * (0.5 - px), 0)
    cx = (bl[0] + tl[0]) / 2 + 1.4
    cyc = (bl[1] + tl[1]) / 2 + 1.4 * math.tan(thr) * 0  # place on surface
    # point on surface (mid)
    sx = -0.4
    sy = (sx - bl[0]) * math.tan(thr)
    ax.add_patch(mpatches.FancyBboxPatch((sx - 0.45, sy + 0.02), 0.9, 0.45,
                 boxstyle="round,pad=0.02", facecolor="#5DADE2", edgecolor="black",
                 transform=(mpl_transform_rotate(ax, sx, sy, th))))
    ax.plot(sx, sy, "ko", ms=2)

    L = 2.4
    # Normal force: perpendicular to incline surface
    nx, ny = math.sin(thr), math.cos(thr)
    if schema.show_forces:
        ax.annotate("", xy=(sx + L * nx, sy + L * ny), xytext=(sx, sy),
                    arrowprops=dict(arrowstyle="-|>", color="#1E8449", lw=2.2))
        ax.text(sx + L * nx + 0.1, sy + L * ny, "N", color="#1E8449", fontsize=12)
        # weight
        ax.annotate("", xy=(sx, sy - L), xytext=(sx, sy),
                    arrowprops=dict(arrowstyle="-|>", color="#C0392B", lw=2.2))
        ax.text(sx + 0.12, sy - L - 0.1, "mg", color="#C0392B", fontsize=12)
        # Horizontal centripetal resultant. The bank rises to the left, so the
        # centre of the circular track is on the LOW side (right); the horizontal
        # component of N points that way, toward the centre.
        ax.annotate("", xy=(sx + 1.9, sy), xytext=(sx, sy),
                    arrowprops=dict(arrowstyle="-|>", color="#1B4F72", lw=2.2))
        ax.text(sx + 2.0, sy - 0.28, r"$F_c$ (centripetal, to centre)",
                color="#1B4F72", fontsize=10, ha="left")
    if schema.show_friction and schema.friction_coefficient > 0:
        # Friction acts ALONG the incline surface. Here it points up the slope
        # (the case of a car moving below the ideal speed, tending to slide down).
        fx, fy = -math.cos(thr), math.sin(thr)
        ax.annotate("", xy=(sx + 1.4 * fx, sy + 1.4 * fy), xytext=(sx, sy),
                    arrowprops=dict(arrowstyle="-|>", color="#E67E22", lw=2))
        ax.text(sx + 1.4 * fx - 0.1, sy + 1.4 * fy + 0.2,
                f"f (μ={schema.friction_coefficient:g})", color="#E67E22", fontsize=9,
                ha="right")

    ax.text(0.5, 0.03, rf"ideal speed  $v=\sqrt{{r g \tan\theta}} = {v_ideal:.1f}$ m/s"
            rf"  (r = {schema.radius:g} m)", transform=ax.transAxes, ha="center",
            fontsize=12, color="#1B4F72")
    ax.set_xlim(-base / 2 - 2.4, base / 2 + 1.0)
    ax.set_ylim(-1.2, h + 1.0)
    ax.set_title(schema.title or "Car on a banked road", fontsize=13,
                 fontweight="bold")
    fig.tight_layout()
    return _fig_to_svg_phys(fig)


def mpl_transform_rotate(ax, x, y, angle_deg):
    import matplotlib.transforms as mtransforms
    return (mtransforms.Affine2D().rotate_deg_around(x, y, angle_deg)
            + ax.transData)


# ── Electromagnetic Induction ─────────────────────────────────────────────────

def render_em_induction(data: Dict[str, Any], canvas_w: int = 800,
                        canvas_h: int = 600) -> str:
    from diagrams.schemas.physics import EMInductionSchema
    schema = EMInductionSchema(**data)

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))
    ax.set_aspect("equal")
    ax.axis("off")
    ph = schema.phenomenon

    if ph in ("lenz_law", "flux_change"):
        # Coil/loop on the right; a bar magnet (N facing) approaches from the left.
        loop_x = 2.2
        ax.add_patch(mpatches.Ellipse((loop_x, 0), 1.0, 3.0, fill=False,
                     edgecolor="#7D3C98", lw=2.5))
        if ph == "lenz_law":
            # Bar magnet approaching, N pole toward the coil.
            ax.add_patch(mpatches.Rectangle((-2.8, -0.5), 1.3, 1.0,
                         facecolor="#5DADE2", edgecolor="black"))
            ax.add_patch(mpatches.Rectangle((-1.5, -0.5), 1.3, 1.0,
                         facecolor="#EC7063", edgecolor="black"))
            ax.text(-2.15, 0, "S", ha="center", va="center", fontsize=12,
                    color="white", fontweight="bold")
            ax.text(-0.85, 0, "N", ha="center", va="center", fontsize=12,
                    color="white", fontweight="bold")
            ax.annotate("", xy=(0.4, 0), xytext=(-0.1, 0),
                        arrowprops=dict(arrowstyle="-|>", color="black", lw=2))
            ax.text(0.15, 0.35, "v", fontsize=11)
            change = "magnet approaching (flux increasing)"
        else:
            # Loop in a field that is increasing into the page.
            for gx in np.linspace(loop_x - 0.3, loop_x + 0.3, 3):
                for gy in np.linspace(-1.0, 1.0, 3):
                    ax.plot(gx, gy, "x", color="#5D6D7E", ms=6)
            ax.text(loop_x, 1.9, "B into page, increasing", ha="center", fontsize=9,
                    color="#5D6D7E")
            change = "flux into page increasing"
        if schema.show_induced_current:
            # Induced current OPPOSES the change → its near face becomes N (repels).
            ax.add_patch(mpatches.Arc((loop_x, 0), 1.4, 3.4, theta1=250, theta2=290,
                         color="#C0392B", lw=2))
            ax.annotate("", xy=(loop_x + 0.28, -1.62), xytext=(loop_x - 0.05, -1.68),
                        arrowprops=dict(arrowstyle="-|>", color="#C0392B", lw=2))
            ax.text(loop_x + 1.0, 0, "$I_{ind}$", color="#C0392B", fontsize=12)
            ax.text(loop_x, -2.1, "coil face = N (repels)", ha="center", fontsize=8,
                    color="#C0392B")
        note = f"Lenz's law: induced current opposes the change ({change})"
        ax.set_xlim(-3.2, 4.2)
        ax.set_ylim(-2.6, 2.4)

    elif ph == "motional_emf":
        # Conducting rod sliding on rails in a magnetic field.
        ax.add_patch(mpatches.Rectangle((-3, -2), 6, 4, fill=False, edgecolor="none"))
        ax.plot([-3, 3], [1.5, 1.5], color="black", lw=2)      # top rail
        ax.plot([-3, 3], [-1.5, -1.5], color="black", lw=2)    # bottom rail
        ax.plot([-3, -3], [-1.5, 1.5], color="black", lw=2)    # left (resistor side)
        rod_x = 0.8
        ax.plot([rod_x, rod_x], [-1.5, 1.5], color="#C0392B", lw=4)  # moving rod
        ax.annotate("", xy=(rod_x + 1.1, 0), xytext=(rod_x, 0),
                    arrowprops=dict(arrowstyle="-|>", color="black", lw=2))
        ax.text(rod_x + 0.55, 0.25, "v", fontsize=12)
        ax.text(rod_x + 0.1, 1.7, "rod (length $l$)", fontsize=9, color="#C0392B")
        for gx in np.linspace(-2.6, 2.6, 7):
            for gy in np.linspace(-1.1, 1.1, 3):
                ax.plot(gx, gy, "x", color="#5D6D7E", ms=6)
        ax.text(-2.9, 1.9, "B into page", fontsize=9, color="#5D6D7E")
        if schema.show_induced_current:
            # qv×B drives current UP the rod (v is +x, B into page), so the loop
            # circulates: up the rod, left on top, down the left side, right on
            # the bottom.
            for (ax0, ay0, ax1, ay1) in [(rod_x, -0.7, rod_x, 0.7),   # up the rod
                                         (rod_x, 1.5, -1.6, 1.5),     # top: left
                                         (-3, 0.7, -3, -0.7),         # left: down
                                         (-3, -1.5, rod_x - 1.6, -1.5)]:  # bottom: right
                ax.annotate("", xy=(ax1, ay1), xytext=(ax0, ay0),
                            arrowprops=dict(arrowstyle="-|>", color="#1E8449", lw=1.6))
            ax.text(-3.4, 0, "$I$", color="#1E8449", fontsize=12, ha="right")
        note = r"Motional emf  $\varepsilon = Blv$"
        ax.set_xlim(-4.0, 3.4)
        ax.set_ylim(-2.4, 2.4)

    else:   # eddy_currents
        # A metal plate swinging into a field region develops opposing eddy currents.
        ax.add_patch(mpatches.Rectangle((-2.2, -2.2), 4.4, 4.4, facecolor="#FCF3CF",
                     edgecolor="black", lw=1.2))
        for gx in np.linspace(-1.8, 1.8, 6):
            for gy in np.linspace(-1.8, 1.8, 6):
                ax.plot(gx, gy, ".", color="#5D6D7E", ms=3)
        ax.text(0, 2.5, "field region (B out of page)", ha="center", fontsize=9,
                color="#5D6D7E")
        ax.add_patch(mpatches.Rectangle((-1.4, -1.4), 2.8, 2.8, fill=False,
                     edgecolor="#B03A2E", lw=2))
        ax.text(-1.4, -2.0, "metal plate entering", fontsize=9, color="#B03A2E")
        if schema.show_induced_current:
            for cxy in [(-0.7, 0.6), (0.7, 0.6), (-0.7, -0.6), (0.7, -0.6)]:
                ax.add_patch(mpatches.Arc(cxy, 0.9, 0.9, theta1=0, theta2=300,
                             color="#C0392B", lw=1.6))
                ax.annotate("", xy=(cxy[0] + 0.45, cxy[1] - 0.05),
                            xytext=(cxy[0] + 0.45, cxy[1] + 0.05),
                            arrowprops=dict(arrowstyle="-|>", color="#C0392B", lw=1.6))
        ax.annotate("", xy=(3.0, 0), xytext=(2.4, 0),
                    arrowprops=dict(arrowstyle="-|>", color="black", lw=2))
        ax.text(2.7, 0.25, "v", fontsize=11)
        note = "Eddy currents circulate to oppose the motion (Lenz's law)"
        ax.set_xlim(-3.0, 3.4)
        ax.set_ylim(-2.8, 3.0)

    ax.text(0.5, -0.02, note, transform=ax.transAxes, ha="center", va="top",
            fontsize=11, color="#1B4F72")
    ax.set_title(schema.title or f"Electromagnetic induction — "
                 f"{ph.replace('_', ' ')}", fontsize=13, fontweight="bold")
    fig.tight_layout()
    return _fig_to_svg_phys(fig)


# ── Nuclear Reactor Schematic ─────────────────────────────────────────────────

def render_nuclear_reactor(data: Dict[str, Any], canvas_w: int = 800,
                           canvas_h: int = 600) -> str:
    from diagrams.schemas.physics import NuclearReactorSchema
    schema = NuclearReactorSchema(**data)

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))
    ax.axis("off")

    def lbl(x, y, text, ha="center", color="black"):
        if schema.show_labels:
            ax.text(x, y, text, ha=ha, va="center", fontsize=9, color=color)

    # Containment vessel
    ax.add_patch(mpatches.FancyBboxPatch((0.3, 1.0), 3.6, 4.2,
                 boxstyle="round,pad=0.05", facecolor="#EAECEE",
                 edgecolor="black", lw=2.5))
    lbl(2.1, 5.4, "containment / pressure vessel")
    # Core with fuel rods + control rods + moderator
    ax.add_patch(mpatches.Rectangle((0.9, 1.6), 2.4, 2.6, facecolor="#D6EAF8",
                 edgecolor="#2874A6"))
    lbl(2.1, 4.35, "moderator (water) + core", color="#2874A6")
    for i, x in enumerate(np.linspace(1.15, 3.05, 8)):
        if i % 2 == 0:
            ax.add_patch(mpatches.Rectangle((x, 1.7), 0.12, 2.4,
                         facecolor="#27AE60", edgecolor="none"))   # fuel rod
        else:
            top = 3.6 if i != 3 else 4.5
            ax.add_patch(mpatches.Rectangle((x, 1.7), 0.12, top - 1.7,
                         facecolor="#7B241C", edgecolor="none"))   # control rod
    lbl(0.55, 2.9, "fuel\nrods", ha="center", color="#1E8449")
    lbl(2.1, 0.7, "control rods (absorb neutrons, throttle the chain reaction)",
        color="#7B241C")

    # Coolant loop to heat exchanger (steam generator)
    ax.annotate("", xy=(5.2, 4.4), xytext=(3.9, 4.4),
                arrowprops=dict(arrowstyle="-|>", color="#C0392B", lw=2.5))
    ax.annotate("", xy=(3.9, 1.6), xytext=(5.2, 1.6),
                arrowprops=dict(arrowstyle="-|>", color="#2874A6", lw=2.5))
    lbl(4.5, 4.65, "hot coolant", color="#C0392B")
    lbl(4.5, 1.85, "cool coolant", color="#2874A6")
    ax.add_patch(mpatches.Rectangle((5.2, 1.4), 1.2, 3.2, facecolor="#FDEBD0",
                 edgecolor="black"))
    lbl(5.8, 3.0, "steam\ngenerator")

    # Steam to turbine + generator
    ax.annotate("", xy=(7.6, 4.4), xytext=(6.4, 4.4),
                arrowprops=dict(arrowstyle="-|>", color="#F39C12", lw=2.5))
    lbl(7.0, 4.65, "steam")
    if schema.show_turbine:
        ax.add_patch(mpatches.Polygon([(7.6, 3.9), (8.8, 4.6), (8.8, 3.2),
                     (7.6, 3.9)], closed=True, facecolor="#AED6F1", edgecolor="black"))
        lbl(8.2, 3.75, "turbine")
        ax.add_patch(plt.Circle((9.4, 3.9), 0.45, facecolor="#F9E79F",
                     edgecolor="black"))
        lbl(9.4, 3.9, "G")
        lbl(9.4, 3.25, "generator")
        ax.annotate("", xy=(8.95, 3.9), xytext=(8.8, 3.9),
                    arrowprops=dict(arrowstyle="-|>", color="black", lw=1.5))

    ax.set_xlim(-0.2, 10.2)
    ax.set_ylim(0.2, 5.8)
    ax.set_title(schema.title or f"Nuclear reactor ({schema.reactor_type}) — "
                 "chain reaction to electricity", fontsize=13, fontweight="bold")
    fig.tight_layout()
    return _fig_to_svg_phys(fig)


# ── Band Theory of Solids ─────────────────────────────────────────────────────

def render_band_theory(data: Dict[str, Any], canvas_w: int = 800,
                       canvas_h: int = 600) -> str:
    from diagrams.schemas.physics import BandTheorySchema
    schema = BandTheorySchema(**data)
    mat = schema.material

    fig, ax = plt.subplots(figsize=(canvas_w / 100, canvas_h / 100))
    ax.axis("off")

    x0, x1 = 0.15, 0.85
    vb_top = 2.0
    # Gap size (eV) per material — the distinction is the whole point.
    gaps = {"conductor": 0.0, "semiconductor": 1.1, "insulator": 6.0,
            "n_type": 1.1, "p_type": 1.1}
    gap = gaps[mat]
    cb_bot = vb_top + gap

    # Valence band (filled)
    ax.add_patch(mpatches.Rectangle((x0, 0.2), x1 - x0, vb_top - 0.2,
                 facecolor="#5DADE2", edgecolor="black", alpha=0.85))
    ax.text((x0 + x1) / 2, (0.2 + vb_top) / 2, "Valence band (filled)",
            ha="center", va="center", fontsize=10)

    if mat == "conductor":
        # Overlapping bands / partly filled — no gap.
        ax.add_patch(mpatches.Rectangle((x0, vb_top - 0.6), x1 - x0, 1.6,
                     facecolor="#F5B041", edgecolor="black", alpha=0.5))
        ax.text((x0 + x1) / 2, vb_top + 0.6, "Conduction band overlaps valence band",
                ha="center", va="center", fontsize=10)
        top = vb_top + 1.0
    else:
        cb_top = cb_bot + 1.8
        ax.add_patch(mpatches.Rectangle((x0, cb_bot), x1 - x0, cb_top - cb_bot,
                     facecolor="#F5B041", edgecolor="black", alpha=0.5))
        ax.text((x0 + x1) / 2, (cb_bot + cb_top) / 2, "Conduction band (empty)",
                ha="center", va="center", fontsize=10)
        # Band gap annotation
        ax.annotate("", xy=(0.5, cb_bot), xytext=(0.5, vb_top),
                    arrowprops=dict(arrowstyle="<->", color="#C0392B", lw=1.5))
        kind = {"insulator": "large", "semiconductor": "small",
                "n_type": "small", "p_type": "small"}[mat]
        ax.text(0.53, cb_bot - 0.28, f"$E_g$ = {gap:.1f} eV ({kind})",
                color="#C0392B", fontsize=11, va="center")
        # Dopant levels
        if mat == "n_type":
            ax.plot([0.3, 0.7], [cb_bot - 0.25, cb_bot - 0.25], color="#1E8449",
                    lw=2, ls="--")
            ax.text(0.72, cb_bot - 0.25, "donor level", color="#1E8449", fontsize=9,
                    va="center")
        elif mat == "p_type":
            ax.plot([0.3, 0.7], [vb_top + 0.25, vb_top + 0.25], color="#7D3C98",
                    lw=2, ls="--")
            ax.text(0.72, vb_top + 0.25, "acceptor level", color="#7D3C98",
                    fontsize=9, va="center")
        top = cb_top

    # Fermi level
    if schema.show_fermi:
        ef = {"conductor": vb_top, "semiconductor": (vb_top + cb_bot) / 2,
              "insulator": (vb_top + cb_bot) / 2,
              "n_type": cb_bot - 0.12, "p_type": vb_top + 0.12}[mat]
        ax.plot([x0 - 0.05, x1 + 0.05], [ef, ef], color="black", lw=1.2, ls=":")
        ax.text(x0 - 0.07, ef, "$E_F$", ha="right", va="center", fontsize=11)

    ax.set_xlim(0.0, 1.15)
    ax.set_ylim(0, top + 0.6)
    label = mat.replace("_", "-")
    ax.set_title(schema.title or f"Energy bands — {label}", fontsize=13,
                 fontweight="bold")
    fig.tight_layout()
    return _fig_to_svg_phys(fig)


# ── Dispatcher ────────────────────────────────────────────────────────────────

PHYSICS_RENDERERS = {
    "inclined_plane": render_inclined_plane,
    "free_body_diagram": render_free_body_diagram,
    "pulley_system": render_pulley_system,
    "projectile_motion": render_projectile_motion,
    "spring_block": render_spring_block,
    "optics_convex_lens": render_optics_convex_lens,
    "optics_concave_mirror": render_optics_concave_mirror,
    "wave_diagram": render_wave_diagram,
    "thermodynamics_pv": render_thermodynamics_pv,
    "ray_optics_prism": render_ray_optics_prism,
    "electric_field_lines": render_electric_field_lines,
    "magnetic_field_lines": render_magnetic_field_lines,
    "circular_motion": render_circular_motion,
    "doppler_effect": render_doppler_effect,
    "interference_pattern": render_interference_pattern,
    "bohr_atom": render_bohr_atom,
    "capacitor_dielectric": render_capacitor_dielectric,
    "lc_oscillation": render_lc_oscillation,
    "pn_junction": render_pn_junction,
    "semiconductor_iv": render_semiconductor_iv,
    "photoelectric_effect": render_photoelectric_effect,
    "nuclear_binding_energy": render_nuclear_binding_energy,
    "em_wave": render_em_wave,
    "total_internal_reflection": render_total_internal_reflection,
    "moment_of_inertia": render_moment_of_inertia,
    "fluid_mechanics": render_fluid_mechanics,
    "motion_graph": render_motion_graph,
    "shm_system": render_shm_system,
    "standing_wave": render_standing_wave,
    "stress_strain": render_stress_strain,
    "heating_curve": render_heating_curve,
    "blackbody_spectrum": render_blackbody_spectrum,
    "maxwell_boltzmann": render_maxwell_boltzmann,
    "gravitation": render_gravitation,
    "radioactive_decay": render_radioactive_decay,
    "wavefront": render_wavefront,
    "polarisation": render_polarisation,
    "measuring_instrument": render_measuring_instrument,
    "rolling_motion": render_rolling_motion,
    # WAVE-3 extension
    "optics_concave_lens": render_optics_concave_lens,
    "optics_convex_mirror": render_optics_convex_mirror,
    "optical_instrument": render_optical_instrument,
    "prism_dispersion": render_prism_dispersion,
    "energy_level_diagram": render_energy_level_diagram,
    "alpha_scattering": render_alpha_scattering,
    "heat_engine": render_heat_engine,
    "thermal_conduction": render_thermal_conduction,
    "gauss_surface": render_gauss_surface,
    "equipotential": render_equipotential,
    "cyclotron": render_cyclotron,
    "velocity_selector": render_velocity_selector,
    "xray_spectrum": render_xray_spectrum,
    "beats": render_beats,
    "damped_oscillation": render_damped_oscillation,
    "collision": render_collision,
    "banked_road": render_banked_road,
    "em_induction": render_em_induction,
    "nuclear_reactor": render_nuclear_reactor,
    "band_theory": render_band_theory,
    # Shared across physics/chemistry/mathematics — see diagrams/service/shared/xygraph.py.
    "annotated_xy_graph": render_annotated_xy_graph,
}


def render_physics(subtype: str, params: Dict[str, Any],
                   canvas_w: int = 800, canvas_h: int = 600) -> str:
    renderer = PHYSICS_RENDERERS.get(subtype)
    if not renderer:
        raise ValueError(f"Unknown physics subtype: '{subtype}'. "
                         f"Supported: {list(PHYSICS_RENDERERS.keys())}")
    return renderer(params, canvas_w=canvas_w, canvas_h=canvas_h)
