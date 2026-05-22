from dataclasses import dataclass
from typing import Optional

import marshmallow_dataclass
from dataclasses_json import dataclass_json


@dataclass
class CourseRequest:
    name: str
    course_type: Optional[str] = 'common'
    description: Optional[str] = None
    grade_level: Optional[str] = None
    duration_minutes: Optional[int] = 0
    total_marks: Optional[int] = 0
    instructions: Optional[str] = None
    is_active: Optional[bool] = True
    authority_id: Optional[str] = None
    slug: Optional[str] = None
    id: Optional[str] = None


course_req_schema = marshmallow_dataclass.class_schema(CourseRequest)()


@dataclass_json
@dataclass
class CourseResponse:
    id: str
    name: str
    slug: str
    course_type: str
    description: Optional[str]
    grade_level: Optional[str]
    duration_minutes: int
    total_marks: int
    instructions: Optional[str]
    is_active: bool
    is_sys: bool
    authority_id: Optional[str]
    authority_name: Optional[str]
    authority_short_name: Optional[str]
    created_at: str
    updated_at: str
    staff_count: int = 0
    student_count: int = 0
    subject_count: int = 0
    is_subscribed: bool = False
