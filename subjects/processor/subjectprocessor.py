from dataclasses import dataclass
from typing import Optional, List

import marshmallow_dataclass
from dataclasses_json import dataclass_json


@dataclass
class SubjectRequest:
    course_id: int
    name: str
    description: Optional[str] = None
    id: Optional[int] = None


subject_req_schema = marshmallow_dataclass.class_schema(SubjectRequest)()


@dataclass_json
@dataclass
class SyllabusFileResponse:
    id: int
    name: str
    file_url: Optional[str]
    file_size: Optional[str]
    uploaded_at: str


@dataclass_json
@dataclass
class SubjectResponse:
    id: int
    course_id: int
    name: str
    description: Optional[str]
    created_at: str
    syllabus_files: List[SyllabusFileResponse]
