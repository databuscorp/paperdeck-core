from dataclasses import dataclass
from typing import Optional

import marshmallow_dataclass
from dataclasses_json import dataclass_json


@dataclass
class StudentRequest:
    course_id: int
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    roll_no: Optional[str] = None
    joined_date: Optional[str] = None
    attendance: Optional[int] = 0
    id: Optional[int] = None


student_req_schema = marshmallow_dataclass.class_schema(StudentRequest)()


@dataclass_json
@dataclass
class StudentResponse:
    id: int
    course_id: int
    name: str
    email: Optional[str]
    phone: Optional[str]
    roll_no: Optional[str]
    joined_date: Optional[str]
    attendance: int
    created_at: str
    course_name: Optional[str] = None
