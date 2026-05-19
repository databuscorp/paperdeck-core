from dataclasses import dataclass
from typing import Any, List, Optional

import marshmallow_dataclass
from dataclasses_json import dataclass_json


@dataclass
class QuestionRequest:
    exam:        str
    subject:     str
    topic:       str
    q_type:      str
    difficulty:  str
    marks:       int
    text:        str
    bloom:       Optional[str] = 'Understand'
    options:     Optional[Any] = None
    explanation: Optional[str] = None
    id:          Optional[int] = None


question_req_schema = marshmallow_dataclass.class_schema(QuestionRequest)()


@dataclass_json
@dataclass
class QuestionResponse:
    id:          int
    exam:        str
    subject:     str
    topic:       str
    q_type:      str
    difficulty:  str
    bloom:       str
    marks:       int
    text:        str
    options:     Optional[Any]
    explanation: Optional[str]
    created_at:  str
