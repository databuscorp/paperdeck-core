"""
Field-level validation and repair for AI-generated questions.

The generator used to accept whatever JSON came back: an MCQ with three options,
two options both flagged correct, `difficulty: "very hard"`, a missing `marks` —
all of it persisted silently and surfaced as a broken question in front of a class.

This module is the gate. Anything structurally repairable is repaired (enums are
snapped to the closest legal value, marks are defaulted); anything that cannot be
trusted — an MCQ with no correct option, no options at all, empty text — is
rejected so the caller can regenerate it rather than ship it.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)

DIFFICULTIES = ["Easy", "Medium", "Hard", "HOTS"]
BLOOMS = ["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"]

# Question types whose answers live in `options`.
OPTION_TYPES = {"MCQ", "Image Based", "Assertion Reason", "Multiple Correct"}
# Exactly one option must be correct for these; Multiple Correct allows 2+.
SINGLE_CORRECT_TYPES = OPTION_TYPES - {"Multiple Correct"}

MIN_OPTIONS = 4


def _snap(value: Any, allowed: List[str], default: str) -> str:
    """Snap a free-text enum to the closest legal value (case/space insensitive)."""
    if not isinstance(value, str):
        return default
    v = value.strip().lower()
    for a in allowed:
        if a.lower() == v:
            return a
    # Tolerate near-misses like "analyse" / "very hard" / "medium-hard".
    for a in allowed:
        if a.lower().startswith(v[:4]) or v.startswith(a.lower()[:4]):
            return a
    return default


def validate_question(q: Dict[str, Any], q_type: str) -> Tuple[bool, List[str]]:
    """Repair `q` in place where safe. Returns (is_usable, problems).

    `problems` is always populated when something was wrong, even if it was repaired,
    so callers can log what the model got wrong.
    """
    problems: List[str] = []

    if not isinstance(q, dict):
        return False, ["not an object"]

    text = (q.get("text") or "").strip()
    if not text:
        return False, ["empty question text"]
    q["text"] = text

    # ── enums: repairable ─────────────────────────────────────────────────────
    d = _snap(q.get("difficulty"), DIFFICULTIES, "Medium")
    if d != q.get("difficulty"):
        problems.append(f"difficulty {q.get('difficulty')!r} → {d!r}")
    q["difficulty"] = d

    b = _snap(q.get("bloom"), BLOOMS, "Apply")
    if b != q.get("bloom"):
        problems.append(f"bloom {q.get('bloom')!r} → {b!r}")
    q["bloom"] = b

    try:
        marks = float(q.get("marks"))
        if marks <= 0:
            raise ValueError
        q["marks"] = int(marks) if marks == int(marks) else marks
    except (TypeError, ValueError):
        problems.append(f"marks {q.get('marks')!r} → 4")
        q["marks"] = 4

    # ── options ───────────────────────────────────────────────────────────────
    if q_type not in OPTION_TYPES:
        q["options"] = None
        return True, problems

    opts = q.get("options")
    if not isinstance(opts, list) or len(opts) < 2:
        return False, problems + [f"{q_type} needs options, got {type(opts).__name__}"]

    clean: List[Dict[str, Any]] = []
    for o in opts:
        rationale = ""
        if isinstance(o, dict):
            otext = (o.get("text") or "").strip()
            correct = bool(o.get("correct"))
            # Carry the distractor rationale through. This used to rebuild the option
            # as {text, correct} only, which silently DROPPED every other field — the
            # model was emitting the rationale and the validator was discarding it, so
            # the field looked like the model ignoring it. Any new option field has to
            # be forwarded here or it dies the same quiet death.
            rationale = (o.get("rationale") or "").strip()
        else:
            otext, correct = str(o).strip(), False
        if otext:
            option: Dict[str, Any] = {"text": otext, "correct": correct}
            if rationale:
                option["rationale"] = rationale
            clean.append(option)

    if len(clean) < MIN_OPTIONS:
        return False, problems + [f"{q_type} needs {MIN_OPTIONS} options, got {len(clean)}"]

    n_correct = sum(1 for o in clean if o["correct"])
    if n_correct == 0:
        # No key at all — unusable. Verification can fix a WRONG key, but it cannot
        # invent one we'd have any reason to trust.
        return False, problems + ["no option marked correct"]

    if q_type in SINGLE_CORRECT_TYPES and n_correct > 1:
        return False, problems + [f"{q_type} has {n_correct} correct options, expected 1"]

    if q_type == "Multiple Correct" and n_correct == len(clean):
        return False, problems + ["every option marked correct"]

    q["options"] = clean
    return True, problems


def validate_batch(questions: List[Dict[str, Any]], q_type: str) -> List[Dict[str, Any]]:
    """Drop unusable questions, repair the rest. Returns the usable ones."""
    usable = []
    for q in questions or []:
        ok, problems = validate_question(q, q_type)
        if problems:
            logger.info("Question validation [%s]: %s (%s)",
                        q_type, "; ".join(problems), "kept" if ok else "DROPPED")
        if ok:
            usable.append(q)
    dropped = len(questions or []) - len(usable)
    if dropped:
        logger.warning("Dropped %d/%d invalid %s questions from batch",
                       dropped, len(questions or []), q_type)
    return usable
