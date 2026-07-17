"""
Unit tests for the THIRD wave of extended Biology renderers — the NEET units
that were still uncovered (neurophysiology, human physiology, reproduction,
botany, molecular biology, cytology, tissues, animal anatomy, immunology,
ecology and biotechnology).

Covers all twenty wave-3 subtypes:
    action_potential, synapse, reflex_arc, transcription_translation,    (batch 1)
    oxygen_dissociation_curve, circulatory_system, menstrual_cycle,
        embryo_development,                                              (batch 2)
    seed_structure, floral_diagram, plant_morphology, plant_life_cycle,  (batch 3)
    photosynthesis_zscheme, electron_transport_chain, chromosome_structure,
        animal_tissue,                                                   (batch 4)
    animal_anatomy, immune_response, ecological_succession,
        biotech_workflow.                                                (batch 5)

Every renderer is a pure function of its params and never touches the database,
so SimpleTestCase is enough. Assertions are on COMPUTED FACTS (a membrane
voltage, a p50 ordering, a ploidy label, a centromere position) rather than on
raw SVG bytes — a diagram that is merely valid SVG can still teach the biology
backwards. Each test's docstring says what breaks if it fails.
"""
from django.test import SimpleTestCase

# Glyphs cairosvg (the print rasteriser) renders as tofu boxes. They must NEVER
# appear inside an SVG <text> node — arrows are drawn as patches instead.
_FORBIDDEN_GLYPHS = ["→", "⇒", "✗", "⟂", "↔",
                     "←", "⇐", "⇔", "↘", "↗",
                     "↙", "↖", "⇄", "↕"]


def _is_valid_svg(content: str) -> bool:
    return bool(content and "<svg" in content and "</svg>" in content)


def _svg_text_nodes(svg: str):
    """The rendered text nodes of the SVG. matplotlib silently DROPS text drawn
    outside the axes, so asserting on rendered text is the only way to catch a
    label that has fallen off the canvas."""
    import re
    return re.findall(r">([^<>]*)<", svg)


def _svg_text(svg: str) -> str:
    return " ".join(_svg_text_nodes(svg))


class _Base(SimpleTestCase):
    def _render(self, subtype, params):
        from diagrams.service.biology.renderer import render_biology
        return render_biology(subtype, params)

    def _assert_labels(self, svg, *labels):
        self.assertTrue(_is_valid_svg(svg))
        text = _svg_text(svg)
        for label in labels:
            self.assertIn(label, text, f"label '{label}' missing from the SVG")

    def _assert_no_tofu(self, svg):
        for node in _svg_text_nodes(svg):
            for g in _FORBIDDEN_GLYPHS:
                self.assertNotIn(
                    g, node,
                    f"forbidden glyph {g!r} reached a text node: {node!r}")


# ══════════════════════════════════════════════════════════════════════════════
# Batch 1 — cell / molecular neurobiology
# ══════════════════════════════════════════════════════════════════════════════

class TestActionPotential(_Base):
    def test_trace_hits_the_four_landmark_voltages(self):
        """The trace must REST at −70, cross the −55 threshold, PEAK near +30 and
        RETURN to rest. If any landmark is missing the diagram no longer teaches
        the standard NEET action-potential trace."""
        from diagrams.service.biology.renderer import _action_potential_trace
        t, V = _action_potential_trace(-70.0, -55.0, 30.0)
        self.assertAlmostEqual(V[0], -70.0, places=3)          # starts at rest
        self.assertAlmostEqual(V[-1], -70.0, places=1)         # returns to rest
        self.assertGreaterEqual(V.max(), 28.0)                 # peaks near +30
        self.assertLessEqual(V.max(), 32.0)
        # crosses the threshold on the way up
        self.assertTrue((V >= -55.0).any() and (V <= -55.0).any())
        # hyperpolarises BELOW the resting potential before recovering
        self.assertLess(V.min(), -70.0)

    def test_renders_phases_and_channels(self):
        svg = self._render("action_potential", {})
        self._assert_labels(svg, "Depolarisation", "Repolarisation",
                            "Threshold", "Resting potential")
        self._assert_no_tofu(svg)


