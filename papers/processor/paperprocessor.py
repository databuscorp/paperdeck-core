from dataclasses import dataclass
from typing import Optional, List, Any

import marshmallow_dataclass
from dataclasses_json import dataclass_json


@dataclass
class PaperGenerateRequest:
    title: str
    exam_type: str
    subjects: List[str]
    difficulty: Optional[str] = 'medium'
    total_marks: Optional[int] = 720
    duration_minutes: Optional[int] = 180
    course_id: Optional[int] = None
    instructions: Optional[str] = None
    id: Optional[int] = None


@dataclass
class PaperSaveRequest:
    title: str
    exam_type: str
    total_marks: int
    duration_minutes: int
    meta: Any = None       # full PaperMeta object
    sections: Any = None   # full sections + questions
    id: Optional[int] = None


paper_generate_req_schema = marshmallow_dataclass.class_schema(PaperGenerateRequest)()
paper_save_req_schema = marshmallow_dataclass.class_schema(PaperSaveRequest)()


@dataclass_json
@dataclass
class PaperResponse:
    id: int
    title: str
    exam_type: str
    subjects: List[str]
    difficulty: str
    total_marks: int
    duration_minutes: int
    instructions: Optional[str]
    content: Optional[Any]
    status: str
    created_at: str
    updated_at: str
    course_id: Optional[int] = None
