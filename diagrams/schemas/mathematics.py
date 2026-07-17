"""
Pydantic schemas for Mathematics diagram types.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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


# ── Pie Chart ─────────────────────────────────────────────────────────────────

class PieSlice(BaseModel):
    label: str
    value: float = Field(gt=0)   # slice magnitude (any positive number)
    color: Optional[str] = None  # auto-assigned from palette if None


class PieChartSchema(BaseModel):
    slices: List[PieSlice] = Field(min_length=2)
    show_percentages: bool = True    # label each slice with its % of total
    show_values: bool = False        # label each slice with its raw value
    show_legend: bool = True         # legend beside chart (else labels on slices)
    explode_slice: Optional[str] = None   # label of one slice to pull out
    title: str = ""

    @field_validator("slices")
    @classmethod
    def at_least_two_positive(cls, v):
        if len(v) < 2:
            raise ValueError("A pie chart needs at least 2 slices")
        return v


# ── Line Chart (data-interpretation / time-series) ────────────────────────────

class LineChartPoint(BaseModel):
    x: float
    y: float


class LineChartSeries(BaseModel):
    label: str = ""
    points: List[LineChartPoint] = Field(min_length=2)
    color: Optional[str] = None      # auto-assigned from palette if None
    line_style: str = "solid"        # solid | dashed
    marker: bool = True              # draw point markers


class LineChartSchema(BaseModel):
    series: List[LineChartSeries] = Field(min_length=1)
    x_label: str = "x"
    y_label: str = "y"
    show_grid: bool = True
    show_legend: bool = True
    title: str = ""

    @field_validator("series")
    @classmethod
    def at_least_one_series(cls, v):
        if not v:
            raise ValueError("At least one series is required")
        return v


# ── 3D Solid (mensuration figure) ─────────────────────────────────────────────

_SOLID_REQUIRED_DIMS = {
    "cube":       ["side"],
    "cuboid":     ["length", "width", "height"],
    "cone":       ["radius", "height"],
    "cylinder":   ["radius", "height"],
    "sphere":     ["radius"],
    "hemisphere": ["radius"],
    "pyramid":    ["side", "height"],                       # square-base pyramid
    "frustum":    ["radius_top", "radius_bottom", "height"],
}


class Solid3DSchema(BaseModel):
    solid_type: str   # cube | cuboid | cone | cylinder | sphere | hemisphere | pyramid | frustum
    # Dimensions (which ones are required depends on solid_type)
    side: Optional[float] = Field(default=None, gt=0)
    length: Optional[float] = Field(default=None, gt=0)
    width: Optional[float] = Field(default=None, gt=0)
    height: Optional[float] = Field(default=None, gt=0)
    radius: Optional[float] = Field(default=None, gt=0)
    slant_height: Optional[float] = Field(default=None, gt=0)   # cone/frustum annotation
    radius_top: Optional[float] = Field(default=None, gt=0)     # frustum
    radius_bottom: Optional[float] = Field(default=None, gt=0)  # frustum
    unit: str = "cm"                 # unit shown in dimension labels
    show_dimensions: bool = True     # annotate edges e.g. "r = 7 cm"
    show_hidden_edges: bool = True   # dashed back/hidden edges
    label_faces: bool = False        # letter the vertices (cube/cuboid/pyramid)
    title: str = ""

    @model_validator(mode="after")
    def check_required_dimensions(self):
        st = self.solid_type.lower().strip()
        if st not in _SOLID_REQUIRED_DIMS:
            raise ValueError(
                f"Unknown solid_type '{self.solid_type}'. "
                f"Supported: {sorted(_SOLID_REQUIRED_DIMS.keys())}"
            )
        self.solid_type = st
        missing = [f for f in _SOLID_REQUIRED_DIMS[st] if getattr(self, f) is None]
        if missing:
            raise ValueError(
                f"solid_type '{st}' requires dimension(s): {_SOLID_REQUIRED_DIMS[st]} "
                f"(missing: {missing})"
            )
        return self


# ── Argand Diagram (complex plane) ────────────────────────────────────────────

class ArgandPoint(BaseModel):
    real: float
    imag: float
    label: str = ""
    show_value: bool = True      # print "z = 3 + 4i" beside the point
    show_vector: bool = True     # arrow from the origin to z
    show_modulus: bool = False   # annotate |z| along the vector
    show_argument: bool = False  # arc from the positive real axis round to the vector


class ArgandCircle(BaseModel):
    """A locus of the form |z - centre| = radius."""
    centre_real: float = 0.0
    centre_imag: float = 0.0
    radius: float = Field(gt=0)
    label: str = ""     # e.g. "|z - 2| = 3"


_ARGAND_REGION_TYPES = {"disc", "annulus", "wedge", "half_plane"}


class ArgandRegion(BaseModel):
    region_type: str = "disc"    # disc | annulus | wedge | half_plane
    centre_real: float = 0.0
    centre_imag: float = 0.0
    radius: Optional[float] = Field(default=None, gt=0)        # disc:    |z - c| ≤ radius
    inner_radius: Optional[float] = Field(default=None, ge=0)  # annulus: inner ≤ |z - c| ≤ outer
    outer_radius: Optional[float] = Field(default=None, gt=0)
    start_angle: Optional[float] = None    # wedge: arg z from … (degrees)
    end_angle: Optional[float] = None      # wedge: … to (degrees)
    axis: str = "real"    # half_plane: "real" → Re z, "imag" → Im z
    op: str = ">="        # half_plane: ">=" | "<="
    value: float = 0.0    # half_plane: the bound, e.g. Re z ≥ 1
    label: str = ""

    @model_validator(mode="after")
    def check_region(self):
        rt = self.region_type.lower().strip()
        if rt not in _ARGAND_REGION_TYPES:
            raise ValueError(
                f"Unknown region_type '{self.region_type}'. "
                f"Supported: {sorted(_ARGAND_REGION_TYPES)}"
            )
        self.region_type = rt
        if rt == "disc" and self.radius is None:
            raise ValueError("region_type 'disc' requires 'radius'")
        if rt == "annulus":
            if self.inner_radius is None or self.outer_radius is None:
                raise ValueError("region_type 'annulus' requires 'inner_radius' and 'outer_radius'")
            if self.outer_radius <= self.inner_radius:
                raise ValueError("annulus outer_radius must exceed inner_radius")
        if rt == "wedge" and (self.start_angle is None or self.end_angle is None):
            raise ValueError("region_type 'wedge' requires 'start_angle' and 'end_angle' (degrees)")
        if rt == "half_plane":
            if self.axis.lower().strip() not in ("real", "imag"):
                raise ValueError("half_plane 'axis' must be 'real' or 'imag'")
            self.axis = self.axis.lower().strip()
            if self.op not in ("<=", ">="):
                raise ValueError("half_plane 'op' must be '<=' or '>='")
        return self


class ArgandDiagramSchema(BaseModel):
    points: List[ArgandPoint] = Field(default_factory=list)
    circles: List[ArgandCircle] = Field(default_factory=list)
    regions: List[ArgandRegion] = Field(default_factory=list)
    # nth roots of unity are generated in the renderer, never taken from params
    roots_of_unity: Optional[int] = Field(default=None, ge=2, le=12)
    show_unit_circle: bool = False
    show_axes_labels: bool = True          # "Re" / "Im" instead of x / y
    show_modulus_argument: bool = False    # annotate |z| and arg z on every point
    show_grid: bool = True
    title: str = ""

    @model_validator(mode="after")
    def needs_content(self):
        if not (self.points or self.circles or self.regions or self.roots_of_unity):
            raise ValueError(
                "argand_diagram needs at least one of: points, circles, regions, roots_of_unity"
            )
        return self


# ── Linear Programming ────────────────────────────────────────────────────────

_LP_OPS = {"<=", ">=", "=", "==", "<", ">"}


class LPConstraint(BaseModel):
    """a·x + b·y  op  c. Supply either `expression` ("2x + 3y <= 12") or a/b/op/c."""
    expression: Optional[str] = None
    a: Optional[float] = None
    b: Optional[float] = None
    op: str = "<="
    c: Optional[float] = None
    label: str = ""

    @model_validator(mode="after")
    def check_form(self):
        if self.expression is None:
            if self.a is None or self.b is None or self.c is None:
                raise ValueError(
                    "A constraint needs either 'expression' or all of 'a', 'b', 'c'"
                )
            if self.op not in _LP_OPS:
                raise ValueError(f"Unknown constraint op '{self.op}'. Supported: {sorted(_LP_OPS)}")
            if abs(self.a) < 1e-12 and abs(self.b) < 1e-12:
                raise ValueError("A constraint must involve x or y (a and b cannot both be 0)")
        return self


class LPObjective(BaseModel):
    a: float
    b: float
    label: str = "Z"


class LinearProgrammingSchema(BaseModel):
    constraints: List[LPConstraint] = Field(min_length=1)
    objective: Optional[LPObjective] = None      # Z = a·x + b·y
    x_range: Optional[Tuple[float, float]] = None   # auto-fitted to the region if None
    y_range: Optional[Tuple[float, float]] = None
    non_negative: bool = True        # implicit x ≥ 0, y ≥ 0
    show_feasible_region: bool = True
    show_corner_points: bool = True  # corners are computed, never supplied
    show_objective_line: bool = True
    maximise: bool = True            # False → minimise
    show_grid: bool = True
    x_label: str = "x"
    y_label: str = "y"
    title: str = ""


# ── Histogram / Ogive (grouped-frequency statistics) ──────────────────────────

class ClassInterval(BaseModel):
    lower: float
    upper: float
    frequency: float = Field(ge=0)

    @model_validator(mode="after")
    def check_bounds(self):
        if self.upper <= self.lower:
            raise ValueError(
                f"Class interval upper ({self.upper}) must exceed lower ({self.lower})"
            )
        return self


_HISTOGRAM_OVERLAYS = {
    "none", "frequency_polygon", "ogive_less_than", "ogive_more_than", "both_ogives",
}


def _bin_raw_data(values: List[float], bins: int) -> List[ClassInterval]:
    """Equal-width binning of raw observations; the top bin includes the maximum."""
    lo, hi = min(values), max(values)
    if hi == lo:
        hi = lo + 1.0
    width = (hi - lo) / bins
    intervals: List[ClassInterval] = []
    for i in range(bins):
        b_lo = lo + i * width
        b_hi = b_lo + width
        if i == bins - 1:
            freq = sum(1 for v in values if b_lo <= v <= b_hi)   # top bin is closed
        else:
            freq = sum(1 for v in values if b_lo <= v < b_hi)
        intervals.append(ClassInterval(lower=b_lo, upper=b_hi, frequency=freq))
    return intervals


class HistogramSchema(BaseModel):
    class_intervals: List[ClassInterval] = Field(default_factory=list)
    data: List[float] = Field(default_factory=list)   # raw observations, binned if no class_intervals
    bins: int = Field(default=5, ge=2, le=20)
    overlay: str = "none"   # none | frequency_polygon | ogive_less_than | ogive_more_than | both_ogives
    show_mode_construction: bool = False     # the two diagonals in the modal class
    show_median_from_ogive: bool = False     # perpendicular from N/2 on the less-than ogive
    # Inclusive classes (10–19, 20–29) have gaps; the true boundaries sit at the gap midpoints
    # and every plotted position (bar edge, midpoint, ogive x) must use the corrected boundary.
    continuity_correction: bool = True
    show_values: bool = False
    show_grid: bool = True
    x_label: str = "Class"
    y_label: str = "Frequency"
    title: str = ""

    @model_validator(mode="after")
    def build_and_check(self):
        ov = self.overlay.lower().strip()
        if ov not in _HISTOGRAM_OVERLAYS:
            raise ValueError(
                f"Unknown overlay '{self.overlay}'. Supported: {sorted(_HISTOGRAM_OVERLAYS)}"
            )
        self.overlay = ov

        if not self.class_intervals:
            if not self.data:
                raise ValueError("histogram needs either 'class_intervals' or 'data'")
            self.class_intervals = _bin_raw_data(self.data, self.bins)

        self.class_intervals = sorted(self.class_intervals, key=lambda ci: ci.lower)
        for prev, nxt in zip(self.class_intervals, self.class_intervals[1:]):
            if nxt.lower < prev.upper - 1e-9:
                raise ValueError(
                    f"Class intervals must not overlap: [{prev.lower}, {prev.upper}] "
                    f"overlaps [{nxt.lower}, {nxt.upper}]"
                )
        if sum(ci.frequency for ci in self.class_intervals) <= 0:
            raise ValueError("Total frequency must be positive")
        return self


# ── Probability Tree ──────────────────────────────────────────────────────────

_TREE_MAX_DEPTH = 4
_TREE_PROB_TOL = 1e-6


class TreeBranch(BaseModel):
    label: str = ""
    probability: float = Field(ge=0.0, le=1.0)
    outcome: str = ""     # leaf-only outcome text; defaults to the joined path labels
    children: List["TreeBranch"] = Field(default_factory=list)


TreeBranch.model_rebuild()


def _check_sibling_sum(siblings: List[TreeBranch], path: str, depth: int) -> None:
    """Sibling probabilities must sum to 1 — a tree that doesn't is a broken question."""
    total = sum(b.probability for b in siblings)
    if abs(total - 1.0) > _TREE_PROB_TOL:
        where = path or "root"
        raise ValueError(
            f"Sibling branch probabilities must sum to 1 at '{where}', got {total:g} "
            f"({[b.probability for b in siblings]})"
        )
    if depth > _TREE_MAX_DEPTH:
        raise ValueError(f"probability_tree depth exceeds the limit of {_TREE_MAX_DEPTH}")
    for b in siblings:
        if b.children:
            _check_sibling_sum(b.children, f"{path}/{b.label}" if path else b.label, depth + 1)


