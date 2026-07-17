import re
from collections import defaultdict
from datetime import timedelta

from django.db.models import Count
from django.utils import timezone

from questions.models import Question
from questions.processor.questionprocessor import (
    QualityBucket,
    QualityGroup,
    QualityHotspot,
    QualityResponse,
    QuestionRequest,
    QuestionResponse,
    ReviewActionResponse,
    ReviewCorrection,
    ReviewQuestionResponse,
    ReviewQueueResponse,
)
from utility.dbservice import DBService
from utility.utilityobj import Pagination, SuccessResponse, ErrorResponse
from latex.service.latexservice import has_math


# ── Verification state machine ────────────────────────────────────────────────
#
# `Question.verification` carries BOTH the machine verdict and the human verdict,
# because the review queue could not add columns (see the follow-up-migration note
# at the bottom of this block). The full set of values:
#
#   ''         unverified — never checked (manual entry, import, pre-existing row)
#   'verified'   ┐ written by papers/service/verificationservice.py
#   'corrected'  │  verified  — a blind re-solve agreed with the key
#   'flagged'    │  corrected — the key was WRONG and was auto-fixed
#   'skipped'  ┘  flagged   — could not be confirmed
#                 skipped   — not auto-verifiable (e.g. long answer)
#   'approved'  a human confirmed the key   (NEW — set by review_action)
#   'rejected'  a human rejected the question (NEW — set by review_action)
#
# Transitions:
#
#   ''  ──generate/verify──▶  verified | corrected | flagged | skipped
#
#   flagged ─┐
#   corrected┤──approve──▶ approved     (leaves the queue, usable in papers)
#   verified │──reject───▶ rejected     (leaves the queue, EXCLUDED from papers,
#   skipped  │                           never hard-deleted — the teacher still
#   ''       ┘                           wants to see what the AI got wrong)
#
#   rejected ──approve──▶ approved      (un-reject; a rejection is reversible)
#
#   <any> ──edit that changes text/options──▶ ''   (re-opens verification: an old
#          verdict only applies to the exact text/options that were solved, and a
#          stale "verified" badge is worse than none — see create_or_update)
#
# The review queue shows flagged + corrected by default. `corrected` is in there on
# purpose: an AI silently CHANGED the answer key, and a human should confirm that.
#
# Because the human verdict overwrites the machine verdict in the same column, an
# approve/reject would otherwise destroy the generation-quality signal the quality
# dashboard is built on. So review_action stamps the prior state into
# verification_note as "(was: flagged)" and _ai_state() reads it back. This is a
# workaround, not a design:
#
#   FOLLOW-UP MIGRATION (deliberately not written here): split these into proper
#   columns — `verification` (machine verdict only), `review_status`
#   (pending|approved|rejected), `reviewed_by` (FK to users.User), `reviewed_at`
#   (DateTimeField), and index (org, verification, review_status). Then _ai_state()
#   and the note-stamping below can be deleted outright.

VERIFIED   = 'verified'
CORRECTED  = 'corrected'
FLAGGED    = 'flagged'
SKIPPED    = 'skipped'
APPROVED   = 'approved'   # new — human confirmed
REJECTED   = 'rejected'   # new — human rejected (soft-delete)
UNVERIFIED = ''

# Verdicts the machine can emit.
AI_STATES = (VERIFIED, CORRECTED, FLAGGED, SKIPPED)
# Verdicts a human can emit.
HUMAN_STATES = (APPROVED, REJECTED)
# What lands in the queue when the caller doesn't say otherwise: both of these need
# a human's eyes — `flagged` because the AI couldn't confirm the key, `corrected`
# because the AI changed it.
REVIEW_QUEUE_DEFAULT = (FLAGGED, CORRECTED)
# Only these three ever received a verdict, so only these three form the denominator
# for the quality rates. Counting `skipped`/unverified in would dilute every rate
# towards zero and hide real drift.
RATED_STATES = (VERIFIED, CORRECTED, FLAGGED)

VALID_ACTIONS = ('approve', 'reject', 'edit')

# Minimum sample size before a slice (subject / topic / exam / time bucket) is
# allowed to report RATES. Below it, `rates` is None and `enough_data` is False —
# counts are still returned. 10 is a deliberately modest bar: it is small enough
# that a real subject clears it within a couple of generation runs, and large enough
# that one bad question can't push a slice to a headline-grabbing "50% flagged".
# Callers can raise it per-request with ?min_n=.
MIN_SAMPLE_N = 10

