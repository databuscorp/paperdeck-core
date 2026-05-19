import json

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view

from exams.service.examservice import ExamTemplateService


@csrf_exempt
@api_view(['GET'])
def exam_templates(request):
    service = ExamTemplateService()
    templates = service.fetch_all()
    return HttpResponse(
        json.dumps([t.to_dict() for t in templates]),
        content_type='application/json'
    )
