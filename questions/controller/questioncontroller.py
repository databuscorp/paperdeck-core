import json

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from rest_framework.decorators import api_view

from questions.processor.questionprocessor import question_req_schema, question_generate_req_schema
from questions.service.questionservice import QuestionService
from papers.service.aigeneratorservice import AIGeneratorService
from utility.decorator.auth import auth_required
from utility.utilityobj import ErrorResponse


@csrf_exempt
@api_view(['GET', 'POST', 'DELETE'])
@auth_required
@transaction.atomic
def question(request):
    if request.method == 'GET':
        return _fetch(request)
    elif request.method == 'POST':
        return _post(request)
    elif request.method == 'DELETE':
        return _delete(request)


def _fetch(request):
    scope = request.scope
    org_id = scope.get('org_id')
    question_id = request.query_params.get('question_id')
    course_id = request.query_params.get('course_id')
    service = QuestionService(scope)
    if question_id:
        resp = service.fetch_one(question_id, scope['user_id'], org_id=org_id)
        if isinstance(resp, ErrorResponse):
            return HttpResponse(resp.to_json(), status=resp.status, content_type='application/json')
        return HttpResponse(resp.to_json(), content_type='application/json')
    resp_list = service.fetch_all(scope['user_id'], org_id=org_id, course_id=course_id)
    return HttpResponse(json.dumps([q.to_dict() for q in resp_list]), content_type='application/json')


def _post(request):
    scope = request.scope
    org_id = scope.get('org_id')
    obj = question_req_schema.load(request.data)
    service = QuestionService(scope)
    resp = service.create_or_update(obj, scope['user_id'], org_id=org_id)
    if isinstance(resp, ErrorResponse):
        return HttpResponse(resp.to_json(), status=resp.status, content_type='application/json')
    return HttpResponse(resp.to_json(), content_type='application/json')


def _delete(request):
    scope = request.scope
    org_id = scope.get('org_id')
    question_id = request.query_params.get('question_id')
    if not question_id:
        return HttpResponse(
            ErrorResponse(status=400, message='question_id is required').to_json(),
            status=400, content_type='application/json'
        )
    service = QuestionService(scope)
    resp = service.delete(question_id, scope['user_id'], org_id=org_id)
    if isinstance(resp, ErrorResponse):
        return HttpResponse(resp.to_json(), status=resp.status, content_type='application/json')
    return HttpResponse(resp.to_json(), content_type='application/json')


@csrf_exempt
@api_view(['POST'])
@auth_required
def generate_questions(request):
    try:
        obj = question_generate_req_schema.load(request.data)
    except Exception as e:
        return HttpResponse(
            ErrorResponse(status=400, message=str(e)).to_json(),
            status=400, content_type='application/json'
        )

    # Resolve exam/subject/topic display strings from DB when FK IDs are provided
    exam = obj.exam or ''
    subject = obj.subject or ''
    topic = obj.topic or ''

    if obj.course_id:
        try:
            from courses.models import Course
            course = Course.objects.select_related('authority').get(id=obj.course_id)
            if course.authority:
                exam = course.authority.name
        except Exception:
            pass

    if obj.subject_id:
        try:
            from subjects.models import Subject
            subj = Subject.objects.get(id=obj.subject_id)
            subject = subj.name
        except Exception:
            pass

    if obj.topic_id:
        try:
            from subjects.models import Topic
            t = Topic.objects.get(id=obj.topic_id)
            topic = t.name
        except Exception:
            pass

    try:
        generator = AIGeneratorService()
        questions = generator.generate_questions(
            exam=exam,
            subject=subject,
            topic=topic or '',
            q_type=obj.q_type,
            difficulty=obj.difficulty,
            bloom=obj.bloom,
            count=obj.count,
        )
        return HttpResponse(
            json.dumps({'questions': questions, 'usage': generator.last_usage}),
            content_type='application/json',
        )
    except Exception as e:
        return HttpResponse(
            ErrorResponse(status=500, message=f'Generation failed: {str(e)}').to_json(),
            status=500, content_type='application/json'
        )


class _MissingDependency(Exception):
    """Raised when an optional extraction dependency isn't installed, so the
    controller can return a clear message instead of a raw 500 ImportError."""


