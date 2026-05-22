import json

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from rest_framework.decorators import api_view

from questions.processor.questionprocessor import question_req_schema, question_generate_req_schema
from questions.service.questionservice import QuestionService
from papers.service.aigeneratorservice import AIGeneratorService
from utility.decorator.auth import auth_required
from utility.utilityobj import ErrorResponse


@csrf_exempt
@api_view(['GET', 'POST', 'DELETE'])
@auth_required
@transaction.atomic
def question(request):
    if request.method == 'GET':
        return _fetch(request)
    elif request.method == 'POST':
        return _post(request)
    elif request.method == 'DELETE':
        return _delete(request)


def _fetch(request):
    scope = request.scope
    org_id = scope.get('org_id')
    question_id = request.query_params.get('question_id')
    course_id = request.query_params.get('course_id')
    service = QuestionService(scope)
    if question_id:
        resp = service.fetch_one(question_id, scope['user_id'], org_id=org_id)
        if isinstance(resp, ErrorResponse):
            return HttpResponse(resp.to_json(), status=resp.status, content_type='application/json')
        return HttpResponse(resp.to_json(), content_type='application/json')
    resp_list = service.fetch_all(scope['user_id'], org_id=org_id, course_id=course_id)
    return HttpResponse(json.dumps([q.to_dict() for q in resp_list]), content_type='application/json')


def _post(request):
    scope = request.scope
    org_id = scope.get('org_id')
    obj = question_req_schema.load(request.data)
    service = QuestionService(scope)
    resp = service.create_or_update(obj, scope['user_id'], org_id=org_id)
    if isinstance(resp, ErrorResponse):
        return HttpResponse(resp.to_json(), status=resp.status, content_type='application/json')
    return HttpResponse(resp.to_json(), content_type='application/json')


def _delete(request):
    scope = request.scope
    org_id = scope.get('org_id')
    question_id = request.query_params.get('question_id')
    if not question_id:
        return HttpResponse(
            ErrorResponse(status=400, message='question_id is required').to_json(),
            status=400, content_type='application/json'
        )
    service = QuestionService(scope)
    resp = service.delete(question_id, scope['user_id'], org_id=org_id)
    if isinstance(resp, ErrorResponse):
        return HttpResponse(resp.to_json(), status=resp.status, content_type='application/json')
    return HttpResponse(resp.to_json(), content_type='application/json')


@csrf_exempt
@api_view(['POST'])
@auth_required
def generate_questions(request):
    try:
        obj = question_generate_req_schema.load(request.data)
    except Exception as e:
        return HttpResponse(
            ErrorResponse(status=400, message=str(e)).to_json(),
            status=400, content_type='application/json'
        )

    # Resolve exam/subject/topic display strings from DB when FK IDs are provided
    exam = obj.exam or ''
    subject = obj.subject or ''
    topic = obj.topic or ''

    if obj.course_id:
        try:
            from courses.models import Course
            course = Course.objects.select_related('authority').get(id=obj.course_id)
            if course.authority:
                exam = course.authority.name
        except Exception:
            pass

    if obj.subject_id:
        try:
            from subjects.models import Subject
            subj = Subject.objects.get(id=obj.subject_id)
            subject = subj.name
        except Exception:
            pass

    if obj.topic_id:
        try:
            from subjects.models import Topic
            t = Topic.objects.get(id=obj.topic_id)
            topic = t.name
        except Exception:
            pass

    try:
        generator = AIGeneratorService()
        questions = generator.generate_questions(
            exam=exam,
            subject=subject,
            topic=topic or '',
            q_type=obj.q_type,
            difficulty=obj.difficulty,
            bloom=obj.bloom,
            count=obj.count,
        )
        return HttpResponse(json.dumps(questions), content_type='application/json')
    except Exception as e:
        return HttpResponse(
            ErrorResponse(status=500, message=f'Generation failed: {str(e)}').to_json(),
            status=500, content_type='application/json'
        )
