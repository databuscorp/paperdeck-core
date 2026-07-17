"""Adaptive practice: generate a fresh question set aimed at a student's weak topics.

This closes the loop from attempts back into generation. `ItemAnalysisService.student_summary`
already produces the "what should this kid revise" list (topics, weakest first, from every
graded attempt); this service takes that list and asks the generator for NEW questions on
those exact topics — so a student's practice targets what they actually get wrong, instead of
random drilling.

Fresh generation (not bank re-service) is deliberate: the point is questions the student has
NOT seen, and `generate_questions` already dedupes against the existing bank.
"""
import logging
from typing import Dict

from attempts.models import StudentAttempt
from papers.service.aigeneratorservice import AIGeneratorService

logger = logging.getLogger(__name__)

_USAGE_FIELDS = ('input_tokens', 'output_tokens',
                 'cache_creation_input_tokens', 'cache_read_input_tokens')

# A topic counts as "weak" below this cohort-independent accuracy; if a student is weak
# nowhere yet (all above), we still practise their relatively-weakest topics.
_WEAK_ACCURACY = 0.6


def _add(into: Dict, src: Dict) -> None:
    for f in _USAGE_FIELDS:
        into[f] = into.get(f, 0) + int((src or {}).get(f, 0) or 0)


class AdaptivePracticeService:
    def __init__(self, scope):
        self.scope = scope
        self.org_id = (scope or {}).get('org_id')

    def _exam_for_student(self, student_id) -> str:
        qs = StudentAttempt.objects.filter(
            student_id=student_id, status=StudentAttempt.STATUS_GRADED
        ).select_related('paper')
        if self.org_id:
            qs = qs.filter(org_id=self.org_id)
        for a in qs.order_by('-started_at'):
            exam = getattr(a.paper, 'exam', '') if a.paper_id else ''
            if exam:
                return exam
        # No paper (e.g. OMR-only attempts) — fall back to the exam tagged on a question the
        # student actually answered, so the generated practice matches their exam.
        from questions.models import Question
        exam = (Question.objects.filter(responses__attempt__student_id=student_id)
                .exclude(exam='').values_list('exam', flat=True).first())
        return exam or ''

    @staticmethod
    def _allocate(count: int, k: int):
        """Spread `count` questions across `k` weakest topics, weakest topics first."""
        base, extra = divmod(count, k)
        return [base + (1 if i < extra else 0) for i in range(k)]

    def generate(self, student_id, count=10, language='English', max_topics=3) -> dict:
        from attempts.service.itemanalysisservice import ItemAnalysisService

        count = max(1, min(int(count or 10), 40))
        max_topics = max(1, min(int(max_topics or 3), 6))

        summary = ItemAnalysisService(self.scope).student_summary(student_id)
        # `summary.topics` is already weakest-first. Prefer genuinely-weak topics; if the
        # student is above the bar everywhere, still drill their relatively-weakest few.
        weak = [t for t in summary.topics if t.accuracy < _WEAK_ACCURACY] or list(summary.topics)
        weak = weak[:max_topics]

        if not weak:
            return {
                'questions': [], 'targeted_topics': [], 'usage': {}, 'usage_by_phase': {},
                'message': ('No graded attempts yet for this student — they need to sit a '
                            'test first so we can find weak areas to target.'),
            }

        exam = self._exam_for_student(student_id)
        alloc = self._allocate(count, len(weak))
        gen = AIGeneratorService()

        questions: list = []
        targeted: list = []
        usage: Dict = {}
        usage_by_phase: Dict = {}

        for topic_stat, n in zip(weak, alloc):
            if n <= 0:
                continue
            try:
                got = gen.generate_questions(
                    exam=exam, subject=topic_stat.subject, topic=topic_stat.topic,
                    q_type='MCQ', difficulty='Mixed', bloom='Mixed', count=n,
                    language=language,
                )
            except Exception:
                logger.exception("Adaptive practice generation failed for topic %r",
                                 topic_stat.topic)
                got = []
            questions.extend(got)
            # generate_questions RESETS last_usage per call, so accumulate after each one.
            _add(usage, gen.last_usage)
            for phase, u in (gen.usage_by_phase or {}).items():
                _add(usage_by_phase.setdefault(phase, {}), u)
            targeted.append({
                'topic': topic_stat.topic, 'subject': topic_stat.subject,
                'accuracy': topic_stat.accuracy, 'requested': n, 'generated': len(got),
            })

        return {
            'questions': questions, 'targeted_topics': targeted,
            'usage': usage, 'usage_by_phase': usage_by_phase,
            'message': 'ok',
        }
