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
    PNJunctionSchema, SemiconductorIVSchema, PhotoelectricEffectSchema,
    NuclearBindingEnergySchema, EMWaveSchema, TotalInternalReflectionSchema,
    MomentOfInertiaSchema, FluidMechanicsSchema, MotionGraphSchema,
    SHMSystemSchema, StandingWaveSchema, StressStrainSchema, HeatingCurveSchema,
    BlackbodySpectrumSchema, MaxwellBoltzmannSchema, GravitationSchema,
    RadioactiveDecaySchema, WavefrontSchema, PolarisationSchema,
    MeasuringInstrumentSchema, RollingMotionSchema,
    ConcaveLensSchema, ConvexMirrorSchema,
    OpticalInstrumentSchema, PrismDispersionSchema, EnergyLevelDiagramSchema,
    AlphaScatteringSchema, HeatEngineSchema, ThermalConductionSchema,
    GaussSurfaceSchema, EquipotentialSchema, CyclotronSchema,
    VelocitySelectorSchema, XraySpectrumSchema, BeatsSchema,
    DampedOscillationSchema, CollisionSchema, BankedRoadSchema,
    EMInductionSchema, NuclearReactorSchema, BandTheorySchema,
)
from diagrams.schemas.chemistry import (
    OrganicStructureSchema, InorganicStructureSchema,
    OrbitalDiagramSchema, ReactionCoordinateSchema,
    ElectrochemicalCellSchema, EquilibriumGraphSchema, TitrationCurveSchema,
    SN1SN2MechanismSchema, NewmanProjectionSchema, ConformationalIsomersSchema,
    CrystalLatticeSchema, VseprShapeSchema, MoDiagramSchema, PhaseDiagramSchema,
    HaworthFischerSchema, LabApparatusSchema,
    ReactionSchemeSchema, CrystalFieldSplittingSchema, KineticsGraphSchema,
    ColligativeGraphSchema, OrganicMechanismSchema, HybridisationOverlapSchema,
    AdsorptionIsothermSchema,
    ElectrolyticCellSchema, IonicLatticeSchema, SolidDefectsSchema,
    ComplexIsomerismSchema, PolymerStructureSchema, MetallurgyFlowchartSchema,
    IndustrialProcessSchema, ProteinStructureSchema, HydrogenBondingSchema,
    ResonanceStructuresSchema, FreeRadicalMechanismSchema,
)
from diagrams.schemas.mathematics import (
    FunctionGraphSchema, GeometryTriangleSchema, GeometryCircleSchema,
    CoordinateGeometrySchema, CalculusGraphSchema,
    ConicSectionSchema, VennDiagramSchema, NumberLineSchema,
    BarChartSchema, ScatterPlotSchema, Vector3DSchema,
    PieChartSchema, LineChartSchema, Solid3DSchema,
    ArgandDiagramSchema, LinearProgrammingSchema, HistogramSchema,
    ProbabilityTreeSchema, HeightDistanceSchema, CombinedSolidSchema,
    PlaneLine3DSchema, DistributionCurveSchema,
    PiecewiseGraphSchema, CircleTheoremSchema, SimilarTrianglesSchema,
    GeometricConstructionSchema, SolidOfRevolutionSchema,
    GraphTransformationSchema, BoxPlotSchema,
)
# One renderer, three domains. `annotated_xy_graph` is the generic "annotated curve with
# regions, asymptotes and marked points" figure — it subsumes the stress-strain curve, the
# heating curve, blackbody spectra, decay curves, kinetics and Arrhenius plots. Registering it
# under physics, chemistry AND mathematics means the model reaches for it with whichever
# diagram_type the question already implies, instead of being forced to misfile the question.
from diagrams.schemas.shared import AnnotatedXYGraphSchema
from diagrams.schemas.circuits import (
    ResistorNetworkSchema, CapacitorNetworkSchema, BasicDCCircuitSchema,
    LogicGatesSchema, ACPhasorSchema,
    WheatstoneBridgeSchema, RectifierSchema, RLCCircuitSchema, MeshCircuitSchema,
    TransistorAmplifierSchema, TransformerSchema, RCCircuitSchema,
    GalvanometerConversionSchema,
    EMMachineSchema, LogicCombinationalSchema, ZenerRegulatorSchema,
    TransistorSwitchSchema, CROSchema,
)
from diagrams.schemas.biology import (
    CellDiagramSchema, DNAStructureSchema, CellDivisionSchema,
    HeartDiagramSchema, NephronDiagramSchema, NeuronDiagramSchema,
    FoodWebSchema, FoodChainSchema, EcologicalPyramidSchema,
    PunnettSquareSchema, PedigreeChartSchema,
    FlowerStructureSchema, EyeDiagramSchema, DigestiveSystemSchema,
    RespiratorySystemSchema, PlantTissueSchema, OrganelleDetailSchema,
    MetabolicCycleSchema, GelElectrophoresisSchema, PlasmidMapSchema,
    BrainDiagramSchema, ReproductiveSystemSchema, GametogenesisSchema,
    EmbryoSacSchema, AntherTSSchema, SarcomereSchema, PopulationGrowthSchema,
    LacOperonSchema, MicrobeStructureSchema, EarDiagramSchema,
    EndocrineSystemSchema, KranzAnatomySchema, StomataSchema,
    ActionPotentialSchema, SynapseSchema, ReflexArcSchema,
    TranscriptionTranslationSchema, OxygenDissociationCurveSchema,
    CirculatorySystemSchema, MenstrualCycleSchema, EmbryoDevelopmentSchema,
    SeedStructureSchema, FloralDiagramSchema, PlantMorphologySchema,
    PlantLifeCycleSchema, PhotosynthesisZSchemeSchema,
    ElectronTransportChainSchema, ChromosomeStructureSchema,
    AnimalTissueSchema, AnimalAnatomySchema, ImmuneResponseSchema,
    EcologicalSuccessionSchema, BiotechWorkflowSchema,
    LabeledSchematicSchema,
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
        "pn_junction": PNJunctionSchema,
        "semiconductor_iv": SemiconductorIVSchema,
        "photoelectric_effect": PhotoelectricEffectSchema,
        "nuclear_binding_energy": NuclearBindingEnergySchema,
        "em_wave": EMWaveSchema,
        "total_internal_reflection": TotalInternalReflectionSchema,
        "moment_of_inertia": MomentOfInertiaSchema,
        "fluid_mechanics": FluidMechanicsSchema,
        "motion_graph": MotionGraphSchema,
        "shm_system": SHMSystemSchema,
        "standing_wave": StandingWaveSchema,
        "stress_strain": StressStrainSchema,
        "heating_curve": HeatingCurveSchema,
        "blackbody_spectrum": BlackbodySpectrumSchema,
        "maxwell_boltzmann": MaxwellBoltzmannSchema,
        "gravitation": GravitationSchema,
        "radioactive_decay": RadioactiveDecaySchema,
        "wavefront": WavefrontSchema,
        "polarisation": PolarisationSchema,
        "measuring_instrument": MeasuringInstrumentSchema,
        "rolling_motion": RollingMotionSchema,
        "optics_concave_lens": ConcaveLensSchema,
        "optics_convex_mirror": ConvexMirrorSchema,
        "optical_instrument": OpticalInstrumentSchema,
        "prism_dispersion": PrismDispersionSchema,
        "energy_level_diagram": EnergyLevelDiagramSchema,
        "alpha_scattering": AlphaScatteringSchema,
        "heat_engine": HeatEngineSchema,
        "thermal_conduction": ThermalConductionSchema,
        "gauss_surface": GaussSurfaceSchema,
        "equipotential": EquipotentialSchema,
        "cyclotron": CyclotronSchema,
        "velocity_selector": VelocitySelectorSchema,
        "xray_spectrum": XraySpectrumSchema,
        "beats": BeatsSchema,
        "damped_oscillation": DampedOscillationSchema,
        "collision": CollisionSchema,
        "banked_road": BankedRoadSchema,
        "em_induction": EMInductionSchema,
        "nuclear_reactor": NuclearReactorSchema,
        "band_theory": BandTheorySchema,
        "annotated_xy_graph": AnnotatedXYGraphSchema,
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
        "crystal_lattice": CrystalLatticeSchema,
        "vsepr_shape": VseprShapeSchema,
        "mo_diagram": MoDiagramSchema,
        "phase_diagram": PhaseDiagramSchema,
        "haworth_fischer": HaworthFischerSchema,
        "lab_apparatus": LabApparatusSchema,
        "reaction_scheme": ReactionSchemeSchema,
        "crystal_field_splitting": CrystalFieldSplittingSchema,
        "kinetics_graph": KineticsGraphSchema,
        "colligative_graph": ColligativeGraphSchema,
        "organic_mechanism": OrganicMechanismSchema,
        "hybridisation_overlap": HybridisationOverlapSchema,
        "adsorption_isotherm": AdsorptionIsothermSchema,
        "electrolytic_cell": ElectrolyticCellSchema,
        "ionic_lattice": IonicLatticeSchema,
        "solid_defects": SolidDefectsSchema,
        "complex_isomerism": ComplexIsomerismSchema,
        "polymer_structure": PolymerStructureSchema,
        "metallurgy_flowchart": MetallurgyFlowchartSchema,
        "industrial_process": IndustrialProcessSchema,
        "protein_structure": ProteinStructureSchema,
        "hydrogen_bonding": HydrogenBondingSchema,
        "resonance_structures": ResonanceStructuresSchema,
        "free_radical_mechanism": FreeRadicalMechanismSchema,
        "annotated_xy_graph": AnnotatedXYGraphSchema,
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
        "pie_chart": PieChartSchema,
        "line_chart": LineChartSchema,
        "solid_3d": Solid3DSchema,
        "argand_diagram": ArgandDiagramSchema,
        "linear_programming": LinearProgrammingSchema,
        "histogram": HistogramSchema,
        "probability_tree": ProbabilityTreeSchema,
        "height_distance": HeightDistanceSchema,
        "combined_solid": CombinedSolidSchema,
        "plane_line_3d": PlaneLine3DSchema,
        "distribution_curve": DistributionCurveSchema,
        "piecewise_graph": PiecewiseGraphSchema,
        "circle_theorem": CircleTheoremSchema,
        "similar_triangles": SimilarTrianglesSchema,
        "geometric_construction": GeometricConstructionSchema,
        "solid_of_revolution": SolidOfRevolutionSchema,
        "graph_transformation": GraphTransformationSchema,
        "box_plot": BoxPlotSchema,
        "annotated_xy_graph": AnnotatedXYGraphSchema,
    },
    DiagramType.CIRCUITS: {
        "resistor_network": ResistorNetworkSchema,
        "capacitor_network": CapacitorNetworkSchema,
        "basic_dc_circuit": BasicDCCircuitSchema,
        "logic_gates": LogicGatesSchema,
        "ac_phasor": ACPhasorSchema,
        "wheatstone_bridge": WheatstoneBridgeSchema,
        "rectifier": RectifierSchema,
        "rlc_circuit": RLCCircuitSchema,
        # basic_dc_circuit is an ORDERED LIST of components, i.e. a single loop — so every
        # Kirchhoff / multi-loop question was unmakeable until mesh_circuit.
        "mesh_circuit": MeshCircuitSchema,
        "transistor_amplifier": TransistorAmplifierSchema,
        "transformer": TransformerSchema,
        "rc_circuit": RCCircuitSchema,
        "galvanometer_conversion": GalvanometerConversionSchema,
        "em_machine": EMMachineSchema,
        "logic_combinational": LogicCombinationalSchema,
        "zener_regulator": ZenerRegulatorSchema,
        "transistor_switch": TransistorSwitchSchema,
        "cro": CROSchema,
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
        "punnett_square":     PunnettSquareSchema,
        "pedigree_chart":     PedigreeChartSchema,
        "flower_structure":   FlowerStructureSchema,
        "eye_diagram":        EyeDiagramSchema,
        "digestive_system":   DigestiveSystemSchema,
        "respiratory_system": RespiratorySystemSchema,
        "plant_tissue":       PlantTissueSchema,
        "organelle_detail":   OrganelleDetailSchema,
        "metabolic_cycle":    MetabolicCycleSchema,
        "gel_electrophoresis": GelElectrophoresisSchema,
        "plasmid_map":        PlasmidMapSchema,
        "brain_diagram":      BrainDiagramSchema,
        "reproductive_system": ReproductiveSystemSchema,
        "gametogenesis":      GametogenesisSchema,
        "embryo_sac":         EmbryoSacSchema,
        "anther_ts":          AntherTSSchema,
        "sarcomere":          SarcomereSchema,
        "population_growth":  PopulationGrowthSchema,
        "lac_operon":         LacOperonSchema,
        "microbe_structure":  MicrobeStructureSchema,
        "ear_diagram":        EarDiagramSchema,
        "endocrine_system":   EndocrineSystemSchema,
        "kranz_anatomy":      KranzAnatomySchema,
        "stomata":            StomataSchema,
        "action_potential":   ActionPotentialSchema,
        "synapse":            SynapseSchema,
        "reflex_arc":         ReflexArcSchema,
        "transcription_translation": TranscriptionTranslationSchema,
        "oxygen_dissociation_curve": OxygenDissociationCurveSchema,
        "circulatory_system": CirculatorySystemSchema,
        "menstrual_cycle":    MenstrualCycleSchema,
        "embryo_development": EmbryoDevelopmentSchema,
        "seed_structure":     SeedStructureSchema,
        "floral_diagram":     FloralDiagramSchema,
        "plant_morphology":   PlantMorphologySchema,
        "plant_life_cycle":   PlantLifeCycleSchema,
        "photosynthesis_zscheme": PhotosynthesisZSchemeSchema,
        "electron_transport_chain": ElectronTransportChainSchema,
        "chromosome_structure": ChromosomeStructureSchema,
        "animal_tissue":      AnimalTissueSchema,
        "animal_anatomy":     AnimalAnatomySchema,
        "immune_response":    ImmuneResponseSchema,
        "ecological_succession": EcologicalSuccessionSchema,
        "biotech_workflow":   BiotechWorkflowSchema,
        "labeled_schematic":  LabeledSchematicSchema,
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
