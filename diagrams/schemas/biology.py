"""
Pydantic schemas for Biology diagram types (NEET-focused).
"""
from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import (
    AliasChoices, BaseModel, ConfigDict, Field,
    field_validator, model_validator,
)


# ── 1. Cell Organelle Diagram ─────────────────────────────────────────────────

class CellDiagramSchema(BaseModel):
    cell_type: str = "animal"           # animal | plant
    labeled: bool = True
    highlight_organelle: Optional[str] = None  # focus arrow on one organelle
    # Visibility toggles
    show_nucleus: bool = True
    show_mitochondria: bool = True
    show_er: bool = True                # endoplasmic reticulum (rough + smooth)
    show_golgi: bool = True
    show_ribosome: bool = True
    show_lysosome: bool = True          # animal only
    show_vacuole: bool = True
    show_chloroplast: bool = False      # plant only  — auto-enabled when cell_type="plant"
    show_cell_wall: bool = False        # plant only  — auto-enabled when cell_type="plant"
    show_centriole: bool = True         # animal only
    title: str = ""


# ── 2. DNA Structure ──────────────────────────────────────────────────────────

class DNAStructureSchema(BaseModel):
    structure_type: str = "double_helix"  # double_helix | replication_fork
    num_base_pairs: int = Field(default=10, ge=5, le=20)
    show_base_labels: bool = True    # A / T / G / C labels on rungs
    show_labels: bool = True         # backbone, hydrogen bond labels
    title: str = ""


# ── 3. Cell Division ──────────────────────────────────────────────────────────

class CellDivisionSchema(BaseModel):
    division_type: str = "mitosis"   # mitosis | meiosis
    stage: str = "metaphase"
    # mitosis stages: prophase | metaphase | anaphase | telophase | cytokinesis
    # meiosis stages: prophase_1 | metaphase_1 | anaphase_1 | telophase_1
    #                 prophase_2 | metaphase_2 | anaphase_2 | telophase_2
    num_chromosome_pairs: int = Field(default=2, ge=1, le=4)
    show_spindle: bool = True
    show_labels: bool = True
    title: str = ""

    @field_validator("stage")
    @classmethod
    def normalise_stage(cls, v: str) -> str:
        return v.lower().strip().replace(" ", "_").replace("-", "_")


# ── 4. Heart Diagram ──────────────────────────────────────────────────────────

class HeartDiagramSchema(BaseModel):
    show_labels: bool = True
    show_blood_flow: bool = True     # directional arrows on vessels
    show_valves: bool = True
    title: str = ""


# ── 5. Nephron Diagram ────────────────────────────────────────────────────────

class NephronDiagramSchema(BaseModel):
    show_labels: bool = True
    show_blood_vessels: bool = True  # afferent/efferent arterioles + capillaries
    highlight_region: Optional[str] = None   # bowman_capsule | pct | loop_of_henle | dct | collecting_duct
    title: str = ""


# ── 6. Neuron Diagram ─────────────────────────────────────────────────────────

class NeuronDiagramSchema(BaseModel):
    neuron_type: str = "myelinated"  # myelinated | unmyelinated
    show_labels: bool = True
    show_impulse_direction: bool = True
    title: str = ""


# ── 7. Food Web ───────────────────────────────────────────────────────────────

class FoodWebNode(BaseModel):
    id: str
    label: str
    trophic_level: int = Field(default=1, ge=1, le=5)


class FoodWebEdge(BaseModel):
    from_id: str   # prey
    to_id: str     # predator


class FoodWebSchema(BaseModel):
    nodes: List[FoodWebNode] = Field(default_factory=list)
    edges: List[FoodWebEdge] = Field(default_factory=list)
    title: str = ""

    @field_validator("nodes")
    @classmethod
    def at_least_two(cls, v):
        if len(v) < 2:
            raise ValueError("Food web requires at least 2 organisms")
        return v


# ── 8. Food Chain ─────────────────────────────────────────────────────────────

class FoodChainSchema(BaseModel):
    organisms: List[str] = Field(min_length=2, max_length=8)
    title: str = ""


# ── 9. Ecological Pyramid ─────────────────────────────────────────────────────

class EcologicalPyramidLevel(BaseModel):
    label: str
    value: Optional[float] = None    # biomass / energy / number value
    unit: str = ""


class EcologicalPyramidSchema(BaseModel):
    pyramid_type: str = "biomass"    # biomass | energy | numbers
    levels: List[EcologicalPyramidLevel] = Field(min_length=2, max_length=6)
    title: str = ""


