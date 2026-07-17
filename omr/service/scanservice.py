"""
OMR scanning: a photo/scan of a filled sheet → structured responses.

Pipeline
--------
  1. DECODE      bytes → page image(s). PDFs are rasterized at 200dpi (pymupdf);
                 JPEG/PNG go through Pillow with EXIF rotation applied.
  2. FIDUCIALS   find the four solid corner squares (imageops.find_fiducials).
                 If we can't, we FAIL the scan — we never "read it anyway".
  3. WARP        solve a homography from those four points to their normalized
                 positions in the layout, and perspective-correct the page into
                 a canonical 1240x1754 raster. A photo taken at an angle is now
                 flat, so a bubble centre from the layout lands on the bubble.
  4. ORIENT      read the printed code track. Its 4-bit checksum tells us whether
                 the corner ordering was right; if not we re-warp with the
                 corners rotated 180 degrees and read again. The code track also
                 tells us WHICH page of the sheet this image is.
  5. CALIBRATE   estimate this sheet's own ink and paper levels:
                    ink   = median grey inside the four fiducial squares
                            (guaranteed solid printer ink, on THIS sheet, under
                             THIS lighting)
                    paper = 92nd percentile of the page
                 Every darkness score below is expressed as a fraction of that
                 ink-to-paper range, so nothing in this file compares against a
                 hardcoded grey level. A dim phone photo and a bright flatbed
                 scan land on the same scale.
  6. SAMPLE      mean intensity over a disc at each bubble centre (inset to 70%
                 of the bubble radius so the printed outline is excluded).
  7. DECIDE      per question, with explicit ambiguity reporting. See `_decide`.

Correctness stance
------------------
A wrongly-read bubble is a wrongly-graded student, so the scanner is built to
refuse rather than guess. `selected_option_index` is non-null ONLY for status
`ok`. Everything else (multiple marks, blank, faint/uncertain) returns null and
lands in `needs_review`. `best_guess_option_index` exists purely so the review UI
can pre-highlight a candidate for a human — it must never be auto-graded.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from omr.models import OMRScan, OMRSheet
from omr.service import geometry as geo
from omr.service.imageops import (
    ScanError, disc_mean, find_fiducials, homography, load_pages, rect_median,
    to_gray, warp,
)
from utility.utilityobj import ErrorResponse

# Canonical raster: A4 at ~150dpi. A bubble is ~10px across here, so a sampling
# disc holds ~150 pixels — plenty for a stable mean, and cheap to warp.
CANON_W = 1240
CANON_H = int(round(CANON_W * geo.PAGE_H / geo.PAGE_W))   # 1754

# Thresholds on the NORMALIZED darkness scale (0 = paper, 1 = as dark as this
# sheet's own printer ink). These are not grey levels; they are fractions of the
# sheet's measured ink/paper contrast, which is what makes them portable across
# a washed-out photo and a high-contrast scan.
MARK_HI = 0.60      # at or above → a deliberate mark
MARK_LO = 0.30      # below       → paper
CODE_BIT_THRESHOLD = 0.45

# Minimum ink/paper separation (grey levels out of 255) before we trust anything.
MIN_CONTRAST = 25.0

BUBBLE_SAMPLE_INSET = 0.70   # sample the inner 70% of the bubble (skip the outline)
CODE_SAMPLE_INSET = 0.60

STATUS_OK             = 'ok'
STATUS_MULTIPLE       = 'multiple_marks'
STATUS_BLANK          = 'blank'
STATUS_LOW_CONFIDENCE = 'low_confidence'


# ── calibration ───────────────────────────────────────────────────────────────

class Calibration:
    """This sheet's own ink and paper levels, measured from this sheet."""

    def __init__(self, ink: float, paper: float):
        self.ink = ink
        self.paper = paper
        self.contrast = paper - ink

    def darkness(self, mean_intensity: float) -> float:
        return float(np.clip((self.paper - mean_intensity) / self.contrast, 0.0, 1.0))


