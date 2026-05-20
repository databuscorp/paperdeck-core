from django.db import migrations

GMAT = {
    "name": "GMAT",
    "duration": "2 Hours 15 Min",
    "total_marks": 805,
    "neg_marking": "No negative marking; adaptive scoring (205–805)",
    "sections": [
        {
            "id": "gmat-quant",
            "name": "Quantitative Reasoning",
            "subject": "Quantitative Aptitude",
            "q_type": "MCQ",
            "count": 21,
            "marks_per_q": 1,
            "difficulty": "Hard",
            "topics": "Problem Solving, Data Sufficiency, Arithmetic, Algebra, Geometry, Word Problems, Number Properties",
        },
        {
            "id": "gmat-verbal",
            "name": "Verbal Reasoning",
            "subject": "English Language",
            "q_type": "MCQ",
            "count": 23,
            "marks_per_q": 1,
            "difficulty": "Hard",
            "topics": "Critical Reasoning, Reading Comprehension, Sentence Correction, Argument Analysis, Inference",
        },
        {
            "id": "gmat-di",
            "name": "Data Insights",
            "subject": "Logical Reasoning",
            "q_type": "MCQ",
            "count": 20,
            "marks_per_q": 1,
            "difficulty": "Hard",
            "topics": "Data Sufficiency, Multi-Source Reasoning, Table Analysis, Graphics Interpretation, Two-Part Analysis",
        },
    ],
}

GRE = {
    "name": "GRE",
    "duration": "1 Hour 58 Min",
    "total_marks": 340,
    "neg_marking": "No negative marking; scaled scoring (130–170 per section)",
    "sections": [
        {
            "id": "gre-verbal1",
            "name": "Verbal Reasoning – Section 1",
            "subject": "English Language",
            "q_type": "MCQ",
            "count": 12,
            "marks_per_q": 1,
            "difficulty": "Hard",
            "topics": "Reading Comprehension, Text Completion, Sentence Equivalence, Vocabulary in Context, Critical Reasoning",
        },
        {
            "id": "gre-verbal2",
            "name": "Verbal Reasoning – Section 2",
            "subject": "English Language",
            "q_type": "MCQ",
            "count": 15,
            "marks_per_q": 1,
            "difficulty": "Hard",
            "topics": "Reading Comprehension, Text Completion, Sentence Equivalence, Vocabulary in Context, Critical Reasoning",
        },
        {
            "id": "gre-quant1",
            "name": "Quantitative Reasoning – Section 1",
            "subject": "Quantitative Aptitude",
            "q_type": "MCQ",
            "count": 12,
            "marks_per_q": 1,
            "difficulty": "Hard",
            "topics": "Arithmetic, Algebra, Geometry, Data Analysis, Quantitative Comparison, Problem Solving",
        },
        {
            "id": "gre-quant2",
            "name": "Quantitative Reasoning – Section 2",
            "subject": "Quantitative Aptitude",
            "q_type": "MCQ",
            "count": 15,
            "marks_per_q": 1,
            "difficulty": "Hard",
            "topics": "Arithmetic, Algebra, Geometry, Data Analysis, Quantitative Comparison, Problem Solving",
        },
        {
            "id": "gre-aw",
            "name": "Analytical Writing",
            "subject": "English Language",
            "q_type": "Long Answer",
            "count": 1,
            "marks_per_q": 6,
            "difficulty": "Hard",
            "topics": "Analyse an Issue – construct a reasoned argument on a given topic with evidence and logical structure",
        },
    ],
}


def add_gmat_gre(apps, schema_editor):
    ExamTemplate = apps.get_model('exams', 'ExamTemplate')
    for tpl in [GMAT, GRE]:
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


def remove_gmat_gre(apps, schema_editor):
    ExamTemplate = apps.get_model('exams', 'ExamTemplate')
    ExamTemplate.objects.filter(name__in=["GMAT", "GRE"], is_default=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('exams', '0015_add_cmat_mat'),
    ]

    operations = [
        migrations.RunPython(add_gmat_gre, remove_gmat_gre),
    ]
