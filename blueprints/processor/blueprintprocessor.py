from dataclasses import dataclass, field
from typing import List, Optional

import marshmallow_dataclass
from dataclasses_json import dataclass_json


@dataclass
class BlueprintSectionRequest:
    name:            str
    subject:         str
    q_type:          str
    count:           int
    marks_per_q:     float
    topics:          str = ''
    neg_marks_per_q: float = 0.0
    difficulty:      str = 'Mixed'
    bloom:           str = 'Mixed'
    order:           int = 0
    id:              Optional[int] = None


@dataclass
class BlueprintRequest:
    duration:            str
    total_marks:         int
    neg_marking_enabled: bool
    neg_marking_value:   float
    sections:            List[BlueprintSectionRequest] = field(default_factory=list)
    course_id:           Optional[str] = None
    id:                  Optional[int] = None


blueprint_req_schema = marshmallow_dataclass.class_schema(BlueprintRequest)()


@dataclass_json
@dataclass
class BlueprintSectionResponse:
    id:              int
    name:            str
    subject:         str
    topics:          str
    q_type:          str
    count:           int
    marks_per_q:     float
    neg_marks_per_q: float
    difficulty:      str
    bloom:           str
    order:           int


@dataclass_json
@dataclass
class BlueprintResponse:
    id:                  int
    is_sys:              bool
    course_id:           Optional[str]
    course_name:         Optional[str]
    org_id:              Optional[int]
    duration:            str
    total_marks:         int
    neg_marking_enabled: bool
    neg_marking_value:   float
    sections:            List[BlueprintSectionResponse]
    created_at:          str
