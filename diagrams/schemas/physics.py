"""
Pydantic schemas for Physics diagram types.
"""
from __future__ import annotations

from enum import Enum
from typing import List, Optional, Tuple

from pydantic import BaseModel, Field, field_validator, model_validator


class ForceArrow(BaseModel):
    label: str                          # e.g. "mg", "N", "f"
    direction: str                      # "down" | "up" | "left" | "right" | "normal" | "along_incline"
    magnitude: Optional[float] = None  # optional numeric value for labelling


class PhysicsObject(BaseModel):
    type: str                                   # incline | block | pulley | mass | spring | wall
    label: Optional[str] = None
    angle: Optional[float] = None              # degrees
    mass: Optional[float] = None               # kg
    coefficient_friction: Optional[float] = None
    spring_constant: Optional[float] = None    # N/m
    radius: Optional[float] = None             # m, for pulleys


# ── Inclined Plane ────────────────────────────────────────────────────────────

class InclinedPlaneSchema(BaseModel):
    angle: float = Field(default=30.0, ge=1.0, le=89.0)
    block_label: str = "m"
    forces: List[str] = Field(default_factory=lambda: ["mg", "N", "f"])
    show_angle_label: bool = True
    friction_direction: str = "up"    # "up" | "down" along incline

    @field_validator("forces")
    @classmethod
    def validate_forces(cls, v: List[str]) -> List[str]:
        allowed = {"mg", "N", "f", "T", "W"}
        for f in v:
            if f not in allowed:
                raise ValueError(f"Unknown force '{f}'. Allowed: {allowed}")
        return v


# ── Free Body Diagram ─────────────────────────────────────────────────────────

class FBDObject(BaseModel):
    shape: str = "square"   # square | circle | point
    label: str = "m"


class FBDForce(BaseModel):
    label: str
    direction_deg: float = Field(ge=0, le=360)   # 0=right, 90=up, 180=left, 270=down
    magnitude: Optional[float] = None


class FreeBodyDiagramSchema(BaseModel):
    object: FBDObject = Field(default_factory=FBDObject)
    forces: List[FBDForce] = Field(default_factory=list)


# ── Pulley System ─────────────────────────────────────────────────────────────

class PulleyMass(BaseModel):
    label: str = "m"
    mass: Optional[float] = None
    side: str = "left"   # left | right | hanging


class PulleySystemSchema(BaseModel):
    pulley_count: int = Field(default=1, ge=1, le=4)
    masses: List[PulleyMass] = Field(default_factory=list)
    fixed_support: str = "ceiling"   # ceiling | wall


# ── Projectile Motion ─────────────────────────────────────────────────────────

class ProjectileMotionSchema(BaseModel):
    initial_velocity: float = Field(default=20.0, ge=1.0)
    launch_angle: float = Field(default=45.0, ge=1.0, le=89.0)
    show_components: bool = True
    show_trajectory: bool = True
    show_max_height_line: bool = True
    label_points: List[str] = Field(default_factory=lambda: ["O", "H", "R"])


# ── Spring Block ──────────────────────────────────────────────────────────────

class SpringBlockSchema(BaseModel):
    orientation: str = "horizontal"   # horizontal | vertical
    block_label: str = "m"
    spring_label: str = "k"
    wall_side: str = "left"          # left | right | top | bottom
    show_equilibrium: bool = True
    displacement_label: Optional[str] = "x"


# ── Optics: Convex Lens ───────────────────────────────────────────────────────

class OpticsObjectArrow(BaseModel):
    height: float = Field(default=80.0, ge=10.0)
    position: str = "beyond_2f"   # beyond_2f | at_2f | between_f_2f | at_f | within_f


class ConvexLensSchema(BaseModel):
    focal_length: float = Field(default=100.0, ge=10.0)
    object_arrow: OpticsObjectArrow = Field(default_factory=OpticsObjectArrow)
    show_rays: bool = True
    show_focal_points: bool = True
    show_center: bool = True


# ── Optics: Concave Mirror ────────────────────────────────────────────────────

class ConcaveMirrorSchema(BaseModel):
    focal_length: float = Field(default=100.0, ge=10.0)
    object_arrow: OpticsObjectArrow = Field(default_factory=OpticsObjectArrow)
    show_rays: bool = True
    show_focal_points: bool = True


# ── Wave Diagram ──────────────────────────────────────────────────────────────

class WaveDiagramSchema(BaseModel):
    amplitude: float = Field(default=80.0, ge=10.0, le=250.0)
    wavelength_px: float = Field(default=160.0, ge=40.0)
    num_cycles: float = Field(default=2.5, ge=0.5, le=10.0)
    wave_type: str = "transverse"   # transverse | longitudinal
    label_amplitude: bool = True
    label_wavelength: bool = True
    label_crest: bool = True
    label_trough: bool = True


# ── Thermodynamics P-V Diagram ────────────────────────────────────────────────

class ThermoPVState(BaseModel):
    label: str = ""
    volume: float           # in any consistent units
    pressure: float         # in any consistent units


class ThermoPVProcess(BaseModel):
    from_state: str         # label of starting state
    to_state: str           # label of ending state
    process_type: str = "general"  # isothermal | isobaric | isochoric | adiabatic | general
    label: str = ""         # optional label on the curve


class ThermoPVSchema(BaseModel):
    states: List[ThermoPVState] = Field(default_factory=list)
    processes: List[ThermoPVProcess] = Field(default_factory=list)
    x_label: str = "V →"
    y_label: str = "P →"
    title: str = ""
    show_work_area: bool = False   # shade area under cycle
    gamma: float = Field(default=1.4, ge=1.0, le=2.0)   # adiabatic exponent


# ── Ray Optics: Prism ─────────────────────────────────────────────────────────

class RayOpticsPrismSchema(BaseModel):
    prism_angle: float = Field(default=60.0, ge=20.0, le=89.0)     # apex angle A
    incident_angle: float = Field(default=45.0, ge=5.0, le=85.0)   # angle of incidence i
    refractive_index: float = Field(default=1.5, ge=1.0, le=3.0)
    show_normals: bool = True
    show_angles: bool = True
    label_deviation: bool = True
    title: str = ""


# ── Electric Field Lines ──────────────────────────────────────────────────────

class ElectricCharge(BaseModel):
    x: float = 0.0
    y: float = 0.0
    charge: float = 1.0    # positive or negative, relative magnitude
    label: str = ""


class ElectricFieldSchema(BaseModel):
    charges: List[ElectricCharge] = Field(default_factory=list)
    field_type: str = "point_charges"   # point_charges | uniform | dipole
    num_lines: int = Field(default=8, ge=4, le=24)
    show_equipotential: bool = False
    title: str = ""


# ── Magnetic Field Lines ──────────────────────────────────────────────────────

