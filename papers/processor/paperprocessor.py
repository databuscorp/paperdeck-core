from dataclasses import dataclass, field
from typing import Optional, List, Any

import marshmallow_dataclass
from dataclasses_json import dataclass_json
from marshmallow import EXCLUDE


@dataclass
class PaperGenerateRequest:
    title:            str
    subjects:         List[str]
    difficulty:       Optional[str] = 'medium'
    total_marks:      Optional[int] = 720
    duration_minutes: Optional[int] = 180
    # FK-based (preferred)
    course_id:        Optional[str] = None   # UUID string
    blueprint_id:     Optional[int] = None
    # Legacy string fallback
    exam_type:        Optional[str] = None
    instructions:     Optional[str] = None
    id:               Optional[int] = None


@dataclass
class PaperSaveRequest:
    title:            str
    total_marks:      int
    duration_minutes: int
    # FK-based
    course_id:        Optional[str] = None   # UUID string
    blueprint_id:     Optional[int] = None
    # Legacy string fallback
    exam_type:        Optional[str] = None
    meta:             Any = None
    sections:         Any = None
    id:               Optional[int] = None


paper_generate_req_schema = marshmallow_dataclass.class_schema(PaperGenerateRequest)(unknown=EXCLUDE)
paper_save_req_schema     = marshmallow_dataclass.class_schema(PaperSaveRequest)(unknown=EXCLUDE)


@dataclass_json
@dataclass
class PaperSectionResponse:
    id:         int
    name:       str
    order:      int
    subject_id: Optional[int]
    question_count: int


@dataclass_json
@dataclass
class PaperResponse:
    id:               int
    title:            str
    difficulty:       str
    total_marks:      int
    duration_minutes: int
    status:           str
    source:           str
    created_at:       str
    updated_at:       str
    exam_type:        Optional[str]
    subjects:         List[str]
    instructions:     Optional[str]
    content:          Optional[Any]
    # FK references
    org_id:           Optional[int]
    course_id:        Optional[str]   # UUID string
    blueprint_id:     Optional[int]
    sections:         List[PaperSectionResponse] = field(default_factory=list)