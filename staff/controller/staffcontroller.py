import json

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from rest_framework.decorators import api_view

from staff.processor.staffprocessor import staff_req_schema
from staff.service.staffservice import StaffService
from utility.decorator.auth import auth_required
from utility.utilityobj import ErrorResponse


@csrf_exempt
@api_view(['GET', 'POST', 'DELETE'])
@auth_required
@transaction.atomic
def staff(request):
    if request.method == 'GET':
        return _fetch_staff(request)
    elif request.method == 'POST':
        return _post_staff(request)
    elif request.method == 'DELETE':
        return _delete_staff(request)


def _fetch_staff(request):
    scope = request.scope
    org_id = scope.get('org_id')
    staff_id = request.query_params.get('staff_id')
    course_id = request.query_params.get('course_id')
    service = StaffService(scope)
    if staff_id:
        resp = service.fetch_one_staff(staff_id, org_id=org_id)
        if isinstance(resp, ErrorResponse):
            return HttpResponse(resp.to_json(), status=resp.status, content_type='application/json')
        return HttpResponse(resp.to_json(), content_type='application/json')
    if course_id:
        resp_list = service.fetch_staff(course_id, org_id=org_id)
    else:
        resp_list = service.fetch_all_staff(scope['user_id'], org_id=org_id)
    return HttpResponse(json.dumps([s.to_dict() for s in resp_list]), content_type='application/json')


def _post_staff(request):
    scope = request.scope
    if scope.get('role') != 1:
        return HttpResponse(
            ErrorResponse(status=403, message='Admin access required').to_json(),
            status=403, content_type='application/json'
        )
    org_id = scope.get('org_id')
    obj = staff_req_schema.load(request.data)
    service = StaffService(scope)
    resp = service.create_or_update_staff(obj, org_id=org_id)
    if isinstance(resp, ErrorResponse):
        return HttpResponse(resp.to_json(), status=resp.status, content_type='application/json')
    return HttpResponse(resp.to_json(), content_type='application/json')


def _delete_staff(request):
    scope = request.scope
    if scope.get('role') != 1:
        return HttpResponse(
            ErrorResponse(status=403, message='Admin access required').to_json(),
            status=403, content_type='application/json'
        )
    org_id = scope.get('org_id')
    staff_id = request.query_params.get('staff_id')
    if not staff_id:
        return HttpResponse(
            ErrorResponse(status=400, message='staff_id is required').to_json(),
            status=400, content_type='application/json'
        )
    service = StaffService(scope)
    resp = service.delete_staff(staff_id, org_id=org_id)
    if isinstance(resp, ErrorResponse):
        return HttpResponse(resp.to_json(), status=resp.status, content_type='application/json')
    return HttpResponse(resp.to_json(), content_type='application/json')
