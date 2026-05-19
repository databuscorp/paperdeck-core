from papers.models import Paper
from papers.processor.paperprocessor import PaperResponse
from papers.service.aigeneratorservice import AIGeneratorService
from utility.dbservice import DBService
from utility.utilityobj import SuccessResponse, ErrorResponse


def _build_paper_response(paper: Paper) -> PaperResponse:
    return PaperResponse(
        id=paper.id,
        title=paper.title,
        exam_type=paper.exam_type,
        subjects=paper.subjects,
        difficulty=paper.difficulty,
        total_marks=paper.total_marks,
        duration_minutes=paper.duration_minutes,
        instructions=paper.instructions,
        content=paper.content,
        status=paper.status,
        created_at=paper.created_at.isoformat(),
        updated_at=paper.updated_at.isoformat(),
        course_id=paper.course_id,
    )


class PaperService(DBService):
    def __init__(self, scope):
        super().__init__(scope)

    def fetch_papers(self, user_id, course_id=None):
        qs = Paper.objects.filter(owner_id=user_id)
        if course_id:
            qs = qs.filter(course_id=course_id)
        return [_build_paper_response(p) for p in qs]

    def fetch_paper(self, paper_id, user_id):
        try:
            paper = Paper.objects.get(id=paper_id, owner_id=user_id)
        except Paper.DoesNotExist:
            return ErrorResponse(status=404, message='Paper not found')
        return _build_paper_response(paper)

    def generate_paper(self, req, user_id):
        paper = Paper.objects.create(
            owner_id=user_id,
            course_id=req.course_id,
            title=req.title,
            exam_type=req.exam_type,
            subjects=req.subjects,
            difficulty=req.difficulty or 'medium',
            total_marks=req.total_marks or 720,
            duration_minutes=req.duration_minutes or 180,
            instructions=req.instructions,
            status=Paper.STATUS_DRAFT,
        )

        try:
            generator = AIGeneratorService()
            content = generator.generate_paper(
                exam_type=req.exam_type,
                subjects=req.subjects,
                difficulty=req.difficulty or 'medium',
                total_marks=req.total_marks or 720,
            )
            paper.content = content
            paper.status = Paper.STATUS_GENERATED
            paper.save()
        except Exception as e:
            paper.status = Paper.STATUS_FAILED
            paper.save()
            return ErrorResponse(status=500, message=f'Paper generation failed: {str(e)}')

        from users.models import User
        User.objects.filter(id=user_id).update(papers_used=User.objects.get(id=user_id).papers_used + 1)

        return _build_paper_response(paper)

    def save_paper(self, req, user_id):
        if req.id:
            try:
                paper = Paper.objects.get(id=req.id, owner_id=user_id)
            except Paper.DoesNotExist:
                return ErrorResponse(status=404, message='Paper not found')
            paper.title = req.title
            paper.exam_type = req.exam_type
            paper.total_marks = req.total_marks
            paper.duration_minutes = req.duration_minutes
            paper.content = {'meta': req.meta, 'sections': req.sections}
            paper.status = Paper.STATUS_DRAFT
            paper.save()
        else:
            paper = Paper.objects.create(
                owner_id=user_id,
                title=req.title,
                exam_type=req.exam_type,
                subjects=[],
                total_marks=req.total_marks,
                duration_minutes=req.duration_minutes,
                content={'meta': req.meta, 'sections': req.sections},
                status=Paper.STATUS_DRAFT,
            )
        return _build_paper_response(paper)

    def delete_paper(self, paper_id, user_id):
        deleted, _ = Paper.objects.filter(id=paper_id, owner_id=user_id).delete()
        if not deleted:
            return ErrorResponse(status=404, message='Paper not found')
        return SuccessResponse(status=200, message='Paper deleted')
