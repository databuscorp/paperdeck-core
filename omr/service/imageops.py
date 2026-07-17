"""
Image primitives for the OMR scanner — binarization, blob detection, homography
and perspective warping.

Implemented on numpy + Pillow ONLY. We deliberately did not add OpenCV: the four
things we need from it (adaptive threshold, connected components,
getPerspectiveTransform, warpPerspective) are ~150 lines of numpy, and they are
exercised end-to-end by the synthetic-scan tests. Adding opencv-python-headless
would put a ~100MB native wheel into every container image to save those lines.
If real-world scans ever demand OpenCV's more sophisticated contour handling,
swapping this module out is a contained change — nothing else imports cv2-shaped
concepts.
"""
from __future__ import annotations

import io
from typing import Any, Dict, List, Tuple

import numpy as np
from PIL import Image, ImageOps


class ScanError(RuntimeError):
    """The sheet could not be registered at all (no fiducials, no contrast).

    Loud on purpose: a scan we cannot register must never fall back to
    "read it anyway and hope", because that silently mis-grades a student.
    """


# ── loading ───────────────────────────────────────────────────────────────────

def load_pages(data: bytes, content_type: str = '') -> List[Image.Image]:
    """Bytes (PDF | JPEG | PNG | …) → a list of RGB PIL pages."""
    is_pdf = data[:5] == b'%PDF-' or 'pdf' in (content_type or '').lower()
    if is_pdf:
        import fitz  # pymupdf
        pages: List[Image.Image] = []
        with fitz.open(stream=data, filetype='pdf') as doc:
            for page in doc:
                pix = page.get_pixmap(dpi=200)
                pages.append(Image.frombytes('RGB', (pix.width, pix.height), pix.samples))
        if not pages:
            raise ScanError('PDF contained no pages')
        return pages
    try:
        img = Image.open(io.BytesIO(data))
        img = ImageOps.exif_transpose(img)   # phone photos carry a rotation tag
        return [img.convert('RGB')]
    except ScanError:
        raise
    except Exception as e:
        raise ScanError(f'could not decode uploaded image: {e}')


def to_gray(img: Image.Image) -> np.ndarray:
    return np.asarray(img.convert('L'), dtype=np.float32)


# ── binarization ──────────────────────────────────────────────────────────────

def _box_mean(gray: np.ndarray, win: int) -> np.ndarray:
    """Mean over a (win x win) box, via an integral image. O(n) regardless of win."""
    h, w = gray.shape
    win = max(3, win | 1)
    r = win // 2
    ii = np.zeros((h + 1, w + 1), dtype=np.float64)
    ii[1:, 1:] = gray.cumsum(0).cumsum(1)

    ys = np.arange(h)
    xs = np.arange(w)
    y0 = np.clip(ys - r, 0, h)[:, None]
    y1 = np.clip(ys + r + 1, 0, h)[:, None]
    x0 = np.clip(xs - r, 0, w)[None, :]
    x1 = np.clip(xs + r + 1, 0, w)[None, :]

    total = ii[y1, x1] - ii[y0, x1] - ii[y1, x0] + ii[y0, x0]
    area = (y1 - y0) * (x1 - x0)
    return (total / area).astype(np.float32)


def ink_mask(gray: np.ndarray) -> np.ndarray:
    """True where the pixel is ink.

    Local (not global) thresholding, because a phone photo of a sheet has a
    lighting gradient across it — a single grey level would eat one side of the
    page. The window is deliberately LARGE (~18% of the page) so that it always
    straddles paper even when centred inside a 20pt fiducial square; a small
    window would average the square with itself and make it disappear.
    """
    h, w = gray.shape
    win = max(31, int(0.18 * max(h, w)))
    local = _box_mean(gray, win)
    return gray < (local * 0.72)


# ── connected components (run-length + union-find) ────────────────────────────

def _find(parent: List[int], i: int) -> int:
    root = i
    while parent[root] != root:
        root = parent[root]
    while parent[i] != root:
        parent[i], i = root, parent[i]
    return root