def _calibrate(canon: np.ndarray, page_layout: Dict[str, Any]) -> Calibration:
    fw = page_layout['fiducial_size']['w'] * CANON_W
    fh = page_layout['fiducial_size']['h'] * CANON_H
    inks = [
        rect_median(canon, f['x'] * CANON_W, f['y'] * CANON_H, fw * 0.3, fh * 0.3)
        for f in page_layout['fiducials']
    ]
    ink = float(np.median(inks))
    paper = float(np.percentile(canon, 92))
    if paper - ink < MIN_CONTRAST:
        raise ScanError(
            f'sheet contrast is too low to read reliably '
            f'(ink={ink:.0f}, paper={paper:.0f}) — rescan with more light or '
            f'less glare')
    return Calibration(ink, paper)


# ── sampling ──────────────────────────────────────────────────────────────────

def _bubble_darkness(canon: np.ndarray, cal: Calibration,
                     nx: float, ny: float, radius_px: float) -> float:
    m = disc_mean(canon, nx * CANON_W, ny * CANON_H, radius_px * BUBBLE_SAMPLE_INSET)
    return cal.darkness(m)


def _read_code_track(canon: np.ndarray, cal: Calibration,
                     page_layout: Dict[str, Any]) -> Dict[str, Any]:
    mw = page_layout['code_module_size']['w'] * CANON_W
    bits = []
    for m in page_layout['code_track']:
        v = disc_mean(canon, m['x'] * CANON_W, m['y'] * CANON_H, mw * CODE_SAMPLE_INSET / 2)
        bits.append(1 if cal.darkness(v) >= CODE_BIT_THRESHOLD else 0)
    decoded = geo.decode_sheet_code(bits)
    decoded['bits'] = bits
    return decoded


# ── decision ──────────────────────────────────────────────────────────────────

def _decide(scores: List[float]) -> Dict[str, Any]:
    """One question's option darknesses → a status we are willing to defend.

    The only path to a non-null `selected_option_index` is: exactly one option
    at/above MARK_HI and every other option below MARK_LO. A second option
    sitting in the grey band (an eraser smudge, a bled pen stroke) is enough to
    demote the read to low_confidence — we would rather send a clean sheet to a
    human than hand back a plausible-looking wrong answer.
    """
    order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
    best_i = order[0]
    best = scores[best_i]
    second = scores[order[1]] if len(order) > 1 else 0.0
    n_marked = sum(1 for s in scores if s >= MARK_HI)

    if n_marked >= 2:
        return {
            'status': STATUS_MULTIPLE,
            'selected_option_index': None,
            'best_guess_option_index': None,   # genuinely ambiguous; do not hint
            'confidence': round(float(min(1.0, 0.6 + 0.4 * second)), 3),
        }
    if best >= MARK_HI and second < MARK_LO:
        margin = best - second
        return {
            'status': STATUS_OK,
            'selected_option_index': best_i,
            'best_guess_option_index': best_i,
            'confidence': round(float(min(0.999, 0.60 + 0.40 * margin)), 3),
        }
    if best < MARK_LO:
        clarity = (MARK_LO - best) / MARK_LO
        return {
            'status': STATUS_BLANK,
            'selected_option_index': None,
            'best_guess_option_index': None,
            'confidence': round(float(min(0.999, 0.60 + 0.40 * clarity)), 3),
        }
    # Somewhere in between: a faint mark, a half-shaded bubble, or a strong mark
    # next to a smudge. Never resolved automatically.
    return {
        'status': STATUS_LOW_CONFIDENCE,
        'selected_option_index': None,
        'best_guess_option_index': best_i,
        'confidence': round(float(np.clip(best / MARK_HI * 0.49, 0.0, 0.49)), 3),
    }


