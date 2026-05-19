from dataclasses import dataclass
from typing import Optional

import marshmallow_dataclass
from dataclasses_json import dataclass_json


@dataclass
class CourseRequest:
    name: str
    category: str
    description: Optional[str] = None
    status: Optional[str] = 'active'
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    duration: Optional[str] = None
    id: Optional[int] = None


course_req_schema = marshmallow_dataclass.class_schema(CourseRequest)()


@dataclass_json
@dataclass
class CourseResponse:
    id: int
    name: str
    category: str
    description: Optional[str]
    status: str
    start_date: Optional[str]
    end_date: Optional[str]
    duration: Optional[str]
    created_at: str
    staff_count: int = 0
    student_count: int = 0
    subject_count: int = 0
