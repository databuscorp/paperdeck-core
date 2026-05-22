from django.db import models
from courses.models import Course


class Subject(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='subjects')
    org = models.ForeignKey('users.Organization', on_delete=models.CASCADE, null=True, blank=True, related_name='subjects')
    created_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='created_subjects')
    name = models.CharField(max_length=200)
    description = models.CharField(max_length=500, null=True, blank=True)
    is_sys = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'pd_subjects'
        ordering = ['name']


class Topic(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='topics')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    order = models.PositiveIntegerField(default=0)
    is_sys = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'pd_topics'
        ordering = ['order', 'name']


class Chapter(models.Model):
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name='chapters')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    order = models.PositiveIntegerField(default=0)
    is_sys = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'pd_chapters'
        ordering = ['order', 'name']


class SyllabusFile(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='syllabus_files')
    name = models.CharField(max_length=255)
    file = models.FileField(upload_to='syllabus/', null=True, blank=True)
    file_url = models.CharField(max_length=500, null=True, blank=True)
    file_size = models.CharField(max_length=50, null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'pd_syllabus_files'
