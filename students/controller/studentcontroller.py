import json

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from rest_framework.decorators import api_view

from students.processor.studentprocessor import student_req_schema
from students.service.studentservice import StudentService
from utility.decorator.auth import auth_required
from utility.utilityobj import ErrorResponse


@csrf_exempt
@api_view(['GET', 'POST', 'DELETE'])
@auth_required
@transaction.atomic
def student(request):
    if request.method == 'GET':
        return _fetch_students(request)
    elif request.method == 'POST':
        return _post_student(request)
    elif request.method == 'DELETE':
        return _delete_student(request)


def _fetch_students(request):
    scope = request.scope
    org_id = scope.get('org_id')
    student_id = request.query_params.get('student_id')
    course_id = request.query_params.get('course_id')
    service = StudentService(scope)
    if student_id:
        resp = service.fetch_one_student(student_id, org_id=org_id)
        if isinstance(resp, ErrorResponse):
            return HttpResponse(resp.to_json(), status=resp.status, content_type='application/json')
        return HttpResponse(resp.to_json(), content_type='application/json')
    if course_id:
        resp_list = service.fetch_students(course_id, org_id=org_id)
    else:
        resp_list = service.fetch_all_students(scope['user_id'], org_id=org_id)
    return HttpResponse(json.dumps([s.to_dict() for s in resp_list]), content_type='application/json')


def _post_student(request):
    scope = request.scope
    if scope.get('role') != 1:
        return HttpResponse(
            ErrorResponse(status=403, message='Admin access required').to_json(),
            status=403, content_type='application/json'
        )
    org_id = scope.get('org_id')
    obj = student_req_schema.load(request.data)
    service = StudentService(scope)
    resp = service.create_or_update_student(obj, org_id=org_id)
    if isinstance(resp, ErrorResponse):
        return HttpResponse(resp.to_json(), status=resp.status, content_type='application/json')
    return HttpResponse(resp.to_json(), content_type='application/json')


def _delete_student(request):
    scope = request.scope
    if scope.get('role') != 1:
        return HttpResponse(
            ErrorResponse(status=403, message='Admin access required').to_json(),
            status=403, content_type='application/json'
        )
    org_id = scope.get('org_id')
    student_id = request.query_params.get('student_id')
    if not student_id:
        return HttpResponse(
            ErrorResponse(status=400, message='student_id is required').to_json(),
            status=400, content_type='application/json'
        )
    service = StudentService(scope)
    resp = service.delete_student(student_id, org_id=org_id)
    if isinstance(resp, ErrorResponse):
        return HttpResponse(resp.to_json(), status=resp.status, content_type='application/json')
    return HttpResponse(resp.to_json(), content_type='application/json')
