from django.db import models
from django.conf import settings


class Course(models.Model):
    CATEGORY_CHOICES = [
        ('NEET', 'NEET'),
        ('JEE Mains', 'JEE Mains'),
        ('JEE Advanced', 'JEE Advanced'),
        ('UPSC', 'UPSC'),
        ('Banking', 'Banking'),
        ('State PSC', 'State PSC'),
    ]
    STATUS_CHOICES = [('active', 'Active'), ('inactive', 'Inactive')]

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='courses')
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='NEET')
    description = models.CharField(max_length=1000, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    duration = models.CharField(max_length=50, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'pd_courses'
        ordering = ['-created_at']
