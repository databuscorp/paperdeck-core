import uuid
import django.db.models.deletion
from django.db import migrations, models


def rebuild_course_table(apps, schema_editor):
    schema_editor.execute("""
        -- Drop all FK constraints referencing pd_courses
        DO $$
        DECLARE r RECORD;
        BEGIN
            FOR r IN (
                SELECT tc.table_name, tc.constraint_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.referential_constraints rc
                    ON tc.constraint_name = rc.constraint_name
                JOIN information_schema.table_constraints ctu
                    ON rc.unique_constraint_name = ctu.constraint_name
                WHERE ctu.table_name = 'pd_courses'
                  AND tc.constraint_type = 'FOREIGN KEY'
            ) LOOP
                EXECUTE 'ALTER TABLE ' || quote_ident(r.table_name) ||
                        ' DROP CONSTRAINT ' || quote_ident(r.constraint_name);
            END LOOP;
        END $$;

        DROP TABLE IF EXISTS pd_courses;

        CREATE TABLE courses (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            authority_id UUID REFERENCES exam_authorities(id) ON DELETE SET NULL,
            created_by_id INTEGER REFERENCES pd_users(id) ON DELETE SET NULL,
            name VARCHAR(255) NOT NULL,
            slug VARCHAR(255) UNIQUE NOT NULL,
            course_type VARCHAR(20) NOT NULL DEFAULT 'common',
            description TEXT,
            grade_level VARCHAR(100),
            duration_minutes INTEGER NOT NULL DEFAULT 0,
            total_marks INTEGER NOT NULL DEFAULT 0,
            instructions TEXT,
            thumbnail VARCHAR(100),
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        );

        ALTER TABLE pd_staff DROP COLUMN IF EXISTS course_id;
        ALTER TABLE pd_staff ADD COLUMN course_id UUID REFERENCES courses(id) ON DELETE CASCADE;

        ALTER TABLE pd_students DROP COLUMN IF EXISTS course_id;
        ALTER TABLE pd_students ADD COLUMN course_id UUID REFERENCES courses(id) ON DELETE CASCADE;

        ALTER TABLE pd_subjects DROP COLUMN IF EXISTS course_id;
        ALTER TABLE pd_subjects ADD COLUMN course_id UUID REFERENCES courses(id) ON DELETE CASCADE;
    """)


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0002_initial'),
        ('exams', '0017_add_exam_authority'),
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.DeleteModel(name='Course'),
                migrations.CreateModel(
                    name='Course',
                    fields=[
                        ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                        ('authority', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='courses', to='exams.examauthority')),
                        ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_courses', to='users.user')),
                        ('name', models.CharField(max_length=255)),
                        ('slug', models.SlugField(max_length=255, unique=True)),
                        ('course_type', models.CharField(choices=[('common', 'Common'), ('custom', 'Custom')], default='common', max_length=20)),
                        ('description', models.TextField(blank=True, null=True)),
                        ('grade_level', models.CharField(blank=True, max_length=100, null=True)),
                        ('duration_minutes', models.PositiveIntegerField(default=0)),
                        ('total_marks', models.PositiveIntegerField(default=0)),
                        ('instructions', models.TextField(blank=True, null=True)),
                        ('thumbnail', models.ImageField(blank=True, null=True, upload_to='courses/thumbnails/')),
                        ('is_active', models.BooleanField(default=True)),
                        ('created_at', models.DateTimeField(auto_now_add=True)),
                        ('updated_at', models.DateTimeField(auto_now=True)),
                    ],
                    options={'db_table': 'courses', 'ordering': ['name']},
                ),
            ],
            database_operations=[
                migrations.RunPython(rebuild_course_table, migrations.RunPython.noop),
            ],
        ),
    ]
