from django.db import migrations

IIFT = {
    "name": "IIFT",
    "duration": "2 Hours",
    "total_marks": 300,
    "neg_marking": "-1 per wrong answer",
    "sections": [
        {
            "id": "iift-varc",
            "name": "Verbal Ability & Reading Comprehension",
            "subject": "English Language",
            "q_type": "MCQ",
            "count": 35,
            "marks_per_q": 3,
            "difficulty": "Hard",
            "topics": "Reading Comprehension, Vocabulary, Grammar, Sentence Correction, Para-jumbles, Analogies, Idioms",
        },
        {
            "id": "iift-dilr",
            "name": "Data Interpretation & Logical Reasoning",
            "subject": "Logical Reasoning",
            "q_type": "MCQ",
            "count": 30,
            "marks_per_q": 3,
            "difficulty": "Hard",
            "topics": "Data Interpretation Sets, Tables, Charts, Graphs, Logical Puzzles, Arrangements, Syllogisms",
        },
        {
            "id": "iift-quant",
            "name": "Quantitative Analysis",
            "subject": "Quantitative Aptitude",
            "q_type": "MCQ",
            "count": 25,
            "marks_per_q": 3,
            "difficulty": "Hard",
            "topics": "Arithmetic, Algebra, Geometry, Trigonometry, Number Systems, Modern Maths, Permutation & Combination",
        },
        {
            "id": "iift-gk",
            "name": "General Knowledge & Awareness",
            "subject": "General Knowledge",
            "q_type": "MCQ",
            "count": 10,
            "marks_per_q": 1.5,
            "difficulty": "Medium",
            "topics": "International Trade, Business & Economy, Current Affairs, World Affairs, Geography, Awards & Honours",
        },
    ],
}

TISSNET = {
    "name": "TISSNET",
    "duration": "100 Minutes",
    "total_marks": 100,
    "neg_marking": "No negative marking",
    "sections": [
        {
            "id": "tiss-english",
            "name": "English Proficiency",
            "subject": "English Language",
            "q_type": "MCQ",
            "count": 30,
            "marks_per_q": 1,
            "difficulty": "Medium",
            "topics": "Reading Comprehension, Vocabulary, Grammar, Sentence Correction, Para-jumbles, Verbal Reasoning",
        },
        {
            "id": "tiss-maths",
            "name": "Mathematics & Logical Reasoning",
            "subject": "Quantitative Aptitude",
            "q_type": "MCQ",
            "count": 40,
            "marks_per_q": 1,
            "difficulty": "Medium",
            "topics": "Arithmetic, Algebra, Geometry, Data Interpretation, Logical Puzzles, Arrangements, Series, Coding-Decoding",
        },
        {
            "id": "tiss-ga",
            "name": "General Awareness",
            "subject": "General Knowledge",
            "q_type": "MCQ",
            "count": 30,
            "marks_per_q": 1,
            "difficulty": "Medium",
            "topics": "Current Affairs, Social Issues, Government Schemes, History, Geography, Science & Technology, Sports, Awards",
        },
    ],
}


def add_iift_tissnet(apps, schema_editor):
    ExamTemplate = apps.get_model('exams', 'ExamTemplate')
    for tpl in [IIFT, TISSNET]:
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


def remove_iift_tissnet(apps, schema_editor):
    ExamTemplate = apps.get_model('exams', 'ExamTemplate')
    ExamTemplate.objects.filter(name__in=["IIFT", "TISSNET"], is_default=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('exams', '0013_add_snap_nmat'),
    ]

    operations = [
        migrations.RunPython(add_iift_tissnet, remove_iift_tissnet),
    ]