def _read_roll(canon: np.ndarray, cal: Calibration, page_layout: Dict[str, Any],
               radius_px: float, roll_digits: int) -> Dict[str, Any]:
    by_digit: Dict[int, List[float]] = {d: [0.0] * 10 for d in range(roll_digits)}
    for b in page_layout['roll']:
        by_digit[b['digit_index']][b['value']] = _bubble_darkness(
            canon, cal, b['x'], b['y'], radius_px)

    digits = []
    text = ''
    needs_review = False
    for d in range(roll_digits):
        scores = by_digit[d]
        res = _decide(scores)
        val = res['selected_option_index']
        digits.append({
            'digit_index': d,
            'value': val,
            'status': res['status'],
            'confidence': res['confidence'],
            'scores': [round(s, 3) for s in scores],
        })
        text += str(val) if val is not None else '?'
        if res['status'] != STATUS_OK:
            needs_review = True
    return {'roll_number': text, 'digits': digits, 'needs_review': needs_review}


# ── per-page scan ─────────────────────────────────────────────────────────────

def _scan_page(gray: np.ndarray, layout: Dict[str, Any],
               expected_short_id: int) -> Dict[str, Any]:
    """Register one page image against the layout and read everything on it."""
    page0 = layout['pages'][0]
    fid_norm_w = page0['fiducial_size']['w']
    src = find_fiducials(gray, fid_norm_w)

    # Candidate corner orderings: as-detected, and the 180-degree rotation
    # (staff feed sheets upside-down all the time). The code track's checksum
    # picks the right one — it is a full end-to-end validation of the homography,
    # not just a rotation flag.
    perms = [(0, 1, 2, 3), (2, 3, 0, 1)]
    dst = [(f['x'] * CANON_W, f['y'] * CANON_H) for f in page0['fiducials']]

    attempts: List[Tuple[Dict[str, Any], np.ndarray, Calibration]] = []
    chosen = None
    for perm in perms:
        pts = [src[i] for i in perm]
        H = homography(pts, dst)
        canon = warp(gray, H, CANON_W, CANON_H)
        cal = _calibrate(canon, page0)
        code = _read_code_track(canon, cal, page0)
        attempts.append((code, canon, cal))
        if code['valid'] and code['sheet_short_id'] == expected_short_id:
            chosen = (code, canon, cal, perm)
            break

    warnings: List[str] = []
    if chosen is None:
        code, canon, cal = attempts[0]
        warnings.append(
            'printed sheet code did not validate — the image was registered on '
            'the corner markers alone. Verify this is the right sheet before '
            'trusting the read.')
        page_index = None
    else:
        code, canon, cal, perm = chosen
        page_index = code['page_index']
        if perm != (0, 1, 2, 3):
            warnings.append('sheet was upside-down; corrected via the sheet code.')

    if page_index is None or not (1 <= page_index <= layout['num_pages']):
        page_index = 1
        if chosen is not None:
            warnings.append('sheet code carried an out-of-range page number; '
                            'assumed page 1.')

    page_layout = next(p for p in layout['pages'] if p['page_index'] == page_index)
    radius_px = layout['bubble_radius'] * CANON_W

    responses: List[Dict[str, Any]] = []
    for q in page_layout['questions']:
        scores = [_bubble_darkness(canon, cal, o['x'], o['y'], radius_px)
                  for o in q['options']]
        res = _decide(scores)
        responses.append({
            'question_number': q['question_number'],
            'selected_option_index': res['selected_option_index'],
            'selected_option': (layout['option_labels'][res['selected_option_index']]
                                if res['selected_option_index'] is not None else None),
            'status': res['status'],
            'confidence': res['confidence'],
            'best_guess_option_index': res['best_guess_option_index'],
            'scores': [round(s, 3) for s in scores],
        })

    roll = None
    if page_layout['roll']:
        roll = _read_roll(canon, cal, page_layout, radius_px, layout['roll_digits'])

    return {
        'page_index': page_index,
        'responses': responses,
        'roll': roll,
        'warnings': warnings,
        'diagnostics': {
            'fiducials_px': [[round(x, 1), round(y, 1)] for x, y in src],
            'ink_level': round(cal.ink, 1),
            'paper_level': round(cal.paper, 1),
            'contrast': round(cal.contrast, 1),
            'sheet_code_valid': bool(code['valid']),
            'sheet_code_short_id': code['sheet_short_id'],
            'mark_threshold_hi': MARK_HI,
            'mark_threshold_lo': MARK_LO,
        },
    }


