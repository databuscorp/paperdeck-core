import logging
import re

from papers.models import Paper, PaperSection, PaperQuestion
from papers.processor.paperprocessor import PaperResponse, PaperSectionResponse
from papers.service.aigeneratorservice import AIGeneratorService
from utility.dbservice import DBService
from utility.utilityobj import SuccessResponse, ErrorResponse

logger = logging.getLogger(__name__)


# Strips a leading option label like "A) ", "(B) ", "C. " so it isn't double-numbered
# by the renderer (which prepends its own "(a) (b) …").
_OPT_PREFIX_RE = re.compile(r'^\s*\(?[A-Da-d][\)\.\]]\s*')


def _normalize_options(q):
    """Convert AI option strings (["A) foo", …]) into builder options
    [{id, text, correct}], using `correct_answer` (a letter) to flag the right one."""
    raw = q.get('options') or []
    corr = (str(q.get('correct_answer') or '')).strip().upper()[:1]
    out = []
    for oi, o in enumerate(raw):
        letter = chr(65 + oi)
        if isinstance(o, dict):
            text = o.get('text') or o.get('label') or ''
            is_correct = bool(o.get('correct')) or (corr == letter)
        else:
            text = _OPT_PREFIX_RE.sub('', str(o)).strip()
            is_correct = (corr == letter)
        out.append({'id': oi + 1, 'text': text, 'correct': is_correct})
    return out


def load_blueprint_spec(blueprint_id):
    """Load a Blueprint into the plain dict the generator consumes.

    The blueprint is the teacher's actual intent — per-section subject, topics,
    question type, count, marks, difficulty and Bloom level. It used to be stored
    on the Paper and then ignored at generation time; feeding it to the prompt is
    what makes a generated paper match the blueprint the user built.
    """
    if not blueprint_id:
        return None
    try:
        from blueprints.models import Blueprint
        bp = Blueprint.objects.prefetch_related('sections').get(id=blueprint_id)
    except Exception:
        return None

    sections = []
    for s in bp.sections.all():
        if not s.count:
            continue
        sections.append({
            'name': s.name,
            'subject': s.subject,
            'topic': (s.topics or '').strip(),
            'q_type': s.q_type or 'MCQ',
            'count': int(s.count),
            'marks_per_q': float(s.marks_per_q or 0) or 4,
            'negative_marks': (
                -abs(float(bp.neg_marking_value or 0)) if bp.neg_marking_enabled
                else -abs(float(s.neg_marks_per_q or 0))
            ),
            'difficulty': s.difficulty or 'Mixed',
            'bloom': s.bloom or 'Mixed',
        })
    if not sections:
        return None
    return {'total_marks': bp.total_marks, 'duration': bp.duration, 'sections': sections}


class _ParamShim:
    """Adapts a params dict back to the attribute access `_normalize_ai_content` wants,
    so the normalizer works identically whether it's called from the request path or
    from a background job (which only has the serialized params)."""

    def __init__(self, params):
        self.title = params.get('title') or ''
        self.difficulty = params.get('difficulty') or 'medium'
        self.total_marks = params.get('total_marks') or 0
        self.duration_minutes = params.get('duration_minutes') or 180
        self.instructions = params.get('instructions') or ''
        self.subjects = params.get('subjects') or []
        # Without this the shim silently reports English for a Hindi paper, because the
        # background path never sees the original request object.
        self.language = params.get('language') or 'English'


def _params_from_req(req, exam_type):
    return {
        'title': req.title,
        'exam_type': exam_type,
        'subjects': req.subjects or [],
        'difficulty': req.difficulty or 'medium',
        'total_marks': req.total_marks or 720,
        'duration_minutes': req.duration_minutes or 180,
        'instructions': req.instructions or '',
        # Carried in params so the ASYNC path (which rebuilds the request from the job
        # row, not from the HTTP request) generates in the same language as the sync one.
        'language': getattr(req, 'language', None) or 'English',
    }


