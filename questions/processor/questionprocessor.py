from dataclasses import dataclass
from typing import Any, List, Optional

import marshmallow_dataclass
from dataclasses_json import dataclass_json
from marshmallow import EXCLUDE

from utility.utilityobj import Pagination


@dataclass
class QuestionRequest:
    q_type:      str
    difficulty:  str
    marks:       int
    text:        str
    # FK-based fields (new flow)
    course_id:   Optional[str] = None   # UUID string
    subject_id:  Optional[int] = None
    topic_id:    Optional[int] = None
    # String fallbacks (legacy / AI-generated display values)
    exam:        Optional[str] = None
    subject:     Optional[str] = None
    topic:       Optional[str] = None
    bloom:       Optional[str] = 'Understand'
    neg_marks:   Optional[int] = 0
    options:     Optional[Any] = None
    explanation: Optional[str] = None
    solution:    Optional[str] = None   # full worked derivation (solution booklet)
    translations: Optional[Any] = None  # {"hi": {text, solution, options:[{text}]}}
    image_svg:   Optional[str] = None
    images:      Optional[Any] = None   # {"1": dataUrl, ...} for [[IMG:n]] markers
    source:      Optional[str] = 'manual'
    # Previous-year question: set when importing a real past paper. PYQs are retrieved
    # first as generation exemplars, newest year first.
    is_pyq:      Optional[bool] = False
    year:        Optional[int] = None
    id:          Optional[int] = None
    # has_latex is computed server-side; clients may send it but it is re-computed on every save
    has_latex:   Optional[bool] = None
    # Numerical-answer questions (no options) carry their key here.
    numeric_answer: Optional[float] = None
    unit:           Optional[str] = ''
    # Answer-key verification outcome, carried through from AI generation so a
    # flagged/corrected question stays flagged/corrected once saved to the bank.
    verification:      Optional[str] = ''
    verification_note: Optional[str] = ''


question_req_schema = marshmallow_dataclass.class_schema(QuestionRequest)(unknown=EXCLUDE)


@dataclass
class QuestionGenerateRequest:
    q_type:     str
    difficulty: str
    bloom:      str
    count:      int
    # FK-based (preferred — resolves names from DB)
    course_id:  Optional[str] = None
    subject_id: Optional[int] = None
    topic_id:   Optional[int] = None
    # String fallbacks (legacy)
    exam:       Optional[str] = None
    subject:    Optional[str] = None
    topic:      Optional[str] = None
    # English | Hindi | Tamil | ... (papers.service.aigeneratorservice.LANGUAGES).
    # A non-English value generates the question in BOTH languages in one call.
    language:   Optional[str] = 'English'


question_generate_req_schema = marshmallow_dataclass.class_schema(QuestionGenerateRequest)(unknown=EXCLUDE)


@dataclass
class VariantRequest:
    """POST /api/questions/variants/ — ask for N parametric variants of one question.

    Either point at an existing bank question by `question_id` (resolved and scoped to
    the org server-side), or pass the source `question` dict inline (e.g. for a
    generated-but-unsaved question). `count` is clamped to a sane range in the view.
    """
    question_id: Optional[int] = None
    count:       int = 4
    language:    Optional[str] = 'English'
    # Inline source question dict when there is no saved id (text, options, q_type,
    # difficulty, marks, subject, topic, exam, bloom, solution, numeric_answer/unit,
    # diagram_schema). Any is a schema-free passthrough — the generator reads keys off it.
    question:    Optional[Any] = None


variant_req_schema = marshmallow_dataclass.class_schema(VariantRequest)(unknown=EXCLUDE)


@dataclass_json
@dataclass
class QuestionResponse:
    id:          int
    q_type:      str
    difficulty:  str
    bloom:       str
    marks:       int
    neg_marks:   int
    text:        str
    source:      str
    created_at:  str
    # Resolved display strings
    exam:        Optional[str]
    subject:     Optional[str]
    topic:       Optional[str]
    # FK references
    course_id:   Optional[str]
    course_name: Optional[str]
    subject_id:  Optional[int]
    topic_id:    Optional[int]
    options:     Optional[Any]
    explanation: Optional[str]
    image_svg:   Optional[str]
    solution:    Optional[str] = None   # full worked derivation (solution booklet)
    translations: Optional[Any] = None  # {"hi": {text, solution, options:[{text}]}}
    images:      Optional[Any] = None   # {"1": dataUrl, ...} for [[IMG:n]] markers
    is_pyq:      bool = False
    year:        Optional[int] = None
    # LaTeX flag — True when text/options contain $...$ math notation
    has_latex:   bool = False
    # Numerical-answer key (options is null for these).
    numeric_answer: Optional[float] = None
    unit:           Optional[str] = ''
    # verified | corrected | flagged | skipped | approved | rejected | '' (never
    # verified). The UI should surface `flagged` — those are the questions a human
    # still needs to look at. See questions/service/questionservice.py for the full
    # state machine.
    verification:      Optional[str] = ''
    verification_note: Optional[str] = ''


