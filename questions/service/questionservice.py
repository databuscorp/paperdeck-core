from questions.models import Question
from questions.processor.questionprocessor import QuestionResponse
from utility.dbservice import DBService
from utility.utilityobj import SuccessResponse, ErrorResponse


def _build(q: Question) -> QuestionResponse:
    return QuestionResponse(
        id=q.id,
        exam=q.exam,
        subject=q.subject,
        topic=q.topic,
        q_type=q.q_type,
        difficulty=q.difficulty,
        bloom=q.bloom,
        marks=q.marks,
        text=q.text,
        options=q.options,
        explanation=q.explanation,
        created_at=q.created_at.isoformat(),
    )


class QuestionService(DBService):
    def __init__(self, scope):
        super().__init__(scope)

    def fetch_all(self, user_id):
        return [_build(q) for q in Question.objects.filter(owner_id=user_id)]

    def fetch_one(self, question_id, user_id):
        try:
            return _build(Question.objects.get(id=question_id, owner_id=user_id))
        except Question.DoesNotExist:
            return ErrorResponse(status=404, message='Question not found')

    def create_or_update(self, req, user_id):
        if req.id is None:
            q = Question.objects.create(
                owner_id=user_id,
                exam=req.exam,
                subject=req.subject,
                topic=req.topic,
                q_type=req.q_type,
                difficulty=req.difficulty,
                bloom=req.bloom or 'Understand',
                marks=req.marks,
                text=req.text,
                options=req.options,
                explanation=req.explanation,
            )
        else:
            try:
                q = Question.objects.get(id=req.id, owner_id=user_id)
            except Question.DoesNotExist:
                return ErrorResponse(status=404, message='Question not found')
            q.exam = req.exam
            q.subject = req.subject
            q.topic = req.topic
            q.q_type = req.q_type
            q.difficulty = req.difficulty
            q.bloom = req.bloom or q.bloom
            q.marks = req.marks
            q.text = req.text
            q.options = req.options
            q.explanation = req.explanation
            q.save()
        return _build(q)

    def delete(self, question_id, user_id):
        deleted, _ = Question.objects.filter(id=question_id, owner_id=user_id).delete()
        if not deleted:
            return ErrorResponse(status=404, message='Question not found')
        return SuccessResponse(status=200, message='Question deleted')