def _extract_pdf_text(f) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        raise _MissingDependency(
            "PDF support is not installed on the server (pypdf). "
            "Run 'pip install -r requirements.txt' on the backend, or upload a Word (.docx) file instead."
        )
    reader = PdfReader(f)
    return "\n".join((p.extract_text() or "") for p in reader.pages)


_RASTER_MIME = {'png': 'image/png', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'gif': 'image/gif'}


def _autocrop_png(png_bytes: bytes) -> bytes:
    """Trim the white border off a converted equation PNG. LibreOffice renders a
    WMF onto a full page canvas (e.g. 794x1123) with a tiny equation in it, which
    otherwise shows as a big white box. Best-effort: returns input on any failure."""
    try:
        import io
        from PIL import Image, ImageChops
        im = Image.open(io.BytesIO(png_bytes)).convert('RGB')
        bg = Image.new('RGB', im.size, (255, 255, 255))
        # Threshold out anti-alias halo so the bbox hugs the real ink.
        diff = ImageChops.difference(im, bg).convert('L').point(lambda p: 255 if p > 12 else 0)
        bbox = diff.getbbox()
        if not bbox:
            return png_bytes
        pad = 6
        l, t, r, b = bbox
        box = (max(0, l - pad), max(0, t - pad), min(im.width, r + pad), min(im.height, b + pad))
        out = io.BytesIO()
        im.crop(box).save(out, 'PNG')
        return out.getvalue()
    except Exception:
        return png_bytes


