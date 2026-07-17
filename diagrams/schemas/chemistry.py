"""
Pydantic schemas for Chemistry diagram types.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

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


# ── Crystal Lattice (Solid State) ─────────────────────────────────────────────

_UNIT_CELLS = ("simple_cubic", "bcc", "fcc", "end_centred", "hcp")


class CrystalLatticeSchema(BaseModel):
    unit_cell: str = "fcc"              # simple_cubic | bcc | fcc | end_centred | hcp
    show_atoms: bool = True
    show_edges: bool = True
    show_unit_cell_box: bool = True
    atom_label: Optional[str] = None    # e.g. "Na", "Cu"
    show_coordination_number: bool = False
    show_packing_efficiency: bool = False
    show_atoms_per_cell: bool = True
    title: str = ""

    @field_validator("unit_cell")
    @classmethod
    def known_unit_cell(cls, v: str) -> str:
        key = v.strip().lower()
        if key not in _UNIT_CELLS:
            raise ValueError(f"unit_cell must be one of {list(_UNIT_CELLS)}")
        return key


# ── VSEPR Shape ───────────────────────────────────────────────────────────────

_VSEPR_GEOMETRIES = (
    "linear", "bent", "trigonal_planar", "trigonal_pyramidal", "tetrahedral",
    "trigonal_bipyramidal", "see_saw", "t_shaped", "linear_3",
    "octahedral", "square_planar", "square_pyramidal",
)


class VseprShapeSchema(BaseModel):
    geometry: str = "tetrahedral"
    central_atom: str = "A"
    ligand_atoms: List[str] = Field(default_factory=list)   # padded/truncated to the geometry
    lone_pairs: Optional[int] = Field(default=None, ge=0, le=3)   # None → geometry default
    bond_angle: Optional[float] = Field(default=None, gt=0.0, le=180.0)
    hybridisation: Optional[str] = None      # None → geometry default (e.g. "sp³d")
    show_lone_pairs: bool = True
    title: str = ""

    @field_validator("geometry")
    @classmethod
    def known_geometry(cls, v: str) -> str:
        key = v.strip().lower()
        if key not in _VSEPR_GEOMETRIES:
            raise ValueError(f"geometry must be one of {list(_VSEPR_GEOMETRIES)}")
        return key


# ── Molecular Orbital Diagram ─────────────────────────────────────────────────

class MolecularOrbital(BaseModel):
    label: str                       # e.g. "π*2p"
    energy: float                    # relative energy (larger = higher)
    electrons: int = Field(default=0, ge=0, le=2)
    orbital_type: str = "bonding"    # bonding | antibonding | nonbonding

    @field_validator("orbital_type")
    @classmethod
    def known_type(cls, v: str) -> str:
        key = v.strip().lower()
        if key not in ("bonding", "antibonding", "nonbonding"):
            raise ValueError("orbital_type must be bonding | antibonding | nonbonding")
        return key


class MoDiagramSchema(BaseModel):
    molecule: str = "O₂"                       # O₂ | N₂ | F₂ | CO | NO | He₂ | H₂ | B₂ | C₂ …
    atom_left: Optional[str] = None            # None → derived from `molecule`
    atom_right: Optional[str] = None
    electrons_left: Optional[int] = Field(default=None, ge=0, le=8)    # valence e⁻ override
    electrons_right: Optional[int] = Field(default=None, ge=0, le=8)
    orbitals: List[MolecularOrbital] = Field(default_factory=list)     # explicit override
    # auto → ≤14 total e⁻ uses the s–p-mixed (N₂-type) order, >14 the O₂-type order
    orbital_order: str = "auto"                # auto | n2_type | o2_type
    show_bond_order: bool = True
    show_magnetic_behaviour: bool = True
    title: str = ""

    @field_validator("orbital_order")
    @classmethod
    def known_order(cls, v: str) -> str:
        key = v.strip().lower()
        if key not in ("auto", "n2_type", "o2_type"):
            raise ValueError("orbital_order must be auto | n2_type | o2_type")
        return key


# ── Phase Diagram ─────────────────────────────────────────────────────────────

class PhaseDiagramSchema(BaseModel):
    substance: str = "water"          # water | co2 | generic
    show_triple_point: bool = True
    show_critical_point: bool = True
    show_regions: bool = True
    highlight_transition: Optional[str] = None   # sublimation | vaporisation | fusion
    title: str = ""

    @field_validator("substance")
    @classmethod
    def known_substance(cls, v: str) -> str:
        key = v.strip().lower().replace("₂", "2")
        if key in ("h2o", "ice"):
            key = "water"
        if key not in ("water", "co2", "generic"):
            raise ValueError("substance must be water | co2 | generic")
        return key


# ── Haworth / Fischer Projection ──────────────────────────────────────────────

class HaworthFischerSchema(BaseModel):
    projection: str = "haworth"        # fischer | haworth
    molecule: str = "glucose"          # glucose | fructose | ribose | galactose | generic
    anomer: str = "alpha"              # alpha | beta | none   (Haworth only)
    ring_size: Optional[str] = None    # pyranose | furanose | none → molecule default
    substituents: List[str] = Field(default_factory=list)   # explicit override, ring/chain order
    show_carbon_numbers: bool = True
    title: str = ""

    @field_validator("projection")
    @classmethod
    def known_projection(cls, v: str) -> str:
        key = v.strip().lower()
        if key not in ("fischer", "haworth"):
            raise ValueError("projection must be fischer | haworth")
        return key

    @field_validator("anomer")
    @classmethod
    def known_anomer(cls, v: str) -> str:
        key = v.strip().lower().replace("α", "alpha").replace("β", "beta")
        if key not in ("alpha", "beta", "none"):
            raise ValueError("anomer must be alpha | beta | none")
        return key

    @field_validator("molecule")
    @classmethod
    def known_molecule(cls, v: str) -> str:
        return v.strip().lower()


# ── Lab Apparatus ─────────────────────────────────────────────────────────────

_APPARATUS_SETUPS = (
    "simple_distillation", "fractional_distillation", "filtration", "titration",
    "reflux", "steam_distillation", "sublimation", "separating_funnel",
    "chromatography",
)


class LabApparatusSchema(BaseModel):
    setup: str = "simple_distillation"
    show_labels: bool = True
    labels: Dict[str, str] = Field(default_factory=dict)   # override default part names
    title: str = ""

    @field_validator("setup")
    @classmethod
    def known_setup(cls, v: str) -> str:
        key = v.strip().lower()
        if key not in _APPARATUS_SETUPS:
            raise ValueError(f"setup must be one of {list(_APPARATUS_SETUPS)}")
        return key


# ── Reaction Scheme (multi-step organic roadmap) ──────────────────────────────

_ARROW_TYPES = ("forward", "reversible", "equilibrium")
_SCHEME_LAYOUTS = ("horizontal", "grid", "branched")


class ReactionSpecies(BaseModel):
    label: str                              # the roadmap letter: "A", "B", "C" …
    smiles: Optional[str] = None            # drawn as a real structure when present
    name: Optional[str] = None
    formula: Optional[str] = None
    is_unknown: bool = False                # drawn as a boxed "?" — "identify B"

    @field_validator("label")
    @classmethod
    def label_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("species label cannot be empty")
        return v.strip()


class ReactionStep(BaseModel):
    from_label: str
    to_label: str
    reagent: str = ""            # printed ABOVE the arrow
    conditions: str = ""         # printed BELOW the arrow, e.g. "conc. H₂SO₄, 443 K"
    arrow_type: str = "forward"

    @field_validator("arrow_type")
    @classmethod
    def known_arrow(cls, v: str) -> str:
        key = v.strip().lower()
        if key not in _ARROW_TYPES:
            raise ValueError(f"arrow_type must be one of {list(_ARROW_TYPES)}")
        return key


class ReactionSchemeSchema(BaseModel):
    steps: List[ReactionStep]
    species: List[ReactionSpecies] = Field(default_factory=list)
    layout: str = "horizontal"
    show_structures: bool = True     # render each SMILES rather than the bare label
    title: str = ""

    @field_validator("steps")
    @classmethod
    def at_least_one_step(cls, v):
        if not v:
            raise ValueError("A reaction scheme needs at least one step")
        return v

    @field_validator("layout")
    @classmethod
    def known_layout(cls, v: str) -> str:
        key = v.strip().lower()
        if key not in _SCHEME_LAYOUTS:
            raise ValueError(f"layout must be one of {list(_SCHEME_LAYOUTS)}")
        return key


# ── Crystal Field Splitting ───────────────────────────────────────────────────

_CFS_GEOMETRIES = ("octahedral", "tetrahedral", "square_planar")


class CrystalFieldSplittingSchema(BaseModel):
    geometry: str = "octahedral"
    metal_ion: str = "Fe³⁺"
    ligand_field: str = "strong"          # strong (low-spin) | weak (high-spin)
    d_electrons: int = Field(default=5, ge=0, le=10)
    show_splitting_energy: bool = True    # the Δo / Δt gap and its label
    show_electron_filling: bool = True
    show_pairing_energy: bool = False
    show_cfse: bool = True
    show_magnetic_behaviour: bool = True
    title: str = ""

    @field_validator("geometry")
    @classmethod
    def known_geometry(cls, v: str) -> str:
        key = v.strip().lower()
        if key not in _CFS_GEOMETRIES:
            raise ValueError(f"geometry must be one of {list(_CFS_GEOMETRIES)}")
        return key

    @field_validator("ligand_field")
    @classmethod
    def known_field(cls, v: str) -> str:
        key = v.strip().lower()
        if key in ("low_spin", "low-spin", "strong_field"):
            key = "strong"
        if key in ("high_spin", "high-spin", "weak_field"):
            key = "weak"
        if key not in ("strong", "weak"):
            raise ValueError("ligand_field must be strong | weak")
        return key


# ── Chemical Kinetics Graph ───────────────────────────────────────────────────

_KINETICS_PLOTS = (
    "concentration_time", "ln_concentration_time", "inverse_concentration_time",
    "rate_vs_concentration", "arrhenius", "half_life",
)


class KineticsGraphSchema(BaseModel):
    plot: str = "ln_concentration_time"
    order: int = Field(default=1, ge=0, le=2)
    rate_constant: float = Field(default=0.05, gt=0.0)
    initial_concentration: float = Field(default=1.0, gt=0.0)
    activation_energy: float = Field(default=50.0, gt=0.0)      # kJ mol⁻¹
    temperature_range: Tuple[float, float] = (300.0, 400.0)     # K
    show_half_life: bool = False
    show_slope: bool = True
    show_linearity_note: bool = True
    title: str = ""

    @field_validator("plot")
    @classmethod
    def known_plot(cls, v: str) -> str:
        key = v.strip().lower()
        if key not in _KINETICS_PLOTS:
            raise ValueError(f"plot must be one of {list(_KINETICS_PLOTS)}")
        return key

    @field_validator("temperature_range")
    @classmethod
    def ascending_positive(cls, v):
        lo, hi = v
        if lo <= 0 or hi <= lo:
            raise ValueError("temperature_range must be (low, high) in kelvin with 0 < low < high")
        return v


# ── Colligative Properties Graph ──────────────────────────────────────────────

_COLLIGATIVE_PROPERTIES = (
    "vapour_pressure_lowering", "boiling_point_elevation", "freezing_point_depression",
    "osmotic_pressure", "raoult_ideal", "raoult_deviation",
)


class ColligativeGraphSchema(BaseModel):
    property: str = "boiling_point_elevation"
    solute_label: str = "solute"
    solvent_label: str = "water"
    mole_fraction: float = Field(default=0.10, ge=0.0, lt=1.0)   # x(solute) in the solution
    mole_fraction_range: Tuple[float, float] = (0.0, 1.0)
    deviation: str = "none"          # none | positive | negative  (non-ideal Raoult plots)
    show_ideal_line: bool = True
    show_azeotrope: bool = False
    kb: float = Field(default=0.52, gt=0.0)    # K kg mol⁻¹ (water)
    kf: float = Field(default=1.86, gt=0.0)    # K kg mol⁻¹ (water)
    molality: float = Field(default=1.0, gt=0.0)
    show_equations: bool = True
    title: str = ""

    @field_validator("property")
    @classmethod
    def known_property(cls, v: str) -> str:
        key = v.strip().lower()
        if key not in _COLLIGATIVE_PROPERTIES:
            raise ValueError(f"property must be one of {list(_COLLIGATIVE_PROPERTIES)}")
        return key

    @field_validator("deviation")
    @classmethod
    def known_deviation(cls, v: str) -> str:
        key = v.strip().lower()
        if key not in ("none", "positive", "negative"):
            raise ValueError("deviation must be none | positive | negative")
        return key

    @field_validator("mole_fraction_range")
    @classmethod
    def unit_interval(cls, v):
        lo, hi = v
        if not (0.0 <= lo < hi <= 1.0):
            raise ValueError("mole_fraction_range must satisfy 0 ≤ low < high ≤ 1")
        return v


# ── Organic Reaction Mechanism ────────────────────────────────────────────────

_MECHANISMS = (
    "e1", "e2", "electrophilic_aromatic_substitution", "markovnikov_addition",
    "anti_markovnikov", "aldol", "cannizzaro", "esterification",
    "free_radical_substitution",
)


class OrganicMechanismSchema(BaseModel):
    mechanism: str = "e1"
    substrate: Optional[str] = None      # None → the worked example for this mechanism
    reagent: Optional[str] = None
    intermediate: Optional[str] = None
    product: Optional[str] = None
    show_curved_arrows: bool = True
    show_intermediate: bool = True
    show_rule: bool = True               # Saytzeff / Markovnikov / anti-periplanar note
    title: str = ""

    @field_validator("mechanism")
    @classmethod
    def known_mechanism(cls, v: str) -> str:
        key = v.strip().lower().replace("-", "_").replace(" ", "_")
        aliases = {
            "eas": "electrophilic_aromatic_substitution",
            "markovnikov": "markovnikov_addition",
            "antimarkovnikov": "anti_markovnikov",
            "free_radical": "free_radical_substitution",
        }
        key = aliases.get(key, key)
        if key not in _MECHANISMS:
            raise ValueError(f"mechanism must be one of {list(_MECHANISMS)}")
        return key


# ── Hybridisation / Orbital Overlap ───────────────────────────────────────────

_HYBRIDISATIONS = ("sp", "sp2", "sp3", "sp3d", "sp3d2")


class HybridisationOverlapSchema(BaseModel):
    hybridisation: str = "sp2"
    bond_type: str = "both"            # sigma | pi | both
    molecule_example: str = ""         # e.g. "C₂H₄"; blank → the default for the hybrid
    show_orbital_lobes: bool = True
    show_bond_angle: bool = True       # angle is COMPUTED from the hybridisation
    show_unhybridised_p: bool = True
    title: str = ""

    @field_validator("hybridisation")
    @classmethod
    def known_hybridisation(cls, v: str) -> str:
        key = v.strip().lower().replace("³", "3").replace("²", "2").replace("¹", "")
        if key not in _HYBRIDISATIONS:
            raise ValueError(f"hybridisation must be one of {list(_HYBRIDISATIONS)}")
        return key

    @field_validator("bond_type")
    @classmethod
    def known_bond_type(cls, v: str) -> str:
        key = v.strip().lower().replace("σ", "sigma").replace("π", "pi")
        if key not in ("sigma", "pi", "both"):
            raise ValueError("bond_type must be sigma | pi | both")
        return key


# ── Adsorption Isotherm ───────────────────────────────────────────────────────

_ISOTHERMS = ("freundlich", "langmuir", "bet")


class AdsorptionIsothermSchema(BaseModel):
    isotherm: str = "freundlich"
    pressure_range: Tuple[float, float] = (0.0, 10.0)   # atm
    k: float = Field(default=1.0, gt=0.0)               # Freundlich k / Langmuir a
    n: float = Field(default=2.0, gt=1.0)               # Freundlich n (n > 1 always)
    monolayer_capacity: float = Field(default=4.0, gt=0.0)   # Langmuir/BET saturation x/m
    bet_c: float = Field(default=20.0, gt=0.0)         # BET constant
    show_saturation: bool = True
    show_linearised_form: bool = False
    show_physisorption_chemisorption: bool = False
    title: str = ""

    @field_validator("isotherm")
    @classmethod
    def known_isotherm(cls, v: str) -> str:
        key = v.strip().lower()
        if key not in _ISOTHERMS:
            raise ValueError(f"isotherm must be one of {list(_ISOTHERMS)}")
        return key

    @field_validator("pressure_range")
    @classmethod
    def ascending(cls, v):
        lo, hi = v
        if lo < 0 or hi <= lo:
            raise ValueError("pressure_range must be (low, high) with 0 ≤ low < high")
        return v


# ══════════════════════════════════════════════════════════════════════════════
# THIRD WAVE — inorganic / physical / organic units still uncovered
# ══════════════════════════════════════════════════════════════════════════════

# ── Electrolytic Cell (electrolysis) ──────────────────────────────────────────

class ElectrolyticCellSchema(BaseModel):
    # Electrolysis, NOT a galvanic cell: the battery DRIVES the reaction, so the
    # cathode is the NEGATIVE terminal and the anode the POSITIVE one — the exact
    # inverse of a Daniell cell. Cations still go to the cathode, anions to the
    # anode; it is the sign that flips, and that flip is the whole question.
    electrolyte: str = "molten NaCl"
    electrodes: str = "inert (graphite)"
    cation: Optional[str] = None            # None → looked up from the electrolyte
    anion: Optional[str] = None
    cathode_product: Optional[str] = None
    anode_product: Optional[str] = None
    cathode_half_reaction: Optional[str] = None
    anode_half_reaction: Optional[str] = None
    show_ion_migration: bool = True
    show_half_reactions: bool = True
    show_battery: bool = True
    title: str = ""


# ── Ionic Lattice (rock-salt & friends) ───────────────────────────────────────

_IONIC_LATTICES = ("nacl", "cscl", "zns_blende", "zns_wurtzite", "fluorite",
                   "antifluorite")

_IONIC_LATTICE_ALIASES = {
    "rock_salt": "nacl", "rocksalt": "nacl", "sodium_chloride": "nacl",
    "caesium_chloride": "cscl", "cesium_chloride": "cscl",
    "sphalerite": "zns_blende", "zinc_blende": "zns_blende", "blende": "zns_blende",
    "zincblende": "zns_blende",
    "wurtzite": "zns_wurtzite", "zns": "zns_blende",
    "fluorite_type": "fluorite", "caf2": "fluorite",
    "anti_fluorite": "antifluorite", "na2o": "antifluorite",
}


class IonicLatticeSchema(BaseModel):
    lattice_type: str = "nacl"
    cation: str = "Na⁺"
    anion: str = "Cl⁻"
    # r+/r− radius ratio. If supplied, the predicted coordination geometry is COMPUTED
    # from the radius-ratio rule and checked against lattice_type.
    radius_ratio: Optional[float] = Field(default=None, gt=0.0, lt=1.0)
    show_coordination: bool = True
    show_radius_ratio: bool = True
    title: str = ""

    @field_validator("lattice_type")
    @classmethod
    def known_lattice(cls, v: str) -> str:
        key = v.strip().lower().replace("-", "_").replace(" ", "_")
        key = _IONIC_LATTICE_ALIASES.get(key, key)
        if key not in _IONIC_LATTICES:
            raise ValueError(f"lattice_type must be one of {list(_IONIC_LATTICES)}")
        return key


# ── Solid State Point Defects ─────────────────────────────────────────────────

_DEFECTS = ("schottky", "frenkel", "interstitial", "substitutional", "f_centre")

_DEFECT_ALIASES = {
    "f_center": "f_centre", "fcentre": "f_centre", "f-centre": "f_centre",
    "colour_centre": "f_centre", "color_center": "f_centre",
}


class SolidDefectsSchema(BaseModel):
    defect: str = "schottky"
    cation: str = "Na⁺"
    anion: str = "Cl⁻"
    show_density_effect: bool = True
    title: str = ""

    @field_validator("defect")
    @classmethod
    def known_defect(cls, v: str) -> str:
        key = v.strip().lower().replace("-", "_").replace(" ", "_")
        key = _DEFECT_ALIASES.get(key, key)
        if key not in _DEFECTS:
            raise ValueError(f"defect must be one of {list(_DEFECTS)}")
        return key


# ── Coordination-Complex Isomerism ────────────────────────────────────────────

_ISOMERISMS = ("cis_trans", "fac_mer", "optical", "linkage", "ionisation",
               "coordination")
_ISOMER_GEOMETRIES = ("octahedral", "square_planar", "tetrahedral")

_ISOMERISM_ALIASES = {
    "geometric": "cis_trans", "geometrical": "cis_trans", "cis_and_trans": "cis_trans",
    "facial_meridional": "fac_mer", "fac_and_mer": "fac_mer",
    "optical_isomerism": "optical", "enantiomerism": "optical",
    "ionization": "ionisation", "ionisation_isomerism": "ionisation",
}


class ComplexIsomerismSchema(BaseModel):
    isomerism: str = "cis_trans"
    complex_formula: str = "[MA₄B₂]"
    geometry: str = "octahedral"
    metal: str = "M"
    ligands: List[str] = Field(default_factory=list)   # ["A","B"] etc.
    show_labels: bool = True
    title: str = ""

    @field_validator("isomerism")
    @classmethod
    def known_isomerism(cls, v: str) -> str:
        key = v.strip().lower().replace("-", "_").replace(" ", "_")
        key = _ISOMERISM_ALIASES.get(key, key)
        if key not in _ISOMERISMS:
            raise ValueError(f"isomerism must be one of {list(_ISOMERISMS)}")
        return key

    @field_validator("geometry")
    @classmethod
    def known_geometry(cls, v: str) -> str:
        key = v.strip().lower().replace("-", "_").replace(" ", "_")
        if key not in _ISOMER_GEOMETRIES:
            raise ValueError(f"geometry must be one of {list(_ISOMER_GEOMETRIES)}")
        return key


# ── Polymer Structure ─────────────────────────────────────────────────────────

_POLYMERS = ("polythene", "pvc", "nylon-6,6", "terylene", "bakelite",
             "natural_rubber")

_POLYMER_ALIASES = {
    "polyethylene": "polythene", "polyethene": "polythene", "polythene": "polythene",
    "poly_vinyl_chloride": "pvc", "polyvinyl_chloride": "pvc",
    "nylon66": "nylon-6,6", "nylon_6_6": "nylon-6,6", "nylon6,6": "nylon-6,6",
    "nylon-66": "nylon-6,6",
    "pet": "terylene", "dacron": "terylene", "polyester": "terylene",
    "phenol_formaldehyde": "bakelite",
    "rubber": "natural_rubber", "polyisoprene": "natural_rubber",
    "natural-rubber": "natural_rubber",
}


class PolymerStructureSchema(BaseModel):
    polymer: str = "polythene"
    show_monomer: bool = True
    show_repeating_unit: bool = True
    show_linkage: bool = True
    classification: Optional[str] = None      # None → from database (addition|condensation)
    title: str = ""

    @field_validator("polymer")
    @classmethod
    def known_polymer(cls, v: str) -> str:
        key = v.strip().lower().replace(" ", "_")
        key = _POLYMER_ALIASES.get(key, key)
        if key not in _POLYMERS:
            raise ValueError(f"polymer must be one of {list(_POLYMERS)}")
        return key


# ── Metallurgy Flowchart ──────────────────────────────────────────────────────

_METALLURGY = ("froth_flotation", "roasting", "calcination", "smelting",
               "refining", "full_extraction")

_METALLURGY_ALIASES = {
    "flotation": "froth_flotation", "froth_floatation": "froth_flotation",
    "reduction": "smelting", "electrolytic_refining": "refining",
    "extraction": "full_extraction", "full": "full_extraction",
}


class MetallurgyStep(BaseModel):
    label: str                       # box text, e.g. "Roasting"
    reagent: str = ""                # printed on the arrow leading IN

    @field_validator("label")
    @classmethod
    def label_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("step label cannot be empty")
        return v.strip()


class MetallurgyFlowchartSchema(BaseModel):
    process: str = "roasting"
    metal: str = "Zn"
    ore: str = "ZnS (zinc blende)"
    steps: List[MetallurgyStep] = Field(default_factory=list)   # [] → process default
    ellingham: bool = False
    title: str = ""

    @field_validator("process")
    @classmethod
    def known_process(cls, v: str) -> str:
        key = v.strip().lower().replace("-", "_").replace(" ", "_")
        key = _METALLURGY_ALIASES.get(key, key)
        if key not in _METALLURGY:
            raise ValueError(f"process must be one of {list(_METALLURGY)}")
        return key


# ── Industrial Process Flow ───────────────────────────────────────────────────

_INDUSTRIAL = ("haber", "contact", "ostwald", "solvay", "chlor_alkali")

_INDUSTRIAL_ALIASES = {
    "haber_bosch": "haber", "haber_process": "haber", "ammonia": "haber",
    "contact_process": "contact", "sulphuric_acid": "contact",
    "ostwald_process": "ostwald", "nitric_acid": "ostwald",
    "solvay_process": "solvay", "sodium_carbonate": "solvay",
    "chloralkali": "chlor_alkali", "chlor-alkali": "chlor_alkali",
    "chlor_alkali_process": "chlor_alkali",
}


class IndustrialProcessSchema(BaseModel):
    process: str = "haber"
    show_conditions: bool = True
    show_recycle: bool = True
    title: str = ""

    @field_validator("process")
    @classmethod
    def known_process(cls, v: str) -> str:
        key = v.strip().lower().replace(" ", "_")
        key = _INDUSTRIAL_ALIASES.get(key, key)
        if key not in _INDUSTRIAL:
            raise ValueError(f"process must be one of {list(_INDUSTRIAL)}")
        return key


# ── Protein Structure ─────────────────────────────────────────────────────────

_PROTEIN_LEVELS = ("primary", "secondary_helix", "secondary_sheet", "tertiary",
                   "peptide_bond")

_PROTEIN_ALIASES = {
    "alpha_helix": "secondary_helix", "helix": "secondary_helix",
    "beta_sheet": "secondary_sheet", "beta_pleated_sheet": "secondary_sheet",
    "sheet": "secondary_sheet", "peptide": "peptide_bond",
    "primary_structure": "primary",
}


class ProteinStructureSchema(BaseModel):
    level: str = "peptide_bond"
    sequence: List[str] = Field(default_factory=list)   # residue labels for `primary`
    show_hydrogen_bonds: bool = True
    show_r_groups: bool = True
    title: str = ""

    @field_validator("level")
    @classmethod
    def known_level(cls, v: str) -> str:
        key = v.strip().lower().replace("-", "_").replace(" ", "_")
        key = _PROTEIN_ALIASES.get(key, key)
        if key not in _PROTEIN_LEVELS:
            raise ValueError(f"level must be one of {list(_PROTEIN_LEVELS)}")
        return key


# ── Hydrogen Bonding ──────────────────────────────────────────────────────────

_HBOND_SUBSTANCES = ("water", "ice", "hf", "ammonia", "dna_base_pair", "ethanol")

_HBOND_ALIASES = {
    "h2o": "water", "liquid_water": "water",
    "hydrogen_fluoride": "hf", "nh3": "ammonia",
    "dna": "dna_base_pair", "base_pair": "dna_base_pair",
    "dna_base_pairs": "dna_base_pair", "alcohol": "ethanol",
}


class HydrogenBondingSchema(BaseModel):
    substance: str = "water"
    show_partial_charges: bool = True
    title: str = ""

    @field_validator("substance")
    @classmethod
    def known_substance(cls, v: str) -> str:
        key = v.strip().lower().replace("-", "_").replace(" ", "_")
        key = _HBOND_ALIASES.get(key, key)
        if key not in _HBOND_SUBSTANCES:
            raise ValueError(f"substance must be one of {list(_HBOND_SUBSTANCES)}")
        return key


# ── Resonance Structures ──────────────────────────────────────────────────────

_RESONANCE_SPECIES = ("benzene", "carbonate", "nitrate", "ozone")

_RESONANCE_ALIASES = {
    "c6h6": "benzene", "co3": "carbonate", "co3^2-": "carbonate",
    "carbonate_ion": "carbonate", "co3_2-": "carbonate",
    "no3": "nitrate", "no3^-": "nitrate", "nitrate_ion": "nitrate",
    "o3": "ozone",
}


class ResonanceStructuresSchema(BaseModel):
    species: str = "benzene"
    show_curved_arrows: bool = True
    show_hybrid: bool = True
    title: str = ""

    @field_validator("species")
    @classmethod
    def known_species(cls, v: str) -> str:
        key = v.strip().lower().replace(" ", "_")
        key = _RESONANCE_ALIASES.get(key, key)
        if key not in _RESONANCE_SPECIES:
            raise ValueError(f"species must be one of {list(_RESONANCE_SPECIES)}")
        return key


# ── Free-Radical Chain Mechanism ──────────────────────────────────────────────

_FREE_RADICAL_REACTIONS = ("methane_chlorination", "methane_bromination",
                           "ethane_chlorination", "chlorination_of_alkane")

_FREE_RADICAL_ALIASES = {
    "chlorination_of_methane": "methane_chlorination",
    "methane_chlorination": "methane_chlorination",
    "bromination_of_methane": "methane_bromination",
    "chlorination_of_ethane": "ethane_chlorination",
    "alkane_chlorination": "chlorination_of_alkane",
    "halogenation": "methane_chlorination",
}


class FreeRadicalMechanismSchema(BaseModel):
    reaction: str = "methane_chlorination"
    show_fish_hook_arrows: bool = True
    show_all_phases: bool = True
    title: str = ""

    @field_validator("reaction")
    @classmethod
    def known_reaction(cls, v: str) -> str:
        key = v.strip().lower().replace("-", "_").replace(" ", "_")
        key = _FREE_RADICAL_ALIASES.get(key, key)
        if key not in _FREE_RADICAL_REACTIONS:
            raise ValueError(f"reaction must be one of {list(_FREE_RADICAL_REACTIONS)}")
        return key
