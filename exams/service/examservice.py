from exams.models import ExamTemplate
from exams.processor.examprocessor import ExamTemplateResponse


class ExamTemplateService:
    def fetch_all(self):
        return [
            ExamTemplateResponse(
                id=t.id,
                name=t.name,
                duration=t.duration,
                total_marks=t.total_marks,
                neg_marking=t.neg_marking,
                sections=t.sections,
                is_default=t.is_default,
                created_at=t.created_at.isoformat(),
            )
            for t in ExamTemplate.objects.all()
        ]
