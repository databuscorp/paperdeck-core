from courses.models import Course
from mocktests.models import MockTest
from mocktests.processor.mocktestprocessor import MockTestResponse
from utility.dbservice import DBService
from utility.utilityobj import SuccessResponse, ErrorResponse


def _fmt_dt(d):
    if d is None:
        return None
    if isinstance(d, str):
        return d
    return d.isoformat()


def _build(t: MockTest) -> MockTestResponse:
    return MockTestResponse(
        id=t.id,
        title=t.title,
        exam=t.exam,
        course_id=t.course_id,
        course_name=t.course.name if t.course else None,
        total_q=t.total_q,
        total_marks=t.total_marks,
        duration=t.duration,
        scheduled_on=_fmt_dt(t.scheduled_on),
        ends_at=_fmt_dt(t.ends_at),
        status=t.status,
        enrolled=t.enrolled,
        attempted=t.attempted,
        avg_score=t.avg_score,
        created_at=t.created_at.isoformat(),
    )


class MockTestService(DBService):
    def __init__(self, scope):
        super().__init__(scope)

    def fetch_all(self, user_id, org_id=None):
        qs = MockTest.objects.filter(owner__org_id=org_id) if org_id else MockTest.objects.filter(owner_id=user_id)
        return [_build(t) for t in qs.select_related('course')]

    def fetch_one(self, test_id, user_id, org_id=None):
        try:
            if org_id:
                return _build(MockTest.objects.select_related('course').get(id=test_id, owner__org_id=org_id))
            return _build(MockTest.objects.select_related('course').get(id=test_id, owner_id=user_id))
        except MockTest.DoesNotExist:
            return ErrorResponse(status=404, message='Mock test not found')

    def create_or_update(self, req, user_id, org_id=None):
        if req.id is None:
            course_id = req.course_id or None
            if course_id and org_id and not Course.objects.filter(id=course_id, owner__org_id=org_id).exists():
                return ErrorResponse(status=403, message='Course not found or access denied')
            t = MockTest.objects.create(
                owner_id=user_id,
                title=req.title,
                exam=req.exam,
                course_id=course_id,
                total_q=req.total_q,
                total_marks=req.total_marks,
                duration=req.duration,
                scheduled_on=req.scheduled_on or None,
                ends_at=req.ends_at or None,
                status=req.status or 'Upcoming',
            )
            t = MockTest.objects.select_related('course').get(id=t.id)
        else:
            try:
                if org_id:
                    t = MockTest.objects.select_related('course').get(id=req.id, owner__org_id=org_id)
                else:
                    t = MockTest.objects.select_related('course').get(id=req.id, owner_id=user_id)
            except MockTest.DoesNotExist:
                return ErrorResponse(status=404, message='Mock test not found')
            new_course_id = req.course_id or None
            if new_course_id and org_id and not Course.objects.filter(id=new_course_id, owner__org_id=org_id).exists():
                return ErrorResponse(status=403, message='Course not found or access denied')
            t.title = req.title
            t.exam = req.exam
            t.course_id = new_course_id
            t.total_q = req.total_q
            t.total_marks = req.total_marks
            t.duration = req.duration
            t.scheduled_on = req.scheduled_on or None
            t.ends_at = req.ends_at or None
            t.status = req.status or t.status
            t.save()
            t = MockTest.objects.select_related('course').get(id=t.id)
        return _build(t)

    def delete(self, test_id, user_id, org_id=None):
        if org_id:
            deleted, _ = MockTest.objects.filter(id=test_id, owner__org_id=org_id).delete()
        else:
            deleted, _ = MockTest.objects.filter(id=test_id, owner_id=user_id).delete()
        if not deleted:
            return ErrorResponse(status=404, message='Mock test not found')
        return SuccessResponse(status=200, message='Mock test deleted')