class MagneticFieldSchema(BaseModel):
    source_type: str = "bar_magnet"   # bar_magnet | solenoid | straight_wire | circular_loop
    show_field_lines: bool = True
    label_poles: bool = True
    num_field_lines: int = Field(default=8, ge=4, le=20)
    current_direction: str = "out"    # out | in  (for wire/loop)
    title: str = ""


# ── Circular Motion ───────────────────────────────────────────────────────────

class CircularMotionSchema(BaseModel):
    show_velocity: bool = True
    show_centripetal: bool = True
    show_angular_velocity: bool = False
    radius_label: str = "r"
    mass_label: str = "m"
    velocity_label: str = "v"
    centripetal_label: str = "F_c"
    object_angle_deg: float = Field(default=45.0, ge=0.0, le=360.0)
    title: str = ""


# ── Doppler Effect ────────────────────────────────────────────────────────────

class DopplerEffectSchema(BaseModel):
    source_velocity: float = Field(default=0.5, ge=0.0, le=0.99)  # fraction of wave speed
    direction: str = "right"         # right | left (direction of source motion)
    show_observer: bool = True
    observer_side: str = "right"     # right | left (where observer is)
    num_wavefronts: int = Field(default=6, ge=3, le=12)
    show_labels: bool = True
    show_frequency_labels: bool = True
    title: str = ""


# ── Interference / Diffraction Pattern ───────────────────────────────────────

class InterferencePatternSchema(BaseModel):
    pattern_type: str = "double_slit"   # double_slit | single_slit
    slit_separation: float = Field(default=2.0, ge=0.5, le=10.0)  # in units of wavelength
    wavelength: float = Field(default=500.0, ge=300.0, le=800.0)  # nm, for color
    num_maxima: int = Field(default=5, ge=1, le=10)
    show_central_max: bool = True
    show_order_labels: bool = True
    show_intensity_curve: bool = True
    title: str = ""


# ── Bohr Atom Model ───────────────────────────────────────────────────────────

class BohrTransition(BaseModel):
    from_shell: int = Field(ge=1, le=7)
    to_shell: int = Field(ge=1, le=7)
    label: str = ""                  # e.g. "Hα", "Lyman α"
    color: str = "red"


class BohrAtomSchema(BaseModel):
    element: str = "H"               # element symbol
    num_shells: int = Field(default=3, ge=1, le=7)
    electrons_per_shell: List[int] = Field(default_factory=list)  # auto if empty
    show_nucleus: bool = True
    nucleus_label: str = ""          # auto if empty
    transitions: List[BohrTransition] = Field(default_factory=list)
    show_energy_levels: bool = True
    title: str = ""


# ── Capacitor with Dielectric ─────────────────────────────────────────────────

class CapacitorDielectricSchema(BaseModel):
    dielectric_label: str = "ε_r = 2"
    plate_label_pos: str = "+Q"      # charge label on positive plate
    plate_label_neg: str = "-Q"
    show_field_lines: bool = True
    num_field_lines: int = Field(default=6, ge=3, le=12)
    show_charges: bool = True
    show_induced_charges: bool = True
    voltage_label: str = "V"
    show_capacitance_formula: bool = True
    title: str = ""


# ── LC Circuit Oscillation ────────────────────────────────────────────────────

class LCOscillationSchema(BaseModel):
    inductance_label: str = "L"
    capacitance_label: str = "C"
    show_circuit: bool = True
    show_graphs: bool = True         # Q, I, U_E, U_B vs time
    num_cycles: float = Field(default=2.0, ge=0.5, le=5.0)
    initial_state: str = "charged"   # charged | discharged
    show_energy_labels: bool = True
    title: str = ""


# ── Semiconductors: p-n Junction ──────────────────────────────────────────────

class PNJunctionSchema(BaseModel):
    bias: str = "unbiased"              # unbiased | forward | reverse
    show_depletion_region: bool = True
    show_barrier_potential: bool = True  # potential plot beneath the junction
    show_carriers: bool = True           # holes (○) in p, electrons (●) in n
    show_battery: bool = True
    show_current_arrow: bool = True
    title: str = ""

    @field_validator("bias")
    @classmethod
    def validate_bias(cls, v: str) -> str:
        allowed = {"unbiased", "forward", "reverse"}
        if v not in allowed:
            raise ValueError(f"Unknown bias '{v}'. Allowed: {sorted(allowed)}")
        return v


# ── Semiconductors: I-V Characteristics ──────────────────────────────────────

class SemiconductorIVSchema(BaseModel):
    device: str = "pn_diode"    # pn_diode | zener | led | photodiode | transistor_ce | transistor_input
    knee_voltage: Optional[float] = None       # V; None → device default (0.7 Si, 0.3 Ge, 1.8 LED)
    breakdown_voltage: Optional[float] = None  # V (magnitude); None → device default
    show_quadrant_labels: bool = False
    label_regions: bool = True                 # forward / reverse / breakdown
    title: str = ""

    @field_validator("device")
    @classmethod
    def validate_device(cls, v: str) -> str:
        allowed = {"pn_diode", "zener", "led", "photodiode",
                   "transistor_ce", "transistor_input"}
        if v not in allowed:
            raise ValueError(f"Unknown device '{v}'. Allowed: {sorted(allowed)}")
        return v


# ── Photoelectric Effect ──────────────────────────────────────────────────────

class PhotoelectricEffectSchema(BaseModel):
    graph_type: str = "stopping_potential_vs_frequency"
    # stopping_potential_vs_frequency | current_vs_voltage | current_vs_intensity
    # | max_ke_vs_frequency | apparatus
    work_function: float = Field(default=2.0, gt=0.0, le=10.0)   # eV
    threshold_frequency: Optional[float] = None   # Hz; derived from work function if omitted
    intensities: List[float] = Field(default_factory=lambda: [1.0, 2.0, 3.0])   # relative
    frequencies: List[float] = Field(default_factory=list)                      # Hz
    show_threshold: bool = True
    show_slope_h: bool = True     # annotate that the slope is h/e
    title: str = ""

    @field_validator("graph_type")
    @classmethod
    def validate_graph_type(cls, v: str) -> str:
        allowed = {"stopping_potential_vs_frequency", "current_vs_voltage",
                   "current_vs_intensity", "max_ke_vs_frequency", "apparatus"}
        if v not in allowed:
            raise ValueError(f"Unknown graph_type '{v}'. Allowed: {sorted(allowed)}")
        return v


# ── Nuclear Binding Energy Curve ──────────────────────────────────────────────

class MarkedNucleus(BaseModel):
    symbol: str                       # e.g. "He", "Fe", "U"
    mass_number: int = Field(ge=1, le=250)


class NuclearBindingEnergySchema(BaseModel):
    marked_nuclei: List[MarkedNucleus] = Field(default_factory=list)
    show_fusion_region: bool = True
    show_fission_region: bool = True
    show_peak: bool = True            # Fe-56 at ~8.8 MeV
    title: str = ""


# ── Electromagnetic Wave ──────────────────────────────────────────────────────

