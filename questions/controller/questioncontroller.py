import json
import re

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


def _merge_rects(rects, gap, _fitz):
    """Union overlapping/nearby rectangles (within `gap` pts) into clusters."""
    rects = [_fitz.Rect(r) for r in rects]
    changed = True
    while changed:
        changed = False
        out = []
        while rects:
            r = rects.pop()
            merged = True
            while merged:
                merged = False
                rest = []
                for o in rects:
                    expanded = _fitz.Rect(r.x0 - gap, r.y0 - gap, r.x1 + gap, r.y1 + gap)
                    if expanded.intersects(o):
                        r |= o
                        merged = changed = True
                    else:
                        rest.append(o)
                rects = rest
            out.append(r)
        rects = out
    return rects


_FURNITURE_RES = [
    re.compile(p, re.I) for p in (
        r'^©\s*ucles',                      # copyright line
        r'^dc\s*\([^)]*\)',                 # printer code, e.g. DC (DE/CT) 343111/3
        r'this document (has|consists of)\b',
        r'^\[?\s*turn over\b',
        r'permission to reproduce',
        r'^blank page$',
    )
]


def _is_furniture(text: str) -> bool:
    """True for page furniture that should not be parsed as question content:
    margin notes, barcodes, copyright/printer codes, 'Turn over', etc."""
    s = re.sub(r'\s+', ' ', text).strip()
    if not s:
        return True
    low = s.lower()
    # "DO NOT WRITE IN THIS MARGIN" — usually a block of just that, repeated.
    if 'do not write in this margin' in low:
        if len(low.replace('do not write in this margin', '').strip(' ·,|')) < 15:
            return True
    if re.fullmatch(r'\*?\s*[\d ]{5,}\s*\*?', s):       # candidate barcode (digits/spaces)
        return True
    return any(rx.search(low) for rx in _FURNITURE_RES)


def _clean_block(text: str) -> str:
    """Collapse dotted/underscore answer-line leaders that pollute extracted text."""
    text = re.sub(r'[.…_]{4,}', ' ', text)            # solid leaders ........
    text = re.sub(r'(?:[._·]\s){4,}[._·]?', ' ', text)  # spaced leaders . . . .
    return text.strip()


def _column_split(boxes, W):
    """Return an x split position if the page is clearly two-column, else None.
    Conservative: requires an empty central gutter (no block crosses it) and
    enough content on both sides, so single-column pages are left untouched."""
    if len(boxes) < 6:
        return None
    mid_lo, mid_hi = W * 0.42, W * 0.58
    if any(b[0] < mid_lo and b[2] > mid_hi for b in boxes):   # a block spans the middle
        return None
    left = sum(1 for b in boxes if b[2] <= W * 0.52)
    right = sum(1 for b in boxes if b[0] >= W * 0.48)
    return W * 0.5 if left >= 3 and right >= 3 else None


def _is_label(text: str) -> bool:
    """A short, single-line caption/annotation (e.g. 'width', 'length', '250') that
    belongs to an adjacent figure rather than the question prose."""
    s = text.strip()
    return 0 < len(s) <= 25 and "\n" not in s


def _near_aligned(a, b, gap: float) -> bool:
    """True if rect b is close to rect a AND aligned with it — directly above/below
    (x-ranges overlap) or beside (y-ranges overlap) within `gap`, or hugging a
    corner within a tighter gap. Keeps figure-annotation absorption from grabbing
    far-off or unrelated text."""
    dx = max(b.x0 - a.x1, a.x0 - b.x1, 0.0)
    dy = max(b.y0 - a.y1, a.y0 - b.y1, 0.0)
    x_overlap = min(a.x1, b.x1) > max(a.x0, b.x0)
    y_overlap = min(a.y1, b.y1) > max(a.y0, b.y0)
    return ((x_overlap and dy <= gap) or (y_overlap and dx <= gap)
            or (dx <= gap * 0.6 and dy <= gap * 0.6))


