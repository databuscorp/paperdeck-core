from blueprints.models import Blueprint, BlueprintSection
from blueprints.processor.blueprintprocessor import BlueprintResponse, BlueprintSectionResponse
from utility.dbservice import DBService
from utility.utilityobj import ErrorResponse, SuccessResponse


def _build_section(s: BlueprintSection) -> BlueprintSectionResponse:
    return BlueprintSectionResponse(
        id=s.id,
        name=s.name,
        subject=s.subject,
        topics=s.topics,
        q_type=s.q_type,
        count=s.count,
        marks_per_q=float(s.marks_per_q),
        neg_marks_per_q=float(s.neg_marks_per_q),
        difficulty=s.difficulty,
        bloom=s.bloom,
        order=s.order,
    )


def _build(b: Blueprint) -> BlueprintResponse:
    sections = BlueprintSection.objects.filter(blueprint=b)
    return BlueprintResponse(
        id=b.id,
        is_sys=b.is_sys,
        course_id=str(b.course_id) if b.course_id else None,
        course_name=b.course.name if b.course_id else None,
        org_id=b.org_id,
        duration=b.duration,
        total_marks=b.total_marks,
        neg_marking_enabled=b.neg_marking_enabled,
        neg_marking_value=float(b.neg_marking_value),
        sections=[_build_section(s) for s in sections],
        created_at=b.created_at.isoformat(),
    )


class BlueprintService(DBService):
    def __init__(self, scope):
        super().__init__(scope)

    def fetch_all(self, org_id=None, user_id=None, course_id=None):
        from django.db.models import Q
        if course_id:
            # Return sys blueprints + org blueprints for this course
            qs = Blueprint.objects.filter(
                Q(is_sys=True, course_id=course_id) |
                Q(org_id=org_id, course_id=course_id)
            )
        elif org_id:
            qs = Blueprint.objects.filter(org_id=org_id)
        else:
            qs = Blueprint.objects.filter(created_by_id=user_id)
        return [_build(b) for b in qs]

    def fetch_one(self, blueprint_id, org_id=None, user_id=None):
        try:
            if org_id:
                b = Blueprint.objects.get(id=blueprint_id, org_id=org_id)
            else:
                b = Blueprint.objects.get(id=blueprint_id, created_by_id=user_id)
        except Blueprint.DoesNotExist:
            return ErrorResponse(status=404, message='Blueprint not found')
        return _build(b)

    def create_or_update(self, req, user_id, org_id):
        if req.id is not None:
            try:
                existing = Blueprint.objects.get(id=req.id)
                if existing.is_sys:
                    return ErrorResponse(status=403, message='System blueprints cannot be modified')
            except Blueprint.DoesNotExist:
                pass
        if req.id is None:
            b = Blueprint.objects.create(
                course_id=req.course_id or None,
                org_id=org_id,
                created_by_id=user_id,
                duration=req.duration,
                total_marks=req.total_marks,
                neg_marking_enabled=req.neg_marking_enabled,
                neg_marking_value=req.neg_marking_value,
            )
        else:
            try:
                if org_id:
                    b = Blueprint.objects.get(id=req.id, org_id=org_id)
                else:
                    b = Blueprint.objects.get(id=req.id, created_by_id=user_id)
            except Blueprint.DoesNotExist:
                return ErrorResponse(status=404, message='Blueprint not found')
            b.course_id = req.course_id or None
            b.duration = req.duration
            b.total_marks = req.total_marks
            b.neg_marking_enabled = req.neg_marking_enabled
            b.neg_marking_value = req.neg_marking_value
            b.save()

        # Replace all sections atomically
        BlueprintSection.objects.filter(blueprint=b).delete()
        for i, s in enumerate(req.sections):
            BlueprintSection.objects.create(
                blueprint=b,
                name=s.name,
                subject=s.subject,
                topics=s.topics,
                q_type=s.q_type,
                count=s.count,
                marks_per_q=s.marks_per_q,
                neg_marks_per_q=s.neg_marks_per_q,
                difficulty=s.difficulty,
                bloom=s.bloom,
                order=s.order if s.order else i,
            )

        return _build(b)

    def delete(self, blueprint_id, org_id=None, user_id=None):
        try:
            bp = Blueprint.objects.get(id=blueprint_id)
            if bp.is_sys:
                return ErrorResponse(status=403, message='System blueprints cannot be deleted')
        except Blueprint.DoesNotExist:
            return ErrorResponse(status=404, message='Blueprint not found')
        if org_id:
            deleted, _ = Blueprint.objects.filter(id=blueprint_id, org_id=org_id).delete()
        else:
            deleted, _ = Blueprint.objects.filter(id=blueprint_id, created_by_id=user_id).delete()
        if not deleted:
            return ErrorResponse(status=404, message='Blueprint not found')
        return SuccessResponse(status=200, message='Blueprint deleted')
