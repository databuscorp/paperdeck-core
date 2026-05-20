from django.db import migrations

UPSC_PAPER1 = {
    "name": "UPSC CSE Prelims Paper 1",
    "duration": "2 Hours",
    "total_marks": 200,
    "neg_marking": "-1/3 per wrong answer",
    "sections": [
        {
            "id": "upsc-gs1",
            "name": "General Studies I",
            "subject": "General Knowledge",
            "q_type": "MCQ",
            "count": 100,
            "marks_per_q": 2,
            "difficulty": "Hard",
            "topics": "History, Geography, Polity, Economy, Environment, Science & Technology, Current Affairs",
        },
    ],
}

UPSC_PAPER2 = {
    "name": "UPSC CSE Prelims Paper 2",
    "duration": "2 Hours",
    "total_marks": 200,
    "neg_marking": "-1/3 per wrong answer (qualifying; 33% cutoff)",
    "sections": [
        {
            "id": "upsc-csat-comprehension",
            "name": "Comprehension",
            "subject": "English Language",
            "q_type": "MCQ",
            "count": 25,
            "marks_per_q": 2.5,
            "difficulty": "Medium",
            "topics": "Reading Comprehension, Passage Analysis",
        },
        {
            "id": "upsc-csat-reasoning",
            "name": "Logical Reasoning & Analytical Ability",
            "subject": "Logical Reasoning",
            "q_type": "MCQ",
            "count": 30,
            "marks_per_q": 2.5,
            "difficulty": "Medium",
            "topics": "Puzzles, Arrangements, Syllogisms, Data Sufficiency",
        },
        {
            "id": "upsc-csat-quant",
            "name": "Basic Numeracy & Data Interpretation",
            "subject": "Quantitative Aptitude",
            "q_type": "MCQ",
            "count": 25,
            "marks_per_q": 2.5,
            "difficulty": "Medium",
            "topics": "Arithmetic, Number Systems, Data Interpretation, DI Sets",
        },
    ],
}


def split_upsc_prelims(apps, schema_editor):
    ExamTemplate = apps.get_model('exams', 'ExamTemplate')
    ExamTemplate.objects.filter(name="UPSC CSE (Prelims)").delete()
    for tpl in [UPSC_PAPER1, UPSC_PAPER2]:
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


def merge_upsc_prelims(apps, schema_editor):
    ExamTemplate = apps.get_model('exams', 'ExamTemplate')
    ExamTemplate.objects.filter(
        name__in=["UPSC CSE Prelims Paper 1", "UPSC CSE Prelims Paper 2"]
    ).delete()
    ExamTemplate.objects.get_or_create(
        name="UPSC CSE (Prelims)",
        defaults={
            'duration':    "4 Hours (2 papers)",
            'total_marks': 400,
            'neg_marking': "-1/3 per wrong",
            'sections':    UPSC_PAPER1['sections'] + UPSC_PAPER2['sections'],
            'is_default':  True,
        }
    )


class Migration(migrations.Migration):

    dependencies = [
        ('exams', '0003_split_jee_advanced'),
    ]

    operations = [
        migrations.RunPython(split_upsc_prelims, merge_upsc_prelims),
    ]
