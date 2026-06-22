import json
import logging
import os
import re
import time

import anthropic

logger = logging.getLogger(__name__)

HAIKU_MODEL = "claude-haiku-4-5-20251001"
SONNET_MODEL = "claude-sonnet-4-6"


# Matches a real JSON escape (``\\`` pair, ``\"``, ``\/`` or ``\uXXXX``) OR a
# single backslash. The ``\\\\`` alternative is first so already-escaped pairs
# are consumed as a unit and left intact.
_JSON_ESCAPE_RE = re.compile(r'\\\\|\\"|\\/|\\u[0-9a-fA-F]{4}|\\')


def _loads_lenient(raw: str):
    """Parse model JSON, fixing LaTeX backslashes that JSON would mis-handle.

    The model is asked to emit LaTeX such as ``$\\frac{a}{b}$`` with single
    backslashes. Those break JSON in two different ways:

    * ``\\c \\s \\a \\m \\p`` …  → ``json.loads`` raises ``Invalid \\escape``.
    * ``\\t \\f \\n \\r \\b``   → ``json.loads`` *silently* parses them to
      tab / form-feed / newline etc. and corrupts ``\\text``, ``\\frac``,
      ``\\nabla`` …  (no error, just mangled output).

    Because of the second case we can't simply try a strict parse first — we
    always rewrite escapes, keeping only the genuine JSON ones (``\\\\``,
    ``\\"``, ``\\/`` and ``\\uXXXX``) and turning every other backslash into a
    literal ``\\\\`` so the LaTeX survives intact. The ``\\\\`` alternative in the
    regex consumes already-escaped pairs as a unit, so correctly-escaped input
    is left unchanged.
    """
    sanitized = _JSON_ESCAPE_RE.sub(lambda m: m.group(0) if m.group(0) != "\\" else "\\\\", raw)
    return json.loads(sanitized)


def _img_is_block(data_url: str) -> bool:
    """True if an image is a figure/diagram (render as a block) rather than an
    inline equation. A real diagram is large in BOTH dimensions or has a large
    area; a tall fraction or a wide expression stays inline so it isn't blown up."""
    try:
        import base64
        import io
        from PIL import Image
        b64 = data_url.split(',', 1)[1]
        w, h = Image.open(io.BytesIO(base64.b64decode(b64))).size
        return (w >= 200 and h >= 120) or (w * h >= 45000)
    except Exception:
        return False


def _salvage_objects(raw: str) -> list:
    """Extract every COMPLETE top-level {...} object from a (possibly truncated)
    string via brace counting, parsing each individually. Lets us recover all
    finished question objects when the model's JSON was cut off mid-array."""
    out = []
    depth = 0
    start = -1
    in_str = False
    esc = False
    for i, ch in enumerate(raw):
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            if depth > 0:
                depth -= 1
                if depth == 0 and start != -1:
                    chunk = raw[start:i + 1]
                    for parse in (lambda: _loads_lenient(chunk), lambda: json.loads(chunk)):
                        try:
                            obj = parse()
                            if isinstance(obj, dict):
                                out.append(obj)
                            break
                        except Exception:
                            continue
                    start = -1
    return out

# ── LaTeX math notation hint ──────────────────────────────────────────────────
# Injected into every question-generation prompt so the AI consistently
# uses $...$ delimiters that the LaTeX rendering pipeline can parse.
_LATEX_MATH_HINT = """
IMPORTANT — Mathematical Notation Rules:
Use LaTeX math notation for ALL mathematical expressions:
  Inline math  →  wrap with $...$         e.g. "A block of mass $m = 2\\text{ kg}$"
  Display math →  wrap with $$...$$       e.g. "$$\\int_0^{\\pi} \\sin x\\, dx = 2$$"

Common patterns:
  Fractions:       $\\frac{a}{b}$
  Powers:          $x^2$, $e^{-kt}$
  Subscripts:      $x_1$, $v_0$
  Greek letters:   $\\alpha$, $\\beta$, $\\theta$, $\\omega$, $\\Delta$, $\\lambda$
  Vectors:         $\\vec{F}$, $\\hat{n}$
  Derivatives:     $\\frac{d}{dx}$, $\\frac{dy}{dt}$
  Integrals:       $\\int_a^b f(x)\\,dx$
  Square roots:    $\\sqrt{2}$, $\\sqrt[3]{x}$
  Trigonometry:    $\\sin\\theta$, $\\cos\\frac{\\pi}{3}$, $\\tan^{-1}$
  Units (inline):  $10\\text{ m/s}$, $9.8\\text{ m/s}^2$
  Equations:       $F = ma$, $E = mc^2$, $PV = nRT$
  Limits:          $\\lim_{x \\to 0}$
  Summation:       $\\sum_{n=1}^{\\infty}$

Chemical formulas use plain Unicode (not LaTeX): H₂O, CO₂, H₂SO₄, CaCO₃
Do NOT use LaTeX for purely textual content.
"""

