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


def _build_student_response(s: Student) -> StudentResponse:
    courses = list(s.courses.all())
    return StudentResponse(
        id=s.id,
        name=s.name,
        email=s.email,
        phone=s.phone,
        roll_no=s.roll_no,
        joined_date=_fmt_date(s.joined_date),
        created_at=s.created_at.isoformat(),
        user_id=s.user_id,
        course_ids=[str(c.id) for c in courses],
        course_names=[c.name for c in courses],
    )


def _create_user(email, password, name, org_id, role_const):
    from users.models import User
    if User.objects.filter(email=email).exists():
        raise ValueError(f'A user with email {email} already exists')
    name_parts = name.strip().split(' ', 1)
    return User.objects.create_user(
        username=email,
        email=email,
        password=password,
        first_name=name_parts[0],
        last_name=name_parts[1] if len(name_parts) > 1 else '',
        org_id=org_id,
        role=role_const,
    )


class StudentService(DBService):
    def __init__(self, scope):
        super().__init__(scope)

    def fetch_students(self, course_id, org_id=None):
        qs = Student.objects.filter(courses__id=course_id).prefetch_related('courses')
        if org_id:
            qs = qs.filter(org_id=org_id)
        return [_build_student_response(s) for s in qs.distinct()]

    def fetch_all_students(self, user_id, org_id=None):
        qs = Student.objects.prefetch_related('courses').order_by('name')
        if org_id:
            qs = qs.filter(org_id=org_id)
        return [_build_student_response(s) for s in qs]

    def fetch_one_student(self, student_id, org_id=None):
        try:
            s = Student.objects.prefetch_related('courses').get(id=student_id)
            if org_id and s.org_id is not None and s.org_id != org_id:
                return ErrorResponse(status=404, message='Student not found')
            return _build_student_response(s)
        except Student.DoesNotExist:
            return ErrorResponse(status=404, message='Student not found')

    def create_or_update_student(self, req, org_id=None):
        if req.id is None:
            user = None
            if req.email and req.password:
                from users.models import User
                try:
                    user = _create_user(req.email, req.password, req.name, org_id, User.ROLE_STUDENT)
                except ValueError as e:
                    return ErrorResponse(status=409, message=str(e))

            student = Student.objects.create(
                org_id=org_id,
                name=req.name,
                email=req.email,
                phone=req.phone,
                roll_no=req.roll_no,
                joined_date=req.joined_date or None,
                user=user,
            )
            if req.course_ids:
                from courses.models import Course
                from django.db.models import Q
                valid_ids = list(Course.objects.filter(
                    Q(id__in=req.course_ids) & (Q(org_id=org_id) | Q(is_sys=True))
                ).values_list('id', flat=True))
                student.courses.set(valid_ids)
        else:
            try:
                student = Student.objects.prefetch_related('courses').get(id=req.id)
            except Student.DoesNotExist:
                return ErrorResponse(status=404, message='Student not found')
            if org_id and student.org_id != org_id:
                return ErrorResponse(status=404, message='Student not found')
            student.name = req.name
            student.email = req.email
            student.phone = req.phone
            student.roll_no = req.roll_no
            student.joined_date = req.joined_date or None
            student.save()
            if req.course_ids is not None:
                student.courses.set(req.course_ids)
        return _build_student_response(Student.objects.prefetch_related('courses').get(id=student.id))

    def delete_student(self, student_id, org_id=None):
        try:
            student = Student.objects.get(id=student_id)
        except Student.DoesNotExist:
            return ErrorResponse(status=404, message='Student not found')
        if org_id and student.org_id != org_id:
            return ErrorResponse(status=404, message='Student not found')
        student.delete()
        return SuccessResponse(status=200, message='Student deleted')
