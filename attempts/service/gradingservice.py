"""Grading — turns raw responses into marks.

GRADING RULES (all decided here, in one place, so an institute can argue with them):

  MCQ / Image Based / Assertion Reason  (single correct)
      correct                 → +marks
      wrong                   → −neg_marks
      blank                   →  0            (status=unattempted, NOT incorrect)

  Multiple Correct  — PARTIAL CREDIT IS ON, and it is PROPORTIONAL:
      exactly the correct set                     → +marks                    (correct)
      a strict subset of correct, no wrong option → +marks × chosen/total     (partial)
      any wrong option selected                   → −neg_marks                (incorrect)
      blank                                       →  0                        (unattempted)
      Rationale: JEE Advanced awards +1 per correct option chosen when no wrong option is
      marked, and full negative for any wrong one. Proportional credit generalizes that to
      any `marks` value without hard-coding JEE's +4/+1. A partial answer is deliberately
      NOT counted as "correct" in item analysis — see itemanalysisservice.

  Numerical / Integer / TITA
      |given − key| ≤ tolerance → +marks, where
          tolerance = max(ABS_TOLERANCE, REL_TOLERANCE × |key|)
      Both an absolute floor and a relative band are needed: a relative-only tolerance
      collapses to zero for a key of 0.0, and an absolute-only one is far too strict for
      an answer like 6.02e23.
      otherwise                 → −neg_marks   (usually 0 — most boards don't penalise TITA)
      blank                     →  0

  Ungradable items (long answer, or a key with no correct option marked) are skipped: they
  score 0, stay `unattempted`, and are EXCLUDED from max_score so they can't silently drag
  every student's percentage down.
"""
from typing import Dict, Optional

from attempts.models import QuestionResponse, StudentAttempt
from attempts.service import answerkey
from attempts.service.answerkey import AnswerKeyItem

# Numerical answers are floats coming off a scan or a text box. 1% relative with a 0.01
# absolute floor accepts 9.79 for g = 9.8 but rejects 9.5.
REL_TOLERANCE = 0.01
ABS_TOLERANCE = 0.01


def numeric_tolerance(key_value: float, rel: float = REL_TOLERANCE, abs_: float = ABS_TOLERANCE) -> float:
    return max(abs_, rel * abs(key_value))


def _is_blank(resp: QuestionResponse, kind: str) -> bool:
    if kind == 'numerical':
        return resp.numeric_answer is None
    if kind == 'multiple':
        idx = resp.selected_option_indices
        if isinstance(idx, list) and len(idx) > 0:
            return False
        # A student may have ticked a single box on a multiple-correct question.
        return resp.selected_option_index is None
    return resp.selected_option_index is None


def _selected_set(resp: QuestionResponse):
    idx = resp.selected_option_indices
    if isinstance(idx, list) and idx:
        return {int(i) for i in idx}
    if resp.selected_option_index is not None:
        return {int(resp.selected_option_index)}
    return set()


def grade_response(resp: QuestionResponse, item: Optional[AnswerKeyItem]) -> QuestionResponse:
    """Score one response in place (does not save). Returns the same object."""
    # No key at all (question deleted, or a long-answer item): leave it ungraded.
    if item is None or not item.is_gradable:
        resp.status = QuestionResponse.STATUS_UNATTEMPTED
        resp.is_correct = None
        resp.marks_awarded = 0.0
        return resp

    kind = item.kind

    if _is_blank(resp, kind):
        resp.status = QuestionResponse.STATUS_UNATTEMPTED
        resp.is_correct = None          # None == "no evidence", not "wrong"
        resp.marks_awarded = 0.0
        return resp

    if kind == 'numerical':
        tol = numeric_tolerance(item.numeric_answer)
        if abs(float(resp.numeric_answer) - float(item.numeric_answer)) <= tol:
            resp.status = QuestionResponse.STATUS_CORRECT
            resp.is_correct = True
            resp.marks_awarded = item.marks
        else:
            resp.status = QuestionResponse.STATUS_INCORRECT
            resp.is_correct = False
            resp.marks_awarded = -item.neg_marks
        return resp

    selected = _selected_set(resp)
    correct = set(item.correct_indices)

    if kind == 'multiple':
        if selected - correct:                       # any wrong option ticked
            resp.status = QuestionResponse.STATUS_INCORRECT
            resp.is_correct = False
            resp.marks_awarded = -item.neg_marks
        elif selected == correct:
            resp.status = QuestionResponse.STATUS_CORRECT
            resp.is_correct = True
            resp.marks_awarded = item.marks
        else:                                        # strict, non-empty subset
            resp.status = QuestionResponse.STATUS_PARTIAL
            resp.is_correct = False                  # partial is not "correct" for item analysis
            resp.marks_awarded = round(item.marks * len(selected) / len(correct), 4)
        return resp

    # single correct
    if selected and selected <= correct:
        resp.status = QuestionResponse.STATUS_CORRECT
        resp.is_correct = True
        resp.marks_awarded = item.marks
    else:
        resp.status = QuestionResponse.STATUS_INCORRECT
        resp.is_correct = False
        resp.marks_awarded = -item.neg_marks
    return resp


def key_for_attempt(attempt: StudentAttempt) -> Dict[str, AnswerKeyItem]:
    if attempt.paper_id:
        return answerkey.build_for_paper(attempt.paper_id)
    q_ids = [r.question_id for r in attempt.responses.all() if r.question_id]
    return answerkey.build_for_questions(q_ids)


def grade_attempt(attempt: StudentAttempt, key: Optional[Dict[str, AnswerKeyItem]] = None) -> StudentAttempt:
    """Grade every response on `attempt`, persist them, and roll up the totals."""
    if key is None:
        key = key_for_attempt(attempt)

    responses = list(attempt.responses.all())
    total = 0.0
    for resp in responses:
        grade_response(resp, key.get(resp.item_key))
        total += resp.marks_awarded

    if responses:
        QuestionResponse.objects.bulk_update(
            responses, ['status', 'is_correct', 'marks_awarded']
        )

    # max_score is the paper's total over gradable items — NOT the sum of what the student
    # happened to answer, otherwise skipping a question would raise your percentage.
    if key:
        max_score = sum(i.marks for i in key.values() if i.is_gradable)
    else:
        max_score = 0.0

    attempt.total_score = round(total, 4)
    attempt.max_score = round(float(max_score), 4)
    attempt.status = StudentAttempt.STATUS_GRADED
    attempt.save(update_fields=['total_score', 'max_score', 'status'])
    return attempt
