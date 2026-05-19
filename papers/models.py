from django.db import models
from django.conf import settings
from courses.models import Course


class Paper(models.Model):
    STATUS_DRAFT = 'draft'
    STATUS_GENERATED = 'generated'
    STATUS_FAILED = 'failed'
    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Draft'),
        (STATUS_GENERATED, 'Generated'),
        (STATUS_FAILED, 'Failed'),
    ]

    EXAM_NEET = 'NEET'
    EXAM_JEE_MAINS = 'JEE Mains'
    EXAM_JEE_ADVANCED = 'JEE Advanced'
    EXAM_CUSTOM = 'Custom'

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='papers')
    course = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True, blank=True, related_name='papers')
    title = models.CharField(max_length=300)
    exam_type = models.CharField(max_length=50, default=EXAM_NEET)
    subjects = models.JSONField(default=list)
    difficulty = models.CharField(max_length=20, default='medium')
    total_marks = models.IntegerField(default=0)
    duration_minutes = models.IntegerField(default=180)
    instructions = models.TextField(null=True, blank=True)
    content = models.JSONField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    generation_cost_paise = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'pd_papers'
        ordering = ['-created_at']