class EMWaveSchema(BaseModel):
    num_cycles: float = Field(default=2.0, ge=0.5, le=5.0)
    show_e_field: bool = True
    show_b_field: bool = True
    propagation_axis: str = "z"       # z (E along x, B along y)
    e_label: str = "E"
    b_label: str = "B"
    show_wavelength: bool = True
    show_propagation_arrow: bool = True
    wave_type: str = ""               # optional, e.g. "Visible light"
    title: str = ""

    @field_validator("propagation_axis")
    @classmethod
    def validate_axis(cls, v: str) -> str:
        if v != "z":
            raise ValueError("propagation_axis must be 'z' (E along x, B along y)")
        return v


# ── Total Internal Reflection ─────────────────────────────────────────────────

class TotalInternalReflectionSchema(BaseModel):
    n1: float = Field(default=1.5, gt=1.0, le=4.0)    # denser medium
    n2: float = Field(default=1.0, ge=1.0, le=4.0)    # rarer medium
    show_critical_angle: bool = True
    incident_angles: List[float] = Field(default_factory=list)   # deg; auto if empty
    medium_labels: List[str] = Field(default_factory=list)       # [denser, rarer]
    mode: str = "rays"                # rays | optical_fibre
    title: str = ""

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, v: str) -> str:
        allowed = {"rays", "optical_fibre"}
        if v not in allowed:
            raise ValueError(f"Unknown mode '{v}'. Allowed: {sorted(allowed)}")
        return v

    @model_validator(mode="after")
    def validate_denser_first(self) -> "TotalInternalReflectionSchema":
        # TIR only exists going from denser to rarer; n1 <= n2 has no critical angle
        # and arcsin(n2/n1) would be undefined.
        if self.n1 <= self.n2:
            raise ValueError(
                f"n1 ({self.n1}) must be greater than n2 ({self.n2}): "
                "total internal reflection requires a denser → rarer interface."
            )
        return self


# ── Moment of Inertia ─────────────────────────────────────────────────────────

# Axis positions that are physically defined for each body. The (body, axis)
# pair fixes the standard I expression — a rod has no 'diameter', a sphere no
# 'end', so an unlisted pair is rejected rather than silently mis-rendered.
MOI_VALID_AXES = {
    "rod": ("centre", "end", "perpendicular_bisector"),
    "ring": ("centre", "diameter", "tangent"),
    "disc": ("centre", "diameter", "tangent"),
    "solid_sphere": ("centre", "diameter", "tangent"),
    "hollow_sphere": ("centre", "diameter", "tangent"),
    "solid_cylinder": ("centre", "diameter", "end"),
    "hollow_cylinder": ("centre", "diameter", "end"),
    "rectangular_plate": ("centre", "perpendicular_bisector", "end"),
}


class MomentOfInertiaSchema(BaseModel):
    body: str = "disc"       # rod | ring | disc | solid_sphere | hollow_sphere
                             # | solid_cylinder | hollow_cylinder | rectangular_plate
    axis: str = "centre"     # centre | end | diameter | tangent | perpendicular_bisector
    show_axis: bool = True
    show_formula: bool = True
    mass_label: str = "M"
    radius_label: str = "R"
    length_label: str = "L"
    breadth_label: str = "b"   # rectangular_plate only
    title: str = ""

    @field_validator("body")
    @classmethod
    def validate_body(cls, v: str) -> str:
        if v not in MOI_VALID_AXES:
            raise ValueError(f"Unknown body '{v}'. Allowed: {sorted(MOI_VALID_AXES)}")
        return v

    @model_validator(mode="after")
    def validate_axis_for_body(self) -> "MomentOfInertiaSchema":
        valid = MOI_VALID_AXES[self.body]
        if self.axis not in valid:
            raise ValueError(
                f"axis '{self.axis}' is not defined for body '{self.body}'. "
                f"Allowed: {list(valid)}"
            )
        return self


# ── Fluid Mechanics ───────────────────────────────────────────────────────────

class FluidMechanicsSchema(BaseModel):
    setup: str = "venturimeter"
    # venturimeter | manometer | capillary_rise | hydraulic_press
    # | floating_body | streamline_flow

    fluid_density: float = Field(default=1000.0, gt=0.0)      # kg/m³ (water)
    gravity: float = Field(default=9.8, gt=0.0)               # m/s²

    # venturimeter / streamline_flow
    area_wide: float = Field(default=8e-4, gt=0.0)            # A₁, m²
    area_narrow: float = Field(default=4e-4, gt=0.0)          # A₂, m²
    velocity_wide: float = Field(default=2.0, gt=0.0)         # v₁, m/s

    # manometer
    gauge_pressure: float = Field(default=2000.0)             # Pa (may be negative)
    manometer_fluid_density: float = Field(default=13600.0, gt=0.0)   # kg/m³ (mercury)

    # capillary_rise
    surface_tension: float = Field(default=0.073, gt=0.0)     # N/m (water-air)
    contact_angle: float = Field(default=0.0, ge=0.0, le=180.0)   # degrees
    tube_radius: float = Field(default=2e-4, gt=0.0)          # m

    # hydraulic_press
    input_force: float = Field(default=100.0, gt=0.0)         # F₁, N
    piston_area_small: float = Field(default=0.01, gt=0.0)    # A₁, m²
    piston_area_large: float = Field(default=0.25, gt=0.0)    # A₂, m²

    # floating_body
    body_density: float = Field(default=800.0, gt=0.0)        # kg/m³

    show_derivation: bool = True
    title: str = ""

    @field_validator("setup")
    @classmethod
    def validate_setup(cls, v: str) -> str:
        allowed = {"venturimeter", "manometer", "capillary_rise",
                   "hydraulic_press", "floating_body", "streamline_flow"}
        if v not in allowed:
            raise ValueError(f"Unknown setup '{v}'. Allowed: {sorted(allowed)}")
        return v

    @model_validator(mode="after")
    def validate_physics(self) -> "FluidMechanicsSchema":
        if self.setup == "floating_body" and self.body_density >= self.fluid_density:
            # A body denser than its fluid sinks: there is no equilibrium submerged
            # fraction to draw, and ρ_body/ρ_fluid ≥ 1 would render as a block
            # sticking out of the liquid while claiming to float.
            raise ValueError(
                f"body_density ({self.body_density}) must be less than fluid_density "
                f"({self.fluid_density}): a denser body sinks, it does not float."
            )
        if self.setup in ("venturimeter", "streamline_flow") \
                and self.area_narrow >= self.area_wide:
            raise ValueError(
                f"area_narrow ({self.area_narrow}) must be less than area_wide "
                f"({self.area_wide}): the throat is the constriction."
            )
        return self


# ── Kinematics: Motion Graphs ─────────────────────────────────────────────────

