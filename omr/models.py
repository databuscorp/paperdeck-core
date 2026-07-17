from django.db import models


class OMRSheet(models.Model):
    """A printable OMR answer sheet for a paper.

    `layout` is the source of truth for geometry: it holds the normalized (0..1)
    centre of every bubble, fiducial and sheet-code module that gets printed.
    The scanner reads coordinates from this exact JSON rather than re-deriving
    them from the image, so the printer and the reader can never disagree.
    """
    org   = models.ForeignKey('users.Organization', on_delete=models.SET_NULL,
                              null=True, blank=True, related_name='omr_sheets')
    paper = models.ForeignKey('papers.Paper', on_delete=models.CASCADE,
                              related_name='omr_sheets')

    num_questions        = models.IntegerField()
    options_per_question = models.IntegerField(default=4)
    roll_digits          = models.IntegerField(default=6)

    layout        = models.JSONField(default=dict)
    sheet_version = models.IntegerField(default=1)

    pdf        = models.FileField(upload_to='omr/sheets/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'pd_omr_sheets'
        ordering = ['-created_at']
        unique_together = [('paper', 'sheet_version')]

    def __str__(self):
        return f'OMRSheet<{self.id}> paper={self.paper_id} v{self.sheet_version}'

    @property
    def short_id(self) -> int:
        """The 16-bit id baked into the printed code track."""
        return (self.id or 0) & 0xFFFF


class OMRScan(models.Model):
    """One scanned/photographed sheet, and what we read off it.

    Deliberately does NOT write into `attempts` — the scan endpoint returns the
    parsed responses and this row is the audit trail. Wiring `responses` into
    attempts.QuestionResponse is a separate integration step.
    """
    STATUS_OK           = 'ok'            # every question read cleanly
    STATUS_NEEDS_REVIEW = 'needs_review'  # at least one question is ambiguous
    STATUS_FAILED       = 'failed'        # could not even register the sheet

    org   = models.ForeignKey('users.Organization', on_delete=models.SET_NULL,
                              null=True, blank=True, related_name='omr_scans')
    sheet = models.ForeignKey(OMRSheet, on_delete=models.CASCADE,
                              null=True, blank=True, related_name='scans')

    status      = models.CharField(max_length=20, default=STATUS_OK)
    roll_number = models.CharField(max_length=20, blank=True, default='')

    responses     = models.JSONField(default=list)  # [{question_number, selected_option_index, ...}]
    needs_review  = models.JSONField(default=list)  # question numbers requiring a human
    diagnostics   = models.JSONField(default=dict)  # ink/paper levels, fiducials, warnings
    error         = models.TextField(blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'pd_omr_scans'
        ordering = ['-created_at']
