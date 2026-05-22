import django.db.models.deletion
from django.db import migrations, models


def backfill_org(apps, schema_editor):
    Question = apps.get_model('questions', 'Question')
    for q in Question.objects.select_related('owner').filter(org__isnull=True):
        if hasattr(q.owner, 'org_id') and q.owner.org_id:
            q.org_id = q.owner.org_id
            q.save(update_fields=['org_id'])


class Migration(migrations.Migration):

    dependencies = [
        ('questions', '0002_add_image_svg'),
        ('courses', '0001_initial'),
        ('subjects', '0005_add_topics_chapters'),
        ('users', '0002_add_organization'),
    ]

    operations = [
        migrations.AddField(
            model_name='question',
            name='org',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='questions',
                to='users.organization',
            ),
        ),
        migrations.AddField(
            model_name='question',
            name='course',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='questions',
                to='courses.course',
            ),
        ),
        migrations.AddField(
            model_name='question',
            name='subject_ref',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='questions',
                to='subjects.subject',
            ),
        ),
        migrations.AddField(
            model_name='question',
            name='topic_ref',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='questions',
                to='subjects.topic',
            ),
        ),
        migrations.AddField(
            model_name='question',
            name='neg_marks',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='question',
            name='source',
            field=models.CharField(default='manual', max_length=20),
        ),
        migrations.RunPython(backfill_org, migrations.RunPython.noop),
    ]