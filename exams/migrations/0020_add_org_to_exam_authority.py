import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('exams', '0019_add_is_sys'),
        ('users', '0002_add_organization'),
    ]

    operations = [
        migrations.AddField(
            model_name='examauthority',
            name='org',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='exam_authorities',
                to='users.organization',
            ),
        ),
    ]
