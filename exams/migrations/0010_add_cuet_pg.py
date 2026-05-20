from django.db import migrations


def add_cuet_pg(apps, schema_editor):
    ExamTemplate = apps.get_model('exams', 'ExamTemplate')
    ExamTemplate.objects.get_or_create(
        name="CUET PG",
        defaults={
            'duration':    "2 Hours",
            'total_marks': 400,
            'neg_marking': "-1 per wrong answer",
            'sections': [
                {
                    "id": "cuetpg-lang",
                    "name": "Part A – Language Comprehension",
                    "subject": "English Language",
                    "q_type": "MCQ",
                    "count": 10,
                    "marks_per_q": 4,
                    "difficulty": "Medium",
                    "topics": "Reading Comprehension, Vocabulary, Grammar, Para-jumbles, Sentence Correction",
                },
                {
                    "id": "cuetpg-reasoning",
                    "name": "Part A – Quantitative & Analytical Reasoning",
                    "subject": "Logical Reasoning",
                    "q_type": "MCQ",
                    "count": 10,
                    "marks_per_q": 4,
                    "difficulty": "Medium",
                    "topics": "Quantitative Reasoning, Analytical Skills, Data Interpretation, Logical Puzzles, Series",
                },
                {
                    "id": "cuetpg-ga",
                    "name": "Part A – General Awareness",
                    "subject": "General Knowledge",
                    "q_type": "MCQ",
                    "count": 5,
                    "marks_per_q": 4,
                    "difficulty": "Easy",
                    "topics": "Current Affairs, Static GK, Science & Technology, Sports, Culture",
                },
                {
                    "id": "cuetpg-domain",
                    "name": "Part B – Domain Knowledge",
                    "subject": "Domain Subject",
                    "q_type": "MCQ",
                    "count": 75,
                    "marks_per_q": 4,
                    "difficulty": "Hard",
                    "topics": "Subject-specific core concepts as per chosen PG programme (Science / Arts / Commerce / Law / Management / Social Sciences)",
                },
            ],
            'is_default': True,
        }
    )


def remove_cuet_pg(apps, schema_editor):
    ExamTemplate = apps.get_model('exams', 'ExamTemplate')
    ExamTemplate.objects.filter(name="CUET PG", is_default=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('exams', '0009_add_neet_pg'),
    ]

    operations = [
        migrations.RunPython(add_cuet_pg, remove_cuet_pg),
    ]