class MotionPhase(BaseModel):
    duration: float = Field(gt=0.0)                   # s
    acceleration: float = 0.0                         # m/s²
    initial_velocity: Optional[float] = None          # m/s; only the FIRST phase may
                                                      # set this — v is continuous, so
                                                      # later phases inherit it.
    label: str = ""


class MotionGraphSchema(BaseModel):
    graph_types: List[str] = Field(
        default_factory=lambda: ["position_time", "velocity_time", "acceleration_time"])

    phases: List[MotionPhase] = Field(default_factory=list)
    # Alternative to phases: x(t) = c₀ + c₁t + c₂t² + …  (the "explicit expression"
    # form). v and a are then the analytic derivatives of THIS polynomial.
    position_coeffs: List[float] = Field(default_factory=list)
    total_time: Optional[float] = None                # s; required with position_coeffs

    initial_position: float = 0.0                     # m
    show_area: bool = False                           # shade ∫v dt on the v-t panel
    show_slope: bool = False                          # tangent construction
    slope_at: Optional[float] = None                  # s; midpoint if omitted
    annotations: List[str] = Field(default_factory=list)
    title: str = ""

    @field_validator("graph_types")
    @classmethod
    def validate_graph_types(cls, v: List[str]) -> List[str]:
        allowed = ["position_time", "velocity_time", "acceleration_time"]
        if not v:
            raise ValueError("graph_types must not be empty.")
        for g in v:
            if g not in allowed:
                raise ValueError(f"Unknown graph_type '{g}'. Allowed: {allowed}")
        # Panels are stacked on a shared time axis, so they are ordered by
        # derivative order regardless of the order supplied.
        return [g for g in allowed if g in v]

    @model_validator(mode="after")
    def validate_motion(self) -> "MotionGraphSchema":
        if not self.phases and not self.position_coeffs:
            raise ValueError(
                "Supply either phases or position_coeffs to define the motion.")
        if self.phases and self.position_coeffs:
            raise ValueError(
                "Supply phases OR position_coeffs, not both: two independent "
                "definitions of the motion cannot be guaranteed to agree.")
        if self.position_coeffs:
            if len(self.position_coeffs) < 2:
                raise ValueError("position_coeffs needs at least [c0, c1].")
            if self.total_time is None or self.total_time <= 0:
                raise ValueError("position_coeffs requires a positive total_time.")
        return self


# ── Simple Harmonic Motion ────────────────────────────────────────────────────

class SHMSystemSchema(BaseModel):
    setup: str = "spring_horizontal"
    # spring_horizontal | spring_vertical | simple_pendulum | torsional

    mass: float = Field(default=0.5, gt=0.0)              # kg
    spring_constant: float = Field(default=20.0, gt=0.0)  # N/m
    length: float = Field(default=1.0, gt=0.0)            # m (pendulum)
    gravity: float = Field(default=9.8, gt=0.0)           # m/s²
    torsional_constant: float = Field(default=0.02, gt=0.0)   # N·m/rad
    inertia: float = Field(default=0.005, gt=0.0)             # kg·m² (torsional)
    amplitude: float = Field(default=0.1, gt=0.0)         # m (or rad, torsional)

    show_graphs: bool = True          # x, v, a vs t
    show_period: bool = True
    show_phase_note: bool = True
    num_cycles: float = Field(default=2.0, ge=0.5, le=4.0)
    title: str = ""

    @field_validator("setup")
    @classmethod
    def validate_setup(cls, v: str) -> str:
        allowed = {"spring_horizontal", "spring_vertical", "simple_pendulum", "torsional"}
        if v not in allowed:
            raise ValueError(f"Unknown setup '{v}'. Allowed: {sorted(allowed)}")
        return v


# ── Standing Waves ────────────────────────────────────────────────────────────

class StandingWaveSchema(BaseModel):
    mode: str = "string"                  # string | open_pipe | closed_pipe
    harmonic: int = Field(default=1, ge=1, le=9)
    length: float = Field(default=1.0, gt=0.0)        # m
    wave_speed: float = Field(default=340.0, gt=0.0)  # m/s
    show_nodes: bool = True
    show_antinodes: bool = True
    show_wavelength: bool = True
    show_frequency_relation: bool = True
    # A closed pipe cannot sustain an even harmonic. Rather than silently drawing an
    # impossible mode, snap up to the next odd harmonic (default) or reject outright.
    on_invalid_harmonic: str = "snap"     # snap | reject
    title: str = ""

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, v: str) -> str:
        allowed = {"string", "open_pipe", "closed_pipe"}
        if v not in allowed:
            raise ValueError(f"Unknown mode '{v}'. Allowed: {sorted(allowed)}")
        return v

    @field_validator("on_invalid_harmonic")
    @classmethod
    def validate_policy(cls, v: str) -> str:
        allowed = {"snap", "reject"}
        if v not in allowed:
            raise ValueError(f"Unknown on_invalid_harmonic '{v}'. Allowed: {sorted(allowed)}")
        return v

    @model_validator(mode="after")
    def validate_closed_pipe_harmonic(self) -> "StandingWaveSchema":
        if self.mode == "closed_pipe" and self.harmonic % 2 == 0 \
                and self.on_invalid_harmonic == "reject":
            raise ValueError(
                f"A closed pipe supports only ODD harmonics (n = 1, 3, 5 …); "
                f"n = {self.harmonic} is impossible. The closed end must be a "
                f"displacement node and the open end an antinode, which forces "
                f"L = (2m−1)λ/4."
            )
        return self


# ── Elasticity: Stress-Strain Curve ───────────────────────────────────────────

class StressStrainSchema(BaseModel):
    material: str = "ductile"        # ductile | brittle | elastomer
    material_name: str = ""          # e.g. "Mild steel"; a default per material
    show_hookes_law_region: bool = True
    show_young_modulus: bool = True  # slope of the linear (proportional) part
    show_regions: bool = True        # elastic vs plastic shading
    mark_points: bool = True         # P, E, Y, U, F
    title: str = ""

    @field_validator("material")
    @classmethod
    def validate_material(cls, v: str) -> str:
        allowed = {"ductile", "brittle", "elastomer"}
        if v not in allowed:
            raise ValueError(f"Unknown material '{v}'. Allowed: {sorted(allowed)}")
        return v


# ── Calorimetry: Heating Curve ────────────────────────────────────────────────

class HeatingCurveSchema(BaseModel):
    substance: str = "water"
    mass: float = Field(default=1.0, gt=0.0)              # kg
    melting_point: float = 0.0                            # °C
    boiling_point: float = 100.0                          # °C
    start_temp: float = -20.0                             # °C
    end_temp: float = 120.0                               # °C
    specific_heat_solid: float = Field(default=2100.0, gt=0.0)    # J/kg·K (ice)
    specific_heat_liquid: float = Field(default=4186.0, gt=0.0)   # J/kg·K (water)
    specific_heat_gas: float = Field(default=2010.0, gt=0.0)      # J/kg·K (steam)
    latent_heat_fusion: float = Field(default=334000.0, gt=0.0)   # J/kg
    latent_heat_vaporisation: float = Field(default=2260000.0, gt=0.0)  # J/kg
    show_regions: bool = True
    show_plateau_labels: bool = True
    show_heat_values: bool = True
    title: str = ""

    @model_validator(mode="after")
    def validate_temperatures(self) -> "HeatingCurveSchema":
        if not (self.start_temp < self.melting_point < self.boiling_point < self.end_temp):
            raise ValueError(
                "Require start_temp < melting_point < boiling_point < end_temp so that "
                "the curve actually crosses both phase changes."
            )
        return self


