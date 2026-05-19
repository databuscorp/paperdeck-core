import json

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from rest_framework.decorators import api_view

from subjects.processor.subjectprocessor import subject_req_schema
from subjects.service.subjectservice import SubjectService
from utility.decorator.auth import auth_required
from utility.utilityobj import ErrorResponse


@csrf_exempt
@api_view(['GET', 'POST', 'DELETE'])
@auth_required
@transaction.atomic
def subject(request):
    if request.method == 'GET':
        return _fetch_subjects(request)
    elif request.method == 'POST':
        return _post_subject(request)
    elif request.method == 'DELETE':
        return _delete_subject(request)


def _fetch_subjects(request):
    scope = request.scope
    service = SubjectService(scope)
    subject_id = request.query_params.get('subject_id')
    course_id = request.query_params.get('course_id')

    if subject_id:
        resp = service.fetch_subject(subject_id)
        if isinstance(resp, ErrorResponse):
            return HttpResponse(resp.to_json(), status=resp.status, content_type='application/json')
        return HttpResponse(resp.to_json(), content_type='application/json')

    if not course_id:
        return HttpResponse(
            ErrorResponse(status=400, message='course_id is required').to_json(),
            status=400, content_type='application/json'
        )
    resp_list = service.fetch_subjects(course_id)
    return HttpResponse(json.dumps([s.to_dict() for s in resp_list]), content_type='application/json')


def _post_subject(request):
    scope = request.scope
    obj = subject_req_schema.load(request.data)
    service = SubjectService(scope)
    resp = service.create_or_update_subject(obj)
    if isinstance(resp, ErrorResponse):
        return HttpResponse(resp.to_json(), status=resp.status, content_type='application/json')
    return HttpResponse(resp.to_json(), content_type='application/json')


def _delete_subject(request):
    scope = request.scope
    subject_id = request.query_params.get('subject_id')
    if not subject_id:
        return HttpResponse(
            ErrorResponse(status=400, message='subject_id is required').to_json(),
            status=400, content_type='application/json'
        )
    service = SubjectService(scope)
    resp = service.delete_subject(subject_id)
    if isinstance(resp, ErrorResponse):
        return HttpResponse(resp.to_json(), status=resp.status, content_type='application/json')
    return HttpResponse(resp.to_json(), content_type='application/json')


@csrf_exempt
@api_view(['POST', 'DELETE'])
@auth_required
@transaction.atomic
def syllabus(request):
    if request.method == 'POST':
        return _upload_syllabus(request)
    elif request.method == 'DELETE':
        return _delete_syllabus(request)


def _upload_syllabus(request):
    scope = request.scope
    subject_id = request.data.get('subject_id')
    if not subject_id:
        return HttpResponse(
            ErrorResponse(status=400, message='subject_id is required').to_json(),
            status=400, content_type='application/json'
        )

    file = request.FILES.get('file')
    if not file:
        return HttpResponse(
            ErrorResponse(status=400, message='file is required').to_json(),
            status=400, content_type='application/json'
        )

    size_bytes = file.size
    if size_bytes < 1024:
        file_size = f'{size_bytes} B'
    elif size_bytes < 1024 * 1024:
        file_size = f'{size_bytes // 1024} KB'
    else:
        file_size = f'{round(size_bytes / (1024 * 1024), 1)} MB'

    service = SubjectService(scope)
    resp = service.upload_syllabus(subject_id, file, file.name, file_size)
    if isinstance(resp, ErrorResponse):
        return HttpResponse(resp.to_json(), status=resp.status, content_type='application/json')
    return HttpResponse(resp.to_json(), content_type='application/json')


def _delete_syllabus(request):
    scope = request.scope
    syllabus_id = request.query_params.get('syllabus_id')
    if not syllabus_id:
        return HttpResponse(
            ErrorResponse(status=400, message='syllabus_id is required').to_json(),
            status=400, content_type='application/json'
        )
    service = SubjectService(scope)
    resp = service.delete_syllabus(syllabus_id)
    if isinstance(resp, ErrorResponse):
        return HttpResponse(resp.to_json(), status=resp.status, content_type='application/json')
    return HttpResponse(resp.to_json(), content_type='application/json')
