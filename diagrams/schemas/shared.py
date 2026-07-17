"""
Pydantic schemas for diagram types shared across domains.

annotated_xy_graph is the generic "annotated x-y curve" figure: a curve (analytic or an
explicit point list) with marked points, labelled bands, shaded areas, asymptotes and
annotations. It replaces the long tail of one-off plots — stress-strain, heating curve,
blackbody spectra, Maxwell-Boltzmann, radioactive decay, reaction kinetics, Arrhenius,
conductivity vs concentration, resonance curves — and is registered under physics,
chemistry and mathematics alike.
"""
from __future__ import annotations

from typing import List, Optional, Tuple, Union

from pydantic import (AliasChoices, BaseModel, ConfigDict, Field, field_validator,
                      model_validator)

LINE_STYLES = ("solid", "dashed", "dotted", "dashdot")
ANNOTATION_STYLES = ("dot", "crosshair", "arrow")
ORIENTATIONS = ("horizontal", "vertical")
LABEL_POSITIONS = ("auto", "top", "bottom")

# The LLM writes either spelling; the renderer only ever reads `colour`.
_COLOUR_ALIAS = AliasChoices("colour", "color")


class XYPoint(BaseModel):
    x: float
    y: float


class CurveSpec(BaseModel):
    """One curve: either an analytic expression in x, or an explicit list of points.

    Explicit points matter — a stress-strain curve or a heating curve is not an analytic
    function. Points are drawn in the order given (so a hysteresis loop works), while any
    value DERIVED from the curve interpolates an x-sorted copy.
    """
    model_config = ConfigDict(populate_by_name=True)

    expression: Optional[str] = None          # sympy expression in x, e.g. "100*exp(-0.0866*x)"
    points: List[XYPoint] = Field(default_factory=list)
    label: Optional[str] = None
    colour: Optional[str] = Field(default=None, validation_alias=_COLOUR_ALIAS)
    line_style: Optional[str] = None          # auto-rotated when omitted
    line_width: float = Field(default=2.2, ge=0.5, le=6.0)
    show_marker: bool = False                 # dot on every data point
    x_range: Optional[Tuple[float, float]] = None   # falls back to the figure x_range

    @field_validator("line_style")
    @classmethod
    def known_line_style(cls, v):
        if v is not None and v not in LINE_STYLES:
            raise ValueError(f"Unknown line_style '{v}'. Supported: {list(LINE_STYLES)}")
        return v

    @model_validator(mode="after")
    def one_source(self):
        if bool(self.expression) == bool(self.points):
            raise ValueError("A curve needs exactly one of 'expression' or 'points'")
        if self.points and len(self.points) < 2:
            raise ValueError("A curve given as 'points' needs at least 2 points")
        return self


class CurveFamilyMember(CurveSpec):
    """One member of a curve family. `label` carries the parameter value ("T = 3000 K")."""
    label: str


class CurveFamily(BaseModel):
    """The very common "same curve at several parameter values" figure — blackbody at three
    temperatures, I-V at three intensities. Each member gets its own colour + legend entry."""
    members: List[CurveFamilyMember] = Field(min_length=1)
    name: str = ""     # legend title, e.g. "Temperature"


class MarkedPoint(BaseModel):
    """A point called out on a curve — yield point, peak, half-life, triple point.

    `y` is optional and SHOULD be omitted: the renderer evaluates the curve at x, which is
    the only way the dot is guaranteed to sit on the line.
    """
    x: float
    y: Optional[float] = None
    label: str = ""
    curve: Optional[Union[int, str]] = None    # curve index or label; defaults to the first curve
    annotation_style: str = "dot"              # dot | crosshair | arrow
    show_coordinates: bool = False
    show_dropline: bool = False                # dashed lines to both axes
    label_offset: Tuple[float, float] = (8.0, 8.0)   # points, from the marker

    @field_validator("annotation_style")
    @classmethod
    def known_style(cls, v):
        if v not in ANNOTATION_STYLES:
            raise ValueError(
                f"Unknown annotation_style '{v}'. Supported: {list(ANNOTATION_STYLES)}"
            )
        return v


