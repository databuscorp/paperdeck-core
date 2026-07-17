"""
Unit tests for the SECOND wave of extended Biology renderers — the NEET
human-physiology, reproduction, molecular-biology and plant-physiology diagrams
added on top of ``test_biology_ext.py``.

Covers all twelve wave-2 subtypes:
    reproductive_system, gametogenesis, embryo_sac, anther_ts, sarcomere,
    population_growth, lac_operon, microbe_structure,      (wave-2 batch 1)
    ear_diagram, endocrine_system, kranz_anatomy, stomata.  (wave-2 batch 2)

These renderers are pure functions of their params and never touch the
database, so SimpleTestCase is enough. Every assertion is on a COMPUTED FACT
(a band width, a cell count, an aperture, a feedback direction) rather than on
raw SVG bytes — a diagram that is merely valid SVG can still teach the biology
backwards.
"""
from django.test import SimpleTestCase


def _is_valid_svg(content: str) -> bool:
    return bool(content and "<svg" in content and "</svg>" in content)


def _svg_text(svg: str) -> str:
    """Rendered text of the SVG. matplotlib silently DROPS text drawn outside
    the axes, so asserting on the rendered text is the only way to catch a label
    that has fallen off the canvas."""
    import re
    return " ".join(re.findall(r">([^<>]*)<", svg))


