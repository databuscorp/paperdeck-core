from django.db import models
from django.conf import settings


class Blueprint(models.Model):
    course              = models.ForeignKey('courses.Course', on_delete=models.SET_NULL, null=True, blank=True, related_name='blueprints')
    org                 = models.ForeignKey('users.Organization', on_delete=models.CASCADE, null=True, blank=True, related_name='blueprints')
    is_sys              = models.BooleanField(default=False)
    created_by          = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='blueprints')
    duration            = models.CharField(max_length=50, default='3 Hours')
    total_marks         = models.IntegerField(default=0)
    neg_marking_enabled = models.BooleanField(default=False)
    neg_marking_value   = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    created_at          = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'pd_blueprints'
        ordering = ['-created_at']


class BlueprintSection(models.Model):
    blueprint       = models.ForeignKey(Blueprint, on_delete=models.CASCADE, related_name='sections')
    name            = models.CharField(max_length=200)
    subject         = models.CharField(max_length=200)
    topics          = models.TextField(blank=True, default='')
    q_type          = models.CharField(max_length=50)
    count           = models.PositiveIntegerField(default=0)
    marks_per_q     = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    neg_marks_per_q = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    difficulty      = models.CharField(max_length=50, default='Mixed')
    bloom           = models.CharField(max_length=50, default='Mixed')
    order           = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'pd_blueprint_sections'
        ordering = ['order']
