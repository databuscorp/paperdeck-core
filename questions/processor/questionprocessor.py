from dataclasses import dataclass
from typing import Any, List, Optional

import marshmallow_dataclass
from dataclasses_json import dataclass_json
from marshmallow import EXCLUDE


@dataclass
class QuestionRequest:
    q_type:      str
    difficulty:  str
    marks:       int
    text:        str
    # FK-based fields (new flow)
    course_id:   Optional[str] = None   # UUID string
    subject_id:  Optional[int] = None
    topic_id:    Optional[int] = None
    # String fallbacks (legacy / AI-generated display values)
    exam:        Optional[str] = None
    subject:     Optional[str] = None
    topic:       Optional[str] = None
    bloom:       Optional[str] = 'Understand'
    neg_marks:   Optional[int] = 0
    options:     Optional[Any] = None
    explanation: Optional[str] = None
    image_svg:   Optional[str] = None
    source:      Optional[str] = 'manual'
    id:          Optional[int] = None
    # has_latex is computed server-side; clients may send it but it is re-computed on every save
    has_latex:   Optional[bool] = None


question_req_schema = marshmallow_dataclass.class_schema(QuestionRequest)(unknown=EXCLUDE)


@dataclass
class QuestionGenerateRequest:
    q_type:     str
    difficulty: str
    bloom:      str
    count:      int
    # FK-based (preferred — resolves names from DB)
    course_id:  Optional[str] = None
    subject_id: Optional[int] = None
    topic_id:   Optional[int] = None
    # String fallbacks (legacy)
    exam:       Optional[str] = None
    subject:    Optional[str] = None
    topic:      Optional[str] = None


question_generate_req_schema = marshmallow_dataclass.class_schema(QuestionGenerateRequest)(unknown=EXCLUDE)


@dataclass_json
@dataclass
class QuestionResponse:
    id:          int
    q_type:      str
    difficulty:  str
    bloom:       str
    marks:       int
    neg_marks:   int
    text:        str
    source:      str
    created_at:  str
    # Resolved display strings
    exam:        Optional[str]
    subject:     Optional[str]
    topic:       Optional[str]
    # FK references
    course_id:   Optional[str]
    course_name: Optional[str]
    subject_id:  Optional[int]
    topic_id:    Optional[int]
    options:     Optional[Any]
    explanation: Optional[str]
    image_svg:   Optional[str]
    # LaTeX flag — True when text/options contain $...$ math notation
    has_latex:   bool = False