# ── Review queue ──────────────────────────────────────────────────────────────
# Everything below backs the teacher-facing review queue and the quality dashboard
# (questions/service/questionservice.py). Kept at the end of the file so the DTOs
# above stay in their original order.


@dataclass
class ReviewActionRequest:
    """POST /api/questions/review/ — act on one question in the queue.

    `action`:
        approve — a human confirms the key; question leaves the queue
        reject  — a human rejects it; excluded from papers, but never hard-deleted
        edit    — apply an edit; changing text/options re-opens verification
    The text/options/explanation/numeric_answer/unit fields are only read for
    `edit`; anything omitted keeps its current value.
    """
    question_id: int
    action:      str
    note:        Optional[str] = ''      # free-text teacher comment, kept in verification_note
    text:        Optional[str] = None
    options:     Optional[Any] = None
    explanation: Optional[str] = None
    solution:    Optional[str] = None
    numeric_answer: Optional[float] = None
    unit:           Optional[str] = None


review_action_req_schema = marshmallow_dataclass.class_schema(ReviewActionRequest)(unknown=EXCLUDE)


@dataclass_json
@dataclass
class ReviewCorrection:
    """What the verifier CHANGED on a `corrected` question, so a teacher can see the
    before/after at a glance instead of reading prose. Fields are None when the
    note could not be parsed (hand-written note, older row)."""
    from_index: Optional[int] = None
    from_text:  Optional[str] = None
    to_index:   Optional[int] = None
    to_text:    Optional[str] = None
    reason:     Optional[str] = None


@dataclass_json
@dataclass
class ReviewQuestionResponse:
    question:          QuestionResponse
    verification:      str
    verification_note: str
    # Only populated for verification == 'corrected'.
    correction:        Optional[ReviewCorrection] = None
    # The key as it currently stands (post-correction).
    current_answer_index: Optional[int] = None
    current_answer_text:  Optional[str] = None
    # Parsed back out of verification_note — see the migration note in questionservice.
    reviewed_by: Optional[int] = None
    reviewed_at: Optional[str] = None


@dataclass_json
@dataclass
class ReviewQueueResponse:
    data:       List[ReviewQuestionResponse]
    total:      int                  # rows matching the filter, before pagination
    counts:     Any                  # {'flagged': n, 'corrected': n, ...} for the filtered set
    pagination: Optional[Pagination] = None


@dataclass_json
@dataclass
class ReviewActionResponse:
    status:   int
    message:  str
    question: Optional[ReviewQuestionResponse] = None


# ── Quality dashboard ─────────────────────────────────────────────────────────


@dataclass_json
@dataclass
class QualityGroup:
    """Stats for one slice (overall, or one subject / exam / topic).

    `n` is the AUTO-VERIFIABLE denominator (verified + corrected + flagged) — not
    `total` — because skipped/unverified questions never got a verdict and would
    otherwise dilute every rate. `rates` is None when n < min_n: a 2-question
    subject must not report "100% flagged".
    """
    key:         str
    total:       int    # every question in the slice, whatever its state
    n:           int    # denominator for `rates`
    counts:      Any    # {'verified':.., 'corrected':.., 'flagged':.., 'skipped':.., 'unverified':.., 'approved':.., 'rejected':..}
    rates:       Optional[Any] = None   # {'verified':.., 'corrected':.., 'flagged':.., 'needs_review':..} or None
    enough_data: bool = False


@dataclass_json
@dataclass
class QualityBucket:
    """One point on the drift time-series (a day or an ISO week)."""
    bucket:      str
    total:       int
    n:           int
    counts:      Any
    rates:       Optional[Any] = None
    enough_data: bool = False


@dataclass_json
@dataclass
class QualityHotspot:
    """A subject/topic ranked by how often its questions need a human. Only slices
    that clear min_n ever make this list."""
    scope:             str    # 'subject' | 'topic'
    key:               str
    n:                 int
    corrected:         int
    flagged:           int
    needs_review_rate: float  # (corrected + flagged) / n


@dataclass_json
@dataclass
class QualityResponse:
    min_n:       int          # slices below this report rates=None
    window_days: int          # time-series window
    bucket:      str          # 'day' | 'week'
    overall:     QualityGroup
    by_subject:  List[QualityGroup]
    by_exam:     List[QualityGroup]
    by_topic:    List[QualityGroup]
    series:      List[QualityBucket]
    worst_subjects: List[QualityHotspot]
    worst_topics:   List[QualityHotspot]