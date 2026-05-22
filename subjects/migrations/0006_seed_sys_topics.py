from django.db import migrations

# (course_slug, subject_name, topic_name, description, [(chapter_name, chapter_desc), ...])
SYS_TOPICS = [
    # ── NEET UG · Physics ────────────────────────────────────────────────────
    ("neet-ug", "Physics", "Kinematics", "Motion equations, projectile motion, relative velocity.", [
        ("Motion in a Straight Line", "Uniform/non-uniform motion, equations of motion, graphs."),
        ("Motion in a Plane", "Vectors, projectile motion, uniform circular motion."),
    ]),
    ("neet-ug", "Physics", "Laws of Motion", "Newton's three laws, friction, circular dynamics.", [
        ("Newton's Laws of Motion", "Inertia, momentum, impulse, free-body diagrams."),
        ("Work, Energy and Power", "Work-energy theorem, conservative forces, power."),
        ("System of Particles & Rotational Motion", "Centre of mass, torque, angular momentum, MOI."),
    ]),
    ("neet-ug", "Physics", "Gravitation", "Universal law, orbital motion, escape velocity, Kepler's laws.", []),
    ("neet-ug", "Physics", "Properties of Matter", "Elasticity, viscosity, surface tension, Bernoulli's theorem.", []),
    ("neet-ug", "Physics", "Thermodynamics & Kinetic Theory", "Laws of thermodynamics, ideal gas, heat engines.", [
        ("Thermal Properties of Matter", "Temperature scales, calorimetry, heat transfer modes."),
        ("Thermodynamics", "Zeroth, first, second law; Carnot engine; entropy."),
        ("Kinetic Theory of Gases", "Postulates, pressure, temperature, degrees of freedom."),
    ]),
    ("neet-ug", "Physics", "Oscillations & Waves", "SHM, damping, wave motion, sound, Doppler effect.", [
        ("Oscillations (SHM)", "Displacement, velocity, energy, spring-mass, pendulum."),
        ("Waves", "Transverse/longitudinal, superposition, standing waves, beats."),
    ]),
    ("neet-ug", "Physics", "Electrostatics", "Coulomb's law, electric field, potential, capacitors.", [
        ("Electric Charges and Fields", "Coulomb's law, field lines, Gauss's law, dipole."),
        ("Electrostatic Potential and Capacitance", "Potential, potential energy, capacitors, dielectrics."),
    ]),
    ("neet-ug", "Physics", "Current Electricity", "Ohm's law, Kirchhoff's laws, Wheatstone bridge, potentiometer.", []),
    ("neet-ug", "Physics", "Magnetism", "Biot-Savart, Ampere's law, Earth's magnetism, magnetic materials.", [
        ("Moving Charges and Magnetism", "Lorentz force, cyclotron, solenoid, toroid."),
        ("Magnetism and Matter", "Magnetic dipole, para/dia/ferromagnetism."),
    ]),
    ("neet-ug", "Physics", "Electromagnetic Induction & AC", "Faraday's law, Lenz's law, inductance, AC circuits.", [
        ("Electromagnetic Induction", "Faraday's law, Lenz's law, self/mutual inductance."),
        ("Alternating Current", "RMS values, LC/LCR circuits, resonance, transformers."),
    ]),
    ("neet-ug", "Physics", "Electromagnetic Waves", "Maxwell's equations, EM spectrum, characteristics.", []),
    ("neet-ug", "Physics", "Optics", "Reflection, refraction, lenses, wave optics.", [
        ("Ray Optics and Optical Instruments", "Mirrors, lenses, prism, microscope, telescope."),
        ("Wave Optics", "Huygens' principle, interference, diffraction, polarisation."),
    ]),
    ("neet-ug", "Physics", "Modern Physics", "Dual nature, atomic models, nuclear physics, semiconductors.", [
        ("Dual Nature of Radiation and Matter", "Photoelectric effect, de Broglie wavelength."),
        ("Atoms", "Rutherford/Bohr model, hydrogen spectrum."),
        ("Nuclei", "Binding energy, radioactivity, nuclear reactions."),
        ("Semiconductor Devices", "p-n junction, diode, transistor, logic gates."),
    ]),

    # ── NEET UG · Chemistry ──────────────────────────────────────────────────
    ("neet-ug", "Chemistry", "Basic Concepts & Atomic Structure", "Mole concept, stoichiometry, Bohr model, quantum numbers.", [
        ("Some Basic Concepts of Chemistry", "Mole concept, empirical/molecular formula, limiting reagent."),
        ("Structure of Atom", "Bohr model, quantum numbers, orbitals, electronic configuration."),
    ]),
    ("neet-ug", "Chemistry", "Chemical Bonding & Molecular Structure", "Ionic, covalent bonds, VSEPR, hybridisation, MO theory.", []),
    ("neet-ug", "Chemistry", "States of Matter", "Ideal gas laws, kinetic theory, van der Waals, liquid state, solids.", []),
    ("neet-ug", "Chemistry", "Thermodynamics", "Enthalpy, entropy, Gibbs energy, Hess's law, spontaneity.", []),
    ("neet-ug", "Chemistry", "Equilibrium", "Kp/Kc, Le Chatelier's principle, acids, bases, pH, buffers, Ksp.", [
        ("Chemical Equilibrium", "Equilibrium constants, homogeneous/heterogeneous equilibria."),
        ("Ionic Equilibrium", "Strong/weak acids/bases, pH, buffer, solubility product."),
    ]),
    ("neet-ug", "Chemistry", "Redox & Electrochemistry", "Oxidation states, galvanic cells, electrolysis, Nernst equation.", []),
    ("neet-ug", "Chemistry", "Chemical Kinetics", "Rate laws, order, Arrhenius equation, activation energy, catalysis.", []),
    ("neet-ug", "Chemistry", "p-Block Elements", "Groups 13–18: properties, important compounds, reactions.", []),
    ("neet-ug", "Chemistry", "d & f Block and Coordination", "Transition metals, coordination compounds, ligands, isomerism.", []),
    ("neet-ug", "Chemistry", "Organic Chemistry — Basics", "IUPAC nomenclature, isomerism, reaction mechanisms, hydrocarbons.", [
        ("Basic Principles & Nomenclature", "IUPAC rules, isomerism, inductive/resonance effects."),
        ("Hydrocarbons", "Alkanes, alkenes, alkynes, benzene reactions."),
    ]),
    ("neet-ug", "Chemistry", "Organic Chemistry — Functional Groups", "Alcohols, carbonyls, amines, biomolecules, polymers.", [
        ("Alcohols, Phenols and Ethers", "Preparation, properties, reactions, tests."),
        ("Aldehydes, Ketones and Carboxylic Acids", "Nucleophilic addition, aldol condensation, oxidation."),
        ("Amines", "Classification, preparation, basicity, diazonium salts."),
        ("Biomolecules", "Carbohydrates, proteins, nucleic acids, vitamins, enzymes."),
        ("Polymers", "Natural/synthetic polymers, classification, polymerisation."),
    ]),

    # ── NEET UG · Botany ─────────────────────────────────────────────────────
    ("neet-ug", "Botany", "Diversity in the Living World", "Five-kingdom classification, algae, bryophytes, pteridophytes, gymnosperms, angiosperms.", [
        ("The Living World", "Biodiversity, taxonomy, binomial nomenclature."),
        ("Biological Classification", "Kingdoms: Monera, Protista, Fungi; viruses and lichens."),
        ("Plant Kingdom", "Algae, bryophytes, pteridophytes, gymnosperms, angiosperms."),
    ]),
    ("neet-ug", "Botany", "Morphology of Flowering Plants", "Root, stem, leaf, flower, fruit, seed morphology and modifications.", []),
    ("neet-ug", "Botany", "Anatomy of Flowering Plants", "Meristems, permanent tissues, anatomy of dicot/monocot organs.", []),
    ("neet-ug", "Botany", "Cell Biology & Division", "Cell organelles, cell cycle, mitosis, meiosis.", [
        ("Cell: The Unit of Life", "Prokaryotic vs eukaryotic, organelles, nucleus, cell wall."),
        ("Cell Cycle and Cell Division", "Interphase, mitosis, meiosis, significance."),
    ]),
    ("neet-ug", "Botany", "Plant Physiology", "Transport, photosynthesis, respiration, growth regulators.", [
        ("Transport in Plants", "Osmosis, xylem transport, phloem translocation, mineral nutrition."),
        ("Photosynthesis", "Light reactions, Calvin cycle, C3/C4, photorespiration."),
        ("Respiration in Plants", "Glycolysis, Krebs cycle, oxidative phosphorylation."),
        ("Plant Growth and Development", "Auxins, gibberellins, cytokinins, ABA, ethylene; photoperiodism."),
    ]),
    ("neet-ug", "Botany", "Reproduction in Plants", "Asexual, sexual reproduction, fertilisation, seed formation.", [
        ("Reproduction in Organisms", "Binary fission, spore formation, vegetative propagation."),
        ("Sexual Reproduction in Flowering Plants", "Pollination, double fertilisation, embryo development."),
    ]),
    ("neet-ug", "Botany", "Genetics & Evolution", "Mendel's laws, chromosomal theory, DNA, evolution.", [
        ("Principles of Inheritance and Variation", "Mendel's laws, linkage, crossing over, sex-linked traits."),
        ("Molecular Basis of Inheritance", "DNA replication, transcription, translation, genetic code."),
        ("Evolution", "Darwinism, modern synthesis, Hardy-Weinberg, speciation."),
    ]),
    ("neet-ug", "Botany", "Ecology", "Ecosystems, biodiversity, environmental issues.", [
        ("Organisms and Populations", "Ecological interactions, population growth models."),
        ("Ecosystem", "Food chains, energy flow, nutrient cycling, productivity."),
        ("Biodiversity and Conservation", "Hotspots, threatened species, in situ/ex situ conservation."),
        ("Environmental Issues", "Pollution, greenhouse effect, ozone depletion, biomagnification."),
    ]),

    # ── NEET UG · Zoology ────────────────────────────────────────────────────
    ("neet-ug", "Zoology", "Animal Kingdom", "Classification based on body organisation, symmetry, coelom, segmentation.", []),
    ("neet-ug", "Zoology", "Structural Organisation in Animals", "Morphology and anatomy of earthworm, cockroach, frog.", []),
    ("neet-ug", "Zoology", "Human Physiology", "Digestion, respiration, circulation, excretion, locomotion, neural and chemical coordination.", [
        ("Digestion and Absorption", "GI tract, enzymes, absorption, disorders."),
        ("Breathing and Exchange of Gases", "Mechanism of breathing, transport of O2/CO2."),
        ("Body Fluids and Circulation", "Blood composition, cardiac cycle, ECG, disorders."),
        ("Excretory Products", "Nephron, urine formation, osmoregulation."),
        ("Locomotion and Movement", "Skeletal and muscular system, joints."),
        ("Neural Control and Coordination", "Neuron, action potential, brain, spinal cord."),
        ("Chemical Coordination", "Endocrine glands, hormones, feedback mechanisms."),
    ]),
    ("neet-ug", "Zoology", "Reproduction", "Human reproductive system, fertilisation, embryology, reproductive health.", [
        ("Human Reproduction", "Gametogenesis, fertilisation, implantation, development."),
        ("Reproductive Health", "Contraception, STDs, infertility, ART."),
    ]),
    ("neet-ug", "Zoology", "Genetics & Evolution", "Chromosomal basis, genetic disorders, molecular genetics, evolution.", []),
    ("neet-ug", "Zoology", "Biotechnology", "Recombinant DNA technology, applications in medicine and agriculture.", [
        ("Biotechnology: Principles and Processes", "Restriction enzymes, vectors, PCR, gel electrophoresis."),
        ("Biotechnology and Its Applications", "GM crops, insulin, gene therapy, biopiracy."),
    ]),

    # ── JEE Mains · Physics ──────────────────────────────────────────────────
    ("jee-mains", "Physics", "Kinematics & Laws of Motion", "Equations of motion, projectile, Newton's laws, friction.", [
        ("Kinematics", "Displacement, velocity, acceleration, equations of motion, relative motion."),
        ("Laws of Motion", "Free-body diagrams, Newton's laws, friction, circular motion dynamics."),
    ]),
    ("jee-mains", "Physics", "Work, Energy, Power & Gravitation", "Energy conservation, orbital motion, Kepler's laws.", []),
    ("jee-mains", "Physics", "Rotational Motion", "MOI, torque, angular momentum, rolling, conservation.", []),
    ("jee-mains", "Physics", "Properties of Matter & SHM", "Elasticity, viscosity, SHM, damped and forced oscillations.", []),
    ("jee-mains", "Physics", "Thermodynamics & Waves", "Laws of thermodynamics, heat engines, wave motion, Doppler.", []),
    ("jee-mains", "Physics", "Electrostatics & Current Electricity", "Fields, potential, capacitors, circuits, Kirchhoff's laws.", [
        ("Electrostatics", "Coulomb's law, Gauss's law, potential, capacitors."),
        ("Current Electricity", "Ohm's law, Kirchhoff's laws, Wheatstone bridge, meters."),
    ]),
    ("jee-mains", "Physics", "Magnetism & Electromagnetic Induction", "Magnetic force, Biot-Savart, Faraday's law, AC circuits.", []),
    ("jee-mains", "Physics", "Optics", "Ray optics, lenses, mirrors, wave optics, interference, diffraction.", []),
    ("jee-mains", "Physics", "Modern Physics", "Photoelectric effect, Bohr model, nuclear physics, semiconductors.", []),

    # ── JEE Mains · Chemistry ────────────────────────────────────────────────
    ("jee-mains", "Chemistry", "Physical Chemistry", "Mole concept, thermodynamics, equilibrium, kinetics, solutions, electrochemistry.", [
        ("Atomic Structure & Chemical Bonding", "Bohr model, quantum numbers, hybridisation, VSEPR."),
        ("Thermodynamics & Equilibrium", "Enthalpy, entropy, Kp/Kc, Le Chatelier's principle."),
        ("Electrochemistry & Chemical Kinetics", "Cell EMF, Nernst equation, rate laws, Arrhenius."),
        ("Solutions & Surface Chemistry", "Colligative properties, colloids, adsorption, catalysis."),
    ]),
    ("jee-mains", "Chemistry", "Inorganic Chemistry", "Periodic trends, s/p/d/f-blocks, coordination compounds.", [
        ("Periodic Table & s-Block", "Periodicity trends, alkali and alkaline earth metals."),
        ("p-Block Elements", "Groups 13–18, important compounds, reactions."),
        ("d & f Block & Coordination Chemistry", "Transition metals, Werner's theory, isomerism, CFT."),
    ]),
    ("jee-mains", "Chemistry", "Organic Chemistry", "Nomenclature, mechanisms, functional groups, named reactions.", [
        ("Basic Organic Chemistry & Hydrocarbons", "IUPAC, isomerism, alkanes, alkenes, alkynes, arenes."),
        ("Haloalkanes, Alcohols, Ethers", "SN1/SN2/E1/E2 reactions, preparation, properties."),
        ("Carbonyl Compounds & Amines", "Aldehydes, ketones, carboxylic acids, amines, diazonium."),
        ("Biomolecules & Polymers", "Carbohydrates, proteins, nucleic acids, natural/synthetic polymers."),
    ]),

    # ── JEE Mains · Mathematics ──────────────────────────────────────────────
    ("jee-mains", "Mathematics", "Algebra", "Complex numbers, matrices, sequences, binomial theorem, P&C.", [
        ("Complex Numbers & Quadratics", "Argand plane, polar form, roots of quadratic equations."),
        ("Sequences and Series", "AP, GP, AGP, special series, sum to n terms."),
        ("Matrices and Determinants", "Operations, inverse, rank, system of equations."),
        ("Permutations, Combinations & Binomial Theorem", "Counting, nCr, general term, middle term."),
    ]),
    ("jee-mains", "Mathematics", "Coordinate Geometry", "Straight lines, circles, conic sections, 3D geometry.", [
        ("Straight Lines & Circles", "Forms of line, distance, tangent, chord."),
        ("Conic Sections", "Parabola, ellipse, hyperbola — standard forms, tangent, normal."),
        ("3D Geometry", "Direction cosines, lines, planes, shortest distance."),
    ]),
    ("jee-mains", "Mathematics", "Calculus", "Limits, differentiation, integration, differential equations.", [
        ("Limits, Continuity and Differentiability", "Standard limits, L'Hopital, continuity, differentiability."),
        ("Differentiation & Applications", "Chain rule, parametric, maxima/minima, tangent/normal."),
        ("Integration", "Standard integrals, substitution, by parts, definite, area."),
        ("Differential Equations", "Separable, homogeneous, linear first-order ODE."),
    ]),
    ("jee-mains", "Mathematics", "Trigonometry", "Ratios, identities, inverse functions, equations, properties of triangles.", []),
    ("jee-mains", "Mathematics", "Vectors & 3D Geometry", "Vector algebra, dot/cross product, lines and planes.", []),
    ("jee-mains", "Mathematics", "Statistics & Probability", "Mean, median, mode, SD, probability, Bayes' theorem, distributions.", []),
    ("jee-mains", "Mathematics", "Sets, Relations & Functions", "Set operations, types of functions, inverse, composite functions.", []),

    # ── JEE Advanced Paper 1 ─────────────────────────────────────────────────
    ("jee-advanced-paper-1", "Physics", "Mechanics", "Advanced rigid-body dynamics, fluid mechanics, SHM at IIT level.", []),
    ("jee-advanced-paper-1", "Physics", "Electromagnetism", "Advanced E&M, self/mutual inductance, Maxwell's equations.", []),
    ("jee-advanced-paper-1", "Physics", "Optics & Modern Physics", "Wave optics, Bohr model, nuclear decay, semiconductors.", []),
    ("jee-advanced-paper-1", "Physics", "Thermodynamics & Waves", "Carnot efficiency, entropy, wave superposition.", []),
    ("jee-advanced-paper-1", "Chemistry", "Physical Chemistry", "Advanced kinetics, electrochemistry, phase diagrams, colligative properties.", []),
    ("jee-advanced-paper-1", "Chemistry", "Inorganic Chemistry", "p-block reactions, coordination chemistry, qualitative analysis.", []),
    ("jee-advanced-paper-1", "Chemistry", "Organic Chemistry", "Named reactions, stereochemistry, multi-step synthesis, mechanisms.", []),
    ("jee-advanced-paper-1", "Mathematics", "Algebra & Trigonometry", "Complex numbers, matrices, probability, trigonometric equations.", []),
    ("jee-advanced-paper-1", "Mathematics", "Calculus", "Advanced integration, differential equations, area under curves.", []),
    ("jee-advanced-paper-1", "Mathematics", "Coordinate Geometry & Vectors", "Conic sections, 3D geometry, vector proofs.", []),

    # ── JEE Advanced Paper 2 ─────────────────────────────────────────────────
    ("jee-advanced-paper-2", "Physics", "Mechanics", "Matching/short-answer — rotational dynamics, fluid mechanics.", []),
    ("jee-advanced-paper-2", "Physics", "Electromagnetism", "Matching/short-answer — advanced E&M problems.", []),
    ("jee-advanced-paper-2", "Physics", "Optics & Modern Physics", "Nuclear physics, wave optics, semiconductor problems.", []),
    ("jee-advanced-paper-2", "Chemistry", "Physical Chemistry", "Thermodynamics, kinetics, electrochemistry — matching format.", []),
    ("jee-advanced-paper-2", "Chemistry", "Inorganic Chemistry", "Reaction types, coordination isomerism, analytical chemistry.", []),
    ("jee-advanced-paper-2", "Chemistry", "Organic Chemistry", "Multi-step synthesis, mechanism identification, stereochemistry.", []),
    ("jee-advanced-paper-2", "Mathematics", "Calculus & Differential Equations", "Advanced definite integrals, ODE applications.", []),
    ("jee-advanced-paper-2", "Mathematics", "Algebra & Coordinate Geometry", "Conics, complex numbers, matrices.", []),
    ("jee-advanced-paper-2", "Mathematics", "Vectors & 3D Geometry", "3D lines, planes, angle bisectors, vector equations.", []),

    # ── UPSC CSE Prelims Paper 1 · History ───────────────────────────────────
    ("upsc-cse-prelims-paper-1", "History", "Ancient India", "Harappan civilisation, Vedic age, Mauryas, Guptas, art & architecture.", [
        ("Prehistory & Harappan Civilisation", "Stone Age, Chalcolithic, Indus Valley cities, trade, decline."),
        ("Vedic Period & Mahajanapadas", "Early Vedic, Later Vedic, Buddhism, Jainism, rise of states."),
        ("Mauryan Empire", "Chandragupta, Ashoka's Dhamma, administration, inscriptions."),
        ("Post-Mauryan & Gupta Age", "Sungas, Satavahanas, Kushanas, Gupta Golden Age, science."),
    ]),
    ("upsc-cse-prelims-paper-1", "History", "Medieval India", "Delhi Sultanate, Mughal Empire, Bhakti movement, regional kingdoms.", [
        ("Delhi Sultanate", "Slave, Khalji, Tughlaq dynasties; Iqta, revenue administration."),
        ("Mughal Empire", "Babur to Aurangzeb; mansabdari, land revenue, art, architecture."),
        ("Bhakti & Sufi Movements", "Kabir, Tukaram, Chaitanya, Sufism, socio-religious impact."),
    ]),
    ("upsc-cse-prelims-paper-1", "History", "Modern India & Freedom Struggle", "Colonial administration, reform movements, national movement, partition.", [
        ("British Conquest & Administration", "Battles, subsidiary alliance, revenue policies, drain theory."),
        ("Socio-Religious Reform Movements", "Brahmo Samaj, Arya Samaj, Aligarh, Ramakrishna Mission."),
        ("Early Nationalism & Swadeshi", "INC formation, moderates, extremists, partition of Bengal."),
        ("Gandhian Era", "Non-cooperation, Civil Disobedience, Quit India, parallel movements."),
        ("Towards Independence", "Cabinet Mission, partition plan, independence, integration."),
    ]),
    ("upsc-cse-prelims-paper-1", "History", "Art & Culture", "Painting, architecture, music, dance, UNESCO World Heritage sites.", []),

    # ── UPSC CSE Prelims Paper 1 · Geography ─────────────────────────────────
    ("upsc-cse-prelims-paper-1", "Geography", "Physical Geography", "Geomorphology, climatology, oceanography, biogeography.", [
        ("Geomorphology", "Plate tectonics, fold/fault mountains, volcanoes, rocks, landforms."),
        ("Climatology", "Atmospheric layers, pressure belts, wind systems, monsoon, climate types."),
        ("Oceanography", "Ocean currents, tides, El Nino, coral reefs, marine resources."),
    ]),
    ("upsc-cse-prelims-paper-1", "Geography", "Indian Geography", "Physical features, climate, drainage, agriculture, industry, population.", [
        ("Physical Features & Drainage", "Himalayas, peninsular plateau, plains, rivers, lakes."),
        ("Climate, Soils & Vegetation", "Monsoon, rainfall distribution, soil types, forest types."),
        ("Agriculture & Industry", "Major crops, irrigation, industrial regions, mineral resources."),
        ("Population & Urbanisation", "Census data, demographic trends, metro cities, migration."),
    ]),
    ("upsc-cse-prelims-paper-1", "Geography", "World Geography", "World physical features, continents, climate regions, economic geography.", []),

    # ── UPSC CSE Prelims Paper 1 · Polity ────────────────────────────────────
    ("upsc-cse-prelims-paper-1", "Indian Polity & Governance", "Indian Constitution", "Framing, Preamble, fundamental rights, DPSP, amendments.", [
        ("Salient Features & Preamble", "Federal features, parliamentary system, secularism, objectives."),
        ("Fundamental Rights (Art 12–35)", "Categories, enforceability, exceptions, writs."),
        ("DPSP & Fundamental Duties", "Articles 36–51, Art 51A, directive vs justiciable."),
    ]),
    ("upsc-cse-prelims-paper-1", "Indian Polity & Governance", "Union Government", "President, PM, Parliament, Supreme Court, judicial review.", [
        ("President & Vice President", "Election, powers, position, impeachment."),
        ("Parliament", "Rajya Sabha/Lok Sabha composition, legislative procedure, sessions."),
        ("Judiciary", "SC jurisdiction, original/appellate/writ, judicial activism."),
    ]),
    ("upsc-cse-prelims-paper-1", "Indian Polity & Governance", "State Government & Local Bodies", "Governor, State Legislature, Panchayati Raj, urban local bodies.", []),
    ("upsc-cse-prelims-paper-1", "Indian Polity & Governance", "Constitutional & Statutory Bodies", "Election Commission, CAG, UPSC, Finance Commission, NITI Aayog.", []),

    # ── UPSC CSE Prelims Paper 1 · Economy ───────────────────────────────────
    ("upsc-cse-prelims-paper-1", "Economy", "National Income & Planning", "GDP, GNP, NNP, planning history, NITI Aayog, economic reforms.", []),
    ("upsc-cse-prelims-paper-1", "Economy", "Money, Banking & Monetary Policy", "RBI functions, monetary policy tools, banking system, financial markets.", []),
    ("upsc-cse-prelims-paper-1", "Economy", "Fiscal Policy & Government Budget", "Tax types, fiscal deficit, Budget terminologies, FRBM Act.", []),
    ("upsc-cse-prelims-paper-1", "Economy", "Agriculture & Food Security", "Green revolution, MSP, APMC, food security schemes, land reforms.", []),
    ("upsc-cse-prelims-paper-1", "Economy", "Industry & External Sector", "Industrial policy, FDI, WTO, BoP, exchange rate, exports.", []),
    ("upsc-cse-prelims-paper-1", "Economy", "Social Sector & Poverty", "Poverty measurement, social schemes (MGNREGS, PM-KISAN etc.), HDI.", []),

    # ── UPSC CSE Prelims Paper 1 · Environment ───────────────────────────────
    ("upsc-cse-prelims-paper-1", "Environment & Ecology", "Ecology Basics", "Ecosystem structure, food chains, energy flow, nutrient cycles, succession.", []),
    ("upsc-cse-prelims-paper-1", "Environment & Ecology", "Biodiversity", "Types, hotspots, IUCN categories, protected areas, CBD, conventions.", []),
    ("upsc-cse-prelims-paper-1", "Environment & Ecology", "Climate Change", "Greenhouse gases, IPCC, Paris Agreement, carbon credits, UNFCCC.", []),
    ("upsc-cse-prelims-paper-1", "Environment & Ecology", "Pollution & Waste", "Air, water, soil, noise, radioactive pollution; solid/hazardous waste.", []),
    ("upsc-cse-prelims-paper-1", "Environment & Ecology", "Environmental Laws & Bodies", "EPA 1986, Wildlife Act, Forest Act, NGT, MoEFCC, EIA.", []),

    # ── UPSC CSE Prelims Paper 1 · Science & Technology ──────────────────────
    ("upsc-cse-prelims-paper-1", "Science & Technology", "Space Technology", "ISRO missions, launch vehicles, satellites, planetary exploration, NAVIC.", []),
    ("upsc-cse-prelims-paper-1", "Science & Technology", "Defence & Nuclear Technology", "DRDO projects, nuclear doctrine, missile systems, INS, indigenous defence.", []),
    ("upsc-cse-prelims-paper-1", "Science & Technology", "Biotechnology & Health", "GM crops, biopharmaceuticals, CRISPR, vaccines, One Health approach.", []),
    ("upsc-cse-prelims-paper-1", "Science & Technology", "IT, AI & Cyber Security", "AI/ML applications, 5G, digital India, cybersecurity, data protection.", []),

    # ── UPSC CSE Prelims Paper 1 · Current Affairs ───────────────────────────
    ("upsc-cse-prelims-paper-1", "Current Affairs", "National Developments", "Government schemes, policy changes, awards, appointments.", []),
    ("upsc-cse-prelims-paper-1", "Current Affairs", "International Events", "Bilateral relations, multilateral summits, international organisations.", []),

    # ── UPSC CSAT Paper 2 ────────────────────────────────────────────────────
    ("upsc-cse-prelims-paper-2", "Comprehension", "Reading Comprehension Techniques", "Main idea, inference, tone, vocabulary in context.", []),
    ("upsc-cse-prelims-paper-2", "Comprehension", "Critical Reading", "Implicit assumptions, author's argument, weakening/strengthening.", []),
    ("upsc-cse-prelims-paper-2", "Logical Reasoning & Analytical Ability", "Statements & Conclusions", "Syllogisms, course of action, assumptions, inferences.", []),
    ("upsc-cse-prelims-paper-2", "Logical Reasoning & Analytical Ability", "Puzzles & Arrangements", "Seating arrangements, scheduling, blood relations, direction sense.", []),
    ("upsc-cse-prelims-paper-2", "Logical Reasoning & Analytical Ability", "Series & Analogies", "Number series, letter series, analogy, odd one out.", []),
    ("upsc-cse-prelims-paper-2", "Decision Making & Problem Solving", "Administrative Scenarios", "Prioritising actions, resource allocation, stakeholder management.", []),
    ("upsc-cse-prelims-paper-2", "Decision Making & Problem Solving", "Ethical Dilemmas", "Situational judgement, public interest vs personal interest.", []),
    ("upsc-cse-prelims-paper-2", "Basic Numeracy & Data Interpretation", "Arithmetic", "Percentages, ratio & proportion, averages, profit-loss, time-speed-distance.", []),
    ("upsc-cse-prelims-paper-2", "Basic Numeracy & Data Interpretation", "Data Interpretation", "Tables, bar graphs, pie charts, line graphs — multi-step calculations.", []),
    ("upsc-cse-prelims-paper-2", "General Mental Ability", "Verbal Reasoning", "Analogies, classification, series, critical reasoning.", []),
    ("upsc-cse-prelims-paper-2", "General Mental Ability", "Non-verbal Reasoning", "Mirror images, paper folding, matrix patterns, embedded figures.", []),

    # ── SSC CGL Tier 1 ───────────────────────────────────────────────────────
    ("ssc-cgl", "General Intelligence & Reasoning", "Verbal Reasoning", "Analogies, classification, series, coding-decoding, blood relations.", []),
    ("ssc-cgl", "General Intelligence & Reasoning", "Non-verbal Reasoning", "Pattern series, mirror images, paper folding, embedded figures.", []),
    ("ssc-cgl", "General Intelligence & Reasoning", "Logical Deduction", "Syllogisms, input-output, statements and conclusions.", []),
    ("ssc-cgl", "General Intelligence & Reasoning", "Miscellaneous", "Venn diagrams, mathematical operations, direction sense, missing numbers.", []),
    ("ssc-cgl", "General Awareness", "Indian Polity & History", "Constitution, government, ancient/medieval/modern history.", []),
    ("ssc-cgl", "General Awareness", "Science & Technology", "Physics, chemistry, biology basics; space, IT developments.", []),
    ("ssc-cgl", "General Awareness", "Economy & Geography", "Indian economy basics, world and Indian geography.", []),
    ("ssc-cgl", "General Awareness", "Current Affairs", "National/international events, awards, sports, summits.", []),
    ("ssc-cgl", "Quantitative Aptitude", "Arithmetic", "Number system, HCF/LCM, percentage, profit-loss, ratio, time-work, speed-distance.", []),
    ("ssc-cgl", "Quantitative Aptitude", "Algebra & Geometry", "Algebraic identities, equations, triangles, circles, quadrilaterals.", []),
    ("ssc-cgl", "Quantitative Aptitude", "Mensuration & Trigonometry", "2D/3D areas and volumes, trigonometric ratios, heights and distances.", []),
    ("ssc-cgl", "Quantitative Aptitude", "Data Interpretation", "Tables, bar graphs, pie charts — percentage-based calculations.", []),
    ("ssc-cgl", "English Language", "Grammar", "Tenses, voice, narration, subject-verb agreement, articles, prepositions.", []),
    ("ssc-cgl", "English Language", "Vocabulary & Comprehension", "Synonyms, antonyms, idioms, one-word substitution, reading comprehension.", []),
    ("ssc-cgl", "English Language", "Sentence Skills", "Error detection, sentence improvement, cloze test, para-jumbles.", []),

    # ── SSC CGL Tier 2 ───────────────────────────────────────────────────────
    ("ssc-cgl-tier-2", "Mathematical Abilities", "Algebra & Trigonometry", "Advanced algebraic identities, trigonometric identities, heights and distances.", []),
    ("ssc-cgl-tier-2", "Mathematical Abilities", "Geometry & Mensuration", "Properties of triangles, quadrilaterals, circles; 2D and 3D mensuration.", []),
    ("ssc-cgl-tier-2", "Mathematical Abilities", "Arithmetic & DI", "Advanced ratio, percentage, interest, work-speed, data tables and charts.", []),
    ("ssc-cgl-tier-2", "Reasoning & General Intelligence", "Advanced Reasoning", "Critical thinking, decision-making, passage-based reasoning.", []),
    ("ssc-cgl-tier-2", "English Language & Comprehension", "Advanced Grammar", "Error spotting, sentence improvement, active/passive, direct/indirect.", []),
    ("ssc-cgl-tier-2", "English Language & Comprehension", "Reading & Writing", "Long RC passages, precise writing, essay, letter formats.", []),
    ("ssc-cgl-tier-2", "General Awareness", "Current Affairs & GK", "National/international events, polity, economy, science.", []),
    ("ssc-cgl-tier-2", "Computer Knowledge", "Computer Fundamentals", "Hardware, software, OS, MS Office, internet, networking, cybersecurity.", []),

    # ── CAT ──────────────────────────────────────────────────────────────────
    ("cat", "Verbal Ability & Reading Comprehension (VARC)", "Reading Comprehension", "Dense academic passages — factual, inferential, vocabulary, tone questions.", []),
    ("cat", "Verbal Ability & Reading Comprehension (VARC)", "Para Jumbles", "Logical ordering of 4–5 sentences; mandatory pairs; opening sentence identification.", []),
    ("cat", "Verbal Ability & Reading Comprehension (VARC)", "Para Summary & Odd Sentence Out", "Identify central theme of a paragraph; find the sentence that doesn't fit.", []),
    ("cat", "Data Interpretation & Logical Reasoning (DILR)", "Data Interpretation", "Tables, bar/line/pie charts, caselets — multi-step percentage and ratio calculations.", []),
    ("cat", "Data Interpretation & Logical Reasoning (DILR)", "Logical Reasoning Sets", "Seating arrangements, blood relations, scheduling, games & tournaments, binary logic.", []),
    ("cat", "Quantitative Ability (QA)", "Arithmetic", "Percentages, profit-loss, ratio, averages, time-work, TSD, mixtures, interests.", []),
    ("cat", "Quantitative Ability (QA)", "Algebra & Modern Maths", "Quadratics, functions, logarithm, progressions, P&C, probability, set theory.", []),
    ("cat", "Quantitative Ability (QA)", "Geometry & Mensuration", "Triangles, circles, quadrilaterals, 3D solids, coordinate geometry.", []),
    ("cat", "Quantitative Ability (QA)", "Number System", "Divisibility, factors, LCM/HCF, remainders, base systems, factorials.", []),

    # ── XAT ──────────────────────────────────────────────────────────────────
    ("xat", "Verbal & Logical Ability (VALR)", "Reading Comprehension", "Dense passages — abstract, philosophical, factual; inference and critical analysis.", []),
    ("xat", "Verbal & Logical Ability (VALR)", "Logical Reasoning", "Assumptions, inferences, strengthen/weaken, logical puzzles.", []),
    ("xat", "Decision Making", "Business Case Studies", "Situational judgement, resource allocation, stakeholder management.", []),
    ("xat", "Decision Making", "Ethical Dilemmas", "Value-based decision making, public vs private interest.", []),
    ("xat", "Quantitative Ability & Data Interpretation", "Quantitative Aptitude", "Arithmetic, algebra, geometry, modern maths — moderate to high difficulty.", []),
    ("xat", "Quantitative Ability & Data Interpretation", "Data Interpretation", "Complex multi-graph DI sets requiring multi-step calculations.", []),
    ("xat", "General Knowledge", "Business & Economy GK", "Indian and global business news, economic indicators, corporate events.", []),
    ("xat", "General Knowledge", "Static GK", "Geography, polity, science, awards, sports, international affairs.", []),

    # ── CLAT UG ──────────────────────────────────────────────────────────────
    ("clat", "English Language", "Reading Comprehension", "Passages with factual, inferential and vocabulary-based questions.", []),
    ("clat", "English Language", "Grammar & Writing", "Error correction, sentence improvement, para-jumbles.", []),
    ("clat", "Current Affairs & General Knowledge", "Legal Current Affairs", "Landmark SC/HC judgements, legislative changes, constitutional events.", []),
    ("clat", "Current Affairs & General Knowledge", "General Current Affairs", "National/international events, economy, environment, sports, awards.", []),
    ("clat", "Legal Reasoning", "Legal Principle Application", "Given principle + facts → conclusion; no prior legal knowledge needed.", []),
    ("clat", "Legal Reasoning", "Legal Aptitude", "Contract, tort, crime, family law — principle-based questions.", []),
    ("clat", "Logical Reasoning", "Critical Reasoning", "Strengthen/weaken, assumption identification, conclusion drawing.", []),
    ("clat", "Logical Reasoning", "Deductive Reasoning", "Syllogisms, analogies, series, classification, Venn diagrams.", []),
    ("clat", "Quantitative Techniques", "Arithmetic & Data Interpretation", "Ratio, percentage, graphs, tables — Class 10 level maths.", []),

    # ── CLAT PG ──────────────────────────────────────────────────────────────
    ("clat-pg", "Constitutional Law", "Fundamental Rights & DPSP", "Articles 12–51A, enforceability, balancing FR vs DPSP.", []),
    ("clat-pg", "Constitutional Law", "Constitutional Amendments & Basic Structure", "Article 368, Kesavananda Bharati doctrine, major amendments.", []),
    ("clat-pg", "Constitutional Law", "Federalism & Centre-State Relations", "Legislative, executive, financial relations, emergency provisions.", []),
    ("clat-pg", "Jurisprudence", "Nature and Sources of Law", "Natural law, legal positivism, sociological jurisprudence, realism.", []),
    ("clat-pg", "Jurisprudence", "Theories of Rights and Justice", "Rights theories, Rawls' justice, Dworkin, Hart-Fuller debate.", []),
    ("clat-pg", "Administrative Law", "Delegated Legislation & Judicial Review", "Sub-delegation, writs (certiorari, mandamus, prohibition), natural justice.", []),
    ("clat-pg", "Law of Torts", "General Principles", "Negligence, strict liability, nuisance, defamation, vicarious liability.", []),
    ("clat-pg", "Contract & Specific Relief", "Essentials & Breach", "Offer, acceptance, consideration, capacity, remedies, specific performance.", []),
    ("clat-pg", "Criminal Law", "General Exceptions & Major Offences", "IPC sections 76–106; murder, theft, robbery, assault, fraud.", []),
    ("clat-pg", "International Law", "Sources, Principles & Human Rights", "Treaties, customary IL, UDHR, ICCPR, ICESCR, regional mechanisms.", []),

    # ── GATE CS ──────────────────────────────────────────────────────────────
    ("gate-cs", "Engineering Mathematics", "Discrete Mathematics", "Set theory, logic, graph theory, combinatorics, recurrence relations.", [
        ("Set Theory, Relations & Functions", "Sets, relations, equivalence, partial order, functions."),
        ("Propositional & Predicate Logic", "Connectives, truth tables, tautology, inference rules."),
        ("Graph Theory", "Types of graphs, trees, Euler/Hamiltonian paths, planarity, colouring."),
        ("Combinatorics", "Counting principles, P&C, pigeonhole, inclusion-exclusion, generating functions."),
    ]),
    ("gate-cs", "Engineering Mathematics", "Linear Algebra", "Matrix operations, determinants, rank, eigenvalues, vector spaces.", []),
    ("gate-cs", "Engineering Mathematics", "Calculus & Probability", "Limits, differentiation, integration, mean/variance, distributions, Bayes.", []),
    ("gate-cs", "Digital Logic", "Boolean Algebra & Minimisation", "Boolean laws, K-map, Quine-McCluskey, SOP/POS forms.", []),
    ("gate-cs", "Digital Logic", "Combinational Circuits", "Multiplexers, decoders, encoders, adders, subtractors, comparators.", []),
    ("gate-cs", "Digital Logic", "Sequential Circuits", "Flip-flops (SR/JK/D/T), registers, counters, Moore/Mealy machines.", []),
    ("gate-cs", "Computer Organization & Architecture", "Instruction Set & ALU", "RISC/CISC, addressing modes, instruction formats, number representation.", []),
    ("gate-cs", "Computer Organization & Architecture", "Memory & Cache", "Memory hierarchy, cache mapping (direct/set-associative/fully), cache replacement.", []),
    ("gate-cs", "Computer Organization & Architecture", "Pipelining & I/O", "Pipeline stages/hazards, branch prediction, interrupts, DMA, I/O techniques.", []),
    ("gate-cs", "Programming & Data Structures", "Programming in C", "Pointers, arrays, structures, recursion, dynamic memory allocation.", []),
    ("gate-cs", "Programming & Data Structures", "Linear Data Structures", "Arrays, linked lists (singly/doubly/circular), stacks, queues, deque.", []),
    ("gate-cs", "Programming & Data Structures", "Trees & Graphs", "Binary tree, BST, AVL, heap, B-tree; graph representation, traversal.", []),
    ("gate-cs", "Algorithms", "Analysis of Algorithms", "Big-O notation, time/space complexity, recurrences, master theorem.", []),
    ("gate-cs", "Algorithms", "Sorting Algorithms", "Bubble, selection, insertion, merge, quick, heap, counting, radix sort.", []),
    ("gate-cs", "Algorithms", "Graph Algorithms", "BFS, DFS, Dijkstra, Bellman-Ford, Floyd-Warshall, Prim, Kruskal, Topological sort, SCC.", []),
    ("gate-cs", "Algorithms", "Dynamic Programming & Greedy", "LCS, LIS, 0-1 knapsack, matrix chain; activity selection, Huffman coding.", []),
    ("gate-cs", "Theory of Computation", "Finite Automata & Regular Languages", "DFA, NFA, ε-NFA, regular expressions, pumping lemma, minimisation.", []),
    ("gate-cs", "Theory of Computation", "Context-Free Languages", "CFG, CNF, GNF, PDA, CYK algorithm, pumping lemma for CFLs.", []),
    ("gate-cs", "Theory of Computation", "Turing Machines & Decidability", "TM variants, decidable/undecidable problems, reduction, Rice's theorem, Halting problem.", []),
    ("gate-cs", "Compiler Design", "Lexical & Syntax Analysis", "Regular expressions, DFA-based lexer, LL(1), LR(0), SLR, LALR parsers.", []),
    ("gate-cs", "Compiler Design", "Semantic Analysis & Code Generation", "SDT, three-address code, basic blocks, code optimisation, register allocation.", []),
    ("gate-cs", "Operating Systems", "Processes & Scheduling", "Process states, PCB, FCFS, SJF, Round Robin, Priority scheduling, Gantt charts.", []),
    ("gate-cs", "Operating Systems", "Synchronisation & Deadlock", "Race conditions, mutex, semaphores, monitors, deadlock conditions, banker's algorithm.", []),
    ("gate-cs", "Operating Systems", "Memory Management", "Paging, segmentation, virtual memory, page replacement (FIFO, LRU, Optimal, LFU).", []),
    ("gate-cs", "Operating Systems", "File Systems", "Directory structure, file allocation (contiguous, linked, indexed), FAT, i-node.", []),
    ("gate-cs", "Databases", "ER Model & Relational Algebra", "ER to relation mapping, relational algebra, relational calculus, integrity constraints.", []),
    ("gate-cs", "Databases", "SQL", "DDL, DML, joins, subqueries, aggregation, views, triggers, indexing (B+ tree).", []),
    ("gate-cs", "Databases", "Normalisation", "Functional dependencies, closure, 1NF–BCNF, lossless join, dependency preserving.", []),
    ("gate-cs", "Databases", "Transaction Management", "ACID, conflict serializability, 2PL, timestamp ordering, recovery.", []),
    ("gate-cs", "Computer Networks", "Data Link Layer", "Framing, error detection/correction (CRC, Hamming), flow control, CSMA/CD, MAC protocols.", []),
    ("gate-cs", "Computer Networks", "Network Layer", "IPv4/IPv6, subnetting, CIDR, routing algorithms, OSPF, BGP, NAT.", []),
    ("gate-cs", "Computer Networks", "Transport & Application Layer", "TCP (3-way handshake, congestion control), UDP, HTTP, DNS, SMTP, FTP, SSL/TLS.", []),

    # ── GATE ECE ─────────────────────────────────────────────────────────────
    ("gate-ece", "Engineering Mathematics", "Linear Algebra, Calculus & Complex Variables", "Matrix operations, ODEs, Fourier series, contour integration.", []),
    ("gate-ece", "Engineering Mathematics", "Probability & Numerical Methods", "Random variables, distributions, Newton-Raphson, numerical integration.", []),
    ("gate-ece", "Networks, Signals & Systems", "Network Analysis", "KVL/KCL, Thevenin/Norton, superposition, resonance, two-port networks.", []),
    ("gate-ece", "Networks, Signals & Systems", "Signals & LTI Systems", "CT/DT signals, convolution, CTFT, DTFT, DFT, Laplace, Z-transform.", []),
    ("gate-ece", "Electronic Devices", "Semiconductor Physics & PN Junction", "Energy bands, carriers, drift-diffusion, diode equation, Zener.", []),
    ("gate-ece", "Electronic Devices", "BJT & MOSFET", "Characteristics, biasing, small-signal models, CMOS basics.", []),
    ("gate-ece", "Analog Circuits", "Amplifiers & Feedback", "Common-emitter/source amplifiers, gain-bandwidth, feedback topologies.", []),
    ("gate-ece", "Analog Circuits", "Op-Amps & Oscillators", "Ideal/practical op-amp, inverting/non-inverting, integrator, differentiator, LC/RC oscillators.", []),
    ("gate-ece", "Digital Circuits", "Combinational & Sequential Design", "Logic minimisation, MUX/DEMUX, flip-flops, counters, registers, ADC/DAC.", []),
    ("gate-ece", "Control Systems", "Time & Frequency Domain", "Transfer function, time response specs, Bode plot, Nyquist, root locus, PID.", []),
    ("gate-ece", "Communications", "Analog Modulation", "AM (DSB/SSB/VSB), FM, PM, bandwidth, noise analysis, SNR.", []),
    ("gate-ece", "Communications", "Digital Communications", "PCM/DPCM, ASK/FSK/PSK/QAM, BER, matched filter, channel coding.", []),
    ("gate-ece", "Electromagnetics", "Static Fields", "Coulomb/Gauss/Ampere laws, Poisson/Laplace, boundary conditions.", []),
    ("gate-ece", "Electromagnetics", "EM Waves & Transmission Lines", "Maxwell's equations, plane wave propagation, transmission line theory, Smith chart, waveguides.", []),

    # ── GATE ME ──────────────────────────────────────────────────────────────
    ("gate-me", "Engineering Mathematics", "Linear Algebra, Calculus & Numerical Methods", "Matrix operations, ODEs, numerical integration, Newton-Raphson.", []),
    ("gate-me", "Applied Mechanics & Design", "Mechanics of Solids", "Stress-strain, bending moment, shear force, torsion, columns, Mohr's circle.", []),
    ("gate-me", "Applied Mechanics & Design", "Theory of Machines & Vibrations", "Kinematics of mechanisms, gear trains, flywheel, forced/free vibrations.", []),
    ("gate-me", "Applied Mechanics & Design", "Machine Design", "Fatigue, Mohr's circle, shafts, keys, couplings, bearings, springs, gears.", []),
    ("gate-me", "Fluid Mechanics & Thermal Sciences", "Fluid Mechanics", "Hydrostatics, Bernoulli, pipe flow, boundary layer, turbomachinery.", []),
    ("gate-me", "Fluid Mechanics & Thermal Sciences", "Heat Transfer", "Conduction (Fourier), convection (Newton's law), radiation, heat exchangers.", []),
    ("gate-me", "Fluid Mechanics & Thermal Sciences", "Thermodynamics", "Laws, properties of steam, Rankine, Otto, Diesel, Brayton cycles; refrigeration.", []),
    ("gate-me", "Materials Science", "Phase Diagrams & Heat Treatment", "Iron-carbon diagram, TTT, annealing, quenching, case hardening.", []),
    ("gate-me", "Manufacturing & Industrial Engineering", "Casting & Forming", "Sand casting, shell moulding, forging, rolling, extrusion, sheet metal.", []),
    ("gate-me", "Manufacturing & Industrial Engineering", "Machining & Metrology", "Turning, milling, grinding; cutting forces, tool life, limits/fits/tolerances.", []),
    ("gate-me", "Manufacturing & Industrial Engineering", "Industrial Engineering", "Work measurement, scheduling, inventory models, queuing, LP.", []),

    # ── GATE Civil ───────────────────────────────────────────────────────────
    ("gate-civil", "Engineering Mathematics", "Linear Algebra, Calculus & Numerical Methods", "Eigenvalues, ODEs, Newton-Raphson, numerical integration, statistics.", []),
    ("gate-civil", "Structural Engineering", "Structural Analysis", "Determinacy, trusses, beams, slope-deflection, moment distribution, influence lines.", []),
    ("gate-civil", "Structural Engineering", "RCC Design", "Limit state design — beams, slabs, columns, footings, IS 456:2000.", []),
    ("gate-civil", "Structural Engineering", "Steel Design", "Tension/compression members, beams, welded/bolted connections, IS 800.", []),
    ("gate-civil", "Geotechnical Engineering", "Soil Classification & Seepage", "Phase relations, Atterberg limits, IS classification, permeability, seepage.", []),
    ("gate-civil", "Geotechnical Engineering", "Consolidation, Shear Strength & Foundations", "Terzaghi's theory, Mohr-Coulomb, bearing capacity, pile foundation, slope stability.", []),
    ("gate-civil", "Water Resources Engineering", "Fluid Mechanics & Hydraulics", "Fluid properties, Bernoulli, pipe flow, open channel, hydraulic jumps, turbines.", []),
    ("gate-civil", "Water Resources Engineering", "Hydrology & Irrigation", "Rainfall-runoff, flood routing, groundwater, reservoir, irrigation systems.", []),
    ("gate-civil", "Environmental Engineering", "Water & Wastewater Treatment", "Coagulation, sedimentation, filtration, disinfection, BOD/COD, activated sludge.", []),
    ("gate-civil", "Transportation Engineering", "Highway & Traffic Engineering", "Geometric design, pavement design (flexible/rigid), traffic flow, IRC standards.", []),
    ("gate-civil", "Surveying", "Survey Methods", "Chain/compass/plane table/theodolite surveying, levelling, curves, photogrammetry, GPS.", []),

    # ── GATE EE ──────────────────────────────────────────────────────────────
    ("gate-ee", "Engineering Mathematics", "Linear Algebra & Calculus", "Eigenvalues, vector spaces, complex analysis, Fourier/Laplace transforms.", []),
    ("gate-ee", "Electric Circuits", "DC & AC Analysis", "KVL/KCL, superposition, Thevenin/Norton, resonance, two-port networks.", []),
    ("gate-ee", "Electromagnetic Fields", "Static & Dynamic Fields", "Coulomb/Gauss/Ampere/Faraday laws, Maxwell's equations, boundary conditions.", []),
    ("gate-ee", "Signals & Systems", "CT & DT Analysis", "Fourier series, Fourier/Laplace/Z-transforms, convolution, correlation.", []),
    ("gate-ee", "Electrical Machines", "DC Machines & Transformers", "DC generator/motor characteristics, losses, speed control; transformer equivalent circuit.", []),
    ("gate-ee", "Electrical Machines", "AC Machines", "Induction motor equivalent circuit, torque-slip, starting/speed control; synchronous generator.", []),
    ("gate-ee", "Power Systems", "Load Flow & Fault Analysis", "Gauss-Seidel, Newton-Raphson; symmetrical/unsymmetrical faults, bus impedance matrix.", []),
    ("gate-ee", "Power Systems", "Stability & Protection", "Equal area criterion, swing equation; relay types, CT/PT, circuit breakers.", []),
    ("gate-ee", "Control Systems", "Time & Frequency Domain", "Transfer function, Routh-Hurwitz, root locus, Bode/Nyquist, PID compensator design.", []),
    ("gate-ee", "Power Electronics", "Converters & Drives", "Rectifiers (1φ/3φ), DC-DC choppers, inverters, AC voltage controllers, electric drives.", []),
    ("gate-ee", "Analog & Digital Electronics", "Circuits & Logic", "BJT/MOSFET amplifiers, op-amps; Boolean algebra, combinational/sequential circuits, ADC/DAC.", []),

    # ── NEET PG ──────────────────────────────────────────────────────────────
    ("neet-pg", "Preclinical Sciences", "Anatomy", "Head & neck, thorax, abdomen, upper/lower limb anatomy; neuroanatomy.", []),
    ("neet-pg", "Preclinical Sciences", "Physiology", "CVS, respiratory, renal, endocrine, neurophysiology, muscle, GI physiology.", []),
    ("neet-pg", "Preclinical Sciences", "Biochemistry", "Carbohydrate/lipid/protein metabolism, enzymology, molecular biology, clinical biochemistry.", []),
    ("neet-pg", "Pathology", "General Pathology", "Cell injury, inflammation, repair/regeneration, neoplasia, haemodynamic disorders.", []),
    ("neet-pg", "Pathology", "Systemic Pathology", "CVS, respiratory, GI, liver, kidney, CNS, endocrine, haematopoietic pathology.", []),
    ("neet-pg", "Pharmacology", "General Pharmacology", "Pharmacokinetics (ADME), pharmacodynamics, drug interactions, adverse drug reactions.", []),
    ("neet-pg", "Pharmacology", "Systemic Pharmacology", "CNS, CVS, ANS, GI, antimicrobials, anticancer, anti-inflammatory, endocrine drugs.", []),
    ("neet-pg", "Microbiology", "Bacteriology", "Gram +/- bacteria, culture methods, virulence, clinically important pathogens.", []),
    ("neet-pg", "Microbiology", "Virology & Immunology", "DNA/RNA viruses (HIV, hepatitis, herpes); innate/adaptive immunity, vaccines.", []),
    ("neet-pg", "Forensic Medicine & Toxicology", "Medical Jurisprudence", "Death, post-mortem changes, wounds, sexual offences, dying declaration, MLC.", []),
    ("neet-pg", "Forensic Medicine & Toxicology", "Toxicology", "Corrosive, metallic, organic, insecticide poisons; treatment principles.", []),
    ("neet-pg", "Community Medicine (PSM)", "Epidemiology & Biostatistics", "Study designs, measures of disease frequency, screening tests, vital statistics.", []),
    ("neet-pg", "Community Medicine (PSM)", "National Health Programmes", "NHM, TB (NTEP), malaria, HIV, immunisation schedule, MCH, nutrition programmes.", []),
    ("neet-pg", "Medicine & Allied Specialties", "Clinical Medicine", "Cardiology, pulmonology, nephrology, neurology, haematology, endocrinology, rheumatology.", []),
    ("neet-pg", "Medicine & Allied Specialties", "Dermatology & Psychiatry", "Common skin disorders, STDs, classifications; psychiatric disorders, pharmacotherapy.", []),
    ("neet-pg", "Surgery & Allied Specialties", "General Surgery", "Trauma, acute abdomen, breast, thyroid, hernias, colorectal, vascular surgery.", []),
    ("neet-pg", "Surgery & Allied Specialties", "Orthopaedics & ENT", "Fractures, joint disorders, spine; ear/nose/throat anatomy, disorders, surgeries.", []),
    ("neet-pg", "Surgery & Allied Specialties", "Ophthalmology", "Refractive errors, glaucoma, cataract, retinal disorders, ocular trauma.", []),
    ("neet-pg", "Obstetrics & Gynaecology", "Obstetrics", "Normal/abnormal pregnancy, labour, puerperium, obstetric emergencies, antepartum haemorrhage.", []),
    ("neet-pg", "Obstetrics & Gynaecology", "Gynaecology", "Menstrual disorders, PCOS, infertility, contraception, gynaecologic cancers, STDs.", []),
    ("neet-pg", "Paediatrics", "Neonatology & Growth", "Newborn assessment, LBW, neonatal jaundice, growth charts, developmental milestones.", []),
    ("neet-pg", "Paediatrics", "Paediatric Diseases", "Malnutrition, infectious diseases, respiratory, cardiac, haematologic disorders in children.", []),

    # ── CUET UG ──────────────────────────────────────────────────────────────
    ("cuet-ug", "English (Language)", "Reading Comprehension", "Factual and literary passages — main idea, inference, vocabulary questions.", []),
    ("cuet-ug", "English (Language)", "Grammar & Vocabulary", "Tenses, voice, narration, word usage, synonyms, antonyms.", []),
    ("cuet-ug", "General Test", "General Knowledge & Current Affairs", "National/international events, government schemes, awards, appointments.", []),
    ("cuet-ug", "General Test", "Logical Reasoning & Numerical Ability", "Series, analogies, coding, percentages, ratio, DI — Class 12 level.", []),
    ("cuet-ug", "Domain Subjects", "Science Stream", "Physics, Chemistry, Biology, Mathematics at Class 12 NCERT level.", []),
    ("cuet-ug", "Domain Subjects", "Humanities & Commerce Stream", "History, Geography, Political Science, Economics, Accountancy, Business Studies.", []),

    # ── CUET PG ──────────────────────────────────────────────────────────────
    ("cuet-pg", "English Comprehension", "Reading Comprehension & Grammar", "Short passages, grammar, vocabulary, verbal ability.", []),
    ("cuet-pg", "Domain-Specific Subject", "Core Discipline Topics", "Complete UG-level syllabus of the chosen postgraduate discipline as per NTA.", []),
    ("cuet-pg", "General Awareness", "Current Affairs & Static GK", "National/international events, science, culture, awards, appointments.", []),

    # ── SNAP ─────────────────────────────────────────────────────────────────
    ("snap", "General English", "Reading Comprehension", "Passages with factual, inferential, and vocabulary questions.", []),
    ("snap", "General English", "Verbal Ability", "Sentence completion, error detection, synonyms, antonyms, para-jumbles.", []),
    ("snap", "Analytical & Logical Reasoning", "Analytical Reasoning", "Seating arrangements, blood relations, Venn diagrams, syllogisms.", []),
    ("snap", "Analytical & Logical Reasoning", "Logical Reasoning", "Binary logic, critical reasoning, input-output, coding-decoding.", []),
    ("snap", "Quantitative, Data Interpretation & Data Sufficiency", "Quantitative Aptitude", "Arithmetic, algebra, geometry, number theory — moderate difficulty.", []),
    ("snap", "Quantitative, Data Interpretation & Data Sufficiency", "Data Interpretation & Sufficiency", "Tables, pie charts, bar/line graphs, two-statement data sufficiency.", []),

    # ── NMAT ─────────────────────────────────────────────────────────────────
    ("nmat", "Language Skills", "Reading Comprehension", "Academic/business passages — main idea, inference, vocabulary.", []),
    ("nmat", "Language Skills", "Grammar & Vocabulary", "Sentence correction, fill-in-the-blanks, synonyms, antonyms.", []),
    ("nmat", "Quantitative Skills", "Arithmetic & Algebra", "Percentages, profit-loss, TSD, quadratics, functions — timed format.", []),
    ("nmat", "Quantitative Skills", "Data Interpretation", "Tables, bar/pie/line graphs, data sufficiency.", []),
    ("nmat", "Logical Reasoning", "Deductive & Inductive Reasoning", "Syllogisms, blood relations, series, pattern recognition.", []),
    ("nmat", "Logical Reasoning", "Analytical Puzzles", "Seating arrangements, scheduling, games and tournaments.", []),

    # ── IIFT ─────────────────────────────────────────────────────────────────
    ("iift", "English Grammar & Reading Comprehension", "Reading Comprehension", "Dense academic and business passages — inference and critical analysis.", []),
    ("iift", "English Grammar & Reading Comprehension", "Grammar & Vocabulary", "Error correction, sentence improvement, word usage, one-word substitution, idioms.", []),
    ("iift", "General Knowledge & Awareness", "Business & Trade GK", "Trade agreements, FDI, WTO, tariffs, business news, economic data.", []),
    ("iift", "General Knowledge & Awareness", "Static & Current GK", "History, geography, polity, science, awards, sports, international affairs.", []),
    ("iift", "Logical Reasoning & Data Interpretation", "Logical Reasoning", "Analytical puzzles, critical reasoning, binary logic, seating arrangements.", []),
    ("iift", "Logical Reasoning & Data Interpretation", "Data Interpretation", "Complex multi-graph DI sets requiring multi-step calculations.", []),
    ("iift", "Quantitative Analysis", "Arithmetic & Number Theory", "Percentages, profit-loss, ratio, TSD, time-work, number properties.", []),
    ("iift", "Quantitative Analysis", "Algebra, Geometry & Modern Maths", "Quadratics, functions, mensuration, P&C, probability, set theory.", []),

    # ── TISSNET ──────────────────────────────────────────────────────────────
    ("tissnet", "English Proficiency", "Reading Comprehension", "Short to medium passages — factual and critical questions.", []),
    ("tissnet", "English Proficiency", "Grammar & Vocabulary", "Error detection, fill-in-the-blanks, synonyms, antonyms, idioms.", []),
    ("tissnet", "Mathematics & Logical Reasoning", "Arithmetic & DI", "Basic arithmetic, percentages, ratios, data interpretation from charts.", []),
    ("tissnet", "Mathematics & Logical Reasoning", "Logical Reasoning", "Series, coding-decoding, blood relations, puzzles, analogies.", []),
    ("tissnet", "General Awareness", "Social Issues & Current Affairs", "Social sector, poverty, health, education, TISS research themes.", []),
    ("tissnet", "General Awareness", "National & International Events", "Government policies, international organisations, current affairs.", []),

    # ── CMAT ─────────────────────────────────────────────────────────────────
    ("cmat", "Quantitative Techniques & Data Interpretation", "Arithmetic", "Percentages, ratios, profit-loss, time-work, speed-distance, interest.", []),
    ("cmat", "Quantitative Techniques & Data Interpretation", "Data Interpretation", "Tables, bar/pie/line graphs — percentage and ratio based.", []),
    ("cmat", "Logical Reasoning", "Analytical Puzzles", "Seating arrangements, scheduling, blood relations, binary logic.", []),
    ("cmat", "Logical Reasoning", "Verbal Reasoning", "Syllogisms, critical reasoning, assumptions and conclusions.", []),
    ("cmat", "Language Comprehension", "Reading Comprehension", "Passages with inference and factual questions.", []),
    ("cmat", "Language Comprehension", "Grammar & Vocabulary", "Sentence correction, fill-in-the-blanks, word usage.", []),
    ("cmat", "General Awareness", "Current Affairs & Static GK", "National/international news, history, geography, science, awards.", []),
    ("cmat", "Innovation & Entrepreneurship", "Entrepreneurship Concepts", "Business models, startup ecosystem, innovation theories, Indian unicorns.", []),

    # ── MAT ──────────────────────────────────────────────────────────────────
    ("mat", "Language Comprehension", "Reading Comprehension", "Passages from various domains — factual and inferential questions.", []),
    ("mat", "Language Comprehension", "Verbal Ability", "Synonyms, antonyms, analogies, para-jumbles, sentence correction.", []),
    ("mat", "Intelligence & Critical Reasoning", "Logical Reasoning", "Syllogisms, coding-decoding, blood relations, direction sense.", []),
    ("mat", "Intelligence & Critical Reasoning", "Critical Thinking", "Argument analysis, assumptions, course of action.", []),
    ("mat", "Data Analysis & Sufficiency", "Data Interpretation", "Tables, bar/pie/line graphs, caselet DI.", []),
    ("mat", "Data Analysis & Sufficiency", "Data Sufficiency", "Two-statement problems — is the given data sufficient to answer?", []),
    ("mat", "Mathematical Skills", "Arithmetic", "Number system, percentages, ratio, profit-loss, time-work, speed-distance.", []),
    ("mat", "Mathematical Skills", "Advanced Maths", "Algebra, geometry, trigonometry, mensuration, modern maths.", []),
    ("mat", "Indian & Global Environment", "Business & Economy GK", "Business news, economic indicators, market trends, RBI policy.", []),
    ("mat", "Indian & Global Environment", "Current Affairs", "National/international events, awards, appointments, sports.", []),

    # ── GMAT ─────────────────────────────────────────────────────────────────
    ("gmat", "Analytical Writing Assessment", "Issue Analysis", "Construct a well-reasoned position on a broad issue with examples.", []),
    ("gmat", "Integrated Reasoning", "Multi-Source Reasoning", "Evaluate information from 2–3 tabs (text, table, graph) to answer questions.", []),
    ("gmat", "Integrated Reasoning", "Table Analysis & Graphics Interpretation", "Sort/filter tables, interpret charts/graphs, identify relationships.", []),
    ("gmat", "Integrated Reasoning", "Two-Part Analysis", "Solve problems requiring two-component answers — quant or verbal.", []),
    ("gmat", "Quantitative Reasoning", "Problem Solving", "Arithmetic, algebra, geometry — choose from 5 answer choices.", []),
    ("gmat", "Quantitative Reasoning", "Data Sufficiency", "Determine whether one or both statements are sufficient to answer the question.", []),
    ("gmat", "Verbal Reasoning", "Reading Comprehension", "Business and science passages — main idea, inference, logical structure.", []),
    ("gmat", "Verbal Reasoning", "Critical Reasoning", "Strengthen, weaken, assumption, evaluate argument, boldface questions.", []),
    ("gmat", "Verbal Reasoning", "Sentence Correction", "Grammar, parallelism, modifier placement, diction, correct and effective expression.", []),

    # ── GRE ──────────────────────────────────────────────────────────────────
    ("gre", "Analytical Writing", "Issue Task", "Write a well-reasoned, position-taking essay on a given topic.", []),
    ("gre", "Analytical Writing", "Argument Task", "Critique logical flaws in a given argument — no need to take a position.", []),
    ("gre", "Verbal Reasoning", "Reading Comprehension", "Passages — select one answer, select multiple answers, highlight in passage.", []),
    ("gre", "Verbal Reasoning", "Text Completion & Sentence Equivalence", "1–3 blank fill-in; paired-answer format using context clues and vocabulary.", []),
    ("gre", "Verbal Reasoning", "GRE Vocabulary", "High-frequency words: arcane, loquacious, obsequious, equivocate, etc.", []),
    ("gre", "Quantitative Reasoning", "Arithmetic & Algebra", "Number properties, exponents, algebraic expressions, equations, inequalities, sequences.", []),
    ("gre", "Quantitative Reasoning", "Geometry", "Lines, angles, triangles, quadrilaterals, circles, 3D solids, coordinate geometry.", []),
    ("gre", "Quantitative Reasoning", "Data Analysis", "Statistics, probability, charts, tables, scatter plots, data interpretation.", []),
    ("gre", "Quantitative Reasoning", "Quantitative Comparison", "Compare Quantity A vs Quantity B — always, sometimes, never, cannot determine.", []),
]


