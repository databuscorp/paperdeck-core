"""
Pydantic schemas for Chemistry diagram types.
"""
from __future__ import annotations

from typing import List, Optional, Tuple

from pydantic import BaseModel, Field, field_validator


# ── Organic Structure (SMILES-based) ─────────────────────────────────────────

class OrganicStructureSchema(BaseModel):
    smiles: str
    name: Optional[str] = None
    show_hydrogens: bool = False
    kekulize: bool = True
    # EAS / directing-effect annotation
    show_eas_positions: bool = False       # label ortho / meta / para positions on ring
    activated_positions: List[str] = Field(default_factory=list)   # ["ortho","para"] → highlight those

    @field_validator("smiles")
    @classmethod
    def smiles_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("SMILES string cannot be empty")
        return v.strip()


# ── Inorganic Structure ───────────────────────────────────────────────────────

class InorganicAtom(BaseModel):
    symbol: str
    label: Optional[str] = None
    charge: Optional[str] = None    # e.g. "2+", "1-"
    x: Optional[float] = None
    y: Optional[float] = None


class InorganicBond(BaseModel):
    from_atom: int   # index into atoms list
    to_atom: int
    bond_type: str = "single"   # single | double | triple | dative


class InorganicStructureSchema(BaseModel):
    atoms: List[InorganicAtom]
    bonds: List[InorganicBond] = Field(default_factory=list)
    title: Optional[str] = None

    @field_validator("atoms")
    @classmethod
    def at_least_one_atom(cls, v):
        if not v:
            raise ValueError("At least one atom is required")
        return v


# ── Orbital Diagram ───────────────────────────────────────────────────────────

class OrbitalShell(BaseModel):
    shell: str              # e.g. "1s", "2s", "2p", "3d"
    electrons: int = Field(ge=0, le=14)
    max_electrons: int = Field(ge=1, le=14)
    sublevel_count: int = Field(default=1, ge=1, le=7)  # number of boxes (orbitals)


class OrbitalDiagramSchema(BaseModel):
    element: str
    electron_config: List[OrbitalShell]
    show_labels: bool = True
    show_arrows: bool = True
    aufbau_order: bool = True


# ── Reaction Coordinate Graph ─────────────────────────────────────────────────

class EnergyPoint(BaseModel):
    label: str
    energy: float   # relative energy value


class ReactionCoordinateSchema(BaseModel):
    reactant_label: str = "Reactants"
    product_label: str = "Products"
    reactant_energy: float = 0.0
    product_energy: float = -20.0
    activation_energy: float = 60.0
    transition_state_label: str = "Transition State"
    is_exothermic: Optional[bool] = None   # auto-calculated if None
    label_delta_h: bool = True
    label_ea: bool = True

    @field_validator("activation_energy")
    @classmethod
    def ea_must_be_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Activation energy must be positive")
        return v


# ── Electrochemical Cell ──────────────────────────────────────────────────────

class ElectrodeSpec(BaseModel):
    material: str = "Zn"
    ion_label: str = "Zn²⁺"
    solution_label: str = "ZnSO₄"


class ElectrochemicalCellSchema(BaseModel):
    anode_material: str = "Zn"
    anode_ion: str = "Zn²⁺"
    anode_solution: str = "ZnSO₄"
    cathode_material: str = "Cu"
    cathode_ion: str = "Cu²⁺"
    cathode_solution: str = "CuSO₄"
    cell_name: str = "Daniell Cell"
    show_salt_bridge: bool = True
    show_current: bool = True
    emf: Optional[float] = None          # cell EMF to display, None = don't show
    show_half_reactions: bool = True


# ── Equilibrium Graph ─────────────────────────────────────────────────────────

class EquilibriumGraphSchema(BaseModel):
    reactant_labels: List[str] = Field(default_factory=lambda: ["[A]", "[B]"])
    product_labels: List[str] = Field(default_factory=lambda: ["[C]"])
    equilibrium_time: float = Field(default=0.5, ge=0.1, le=0.9)
    show_kc_marker: bool = True
    title: str = ""
    x_label: str = "Time →"
    y_label: str = "Concentration"


# ── Titration Curve ───────────────────────────────────────────────────────────

class TitrationCurveSchema(BaseModel):
    acid_type: str = "strong"   # strong | weak
    base_type: str = "strong"   # strong | weak
    initial_ph: float = Field(default=1.0, ge=0.0, le=7.0)
    equivalence_ph: float = Field(default=7.0, ge=0.0, le=14.0)
    final_ph: float = Field(default=13.0, ge=7.0, le=14.0)
    titrant_label: str = "NaOH"
    analyte_label: str = "HCl"
    show_equivalence_point: bool = True
    show_half_equivalence: bool = False   # for weak acid (pKa point)
    title: str = ""


# ── SN1 / SN2 Mechanism ───────────────────────────────────────────────────────

class MechanismStep(BaseModel):
    step_num: int = 1
    description: str = ""
    arrow_type: str = "full"     # full (bond formation) | half (radical)


class SN1SN2MechanismSchema(BaseModel):
    mechanism_type: str = "sn2"          # sn1 | sn2
    substrate: str = "CH₃Br"
    nucleophile: str = "OH⁻"
    leaving_group: str = "Br⁻"
    product: str = "CH₃OH"
    intermediate: str = ""               # for SN1: carbocation intermediate
    show_curved_arrows: bool = True
    show_stereochemistry: bool = True
    show_energy_diagram: bool = False
    title: str = ""


# ── Newman Projection ─────────────────────────────────────────────────────────

class NewmanProjectionSchema(BaseModel):
    front_carbon: str = "C1"
    back_carbon: str = "C2"
    front_substituents: List[str] = Field(
        default_factory=lambda: ["H", "H", "H"])   # 3 substituents
    back_substituents: List[str] = Field(
        default_factory=lambda: ["H", "H", "H"])
    dihedral_angle: float = Field(default=60.0, ge=0.0, le=360.0)
    conformation_label: str = ""     # e.g. "anti", "gauche", "eclipsed"
    show_dihedral_annotation: bool = True
    title: str = ""


# ── Conformational Isomers ────────────────────────────────────────────────────

class ConformationalIsomersSchema(BaseModel):
    molecule_type: str = "cyclohexane"   # cyclohexane | ethane
    conformations: List[str] = Field(
        default_factory=lambda: ["chair", "boat"])   # for cyclohexane: chair | boat | twist_boat
    # for ethane: staggered | eclipsed
    show_labels: bool = True
    show_axial_equatorial: bool = True   # for chair cyclohexane
    substituents: List[str] = Field(default_factory=list)   # substituents on ring
    title: str = ""
