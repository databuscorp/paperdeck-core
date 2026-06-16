"""
Physics Diagram Renderer using svgwrite.
All coordinates are computed deterministically — no AI geometry.
Exam-style: black-and-white, clean, publication-quality.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

import svgwrite

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
        dwg.add(dwg.text(label, insert=(mx, my), font_size=FONT_SZ,
                         font_family=FONT, text_anchor="middle"))


def _text(dwg: svgwrite.Drawing, txt: str, x: float, y: float,
          anchor: str = "middle", size: int = FONT_SZ, bold: bool = False):
    weight = "bold" if bold else "normal"
    dwg.add(dwg.text(txt, insert=(x, y), font_size=size, font_family=FONT,
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
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import io as _io

def _fig_to_svg_phys(fig) -> str:
    buf = _io.BytesIO()
    fig.savefig(buf, format="svg", bbox_inches="tight", facecolor="white", dpi=100)
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
}


def render_physics(subtype: str, params: Dict[str, Any],
                   canvas_w: int = 800, canvas_h: int = 600) -> str:
    renderer = PHYSICS_RENDERERS.get(subtype)
    if not renderer:
        raise ValueError(f"Unknown physics subtype: '{subtype}'. "
                         f"Supported: {list(PHYSICS_RENDERERS.keys())}")
    return renderer(params, canvas_w=canvas_w, canvas_h=canvas_h)
