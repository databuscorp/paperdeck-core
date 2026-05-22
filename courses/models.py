from django.conf import settings
from django.db import models
import uuid


class Course(models.Model):
    COURSE_TYPES = (
        ("common", "Common"),
        ("custom", "Custom"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    authority = models.ForeignKey(
        "exams.ExamAuthority",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="courses"
    )

    org = models.ForeignKey(
        "users.Organization",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="courses",
    )

    created_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_courses",
    )

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    course_type = models.CharField(max_length=20, choices=COURSE_TYPES, default="common")
    description = models.TextField(blank=True, null=True)
    grade_level = models.CharField(max_length=100, blank=True, null=True)
    duration_minutes = models.PositiveIntegerField(default=0)
    total_marks = models.PositiveIntegerField(default=0)
    instructions = models.TextField(blank=True, null=True)
    thumbnail = models.ImageField(upload_to="courses/thumbnails/", blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_sys = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "courses"
        ordering = ["name"]

    def __str__(self):
        return self.name


class CourseSubscription(models.Model):
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='subscriptions',
    )
    org = models.ForeignKey(
        'users.Organization',
        on_delete=models.CASCADE,
        related_name='course_subscriptions',
    )
    subscribed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    subscribed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'pd_course_subscriptions'
        constraints = [
            models.UniqueConstraint(fields=['course', 'org'], name='unique_course_org_sub')
        ]
        ordering = ['-subscribed_at']
