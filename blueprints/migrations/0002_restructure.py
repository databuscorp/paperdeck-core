import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('blueprints', '0001_initial'),
        ('courses', '0006_seed_sys_courses'),
        ('users', '0003_backfill_org'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Drop and recreate pd_blueprints cleanly (no rows exist)
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql='DROP TABLE IF EXISTS pd_blueprints CASCADE;',
                    reverse_sql='',
                ),
            ],
            state_operations=[
                migrations.DeleteModel('Blueprint'),
            ],
        ),
        migrations.CreateModel(
            name='Blueprint',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('duration', models.CharField(default='3 Hours', max_length=50)),
                ('total_marks', models.IntegerField(default=0)),
                ('neg_marking_enabled', models.BooleanField(default=False)),
                ('neg_marking_value', models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('course', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='blueprints',
                    to='courses.course',
                )),
                ('org', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='blueprints',
                    to='users.organization',
                )),
                ('created_by', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='blueprints',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'db_table': 'pd_blueprints',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='BlueprintSection',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('subject', models.CharField(max_length=200)),
                ('topics', models.TextField(blank=True, default='')),
                ('q_type', models.CharField(max_length=50)),
                ('count', models.PositiveIntegerField(default=0)),
                ('marks_per_q', models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ('neg_marks_per_q', models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ('difficulty', models.CharField(default='Mixed', max_length=50)),
                ('bloom', models.CharField(default='Mixed', max_length=50)),
                ('order', models.PositiveIntegerField(default=0)),
                ('blueprint', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='sections',
                    to='blueprints.blueprint',
                )),
            ],
            options={
                'db_table': 'pd_blueprint_sections',
                'ordering': ['order'],
            },
        ),
    ]
