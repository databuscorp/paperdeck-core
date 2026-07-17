"""Classical item analysis — the point of recording attempts at all.

Two numbers, and both are easy to get subtly wrong, so read this before using them.

────────────────────────────────────────────────────────────────────────────────
p_value  (the "difficulty index")

    p = n_correct / n_students

    HIGH p_value MEANS THE QUESTION IS EASY. It is the proportion of students who got it
    RIGHT. It is called a *difficulty* index for historical reasons and it trips people up
    constantly: p = 0.9 is a giveaway, p = 0.1 is brutal. Sort ascending to find the hard
    ones. `calibrated_difficulty` below exists so nobody has to remember this.

    Denominator: every student in the cohort who was PRESENTED the item (has a response
    row for it). An unattempted item counts as not-correct — skipping is evidence about
    difficulty, and pretending otherwise flatters hard questions. `attempt_rate` is
    reported separately so a "hard" item and a "nobody even tried" item are told apart.

    Numerator: status == 'correct' only. A PARTIAL Multiple-Correct answer is NOT correct.

────────────────────────────────────────────────────────────────────────────────
discrimination index  (D), the standard exam-board 27% method

    D = (proportion correct in the TOP 27% by total paper score)
      − (proportion correct in the BOTTOM 27% by total paper score)

    Rank every attempt by total_score (ties broken by attempt id, ascending, so the cut is
    deterministic). group_size = max(1, int(0.27 × N + 0.5)) — the 27% split maximises the
    stability of the contrast between groups for a normally distributed cohort (Kelley).

        D ≥ 0.4    excellent
        0.2 – 0.4  acceptable
        0 – 0.2    POOR — the item does not separate strong students from weak ones
        D < 0      BROKEN. The students who did best on the paper overall got THIS question
                   wrong MORE often than the weakest students did. That is not a hard
                   question; it is almost always a wrong answer key, an ambiguous option, or
                   a misprint. It is surfaced as `is_broken` and it is the single most
                   valuable defect signal in this file.

────────────────────────────────────────────────────────────────────────────────
SMALL-SAMPLE GUARD

    Both statistics are noise at small N. With 3 students, one careless mistake swings
    p_value by 0.33 and D by a full 1.0. So:

        N <  MIN_STUDENTS (5)                      → NOTHING is computed. p_value,
                                                     discrimination and calibrated_difficulty
                                                     are all None; confidence='insufficient'.
        N <  MIN_STUDENTS_FOR_DISCRIMINATION (10)  → p_value and calibration are reported but
                                                     discrimination is None; confidence='low'.
                                                     Below 10, the 27% groups are 1–2 students
                                                     and D is a coin flip.
        N >= 10                                    → everything; confidence='ok'.

    These floors are low by psychometric standards (textbooks want 100+ for stable D); they
    are set for a coaching-batch reality where 30 students is a big class. Treat D from a
    batch of 12 as a smoke alarm, not a measurement.
"""
from typing import Dict, List, Optional

from attempts.models import QuestionResponse, StudentAttempt
from attempts.processor.attemptprocessor import (CohortSummaryResponse, CohortTopicStat,
                                                 ItemAnalysisEntry, ItemAnalysisResponse,
                                                 StudentSummaryResponse, TopicWeakness)
from attempts.service import answerkey

# ── Guards (documented above) ─────────────────────────────────────────────────
MIN_STUDENTS = 5
MIN_STUDENTS_FOR_DISCRIMINATION = 10

# ── Discrimination thresholds ─────────────────────────────────────────────────
POOR_DISCRIMINATION = 0.2      # 0 <= D < 0.2  → does not separate strong from weak
GROUP_FRACTION = 0.27          # the classic Kelley upper/lower 27%

# ── p_value → difficulty label. HIGH p == EASY. ───────────────────────────────
# Bands are aligned to how Indian coaching institutes actually talk about a question:
# 4 in 5 got it (Easy) / most got it (Medium) / most missed it (Hard) / almost nobody (HOTS).
CALIBRATION_BANDS = [
    (0.80, 'Easy'),
    (0.55, 'Medium'),
    (0.30, 'Hard'),
    (0.00, 'HOTS'),
]

TOO_EASY_P = 0.95
TOO_HARD_P = 0.10
HIGH_SKIP_RATE = 0.5


def calibrate_difficulty(p_value: Optional[float]) -> Optional[str]:
    """Map a MEASURED p_value back onto the Easy/Medium/Hard/HOTS vocabulary the rest of
    PaperDeck uses, so the LLM's *guess* (`Question.difficulty`) can be compared with what
    students actually did. Remember: high p_value = easy."""
    if p_value is None:
        return None
    for floor, label in CALIBRATION_BANDS:
        if p_value >= floor:
            return label
    return 'HOTS'


