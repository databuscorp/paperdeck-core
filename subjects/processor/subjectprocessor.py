from dataclasses import dataclass
from typing import Optional, List

import marshmallow_dataclass
from dataclasses_json import dataclass_json


@dataclass
class SubjectRequest:
    course_id: str
    name: str
    description: Optional[str] = None
    id: Optional[int] = None


subject_req_schema = marshmallow_dataclass.class_schema(SubjectRequest)()


@dataclass
class TopicRequest:
    subject_id: int
    name: str
    description: Optional[str] = None
    order: int = 0
    id: Optional[int] = None


topic_req_schema = marshmallow_dataclass.class_schema(TopicRequest)()


@dataclass
class ChapterRequest:
    topic_id: int
    name: str
    description: Optional[str] = None
    order: int = 0
    id: Optional[int] = None


chapter_req_schema = marshmallow_dataclass.class_schema(ChapterRequest)()


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
class ChapterResponse:
    id: int
    topic_id: int
    name: str
    description: Optional[str]
    order: int
    is_sys: bool


@dataclass_json
@dataclass
class TopicResponse:
    id: int
    subject_id: int
    name: str
    description: Optional[str]
    order: int
    is_sys: bool
    chapters: List[ChapterResponse]


@dataclass_json
@dataclass
class SubjectResponse:
    id: int
    course_id: str
    name: str
    description: Optional[str]
    is_sys: bool
    created_at: str
    syllabus_files: List[SyllabusFileResponse]
    topics: List[TopicResponse]