def connected_components(mask: np.ndarray) -> List[Dict[str, Any]]:
    """8-connected components of a boolean mask.

    Row runs are extracted with numpy, then unioned across adjacent rows, so the
    Python-level loop is over runs (thousands) and not pixels (millions).
    Returns dicts: area, bbox (x0,y0,x1,y1 inclusive), centroid (cx,cy).
    """
    h, w = mask.shape
    runs: List[Tuple[int, int, int]] = []          # (row, x_start, x_end_exclusive)
    row_runs: List[List[int]] = [[] for _ in range(h)]

    padded = np.zeros((h, w + 2), dtype=bool)
    padded[:, 1:-1] = mask
    diff = np.diff(padded.astype(np.int8), axis=1)
    for y in range(h):
        starts = np.flatnonzero(diff[y] == 1)
        ends = np.flatnonzero(diff[y] == -1)
        for s, e in zip(starts, ends):
            row_runs[y].append(len(runs))
            runs.append((y, int(s), int(e)))

    parent = list(range(len(runs)))
    for y in range(1, h):
        for i in row_runs[y]:
            _, s1, e1 = runs[i]
            for j in row_runs[y - 1]:
                _, s2, e2 = runs[j]
                if s1 - 1 < e2 and s2 - 1 < e1:      # 8-connectivity: allow diagonal touch
                    ri, rj = _find(parent, i), _find(parent, j)
                    if ri != rj:
                        parent[max(ri, rj)] = min(ri, rj)

    acc: Dict[int, Dict[str, float]] = {}
    for i, (y, s, e) in enumerate(runs):
        root = _find(parent, i)
        n = e - s
        a = acc.get(root)
        if a is None:
            acc[root] = a = {'area': 0.0, 'sx': 0.0, 'sy': 0.0,
                             'x0': float(s), 'x1': float(e - 1),
                             'y0': float(y), 'y1': float(y)}
        a['area'] += n
        a['sx'] += (s + e - 1) * n / 2.0            # sum of x over the run
        a['sy'] += y * n
        a['x0'] = min(a['x0'], s)
        a['x1'] = max(a['x1'], e - 1)
        a['y0'] = min(a['y0'], y)
        a['y1'] = max(a['y1'], y)

    out = []
    for a in acc.values():
        area = a['area']
        out.append({
            'area': area,
            'bbox': (a['x0'], a['y0'], a['x1'], a['y1']),
            'centroid': (a['sx'] / area, a['sy'] / area),
        })
    return out


# ── fiducial detection ────────────────────────────────────────────────────────

def find_fiducials(gray: np.ndarray, fid_norm_w: float,
                   detect_max_dim: int = 900) -> List[Tuple[float, float]]:
    """Locate the four corner squares. Returns centres in FULL-RESOLUTION image
    pixels, ordered [top-left, top-right, bottom-right, bottom-left] as seen in
    the image (which may still be the sheet's 180-degree rotation — the caller
    resolves that with the code-track checksum).

    Assumes the sheet occupies most of the frame, which is what "photograph the
    sheet" means in practice. Candidates are filtered on size, squareness and
    solidity, then the one nearest each image corner wins — the fiducials are by
    construction the outermost solid squares on the page.
    """
    H, W = gray.shape
    scale = min(1.0, detect_max_dim / float(max(H, W)))
    if scale < 1.0:
        small = np.asarray(
            Image.fromarray(gray.astype(np.uint8)).resize(
                (max(1, int(W * scale)), max(1, int(H * scale))), Image.BILINEAR),
            dtype=np.float32)
    else:
        small = gray
    sh, sw = small.shape

    mask = ink_mask(small)

    # Expected marker side, assuming the sheet fills the frame. The 0.55 floor is
    # what keeps a *filled bubble* (roughly half a fiducial's size) from ever
    # qualifying; it holds as long as the sheet occupies >= ~65% of the frame
    # width, which is what "photograph the sheet" means in practice.
    exp_side = fid_norm_w * sw
    min_side = exp_side * 0.55
    max_side = exp_side * 2.40

    candidates: List[Dict[str, Any]] = []
    for comp in connected_components(mask):
        bx0, by0, bx1, by1 = comp['bbox']
        bw = bx1 - bx0 + 1
        bh = by1 - by0 + 1
        if not (min_side <= bw <= max_side and min_side <= bh <= max_side):
            continue
        if not 0.55 <= (bw / bh if bh else 99.0) <= 1.80:
            continue
        if comp['area'] / float(bw * bh) < 0.62:     # solid block, not an outline/glyph
            continue
        if bx0 <= 1 or by0 <= 1 or bx1 >= sw - 2 or by1 >= sh - 2:
            continue                                 # touches the frame → background, not paper
        candidates.append(comp)

    if len(candidates) < 4:
        raise ScanError(
            'could not find all 4 registration markers — make sure the whole '
            'sheet including its four corner squares is in frame, in focus, '
            'and evenly lit')

    # The fiducials are, by construction, the outermost solid squares on the
    # sheet: nothing else printed on the page lies closer to a paper corner. So
    # for each image corner take the nearest surviving candidate. Searching the
    # whole frame (rather than a fixed corner window) is what makes this work
    # when the sheet is inset in the photo or slightly rotated.
    corners = [(0.0, 0.0), (sw - 1.0, 0.0), (sw - 1.0, sh - 1.0), (0.0, sh - 1.0)]
    picked: List[Dict[str, Any]] = []
    for (cx, cy) in corners:
        best = min(candidates,
                   key=lambda c: (c['centroid'][0] - cx) ** 2 + (c['centroid'][1] - cy) ** 2)
        picked.append(best)

    if len({id(c) for c in picked}) != 4:
        raise ScanError('registration markers are degenerate — the same marker was '
                        'nearest to two corners; rescan with the whole sheet in frame')

    areas = [c['area'] for c in picked]
    if max(areas) > 3.0 * min(areas):
        raise ScanError('the four detected corner markers are not the same size — '
                        'something other than a registration marker was picked up')

    found = [tuple(c['centroid']) for c in picked]
    if _polygon_area(found) < 0.15 * sh * sw:
        raise ScanError('registration markers found but the sheet occupies too '
                        'little of the frame — move the camera closer')

    inv = 1.0 / scale
    return [(x * inv, y * inv) for (x, y) in found]


