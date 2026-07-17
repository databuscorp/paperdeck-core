"""Cohort analytics — per-topic mastery across all students in an org.

Statuses are set explicitly (not via the grader) so the aggregated counts are unambiguous.
Attempts use paper=None so the answer key is built straight from the responses' questions.
"""
from django.test import TestCase

from attempts.models import QuestionResponse, StudentAttempt
from attempts.service.itemanalysisservice import ItemAnalysisService
from questions.models import Question
from students.models import Student
from users.models import Organization, User


def _opts(n, correct):
    return [{'id': i + 1, 'text': f'opt{i}', 'correct': i in correct} for i in range(n)]


class CohortSummaryTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.org = Organization.objects.create(name='Cohort Coaching')
        cls.user = User.objects.create_user(
            username='cohortteacher', password='x', org=cls.org, role=User.ROLE_ADMIN)
        cls.scope = {'org_id': cls.org.id}

        cls.q_kin = cls._q('Kinematics')
        cls.q_opt = cls._q('Optics')

        # 6 students face both. Kinematics is weak (2/6 correct → 0.333 → Hard); Optics is
        # strong (5/6 correct → 0.833 → Easy).
        kin = ['correct', 'correct', 'incorrect', 'incorrect', 'incorrect', 'unattempted']
        opt = ['correct'] * 5 + ['incorrect']
        for i in range(6):
            student = Student.objects.create(org=cls.org, name=f's{i}')
            att = StudentAttempt.objects.create(
                org=cls.org, student=student, status=StudentAttempt.STATUS_GRADED)
            QuestionResponse.objects.create(attempt=att, question=cls.q_kin,
                                            status=kin[i], time_spent_seconds=40)
            QuestionResponse.objects.create(attempt=att, question=cls.q_opt,
                                            status=opt[i], time_spent_seconds=20)

    @classmethod
    def _q(cls, topic):
        return Question.objects.create(
            org=cls.org, owner=cls.user, exam='JEE', subject='Physics', topic=topic,
            q_type='MCQ', difficulty='Medium', marks=4, neg_marks=1,
            text=f'{topic} Q', options=_opts(4, {0}))

    def test_topics_aggregate_with_correct_counts(self):
        resp = ItemAnalysisService(self.scope).cohort_summary()
        by_topic = {t.topic: t for t in resp.topics}
        kin = by_topic['Kinematics']
        self.assertEqual(kin.n_responses, 6)
        self.assertEqual(kin.n_correct, 2)
        self.assertEqual(kin.n_unattempted, 1)
        self.assertEqual(kin.n_students, 6)
        self.assertEqual(kin.accuracy, round(2 / 6, 4))
        self.assertEqual(kin.avg_time_seconds, 40.0)

    def test_calibrated_difficulty_from_cohort_accuracy(self):
        by_topic = {t.topic: t for t in
                    ItemAnalysisService(self.scope).cohort_summary().topics}
        self.assertEqual(by_topic['Kinematics'].calibrated_difficulty, 'Hard')   # 0.33
        self.assertEqual(by_topic['Optics'].calibrated_difficulty, 'Easy')       # 0.83

    def test_weakest_first_and_lists(self):
        resp = ItemAnalysisService(self.scope).cohort_summary()
        self.assertEqual(resp.topics[0].topic, 'Kinematics')     # weakest first
        self.assertIn('Kinematics', resp.weakest_topics)
        self.assertIn('Optics', resp.strongest_topics)
        self.assertEqual(resp.n_students, 6)
        self.assertTrue(resp.reliable)                            # 6 >= MIN_STUDENTS (5)

    def test_below_min_students_is_flagged_unreliable(self):
        org2 = Organization.objects.create(name='Tiny Batch')
        u2 = User.objects.create_user(username='tiny', password='x', org=org2,
                                      role=User.ROLE_ADMIN)
        q = Question.objects.create(org=org2, owner=u2, exam='JEE', subject='Physics',
                                    topic='Waves', q_type='MCQ', difficulty='Medium',
                                    marks=4, text='Waves Q', options=_opts(4, {0}))
        for i in range(2):
            s = Student.objects.create(org=org2, name=f't{i}')
            att = StudentAttempt.objects.create(org=org2, student=s,
                                                status=StudentAttempt.STATUS_GRADED)
            QuestionResponse.objects.create(attempt=att, question=q, status='correct')
        resp = ItemAnalysisService({'org_id': org2.id}).cohort_summary()
        self.assertFalse(resp.reliable)
        self.assertEqual(resp.n_students, 2)

    def test_org_scoping_isolates_cohorts(self):
        # The tiny second org's topic must not leak into the first org's summary.
        other = Organization.objects.create(name='Other Org')
        uo = User.objects.create_user(username='other', password='x', org=other,
                                      role=User.ROLE_ADMIN)
        q = Question.objects.create(org=other, owner=uo, exam='NEET', subject='Biology',
                                    topic='Genetics', q_type='MCQ', difficulty='Medium',
                                    marks=4, text='Genetics Q', options=_opts(4, {0}))
        s = Student.objects.create(org=other, name='x')
        att = StudentAttempt.objects.create(org=other, student=s,
                                            status=StudentAttempt.STATUS_GRADED)
        QuestionResponse.objects.create(attempt=att, question=q, status='correct')
        topics = {t.topic for t in ItemAnalysisService(self.scope).cohort_summary().topics}
        self.assertNotIn('Genetics', topics)