class ProbabilityTreeSchema(BaseModel):
    branches: List[TreeBranch] = Field(min_length=1)
    show_probabilities: bool = True           # probability on each edge
    show_outcome_probabilities: bool = True   # product along the path, printed at the leaf
    show_outcomes: bool = True                # leaf outcome labels
    highlight_paths: List[List[str]] = Field(default_factory=list)  # e.g. [["R", "R"]]
    title: str = ""

    @model_validator(mode="after")
    def check_probabilities(self):
        _check_sibling_sum(self.branches, "", 1)
        return self


# ── Height & Distance (angle of elevation / depression) ───────────────────────

_HD_SCENARIOS = {"elevation", "depression", "both", "tower_and_building"}


class HDObserver(BaseModel):
    label: str = "Observer"
    height: float = Field(default=0.0, ge=0.0)   # eye level above the ground


class HDObject(BaseModel):
    """Two of (height, distance, angle) fix the triangle; the renderer derives the third."""
    label: str = ""
    height: Optional[float] = Field(default=None, gt=0)     # top of the object above the ground
    distance: Optional[float] = Field(default=None, gt=0)   # horizontal distance from the observer
    angle_of_elevation: Optional[float] = Field(default=None, gt=0, lt=90)
    angle_of_depression: Optional[float] = Field(default=None, gt=0, lt=90)


