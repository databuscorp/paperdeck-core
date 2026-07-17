import json
import uuid

from django.db import transaction
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view

from attempts.processor.attemptprocessor import (adaptive_practice_req_schema,
                                                 attempt_req_schema)
from attempts.service.attemptservice import AttemptService
from attempts.service.itemanalysisservice import ItemAnalysisService
from utility.decorator.auth import auth_required
from utility.decorator.ratelimit import rate_limit
from utility.utilityobj import ErrorResponse


def _err(status, message):
    return HttpResponse(
        ErrorResponse(status=status, message=message).to_json(),
        status=status, content_type='application/json',
    )


def _ok(resp):
    if isinstance(resp, ErrorResponse):
        return HttpResponse(resp.to_json(), status=resp.status, content_type='application/json')
    return HttpResponse(resp.to_json(), content_type='application/json')


@csrf_exempt
@api_view(['GET', 'POST'])
@auth_required
@transaction.atomic
def attempt(request):
    if request.method == 'POST':
        return _post(request)
    return _fetch(request)


def _post(request):
    """POST /api/attempts/ — create an attempt with its responses, and grade it."""
    try:
        obj = attempt_req_schema.load(request.data)
    except Exception as e:
        return _err(400, str(e))

    scope = request.scope
    service = AttemptService(scope)
    return _ok(service.submit(obj, org_id=scope.get('org_id')))


def _fetch(request):
    """GET /api/attempts/?paper_id= | ?student_id= | ?attempt_id="""
    scope = request.scope
    org_id = scope.get('org_id')
    service = AttemptService(scope)

    attempt_id = request.query_params.get('attempt_id')
    if attempt_id:
        return _ok(service.fetch_one(attempt_id, org_id=org_id))

    resp_list = service.fetch_all(
        org_id=org_id,
        paper_id=request.query_params.get('paper_id'),
        student_id=request.query_params.get('student_id'),
        mock_test_id=request.query_params.get('mock_test_id'),
    )
    return HttpResponse(json.dumps([a.to_dict() for a in resp_list]), content_type='application/json')


@csrf_exempt
@api_view(['GET'])
@auth_required
def analysis(request):
    """GET /api/attempts/analysis/?paper_id= — per-question item analysis.

    Returns p_value (high == EASY), the 27% discrimination index, a calibrated_difficulty
    measured from real students, and `is_broken` for questions with NEGATIVE discrimination
    (top students getting it wrong more than bottom students — almost always a bad key).
    Below the documented minimum N the statistics are suppressed rather than guessed at.
    """
    paper_id = request.query_params.get('paper_id')
    if not paper_id:
        return _err(400, 'paper_id is required')
    try:
        paper_id = int(paper_id)
    except (TypeError, ValueError):
        return _err(400, 'paper_id must be an integer')

    service = ItemAnalysisService(request.scope)
    return _ok(service.analyse_paper(paper_id))


@csrf_exempt
@api_view(['GET'])
@auth_required
def student_summary(request):
    """GET /api/attempts/student/?student_id= — per-topic weakness summary, weakest first."""
    student_id = request.query_params.get('student_id')
    if not student_id:
        return _err(400, 'student_id is required')
    try:
        student_id = int(student_id)
    except (TypeError, ValueError):
        return _err(400, 'student_id must be an integer')

    service = ItemAnalysisService(request.scope)
    return _ok(service.student_summary(student_id))


@csrf_exempt
@api_view(['GET'])
@auth_required
def cohort_summary(request):
    """GET /api/attempts/cohort/?course_id=&exam= — topic mastery across the whole batch.

    The "what should we re-teach" view for a coaching owner: per-topic cohort accuracy
    (== the topic's p_value, so it carries a calibrated Easy/Medium/Hard/HOTS label), how
    many students it covers, and average time spent. Weakest topics first.
    """
    course_id = request.query_params.get('course_id') or None
    exam = request.query_params.get('exam') or None
    service = ItemAnalysisService(request.scope)
    return _ok(service.cohort_summary(course_id=course_id, exam=exam))


@csrf_exempt
@api_view(['POST'])
@auth_required
@rate_limit('question_generate', limit=20, window_seconds=60)
@rate_limit('question_generate', limit=200, window_seconds=3600)
def adaptive_practice(request):
    """POST /api/attempts/adaptive-practice/ — generate a practice set on a student's weak topics.

    Body: {student_id, count=10, language='English', max_topics=3}. Reads the student's weak
    topics from their graded attempts, then generates fresh questions targeting them. Billed
    exactly like question generation: wallet checked first (402 if short), charged from real
    token usage after.
    """
    try:
        obj = adaptive_practice_req_schema.load(request.data)
    except Exception as e:
        return _err(400, str(e))

    scope = request.scope
    org_id = scope.get('org_id')
    count = max(1, min(int(obj.count or 10), 40))

    from billing.service.billingservice import BillingService
    from attempts.service.adaptivepracticeservice import AdaptivePracticeService

    billing = BillingService(scope)
    gate = billing.preflight(org_id, 'questions', count=count)
    if gate:
        return HttpResponse(gate.to_json(), status=gate.status, content_type='application/json')

    service = AdaptivePracticeService(scope)
    result = service.generate(obj.student_id, count=count,
                              language=obj.language or 'English',
                              max_topics=obj.max_topics or 3)

    usage = result.get('usage') or {}
    charge = billing.charge_usage(
        org_id,
        input_tokens=usage.get('input_tokens', 0),
        output_tokens=usage.get('output_tokens', 0),
        cache_read_tokens=usage.get('cache_read_input_tokens', 0),
        cache_write_tokens=usage.get('cache_creation_input_tokens', 0),
        reason='Adaptive practice: weak-topic targeting',
        ref=f'adaptive:{uuid.uuid4().hex}',
    )
    return HttpResponse(json.dumps({
        'questions': result.get('questions', []),
        'targeted_topics': result.get('targeted_topics', []),
        'message': result.get('message', 'ok'),
        'usage': usage,
        'usage_by_phase': result.get('usage_by_phase', {}),
        'charged': charge.get('charged', 0),
        'balance': charge.get('balance'),
    }), content_type='application/json')
