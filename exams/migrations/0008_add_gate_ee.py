from django.db import migrations


def add_gate_ee(apps, schema_editor):
    ExamTemplate = apps.get_model('exams', 'ExamTemplate')
    ExamTemplate.objects.get_or_create(
        name="GATE EE",
        defaults={
            'duration':    "3 Hours",
            'total_marks': 100,
            'neg_marking': "-1/3 (1M) / -2/3 (2M)",
            'sections': [
                {
                    "id": "gate-ee-ga",
                    "name": "General Aptitude",
                    "subject": "Quantitative Aptitude",
                    "q_type": "MCQ",
                    "count": 10,
                    "marks_per_q": 1,
                    "difficulty": "Easy",
                    "topics": "Verbal Ability, Numerical Aptitude, Logical Reasoning",
                },
                {
                    "id": "gate-ee-math",
                    "name": "Engineering Mathematics",
                    "subject": "Mathematics",
                    "q_type": "MCQ",
                    "count": 13,
                    "marks_per_q": 1,
                    "difficulty": "Medium",
                    "topics": "Linear Algebra, Calculus, Differential Equations, Complex Variables, Probability & Statistics, Numerical Methods, Transform Theory",
                },
                {
                    "id": "gate-ee-core-1m",
                    "name": "EE Core – 1 Mark",
                    "subject": "Electrical Engineering",
                    "q_type": "MCQ",
                    "count": 22,
                    "marks_per_q": 1,
                    "difficulty": "Medium",
                    "topics": "Electric Circuits, Electromagnetic Fields, Signals & Systems, Electrical Machines, Power Systems, Control Systems, Electrical Measurements, Analog Electronics, Digital Electronics, Power Electronics",
                },
                {
                    "id": "gate-ee-core-2m",
                    "name": "EE Core – 2 Marks",
                    "subject": "Electrical Engineering",
                    "q_type": "Numerical",
                    "count": 20,
                    "marks_per_q": 2,
                    "difficulty": "Hard",
                    "topics": "Electric Circuits, Electromagnetic Fields, Signals & Systems, Electrical Machines, Power Systems, Control Systems, Electrical Measurements, Analog Electronics, Digital Electronics, Power Electronics",
                },
            ],
            'is_default': True,
        }
    )


def remove_gate_ee(apps, schema_editor):
    ExamTemplate = apps.get_model('exams', 'ExamTemplate')
    ExamTemplate.objects.filter(name="GATE EE", is_default=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('exams', '0007_add_gate_branches'),
    ]

    operations = [
        migrations.RunPython(add_gate_ee, remove_gate_ee),
    ]
