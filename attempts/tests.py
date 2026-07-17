"""Item analysis is only worth having if the arithmetic is right, so the numbers below are
hand-computed and pinned, not recomputed by the code under test.

THE FIXTURE — 10 students (S0 strongest … S9 weakest), 6 questions, 4 marks each.
`C` = correct, `W` = wrong, `P` = partial, `U` = unattempted (blank).

              Q1      Q2       Q3        Q4       Q5      Q6
           MCQ 4/-1 MCQ 4/-1  MC 4/-2  NUM 4/-0 MCQ 4/-1 MCQ 4/-1
           key=0    key=1     key={0,2} key=9.8  key=2    key=0
    S0        C        W        C          C        C        C     → 19
    S1        C        W        C     C(9.81)      U        C     → 15
    S2        C        W        C     C(9.75)      U        C     → 15
    S3        C        W        P([0])  W(9.9)      U        C     →  9
    S4        C        C        W([0,1])   C        U        C     → 14
    S5        C        C        U        W(5.0)     U        C     → 12
    S6        C        C        U          U        U        C     → 12
    S7        W        C        W([1])  W(1.0)      U        C     →  5
    S8        W        C        U          U        U        C     →  7
    S9        U        C        U          U        W        C     →  7

Ranked by total score (desc, id asc): S0 19 | S1 15 | S2 15 | S4 14 | S5 12 | S6 12 |
S3 9 | S8 7 | S9 7 | S7 5.
N = 10 → group_size = int(0.27 × 10 + 0.5) = 3.
    TOP 27%    = {S0, S1, S2}
    BOTTOM 27% = {S8, S9, S7}
No tie straddles either boundary, so the groups are unambiguous.

Q2 is DELIBERATELY BROKEN: the four strongest students get it wrong and the six weakest
get it right — exactly the signature of a wrong answer key. Its D must come out NEGATIVE.
"""
from django.test import TestCase

from attempts.models import QuestionResponse, StudentAttempt
from attempts.service import gradingservice
from attempts.service.itemanalysisservice import (MIN_STUDENTS, MIN_STUDENTS_FOR_DISCRIMINATION,
                                                  ItemAnalysisService, calibrate_difficulty,
                                                  group_size_for)
from courses.models import Course
from papers.models import Paper, PaperQuestion, PaperSection
from questions.models import Question
from students.models import Student
from users.models import Organization, User


def _opts(n, correct):
    """[{id, text, correct}] — the project's option format (papers/service/paperservice.py)."""
    return [{'id': i + 1, 'text': f'opt{i}', 'correct': i in correct} for i in range(n)]


class ItemAnalysisTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.org = Organization.objects.create(name='Test Coaching')
        cls.user = User.objects.create_user(
            username='teacher', password='x', org=cls.org, role=User.ROLE_ADMIN)
        cls.course = Course.objects.create(name='JEE Main', org=cls.org)
        cls.scope = {'user_id': cls.user.id, 'org_id': cls.org.id, 'role': 1}

        cls.paper = Paper.objects.create(
            org=cls.org, owner=cls.user, course=cls.course,
            title='Physics Unit Test', total_marks=24,
        )
        section = PaperSection.objects.create(paper=cls.paper, name='Physics', order=0)

        def q(text, q_type, marks, neg, difficulty, topic, options=None, numeric=None):
            return Question.objects.create(
                org=cls.org, owner=cls.user, course=cls.course,
                exam='JEE Main', subject='Physics', topic=topic,
                q_type=q_type, difficulty=difficulty, marks=marks, neg_marks=neg,
                text=text, options=options, numeric_answer=numeric,
                unit='m/s^2' if numeric is not None else '',
            )

        # stated difficulty is the LLM's GUESS — several are deliberately wrong, so that
        # calibrated_difficulty has something to disagree with.
        cls.q1 = q('Q1', 'MCQ',              4, 1, 'Medium', 'Kinematics',     _opts(4, {0}))
        cls.q2 = q('Q2', 'MCQ',              4, 1, 'Easy',   'Thermodynamics', _opts(4, {1}))
        cls.q3 = q('Q3', 'Multiple Correct', 4, 2, 'Easy',   'Optics',         _opts(4, {0, 2}))
        cls.q4 = q('Q4', 'Numerical',        4, 0, 'Hard',   'Gravitation',    None, 9.8)
        cls.q5 = q('Q5', 'MCQ',              4, 1, 'Medium', 'Electrostatics', _opts(4, {2}))
        cls.q6 = q('Q6', 'MCQ',              4, 1, 'Hard',   'Units',          _opts(4, {0}))

        for i, qq in enumerate([cls.q1, cls.q2, cls.q3, cls.q4, cls.q5, cls.q6]):
            PaperQuestion.objects.create(section=section, question=qq, order=i)

        cls.students = [
            Student.objects.create(org=cls.org, name=f'S{i}', roll_no=str(i))
            for i in range(10)
        ]

        # (q1_idx, q2_idx, q3_indices, q4_value, q5_idx) — None everywhere means blank.
        # q6 is correct for everyone, which leaves the ranking untouched (+4 to all) while
        # giving us a zero-discrimination item to assert on.
        sheet = [
            # q1   q2   q3        q4    q5
            (0,    0,   [0, 2],   9.8,  2),     # S0
            (0,    0,   [0, 2],   9.81, None),  # S1
            (0,    0,   [0, 2],   9.75, None),  # S2
            (0,    0,   [0],      9.9,  None),  # S3  partial on q3, out-of-tolerance on q4
            (0,    1,   [0, 1],   9.8,  None),  # S4  a wrong option on q3 => full negative
            (0,    1,   None,     5.0,  None),  # S5
            (0,    1,   None,     None, None),  # S6
            (1,    1,   [1],      1.0,  None),  # S7
            (1,    1,   None,     None, None),  # S8
            (None, 1,   None,     None, 0),     # S9  q1 BLANK (not wrong) — 0, no penalty
        ]

        cls.attempts = []
        for student, (a1, a2, a3, a4, a5) in zip(cls.students, sheet):
            attempt = StudentAttempt.objects.create(
                org=cls.org, student=student, paper=cls.paper,
                source=StudentAttempt.SOURCE_OMR, status=StudentAttempt.STATUS_SUBMITTED,
            )
            QuestionResponse.objects.create(attempt=attempt, question=cls.q1, selected_option_index=a1)
            QuestionResponse.objects.create(attempt=attempt, question=cls.q2, selected_option_index=a2)
            QuestionResponse.objects.create(attempt=attempt, question=cls.q3, selected_option_indices=a3)
            QuestionResponse.objects.create(attempt=attempt, question=cls.q4, numeric_answer=a4)
            QuestionResponse.objects.create(attempt=attempt, question=cls.q5, selected_option_index=a5)
            QuestionResponse.objects.create(attempt=attempt, question=cls.q6, selected_option_index=0)
            gradingservice.grade_attempt(attempt)
            cls.attempts.append(attempt)

    def _items(self):
        resp = ItemAnalysisService(self.scope).analyse_paper(self.paper.id)
        return resp, {i.item_key: i for i in resp.items}

    def _resp(self, student_idx, question):
        return QuestionResponse.objects.get(
            attempt=self.attempts[student_idx], question=question)

    # ── Grading ───────────────────────────────────────────────────────────────

    def test_total_scores_match_the_hand_computed_marksheet(self):
        expected = [19, 15, 15, 9, 14, 12, 12, 5, 7, 7]
        actual = [a.total_score for a in
                  StudentAttempt.objects.filter(paper=self.paper).order_by('student__roll_no')]
        # roll_no is '0'..'9', so string ordering matches S0..S9 here.
        self.assertEqual(actual, [float(e) for e in expected])

    def test_max_score_is_the_paper_total_not_what_the_student_answered(self):
        # 6 questions × 4 marks. S6 left three blank; his denominator must still be 24,
        # otherwise skipping questions would inflate your percentage.
        for a in self.attempts:
            self.assertEqual(a.max_score, 24.0)

    def test_negative_marking_is_applied_to_a_wrong_mcq(self):
        r = self._resp(7, self.q1)          # S7 picked option 1, key is 0
        self.assertEqual(r.status, QuestionResponse.STATUS_INCORRECT)
        self.assertIs(r.is_correct, False)
        self.assertEqual(r.marks_awarded, -1.0)   # neg_marks=1

    def test_unattempted_is_not_incorrect(self):
        """THE distinction. S9 left Q1 blank; S7 answered Q1 and got it wrong. They must not
        look the same: blank scores 0 with is_correct=None, wrong scores -1 with False."""
        blank = self._resp(9, self.q1)
        wrong = self._resp(7, self.q1)

        self.assertEqual(blank.status, QuestionResponse.STATUS_UNATTEMPTED)
        self.assertIsNone(blank.is_correct)
        self.assertEqual(blank.marks_awarded, 0.0)

        self.assertEqual(wrong.status, QuestionResponse.STATUS_INCORRECT)
        self.assertIs(wrong.is_correct, False)
        self.assertEqual(wrong.marks_awarded, -1.0)

        self.assertNotEqual(blank.status, wrong.status)

    def test_multiple_correct_full_partial_and_wrong(self):
        full = self._resp(0, self.q3)       # [0, 2] == key
        self.assertEqual(full.status, QuestionResponse.STATUS_CORRECT)
        self.assertEqual(full.marks_awarded, 4.0)

        partial = self._resp(3, self.q3)    # [0] — half the key, no wrong option
        self.assertEqual(partial.status, QuestionResponse.STATUS_PARTIAL)
        self.assertIs(partial.is_correct, False)   # partial is NOT correct for item analysis
        self.assertEqual(partial.marks_awarded, 2.0)   # 4 × 1/2

        wrong = self._resp(4, self.q3)      # [0, 1] — one right, one WRONG => full negative
        self.assertEqual(wrong.status, QuestionResponse.STATUS_INCORRECT)
        self.assertEqual(wrong.marks_awarded, -2.0)

        blank = self._resp(5, self.q3)
        self.assertEqual(blank.status, QuestionResponse.STATUS_UNATTEMPTED)
        self.assertEqual(blank.marks_awarded, 0.0)

    def test_numeric_tolerance(self):
        # key = 9.8 → tolerance = max(0.01, 0.01 × 9.8) = 0.098
        self.assertAlmostEqual(gradingservice.numeric_tolerance(9.8), 0.098)

        self.assertEqual(self._resp(1, self.q4).status, QuestionResponse.STATUS_CORRECT)    # 9.81, Δ=0.01
        self.assertEqual(self._resp(2, self.q4).status, QuestionResponse.STATUS_CORRECT)    # 9.75, Δ=0.05
        self.assertEqual(self._resp(3, self.q4).status, QuestionResponse.STATUS_INCORRECT)  # 9.90, Δ=0.10 > 0.098
        # neg_marks = 0 on this question, so being wrong costs nothing
        self.assertEqual(self._resp(3, self.q4).marks_awarded, 0.0)
        self.assertEqual(self._resp(6, self.q4).status, QuestionResponse.STATUS_UNATTEMPTED)

    def test_numeric_tolerance_has_an_absolute_floor_for_a_zero_key(self):
        # A purely relative tolerance collapses to 0 when the key is 0.0.
        self.assertEqual(gradingservice.numeric_tolerance(0.0), 0.01)

    # ── p_value ───────────────────────────────────────────────────────────────

    def test_p_value_is_hand_computed_correctly(self):
        _, items = self._items()

        # Q1: 7 of 10 correct (S0..S6), S7/S8 wrong, S9 blank. Blank counts in the denominator.
        self.assertEqual(items[f'q:{self.q1.id}'].n_correct, 7)
        self.assertEqual(items[f'q:{self.q1.id}'].n_unattempted, 1)
        self.assertEqual(items[f'q:{self.q1.id}'].n_incorrect, 2)
        self.assertEqual(items[f'q:{self.q1.id}'].p_value, 0.7)

        # Q2 (the broken one): 6 of 10 correct.
        self.assertEqual(items[f'q:{self.q2.id}'].p_value, 0.6)

        # Q3: 3 fully correct (S0,S1,S2). The PARTIAL (S3) does not count as correct.
        self.assertEqual(items[f'q:{self.q3.id}'].n_correct, 3)
        self.assertEqual(items[f'q:{self.q3.id}'].p_value, 0.3)

        # Q4: S0, S1, S2, S4 within tolerance.
        self.assertEqual(items[f'q:{self.q4.id}'].p_value, 0.4)

        # Q5: only S0.
        self.assertEqual(items[f'q:{self.q5.id}'].p_value, 0.1)

        # Q6: everybody. p_value = 1.0 — HIGH p_value MEANS EASY.
        self.assertEqual(items[f'q:{self.q6.id}'].p_value, 1.0)

    def test_high_p_value_means_easy_not_hard(self):
        """The classic footgun, pinned. Q6 (everyone right) must calibrate EASY and
        Q5 (one student right) must calibrate HOTS — not the other way round."""
        _, items = self._items()
        self.assertEqual(items[f'q:{self.q6.id}'].p_value, 1.0)
        self.assertEqual(items[f'q:{self.q6.id}'].calibrated_difficulty, 'Easy')
        self.assertEqual(items[f'q:{self.q5.id}'].p_value, 0.1)
        self.assertEqual(items[f'q:{self.q5.id}'].calibrated_difficulty, 'HOTS')

    def test_attempt_rate_separates_hard_from_skipped(self):
        _, items = self._items()
        q5 = items[f'q:{self.q5.id}']
        self.assertEqual(q5.n_unattempted, 8)
        self.assertEqual(q5.attempt_rate, 0.2)
        self.assertIn('high_skip_rate', q5.flags)

    # ── Discrimination ────────────────────────────────────────────────────────

    def test_group_size_is_27_percent(self):
        self.assertEqual(group_size_for(10), 3)    # int(2.7 + 0.5) = 3
        self.assertEqual(group_size_for(100), 27)
        self.assertEqual(group_size_for(1), 1)     # never zero

    def test_discrimination_is_hand_computed_correctly(self):
        resp, items = self._items()
        self.assertEqual(resp.n_students, 10)
        self.assertEqual(resp.group_size, 3)
        self.assertTrue(resp.reliable)

        # Q1 — top {S0,S1,S2} all correct (3/3 = 1.0); bottom {S7 wrong, S8 wrong, S9 blank}
        # none correct (0/3 = 0.0).  D = 1.0 − 0.0 = 1.0
        self.assertEqual(items[f'q:{self.q1.id}'].discrimination, 1.0)

        # Q5 — top: S0 correct, S1 blank, S2 blank (1/3); bottom: none correct (0/3).
        # D = 1/3 − 0 = 0.3333
        self.assertEqual(items[f'q:{self.q5.id}'].discrimination, 0.3333)

        # Q6 — everyone correct: top 3/3, bottom 3/3.  D = 1.0 − 1.0 = 0.0
        self.assertEqual(items[f'q:{self.q6.id}'].discrimination, 0.0)

    def test_a_broken_question_produces_negative_discrimination_and_is_flagged(self):
        """Q2's key is such that the four BEST students miss it and the six worst nail it.
        top {S0,S1,S2}: 0/3 correct.  bottom {S7,S8,S9}: 3/3 correct.  D = 0 − 1 = −1.0.
        A question the strongest students get wrong more often than the weakest is not
        hard — it is broken, and that is the defect signal this whole file exists for."""
        _, items = self._items()
        q2 = items[f'q:{self.q2.id}']

        self.assertEqual(q2.discrimination, -1.0)
        self.assertTrue(q2.is_broken)
        self.assertIn('broken_negative_discrimination', q2.flags)
        # And note it does NOT look hard on p_value alone — 0.6, a perfectly ordinary
        # "Medium". Only D exposes it.
        self.assertEqual(q2.p_value, 0.6)
        self.assertEqual(q2.calibrated_difficulty, 'Medium')

    def test_a_zero_discrimination_question_is_flagged_as_a_poor_discriminator(self):
        _, items = self._items()
        q6 = items[f'q:{self.q6.id}']
        self.assertEqual(q6.discrimination, 0.0)
        self.assertFalse(q6.is_broken)               # 0 is useless, but not evidence of a bug
        self.assertTrue(q6.is_poor_discriminator)
        self.assertIn('poor_discriminator', q6.flags)
        self.assertIn('too_easy', q6.flags)

    # ── Calibration ───────────────────────────────────────────────────────────

    def test_calibration_bands(self):
        self.assertEqual(calibrate_difficulty(1.0),  'Easy')
        self.assertEqual(calibrate_difficulty(0.80), 'Easy')
        self.assertEqual(calibrate_difficulty(0.79), 'Medium')
        self.assertEqual(calibrate_difficulty(0.55), 'Medium')
        self.assertEqual(calibrate_difficulty(0.54), 'Hard')
        self.assertEqual(calibrate_difficulty(0.30), 'Hard')
        self.assertEqual(calibrate_difficulty(0.29), 'HOTS')
        self.assertEqual(calibrate_difficulty(0.0),  'HOTS')
        self.assertIsNone(calibrate_difficulty(None))

    def test_calibrated_difficulty_contradicts_the_llms_guess(self):
        """Q6 was generated as 'Hard'. Every single student got it right. The measured
        label is Easy, and the mismatch is surfaced rather than silently ignored."""
        _, items = self._items()
        q6 = items[f'q:{self.q6.id}']
        self.assertEqual(q6.stated_difficulty, 'Hard')
        self.assertEqual(q6.calibrated_difficulty, 'Easy')
        self.assertIn('difficulty_mismatch', q6.flags)

        # Q4 was generated 'Hard' and measures Hard (p = 0.4) — no mismatch.
        q4 = items[f'q:{self.q4.id}']
        self.assertEqual(q4.calibrated_difficulty, 'Hard')
        self.assertNotIn('difficulty_mismatch', q4.flags)

    # ── Per-student weakness ──────────────────────────────────────────────────

    def test_student_summary_ranks_weakest_topics_first(self):
        summary = ItemAnalysisService(self.scope).student_summary(self.students[7].id)
        self.assertEqual(summary.n_attempts, 1)
        self.assertEqual(summary.total_score, 5.0)
        self.assertEqual(summary.max_score, 24.0)

        by_topic = {t.topic: t for t in summary.topics}
        self.assertEqual(by_topic['Thermodynamics'].n_correct, 1)   # S7 got Q2 right
        self.assertEqual(by_topic['Kinematics'].n_correct, 0)       # and Q1 wrong
        self.assertEqual(by_topic['Electrostatics'].n_unattempted, 1)

        # Weakest first: the 0%-accuracy topics come before Thermodynamics/Units (100%).
        self.assertLessEqual(summary.topics[0].accuracy, summary.topics[-1].accuracy)
        self.assertIn('Kinematics', summary.weakest_topics)
        self.assertNotIn('Thermodynamics', summary.weakest_topics)


