from django.db import migrations

GATE_BRANCHES = [
    {
        "name": "GATE ECE",
        "duration": "3 Hours",
        "total_marks": 100,
        "neg_marking": "-1/3 (1M) / -2/3 (2M)",
        "sections": [
            {
                "id": "gate-ece-ga",
                "name": "General Aptitude",
                "subject": "Quantitative Aptitude",
                "q_type": "MCQ",
                "count": 10,
                "marks_per_q": 1,
                "difficulty": "Easy",
                "topics": "Verbal Ability, Numerical Aptitude, Logical Reasoning",
            },
            {
                "id": "gate-ece-math",
                "name": "Engineering Mathematics",
                "subject": "Mathematics",
                "q_type": "MCQ",
                "count": 13,
                "marks_per_q": 1,
                "difficulty": "Medium",
                "topics": "Linear Algebra, Calculus, Differential Equations, Probability & Statistics, Complex Variables, Transform Theory",
            },
            {
                "id": "gate-ece-core-1m",
                "name": "ECE Core – 1 Mark",
                "subject": "Electronics & Communication",
                "q_type": "MCQ",
                "count": 22,
                "marks_per_q": 1,
                "difficulty": "Medium",
                "topics": "Network Theory, Electronic Devices, Analog Circuits, Digital Circuits, Signals & Systems, Control Systems, Communications, Electromagnetics",
            },
            {
                "id": "gate-ece-core-2m",
                "name": "ECE Core – 2 Marks",
                "subject": "Electronics & Communication",
                "q_type": "Numerical",
                "count": 20,
                "marks_per_q": 2,
                "difficulty": "Hard",
                "topics": "Network Theory, Electronic Devices, Analog Circuits, Digital Circuits, Signals & Systems, Control Systems, Communications, Electromagnetics",
            },
        ],
    },
    {
        "name": "GATE ME",
        "duration": "3 Hours",
        "total_marks": 100,
        "neg_marking": "-1/3 (1M) / -2/3 (2M)",
        "sections": [
            {
                "id": "gate-me-ga",
                "name": "General Aptitude",
                "subject": "Quantitative Aptitude",
                "q_type": "MCQ",
                "count": 10,
                "marks_per_q": 1,
                "difficulty": "Easy",
                "topics": "Verbal Ability, Numerical Aptitude, Logical Reasoning",
            },
            {
                "id": "gate-me-math",
                "name": "Engineering Mathematics",
                "subject": "Mathematics",
                "q_type": "MCQ",
                "count": 13,
                "marks_per_q": 1,
                "difficulty": "Medium",
                "topics": "Linear Algebra, Calculus, Differential Equations, Probability & Statistics, Numerical Methods, Complex Variables",
            },
            {
                "id": "gate-me-core-1m",
                "name": "ME Core – 1 Mark",
                "subject": "Mechanical Engineering",
                "q_type": "MCQ",
                "count": 22,
                "marks_per_q": 1,
                "difficulty": "Medium",
                "topics": "Engineering Mechanics, Strength of Materials, Thermodynamics, Fluid Mechanics, Heat Transfer, Machine Design, Manufacturing, Industrial Engineering",
            },
            {
                "id": "gate-me-core-2m",
                "name": "ME Core – 2 Marks",
                "subject": "Mechanical Engineering",
                "q_type": "Numerical",
                "count": 20,
                "marks_per_q": 2,
                "difficulty": "Hard",
                "topics": "Engineering Mechanics, Strength of Materials, Thermodynamics, Fluid Mechanics, Heat Transfer, Machine Design, Manufacturing, Industrial Engineering",
            },
        ],
    },
    {
        "name": "GATE Civil",
        "duration": "3 Hours",
        "total_marks": 100,
        "neg_marking": "-1/3 (1M) / -2/3 (2M)",
        "sections": [
            {
                "id": "gate-civil-ga",
                "name": "General Aptitude",
                "subject": "Quantitative Aptitude",
                "q_type": "MCQ",
                "count": 10,
                "marks_per_q": 1,
                "difficulty": "Easy",
                "topics": "Verbal Ability, Numerical Aptitude, Logical Reasoning",
            },
            {
                "id": "gate-civil-math",
                "name": "Engineering Mathematics",
                "subject": "Mathematics",
                "q_type": "MCQ",
                "count": 13,
                "marks_per_q": 1,
                "difficulty": "Medium",
                "topics": "Linear Algebra, Calculus, Differential Equations, Probability & Statistics, Numerical Methods",
            },
            {
                "id": "gate-civil-core-1m",
                "name": "Civil Core – 1 Mark",
                "subject": "Civil Engineering",
                "q_type": "MCQ",
                "count": 22,
                "marks_per_q": 1,
                "difficulty": "Medium",
                "topics": "Structural Analysis, Concrete Structures, Steel Structures, Soil Mechanics & Foundation, Fluid Mechanics, Hydrology, Transportation Engineering, Environmental Engineering, Geomatics",
            },
            {
                "id": "gate-civil-core-2m",
                "name": "Civil Core – 2 Marks",
                "subject": "Civil Engineering",
                "q_type": "Numerical",
                "count": 20,
                "marks_per_q": 2,
                "difficulty": "Hard",
                "topics": "Structural Analysis, Concrete Structures, Steel Structures, Soil Mechanics & Foundation, Fluid Mechanics, Hydrology, Transportation Engineering, Environmental Engineering",
            },
        ],
    },
]


def add_gate_branches(apps, schema_editor):
    ExamTemplate = apps.get_model('exams', 'ExamTemplate')
    for tpl in GATE_BRANCHES:
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


def remove_gate_branches(apps, schema_editor):
    ExamTemplate = apps.get_model('exams', 'ExamTemplate')
    ExamTemplate.objects.filter(
        name__in=[t['name'] for t in GATE_BRANCHES],
        is_default=True,
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('exams', '0006_add_clat_pg'),
    ]

    operations = [
        migrations.RunPython(add_gate_branches, remove_gate_branches),
    ]
