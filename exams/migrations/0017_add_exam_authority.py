import uuid
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('exams', '0016_add_gmat_gre'),
    ]

    operations = [
        migrations.CreateModel(
            name='ExamAuthority',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('short_name', models.CharField(max_length=50, unique=True)),
                ('authority_type', models.CharField(choices=[('board', 'Board'), ('govt', 'Government'), ('university', 'University'), ('coaching', 'Coaching'), ('institution', 'Institution'), ('other', 'Other')], max_length=20)),
                ('description', models.TextField(blank=True, null=True)),
                ('website', models.URLField(blank=True, null=True)),
                ('logo', models.ImageField(blank=True, null=True, upload_to='exam_authorities/logos/')),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'exam_authorities',
                'ordering': ['name'],
            },
        ),
    ]