def _convert_wmf_batch(files: dict) -> dict:
    """Convert {name: wmf_bytes} → {name: png_bytes} via the external LibreOffice
    conversion VM (WMF_CONVERT_URL). Best-effort: returns {} if unconfigured or
    unreachable so import degrades gracefully (legacy equations just get skipped)."""
    import base64
    import json
    import os
    import urllib.request

    url = os.environ.get('WMF_CONVERT_URL', '')
    if not url or not files:
        return {}
    key = os.environ.get('WMF_CONVERT_KEY', '')
    timeout = int(os.environ.get('WMF_CONVERT_TIMEOUT', '180'))
    body = json.dumps({'files': {n: base64.b64encode(b).decode('ascii') for n, b in files.items()}}).encode()
    req = urllib.request.Request(url, data=body, method='POST',
                                 headers={'Content-Type': 'application/json',
                                          **({'X-API-Key': key} if key else {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        return {n: _autocrop_png(base64.b64decode(b64)) for n, b64 in (data.get('images') or {}).items()}
    except Exception:
        return {}


def _extract_docx_text(f):
    # A .docx is a zip of XML — extract text from word/document.xml with the
    # standard library so we don't depend on python-docx being installed.
    # Returns (text_with_markers, equation_object_count, images) where:
    #   - inline pictures leave a `[[IMG:rId]]` marker in reading order, and
    #   - images maps that rId -> a base64 data URL (raster formats only; legacy
    #     WMF/EMF equation images can't be shown in a browser so they're skipped).
    # Modern OMML math (<m:t>) survives as text; legacy Equation-Editor objects do not.
    import base64
    import zipfile
    import re
    from xml.sax.saxutils import unescape

    with zipfile.ZipFile(f) as z:
        xml = z.read('word/document.xml').decode('utf-8', 'ignore')
        # rId -> media path, from the document relationships.
        rels = {}
        try:
            rels_xml = z.read('word/_rels/document.xml.rels').decode('utf-8', 'ignore')
            for m in re.finditer(r'Id="([^"]+)"[^>]*Target="([^"]+)"', rels_xml):
                rels[m.group(1)] = m.group(2)
        except KeyError:
            pass

        eqn_objects = xml.count('OLEObject')
        # Drop a marker where each inline image/picture sits (DrawingML + VML).
        xml = re.sub(r'<a:blip[^>]*r:embed="([^"]+)"[^>]*>', r' [[IMG:\1]] ', xml)
        xml = re.sub(r'<v:imagedata[^>]*r:id="([^"]+)"[^>]*>', r' [[IMG:\1]] ', xml)
        xml = re.sub(r'<w:tab\b[^>]*/?>', '\t', xml)
        xml = re.sub(r'<w:br\b[^>]*/?>', '\n', xml)
        xml = xml.replace('</w:p>', '\n')      # paragraph breaks
        text = unescape(re.sub(r'<[^>]+>', '', xml))   # drop all tags, keep text content

        # Resolve markers to images. Raster (PNG/JPEG/GIF) embed directly; legacy
        # WMF/EMF equations are collected for batch conversion via the LibreOffice VM.
        images = {}
        kept = set()
        wmf_pending = {}   # rid -> wmf bytes
        for rid in set(re.findall(r'\[\[IMG:([^\]]+)\]\]', text)):
            target = rels.get(rid, '')
            ext = target.rsplit('.', 1)[-1].lower() if '.' in target else ''
            path = 'word/' + target.lstrip('/') if not target.startswith('word/') else target
            try:
                raw = z.read(path)
            except KeyError:
                continue
            mime = _RASTER_MIME.get(ext)
            if mime:
                images[rid] = f"data:{mime};base64,{base64.b64encode(raw).decode('ascii')}"
                kept.add(rid)
            elif ext in ('wmf', 'emf'):
                wmf_pending[rid] = raw

    wmf_total = len(wmf_pending)
    wmf_converted = 0
    if wmf_pending:
        converted = _convert_wmf_batch({rid: b for rid, b in wmf_pending.items()})
        for rid, png in converted.items():
            images[rid] = f"data:image/png;base64,{base64.b64encode(png).decode('ascii')}"
            kept.add(rid)
            wmf_converted += 1

    # Strip markers we can't display so they don't pollute the parsed text.
    text = re.sub(r'\[\[IMG:([^\]]+)\]\]',
                  lambda m: m.group(0) if m.group(1) in kept else '', text)
    return text, eqn_objects, images, wmf_total, wmf_converted


@csrf_exempt
@api_view(['POST'])
@auth_required
def import_paper(request):
    """Extract questions from an uploaded PDF/Word paper (text-based only)."""
    f = request.FILES.get('file')
    if not f:
        return HttpResponse(ErrorResponse(status=400, message='No file uploaded.').to_json(),
                            status=400, content_type='application/json')

    name = (f.name or '').lower()
    exam = request.data.get('exam', '') if hasattr(request, 'data') else ''
    eqn_objects = 0
    images = {}
    wmf_total = wmf_converted = 0
    try:
        if name.endswith('.pdf'):
            text = _extract_pdf_text(f)
        elif name.endswith('.docx'):
            text, eqn_objects, images, wmf_total, wmf_converted = _extract_docx_text(f)
        elif name.endswith('.doc'):
            return HttpResponse(ErrorResponse(status=400, message='Legacy .doc is not supported — please upload .docx or PDF.').to_json(),
                                status=400, content_type='application/json')
        else:
            return HttpResponse(ErrorResponse(status=400, message='Unsupported file type — upload a PDF or Word (.docx).').to_json(),
                                status=400, content_type='application/json')
    except _MissingDependency as e:
        return HttpResponse(ErrorResponse(status=503, message=str(e)).to_json(),
                            status=503, content_type='application/json')
    except Exception as e:
        return HttpResponse(ErrorResponse(status=400, message=f'Could not read the file: {str(e)}').to_json(),
                            status=400, content_type='application/json')

    if len((text or '').strip()) < 40:
        return HttpResponse(
            ErrorResponse(status=422, message='No readable text found — this looks like a scanned image. Upload a Word file or a text-based PDF.').to_json(),
            status=422, content_type='application/json')

    # Heavy legacy Equation-Editor use → most math is stored as images (WMF/OLE).
    # If the conversion VM turned them into PNGs we proceed; otherwise warn rather
    # than charge for a poor parse.
    words = len(text.split())
    if eqn_objects >= 20 and eqn_objects > words / 60 and wmf_converted == 0:
        return HttpResponse(
            ErrorResponse(status=422, message=(
                'This document’s equations are stored as images (legacy Equation Editor), '
                'so the math can’t be read as text. Re-create equations with Word’s built-in '
                'equation tool (Insert ▸ Equation), or upload a text-based version.'
            )).to_json(),
            status=422, content_type='application/json')

    try:
        generator = AIGeneratorService()
        result = generator.parse_paper(text, exam=exam, images=images)
        return HttpResponse(
            json.dumps({'questions': result.get('questions', []), 'meta': result.get('meta', {}),
                        'truncated': result.get('truncated', False), 'usage': generator.last_usage}),
            content_type='application/json',
        )
    except Exception as e:
        return HttpResponse(ErrorResponse(status=500, message=f'Import failed: {str(e)}').to_json(),
                            status=500, content_type='application/json')