class ShadedRegionSpec(BaseModel):
    """A filled area. With under_curve the fill follows the actual curve (work done, area
    under a distribution); otherwise it is the rectangle x_from..x_to × y_from..y_to, with
    unset y bounds meaning the full axis height."""
    model_config = ConfigDict(populate_by_name=True)

    x_from: float
    x_to: float
    y_from: Optional[float] = None
    y_to: Optional[float] = None
    under_curve: bool = False
    curve: Optional[Union[int, str]] = None
    label: Optional[str] = None
    colour: str = Field(default="#9CA3AF", validation_alias=_COLOUR_ALIAS)
    alpha: float = Field(default=0.35, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def ordered(self):
        if self.x_to <= self.x_from:
            raise ValueError(f"shaded_region x_to ({self.x_to}) must exceed x_from ({self.x_from})")
        return self


class BandRegion(BaseModel):
    """A labelled band across the full height of the plot — "Elastic region", "Plastic
    region", "Solid", "Liquid". Identifying these bands is what most of these questions
    actually ask for."""
    model_config = ConfigDict(populate_by_name=True)

    x_from: float
    x_to: float
    label: str = ""
    colour: Optional[str] = Field(default=None, validation_alias=_COLOUR_ALIAS)
    alpha: float = Field(default=0.16, ge=0.0, le=1.0)
    label_position: str = "auto"        # auto → placed clear of the curve
    label_rotation: float = 0.0         # 90 reads a long name into a narrow band
    show_boundaries: bool = True        # dashed dividers at the band edges

    @field_validator("label_position")
    @classmethod
    def known_position(cls, v):
        if v not in LABEL_POSITIONS:
            raise ValueError(
                f"Unknown label_position '{v}'. Supported: {list(LABEL_POSITIONS)}"
            )
        return v

    @model_validator(mode="after")
    def ordered(self):
        if self.x_to <= self.x_from:
            raise ValueError(f"region x_to ({self.x_to}) must exceed x_from ({self.x_from})")
        return self


class _AxisLine(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    orientation: str            # horizontal (y = value) | vertical (x = value)
    value: float
    label: str = ""
    line_style: str = "dashed"
    colour: Optional[str] = Field(default=None, validation_alias=_COLOUR_ALIAS)

    @field_validator("orientation")
    @classmethod
    def known_orientation(cls, v):
        if v not in ORIENTATIONS:
            raise ValueError(f"Unknown orientation '{v}'. Supported: {list(ORIENTATIONS)}")
        return v

    @field_validator("line_style")
    @classmethod
    def known_line_style(cls, v):
        if v not in LINE_STYLES:
            raise ValueError(f"Unknown line_style '{v}'. Supported: {list(LINE_STYLES)}")
        return v


class AsymptoteSpec(_AxisLine):
    """A limit the curve approaches but never reaches (saturation current, N → 0)."""


class ReferenceLine(_AxisLine):
    """A level the question refers to — a threshold, a melting point, N₀/2."""
    line_style: str = "dotted"


class AnnotationSpec(BaseModel):
    """Free text at (x, y); with target_x/target_y it grows an arrow to that point on the
    curve — "peak shifts left as T increases"."""
    text: str
    x: float
    y: float
    target_x: Optional[float] = None
    target_y: Optional[float] = None
    fontsize: float = Field(default=10.0, ge=6.0, le=20.0)

    @model_validator(mode="after")
    def arrow_needs_both_ends(self):
        if (self.target_x is None) != (self.target_y is None):
            raise ValueError("An annotation arrow needs both 'target_x' and 'target_y'")
        return self


class AnnotatedXYGraphSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    curves: List[CurveSpec] = Field(default_factory=list)
    curve_family: Optional[CurveFamily] = None

    x_label: str = "x"
    y_label: str = "y"
    title: str = ""
    x_range: Optional[Tuple[float, float]] = None   # auto-fitted to the data if None
    y_range: Optional[Tuple[float, float]] = None
    show_grid: bool = True
    show_legend: bool = True
    legend_loc: str = "best"
    log_x: bool = False
    log_y: bool = False       # semi-log decay / kinetics plot

    marked_points: List[MarkedPoint] = Field(default_factory=list)
    shaded_regions: List[ShadedRegionSpec] = Field(default_factory=list)
    regions: List[BandRegion] = Field(default_factory=list)
    asymptotes: List[AsymptoteSpec] = Field(default_factory=list)
    reference_lines: List[ReferenceLine] = Field(default_factory=list)
    annotations: List[AnnotationSpec] = Field(
        default_factory=list, validation_alias=AliasChoices("annotations", "arrows"))

    @model_validator(mode="after")
    def needs_a_curve(self):
        if not self.curves and not self.curve_family:
            raise ValueError("annotated_xy_graph needs at least one curve or a curve_family")
        if self.x_range and self.x_range[1] <= self.x_range[0]:
            raise ValueError(f"x_range must be increasing, got {self.x_range}")
        if self.y_range and self.y_range[1] <= self.y_range[0]:
            raise ValueError(f"y_range must be increasing, got {self.y_range}")
        return self