def seed_sys_topics(apps, schema_editor):
    Subject = apps.get_model('subjects', 'Subject')
    Topic = apps.get_model('subjects', 'Topic')
    Chapter = apps.get_model('subjects', 'Chapter')

    # Build lookup: (course_slug, subject_name) → Subject
    subject_map = {}
    for s in Subject.objects.filter(is_sys=True).select_related('course'):
        subject_map[(s.course.slug, s.name)] = s

    for (course_slug, subject_name, topic_name, description, chapters) in SYS_TOPICS:
        subject = subject_map.get((course_slug, subject_name))
        if not subject:
            continue

        # order = count of existing topics for this subject
        order = Topic.objects.filter(subject=subject).count()
        topic, created = Topic.objects.get_or_create(
            subject=subject,
            name=topic_name,
            defaults={
                'description': description,
                'order': order,
                'is_sys': True,
            }
        )

        for ch_order, (ch_name, ch_desc) in enumerate(chapters):
            Chapter.objects.get_or_create(
                topic=topic,
                name=ch_name,
                defaults={
                    'description': ch_desc,
                    'order': ch_order,
                    'is_sys': True,
                }
            )


def remove_sys_topics(apps, schema_editor):
    Topic = apps.get_model('subjects', 'Topic')
    Topic.objects.filter(is_sys=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('subjects', '0005_add_topics_chapters'),
    ]

    operations = [
        migrations.RunPython(seed_sys_topics, remove_sys_topics),
    ]
