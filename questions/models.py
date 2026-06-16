from django.db import models
from django.conf import settings


class Question(models.Model):
    org         = models.ForeignKey('users.Organization', on_delete=models.SET_NULL, null=True, blank=True, related_name='questions')
    course      = models.ForeignKey('courses.Course', on_delete=models.SET_NULL, null=True, blank=True, related_name='questions')
    subject_ref = models.ForeignKey('subjects.Subject', on_delete=models.SET_NULL, null=True, blank=True, related_name='questions')
    topic_ref   = models.ForeignKey('subjects.Topic', on_delete=models.SET_NULL, null=True, blank=True, related_name='questions')
    owner       = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='questions')
    # Display/prompt strings — auto-populated from FK names on save
    exam        = models.CharField(max_length=100)
    subject     = models.CharField(max_length=100)
    topic       = models.CharField(max_length=200)
    q_type      = models.CharField(max_length=50)
    difficulty  = models.CharField(max_length=50)
    bloom       = models.CharField(max_length=50, default='Understand')
    marks       = models.IntegerField(default=1)
    neg_marks   = models.IntegerField(default=0)
    text        = models.TextField()
    options     = models.JSONField(null=True, blank=True)
    explanation = models.TextField(null=True, blank=True)
    image_svg   = models.TextField(null=True, blank=True)
    source      = models.CharField(max_length=20, default='manual')  # manual | ai
    # True when text or any option contains $...$ / $$...$$ math notation.
    # Set automatically on every save via QuestionService / AI generator.
    has_latex   = models.BooleanField(default=False)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'pd_questions'
        ordering = ['-created_at']