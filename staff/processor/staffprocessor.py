from dataclasses import dataclass
from typing import Optional

import marshmallow_dataclass
from dataclasses_json import dataclass_json


@dataclass
class StaffRequest:
    course_id: int
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    subject: Optional[str] = None
    role: Optional[str] = None
    joined_date: Optional[str] = None
    id: Optional[int] = None


staff_req_schema = marshmallow_dataclass.class_schema(StaffRequest)()


@dataclass_json
@dataclass
class StaffResponse:
    id: int
    course_id: int
    name: str
    email: Optional[str]
    phone: Optional[str]
    subject: Optional[str]
    role: Optional[str]
    joined_date: Optional[str]
    created_at: str
    course_name: Optional[str] = None
