"""
Schema validation layer.
Validates incoming JSON against the master DiagramSchema,
then delegates to type-specific schema validators.
Returns structured validation results.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import ValidationError

from diagrams.schemas.base import DiagramSchema, DiagramType
from diagrams.schemas.physics import (
    InclinedPlaneSchema, FreeBodyDiagramSchema, PulleySystemSchema,
    ProjectileMotionSchema, SpringBlockSchema, ConvexLensSchema,
    ConcaveMirrorSchema, WaveDiagramSchema,
    ThermoPVSchema, RayOpticsPrismSchema, ElectricFieldSchema,
    MagneticFieldSchema, CircularMotionSchema,
    DopplerEffectSchema, InterferencePatternSchema, BohrAtomSchema,
    CapacitorDielectricSchema, LCOscillationSchema,
)
from diagrams.schemas.chemistry import (
    OrganicStructureSchema, InorganicStructureSchema,
    OrbitalDiagramSchema, ReactionCoordinateSchema,
    ElectrochemicalCellSchema, EquilibriumGraphSchema, TitrationCurveSchema,
    SN1SN2MechanismSchema, NewmanProjectionSchema, ConformationalIsomersSchema,
)
from diagrams.schemas.mathematics import (
    FunctionGraphSchema, GeometryTriangleSchema, GeometryCircleSchema,
    CoordinateGeometrySchema, CalculusGraphSchema,
    ConicSectionSchema, VennDiagramSchema, NumberLineSchema,
    BarChartSchema, ScatterPlotSchema, Vector3DSchema,
)
from diagrams.schemas.circuits import (
    ResistorNetworkSchema, CapacitorNetworkSchema, BasicDCCircuitSchema,
)
from diagrams.schemas.biology import (
    CellDiagramSchema, DNAStructureSchema, CellDivisionSchema,
    HeartDiagramSchema, NephronDiagramSchema, NeuronDiagramSchema,
    FoodWebSchema, FoodChainSchema, EcologicalPyramidSchema,
)


# Maps (diagram_type, subtype) → Pydantic schema class for the `objects[0]` payload.
# The per-type schema is validated against the first item in schema["objects"]
# OR against the top-level schema dict itself (for single-object diagrams).
_SUBTYPE_SCHEMAS: Dict[str, Dict[str, Any]] = {
    DiagramType.PHYSICS: {
        "inclined_plane": InclinedPlaneSchema,
        "free_body_diagram": FreeBodyDiagramSchema,
        "pulley_system": PulleySystemSchema,
        "projectile_motion": ProjectileMotionSchema,
        "spring_block": SpringBlockSchema,
        "optics_convex_lens": ConvexLensSchema,
        "optics_concave_mirror": ConcaveMirrorSchema,
        "wave_diagram": WaveDiagramSchema,
        "thermodynamics_pv": ThermoPVSchema,
        "ray_optics_prism": RayOpticsPrismSchema,
        "electric_field_lines": ElectricFieldSchema,
        "magnetic_field_lines": MagneticFieldSchema,
        "circular_motion": CircularMotionSchema,
        "doppler_effect": DopplerEffectSchema,
        "interference_pattern": InterferencePatternSchema,
        "bohr_atom": BohrAtomSchema,
        "capacitor_dielectric": CapacitorDielectricSchema,
        "lc_oscillation": LCOscillationSchema,
    },
    DiagramType.CHEMISTRY: {
        "organic_structure": OrganicStructureSchema,
        "inorganic_structure": InorganicStructureSchema,
        "orbital_diagram": OrbitalDiagramSchema,
        "reaction_coordinate_graph": ReactionCoordinateSchema,
        "electrochemical_cell": ElectrochemicalCellSchema,
        "equilibrium_graph": EquilibriumGraphSchema,
        "titration_curve": TitrationCurveSchema,
        "sn1_sn2_mechanism": SN1SN2MechanismSchema,
        "newman_projection": NewmanProjectionSchema,
        "conformational_isomers": ConformationalIsomersSchema,
    },
    DiagramType.MATHEMATICS: {
        "function_graph": FunctionGraphSchema,
        "geometry_triangle": GeometryTriangleSchema,
        "geometry_circle": GeometryCircleSchema,
        "coordinate_geometry": CoordinateGeometrySchema,
        "calculus_graph": CalculusGraphSchema,
        "conic_section": ConicSectionSchema,
        "venn_diagram": VennDiagramSchema,
        "number_line": NumberLineSchema,
        "bar_chart": BarChartSchema,
        "scatter_plot": ScatterPlotSchema,
        "vector_3d": Vector3DSchema,
    },
    DiagramType.CIRCUITS: {
        "resistor_network": ResistorNetworkSchema,
        "capacitor_network": CapacitorNetworkSchema,
        "basic_dc_circuit": BasicDCCircuitSchema,
    },
    DiagramType.BIOLOGY: {
        "cell_diagram":       CellDiagramSchema,
        "dna_structure":      DNAStructureSchema,
        "cell_division":      CellDivisionSchema,
        "heart_diagram":      HeartDiagramSchema,
        "nephron_diagram":    NephronDiagramSchema,
        "neuron_diagram":     NeuronDiagramSchema,
        "food_web":           FoodWebSchema,
        "food_chain":         FoodChainSchema,
        "ecological_pyramid": EcologicalPyramidSchema,
    },
}

SUPPORTED_SUBTYPES: Dict[str, List[str]] = {
    k.value: list(v.keys()) for k, v in _SUBTYPE_SCHEMAS.items()
}


class ValidationResult:
    def __init__(self, valid: bool, errors: List[Dict], warnings: List[str] = None,
                 parsed: Optional[Any] = None):
        self.valid = valid
        self.errors = errors or []
        self.warnings = warnings or []
        self.parsed = parsed

    def to_dict(self) -> Dict:
        return {
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
        }


def validate_diagram(data: Dict[str, Any]) -> ValidationResult:
    """
    Two-phase validation:
      1. Parse the master DiagramSchema (diagram_type, subtype, canvas, annotations).
      2. Parse the type-specific sub-schema from `objects[0]` or the data dict itself.
    Returns a ValidationResult with structured error info.
    """
    errors: List[Dict] = []
    warnings: List[str] = []

    # ── Phase 1: master schema ────────────────────────────────────────────────
    try:
        master = DiagramSchema(**data)
    except ValidationError as exc:
        for e in exc.errors():
            errors.append({
                "field": ".".join(str(loc) for loc in e["loc"]),
                "message": e["msg"],
                "type": e["type"],
            })
        return ValidationResult(valid=False, errors=errors)

    dtype = master.diagram_type
    subtype = master.subtype

    # ── Phase 2: subtype registry check ──────────────────────────────────────
    type_map = _SUBTYPE_SCHEMAS.get(dtype, {})
    if not type_map:
        errors.append({"field": "diagram_type", "message": f"Unknown diagram_type '{dtype}'", "type": "value_error"})
        return ValidationResult(valid=False, errors=errors)

    schema_cls = type_map.get(subtype)
    if schema_cls is None:
        supported = list(type_map.keys())
        errors.append({
            "field": "subtype",
            "message": f"Unknown subtype '{subtype}' for type '{dtype}'. Supported: {supported}",
            "type": "value_error",
        })
        return ValidationResult(valid=False, errors=errors)

    # ── Phase 3: sub-schema validation ────────────────────────────────────────
    # Sub-schema data can be in objects[0] or inline at top level under "params"
    sub_data = data.get("params") or (data["objects"][0] if data.get("objects") else {})
    try:
        parsed_sub = schema_cls(**sub_data)
    except ValidationError as exc:
        for e in exc.errors():
            errors.append({
                "field": "objects[0]." + ".".join(str(loc) for loc in e["loc"]),
                "message": e["msg"],
                "type": e["type"],
            })
        return ValidationResult(valid=False, errors=errors)

    # ── Warnings ──────────────────────────────────────────────────────────────
    if not master.annotations:
        warnings.append("No annotations provided — diagram will have no text labels.")
    if master.canvas.width > 2048 or master.canvas.height > 2048:
        warnings.append("Large canvas size may slow rendering.")

    return ValidationResult(valid=True, errors=[], warnings=warnings, parsed=parsed_sub)


def list_supported_subtypes() -> Dict[str, List[str]]:
    return SUPPORTED_SUBTYPES