class TestSynapse(_Base):
    def test_chemical_synapse_parts(self):
        """A chemical synapse needs the pre-synaptic knob, vesicles, cleft,
        neurotransmitter, receptors and the Ca²⁺ trigger. A missing cleft or
        receptor breaks the 'how does an impulse cross a synapse?' question."""
        svg = self._render("synapse", {})
        self._assert_labels(svg, "Axon terminal", "Synaptic vesicles",
                            "Synaptic cleft", "Neurotransmitter",
                            "Receptor proteins", "Post-synaptic membrane")
        self.assertIn("Ca²⁺ influx", _svg_text(svg))
        self._assert_no_tofu(svg)


class TestReflexArc(_Base):
    def test_monosynaptic_has_no_interneuron(self):
        """A monosynaptic arc (knee-jerk) has the sensory neuron synapsing
        DIRECTLY on the motor neuron; only the polysynaptic arc adds a relay
        interneuron. Getting this wrong misclassifies the reflex."""
        mono = self._render("reflex_arc", {"reflex_type": "monosynaptic"})
        poly = self._render("reflex_arc", {"reflex_type": "polysynaptic"})
        self.assertNotIn("Relay interneuron", _svg_text(mono))
        self.assertIn("Relay interneuron", _svg_text(poly))
        for svg in (mono, poly):
            self._assert_labels(svg, "Spinal cord", "Dorsal root ganglion",
                                "Receptor", "Effector muscle")
            self._assert_no_tofu(svg)


class TestTranscriptionTranslation(_Base):
    def test_transcription_names_polymerase_and_strands(self):
        """Transcription reads the TEMPLATE strand and needs RNA polymerase and
        the mRNA product. Losing the template-strand label breaks the
        'which strand is copied?' question."""
        svg = self._render("transcription_translation",
                           {"stage": "transcription"})
        self._assert_labels(svg, "RNA", "Template (antisense) strand",
                            "mRNA transcript")
        self._assert_no_tofu(svg)

    def test_translation_shows_codon_anticodon_and_ribosome(self):
        """Translation needs the ribosome, tRNA anti-codon and the growing
        polypeptide. The codon/anti-codon pairing is the whole point."""
        svg = self._render("transcription_translation",
                           {"stage": "translation"})
        self._assert_labels(svg, "Ribosome", "tRNA (anti-codon)", "Amino acid",
                            "Polypeptide (protein)")
        self._assert_no_tofu(svg)

    def test_both_stages_render(self):
        svg = self._render("transcription_translation", {"stage": "both"})
        self.assertTrue(_is_valid_svg(svg))
        self._assert_no_tofu(svg)


# ══════════════════════════════════════════════════════════════════════════════
# Batch 2 — physiology
# ══════════════════════════════════════════════════════════════════════════════

