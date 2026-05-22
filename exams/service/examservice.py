from exams.models import ExamTemplate, ExamAuthority
from exams.processor.examprocessor import ExamTemplateResponse, ExamAuthorityResponse, ExamAuthorityRequest
from utility.utilityobj import SuccessResponse, ErrorResponse


def _build_authority_response(a: ExamAuthority) -> ExamAuthorityResponse:
    return ExamAuthorityResponse(
        id=str(a.id),
        name=a.name,
        short_name=a.short_name,
        authority_type=a.authority_type,
        description=a.description,
        website=a.website,
        is_active=a.is_active,
        is_sys=a.is_sys,
        created_at=a.created_at.isoformat(),
    )


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


class ExamAuthorityService:
    def fetch_all(self, org_id=None):
        # Return sys authorities + org's own authorities
        from django.db.models import Q
        qs = ExamAuthority.objects.filter(is_active=True).filter(
            Q(is_sys=True) | Q(org_id=org_id)
        )
        return [_build_authority_response(a) for a in qs]

    def create_or_update(self, req: ExamAuthorityRequest, org_id=None):
        if req.id is None:
            authority = ExamAuthority.objects.create(
                org_id=org_id,
                name=req.name,
                short_name=req.short_name,
                authority_type=req.authority_type,
                description=req.description,
                website=req.website,
                is_active=req.is_active if req.is_active is not None else True,
                is_sys=False,
            )
        else:
            try:
                qs = ExamAuthority.objects.filter(id=req.id, is_sys=False)
                if org_id:
                    qs = qs.filter(org_id=org_id)
                authority = qs.get()
            except ExamAuthority.DoesNotExist:
                return ErrorResponse(status=404, message='Authority not found')
            authority.name = req.name
            authority.short_name = req.short_name
            authority.authority_type = req.authority_type
            authority.description = req.description
            authority.website = req.website
            if req.is_active is not None:
                authority.is_active = req.is_active
            authority.save()
        return _build_authority_response(authority)

    def delete(self, authority_id: str, org_id=None):
        qs = ExamAuthority.objects.filter(id=authority_id, is_sys=False)
        if org_id:
            qs = qs.filter(org_id=org_id)
        deleted, _ = qs.delete()
        if not deleted:
            return ErrorResponse(status=404, message='Authority not found or cannot delete system authority')
        return SuccessResponse(status=200, message='Authority deleted')
