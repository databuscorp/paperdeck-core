from courses.models import Course
from subjects.models import Subject, SyllabusFile
from subjects.processor.subjectprocessor import SubjectResponse, SyllabusFileResponse
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


def _build_subject_response(subject: Subject) -> SubjectResponse:
    files = SyllabusFile.objects.filter(subject_id=subject.id)
    return SubjectResponse(
        id=subject.id,
        course_id=subject.course_id,
        name=subject.name,
        description=subject.description,
        created_at=subject.created_at.isoformat(),
        syllabus_files=[_build_syllabus_response(f) for f in files],
    )


class SubjectService(DBService):
    def __init__(self, scope):
        super().__init__(scope)

    def fetch_subjects(self, course_id, org_id=None):
        if org_id:
            subjects = Subject.objects.filter(course_id=course_id, course__owner__org_id=org_id)
        else:
            subjects = Subject.objects.filter(course_id=course_id)
        return [_build_subject_response(s) for s in subjects]

    def fetch_subject(self, subject_id, org_id=None):
        try:
            if org_id:
                subject = Subject.objects.get(id=subject_id, course__owner__org_id=org_id)
            else:
                subject = Subject.objects.get(id=subject_id)
        except Subject.DoesNotExist:
            return ErrorResponse(status=404, message='Subject not found')
        return _build_subject_response(subject)

    def create_or_update_subject(self, req, org_id=None):
        if req.id is None:
            if org_id and not Course.objects.filter(id=req.course_id, owner__org_id=org_id).exists():
                return ErrorResponse(status=403, message='Course not found or access denied')
            subject = Subject.objects.create(
                course_id=req.course_id,
                name=req.name,
                description=req.description,
            )
        else:
            try:
                if org_id:
                    subject = Subject.objects.get(id=req.id, course__owner__org_id=org_id)
                else:
                    subject = Subject.objects.get(id=req.id)
            except Subject.DoesNotExist:
                return ErrorResponse(status=404, message='Subject not found')
            subject.name = req.name
            subject.description = req.description
            subject.save()
        return _build_subject_response(subject)

    def delete_subject(self, subject_id, org_id=None):
        if org_id:
            deleted, _ = Subject.objects.filter(id=subject_id, course__owner__org_id=org_id).delete()
        else:
            deleted, _ = Subject.objects.filter(id=subject_id).delete()
        if not deleted:
            return ErrorResponse(status=404, message='Subject not found')
        return SuccessResponse(status=200, message='Subject deleted')

    def upload_syllabus(self, subject_id, file, name, file_size, org_id=None):
        try:
            if org_id:
                subject = Subject.objects.get(id=subject_id, course__owner__org_id=org_id)
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
            deleted, _ = SyllabusFile.objects.filter(id=syllabus_id, subject__course__owner__org_id=org_id).delete()
        else:
            deleted, _ = SyllabusFile.objects.filter(id=syllabus_id).delete()
        if not deleted:
            return ErrorResponse(status=404, message='Syllabus file not found')
        return SuccessResponse(status=200, message='Syllabus file deleted')