# ── Blackbody Radiation Spectrum ──────────────────────────────────────────────

class BlackbodySpectrumSchema(BaseModel):
    temperatures: List[float] = Field(default_factory=lambda: [3000.0, 4000.0, 5000.0])
    show_wien_line: bool = True       # locus of the peaks
    show_peak_labels: bool = True
    show_visible_band: bool = False
    log_intensity: bool = False       # log y — keeps a cool curve visible beside a hot one
    title: str = ""

    @field_validator("temperatures")
    @classmethod
    def validate_temperatures(cls, v: List[float]) -> List[float]:
        if not v:
            raise ValueError("temperatures must not be empty.")
        for t in v:
            if t <= 0:
                raise ValueError(f"Temperature {t} K must be positive.")
            if t > 20000:
                raise ValueError(f"Temperature {t} K is out of the plotted range (≤ 20000 K).")
        return v


# ── Kinetic Theory: Maxwell-Boltzmann Distribution ────────────────────────────

class MaxwellBoltzmannSchema(BaseModel):
    temperatures: List[float] = Field(default_factory=lambda: [300.0, 600.0, 1200.0])
    molar_masses: List[float] = Field(default_factory=list)   # g/mol; varies gas instead of T
    gas_name: str = "N₂"
    molar_mass: float = Field(default=28.0, gt=0.0)           # g/mol, used with temperatures
    reference_temperature: float = Field(default=300.0, gt=0.0)   # K, used with molar_masses
    show_speed_markers: bool = True     # v_mp, v_avg, v_rms on the first curve
    show_area_note: bool = True         # the area under every curve is the same (= 1)
    title: str = ""

    @model_validator(mode="after")
    def validate_series(self) -> "MaxwellBoltzmannSchema":
        if self.molar_masses:
            for m in self.molar_masses:
                if m <= 0:
                    raise ValueError(f"molar mass {m} g/mol must be positive.")
        else:
            if not self.temperatures:
                raise ValueError("Supply temperatures or molar_masses.")
            for t in self.temperatures:
                if t <= 0:
                    raise ValueError(f"Temperature {t} K must be positive.")
        return self


# ── Gravitation ───────────────────────────────────────────────────────────────

class GravitationSchema(BaseModel):
    setup: str = "satellite_orbit"
    # satellite_orbit | kepler_ellipse | g_variation | field_lines

    # satellite_orbit
    orbit_height_km: float = Field(default=400.0, gt=0.0)     # above the surface
    show_orbital_velocity: bool = True
    show_period: bool = True

    # kepler_ellipse
    eccentricity: float = Field(default=0.6, ge=0.05, le=0.9)
    show_equal_areas: bool = True
    show_foci: bool = True
    planet_name: str = "Planet"
    star_name: str = "Sun"

    # g_variation
    show_surface_marker: bool = True
    max_radius_factor: float = Field(default=3.0, ge=1.5, le=6.0)   # in units of R_E

    # field_lines
    show_equipotentials: bool = True
    num_field_lines: int = Field(default=12, ge=4, le=24)

    title: str = ""

    @field_validator("setup")
    @classmethod
    def validate_setup(cls, v: str) -> str:
        allowed = {"satellite_orbit", "kepler_ellipse", "g_variation", "field_lines"}
        if v not in allowed:
            raise ValueError(f"Unknown setup '{v}'. Allowed: {sorted(allowed)}")
        return v


# ── Radioactive Decay ─────────────────────────────────────────────────────────

class DecayStep(BaseModel):
    type: str          # alpha | beta_minus | beta_plus | gamma
    label: str = ""

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        allowed = {"alpha", "beta_minus", "beta_plus", "gamma"}
        if v not in allowed:
            raise ValueError(f"Unknown decay type '{v}'. Allowed: {sorted(allowed)}")
        return v


class RadioactiveDecaySchema(BaseModel):
    half_life: float = Field(default=10.0, gt=0.0)          # in half_life_unit
    half_life_unit: str = "years"
    initial_amount: float = Field(default=100.0, gt=0.0)    # N₀ (any unit)
    num_half_lives: int = Field(default=4, ge=1, le=8)
    show_half_life_markers: bool = True
    show_decay_constant: bool = True     # λ = ln2 / T½
    show_semi_log: bool = False          # ln N vs t — a straight line of slope −λ
    show_decay_chain: bool = False       # N-vs-Z chart of the transitions
    parent_symbol: str = "U"
    parent_z: int = Field(default=92, ge=1, le=118)
    parent_a: int = Field(default=238, ge=1, le=300)
    chain: List[DecayStep] = Field(default_factory=list)
    title: str = ""

    @model_validator(mode="after")
    def validate_chain(self) -> "RadioactiveDecaySchema":
        if self.show_decay_chain and not self.chain:
            raise ValueError("show_decay_chain needs at least one step in `chain`.")
        if self.parent_a < self.parent_z:
            raise ValueError(
                f"parent_a ({self.parent_a}) cannot be less than parent_z "
                f"({self.parent_z}): N = A − Z would be negative."
            )
        return self


# ── Wave Optics: Huygens Wavefronts ───────────────────────────────────────────

class WavefrontSchema(BaseModel):
    wavefront_type: str = "plane"     # plane | spherical | cylindrical
    phenomenon: str = "propagation"   # propagation | reflection | refraction | diffraction
    n1: float = Field(default=1.0, ge=1.0, le=4.0)     # incident medium
    n2: float = Field(default=1.5, ge=1.0, le=4.0)     # second medium (refraction)
    incidence_angle: float = Field(default=40.0, ge=5.0, le=80.0)   # deg, to the normal
    show_wavelets: bool = True        # Huygens' secondary wavelets
    show_envelope: bool = True        # the new wavefront as their envelope
    show_rays: bool = True
    num_wavefronts: int = Field(default=4, ge=2, le=8)
    slit_width_ratio: float = Field(default=1.5, ge=0.4, le=6.0)   # a/λ, diffraction
    title: str = ""

    @field_validator("wavefront_type")
    @classmethod
    def validate_wavefront_type(cls, v: str) -> str:
        allowed = {"plane", "spherical", "cylindrical"}
        if v not in allowed:
            raise ValueError(f"Unknown wavefront_type '{v}'. Allowed: {sorted(allowed)}")
        return v

    @field_validator("phenomenon")
    @classmethod
    def validate_phenomenon(cls, v: str) -> str:
        allowed = {"propagation", "reflection", "refraction", "diffraction"}
        if v not in allowed:
            raise ValueError(f"Unknown phenomenon '{v}'. Allowed: {sorted(allowed)}")
        return v

    @model_validator(mode="after")
    def validate_refraction(self) -> "WavefrontSchema":
        if self.phenomenon == "refraction" and abs(self.n1 - self.n2) < 1e-9:
            raise ValueError(
                "Refraction needs n1 ≠ n2: with equal indices the wavefront does not "
                "bend and the figure asserts nothing."
            )
        return self


