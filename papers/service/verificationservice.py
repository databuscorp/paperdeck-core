"""
Answer-key verification for AI-generated questions.

A wrong answer key destroys trust faster than any other defect, and a model asked
"is this right?" about its own output will almost always say yes. So verification
here never shows the model its own key:

    1. BLIND SOLVE   — a solver pass sees only the question + options and must
                       solve it from scratch and commit to an answer.
    2. COMPARE       — solver's choice vs. the generator's key.
    3. ADJUDICATE    — disagreements go to a stronger model that solves step by
                       step. If the adjudicator sides with the blind solver, the
                       key was wrong and we fix it. If it sides with the key, the
                       key stands.
    4. FLAG          — anything still unresolved is marked for human review rather
                       than silently shipped.

Numeric answers are additionally cross-checked with SymPy, so "2.5" / "5/2" /
"$\\frac{5}{2}$" all compare equal instead of failing on formatting.

Every question comes back with a `verification` field:
    verified   — blind solver independently agreed with the key
    corrected  — key was wrong and has been fixed (see verification_note)
    flagged    — could not be confirmed; needs a human (see verification_note)
    skipped    — not auto-verifiable (e.g. long-answer, no options)
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

VERIFIED = "verified"
CORRECTED = "corrected"
FLAGGED = "flagged"
SKIPPED = "skipped"

# Questions are solved in groups — one call per group keeps token cost sane while
# staying well inside the output budget.
_SOLVE_GROUP_SIZE = 5


# ── Numeric comparison (SymPy) ────────────────────────────────────────────────

_NUM_CLEAN_RE = re.compile(r"[$\\]|\\text\{[^}]*\}|[a-zA-Z°%]+\s*$")


def _to_number(text: str) -> Optional[float]:
    """Best-effort parse of an option/answer string into a float.

    Handles plain numbers, fractions ("5/2"), LaTeX fractions, scientific notation
    and trailing units. Returns None when the value isn't numeric — callers then
    fall back to comparing option indices.
    """
    if text is None:
        return None
    s = str(text).strip()
    if not s:
        return None

    # Strip a leading "A)" / "(b)" / "3." option marker.
    s = re.sub(r"^\(?[A-Da-d][\).]\s*", "", s)
    # LaTeX fraction → plain fraction.
    m = re.search(r"\\d?frac\{([^}]*)\}\{([^}]*)\}", s)
    if m:
        s = f"({m.group(1)})/({m.group(2)})"
    # Drop math delimiters, \text{...} unit wrappers, and trailing unit words.
    s = s.replace("$", "").replace("\\,", " ")
    s = re.sub(r"\\text\{([^}]*)\}", r" ", s)
    s = re.sub(r"\\times\s*10\^\{?(-?\d+)\}?", r"e\1", s)   # 3\times10^{-2} → 3e-2
    s = re.sub(r"\\[a-zA-Z]+", " ", s)                      # remaining LaTeX cmds
    s = s.replace("^", "**").replace("×", "*")
    # Keep only the leading numeric expression; drop trailing units like "m/s^2".
    m = re.match(r"^\s*[-+]?[\d\.\(\)/\*\se\+\-]+", s)
    if not m:
        return None
    expr = m.group(0).strip().rstrip("*/+-e")
    if not expr or not re.search(r"\d", expr):
        return None
    try:
        from sympy import sympify
        val = sympify(expr, rational=False)
        return float(val)
    except Exception:
        return None


def _numbers_match(a: Optional[float], b: Optional[float], rel_tol: float = 0.02) -> bool:
    """Compare two numeric answers with a 2% relative tolerance (rounding in
    intermediate steps is normal in exam solutions)."""
    if a is None or b is None:
        return False
    if a == b:
        return True
    scale = max(abs(a), abs(b))
    if scale == 0:
        return abs(a - b) < 1e-9
    return abs(a - b) / scale <= rel_tol


def _key_index(q: Dict[str, Any]) -> Optional[int]:
    """Index of the option currently marked correct, or None."""
    opts = q.get("options")
    if not isinstance(opts, list):
        return None
    for i, o in enumerate(opts):
        if isinstance(o, dict) and o.get("correct"):
            return i
    return None


def _set_key(q: Dict[str, Any], idx: int) -> None:
    """Move the correct flag to `idx` (exactly one correct option)."""
    opts = q.get("options") or []
    for i, o in enumerate(opts):
        if isinstance(o, dict):
            o["correct"] = (i == idx)


def _opt_texts(q: Dict[str, Any]) -> List[str]:
    return [
        (o.get("text", "") if isinstance(o, dict) else str(o))
        for o in (q.get("options") or [])
    ]


def _verifiable(q: Dict[str, Any]) -> bool:
    """Only single-correct MCQ-shaped questions can be auto-verified this way."""
    opts = q.get("options")
    if not isinstance(opts, list) or len(opts) < 2:
        return False
    return _key_index(q) is not None


def _numeric_key(q: Dict[str, Any]) -> Optional[float]:
    """The keyed numeric answer as a float, or None if absent/unparseable."""
    if "numeric_answer" not in q or q.get("numeric_answer") is None:
        return None
    val = q.get("numeric_answer")
    if isinstance(val, (int, float)):
        return float(val)
    return _to_number(str(val))


def _verifiable_numeric(q: Dict[str, Any]) -> bool:
    """A Numerical question carries a numeric key but no options to index into.

    These were previously skipped entirely — a wrong numeric key is just as damaging as a
    wrong MCQ key, so they get their own blind-solve path (see AnswerVerifier._verify_numeric).
    Questions that ALSO have options go down the MCQ path instead (checked by the caller).
    """
    return _numeric_key(q) is not None


# ── Verifier ──────────────────────────────────────────────────────────────────

class AnswerVerifier:
    """Verifies answer keys via blind re-solve + adjudication.

    Uses the caller's Anthropic client (so token usage keeps accruing into the
    caller's `last_usage` for credit metering).
    """

    def __init__(self, client, solver_model: str, adjudicator_model: str,
                 usage_sink=None):
        self._client = client
        self._solver_model = solver_model
        self._adjudicator_model = adjudicator_model
        self._usage_sink = usage_sink   # callable(message) → accumulates tokens

    def _call(self, model: str, prompt: str, max_tokens: int) -> str:
        message = self._client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        if self._usage_sink:
            self._usage_sink(message)
        return (message.content[0].text or "").strip()

    # ── public entry point ────────────────────────────────────────────────────

    def verify(self, questions: List[Dict[str, Any]], subject: str = "",
               exam: str = "") -> List[Dict[str, Any]]:
        """Verify (and where possible correct) the answer keys. Mutates in place."""
        if not self._client or not questions:
            for q in questions or []:
                q.setdefault("verification", SKIPPED)
            return questions

        # MCQ questions verify by option index; Numerical questions (a numeric key, no
        # options) verify by computed value. Anything that is neither is skipped.
        mcq_targets = [q for q in questions if _verifiable(q)]
        num_targets = [q for q in questions
                       if q not in mcq_targets and _verifiable_numeric(q)]
        targets = mcq_targets + num_targets
        for q in questions:
            if q not in targets:
                q["verification"] = SKIPPED
        if not targets:
            return questions

        if mcq_targets:
            self._verify_mcq(mcq_targets, subject, exam)
        if num_targets:
            self._verify_numeric(num_targets, subject, exam)

        n_ok = sum(1 for q in targets if q.get("verification") == VERIFIED)
        n_fix = sum(1 for q in targets if q.get("verification") == CORRECTED)
        n_flag = sum(1 for q in targets if q.get("verification") == FLAGGED)
        logger.info("Answer verification [%s/%s]: %d verified, %d corrected, %d flagged "
                    "(of %d — %d MCQ, %d numeric)", exam or "?", subject or "?",
                    n_ok, n_fix, n_flag, len(targets), len(mcq_targets), len(num_targets))
        return questions

    def _verify_mcq(self, targets: List[Dict[str, Any]], subject: str, exam: str) -> None:
        """Blind-solve MCQ targets by option index and adjudicate disagreements."""
        solved = self._blind_solve(targets, subject, exam)

        disputes = []
        for i, q in enumerate(targets):
            answer = solved.get(i)
            if answer is None:
                q["verification"] = FLAGGED
                q["verification_note"] = "Independent solver did not return an answer."
                continue

            key = _key_index(q)
            if self._agrees(q, key, answer):
                q["verification"] = VERIFIED
            else:
                disputes.append((q, key, answer))

        if disputes:
            self._adjudicate(disputes, subject, exam)

    # ── step 1: blind solve ───────────────────────────────────────────────────

    def _agrees(self, q: Dict[str, Any], key: Optional[int], answer: Dict) -> bool:
        """Solver agrees with the key by option index, or by numeric value.

        The numeric path matters: a solver can compute the right value but cite the
        wrong letter (or the options may be reordered), and conversely two options
        can be textually different but numerically equal.
        """
        idx = answer.get("option_index")
        if idx is not None and idx == key:
            return True
        # Numeric cross-check: does the solver's computed value match the keyed option?
        solver_val = _to_number(answer.get("final_answer"))
        if solver_val is not None and key is not None:
            texts = _opt_texts(q)
            if key < len(texts) and _numbers_match(solver_val, _to_number(texts[key])):
                return True
        return False

    def _blind_solve(self, questions: List[Dict[str, Any]], subject: str,
                     exam: str) -> Dict[int, Dict]:
        """Solve each question from scratch, WITHOUT ever showing the key."""
        results: Dict[int, Dict] = {}
        for start in range(0, len(questions), _SOLVE_GROUP_SIZE):
            group = questions[start:start + _SOLVE_GROUP_SIZE]
            payload = []
            for i, q in enumerate(group):
                payload.append({
                    "index": start + i,
                    "question": q.get("text", ""),
                    # Options are sent WITHOUT the `correct` flag — this is the whole point.
                    "options": [
                        {"index": j, "text": t} for j, t in enumerate(_opt_texts(q))
                    ],
                })

            prompt = f"""You are an expert {subject or 'science'} examiner for the {exam or 'competitive'} exam.
