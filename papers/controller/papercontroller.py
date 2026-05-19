import json

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from rest_framework.decorators import api_view

from papers.processor.paperprocessor import paper_generate_req_schema, paper_save_req_schema
from papers.service.paperservice import PaperService
from utility.decorator.auth import auth_required
from utility.utilityobj import ErrorResponse


@csrf_exempt
@api_view(['GET', 'POST', 'DELETE'])
@auth_required
def papers(request):
    if request.method == 'GET':
        return _fetch_papers(request)
    elif request.method == 'POST':
        return _save_paper(request)
    elif request.method == 'DELETE':
        return _delete_paper(request)


@csrf_exempt
@api_view(['POST'])
@auth_required
@transaction.atomic
def generate(request):
    return _generate_paper(request)


def _save_paper(request):
    scope = request.scope
    user_id = scope['user_id']
    try:
        obj = paper_save_req_schema.load(request.data)
    except Exception as e:
        return HttpResponse(ErrorResponse(status=400, message=str(e)).to_json(), status=400, content_type='application/json')
    service = PaperService(scope)
    resp = service.save_paper(obj, user_id)
    if isinstance(resp, ErrorResponse):
        return HttpResponse(resp.to_json(), status=resp.status, content_type='application/json')
    return HttpResponse(resp.to_json(), content_type='application/json')


def _fetch_papers(request):
    scope = request.scope
    user_id = scope['user_id']
    course_id = request.query_params.get('course_id')
    paper_id = request.query_params.get('paper_id')
    service = PaperService(scope)

    if paper_id:
        resp = service.fetch_paper(paper_id, user_id)
        if isinstance(resp, ErrorResponse):
            return HttpResponse(resp.to_json(), status=resp.status, content_type='application/json')
        return HttpResponse(resp.to_json(), content_type='application/json')

    resp_list = service.fetch_papers(user_id, course_id)
    return HttpResponse(json.dumps([p.to_dict() for p in resp_list]), content_type='application/json')


def _generate_paper(request):
    scope = request.scope
    user_id = scope['user_id']
    obj = paper_generate_req_schema.load(request.data)
    service = PaperService(scope)
    resp = service.generate_paper(obj, user_id)
    if isinstance(resp, ErrorResponse):
        return HttpResponse(resp.to_json(), status=resp.status, content_type='application/json')
    return HttpResponse(resp.to_json(), content_type='application/json')


def _delete_paper(request):
    scope = request.scope
    user_id = scope['user_id']
    paper_id = request.query_params.get('paper_id')
    if not paper_id:
        return HttpResponse(
            ErrorResponse(status=400, message='paper_id is required').to_json(),
            status=400, content_type='application/json'
        )
    service = PaperService(scope)
    resp = service.delete_paper(paper_id, user_id)
    if isinstance(resp, ErrorResponse):
        return HttpResponse(resp.to_json(), status=resp.status, content_type='application/json')
    return HttpResponse(resp.to_json(), content_type='application/json')
