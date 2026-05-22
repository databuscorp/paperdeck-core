import django.db.models.deletion
from django.db import migrations, models


def copy_fk_to_m2m(apps, schema_editor):
    Staff = apps.get_model('staff', 'Staff')
    StaffCourse = apps.get_model('staff', 'StaffCourse')
    db = schema_editor.connection.alias
    for s in Staff.objects.using(db).all():
        # course_id still exists in the DB at this point
        if s.course_id:
            StaffCourse.objects.using(db).get_or_create(staff=s, course_id=s.course_id)


def reverse_m2m_to_fk(apps, schema_editor):
    pass  # irreversible data migration — column will be re-added by RemoveField reverse


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0007_course_subscription'),
        ('staff', '0003_add_user_fk'),
    ]

    operations = [
        # 1. Create the through model / junction table
        migrations.CreateModel(
            name='StaffCourse',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False)),
                ('staff', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='staff.staff')),
                ('course', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='courses.course')),
            ],
            options={'db_table': 'pd_staff_courses'},
        ),
        migrations.AlterUniqueTogether(
            name='staffcourse',
            unique_together={('staff', 'course')},
        ),
        # 2. Add M2M field via the through model
        migrations.AddField(
            model_name='staff',
            name='courses',
            field=models.ManyToManyField(
                blank=True,
                related_name='staff_members',
                through='staff.StaffCourse',
                to='courses.course',
            ),
        ),
        # 3. Copy existing FK data into the junction table
        migrations.RunPython(copy_fk_to_m2m, reverse_m2m_to_fk),
        # 4. Remove the old course FK from model state and DB
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RemoveField(model_name='staff', name='course'),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql='ALTER TABLE pd_staff DROP COLUMN course_id',
                    reverse_sql='ALTER TABLE pd_staff ADD COLUMN course_id integer',
                ),
            ],
        ),
    ]
