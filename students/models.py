from django.conf import settings
from django.db import models
from courses.models import Course


class Student(models.Model):
    org         = models.ForeignKey('users.Organization', on_delete=models.CASCADE, null=True, blank=True, related_name='students')
    courses     = models.ManyToManyField(Course, through='StudentCourse', related_name='students', blank=True)
    user        = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='student_entries')
    name        = models.CharField(max_length=200)
    email       = models.EmailField(null=True, blank=True)
    phone       = models.CharField(max_length=20, null=True, blank=True)
    roll_no     = models.CharField(max_length=50, null=True, blank=True)
    joined_date = models.DateField(null=True, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'pd_students'
        ordering = ['name']


class StudentCourse(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    course  = models.ForeignKey(Course, on_delete=models.CASCADE)

    class Meta:
        db_table = 'pd_student_courses'
        unique_together = [('student', 'course')]
