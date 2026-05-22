from questions.models import Question
from questions.processor.questionprocessor import QuestionResponse
from utility.dbservice import DBService
from utility.utilityobj import SuccessResponse, ErrorResponse


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
        image_svg=q.image_svg,
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


class QuestionService(DBService):
    def __init__(self, scope):
        super().__init__(scope)

    def fetch_all(self, user_id, org_id=None, course_id=None):
        if org_id:
            # Show all org questions — any staff member can view
            qs = Question.objects.filter(org_id=org_id)
        else:
            qs = Question.objects.filter(owner_id=user_id)

        if course_id:
            qs = qs.filter(course_id=course_id)

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
                image_svg=req.image_svg,
                source=req.source or 'manual',
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
            q.text = req.text
            q.options = req.options
            q.explanation = req.explanation
            q.image_svg = req.image_svg
            if req.source:
                q.source = req.source
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