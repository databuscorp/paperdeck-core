"""
OMR tests.

There are no real scans to test against, so every scan here is SYNTHESIZED:
generate a real sheet → rasterize the real PDF → programmatically darken bubbles
at the layout's own coordinates → run the real scanner → assert it recovers
exactly the bubbles we filled.

That closes the loop end to end: if the generator and the scanner ever disagreed
about where a bubble is, or the deskew were wrong, or the threshold drifted, the
recovered answer key would not match the one we drew.

The hard cases (perspective warp, noise + low contrast + JPEG, upside-down,
multi-mark, blank, faint half-fill) are the point of the file. A scanner that is
only correct on a flatbed scan of a pristine sheet is not a scanner.
"""
from __future__ import annotations

import io
import json
import shutil
import tempfile
from types import SimpleNamespace
from typing import Dict, Tuple

import numpy as np
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from PIL import Image, ImageDraw
from rest_framework_simplejwt.tokens import AccessToken

from omr.models import OMRScan, OMRSheet
from omr.service import geometry as geo
from omr.service.imageops import disc_mean, find_fiducials, homography
from omr.service.scanservice import (
    MARK_HI, MARK_LO, OMRScanService, STATUS_BLANK, STATUS_LOW_CONFIDENCE,
    STATUS_MULTIPLE, STATUS_OK, _decide,
)
from omr.service.sheetservice import OMRSheetService, render_pdf
from papers.models import Paper
from users.models import Organization
from utility.utilityobj import ErrorResponse

MEDIA = tempfile.mkdtemp(prefix='omr-test-media-')

RENDER_DPI = 200
PEN = 25          # a ball-point mark, not pure black


# ── synthetic-scan helpers ────────────────────────────────────────────────────

def rasterize(pdf_bytes: bytes, page_index: int = 1, dpi: int = RENDER_DPI) -> Image.Image:
    import fitz
    with fitz.open(stream=pdf_bytes, filetype='pdf') as doc:
        pix = doc[page_index - 1].get_pixmap(dpi=dpi)
        return Image.frombytes('RGB', (pix.width, pix.height), pix.samples).convert('L')


def _bubble_xy(layout: dict, page_index: int, q: int, opt: int,
               size: Tuple[int, int]) -> Tuple[float, float, float]:
    page = next(p for p in layout['pages'] if p['page_index'] == page_index)
    qd = next(x for x in page['questions'] if x['question_number'] == q)
    o = qd['options'][opt]
    w, h = size
    r = layout['bubble_radius'] * w
    return o['x'] * w, o['y'] * h, r


def fill_bubble(img: Image.Image, layout: dict, page_index: int, q: int, opt: int,
                *, shade: int = PEN, coverage: float = 1.0) -> None:
    """Darken a bubble exactly where the layout says it is.

    coverage=1.0  → a proper, fully darkened bubble.
    coverage=0.5  → a half-shaded bubble (the classic "student was in a hurry"),
                    which must come back as low_confidence, never as an answer.
    """
    cx, cy, r = _bubble_xy(layout, page_index, q, opt, img.size)
    d = ImageDraw.Draw(img)
    rr = r * 0.95
    box = [cx - rr, cy - rr, cx + rr, cy + rr]
    if coverage >= 0.999:
        d.ellipse(box, fill=shade)
    else:
        d.pieslice(box, start=0, end=int(360 * coverage), fill=shade)


def fill_roll(img: Image.Image, layout: dict, roll: str) -> None:
    page = layout['pages'][0]
    w, h = img.size
    r = layout['bubble_radius'] * w
    d = ImageDraw.Draw(img)
    for i, ch in enumerate(roll):
        b = next(x for x in page['roll']
                 if x['digit_index'] == i and x['value'] == int(ch))
        cx, cy = b['x'] * w, b['y'] * h
        rr = r * 0.95
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=PEN)


