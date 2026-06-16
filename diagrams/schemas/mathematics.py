"""
Pydantic schemas for Mathematics diagram types.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel, Field, field_validator


# ── Function Graph ─────────────────────────────────────────────────────────────

class FunctionSpec(BaseModel):
    expression: str        # e.g. "x**2", "sin(x)", "exp(-x)"
    label: Optional[str] = None
    color: str = "black"
    x_range: Optional[Tuple[float, float]] = None   # uses parent x_range if None
    line_style: Optional[str] = None   # None = auto-assign by position; "solid"|"dashed"|"dotted"|"dashdot"
    line_width: float = Field(default=2.0, ge=0.5, le=6.0)


class FunctionGraphSchema(BaseModel):
    functions: List[FunctionSpec] = Field(default_factory=list)
    x_range: Tuple[float, float] = (-5.0, 5.0)
    y_range: Optional[Tuple[float, float]] = None   # auto if None
    x_label: str = "x"
    y_label: str = "y"
    title: str = ""
    grid: bool = True
    show_axes: bool = True
    special_points: List[Dict] = Field(default_factory=list)  # {"x": ..., "y": ..., "label": ...}
    # Intersection detection
    show_intersections: bool = True      # auto-find + mark where curves cross
    intersection_labels: bool = True     # show x-coordinate at each intersection
    # Axis formatting
    pi_axis: bool = False                # force π-based tick labels (auto-detected if False)
    x_ticks: Optional[List[float]] = None   # explicit tick positions (overrides auto)

    @field_validator("functions")
    @classmethod
    def at_least_one(cls, v):
        if not v:
            raise ValueError("At least one function is required")
        return v


# ── Geometry: Triangle ────────────────────────────────────────────────────────

class TriangleVertex(BaseModel):
    label: str = ""
    x: float
    y: float


class TriangleSide(BaseModel):
    label: str = ""
    length: Optional[float] = None


class GeometryTriangleSchema(BaseModel):
    vertices: List[TriangleVertex] = Field(min_length=3, max_length=3)
    sides: List[TriangleSide] = Field(default_factory=list)
    angles: List[Optional[float]] = Field(default_factory=list)    # in degrees
    show_angle_arcs: bool = True
    show_right_angle: bool = False
    title: str = ""
    fill_color: str = "none"
    stroke_color: str = "black"


# ── Geometry: Circle ──────────────────────────────────────────────────────────

class GeometryCircleSchema(BaseModel):
    center_label: str = "O"
    radius_label: str = "r"
    show_radius: bool = True
    show_diameter: bool = False
    show_chord: bool = False
    chord_label: str = ""
    tangent_point_label: Optional[str] = None
    show_tangent: bool = False
    arc_angle: Optional[float] = None    # highlight an arc sector


# ── Coordinate Geometry ───────────────────────────────────────────────────────

class CoordPoint(BaseModel):
    x: float
    y: float
    label: str = ""
    show_dot: bool = True
    label_offset: Tuple[float, float] = (6.0, 6.0)   # points offset for annotation


class CoordLine(BaseModel):
    slope: Optional[float] = None
    intercept: Optional[float] = 0.0
    label: str = ""
    line_style: str = "solid"    # solid | dashed | dotted
    # OR two-point form
    x1: Optional[float] = None
    y1: Optional[float] = None
    x2: Optional[float] = None
    y2: Optional[float] = None


class CoordVector(BaseModel):
    """Arrow from (from_x, from_y) → (to_x, to_y) with optional label."""
    from_x: float
    from_y: float
    to_x: float
    to_y: float
    label: str = ""
    label_position: str = "middle"  # middle | end | start


class CoordinateGeometrySchema(BaseModel):
    points: List[CoordPoint] = Field(default_factory=list)
    lines: List[CoordLine] = Field(default_factory=list)
    vectors: List[CoordVector] = Field(default_factory=list)
    x_range: Tuple[float, float] = (-10.0, 10.0)
    y_range: Tuple[float, float] = (-10.0, 10.0)
    grid: bool = True
    title: str = ""
    # Auto-compute and mark all line-line intersections
    show_line_intersections: bool = True
    intersection_label: str = "P"   # label for the computed intersection point
    # Merge point labels when a named point coincides with the intersection
    merge_coincident_labels: bool = True


# ── Calculus Graph ────────────────────────────────────────────────────────────

class ShadedRegion(BaseModel):
    x_from: float
    x_to: float
    label: Optional[str] = None
    color: str = "lightgray"
    alpha: float = Field(default=0.4, ge=0.0, le=1.0)


class CalculusGraphSchema(BaseModel):
    function: str                     # e.g. "x**2 - 4"
    x_range: Tuple[float, float] = (-5.0, 5.0)
    y_range: Optional[Tuple[float, float]] = None
    shaded_regions: List[ShadedRegion] = Field(default_factory=list)
    show_derivative: bool = False
    show_tangent_at: Optional[float] = None   # x-value
    label_zeros: bool = True
    label_extrema: bool = True
    x_label: str = "x"
    y_label: str = "f(x)"
    title: str = ""
    grid: bool = True


# ── Conic Section ─────────────────────────────────────────────────────────────

class ConicSectionSchema(BaseModel):
    conic_type: str = "ellipse"   # ellipse | parabola | hyperbola | circle
    a: float = Field(default=4.0, ge=0.1)   # semi-major axis (ellipse/hyperbola) or focal param (parabola)
    b: float = Field(default=2.0, ge=0.1)   # semi-minor axis (ellipse/hyperbola); unused for parabola
    center_x: float = 0.0
    center_y: float = 0.0
    orientation: str = "horizontal"   # horizontal | vertical
    show_foci: bool = True
    show_vertices: bool = True
    show_directrix: bool = True    # for parabola
    show_asymptotes: bool = True   # for hyperbola
    label_foci: bool = True
    title: str = ""


# ── Venn Diagram ──────────────────────────────────────────────────────────────

class VennSet(BaseModel):
    label: str = ""
    region_value: Optional[str] = None   # text inside exclusive region


class VennDiagramSchema(BaseModel):
    sets: List[VennSet] = Field(min_length=2, max_length=3)
    intersection_labels: List[str] = Field(default_factory=list)   # for each intersection region
    universal_set_label: str = ""
    title: str = ""


# ── Number Line ───────────────────────────────────────────────────────────────

class NumberLinePoint(BaseModel):
    value: float
    label: str = ""
    filled: bool = True   # True = closed (included), False = open (excluded)


class NumberLineInterval(BaseModel):
    start: float
    end: float
    filled_start: bool = True
    filled_end: bool = True
    color: str = "black"


class NumberLineSchema(BaseModel):
    x_min: float = -5.0
    x_max: float = 5.0
    points: List[NumberLinePoint] = Field(default_factory=list)
    intervals: List[NumberLineInterval] = Field(default_factory=list)
    title: str = ""
    axis_label: str = "x"


# ── Bar Chart / Histogram ─────────────────────────────────────────────────────

class BarChartBar(BaseModel):
    label: str
    value: float
    color: str = ""   # auto if empty


class BarChartSchema(BaseModel):
    bars: List[BarChartBar] = Field(min_length=1)
    chart_type: str = "bar"      # bar | histogram
    x_label: str = ""
    y_label: str = "Value"
    show_values: bool = True     # display value on top of each bar
    show_grid: bool = True
    color_scheme: str = "default"  # default | blue | rainbow
    title: str = ""


# ── Scatter Plot with Regression Line ────────────────────────────────────────

class ScatterPoint(BaseModel):
    x: float
    y: float
    label: str = ""


class ScatterPlotSchema(BaseModel):
    points: List[ScatterPoint] = Field(min_length=2)
    show_regression_line: bool = True
    regression_degree: int = Field(default=1, ge=1, le=3)  # 1=linear, 2=quadratic, 3=cubic
    show_r_squared: bool = True
    show_grid: bool = True
    x_label: str = "x"
    y_label: str = "y"
    point_color: str = "steelblue"
    line_color: str = "red"
    title: str = ""


# ── 3D Vector Diagram ─────────────────────────────────────────────────────────

class Vector3D(BaseModel):
    x: float
    y: float
    z: float
    label: str = ""
    color: str = "blue"
    origin_x: float = 0.0
    origin_y: float = 0.0
    origin_z: float = 0.0


class Vector3DSchema(BaseModel):
    vectors: List[Vector3D] = Field(min_length=1, max_length=6)
    show_axes: bool = True
    show_grid: bool = True
    show_projections: bool = False   # draw dashed projections onto xy-plane
    axis_labels: List[str] = Field(default_factory=lambda: ["x", "y", "z"])
    show_angle_between: bool = False  # annotate angle between first two vectors
    title: str = ""
