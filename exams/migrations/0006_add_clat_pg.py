from django.db import migrations

CLAT_PG = {
    "name": "CLAT PG",
    "duration": "2 Hours",
    "total_marks": 120,
    "neg_marking": "-0.25 per wrong answer",
    "sections": [
        {
            "id": "clatp-const",
            "name": "Constitutional Law",
            "subject": "Constitutional Law",
            "q_type": "MCQ",
            "count": 40,
            "marks_per_q": 1,
            "difficulty": "Hard",
            "topics": "Fundamental Rights, DPSPs, Constitutional Amendments, Federalism, Parliamentary System, Judicial Review",
        },
        {
            "id": "clatp-juris",
            "name": "Jurisprudence",
            "subject": "Jurisprudence",
            "q_type": "MCQ",
            "count": 20,
            "marks_per_q": 1,
            "difficulty": "Hard",
            "topics": "Schools of Law, Sources of Law, Rights and Duties, Legal Concepts, Theories of Punishment",
        },
        {
            "id": "clatp-contract",
            "name": "Law of Contracts",
            "subject": "Law",
            "q_type": "MCQ",
            "count": 12,
            "marks_per_q": 1,
            "difficulty": "Medium",
            "topics": "Formation of Contract, Consideration, Breach, Remedies, Specific Relief",
        },
        {
            "id": "clatp-torts",
            "name": "Law of Torts",
            "subject": "Law",
            "q_type": "MCQ",
            "count": 12,
            "marks_per_q": 1,
            "difficulty": "Medium",
            "topics": "Negligence, Nuisance, Defamation, Strict & Absolute Liability, Consumer Protection",
        },
        {
            "id": "clatp-criminal",
            "name": "Criminal Law",
            "subject": "Law",
            "q_type": "MCQ",
            "count": 12,
            "marks_per_q": 1,
            "difficulty": "Medium",
            "topics": "IPC, CrPC, Evidence Act, Offences Against Person & Property, Mens Rea",
        },
        {
            "id": "clatp-intl",
            "name": "International Law",
            "subject": "Law",
            "q_type": "MCQ",
            "count": 12,
            "marks_per_q": 1,
            "difficulty": "Hard",
            "topics": "Sources of International Law, UN System, Treaties, State Responsibility, Human Rights",
        },
        {
            "id": "clatp-ipr",
            "name": "IPR & Other Law",
            "subject": "Law",
            "q_type": "MCQ",
            "count": 12,
            "marks_per_q": 1,
            "difficulty": "Medium",
            "topics": "Patents, Trademarks, Copyright, Administrative Law, Environmental Law",
        },
    ],
}


def add_clat_pg(apps, schema_editor):
    ExamTemplate = apps.get_model('exams', 'ExamTemplate')
    ExamTemplate.objects.get_or_create(
        name=CLAT_PG['name'],
        defaults={
            'duration':    CLAT_PG['duration'],
            'total_marks': CLAT_PG['total_marks'],
            'neg_marking': CLAT_PG['neg_marking'],
            'sections':    CLAT_PG['sections'],
            'is_default':  True,
        }
    )


def remove_clat_pg(apps, schema_editor):
    ExamTemplate = apps.get_model('exams', 'ExamTemplate')
    ExamTemplate.objects.filter(name="CLAT PG", is_default=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('exams', '0005_add_ssc_cgl_tier2'),
    ]

    operations = [
        migrations.RunPython(add_clat_pg, remove_clat_pg),
    ]