def finalize_generated_paper(paper_id, raw_content, params):
    """Normalize generated content onto the Paper row and build its sections.

    Shared by the synchronous path and the background job so a paper looks the same
    however it was produced.
    """
    paper = Paper.objects.get(id=paper_id)
    content = _normalize_ai_content(raw_content, _ParamShim(params), params.get('exam_type') or '')
    paper.content = content
    paper.status = Paper.STATUS_GENERATED
    paper.save()
    _sync_sections(paper, content.get('sections', []))
    return paper


def job_to_dict(job):
    return {
        'job_id': job.id,
        'paper_id': job.paper_id,
        'kind': job.kind,
        'status': job.status,
        'percent': job.percent,
        'done_steps': job.done_steps,
        'total_steps': job.total_steps,
        'message': job.message,
        'error': job.error,
        'usage': job.usage or {},
        'result': job.result if job.status == 'done' else None,
    }


def _normalize_ai_content(content, req, exam_type):
    """Convert the AI generator's paper JSON into the builder's {meta, sections}
    shape so generated papers round-trip cleanly through the Paper Builder (Edit)
    exactly like manually-built and imported papers."""
    if not isinstance(content, dict):
        return content
    raw_sections = content.get('sections') or []
    sections = []
    for idx, sec in enumerate(raw_sections):
        subject = sec.get('subject') or sec.get('name') or f'Section {idx + 1}'
        questions = []
        for qi, q in enumerate(sec.get('questions') or []):
            questions.append({
                'id':         f'ai-{idx}-{qi}',
                'uid':        f'ai-{idx}-{qi}',
                'exam':       exam_type,
                'subject':    subject,
                'topic':      q.get('topic') or '',
                'type':       q.get('type') or q.get('q_type') or 'MCQ',
                'difficulty': (req.difficulty or 'medium').capitalize(),
                'bloom':      q.get('bloom') or '',
                'marks':      q.get('marks') or 1,
                'text':       q.get('text') or q.get('question') or '',
                'explanation': q.get('explanation'),
                'diagram':    q.get('diagram') or q.get('image_svg'),
                'images':     q.get('images'),
                'options':    _normalize_options(q),
            })
        sections.append({
            'id':           f'ai-sec-{idx}',
            'name':         subject,
            'instructions': '',
            'markLimit':    sum((qq.get('marks') or 0) for qq in questions),
            'questions':    questions,
        })
    total_marks = content.get('total_marks') or req.total_marks or sum(s['markLimit'] for s in sections)
    neg = next((q.get('negative_marks') for s in raw_sections
                for q in (s.get('questions') or []) if q.get('negative_marks')), None)
    meta = {
        'title':        req.title,
        'exam':         exam_type,
        'duration':     f'{req.duration_minutes or 180} min',
        'totalMarks':   total_marks,
        'date':         '',
        'negMarking':   f'{neg} for each wrong answer' if neg else '',
        'instructions': req.instructions or '',
        # The print layer needs to know a paper is bilingual — it decides whether to lay
        # each question out with its translation underneath. Comes off _ParamShim, so it
        # is the same value on the sync and the background-job path.
        'language': getattr(req, 'language', None) or 'English',
    }
    return {'meta': meta, 'sections': sections}


def _build_section_response(sec: PaperSection) -> PaperSectionResponse:
    return PaperSectionResponse(
        id=sec.id,
        name=sec.name,
        order=sec.order,
        subject_id=sec.subject_ref_id,
        question_count=sec.paper_questions.count(),
    )


def _build_paper_response(paper: Paper) -> PaperResponse:
    sections = [_build_section_response(s) for s in paper.sections.all()]
    return PaperResponse(
        id=paper.id,
        title=paper.title,
        difficulty=paper.difficulty,
        total_marks=paper.total_marks,
        duration_minutes=paper.duration_minutes,
        status=paper.status,
        source=paper.source,
        created_at=paper.created_at.isoformat(),
        updated_at=paper.updated_at.isoformat(),
        exam_type=paper.exam_type or None,
        subjects=paper.subjects,
        instructions=paper.instructions,
        content=paper.content,
        org_id=paper.org_id,
        course_id=str(paper.course_id) if paper.course_id else None,
        blueprint_id=paper.blueprint_id,
        sections=sections,
    )


