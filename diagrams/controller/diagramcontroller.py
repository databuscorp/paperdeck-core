"""
REST API controllers for the STEM Diagram Rendering Engine.
Follows the same pattern as other PaperDeck controllers.

Endpoints:
  POST /api/diagrams/render/     — validate + render a diagram schema
  POST /api/diagrams/validate/   — validate only (no rendering)
  POST /api/diagrams/pdf/        — generate PDF for a question paper
  GET  /api/health/              — health check
  GET  /api/diagrams/types/      — list supported diagram types + subtypes
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime

from django.http import HttpResponse, JsonResponse
from django.utils.timezone import now
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view

from utility.utilityobj import ErrorResponse

from diagrams.models import RenderedDiagram, RenderingJob
from diagrams.processor.diagramprocessor import (
    render_request_schema, validate_request_schema, pdf_request_schema,
)
from diagrams.service.dispatcher import dispatch_render, validate_only
from diagrams.service.pdf.composer import generate_paper_pdf, generate_diagram_pdf
from diagrams.validators.schema_validator import list_supported_subtypes


# ── POST /api/diagrams/render/ ─────────────────────────────────────────────────

@csrf_exempt
@api_view(["POST"])
def render_diagram(request):
    """
    Validate and render a diagram schema.
    Returns: SVG content inline + file paths if saved.
    """
    try:
        req = render_request_schema.load(request.data)
    except Exception as e:
        return HttpResponse(
            ErrorResponse(status=400, message=f"Invalid request: {e}").to_json(),
            status=400, content_type="application/json",
        )

    # Build full schema dict
    schema_data = {
        "diagram_type": req.diagram_type,
        "subtype": req.subtype,
        "canvas": req.canvas or {"width": 800, "height": 600},
        "objects": req.objects,
        "params": req.params or {},
        "annotations": req.annotations,
        "metadata": req.metadata,
    }

    # Create a pending DB record
    diagram_id = str(uuid.uuid4())
    record = RenderedDiagram.objects.create(
        id=diagram_id,
        diagram_type=req.diagram_type,
        subtype=req.subtype,
        input_schema=schema_data,
        status=RenderedDiagram.STATUS_PENDING,
    )
    job = RenderingJob.objects.create(
        rendered_diagram=record,
        status=RenderingJob.STATUS_PROCESSING,
        started_at=now(),
    )

    # Dispatch
    validation, result = dispatch_render(schema_data, save_files=req.save_files,
                                         diagram_id=diagram_id)

    # Update DB record
    if result.success:
        record.status = RenderedDiagram.STATUS_SUCCESS
        record.svg_content = result.svg_content
        record.svg_path = result.svg_path
        record.png_path = result.png_path
        record.render_time_ms = result.render_time_ms
        record.validation_result = validation.to_dict()
        job.status = RenderingJob.STATUS_DONE
        job.completed_at = now()
    else:
        record.status = RenderedDiagram.STATUS_FAILED
        record.error_message = result.error
        record.validation_result = validation.to_dict()
        job.status = RenderingJob.STATUS_FAILED
        job.completed_at = now()
        job.error_trace = result.error

    record.save()
    job.save()

    if not result.success:
        return HttpResponse(
            json.dumps({
                "success": False,
                "diagram_id": diagram_id,
                "error": result.error,
                "validation": validation.to_dict(),
            }),
            status=422, content_type="application/json",
        )

    return HttpResponse(
        json.dumps({
            "success": True,
            "diagram_id": diagram_id,
            "diagram_type": req.diagram_type,
            "subtype": req.subtype,
            "svg_content": result.svg_content,
            "svg_path": result.svg_path,
            "png_path": result.png_path,
            "svg_url": record.svg_url,
            "png_url": record.png_url,
            "render_time_ms": result.render_time_ms,
            "validation": validation.to_dict(),
        }),
        status=200, content_type="application/json",
    )


# ── POST /api/diagrams/validate/ ──────────────────────────────────────────────

@csrf_exempt
@api_view(["POST"])
def validate_diagram_view(request):
    """
    Validate a diagram schema without rendering.
    Useful for client-side pre-validation before submitting for rendering.
    """
    try:
        req = validate_request_schema.load(request.data)
    except Exception as e:
        return HttpResponse(
            ErrorResponse(status=400, message=f"Invalid request: {e}").to_json(),
            status=400, content_type="application/json",
        )

    schema_data = {
        "diagram_type": req.diagram_type,
        "subtype": req.subtype,
        "canvas": req.canvas or {"width": 800, "height": 600},
        "objects": req.objects,
        "params": req.params or {},
        "annotations": req.annotations,
        "metadata": req.metadata,
    }

    validation = validate_only(schema_data)
    status_code = 200 if validation.valid else 422
    return HttpResponse(
        json.dumps({
            "valid": validation.valid,
            "errors": validation.errors,
            "warnings": validation.warnings,
        }),
        status=status_code, content_type="application/json",
    )


# ── POST /api/diagrams/pdf/ ────────────────────────────────────────────────────

@csrf_exempt
@api_view(["POST"])
def generate_pdf(request):
    """
    Generate a full question paper PDF.
    Accepts the paper data structure with sections + questions.
    Returns the PDF as a binary download.
    """
    try:
        req = pdf_request_schema.load(request.data)
    except Exception as e:
        return HttpResponse(
            ErrorResponse(status=400, message=f"Invalid request: {e}").to_json(),
            status=400, content_type="application/json",
        )

    paper_data = {
        "title": req.title,
        "exam_name": req.exam_name,
        "duration_minutes": req.duration_minutes,
        "total_marks": req.total_marks,
        "instructions": req.instructions,
        "sections": req.sections,
    }

    try:
        pdf_bytes = generate_paper_pdf(paper_data)
    except Exception as e:
        return HttpResponse(
            ErrorResponse(status=500, message=f"PDF generation failed: {e}").to_json(),
            status=500, content_type="application/json",
        )

    safe_title = req.title.replace(" ", "_")[:50]
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{safe_title}.pdf"'
    return response


# ── GET /api/diagrams/types/ ───────────────────────────────────────────────────

@api_view(["GET"])
def list_diagram_types(request):
    """List all supported diagram types and their subtypes."""
    return HttpResponse(
        json.dumps({
            "supported_types": list_supported_subtypes(),
        }),
        content_type="application/json",
    )


# ── GET /api/health/ ───────────────────────────────────────────────────────────

@api_view(["GET"])
def health_check(request):
    """Service health check — verifies DB and rendering dependencies."""
    checks = {}

    # DB connectivity
    try:
        from diagrams.models import RenderedDiagram
        RenderedDiagram.objects.count()
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {e}"

    # svgwrite
    try:
        import svgwrite
        checks["svgwrite"] = svgwrite.__version__
    except ImportError:
        checks["svgwrite"] = "not installed"

    # matplotlib
    try:
        import matplotlib
        checks["matplotlib"] = matplotlib.__version__
    except ImportError:
        checks["matplotlib"] = "not installed"

    # schemdraw
    try:
        import schemdraw
        checks["schemdraw"] = schemdraw.__version__
    except ImportError:
        checks["schemdraw"] = "not installed"

    # rdkit
    try:
        from rdkit import Chem
        checks["rdkit"] = "available"
    except ImportError:
        checks["rdkit"] = "not installed (organic structure rendering uses fallback)"

    # reportlab
    try:
        import reportlab
        checks["reportlab"] = reportlab.Version
    except ImportError:
        checks["reportlab"] = "not installed"

    # cairosvg. Broad except: with the package installed but the native cairo library
    # missing, cairocffi raises OSError — and a health check that crashes while
    # reporting health is worse than useless.
    try:
        import cairosvg
        checks["cairosvg"] = cairosvg.__version__
    except ImportError:
        checks["cairosvg"] = "not installed (PNG export and PDF diagrams disabled)"
    except Exception as exc:
        checks["cairosvg"] = f"installed but unusable — native cairo library missing ({exc})"

    # pydantic
    try:
        import pydantic
        checks["pydantic"] = pydantic.__version__
    except ImportError:
        checks["pydantic"] = "not installed"

    all_ok = checks.get("database") == "ok"
    return HttpResponse(
        json.dumps({
            "status": "healthy" if all_ok else "degraded",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "checks": checks,
        }),
        status=200 if all_ok else 503,
        content_type="application/json",
    )
