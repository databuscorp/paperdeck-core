from django.db import migrations


BLUEPRINTS = [
    # ── CAT ──────────────────────────────────────────────────────────────────
    {
        'course_slug': 'cat',
        'duration': '2 Hours',
        'total_marks': 198,
        'neg_marking_enabled': True,
        'neg_marking_value': 1.00,
        'sections': [
            {'name': 'VARC – MCQ',  'subject': 'Verbal Ability & Reading Comprehension', 'q_type': 'MCQ',      'count': 16, 'marks_per_q': 3.00, 'neg_marks_per_q': 1.00, 'difficulty': 'Hard',  'bloom': 'Mixed', 'order': 1},
            {'name': 'VARC – TITA', 'subject': 'Verbal Ability & Reading Comprehension', 'q_type': 'Numerical', 'count': 8,  'marks_per_q': 3.00, 'neg_marks_per_q': 0.00, 'difficulty': 'Hard',  'bloom': 'Mixed', 'order': 2},
            {'name': 'DILR – MCQ',  'subject': 'Data Interpretation & Logical Reasoning',  'q_type': 'MCQ',      'count': 16, 'marks_per_q': 3.00, 'neg_marks_per_q': 1.00, 'difficulty': 'HOTS',  'bloom': 'Mixed', 'order': 3},
            {'name': 'DILR – TITA', 'subject': 'Data Interpretation & Logical Reasoning',  'q_type': 'Numerical', 'count': 8,  'marks_per_q': 3.00, 'neg_marks_per_q': 0.00, 'difficulty': 'HOTS',  'bloom': 'Mixed', 'order': 4},
            {'name': 'QA – MCQ',    'subject': 'Quantitative Aptitude',                  'q_type': 'MCQ',      'count': 14, 'marks_per_q': 3.00, 'neg_marks_per_q': 1.00, 'difficulty': 'Hard',  'bloom': 'Mixed', 'order': 5},
            {'name': 'QA – TITA',   'subject': 'Quantitative Aptitude',                  'q_type': 'Numerical', 'count': 4,  'marks_per_q': 3.00, 'neg_marks_per_q': 0.00, 'difficulty': 'Hard',  'bloom': 'Mixed', 'order': 6},
        ],
    },
    # ── CLAT UG ──────────────────────────────────────────────────────────────
    {
        'course_slug': 'clat',
        'duration': '2 Hours',
        'total_marks': 150,
        'neg_marking_enabled': True,
        'neg_marking_value': 0.25,
        'sections': [
            {'name': 'English Language',           'subject': 'English Language',           'q_type': 'MCQ', 'count': 28, 'marks_per_q': 1.00, 'neg_marks_per_q': 0.25, 'difficulty': 'Hard', 'bloom': 'Mixed', 'order': 1},
            {'name': 'Current Affairs & GK',        'subject': 'Current Affairs & GK',        'q_type': 'MCQ', 'count': 35, 'marks_per_q': 1.00, 'neg_marks_per_q': 0.25, 'difficulty': 'Hard', 'bloom': 'Mixed', 'order': 2},
            {'name': 'Legal Reasoning',             'subject': 'Legal Reasoning',             'q_type': 'MCQ', 'count': 39, 'marks_per_q': 1.00, 'neg_marks_per_q': 0.25, 'difficulty': 'HOTS', 'bloom': 'Mixed', 'order': 3},
            {'name': 'Logical Reasoning',           'subject': 'Logical Reasoning',           'q_type': 'MCQ', 'count': 32, 'marks_per_q': 1.00, 'neg_marks_per_q': 0.25, 'difficulty': 'Hard', 'bloom': 'Mixed', 'order': 4},
            {'name': 'Quantitative Techniques',     'subject': 'Quantitative Techniques',     'q_type': 'MCQ', 'count': 16, 'marks_per_q': 1.00, 'neg_marks_per_q': 0.25, 'difficulty': 'Hard', 'bloom': 'Mixed', 'order': 5},
        ],
    },
    # ── CLAT PG ──────────────────────────────────────────────────────────────
    {
        'course_slug': 'clat-pg',
        'duration': '2 Hours',
        'total_marks': 150,
        'neg_marking_enabled': True,
        'neg_marking_value': 0.25,
        'sections': [
            {'name': 'Constitutional Law',          'subject': 'Constitutional Law',          'q_type': 'MCQ', 'count': 40, 'marks_per_q': 1.00, 'neg_marks_per_q': 0.25, 'difficulty': 'HOTS', 'bloom': 'Mixed', 'order': 1},
            {'name': 'Jurisprudence & Legal Theory','subject': 'Jurisprudence & Legal Theory','q_type': 'MCQ', 'count': 30, 'marks_per_q': 1.00, 'neg_marks_per_q': 0.25, 'difficulty': 'Hard', 'bloom': 'Mixed', 'order': 2},
            {'name': 'Law of Contracts',            'subject': 'Law of Contracts',            'q_type': 'MCQ', 'count': 20, 'marks_per_q': 1.00, 'neg_marks_per_q': 0.25, 'difficulty': 'Hard', 'bloom': 'Mixed', 'order': 3},
            {'name': 'Law of Torts',                'subject': 'Law of Torts',                'q_type': 'MCQ', 'count': 20, 'marks_per_q': 1.00, 'neg_marks_per_q': 0.25, 'difficulty': 'Hard', 'bloom': 'Mixed', 'order': 4},
            {'name': 'Other Core Law Papers',       'subject': 'Other Core Law Papers',       'q_type': 'MCQ', 'count': 40, 'marks_per_q': 1.00, 'neg_marks_per_q': 0.25, 'difficulty': 'Hard', 'bloom': 'Mixed', 'order': 5},
        ],
    },
    # ── CMAT ─────────────────────────────────────────────────────────────────
    {
        'course_slug': 'cmat',
        'duration': '3 Hours',
        'total_marks': 400,
        'neg_marking_enabled': True,
        'neg_marking_value': 1.00,
        'sections': [
            {'name': 'Language Comprehension',      'subject': 'Language Comprehension',      'q_type': 'MCQ', 'count': 25, 'marks_per_q': 4.00, 'neg_marks_per_q': 1.00, 'difficulty': 'Hard', 'bloom': 'Mixed', 'order': 1},
            {'name': 'Logical Reasoning',           'subject': 'Logical Reasoning',           'q_type': 'MCQ', 'count': 25, 'marks_per_q': 4.00, 'neg_marks_per_q': 1.00, 'difficulty': 'Hard', 'bloom': 'Mixed', 'order': 2},
            {'name': 'Quantitative Techniques',     'subject': 'Quantitative Techniques & DI','q_type': 'MCQ', 'count': 25, 'marks_per_q': 4.00, 'neg_marks_per_q': 1.00, 'difficulty': 'Hard', 'bloom': 'Mixed', 'order': 3},
            {'name': 'General Awareness',           'subject': 'General Awareness',           'q_type': 'MCQ', 'count': 25, 'marks_per_q': 4.00, 'neg_marks_per_q': 1.00, 'difficulty': 'Hard', 'bloom': 'Mixed', 'order': 4},
        ],
    },
    # ── CUET PG ──────────────────────────────────────────────────────────────
    {
        'course_slug': 'cuet-pg',
        'duration': '2 Hours',
        'total_marks': 400,
        'neg_marking_enabled': True,
        'neg_marking_value': 1.00,
        'sections': [
            {'name': 'Part A – Languages & GA',     'subject': 'General English & GK',        'q_type': 'MCQ', 'count': 25,  'marks_per_q': 4.00, 'neg_marks_per_q': 1.00, 'difficulty': 'Hard', 'bloom': 'Mixed', 'order': 1},
            {'name': 'Part B – Domain Subject',     'subject': 'Domain Subject',               'q_type': 'MCQ', 'count': 75,  'marks_per_q': 4.00, 'neg_marks_per_q': 1.00, 'difficulty': 'HOTS', 'bloom': 'Mixed', 'order': 2},
        ],
    },
    # ── CUET UG ──────────────────────────────────────────────────────────────
    {
        'course_slug': 'cuet-ug',
        'duration': '3 Hours 15 Minutes',
        'total_marks': 700,
        'neg_marking_enabled': True,
        'neg_marking_value': 1.00,
        'sections': [
            {'name': 'Section 1 – Language',        'subject': 'Language (English)',           'q_type': 'MCQ', 'count': 40,  'marks_per_q': 5.00, 'neg_marks_per_q': 1.00, 'difficulty': 'Hard', 'bloom': 'Mixed', 'order': 1},
            {'name': 'Section 2 – Domain Subjects', 'subject': 'Domain Subject',               'q_type': 'MCQ', 'count': 50,  'marks_per_q': 5.00, 'neg_marks_per_q': 1.00, 'difficulty': 'HOTS', 'bloom': 'Mixed', 'order': 2},
            {'name': 'Section 3 – GK & CA',         'subject': 'General Knowledge & CA',       'q_type': 'MCQ', 'count': 50,  'marks_per_q': 5.00, 'neg_marks_per_q': 1.00, 'difficulty': 'Hard', 'bloom': 'Mixed', 'order': 3},
        ],
    },
    # ── GATE CS ──────────────────────────────────────────────────────────────
    {
        'course_slug': 'gate-cs',
        'duration': '3 Hours',
        'total_marks': 100,
        'neg_marking_enabled': True,
        'neg_marking_value': 0.33,
        'sections': [
            {'name': 'GA – 1 Mark',        'subject': 'General Aptitude',             'q_type': 'MCQ', 'count': 5,  'marks_per_q': 1.00, 'neg_marks_per_q': 0.33, 'difficulty': 'Hard', 'bloom': 'Mixed', 'order': 1},
            {'name': 'GA – 2 Mark',        'subject': 'General Aptitude',             'q_type': 'MCQ', 'count': 5,  'marks_per_q': 2.00, 'neg_marks_per_q': 0.67, 'difficulty': 'HOTS', 'bloom': 'Mixed', 'order': 2},
            {'name': 'CS Technical – 1 Mark', 'subject': 'Computer Science',          'q_type': 'MCQ', 'count': 25, 'marks_per_q': 1.00, 'neg_marks_per_q': 0.33, 'difficulty': 'Hard', 'bloom': 'Mixed', 'order': 3},
            {'name': 'CS Technical – 2 Mark', 'subject': 'Computer Science',          'q_type': 'MCQ', 'count': 30, 'marks_per_q': 2.00, 'neg_marks_per_q': 0.67, 'difficulty': 'HOTS', 'bloom': 'Mixed', 'order': 4},
        ],
    },
    # ── GATE Civil ───────────────────────────────────────────────────────────
    {
        'course_slug': 'gate-civil',
        'duration': '3 Hours',
        'total_marks': 100,
        'neg_marking_enabled': True,
        'neg_marking_value': 0.33,
        'sections': [
            {'name': 'GA – 1 Mark',              'subject': 'General Aptitude',         'q_type': 'MCQ', 'count': 5,  'marks_per_q': 1.00, 'neg_marks_per_q': 0.33, 'difficulty': 'Hard', 'bloom': 'Mixed', 'order': 1},
            {'name': 'GA – 2 Mark',              'subject': 'General Aptitude',         'q_type': 'MCQ', 'count': 5,  'marks_per_q': 2.00, 'neg_marks_per_q': 0.67, 'difficulty': 'HOTS', 'bloom': 'Mixed', 'order': 2},
            {'name': 'Civil Technical – 1 Mark', 'subject': 'Civil Engineering',        'q_type': 'MCQ', 'count': 25, 'marks_per_q': 1.00, 'neg_marks_per_q': 0.33, 'difficulty': 'Hard', 'bloom': 'Mixed', 'order': 3},
            {'name': 'Civil Technical – 2 Mark', 'subject': 'Civil Engineering',        'q_type': 'MCQ', 'count': 30, 'marks_per_q': 2.00, 'neg_marks_per_q': 0.67, 'difficulty': 'HOTS', 'bloom': 'Mixed', 'order': 4},
        ],
    },
    # ── GATE ECE ─────────────────────────────────────────────────────────────
    {
        'course_slug': 'gate-ece',
        'duration': '3 Hours',
        'total_marks': 100,
        'neg_marking_enabled': True,
        'neg_marking_value': 0.33,
        'sections': [
            {'name': 'GA – 1 Mark',              'subject': 'General Aptitude',            'q_type': 'MCQ', 'count': 5,  'marks_per_q': 1.00, 'neg_marks_per_q': 0.33, 'difficulty': 'Hard', 'bloom': 'Mixed', 'order': 1},
            {'name': 'GA – 2 Mark',              'subject': 'General Aptitude',            'q_type': 'MCQ', 'count': 5,  'marks_per_q': 2.00, 'neg_marks_per_q': 0.67, 'difficulty': 'HOTS', 'bloom': 'Mixed', 'order': 2},
            {'name': 'ECE Technical – 1 Mark',   'subject': 'Electronics & Communication', 'q_type': 'MCQ', 'count': 25, 'marks_per_q': 1.00, 'neg_marks_per_q': 0.33, 'difficulty': 'Hard', 'bloom': 'Mixed', 'order': 3},
            {'name': 'ECE Technical – 2 Mark',   'subject': 'Electronics & Communication', 'q_type': 'MCQ', 'count': 30, 'marks_per_q': 2.00, 'neg_marks_per_q': 0.67, 'difficulty': 'HOTS', 'bloom': 'Mixed', 'order': 4},
        ],
    },
    # ── GATE EE ──────────────────────────────────────────────────────────────
    {
        'course_slug': 'gate-ee',
        'duration': '3 Hours',
        'total_marks': 100,
        'neg_marking_enabled': True,
        'neg_marking_value': 0.33,
        'sections': [
            {'name': 'GA – 1 Mark',              'subject': 'General Aptitude',            'q_type': 'MCQ', 'count': 5,  'marks_per_q': 1.00, 'neg_marks_per_q': 0.33, 'difficulty': 'Hard', 'bloom': 'Mixed', 'order': 1},
            {'name': 'GA – 2 Mark',              'subject': 'General Aptitude',            'q_type': 'MCQ', 'count': 5,  'marks_per_q': 2.00, 'neg_marks_per_q': 0.67, 'difficulty': 'HOTS', 'bloom': 'Mixed', 'order': 2},
            {'name': 'EE Technical – 1 Mark',    'subject': 'Electrical Engineering',      'q_type': 'MCQ', 'count': 25, 'marks_per_q': 1.00, 'neg_marks_per_q': 0.33, 'difficulty': 'Hard', 'bloom': 'Mixed', 'order': 3},
            {'name': 'EE Technical – 2 Mark',    'subject': 'Electrical Engineering',      'q_type': 'MCQ', 'count': 30, 'marks_per_q': 2.00, 'neg_marks_per_q': 0.67, 'difficulty': 'HOTS', 'bloom': 'Mixed', 'order': 4},
        ],
    },
    # ── GATE ME ──────────────────────────────────────────────────────────────
    {
        'course_slug': 'gate-me',
        'duration': '3 Hours',
        'total_marks': 100,
        'neg_marking_enabled': True,
        'neg_marking_value': 0.33,
        'sections': [
            {'name': 'GA – 1 Mark',              'subject': 'General Aptitude',            'q_type': 'MCQ', 'count': 5,  'marks_per_q': 1.00, 'neg_marks_per_q': 0.33, 'difficulty': 'Hard', 'bloom': 'Mixed', 'order': 1},
            {'name': 'GA – 2 Mark',              'subject': 'General Aptitude',            'q_type': 'MCQ', 'count': 5,  'marks_per_q': 2.00, 'neg_marks_per_q': 0.67, 'difficulty': 'HOTS', 'bloom': 'Mixed', 'order': 2},
            {'name': 'ME Technical – 1 Mark',    'subject': 'Mechanical Engineering',      'q_type': 'MCQ', 'count': 25, 'marks_per_q': 1.00, 'neg_marks_per_q': 0.33, 'difficulty': 'Hard', 'bloom': 'Mixed', 'order': 3},
            {'name': 'ME Technical – 2 Mark',    'subject': 'Mechanical Engineering',      'q_type': 'MCQ', 'count': 30, 'marks_per_q': 2.00, 'neg_marks_per_q': 0.67, 'difficulty': 'HOTS', 'bloom': 'Mixed', 'order': 4},
        ],
    },
    # ── GMAT Focus Edition ───────────────────────────────────────────────────
    {
        'course_slug': 'gmat',
        'duration': '2 Hours 15 Minutes',
        'total_marks': 64,
        'neg_marking_enabled': False,
        'neg_marking_value': 0.00,
        'sections': [
            {'name': 'Quantitative Reasoning',  'subject': 'Quantitative Reasoning', 'q_type': 'MCQ', 'count': 21, 'marks_per_q': 1.00, 'neg_marks_per_q': 0.00, 'difficulty': 'HOTS', 'bloom': 'Mixed', 'order': 1},
            {'name': 'Verbal Reasoning',        'subject': 'Verbal Reasoning',       'q_type': 'MCQ', 'count': 23, 'marks_per_q': 1.00, 'neg_marks_per_q': 0.00, 'difficulty': 'Hard', 'bloom': 'Mixed', 'order': 2},
            {'name': 'Data Insights',           'subject': 'Data Insights',          'q_type': 'MCQ', 'count': 20, 'marks_per_q': 1.00, 'neg_marks_per_q': 0.00, 'difficulty': 'HOTS', 'bloom': 'Mixed', 'order': 3},
        ],
    },
    # ── GRE General ──────────────────────────────────────────────────────────
    {
        'course_slug': 'gre',
        'duration': '1 Hour 58 Minutes',
        'total_marks': 55,
        'neg_marking_enabled': False,
        'neg_marking_value': 0.00,
        'sections': [
            {'name': 'Verbal Reasoning 1',       'subject': 'Verbal Reasoning',       'q_type': 'MCQ', 'count': 12, 'marks_per_q': 1.00, 'neg_marks_per_q': 0.00, 'difficulty': 'Hard', 'bloom': 'Mixed', 'order': 1},
            {'name': 'Verbal Reasoning 2',       'subject': 'Verbal Reasoning',       'q_type': 'MCQ', 'count': 15, 'marks_per_q': 1.00, 'neg_marks_per_q': 0.00, 'difficulty': 'HOTS', 'bloom': 'Mixed', 'order': 2},
            {'name': 'Quantitative Reasoning 1', 'subject': 'Quantitative Reasoning', 'q_type': 'MCQ', 'count': 12, 'marks_per_q': 1.00, 'neg_marks_per_q': 0.00, 'difficulty': 'Hard', 'bloom': 'Mixed', 'order': 3},
            {'name': 'Quantitative Reasoning 2', 'subject': 'Quantitative Reasoning', 'q_type': 'MCQ', 'count': 15, 'marks_per_q': 1.00, 'neg_marks_per_q': 0.00, 'difficulty': 'HOTS', 'bloom': 'Mixed', 'order': 4},
            {'name': 'Analytical Writing',       'subject': 'Analytical Writing',     'q_type': 'Essay',  'count': 1,  'marks_per_q': 6.00, 'neg_marks_per_q': 0.00, 'difficulty': 'HOTS', 'bloom': 'Mixed', 'order': 5},
        ],
    },
    # ── IIFT ─────────────────────────────────────────────────────────────────
    {
        'course_slug': 'iift',
        'duration': '2 Hours',
        'total_marks': 300,
        'neg_marking_enabled': True,
        'neg_marking_value': 1.00,
        'sections': [
            {'name': 'Verbal Ability & Reading Comprehension', 'subject': 'Verbal Ability & RC', 'q_type': 'MCQ', 'count': 35, 'marks_per_q': 3.00, 'neg_marks_per_q': 1.00, 'difficulty': 'Hard', 'bloom': 'Mixed', 'order': 1},
            {'name': 'Data Interpretation & Logical Reasoning','subject': 'DI & Logical Reasoning', 'q_type': 'MCQ', 'count': 30, 'marks_per_q': 3.00, 'neg_marks_per_q': 1.00, 'difficulty': 'HOTS', 'bloom': 'Mixed', 'order': 2},
            {'name': 'General Awareness',                      'subject': 'General Awareness',      'q_type': 'MCQ', 'count': 20, 'marks_per_q': 1.50, 'neg_marks_per_q': 0.50, 'difficulty': 'Hard', 'bloom': 'Mixed', 'order': 3},
            {'name': 'Quantitative Analysis',                  'subject': 'Quantitative Analysis',  'q_type': 'MCQ', 'count': 25, 'marks_per_q': 3.00, 'neg_marks_per_q': 1.00, 'difficulty': 'HOTS', 'bloom': 'Mixed', 'order': 4},
        ],
    },
    # ── JEE Advanced Paper 1 ─────────────────────────────────────────────────
    {
        'course_slug': 'jee-advanced-paper-1',
        'duration': '3 Hours',
        'total_marks': 180,
        'neg_marking_enabled': True,
        'neg_marking_value': 1.00,
        'sections': [
            {'name': 'Physics – MCQ Single',     'subject': 'Physics',    'q_type': 'MCQ',              'count': 4,  'marks_per_q': 3.00, 'neg_marks_per_q': 1.00, 'difficulty': 'HOTS', 'bloom': 'Mixed', 'order': 1},
            {'name': 'Physics – MCQ Multi',      'subject': 'Physics',    'q_type': 'MCQ (Multi)',      'count': 4,  'marks_per_q': 4.00, 'neg_marks_per_q': 2.00, 'difficulty': 'HOTS', 'bloom': 'Mixed', 'order': 2},
            {'name': 'Physics – Integer',        'subject': 'Physics',    'q_type': 'Numerical',        'count': 9,  'marks_per_q': 4.00, 'neg_marks_per_q': 0.00, 'difficulty': 'HOTS', 'bloom': 'Mixed', 'order': 3},
            {'name': 'Chemistry – MCQ Single',   'subject': 'Chemistry',  'q_type': 'MCQ',              'count': 4,  'marks_per_q': 3.00, 'neg_marks_per_q': 1.00, 'difficulty': 'HOTS', 'bloom': 'Mixed', 'order': 4},
            {'name': 'Chemistry – MCQ Multi',    'subject': 'Chemistry',  'q_type': 'MCQ (Multi)',      'count': 4,  'marks_per_q': 4.00, 'neg_marks_per_q': 2.00, 'difficulty': 'HOTS', 'bloom': 'Mixed', 'order': 5},
            {'name': 'Chemistry – Integer',      'subject': 'Chemistry',  'q_type': 'Numerical',        'count': 9,  'marks_per_q': 4.00, 'neg_marks_per_q': 0.00, 'difficulty': 'HOTS', 'bloom': 'Mixed', 'order': 6},
            {'name': 'Maths – MCQ Single',       'subject': 'Mathematics','q_type': 'MCQ',              'count': 4,  'marks_per_q': 3.00, 'neg_marks_per_q': 1.00, 'difficulty': 'HOTS', 'bloom': 'Mixed', 'order': 7},
            {'name': 'Maths – MCQ Multi',        'subject': 'Mathematics','q_type': 'MCQ (Multi)',      'count': 4,  'marks_per_q': 4.00, 'neg_marks_per_q': 2.00, 'difficulty': 'HOTS', 'bloom': 'Mixed', 'order': 8},
            {'name': 'Maths – Integer',          'subject': 'Mathematics','q_type': 'Numerical',        'count': 9,  'marks_per_q': 4.00, 'neg_marks_per_q': 0.00, 'difficulty': 'HOTS', 'bloom': 'Mixed', 'order': 9},
        ],
    },
    # ── JEE Advanced Paper 2 ─────────────────────────────────────────────────
    {
        'course_slug': 'jee-advanced-paper-2',
        'duration': '3 Hours',
        'total_marks': 180,
        'neg_marking_enabled': True,
        'neg_marking_value': 1.00,
        'sections': [
            {'name': 'Physics – MCQ Single',     'subject': 'Physics',    'q_type': 'MCQ',         'count': 4,  'marks_per_q': 3.00, 'neg_marks_per_q': 1.00, 'difficulty': 'HOTS', 'bloom': 'Mixed', 'order': 1},
            {'name': 'Physics – MCQ Multi',      'subject': 'Physics',    'q_type': 'MCQ (Multi)', 'count': 4,  'marks_per_q': 4.00, 'neg_marks_per_q': 2.00, 'difficulty': 'HOTS', 'bloom': 'Mixed', 'order': 2},
            {'name': 'Physics – Integer',        'subject': 'Physics',    'q_type': 'Numerical',   'count': 9,  'marks_per_q': 4.00, 'neg_marks_per_q': 0.00, 'difficulty': 'HOTS', 'bloom': 'Mixed', 'order': 3},
            {'name': 'Chemistry – MCQ Single',   'subject': 'Chemistry',  'q_type': 'MCQ',         'count': 4,  'marks_per_q': 3.00, 'neg_marks_per_q': 1.00, 'difficulty': 'HOTS', 'bloom': 'Mixed', 'order': 4},
            {'name': 'Chemistry – MCQ Multi',    'subject': 'Chemistry',  'q_type': 'MCQ (Multi)', 'count': 4,  'marks_per_q': 4.00, 'neg_marks_per_q': 2.00, 'difficulty': 'HOTS', 'bloom': 'Mixed', 'order': 5},
            {'name': 'Chemistry – Integer',      'subject': 'Chemistry',  'q_type': 'Numerical',   'count': 9,  'marks_per_q': 4.00, 'neg_marks_per_q': 0.00, 'difficulty': 'HOTS', 'bloom': 'Mixed', 'order': 6},
            {'name': 'Maths – MCQ Single',       'subject': 'Mathematics','q_type': 'MCQ',         'count': 4,  'marks_per_q': 3.00, 'neg_marks_per_q': 1.00, 'difficulty': 'HOTS', 'bloom': 'Mixed', 'order': 7},
            {'name': 'Maths – MCQ Multi',        'subject': 'Mathematics','q_type': 'MCQ (Multi)', 'count': 4,  'marks_per_q': 4.00, 'neg_marks_per_q': 2.00, 'difficulty': 'HOTS', 'bloom': 'Mixed', 'order': 8},
            {'name': 'Maths – Integer',          'subject': 'Mathematics','q_type': 'Numerical',   'count': 9,  'marks_per_q': 4.00, 'neg_marks_per_q': 0.00, 'difficulty': 'HOTS', 'bloom': 'Mixed', 'order': 9},
        ],
    },
    # ── JEE Mains ────────────────────────────────────────────────────────────
    {
        'course_slug': 'jee-mains',
        'duration': '3 Hours',
        'total_marks': 300,
        'neg_marking_enabled': True,
        'neg_marking_value': 1.00,
        'sections': [
            {'name': 'Physics – MCQ',        'subject': 'Physics',    'q_type': 'MCQ',      'count': 20, 'marks_per_q': 4.00, 'neg_marks_per_q': 1.00, 'difficulty': 'Hard', 'bloom': 'Mixed', 'order': 1},
            {'name': 'Physics – Numerical',  'subject': 'Physics',    'q_type': 'Numerical', 'count': 5,  'marks_per_q': 4.00, 'neg_marks_per_q': 0.00, 'difficulty': 'HOTS', 'bloom': 'Mixed', 'order': 2},
            {'name': 'Chemistry – MCQ',      'subject': 'Chemistry',  'q_type': 'MCQ',      'count': 20, 'marks_per_q': 4.00, 'neg_marks_per_q': 1.00, 'difficulty': 'Hard', 'bloom': 'Mixed', 'order': 3},
            {'name': 'Chemistry – Numerical','subject': 'Chemistry',  'q_type': 'Numerical', 'count': 5,  'marks_per_q': 4.00, 'neg_marks_per_q': 0.00, 'difficulty': 'Hard', 'bloom': 'Mixed', 'order': 4},
            {'name': 'Maths – MCQ',          'subject': 'Mathematics','q_type': 'MCQ',      'count': 20, 'marks_per_q': 4.00, 'neg_marks_per_q': 1.00, 'difficulty': 'HOTS', 'bloom': 'Mixed', 'order': 5},
            {'name': 'Maths – Numerical',    'subject': 'Mathematics','q_type': 'Numerical', 'count': 5,  'marks_per_q': 4.00, 'neg_marks_per_q': 0.00, 'difficulty': 'HOTS', 'bloom': 'Mixed', 'order': 6},
        ],
    },
    # ── MAT ──────────────────────────────────────────────────────────────────
    {
        'course_slug': 'mat',
        'duration': '2 Hours 30 Minutes',
        'total_marks': 200,
        'neg_marking_enabled': True,
        'neg_marking_value': 0.25,
        'sections': [
            {'name': 'Language Comprehension',          'subject': 'Language Comprehension',     'q_type': 'MCQ', 'count': 40, 'marks_per_q': 1.00, 'neg_marks_per_q': 0.25, 'difficulty': 'Hard', 'bloom': 'Mixed', 'order': 1},
            {'name': 'Mathematical Skills',              'subject': 'Mathematical Skills',         'q_type': 'MCQ', 'count': 40, 'marks_per_q': 1.00, 'neg_marks_per_q': 0.25, 'difficulty': 'Hard', 'bloom': 'Mixed', 'order': 2},
            {'name': 'Data Analysis & Sufficiency',     'subject': 'Data Analysis & Sufficiency', 'q_type': 'MCQ', 'count': 40, 'marks_per_q': 1.00, 'neg_marks_per_q': 0.25, 'difficulty': 'Hard', 'bloom': 'Mixed', 'order': 3},
            {'name': 'Intelligence & Critical Reasoning','subject': 'Intelligence & Reasoning',   'q_type': 'MCQ', 'count': 40, 'marks_per_q': 1.00, 'neg_marks_per_q': 0.25, 'difficulty': 'HOTS', 'bloom': 'Mixed', 'order': 4},
            {'name': 'Indian & Global Environment',     'subject': 'Indian & Global Environment', 'q_type': 'MCQ', 'count': 40, 'marks_per_q': 1.00, 'neg_marks_per_q': 0.25, 'difficulty': 'Hard', 'bloom': 'Mixed', 'order': 5},
        ],
    },
    # ── NEET PG ──────────────────────────────────────────────────────────────
    {
        'course_slug': 'neet-pg',
        'duration': '3 Hours 30 Minutes',
        'total_marks': 800,
        'neg_marking_enabled': True,
        'neg_marking_value': 1.00,
        'sections': [
            {'name': 'Pre-Clinical',  'subject': 'Pre-Clinical (Anatomy, Physiology, Biochemistry)',              'q_type': 'MCQ', 'count': 67, 'marks_per_q': 4.00, 'neg_marks_per_q': 1.00, 'difficulty': 'Hard', 'bloom': 'Mixed', 'order': 1},
            {'name': 'Para-Clinical', 'subject': 'Para-Clinical (Pathology, Micro, Pharma, Forensic)',            'q_type': 'MCQ', 'count': 66, 'marks_per_q': 4.00, 'neg_marks_per_q': 1.00, 'difficulty': 'HOTS', 'bloom': 'Mixed', 'order': 2},
            {'name': 'Clinical',      'subject': 'Clinical (Medicine, Surgery, OB-GYN, Paediatrics, PSM, etc.)', 'q_type': 'MCQ', 'count': 67, 'marks_per_q': 4.00, 'neg_marks_per_q': 1.00, 'difficulty': 'HOTS', 'bloom': 'Mixed', 'order': 3},
        ],
    },
    # ── NEET UG ──────────────────────────────────────────────────────────────
    {
        'course_slug': 'neet-ug',
        'duration': '3 Hours 20 Minutes',
        'total_marks': 720,
        'neg_marking_enabled': True,
        'neg_marking_value': 1.00,
        'sections': [
            {'name': 'Physics – Section A',   'subject': 'Physics',   'q_type': 'MCQ', 'count': 35, 'marks_per_q': 4.00, 'neg_marks_per_q': 1.00, 'difficulty': 'Hard', 'bloom': 'Mixed', 'order': 1},
            {'name': 'Physics – Section B',   'subject': 'Physics',   'q_type': 'MCQ', 'count': 10, 'marks_per_q': 4.00, 'neg_marks_per_q': 1.00, 'difficulty': 'HOTS', 'bloom': 'Mixed', 'order': 2},
            {'name': 'Chemistry – Section A', 'subject': 'Chemistry', 'q_type': 'MCQ', 'count': 35, 'marks_per_q': 4.00, 'neg_marks_per_q': 1.00, 'difficulty': 'Hard', 'bloom': 'Mixed', 'order': 3},
            {'name': 'Chemistry – Section B', 'subject': 'Chemistry', 'q_type': 'MCQ', 'count': 10, 'marks_per_q': 4.00, 'neg_marks_per_q': 1.00, 'difficulty': 'HOTS', 'bloom': 'Mixed', 'order': 4},
            {'name': 'Botany – Section A',    'subject': 'Biology (Botany)',   'q_type': 'MCQ', 'count': 35, 'marks_per_q': 4.00, 'neg_marks_per_q': 1.00, 'difficulty': 'Hard', 'bloom': 'Mixed', 'order': 5},
            {'name': 'Botany – Section B',    'subject': 'Biology (Botany)',   'q_type': 'MCQ', 'count': 10, 'marks_per_q': 4.00, 'neg_marks_per_q': 1.00, 'difficulty': 'HOTS', 'bloom': 'Mixed', 'order': 6},
            {'name': 'Zoology – Section A',   'subject': 'Biology (Zoology)',  'q_type': 'MCQ', 'count': 35, 'marks_per_q': 4.00, 'neg_marks_per_q': 1.00, 'difficulty': 'Hard', 'bloom': 'Mixed', 'order': 7},
            {'name': 'Zoology – Section B',   'subject': 'Biology (Zoology)',  'q_type': 'MCQ', 'count': 10, 'marks_per_q': 4.00, 'neg_marks_per_q': 1.00, 'difficulty': 'HOTS', 'bloom': 'Mixed', 'order': 8},
        ],
    },
    # ── NMAT ─────────────────────────────────────────────────────────────────
    {
        'course_slug': 'nmat',
        'duration': '2 Hours',
        'total_marks': 108,
        'neg_marking_enabled': False,
        'neg_marking_value': 0.00,
        'sections': [
            {'name': 'Language Skills',      'subject': 'Language Skills',      'q_type': 'MCQ', 'count': 36, 'marks_per_q': 1.00, 'neg_marks_per_q': 0.00, 'difficulty': 'Hard', 'bloom': 'Mixed', 'order': 1},
            {'name': 'Quantitative Skills',  'subject': 'Quantitative Skills',  'q_type': 'MCQ', 'count': 36, 'marks_per_q': 1.00, 'neg_marks_per_q': 0.00, 'difficulty': 'Hard', 'bloom': 'Mixed', 'order': 2},
            {'name': 'Logical Reasoning',    'subject': 'Logical Reasoning',    'q_type': 'MCQ', 'count': 36, 'marks_per_q': 1.00, 'neg_marks_per_q': 0.00, 'difficulty': 'HOTS', 'bloom': 'Mixed', 'order': 3},
        ],
    },
    # ── SNAP ─────────────────────────────────────────────────────────────────
    {
        'course_slug': 'snap',
        'duration': '1 Hour',
        'total_marks': 90,
        'neg_marking_enabled': True,
        'neg_marking_value': 0.50,
        'sections': [
            {'name': 'General English',                     'subject': 'General English',                     'q_type': 'MCQ', 'count': 15, 'marks_per_q': 1.50, 'neg_marks_per_q': 0.50, 'difficulty': 'Hard', 'bloom': 'Mixed', 'order': 1},
            {'name': 'Analytical & Logical Reasoning',      'subject': 'Analytical & Logical Reasoning',      'q_type': 'MCQ', 'count': 25, 'marks_per_q': 1.50, 'neg_marks_per_q': 0.50, 'difficulty': 'HOTS', 'bloom': 'Mixed', 'order': 2},
            {'name': 'Quantitative – Data Interpretation',  'subject': 'Quantitative – Data Interpretation',  'q_type': 'MCQ', 'count': 20, 'marks_per_q': 1.50, 'neg_marks_per_q': 0.50, 'difficulty': 'Hard', 'bloom': 'Mixed', 'order': 3},
        ],
    },
    # ── SSC CGL Tier 1 ───────────────────────────────────────────────────────
    {
        'course_slug': 'ssc-cgl',
        'duration': '1 Hour',
        'total_marks': 200,
        'neg_marking_enabled': True,
        'neg_marking_value': 0.50,
        'sections': [
            {'name': 'General Intelligence & Reasoning', 'subject': 'General Intelligence & Reasoning', 'q_type': 'MCQ', 'count': 25, 'marks_per_q': 2.00, 'neg_marks_per_q': 0.50, 'difficulty': 'Hard', 'bloom': 'Mixed', 'order': 1},
            {'name': 'General Awareness',                'subject': 'General Awareness',                'q_type': 'MCQ', 'count': 25, 'marks_per_q': 2.00, 'neg_marks_per_q': 0.50, 'difficulty': 'Hard', 'bloom': 'Mixed', 'order': 2},
            {'name': 'Quantitative Aptitude',            'subject': 'Quantitative Aptitude',            'q_type': 'MCQ', 'count': 25, 'marks_per_q': 2.00, 'neg_marks_per_q': 0.50, 'difficulty': 'Hard', 'bloom': 'Mixed', 'order': 3},
            {'name': 'English Comprehension',            'subject': 'English Comprehension',            'q_type': 'MCQ', 'count': 25, 'marks_per_q': 2.00, 'neg_marks_per_q': 0.50, 'difficulty': 'Hard', 'bloom': 'Mixed', 'order': 4},
        ],
    },
    # ── SSC CGL Tier 2 ───────────────────────────────────────────────────────
    {
        'course_slug': 'ssc-cgl-tier-2',
        'duration': '2 Hours 30 Minutes',
        'total_marks': 450,
        'neg_marking_enabled': True,
        'neg_marking_value': 1.00,
        'sections': [
            {'name': 'Mathematical Abilities',            'subject': 'Mathematical Abilities',    'q_type': 'MCQ', 'count': 30, 'marks_per_q': 3.00, 'neg_marks_per_q': 1.00, 'difficulty': 'HOTS', 'bloom': 'Mixed', 'order': 1},
            {'name': 'Reasoning & General Intelligence',  'subject': 'Reasoning & GI',            'q_type': 'MCQ', 'count': 30, 'marks_per_q': 3.00, 'neg_marks_per_q': 1.00, 'difficulty': 'Hard', 'bloom': 'Mixed', 'order': 2},
            {'name': 'English Language & Comprehension',  'subject': 'English Language',          'q_type': 'MCQ', 'count': 45, 'marks_per_q': 3.00, 'neg_marks_per_q': 1.00, 'difficulty': 'Hard', 'bloom': 'Mixed', 'order': 3},
            {'name': 'General Awareness',                 'subject': 'General Awareness',         'q_type': 'MCQ', 'count': 25, 'marks_per_q': 3.00, 'neg_marks_per_q': 1.00, 'difficulty': 'Hard', 'bloom': 'Mixed', 'order': 4},
            {'name': 'Computer Knowledge',                'subject': 'Computer Knowledge',        'q_type': 'MCQ', 'count': 20, 'marks_per_q': 3.00, 'neg_marks_per_q': 1.00, 'difficulty': 'Hard', 'bloom': 'Mixed', 'order': 5},
        ],
    },
    # ── TISSNET ──────────────────────────────────────────────────────────────
    {
        'course_slug': 'tissnet',
        'duration': '1 Hour 40 Minutes',
        'total_marks': 100,
        'neg_marking_enabled': False,
        'neg_marking_value': 0.00,
        'sections': [
            {'name': 'English Proficiency',           'subject': 'English Proficiency',           'q_type': 'MCQ', 'count': 30, 'marks_per_q': 1.00, 'neg_marks_per_q': 0.00, 'difficulty': 'Hard', 'bloom': 'Mixed', 'order': 1},
            {'name': 'Maths & Logical Reasoning',     'subject': 'Maths & Logical Reasoning',     'q_type': 'MCQ', 'count': 30, 'marks_per_q': 1.00, 'neg_marks_per_q': 0.00, 'difficulty': 'Hard', 'bloom': 'Mixed', 'order': 2},
            {'name': 'General Awareness',             'subject': 'General Awareness',             'q_type': 'MCQ', 'count': 40, 'marks_per_q': 1.00, 'neg_marks_per_q': 0.00, 'difficulty': 'Hard', 'bloom': 'Mixed', 'order': 3},
        ],
    },
    # ── UPSC CSE Prelims Paper 1 ──────────────────────────────────────────────
    {
        'course_slug': 'upsc-cse-prelims-paper-1',
        'duration': '2 Hours',
        'total_marks': 200,
        'neg_marking_enabled': True,
        'neg_marking_value': 0.67,
        'sections': [
            {'name': 'History',                   'subject': 'History',                   'q_type': 'MCQ', 'count': 18, 'marks_per_q': 2.00, 'neg_marks_per_q': 0.67, 'difficulty': 'Hard', 'bloom': 'Mixed', 'order': 1},
            {'name': 'Geography',                 'subject': 'Geography',                 'q_type': 'MCQ', 'count': 15, 'marks_per_q': 2.00, 'neg_marks_per_q': 0.67, 'difficulty': 'Hard', 'bloom': 'Mixed', 'order': 2},
            {'name': 'Polity & Governance',       'subject': 'Polity & Governance',       'q_type': 'MCQ', 'count': 16, 'marks_per_q': 2.00, 'neg_marks_per_q': 0.67, 'difficulty': 'HOTS', 'bloom': 'Mixed', 'order': 3},
            {'name': 'Economy',                   'subject': 'Economy',                   'q_type': 'MCQ', 'count': 14, 'marks_per_q': 2.00, 'neg_marks_per_q': 0.67, 'difficulty': 'Hard', 'bloom': 'Mixed', 'order': 4},
            {'name': 'Environment & Ecology',     'subject': 'Environment & Ecology',     'q_type': 'MCQ', 'count': 12, 'marks_per_q': 2.00, 'neg_marks_per_q': 0.67, 'difficulty': 'Hard', 'bloom': 'Mixed', 'order': 5},
            {'name': 'Science & Technology',      'subject': 'Science & Technology',      'q_type': 'MCQ', 'count': 12, 'marks_per_q': 2.00, 'neg_marks_per_q': 0.67, 'difficulty': 'Hard', 'bloom': 'Mixed', 'order': 6},
            {'name': 'Current Affairs',           'subject': 'Current Affairs',           'q_type': 'MCQ', 'count': 13, 'marks_per_q': 2.00, 'neg_marks_per_q': 0.67, 'difficulty': 'Hard', 'bloom': 'Mixed', 'order': 7},
        ],
    },
    # ── UPSC CSE Prelims Paper 2 (CSAT) ──────────────────────────────────────
    {
        'course_slug': 'upsc-cse-prelims-paper-2',
        'duration': '2 Hours',
        'total_marks': 200,
        'neg_marking_enabled': True,
        'neg_marking_value': 0.67,
        'sections': [
            {'name': 'Reading Comprehension',         'subject': 'Reading Comprehension',         'q_type': 'MCQ', 'count': 30, 'marks_per_q': 2.00, 'neg_marks_per_q': 0.67, 'difficulty': 'Hard', 'bloom': 'Mixed', 'order': 1},
            {'name': 'Mathematical Operations',       'subject': 'Mathematical Operations',       'q_type': 'MCQ', 'count': 20, 'marks_per_q': 2.00, 'neg_marks_per_q': 0.67, 'difficulty': 'Hard', 'bloom': 'Mixed', 'order': 2},
            {'name': 'Data Interpretation',           'subject': 'Data Interpretation',           'q_type': 'MCQ', 'count': 20, 'marks_per_q': 2.00, 'neg_marks_per_q': 0.67, 'difficulty': 'HOTS', 'bloom': 'Mixed', 'order': 3},
            {'name': 'Analytical Reasoning',          'subject': 'Analytical Reasoning',          'q_type': 'MCQ', 'count': 20, 'marks_per_q': 2.00, 'neg_marks_per_q': 0.67, 'difficulty': 'HOTS', 'bloom': 'Mixed', 'order': 4},
            {'name': 'Communication & Decision Making','subject': 'Communication & Decision Making','q_type': 'MCQ', 'count': 10, 'marks_per_q': 2.00, 'neg_marks_per_q': 0.67, 'difficulty': 'Hard', 'bloom': 'Mixed', 'order': 5},
        ],
    },
    # ── XAT ──────────────────────────────────────────────────────────────────
    {
        'course_slug': 'xat',
        'duration': '3 Hours',
        'total_marks': 100,
        'neg_marking_enabled': True,
        'neg_marking_value': 0.25,
        'sections': [
            {'name': 'Verbal & Logical Ability',        'subject': 'Verbal & Logical Ability',     'q_type': 'MCQ', 'count': 26, 'marks_per_q': 1.00, 'neg_marks_per_q': 0.25, 'difficulty': 'HOTS', 'bloom': 'Mixed', 'order': 1},
            {'name': 'Decision Making',                 'subject': 'Decision Making',              'q_type': 'MCQ', 'count': 21, 'marks_per_q': 1.00, 'neg_marks_per_q': 0.25, 'difficulty': 'HOTS', 'bloom': 'Mixed', 'order': 2},
            {'name': 'Quantitative Aptitude & DI',      'subject': 'Quantitative Aptitude & DI',   'q_type': 'MCQ', 'count': 28, 'marks_per_q': 1.00, 'neg_marks_per_q': 0.25, 'difficulty': 'HOTS', 'bloom': 'Mixed', 'order': 3},
            {'name': 'General Knowledge',               'subject': 'General Knowledge',            'q_type': 'MCQ', 'count': 25, 'marks_per_q': 1.00, 'neg_marks_per_q': 0.25, 'difficulty': 'Hard', 'bloom': 'Mixed', 'order': 4},
        ],
    },
]


def seed_blueprints(apps, schema_editor):
    Blueprint = apps.get_model('blueprints', 'Blueprint')
    BlueprintSection = apps.get_model('blueprints', 'BlueprintSection')
    Course = apps.get_model('courses', 'Course')
    course_map = {c.slug: c for c in Course.objects.filter(is_sys=True)}
    for bp_data in BLUEPRINTS:
        sections = bp_data.pop('sections')
        slug = bp_data.pop('course_slug')
        course = course_map.get(slug)
        bp = Blueprint.objects.create(is_sys=True, course=course, **bp_data)
        for s in sections:
            BlueprintSection.objects.create(blueprint=bp, topics='', **s)
        bp_data['course_slug'] = slug
        bp_data['sections'] = sections


def unseed_blueprints(apps, schema_editor):
    Blueprint = apps.get_model('blueprints', 'Blueprint')
    Blueprint.objects.filter(is_sys=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('blueprints', '0003_org_nullable_is_sys'),
        ('courses', '0006_seed_sys_courses'),
    ]

    operations = [
        migrations.RunPython(seed_blueprints, unseed_blueprints),
    ]
