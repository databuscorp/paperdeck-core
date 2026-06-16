"""
Pydantic schemas for Biology diagram types (NEET-focused).
"""
from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


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
