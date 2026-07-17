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
        # default_storage.url() resolves the stored key to a real URL for whichever backend
        # is active: MEDIA_URL-prefixed locally, a short-lived SAS-signed URL on Azure Blob.
        from django.core.files.storage import default_storage
        if self.svg_path:
            return default_storage.url(self.svg_path)
        return None

    @property
    def png_url(self):
        from django.core.files.storage import default_storage
        if self.png_path:
            return default_storage.url(self.png_path)
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


class DiagramDemand(models.Model):
    """Durable tally of diagrams the engine was asked to draw but could NOT.

    Every unrenderable figure (an unknown subtype, an unknown diagram_type, or a renderer
    crash) is recorded here, keyed by (diagram_type, subtype, category) with a running count.
    It turns the `paperdeck.diagram_demand` log stream — ephemeral on a container host — into
    a queryable, ranked backlog: the highest-count rows are the renderers worth building next.
    Written from diagrams.service.demand.record_demand; read by `manage.py diagram_demand`.
    """
    CATEGORY_UNKNOWN_SUBTYPE = "unknown_subtype"
    CATEGORY_UNKNOWN_TYPE = "unknown_type"
    CATEGORY_RENDER_ERROR = "render_error"
    CATEGORY_OTHER = "other"

    diagram_type = models.CharField(max_length=50)
    subtype = models.CharField(max_length=100)
    category = models.CharField(max_length=30, default=CATEGORY_OTHER)
    count = models.PositiveIntegerField(default=0)
    sample_reason = models.TextField(blank=True, default="")
    first_seen = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "pd_diagram_demand"
        ordering = ["-count"]
        constraints = [
            models.UniqueConstraint(
                fields=["diagram_type", "subtype", "category"],
                name="uniq_diagram_demand_key",
            ),
        ]
        indexes = [models.Index(fields=["-count"])]

    def __str__(self):
        return f"{self.diagram_type}/{self.subtype} [{self.category}] ×{self.count}"
