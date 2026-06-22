import json

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from rest_framework.decorators import api_view

from billing.processor.billingprocessor import charge_req_schema, buy_req_schema
from billing.service.billingservice import BillingService
from utility.decorator.auth import auth_required
from utility.utilityobj import ErrorResponse


def _require_org(request):
    org_id = request.scope.get('org_id')
    if not org_id:
        return None, HttpResponse(
            ErrorResponse(status=403, message='org_id required').to_json(),
            status=403, content_type='application/json',
        )
    return org_id, None


@csrf_exempt
@api_view(['GET'])
@auth_required
def status(request):
    org_id, err = _require_org(request)
    if err:
        return err
    data = BillingService(request.scope).status(org_id)
    return HttpResponse(json.dumps(data), content_type='application/json')


@csrf_exempt
@api_view(['POST'])
@auth_required
@transaction.atomic
def charge(request):
    org_id, err = _require_org(request)
    if err:
        return err
    obj = charge_req_schema.load(request.data)
    resp = BillingService(request.scope).charge(
        org_id,
        input_tokens=obj.input_tokens, output_tokens=obj.output_tokens,
        question_count=obj.question_count, with_answer_key=obj.with_answer_key,
        versions=obj.versions, title=obj.title,
    )
    if isinstance(resp, ErrorResponse):
        return HttpResponse(resp.to_json(), status=resp.status, content_type='application/json')
    return HttpResponse(json.dumps(resp), content_type='application/json')


@csrf_exempt
@api_view(['POST'])
@auth_required
@transaction.atomic
def buy_credits(request):
    org_id, err = _require_org(request)
    if err:
        return err
    obj = buy_req_schema.load(request.data)
    resp = BillingService(request.scope).buy(org_id, obj.pack, request.scope.get('user_id'))
    if isinstance(resp, ErrorResponse):
        return HttpResponse(resp.to_json(), status=resp.status, content_type='application/json')
    return HttpResponse(json.dumps(resp), content_type='application/json')