class HeightDistanceSchema(BaseModel):
    objects: List[HDObject] = Field(min_length=1, max_length=3)
    observer: HDObserver = Field(default_factory=HDObserver)
    scenario: str = "elevation"   # elevation | depression | both | tower_and_building
    ground_label: str = ""
    unit: str = "m"
    show_angles: bool = True          # arc + degree label at the observer's eye
    show_right_angles: bool = True
    show_dimensions: bool = True      # label the horizontal distance and the vertical height
    title: str = ""

    @model_validator(mode="after")
    def check_scenario_and_solvability(self):
        sc = self.scenario.lower().strip()
        if sc not in _HD_SCENARIOS:
            raise ValueError(
                f"Unknown scenario '{self.scenario}'. Supported: {sorted(_HD_SCENARIOS)}"
            )
        self.scenario = sc
        if sc in ("depression", "both", "tower_and_building") and self.observer.height <= 0:
            raise ValueError(
                f"scenario '{sc}' looks down from somewhere — set observer.height > 0"
            )
        for i, ob in enumerate(self.objects):
            name = ob.label or f"object {i + 1}"
            elev, dep = ob.angle_of_elevation, ob.angle_of_depression
            if elev is not None and dep is not None:
                continue    # the depression fixes the distance, the elevation then fixes the top
            if elev is not None:
                if ob.height is None and ob.distance is None:
                    raise ValueError(
                        f"{name}: an angle of elevation on its own does not fix a triangle — "
                        f"add 'distance' or 'height'"
                    )
            elif dep is not None:
                if ob.height is None and ob.distance is None and self.observer.height <= 0:
                    raise ValueError(
                        f"{name}: an angle of depression needs an elevated observer, "
                        f"a distance or a height"
                    )
            elif ob.height is None or ob.distance is None:
                raise ValueError(
                    f"{name}: give two of height / distance / angle — one measurement "
                    f"cannot fix a triangle"
                )
        return self