# Ranked-hotspot list length (worst subjects / worst topics).
DEFAULT_TOP_N = 5

_WAS_RE = re.compile(r'\(was: ([a-z]*)\)')
_REVIEW_STAMP_RE = re.compile(
    r'^\[review\] (approved|rejected) by user_id=(\d+) at (\S+)'
)
# verificationservice writes: "Answer key corrected from option 2 ('...') to option 0 ('...'): reason"
# Non-greedy between the two indices so a reason that happens to say "to option 3"
# can't hijack the match.
_CORRECTION_RE = re.compile(
    r'corrected from option (\d+).*? to option (\d+)[^:]*:?\s*(.*)', re.S
)


def _review_stamp(action_past: str, user_id, prev_state: str, comment: str, old_note: str) -> str:
    """Record who/when/from-what on a human review action.

    This is note-stamping standing in for columns we can't add — see the migration
    note above. The prior state is written as "(was: X)" and the previous note is
    kept underneath, so the AI's original explanation is never lost and the quality
    dashboard can still recover the machine verdict.
    """
    head = (f"[review] {action_past} by user_id={user_id} at "
            f"{timezone.now().isoformat()} (was: {prev_state or 'unverified'})")
    if comment and comment.strip():
        head += f" — {comment.strip()}"
    return f"{head}\n{old_note}" if old_note else head


def _ai_state(verification: str, note: str) -> str:
    """The MACHINE verdict for a question, seen through any later human action.

    A question a teacher approved still tells us what the generator did — it was
    'flagged' or 'corrected' once, and that is what the quality dashboard needs to
    measure drift. Since approve/reject overwrite the column, recover the original
    verdict from the "(was: X)" stamps in the note: notes are prepended, so the LAST
    stamp in the text is the OLDEST action, i.e. the state the machine left behind.
    Returns '' when the question was never machine-verified.
    """
    if verification in AI_STATES:
        return verification
    if verification in HUMAN_STATES:
        for was in reversed(_WAS_RE.findall(note or '')):
            if was in AI_STATES:
                return was
    return UNVERIFIED


def _parse_review_stamp(note: str):
    """(reviewed_by, reviewed_at) from the newest review stamp, or (None, None)."""
    m = _REVIEW_STAMP_RE.match((note or '').lstrip())
    if not m:
        return None, None
    try:
        return int(m.group(2)), m.group(3)
    except (TypeError, ValueError):
        return None, None


def _key_index(options):
    """Index of the option currently marked correct, or None."""
    if not isinstance(options, list):
        return None
    for i, o in enumerate(options):
        if isinstance(o, dict) and o.get('correct'):
            return i
    return None


def _opt_text(options, idx):
    if not isinstance(options, list) or idx is None or idx < 0 or idx >= len(options):
        return None
    o = options[idx]
    return o.get('text') if isinstance(o, dict) else str(o)


def _parse_correction(q: Question):
    """Turn a `corrected` note back into a structured before/after.

    The verifier only moves the `correct` flag — it never rewrites the option texts —
    so the OLD option is still sitting in `options` at the index named in the note.
    That makes from_text/to_text exact rather than scraped out of prose; only the
    two indices and the reason come from the note.
    """
    m = _CORRECTION_RE.search(q.verification_note or '')
    if not m:
        return ReviewCorrection()
    try:
        from_index = int(m.group(1))
        to_index = int(m.group(2))
    except (TypeError, ValueError):
        return ReviewCorrection()
    reason = (m.group(3) or '').strip() or None
    return ReviewCorrection(
        from_index=from_index,
        from_text=_opt_text(q.options, from_index),
        to_index=to_index,
        to_text=_opt_text(q.options, to_index),
        reason=reason,
    )


def _build_review(q: Question) -> ReviewQuestionResponse:
    reviewed_by, reviewed_at = _parse_review_stamp(q.verification_note)
    key = _key_index(q.options)
    return ReviewQuestionResponse(
        question=_build(q),
        verification=q.verification,
        verification_note=q.verification_note,
        correction=_parse_correction(q) if q.verification == CORRECTED else None,
        current_answer_index=key,
        current_answer_text=_opt_text(q.options, key),
        reviewed_by=reviewed_by,
        reviewed_at=reviewed_at,
    )


