from django.db import migrations


class Migration(migrations.Migration):
    """
    papers.course_id was created as bigint when courses.id was still a BigAutoField.
    Courses later migrated to UUIDField. All existing course_id values are NULL so
    the cast is safe — no data conversion required.
    """

    dependencies = [
        ('papers', '0003_add_org_blueprint_sections'),
        ('courses', '__latest__'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                ALTER TABLE pd_papers
                    DROP CONSTRAINT IF EXISTS pd_papers_course_id_id_fk,
                    DROP CONSTRAINT IF EXISTS pd_papers_course_id_fkey,
                    DROP CONSTRAINT IF EXISTS pd_papers_course_id_courses_course_id_fk;

                ALTER TABLE pd_papers
                    ALTER COLUMN course_id TYPE uuid
                    USING course_id::text::uuid;

                ALTER TABLE pd_papers
                    ADD CONSTRAINT pd_papers_course_id_fkey
                    FOREIGN KEY (course_id) REFERENCES courses(id)
                    ON DELETE SET NULL DEFERRABLE INITIALLY DEFERRED;
            """,
            reverse_sql="""
                ALTER TABLE pd_papers
                    DROP CONSTRAINT IF EXISTS pd_papers_course_id_fkey;

                ALTER TABLE pd_papers
                    ALTER COLUMN course_id TYPE bigint
                    USING NULL;
            """,
        ),
    ]