class TestOxygenDissociationCurve(_Base):
    def test_curve_is_sigmoid_and_passes_through_p50(self):
        """Haemoglobin binds O₂ CO-OPERATIVELY, so the curve is sigmoid (n>1)
        and reaches 50 % saturation exactly at its p50. A hyperbola here would
        deny co-operativity."""
        from diagrams.service.biology.renderer import (_hb_saturation,
                                                       _ODC_CURVES)
        p50 = _ODC_CURVES["normal"]["p50"]
        n = _ODC_CURVES["normal"]["n"]
        self.assertGreater(n, 1.0)                             # co-operative
        self.assertAlmostEqual(_hb_saturation(p50, p50, n), 50.0, places=3)
        # sigmoid: the low-pO₂ region is CONVEX (slope accelerates), so the
        # gradient at 0.5*p50 is smaller than the gradient at p50.
        eps = 0.5
        g_low = _hb_saturation(0.5 * p50 + eps, p50, n) - \
            _hb_saturation(0.5 * p50 - eps, p50, n)
        g_mid = _hb_saturation(p50 + eps, p50, n) - \
            _hb_saturation(p50 - eps, p50, n)
        self.assertGreater(g_mid, g_low)
        # monotonically increasing
        self.assertLess(_hb_saturation(10, p50, n),
                        _hb_saturation(60, p50, n))

    def test_bohr_shift_moves_the_curve_to_the_right(self):
        """The Bohr effect shifts the curve RIGHT — a HIGHER p50 — so at any
        given pO₂ the saturation is LOWER (O₂ unloaded to tissues). If the
        shifted p50 were smaller the diagram would teach the effect backwards."""
        from diagrams.service.biology.renderer import (_hb_saturation,
                                                       _ODC_CURVES)
        normal = _ODC_CURVES["normal"]
        right = _ODC_CURVES["bohr_right"]
        self.assertGreater(right["p50"], normal["p50"])
        # at a fixed pO₂ the right-shifted Hb is less saturated
        po2 = 40.0
        self.assertLess(_hb_saturation(po2, right["p50"], right["n"]),
                        _hb_saturation(po2, normal["p50"], normal["n"]))

    def test_all_curve_variants_render(self):
        svg = self._render("oxygen_dissociation_curve",
                           {"curves": ["myoglobin", "bohr_left", "normal",
                                       "bohr_right"]})
        self._assert_labels(svg, "Normal Hb", "Myoglobin")
        self._assert_no_tofu(svg)


class TestCirculatorySystem(_Base):
    def test_double_circulation_labels_both_circuits(self):
        """Double circulation needs the pulmonary and systemic circuits and the
        four heart chambers. The pulmonary ARTERY carrying DEOXYGENATED blood is
        the classic trap."""
        svg = self._render("circulatory_system", {})
        self._assert_labels(svg, "atrium", "ventricle", "LUNGS",
                            "BODY TISSUES", "Pulmonary artery", "Pulmonary vein",
                            "Oxygenated blood", "Deoxygenated blood")
        self._assert_no_tofu(svg)

    def test_highlight_circuit_variants(self):
        for circuit in ("pulmonary", "systemic"):
            svg = self._render("circulatory_system",
                               {"highlight_circuit": circuit})
            self.assertTrue(_is_valid_svg(svg))
            self._assert_no_tofu(svg)


class TestMenstrualCycle(_Base):
    def test_hormones_ovarian_and_uterine_panels(self):
        """The cycle question is the ALIGNMENT: the LH surge, ovulation and the
        thickened endometrium must all sit at ~mid-cycle on one axis."""
        svg = self._render("menstrual_cycle", {})
        self._assert_labels(svg, "FSH", "LH", "Oestrogen", "Progesterone",
                            "Follicular phase", "Ovulation", "Luteal phase")
        self.assertIn("LH surge", _svg_text(svg))
        self._assert_no_tofu(svg)


class TestEmbryoDevelopment(_Base):
    def test_all_stages_in_order(self):
        """Development runs zygote → cleavage → morula → blastocyst → gastrula.
        The blastocyst's inner cell mass + trophoblast and the gastrula's three
        germ layers are the named parts."""
        svg = self._render("embryo_development", {"stage": "all"})
        self._assert_labels(svg, "Zygote (2n)", "Cleavage", "Morula",
                            "Blastocyst", "Inner cell mass",
                            "Trophoblast", "Ectoderm", "Mesoderm", "Endoderm")
        self._assert_no_tofu(svg)

    def test_placenta_view(self):
        svg = self._render("embryo_development", {"stage": "placenta"})
        self._assert_labels(svg, "Chorionic villi", "Umbilical cord")
        self._assert_no_tofu(svg)


# ══════════════════════════════════════════════════════════════════════════════
# Batch 3 — botany
# ══════════════════════════════════════════════════════════════════════════════

