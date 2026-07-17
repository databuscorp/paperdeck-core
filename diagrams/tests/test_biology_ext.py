"""
Unit tests for the extended Biology renderers (NEET anatomy, plant anatomy,
metabolic pathways and biotechnology diagrams).

SimpleTestCase — these renderers are pure functions over their params and never
touch the database.
"""
from django.test import SimpleTestCase


def _is_valid_svg(content: str) -> bool:
    """Basic SVG validity check."""
    return bool(content and "<svg" in content and "</svg>" in content)


def _svg_text(svg: str) -> str:
    """Text content of the SVG.

    matplotlib silently DROPS text drawn outside the axes limits, so a label can
    disappear without raising. Asserting on the rendered text is the only way to
    catch a label that has fallen off the canvas.
    """
    import re
    return " ".join(re.findall(r">([^<>]*)<", svg))


class TestBiologyExtendedRenderers(SimpleTestCase):
    def _render(self, subtype, params):
        from diagrams.service.biology.renderer import render_biology
        return render_biology(subtype, params)

    def _assert_labels(self, svg, *labels):
        self.assertTrue(_is_valid_svg(svg))
        text = _svg_text(svg)
        for label in labels:
            self.assertIn(label, text, f"label '{label}' missing from the SVG")

    # ── Flower structure ──────────────────────────────────────────────────────
    def test_flower_structure_typical(self):
        """Every whorl of a typical flower must be labelled. If this fails the
        diagram can no longer answer 'identify the labelled part' questions."""
        svg = self._render("flower_structure", {"flower_type": "typical"})
        self._assert_labels(svg, "Sepal", "Petal", "Anther", "Filament",
                            "Stigma", "Style", "Ovary", "Ovule",
                            "Receptacle", "Pedicel", "Carpel / Pistil")

    def test_flower_structure_hibiscus(self):
        """Hibiscus is asked precisely because its stamens are monadelphous and
        it carries an epicalyx. Losing those makes it a generic flower."""
        svg = self._render("flower_structure", {"flower_type": "hibiscus"})
        self._assert_labels(svg, "Epicalyx", "monadelphous", "Stigma", "Ovary")

    def test_flower_structure_no_half_section_hides_ovules(self):
        """Without the half-section the ovary is uncut, so no ovule may be
        claimed in the labels."""
        svg = self._render("flower_structure", {"show_half_section": False})
        self.assertTrue(_is_valid_svg(svg))
        self.assertNotIn("Ovule", _svg_text(svg))

    def test_flower_structure_highlight_and_no_labels(self):
        svg = self._render("flower_structure",
                           {"highlight_part": "ovary", "show_labels": True})
        self.assertTrue(_is_valid_svg(svg))
        self.assertTrue(_is_valid_svg(
            self._render("flower_structure", {"show_labels": False})))

    # ── Eye diagram ───────────────────────────────────────────────────────────
    def test_eye_diagram_all_coats_and_parts(self):
        """The three coats plus the refracting media. A mislabelled eye is the
        single most common NEET diagram question — it must carry every part."""
        svg = self._render("eye_diagram", {"show_labels": True})
        self._assert_labels(svg, "Cornea", "Aqueous humour", "Iris", "Pupil",
                            "Lens", "Ciliary body", "Vitreous humour", "Retina",
                            "Fovea centralis", "Blind spot", "Optic nerve",
                            "Sclera", "Choroid")

    def test_eye_diagram_myopia_focuses_in_front(self):
        """Myopia focuses SHORT of the retina. If the note or the focus flips,
        the diagram teaches the defect backwards."""
        svg = self._render("eye_diagram", {"defect": "myopia"})
        self._assert_labels(svg, "IN FRONT of the retina", "concave")

        from diagrams.service.biology.renderer import _EYE_FOCUS
        self.assertLess(_EYE_FOCUS["myopia"], _EYE_FOCUS["none"])

    def test_eye_diagram_hypermetropia_focuses_behind(self):
        """Hypermetropia focuses BEYOND the retina — the mirror image of myopia."""
        svg = self._render("eye_diagram", {"defect": "hypermetropia"})
        self._assert_labels(svg, "BEHIND the", "convex")

        from diagrams.service.biology.renderer import _EYE_FOCUS
        self.assertGreater(_EYE_FOCUS["hypermetropia"], _EYE_FOCUS["none"])

    def test_eye_diagram_normal_focus_lands_on_the_retina(self):
        """The emmetropic eye focuses ON the retina, so the focus must coincide
        with the retinal surface on the optic axis."""
        from diagrams.service.biology.renderer import (
            _EYE_FOCUS, _EYE_C, _R_RETINA,
        )
        self.assertAlmostEqual(_EYE_FOCUS["none"], _EYE_C[0] + _R_RETINA,
                               places=2)
        self.assertTrue(_is_valid_svg(self._render("eye_diagram",
                                                   {"defect": "none"})))

    def test_eye_diagram_without_rays(self):
        svg = self._render("eye_diagram",
                           {"show_light_rays": False, "highlight_part": "retina"})
        self._assert_labels(svg, "Retina")

    # ── Digestive system ──────────────────────────────────────────────────────
    def test_digestive_system_full_alimentary_canal(self):
        """The whole canal plus the associated glands. A missing region breaks
        'trace the path of food' questions."""
        svg = self._render("digestive_system", {"show_labels": True})
        self._assert_labels(svg, "Mouth", "Oesophagus", "Stomach", "Liver",
                            "Gall bladder", "Pancreas", "Duodenum", "Jejunum",
                            "Ileum", "Caecum", "Rectum", "Anus", "appendix",
                            "Ascending colon", "Transverse colon",
                            "Descending colon", "Small intestine")

    def test_digestive_system_highlight_and_no_labels(self):
        self.assertTrue(_is_valid_svg(
            self._render("digestive_system", {"highlight_organ": "stomach"})))
        self.assertTrue(_is_valid_svg(
            self._render("digestive_system", {"show_labels": False})))

    # ── Respiratory system ────────────────────────────────────────────────────
    def test_respiratory_system_full_tract(self):
        """Nose → alveoli, plus the pleura and diaphragm."""
        svg = self._render("respiratory_system", {"show_labels": True})
        self._assert_labels(svg, "Nasal cavity", "Pharynx", "Larynx", "Trachea",
                            "Bronchus", "Bronchiole", "Alveoli", "Diaphragm",
                            "Pleura", "Right lung", "Left lung")

    def test_respiratory_system_alveoli_inset_shows_gas_exchange(self):
        """The inset exists to show the direction of diffusion: O₂ into the
        blood, CO₂ out of it. Without both arrows the inset is decoration."""
        svg = self._render("respiratory_system", {"show_alveoli_inset": True})
        self._assert_labels(svg, "Alveolus (magnified)", "O₂ → blood",
                            "CO₂ → alveolus", "Pulmonary capillary")

    def test_respiratory_system_without_inset(self):
        svg = self._render("respiratory_system",
                           {"show_alveoli_inset": False,
                            "highlight_organ": "diaphragm"})
        self.assertTrue(_is_valid_svg(svg))
        self.assertNotIn("Alveolus (magnified)", _svg_text(svg))

    # ── Plant tissue ──────────────────────────────────────────────────────────
    def test_plant_tissue_dicot_stem_is_an_open_ring(self):
        """Dicot stem = bundles in a RING, conjoint/collateral/OPEN, so a
        cambium MUST be drawn. Lose the cambium and it becomes a monocot."""
        svg = self._render("plant_tissue", {"section_type": "dicot_stem"})
        self._assert_labels(svg, "Cambium", "Xylem", "Phloem", "Pith",
                            "Endodermis", "Pericycle", "Cortex", "RING")

        from diagrams.service.biology.renderer import _TISSUE_LAYOUT
        layout = _TISSUE_LAYOUT["dicot_stem"]
        self.assertEqual(layout["arrangement"], "ring")
        self.assertTrue(layout["cambium"])

    def test_plant_tissue_monocot_stem_is_scattered_and_closed(self):
        """Monocot stem = bundles SCATTERED in undifferentiated ground tissue and
        CLOSED (no cambium). Drawing a cambium here would be the wrong answer."""
        svg = self._render("plant_tissue", {"section_type": "monocot_stem"})
        text = _svg_text(svg)
        self._assert_labels(svg, "Ground tissue", "SCATTERED", "CLOSED",
                            "Xylem", "Phloem", "Bundle sheath")
        self.assertNotIn("Cambium", text)

        from diagrams.service.biology.renderer import _TISSUE_LAYOUT
        layout = _TISSUE_LAYOUT["monocot_stem"]
        self.assertEqual(layout["arrangement"], "scattered")
        self.assertFalse(layout["cambium"])

    def test_plant_tissue_dicot_root_is_tetrarch(self):
        """Dicot root = radial, exarch, 2–4 xylem arms (tetrarch). The arm count
        is what distinguishes it from a monocot root."""
        svg = self._render("plant_tissue", {"section_type": "dicot_root"})
        self._assert_labels(svg, "Tetrarch", "RADIAL", "Xylem", "Phloem",
                            "Epiblema", "Endodermis", "Pericycle")

        from diagrams.service.biology.renderer import _TISSUE_LAYOUT
        arms = _TISSUE_LAYOUT["dicot_root"]["n_xylem_arms"]
        self.assertEqual(_TISSUE_LAYOUT["dicot_root"]["arrangement"], "radial")
        self.assertTrue(2 <= arms <= 4, f"dicot root must be 2-4 arch, got {arms}")

    def test_plant_tissue_monocot_root_is_polyarch(self):
        """Monocot root = radial and POLYARCH (more than six xylem arms), with a
        large pith. Fewer than seven arms would make it a dicot root."""
        svg = self._render("plant_tissue", {"section_type": "monocot_root"})
        self._assert_labels(svg, "Polyarch", "RADIAL", "Xylem", "Phloem",
                            "Pith (large)")

        from diagrams.service.biology.renderer import _TISSUE_LAYOUT
        arms = _TISSUE_LAYOUT["monocot_root"]["n_xylem_arms"]
        self.assertEqual(_TISSUE_LAYOUT["monocot_root"]["arrangement"], "radial")
        self.assertGreater(arms, 6, f"monocot root must be polyarch, got {arms}")

    def test_plant_tissue_root_arm_counts_stay_distinct(self):
        """The single fact the two root sections exist to contrast: a monocot
        root carries strictly more xylem arms than a dicot root."""
        from diagrams.service.biology.renderer import _TISSUE_LAYOUT
        self.assertGreater(_TISSUE_LAYOUT["monocot_root"]["n_xylem_arms"],
                           _TISSUE_LAYOUT["dicot_root"]["n_xylem_arms"])

    def test_plant_tissue_leaf_is_dorsiventral(self):
        """In a leaf the xylem sits on the UPPER side and the phloem below it —
        the reverse of what students usually guess."""
        svg = self._render("plant_tissue", {"section_type": "leaf"})
        self._assert_labels(svg, "Cuticle", "Upper epidermis", "Lower epidermis",
                            "Palisade parenchyma", "Spongy parenchyma",
                            "Xylem (upper side)", "Phloem (lower side)",
                            "Stoma + guard cells", "Bundle sheath")

    def test_plant_tissue_highlight_and_no_labels(self):
        self.assertTrue(_is_valid_svg(self._render(
            "plant_tissue", {"section_type": "dicot_stem",
                             "highlight_tissue": "xylem"})))
        self.assertTrue(_is_valid_svg(self._render(
            "plant_tissue", {"section_type": "leaf", "show_labels": False})))

    # ── Organelle detail ──────────────────────────────────────────────────────
    def test_organelle_mitochondrion(self):
        """Cristae are infoldings of the INNER membrane — both membranes, the
        matrix, the 70S ribosomes and the circular DNA must all be labelled."""
        svg = self._render("organelle_detail", {"organelle": "mitochondrion"})
        self._assert_labels(svg, "Outer membrane", "Inner membrane", "Cristae",
                            "Matrix", "Ribosome (70S)", "DNA (circular)",
                            "Intermembrane space")

    def test_organelle_chloroplast(self):
        """A granum is a STACK of thylakoids joined by stroma lamellae. Losing
        that distinction breaks the standard photosynthesis question."""
        svg = self._render("organelle_detail", {"organelle": "chloroplast"})
        self._assert_labels(svg, "Outer membrane", "Inner membrane", "Stroma",
                            "Thylakoid", "Granum", "Stroma lamella",
                            "DNA (circular)")

    def test_organelle_nucleus(self):
        svg = self._render("organelle_detail", {"organelle": "nucleus"})
        self._assert_labels(svg, "Nuclear envelope", "Nuclear pore",
                            "Nucleolus", "Chromatin")

    def test_organelle_highlight_and_no_labels(self):
        self.assertTrue(_is_valid_svg(self._render(
            "organelle_detail", {"organelle": "nucleus",
                                 "highlight_part": "nucleolus"})))
        self.assertTrue(_is_valid_svg(self._render(
            "organelle_detail", {"organelle": "chloroplast",
                                 "show_labels": False})))

    # ── Metabolic cycles ──────────────────────────────────────────────────────
    def test_metabolic_cycle_krebs(self):
        """All eight intermediates in order, fed by acetyl CoA. A wrong Krebs
        cycle is worse than no diagram — this pins the intermediates."""
        svg = self._render("metabolic_cycle", {"cycle": "krebs"})
        self._assert_labels(svg, "Citrate (6C)", "Isocitrate (6C)",
                            "α-Ketoglutarate (5C)", "Succinyl CoA (4C)",
                            "Succinate (4C)", "Fumarate (4C)", "Malate (4C)",
                            "Oxaloacetate (4C)", "Acetyl CoA (2C)")

    def test_metabolic_cycle_krebs_cofactor_yield(self):
        """The co-factor tally (3 NADH, 1 FADH₂, 1 GTP, 2 CO₂ per acetyl CoA) is
        itself an exam question, so the edges must carry it."""
        svg = self._render("metabolic_cycle", {"cycle": "krebs"})
        self._assert_labels(svg, "FAD → FADH₂", "CO₂ released",
                            "3 NADH + 1 FADH₂ + 1 GTP (ATP) + 2 CO₂")

    def test_metabolic_cycle_calvin(self):
        """The three phases — carboxylation, reduction, regeneration."""
        svg = self._render("metabolic_cycle", {"cycle": "calvin"})
        self._assert_labels(svg, "RuBP (5C)", "3-PGA (3C)", "RuBisCO",
                            "CARBOXYLATION", "REDUCTION", "REGENERATION")

    def test_metabolic_cycle_glycolysis_is_linear(self):
        """Glycolysis is a linear cascade, not a cycle, and must run from glucose
        to pyruvate with the net 2 ATP + 2 NADH stated."""
        svg = self._render("metabolic_cycle", {"cycle": "glycolysis"})
        self._assert_labels(svg, "Glucose (6C)", "Fructose-1,6-bisphosphate",
                            "Phosphoenolpyruvate (PEP) × 2",
                            "Pyruvic acid (3C) × 2", "2 ATP + 2 NADH")

    def test_metabolic_cycle_nitrogen(self):
        """Nitrification is a two-organism relay (Nitrosomonas → Nitrobacter) and
        denitrification returns N₂. Naming the wrong genus is a wrong answer."""
        svg = self._render("metabolic_cycle", {"cycle": "nitrogen"})
        self._assert_labels(svg, "Nitrosomonas", "Nitrobacter", "Rhizobium",
                            "Denitrification", "Ammonification")

    def test_metabolic_cycle_carbon(self):
        svg = self._render("metabolic_cycle", {"cycle": "carbon"})
        self._assert_labels(svg, "Photosynthesis", "Respiration", "Combustion",
                            "Fossil fuels")

    def test_metabolic_cycle_urea(self):
        """The ornithine cycle, in order, with urea released at the arginase step."""
        svg = self._render("metabolic_cycle", {"cycle": "urea"})
        self._assert_labels(svg, "Ornithine", "Citrulline", "Argininosuccinate",
                            "Arginine", "UREA released")

    def test_metabolic_cycle_steps_override(self):
        """A model-supplied node/edge list must override the built-in defaults."""
        svg = self._render("metabolic_cycle", {
            "cycle": "krebs",
            "steps": [
                {"label": "Substrate A", "edge_label": "enzyme 1"},
                {"label": "Substrate B", "edge_label": "enzyme 2"},
                {"label": "Substrate C", "edge_label": "enzyme 3"},
            ],
        })
        text = _svg_text(svg)
        self._assert_labels(svg, "Substrate A", "enzyme 1", "Substrate C")
        self.assertNotIn("Isocitrate (6C)", text)

    def test_metabolic_cycle_layout_override(self):
        svg = self._render("metabolic_cycle",
                           {"cycle": "calvin", "layout": "linear"})
        self._assert_labels(svg, "RuBP (5C)")

    # ── Gel electrophoresis ───────────────────────────────────────────────────
    def test_gel_electrophoresis_renders(self):
        svg = self._render("gel_electrophoresis", {
            "lanes": [
                {"label": "Uncut", "bands": [{"size_bp": 10000}]},
                {"label": "EcoRI", "bands": [{"size_bp": 6000},
                                             {"size_bp": 4000,
                                              "intensity": 0.6}]},
            ],
            "ladder_sizes": [10000, 5000, 2000, 1000, 500, 100],
            "gel_label": "0.8% agarose gel",
        })
        self._assert_labels(svg, "Ladder", "Uncut", "EcoRI", "Wells",
                            "10,000 bp", "0.8% agarose gel")

    def test_gel_band_position_is_inverse_log_of_size(self):
        """THE invariant of the technique: DNA migration is inverse-log in
        fragment size, so a 10 000 bp band sits ABOVE (nearer the well than) a
        100 bp band. If this inverts, every gel question is answered backwards."""
        from diagrams.service.biology.renderer import _band_y
        lo, hi = 60, 16000
        y_10000 = _band_y(10000, lo, hi)
        y_1000 = _band_y(1000, lo, hi)
        y_100 = _band_y(100, lo, hi)
        self.assertGreater(y_10000, y_100)
        # ...and it is monotonic, not merely ordered at the extremes.
        self.assertGreater(y_10000, y_1000)
        self.assertGreater(y_1000, y_100)

    def test_gel_band_spacing_is_logarithmic(self):
        """Equal FOLD changes in size must give equal migration steps — that is
        what makes a ladder readable. 10000→1000 and 1000→100 are both 10-fold,
        so the two gaps must match."""
        from diagrams.service.biology.renderer import _band_y
        lo, hi = 60, 16000
        gap_upper = _band_y(10000, lo, hi) - _band_y(1000, lo, hi)
        gap_lower = _band_y(1000, lo, hi) - _band_y(100, lo, hi)
        self.assertAlmostEqual(gap_upper, gap_lower, places=6)

    def test_gel_migration_electrodes(self):
        """DNA is negatively charged: it runs away from the cathode towards the
        anode, i.e. down the gel."""
        svg = self._render("gel_electrophoresis", {
            "lanes": [{"label": "L1", "bands": [{"size_bp": 800}]}],
            "show_migration_arrow": True,
        })
        self._assert_labels(svg, "– cathode", "+ anode",
                            "Direction of migration")

    def test_gel_without_wells_or_arrow(self):
        svg = self._render("gel_electrophoresis", {
            "lanes": [{"label": "L1", "bands": [{"size_bp": 500}]}],
            "show_wells": False, "show_migration_arrow": False,
        })
        self.assertTrue(_is_valid_svg(svg))

    # ── Plasmid map ───────────────────────────────────────────────────────────
    def test_plasmid_map_features_and_sites(self):
        """Every feature arc and every restriction site must be labelled with its
        bp position — 'how many fragments does EcoRI give?' depends on it."""
        svg = self._render("plasmid_map", {
            "plasmid_name": "pBR322",
            "size_bp": 4361,
            "features": [
                {"name": "ori", "start_bp": 2500, "end_bp": 3200,
                 "feature_type": "ori"},
                {"name": "ampR", "start_bp": 3300, "end_bp": 4100,
                 "feature_type": "resistance_marker"},
                {"name": "tetR", "start_bp": 100, "end_bp": 1200,
                 "feature_type": "resistance_marker"},
            ],
            "restriction_sites": [
                {"enzyme": "EcoRI", "position_bp": 4359},
                {"enzyme": "BamHI", "position_bp": 375},
            ],
        })
        self._assert_labels(svg, "pBR322", "4,361 bp", "ori", "ampR", "tetR",
                            "EcoRI", "BamHI", "Origin of replication",
                            "Selectable (resistance) marker")

    def test_plasmid_map_every_feature_type(self):
        svg = self._render("plasmid_map", {
            "plasmid_name": "pUC19", "size_bp": 2686,
            "features": [
                {"name": "ori", "start_bp": 100, "end_bp": 600,
                 "feature_type": "ori"},
                {"name": "ampR", "start_bp": 700, "end_bp": 1200,
                 "feature_type": "resistance_marker"},
                {"name": "lacP", "start_bp": 1300, "end_bp": 1500,
                 "feature_type": "promoter"},
                {"name": "insert", "start_bp": 1600, "end_bp": 2000,
                 "feature_type": "insert"},
                {"name": "lacZ", "start_bp": 2100, "end_bp": 2600,
                 "feature_type": "gene"},
            ],
            "restriction_sites": [{"enzyme": "HindIII", "position_bp": 1650}],
        })
        self._assert_labels(svg, "Promoter", "Insert / foreign DNA", "Gene",
                            "HindIII")

    def test_plasmid_feature_may_wrap_the_origin(self):
        """A feature whose end_bp < start_bp spans the 0 bp mark. It must still
        draw as one arc rather than sweeping the long way round."""
        svg = self._render("plasmid_map", {
            "plasmid_name": "pWrap", "size_bp": 3000,
            "features": [{"name": "wrapped", "start_bp": 2800, "end_bp": 200,
                          "feature_type": "gene"}],
        })
        self._assert_labels(svg, "pWrap", "wrapped")

    def test_plasmid_position_outside_plasmid_is_rejected(self):
        """A site beyond the plasmid length is nonsense and must not silently
        render at some wrapped-around angle."""
        from diagrams.schemas.biology import PlasmidMapSchema
        with self.assertRaises(Exception):
            PlasmidMapSchema(
                size_bp=1000,
                restriction_sites=[{"enzyme": "EcoRI", "position_bp": 5000}],
            )

    # ── Brain diagram ─────────────────────────────────────────────────────────
    def test_brain_diagram_all_regions(self):
        """Every region NCERT names on the sagittal section."""
        svg = self._render("brain_diagram", {"show_labels": True})
        self._assert_labels(svg, "Cerebrum", "Cerebellum", "Medulla oblongata",
                            "Pons", "Midbrain", "Thalamus", "Hypothalamus",
                            "Corpus callosum", "Pituitary", "Olfactory lobe",
                            "Spinal cord")

    def test_brain_diagram_highlight_and_no_labels(self):
        self.assertTrue(_is_valid_svg(
            self._render("brain_diagram", {"highlight_region": "cerebellum"})))
        self.assertTrue(_is_valid_svg(
            self._render("brain_diagram", {"show_labels": False})))

    # ── Cross-cutting guarantees ──────────────────────────────────────────────
    def test_all_new_subtypes_are_registered(self):
        """The dispatcher is the only route the pipeline uses. An unregistered
        renderer is dead code no question can ever reach."""
        from diagrams.service.biology.renderer import BIOLOGY_RENDERERS
        for subtype in ("flower_structure", "eye_diagram", "digestive_system",
                        "respiratory_system", "plant_tissue", "organelle_detail",
                        "metabolic_cycle", "gel_electrophoresis", "plasmid_map",
                        "brain_diagram"):
            self.assertIn(subtype, BIOLOGY_RENDERERS)

    def test_renderers_are_deterministic(self):
        """Same params → byte-identical SVG. Papers are cached and re-printed;
        a diagram that changes between renders would break that."""
        cases = [
            ("eye_diagram", {"defect": "myopia"}),
            ("plant_tissue", {"section_type": "monocot_root"}),
            ("metabolic_cycle", {"cycle": "krebs"}),
            ("gel_electrophoresis",
             {"lanes": [{"label": "A", "bands": [{"size_bp": 500}]}]}),
        ]
        for subtype, params in cases:
            self.assertEqual(self._render(subtype, params),
                             self._render(subtype, params),
                             f"{subtype} is not deterministic")

    def test_invalid_enum_values_are_rejected(self):
        """A typo'd enum must fail loudly at validation rather than fall through
        to a silently wrong default diagram."""
        for subtype, params in (
            ("eye_diagram", {"defect": "astigmatism"}),
            ("plant_tissue", {"section_type": "fern_stem"}),
            ("organelle_detail", {"organelle": "golgi"}),
            ("metabolic_cycle", {"cycle": "photosynthesis"}),
            ("flower_structure", {"flower_type": "rose"}),
        ):
            with self.assertRaises(Exception, msg=f"{subtype} {params}"):
                self._render(subtype, params)
