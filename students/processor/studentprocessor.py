from dataclasses import dataclass, field
from typing import List, Optional

import marshmallow_dataclass
from dataclasses_json import dataclass_json
from marshmallow import EXCLUDE


@dataclass
class StudentRequest:
    name: str
    course_ids: Optional[List[str]] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    roll_no: Optional[str] = None
    joined_date: Optional[str] = None
    password: Optional[str] = None
    id: Optional[int] = None


student_req_schema = marshmallow_dataclass.class_schema(StudentRequest)(unknown=EXCLUDE)


@dataclass_json
@dataclass
class StudentResponse:
    id: int
    name: str
    email: Optional[str]
    phone: Optional[str]
    roll_no: Optional[str]
    joined_date: Optional[str]
    created_at: str
    course_ids: List[str] = field(default_factory=list)
    course_names: List[str] = field(default_factory=list)
    user_id: Optional[int] = None
