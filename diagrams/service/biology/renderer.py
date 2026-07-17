"""
Biology Diagram Renderer (NEET-focused).
All diagrams are drawn deterministically with matplotlib.
Covers 9 diagram types across cell biology, genetics, anatomy, and ecology.
"""
from __future__ import annotations

import io
import math
from collections import Counter
from functools import reduce
from typing import Any, Dict, List, Optional, Tuple

import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["svg.fonttype"] = "none"   # real <text> nodes, not paths
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
from matplotlib.patches import (
    Arc, FancyArrowPatch, FancyBboxPatch, Ellipse, Circle, Rectangle,
    PathPatch, Polygon, Wedge,
)
from matplotlib.path import Path
import numpy as np

from diagrams.schemas.biology import (
    CellDiagramSchema, DNAStructureSchema, CellDivisionSchema,
    HeartDiagramSchema, NephronDiagramSchema, NeuronDiagramSchema,
    FoodWebSchema, FoodChainSchema, EcologicalPyramidSchema,
    PunnettSquareSchema, PedigreeChartSchema,
    FlowerStructureSchema, EyeDiagramSchema, DigestiveSystemSchema,
    RespiratorySystemSchema, PlantTissueSchema, OrganelleDetailSchema,
    MetabolicCycleSchema, GelElectrophoresisSchema, PlasmidMapSchema,
    BrainDiagramSchema,
    ReproductiveSystemSchema, GametogenesisSchema, EmbryoSacSchema,
    AntherTSSchema, SarcomereSchema, PopulationGrowthSchema, LacOperonSchema,
    MicrobeStructureSchema, EarDiagramSchema, EndocrineSystemSchema,
    KranzAnatomySchema, StomataSchema,
    ActionPotentialSchema, SynapseSchema, ReflexArcSchema,
    TranscriptionTranslationSchema, OxygenDissociationCurveSchema,
    CirculatorySystemSchema, MenstrualCycleSchema, EmbryoDevelopmentSchema,
    SeedStructureSchema, FloralDiagramSchema, PlantMorphologySchema,
    PlantLifeCycleSchema, PhotosynthesisZSchemeSchema,
    ElectronTransportChainSchema, ChromosomeStructureSchema, AnimalTissueSchema,
    AnimalAnatomySchema, ImmuneResponseSchema, EcologicalSuccessionSchema,
    BiotechWorkflowSchema,
)

# ── Shared palette ────────────────────────────────────────────────────────────
C = {
    "cell_membrane":    "#e53935",
    "cell_wall":        "#388e3c",
    "nucleus":          "#5c35b5",
    "nucleolus":        "#7e57c2",
    "mitochondria":     "#ef6c00",
    "er_rough":         "#6d4c41",
    "er_smooth":        "#a1887f",
    "golgi":            "#f57f17",
    "lysosome":         "#d32f2f",
    "vacuole":          "#1565c0",
    "chloroplast":      "#2e7d32",
    "ribosome":         "#795548",
    "centriole":        "#455a64",
    "dna_strand1":      "#1565c0",
    "dna_strand2":      "#c62828",
    "at_pair":          "#ff8f00",
    "gc_pair":          "#2e7d32",
    "chromosome":       "#6a1b9a",
    "spindle":          "#0277bd",
    "heart_oxy":        "#c62828",
    "heart_deoxy":      "#1565c0",
    "nephron_tubule":   "#1565c0",
    "nephron_blood":    "#c62828",
    "neuron_soma":      "#f57c00",
    "neuron_axon":      "#1b5e20",
    "neuron_myelin":    "#fff9c4",
    "neuron_dendrite":  "#4a148c",
    "producer":         "#2e7d32",
    "primary":          "#f57c00",
    "secondary":        "#1565c0",
    "tertiary":         "#ad1457",
    "quaternary":       "#4a148c",
    "quinary":          "#37474f",
    "punnett_grid":     "#37474f",
    "punnett_header":   "#ede7f6",
    "punnett_corner":   "#cfd8dc",
    "punnett_cell":     "#fafafa",
    "pedigree_line":    "#37474f",
    "pedigree_fill":    "#37474f",   # affected → shaded symbol
    # Flower
    "sepal":            "#43a047",
    "petal":            "#ec407a",
    "petal_hibiscus":   "#d81b60",
    "anther":           "#fbc02d",
    "filament":         "#c0ca33",
    "stigma":           "#8e24aa",
    "style":            "#ab47bc",
    "ovary":            "#2e7d32",
    "ovule":            "#00897b",
    "receptacle":       "#558b2f",
    "pedicel":          "#33691e",
    # Eye
    "cornea":           "#0288d1",
    "aqueous":          "#e3f2fd",
    "iris":             "#00695c",
    "lens_body":        "#b3e5fc",
    "ciliary":          "#8d6e63",
    "vitreous":         "#e0f2f1",
    "retina":           "#ef5350",
    "choroid":          "#6d4c41",
    "sclera":           "#90a4ae",
    "fovea":            "#f9a825",
    "blind_spot":       "#616161",
    "optic_nerve":      "#fdd835",
    "light_ray":        "#f57f17",
    # Digestive
    "gut_tube":         "#e57373",
    "stomach":          "#ef5350",
    "liver":            "#8d6e63",
    "gall_bladder":     "#2e7d32",
    "pancreas":         "#fb8c00",
    "small_intestine":  "#ec407a",
    "large_intestine":  "#7e57c2",
    "appendix":         "#c62828",
    # Respiratory
    "airway":           "#5c6bc0",
    "lung":             "#ef9a9a",
    "lung_edge":        "#c62828",
    "diaphragm":        "#8d6e63",
    "pleura":           "#7986cb",
    "alveolus":         "#f8bbd0",
    "capillary_o2":     "#c62828",
    "capillary_co2":    "#1565c0",
    # Plant tissue
    "epidermis":        "#455a64",
    "cortex":           "#c5e1a5",
    "endodermis":       "#6d4c41",
    "pericycle":        "#8d6e63",
    "xylem":            "#c62828",
    "phloem":           "#1565c0",
    "cambium":          "#00897b",
    "pith":             "#fff59d",
    "ground_tissue":    "#dcedc8",
    "bundle_sheath":    "#33691e",
    "palisade":         "#43a047",
    "spongy":           "#a5d6a7",
    "stoma":            "#00695c",
    # Organelles
    "cristae":          "#e65100",
    "matrix":           "#ffe0b2",
    "thylakoid":        "#1b5e20",
    "granum":           "#2e7d32",
    "stroma":           "#c8e6c9",
    "lamella":          "#558b2f",
    "organelle_dna":    "#4527a0",
    "nuclear_pore":     "#d84315",
    "chromatin":        "#6a1b9a",
    # Metabolic cycles
    "cycle_node":       "#ede7f6",
    "cycle_node_edge":  "#5e35b1",
    "cycle_arrow":      "#455a64",
    "cycle_enzyme":     "#00695c",
    "cycle_chord":      "#ad1457",
    "cycle_hub":        "#fff59d",
    # Gel electrophoresis
    "gel_bg":           "#37474f",
    "gel_band":         "#eceff1",
    "gel_ladder":       "#ffd54f",
    "gel_well":         "#263238",
    "gel_cathode":      "#212121",
    "gel_anode":        "#c62828",
    # Plasmid
    "plasmid_backbone": "#37474f",
    "feat_ori":         "#1565c0",
    "feat_resistance":  "#c62828",
    "feat_promoter":    "#2e7d32",
    "feat_insert":      "#f57f17",
    "feat_gene":        "#6a1b9a",
    "restriction":      "#00695c",
    # Brain
    "cerebrum":         "#f8bbd0",
    "cerebellum":       "#b39ddb",
    "medulla":          "#80cbc4",
    "pons":             "#4db6ac",
    "midbrain":         "#26a69a",
    "thalamus":         "#ffcc80",
    "hypothalamus":     "#ffb74d",
    "corpus_callosum":  "#90a4ae",
    "pituitary":        "#ef5350",
    "olfactory":        "#aed581",
    "spinal_cord":      "#00897b",
    # Reproductive system
    "testis":           "#5e35b1",
    "epididymis":       "#8e24aa",
    "vas_deferens":     "#c2185b",
    "seminal_vesicle":  "#f9a825",
    "prostate":         "#00838f",
    "cowper":           "#6d4c41",
    "urethra":          "#fb8c00",
    "penis":            "#d84315",
    "scrotum":          "#a1887f",
    "bladder":          "#42a5f5",
    "ovary_f":          "#8e24aa",
    "fallopian":        "#c2185b",
    "myometrium":       "#ef9a9a",
    "endometrium":      "#ad1457",
    "perimetrium":      "#b0bec5",
    "cervix":           "#00838f",
    "vagina":           "#7e57c2",
    "fimbriae":         "#ec407a",
    # Gametogenesis
    "germ_cell":        "#455a64",
    "meiotic":          "#5e35b1",
    "sperm":            "#1565c0",
    "ovum":             "#ad1457",
    "polar_body":       "#8d6e63",
    "ploidy_2n":        "#c62828",
    "ploidy_n":         "#1565c0",
    # Embryo sac
    "embryo_sac":       "#e8f5e9",
    "antipodal":        "#7cb342",
    "central_cell":     "#e0f7fa",
    "egg_cell":         "#ec407a",
    "synergid":         "#26a69a",
    "filiform":         "#00695c",
    "polar_nucleus":    "#f57f17",
    "pollen_tube":      "#8e24aa",
    "male_gamete":      "#1565c0",
    "zygote":           "#c62828",
    "pen":              "#6a1b9a",
    # Anther T.S.
    "endothecium":      "#8d6e63",
    "middle_layer":     "#bcaaa4",
    "tapetum":          "#f57f17",
    "sporogenous":      "#7e57c2",
    "pollen_grain":     "#fbc02d",
    "connective":       "#aed581",
    "stomium":          "#c62828",
    # Sarcomere
    "actin":            "#1565c0",
    "myosin":           "#c62828",
    "z_line":           "#37474f",
    "m_line":           "#455a64",
    "band_a":           "#ffe0b2",
    "band_i":           "#e3f2fd",
    "zone_h":           "#fff9c4",
    "cross_bridge":     "#ad1457",
    # Population growth
    "curve_exp":        "#c62828",
    "curve_log":        "#1565c0",
    "carrying_cap":     "#2e7d32",
    "phase_lag":        "#eceff1",
    "phase_log":        "#e8f5e9",
    "phase_stat":       "#fff3e0",
    "half_k":           "#6a1b9a",
    # lac operon
    "dna_bar":          "#455a64",
    "gene_i":           "#5e35b1",
    "gene_p":           "#00897b",
    "gene_o":           "#c62828",
    "gene_z":           "#1565c0",
    "gene_y":           "#0288d1",
    "gene_a":           "#4dd0e1",
    "repressor":        "#6a1b9a",
    "inducer":          "#f57f17",
    "rna_pol":          "#2e7d32",
    "mrna":             "#e65100",
    "blocked":          "#b71c1c",
    # Microbes
    "capsid":           "#5e35b1",
    "phage_dna":        "#c62828",
    "collar":           "#00838f",
    "sheath":           "#f57f17",
    "tail_core":        "#8d6e63",
    "base_plate":       "#455a64",
    "tail_fibre":       "#37474f",
    "capsule":          "#b3e5fc",
    "cell_wall_b":      "#2e7d32",
    "nucleoid":         "#c62828",
    "bact_plasmid":     "#6a1b9a",
    "mesosome":         "#00838f",
    "flagellum":        "#5d4037",
    "pili":             "#8d6e63",
    "envelope":         "#ef9a9a",
    "spike":            "#1565c0",
    "matrix_prot":      "#ffb74d",
    "rna_strand":       "#6a1b9a",
    "enzyme_rt":        "#00695c",
    "capsomere":        "#7e57c2",
    # Ear
    "pinna":            "#f8bbd0",
    "ear_canal":        "#ffe0b2",
    "tympanum":         "#8d6e63",
    "ossicle":          "#5d4037",
    "eustachian":       "#00897b",
    "cochlea":          "#5e35b1",
    "semicircular":     "#1565c0",
    "vestibule":        "#7e57c2",
    "auditory_nerve":   "#fdd835",
    "organ_corti":      "#c2185b",
    "ear_external":     "#e8eaf6",
    "ear_middle":       "#fff3e0",
    "ear_internal":     "#e0f2f1",
    "scala":            "#e3f2fd",
    "basilar":          "#37474f",
    # Endocrine
    "body_outline":     "#90a4ae",
    "pineal":           "#7e57c2",
    "thyroid":          "#e53935",
    "parathyroid":      "#8e24aa",
    "thymus":           "#43a047",
    "adrenal":          "#fb8c00",
    "gonad":            "#00838f",
    "feedback_neg":     "#c62828",
    "axis_arrow":       "#1565c0",
    "table_head":       "#ede7f6",
    "table_row":        "#fafafa",
    # Kranz anatomy
    "mesophyll":        "#a5d6a7",
    "kranz_sheath":     "#2e7d32",
    "chloroplast_bs":   "#1b5e20",
    "c4_arrow":         "#e65100",
    "pep_enzyme":       "#ad1457",
    "rubisco":          "#1565c0",
    # Stomata
    "guard_cell":       "#66bb6a",
    "guard_wall":       "#1b5e20",
    "subsidiary":       "#c8e6c9",
    "epidermal":        "#eceff1",
    "pore":             "#ffffff",
    "guard_nucleus":    "#5e35b1",
    "k_ion":            "#e65100",
    "water_flow":       "#1565c0",
    # ── Wave 3 ────────────────────────────────────────────────────────────────
    # Action potential
    "ap_curve":         "#5e35b1",
    "ap_rest":          "#455a64",
    "ap_threshold":     "#e65100",
    "ap_depol":         "#c62828",
    "ap_repol":         "#1565c0",
    "ap_hyper":         "#00838f",
    "na_ion":           "#e65100",
    # Synapse
    "presynaptic":      "#f57c00",
    "postsynaptic":     "#5e35b1",
    "vesicle":          "#1e88e5",
    "neurotransmitter": "#c2185b",
    "receptor":         "#2e7d32",
    "ca_ion":           "#00695c",
    "synaptic_cleft":   "#eceff1",
    # Reflex arc
    "grey_matter":      "#bcaaa4",
    "white_matter":     "#eceff1",
    "afferent":         "#1565c0",
    "efferent":         "#c62828",
    "interneuron":      "#6a1b9a",
    "receptor_skin":    "#ffcc80",
    "effector":         "#ef9a9a",
    "dorsal_ganglion":  "#8e24aa",
    # Central dogma
    "dna_tmpl":         "#1565c0",
    "dna_coding":       "#7986cb",
    "rna_pol2":         "#2e7d32",
    "mrna_strand":      "#e65100",
    "ribosome_l":       "#8d6e63",
    "ribosome_s":       "#a1887f",
    "trna":             "#00838f",
    "codon":            "#5e35b1",
    "aminoacid":        "#c2185b",
    # Oxygen dissociation
    "odc_normal":       "#c62828",
    "odc_right":        "#e65100",
    "odc_left":         "#1565c0",
    "odc_myoglobin":    "#6a1b9a",
    "p50_mark":         "#37474f",
    # Circulatory
    "oxy_blood":        "#c62828",
    "deoxy_blood":      "#1565c0",
    "lungs_circ":       "#ef9a9a",
    "body_circ":        "#b0bec5",
    "heart_muscle":     "#ad1457",
    # Menstrual cycle
    "hormone_fsh":      "#1565c0",
    "hormone_lh":       "#e65100",
    "hormone_oestrogen":"#2e7d32",
    "hormone_progest":  "#8e24aa",
    "uterine_lining":   "#ec407a",
    "follicle":         "#f9a825",
    "corpus_luteum":    "#fb8c00",
    # Embryo development
    "blastomere":       "#7e57c2",
    "blastocoel":       "#e3f2fd",
    "trophoblast":      "#8d6e63",
    "icm":              "#c2185b",
    "ectoderm":         "#1565c0",
    "mesoderm":         "#c62828",
    "endoderm":         "#f9a825",
    "chorionic_villi":  "#ad1457",
    "umbilical":        "#00838f",
    # Seed
    "testa":            "#8d6e63",
    "cotyledon":        "#aed581",
    "plumule":          "#2e7d32",
    "radicle":          "#c62828",
    "endosperm":        "#fff59d",
    "scutellum":        "#f9a825",
    "coleoptile":       "#43a047",
    "coleorhiza":       "#8d6e63",
    "aleurone":         "#fb8c00",
    "micropyle":        "#455a64",
    # Floral diagram
    "calyx":            "#43a047",
    "corolla":          "#ec407a",
    "androecium":       "#fbc02d",
    "gynoecium":        "#8e24aa",
    "mother_axis":      "#37474f",
    "bract":            "#2e7d32",
    # Plant morphology
    "morph_leaf":       "#66bb6a",
    "morph_vein":       "#1b5e20",
    "morph_stem":       "#6d4c41",
    "morph_root":       "#8d6e63",
    "morph_flower":     "#ec407a",
    "morph_fruit":      "#ef6c00",
    # Plant life cycle
    "sporophyte":       "#2e7d32",
    "gametophyte":      "#43a047",
    "meiosis_mark":     "#c62828",
    "fert_mark":        "#1565c0",
    "spore":            "#f9a825",
    "gamete":           "#8e24aa",
    # Z-scheme
    "psii":             "#2e7d32",
    "psi":              "#1b5e20",
    "photon":           "#f9a825",
    "electron_path":    "#455a64",
    "nadph":            "#5e35b1",
    "water_split":      "#1565c0",
    # ETC
    "etc_membrane":     "#ffe0b2",
    "complex_i":        "#5e35b1",
    "complex_ii":       "#00897b",
    "complex_iii":      "#c62828",
    "complex_iv":       "#f57f17",
    "atp_synthase":     "#1565c0",
    "ubiquinone":       "#6a1b9a",
    "cyt_c":            "#ad1457",
    "proton":           "#e65100",
    "intermembrane":    "#e3f2fd",
    "matrix_m":         "#fff3e0",
    # Chromosome
    "chromatid":        "#5e35b1",
    "centromere":       "#c62828",
    "telomere":         "#f57f17",
    "kinetochore":      "#37474f",
    "karyo_band":       "#7e57c2",
    "chr_x":            "#c2185b",
    "chr_y":            "#1565c0",
    # Animal tissue
    "cell_fill":        "#ffe0b2",
    "cell_edge":        "#8d6e63",
    "tissue_nucleus":   "#5e35b1",
    "matrix_ct":        "#f3e5f5",
    "fibre_collagen":   "#ffb74d",
    "fibre_elastin":    "#66bb6a",
    "rbc":              "#c62828",
    "wbc":              "#7e57c2",
    "bone_matrix":      "#eceff1",
    "cartilage_m":      "#e1f5fe",
    "muscle_fibre":     "#ef9a9a",
    "nerve_cell":       "#f57c00",
    # Animal anatomy
    "anat_body":        "#f5f5f5",
    "anat_gut":         "#ef9a9a",
    "anat_organ":       "#ce93d8",
    "anat_vessel":      "#c62828",
    "anat_nerve":       "#fdd835",
    "anat_gonad":       "#8e24aa",
    # Immune response
    "heavy_chain":      "#1565c0",
    "light_chain":      "#e65100",
    "variable_region":  "#c2185b",
    "constant_region":  "#5e35b1",
    "antigen":          "#2e7d32",
    "titre_primary":    "#1565c0",
    "titre_secondary":  "#c62828",
    # Succession
    "pioneer":          "#8d6e63",
    "lichen":           "#9ccc65",
    "moss":             "#66bb6a",
    "herb":             "#43a047",
    "shrub":            "#2e7d32",
    "forest":           "#1b5e20",
    "pyramid_pre":      "#90caf9",
    "pyramid_repro":    "#66bb6a",
    "pyramid_post":     "#ffb74d",
    # Biotech
    "pcr_denature":     "#c62828",
    "pcr_anneal":       "#1565c0",
    "pcr_extend":       "#2e7d32",
    "vector":           "#5e35b1",
    "insert_dna":       "#f57f17",
    "restr_enzyme":     "#00695c",
    "ligase":           "#c2185b",
    "host_cell":        "#a5d6a7",
    "primer":           "#e65100",
}

# Soft cell fills used to shade Punnett cells by phenotype (dark text stays legible)
_PHENOTYPE_FILLS = [
    "#c8e6c9", "#ffe0b2", "#bbdefb", "#f8bbd0",
    "#e1bee7", "#b2dfdb", "#fff9c4", "#d7ccc8",
]

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    # Without a fixed salt matplotlib derives clip-path ids from object addresses,
    # so the same diagram would emit different SVG bytes on every render.
    "svg.hashsalt": "paperdeck",
})


def _fig_to_svg(fig) -> str:
    buf = io.BytesIO()
    # Date=None drops the <dc:date> stamp — the only other non-reproducible byte
    # in matplotlib's SVG output. Same params → byte-identical SVG.
    fig.savefig(buf, format="svg", bbox_inches="tight", facecolor="white", dpi=110,
                metadata={"Date": None})
    buf.seek(0)
    svg = buf.getvalue().decode("utf-8")
    plt.close(fig)
    return svg


def _annotate(ax, text, xy, xytext, color="black", fontsize=9, highlight=False):
    """Arrow annotation pointing from xytext label to xy target."""
    fc = "#fff176" if highlight else "white"
    ax.annotate(
        text, xy=xy, xytext=xytext,
        fontsize=fontsize, color=color,
        ha="center", va="center",
        bbox=dict(boxstyle="round,pad=0.25", fc=fc, ec=color, lw=0.8),
        arrowprops=dict(arrowstyle="-|>", color=color, lw=1.0,
                        connectionstyle="arc3,rad=0.1"),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Cell Organelle Diagram
# ═══════════════════════════════════════════════════════════════════════════════

def render_cell_diagram(data: Dict[str, Any],
                        canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = CellDiagramSchema(**data)

    # plant cells auto-enable wall + chloroplast
    is_plant = schema.cell_type.lower() == "plant"
    show_wall       = is_plant or schema.show_cell_wall
    show_chloro     = is_plant or schema.show_chloroplast
    show_lysosome   = schema.show_lysosome and not is_plant
    show_centriole  = schema.show_centriole and not is_plant
    hl = (schema.highlight_organelle or "").lower().replace(" ", "_")

    fig, ax = plt.subplots(figsize=(10, 8))
    ax.set_xlim(0, 10); ax.set_ylim(0, 8)
    ax.set_aspect("equal"); ax.axis("off")

    if is_plant:
        _draw_plant_cell(ax, schema, show_wall, show_chloro, hl)
    else:
        _draw_animal_cell(ax, schema, show_lysosome, show_centriole, hl)

    title = schema.title or f"{'Plant' if is_plant else 'Animal'} Cell"
    ax.set_title(title, fontsize=14, fontweight="bold", pad=6)
    fig.tight_layout(pad=0.4)
    return _fig_to_svg(fig)


def _draw_animal_cell(ax, schema, show_lysosome, show_centriole, hl):
    # ── Cell membrane ─────────────────────────────────────────────────────────
    cell = Ellipse((5, 4), 9.0, 7.2, fc="#fff8e1", ec=C["cell_membrane"], lw=2.5, zorder=1)
    ax.add_patch(cell)
    if schema.labeled:
        _annotate(ax, "Cell membrane", (1.0, 5.0), (0.4, 6.5),
                  C["cell_membrane"], highlight=(hl == "cell_membrane"))

    # ── Nucleus ───────────────────────────────────────────────────────────────
    if schema.show_nucleus:
        # Nuclear envelope (double membrane — two concentric ellipses)
        nuc_outer = Ellipse((4.2, 4.6), 2.4, 1.9, fc="#ede7f6",
                            ec=C["nucleus"], lw=2.0, zorder=3)
        nuc_inner = Ellipse((4.2, 4.6), 2.05, 1.6, fc="none",
                            ec=C["nucleus"], lw=0.8, ls="--", zorder=4)
        ax.add_patch(nuc_outer)
        ax.add_patch(nuc_inner)
        # Nucleolus
        nucl = Ellipse((4.0, 4.8), 0.65, 0.55, fc=C["nucleolus"],
                       ec="none", zorder=5)
        ax.add_patch(nucl)
        if schema.labeled:
            _annotate(ax, "Nucleus", (4.2, 4.6), (2.2, 6.2),
                      C["nucleus"], highlight=(hl == "nucleus"))
            _annotate(ax, "Nucleolus", (4.0, 4.8), (2.0, 5.0),
                      C["nucleolus"], highlight=(hl == "nucleolus"))

    # ── Mitochondria ──────────────────────────────────────────────────────────
    if schema.show_mitochondria:
        mito_positions = [(7.2, 5.8, 25), (7.8, 3.2, -15), (2.8, 2.4, 10)]
        for mx, my, ang in mito_positions:
            outer = Ellipse((mx, my), 1.1, 0.55, angle=ang,
                            fc="#ffe0b2", ec=C["mitochondria"], lw=1.5, zorder=3)
            inner = Ellipse((mx, my), 0.7, 0.3, angle=ang,
                            fc="none", ec=C["mitochondria"], lw=0.8,
                            ls="dotted", zorder=4)
            ax.add_patch(outer)
            ax.add_patch(inner)
        if schema.labeled:
            _annotate(ax, "Mitochondria", (7.2, 5.8), (8.5, 7.0),
                      C["mitochondria"], highlight=(hl in ("mitochondria", "mitochondrion")))

    # ── Rough ER ──────────────────────────────────────────────────────────────
    if schema.show_er:
        # Rough ER: wavy stack of lines near nucleus
        for i, dy in enumerate([-0.15, 0, 0.15]):
            xs = np.linspace(5.2, 7.4, 50)
            ys = 4.6 + dy + 0.12 * np.sin(6 * np.pi * (xs - 5.2) / 2.2)
            ax.plot(xs, ys, color=C["er_rough"], lw=1.5, zorder=3)
        # ribosome dots on rough ER
        if schema.show_ribosome:
            for xi in np.arange(5.3, 7.4, 0.35):
                ax.plot(xi, 4.75, "o", color=C["ribosome"],
                        markersize=3, zorder=5)
        # Smooth ER: smoother curves below
        for dy in [-0.1, 0.05]:
            xs = np.linspace(5.5, 7.0, 40)
            ys = 3.5 + dy + 0.09 * np.sin(4 * np.pi * (xs - 5.5) / 1.5)
            ax.plot(xs, ys, color=C["er_smooth"], lw=1.5, zorder=3)
        if schema.labeled:
            _annotate(ax, "Rough ER", (6.4, 4.75), (8.0, 5.5),
                      C["er_rough"], highlight=(hl in ("er", "rough_er", "endoplasmic_reticulum")))
            _annotate(ax, "Smooth ER", (6.2, 3.5), (8.0, 2.8),
                      C["er_smooth"], highlight=(hl == "smooth_er"))

    # ── Golgi apparatus ───────────────────────────────────────────────────────
    if schema.show_golgi:
        golgi_cx, golgi_cy = 6.7, 2.2
        for i, (rx, ry) in enumerate([(0.7, 0.18), (0.6, 0.16), (0.5, 0.14),
                                       (0.4, 0.12), (0.3, 0.10)]):
            arc = Arc((golgi_cx, golgi_cy + i * 0.22), rx * 2, ry * 2,
                      angle=0, theta1=200, theta2=340,
                      color=C["golgi"], lw=1.8, zorder=3)
            ax.add_patch(arc)
        # Vesicles budding off
        for vx, vy in [(7.5, 2.1), (7.3, 2.4)]:
            ax.add_patch(Circle((vx, vy), 0.12, fc=C["golgi"],
                                ec=C["golgi"], lw=1, zorder=4))
        if schema.labeled:
            _annotate(ax, "Golgi apparatus", (golgi_cx, golgi_cy + 0.4),
                      (8.8, 3.0), C["golgi"],
                      highlight=(hl in ("golgi", "golgi_apparatus")))

    # ── Lysosome ──────────────────────────────────────────────────────────────
    if show_lysosome:
        ax.add_patch(Circle((8.0, 1.6), 0.28, fc="#ffcdd2",
                             ec=C["lysosome"], lw=1.5, zorder=4))
        ax.text(8.0, 1.6, "L", ha="center", va="center",
                fontsize=7, color=C["lysosome"], fontweight="bold", zorder=5)
        if schema.labeled:
            _annotate(ax, "Lysosome", (8.0, 1.6), (9.2, 1.0),
                      C["lysosome"], highlight=(hl == "lysosome"))

    # ── Vacuole ───────────────────────────────────────────────────────────────
    if schema.show_vacuole:
        for vx, vy, vr in [(2.0, 5.8, 0.35), (2.8, 2.8, 0.25)]:
            ax.add_patch(Circle((vx, vy), vr, fc="#e3f2fd",
                                 ec=C["vacuole"], lw=1.2, zorder=3))
        if schema.labeled:
            _annotate(ax, "Vacuole", (2.0, 5.8), (0.8, 7.0),
                      C["vacuole"], highlight=(hl == "vacuole"))

    # ── Centriole ─────────────────────────────────────────────────────────────
    if show_centriole:
        cx_c, cy_c = 5.2, 5.7
        # Two perpendicular small rectangles
        ax.add_patch(FancyBboxPatch((cx_c - 0.28, cy_c - 0.1), 0.56, 0.2,
                                    boxstyle="round,pad=0.02",
                                    fc="#b0bec5", ec=C["centriole"], lw=1.2, zorder=4))
        ax.add_patch(FancyBboxPatch((cx_c - 0.1, cy_c - 0.28), 0.2, 0.56,
                                    boxstyle="round,pad=0.02",
                                    fc="#b0bec5", ec=C["centriole"], lw=1.2, zorder=4))
        if schema.labeled:
            _annotate(ax, "Centriole", (cx_c, cy_c), (5.8, 7.0),
                      C["centriole"], highlight=(hl == "centriole"))

    # ── Ribosome label ────────────────────────────────────────────────────────
    if schema.show_ribosome and schema.labeled:
        _annotate(ax, "Ribosomes", (5.65, 4.75), (5.5, 6.5),
                  C["ribosome"], highlight=(hl == "ribosome"))


def _draw_plant_cell(ax, schema, show_wall, show_chloro, hl):
    # ── Cell wall ─────────────────────────────────────────────────────────────
    if show_wall:
        wall = FancyBboxPatch((0.2, 0.3), 9.6, 7.4,
                               boxstyle="square,pad=0",
                               fc="#e8f5e9", ec=C["cell_wall"], lw=4, zorder=1)
        ax.add_patch(wall)
        if schema.labeled:
            _annotate(ax, "Cell wall", (0.2, 4.0), (0.8, 7.5),
                      C["cell_wall"], highlight=(hl == "cell_wall"))

    # ── Cell membrane ─────────────────────────────────────────────────────────
    membrane = FancyBboxPatch((0.55, 0.65), 8.9, 6.7,
                               boxstyle="square,pad=0",
                               fc="#f9fbe7", ec=C["cell_membrane"], lw=1.5, zorder=2)
    ax.add_patch(membrane)

    # ── Central vacuole ───────────────────────────────────────────────────────
    if schema.show_vacuole:
        vac = Ellipse((5.5, 3.8), 5.6, 4.4, fc="#e3f2fd",
                      ec=C["vacuole"], lw=2, zorder=3)
        ax.add_patch(vac)
        if schema.labeled:
            _annotate(ax, "Central\nVacuole", (5.5, 3.8), (5.5, 1.8),
                      C["vacuole"], fontsize=10, highlight=(hl == "vacuole"))

    # ── Nucleus ───────────────────────────────────────────────────────────────
    if schema.show_nucleus:
        nuc_o = Ellipse((2.4, 6.0), 2.2, 1.6, fc="#ede7f6",
                        ec=C["nucleus"], lw=2, zorder=4)
        nuc_i = Ellipse((2.4, 6.0), 1.9, 1.35, fc="none",
                        ec=C["nucleus"], lw=0.8, ls="--", zorder=5)
        ax.add_patch(nuc_o); ax.add_patch(nuc_i)
        ax.add_patch(Ellipse((2.3, 6.1), 0.6, 0.5, fc=C["nucleolus"],
                              ec="none", zorder=6))
        if schema.labeled:
            _annotate(ax, "Nucleus", (2.4, 6.0), (0.9, 7.4),
                      C["nucleus"], highlight=(hl == "nucleus"))

    # ── Chloroplasts ──────────────────────────────────────────────────────────
    if show_chloro:
        chloro_pos = [(1.5, 4.6, 15), (1.5, 3.0, -10),
                      (1.5, 1.5, 20), (8.5, 5.5, -20), (8.6, 1.8, 10)]
        for cx, cy, ang in chloro_pos:
            outer = Ellipse((cx, cy), 1.3, 0.65, angle=ang,
                            fc="#c8e6c9", ec=C["chloroplast"], lw=1.5, zorder=4)
            inner = Ellipse((cx, cy), 0.9, 0.38, angle=ang,
                            fc="#a5d6a7", ec=C["chloroplast"], lw=0.8, zorder=5)
            ax.add_patch(outer); ax.add_patch(inner)
        if schema.labeled:
            _annotate(ax, "Chloroplast", (1.5, 4.6), (0.6, 6.0),
                      C["chloroplast"], highlight=(hl == "chloroplast"))

    # ── Mitochondria ──────────────────────────────────────────────────────────
    if schema.show_mitochondria:
        for mx, my, ang in [(3.5, 1.2, 5), (4.2, 7.3, -10)]:
            ax.add_patch(Ellipse((mx, my), 1.0, 0.5, angle=ang,
                                  fc="#ffe0b2", ec=C["mitochondria"], lw=1.5, zorder=4))
        if schema.labeled:
            _annotate(ax, "Mitochondria", (3.5, 1.2), (5.0, 0.6),
                      C["mitochondria"], highlight=(hl in ("mitochondria", "mitochondrion")))

    # ── Golgi apparatus ───────────────────────────────────────────────────────
    if schema.show_golgi:
        gx, gy = 8.0, 3.5
        for i, rx in enumerate([0.65, 0.55, 0.45, 0.35]):
            ax.add_patch(Arc((gx, gy + i * 0.22), rx * 2, 0.28,
                              theta1=200, theta2=340,
                              color=C["golgi"], lw=1.8, zorder=4))
        if schema.labeled:
            _annotate(ax, "Golgi body", (gx, gy + 0.4), (9.5, 4.2),
                      C["golgi"], highlight=(hl in ("golgi", "golgi_apparatus")))

    # ── Cell wall label ───────────────────────────────────────────────────────
    if schema.labeled and show_wall:
        ax.text(0.38, 7.9, "Plasmodesmata", fontsize=7, color=C["cell_wall"],
                ha="left", va="center", style="italic")


# ═══════════════════════════════════════════════════════════════════════════════
# 2. DNA Structure
# ═══════════════════════════════════════════════════════════════════════════════

# Fixed sequence for deterministic base-pair labeling
_BASES_FIXED = "ATCGATCGATCGATCGATCG"
_COMPLEMENT  = {"A": "T", "T": "A", "G": "C", "C": "G"}
_PAIR_COLOR  = {"A": C["at_pair"], "T": C["at_pair"],
                "G": C["gc_pair"],  "C": C["gc_pair"]}


def render_dna_structure(data: Dict[str, Any],
                          canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = DNAStructureSchema(**data)

    if schema.structure_type.lower() == "replication_fork":
        return _draw_replication_fork(schema)
    return _draw_double_helix(schema)


def _draw_double_helix(schema: DNAStructureSchema) -> str:
    n = schema.num_base_pairs
    turns = max(1, n / 5)          # ~5 bp per turn
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.set_xlim(-0.5, n + 0.5)
    ax.set_ylim(-2.0, 2.5)
    ax.axis("off")

    t = np.linspace(0, n, 600)
    amp = 1.2
    freq = turns * 2 * np.pi / n

    y1 = amp * np.sin(freq * t)
    y2 = -amp * np.sin(freq * t)   # complementary strand

    # ── Rungs (base pairs) ────────────────────────────────────────────────────
    for i in range(n):
        xi = i + 0.5
        v1 = amp * math.sin(freq * xi)
        v2 = -v1
        base = _BASES_FIXED[i % len(_BASES_FIXED)]
        comp = _COMPLEMENT[base]
        clr  = _PAIR_COLOR[base]
        # rung
        ax.plot([xi, xi], [v2 + 0.08, v1 - 0.08], color=clr,
                lw=1.8, alpha=0.85, zorder=2)
        # base labels
        if schema.show_base_labels:
            ax.text(xi, v1 - 0.28, base, ha="center", va="center",
                    fontsize=7, color=clr, fontweight="bold", zorder=4)
            ax.text(xi, v2 + 0.28, comp, ha="center", va="center",
                    fontsize=7, color=clr, fontweight="bold", zorder=4)

    # ── Backbone strands ──────────────────────────────────────────────────────
    ax.plot(t, y1, color=C["dna_strand1"], lw=2.8, solid_capstyle="round",
            label="5′→3′ strand", zorder=3)
    ax.plot(t, y2, color=C["dna_strand2"], lw=2.8, solid_capstyle="round",
            label="3′→5′ strand", zorder=3)

    # ── Labels ────────────────────────────────────────────────────────────────
    if schema.show_labels:
        ax.text(-0.3, amp + 0.2, "5′", ha="right", fontsize=11,
                color=C["dna_strand1"], fontweight="bold")
        ax.text(n + 0.3, amp + 0.2, "3′", ha="left", fontsize=11,
                color=C["dna_strand1"], fontweight="bold")
        ax.text(-0.3, -amp - 0.2, "3′", ha="right", fontsize=11,
                color=C["dna_strand2"], fontweight="bold")
        ax.text(n + 0.3, -amp - 0.2, "5′", ha="left", fontsize=11,
                color=C["dna_strand2"], fontweight="bold")
        # Sugar-phosphate backbone labels
        mid = n / 2
        ax.annotate("Sugar-phosphate\nbackbone",
                    xy=(mid, amp), xytext=(mid, 1.85),
                    fontsize=8, ha="center", color=C["dna_strand1"],
                    arrowprops=dict(arrowstyle="-|>", lw=0.8,
                                   color=C["dna_strand1"]))
        # Hydrogen bonds label
        xi_h = int(n * 0.3) + 0.5
        v1_h = amp * math.sin(freq * xi_h)
        v2_h = -v1_h
        mid_h = (v1_h + v2_h) / 2
        ax.annotate("H-bonds",
                    xy=(xi_h, mid_h), xytext=(xi_h - 2.5, -1.6),
                    fontsize=8, ha="center", color="#555555",
                    arrowprops=dict(arrowstyle="-|>", lw=0.8, color="#555555"))

        # A-T / G-C key
        ax.text(n * 0.7, -1.7, "─── A-T pair", fontsize=8, color=C["at_pair"])
        ax.text(n * 0.7, -1.95, "─── G-C pair", fontsize=8, color=C["gc_pair"])

    title = schema.title or "DNA Double Helix"
    ax.set_title(title, fontsize=13, fontweight="bold", pad=4)
    ax.legend(loc="upper right", fontsize=8)
    fig.tight_layout(pad=0.5)
    return _fig_to_svg(fig)


def _draw_replication_fork(schema: DNAStructureSchema) -> str:
    fig, ax = plt.subplots(figsize=(10, 6.5))
    ax.set_xlim(-1, 11)
    ax.set_ylim(-3.5, 3.5)
    ax.axis("off")
    ax.set_title(schema.title or "DNA Replication Fork",
                 fontsize=13, fontweight="bold", pad=4)

    n = schema.num_base_pairs

    # ── Left: intact double-stranded DNA (template) ───────────────────────────
    t_left = np.linspace(0, 4, 200)
    amp, freq = 0.9, 2 * np.pi / 4
    y1_l = amp * np.sin(freq * t_left)
    y2_l = -amp * np.sin(freq * t_left)
    ax.plot(t_left, y1_l, color=C["dna_strand1"], lw=2.5, zorder=3)
    ax.plot(t_left, y2_l, color=C["dna_strand2"], lw=2.5, zorder=3)
    # rungs on intact region
    for xi in np.arange(0.5, 4, 0.5):
        v1 = amp * math.sin(freq * xi)
        ax.plot([xi, xi], [-v1 + 0.07, v1 - 0.07],
                color=C["at_pair"], lw=1.5, alpha=0.7, zorder=2)

    # ── Helicase at fork (x=4) ────────────────────────────────────────────────
    helicase = Circle((4.0, 0), 0.45, fc="#80cbc4", ec="#00796b", lw=1.8, zorder=5)
    ax.add_patch(helicase)
    ax.text(4.0, 0, "He", ha="center", va="center", fontsize=8,
            color="#004d40", fontweight="bold", zorder=6)
    if schema.show_labels:
        ax.annotate("Helicase", xy=(4.0, 0), xytext=(3.2, 1.8),
                    fontsize=8, color="#00796b",
                    arrowprops=dict(arrowstyle="-|>", color="#00796b", lw=0.9))

    # ── Leading strand (top arm of fork, rightward) ───────────────────────────
    t_lead = np.linspace(4.4, 10, 200)
    y_lead_template = amp * np.sin(freq * t_lead)
    y_lead_new = y_lead_template + 0.25   # new strand slightly above
    ax.plot(t_lead, y_lead_template, color=C["dna_strand1"],
            lw=2.5, zorder=3)
    ax.plot(t_lead, y_lead_new, color="#43a047",
            lw=2.0, ls="-", zorder=3)
    # Continuous synthesis arrow
    ax.annotate("", xy=(10, y_lead_new[-1]), xytext=(5.5, y_lead_new[50]),
                arrowprops=dict(arrowstyle="-|>", color="#43a047", lw=1.5))
    if schema.show_labels:
        ax.text(10.2, y_lead_new[-1], "Leading\nstrand\n(continuous)",
                fontsize=7.5, color="#43a047", va="center")
    # DNA Pol on leading strand
    ax.add_patch(Circle((8, y_lead_new[100]), 0.35, fc="#ffe082",
                         ec="#f57c00", lw=1.5, zorder=5))
    ax.text(8, y_lead_new[100], "Pol", ha="center", va="center",
            fontsize=7, color="#bf360c", fontweight="bold", zorder=6)

    # ── Lagging strand (bottom arm, synthesised in fragments) ─────────────────
    y_lag_template = -amp * np.sin(freq * t_lead)
    y_lag_new = y_lag_template - 0.25
    ax.plot(t_lead, y_lag_template, color=C["dna_strand2"],
            lw=2.5, zorder=3)
    # Okazaki fragments (3 segments, rightward)
    frag_starts = [4.6, 6.3, 8.0]
    for i, fs in enumerate(frag_starts):
        fe = min(fs + 1.5, 10)
        t_frag = np.linspace(fs, fe, 60)
        y_frag = -amp * np.sin(freq * t_frag) - 0.25
        ax.plot(t_frag, y_frag, color="#e57373", lw=2.0, zorder=3)
        # small arrow showing synthesis direction (right→left on lagging)
        mid_t = (fs + fe) / 2
        mid_y = float(np.interp(mid_t, t_frag, y_frag))
        ax.annotate("", xy=(fs + 0.2, mid_y), xytext=(fe - 0.2, mid_y),
                    arrowprops=dict(arrowstyle="-|>", color="#e57373", lw=1.2))
        if i == 1 and schema.show_labels:
            ax.text(mid_t, mid_y - 0.45, "Okazaki\nfragment",
                    ha="center", fontsize=7.5, color="#e57373")

    if schema.show_labels:
        ax.text(10.2, y_lag_new[-1] + 0.1, "Lagging\nstrand\n(fragments)",
                fontsize=7.5, color="#e57373", va="center")
        # Primase label
        ax.annotate("Primase/\nPrimer", xy=(4.7, y_lag_template[10]),
                    xytext=(3.5, -2.8), fontsize=7.5, color="#7b1fa2",
                    arrowprops=dict(arrowstyle="-|>", color="#7b1fa2", lw=0.9))

    # ── 5' / 3' labels ────────────────────────────────────────────────────────
    if schema.show_labels:
        ax.text(-0.8, amp + 0.1, "5′", fontsize=10, color=C["dna_strand1"],
                fontweight="bold")
        ax.text(-0.8, -amp - 0.1, "3′", fontsize=10, color=C["dna_strand2"],
                fontweight="bold")

    fig.tight_layout(pad=0.5)
    return _fig_to_svg(fig)


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Cell Division
# ═══════════════════════════════════════════════════════════════════════════════

def render_cell_division(data: Dict[str, Any],
                          canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = CellDivisionSchema(**data)
    stage  = schema.stage
    is_meiosis = schema.division_type.lower() == "meiosis"

    fig, ax = plt.subplots(figsize=(7, 7))
    ax.set_xlim(-5, 5); ax.set_ylim(-5, 5)
    ax.set_aspect("equal"); ax.axis("off")

    n_pairs = schema.num_chromosome_pairs

    if is_meiosis:
        _draw_meiosis_stage(ax, stage, n_pairs, schema.show_spindle, schema.show_labels)
    else:
        _draw_mitosis_stage(ax, stage, n_pairs, schema.show_spindle, schema.show_labels)

    div_name = "Meiosis" if is_meiosis else "Mitosis"
    stage_name = stage.replace("_", " ").title()
    title = schema.title or f"{div_name} — {stage_name}"
    ax.set_title(title, fontsize=14, fontweight="bold", pad=6)
    fig.tight_layout(pad=0.3)
    return _fig_to_svg(fig)


def _chromosome(ax, cx, cy, size=0.4, angle=0.0, color=C["chromosome"],
                condensed=True):
    """Draw a chromosome as an X-shape (two sister chromatids)."""
    r = math.radians(angle)
    cos_r, sin_r = math.cos(r), math.sin(r)
    # Two arms
    for sign in [1, -1]:
        for arm in [1, -1]:
            dx = size * (arm * cos_r - sign * 0.25 * sin_r)
            dy = size * (arm * sin_r + sign * 0.25 * cos_r)
            ax.plot([cx, cx + dx], [cy, cy + dy],
                    color=color, lw=3.5 if condensed else 1.5,
                    solid_capstyle="round", zorder=4)
    # Centromere dot
    ax.plot(cx, cy, "o", color=color, markersize=6, zorder=5)


def _draw_mitosis_stage(ax, stage, n_pairs, show_spindle, show_labels):
    # Cell outline
    cell_w, cell_h = 4.2, 4.2
    angle_stage = {"anaphase": (3.0, 4.8), "telophase": (2.8, 5.0),
                   "cytokinesis": (2.5, 5.2)}.get(stage, (cell_w, cell_h))

    cell = Ellipse((0, 0), angle_stage[0] * 2, angle_stage[1] * 2,
                   fc="#fffde7", ec=C["cell_membrane"], lw=2.5, zorder=1)
    ax.add_patch(cell)

    if stage in ("prophase",):
        # Nuclear envelope (dissolving)
        nuc = Ellipse((0, 0), 2.6, 2.0, fc="#ede7f6",
                      ec=C["nucleus"], lw=1.5, ls="--", zorder=2)
        ax.add_patch(nuc)
        if show_labels:
            ax.text(0, -1.3, "Nuclear envelope\n(dissolving)", ha="center",
                    fontsize=8, color=C["nucleus"], style="italic")
        # Chromosomes: condensing, scattered
        positions = [(-1.0, 0.5, 30), (0.0, 0.8, -20), (1.0, 0.3, 60),
                     (-0.5, -0.5, 10), (0.5, -0.7, -40)][:n_pairs * 2]
        for cx, cy, ang in positions:
            _chromosome(ax, cx, cy, size=0.38, angle=ang)
        if show_labels:
            ax.text(0, 3.5, "Condensing chromosomes", ha="center",
                    fontsize=9, color=C["chromosome"])

    elif stage == "metaphase":
        # Chromosomes at equatorial plate
        if show_spindle:
            for sign in [-1, 1]:
                for xi in np.linspace(-2.5, 2.5, n_pairs * 2 + 1):
                    ax.plot([xi * 0.3, sign * 3.8],
                            [0, sign * 3.8 * 0.05], color=C["spindle"],
                            lw=0.8, alpha=0.6, zorder=2)
            ax.plot([-4, 4], [0, 0], color=C["spindle"],
                    lw=0.5, ls="--", alpha=0.4)
            if show_labels:
                ax.text(-4.5, 0, "Spindle", ha="right", fontsize=8,
                        color=C["spindle"])
                ax.text(0, -0.5, "Metaphase plate", ha="center", fontsize=8,
                        color="#555555", style="italic")

        xs = np.linspace(-1.5 * (n_pairs - 1) / 2, 1.5 * (n_pairs - 1) / 2,
                         n_pairs)
        for i, xi in enumerate(xs):
            _chromosome(ax, xi, 0, size=0.42, angle=90)

    elif stage == "anaphase":
        # Chromosomes moving to poles
        for sign in [-1, 1]:
            xs = np.linspace(-1.2 * (n_pairs - 1) / 2,
                              1.2 * (n_pairs - 1) / 2, n_pairs)
            for xi in xs:
                _chromosome(ax, xi * 0.6, sign * 2.0,
                             size=0.35, angle=90 + sign * 15)
        if show_spindle:
            for sign in [-1, 1]:
                ax.annotate("", xy=(0, sign * 3.8), xytext=(0, 0),
                            arrowprops=dict(arrowstyle="-|>",
                                           color=C["spindle"], lw=1.0))
        if show_labels:
            for sign, lbl in [(-1, "To poles →"), (1, "← To poles")]:
                ax.text(0, sign * 3.0, lbl, ha="center", fontsize=8,
                        color="#555555")

    elif stage == "telophase":
        # Two nuclear envelopes re-forming
        for sign in [-1, 1]:
            nuc_t = Ellipse((0, sign * 2.0), 2.4, 1.4,
                             fc="#ede7f6", ec=C["nucleus"],
                             lw=1.5, ls="--", zorder=2)
            ax.add_patch(nuc_t)
            xs = np.linspace(-0.8, 0.8, n_pairs)
            for xi in xs:
                _chromosome(ax, xi, sign * 2.0, size=0.28, angle=0,
                             condensed=False)
        if show_labels:
            ax.text(0, 0, "Cleavage\nfurrow", ha="center",
                    fontsize=9, color=C["cell_membrane"])
            ax.plot([-3.0, 3.0], [0, 0],
                    color=C["cell_membrane"], lw=2, ls="--", zorder=3)

    elif stage == "cytokinesis":
        # Two daughter cells
        for sign in [-1, 1]:
            daughter = Ellipse((0, sign * 2.4), 3.8, 2.6,
                                fc="#fffde7", ec=C["cell_membrane"],
                                lw=2.5, zorder=2)
            ax.add_patch(daughter)
            nuc_d = Ellipse((0, sign * 2.4), 1.2, 0.9,
                             fc="#ede7f6", ec=C["nucleus"], lw=1.5, zorder=3)
            ax.add_patch(nuc_d)
        # Remove original outer cell patch visibility
        cell.set_visible(False)
        if show_labels:
            for sign, lbl in [(-1, "Daughter cell 1"), (1, "Daughter cell 2")]:
                ax.text(0, sign * 3.8, lbl, ha="center",
                        fontsize=9, color=C["cell_membrane"])

    else:
        # Generic fallback — show label
        ax.text(0, 0, f"Stage: {stage}", ha="center", va="center",
                fontsize=12, color="#555555")


def _draw_meiosis_stage(ax, stage, n_pairs, show_spindle, show_labels):
    """Draw a meiosis stage — key NEET-relevant stages."""
    cell = Ellipse((0, 0), 8.5, 8.5, fc="#f3e5f5",
                   ec=C["nucleus"], lw=2.5, zorder=1)
    ax.add_patch(cell)

    if stage in ("prophase_1", "prophase1"):
        # Homologous chromosomes pairing (synapsis)
        for i in range(n_pairs):
            angle = (i / n_pairs) * 2 * math.pi
            cx = 2.0 * math.cos(angle)
            cy = 2.0 * math.sin(angle)
            # Pair of homologs side by side with chiasma
            for sign, clr in [(-0.25, C["chromosome"]),
                               (0.25, "#e57373")]:
                ax.plot([cx + sign, cx + sign],
                        [cy - 0.5, cy + 0.5],
                        color=clr, lw=4, solid_capstyle="round", zorder=4)
            # Chiasma (X)
            ax.plot(cx, cy, "x", color="#ad1457",
                    markersize=8, markeredgewidth=2, zorder=5)
        if show_labels:
            ax.text(0, -4.5, "Synapsis / Bivalents / Chiasma",
                    ha="center", fontsize=9, color=C["chromosome"])
            ax.text(0, -4.0, "(Crossing over occurs)", ha="center",
                    fontsize=8, color="#ad1457", style="italic")

    elif stage in ("metaphase_1", "metaphase1"):
        # Bivalents at equator
        if show_spindle:
            ax.plot([-4, 4], [0, 0], color=C["spindle"],
                    lw=0.8, ls="--", alpha=0.5)
        for i in range(n_pairs):
            xi = (i - (n_pairs - 1) / 2.0) * 1.4
            for sign, clr in [(-0.25, C["chromosome"]),
                               (0.25, "#e57373")]:
                ax.plot([xi + sign, xi + sign],
                        [-0.5, 0.5], color=clr,
                        lw=4, solid_capstyle="round", zorder=4)
        if show_labels:
            ax.text(0, -1.0, "Bivalents at equatorial plate",
                    ha="center", fontsize=9, color="#555555", style="italic")

    elif stage in ("anaphase_1", "anaphase1"):
        # Homologs moving to opposite poles
        for i in range(n_pairs):
            xi = (i - (n_pairs - 1) / 2.0) * 1.4
            for sign_y, clr in [(-2.5, C["chromosome"]),
                                  (2.5, "#e57373")]:
                ax.plot([xi, xi], [sign_y - 0.4, sign_y + 0.4],
                        color=clr, lw=4, solid_capstyle="round", zorder=4)
        if show_labels:
            ax.text(0, 0, "Homologs separate\n(sister chromatids together)",
                    ha="center", fontsize=9, color="#555555")

    elif stage in ("metaphase_2", "metaphase2"):
        # Individual chromosomes at equator (no bivalents)
        if show_spindle:
            ax.plot([-4, 4], [0, 0], color=C["spindle"],
                    lw=0.8, ls="--", alpha=0.5)
        for i in range(n_pairs * 2):
            xi = (i - n_pairs + 0.5) * 0.9
            _chromosome(ax, xi, 0, size=0.38, angle=90)
        if show_labels:
            ax.text(0, -1.5, "Sister chromatids at equator",
                    ha="center", fontsize=9, color="#555555", style="italic")

    elif stage in ("anaphase_2", "anaphase2"):
        # Sister chromatids separating
        for i in range(n_pairs * 2):
            xi = (i - n_pairs + 0.5) * 0.8
            for sign_y in [-2.0, 2.0]:
                ax.plot([xi, xi], [sign_y - 0.3, sign_y + 0.3],
                        color=C["chromosome"], lw=3.5,
                        solid_capstyle="round", zorder=4)
        if show_labels:
            ax.text(0, 0, "Sister chromatids separate",
                    ha="center", fontsize=9, color="#555555")

    else:
        ax.text(0, 0, f"Meiosis\n{stage.replace('_', ' ').title()}",
                ha="center", va="center", fontsize=13, color=C["nucleus"])


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Heart Diagram
# ═══════════════════════════════════════════════════════════════════════════════

def render_heart_diagram(data: Dict[str, Any],
                          canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = HeartDiagramSchema(**data)

    fig, ax = plt.subplots(figsize=(9, 8))
    ax.set_xlim(0, 10); ax.set_ylim(0, 10)
    ax.set_aspect("equal"); ax.axis("off")

    # ── Outer heart shape (pericardium) ───────────────────────────────────────
    heart_bg = Ellipse((5, 4.5), 8.5, 7.5, fc="#fce4ec",
                        ec="#e91e63", lw=3, zorder=1, alpha=0.35)
    ax.add_patch(heart_bg)

    # ── Four chambers ─────────────────────────────────────────────────────────
    # Anatomical note: viewer's LEFT = patient's RIGHT
    # Right side of diagram = patient's left (systemic circuit = oxygenated)
    # Left side of diagram  = patient's right (pulmonary circuit = deoxygenated)

    # Right Atrium (viewer's left side, deoxygenated blood from body)
    RA = FancyBboxPatch((1.0, 5.5), 2.8, 2.2, boxstyle="round,pad=0.3",
                         fc="#bbdefb", ec=C["heart_deoxy"], lw=2, zorder=3)
    ax.add_patch(RA)
    ax.text(2.4, 6.6, "Right\nAtrium", ha="center", va="center",
            fontsize=10, fontweight="bold", color=C["heart_deoxy"])

    # Left Atrium (viewer's right, oxygenated blood from lungs)
    LA = FancyBboxPatch((6.2, 5.5), 2.8, 2.2, boxstyle="round,pad=0.3",
                         fc="#ffcdd2", ec=C["heart_oxy"], lw=2, zorder=3)
    ax.add_patch(LA)
    ax.text(7.6, 6.6, "Left\nAtrium", ha="center", va="center",
            fontsize=10, fontweight="bold", color=C["heart_oxy"])

    # Interatrial septum
    ax.plot([3.8, 6.2], [5.5, 5.5], color="#555555", lw=2, zorder=4)
    ax.plot([3.8, 6.2], [7.7, 7.7], color="#555555", lw=2, zorder=4)
    ax.plot([3.8, 3.8], [5.5, 7.7], color="#555555", lw=1.5, zorder=4)
    ax.plot([6.2, 6.2], [5.5, 7.7], color="#555555", lw=1.5, zorder=4)

    # Right Ventricle
    RV_pts = np.array([[1.0, 5.5], [1.0, 2.0], [4.5, 1.0],
                        [3.8, 5.5], [1.0, 5.5]])
    ax.fill(RV_pts[:, 0], RV_pts[:, 1], fc="#bbdefb",
            ec=C["heart_deoxy"], lw=2, zorder=3)
    ax.text(2.2, 3.5, "Right\nVentricle", ha="center", va="center",
            fontsize=10, fontweight="bold", color=C["heart_deoxy"])

    # Left Ventricle (larger, thicker wall)
    LV_pts = np.array([[6.2, 5.5], [5.5, 1.0], [9.0, 2.0],
                        [9.0, 5.5], [6.2, 5.5]])
    ax.fill(LV_pts[:, 0], LV_pts[:, 1], fc="#ffcdd2",
            ec=C["heart_oxy"], lw=2.5, zorder=3)
    ax.text(7.5, 3.5, "Left\nVentricle", ha="center", va="center",
            fontsize=10, fontweight="bold", color=C["heart_oxy"])

    # Interventricular septum
    ax.plot([3.8, 5.5], [5.5, 1.0], color="#555555", lw=2.5, zorder=4)

    # ── Valves ────────────────────────────────────────────────────────────────
    if schema.show_valves:
        # Tricuspid (RA→RV) — between right chambers
        ax.text(2.4, 5.4, "Tricuspid", ha="center", va="top",
                fontsize=7.5, color=C["heart_deoxy"],
                bbox=dict(fc="#bbdefb", ec=C["heart_deoxy"], lw=0.8, pad=1.5))
        # Bicuspid/Mitral (LA→LV)
        ax.text(7.6, 5.4, "Bicuspid\n(Mitral)", ha="center", va="top",
                fontsize=7.5, color=C["heart_oxy"],
                bbox=dict(fc="#ffcdd2", ec=C["heart_oxy"], lw=0.8, pad=1.5))
        # Pulmonary semilunar (RV→PA)
        ax.text(2.0, 8.0, "Pulmonary\nvalve", ha="center",
                fontsize=7.0, color=C["heart_deoxy"])
        # Aortic semilunar (LV→Aorta)
        ax.text(8.0, 8.0, "Aortic\nvalve", ha="center",
                fontsize=7.0, color=C["heart_oxy"])

    # ── Major vessels ─────────────────────────────────────────────────────────
    # Superior Vena Cava (→ RA, from top)
    ax.annotate("", xy=(2.0, 7.7), xytext=(2.0, 9.5),
                arrowprops=dict(arrowstyle="-|>", color=C["heart_deoxy"], lw=2.5))
    ax.text(1.0, 9.6, "Superior\nVena Cava", ha="center", fontsize=8.5,
            color=C["heart_deoxy"], fontweight="bold")

    # Inferior Vena Cava (→ RA, from bottom)
    ax.annotate("", xy=(1.8, 5.5), xytext=(1.0, 3.8),
                arrowprops=dict(arrowstyle="-|>", color=C["heart_deoxy"], lw=2.0))
    ax.text(0.2, 3.5, "Inferior\nVena Cava", ha="center", fontsize=8,
            color=C["heart_deoxy"], fontweight="bold")

    # Pulmonary Artery (← RV, to lungs)
    ax.annotate("", xy=(2.8, 9.5), xytext=(2.8, 7.7),
                arrowprops=dict(arrowstyle="-|>", color=C["heart_deoxy"], lw=2.5))
    ax.text(3.2, 9.8, "Pulmonary\nArtery\n(to lungs)", ha="center", fontsize=8.5,
            color=C["heart_deoxy"], fontweight="bold")

    # Pulmonary Veins (→ LA, from lungs)
    ax.annotate("", xy=(7.0, 7.7), xytext=(7.0, 9.5),
                arrowprops=dict(arrowstyle="-|>", color=C["heart_oxy"], lw=2.5))
    ax.text(6.5, 9.8, "Pulmonary\nVeins\n(from lungs)", ha="center", fontsize=8.5,
            color=C["heart_oxy"], fontweight="bold")

    # Aorta (← LV, to body)
    ax.annotate("", xy=(8.5, 9.5), xytext=(8.5, 7.7),
                arrowprops=dict(arrowstyle="-|>", color=C["heart_oxy"], lw=2.5))
    ax.text(9.5, 9.8, "Aorta\n(to body)", ha="center", fontsize=8.5,
            color=C["heart_oxy"], fontweight="bold")

    # ── Blood flow annotations ────────────────────────────────────────────────
    if schema.show_blood_flow:
        ax.text(0.1, 1.5, "Deoxygenated\nblood (blue)",
                fontsize=8, color=C["heart_deoxy"],
                bbox=dict(fc="#e3f2fd", ec=C["heart_deoxy"], lw=1, pad=2))
        ax.text(6.5, 0.3, "Oxygenated\nblood (red)",
                fontsize=8, color=C["heart_oxy"],
                bbox=dict(fc="#ffebee", ec=C["heart_oxy"], lw=1, pad=2))

    ax.set_title(schema.title or "Human Heart (Schematic)",
                 fontsize=14, fontweight="bold", pad=6)
    fig.tight_layout(pad=0.4)
    return _fig_to_svg(fig)


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Nephron Diagram
# ═══════════════════════════════════════════════════════════════════════════════

def render_nephron_diagram(data: Dict[str, Any],
                            canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = NephronDiagramSchema(**data)
    hl = (schema.highlight_region or "").lower().replace(" ", "_")

    fig, ax = plt.subplots(figsize=(9, 9))
    ax.set_xlim(0, 10); ax.set_ylim(0, 11)
    ax.set_aspect("equal"); ax.axis("off")

    def _tubule_color(region):
        if hl and hl in region:
            return "#ffeb3b"     # highlighted yellow
        return "#e3f2fd"        # default light blue

    lw_t = 2.5   # tubule line width

    # ── Bowman's capsule + Glomerulus ─────────────────────────────────────────
    # Outer capsule
    cap_outer = Circle((5, 9.5), 0.85, fc=_tubule_color("bowman"),
                        ec=C["nephron_tubule"], lw=lw_t, zorder=3)
    ax.add_patch(cap_outer)
    # Glomerular tuft (tangled capillaries — drawn as small coiled circle)
    cap_inner = Circle((5, 9.5), 0.55, fc="#ffcdd2",
                        ec=C["nephron_blood"], lw=1.5, zorder=4)
    ax.add_patch(cap_inner)
    ax.text(5, 9.5, "Glomerulus", ha="center", va="center",
            fontsize=7, fontweight="bold", color=C["nephron_blood"], zorder=5)
    if schema.show_labels:
        _annotate(ax, "Bowman's\nCapsule", (5, 9.5), (2.8, 9.5),
                  C["nephron_tubule"], fontsize=8.5,
                  highlight=bool(hl and "bowman" in hl))

    # Afferent arteriole (→ glomerulus)
    if schema.show_blood_vessels:
        ax.annotate("", xy=(4.55, 9.8), xytext=(3.2, 10.5),
                    arrowprops=dict(arrowstyle="-|>",
                                   color=C["nephron_blood"], lw=2))
        ax.text(2.9, 10.7, "Afferent\narteriole", ha="center",
                fontsize=8, color=C["nephron_blood"])
        ax.annotate("", xy=(3.2, 9.2), xytext=(4.45, 9.2),
                    arrowprops=dict(arrowstyle="-|>",
                                   color="#c0392b", lw=2))
        ax.text(2.6, 9.0, "Efferent\narteriole", ha="center",
                fontsize=8, color="#c0392b")

    # ── Proximal Convoluted Tubule (PCT) ──────────────────────────────────────
    t_pct = np.linspace(0, 4 * np.pi, 200)
    x_pct = 5.4 + 1.6 * np.sin(t_pct) + 0.15 * t_pct
    y_pct = 8.65 - 0.35 * t_pct / (4 * np.pi)
    ax.plot(x_pct, y_pct, color=C["nephron_tubule"], lw=lw_t,
            solid_capstyle="round", zorder=3)
    if schema.show_labels:
        _annotate(ax, "PCT\n(Proximal Convoluted\nTubule)",
                  (x_pct[80], y_pct[80]), (8.5, 8.0),
                  C["nephron_tubule"], fontsize=8,
                  highlight=bool(hl and "pct" in hl))

    # ── Loop of Henle ─────────────────────────────────────────────────────────
    # Descending limb
    x_desc = np.linspace(6.5, 6.5, 50)
    y_desc = np.linspace(8.1, 3.0, 50)
    ax.plot(x_desc, y_desc, color=C["nephron_tubule"], lw=lw_t, zorder=3)
    # Bend at bottom
    theta_bend = np.linspace(np.pi, 0, 50)
    x_bend = 5.5 + 1.0 * np.cos(theta_bend)
    y_bend = 3.0 + 0.6 * np.sin(theta_bend)
    ax.plot(x_bend, y_bend, color=C["nephron_tubule"], lw=lw_t, zorder=3)
    # Ascending limb
    x_asc = np.linspace(4.5, 4.5, 50)
    y_asc = np.linspace(3.0, 7.8, 50)
    ax.plot(x_asc, y_asc, color=C["nephron_tubule"], lw=lw_t, zorder=3)
    if schema.show_labels:
        _annotate(ax, "Loop of Henle\n(Descending limb)",
                  (6.5, 5.5), (8.2, 5.5), C["nephron_tubule"], fontsize=8,
                  highlight=bool(hl and "loop" in hl))
        _annotate(ax, "Ascending\nlimb",
                  (4.5, 5.5), (2.5, 5.0), C["nephron_tubule"], fontsize=8,
                  highlight=bool(hl and "loop" in hl))

    # ── Distal Convoluted Tubule (DCT) ────────────────────────────────────────
    t_dct = np.linspace(0, 3 * np.pi, 150)
    x_dct = 4.0 - 1.4 * np.sin(t_dct) - 0.08 * t_dct
    y_dct = 7.8 + 0.28 * t_dct / (3 * np.pi)
    ax.plot(x_dct, y_dct, color=C["nephron_tubule"], lw=lw_t,
            solid_capstyle="round", zorder=3)
    if schema.show_labels:
        _annotate(ax, "DCT\n(Distal Convoluted\nTubule)",
                  (x_dct[60], y_dct[60]), (1.5, 8.5),
                  C["nephron_tubule"], fontsize=8,
                  highlight=bool(hl and "dct" in hl))

    # ── Collecting Duct ───────────────────────────────────────────────────────
    cd_x = [3.0, 3.0]
    cd_y = [8.1, 1.0]
    ax.plot(cd_x, cd_y, color=C["nephron_tubule"], lw=lw_t + 0.5,
            solid_capstyle="butt", zorder=3)
    # Funnel at bottom → pelvis
    ax.annotate("", xy=(5, 0.5), xytext=(3.0, 1.0),
                arrowprops=dict(arrowstyle="-|>", color=C["nephron_tubule"], lw=2))
    ax.text(5.5, 0.4, "Renal pelvis", fontsize=8, color=C["nephron_tubule"])
    if schema.show_labels:
        _annotate(ax, "Collecting\nDuct",
                  (3.0, 5.0), (1.2, 4.0), C["nephron_tubule"], fontsize=8,
                  highlight=bool(hl and "collecting" in hl))

    # ── Peritubular capillaries ────────────────────────────────────────────────
    if schema.show_blood_vessels:
        # Simple representation: dotted red lines alongside tubules
        ax.plot([6.8, 6.8], [8.0, 3.2], color="#ef9a9a",
                lw=1.8, ls="dotted", zorder=2)
        ax.plot([4.2, 4.2], [3.2, 7.8], color="#ef9a9a",
                lw=1.8, ls="dotted", zorder=2)
        ax.text(7.1, 5.5, "Peritubular\ncapillaries",
                fontsize=7.5, color=C["nephron_blood"], rotation=90,
                ha="center", va="center")

    ax.set_title(schema.title or "Nephron Structure",
                 fontsize=14, fontweight="bold", pad=6)
    fig.tight_layout(pad=0.4)
    return _fig_to_svg(fig)


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Neuron Diagram
# ═══════════════════════════════════════════════════════════════════════════════

def render_neuron_diagram(data: Dict[str, Any],
                           canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = NeuronDiagramSchema(**data)

    fig, ax = plt.subplots(figsize=(12, 4.5))
    ax.set_xlim(-1, 14); ax.set_ylim(-2.5, 3.5)
    ax.set_aspect("equal"); ax.axis("off")

    # ── Dendrites (branching from soma) ───────────────────────────────────────
    soma_x = 1.5
    dendrite_tips = [(-0.5, 2.0), (-0.8, 0.5), (-0.5, -1.2),
                      (0.2, 2.4), (0.8, -1.8)]
    for dx, dy in dendrite_tips:
        ax.plot([soma_x + dx * 0.7, soma_x - 0.4],
                [dy * 0.7, 0], color=C["neuron_dendrite"],
                lw=2.0, solid_capstyle="round", zorder=3)
        # Secondary branches
        mid_x = (soma_x + dx * 0.7 + soma_x - 0.4) / 2
        mid_y = (dy * 0.7 + 0) / 2
        ax.plot([mid_x, mid_x + 0.3 * dy * 0.2],
                [mid_y, mid_y + 0.4], color=C["neuron_dendrite"],
                lw=1.2, solid_capstyle="round", zorder=3)

    if schema.show_labels:
        _annotate(ax, "Dendrites", (-0.5, 1.5), (-1.0, 2.8),
                  C["neuron_dendrite"], fontsize=9)

    # ── Cell body (soma) ──────────────────────────────────────────────────────
    soma = Circle((soma_x, 0), 0.85, fc="#ffe0b2",
                   ec=C["neuron_soma"], lw=2.5, zorder=5)
    ax.add_patch(soma)
    # Nucleus inside soma
    nuc = Circle((soma_x, 0.1), 0.38, fc="#e8eaf6",
                  ec=C["nucleus"], lw=1.5, zorder=6)
    ax.add_patch(nuc)
    ax.text(soma_x, 0.1, "N", ha="center", va="center",
            fontsize=8, fontweight="bold", color=C["nucleus"], zorder=7)
    if schema.show_labels:
        _annotate(ax, "Cell body\n(Soma)", (soma_x, -0.85), (0.5, -2.0),
                  C["neuron_soma"], fontsize=9)
        ax.text(soma_x + 0.05, 0.1, "", ha="center")   # nucleus already marked
        _annotate(ax, "Nucleus", (soma_x, 0.1), (soma_x - 0.8, 1.5),
                  C["nucleus"], fontsize=8)

    # ── Axon hillock ──────────────────────────────────────────────────────────
    ax.annotate("", xy=(2.8, 0), xytext=(soma_x + 0.85, 0),
                arrowprops=dict(arrowstyle="-", color=C["neuron_axon"], lw=2.5))
    if schema.show_labels:
        ax.text(2.4, 0.35, "Axon\nhillock", ha="center",
                fontsize=8, color="#555555")

    # ── Axon with myelin sheath and nodes of Ranvier ──────────────────────────
    axon_start = 2.8
    axon_end   = 11.5
    ax.plot([axon_start, axon_end], [0, 0],
            color=C["neuron_axon"], lw=2.5, zorder=3)

    if schema.neuron_type == "myelinated":
        # Myelin sheath segments (rectangles) with gaps (nodes of Ranvier)
        node_positions = np.arange(3.2, axon_end - 0.5, 2.0)
        for nx in node_positions:
            sheath = FancyBboxPatch((nx, -0.35), 1.6, 0.7,
                                    boxstyle="round,pad=0.05",
                                    fc=C["neuron_myelin"],
                                    ec="#f9a825", lw=1.5, zorder=4)
            ax.add_patch(sheath)
            # Node of Ranvier (gap between sheaths)
            ax.plot(nx - 0.05, 0, "o", color=C["neuron_axon"],
                    markersize=5, zorder=5)

        if schema.show_labels:
            _annotate(ax, "Myelin sheath\n(Schwann cell)",
                      (5.0, 0.35), (5.0, 1.8), "#f9a825", fontsize=9)
            _annotate(ax, "Node of\nRanvier",
                      (5.1, 0), (6.2, -1.5), "#795548", fontsize=9)

    # ── Impulse direction arrow ────────────────────────────────────────────────
    if schema.show_impulse_direction:
        ax.annotate("", xy=(8.5, 0.85), xytext=(5.0, 0.85),
                    arrowprops=dict(arrowstyle="-|>", color="#e53935", lw=1.5))
        ax.text(6.8, 1.1, "Impulse →", ha="center",
                fontsize=8.5, color="#e53935", fontweight="bold")

    # ── Axon terminal / end bulbs ─────────────────────────────────────────────
    terminal_x = axon_end
    for dy, offset_x in [(0.0, 0.5), (0.6, 0.6), (-0.6, 0.6)]:
        tx = terminal_x + offset_x
        ty = dy
        ax.plot([terminal_x, tx], [0, ty],
                color=C["neuron_axon"], lw=2, solid_capstyle="round", zorder=3)
        ax.add_patch(Circle((tx + 0.25, ty), 0.3, fc="#e8f5e9",
                             ec=C["neuron_axon"], lw=1.5, zorder=4))
    if schema.show_labels:
        _annotate(ax, "Axon terminal\n(End bulbs / Synaptic knobs)",
                  (terminal_x + 0.5, 0), (terminal_x + 0.5, 2.0),
                  C["neuron_axon"], fontsize=9)

    if schema.show_labels:
        _annotate(ax, "Axon", (7.0, 0), (7.0, -2.0),
                  C["neuron_axon"], fontsize=9)

    ax.set_title(schema.title or f"Neuron ({schema.neuron_type.capitalize()})",
                 fontsize=13, fontweight="bold", pad=6)
    fig.tight_layout(pad=0.3)
    return _fig_to_svg(fig)


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Food Web
# ═══════════════════════════════════════════════════════════════════════════════

def render_food_web(data: Dict[str, Any],
                    canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = FoodWebSchema(**data)

    fig, ax = plt.subplots(figsize=(10, 7))
    ax.set_aspect("equal"); ax.axis("off")

    # Position nodes by trophic level (y) and spread evenly (x)
    levels: Dict[int, list] = {}
    for node in schema.nodes:
        levels.setdefault(node.trophic_level, []).append(node)

    max_level = max(levels.keys())
    pos: Dict[str, Tuple[float, float]] = {}
    ax.set_xlim(-1, 11); ax.set_ylim(-0.5, max_level + 0.5)

    level_colors = [C["producer"], C["primary"], C["secondary"],
                    C["tertiary"], C["quaternary"]]
    level_names  = ["Producer", "Primary Consumer", "Secondary Consumer",
                    "Tertiary Consumer", "Quaternary Consumer"]

    for lvl, nodes_at_level in sorted(levels.items()):
        n = len(nodes_at_level)
        xs = np.linspace(1.0, 9.0, n)
        for i, node in enumerate(nodes_at_level):
            y = lvl - 0.5
            pos[node.id] = (xs[i], y)
            clr = level_colors[min(lvl - 1, len(level_colors) - 1)]
            box = FancyBboxPatch((xs[i] - 0.7, y - 0.3), 1.4, 0.6,
                                  boxstyle="round,pad=0.1",
                                  fc=clr, ec="white", lw=1.5,
                                  alpha=0.85, zorder=3)
            ax.add_patch(box)
            ax.text(xs[i], y, node.label, ha="center", va="center",
                    fontsize=9, color="white", fontweight="bold", zorder=4)

    # ── Arrows (energy flow: prey → predator) ────────────────────────────────
    for edge in schema.edges:
        if edge.from_id in pos and edge.to_id in pos:
            x1, y1 = pos[edge.from_id]
            x2, y2 = pos[edge.to_id]
            ax.annotate("", xy=(x2, y2 - 0.3), xytext=(x1, y1 + 0.3),
                        arrowprops=dict(arrowstyle="-|>", color="#555555",
                                       lw=1.5, connectionstyle="arc3,rad=0.1"),
                        zorder=2)

    # ── Trophic level labels on y-axis ────────────────────────────────────────
    for lvl in sorted(levels.keys()):
        name = level_names[min(lvl - 1, len(level_names) - 1)]
        ax.text(-0.8, lvl - 0.5, f"T{lvl}\n{name}", ha="right",
                va="center", fontsize=8, color="#555555")

    ax.set_title(schema.title or "Food Web", fontsize=14,
                 fontweight="bold", pad=6)
    fig.tight_layout(pad=0.4)
    return _fig_to_svg(fig)


# ═══════════════════════════════════════════════════════════════════════════════
# 8. Food Chain
# ═══════════════════════════════════════════════════════════════════════════════

def render_food_chain(data: Dict[str, Any],
                       canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = FoodChainSchema(**data)
    organisms = schema.organisms
    n = len(organisms)

    fig, ax = plt.subplots(figsize=(max(8, n * 1.8), 3.5))
    ax.set_xlim(-0.5, n); ax.set_ylim(-0.8, 1.5)
    ax.set_aspect("equal"); ax.axis("off")

    level_colors = [C["producer"], C["primary"], C["secondary"],
                    C["tertiary"], C["quaternary"], C["quinary"],
                    "#37474f", "#263238"]
    trophic_names = ["Producer", "1° Consumer", "2° Consumer",
                     "3° Consumer", "4° Consumer", "5° Consumer", "", ""]

    for i, name in enumerate(organisms):
        xi = i
        clr = level_colors[min(i, len(level_colors) - 1)]
        box = FancyBboxPatch((xi - 0.42, -0.22), 0.84, 0.44,
                              boxstyle="round,pad=0.08",
                              fc=clr, ec="white", lw=1.8, zorder=3)
        ax.add_patch(box)
        ax.text(xi, 0, name, ha="center", va="center",
                fontsize=10, color="white", fontweight="bold", zorder=4)
        # Trophic level label below
        tname = trophic_names[min(i, len(trophic_names) - 1)]
        ax.text(xi, -0.52, tname, ha="center", va="center",
                fontsize=7.5, color="#555555")
        # Arrow to next
        if i < n - 1:
            ax.annotate("", xy=(xi + 0.48, 0), xytext=(xi + 0.44, 0),
                        arrowprops=dict(arrowstyle="-|>", color="#333333",
                                       lw=1.8, mutation_scale=16))

    ax.set_title(schema.title or "Food Chain", fontsize=13,
                 fontweight="bold", pad=6)
    ax.text(n / 2 - 0.5, 1.1,
            "Energy flow direction →",
            ha="center", fontsize=9, color="#555555", style="italic")
    fig.tight_layout(pad=0.3)
    return _fig_to_svg(fig)


# ═══════════════════════════════════════════════════════════════════════════════
# 9. Ecological Pyramid
# ═══════════════════════════════════════════════════════════════════════════════

def render_ecological_pyramid(data: Dict[str, Any],
                               canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = EcologicalPyramidSchema(**data)
    levels = schema.levels
    n = len(levels)

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.set_xlim(-0.5, 10.5); ax.set_ylim(-0.5, n + 0.5)
    ax.set_aspect("equal"); ax.axis("off")

    level_colors = [C["producer"], C["primary"], C["secondary"],
                    C["tertiary"], C["quaternary"], C["quinary"]]

    max_half_width = 4.5
    row_height = 0.8
    row_gap    = 0.12

    for i, lvl in enumerate(levels):
        # Widest at bottom (i=0), narrowest at top (i=n-1)
        frac = 1.0 - (i / (n - 0.5)) * 0.88
        hw = max_half_width * frac
        cx = 5.0
        y_bottom = i * (row_height + row_gap)
        y_top    = y_bottom + row_height

        clr = level_colors[min(i, len(level_colors) - 1)]
        # Trapezoid vertices (bottom wider, top narrower for next level)
        next_frac = 1.0 - ((i + 1) / (n - 0.5)) * 0.88 if i < n - 1 else frac * 0.3
        nhw = max_half_width * next_frac
        trap = plt.Polygon(
            [[cx - hw, y_bottom], [cx + hw, y_bottom],
             [cx + nhw, y_top],   [cx - nhw, y_top]],
            fc=clr, ec="white", lw=1.5, zorder=3, alpha=0.88,
        )
        ax.add_patch(trap)

        # Label inside
        label = lvl.label
        ax.text(cx, y_bottom + row_height / 2, label,
                ha="center", va="center",
                fontsize=9.5, color="white", fontweight="bold", zorder=4)

        # Value on right side
        if lvl.value is not None:
            val_str = f"{lvl.value:g} {lvl.unit}".strip()
            ax.text(cx + hw + 0.2, y_bottom + row_height / 2,
                    val_str, ha="left", va="center",
                    fontsize=8.5, color=clr)

    # ── Pyramid type label ────────────────────────────────────────────────────
    ptype = schema.pyramid_type.capitalize()
    ax.set_title(schema.title or f"Ecological Pyramid of {ptype}",
                 fontsize=13, fontweight="bold", pad=6)
    # Y-axis label
    ax.text(-0.3, n / 2, "Trophic Levels →",
            ha="center", va="center", rotation=90,
            fontsize=9, color="#555555")

    fig.tight_layout(pad=0.4)
    return _fig_to_svg(fig)


# ═══════════════════════════════════════════════════════════════════════════════
# 10. Punnett Square
# ═══════════════════════════════════════════════════════════════════════════════

def _allele_key(ch: str) -> Tuple[str, bool]:
    """Sort key: dominant (uppercase) allele before recessive of the same letter."""
    return (ch.lower(), ch.islower())


def _canonical_genotype(genotype: str) -> str:
    """'aA'→'Aa', 'bBaA'→'AaBb' — order each locus pair, then order loci by letter."""
    pairs = [genotype[i:i + 2] for i in range(0, len(genotype), 2)]
    ordered = ["".join(sorted(p, key=_allele_key)) for p in pairs]
    ordered.sort(key=lambda p: p[0].lower())
    return "".join(ordered)


def _combine_gametes(g1: str, g2: str) -> str:
    """Fuse two gametes locus by locus: ('AB','ab') → 'AaBb'."""
    return "".join(
        "".join(sorted([g1[i], g2[i]], key=_allele_key))
        for i in range(len(g1))
    )


def _dominance_rank(genotype: str) -> Tuple[int, str]:
    """Order genotypes AA → Aa → aa (most dominant alleles first)."""
    return (-sum(1 for ch in genotype if ch.isupper()), genotype)


def _ratio_text(counts: Dict[str, int], order: List[str]) -> str:
    """{'AA':1,'Aa':2,'aa':1} → '1 AA : 2 Aa : 1 aa' (reduced to lowest terms)."""
    divisor = reduce(math.gcd, counts.values())
    return "  :  ".join(f"{counts[k] // divisor} {k}" for k in order)


def render_punnett_square(data: Dict[str, Any],
                          canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = PunnettSquareSchema(**data)

    cols = schema.parent1_alleles     # across the top
    rows = schema.parent2_alleles     # down the left
    n, m = len(cols), len(rows)
    loci = len(cols[0])

    # ── Offspring grid ────────────────────────────────────────────────────────
    # cell[i][j] = parent2 gamete i  ×  parent1 gamete j
    cells = [[_combine_gametes(cols[j], rows[i]) for j in range(n)]
             for i in range(m)]
    flat = [g for row in cells for g in row]

    # ── Ratios ────────────────────────────────────────────────────────────────
    geno_counts = Counter(flat)
    geno_order = sorted(geno_counts, key=_dominance_rank)

    pheno_map = {_canonical_genotype(k): v
                 for k, v in (schema.phenotype_map or {}).items()}
    has_pheno = bool(pheno_map)
    pheno_of = {g: pheno_map.get(g, g) for g in geno_counts}
    pheno_counts = Counter(pheno_of[g] for g in flat)
    # most common phenotype first; alphabetical tie-break keeps it deterministic
    pheno_order = sorted(pheno_counts, key=lambda p: (-pheno_counts[p], p))
    pheno_fill = {p: _PHENOTYPE_FILLS[k % len(_PHENOTYPE_FILLS)]
                  for k, p in enumerate(pheno_order)}

    show_geno = schema.show_genotype_ratio
    show_pheno = schema.show_phenotype_ratio and has_pheno
    n_ratio_lines = int(show_geno) + int(show_pheno)

    # ── Canvas ────────────────────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(2.2 + 1.05 * (n + 1),
                                    2.2 + 1.05 * (m + 1)))
    y_bottom = -0.35 - 0.62 * n_ratio_lines
    ax.set_xlim(-1.15, n + 1.25)
    ax.set_ylim(y_bottom, m + 1.8)
    ax.set_aspect("equal")
    ax.axis("off")

    # Font sizes shrink as the grid grows / genotypes get longer, so a dihybrid
    # square stays legible at exam print size.
    geno_len = 2 * loci
    cell_fs = max(6.5, 24.0 - 2.0 * geno_len - 1.0 * max(n, m))
    head_fs = cell_fs + 1.5

    # ── Header row (parent 1 gametes) ─────────────────────────────────────────
    for j, gamete in enumerate(cols):
        ax.add_patch(Rectangle((1 + j, m), 1, 1, fc=C["punnett_header"],
                               ec=C["punnett_grid"], lw=1.2, zorder=3))
        ax.text(1.5 + j, m + 0.5, gamete, ha="center", va="center",
                fontsize=head_fs, fontweight="bold",
                color=C["nucleus"], zorder=4)

    # ── Header column (parent 2 gametes) ──────────────────────────────────────
    for i, gamete in enumerate(rows):
        ax.add_patch(Rectangle((0, m - 1 - i), 1, 1, fc=C["punnett_header"],
                               ec=C["punnett_grid"], lw=1.2, zorder=3))
        ax.text(0.5, m - 0.5 - i, gamete, ha="center", va="center",
                fontsize=head_fs, fontweight="bold",
                color=C["nucleus"], zorder=4)

    # ── Corner cell ───────────────────────────────────────────────────────────
    ax.add_patch(Rectangle((0, m), 1, 1, fc=C["punnett_corner"],
                           ec=C["punnett_grid"], lw=1.2, zorder=3))
    ax.text(0.5, m + 0.5, "×", ha="center", va="center",
            fontsize=head_fs + 2, color="#546e7a", zorder=4)

    # ── Offspring cells ───────────────────────────────────────────────────────
    for i in range(m):
        for j in range(n):
            genotype = cells[i][j]
            fc = pheno_fill[pheno_of[genotype]] if has_pheno else C["punnett_cell"]
            ax.add_patch(Rectangle((1 + j, m - 1 - i), 1, 1, fc=fc,
                                   ec=C["punnett_grid"], lw=1.2, zorder=3))
            ax.text(1.5 + j, m - 0.5 - i, genotype, ha="center", va="center",
                    fontsize=cell_fs, fontweight="bold",
                    color="#212121", zorder=4)

    # ── Outer border ──────────────────────────────────────────────────────────
    ax.add_patch(Rectangle((0, 0), n + 1, m + 1, fill=False,
                           ec=C["punnett_grid"], lw=2.2, zorder=5))

    # ── Parent labels ─────────────────────────────────────────────────────────
    p1_label = schema.parent1_label or "Parent 1 gametes"
    p2_label = schema.parent2_label or "Parent 2 gametes"
    ax.text(1 + n / 2, m + 1.32, p1_label, ha="center", va="center",
            fontsize=11, fontweight="bold", color=C["nucleus"])
    ax.text(-0.48, m / 2, p2_label, ha="center", va="center", rotation=90,
            fontsize=11, fontweight="bold", color=C["nucleus"])

    # ── Ratios ────────────────────────────────────────────────────────────────
    y_line = -0.55
    if show_geno:
        ax.text((n + 1) / 2, y_line,
                f"Genotype ratio  —  {_ratio_text(geno_counts, geno_order)}",
                ha="center", va="center", fontsize=10.5,
                fontweight="bold", color=C["chromosome"])
        y_line -= 0.62
    if show_pheno:
        ax.text((n + 1) / 2, y_line,
                f"Phenotype ratio  —  {_ratio_text(pheno_counts, pheno_order)}",
                ha="center", va="center", fontsize=10.5,
                fontweight="bold", color=C["producer"])

    # ── Phenotype key ─────────────────────────────────────────────────────────
    if has_pheno:
        handles = [mpatches.Patch(fc=pheno_fill[p], ec=C["punnett_grid"],
                                  lw=1.0, label=p) for p in pheno_order]
        ax.legend(handles=handles, title="Phenotype", loc="upper left",
                  bbox_to_anchor=(1.01, 1.0), fontsize=8.5,
                  title_fontsize=9, frameon=True)

    # ── Title ─────────────────────────────────────────────────────────────────
    cross_name = {1: "Monohybrid", 2: "Dihybrid", 3: "Trihybrid"}.get(
        loci, f"{loci}-Locus")
    default_title = f"Punnett Square — {cross_name} Cross"
    if schema.trait_name:
        default_title += f" ({schema.trait_name})"
    ax.set_title(schema.title or default_title,
                 fontsize=13, fontweight="bold", pad=6)

    fig.tight_layout(pad=0.4)
    return _fig_to_svg(fig)


# ═══════════════════════════════════════════════════════════════════════════════
# 11. Pedigree Chart
# ═══════════════════════════════════════════════════════════════════════════════

_ROMAN = [(10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]


def _roman_numeral(num: int) -> str:
    out, n = [], num
    for value, sym in _ROMAN:
        while n >= value:
            out.append(sym)
            n -= value
    return "".join(out)


def render_pedigree_chart(data: Dict[str, Any],
                          canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = PedigreeChartSchema(**data)

    inds = schema.individuals
    by_id = {ind.id: ind for ind in inds}
    matings = schema.matings

    SPACING = 2.0      # min horizontal gap between individuals
    GROUP_GAP = 1.0    # extra gap between distinct sibships
    ROW_H = 2.6        # vertical gap between generations
    SYM_R = 0.42       # circle radius / half square side

    # ── Generation rows (generation 1 at the top) ─────────────────────────────
    gens = sorted({ind.generation for ind in inds})
    row_of = {g: idx for idx, g in enumerate(gens)}
    row_y = {g: -row_of[g] * ROW_H for g in gens}
    y_of = {ind.id: row_y[ind.generation] for ind in inds}

    # ── Relationship lookups ──────────────────────────────────────────────────
    child_group: Dict[str, int] = {}     # child id → index of the mating it came from
    for mi, mating in enumerate(matings):
        for cid in mating.child_ids:
            child_group.setdefault(cid, mi)

    mate_of: Dict[str, str] = {}
    for mating in matings:
        mate_of.setdefault(mating.parent1_id, mating.parent2_id)
        mate_of.setdefault(mating.parent2_id, mating.parent1_id)

    parent_mating: Dict[str, Any] = {}   # parent id → their mating that has children
    for mating in matings:
        if mating.child_ids:
            parent_mating.setdefault(mating.parent1_id, mating)
            parent_mating.setdefault(mating.parent2_id, mating)

    # ── Left→right ordering within each generation ────────────────────────────
    # Siblings stay contiguous; a married-in spouse sits next to their mate.
    def _order_generation(gen: int) -> List[str]:
        gen_ids = [ind.id for ind in inds if ind.generation == gen]
        ordered: List[str] = []
        placed: set = set()

        def _same_gen(cid: str) -> bool:
            return cid in by_id and by_id[cid].generation == gen

        for id_ in gen_ids:
            if id_ in placed:
                continue
            # A married-in spouse is emitted right after their mate, not here.
            if child_group.get(id_) is None:
                mate = mate_of.get(id_)
                if mate and _same_gen(mate) and child_group.get(mate) is not None:
                    continue
            mi = child_group.get(id_)
            sibship = ([c for c in matings[mi].child_ids if _same_gen(c)]
                       if mi is not None else [id_])
            for member in sibship:
                if member in placed:
                    continue
                ordered.append(member)
                placed.add(member)
                mate = mate_of.get(member)
                if (mate and mate not in placed and _same_gen(mate)
                        and child_group.get(mate) is None):
                    ordered.append(mate)
                    placed.add(mate)

        # Safety net — anything the rules above missed keeps its input order.
        ordered.extend(i for i in gen_ids if i not in placed)
        return ordered

    order = {g: _order_generation(g) for g in gens}

    # ── X layout, bottom-up: parents are centred over their children ──────────
    x: Dict[str, float] = {}

    cursor, prev_group = 0.0, None
    for id_ in order[gens[-1]]:
        group = child_group.get(id_, f"solo:{id_}")
        if prev_group is not None and group != prev_group:
            cursor += GROUP_GAP
        x[id_] = cursor
        cursor += SPACING
        prev_group = group

    for gen in reversed(gens[:-1]):
        ordered = order[gen]
        pos: Dict[str, Optional[float]] = {id_: None for id_ in ordered}

        for id_ in ordered:
            mating = parent_mating.get(id_)
            if mating is None:
                continue
            child_xs = [x[c] for c in mating.child_ids if c in x]
            if not child_xs:
                continue
            centre = sum(child_xs) / len(child_xs)
            partner = (mating.parent2_id if mating.parent1_id == id_
                       else mating.parent1_id)
            offset = 0.0
            if partner in ordered:
                offset = (-SPACING / 2 if ordered.index(id_) < ordered.index(partner)
                          else SPACING / 2)
            pos[id_] = centre + offset

        # Individuals with no placed children hang off their nearest neighbour.
        for k, id_ in enumerate(ordered):
            if pos[id_] is not None:
                continue
            anchor = next((j for j in range(k - 1, -1, -1)
                           if pos[ordered[j]] is not None), None)
            if anchor is not None:
                pos[id_] = pos[ordered[anchor]] + SPACING * (k - anchor)
                continue
            anchor = next((j for j in range(k + 1, len(ordered))
                           if pos[ordered[j]] is not None), None)
            pos[id_] = (pos[ordered[anchor]] - SPACING * (anchor - k)
                        if anchor is not None else k * SPACING)

        # Left→right sweep: keep the order, enforce the minimum spacing.
        for k in range(1, len(ordered)):
            lo = pos[ordered[k - 1]] + SPACING
            if pos[ordered[k]] < lo:
                pos[ordered[k]] = lo
        for id_ in ordered:
            x[id_] = pos[id_]

    # ── Canvas ────────────────────────────────────────────────────────────────
    x_min, x_max = min(x.values()), max(x.values())
    y_min = row_y[gens[-1]]
    x_label = x_min - 1.4      # roman-numeral gutter

    width_units = (x_max - x_label) + 1.6
    height_units = (len(gens) - 1) * ROW_H + 2.8
    fig, ax = plt.subplots(figsize=(max(7.0, 0.8 * width_units),
                                    max(4.2, 0.8 * height_units)))
    ax.set_xlim(x_label - 0.7, x_max + 1.0)
    ax.set_ylim(y_min - 1.5, 1.0)
    ax.set_aspect("equal")
    ax.axis("off")

    line_c = C["pedigree_line"]

    # ── Mating + sibship lines (drawn under the symbols) ──────────────────────
    for mating in matings:
        p1, p2 = mating.parent1_id, mating.parent2_id
        (xl, yl), (xr, yr) = sorted([(x[p1], y_of[p1]), (x[p2], y_of[p2])])
        # Horizontal mating line, symbol edge to symbol edge
        ax.plot([xl + SYM_R, xr - SYM_R], [yl, yr],
                color=line_c, lw=1.6, zorder=2)

        kids = [c for c in mating.child_ids if c in x]
        if not kids:
            continue
        mid_x = (xl + xr) / 2
        mid_y = (yl + yr) / 2
        kid_xs = [x[c] for c in kids]
        top_kid_y = max(y_of[c] for c in kids)
        # Sit the sibship line below the halfway point so it clears the parents'
        # number + label captions rather than cutting through them.
        y_sib = mid_y + (top_kid_y - mid_y) * 0.62

        # Descent line from the mating down to the sibship line
        ax.plot([mid_x, mid_x], [mid_y, y_sib], color=line_c, lw=1.6, zorder=2)
        # Sibship line — always spans the descent point so the two connect
        ax.plot([min(min(kid_xs), mid_x), max(max(kid_xs), mid_x)],
                [y_sib, y_sib], color=line_c, lw=1.6, zorder=2)
        # Drop line to each child
        for c in kids:
            ax.plot([x[c], x[c]], [y_sib, y_of[c] + SYM_R],
                    color=line_c, lw=1.6, zorder=2)

    # ── Individuals: males = squares, females = circles, affected = shaded ────
    for gen in gens:
        ranked = sorted(order[gen], key=lambda i: (x[i], order[gen].index(i)))
        for number, id_ in enumerate(ranked, start=1):
            ind = by_id[id_]
            xi, yi = x[id_], y_of[id_]
            fc = C["pedigree_fill"] if ind.affected else "white"

            if ind.sex == "male":
                ax.add_patch(Rectangle((xi - SYM_R, yi - SYM_R),
                                       2 * SYM_R, 2 * SYM_R,
                                       fc=fc, ec=line_c, lw=1.8, zorder=4))
            else:
                ax.add_patch(Circle((xi, yi), SYM_R,
                                    fc=fc, ec=line_c, lw=1.8, zorder=4))

            # Individual number (e.g. II-2 → the "2")
            ax.text(xi, yi - SYM_R - 0.32, str(number), ha="center", va="center",
                    fontsize=9, fontweight="bold", color=line_c, zorder=5)
            if ind.label:
                ax.text(xi, yi - SYM_R - 0.72, ind.label, ha="center", va="center",
                        fontsize=8, color="#555555", style="italic", zorder=5)

    # ── Generation numerals ───────────────────────────────────────────────────
    for gen in gens:
        ax.text(x_label, row_y[gen], _roman_numeral(gen),
                ha="center", va="center", fontsize=13,
                fontweight="bold", color=C["nucleus"], zorder=5)

    # ── Legend ────────────────────────────────────────────────────────────────
    if schema.show_legend:
        def _key(marker: str, filled: bool, label: str) -> Line2D:
            return Line2D([0], [0], marker=marker, color="none",
                          markerfacecolor=C["pedigree_fill"] if filled else "white",
                          markeredgecolor=line_c, markeredgewidth=1.5,
                          markersize=11, label=label)

        ax.legend(handles=[
            _key("s", False, "Unaffected male"),
            _key("s", True, "Affected male"),
            _key("o", False, "Unaffected female"),
            _key("o", True, "Affected female"),
        ], loc="upper left", bbox_to_anchor=(1.01, 1.0),
            fontsize=8.5, frameon=True)

    ax.set_title(schema.title or "Pedigree Chart",
                 fontsize=14, fontweight="bold", pad=6)
    fig.tight_layout(pad=0.4)
    return _fig_to_svg(fig)


# ═══════════════════════════════════════════════════════════════════════════════
# Shared helpers for the anatomy / molecular-biology renderers
# ═══════════════════════════════════════════════════════════════════════════════

def _norm(name: Optional[str]) -> str:
    return (name or "").lower().strip().replace(" ", "_").replace("-", "_")


def _is_hl(hl: str, *aliases: str) -> bool:
    """True when the caller asked to highlight one of these part names."""
    return bool(hl) and hl in aliases


def _blade(x0: float, y0: float, angle_deg: float,
           length: float, width: float) -> Path:
    """Leaf-shaped blade (two quadratic Béziers, base → tip → base).

    Used for sepals and petals; `width` is the half-width at the widest point.
    """
    a = math.radians(angle_deg)
    ux, uy = math.cos(a), math.sin(a)
    px, py = -uy, ux
    tip = (x0 + ux * length, y0 + uy * length)
    mid_x, mid_y = x0 + ux * length * 0.4, y0 + uy * length * 0.4
    c1 = (mid_x + px * width, mid_y + py * width)
    c2 = (mid_x - px * width, mid_y - py * width)
    return Path(
        [(x0, y0), c1, tip, c2, (x0, y0)],
        [Path.MOVETO, Path.CURVE3, Path.CURVE3, Path.CURVE3, Path.CURVE3],
    )


def _bezier(p0: Tuple[float, float], ctrl: Tuple[float, float],
            p1: Tuple[float, float]) -> Path:
    return Path([p0, ctrl, p1], [Path.MOVETO, Path.CURVE3, Path.CURVE3])


def _coil(cx: float, amp: float, y_top: float, y_bot: float,
          loops: int, n: int = 600) -> Tuple[np.ndarray, np.ndarray]:
    """Serpentine coil descending from y_top to y_bot — gut loops, tubules."""
    theta = np.linspace(0, loops * np.pi, n)
    x = cx + amp * np.sin(theta)
    y = y_top - (theta / (loops * np.pi)) * (y_top - y_bot)
    return x, y


def _wrap(text: str, width: int = 18) -> str:
    """Greedy word wrap — keeps model-supplied node labels inside their box."""
    if "\n" in text:
        return text
    words, lines, line = text.split(), [], ""
    for w in words:
        candidate = f"{line} {w}".strip()
        if len(candidate) > width and line:
            lines.append(line)
            line = w
        else:
            line = candidate
    if line:
        lines.append(line)
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# 12. Flower Structure (L.S.)
# ═══════════════════════════════════════════════════════════════════════════════

def render_flower_structure(data: Dict[str, Any],
                            canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = FlowerStructureSchema(**data)
    hl = _norm(schema.highlight_part)
    hibiscus = schema.flower_type == "hibiscus"
    petal_c = C["petal_hibiscus"] if hibiscus else C["petal"]

    fig, ax = plt.subplots(figsize=(11, 9))
    ax.set_xlim(-2.4, 12.4); ax.set_ylim(-0.4, 9.8)
    ax.set_aspect("equal"); ax.axis("off")

    # ── Pedicel + receptacle (thalamus) ───────────────────────────────────────
    ax.plot([5, 5], [0.2, 2.1], color=C["pedicel"], lw=7,
            solid_capstyle="round", zorder=2)
    ax.add_patch(Ellipse((5, 2.4), 2.0, 1.0, fc=C["receptacle"],
                         ec=C["pedicel"], lw=1.5, zorder=3))

    # Hibiscus alone carries an epicalyx below the calyx.
    if hibiscus:
        for ang in (205, 335):
            ax.add_patch(PathPatch(_blade(5 + 0.7 * math.cos(math.radians(ang)),
                                          2.15, ang, 1.5, 0.18),
                                   fc="#7cb342", ec=C["pedicel"], lw=1.0, zorder=2))

    # ── Calyx (sepals) ────────────────────────────────────────────────────────
    for ang, base_x in ((152, 4.25), (28, 5.75)):
        ax.add_patch(PathPatch(_blade(base_x, 2.55, ang, 2.6, 0.32),
                               fc=C["sepal"], ec="#1b5e20", lw=1.4, zorder=3))

    # ── Corolla (petals) ──────────────────────────────────────────────────────
    for ang, base_x in ((133, 4.5), (47, 5.5)):
        ax.add_patch(PathPatch(_blade(base_x, 2.85, ang, 3.9, 0.8),
                               fc=petal_c, ec="#880e4f", lw=1.4,
                               alpha=0.9, zorder=3))

    # ── Gynoecium (carpel / pistil) ───────────────────────────────────────────
    ax.add_patch(Ellipse((5, 3.95), 1.9, 1.8, fc=C["ovary"],
                         ec="#1b5e20", lw=1.8, zorder=5))
    if schema.show_half_section:
        # The median half-section is what exposes the locule and the ovules.
        ax.add_patch(Ellipse((5, 3.95), 1.35, 1.25, fc="#e8f5e9",
                             ec="#1b5e20", lw=1.0, zorder=6))
        ax.plot([5, 5], [3.35, 4.55], color="#6d4c41", lw=1.6, zorder=7)  # placenta
        for sx in (-0.42, 0.42):
            ax.plot([5, 5 + sx * 0.55], [3.95, 3.85], color="#6d4c41",
                    lw=0.9, zorder=7)                                     # funicle
            ax.add_patch(Circle((5 + sx, 3.85), 0.3, fc=C["ovule"],
                                ec="#004d40", lw=1.2, zorder=8))
            ax.add_patch(Circle((5 + sx, 3.85), 0.13, fc="#b2dfdb",
                                ec="none", zorder=9))

    style_top = 6.6 if not hibiscus else 6.9
    ax.plot([5, 5], [4.7, style_top], color=C["style"], lw=3.5,
            solid_capstyle="round", zorder=5)

    if hibiscus:
        # Monadelphous androecium — filaments fused into a staminal tube around
        # the style, and the style itself ends in five stigmatic knobs.
        ax.add_patch(FancyBboxPatch((4.62, 4.6), 0.76, 2.0,
                                    boxstyle="round,pad=0.05",
                                    fc="#fff9c4", ec=C["filament"],
                                    lw=1.6, alpha=0.85, zorder=6))
        for i, ty in enumerate(np.linspace(4.95, 6.35, 5)):
            for side in (-1, 1):
                fx = 5 + side * 0.38
                ax.plot([fx, fx + side * 0.55], [ty, ty + 0.12],
                        color=C["filament"], lw=1.2, zorder=7)
                ax.add_patch(Ellipse((fx + side * 0.72, ty + 0.14), 0.34, 0.2,
                                     angle=10 * side, fc=C["anther"],
                                     ec="#f57f17", lw=1.0, zorder=8))
        for k, sx in enumerate(np.linspace(-0.5, 0.5, 5)):
            ax.plot([5, 5 + sx], [style_top, style_top + 0.35],
                    color=C["style"], lw=1.6, zorder=7)
            ax.add_patch(Circle((5 + sx, style_top + 0.45), 0.16,
                                fc=C["stigma"], ec="#4a148c", lw=1.0, zorder=8))
        stigma_xy = (5.5, style_top + 0.45)
        anther_xy = (5.72, 6.49)
        filament_xy = (5.38, 5.6)
    else:
        ax.add_patch(Ellipse((5, style_top + 0.25), 1.0, 0.45, fc=C["stigma"],
                             ec="#4a148c", lw=1.4, zorder=6))
        # Two free stamens, one either side of the carpel.
        for side in (-1, 1):
            base = (5 + side * 0.55, 2.95)
            top = (5 + side * 1.35, 5.55)
            ctrl = (5 + side * 1.35, 4.0)
            ax.add_patch(PathPatch(_bezier(base, ctrl, top), fc="none",
                                   ec=C["filament"], lw=2.6, zorder=4))
            ax.add_patch(Ellipse((top[0] + side * 0.05, top[1] + 0.35),
                                 0.55, 0.95, angle=-side * 12,
                                 fc=C["anther"], ec="#f57f17", lw=1.4, zorder=5))
        stigma_xy = (5.45, style_top + 0.3)
        anther_xy = (6.45, 5.9)
        filament_xy = (5.95, 4.3)

    # ── Labels ────────────────────────────────────────────────────────────────
    if schema.show_labels:
        _annotate(ax, "Anther", anther_xy, (-1.0, 8.6), C["anther"],
                  fontsize=9, highlight=_is_hl(hl, "anther"))
        _annotate(ax, "Filament", filament_xy, (-1.0, 7.0), C["filament"],
                  fontsize=9, highlight=_is_hl(hl, "filament"))
        _annotate(ax, "Stamen\n(Androecium)", (3.78, 5.0), (-1.0, 5.3),
                  "#827717", fontsize=9,
                  highlight=_is_hl(hl, "stamen", "androecium"))
        _annotate(ax, "Petal\n(Corolla)", (2.9, 4.9), (-1.1, 3.6), petal_c,
                  fontsize=9, highlight=_is_hl(hl, "petal", "corolla"))
        _annotate(ax, "Sepal\n(Calyx)", (3.4, 3.4), (-1.1, 1.8), C["sepal"],
                  fontsize=9, highlight=_is_hl(hl, "sepal", "calyx"))
        _annotate(ax, "Pedicel", (5.0, 0.9), (2.2, 0.2), C["pedicel"],
                  fontsize=9, highlight=_is_hl(hl, "pedicel"))

        _annotate(ax, "Stigma", stigma_xy, (10.6, 8.6), C["stigma"],
                  fontsize=9, highlight=_is_hl(hl, "stigma"))
        _annotate(ax, "Style", (5.1, 5.9), (10.6, 7.0), C["style"],
                  fontsize=9, highlight=_is_hl(hl, "style"))
        _annotate(ax, "Carpel / Pistil\n(Gynoecium)", (5.75, 4.7), (10.9, 5.4),
                  "#004d40", fontsize=9,
                  highlight=_is_hl(hl, "carpel", "pistil", "gynoecium"))
        _annotate(ax, "Ovary", (5.85, 4.0), (10.6, 3.7), C["ovary"],
                  fontsize=9, highlight=_is_hl(hl, "ovary"))
        if schema.show_half_section:
            _annotate(ax, "Ovule", (5.42, 3.85), (10.6, 2.4), C["ovule"],
                      fontsize=9, highlight=_is_hl(hl, "ovule"))
            _annotate(ax, "Placenta", (5.05, 4.3), (7.5, 5.5), "#6d4c41",
                      fontsize=8.5, highlight=_is_hl(hl, "placenta"))
        _annotate(ax, "Receptacle\n(Thalamus)", (5.9, 2.5), (10.9, 1.0),
                  C["receptacle"], fontsize=9,
                  highlight=_is_hl(hl, "receptacle", "thalamus"))
        if hibiscus:
            ax.text(2.9, 1.3, "Epicalyx", fontsize=8, color="#558b2f",
                    ha="center", style="italic")
            ax.text(5.0, 9.35, "Stamens monadelphous — filaments fused "
                               "into a staminal tube",
                    ha="center", fontsize=8.5, color="#827717", style="italic")

    flower_name = "Hibiscus" if hibiscus else "Typical"
    ax.set_title(schema.title or f"{flower_name} Flower — Longitudinal Section",
                 fontsize=14, fontweight="bold", pad=6)
    fig.tight_layout(pad=0.4)
    return _fig_to_svg(fig)


# ═══════════════════════════════════════════════════════════════════════════════
# 13. Eye Diagram (horizontal section)
# ═══════════════════════════════════════════════════════════════════════════════

# Focus of the parallel rays on the optic axis. The retina sits at x = 7.58, so
# myopia focuses short of it and hypermetropia beyond it — that offset IS the
# question NEET asks.
_EYE_FOCUS = {"none": 7.58, "myopia": 6.55, "hypermetropia": 8.85}
_EYE_DEFECT_NOTE = {
    "myopia": "Myopia (short-sightedness): image forms IN FRONT of the retina "
              "— corrected by a concave (diverging) lens",
    "hypermetropia": "Hypermetropia (long-sightedness): image forms BEHIND the "
                     "retina — corrected by a convex (converging) lens",
    "none": "Normal (emmetropic) eye: parallel rays converge exactly ON the "
            "retina at the yellow spot",
}

_EYE_C = (5.0, 5.0)      # centre of the eyeball
_R_SCLERA, _R_CHOROID, _R_RETINA = 3.0, 2.78, 2.58


def _retina_hit(p0: Tuple[float, float],
                target: Tuple[float, float]) -> Tuple[float, float]:
    """Where the ray from p0 towards `target` meets the retina (forward root)."""
    dx, dy = target[0] - p0[0], target[1] - p0[1]
    norm = math.hypot(dx, dy)
    dx, dy = dx / norm, dy / norm
    fx, fy = p0[0] - _EYE_C[0], p0[1] - _EYE_C[1]
    b = 2 * (fx * dx + fy * dy)
    c = fx * fx + fy * fy - _R_RETINA ** 2
    disc = math.sqrt(max(b * b - 4 * c, 0.0))
    t = (-b + disc) / 2
    return (p0[0] + t * dx, p0[1] + t * dy)


def render_eye_diagram(data: Dict[str, Any],
                       canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = EyeDiagramSchema(**data)
    hl = _norm(schema.highlight_part)

    fig, ax = plt.subplots(figsize=(13, 8))
    ax.set_xlim(-2.6, 13.6); ax.set_ylim(-0.9, 10.0)
    ax.set_aspect("equal"); ax.axis("off")

    cx, cy = _EYE_C

    # ── Eyeball interior + corneal bulge (both filled with aqueous colour) ────
    ax.add_patch(Circle((cx, cy), _R_SCLERA, fc=C["aqueous"], ec="none", zorder=1))
    top = (cx + _R_SCLERA * math.cos(math.radians(150)),
           cy + _R_SCLERA * math.sin(math.radians(150)))
    bot = (top[0], cy - (top[1] - cy))
    cornea_path = Path(
        [top, (0.85, cy), bot, top],
        [Path.MOVETO, Path.CURVE3, Path.CURVE3, Path.CLOSEPOLY],
    )
    ax.add_patch(PathPatch(cornea_path, fc=C["aqueous"], ec="none", zorder=1))
    # Stroke the bulge alone — the closing chord is a fill boundary, not a structure.
    ax.add_patch(PathPatch(_bezier(top, (0.85, cy), bot), fc="none",
                           ec=C["cornea"], lw=3.0, zorder=6))

    # ── Vitreous chamber (behind the lens) ────────────────────────────────────
    th = np.linspace(math.radians(-105), math.radians(105), 200)
    vx = cx + 2.5 * np.cos(th)
    vy = cy + 2.5 * np.sin(th)
    ax.fill(vx, vy, fc=C["vitreous"], ec="none", zorder=2)

    # ── The three coats: sclera → choroid → retina (outermost first) ──────────
    for r, clr, lw, t1, t2 in (
        (_R_SCLERA,  C["sclera"],  5.0, -150, 150),
        (_R_CHOROID, C["choroid"], 3.2, -140, 140),
        (_R_RETINA,  C["retina"],  3.0, -120, 120),   # retina stops at the ora serrata
    ):
        ax.add_patch(Arc((cx, cy), 2 * r, 2 * r, theta1=t1, theta2=t2,
                         color=clr, lw=lw, zorder=4))

    # ── Iris, pupil, lens, ciliary body ───────────────────────────────────────
    for side in (1, -1):
        ax.plot([3.70, 3.56], [cy + side * 2.05, cy + side * 0.75],
                color=C["iris"], lw=6, solid_capstyle="round", zorder=7)
        ax.plot([3.74, 4.00], [cy + side * 2.15, cy + side * 1.32],
                color=C["ciliary"], lw=6, solid_capstyle="round", zorder=6)
        for k in np.linspace(-0.12, 0.12, 3):     # suspensory ligaments
            ax.plot([3.95, 4.05], [cy + side * (1.35 + k), cy + side * (1.28 + k)],
                    color="#a1887f", lw=0.8, zorder=6)
    ax.add_patch(Ellipse((3.95, cy), 0.95, 2.7, fc=C["lens_body"],
                         ec="#0277bd", lw=1.8, zorder=5))

    # ── Fovea, blind spot, optic nerve ────────────────────────────────────────
    ax.add_patch(Circle((cx + _R_RETINA, cy), 0.16, fc=C["fovea"],
                        ec="#f57f17", lw=1.0, zorder=8))
    nerve_ang = math.radians(-18)
    bs = (cx + _R_RETINA * math.cos(nerve_ang), cy + _R_RETINA * math.sin(nerve_ang))
    ax.add_patch(Circle(bs, 0.15, fc=C["blind_spot"], ec="#212121",
                        lw=1.0, zorder=8))
    # The nerve leaves the eyeball at the blind spot, so its base sits on the
    # sclera and it runs outwards along that same radius.
    p1 = _polar(cx, cy, 3.05, -6)
    p2 = _polar(cx, cy, 3.05, -32)
    ux, uy = math.cos(nerve_ang), math.sin(nerve_ang)
    ax.add_patch(Polygon([p1, p2,
                          (p2[0] + ux * 3.0, p2[1] + uy * 3.0),
                          (p1[0] + ux * 3.0, p1[1] + uy * 3.0)],
                         closed=True, fc=C["optic_nerve"], ec="#f9a825",
                         lw=1.5, zorder=3))

    # ── Light rays ────────────────────────────────────────────────────────────
    focus_x = _EYE_FOCUS[schema.defect]
    if schema.show_light_rays:
        for y0 in (5.62, 5.0, 4.38):
            ax.plot([-2.3, 3.95], [y0, y0], color=C["light_ray"], lw=1.4, zorder=9)
            hit = _retina_hit((3.95, y0), (focus_x, cy))
            ax.plot([3.95, hit[0]], [y0, hit[1]], color=C["light_ray"],
                    lw=1.4, zorder=9)
            if focus_x > hit[0]:
                # Hypermetropia — the rays are still converging at the retina, so
                # the focus lies behind it. Show that leg as a virtual (dashed) ray.
                ax.plot([hit[0], focus_x], [hit[1], cy], color=C["light_ray"],
                        lw=1.0, ls="--", alpha=0.8, zorder=9)
        ax.plot(focus_x, cy, "o", color="#d84315", markersize=7, zorder=10)
        ax.annotate("", xy=(-1.3, 6.5), xytext=(-2.3, 6.5),
                    arrowprops=dict(arrowstyle="-|>", color=C["light_ray"], lw=1.6))
        ax.text(-1.8, 6.9, "Parallel\nlight rays", ha="center", fontsize=8.5,
                color=C["light_ray"])
        if schema.defect != "none":
            ax.annotate("Focus", xy=(focus_x, cy), xytext=(focus_x + 0.1, 6.9),
                        fontsize=8.5, color="#d84315", ha="center",
                        arrowprops=dict(arrowstyle="-|>", color="#d84315", lw=1.0))

    # ── Labels ────────────────────────────────────────────────────────────────
    if schema.show_labels:
        _annotate(ax, "Sclera", (4.15, 7.87), (2.6, 9.5), C["sclera"],
                  fontsize=9, highlight=_is_hl(hl, "sclera"))
        _annotate(ax, "Choroid", (5.55, 7.71), (5.2, 9.5), C["choroid"],
                  fontsize=9, highlight=_is_hl(hl, "choroid"))
        _annotate(ax, "Retina", (6.66, 6.99), (7.9, 9.5), C["retina"],
                  fontsize=9, highlight=_is_hl(hl, "retina"))
        _annotate(ax, "Cornea", (1.70, 5.75), (-1.6, 8.3), C["cornea"],
                  fontsize=9, highlight=_is_hl(hl, "cornea"))
        _annotate(ax, "Aqueous humour", (2.75, 6.15), (0.4, 9.3), "#0288d1",
                  fontsize=9, highlight=_is_hl(hl, "aqueous_humour", "aqueous"))
        _annotate(ax, "Iris", (3.62, 3.35), (1.2, 1.4), C["iris"],
                  fontsize=9, highlight=_is_hl(hl, "iris"))
        _annotate(ax, "Pupil", (3.58, 4.32), (3.1, 0.5), "#212121",
                  fontsize=9, highlight=_is_hl(hl, "pupil"))
        _annotate(ax, "Lens", (3.95, 3.85), (5.0, 1.2), "#0277bd",
                  fontsize=9, highlight=_is_hl(hl, "lens"))
        _annotate(ax, "Ciliary body", (3.85, 2.78), (6.9, 0.5), C["ciliary"],
                  fontsize=9, highlight=_is_hl(hl, "ciliary_body", "ciliary"))
        _annotate(ax, "Vitreous humour", (6.0, 3.6), (9.2, 1.3), "#00695c",
                  fontsize=9, highlight=_is_hl(hl, "vitreous_humour", "vitreous"))
        _annotate(ax, "Fovea centralis\n(Yellow spot)", (7.62, 5.05),
                  (11.4, 6.9), "#ef6c00", fontsize=9,
                  highlight=_is_hl(hl, "fovea", "yellow_spot", "fovea_centralis"))
        _annotate(ax, "Blind spot\n(Optic disc)", bs, (11.6, 4.9),
                  C["blind_spot"], fontsize=9,
                  highlight=_is_hl(hl, "blind_spot", "optic_disc"))
        _annotate(ax, "Optic nerve", (9.6, 3.4), (12.0, 2.4), "#f9a825",
                  fontsize=9, highlight=_is_hl(hl, "optic_nerve"))

    ax.text(5.2, -0.65, _EYE_DEFECT_NOTE[schema.defect], ha="center",
            va="center", fontsize=9, color="#37474f", style="italic",
            bbox=dict(boxstyle="round,pad=0.35", fc="#fffde7", ec="#bdbdbd", lw=0.8))

    defect_name = {"none": "Normal Eye", "myopia": "Myopia",
                   "hypermetropia": "Hypermetropia"}[schema.defect]
    ax.set_title(schema.title or f"Human Eye — Horizontal Section ({defect_name})",
                 fontsize=14, fontweight="bold", pad=6)
    fig.tight_layout(pad=0.4)
    return _fig_to_svg(fig)


# ═══════════════════════════════════════════════════════════════════════════════
# 14. Digestive System
# ═══════════════════════════════════════════════════════════════════════════════

def render_digestive_system(data: Dict[str, Any],
                            canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = DigestiveSystemSchema(**data)
    hl = _norm(schema.highlight_organ)

    fig, ax = plt.subplots(figsize=(11, 12))
    ax.set_xlim(-3.4, 13.4); ax.set_ylim(-0.3, 12.9)
    ax.set_aspect("equal"); ax.axis("off")

    # Anterior view: the viewer's LEFT is the body's RIGHT, so the liver, caecum
    # and appendix sit on the left of the drawing and the stomach on the right.

    # ── Mouth (buccal cavity) ─────────────────────────────────────────────────
    ax.add_patch(Ellipse((5.0, 11.9), 1.9, 1.0, fc="#ffccbc",
                         ec=C["gut_tube"], lw=1.8, zorder=3))
    ax.plot([4.2, 5.8], [11.9, 11.9], color=C["gut_tube"], lw=1.2, zorder=4)

    # ── Oesophagus ────────────────────────────────────────────────────────────
    oes = _bezier((5.0, 11.4), (5.1, 10.4), (5.7, 9.35))
    ax.add_patch(PathPatch(oes, fc="none", ec=C["gut_tube"], lw=7,
                           capstyle="round", zorder=3))

    # ── Stomach (J-shaped, viewer's right) ────────────────────────────────────
    ax.add_patch(Ellipse((6.9, 8.5), 2.9, 2.2, angle=-22, fc=C["stomach"],
                         ec="#b71c1c", lw=1.8, zorder=4))
    pyl = _bezier((5.85, 7.55), (5.5, 7.1), (5.05, 7.15))
    ax.add_patch(PathPatch(pyl, fc="none", ec=C["stomach"], lw=6,
                           capstyle="round", zorder=4))

    # ── Liver + gall bladder (viewer's left) ──────────────────────────────────
    ax.add_patch(Polygon([(1.3, 9.1), (2.2, 10.2), (4.7, 10.1), (4.9, 8.7),
                          (3.0, 8.1), (1.4, 8.5)],
                         closed=True, fc=C["liver"], ec="#4e342e",
                         lw=1.8, zorder=4))
    ax.add_patch(Ellipse((3.9, 8.0), 0.75, 1.0, angle=-20,
                         fc=C["gall_bladder"], ec="#1b5e20", lw=1.5, zorder=5))
    ax.plot([4.15, 4.85], [7.5, 7.1], color="#2e7d32", lw=1.4, zorder=5)  # bile duct

    # ── Duodenum (C-loop) + pancreas ──────────────────────────────────────────
    th = np.linspace(math.radians(70), math.radians(290), 120)
    dx = 4.85 + 0.95 * np.cos(th)
    dy = 7.0 + 0.95 * np.sin(th)
    ax.plot(dx, dy, color=C["small_intestine"], lw=6,
            solid_capstyle="round", zorder=4)
    ax.add_patch(Ellipse((6.5, 6.85), 2.6, 0.85, angle=8, fc=C["pancreas"],
                         ec="#e65100", lw=1.5, zorder=3))

    # ── Small intestine (jejunum + ileum coils) ───────────────────────────────
    sx, sy = _coil(5.0, 1.7, 5.75, 2.7, 7)
    ax.plot(sx, sy, color=C["small_intestine"], lw=6, solid_capstyle="round",
            solid_joinstyle="round", zorder=4)
    ax.plot([4.85, 5.0], [6.05, 5.75], color=C["small_intestine"], lw=6,
            solid_capstyle="round", zorder=4)

    # ── Large intestine: caecum → ascending → transverse → descending → rectum ─
    li = C["large_intestine"]
    ax.plot([2.3, 2.3], [2.3, 6.1], color=li, lw=9,
            solid_capstyle="round", zorder=3)                       # ascending
    ax.plot([2.3, 7.8], [6.1, 6.1], color=li, lw=9,
            solid_capstyle="round", zorder=3)                       # transverse
    ax.plot([7.8, 7.8], [6.1, 2.6], color=li, lw=9,
            solid_capstyle="round", zorder=3)                       # descending
    sig = _bezier((7.8, 2.6), (7.4, 1.3), (5.35, 1.55))             # sigmoid colon
    ax.add_patch(PathPatch(sig, fc="none", ec=li, lw=8,
                           capstyle="round", zorder=3))
    ax.add_patch(Ellipse((2.3, 2.1), 1.4, 1.3, fc=li, ec="#4527a0",
                         lw=1.6, zorder=4))                          # caecum
    app = _bezier((2.0, 1.5), (1.5, 0.9), (1.9, 0.45))               # appendix
    ax.add_patch(PathPatch(app, fc="none", ec=C["appendix"], lw=3.5,
                           capstyle="round", zorder=5))
    ax.plot([5.35, 5.35], [1.55, 0.75], color=li, lw=8,
            solid_capstyle="round", zorder=3)                        # rectum
    ax.add_patch(Circle((5.35, 0.4), 0.24, fc="#4527a0", ec="#311b92",
                        lw=1.5, zorder=5))                           # anus

    # ── Labels ────────────────────────────────────────────────────────────────
    if schema.show_labels:
        _annotate(ax, "Mouth\n(Buccal cavity)", (5.0, 12.3), (1.6, 12.4),
                  C["gut_tube"], fontsize=9, highlight=_is_hl(hl, "mouth"))
        _annotate(ax, "Oesophagus", (5.35, 10.4), (9.6, 11.9), C["gut_tube"],
                  fontsize=9, highlight=_is_hl(hl, "oesophagus", "esophagus"))
        _annotate(ax, "Stomach", (7.4, 8.9), (11.1, 10.1), C["stomach"],
                  fontsize=9, highlight=_is_hl(hl, "stomach"))
        _annotate(ax, "Liver", (2.6, 9.4), (-2.0, 11.2), C["liver"],
                  fontsize=9, highlight=_is_hl(hl, "liver"))
        _annotate(ax, "Gall bladder", (3.8, 8.1), (-2.1, 9.4),
                  C["gall_bladder"], fontsize=9,
                  highlight=_is_hl(hl, "gall_bladder", "gallbladder"))
        _annotate(ax, "Duodenum", (4.0, 7.0), (-2.1, 7.4), C["small_intestine"],
                  fontsize=9, highlight=_is_hl(hl, "duodenum"))
        _annotate(ax, "Pancreas", (7.0, 6.9), (11.3, 8.2), C["pancreas"],
                  fontsize=9, highlight=_is_hl(hl, "pancreas"))
        _annotate(ax, "Jejunum", (6.4, 5.1), (11.2, 5.3), C["small_intestine"],
                  fontsize=9, highlight=_is_hl(hl, "jejunum"))
        _annotate(ax, "Ileum", (6.1, 3.4), (11.2, 3.9), C["small_intestine"],
                  fontsize=9, highlight=_is_hl(hl, "ileum"))
        _annotate(ax, "Small intestine", (4.2, 4.4), (-2.2, 5.4),
                  C["small_intestine"], fontsize=9,
                  highlight=_is_hl(hl, "small_intestine"))
        _annotate(ax, "Transverse colon", (6.6, 6.15), (11.0, 6.7), li,
                  fontsize=9, highlight=_is_hl(hl, "colon", "transverse_colon"))
        _annotate(ax, "Ascending colon", (2.3, 4.4), (-2.2, 3.6), li,
                  fontsize=9,
                  highlight=_is_hl(hl, "ascending_colon", "large_intestine"))
        _annotate(ax, "Descending colon", (7.8, 3.7), (11.1, 2.5), li,
                  fontsize=9, highlight=_is_hl(hl, "descending_colon"))
        _annotate(ax, "Caecum", (2.4, 2.1), (-2.0, 2.0), li,
                  fontsize=9, highlight=_is_hl(hl, "caecum", "cecum"))
        _annotate(ax, "Vermiform\nappendix", (1.7, 0.75), (-1.9, 0.5),
                  C["appendix"], fontsize=9, highlight=_is_hl(hl, "appendix"))
        _annotate(ax, "Rectum", (5.55, 1.1), (9.2, 1.2), li,
                  fontsize=9, highlight=_is_hl(hl, "rectum"))
        _annotate(ax, "Anus", (5.45, 0.4), (7.6, 0.2), "#311b92",
                  fontsize=9, highlight=_is_hl(hl, "anus"))

    ax.set_title(schema.title or "Human Digestive System (Alimentary Canal)",
                 fontsize=14, fontweight="bold", pad=6)
    fig.tight_layout(pad=0.4)
    return _fig_to_svg(fig)


# ═══════════════════════════════════════════════════════════════════════════════
# 15. Respiratory System
# ═══════════════════════════════════════════════════════════════════════════════

def render_respiratory_system(data: Dict[str, Any],
                              canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = RespiratorySystemSchema(**data)
    hl = _norm(schema.highlight_organ)
    inset = schema.show_alveoli_inset

    fig, ax = plt.subplots(figsize=(13 if inset else 10, 10))
    ax.set_xlim(-3.4, 17.8 if inset else 12.4)
    ax.set_ylim(-0.4, 13.2)
    ax.set_aspect("equal"); ax.axis("off")

    # ── Nasal cavity → pharynx → larynx ───────────────────────────────────────
    ax.add_patch(Polygon([(3.5, 11.9), (5.9, 12.2), (6.0, 11.2), (4.0, 11.0)],
                         closed=True, fc="#ffe0b2", ec=C["airway"],
                         lw=1.6, zorder=3))
    ax.add_patch(Ellipse((5.6, 10.6), 1.0, 1.3, fc="#ffcc80",
                         ec=C["airway"], lw=1.6, zorder=3))
    ax.add_patch(FancyBboxPatch((5.15, 9.25), 0.9, 0.85,
                                boxstyle="round,pad=0.06", fc="#b0bec5",
                                ec=C["airway"], lw=1.8, zorder=4))

    # ── Trachea with C-shaped cartilage rings ─────────────────────────────────
    ax.add_patch(FancyBboxPatch((5.2, 7.1), 0.8, 2.2,
                                boxstyle="round,pad=0.04", fc="#cfd8dc",
                                ec=C["airway"], lw=1.8, zorder=3))
    for ty in np.arange(7.35, 9.2, 0.32):
        ax.plot([5.25, 5.95], [ty, ty], color=C["airway"], lw=1.6, zorder=4)

    # ── Bronchi → bronchioles ─────────────────────────────────────────────────
    for side in (-1, 1):
        br = _bezier((5.6 + side * 0.25, 7.15),
                     (5.6 + side * 1.1, 6.9),
                     (5.6 + side * 2.1, 6.15))
        ax.add_patch(PathPatch(br, fc="none", ec=C["airway"], lw=5,
                               capstyle="round", zorder=5))
        # Bronchioles: two generations of branching inside each lung.
        for k, (dx2, dy2) in enumerate(((1.0, -1.2), (1.7, -0.4), (0.4, -1.9))):
            tip = (5.6 + side * (2.1 + dx2), 6.15 + dy2)
            ax.plot([5.6 + side * 2.1, tip[0]], [6.15, tip[1]],
                    color=C["airway"], lw=2.4, zorder=5)
            for dx3, dy3 in ((-0.35, -0.5), (0.35, -0.5)):
                end = (tip[0] + side * dx3, tip[1] + dy3)
                ax.plot([tip[0], end[0]], [tip[1], end[1]],
                        color=C["airway"], lw=1.3, zorder=5)
                # Alveolar sac — a grape-like cluster at each bronchiole tip.
                for ax_, ay_ in ((-0.16, -0.16), (0.16, -0.16), (0.0, -0.3)):
                    ax.add_patch(Circle((end[0] + ax_, end[1] + ay_), 0.13,
                                        fc=C["alveolus"], ec="#ad1457",
                                        lw=0.8, zorder=6))

    # ── Lungs (right = 3 lobes on the viewer's left; left = 2 lobes) ──────────
    for side, w in ((-1, 3.5), (1, 3.1)):
        lung = Ellipse((5.6 + side * 2.45, 5.9), w, 6.0,
                       fc=C["lung"], ec=C["lung_edge"], lw=2.0,
                       alpha=0.55, zorder=2)
        ax.add_patch(lung)
        ax.add_patch(Ellipse((5.6 + side * 2.45, 5.9), w + 0.35, 6.35,
                             fc="none", ec=C["pleura"], lw=1.2,
                             ls="--", zorder=2))                    # pleura
    # Fissures: the right lung has two (3 lobes), the left one (2 lobes).
    ax.plot([1.7, 4.6], [6.6, 5.4], color=C["lung_edge"], lw=1.2,
            alpha=0.7, zorder=3)
    ax.plot([1.9, 4.5], [4.4, 3.7], color=C["lung_edge"], lw=1.2,
            alpha=0.7, zorder=3)
    ax.plot([6.7, 9.4], [4.9, 6.3], color=C["lung_edge"], lw=1.2,
            alpha=0.7, zorder=3)

    # ── Diaphragm (dome-shaped, convex upwards) ───────────────────────────────
    dxs = np.linspace(1.0, 10.2, 200)
    dys = 2.35 + 0.95 * np.sin(np.pi * (dxs - 1.0) / 9.2)
    ax.plot(dxs, dys, color=C["diaphragm"], lw=5, solid_capstyle="round",
            zorder=6)
    ax.fill_between(dxs, dys - 0.35, dys, color=C["diaphragm"],
                    alpha=0.35, zorder=5)

    # ── Labels ────────────────────────────────────────────────────────────────
    if schema.show_labels:
        _annotate(ax, "Nasal cavity", (4.5, 11.7), (0.6, 12.1), "#ef6c00",
                  fontsize=9, highlight=_is_hl(hl, "nasal_cavity", "nose"))
        _annotate(ax, "Pharynx", (5.75, 10.7), (8.9, 11.9), "#ef6c00",
                  fontsize=9, highlight=_is_hl(hl, "pharynx"))
        _annotate(ax, "Larynx\n(Voice box)", (5.9, 9.65), (9.2, 10.1),
                  C["airway"], fontsize=9, highlight=_is_hl(hl, "larynx"))
        _annotate(ax, "Trachea\n(with cartilage rings)", (5.35, 8.4),
                  (0.5, 9.8), C["airway"], fontsize=9,
                  highlight=_is_hl(hl, "trachea"))
        _annotate(ax, "Bronchus", (6.9, 6.6), (10.3, 8.3), C["airway"],
                  fontsize=9, highlight=_is_hl(hl, "bronchi", "bronchus"))
        _annotate(ax, "Bronchiole", (8.6, 5.4), (11.4, 6.2), C["airway"],
                  fontsize=9, highlight=_is_hl(hl, "bronchioles", "bronchiole"))
        _annotate(ax, "Alveoli", (9.1, 4.3), (11.1, 2.6), "#ad1457",
                  fontsize=9, highlight=_is_hl(hl, "alveoli", "alveolus"))
        _annotate(ax, "Right lung\n(3 lobes)", (2.2, 7.6), (-2.2, 9.3),
                  C["lung_edge"], fontsize=9,
                  highlight=_is_hl(hl, "lungs", "right_lung"))
        _annotate(ax, "Left lung\n(2 lobes)", (8.6, 7.9), (11.4, 9.2),
                  C["lung_edge"], fontsize=9,
                  highlight=_is_hl(hl, "lungs", "left_lung"))
        _annotate(ax, "Pleura\n(pleural membranes)", (2.0, 3.6), (-2.2, 5.6),
                  C["pleura"], fontsize=9, highlight=_is_hl(hl, "pleura"))
        _annotate(ax, "Diaphragm", (5.6, 3.3), (-1.8, 1.9), C["diaphragm"],
                  fontsize=9, highlight=_is_hl(hl, "diaphragm"))

    # ── Magnified alveolus + gas exchange ─────────────────────────────────────
    if inset:
        ix, iy = 14.0, 6.4
        ax.plot([10.2, 12.0], [4.4, 5.6], color="#9e9e9e", lw=1.0,
                ls="--", zorder=2)
        ax.add_patch(Circle((ix, iy), 1.55, fc=C["alveolus"], ec="#ad1457",
                            lw=2.0, zorder=4))
        ax.add_patch(Circle((ix, iy), 1.2, fc="#fce4ec", ec="#ad1457",
                            lw=0.8, ls="--", zorder=5))
        # Capillary wrapping the alveolus: deoxygenated in, oxygenated out.
        cap_t = np.linspace(math.radians(200), math.radians(-20), 120)
        ax.plot(ix + 1.95 * np.cos(cap_t), iy + 1.95 * np.sin(cap_t),
                color=C["capillary_co2"], lw=4, zorder=3)
        cap_t2 = np.linspace(math.radians(200), math.radians(340), 120)
        ax.plot(ix + 1.95 * np.cos(cap_t2), iy + 1.95 * np.sin(cap_t2),
                color=C["capillary_o2"], lw=4, zorder=3)
        ax.annotate("", xy=(ix - 0.7, iy - 1.0), xytext=(ix - 1.5, iy - 0.2),
                    arrowprops=dict(arrowstyle="-|>", color=C["capillary_o2"],
                                    lw=2.0), zorder=7)
        ax.text(ix - 1.45, iy - 2.1, "O₂ → blood", ha="center", fontsize=9,
                color=C["capillary_o2"], fontweight="bold")
        ax.annotate("", xy=(ix + 1.5, iy - 0.2), xytext=(ix + 0.7, iy - 1.0),
                    arrowprops=dict(arrowstyle="-|>", color=C["capillary_co2"],
                                    lw=2.0), zorder=7)
        ax.text(ix + 1.55, iy - 2.1, "CO₂ → alveolus", ha="center", fontsize=9,
                color=C["capillary_co2"], fontweight="bold")
        ax.text(ix, iy + 0.1, "Alveolus", ha="center", va="center",
                fontsize=9.5, fontweight="bold", color="#880e4f", zorder=6)
        ax.text(ix, iy + 3.35, "Alveolus (magnified)", ha="center",
                fontsize=10, fontweight="bold", color="#880e4f")
        ax.text(ix, iy + 3.0, "gas exchange across the alveolar wall +\n"
                              "capillary endothelium (diffusion)",
                ha="center", va="top", fontsize=8, color="#555555",
                style="italic")
        ax.text(ix, iy - 2.85, "Pulmonary capillary", ha="center", fontsize=9,
                color="#4a148c")

    ax.set_title(schema.title or "Human Respiratory System",
                 fontsize=14, fontweight="bold", pad=6)
    fig.tight_layout(pad=0.4)
    return _fig_to_svg(fig)


# ═══════════════════════════════════════════════════════════════════════════════
# 16. Plant Tissue (T.S.)
# ═══════════════════════════════════════════════════════════════════════════════

# The vascular arrangement IS the answer to these questions, so it is declared
# once here and both the drawing and the caption are derived from it.
_TISSUE_LAYOUT: Dict[str, Dict[str, Any]] = {
    "dicot_stem": {
        "arrangement": "ring", "n_bundles": 8, "n_xylem_arms": 0,
        "cambium": True, "pith": True,
        "caption": "Vascular bundles conjoint, collateral and OPEN "
                   "(cambium present) — arranged in a RING",
    },
    "monocot_stem": {
        "arrangement": "scattered", "n_bundles": 9, "n_xylem_arms": 0,
        "cambium": False, "pith": False,
        "caption": "Vascular bundles conjoint, collateral and CLOSED "
                   "(no cambium) — SCATTERED in the ground tissue",
    },
    "dicot_root": {
        "arrangement": "radial", "n_bundles": 0, "n_xylem_arms": 4,
        "cambium": False, "pith": False,
        "caption": "Xylem exarch and TETRARCH (2–4 arms); phloem alternates "
                   "with xylem — RADIAL arrangement, pith small or absent",
    },
    "monocot_root": {
        "arrangement": "radial", "n_bundles": 0, "n_xylem_arms": 8,
        "cambium": False, "pith": True,
        "caption": "Xylem exarch and POLYARCH (more than six arms); phloem "
                   "alternates with xylem — RADIAL arrangement, large pith",
    },
    "leaf": {
        "arrangement": "dorsiventral", "n_bundles": 1, "n_xylem_arms": 0,
        "cambium": False, "pith": False,
        "caption": "Dorsiventral leaf — xylem lies towards the UPPER (adaxial) "
                   "side and phloem towards the LOWER (abaxial) side",
    },
}


def _polar(cx, cy, r, deg):
    a = math.radians(deg)
    return cx + r * math.cos(a), cy + r * math.sin(a)


def render_plant_tissue(data: Dict[str, Any],
                        canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = PlantTissueSchema(**data)
    hl = _norm(schema.highlight_tissue)
    layout = _TISSUE_LAYOUT[schema.section_type]

    if schema.section_type == "leaf":
        fig, ax = plt.subplots(figsize=(12, 7))
        ax.set_xlim(-3.2, 13.4); ax.set_ylim(-1.6, 7.0)
        _draw_leaf_ts(ax, schema, hl)
    else:
        fig, ax = plt.subplots(figsize=(11, 9))
        ax.set_xlim(-6.6, 11.4); ax.set_ylim(-6.6, 6.4)
        if schema.section_type.endswith("_stem"):
            _draw_stem_ts(ax, schema, hl, layout)
        else:
            _draw_root_ts(ax, schema, hl, layout)
    ax.set_aspect("equal"); ax.axis("off")

    name = schema.section_type.replace("_", " ").title()
    ax.set_title(schema.title or f"T.S. of {name}",
                 fontsize=14, fontweight="bold", pad=6)
    fig.text(0.5, 0.015, layout["caption"], ha="center", fontsize=9.5,
             color="#37474f", style="italic")
    fig.tight_layout(pad=0.4, rect=(0, 0.035, 1, 1))
    return _fig_to_svg(fig)


def _draw_stem_ts(ax, schema, hl, layout):
    dicot = schema.section_type == "dicot_stem"
    R = 4.6

    ax.add_patch(Circle((0, 0), R, fc="#eceff1", ec=C["epidermis"],
                        lw=3.0, zorder=2))                       # epidermis
    ax.add_patch(Circle((0, 0), R - 0.28,
                        fc="#aed581" if dicot else "#bcaaa4",
                        ec="none", zorder=3))                    # hypodermis
    ax.add_patch(Circle((0, 0), R - 0.62,
                        fc=C["cortex"] if dicot else C["ground_tissue"],
                        ec="none", zorder=4))

    if dicot:
        ax.add_patch(Circle((0, 0), 3.35, fc="none", ec=C["endodermis"],
                            lw=2.2, ls="--", zorder=5))          # endodermis
        ax.add_patch(Circle((0, 0), 3.15, fc="none", ec=C["pericycle"],
                            lw=1.6, zorder=5))                   # pericycle
        ax.add_patch(Circle((0, 0), 3.02, fc=C["pith"], ec="none", zorder=5))

        for i in range(layout["n_bundles"]):
            deg = 90 - i * (360 / layout["n_bundles"])
            px, py = _polar(0, 0, 2.55, deg)
            cbx, cby = _polar(0, 0, 2.18, deg)
            xx, xy_ = _polar(0, 0, 1.78, deg)
            ax.add_patch(Ellipse((px, py), 1.05, 0.55, angle=deg + 90,
                                 fc=C["phloem"], ec="#0d47a1", lw=1.0, zorder=6))
            ax.add_patch(Ellipse((cbx, cby), 1.0, 0.18, angle=deg + 90,
                                 fc=C["cambium"], ec="#004d40", lw=0.8, zorder=7))
            ax.add_patch(Ellipse((xx, xy_), 1.0, 0.7, angle=deg + 90,
                                 fc=C["xylem"], ec="#8e0000", lw=1.0, zorder=6))
        first = _polar(0, 0, 2.55, 90)
    else:
        # Scattered closed bundles — a fixed (deterministic) sprinkle, denser
        # towards the periphery, exactly as in a monocot stem.
        spots = [(1.15, 60), (1.3, 190), (1.25, 305),
                 (2.6, 20), (2.55, 95), (2.7, 150),
                 (2.6, 225), (2.65, 275), (2.7, 335)]
        for r, deg in spots:
            bx, by = _polar(0, 0, r, deg)
            ax.add_patch(Ellipse((bx, by), 1.15, 1.0, angle=deg + 90,
                                 fc="#f1f8e9", ec=C["bundle_sheath"],
                                 lw=1.6, zorder=6))
            phx, phy = _polar(bx, by, 0.3, deg)
            ax.add_patch(Ellipse((phx, phy), 0.55, 0.28, angle=deg + 90,
                                 fc=C["phloem"], ec="#0d47a1", lw=0.8, zorder=7))
            for s in (-1, 1):                                     # metaxylem
                mx, my = _polar(bx, by, 0.28, deg + s * 90)
                ax.add_patch(Circle((mx, my), 0.19, fc=C["xylem"],
                                    ec="#8e0000", lw=0.8, zorder=7))
            pxx, pxy = _polar(bx, by, 0.3, deg + 180)
            ax.add_patch(Circle((pxx, pxy), 0.13, fc=C["xylem"],
                                ec="#8e0000", lw=0.8, zorder=7))   # protoxylem
            cvx, cvy = _polar(bx, by, 0.45, deg + 180)
            ax.add_patch(Circle((cvx, cvy), 0.11, fc="white",
                                ec="#8e0000", lw=0.8, zorder=8))   # water cavity
        first = _polar(0, 0, 2.6, 20)

    if not schema.show_labels:
        return

    _annotate(ax, "Epidermis", (0, R), (-4.4, 5.6), C["epidermis"],
              fontsize=9, highlight=_is_hl(hl, "epidermis"))
    _annotate(ax, "Hypodermis", _polar(0, 0, R - 0.4, 140), (-6.0, 3.9),
              "#558b2f" if dicot else "#5d4037", fontsize=9,
              highlight=_is_hl(hl, "hypodermis"))
    if dicot:
        _annotate(ax, "Cortex", _polar(0, 0, 3.9, 165), (-6.0, 2.1),
                  "#689f38", fontsize=9, highlight=_is_hl(hl, "cortex"))
        _annotate(ax, "Endodermis", _polar(0, 0, 3.35, 200), (-6.1, 0.3),
                  C["endodermis"], fontsize=9,
                  highlight=_is_hl(hl, "endodermis"))
        _annotate(ax, "Pericycle", _polar(0, 0, 3.15, 215), (-6.1, -1.5),
                  C["pericycle"], fontsize=9,
                  highlight=_is_hl(hl, "pericycle"))
        _annotate(ax, "Pith", (0.0, -0.9), (-4.2, -5.6), "#f9a825",
                  fontsize=9, highlight=_is_hl(hl, "pith"))
        _annotate(ax, "Medullary ray", _polar(0, 0, 2.2, 67), (5.6, 5.4),
                  "#9e9e9e", fontsize=9, highlight=_is_hl(hl, "medullary_ray"))
        _annotate(ax, "Phloem", first, (8.4, 3.6), C["phloem"],
                  fontsize=9, highlight=_is_hl(hl, "phloem"))
        _annotate(ax, "Cambium", _polar(0, 0, 2.18, 90), (8.6, 1.8),
                  C["cambium"], fontsize=9, highlight=_is_hl(hl, "cambium"))
        _annotate(ax, "Xylem", _polar(0, 0, 1.78, 90), (8.4, 0.0), C["xylem"],
                  fontsize=9, highlight=_is_hl(hl, "xylem"))
    else:
        _annotate(ax, "Ground tissue\n(undifferentiated —\nno cortex/pith)",
                  _polar(0, 0, 3.9, 175), (-5.4, 0.4), "#7cb342", fontsize=9,
                  highlight=_is_hl(hl, "ground_tissue"))
        _annotate(ax, "Bundle sheath\n(sclerenchymatous)",
                  _polar(0, 0, 3.1, 22), (8.2, 4.4), C["bundle_sheath"],
                  fontsize=9, highlight=_is_hl(hl, "bundle_sheath"))
        _annotate(ax, "Phloem", _polar(*first, 0.3, 20), (8.6, 2.3),
                  C["phloem"], fontsize=9, highlight=_is_hl(hl, "phloem"))
        _annotate(ax, "Xylem\n(metaxylem + protoxylem)",
                  _polar(*_polar(0, 0, 2.65, 335), 0.28, 245), (8.0, 0.0),
                  C["xylem"], fontsize=9, highlight=_is_hl(hl, "xylem"))
        _annotate(ax, "Water cavity\n(lysigenous)",
                  _polar(*_polar(0, 0, 2.6, 95), 0.45, 275), (-4.6, -5.4),
                  "#0288d1", fontsize=9, highlight=_is_hl(hl, "water_cavity"))
        ax.text(6.6, -3.6, "No cambium →\nbundles are CLOSED", fontsize=9,
                color="#c62828", ha="center", style="italic")


def _draw_root_ts(ax, schema, hl, layout):
    arms = layout["n_xylem_arms"]
    monocot = schema.section_type == "monocot_root"
    R = 4.6
    stele_r = 2.35 if not monocot else 2.6

    ax.add_patch(Circle((0, 0), R, fc="#e0f2f1", ec=C["epidermis"],
                        lw=2.6, zorder=2))                        # epiblema
    for deg in range(0, 360, 18):                                  # root hairs
        x1, y1 = _polar(0, 0, R, deg)
        x2, y2 = _polar(0, 0, R + 0.55, deg)
        ax.plot([x1, x2], [y1, y2], color=C["epidermis"], lw=1.2, zorder=2)
    ax.add_patch(Circle((0, 0), R - 0.22, fc=C["cortex"], ec="none", zorder=3))
    ax.add_patch(Circle((0, 0), stele_r + 0.28, fc="none", ec=C["endodermis"],
                        lw=2.4, zorder=5))                        # endodermis
    for deg in range(0, 360, 15):                                  # casparian strips
        cxp, cyp = _polar(0, 0, stele_r + 0.28, deg)
        ax.plot([cxp], [cyp], marker="s", color="#3e2723", markersize=3, zorder=6)
    ax.add_patch(Circle((0, 0), stele_r + 0.1, fc="none", ec=C["pericycle"],
                        lw=1.8, zorder=5))                        # pericycle
    ax.add_patch(Circle((0, 0), stele_r, fc="#f1f8e9", ec="none", zorder=4))

    pith_r = 1.15 if monocot else 0.32
    ax.add_patch(Circle((0, 0), pith_r, fc=C["pith"], ec="#f9a825",
                        lw=1.2, zorder=8))

    # Xylem arms reach OUT to the pericycle (exarch: protoxylem outermost) and
    # the phloem patches alternate with them — this is the radial arrangement.
    step = 360 / arms
    for i in range(arms):
        deg = 90 + i * step
        ax.add_patch(Wedge((0, 0), stele_r - 0.05, deg - 7, deg + 7,
                           width=stele_r - pith_r - 0.05, fc=C["xylem"],
                           ec="#8e0000", lw=1.0, zorder=6))
        px, py = _polar(0, 0, stele_r - 0.28, deg)
        ax.add_patch(Circle((px, py), 0.14, fc="#ff8a80", ec="#8e0000",
                            lw=0.7, zorder=7))                    # protoxylem
        pdeg = deg + step / 2
        phx, phy = _polar(0, 0, stele_r - 0.75, pdeg)
        ax.add_patch(Ellipse((phx, phy), 0.72, 0.55, angle=pdeg + 90,
                             fc=C["phloem"], ec="#0d47a1", lw=1.0, zorder=6))

    if not schema.show_labels:
        return

    arm_word = "Polyarch" if monocot else "Tetrarch"
    _annotate(ax, "Epidermis\n(Epiblema) + root hairs", (0, R + 0.3),
              (-4.0, 5.6), C["epidermis"], fontsize=9,
              highlight=_is_hl(hl, "epidermis", "epiblema"))
    _annotate(ax, "Cortex", _polar(0, 0, 3.6, 160), (-6.1, 3.2), "#689f38",
              fontsize=9, highlight=_is_hl(hl, "cortex"))
    _annotate(ax, "Endodermis\n(Casparian strips)",
              _polar(0, 0, stele_r + 0.28, 195), (-6.0, 0.9), C["endodermis"],
              fontsize=9, highlight=_is_hl(hl, "endodermis"))
    _annotate(ax, "Pericycle", _polar(0, 0, stele_r + 0.1, 215), (-6.0, -1.4),
              C["pericycle"], fontsize=9, highlight=_is_hl(hl, "pericycle"))
    _annotate(ax, "Conjunctive tissue", _polar(0, 0, stele_r - 0.6, 240),
              (-4.4, -5.6), "#9e9e9e", fontsize=9,
              highlight=_is_hl(hl, "conjunctive_tissue"))
    _annotate(ax, f"Xylem — {arm_word}\n({arms} radial arms, exarch)",
              _polar(0, 0, stele_r - 0.7, 90), (7.6, 4.4), C["xylem"],
              fontsize=9, highlight=_is_hl(hl, "xylem"))
    _annotate(ax, "Phloem\n(alternates with xylem)",
              _polar(0, 0, stele_r - 0.75, 90 + step / 2), (8.4, 1.6),
              C["phloem"], fontsize=9, highlight=_is_hl(hl, "phloem"))
    _annotate(ax, "Pith" + (" (large)" if monocot else " (small/absent)"),
              (pith_r * 0.4, -pith_r * 0.4), (7.6, -1.6), "#f9a825",
              fontsize=9, highlight=_is_hl(hl, "pith"))
    ax.text(6.4, -4.4, "No cambium →\nvascular tissue is\nradial, not conjoint",
            fontsize=9, color="#c62828", ha="center", style="italic")


def _draw_leaf_ts(ax, schema, hl):
    x0, x1 = 0.0, 10.0

    ax.plot([x0, x1], [5.35, 5.35], color="#455a64", lw=2.6, zorder=6)  # cuticle
    ax.add_patch(Rectangle((x0, 4.7), x1 - x0, 0.6, fc="#e0f7fa",
                           ec=C["epidermis"], lw=1.4, zorder=4))
    for xi in np.arange(x0, x1 + 0.01, 1.0):
        ax.plot([xi, xi], [4.7, 5.3], color=C["epidermis"], lw=0.8, zorder=5)

    # Palisade parenchyma: columnar cells, tightly packed, just below the upper
    # epidermis — the main photosynthetic tissue of a dorsiventral leaf.
    for xi in np.arange(x0 + 0.15, x1 - 0.1, 0.62):
        ax.add_patch(FancyBboxPatch((xi, 3.25), 0.5, 1.35,
                                    boxstyle="round,pad=0.02",
                                    fc=C["palisade"], ec="#1b5e20",
                                    lw=1.0, alpha=0.85, zorder=4))

    # Spongy parenchyma: loosely packed with large intercellular air spaces.
    spongy = [(0.6, 2.7), (1.5, 2.35), (2.4, 2.75), (3.3, 2.3),
              (6.7, 2.75), (7.6, 2.3), (8.5, 2.7), (9.4, 2.35),
              (1.0, 1.75), (2.0, 1.55), (3.0, 1.8),
              (7.2, 1.6), (8.2, 1.8), (9.2, 1.6)]
    for sx, sy in spongy:
        ax.add_patch(Circle((sx, sy), 0.42, fc=C["spongy"], ec="#2e7d32",
                            lw=1.0, zorder=4))

    # Vascular bundle of the vein: xylem ABOVE, phloem BELOW.
    ax.add_patch(Ellipse((5.0, 2.3), 2.6, 2.0, fc="#f1f8e9",
                         ec=C["bundle_sheath"], lw=1.8, zorder=4))
    ax.add_patch(Ellipse((5.0, 2.75), 1.7, 0.75, fc=C["xylem"],
                         ec="#8e0000", lw=1.2, zorder=5))
    ax.add_patch(Ellipse((5.0, 1.8), 1.7, 0.7, fc=C["phloem"],
                         ec="#0d47a1", lw=1.2, zorder=5))

    ax.add_patch(Rectangle((x0, 0.6), x1 - x0, 0.6, fc="#e0f7fa",
                           ec=C["epidermis"], lw=1.4, zorder=4))
    for xi in np.arange(x0, x1 + 0.01, 1.0):
        ax.plot([xi, xi], [0.6, 1.2], color=C["epidermis"], lw=0.8, zorder=5)
    ax.plot([x0, x1], [0.5, 0.5], color="#455a64", lw=2.6, zorder=6)

    # Stoma with its two guard cells + the sub-stomatal air chamber.
    ax.add_patch(Rectangle((7.75, 0.6), 0.5, 0.6, fc="white", ec="none", zorder=5))
    for s in (-1, 1):
        ax.add_patch(Ellipse((8.0 + s * 0.42, 0.9), 0.55, 0.62,
                             fc=C["stoma"], ec="#004d40", lw=1.2, zorder=6))
    ax.add_patch(Ellipse((8.0, 1.55), 1.1, 0.75, fc="white",
                         ec="#90a4ae", lw=1.0, ls="--", zorder=3))

    if not schema.show_labels:
        return

    _annotate(ax, "Cuticle", (2.0, 5.35), (-1.8, 6.5), "#455a64", fontsize=9,
              highlight=_is_hl(hl, "cuticle"))
    _annotate(ax, "Upper epidermis", (4.0, 5.0), (2.6, 6.6), C["epidermis"],
              fontsize=9, highlight=_is_hl(hl, "upper_epidermis", "epidermis"))
    _annotate(ax, "Palisade parenchyma", (1.6, 3.9), (7.2, 6.5), C["palisade"],
              fontsize=9, highlight=_is_hl(hl, "palisade", "palisade_parenchyma"))
    _annotate(ax, "Spongy parenchyma", (2.4, 2.75), (-2.0, 4.2), "#2e7d32",
              fontsize=9, highlight=_is_hl(hl, "spongy", "spongy_parenchyma"))
    _annotate(ax, "Air space", (2.65, 2.1), (-2.0, 2.6), "#90a4ae",
              fontsize=9, highlight=_is_hl(hl, "air_space"))
    _annotate(ax, "Xylem (upper side)", (5.0, 2.85), (12.0, 4.9), C["xylem"],
              fontsize=9, highlight=_is_hl(hl, "xylem"))
    _annotate(ax, "Phloem (lower side)", (5.0, 1.75), (12.2, 3.3), C["phloem"],
              fontsize=9, highlight=_is_hl(hl, "phloem"))
    _annotate(ax, "Bundle sheath", (6.2, 2.9), (12.2, 1.7), C["bundle_sheath"],
              fontsize=9, highlight=_is_hl(hl, "bundle_sheath"))
    _annotate(ax, "Lower epidermis", (3.5, 0.9), (-1.9, 0.2), C["epidermis"],
              fontsize=9, highlight=_is_hl(hl, "lower_epidermis", "epidermis"))
    _annotate(ax, "Stoma + guard cells", (8.0, 0.75), (8.4, -1.1), C["stoma"],
              fontsize=9, highlight=_is_hl(hl, "stoma", "guard_cells"))
    _annotate(ax, "Sub-stomatal chamber", (8.0, 1.6), (3.4, -1.1), "#607d8b",
              fontsize=9, highlight=_is_hl(hl, "sub_stomatal_chamber"))


# ═══════════════════════════════════════════════════════════════════════════════
# 17. Organelle Detail
# ═══════════════════════════════════════════════════════════════════════════════

def render_organelle_detail(data: Dict[str, Any],
                            canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = OrganelleDetailSchema(**data)
    hl = _norm(schema.highlight_part)

    fig, ax = plt.subplots(figsize=(12, 8))
    ax.set_xlim(-3.4, 13.4); ax.set_ylim(-0.4, 10.4)
    ax.set_aspect("equal"); ax.axis("off")

    drawer = {
        "mitochondrion": _draw_mitochondrion,
        "chloroplast": _draw_chloroplast,
        "nucleus": _draw_nucleus_detail,
    }[schema.organelle]
    drawer(ax, schema, hl)

    ax.set_title(schema.title or f"{schema.organelle.capitalize()} — "
                                 f"Detailed Structure",
                 fontsize=14, fontweight="bold", pad=6)
    fig.tight_layout(pad=0.4)
    return _fig_to_svg(fig)


def _draw_mitochondrion(ax, schema, hl):
    cx, cy = 5.0, 5.0
    ax.add_patch(Ellipse((cx, cy), 8.6, 4.8, fc="#fff3e0",
                         ec=C["mitochondria"], lw=2.8, zorder=2))   # outer
    a, b = 3.95, 2.025                                              # inner semi-axes
    ax.add_patch(Ellipse((cx, cy), 2 * a, 2 * b, fc=C["matrix"],
                         ec=C["cristae"], lw=2.0, zorder=3))        # inner

    # Cristae are infoldings OF the inner membrane, so each one's base has to sit
    # ON the ellipse — both base corners are solved back onto it, not approximated.
    def _inner_y(x, up):
        return cy + (b if up else -b) * math.sqrt(
            max(0.0, 1 - ((x - cx) / a) ** 2))

    for i, bx in enumerate(np.linspace(2.4, 7.6, 6)):
        up = i % 2 == 0
        depth = -1.45 if up else 1.45
        xl, xr = bx - 0.3, bx + 0.3
        yl, yr = _inner_y(xl, up), _inner_y(xr, up)
        ax.add_patch(Polygon([(xl, yl), (xr, yr),
                              (xr, yr + depth), (xl, yl + depth)],
                             closed=True, fc="#ffcc80", ec=C["cristae"],
                             lw=1.6, joinstyle="round", zorder=4))
    for rx, ry in ((3.0, 5.4), (4.6, 4.6), (6.1, 5.2), (5.45, 5.9), (3.9, 4.3)):
        ax.plot(rx, ry, "o", color=C["ribosome"], markersize=4, zorder=6)
    dna_t = np.linspace(0, 2 * np.pi, 120)
    ax.plot(6.55 + 0.42 * np.cos(dna_t) + 0.06 * np.sin(5 * dna_t),
            4.35 + 0.3 * np.sin(dna_t), color=C["organelle_dna"], lw=2.0, zorder=6)
    # F₁ particles (oxysomes) stud the crista surface, not the free matrix.
    for ox, oy in ((4.85, 6.2), (5.15, 4.1)):
        ax.plot(ox, oy, "o", color="#6a1b9a", markersize=5, zorder=6)

    if not schema.show_labels:
        return
    _annotate(ax, "Outer membrane", (cx - 3.6, cy + 1.4), (-2.0, 9.4),
              C["mitochondria"], fontsize=9,
              highlight=_is_hl(hl, "outer_membrane"))
    _annotate(ax, "Inner membrane", (cx - 3.3, cy + 1.1), (1.8, 9.8),
              C["cristae"], fontsize=9, highlight=_is_hl(hl, "inner_membrane"))
    _annotate(ax, "Intermembrane space", (cx - 3.45, cy - 1.25), (-1.6, 0.6),
              "#8d6e63", fontsize=9,
              highlight=_is_hl(hl, "intermembrane_space"))
    _annotate(ax, "Cristae", (2.55, 5.9), (5.4, 9.8), C["cristae"],
              fontsize=9, highlight=_is_hl(hl, "cristae", "crista"))
    _annotate(ax, "Matrix", (4.95, 5.05), (9.6, 9.4), "#ef6c00",
              fontsize=9, highlight=_is_hl(hl, "matrix"))
    _annotate(ax, "Ribosome (70S)", (4.6, 4.6), (11.6, 7.4), C["ribosome"],
              fontsize=9, highlight=_is_hl(hl, "ribosome", "ribosomes"))
    _annotate(ax, "DNA (circular)", (6.55, 4.35), (11.6, 5.4),
              C["organelle_dna"], fontsize=9,
              highlight=_is_hl(hl, "dna"))
    _annotate(ax, "Oxysome (F₁ particle)", (5.15, 4.1), (10.6, 2.0),
              "#6a1b9a", fontsize=9, highlight=_is_hl(hl, "oxysome"))


def _draw_chloroplast(ax, schema, hl):
    cx, cy = 5.0, 5.0
    ax.add_patch(Ellipse((cx, cy), 9.0, 5.2, fc="#e8f5e9",
                         ec=C["chloroplast"], lw=2.8, zorder=2))    # outer
    ax.add_patch(Ellipse((cx, cy), 8.35, 4.55, fc=C["stroma"],
                         ec="#66bb6a", lw=1.8, zorder=3))           # inner

    granum_x = [2.4, 4.2, 6.0, 7.8]
    granum_y = [5.6, 4.3, 5.7, 4.4]
    for gx, gy in zip(granum_x, granum_y):
        for k, dy in enumerate(np.linspace(-0.42, 0.42, 5)):        # thylakoids
            ax.add_patch(FancyBboxPatch((gx - 0.62, gy + dy - 0.07), 1.24, 0.14,
                                        boxstyle="round,pad=0.015",
                                        fc=C["thylakoid"], ec=C["granum"],
                                        lw=0.8, zorder=5))
    # Stroma lamellae (intergranal) connect one granum to the next.
    for i in range(len(granum_x) - 1):
        ax.plot([granum_x[i] + 0.6, granum_x[i + 1] - 0.6],
                [granum_y[i], granum_y[i + 1]],
                color=C["lamella"], lw=2.4, solid_capstyle="round", zorder=4)

    dna_t = np.linspace(0, 2 * np.pi, 120)
    ax.plot(5.0 + 0.45 * np.cos(dna_t) + 0.06 * np.sin(5 * dna_t),
            3.1 + 0.3 * np.sin(dna_t), color=C["organelle_dna"], lw=2.0, zorder=6)
    for rx, ry in ((3.3, 3.2), (6.7, 3.2), (4.0, 6.6), (6.4, 6.6)):
        ax.plot(rx, ry, "o", color=C["ribosome"], markersize=4, zorder=6)
    ax.add_patch(Ellipse((7.9, 6.3), 0.9, 0.6, fc="#fff9c4", ec="#f9a825",
                         lw=1.2, zorder=6))                          # starch grain

    if not schema.show_labels:
        return
    _annotate(ax, "Outer membrane", (cx - 3.9, cy + 1.3), (-2.0, 9.4),
              C["chloroplast"], fontsize=9,
              highlight=_is_hl(hl, "outer_membrane"))
    _annotate(ax, "Inner membrane", (cx - 3.55, cy + 1.05), (1.8, 9.9),
              "#66bb6a", fontsize=9, highlight=_is_hl(hl, "inner_membrane"))
    _annotate(ax, "Granum\n(stack of thylakoids)", (2.4, 5.6), (5.4, 9.9),
              C["granum"], fontsize=9, highlight=_is_hl(hl, "granum", "grana"))
    _annotate(ax, "Thylakoid", (6.0, 5.9), (10.2, 9.4), C["thylakoid"],
              fontsize=9, highlight=_is_hl(hl, "thylakoid"))
    _annotate(ax, "Stroma lamella", (5.1, 5.0), (11.8, 7.2), C["lamella"],
              fontsize=9, highlight=_is_hl(hl, "lamella", "stroma_lamella"))
    _annotate(ax, "Stroma", (4.5, 3.9), (11.7, 5.3), "#2e7d32",
              fontsize=9, highlight=_is_hl(hl, "stroma"))
    _annotate(ax, "DNA (circular)", (5.0, 3.1), (7.0, 1.2),
              C["organelle_dna"], fontsize=9, highlight=_is_hl(hl, "dna"))
    _annotate(ax, "Ribosome (70S)", (3.3, 3.2), (2.0, 0.9), C["ribosome"],
              fontsize=9, highlight=_is_hl(hl, "ribosome", "ribosomes"))
    _annotate(ax, "Starch grain", (7.9, 6.3), (11.6, 3.2), "#f9a825",
              fontsize=9, highlight=_is_hl(hl, "starch_grain"))


def _draw_nucleus_detail(ax, schema, hl):
    cx, cy = 5.0, 5.0
    R = 3.5
    ax.add_patch(Circle((cx, cy), R, fc="#ede7f6", ec=C["nucleus"],
                        lw=2.6, zorder=2))                          # outer membrane
    ax.add_patch(Circle((cx, cy), R - 0.3, fc="#f3e5f5", ec=C["nucleus"],
                        lw=2.0, zorder=3))                          # inner membrane

    # Nuclear pores — gaps that pierce BOTH membranes of the envelope.
    for deg in (35, 95, 150, 215, 270, 325):
        ox, oy = _polar(cx, cy, R, deg)
        ix, iy = _polar(cx, cy, R - 0.3, deg)
        ax.plot([ox, ix], [oy, iy], color="white", lw=6, zorder=4)
        ax.plot([ox, ix], [oy, iy], color=C["nuclear_pore"], lw=1.4, zorder=5)
        for s in (-1, 1):
            px, py = _polar(cx, cy, R - 0.15, deg + s * 3.5)
            ax.plot(px, py, "o", color=C["nuclear_pore"], markersize=4, zorder=6)

    ax.add_patch(Circle((cx - 0.9, cy + 0.7), 0.85, fc=C["nucleolus"],
                        ec="#4527a0", lw=1.4, zorder=6))            # nucleolus

    # Chromatin: deterministic squiggles through the nucleoplasm.
    for k, (sx, sy, amp, freq) in enumerate((
            (1.9, 3.4, 0.35, 3.0), (2.4, 6.6, 0.30, 4.0),
            (5.1, 3.1, 0.28, 3.5), (5.4, 6.9, 0.32, 3.0))):
        t = np.linspace(0, 2.6, 120)
        ax.plot(sx + t + 0.0 * t, sy + amp * np.sin(freq * np.pi * t / 2.6),
                color=C["chromatin"], lw=2.0, alpha=0.9, zorder=5)

    if not schema.show_labels:
        return
    _annotate(ax, "Nuclear envelope\n(double membrane)",
              _polar(cx, cy, R, 125), (-1.2, 9.5), C["nucleus"], fontsize=9,
              highlight=_is_hl(hl, "nuclear_envelope", "nuclear_membrane"))
    _annotate(ax, "Nuclear pore", _polar(cx, cy, R, 95), (4.6, 9.8),
              C["nuclear_pore"], fontsize=9,
              highlight=_is_hl(hl, "nuclear_pore", "nuclear_pores"))
    _annotate(ax, "Nucleolus", (cx - 0.9, cy + 0.7), (-1.8, 6.8),
              C["nucleolus"], fontsize=9, highlight=_is_hl(hl, "nucleolus"))
    _annotate(ax, "Chromatin\n(DNA + histones)", (6.2, 6.9), (10.8, 8.6),
              C["chromatin"], fontsize=9, highlight=_is_hl(hl, "chromatin"))
    _annotate(ax, "Nucleoplasm", (6.6, 4.2), (11.2, 4.6), "#7e57c2",
              fontsize=9, highlight=_is_hl(hl, "nucleoplasm"))
    _annotate(ax, "Perinuclear space", _polar(cx, cy, R - 0.15, 250),
              (0.6, 0.6), "#9575cd", fontsize=9,
              highlight=_is_hl(hl, "perinuclear_space"))


# ═══════════════════════════════════════════════════════════════════════════════
# 18. Metabolic Cycle
# ═══════════════════════════════════════════════════════════════════════════════

# Built-in pathways. `nodes` are (label, edge_label) where edge_label rides the
# arrow LEAVING that node; `hub` is a central species feeding the ring; `chords`
# are (from_index, to_index, label) cross-links — an index of -1 means the hub.
_CYCLE_DEFAULTS: Dict[str, Dict[str, Any]] = {
    "krebs": {
        "layout": "circular",
        "hub": "Acetyl CoA (2C)\n(from pyruvate)",
        "nodes": [
            ("Citrate (6C)",         "Aconitase"),
            ("Isocitrate (6C)",      "NAD⁺ → NADH + H⁺\nCO₂ released"),
            ("α-Ketoglutarate (5C)", "NAD⁺ → NADH + H⁺\nCO₂ released"),
            ("Succinyl CoA (4C)",    "GDP + Pi → GTP\n(substrate-level)"),
            ("Succinate (4C)",       "FAD → FADH₂"),
            ("Fumarate (4C)",        "H₂O added"),
            ("Malate (4C)",          "NAD⁺ → NADH + H⁺"),
            ("Oxaloacetate (4C)",    "Citrate synthase"),
        ],
        "chords": [(-1, 0, "Condenses with OAA")],
        "note": "Per acetyl CoA: 3 NADH + 1 FADH₂ + 1 GTP (ATP) + 2 CO₂",
    },
    "calvin": {
        "layout": "circular",
        "hub": "CO₂",
        "nodes": [
            ("RuBP (5C)",            "CO₂ + H₂O; RuBisCO\n(CARBOXYLATION)"),
            ("3-PGA (3C) × 2",       "2 ATP → 2 ADP"),
            ("1,3-BPG (3C)",         "2 NADPH → 2 NADP⁺\n(REDUCTION)"),
            ("G3P / PGAL (3C)",      "1 of 6 G3P leaves\n→ glucose"),
            ("Ribulose-5-\nphosphate (5C)", "ATP → ADP\n(REGENERATION)"),
        ],
        "chords": [(-1, 0, "Fixed by RuBisCO")],
        "note": "3 CO₂ fixed → 1 G3P; costs 9 ATP + 6 NADPH (C₃ pathway)",
    },
    "urea": {
        "layout": "circular",
        "hub": "NH₃ + CO₂\n(carbamoyl phosphate)",
        "nodes": [
            ("Ornithine",         "Carbamoyl phosphate;\nornithine transcarbamylase"),
            ("Citrulline",        "Aspartate + ATP;\nargininosuccinate synthetase"),
            ("Argininosuccinate", "Argininosuccinase;\nfumarate released"),
            ("Arginine",          "Arginase + H₂O →\nUREA released"),
        ],
        "chords": [(-1, 0, "Enters the cycle")],
        "note": "Ornithine cycle — occurs in the liver; urea is excreted by the kidney",
    },
    "nitrogen": {
        "layout": "circular",
        "hub": "N₂\n(atmospheric nitrogen)",
        "nodes": [
            ("Ammonia\nNH₃ / NH₄⁺",  "Nitrification\n(Nitrosomonas)"),
            ("Nitrite\nNO₂⁻",        "Nitrification\n(Nitrobacter)"),
            ("Nitrate\nNO₃⁻",        "Assimilation\n(absorbed by plants)"),
            ("Organic nitrogen\n(plant & animal\nproteins)",
             "Ammonification\n(decomposers)"),
        ],
        "chords": [
            (-1, 0, "Nitrogen fixation\n(Rhizobium, Azotobacter,\nlightning)"),
            (2, -1, "Denitrification\n(Pseudomonas)"),
        ],
        "note": "Nitrogen fixation → nitrification → assimilation → "
                "ammonification → denitrification",
    },
    "carbon": {
        "layout": "circular",
        "hub": "Respiration\nreturns CO₂",
        "nodes": [
            ("CO₂ in the\natmosphere",      "Photosynthesis\n(CO₂ fixed by producers)"),
            ("Producers\n(green plants)",   "Feeding\n(organic carbon)"),
            ("Consumers\n(animals)",        "Death & excretion"),
            ("Dead organic matter\n(detritus)", "Fossilisation\n(over millions of years)"),
            ("Fossil fuels\n(coal, petroleum)", "Combustion\n(burning of fossil fuels)"),
        ],
        "chords": [
            (1, 0, "Respiration"),
            (2, 0, "Respiration"),
            (3, 0, "Decomposition\n(microbial respiration)"),
        ],
        "note": "Photosynthesis fixes CO₂; respiration, decomposition and "
                "combustion return it",
    },
    "glycolysis": {
        "layout": "linear",
        "hub": None,
        "nodes": [
            ("Glucose (6C)",              "ATP → ADP  (hexokinase)"),
            ("Glucose-6-phosphate",       "Phosphohexose isomerase"),
            ("Fructose-6-phosphate",      "ATP → ADP  (phosphofructokinase)"),
            ("Fructose-1,6-bisphosphate", "Aldolase — splits into two 3C sugars"),
            ("DHAP  ⇌  PGAL (3C) × 2",    "2 NAD⁺ → 2 NADH + H⁺;  2 Pi added"),
            ("1,3-Bisphosphoglycerate × 2", "2 ADP → 2 ATP  (substrate-level)"),
            ("3-Phosphoglycerate × 2",    "Phosphoglyceromutase"),
            ("2-Phosphoglycerate × 2",    "Enolase — H₂O removed"),
            ("Phosphoenolpyruvate (PEP) × 2", "2 ADP → 2 ATP  (pyruvate kinase)"),
            ("Pyruvic acid (3C) × 2",     None),
        ],
        "chords": [],
        "note": "EMP pathway, in the cytoplasm. Net gain per glucose: "
                "2 ATP + 2 NADH",
    },
}


def render_metabolic_cycle(data: Dict[str, Any],
                           canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = MetabolicCycleSchema(**data)
    default = _CYCLE_DEFAULTS[schema.cycle]

    if schema.steps:
        nodes = [(_wrap(s.label), s.edge_label) for s in schema.steps]
        hub, chords, note = None, [], ""
    else:
        nodes = default["nodes"]
        hub, chords = default["hub"], default["chords"]
        note = default["note"]

    layout = schema.layout or default["layout"]
    title = schema.title or f"{schema.cycle.capitalize()} — Pathway"
    if layout == "linear":
        return _draw_linear_pathway(nodes, schema, title, note)
    return _draw_circular_cycle(nodes, hub, chords, schema, title, note)


def _cycle_node(ax, x, y, label, fontsize=9):
    ax.text(x, y, label, ha="center", va="center", fontsize=fontsize,
            fontweight="bold", color="#311b92", zorder=6,
            bbox=dict(boxstyle="round,pad=0.35", fc=C["cycle_node"],
                      ec=C["cycle_node_edge"], lw=1.6))


def _draw_circular_cycle(nodes, hub, chords, schema, title, note) -> str:
    n = len(nodes)
    R = 4.2
    fig, ax = plt.subplots(figsize=(12, 11))
    ax.set_xlim(-8.6, 8.6); ax.set_ylim(-8.2, 8.2)
    ax.set_aspect("equal"); ax.axis("off")

    # Clockwise from 12 o'clock — the direction metabolic cycles are drawn in.
    angles = [90 - i * (360 / n) for i in range(n)]
    pts = [_polar(0, 0, R, a) for a in angles]

    for i in range(n):
        a0, a1 = angles[i], angles[(i + 1) % n]
        span = (a0 - a1) % 360
        start = _polar(0, 0, R, a0 - span * 0.30)
        end = _polar(0, 0, R, a0 - span * 0.70)
        ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>",
                                     mutation_scale=20, lw=2.0,
                                     color=C["cycle_arrow"],
                                     connectionstyle="arc3,rad=0.18", zorder=3))
        edge_label = nodes[i][1]
        if edge_label and schema.show_labels:
            lx, ly = _polar(0, 0, R + 1.55, a0 - span * 0.5)
            ax.text(lx, ly, edge_label, ha="center", va="center", fontsize=8,
                    color=C["cycle_enzyme"], zorder=5,
                    bbox=dict(boxstyle="round,pad=0.22", fc="white",
                              ec=C["cycle_enzyme"], lw=0.8, alpha=0.95))

    for (x, y), (label, _) in zip(pts, nodes):
        _cycle_node(ax, x, y, label)

    if hub:
        ax.text(0, 0, hub, ha="center", va="center", fontsize=9.5,
                fontweight="bold", color="#e65100", zorder=6,
                bbox=dict(boxstyle="round,pad=0.4", fc=C["cycle_hub"],
                          ec="#f57f17", lw=1.6))

    for src, dst, label in chords:
        p_src = (0.0, 0.0) if src == -1 else pts[src]
        p_dst = (0.0, 0.0) if dst == -1 else pts[dst]
        # Pull the chord off the box centres so it starts/ends outside the label.
        vx, vy = p_dst[0] - p_src[0], p_dst[1] - p_src[1]
        d = math.hypot(vx, vy) or 1.0
        a_pt = (p_src[0] + vx / d * 1.35, p_src[1] + vy / d * 1.35)
        b_pt = (p_dst[0] - vx / d * 1.35, p_dst[1] - vy / d * 1.35)
        ax.add_patch(FancyArrowPatch(a_pt, b_pt, arrowstyle="-|>",
                                     mutation_scale=16, lw=1.6, ls="--",
                                     color=C["cycle_chord"],
                                     connectionstyle="arc3,rad=0.22", zorder=4))
        if schema.show_labels:
            mx, my = (a_pt[0] + b_pt[0]) / 2, (a_pt[1] + b_pt[1]) / 2
            ax.text(mx, my, label, ha="center", va="center", fontsize=7.5,
                    color=C["cycle_chord"], zorder=5,
                    bbox=dict(boxstyle="round,pad=0.2", fc="#fce4ec",
                              ec=C["cycle_chord"], lw=0.7, alpha=0.95))

    ax.set_title(title, fontsize=14, fontweight="bold", pad=6)
    if note:
        ax.text(0, -7.9, note, ha="center", va="center", fontsize=9.5,
                color="#37474f", style="italic",
                bbox=dict(boxstyle="round,pad=0.3", fc="#fffde7",
                          ec="#bdbdbd", lw=0.8))
    fig.tight_layout(pad=0.4)
    return _fig_to_svg(fig)


def _draw_linear_pathway(nodes, schema, title, note) -> str:
    n = len(nodes)
    step = 1.35
    fig, ax = plt.subplots(figsize=(11, max(6.0, 1.15 * n)))
    ax.set_xlim(-6.2, 8.2)
    ax.set_ylim(-1.4, n * step + 0.6)
    ax.axis("off")

    ys = [n * step - i * step for i in range(n)]
    for (label, edge_label), y in zip(nodes, ys):
        _cycle_node(ax, -1.6, y, label, fontsize=9)

    for i in range(n - 1):
        ax.add_patch(FancyArrowPatch((-1.6, ys[i] - 0.42),
                                     (-1.6, ys[i + 1] + 0.42),
                                     arrowstyle="-|>", mutation_scale=20,
                                     lw=2.0, color=C["cycle_arrow"], zorder=3))
        edge_label = nodes[i][1]
        if edge_label and schema.show_labels:
            ax.text(-1.05, (ys[i] + ys[i + 1]) / 2, edge_label, ha="left",
                    va="center", fontsize=8.5, color=C["cycle_enzyme"],
                    bbox=dict(boxstyle="round,pad=0.22", fc="white",
                              ec=C["cycle_enzyme"], lw=0.8))

    ax.set_title(title, fontsize=14, fontweight="bold", pad=6)
    if note:
        ax.text(0.6, -0.9, note, ha="center", va="center", fontsize=9.5,
                color="#37474f", style="italic",
                bbox=dict(boxstyle="round,pad=0.3", fc="#fffde7",
                          ec="#bdbdbd", lw=0.8))
    fig.tight_layout(pad=0.4)
    return _fig_to_svg(fig)


# ═══════════════════════════════════════════════════════════════════════════════
# 19. Gel Electrophoresis
# ═══════════════════════════════════════════════════════════════════════════════

_GEL_TOP, _GEL_BOT = 8.1, 1.5      # y-range the bands are laid out in


def _band_y(size_bp: float, lo_bp: float, hi_bp: float,
            y_top: float = _GEL_TOP, y_bot: float = _GEL_BOT) -> float:
    """Migration distance is linear in log10(fragment size), and INVERSE:
    a large fragment is retarded by the gel matrix and stays near the well
    (high y), a small one runs far towards the anode (low y). That inverse-log
    relationship is the whole point of the diagram, so it lives in one place."""
    span = math.log10(hi_bp) - math.log10(lo_bp)
    size = min(max(float(size_bp), lo_bp), hi_bp)
    frac = (math.log10(hi_bp) - math.log10(size)) / span
    return y_top - frac * (y_top - y_bot)


def render_gel_electrophoresis(data: Dict[str, Any],
                               canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = GelElectrophoresisSchema(**data)

    sizes = [b.size_bp for lane in schema.lanes for b in lane.bands]
    sizes += list(schema.ladder_sizes)
    if not sizes:
        sizes = [100, 10000]
    # Pad the log range so the extreme bands never sit flush against the edges.
    lo = min(sizes) / 1.6
    hi = max(sizes) * 1.6
    if hi / lo < 10:                     # keep a sane decade span for one-band gels
        lo, hi = lo / 3.0, hi * 3.0

    has_ladder = bool(schema.ladder_sizes)
    n_lanes = len(schema.lanes) + (1 if has_ladder else 0)
    lane_dx = 1.75
    x_first = 1.4
    gel_w = x_first + lane_dx * (n_lanes - 1) + 1.4

    fig, ax = plt.subplots(figsize=(max(7.5, 1.5 * n_lanes + 4.0), 8.5))
    ax.set_xlim(-2.6, gel_w + 1.2); ax.set_ylim(-0.5, 10.4)
    ax.axis("off")

    ax.add_patch(Rectangle((0, 0.6), gel_w, 8.5, fc=C["gel_bg"],
                           ec="#212121", lw=2.0, zorder=2))

    def _lane_x(i):
        return x_first + i * lane_dx

    def _draw_band(x, y, color, intensity, label=None):
        ax.add_patch(Rectangle((x - 0.58, y - 0.07), 1.16, 0.14, fc=color,
                               ec="none", alpha=min(1.0, 0.35 + 0.65 * intensity),
                               zorder=5))
        if label:
            ax.text(x - 0.78, y, label, ha="right", va="center", fontsize=8,
                    color="#37474f", zorder=6)

    idx = 0
    if has_ladder:
        x = _lane_x(0)
        for size in sorted(schema.ladder_sizes, reverse=True):
            _draw_band(x, _band_y(size, lo, hi), C["gel_ladder"], 1.0,
                       label=f"{size:,} bp")
        ax.text(x, 9.35, "Ladder", ha="center", fontsize=9.5,
                fontweight="bold", color="#f9a825")
        idx = 1

    for k, lane in enumerate(schema.lanes):
        x = _lane_x(idx + k)
        for band in lane.bands:
            _draw_band(x, _band_y(band.size_bp, lo, hi), C["gel_band"],
                       band.intensity)
        ax.text(x, 9.35, lane.label, ha="center", fontsize=9.5,
                fontweight="bold", color="#37474f")

    if schema.show_wells:
        for i in range(n_lanes):
            ax.add_patch(Rectangle((_lane_x(i) - 0.6, 8.55), 1.2, 0.45,
                                   fc=C["gel_well"], ec="#eceff1",
                                   lw=1.2, zorder=4))
        ax.text(-0.35, 8.78, "Wells", ha="right", va="center", fontsize=9,
                color="#37474f", fontweight="bold")

    if schema.show_migration_arrow:
        ax.annotate("", xy=(-1.5, 1.2), xytext=(-1.5, 8.6),
                    arrowprops=dict(arrowstyle="-|>", color="#37474f", lw=2.2))
        ax.text(-1.95, 4.9, "Direction of migration", rotation=90,
                ha="center", va="center", fontsize=9.5, color="#37474f")
        # DNA is negatively charged, so it runs from the cathode to the anode.
        ax.text(-1.5, 9.35, "– cathode", ha="center", fontsize=10,
                fontweight="bold", color=C["gel_cathode"])
        ax.text(-1.5, 0.75, "+ anode", ha="center", fontsize=10,
                fontweight="bold", color=C["gel_anode"])
        ax.text(gel_w + 0.9, 7.6, "Larger fragments\nmigrate LESS",
                ha="center", va="center", rotation=90, fontsize=8.5,
                color="#616161", style="italic")
        ax.text(gel_w + 0.9, 2.4, "Smaller fragments\nmigrate MORE",
                ha="center", va="center", rotation=90, fontsize=8.5,
                color="#616161", style="italic")

    if schema.gel_label:
        ax.text(gel_w / 2, 0.05, schema.gel_label, ha="center", fontsize=9.5,
                color="#37474f", style="italic")

    ax.set_title(schema.title or "Agarose Gel Electrophoresis of DNA",
                 fontsize=14, fontweight="bold", pad=6)
    fig.tight_layout(pad=0.4)
    return _fig_to_svg(fig)


# ═══════════════════════════════════════════════════════════════════════════════
# 20. Plasmid Map
# ═══════════════════════════════════════════════════════════════════════════════

_FEATURE_COLORS = {
    "ori":                C["feat_ori"],
    "resistance_marker":  C["feat_resistance"],
    "promoter":           C["feat_promoter"],
    "insert":             C["feat_insert"],
    "gene":               C["feat_gene"],
}
_FEATURE_NAMES = {
    "ori":               "Origin of replication",
    "resistance_marker": "Selectable (resistance) marker",
    "promoter":          "Promoter",
    "insert":            "Insert / foreign DNA",
    "gene":              "Gene",
}


def render_plasmid_map(data: Dict[str, Any],
                       canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = PlasmidMapSchema(**data)
    size = schema.size_bp
    R = 3.4

    def _deg(bp: float) -> float:
        # 0 bp at 12 o'clock, numbering clockwise — the standard vector-map convention.
        return 90.0 - 360.0 * (bp / size)

    fig, ax = plt.subplots(figsize=(11, 10))
    ax.set_xlim(-7.6, 7.6); ax.set_ylim(-6.4, 6.4)
    ax.set_aspect("equal"); ax.axis("off")

    ax.add_patch(Circle((0, 0), R, fc="none", ec=C["plasmid_backbone"],
                        lw=3.5, zorder=2))
    ax.plot([0, 0], [R - 0.28, R + 0.28], color=C["plasmid_backbone"],
            lw=1.6, zorder=3)
    ax.text(0.18, R + 0.42, f"0 / {size:,} bp", fontsize=8,
            color=C["plasmid_backbone"], ha="left")

    used_types = []
    for feat in schema.features:
        start, end = feat.start_bp, feat.end_bp
        t_start, t_end = _deg(start), _deg(end)
        if end < start:                 # feature wraps past the origin
            t_end -= 360.0
        ax.add_patch(Arc((0, 0), 2 * R, 2 * R, theta1=t_end, theta2=t_start,
                         color=_FEATURE_COLORS[feat.feature_type],
                         lw=10, zorder=4))
        if feat.feature_type not in used_types:
            used_types.append(feat.feature_type)
        if schema.show_labels:
            mid = (t_start + t_end) / 2
            lx, ly = _polar(0, 0, R - 1.05, mid)
            ax.text(lx, ly, feat.name, ha="center", va="center", fontsize=8.5,
                    fontweight="bold",
                    color=_FEATURE_COLORS[feat.feature_type], zorder=6,
                    bbox=dict(boxstyle="round,pad=0.2", fc="white",
                              ec=_FEATURE_COLORS[feat.feature_type],
                              lw=0.8, alpha=0.95))

    for site in schema.restriction_sites:
        deg = _deg(site.position_bp)
        x1, y1 = _polar(0, 0, R - 0.42, deg)
        x2, y2 = _polar(0, 0, R + 0.42, deg)
        ax.plot([x1, x2], [y1, y2], color=C["restriction"], lw=2.0, zorder=7)
        if schema.show_labels:
            tx, ty = _polar(0, 0, R + 1.0, deg)
            ha = "left" if math.cos(math.radians(deg)) >= 0 else "right"
            ax.text(tx, ty, f"{site.enzyme} ({site.position_bp:,})",
                    ha=ha, va="center", fontsize=8.5, color=C["restriction"],
                    zorder=7)

    ax.text(0, 0.25, schema.plasmid_name, ha="center", va="center",
            fontsize=15, fontweight="bold", color=C["plasmid_backbone"])
    ax.text(0, -0.35, f"{size:,} bp", ha="center", va="center",
            fontsize=11, color="#607d8b")

    if used_types and schema.show_labels:
        ax.legend(handles=[mpatches.Patch(fc=_FEATURE_COLORS[t], ec="none",
                                          label=_FEATURE_NAMES[t])
                           for t in used_types],
                  loc="lower left", bbox_to_anchor=(0.0, 0.0),
                  fontsize=8.5, frameon=True)

    ax.set_title(schema.title or f"Plasmid Map — {schema.plasmid_name}",
                 fontsize=14, fontweight="bold", pad=6)
    fig.tight_layout(pad=0.4)
    return _fig_to_svg(fig)


# ═══════════════════════════════════════════════════════════════════════════════
# 21. Brain Diagram (L.S.)
# ═══════════════════════════════════════════════════════════════════════════════

def render_brain_diagram(data: Dict[str, Any],
                         canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = BrainDiagramSchema(**data)
    hl = _norm(schema.highlight_region)

    fig, ax = plt.subplots(figsize=(12, 9))
    ax.set_xlim(-4.0, 14.6); ax.set_ylim(-1.6, 10.8)
    ax.set_aspect("equal"); ax.axis("off")

    # Mid-sagittal section, anterior (front) to the LEFT — the NCERT convention.

    # ── Cerebrum, with gyri on the outer surface ──────────────────────────────
    t = np.linspace(0, 2 * np.pi, 500)
    wave = 1 + 0.028 * np.sin(15 * t) * (np.sin(t) > -0.25)
    cx_, cy_ = 5.0, 6.4
    ax.fill(cx_ + 4.1 * np.cos(t) * wave, cy_ + 2.75 * np.sin(t) * wave,
            fc=C["cerebrum"], ec="#ad1457", lw=2.0, zorder=2)

    # ── Corpus callosum: arched band of white matter under the cortex ─────────
    ax.add_patch(Arc((4.7, 5.35), 4.6, 3.0, theta1=15, theta2=170,
                     color=C["corpus_callosum"], lw=8, zorder=4))
    ax.add_patch(Arc((4.7, 5.35), 4.6, 3.0, theta1=15, theta2=170,
                     color="#546e7a", lw=1.0, zorder=5))

    # ── Diencephalon: thalamus + hypothalamus + pituitary ─────────────────────
    ax.add_patch(Ellipse((5.95, 5.15), 1.7, 1.1, angle=-8, fc=C["thalamus"],
                         ec="#ef6c00", lw=1.5, zorder=5))
    ax.add_patch(Ellipse((5.25, 4.3), 1.2, 0.6, angle=-10, fc=C["hypothalamus"],
                         ec="#e65100", lw=1.5, zorder=5))
    ax.plot([5.1, 4.95], [4.05, 3.55], color="#bf360c", lw=2.2, zorder=5)
    ax.add_patch(Circle((4.9, 3.3), 0.35, fc=C["pituitary"], ec="#b71c1c",
                        lw=1.5, zorder=6))
    ax.add_patch(Ellipse((1.35, 4.55), 1.1, 0.62, angle=12, fc=C["olfactory"],
                         ec="#33691e", lw=1.5, zorder=5))          # olfactory lobe

    # ── Brainstem: midbrain → pons → medulla → spinal cord ────────────────────
    ax.add_patch(Ellipse((7.0, 4.35), 1.1, 0.9, angle=-25, fc=C["midbrain"],
                         ec="#00695c", lw=1.5, zorder=5))
    ax.add_patch(Ellipse((7.35, 3.35), 1.5, 1.15, angle=-20, fc=C["pons"],
                         ec="#00695c", lw=1.5, zorder=5))
    ax.add_patch(Ellipse((7.75, 2.15), 1.2, 1.35, angle=-12, fc=C["medulla"],
                         ec="#00695c", lw=1.5, zorder=5))
    ax.add_patch(FancyBboxPatch((7.5, -0.3), 0.85, 1.9,
                                boxstyle="round,pad=0.05", fc=C["spinal_cord"],
                                ec="#004d40", lw=1.5, zorder=4))

    # ── Cerebellum: posterior-inferior, with the arbor vitae inside ───────────
    ax.add_patch(Ellipse((10.0, 3.3), 3.0, 2.6, fc=C["cerebellum"],
                         ec="#4527a0", lw=2.0, zorder=3))
    for deg in range(-60, 130, 24):
        ex, ey = _polar(10.0, 3.3, 1.25, deg)
        ax.plot([9.1, ex], [3.3, ey], color="#ede7f6", lw=2.2, zorder=4)
    ax.plot([9.1, 8.45], [3.3, 3.1], color="#ede7f6", lw=3.0, zorder=4)

    if schema.show_labels:
        _annotate(ax, "Cerebrum", (3.4, 8.4), (0.4, 10.3), "#ad1457",
                  fontsize=9.5, highlight=_is_hl(hl, "cerebrum"))
        _annotate(ax, "Corpus callosum", (4.4, 6.75), (-2.6, 8.6),
                  "#546e7a", fontsize=9.5,
                  highlight=_is_hl(hl, "corpus_callosum"))
        _annotate(ax, "Olfactory lobe\n(bulb)", (1.35, 4.55), (-2.6, 5.6),
                  "#33691e", fontsize=9.5,
                  highlight=_is_hl(hl, "olfactory_lobe", "olfactory"))
        _annotate(ax, "Hypothalamus", (5.05, 4.25), (-2.4, 3.2), "#e65100",
                  fontsize=9.5, highlight=_is_hl(hl, "hypothalamus"))
        _annotate(ax, "Pituitary gland", (4.9, 3.05), (-2.2, 1.3),
                  C["pituitary"], fontsize=9.5,
                  highlight=_is_hl(hl, "pituitary", "pituitary_gland"))
        _annotate(ax, "Thalamus", (6.2, 5.35), (8.0, 9.9), "#ef6c00",
                  fontsize=9.5, highlight=_is_hl(hl, "thalamus"))
        _annotate(ax, "Midbrain", (7.25, 4.55), (11.4, 9.2), "#00695c",
                  fontsize=9.5, highlight=_is_hl(hl, "midbrain"))
        _annotate(ax, "Cerebellum", (10.6, 4.1), (13.4, 7.4), "#4527a0",
                  fontsize=9.5, highlight=_is_hl(hl, "cerebellum"))
        _annotate(ax, "Pons (Varolii)", (6.9, 3.1), (13.0, 5.2), "#00695c",
                  fontsize=9.5, highlight=_is_hl(hl, "pons"))
        _annotate(ax, "Medulla oblongata", (7.35, 1.9), (12.8, 2.6), "#00838f",
                  fontsize=9.5,
                  highlight=_is_hl(hl, "medulla", "medulla_oblongata"))
        _annotate(ax, "Spinal cord", (8.35, 0.4), (12.0, 0.0),
                  C["spinal_cord"], fontsize=9.5,
                  highlight=_is_hl(hl, "spinal_cord"))
        ax.text(0.0, -1.15, "Anterior (front)", fontsize=9, color="#607d8b",
                style="italic", ha="center")
        ax.text(11.6, -1.15, "Posterior (back)", fontsize=9, color="#607d8b",
                style="italic", ha="center")

    ax.set_title(schema.title or "Human Brain — Longitudinal (Sagittal) Section",
                 fontsize=14, fontweight="bold", pad=6)
    fig.tight_layout(pad=0.4)
    return _fig_to_svg(fig)


# ═══════════════════════════════════════════════════════════════════════════════
# Shared geometry helper for the two-lobed outlines (anther lobes, dumb-bell
# guard cells) — one closed path around two circles joined by a straight waist.
# ═══════════════════════════════════════════════════════════════════════════════

def _bilobed_path(c1: Tuple[float, float], c2: Tuple[float, float],
                  r: float, waist_half: float) -> Path:
    if waist_half >= r:
        raise ValueError("waist must be narrower than the lobes")
    (x1, y1), (x2, y2) = c1, c2
    a = math.degrees(math.asin(waist_half / r))     # where the waist meets a lobe
    pts: List[Tuple[float, float]] = []
    for deg in np.linspace(a, 360 - a, 120):        # around the outside of lobe 1
        pts.append(_polar(x1, y1, r, deg))
    for deg in np.linspace(180 + a, 540 - a, 120):  # …and of lobe 2
        pts.append(_polar(x2, y2, r, deg))
    return Path(pts + [pts[0]], closed=True)


# ═══════════════════════════════════════════════════════════════════════════════
# 22. Reproductive System
# ═══════════════════════════════════════════════════════════════════════════════

# The order of the duct system is itself the exam question, so the caption is
# built from this list rather than typed out beside it.
_SPERM_PATH = ["Testis", "Epididymis", "Vas deferens", "Ejaculatory duct",
               "Urethra"]


def render_reproductive_system(data: Dict[str, Any],
                               canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = ReproductiveSystemSchema(**data)
    hl = _norm(schema.highlight_part)

    if schema.system == "human_male":
        fig, ax = plt.subplots(figsize=(13, 8))
        ax.set_xlim(-4.6, 16.4); ax.set_ylim(-1.6, 11.0)
        _draw_male_reproductive(ax, schema, hl)
        caption = "Path of the sperm:  " + "  →  ".join(_SPERM_PATH)
        default_title = "Human Male Reproductive System (sectional view)"
    else:
        fig, ax = plt.subplots(figsize=(13, 8))
        ax.set_xlim(-5.2, 17.4); ax.set_ylim(0.0, 11.6)
        _draw_female_reproductive(ax, schema, hl)
        caption = ("Fertilisation normally occurs in the AMPULLA of the "
                   "fallopian tube; the embryo implants in the ENDOMETRIUM")
        default_title = "Human Female Reproductive System (frontal view)"

    ax.set_aspect("equal"); ax.axis("off")
    ax.set_title(schema.title or default_title,
                 fontsize=14, fontweight="bold", pad=6)
    fig.text(0.5, 0.015, caption, ha="center", fontsize=9.5,
             color="#37474f", style="italic")
    fig.tight_layout(pad=0.4, rect=(0, 0.04, 1, 1))
    return _fig_to_svg(fig)


def _draw_male_reproductive(ax, schema, hl):
    # The urethra is the single duct the bladder, the prostate and the penis all
    # sit on, so it is laid out first and everything else is hung off it.
    urethra = np.array([
        (7.20, 5.55), (7.15, 4.90), (7.05, 4.20), (6.75, 3.58), (6.30, 3.28),
        (5.00, 3.10), (3.50, 2.89), (2.20, 2.71), (1.35, 2.59),
    ])

    # ── Urinary bladder + ureters ─────────────────────────────────────────────
    ax.add_patch(Ellipse((7.2, 6.9), 3.0, 2.6, fc="#e3f2fd",
                         ec=C["bladder"], lw=2.0, zorder=3))
    for sx in (-1, 1):
        ax.plot([7.2 + sx * 1.05, 7.2 + sx * 1.85], [7.75, 9.4],
                color="#0277bd", lw=2.4, zorder=2)

    # ── Penis (the urethra runs down its middle) ──────────────────────────────
    ax.plot([6.30, 1.55], [3.28, 2.62], color=C["penis"], lw=21,
            solid_capstyle="round", zorder=3)
    ax.add_patch(Ellipse((1.25, 2.58), 1.2, 0.95, angle=-7, fc="#ff8a65",
                         ec="#bf360c", lw=1.6, zorder=4))            # glans

    # ── Prostate + bulbourethral gland, both on the urethra ───────────────────
    ax.add_patch(Circle((7.12, 4.45), 0.92, fc="#b2ebf2", ec=C["prostate"],
                        lw=2.0, zorder=4))
    ax.add_patch(Circle((5.60, 3.98), 0.33, fc="#d7ccc8", ec=C["cowper"],
                        lw=1.5, zorder=5))
    ax.plot([5.60, 5.64], [3.65, 3.36], color=C["cowper"], lw=1.4, zorder=5)

    ax.plot(urethra[:, 0], urethra[:, 1], color=C["urethra"], lw=3.0,
            solid_capstyle="round", zorder=6)

    # ── Scrotum, testis, epididymis ───────────────────────────────────────────
    ax.add_patch(Ellipse((7.0, 0.85), 4.2, 2.4, fc="#efebe9",
                         ec=C["scrotum"], lw=2.0, zorder=2))
    ax.add_patch(Ellipse((6.9, 0.95), 2.3, 1.5, fc="#d1c4e9",
                         ec=C["testis"], lw=2.0, zorder=3))
    for dy in (-0.42, -0.14, 0.14, 0.42):                            # seminiferous
        sx_ = np.linspace(5.95, 7.85, 60)                            # tubules
        ax.plot(sx_, 0.95 + dy + 0.09 * np.sin(7 * (sx_ - 5.95)),
                color=C["testis"], lw=0.9, alpha=0.8, zorder=4)
    ax.add_patch(Arc((6.9, 0.95), 2.95, 2.15, theta1=-72, theta2=88,
                     color=C["epididymis"], lw=6, zorder=4))         # epididymis

    # ── Vas deferens → seminal vesicle → ejaculatory duct ─────────────────────
    ax.add_patch(PathPatch(_bezier((7.15, 2.02), (10.0, 2.6), (9.55, 5.05)),
                           fc="none", ec=C["vas_deferens"], lw=3.4, zorder=4))
    sv_c, sv_ang = (11.4, 6.3), -26
    ax.add_patch(Ellipse(sv_c, 2.9, 1.6, angle=sv_ang, fc="#fff59d",
                         ec=C["seminal_vesicle"], lw=2.0, zorder=4))
    for t in (-0.95, -0.32, 0.32, 0.95):                             # lobulations
        lx = sv_c[0] + t * math.cos(math.radians(sv_ang))
        ly = sv_c[1] + t * math.sin(math.radians(sv_ang))
        ax.add_patch(Circle((lx, ly), 0.3, fc="none",
                            ec=C["seminal_vesicle"], lw=1.0, zorder=5))
    ax.plot([10.15, 9.55], [5.65, 5.05], color=C["seminal_vesicle"],
            lw=2.4, zorder=4)
    ax.add_patch(PathPatch(_bezier((9.55, 5.05), (8.7, 4.95), (7.85, 4.72)),
                           fc="none", ec="#00695c", lw=2.8, zorder=5))

    if not schema.show_labels:
        return
    labels = [
        ("Urinary bladder",     (6.10, 7.70), (-2.8, 9.9), C["bladder"],
         ("urinary_bladder", "bladder")),
        ("Prostate gland",      (6.35, 4.80), (-2.8, 7.6), C["prostate"],
         ("prostate", "prostate_gland")),
        ("Bulbourethral gland\n(Cowper's gland)", (5.35, 4.05), (-2.6, 5.9),
         C["cowper"], ("bulbourethral_gland", "cowper", "cowpers_gland")),
        ("Urethra",             (3.60, 2.94), (-2.8, 4.2), C["urethra"],
         ("urethra",)),
        ("Penis",               (2.80, 2.53), (-2.8, 2.6), C["penis"],
         ("penis",)),
        ("Glans penis",         (1.10, 2.15), (-2.6, 0.9), "#bf360c",
         ("glans", "glans_penis")),
        ("Seminiferous tubules", (5.95, 1.25), (2.0, -1.0), "#7e57c2",
         ("seminiferous_tubules", "seminiferous_tubule")),
        ("Ureter",              (8.70, 8.75), (12.6, 10.2), "#0277bd",
         ("ureter",)),
        ("Seminal vesicle",     (11.9, 7.05), (15.4, 8.6), C["seminal_vesicle"],
         ("seminal_vesicle",)),
        ("Ejaculatory duct",    (8.55, 4.85), (15.2, 6.9), "#00695c",
         ("ejaculatory_duct",)),
        ("Vas deferens\n(ductus deferens)", (9.75, 3.55), (15.2, 4.9),
         C["vas_deferens"], ("vas_deferens", "ductus_deferens")),
        ("Epididymis",          (8.32, 1.60), (15.0, 2.8), C["epididymis"],
         ("epididymis",)),
        ("Testis",              (7.55, 0.95), (14.6, 1.1), C["testis"],
         ("testis", "testes")),
        ("Scrotum",             (8.85, 0.10), (11.4, -1.1), C["scrotum"],
         ("scrotum",)),
    ]
    for text, xy, xytext, color, aliases in labels:
        _annotate(ax, text, xy, xytext, color, fontsize=9,
                  highlight=_is_hl(hl, *aliases))


def _draw_female_reproductive(ax, schema, hl):
    CX = 6.0
    uterus_outer = [
        (4.50, 7.00), (4.75, 7.62), (5.30, 7.98), (6.00, 8.08), (6.70, 7.98),
        (7.25, 7.62), (7.50, 7.00), (7.28, 6.00), (7.02, 5.00), (6.80, 4.35),
        (5.20, 4.35), (4.98, 5.00), (4.72, 6.00),
    ]
    endometrium = [
        (5.12, 7.02), (5.55, 7.45), (6.00, 7.56), (6.45, 7.45), (6.88, 7.02),
        (6.42, 5.30), (6.22, 4.55), (5.78, 4.55), (5.58, 5.30),
    ]
    ax.add_patch(Polygon(uterus_outer, closed=True, fc=C["myometrium"],
                         ec="#78909c", lw=3.5, zorder=3))
    ax.add_patch(Polygon(uterus_outer, closed=True, fc="none",
                         ec="#c62828", lw=1.0, zorder=4))
    ax.add_patch(Polygon(endometrium, closed=True, fc="#f8bbd0",
                         ec=C["endometrium"], lw=2.0, zorder=5))
    ax.plot([CX, CX], [4.6, 7.3], color="white", lw=1.8, zorder=6)  # cavity

    # ── Cervix + vagina ───────────────────────────────────────────────────────
    ax.add_patch(Polygon([(5.20, 4.35), (6.80, 4.35), (6.62, 3.30),
                          (5.38, 3.30)], closed=True, fc="#b2ebf2",
                         ec=C["cervix"], lw=2.0, zorder=4))
    ax.plot([CX, CX], [3.35, 4.35], color="white", lw=1.6, zorder=6)
    ax.add_patch(Polygon([(5.38, 3.30), (6.62, 3.30), (6.92, 1.10),
                          (5.08, 1.10)], closed=True, fc="#ede7f6",
                         ec=C["vagina"], lw=2.0, zorder=3))
    ax.plot([CX, CX], [1.2, 3.3], color="white", lw=2.4, zorder=5)

    # ── Fallopian tubes + ovaries (mirrored) ──────────────────────────────────
    for s in (-1, 1):
        # The tube widens as it runs: narrow isthmus → wide ampulla → funnel.
        tube = np.array([
            (CX + s * 1.45, 7.10), (CX + s * 2.20, 7.50),
            (CX + s * 3.05, 7.90), (CX + s * 3.95, 8.18),
            (CX + s * 4.70, 8.25), (CX + s * 5.30, 8.18),
        ])
        for i, lw in enumerate((4.5, 6.0, 7.5, 9.0, 9.5)):
            ax.plot(tube[i:i + 2, 0], tube[i:i + 2, 1], color=C["fallopian"],
                    lw=lw, solid_capstyle="round", zorder=4)
        ovary_c = (CX + s * 4.75, 5.85)
        apex = (CX + s * 5.30, 8.15)
        m1 = (CX + s * 5.95, 6.60)          # funnel mouth, facing the ovary
        m2 = (CX + s * 4.10, 7.00)
        ax.add_patch(Polygon([apex, m1, m2], closed=True, fc="#f8bbd0",
                             ec=C["fallopian"], lw=1.8, zorder=5))
        for f in np.linspace(0.1, 0.9, 6):                            # fimbriae
            fx = m2[0] + f * (m1[0] - m2[0])
            fy = m2[1] + f * (m1[1] - m2[1])
            # Every fimbria reaches down towards the ovary it sweeps the egg from.
            dx, dy = ovary_c[0] - fx, ovary_c[1] - fy
            d = math.hypot(dx, dy) or 1.0
            ax.plot([fx, fx + 0.72 * dx / d], [fy, fy + 0.72 * dy / d],
                    color=C["fimbriae"], lw=1.8, zorder=6)
        ax.add_patch(Ellipse(ovary_c, 1.9, 1.2, angle=-s * 12,
                             fc="#e1bee7", ec=C["ovary_f"], lw=2.0, zorder=5))
        for ox, oy in ((-0.45, 0.14), (0.32, -0.22), (0.16, 0.30)):   # follicles
            ax.add_patch(Circle((ovary_c[0] + ox, ovary_c[1] + oy), 0.19,
                                fc="#fff9c4", ec=C["ovary_f"], lw=1.0, zorder=6))
        ax.plot([ovary_c[0] - s * 0.95, CX + s * 1.25], [5.80, 5.60],
                color="#8d6e63", lw=1.6, ls="--", zorder=3)           # ligament

    if not schema.show_labels:
        return
    labels = [
        ("Fallopian tube\n(oviduct)", (2.35, 7.75), (-3.6, 10.4), C["fallopian"],
         ("fallopian_tube", "oviduct")),
        ("Fimbriae", (1.05, 6.55), (-3.6, 8.5), C["fimbriae"], ("fimbriae",)),
        ("Ovary", (0.55, 5.85), (-3.6, 6.6), C["ovary_f"], ("ovary",)),
        ("Uterus", (4.80, 7.00), (-3.4, 4.6), "#c62828", ("uterus",)),
        ("Endometrium\n(inner lining)", (5.45, 5.85), (-3.2, 2.6),
         C["endometrium"], ("endometrium",)),
        ("Vagina", (5.30, 2.10), (0.8, 0.8), C["vagina"], ("vagina",)),
        ("Infundibulum", (10.85, 7.35), (15.6, 10.4), C["fallopian"],
         ("infundibulum",)),
        ("Ampulla", (9.95, 8.20), (15.6, 8.6), C["fallopian"], ("ampulla",)),
        ("Isthmus", (7.95, 7.35), (15.6, 6.6), C["fallopian"], ("isthmus",)),
        ("Perimetrium", (7.42, 6.90), (15.4, 4.6), "#546e7a",
         ("perimetrium",)),
        ("Myometrium\n(muscle wall)", (7.05, 5.55), (15.2, 2.8), "#c62828",
         ("myometrium",)),
        ("Cervix", (6.70, 3.85), (11.4, 0.8), C["cervix"], ("cervix",)),
    ]
    for text, xy, xytext, color, aliases in labels:
        _annotate(ax, text, xy, xytext, color, fontsize=9,
                  highlight=_is_hl(hl, *aliases))


# ═══════════════════════════════════════════════════════════════════════════════
# 23. Gametogenesis
# ═══════════════════════════════════════════════════════════════════════════════

# Counts and ploidy are declared once. The drawing, the badges and the summary
# caption all read from here, so the picture cannot contradict the arithmetic.
# `ploidy` is a multiple of the haploid set — the chromosome numbers printed on
# the diagram are derived from `diploid_number`, never supplied.
_GAMETOGENESIS: Dict[str, Dict[str, Any]] = {
    "spermatogenesis": {
        "site": "Seminiferous tubules of the testis",
        "stages": [
            {"name": "Spermatogonium\n(male germ cell)", "count": 1, "ploidy": 2,
             "kind": "cell"},
            {"name": "Primary spermatocyte", "count": 1, "ploidy": 2,
             "kind": "cell"},
            {"name": "Secondary spermatocytes", "count": 2, "ploidy": 1,
             "kind": "cell"},
            {"name": "Spermatids", "count": 4, "ploidy": 1, "kind": "cell"},
            {"name": "Spermatozoa (sperms)", "count": 4, "ploidy": 1,
             "kind": "sperm"},
        ],
        "arrows": [
            "Multiplication phase\n(MITOSIS)",
            "MEIOSIS I\n(reduction division) — EQUAL cytokinesis",
            "MEIOSIS II\n(equational) — EQUAL cytokinesis",
            "Spermiogenesis\n(spermatid → spermatozoon)",
        ],
        "functional_gametes": 4,
        "polar_bodies": 0,
        "cytokinesis": "equal",
    },
    "oogenesis": {
        "site": "Ovary (begins in the foetal ovary, completed after fertilisation)",
        "stages": [
            {"name": "Oogonium\n(female germ cell)", "count": 1, "ploidy": 2,
             "kind": "cell"},
            {"name": "Primary oocyte\n(arrested in prophase I)", "count": 1,
             "ploidy": 2, "kind": "cell"},
            {"name": "Secondary oocyte\n+ first polar body", "count": 1,
             "ploidy": 1, "kind": "oocyte", "polar": 1},
            {"name": "Ovum (egg)\n+ second polar body", "count": 1, "ploidy": 1,
             "kind": "ovum", "polar": 1},
        ],
        "arrows": [
            "Multiplication phase\n(MITOSIS, in the foetal ovary)",
            "MEIOSIS I — UNEQUAL cytokinesis\n(one large cell + a tiny polar body)",
            "MEIOSIS II — UNEQUAL cytokinesis\n(completed only after the sperm enters)",
        ],
        "functional_gametes": 1,
        "polar_bodies": 2,          # the first polar body may divide again → 3
        "cytokinesis": "unequal",
    },
}


def _sperm_glyph(ax, cx, cy, scale=1.0):
    ax.add_patch(Ellipse((cx, cy), 0.36 * scale, 0.24 * scale, angle=0,
                         fc="#bbdefb", ec=C["sperm"], lw=1.2, zorder=6))
    ax.add_patch(Circle((cx - 0.05 * scale, cy), 0.07 * scale,
                        fc=C["sperm"], ec="none", zorder=7))
    tx = np.linspace(cx + 0.18 * scale, cx + 0.95 * scale, 40)
    ty = cy + 0.09 * scale * np.sin(10 * (tx - cx) / scale)
    ax.plot(tx, ty, color=C["sperm"], lw=1.2, zorder=6)


def render_gametogenesis(data: Dict[str, Any],
                         canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = GametogenesisSchema(**data)
    spec = _GAMETOGENESIS[schema.process]
    stages = spec["stages"]

    two_n = schema.diploid_number
    n = two_n // 2                       # haploid set — derived, never supplied
    ploidy_text = {2: f"2n = {two_n}", 1: f"n = {n}"}
    ploidy_col = {2: C["ploidy_2n"], 1: C["ploidy_n"]}

    rows = len(stages)
    STEP = 3.0
    ys = [-i * STEP for i in range(rows)]
    x0, x1 = -8.0, 11.0
    y0, y1 = ys[-1] - 1.9, ys[0] + 1.9
    fig, ax = plt.subplots(figsize=(13.0, 13.0 * (y1 - y0) / (x1 - x0)))
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1)
    ax.set_aspect("equal"); ax.axis("off")

    for i, (stage, y) in enumerate(zip(stages, ys)):
        kind, count = stage["kind"], stage["count"]

        if kind == "sperm":
            for k in range(count):
                _sperm_glyph(ax, 1.4 + (k - (count - 1) / 2) * 1.75, y, 1.2)
        elif kind == "ovum":
            ax.add_patch(Circle((1.4, y), 0.98, fc="#fce4ec", ec=C["ovum"],
                                lw=1.2, ls="--", zorder=4))    # zona pellucida
            ax.add_patch(Circle((1.4, y), 0.75, fc="#f8bbd0", ec=C["ovum"],
                                lw=2.2, zorder=5))
            ax.add_patch(Circle((1.4, y + 0.12), 0.25, fc=C["ovum"],
                                ec="none", zorder=6))
            ax.add_patch(Circle((2.35, y + 0.85), 0.2, fc="#d7ccc8",
                                ec=C["polar_body"], lw=1.2, zorder=6))
            ax.text(2.75, y + 0.85, "2nd polar body (n)", fontsize=8.5,
                    color=C["polar_body"], va="center", zorder=6)
            ax.add_patch(Circle((-0.20, y + 0.90), 0.2, fc="#d7ccc8",
                                ec=C["polar_body"], lw=1.2, zorder=6))
            ax.add_patch(Circle((-0.80, y + 0.90), 0.2, fc="#d7ccc8",
                                ec=C["polar_body"], lw=1.0, ls=":", zorder=6))
            ax.text(-0.5, y + 1.55, "1st polar body\n(may divide)", fontsize=8,
                    color=C["polar_body"], ha="center", va="center", zorder=6)
        elif kind == "oocyte":
            ax.add_patch(Circle((1.4, y), 0.8, fc="#f8bbd0", ec=C["ovum"],
                                lw=2.0, zorder=5))
            ax.add_patch(Circle((1.4, y + 0.1), 0.25, fc=C["ovum"],
                                ec="none", zorder=6))
            ax.add_patch(Circle((2.30, y + 0.72), 0.2, fc="#d7ccc8",
                                ec=C["polar_body"], lw=1.2, zorder=6))
            ax.text(2.70, y + 0.72, "1st polar body (n)", fontsize=8.5,
                    color=C["polar_body"], va="center", zorder=6)
        else:
            for k in range(count):
                cx = 1.4 + (k - (count - 1) / 2) * (1.6 if count > 2 else 1.9)
                r = 0.66 if stage["ploidy"] == 2 else 0.52
                ax.add_patch(Circle((cx, y), r, fc="#e8eaf6",
                                    ec=C["germ_cell"], lw=2.0, zorder=5))
                ax.add_patch(Circle((cx, y), r * 0.42, fc=C["meiotic"],
                                    ec="none", alpha=0.75, zorder=6))

        ax.text(-2.7, y, stage["name"], ha="right", va="center", fontsize=10,
                fontweight="bold", color="#263238", zorder=6,
                bbox=dict(boxstyle="round,pad=0.3", fc="#f5f5f5",
                          ec="#90a4ae", lw=1.0))
        if schema.show_chromosome_number:
            p = stage["ploidy"]
            ax.text(7.4, y, ploidy_text[p], ha="center", va="center",
                    fontsize=11, fontweight="bold", color="white", zorder=6,
                    bbox=dict(boxstyle="round,pad=0.32", fc=ploidy_col[p],
                              ec="none"))
        ax.text(9.6, y, f"× {count}", ha="center", va="center", fontsize=10,
                color="#37474f", zorder=6)

        if i < rows - 1 and schema.show_labels:
            ax.add_patch(FancyArrowPatch((1.4, y - 1.05), (1.4, ys[i + 1] + 1.15),
                                         arrowstyle="-|>", mutation_scale=22,
                                         lw=2.2, color=C["meiotic"], zorder=4))
            ax.text(2.1, (y + ys[i + 1]) / 2, spec["arrows"][i],
                    ha="left", va="center", fontsize=8.5, color="#4527a0",
                    zorder=7,
                    bbox=dict(boxstyle="round,pad=0.25", fc="#ede7f6",
                              ec=C["meiotic"], lw=0.9))

    gam = spec["functional_gametes"]
    pb = spec["polar_bodies"]
    if pb:
        summary = (f"UNEQUAL cytokinesis: one primary oocyte → {gam} functional "
                   f"OVUM + {pb}–{pb + 1} polar bodies "
                   f"(the polar bodies degenerate)")
    else:
        summary = (f"EQUAL cytokinesis: one primary spermatocyte → {gam} "
                   f"functional SPERMATOZOA")
    ax.set_title(schema.title or
                 f"{schema.process.capitalize()} — {spec['site']}",
                 fontsize=14, fontweight="bold", pad=6)
    fig.text(0.5, 0.012, summary, ha="center", fontsize=10,
             color="#37474f", style="italic")
    fig.tight_layout(pad=0.4, rect=(0, 0.035, 1, 1))
    return _fig_to_svg(fig)


# ═══════════════════════════════════════════════════════════════════════════════
# 24. Embryo Sac (mature female gametophyte)
# ═══════════════════════════════════════════════════════════════════════════════

# 7 cells, 8 nuclei. Both totals are SUMMED from this table, so a cell added or
# removed here re-counts the caption automatically instead of contradicting it.
_EMBRYO_SAC_CELLS = [
    {"key": "antipodal", "name": "Antipodal cells", "cells": 3, "nuclei": 1,
     "end": "chalazal"},
    {"key": "central_cell", "name": "Central cell", "cells": 1, "nuclei": 2,
     "end": "centre"},
    {"key": "egg", "name": "Egg cell", "cells": 1, "nuclei": 1,
     "end": "micropylar"},
    {"key": "synergid", "name": "Synergids", "cells": 2, "nuclei": 1,
     "end": "micropylar"},
]


def _embryo_sac_counts() -> Tuple[int, int]:
    cells = sum(c["cells"] for c in _EMBRYO_SAC_CELLS)
    nuclei = sum(c["cells"] * c["nuclei"] for c in _EMBRYO_SAC_CELLS)
    return cells, nuclei


def render_embryo_sac(data: Dict[str, Any],
                      canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = EmbryoSacSchema(**data)
    n_cells, n_nuclei = _embryo_sac_counts()
    polar_nuclei = next(c["nuclei"] for c in _EMBRYO_SAC_CELLS
                        if c["key"] == "central_cell")

    fig, ax = plt.subplots(figsize=(12, 9.5))
    ax.set_xlim(-4.8, 15.2); ax.set_ylim(0.0, 11.6)
    ax.set_aspect("equal"); ax.axis("off")

    CX = 6.2
    # Nucellus + embryo sac. Micropylar end at the BOTTOM — the egg apparatus
    # always lies at the micropylar end, which is where the pollen tube arrives.
    ax.add_patch(Ellipse((CX, 6.0), 7.2, 10.0, fc="#f1f8e9", ec="#9ccc65",
                         lw=2.0, zorder=1))
    ax.add_patch(Ellipse((CX, 6.1), 5.0, 8.2, fc=C["embryo_sac"],
                         ec="#33691e", lw=2.4, zorder=2))
    ax.add_patch(Ellipse((CX, 6.3), 3.9, 5.0, fc=C["central_cell"],
                         ec="#4dd0e1", lw=1.4, zorder=3))     # central cell

    # ── Chalazal end: 3 antipodal cells ───────────────────────────────────────
    for dx, dy in ((-0.80, 8.75), (0.0, 9.35), (0.80, 8.75)):
        ax.add_patch(Circle((CX + dx, dy), 0.55, fc="#dcedc8",
                            ec=C["antipodal"], lw=1.8, zorder=5))
        ax.add_patch(Circle((CX + dx, dy), 0.19, fc=C["antipodal"],
                            ec="none", zorder=6))

    # ── Central cell: the two polar nuclei ────────────────────────────────────
    for dx in (-0.62, 0.62):
        ax.add_patch(Circle((CX + dx, 6.4), 0.42, fc="#ffe082",
                            ec=C["polar_nucleus"], lw=1.8, zorder=6))

    # ── Micropylar end: the egg apparatus (1 egg + 2 synergids) ───────────────
    for s in (-1, 1):
        ax.add_patch(Ellipse((CX + s * 1.30, 3.95), 1.25, 2.10, angle=-s * 8,
                             fc="#b2dfdb", ec=C["synergid"], lw=1.8, zorder=5))
        ax.add_patch(Circle((CX + s * 1.30, 4.35), 0.24, fc=C["synergid"],
                            ec="none", zorder=6))
        for k in np.linspace(-0.32, 0.32, 5):                 # filiform apparatus
            ax.plot([CX + s * 1.30 + k, CX + s * 1.30 + k * 1.2],
                    [3.30, 3.02], color=C["filiform"], lw=1.7, zorder=7)
    ax.add_patch(Ellipse((CX, 3.60), 1.5, 2.05, fc="#f8bbd0",
                         ec=C["egg_cell"], lw=2.2, zorder=6))
    ax.add_patch(Circle((CX, 4.05), 0.3, fc=C["egg_cell"], ec="none", zorder=7))
    ax.add_patch(Circle((CX, 3.20), 0.28, fc="white", ec=C["egg_cell"],
                        lw=0.8, zorder=7))                    # vacuole
    ax.plot([5.00, 5.42, 5.90], [1.50, 1.10, 1.42], color="#33691e",
            lw=2.6, zorder=4)                                 # micropyle notch

    if schema.show_double_fertilisation:
        # The pollen tube enters through the MICROPYLE (porogamy), is guided by
        # the filiform apparatus and bursts into ONE synergid — it never enters
        # the egg itself.
        tube = np.array([(-1.0, 0.85), (1.8, 0.95), (3.8, 1.02), (5.42, 1.12),
                         (6.05, 1.60), (5.85, 2.65), (5.20, 3.35)])
        ax.plot(tube[:, 0], tube[:, 1], color=C["pollen_tube"], lw=7,
                solid_capstyle="round", zorder=7)
        ax.plot(tube[:, 0], tube[:, 1], color="#f3e5f5", lw=3.4,
                solid_capstyle="round", zorder=8)
        for gx, gy in ((CX - 1.55, 3.85), (CX - 1.05, 3.85)):
            ax.add_patch(Circle((gx, gy), 0.22, fc=C["male_gamete"],
                                ec="#0d47a1", lw=1.0, zorder=9))
        ax.add_patch(FancyArrowPatch((CX - 0.90, 3.85), (CX - 0.45, 3.80),
                                     arrowstyle="-|>", mutation_scale=16,
                                     lw=2.2, color=C["zygote"], zorder=9))
        ax.add_patch(FancyArrowPatch((CX - 1.45, 4.15), (CX - 0.95, 6.15),
                                     arrowstyle="-|>", mutation_scale=16,
                                     lw=2.2, color=C["pen"],
                                     connectionstyle="arc3,rad=-0.3", zorder=9))
        zyg = 1 + 1                                # male gamete (n) + egg (n)
        pen = 1 + polar_nuclei                     # male gamete (n) + 2 polar (n)
        ax.text(11.9, 3.4,
                f"SYNGAMY\nmale gamete (n) + egg (n)\n→ ZYGOTE ({zyg}n)",
                ha="center", va="center", fontsize=9.5, color="white",
                fontweight="bold", zorder=10,
                bbox=dict(boxstyle="round,pad=0.4", fc=C["zygote"], ec="none"))
        ax.text(11.9, 6.9,
                f"TRIPLE FUSION\nmale gamete (n) + {polar_nuclei} polar nuclei "
                f"(n + n)\n→ PEN ({pen}n) → ENDOSPERM ({pen}n)",
                ha="center", va="center", fontsize=9.5, color="white",
                fontweight="bold", zorder=10,
                bbox=dict(boxstyle="round,pad=0.4", fc=C["pen"], ec="none"))
        ax.add_patch(FancyArrowPatch((9.85, 3.55), (7.2, 3.7), arrowstyle="-|>",
                                     mutation_scale=14, lw=1.4, ls="--",
                                     color=C["zygote"], zorder=8))
        ax.add_patch(FancyArrowPatch((9.85, 6.7), (7.3, 6.5), arrowstyle="-|>",
                                     mutation_scale=14, lw=1.4, ls="--",
                                     color=C["pen"], zorder=8))

    if schema.show_labels:
        _annotate(ax, "Antipodal cells (3)", (CX + 1.2, 9.0), (-2.6, 10.8),
                  C["antipodal"], fontsize=9.5)
        _annotate(ax, "Chalazal end", (CX + 0.4, 10.85), (10.6, 10.9), "#33691e",
                  fontsize=9.5)
        _annotate(ax, f"Polar nuclei ({polar_nuclei})", (CX + 0.9, 6.7),
                  (-2.8, 8.3), C["polar_nucleus"], fontsize=9.5)
        _annotate(ax, "Central cell", (CX - 1.75, 7.3), (-2.8, 6.0),
                  "#00838f", fontsize=9.5)
        _annotate(ax, "Nucellus", (CX + 3.2, 8.4), (10.9, 9.5), "#689f38",
                  fontsize=9.5)
        _annotate(ax, "Egg cell (n)", (CX + 0.55, 3.4), (-2.4, 3.6),
                  C["egg_cell"], fontsize=9.5)
        _annotate(ax, "Synergid", (CX + 1.55, 4.6), (10.5, 8.0),
                  C["synergid"], fontsize=9.5)
        _annotate(ax, "Filiform apparatus", (CX + 1.5, 3.1), (10.7, 1.6),
                  C["filiform"], fontsize=9.5)
        _annotate(ax, "Egg apparatus\n(1 egg + 2 synergids)", (CX - 1.95, 3.4),
                  (-2.6, 1.4), "#00695c", fontsize=9.5)
        _annotate(ax, "Micropylar end\n(micropyle)", (5.45, 1.15),
                  (2.6, 0.5), "#33691e", fontsize=9.5)
        if schema.show_double_fertilisation:
            _annotate(ax, "Pollen tube", (1.4, 0.92), (-0.8, 2.6),
                      C["pollen_tube"], fontsize=9.5)
            _annotate(ax, "Two male gametes (n)", (CX - 1.5, 4.1),
                      (0.8, 6.9), C["male_gamete"], fontsize=9.5)

    caption_bits = []
    if schema.show_nuclei_count:
        caption_bits.append(
            f"The mature embryo sac is {n_cells}-CELLED and {n_nuclei}-NUCLEATE"
        )
    if schema.show_double_fertilisation:
        caption_bits.append("DOUBLE FERTILISATION = syngamy + triple fusion "
                            "(unique to angiosperms)")
    ax.set_title(schema.title or
                 "Mature Embryo Sac — Female Gametophyte of an Angiosperm",
                 fontsize=14, fontweight="bold", pad=6)
    if caption_bits:
        fig.text(0.5, 0.015, "   |   ".join(caption_bits), ha="center",
                 fontsize=10, color="#37474f", style="italic")
        fig.tight_layout(pad=0.4, rect=(0, 0.04, 1, 1))
    else:
        fig.tight_layout(pad=0.4)
    return _fig_to_svg(fig)


# ═══════════════════════════════════════════════════════════════════════════════
# 25. Anther T.S.
# ═══════════════════════════════════════════════════════════════════════════════

# An anther is TETRASPORANGIATE — 4 microsporangia — at every stage. On
# dehiscence the two sporangia of a lobe fuse, so the CHAMBERS drop to 2 while
# the microsporangium count stays 4; the caption is built from both numbers.
_ANTHER_STAGE: Dict[str, Dict[str, Any]] = {
    "young": {
        "microsporangia": 4, "chambers": 4,
        "tapetum": True, "middle_layers": True, "content": "sporogenous",
        "dehisced": False,
        "caption": "Young anther — the sporangium is packed with SPOROGENOUS "
                   "TISSUE; the tapetum (innermost wall layer) nourishes the "
                   "developing microspores",
    },
    "mature": {
        "microsporangia": 4, "chambers": 4,
        "tapetum": False, "middle_layers": False, "content": "pollen",
        "dehisced": False,
        "caption": "Mature anther — microspore mother cells have completed "
                   "meiosis to give POLLEN GRAINS; the tapetum and middle "
                   "layers have degenerated",
    },
    "dehisced": {
        "microsporangia": 4, "chambers": 2,
        "tapetum": False, "middle_layers": False, "content": "pollen",
        "dehisced": True,
        "caption": "Dehisced anther — the two sporangia of each lobe have fused "
                   "into one chamber and the wall has split at the STOMIUM, "
                   "releasing the pollen",
    },
}

_ANTHER_WALL = [                       # outermost → innermost (the exam order)
    ("epidermis",     "Epidermis",     "epidermis",   1.20),
    ("endothecium",   "Endothecium",   "endothecium", 1.06),
    ("middle_layers", "Middle layers", "middle_layer", 0.94),
    ("tapetum",       "Tapetum",       "tapetum",     0.84),
]


def render_anther_ts(data: Dict[str, Any],
                     canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = AntherTSSchema(**data)
    hl = _norm(schema.highlight_layer)
    spec = _ANTHER_STAGE[schema.stage]

    fig, ax = plt.subplots(figsize=(12.5, 6.6))
    ax.set_xlim(-4.2, 16.2); ax.set_ylim(0.1, 10.7)
    ax.set_aspect("equal"); ax.axis("off")

    L, R, LOBE_R, WAIST = (3.6, 5.0), (8.4, 5.0), 2.45, 0.95
    outline = _bilobed_path(L, R, LOBE_R, WAIST)
    ax.add_patch(PathPatch(outline, fc=C["connective"], ec=C["epidermis"],
                           lw=3.2, zorder=2))

    # ── Connective tissue + vascular bundle in the mid-line ───────────────────
    ax.add_patch(Ellipse((6.0, 5.0), 1.35, 1.15, fc="#f1f8e9",
                         ec="#7cb342", lw=1.4, zorder=3))
    ax.add_patch(Circle((6.0, 5.25), 0.28, fc=C["xylem"], ec="#8e0000",
                        lw=1.0, zorder=4))
    ax.add_patch(Circle((6.0, 4.72), 0.26, fc=C["phloem"], ec="#0d47a1",
                        lw=1.0, zorder=4))

    if spec["dehisced"]:
        chambers = [(3.6, 5.0), (8.4, 5.0)]        # one fused chamber per lobe
        chamber_r = 1.55
    else:
        chambers = [(3.35, 6.35), (3.35, 3.65), (8.65, 6.35), (8.65, 3.65)]
        chamber_r = 1.18

    for cx, cy in chambers:
        # Wall layers, outermost first. The epidermis is the anther surface, so
        # inside each sporangium the outermost ring drawn is the endothecium.
        ax.add_patch(Circle((cx, cy), chamber_r, fc="#efebe9",
                            ec=C["endothecium"], lw=2.6, zorder=4))
        if spec["middle_layers"]:
            ax.add_patch(Circle((cx, cy), chamber_r * 0.88, fc="#d7ccc8",
                                ec=C["middle_layer"], lw=1.4, zorder=5))
        if spec["tapetum"]:
            ax.add_patch(Circle((cx, cy), chamber_r * 0.78, fc="#ffe0b2",
                                ec=C["tapetum"], lw=2.4, zorder=6))
            for k in range(12):                    # dense, nutritive tapetal cells
                tx, ty = _polar(cx, cy, chamber_r * 0.72, k * 30)
                ax.add_patch(Circle((tx, ty), 0.11, fc=C["tapetum"],
                                    ec="#e65100", lw=0.7, zorder=7))
        inner_r = chamber_r * (0.66 if spec["tapetum"] else 0.86)
        ax.add_patch(Circle((cx, cy), inner_r, fc="white", ec="#bdbdbd",
                            lw=0.8, zorder=7))

        if spec["content"] == "sporogenous":
            for gx, gy in ((-0.28, 0.28), (0.28, 0.28), (-0.28, -0.28),
                           (0.28, -0.28), (0.0, 0.0)):
                ax.add_patch(Circle((cx + gx * 1.5, cy + gy * 1.5), 0.24,
                                    fc="#d1c4e9", ec=C["sporogenous"],
                                    lw=1.2, zorder=8))
        else:
            step = 0.42 if not spec["dehisced"] else 0.5
            for gx in np.arange(-inner_r + 0.2, inner_r - 0.1, step):
                for gy in np.arange(-inner_r + 0.2, inner_r - 0.1, step):
                    if gx * gx + gy * gy > (inner_r - 0.22) ** 2:
                        continue
                    ax.add_patch(Circle((cx + gx, cy + gy), 0.16,
                                        fc=C["pollen_grain"], ec="#f57f17",
                                        lw=0.8, zorder=8))

    if spec["dehisced"]:
        # Dehiscence is a real BREAK in the wall: a background-coloured wedge is
        # cut from the chamber out through the epidermis at the stomium, so the
        # sporangium is genuinely open to the outside rather than merely marked.
        for s, lobe in ((-1, L), (1, R)):
            mid = 0 if s > 0 else 180
            th1, th2 = mid - 13, mid + 13
            r_in = chamber_r * 0.78
            ax.add_patch(Wedge(lobe, LOBE_R + 0.22, th1, th2,
                               width=LOBE_R + 0.22 - r_in, fc="white",
                               ec="none", zorder=8))
            for th in (th1, th2):
                ax.plot(*zip(_polar(*lobe, r_in, th),
                             _polar(*lobe, LOBE_R + 0.12, th)),
                        color=C["stomium"], lw=2.2, zorder=9)
            sx, _ = _polar(*lobe, LOBE_R, mid)
            for k in (-1, 0, 1):
                ax.add_patch(Circle((sx + s * 0.75, 5.0 + k * 0.42), 0.16,
                                    fc=C["pollen_grain"], ec="#f57f17",
                                    lw=0.8, zorder=9))
            ax.add_patch(FancyArrowPatch((sx + s * 0.25, 5.0),
                                         (sx + s * 1.45, 5.0),
                                         arrowstyle="-|>", mutation_scale=16,
                                         lw=1.8, color=C["stomium"], zorder=9))

    if schema.show_labels:
        # Every wall-layer arrow is aimed at the radius the layer is actually
        # drawn at, so a change to the chamber geometry cannot orphan a label.
        first = chambers[0]
        _annotate(ax, "Epidermis", _polar(*L, LOBE_R, 145), (-3.0, 10.2),
                  C["epidermis"], fontsize=9.5,
                  highlight=_is_hl(hl, "epidermis"))
        _annotate(ax, "Endothecium", _polar(*first, chamber_r, 135),
                  (-3.2, 8.7), C["endothecium"], fontsize=9.5,
                  highlight=_is_hl(hl, "endothecium"))
        if spec["middle_layers"]:
            _annotate(ax, "Middle layers",
                      _polar(*first, chamber_r * 0.88, 163), (-3.2, 7.2),
                      "#8d6e63", fontsize=9.5,
                      highlight=_is_hl(hl, "middle_layers", "middle_layer"))
        if spec["tapetum"]:
            _annotate(ax, "Tapetum\n(nourishes the microspores)",
                      _polar(*first, chamber_r * 0.78, 200), (-2.6, 5.4),
                      C["tapetum"], fontsize=9.5,
                      highlight=_is_hl(hl, "tapetum"))
        if spec["content"] == "sporogenous":
            _annotate(ax, "Sporogenous tissue\n(microspore mother cells)",
                      first, (-2.4, 3.0), C["sporogenous"], fontsize=9.5,
                      highlight=_is_hl(hl, "sporogenous_tissue",
                                       "sporogenous"))
        else:
            _annotate(ax, "Pollen grains\n(microspores)", first,
                      (-2.4, 3.0), "#f57f17", fontsize=9.5,
                      highlight=_is_hl(hl, "pollen", "pollen_grains",
                                       "microspores"))
        _annotate(ax, "Microsporangium\n(pollen sac)",
                  _polar(*chambers[-1], chamber_r * 0.5, 45), (13.4, 10.2),
                  "#6a1b9a", fontsize=9.5,
                  highlight=_is_hl(hl, "microsporangium", "pollen_sac"))
        _annotate(ax, "Connective tissue", (6.55, 5.75), (12.8, 8.4), "#558b2f",
                  fontsize=9.5, highlight=_is_hl(hl, "connective",
                                                 "connective_tissue"))
        _annotate(ax, "Vascular bundle\n(xylem + phloem)", (6.0, 4.9),
                  (13.2, 6.4), "#8e0000", fontsize=9.5,
                  highlight=_is_hl(hl, "vascular_bundle"))
        _annotate(ax, "Anther lobe", (9.9, 3.4), (13.6, 3.7), "#33691e",
                  fontsize=9.5, highlight=_is_hl(hl, "anther_lobe", "lobe"))
        if spec["dehisced"]:
            _annotate(ax, "Stomium\n(line of dehiscence)", (10.9, 5.0),
                      (13.2, 1.4), C["stomium"], fontsize=9.5,
                      highlight=_is_hl(hl, "stomium"))
        ax.text(6.0, 1.0,
                f"{spec['microsporangia']} microsporangia — the anther is "
                f"TETRASPORANGIATE and BILOBED",
                ha="center", fontsize=10, color="#4a148c", fontweight="bold")

    ax.set_title(schema.title or f"T.S. of a {schema.stage.capitalize()} Anther",
                 fontsize=14, fontweight="bold", pad=6)
    fig.text(0.5, 0.015, spec["caption"], ha="center", fontsize=9.5,
             color="#37474f", style="italic")
    fig.tight_layout(pad=0.4, rect=(0, 0.04, 1, 1))
    return _fig_to_svg(fig)


# ═══════════════════════════════════════════════════════════════════════════════
# 26. Sarcomere (sliding-filament model)
# ═══════════════════════════════════════════════════════════════════════════════

# Filament LENGTHS (µm) are properties of the filaments themselves and are
# therefore the same in both states — contraction slides them past one another,
# it does not shorten them. Every band width below is DERIVED from these three
# numbers, which is why the A band cannot come out shorter when the sarcomere
# shortens: the A band IS the thick filament.
_MYOSIN_LEN = 1.60          # thick filament  → defines the A band
_ACTIN_LEN = 0.95           # thin filament, anchored at a Z line
_SARCOMERE_LENGTH = {"relaxed": 2.40, "contracted": 2.10}


def _sarcomere_geometry(state: str) -> Dict[str, float]:
    """Band widths (µm) of one sarcomere, computed from the filament overlap."""
    L = _SARCOMERE_LENGTH[state]
    a_band = _MYOSIN_LEN                       # thick filament, end to end
    i_band = L - a_band                        # thin filament only, across a Z line
    overlap = _ACTIN_LEN - i_band / 2          # thin filament inside the A band
    h_zone = a_band - 2 * overlap              # thick filament only, mid A band
    if h_zone <= 0 or i_band <= 0:
        raise ValueError(
            f"sarcomere length {L} µm is not physically drawable with a "
            f"{a_band} µm thick and a {_ACTIN_LEN} µm thin filament"
        )
    return {"sarcomere_length": L, "a_band": a_band, "i_band": i_band,
            "h_zone": h_zone, "overlap": overlap}


def _draw_sarcomere_row(ax, state, y0, schema, scale=3.0):
    g = _sarcomere_geometry(state)
    L, A, I, H, OV = (g["sarcomere_length"], g["a_band"], g["i_band"],
                      g["h_zone"], g["overlap"])
    z = [0.0, L * scale, 2 * L * scale]        # three Z lines = two sarcomeres
    a_lo, a_hi = (L - A) / 2 * scale, (L + A) / 2 * scale
    h_lo, h_hi = (L / 2 - H / 2) * scale, (L / 2 + H / 2) * scale
    half = 0.78

    if schema.show_bands:
        for k in (0, 1):                       # both sarcomeres get their bands
            off = k * L * scale
            ax.add_patch(Rectangle((a_lo + off, y0 - half), A * scale, 2 * half,
                                   fc=C["band_a"], ec="none", zorder=1))
            ax.add_patch(Rectangle((h_lo + off, y0 - half), H * scale, 2 * half,
                                   fc=C["zone_h"], ec="none", zorder=2))
        ax.add_patch(Rectangle((a_hi, y0 - half), I * scale, 2 * half,
                               fc=C["band_i"], ec="none", zorder=1))
        for x0 in (0.0, z[2] - (L - A) / 2 * scale):   # the two half I bands
            ax.add_patch(Rectangle((x0, y0 - half), (L - A) / 2 * scale,
                                   2 * half, fc=C["band_i"], ec="none", zorder=1))

    for k in (0, 1):                           # thick filaments + cross-bridges
        off = k * L * scale
        for dy in (-0.36, 0.0, 0.36):
            ax.plot([a_lo + off, a_hi + off], [y0 + dy, y0 + dy],
                    color=C["myosin"], lw=5, solid_capstyle="round", zorder=5)
            # Cross-bridges only exist where a thin filament lies alongside the
            # thick one — i.e. exactly across the overlap, never in the H zone.
            for xb in np.arange(a_lo + off + 0.15, a_lo + off + OV * scale, 0.44):
                for s in (-1, 1):
                    ax.plot([xb, xb - 0.12], [y0 + dy, y0 + dy + s * 0.16],
                            color=C["cross_bridge"], lw=1.3, zorder=6)
            for xb in np.arange(a_hi + off - 0.15, a_hi + off - OV * scale, -0.44):
                for s in (-1, 1):
                    ax.plot([xb, xb + 0.12], [y0 + dy, y0 + dy + s * 0.16],
                            color=C["cross_bridge"], lw=1.3, zorder=6)
        ax.plot([(L / 2) * scale + off] * 2, [y0 - 0.5, y0 + 0.5],
                color=C["m_line"], lw=2.4, zorder=7)                    # M line

    for zx in z:                               # thin filaments run from a Z line
        for dy in (-0.54, -0.18, 0.18, 0.54):
            for s in (-1, 1):
                x_end = zx + s * _ACTIN_LEN * scale
                if x_end < -0.01 or x_end > z[2] + 0.01:
                    continue
                ax.plot([zx, x_end], [y0 + dy, y0 + dy], color=C["actin"],
                        lw=2.6, solid_capstyle="round", zorder=4)
        ax.plot([zx, zx], [y0 - 0.88, y0 + 0.88], color=C["z_line"],
                lw=4, zorder=8)                                         # Z line
    return g, z, (a_lo, a_hi), (h_lo, h_hi), half


def _sarcomere_brackets(ax, y0, z, a_span, h_span, half, g):
    a_lo, a_hi = a_span
    h_lo, h_hi = h_span
    # Two tiers, both ABOVE the row: the H zone sits inside the A band, so they
    # cannot share a line.
    for x0, x1, name, width, col, tier in (
        (h_lo, h_hi, "H zone", g["h_zone"], "#f9a825", 0.55),
        (a_lo, a_hi, "A band", g["a_band"], "#e65100", 1.55),
        (a_hi, z[1] + (z[1] - a_hi), "I band", g["i_band"], "#1565c0", 1.55),
    ):
        y = y0 + half + tier
        ax.add_patch(FancyArrowPatch((x0, y), (x1, y), arrowstyle="<|-|>",
                                     mutation_scale=12, lw=1.4, color=col,
                                     zorder=9))
        ax.text((x0 + x1) / 2, y + 0.12, f"{name} = {width:.2f} µm",
                ha="center", va="bottom", fontsize=9, color=col,
                fontweight="bold", zorder=9)


def render_sarcomere(data: Dict[str, Any],
                     canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = SarcomereSchema(**data)
    scale = 3.0
    states = (["relaxed", "contracted"] if schema.show_sliding_filament
              else [schema.state])

    width = 2 * _SARCOMERE_LENGTH["relaxed"] * scale
    y_last = -5.0 * (len(states) - 1)
    x0, x1 = -1.8, width + 5.6
    y0_lim, y1_lim = y_last - 4.4, 3.1
    fig, ax = plt.subplots(figsize=(13.5,
                                    13.5 * (y1_lim - y0_lim) / (x1 - x0)))
    ax.set_xlim(x0, x1); ax.set_ylim(y0_lim, y1_lim)
    ax.set_aspect("equal"); ax.axis("off")

    geoms = {}
    for i, state in enumerate(states):
        y0 = -5.0 * i
        g, z, a_span, h_span, half = _draw_sarcomere_row(ax, state, y0, schema,
                                                         scale)
        geoms[state] = g
        if schema.show_bands and schema.show_labels:
            _sarcomere_brackets(ax, y0, z, a_span, h_span, half, g)
        ax.text(width + 0.8, y0,
                f"{state.upper()}\n{g['sarcomere_length']:.2f} µm",
                ha="left", va="center", fontsize=10.5, fontweight="bold",
                color="#37474f",
                bbox=dict(boxstyle="round,pad=0.3", fc="#eceff1",
                          ec="#90a4ae", lw=1.0))

    if schema.show_labels:
        last = states[-1]
        L = _SARCOMERE_LENGTH[last]
        a_lo = (L - _MYOSIN_LEN) / 2 * scale
        _annotate(ax, "Z line", (0.0, y_last - 0.9), (-0.4, y_last - 2.5),
                  C["z_line"], fontsize=9.5)
        _annotate(ax, "Actin (thin filament)", (0.7, y_last - 0.54),
                  (3.6, y_last - 2.5), C["actin"], fontsize=9.5)
        _annotate(ax, "Cross bridge", (a_lo + 0.35, y_last - 0.5),
                  (9.0, y_last - 2.5), C["cross_bridge"], fontsize=9.5)
        _annotate(ax, "Myosin (thick filament)", (L / 2 * scale + 1.0,
                                                  y_last - 0.36),
                  (15.0, y_last - 2.5), C["myosin"], fontsize=9.5)
        _annotate(ax, "M line", (L / 2 * scale, y_last - 0.5),
                  (6.6, y_last - 3.8), C["m_line"], fontsize=9.5)

    if schema.show_sliding_filament:
        rel, con = geoms["relaxed"], geoms["contracted"]
        note = (
            f"SLIDING FILAMENT: sarcomere {rel['sarcomere_length']:.2f} → "
            f"{con['sarcomere_length']:.2f} µm.  "
            f"I band {rel['i_band']:.2f} → {con['i_band']:.2f} µm (SHORTENS)  |  "
            f"H zone {rel['h_zone']:.2f} → {con['h_zone']:.2f} µm (SHORTENS)  |  "
            f"A band {rel['a_band']:.2f} → {con['a_band']:.2f} µm (UNCHANGED — "
            f"the filaments slide, they do not shorten)"
        )
    else:
        g = geoms[states[0]]
        note = (f"{states[0].capitalize()} sarcomere: A band {g['a_band']:.2f} µm "
                f"(= the thick filament)  |  I band {g['i_band']:.2f} µm  |  "
                f"H zone {g['h_zone']:.2f} µm  |  overlap {g['overlap']:.2f} µm "
                f"per half-sarcomere")
    ax.set_title(schema.title or "Sarcomere — Ultrastructure of a Myofibril",
                 fontsize=14, fontweight="bold", pad=6)
    fig.text(0.5, 0.015, note, ha="center", fontsize=9, color="#37474f",
             style="italic")
    fig.tight_layout(pad=0.4, rect=(0, 0.045, 1, 1))
    return _fig_to_svg(fig)


# ═══════════════════════════════════════════════════════════════════════════════
# 27. Population Growth
# ═══════════════════════════════════════════════════════════════════════════════

def _exp_growth(t, r, N0):
    return N0 * np.exp(r * t)


def _logistic_growth(t, r, N0, K):
    return K / (1.0 + ((K - N0) / N0) * np.exp(-r * t))


def _logistic_rate(N, r, K):
    """dN/dt = rN(K − N)/K — a downward parabola in N, so it peaks at N = K/2."""
    return r * N * (K - N) / K


def _t_of_N(N, r, N0, K):
    """Invert the logistic curve — used to place the phase boundaries and K/2."""
    return (1.0 / r) * math.log((N * (K - N0)) / (N0 * (K - N)))


def render_population_growth(data: Dict[str, Any],
                             canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = PopulationGrowthSchema(**data)
    r, N0, K = schema.r, schema.N0, schema.K
    y_max = K * 1.25

    if schema.model == "exponential":
        t_end = min(schema.t_max, math.log(y_max / N0) / r)
    else:
        t_end = schema.t_max

    fig, ax = plt.subplots(figsize=(11, 7.2))
    t = np.linspace(0, t_end, 600)

    if schema.model in ("logistic", "both"):
        N_log = _logistic_growth(t, r, N0, K)
        t_half = _t_of_N(K / 2, r, N0, K)              # the inflection point

        if schema.show_phases:
            t_lag = _t_of_N(0.10 * K, r, N0, K)
            t_stat = _t_of_N(0.90 * K, r, N0, K)
            for x0, x1, col, name in (
                (0, t_lag, C["phase_lag"], "Lag\nphase"),
                (t_lag, t_stat, C["phase_log"], "Log (exponential)\nphase"),
                (t_stat, t_end, C["phase_stat"], "Stationary\nphase"),
            ):
                ax.axvspan(x0, x1, color=col, zorder=0)
                ax.text((x0 + x1) / 2, y_max * 0.06, name, ha="center",
                        va="center", fontsize=9, color="#455a64", style="italic")

        ax.axhline(K, color=C["carrying_cap"], lw=1.8, ls="--", zorder=3)
        ax.text(t_end * 0.985, K + y_max * 0.02,
                f"Carrying capacity  K = {K:g}", ha="right", va="bottom",
                fontsize=10, color=C["carrying_cap"], fontweight="bold")
        ax.plot(t, N_log, color=C["curve_log"], lw=3.0, zorder=5,
                label="Logistic (S-shaped / sigmoid):  dN/dt = rN(K−N)/K")

        ax.axhline(K / 2, color=C["half_k"], lw=1.0, ls=":", zorder=3)
        ax.plot([t_half], [K / 2], "o", ms=9, color=C["half_k"], zorder=6)
        ax.annotate(
            f"N = K/2 = {K / 2:g}\nPOINT OF INFLECTION —\ngrowth rate dN/dt is MAXIMUM here",
            xy=(t_half, K / 2), xytext=(t_half + t_end * 0.10, K * 0.30),
            fontsize=9.5, color=C["half_k"], ha="left",
            bbox=dict(boxstyle="round,pad=0.3", fc="#f3e5f5",
                      ec=C["half_k"], lw=1.0),
            arrowprops=dict(arrowstyle="-|>", color=C["half_k"], lw=1.2),
        )

    if schema.model in ("exponential", "both"):
        N_exp = np.clip(_exp_growth(t, r, N0), 0, y_max * 1.02)
        ax.plot(t, N_exp, color=C["curve_exp"], lw=3.0, zorder=5,
                label="Exponential (J-shaped):  dN/dt = rN")
        t_top = min(t_end, math.log(y_max / N0) / r)
        ax.text(t_top, y_max * 0.97, "J-shaped —\nno upper limit",
                ha="right", va="top", fontsize=9.5, color=C["curve_exp"],
                fontweight="bold")

    ax.set_xlim(0, t_end); ax.set_ylim(0, y_max)
    ax.set_xlabel("Time (t)", fontsize=11)
    ax.set_ylabel("Population size (N)", fontsize=11)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(alpha=0.18, zorder=0)
    if schema.show_equations:
        ax.legend(loc="lower right", fontsize=9.5, framealpha=0.95)
    ax.text(t_end * 0.012, N0 + y_max * 0.035, f"N₀ = {N0:g}", fontsize=9,
            color="#37474f", va="bottom", ha="left")

    titles = {
        "exponential": "Exponential (Geometric) Population Growth",
        "logistic": "Logistic (Verhulst–Pearl) Population Growth",
        "both": "Exponential vs Logistic Population Growth",
    }
    notes = {
        "exponential": "dN/dt = rN — unlimited resources, J-shaped; "
                       "no habitat can supply them, so this is unrealistic",
        "logistic": "dN/dt = rN(K−N)/K — sigmoid; growth is FASTEST at N = K/2 "
                    "and STOPS (dN/dt = 0) when N reaches K",
        "both": "Exponential growth is unbounded (J); logistic growth levels off "
                "at the carrying capacity K (S) — growth is fastest at N = K/2",
    }
    ax.set_title(schema.title or titles[schema.model],
                 fontsize=14, fontweight="bold", pad=8)
    fig.text(0.5, 0.015, notes[schema.model], ha="center", fontsize=9.5,
             color="#37474f", style="italic")
    fig.tight_layout(pad=0.6, rect=(0, 0.05, 1, 1))
    return _fig_to_svg(fig)


# ═══════════════════════════════════════════════════════════════════════════════
# 28. lac Operon
# ═══════════════════════════════════════════════════════════════════════════════

# The gene order i – p – o – z – y – a is itself the question, so the boxes, the
# structural-gene bracket and the caption are all built from this one list.
_LAC_GENES = [
    ("i", "i", "Regulator gene\n(makes the repressor)", 0.30, 2.20, "gene_i"),
    ("p", "p", "Promoter\n(RNA polymerase binds)", 3.10, 4.30, "gene_p"),
    ("o", "o", "Operator\n(repressor binds)", 4.40, 5.60, "gene_o"),
    ("z", "z", "β-galactosidase", 5.80, 7.90, "gene_z"),
    ("y", "y", "Permease", 8.00, 9.60, "gene_y"),
    ("a", "a", "Transacetylase", 9.70, 11.30, "gene_a"),
]
_LAC_STRUCTURAL = ("z", "y", "a")

_LAC_STATE: Dict[str, Dict[str, Any]] = {
    "repressed_off": {
        "repressor_on_operator": True,
        "transcription": False,
        "inducer_present": False,
        "title": "lac Operon — SWITCHED OFF (lactose absent)",
        "caption": "Lactose ABSENT → the active repressor binds the OPERATOR → "
                   "RNA polymerase cannot move past it → z, y and a are not "
                   "transcribed. The lac operon is a NEGATIVELY regulated, "
                   "INDUCIBLE operon.",
    },
    "inducible_on": {
        "repressor_on_operator": False,
        "transcription": True,
        "inducer_present": True,
        "title": "lac Operon — SWITCHED ON (lactose present)",
        "caption": "Lactose → allolactose (the INDUCER) binds the repressor and "
                   "inactivates it → the operator is free → RNA polymerase "
                   "transcribes z, y and a as ONE polycistronic mRNA.",
    },
}


def _repressor_shape(cx, cy, scale=1.0):
    pts = [(-0.62, 0.34), (0.62, 0.34), (0.62, -0.12), (0.22, -0.12),
           (0.0, -0.44), (-0.22, -0.12), (-0.62, -0.12)]
    return Polygon([(cx + x * scale, cy + y * scale) for x, y in pts],
                   closed=True, fc="#d1c4e9", ec=C["repressor"], lw=2.0,
                   zorder=8)


def _cross(ax, cx, cy, size=0.28, color=None, lw=3.4):
    """A drawn ✗. Never a glyph — a missing font would silently drop the mark
    that carries the whole 'this cannot happen' meaning."""
    col = color or C["blocked"]
    ax.plot([cx - size, cx + size], [cy - size, cy + size], color=col, lw=lw,
            solid_capstyle="round", zorder=10)
    ax.plot([cx - size, cx + size], [cy + size, cy - size], color=col, lw=lw,
            solid_capstyle="round", zorder=10)


def render_lac_operon(data: Dict[str, Any],
                      canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = LacOperonSchema(**data)
    spec = _LAC_STATE[schema.state]

    fig, ax = plt.subplots(figsize=(13.5, 8.6))
    ax.set_xlim(-1.4, 13.6); ax.set_ylim(-1.2, 9.4)
    ax.axis("off")

    DNA_Y = 6.0
    boxes = {k: (x0, x1) for k, _, _, x0, x1, _ in _LAC_GENES}
    for dy in (-0.32, 0.32):
        ax.plot([-0.6, 12.1], [DNA_Y + dy, DNA_Y + dy], color=C["dna_bar"],
                lw=2.0, zorder=2)
    for key, sym, name, x0, x1, col in _LAC_GENES:
        ax.add_patch(Rectangle((x0, DNA_Y - 0.32), x1 - x0, 0.64,
                               fc=C[col], ec="#263238", lw=1.2, zorder=3))
        ax.text((x0 + x1) / 2, DNA_Y, sym, ha="center", va="center",
                fontsize=13, fontweight="bold", color="white", zorder=4,
                style="italic")
        if schema.show_labels:
            ax.text((x0 + x1) / 2, DNA_Y - 0.75, name, ha="center", va="top",
                    fontsize=8.5, color=C[col], zorder=4)
    ax.text(12.4, DNA_Y, "DNA", ha="left", va="center", fontsize=10,
            color=C["dna_bar"], fontweight="bold")

    zx0 = boxes["z"][0]
    ax0 = boxes["a"][1]
    ax.add_patch(FancyArrowPatch((zx0, DNA_Y + 0.95), (ax0, DNA_Y + 0.95),
                                 arrowstyle="<|-|>", mutation_scale=12, lw=1.3,
                                 color="#0d47a1", zorder=4))
    ax.text((zx0 + ax0) / 2, DNA_Y + 1.15, "Structural genes (polycistronic)",
            ha="center", fontsize=9, color="#0d47a1", fontweight="bold")

    # ── The repressor is made from i whatever the state ───────────────────────
    ax.add_patch(FancyArrowPatch((1.25, DNA_Y - 1.55), (1.25, 3.55),
                                 arrowstyle="-|>", mutation_scale=16, lw=1.6,
                                 color=C["repressor"], zorder=4))
    ax.text(1.45, 4.2, "transcription\n+ translation", fontsize=8,
            color=C["repressor"], ha="left", va="center")

    op_c = ((boxes["o"][0] + boxes["o"][1]) / 2, DNA_Y)
    pr_c = ((boxes["p"][0] + boxes["p"][1]) / 2, DNA_Y)

    if spec["repressor_on_operator"]:
        # OFF — the repressor is sitting ON the operator, physically in the way.
        ax.add_patch(_repressor_shape(op_c[0], DNA_Y + 0.78, 1.25))
        ax.text(op_c[0], DNA_Y + 0.95, "Repressor", ha="center", va="center",
                fontsize=8.5, color=C["repressor"], fontweight="bold", zorder=9)
        ax.add_patch(_repressor_shape(1.25, 3.1, 1.25))
        ax.text(1.25, 3.25, "Repressor\n(ACTIVE)", ha="center", va="center",
                fontsize=8, color=C["repressor"], fontweight="bold", zorder=9)
        ax.add_patch(FancyArrowPatch((1.95, 3.55), (op_c[0] - 0.6, DNA_Y + 0.35),
                                     arrowstyle="-|>", mutation_scale=16, lw=1.8,
                                     color=C["repressor"],
                                     connectionstyle="arc3,rad=-0.25", zorder=6))
        ax.text(3.1, 4.35, "binds the operator", fontsize=9,
                color=C["repressor"], ha="center", fontweight="bold")

        # RNA polymerase binds the promoter but cannot advance: the repressor
        # sitting on the operator physically blocks its path along the DNA.
        rna_c = (pr_c[0] - 0.3, DNA_Y + 2.05)
        ax.add_patch(Ellipse(rna_c, 1.95, 1.05, fc="#c8e6c9",
                             ec=C["rna_pol"], lw=2.0, zorder=7))
        ax.text(rna_c[0], rna_c[1], "RNA\npolymerase", ha="center", va="center",
                fontsize=8, color="#1b5e20", fontweight="bold", zorder=8)
        ax.add_patch(FancyArrowPatch((rna_c[0] + 0.7, rna_c[1] - 0.7),
                                     (boxes["o"][0] + 0.02, DNA_Y + 0.95),
                                     arrowstyle="-|>", mutation_scale=15, lw=1.8,
                                     color=C["blocked"],
                                     connectionstyle="arc3,rad=-0.12", zorder=8))
        _cross(ax, boxes["o"][0] + 0.05, DNA_Y + 1.15, size=0.24)
        ax.text(8.7, DNA_Y + 1.95, "RNA polymerase is BLOCKED —\n"
                "it cannot move past the repressor", fontsize=9.5,
                color=C["blocked"], ha="center", va="center", fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.35", fc="#ffebee",
                          ec=C["blocked"], lw=1.0))
        ax.text(8.7, 2.9, "NO mRNA  →  NO enzymes\n(the operon is OFF)",
                ha="center", va="center", fontsize=12.5, color=C["blocked"],
                fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.5", fc="#ffebee",
                          ec=C["blocked"], lw=1.6))
    else:
        # ON — the inducer has changed the repressor's shape, so it can no
        # longer sit on the operator and the operator stays free.
        ax.add_patch(_repressor_shape(1.25, 3.1, 1.25))
        ax.text(1.25, 3.25, "Repressor\n(INACTIVE)", ha="center", va="center",
                fontsize=8, color=C["repressor"], fontweight="bold", zorder=9)
        ax.add_patch(Circle((2.3, 2.75), 0.34, fc="#ffe082", ec=C["inducer"],
                            lw=1.8, zorder=9))
        ax.text(2.3, 1.95, "Allolactose\n(INDUCER,\nfrom lactose)", ha="center",
                va="center", fontsize=8.5, color=C["inducer"], fontweight="bold")
        ax.add_patch(FancyArrowPatch((2.1, 3.9), (op_c[0] - 0.4, DNA_Y + 0.5),
                                     arrowstyle="-|>", mutation_scale=14, lw=1.6,
                                     ls="--", color="#9e9e9e",
                                     connectionstyle="arc3,rad=-0.3", zorder=6))
        _cross(ax, 3.5, 4.85, size=0.26)
        ax.text(3.5, 4.25, "cannot bind\nthe operator", fontsize=8.5,
                color=C["blocked"], ha="center", va="center", fontweight="bold")

        ax.add_patch(Ellipse((pr_c[0], DNA_Y + 1.35), 1.9, 1.1, fc="#c8e6c9",
                             ec=C["rna_pol"], lw=2.0, zorder=7))
        ax.text(pr_c[0], DNA_Y + 1.35, "RNA\npolymerase", ha="center",
                va="center", fontsize=8, color="#1b5e20", fontweight="bold",
                zorder=8)
        ax.add_patch(FancyArrowPatch((pr_c[0] + 1.0, DNA_Y + 1.35),
                                     (ax0, DNA_Y + 1.35), arrowstyle="-|>",
                                     mutation_scale=18, lw=2.2,
                                     color=C["rna_pol"], zorder=7))
        ax.text((pr_c[0] + ax0) / 2 + 0.6, DNA_Y + 1.75, "transcription proceeds",
                ha="center", fontsize=9.5, color=C["rna_pol"], fontweight="bold")

        mx = np.linspace(zx0, ax0, 200)
        ax.plot(mx, 3.9 + 0.13 * np.sin(6 * mx), color=C["mrna"], lw=3.0,
                zorder=6)
        ax.text(ax0 + 0.25, 3.9, "polycistronic\nmRNA", ha="left", va="center",
                fontsize=9, color=C["mrna"], fontweight="bold")
        for key, sym, name, x0, x1, col in _LAC_GENES:
            if key not in _LAC_STRUCTURAL:
                continue
            cx = (x0 + x1) / 2
            ax.add_patch(FancyArrowPatch((cx, DNA_Y - 1.55), (cx, 3.65),
                                         arrowstyle="-|>", mutation_scale=14,
                                         lw=1.4, color=C["mrna"], zorder=5))
            if schema.show_products:
                ax.add_patch(Ellipse((cx, 2.2), 1.9, 0.95, fc="#e1f5fe",
                                     ec=C[col], lw=1.8, zorder=6))
                ax.text(cx, 2.2, name, ha="center", va="center", fontsize=8.5,
                        color=C[col], fontweight="bold", zorder=7)
        if schema.show_products:
            ax.text((zx0 + ax0) / 2, 1.15, "translation → the three enzymes of "
                    "lactose metabolism", ha="center", fontsize=9.5,
                    color="#0d47a1", style="italic")

    ax.set_title(schema.title or spec["title"], fontsize=14,
                 fontweight="bold", pad=8)
    fig.text(0.5, 0.015, _wrap(spec["caption"], 110), ha="center", fontsize=9.5,
             color="#37474f", style="italic")
    fig.tight_layout(pad=0.4, rect=(0, 0.06, 1, 1))
    return _fig_to_svg(fig)


# ═══════════════════════════════════════════════════════════════════════════════
# 29. Microbe Structure
# ═══════════════════════════════════════════════════════════════════════════════

_MICROBE_TITLE = {
    "bacteriophage": "Bacteriophage (T₄) — Structure",
    "bacterium": "Bacterial Cell (Prokaryote) — Structure",
    "virus_tmv": "Tobacco Mosaic Virus (TMV) — Structure",
    "virus_hiv": "Human Immunodeficiency Virus (HIV) — Structure",
}
_MICROBE_NOTE = {
    "bacteriophage": "A tailed DNA virus that infects bacteria — it injects its "
                     "DNA through the tail and leaves the capsid outside",
    "bacterium": "A PROKARYOTE — no nuclear membrane and no membrane-bound "
                 "organelles; ribosomes are 70S",
    "virus_tmv": "HELICAL capsid of protein capsomeres wound around a single "
                 "strand of RNA (ssRNA) — a rod-shaped plant virus",
    "virus_hiv": "An enveloped RETROVIRUS: two copies of (+) ssRNA plus reverse "
                 "transcriptase inside a cone-shaped capsid",
}


def render_microbe_structure(data: Dict[str, Any],
                             canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = MicrobeStructureSchema(**data)
    hl = _norm(schema.highlight_part)

    fig, ax = plt.subplots(figsize=(12, 9))
    ax.set_aspect("equal"); ax.axis("off")

    drawer = {
        "bacteriophage": _draw_bacteriophage,
        "bacterium": _draw_bacterium,
        "virus_tmv": _draw_tmv,
        "virus_hiv": _draw_hiv,
    }[schema.microbe]
    drawer(ax, schema, hl)

    ax.set_title(schema.title or _MICROBE_TITLE[schema.microbe],
                 fontsize=14, fontweight="bold", pad=6)
    fig.text(0.5, 0.015, _MICROBE_NOTE[schema.microbe], ha="center",
             fontsize=9.5, color="#37474f", style="italic")
    fig.tight_layout(pad=0.4, rect=(0, 0.04, 1, 1))
    return _fig_to_svg(fig)


def _draw_bacteriophage(ax, schema, hl):
    ax.set_xlim(-4.0, 14.0); ax.set_ylim(-1.4, 12.2)
    CX = 5.0

    head = [(CX - 1.5, 9.4), (CX, 10.9), (CX + 1.5, 9.4), (CX + 1.5, 7.6),
            (CX, 6.9), (CX - 1.5, 7.6)]
    ax.add_patch(Polygon(head, closed=True, fc="#ede7f6", ec=C["capsid"],
                         lw=2.6, zorder=3))
    dx = np.linspace(CX - 1.0, CX + 1.0, 200)                      # packed DNA
    for k, amp in ((0, 0.55), (1, 0.35)):
        ax.plot(dx, 8.9 - k * 0.9 + amp * np.sin(7 * (dx - CX) + k),
                color=C["phage_dna"], lw=1.6, zorder=4)

    ax.add_patch(Rectangle((CX - 0.55, 6.5), 1.1, 0.42, fc="#b2ebf2",
                           ec=C["collar"], lw=1.8, zorder=4))       # collar
    ax.add_patch(Rectangle((CX - 0.48, 3.6), 0.96, 2.9, fc="#ffe0b2",
                           ec=C["sheath"], lw=2.0, zorder=3))       # sheath
    for y in np.arange(3.85, 6.5, 0.36):                            # striations
        ax.plot([CX - 0.48, CX + 0.48], [y, y], color=C["sheath"], lw=1.0,
                zorder=4)
    ax.plot([CX, CX], [3.6, 6.5], color=C["tail_core"], lw=2.4, zorder=5)

    ax.add_patch(Polygon([(CX - 1.25, 3.55), (CX + 1.25, 3.55),
                          (CX + 0.95, 3.0), (CX - 0.95, 3.0)], closed=True,
                         fc="#cfd8dc", ec=C["base_plate"], lw=2.0, zorder=5))
    for s in (-1, 1):                                               # tail fibres
        for k, (bx, kink) in enumerate(((0.95, 1.9), (0.55, 1.35))):
            ax.plot([CX + s * bx, CX + s * (bx + kink), CX + s * (bx + kink + 0.5)],
                    [3.0, 2.0, 0.4], color=C["tail_fibre"], lw=2.0,
                    solid_capstyle="round", zorder=4)
        ax.plot([CX + s * 0.8, CX + s * 0.95], [3.0, 2.45],
                color=C["base_plate"], lw=2.2, zorder=5)            # tail pins

    if not schema.show_labels:
        return
    for text, xy, xytext, col, aliases in (
        ("Head (capsid)", (CX - 1.2, 9.9), (-2.6, 11.6), C["capsid"],
         ("head", "capsid")),
        ("DNA (genetic material)", (CX + 0.5, 8.9), (10.6, 11.4),
         C["phage_dna"], ("dna", "genetic_material")),
        ("Collar", (CX + 0.55, 6.7), (10.4, 9.0), C["collar"], ("collar",)),
        ("Sheath (contractile)", (CX + 0.48, 5.6), (10.6, 7.2), C["sheath"],
         ("sheath",)),
        ("Tail core (hollow)", (CX, 4.6), (-2.4, 6.6), C["tail_core"],
         ("tail_core", "core")),
        ("Base plate", (CX + 1.0, 3.3), (10.2, 4.6), C["base_plate"],
         ("base_plate",)),
        ("Tail pin", (CX - 0.92, 2.5), (-2.6, 3.4), C["base_plate"],
         ("tail_pin", "pin")),
        ("Tail fibres", (CX + 2.6, 1.6), (10.0, 1.8), C["tail_fibre"],
         ("tail_fibre", "tail_fibres")),
    ):
        _annotate(ax, text, xy, xytext, col, fontsize=9.5,
                  highlight=_is_hl(hl, *aliases))


def _draw_bacterium(ax, schema, hl):
    ax.set_xlim(-4.4, 15.6); ax.set_ylim(-1.0, 10.0)
    CX, CY = 5.6, 4.8

    ax.add_patch(Ellipse((CX, CY), 9.4, 5.6, fc="#e1f5fe", ec="#4fc3f7",
                         lw=2.2, ls="--", zorder=2))               # capsule
    ax.add_patch(Ellipse((CX, CY), 8.6, 4.9, fc="#e8f5e9", ec=C["cell_wall_b"],
                         lw=3.0, zorder=3))                        # cell wall
    ax.add_patch(Ellipse((CX, CY), 8.2, 4.5, fc="#fffde7",
                         ec=C["cell_membrane"], lw=2.0, zorder=4))  # membrane

    nx = np.linspace(CX - 1.9, CX + 1.9, 300)                      # nucleoid
    ax.plot(nx, CY + 0.75 * np.sin(3.2 * (nx - CX)) * np.cos(1.1 * (nx - CX)),
            color=C["nucleoid"], lw=2.6, zorder=6)
    ax.add_patch(Ellipse((CX, CY), 4.6, 2.5, fc="none", ec=C["nucleoid"],
                         lw=1.0, ls=":", zorder=5))
    for px, py in ((CX + 2.9, CY + 1.2), (CX - 3.0, CY - 1.1)):    # plasmids
        ax.add_patch(Circle((px, py), 0.42, fc="none", ec=C["bact_plasmid"],
                            lw=2.2, zorder=6))
    for k in range(26):                                            # 70S ribosomes
        a = k * 137.5
        rr = 1.1 + 2.6 * ((k % 7) / 7.0)
        rx, ry = _polar(CX, CY, rr, a)
        if (rx - CX) ** 2 / 15.0 + (ry - CY) ** 2 / 4.6 > 1:
            continue
        ax.add_patch(Circle((rx, ry), 0.11, fc=C["ribosome"], ec="none",
                            zorder=6))
    mth = np.linspace(0, 2.6 * np.pi, 120)                         # mesosome
    ax.plot(CX - 2.6 + 0.45 * np.sin(mth) * (1 - mth / 9),
            CY + 2.15 - 0.16 * mth, color=C["mesosome"], lw=2.0, zorder=6)

    fx = np.linspace(CX + 4.3, CX + 8.0, 200)                      # flagellum
    ax.plot(fx, CY + 0.55 * np.sin(3.4 * (fx - CX - 4.3)), color=C["flagellum"],
            lw=2.6, zorder=3)
    for a in range(150, 215, 12):                                  # pili/fimbriae
        x0, y0 = CX + 4.3 * math.cos(math.radians(a)), \
            CY + 2.45 * math.sin(math.radians(a))
        x1, y1 = CX + 5.2 * math.cos(math.radians(a)), \
            CY + 3.1 * math.sin(math.radians(a))
        ax.plot([x0, x1], [y0, y1], color=C["pili"], lw=1.6, zorder=3)

    if not schema.show_labels:
        return
    for text, xy, xytext, col, aliases in (
        ("Capsule (glycocalyx)", (CX - 1.6, 7.5), (-2.8, 9.4), "#0288d1",
         ("capsule", "glycocalyx")),
        ("Cell wall", (CX + 1.2, 7.15), (3.4, 9.4), C["cell_wall_b"],
         ("cell_wall",)),
        ("Plasma membrane", (CX + 2.9, 6.55), (9.8, 9.4), C["cell_membrane"],
         ("plasma_membrane", "cell_membrane", "membrane")),
        ("Nucleoid\n(circular DNA, no nuclear membrane)", (CX + 0.9, 5.2),
         (12.0, 7.2), C["nucleoid"], ("nucleoid", "dna")),
        ("Plasmid", (CX + 2.9, 6.0), (12.4, 4.6), C["bact_plasmid"],
         ("plasmid",)),
        ("Ribosomes (70S)", (CX + 2.2, 3.3), (12.2, 2.4), C["ribosome"],
         ("ribosome", "ribosomes")),
        ("Flagellum", (CX + 6.3, 5.0), (11.6, 0.4), C["flagellum"],
         ("flagellum",)),
        ("Mesosome", (CX - 2.6, 2.5), (-2.8, 1.0), C["mesosome"],
         ("mesosome",)),
        ("Pili / fimbriae", (CX - 4.6, 3.4), (-2.8, 4.2), C["pili"],
         ("pili", "fimbriae", "pilus")),
        ("Cytoplasm", (CX - 2.2, 4.0), (-2.6, 6.6), "#827717", ("cytoplasm",)),
    ):
        _annotate(ax, text, xy, xytext, col, fontsize=9.5,
                  highlight=_is_hl(hl, *aliases))


def _draw_tmv(ax, schema, hl):
    ax.set_xlim(-4.0, 15.0); ax.set_ylim(-1.0, 10.0)
    CY = 5.0

    # Rod of stacked capsomeres; the left end is stripped to show the RNA helix.
    for i, x in enumerate(np.arange(1.6, 10.4, 0.62)):
        ax.add_patch(Ellipse((x, CY), 0.58, 3.4, fc="#d1c4e9",
                             ec=C["capsomere"], lw=1.4, zorder=4))
    ax.add_patch(Rectangle((1.4, CY - 1.7), 9.2, 3.4, fc="none",
                           ec=C["capsid"], lw=2.6, zorder=5))

    t = np.linspace(0, 7.5 * np.pi, 500)                           # ssRNA helix
    rx = 0.9 + t * (5.4 / (7.5 * np.pi))
    ax.plot(rx, CY + 1.05 * np.sin(t), color=C["rna_strand"], lw=2.6, zorder=6)
    ax.add_patch(Rectangle((0.7, CY - 1.75), 2.6, 3.5, fc="white", ec="none",
                           zorder=3))
    for i, x in enumerate(np.arange(3.5, 10.4, 0.62)):             # re-draw the
        ax.add_patch(Ellipse((x, CY), 0.58, 3.4, fc="#d1c4e9",     # covered part
                             ec=C["capsomere"], lw=1.4, zorder=4))
    ax.plot([3.4, 3.4], [CY - 1.7, CY + 1.7], color=C["capsid"], lw=2.2,
            zorder=5)
    ax.plot([3.4, 10.6], [CY + 1.7, CY + 1.7], color=C["capsid"], lw=2.4,
            zorder=5)
    ax.plot([3.4, 10.6], [CY - 1.7, CY - 1.7], color=C["capsid"], lw=2.4,
            zorder=5)
    ax.plot([10.6, 10.6], [CY - 1.7, CY + 1.7], color=C["capsid"], lw=2.4,
            zorder=5)

    ax.add_patch(FancyArrowPatch((1.4, 1.9), (10.6, 1.9), arrowstyle="<|-|>",
                                 mutation_scale=12, lw=1.3, color="#546e7a",
                                 zorder=6))
    ax.text(6.0, 1.5, "≈ 300 nm long", ha="center", fontsize=9,
            color="#546e7a")
    ax.add_patch(FancyArrowPatch((11.1, CY - 1.7), (11.1, CY + 1.7),
                                 arrowstyle="<|-|>", mutation_scale=12, lw=1.3,
                                 color="#546e7a", zorder=6))
    ax.text(11.4, CY, "≈ 18 nm\nwide", ha="left", va="center", fontsize=9,
            color="#546e7a")

    if not schema.show_labels:
        return
    for text, xy, xytext, col, aliases in (
        ("Capsid\n(helical protein coat)", (7.0, 6.7), (7.0, 9.2), C["capsid"],
         ("capsid", "coat")),
        ("Capsomere\n(protein subunit)", (5.15, 5.9), (1.6, 8.8),
         C["capsomere"], ("capsomere", "capsomeres")),
        ("ssRNA (genome),\nhelically coiled", (1.7, 5.9), (-2.6, 7.6),
         C["rna_strand"], ("rna", "ssrna", "genome", "nucleic_acid")),
        ("Helical symmetry —\nno envelope, no tail", (9.0, 3.6), (13.2, 6.6),
         "#4a148c", ("symmetry",)),
    ):
        _annotate(ax, text, xy, xytext, col, fontsize=9.5,
                  highlight=_is_hl(hl, *aliases))


def _draw_hiv(ax, schema, hl):
    ax.set_xlim(-4.6, 15.4); ax.set_ylim(-0.6, 10.6)
    CX, CY, R = 5.4, 5.0, 3.5

    ax.add_patch(Circle((CX, CY), R, fc="#ffebee", ec=C["envelope"], lw=3.0,
                        zorder=3))                                  # envelope
    ax.add_patch(Circle((CX, CY), R - 0.32, fc="#ffe0b2",
                        ec=C["matrix_prot"], lw=2.0, zorder=4))     # matrix
    ax.add_patch(Circle((CX, CY), R - 0.62, fc="#fff8e1", ec="none", zorder=5))
    for a in range(0, 360, 24):                                     # gp120/gp41
        x0, y0 = _polar(CX, CY, R, a)
        x1, y1 = _polar(CX, CY, R + 0.55, a)
        ax.plot([x0, x1], [y0, y1], color=C["spike"], lw=2.0, zorder=6)
        ax.add_patch(Circle((x1, y1), 0.2, fc=C["spike"], ec="#0d47a1",
                            lw=0.8, zorder=6))

    cone = [(CX - 1.05, CY + 1.85), (CX + 1.05, CY + 1.85),
            (CX + 0.42, CY - 2.05), (CX - 0.42, CY - 2.05)]
    ax.add_patch(Polygon(cone, closed=True, fc="#e1bee7", ec=C["capsid"],
                         lw=2.4, zorder=6))                         # p24 capsid
    for s in (-1, 1):                                               # 2 × ssRNA
        yy = np.linspace(CY - 1.6, CY + 1.5, 120)
        ax.plot(CX + s * 0.28 + 0.14 * np.sin(5 * yy), yy,
                color=C["rna_strand"], lw=2.0, zorder=7)
    ax.add_patch(Ellipse((CX + 0.05, CY - 1.15), 0.75, 0.45, angle=-15,
                         fc="#b2dfdb", ec=C["enzyme_rt"], lw=1.4, zorder=8))
    ax.add_patch(Ellipse((CX - 0.1, CY + 1.15), 0.6, 0.4, angle=12,
                         fc="#b2dfdb", ec=C["enzyme_rt"], lw=1.4, zorder=8))

    if not schema.show_labels:
        return
    for text, xy, xytext, col, aliases in (
        ("Lipid envelope", (CX - 2.3, CY + 2.5), (-3.0, 9.6), C["envelope"],
         ("envelope", "lipid_envelope")),
        ("Glycoprotein spikes\n(gp120 knob + gp41 stalk)", (CX + 2.6, CY + 2.9),
         (11.6, 9.6), C["spike"], ("spike", "spikes", "gp120", "gp41",
                                   "glycoprotein")),
        ("Matrix protein (p17)", (CX - 3.1, CY - 1.0), (-3.0, 2.2),
         C["matrix_prot"], ("matrix", "matrix_protein", "p17")),
        ("Capsid (p24, cone-shaped)", (CX - 0.85, CY + 1.55), (-2.4, 6.6),
         C["capsid"], ("capsid", "p24")),
        ("Two copies of (+) ssRNA", (CX + 0.42, CY + 0.6), (12.0, 6.4),
         C["rna_strand"], ("rna", "ssrna", "genome")),
        ("Reverse transcriptase\n(RNA → DNA)", (CX + 0.42, CY - 1.15),
         (11.8, 2.6), C["enzyme_rt"], ("reverse_transcriptase", "enzyme")),
    ):
        _annotate(ax, text, xy, xytext, col, fontsize=9.5,
                  highlight=_is_hl(hl, *aliases))


# ═══════════════════════════════════════════════════════════════════════════════
# 33. Stomata
# ═══════════════════════════════════════════════════════════════════════════════

# The whole diagram turns on ONE number: the pore aperture. Turgid (open) guard
# cells bow apart; flaccid (closed) guard cells meet, so the aperture is zero.
# Both the drawing and the caption read the aperture from this one table.
_STOMATA_APERTURE = {"open": 0.85, "closed": 0.0}


def _stomata_aperture(state: str) -> float:
    """Half-height of the stomatal pore (arbitrary units, > 0 when open)."""
    return _STOMATA_APERTURE[state]


def _draw_stoma_kidney(ax, cx, cy, p, schema):
    """Two kidney-shaped guard cells (dicot) enclosing a lens-shaped pore."""
    A, B, a = 2.4, 1.5, 1.7            # outer semi-length, semi-height, pore half-length
    th = np.linspace(0.0, np.pi, 160)
    xs = np.linspace(-a, a, 90)
    up = p * np.sqrt(np.clip(1.0 - (xs / a) ** 2, 0.0, 1.0))
    inner_x = np.concatenate(([-A, -a], xs, [a, A]))   # (-A,0) → over pore → (A,0)
    inner_y = np.concatenate(([0.0, 0.0], up, [0.0, 0.0]))
    for sgn in (1, -1):                # upper (sgn=1) then lower guard cell
        bx = np.concatenate((A * np.cos(th), inner_x)) + cx
        by = np.concatenate((sgn * B * np.sin(th), sgn * inner_y)) + cy
        ax.add_patch(Polygon(np.column_stack([bx, by]), closed=True,
                             fc=C["guard_cell"], ec=C["guard_wall"], lw=1.6,
                             zorder=5))
    if p > 1e-6:                       # the pore itself
        px = np.concatenate((xs, xs[::-1])) + cx
        py = np.concatenate((up, -up[::-1])) + cy
        ax.add_patch(Polygon(np.column_stack([px, py]), closed=True,
                             fc=C["pore"], ec="none", zorder=6))
    # Unevenly thickened INNER wall (facing the pore) — drawn heavier than the
    # thin, elastic outer wall. This asymmetry is why the cells bow open.
    for sgn in (1, -1):
        ax.plot(xs + cx, sgn * up + cy, color=C["guard_wall"], lw=4.0,
                solid_capstyle="round", zorder=7)
        for s in (-1, 1):             # guard cells meet along y=0 at the poles
            ax.plot([s * a + cx, s * A + cx], [cy, cy], color=C["guard_wall"],
                    lw=4.0, solid_capstyle="round", zorder=7)
    _chloro = [(-1.55, 0.72), (-0.65, 0.92), (0.35, 0.92), (1.35, 0.72),
               (-1.05, 0.45), (0.95, 0.45)]
    for sgn in (1, -1):
        for dx, dy in _chloro:
            ax.add_patch(Circle((cx + dx, cy + sgn * dy), 0.12,
                                fc=C["chloroplast"], ec="none", zorder=8))
        ax.add_patch(Ellipse((cx + 1.75, cy + sgn * 0.62), 0.52, 0.34,
                             fc=C["guard_nucleus"], ec="none", zorder=8))


def _draw_stoma_dumbbell(ax, cx, cy, p, schema):
    """Two dumb-bell guard cells (monocot / grass): bulbous elastic ends and a
    thick-walled straight middle. The bulbs swell and force the middles apart."""
    xb, rb, rod_hw = 1.8, 0.7, 0.24
    gap = xb - rb                      # central bulb-free span (pore length/2)
    for sgn in (1, -1):
        yc = sgn * (p + rod_hw)        # rod centre; inner face at sgn*p
        ax.add_patch(Rectangle((cx - xb, cy + yc - rod_hw), 2 * xb, 2 * rod_hw,
                               fc=C["guard_cell"], ec="none", zorder=5))
        for s in (-1, 1):
            ax.add_patch(Circle((cx + s * xb, cy + yc), rb, fc=C["guard_cell"],
                                ec=C["guard_wall"], lw=1.6, zorder=5))
        # outer (thin) long wall of the rod
        ax.plot([cx - xb, cx + xb], [cy + yc + rod_hw] * 2, color=C["guard_wall"],
                lw=1.6, zorder=6)
        # inner (thick) long wall facing the pore
        ax.plot([cx - xb, cx + xb], [cy + sgn * p] * 2, color=C["guard_wall"],
                lw=4.0, solid_capstyle="round", zorder=7)
    if p > 1e-6:                       # the central slit pore
        ax.add_patch(Rectangle((cx - gap, cy - p), 2 * gap, 2 * p,
                               fc=C["pore"], ec="none", zorder=6))
    for sgn in (1, -1):
        for s in (-1, 1):
            for dx, dy in ((-0.18, 0.18), (0.2, -0.15), (0.0, -0.02)):
                ax.add_patch(Circle((cx + s * xb + dx, cy + sgn * (p + rod_hw) + dy),
                                    0.1, fc=C["chloroplast"], ec="none", zorder=8))
        ax.add_patch(Ellipse((cx - xb, cy + sgn * (p + rod_hw)), 0.34, 0.24,
                             fc=C["guard_nucleus"], ec="none", zorder=8))


def _draw_stoma_surround(ax, cx, cy, shape):
    """Epidermal background with two flanking subsidiary cells."""
    ax.add_patch(FancyBboxPatch((cx - 4.0, cy - 3.4), 8.0, 6.8,
                                boxstyle="round,pad=0.02,rounding_size=0.3",
                                fc=C["epidermal"], ec="#b0bec5", lw=1.2,
                                zorder=1))
    # Subsidiary cells flank the guard-cell pair, distinct from ordinary
    # epidermal cells (parallel to the long axis of the pore).
    for sgn in (1, -1):
        ax.add_patch(FancyBboxPatch((cx - 3.4, cy + sgn * 1.9 - 0.7), 6.8, 1.4,
                                    boxstyle="round,pad=0.02,rounding_size=0.35",
                                    fc=C["subsidiary"], ec="#81c784", lw=1.3,
                                    zorder=2))


def _stoma_ion_arrows(ax, cx, cy, state):
    into = state == "open"
    for s, lbl, col in ((-1, "K⁺", C["k_ion"]), (1, "H₂O", C["water_flow"])):
        y = cy
        x_far, x_near = cx + s * 3.75, cx + s * 2.55
        x0, x1 = (x_far, x_near) if into else (x_near, x_far)
        ax.add_patch(FancyArrowPatch((x0, y), (x1, y), arrowstyle="-|>",
                                     mutation_scale=16, lw=2.4, color=col,
                                     zorder=9))
        ax.text(cx + s * 3.8, y + 0.45, f"{lbl} {'in' if into else 'out'}",
                ha="center", va="bottom", fontsize=10, fontweight="bold",
                color=col, zorder=9)


def _stoma_labels(ax, cx, cy, shape, p):
    pore_top = p if p > 1e-6 else 0.05
    rows = [
        ("Guard cell", (cx - 1.6, cy + 1.35), (cx - 3.9, cy + 2.9),
         C["guard_wall"]),
        ("Stomatal pore", (cx, cy), (cx + 0.0, cy - 3.15), C["stoma"]),
        ("Subsidiary cell", (cx + 2.4, cy + 1.9), (cx + 3.7, cy + 3.0),
         "#2e7d32"),
        ("Chloroplast", (cx - 0.65, cy + 0.92), (cx - 3.7, cy + 1.2),
         C["chloroplast"]),
        ("Nucleus", (cx + 1.75, cy + 0.62), (cx + 3.8, cy + 1.1),
         C["guard_nucleus"]),
        ("Thick inner wall", (cx + 0.55, cy + pore_top), (cx + 3.6, cy - 0.3),
         C["guard_wall"]),
        ("Thin outer wall", (cx - 0.1, cy + 1.5), (cx - 3.6, cy - 0.4),
         C["guard_wall"]),
    ]
    for text, xy, xytext, col in rows:
        _annotate(ax, text, xy, xytext, col, fontsize=9)


def render_stomata(data: Dict[str, Any],
                   canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = StomataSchema(**data)
    states = ["open", "closed"] if schema.state == "both" else [schema.state]
    shape = schema.guard_cell_shape
    single = len(states) == 1
    draw = _draw_stoma_kidney if shape == "kidney" else _draw_stoma_dumbbell

    panel_w = 9.0
    fig, ax = plt.subplots(figsize=(8.0 * len(states), 8.2))
    ax.set_aspect("equal"); ax.axis("off")
    ax.set_xlim(-4.4, panel_w * (len(states) - 1) + 4.4)
    ax.set_ylim(-4.9, 4.9)

    for i, state in enumerate(states):
        cx = i * panel_w
        cy = 0.3
        p = _stomata_aperture(state)
        _draw_stoma_surround(ax, cx, cy, shape)
        draw(ax, cx, cy, p, schema)
        turgor = "TURGID" if state == "open" else "FLACCID"
        ax.text(cx, cy + 4.15, f"{state.upper()} — guard cells {turgor}",
                ha="center", va="center", fontsize=11.5, fontweight="bold",
                color=C["guard_wall"],
                bbox=dict(boxstyle="round,pad=0.3", fc="#e8f5e9",
                          ec=C["guard_wall"], lw=1.1))
        if schema.show_ion_flux:
            _stoma_ion_arrows(ax, cx, cy, state)
        if schema.show_labels and (single or i == 0):
            _stoma_labels(ax, cx, cy, shape, p)

    shape_name = ("kidney-shaped (dicot)" if shape == "kidney"
                  else "dumb-bell shaped (monocot / grass)")
    if schema.show_mechanism:
        note = (f"{shape_name} guard cells.  K⁺ influx lowers the water "
                f"potential → water enters → guard cells become TURGID → the "
                f"unevenly thickened inner walls bow apart → pore OPENS "
                f"(aperture {_stomata_aperture('open'):.2f}).  K⁺ efflux → water "
                f"leaves → cells FLACCID → pore CLOSES (aperture "
                f"{_stomata_aperture('closed'):.2f}).")
    else:
        note = f"Stoma with {shape_name} guard cells and subsidiary cells."
    ax.set_title(schema.title or "Stoma — Guard Cells and the Stomatal Pore",
                 fontsize=14, fontweight="bold", pad=6)
    fig.text(0.5, 0.015, _wrap(note, 118), ha="center", fontsize=9.5,
             color="#37474f", style="italic")
    fig.tight_layout(pad=0.5, rect=(0, 0.05, 1, 1))
    return _fig_to_svg(fig)


# ═══════════════════════════════════════════════════════════════════════════════
# 30. Ear Diagram
# ═══════════════════════════════════════════════════════════════════════════════

# Region → (label, x-span). Every part below is tagged with its region so the
# external / middle / internal division is a single source of truth.
_EAR_REGIONS = [
    ("EXTERNAL EAR", -2.0, 5.0, "ear_external"),
    ("MIDDLE EAR", 5.0, 8.3, "ear_middle"),
    ("INTERNAL EAR", 8.3, 17.0, "ear_internal"),
]


def _draw_cochlea_inset(ax, ox, oy):
    """Section through one cochlear turn → the organ of Corti on the basilar
    membrane, between the three scalae."""
    ax.add_patch(FancyBboxPatch((ox - 2.7, oy - 2.6), 5.4, 5.2,
                                boxstyle="round,pad=0.1", fc="white",
                                ec="#78909c", lw=1.4, zorder=11))
    ax.text(ox, oy + 2.25, "Section through one cochlear turn", ha="center",
            fontsize=9, style="italic", color="#455a64", zorder=13)
    R = 1.9
    ax.add_patch(Circle((ox, oy - 0.1), R, fc=C["scala"], ec=C["cochlea"],
                        lw=1.8, zorder=12))
    # Reissner's (vestibular) membrane and the basilar membrane cut the duct
    # into three chambers; the scala media (cochlear duct) is the wedge between.
    xr = np.linspace(ox - R * 0.94, ox + R * 0.94, 40)
    reiss = oy - 0.1 + 0.55 + 0.12 * (xr - ox)
    basil = oy - 0.1 - 0.55 + 0.05 * (xr - ox)
    ax.plot(xr, reiss, color="#00897b", lw=2.0, zorder=13)
    ax.plot(xr, basil, color=C["basilar"], lw=2.6, zorder=13)
    # organ of Corti — hair cells + tectorial membrane, on the basilar membrane
    for k in range(5):
        hx = ox - 0.5 + k * 0.25
        ax.add_patch(Polygon([(hx, basil[16 + k]), (hx - 0.07, basil[16 + k] + 0.42),
                              (hx + 0.07, basil[16 + k] + 0.42)], closed=True,
                             fc=C["organ_corti"], ec="none", zorder=14))
    ax.plot([ox - 0.75, ox + 0.35], [oy + 0.15, oy - 0.02], color="#ad1457",
            lw=1.6, zorder=14)                                   # tectorial membrane
    labels = [
        ("Scala vestibuli", (ox, oy + 1.25), (ox + 0.2, oy + 1.95), C["cochlea"]),
        ("Scala media\n(cochlear duct)", (ox + 0.2, oy + 0.15),
         (ox + 2.0, oy + 0.9), "#00695c"),
        ("Scala tympani", (ox, oy - 1.25), (ox + 0.2, oy - 2.0), C["cochlea"]),
        ("Basilar membrane", (ox - 0.2, basil[14]), (ox - 2.0, oy - 1.7),
         C["basilar"]),
        ("Organ of Corti", (ox - 0.25, oy - 0.2), (ox - 2.1, oy + 0.9),
         C["organ_corti"]),
    ]
    for text, xy, xytext, col in labels:
        ax.annotate(text, xy=xy, xytext=xytext, fontsize=7.6, color=col,
                    ha="center", va="center", zorder=15,
                    bbox=dict(boxstyle="round,pad=0.16", fc="white", ec=col,
                              lw=0.7),
                    arrowprops=dict(arrowstyle="-|>", color=col, lw=0.8))


def render_ear_diagram(data: Dict[str, Any],
                       canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = EarDiagramSchema(**data)
    hl = _norm(schema.highlight_part)

    fig, ax = plt.subplots(figsize=(14.5, 8.6))
    ax.set_aspect("equal"); ax.axis("off")
    ax.set_xlim(-2.2, 17.2); ax.set_ylim(-3.4, 10.6)

    if schema.show_regions:
        for label, x0, x1, col in _EAR_REGIONS:
            ax.add_patch(Rectangle((x0, -3.4), x1 - x0, 14.0, fc=C[col],
                                   ec="none", zorder=0))
            ax.plot([x1, x1], [-3.4, 9.4], ls=(0, (4, 3)), color="#b0bec5",
                    lw=1.2, zorder=1)
            ax.text((x0 + x1) / 2, 9.9, label, ha="center", va="center",
                    fontsize=11, fontweight="bold", color="#607d8b", zorder=1)

    # ── External ear ──────────────────────────────────────────────────────────
    # Pinna: a funnel that collects sound into the canal.
    ax.add_patch(Polygon([(-2.0, 8.6), (2.1, 6.5), (2.1, 3.4), (-2.0, 1.3),
                          (-0.7, 4.95)], closed=True, fc=C["pinna"],
                         ec="#c2185b", lw=1.8, zorder=3))
    ax.add_patch(Rectangle((2.1, 4.3), 2.9, 1.35, fc=C["ear_canal"],
                           ec="#e0a96d", lw=1.6, zorder=3))          # canal
    # Tympanic membrane — the slanted eardrum closing the canal.
    ax.add_patch(Polygon([(4.98, 3.95), (5.22, 3.95), (5.42, 6.0), (5.18, 6.0)],
                         closed=True, fc=C["tympanum"], ec="#4e342e", lw=1.4,
                         zorder=4))

    # ── Middle ear: the three ossicles, eardrum → oval window ─────────────────
    ax.plot([5.25, 5.95], [5.35, 6.55], color=C["ossicle"], lw=3.2,
            solid_capstyle="round", zorder=5)                        # malleus handle
    ax.add_patch(Circle((6.02, 6.62), 0.2, fc="#8d6e63", ec=C["ossicle"],
                        lw=1.4, zorder=5))                           # malleus head
    ax.add_patch(Polygon([(6.05, 6.6), (6.85, 6.5), (6.6, 5.7), (6.2, 6.05)],
                         closed=True, fc="#a1887f", ec=C["ossicle"], lw=1.4,
                         zorder=5))                                  # incus
    ax.plot([6.75, 7.55], [5.95, 5.35], color=C["ossicle"], lw=2.4, zorder=5)
    ax.plot([6.75, 7.55], [5.55, 5.05], color=C["ossicle"], lw=2.4, zorder=5)
    ax.plot([7.55, 7.95], [5.35, 5.2], color=C["ossicle"], lw=2.4, zorder=5)
    ax.plot([7.55, 7.95], [5.05, 5.2], color=C["ossicle"], lw=2.4, zorder=5)  # stapes
    ax.add_patch(Ellipse((8.15, 5.2), 0.16, 0.5, fc="#cfd8dc", ec="#455a64",
                        lw=1.4, zorder=4))                           # oval window
    ax.add_patch(Ellipse((8.15, 3.9), 0.16, 0.42, fc="#cfd8dc", ec="#455a64",
                        lw=1.4, zorder=4))                           # round window
    # Eustachian tube — middle-ear cavity down to the pharynx.
    et = np.linspace(0, 1, 60)
    ax.add_patch(Polygon(
        list(zip(6.4 + 1.5 * et, 3.3 - 4.6 * et)) +
        list(zip(7.0 + 1.5 * et[::-1], 3.3 - 4.6 * et[::-1])),
        closed=True, fc=C["eustachian"], ec="#00695c", lw=1.4, zorder=2,
        alpha=0.9))

    # ── Internal ear ──────────────────────────────────────────────────────────
    ax.add_patch(Ellipse((8.95, 5.55), 1.1, 1.5, fc=C["vestibule"],
                        ec="#4527a0", lw=1.6, zorder=4))             # vestibule
    for cx_, cy_, w, h, ang in ((8.7, 7.7, 1.5, 2.3, 22),
                                (9.9, 7.6, 1.5, 2.3, -22),
                                (9.35, 6.85, 2.6, 1.1, 0)):          # 3 SC canals
        ax.add_patch(Ellipse((cx_, cy_), w, h, angle=ang, fc="none",
                            ec=C["semicircular"], lw=3.0, zorder=3))
    for a in (150, 30, 265):                                         # ampullae
        ax.add_patch(Circle((8.95 + 0.9 * math.cos(math.radians(a)),
                             6.6 + 0.9 * math.sin(math.radians(a))), 0.2,
                            fc="#90caf9", ec=C["semicircular"], lw=1.2, zorder=4))
    # Cochlea — a snail-shell spiral opening at the vestibule.
    th = np.linspace(0.0, 2.4 * 2 * np.pi, 400)
    rr = 0.14 + 0.135 * th
    ccx, ccy = 10.9, 3.1
    ax.add_patch(Circle((ccx, ccy), rr.max() + 0.25, fc="#ede7f6",
                        ec=C["cochlea"], lw=1.8, zorder=3))
    ax.plot(ccx + rr * np.cos(th), ccy + rr * np.sin(th), color=C["cochlea"],
            lw=2.6, zorder=4)
    ax.plot([9.4, ccx - rr.max()], [4.9, ccy + 0.6], color=C["cochlea"], lw=2.4,
            zorder=3)                                                # to vestibule
    # Auditory nerve leaving the cochlea and the vestibule.
    for y0 in (2.6, 3.1, 3.6):
        ax.add_patch(FancyArrowPatch((ccx + 1.0, y0), (14.6, 3.1),
                                     arrowstyle="-", lw=3.2,
                                     color=C["auditory_nerve"],
                                     connectionstyle="arc3,rad=0.02", zorder=2))
    ax.add_patch(Circle((14.7, 3.1), 0.28, fc=C["auditory_nerve"],
                        ec="#f9a825", lw=1.4, zorder=3))

    if schema.show_labels:
        rows = [
            ("Pinna", (-0.9, 5.0), (-1.4, 8.9), "#c2185b", ("pinna",)),
            ("External auditory\ncanal (meatus)", (3.5, 5.0), (2.4, 8.7),
             "#c07c30", ("external_auditory_canal", "canal", "meatus")),
            ("Tympanic membrane\n(ear drum)", (5.2, 5.0), (4.9, 8.4),
             "#4e342e", ("tympanic_membrane", "ear_drum", "eardrum", "tympanum")),
            ("Malleus", (5.7, 6.0), (5.7, 8.9), C["ossicle"], ("malleus",)),
            ("Incus", (6.5, 6.2), (6.7, 8.6), C["ossicle"], ("incus",)),
            ("Stapes", (7.2, 5.4), (7.6, 8.9), C["ossicle"], ("stapes",)),
            ("Ear ossicles", (6.4, 5.9), (6.4, 8.0), "#4e342e",
             ("ear_ossicles", "ossicles")),
            ("Oval window", (8.15, 5.2), (9.4, 8.9), "#455a64",
             ("oval_window",)),
            ("Round window", (8.15, 3.9), (7.1, 1.3), "#455a64",
             ("round_window",)),
            ("Eustachian tube\n(to pharynx)", (7.4, 0.6), (9.9, -1.6),
             C["eustachian"], ("eustachian_tube", "eustachian")),
            ("Semicircular\ncanals", (8.6, 8.4), (11.6, 8.9), C["semicircular"],
             ("semicircular_canals", "semicircular")),
            ("Vestibule", (8.95, 5.55), (11.6, 6.6), "#4527a0",
             ("vestibule",)),
            ("Cochlea", (ccx + 0.4, ccy - 0.4), (12.9, 4.8), C["cochlea"],
             ("cochlea",)),
            ("Auditory nerve", (13.5, 3.1), (13.9, 5.4), "#c49000",
             ("auditory_nerve", "nerve")),
        ]
        for text, xy, xytext, col, aliases in rows:
            _annotate(ax, text, xy, xytext, col, fontsize=8.4,
                      highlight=_is_hl(hl, *aliases))

    if schema.show_cochlea_inset:
        ax.plot([ccx, 14.3], [ccy - 0.4, -0.1 + 2.6], color="#90a4ae", lw=1.0,
                ls=":", zorder=10)
        _draw_cochlea_inset(ax, 14.3, -0.4)

    ax.set_title(schema.title or "Human Ear — Structure", fontsize=14,
                 fontweight="bold", pad=6)
    fig.text(0.5, 0.015,
             "External ear (pinna + auditory canal) collects sound → tympanic "
             "membrane vibrates → ossicles (malleus, incus, stapes) amplify it "
             "→ oval window → cochlea, where the organ of Corti transduces it to "
             "nerve impulses in the auditory nerve.", ha="center", fontsize=9,
             color="#37474f", style="italic", wrap=True)
    fig.tight_layout(pad=0.5, rect=(0, 0.05, 1, 1))
    return _fig_to_svg(fig)


# ═══════════════════════════════════════════════════════════════════════════════
# 31. Endocrine System
# ═══════════════════════════════════════════════════════════════════════════════

# (key, gland name, body position, label side, hormone) — one source of truth
# for both the location map and the hormone table.
_ENDOCRINE_GLANDS = [
    ("hypothalamus", "Hypothalamus", (-0.45, 7.95), "L",
     "Releasing / inhibiting hormones"),
    ("pineal", "Pineal gland", (0.05, 8.45), "R", "Melatonin"),
    ("pituitary", "Pituitary gland", (0.4, 7.5), "R",
     "GH, TSH, ACTH, FSH, LH, Prolactin; ADH, Oxytocin"),
    ("thyroid", "Thyroid gland", (0.0, 6.05), "L",
     "Thyroxine (T₃, T₄), Calcitonin"),
    ("parathyroid", "Parathyroid glands", (0.5, 5.9), "R",
     "Parathormone (PTH)"),
    ("thymus", "Thymus", (0.0, 4.5), "L", "Thymosins"),
    ("adrenal", "Adrenal glands", (0.95, 2.2), "R",
     "Adrenaline / Noradrenaline; Cortisol, Aldosterone"),
    ("pancreas", "Pancreas (Islets of Langerhans)", (-0.65, 1.3), "L",
     "Insulin, Glucagon"),
    ("gonad", "Gonads (testis / ovary)", (0.8, -1.6), "R",
     "Androgens; Estrogen, Progesterone"),
]
_ENDOCRINE_LABEL_Y = {
    "hypothalamus": 8.7, "thyroid": 5.9, "thymus": 3.4, "pancreas": 0.8,
    "pineal": 8.7, "pituitary": 7.0, "parathyroid": 5.2, "adrenal": 2.3,
    "gonad": -1.4,
}

_ENDOCRINE_AXES = {
    "thyroid": {"target": "Thyroid gland", "releasing": "TRH", "tropic": "TSH",
                "product": "Thyroxine (T₃ / T₄)"},
    "adrenal": {"target": "Adrenal cortex", "releasing": "CRH", "tropic": "ACTH",
                "product": "Cortisol"},
    "gonad": {"target": "Gonad (testis / ovary)", "releasing": "GnRH",
              "tropic": "FSH / LH", "product": "Testosterone / Estrogen"},
}


def _draw_body_outline(ax):
    ax.add_patch(Circle((0, 7.9), 1.25, fc="#fff3e0", ec=C["body_outline"],
                        lw=2.0, zorder=2))                           # head
    ax.add_patch(Polygon([(-0.55, 6.75), (0.55, 6.75), (0.55, 6.2),
                          (-0.55, 6.2)], closed=True, fc="#fff3e0",
                         ec=C["body_outline"], lw=2.0, zorder=2))     # neck
    ax.add_patch(FancyBboxPatch((-2.3, -2.6), 4.6, 8.7,
                                boxstyle="round,pad=0.02,rounding_size=0.8",
                                fc="#fff3e0", ec=C["body_outline"], lw=2.0,
                                zorder=1))                            # torso
    for s in (-1, 1):                                                # legs
        ax.add_patch(FancyBboxPatch((s * 0.2 - (0.9 if s < 0 else 0.0), -8.8),
                                    0.9, 6.4,
                                    boxstyle="round,pad=0.02,rounding_size=0.4",
                                    fc="#fff3e0", ec=C["body_outline"], lw=2.0,
                                    zorder=0))


def _draw_gland_locations(ax, schema, hl):
    ax.set_xlim(-7.6, 7.6); ax.set_ylim(-9.2, 10.0)
    _draw_body_outline(ax)
    for key, name, (gx, gy), side, hormone in _ENDOCRINE_GLANDS:
        ax.add_patch(Circle((gx, gy), 0.26, fc=C[key], ec="#37474f", lw=1.2,
                            zorder=6))
        colx = -5.6 if side == "L" else 5.6
        text = f"{name}\n{hormone}" if schema.show_hormones else name
        _annotate(ax, text, (gx, gy), (colx, _ENDOCRINE_LABEL_Y[key]),
                  C[key], fontsize=8.0, highlight=_is_hl(hl, key, name.lower()))


def _draw_feedback_axis(ax, schema, hl):
    ax.set_xlim(-6.4, 6.4); ax.set_ylim(-6.6, 6.4)
    axis = _ENDOCRINE_AXES[schema.axis]
    boxes = [
        ("Hypothalamus", 4.6, C["hypothalamus"], "hypothalamus"),
        ("Anterior pituitary", 0.6, C["pituitary"], "pituitary"),
        (axis["target"], -3.4, C[schema.axis if schema.axis in C else "thyroid"],
         schema.axis),
    ]
    bx, bw, bh = -2.4, 4.8, 1.5
    centers = []
    for name, y, col, key in boxes:
        hlb = _is_hl(hl, key, name.lower())
        ax.add_patch(FancyBboxPatch((bx, y - bh / 2), bw, bh,
                                    boxstyle="round,pad=0.1",
                                    fc="#fff176" if hlb else "#ede7f6",
                                    ec=col, lw=2.2, zorder=4))
        ax.text(0, y, name, ha="center", va="center", fontsize=11,
                fontweight="bold", color=col, zorder=5)
        centers.append(y)

    # Down the axis: each gland STIMULATES (+) the next with its tropic hormone.
    for (y0, y1, horm) in ((centers[0], centers[1], axis["releasing"]),
                           (centers[1], centers[2], axis["tropic"])):
        ax.add_patch(FancyArrowPatch((0, y0 - bh / 2), (0, y1 + bh / 2),
                                     arrowstyle="-|>", mutation_scale=18,
                                     lw=2.4, color=C["axis_arrow"], zorder=3))
        ax.text(0.35, (y0 + y1) / 2, f"+  {horm}\n(stimulates)", ha="left",
                va="center", fontsize=9, color=C["axis_arrow"],
                fontweight="bold")

    # The question: NEGATIVE FEEDBACK. The target hormone loops back up the side
    # and INHIBITS (−, drawn as a stop-bar) both the pituitary and hypothalamus.
    for y_to in (centers[1], centers[0]):
        ax.add_patch(FancyArrowPatch((bx, centers[2]), (bx - 1.6, centers[2]),
                                     arrowstyle="-", lw=2.2,
                                     color=C["feedback_neg"], zorder=3))
        ax.add_patch(FancyArrowPatch((bx - 1.6, centers[2]), (bx - 1.6, y_to),
                                     arrowstyle="-", lw=2.2,
                                     color=C["feedback_neg"], zorder=3))
        ax.add_patch(FancyArrowPatch((bx - 1.6, y_to), (bx - 0.08, y_to),
                                     arrowstyle="-", lw=2.2,
                                     color=C["feedback_neg"], zorder=3))
        ax.plot([bx - 0.08, bx - 0.08], [y_to - 0.24, y_to + 0.24],
                color=C["feedback_neg"], lw=3.4, zorder=4)          # ⊣ stop-bar
    ax.text(bx - 1.9, (centers[0] + centers[2]) / 2,
            f"–  {axis['product']}\nNEGATIVE FEEDBACK\n(inhibits)", ha="right",
            va="center", fontsize=9.5, color=C["feedback_neg"],
            fontweight="bold")
    ax.text(bx + bw + 0.2, centers[2], f"secretes\n{axis['product']}", ha="left",
            va="center", fontsize=9, color="#37474f", style="italic")


def _draw_hormone_table(ax, schema, hl):
    ax.set_xlim(0, 12); ax.set_ylim(0, 11)
    rows = [(name, hormone) for _, name, _, _, hormone in _ENDOCRINE_GLANDS]
    n = len(rows) + 1
    y_top, row_h = 10.4, 10.0 / n
    cols = [(0.2, 3.6, "Gland"), (3.6, 12.0, "Hormone(s)")]
    for i in range(n):
        y = y_top - i * row_h
        head = i == 0
        for x0, x1, _ in cols:
            ax.add_patch(Rectangle((x0, y - row_h), x1 - x0, row_h,
                                   fc=C["table_head"] if head else C["table_row"],
                                   ec="#b0bec5", lw=1.0, zorder=2))
        if head:
            for x0, x1, title in cols:
                ax.text(x0 + 0.15, y - row_h / 2, title, ha="left", va="center",
                        fontsize=10.5, fontweight="bold", color="#4527a0")
        else:
            name, hormone = rows[i - 1]
            key = _ENDOCRINE_GLANDS[i - 1][0]
            if _is_hl(hl, key, name.lower()):
                ax.add_patch(Rectangle((0.2, y - row_h), 11.8, row_h,
                                       fc="#fff9c4", ec="#fbc02d", lw=1.4,
                                       zorder=1))
            ax.text(0.35, y - row_h / 2, name, ha="left", va="center",
                    fontsize=8.8, fontweight="bold", color=C[key])
            ax.text(3.75, y - row_h / 2, hormone, ha="left", va="center",
                    fontsize=8.6, color="#37474f")


def render_endocrine_system(data: Dict[str, Any],
                            canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = EndocrineSystemSchema(**data)
    hl = _norm(schema.highlight_gland)

    if schema.view == "gland_locations":
        fig, ax = plt.subplots(figsize=(11, 9.2))
        ax.set_aspect("equal")
        _draw_gland_locations(ax, schema, hl)
        default_title = "Endocrine System — Glands and their Hormones"
        note = ("The endocrine glands are ductless; they pour hormones straight "
                "into the blood. Hypothalamus and pituitary are the master "
                "control; the others act on specific target organs.")
    elif schema.view == "feedback_loop":
        fig, ax = plt.subplots(figsize=(11, 9.0))
        _draw_feedback_axis(ax, schema, hl)
        a = _ENDOCRINE_AXES[schema.axis]
        default_title = (f"Hypothalamo–Pituitary–{a['target']} Axis — "
                         f"Negative Feedback")
        note = (f"{a['releasing']} → {a['tropic']} → {a['product']}. Rising "
                f"{a['product']} feeds BACK to inhibit the hypothalamus and "
                f"pituitary, so its own secretion is switched down — negative "
                f"feedback keeps the hormone level steady.")
    else:  # hormone_table
        fig, ax = plt.subplots(figsize=(11, 8.4))
        _draw_hormone_table(ax, schema, hl)
        default_title = "Endocrine Glands and their Hormones"
        note = ("Each endocrine gland secretes specific hormones that regulate "
                "growth, metabolism, and reproduction.")
    ax.axis("off")

    ax.set_title(schema.title or default_title, fontsize=14, fontweight="bold",
                 pad=6)
    fig.text(0.5, 0.015, _wrap(note, 116), ha="center", fontsize=9.5,
             color="#37474f", style="italic")
    fig.tight_layout(pad=0.5, rect=(0, 0.05, 1, 1))
    return _fig_to_svg(fig)


# ═══════════════════════════════════════════════════════════════════════════════
# 32. Kranz Anatomy
# ═══════════════════════════════════════════════════════════════════════════════

# The presence or absence of the Kranz ("wreath") bundle-sheath IS the question,
# so the drawing and the caption both read from this single table. A C4 leaf has
# the wreath; a C3 leaf does not.
_KRANZ_FEATURES: Dict[str, Dict[str, Any]] = {
    "c3": {
        "kranz": False,
        "co2_fixed_in": "mesophyll",
        "primary_enzyme": "RuBisCO",
        "first_product": "3-PGA (3-carbon)",
        "title": "C₃ Leaf — NO Kranz Anatomy",
        "note": "C₃ leaf: mesophyll is differentiated into palisade and spongy "
                "parenchyma; the bundle-sheath cells are small and chloroplast-"
                "poor. There is NO wreath — RuBisCO fixes CO₂ directly to a "
                "3-carbon acid (3-PGA) in the mesophyll.",
    },
    "c4": {
        "kranz": True,
        "co2_fixed_in": "mesophyll (PEP carboxylase)",
        "primary_enzyme": "PEP carboxylase (mesophyll) + RuBisCO (bundle sheath)",
        "first_product": "Oxaloacetate / OAA (4-carbon)",
        "title": "C₄ Leaf — Kranz Anatomy",
        "note": "C₄ (Hatch–Slack) leaf: a WREATH of large, chloroplast-rich "
                "bundle-sheath cells encircles each vascular bundle, with "
                "mesophyll around it. PEP carboxylase fixes CO₂ to OAA (4C) in "
                "the MESOPHYLL; RuBisCO runs the Calvin cycle in the BUNDLE "
                "SHEATH — this is Kranz anatomy.",
    },
}


def _kranz_chloroplasts(ax, cx, cy, r, n, seed_pts, col):
    for dx, dy in seed_pts[:n]:
        ax.add_patch(Circle((cx + dx * r, cy + dy * r), 0.1 * r,
                            fc=col, ec="none", zorder=9))


def _draw_vascular_bundle(ax, cx, cy, r):
    ax.add_patch(Wedge((cx, cy), r, 0, 180, fc="#ffcdd2", ec=C["xylem"],
                       lw=1.4, zorder=6))                       # xylem (upper)
    ax.add_patch(Wedge((cx, cy), r, 180, 360, fc="#bbdefb", ec=C["phloem"],
                       lw=1.4, zorder=6))                       # phloem (lower)
    ax.plot([cx - r, cx + r], [cy, cy], color="#455a64", lw=1.0, zorder=7)


def _draw_epidermis(ax, cx, y_lo, y_hi, half_w, cuticle_above):
    n = 9
    xs = np.linspace(cx - half_w, cx + half_w, n + 1)
    for k in range(n):
        ax.add_patch(Rectangle((xs[k], y_lo), xs[k + 1] - xs[k], y_hi - y_lo,
                               fc="#eceff1", ec="#90a4ae", lw=1.0, zorder=3))
    cy = y_hi + 0.06 if cuticle_above else y_lo - 0.06
    ax.plot([cx - half_w, cx + half_w], [cy, cy], color="#f9a825", lw=2.6,
            zorder=4)


_CHL_SEEDS = [(-0.4, 0.35), (0.35, 0.42), (0.1, -0.35), (-0.35, -0.3),
              (0.45, -0.05), (-0.05, 0.1), (0.2, 0.15), (-0.25, 0.0)]


def _draw_kranz_c4(ax, cx, cy, schema, hl):
    R_vb, R_bs, R_ms = 0.95, 2.15, 3.55
    _draw_epidermis(ax, cx, cy + 4.3, cy + 4.9, 4.8, cuticle_above=True)
    _draw_epidermis(ax, cx, cy - 4.9, cy - 4.3, 4.8, cuticle_above=False)

    # Mesophyll — outer ring of cells (drawn first, behind the sheath)
    for k in range(12):
        ang = k * 30.0
        mx, my = _polar(cx, cy, R_ms, ang)
        hlm = _is_hl(hl, "mesophyll")
        ax.add_patch(Circle((mx, my), 0.62,
                            fc="#c8e6c9" if hlm else C["mesophyll"],
                            ec="#66bb6a", lw=1.3, zorder=4))
        _kranz_chloroplasts(ax, mx, my, 0.62, 3, _CHL_SEEDS, "#2e7d32")

    # Bundle-sheath WREATH — large chloroplast-rich cells around the vein
    for k in range(8):
        ang = 90 + k * 45.0
        bx, by = _polar(cx, cy, R_bs, ang)
        hlb = _is_hl(hl, "bundle_sheath")
        ax.add_patch(Circle((bx, by), 0.8,
                            fc="#a5d6a7" if hlb else C["kranz_sheath"],
                            ec="#1b5e20", lw=1.8, zorder=6))
        _kranz_chloroplasts(ax, bx, by, 0.8, 6, _CHL_SEEDS, C["chloroplast_bs"])

    _draw_vascular_bundle(ax, cx, cy, R_vb)
    if _is_hl(hl, "vascular_bundle"):
        ax.add_patch(Circle((cx, cy), R_vb + 0.12, fc="none", ec="#fbc02d",
                            lw=2.4, zorder=8))


def _draw_leaf_c3(ax, cx, cy, schema, hl):
    _draw_epidermis(ax, cx, cy + 4.3, cy + 4.9, 4.8, cuticle_above=True)
    _draw_epidermis(ax, cx, cy - 4.9, cy - 4.3, 4.8, cuticle_above=False)

    hlm = _is_hl(hl, "mesophyll")
    pal = "#c8e6c9" if hlm else C["palisade"]
    spo = "#c8e6c9" if hlm else C["spongy"]
    xs = np.linspace(cx - 4.4, cx + 4.4, 10)
    for k in range(9):                                   # palisade parenchyma
        ax.add_patch(Rectangle((xs[k] + 0.05, cy + 1.9), xs[k + 1] - xs[k] - 0.1,
                               2.3, fc=pal, ec="#2e7d32", lw=1.1, zorder=4))
        _kranz_chloroplasts(ax, (xs[k] + xs[k + 1]) / 2, cy + 3.05, 1.2, 6,
                            [(0, 0.6), (0, 0.2), (0, -0.2), (0, -0.55),
                             (0, 0.4), (0, -0.4)], "#1b5e20")
    for k in range(11):                                  # spongy parenchyma
        sx = cx - 4.0 + (k % 6) * 1.6 + (0.8 if k >= 6 else 0)
        sy = cy + 0.6 - (0 if k < 6 else 1.7)
        if abs(sx - cx) < 1.4 and sy < cy + 0.2:
            continue                                     # leave room for the vein
        ax.add_patch(Circle((sx, sy), 0.7, fc=spo, ec="#66bb6a", lw=1.1,
                            zorder=4))
        _kranz_chloroplasts(ax, sx, sy, 0.7, 3, _CHL_SEEDS, "#2e7d32")

    # Vascular bundle with a THIN, chloroplast-poor bundle sheath (no wreath)
    for k in range(8):
        ang = 90 + k * 45.0
        bx, by = _polar(cx, cy - 0.9, 0.95, ang)
        hlb = _is_hl(hl, "bundle_sheath")
        ax.add_patch(Circle((bx, by), 0.42,
                            fc="#fff9c4" if hlb else "#f0f4c3",
                            ec="#c0ca33", lw=1.2, zorder=5))
    _draw_vascular_bundle(ax, cx, cy - 0.9, 0.72)
    if _is_hl(hl, "vascular_bundle"):
        ax.add_patch(Circle((cx, cy - 0.9), 0.84, fc="none", ec="#fbc02d",
                            lw=2.4, zorder=8))
    # a stoma in the lower epidermis
    ax.add_patch(Rectangle((cx + 2.4, cy - 4.95), 1.1, 0.12, fc="white",
                           ec="none", zorder=5))
    for s in (-1, 1):
        ax.add_patch(Ellipse((cx + 2.95 + s * 0.55, cy - 4.6), 0.3, 0.55,
                             fc=C["guard_cell"], ec=C["guard_wall"], lw=1.2,
                             zorder=5))


def _kranz_c4_pathway(ax, x0, cy):
    """The Hatch–Slack split drawn as a two-compartment flow chart."""
    ax.add_patch(FancyBboxPatch((x0, cy + 0.6), 5.4, 3.0,
                                boxstyle="round,pad=0.1", fc="#e8f5e9",
                                ec=C["kranz_sheath"], lw=1.6, zorder=3))
    ax.text(x0 + 2.7, cy + 3.25, "MESOPHYLL", ha="center", fontsize=10.5,
            fontweight="bold", color=C["kranz_sheath"])
    ax.text(x0 + 2.7, cy + 2.05,
            "CO₂ + PEP  →  OAA (4C)\n"
            "(enzyme: PEP carboxylase)\n"
            "OAA  →  malate (4C)", ha="center", va="center", fontsize=9.4,
            color="#1b5e20")

    ax.add_patch(FancyBboxPatch((x0, cy - 3.9), 5.4, 3.2,
                                boxstyle="round,pad=0.1", fc="#fff8e1",
                                ec="#1565c0", lw=1.6, zorder=3))
    ax.text(x0 + 2.7, cy - 1.05, "BUNDLE SHEATH", ha="center", fontsize=10.5,
            fontweight="bold", color="#1565c0")
    ax.text(x0 + 2.7, cy - 2.35,
            "malate  →  CO₂ + pyruvate (3C)\n"
            "CO₂ + RuBP  →  Calvin cycle  →  sugar\n"
            "(enzyme: RuBisCO)",
            ha="center", va="center", fontsize=9.4, color="#0d47a1")

    ax.add_patch(FancyArrowPatch((x0 + 1.4, cy + 0.55), (x0 + 1.4, cy - 0.65),
                                 arrowstyle="-|>", mutation_scale=16, lw=2.0,
                                 color=C["c4_arrow"], zorder=4))
    ax.text(x0 + 1.0, cy - 0.05, "malate", ha="right", fontsize=8.6,
            color=C["c4_arrow"], fontweight="bold")
    ax.add_patch(FancyArrowPatch((x0 + 4.0, cy - 0.65), (x0 + 4.0, cy + 0.55),
                                 arrowstyle="-|>", mutation_scale=16, lw=2.0,
                                 color="#8d6e63", zorder=4))
    ax.text(x0 + 4.4, cy - 0.05, "pyruvate", ha="left", fontsize=8.6,
            color="#8d6e63", fontweight="bold")


def render_kranz_anatomy(data: Dict[str, Any],
                         canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = KranzAnatomySchema(**data)
    hl = _norm(schema.highlight_cell)

    if schema.pathway == "comparison":
        panels = [("c3", -6.0), ("c4", 6.0)]
        show_biochem = False
        fig, ax = plt.subplots(figsize=(14.5, 8.4))
        ax.set_xlim(-11.6, 11.6); ax.set_ylim(-6.4, 6.6)
    elif schema.pathway == "c4" and schema.show_pathway:
        panels = [("c4", -5.6)]
        show_biochem = True
        fig, ax = plt.subplots(figsize=(14.5, 8.0))
        ax.set_xlim(-11.0, 12.0); ax.set_ylim(-6.2, 6.4)
    else:
        panels = [(schema.pathway, 0.0)]
        show_biochem = False
        fig, ax = plt.subplots(figsize=(9.0, 8.4))
        ax.set_xlim(-5.4, 5.4); ax.set_ylim(-6.2, 6.4)
    ax.set_aspect("equal"); ax.axis("off")

    for pathway, cx in panels:
        feat = _KRANZ_FEATURES[pathway]
        if pathway == "c4":
            _draw_kranz_c4(ax, cx, 0.4, schema, hl)
        else:
            _draw_leaf_c3(ax, cx, 0.4, schema, hl)
        if schema.show_labels:
            tag = "Kranz anatomy" if feat["kranz"] else "NO Kranz anatomy"
            tcol = C["kranz_sheath"] if feat["kranz"] else "#c62828"
            ax.text(cx, 5.9, f"{pathway.upper().replace('C', 'C')}  —  {tag}",
                    ha="center", va="center", fontsize=11.5, fontweight="bold",
                    color=tcol,
                    bbox=dict(boxstyle="round,pad=0.3", fc="#ffffff",
                              ec=tcol, lw=1.3))
            if pathway == "c4":
                _annotate(ax, "Bundle-sheath wreath\n(large, chloroplast-rich)",
                          _polar(cx, 0.4, 2.15, 90), (cx - 3.9, 3.4),
                          C["kranz_sheath"], fontsize=8.8,
                          highlight=_is_hl(hl, "bundle_sheath"))
                _annotate(ax, "Mesophyll cell", _polar(cx, 0.4, 3.55, 30),
                          (cx + 3.9, 3.0), "#2e7d32", fontsize=8.8,
                          highlight=_is_hl(hl, "mesophyll"))
                _annotate(ax, "Vascular bundle\n(xylem + phloem)", (cx, 0.4),
                          (cx + 3.9, -3.2), "#455a64", fontsize=8.8,
                          highlight=_is_hl(hl, "vascular_bundle"))
            else:
                _annotate(ax, "Palisade parenchyma", (cx - 2.0, 3.05),
                          (cx - 4.2, 5.2), "#2e7d32", fontsize=8.6)
                _annotate(ax, "Spongy parenchyma", (cx + 2.0, 1.0),
                          (cx + 3.9, 3.3), "#66bb6a", fontsize=8.6)
                _annotate(ax, "Bundle sheath\n(small, few chloroplasts)",
                          _polar(cx, -0.5, 0.95, 90), (cx + 3.9, -1.4),
                          "#9e9d24", fontsize=8.6,
                          highlight=_is_hl(hl, "bundle_sheath"))
                _annotate(ax, "Vascular bundle", (cx, -0.5), (cx - 4.2, -3.2),
                          "#455a64", fontsize=8.6,
                          highlight=_is_hl(hl, "vascular_bundle"))

    if show_biochem:
        _kranz_c4_pathway(ax, 4.6, 0.4)

    if len(panels) == 1:
        note = _KRANZ_FEATURES[panels[0][0]]["note"]
    else:
        note = ("Kranz anatomy is the diagnostic difference: the C₄ leaf has a "
                "wreath of chloroplast-rich bundle-sheath cells around each vein "
                "(spatial split of PEP carboxylase and RuBisCO); the C₃ leaf has "
                "no such wreath.")
    ax.set_title(schema.title or ("C₃ vs C₄ Leaf — Kranz Anatomy"
                 if len(panels) > 1 else _KRANZ_FEATURES[panels[0][0]]["title"]),
                 fontsize=14, fontweight="bold", pad=6)
    fig.text(0.5, 0.015, _wrap(note, 122), ha="center", fontsize=9.5,
             color="#37474f", style="italic")
    fig.tight_layout(pad=0.5, rect=(0, 0.05, 1, 1))
    return _fig_to_svg(fig)


# ═══════════════════════════════════════════════════════════════════════════════
# 34. Action Potential
# ═══════════════════════════════════════════════════════════════════════════════

def _action_potential_trace(resting: float = -70.0, threshold: float = -55.0,
                            peak: float = 30.0, hyper: Optional[float] = None,
                            n: int = 700):
    """Derive the classic membrane-potential trace as (t, V) arrays.

    Single source of truth: the diagram, the marked levels and the tests all
    read this. Anchors are (time_ms, mV); each segment is a raised-cosine
    (smoothstep) so the curve is smooth and monotone within a phase.
    """
    if hyper is None:
        hyper = resting - 10.0                     # ~−80 mV undershoot
    anchors = [
        (0.0, resting),      # resting membrane potential
        (1.0, resting),
        (2.2, threshold),    # local/graded depolarisation reaches threshold
        (3.0, peak),         # rapid depolarisation (rising phase) — Na⁺ influx
        (4.4, hyper),        # repolarisation → hyperpolarisation undershoot
        (5.8, resting),      # Na⁺/K⁺ pump restores resting potential
        (7.0, resting),
    ]
    t = np.linspace(0.0, anchors[-1][0], n)
    V = np.empty_like(t)
    for (t0, v0), (t1, v1) in zip(anchors, anchors[1:]):
        m = (t >= t0) & (t <= t1)
        x = (t[m] - t0) / (t1 - t0)
        V[m] = v0 + (v1 - v0) * (0.5 - 0.5 * np.cos(np.pi * x))
    return t, V


def render_action_potential(data: Dict[str, Any],
                            canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = ActionPotentialSchema(**data)
    rest, thr, peak = schema.resting_mv, schema.threshold_mv, schema.peak_mv
    hyper = rest - 10.0
    t, V = _action_potential_trace(rest, thr, peak, hyper)
    t_peak = t[int(np.argmax(V))]

    fig, ax = plt.subplots(figsize=(11.5, 7.2))
    y_lo, y_hi = hyper - 12, peak + 18
    ax.set_xlim(0, t[-1]); ax.set_ylim(y_lo, y_hi)

    if schema.show_phases:
        for x0, x1, col, name in (
            (1.0, 2.2, C["phase_lag"], "Depolarising\nstimulus"),
            (2.2, 3.0, "#ffe0b2", "Depolarisation\n(rising phase)"),
            (3.0, 4.4, "#e3f2fd", "Repolarisation\n(falling phase)"),
            (4.4, 5.8, "#e0f2f1", "Hyper-\npolarisation"),
        ):
            ax.axvspan(x0, x1, color=col, alpha=0.7, zorder=0)
            ax.text((x0 + x1) / 2, y_hi - 3, name, ha="center", va="top",
                    fontsize=8.3, color="#455a64", style="italic")

    for mv, col, lab in (
        (rest, C["ap_rest"], f"Resting potential ({rest:g} mV)"),
        (thr, C["ap_threshold"], f"Threshold ({thr:g} mV)"),
        (0.0, "#90a4ae", "0 mV"),
        (peak, C["ap_depol"], f"Peak ({peak:+g} mV)"),
    ):
        ax.axhline(mv, color=col, lw=1.0, ls="--", zorder=1)
        ax.text(t[-1] * 0.995, mv + 1.0, lab, ha="right", va="bottom",
                fontsize=8.6, color=col, fontweight="bold")

    ax.plot(t, V, color=C["ap_curve"], lw=3.2, zorder=6,
            solid_capstyle="round")

    # threshold crossing dot
    ax.plot([2.2], [thr], "o", ms=8, color=C["ap_threshold"], zorder=7)

    if schema.show_channels:
        ax.annotate("Voltage-gated Na⁺ channels OPEN\n(Na⁺ rushes IN, inside becomes +ve)",
                    xy=(2.75, (thr + peak) / 2), xytext=(3.35, peak - 4),
                    fontsize=8.7, color=C["na_ion"], ha="left",
                    bbox=dict(boxstyle="round,pad=0.3", fc="#fff3e0",
                              ec=C["na_ion"], lw=1.0),
                    arrowprops=dict(arrowstyle="-|>", color=C["na_ion"], lw=1.2))
        ax.annotate("Na⁺ channels close, K⁺ channels OPEN\n(K⁺ moves OUT, inside becomes −ve)",
                    xy=(3.7, (peak + rest) / 2), xytext=(4.6, (0 + peak) / 2 + 2),
                    fontsize=8.7, color=C["ap_repol"], ha="left",
                    bbox=dict(boxstyle="round,pad=0.3", fc="#e3f2fd",
                              ec=C["ap_repol"], lw=1.0),
                    arrowprops=dict(arrowstyle="-|>", color=C["ap_repol"], lw=1.2))
        ax.annotate("K⁺ channels slow to close,\nundershoot below rest",
                    xy=(4.7, hyper + 1.5), xytext=(5.0, rest - 18),
                    fontsize=8.7, color=C["ap_hyper"], ha="left",
                    bbox=dict(boxstyle="round,pad=0.3", fc="#e0f2f1",
                              ec=C["ap_hyper"], lw=1.0),
                    arrowprops=dict(arrowstyle="-|>", color=C["ap_hyper"], lw=1.2))

    if schema.show_labels:
        ax.text(0.5, rest + 2.0, "Polarised\n(resting)", fontsize=8.5,
                color=C["ap_rest"], ha="center", va="bottom")

    ax.set_xlabel("Time (ms)", fontsize=11)
    ax.set_ylabel("Membrane potential (mV)", fontsize=11)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(alpha=0.15, zorder=0)
    ax.set_title(schema.title or "Action Potential across a Neuron Membrane",
                 fontsize=14, fontweight="bold", pad=8)
    fig.text(0.5, 0.015,
             "Resting −70 mV, depolarisation to threshold −55 mV, spike to "
             "+30 mV (Na⁺ in), repolarisation (K⁺ out), hyperpolarisation, then "
             "back to resting. All-or-none.",
             ha="center", fontsize=9, color="#37474f", style="italic")
    fig.tight_layout(pad=0.5, rect=(0, 0.05, 1, 1))
    return _fig_to_svg(fig)


# ═══════════════════════════════════════════════════════════════════════════════
# 35. Synapse (chemical)
# ═══════════════════════════════════════════════════════════════════════════════

def render_synapse(data: Dict[str, Any],
                   canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = SynapseSchema(**data)
    lab = schema.show_labels

    fig, ax = plt.subplots(figsize=(10.5, 9.5))
    ax.set_xlim(0, 10); ax.set_ylim(0, 10)
    ax.set_aspect("equal"); ax.axis("off")

    CLEFT_TOP, CLEFT_BOT = 5.4, 4.3          # synaptic cleft band
    # ── Pre-synaptic axon + terminal bulb ─────────────────────────────────────
    ax.add_patch(Rectangle((4.1, 9.2), 1.8, 0.9, fc="#ffe0b2",
                           ec=C["presynaptic"], lw=2.0, zorder=3))
    bulb = mpatches.FancyBboxPatch((2.4, CLEFT_TOP), 5.2, 3.9,
                                   boxstyle="round,pad=0.02,rounding_size=0.9",
                                   fc="#ffe0b2", ec=C["presynaptic"], lw=2.4,
                                   zorder=3)
    ax.add_patch(bulb)
    # mitochondrion (energy for vesicle recycling)
    ax.add_patch(Ellipse((3.4, 7.9), 1.1, 0.6, fc=C["matrix"],
                         ec=C["mitochondria"], lw=1.6, zorder=4))
    ax.plot([2.95, 3.85], [7.9, 7.9], color=C["cristae"], lw=1.0, zorder=5)

    # ── Synaptic vesicles ─────────────────────────────────────────────────────
    vesicle_pos = [(4.4, 7.6), (5.4, 7.9), (6.3, 7.2), (4.9, 6.7),
                   (6.1, 6.4), (5.5, 6.0)]
    for vx, vy in vesicle_pos:
        ax.add_patch(Circle((vx, vy), 0.34, fc="#e3f2fd",
                            ec=C["vesicle"], lw=1.8, zorder=5))
        for a in (30, 150, 270):
            ax.add_patch(Circle((vx + 0.18 * math.cos(math.radians(a)),
                                 vy + 0.18 * math.sin(math.radians(a))),
                                0.06, fc=C["neurotransmitter"], ec="none",
                                zorder=6))
    # a vesicle fusing with the pre-synaptic membrane (exocytosis)
    ax.add_patch(mpatches.Wedge((5.0, CLEFT_TOP + 0.02), 0.36, 200, 340,
                                fc="#e3f2fd", ec=C["vesicle"], lw=1.8, zorder=5))

    # ── Neurotransmitter in the cleft + receptors on post-synaptic membrane ───
    ax.axhspan(CLEFT_BOT, CLEFT_TOP, xmin=0.18, xmax=0.82,
               color=C["synaptic_cleft"], zorder=1)
    nt_dots = [(5.0, 5.0), (5.35, 4.75), (4.7, 4.7), (5.55, 5.05), (4.5, 4.95)]
    for nx, ny in nt_dots:
        ax.add_patch(Circle((nx, ny), 0.10, fc=C["neurotransmitter"],
                            ec="none", zorder=6))

    ax.add_patch(Rectangle((2.0, CLEFT_BOT - 0.9), 6.0, 0.9,
                           fc="#ede7f6", ec=C["postsynaptic"], lw=2.4, zorder=3))
    for rx in (3.2, 4.4, 5.6, 6.8):
        ax.add_patch(Rectangle((rx - 0.22, CLEFT_BOT - 0.02), 0.44, 0.30,
                               fc=C["receptor"], ec="#1b5e20", lw=1.4, zorder=5))

    # ── Ca²⁺ influx (drives vesicle fusion) — drawn arrow, never a glyph ───────
    if schema.show_neurotransmitter_flow:
        ax.add_patch(FancyArrowPatch((7.2, CLEFT_TOP - 0.55), (6.5, 6.05),
                                     arrowstyle="-|>", mutation_scale=16,
                                     lw=2.0, color=C["ca_ion"], zorder=7))
        ax.text(7.55, 6.55, "Ca²⁺ influx", fontsize=9, color=C["ca_ion"],
                ha="center", va="center", fontweight="bold")
        # neurotransmitter release + diffusion across the cleft
        for x0 in (4.7, 5.0, 5.3):
            ax.add_patch(FancyArrowPatch((x0, CLEFT_TOP - 0.15),
                                         (x0, CLEFT_BOT + 0.05),
                                         arrowstyle="-|>", mutation_scale=11,
                                         lw=1.5, color=C["neurotransmitter"],
                                         zorder=7))

    if lab:
        _annotate(ax, "Axon terminal\n(pre-synaptic knob)", (3.0, 8.6),
                  (1.0, 9.2), C["presynaptic"], fontsize=8.8)
        _annotate(ax, "Mitochondrion", (3.4, 7.9), (1.2, 7.4),
                  C["mitochondria"], fontsize=8.5)
        _annotate(ax, "Synaptic vesicles\n(neurotransmitter)", (6.3, 7.2),
                  (8.6, 8.2), C["vesicle"], fontsize=8.8)
        _annotate(ax, "Pre-synaptic membrane", (4.2, CLEFT_TOP), (1.4, 6.0),
                  C["presynaptic"], fontsize=8.5)
        _annotate(ax, "Synaptic cleft", (3.4, (CLEFT_TOP + CLEFT_BOT) / 2),
                  (1.0, 4.9), "#607d8b", fontsize=8.8)
        _annotate(ax, "Neurotransmitter", (5.35, 4.75), (9.2, 5.2),
                  C["neurotransmitter"], fontsize=8.8)
        _annotate(ax, "Receptor proteins", (6.8, CLEFT_BOT + 0.1),
                  (8.7, 3.9), C["receptor"], fontsize=8.8)
        _annotate(ax, "Post-synaptic membrane\n(next neuron / muscle)",
                  (3.0, CLEFT_BOT - 0.45), (1.0, 2.9),
                  C["postsynaptic"], fontsize=8.5)

    ax.set_title(schema.title or "Chemical Synapse — Neurotransmitter Release",
                 fontsize=14, fontweight="bold", pad=6)
    fig.text(0.5, 0.02,
             "Impulse depolarises the knob, Ca²⁺ enters, vesicles fuse and "
             "release neurotransmitter, it diffuses across the cleft and binds "
             "receptors, generating a new impulse in the post-synaptic membrane.",
             ha="center", fontsize=8.6, color="#37474f", style="italic")
    fig.tight_layout(pad=0.4, rect=(0, 0.045, 1, 1))
    return _fig_to_svg(fig)


# ═══════════════════════════════════════════════════════════════════════════════
# 36. Reflex Arc
# ═══════════════════════════════════════════════════════════════════════════════

def render_reflex_arc(data: Dict[str, Any],
                      canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = ReflexArcSchema(**data)
    poly = schema.reflex_type == "polysynaptic"
    lab = schema.show_labels

    fig, ax = plt.subplots(figsize=(12.0, 8.4))
    ax.set_xlim(0, 12); ax.set_ylim(0, 9)
    ax.set_aspect("equal"); ax.axis("off")

    # ── Spinal-cord cross section (left) ──────────────────────────────────────
    SC = (3.2, 4.5)                       # centre
    ax.add_patch(Ellipse(SC, 4.2, 5.4, fc=C["white_matter"],
                         ec="#90a4ae", lw=2.2, zorder=2))
    # dorsal (top) fissure notch + ventral (bottom) fissure
    ax.plot([SC[0], SC[0]], [SC[1] + 2.7, SC[1] + 1.5], color="#90a4ae",
            lw=1.4, zorder=3)
    # butterfly / H-shaped grey matter
    grey = Polygon([
        (SC[0] - 1.3, SC[1] + 2.0), (SC[0] - 0.35, SC[1] + 1.0),
        (SC[0] + 0.35, SC[1] + 1.0), (SC[0] + 1.3, SC[1] + 2.0),
        (SC[0] + 1.55, SC[1] + 1.2), (SC[0] + 0.6, SC[1]),
        (SC[0] + 1.5, SC[1] - 1.9), (SC[0] + 0.4, SC[1] - 1.2),
        (SC[0] - 0.4, SC[1] - 1.2), (SC[0] - 1.5, SC[1] - 1.9),
        (SC[0] - 0.6, SC[1]), (SC[0] - 1.55, SC[1] + 1.2),
    ], closed=True, fc=C["grey_matter"], ec="#6d4c41", lw=1.8, zorder=3)
    ax.add_patch(grey)
    ax.plot([SC[0], SC[0]], [SC[1] - 1.2, SC[1] + 1.0], color="#8d6e63",
            lw=1.2, zorder=4)                 # grey commissure with central canal
    ax.add_patch(Circle(SC, 0.14, fc="white", ec="#6d4c41", lw=1.0, zorder=5))

    dorsal_horn = (SC[0] + 0.9, SC[1] + 1.5)
    ventral_horn = (SC[0] + 0.9, SC[1] - 1.4)

    # ── Receptor (skin) and effector (muscle) on the right ────────────────────
    RECEPTOR = (10.8, 6.6)
    EFFECTOR = (10.6, 2.1)
    ax.add_patch(mpatches.FancyBboxPatch((9.7, 6.0), 2.0, 1.4,
                 boxstyle="round,pad=0.05", fc=C["receptor_skin"],
                 ec="#e65100", lw=2.0, zorder=3))
    ax.text(10.7, 7.15, "Skin", fontsize=8.5, ha="center", color="#e65100")
    ax.add_patch(Circle((10.2, 6.5), 0.16, fc="#e65100", ec="none", zorder=4))
    # effector muscle (striations)
    ax.add_patch(mpatches.FancyBboxPatch((9.6, 1.4), 2.2, 1.5,
                 boxstyle="round,pad=0.05", fc=C["effector"],
                 ec="#c62828", lw=2.0, zorder=3))
    for yy in np.linspace(1.55, 2.75, 6):
        ax.plot([9.7, 11.7], [yy, yy], color="#c62828", lw=0.8, zorder=4)

    # ── Dorsal root ganglion (afferent cell body) ─────────────────────────────
    DRG = (6.6, 6.6)
    ax.add_patch(Ellipse(DRG, 1.0, 0.7, fc="#f3e5f5",
                         ec=C["dorsal_ganglion"], lw=2.0, zorder=4))
    ax.add_patch(Circle(DRG, 0.16, fc=C["dorsal_ganglion"], ec="none", zorder=5))

    def path_arrow(pts, color, lw=2.4, z=6):
        for a, b in zip(pts, pts[1:]):
            ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>",
                                         mutation_scale=15, lw=lw, color=color,
                                         zorder=z,
                                         connectionstyle="arc3,rad=0.02"))

    # afferent (sensory) path: receptor → DRG → dorsal horn
    path_arrow([(RECEPTOR[0] - 1.1, RECEPTOR[1]), (DRG[0] + 0.5, DRG[1]),
                (dorsal_horn[0] + 0.3, dorsal_horn[1] + 0.25)], C["afferent"])
    # efferent (motor) path: ventral horn → ventral root → muscle
    path_arrow([(ventral_horn[0] + 0.3, ventral_horn[1] - 0.2),
                (7.4, 2.6), (EFFECTOR[0] - 1.2, EFFECTOR[1] + 0.4)],
               C["efferent"])

    if poly:
        # relay interneuron connects the two horns inside the grey matter
        ax.add_patch(Circle((SC[0] + 0.15, SC[1]), 0.28, fc="#ede7f6",
                            ec=C["interneuron"], lw=2.0, zorder=6))
        path_arrow([(dorsal_horn[0] - 0.1, dorsal_horn[1] - 0.2),
                    (SC[0] + 0.15, SC[1] + 0.3)], C["interneuron"], lw=1.8)
        path_arrow([(SC[0] + 0.15, SC[1] - 0.3),
                    (ventral_horn[0] - 0.1, ventral_horn[1] + 0.2)],
                   C["interneuron"], lw=1.8)
    else:
        # monosynaptic: sensory neuron synapses DIRECTLY on the motor neuron
        path_arrow([(dorsal_horn[0] - 0.1, dorsal_horn[1] - 0.2),
                    (ventral_horn[0] - 0.1, ventral_horn[1] + 0.2)],
                   C["afferent"], lw=1.8)

    if lab:
        ax.text(SC[0], SC[1] - 2.95, "Spinal cord (T.S.)", ha="center",
                fontsize=9.5, fontweight="bold", color="#455a64")
        _annotate(ax, "Grey matter", (SC[0] - 1.2, SC[1] + 0.2),
                  (1.0, 7.4), "#6d4c41", fontsize=8.5)
        _annotate(ax, "White matter", (SC[0] - 1.9, SC[1] - 1.5),
                  (0.9, 2.0), "#607d8b", fontsize=8.5)
        _annotate(ax, "Dorsal root ganglion", DRG, (6.4, 8.3),
                  C["dorsal_ganglion"], fontsize=8.5)
        _annotate(ax, "Receptor", (10.2, 6.5), (10.9, 8.4),
                  "#e65100", fontsize=8.7)
        _annotate(ax, "Effector muscle", (10.6, 2.1), (10.4, 0.5),
                  "#c62828", fontsize=8.7)
        ax.text(8.4, 6.95, "Sensory (afferent)\nneuron", ha="center",
                fontsize=8.3, color=C["afferent"], fontweight="bold")
        ax.text(8.4, 3.15, "Motor (efferent)\nneuron", ha="center",
                fontsize=8.3, color=C["efferent"], fontweight="bold")
        ax.text(dorsal_horn[0] + 0.15, dorsal_horn[1] + 0.55, "Dorsal\nhorn",
                fontsize=7.6, color="#5d4037", ha="center")
        ax.text(ventral_horn[0] + 0.15, ventral_horn[1] - 0.55, "Ventral\nhorn",
                fontsize=7.6, color="#5d4037", ha="center")
        if poly:
            _annotate(ax, "Relay interneuron", (SC[0] + 0.15, SC[1]),
                      (0.9, 4.6), C["interneuron"], fontsize=8.3)

    subtitle = ("Monosynaptic (e.g. knee-jerk): sensory neuron synapses "
                "directly on the motor neuron — NO interneuron." if not poly
                else "Polysynaptic (e.g. withdrawal): a relay interneuron in "
                     "the grey matter links the sensory and motor neurons.")
    ax.set_title(schema.title or
                 f"Reflex Arc — {schema.reflex_type.capitalize()}",
                 fontsize=14, fontweight="bold", pad=6)
    fig.text(0.5, 0.02,
             "Pathway: receptor, sensory neuron, spinal cord, motor neuron, "
             "effector.  " + subtitle,
             ha="center", fontsize=8.7, color="#37474f", style="italic")
    fig.tight_layout(pad=0.4, rect=(0, 0.05, 1, 1))
    return _fig_to_svg(fig)


# ═══════════════════════════════════════════════════════════════════════════════
# 37. Transcription / Translation (central dogma)
# ═══════════════════════════════════════════════════════════════════════════════

# Codon → amino-acid, used schematically for the ribosome panel. The mRNA codons
# and the tRNA anti-codons are complements of each other — that pairing IS the
# question, so both are generated from this one table.
_CODON_TABLE = [
    ("AUG", "UAC", "Met"),
    ("GCU", "CGA", "Ala"),
    ("GAA", "CUU", "Glu"),
    ("UUC", "AAG", "Phe"),
]


def _fwd_arrow(ax, a, b, color, lw=2.4, ms=18, rad=0.0, z=8):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=ms,
                                 lw=lw, color=color, zorder=z,
                                 connectionstyle=f"arc3,rad={rad}"))


def render_transcription_translation(data: Dict[str, Any],
                                     canvas_w: int = 800,
                                     canvas_h: int = 600) -> str:
    schema = TranscriptionTranslationSchema(**data)
    stage = schema.stage
    lab = schema.show_labels

    do_tx = stage in ("transcription", "both")
    do_tl = stage in ("translation", "both")

    fig, ax = plt.subplots(figsize=(12.5, 9.0 if stage == "both" else 6.2))
    if stage == "both":
        ax.set_xlim(0, 13); ax.set_ylim(0, 10)
    else:
        ax.set_xlim(0, 13); ax.set_ylim(0, 7.0)
    ax.axis("off")

    tx_y = 8.2 if stage == "both" else 3.2
    tl_y = 3.0

    if do_tx:
        # ── DNA template + coding strands ─────────────────────────────────────
        ax.plot([1.0, 11.5], [tx_y + 0.35, tx_y + 0.35], color=C["dna_coding"],
                lw=6, solid_capstyle="round", zorder=3)
        ax.plot([1.0, 11.5], [tx_y - 0.35, tx_y - 0.35], color=C["dna_tmpl"],
                lw=6, solid_capstyle="round", zorder=3)
        # RNA polymerase bubble
        ax.add_patch(Ellipse((6.5, tx_y), 2.0, 1.7, fc="#c8e6c9",
                            ec=C["rna_pol2"], lw=2.2, alpha=0.75, zorder=4))
        ax.text(6.5, tx_y + 0.02, "RNA\npolymerase", ha="center", va="center",
                fontsize=8.5, fontweight="bold", color="#1b5e20", zorder=6)
        # nascent mRNA peeling off
        ax.plot([6.5, 8.2, 9.6, 11.2], [tx_y - 0.2, tx_y - 1.1, tx_y - 1.0,
                tx_y - 1.25], color=C["mrna_strand"], lw=4,
                solid_capstyle="round", zorder=5)
        _fwd_arrow(ax, (4.2, tx_y + 1.15), (8.8, tx_y + 1.15),
                   C["rna_pol2"], lw=2.0)
        ax.text(6.5, tx_y + 1.45, "direction of transcription", ha="center",
                fontsize=8.3, color="#1b5e20")
        if lab:
            _annotate(ax, "Coding (sense) strand", (2.2, tx_y + 0.35),
                      (2.4, tx_y + 1.9), C["dna_coding"], fontsize=8.4)
            _annotate(ax, "Template (antisense) strand", (2.2, tx_y - 0.35),
                      (2.6, tx_y - 1.6), C["dna_tmpl"], fontsize=8.4)
            _annotate(ax, "mRNA transcript", (10.4, tx_y - 1.2),
                      (11.0, tx_y + 0.8), C["mrna_strand"], fontsize=8.4)
        ax.text(0.6, tx_y, "DNA", ha="right", va="center", fontsize=10,
                fontweight="bold", color="#37474f")

    if do_tx and do_tl:
        _fwd_arrow(ax, (6.5, tx_y - 1.9), (6.5, tl_y + 2.0), C["cycle_arrow"],
                   lw=2.6, ms=22)
        ax.text(6.8, (tx_y - 1.9 + tl_y + 2.0) / 2,
                "mRNA leaves nucleus", ha="left", va="center", fontsize=8.6,
                color="#455a64", style="italic")

    if do_tl:
        # ── mRNA with codons + ribosome + tRNA ────────────────────────────────
        mrna_left, mrna_right = 1.0, 12.0
        ax.add_patch(Rectangle((mrna_left, tl_y - 0.18), mrna_right - mrna_left,
                               0.36, fc=C["mrna_strand"], ec="#bf360c", lw=1.2,
                               zorder=3))
        codon_w = 1.35
        for i, (codon, anti, aa) in enumerate(_CODON_TABLE):
            cx0 = 2.0 + i * (codon_w + 0.25)
            ax.add_patch(Rectangle((cx0, tl_y - 0.16), codon_w, 0.32,
                                   fc="#ede7f6", ec=C["codon"], lw=1.2,
                                   zorder=4))
            ax.text(cx0 + codon_w / 2, tl_y, codon, ha="center", va="center",
                    fontsize=8.2, color=C["codon"], fontweight="bold", zorder=5)
            if i == 1:                          # tRNA docked at the second codon
                trna_x = cx0 + codon_w / 2
                ax.add_patch(Polygon([(trna_x - 0.55, tl_y + 0.9),
                                      (trna_x + 0.55, tl_y + 0.9),
                                      (trna_x, tl_y + 0.30)], closed=True,
                                     fc="#e0f2f1", ec=C["trna"], lw=1.8,
                                     zorder=6))
                ax.text(trna_x, tl_y + 0.62, anti, ha="center", va="center",
                        fontsize=8.0, color=C["trna"], fontweight="bold",
                        zorder=7)
                ax.add_patch(Circle((trna_x, tl_y + 1.15), 0.22,
                                    fc=C["aminoacid"], ec="#880e4f", lw=1.4,
                                    zorder=7))
                ax.text(trna_x, tl_y + 1.15, aa, ha="center", va="center",
                        fontsize=7.2, color="white", zorder=8)
                if lab:
                    _annotate(ax, "tRNA (anti-codon)",
                              (trna_x - 0.4, tl_y + 0.75), (trna_x - 2.6,
                              tl_y + 1.4), C["trna"], fontsize=8.3)
                    _annotate(ax, "Amino acid", (trna_x, tl_y + 1.35),
                              (trna_x + 1.9, tl_y + 1.9), C["aminoacid"],
                              fontsize=8.3)

        # ribosome straddling the mRNA
        rib_x = 2.0 + 1 * (codon_w + 0.25) + codon_w / 2
        ax.add_patch(mpatches.FancyBboxPatch((rib_x - 1.15, tl_y + 0.20), 2.3,
                     0.95, boxstyle="round,pad=0.05,rounding_size=0.3",
                     fc="#d7ccc8", ec=C["ribosome_l"], lw=2.0, alpha=0.55,
                     zorder=5))
        ax.add_patch(mpatches.FancyBboxPatch((rib_x - 1.15, tl_y - 0.55), 2.3,
                     0.55, boxstyle="round,pad=0.05,rounding_size=0.3",
                     fc="#bcaaa4", ec=C["ribosome_l"], lw=2.0, alpha=0.55,
                     zorder=5))
        _fwd_arrow(ax, (rib_x + 1.3, tl_y - 1.0), (rib_x + 2.6, tl_y - 1.0),
                   C["ribosome_l"], lw=2.0)
        ax.text(rib_x + 1.9, tl_y - 1.35, "ribosome moves 5' to 3'",
                ha="center", fontsize=8.0, color=C["ribosome_l"])

        # growing polypeptide chain
        px = np.array([rib_x - 1.5, rib_x - 2.1, rib_x - 2.8, rib_x - 3.4])
        py = tl_y + 2.35 + 0.30 * np.sin(np.arange(len(px)))
        for i in range(len(px)):
            ax.add_patch(Circle((px[i], py[i]), 0.24, fc=C["aminoacid"],
                                ec="#880e4f", lw=1.2, zorder=7))
            if i:
                ax.plot([px[i - 1], px[i]], [py[i - 1], py[i]],
                        color="#880e4f", lw=1.4, zorder=6)
        if lab:
            _annotate(ax, "Ribosome", (rib_x, tl_y + 0.7), (rib_x + 2.6,
                      tl_y + 1.0), C["ribosome_l"], fontsize=8.4)
            _annotate(ax, "mRNA (codons)", (2.6, tl_y - 0.16),
                      (1.6, tl_y - 1.2), C["mrna_strand"], fontsize=8.4)
            _annotate(ax, "Polypeptide (protein)", (px[-1], py[-1]),
                      (px[-1] - 0.2, tl_y + 3.4), C["aminoacid"], fontsize=8.4)
        ax.text(0.6, tl_y, "mRNA", ha="right", va="center", fontsize=10,
                fontweight="bold", color="#37474f")

    titles = {
        "transcription": "Transcription — DNA to mRNA",
        "translation": "Translation — mRNA to Protein",
        "both": "Central Dogma — DNA to RNA to Protein",
    }
    notes = {
        "transcription": "RNA polymerase reads the template (antisense) strand "
                         "3' to 5' and builds an mRNA complementary to it (U "
                         "replaces T).",
        "translation": "The ribosome reads mRNA codons 5' to 3'; each tRNA "
                       "anti-codon base-pairs with a codon and adds its amino "
                       "acid to the chain.",
        "both": "DNA is transcribed to mRNA (in the nucleus) which is "
                "translated to protein on ribosomes (in the cytoplasm).",
    }
    ax.set_title(schema.title or titles[stage], fontsize=14,
                 fontweight="bold", pad=6)
    fig.text(0.5, 0.02, _wrap(notes[stage], 118), ha="center", fontsize=8.8,
             color="#37474f", style="italic")
    fig.tight_layout(pad=0.4, rect=(0, 0.05, 1, 1))
    return _fig_to_svg(fig)


# ═══════════════════════════════════════════════════════════════════════════════
# 38. Oxygen (Haemoglobin) Dissociation Curve
# ═══════════════════════════════════════════════════════════════════════════════

def _hb_saturation(pO2, p50: float, n: float):
    """Hill equation — % saturation of Hb with O₂.

    n > 1 (co-operative binding) gives the SIGMOID curve of haemoglobin;
    n = 1 gives the rectangular hyperbola of myoglobin. p50 is the pO₂ at 50 %
    saturation, so a RIGHT shift (unloading) IS a larger p50.
    """
    pO2 = np.asarray(pO2, dtype=float)
    return 100.0 * pO2 ** n / (p50 ** n + pO2 ** n)


# p50 in mmHg. Right shift = larger p50 (O₂ released more easily to tissues).
_ODC_CURVES = {
    "normal":     {"p50": 26.0, "n": 2.8, "color": "odc_normal",
                   "label": "Normal Hb (pH 7.4, 37 °C)"},
    "bohr_right": {"p50": 34.0, "n": 2.8, "color": "odc_right",
                   "label": "Right shift (more CO₂, higher temp, lower pH, "
                            "more BPG)"},
    "bohr_left":  {"p50": 19.0, "n": 2.8, "color": "odc_left",
                   "label": "Left shift (less CO₂, lower temp, higher pH)"},
    "myoglobin":  {"p50": 5.0, "n": 1.0, "color": "odc_myoglobin",
                   "label": "Myoglobin (n = 1, hyperbolic)"},
}


def render_oxygen_dissociation_curve(data: Dict[str, Any],
                                     canvas_w: int = 800,
                                     canvas_h: int = 600) -> str:
    schema = OxygenDissociationCurveSchema(**data)
    keys = list(schema.curves)
    if schema.show_bohr_shift and "bohr_right" not in keys and "normal" in keys:
        keys.append("bohr_right")

    fig, ax = plt.subplots(figsize=(11, 7.2))
    x = np.linspace(0.5, 100, 500)
    ax.set_xlim(0, 100); ax.set_ylim(0, 105)

    if schema.show_loading_unloading:
        for xv, name, col in ((40, "Tissues\n(pO₂ ≈ 40)", "#8d6e63"),
                              (100, "Lungs\n(pO₂ ≈ 100)", "#c62828")):
            ax.axvline(xv, color=col, lw=1.0, ls=":", zorder=1)
            ax.text(xv - 1.2, 3, name, ha="right", va="bottom", fontsize=8.3,
                    color=col, style="italic")

    for key in keys:
        spec = _ODC_CURVES[key]
        y = _hb_saturation(x, spec["p50"], spec["n"])
        ax.plot(x, y, color=C[spec["color"]], lw=3.0, zorder=5,
                label=spec["label"])
        if schema.show_p50:
            p50 = spec["p50"]
            ax.plot([p50], [50], "o", ms=8, color=C[spec["color"]], zorder=6)
            ax.plot([p50, p50], [0, 50], color=C[spec["color"]], lw=0.9,
                    ls="--", zorder=2)
            ax.text(p50, 52, f"p50={p50:g}", ha="center", va="bottom",
                    fontsize=8.0, color=C[spec["color"]], fontweight="bold")

    ax.axhline(50, color="#b0bec5", lw=0.9, ls=":", zorder=1)

    # ── Bohr shift arrow (drawn as a patch, never a glyph) ────────────────────
    if schema.show_bohr_shift and "normal" in keys and "bohr_right" in keys:
        ax.add_patch(FancyArrowPatch((26, 50), (34, 50), arrowstyle="-|>",
                                     mutation_scale=20, lw=2.6,
                                     color=C["ap_threshold"], zorder=7))
        ax.text(30, 44, "Bohr\nshift", ha="center", va="top", fontsize=9,
                color=C["ap_threshold"], fontweight="bold")

    ax.set_xlabel("Partial pressure of O₂,  pO₂ (mmHg)", fontsize=11)
    ax.set_ylabel("% saturation of haemoglobin with O₂", fontsize=11)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(alpha=0.15, zorder=0)
    ax.legend(loc="lower right", fontsize=8.8, framealpha=0.95)
    ax.set_title(schema.title or "Oxygen–Haemoglobin Dissociation Curve",
                 fontsize=14, fontweight="bold", pad=8)
    fig.text(0.5, 0.015,
             "The sigmoid curve reflects co-operative O₂ binding. A RIGHT shift "
             "(larger p50) means Hb unloads O₂ more readily to actively "
             "respiring tissues — the Bohr effect.",
             ha="center", fontsize=9, color="#37474f", style="italic")
    fig.tight_layout(pad=0.5, rect=(0, 0.05, 1, 1))
    return _fig_to_svg(fig)


# ═══════════════════════════════════════════════════════════════════════════════
# 39. Circulatory System (double circulation)
# ═══════════════════════════════════════════════════════════════════════════════

def render_circulatory_system(data: Dict[str, Any],
                              canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = CirculatorySystemSchema(**data)
    lab = schema.show_labels
    hl = schema.highlight_circuit

    fig, ax = plt.subplots(figsize=(10.5, 10.0))
    ax.set_xlim(0, 10); ax.set_ylim(0, 10.5)
    ax.set_aspect("equal"); ax.axis("off")

    OXY, DEOXY = C["oxy_blood"], C["deoxy_blood"]

    def alpha_for(circuit):
        if hl is None:
            return 1.0
        return 1.0 if hl == circuit else 0.28

    # ── Lungs (top) ───────────────────────────────────────────────────────────
    for cx in (3.2, 6.8):
        ax.add_patch(Ellipse((cx, 8.9), 1.7, 1.7, fc=C["lungs_circ"],
                             ec="#c62828", lw=1.8, zorder=3))
    ax.text(5.0, 9.9, "LUNGS", ha="center", fontsize=10, fontweight="bold",
            color="#c62828")
    ax.text(5.0, 8.35, "gas exchange\n(O₂ in, CO₂ out)", ha="center",
            fontsize=8, color="#880e4f", style="italic")

    # ── Body tissues (bottom) ─────────────────────────────────────────────────
    ax.add_patch(mpatches.FancyBboxPatch((3.0, 0.5), 4.0, 1.5,
                 boxstyle="round,pad=0.1", fc=C["body_circ"], ec="#607d8b",
                 lw=1.8, zorder=3))
    ax.text(5.0, 1.25, "BODY TISSUES", ha="center", fontsize=10,
            fontweight="bold", color="#455a64")

    # ── Heart (centre): RA/RV deoxygenated (blue), LA/LV oxygenated (red) ──────
    heart_cx, heart_cy = 5.0, 5.0
    # right side (deoxygenated) — patient's right = image left
    ax.add_patch(mpatches.FancyBboxPatch((3.3, 5.05), 1.5, 1.15,
                 boxstyle="round,pad=0.03", fc="#bbdefb", ec=DEOXY, lw=2.0,
                 zorder=4))
    ax.text(4.05, 5.62, "Right\natrium", ha="center", va="center",
            fontsize=8, color=DEOXY, fontweight="bold", zorder=5)
    ax.add_patch(mpatches.FancyBboxPatch((3.3, 3.5), 1.5, 1.45,
                 boxstyle="round,pad=0.03", fc="#90caf9", ec=DEOXY, lw=2.0,
                 zorder=4))
    ax.text(4.05, 4.2, "Right\nventricle", ha="center", va="center",
            fontsize=8, color=DEOXY, fontweight="bold", zorder=5)
    # left side (oxygenated)
    ax.add_patch(mpatches.FancyBboxPatch((5.2, 5.05), 1.5, 1.15,
                 boxstyle="round,pad=0.03", fc="#ffcdd2", ec=OXY, lw=2.0,
                 zorder=4))
    ax.text(5.95, 5.62, "Left\natrium", ha="center", va="center",
            fontsize=8, color=OXY, fontweight="bold", zorder=5)
    ax.add_patch(mpatches.FancyBboxPatch((5.2, 3.5), 1.5, 1.45,
                 boxstyle="round,pad=0.03", fc="#ef9a9a", ec=OXY, lw=2.0,
                 zorder=4))
    ax.text(5.95, 4.2, "Left\nventricle", ha="center", va="center",
            fontsize=8, color=OXY, fontweight="bold", zorder=5)
    ax.text(heart_cx, 6.55, "HEART", ha="center", fontsize=10.5,
            fontweight="bold", color=C["heart_muscle"])

    def flow(a, b, color, circuit, rad=0.0, lw=3.2, label=None, lx=0, ly=0):
        al = alpha_for(circuit)
        ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=18,
                                     lw=lw, color=color, alpha=al, zorder=6,
                                     connectionstyle=f"arc3,rad={rad}"))
        if label and lab:
            ax.text(lx, ly, label, fontsize=7.8, color=color, alpha=al,
                    ha="center", va="center", fontweight="bold", zorder=7,
                    bbox=dict(boxstyle="round,pad=0.15", fc="white",
                              ec=color, lw=0.8, alpha=al))

    # ── Pulmonary circuit (heart → lungs → heart) ─────────────────────────────
    # pulmonary artery leaves the RIGHT VENTRICLE (deoxygenated blood to lungs)
    flow((4.05, 4.6), (3.05, 7.9), DEOXY, "pulmonary", rad=-0.25,
         label="Pulmonary artery\n(deoxygenated)", lx=2.15, ly=6.6)
    flow((6.6, 7.9), (5.95, 5.05), OXY, "pulmonary", rad=-0.25,
         label="Pulmonary vein\n(oxygenated)", lx=7.9, ly=6.6)

    # ── Systemic circuit (heart → body → heart) ───────────────────────────────
    flow((6.0, 3.5), (6.0, 1.95), OXY, "systemic", rad=0.0,
         label="Aorta\n(oxygenated)", lx=7.3, ly=2.9)
    flow((4.0, 2.0), (4.0, 5.05), DEOXY, "systemic", rad=0.25,
         label="Vena cava\n(deoxygenated)", lx=2.35, ly=3.2)

    # internal transfers
    flow((4.05, 5.05), (4.05, 4.9), DEOXY, "pulmonary", lw=2.2)
    flow((5.95, 5.05), (5.95, 4.9), OXY, "systemic", lw=2.2)

    if lab:
        legend = [
            mpatches.Patch(color=OXY, label="Oxygenated blood"),
            mpatches.Patch(color=DEOXY, label="Deoxygenated blood"),
        ]
        ax.legend(handles=legend, loc="upper left", fontsize=8.6,
                  framealpha=0.95)

    ax.set_title(schema.title or "Double Circulation in Humans",
                 fontsize=14, fontweight="bold", pad=6)
    fig.text(0.5, 0.02,
             "Blood passes through the heart TWICE per cycle: pulmonary "
             "circuit (right heart, lungs, back to left heart) and systemic "
             "circuit (left heart, body, back to right heart). The pulmonary "
             "artery is the only artery carrying deoxygenated blood.",
             ha="center", fontsize=8.6, color="#37474f", style="italic")
    fig.tight_layout(pad=0.4, rect=(0, 0.05, 1, 1))
    return _fig_to_svg(fig)


# ═══════════════════════════════════════════════════════════════════════════════
# 40. Menstrual Cycle
# ═══════════════════════════════════════════════════════════════════════════════

def _gauss(x, mu, sig, amp):
    return amp * np.exp(-0.5 * ((x - mu) / sig) ** 2)


def render_menstrual_cycle(data: Dict[str, Any],
                           canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = MenstrualCycleSchema(**data)
    D = schema.cycle_days
    ov = round(D / 2)                     # ovulation ~ mid-cycle (day 14 for 28)
    x = np.linspace(1, D, 400)

    rows = sum([schema.show_hormones, schema.show_ovarian_phase,
                schema.show_uterine_lining]) or 1
    fig, axes = plt.subplots(rows, 1, figsize=(11.5, 2.7 * rows + 0.8),
                             sharex=True)
    if rows == 1:
        axes = [axes]
    axes = list(axes)
    ai = 0

    # ── Hormones ──────────────────────────────────────────────────────────────
    if schema.show_hormones:
        ax = axes[ai]; ai += 1
        fsh = 0.18 + _gauss(x, 3, 3.2, 0.5) + _gauss(x, ov, 1.1, 0.55)
        lh = 0.15 + _gauss(x, ov - 0.5, 0.9, 1.0)
        oest = 0.10 + _gauss(x, ov - 1.5, 2.6, 0.85) + _gauss(x, ov + 7, 3.2, 0.42)
        prog = 0.08 + _gauss(x, ov + 7, 3.6, 0.95)
        for arr, key, name in ((fsh, "hormone_fsh", "FSH"),
                               (lh, "hormone_lh", "LH"),
                               (oest, "hormone_oestrogen", "Oestrogen"),
                               (prog, "hormone_progest", "Progesterone")):
            ax.plot(x, arr, color=C[key], lw=2.4, label=name, zorder=5)
        ax.annotate("LH surge\ntriggers ovulation", xy=(ov - 0.5, 1.15),
                    xytext=(ov + 2.5, 1.05), fontsize=8.3, color=C["hormone_lh"],
                    fontweight="bold",
                    arrowprops=dict(arrowstyle="-|>", color=C["hormone_lh"],
                                    lw=1.2))
        ax.set_ylim(0, 1.4)
        ax.set_ylabel("Pituitary &\novarian hormones", fontsize=9.5)
        ax.legend(loc="upper left", fontsize=8, ncol=4, framealpha=0.9)
        ax.set_title("Hormonal, ovarian and uterine events of the menstrual "
                     "cycle", fontsize=12.5, fontweight="bold", pad=6)

    # ── Ovarian cycle ─────────────────────────────────────────────────────────
    if schema.show_ovarian_phase:
        ax = axes[ai]; ai += 1
        ax.set_ylim(0, 1); ax.set_yticks([])
        for x0, x1, col, name in (
            (1, ov - 0.5, C["phase_log"], "Follicular phase"),
            (ov - 0.5, ov + 0.5, "#ffe0b2", "Ovulation"),
            (ov + 0.5, D, "#fff3e0", "Luteal phase"),
        ):
            ax.axvspan(x0, x1, color=col, zorder=0)
            ax.text((x0 + x1) / 2, 0.12, name, ha="center", fontsize=8.5,
                    color="#455a64", style="italic")
        # follicle maturation, ovulation, corpus luteum
        for i, day in enumerate(np.linspace(2, ov - 2, 4)):
            ax.add_patch(Circle((day, 0.6), 0.06 + i * 0.04,
                                fc=C["follicle"], ec="#f57f17", lw=1.2,
                                zorder=4))
        ax.add_patch(Circle((ov, 0.6), 0.18, fc="none", ec="#e65100",
                            lw=1.6, ls="--", zorder=4))
        ax.plot([ov], [0.6], "*", ms=15, color="#e65100", zorder=5)
        for day in (ov + 3, ov + 7):
            ax.add_patch(Circle((day, 0.6), 0.18, fc=C["corpus_luteum"],
                                ec="#e65100", lw=1.4, zorder=4))
        ax.add_patch(Circle((D - 1.5, 0.6), 0.10, fc="#bcaaa4",
                            ec="#6d4c41", lw=1.2, zorder=4))
        ax.annotate("Ovulation", xy=(ov, 0.78), xytext=(ov, 0.95),
                    ha="center", fontsize=8.3, color="#e65100",
                    fontweight="bold",
                    arrowprops=dict(arrowstyle="-|>", color="#e65100", lw=1.0))
        ax.text(ov + 5, 0.85, "Corpus luteum", ha="center", fontsize=8,
                color=C["corpus_luteum"])
        ax.text(D - 1.5, 0.85, "Corpus\nalbicans", ha="center", fontsize=7.5,
                color="#6d4c41")
        ax.set_ylabel("Ovarian\ncycle", fontsize=9.5)

    # ── Uterine lining ────────────────────────────────────────────────────────
    if schema.show_uterine_lining:
        ax = axes[ai]; ai += 1
        thick = np.piecewise(
            x,
            [x <= 5, (x > 5) & (x <= ov), x > ov],
            [lambda t: 2.2 - 0.3 * t / 5,
             lambda t: 1.9 + (t - 5) / (ov - 5) * 3.1,
             lambda t: 5.0 + _gauss(t, ov + 7, 4.0, 2.2) - np.clip(
                 (t - (D - 2)) * 1.4, 0, 3)],
        )
        ax.fill_between(x, 0, thick, color=C["uterine_lining"], alpha=0.55,
                        zorder=3)
        ax.plot(x, thick, color="#ad1457", lw=1.8, zorder=4)
        ax.axvspan(1, 5, color="#ffcdd2", alpha=0.6, zorder=0)
        ax.text(3, 6.5, "Menstruation\n(lining shed)", ha="center",
                fontsize=8, color="#c62828", style="italic")
        ax.text((5 + ov) / 2, 6.5, "Proliferative phase", ha="center",
                fontsize=8, color="#455a64", style="italic")
        ax.text((ov + D) / 2, 6.5, "Secretory phase", ha="center",
                fontsize=8, color="#455a64", style="italic")
        ax.set_ylim(0, 7.5)
        ax.set_ylabel("Endometrial\nthickness", fontsize=9.5)

    axes[-1].set_xlabel("Day of cycle", fontsize=11)
    axes[-1].set_xlim(1, D)
    axes[-1].set_xticks(list(range(0, D + 1, 2)))
    for ax in axes:
        ax.axvline(ov, color="#e65100", lw=0.9, ls=":", zorder=1)
        ax.spines[["top", "right"]].set_visible(False)

    fig.text(0.5, 0.01,
             f"Day {ov}: the mid-cycle LH surge (driven by peak oestrogen) "
             "triggers ovulation; the corpus luteum then secretes progesterone "
             "to maintain the thickened endometrium.",
             ha="center", fontsize=8.6, color="#37474f", style="italic")
    fig.tight_layout(pad=0.5, rect=(0, 0.04, 1, 1))
    return _fig_to_svg(fig)


# ═══════════════════════════════════════════════════════════════════════════════
# 41. Embryo Development
# ═══════════════════════════════════════════════════════════════════════════════

def _blastomere_cluster(ax, cx, cy, r, n, col, seed=0):
    """n cells packed inside a circle of radius r (deterministic layout)."""
    rng = np.random.RandomState(seed)
    ax.add_patch(Circle((cx, cy), r, fc="#f3e5f5", ec="#8d6e63", lw=1.6,
                        zorder=3))
    if n == 1:
        pts = [(cx, cy)]
    elif n <= 8:
        ang = np.linspace(0, 2 * np.pi, n, endpoint=False) + 0.3
        rr = r * 0.45
        pts = [(cx + rr * np.cos(a), cy + rr * np.sin(a)) for a in ang]
    else:
        pts = []
        for _ in range(n):
            a = rng.uniform(0, 2 * np.pi); d = r * 0.72 * math.sqrt(rng.uniform())
            pts.append((cx + d * math.cos(a), cy + d * math.sin(a)))
    cr = max(0.06, r * (0.5 if n == 1 else 0.9 / math.sqrt(n)))
    for px, py in pts:
        ax.add_patch(Circle((px, py), cr, fc=col, ec="#4a148c", lw=1.0,
                            zorder=4))


def render_embryo_development(data: Dict[str, Any],
                             canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = EmbryoDevelopmentSchema(**data)
    lab = schema.show_labels

    if schema.stage == "placenta":
        return _render_placenta(schema)

    stages = [
        ("zygote", "Zygote (2n)\n1 cell", 1),
        ("cleavage", "Cleavage\n(2, 4, 8-cell)", 8),
        ("morula", "Morula\n(solid ball, ~16–32)", 20),
        ("blastula", "Blastocyst\n(hollow, with cavity)", 0),
        ("gastrula", "Gastrula\n(3 germ layers)", 0),
    ]
    if schema.stage != "all":
        stages = [s for s in stages if s[0] == schema.stage] or stages

    n = len(stages)
    STEP = 3.6
    fig, ax = plt.subplots(figsize=(STEP * n + 1, 5.6))
    ax.set_xlim(0, n * STEP); ax.set_ylim(0, 5.6)
    ax.set_aspect("equal"); ax.axis("off")
    r = 1.05
    cy = 3.4

    for i, (key, name, ncell) in enumerate(stages):
        cx = 1.8 + i * STEP
        if key == "blastula":
            ax.add_patch(Circle((cx, cy), r, fc=C["blastocoel"],
                                ec=C["trophoblast"], lw=2.0, zorder=3))
            ang = np.linspace(0, 2 * np.pi, 18, endpoint=False)
            for a in ang:
                ax.add_patch(Circle((cx + r * 0.86 * math.cos(a),
                                     cy + r * 0.86 * math.sin(a)), 0.10,
                                    fc=C["trophoblast"], ec="#5d4037", lw=0.8,
                                    zorder=4))
            # inner cell mass at one pole
            for dx, dy in [(-0.15, 0.55), (0.15, 0.62), (0.0, 0.42),
                           (0.3, 0.5), (-0.3, 0.48)]:
                ax.add_patch(Circle((cx + dx, cy + dy), 0.14, fc=C["icm"],
                                    ec="#880e4f", lw=1.0, zorder=5))
            if lab:
                ax.text(cx, cy - 0.05, "blastocoel", ha="center", fontsize=7,
                        color="#5d4037", style="italic")
                _annotate(ax, "Inner cell mass\n(embryoblast)", (cx, cy + 0.55),
                          (cx, cy + 1.9), C["icm"], fontsize=7.6)
                _annotate(ax, "Trophoblast", (cx + r * 0.86, cy),
                          (cx + 1.4, cy - 1.3), C["trophoblast"], fontsize=7.6)
        elif key == "gastrula":
            ax.add_patch(Circle((cx, cy), r, fc="#eceff1", ec="#607d8b",
                                lw=1.8, zorder=3))
            for rr, col, gname in ((0.95, C["ectoderm"], "Ectoderm"),
                                   (0.62, C["mesoderm"], "Mesoderm"),
                                   (0.32, C["endoderm"], "Endoderm")):
                ax.add_patch(Circle((cx, cy), rr, fc="none", ec=col, lw=3.0,
                                    zorder=4))
            if lab:
                _annotate(ax, "Ectoderm", (cx, cy + 0.95), (cx - 0.2, cy + 1.9),
                          C["ectoderm"], fontsize=7.4)
                _annotate(ax, "Mesoderm", (cx + 0.44, cy - 0.44),
                          (cx + 1.5, cy - 1.0), C["mesoderm"], fontsize=7.4)
                _annotate(ax, "Endoderm", (cx, cy - 0.32), (cx - 1.4, cy - 1.2),
                          C["endoderm"], fontsize=7.4)
        else:
            _blastomere_cluster(ax, cx, cy, r, ncell, C["blastomere"], seed=i)

        ax.text(cx, cy - 1.7, name, ha="center", va="top", fontsize=8.8,
                fontweight="bold", color="#37474f")

        if i < n - 1:
            ax.add_patch(FancyArrowPatch((cx + r + 0.15, cy),
                                         (cx + STEP - r - 0.15, cy),
                                         arrowstyle="-|>", mutation_scale=16,
                                         lw=2.2, color=C["cycle_arrow"],
                                         zorder=2))

    ax.text(1.8, cy + 1.9, "mitotic cleavage divisions (cell number rises, "
            "total size stays ~constant)", ha="left", fontsize=8,
            color="#607d8b", style="italic")
    ax.set_title(schema.title or "Early Embryonic Development",
                 fontsize=14, fontweight="bold", pad=6)
    fig.text(0.5, 0.02,
             "Zygote, then repeated cleavage, solid morula, hollow blastocyst "
             "(trophoblast + inner cell mass), and gastrula with the three "
             "primary germ layers (ectoderm, mesoderm, endoderm).",
             ha="center", fontsize=8.6, color="#37474f", style="italic")
    fig.tight_layout(pad=0.4, rect=(0, 0.05, 1, 1))
    return _fig_to_svg(fig)


def _render_placenta(schema) -> str:
    lab = schema.show_labels
    fig, ax = plt.subplots(figsize=(10.0, 9.0))
    ax.set_xlim(0, 10); ax.set_ylim(0, 9)
    ax.set_aspect("equal"); ax.axis("off")

    # uterine (maternal) wall
    ax.add_patch(mpatches.Wedge((5, 11.5), 8.2, 200, 340, width=2.2,
                                fc="#f8bbd0", ec="#ad1457", lw=2.0, zorder=2))
    # placental disc
    ax.add_patch(mpatches.Wedge((5, 11.5), 6.0, 205, 335, width=1.6,
                                fc="#ef9a9a", ec="#c62828", lw=1.8, zorder=3))
    # chorionic villi projecting into maternal blood sinuses
    for a in np.linspace(212, 328, 9):
        r0, r1 = 5.9, 5.0
        ax0 = 5 + r0 * math.cos(math.radians(a))
        ay0 = 11.5 + r0 * math.sin(math.radians(a))
        ax1 = 5 + r1 * math.cos(math.radians(a))
        ay1 = 11.5 + r1 * math.sin(math.radians(a))
        ax.plot([ax0, ax1], [ay0, ay1], color=C["chorionic_villi"], lw=2.6,
                solid_capstyle="round", zorder=4)
        ax.add_patch(Circle((ax1, ay1), 0.16, fc=C["chorionic_villi"],
                            ec="#880e4f", lw=1.0, zorder=5))

    # umbilical cord + foetus
    ax.add_patch(FancyArrowPatch((5, 5.5), (5, 3.4), arrowstyle="-",
                                 lw=6, color=C["umbilical"], zorder=4))
    ax.plot([5, 5], [5.5, 3.4], color="#004d40", lw=1.0, ls=":", zorder=5)
    ax.add_patch(Ellipse((5, 2.4), 2.6, 2.0, fc="#ffe0b2", ec="#8d6e63",
                        lw=2.0, zorder=3))
    ax.add_patch(Circle((4.5, 2.6), 0.5, fc="#ffcc80", ec="#8d6e63", lw=1.5,
                        zorder=4))
    ax.text(5.4, 1.9, "Foetus", ha="center", fontsize=9, color="#6d4c41")

    if lab:
        _annotate(ax, "Uterine wall\n(maternal tissue)", (5, 9.4), (8.3, 8.4),
                  "#ad1457", fontsize=8.4)
        _annotate(ax, "Maternal blood\nsinus", (3.0, 6.6), (0.8, 7.6),
                  "#c62828", fontsize=8.4)
        _annotate(ax, "Chorionic villi\n(foetal)", (6.3, 6.1), (8.4, 6.3),
                  C["chorionic_villi"], fontsize=8.4)
        _annotate(ax, "Umbilical cord\n(2 arteries, 1 vein)", (5, 4.4),
                  (2.0, 4.2), C["umbilical"], fontsize=8.4)

    ax.set_title(schema.title or "Placenta and Foetal Membranes",
                 fontsize=14, fontweight="bold", pad=6)
    fig.text(0.5, 0.03,
             "Chorionic villi of the foetus project into maternal blood "
             "sinuses; the two circulations stay separate but exchange O₂, "
             "nutrients and wastes across the placental barrier.",
             ha="center", fontsize=8.6, color="#37474f", style="italic")
    fig.tight_layout(pad=0.4, rect=(0, 0.05, 1, 1))
    return _fig_to_svg(fig)


# ═══════════════════════════════════════════════════════════════════════════════
# 42. Seed Structure
# ═══════════════════════════════════════════════════════════════════════════════

def _germination_inset(ax, x0, y0, kind):
    """Small two-panel seedling sketch: epigeal lifts cotyledons above soil,
    hypogeal leaves them below."""
    soil = y0 + 0.35
    ax.plot([x0 - 0.9, x0 + 2.4], [soil, soil], color="#6d4c41", lw=1.6,
            zorder=3)
    ax.plot([x0 - 0.9, x0 + 2.4], [soil - 0.12, soil - 0.12], color="#a1887f",
            lw=1.0, ls=":", zorder=3)
    if kind == "epigeal":
        ax.plot([x0, x0], [soil, y0 + 1.6], color="#2e7d32", lw=2.2, zorder=4)
        for s in (-1, 1):
            ax.add_patch(Ellipse((x0 + s * 0.45, y0 + 1.75), 0.7, 0.32,
                                fc=C["cotyledon"], ec="#33691e", lw=1.2,
                                zorder=5))
        ax.text(x0 + 0.75, y0 + 1.95, "cotyledons\nraised above soil",
                fontsize=7, color="#33691e", va="center")
    else:
        ax.plot([x0, x0], [soil, y0 + 1.6], color="#2e7d32", lw=2.2, zorder=4)
        ax.add_patch(Ellipse((x0, soil - 0.35), 0.7, 0.3, fc=C["cotyledon"],
                            ec="#33691e", lw=1.2, zorder=5))
        ax.text(x0 + 0.55, soil - 0.35, "cotyledon stays\nbelow soil",
                fontsize=7, color="#33691e", va="center")
    ax.plot([x0, x0 - 0.3], [soil, soil - 0.7], color="#8d6e63", lw=1.6,
            zorder=4)
    ax.plot([x0, x0 + 0.25], [soil, soil - 0.6], color="#8d6e63", lw=1.4,
            zorder=4)


def render_seed_structure(data: Dict[str, Any],
                          canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = SeedStructureSchema(**data)
    lab = schema.show_labels
    dicot = schema.seed_type == "dicot"

    fig, ax = plt.subplots(figsize=(11, 8.4))
    ax.set_xlim(0, 11); ax.set_ylim(0, 8.4)
    ax.set_aspect("equal"); ax.axis("off")
    cx, cy = 3.6, 5.0

    if dicot:
        # bean (kidney-shaped) L.S. — two cotyledons + embryo axis
        outer = Ellipse((cx, cy), 4.2, 3.0, fc="#efebe9", ec=C["testa"],
                        lw=2.6, zorder=2)
        ax.add_patch(outer)
        ax.add_patch(Ellipse((cx, cy), 3.7, 2.5, fc="#f1f8e9", ec="#a1887f",
                            lw=1.0, zorder=3))
        # two cotyledons (fill most of the seed)
        ax.add_patch(mpatches.Wedge((cx, cy), 1.7, 95, 265, width=1.55,
                     fc=C["cotyledon"], ec="#33691e", lw=1.8, zorder=4))
        ax.add_patch(mpatches.Wedge((cx, cy), 1.7, -85, 85, width=1.55,
                     fc="#c5e1a5", ec="#33691e", lw=1.8, zorder=4))
        # embryo axis: plumule (up) + radicle (down) toward micropyle end
        ax.add_patch(FancyArrowPatch((cx, cy + 0.2), (cx, cy + 1.25),
                     arrowstyle="-", lw=3.0, color=C["plumule"], zorder=6))
        ax.add_patch(FancyArrowPatch((cx, cy - 0.2), (cx - 1.9, cy - 1.0),
                     arrowstyle="-", lw=3.4, color=C["radicle"], zorder=6))
        ax.add_patch(Circle((cx, cy + 1.25), 0.18, fc=C["plumule"],
                            ec="#1b5e20", lw=1.0, zorder=7))
        # hilum + micropyle on the concave (left) side
        ax.add_patch(Ellipse((cx - 2.05, cy - 0.55), 0.30, 0.16,
                            fc="#5d4037", ec="#3e2723", lw=1.0, zorder=6))
        ax.add_patch(Circle((cx - 2.12, cy - 0.95), 0.07, fc="#37474f",
                            ec="none", zorder=7))
        if lab:
            _annotate(ax, "Testa (seed coat)", (cx + 2.0, cy + 0.4),
                      (cx + 3.6, cy + 1.9), C["testa"], fontsize=8.3)
            _annotate(ax, "Cotyledon (2)\nfood store", (cx + 0.9, cy + 1.0),
                      (cx + 3.4, cy + 0.6), "#33691e", fontsize=8.3)
            _annotate(ax, "Plumule\n(future shoot)", (cx, cy + 1.25),
                      (cx + 2.6, cy + 2.6), C["plumule"], fontsize=8.3)
            _annotate(ax, "Radicle\n(future root)", (cx - 1.4, cy - 0.75),
                      (cx - 0.4, cy - 2.5), C["radicle"], fontsize=8.3)
            _annotate(ax, "Hilum", (cx - 2.05, cy - 0.55), (cx - 3.2, cy + 0.6),
                      "#5d4037", fontsize=8.3)
            _annotate(ax, "Micropyle", (cx - 2.12, cy - 0.95),
                      (cx - 3.3, cy - 1.4), "#37474f", fontsize=8.3)
        subtitle = ("Dicot seed (bean): NON-endospermic — food is stored in the "
                    "two fleshy cotyledons.")
    else:
        # maize (oval) L.S. — endosperm + single cotyledon (scutellum)
        ax.add_patch(Ellipse((cx, cy), 3.4, 4.4, fc=C["endosperm"],
                            ec=C["testa"], lw=2.6, zorder=2))
        # aleurone layer (outer boundary of endosperm)
        ax.add_patch(Ellipse((cx, cy), 3.0, 4.0, fc="none", ec=C["aleurone"],
                            lw=2.2, zorder=3))
        # scutellum (shield) separating endosperm from embryo, on left
        scut = mpatches.Wedge((cx + 0.5, cy), 1.9, 110, 250, width=0.5,
                              fc=C["scutellum"], ec="#e65100", lw=1.8, zorder=4)
        ax.add_patch(scut)
        # embryo axis: coleoptile+plumule up, coleorhiza+radicle down
        ex = cx - 1.1
        ax.add_patch(FancyBboxPatch((ex - 0.28, cy + 0.1), 0.56, 1.2,
                     boxstyle="round,pad=0.02", fc="#c8e6c9",
                     ec=C["coleoptile"], lw=1.8, zorder=5))
        ax.add_patch(FancyArrowPatch((ex, cy + 0.2), (ex, cy + 1.15),
                     arrowstyle="-", lw=2.4, color=C["plumule"], zorder=6))
        ax.add_patch(FancyBboxPatch((ex - 0.28, cy - 1.3), 0.56, 1.1,
                     boxstyle="round,pad=0.02", fc="#d7ccc8",
                     ec=C["coleorhiza"], lw=1.8, zorder=5))
        ax.add_patch(FancyArrowPatch((ex, cy - 0.2), (ex, cy - 1.15),
                     arrowstyle="-", lw=2.4, color=C["radicle"], zorder=6))
        if lab:
            _annotate(ax, "Pericarp + testa\n(fused seed coat)", (cx + 1.6, cy + 1.4),
                      (cx + 3.4, cy + 2.2), C["testa"], fontsize=8.3)
            _annotate(ax, "Endosperm\n(food store)", (cx + 0.9, cy + 0.4),
                      (cx + 3.4, cy + 0.4), "#c9a227", fontsize=8.3)
            _annotate(ax, "Aleurone layer", (cx + 1.35, cy - 1.2),
                      (cx + 3.3, cy - 1.6), C["aleurone"], fontsize=8.3)
            _annotate(ax, "Scutellum\n(cotyledon)", (cx + 0.55, cy + 0.9),
                      (cx + 2.6, cy + 3.0), "#e65100", fontsize=8.3)
            _annotate(ax, "Coleoptile\n(+ plumule)", (ex, cy + 1.1),
                      (ex - 2.2, cy + 2.4), C["coleoptile"], fontsize=8.3)
            _annotate(ax, "Coleorhiza\n(+ radicle)", (ex, cy - 1.05),
                      (ex - 2.2, cy - 2.4), C["coleorhiza"], fontsize=8.3)
        subtitle = ("Monocot seed (maize): ENDOSPERMIC — the single cotyledon "
                    "(scutellum) absorbs food from the endosperm.")

    if schema.show_germination:
        _germination_inset(ax, 8.5, 2.0, schema.show_germination)
        ax.text(9.0, 5.0, f"{schema.show_germination.capitalize()}\ngermination",
                ha="center", fontsize=9.5, fontweight="bold", color="#33691e")

    ax.set_title(schema.title or
                 f"{'Dicot' if dicot else 'Monocot'} Seed Structure (L.S.)",
                 fontsize=14, fontweight="bold", pad=6)
    fig.text(0.5, 0.02, subtitle, ha="center", fontsize=9,
             color="#37474f", style="italic")
    fig.tight_layout(pad=0.4, rect=(0, 0.045, 1, 1))
    return _fig_to_svg(fig)


# ═══════════════════════════════════════════════════════════════════════════════
# 43. Floral Diagram
# ═══════════════════════════════════════════════════════════════════════════════

# whorl counts + floral formula per family. The DIAGRAM and the FORMULA are both
# generated from this one table, so they can never disagree.
_FLORAL_FAMILIES = {
    "solanaceae": {
        "symmetry": "actinomorphic",
        "calyx": 5, "corolla": 5, "androecium": 5, "gynoecium": 2,
        "calyx_fused": True, "corolla_fused": True, "carpel_fused": True,
        "epipetalous": True,
        "formula": "K(5)  C(5)  A5  G(2)",
        "example": "Solanaceae (e.g. Solanum, Petunia) — potato/tomato family; "
                   "bisexual, actinomorphic",
    },
    "fabaceae": {
        "symmetry": "zygomorphic",
        "calyx": 5, "corolla": 5, "androecium": 10, "gynoecium": 1,
        "calyx_fused": True, "corolla_fused": False, "carpel_fused": False,
        "epipetalous": False,
        "formula": "K(5)  C1+2+(2)  A(9)+1  G1",
        "example": "Fabaceae (Papilionoideae, e.g. Pisum) — pea family, "
                   "bisexual, zygomorphic, diadelphous stamens",
    },
    "liliaceae": {
        "symmetry": "actinomorphic",
        "calyx": 3, "corolla": 3, "androecium": 6, "gynoecium": 3,
        "calyx_fused": False, "corolla_fused": False, "carpel_fused": True,
        "epipetalous": False, "tepals": True,
        "formula": "P3+3  A3+3  G(3)",
        "example": "Liliaceae (e.g. Allium, Lilium) — bisexual, actinomorphic, "
                   "trimerous, tepals (P)",
    },
}


def _whorl_ring(ax, cx, cy, r, count, shape_r, color, edge, start=90,
                fused=False, zorder=4):
    ang = np.linspace(0, 2 * np.pi, count, endpoint=False) + math.radians(start)
    if fused:
        ax.add_patch(Circle((cx, cy), r, fc="none", ec=edge, lw=1.4, ls="--",
                            zorder=zorder - 1))
    pts = []
    for a in ang:
        px, py = cx + r * math.cos(a), cy + r * math.sin(a)
        ax.add_patch(Ellipse((px, py), shape_r * 1.6, shape_r * 1.1,
                            angle=math.degrees(a) - 90, fc=color, ec=edge,
                            lw=1.4, zorder=zorder))
        pts.append((px, py))
    return pts


def render_floral_diagram(data: Dict[str, Any],
                          canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = FloralDiagramSchema(**data)
    fam = _FLORAL_FAMILIES[schema.family]
    symmetry = schema.symmetry or fam["symmetry"]
    lab = schema.show_labels
    tepals = fam.get("tepals", False)

    fig, ax = plt.subplots(figsize=(9.5, 9.5))
    ax.set_xlim(-6, 6); ax.set_ylim(-6, 6.2)
    ax.set_aspect("equal"); ax.axis("off")
    cx, cy = 0, 0

    # mother axis (posterior) marked at top; bract (anterior) at bottom
    ax.add_patch(Circle((0, 5.2), 0.34, fc=C["mother_axis"], ec="#263238",
                        lw=1.5, zorder=6))
    ax.text(0, 5.2, "axis", ha="center", va="center", fontsize=7,
            color="white", zorder=7)
    ax.add_patch(mpatches.Wedge((0, -5.0), 0.9, 60, 120, fc=C["bract"],
                                ec="#1b5e20", lw=1.5, zorder=6))
    if lab:
        ax.text(0.5, 5.2, "Mother axis (posterior)", ha="left", va="center",
                fontsize=8, color=C["mother_axis"])
        ax.text(0, -5.6, "Bract (anterior)", ha="center", va="top",
                fontsize=8, color="#1b5e20")

    # concentric whorls (outer → inner)
    if tepals:
        _whorl_ring(ax, cx, cy, 4.2, fam["calyx"], 0.55, C["corolla"],
                    "#880e4f", start=90, fused=fam["calyx_fused"])
        _whorl_ring(ax, cx, cy, 3.2, fam["corolla"], 0.5, "#f48fb1",
                    "#880e4f", start=150, fused=fam["corolla_fused"])
        perianth_label = "Perianth — tepals (P) in two whorls of 3"
    else:
        _whorl_ring(ax, cx, cy, 4.4, fam["calyx"], 0.5, C["calyx"],
                    "#1b5e20", start=90, fused=fam["calyx_fused"])
        _whorl_ring(ax, cx, cy, 3.3, fam["corolla"], 0.55, C["corolla"],
                    "#880e4f", start=90 + 36, fused=fam["corolla_fused"])
        perianth_label = "Calyx (K, outer) + Corolla (C)"

    stamens = _whorl_ring(ax, cx, cy, 2.2, fam["androecium"], 0.28,
                          C["androecium"], "#f57f17", start=90)
    # epipetalous: link stamens to the corolla whorl
    if fam.get("epipetalous"):
        for px, py in stamens:
            ax.plot([px * 1.5, px], [py * 1.5, py], color="#f9a825", lw=0.8,
                    ls=":", zorder=3)

    # gynoecium (carpels) in the centre — a T.S. of the ovary
    gyn_r = 1.1
    ax.add_patch(Circle((cx, cy), gyn_r, fc="#f3e5f5", ec=C["gynoecium"],
                        lw=1.8, zorder=4))
    ncarp = fam["gynoecium"]
    if ncarp == 1:
        ax.add_patch(Circle((cx, cy), 0.4, fc=C["gynoecium"], ec="#4a148c",
                            lw=1.2, zorder=5))
    else:
        ang = np.linspace(0, 2 * np.pi, ncarp, endpoint=False) + math.radians(90)
        for a in ang:
            ax.add_patch(Circle((cx + 0.45 * math.cos(a),
                                 cy + 0.45 * math.sin(a)), 0.34,
                                fc="#ce93d8", ec="#4a148c", lw=1.2, zorder=5))
    if fam["carpel_fused"] and ncarp > 1:
        ax.text(cx, cy - 1.5, f"syncarpous ({ncarp} fused carpels)",
                ha="center", fontsize=7.5, color=C["gynoecium"], style="italic")

    if lab:
        ax.text(-5.7, 4.6, perianth_label, fontsize=8.5, color="#455a64",
                fontweight="bold", va="center")
        _annotate(ax, "Androecium (A)\nstamens", (2.2, 0), (5.2, -1.5),
                  "#f57f17", fontsize=8.3)
        _annotate(ax, "Gynoecium (G)\ncarpels", (0, 0.4), (4.6, 2.6),
                  C["gynoecium"], fontsize=8.3)

    sym_txt = ("Actinomorphic (radial symmetry)" if symmetry == "actinomorphic"
               else "Zygomorphic (bilateral symmetry)")
    if schema.show_formula:
        ax.text(0, -6.0, fam["formula"], ha="center", va="top", fontsize=13,
                fontweight="bold", color="#4527a0",
                bbox=dict(boxstyle="round,pad=0.4", fc="#ede7f6",
                          ec="#4527a0", lw=1.2))

    ax.set_title(schema.title or
                 f"Floral Diagram — {schema.family.capitalize()}",
                 fontsize=14, fontweight="bold", pad=6)
    fig.text(0.5, 0.015, f"{sym_txt}.  {fam['example']}", ha="center",
             fontsize=8.8, color="#37474f", style="italic")
    fig.tight_layout(pad=0.4, rect=(0, 0.08, 1, 1))
    return _fig_to_svg(fig)


# ═══════════════════════════════════════════════════════════════════════════════
# 44. Plant Morphology
# ═══════════════════════════════════════════════════════════════════════════════

_MORPH_DEFAULTS = {
    "venation": "reticulate", "phyllotaxy": "alternate",
    "inflorescence": "racemose", "root_system": "tap", "fruit_type": "drupe",
}


def _ovate_leaf(ax, cx, cy, half_w, half_h, color="#c8e6c9"):
    """Ovate leaf blade (pointed base and tip). Returns half_width(y) so veins
    can be drawn strictly INSIDE the margin."""
    def half_width(y):
        frac = np.clip((y - (cy - half_h)) / (2 * half_h), 0, 1)
        return half_w * np.sin(np.pi * frac) ** 0.6
    ys = np.linspace(cy - half_h, cy + half_h, 240)
    w = half_width(ys)
    xs = np.concatenate([cx + w, (cx - w)[::-1]])
    yy = np.concatenate([ys, ys[::-1]])
    ax.fill(xs, yy, color=color, ec="#33691e", lw=1.8, zorder=3)
    return half_width


def render_plant_morphology(data: Dict[str, Any],
                            canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = PlantMorphologySchema(**data)
    feature = schema.feature
    variant = schema.variant or _MORPH_DEFAULTS[feature]
    lab = schema.show_labels

    fig, ax = plt.subplots(figsize=(9.5, 8.0))
    ax.set_xlim(0, 10); ax.set_ylim(0, 9)
    ax.set_aspect("equal"); ax.axis("off")
    note = ""

    if feature == "venation":
        cxL, cyL, hw, hh = 5.0, 4.5, 2.5, 3.0
        hwidth = _ovate_leaf(ax, cxL, cyL, hw, hh, color=C["morph_leaf"])
        y_lo, y_hi = cyL - hh + 0.15, cyL + hh - 0.15
        ax.plot([cxL, cxL], [y_lo, y_hi], color=C["morph_vein"], lw=2.6,
                zorder=4)
        if variant == "reticulate":
            rows = np.linspace(y_lo + 0.5, y_hi - 1.0, 6)
            rng = np.random.RandomState(3)
            for yb in rows:
                w = float(hwidth(yb)) * 0.82
                for s in (-1, 1):
                    xe = cxL + s * w
                    ye = min(yb + 0.35, y_hi - 0.35)   # arch toward the tip
                    xs = np.linspace(cxL, xe, 20)
                    ys = np.linspace(yb, ye, 20) + 0.08 * np.sin(
                        np.linspace(0, np.pi, 20))
                    ax.plot(xs, ys, color=C["morph_vein"], lw=1.3, zorder=4)
                    # netted minor veins, kept well inside the secondary
                    for _ in range(4):
                        t = rng.uniform(0.2, 0.7)
                        x1 = cxL + s * w * t
                        y1 = yb + 0.35 * t
                        ax.plot([x1, x1 + s * 0.30 * rng.uniform(0.3, 0.8)],
                                [y1, y1 + rng.uniform(0.2, 0.4)],
                                color="#7cb342", lw=0.7, zorder=3)
            note = ("Reticulate venation — veins form a NETWORK; typical of "
                    "DICOT leaves.")
        else:
            rows = np.linspace(y_lo + 0.4, y_hi - 0.4, 40)
            wrow = np.array([float(hwidth(yb)) for yb in rows])
            # parallel veins run base→tip, each a constant fraction of the
            # local half-width, so all stay inside the margin
            for frac in np.linspace(0.16, 0.94, 5):
                ax.plot(cxL + frac * wrow, rows, color=C["morph_vein"],
                        lw=1.4, zorder=4)
                ax.plot(cxL - frac * wrow, rows, color=C["morph_vein"],
                        lw=1.4, zorder=4)
            note = ("Parallel venation — veins run PARALLEL; typical of MONOCOT "
                    "leaves.")
        if lab:
            _annotate(ax, "Midrib", (cxL, cyL + 1.6), (7.7, 7.2),
                      C["morph_vein"], fontsize=8.5)
            _annotate(ax, f"{variant.capitalize()} veins",
                      (cxL + hwidth(cyL) * 0.6, cyL - 0.3), (8.3, 4.0),
                      "#558b2f", fontsize=8.5)

    elif feature == "phyllotaxy":
        ax.plot([5, 5], [0.8, 8.2], color=C["morph_stem"], lw=5,
                solid_capstyle="round", zorder=3)
        def leaf(x, y, s):
            ax.add_patch(Ellipse((x + s * 1.0, y), 2.0, 0.7,
                                angle=s * 18, fc=C["morph_leaf"],
                                ec="#33691e", lw=1.4, zorder=4))
        if variant == "alternate":
            for i, y in enumerate(np.linspace(1.6, 7.4, 6)):
                leaf(5, y, 1 if i % 2 else -1)
            note = "Alternate — ONE leaf per node, on alternating sides."
        elif variant == "opposite":
            for y in np.linspace(1.8, 7.2, 4):
                leaf(5, y, 1); leaf(5, y, -1)
            note = "Opposite — a PAIR of leaves per node, facing each other."
        else:  # whorled
            for y in (2.4, 5.4):
                for s, dy in ((-1, 0), (1, 0), (-0.5, 0.5), (0.5, -0.5)):
                    ax.add_patch(Ellipse((5 + s * 1.1, y + dy * 0.6), 1.9, 0.6,
                                        angle=s * 20, fc=C["morph_leaf"],
                                        ec="#33691e", lw=1.4, zorder=4))
            note = "Whorled — THREE or more leaves at each node."
        if lab:
            _annotate(ax, "Node", (5, 4.4), (2.4, 4.8), C["morph_stem"],
                      fontsize=8.5)

    elif feature == "inflorescence":
        ax.plot([5, 5], [0.8, 7.8], color=C["morph_stem"], lw=4,
                solid_capstyle="round", zorder=3)
        if variant == "racemose":
            # main axis keeps growing; oldest flowers at the base (acropetal)
            for i, y in enumerate(np.linspace(1.6, 7.0, 6)):
                for s in (-1, 1):
                    ax.plot([5, 5 + s * 1.6], [y, y + 0.3], color="#33691e",
                            lw=1.6, zorder=4)
                    r = 0.34 - i * 0.02
                    ax.add_patch(Circle((5 + s * 1.6, y + 0.3), r,
                                        fc=C["morph_flower"], ec="#880e4f",
                                        lw=1.2, zorder=5))
            ax.add_patch(Circle((5, 7.9), 0.16, fc="#c5e1a5", ec="#33691e",
                                lw=1.2, zorder=5))
            note = ("Racemose — main axis grows indefinitely; flowers open "
                    "bottom-up (acropetal). Youngest at the tip.")
        else:  # cymose
            def cyme(x, y, depth, s):
                if depth == 0:
                    return
                ax.add_patch(Circle((x, y), 0.36, fc=C["morph_flower"],
                                    ec="#880e4f", lw=1.2, zorder=5))
                for ss in (-1, 1):
                    nx, ny = x + ss * 1.5 * depth * 0.5, y - 1.4
                    ax.plot([x, nx], [y - 0.3, ny + 0.3], color="#33691e",
                            lw=1.6, zorder=4)
                    cyme(nx, ny, depth - 1, ss)
            cyme(5, 7.4, 3, 1)
            note = ("Cymose — main axis ENDS in a flower (oldest, at the top); "
                    "growth continues from lateral branches (basipetal).")
        if lab:
            _annotate(ax, "Main axis (peduncle)", (5, 3.0), (1.6, 2.4),
                      C["morph_stem"], fontsize=8.3)

    elif feature == "root_system":
        ax.plot([2.5, 7.5], [6.0, 6.0], color="#8d6e63", lw=2.0, zorder=2)
        ax.text(5, 6.25, "soil surface", ha="center", fontsize=7.5,
                color="#6d4c41", style="italic")
        ax.plot([5, 5], [6.0, 8.2], color="#2e7d32", lw=4, zorder=3)   # shoot
        if variant == "tap":
            ax.plot([5, 5], [6.0, 1.2], color=C["morph_root"], lw=5,
                    solid_capstyle="round", zorder=3)
            rng = np.random.RandomState(5)
            for y in np.linspace(2.0, 5.4, 8):
                for s in (-1, 1):
                    L = rng.uniform(0.6, 1.4)
                    ax.plot([5, 5 + s * L], [y, y - 0.5], color="#a1887f",
                            lw=1.6, zorder=3)
            note = ("Tap root system — one primary root with lateral branches; "
                    "typical of DICOTS.")
        else:  # fibrous
            for s in np.linspace(-1, 1, 11):
                xs = np.linspace(5, 5 + s * 2.3, 20)
                ys = 6.0 - np.linspace(0, 4.2, 20) - 0.3 * np.sin(xs)
                ax.plot(xs, ys, color=C["morph_root"], lw=2.0, zorder=3)
            note = ("Fibrous root system — a cluster of thin roots from the "
                    "stem base; typical of MONOCOTS.")
        if lab:
            _annotate(ax, f"{variant.capitalize()} root", (5, 3.4),
                      (8.0, 3.0), C["morph_root"], fontsize=8.5)

    else:  # fruit_type — a drupe L.S. (pericarp layers)
        ax.add_patch(Ellipse((5, 4.5), 4.6, 5.6, fc="#ffe0b2",
                            ec="#e65100", lw=2.4, zorder=2))
        ax.add_patch(Ellipse((5, 4.5), 4.2, 5.2, fc="#fff3e0",
                            ec="#fb8c00", lw=1.4, zorder=3))
        ax.add_patch(Ellipse((5, 4.2), 2.2, 3.0, fc="#d7ccc8",
                            ec="#5d4037", lw=2.4, zorder=4))    # endocarp (stony)
        ax.add_patch(Ellipse((5, 4.2), 1.5, 2.2, fc="#c5e1a5",
                            ec="#33691e", lw=1.6, zorder=5))    # seed
        note = ("Drupe (e.g. mango, coconut) — a fleshy fruit with a hard "
                "stony endocarp enclosing one seed.")
        if lab:
            _annotate(ax, "Epicarp (skin)", (5, 7.2), (7.8, 8.0), "#e65100",
                      fontsize=8.3)
            _annotate(ax, "Mesocarp (fleshy, edible)", (6.6, 5.4),
                      (8.6, 6.0), "#fb8c00", fontsize=8.3)
            _annotate(ax, "Endocarp (stony)", (5.9, 4.2), (8.2, 3.4),
                      "#5d4037", fontsize=8.3)
            _annotate(ax, "Seed", (5, 4.2), (2.0, 2.2), "#33691e",
                      fontsize=8.3)

    ax.set_title(schema.title or
                 f"Plant Morphology — {feature.replace('_', ' ').capitalize()} "
                 f"({variant})", fontsize=13.5, fontweight="bold", pad=6)
    fig.text(0.5, 0.02, _wrap(note, 96), ha="center", fontsize=9,
             color="#37474f", style="italic")
    fig.tight_layout(pad=0.4, rect=(0, 0.05, 1, 1))
    return _fig_to_svg(fig)


# ═══════════════════════════════════════════════════════════════════════════════
# 45. Plant Life Cycle (alternation of generations)
# ═══════════════════════════════════════════════════════════════════════════════

# Six stages round one cycle. Ploidy is ENCODED here (not drawn by eye), so the
# 2n/n badges and the test read the same source. Meiosis is the 2n→n step
# (sporophyte → spores); fertilisation is the n→2n step (gametes → zygote).
_LIFE_CYCLE_STAGES = [
    {"name": "Sporophyte", "ploidy": 2, "gen": "sporophyte"},
    {"name": "Spores", "ploidy": 1, "gen": "gametophyte", "via": "MEIOSIS"},
    {"name": "Gametophyte", "ploidy": 1, "gen": "gametophyte"},
    {"name": "Gametes", "ploidy": 1, "gen": "gametophyte"},
    {"name": "Zygote", "ploidy": 2, "gen": "sporophyte", "via": "FERTILISATION"},
    {"name": "(Embryo)", "ploidy": 2, "gen": "sporophyte"},
]

_LIFE_CYCLE_GROUPS = {
    "bryophyte": {
        "dominant": "gametophyte",
        "note": "Bryophytes: the GAMETOPHYTE (n) is dominant, green and "
                "long-lived; the sporophyte (2n) is small and dependent on it.",
        "sporo_ex": "Capsule (2n)", "gameto_ex": "Leafy moss / thallus (n)",
    },
    "pteridophyte": {
        "dominant": "sporophyte",
        "note": "Pteridophytes: the SPOROPHYTE (2n) is the dominant plant; the "
                "gametophyte is a small, independent prothallus (n).",
        "sporo_ex": "Fern plant (2n)", "gameto_ex": "Prothallus (n)",
    },
    "angiosperm": {
        "dominant": "sporophyte",
        "note": "Angiosperms: the SPOROPHYTE (2n) is dominant; the gametophytes "
                "are highly reduced — pollen grain (male) and embryo sac "
                "(female).",
        "sporo_ex": "Flowering plant (2n)", "gameto_ex": "Pollen / embryo sac (n)",
    },
}


def render_plant_life_cycle(data: Dict[str, Any],
                            canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = PlantLifeCycleSchema(**data)
    grp = _LIFE_CYCLE_GROUPS[schema.group]
    lab = schema.show_labels
    stages = _LIFE_CYCLE_STAGES

    fig, ax = plt.subplots(figsize=(9.8, 9.8))
    ax.set_xlim(-6, 6); ax.set_ylim(-6, 6)
    ax.set_aspect("equal"); ax.axis("off")

    R = 4.2
    n = len(stages)
    ang = [math.radians(90 - i * 360 / n) for i in range(n)]
    pos = [(R * math.cos(a), R * math.sin(a)) for a in ang]
    ploidy_col = {2: C["ploidy_2n"], 1: C["ploidy_n"]}
    gen_col = {"sporophyte": C["sporophyte"], "gametophyte": C["gametophyte"]}

    # 2n vs n half-plane shading. The cycle runs clockwise from the sporophyte
    # at the top: meiosis on the RIGHT drops it to haploid (spores → gametophyte
    # → gametes), fertilisation on the LEFT restores diploid (zygote → embryo).
    ax.add_patch(mpatches.Wedge((0, 0), 5.6, -90, 90, fc="#e3f2fd",
                                alpha=0.5, zorder=0))
    ax.add_patch(mpatches.Wedge((0, 0), 5.6, 90, 270, fc="#ffebee",
                                alpha=0.5, zorder=0))
    ax.text(3.4, 4.6, "HAPLOID (n)\ngametophyte phase", ha="center",
            fontsize=9, color=C["ploidy_n"], fontweight="bold")
    ax.text(-3.4, 4.6, "DIPLOID (2n)\nsporophyte phase", ha="center",
            fontsize=9, color=C["ploidy_2n"], fontweight="bold")

    for i, st in enumerate(stages):
        px, py = pos[i]
        col = gen_col[st["gen"]]
        ax.add_patch(mpatches.FancyBboxPatch((px - 1.15, py - 0.55), 2.3, 1.1,
                     boxstyle="round,pad=0.05", fc="white", ec=col, lw=2.2,
                     zorder=5))
        name = st["name"]
        if name == "Sporophyte":
            name = f"Sporophyte\n{grp['sporo_ex']}"
        elif name == "Gametophyte":
            name = f"Gametophyte\n{grp['gameto_ex']}"
        ax.text(px, py + 0.12, name, ha="center", va="center", fontsize=7.8,
                fontweight="bold", color=col, zorder=6)
        # ploidy badge
        ptxt = "2n" if st["ploidy"] == 2 else "n"
        ax.text(px, py - 0.34, ptxt, ha="center", va="center", fontsize=8.5,
                fontweight="bold", color="white", zorder=7,
                bbox=dict(boxstyle="circle,pad=0.18",
                          fc=ploidy_col[st["ploidy"]], ec="none"))

        # arrow to the next stage
        a0, a1 = ang[i], ang[(i + 1) % n]
        mid = ((pos[i][0] + pos[(i + 1) % n][0]) / 2,
               (pos[i][1] + pos[(i + 1) % n][1]) / 2)
        nxt = stages[(i + 1) % n]
        ax.add_patch(FancyArrowPatch(pos[i], pos[(i + 1) % n],
                     arrowstyle="-|>", mutation_scale=18, lw=2.0,
                     color=C["cycle_arrow"], zorder=3,
                     connectionstyle="arc3,rad=0.16",
                     shrinkA=26, shrinkB=26))
        via = nxt.get("via")
        if via:
            key_col = C["meiosis_mark"] if via == "MEIOSIS" else C["fert_mark"]
            ax.text(mid[0] * 1.28, mid[1] * 1.28, via, ha="center",
                    va="center", fontsize=9, fontweight="bold", color="white",
                    zorder=8, bbox=dict(boxstyle="round,pad=0.28", fc=key_col,
                                        ec="none"))
            if via == "MEIOSIS":
                ax.text(mid[0] * 1.28, mid[1] * 1.28 - 0.5,
                        "(2n to n)", ha="center", fontsize=7.5,
                        color=key_col, zorder=8)
            else:
                ax.text(mid[0] * 1.28, mid[1] * 1.28 - 0.5,
                        "(n gametes fuse to 2n)", ha="center", fontsize=7.5,
                        color=key_col, zorder=8)

    ax.text(0, 0, "Alternation\nof Generations", ha="center", va="center",
            fontsize=11, fontweight="bold", color="#455a64", zorder=6)

    ax.set_title(schema.title or
                 f"Plant Life Cycle — {schema.group.capitalize()} "
                 f"({grp['dominant']}-dominant)",
                 fontsize=14, fontweight="bold", pad=6)
    fig.text(0.5, 0.015, _wrap(grp["note"], 104), ha="center", fontsize=9,
             color="#37474f", style="italic")
    fig.tight_layout(pad=0.4, rect=(0, 0.05, 1, 1))
    return _fig_to_svg(fig)


# ═══════════════════════════════════════════════════════════════════════════════
# 46. Photosynthesis Z-Scheme (light reaction)
# ═══════════════════════════════════════════════════════════════════════════════

# (x, redox_potential_V, label, colour). Electrons flow left→right; the y-axis is
# redox potential (more negative = higher up = stronger reductant), so the two
# photon absorptions are the two UPWARD jumps at PSII and PSI.
_ZSCHEME_NODES = [
    (0.6, 0.82, "H₂O\n(½O₂ + 2H⁺)", "water_split"),
    (1.4, 1.15, "P680\n(PSII)", "psii"),
    (1.4, -0.75, "P680*", "psii"),
    (2.4, -0.55, "Pheophytin", "electron_path"),
    (3.4, -0.05, "Plastoquinone\n(PQ)", "electron_path"),
    (4.4, 0.30, "Cytochrome\nb₆f", "electron_path"),
    (5.4, 0.42, "Plastocyanin\n(PC)", "electron_path"),
    (6.2, 0.45, "P700\n(PSI)", "psi"),
    (6.2, -1.30, "P700*", "psi"),
    (7.2, -0.55, "Ferredoxin\n(Fd)", "electron_path"),
    (8.2, -0.32, "NADP⁺ + H⁺\n(to NADPH)", "nadph"),
]


def render_photosynthesis_zscheme(data: Dict[str, Any],
                                  canvas_w: int = 800,
                                  canvas_h: int = 600) -> str:
    schema = PhotosynthesisZSchemeSchema(**data)
    lab = schema.show_labels
    nd = {i: n for i, n in enumerate(_ZSCHEME_NODES)}

    fig, ax = plt.subplots(figsize=(12.5, 8.2))
    ax.set_xlim(0, 9); ax.set_ylim(-1.6, 1.5)
    ax.invert_yaxis()                     # negative potentials at the TOP
    ax.set_ylabel("Redox potential (volts)", fontsize=11)
    ax.set_xticks([])
    ax.spines[["top", "right", "bottom"]].set_visible(False)
    ax.axhline(0, color="#cfd8dc", lw=1.0, ls=":", zorder=1)

    # electron-transport path (downhill segments) as drawn arrows
    order = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    for a, b in zip(order, order[1:]):
        xa, ya = nd[a][0], nd[a][1]
        xb, yb = nd[b][0], nd[b][1]
        col = C["photon"] if (a in (1,) or a == 7) else C["electron_path"]
        ax.add_patch(FancyArrowPatch((xa, ya), (xb, yb), arrowstyle="-|>",
                     mutation_scale=13, lw=2.0, color=C["electron_path"],
                     zorder=4, shrinkA=12, shrinkB=12))

    # water → P680⁺ (fills the electron hole left by excitation)
    ax.add_patch(FancyArrowPatch((nd[0][0], nd[0][1]), (nd[1][0], nd[1][1]),
                 arrowstyle="-|>", mutation_scale=13, lw=2.0,
                 color=C["water_split"], zorder=4, shrinkA=12, shrinkB=12))

    # the two photon excitations (vertical UP jumps)
    if schema.show_photons:
        for base, exc, name in ((1, 2, "Photon\n(PSII light)"),
                                (7, 8, "Photon\n(PSI light)")):
            ax.add_patch(FancyArrowPatch((nd[base][0], nd[base][1]),
                         (nd[exc][0], nd[exc][1]), arrowstyle="-|>",
                         mutation_scale=16, lw=3.0, color=C["photon"],
                         zorder=5, shrinkA=12, shrinkB=12))
            ax.text(nd[base][0] - 0.35, (nd[base][1] + nd[exc][1]) / 2, name,
                    ha="right", va="center", fontsize=8.3,
                    color="#f57f17", fontweight="bold")

    for i, (x, y, name, col) in nd.items():
        ax.add_patch(Circle((x, y), 0.11, fc=C[col], ec="#263238", lw=1.2,
                            zorder=6))
        if lab:
            dy = 0.16 if col in ("psii", "psi", "nadph", "water_split") else -0.16
            va = "bottom" if dy < 0 else "top"
            ax.text(x, y + dy, name, ha="center", va=va, fontsize=8.0,
                    color="#37474f", zorder=7)

    if schema.show_products:
        ax.text(nd[0][0], nd[0][1] + 0.42, "O₂ evolved\n(water splitting)",
                ha="center", va="top", fontsize=8.3, color=C["water_split"],
                fontweight="bold")
        ax.text(8.2, -0.75, "NADPH\n(reducing power\nfor Calvin cycle)",
                ha="center", fontsize=8.5, color=C["nadph"], fontweight="bold")

    ax.set_title(schema.title or "Z-Scheme of the Light Reaction "
                 "(non-cyclic photophosphorylation)", fontsize=13.5,
                 fontweight="bold", pad=8)
    fig.text(0.5, 0.015,
             "Electrons from split water are raised twice — by PSII (P680) then "
             "PSI (P700) — flowing downhill through PQ, cyt b₆f and PC to "
             "ferredoxin, finally reducing NADP⁺ to NADPH.",
             ha="center", fontsize=8.8, color="#37474f", style="italic")
    fig.tight_layout(pad=0.5, rect=(0, 0.05, 1, 1))
    return _fig_to_svg(fig)


# ═══════════════════════════════════════════════════════════════════════════════
# 47. Electron Transport Chain (mitochondrial, chemiosmosis)
# ═══════════════════════════════════════════════════════════════════════════════

def render_electron_transport_chain(data: Dict[str, Any],
                                    canvas_w: int = 800,
                                    canvas_h: int = 600) -> str:
    schema = ElectronTransportChainSchema(**data)
    lab = schema.show_labels

    fig, ax = plt.subplots(figsize=(13, 8.0))
    ax.set_xlim(0, 13); ax.set_ylim(0, 9)
    ax.axis("off")

    MEM_LO, MEM_HI = 3.2, 5.4
    ax.axhspan(MEM_LO, MEM_HI, color=C["etc_membrane"], zorder=1)
    ax.axhspan(MEM_HI, 9, color=C["intermembrane"], alpha=0.5, zorder=0)
    ax.axhspan(0, MEM_LO, color=C["matrix_m"], alpha=0.6, zorder=0)
    ax.text(0.3, (MEM_HI + 9) / 2, "INTERMEMBRANE\nSPACE (high H⁺)",
            fontsize=9, color="#1565c0", fontweight="bold", va="center")
    ax.text(0.3, MEM_LO / 2, "MATRIX (low H⁺)", fontsize=9, color="#e65100",
            fontweight="bold", va="center")
    ax.text(11.5, (MEM_LO + MEM_HI) / 2, "Inner\nmitochondrial\nmembrane",
            fontsize=8, color="#8d6e63", va="center", ha="center",
            style="italic")

    complexes = [
        (2.4, "I", "complex_i", "NADH\ndehydrogenase", True),
        (4.2, "II", "complex_ii", "Succinate\ndehydrogenase", False),
        (6.2, "III", "complex_iii", "Cytochrome\nbc₁", True),
        (8.4, "IV", "complex_iv", "Cytochrome c\noxidase", True),
    ]
    for cx, rn, col, name, pumps in complexes:
        ax.add_patch(mpatches.FancyBboxPatch((cx - 0.75, MEM_LO - 0.1), 1.5,
                     MEM_HI - MEM_LO + 0.2, boxstyle="round,pad=0.03",
                     fc=C[col], ec="#263238", lw=1.8, zorder=4))
        ax.text(cx, (MEM_LO + MEM_HI) / 2 + 0.35, rn, ha="center", va="center",
                fontsize=13, fontweight="bold", color="white", zorder=5)
        if lab:
            ax.text(cx, MEM_LO - 0.35, name, ha="center", va="top",
                    fontsize=7.6, color=C[col], zorder=5)
        if pumps and schema.show_proton_gradient:
            ax.add_patch(FancyArrowPatch((cx, MEM_HI - 0.1), (cx, MEM_HI + 1.3),
                         arrowstyle="-|>", mutation_scale=14, lw=2.2,
                         color=C["proton"], zorder=6))
            ax.text(cx, MEM_HI + 1.5, "H⁺", ha="center", fontsize=9,
                    color=C["proton"], fontweight="bold")

    # mobile carriers: ubiquinone (Q) and cytochrome c
    ax.add_patch(Circle((5.2, MEM_LO + 0.6), 0.28, fc=C["ubiquinone"],
                        ec="#4a148c", lw=1.4, zorder=5))
    ax.text(5.2, MEM_LO + 0.6, "Q", ha="center", va="center", fontsize=9,
            color="white", fontweight="bold", zorder=6)
    ax.add_patch(Circle((7.3, MEM_HI - 0.4), 0.26, fc=C["cyt_c"],
                        ec="#880e4f", lw=1.4, zorder=5))
    ax.text(7.3, MEM_HI - 0.4, "c", ha="center", va="center", fontsize=9,
            color="white", fontweight="bold", zorder=6)

    # electron flow along the chain (drawn arrows)
    epath = [(2.4, MEM_HI - 0.5), (5.2, MEM_LO + 0.9), (6.2, MEM_HI - 0.5),
             (7.3, MEM_HI - 0.4), (8.4, MEM_HI - 0.5)]
    for a, b in zip(epath, epath[1:]):
        ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=11,
                     lw=1.6, color="#37474f", ls="--", zorder=6))
    ax.add_patch(FancyArrowPatch((4.2, MEM_HI - 0.5), (5.2, MEM_LO + 0.9),
                 arrowstyle="-|>", mutation_scale=11, lw=1.6, color="#37474f",
                 ls="--", zorder=6))

    # inputs / final acceptor
    ax.text(2.4, 8.2, "e⁻", ha="center", fontsize=9, color="#37474f")
    ax.text(1.5, MEM_LO - 0.9, "NADH oxidised to NAD⁺", fontsize=8.5,
            color=C["complex_i"], fontweight="bold")
    ax.text(4.2, MEM_LO - 1.25, "FADH₂ oxidised to FAD", fontsize=8.5,
            color=C["complex_ii"], fontweight="bold", ha="center")
    ax.text(8.4, MEM_LO - 0.9, "½O₂ + 2H⁺ + 2e⁻ gives H₂O", fontsize=8.5,
            color=C["complex_iv"], fontweight="bold", ha="center")

    # ── ATP synthase (complex V) — chemiosmosis ───────────────────────────────
    if schema.show_atp_synthase:
        vx = 10.6
        ax.add_patch(mpatches.FancyBboxPatch((vx - 0.55, MEM_LO - 0.1), 1.1,
                     MEM_HI - MEM_LO + 0.2, boxstyle="round,pad=0.03",
                     fc=C["atp_synthase"], ec="#263238", lw=1.8, zorder=4))
        ax.add_patch(Circle((vx, MEM_LO - 0.05), 0.5, fc=C["atp_synthase"],
                            ec="#263238", lw=1.8, zorder=4))
        ax.text(vx, (MEM_LO + MEM_HI) / 2 + 0.3, "V", ha="center", va="center",
                fontsize=12, fontweight="bold", color="white", zorder=5)
        ax.add_patch(FancyArrowPatch((vx, MEM_HI + 1.0), (vx, MEM_LO - 0.6),
                     arrowstyle="-|>", mutation_scale=16, lw=2.6,
                     color=C["proton"], zorder=6))
        ax.text(vx + 0.7, MEM_HI + 0.7, "H⁺ flows\nback (down\ngradient)",
                fontsize=7.8, color=C["proton"], va="center")
        ax.text(vx, MEM_LO - 1.15, "ADP + Pi gives ATP", ha="center",
                fontsize=9, color=C["atp_synthase"], fontweight="bold")
        if lab:
            ax.text(vx, MEM_HI + 1.9, "ATP synthase", ha="center", fontsize=8.5,
                    color=C["atp_synthase"], fontweight="bold")

    ax.set_title(schema.title or "Mitochondrial Electron Transport Chain & "
                 "Chemiosmosis", fontsize=13.5, fontweight="bold", pad=6)
    fig.text(0.5, 0.02,
             "Electrons from NADH/FADH₂ pass along complexes I–IV; complexes I, "
             "III and IV pump H⁺ into the intermembrane space. The proton "
             "gradient drives ATP synthase (chemiosmosis); O₂ is the terminal "
             "electron acceptor.",
             ha="center", fontsize=8.5, color="#37474f", style="italic")
    fig.tight_layout(pad=0.4, rect=(0, 0.05, 1, 1))
    return _fig_to_svg(fig)


# ═══════════════════════════════════════════════════════════════════════════════
# 48. Chromosome Structure / Karyotype
# ═══════════════════════════════════════════════════════════════════════════════

# centromere position as a fraction of chromosome length from the TOP end.
# metacentric = 0.5 (central); telocentric ≈ terminal. This single mapping is
# read by both the drawing and the test.
_CENTROMERE_POS = {
    "metacentric": 0.50,
    "submetacentric": 0.35,
    "acrocentric": 0.15,
    "telocentric": 0.02,
}


def _draw_chromosome(ax, cx, top, bot, cpos, width=0.5, satellite=False):
    """A duplicated chromosome (two sister chromatids) with the centromere at
    fractional position `cpos` from the top."""
    length = top - bot
    cy = top - cpos * length
    for s in (-1, 1):
        xoff = cx + s * width * 0.55
        # each chromatid pinches in at the centromere
        ax.add_patch(mpatches.FancyBboxPatch((xoff - width * 0.28, bot),
                     width * 0.56, cy - bot - 0.05,
                     boxstyle="round,pad=0.02,rounding_size=0.12",
                     fc=C["chromatid"], ec="#311b92", lw=1.4, zorder=4))
        ax.add_patch(mpatches.FancyBboxPatch((xoff - width * 0.28, cy + 0.05),
                     width * 0.56, top - cy - 0.05,
                     boxstyle="round,pad=0.02,rounding_size=0.12",
                     fc=C["chromatid"], ec="#311b92", lw=1.4, zorder=4))
    # centromere constriction
    ax.add_patch(Circle((cx, cy), width * 0.30, fc=C["centromere"],
                        ec="#7f0000", lw=1.4, zorder=6))
    if satellite:
        ax.add_patch(Circle((cx, top + 0.18), 0.10, fc="#f57f17",
                            ec="#e65100", lw=1.0, zorder=5))
        ax.plot([cx, cx], [top, top + 0.08], color="#311b92", lw=1.0, zorder=5)
    return cy


def render_chromosome_structure(data: Dict[str, Any],
                                canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = ChromosomeStructureSchema(**data)
    lab = schema.show_labels

    if schema.view == "karyotype":
        return _render_karyotype(schema)
    if schema.view == "sex_determination":
        return _render_sex_determination(schema)

    # ── single chromosome anatomy ─────────────────────────────────────────────
    ctype = schema.centromere
    cpos = _CENTROMERE_POS[ctype]
    fig, ax = plt.subplots(figsize=(9.5, 8.4))
    ax.set_xlim(0, 10); ax.set_ylim(0, 9)
    ax.set_aspect("equal"); ax.axis("off")

    top, bot = 7.4, 1.4
    cy = _draw_chromosome(ax, 3.2, top, bot, cpos, width=1.0,
                          satellite=(ctype == "acrocentric"))
    p_end = (cy + top) / 2
    q_end = (cy + bot) / 2

    if lab:
        _annotate(ax, "Telomere (tip)", (3.2, top - 0.05), (6.0, top + 0.6),
                  C["telomere"], fontsize=8.6)
        _annotate(ax, "Telomere (tip)", (3.2, bot + 0.05), (6.0, bot - 0.4),
                  C["telomere"], fontsize=8.6)
        _annotate(ax, "Centromere\n(primary constriction)", (3.2, cy),
                  (6.4, cy + 0.3), C["centromere"], fontsize=8.6)
        _annotate(ax, "Sister chromatids", (3.75, q_end), (6.6, q_end - 0.4),
                  C["chromatid"], fontsize=8.6)
        ax.text(1.7, p_end, "p arm\n(short)", ha="right", va="center",
                fontsize=8.6, color="#5e35b1", fontweight="bold")
        ax.text(1.7, q_end, "q arm\n(long)", ha="right", va="center",
                fontsize=8.6, color="#5e35b1", fontweight="bold")
        if ctype == "acrocentric":
            _annotate(ax, "Satellite", (3.2, top + 0.18), (5.6, top + 1.2),
                      "#e65100", fontsize=8.4)

    descr = {
        "metacentric": "Centromere in the MIDDLE — the two arms are equal "
                       "(V-shaped at anaphase).",
        "submetacentric": "Centromere slightly off-centre — arms slightly "
                          "unequal (L-shaped).",
        "acrocentric": "Centromere near one end — one very short arm (often "
                       "bearing a satellite); J-shaped.",
        "telocentric": "Centromere at the very TIP — a single arm (i-shaped). "
                       "Not found in the normal human karyotype.",
    }
    ax.set_title(schema.title or f"Chromosome Structure — {ctype.capitalize()}",
                 fontsize=14, fontweight="bold", pad=6)
    fig.text(0.5, 0.02, descr[ctype], ha="center", fontsize=9.2,
             color="#37474f", style="italic")
    fig.tight_layout(pad=0.4, rect=(0, 0.05, 1, 1))
    return _fig_to_svg(fig)


def _render_karyotype(schema) -> str:
    fig, ax = plt.subplots(figsize=(12, 7.2))
    ax.set_xlim(0, 12); ax.set_ylim(0, 8)
    ax.axis("off")
    # 22 autosome pairs + 1 sex pair, sizes decreasing (schematic)
    n_pairs = 23
    per_row = 8
    for idx in range(n_pairs):
        row = idx // per_row
        col = idx % per_row
        x = 0.9 + col * 1.4
        y = 6.5 - row * 2.3
        h = 1.4 - 0.03 * idx if idx < 22 else 1.0
        cpos = 0.5 if idx % 3 == 0 else (0.35 if idx % 3 == 1 else 0.2)
        for k, dx in enumerate((-0.22, 0.22)):
            _draw_chromosome(ax, x + dx, y, y - h, cpos, width=0.34)
        label = str(idx + 1) if idx < 22 else "XY"
        ax.text(x, y - h - 0.28, label, ha="center", fontsize=8,
                color="#37474f", fontweight="bold")
    ax.set_title(schema.title or "Human Karyotype (46 chromosomes, 23 pairs)",
                 fontsize=14, fontweight="bold", pad=6)
    fig.text(0.5, 0.02,
             "22 pairs of autosomes plus one pair of sex chromosomes. Pairs are "
             "arranged by decreasing size and centromere position.",
             ha="center", fontsize=9, color="#37474f", style="italic")
    fig.tight_layout(pad=0.4, rect=(0, 0.04, 1, 1))
    return _fig_to_svg(fig)


def _render_sex_determination(schema) -> str:
    fig, ax = plt.subplots(figsize=(10, 8.4))
    ax.set_xlim(0, 10); ax.set_ylim(0, 9)
    ax.axis("off")

    ax.text(2.0, 8.4, "Mother  XX", ha="center", fontsize=12,
            fontweight="bold", color=C["chr_x"])
    ax.text(8.0, 8.4, "Father  XY", ha="center", fontsize=12,
            fontweight="bold", color=C["chr_y"])
    ax.text(2.0, 7.9, "(homogametic)", ha="center", fontsize=8.5,
            color="#607d8b")
    ax.text(8.0, 7.9, "(heterogametic)", ha="center", fontsize=8.5,
            color="#607d8b")

    # gametes: mother makes only X eggs; father makes X or Y sperm
    egg = (2.0, 6.4)
    ax.add_patch(Circle(egg, 0.46, fc="white", ec=C["chr_x"], lw=2.2, zorder=4))
    ax.text(egg[0], egg[1], "X", ha="center", va="center", fontsize=13,
            fontweight="bold", color=C["chr_x"], zorder=5)
    ax.text(egg[0], egg[1] - 0.8, "egg (X only)", ha="center", fontsize=8,
            color=C["chr_x"])
    sperm = {"X": (7.2, 6.4), "Y": (8.8, 6.4)}
    for g, (sx, sy) in sperm.items():
        col = C["chr_x"] if g == "X" else C["chr_y"]
        ax.add_patch(Circle((sx, sy), 0.46, fc="white", ec=col, lw=2.2,
                            zorder=4))
        ax.text(sx, sy, g, ha="center", va="center", fontsize=13,
                fontweight="bold", color=col, zorder=5)
    ax.text(8.0, 5.5, "sperm (X or Y)", ha="center", fontsize=8,
            color="#455a64")

    # offspring: egg-X + sperm-X → girl (XX); egg-X + sperm-Y → boy (XY)
    kids = [(3.6, "XX", "Girl (50%)", C["chr_x"], sperm["X"]),
            (6.4, "XY", "Boy (50%)", C["chr_y"], sperm["Y"])]
    for x, geno, sex, col, sp in kids:
        ax.add_patch(mpatches.FancyBboxPatch((x - 0.75, 2.2), 1.5, 1.3,
                     boxstyle="round,pad=0.05", fc="white", ec=col, lw=2.2,
                     zorder=4))
        ax.text(x, 3.15, geno, ha="center", fontsize=13, fontweight="bold",
                color=col, zorder=5)
        ax.text(x, 2.6, sex, ha="center", fontsize=9, color="#37474f",
                zorder=5)
        # maternal X to this child + the specific paternal gamete to this child
        ax.add_patch(FancyArrowPatch((egg[0], egg[1] - 0.5), (x - 0.15, 3.6),
                     arrowstyle="-|>", mutation_scale=12, lw=1.6,
                     color=C["chr_x"], zorder=2,
                     connectionstyle="arc3,rad=0.08"))
        ax.add_patch(FancyArrowPatch((sp[0], sp[1] - 0.5), (x + 0.15, 3.6),
                     arrowstyle="-|>", mutation_scale=12, lw=1.6, color=col,
                     zorder=2, connectionstyle="arc3,rad=-0.08"))

    ax.text(5.0, 0.9, "Ratio  50 % girls (XX) : 50 % boys (XY)", ha="center",
            fontsize=11, fontweight="bold", color="#4527a0",
            bbox=dict(boxstyle="round,pad=0.35", fc="#ede7f6", ec="#4527a0",
                      lw=1.2))
    ax.set_title(schema.title or "Sex Determination in Humans (XX / XY)",
                 fontsize=14, fontweight="bold", pad=6)
    fig.text(0.5, 0.02,
             "The mother is homogametic (all X eggs); the father is "
             "heterogametic (X or Y sperm). The father's sperm therefore "
             "determines the sex of the child.",
             ha="center", fontsize=9, color="#37474f", style="italic")
    fig.tight_layout(pad=0.4, rect=(0, 0.05, 1, 1))
    return _fig_to_svg(fig)


# ═══════════════════════════════════════════════════════════════════════════════
# 49. Animal Tissue
# ═══════════════════════════════════════════════════════════════════════════════

_TISSUE_GROUP = {
    "squamous": "epithelial", "cuboidal": "epithelial",
    "columnar": "epithelial", "ciliated": "epithelial",
    "areolar": "connective", "adipose": "connective", "bone": "connective",
    "cartilage": "connective", "blood": "connective",
    "striated": "muscular", "smooth": "muscular", "cardiac": "muscular",
    "nervous": "nervous",
}


def _basement_membrane(ax, x0, x1, y):
    ax.plot([x0, x1], [y, y], color="#6d4c41", lw=2.4, zorder=3)
    ax.plot([x0, x1], [y - 0.12, y - 0.12], color="#a1887f", lw=1.0, ls=":",
            zorder=3)


def render_animal_tissue(data: Dict[str, Any],
                         canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = AnimalTissueSchema(**data)
    t = schema.tissue
    group = _TISSUE_GROUP[t]
    lab = schema.show_labels

    fig, ax = plt.subplots(figsize=(10, 7.6))
    ax.set_xlim(0, 10); ax.set_ylim(0, 8)
    ax.axis("off")
    note = ""
    NUC = C["tissue_nucleus"]

    def nucleus(x, y, r=0.16):
        ax.add_patch(Circle((x, y), r, fc=NUC, ec="#311b92", lw=1.0, zorder=6))

    if group == "epithelial":
        bm_y = 2.2
        _basement_membrane(ax, 1.0, 9.0, bm_y)
        if t == "squamous":
            for i in range(4):
                x0 = 1.2 + i * 1.95
                ax.add_patch(mpatches.Ellipse((x0 + 0.9, bm_y + 0.45), 1.8,
                             0.7, fc=C["cell_fill"], ec=C["cell_edge"], lw=1.6,
                             zorder=4))
                nucleus(x0 + 0.9, bm_y + 0.45, 0.22)
            note = ("Squamous epithelium — flat, tile-like cells; lines alveoli "
                    "and blood vessels (diffusion).")
        elif t == "cuboidal":
            for i in range(6):
                x0 = 1.4 + i * 1.15
                ax.add_patch(Rectangle((x0, bm_y), 1.0, 1.0, fc=C["cell_fill"],
                             ec=C["cell_edge"], lw=1.6, zorder=4))
                nucleus(x0 + 0.5, bm_y + 0.5)
            note = ("Cuboidal epithelium — cube-shaped cells with central "
                    "nuclei; lines kidney tubules and gland ducts.")
        elif t == "columnar":
            for i in range(6):
                x0 = 1.4 + i * 1.15
                ax.add_patch(Rectangle((x0, bm_y), 1.0, 2.2, fc=C["cell_fill"],
                             ec=C["cell_edge"], lw=1.6, zorder=4))
                nucleus(x0 + 0.5, bm_y + 0.45)
            note = ("Columnar epithelium — tall pillar-like cells with basal "
                    "nuclei; lines the stomach and intestine.")
        else:  # ciliated
            for i in range(6):
                x0 = 1.4 + i * 1.15
                ax.add_patch(Rectangle((x0, bm_y), 1.0, 2.2, fc=C["cell_fill"],
                             ec=C["cell_edge"], lw=1.6, zorder=4))
                nucleus(x0 + 0.5, bm_y + 0.45)
                for c in np.linspace(x0 + 0.15, x0 + 0.85, 5):
                    ax.plot([c, c], [bm_y + 2.2, bm_y + 2.6], color="#00838f",
                            lw=1.2, zorder=5)
            ax.text(5.0, bm_y + 2.85, "cilia", ha="center", fontsize=8.5,
                    color="#00838f", style="italic")
            note = ("Ciliated epithelium — columnar cells bearing cilia; lines "
                    "the trachea and fallopian tubes (moves mucus / ovum).")
        if lab:
            _annotate(ax, "Basement membrane", (5.0, bm_y), (2.4, 0.9),
                      "#6d4c41", fontsize=8.5)
            _annotate(ax, "Nucleus", (2.4, bm_y + 0.45), (0.9, 4.4), NUC,
                      fontsize=8.5)

    elif group == "connective":
        if t == "areolar":
            ax.add_patch(Rectangle((1, 1.2), 8, 5.4, fc=C["matrix_ct"],
                         ec="#bdbdbd", lw=1.2, zorder=2))
            rng = np.random.RandomState(7)
            for _ in range(6):                     # collagen fibres (wavy)
                y = rng.uniform(1.6, 6.2)
                xs = np.linspace(1.2, 8.8, 60)
                ax.plot(xs, y + 0.22 * np.sin((xs) * 3 + rng.uniform(0, 3)),
                        color=C["fibre_collagen"], lw=2.2, zorder=3)
            for _ in range(4):                     # elastin fibres (straight)
                y = rng.uniform(1.6, 6.2)
                ax.plot([1.2, 8.8], [y, y + rng.uniform(-0.6, 0.6)],
                        color=C["fibre_elastin"], lw=1.2, zorder=3)
            for _ in range(6):                     # fibroblasts
                x, y = rng.uniform(1.6, 8.4), rng.uniform(1.6, 6.2)
                ax.add_patch(mpatches.Ellipse((x, y), 0.7, 0.32,
                             angle=rng.uniform(0, 180), fc="#ffe0b2",
                             ec="#8d6e63", lw=1.2, zorder=4))
                nucleus(x, y, 0.12)
            note = ("Areolar (loose) connective tissue — a jelly matrix with "
                    "collagen + elastin fibres, fibroblasts and mast cells; "
                    "fills spaces between organs.")
            if lab:
                _annotate(ax, "Collagen fibre", (4.6, 4.6), (7.6, 7.2),
                          C["fibre_collagen"], fontsize=8.3)
                _annotate(ax, "Elastin fibre", (3.4, 3.0), (0.9, 7.0),
                          "#2e7d32", fontsize=8.3)
                _annotate(ax, "Fibroblast", (5.0, 2.4), (6.6, 0.8),
                          "#8d6e63", fontsize=8.3)
        elif t == "adipose":
            for gx in range(3):
                for gy in range(2):
                    x = 2.2 + gx * 2.8
                    y = 2.2 + gy * 2.6
                    ax.add_patch(Circle((x, y), 1.15, fc="#fff8e1",
                                 ec="#f9a825", lw=1.8, zorder=4))
                    ax.add_patch(Circle((x, y), 0.9, fc="#fffde7",
                                 ec="#fdd835", lw=1.0, zorder=5))  # fat globule
                    nucleus(x + 0.85, y + 0.55, 0.16)              # pushed to rim
            note = ("Adipose tissue — cells packed with a large fat globule "
                    "that pushes the nucleus to the periphery; stores fat and "
                    "insulates.")
            if lab:
                _annotate(ax, "Fat globule", (2.2, 2.2), (0.8, 6.6),
                          "#f9a825", fontsize=8.3)
                _annotate(ax, "Peripheral nucleus", (3.05, 2.75), (6.8, 6.9),
                          NUC, fontsize=8.3)
        elif t == "bone":
            ax.add_patch(Circle((5, 4), 3.0, fc="#eceff1", ec="#90a4ae",
                         lw=2.0, zorder=2))
            for r in (0.9, 1.5, 2.1, 2.7):         # concentric lamellae
                ax.add_patch(Circle((5, 4), r, fc="none", ec="#b0bec5",
                             lw=1.4, zorder=3))
            ax.add_patch(Circle((5, 4), 0.45, fc="#c62828", ec="#7f0000",
                         lw=1.6, zorder=4))        # Haversian canal
            for r in (1.2, 1.8, 2.4):              # lacunae with osteocytes
                for a in np.linspace(0, 2 * np.pi, 8, endpoint=False):
                    x, y = 5 + r * math.cos(a), 4 + r * math.sin(a)
                    ax.add_patch(mpatches.Ellipse((x, y), 0.26, 0.14,
                                 angle=math.degrees(a), fc="#5e35b1",
                                 ec="#311b92", lw=1.0, zorder=5))
            note = ("Bone (compact) — a Haversian system: a central canal with "
                    "blood vessels ringed by hard concentric lamellae; "
                    "osteocytes sit in lacunae.")
            if lab:
                _annotate(ax, "Haversian canal", (5, 4), (8.4, 5.2), "#c62828",
                          fontsize=8.3)
                _annotate(ax, "Lamellae", (6.2, 4), (8.6, 3.0), "#607d8b",
                          fontsize=8.3)
                _annotate(ax, "Lacuna (osteocyte)", (5, 5.8), (2.0, 7.2),
                          "#5e35b1", fontsize=8.3)
        elif t == "cartilage":
            ax.add_patch(Rectangle((1, 1.2), 8, 5.4, fc=C["cartilage_m"],
                         ec="#4fc3f7", lw=1.6, zorder=2))
            rng = np.random.RandomState(9)
            for _ in range(9):
                x, y = rng.uniform(1.8, 8.2), rng.uniform(1.8, 6.0)
                ax.add_patch(mpatches.Ellipse((x, y), 1.0, 0.8, fc="white",
                             ec="#0288d1", lw=1.4, zorder=3))   # lacuna
                for dx in (-0.2, 0.2):
                    nucleus(x + dx, y, 0.16)                    # chondrocytes
            note = ("Cartilage — chondrocytes lodged in fluid-filled lacunae "
                    "within a firm matrix (chondrin); at joints, nose and ear "
                    "pinna.")
            if lab:
                _annotate(ax, "Chondrocyte", (5, 4), (7.8, 7.0), NUC,
                          fontsize=8.3)
                _annotate(ax, "Lacuna", (5.5, 4), (8.2, 2.0), "#0288d1",
                          fontsize=8.3)
                _annotate(ax, "Matrix (chondrin)", (2.4, 5.6), (0.8, 7.2),
                          "#0288d1", fontsize=8.3)
        else:  # blood
            ax.add_patch(Rectangle((1, 1.2), 8, 5.4, fc="#fff3e0",
                         ec="#ffb74d", lw=1.2, zorder=2))
            rng = np.random.RandomState(11)
            for _ in range(14):                    # RBCs — biconcave discs
                x, y = rng.uniform(1.6, 8.4), rng.uniform(1.6, 6.2)
                ax.add_patch(Circle((x, y), 0.42, fc=C["rbc"], ec="#7f0000",
                             lw=1.2, zorder=3))
                ax.add_patch(Circle((x, y), 0.17, fc="#e57373", ec="none",
                             zorder=4))            # pale centre (no nucleus)
            for _ in range(3):                     # WBCs — nucleated
                x, y = rng.uniform(2.0, 8.0), rng.uniform(2.0, 6.0)
                ax.add_patch(Circle((x, y), 0.5, fc="#ede7f6", ec="#7e57c2",
                             lw=1.4, zorder=4))
                nucleus(x, y, 0.26)
            for _ in range(6):                     # platelets
                x, y = rng.uniform(1.8, 8.2), rng.uniform(1.8, 6.0)
                ax.add_patch(Circle((x, y), 0.10, fc="#5d4037", ec="none",
                             zorder=4))
            note = ("Blood — a fluid connective tissue: biconcave RBCs (no "
                    "nucleus), nucleated WBCs and platelets in plasma.")
            if lab:
                _annotate(ax, "RBC (erythrocyte)", (4.4, 4.2), (7.6, 7.1),
                          C["rbc"], fontsize=8.3)
                _annotate(ax, "WBC (leucocyte)", (5.4, 3.4), (8.2, 1.0),
                          "#7e57c2", fontsize=8.3)
                _annotate(ax, "Platelets", (3.0, 2.4), (0.9, 1.0), "#5d4037",
                          fontsize=8.3)

    elif group == "muscular":
        if t == "striated":
            for i in range(3):
                y = 1.8 + i * 1.9
                ax.add_patch(mpatches.FancyBboxPatch((1.0, y), 8.0, 1.2,
                             boxstyle="round,pad=0.02", fc=C["muscle_fibre"],
                             ec="#c62828", lw=1.8, zorder=3))
                for xb in np.linspace(1.3, 8.7, 26):
                    ax.plot([xb, xb], [y + 0.1, y + 1.1], color="#7f0000",
                            lw=0.8, zorder=4)      # cross striations
                for xn in (2.2, 4.6, 7.0):
                    nucleus(xn, y + 1.0, 0.15)     # peripheral, multinucleate
            note = ("Striated (skeletal) muscle — long, cylindrical, "
                    "unbranched, MULTINUCLEATE fibres with cross striations; "
                    "voluntary.")
            if lab:
                _annotate(ax, "Cross striations", (5.0, 3.6), (7.8, 7.2),
                          "#7f0000", fontsize=8.3)
                _annotate(ax, "Peripheral nuclei", (4.6, 4.7), (1.4, 7.2),
                          NUC, fontsize=8.3)
        elif t == "smooth":
            rng = np.random.RandomState(4)
            for i in range(7):
                x = 1.4 + i * 1.1
                ax.add_patch(mpatches.Ellipse((x, 4), 0.7, 3.4,
                             angle=8 * ((-1) ** i), fc=C["muscle_fibre"],
                             ec="#c62828", lw=1.6, zorder=3))
                nucleus(x, 4, 0.2)                 # single central nucleus
            note = ("Smooth (unstriated) muscle — spindle-shaped cells, each "
                    "with ONE central nucleus, no striations; involuntary "
                    "(gut, blood vessels).")
            if lab:
                _annotate(ax, "Spindle-shaped cell", (2.5, 5.2), (2.0, 7.2),
                          "#c62828", fontsize=8.3)
                _annotate(ax, "Central nucleus", (4.7, 4), (7.6, 6.8), NUC,
                          fontsize=8.3)
        else:  # cardiac
            for i in range(2):
                y = 2.4 + i * 2.4
                ax.add_patch(mpatches.FancyBboxPatch((1.0, y), 8.0, 1.4,
                             boxstyle="round,pad=0.02", fc=C["muscle_fibre"],
                             ec="#c62828", lw=1.8, zorder=3))
                for xb in np.linspace(1.3, 8.7, 22):
                    ax.plot([xb, xb], [y + 0.15, y + 1.25], color="#7f0000",
                            lw=0.7, zorder=4)
                for xd in (3.0, 5.6, 7.8):         # intercalated discs
                    ax.plot([xd, xd], [y, y + 1.4], color="#311b92", lw=2.6,
                            zorder=5)
                nucleus(2.0, y + 0.7, 0.18)
                nucleus(6.6, y + 0.7, 0.18)
            note = ("Cardiac muscle — branched, striated, UNINUCLEATE fibres "
                    "joined by intercalated discs; involuntary and never "
                    "fatigues (heart).")
            if lab:
                _annotate(ax, "Intercalated disc", (3.0, 3.1), (5.4, 1.0),
                          "#311b92", fontsize=8.3)
                _annotate(ax, "Striations", (5.0, 5.6), (7.8, 7.2), "#7f0000",
                          fontsize=8.3)

    else:  # nervous
        soma = (3.0, 4.0)
        ax.add_patch(Circle(soma, 0.85, fc="#ffe0b2", ec=C["nerve_cell"],
                     lw=2.2, zorder=4))
        nucleus(soma[0], soma[1], 0.28)
        for a in np.linspace(70, 290, 6):          # dendrites
            x2 = soma[0] + 1.6 * math.cos(math.radians(a))
            y2 = soma[1] + 1.6 * math.sin(math.radians(a))
            ax.plot([soma[0] + 0.8 * math.cos(math.radians(a)), x2],
                    [soma[1] + 0.8 * math.sin(math.radians(a)), y2],
                    color=C["neuron_dendrite"], lw=1.8, zorder=3)
        ax.plot([3.85, 8.4], [4.0, 4.0], color=C["neuron_axon"], lw=2.6,
                zorder=3)                            # axon
        for nx in np.arange(4.4, 8.2, 1.2):         # myelin sheath
            ax.add_patch(mpatches.FancyBboxPatch((nx, 3.7), 0.9, 0.6,
                         boxstyle="round,pad=0.03", fc=C["neuron_myelin"],
                         ec="#f9a825", lw=1.2, zorder=4))
        for dy, ox in ((0, 0.5), (0.5, 0.5), (-0.5, 0.5)):
            ax.add_patch(Circle((8.4 + ox, 4.0 + dy), 0.2, fc="#e8f5e9",
                         ec=C["neuron_axon"], lw=1.4, zorder=4))
        note = ("Nervous tissue — neurons (cell body + dendrites + axon) that "
                "conduct impulses, supported by neuroglia.")
        if lab:
            _annotate(ax, "Cell body (cyton)", soma, (2.0, 6.6),
                      C["nerve_cell"], fontsize=8.4)
            _annotate(ax, "Dendrites", (1.9, 5.0), (0.8, 6.6),
                      C["neuron_dendrite"], fontsize=8.4)
            _annotate(ax, "Axon", (6.0, 4.0), (6.0, 6.4), C["neuron_axon"],
                      fontsize=8.4)
            _annotate(ax, "Myelin sheath", (5.2, 4.3), (3.2, 1.2), "#f9a825",
                      fontsize=8.4)
            _annotate(ax, "Axon terminals", (8.9, 4.0), (8.4, 6.4),
                      C["neuron_axon"], fontsize=8.4)

    ax.set_title(schema.title or
                 f"{group.capitalize()} Tissue — {t.capitalize()}",
                 fontsize=14, fontweight="bold", pad=6)
    fig.text(0.5, 0.02, _wrap(note, 96), ha="center", fontsize=9,
             color="#37474f", style="italic")
    fig.tight_layout(pad=0.4, rect=(0, 0.05, 1, 1))
    return _fig_to_svg(fig)


# ═══════════════════════════════════════════════════════════════════════════════
# 50. Animal Anatomy (NCERT sectional / systemic schematics)
# ═══════════════════════════════════════════════════════════════════════════════

# Ordered parts of each organism/system. A labelled ordered chain answers the
# NEET asks directly ("trace the path", "name the labelled part") without
# risking an elaborate-but-wrong sectional drawing.
_ANIMAL_ANATOMY = {
    "earthworm": {
        "digestive": (["Mouth", "Buccal cavity", "Pharynx", "Oesophagus",
                       "Gizzard", "Stomach", "Intestine (typhlosole)", "Anus"],
                      "Earthworm alimentary canal — the typhlosole folds the "
                      "intestine wall to increase absorptive area."),
        "circulatory": (["Dorsal blood vessel", "Lateral hearts (seg 7–11)",
                         "Ventral blood vessel", "Capillary network",
                         "Blood glands"],
                        "Earthworm has a CLOSED circulatory system; four pairs "
                        "of lateral hearts pump blood."),
        "nervous": (["Cerebral ganglia", "Circumpharyngeal connectives",
                     "Sub-pharyngeal ganglion", "Ventral nerve cord",
                     "Segmental ganglia"],
                    "Earthworm nervous system — a nerve ring round the pharynx "
                    "leading to a ganglionated ventral nerve cord."),
        "reproductive": (["Testes (seg 10–11)", "Seminal vesicles",
                          "Ovaries (seg 13)", "Spermathecae (seg 6–9)",
                          "Clitellum (seg 14–16)"],
                         "Earthworm is HERMAPHRODITE (bisexual) but cross-"
                         "fertilises; the clitellum secretes the cocoon."),
    },
    "cockroach": {
        "digestive": (["Mouth", "Pharynx", "Oesophagus", "Crop (storage)",
                       "Gizzard / proventriculus", "Gastric caeca",
                       "Midgut (mesenteron)", "Malpighian tubules",
                       "Ileum", "Colon", "Rectum", "Anus"],
                      "Cockroach gut — the crop stores food, the gizzard grinds "
                      "it; Malpighian tubules (excretory) lie at the midgut–"
                      "hindgut junction."),
        "circulatory": (["Dorsal tubular heart (13 chambers)", "Ostia (valves)",
                         "Haemocoel (body cavity)", "Blood sinuses"],
                        "Cockroach has an OPEN circulatory system; colourless "
                        "haemolymph bathes the organs in the haemocoel."),
        "nervous": (["Supra-oesophageal ganglion (brain)",
                     "Sub-oesophageal ganglion", "3 thoracic ganglia",
                     "6 abdominal ganglia", "Ventral nerve cord"],
                    "Cockroach nervous system — a double, ganglionated ventral "
                    "nerve cord; much control is decentralised in the ganglia."),
        "reproductive": (["Testes", "Vas deferens", "Seminal vesicle",
                          "Mushroom (utricular) gland", "Ejaculatory duct",
                          "Phallic gland"],
                         "Cockroach is DIOECIOUS (sexes separate); the male "
                         "reproductive system shown, with the mushroom gland."),
    },
    "frog": {
        "digestive": (["Mouth", "Buccal cavity", "Oesophagus", "Stomach",
                       "Duodenum", "Ileum", "Large intestine", "Cloaca"],
                      "Frog alimentary canal — liver and pancreas pour "
                      "secretions into the duodenum; all waste exits the "
                      "cloaca."),
        "circulatory": (["Sinus venosus", "Right & left atria", "Ventricle",
                         "Truncus arteriosus", "Carotid / systemic / "
                         "pulmocutaneous arches"],
                        "Frog heart is THREE-CHAMBERED (two atria, one "
                        "ventricle); incomplete separation mixes the blood."),
        "nervous": (["Fore-brain (olfactory lobes + cerebrum)",
                     "Mid-brain (optic lobes)",
                     "Hind-brain (cerebellum + medulla)", "Spinal cord",
                     "10 pairs of cranial nerves"],
                    "Frog brain in three regions; 10 pairs of cranial nerves "
                    "(against 12 in mammals)."),
        "reproductive": (["Testes", "Vasa efferentia", "Kidney (Bidder's "
                          "canal)", "Ureter", "Cloaca"],
                         "Male frog — sperm pass from the testes through the "
                         "kidney and ureter to the cloaca."),
    },
}


def render_animal_anatomy(data: Dict[str, Any],
                          canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = AnimalAnatomySchema(**data)
    org, sysname = schema.organism, schema.system
    parts, note = _ANIMAL_ANATOMY[org][sysname]
    lab = schema.show_labels
    is_flow = sysname == "digestive"

    n = len(parts)
    per_row = 4
    rows = math.ceil(n / per_row)
    fig, ax = plt.subplots(figsize=(12.5, 1.9 * rows + 2.2))
    ax.set_xlim(0, 12.5); ax.set_ylim(0, 1.9 * rows + 1.4)
    ax.axis("off")

    body_col = {"earthworm": "#f8bbd0", "cockroach": "#d7ccc8",
                "frog": "#c8e6c9"}[org]
    seg_col = {"digestive": C["anat_gut"], "circulatory": C["anat_vessel"],
               "nervous": C["anat_nerve"], "reproductive": C["anat_gonad"]}[sysname]
    edge = {"digestive": "#c62828", "circulatory": "#7f0000",
            "nervous": "#f9a825", "reproductive": "#4a148c"}[sysname]

    # faint organism silhouette behind the chain
    top = 1.9 * rows + 0.6
    ax.add_patch(mpatches.FancyBboxPatch((0.3, 0.4), 11.9, top - 0.2,
                 boxstyle="round,pad=0.05,rounding_size=0.4", fc=body_col,
                 ec="#bdbdbd", lw=1.2, alpha=0.35, zorder=0))

    centres = []
    for i, part in enumerate(parts):
        r = i // per_row
        c = i % per_row
        if r % 2 == 1:                     # serpentine (boustrophedon) ordering
            c = per_row - 1 - c
        x = 1.7 + c * 3.0
        y = top - 0.9 - r * 1.9
        centres.append((x, y))
        ax.add_patch(mpatches.FancyBboxPatch((x - 1.3, y - 0.55), 2.6, 1.1,
                     boxstyle="round,pad=0.05", fc="white", ec=edge, lw=1.8,
                     zorder=4))
        ax.text(x, y, _wrap(part, 20), ha="center", va="center", fontsize=8.3,
                color="#37474f", fontweight="bold", zorder=5)
        ax.add_patch(Circle((x - 1.05, y + 0.32), 0.13, fc=seg_col,
                            ec=edge, lw=1.0, zorder=6))
        ax.text(x - 1.05, y + 0.32, str(i + 1), ha="center", va="center",
                fontsize=7, color="white", zorder=7)

    # connect consecutive parts (arrows for the food path, plain links else)
    for i in range(n - 1):
        a, b = centres[i], centres[i + 1]
        style = "-|>" if is_flow else "-"
        ax.add_patch(FancyArrowPatch(a, b, arrowstyle=style, mutation_scale=14,
                     lw=1.8, color=seg_col, zorder=2,
                     connectionstyle="arc3,rad=0.0", shrinkA=34, shrinkB=34))

    sys_title = sysname.capitalize()
    ax.set_title(schema.title or
                 f"{org.capitalize()} — {sys_title} System (schematic)",
                 fontsize=14, fontweight="bold", pad=6)
    fig.text(0.5, 0.02, _wrap(note, 110), ha="center", fontsize=9,
             color="#37474f", style="italic")
    fig.tight_layout(pad=0.4, rect=(0, 0.05, 1, 1))
    return _fig_to_svg(fig)


# ═══════════════════════════════════════════════════════════════════════════════
# 51. Immune Response
# ═══════════════════════════════════════════════════════════════════════════════

def render_immune_response(data: Dict[str, Any],
                           canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = ImmuneResponseSchema(**data)
    lab = schema.show_labels

    if schema.view == "response_curve":
        return _render_immune_curve(schema)

    # ── Antibody (immunoglobulin) structure — Y-shaped ────────────────────────
    fig, ax = plt.subplots(figsize=(9.5, 8.6))
    ax.set_xlim(0, 10); ax.set_ylim(0, 9)
    ax.set_aspect("equal"); ax.axis("off")
    cx, cy = 5.0, 3.4

    # two heavy chains (inner, from the stem splaying into both arms)
    for s in (-1, 1):
        ax.plot([cx, cx + s * 2.2], [cy + 0.6, cy + 3.6], color=C["heavy_chain"],
                lw=9, solid_capstyle="round", zorder=3)
    ax.plot([cx, cx], [cy - 1.6, cy + 0.6], color=C["heavy_chain"], lw=9,
            solid_capstyle="round", zorder=3)          # stem (Fc)
    # two light chains (outer, along each arm)
    for s in (-1, 1):
        ax.plot([cx + s * 0.55, cx + s * 2.55], [cy + 1.4, cy + 3.75],
                color=C["light_chain"], lw=6, solid_capstyle="round", zorder=4)
    # variable-region tips (antigen-binding sites)
    for s in (-1, 1):
        ax.add_patch(Circle((cx + s * 2.4, cy + 3.7), 0.28,
                            fc=C["variable_region"], ec="#880e4f", lw=1.4,
                            zorder=5))
        ax.add_patch(Circle((cx + s * 1.85, cy + 3.55), 0.24,
                            fc=C["variable_region"], ec="#880e4f", lw=1.2,
                            zorder=5))
        # antigen sitting in the binding cleft
        ax.add_patch(mpatches.RegularPolygon((cx + s * 2.55, cy + 4.3), 3,
                     radius=0.34, orientation=math.radians(180),
                     fc=C["antigen"], ec="#1b5e20", lw=1.2, zorder=6))
    # disulfide bonds between heavy chains at the hinge
    ax.plot([cx - 0.18, cx + 0.18], [cy + 0.65, cy + 0.65], color="#37474f",
            lw=2.0, zorder=6)
    ax.plot([cx - 0.18, cx + 0.18], [cy + 0.35, cy + 0.35], color="#37474f",
            lw=2.0, zorder=6)

    if lab:
        _annotate(ax, "Antigen-binding site\n(paratope)", (cx + 2.5, cy + 4.2),
                  (cx + 3.6, cy + 4.6), C["antigen"], fontsize=8.4)
        _annotate(ax, "Variable region (V)", (cx + 2.1, cy + 3.6),
                  (cx + 3.9, cy + 3.0), C["variable_region"], fontsize=8.4)
        _annotate(ax, "Light chain", (cx + 1.7, cy + 2.7), (cx + 3.7, cy + 1.6),
                  C["light_chain"], fontsize=8.4)
        _annotate(ax, "Heavy chain", (cx - 1.3, cy + 2.1), (cx - 3.6, cy + 1.4),
                  C["heavy_chain"], fontsize=8.4)
        _annotate(ax, "Constant region (C)", (cx, cy - 0.6), (cx - 3.5, cy - 1.0),
                  C["constant_region"], fontsize=8.4)
        _annotate(ax, "Disulphide bonds\n(hinge)", (cx, cy + 0.5),
                  (cx + 2.9, cy - 0.4), "#37474f", fontsize=8.4)
        ax.text(cx, cy - 2.1, "Fc region (stem)", ha="center", fontsize=8.4,
                color=C["heavy_chain"])

    ax.set_title(schema.title or "Antibody (Immunoglobulin) Structure",
                 fontsize=14, fontweight="bold", pad=6)
    fig.text(0.5, 0.02,
             "Each Y-shaped antibody has 2 heavy + 2 light chains held by "
             "disulphide bonds; the two variable-region tips are the antigen-"
             "binding sites (specificity). Formula H₂L₂.",
             ha="center", fontsize=8.6, color="#37474f", style="italic")
    fig.tight_layout(pad=0.4, rect=(0, 0.05, 1, 1))
    return _fig_to_svg(fig)


def _render_immune_curve(schema) -> str:
    fig, ax = plt.subplots(figsize=(11, 7))
    t = np.linspace(0, 60, 600)
    # smooth onset gates (a short lag ramp) avoid an unnatural vertical jump
    gate1 = np.clip((t - 3) / 3.0, 0, 1)
    gate2 = np.clip((t - 30) / 3.0, 0, 1)
    # primary: first exposure at day 0, lag then a modest peak
    primary = _gauss(t, 16, 6, 30) * gate1
    # secondary: second exposure at day 30, faster + far larger peak
    secondary = _gauss(t, 40, 5, 100) * gate2
    ax.plot(t, primary + 1, color=C["titre_primary"], lw=3.0,
            label="Primary response (1st exposure)")
    ax.plot(t, primary + secondary + 1, color=C["titre_secondary"], lw=3.0,
            label="Secondary response (2nd exposure)")
    for xd, name, col in ((0, "1st antigen\nexposure", C["titre_primary"]),
                          (30, "2nd antigen\nexposure (same)",
                           C["titre_secondary"])):
        ax.axvline(xd, color=col, lw=1.2, ls="--", zorder=1)
        ax.text(xd + 0.6, 95, name, fontsize=8.5, color=col, va="top")
    ax.annotate("Secondary response is FASTER,\nSTRONGER and longer-lasting\n"
                "(memory cells)", xy=(40, 100), xytext=(46, 70),
                fontsize=9, color=C["titre_secondary"], fontweight="bold",
                ha="left",
                arrowprops=dict(arrowstyle="-|>", color=C["titre_secondary"],
                                lw=1.2))
    ax.set_yscale("log")
    ax.set_xlim(0, 60); ax.set_ylim(1, 200)
    ax.set_xlabel("Time (days)", fontsize=11)
    ax.set_ylabel("Antibody titre (log scale)", fontsize=11)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(alpha=0.15, which="both")
    ax.legend(loc="upper left", fontsize=9.5, framealpha=0.95)
    ax.set_title(schema.title or "Primary vs Secondary Immune Response",
                 fontsize=14, fontweight="bold", pad=8)
    fig.text(0.5, 0.015,
             "On re-exposure to the same antigen, memory B-cells trigger a "
             "secondary response with a shorter lag and a much higher antibody "
             "titre — the basis of immunological memory and vaccination.",
             ha="center", fontsize=8.8, color="#37474f", style="italic")
    fig.tight_layout(pad=0.5, rect=(0, 0.05, 1, 1))
    return _fig_to_svg(fig)


# ═══════════════════════════════════════════════════════════════════════════════
# 52. Ecological Succession / Age Pyramid
# ═══════════════════════════════════════════════════════════════════════════════

def render_ecological_succession(data: Dict[str, Any],
                                 canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = EcologicalSuccessionSchema(**data)
    if schema.view == "age_pyramid":
        return _render_age_pyramid(schema)

    lab = schema.show_labels
    primary = schema.succession_type == "primary"
    if primary:
        stages = [("Bare rock", "pioneer", 0.5),
                  ("Lichens\n(pioneer)", "lichen", 0.9),
                  ("Mosses", "moss", 1.5),
                  ("Herbs / grasses", "herb", 2.4),
                  ("Shrubs", "shrub", 3.4),
                  ("Forest\n(climax)", "forest", 4.6)]
        note = ("Primary succession — life colonises a bare, lifeless surface "
                "(rock). Lichens are the PIONEER community; the forest is the "
                "stable CLIMAX community. Very slow.")
    else:
        stages = [("Cleared land\n(soil intact)", "pioneer", 0.8),
                  ("Grasses / weeds", "herb", 1.8),
                  ("Shrubs", "shrub", 3.0),
                  ("Young trees", "moss", 4.0),
                  ("Forest\n(climax)", "forest", 4.8)]
        note = ("Secondary succession — begins where a community was cleared "
                "(fire, flood) but SOIL remains, so it is much FASTER, reaching "
                "the same climax.")

    n = len(stages)
    fig, ax = plt.subplots(figsize=(2.4 * n + 1, 6.4))
    ax.set_xlim(0, n * 2.4); ax.set_ylim(0, 6.4)
    ax.axis("off")
    ax.plot([0.3, n * 2.4 - 0.3], [1.0, 1.0], color="#6d4c41", lw=2.4,
            zorder=2)

    for i, (name, col, h) in enumerate(stages):
        cx = 1.2 + i * 2.4
        # simple vegetation glyph scaling with succession
        if col in ("pioneer",):
            ax.add_patch(mpatches.FancyBboxPatch((cx - 0.9, 0.6), 1.8, 0.4,
                         boxstyle="round,pad=0.02", fc="#bcaaa4",
                         ec="#6d4c41", lw=1.4, zorder=3))
        elif col in ("lichen", "moss"):
            for dx in (-0.5, 0, 0.5):
                ax.add_patch(mpatches.Ellipse((cx + dx, 1.1 + h * 0.1),
                             0.6, 0.3 + h * 0.1, fc=C[col], ec="#33691e",
                             lw=1.2, zorder=3))
        else:
            ax.plot([cx, cx], [1.0, 1.0 + h], color="#6d4c41",
                    lw=2.5 + h, zorder=3)
            ax.add_patch(Circle((cx, 1.0 + h), 0.35 + h * 0.16, fc=C[col],
                                ec="#1b5e20", lw=1.6, zorder=4))
            if col in ("shrub", "forest"):
                for dx in (-0.5, 0.5):
                    ax.add_patch(Circle((cx + dx, 0.9 + h * 0.85),
                                 0.28 + h * 0.10, fc=C[col], ec="#1b5e20",
                                 lw=1.2, zorder=4))
        ax.text(cx, 0.55, name, ha="center", va="top", fontsize=8.4,
                fontweight="bold", color="#37474f")
        if i < n - 1:
            ax.add_patch(FancyArrowPatch((cx + 0.95, 1.9),
                         (cx + 2.4 - 0.95, 1.9), arrowstyle="-|>",
                         mutation_scale=15, lw=2.0, color=C["cycle_arrow"],
                         zorder=2))
    ax.annotate("increasing time, biomass & species diversity",
                xy=(n * 2.4 - 1.0, 5.6), xytext=(1.0, 5.6), fontsize=9,
                color="#607d8b", va="center",
                arrowprops=dict(arrowstyle="-|>", color="#607d8b", lw=1.4))

    ax.set_title(schema.title or
                 f"{'Primary' if primary else 'Secondary'} Ecological "
                 f"Succession", fontsize=14, fontweight="bold", pad=6)
    fig.text(0.5, 0.02, _wrap(note, 104), ha="center", fontsize=9,
             color="#37474f", style="italic")
    fig.tight_layout(pad=0.4, rect=(0, 0.05, 1, 1))
    return _fig_to_svg(fig)


# (pre-reproductive, reproductive, post-reproductive) relative half-widths.
# The broad-vs-narrow BASE is the whole demographic message, so both the drawing
# and the test read this one table.
_AGE_PYRAMID_SHAPES = {
    "expanding": [3.8, 2.4, 1.1],     # broad base — many young → growing
    "stable":    [2.6, 2.5, 1.9],     # bell — roughly equal → steady
    "declining": [1.4, 2.5, 2.2],     # narrow base — few young → shrinking
}


def _render_age_pyramid(schema) -> str:
    ptype = schema.pyramid_type
    fig, ax = plt.subplots(figsize=(8.6, 7.6))
    ax.set_xlim(-6, 6); ax.set_ylim(0, 7)
    ax.axis("off")

    widths = _AGE_PYRAMID_SHAPES[ptype]
    bands = [("Pre-reproductive\n(0–14 yr)", C["pyramid_pre"]),
             ("Reproductive\n(15–44 yr)", C["pyramid_repro"]),
             ("Post-reproductive\n(45+ yr)", C["pyramid_post"])]
    y0 = 1.0
    for i, ((name, col), w) in enumerate(zip(bands, widths)):
        wl = w
        wu = widths[i + 1] if i + 1 < len(widths) else w * 0.4
        y1 = y0 + 1.6
        poly = Polygon([(-wl, y0), (wl, y0), (wu, y1), (-wu, y1)], closed=True,
                       fc=col, ec="#37474f", lw=1.6, zorder=3)
        ax.add_patch(poly)
        ax.text(0, (y0 + y1) / 2, name, ha="center", va="center", fontsize=8.6,
                fontweight="bold", color="#263238", zorder=4)
        y0 = y1
    ax.axvline(0, color="#90a4ae", lw=1.0, ls=":", zorder=1)
    ax.text(-4.2, 0.5, "Male", ha="center", fontsize=9, color="#455a64")
    ax.text(4.2, 0.5, "Female", ha="center", fontsize=9, color="#455a64")

    notes = {
        "expanding": "Expanding (pyramid-shaped) — a broad base of young "
                     "individuals; the population is GROWING rapidly.",
        "stable": "Stable (bell-shaped) — pre-reproductive ≈ reproductive; "
                  "birth ≈ death, so population size is steady.",
        "declining": "Declining (urn-shaped) — a narrow base; more old than "
                     "young, so the population is SHRINKING.",
    }
    ax.set_title(schema.title or f"Age Pyramid — {ptype.capitalize()} "
                 "Population", fontsize=14, fontweight="bold", pad=6)
    fig.text(0.5, 0.02, _wrap(notes[ptype], 92), ha="center", fontsize=9,
             color="#37474f", style="italic")
    fig.tight_layout(pad=0.4, rect=(0, 0.05, 1, 1))
    return _fig_to_svg(fig)


# ═══════════════════════════════════════════════════════════════════════════════
# 53. Biotechnology Workflow
# ═══════════════════════════════════════════════════════════════════════════════

def _stage_box(ax, x, y, w, h, title, col, body=None):
    ax.add_patch(mpatches.FancyBboxPatch((x - w / 2, y - h / 2), w, h,
                 boxstyle="round,pad=0.05", fc="white", ec=col, lw=2.0,
                 zorder=3))
    ax.text(x, y + h / 2 - 0.28, title, ha="center", va="center", fontsize=9,
            fontweight="bold", color=col, zorder=4)
    if body:
        ax.text(x, y - 0.15, body, ha="center", va="center", fontsize=7.8,
                color="#37474f", zorder=4)


def render_biotech_workflow(data: Dict[str, Any],
                            canvas_w: int = 800, canvas_h: int = 600) -> str:
    schema = BiotechWorkflowSchema(**data)
    proc = schema.process
    lab = schema.show_labels

    fig, ax = plt.subplots(figsize=(12.5, 8.0))
    ax.set_xlim(0, 12.5); ax.set_ylim(0, 9)
    ax.axis("off")

    if proc == "pcr":
        cx, cy, r = 6.25, 4.9, 2.9
        # steps at 90° (top), 210° (bottom-left), 330° (bottom-right)
        steps = [(90, "Denaturation", "94 °C — strands separate",
                  C["pcr_denature"]),
                 (210, "Annealing", "55 °C — primers bind", C["pcr_anneal"]),
                 (330, "Extension", "72 °C — Taq polymerase\ncopies each strand",
                  C["pcr_extend"])]
        for ang, name, body, col in steps:
            x = cx + r * math.cos(math.radians(ang))
            y = cy + r * math.sin(math.radians(ang))
            _stage_box(ax, x, y, 3.0, 1.4, name, col, body)
        # clean arcs OUTSIDE the triangle, denat → anneal → extension → denat
        Rp = r + 0.55
        for A in (90, 210, 330):
            a0 = math.radians(A + 42)
            a1 = math.radians(A + 120 - 42)
            p0 = (cx + Rp * math.cos(a0), cy + Rp * math.sin(a0))
            p1 = (cx + Rp * math.cos(a1), cy + Rp * math.sin(a1))
            ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle="-|>",
                         mutation_scale=17, lw=2.4, color=C["cycle_arrow"],
                         zorder=2, connectionstyle="arc3,rad=-0.28"))
        ax.text(cx, cy + 0.35, "PCR\ncycle", ha="center", va="center",
                fontsize=12, fontweight="bold", color="#455a64")
        ax.text(cx, cy - 0.5, "×25–35", ha="center", fontsize=9,
                color="#607d8b")
        # exponential amplification strip
        for i, k in enumerate((1, 2, 4, 8, 16)):
            ax.text(1.0 + i * 0.7, 0.8, f"{k}", ha="center", fontsize=8,
                    color=C["pcr_extend"], fontweight="bold")
        ax.text(1.0, 1.2, "copies double each cycle (exponential):",
                ha="left", fontsize=8.4, color="#37474f")
        note = ("PCR amplifies DNA in vitro by repeating denaturation, "
                "annealing and extension; each cycle DOUBLES the target — "
                "millions of copies in ~30 cycles.")

    elif proc == "recombinant_dna":
        # vector (plasmid) + insert cut by the SAME restriction enzyme
        ax.add_patch(Circle((2.4, 6.4), 1.2, fc="none", ec=C["vector"],
                            lw=3.0, zorder=3))
        ax.text(2.4, 6.4, "Vector\n(plasmid)", ha="center", va="center",
                fontsize=8.5, color=C["vector"], fontweight="bold")
        _cross(ax, 2.4, 7.6, size=0.18, color=C["restr_enzyme"])
        ax.add_patch(Rectangle((6.0, 6.0), 3.0, 0.7, fc=C["insert_dna"],
                     ec="#e65100", lw=2.0, zorder=3))
        ax.text(7.5, 6.35, "Gene of interest (insert)", ha="center",
                va="center", fontsize=8.2, color="white", fontweight="bold")
        ax.text(5.0, 8.2, "Both cut by the SAME restriction enzyme, "
                "giving matching STICKY ENDS", ha="center", fontsize=8.6,
                color=C["restr_enzyme"], fontweight="bold")
        _fwd_arrow(ax, (5.0, 5.4), (5.0, 4.4), C["cycle_arrow"], lw=2.4)
        ax.text(5.4, 4.9, "DNA ligase joins them", ha="left", fontsize=8.4,
                color=C["ligase"])
        # recombinant plasmid
        ax.add_patch(Circle((3.0, 3.0), 1.3, fc="none", ec=C["vector"],
                            lw=3.0, zorder=3))
        ax.add_patch(mpatches.Wedge((3.0, 3.0), 1.3, -25, 25, width=0.35,
                     fc=C["insert_dna"], ec="#e65100", lw=1.5, zorder=4))
        ax.text(3.0, 3.0, "Recombinant\nDNA", ha="center", va="center",
                fontsize=8, color=C["vector"], fontweight="bold")
        _fwd_arrow(ax, (4.4, 3.0), (5.6, 3.0), C["cycle_arrow"], lw=2.4)
        ax.add_patch(mpatches.FancyBboxPatch((6.0, 2.0), 3.4, 2.0,
                     boxstyle="round,pad=0.05", fc=C["host_cell"],
                     ec="#2e7d32", lw=2.0, zorder=3))
        ax.text(7.7, 3.4, "Transformation", ha="center", fontsize=8.8,
                fontweight="bold", color="#1b5e20")
        ax.text(7.7, 2.7, "into host (E. coli)\nfor cloning & expression",
                ha="center", fontsize=8, color="#37474f")
        note = ("Recombinant DNA — vector and target gene are cut with the "
                "same restriction enzyme, joined by DNA ligase, and the "
                "recombinant plasmid is transformed into a host cell.")

    elif proc == "dna_fingerprinting":
        steps = [("1. Extract DNA", "from blood / tissue", C["vector"]),
                 ("2. Cut with\nrestriction enzyme", "at VNTR sites",
                  C["restr_enzyme"]),
                 ("3. Gel\nelectrophoresis", "separate by size",
                  C["pcr_anneal"]),
                 ("4. Southern\nblotting", "transfer to membrane",
                  C["ligase"]),
                 ("5. Probe +\nautoradiograph", "banding pattern",
                  C["pcr_extend"])]
        for i, (name, body, col) in enumerate(steps):
            x = 1.5 + i * 2.35
            _stage_box(ax, x, 5.2, 2.1, 1.7, name, col, body)
            if i < len(steps) - 1:
                ax.add_patch(FancyArrowPatch((x + 1.05, 5.2), (x + 1.3, 5.2),
                             arrowstyle="-|>", mutation_scale=14, lw=2.0,
                             color=C["cycle_arrow"], zorder=2))
        # the resulting fingerprint (VNTR bands)
        rng = np.random.RandomState(21)
        for lane, lx in enumerate((3.0, 5.0, 7.0, 9.0)):
            ax.add_patch(Rectangle((lx - 0.4, 1.2), 0.8, 2.2, fc="#eceff1",
                         ec="#90a4ae", lw=1.0, zorder=2))
            for _ in range(rng.randint(3, 6)):
                yb = 1.4 + rng.uniform(0, 1.9)
                ax.add_patch(Rectangle((lx - 0.36, yb), 0.72, 0.10,
                             fc="#263238", ec="none", zorder=3))
            ax.text(lx, 1.0, f"Ind {lane + 1}", ha="center", fontsize=7.5,
                    color="#455a64")
        ax.text(6.0, 3.7, "DNA fingerprint — each individual's VNTR band "
                "pattern is unique (except identical twins)", ha="center",
                fontsize=8.4, color="#37474f", style="italic")
        note = ("DNA fingerprinting compares VNTR (repeat) regions: DNA is cut, "
                "size-separated, blotted and probed to reveal a band pattern "
                "unique to each person.")

    else:  # gel_to_blot
        ax.add_patch(Rectangle((1.0, 4.0), 3.0, 3.0, fc=C["gel_bg"],
                     ec="#263238", lw=1.8, zorder=2))
        for yb in np.linspace(4.4, 6.4, 5):
            ax.add_patch(Rectangle((1.4, yb), 2.2, 0.12, fc=C["gel_band"],
                         ec="none", zorder=3))
        ax.text(2.5, 7.3, "Agarose gel\n(separated fragments)", ha="center",
                fontsize=8.6, color="white", fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.2", fc=C["gel_bg"], ec="none"))
        _fwd_arrow(ax, (4.3, 5.5), (6.0, 5.5), C["cycle_arrow"], lw=2.6)
        ax.text(5.15, 6.0, "capillary\ntransfer", ha="center", fontsize=8,
                color="#455a64")
        # stack: gel → membrane → blotting paper
        for i, (name, col) in enumerate([("Weights", "#90a4ae"),
                                         ("Blotting paper", "#e0e0e0"),
                                         ("Nylon membrane", "#ffe0b2"),
                                         ("Gel", "#b0bec5"),
                                         ("Buffer wick", "#b3e5fc")]):
            y = 6.6 - i * 0.7
            ax.add_patch(Rectangle((6.4, y), 3.6, 0.55, fc=col, ec="#607d8b",
                         lw=1.2, zorder=3))
            ax.text(8.2, y + 0.27, name, ha="center", va="center", fontsize=7.8,
                    color="#263238", zorder=4)
        ax.text(8.2, 2.6, "Southern blot — DNA fragments transfer\nfrom the gel "
                "onto the membrane, preserving\ntheir positions", ha="center",
                fontsize=8.2, color="#37474f", style="italic")
        note = ("Southern blotting transfers size-separated DNA from a fragile "
                "gel onto a durable membrane (by capillary action), ready for "
                "probe hybridisation.")

    ax.set_title(schema.title or
                 f"Biotechnology Workflow — {proc.replace('_', ' ').title()}",
                 fontsize=14, fontweight="bold", pad=6)
    fig.text(0.5, 0.02, _wrap(note, 112), ha="center", fontsize=8.8,
             color="#37474f", style="italic")
    fig.tight_layout(pad=0.4, rect=(0, 0.05, 1, 1))
    return _fig_to_svg(fig)


# ═══════════════════════════════════════════════════════════════════════════════
# Labeled schematic — the config-defined "template layer"
# ═══════════════════════════════════════════════════════════════════════════════
# One renderer drives an open-ended family of "label the parts" biology diagrams. The
# artwork is DATA: primitive shapes + leader-line labels on a 0–100 grid, either inline in
# the schema or pulled from a named entry in diagrams/service/biology/templates.py. Adding a
# new labelled diagram is a new dict there, not a new Python renderer — that is the whole
# point of this layer.


def _grid_y(v: float) -> float:
    """Grid uses a top-left origin (author-friendly); matplotlib uses bottom-left."""
    return 100.0 - float(v)


def _schematic_path(d: str):
    """Parse a minimal 'M x y L x y ... Z' path on the grid into a matplotlib Path."""
    tokens = d.replace(",", " ").split()
    verts, codes, i = [], [], 0
    while i < len(tokens):
        cmd = tokens[i].upper()
        if cmd in ("M", "L"):
            x, y = float(tokens[i + 1]), float(tokens[i + 2])
            verts.append((x, _grid_y(y)))
            codes.append(Path.MOVETO if cmd == "M" else Path.LINETO)
            i += 3
        elif cmd == "Z":
            verts.append((0.0, 0.0))
            codes.append(Path.CLOSEPOLY)
            i += 1
        else:
            i += 1   # skip anything we don't support rather than crash
    return Path(verts, codes) if verts else None


def _draw_shape(ax, s: Dict[str, Any]) -> None:
    kind = (s.get("kind") or "").lower()
    fill = s.get("fill", "#ffffff")
    stroke = s.get("stroke", "#333333")
    lw = float(s.get("stroke_width", 1.5) or 0)
    common = dict(facecolor=fill, edgecolor=stroke, linewidth=lw, zorder=2)
    if kind == "ellipse":
        ax.add_patch(Ellipse((s["cx"], _grid_y(s["cy"])),
                             2 * float(s.get("rx", 5)), 2 * float(s.get("ry", 5)), **common))
    elif kind == "circle":
        ax.add_patch(Circle((s["cx"], _grid_y(s["cy"])), float(s.get("r", 5)), **common))
    elif kind == "rect":
        x, y, w, h = float(s["x"]), float(s["y"]), float(s.get("w", 10)), float(s.get("h", 10))
        ax.add_patch(Rectangle((x, _grid_y(y + h)), w, h, **common))
    elif kind == "polygon":
        pts = [(float(px), _grid_y(py)) for px, py in (s.get("points") or [])]
        if pts:
            ax.add_patch(Polygon(pts, closed=True, **common))
    elif kind == "line":
        pts = [(float(px), _grid_y(py)) for px, py in (s.get("points") or [])]
        if len(pts) >= 2:
            xs, ys = zip(*pts)
            ax.plot(xs, ys, color=stroke, linewidth=lw or 1.5, zorder=2, solid_capstyle="round")
    elif kind == "path":
        p = _schematic_path(s.get("path") or "")
        if p is not None:
            ax.add_patch(PathPatch(p, **common))


def render_labeled_schematic(params: Dict[str, Any],
                             canvas_w: int = 800, canvas_h: int = 600) -> str:
    from diagrams.service.biology.templates import BIOLOGY_TEMPLATES

    template = (params.get("template") or "").strip()
    base: Dict[str, Any] = {}
    if template:
        base = BIOLOGY_TEMPLATES.get(template)
        if base is None:
            # Recorded as demand (unknown template) and repaired/flagged upstream.
            raise ValueError(
                f"Unknown labeled_schematic template: '{template}'. "
                f"Available: {sorted(BIOLOGY_TEMPLATES)}")

    # Template supplies the base artwork; inline shapes overlay it. Inline labels REPLACE the
    # template's labels (so a question can relabel or blank them); otherwise use the template's.
    shapes = list(base.get("shapes") or []) + list(params.get("shapes") or [])
    labels = params.get("labels") if params.get("labels") is not None else base.get("labels", [])
    title = params.get("title") or base.get("title", "")

    fig, ax = plt.subplots(figsize=(canvas_w / 100.0, canvas_h / 100.0))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.set_aspect("equal")
    ax.axis("off")

    for s in shapes:
        try:
            _draw_shape(ax, s)
        except Exception:
            # A single malformed shape must not sink the whole figure.
            continue

    for lb in labels or []:
        text = str(lb.get("text", ""))
        lx, ly = float(lb.get("x", 50)), _grid_y(lb.get("y", 50))
        target = lb.get("target")
        if target and len(target) == 2:
            ax.annotate(
                text, xy=(float(target[0]), _grid_y(target[1])), xytext=(lx, ly),
                fontsize=9.5, ha="center", va="center", zorder=4,
                bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="#90a4ae", lw=0.6),
                arrowprops=dict(arrowstyle="-", color="#607d8b", lw=0.9,
                                shrinkA=3, shrinkB=2),
            )
        else:
            ax.text(lx, ly, text, fontsize=9.5, ha="center", va="center", zorder=4,
                    bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="#90a4ae", lw=0.6))

    if title:
        ax.set_title(title, fontsize=14, fontweight="bold", pad=6)
    fig.tight_layout(pad=0.4)
    return _fig_to_svg(fig)


# ═══════════════════════════════════════════════════════════════════════════════
# Dispatcher
# ═══════════════════════════════════════════════════════════════════════════════

BIOLOGY_RENDERERS = {
    "labeled_schematic":    render_labeled_schematic,
    "cell_diagram":         render_cell_diagram,
    "dna_structure":        render_dna_structure,
    "cell_division":        render_cell_division,
    "heart_diagram":        render_heart_diagram,
    "nephron_diagram":      render_nephron_diagram,
    "neuron_diagram":       render_neuron_diagram,
    "food_web":             render_food_web,
    "food_chain":           render_food_chain,
    "ecological_pyramid":   render_ecological_pyramid,
    "punnett_square":       render_punnett_square,
    "pedigree_chart":       render_pedigree_chart,
    "flower_structure":     render_flower_structure,
    "eye_diagram":          render_eye_diagram,
    "digestive_system":     render_digestive_system,
    "respiratory_system":   render_respiratory_system,
    "plant_tissue":         render_plant_tissue,
    "organelle_detail":     render_organelle_detail,
    "metabolic_cycle":      render_metabolic_cycle,
    "gel_electrophoresis":  render_gel_electrophoresis,
    "plasmid_map":          render_plasmid_map,
    "brain_diagram":        render_brain_diagram,
    "reproductive_system":  render_reproductive_system,
    "gametogenesis":        render_gametogenesis,
    "embryo_sac":           render_embryo_sac,
    "anther_ts":            render_anther_ts,
    "sarcomere":            render_sarcomere,
    "population_growth":    render_population_growth,
    "lac_operon":           render_lac_operon,
    "microbe_structure":    render_microbe_structure,
    "stomata":              render_stomata,
    "kranz_anatomy":        render_kranz_anatomy,
    "ear_diagram":          render_ear_diagram,
    "endocrine_system":     render_endocrine_system,
    # ── Wave 3 ────────────────────────────────────────────────────────────────
    "action_potential":            render_action_potential,
    "synapse":                     render_synapse,
    "reflex_arc":                  render_reflex_arc,
    "transcription_translation":   render_transcription_translation,
    "oxygen_dissociation_curve":   render_oxygen_dissociation_curve,
    "circulatory_system":          render_circulatory_system,
    "menstrual_cycle":             render_menstrual_cycle,
    "embryo_development":          render_embryo_development,
    "seed_structure":              render_seed_structure,
    "floral_diagram":              render_floral_diagram,
    "plant_morphology":            render_plant_morphology,
    "plant_life_cycle":            render_plant_life_cycle,
    "photosynthesis_zscheme":      render_photosynthesis_zscheme,
    "electron_transport_chain":    render_electron_transport_chain,
    "chromosome_structure":        render_chromosome_structure,
    "animal_tissue":               render_animal_tissue,
    "animal_anatomy":              render_animal_anatomy,
    "immune_response":             render_immune_response,
    "ecological_succession":       render_ecological_succession,
    "biotech_workflow":            render_biotech_workflow,
}


def render_biology(subtype: str, params: Dict[str, Any],
                   canvas_w: int = 800, canvas_h: int = 600) -> str:
    renderer = BIOLOGY_RENDERERS.get(subtype)
    if not renderer:
        raise ValueError(
            f"Unknown biology subtype: '{subtype}'. "
            f"Supported: {list(BIOLOGY_RENDERERS.keys())}"
        )
    return renderer(params, canvas_w=canvas_w, canvas_h=canvas_h)