# ── 10. Punnett Square ────────────────────────────────────────────────────────

class PunnettSquareSchema(BaseModel):
    """
    Monohybrid  → alleles are 1 locus each:  ["A", "a"]              → 2x2 grid
    Dihybrid    → alleles are 2 loci each:   ["AB","Ab","aB","ab"]   → 4x4 grid
    The grid is sized from len(parent1_alleles) x len(parent2_alleles).
    """
    parent1_alleles: List[str] = Field(min_length=1, max_length=8)   # grid columns
    parent2_alleles: List[str] = Field(min_length=1, max_length=8)   # grid rows
    trait_name: Optional[str] = None
    parent1_label: Optional[str] = None
    parent2_label: Optional[str] = None
    show_genotype_ratio: bool = True
    show_phenotype_ratio: bool = True
    # genotype → phenotype, e.g. {"AA": "Tall", "Aa": "Tall", "aa": "Short"}
    phenotype_map: Optional[Dict[str, str]] = None
    title: str = ""

    @field_validator("parent1_alleles", "parent2_alleles")
    @classmethod
    def validate_gametes(cls, v: List[str]) -> List[str]:
        cleaned = [a.strip() for a in v]
        if any(not a for a in cleaned):
            raise ValueError("Allele entries must be non-empty strings")
        if any(not a.isalpha() for a in cleaned):
            raise ValueError("Allele entries must contain letters only (e.g. 'A', 'aB')")
        loci = {len(a) for a in cleaned}
        if len(loci) > 1:
            raise ValueError(
                "All gametes of a parent must cover the same number of loci "
                "(e.g. ['A','a'] for monohybrid, ['AB','Ab','aB','ab'] for dihybrid)"
            )
        n = len(cleaned)
        if n & (n - 1) != 0:            # not a power of two → not a valid gamete set
            raise ValueError(
                f"Gamete count must be a power of 2 (2 = monohybrid, 4 = dihybrid); got {n}"
            )
        return cleaned

    @model_validator(mode="after")
    def validate_grid(self) -> "PunnettSquareSchema":
        loci1 = len(self.parent1_alleles[0])
        loci2 = len(self.parent2_alleles[0])
        if loci1 != loci2:
            raise ValueError(
                "Both parents must have the same number of loci per gamete "
                f"(parent1 has {loci1}, parent2 has {loci2})"
            )
        return self


# ── 11. Pedigree Chart ────────────────────────────────────────────────────────

class PedigreeIndividual(BaseModel):
    id: str
    generation: int = Field(default=1, ge=1, le=8)   # 1 = topmost generation
    sex: str = "male"                                 # male | female
    affected: bool = False                            # True → shaded symbol
    label: Optional[str] = None                       # optional caption under the symbol

    @field_validator("sex")
    @classmethod
    def normalise_sex(cls, v: str) -> str:
        s = v.lower().strip()
        if s in ("m", "male"):
            return "male"
        if s in ("f", "female"):
            return "female"
        raise ValueError("sex must be 'male' or 'female'")


class PedigreeMating(BaseModel):
    parent1_id: str
    parent2_id: str
    child_ids: List[str] = Field(default_factory=list)


class PedigreeChartSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    individuals: List[PedigreeIndividual] = Field(min_length=1, max_length=40)
    matings: List[PedigreeMating] = Field(
        default_factory=list,
        validation_alias=AliasChoices("matings", "edges"),
    )
    title: str = ""
    show_legend: bool = True

    @model_validator(mode="after")
    def validate_references(self) -> "PedigreeChartSchema":
        ids = [ind.id for ind in self.individuals]
        if len(set(ids)) != len(ids):
            raise ValueError("Individual ids must be unique")
        known = set(ids)
        for mating in self.matings:
            for ref in (mating.parent1_id, mating.parent2_id, *mating.child_ids):
                if ref not in known:
                    raise ValueError(
                        f"Mating references unknown individual id '{ref}'"
                    )
            if mating.parent1_id == mating.parent2_id:
                raise ValueError(
                    f"A mating needs two distinct parents (got '{mating.parent1_id}' twice)"
                )
        return self


def _enum_validator(field: str, allowed: tuple):
    """Lower-case + underscore an enum-ish field, rejecting unknown values."""
    def _check(v: str) -> str:
        s = v.lower().strip().replace(" ", "_").replace("-", "_")
        if s not in allowed:
            raise ValueError(f"{field} must be one of {list(allowed)}; got '{v}'")
        return s
    return _check


