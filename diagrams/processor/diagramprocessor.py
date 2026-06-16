"""
Request/Response data parsers for the Diagrams API.
Follows the marshmallow-dataclass pattern used elsewhere in this project.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from marshmallow_dataclass import class_schema


# ── Render Request ─────────────────────────────────────────────────────────────

@dataclass
class CanvasData:
    width: int = 800
    height: int = 600


@dataclass
class RenderRequest:
    diagram_type: str = ""
    subtype: str = ""
    canvas: Optional[Dict[str, Any]] = None
    objects: List[Dict[str, Any]] = field(default_factory=list)
    params: Optional[Dict[str, Any]] = None
    annotations: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    save_files: bool = True


render_request_schema = class_schema(RenderRequest)()


# ── Validate Request ───────────────────────────────────────────────────────────

@dataclass
class ValidateRequest:
    diagram_type: str = ""
    subtype: str = ""
    canvas: Optional[Dict[str, Any]] = None
    objects: List[Dict[str, Any]] = field(default_factory=list)
    params: Optional[Dict[str, Any]] = None
    annotations: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


validate_request_schema = class_schema(ValidateRequest)()


# ── PDF Request ────────────────────────────────────────────────────────────────

@dataclass
class PaperSection:
    name: str = ""
    questions: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class PDFRequest:
    title: str = "Question Paper"
    exam_name: str = ""
    duration_minutes: int = 180
    total_marks: int = 0
    instructions: List[str] = field(default_factory=list)
    sections: List[Dict[str, Any]] = field(default_factory=list)


pdf_request_schema = class_schema(PDFRequest)()
