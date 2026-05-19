import json

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from rest_framework.decorators import api_view

from questions.processor.questionprocessor import question_req_schema
from questions.service.questionservice import QuestionService
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
    question_id = request.query_params.get('question_id')
    service = QuestionService(scope)
    if question_id:
        resp = service.fetch_one(question_id, scope['user_id'])
        if isinstance(resp, ErrorResponse):
            return HttpResponse(resp.to_json(), status=resp.status, content_type='application/json')
        return HttpResponse(resp.to_json(), content_type='application/json')
    resp_list = service.fetch_all(scope['user_id'])
    return HttpResponse(json.dumps([q.to_dict() for q in resp_list]), content_type='application/json')


def _post(request):
    scope = request.scope
    obj = question_req_schema.load(request.data)
    service = QuestionService(scope)
    resp = service.create_or_update(obj, scope['user_id'])
    if isinstance(resp, ErrorResponse):
        return HttpResponse(resp.to_json(), status=resp.status, content_type='application/json')
    return HttpResponse(resp.to_json(), content_type='application/json')


def _delete(request):
    scope = request.scope
    question_id = request.query_params.get('question_id')
    if not question_id:
        return HttpResponse(
            ErrorResponse(status=400, message='question_id is required').to_json(),
            status=400, content_type='application/json'
        )
    service = QuestionService(scope)
    resp = service.delete(question_id, scope['user_id'])
    if isinstance(resp, ErrorResponse):
        return HttpResponse(resp.to_json(), status=resp.status, content_type='application/json')
    return HttpResponse(resp.to_json(), content_type='application/json')