# ── Combined Solid (two or more solids joined) ────────────────────────────────

_COMBINED_REQUIRED_DIMS = {
    "cube":       ["side"],
    "cuboid":     ["length", "width", "height"],
    "cone":       ["radius", "height"],
    "cylinder":   ["radius", "height"],
    "sphere":     ["radius"],
    "hemisphere": ["radius"],
    "frustum":    ["radius_top", "radius_bottom", "height"],
}
_ARRANGEMENTS = {"stacked_vertical", "side_by_side", "inscribed", "hollowed_out"}
_JOIN_TOL = 1e-6


class SolidComponent(BaseModel):
    solid_type: str   # cone | cylinder | hemisphere | cube | cuboid | frustum | sphere
    radius: Optional[float] = Field(default=None, gt=0)
    height: Optional[float] = Field(default=None, gt=0)
    side: Optional[float] = Field(default=None, gt=0)
    length: Optional[float] = Field(default=None, gt=0)
    width: Optional[float] = Field(default=None, gt=0)
    radius_top: Optional[float] = Field(default=None, gt=0)     # frustum
    radius_bottom: Optional[float] = Field(default=None, gt=0)  # frustum
    # A supplied slant height is ignored: l is recomputed from r and h, because πrl is only the
    # curved surface area for the l that actually belongs to that cone.
    slant_height: Optional[float] = Field(default=None, gt=0)
    label: str = ""

    @model_validator(mode="after")
    def check_dimensions(self):
        st = self.solid_type.lower().strip()
        if st not in _COMBINED_REQUIRED_DIMS:
            raise ValueError(
                f"Unknown solid_type '{self.solid_type}'. "
                f"Supported: {sorted(_COMBINED_REQUIRED_DIMS.keys())}"
            )
        self.solid_type = st
        if st == "frustum" and self.radius_bottom is None and self.radius is not None:
            self.radius_bottom = self.radius       # a bare 'radius' reads as the base radius
        missing = [f for f in _COMBINED_REQUIRED_DIMS[st] if getattr(self, f) is None]
        if missing:
            raise ValueError(
                f"solid_type '{st}' requires dimension(s): {_COMBINED_REQUIRED_DIMS[st]} "
                f"(missing: {missing})"
            )
        if st == "frustum" and self.radius_top >= self.radius_bottom:
            raise ValueError("frustum radius_top must be smaller than radius_bottom")
        return self


def _cs_flipped(index: int, count: int, solid_type: str, arrangement: str) -> bool:
    """
    A cone or a hemisphere at the BOTTOM of a stack is inverted so its one flat face meets the
    solid above it: an ice-cream cone points down, a toy's hemisphere is a bowl under the cone.
    """
    return (arrangement == "stacked_vertical" and index == 0 and count > 1
            and solid_type in ("cone", "hemisphere"))


