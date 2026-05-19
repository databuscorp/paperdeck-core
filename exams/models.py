from django.db import models


class ExamTemplate(models.Model):
    name        = models.CharField(max_length=100, unique=True)
    duration    = models.CharField(max_length=50)
    total_marks = models.FloatField()
    neg_marking = models.CharField(max_length=100)
    sections    = models.JSONField(default=list)
    is_default  = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'pd_exam_templates'
        ordering = ['name']
