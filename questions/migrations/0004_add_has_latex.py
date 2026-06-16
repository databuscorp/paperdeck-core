from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("questions", "0003_add_org_course_fks"),
    ]

    operations = [
        migrations.AddField(
            model_name="question",
            name="has_latex",
            field=models.BooleanField(default=False),
        ),
    ]