class TestSeedStructure(_Base):
    def test_dicot_has_two_cotyledons_no_endosperm(self):
        """A dicot bean is NON-endospermic with two food-storing cotyledons,
        plumule, radicle, hilum and micropyle."""
        svg = self._render("seed_structure", {"seed_type": "dicot"})
        self._assert_labels(svg, "Testa (seed coat)", "Cotyledon (2)",
                            "Plumule", "Radicle", "Hilum", "Micropyle")
        self._assert_no_tofu(svg)

    def test_monocot_is_endospermic_with_scutellum(self):
        """A monocot maize grain is ENDOSPERMIC; its single cotyledon
        (scutellum) plus coleoptile and coleorhiza distinguish it from a dicot."""
        svg = self._render("seed_structure", {"seed_type": "monocot"})
        self._assert_labels(svg, "Endosperm", "Scutellum", "Coleoptile",
                            "Coleorhiza", "Aleurone layer")
        self._assert_no_tofu(svg)

    def test_germination_variants(self):
        for kind in ("epigeal", "hypogeal"):
            svg = self._render("seed_structure",
                               {"seed_type": "dicot", "show_germination": kind})
            self.assertTrue(_is_valid_svg(svg))
            self._assert_no_tofu(svg)


class TestFloralDiagram(_Base):
    def test_family_formulae_match_the_whorl_counts(self):
        """The floral formula MUST be built from the same whorl-count table the
        diagram draws — a K(5) label over four sepals would be self-
        contradicting. Solanaceae is bicarpellary syncarpous G(2)."""
        from diagrams.service.biology.renderer import _FLORAL_FAMILIES
        sol = _FLORAL_FAMILIES["solanaceae"]
        self.assertEqual(sol["calyx"], 5)
        self.assertEqual(sol["corolla"], 5)
        self.assertEqual(sol["gynoecium"], 2)
        svg = self._render("floral_diagram", {"family": "solanaceae"})
        self.assertIn("K(5)", _svg_text(svg))
        self.assertIn("G(2)", _svg_text(svg))
        self._assert_no_tofu(svg)

    def test_all_families_render(self):
        for fam in ("solanaceae", "fabaceae", "liliaceae"):
            svg = self._render("floral_diagram", {"family": fam})
            self.assertTrue(_is_valid_svg(svg))
            self._assert_no_tofu(svg)


class TestPlantMorphology(_Base):
    def test_every_feature_and_variant_renders_with_no_tofu(self):
        """Each morphology feature must render its chosen variant cleanly; a
        dropped label would leave the schematic unnamed."""
        cases = {
            "venation": ("reticulate", "parallel"),
            "phyllotaxy": ("alternate", "opposite", "whorled"),
            "inflorescence": ("racemose", "cymose"),
            "root_system": ("tap", "fibrous"),
            "fruit_type": (None,),
        }
        for feature, variants in cases.items():
            for v in variants:
                params = {"feature": feature}
                if v:
                    params["variant"] = v
                svg = self._render("plant_morphology", params)
                self.assertTrue(_is_valid_svg(svg), f"{feature}/{v}")
                self._assert_no_tofu(svg)

    def test_venation_types_named(self):
        ret = self._render("plant_morphology",
                           {"feature": "venation", "variant": "reticulate"})
        par = self._render("plant_morphology",
                           {"feature": "venation", "variant": "parallel"})
        self.assertIn("Reticulate", _svg_text(ret))
        self.assertIn("Parallel", _svg_text(par))