# ── Wave Optics: Polarisation ─────────────────────────────────────────────────

class PolarisationSchema(BaseModel):
    analyser_angle: float = Field(default=60.0, ge=0.0, le=180.0)   # θ between axes
    incident_intensity: float = Field(default=100.0, gt=0.0)        # I of the unpolarised beam
    show_malus_law: bool = True
    show_intensity_graph: bool = False    # I vs θ
    show_brewster: bool = False           # Brewster's-angle panel instead of the analyser
    n1: float = Field(default=1.0, ge=1.0, le=4.0)
    n2: float = Field(default=1.5, ge=1.0, le=4.0)
    title: str = ""

    @model_validator(mode="after")
    def validate_brewster(self) -> "PolarisationSchema":
        if self.show_brewster and abs(self.n1 - self.n2) < 1e-9:
            raise ValueError(
                "Brewster's angle needs n1 ≠ n2: arctan(n2/n1) = 45° with no "
                "polarising interface to speak of."
            )
        return self


# ── Measurement: Vernier Calipers / Screw Gauge ───────────────────────────────

class MeasuringInstrumentSchema(BaseModel):
    instrument: str = "vernier_calipers"   # vernier_calipers | screw_gauge

    # The value the instrument is drawn as DISPLAYING (the observed reading, before
    # any zero-error correction). cm for the vernier, mm for the screw gauge.
    reading: float = Field(default=2.34, ge=0.0)
    # Zero error in the same unit; corrected value = reading − zero_error.
    zero_error: float = 0.0

    vernier_divisions: int = Field(default=10, ge=5, le=50)     # vernier calipers
    main_scale_division: float = Field(default=0.1, gt=0.0)     # cm, vernier calipers
    circular_divisions: int = Field(default=50, ge=10, le=100)  # screw gauge
    pitch: float = Field(default=0.5, gt=0.0)                   # mm, screw gauge

    show_least_count: bool = True
    show_reading_breakdown: bool = True
    title: str = ""

    @field_validator("instrument")
    @classmethod
    def validate_instrument(cls, v: str) -> str:
        allowed = {"vernier_calipers", "screw_gauge"}
        if v not in allowed:
            raise ValueError(f"Unknown instrument '{v}'. Allowed: {sorted(allowed)}")
        return v

    @model_validator(mode="after")
    def validate_reading_range(self) -> "MeasuringInstrumentSchema":
        # Beyond these the drawn scale would run off the figure, and a reading that
        # cannot be SEEN on the scale defeats the whole point of the diagram.
        limit = 5.0 if self.instrument == "vernier_calipers" else 10.0
        unit = "cm" if self.instrument == "vernier_calipers" else "mm"
        if self.reading > limit:
            raise ValueError(
                f"reading {self.reading} {unit} exceeds the drawable scale "
                f"({limit} {unit}) for a {self.instrument}."
            )
        return self


# ── Rolling Motion ────────────────────────────────────────────────────────────

# k = I/MR² for each rolling body. The acceleration a = g·sinθ/(1 + k) and the race
# ranking follow from this one number, so it is the only thing stored.
ROLLING_BODY_K = {
    "ring": 1.0,
    "hollow_cylinder": 1.0,
    "disc": 0.5,
    "cylinder": 0.5,
    "solid_sphere": 0.4,
    "sphere": 0.4,
    "hollow_sphere": 2.0 / 3.0,
}


class RollingMotionSchema(BaseModel):
    body: str = "disc"        # disc | ring | sphere | cylinder | solid_sphere
                              # | hollow_sphere | hollow_cylinder
    incline_angle: float = Field(default=30.0, ge=5.0, le=75.0)
    gravity: float = Field(default=9.8, gt=0.0)
    show_friction: bool = True
    show_contact_point: bool = True      # v_contact = 0 — the conceptual question
    show_velocity_relation: bool = True  # v = ωR
    show_acceleration: bool = True       # a = g sinθ / (1 + I/MR²)
    show_race_ranking: bool = False      # which body reaches the bottom first
    title: str = ""

    @field_validator("body")
    @classmethod
    def validate_body(cls, v: str) -> str:
        if v not in ROLLING_BODY_K:
            raise ValueError(f"Unknown body '{v}'. Allowed: {sorted(ROLLING_BODY_K)}")
        return v


# ══════════════════════════════════════════════════════════════════════════════
# WAVE-3 EXTENSION SCHEMAS
# ══════════════════════════════════════════════════════════════════════════════

# ── Optics: Concave (Diverging) Lens ──────────────────────────────────────────

class ConcaveLensSchema(BaseModel):
    # A diverging lens has a NEGATIVE focal length. It always forms a virtual,
    # erect, diminished image on the same side as the object, for any real object.
    focal_length: float = Field(default=-120.0, lt=0.0)
    object_distance: float = Field(default=200.0, gt=0.0)   # magnitude, object to the left
    object_height: float = Field(default=80.0, ge=10.0)
    show_rays: bool = True
    show_image: bool = True
    show_focal_points: bool = True
    title: str = ""


# ── Optics: Convex (Diverging) Mirror ─────────────────────────────────────────

class ConvexMirrorSchema(BaseModel):
    # A convex mirror is diverging: with the Cartesian convention (distances
    # against the incident light are negative) its focal length is POSITIVE and
    # the image is always virtual, erect and diminished behind the mirror.
    focal_length: float = Field(default=120.0, gt=0.0)
    object_distance: float = Field(default=220.0, gt=0.0)   # magnitude, object in front
    object_height: float = Field(default=80.0, ge=10.0)
    show_rays: bool = True
    show_image: bool = True
    show_focal_points: bool = True
    title: str = ""


# ── Optical Instruments (microscopes / telescopes) ────────────────────────────

class OpticalInstrumentSchema(BaseModel):
    instrument: str = "compound_microscope"
    # compound_microscope | astronomical_telescope | simple_microscope
    # | terrestrial_telescope
    objective_focal_length: float = Field(default=1.5, gt=0.0)   # f_o, cm
    eyepiece_focal_length: float = Field(default=5.0, gt=0.0)    # f_e, cm
    tube_length: float = Field(default=16.0, gt=0.0)   # L, cm (compound microscope)
    near_point: float = Field(default=25.0, gt=0.0)    # D, cm (least distance of distinct vision)
    object_distance: float = Field(default=1.8, gt=0.0)   # cm, object for a microscope
    show_rays: bool = True
    show_image: bool = True
    show_magnification: bool = True
    title: str = ""

    @field_validator("instrument")
    @classmethod
    def validate_instrument(cls, v: str) -> str:
        allowed = {"compound_microscope", "astronomical_telescope",
                   "simple_microscope", "terrestrial_telescope"}
        if v not in allowed:
            raise ValueError(f"Unknown instrument '{v}'. Allowed: {sorted(allowed)}")
        return v


