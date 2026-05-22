import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('staff', '0001_initial'),
        ('courses', '0003_replace_course_model'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name='staff',
                    name='course',
                    field=models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='staff_members',
                        to='courses.course',
                    ),
                ),
            ],
            database_operations=[],
        ),
    ]