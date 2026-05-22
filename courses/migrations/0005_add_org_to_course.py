import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0004_add_is_sys'),
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='course',
            name='org',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='courses',
                to='users.organization',
            ),
        ),
    ]
