from printtemplates.models import PrintTemplate
from printtemplates.processor.printtemplateprocessor import PrintTemplateResponse
from utility.dbservice import DBService
from utility.utilityobj import ErrorResponse, SuccessResponse


def _build(t: PrintTemplate) -> PrintTemplateResponse:
    return PrintTemplateResponse(
        id=t.id,
        org_id=t.org_id,
        name=t.name,
        style_config=t.style_config or '{}',
        is_active=t.is_active,
        created_at=t.created_at.isoformat(),
    )


class PrintTemplateService(DBService):
    def __init__(self, scope):
        super().__init__(scope)

    def fetch_all(self, org_id):
        return [_build(t) for t in PrintTemplate.objects.filter(org_id=org_id)]

    def fetch_active(self, org_id):
        t = PrintTemplate.objects.filter(org_id=org_id, is_active=True).first()
        return _build(t) if t else None

    def create_or_update(self, req, user_id, org_id):
        if req.id is None:
            t = PrintTemplate.objects.create(
                org_id=org_id,
                created_by_id=user_id,
                name=req.name,
                style_config=req.style_config or '{}',
                is_active=False,
            )
        else:
            try:
                t = PrintTemplate.objects.get(id=req.id, org_id=org_id)
            except PrintTemplate.DoesNotExist:
                return ErrorResponse(status=404, message='Print template not found')
            t.name = req.name
            t.style_config = req.style_config or '{}'
            t.save()

        # Activation rules: a request can explicitly activate this template, and an
        # org must always have exactly one active template once it has any at all.
        has_active = PrintTemplate.objects.filter(org_id=org_id, is_active=True).exclude(id=t.id).exists()
        if req.is_active or not has_active:
            PrintTemplate.objects.filter(org_id=org_id).exclude(id=t.id).update(is_active=False)
            t.is_active = True
            t.save(update_fields=['is_active'])

        return _build(t)

    def set_active(self, template_id, org_id):
        try:
            t = PrintTemplate.objects.get(id=template_id, org_id=org_id)
        except PrintTemplate.DoesNotExist:
            return ErrorResponse(status=404, message='Print template not found')
        PrintTemplate.objects.filter(org_id=org_id).exclude(id=t.id).update(is_active=False)
        t.is_active = True
        t.save(update_fields=['is_active'])
        return _build(t)

    def delete(self, template_id, org_id):
        try:
            t = PrintTemplate.objects.get(id=template_id, org_id=org_id)
        except PrintTemplate.DoesNotExist:
            return ErrorResponse(status=404, message='Print template not found')
        was_active = t.is_active
        t.delete()
        # If the active template was removed, promote the most-recent remaining one.
        if was_active:
            nxt = PrintTemplate.objects.filter(org_id=org_id).first()
            if nxt:
                nxt.is_active = True
                nxt.save(update_fields=['is_active'])
        return SuccessResponse(status=200, message='Print template deleted')
