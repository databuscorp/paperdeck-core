import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('staff', '0004_staff_m2m_courses'),
        ('users', '0002_add_organization'),
    ]

    operations = [
        migrations.AddField(
            model_name='staff',
            name='org',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='staff_members',
                to='users.organization',
            ),
        ),
    ]
