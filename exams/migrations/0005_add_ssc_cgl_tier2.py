from django.db import migrations

SSC_CGL_TIER2 = {
    "name": "SSC CGL Tier 2",
    "duration": "2 Hours 15 Min",
    "total_marks": 450,
    "neg_marking": "-1 per wrong answer",
    "sections": [
        {
            "id": "ssc2-math",
            "name": "Mathematical Abilities",
            "subject": "Mathematics",
            "q_type": "MCQ",
            "count": 30,
            "marks_per_q": 3,
            "difficulty": "Medium",
            "topics": "Arithmetic, Algebra, Geometry, Trigonometry, Data Interpretation",
        },
        {
            "id": "ssc2-reasoning",
            "name": "Reasoning & General Intelligence",
            "subject": "Logical Reasoning",
            "q_type": "MCQ",
            "count": 30,
            "marks_per_q": 3,
            "difficulty": "Medium",
            "topics": "Analogies, Series, Coding-Decoding, Puzzles, Matrix, Venn Diagrams",
        },
        {
            "id": "ssc2-english",
            "name": "English Language & Comprehension",
            "subject": "English Language",
            "q_type": "MCQ",
            "count": 45,
            "marks_per_q": 3,
            "difficulty": "Medium",
            "topics": "Reading Comprehension, Cloze Test, Error Detection, Synonyms, Antonyms, One Word Substitution",
        },
        {
            "id": "ssc2-ga",
            "name": "General Awareness",
            "subject": "General Knowledge",
            "q_type": "MCQ",
            "count": 25,
            "marks_per_q": 3,
            "difficulty": "Easy",
            "topics": "Current Affairs, History, Geography, Polity, Economy, Science & Technology",
        },
        {
            "id": "ssc2-computer",
            "name": "Computer Knowledge",
            "subject": "Computer Science",
            "q_type": "MCQ",
            "count": 20,
            "marks_per_q": 3,
            "difficulty": "Easy",
            "topics": "MS Office, Internet, Networking Basics, Hardware & Software, Shortcuts",
        },
    ],
}


def add_ssc_tier2(apps, schema_editor):
    ExamTemplate = apps.get_model('exams', 'ExamTemplate')
    ExamTemplate.objects.get_or_create(
        name=SSC_CGL_TIER2['name'],
        defaults={
            'duration':    SSC_CGL_TIER2['duration'],
            'total_marks': SSC_CGL_TIER2['total_marks'],
            'neg_marking': SSC_CGL_TIER2['neg_marking'],
            'sections':    SSC_CGL_TIER2['sections'],
            'is_default':  True,
        }
    )


def remove_ssc_tier2(apps, schema_editor):
    ExamTemplate = apps.get_model('exams', 'ExamTemplate')
    ExamTemplate.objects.filter(name="SSC CGL Tier 2", is_default=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('exams', '0004_split_upsc_prelims'),
    ]

    operations = [
        migrations.RunPython(add_ssc_tier2, remove_ssc_tier2),
    ]
