from dataclasses import dataclass
from typing import Optional

import marshmallow_dataclass
from dataclasses_json import dataclass_json


@dataclass
class MockTestRequest:
    title:        str
    exam:         str
    total_q:      int
    total_marks:  int
    duration:     str
    course_id:    Optional[int] = None
    scheduled_on: Optional[str] = None
    ends_at:      Optional[str] = None
    status:       Optional[str] = 'Upcoming'
    id:           Optional[int] = None


mocktest_req_schema = marshmallow_dataclass.class_schema(MockTestRequest)()


@dataclass_json
@dataclass
class MockTestResponse:
    id:           int
    title:        str
    exam:         str
    course_id:    Optional[int]
    course_name:  Optional[str]
    total_q:      int
    total_marks:  int
    duration:     str
    scheduled_on: Optional[str]
    ends_at:      Optional[str]
    status:       str
    enrolled:     int
    attempted:    int
    avg_score:    Optional[float]
    created_at:   str
