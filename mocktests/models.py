from django.db import models
from django.conf import settings
from courses.models import Course


class MockTest(models.Model):
    owner        = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='mock_tests')
    course       = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True, blank=True, related_name='mock_tests')
    title        = models.CharField(max_length=300)
    exam         = models.CharField(max_length=100)
    total_q      = models.IntegerField(default=0)
    total_marks  = models.IntegerField(default=0)
    duration     = models.CharField(max_length=50)
    scheduled_on = models.DateTimeField(null=True, blank=True)
    ends_at      = models.DateTimeField(null=True, blank=True)
    status       = models.CharField(max_length=20, default='Upcoming')
    enrolled     = models.IntegerField(default=0)
    attempted    = models.IntegerField(default=0)
    avg_score    = models.FloatField(null=True, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'pd_mock_tests'
        ordering = ['-created_at']