Solve each question below from first principles. You are NOT told the answer — work it out.

For each question: reason through it, then commit to exactly one option.

Questions:
{json.dumps(payload, ensure_ascii=False, indent=1)}

Return ONLY a JSON array, one element per question, no markdown:
[{{"index": <the index given above>,
   "option_index": <0-based index of the option you believe is correct>,
   "final_answer": "<your computed answer as a bare value, e.g. '9.8' or '5/2'; use '' if not numeric>",
   "confidence": "high|medium|low"}}]"""
            try:
                raw = self._call(self._solver_model, prompt, max_tokens=4096)
                for item in _parse_json_array(raw):
                    if isinstance(item, dict) and isinstance(item.get("index"), int):
                        results[item["index"]] = item
            except Exception:
                logger.exception("Blind solve pass failed for a group; those questions are flagged")
        return results

    # ── step 2: adjudicate disagreements ──────────────────────────────────────

    def _adjudicate(self, disputes: List, subject: str, exam: str) -> None:
        """A stronger model settles solver-vs-key disagreements by solving carefully."""
        for q, key, answer in disputes:
            texts = _opt_texts(q)
            try:
                raw = self._call(self._adjudicator_model, f"""You are a senior {subject or 'science'} professor setting a {exam or 'competitive'} exam.
