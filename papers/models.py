from django.db import models
from django.conf import settings
from courses.models import Course


class Paper(models.Model):
    STATUS_DRAFT     = 'draft'
    STATUS_GENERATED = 'generated'
    STATUS_FAILED    = 'failed'
    STATUS_CHOICES   = [
        (STATUS_DRAFT,     'Draft'),
        (STATUS_GENERATED, 'Generated'),
        (STATUS_FAILED,    'Failed'),
    ]

    org       = models.ForeignKey('users.Organization', on_delete=models.SET_NULL, null=True, blank=True, related_name='papers')
    owner     = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='papers')
    course    = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True, blank=True, related_name='papers')
    blueprint = models.ForeignKey('blueprints.Blueprint', on_delete=models.SET_NULL, null=True, blank=True, related_name='papers')

    title            = models.CharField(max_length=300)
    exam_type        = models.CharField(max_length=100, blank=True, default='')
    subjects         = models.JSONField(default=list)
    difficulty       = models.CharField(max_length=20, default='medium')
    total_marks      = models.IntegerField(default=0)
    duration_minutes = models.IntegerField(default=180)
    instructions     = models.TextField(null=True, blank=True)
    # Legacy JSON blob — kept for the existing paper viewer; populated on every save
    content          = models.JSONField(null=True, blank=True)
    status           = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    source           = models.CharField(max_length=20, default='manual')  # manual | ai
    generation_cost_paise = models.IntegerField(default=0)
    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'pd_papers'
        ordering = ['-created_at']


class GenerationJob(models.Model):
    """A long-running AI generation, tracked out of the request cycle.

    A full NEET paper is 180 questions — tens of LLM calls and several minutes.
    Doing that inside the HTTP request holds a worker open and dies to proxy
    timeouts, so the request now just enqueues a job and returns its id; the
    client polls `progress`/`status` and collects `result` when it's done.
    """
    STATUS_QUEUED  = 'queued'
    STATUS_RUNNING = 'running'
    STATUS_DONE    = 'done'
    STATUS_FAILED  = 'failed'
    STATUS_CHOICES = [
        (STATUS_QUEUED,  'Queued'),
        (STATUS_RUNNING, 'Running'),
        (STATUS_DONE,    'Done'),
        (STATUS_FAILED,  'Failed'),
    ]

    KIND_PAPER     = 'paper'
    KIND_QUESTIONS = 'questions'

    org     = models.ForeignKey('users.Organization', on_delete=models.SET_NULL, null=True, blank=True, related_name='generation_jobs')
    owner   = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='generation_jobs')
    paper   = models.ForeignKey(Paper, on_delete=models.SET_NULL, null=True, blank=True, related_name='generation_jobs')

    kind    = models.CharField(max_length=20, default=KIND_PAPER)
    status  = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_QUEUED)
    # Request params, so the job can be retried or audited.
    params  = models.JSONField(default=dict)

    total_steps = models.IntegerField(default=0)
    done_steps  = models.IntegerField(default=0)
    message     = models.CharField(max_length=300, blank=True, default='')

    result  = models.JSONField(null=True, blank=True)
    error   = models.TextField(blank=True, default='')
    usage   = models.JSONField(default=dict)   # {input_tokens, output_tokens} for metering

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'pd_generation_jobs'
        ordering = ['-created_at']

    @property
    def percent(self) -> int:
        if self.total_steps <= 0:
            return 0
        return min(100, int(self.done_steps * 100 / self.total_steps))


class PaperSection(models.Model):
    paper       = models.ForeignKey(Paper, on_delete=models.CASCADE, related_name='sections')
    subject_ref = models.ForeignKey('subjects.Subject', on_delete=models.SET_NULL, null=True, blank=True, related_name='paper_sections')
    name        = models.CharField(max_length=200)
    order       = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'pd_paper_sections'
        ordering = ['order']


class PaperQuestion(models.Model):
    section        = models.ForeignKey(PaperSection, on_delete=models.CASCADE, related_name='paper_questions')
    # FK to bank question — null when question has not been added to the bank yet
    question       = models.ForeignKey('questions.Question', on_delete=models.SET_NULL, null=True, blank=True, related_name='paper_questions')
    order          = models.PositiveIntegerField(default=0)
    marks_override = models.IntegerField(null=True, blank=True)
    # Snapshot of the question content — used when question FK is null (not yet in bank)
    snapshot       = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = 'pd_paper_questions'
        ordering = ['order']
