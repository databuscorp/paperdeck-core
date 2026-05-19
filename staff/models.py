from django.db import models
from courses.models import Course


class Staff(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='staff_members')
    name = models.CharField(max_length=200)
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    subject = models.CharField(max_length=200, null=True, blank=True)
    role = models.CharField(max_length=100, null=True, blank=True)
    joined_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'pd_staff'
        ordering = ['name']