# ── 12. Flower Structure ──────────────────────────────────────────────────────

class FlowerStructureSchema(BaseModel):
    flower_type: str = "typical"        # typical | hibiscus
    show_labels: bool = True
    # A half (median longitudinal) section cuts the ovary open so the ovules show.
    show_half_section: bool = True
    highlight_part: Optional[str] = None   # sepal | petal | anther | filament |
                                           # stigma | style | ovary | ovule |
                                           # receptacle | pedicel
    title: str = ""

    _norm_type = field_validator("flower_type")(
        _enum_validator("flower_type", ("typical", "hibiscus"))
    )


# ── 13. Eye Diagram ───────────────────────────────────────────────────────────

class EyeDiagramSchema(BaseModel):
    show_labels: bool = True
    show_light_rays: bool = True
    defect: str = "none"                # none | myopia | hypermetropia
    highlight_part: Optional[str] = None
    title: str = ""

    _norm_defect = field_validator("defect")(
        _enum_validator("defect", ("none", "myopia", "hypermetropia"))
    )


# ── 14. Digestive System ──────────────────────────────────────────────────────

class DigestiveSystemSchema(BaseModel):
    show_labels: bool = True
    highlight_organ: Optional[str] = None   # stomach | liver | pancreas |
                                            # small_intestine | large_intestine | ...
    title: str = ""


# ── 15. Respiratory System ────────────────────────────────────────────────────

class RespiratorySystemSchema(BaseModel):
    show_labels: bool = True
    show_alveoli_inset: bool = True     # magnified alveolus + capillary gas exchange
    highlight_organ: Optional[str] = None   # trachea | bronchi | lungs | diaphragm | ...
    title: str = ""


# ── 16. Plant Tissue (transverse section) ─────────────────────────────────────

class PlantTissueSchema(BaseModel):
    section_type: str = "dicot_stem"
    # dicot_stem | monocot_stem | dicot_root | monocot_root | leaf
    show_labels: bool = True
    highlight_tissue: Optional[str] = None  # xylem | phloem | cambium | endodermis | ...
    title: str = ""

    _norm_section = field_validator("section_type")(
        _enum_validator(
            "section_type",
            ("dicot_stem", "monocot_stem", "dicot_root", "monocot_root", "leaf"),
        )
    )


# ── 17. Organelle Detail ──────────────────────────────────────────────────────

class OrganelleDetailSchema(BaseModel):
    organelle: str = "mitochondrion"    # mitochondrion | chloroplast | nucleus
    show_labels: bool = True
    highlight_part: Optional[str] = None
    title: str = ""

    _norm_organelle = field_validator("organelle")(
        _enum_validator("organelle", ("mitochondrion", "chloroplast", "nucleus"))
    )


# ── 18. Metabolic Cycle ───────────────────────────────────────────────────────

class CycleStep(BaseModel):
    label: str                          # node text, e.g. "Citrate (6C)"
    edge_label: Optional[str] = None    # enzyme / co-factor on the arrow LEAVING it


