import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('subjects', '0002_update_course_fk_uuid'),
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='subject',
            name='org',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='subjects',
                to='users.organization',
            ),
        ),
        migrations.AddField(
            model_name='subject',
            name='created_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='created_subjects',
                to='users.user',
            ),
        ),
        migrations.AddField(
            model_name='subject',
            name='is_sys',
            field=models.BooleanField(default=False),
        ),
    ]