class TestPlantLifeCycle(_Base):
    def test_sporophyte_is_2n_gametophyte_is_n(self):
        """Alternation of generations turns on PLOIDY: the sporophyte is 2n and
        the gametophyte is n. If a label flips, the 'state the ploidy' question
        is answered wrong."""
        from diagrams.service.biology.renderer import _LIFE_CYCLE_STAGES
        by_name = {s["name"]: s for s in _LIFE_CYCLE_STAGES}
        self.assertEqual(by_name["Sporophyte"]["ploidy"], 2)
        self.assertEqual(by_name["Gametophyte"]["ploidy"], 1)
        self.assertEqual(by_name["Spores"]["ploidy"], 1)
        self.assertEqual(by_name["Zygote"]["ploidy"], 2)

    def test_meiosis_reduces_2n_to_n_at_the_spore_step(self):
        """Meiosis is the 2n → n step (sporophyte makes spores); fertilisation
        is the n → 2n step (gametes make the zygote). A meiosis label on the
        wrong arrow denies the reduction division."""
        from diagrams.service.biology.renderer import _LIFE_CYCLE_STAGES
        stages = _LIFE_CYCLE_STAGES
        idx = {s["name"]: i for i, s in enumerate(stages)}
        spore = stages[idx["Spores"]]
        zygote = stages[idx["Zygote"]]
        self.assertEqual(spore.get("via"), "MEIOSIS")
        self.assertEqual(zygote.get("via"), "FERTILISATION")
        # the stage entering MEIOSIS is diploid, the one it produces is haploid
        before_meiosis = stages[idx["Spores"] - 1]
        self.assertEqual(before_meiosis["ploidy"], 2)
        self.assertEqual(spore["ploidy"], 1)
        # fertilisation restores diploidy
        before_fert = stages[idx["Zygote"] - 1]
        self.assertEqual(before_fert["ploidy"], 1)
        self.assertEqual(zygote["ploidy"], 2)

    def test_all_groups_render_with_ploidy_badges(self):
        for grp in ("bryophyte", "pteridophyte", "angiosperm"):
            svg = self._render("plant_life_cycle", {"group": grp})
            text = _svg_text(svg)
            self.assertIn("2n", text)
            self.assertIn("MEIOSIS", text)
            self.assertIn("FERTILISATION", text)
            self._assert_no_tofu(svg)


# ══════════════════════════════════════════════════════════════════════════════
# Batch 4 — molecular / cytology / tissues
# ══════════════════════════════════════════════════════════════════════════════

class TestPhotosynthesisZScheme(_Base):
    def test_zscheme_names_both_photosystems_and_products(self):
        """The Z-scheme needs both photosystems (P680/PSII and P700/PSI), water
        splitting and NADPH. Losing a photosystem breaks the 'two photon jumps'
        story."""
        svg = self._render("photosynthesis_zscheme", {})
        text = _svg_text(svg)
        self.assertIn("P680", text)
        self.assertIn("P700", text)
        self.assertIn("NADPH", text)
        self.assertIn("Ferredoxin", text)
        self._assert_no_tofu(svg)


class TestElectronTransportChain(_Base):
    def test_etc_has_four_complexes_and_atp_synthase(self):
        """Oxidative phosphorylation needs complexes I–IV, the proton gradient
        and ATP synthase. Without ATP synthase there is no chemiosmosis."""
        svg = self._render("electron_transport_chain", {})
        text = _svg_text(svg)
        for rn in ("I", "II", "III", "IV", "V"):
            self.assertIn(rn, text)
        self.assertIn("ATP synthase", text)
        self.assertIn("MATRIX (low H⁺)", text)
        self._assert_no_tofu(svg)

    def test_without_atp_synthase_flag_it_is_dropped(self):
        svg = self._render("electron_transport_chain",
                           {"show_atp_synthase": False,
                            "show_proton_gradient": False})
        # the drawn complex-V reaction label is gone (the caption still names it)
        self.assertNotIn("ADP + Pi gives ATP", _svg_text(svg))
        self._assert_no_tofu(svg)


