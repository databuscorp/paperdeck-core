from django.db import migrations

CMAT = {
    "name": "CMAT",
    "duration": "3 Hours",
    "total_marks": 400,
    "neg_marking": "-1 per wrong answer",
    "sections": [
        {
            "id": "cmat-quant",
            "name": "Quantitative Techniques & Data Interpretation",
            "subject": "Quantitative Aptitude",
            "q_type": "MCQ",
            "count": 25,
            "marks_per_q": 4,
            "difficulty": "Medium",
            "topics": "Arithmetic, Algebra, Geometry, Number Systems, Data Interpretation, Tables, Charts, Data Sufficiency",
        },
        {
            "id": "cmat-reasoning",
            "name": "Logical Reasoning",
            "subject": "Logical Reasoning",
            "q_type": "MCQ",
            "count": 25,
            "marks_per_q": 4,
            "difficulty": "Medium",
            "topics": "Puzzles, Arrangements, Syllogisms, Series, Coding-Decoding, Blood Relations, Direction Sense, Critical Reasoning",
        },
        {
            "id": "cmat-lang",
            "name": "Language Comprehension",
            "subject": "English Language",
            "q_type": "MCQ",
            "count": 25,
            "marks_per_q": 4,
            "difficulty": "Medium",
            "topics": "Reading Comprehension, Vocabulary, Grammar, Sentence Correction, Para-jumbles, Verbal Ability",
        },
        {
            "id": "cmat-ga",
            "name": "General Awareness",
            "subject": "General Knowledge",
            "q_type": "MCQ",
            "count": 25,
            "marks_per_q": 4,
            "difficulty": "Easy",
            "topics": "Current Affairs, Business & Economy, History, Geography, Science & Technology, Sports, Awards, Government Schemes",
        },
        {
            "id": "cmat-innovation",
            "name": "Innovation & Entrepreneurship",
            "subject": "General Knowledge",
            "q_type": "MCQ",
            "count": 25,
            "marks_per_q": 4,
            "difficulty": "Medium",
            "topics": "Startup Ecosystem, Business Models, Innovation Concepts, Entrepreneurship Cases, Government Initiatives, Social Entrepreneurship",
        },
    ],
}

MAT = {
    "name": "MAT",
    "duration": "2 Hours 30 Min",
    "total_marks": 200,
    "neg_marking": "-0.25 per wrong answer",
    "sections": [
        {
            "id": "mat-lang",
            "name": "Language Comprehension",
            "subject": "English Language",
            "q_type": "MCQ",
            "count": 40,
            "marks_per_q": 1,
            "difficulty": "Medium",
            "topics": "Reading Comprehension, Vocabulary, Grammar, Sentence Correction, Para-jumbles, Analogies, Verbal Reasoning",
        },
        {
            "id": "mat-math",
            "name": "Mathematical Skills",
            "subject": "Quantitative Aptitude",
            "q_type": "MCQ",
            "count": 40,
            "marks_per_q": 1,
            "difficulty": "Medium",
            "topics": "Arithmetic, Algebra, Geometry, Trigonometry, Number Systems, Data Interpretation, Data Sufficiency",
        },
        {
            "id": "mat-da",
            "name": "Data Analysis & Sufficiency",
            "subject": "Logical Reasoning",
            "q_type": "MCQ",
            "count": 40,
            "marks_per_q": 1,
            "difficulty": "Hard",
            "topics": "Data Interpretation Sets, Tables, Graphs, Caselets, Data Sufficiency, Quantitative Reasoning",
        },
        {
            "id": "mat-int",
            "name": "Intelligence & Critical Reasoning",
            "subject": "Logical Reasoning",
            "q_type": "MCQ",
            "count": 40,
            "marks_per_q": 1,
            "difficulty": "Medium",
            "topics": "Puzzles, Arrangements, Series, Coding-Decoding, Blood Relations, Syllogisms, Critical Reasoning, Visual Reasoning",
        },
        {
            "id": "mat-ibe",
            "name": "Indian & Global Environment",
            "subject": "General Knowledge",
            "q_type": "MCQ",
            "count": 40,
            "marks_per_q": 1,
            "difficulty": "Easy",
            "topics": "Current Affairs, Business & Economy, Indian Constitution, Geography, Science & Technology, Sports, Awards, International Affairs",
        },
    ],
}


def add_cmat_mat(apps, schema_editor):
    ExamTemplate = apps.get_model('exams', 'ExamTemplate')
    for tpl in [CMAT, MAT]:
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


def remove_cmat_mat(apps, schema_editor):
    ExamTemplate = apps.get_model('exams', 'ExamTemplate')
    ExamTemplate.objects.filter(name__in=["CMAT", "MAT"], is_default=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('exams', '0014_add_iift_tissnet'),
    ]

    operations = [
        migrations.RunPython(add_cmat_mat, remove_cmat_mat),
    ]