def _cs_face(c: SolidComponent, face: str, flipped: bool) -> Optional[Dict[str, Any]]:
    """
    The flat face a component presents at its `face` ("top" | "bottom") end, or None when that
    end is curved — a dome, an apex or a sphere glues to nothing and hides no area.
    """
    st = c.solid_type
    if st == "cylinder":
        return {"kind": "circle", "r": c.radius, "area": math.pi * c.radius ** 2}
    if st in ("cone", "hemisphere"):
        if face != ("top" if flipped else "bottom"):
            return None
        return {"kind": "circle", "r": c.radius, "area": math.pi * c.radius ** 2}
    if st == "frustum":
        r = c.radius_top if face == "top" else c.radius_bottom
        return {"kind": "circle", "r": r, "area": math.pi * r ** 2}
    if st == "cube":
        return {"kind": "rect", "w": c.side, "d": c.side, "area": c.side ** 2}
    if st == "cuboid":
        return {"kind": "rect", "w": c.length, "d": c.width, "area": c.length * c.width}
    return None    # a sphere rests on a single point


def _check_flush_joint(lower: SolidComponent, upper: SolidComponent,
                       top: Dict[str, Any], bottom: Dict[str, Any], i: int) -> None:
    """A solid that overhangs the one it stands on, or floats on a rim of the wrong size,
    is a broken figure — and its combined surface area would be a fiction."""
    where = (f"component {i + 1} ({lower.solid_type}) and component {i + 2} "
             f"({upper.solid_type})")
    if top["kind"] == "circle" and bottom["kind"] == "circle":
        if abs(top["r"] - bottom["r"]) > _JOIN_TOL:
            raise ValueError(
                f"{where} must share the joining radius to sit flush: "
                f"{top['r']:g} ≠ {bottom['r']:g}"
            )
        return
    if top["kind"] == "rect" and bottom["kind"] == "rect":
        if bottom["w"] > top["w"] + _JOIN_TOL or bottom["d"] > top["d"] + _JOIN_TOL:
            raise ValueError(f"{where}: the upper solid overhangs the face it stands on")
        return
    circle = top if top["kind"] == "circle" else bottom
    rect = top if top["kind"] == "rect" else bottom
    if circle["r"] > min(rect["w"], rect["d"]) / 2 + _JOIN_TOL:
        raise ValueError(
            f"{where}: a circular face of radius {circle['r']:g} does not fit on a "
            f"{rect['w']:g} × {rect['d']:g} face"
        )


class CombinedSolidSchema(BaseModel):
    components: List[SolidComponent] = Field(min_length=2, max_length=3)   # ordered bottom → top
    arrangement: str = "stacked_vertical"  # stacked_vertical | side_by_side | inscribed | hollowed_out
    unit: str = "cm"
    show_dimensions: bool = True
    show_hidden_edges: bool = True
    show_total_surface_area: bool = False   # computed, never supplied
    show_volume: bool = False               # computed, never supplied
    title: str = ""

    @model_validator(mode="after")
    def check_arrangement_and_joints(self):
        ar = self.arrangement.lower().strip()
        if ar not in _ARRANGEMENTS:
            raise ValueError(
                f"Unknown arrangement '{self.arrangement}'. Supported: {sorted(_ARRANGEMENTS)}"
            )
        self.arrangement = ar
        n = len(self.components)
        if ar in ("inscribed", "hollowed_out") and n != 2:
            raise ValueError(
                f"arrangement '{ar}' takes exactly 2 components (outer, inner), got {n}"
            )
        if ar == "stacked_vertical":
            for i in range(n - 1):
                lower, upper = self.components[i], self.components[i + 1]
                top = _cs_face(lower, "top", _cs_flipped(i, n, lower.solid_type, ar))
                bottom = _cs_face(upper, "bottom", _cs_flipped(i + 1, n, upper.solid_type, ar))
                if top is None or bottom is None:
                    continue    # a dome or a sphere touches its neighbour at one point
                _check_flush_joint(lower, upper, top, bottom, i)
        return self


# ── 3D Coordinate Geometry: planes and lines ──────────────────────────────────

class Plane3D(BaseModel):
    """ax + by + cz = d."""
    model_config = ConfigDict(populate_by_name=True)

    a: float
    b: float
    c: float
    d: float = 0.0
    label: str = ""
    colour: str = Field(default="", alias="color")

    @model_validator(mode="after")
    def check_normal(self):
        if math.sqrt(self.a ** 2 + self.b ** 2 + self.c ** 2) < 1e-9:
            raise ValueError("A plane needs a non-zero normal (a, b, c cannot all be 0)")
        return self


