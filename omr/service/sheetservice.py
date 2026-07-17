"""
OMR sheet generation: layout dict → printable A4 PDF (reportlab), plus the
OMRSheet persistence around it.

The renderer is a *pure consumer* of the layout dict. It never computes a bubble
position of its own — it reads the normalized centre out of the layout and
converts it to reportlab's bottom-left-origin points. That is what guarantees
the scanner and the printer agree.
"""
from __future__ import annotations

import io
from typing import Any, Dict, Optional

from django.core.files.base import ContentFile
from django.db import transaction

from reportlab.lib.colors import black, white, HexColor
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from omr.models import OMRSheet
from omr.service import geometry as geo
from utility.utilityobj import ErrorResponse

GREY = HexColor('#6b7280')
RULE = HexColor('#9ca3af')


def _y(y_top: float) -> float:
    """top-left-origin pt → reportlab bottom-left-origin pt."""
    return geo.PAGE_H - y_top


def _px(nx: float) -> float:
    return nx * geo.PAGE_W


def _py(ny: float) -> float:
    return _y(ny * geo.PAGE_H)


def render_pdf(layout: Dict[str, Any]) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.setTitle(layout.get('title') or 'OMR Answer Sheet')

    npages = layout['num_pages']
    for page in layout['pages']:
        _draw_page(c, layout, page)
        if page['page_index'] < npages:
            c.showPage()
    c.showPage()
    c.save()
    return buf.getvalue()


def _draw_page(c: canvas.Canvas, layout: Dict[str, Any], page: Dict[str, Any]) -> None:
    p = page['page_index']
    labels = layout['option_labels']
    nopts = layout['options_per_question']

    _draw_fiducials(c, layout, page)
    _draw_code_track(c, layout, page)

    # ── header ────────────────────────────────────────────────────────────────
    title = (layout.get('title') or 'OMR Answer Sheet')[:70]
    c.setFont('Helvetica-Bold', 13)
    c.drawCentredString(geo.PAGE_W / 2, _y(46), title)

    meta = layout.get('meta') or {}
    bits = [f"Sheet {layout['sheet_short_id']:05d}",
            f"v{layout['sheet_version']}",
            f"Page {p}/{layout['num_pages']}",
            f"{layout['num_questions']} questions x {nopts} options"]
    if meta.get('paper_id'):
        bits.insert(0, f"Paper #{meta['paper_id']}")
    c.setFont('Helvetica', 8)
    c.setFillColor(GREY)
    c.drawCentredString(geo.PAGE_W / 2, _y(60), '   |   '.join(bits))
    c.setFillColor(black)

    if p == 1:
        _draw_identity_block(c, layout)
        _draw_roll_grid(c, layout, page)
        _draw_instructions(c, layout)

    # ── question grid ─────────────────────────────────────────────────────────
    r_pt = layout['bubble_radius'] * geo.PAGE_W
    questions = page['questions']
    if questions:
        # A/B/C/D header above the first row of every column
        seen_cols = set()
        for q in questions:
            if q['column'] in seen_cols or q['row'] != 0:
                continue
            seen_cols.add(q['column'])
            c.setFont('Helvetica-Bold', 7)
            c.setFillColor(GREY)
            for o in q['options']:
                c.drawCentredString(_px(o['x']),
                                    _py(q['options'][0]['y']) + geo.COL_HEADER_DY - 2,
                                    labels[o['option_index']])
            c.setFillColor(black)

    for q in questions:
        y = _py(q['options'][0]['y'])
        c.setFont('Helvetica', 8)
        c.setFillColor(GREY)
        c.drawRightString(_px(q['label_right_x']), y - 3, str(q['question_number']))
        c.setFillColor(black)
        c.setStrokeColor(RULE)
        c.setLineWidth(0.7)
        for o in q['options']:
            c.circle(_px(o['x']), _py(o['y']), r_pt, stroke=1, fill=0)
        c.setStrokeColor(black)


def _draw_fiducials(c: canvas.Canvas, layout: Dict[str, Any], page: Dict[str, Any]) -> None:
    fw = layout['pages'][0]['fiducial_size']['w'] * geo.PAGE_W
    fh = layout['pages'][0]['fiducial_size']['h'] * geo.PAGE_H
    c.setFillColor(black)
    for f in page['fiducials']:
        cx, cy = _px(f['x']), _py(f['y'])
        c.rect(cx - fw / 2, cy - fh / 2, fw, fh, stroke=0, fill=1)


