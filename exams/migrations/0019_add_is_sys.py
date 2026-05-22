from django.db import migrations, models

SYS_AUTHORITY_SHORT_NAMES = [
    "NTA", "JAB", "UPSC", "SSC", "Consortium NLU", "IIMs",
    "IIT/IISc", "XLRI", "GMAC", "SIU", "IIFT", "TISS",
    "AIMA", "NBEMS", "ETS",
]


def mark_sys_authorities(apps, schema_editor):
    ExamAuthority = apps.get_model('exams', 'ExamAuthority')
    ExamAuthority.objects.filter(short_name__in=SYS_AUTHORITY_SHORT_NAMES).update(is_sys=True)


class Migration(migrations.Migration):

    dependencies = [
        ('exams', '0018_seed_exam_authorities'),
    ]

    operations = [
        migrations.AddField(
            model_name='examauthority',
            name='is_sys',
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(mark_sys_authorities, migrations.RunPython.noop),
    ]
