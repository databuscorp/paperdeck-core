import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0006_seed_sys_courses'),
        ('users', '0003_backfill_org'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='CourseSubscription',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('subscribed_at', models.DateTimeField(auto_now_add=True)),
                ('course', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='subscriptions',
                    to='courses.course',
                )),
                ('org', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='course_subscriptions',
                    to='users.organization',
                )),
                ('subscribed_by', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'db_table': 'pd_course_subscriptions',
                'ordering': ['-subscribed_at'],
            },
        ),
        migrations.AddConstraint(
            model_name='coursesubscription',
            constraint=models.UniqueConstraint(
                fields=['course', 'org'],
                name='unique_course_org_sub',
            ),
        ),
    ]
