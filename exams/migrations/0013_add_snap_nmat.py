from django.db import migrations

SNAP = {
    "name": "SNAP",
    "duration": "60 Minutes",
    "total_marks": 90,
    "neg_marking": "-0.5 per wrong answer",
    "sections": [
        {
            "id": "snap-english",
            "name": "General English",
            "subject": "English Language",
            "q_type": "MCQ",
            "count": 15,
            "marks_per_q": 1.5,
            "difficulty": "Medium",
            "topics": "Reading Comprehension, Vocabulary, Grammar, Verbal Reasoning, Fill in the Blanks",
        },
        {
            "id": "snap-quant",
            "name": "Quantitative, DI & Data Sufficiency",
            "subject": "Quantitative Aptitude",
            "q_type": "MCQ",
            "count": 20,
            "marks_per_q": 1.5,
            "difficulty": "Medium",
            "topics": "Arithmetic, Algebra, Geometry, Number Systems, Data Interpretation, Data Sufficiency",
        },
        {
            "id": "snap-reasoning",
            "name": "Analytical & Logical Reasoning",
            "subject": "Logical Reasoning",
            "q_type": "MCQ",
            "count": 25,
            "marks_per_q": 1.5,
            "difficulty": "Hard",
            "topics": "Puzzles, Arrangements, Syllogisms, Series, Coding-Decoding, Critical Reasoning, Visual Reasoning",
        },
    ],
}

NMAT = {
    "name": "NMAT",
    "duration": "108 Minutes (3 timed sections)",
    "total_marks": 108,
    "neg_marking": "No negative marking",
    "sections": [
        {
            "id": "nmat-lang",
            "name": "Language Skills",
            "subject": "English Language",
            "q_type": "MCQ",
            "count": 36,
            "marks_per_q": 1,
            "difficulty": "Medium",
            "topics": "Reading Comprehension, Vocabulary, Grammar, Sentence Correction, Para-jumbles, Analogies",
        },
        {
            "id": "nmat-quant",
            "name": "Quantitative Skills",
            "subject": "Quantitative Aptitude",
            "q_type": "MCQ",
            "count": 36,
            "marks_per_q": 1,
            "difficulty": "Medium",
            "topics": "Arithmetic, Algebra, Geometry, Modern Maths, Data Interpretation, Data Sufficiency",
        },
        {
            "id": "nmat-reasoning",
            "name": "Logical Reasoning",
            "subject": "Logical Reasoning",
            "q_type": "MCQ",
            "count": 36,
            "marks_per_q": 1,
            "difficulty": "Medium",
            "topics": "Puzzles, Arrangements, Series, Coding-Decoding, Blood Relations, Direction Sense, Clocks & Calendars",
        },
    ],
}


def add_snap_nmat(apps, schema_editor):
    ExamTemplate = apps.get_model('exams', 'ExamTemplate')
    for tpl in [SNAP, NMAT]:
        ExamTemplate.objects.get_or_create(
            name=tpl['name'],
            defaults={
                'duration':    tpl['duration'],
                'total_marks': tpl['total_marks'],
                'neg_marking': tpl['neg_marking'],
                'sections':    tpl['sections'],
                'is_default':  True,
            }
        )


def remove_snap_nmat(apps, schema_editor):
    ExamTemplate = apps.get_model('exams', 'ExamTemplate')
    ExamTemplate.objects.filter(name__in=["SNAP", "NMAT"], is_default=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('exams', '0012_update_cat_add_xat'),
    ]

    operations = [
        migrations.RunPython(add_snap_nmat, remove_snap_nmat),
    ]
