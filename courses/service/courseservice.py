from django.utils.text import slugify

from courses.models import Course, CourseSubscription
from courses.processor.courseprocessor import CourseResponse, CourseRequest
from utility.dbservice import DBService
from utility.utilityobj import SuccessResponse, ErrorResponse


def _build_course_response(course: Course, subscribed_ids: set = None) -> CourseResponse:
    from staff.models import Staff
    from students.models import Student
    from subjects.models import Subject
    return CourseResponse(
        id=str(course.id),
        name=course.name,
        slug=course.slug,
        course_type=course.course_type,
        description=course.description,
        grade_level=course.grade_level,
        duration_minutes=course.duration_minutes,
        total_marks=course.total_marks,
        instructions=course.instructions,
        is_active=course.is_active,
        is_sys=course.is_sys,
        authority_id=str(course.authority_id) if course.authority_id else None,
        authority_name=course.authority.name if course.authority else None,
        authority_short_name=course.authority.short_name if course.authority else None,
        created_at=course.created_at.isoformat(),
        updated_at=course.updated_at.isoformat(),
        staff_count=Staff.objects.filter(courses__id=course.id).count(),
        student_count=Student.objects.filter(courses__id=course.id).count(),
        subject_count=Subject.objects.filter(course_id=course.id).count(),
        is_subscribed=course.id in subscribed_ids if subscribed_ids is not None else False,
    )


def _unique_slug(name: str, exclude_id=None) -> str:
    base = slugify(name)
    slug = base
    n = 1
    qs = Course.objects.filter(slug=slug)
    if exclude_id:
        qs = qs.exclude(id=exclude_id)
    while qs.exists():
        slug = f"{base}-{n}"
        n += 1
        qs = Course.objects.filter(slug=slug)
        if exclude_id:
            qs = qs.exclude(id=exclude_id)
    return slug


class CourseService(DBService):
    def __init__(self, scope):
        super().__init__(scope)

    def _subscribed_ids(self, org_id):
        if not org_id:
            return set()
        # Explicit subscriptions + org's own courses are always considered subscribed
        sub_ids = set(CourseSubscription.objects.filter(org_id=org_id).values_list('course_id', flat=True))
        own_ids = set(Course.objects.filter(org_id=org_id).values_list('id', flat=True))
        return sub_ids | own_ids

    def fetch_courses(self, user_id, org_id=None):
        from django.db.models import Q
        courses = Course.objects.filter(
            Q(is_sys=True) | Q(org_id=org_id) if org_id else Q(is_sys=True) | Q(created_by_id=user_id)
        ).select_related('authority')
        subscribed_ids = self._subscribed_ids(org_id)
        return [_build_course_response(c, subscribed_ids=subscribed_ids) for c in courses]

    def fetch_course(self, course_id, user_id, org_id=None):
        from django.db.models import Q
        try:
            course = Course.objects.select_related('authority').get(
                Q(id=course_id),
                Q(is_sys=True) | Q(org_id=org_id) if org_id else Q(is_sys=True) | Q(created_by_id=user_id)
            )
        except Course.DoesNotExist:
            return ErrorResponse(status=404, message='Course not found')
        subscribed_ids = self._subscribed_ids(org_id)
        return _build_course_response(course, subscribed_ids=subscribed_ids)

    def create_or_update_course(self, req: CourseRequest, user_id, org_id=None):
        if req.id is None:
            slug = req.slug or _unique_slug(req.name)
            course = Course.objects.create(
                org_id=org_id,
                created_by_id=user_id,
                name=req.name,
                slug=slug,
                course_type=req.course_type or 'common',
                description=req.description,
                grade_level=req.grade_level,
                duration_minutes=req.duration_minutes or 0,
                total_marks=req.total_marks or 0,
                instructions=req.instructions,
                is_active=req.is_active if req.is_active is not None else True,
                authority_id=req.authority_id or None,
            )
            # Auto-subscribe the org that creates the course
            if org_id:
                CourseSubscription.objects.get_or_create(
                    course_id=course.id,
                    org_id=org_id,
                    defaults={'subscribed_by_id': user_id},
                )
        else:
            try:
                if org_id:
                    course = Course.objects.get(id=req.id, org_id=org_id)
                else:
                    course = Course.objects.get(id=req.id, created_by_id=user_id)
            except Course.DoesNotExist:
                return ErrorResponse(status=404, message='Course not found')
            course.name = req.name
            course.slug = req.slug or _unique_slug(req.name, exclude_id=req.id)
            course.course_type = req.course_type or course.course_type
            course.description = req.description
            course.grade_level = req.grade_level
            course.duration_minutes = req.duration_minutes if req.duration_minutes is not None else course.duration_minutes
            course.total_marks = req.total_marks if req.total_marks is not None else course.total_marks
            course.instructions = req.instructions
            course.is_active = req.is_active if req.is_active is not None else course.is_active
            course.authority_id = req.authority_id or None
            course.save()
        course.refresh_from_db()
        if course.authority_id:
            course = Course.objects.select_related('authority').get(id=course.id)
        return _build_course_response(course)

    def delete_course(self, course_id, user_id, org_id=None):
        if org_id:
            deleted, _ = Course.objects.filter(id=course_id, org_id=org_id).delete()
        else:
            deleted, _ = Course.objects.filter(id=course_id, created_by_id=user_id).delete()
        if not deleted:
            return ErrorResponse(status=404, message='Course not found')
        return SuccessResponse(status=200, message='Course deleted')

    def subscribe(self, course_id, org_id, user_id):
        if not org_id:
            return ErrorResponse(status=403, message='org_id required to subscribe')
        try:
            course = Course.objects.select_related('authority').get(id=course_id)
        except Course.DoesNotExist:
            return ErrorResponse(status=404, message='Course not found')
        _, created = CourseSubscription.objects.get_or_create(
            course_id=course_id,
            org_id=org_id,
            defaults={'subscribed_by_id': user_id},
        )
        if not created:
            return ErrorResponse(status=409, message='Already subscribed to this course')
        return _build_course_response(course, subscribed_ids={course.id})

    def unsubscribe(self, course_id, org_id, user_id):
        if not org_id:
            return ErrorResponse(status=403, message='org_id required')
        deleted, _ = CourseSubscription.objects.filter(course_id=course_id, org_id=org_id).delete()
        if not deleted:
            return ErrorResponse(status=404, message='Subscription not found')
        try:
            course = Course.objects.select_related('authority').get(id=course_id)
        except Course.DoesNotExist:
            return SuccessResponse(status=200, message='Unsubscribed')
        return _build_course_response(course, subscribed_ids=set())