Solve this question rigorously, step by step. Two sources disagree on the answer,
so your solution must be independent and careful.

QUESTION:
{q.get('text', '')}

OPTIONS:
{json.dumps([{'index': i, 'text': t} for i, t in enumerate(texts)], ensure_ascii=False, indent=1)}

Work the problem, then answer. If the question is flawed (no correct option, more
than one correct option, ambiguous, or missing information), say so instead of
forcing a choice.

Return ONLY JSON, no markdown:
{{"option_index": <0-based correct option, or null if the question is flawed>,
  "final_answer": "<computed value, or ''>",
  "flawed": <true|false>,
  "reason": "<one sentence>"}}""", max_tokens=2048)
                verdict = _parse_json_object(raw)
            except Exception:
                logger.exception("Adjudication call failed")
                verdict = None

            if not verdict:
                q["verification"] = FLAGGED
                q["verification_note"] = "Solver disagreed with the key and adjudication failed."
                continue

            if verdict.get("flawed") or verdict.get("option_index") is None:
                q["verification"] = FLAGGED
                q["verification_note"] = (
                    f"Question may be flawed: {verdict.get('reason', 'no reason given')}"
                )
                continue

            adj_idx = verdict.get("option_index")
            if not isinstance(adj_idx, int) or not (0 <= adj_idx < len(texts)):
                q["verification"] = FLAGGED
                q["verification_note"] = "Adjudicator returned an out-of-range option."
                continue

            solver_idx = answer.get("option_index")
            if adj_idx == key:
                # Adjudicator sided with the original key — the blind solver was wrong.
                q["verification"] = VERIFIED
            elif adj_idx == solver_idx:
                # Two independent solves agree against the key → the key was wrong.
                old = texts[key] if key is not None and key < len(texts) else "?"
                _set_key(q, adj_idx)
                q["verification"] = CORRECTED
                q["verification_note"] = (
                    f"Answer key corrected from option {key} ({old!r}) to option "
                    f"{adj_idx} ({texts[adj_idx]!r}): {verdict.get('reason', '')}".strip()
                )
            else:
                # Three-way disagreement — no confident resolution.
                q["verification"] = FLAGGED
                q["verification_note"] = (
                    f"Unresolved: key=option {key}, solver=option {solver_idx}, "
                    f"adjudicator=option {adj_idx}. Needs human review."
                )

    # ── numeric verification (blind solve by VALUE, not option index) ─────────

    def _verify_numeric(self, targets: List[Dict[str, Any]], subject: str, exam: str) -> None:
        """Blind-solve Numerical targets and adjudicate value mismatches."""
        solved = self._blind_solve_numeric(targets, subject, exam)

        disputes = []
        for i, q in enumerate(targets):
            solver_val = solved.get(i)
            if solver_val is None:
                q["verification"] = FLAGGED
                q["verification_note"] = "Independent solver did not return a numeric answer."
                continue
            if _numbers_match(solver_val, _numeric_key(q)):
                q["verification"] = VERIFIED
            else:
                disputes.append((q, solver_val))

        if disputes:
            self._adjudicate_numeric(disputes, subject, exam)

    def _blind_solve_numeric(self, questions: List[Dict[str, Any]], subject: str,
                             exam: str) -> Dict[int, float]:
        """Solve each numeric question from scratch, WITHOUT ever showing the key."""
        results: Dict[int, float] = {}
        for start in range(0, len(questions), _SOLVE_GROUP_SIZE):
            group = questions[start:start + _SOLVE_GROUP_SIZE]
            payload = [
                {"index": start + i, "question": q.get("text", ""),
                 "expected_unit": q.get("unit", "")}
                for i, q in enumerate(group)
            ]
            prompt = f"""You are an expert {subject or 'science'} examiner for the {exam or 'competitive'} exam.