class SmallSampleGuardTests(TestCase):
    """Do not emit confident-looking statistics from a handful of students."""

    def setUp(self):
        self.org = Organization.objects.create(name='Tiny Coaching')
        self.user = User.objects.create_user(
            username='t2', password='x', org=self.org, role=User.ROLE_ADMIN)
        self.scope = {'user_id': self.user.id, 'org_id': self.org.id, 'role': 1}
        self.paper = Paper.objects.create(org=self.org, owner=self.user, title='Tiny', total_marks=4)
        section = PaperSection.objects.create(paper=self.paper, name='S', order=0)
        self.q = Question.objects.create(
            org=self.org, owner=self.user, exam='JEE', subject='Physics', topic='Kinematics',
            q_type='MCQ', difficulty='Medium', marks=4, neg_marks=1, text='Q', options=_opts(4, {0}),
        )
        PaperQuestion.objects.create(section=section, question=self.q, order=0)

    def _seed(self, n, correct_upto):
        for i in range(n):
            student = Student.objects.create(org=self.org, name=f'X{i}')
            attempt = StudentAttempt.objects.create(
                org=self.org, student=student, paper=self.paper,
                status=StudentAttempt.STATUS_SUBMITTED)
            QuestionResponse.objects.create(
                attempt=attempt, question=self.q,
                selected_option_index=0 if i < correct_upto else 1)
            gradingservice.grade_attempt(attempt)

    def test_three_students_yield_no_statistics_at_all(self):
        self._seed(3, 2)
        resp = ItemAnalysisService(self.scope).analyse_paper(self.paper.id)
        self.assertEqual(resp.n_students, 3)
        self.assertFalse(resp.reliable)
        self.assertEqual(resp.items, [])          # NOT "p_value = 0.67"
        self.assertIn(str(MIN_STUDENTS), resp.message)

    def test_seven_students_get_a_p_value_but_no_discrimination(self):
        # 7 >= MIN_STUDENTS (5) but < MIN_STUDENTS_FOR_DISCRIMINATION (10): the 27% groups
        # would be 2 students each, and D from 2-vs-2 is a coin flip.
        self._seed(7, 4)
        resp = ItemAnalysisService(self.scope).analyse_paper(self.paper.id)
        self.assertEqual(resp.n_students, 7)
        self.assertFalse(resp.reliable)
        self.assertEqual(len(resp.items), 1)

        item = resp.items[0]
        self.assertAlmostEqual(item.p_value, 0.5714)      # 4/7
        self.assertIsNone(item.discrimination)            # suppressed, not guessed
        self.assertEqual(item.confidence, 'low')
        self.assertIn('low_confidence', item.flags)
        self.assertIsNotNone(item.calibrated_difficulty)
        self.assertIn(str(MIN_STUDENTS_FOR_DISCRIMINATION), resp.message)

    def test_ten_students_unlock_discrimination(self):
        self._seed(10, 6)
        resp = ItemAnalysisService(self.scope).analyse_paper(self.paper.id)
        self.assertTrue(resp.reliable)
        self.assertEqual(resp.items[0].confidence, 'ok')
        self.assertIsNotNone(resp.items[0].discrimination)


