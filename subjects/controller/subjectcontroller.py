import json

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from rest_framework.decorators import api_view

from subjects.processor.subjectprocessor import subject_req_schema, topic_req_schema, chapter_req_schema
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
    org_id = scope.get('org_id')
    service = SubjectService(scope)
    subject_id = request.query_params.get('subject_id')
    course_id = request.query_params.get('course_id')

    if subject_id:
        resp = service.fetch_subject(subject_id, org_id=org_id)
        if isinstance(resp, ErrorResponse):
            return HttpResponse(resp.to_json(), status=resp.status, content_type='application/json')
        return HttpResponse(resp.to_json(), content_type='application/json')

    if not course_id:
        return HttpResponse(
            ErrorResponse(status=400, message='course_id is required').to_json(),
            status=400, content_type='application/json'
        )
    resp_list = service.fetch_subjects(course_id, org_id=org_id)
    return HttpResponse(json.dumps([s.to_dict() for s in resp_list]), content_type='application/json')


def _post_subject(request):
    scope = request.scope
    user_id = scope['user_id']
    org_id = scope.get('org_id')
    obj = subject_req_schema.load(request.data)
    service = SubjectService(scope)
    resp = service.create_or_update_subject(obj, user_id=user_id, org_id=org_id)
    if isinstance(resp, ErrorResponse):
        return HttpResponse(resp.to_json(), status=resp.status, content_type='application/json')
    return HttpResponse(resp.to_json(), content_type='application/json')


def _delete_subject(request):
    scope = request.scope
    user_id = scope['user_id']
    org_id = scope.get('org_id')
    subject_id = request.query_params.get('subject_id')
    if not subject_id:
        return HttpResponse(
            ErrorResponse(status=400, message='subject_id is required').to_json(),
            status=400, content_type='application/json'
        )
    service = SubjectService(scope)
    resp = service.delete_subject(subject_id, user_id=user_id, org_id=org_id)
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
    org_id = scope.get('org_id')
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
    resp = service.upload_syllabus(subject_id, file, file.name, file_size, org_id=org_id)
    if isinstance(resp, ErrorResponse):
        return HttpResponse(resp.to_json(), status=resp.status, content_type='application/json')
    return HttpResponse(resp.to_json(), content_type='application/json')


def _delete_syllabus(request):
    scope = request.scope
    org_id = scope.get('org_id')
    syllabus_id = request.query_params.get('syllabus_id')
    if not syllabus_id:
        return HttpResponse(
            ErrorResponse(status=400, message='syllabus_id is required').to_json(),
            status=400, content_type='application/json'
        )
    service = SubjectService(scope)
    resp = service.delete_syllabus(syllabus_id, org_id=org_id)
    if isinstance(resp, ErrorResponse):
        return HttpResponse(resp.to_json(), status=resp.status, content_type='application/json')
    return HttpResponse(resp.to_json(), content_type='application/json')


@csrf_exempt
@api_view(['GET', 'POST', 'DELETE'])
@auth_required
@transaction.atomic
def topic(request):
    if request.method == 'GET':
        return _fetch_topics(request)
    elif request.method == 'POST':
        return _post_topic(request)
    elif request.method == 'DELETE':
        return _delete_topic(request)


def _fetch_topics(request):
    scope = request.scope
    org_id = scope.get('org_id')
    subject_id = request.query_params.get('subject_id')
    if not subject_id:
        return HttpResponse(
            ErrorResponse(status=400, message='subject_id is required').to_json(),
            status=400, content_type='application/json'
        )
    service = SubjectService(scope)
    topics = service.fetch_topics(subject_id, org_id=org_id)
    return HttpResponse(json.dumps([t.to_dict() for t in topics]), content_type='application/json')


def _post_topic(request):
    scope = request.scope
    org_id = scope.get('org_id')
    obj = topic_req_schema.load(request.data)
    service = SubjectService(scope)
    resp = service.create_or_update_topic(obj, org_id=org_id)
    if isinstance(resp, ErrorResponse):
        return HttpResponse(resp.to_json(), status=resp.status, content_type='application/json')
    return HttpResponse(resp.to_json(), content_type='application/json')


def _delete_topic(request):
    scope = request.scope
    org_id = scope.get('org_id')
    topic_id = request.query_params.get('topic_id')
    if not topic_id:
        return HttpResponse(
            ErrorResponse(status=400, message='topic_id is required').to_json(),
            status=400, content_type='application/json'
        )
    service = SubjectService(scope)
    resp = service.delete_topic(topic_id, org_id=org_id)
    if isinstance(resp, ErrorResponse):
        return HttpResponse(resp.to_json(), status=resp.status, content_type='application/json')
    return HttpResponse(resp.to_json(), content_type='application/json')


@csrf_exempt
@api_view(['POST', 'DELETE'])
@auth_required
@transaction.atomic
def chapter(request):
    if request.method == 'POST':
        return _post_chapter(request)
    elif request.method == 'DELETE':
        return _delete_chapter(request)


def _post_chapter(request):
    scope = request.scope
    org_id = scope.get('org_id')
    obj = chapter_req_schema.load(request.data)
    service = SubjectService(scope)
    resp = service.create_or_update_chapter(obj, org_id=org_id)
    if isinstance(resp, ErrorResponse):
        return HttpResponse(resp.to_json(), status=resp.status, content_type='application/json')
    return HttpResponse(resp.to_json(), content_type='application/json')


def _delete_chapter(request):
    scope = request.scope
    org_id = scope.get('org_id')
    chapter_id = request.query_params.get('chapter_id')
    if not chapter_id:
        return HttpResponse(
            ErrorResponse(status=400, message='chapter_id is required').to_json(),
            status=400, content_type='application/json'
        )
    service = SubjectService(scope)
    resp = service.delete_chapter(chapter_id, org_id=org_id)
    if isinstance(resp, ErrorResponse):
        return HttpResponse(resp.to_json(), status=resp.status, content_type='application/json')
    return HttpResponse(resp.to_json(), content_type='application/json')
