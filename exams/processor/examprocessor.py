from dataclasses import dataclass
from typing import Any
from dataclasses_json import dataclass_json


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