class Line3D(BaseModel):
    """Vector form r = point + λ·direction."""
    model_config = ConfigDict(populate_by_name=True)

    point: Tuple[float, float, float]
    direction: Tuple[float, float, float]
    label: str = ""
    colour: str = Field(default="", alias="color")

    @model_validator(mode="after")
    def check_direction(self):
        if math.sqrt(sum(v ** 2 for v in self.direction)) < 1e-9:
            raise ValueError("A line needs a non-zero direction vector")
        return self


class Point3D(BaseModel):
    x: float
    y: float
    z: float
    label: str = ""


class PlaneLine3DSchema(BaseModel):
    planes: List[Plane3D] = Field(default_factory=list, max_length=3)
    lines: List[Line3D] = Field(default_factory=list, max_length=3)
    points: List[Point3D] = Field(default_factory=list, max_length=4)
    show_normals: bool = False       # normal vector to each plane
    show_intersection: bool = False  # plane ∩ plane, and where a line pierces a plane
    show_angle: bool = False         # between two planes, or a line and a plane
    show_distance: bool = False      # perpendicular distance from each point to each plane
    show_axes: bool = True
    title: str = ""

    @model_validator(mode="after")
    def needs_content(self):
        if not (self.planes or self.lines or self.points):
            raise ValueError("plane_line_3d needs at least one plane, line or point")
        return self


# ── Distribution Curve (probability / statistics) ─────────────────────────────

_DISTRIBUTIONS = {"normal", "standard_normal", "binomial", "poisson", "t"}
_DISCRETE_DISTRIBUTIONS = {"binomial", "poisson"}


