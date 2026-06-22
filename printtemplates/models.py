from django.db import models
from django.conf import settings


class PrintTemplate(models.Model):
    org          = models.ForeignKey('users.Organization', on_delete=models.CASCADE, related_name='print_templates')
    created_by   = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='print_templates')
    updated_by   = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='print_templates_updated')
    name         = models.CharField(max_length=200)
    # Structured, no-code style definition (JSON) authored by the visual editor.
    style_config = models.TextField(blank=True, default='{}')
    is_active    = models.BooleanField(default=False)
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'pd_print_templates'
        ordering = ['-created_at']


class PrintTemplateAudit(models.Model):
    """Change trace for org print templates (survives template deletion)."""
    org           = models.ForeignKey('users.Organization', on_delete=models.CASCADE, related_name='print_template_audits')
    template_id   = models.IntegerField(null=True, blank=True)   # not a FK, so deletes are retained
    template_name = models.CharField(max_length=200, blank=True, default='')
    action        = models.CharField(max_length=20)              # created | updated | activated | deleted
    user          = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    user_name     = models.CharField(max_length=200, blank=True, default='')
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'pd_print_template_audits'
        ordering = ['-created_at']
