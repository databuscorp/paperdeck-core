from django.db import models
from django.conf import settings


class Question(models.Model):
    owner      = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='questions')
    exam       = models.CharField(max_length=100)
    subject    = models.CharField(max_length=100)
    topic      = models.CharField(max_length=200)
    q_type     = models.CharField(max_length=50)
    difficulty = models.CharField(max_length=50)
    bloom      = models.CharField(max_length=50, default='Understand')
    marks      = models.IntegerField(default=1)
    text       = models.TextField()
    options    = models.JSONField(null=True, blank=True)
    explanation= models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'pd_questions'
        ordering = ['-created_at']