def _draw_code_track(c: canvas.Canvas, layout: Dict[str, Any], page: Dict[str, Any]) -> None:
    """Binary track: solid square = 1, hollow square = 0. Read back by the same
    darkness sampler the bubbles use (see geometry.py for why not a QR code)."""
    mw = page['code_module_size']['w'] * geo.PAGE_W
    mh = page['code_module_size']['h'] * geo.PAGE_H
    for m in page['code_track']:
        cx, cy = _px(m['x']), _py(m['y'])
        if m['bit']:
            c.setFillColor(black)
            c.rect(cx - mw / 2, cy - mh / 2, mw, mh, stroke=0, fill=1)
        else:
            c.setStrokeColor(RULE)
            c.setLineWidth(0.5)
            c.setFillColor(white)
            c.rect(cx - mw / 2, cy - mh / 2, mw, mh, stroke=1, fill=1)
    c.setFillColor(GREY)
    c.setFont('Helvetica', 6)
    track_right = max(_px(m['x']) for m in page['code_track'])
    c.drawString(track_right + 12, _y(geo.PAGE_H - geo.CODE_Y_FROM_BOTTOM) - 2,
                 f"S{layout['sheet_short_id']:05d}-P{page['page_index']}")
    c.setFillColor(black)
    c.setStrokeColor(black)


def _draw_identity_block(c: canvas.Canvas, layout: Dict[str, Any]) -> None:
    c.setStrokeColor(RULE)
    c.setLineWidth(0.6)
    c.setFont('Helvetica', 8)
    c.setFillColor(GREY)
    rows = [('STUDENT NAME', 45.0, 300.0), ('ROLL NO', 355.0, 100.0),
            ('DATE', 470.0, 80.0)]
    for label, x, w in rows:
        c.drawString(x, _y(80), label)
        c.line(x, _y(98), x + w, _y(98))
    c.setFillColor(black)
    c.setStrokeColor(black)


def _draw_roll_grid(c: canvas.Canvas, layout: Dict[str, Any], page: Dict[str, Any]) -> None:
    roll = page['roll']
    if not roll:
        return
    r_pt = layout['bubble_radius'] * geo.PAGE_W

    c.setFont('Helvetica-Bold', 8)
    c.drawString(geo.ROLL_X0 - 22, _y(geo.ROLL_HEADER_Y - 8), 'ROLL NUMBER')

    c.setFont('Helvetica', 7)
    c.setFillColor(GREY)
    for d in range(layout['roll_digits']):
        cx = geo.ROLL_X0 + d * geo.ROLL_COL_PITCH
        c.drawCentredString(cx, _y(geo.ROLL_HEADER_Y + 4), str(d + 1))
    for v in range(10):
        cy = geo.ROLL_Y0 + v * geo.ROLL_ROW_PITCH
        c.drawRightString(geo.ROLL_X0 - 12, _y(cy) - 2.5, str(v))
    c.setFillColor(black)

    c.setStrokeColor(RULE)
    c.setLineWidth(0.7)
    for b in roll:
        c.circle(_px(b['x']), _py(b['y']), r_pt, stroke=1, fill=0)
    c.setStrokeColor(black)


def _draw_instructions(c: canvas.Canvas, layout: Dict[str, Any]) -> None:
    x = 230.0
    y = geo.ROLL_HEADER_Y
    c.setFont('Helvetica-Bold', 8)
    c.drawString(x, _y(y - 8), 'INSTRUCTIONS')
    c.setFont('Helvetica', 7.5)
    c.setFillColor(GREY)
    # Each entry must fit on ONE line at 7.5pt within the ~310pt column — there
    # is no wrapping here, and a wrapped line would print a stray bullet.
    lines = [
        'Use a BLUE or BLACK ball-point pen only.',
        'Darken the bubble COMPLETELY. Do not tick or cross.',
        'Mark ONE bubble per question. Two marks = no marks.',
        'Do not fold, staple or write in the margins.',
        'Keep the four black corner squares clean and unmarked.',
    ]
    for i, ln in enumerate(lines):
        c.drawString(x, _y(y + 10 + i * 11), u'•  ' + ln)

    # a filled-vs-empty example so a student can see what "darkened" means
    ey = y + 10 + len(lines) * 11 + 14
    c.setFillColor(black)
    c.setFont('Helvetica', 7.5)
    c.drawString(x, _y(ey), 'Correct:')
    c.circle(x + 48, _y(ey) + 2.5, 5, stroke=0, fill=1)
    c.drawString(x + 62, _y(ey), 'Wrong:')
    c.setStrokeColor(RULE)
    c.circle(x + 104, _y(ey) + 2.5, 5, stroke=1, fill=0)
    c.setStrokeColor(black)
    c.setLineWidth(0.8)
    c.line(x + 100, _y(ey) - 1, x + 108, _y(ey) + 6)
    c.setFillColor(black)


