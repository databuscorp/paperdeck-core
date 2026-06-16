"""
Django models for the STEM Diagram Rendering Engine.
"""
import uuid
from django.db import models


class DiagramTemplate(models.Model):
    """
    Reusable diagram schema templates — can be seeded with canonical examples
    for each supported diagram type/subtype.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    diagram_type = models.CharField(max_length=50)
    subtype = models.CharField(max_length=100)
    schema = models.JSONField(help_text="Full diagram JSON schema (diagram_type, subtype, params, canvas)")
    description = models.TextField(blank=True, default="")
    thumbnail_svg = models.TextField(null=True, blank=True,
                                     help_text="Pre-rendered SVG thumbnail")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "pd_diagram_templates"
        ordering = ["diagram_type", "subtype"]
        unique_together = [("diagram_type", "subtype", "name")]

    def __str__(self):
        return f"{self.diagram_type}/{self.subtype} — {self.name}"


class RenderedDiagram(models.Model):
    """
    Record of each rendered diagram, linking to the source question if applicable.
    Stores both the input schema and the rendered SVG/PNG outputs.
    """
    STATUS_PENDING = "pending"
    STATUS_SUCCESS = "success"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_SUCCESS, "Success"),
        (STATUS_FAILED, "Failed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    question = models.ForeignKey(
        "questions.Question",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="rendered_diagrams",
        help_text="Source question this diagram belongs to (optional)",
    )
    template = models.ForeignKey(
        DiagramTemplate,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="rendered_instances",
    )
    diagram_type = models.CharField(max_length=50)
    subtype = models.CharField(max_length=100)
    input_schema = models.JSONField(help_text="Full JSON input that was rendered")
    svg_content = models.TextField(null=True, blank=True, help_text="Inline SVG string")
    svg_path = models.CharField(max_length=500, null=True, blank=True,
                                help_text="Relative path under MEDIA_ROOT")
    png_path = models.CharField(max_length=500, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    error_message = models.TextField(null=True, blank=True)
    validation_result = models.JSONField(null=True, blank=True)
    render_time_ms = models.IntegerField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "pd_rendered_diagrams"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["diagram_type", "subtype"]),
            models.Index(fields=["status"]),
            models.Index(fields=["question"]),
        ]

    def __str__(self):
        return f"{self.diagram_type}/{self.subtype} [{self.status}] @ {self.created_at:%Y-%m-%d %H:%M}"

    @property
    def svg_url(self):
        from django.conf import settings
        if self.svg_path:
            return settings.MEDIA_URL + self.svg_path
        return None

    @property
    def png_url(self):
        from django.conf import settings
        if self.png_path:
            return settings.MEDIA_URL + self.png_path
        return None


class RenderingJob(models.Model):
    """
    Tracks the lifecycle of an async rendering job.
    For sync rendering, jobs are created and completed in one request.
    """
    STATUS_QUEUED = "queued"
    STATUS_PROCESSING = "processing"
    STATUS_DONE = "done"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_QUEUED, "Queued"),
        (STATUS_PROCESSING, "Processing"),
        (STATUS_DONE, "Done"),
        (STATUS_FAILED, "Failed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rendered_diagram = models.OneToOneField(
        RenderedDiagram, on_delete=models.CASCADE, related_name="job",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_QUEUED)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_trace = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "pd_rendering_jobs"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Job[{self.id}] {self.status}"