def to_png(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()


def to_jpeg(img: Image.Image, quality: int = 60) -> bytes:
    buf = io.BytesIO()
    img.convert('L').save(buf, format='JPEG', quality=quality)
    return buf.getvalue()


def perspective(img: Image.Image, pad: int = 70, strength: float = 0.05) -> Image.Image:
    """Simulate a phone photo taken at an angle: paste the page onto a larger
    white canvas and pull its four corners inwards by DIFFERENT amounts.

    This is not a rotation and not a crop — the left edge ends up shorter than
    the right one, so the sheet is genuinely projected, not just turned. A
    scanner that merely crops or merely rotates cannot pass the tests that use
    this: its sample points would drift progressively off the bubbles towards
    the far edge of the page.
    """
    w, h = img.size
    cw, ch = w + 2 * pad, h + 2 * pad
    s = strength
    quad = [
        (pad + s * w,             pad + s * 0.90 * h),        # tl
        (pad + w,                 pad + s * 0.15 * h),        # tr
        (pad + w - s * 0.35 * w,  pad + h),                   # br
        (pad + s * 0.55 * w,      pad + h - s * 1.10 * h),    # bl
    ]
    src = [(0, 0), (w, 0), (w, h), (0, h)]
    # PIL's PERSPECTIVE data maps OUTPUT -> INPUT.
    H = homography(quad, src)
    coeffs = (H / H[2, 2]).ravel()[:8]
    return img.transform((cw, ch), Image.PERSPECTIVE, tuple(coeffs),
                         resample=Image.BICUBIC, fillcolor=255)


def degrade(img: Image.Image, sigma: float = 10.0,
            gain: float = 0.60, lift: float = 45.0, seed: int = 7) -> Image.Image:
    """Sensor noise + a badly lit, washed-out capture.

    `gain`/`lift` crush the dynamic range: paper lands around 198 and ink around
    45 instead of 255/25. A scanner with a hardcoded grey threshold reads this
    sheet as entirely blank; ours re-derives its scale from the sheet's own
    fiducial ink and paper, so it must not care.
    """
    a = np.asarray(img.convert('L'), dtype=np.float32)
    a = a * gain + lift
    rng = np.random.default_rng(seed)
    a = a + rng.normal(0.0, sigma, a.shape)
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), mode='L')


# ── base ──────────────────────────────────────────────────────────────────────

@override_settings(MEDIA_ROOT=MEDIA)
class OMRBase(TestCase):
    N_Q = 40
    N_OPT = 4

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MEDIA, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.org = Organization.objects.create(name='Test Coaching')
        User = get_user_model()
        self.user = User.objects.create_user(
            username='staff1', password='x', email='s@x.com', org=self.org)
        self.paper = Paper.objects.create(
            org=self.org, owner=self.user, title='NEET Mock 1',
            exam_type='NEET', total_marks=160, duration_minutes=180)
        self.scope = {'user_id': self.user.id, 'org_id': self.org.id, 'role': 1}
        self.sheet = self._make_sheet(self.N_Q, self.N_OPT)
        self.layout = self.sheet.layout
        self.pdf = render_pdf(self.layout)

    def _make_sheet(self, n_q: int, n_opt: int = 4, roll_digits: int = 6) -> OMRSheet:
        req = SimpleNamespace(paper_id=self.paper.id, num_questions=n_q,
                              options_per_question=n_opt, roll_digits=roll_digits,
                              regenerate=True)
        resp = OMRSheetService(self.scope).create(req)
        self.assertNotIsInstance(resp, ErrorResponse, getattr(resp, 'message', ''))
        return OMRSheet.objects.get(id=resp.sheet_id)

    def _blank_page(self, page_index: int = 1) -> Image.Image:
        return rasterize(self.pdf, page_index)

    def _scan(self, img_or_bytes, content_type='image/png', sheet=None):
        data = img_or_bytes if isinstance(img_or_bytes, bytes) else to_png(img_or_bytes)
        return OMRScanService(self.scope).scan(
            data, content_type=content_type,
            sheet_id=(sheet or self.sheet).id, persist=True)

    def _answer_key(self, n: int = None) -> Dict[int, int]:
        n = n or self.N_Q
        return {q: (q * 3 + 1) % self.N_OPT for q in range(1, n + 1)}

    def _filled(self, key: Dict[int, int], page_index: int = 1) -> Image.Image:
        img = self._blank_page(page_index)
        for q, opt in key.items():
            fill_bubble(img, self.layout, page_index, q, opt)
        return img

    def _assert_matches_key(self, resp, key: Dict[int, int]):
        self.assertNotIsInstance(resp, ErrorResponse, getattr(resp, 'message', ''))
        got = {r['question_number']: r for r in resp.responses}
        self.assertEqual(len(got), len(key))
        wrong = []
        for q, opt in key.items():
            r = got[q]
            if r['status'] != STATUS_OK or r['selected_option_index'] != opt:
                wrong.append((q, opt, r['status'], r['selected_option_index'],
                              r['scores']))
        self.assertEqual(wrong, [], f'{len(wrong)} question(s) misread: {wrong[:5]}')
        self.assertEqual(resp.needs_review, [])


