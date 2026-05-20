from django.db import migrations


def add_cuet_ug(apps, schema_editor):
    ExamTemplate = apps.get_model('exams', 'ExamTemplate')
    ExamTemplate.objects.get_or_create(
        name="CUET UG",
        defaults={
            'duration':    "2 Hours 30 Min (modular slots)",
            'total_marks': 700,
            'neg_marking': "-1 per wrong answer",
            'sections': [
                {
                    "id": "cuetug-lang",
                    "name": "Section IA – Language Test",
                    "subject": "English Language",
                    "q_type": "MCQ",
                    "count": 40,
                    "marks_per_q": 5,
                    "difficulty": "Medium",
                    "topics": "Reading Comprehension, Literary Aptitude, Vocabulary, Grammar, Verbal Ability, Para-jumbles",
                },
                {
                    "id": "cuetug-domain1",
                    "name": "Section II – Domain Subject 1",
                    "subject": "Domain Subject",
                    "q_type": "MCQ",
                    "count": 40,
                    "marks_per_q": 5,
                    "difficulty": "Hard",
                    "topics": "Core concepts of chosen domain (Physics / Chemistry / Mathematics / Biology / Accountancy / Economics / History / Political Science / Geography / Sociology / Psychology / Business Studies / etc.)",
                },
                {
                    "id": "cuetug-domain2",
                    "name": "Section II – Domain Subject 2",
                    "subject": "Domain Subject",
                    "q_type": "MCQ",
                    "count": 40,
                    "marks_per_q": 5,
                    "difficulty": "Hard",
                    "topics": "Core concepts of chosen domain (Physics / Chemistry / Mathematics / Biology / Accountancy / Economics / History / Political Science / Geography / Sociology / Psychology / Business Studies / etc.)",
                },
                {
                    "id": "cuetug-gentest",
                    "name": "Section III – General Test",
                    "subject": "General Knowledge",
                    "q_type": "MCQ",
                    "count": 60,
                    "marks_per_q": 5,
                    "difficulty": "Medium",
                    "topics": "General Knowledge, Current Affairs, General Mental Ability, Numerical Ability, Quantitative Reasoning, Logical Reasoning",
                },
            ],
            'is_default': True,
        }
    )


def remove_cuet_ug(apps, schema_editor):
    ExamTemplate = apps.get_model('exams', 'ExamTemplate')
    ExamTemplate.objects.filter(name="CUET UG", is_default=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('exams', '0010_add_cuet_pg'),
    ]

    operations = [
        migrations.RunPython(add_cuet_ug, remove_cuet_ug),
    ]
