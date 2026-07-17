"""
Visual verification for AI-generated diagrams.

The generation pipeline already guarantees a diagram *renders* (schema → validate →
render → repair). But "it rendered" is not "it is correct". A schema can be perfectly
valid and still draw the wrong thing: a ray diagram with the arrow pointing the wrong
way, a labelled part hidden behind a shape, values in the figure that contradict the
question stem, or simply a figure that answers a different question than the one asked.
None of that is catchable by the deterministic renderer — the pixels are self-consistent;
they just don't match intent.

This is the visual analogue of blind-solve answer verification (see verificationservice):
we render the figure to an image and hand it, together with the question a student would
read, to a vision model acting as an adversarial proofreader. It is asked to *find defects*,
not to bless the figure — a model asked "is this right?" says yes, so the framing is
"list everything wrong with this figure for this question". The schema is deliberately NOT
shown: the verifier judges the figure the way a student sees it (question + options +
picture), so a schema whose params look plausible but render wrong is still caught.

A verdict is one of:
    clean    — no defects; ship as-is
    minor    — cosmetic issues recorded on the question but not blocking
    major    — the figure is wrong/misleading for this question; caller repairs or regenerates

Verification never *loses* a question: any error (no vision support, rasterisation failure,
API error, unparseable verdict) degrades to `skipped`, and the figure ships as the render
pipeline produced it. The guarantee this adds is one-directional — it can reject a bad
figure, never manufacture a worse one.

Tokens accrue into the caller's usage sink (same client, same `last_usage`) so the credit
meter already bills this exactly like the answer verifier.
"""
from __future__ import annotations

import base64
import logging
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

CLEAN = "clean"
MINOR = "minor"
MAJOR = "major"
SKIPPED = "skipped"

# The rasterised figure sent to the vision model. Wide enough that labels are legible to
# the model, small enough to keep image-input tokens modest (Anthropic bills vision at
# roughly (w×h)/750 tokens, so ~720px keeps a typical figure well under ~1k image tokens).
_RASTER_WIDTH = 720

# Forced-schema verdict. Tool-use, not text parsing — same principle as the generator:
# the API rejects a malformed verdict server-side instead of us guessing at prose.
_VERDICT_TOOL = {
    "name": "report_diagram_defects",
    "description": (
        "Report defects found in a diagram rendered for an exam question. "
        "Report ONLY genuine defects that would confuse or mislead a student; do not "
        "invent problems to seem thorough."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "severity": {
                "type": "string",
                "enum": [CLEAN, MINOR, MAJOR],
                "description": (
                    "clean = the figure correctly and unambiguously depicts what this "
                    "question needs, with no defects. "
                    "minor = usable but has cosmetic flaws (slight overlap, imperfect "
                    "spacing) that do not change what a student concludes. "
                    "major = the figure is wrong or misleading FOR THIS QUESTION: it shows "
                    "the wrong object/scenario, an essential element or label is missing or "
                    "unreadable, a value/orientation/direction contradicts the stem, or the "
                    "figure is blank/degenerate."
                ),
            },
            "defects": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "Each defect as one concrete, specific sentence naming what is wrong and "
                    "where (e.g. 'the angle label 30° sits on top of the arc and is "
                    "unreadable', not 'labels could be clearer'). Empty when severity=clean."
                ),
            },
            "fix_hint": {
                "type": "string",
                "description": (
                    "One imperative sentence telling the schema author what to change to fix "
                    "the MAJOR defect (e.g. 'reverse the velocity arrow to point toward the "
                    "centre'). Empty unless severity=major."
                ),
            },
        },
        "required": ["severity", "defects"],
    },
}


def _svg_to_png_b64(svg: str, *, width: int = _RASTER_WIDTH) -> Optional[str]:
    """Rasterise SVG to a base64 PNG for the vision API, or None if unavailable.

    Broad except on purpose: when cairosvg is installed but the native cairo library is
    not findable, cairocffi raises OSError (not ImportError). A rasterisation failure must
    never take down generation — it just skips verification for that figure.
    """
    if not svg:
        return None
    try:
        import cairosvg
        png = cairosvg.svg2png(
            bytestring=svg.encode("utf-8"),
            output_width=width,
            background_color="white",  # figures assume paper-white; transparent confuses the model
        )
        return base64.b64encode(png).decode("ascii")
    except Exception:
        logger.warning("Could not rasterise SVG for visual verification — skipping", exc_info=True)
        return None