# ── geometry / layout ─────────────────────────────────────────────────────────

class LayoutTests(TestCase):

    def test_layout_is_complete_and_on_page(self):
        lay = geo.build_layout(num_questions=90, options_per_question=4,
                               roll_digits=6, sheet_short_id=1234)
        self.assertEqual(lay['num_questions'], 90)
        qs = [q for p in lay['pages'] for q in p['questions']]
        self.assertEqual([q['question_number'] for q in qs], list(range(1, 91)))
        for q in qs:
            self.assertEqual(len(q['options']), 4)
            for o in q['options']:
                self.assertTrue(0.0 < o['x'] < 1.0 and 0.0 < o['y'] < 1.0)

    def test_no_two_bubbles_collide(self):
        lay = geo.build_layout(num_questions=125, options_per_question=4,
                               roll_digits=6, sheet_short_id=7)
        r = lay['bubble_radius']
        pts = [(o['x'], o['y'] * geo.PAGE_H / geo.PAGE_W)
               for p in lay['pages'] for q in p['questions'] for o in q['options']]
        pts += [(b['x'], b['y'] * geo.PAGE_H / geo.PAGE_W)
                for b in lay['pages'][0]['roll']]
        a = np.array(pts)
        d = np.linalg.norm(a[:, None, :] - a[None, :, :], axis=-1)
        np.fill_diagonal(d, 9.9)
        self.assertGreater(d.min(), 2 * r,
                           'two bubbles are closer than one diameter apart')

    def test_paginates_beyond_one_page(self):
        lay = geo.build_layout(num_questions=180, options_per_question=4,
                               roll_digits=6, sheet_short_id=9)
        self.assertGreaterEqual(lay['num_pages'], 2)
        self.assertEqual(sum(len(p['questions']) for p in lay['pages']), 180)
        self.assertTrue(lay['pages'][0]['roll'])
        self.assertFalse(lay['pages'][1]['roll'])   # roll grid only on page 1

    def test_sheet_code_round_trip(self):
        for sid in (0, 1, 4095, 65535):
            for page in (1, 5, 15):
                bits = geo.encode_sheet_code(sid, page)
                self.assertEqual(len(bits), geo.CODE_MODULES)
                dec = geo.decode_sheet_code(bits)
                self.assertTrue(dec['valid'])
                self.assertEqual(dec['sheet_short_id'], sid)
                self.assertEqual(dec['page_index'], page)

    def test_sheet_code_checksum_catches_corruption(self):
        bits = geo.encode_sheet_code(1234, 1)
        for i in (0, 5, 19, 23):
            bad = list(bits)
            bad[i] ^= 1
            self.assertFalse(geo.decode_sheet_code(bad)['valid'],
                             f'flipped module {i} slipped past the checksum')


# ── generation ────────────────────────────────────────────────────────────────

class SheetGenerationTests(OMRBase):

    def test_generates_pdf_and_persists_layout(self):
        self.assertTrue(self.pdf.startswith(b'%PDF-'))
        self.assertTrue(self.sheet.pdf.name.endswith('.pdf'))
        self.assertEqual(self.sheet.layout['sheet_short_id'], self.sheet.short_id)
        self.assertEqual(len(self.sheet.layout['pages'][0]['fiducials']), 4)

    def test_pdf_page_count_matches_layout(self):
        import fitz
        big = self._make_sheet(200)
        pdf = render_pdf(big.layout)
        with fitz.open(stream=pdf, filetype='pdf') as doc:
            self.assertEqual(doc.page_count, big.layout['num_pages'])

    def test_regenerate_bumps_version_not_layout_of_printed_sheet(self):
        v1_layout = json.dumps(self.sheet.layout, sort_keys=True)
        s2 = self._make_sheet(self.N_Q)
        self.assertEqual(s2.sheet_version, self.sheet.sheet_version + 1)
        self.sheet.refresh_from_db()
        self.assertEqual(json.dumps(self.sheet.layout, sort_keys=True), v1_layout)