# ── service ───────────────────────────────────────────────────────────────────

class OMRScanService:
    def __init__(self, scope: Dict[str, Any]):
        self.scope = scope or {}
        self.org_id = self.scope.get('org_id')

    def _resolve_sheet(self, sheet_id=None, paper_id=None) -> Optional[OMRSheet]:
        qs = OMRSheet.objects.all()
        if self.org_id:
            qs = qs.filter(org_id=self.org_id)
        if sheet_id:
            return qs.filter(id=sheet_id).first()
        if paper_id:
            return qs.filter(paper_id=paper_id).order_by('-sheet_version').first()
        return None

    def scan(self, data: bytes, content_type: str = '',
             sheet_id=None, paper_id=None, persist: bool = True) -> Any:
        sheet = self._resolve_sheet(sheet_id=sheet_id, paper_id=paper_id)
        if sheet is None:
            return ErrorResponse(status=404,
                                 message='OMR sheet not found for this paper/sheet id')
        layout = sheet.layout or {}
        if not layout.get('pages'):
            return ErrorResponse(status=400, message='OMR sheet has no layout')

        try:
            pages = load_pages(data, content_type)
        except ScanError as e:
            return self._fail(sheet, str(e), persist)

        merged: Dict[int, Dict[str, Any]] = {}
        warnings: List[str] = []
        diagnostics: Dict[str, Any] = {'pages': []}
        roll_result = None
        pages_scanned: List[int] = []

        for i, img in enumerate(pages):
            gray = to_gray(img)
            try:
                page_res = _scan_page(gray, layout, sheet.short_id)
            except ScanError as e:
                if len(pages) == 1:
                    return self._fail(sheet, str(e), persist)
                warnings.append(f'image {i + 1}: {e}')
                continue

            pages_scanned.append(page_res['page_index'])
            for r in page_res['responses']:
                merged[r['question_number']] = r
            if page_res['roll'] and roll_result is None:
                roll_result = page_res['roll']
            warnings.extend(f"page {page_res['page_index']}: {w}"
                            for w in page_res['warnings'])
            diagnostics['pages'].append(
                dict(page_index=page_res['page_index'], **page_res['diagnostics']))

        if not merged:
            return self._fail(sheet, 'no page of the upload could be registered '
                                     'against this sheet', persist)

        responses = [merged[k] for k in sorted(merged)]
        needs_review = [r['question_number'] for r in responses
                        if r['status'] != STATUS_OK]
        missing = [q for q in range(1, layout['num_questions'] + 1) if q not in merged]
        if missing:
            warnings.append(
                f'{len(missing)} question(s) are not on the page(s) supplied — '
                f'scan every page of the sheet to read them.')

        roll_number = roll_result['roll_number'] if roll_result else ''
        if roll_result and roll_result['needs_review']:
            warnings.append('roll number could not be read cleanly — confirm it manually.')

        diagnostics['pages_scanned'] = pages_scanned
        status = (OMRScan.STATUS_OK
                  if not needs_review and not missing and not warnings
                  else OMRScan.STATUS_NEEDS_REVIEW)

        scan_row = None
        if persist:
            scan_row = OMRScan.objects.create(
                org_id=self.org_id, sheet=sheet, status=status,
                roll_number=roll_number, responses=responses,
                needs_review=needs_review, diagnostics=diagnostics)

        from omr.processor.omrprocessor import OMRScanResponse
        return OMRScanResponse(
            scan_id=scan_row.id if scan_row else None,
            sheet_id=sheet.id,
            paper_id=sheet.paper_id,
            status=status,
            roll_number=roll_number,
            roll=roll_result,
            pages_scanned=pages_scanned,
            responses=responses,
            needs_review=needs_review,
            missing_questions=missing,
            warnings=warnings,
            diagnostics=diagnostics,
        )

    def _fail(self, sheet: OMRSheet, message: str, persist: bool):
        if persist:
            OMRScan.objects.create(org_id=self.org_id, sheet=sheet,
                                   status=OMRScan.STATUS_FAILED, error=message)
        return ErrorResponse(status=422, message=message)
