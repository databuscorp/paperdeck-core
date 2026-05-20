from django.db import migrations


def add_neet_pg(apps, schema_editor):
    ExamTemplate = apps.get_model('exams', 'ExamTemplate')
    ExamTemplate.objects.get_or_create(
        name="NEET PG",
        defaults={
            'duration':    "3 Hours 30 Min",
            'total_marks': 800,
            'neg_marking': "-1 per wrong answer",
            'sections': [
                {
                    "id": "neetpg-anatomy",
                    "name": "Anatomy",
                    "subject": "Anatomy",
                    "q_type": "MCQ",
                    "count": 18,
                    "marks_per_q": 4,
                    "difficulty": "Hard",
                    "topics": "General Anatomy, Gross Anatomy, Neuroanatomy, Embryology, Histology",
                },
                {
                    "id": "neetpg-physio",
                    "name": "Physiology",
                    "subject": "Physiology",
                    "q_type": "MCQ",
                    "count": 18,
                    "marks_per_q": 4,
                    "difficulty": "Hard",
                    "topics": "General Physiology, CVS, Respiratory, Renal, Neurophysiology, Endocrinology, GIT",
                },
                {
                    "id": "neetpg-biochem",
                    "name": "Biochemistry",
                    "subject": "Biochemistry",
                    "q_type": "MCQ",
                    "count": 14,
                    "marks_per_q": 4,
                    "difficulty": "Hard",
                    "topics": "Enzymes, Metabolism, Molecular Biology, Vitamins, Genetics, Clinical Biochemistry",
                },
                {
                    "id": "neetpg-path",
                    "name": "Pathology",
                    "subject": "Pathology",
                    "q_type": "MCQ",
                    "count": 22,
                    "marks_per_q": 4,
                    "difficulty": "Hard",
                    "topics": "General Pathology, Systemic Pathology, Hematology, Clinical Pathology, Oncology",
                },
                {
                    "id": "neetpg-micro",
                    "name": "Microbiology",
                    "subject": "Microbiology",
                    "q_type": "MCQ",
                    "count": 18,
                    "marks_per_q": 4,
                    "difficulty": "Hard",
                    "topics": "Bacteriology, Virology, Parasitology, Mycology, Immunology, Sterilization",
                },
                {
                    "id": "neetpg-pharma",
                    "name": "Pharmacology",
                    "subject": "Pharmacology",
                    "q_type": "MCQ",
                    "count": 22,
                    "marks_per_q": 4,
                    "difficulty": "Hard",
                    "topics": "General Pharmacology, ANS, CVS Drugs, CNS Drugs, Chemotherapy, Endocrine Pharmacology",
                },
                {
                    "id": "neetpg-forensic",
                    "name": "Forensic Medicine & Toxicology",
                    "subject": "Forensic Medicine",
                    "q_type": "MCQ",
                    "count": 8,
                    "marks_per_q": 4,
                    "difficulty": "Medium",
                    "topics": "Forensic Pathology, Medical Jurisprudence, Toxicology, Clinical Forensics",
                },
                {
                    "id": "neetpg-medicine",
                    "name": "Medicine & Allied",
                    "subject": "Medicine",
                    "q_type": "MCQ",
                    "count": 30,
                    "marks_per_q": 4,
                    "difficulty": "Hard",
                    "topics": "Internal Medicine, Psychiatry, Dermatology, Venereology, Neurology, Nephrology, Cardiology",
                },
                {
                    "id": "neetpg-surgery",
                    "name": "Surgery & Allied",
                    "subject": "Surgery",
                    "q_type": "MCQ",
                    "count": 25,
                    "marks_per_q": 4,
                    "difficulty": "Hard",
                    "topics": "General Surgery, Orthopedics, Anesthesia, Radiology, Radiodiagnosis",
                },
                {
                    "id": "neetpg-obg",
                    "name": "Obstetrics & Gynaecology",
                    "subject": "Obstetrics & Gynaecology",
                    "q_type": "MCQ",
                    "count": 18,
                    "marks_per_q": 4,
                    "difficulty": "Hard",
                    "topics": "Obstetrics, Gynaecology, Reproductive Medicine, Family Planning",
                },
                {
                    "id": "neetpg-paeds",
                    "name": "Paediatrics",
                    "subject": "Paediatrics",
                    "q_type": "MCQ",
                    "count": 14,
                    "marks_per_q": 4,
                    "difficulty": "Hard",
                    "topics": "Neonatology, Growth & Development, Paediatric Diseases, Immunization, Nutrition",
                },
                {
                    "id": "neetpg-psm",
                    "name": "Community Medicine (PSM)",
                    "subject": "Community Medicine",
                    "q_type": "MCQ",
                    "count": 14,
                    "marks_per_q": 4,
                    "difficulty": "Medium",
                    "topics": "Epidemiology, Biostatistics, Health Programs, Nutrition, Environment & Occupational Health",
                },
                {
                    "id": "neetpg-ent-oph",
                    "name": "ENT & Ophthalmology",
                    "subject": "ENT & Ophthalmology",
                    "q_type": "MCQ",
                    "count": 10,
                    "marks_per_q": 4,
                    "difficulty": "Medium",
                    "topics": "Ear, Nose & Throat Diseases, Eye Disorders, Refraction, Glaucoma, Retinal Diseases",
                },
            ],
            'is_default': True,
        }
    )


def remove_neet_pg(apps, schema_editor):
    ExamTemplate = apps.get_model('exams', 'ExamTemplate')
    ExamTemplate.objects.filter(name="NEET PG", is_default=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('exams', '0008_add_gate_ee'),
    ]

    operations = [
        migrations.RunPython(add_neet_pg, remove_neet_pg),
    ]