# ── Diagram schema hint injected into the AI prompt ───────────────────────────
# Tells the AI exactly what schemas are valid so it picks the right one.
_DIAGRAM_SCHEMA_HINT = """
SUPPORTED diagram_schema values (pick the ONE that best fits the question):

Physics:
  {"diagram_type":"physics","subtype":"inclined_plane","params":{"angle":<deg 1-89>,"forces":["mg","N","f"],"block_label":"m"}}
  {"diagram_type":"physics","subtype":"free_body_diagram","params":{"object":{"shape":"square","label":"m"},"forces":[{"label":"mg","direction_deg":270},{"label":"N","direction_deg":90}]}}
  {"diagram_type":"physics","subtype":"pulley_system","params":{"pulley_count":1,"masses":[{"label":"m₁"},{"label":"m₂"}]}}
  {"diagram_type":"physics","subtype":"projectile_motion","params":{"initial_velocity":20,"launch_angle":45,"show_components":true}}
  {"diagram_type":"physics","subtype":"spring_block","params":{"orientation":"horizontal","block_label":"m","spring_label":"k"}}
  {"diagram_type":"physics","subtype":"optics_convex_lens","params":{"focal_length":100,"show_rays":true}}
  {"diagram_type":"physics","subtype":"optics_concave_mirror","params":{"focal_length":110,"show_rays":true}}
  {"diagram_type":"physics","subtype":"wave_diagram","params":{"amplitude":80,"num_cycles":2.5}}
  {"diagram_type":"physics","subtype":"thermodynamics_pv","params":{"states":[{"label":"A","volume":2,"pressure":5},{"label":"B","volume":4,"pressure":5},{"label":"C","volume":4,"pressure":2}],"processes":[{"from_state":"A","to_state":"B","process_type":"isobaric"},{"from_state":"B","to_state":"C","process_type":"isochoric"}],"title":"P-V Diagram"}}
  {"diagram_type":"physics","subtype":"ray_optics_prism","params":{"prism_angle":60,"incident_angle":45,"refractive_index":1.5,"show_normals":true,"show_angles":true,"label_deviation":true}}
  {"diagram_type":"physics","subtype":"electric_field_lines","params":{"field_type":"point_charges","charges":[{"x":-1,"y":0,"charge":1,"label":"+q"},{"x":1,"y":0,"charge":-1,"label":"-q"}],"num_lines":8}}
  {"diagram_type":"physics","subtype":"magnetic_field_lines","params":{"source_type":"bar_magnet","label_poles":true,"num_field_lines":8}}
  {"diagram_type":"physics","subtype":"circular_motion","params":{"show_velocity":true,"show_centripetal":true,"radius_label":"r","mass_label":"m","velocity_label":"v","centripetal_label":"F_c","object_angle_deg":45}}

Chemistry:
  {"diagram_type":"chemistry","subtype":"organic_structure","params":{"smiles":"<SMILES string>","name":"<compound name>"}}
  {"diagram_type":"chemistry","subtype":"organic_structure","params":{"smiles":"CC(=O)Oc1ccccc1","name":"Aspirin","show_eas_positions":true,"activated_positions":["ortho","para"]}}
  {"diagram_type":"chemistry","subtype":"inorganic_structure","params":{"atoms":[{"symbol":"O"},{"symbol":"H"},{"symbol":"H"}],"bonds":[{"from_atom":0,"to_atom":1,"bond_type":"single"},{"from_atom":0,"to_atom":2,"bond_type":"single"}],"title":"<name>"}}
  {"diagram_type":"chemistry","subtype":"reaction_coordinate_graph","params":{"reactant_energy":0,"product_energy":-40,"activation_energy":80}}
  {"diagram_type":"chemistry","subtype":"orbital_diagram","params":{"element":"Carbon","electron_config":[{"shell":"1s","electrons":2,"max_electrons":2,"sublevel_count":1},{"shell":"2s","electrons":2,"max_electrons":2,"sublevel_count":1},{"shell":"2p","electrons":2,"max_electrons":6,"sublevel_count":3}]}}
  {"diagram_type":"chemistry","subtype":"electrochemical_cell","params":{"anode_material":"Zn","anode_ion":"Zn²⁺","anode_solution":"ZnSO₄","cathode_material":"Cu","cathode_ion":"Cu²⁺","cathode_solution":"CuSO₄","cell_name":"Daniell Cell","emf":1.10,"show_half_reactions":true}}
  {"diagram_type":"chemistry","subtype":"equilibrium_graph","params":{"reactant_labels":["[A]","[B]"],"product_labels":["[C]"],"equilibrium_time":0.5,"show_kc_marker":true,"title":"Equilibrium Concentration vs Time"}}
  {"diagram_type":"chemistry","subtype":"titration_curve","params":{"acid_type":"strong","base_type":"strong","initial_ph":1.0,"equivalence_ph":7.0,"final_ph":13.0,"titrant_label":"NaOH","analyte_label":"HCl","show_equivalence_point":true}}

Mathematics:
  {"diagram_type":"mathematics","subtype":"function_graph","params":{"functions":[{"expression":"<sympy expr>","label":"<label>","x_range":[-5,5],"line_style":"solid"},{"expression":"<sympy expr2>","label":"<label2>","x_range":[-5,5],"line_style":"dashed"}],"x_range":[-5,5],"show_intersections":true,"intersection_labels":true}}
  {"diagram_type":"mathematics","subtype":"geometry_triangle","params":{"vertices":[{"label":"A","x":0,"y":0},{"label":"B","x":4,"y":0},{"label":"C","x":2,"y":3}],"angles":[60,60,60]}}
  {"diagram_type":"mathematics","subtype":"geometry_circle","params":{"show_radius":true,"arc_angle":90}}
  {"diagram_type":"mathematics","subtype":"calculus_graph","params":{"function":"<sympy expr>","x_range":[-4,4],"shaded_regions":[{"x_from":<a>,"x_to":<b>,"label":"A"}]}}
  {"diagram_type":"mathematics","subtype":"coordinate_geometry","params":{"lines":[{"slope":<m>,"intercept":<b>,"label":"<eq>"}],"points":[{"x":<x>,"y":<y>,"label":"<lbl>"}]}}
  {"diagram_type":"mathematics","subtype":"conic_section","params":{"conic_type":"ellipse","a":5,"b":3,"orientation":"horizontal","show_foci":true,"show_vertices":true,"title":"Ellipse"}}
  {"diagram_type":"mathematics","subtype":"conic_section","params":{"conic_type":"parabola","a":2,"orientation":"horizontal","show_foci":true,"show_directrix":true,"title":"Parabola y²=8x"}}
  {"diagram_type":"mathematics","subtype":"conic_section","params":{"conic_type":"hyperbola","a":3,"b":4,"orientation":"horizontal","show_foci":true,"show_asymptotes":true,"title":"Hyperbola"}}
  {"diagram_type":"mathematics","subtype":"venn_diagram","params":{"sets":[{"label":"A","region_value":"3"},{"label":"B","region_value":"5"}],"intersection_labels":["2"],"universal_set_label":"U","title":"Venn Diagram"}}
  {"diagram_type":"mathematics","subtype":"number_line","params":{"x_min":-3,"x_max":5,"points":[{"value":2,"label":"2","filled":true}],"intervals":[{"start":-1,"end":3,"filled_start":false,"filled_end":true}],"title":"Solution set"}}

Biology (NEET):
  {"diagram_type":"biology","subtype":"cell_diagram","params":{"cell_type":"animal","labeled":true,"highlight_organelle":"mitochondria"}}
  {"diagram_type":"biology","subtype":"cell_diagram","params":{"cell_type":"plant","labeled":true,"show_chloroplast":true,"show_cell_wall":true,"show_vacuole":true}}
  {"diagram_type":"biology","subtype":"dna_structure","params":{"structure_type":"double_helix","num_base_pairs":10,"show_base_labels":true,"show_labels":true}}
  {"diagram_type":"biology","subtype":"dna_structure","params":{"structure_type":"replication_fork","num_base_pairs":10,"show_labels":true}}
  {"diagram_type":"biology","subtype":"cell_division","params":{"division_type":"mitosis","stage":"metaphase","num_chromosome_pairs":2,"show_spindle":true,"show_labels":true}}
  {"diagram_type":"biology","subtype":"cell_division","params":{"division_type":"meiosis","stage":"metaphase_1","num_chromosome_pairs":2,"show_labels":true}}
  {"diagram_type":"biology","subtype":"cell_division","params":{"division_type":"meiosis","stage":"prophase_1","num_chromosome_pairs":2,"show_labels":true}}
  {"diagram_type":"biology","subtype":"heart_diagram","params":{"show_labels":true,"show_blood_flow":true,"show_valves":true}}
  {"diagram_type":"biology","subtype":"nephron_diagram","params":{"show_labels":true,"show_blood_vessels":true,"highlight_region":"loop_of_henle"}}
  {"diagram_type":"biology","subtype":"neuron_diagram","params":{"neuron_type":"myelinated","show_labels":true,"show_impulse_direction":true}}
  {"diagram_type":"biology","subtype":"food_web","params":{"nodes":[{"id":"grass","label":"Grass","trophic_level":1},{"id":"rabbit","label":"Rabbit","trophic_level":2},{"id":"fox","label":"Fox","trophic_level":3},{"id":"eagle","label":"Eagle","trophic_level":4}],"edges":[{"from_id":"grass","to_id":"rabbit"},{"from_id":"rabbit","to_id":"fox"},{"from_id":"fox","to_id":"eagle"}],"title":"Grassland Food Web"}}
  {"diagram_type":"biology","subtype":"food_chain","params":{"organisms":["Grass","Grasshopper","Frog","Snake","Eagle"],"title":"Grassland Food Chain"}}
  {"diagram_type":"biology","subtype":"ecological_pyramid","params":{"pyramid_type":"biomass","levels":[{"label":"Producers","value":10000,"unit":"kg"},{"label":"Herbivores","value":1000,"unit":"kg"},{"label":"Carnivores","value":100,"unit":"kg"},{"label":"Top Carnivores","value":10,"unit":"kg"}]}}

Circuits:
  {"diagram_type":"circuits","subtype":"resistor_network","params":{"topology":"series","resistors":["R₁=<val>Ω","R₂=<val>Ω"],"voltage_source":"<V>V"}}
  {"diagram_type":"circuits","subtype":"capacitor_network","params":{"topology":"parallel","capacitors":["C₁=<val>μF","C₂=<val>μF"]}}
  {"diagram_type":"circuits","subtype":"basic_dc_circuit","params":{"components":[{"type":"battery","value":"<V>V","direction":"up"},{"type":"resistor","label":"R","value":"<val>Ω","direction":"right"}]}}

Physics (advanced):
  {"diagram_type":"physics","subtype":"doppler_effect","params":{"source_velocity":0.6,"direction":"right","observer_side":"right","num_wavefronts":8,"show_frequency_labels":true,"title":"Doppler Effect: Moving Source"}}
  {"diagram_type":"physics","subtype":"interference_pattern","params":{"pattern_type":"double_slit","slit_separation":2.5,"wavelength":550,"num_maxima":5,"show_intensity_curve":true,"title":"Young's Double Slit"}}
  {"diagram_type":"physics","subtype":"interference_pattern","params":{"pattern_type":"single_slit","wavelength":600,"num_maxima":3,"show_intensity_curve":true,"title":"Single Slit Diffraction"}}
  {"diagram_type":"physics","subtype":"bohr_atom","params":{"element":"H","num_shells":5,"transitions":[{"from_shell":3,"to_shell":1,"label":"Lyman α","color":"purple"},{"from_shell":3,"to_shell":2,"label":"Hα","color":"red"}],"title":"Hydrogen Bohr Model"}}
  {"diagram_type":"physics","subtype":"bohr_atom","params":{"element":"Na","num_shells":3,"electrons_per_shell":[2,8,1],"title":"Sodium Atom"}}
  {"diagram_type":"physics","subtype":"capacitor_dielectric","params":{"dielectric_label":"Glass (ε_r = 6)","num_field_lines":8,"show_induced_charges":true,"voltage_label":"V","title":"Capacitor with Glass Dielectric"}}
  {"diagram_type":"physics","subtype":"lc_oscillation","params":{"inductance_label":"L","capacitance_label":"C","show_circuit":true,"show_graphs":true,"num_cycles":2,"initial_state":"charged","title":"LC Oscillation"}}

Chemistry (advanced):
  {"diagram_type":"chemistry","subtype":"sn1_sn2_mechanism","params":{"mechanism_type":"sn2","substrate":"CH₃Br","nucleophile":"OH⁻","leaving_group":"Br⁻","product":"CH₃OH","show_curved_arrows":true,"show_stereochemistry":true,"title":"SN2 Mechanism"}}
  {"diagram_type":"chemistry","subtype":"sn1_sn2_mechanism","params":{"mechanism_type":"sn1","substrate":"(CH₃)₃CBr","nucleophile":"H₂O","leaving_group":"Br⁻","product":"(CH₃)₃COH","intermediate":"(CH₃)₃C⁺","title":"SN1 Mechanism"}}
  {"diagram_type":"chemistry","subtype":"newman_projection","params":{"front_carbon":"C1","back_carbon":"C2","front_substituents":["H","CH₃","H"],"back_substituents":["H","H","CH₃"],"dihedral_angle":180,"conformation_label":"Anti","title":"Newman Projection (Anti)"}}
  {"diagram_type":"chemistry","subtype":"conformational_isomers","params":{"molecule_type":"cyclohexane","conformations":["chair","boat"],"show_axial_equatorial":true,"title":"Cyclohexane Conformations"}}
  {"diagram_type":"chemistry","subtype":"conformational_isomers","params":{"molecule_type":"ethane","conformations":["staggered","eclipsed"],"title":"Ethane Conformations"}}

Mathematics (advanced):
  {"diagram_type":"mathematics","subtype":"bar_chart","params":{"bars":[{"label":"Jan","value":120},{"label":"Feb","value":95},{"label":"Mar","value":145},{"label":"Apr","value":110}],"x_label":"Month","y_label":"Frequency","show_values":true,"title":"Monthly Distribution"}}
  {"diagram_type":"mathematics","subtype":"scatter_plot","params":{"points":[{"x":1,"y":2.1},{"x":2,"y":3.9},{"x":3,"y":6.2},{"x":4,"y":7.8},{"x":5,"y":10.1}],"show_regression_line":true,"show_r_squared":true,"x_label":"Time (s)","y_label":"Distance (m)","title":"Distance vs Time"}}
  {"diagram_type":"mathematics","subtype":"vector_3d","params":{"vectors":[{"x":2,"y":0,"z":0,"label":"i","color":"red"},{"x":0,"y":2,"z":0,"label":"j","color":"green"},{"x":0,"y":0,"z":2,"label":"k","color":"blue"}],"show_axes":true,"title":"Unit Vectors"}}
  {"diagram_type":"mathematics","subtype":"vector_3d","params":{"vectors":[{"x":3,"y":4,"z":5,"label":"F","color":"purple"}],"show_projections":true,"show_angle_between":false,"title":"Force Vector in 3D"}}
"""