Solve each numerical question below from first principles. You are NOT told the answer —
compute it. Give the answer as a bare number in the question's expected unit (no unit text,
no working), using a decimal (e.g. 9.8, 0.045, 6.02e23).

Questions:
{json.dumps(payload, ensure_ascii=False, indent=1)}

Return ONLY a JSON array, one element per question, no markdown:
[{{"index": <the index given above>,
   "value": <your computed numeric answer as a number>,
   "confidence": "high|medium|low"}}]"""
            try:
                raw = self._call(self._solver_model, prompt, max_tokens=4096)
                for item in _parse_json_array(raw):
                    if isinstance(item, dict) and isinstance(item.get("index"), int):
                        val = _to_number(str(item.get("value")))
                        if val is not None:
                            results[item["index"]] = val
            except Exception:
                logger.exception("Numeric blind solve failed for a group; those questions are flagged")
        return results

    def _adjudicate_numeric(self, disputes: List, subject: str, exam: str) -> None:
        """A stronger model settles solver-vs-key numeric disagreements."""
        for q, solver_val in disputes:
            key_val = _numeric_key(q)
            try:
                raw = self._call(self._adjudicator_model, f"""You are a senior {subject or 'science'} professor setting a {exam or 'competitive'} exam.
Solve this numerical question rigorously, step by step. Two sources disagree on the answer,
so your solution must be independent and careful.