def _polygon_area(pts: List[Tuple[float, float]]) -> float:
    a = 0.0
    n = len(pts)
    for i in range(n):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % n]
        a += x0 * y1 - x1 * y0
    return abs(a) / 2.0


# ── homography + warp ─────────────────────────────────────────────────────────

def homography(src: List[Tuple[float, float]],
               dst: List[Tuple[float, float]]) -> np.ndarray:
    """3x3 H with dst ~ H @ src, from 4 point correspondences (DLT)."""
    if len(src) != 4 or len(dst) != 4:
        raise ScanError('homography needs exactly 4 correspondences')
    A = np.zeros((8, 8), dtype=np.float64)
    b = np.zeros(8, dtype=np.float64)
    for i in range(4):
        x, y = src[i]
        u, v = dst[i]
        A[2 * i] = [x, y, 1, 0, 0, 0, -u * x, -u * y]
        A[2 * i + 1] = [0, 0, 0, x, y, 1, -v * x, -v * y]
        b[2 * i] = u
        b[2 * i + 1] = v
    try:
        h = np.linalg.solve(A, b)
    except np.linalg.LinAlgError:
        raise ScanError('registration markers are degenerate (collinear?)')
    return np.append(h, 1.0).reshape(3, 3)


def warp(gray: np.ndarray, H: np.ndarray, out_w: int, out_h: int) -> np.ndarray:
    """Perspective-correct `gray` into an (out_h, out_w) canonical raster.

    Inverse mapping + bilinear resampling. This is what turns an angled phone
    photo into a flat sheet; cropping alone would leave the bubble grid sheared
    and every sample would drift off-centre towards the far edge of the page.
    """
    Hinv = np.linalg.inv(H)
    ys, xs = np.mgrid[0:out_h, 0:out_w]
    ones = np.ones_like(xs, dtype=np.float64)
    pts = np.stack([xs.ravel(), ys.ravel(), ones.ravel()])       # 3 x N
    src = Hinv @ pts
    w = src[2]
    w[np.abs(w) < 1e-12] = 1e-12
    sx = (src[0] / w).reshape(out_h, out_w)
    sy = (src[1] / w).reshape(out_h, out_w)

    h_in, w_in = gray.shape
    x0 = np.floor(sx).astype(np.int64)
    y0 = np.floor(sy).astype(np.int64)
    fx = sx - x0
    fy = sy - y0

    x0c = np.clip(x0, 0, w_in - 1)
    x1c = np.clip(x0 + 1, 0, w_in - 1)
    y0c = np.clip(y0, 0, h_in - 1)
    y1c = np.clip(y0 + 1, 0, h_in - 1)

    out = (gray[y0c, x0c] * (1 - fx) * (1 - fy) +
           gray[y0c, x1c] * fx * (1 - fy) +
           gray[y1c, x0c] * (1 - fx) * fy +
           gray[y1c, x1c] * fx * fy)

    # anything sampled from outside the source is paper, not ink
    oob = (sx < -1) | (sx > w_in) | (sy < -1) | (sy > h_in)
    out[oob] = 255.0
    return out.astype(np.float32)


# ── sampling ──────────────────────────────────────────────────────────────────

def _disc_offsets(radius: float) -> Tuple[np.ndarray, np.ndarray]:
    r = int(np.ceil(radius))
    dy, dx = np.mgrid[-r:r + 1, -r:r + 1]
    keep = (dx * dx + dy * dy) <= radius * radius
    return dy[keep], dx[keep]


def disc_mean(img: np.ndarray, cx: float, cy: float, radius: float) -> float:
    """Mean intensity over a disc. Used for bubbles (and code modules)."""
    h, w = img.shape
    dy, dx = _disc_offsets(radius)
    ys = np.clip(np.rint(cy).astype(int) + dy, 0, h - 1)
    xs = np.clip(np.rint(cx).astype(int) + dx, 0, w - 1)
    return float(img[ys, xs].mean())


def rect_median(img: np.ndarray, cx: float, cy: float, half_w: float, half_h: float) -> float:
    h, w = img.shape
    x0 = int(max(0, np.floor(cx - half_w)))
    x1 = int(min(w, np.ceil(cx + half_w) + 1))
    y0 = int(max(0, np.floor(cy - half_h)))
    y1 = int(min(h, np.ceil(cy + half_h) + 1))
    if x1 <= x0 or y1 <= y0:
        return float(img[int(np.clip(cy, 0, h - 1)), int(np.clip(cx, 0, w - 1))])
    return float(np.median(img[y0:y1, x0:x1]))
