from django.db import models
import uuid


class ExamAuthority(models.Model):
    AUTHORITY_TYPES = (
        ("board", "Board"),
        ("govt", "Government"),
        ("university", "University"),
        ("coaching", "Coaching"),
        ("institution", "Institution"),
        ("other", "Other"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    org = models.ForeignKey(
        "users.Organization",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="exam_authorities",
    )
    name = models.CharField(max_length=255)
    short_name = models.CharField(max_length=50, unique=True)
    authority_type = models.CharField(max_length=20, choices=AUTHORITY_TYPES)
    description = models.TextField(blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    logo = models.ImageField(upload_to="exam_authorities/logos/", blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_sys = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "exam_authorities"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.short_name})"


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
