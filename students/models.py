from django.db import models
from courses.models import Course


class Student(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='students')
    name = models.CharField(max_length=200)
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    roll_no = models.CharField(max_length=50, null=True, blank=True)
    joined_date = models.DateField(null=True, blank=True)
    attendance = models.SmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'pd_students'
        ordering = ['name']
