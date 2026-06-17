from django.db import models
from django.conf import settings


class PrintTemplate(models.Model):
    org         = models.ForeignKey('users.Organization', on_delete=models.CASCADE, related_name='print_templates')
    created_by  = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='print_templates')
    name         = models.CharField(max_length=200)
    # Structured, no-code style definition (JSON) authored by the visual editor.
    style_config = models.TextField(blank=True, default='{}')
    is_active    = models.BooleanField(default=False)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'pd_print_templates'
        ordering = ['-created_at']
