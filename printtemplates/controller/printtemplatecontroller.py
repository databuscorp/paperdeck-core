import json

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from rest_framework.decorators import api_view

from printtemplates.processor.printtemplateprocessor import print_template_req_schema
from printtemplates.service.printtemplateservice import PrintTemplateService
from utility.decorator.auth import auth_required
from utility.utilityobj import ErrorResponse


@csrf_exempt
@api_view(['GET', 'POST', 'DELETE'])
@auth_required
@transaction.atomic
def print_templates(request):
    if request.method == 'GET':
        return _fetch(request)
    elif request.method == 'POST':
        return _post(request)
    elif request.method == 'DELETE':
        return _delete(request)


def _fetch(request):
    scope = request.scope
    org_id = scope.get('org_id')
    service = PrintTemplateService(scope)

    if request.query_params.get('active'):
        resp = service.fetch_active(org_id=org_id)
        if resp is None:
            return HttpResponse('null', content_type='application/json')
        return HttpResponse(resp.to_json(), content_type='application/json')

    resp_list = service.fetch_all(org_id=org_id)
    return HttpResponse(json.dumps([t.to_dict() for t in resp_list]), content_type='application/json')


def _post(request):
    scope = request.scope
    org_id = scope.get('org_id')
    user_id = scope['user_id']

    if not org_id:
        return HttpResponse(
            ErrorResponse(status=403, message='org_id required to save a print template').to_json(),
            status=403, content_type='application/json'
        )

    # A POST with only a template_id + active flag toggles the active template.
    set_active_id = request.query_params.get('set_active')
    service = PrintTemplateService(scope)
    if set_active_id:
        resp = service.set_active(set_active_id, org_id=org_id)
        if isinstance(resp, ErrorResponse):
            return HttpResponse(resp.to_json(), status=resp.status, content_type='application/json')
        return HttpResponse(resp.to_json(), content_type='application/json')

    obj = print_template_req_schema.load(request.data)
    resp = service.create_or_update(obj, user_id=user_id, org_id=org_id)
    if isinstance(resp, ErrorResponse):
        return HttpResponse(resp.to_json(), status=resp.status, content_type='application/json')
    return HttpResponse(resp.to_json(), content_type='application/json')


def _delete(request):
    scope = request.scope
    org_id = scope.get('org_id')
    template_id = request.query_params.get('template_id')

    if not org_id:
        return HttpResponse(
            ErrorResponse(status=403, message='org_id required to delete a print template').to_json(),
            status=403, content_type='application/json'
        )
    if not template_id:
        return HttpResponse(
            ErrorResponse(status=400, message='template_id is required').to_json(),
            status=400, content_type='application/json'
        )

    service = PrintTemplateService(scope)
    resp = service.delete(template_id, org_id=org_id)
    if isinstance(resp, ErrorResponse):
        return HttpResponse(resp.to_json(), status=resp.status, content_type='application/json')
    return HttpResponse(resp.to_json(), content_type='application/json')
