from dataclasses import dataclass, field
from typing import Any, Optional
from dataclasses_json import dataclass_json
import marshmallow_dataclass


@dataclass_json
@dataclass
class ExamTemplateResponse:
    id:          int
    name:        str
    duration:    str
    total_marks: float
    neg_marking: str
    sections:    Any
    is_default:  bool
    created_at:  str


@dataclass
class ExamAuthorityRequest:
    name: str
    short_name: str
    authority_type: str
    description: Optional[str] = None
    website: Optional[str] = None
    is_active: Optional[bool] = True
    id: Optional[str] = None


exam_authority_req_schema = marshmallow_dataclass.class_schema(ExamAuthorityRequest)()


@dataclass_json
@dataclass
class ExamAuthorityResponse:
    id: str
    name: str
    short_name: str
    authority_type: str
    description: Optional[str]
    website: Optional[str]
    is_active: bool
    is_sys: bool
    created_at: str
