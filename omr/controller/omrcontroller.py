from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view

from omr.processor.omrprocessor import omr_sheet_req_schema
from omr.service.scanservice import OMRScanService
from omr.service.sheetservice import OMRSheetService, render_pdf
from utility.decorator.auth import auth_required
from utility.utilityobj import ErrorResponse

MAX_UPLOAD_BYTES = 25 * 1024 * 1024


def _err(status: int, message: str) -> HttpResponse:
    resp = ErrorResponse(status=status, message=message)
    return HttpResponse(resp.to_json(), status=status, content_type='application/json')


def _json(resp) -> HttpResponse:
    if isinstance(resp, ErrorResponse):
        return HttpResponse(resp.to_json(), status=resp.status,
                            content_type='application/json')
    return HttpResponse(resp.to_json(), content_type='application/json')


@csrf_exempt
@api_view(['GET', 'POST'])
@auth_required
def sheet(request):
    """POST → generate (or return the existing) OMR sheet for a paper.
       GET  ?paper_id= | ?sheet_id= → the sheet plus its layout JSON.

    POST additionally accepts ?download=1 to stream the PDF straight back
    instead of the JSON envelope (the JSON always carries `pdf_url`).
    """
    service = OMRSheetService(request.scope)

    if request.method == 'GET':
        return _json(service.fetch(
            paper_id=request.query_params.get('paper_id'),
            sheet_id=request.query_params.get('sheet_id'),
        ))

    try:
        req = omr_sheet_req_schema.load(request.data)
    except Exception as e:
        return _err(400, f'Invalid request: {e}')

    resp = service.create(req)
    if isinstance(resp, ErrorResponse):
        return _json(resp)

    if str(request.query_params.get('download', '')).lower() in ('1', 'true', 'yes'):
        return _pdf_response(resp.layout, resp.sheet_id, resp.sheet_version)
    return _json(resp)


@csrf_exempt
@api_view(['GET'])
@auth_required
def sheet_pdf(request):
    """GET ?sheet_id= | ?paper_id= → the printable A4 PDF."""
    service = OMRSheetService(request.scope)
    sheet_id = request.query_params.get('sheet_id')
    paper_id = request.query_params.get('paper_id')
    obj = (service.get_sheet(sheet_id) if sheet_id
           else service.get_sheet_for_paper(paper_id) if paper_id else None)
    if obj is None:
        return _err(404, 'OMR sheet not found')
    return _pdf_response(obj.layout, obj.id, obj.sheet_version)


def _pdf_response(layout, sheet_id, version) -> HttpResponse:
    try:
        pdf_bytes = render_pdf(layout)
    except Exception as e:
        return _err(500, f'OMR sheet render failed: {e}')
    resp = HttpResponse(pdf_bytes, content_type='application/pdf')
    resp['Content-Disposition'] = f'attachment; filename="omr_sheet_{sheet_id}_v{version}.pdf"'
    return resp


@csrf_exempt
@api_view(['POST'])
@auth_required
def scan(request):
    """POST multipart: file=<scan/photo/pdf>, sheet_id= or paper_id=

    Returns the parsed responses and an explicit `needs_review` list. Questions
    the scanner could not read cleanly come back with selected_option_index=null
    — it never guesses an answer on a student's exam.
    """
    upload = request.FILES.get('file') or request.FILES.get('image')
    if upload is None:
        return _err(400, 'a scanned sheet must be uploaded as multipart field "file"')
    if upload.size > MAX_UPLOAD_BYTES:
        return _err(413, 'uploaded file is larger than 25MB')

    sheet_id = request.data.get('sheet_id') or request.query_params.get('sheet_id')
    paper_id = request.data.get('paper_id') or request.query_params.get('paper_id')
    if not sheet_id and not paper_id:
        return _err(400, 'sheet_id or paper_id is required')

    data = upload.read()
    if not data:
        return _err(400, 'uploaded file is empty')

    service = OMRScanService(request.scope)
    resp = service.scan(data, content_type=getattr(upload, 'content_type', '') or '',
                        sheet_id=sheet_id, paper_id=paper_id)
    return _json(resp)
