import json

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from rest_framework.decorators import api_view

from courses.processor.courseprocessor import course_req_schema
from courses.service.courseservice import CourseService
from utility.decorator.auth import auth_required
from utility.utilityobj import ErrorResponse


@csrf_exempt
@api_view(['GET', 'POST', 'DELETE'])
@auth_required
@transaction.atomic
def courses(request):
    if request.method == 'GET':
        return _fetch_courses(request)
    elif request.method == 'POST':
        return _post_course(request)
    elif request.method == 'DELETE':
        return _delete_course(request)


def _fetch_courses(request):
    scope = request.scope
    user_id = scope['user_id']
    course_id = request.query_params.get('course_id')
    service = CourseService(scope)

    if course_id:
        resp = service.fetch_course(course_id, user_id)
        if isinstance(resp, ErrorResponse):
            return HttpResponse(resp.to_json(), status=resp.status, content_type='application/json')
        return HttpResponse(resp.to_json(), content_type='application/json')

    resp_list = service.fetch_courses(user_id)
    return HttpResponse(json.dumps([c.to_dict() for c in resp_list]), content_type='application/json')


def _post_course(request):
    scope = request.scope
    user_id = scope['user_id']
    obj = course_req_schema.load(request.data)
    service = CourseService(scope)
    resp = service.create_or_update_course(obj, user_id)
    if isinstance(resp, ErrorResponse):
        return HttpResponse(resp.to_json(), status=resp.status, content_type='application/json')
    return HttpResponse(resp.to_json(), content_type='application/json')


def _delete_course(request):
    scope = request.scope
    user_id = scope['user_id']
    course_id = request.query_params.get('course_id')
    if not course_id:
        return HttpResponse(
            ErrorResponse(status=400, message='course_id is required').to_json(),
            status=400, content_type='application/json'
        )
    service = CourseService(scope)
    resp = service.delete_course(course_id, user_id)
    if isinstance(resp, ErrorResponse):
        return HttpResponse(resp.to_json(), status=resp.status, content_type='application/json')
    return HttpResponse(resp.to_json(), content_type='application/json')
