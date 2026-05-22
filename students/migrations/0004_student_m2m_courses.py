import django.db.models.deletion
from django.db import migrations, models


def copy_fk_to_m2m(apps, schema_editor):
    Student = apps.get_model('students', 'Student')
    StudentCourse = apps.get_model('students', 'StudentCourse')
    db = schema_editor.connection.alias
    for s in Student.objects.using(db).all():
        if s.course_id:
            StudentCourse.objects.using(db).get_or_create(student=s, course_id=s.course_id)


def reverse_m2m_to_fk(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0007_course_subscription'),
        ('students', '0003_add_user_fk'),
    ]

    operations = [
        # 1. Create through model / junction table
        migrations.CreateModel(
            name='StudentCourse',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False)),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='students.student')),
                ('course', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='courses.course')),
            ],
            options={'db_table': 'pd_student_courses'},
        ),
        migrations.AlterUniqueTogether(
            name='studentcourse',
            unique_together={('student', 'course')},
        ),
        # 2. Add M2M field via the through model
        migrations.AddField(
            model_name='student',
            name='courses',
            field=models.ManyToManyField(
                blank=True,
                related_name='students',
                through='students.StudentCourse',
                to='courses.course',
            ),
        ),
        # 3. Copy existing FK data into the junction table
        migrations.RunPython(copy_fk_to_m2m, reverse_m2m_to_fk),
        # 4. Remove old FK from state and DB
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RemoveField(model_name='student', name='course'),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql='ALTER TABLE pd_students DROP COLUMN course_id',
                    reverse_sql='ALTER TABLE pd_students ADD COLUMN course_id integer',
                ),
            ],
        ),
    ]
