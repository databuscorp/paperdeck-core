"""
OMR sheet geometry — the SINGLE SOURCE OF TRUTH for every printed mark.

Both the generator (reportlab, `sheetservice.py`) and the scanner
(`scanservice.py`) read their coordinates from the layout dict built here. The
scanner NEVER re-derives geometry from the image; it warps the photo into a
canonical rectangle and then looks up each bubble centre in this layout. That is
the core design decision of the whole feature: a bubble can only be mis-sampled
if the layout is wrong, never because two code paths disagreed about where the
bubble was.

Coordinate systems
------------------
* Internally everything is in **PDF points, top-left origin, y growing down**
  (image convention). reportlab wants bottom-left origin, so the generator flips
  y exactly once, at draw time (`_y()`).
* The layout dict stores **normalized** coordinates: x / PAGE_W, y / PAGE_H,
  both in 0..1. Those are resolution independent, so the scanner can warp a
  4000px phone photo or a 1240px canonical raster and use the same numbers.

Machine-readable sheet id — why a bubble code track and not a QR code
--------------------------------------------------------------------
We print a 24-module binary track (solid square = 1, hollow square = 0) rather
than a QR code. Reasons:
  1. Once the four corner fiducials give us a homography, the track's modules
     are at *known* normalized coordinates. Reading them is the exact same
     "sample a disc, measure darkness" operation the bubbles already need — zero
     new code, zero new failure modes, zero new dependencies (a QR decoder would
     mean pyzbar/zxing/opencv).
  2. A QR code needs its own locator patterns and its own perspective solve,
     duplicating what the fiducials already do.
  3. The track's 4-bit checksum doubles as an **orientation check**: if the
     sheet was fed in upside-down, the 180-degree-rotated read fails its
     checksum and the scanner retries with the corners rotated. A QR code would
     give us orientation but not this cheap end-to-end validation of the whole
     homography.
The human-readable id is also printed as text next to the track for staff.
"""
from __future__ import annotations

from typing import Any, Dict, List

# ── Page ──────────────────────────────────────────────────────────────────────
PAGE_W = 595.2756   # A4 width  in pt
PAGE_H = 841.8898   # A4 height in pt

# ── Fiducials (registration markers) ──────────────────────────────────────────
# Solid black squares, one per corner. Deliberately much LARGER than a bubble
# (20pt square vs a 10pt bubble diameter) so that a filled-in bubble can never
# clear the blob detector's minimum-size filter and masquerade as a marker.
FID_SIZE   = 20.0
FID_MARGIN = 16.0                       # gap from the paper edge to the square
FID_C      = FID_MARGIN + FID_SIZE / 2  # 26pt → centre offset from each edge

# ── Sheet-code track ──────────────────────────────────────────────────────────
CODE_MODULES     = 24        # 16 bits sheet id | 4 bits page no | 4 bits checksum
CODE_MODULE_SIZE = 8.0
CODE_MODULE_PITCH = 11.0
CODE_Y_FROM_BOTTOM = 45.0    # sits above the bottom fiducials

# ── Bubbles ───────────────────────────────────────────────────────────────────
BUBBLE_R      = 5.0
BUBBLE_PITCH  = 16.0
LABEL_W       = 20.0
COL_GAP       = 8.0
ROW_PITCH     = 18.0

# ── Roll-number grid (page 1 only) ────────────────────────────────────────────
ROLL_COL_PITCH = 20.0
ROLL_ROW_PITCH = 17.0
ROLL_X0        = 72.0
ROLL_Y0        = 138.0     # centre of the "0" row
ROLL_HEADER_Y  = 120.0

# ── Question grid bounds ──────────────────────────────────────────────────────
Q_X_MIN        = 45.0
Q_X_MAX        = PAGE_W - 45.0
Q_Y_BOTTOM     = PAGE_H - 70.0          # last row centre may not go past here
Q_TOP_PAGE1    = 334.0                  # first row centre, page 1 (below roll grid)
Q_TOP_PAGEN    = 74.0                   # first row centre, pages 2+
COL_HEADER_DY  = 14.0                   # A/B/C/D letters sit this far above row 1