# ── the clean round trip ──────────────────────────────────────────────────────

class CleanScanTests(OMRBase):

    def test_clean_synthetic_sheet_reads_100_percent(self):
        key = self._answer_key()
        img = self._filled(key)
        fill_roll(img, self.layout, '000042')
        resp = self._scan(img)
        self._assert_matches_key(resp, key)
        # A fully-filled sheet with a readable roll number is the ONLY case that
        # earns a clean status — everything else routes to a human.
        self.assertEqual(resp.status, OMRScan.STATUS_OK)
        self.assertEqual(resp.warnings, [])
        self.assertTrue(all(r['confidence'] > 0.8 for r in resp.responses))

    def test_reads_the_printed_sheet_code(self):
        resp = self._scan(self._filled(self._answer_key()))
        d = resp.diagnostics['pages'][0]
        self.assertTrue(d['sheet_code_valid'])
        self.assertEqual(d['sheet_code_short_id'], self.sheet.short_id)

    def test_reads_roll_number(self):
        img = self._filled(self._answer_key())
        fill_roll(img, self.layout, '204815')
        resp = self._scan(img)
        self.assertEqual(resp.roll_number, '204815')
        self.assertFalse(resp.roll['needs_review'])

    def test_unmarked_roll_digits_are_blank_not_guessed(self):
        resp = self._scan(self._filled(self._answer_key()))
        self.assertEqual(resp.roll_number, '??????')
        self.assertTrue(resp.roll['needs_review'])
        self.assertTrue(all(d['status'] == STATUS_BLANK for d in resp.roll['digits']))

    def test_scan_row_is_persisted(self):
        self._scan(self._filled(self._answer_key()))
        row = OMRScan.objects.latest('id')
        self.assertEqual(row.sheet_id, self.sheet.id)
        self.assertEqual(len(row.responses), self.N_Q)

    def test_pdf_scan_of_all_pages_of_a_multipage_sheet(self):
        sheet = self._make_sheet(180)
        self.layout = sheet.layout
        self.pdf = render_pdf(sheet.layout)
        key = {q: q % 4 for q in range(1, 181)}

        import fitz
        out = fitz.open()
        for p in range(1, sheet.layout['num_pages'] + 1):
            img = rasterize(self.pdf, p)
            for q, opt in key.items():
                page = next(x for x in sheet.layout['pages'] if x['page_index'] == p)
                if any(y['question_number'] == q for y in page['questions']):
                    fill_bubble(img, sheet.layout, p, q, opt)
            pg = out.new_page(width=geo.PAGE_W, height=geo.PAGE_H)
            pg.insert_image(pg.rect, stream=to_png(img))
        data = out.tobytes()
        out.close()

        resp = OMRScanService(self.scope).scan(data, content_type='application/pdf',
                                               sheet_id=sheet.id)
        self.assertNotIsInstance(resp, ErrorResponse, getattr(resp, 'message', ''))
        self.assertEqual(len(resp.responses), 180)
        self.assertEqual(resp.needs_review, [])
        self.assertEqual(resp.missing_questions, [])
        got = {r['question_number']: r['selected_option_index'] for r in resp.responses}
        self.assertEqual(got, key)


# ── the hard cases ────────────────────────────────────────────────────────────

