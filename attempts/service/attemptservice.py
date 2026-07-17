from django.utils import timezone
from django.utils.dateparse import parse_datetime

from attempts.models import QuestionResponse, StudentAttempt
from attempts.processor.attemptprocessor import (AttemptResponse, QuestionResponseResponse)
from attempts.service import gradingservice
from utility.dbservice import DBService
from utility.utilityobj import ErrorResponse


def _build_response(r: QuestionResponse) -> QuestionResponseResponse:
    return QuestionResponseResponse(
        id=r.id,
        question_id=r.question_id,
        question_snapshot_id=r.question_snapshot_id or '',
        selected_option_index=r.selected_option_index,
        selected_option_indices=r.selected_option_indices,
        numeric_answer=r.numeric_answer,
        status=r.status,
        is_correct=r.is_correct,
        marks_awarded=r.marks_awarded,
        time_spent_seconds=r.time_spent_seconds,
    )


def _build(attempt: StudentAttempt, with_responses: bool = True) -> AttemptResponse:
    student = getattr(attempt, 'student', None)
    return AttemptResponse(
        id=attempt.id,
        student_id=attempt.student_id,
        student_name=student.name if student else None,
        paper_id=attempt.paper_id,
        mock_test_id=attempt.mock_test_id,
        status=attempt.status,
        source=attempt.source,
        total_score=attempt.total_score,
        max_score=attempt.max_score,
        started_at=attempt.started_at.isoformat() if attempt.started_at else None,
        submitted_at=attempt.submitted_at.isoformat() if attempt.submitted_at else None,
        responses=[_build_response(r) for r in attempt.responses.all()] if with_responses else [],
    )


class AttemptService(DBService):
    def __init__(self, scope):
        super().__init__(scope)

    def submit(self, req, org_id=None):
        """Create an attempt with its responses and grade it in one shot.

        This is deliberately a submit-the-whole-thing endpoint rather than an
        answer-by-answer one: the OMR scanner, the bulk teacher entry screen and an online
        player all naturally produce a complete response set, and grading is cheap.
        """
        from students.models import Student

        student_qs = Student.objects.filter(id=req.student_id)
        if org_id:
            student_qs = student_qs.filter(org_id=org_id)
        student = student_qs.first()
        if student is None:
            return ErrorResponse(status=404, message='Student not found')

        if not req.paper_id and not req.mock_test_id:
            return ErrorResponse(status=400, message='paper_id or mock_test_id is required')

        if req.paper_id:
            from papers.models import Paper
            paper_qs = Paper.objects.filter(id=req.paper_id)
            if org_id:
                paper_qs = paper_qs.filter(org_id=org_id)
            if not paper_qs.exists():
                return ErrorResponse(status=404, message='Paper not found')

        submitted_at = parse_datetime(req.submitted_at) if req.submitted_at else None

        attempt = StudentAttempt.objects.create(
            org_id=org_id,
            student_id=student.id,
            paper_id=req.paper_id or None,
            mock_test_id=req.mock_test_id or None,
            source=req.source or StudentAttempt.SOURCE_ONLINE,
            submitted_at=submitted_at or timezone.now(),
            status=StudentAttempt.STATUS_SUBMITTED,
        )

        seen = set()
        rows = []
        for r in (req.responses or []):
            if r.question_id is None and not r.question_snapshot_id:
                continue
            # unique_together (attempt, question) — drop dupes rather than 500 on the insert.
            ident = ('q', r.question_id) if r.question_id else ('s', str(r.question_snapshot_id))
            if ident in seen:
                continue
            seen.add(ident)
            rows.append(QuestionResponse(
                attempt=attempt,
                question_id=r.question_id,
                question_snapshot_id=str(r.question_snapshot_id or ''),
                selected_option_index=r.selected_option_index,
                selected_option_indices=r.selected_option_indices,
                numeric_answer=r.numeric_answer,
                time_spent_seconds=r.time_spent_seconds,
            ))
        if rows:
            QuestionResponse.objects.bulk_create(rows)

        gradingservice.grade_attempt(attempt)
        attempt.refresh_from_db()
        return _build(attempt)

    def fetch_all(self, org_id=None, paper_id=None, student_id=None, mock_test_id=None):
        qs = StudentAttempt.objects.all().select_related('student')
        if org_id:
            qs = qs.filter(org_id=org_id)
        if paper_id:
            qs = qs.filter(paper_id=paper_id)
        if student_id:
            qs = qs.filter(student_id=student_id)
        if mock_test_id:
            qs = qs.filter(mock_test_id=mock_test_id)
        return [_build(a, with_responses=False) for a in qs]

    def fetch_one(self, attempt_id, org_id=None):
        qs = StudentAttempt.objects.select_related('student').prefetch_related('responses')
        if org_id:
            qs = qs.filter(org_id=org_id)
        attempt = qs.filter(id=attempt_id).first()
        if attempt is None:
            return ErrorResponse(status=404, message='Attempt not found')
        return _build(attempt)
