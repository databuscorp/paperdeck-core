from django.db import models


class StudentAttempt(models.Model):
    """One student's sitting of one paper / mock test.

    This is the row PaperDeck never had: until now a paper was generated, printed and
    forgotten, and the only trace a cohort left behind was `MockTest.attempted` and
    `MockTest.avg_score`. Without per-response data no item analysis is possible, so
    the LLM's guessed `difficulty` could never be checked against reality.
    """

    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_SUBMITTED   = 'submitted'
    STATUS_GRADED      = 'graded'
    STATUS_CHOICES = [
        (STATUS_IN_PROGRESS, 'In progress'),
        (STATUS_SUBMITTED,   'Submitted'),
        (STATUS_GRADED,      'Graded'),
    ]

    SOURCE_ONLINE = 'online'   # student took it in an online test player
    SOURCE_OMR    = 'omr'      # scanned OMR sheet
    SOURCE_MANUAL = 'manual'   # a teacher keyed the marks in by hand
    SOURCE_CHOICES = [
        (SOURCE_ONLINE, 'Online'),
        (SOURCE_OMR,    'OMR'),
        (SOURCE_MANUAL, 'Manual'),
    ]

    org       = models.ForeignKey('users.Organization', on_delete=models.CASCADE, null=True, blank=True, related_name='student_attempts')
    student   = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='attempts')
    # Exactly one of these two is normally set. A paper attempt can be graded (we have
    # the answer key); a mock-test-only attempt may only carry a score.
    paper     = models.ForeignKey('papers.Paper', on_delete=models.SET_NULL, null=True, blank=True, related_name='attempts')
    mock_test = models.ForeignKey('mocktests.MockTest', on_delete=models.SET_NULL, null=True, blank=True, related_name='attempts')

    started_at   = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    status       = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_IN_PROGRESS)

    total_score  = models.FloatField(default=0)
    max_score    = models.FloatField(default=0)
    source       = models.CharField(max_length=20, choices=SOURCE_CHOICES, default=SOURCE_ONLINE)

    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'pd_student_attempts'
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['org', 'paper'], name='pd_attempt_org_paper_idx'),
            models.Index(fields=['student'],      name='pd_attempt_student_idx'),
        ]


class QuestionResponse(models.Model):
    """What one student did with one question on one attempt.

    UNATTEMPTED IS NOT WRONG. Conflating the two is the classic item-analysis bug: a
    hard question most students *skip* would look identical to one most students get
    *wrong*, and under negative marking the two carry very different scores. So the
    outcome is stored explicitly in `status`:

        unattempted — left blank.                            marks_awarded = 0,  is_correct = None
        correct     — full credit.                                               is_correct = True
        partial     — Multiple Correct only: a strict subset                     is_correct = False
                      of the correct options and no wrong one.
        incorrect   — answered, and wrong.                                       is_correct = False

    `is_correct` is a nullable convenience mirror (None == ungraded/unattempted), but
    `status` is the source of truth — query it, not `is_correct`, when you need to tell
    "skipped" from "wrong".
    """

    STATUS_UNATTEMPTED = 'unattempted'
    STATUS_CORRECT     = 'correct'
    STATUS_PARTIAL     = 'partial'
    STATUS_INCORRECT   = 'incorrect'
    STATUS_CHOICES = [
        (STATUS_UNATTEMPTED, 'Unattempted'),
        (STATUS_CORRECT,     'Correct'),
        (STATUS_PARTIAL,     'Partial'),
        (STATUS_INCORRECT,   'Incorrect'),
    ]

    attempt  = models.ForeignKey(StudentAttempt, on_delete=models.CASCADE, related_name='responses')
    # Null when the paper question was never promoted into the bank (PaperQuestion.snapshot).
    question = models.ForeignKey('questions.Question', on_delete=models.SET_NULL, null=True, blank=True, related_name='responses')
    # Stable identity of a paper-only question: the PaperQuestion row id, as a string.
    question_snapshot_id = models.CharField(max_length=64, blank=True, default='')

    # Single-correct MCQ: 0-based index into the question's `options` list.
    selected_option_index   = models.IntegerField(null=True, blank=True)
    # Multiple Correct: list of 0-based indices, e.g. [0, 2].
    selected_option_indices = models.JSONField(null=True, blank=True)
    # Numerical ("TITA") questions.
    numeric_answer          = models.FloatField(null=True, blank=True)

    is_correct         = models.BooleanField(null=True, blank=True)
    status             = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_UNATTEMPTED)
    marks_awarded      = models.FloatField(default=0)
    time_spent_seconds = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = 'pd_question_responses'
        unique_together = [('attempt', 'question')]
        indexes = [
            models.Index(fields=['question'], name='pd_qresp_question_idx'),
        ]

    @property
    def item_key(self) -> str:
        """Identity used to group this response with the same item across students."""
        if self.question_id:
            return f'q:{self.question_id}'
        return f's:{self.question_snapshot_id}'
