from django.db import models
from courses.models import Course


class Subject(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='subjects')
    name = models.CharField(max_length=200)
    description = models.CharField(max_length=500, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'pd_subjects'
        ordering = ['name']


class SyllabusFile(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='syllabus_files')
    name = models.CharField(max_length=255)
    file = models.FileField(upload_to='syllabus/', null=True, blank=True)
    file_url = models.CharField(max_length=500, null=True, blank=True)
    file_size = models.CharField(max_length=50, null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'pd_syllabus_files'
