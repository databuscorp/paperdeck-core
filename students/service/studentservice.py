from courses.models import Course
from students.models import Student
from students.processor.studentprocessor import StudentResponse
from utility.dbservice import DBService
from utility.utilityobj import SuccessResponse, ErrorResponse


def _fmt_date(d):
    if d is None:
        return None
    if isinstance(d, str):
        return d
    return d.strftime('%Y-%m-%d')


def _build_student_response(s: Student, course_name: str = None) -> StudentResponse:
    return StudentResponse(
        id=s.id,
        course_id=s.course_id,
        name=s.name,
        email=s.email,
        phone=s.phone,
        roll_no=s.roll_no,
        joined_date=_fmt_date(s.joined_date),
        attendance=s.attendance,
        created_at=s.created_at.isoformat(),
        course_name=course_name,
    )


class StudentService(DBService):
    def __init__(self, scope):
        super().__init__(scope)

    def fetch_students(self, course_id, org_id=None):
        if org_id:
            students = Student.objects.filter(course_id=course_id, course__owner__org_id=org_id)
        else:
            students = Student.objects.filter(course_id=course_id)
        return [_build_student_response(s) for s in students]

    def fetch_all_students(self, user_id, org_id=None):
        if org_id:
            students = Student.objects.filter(course__owner__org_id=org_id).select_related('course').order_by('course__name', 'name')
        else:
            students = Student.objects.filter(course__owner_id=user_id).select_related('course').order_by('course__name', 'name')
        return [_build_student_response(s, course_name=s.course.name) for s in students]

    def fetch_one_student(self, student_id, org_id=None):
        try:
            if org_id:
                s = Student.objects.select_related('course').get(id=student_id, course__owner__org_id=org_id)
            else:
                s = Student.objects.select_related('course').get(id=student_id)
            return _build_student_response(s, course_name=s.course.name)
        except Student.DoesNotExist:
            return ErrorResponse(status=404, message='Student not found')

    def create_or_update_student(self, req, org_id=None):
        if req.id is None:
            if org_id and not Course.objects.filter(id=req.course_id, owner__org_id=org_id).exists():
                return ErrorResponse(status=403, message='Course not found or access denied')
            student = Student.objects.create(
                course_id=req.course_id,
                name=req.name,
                email=req.email,
                phone=req.phone,
                roll_no=req.roll_no,
                joined_date=req.joined_date or None,
                attendance=req.attendance or 0,
            )
        else:
            try:
                if org_id:
                    student = Student.objects.get(id=req.id, course__owner__org_id=org_id)
                else:
                    student = Student.objects.get(id=req.id)
            except Student.DoesNotExist:
                return ErrorResponse(status=404, message='Student not found')
            student.name = req.name
            student.email = req.email
            student.phone = req.phone
            student.roll_no = req.roll_no
            student.joined_date = req.joined_date or None
            student.attendance = req.attendance or student.attendance
            student.save()
        return _build_student_response(student)

    def delete_student(self, student_id, org_id=None):
        if org_id:
            deleted, _ = Student.objects.filter(id=student_id, course__owner__org_id=org_id).delete()
        else:
            deleted, _ = Student.objects.filter(id=student_id).delete()
        if not deleted:
            return ErrorResponse(status=404, message='Student not found')
        return SuccessResponse(status=200, message='Student deleted')