class DistributionParameters(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    mean: Optional[float] = None
    std_dev: Optional[float] = Field(default=None, gt=0)
    n: Optional[int] = Field(default=None, ge=1, le=200)
    p: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    lambda_: Optional[float] = Field(default=None, alias="lambda", gt=0)
    df: Optional[float] = Field(default=None, gt=0)     # t: degrees of freedom


class DistributionRegion(BaseModel):
    """An open bound means a tail: {"from": 2} is P(X ≥ 2), {"to": 2} is P(X ≤ 2)."""
    model_config = ConfigDict(populate_by_name=True)

    from_value: Optional[float] = Field(default=None, alias="from")
    to_value: Optional[float] = Field(default=None, alias="to")
    label: str = ""

    @model_validator(mode="after")
    def check_bounds(self):
        if self.from_value is None and self.to_value is None:
            raise ValueError("A shaded region needs at least one of 'from' / 'to'")
        if (self.from_value is not None and self.to_value is not None
                and self.to_value < self.from_value):
            raise ValueError(
                f"Shaded region 'to' ({self.to_value:g}) must not be below "
                f"'from' ({self.from_value:g})"
            )
        return self


class DistributionCurveSchema(BaseModel):
    distribution: str = "normal"   # normal | standard_normal | binomial | poisson | t
    parameters: DistributionParameters = Field(default_factory=DistributionParameters)
    shaded_regions: List[DistributionRegion] = Field(default_factory=list)
    show_mean_line: bool = True
    show_sd_lines: bool = False     # ±1σ, ±2σ, ±3σ with the 68 / 95 / 99.7 annotations
    show_area_value: bool = True    # the shaded probability, integrated/summed in code
    overlay_normal: bool = False    # binomial/poisson → normal approximation
    x_label: str = ""               # defaults per distribution ("k" discrete, "x" continuous)
    y_label: str = ""
    show_grid: bool = True
    title: str = ""

    @model_validator(mode="after")
    def check_parameters(self):
        dist = self.distribution.lower().strip()
        if dist not in _DISTRIBUTIONS:
            raise ValueError(
                f"Unknown distribution '{self.distribution}'. Supported: {sorted(_DISTRIBUTIONS)}"
            )
        self.distribution = dist
        p = self.parameters
        if dist == "standard_normal":
            p.mean, p.std_dev = 0.0, 1.0     # Z is N(0, 1) by definition, whatever was supplied
        elif dist == "normal":
            if p.mean is None or p.std_dev is None:
                raise ValueError("distribution 'normal' requires parameters.mean and .std_dev")
        elif dist == "binomial":
            if p.n is None or p.p is None:
                raise ValueError("distribution 'binomial' requires parameters.n and .p")
        elif dist == "poisson":
            if p.lambda_ is None:
                raise ValueError("distribution 'poisson' requires parameters.lambda")
        elif dist == "t":
            if p.df is None:
                raise ValueError("distribution 't' requires parameters.df (degrees of freedom)")
        if self.overlay_normal and dist not in _DISCRETE_DISTRIBUTIONS:
            raise ValueError(
                "overlay_normal is the normal approximation to a DISCRETE distribution — "
                "it only applies to binomial or poisson"
            )
        return self


# ── Piecewise Graph (continuity / differentiability) ──────────────────────────

class PiecewisePiece(BaseModel):
    """One branch f(x) = <expression> valid on [lo, hi]. The endpoints' closedness is what a
    continuity question turns on, so it is explicit and never guessed from the neighbours."""
    expression: str                    # in x, e.g. "x**2", "2*x + 1", "3"
    domain: Tuple[float, float]        # [lo, hi] over which this branch applies
    closed_left: bool = True           # is the lo endpoint included (●) or excluded (○)
    closed_right: bool = False         # is the hi endpoint included (●) or excluded (○)

    @model_validator(mode="after")
    def check_domain(self):
        if self.domain[1] <= self.domain[0]:
            raise ValueError(
                f"piece domain hi ({self.domain[1]}) must exceed lo ({self.domain[0]})"
            )
        return self


class PiecewiseGraphSchema(BaseModel):
    pieces: List[PiecewisePiece] = Field(min_length=1)
    show_open_closed_points: bool = True   # ● included / ○ excluded circles at every boundary
    check_points: List[float] = Field(default_factory=list)  # x-values to mark and test
    show_continuity: bool = True           # classify each interior boundary (jump / removable / OK)
    x_label: str = "x"
    y_label: str = "y"
    title: str = ""
    grid: bool = True

    @model_validator(mode="after")
    def order_pieces(self):
        self.pieces = sorted(self.pieces, key=lambda p: p.domain[0])
        return self


# ── Circle Theorem ────────────────────────────────────────────────────────────

_CIRCLE_THEOREMS = {
    "angle_at_centre", "angle_in_semicircle", "cyclic_quadrilateral",
    "tangent_radius", "alternate_segment", "equal_chords", "intersecting_chords",
}


class CircleTheoremSchema(BaseModel):
    theorem: str = "angle_at_centre"
    # Positions of the named points on the circle, in DEGREES around the centre. Sensible
    # per-theorem defaults are supplied by the renderer when these are omitted; the actual
    # angles the theorem relates are COMPUTED from whatever positions are used, never trusted.
    point_angles: List[float] = Field(default_factory=list)
    center_label: str = "O"
    show_values: bool = True     # print the computed angle(s) the theorem relates
    title: str = ""

    @model_validator(mode="after")
    def check_theorem(self):
        th = self.theorem.lower().strip()
        if th not in _CIRCLE_THEOREMS:
            raise ValueError(
                f"Unknown theorem '{self.theorem}'. Supported: {sorted(_CIRCLE_THEOREMS)}"
            )
        self.theorem = th
        return self


# ── Similar Triangles ─────────────────────────────────────────────────────────

_SIMILAR_CONFIGS = {
    "basic_proportionality", "aa_similarity", "midpoint_theorem", "pythagoras_geometric",
}


class SimilarTrianglesSchema(BaseModel):
    configuration: str = "basic_proportionality"
    # Triangle ABC apex/base. Defaults per configuration; the ratios/lengths the figure
    # asserts are COMPUTED from these coordinates, never supplied.
    A: Tuple[float, float] = (2.0, 6.0)
    B: Tuple[float, float] = (0.0, 0.0)
    C: Tuple[float, float] = (7.0, 0.0)
    # BPT / midpoint: where D sits on AB and E on AC, as a fraction AD/AB (== AE/AC for a
    # line parallel to BC). Midpoint theorem forces 0.5. Ignored by aa/pythagoras.
    division_ratio: float = Field(default=0.4, gt=0.0, lt=1.0)
    show_ratios: bool = True        # label AD/DB = AE/EC (computed)
    show_parallel_marks: bool = True
    show_angle_arcs: bool = True
    title: str = ""

    @model_validator(mode="after")
    def check_config(self):
        cfg = self.configuration.lower().strip()
        if cfg not in _SIMILAR_CONFIGS:
            raise ValueError(
                f"Unknown configuration '{self.configuration}'. "
                f"Supported: {sorted(_SIMILAR_CONFIGS)}"
            )
        self.configuration = cfg
        return self


# ── Geometric Construction (ruler-and-compass) ────────────────────────────────

_CONSTRUCTIONS = {
    "angle_bisector", "perpendicular_bisector", "angle_60", "angle_30",
    "triangle_sss", "tangent_to_circle", "divide_segment",
}


class GeometricConstructionSchema(BaseModel):
    construction: str = "angle_bisector"
    # Parameters used per construction; unused ones are ignored:
    angle: float = Field(default=70.0, gt=0.0, lt=180.0)   # angle_bisector: the angle to bisect
    segment_length: float = Field(default=6.0, gt=0.0)     # perp_bisector / divide_segment / base
    divisions: int = Field(default=5, ge=2, le=12)         # divide_segment: n equal parts
    # triangle_sss side lengths a=BC, b=CA, c=AB
    side_a: float = Field(default=6.0, gt=0.0)
    side_b: float = Field(default=5.0, gt=0.0)
    side_c: float = Field(default=4.0, gt=0.0)
    circle_radius: float = Field(default=2.5, gt=0.0)      # tangent_to_circle
    external_distance: float = Field(default=6.0, gt=0.0)  # tangent_to_circle: |OP|
    show_construction_arcs: bool = True    # the compass marks the examiner looks for
    show_labels: bool = True
    title: str = ""

    @model_validator(mode="after")
    def check_construction(self):
        c = self.construction.lower().strip()
        if c not in _CONSTRUCTIONS:
            raise ValueError(
                f"Unknown construction '{self.construction}'. Supported: {sorted(_CONSTRUCTIONS)}"
            )
        self.construction = c
        if c == "triangle_sss":
            a, b, cc = self.side_a, self.side_b, self.side_c
            if a + b <= cc or b + cc <= a or a + cc <= b:
                raise ValueError(
                    f"triangle_sss sides {a}, {b}, {cc} violate the triangle inequality — "
                    f"no triangle can be constructed"
                )
        if c == "tangent_to_circle" and self.external_distance <= self.circle_radius:
            raise ValueError(
                "tangent_to_circle needs the point OUTSIDE the circle "
                "(external_distance > circle_radius)"
            )
        return self


# ── Solid of Revolution (volume of revolution figure) ─────────────────────────

class SolidOfRevolutionSchema(BaseModel):
    expression: str                     # generating curve y = f(x), in x, via parse_safe
    x_range: Tuple[float, float] = (0.0, 3.0)
    axis: str = "x"                     # x | y — axis the curve is rotated about
    show_disc: bool = True              # a representative disc/shell element for the integral
    disc_at: Optional[float] = None     # x-position of that element (defaults to mid-range)
    title: str = ""

    @model_validator(mode="after")
    def check_axis(self):
        ax = self.axis.lower().strip()
        if ax not in ("x", "y"):
            raise ValueError(f"axis must be 'x' or 'y', got '{self.axis}'")
        self.axis = ax
        if self.x_range[1] <= self.x_range[0]:
            raise ValueError("x_range hi must exceed lo")
        return self


# ── Graph Transformation ──────────────────────────────────────────────────────

_TRANSFORM_TYPES = {
    "shift_up", "shift_down", "shift_left", "shift_right",
    "scale_vertical", "scale_horizontal", "reflect_x", "reflect_y",
    "abs_outer", "abs_inner",
}


class GraphTransform(BaseModel):
    """A single transformation of the base curve. The transformed curve is DERIVED in code from
    the base's sampled points — the model never supplies a transformed expression."""
    type: str
    param: float = 1.0     # the shift amount a, or the scale factor k (ignored by reflections/abs)
    label: str = ""

    @model_validator(mode="after")
    def check_type(self):
        t = self.type.lower().strip()
        if t not in _TRANSFORM_TYPES:
            raise ValueError(
                f"Unknown transformation '{self.type}'. Supported: {sorted(_TRANSFORM_TYPES)}"
            )
        self.type = t
        if t in ("scale_vertical", "scale_horizontal") and abs(self.param) < 1e-9:
            raise ValueError(f"{t} needs a non-zero scale factor")
        return self


class GraphTransformationSchema(BaseModel):
    base_expression: str                # f(x), in x, via parse_safe
    transformations: List[GraphTransform] = Field(default_factory=list)
    show_base: bool = True
    x_range: Tuple[float, float] = (-5.0, 5.0)
    y_range: Optional[Tuple[float, float]] = None
    title: str = ""
    grid: bool = True


# ── Box Plot (five-number summary) ────────────────────────────────────────────

class BoxPlotDataset(BaseModel):
    """Either raw `data` (quartiles are COMPUTED by linear interpolation) or a precomputed
    five-number `summary`. Raw data is preferred — supplied quartiles cannot then disagree with
    the numbers."""
    label: str = ""
    data: List[float] = Field(default_factory=list)
    summary: Optional[Dict[str, float]] = None   # {min,q1,median,q3,max}; outliers recomputed

    @model_validator(mode="after")
    def check_source(self):
        if not self.data and self.summary is None:
            raise ValueError("a box-plot dataset needs either 'data' or a 'summary'")
        if self.summary is not None and not self.data:
            need = {"min", "q1", "median", "q3", "max"}
            missing = need - set(self.summary)
            if missing:
                raise ValueError(f"box-plot summary missing keys: {sorted(missing)}")
            s = self.summary
            if not (s["min"] <= s["q1"] <= s["median"] <= s["q3"] <= s["max"]):
                raise ValueError(
                    "box-plot summary must satisfy min ≤ q1 ≤ median ≤ q3 ≤ max"
                )
        return self


class BoxPlotSchema(BaseModel):
    datasets: List[BoxPlotDataset] = Field(min_length=1)
    orientation: str = "horizontal"   # horizontal | vertical
    show_outliers: bool = True        # points beyond 1.5·IQR of the fences (computed)
    show_values: bool = True          # print the five-number summary beside each box
    x_label: str = ""
    y_label: str = ""
    title: str = ""
    grid: bool = True

    @model_validator(mode="after")
    def check_orientation(self):
        o = self.orientation.lower().strip()
        if o not in ("horizontal", "vertical"):
            raise ValueError(f"orientation must be 'horizontal' or 'vertical', got '{self.orientation}'")
        self.orientation = o
        return self
