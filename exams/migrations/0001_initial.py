from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='ExamTemplate',
            fields=[
                ('id',          models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name',        models.CharField(max_length=100, unique=True)),
                ('duration',    models.CharField(max_length=50)),
                ('total_marks', models.FloatField()),
                ('neg_marking', models.CharField(max_length=100)),
                ('sections',    models.JSONField(default=list)),
                ('is_default',  models.BooleanField(default=True)),
                ('created_at',  models.DateTimeField(auto_now_add=True)),
            ],
            options={'db_table': 'pd_exam_templates', 'ordering': ['name']},
        ),
    ]
