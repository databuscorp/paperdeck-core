import json

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view

from papers.processor.paperprocessor import paper_generate_req_schema, paper_save_req_schema
from papers.service.paperservice import PaperService
from utility.decorator.auth import auth_required
from utility.decorator.ratelimit import rate_limit
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


# NOTE: no @transaction.atomic here. Generation makes many minute-long LLM calls, and
# wrapping them in a transaction held a DB connection open for the entire run.
# A paper is the single most expensive thing this API does — a NEET paper is ~18 batched
# Claude calls. The rate limit sits BELOW @auth_required on purpose: decorators wrap
# bottom-up, so auth runs first and populates request.scope, which is what the limiter
# keys on. Above it, there is no org_id to key on and every caller would share one bucket.
@csrf_exempt
@api_view(['POST'])
@auth_required
@rate_limit('paper_generate', limit=5, window_seconds=60)      # burst
@rate_limit('paper_generate', limit=40, window_seconds=3600)   # sustained
def generate(request):
    return _generate_paper(request)


@csrf_exempt
@api_view(['POST'])
@auth_required
@rate_limit('paper_generate', limit=5, window_seconds=60)
@rate_limit('paper_generate', limit=40, window_seconds=3600)
def generate_async(request):
    """Enqueue paper generation; returns a job id to poll. Use this for full papers."""
    scope = request.scope
    try:
        obj = paper_generate_req_schema.load(request.data)
    except Exception as e:
        return HttpResponse(ErrorResponse(status=400, message=str(e)).to_json(),
                            status=400, content_type='application/json')
    service = PaperService(scope)
    resp = service.generate_paper_async(obj, scope['user_id'], org_id=scope.get('org_id'))
    if isinstance(resp, ErrorResponse):
        return HttpResponse(resp.to_json(), status=resp.status, content_type='application/json')
    return HttpResponse(resp.to_json(), content_type='application/json')


@csrf_exempt
@api_view(['GET'])
@auth_required
def generation_job(request):
    """Poll a generation job: status, percent, message, and the result once done."""
    from papers.models import GenerationJob
    from papers.service import jobservice
    from papers.service.paperservice import job_to_dict

    scope = request.scope
    job_id = request.GET.get('job_id')
    if not job_id:
        return HttpResponse(ErrorResponse(status=400, message='job_id is required').to_json(),
                            status=400, content_type='application/json')

    # Surface jobs whose worker died (restart/redeploy/scale-in) as FAILED rather than
    # letting the client poll a RUNNING job forever. No-op in the normal case.
    jobservice.reap_stale_jobs()

    qs = GenerationJob.objects.filter(id=job_id)
    # Scope to the caller's org, or to the caller, so jobs aren't readable across tenants.
    org_id = scope.get('org_id')
    qs = qs.filter(org_id=org_id) if org_id else qs.filter(owner_id=scope['user_id'])

    job = qs.first()
    if not job:
        return HttpResponse(ErrorResponse(status=404, message='Job not found').to_json(),
                            status=404, content_type='application/json')
    return HttpResponse(json.dumps(job_to_dict(job)), content_type='application/json')


def _save_paper(request):
    scope = request.scope
    user_id = scope['user_id']
    org_id = scope.get('org_id')
    try:
        obj = paper_save_req_schema.load(request.data)
    except Exception as e:
        return HttpResponse(ErrorResponse(status=400, message=str(e)).to_json(), status=400, content_type='application/json')
    service = PaperService(scope)
    resp = service.save_paper(obj, user_id, org_id=org_id)
    if isinstance(resp, ErrorResponse):
        return HttpResponse(resp.to_json(), status=resp.status, content_type='application/json')
    return HttpResponse(resp.to_json(), content_type='application/json')


def _fetch_papers(request):
    scope = request.scope
    user_id = scope['user_id']
    org_id = scope.get('org_id')
    course_id = request.query_params.get('course_id')
    paper_id = request.query_params.get('paper_id')
    service = PaperService(scope)

    if paper_id:
        resp = service.fetch_paper(paper_id, user_id, org_id=org_id)
        if isinstance(resp, ErrorResponse):
            return HttpResponse(resp.to_json(), status=resp.status, content_type='application/json')
        return HttpResponse(resp.to_json(), content_type='application/json')

    resp_list = service.fetch_papers(user_id, course_id, org_id=org_id)
    return HttpResponse(json.dumps([p.to_dict() for p in resp_list]), content_type='application/json')


def _generate_paper(request):
    scope = request.scope
    user_id = scope['user_id']
    org_id = scope.get('org_id')
    obj = paper_generate_req_schema.load(request.data)
    service = PaperService(scope)
    resp = service.generate_paper(obj, user_id, org_id=org_id)
    if isinstance(resp, ErrorResponse):
        return HttpResponse(resp.to_json(), status=resp.status, content_type='application/json')
    return HttpResponse(resp.to_json(), content_type='application/json')


def _delete_paper(request):
    scope = request.scope
    user_id = scope['user_id']
    org_id = scope.get('org_id')
    paper_id = request.query_params.get('paper_id')
    if not paper_id:
        return HttpResponse(
            ErrorResponse(status=400, message='paper_id is required').to_json(),
            status=400, content_type='application/json'
        )
    service = PaperService(scope)
    resp = service.delete_paper(paper_id, user_id, org_id=org_id)
    if isinstance(resp, ErrorResponse):
        return HttpResponse(resp.to_json(), status=resp.status, content_type='application/json')
    return HttpResponse(resp.to_json(), content_type='application/json')