# ── Prism: Dispersion of White Light ──────────────────────────────────────────

class PrismDispersionSchema(BaseModel):
    prism_angle: float = Field(default=60.0, ge=20.0, le=80.0)      # apex angle A
    incident_angle: float = Field(default=50.0, ge=10.0, le=85.0)   # angle of incidence i
    # n_violet > n_red: violet is refracted MORE, so it deviates most. If this
    # were violated the spectrum would come out reversed.
    n_red: float = Field(default=1.513, gt=1.0, le=3.0)
    n_violet: float = Field(default=1.532, gt=1.0, le=3.0)
    show_spectrum: bool = True
    show_angles: bool = False
    title: str = ""

    @model_validator(mode="after")
    def validate_dispersion(self) -> "PrismDispersionSchema":
        if self.n_violet <= self.n_red:
            raise ValueError(
                f"n_violet ({self.n_violet}) must exceed n_red ({self.n_red}): "
                "normal dispersion refracts violet more than red."
            )
        return self


# ── Atomic Energy Level Diagram ───────────────────────────────────────────────

class EnergyLevel(BaseModel):
    n: int = Field(ge=1, le=12)
    energy: Optional[float] = None    # eV; derived as -13.6/n² for hydrogen if omitted
    label: str = ""


class EnergyTransition(BaseModel):
    from_n: int = Field(ge=1, le=12)
    to_n: int = Field(ge=1, le=12)
    series: str = ""    # optional: lyman | balmer | paschen | brackett | pfund
    label: str = ""

    @model_validator(mode="after")
    def validate_transition(self) -> "EnergyTransition":
        if self.from_n == self.to_n:
            raise ValueError("A transition must change level: from_n ≠ to_n.")
        return self


_SERIES_LANDING = {"lyman": 1, "balmer": 2, "paschen": 3, "brackett": 4, "pfund": 5}


class EnergyLevelDiagramSchema(BaseModel):
    element: str = "H"                 # hydrogen levels derived exactly
    levels: List[EnergyLevel] = Field(default_factory=list)   # auto n=1..max_level if empty
    max_level: int = Field(default=5, ge=2, le=8)
    transitions: List[EnergyTransition] = Field(default_factory=list)
    show_series: List[str] = Field(default_factory=list)      # e.g. ["lyman", "balmer"]
    show_ionisation: bool = True
    show_wavelengths: bool = True
    title: str = ""

    @field_validator("show_series")
    @classmethod
    def validate_series(cls, v: List[str]) -> List[str]:
        out = []
        for s in v:
            key = s.strip().lower()
            if key not in _SERIES_LANDING:
                raise ValueError(
                    f"Unknown series '{s}'. Allowed: {sorted(_SERIES_LANDING)}")
            out.append(key)
        return out


# ── Rutherford Alpha-particle Scattering ──────────────────────────────────────

class AlphaScatteringSchema(BaseModel):
    num_particles: int = Field(default=9, ge=3, le=21)
    impact_scale: float = Field(default=0.45, gt=0.0, le=2.0)   # k in tan(θ/2)=k/b
    show_nucleus: bool = True
    show_impact_parameter: bool = True
    title: str = ""


# ── Heat Engine / Refrigerator / Heat Pump ────────────────────────────────────

class HeatEngineSchema(BaseModel):
    mode: str = "engine"          # engine | refrigerator | heat_pump
    t_hot: float = Field(default=500.0, gt=0.0)     # K
    t_cold: float = Field(default=300.0, gt=0.0)    # K
    # Any two of Q1/Q2/W may be given; the third is DERIVED so that Q1 = W + Q2
    # holds exactly. Sensible per-mode defaults are used when omitted.
    q_hot: Optional[float] = Field(default=None)    # Q1 (J)
    q_cold: Optional[float] = Field(default=None)   # Q2 (J)
    work: Optional[float] = Field(default=None)     # W (J)
    show_carnot_limit: bool = True
    title: str = ""

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, v: str) -> str:
        allowed = {"engine", "refrigerator", "heat_pump"}
        if v not in allowed:
            raise ValueError(f"Unknown mode '{v}'. Allowed: {sorted(allowed)}")
        return v

    @model_validator(mode="after")
    def validate_temps(self) -> "HeatEngineSchema":
        if self.t_hot <= self.t_cold:
            raise ValueError(
                f"t_hot ({self.t_hot}) must exceed t_cold ({self.t_cold}): "
                "there is no engine between reservoirs at the same temperature."
            )
        return self


# ── Thermal Conduction through Slabs ──────────────────────────────────────────

class ConductionLayer(BaseModel):
    material: str = ""
    length: float = Field(gt=0.0)                  # m (thickness along the flow)
    thermal_conductivity: float = Field(gt=0.0)    # k, W/m·K
    area: float = Field(default=1.0, gt=0.0)       # m²


class ThermalConductionSchema(BaseModel):
    layers: List[ConductionLayer] = Field(default_factory=list)   # ≥1; default 2-slab
    arrangement: str = "series"       # series | parallel | single
    t_hot: float = 100.0              # °C
    t_cold: float = 0.0               # °C
    show_temperature_gradient: bool = True
    title: str = ""

    @field_validator("arrangement")
    @classmethod
    def validate_arrangement(cls, v: str) -> str:
        allowed = {"series", "parallel", "single"}
        if v not in allowed:
            raise ValueError(f"Unknown arrangement '{v}'. Allowed: {sorted(allowed)}")
        return v

    @model_validator(mode="after")
    def validate_temps(self) -> "ThermalConductionSchema":
        if self.t_hot <= self.t_cold:
            raise ValueError(
                f"t_hot ({self.t_hot}) must exceed t_cold ({self.t_cold}): "
                "heat flows from hot to cold, so there must be a drop to draw."
            )
        return self


# ── Gauss's Law: Gaussian Surface ─────────────────────────────────────────────

class GaussSurfaceSchema(BaseModel):
    charge_type: str = "point"     # point | line | plane | shell
    surface: str = "sphere"        # sphere | cylinder | pillbox (label of the surface)
    show_field_lines: bool = True
    show_flux: bool = True
    title: str = ""

    @field_validator("charge_type")
    @classmethod
    def validate_charge(cls, v: str) -> str:
        allowed = {"point", "line", "plane", "shell"}
        if v not in allowed:
            raise ValueError(f"Unknown charge_type '{v}'. Allowed: {sorted(allowed)}")
        return v

    @field_validator("surface")
    @classmethod
    def validate_surface(cls, v: str) -> str:
        allowed = {"sphere", "cylinder", "pillbox"}
        if v not in allowed:
            raise ValueError(f"Unknown surface '{v}'. Allowed: {sorted(allowed)}")
        return v


