"""Builds the answer key for a paper.

A paper's questions live in two places: `PaperQuestion.question` (a row in the bank)
or `PaperQuestion.snapshot` (a JSON blob, for questions that were generated straight
into a paper and never promoted to the bank). Grading has to handle both, so both are
flattened into the same `AnswerKeyItem` here and nothing downstream needs to care.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from papers.models import PaperQuestion


# Question types whose answer is "one of the options".
SINGLE_CORRECT_TYPES   = {'mcq', 'image based', 'assertion reason'}
MULTIPLE_CORRECT_TYPES = {'multiple correct'}
NUMERICAL_TYPES        = {'numerical', 'integer', 'tita'}


@dataclass
class AnswerKeyItem:
    item_key:             str
    question_id:          Optional[int]
    question_snapshot_id: str
    q_type:               str
    marks:                float
    neg_marks:            float          # stored as a POSITIVE magnitude; grading subtracts it
    correct_indices:      List[int] = field(default_factory=list)   # 0-based
    numeric_answer:       Optional[float] = None
    unit:                 str = ''
    text:                 str = ''
    topic:                str = ''
    subject:              str = ''
    difficulty:           str = ''

    @property
    def kind(self) -> str:
        t = (self.q_type or '').strip().lower()
        if t in NUMERICAL_TYPES:
            return 'numerical'
        if t in MULTIPLE_CORRECT_TYPES:
            return 'multiple'
        if t in SINGLE_CORRECT_TYPES:
            return 'single'
        # An unknown type still has a usable key if it has options or a number.
        if self.numeric_answer is not None and not self.correct_indices:
            return 'numerical'
        if len(self.correct_indices) > 1:
            return 'multiple'
        return 'single'

    @property
    def is_gradable(self) -> bool:
        """False for e.g. long-answer questions with no machine-checkable key."""
        if self.kind == 'numerical':
            return self.numeric_answer is not None
        return bool(self.correct_indices)


def _correct_indices(options) -> List[int]:
    """0-based indices of the options flagged `correct` — the project's option format is
    [{'id': 1, 'text': '...', 'correct': True}, ...] (see papers/service/paperservice.py)."""
    if not isinstance(options, list):
        return []
    out = []
    for i, o in enumerate(options):
        if isinstance(o, dict) and bool(o.get('correct')):
            out.append(i)
    return out


def _neg(value) -> float:
    """Negative marking is written both ways across the codebase — Question.neg_marks is a
    positive magnitude, blueprints store `negative_marks: -1.0`. Normalize to a magnitude."""
    try:
        return abs(float(value or 0))
    except (TypeError, ValueError):
        return 0.0


def _num(value) -> Optional[float]:
    if value is None or value == '':
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def item_from_question(q, marks_override=None, snapshot_id: str = '') -> AnswerKeyItem:
    return AnswerKeyItem(
        item_key=f'q:{q.id}',
        question_id=q.id,
        question_snapshot_id=snapshot_id,
        q_type=q.q_type or '',
        marks=float(marks_override if marks_override is not None else (q.marks or 0)),
        neg_marks=_neg(q.neg_marks),
        correct_indices=_correct_indices(q.options),
        numeric_answer=_num(q.numeric_answer),
        unit=q.unit or '',
        text=q.text or '',
        topic=q.topic or '',
        subject=q.subject or '',
        difficulty=q.difficulty or '',
    )


def item_from_snapshot(pq_id: int, snap: dict) -> AnswerKeyItem:
    snap = snap or {}
    return AnswerKeyItem(
        item_key=f's:{pq_id}',
        question_id=None,
        question_snapshot_id=str(pq_id),
        q_type=snap.get('q_type') or '',
        marks=float(snap.get('marks') or 0),
        neg_marks=_neg(snap.get('neg_marks', snap.get('negative_marks'))),
        correct_indices=_correct_indices(snap.get('options')),
        numeric_answer=_num(snap.get('numeric_answer')),
        unit=snap.get('unit') or '',
        text=snap.get('text') or '',
        topic=snap.get('topic') or '',
        subject=snap.get('subject') or '',
        difficulty=snap.get('difficulty') or '',
    )


def build_for_paper(paper_id) -> Dict[str, AnswerKeyItem]:
    """item_key -> AnswerKeyItem for every question on the paper, in paper order."""
    key: Dict[str, AnswerKeyItem] = {}
    qs = (PaperQuestion.objects
          .filter(section__paper_id=paper_id)
          .select_related('question', 'section')
          .order_by('section__order', 'order'))
    for pq in qs:
        if pq.question_id:
            item = item_from_question(pq.question, marks_override=pq.marks_override)
        else:
            item = item_from_snapshot(pq.id, pq.snapshot)
        key[item.item_key] = item
    return key


def build_for_questions(question_ids) -> Dict[str, AnswerKeyItem]:
    """Fallback key when an attempt has no paper (e.g. an ad-hoc quiz over bank questions)."""
    from questions.models import Question
    key: Dict[str, AnswerKeyItem] = {}
    for q in Question.objects.filter(id__in=[i for i in question_ids if i]):
        item = item_from_question(q)
        key[item.item_key] = item
    return key