# ── service ───────────────────────────────────────────────────────────────────

class OMRSheetService:
    def __init__(self, scope: Dict[str, Any]):
        self.scope = scope or {}
        self.org_id = self.scope.get('org_id')

    def _paper(self, paper_id):
        from papers.models import Paper
        qs = Paper.objects.filter(id=paper_id)
        if self.org_id:
            qs = qs.filter(org_id=self.org_id)
        else:
            qs = qs.filter(owner_id=self.scope.get('user_id'))
        return qs.first()

    @transaction.atomic
    def create(self, req) -> Any:
        paper = self._paper(req.paper_id)
        if paper is None:
            return ErrorResponse(status=404, message='Paper not found')

        num_questions = req.num_questions or _count_paper_questions(paper)
        if not num_questions:
            return ErrorResponse(
                status=400,
                message='num_questions is required (the paper has no questions yet)')

        existing = OMRSheet.objects.filter(paper=paper).order_by('-sheet_version').first()
        if existing and not req.regenerate:
            return build_sheet_response(existing)

        version = (existing.sheet_version + 1) if existing else 1

        sheet = OMRSheet.objects.create(
            org_id=self.org_id,
            paper=paper,
            num_questions=num_questions,
            options_per_question=req.options_per_question or 4,
            roll_digits=req.roll_digits or 6,
            sheet_version=version,
            layout={},
        )
        # The short id is the row id, so the layout can only be built once the
        # row exists — hence create-then-update inside one transaction.
        try:
            layout = geo.build_layout(
                num_questions=sheet.num_questions,
                options_per_question=sheet.options_per_question,
                roll_digits=sheet.roll_digits,
                sheet_short_id=sheet.short_id,
                sheet_version=sheet.sheet_version,
                title=paper.title,
                meta={
                    'paper_id': paper.id,
                    'exam_type': paper.exam_type,
                    'total_marks': paper.total_marks,
                    'duration_minutes': paper.duration_minutes,
                },
            )
        except ValueError as e:
            return ErrorResponse(status=400, message=str(e))

        sheet.layout = layout
        pdf_bytes = render_pdf(layout)
        sheet.pdf.save(f'omr_sheet_{sheet.id}_v{version}.pdf',
                       ContentFile(pdf_bytes), save=False)
        sheet.save(update_fields=['layout', 'pdf'])
        return build_sheet_response(sheet)

    def fetch(self, paper_id=None, sheet_id=None) -> Any:
        qs = OMRSheet.objects.all()
        if self.org_id:
            qs = qs.filter(org_id=self.org_id)
        if sheet_id:
            sheet = qs.filter(id=sheet_id).first()
        elif paper_id:
            sheet = qs.filter(paper_id=paper_id).order_by('-sheet_version').first()
        else:
            return ErrorResponse(status=400, message='paper_id or sheet_id is required')
        if sheet is None:
            return ErrorResponse(status=404, message='OMR sheet not found')
        return build_sheet_response(sheet)

    def get_sheet(self, sheet_id) -> Optional[OMRSheet]:
        qs = OMRSheet.objects.filter(id=sheet_id)
        if self.org_id:
            qs = qs.filter(org_id=self.org_id)
        return qs.first()

    def get_sheet_for_paper(self, paper_id) -> Optional[OMRSheet]:
        qs = OMRSheet.objects.filter(paper_id=paper_id)
        if self.org_id:
            qs = qs.filter(org_id=self.org_id)
        return qs.order_by('-sheet_version').first()


def _count_paper_questions(paper) -> int:
    from papers.models import PaperQuestion
    return PaperQuestion.objects.filter(section__paper=paper).count()


def build_sheet_response(sheet: OMRSheet):
    from omr.processor.omrprocessor import OMRSheetResponse
    return OMRSheetResponse(
        sheet_id=sheet.id,
        paper_id=sheet.paper_id,
        sheet_version=sheet.sheet_version,
        sheet_short_id=sheet.short_id,
        num_questions=sheet.num_questions,
        options_per_question=sheet.options_per_question,
        roll_digits=sheet.roll_digits,
        num_pages=(sheet.layout or {}).get('num_pages', 1),
        pdf_url=sheet.pdf.url if sheet.pdf else None,
        layout=sheet.layout,
        created_at=sheet.created_at.isoformat() if sheet.created_at else None,
    )
