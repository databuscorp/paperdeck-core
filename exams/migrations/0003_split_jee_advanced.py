from django.db import migrations

JEE_ADV_PAPER1 = {
    "name": "JEE Advanced Paper 1",
    "duration": "3 Hours",
    "total_marks": 180,
    "neg_marking": "Negative marking on MCQ; no penalty on Numerical",
    "sections": [
        {"id": "jeeadv1-phy-mcq",  "name": "Physics – MCQ",         "subject": "Physics",      "q_type": "MCQ",      "count": 10, "marks_per_q": 3, "difficulty": "HOTS", "topics": "Mechanics, Electricity, Optics, Modern Physics"},
        {"id": "jeeadv1-phy-num",  "name": "Physics – Numerical",    "subject": "Physics",      "q_type": "Numerical","count": 5,  "marks_per_q": 4, "difficulty": "HOTS", "topics": "Mechanics, Electromagnetism"},
        {"id": "jeeadv1-chem-mcq", "name": "Chemistry – MCQ",        "subject": "Chemistry",    "q_type": "MCQ",      "count": 10, "marks_per_q": 3, "difficulty": "HOTS", "topics": "Organic, Inorganic, Physical Chemistry"},
        {"id": "jeeadv1-chem-num", "name": "Chemistry – Numerical",  "subject": "Chemistry",    "q_type": "Numerical","count": 5,  "marks_per_q": 4, "difficulty": "HOTS", "topics": "Physical Chemistry, Stoichiometry"},
        {"id": "jeeadv1-math-mcq", "name": "Mathematics – MCQ",      "subject": "Mathematics",  "q_type": "MCQ",      "count": 10, "marks_per_q": 3, "difficulty": "HOTS", "topics": "Calculus, Algebra, Coordinate Geometry"},
        {"id": "jeeadv1-math-num", "name": "Mathematics – Numerical","subject": "Mathematics",  "q_type": "Numerical","count": 5,  "marks_per_q": 4, "difficulty": "HOTS", "topics": "Calculus, Trigonometry"},
    ],
}

JEE_ADV_PAPER2 = {
    "name": "JEE Advanced Paper 2",
    "duration": "3 Hours",
    "total_marks": 180,
    "neg_marking": "Negative marking on MCQ; no penalty on Numerical",
    "sections": [
        {"id": "jeeadv2-phy-mcq",  "name": "Physics – MCQ",           "subject": "Physics",     "q_type": "MCQ",          "count": 8,  "marks_per_q": 3, "difficulty": "HOTS", "topics": "Mechanics, Thermodynamics, Waves"},
        {"id": "jeeadv2-phy-sa",   "name": "Physics – Short Answer",   "subject": "Physics",     "q_type": "Short Answer", "count": 6,  "marks_per_q": 4, "difficulty": "HOTS", "topics": "Optics, Modern Physics, Electricity"},
        {"id": "jeeadv2-chem-mcq", "name": "Chemistry – MCQ",          "subject": "Chemistry",   "q_type": "MCQ",          "count": 8,  "marks_per_q": 3, "difficulty": "HOTS", "topics": "Organic, Inorganic, Electrochemistry"},
        {"id": "jeeadv2-chem-sa",  "name": "Chemistry – Short Answer", "subject": "Chemistry",   "q_type": "Short Answer", "count": 6,  "marks_per_q": 4, "difficulty": "HOTS", "topics": "Organic Reactions, Physical Chemistry"},
        {"id": "jeeadv2-math-mcq", "name": "Mathematics – MCQ",        "subject": "Mathematics", "q_type": "MCQ",          "count": 8,  "marks_per_q": 3, "difficulty": "HOTS", "topics": "Algebra, Probability, Matrices"},
        {"id": "jeeadv2-math-sa",  "name": "Mathematics – Short Answer","subject": "Mathematics", "q_type": "Short Answer", "count": 6,  "marks_per_q": 4, "difficulty": "HOTS", "topics": "Calculus, Vectors, 3D Geometry"},
    ],
}


def split_jee_advanced(apps, schema_editor):
    ExamTemplate = apps.get_model('exams', 'ExamTemplate')
    ExamTemplate.objects.filter(name="JEE Advanced").delete()
    for tpl in [JEE_ADV_PAPER1, JEE_ADV_PAPER2]:
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


def merge_jee_advanced(apps, schema_editor):
    ExamTemplate = apps.get_model('exams', 'ExamTemplate')
    ExamTemplate.objects.filter(name__in=["JEE Advanced Paper 1", "JEE Advanced Paper 2"]).delete()
    ExamTemplate.objects.get_or_create(
        name="JEE Advanced",
        defaults={
            'duration':    "6 Hours (2 papers)",
            'total_marks': 360,
            'neg_marking': "Partial / negative marking",
            'sections':    JEE_ADV_PAPER1['sections'] + JEE_ADV_PAPER2['sections'],
            'is_default':  True,
        }
    )


class Migration(migrations.Migration):

    dependencies = [
        ('exams', '0002_seed_default_templates'),
    ]

    operations = [
        migrations.RunPython(split_jee_advanced, merge_jee_advanced),
    ]
