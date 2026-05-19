from courses.models import Course
from courses.processor.courseprocessor import CourseResponse
from utility.dbservice import DBService
from utility.utilityobj import SuccessResponse, ErrorResponse


def _fmt_date(d):
    if d is None:
        return None
    if isinstance(d, str):
        return d
    return d.strftime('%Y-%m-%d')


def _build_course_response(course: Course) -> CourseResponse:
    from staff.models import Staff
    from students.models import Student
    from subjects.models import Subject
    return CourseResponse(
        id=course.id,
        name=course.name,
        category=course.category,
        description=course.description,
        status=course.status,
        start_date=_fmt_date(course.start_date),
        end_date=_fmt_date(course.end_date),
        duration=course.duration,
        created_at=course.created_at.isoformat(),
        staff_count=Staff.objects.filter(course_id=course.id).count(),
        student_count=Student.objects.filter(course_id=course.id).count(),
        subject_count=Subject.objects.filter(course_id=course.id).count(),
    )


class CourseService(DBService):
    def __init__(self, scope):
        super().__init__(scope)

    def fetch_courses(self, user_id):
        courses = Course.objects.filter(owner_id=user_id)
        return [_build_course_response(c) for c in courses]

    def fetch_course(self, course_id, user_id):
        try:
            course = Course.objects.get(id=course_id, owner_id=user_id)
        except Course.DoesNotExist:
            return ErrorResponse(status=404, message='Course not found')
        return _build_course_response(course)

    def create_or_update_course(self, req, user_id):
        if req.id is None:
            course = Course.objects.create(
                owner_id=user_id,
                name=req.name,
                category=req.category,
                description=req.description,
                status=req.status or 'active',
                start_date=req.start_date or None,
                end_date=req.end_date or None,
                duration=req.duration,
            )
        else:
            try:
                course = Course.objects.get(id=req.id, owner_id=user_id)
            except Course.DoesNotExist:
                return ErrorResponse(status=404, message='Course not found')
            course.name = req.name
            course.category = req.category
            course.description = req.description
            course.status = req.status or course.status
            course.start_date = req.start_date or None
            course.end_date = req.end_date or None
            course.duration = req.duration
            course.save()
        return _build_course_response(course)

    def delete_course(self, course_id, user_id):
        deleted, _ = Course.objects.filter(id=course_id, owner_id=user_id).delete()
        if not deleted:
            return ErrorResponse(status=404, message='Course not found')
        return SuccessResponse(status=200, message='Course deleted')
