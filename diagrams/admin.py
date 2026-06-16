"""
Django admin for the STEM Diagram Rendering Engine.
Provides SVG preview, failure filtering, job retry, and template management.
"""
from django.contrib import admin
from django.utils.html import format_html, mark_safe
from django.utils.timezone import now

from diagrams.models import DiagramTemplate, RenderedDiagram, RenderingJob


@admin.register(DiagramTemplate)
class DiagramTemplateAdmin(admin.ModelAdmin):
    list_display = ["name", "diagram_type", "subtype", "is_active", "created_at", "thumbnail_preview"]
    list_filter = ["diagram_type", "is_active"]
    search_fields = ["name", "description", "subtype"]
    readonly_fields = ["id", "created_at", "updated_at", "thumbnail_preview"]
    ordering = ["diagram_type", "subtype"]

    fieldsets = [
        ("Identity", {"fields": ["id", "name", "diagram_type", "subtype", "is_active"]}),
        ("Schema", {"fields": ["schema"], "classes": ["collapse"]}),
        ("Description", {"fields": ["description"]}),
        ("Thumbnail", {"fields": ["thumbnail_preview", "thumbnail_svg"]}),
        ("Timestamps", {"fields": ["created_at", "updated_at"]}),
    ]

    def thumbnail_preview(self, obj):
        if obj.thumbnail_svg:
            return format_html(
                '<div style="width:200px;height:130px;overflow:hidden;border:1px solid #ddd">'
                "{}"
                "</div>",
                mark_safe(obj.thumbnail_svg),
            )
        return "No thumbnail"
    thumbnail_preview.short_description = "Preview"


class RenderingJobInline(admin.StackedInline):
    model = RenderingJob
    extra = 0
    readonly_fields = ["id", "status", "started_at", "completed_at", "error_trace", "created_at"]
    can_delete = False


@admin.register(RenderedDiagram)
class RenderedDiagramAdmin(admin.ModelAdmin):
    list_display = [
        "id_short", "diagram_type", "subtype", "status_badge",
        "render_time_ms", "question", "created_at",
    ]
    list_filter = ["diagram_type", "status", "subtype"]
    search_fields = ["id", "diagram_type", "subtype", "error_message"]
    readonly_fields = [
        "id", "svg_preview", "svg_path", "png_path",
        "render_time_ms", "validation_result",
        "created_at", "updated_at",
    ]
    inlines = [RenderingJobInline]
    actions = ["retry_failed_renders", "mark_as_pending"]
    ordering = ["-created_at"]

    fieldsets = [
        ("Identity", {"fields": ["id", "diagram_type", "subtype", "status"]}),
        ("Source", {"fields": ["question", "template"]}),
        ("Input", {"fields": ["input_schema"], "classes": ["collapse"]}),
        ("Output", {"fields": ["svg_preview", "svg_path", "png_path", "render_time_ms"]}),
        ("Validation", {"fields": ["validation_result"], "classes": ["collapse"]}),
        ("Error", {"fields": ["error_message"], "classes": ["collapse"]}),
        ("Metadata", {"fields": ["metadata", "created_at", "updated_at"]}),
    ]

    def id_short(self, obj):
        return str(obj.id)[:8] + "…"
    id_short.short_description = "ID"

    def status_badge(self, obj):
        colors = {
            "success": "#28a745",
            "pending": "#ffc107",
            "failed": "#dc3545",
        }
        color = colors.get(obj.status, "#999")
        return format_html(
            '<span style="background:{};color:white;padding:2px 8px;border-radius:3px;font-size:11px">{}</span>',
            color, obj.status.upper(),
        )
    status_badge.short_description = "Status"

    def svg_preview(self, obj):
        if obj.svg_content:
            return format_html(
                '<div style="width:320px;height:220px;overflow:hidden;border:1px solid #ddd;">'
                "{}"
                "</div>",
                mark_safe(obj.svg_content),
            )
        return "No SVG content"
    svg_preview.short_description = "SVG Preview"

    def retry_failed_renders(self, request, queryset):
        from diagrams.service.dispatcher import dispatch_render
        retried, failed = 0, 0
        for diagram in queryset.filter(status=RenderedDiagram.STATUS_FAILED):
            validation, result = dispatch_render(diagram.input_schema, save_files=True,
                                                 diagram_id=str(diagram.id))
            if result.success:
                diagram.status = RenderedDiagram.STATUS_SUCCESS
                diagram.svg_content = result.svg_content
                diagram.svg_path = result.svg_path
                diagram.png_path = result.png_path
                diagram.error_message = None
                diagram.render_time_ms = result.render_time_ms
                diagram.save()
                if hasattr(diagram, "job"):
                    diagram.job.status = RenderingJob.STATUS_DONE
                    diagram.job.completed_at = now()
                    diagram.job.save()
                retried += 1
            else:
                failed += 1
        self.message_user(request, f"Retried {retried} diagrams successfully. {failed} still failing.")
    retry_failed_renders.short_description = "↺ Retry failed renders"

    def mark_as_pending(self, request, queryset):
        queryset.update(status=RenderedDiagram.STATUS_PENDING)
        self.message_user(request, f"Marked {queryset.count()} diagrams as pending.")
    mark_as_pending.short_description = "Mark as pending"


@admin.register(RenderingJob)
class RenderingJobAdmin(admin.ModelAdmin):
    list_display = ["id", "status_badge", "rendered_diagram", "started_at",
                    "completed_at", "duration_ms", "created_at"]
    list_filter = ["status"]
    readonly_fields = ["id", "rendered_diagram", "started_at", "completed_at",
                       "error_trace", "created_at"]
    ordering = ["-created_at"]

    def status_badge(self, obj):
        colors = {
            "done": "#28a745",
            "queued": "#17a2b8",
            "processing": "#ffc107",
            "failed": "#dc3545",
        }
        color = colors.get(obj.status, "#999")
        return format_html(
            '<span style="background:{};color:white;padding:2px 8px;border-radius:3px;font-size:11px">{}</span>',
            color, obj.status.upper(),
        )
    status_badge.short_description = "Status"

    def duration_ms(self, obj):
        if obj.started_at and obj.completed_at:
            delta = obj.completed_at - obj.started_at
            return f"{int(delta.total_seconds() * 1000)} ms"
        return "-"
    duration_ms.short_description = "Duration"
