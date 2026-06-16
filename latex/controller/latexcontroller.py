"""
LaTeX rendering endpoints.

POST /api/latex/render/
    Body: { "text": "...", "color": "black" }
    Returns a list of segments (text + rendered SVG for math).

POST /api/latex/render-batch/
    Body: { "items": [{"id": "q1", "text": "...", "options": [...]}, ...] }
    Renders all math in all text fields of each item in one round-trip.

POST /api/latex/validate/
    Body: { "expressions": ["\\frac{d}{dx}", ...] }
    Returns per-expression validity.

GET  /api/latex/health/
    Quick check that the renderer is operational.
"""
from __future__ import annotations

import json

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view

from latex.service.latexservice import (
    render_text, validate_expression, has_math,
    segment_to_dict, parse_segments,
)


def _json(data, status: int = 200) -> HttpResponse:
    return HttpResponse(json.dumps(data), content_type="application/json", status=status)


def _err(msg: str, status: int = 400) -> HttpResponse:
    return _json({"error": msg}, status=status)


# ── POST /api/latex/render/ ───────────────────────────────────────────────────

@csrf_exempt
@api_view(["POST"])
def render_latex(request):
    """
    Render a single text string that may contain $...$ / $$...$$ math.

    Request JSON:
        { "text": "...",  "color": "black" }

    Response JSON:
        {
          "has_math": true,
          "segments": [
            {"type": "text",         "content": "..."},
            {"type": "math_inline",  "content": "\\frac{d}{dx}", "svg": "<svg>..."},
            {"type": "math_block",   "content": "...",            "svg": "<svg>..."},
          ]
        }
    """
    body = request.data
    if not isinstance(body, dict) or "text" not in body:
        return _err('Request must be JSON with a "text" field.')

    text  = str(body.get("text", ""))
    color = str(body.get("color", "black"))

    segments = render_text(text, color=color)
    return _json({
        "has_math": has_math(text),
        "segments": [segment_to_dict(s) for s in segments],
    })


# ── POST /api/latex/render-batch/ ────────────────────────────────────────────

@csrf_exempt
@api_view(["POST"])
def render_latex_batch(request):
    """
    Render math in multiple question-like objects in a single call.

    Each item has an `id` (echoed back), a `text` field, and optionally
    `options` (list of strings or list of {"text": ...} dicts).

    Request JSON:
        {
          "color": "black",
          "items": [
            {"id": "q1", "text": "Find $x$ if ...", "options": ["$x=1$", "$x=2$", ...]},
            {"id": "q2", "text": "A block of mass $m$...", "options": null}
          ]
        }

    Response JSON:
        {
          "items": [
            {
              "id": "q1",
              "text_segments": [...],
              "options_segments": [[...], [...], ...],
              "has_math": true
            },
            ...
          ]
        }
    """
    body = request.data
    if not isinstance(body, dict) or "items" not in body:
        return _err('Request must be JSON with an "items" list.')

    items  = body.get("items", [])
    color  = str(body.get("color", "black"))

    if not isinstance(items, list):
        return _err('"items" must be a list.')

    rendered_items = []

    for item in items:
        if not isinstance(item, dict):
            continue

        item_id   = item.get("id", "")
        text      = str(item.get("text", ""))
        options   = item.get("options")   # list[str] or list[dict] or None

        text_segs = [segment_to_dict(s) for s in render_text(text, color=color)]

        opts_segs = None
        if isinstance(options, list):
            opts_segs = []
            for opt in options:
                if isinstance(opt, dict):
                    opt_text = str(opt.get("text", ""))
                elif isinstance(opt, str):
                    opt_text = opt
                else:
                    opt_text = str(opt)
                opts_segs.append([segment_to_dict(s)
                                  for s in render_text(opt_text, color=color)])

        item_has_math = has_math(text) or any(
            has_math(o.get("text", o) if isinstance(o, dict) else str(o))
            for o in (options or [])
        )

        rendered_items.append({
            "id":               item_id,
            "text_segments":    text_segs,
            "options_segments": opts_segs,
            "has_math":         item_has_math,
        })

    return _json({"items": rendered_items})


# ── POST /api/latex/validate/ ─────────────────────────────────────────────────

@csrf_exempt
@api_view(["POST"])
def validate_latex(request):
    """
    Validate one or more LaTeX math expressions.

    Request JSON:
        { "expressions": ["\\frac{d}{dx}", "\\invalid{", "E = mc^2"] }

    Response JSON:
        {
          "results": [
            {"expression": "\\frac{d}{dx}", "valid": true},
            {"expression": "\\invalid{",    "valid": false, "error": "..."},
            {"expression": "E = mc^2",      "valid": true}
          ]
        }
    """
    body = request.data
    if not isinstance(body, dict) or "expressions" not in body:
        return _err('Request must be JSON with an "expressions" list.')

    exprs = body.get("expressions", [])
    if not isinstance(exprs, list):
        return _err('"expressions" must be a list of strings.')

    results = []
    for expr in exprs:
        expr_str = str(expr)
        valid, err = validate_expression(expr_str)
        entry: dict = {"expression": expr_str, "valid": valid}
        if err:
            entry["error"] = err
        results.append(entry)

    return _json({"results": results})


# ── GET /api/latex/health/ ────────────────────────────────────────────────────

@api_view(["GET"])
def latex_health(request):
    """Quick smoke-test — renders a trivial expression and confirms SVG output."""
    try:
        segs = render_text(r"$E = mc^2$")
        math_seg = next((s for s in segs if s.svg), None)
        ok = math_seg is not None and "<svg" in (math_seg.svg or "")
        return _json({"status": "ok" if ok else "degraded", "renderer": "matplotlib-mathtext"})
    except Exception as exc:
        return _json({"status": "error", "detail": str(exc)}, status=500)