class DistortedScanTests(OMRBase):

    def test_perspective_photo_still_reads_100_percent(self):
        """A photo shot at an angle. Proves the deskew: without the homography
        the sampling points drift off the bubbles towards the far edge."""
        key = self._answer_key()
        resp = self._scan(perspective(self._filled(key)))
        self._assert_matches_key(resp, key)

    def test_aggressive_perspective(self):
        key = self._answer_key()
        img = perspective(self._filled(key), pad=110, strength=0.10)
        self._assert_matches_key(self._scan(img), key)

    def test_small_rotation(self):
        key = self._answer_key()
        img = self._filled(key)
        big = Image.new('L', (img.width + 200, img.height + 200), 255)
        big.paste(img, (100, 100))
        rot = big.rotate(4.0, resample=Image.BICUBIC, fillcolor=255)
        self._assert_matches_key(self._scan(rot), key)

    def test_noisy_low_contrast_jpeg_still_reads_100_percent(self):
        """Washed-out, noisy, JPEG-compressed. The thresholds are fractions of
        the sheet's OWN ink/paper range, so a crushed dynamic range must not
        change a single answer."""
        key = self._answer_key()
        img = degrade(self._filled(key))
        resp = self._scan(to_jpeg(img), content_type='image/jpeg')
        self._assert_matches_key(resp, key)
        d = resp.diagnostics['pages'][0]
        self.assertLess(d['paper_level'], 235, 'test image was not actually washed out')
        self.assertGreater(d['ink_level'], 25, 'test image was not actually lifted')

    def test_perspective_plus_noise_together(self):
        key = self._answer_key()
        img = degrade(perspective(self._filled(key)), sigma=8.0, gain=0.65, lift=40.0)
        self._assert_matches_key(self._scan(to_jpeg(img, quality=70), 'image/jpeg'), key)

    def test_deskew_is_load_bearing(self):
        """Negative control.

        Read the SAME angled photo the way a crop-only scanner would: detect the
        markers, crop to their bounding box, stretch it to the page rectangle,
        and sample the layout coordinates in that rectangle. No perspective
        solve. If that could read the sheet too, every deskew test above would be
        proving nothing — so this asserts it CANNOT.
        """
        key = self._answer_key()
        img = perspective(self._filled(key), pad=110, strength=0.10)

        a = np.asarray(img.convert('L'), dtype=np.float32)
        fids = find_fiducials(a, self.layout['pages'][0]['fiducial_size']['w'])
        xs = [p[0] for p in fids]
        ys = [p[1] for p in fids]
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)

        page = self.layout['pages'][0]
        f_tl, f_br = page['fiducials'][0], page['fiducials'][2]
        r = self.layout['bubble_radius'] * (x1 - x0) * 0.70

        correct = 0
        for q in page['questions']:
            scores = []
            for o in q['options']:
                u = (o['x'] - f_tl['x']) / (f_br['x'] - f_tl['x'])
                v = (o['y'] - f_tl['y']) / (f_br['y'] - f_tl['y'])
                m = disc_mean(a, x0 + u * (x1 - x0), y0 + v * (y1 - y0), r)
                scores.append(float(np.clip((255.0 - m) / 255.0, 0.0, 1.0)))
            res = _decide(scores)
            if (res['status'] == STATUS_OK
                    and res['selected_option_index'] == key[q['question_number']]):
                correct += 1

        n = len(page['questions'])
        self.assertLess(
            correct, 0.75 * n,
            f'crop-and-stretch read {correct}/{n} correctly — this photo is not '
            f'actually distorted enough for the deskew tests to mean anything')
        # ...and the real pipeline, on the very same image, gets all of them.
        self._assert_matches_key(self._scan(img), key)

    def test_upside_down_sheet_is_corrected(self):
        """Staff feed sheets in backwards. The code-track checksum catches the
        180-degree corner ordering and the scanner re-registers."""
        key = self._answer_key()
        img = self._filled(key).rotate(180, expand=True)
        resp = self._scan(img)
        self._assert_matches_key(resp, key)
        self.assertTrue(any('upside-down' in w for w in resp.warnings))


# ── ambiguity: the part that must never guess ─────────────────────────────────

