"""Push empirical difficulty from graded attempts back onto the question bank.

`itemanalysisservice` computes p_value per PAPER and never writes it anywhere — so the
LLM's guessed `Question.difficulty` is checked against reality on one paper's screen and
then forgotten. This aggregates a question's performance across EVERY graded attempt it
has ever appeared in and stores it on the Question, so future paper/practice assembly can
balance by MEASURED difficulty instead of the guess.

p_value convention is inherited wholesale from itemanalysisservice (read its module
docstring): HIGH p_value = EASY, denominator is everyone who FACED the item (unattempted
counts as not-correct), numerator is status == 'correct' only.

DISCRIMINATION (the 27% index) is deliberately NOT computed here. D is paper-relative — it
ranks a student against the cohort that sat the SAME paper — so it only means something
inside `analyse_paper` and cannot be aggregated across papers. It stays there.
"""
from django.db.models import Count, Q
from django.utils import timezone

from attempts.models import QuestionResponse, StudentAttempt
from attempts.service.itemanalysisservice import MIN_STUDENTS, calibrate_difficulty
from questions.models import Question


def recalibrate(org_id=None, min_students=None) -> dict:
    """Aggregate graded responses per question and write empirical difficulty onto the bank.

    Only questions with response_count >= min_students are touched; the rest keep whatever
    calibration (or none) they already had — a handful of responses is noise, and wiping a
    good prior calibration because this run saw too few attempts would be worse than useless.
    """
    if min_students is None:
        min_students = MIN_STUDENTS

    # Count faced (any real graded status) and correct, per question, in ONE grouped query.
    # question_id is NULL for paper-only snapshot questions — they have no bank row to write
    # to, so exclude them here rather than aggregating rows we can never persist.
    responses = QuestionResponse.objects.filter(
        attempt__status=StudentAttempt.STATUS_GRADED,
        question_id__isnull=False,
        status__in=[
            QuestionResponse.STATUS_CORRECT,
            QuestionResponse.STATUS_INCORRECT,
            QuestionResponse.STATUS_PARTIAL,
            QuestionResponse.STATUS_UNATTEMPTED,
        ],
    )
    if org_id is not None:
        responses = responses.filter(attempt__org_id=org_id)

    rows = responses.values('question_id').annotate(
        n_faced=Count('id'),
        n_correct=Count('id', filter=Q(status=QuestionResponse.STATUS_CORRECT)),
    )

    to_update = []
    skipped = 0
    now = timezone.now()
    stats = {r['question_id']: r for r in rows}

    # Fetch only the questions we actually have data for, in one query.
    questions = Question.objects.filter(id__in=stats.keys())
    for question in questions:
        try:
            row = stats[question.id]
            n_faced = row['n_faced']
            if n_faced < min_students:
                skipped += 1
                continue
            p_value = round(row['n_correct'] / n_faced, 4)
            question.empirical_p_value = p_value
            question.empirical_difficulty = calibrate_difficulty(p_value) or ''
            question.response_count = n_faced
            question.calibrated_at = now
            to_update.append(question)
        except Exception:
            # One malformed row must never sink the whole recalibration run.
            continue

    if to_update:
        Question.objects.bulk_update(
            to_update,
            ['empirical_p_value', 'empirical_difficulty', 'response_count', 'calibrated_at'],
        )

    return {
        'calibrated': len(to_update),
        'skipped_below_threshold': skipped,
        'min_students': min_students,
    }
