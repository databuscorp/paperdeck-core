from django.contrib.auth import get_user_model

from printtemplates.models import PrintTemplate, PrintTemplateAudit
from printtemplates.processor.printtemplateprocessor import PrintTemplateResponse
from utility.dbservice import DBService
from utility.utilityobj import ErrorResponse, SuccessResponse

User = get_user_model()


def _user_name(user_id):
    if not user_id:
        return ''
    try:
        u = User.objects.get(id=user_id)
        full = (f'{u.first_name} {u.last_name}').strip()
        return full or u.username
    except User.DoesNotExist:
        return ''


def _build(t: PrintTemplate) -> PrintTemplateResponse:
    return PrintTemplateResponse(
        id=t.id,
        org_id=t.org_id,
        name=t.name,
        style_config=t.style_config or '{}',
        is_active=t.is_active,
        created_at=t.created_at.isoformat(),
        updated_at=t.updated_at.isoformat() if t.updated_at else None,
        created_by_name=_user_name(t.created_by_id),
        updated_by_name=_user_name(t.updated_by_id),
    )


class PrintTemplateService(DBService):
    def __init__(self, scope):
        super().__init__(scope)

    def _audit(self, org_id, template, action, user_id):
        PrintTemplateAudit.objects.create(
            org_id=org_id,
            template_id=getattr(template, 'id', None),
            template_name=getattr(template, 'name', ''),
            action=action,
            user_id=user_id,
            user_name=_user_name(user_id),
        )

    def fetch_all(self, org_id):
        return [_build(t) for t in PrintTemplate.objects.filter(org_id=org_id)]

    def fetch_active(self, org_id):
        t = PrintTemplate.objects.filter(org_id=org_id, is_active=True).first()
        return _build(t) if t else None

    def fetch_audit(self, org_id, limit=30):
        rows = PrintTemplateAudit.objects.filter(org_id=org_id)[:limit]
        return [{
            'id': a.id, 'template_id': a.template_id, 'template_name': a.template_name,
            'action': a.action, 'user_name': a.user_name, 'created_at': a.created_at.isoformat(),
        } for a in rows]

    def create_or_update(self, req, user_id, org_id):
        is_new = req.id is None
        if is_new:
            t = PrintTemplate.objects.create(
                org_id=org_id,
                created_by_id=user_id,
                updated_by_id=user_id,
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
            t.updated_by_id = user_id
            t.save()

        # Activation rules: a request can explicitly activate this template, and an
        # org must always have exactly one active template once it has any at all.
        has_active = PrintTemplate.objects.filter(org_id=org_id, is_active=True).exclude(id=t.id).exists()
        if req.is_active or not has_active:
            PrintTemplate.objects.filter(org_id=org_id).exclude(id=t.id).update(is_active=False)
            t.is_active = True
            t.save(update_fields=['is_active'])

        self._audit(org_id, t, 'created' if is_new else 'updated', user_id)
        return _build(t)

    def set_active(self, template_id, org_id, user_id=None):
        try:
            t = PrintTemplate.objects.get(id=template_id, org_id=org_id)
        except PrintTemplate.DoesNotExist:
            return ErrorResponse(status=404, message='Print template not found')
        PrintTemplate.objects.filter(org_id=org_id).exclude(id=t.id).update(is_active=False)
        t.is_active = True
        t.save(update_fields=['is_active'])
        self._audit(org_id, t, 'activated', user_id)
        return _build(t)

    def delete(self, template_id, org_id, user_id=None):
        try:
            t = PrintTemplate.objects.get(id=template_id, org_id=org_id)
        except PrintTemplate.DoesNotExist:
            return ErrorResponse(status=404, message='Print template not found')
        was_active = t.is_active
        # Snapshot for the audit before deleting.
        self._audit(org_id, t, 'deleted', user_id)
        t.delete()
        # If the active template was removed, promote the most-recent remaining one.
        if was_active:
            nxt = PrintTemplate.objects.filter(org_id=org_id).first()
            if nxt:
                nxt.is_active = True
                nxt.save(update_fields=['is_active'])
        return SuccessResponse(status=200, message='Print template deleted')