class AmbiguityTests(OMRBase):

    def test_two_marks_on_one_question_report_multiple_marks(self):
        key = self._answer_key()
        img = self._filled(key)
        fill_bubble(img, self.layout, 1, 7, (key[7] + 1) % self.N_OPT)   # a second mark

        resp = self._scan(img)
        r = next(x for x in resp.responses if x['question_number'] == 7)
        self.assertEqual(r['status'], STATUS_MULTIPLE)
        self.assertIsNone(r['selected_option_index'],
                          'the scanner GUESSED an answer on a double-marked question')
        self.assertIsNone(r['best_guess_option_index'])
        self.assertIn(7, resp.needs_review)
        self.assertEqual(resp.status, OMRScan.STATUS_NEEDS_REVIEW)
        # ...and it did not contaminate its neighbours
        for q in (6, 8):
            n = next(x for x in resp.responses if x['question_number'] == q)
            self.assertEqual(n['status'], STATUS_OK)
            self.assertEqual(n['selected_option_index'], key[q])

    def test_unanswered_question_reports_blank(self):
        key = self._answer_key()
        del key[12]
        resp = self._scan(self._filled(key))
        r = next(x for x in resp.responses if x['question_number'] == 12)
        self.assertEqual(r['status'], STATUS_BLANK)
        self.assertIsNone(r['selected_option_index'])
        self.assertIn(12, resp.needs_review)
        self.assertLess(max(r['scores']), MARK_LO)

    def test_faint_half_fill_reports_low_confidence(self):
        key = self._answer_key()
        del key[20]
        img = self._filled(key)
        fill_bubble(img, self.layout, 1, 20, 2, coverage=0.5)   # half-shaded

        resp = self._scan(img)
        r = next(x for x in resp.responses if x['question_number'] == 20)
        self.assertEqual(r['status'], STATUS_LOW_CONFIDENCE, f'scores={r["scores"]}')
        self.assertIsNone(r['selected_option_index'],
                          'the scanner GUESSED an answer on a half-filled bubble')
        self.assertEqual(r['best_guess_option_index'], 2)   # a hint for the human
        self.assertLess(r['confidence'], 0.5)
        self.assertIn(20, resp.needs_review)
        self.assertTrue(MARK_LO <= r['scores'][2] < MARK_HI)

    def test_faint_pencil_mark_reports_low_confidence(self):
        key = self._answer_key()
        del key[30]
        img = self._filled(key)
        fill_bubble(img, self.layout, 1, 30, 1, shade=165)   # too light to call
        r = next(x for x in self._scan(img).responses if x['question_number'] == 30)
        self.assertEqual(r['status'], STATUS_LOW_CONFIDENCE, f'scores={r["scores"]}')
        self.assertIsNone(r['selected_option_index'])

    def test_substantial_smudge_beside_a_real_mark_forces_review(self):
        """An eraser smudge / bled stroke dark enough to land in the uncertain
        band demotes the whole question, even though one option is clearly
        marked. We would rather hand a clean sheet to a human than hand back a
        plausible-looking wrong answer."""
        key = self._answer_key()
        img = self._filled(key)
        fill_bubble(img, self.layout, 1, 15, (key[15] + 2) % self.N_OPT,
                    shade=90, coverage=0.6)
        r = next(x for x in self._scan(img).responses if x['question_number'] == 15)
        self.assertEqual(r['status'], STATUS_LOW_CONFIDENCE, f'scores={r["scores"]}')
        self.assertIsNone(r['selected_option_index'],
                          'a strong mark beside a real smudge was accepted without review')
        self.assertIn(15, self._scan(img).needs_review)

    def test_faint_speck_does_not_trigger_a_false_review(self):
        """The flip side: a scanner that flags everything is a scanner nobody
        uses. A speck well below the paper/ink noise floor stays paper, and the
        question still reads clean."""
        key = self._answer_key()
        img = self._filled(key)
        fill_bubble(img, self.layout, 1, 16, (key[16] + 2) % self.N_OPT,
                    shade=225, coverage=0.5)   # a barely-there stray mark
        r = next(x for x in self._scan(img).responses if x['question_number'] == 16)
        self.assertEqual(r['status'], STATUS_OK, f'scores={r["scores"]}')
        self.assertEqual(r['selected_option_index'], key[16])

    def test_needs_review_lists_every_non_ok_question(self):
        key = self._answer_key()
        del key[3]                                       # blank
        img = self._filled(key)
        fill_bubble(img, self.layout, 1, 5, 0)           # 5 now has two marks
        fill_bubble(img, self.layout, 1, 5, 1)
        fill_bubble(img, self.layout, 1, 9, 3, coverage=0.5)  # half fill (9 was blankable)

        resp = self._scan(img)
        for q in (3, 5, 9):
            self.assertIn(q, resp.needs_review)
        for r in resp.responses:
            if r['status'] != STATUS_OK:
                self.assertIsNone(r['selected_option_index'])
                self.assertIn(r['question_number'], resp.needs_review)
            else:
                self.assertIsNotNone(r['selected_option_index'])


