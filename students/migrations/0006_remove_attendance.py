from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('students', '0005_add_org_fk'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='student',
            name='attendance',
        ),
    ]
