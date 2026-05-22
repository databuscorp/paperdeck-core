from papers.models import Paper, PaperSection, PaperQuestion
from papers.processor.paperprocessor import PaperResponse, PaperSectionResponse
from papers.service.aigeneratorservice import AIGeneratorService
from utility.dbservice import DBService
from utility.utilityobj import SuccessResponse, ErrorResponse


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
                source='manual',
            )

        _sync_sections(paper, req.sections)
        return _build_paper_response(Paper.objects.prefetch_related('sections__paper_questions').get(id=paper.id))

    def generate_paper(self, req, user_id, org_id=None):
        exam_type = _resolve_exam_type(req.course_id, req.exam_type)

        paper = Paper.objects.create(
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

        try:
            generator = AIGeneratorService()
            content = generator.generate_paper(
                exam_type=exam_type,
                subjects=req.subjects or [],
                difficulty=req.difficulty or 'medium',
                total_marks=req.total_marks or 720,
            )
            paper.content = content
            paper.status = Paper.STATUS_GENERATED
            paper.save()
            _sync_sections(paper, content.get('sections', []))
        except Exception as e:
            paper.status = Paper.STATUS_FAILED
            paper.save()
            return ErrorResponse(status=500, message=f'Paper generation failed: {str(e)}')

        from django.db.models import F
        from users.models import User
        User.objects.filter(id=user_id).update(papers_used=F('papers_used') + 1)

        return _build_paper_response(Paper.objects.prefetch_related('sections__paper_questions').get(id=paper.id))

    def delete_paper(self, paper_id, user_id, org_id=None):
        if org_id:
            deleted, _ = Paper.objects.filter(id=paper_id, org_id=org_id).delete()
        else:
            deleted, _ = Paper.objects.filter(id=paper_id, owner_id=user_id).delete()
        if not deleted:
            return ErrorResponse(status=404, message='Paper not found')
        return SuccessResponse(status=200, message='Paper deleted')