class DiagramVerifier:
    """Verifies that a rendered figure actually matches its question, via a vision model.

    Uses the caller's Anthropic client so token usage keeps accruing into the caller's
    `last_usage` for credit metering (see AnswerVerifier for the same contract).
    """

    def __init__(self, client, model: str, usage_sink: Optional[Callable] = None):
        self._client = client
        self._model = model
        self._usage_sink = usage_sink

    def verify(self, question: Dict[str, Any], subject: str = "",
               exam: str = "") -> Dict[str, Any]:
        """Return a verdict dict for a single question's rendered figure.

        Verdict shape: {"severity": clean|minor|major|skipped,
                        "defects": [...], "fix_hint": "..."}.
        Never raises — any failure degrades to a `skipped` verdict.
        """
        svg = question.get("image_svg")
        if not self._client or not svg:
            return {"severity": SKIPPED, "defects": [], "fix_hint": ""}

        img_b64 = _svg_to_png_b64(svg)
        if not img_b64:
            return {"severity": SKIPPED, "defects": [], "fix_hint": ""}

        try:
            message = self._client.messages.create(
                model=self._model,
                max_tokens=1024,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": img_b64,
                            },
                        },
                        {"type": "text", "text": self._prompt(question, subject, exam)},
                    ],
                }],
                tools=[_VERDICT_TOOL],
                tool_choice={"type": "tool", "name": _VERDICT_TOOL["name"]},
            )
        except Exception:
            logger.exception("Diagram visual verification call failed — figure ships unverified")
            return {"severity": SKIPPED, "defects": [], "fix_hint": ""}

        if self._usage_sink:
            self._usage_sink(message)

        verdict = self._extract_verdict(message)
        if verdict is None:
            return {"severity": SKIPPED, "defects": [], "fix_hint": ""}
        return verdict

    # ── prompt ────────────────────────────────────────────────────────────────

    @staticmethod
    def _prompt(question: Dict[str, Any], subject: str, exam: str) -> str:
        stem = (question.get("text") or "").strip()
        opts = question.get("options") or []
        opt_lines = "\n".join(
            f"  {chr(65 + i)}) {(o.get('text') if isinstance(o, dict) else str(o)) or ''}"
            for i, o in enumerate(opts)
        )
        options_block = f"\nOPTIONS:\n{opt_lines}\n" if opt_lines else ""
        return f"""You are a meticulous {subject or 'science'} figure proofreader for the {exam or 'competitive'} exam.

Above is the figure that was generated for the exam question below. Your job is to find
DEFECTS — do not assume the figure is correct. Look specifically for:
  • the figure showing a different object/scenario than the question describes,
  • a required element, arrow, axis, or label that is missing, wrong, or reversed,
  • labels overlapping, hidden behind shapes, or unreadable,
  • a numeric value / angle / direction in the figure that contradicts the question,
  • a blank, empty, or degenerate figure.

Judge ONLY against what a student needs to answer this question. Ignore artistic style.
If the figure is genuinely correct and complete for the question, say so (severity=clean).

QUESTION:
{stem or '(no text)'}
{options_block}
Call `report_diagram_defects` with your verdict."""

    # ── verdict extraction ──────────────────────────────────────────────────────

    @staticmethod
    def _extract_verdict(message) -> Optional[Dict[str, Any]]:
        for block in getattr(message, "content", []) or []:
            if getattr(block, "type", None) == "tool_use":
                data = getattr(block, "input", None)
                if not isinstance(data, dict):
                    return None
                severity = data.get("severity")
                if severity not in (CLEAN, MINOR, MAJOR):
                    return None
                defects = data.get("defects")
                defects = [str(d) for d in defects] if isinstance(defects, list) else []
                return {
                    "severity": severity,
                    "defects": defects,
                    "fix_hint": str(data.get("fix_hint") or ""),
                }
        return None