class ScanFailureTests(OMRBase):

    def test_sheet_without_fiducials_is_rejected_not_guessed(self):
        img = Image.new('L', (1200, 1700), 245)     # blank paper, no markers
        resp = self._scan(img)
        self.assertIsInstance(resp, ErrorResponse)
        self.assertEqual(resp.status, 422)
        self.assertIn('registration markers', resp.message)
        self.assertEqual(OMRScan.objects.latest('id').status, OMRScan.STATUS_FAILED)

    def test_garbage_upload_is_rejected(self):
        resp = self._scan(b'not an image at all', content_type='image/png')
        self.assertIsInstance(resp, ErrorResponse)

    def test_scanning_only_page_1_of_a_2_page_sheet_reports_the_gap(self):
        sheet = self._make_sheet(180)
        pdf = render_pdf(sheet.layout)
        img = rasterize(pdf, 1)
        resp = OMRScanService(self.scope).scan(to_png(img), 'image/png', sheet_id=sheet.id)
        self.assertNotIsInstance(resp, ErrorResponse)
        self.assertEqual(resp.pages_scanned, [1])
        self.assertTrue(resp.missing_questions)
        self.assertTrue(any('not on the page' in w for w in resp.warnings))


# ── API ───────────────────────────────────────────────────────────────────────

@override_settings(MEDIA_ROOT=MEDIA)
class OMRApiTests(OMRBase):

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.auth = {'HTTP_AUTHORIZATION': f'Bearer {AccessToken.for_user(self.user)}'}

    def test_post_sheet_creates_and_returns_layout(self):
        resp = self.client.post(
            '/api/omr/sheet/',
            data=json.dumps({'paper_id': self.paper.id, 'num_questions': 30,
                             'options_per_question': 4, 'regenerate': True}),
            content_type='application/json', **self.auth)
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body['num_questions'], 30)
        self.assertTrue(body['pdf_url'])
        self.assertEqual(len(body['layout']['pages'][0]['questions']), 30)

    def test_post_sheet_download_returns_pdf(self):
        resp = self.client.post(
            '/api/omr/sheet/?download=1',
            data=json.dumps({'paper_id': self.paper.id, 'num_questions': 20,
                             'regenerate': True}),
            content_type='application/json', **self.auth)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'application/pdf')
        self.assertTrue(resp.content.startswith(b'%PDF-'))

    def test_get_sheet_by_paper_id(self):
        resp = self.client.get(f'/api/omr/sheet/?paper_id={self.paper.id}', **self.auth)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['sheet_id'], self.sheet.id)

    def test_get_sheet_pdf(self):
        resp = self.client.get(f'/api/omr/sheet/pdf/?sheet_id={self.sheet.id}', **self.auth)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'application/pdf')

    def test_post_scan_returns_responses_and_needs_review(self):
        key = self._answer_key()
        del key[4]
        img = self._filled(key)
        fill_bubble(img, self.layout, 1, 8, 0)
        fill_bubble(img, self.layout, 1, 8, 2)      # double mark
        fill_roll(img, self.layout, '112233')

        upload = io.BytesIO(to_png(img))
        upload.name = 'scan.png'
        resp = self.client.post(
            '/api/omr/scan/',
            data={'sheet_id': str(self.sheet.id), 'file': upload}, **self.auth)
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body['roll_number'], '112233')
        self.assertEqual(sorted(body['needs_review']), [4, 8])
        by_q = {r['question_number']: r for r in body['responses']}
        self.assertEqual(by_q[4]['status'], STATUS_BLANK)
        self.assertEqual(by_q[8]['status'], STATUS_MULTIPLE)
        self.assertIsNone(by_q[8]['selected_option_index'])
        self.assertEqual(by_q[1]['selected_option_index'], key[1])

    def test_scan_requires_auth(self):
        resp = self.client.post('/api/omr/scan/', data={'sheet_id': str(self.sheet.id)})
        self.assertEqual(resp.status_code, 401)

    def test_scan_without_file_is_400(self):
        resp = self.client.post('/api/omr/scan/',
                                data={'sheet_id': str(self.sheet.id)}, **self.auth)
        self.assertEqual(resp.status_code, 400)

    def test_org_isolation(self):
        other_org = Organization.objects.create(name='Rival Coaching')
        User = get_user_model()
        other = User.objects.create_user(username='rival', password='x',
                                         email='r@x.com', org=other_org)
        auth = {'HTTP_AUTHORIZATION': f'Bearer {AccessToken.for_user(other)}'}
        resp = self.client.get(f'/api/omr/sheet/?sheet_id={self.sheet.id}', **auth)
        self.assertEqual(resp.status_code, 404)
