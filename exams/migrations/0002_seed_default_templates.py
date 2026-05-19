from django.db import migrations

DEFAULT_TEMPLATES = [
    {
        "name": "NEET UG",
        "duration": "3h 20m",
        "total_marks": 720,
        "neg_marking": "-1 per wrong",
        "sections": [
            {"id": "neet-phy",  "name": "Physics",   "subject": "Physics",   "q_type": "MCQ", "count": 45, "marks_per_q": 4, "difficulty": "Mixed", "topics": "Mechanics, Electricity, Optics, Modern Physics"},
            {"id": "neet-chem", "name": "Chemistry", "subject": "Chemistry", "q_type": "MCQ", "count": 45, "marks_per_q": 4, "difficulty": "Mixed", "topics": "Organic, Inorganic, Physical Chemistry"},
            {"id": "neet-bio",  "name": "Biology",   "subject": "Biology",   "q_type": "MCQ", "count": 90, "marks_per_q": 4, "difficulty": "Mixed", "topics": "Botany, Zoology, Cell Biology, Genetics"},
        ],
    },
    {
        "name": "JEE Mains",
        "duration": "3 Hours",
        "total_marks": 300,
        "neg_marking": "-1 per MCQ wrong",
        "sections": [
            {"id": "jee-math-mcq",  "name": "Mathematics – MCQ",       "subject": "Mathematics", "q_type": "MCQ",        "count": 20, "marks_per_q": 4, "difficulty": "Mixed", "topics": "Algebra, Calculus, Trigonometry"},
            {"id": "jee-math-num",  "name": "Mathematics – Numerical", "subject": "Mathematics", "q_type": "Numerical",  "count": 10, "marks_per_q": 4, "difficulty": "Hard",  "topics": "Calculus, Coordinate Geometry"},
            {"id": "jee-phy-mcq",   "name": "Physics – MCQ",           "subject": "Physics",     "q_type": "MCQ",        "count": 20, "marks_per_q": 4, "difficulty": "Mixed", "topics": "Mechanics, EM, Modern Physics"},
            {"id": "jee-phy-num",   "name": "Physics – Numerical",     "subject": "Physics",     "q_type": "Numerical",  "count": 10, "marks_per_q": 4, "difficulty": "Hard",  "topics": "Mechanics, Optics"},
            {"id": "jee-chem-mcq",  "name": "Chemistry – MCQ",         "subject": "Chemistry",   "q_type": "MCQ",        "count": 20, "marks_per_q": 4, "difficulty": "Mixed", "topics": "Organic, Inorganic, Physical"},
            {"id": "jee-chem-num",  "name": "Chemistry – Numerical",   "subject": "Chemistry",   "q_type": "Numerical",  "count": 10, "marks_per_q": 4, "difficulty": "Hard",  "topics": "Physical Chemistry"},
        ],
    },
    {
        "name": "JEE Advanced",
        "duration": "6 Hours (2 papers)",
        "total_marks": 360,
        "neg_marking": "Partial / negative marking",
        "sections": [
            {"id": "jeeadv-p1-phy",  "name": "Paper 1 – Physics",   "subject": "Physics",      "q_type": "MCQ",          "count": 18, "marks_per_q": 3, "difficulty": "HOTS", "topics": "All Physics Topics"},
            {"id": "jeeadv-p1-chem", "name": "Paper 1 – Chemistry", "subject": "Chemistry",    "q_type": "MCQ",          "count": 18, "marks_per_q": 3, "difficulty": "HOTS", "topics": "All Chemistry Topics"},
            {"id": "jeeadv-p1-math", "name": "Paper 1 – Maths",     "subject": "Mathematics",  "q_type": "MCQ",          "count": 18, "marks_per_q": 3, "difficulty": "HOTS", "topics": "All Maths Topics"},
            {"id": "jeeadv-p2-phy",  "name": "Paper 2 – Physics",   "subject": "Physics",      "q_type": "Short Answer", "count": 6,  "marks_per_q": 4, "difficulty": "HOTS", "topics": "All Physics Topics"},
            {"id": "jeeadv-p2-chem", "name": "Paper 2 – Chemistry", "subject": "Chemistry",    "q_type": "Short Answer", "count": 6,  "marks_per_q": 4, "difficulty": "HOTS", "topics": "All Chemistry Topics"},
            {"id": "jeeadv-p2-math", "name": "Paper 2 – Maths",     "subject": "Mathematics",  "q_type": "Short Answer", "count": 6,  "marks_per_q": 4, "difficulty": "HOTS", "topics": "All Maths Topics"},
        ],
    },
    {
        "name": "CAT",
        "duration": "2 Hours",
        "total_marks": 198,
        "neg_marking": "-1 per wrong",
        "sections": [
            {"id": "cat-varc", "name": "Verbal Ability & RC",      "subject": "English Language",      "q_type": "MCQ", "count": 24, "marks_per_q": 3, "difficulty": "Hard",   "topics": "RC, Para-jumbles, Grammar, Vocabulary"},
            {"id": "cat-dilr", "name": "Data Interpretation & LR", "subject": "Logical Reasoning",     "q_type": "MCQ", "count": 20, "marks_per_q": 3, "difficulty": "Hard",   "topics": "DI Sets, Logical Reasoning Puzzles"},
            {"id": "cat-qa",   "name": "Quantitative Ability",     "subject": "Quantitative Aptitude", "q_type": "MCQ", "count": 22, "marks_per_q": 3, "difficulty": "Medium", "topics": "Arithmetic, Algebra, Geometry"},
        ],
    },
    {
        "name": "UPSC CSE (Prelims)",
        "duration": "4 Hours (2 papers)",
        "total_marks": 400,
        "neg_marking": "-1/3 per wrong",
        "sections": [
            {"id": "upsc-gs1",  "name": "General Studies I", "subject": "General Knowledge",     "q_type": "MCQ", "count": 100, "marks_per_q": 2,   "difficulty": "Hard",   "topics": "History, Geography, Polity, Economy, Science"},
            {"id": "upsc-csat", "name": "CSAT",              "subject": "Quantitative Aptitude",  "q_type": "MCQ", "count": 80,  "marks_per_q": 2.5, "difficulty": "Medium", "topics": "Comprehension, Reasoning, Maths"},
        ],
    },
    {
        "name": "GATE CS",
        "duration": "3 Hours",
        "total_marks": 100,
        "neg_marking": "-1/3 (1M) / -2/3 (2M)",
        "sections": [
            {"id": "gate-ga",    "name": "General Aptitude",  "subject": "Quantitative Aptitude", "q_type": "MCQ", "count": 10, "marks_per_q": 1, "difficulty": "Easy",   "topics": "Verbal, Numerical, Reasoning"},
            {"id": "gate-cs-1m", "name": "CS Core – 1 Mark", "subject": "Computer Science",      "q_type": "MCQ", "count": 25, "marks_per_q": 1, "difficulty": "Medium", "topics": "Algorithms, OS, DBMS, CN"},
            {"id": "gate-cs-2m", "name": "CS Core – 2 Marks","subject": "Computer Science",      "q_type": "MCQ", "count": 30, "marks_per_q": 2, "difficulty": "Hard",   "topics": "Algorithms, OS, DBMS, CN"},
        ],
    },
    {
        "name": "SSC CGL",
        "duration": "1 Hour",
        "total_marks": 200,
        "neg_marking": "-0.5 per wrong",
        "sections": [
            {"id": "ssc-reason",  "name": "General Intelligence",  "subject": "Logical Reasoning",     "q_type": "MCQ", "count": 25, "marks_per_q": 2, "difficulty": "Easy",   "topics": "Reasoning Puzzles, Series"},
            {"id": "ssc-gk",      "name": "General Awareness",     "subject": "General Knowledge",     "q_type": "MCQ", "count": 25, "marks_per_q": 2, "difficulty": "Easy",   "topics": "Current Affairs, Static GK"},
            {"id": "ssc-quant",   "name": "Quantitative Aptitude", "subject": "Quantitative Aptitude", "q_type": "MCQ", "count": 25, "marks_per_q": 2, "difficulty": "Medium", "topics": "Arithmetic, Geometry, Algebra"},
            {"id": "ssc-english", "name": "English Comprehension", "subject": "English Language",      "q_type": "MCQ", "count": 25, "marks_per_q": 2, "difficulty": "Easy",   "topics": "Grammar, Comprehension, Vocabulary"},
        ],
    },
    {
        "name": "CLAT",
        "duration": "2 Hours",
        "total_marks": 120,
        "neg_marking": "-0.25 per wrong",
        "sections": [
            {"id": "clat-eng",   "name": "English Language",        "subject": "English Language",      "q_type": "MCQ", "count": 28, "marks_per_q": 1, "difficulty": "Medium", "topics": "Comprehension, Vocabulary, Grammar"},
            {"id": "clat-gk",    "name": "Current Affairs & GK",    "subject": "General Knowledge",     "q_type": "MCQ", "count": 35, "marks_per_q": 1, "difficulty": "Medium", "topics": "Current Affairs, Static GK"},
            {"id": "clat-legal", "name": "Legal Reasoning",         "subject": "Logical Reasoning",     "q_type": "MCQ", "count": 35, "marks_per_q": 1, "difficulty": "Hard",   "topics": "Legal Principles, Cases"},
            {"id": "clat-logic", "name": "Logical Reasoning",       "subject": "Logical Reasoning",     "q_type": "MCQ", "count": 12, "marks_per_q": 1, "difficulty": "Medium", "topics": "Puzzles, Arrangements"},
            {"id": "clat-quant", "name": "Quantitative Techniques", "subject": "Quantitative Aptitude", "q_type": "MCQ", "count": 10, "marks_per_q": 1, "difficulty": "Easy",   "topics": "Basic Maths, Statistics"},
        ],
    },
]


def seed_templates(apps, schema_editor):
    ExamTemplate = apps.get_model('exams', 'ExamTemplate')
    for t in DEFAULT_TEMPLATES:
        ExamTemplate.objects.get_or_create(
            name=t['name'],
            defaults={
                'duration':    t['duration'],
                'total_marks': t['total_marks'],
                'neg_marking': t['neg_marking'],
                'sections':    t['sections'],
                'is_default':  True,
            }
        )


def unseed_templates(apps, schema_editor):
    ExamTemplate = apps.get_model('exams', 'ExamTemplate')
    names = [t['name'] for t in DEFAULT_TEMPLATES]
    ExamTemplate.objects.filter(name__in=names, is_default=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('exams', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_templates, unseed_templates),
    ]