class TestChromosomeStructure(_Base):
    def test_centromere_classified_by_position(self):
        """The karyotype classes ARE the centromere position: metacentric =
        central (0.5), telocentric = terminal. If the ordering breaks, a
        submetacentric could be called metacentric."""
        from diagrams.service.biology.renderer import _CENTROMERE_POS
        self.assertAlmostEqual(_CENTROMERE_POS["metacentric"], 0.5, delta=0.02)
        # position drifts monotonically toward the tip
        self.assertGreater(_CENTROMERE_POS["metacentric"],
                           _CENTROMERE_POS["submetacentric"])
        self.assertGreater(_CENTROMERE_POS["submetacentric"],
                           _CENTROMERE_POS["acrocentric"])
        self.assertGreater(_CENTROMERE_POS["acrocentric"],
                           _CENTROMERE_POS["telocentric"])
        self.assertLess(_CENTROMERE_POS["telocentric"], 0.1)   # at the tip

    def test_single_views_label_arms_and_centromere(self):
        for ct in ("metacentric", "submetacentric", "acrocentric",
                   "telocentric"):
            svg = self._render("chromosome_structure",
                               {"view": "single", "centromere": ct})
            self._assert_labels(svg, "Centromere", "Sister chromatids")
            self._assert_no_tofu(svg)

    def test_karyotype_and_sex_determination_views(self):
        karyo = self._render("chromosome_structure", {"view": "karyotype"})
        self.assertIn("23 pairs", _svg_text(karyo))
        sex = self._render("chromosome_structure",
                           {"view": "sex_determination"})
        text = _svg_text(sex)
        self.assertIn("XX", text)
        self.assertIn("XY", text)
        self._assert_no_tofu(karyo)
        self._assert_no_tofu(sex)


class TestAnimalTissue(_Base):
    def test_every_tissue_variant_renders_named(self):
        """All 13 tissue variants across the four groups must render cleanly;
        a dropped label leaves the tissue unidentifiable."""
        from diagrams.service.biology.renderer import _TISSUE_GROUP
        tissues = ("squamous", "cuboidal", "columnar", "ciliated",
                   "areolar", "adipose", "bone", "cartilage", "blood",
                   "striated", "smooth", "cardiac", "nervous")
        for t in tissues:
            svg = self._render("animal_tissue", {"tissue": t})
            self.assertTrue(_is_valid_svg(svg), t)
            group = _TISSUE_GROUP[t].capitalize()
            self.assertIn(group, _svg_text(svg))
            self._assert_no_tofu(svg)

    def test_bone_shows_haversian_system(self):
        svg = self._render("animal_tissue", {"tissue": "bone"})
        self._assert_labels(svg, "Haversian canal", "Lamellae",
                            "Lacuna (osteocyte)")


# ══════════════════════════════════════════════════════════════════════════════
# Batch 5 — anatomy / immunology / ecology / biotech
# ══════════════════════════════════════════════════════════════════════════════

class TestAnimalAnatomy(_Base):
    def test_every_organism_system_combination_renders(self):
        """All 12 organism/system schematics must render with their parts named
        in order — these are whole NEET units ('trace the earthworm gut')."""
        from diagrams.service.biology.renderer import _ANIMAL_ANATOMY
        for org, systems in _ANIMAL_ANATOMY.items():
            for sysname in systems:
                svg = self._render("animal_anatomy",
                                   {"organism": org, "system": sysname})
                self.assertTrue(_is_valid_svg(svg), f"{org}/{sysname}")
                self._assert_no_tofu(svg)

    def test_earthworm_digestive_order(self):
        svg = self._render("animal_anatomy",
                           {"organism": "earthworm", "system": "digestive"})
        self._assert_labels(svg, "Mouth", "Pharynx", "Gizzard", "Anus")


