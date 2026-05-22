import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('blueprints', '0002_restructure'),
        ('users', '0003_backfill_org'),
    ]

    operations = [
        migrations.AlterField(
            model_name='blueprint',
            name='org',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='blueprints',
                to='users.organization',
            ),
        ),
        migrations.AddField(
            model_name='blueprint',
            name='is_sys',
            field=models.BooleanField(default=False),
        ),
    ]