EXAM_CONFIGS = {
    "NEET": {
        "total_questions": 180,
        "sections": [
            {"subject": "Physics", "questions": 45, "marks_per_q": 4, "negative": -1},
            {"subject": "Chemistry", "questions": 45, "marks_per_q": 4, "negative": -1},
            {"subject": "Botany", "questions": 45, "marks_per_q": 4, "negative": -1},
            {"subject": "Zoology", "questions": 45, "marks_per_q": 4, "negative": -1},
        ],
    },
    "JEE Mains": {
        "total_questions": 90,
        "sections": [
            {"subject": "Physics", "questions": 30, "marks_per_q": 4, "negative": -1},
            {"subject": "Chemistry", "questions": 30, "marks_per_q": 4, "negative": -1},
            {"subject": "Mathematics", "questions": 30, "marks_per_q": 4, "negative": -1},
        ],
    },
    "JEE Advanced": {
        "total_questions": 54,
        "sections": [
            {"subject": "Physics", "questions": 18, "marks_per_q": 3, "negative": -1},
            {"subject": "Chemistry", "questions": 18, "marks_per_q": 3, "negative": -1},
            {"subject": "Mathematics", "questions": 18, "marks_per_q": 3, "negative": -1},
        ],
    },
}


def _build_generation_prompt(exam_type: str, subjects: list, difficulty: str, total_marks: int) -> str:
    config = EXAM_CONFIGS.get(exam_type, {})
    sections_info = ""
    if config:
        for s in config.get("sections", []):
            if not subjects or s["subject"] in subjects:
                sections_info += f"- {s['subject']}: {s['questions']} questions, {s['marks_per_q']} marks each\n"

    return f"""Generate a complete {exam_type} question paper with the following specifications:
Difficulty: {difficulty}
Total Marks: {total_marks}
Subjects: {', '.join(subjects) if subjects else 'all standard subjects'}

{f'Section breakdown:{chr(10)}{sections_info}' if sections_info else ''}

Return ONLY a valid JSON object with this exact structure:
{{
  "sections": [
    {{
      "subject": "Subject Name",
      "questions": [
        {{
          "number": 1,
          "text": "Question text here",
          "options": ["A) option1", "B) option2", "C) option3", "D) option4"],
          "correct_answer": "A",
          "marks": 4,
          "negative_marks": -1,
          "topic": "specific topic",
          "explanation": "Brief explanation of the answer"
        }}
      ]
    }}
  ],
  "total_marks": {total_marks},
  "exam_type": "{exam_type}"
}}

Generate realistic, high-quality MCQ questions appropriate for {exam_type}. Each question must have exactly 4 options labeled A, B, C, D. Include only questions from standard {exam_type} syllabus."""