def _resolve_exam_type(course_id, exam_type_fallback):
    """Return exam name from course's ExamAuthority, or fall back to the provided string."""
    if not course_id:
        return exam_type_fallback or ''
    try:
        from courses.models import Course
        course = Course.objects.select_related('authority').get(id=course_id)
        if course.authority:
            return course.authority.name
    except Exception:
        pass
    return exam_type_fallback or ''


def _sync_sections(paper: Paper, sections_data):
    """Replace PaperSection + PaperQuestion rows from the incoming sections array."""
    if not sections_data:
        return
    paper.sections.all().delete()
    for idx, sec_data in enumerate(sections_data):
        sec_name = sec_data.get('name') or sec_data.get('subject') or f'Section {idx + 1}'
        section = PaperSection.objects.create(
            paper=paper,
            name=sec_name,
            order=idx,
        )
        for q_idx, q_data in enumerate(sec_data.get('questions', [])):
            # Link to bank question by ID if present, otherwise snapshot the data
            raw_id = q_data.get('question_id') or q_data.get('id')
            question_id = raw_id if isinstance(raw_id, int) else None
            PaperQuestion.objects.create(
                section=section,
                question_id=question_id,
                order=q_idx,
                marks_override=q_data.get('marks') if question_id else None,
                snapshot=None if question_id else q_data,
            )


