import json

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from rest_framework.decorators import api_view

from mocktests.processor.mocktestprocessor import mocktest_req_schema
from mocktests.service.mocktestservice import MockTestService
from utility.decorator.auth import auth_required
from utility.utilityobj import ErrorResponse


@csrf_exempt
@api_view(['GET', 'POST', 'DELETE'])
@auth_required
@transaction.atomic
def mocktest(request):
    if request.method == 'GET':
        return _fetch(request)
    elif request.method == 'POST':
        return _post(request)
    elif request.method == 'DELETE':
        return _delete(request)


def _fetch(request):
    scope = request.scope
    test_id = request.query_params.get('test_id')
    service = MockTestService(scope)
    if test_id:
        resp = service.fetch_one(test_id, scope['user_id'])
        if isinstance(resp, ErrorResponse):
            return HttpResponse(resp.to_json(), status=resp.status, content_type='application/json')
        return HttpResponse(resp.to_json(), content_type='application/json')
    resp_list = service.fetch_all(scope['user_id'])
    return HttpResponse(json.dumps([t.to_dict() for t in resp_list]), content_type='application/json')


def _post(request):
    scope = request.scope
    obj = mocktest_req_schema.load(request.data)
    service = MockTestService(scope)
    resp = service.create_or_update(obj, scope['user_id'])
    if isinstance(resp, ErrorResponse):
        return HttpResponse(resp.to_json(), status=resp.status, content_type='application/json')
    return HttpResponse(resp.to_json(), content_type='application/json')


def _delete(request):
    scope = request.scope
    test_id = request.query_params.get('test_id')
    if not test_id:
        return HttpResponse(
            ErrorResponse(status=400, message='test_id is required').to_json(),
            status=400, content_type='application/json'
        )
    service = MockTestService(scope)
    resp = service.delete(test_id, scope['user_id'])
    if isinstance(resp, ErrorResponse):
        return HttpResponse(resp.to_json(), status=resp.status, content_type='application/json')
    return HttpResponse(resp.to_json(), content_type='application/json')