def _build_crosscheck_prompt(section_json: dict, subject: str) -> str:
    return f"""Review these {subject} questions from a {section_json.get('exam_type', 'competitive exam')} paper.
Identify any questions that have: incorrect answers, ambiguous options, factual errors, or poor wording.

Questions to review:
{json.dumps(section_json, indent=2)}

Return the same JSON structure with corrections applied. Fix any errors found. Return ONLY valid JSON, no explanation text."""


class AIGeneratorService:

    def __init__(self):
        api_key = os.environ.get('ANTHROPIC_API_KEY', '')
        self._client = anthropic.Anthropic(api_key=api_key) if api_key else None
        # Accumulated Claude token usage for the current call (for credit metering).
        self.last_usage = {'input_tokens': 0, 'output_tokens': 0}

    def _add_usage(self, message):
        try:
            self.last_usage['input_tokens'] += int(getattr(message.usage, 'input_tokens', 0) or 0)
            self.last_usage['output_tokens'] += int(getattr(message.usage, 'output_tokens', 0) or 0)
        except Exception:
            pass

    def generate_paper(self, exam_type: str, subjects: list, difficulty: str, total_marks: int) -> dict:
        if not self._client:
            return self._mock_paper(exam_type, subjects, total_marks)

        prompt = _build_generation_prompt(exam_type, subjects, difficulty, total_marks)
        message = self._client.messages.create(
            model=HAIKU_MODEL,
            max_tokens=8192,
            messages=[{"role": "user", "content": prompt}]
        )
        content = message.content[0].text
        paper_data = _loads_lenient(content)

        flagged_sections = self._flag_risky_sections(paper_data)
        if flagged_sections:
            paper_data = self._crosscheck_with_sonnet(paper_data, flagged_sections, exam_type)

        return paper_data

    def _flag_risky_sections(self, paper_data: dict) -> list:
        risky = []
        for section in paper_data.get("sections", []):
            subject = section.get("subject", "")
            if subject in ["Physics", "Mathematics"]:
                risky.append(section)
        return risky

    def _crosscheck_with_sonnet(self, paper_data: dict, flagged_sections: list, exam_type: str) -> dict:
        for i, section in enumerate(paper_data.get("sections", [])):
            if section in flagged_sections:
                prompt = _build_crosscheck_prompt({**section, "exam_type": exam_type}, section.get("subject"))
                message = self._client.messages.create(
                    model=SONNET_MODEL,
                    max_tokens=4096,
                    messages=[{"role": "user", "content": prompt}]
                )
                corrected = _loads_lenient(message.content[0].text)
                paper_data["sections"][i] = corrected
        return paper_data

    # Max questions per single API call — keeps output tokens well under limit
    _BATCH_SIZE = 10
    # Seconds to wait between batches to stay under 10k output tokens/minute
    _INTER_BATCH_DELAY = 6

    def generate_questions(self, exam: str, subject: str, topic: str, q_type: str,
                           difficulty: str, bloom: str, count: int) -> list:
        self.last_usage = {'input_tokens': 0, 'output_tokens': 0}
        if not self._client:
            return self._mock_questions(exam, subject, topic, q_type, difficulty, bloom, count)

        if count <= self._BATCH_SIZE:
            return self._generate_batch(exam, subject, topic, q_type, difficulty, bloom, count)

        results = []
        remaining = count
        while remaining > 0:
            batch = min(remaining, self._BATCH_SIZE)
            if results:
                time.sleep(self._INTER_BATCH_DELAY)
            results.extend(self._generate_batch(exam, subject, topic, q_type, difficulty, bloom, batch))
            remaining -= batch
        return results

    # Max characters of source text sent to the model in one parse pass.
    _PARSE_CHAR_LIMIT = 28000

    def parse_paper(self, raw_text: str, exam: str = '', images: dict = None) -> dict:
        """Extract structured questions from the raw text of an uploaded paper.

        `images` maps `[[IMG:rId]]` markers (present in the text in reading order)
        to data URLs; after parsing, each question keeps its image as image_svg.
        """
        images = images or {}
        self.last_usage = {'input_tokens': 0, 'output_tokens': 0}
        text = (raw_text or '').strip()
        if not text:
            return {'questions': [], 'meta': {}}
        if not self._client:
            return {'questions': [], 'meta': {'title': ''}}

        truncated = len(text) > self._PARSE_CHAR_LIMIT
        if truncated:
            text = text[:self._PARSE_CHAR_LIMIT]

        prompt = f"""You are given the raw text extracted from a question paper. Extract EVERY question into structured JSON.

{_LATEX_MATH_HINT}

Return ONLY a JSON object (no markdown, no extra text):
{{
  "title": "the paper/exam title if present, else ''",
  "questions": [
    {{
      "exam": "{exam or 'General'}",
      "subject": "best-guess subject for this question",
      "topic": "best-guess topic or 'General'",
      "q_type": "MCQ | Numerical | Short Answer | Long Answer | Fill in Blank",
      "difficulty": "Easy|Medium|Hard|HOTS",
      "bloom": "Remember|Understand|Apply|Analyze|Evaluate|Create",
      "marks": 1,
      "text": "the full question text, with LaTeX math as $...$",
      "options": [{{"text":"option text","correct":false}}] ,
      "explanation": ""
    }}
  ]
}}

Rules:
- Use "options" ONLY for multiple-choice questions; otherwise set it to null.
- If the correct MCQ option is not indicated in the source, set every option's "correct" to false.
- Read marks from brackets like [2] or "(3 marks)"; default to 1 if absent.
- Keep each question's text complete and verbatim where possible; convert equations to LaTeX.
- Skip headers, instructions, and page furniture — extract questions only.
- The text may contain image markers like [[IMG:rId7]] (figures/diagrams). Keep each marker INSIDE the "text" of the question it belongs to, exactly as written.

SOURCE TEXT:
\"\"\"
{text}
\"\"\""""

        message = self._client.messages.create(
            model=HAIKU_MODEL,
            max_tokens=32000,   # long papers (40+ Q) need a large output budget
            messages=[{"role": "user", "content": prompt}],
        )
        self._add_usage(message)
        # max_tokens cut-off → the JSON is incomplete; we salvage what's complete.
        cut_off = getattr(message, 'stop_reason', None) == 'max_tokens'

        raw = (message.content[0].text or "").strip()
        logger.info("parse_paper: %d chars, stop=%s, usage=%s",
                    len(raw), getattr(message, 'stop_reason', '?'), self.last_usage)

        # The model may wrap JSON in ```fences``` or add prose — extract the JSON
        # object (or array) substring before parsing.
        obj_s, obj_e = raw.find("{"), raw.rfind("}")
        arr_s, arr_e = raw.find("["), raw.rfind("]")
        if obj_s != -1 and obj_e > obj_s and (arr_s == -1 or obj_s < arr_s):
            candidate = raw[obj_s:obj_e + 1]
        elif arr_s != -1 and arr_e > arr_s:
            candidate = raw[arr_s:arr_e + 1]
        else:
            candidate = raw

        data = None
        if not cut_off:
            for attempt in (
                lambda: _loads_lenient(candidate),
                lambda: json.loads(candidate),
                lambda: json.loads(re.sub(r',\s*([}\]])', r'\1', candidate)),  # drop trailing commas
            ):
                try:
                    data = attempt()
                    break
                except Exception:
                    continue

        title = ''
        if isinstance(data, dict):
            title = data.get('title', '') or ''
            questions = data.get('questions', []) or []
        elif isinstance(data, list):
            questions = data
        else:
            # Whole-document parse failed or was cut off — salvage every complete
            # question object from the (partial) array. Skip the leading title obj.
            objs = _salvage_objects(raw)
            questions = [o for o in objs if 'text' in o] or objs
            if cut_off:
                truncated = True
            logger.warning("parse_paper: salvaged %d questions (cut_off=%s)", len(questions), cut_off)

        if not questions:
            logger.warning("parse_paper: 0 questions. Raw head: %r", raw[:600])
        # Normalise + tag LaTeX, mirroring generation output. Inline images: keep
        # every [[IMG:rId]] marker in the text but renumber them per-question to a
        # clean sequence ([[IMG:1]], [[IMG:2]], …) with a matching base64 map.
        for q in questions:
            if q.get('q_type') not in ('MCQ', 'Image Based'):
                q['options'] = None
            if images:
                # Renumber [[IMG:rId]] markers across BOTH the question text and its
                # options into one shared per-question sequence with a base64 map.
                seq = {}        # "1" -> dataUrl, in reading order within this question
                def _renum(m):
                    rid = m.group(1)
                    if rid not in images:
                        return ' '   # unresolved (e.g. WMF not converted) → drop marker
                    n = str(len(seq) + 1)
                    seq[n] = images[rid]
                    # Tall images are figures/diagrams (block); short ones are inline
                    # equations. The renderer sizes them accordingly.
                    tag = 'FIG' if _img_is_block(images[rid]) else 'IMG'
                    return f' [[{tag}:{n}]] '

                def _clean(s):
                    if not s or '[[IMG:' not in s:
                        return s
                    return re.sub(r'\s{2,}', ' ', re.sub(r'\s*\[\[IMG:([^\]]+)\]\]\s*', _renum, s)).strip()

                q['text'] = _clean(q.get('text') or '')
                if isinstance(q.get('options'), list):
                    for opt in q['options']:
                        if isinstance(opt, dict):
                            opt['text'] = _clean(opt.get('text') or '')
                if seq:
                    q['images'] = seq
        self._tag_latex(questions)
        return {'questions': questions, 'meta': {'title': title}, 'truncated': truncated}

    def _generate_batch(self, exam: str, subject: str, topic: str, q_type: str,
                        difficulty: str, bloom: str, count: int, _retry: int = 0) -> list:
        is_image_based = q_type == "Image Based"

        if q_type in ("MCQ", "Image Based"):
            options_instruction = (
                '"options": [{"text": "Option A text", "correct": true}, '
                '{"text": "Option B text", "correct": false}, '
                '{"text": "Option C text", "correct": false}, '
                '{"text": "Option D text", "correct": false}],'
            )
        else:
            options_instruction = '"options": null,'

        # For image-based questions, AI produces a diagram_schema — NOT raw SVG.
        # The deterministic rendering engine converts this to SVG after generation.
        if is_image_based:
            image_field = '"diagram_schema": { /* pick ONE schema from the supported list below */ },'
            diagram_hint = _DIAGRAM_SCHEMA_HINT
        else:
            image_field = '"diagram_schema": null,'
            diagram_hint = ""

        diff_instruction = "" if difficulty == "Mixed" else f"Difficulty: {difficulty}."
        bloom_instruction = "" if bloom == "Mixed" else f"Bloom's level: {bloom}."
        type_note = (
            "These are diagram/figure-based MCQs. Each question MUST include a diagram_schema "
            "that precisely describes the diagram the student is looking at. "
            "Choose the diagram type that best matches the question's physics/chemistry/math content."
            if is_image_based else ""
        )

        prompt = f"""Generate exactly {count} {"MCQ" if is_image_based else q_type} questions for the {exam} exam.
Subject: {subject}
Topic: {topic or 'General'}
{diff_instruction} {bloom_instruction}
{type_note}
{_LATEX_MATH_HINT}
{diagram_hint}

Return ONLY a valid JSON array with no markdown or extra text. Each element:
{{
  "exam": "{exam}",
  "subject": "{subject}",
  "topic": "{topic or 'General'}",
  "q_type": "{q_type}",
  "difficulty": "Easy|Medium|Hard|HOTS",
  "bloom": "Remember|Understand|Apply|Analyze|Evaluate|Create",
  "marks": 4,
  "text": "Question text with LaTeX math e.g. 'A body of mass $m = 2\\\\text{{ kg}}$ accelerates at $a = 5\\\\text{{ m/s}}^2$.'",
  {image_field}
  {options_instruction}
  "explanation": "One sentence explanation"
}}

Return exactly {count} questions as a JSON array. Keep explanations concise (one sentence).
For diagram_schema, fill in real numeric values that make sense for the question topic — do not use placeholders."""

        try:
            message = self._client.messages.create(
                model=HAIKU_MODEL,
                max_tokens=8192,
                messages=[{"role": "user", "content": prompt}]
            )
            self._add_usage(message)
            questions = self._parse_questions_response(message.content[0].text.strip())

            # Render diagram schemas deterministically — no AI image generation
            if is_image_based:
                for q in questions:
                    q['image_svg'] = self._render_diagram_schema(
                        q.get('diagram_schema'),
                        fallback_text=q.get('text', ''),
                        subject=subject,
                    )

            # Tag questions that contain LaTeX math notation
            self._tag_latex(questions)

            return questions
        except anthropic.RateLimitError:
            if _retry >= 4:
                raise
            wait = (2 ** _retry) * 15
            time.sleep(wait)
            return self._generate_batch(exam, subject, topic, q_type, difficulty, bloom, count, _retry + 1)
        except anthropic.APIStatusError as e:
            if e.status_code == 529:
                raise RuntimeError("AI service is currently overloaded. Please wait a moment and try again.") from e
            raise

    @staticmethod
    def _render_diagram_schema(schema: dict, fallback_text: str = "", subject: str = "") -> str | None:
        """
        Render an AI-generated diagram_schema using the deterministic STEM rendering engine.
        Returns SVG string on success, None on failure (caller stores null in image_svg).
        Never calls AI for SVG generation — geometry is always computed programmatically.
        """
        if not schema or not isinstance(schema, dict):
            return None

        try:
            from diagrams.service.dispatcher import dispatch_render
            # save_files=True — saves SVG/PNG to media/ so frontend can reference by URL.
            # Falls back gracefully if file system is unavailable.
            _, result = dispatch_render(schema, save_files=True)
            if result.success:
                logger.debug(
                    "STEM render OK: %s/%s in %dms",
                    schema.get("diagram_type"), schema.get("subtype"), result.render_time_ms,
                )
                return result.svg_content
            else:
                logger.warning(
                    "STEM render failed for %s/%s: %s",
                    schema.get("diagram_type"), schema.get("subtype"), result.error[:200],
                )
                return None
        except Exception as exc:
            logger.exception("Unexpected error in STEM renderer: %s", exc)
            return None

    @staticmethod
    def _tag_latex(questions: list) -> None:
        """
        Set has_latex=True on any question dict whose text or options contain
        $...$ / $$...$$ math delimiters.  Mutates in-place; never raises.
        """
        try:
            from latex.service.latexservice import has_math as _has_math
        except Exception:
            return

        for q in questions:
            text = q.get("text", "") or ""
            opts = q.get("options") or []
            flag = _has_math(text) or any(
                _has_math(o.get("text", "") if isinstance(o, dict) else str(o))
                for o in opts
            )
            q["has_latex"] = flag

    @staticmethod
    def _parse_questions_response(raw: str) -> list:
        # Strip markdown code fences
        if raw.startswith("```"):
            start = raw.find("[")
            end = raw.rfind("]")
            if start != -1 and end != -1:
                raw = raw[start:end + 1]
        elif not raw.startswith("["):
            # Find the JSON array anywhere in the response
            start = raw.find("[")
            end = raw.rfind("]")
            if start != -1 and end != -1:
                raw = raw[start:end + 1]
        return _loads_lenient(raw)

    # Default diagram schemas used for mock (no-API) mode, keyed by subject
    _MOCK_DIAGRAM_SCHEMAS = {
        "Physics": {
            "diagram_type": "physics", "subtype": "inclined_plane",
            "params": {"angle": 37, "forces": ["mg", "N", "f"], "block_label": "m"},
        },
        "Chemistry": {
            "diagram_type": "chemistry", "subtype": "reaction_coordinate_graph",
            "params": {"reactant_energy": 0, "product_energy": -40, "activation_energy": 80},
        },
        "Mathematics": {
            "diagram_type": "mathematics", "subtype": "function_graph",
            "params": {"functions": [{"expression": "x**2 - 4", "label": "f(x)=x²-4", "x_range": [-4, 4]}]},
        },
        "default": {
            "diagram_type": "physics", "subtype": "free_body_diagram",
            "params": {
                "object": {"shape": "square", "label": "m"},
                "forces": [{"label": "mg", "direction_deg": 270}, {"label": "N", "direction_deg": 90}],
            },
        },
    }

    def _mock_questions(self, exam: str, subject: str, topic: str, q_type: str,
                        difficulty: str, bloom: str, count: int) -> list:
        questions = []
        for i in range(count):
            q = {
                "exam": exam,
                "subject": subject,
                "topic": topic or "General",
                "q_type": q_type,
                "difficulty": difficulty if difficulty != "Mixed" else "Medium",
                "bloom": bloom if bloom != "Mixed" else "Apply",
                "marks": 4,
                "text": f"[{subject}] Sample {q_type} question {i + 1} for {exam}.",
                "options": None,
                "explanation": "Sample explanation.",
                "diagram_schema": None,
                "image_svg": None,
            }
            if q_type in ("MCQ", "Image Based"):
                q["options"] = [
                    {"text": "Option A", "correct": True},
                    {"text": "Option B", "correct": False},
                    {"text": "Option C", "correct": False},
                    {"text": "Option D", "correct": False},
                ]
            if q_type == "Image Based":
                schema = self._MOCK_DIAGRAM_SCHEMAS.get(subject, self._MOCK_DIAGRAM_SCHEMAS["default"])
                q["diagram_schema"] = schema
                q["image_svg"] = self._render_diagram_schema(schema, subject=subject)
            questions.append(q)
        return questions

    def _mock_paper(self, exam_type: str, subjects: list, total_marks: int) -> dict:
        config = EXAM_CONFIGS.get(exam_type, EXAM_CONFIGS["NEET"])
        sections = []
        for sec_conf in config["sections"]:
            subject = sec_conf["subject"]
            if subjects and subject not in subjects:
                continue
            questions = []
            for i in range(1, sec_conf["questions"] + 1):
                questions.append({
                    "number": i,
                    "text": f"[{subject}] Sample question {i} for {exam_type}?",
                    "options": [
                        "A) Option A", "B) Option B", "C) Option C", "D) Option D"
                    ],
                    "correct_answer": "A",
                    "marks": sec_conf["marks_per_q"],
                    "negative_marks": sec_conf["negative"],
                    "topic": f"{subject} Topic {i}",
                    "explanation": "Sample explanation."
                })
            sections.append({"subject": subject, "questions": questions})
        return {"sections": sections, "total_marks": total_marks, "exam_type": exam_type}