# ── Equipotential Lines and Field Lines ───────────────────────────────────────

class EquipotentialSchema(BaseModel):
    configuration: str = "point_charge"
    # point_charge | dipole | parallel_plates | two_like_charges
    show_field_lines: bool = True
    show_equipotentials: bool = True
    title: str = ""

    @field_validator("configuration")
    @classmethod
    def validate_config(cls, v: str) -> str:
        allowed = {"point_charge", "dipole", "parallel_plates", "two_like_charges"}
        if v not in allowed:
            raise ValueError(f"Unknown configuration '{v}'. Allowed: {sorted(allowed)}")
        return v


# ── Cyclotron ─────────────────────────────────────────────────────────────────

class CyclotronSchema(BaseModel):
    show_spiral: bool = True
    show_dees: bool = True
    show_magnetic_field: bool = True
    num_turns: int = Field(default=4, ge=1, le=8)
    title: str = ""


# ── Velocity Selector / Mass Spectrometer ─────────────────────────────────────

class VelocitySelectorSchema(BaseModel):
    mode: str = "velocity_selector"    # velocity_selector | mass_spectrometer
    e_field: float = Field(default=1.0e5, gt=0.0)      # V/m
    b_field: float = Field(default=0.2, gt=0.0)        # T
    charge: float = Field(default=1.6e-19, gt=0.0)     # C
    masses: List[float] = Field(default_factory=list)  # kg (spectrometer analyser)
    show_selected_velocity: bool = True
    title: str = ""

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, v: str) -> str:
        allowed = {"velocity_selector", "mass_spectrometer"}
        if v not in allowed:
            raise ValueError(f"Unknown mode '{v}'. Allowed: {sorted(allowed)}")
        return v


# ── X-ray Spectrum ────────────────────────────────────────────────────────────

class XraySpectrumSchema(BaseModel):
    # 80 kV exceeds the ~70 kV needed to knock out a tungsten K-electron, so the
    # characteristic Kα/Kβ lines are actually excited and visible.
    tube_voltage: float = Field(default=80.0, gt=0.0)   # kV
    target_element: str = "W"                            # label only
    target_z: int = Field(default=74, ge=3, le=100)      # drives Moseley Kα/Kβ
    show_characteristic: bool = True
    show_lambda_min: bool = True
    title: str = ""


# ── Beats ─────────────────────────────────────────────────────────────────────

class BeatsSchema(BaseModel):
    frequency1: float = Field(default=10.0, gt=0.0)   # Hz
    frequency2: float = Field(default=12.0, gt=0.0)   # Hz
    duration: float = Field(default=1.0, gt=0.0)      # s
    amplitude: float = Field(default=1.0, gt=0.0)
    show_envelope: bool = True
    title: str = ""


# ── Damped / Forced Oscillation ───────────────────────────────────────────────

class DampedOscillationSchema(BaseModel):
    mode: str = "damped"              # damped | forced_resonance
    damping_type: str = "under"       # under | critical | over  (damped mode)
    omega0: float = Field(default=6.2832, gt=0.0)     # natural angular freq, rad/s
    duration: float = Field(default=4.0, gt=0.0)      # s (damped mode)
    damping_values: List[float] = Field(default_factory=list)   # γ list (forced mode)
    title: str = ""

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, v: str) -> str:
        allowed = {"damped", "forced_resonance"}
        if v not in allowed:
            raise ValueError(f"Unknown mode '{v}'. Allowed: {sorted(allowed)}")
        return v

    @field_validator("damping_type")
    @classmethod
    def validate_damping(cls, v: str) -> str:
        allowed = {"under", "critical", "over"}
        if v not in allowed:
            raise ValueError(f"Unknown damping_type '{v}'. Allowed: {sorted(allowed)}")
        return v


# ── Collision ─────────────────────────────────────────────────────────────────

class CollisionSchema(BaseModel):
    collision_type: str = "elastic"   # elastic | perfectly_inelastic | oblique
    m1: float = Field(default=2.0, gt=0.0)   # kg
    m2: float = Field(default=1.0, gt=0.0)   # kg
    u1: float = Field(default=4.0)           # m/s (body 1, along +x)
    u2: float = Field(default=0.0)           # m/s (body 2)
    angle: float = Field(default=30.0, ge=5.0, le=85.0)   # oblique: body-1 scatter angle
    title: str = ""

    @field_validator("collision_type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        allowed = {"elastic", "perfectly_inelastic", "oblique"}
        if v not in allowed:
            raise ValueError(f"Unknown collision_type '{v}'. Allowed: {sorted(allowed)}")
        return v


# ── Banked Road ───────────────────────────────────────────────────────────────

class BankedRoadSchema(BaseModel):
    bank_angle: float = Field(default=30.0, ge=5.0, le=60.0)   # θ
    radius: float = Field(default=100.0, gt=0.0)               # m
    gravity: float = Field(default=9.8, gt=0.0)
    friction_coefficient: float = Field(default=0.0, ge=0.0, le=1.5)   # μ (0 ⇒ ideal)
    show_friction: bool = True
    show_forces: bool = True
    title: str = ""


# ── Electromagnetic Induction ─────────────────────────────────────────────────

class EMInductionSchema(BaseModel):
    phenomenon: str = "lenz_law"
    # lenz_law | motional_emf | eddy_currents | flux_change
    show_flux: bool = True
    show_induced_current: bool = True
    title: str = ""

    @field_validator("phenomenon")
    @classmethod
    def validate_phenomenon(cls, v: str) -> str:
        allowed = {"lenz_law", "motional_emf", "eddy_currents", "flux_change"}
        if v not in allowed:
            raise ValueError(f"Unknown phenomenon '{v}'. Allowed: {sorted(allowed)}")
        return v


# ── Nuclear Reactor Schematic ─────────────────────────────────────────────────

class NuclearReactorSchema(BaseModel):
    reactor_type: str = "PWR"      # PWR | generic
    show_labels: bool = True
    show_turbine: bool = True
    title: str = ""


# ── Band Theory of Solids ─────────────────────────────────────────────────────

class BandTheorySchema(BaseModel):
    material: str = "semiconductor"
    # conductor | semiconductor | insulator | n_type | p_type
    show_fermi: bool = True
    show_labels: bool = True
    title: str = ""

    @field_validator("material")
    @classmethod
    def validate_material(cls, v: str) -> str:
        allowed = {"conductor", "semiconductor", "insulator", "n_type", "p_type"}
        if v not in allowed:
            raise ValueError(f"Unknown material '{v}'. Allowed: {sorted(allowed)}")
        return v