class TestImmuneResponse(_Base):
    def test_antibody_structure_parts(self):
        """An antibody is Y-shaped with 2 heavy + 2 light chains, variable and
        constant regions and two antigen-binding sites. A missing binding site
        denies its specificity."""
        svg = self._render("immune_response",
                           {"view": "antibody_structure"})
        self._assert_labels(svg, "Heavy chain", "Light chain",
                            "Variable region (V)", "Constant region (C)",
                            "Antigen-binding site")
        self._assert_no_tofu(svg)

    def test_secondary_response_is_larger_than_primary(self):
        """The secondary response must be FASTER and reach a HIGHER antibody
        titre than the primary — the basis of immunological memory. A smaller
        secondary peak would teach the opposite."""
        import re
        svg = self._render("immune_response", {"view": "response_curve"})
        self._assert_labels(svg, "Primary response (1st exposure)",
                            "Secondary response (2nd exposure)")
        self.assertIn("Secondary response is FASTER", _svg_text(svg))
        self._assert_no_tofu(svg)

    def test_secondary_peak_exceeds_primary_peak(self):
        """Cross-check the computed magnitudes: the secondary antibody peak is
        larger than the primary peak."""
        from diagrams.service.biology.renderer import _gauss
        import numpy as np
        t = np.linspace(0, 60, 600)
        primary = _gauss(t, 16, 6, 30)
        secondary = _gauss(t, 40, 5, 100)
        self.assertGreater(secondary.max(), primary.max())


class TestEcologicalSuccession(_Base):
    def test_primary_succession_pioneer_to_climax(self):
        """Primary succession starts on bare rock with lichens (pioneers) and
        ends at the forest climax. Dropping the pioneer or climax breaks the
        sequence question."""
        svg = self._render("ecological_succession",
                           {"view": "succession", "succession_type": "primary"})
        text = _svg_text(svg)
        self.assertIn("Bare rock", text)
        self.assertIn("pioneer", text)
        self.assertIn("climax", text)
        self._assert_no_tofu(svg)

    def test_age_pyramid_base_width_matches_type(self):
        """An expanding pyramid has a BROAD pre-reproductive base; a declining
        one a NARROW base. The base half-width must order expanding > stable >
        declining, else the pyramid teaches the wrong demographic trend."""
        from diagrams.service.biology.renderer import _AGE_PYRAMID_SHAPES
        base = {k: v[0] for k, v in _AGE_PYRAMID_SHAPES.items()}
        self.assertGreater(base["expanding"], base["stable"])
        self.assertGreater(base["stable"], base["declining"])
        # an expanding pyramid tapers upward (base wider than the apex band)
        self.assertGreater(_AGE_PYRAMID_SHAPES["expanding"][0],
                           _AGE_PYRAMID_SHAPES["expanding"][2])
        # a declining pyramid is urn-shaped: base narrower than the middle
        self.assertLess(_AGE_PYRAMID_SHAPES["declining"][0],
                        _AGE_PYRAMID_SHAPES["declining"][1])

    def test_age_pyramid_variants_render(self):
        for ptype in ("expanding", "stable", "declining"):
            svg = self._render("ecological_succession",
                               {"view": "age_pyramid", "pyramid_type": ptype})
            self._assert_labels(svg, "Pre-reproductive")
            self._assert_no_tofu(svg)


class TestBiotechWorkflow(_Base):
    def test_pcr_three_steps(self):
        """PCR is denaturation → annealing → extension, repeated. Missing a step
        breaks the 'name the PCR steps' question."""
        svg = self._render("biotech_workflow", {"process": "pcr"})
        self._assert_labels(svg, "Denaturation", "Annealing", "Extension")
        self._assert_no_tofu(svg)

    def test_all_processes_render(self):
        for proc in ("pcr", "recombinant_dna", "dna_fingerprinting",
                     "gel_to_blot"):
            svg = self._render("biotech_workflow", {"process": proc})
            self.assertTrue(_is_valid_svg(svg), proc)
            self._assert_no_tofu(svg)

    def test_recombinant_dna_uses_same_enzyme_and_ligase(self):
        svg = self._render("biotech_workflow", {"process": "recombinant_dna"})
        text = _svg_text(svg)
        self.assertIn("SAME restriction enzyme", text)
        self.assertIn("DNA ligase joins them", text)


# ══════════════════════════════════════════════════════════════════════════════
# Cross-cutting guarantees
# ══════════════════════════════════════════════════════════════════════════════