QUESTION:
{q.get('text', '')}

Expected unit: {q.get('unit', '') or '(dimensionless)'}

Work the problem, then give the final numeric value in that unit. If the question is flawed
(missing information, contradictory data, or no well-defined numeric answer), say so instead
of forcing a number.

Return ONLY JSON, no markdown:
{{"value": <final numeric answer as a number, or null if the question is flawed>,
  "flawed": <true|false>,
  "reason": "<one sentence>"}}""", max_tokens=2048)
                verdict = _parse_json_object(raw)
            except Exception:
                logger.exception("Numeric adjudication call failed")
                verdict = None

            if not verdict:
                q["verification"] = FLAGGED
                q["verification_note"] = "Solver disagreed with the key and adjudication failed."
                continue

            if verdict.get("flawed") or verdict.get("value") is None:
                q["verification"] = FLAGGED
                q["verification_note"] = (
                    f"Question may be flawed: {verdict.get('reason', 'no reason given')}"
                )
                continue

            adj_val = _to_number(str(verdict.get("value")))
            if adj_val is None:
                q["verification"] = FLAGGED
                q["verification_note"] = "Adjudicator returned a non-numeric answer."
                continue

            if _numbers_match(adj_val, key_val):
                # Adjudicator sided with the original key — the blind solver was wrong.
                q["verification"] = VERIFIED
            elif _numbers_match(adj_val, solver_val):
                # Two independent solves agree against the key → the key was wrong.
                q["numeric_answer"] = _tidy_number(adj_val)
                q["verification"] = CORRECTED
                q["verification_note"] = (
                    f"Numeric answer key corrected from {key_val} to "
                    f"{q['numeric_answer']}: {verdict.get('reason', '')}".strip()
                )
            else:
                # Three-way disagreement — no confident resolution.
                q["verification"] = FLAGGED
                q["verification_note"] = (
                    f"Unresolved: key={key_val}, solver={solver_val}, "
                    f"adjudicator={adj_val}. Needs human review."
                )


# ── JSON helpers (models sometimes wrap output in prose/fences) ───────────────


def _tidy_number(v: float):
    """Present a corrected numeric answer without float noise: whole values as ints."""
    if v == int(v):
        return int(v)
    return round(v, 6)

def _parse_json_array(raw: str) -> List:
    s, e = raw.find("["), raw.rfind("]")
    if s == -1 or e <= s:
        return []
    try:
        data = json.loads(raw[s:e + 1])
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _parse_json_object(raw: str) -> Optional[Dict]:
    s, e = raw.find("{"), raw.rfind("}")
    if s == -1 or e <= s:
        return None
    try:
        data = json.loads(raw[s:e + 1])
        return data if isinstance(data, dict) else None
    except Exception:
        return None
