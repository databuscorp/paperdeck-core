from django.db import migrations

# (course_slug, subject_name, description)
SYS_SUBJECTS = [
    # ── NEET UG ──────────────────────────────────────────────────────────────
    ("neet-ug", "Physics", "Mechanics, thermodynamics, optics, electromagnetism, modern physics. Class 11–12 NCERT syllabus."),
    ("neet-ug", "Chemistry", "Physical, organic, and inorganic chemistry. Class 11–12 NCERT syllabus."),
    ("neet-ug", "Botany", "Plant physiology, plant anatomy, reproduction in plants, ecology, biodiversity. Class 11–12 NCERT."),
    ("neet-ug", "Zoology", "Animal physiology, genetics & evolution, human physiology, biotechnology, ecology. Class 11–12 NCERT."),

    # ── JEE Mains ────────────────────────────────────────────────────────────
    ("jee-mains", "Physics", "Mechanics, waves, thermodynamics, electrostatics, current electricity, magnetism, optics, modern physics."),
    ("jee-mains", "Chemistry", "Physical chemistry, organic chemistry, inorganic chemistry. Class 11–12 CBSE/NCERT."),
    ("jee-mains", "Mathematics", "Algebra, coordinate geometry, calculus, trigonometry, vectors, statistics, 3D geometry."),

    # ── JEE Advanced Paper 1 ─────────────────────────────────────────────────
    ("jee-advanced-paper-1", "Physics", "Advanced mechanics, electricity & magnetism, optics, modern physics. IIT JEE level."),
    ("jee-advanced-paper-1", "Chemistry", "Advanced physical, organic, and inorganic chemistry. IIT JEE level."),
    ("jee-advanced-paper-1", "Mathematics", "Advanced algebra, calculus, coordinate geometry, complex numbers, probability. IIT JEE level."),

    # ── JEE Advanced Paper 2 ─────────────────────────────────────────────────
    ("jee-advanced-paper-2", "Physics", "Advanced mechanics, thermodynamics, optics, nuclear physics. Matching and short-answer format."),
    ("jee-advanced-paper-2", "Chemistry", "Advanced organic reactions, coordination chemistry, electrochemistry. Matching and short-answer format."),
    ("jee-advanced-paper-2", "Mathematics", "Advanced calculus, vectors, matrices, probability. Matching and short-answer format."),

    # ── UPSC CSE Prelims Paper 1 ─────────────────────────────────────────────
    ("upsc-cse-prelims-paper-1", "History", "Ancient, medieval, and modern Indian history. Art & culture, freedom struggle."),
    ("upsc-cse-prelims-paper-1", "Geography", "Physical, Indian, and world geography. Climatology, oceanography, mapping."),
    ("upsc-cse-prelims-paper-1", "Indian Polity & Governance", "Constitution, political system, panchayati raj, public policy, rights issues."),
    ("upsc-cse-prelims-paper-1", "Economy", "Indian economy, planning, poverty, agriculture, national income, budget, banking."),
    ("upsc-cse-prelims-paper-1", "Environment & Ecology", "Biodiversity, climate change, environmental policy, conservation, sustainable development."),
    ("upsc-cse-prelims-paper-1", "Science & Technology", "Everyday science, developments in science & tech, space, IT, biotechnology."),
    ("upsc-cse-prelims-paper-1", "Current Affairs", "National and international events, government schemes, awards, sports, books."),

    # ── UPSC CSE Prelims Paper 2 (CSAT) ──────────────────────────────────────
    ("upsc-cse-prelims-paper-2", "Comprehension", "Reading comprehension passages — inferential, factual, and critical reasoning questions."),
    ("upsc-cse-prelims-paper-2", "Logical Reasoning & Analytical Ability", "Syllogisms, blood relations, seating arrangements, series, coding-decoding, analogies."),
    ("upsc-cse-prelims-paper-2", "Decision Making & Problem Solving", "Situational judgement, administrative scenarios, ethical dilemmas."),
    ("upsc-cse-prelims-paper-2", "Basic Numeracy & Data Interpretation", "Number system, percentages, ratio & proportion, simple/compound interest, tables, charts, graphs."),
    ("upsc-cse-prelims-paper-2", "General Mental Ability", "Verbal and non-verbal reasoning, direction sense, clock & calendar problems."),

    # ── SSC CGL Tier 1 ───────────────────────────────────────────────────────
    ("ssc-cgl", "General Intelligence & Reasoning", "Analogies, series, coding-decoding, matrix, Venn diagrams, classification, direction."),
    ("ssc-cgl", "General Awareness", "History, geography, polity, economy, science, current affairs, static GK."),
    ("ssc-cgl", "Quantitative Aptitude", "Number system, algebra, geometry, trigonometry, DI, percentages, profit & loss, time & work."),
    ("ssc-cgl", "English Language", "Reading comprehension, vocabulary, grammar, cloze test, error detection, sentence rearrangement."),

    # ── SSC CGL Tier 2 ───────────────────────────────────────────────────────
    ("ssc-cgl-tier-2", "Mathematical Abilities", "Advanced quantitative aptitude — algebra, geometry, mensuration, trigonometry, DI."),
    ("ssc-cgl-tier-2", "Reasoning & General Intelligence", "Advanced reasoning — puzzles, critical thinking, analytical ability."),
    ("ssc-cgl-tier-2", "English Language & Comprehension", "Advanced grammar, vocabulary, comprehension, one-word substitution, idioms & phrases."),
    ("ssc-cgl-tier-2", "General Awareness", "Current affairs, polity, economy, science & technology, history."),
    ("ssc-cgl-tier-2", "Computer Knowledge", "Basics of computer, MS Office, internet, networking fundamentals."),

    # ── CAT ──────────────────────────────────────────────────────────────────
    ("cat", "Verbal Ability & Reading Comprehension (VARC)", "RC passages, para-jumbles, para-summary, odd sentence out, vocabulary in context."),
    ("cat", "Data Interpretation & Logical Reasoning (DILR)", "Tables, bar graphs, pie charts, line graphs, caselets, arrangements, binary logic, games."),
    ("cat", "Quantitative Ability (QA)", "Arithmetic, algebra, geometry, modern maths, number system, progressions."),

    # ── XAT ──────────────────────────────────────────────────────────────────
    ("xat", "Verbal & Logical Ability (VALR)", "Reading comprehension, vocabulary, critical reasoning, logical puzzles, para-completion."),
    ("xat", "Decision Making", "Case-based situational questions testing business acumen and analytical decision-making."),
    ("xat", "Quantitative Ability & Data Interpretation", "Arithmetic, algebra, geometry, data interpretation from charts and tables."),
    ("xat", "General Knowledge", "Business, economy, current events, world affairs, static GK."),

    # ── CLAT UG ──────────────────────────────────────────────────────────────
    ("clat", "English Language", "Comprehension passages, grammar correction, vocabulary, inference-based questions."),
    ("clat", "Current Affairs & General Knowledge", "Legal and non-legal current events, static GK, government schemes, awards."),
    ("clat", "Legal Reasoning", "Legal principles applied to fact patterns. No prior legal knowledge required."),
    ("clat", "Logical Reasoning", "Analogies, logical sequences, argument and premise analysis, inference."),
    ("clat", "Quantitative Techniques", "Class 10-level maths — ratios, percentages, graphs, data interpretation."),

    # ── CLAT PG ──────────────────────────────────────────────────────────────
    ("clat-pg", "Constitutional Law", "Fundamental rights, DPSP, constitutional history, judicial review, amendment process."),
    ("clat-pg", "Jurisprudence", "Theories of law, legal reasoning, sources of law, schools of jurisprudence."),
    ("clat-pg", "Administrative Law", "Delegated legislation, natural justice, judicial control, liability of the state."),
    ("clat-pg", "Law of Torts", "Negligence, strict liability, defamation, nuisance, remedies."),
    ("clat-pg", "Contract & Specific Relief", "Essentials of contract, void agreements, breach, remedies, specific performance."),
    ("clat-pg", "Criminal Law", "Indian Penal Code provisions, general exceptions, criminal procedure."),
    ("clat-pg", "International Law", "Treaties, sources, state sovereignty, UN system, human rights law."),

    # ── GATE CS ──────────────────────────────────────────────────────────────
    ("gate-cs", "Engineering Mathematics", "Discrete mathematics, linear algebra, calculus, probability & statistics."),
    ("gate-cs", "Digital Logic", "Boolean algebra, combinational & sequential circuits, minimization."),
    ("gate-cs", "Computer Organization & Architecture", "Machine instructions, ALU, memory hierarchy, I/O, pipelining."),
    ("gate-cs", "Programming & Data Structures", "C programming, arrays, stacks, queues, linked lists, trees, graphs."),
    ("gate-cs", "Algorithms", "Complexity analysis, sorting, searching, dynamic programming, greedy, graph algorithms."),
    ("gate-cs", "Theory of Computation", "Regular languages, CFG, pushdown automata, Turing machines, decidability."),
    ("gate-cs", "Compiler Design", "Lexical analysis, parsing, syntax-directed translation, code generation & optimization."),
    ("gate-cs", "Operating Systems", "Processes, threads, scheduling, memory management, file systems, deadlocks."),
    ("gate-cs", "Databases", "ER model, relational model, SQL, normalization, transactions, concurrency control."),
    ("gate-cs", "Computer Networks", "OSI & TCP/IP model, data link, IP addressing, routing, transport & application layer protocols."),

    # ── GATE ECE ─────────────────────────────────────────────────────────────
    ("gate-ece", "Engineering Mathematics", "Linear algebra, calculus, differential equations, complex variables, probability & statistics, numerical methods."),
    ("gate-ece", "Networks, Signals & Systems", "Network theorems, two-port networks, signal representation, LTI systems, Fourier & Laplace transforms."),
    ("gate-ece", "Electronic Devices", "PN junction, BJT, MOSFET characteristics, diode circuits."),
    ("gate-ece", "Analog Circuits", "Amplifiers, feedback, oscillators, operational amplifiers, filters."),
    ("gate-ece", "Digital Circuits", "Logic gates, combinational & sequential circuits, A/D and D/A converters."),
    ("gate-ece", "Control Systems", "Transfer functions, Bode & root locus plots, stability, compensators."),
    ("gate-ece", "Communications", "AM/FM modulation, digital modulation, noise, information theory, multiple access."),
    ("gate-ece", "Electromagnetics", "Maxwell's equations, transmission lines, waveguides, antennas."),

    # ── GATE ME ──────────────────────────────────────────────────────────────
    ("gate-me", "Engineering Mathematics", "Linear algebra, calculus, differential equations, probability & statistics, numerical methods."),
    ("gate-me", "Applied Mechanics & Design", "Statics, dynamics, mechanics of materials, machine design, vibrations."),
    ("gate-me", "Fluid Mechanics & Thermal Sciences", "Fluid statics & dynamics, heat transfer, thermodynamics, power & refrigeration cycles."),
    ("gate-me", "Materials Science", "Structure of materials, phase diagrams, heat treatment, mechanical properties."),
    ("gate-me", "Manufacturing & Industrial Engineering", "Metal casting, joining, machining, metrology, production planning, operations research."),

    # ── GATE Civil ───────────────────────────────────────────────────────────
    ("gate-civil", "Engineering Mathematics", "Linear algebra, calculus, ODEs, probability & statistics, numerical methods."),
    ("gate-civil", "Structural Engineering", "Structural analysis, steel structures, concrete structures, geotechnical engineering, foundation design."),
    ("gate-civil", "Geotechnical Engineering", "Soil classification, seepage, consolidation, shear strength, slope stability, foundations."),
    ("gate-civil", "Water Resources Engineering", "Fluid mechanics, hydrology, irrigation engineering, hydraulic structures."),
    ("gate-civil", "Environmental Engineering", "Water supply, wastewater treatment, air & noise pollution, solid waste management."),
    ("gate-civil", "Transportation Engineering", "Highway design, pavement, traffic engineering, railways, airports."),
    ("gate-civil", "Surveying", "Levelling, traversing, tacheometry, remote sensing, GIS."),

    # ── GATE EE ──────────────────────────────────────────────────────────────
    ("gate-ee", "Engineering Mathematics", "Linear algebra, calculus, ODEs, complex variables, probability & statistics, numerical methods."),
    ("gate-ee", "Electric Circuits", "Network theorems, transient and steady-state analysis, two-port networks."),
    ("gate-ee", "Electromagnetic Fields", "Coulomb's law, Gauss's law, Faraday's law, Maxwell's equations."),
    ("gate-ee", "Signals & Systems", "LTI systems, Fourier series/transform, Laplace transform, Z-transform."),
    ("gate-ee", "Electrical Machines", "DC machines, transformers, induction machines, synchronous machines."),
    ("gate-ee", "Power Systems", "Load flow, fault analysis, stability, protection, HVDC."),
    ("gate-ee", "Control Systems", "Transfer functions, root locus, Bode plots, stability, compensator design."),
    ("gate-ee", "Power Electronics", "Rectifiers, inverters, choppers, AC voltage controllers, drive systems."),
    ("gate-ee", "Analog & Digital Electronics", "Diodes, BJT, MOSFET, op-amps, logic gates, number systems."),

    # ── NEET PG ──────────────────────────────────────────────────────────────
    ("neet-pg", "Preclinical Sciences", "Anatomy, Physiology, Biochemistry — foundation subjects from MBBS first year."),
    ("neet-pg", "Pathology", "General pathology, systemic pathology, haematology, clinical pathology."),
    ("neet-pg", "Pharmacology", "General pharmacology, CNS, CVS, ANS, antimicrobials, chemotherapy."),
    ("neet-pg", "Microbiology", "Bacteriology, virology, mycology, parasitology, immunology."),
    ("neet-pg", "Forensic Medicine & Toxicology", "Medical jurisprudence, toxicology, postmortem, IPC sections."),
    ("neet-pg", "Community Medicine (PSM)", "Epidemiology, biostatistics, national health programmes, occupational health, environment."),
    ("neet-pg", "Medicine & Allied Specialties", "General medicine, dermatology, psychiatry, radiology, anaesthesia."),
    ("neet-pg", "Surgery & Allied Specialties", "General surgery, orthopaedics, ophthalmology, ENT."),
    ("neet-pg", "Obstetrics & Gynaecology", "Obstetrics, gynaecology, reproductive medicine."),
    ("neet-pg", "Paediatrics", "Neonatology, growth & development, paediatric diseases, immunisation schedule."),

    # ── CUET UG ──────────────────────────────────────────────────────────────
    ("cuet-ug", "English (Language)", "Reading comprehension, vocabulary, grammar, verbal ability."),
    ("cuet-ug", "General Test", "General knowledge, current affairs, general mental ability, numerical ability, quantitative reasoning."),
    ("cuet-ug", "Domain Subjects", "Subject-specific paper chosen by candidate — Physics, Chemistry, Biology, Mathematics, History, Political Science, Economics, etc."),

    # ── CUET PG ──────────────────────────────────────────────────────────────
    ("cuet-pg", "English Comprehension", "Reading comprehension passages, grammar, and verbal ability."),
    ("cuet-pg", "Domain-Specific Subject", "Candidate's chosen postgraduate discipline — covers UG-level syllabus of that subject."),
    ("cuet-pg", "General Awareness", "Current affairs, static GK, science & technology, national/international events."),

    # ── SNAP ─────────────────────────────────────────────────────────────────
    ("snap", "General English", "Reading comprehension, verbal reasoning, verbal ability, grammar, vocabulary."),
    ("snap", "Analytical & Logical Reasoning", "Logical sequences, blood relations, codebreaking, seating arrangements, critical reasoning."),
    ("snap", "Quantitative, Data Interpretation & Data Sufficiency", "Arithmetic, algebra, geometry, data interpretation from tables and charts."),

    # ── NMAT ─────────────────────────────────────────────────────────────────
    ("nmat", "Language Skills", "Reading comprehension, verbal ability, grammar, vocabulary, sentence correction."),
    ("nmat", "Quantitative Skills", "Arithmetic, algebra, geometry, data interpretation, data sufficiency."),
    ("nmat", "Logical Reasoning", "Deductive reasoning, critical reasoning, data arrangements, analytical puzzles."),

    # ── IIFT ─────────────────────────────────────────────────────────────────
    ("iift", "English Grammar & Reading Comprehension", "RC passages, grammar, vocabulary, verbal reasoning."),
    ("iift", "General Knowledge & Awareness", "Business GK, current affairs, trade & economy, world events, static GK."),
    ("iift", "Logical Reasoning & Data Interpretation", "Analytical puzzles, data sets, graphs, tables, case-based DI."),
    ("iift", "Quantitative Analysis", "Arithmetic, algebra, geometry, number system, modern maths."),

    # ── TISSNET ──────────────────────────────────────────────────────────────
    ("tissnet", "English Proficiency", "Reading comprehension, grammar, vocabulary, verbal ability."),
    ("tissnet", "Mathematics & Logical Reasoning", "Arithmetic, data interpretation, logical sequences, analytical reasoning."),
    ("tissnet", "General Awareness", "Current affairs, social issues, Indian constitution, TISS-related themes."),

    # ── CMAT ─────────────────────────────────────────────────────────────────
    ("cmat", "Quantitative Techniques & Data Interpretation", "Arithmetic, algebra, geometry, DI from tables, graphs, and charts."),
    ("cmat", "Logical Reasoning", "Analytical puzzles, syllogisms, coding-decoding, critical reasoning."),
    ("cmat", "Language Comprehension", "RC passages, grammar, vocabulary, para-jumbles, sentence correction."),
    ("cmat", "General Awareness", "Current affairs, business, economy, science & technology, static GK."),
    ("cmat", "Innovation & Entrepreneurship", "Concepts of innovation, startup ecosystem, business models, entrepreneurship theory."),

    # ── MAT ──────────────────────────────────────────────────────────────────
    ("mat", "Language Comprehension", "RC passages, vocabulary, verbal reasoning, grammar, para-jumbles."),
    ("mat", "Intelligence & Critical Reasoning", "Analogies, classification, series, coding-decoding, critical reasoning."),
    ("mat", "Data Analysis & Sufficiency", "Tables, bar & line graphs, pie charts, data sufficiency statements."),
    ("mat", "Mathematical Skills", "Arithmetic, algebra, geometry, trigonometry, number system."),
    ("mat", "Indian & Global Environment", "Current affairs, business GK, world events, economy, static GK."),

    # ── GMAT ─────────────────────────────────────────────────────────────────
    ("gmat", "Analytical Writing Assessment", "Issue analysis essay — critical thinking and communication of ideas."),
    ("gmat", "Integrated Reasoning", "Multi-source reasoning, table analysis, graphics interpretation, two-part analysis."),
    ("gmat", "Quantitative Reasoning", "Problem solving and data sufficiency — arithmetic, algebra, geometry."),
    ("gmat", "Verbal Reasoning", "Reading comprehension, critical reasoning, sentence correction."),

    # ── GRE ──────────────────────────────────────────────────────────────────
    ("gre", "Analytical Writing", "Issue task and argument task essays — evaluate complex ideas and arguments."),
    ("gre", "Verbal Reasoning", "Reading comprehension, text completion, sentence equivalence."),
    ("gre", "Quantitative Reasoning", "Arithmetic, algebra, geometry, data analysis — problem solving and comparison."),
]


def seed_sys_subjects(apps, schema_editor):
    Subject = apps.get_model('subjects', 'Subject')
    Course = apps.get_model('courses', 'Course')

    course_map = {
        c.slug: c
        for c in Course.objects.filter(is_sys=True)
    }

    for (slug, name, description) in SYS_SUBJECTS:
        course = course_map.get(slug)
        if not course:
            continue
        Subject.objects.get_or_create(
            course=course,
            name=name,
            defaults={
                'description': description,
                'org': None,
                'created_by': None,
                'is_sys': True,
            }
        )


def remove_sys_subjects(apps, schema_editor):
    Subject = apps.get_model('subjects', 'Subject')
    Subject.objects.filter(is_sys=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('subjects', '0003_add_org_created_by_is_sys'),
        ('courses', '0006_seed_sys_courses'),
    ]

    operations = [
        migrations.RunPython(seed_sys_subjects, remove_sys_subjects),
    ]
