from courses.models import Course
from subjects.models import Subject, SyllabusFile, Topic, Chapter
from subjects.processor.subjectprocessor import (
    SubjectResponse, SyllabusFileResponse, TopicResponse, ChapterResponse,
)
from utility.dbservice import DBService
from utility.utilityobj import SuccessResponse, ErrorResponse


def _build_syllabus_response(sf: SyllabusFile) -> SyllabusFileResponse:
    return SyllabusFileResponse(
        id=sf.id,
        name=sf.name,
        file_url=sf.file_url or (sf.file.url if sf.file else None),
        file_size=sf.file_size,
        uploaded_at=sf.uploaded_at.isoformat(),
    )


def _build_chapter_response(ch: Chapter) -> ChapterResponse:
    return ChapterResponse(
        id=ch.id,
        topic_id=ch.topic_id,
        name=ch.name,
        description=ch.description,
        order=ch.order,
        is_sys=ch.is_sys,
    )


def _build_topic_response(topic: Topic) -> TopicResponse:
    chapters = Chapter.objects.filter(topic_id=topic.id)
    return TopicResponse(
        id=topic.id,
        subject_id=topic.subject_id,
        name=topic.name,
        description=topic.description,
        order=topic.order,
        is_sys=topic.is_sys,
        chapters=[_build_chapter_response(ch) for ch in chapters],
    )


def _build_subject_response(subject: Subject) -> SubjectResponse:
    files = SyllabusFile.objects.filter(subject_id=subject.id)
    topics = Topic.objects.filter(subject_id=subject.id)
    return SubjectResponse(
        id=subject.id,
        course_id=str(subject.course_id),
        name=subject.name,
        description=subject.description,
        is_sys=subject.is_sys,
        created_at=subject.created_at.isoformat(),
        syllabus_files=[_build_syllabus_response(f) for f in files],
        topics=[_build_topic_response(t) for t in topics],
    )