class MetabolicCycleSchema(BaseModel):
    cycle: str = "krebs"
    # krebs | calvin | glycolysis | nitrogen | carbon | urea
    steps: Optional[List[CycleStep]] = Field(default=None, max_length=14)
    layout: Optional[str] = None        # circular | linear — defaults from `cycle`
    show_labels: bool = True            # enzyme / co-factor edge labels
    title: str = ""

    _norm_cycle = field_validator("cycle")(
        _enum_validator(
            "cycle",
            ("krebs", "calvin", "glycolysis", "nitrogen", "carbon", "urea"),
        )
    )

    @field_validator("layout")
    @classmethod
    def normalise_layout(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        return _enum_validator("layout", ("circular", "linear"))(v)

    @field_validator("steps")
    @classmethod
    def enough_steps(cls, v: Optional[List[CycleStep]]) -> Optional[List[CycleStep]]:
        if v is not None and len(v) < 2:
            raise ValueError("A step override needs at least 2 steps")
        return v


# ── 19. Gel Electrophoresis ───────────────────────────────────────────────────

class GelBand(BaseModel):
    size_bp: int = Field(gt=0)
    intensity: float = Field(default=1.0, ge=0.15, le=1.0)   # band darkness


class GelLane(BaseModel):
    label: str
    bands: List[GelBand] = Field(default_factory=list, max_length=15)


class GelElectrophoresisSchema(BaseModel):
    lanes: List[GelLane] = Field(min_length=1, max_length=10)
    ladder_sizes: List[int] = Field(default_factory=list, max_length=15)
    show_migration_arrow: bool = True
    show_wells: bool = True
    gel_label: str = ""                 # e.g. "0.8% agarose gel"
    title: str = ""

    @field_validator("ladder_sizes")
    @classmethod
    def positive_sizes(cls, v: List[int]) -> List[int]:
        if any(s <= 0 for s in v):
            raise ValueError("ladder_sizes must all be positive fragment sizes in bp")
        return v


# ── 20. Plasmid Map ───────────────────────────────────────────────────────────

class PlasmidFeature(BaseModel):
    name: str
    start_bp: int = Field(ge=0)
    end_bp: int = Field(ge=0)
    feature_type: str = "gene"
    # ori | resistance_marker | promoter | insert | gene

    _norm_ftype = field_validator("feature_type")(
        _enum_validator(
            "feature_type",
            ("ori", "resistance_marker", "promoter", "insert", "gene"),
        )
    )


class RestrictionSite(BaseModel):
    enzyme: str
    position_bp: int = Field(ge=0)


class PlasmidMapSchema(BaseModel):
    plasmid_name: str = "Plasmid"
    size_bp: int = Field(default=4361, gt=0)
    features: List[PlasmidFeature] = Field(default_factory=list, max_length=12)
    restriction_sites: List[RestrictionSite] = Field(default_factory=list,
                                                     max_length=12)
    show_labels: bool = True
    title: str = ""

    @model_validator(mode="after")
    def positions_within_plasmid(self) -> "PlasmidMapSchema":
        for f in self.features:
            for bp in (f.start_bp, f.end_bp):
                if bp > self.size_bp:
                    raise ValueError(
                        f"Feature '{f.name}' position {bp} bp lies outside the "
                        f"{self.size_bp} bp plasmid"
                    )
        for s in self.restriction_sites:
            if s.position_bp > self.size_bp:
                raise ValueError(
                    f"Restriction site '{s.enzyme}' at {s.position_bp} bp lies "
                    f"outside the {self.size_bp} bp plasmid"
                )
        return self


# ── 21. Brain Diagram ─────────────────────────────────────────────────────────

class BrainDiagramSchema(BaseModel):
    show_labels: bool = True
    highlight_region: Optional[str] = None   # cerebrum | cerebellum | medulla |
                                             # pons | midbrain | thalamus | ...
    title: str = ""


# ── 22. Reproductive System ───────────────────────────────────────────────────

class ReproductiveSystemSchema(BaseModel):
    system: str = "human_male"          # human_male | human_female
    show_labels: bool = True
    highlight_part: Optional[str] = None    # testis | epididymis | vas_deferens |
                                            # prostate | ovary | fallopian_tube |
                                            # uterus | cervix | vagina | ...
    title: str = ""

    _norm_system = field_validator("system")(
        _enum_validator("system", ("human_male", "human_female"))
    )


# ── 23. Gametogenesis ─────────────────────────────────────────────────────────

class GametogenesisSchema(BaseModel):
    process: str = "spermatogenesis"    # spermatogenesis | oogenesis
    diploid_number: int = Field(default=46, ge=2, le=200)   # 2n; n is derived
    show_labels: bool = True
    show_chromosome_number: bool = True     # 2n / n badge on every stage
    title: str = ""

    _norm_process = field_validator("process")(
        _enum_validator("process", ("spermatogenesis", "oogenesis"))
    )

    @field_validator("diploid_number")
    @classmethod
    def must_be_even(cls, v: int) -> int:
        if v % 2:
            raise ValueError("diploid_number (2n) must be even — n = 2n / 2")
        return v


# ── 24. Embryo Sac ────────────────────────────────────────────────────────────

class EmbryoSacSchema(BaseModel):
    show_labels: bool = True
    show_double_fertilisation: bool = False  # pollen tube + syngamy + triple fusion
    show_nuclei_count: bool = True           # "7-celled, 8-nucleate" caption
    title: str = ""


# ── 25. Anther T.S. ───────────────────────────────────────────────────────────

class AntherTSSchema(BaseModel):
    stage: str = "mature"               # young | mature | dehisced
    show_labels: bool = True
    highlight_layer: Optional[str] = None   # epidermis | endothecium |
                                            # middle_layers | tapetum |
                                            # sporogenous_tissue | pollen |
                                            # connective | vascular_bundle
    title: str = ""

    _norm_stage = field_validator("stage")(
        _enum_validator("stage", ("young", "mature", "dehisced"))
    )


# ── 26. Sarcomere ─────────────────────────────────────────────────────────────

class SarcomereSchema(BaseModel):
    state: str = "relaxed"              # relaxed | contracted
    show_labels: bool = True
    show_bands: bool = True             # A / I / H band shading + brackets
    show_sliding_filament: bool = False  # relaxed AND contracted, one above the other
    title: str = ""

    _norm_state = field_validator("state")(
        _enum_validator("state", ("relaxed", "contracted"))
    )


# ── 27. Population Growth ─────────────────────────────────────────────────────

class PopulationGrowthSchema(BaseModel):
    model: str = "logistic"             # exponential | logistic | both
    r: float = Field(default=0.3, gt=0, le=3.0)        # intrinsic rate of increase
    N0: float = Field(default=10.0, gt=0)              # initial population
    K: float = Field(default=500.0, gt=0)              # carrying capacity
    t_max: float = Field(default=40.0, gt=0, le=500.0)
    show_labels: bool = True
    show_phases: bool = True            # lag / log / stationary
    show_equations: bool = True
    title: str = ""

    _norm_model = field_validator("model")(
        _enum_validator("model", ("exponential", "logistic", "both"))
    )

    @model_validator(mode="after")
    def n0_below_k(self) -> "PopulationGrowthSchema":
        if self.N0 >= self.K:
            raise ValueError(
                "N0 must be below the carrying capacity K, otherwise the "
                "logistic curve cannot rise towards K"
            )
        return self


# ── 28. lac Operon ────────────────────────────────────────────────────────────

class LacOperonSchema(BaseModel):
    state: str = "inducible_on"         # inducible_on | repressed_off
    show_labels: bool = True
    show_products: bool = True          # mRNA → the three enzymes
    title: str = ""

    _norm_state = field_validator("state")(
        _enum_validator("state", ("inducible_on", "repressed_off"))
    )


# ── 29. Microbe Structure ─────────────────────────────────────────────────────

class MicrobeStructureSchema(BaseModel):
    microbe: str = "bacteriophage"      # bacteriophage | virus_tmv | virus_hiv |
                                        # bacterium
    show_labels: bool = True
    highlight_part: Optional[str] = None
    title: str = ""

    _norm_microbe = field_validator("microbe")(
        _enum_validator(
            "microbe",
            ("bacteriophage", "virus_tmv", "virus_hiv", "bacterium"),
        )
    )


# ── 30. Ear Diagram ───────────────────────────────────────────────────────────

class EarDiagramSchema(BaseModel):
    show_labels: bool = True
    show_regions: bool = True           # external / middle / internal ear bands
    show_cochlea_inset: bool = True     # section through one turn → organ of Corti
    highlight_part: Optional[str] = None
    title: str = ""


# ── 31. Endocrine System ──────────────────────────────────────────────────────

class EndocrineSystemSchema(BaseModel):
    view: str = "gland_locations"       # gland_locations | feedback_loop |
                                        # hormone_table
    axis: str = "thyroid"               # thyroid | adrenal | gonad  (feedback_loop)
    show_hormones: bool = True          # name the hormone alongside each gland
    highlight_gland: Optional[str] = None
    title: str = ""

    _norm_view = field_validator("view")(
        _enum_validator(
            "view", ("gland_locations", "feedback_loop", "hormone_table")
        )
    )
    _norm_axis = field_validator("axis")(
        _enum_validator("axis", ("thyroid", "adrenal", "gonad"))
    )


# ── 32. Kranz Anatomy ─────────────────────────────────────────────────────────

class KranzAnatomySchema(BaseModel):
    pathway: str = "c4"                 # c3 | c4 | comparison
    show_labels: bool = True
    show_pathway: bool = True           # the C4 (Hatch–Slack) biochemistry arrows
    highlight_cell: Optional[str] = None    # mesophyll | bundle_sheath |
                                            # vascular_bundle
    title: str = ""

    _norm_pathway = field_validator("pathway")(
        _enum_validator("pathway", ("c3", "c4", "comparison"))
    )


# ── 33. Stomata ───────────────────────────────────────────────────────────────

class StomataSchema(BaseModel):
    state: str = "open"                 # open | closed | both
    guard_cell_shape: str = "kidney"    # kidney (dicot) | dumbbell (monocot/grass)
    show_labels: bool = True
    show_mechanism: bool = True         # turgid → open, flaccid → closed
    show_ion_flux: bool = True          # K⁺ and H₂O arrows
    title: str = ""

    _norm_state = field_validator("state")(
        _enum_validator("state", ("open", "closed", "both"))
    )
    _norm_shape = field_validator("guard_cell_shape")(
        _enum_validator("guard_cell_shape", ("kidney", "dumbbell"))
    )


# ══════════════════════════════════════════════════════════════════════════════
# WAVE 3 — the NEET units still uncovered (batches 1–5)
# ══════════════════════════════════════════════════════════════════════════════

# ── 34. Action Potential ──────────────────────────────────────────────────────

class ActionPotentialSchema(BaseModel):
    show_labels: bool = True
    show_phases: bool = True            # shaded depol / repol phase bands
    show_channels: bool = True          # Na⁺ / K⁺ channel-state annotations
    resting_mv: float = -70.0
    threshold_mv: float = -55.0
    peak_mv: float = 30.0
    title: str = ""

    @model_validator(mode="after")
    def ordered_levels(self) -> "ActionPotentialSchema":
        if not (self.resting_mv < self.threshold_mv < self.peak_mv):
            raise ValueError(
                "membrane levels must satisfy resting < threshold < peak "
                "(e.g. −70 < −55 < +30 mV)"
            )
        return self


# ── 35. Synapse (chemical) ────────────────────────────────────────────────────

class SynapseSchema(BaseModel):
    show_labels: bool = True
    show_neurotransmitter_flow: bool = True   # drawn release + diffusion arrows
    title: str = ""


# ── 36. Reflex Arc ────────────────────────────────────────────────────────────

class ReflexArcSchema(BaseModel):
    reflex_type: str = "monosynaptic"   # monosynaptic | polysynaptic
    show_labels: bool = True
    title: str = ""

    _norm_type = field_validator("reflex_type")(
        _enum_validator("reflex_type", ("monosynaptic", "polysynaptic"))
    )


# ── 37. Transcription / Translation (central dogma) ───────────────────────────

class TranscriptionTranslationSchema(BaseModel):
    stage: str = "both"                 # transcription | translation | both
    show_labels: bool = True
    title: str = ""

    _norm_stage = field_validator("stage")(
        _enum_validator("stage", ("transcription", "translation", "both"))
    )


# ── 38. Oxygen (Hb) Dissociation Curve ────────────────────────────────────────

class OxygenDissociationCurveSchema(BaseModel):
    show_bohr_shift: bool = True        # right-shifted curve (↑CO₂/↑temp/↓pH)
    show_p50: bool = True               # mark p50 on each curve
    curves: List[str] = Field(default_factory=lambda: ["normal", "bohr_right"])
    # normal | bohr_right | bohr_left | myoglobin
    show_loading_unloading: bool = True
    title: str = ""

    @field_validator("curves")
    @classmethod
    def known_curves(cls, v: List[str]) -> List[str]:
        allowed = ("normal", "bohr_right", "bohr_left", "myoglobin")
        cleaned = [_enum_validator("curves", allowed)(c) for c in v]
        if not cleaned:
            raise ValueError("at least one curve is required")
        return cleaned


# ── 39. Circulatory System (double circulation) ───────────────────────────────

class CirculatorySystemSchema(BaseModel):
    show_labels: bool = True
    highlight_circuit: Optional[str] = None   # pulmonary | systemic
    title: str = ""

    @field_validator("highlight_circuit")
    @classmethod
    def norm_circuit(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        return _enum_validator("highlight_circuit", ("pulmonary", "systemic"))(v)


# ── 40. Menstrual Cycle ───────────────────────────────────────────────────────

class MenstrualCycleSchema(BaseModel):
    show_hormones: bool = True          # FSH, LH, oestrogen, progesterone
    show_ovarian_phase: bool = True     # follicular / ovulation / luteal
    show_uterine_lining: bool = True    # endometrial thickness
    cycle_days: int = Field(default=28, ge=20, le=40)
    title: str = ""


# ── 41. Embryo Development ────────────────────────────────────────────────────

class EmbryoDevelopmentSchema(BaseModel):
    stage: str = "all"
    # zygote | cleavage | morula | blastula | gastrula | all | placenta
    show_labels: bool = True
    title: str = ""

    _norm_stage = field_validator("stage")(
        _enum_validator(
            "stage",
            ("zygote", "cleavage", "morula", "blastula", "gastrula", "all",
             "placenta"),
        )
    )


# ── 42. Seed Structure ────────────────────────────────────────────────────────

class SeedStructureSchema(BaseModel):
    seed_type: str = "dicot"            # dicot (bean) | monocot (maize)
    show_labels: bool = True
    show_germination: Optional[str] = None   # epigeal | hypogeal
    title: str = ""

    _norm_type = field_validator("seed_type")(
        _enum_validator("seed_type", ("dicot", "monocot"))
    )

    @field_validator("show_germination")
    @classmethod
    def norm_germ(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        return _enum_validator("show_germination", ("epigeal", "hypogeal"))(v)


# ── 43. Floral Diagram ────────────────────────────────────────────────────────

class FloralDiagramSchema(BaseModel):
    family: str = "solanaceae"          # solanaceae | fabaceae | liliaceae
    symmetry: Optional[str] = None      # actinomorphic | zygomorphic (defaults from family)
    show_formula: bool = True
    show_labels: bool = True
    title: str = ""

    _norm_family = field_validator("family")(
        _enum_validator("family", ("solanaceae", "fabaceae", "liliaceae"))
    )

    @field_validator("symmetry")
    @classmethod
    def norm_symmetry(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        return _enum_validator("symmetry", ("actinomorphic", "zygomorphic"))(v)


# ── 44. Plant Morphology ──────────────────────────────────────────────────────

class PlantMorphologySchema(BaseModel):
    feature: str = "venation"
    # venation | phyllotaxy | inflorescence | root_system | fruit_type
    variant: Optional[str] = None       # feature-specific; defaults per feature
    show_labels: bool = True
    title: str = ""

    _norm_feature = field_validator("feature")(
        _enum_validator(
            "feature",
            ("venation", "phyllotaxy", "inflorescence", "root_system",
             "fruit_type"),
        )
    )


# ── 45. Plant Life Cycle (alternation of generations) ─────────────────────────

class PlantLifeCycleSchema(BaseModel):
    group: str = "angiosperm"           # bryophyte | pteridophyte | angiosperm
    show_labels: bool = True
    show_ploidy: bool = True            # 2n / n badge at each stage
    title: str = ""

    _norm_group = field_validator("group")(
        _enum_validator("group", ("bryophyte", "pteridophyte", "angiosperm"))
    )


# ── 46. Photosynthesis Z-Scheme ───────────────────────────────────────────────

class PhotosynthesisZSchemeSchema(BaseModel):
    show_labels: bool = True
    show_photons: bool = True           # the two photon-excitation jumps
    show_products: bool = True          # NADPH / ATP / O₂
    title: str = ""


# ── 47. Electron Transport Chain ──────────────────────────────────────────────

class ElectronTransportChainSchema(BaseModel):
    show_proton_gradient: bool = True   # H⁺ pumped to intermembrane space
    show_atp_synthase: bool = True      # chemiosmosis at complex V
    show_labels: bool = True
    title: str = ""


# ── 48. Chromosome Structure / Karyotype ──────────────────────────────────────

class ChromosomeStructureSchema(BaseModel):
    view: str = "single"                # single | karyotype | sex_determination
    centromere: str = "metacentric"
    # metacentric | submetacentric | acrocentric | telocentric  (view=single)
    show_labels: bool = True
    title: str = ""

    _norm_view = field_validator("view")(
        _enum_validator("view", ("single", "karyotype", "sex_determination"))
    )
    _norm_centromere = field_validator("centromere")(
        _enum_validator(
            "centromere",
            ("metacentric", "submetacentric", "acrocentric", "telocentric"),
        )
    )


# ── 49. Animal Tissue ─────────────────────────────────────────────────────────

class AnimalTissueSchema(BaseModel):
    tissue: str = "squamous"
    # epithelial: squamous | cuboidal | columnar | ciliated
    # connective: areolar | adipose | bone | cartilage | blood
    # muscular:   striated | smooth | cardiac
    # nervous:    nervous
    show_labels: bool = True
    title: str = ""

    _norm_tissue = field_validator("tissue")(
        _enum_validator(
            "tissue",
            ("squamous", "cuboidal", "columnar", "ciliated",
             "areolar", "adipose", "bone", "cartilage", "blood",
             "striated", "smooth", "cardiac", "nervous"),
        )
    )


# ── 50. Animal Anatomy (NCERT sectional diagrams) ─────────────────────────────

class AnimalAnatomySchema(BaseModel):
    organism: str = "earthworm"         # frog | earthworm | cockroach
    system: str = "digestive"           # digestive | circulatory | nervous | reproductive
    show_labels: bool = True
    title: str = ""

    _norm_org = field_validator("organism")(
        _enum_validator("organism", ("frog", "earthworm", "cockroach"))
    )
    _norm_sys = field_validator("system")(
        _enum_validator(
            "system",
            ("digestive", "circulatory", "nervous", "reproductive"),
        )
    )


# ── 51. Immune Response ───────────────────────────────────────────────────────

class ImmuneResponseSchema(BaseModel):
    view: str = "antibody_structure"    # antibody_structure | response_curve
    show_labels: bool = True
    title: str = ""

    _norm_view = field_validator("view")(
        _enum_validator("view", ("antibody_structure", "response_curve"))
    )


# ── 52. Ecological Succession / Age Pyramid ───────────────────────────────────

class EcologicalSuccessionSchema(BaseModel):
    view: str = "succession"            # succession | age_pyramid
    succession_type: str = "primary"    # primary | secondary  (view=succession)
    pyramid_type: str = "expanding"     # expanding | stable | declining
    show_labels: bool = True
    title: str = ""

    _norm_view = field_validator("view")(
        _enum_validator("view", ("succession", "age_pyramid"))
    )
    _norm_succ = field_validator("succession_type")(
        _enum_validator("succession_type", ("primary", "secondary"))
    )
    _norm_pyr = field_validator("pyramid_type")(
        _enum_validator("pyramid_type", ("expanding", "stable", "declining"))
    )


# ── 53. Biotechnology Workflow ────────────────────────────────────────────────

class BiotechWorkflowSchema(BaseModel):
    process: str = "pcr"
    # pcr | recombinant_dna | dna_fingerprinting | gel_to_blot
    show_labels: bool = True
    title: str = ""

    _norm_process = field_validator("process")(
        _enum_validator(
            "process",
            ("pcr", "recombinant_dna", "dna_fingerprinting", "gel_to_blot"),
        )
    )


# ── 54. Labeled Schematic (config-defined template layer) ─────────────────────
# A generic "label the parts" diagram: primitive shapes + leader-line labels, authored
# as data. New biology diagrams (plant cell, neuron, flower…) become a config entry in
# diagrams/service/biology/templates.py — no new Python renderer. `template` pulls a named
# base from that registry; inline `shapes`/`labels` work standalone; supplying `labels`
# alongside a `template` overrides the template's labels (e.g. to relabel or blank them).

class SchematicShape(BaseModel):
    # kind: ellipse | circle | rect | polygon | line | path
    kind: str
    # Coordinates are on a 0–100 grid in both axes (origin top-left), so template authors
    # never deal with pixels. Which fields are read depends on `kind`.
    cx: Optional[float] = None
    cy: Optional[float] = None
    rx: Optional[float] = None
    ry: Optional[float] = None
    r: Optional[float] = None
    x: Optional[float] = None
    y: Optional[float] = None
    w: Optional[float] = None
    h: Optional[float] = None
    points: Optional[List[List[float]]] = None    # polygon / line vertices [[x,y],...]
    path: Optional[str] = None                     # SVG-path-style "M x y L x y ..." on the grid
    fill: str = "#ffffff"
    stroke: str = "#333333"
    stroke_width: float = Field(default=1.5, ge=0, le=8)

    _norm_kind = field_validator("kind")(
        _enum_validator("kind", ("ellipse", "circle", "rect", "polygon", "line", "path"))
    )


class SchematicLabel(BaseModel):
    text: str
    x: float                    # label anchor (grid coords)
    y: float
    target: Optional[List[float]] = None   # [tx, ty] the leader line points to; None = no leader


class LabeledSchematicSchema(BaseModel):
    template: str = ""                               # named base from BIOLOGY_TEMPLATES, or ""
    title: str = ""
    shapes: List[SchematicShape] = Field(default_factory=list, max_length=80)
    labels: List[SchematicLabel] = Field(default_factory=list, max_length=40)

    @model_validator(mode="after")
    def _need_content(self):
        # Must render SOMETHING: either a known template or inline shapes.
        if not self.template and not self.shapes:
            raise ValueError("labeled_schematic needs a 'template' name or inline 'shapes'")
        return self