class TestBiologyWave2Renderers(SimpleTestCase):
    def _render(self, subtype, params):
        from diagrams.service.biology.renderer import render_biology
        return render_biology(subtype, params)

    def _assert_labels(self, svg, *labels):
        self.assertTrue(_is_valid_svg(svg))
        text = _svg_text(svg)
        for label in labels:
            self.assertIn(label, text, f"label '{label}' missing from the SVG")

    # ── Reproductive system ───────────────────────────────────────────────────
    def test_reproductive_system_male(self):
        """The male tract, in order testis → epididymis → vas deferens →
        urethra, plus the accessory glands. A missing duct breaks 'trace the
        path of the sperm' questions."""
        svg = self._render("reproductive_system", {"system": "human_male"})
        self._assert_labels(svg, "Testis", "Epididymis", "Vas deferens",
                            "Seminal vesicle", "Prostate gland", "Urethra",
                            "Seminiferous tubules", "Scrotum")

    def test_reproductive_system_female(self):
        """The female tract: ovary → fallopian tube → uterus → cervix → vagina,
        with the three wall layers of the uterus named."""
        svg = self._render("reproductive_system", {"system": "human_female"})
        self._assert_labels(svg, "Ovary", "Fallopian tube", "Fimbriae",
                            "Uterus", "Cervix", "Vagina", "Myometrium",
                            "Endometrium")

    # ── Gametogenesis ─────────────────────────────────────────────────────────
    def test_spermatogenesis_yields_four_spermatozoa(self):
        """One primary spermatocyte → FOUR functional spermatozoa via equal
        cytokinesis. If this count changes, the diagram contradicts the
        1-spermatocyte-to-4-sperm fact that NEET tests directly."""
        from diagrams.service.biology.renderer import _GAMETOGENESIS
        spec = _GAMETOGENESIS["spermatogenesis"]
        self.assertEqual(spec["functional_gametes"], 4)
        self.assertEqual(spec["polar_bodies"], 0)
        self.assertEqual(spec["cytokinesis"], "equal")
        svg = self._render("gametogenesis", {"process": "spermatogenesis"})
        self._assert_labels(svg, "Spermatozoa (sperms)")
        self.assertIn("SPERMATOZOA", _svg_text(svg))

    def test_oogenesis_yields_one_ovum_plus_polar_bodies(self):
        """One primary oocyte → exactly ONE ovum plus polar bodies via UNEQUAL
        cytokinesis. The asymmetry (1 ovum, not 4) is the whole contrast with
        spermatogenesis."""
        from diagrams.service.biology.renderer import _GAMETOGENESIS
        spec = _GAMETOGENESIS["oogenesis"]
        self.assertEqual(spec["functional_gametes"], 1)
        self.assertGreaterEqual(spec["polar_bodies"], 2)
        self.assertEqual(spec["cytokinesis"], "unequal")
        svg = self._render("gametogenesis", {"process": "oogenesis"})
        text = _svg_text(svg)
        self.assertIn("OVUM", text)
        self.assertIn("polar bodies", text)

    # ── Embryo sac ────────────────────────────────────────────────────────────
    def test_embryo_sac_is_seven_celled_eight_nucleate(self):
        """The mature embryo sac is 7-celled and 8-nucleate. Both totals are
        SUMMED from the cell table, so this pins the Polygonum-type sac NEET
        always asks about."""
        from diagrams.service.biology.renderer import _embryo_sac_counts
        cells, nuclei = _embryo_sac_counts()
        self.assertEqual(cells, 7)
        self.assertEqual(nuclei, 8)
        svg = self._render("embryo_sac", {})
        self._assert_labels(svg, "Egg cell", "Synergid", "Antipodal cells",
                            "Central cell", "Polar nuclei")

    def test_embryo_sac_triple_fusion_gives_triploid_pen(self):
        """Triple fusion (one male gamete + two polar nuclei) makes a TRIPLOID
        primary endosperm nucleus. If the ploidy shows anything but 3n the
        double-fertilisation question is answered wrong."""
        svg = self._render("embryo_sac", {"show_double_fertilisation": True})
        text = _svg_text(svg)
        self.assertIn("TRIPLE FUSION", text)
        self.assertIn("PEN (3n)", text)
        self.assertIn("ZYGOTE (2n)", text)

    # ── Anther T.S. ───────────────────────────────────────────────────────────
    def test_anther_ts_young_has_four_wall_layers(self):
        """A young anther wall is four-layered — epidermis, endothecium, middle
        layers and tapetum (outer → inner) — around sporogenous tissue. The
        tapetum is the innermost, nutritive layer."""
        svg = self._render("anther_ts", {"stage": "young"})
        self._assert_labels(svg, "Epidermis", "Endothecium", "Middle layers",
                            "Tapetum")

    def test_anther_ts_is_tetrasporangiate(self):
        """A typical anther is bilobed and TETRASPORANGIATE (four microsporangia
        / pollen sacs). Losing a sporangium makes it the wrong anther."""
        from diagrams.service.biology.renderer import _ANTHER_STAGE
        self.assertEqual(_ANTHER_STAGE["young"]["microsporangia"], 4)
        self.assertTrue(_is_valid_svg(self._render("anther_ts",
                                                   {"stage": "dehisced"})))

    # ── Sarcomere ─────────────────────────────────────────────────────────────
    def test_sarcomere_contraction_shrinks_i_and_h_but_not_a(self):
        """The sliding-filament invariant: on contraction the I band and H zone
        SHORTEN while the A band (= the thick filament) is UNCHANGED. If the A
        band changes, the diagram denies that the filaments slide rather than
        shorten."""
        from diagrams.service.biology.renderer import _sarcomere_geometry
        rel = _sarcomere_geometry("relaxed")
        con = _sarcomere_geometry("contracted")
        self.assertLess(con["i_band"], rel["i_band"])
        self.assertLess(con["h_zone"], rel["h_zone"])
        self.assertAlmostEqual(con["a_band"], rel["a_band"], places=6)
        self.assertLess(con["sarcomere_length"], rel["sarcomere_length"])

    def test_sarcomere_renders_both_states(self):
        svg = self._render("sarcomere", {"show_sliding_filament": True})
        self._assert_labels(svg, "A band", "I band", "H zone", "UNCHANGED")

    # ── Population growth ─────────────────────────────────────────────────────
    def test_logistic_growth_asymptotes_to_carrying_capacity(self):
        """The logistic curve rises towards K and never past it. At large t the
        population must equal K — a curve that overshoots would deny the
        density-dependent brake."""
        from diagrams.service.biology.renderer import _logistic_growth
        K = 500.0
        self.assertAlmostEqual(_logistic_growth(1e6, 0.3, 10.0, K), K, places=3)
        self.assertLess(_logistic_growth(20.0, 0.3, 10.0, K), K)

    def test_logistic_growth_rate_peaks_at_half_K(self):
        """dN/dt of the logistic model is maximal at N = K/2 — the fact behind
        'at what population size is the growth rate greatest?'."""
        from diagrams.service.biology.renderer import _logistic_rate
        K, r = 500.0, 0.3
        peak = _logistic_rate(K / 2, r, K)
        self.assertGreater(peak, _logistic_rate(K * 0.25, r, K))
        self.assertGreater(peak, _logistic_rate(K * 0.75, r, K))
        grid = [n * K / 100 for n in range(1, 100)]
        best = max(grid, key=lambda n: _logistic_rate(n, r, K))
        self.assertAlmostEqual(best, K / 2, delta=K / 100)

    def test_population_growth_renders_both_models(self):
        svg = self._render("population_growth", {"model": "both"})
        self._assert_labels(svg, "Carrying capacity")

    # ── lac operon ────────────────────────────────────────────────────────────
    def test_lac_operon_off_repressor_occupies_operator(self):
        """In the OFF (no-lactose) state the active repressor SITS ON the
        operator and blocks RNA polymerase. If the flag flips, the diagram shows
        transcription happening without lactose — the opposite of the truth."""
        from diagrams.service.biology.renderer import _LAC_STATE
        self.assertTrue(_LAC_STATE["repressed_off"]["repressor_on_operator"])
        self.assertFalse(_LAC_STATE["repressed_off"]["transcription"])
        svg = self._render("lac_operon", {"state": "repressed_off"})
        text = _svg_text(svg)
        self.assertIn("BLOCKED", text)
        self.assertIn("NO mRNA", text)

    def test_lac_operon_on_repressor_off_operator(self):
        """In the ON (lactose present) state allolactose inactivates the
        repressor, the operator is free and the three genes are transcribed as
        one polycistronic mRNA."""
        from diagrams.service.biology.renderer import _LAC_STATE
        self.assertFalse(_LAC_STATE["inducible_on"]["repressor_on_operator"])
        self.assertTrue(_LAC_STATE["inducible_on"]["transcription"])
        svg = self._render("lac_operon", {"state": "inducible_on"})
        text = _svg_text(svg)
        self.assertIn("transcription proceeds", text)
        self.assertIn("Allolactose", text)

    # ── Microbe structure ─────────────────────────────────────────────────────
    def test_microbe_bacteriophage(self):
        """A T-even phage: head (capsid) of DNA on a contractile tail with tail
        fibres. The DNA is inside the head, not the tail — a common trap."""
        svg = self._render("microbe_structure", {"microbe": "bacteriophage"})
        self._assert_labels(svg, "Head (capsid)", "Collar", "Sheath",
                            "Tail fibres")

    def test_microbe_hiv_is_a_retrovirus(self):
        """HIV carries reverse transcriptase and (+) ssRNA inside its capsid —
        the retrovirus features the question turns on."""
        svg = self._render("microbe_structure", {"microbe": "virus_hiv"})
        text = _svg_text(svg)
        self.assertIn("Reverse transcriptase", text)
        self.assertIn("ssRNA", text)

    # ── Ear diagram ───────────────────────────────────────────────────────────
    def test_ear_all_three_regions_and_parts(self):
        """Every part NEET names, grouped external / middle / internal: pinna
        and canal, the three ossicles, cochlea and organ of Corti, the
        semicircular canals and the auditory nerve."""
        svg = self._render("ear_diagram", {})
        self._assert_labels(svg, "EXTERNAL EAR", "MIDDLE EAR", "INTERNAL EAR",
                            "Pinna", "Malleus", "Incus", "Stapes",
                            "Eustachian tube", "Cochlea", "Vestibule",
                            "Auditory nerve", "Organ of Corti")

    def test_ear_semicircular_canals_labelled(self):
        svg = self._render("ear_diagram", {"highlight_part": "cochlea"})
        self._assert_labels(svg, "Semicircular", "Tympanic membrane")

    def test_ear_without_inset_drops_organ_of_corti(self):
        """The organ of Corti lives in the cochlear-turn inset; drop the inset
        and the label must go with it rather than dangling."""
        svg = self._render("ear_diagram", {"show_cochlea_inset": False})
        self.assertTrue(_is_valid_svg(svg))
        self.assertNotIn("Organ of Corti", _svg_text(svg))

    # ── Endocrine system ──────────────────────────────────────────────────────
    def test_endocrine_gland_locations(self):
        """The location map must site every gland from hypothalamus to gonad —
        this is the 'name the labelled gland' diagram."""
        svg = self._render("endocrine_system", {"view": "gland_locations"})
        self._assert_labels(svg, "Hypothalamus", "Pituitary gland",
                            "Pineal gland", "Thyroid gland",
                            "Parathyroid glands", "Thymus", "Adrenal glands",
                            "Gonads (testis / ovary)")

    def test_endocrine_feedback_loop_is_negative(self):
        """The hypothalamo–pituitary–thyroid axis closes with NEGATIVE feedback:
        the target hormone inhibits the hypothalamus and pituitary. The
        inhibition is the whole point of the diagram."""
        svg = self._render("endocrine_system",
                           {"view": "feedback_loop", "axis": "thyroid"})
        text = _svg_text(svg)
        self._assert_labels(svg, "Hypothalamus", "Anterior pituitary",
                            "Thyroid gland", "TSH")
        self.assertIn("NEGATIVE FEEDBACK", text)

    def test_endocrine_feedback_axes_use_correct_hormones(self):
        """Each axis names its own releasing and tropic hormones (CRH/ACTH for
        adrenal, GnRH/FSH-LH for gonad). A swapped hormone is a wrong answer."""
        from diagrams.service.biology.renderer import _ENDOCRINE_AXES
        self.assertEqual(_ENDOCRINE_AXES["adrenal"]["tropic"], "ACTH")
        self.assertEqual(_ENDOCRINE_AXES["gonad"]["releasing"], "GnRH")
        svg = self._render("endocrine_system",
                           {"view": "feedback_loop", "axis": "adrenal"})
        self._assert_labels(svg, "ACTH", "Adrenal cortex")

    def test_endocrine_hormone_table(self):
        svg = self._render("endocrine_system", {"view": "hormone_table"})
        self._assert_labels(svg, "Gland", "Insulin, Glucagon",
                            "Parathormone (PTH)")

    # ── Kranz anatomy ─────────────────────────────────────────────────────────
    def test_kranz_c4_has_wreath_c3_does_not(self):
        """Kranz anatomy IS the C3/C4 diagnostic: only the C4 leaf has a
        chloroplast-rich bundle-sheath wreath. If the flag is wrong, the diagram
        cannot answer 'which leaf shows Kranz anatomy?'."""
        from diagrams.service.biology.renderer import _KRANZ_FEATURES
        self.assertTrue(_KRANZ_FEATURES["c4"]["kranz"])
        self.assertFalse(_KRANZ_FEATURES["c3"]["kranz"])

    def test_kranz_c4_section_renders_the_wreath(self):
        """The C4 section must name the bundle-sheath wreath and the Hatch–Slack
        split (PEP carboxylase in mesophyll, RuBisCO in the bundle sheath)."""
        svg = self._render("kranz_anatomy", {"pathway": "c4"})
        text = _svg_text(svg)
        self.assertIn("Kranz anatomy", text)
        self.assertIn("Bundle-sheath wreath", text)
        self.assertIn("PEP carboxylase", text)

    def test_kranz_c3_section_states_no_kranz(self):
        """The C3 section must explicitly deny Kranz anatomy and show the
        palisade / spongy differentiation instead."""
        svg = self._render("kranz_anatomy", {"pathway": "c3"})
        text = _svg_text(svg)
        self.assertIn("NO Kranz anatomy", text)
        self._assert_labels(svg, "Palisade parenchyma", "Spongy parenchyma")

    def test_kranz_comparison_shows_both(self):
        svg = self._render("kranz_anatomy", {"pathway": "comparison"})
        text = _svg_text(svg)
        self.assertIn("Kranz anatomy", text)
        self.assertIn("NO Kranz anatomy", text)

    # ── Stomata ───────────────────────────────────────────────────────────────
    def test_stomata_open_has_aperture_closed_has_none(self):
        """The mechanism in one number: turgid guard cells give a positive pore
        aperture; flaccid guard cells meet, so the aperture is ~zero. If closed
        kept a pore, the guard-cell turgor mechanism would be denied."""
        from diagrams.service.biology.renderer import _stomata_aperture
        self.assertGreater(_stomata_aperture("open"), 0.0)
        self.assertAlmostEqual(_stomata_aperture("closed"), 0.0, places=6)
        self.assertGreater(_stomata_aperture("open"),
                           _stomata_aperture("closed"))

    def test_stomata_open_ion_flux_is_influx(self):
        """Opening is driven by K⁺ moving IN and water following. The open panel
        must show influx, the closed panel efflux."""
        svg_open = self._render("stomata", {"state": "open"})
        svg_closed = self._render("stomata", {"state": "closed"})
        self.assertIn("K⁺ in", _svg_text(svg_open))
        self.assertIn("K⁺ out", _svg_text(svg_closed))
        self._assert_labels(svg_open, "Guard cell", "Stomatal pore",
                            "Subsidiary cell")

    def test_stomata_dumbbell_shape(self):
        svg = self._render("stomata",
                           {"state": "both", "guard_cell_shape": "dumbbell"})
        self.assertIn("dumb-bell shaped", _svg_text(svg))

    # ── Cross-cutting guarantees ──────────────────────────────────────────────
    def test_all_wave2_subtypes_registered(self):
        """The dispatcher is the only route the pipeline uses; an unregistered
        renderer is dead code no question can ever reach."""
        from diagrams.service.biology.renderer import BIOLOGY_RENDERERS
        for subtype in ("reproductive_system", "gametogenesis", "embryo_sac",
                        "anther_ts", "sarcomere", "population_growth",
                        "lac_operon", "microbe_structure", "ear_diagram",
                        "endocrine_system", "kranz_anatomy", "stomata"):
            self.assertIn(subtype, BIOLOGY_RENDERERS)

    def test_wave2_renderers_are_deterministic(self):
        """Same params → byte-identical SVG. Papers are cached and re-printed; a
        diagram that changed between renders would break that."""
        cases = [
            ("ear_diagram", {}),
            ("endocrine_system", {"view": "feedback_loop", "axis": "gonad"}),
            ("kranz_anatomy", {"pathway": "comparison"}),
            ("stomata", {"state": "both", "guard_cell_shape": "dumbbell"}),
            ("lac_operon", {"state": "repressed_off"}),
        ]
        for subtype, params in cases:
            self.assertEqual(self._render(subtype, params),
                             self._render(subtype, params),
                             f"{subtype} is not deterministic")

    def test_invalid_enum_values_are_rejected(self):
        """A typo'd enum must fail loudly at validation rather than fall through
        to a silently wrong default diagram."""
        for subtype, params in (
            ("endocrine_system", {"view": "map"}),
            ("endocrine_system", {"view": "feedback_loop", "axis": "liver"}),
            ("kranz_anatomy", {"pathway": "c5"}),
            ("stomata", {"state": "ajar"}),
            ("stomata", {"guard_cell_shape": "round"}),
        ):
            with self.assertRaises(Exception, msg=f"{subtype} {params}"):
                self._render(subtype, params)
