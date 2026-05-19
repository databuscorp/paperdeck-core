from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_ADMIN = 1
    ROLE_STAFF = 2
    ROLE_STUDENT = 3

    ROLE_CHOICES = [(ROLE_ADMIN, 'Admin'), (ROLE_STAFF, 'Staff'), (ROLE_STUDENT, 'Student')]

    institute_name = models.CharField(max_length=200, null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    role = models.SmallIntegerField(choices=ROLE_CHOICES, default=ROLE_ADMIN)
    plan = models.CharField(max_length=20, default='basic')  # basic | pro
    papers_used = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'pd_users'