class TestWave3CrossCutting(_Base):
    _ALL = [
        ("action_potential", {}),
        ("synapse", {}),
        ("reflex_arc", {"reflex_type": "polysynaptic"}),
        ("transcription_translation", {"stage": "both"}),
        ("oxygen_dissociation_curve", {}),
        ("circulatory_system", {"highlight_circuit": "pulmonary"}),
        ("menstrual_cycle", {}),
        ("embryo_development", {"stage": "all"}),
        ("embryo_development", {"stage": "placenta"}),
        ("seed_structure", {"seed_type": "monocot"}),
        ("floral_diagram", {"family": "fabaceae"}),
        ("plant_morphology", {"feature": "inflorescence", "variant": "cymose"}),
        ("plant_life_cycle", {"group": "bryophyte"}),
        ("photosynthesis_zscheme", {}),
        ("electron_transport_chain", {}),
        ("chromosome_structure", {"view": "karyotype"}),
        ("chromosome_structure", {"view": "sex_determination"}),
        ("animal_tissue", {"tissue": "cardiac"}),
        ("animal_anatomy", {"organism": "cockroach", "system": "digestive"}),
        ("immune_response", {"view": "antibody_structure"}),
        ("immune_response", {"view": "response_curve"}),
        ("ecological_succession", {"view": "succession"}),
        ("ecological_succession", {"view": "age_pyramid",
                                   "pyramid_type": "declining"}),
        ("biotech_workflow", {"process": "pcr"}),
    ]

    def test_all_wave3_subtypes_registered(self):
        """The dispatcher is the only route the pipeline uses; an unregistered
        renderer is dead code no question can ever reach."""
        from diagrams.service.biology.renderer import BIOLOGY_RENDERERS
        for subtype in ("action_potential", "synapse", "reflex_arc",
                        "transcription_translation",
                        "oxygen_dissociation_curve", "circulatory_system",
                        "menstrual_cycle", "embryo_development",
                        "seed_structure", "floral_diagram",
                        "plant_morphology", "plant_life_cycle",
                        "photosynthesis_zscheme", "electron_transport_chain",
                        "chromosome_structure", "animal_tissue",
                        "animal_anatomy", "immune_response",
                        "ecological_succession", "biotech_workflow"):
            self.assertIn(subtype, BIOLOGY_RENDERERS)

    def test_no_rendered_svg_contains_a_tofu_glyph(self):
        """cairosvg renders → ⇒ ✗ ⟂ ↔ as tofu boxes in the printed paper; not
        one may reach a text node. Arrows are drawn as patches instead."""
        for subtype, params in self._ALL:
            svg = self._render(subtype, params)
            self._assert_no_tofu(svg)

    def test_wave3_renderers_are_deterministic(self):
        """Same params → byte-identical SVG. Papers are cached and re-printed; a
        diagram that changed between renders would break that."""
        for subtype, params in self._ALL:
            self.assertEqual(self._render(subtype, params),
                             self._render(subtype, params),
                             f"{subtype} is not deterministic")

    def test_invalid_enum_values_are_rejected(self):
        """A typo'd enum must fail loudly at validation rather than fall through
        to a silently wrong default diagram."""
        for subtype, params in (
            ("reflex_arc", {"reflex_type": "disynaptic"}),
            ("transcription_translation", {"stage": "replication"}),
            ("seed_structure", {"seed_type": "gymnosperm"}),
            ("floral_diagram", {"family": "poaceae"}),
            ("plant_morphology", {"feature": "trichome"}),
            ("plant_life_cycle", {"group": "algae"}),
            ("chromosome_structure", {"view": "banding"}),
            ("chromosome_structure", {"view": "single",
                                      "centromere": "holocentric"}),
            ("animal_tissue", {"tissue": "glandular"}),
            ("animal_anatomy", {"organism": "hydra", "system": "digestive"}),
            ("immune_response", {"view": "antigen_structure"}),
            ("ecological_succession", {"view": "climax"}),
            ("biotech_workflow", {"process": "crispr"}),
        ):
            with self.assertRaises(Exception, msg=f"{subtype} {params}"):
                self._render(subtype, params)