def _detect_latex(text: str, options) -> bool:
    """Return True if *text* or any option string contains $...$ / $$...$$ math."""
    if has_math(text or ""):
        return True
    if isinstance(options, list):
        for opt in options:
            opt_text = opt.get("text", "") if isinstance(opt, dict) else str(opt)
            if has_math(opt_text):
                return True
    return False


def _build(q: Question) -> QuestionResponse:
    course = getattr(q, 'course', None)
    return QuestionResponse(
        id=q.id,
        q_type=q.q_type,
        difficulty=q.difficulty,
        bloom=q.bloom,
        marks=q.marks,
        neg_marks=q.neg_marks,
        text=q.text,
        source=q.source,
        created_at=q.created_at.isoformat(),
        exam=q.exam,
        subject=q.subject,
        topic=q.topic,
        course_id=str(q.course_id) if q.course_id else None,
        course_name=course.name if course else None,
        subject_id=q.subject_ref_id,
        topic_id=q.topic_ref_id,
        options=q.options,
        explanation=q.explanation,
        solution=q.solution,
        translations=q.translations,
        is_pyq=q.is_pyq,
        year=q.year,
        image_svg=q.image_svg,
        images=q.images,
        has_latex=q.has_latex,
        numeric_answer=q.numeric_answer,
        unit=q.unit,
        verification=q.verification,
        verification_note=q.verification_note,
    )


def _resolve_display_strings(req):
    """Resolve exam/subject/topic display strings from FK objects when IDs are provided."""
    exam = req.exam or ''
    subject = req.subject or ''
    topic = req.topic or ''

    if req.course_id:
        try:
            from courses.models import Course
            course = Course.objects.select_related('authority').get(id=req.course_id)
            if course.authority:
                exam = course.authority.name
        except Exception:
            pass

    if req.subject_id:
        try:
            from subjects.models import Subject
            subj = Subject.objects.get(id=req.subject_id)
            subject = subj.name
        except Exception:
            pass

    if req.topic_id:
        try:
            from subjects.models import Topic
            t = Topic.objects.get(id=req.topic_id)
            topic = t.name
        except Exception:
            pass

    return exam, subject, topic


def _bucket_key(dt, bucket: str) -> str:
    """Day bucket → '2026-07-13'. Week bucket → the ISO Monday, '2026-07-13'.
    Local time, because "how did we do yesterday" means the teacher's yesterday."""
    d = timezone.localtime(dt).date()
    if bucket == 'week':
        d = d - timedelta(days=d.weekday())
    return d.isoformat()


class _Agg:
    """Counts for one slice. `ai` is the machine verdict (recovered through any human
    action); `current` is the state the row is in right now — the two differ exactly
    when a human has reviewed the question, which is why both are kept."""

    def __init__(self):
        self.total = 0
        self.counts = {
            VERIFIED: 0, CORRECTED: 0, FLAGGED: 0, SKIPPED: 0,
            'unverified': 0, APPROVED: 0, REJECTED: 0,
        }

    def add(self, ai: str, current: str):
        self.total += 1
        self.counts[ai or 'unverified'] += 1
        if current in HUMAN_STATES:
            self.counts[current] += 1

    @property
    def n(self) -> int:
        """The rated population: only these ever got a verdict."""
        return sum(self.counts[s] for s in RATED_STATES)

    def rates(self, min_n: int):
        """None below min_n — a slice with 2 questions does not get to claim a rate."""
        n = self.n
        if n < min_n:
            return None
        return {
            VERIFIED:  round(self.counts[VERIFIED] / n, 4),
            CORRECTED: round(self.counts[CORRECTED] / n, 4),
            FLAGGED:   round(self.counts[FLAGGED] / n, 4),
            'needs_review': round(
                (self.counts[CORRECTED] + self.counts[FLAGGED]) / n, 4),
        }

    def to_group(self, key: str, min_n: int) -> QualityGroup:
        return QualityGroup(key=key, total=self.total, n=self.n, counts=dict(self.counts),
                            rates=self.rates(min_n), enough_data=self.n >= min_n)

    def to_bucket(self, key: str, min_n: int) -> QualityBucket:
        return QualityBucket(bucket=key, total=self.total, n=self.n, counts=dict(self.counts),
                             rates=self.rates(min_n), enough_data=self.n >= min_n)


def _groups(agg_map, min_n: int):
    """Biggest slices first — a breakdown is read top-down."""
    return [a.to_group(k, min_n)
            for k, a in sorted(agg_map.items(), key=lambda kv: (-kv[1].n, kv[0]))]