class SnapshotQuestionTests(TestCase):
    """A paper question that was never promoted to the bank has no questions.Question row.
    It still has to be gradable and still has to appear in item analysis."""

    def setUp(self):
        self.org = Organization.objects.create(name='Snap Coaching')
        self.user = User.objects.create_user(
            username='t3', password='x', org=self.org, role=User.ROLE_ADMIN)
        self.scope = {'user_id': self.user.id, 'org_id': self.org.id, 'role': 1}
        self.paper = Paper.objects.create(org=self.org, owner=self.user, title='Snap', total_marks=4)
        section = PaperSection.objects.create(paper=self.paper, name='S', order=0)
        self.pq = PaperQuestion.objects.create(
            section=section, question=None, order=0,
            snapshot={
                'text': 'Snapshot Q', 'q_type': 'MCQ', 'marks': 4, 'neg_marks': 1,
                'difficulty': 'Medium', 'topic': 'Optics', 'subject': 'Physics',
                'options': _opts(4, {2}),
            },
        )

    def test_snapshot_question_is_graded_and_analysed(self):
        for i in range(10):
            student = Student.objects.create(org=self.org, name=f'Y{i}')
            attempt = StudentAttempt.objects.create(
                org=self.org, student=student, paper=self.paper,
                status=StudentAttempt.STATUS_SUBMITTED)
            QuestionResponse.objects.create(
                attempt=attempt, question=None, question_snapshot_id=str(self.pq.id),
                selected_option_index=2 if i < 8 else 0)
            gradingservice.grade_attempt(attempt)

        resp = ItemAnalysisService(self.scope).analyse_paper(self.paper.id)
        self.assertEqual(len(resp.items), 1)
        item = resp.items[0]
        self.assertEqual(item.item_key, f's:{self.pq.id}')
        self.assertIsNone(item.question_id)
        self.assertEqual(item.p_value, 0.8)
        self.assertEqual(item.calibrated_difficulty, 'Easy')


