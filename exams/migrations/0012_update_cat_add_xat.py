from django.db import migrations

CAT_SECTIONS = [
    {
        "id": "cat-varc-mcq",
        "name": "VARC – MCQ",
        "subject": "English Language",
        "q_type": "MCQ",
        "count": 16,
        "marks_per_q": 3,
        "difficulty": "Hard",
        "topics": "Reading Comprehension, Para-jumbles, Para-summary, Odd Sentence Out",
    },
    {
        "id": "cat-varc-tita",
        "name": "VARC – TITA",
        "subject": "English Language",
        "q_type": "Short Answer",
        "count": 8,
        "marks_per_q": 3,
        "difficulty": "Hard",
        "topics": "Para-jumbles, Sentence Completion, Verbal Reasoning (no negative marking)",
    },
    {
        "id": "cat-dilr-mcq",
        "name": "DILR – MCQ",
        "subject": "Logical Reasoning",
        "q_type": "MCQ",
        "count": 14,
        "marks_per_q": 3,
        "difficulty": "Hard",
        "topics": "Data Interpretation Sets, Logical Reasoning Puzzles, Caselets",
    },
    {
        "id": "cat-dilr-tita",
        "name": "DILR – TITA",
        "subject": "Logical Reasoning",
        "q_type": "Numerical",
        "count": 6,
        "marks_per_q": 3,
        "difficulty": "Hard",
        "topics": "Data Interpretation, Logical Reasoning (no negative marking)",
    },
    {
        "id": "cat-qa-mcq",
        "name": "QA – MCQ",
        "subject": "Quantitative Aptitude",
        "q_type": "MCQ",
        "count": 14,
        "marks_per_q": 3,
        "difficulty": "Medium",
        "topics": "Arithmetic, Algebra, Geometry, Number Systems, Modern Maths",
    },
    {
        "id": "cat-qa-tita",
        "name": "QA – TITA",
        "subject": "Quantitative Aptitude",
        "q_type": "Numerical",
        "count": 8,
        "marks_per_q": 3,
        "difficulty": "Hard",
        "topics": "Arithmetic, Algebra, Geometry, Number Systems (no negative marking)",
    },
]

XAT_SECTIONS = [
    {
        "id": "xat-dm",
        "name": "Decision Making",
        "subject": "Logical Reasoning",
        "q_type": "MCQ",
        "count": 21,
        "marks_per_q": 1,
        "difficulty": "Hard",
        "topics": "Ethical Dilemmas, Data Arrangement, Conditions & Grouping, Complex Arrangements, Situational Decision Making",
    },
    {
        "id": "xat-vla",
        "name": "Verbal & Logical Ability",
        "subject": "English Language",
        "q_type": "MCQ",
        "count": 26,
        "marks_per_q": 1,
        "difficulty": "Hard",
        "topics": "Reading Comprehension, Vocabulary, Grammar, Critical Reasoning, Para-jumbles, Analogy",
    },
    {
        "id": "xat-qadi",
        "name": "Quantitative Ability & Data Interpretation",
        "subject": "Quantitative Aptitude",
        "q_type": "MCQ",
        "count": 28,
        "marks_per_q": 1,
        "difficulty": "Hard",
        "topics": "Arithmetic, Algebra, Geometry, Modern Maths, Data Interpretation Sets, Tables, Graphs",
    },
    {
        "id": "xat-gk",
        "name": "General Knowledge",
        "subject": "General Knowledge",
        "q_type": "MCQ",
        "count": 25,
        "marks_per_q": 1,
        "difficulty": "Medium",
        "topics": "Current Affairs, Business & Economy, Static GK, Science & Technology, Awards, Sports",
    },
]


def update_cat_add_xat(apps, schema_editor):
    ExamTemplate = apps.get_model('exams', 'ExamTemplate')

    # Update existing CAT with accurate MCQ + TITA structure
    ExamTemplate.objects.filter(name="CAT").update(
        duration="2 Hours",
        total_marks=198,
        neg_marking="-1 per wrong MCQ; no penalty on TITA",
        sections=CAT_SECTIONS,
    )

    # Add XAT
    ExamTemplate.objects.get_or_create(
        name="XAT",
        defaults={
            'duration':    "3 Hours 30 Min",
            'total_marks': 100,
            'neg_marking': "-0.25 per wrong answer (Part 1); no penalty for GK",
            'sections':    XAT_SECTIONS,
            'is_default':  True,
        }
    )


def reverse_update_cat_add_xat(apps, schema_editor):
    ExamTemplate = apps.get_model('exams', 'ExamTemplate')

    # Restore original CAT sections
    ExamTemplate.objects.filter(name="CAT").update(
        duration="2 Hours",
        total_marks=198,
        neg_marking="-1 per wrong",
        sections=[
            {"id": "cat-varc", "name": "Verbal Ability & RC",       "subject": "English Language",   "q_type": "MCQ", "count": 24, "marks_per_q": 3, "difficulty": "Hard",   "topics": "RC, Para-jumbles, Grammar, Vocabulary"},
            {"id": "cat-dilr", "name": "Data Interpretation & LR",  "subject": "Logical Reasoning",  "q_type": "MCQ", "count": 20, "marks_per_q": 3, "difficulty": "Hard",   "topics": "DI Sets, Logical Reasoning Puzzles"},
            {"id": "cat-qa",   "name": "Quantitative Ability",       "subject": "Quantitative Aptitude","q_type": "MCQ","count": 22, "marks_per_q": 3, "difficulty": "Medium", "topics": "Arithmetic, Algebra, Geometry"},
        ],
    )

    ExamTemplate.objects.filter(name="XAT", is_default=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('exams', '0011_add_cuet_ug'),
    ]

    operations = [
        migrations.RunPython(update_cat_add_xat, reverse_update_cat_add_xat),
    ]