def _extract_pdf_text_images(f):
    """Extract text + figures from a PDF, returning (text_with_markers, images).

    Unlike pypdf (text-only), this also captures FIGURES — including vector line
    drawings, which aren't embedded raster images and so are invisible to
    pypdf.page.images. Each page's graphics are clustered into figure regions,
    rendered to PNG, and a `[[IMG:key]]` marker is left in reading order so
    parse_paper can attach the figure to the question it belongs to (mirroring the
    .docx path). Falls back to text-only if PyMuPDF isn't installed."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        # A long-running server started before PyMuPDF was installed caches an
        # import-path listing that omits it. Invalidate the caches and retry so we
        # don't silently fall back to text-only (which drops all figures).
        import importlib
        importlib.invalidate_caches()
        try:
            import fitz  # noqa: F811
        except ImportError:
            import logging
            logging.getLogger(__name__).warning(
                "PyMuPDF (fitz) not importable — PDF figures will be skipped (text-only).")
            return _extract_pdf_text(f), {}
    import base64

    doc = fitz.open(stream=f.read(), filetype="pdf")
    parts = []
    images = {}
    fig_no = 0
    for pno in range(len(doc)):
        page = doc[pno]
        pr = page.rect
        W, H = pr.width, pr.height

        # Graphics: substantial rects (cluster into figures) vs thin lines
        # (dimension arrows / leaders that annotate a figure).
        substantial, thin = [], []
        for d in page.get_drawings():
            r = fitz.Rect(d["rect"])
            if r.width > W * 0.92 and r.height > H * 0.92:  # full-page frame
                continue
            (thin if (r.width < 3 or r.height < 3) else substantial).append(r)
        for img in page.get_images(full=True):
            try:
                for r in page.get_image_rects(img[0]):
                    substantial.append(fitz.Rect(r))
            except Exception:
                pass

        figs = [c for c in _merge_rects(substantial, 14, fitz)
                if c.width >= 40 and c.height >= 40 and c.get_area() >= 4000 and c.height <= H * 0.9]
        orig_figs = [fitz.Rect(c) for c in figs]   # before annotation absorption

        # Content text blocks (furniture + dotted answer lines already dropped).
        raw_blocks = []
        for b in page.get_text("blocks"):
            x0, y0, x1, y1, btext = b[0], b[1], b[2], b[3], (b[4] or "")
            btext = _clean_block(btext)
            if not btext or _is_furniture(btext):
                continue
            raw_blocks.append((fitz.Rect(x0, y0, x1, y1), btext))

        # Figures absorb their annotations: nearby short dimension arrows and short
        # labels (e.g. "width", "length", "250") grow into the figure so they render
        # as part of the crop instead of leaking out as floating text (which both
        # mislabels them and scrambles reading order). Grows iteratively within a gap.
        # Each thin line / label is absorbed at most once (tracked by index) so the
        # loop always terminates — a degenerate line on a figure edge would otherwise
        # never read back as "contained" and spin forever.
        used_thin = [False] * len(thin)
        used_lbl  = [False] * len(raw_blocks)
        for idx, fg in enumerate(figs):
            grew = True
            while grew:
                grew = False
                for j, r in enumerate(thin):                    # short arrows/leaders only
                    if not used_thin[j] and max(r.width, r.height) <= 90 and _near_aligned(fg, r, 24):
                        fg |= r; used_thin[j] = True; grew = True
                for j, (rect, t) in enumerate(raw_blocks):
                    if not used_lbl[j] and _is_label(t) and _near_aligned(fg, rect, 46):
                        fg |= rect; used_lbl[j] = True; grew = True
            figs[idx] = fg & pr

        # Keep a text block unless it was absorbed as a figure label, or it sat inside
        # the original figure region (a caption that renders inside the crop).
        text_blocks = [
            (r.x0, r.y0, r.x1, r.y1, t)
            for j, (r, t) in enumerate(raw_blocks)
            if not used_lbl[j] and not any(of.contains(r) for of in orig_figs)
        ]

        # Reading order: top→bottom, left→right — but read column-by-column when the
        # page is clearly two-column, so left/right text isn't interleaved per line.
        boxes = [b[:4] for b in text_blocks] + [(fg.x0, fg.y0, fg.x1, fg.y1) for fg in figs]
        split = _column_split(boxes, W)
        col = lambda x0: 1 if (split is not None and x0 >= split) else 0
        items = [(col(b[0]), round(b[1] / 6), b[0], "text", b[4]) for b in text_blocks]
        items += [(col(fg.x0), round(fg.y0 / 6), fg.x0, "fig", fg) for fg in figs]
        items.sort(key=lambda it: (it[0], it[1], it[2]))

        for it in items:
            kind, payload = it[3], it[4]
            if kind == "text":
                parts.append(payload)
            else:
                pad = 6
                clip = fitz.Rect(payload.x0 - pad, payload.y0 - pad, payload.x1 + pad, payload.y1 + pad) & pr
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), clip=clip, alpha=False)
                png = _autocrop_png(pix.tobytes("png"))
                key = f"p{pno}f{fig_no}"
                images[key] = "data:image/png;base64," + base64.b64encode(png).decode("ascii")
                parts.append(f" [[IMG:{key}]] ")
                fig_no += 1

    return "\n".join(parts), images


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

    # Same noise cleanup as the PDF path: collapse dotted answer-line leaders and
    # drop page-furniture lines (keep blanks as separators and any marker lines).
    text = re.sub(r'[.…_]{4,}', ' ', text)
    text = re.sub(r'(?:[._·]\s){4,}[._·]?', ' ', text)
    # Word text-box/shape EMU coordinates leak in as long digit runs / coordinate
    # pairs (e.g. 5153025203200, 2399515-75477). Real exam numbers are ≤4 digits,
    # so this is safe (won't touch years, marks, or 2024-2026 ranges).
    text = re.sub(r'-?\d{8,}', ' ', text)
    text = re.sub(r'\d{5,}-\d{3,}|\d{3,}-\d{5,}', ' ', text)
    text = '\n'.join(
        ln for ln in text.split('\n')
        if (not ln.strip()) or ('[[IMG:' in ln) or (not _is_furniture(ln))
    )
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
            text, images = _extract_pdf_text_images(f)
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
