from django.db import migrations


BLUEPRINTS = [
    # ── CAT ──────────────────────────────────────────────────────────────────
    {
        'course_id': '0ba0868f-9acf-4fdb-b879-9edd78795f63',
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
        'course_id': 'c20ba509-4a80-4616-89a7-39d95b960864',
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
        'course_id': 'bf7ae215-effb-4741-ac4e-91064f40a3c7',
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
        'course_id': 'ba0eb025-1d5d-4b92-a74c-8124855927d7',
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
        'course_id': '423dcacb-4453-4b2b-95a4-62a019783cea',
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
        'course_id': '3f2f1290-0c2d-4f63-b83b-4bf14a175f72',
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
        'course_id': '29dc7d67-954f-4351-b2f9-803edb5374b0',
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
        'course_id': '984eb819-5f55-4347-a144-ca2456015fb4',
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
        'course_id': '8d610185-6e14-492b-b77f-334b213ec4cd',
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
        'course_id': '08a742a1-47a6-43ca-ae03-a52e364931d2',
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
        'course_id': '0f7f4d9c-1215-4c33-9c13-a5ef0b17bee4',
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
        'course_id': '73cee998-aff7-4319-bbfa-630d72a5aac4',
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
        'course_id': 'da7c0a14-1104-49c5-9748-bc2ecb3cd141',
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
        'course_id': '93e0a950-ea06-460c-a92a-b7825b54095f',
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
        'course_id': '60fe75c1-0da9-4d48-b857-5e876ff65184',
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
        'course_id': '990a1b39-2158-4d25-8584-9ea088dbaddf',
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
        'course_id': '96ff31f0-b25f-48e3-a37c-16b04c198218',
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
        'course_id': '9ba06831-6ccf-4a5e-b348-04eab6da1a89',
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
        'course_id': '1cddf49f-1dce-449d-9ca8-c561e93edfd7',
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
        'course_id': '9c24de70-b24e-4df6-8c2f-f8c6a015ed38',
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
        'course_id': 'e87ee9b4-aeac-4e6b-b1f9-9d202f0943bb',
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
        'course_id': 'cac55d83-445a-4d8f-a3da-27a83b1ab3ef',
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
        'course_id': '2f06fe90-eb1a-476c-b633-f9a20ecabcb2',
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
        'course_id': '2b7649ef-c249-4320-9135-17e39a6d313a',
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
        'course_id': '26a473ba-fc12-442e-98f3-d4bfefc7fe08',
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
        'course_id': '59d985f7-d772-4d1f-ae07-889a22af52b2',
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
        'course_id': 'a50d7ab8-345a-42f8-bc6e-e98929dd8602',
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
        'course_id': 'fcaff2a2-a0b0-4d03-9aa9-f829c339b50e',
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
    for bp_data in BLUEPRINTS:
        sections = bp_data.pop('sections')
        bp = Blueprint.objects.create(is_sys=True, **bp_data)
        for s in sections:
            BlueprintSection.objects.create(blueprint=bp, topics='', **s)
        bp_data['sections'] = sections  # restore for idempotency if re-run


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
