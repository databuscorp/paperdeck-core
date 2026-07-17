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
    # `explanation` is one sentence — why the key is the key. `solution` is the full
    # worked derivation, step by step, with LaTeX. They are separate on purpose: the
    # question paper prints neither, the answer key prints the explanation, and the
    # solution booklet (what coaching institutes actually sell) prints the solution.
    # Collapsing them into one field would force every surface to show the same thing.
    explanation = models.TextField(null=True, blank=True)
    solution    = models.TextField(null=True, blank=True)
    # Translations of this question, keyed by ISO code:
    #   {"hi": {"text": ..., "solution": ..., "options": [{"text": ...}, ...]}}
    # The translated options are TEXT ONLY and positional — `correct` is never stored
    # here. The answer key lives in `options` (the English list) and nowhere else, so a
    # mistranslated distractor can never turn into a second correct answer. A translation
    # whose option count doesn't match is rejected at generation rather than stored.
    translations = models.JSONField(null=True, blank=True)
    image_svg   = models.TextField(null=True, blank=True)
    # Inline images referenced by [[IMG:n]] markers in `text` — {"1": dataUrl, ...}.
    images      = models.JSONField(null=True, blank=True)
    source      = models.CharField(max_length=20, default='manual')  # manual | ai | import
    # Previous-year questions. These are the single most valuable grounding material for
    # JEE/NEET — a real 2023 NEET question tells the generator what the exam actually
    # asks far better than any instruction can — so they are marked and retrieved
    # preferentially as style exemplars. `year` is the year the question was SET, and it
    # orders the exemplars: recent papers reflect the current syllabus and question style.
    is_pyq      = models.BooleanField(default=False)
    year        = models.IntegerField(null=True, blank=True)
    # True when text or any option contains $...$ / $$...$$ math notation.
    # Set automatically on every save via QuestionService / AI generator.
    has_latex   = models.BooleanField(default=False)

    # Numerical-answer questions carry no options, so the key has to live here.
    numeric_answer = models.FloatField(null=True, blank=True)
    unit           = models.CharField(max_length=50, blank=True, default='')

    # Answer-key verification (papers/service/verificationservice.py).
    #   verified  — an independent blind re-solve agreed with the key
    #   corrected — the key was wrong and has been fixed
    #   flagged   — could not be confirmed; a human should review it
    #   skipped   — not auto-verifiable (e.g. long answer)
    #   ''        — never verified (manual entry, import, pre-existing rows)
    VERIFICATION_CHOICES = [
        ('verified',  'Verified'),
        ('corrected', 'Corrected'),
        ('flagged',   'Flagged'),
        ('skipped',   'Skipped'),
    ]
    verification      = models.CharField(max_length=20, blank=True, default='')
    verification_note = models.TextField(blank=True, default='')

    # Empirical difficulty — what students ACTUALLY did with this question, not the LLM's
    # guess in `difficulty`. Written by attempts/service/calibrationservice.py from graded
    # attempts so paper/practice assembly can balance by MEASURED difficulty.
    #   empirical_p_value is the proportion who got it RIGHT among everyone who FACED it
    #   (unattempted counts as not-correct). HIGH p_value MEANS THE QUESTION IS EASY —
    #   p = 0.9 is a giveaway, p = 0.1 is brutal. `difficulty` is the guess; this is reality.
    empirical_p_value    = models.FloatField(null=True, blank=True)
    empirical_difficulty = models.CharField(max_length=20, blank=True, default='')   # calibrate_difficulty(p_value) label
    response_count       = models.IntegerField(default=0)                            # graded responses backing the calibration
    calibrated_at        = models.DateTimeField(null=True, blank=True)

    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'pd_questions'
        ordering = ['-created_at']