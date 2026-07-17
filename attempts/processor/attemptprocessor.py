from dataclasses import dataclass, field
from typing import Any, List, Optional

import marshmallow_dataclass
from dataclasses_json import dataclass_json
from marshmallow import EXCLUDE


# ── Requests ──────────────────────────────────────────────────────────────────

@dataclass
class QuestionResponseRequest:
    """One student's answer to one question.

    Identify the question with EITHER `question_id` (a bank questions.Question) OR
    `question_snapshot_id` (the PaperQuestion row id, for paper-only questions that
    were never promoted to the bank).

    Leaving every answer field null means UNATTEMPTED — which is graded 0, not wrong.
    """
    question_id:             Optional[int] = None
    question_snapshot_id:    Optional[str] = None
    selected_option_index:   Optional[int] = None          # 0-based, single-correct MCQ
    selected_option_indices: Optional[List[int]] = None    # 0-based, Multiple Correct
    numeric_answer:          Optional[float] = None        # Numerical / TITA
    time_spent_seconds:      Optional[int] = None


@dataclass
class AttemptRequest:
    student_id:   int
    paper_id:     Optional[int] = None
    mock_test_id: Optional[int] = None
    source:       Optional[str] = 'online'                 # online | omr | manual
    submitted_at: Optional[str] = None                     # ISO-8601; defaults to now
    responses:    List[QuestionResponseRequest] = field(default_factory=list)


attempt_req_schema = marshmallow_dataclass.class_schema(AttemptRequest)(unknown=EXCLUDE)


# ── Responses ─────────────────────────────────────────────────────────────────

@dataclass_json
@dataclass
class QuestionResponseResponse:
    id:                      int
    question_id:             Optional[int]
    question_snapshot_id:    str
    selected_option_index:   Optional[int]
    selected_option_indices: Optional[Any]
    numeric_answer:          Optional[float]
    # unattempted | correct | partial | incorrect  — `status` distinguishes skipped
    # from wrong; `is_correct` is None for unattempted.
    status:                  str
    is_correct:              Optional[bool]
    marks_awarded:           float
    time_spent_seconds:      Optional[int] = None


@dataclass_json
@dataclass
class AttemptResponse:
    id:           int
    student_id:   int
    student_name: Optional[str]
    paper_id:     Optional[int]
    mock_test_id: Optional[int]
    status:       str
    source:       str
    total_score:  float
    max_score:    float
    started_at:   Optional[str]
    submitted_at: Optional[str]
    responses:    List[QuestionResponseResponse] = field(default_factory=list)


@dataclass_json
@dataclass
class ItemAnalysisEntry:
    """Classical Test Theory statistics for one question, over one paper's cohort."""
    item_key:               str            # 'q:<question_id>' or 's:<paper_question_id>'
    question_id:            Optional[int]
    question_snapshot_id:   str
    text:                   str
    topic:                  str
    subject:                str
    q_type:                 str
    # What the LLM *guessed* when it wrote the question.
    stated_difficulty:      str
    # What the students actually did. None when the sample is too small to say.
    n_students:             int
    n_correct:              int
    n_incorrect:            int
    n_unattempted:          int
    # p_value = n_correct / n_students. HIGH p_value == EASY (it is the proportion who
    # got it RIGHT). It is a "difficulty index" only in the perverse classical sense.
    p_value:                Optional[float]
    # D = (proportion correct in top 27%) - (proportion correct in bottom 27%).
    discrimination:         Optional[float]
    # Difficulty label derived from the measured p_value — compare with stated_difficulty.
    calibrated_difficulty:  Optional[str]
    # ok | low | insufficient  — see attempts/service/itemanalysisservice.py
    confidence:             str
    # True when D < 0: the students who scored best on the paper overall got THIS
    # question wrong more often than the weakest ones did. That is not a hard question,
    # that is a broken one (wrong key, ambiguous options, misprint).
    is_broken:              bool
    # True when 0 <= D < 0.2: keeps its key, but tells you nothing about ability.
    is_poor_discriminator:  bool
    flags:                  List[str] = field(default_factory=list)
    attempt_rate:           Optional[float] = None   # 1 - unattempted/n_students
    mean_marks:             Optional[float] = None


@dataclass_json
@dataclass
class ItemAnalysisResponse:
    paper_id:            int
    n_students:          int
    # The N below which we refuse to publish stats at all.
    min_students:        int
    # The N below which discrimination is suppressed (p_value still shown, low confidence).
    min_students_for_discrimination: int
    group_size:          int            # size of the top / bottom 27% groups
    reliable:            bool           # False => treat every number here as indicative only
    message:             str
    items:               List[ItemAnalysisEntry] = field(default_factory=list)


@dataclass_json
@dataclass
class TopicWeakness:
    topic:          str
    subject:        str
    n_questions:    int
    n_correct:      int
    n_incorrect:    int
    n_unattempted:  int
    accuracy:       float      # n_correct / n_questions  (unattempted counts against)
    marks_awarded:  float
    max_marks:      float
    score_pct:      float


@dataclass_json
@dataclass
class StudentSummaryResponse:
    student_id:    int
    student_name:  Optional[str]
    n_attempts:    int
    total_score:   float
    max_score:     float
    score_pct:     float
    # Weakest topics first — this is the "what should this kid revise" list.
    topics:        List[TopicWeakness] = field(default_factory=list)
    weakest_topics: List[str] = field(default_factory=list)


# ── Cohort analytics (across all students in an org / course) ──────────────────

@dataclass_json
@dataclass
class CohortTopicStat:
    topic:                 str
    subject:               str
    n_students:            int              # distinct students who faced ≥1 question here
    n_responses:           int              # gradable responses in this topic across the cohort
    n_correct:             int
    n_incorrect:           int
    n_unattempted:         int
    accuracy:              float            # n_correct / n_responses (unattempted counts against)
    avg_time_seconds:      Optional[float]
    # Cohort p_value == accuracy, mapped to the Easy/Medium/Hard/HOTS vocabulary. HIGH = easy.
    calibrated_difficulty: Optional[str]


@dataclass_json
@dataclass
class CohortSummaryResponse:
    org_id:          Optional[int]
    scope_label:     str                    # 'all', 'course:<id>', 'exam:<name>'
    n_students:      int                    # distinct students in the cohort
    n_attempts:      int
    min_students:    int
    reliable:        bool                   # False => too few students to trust the topic split
    message:         str
    topics:          List[CohortTopicStat] = field(default_factory=list)
    weakest_topics:  List[str] = field(default_factory=list)
    strongest_topics: List[str] = field(default_factory=list)


# ── Adaptive practice ─────────────────────────────────────────────────────────

@dataclass
class AdaptivePracticeRequest:
    student_id: int
    count:      Optional[int] = 10
    language:   Optional[str] = 'English'
    # Cap how many distinct weak topics the practice set spans (breadth vs depth).
    max_topics: Optional[int] = 3


adaptive_practice_req_schema = marshmallow_dataclass.class_schema(AdaptivePracticeRequest)(unknown=EXCLUDE)
