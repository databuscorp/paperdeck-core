"""Font-independent text for the svgwrite-based renderers (physics, chemistry, circuits).

Unicode sub/superscripts (m₁, Zn²⁺, V₀) cannot be trusted to a font. Arial carries no
U+2080–2089 at all, and cairosvg — the rasterizer behind the PNG/PDF print path — does not
fall back per glyph the way a browser does. The result is `m□` on the printed paper while
the same SVG looks perfect in the web UI, so the corruption only ever surfaces on the
artifact a student is handed.

The fix is to stop depending on font coverage: strip the exotic codepoints and re-create the
sub/superscript with a shifted <tspan> carrying an ordinary ASCII digit, which every font has.
Typography is preserved (physics papers want a real subscript on m₁, not "m1") and the output
no longer varies with whichever fonts happen to be installed on the host.
"""
from __future__ import annotations

from typing import Iterator, List, Tuple

import svgwrite

_SUBSCRIPT = {
    "₀": "0", "₁": "1", "₂": "2", "₃": "3", "₄": "4",
    "₅": "5", "₆": "6", "₇": "7", "₈": "8", "₉": "9",
    "₊": "+", "₋": "-", "₌": "=", "₍": "(", "₎": ")",
    "ₐ": "a", "ₑ": "e", "ₒ": "o", "ₓ": "x", "ₙ": "n", "ᵢ": "i", "ⱼ": "j",
}

_SUPERSCRIPT = {
    "⁰": "0", "¹": "1", "²": "2", "³": "3", "⁴": "4",
    "⁵": "5", "⁶": "6", "⁷": "7", "⁸": "8", "⁹": "9",
    "⁺": "+", "⁻": "-", "⁼": "=", "⁽": "(", "⁾": ")", "ⁿ": "n", "ᵐ": "m",
}

# Baseline offset as a fraction of the font size. Applied as a <tspan dy>, which is relative
# to the *previous* tspan — so returning to the base line needs the opposite shift, and the
# shifts must be tracked cumulatively rather than emitted per segment.
_BASELINE = {"base": 0.0, "sub": 0.30, "sup": -0.42}
_SCALE = {"base": 1.0, "sub": 0.72, "sup": 0.72}


def _segments(txt: str) -> Iterator[Tuple[str, str]]:
    """Split text into (chunk, kind) runs, kind ∈ {base, sub, sup}."""
    buf: List[str] = []
    kind = "base"
    for ch in txt:
        if ch in _SUBSCRIPT:
            ch_kind, ch = "sub", _SUBSCRIPT[ch]
        elif ch in _SUPERSCRIPT:
            ch_kind, ch = "sup", _SUPERSCRIPT[ch]
        else:
            ch_kind = "base"
        if ch_kind != kind and buf:
            yield "".join(buf), kind
            buf = []
        kind = ch_kind
        buf.append(ch)
    if buf:
        yield "".join(buf), kind


def has_special(txt: str) -> bool:
    return any(c in _SUBSCRIPT or c in _SUPERSCRIPT for c in txt)


def fold(txt: str) -> str:
    """Flatten to pure ASCII (m₁ → m1). For contexts that cannot carry tspans."""
    return "".join(_SUBSCRIPT.get(c, _SUPERSCRIPT.get(c, c)) for c in txt)


def tspan_markup(txt: str, font_size: int) -> str:
    """Same transform, emitted as raw XML — for SVG assembled as a string rather than
    through svgwrite (e.g. the compound-name label injected into RDKit's output)."""
    from xml.sax.saxutils import escape
    if not has_special(txt):
        return escape(txt)
    parts, current = [], 0.0
    for chunk, kind in _segments(txt):
        target = _BASELINE[kind] * font_size
        parts.append(
            f'<tspan dy="{round(target - current, 2)}" '
            f'font-size="{round(font_size * _SCALE[kind], 1)}px">{escape(chunk)}</tspan>'
        )
        current = target
    return "".join(parts)


def make_text(dwg: svgwrite.Drawing, txt: str, insert, *, font_size: int,
              font_family: str, text_anchor: str = "middle",
              font_weight: str = "normal", fill: str = "black"):
    """Build an svgwrite <text> whose sub/superscripts survive rasterization."""
    text = dwg.text("", insert=insert, font_size=font_size, font_family=font_family,
                    text_anchor=text_anchor, font_weight=font_weight, fill=fill)
    if not has_special(txt):
        text.add(dwg.tspan(txt))
        return text

    current = 0.0
    for chunk, kind in _segments(txt):
        target = _BASELINE[kind] * font_size
        text.add(dwg.tspan(
            chunk,
            dy=[round(target - current, 2)],
            font_size=f"{round(font_size * _SCALE[kind], 1)}px",
        ))
        current = target
    return text
