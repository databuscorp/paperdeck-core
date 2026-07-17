"""Adaptive practice — generate questions aimed at a student's weak topics.

The generator is faked (no network): the point under test is that weak topics are read from
the student's attempts and drive what gets generated, and that usage accumulates across the
per-topic calls (generate_questions resets last_usage each call).
"""
from unittest import mock

from django.test import TestCase

from attempts.models import QuestionResponse, StudentAttempt
from attempts.service import adaptivepracticeservice
from attempts.service.adaptivepracticeservice import AdaptivePracticeService
from questions.models import Question
from students.models import Student
from users.models import Organization, User


def _opts(n, correct):
    return [{'id': i + 1, 'text': f'opt{i}', 'correct': i in correct} for i in range(n)]


class _FakeGen:
    """Stands in for AIGeneratorService — returns N stub questions per topic, reports usage."""

    def __init__(self):
        self.last_usage = {'input_tokens': 0, 'output_tokens': 0,
                           'cache_creation_input_tokens': 0, 'cache_read_input_tokens': 0}
        self.usage_by_phase = {}
        self.calls = []

    def generate_questions(self, exam, subject, topic, q_type, difficulty, bloom, count,
                           language='English'):
        self.calls.append({'topic': topic, 'subject': subject, 'exam': exam, 'count': count})
        # generate_questions resets usage per call; mimic that so the service must accumulate.
        self.last_usage = {'input_tokens': 100 * count, 'output_tokens': 50 * count,
                           'cache_creation_input_tokens': 0, 'cache_read_input_tokens': 0}
        self.usage_by_phase = {'generation': dict(self.last_usage)}
        return [{'text': f'{topic} practice {i}', 'q_type': 'MCQ',
                 'subject': subject, 'topic': topic} for i in range(count)]


class AdaptivePracticeTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.org = Organization.objects.create(name='Adaptive Coaching')
        cls.user = User.objects.create_user(username='adaptteacher', password='x',
                                            org=cls.org, role=User.ROLE_ADMIN)
        cls.scope = {'org_id': cls.org.id}
        cls.student = Student.objects.create(org=cls.org, name='Weak Student')

        # One graded attempt: wrong on Kinematics (weak), right on Optics (strong).
        q_kin = cls._q('Kinematics')
        q_opt = cls._q('Optics')
        att = StudentAttempt.objects.create(org=cls.org, student=cls.student,
                                            status=StudentAttempt.STATUS_GRADED)
        QuestionResponse.objects.create(attempt=att, question=q_kin, status='incorrect')
        QuestionResponse.objects.create(attempt=att, question=q_opt, status='correct')

    @classmethod
    def _q(cls, topic):
        return Question.objects.create(
            org=cls.org, owner=cls.user, exam='JEE', subject='Physics', topic=topic,
            q_type='MCQ', difficulty='Medium', marks=4, text=f'{topic} Q',
            options=_opts(4, {0}))

    def test_targets_weak_topic_and_returns_questions(self):
        fake = _FakeGen()
        with mock.patch.object(adaptivepracticeservice, 'AIGeneratorService', return_value=fake):
            result = AdaptivePracticeService(self.scope).generate(
                self.student.id, count=6, max_topics=3)
        self.assertEqual(len(result['questions']), 6)
        targeted = {t['topic'] for t in result['targeted_topics']}
        self.assertIn('Kinematics', targeted)         # the weak one
        self.assertNotIn('Optics', targeted)          # strong (accuracy 1.0) is not weak
        # exam was inferred and passed through to generation.
        self.assertTrue(all(c['exam'] == 'JEE' for c in fake.calls))

    def test_usage_accumulates_across_topic_calls(self):
        # Force two weak topics so the service makes two generate calls and must SUM usage.
        q_dyn = self._q('Dynamics')
        att = StudentAttempt.objects.create(org=self.org, student=self.student,
                                            status=StudentAttempt.STATUS_GRADED)
        QuestionResponse.objects.create(attempt=att, question=q_dyn, status='incorrect')

        fake = _FakeGen()
        with mock.patch.object(adaptivepracticeservice, 'AIGeneratorService', return_value=fake):
            result = AdaptivePracticeService(self.scope).generate(
                self.student.id, count=6, max_topics=2)
        self.assertEqual(len(fake.calls), 2)           # two weak topics → two calls
        # 6 questions total → 100*6 input across the two calls, summed (not overwritten).
        self.assertEqual(result['usage']['input_tokens'], 600)
        self.assertEqual(result['usage']['output_tokens'], 300)
        self.assertEqual(result['usage_by_phase']['generation']['input_tokens'], 600)

    def test_student_with_no_attempts_returns_message_not_error(self):
        blank = Student.objects.create(org=self.org, name='New Student')
        fake = _FakeGen()
        with mock.patch.object(adaptivepracticeservice, 'AIGeneratorService', return_value=fake):
            result = AdaptivePracticeService(self.scope).generate(blank.id, count=6)
        self.assertEqual(result['questions'], [])
        self.assertEqual(fake.calls, [])               # nothing generated, nothing billed
        self.assertIn('weak areas', result['message'])
