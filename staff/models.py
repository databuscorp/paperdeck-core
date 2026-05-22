from django.conf import settings
from django.db import models
from courses.models import Course


class Staff(models.Model):
    org     = models.ForeignKey('users.Organization', on_delete=models.CASCADE, null=True, blank=True, related_name='staff_members')
    courses = models.ManyToManyField(Course, through='StaffCourse', related_name='staff_members', blank=True)
    user    = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='staff_entries')
    name    = models.CharField(max_length=200)
    email   = models.EmailField(null=True, blank=True)
    phone   = models.CharField(max_length=20, null=True, blank=True)
    subject = models.CharField(max_length=200, null=True, blank=True)
    role    = models.CharField(max_length=100, null=True, blank=True)
    joined_date = models.DateField(null=True, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'pd_staff'
        ordering = ['name']


class StaffCourse(models.Model):
    staff  = models.ForeignKey(Staff, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)

    class Meta:
        db_table = 'pd_staff_courses'
        unique_together = [('staff', 'course')]
