"""Empirical difficulty calibration — the numbers are hand-computed and pinned.

recalibrate() aggregates every GRADED response for a question and writes the measured
p_value (HIGH = EASY) and its Easy/Medium/Hard/HOTS label back onto the bank. The statuses
below are set explicitly (not via the grader) so the counts under test are unambiguous.
"""
from django.test import TestCase

from attempts.models import QuestionResponse, StudentAttempt
from attempts.service.calibrationservice import recalibrate
from attempts.service.itemanalysisservice import MIN_STUDENTS
from questions.models import Question
from students.models import Student
from users.models import Organization, User


def _opts(n, correct):
    return [{'id': i + 1, 'text': f'opt{i}', 'correct': i in correct} for i in range(n)]


class CalibrationTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.org = Organization.objects.create(name='Calib Coaching')
        cls.user = User.objects.create_user(
            username='calibteacher', password='x', org=cls.org, role=User.ROLE_ADMIN)

        def q(text, difficulty):
            return Question.objects.create(
                org=cls.org, owner=cls.user, exam='JEE', subject='Physics', topic='Kinematics',
                q_type='MCQ', difficulty=difficulty, marks=4, neg_marks=1,
                text=text, options=_opts(4, {0}),
            )

        # stated difficulty is the LLM guess — several are wrong so the measured label disagrees.
        cls.q_easy   = q('Easy Q',   'Hard')     # 8/10 correct              → p=0.8 → Easy
        cls.q_hard   = q('Hard Q',   'Easy')     # 3 correct, rest wrong/blank → p=0.3 → Hard
        cls.q_skip   = q('Skip Q',   'Medium')   # 4 correct, 4 blank, 2 wrong → p=0.4 → Hard
        cls.q_below  = q('Below Q',  'Medium')   # only 3 faced → below MIN_STUDENTS, untouched

        cls._face(cls.q_easy, ['correct'] * 8 + ['incorrect'] * 2)
        cls._face(cls.q_hard, ['correct'] * 3 + ['incorrect'] * 5 + ['unattempted'] * 2)
        # q_skip: unattempted must count in the denominator but NOT the numerator.
        # 10 faced, 4 correct, 4 unattempted, 2 incorrect → p = 4/10 = 0.4 → Hard.
        cls._face(cls.q_skip, ['correct'] * 4 + ['unattempted'] * 4 + ['incorrect'] * 2)
        cls._face(cls.q_below, ['correct'] * 3)

    @classmethod
    def _face(cls, question, statuses):
        """Create one GRADED attempt per status, each holding this question's response."""
        for i, status in enumerate(statuses):
            student = Student.objects.create(org=cls.org, name=f'{question.text}-{i}')
            attempt = StudentAttempt.objects.create(
                org=cls.org, student=student, status=StudentAttempt.STATUS_GRADED)
            QuestionResponse.objects.create(attempt=attempt, question=question, status=status)

    # ── p_value, label, response_count ─────────────────────────────────────────

    def test_easy_question_calibrates_easy(self):
        recalibrate()
        self.q_easy.refresh_from_db()
        self.assertEqual(self.q_easy.empirical_p_value, 0.8)
        self.assertEqual(self.q_easy.empirical_difficulty, 'Easy')   # HIGH p == EASY
        self.assertEqual(self.q_easy.response_count, 10)
        self.assertIsNotNone(self.q_easy.calibrated_at)

    def test_hard_question_calibrates_hard(self):
        recalibrate()
        self.q_hard.refresh_from_db()
        # 3 correct of 10 faced (unattempted included in denominator) → 0.3 → Hard
        self.assertEqual(self.q_hard.empirical_p_value, 0.3)
        self.assertEqual(self.q_hard.empirical_difficulty, 'Hard')
        self.assertEqual(self.q_hard.response_count, 10)

    def test_unattempted_counts_in_denominator_not_numerator(self):
        recalibrate()
        self.q_skip.refresh_from_db()
        # 4 correct / 10 faced = 0.4 (NOT 4/6). Skipping is evidence of difficulty.
        self.assertEqual(self.q_skip.empirical_p_value, 0.4)
        self.assertEqual(self.q_skip.empirical_difficulty, 'Hard')
        self.assertEqual(self.q_skip.response_count, 10)

    def test_calibrated_label_contradicts_the_llms_guess(self):
        recalibrate()
        self.q_easy.refresh_from_db()
        # Generated as 'Hard', students found it Easy — the whole point of measuring.
        self.assertEqual(self.q_easy.difficulty, 'Hard')
        self.assertEqual(self.q_easy.empirical_difficulty, 'Easy')

    # ── Threshold guard ────────────────────────────────────────────────────────

    def test_question_below_threshold_is_not_calibrated(self):
        summary = recalibrate()
        self.q_below.refresh_from_db()
        self.assertIsNone(self.q_below.empirical_p_value)
        self.assertEqual(self.q_below.empirical_difficulty, '')
        self.assertEqual(self.q_below.response_count, 0)
        self.assertIsNone(self.q_below.calibrated_at)
        self.assertGreaterEqual(summary['skipped_below_threshold'], 1)

    def test_prior_calibration_is_not_wiped_when_below_threshold(self):
        # A question calibrated on an earlier, larger run must survive a run that now sees
        # too few rows — recalibrate leaves sub-threshold questions untouched.
        self.q_below.empirical_p_value = 0.5
        self.q_below.empirical_difficulty = 'Hard'
        self.q_below.response_count = 42
        self.q_below.save()
        recalibrate()
        self.q_below.refresh_from_db()
        self.assertEqual(self.q_below.empirical_p_value, 0.5)
        self.assertEqual(self.q_below.response_count, 42)

    # ── Summary dict ───────────────────────────────────────────────────────────

    def test_summary_dict_shape(self):
        summary = recalibrate()
        self.assertEqual(summary['calibrated'], 3)          # easy, hard, skip
        self.assertEqual(summary['skipped_below_threshold'], 1)
        self.assertEqual(summary['min_students'], MIN_STUDENTS)

    def test_min_students_override(self):
        # Raise the bar above q_hard/q_skip's 10 and everything is skipped.
        summary = recalibrate(min_students=11)
        self.assertEqual(summary['calibrated'], 0)

    # ── Org scoping ────────────────────────────────────────────────────────────

    def test_org_scope_excludes_other_orgs_attempts(self):
        other = Organization.objects.create(name='Other Coaching')
        summary = recalibrate(org_id=other.id)
        self.assertEqual(summary['calibrated'], 0)
        self.q_easy.refresh_from_db()
        self.assertIsNone(self.q_easy.empirical_p_value)

    def test_only_graded_attempts_are_counted(self):
        # An in-progress attempt for a fresh question must not calibrate it.
        q = Question.objects.create(
            org=self.org, owner=self.user, exam='JEE', subject='Physics', topic='Optics',
            q_type='MCQ', difficulty='Medium', marks=4, neg_marks=1, text='Ungraded Q',
            options=_opts(4, {0}))
        for i in range(8):
            student = Student.objects.create(org=self.org, name=f'ip-{i}')
            attempt = StudentAttempt.objects.create(
                org=self.org, student=student, status=StudentAttempt.STATUS_IN_PROGRESS)
            QuestionResponse.objects.create(attempt=attempt, question=q, status='correct')
        recalibrate()
        q.refresh_from_db()
        self.assertIsNone(q.empirical_p_value)