def _hotspots(agg_map, scope: str, min_n: int, top: int):
    """Worst slices by needs-review rate.

    THE min-N guard lives here: a slice below min_n is not ranked at all, so a
    subject with 2 questions and 1 flag cannot sit at the top of the chart claiming
    "50% flagged" while a subject with 400 questions and a genuine 8% problem is
    buried under it.
    """
    out = []
    for key, a in agg_map.items():
        n = a.n
        if n < min_n:
            continue
        needs = a.counts[CORRECTED] + a.counts[FLAGGED]
        if not needs:
            continue
        out.append(QualityHotspot(
            scope=scope, key=key, n=n,
            corrected=a.counts[CORRECTED], flagged=a.counts[FLAGGED],
            needs_review_rate=round(needs / n, 4),
        ))
    # Ties broken by sample size: a problem seen 200 times outranks the same rate seen 10.
    out.sort(key=lambda h: (-h.needs_review_rate, -h.n, h.key))
    return out[:max(1, int(top or DEFAULT_TOP_N))]


class QuestionService(DBService):
    def __init__(self, scope):
        super().__init__(scope)

    def _scoped(self, user_id, org_id=None):
        """Every read is tenant-scoped here, in one place: org members see the org's
        bank, an org-less user sees only their own rows."""
        if org_id:
            # Show all org questions — any staff member can view
            return Question.objects.filter(org_id=org_id)
        return Question.objects.filter(owner_id=user_id)

    def fetch_all(self, user_id, org_id=None, course_id=None,
                  verification=None, include_rejected=False):
        """The question bank.

        Questions a human REJECTED are excluded by default — that is what a rejection
        means: it must not turn up in a paper. They are soft-deleted, never dropped,
        so they stay reachable two ways: `include_rejected=True`, or by asking for
        them explicitly with `verification=['rejected']` (which is how a teacher
        reviews what the AI got wrong).

        `verification` — optional list of states to keep. When it is given it is
        honoured as-is, including 'rejected'.
        """
        qs = self._scoped(user_id, org_id)

        if course_id:
            qs = qs.filter(course_id=course_id)

        if verification:
            qs = qs.filter(verification__in=list(verification))
        elif not include_rejected:
            qs = qs.exclude(verification=REJECTED)

        return [_build(q) for q in qs.select_related('course', 'subject_ref', 'topic_ref')]

    def fetch_one(self, question_id, user_id, org_id=None):
        try:
            qs = Question.objects.select_related('course', 'subject_ref', 'topic_ref')
            if org_id:
                q = qs.get(id=question_id, org_id=org_id)
            else:
                q = qs.get(id=question_id, owner_id=user_id)
            return _build(q)
        except Question.DoesNotExist:
            return ErrorResponse(status=404, message='Question not found')

    def create_or_update(self, req, user_id, org_id=None):
        exam, subject, topic = _resolve_display_strings(req)

        if req.id is None:
            q = Question.objects.create(
                owner_id=user_id,
                org_id=org_id,
                course_id=req.course_id or None,
                subject_ref_id=req.subject_id or None,
                topic_ref_id=req.topic_id or None,
                exam=exam,
                subject=subject,
                topic=topic,
                q_type=req.q_type,
                difficulty=req.difficulty,
                bloom=req.bloom or 'Understand',
                marks=req.marks,
                neg_marks=req.neg_marks or 0,
                text=req.text,
                options=req.options,
                explanation=req.explanation,
                solution=req.solution,
                translations=req.translations,
                is_pyq=bool(req.is_pyq),
                year=req.year,
                image_svg=req.image_svg,
                images=req.images,
                source=req.source or 'manual',
                has_latex=_detect_latex(req.text, req.options),
                numeric_answer=req.numeric_answer,
                unit=req.unit or '',
                verification=req.verification or '',
                verification_note=req.verification_note or '',
            )
        else:
            try:
                if org_id:
                    q = Question.objects.get(id=req.id, org_id=org_id)
                else:
                    q = Question.objects.get(id=req.id, owner_id=user_id)
            except Question.DoesNotExist:
                return ErrorResponse(status=404, message='Question not found')

            if req.course_id is not None:
                q.course_id = req.course_id or None
            if req.subject_id is not None:
                q.subject_ref_id = req.subject_id or None
            if req.topic_id is not None:
                q.topic_ref_id = req.topic_id or None
            q.exam = exam or q.exam
            q.subject = subject or q.subject
            q.topic = topic or q.topic
            q.q_type = req.q_type
            q.difficulty = req.difficulty
            q.bloom = req.bloom or q.bloom
            q.marks = req.marks
            q.neg_marks = req.neg_marks if req.neg_marks is not None else q.neg_marks
            # A prior verification only applies to the exact text/options that were
            # solved. If either changed, the old verdict is stale — and a stale
            # "verified" badge is worse than none, so drop it unless the caller
            # explicitly supplies a fresh one.
            content_changed = (q.text != req.text) or (q.options != req.options)

            q.text = req.text
            q.options = req.options
            q.explanation = req.explanation
            q.image_svg = req.image_svg
            q.images = req.images
            if req.numeric_answer is not None:
                q.numeric_answer = req.numeric_answer
            if req.unit is not None:
                q.unit = req.unit
            if req.source:
                q.source = req.source

            if req.verification:
                q.verification = req.verification
                q.verification_note = req.verification_note or ''
            elif content_changed:
                q.verification = ''
                q.verification_note = ''

            # Re-compute has_latex whenever text or options change
            q.has_latex = _detect_latex(req.text, req.options)
            q.save()

        return _build(q)

    def delete(self, question_id, user_id, org_id=None):
        if org_id:
            deleted, _ = Question.objects.filter(id=question_id, org_id=org_id).delete()
        else:
            deleted, _ = Question.objects.filter(id=question_id, owner_id=user_id).delete()
        if not deleted:
            return ErrorResponse(status=404, message='Question not found')
        return SuccessResponse(status=200, message='Question deleted')

    # ── Review queue ──────────────────────────────────────────────────────────

    def review_queue(self, user_id, org_id=None, status=None, subject=None,
                     topic=None, exam=None, course_id=None, index=1, limit=20):
        """Questions waiting on a human, newest first.

        Defaults to flagged + corrected. Any state can be requested explicitly —
        `status=['rejected']` is how a teacher goes back over what the AI got wrong.
        """
        states = list(status) if status else list(REVIEW_QUEUE_DEFAULT)

        qs = self._scoped(user_id, org_id).filter(verification__in=states)
        if subject:
            qs = qs.filter(subject__iexact=subject)
        if topic:
            qs = qs.filter(topic__iexact=topic)
        if exam:
            qs = qs.filter(exam__iexact=exam)
        if course_id:
            qs = qs.filter(course_id=course_id)

        # Queue composition BEFORE pagination — the UI shows "12 flagged, 25 corrected"
        # above the list, and that must not describe just the current page.
        counts = {s: 0 for s in states}
        for row in qs.values('verification').annotate(n=Count('id')):
            counts[row['verification']] = row['n']
        total = sum(counts.values())

        index = max(1, int(index or 1))
        limit = max(1, min(int(limit or 20), 100))
        offset = (index - 1) * limit
        page = qs.select_related('course', 'subject_ref', 'topic_ref')[offset:offset + limit]

        has_next = offset + limit < total
        has_previous = index > 1
        return ReviewQueueResponse(
            data=[_build_review(q) for q in page],
            total=total,
            counts=counts,
            pagination=Pagination(
                index=index,
                limit=limit,
                has_previous=has_previous,
                has_next=has_next,
                next_index=index + 1 if has_next else index,
                prev_index=index - 1 if has_previous else index,
            ),
        )

    def review_action(self, req, user_id, org_id=None):
        """approve / reject / edit one question in the queue."""
        action = (req.action or '').strip().lower()
        if action not in VALID_ACTIONS:
            return ErrorResponse(
                status=400,
                message=f"action must be one of {', '.join(VALID_ACTIONS)}",
            )

        try:
            q = self._scoped(user_id, org_id).get(id=req.question_id)
        except Question.DoesNotExist:
            # Also the cross-tenant path: another org's question is simply not found.
            return ErrorResponse(status=404, message='Question not found')

        if action == 'edit':
            return self._review_edit(req, q, user_id, org_id)

        prev = q.verification
        new_state = APPROVED if action == 'approve' else REJECTED
        q.verification = new_state
        q.verification_note = _review_stamp(
            'approved' if action == 'approve' else 'rejected',
            user_id, prev, req.note or '', q.verification_note,
        )
        q.save(update_fields=['verification', 'verification_note'])

        message = ('Question approved' if action == 'approve'
                   else 'Question rejected — it will not be used in papers')
        return ReviewActionResponse(status=200, message=message, question=_build_review(q))

    def _review_edit(self, req, q: Question, user_id, org_id):
        """Apply a teacher's edit through the EXISTING save path.

        Deliberately routed through create_or_update rather than re-implementing the
        write: that is the one place that knows a content change invalidates the old
        verdict (verification → '', i.e. re-opened for verification) and that
        has_latex must be recomputed. Fields the caller omits keep their current
        values. Note that an edit which does NOT touch text/options leaves the
        verification state alone, so a flagged question edited only for, say, its
        explanation correctly stays in the queue.
        """
        patch = QuestionRequest(
            id=q.id,
            q_type=q.q_type,
            difficulty=q.difficulty,
            marks=q.marks,
            course_id=str(q.course_id) if q.course_id else None,
            subject_id=q.subject_ref_id,
            topic_id=q.topic_ref_id,
            exam=q.exam,
            subject=q.subject,
            topic=q.topic,
            bloom=q.bloom,
            neg_marks=q.neg_marks,
            text=req.text if req.text is not None else q.text,
            options=req.options if req.options is not None else q.options,
            explanation=req.explanation if req.explanation is not None else q.explanation,
            solution=req.solution if req.solution is not None else q.solution,
            image_svg=q.image_svg,
            images=q.images,
            source=q.source,
            numeric_answer=(req.numeric_answer if req.numeric_answer is not None
                            else q.numeric_answer),
            unit=req.unit if req.unit is not None else q.unit,
            # Left empty on purpose: create_or_update only keeps a verdict the caller
            # explicitly supplies, otherwise it clears the verdict when the content
            # changed. An edit must never carry the stale verdict forward.
            verification='',
            verification_note='',
        )
        resp = self.create_or_update(patch, user_id, org_id=org_id)
        if isinstance(resp, ErrorResponse):
            return resp

        q.refresh_from_db()
        return ReviewActionResponse(
            status=200,
            message=('Question updated — verification re-opened' if not q.verification
                     else 'Question updated'),
            question=_build_review(q),
        )

    # ── Quality dashboard ─────────────────────────────────────────────────────

    def quality(self, user_id, org_id=None, days=30, bucket='day', min_n=MIN_SAMPLE_N,
                subject=None, exam=None, course_id=None, top=DEFAULT_TOP_N):
        """Aggregate verification stats so generation drift is visible.

        A rising `corrected` rate is the early warning worth watching: it means the
        generator is increasingly shipping keys that turn out to be wrong. A rising
        `flagged` rate means it is shipping questions nobody can confirm.

        Every rate is over `n` = verified + corrected + flagged (see RATED_STATES),
        and is suppressed to None wherever n < min_n (see MIN_SAMPLE_N).
        """
        bucket = 'week' if str(bucket).lower() == 'week' else 'day'
        days = max(1, int(days or 30))
        min_n = max(1, int(min_n or MIN_SAMPLE_N))

        qs = self._scoped(user_id, org_id)
        if subject:
            qs = qs.filter(subject__iexact=subject)
        if exam:
            qs = qs.filter(exam__iexact=exam)
        if course_id:
            qs = qs.filter(course_id=course_id)

        # Rejected questions stay IN these numbers. A rejection is a quality signal —
        # dropping it would flatter the generator by hiding its worst output.
        rows = list(qs.values_list('verification', 'verification_note',
                                   'subject', 'topic', 'exam', 'created_at'))

        overall = _Agg()
        by_subject, by_exam, by_topic, series = (defaultdict(_Agg) for _ in range(4))

        cutoff = timezone.now() - timedelta(days=days)
        for verification, note, subj, top_ic, exm, created_at in rows:
            ai = _ai_state(verification, note)
            overall.add(ai, verification)
            by_subject[subj or '(none)'].add(ai, verification)
            by_exam[exm or '(none)'].add(ai, verification)
            by_topic[top_ic or '(none)'].add(ai, verification)
            if created_at >= cutoff:
                series[_bucket_key(created_at, bucket)].add(ai, verification)

        return QualityResponse(
            min_n=min_n,
            window_days=days,
            bucket=bucket,
            overall=overall.to_group('overall', min_n),
            by_subject=_groups(by_subject, min_n),
            by_exam=_groups(by_exam, min_n),
            by_topic=_groups(by_topic, min_n),
            series=[series[k].to_bucket(k, min_n) for k in sorted(series)],
            worst_subjects=_hotspots(by_subject, 'subject', min_n, top),
            worst_topics=_hotspots(by_topic, 'topic', min_n, top),
        )