class SubjectService(DBService):
    def __init__(self, scope):
        super().__init__(scope)

    def fetch_subjects(self, course_id, org_id=None):
        from django.db.models import Q
        if org_id:
            subjects = Subject.objects.filter(
                Q(course_id=course_id),
                Q(org_id=org_id) | Q(is_sys=True),
            )
        else:
            subjects = Subject.objects.filter(course_id=course_id)
        return [_build_subject_response(s) for s in subjects]

    def fetch_subject(self, subject_id, org_id=None):
        try:
            if org_id:
                subject = Subject.objects.get(id=subject_id, course__org_id=org_id)
            else:
                subject = Subject.objects.get(id=subject_id)
        except Subject.DoesNotExist:
            return ErrorResponse(status=404, message='Subject not found')
        return _build_subject_response(subject)

    def create_or_update_subject(self, req, user_id=None, org_id=None):
        if req.id is None:
            if org_id and not Course.objects.filter(id=req.course_id, org_id=org_id).exists():
                return ErrorResponse(status=403, message='Course not found or access denied')
            subject = Subject.objects.create(
                course_id=req.course_id,
                org_id=org_id,
                created_by_id=user_id,
                name=req.name,
                description=req.description,
            )
        else:
            try:
                if org_id:
                    subject = Subject.objects.get(id=req.id, org_id=org_id)
                else:
                    subject = Subject.objects.get(id=req.id, created_by_id=user_id)
            except Subject.DoesNotExist:
                return ErrorResponse(status=404, message='Subject not found')
            subject.name = req.name
            subject.description = req.description
            subject.save()
        return _build_subject_response(subject)

    def delete_subject(self, subject_id, user_id=None, org_id=None):
        qs = Subject.objects.filter(id=subject_id, is_sys=False)
        if org_id:
            qs = qs.filter(org_id=org_id)
        elif user_id:
            qs = qs.filter(created_by_id=user_id)
        deleted, _ = qs.delete()
        if not deleted:
            return ErrorResponse(status=404, message='Subject not found')
        return SuccessResponse(status=200, message='Subject deleted')

    def upload_syllabus(self, subject_id, file, name, file_size, org_id=None):
        try:
            if org_id:
                subject = Subject.objects.get(id=subject_id, course__org_id=org_id)
            else:
                subject = Subject.objects.get(id=subject_id)
        except Subject.DoesNotExist:
            return ErrorResponse(status=404, message='Subject not found')

        sf = SyllabusFile.objects.create(
            subject=subject,
            name=name,
            file=file,
            file_size=file_size,
        )
        return _build_syllabus_response(sf)

    def delete_syllabus(self, syllabus_id, org_id=None):
        if org_id:
            deleted, _ = SyllabusFile.objects.filter(id=syllabus_id, subject__course__org_id=org_id).delete()
        else:
            deleted, _ = SyllabusFile.objects.filter(id=syllabus_id).delete()
        if not deleted:
            return ErrorResponse(status=404, message='Syllabus file not found')
        return SuccessResponse(status=200, message='Syllabus file deleted')

    # ── Topics ────────────────────────────────────────────────────────────────

    def fetch_topics(self, subject_id, org_id=None):
        from subjects.processor.subjectprocessor import TopicResponse
        if org_id:
            topics = Topic.objects.filter(
                subject_id=subject_id,
                subject__course__org_id=org_id,
            )
        else:
            topics = Topic.objects.filter(subject_id=subject_id)
        return [_build_topic_response(t) for t in topics]

    def create_or_update_topic(self, req, org_id=None):
        if req.id is None:
            try:
                if org_id:
                    subject = Subject.objects.get(id=req.subject_id, org_id=org_id, is_sys=False)
                else:
                    subject = Subject.objects.get(id=req.subject_id, is_sys=False)
            except Subject.DoesNotExist:
                return ErrorResponse(status=404, message='Subject not found or is read-only')
            topic = Topic.objects.create(
                subject=subject,
                name=req.name,
                description=req.description,
                order=req.order,
                is_sys=False,
            )
        else:
            try:
                if org_id:
                    topic = Topic.objects.get(id=req.id, is_sys=False, subject__org_id=org_id)
                else:
                    topic = Topic.objects.get(id=req.id, is_sys=False)
            except Topic.DoesNotExist:
                return ErrorResponse(status=404, message='Topic not found or is read-only')
            topic.name = req.name
            topic.description = req.description
            topic.order = req.order
            topic.save()
        return _build_topic_response(topic)

    def delete_topic(self, topic_id, org_id=None):
        qs = Topic.objects.filter(id=topic_id, is_sys=False)
        if org_id:
            qs = qs.filter(subject__org_id=org_id)
        deleted, _ = qs.delete()
        if not deleted:
            return ErrorResponse(status=404, message='Topic not found or is read-only')
        return SuccessResponse(status=200, message='Topic deleted')

    # ── Chapters ──────────────────────────────────────────────────────────────

    def create_or_update_chapter(self, req, org_id=None):
        if req.id is None:
            try:
                if org_id:
                    topic = Topic.objects.get(id=req.topic_id, is_sys=False, subject__org_id=org_id)
                else:
                    topic = Topic.objects.get(id=req.topic_id, is_sys=False)
            except Topic.DoesNotExist:
                return ErrorResponse(status=404, message='Topic not found or is read-only')
            chapter = Chapter.objects.create(
                topic=topic,
                name=req.name,
                description=req.description,
                order=req.order,
                is_sys=False,
            )
        else:
            try:
                if org_id:
                    chapter = Chapter.objects.get(id=req.id, is_sys=False, topic__subject__org_id=org_id)
                else:
                    chapter = Chapter.objects.get(id=req.id, is_sys=False)
            except Chapter.DoesNotExist:
                return ErrorResponse(status=404, message='Chapter not found or is read-only')
            chapter.name = req.name
            chapter.description = req.description
            chapter.order = req.order
            chapter.save()
        return _build_chapter_response(chapter)

    def delete_chapter(self, chapter_id, org_id=None):
        qs = Chapter.objects.filter(id=chapter_id, is_sys=False)
        if org_id:
            qs = qs.filter(topic__subject__org_id=org_id)
        deleted, _ = qs.delete()
        if not deleted:
            return ErrorResponse(status=404, message='Chapter not found or is read-only')
        return SuccessResponse(status=200, message='Chapter deleted')