class ApiTests(TestCase):
    """The endpoints, end to end, through the real auth decorator."""

    def setUp(self):
        from rest_framework_simplejwt.tokens import AccessToken

        self.org = Organization.objects.create(name='API Coaching')
        self.user = User.objects.create_user(
            username='api', password='x', org=self.org, role=User.ROLE_ADMIN)
        self.auth = {'HTTP_AUTHORIZATION': f'Bearer {AccessToken.for_user(self.user)}'}

        self.paper = Paper.objects.create(org=self.org, owner=self.user, title='API', total_marks=8)
        section = PaperSection.objects.create(paper=self.paper, name='S', order=0)
        self.q1 = Question.objects.create(
            org=self.org, owner=self.user, exam='JEE', subject='Physics', topic='Kinematics',
            q_type='MCQ', difficulty='Medium', marks=4, neg_marks=1, text='A', options=_opts(4, {0}))
        self.q2 = Question.objects.create(
            org=self.org, owner=self.user, exam='JEE', subject='Physics', topic='Optics',
            q_type='Numerical', difficulty='Hard', marks=4, neg_marks=0, text='B', numeric_answer=2.5)
        PaperQuestion.objects.create(section=section, question=self.q1, order=0)
        PaperQuestion.objects.create(section=section, question=self.q2, order=1)
        self.student = Student.objects.create(org=self.org, name='API Student')

    def _submit(self, **overrides):
        body = {
            'student_id': self.student.id,
            'paper_id': self.paper.id,
            'source': 'omr',
            'responses': [
                {'question_id': self.q1.id, 'selected_option_index': 0},
                {'question_id': self.q2.id, 'numeric_answer': 2.5},
            ],
        }
        body.update(overrides)
        return self.client.post(
            '/api/attempts/', data=body, content_type='application/json', **self.auth)

    def test_post_creates_and_grades_an_attempt(self):
        resp = self._submit()
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['status'], 'graded')
        self.assertEqual(data['total_score'], 8.0)
        self.assertEqual(data['max_score'], 8.0)
        self.assertEqual(len(data['responses']), 2)
        self.assertTrue(all(r['is_correct'] for r in data['responses']))

    def test_post_requires_auth(self):
        self.assertEqual(self.client.post('/api/attempts/', data={}, content_type='application/json').status_code, 401)

    def test_post_rejects_an_unknown_student(self):
        resp = self._submit(student_id=999999)
        self.assertEqual(resp.status_code, 404)

    def test_get_lists_attempts_for_a_paper(self):
        self._submit()
        resp = self.client.get(f'/api/attempts/?paper_id={self.paper.id}', **self.auth)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['student_id'], self.student.id)

    def test_analysis_endpoint_requires_paper_id(self):
        self.assertEqual(self.client.get('/api/attempts/analysis/', **self.auth).status_code, 400)

    def test_analysis_endpoint_returns_the_small_sample_guard(self):
        self._submit()
        resp = self.client.get(f'/api/attempts/analysis/?paper_id={self.paper.id}', **self.auth)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['n_students'], 1)
        self.assertFalse(data['reliable'])
        self.assertEqual(data['items'], [])

    def test_student_endpoint_returns_a_topic_summary(self):
        self._submit()
        resp = self.client.get(f'/api/attempts/student/?student_id={self.student.id}', **self.auth)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['n_attempts'], 1)
        self.assertEqual(data['score_pct'], 100.0)
        self.assertEqual({t['topic'] for t in data['topics']}, {'Kinematics', 'Optics'})
