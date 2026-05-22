import django.db.models.deletion
from django.db import migrations, models


def backfill_org(apps, schema_editor):
    Paper = apps.get_model('papers', 'Paper')
    for p in Paper.objects.select_related('owner').filter(org__isnull=True):
        if hasattr(p.owner, 'org_id') and p.owner.org_id:
            p.org_id = p.owner.org_id
            p.save(update_fields=['org_id'])


class Migration(migrations.Migration):

    dependencies = [
        ('papers', '0002_initial'),
        ('blueprints', '0004_seed_sys_blueprints'),
        ('subjects', '0001_initial'),
        ('questions', '0003_add_org_course_fks'),
        ('users', '0002_add_organization'),
    ]

    operations = [
        migrations.AddField(
            model_name='paper',
            name='org',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='papers',
                to='users.organization',
            ),
        ),
        migrations.AddField(
            model_name='paper',
            name='blueprint',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='papers',
                to='blueprints.blueprint',
            ),
        ),
        migrations.AddField(
            model_name='paper',
            name='source',
            field=models.CharField(default='manual', max_length=20),
        ),
        migrations.AlterField(
            model_name='paper',
            name='exam_type',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
        migrations.CreateModel(
            name='PaperSection',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('order', models.PositiveIntegerField(default=0)),
                ('paper', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sections', to='papers.paper')),
                ('subject_ref', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='paper_sections',
                    to='subjects.subject',
                )),
            ],
            options={'db_table': 'pd_paper_sections', 'ordering': ['order']},
        ),
        migrations.CreateModel(
            name='PaperQuestion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order', models.PositiveIntegerField(default=0)),
                ('marks_override', models.IntegerField(blank=True, null=True)),
                ('snapshot', models.JSONField(blank=True, null=True)),
                ('section', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='paper_questions', to='papers.papersection')),
                ('question', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='paper_questions',
                    to='questions.question',
                )),
            ],
            options={'db_table': 'pd_paper_questions', 'ordering': ['order']},
        ),
        migrations.RunPython(backfill_org, migrations.RunPython.noop),
    ]