def group_size_for(n: int) -> int:
    """Size of the top / bottom 27% groups. int(x + 0.5) rather than round(), because
    Python's round() is banker's rounding and would make the cut depend on parity."""
    if n <= 0:
        return 0
    return max(1, int(GROUP_FRACTION * n + 0.5))


def _rank(attempts: List[StudentAttempt]) -> List[StudentAttempt]:
    # Deterministic: score desc, then id asc. Ties at the group boundary have to be cut
    # somewhere; doing it by id means the same cohort always yields the same D.
    return sorted(attempts, key=lambda a: (-float(a.total_score or 0), a.id))


def _proportion_correct(attempt_ids, by_attempt: Dict[int, QuestionResponse]):
    """(proportion, n) over the attempts in the group that were PRESENTED this item."""
    seen = [by_attempt[aid] for aid in attempt_ids if aid in by_attempt]
    if not seen:
        return None, 0
    n_correct = sum(1 for r in seen if r.status == QuestionResponse.STATUS_CORRECT)
    return n_correct / len(seen), len(seen)


class ItemAnalysisService:
    def __init__(self, scope):
        self.scope = scope
        self.org_id = (scope or {}).get('org_id')

    def _cohort(self, paper_id) -> List[StudentAttempt]:
        qs = StudentAttempt.objects.filter(
            paper_id=paper_id, status=StudentAttempt.STATUS_GRADED
        )
        if self.org_id:
            qs = qs.filter(org_id=self.org_id)
        return list(qs)

    def analyse_paper(self, paper_id) -> ItemAnalysisResponse:
        attempts = self._cohort(paper_id)
        n = len(attempts)
        key = answerkey.build_for_paper(paper_id)

        if n < MIN_STUDENTS:
            # Refuse outright. Emitting a p_value from 3 students is worse than emitting
            # nothing — it looks like a measurement and gets acted on.
            return ItemAnalysisResponse(
                paper_id=int(paper_id),
                n_students=n,
                min_students=MIN_STUDENTS,
                min_students_for_discrimination=MIN_STUDENTS_FOR_DISCRIMINATION,
                group_size=0,
                reliable=False,
                message=(f'Only {n} graded attempt(s). Item analysis needs at least '
                         f'{MIN_STUDENTS} students before any statistic is meaningful; '
                         f'discrimination needs {MIN_STUDENTS_FOR_DISCRIMINATION}.'),
                items=[],
            )

        ranked = _rank(attempts)
        g = group_size_for(n)
        top_ids = [a.id for a in ranked[:g]]
        bottom_ids = [a.id for a in ranked[-g:]]

        can_discriminate = n >= MIN_STUDENTS_FOR_DISCRIMINATION
        confidence = 'ok' if can_discriminate else 'low'

        # Group every response by item, then by attempt.
        responses = QuestionResponse.objects.filter(attempt_id__in=[a.id for a in ranked])
        by_item: Dict[str, Dict[int, QuestionResponse]] = {}
        for r in responses:
            by_item.setdefault(r.item_key, {})[r.attempt_id] = r

        items: List[ItemAnalysisEntry] = []
        for item_key, item in key.items():
            per_attempt = by_item.get(item_key, {})
            item_n = len(per_attempt)
            if item_n == 0:
                continue

            rows = list(per_attempt.values())
            n_correct = sum(1 for r in rows if r.status == QuestionResponse.STATUS_CORRECT)
            n_unattempted = sum(1 for r in rows if r.status == QuestionResponse.STATUS_UNATTEMPTED)
            # partial counts as not-correct but IS an attempt
            n_incorrect = item_n - n_correct - n_unattempted

            item_confidence = confidence
            if item_n < MIN_STUDENTS:
                item_confidence = 'insufficient'
            elif item_n < MIN_STUDENTS_FOR_DISCRIMINATION:
                item_confidence = 'low'

            p_value = None if item_confidence == 'insufficient' else n_correct / item_n

            d = None
            if item_confidence == 'ok':
                p_top, n_top = _proportion_correct(top_ids, per_attempt)
                p_bot, n_bot = _proportion_correct(bottom_ids, per_attempt)
                if p_top is not None and p_bot is not None:
                    d = round(p_top - p_bot, 4)

            is_broken = d is not None and d < 0
            is_poor = d is not None and 0 <= d < POOR_DISCRIMINATION
            calibrated = calibrate_difficulty(p_value)

            flags: List[str] = []
            if is_broken:
                flags.append('broken_negative_discrimination')
            if is_poor:
                flags.append('poor_discriminator')
            if p_value is not None and p_value >= TOO_EASY_P:
                flags.append('too_easy')
            if p_value is not None and p_value <= TOO_HARD_P:
                flags.append('too_hard')
            if item_n and (n_unattempted / item_n) >= HIGH_SKIP_RATE:
                flags.append('high_skip_rate')
            if calibrated and item.difficulty and calibrated.lower() != item.difficulty.strip().lower():
                # The LLM said one thing, the cohort said another. Not a defect on its own,
                # but it is exactly what `calibrated_difficulty` exists to expose.
                flags.append('difficulty_mismatch')
            if item_confidence != 'ok':
                flags.append('low_confidence')

            items.append(ItemAnalysisEntry(
                item_key=item_key,
                question_id=item.question_id,
                question_snapshot_id=item.question_snapshot_id,
                text=item.text,
                topic=item.topic,
                subject=item.subject,
                q_type=item.q_type,
                stated_difficulty=item.difficulty,
                n_students=item_n,
                n_correct=n_correct,
                n_incorrect=n_incorrect,
                n_unattempted=n_unattempted,
                p_value=None if p_value is None else round(p_value, 4),
                discrimination=d,
                calibrated_difficulty=calibrated,
                confidence=item_confidence,
                is_broken=is_broken,
                is_poor_discriminator=is_poor,
                flags=flags,
                attempt_rate=round(1 - (n_unattempted / item_n), 4) if item_n else None,
                mean_marks=round(sum(r.marks_awarded for r in rows) / item_n, 4),
            ))

        msg = 'ok'
        if not can_discriminate:
            msg = (f'{n} graded attempts: p_value is reported but discrimination is '
                   f'suppressed below {MIN_STUDENTS_FOR_DISCRIMINATION} students, where the '
                   f'27% groups are too small to mean anything.')

        return ItemAnalysisResponse(
            paper_id=int(paper_id),
            n_students=n,
            min_students=MIN_STUDENTS,
            min_students_for_discrimination=MIN_STUDENTS_FOR_DISCRIMINATION,
            group_size=g,
            reliable=can_discriminate,
            message=msg,
            items=items,
        )

    # ── Per-student weakness ──────────────────────────────────────────────────

    def student_summary(self, student_id) -> StudentSummaryResponse:
        """Which topics is this student actually weak in — across every graded attempt."""
        qs = StudentAttempt.objects.filter(
            student_id=student_id, status=StudentAttempt.STATUS_GRADED
        ).select_related('student')
        if self.org_id:
            qs = qs.filter(org_id=self.org_id)
        attempts = list(qs)

        student_name = attempts[0].student.name if attempts else None
        if not student_name:
            from students.models import Student
            student_name = (Student.objects.filter(id=student_id)
                            .values_list('name', flat=True).first())

        key_cache: Dict[int, dict] = {}
        buckets: Dict[str, TopicWeakness] = {}
        total_score = 0.0
        max_score = 0.0

        for attempt in attempts:
            total_score += float(attempt.total_score or 0)
            max_score += float(attempt.max_score or 0)
            if attempt.paper_id:
                if attempt.paper_id not in key_cache:
                    key_cache[attempt.paper_id] = answerkey.build_for_paper(attempt.paper_id)
                key = key_cache[attempt.paper_id]
            else:
                key = answerkey.build_for_questions(
                    [r.question_id for r in attempt.responses.all() if r.question_id])

            for r in attempt.responses.all():
                item = key.get(r.item_key)
                if item is None or not item.is_gradable:
                    continue
                topic = (item.topic or '').strip() or 'Uncategorised'
                bucket = buckets.get(topic)
                if bucket is None:
                    bucket = buckets[topic] = TopicWeakness(
                        topic=topic, subject=(item.subject or '').strip(),
                        n_questions=0, n_correct=0, n_incorrect=0, n_unattempted=0,
                        accuracy=0.0, marks_awarded=0.0, max_marks=0.0, score_pct=0.0,
                    )
                bucket.n_questions += 1
                if r.status == QuestionResponse.STATUS_CORRECT:
                    bucket.n_correct += 1
                elif r.status == QuestionResponse.STATUS_UNATTEMPTED:
                    bucket.n_unattempted += 1
                else:
                    bucket.n_incorrect += 1
                bucket.marks_awarded += float(r.marks_awarded or 0)
                bucket.max_marks += float(item.marks or 0)

        for b in buckets.values():
            b.accuracy = round(b.n_correct / b.n_questions, 4) if b.n_questions else 0.0
            b.marks_awarded = round(b.marks_awarded, 4)
            b.max_marks = round(b.max_marks, 4)
            b.score_pct = round(100 * b.marks_awarded / b.max_marks, 2) if b.max_marks else 0.0

        # Weakest first — that is the revision list.
        topics = sorted(buckets.values(), key=lambda b: (b.accuracy, -b.n_questions))

        return StudentSummaryResponse(
            student_id=int(student_id),
            student_name=student_name,
            n_attempts=len(attempts),
            total_score=round(total_score, 4),
            max_score=round(max_score, 4),
            score_pct=round(100 * total_score / max_score, 2) if max_score else 0.0,
            topics=topics,
            weakest_topics=[t.topic for t in topics if t.accuracy < 0.5][:5],
        )

    # ── Cohort weakness (across every student in the org / a course) ───────────

    def cohort_summary(self, course_id=None, exam=None) -> CohortSummaryResponse:
        """Where is the WHOLE batch weak — the topic mastery map a coaching owner acts on.

        Aggregates every graded response in scope by topic: cohort accuracy (== the topic's
        p_value, so it maps onto the same Easy/Medium/Hard/HOTS calibration), how many
        distinct students it covers, and average time spent. `student_summary` answers "what
        should THIS kid revise"; this answers "what should we RE-TEACH the class".
        """
        qs = StudentAttempt.objects.filter(status=StudentAttempt.STATUS_GRADED)
        if self.org_id:
            qs = qs.filter(org_id=self.org_id)
        scope_label = 'all'
        if course_id:
            qs = qs.filter(paper__course_id=course_id)
            scope_label = f'course:{course_id}'
        elif exam:
            qs = qs.filter(paper__exam=exam)
            scope_label = f'exam:{exam}'
        attempts = list(qs)

        n_students = len({a.student_id for a in attempts})

        key_cache: Dict[int, dict] = {}
        # topic -> aggregate; students tracked as a set so a kid who saw a topic on 3 papers
        # is still one student for coverage.
        agg: Dict[str, dict] = {}

        for attempt in attempts:
            if attempt.paper_id:
                if attempt.paper_id not in key_cache:
                    key_cache[attempt.paper_id] = answerkey.build_for_paper(attempt.paper_id)
                key = key_cache[attempt.paper_id]
            else:
                key = answerkey.build_for_questions(
                    [r.question_id for r in attempt.responses.all() if r.question_id])

            for r in attempt.responses.all():
                item = key.get(r.item_key)
                if item is None or not item.is_gradable:
                    continue
                topic = (item.topic or '').strip() or 'Uncategorised'
                a = agg.get(topic)
                if a is None:
                    a = agg[topic] = {
                        'subject': (item.subject or '').strip(), 'students': set(),
                        'n': 0, 'correct': 0, 'incorrect': 0, 'unattempted': 0,
                        'time_sum': 0, 'time_n': 0,
                    }
                a['students'].add(attempt.student_id)
                a['n'] += 1
                if r.status == QuestionResponse.STATUS_CORRECT:
                    a['correct'] += 1
                elif r.status == QuestionResponse.STATUS_UNATTEMPTED:
                    a['unattempted'] += 1
                else:
                    a['incorrect'] += 1
                if r.time_spent_seconds is not None:
                    a['time_sum'] += int(r.time_spent_seconds)
                    a['time_n'] += 1

        topics: List[CohortTopicStat] = []
        for topic, a in agg.items():
            accuracy = round(a['correct'] / a['n'], 4) if a['n'] else 0.0
            topics.append(CohortTopicStat(
                topic=topic, subject=a['subject'],
                n_students=len(a['students']), n_responses=a['n'],
                n_correct=a['correct'], n_incorrect=a['incorrect'],
                n_unattempted=a['unattempted'], accuracy=accuracy,
                avg_time_seconds=round(a['time_sum'] / a['time_n'], 1) if a['time_n'] else None,
                calibrated_difficulty=calibrate_difficulty(accuracy),
            ))

        # Weakest (lowest accuracy) first — that is the re-teach queue.
        topics.sort(key=lambda t: (t.accuracy, -t.n_responses))
        reliable = n_students >= MIN_STUDENTS
        message = 'ok' if reliable else (
            f'Only {n_students} student(s) in scope; the topic split needs at least '
            f'{MIN_STUDENTS} to be trusted.')

        return CohortSummaryResponse(
            org_id=self.org_id, scope_label=scope_label,
            n_students=n_students, n_attempts=len(attempts),
            min_students=MIN_STUDENTS, reliable=reliable, message=message,
            topics=topics,
            weakest_topics=[t.topic for t in topics if t.accuracy < 0.5][:5],
            strongest_topics=[t.topic for t in reversed(topics) if t.accuracy >= 0.8][:5],
        )