OPTION_LABELS = ['A', 'B', 'C', 'D', 'E', 'F']

LAYOUT_VERSION = 1


# ── helpers ───────────────────────────────────────────────────────────────────

def _n(x: float, y: float) -> Dict[str, float]:
    """Point in top-left-origin pt → normalized 0..1 dict."""
    return {'x': round(x / PAGE_W, 6), 'y': round(y / PAGE_H, 6)}


def column_width(options_per_question: int) -> float:
    return LABEL_W + options_per_question * BUBBLE_PITCH + COL_GAP


def columns_per_page(options_per_question: int) -> int:
    return max(1, int((Q_X_MAX - Q_X_MIN) // column_width(options_per_question)))


def rows_for_page(page_index: int) -> int:
    top = Q_TOP_PAGE1 if page_index == 1 else Q_TOP_PAGEN
    return max(1, int((Q_Y_BOTTOM - top) // ROW_PITCH) + 1)


def capacity(page_index: int, options_per_question: int) -> int:
    return columns_per_page(options_per_question) * rows_for_page(page_index)


def page_count(num_questions: int, options_per_question: int) -> int:
    remaining = num_questions - capacity(1, options_per_question)
    if remaining <= 0:
        return 1
    per_extra = capacity(2, options_per_question)
    return 1 + (remaining + per_extra - 1) // per_extra


# ── sheet code ────────────────────────────────────────────────────────────────

def encode_sheet_code(sheet_short_id: int, page_index: int) -> List[int]:
    """24 bits, MSB first: [16 = sheet id & 0xFFFF][4 = page][4 = checksum]."""
    sid = int(sheet_short_id) & 0xFFFF
    page = int(page_index) & 0xF
    payload = (sid << 4) | page                       # 20 bits
    checksum = _checksum(payload)
    word = (payload << 4) | checksum                  # 24 bits
    return [(word >> (CODE_MODULES - 1 - i)) & 1 for i in range(CODE_MODULES)]


def _checksum(payload20: int) -> int:
    """Sum of the payload's five nibbles, mod 16. Cheap, catches single-module
    flips and — importantly — catches a 180-degree-rotated read."""
    s = 0
    v = payload20 & 0xFFFFF
    for _ in range(5):
        s += v & 0xF
        v >>= 4
    return s & 0xF


def decode_sheet_code(bits: List[int]) -> Dict[str, Any]:
    if len(bits) != CODE_MODULES:
        return {'valid': False, 'sheet_short_id': None, 'page_index': None}
    word = 0
    for b in bits:
        word = (word << 1) | (1 if b else 0)
    checksum = word & 0xF
    payload = (word >> 4) & 0xFFFFF
    page = payload & 0xF
    sid = (payload >> 4) & 0xFFFF
    return {
        'valid': _checksum(payload) == checksum,
        'sheet_short_id': sid,
        'page_index': page,
    }


# ── layout construction ───────────────────────────────────────────────────────

def _fiducials() -> List[Dict[str, Any]]:
    """Clockwise from top-left. The scanner relies on this exact order."""
    pts = [
        ('tl', FID_C,          FID_C),
        ('tr', PAGE_W - FID_C, FID_C),
        ('br', PAGE_W - FID_C, PAGE_H - FID_C),
        ('bl', FID_C,          PAGE_H - FID_C),
    ]
    return [dict(id=i, **_n(x, y)) for i, x, y in pts]


def _code_track(sheet_short_id: int, page_index: int) -> List[Dict[str, Any]]:
    bits = encode_sheet_code(sheet_short_id, page_index)
    total_w = CODE_MODULES * CODE_MODULE_PITCH - (CODE_MODULE_PITCH - CODE_MODULE_SIZE)
    x0 = (PAGE_W - total_w) / 2.0 + CODE_MODULE_SIZE / 2.0
    cy = PAGE_H - CODE_Y_FROM_BOTTOM
    out = []
    for i, bit in enumerate(bits):
        cx = x0 + i * CODE_MODULE_PITCH
        out.append(dict(index=i, bit=int(bit), **_n(cx, cy)))
    return out


def _roll_grid(roll_digits: int) -> List[Dict[str, Any]]:
    out = []
    for d in range(roll_digits):
        cx = ROLL_X0 + d * ROLL_COL_PITCH
        for v in range(10):
            cy = ROLL_Y0 + v * ROLL_ROW_PITCH
            out.append(dict(digit_index=d, value=v, **_n(cx, cy)))
    return out


def _questions_for_page(page_index: int, first_q: int, count: int,
                        options_per_question: int) -> List[Dict[str, Any]]:
    ncols = columns_per_page(options_per_question)
    nrows = rows_for_page(page_index)
    colw = column_width(options_per_question)
    block_w = ncols * colw
    x_start = Q_X_MIN + (Q_X_MAX - Q_X_MIN - block_w) / 2.0
    y_top = Q_TOP_PAGE1 if page_index == 1 else Q_TOP_PAGEN

    out = []
    for i in range(count):
        col = i // nrows                 # column-major fill (Q1..Qn down column 1)
        row = i % nrows
        col_x = x_start + col * colw
        cy = y_top + row * ROW_PITCH
        opts = []
        for o in range(options_per_question):
            cx = col_x + LABEL_W + 4.0 + o * BUBBLE_PITCH + BUBBLE_R
            opts.append(dict(option_index=o, label=OPTION_LABELS[o], **_n(cx, cy)))
        out.append({
            'question_number': first_q + i,
            'column': col,
            'row': row,
            'label_right_x': round((col_x + LABEL_W - 4.0) / PAGE_W, 6),
            'options': opts,
        })
    return out


def build_layout(num_questions: int,
                 options_per_question: int = 4,
                 roll_digits: int = 6,
                 sheet_short_id: int = 0,
                 sheet_version: int = 1,
                 title: str = '',
                 meta: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """The layout JSON persisted on OMRSheet.layout. Everything downstream —
    the PDF and the scanner — is a pure function of this dict."""
    if num_questions < 1:
        raise ValueError('num_questions must be >= 1')
    if not 2 <= options_per_question <= len(OPTION_LABELS):
        raise ValueError(f'options_per_question must be 2..{len(OPTION_LABELS)}')
    if not 1 <= roll_digits <= 10:
        raise ValueError('roll_digits must be 1..10')

    npages = page_count(num_questions, options_per_question)
    if npages > 15:
        # page index is 4 bits in the code track
        raise ValueError('too many questions for one OMR sheet (max 15 pages)')

    pages: List[Dict[str, Any]] = []
    assigned = 0
    for p in range(1, npages + 1):
        cap = capacity(p, options_per_question)
        count = min(cap, num_questions - assigned)
        page = {
            'page_index': p,
            'fiducials': _fiducials(),
            'fiducial_size': {'w': round(FID_SIZE / PAGE_W, 6),
                              'h': round(FID_SIZE / PAGE_H, 6)},
            'code_track': _code_track(sheet_short_id, p),
            'code_module_size': {'w': round(CODE_MODULE_SIZE / PAGE_W, 6),
                                 'h': round(CODE_MODULE_SIZE / PAGE_H, 6)},
            'roll': _roll_grid(roll_digits) if p == 1 else [],
            'questions': _questions_for_page(p, assigned + 1, count, options_per_question),
        }
        pages.append(page)
        assigned += count

    return {
        'layout_version': LAYOUT_VERSION,
        'sheet_version': sheet_version,
        'sheet_short_id': int(sheet_short_id) & 0xFFFF,
        'title': title,
        'meta': meta or {},
        'page_size': 'A4',
        'page_width_pt': PAGE_W,
        'page_height_pt': PAGE_H,
        'num_questions': num_questions,
        'options_per_question': options_per_question,
        'option_labels': OPTION_LABELS[:options_per_question],
        'roll_digits': roll_digits,
        'num_pages': npages,
        # normalized against page WIDTH — a bubble is a circle, so the scanner
        # multiplies this by the canonical raster width for a pixel radius.
        'bubble_radius': round(BUBBLE_R / PAGE_W, 6),
        'pages': pages,
    }
