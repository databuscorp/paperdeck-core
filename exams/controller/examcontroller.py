import json

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from rest_framework.decorators import api_view

from exams.processor.examprocessor import exam_authority_req_schema
from exams.service.examservice import ExamTemplateService, ExamAuthorityService
from utility.decorator.auth import auth_required
from utility.utilityobj import ErrorResponse


@csrf_exempt
@api_view(['GET'])
def exam_templates(request):
    service = ExamTemplateService()
    templates = service.fetch_all()
    return HttpResponse(
        json.dumps([t.to_dict() for t in templates]),
        content_type='application/json'
    )


@csrf_exempt
@api_view(['GET', 'POST', 'DELETE'])
@auth_required
@transaction.atomic
def exam_authorities(request):
    org_id = request.scope.get('org_id')

    if request.method == 'GET':
        service = ExamAuthorityService()
        authorities = service.fetch_all(org_id=org_id)
        return HttpResponse(
            json.dumps([a.to_dict() for a in authorities]),
            content_type='application/json'
        )

    elif request.method == 'POST':
        obj = exam_authority_req_schema.load(request.data)
        service = ExamAuthorityService()
        resp = service.create_or_update(obj, org_id=org_id)
        if isinstance(resp, ErrorResponse):
            return HttpResponse(resp.to_json(), status=resp.status, content_type='application/json')
        return HttpResponse(resp.to_json(), content_type='application/json')

    elif request.method == 'DELETE':
        authority_id = request.query_params.get('authority_id')
        if not authority_id:
            return HttpResponse(
                ErrorResponse(status=400, message='authority_id is required').to_json(),
                status=400, content_type='application/json'
            )
        service = ExamAuthorityService()
        resp = service.delete(authority_id, org_id=org_id)
        if isinstance(resp, ErrorResponse):
            return HttpResponse(resp.to_json(), status=resp.status, content_type='application/json')
        return HttpResponse(resp.to_json(), content_type='application/json')