class PaperService(DBService):
    def __init__(self, scope):
        super().__init__(scope)

    def fetch_papers(self, user_id, course_id=None, org_id=None):
        if org_id:
            qs = Paper.objects.filter(org_id=org_id)
        else:
            qs = Paper.objects.filter(owner_id=user_id)
        if course_id:
            qs = qs.filter(course_id=course_id)
        return [_build_paper_response(p) for p in qs.prefetch_related('sections__paper_questions')]

    def fetch_paper(self, paper_id, user_id, org_id=None):
        try:
            qs = Paper.objects.prefetch_related('sections__paper_questions')
            if org_id:
                paper = qs.get(id=paper_id, org_id=org_id)
            else:
                paper = qs.get(id=paper_id, owner_id=user_id)
        except Paper.DoesNotExist:
            return ErrorResponse(status=404, message='Paper not found')
        return _build_paper_response(paper)

    def save_paper(self, req, user_id, org_id=None):
        exam_type = _resolve_exam_type(req.course_id, req.exam_type)

        if req.id:
            try:
                if org_id:
                    paper = Paper.objects.get(id=req.id, org_id=org_id)
                else:
                    paper = Paper.objects.get(id=req.id, owner_id=user_id)
            except Paper.DoesNotExist:
                return ErrorResponse(status=404, message='Paper not found')

            paper.title = req.title
            paper.exam_type = exam_type
            paper.total_marks = req.total_marks
            paper.duration_minutes = req.duration_minutes
            if req.course_id is not None:
                paper.course_id = req.course_id or None
            if req.blueprint_id is not None:
                paper.blueprint_id = req.blueprint_id or None
            paper.content = {'meta': req.meta, 'sections': req.sections}
            paper.status = Paper.STATUS_DRAFT
            paper.save()
        else:
            paper = Paper.objects.create(
                owner_id=user_id,
                org_id=org_id,
                course_id=req.course_id or None,
                blueprint_id=req.blueprint_id or None,
                title=req.title,
                exam_type=exam_type,
                subjects=[],
                total_marks=req.total_marks,
                duration_minutes=req.duration_minutes,
                content={'meta': req.meta, 'sections': req.sections},
                status=Paper.STATUS_DRAFT,
                source=req.source or 'manual',
            )

        _sync_sections(paper, req.sections)
        return _build_paper_response(Paper.objects.prefetch_related('sections__paper_questions').get(id=paper.id))

    def _create_draft(self, req, user_id, org_id, exam_type):
        return Paper.objects.create(
            owner_id=user_id,
            org_id=org_id,
            course_id=req.course_id or None,
            blueprint_id=req.blueprint_id or None,
            title=req.title,
            exam_type=exam_type,
            subjects=req.subjects or [],
            difficulty=req.difficulty or 'medium',
            total_marks=req.total_marks or 720,
            duration_minutes=req.duration_minutes or 180,
            instructions=req.instructions,
            status=Paper.STATUS_DRAFT,
            source='ai',
        )

    def generate_paper(self, req, user_id, org_id=None):
        """Synchronous generation — kept for small papers and backward compatibility.

        Prefer `generate_paper_async` for anything large: a full NEET paper is tens
        of LLM calls and will outlive an HTTP request.
        """
        from billing.service.billingservice import BillingService

        exam_type = _resolve_exam_type(req.course_id, req.exam_type)
        params = _params_from_req(req, exam_type)
        params['blueprint'] = load_blueprint_spec(req.blueprint_id)

        # Pay-before-work: refuse (402) if the wallet can't cover the estimated cost, so
        # an org with no credits can't burn AI spend we'd never recover. The real charge
        # is metered from actual usage below.
        billing = BillingService(self._scope_dict() or {})
        gate = billing.preflight(org_id, 'paper', params)
        if gate:
            return gate

        paper = self._create_draft(req, user_id, org_id, exam_type)

        try:
            generator = AIGeneratorService()
            raw_content = generator.generate_paper(
                exam_type=exam_type,
                subjects=req.subjects or [],
                difficulty=req.difficulty or 'medium',
                total_marks=req.total_marks or 720,
                blueprint=params['blueprint'],
                language=params.get('language') or 'English',
            )
            finalize_generated_paper(paper.id, raw_content, params)
        except Exception as e:
            paper.status = Paper.STATUS_FAILED
            paper.save()
            return ErrorResponse(status=500, message=f'Paper generation failed: {str(e)}')

        # Charge here, not in the browser. `paper:<id>` keys the debit so a retry of the
        # same paper can't be billed twice, and a client that never calls the (deprecated)
        # charge endpoint is billed all the same.
        usage = getattr(generator, 'last_usage', None) or {}
        try:
            billing.charge_usage(
                org_id,
                input_tokens=usage.get('input_tokens', 0),
                output_tokens=usage.get('output_tokens', 0),
                # Cached prompt tokens live outside input_tokens and still cost money.
                cache_read_tokens=usage.get('cache_read_input_tokens', 0),
                cache_write_tokens=usage.get('cache_creation_input_tokens', 0),
                reason=f'Paper generation: {req.title}' if req.title else 'Paper generation',
                ref=f'paper:{paper.id}',
            )
        except Exception:
            logger.exception('Could not charge org %s for paper %s (usage=%s)', org_id, paper.id, usage)

        from django.db.models import F
        from users.models import User
        User.objects.filter(id=user_id).update(papers_used=F('papers_used') + 1)

        return _build_paper_response(Paper.objects.prefetch_related('sections__paper_questions').get(id=paper.id))

    def generate_paper_async(self, req, user_id, org_id=None):
        """Enqueue generation and return the job immediately.

        The Paper row is created up-front (status draft) so the client has something
        to navigate to while the job runs.
        """
        from billing.service.billingservice import BillingService
        from papers.models import GenerationJob
        from papers.service import jobservice

        exam_type = _resolve_exam_type(req.course_id, req.exam_type)

        params = _params_from_req(req, exam_type)
        params['blueprint'] = load_blueprint_spec(req.blueprint_id)

        # Gate before anything is created or enqueued — no draft, no job, no AI spend for
        # an org that cannot pay. The job charges the real cost when it finishes.
        gate = BillingService(self._scope_dict() or {}).preflight(org_id, 'paper', params)
        if gate:
            return gate

        paper = self._create_draft(req, user_id, org_id, exam_type)

        job = GenerationJob.objects.create(
            owner_id=user_id,
            org_id=org_id,
            paper=paper,
            kind=GenerationJob.KIND_PAPER,
            params=params,
            status=GenerationJob.STATUS_QUEUED,
            message='Queued',
        )
        jobservice.enqueue(job)
        return SuccessResponse(data=job_to_dict(job))

    def delete_paper(self, paper_id, user_id, org_id=None):
        if org_id:
            deleted, _ = Paper.objects.filter(id=paper_id, org_id=org_id).delete()
        else:
            deleted, _ = Paper.objects.filter(id=paper_id, owner_id=user_id).delete()
        if not deleted:
            return ErrorResponse(status=404, message='Paper not found')
        return SuccessResponse(status=200, message='Paper deleted')