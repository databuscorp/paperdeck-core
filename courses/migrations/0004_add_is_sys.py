from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0003_replace_course_model'),
    ]

    operations = [
        migrations.AddField(
            model_name='course',
            name='is_sys',
            field=models.BooleanField(default=False),
        ),
    ]
