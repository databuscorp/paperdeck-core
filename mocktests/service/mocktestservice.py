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

    def fetch_all(self, user_id):
        tests = MockTest.objects.filter(owner_id=user_id).select_related('course')
        return [_build(t) for t in tests]

    def fetch_one(self, test_id, user_id):
        try:
            return _build(MockTest.objects.select_related('course').get(id=test_id, owner_id=user_id))
        except MockTest.DoesNotExist:
            return ErrorResponse(status=404, message='Mock test not found')

    def create_or_update(self, req, user_id):
        if req.id is None:
            t = MockTest.objects.create(
                owner_id=user_id,
                title=req.title,
                exam=req.exam,
                course_id=req.course_id or None,
                total_q=req.total_q,
                total_marks=req.total_marks,
                duration=req.duration,
                scheduled_on=req.scheduled_on or None,
                ends_at=req.ends_at or None,
                status=req.status or 'Upcoming',
            )
            t.refresh_from_db()
            t = MockTest.objects.select_related('course').get(id=t.id)
        else:
            try:
                t = MockTest.objects.select_related('course').get(id=req.id, owner_id=user_id)
            except MockTest.DoesNotExist:
                return ErrorResponse(status=404, message='Mock test not found')
            t.title = req.title
            t.exam = req.exam
            t.course_id = req.course_id or None
            t.total_q = req.total_q
            t.total_marks = req.total_marks
            t.duration = req.duration
            t.scheduled_on = req.scheduled_on or None
            t.ends_at = req.ends_at or None
            t.status = req.status or t.status
            t.save()
            t = MockTest.objects.select_related('course').get(id=t.id)
        return _build(t)

    def delete(self, test_id, user_id):
        deleted, _ = MockTest.objects.filter(id=test_id, owner_id=user_id).delete()
        if not deleted:
            return ErrorResponse(status=404, message='Mock test not found')
        return SuccessResponse(status=200, message='Mock test deleted')
