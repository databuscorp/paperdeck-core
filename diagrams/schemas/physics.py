"""
Pydantic schemas for Physics diagram types.
"""
from __future__ import annotations

from enum import Enum
from typing import List, Optional, Tuple

from pydantic import BaseModel, Field, field_validator


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
