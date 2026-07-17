"""Retrieval of grounding exemplars.

The generator writes generic textbook questions unless it is shown what this exam really
asks. Previous-year questions are the best possible answer to that — a real 2024 NEET
question IS the target — so retrieval has to find them, prefer them, and never ground on
something a teacher already threw away.
"""
from django.test import TestCase

from papers.service.aigeneratorservice import AIGeneratorService
from questions.models import Question
from users.models import Organization, User


class ExemplarRetrievalTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.org = Organization.objects.create(name='Acme Coaching')
        cls.user = User.objects.create(
            username='t', email='t@x.com', org=cls.org, role=2)
        cls.svc = AIGeneratorService.__new__(AIGeneratorService)
        cls.svc._client = None

    def _q(self, text, **kw):
        defaults = dict(
            owner=self.user, org=self.org, exam='NEET', subject='Physics',
            topic='Laws of Motion', q_type='MCQ', difficulty='Medium', marks=4,
        )
        defaults.update(kw)
        return Question.objects.create(text=text, **defaults)

    def _retrieve(self, topic='Laws of Motion'):
        return self.svc._retrieve_exemplars('NEET', 'Physics', topic, 'MCQ')

    def test_previous_year_questions_are_preferred_over_our_own_output(self):
        """A real exam question outranks anything we generated ourselves."""
        self._q('Generated question about friction', source='ai')
        self._q('NEET 2024: a block on an inclined plane', is_pyq=True, year=2024)

        top = self._retrieve()[0]
        self.assertIn('NEET 2024', top)

    def test_recent_previous_year_questions_come_first(self):
        """The syllabus and the house style move. 2024 beats 2015."""
        self._q('NEET 2015 question', is_pyq=True, year=2015)
        self._q('NEET 2024 question', is_pyq=True, year=2024)
        self._q('NEET 2020 question', is_pyq=True, year=2020)

        got = self._retrieve()
        self.assertEqual([t.split()[1] for t in got], ['2024', '2020', '2015'])

    def test_a_pyq_with_no_year_does_not_outrank_a_dated_one(self):
        """NULL year must sort last, not first — otherwise an untagged import silently
        displaces the newest real paper."""
        self._q('NEET undated question', is_pyq=True, year=None)
        self._q('NEET 2024 question', is_pyq=True, year=2024)

        self.assertIn('2024', self._retrieve()[0])

    def test_rejected_questions_are_never_used_as_exemplars(self):
        """THE one that matters. Grounding the generator on output a human rejected
        teaches it to make the same mistake again — worse than no grounding at all."""
        self._q('Rejected rubbish about momentum', verification='rejected')
        self._q('Good question about momentum', verification='verified')

        got = self._retrieve()
        self.assertTrue(all('Rejected' not in t for t in got), got)
        self.assertTrue(any('Good question' in t for t in got))

    def test_only_rejected_questions_means_no_exemplars_rather_than_bad_ones(self):
        self._q('Rejected rubbish', verification='rejected')
        self.assertEqual(self._retrieve(), [])

    def test_topic_is_matched_by_meaning_not_exact_string(self):
        """The old code did topic__iexact, so a bank tagged 'Laws of Motion' returned
        NOTHING for a request about "Newton's laws" — the grounding vanished exactly when
        someone asked for something specific. Full-text search finds it."""
        self._q("A body obeys Newton's laws of motion on a frictionless surface",
                topic='Laws of Motion', is_pyq=True, year=2023)

        got = self.svc._retrieve_exemplars('NEET', 'Physics', "Newton's laws", 'MCQ')
        self.assertTrue(got, 'full-text fallback found nothing')
        self.assertIn('Newton', got[0])

    def test_an_empty_bank_yields_no_exemplars_and_does_not_raise(self):
        """A fresh org has nothing to ground on. That must degrade to 'no exemplars',
        never to an exception in the middle of a paid generation."""
        self.assertEqual(self._retrieve(), [])
        self.assertEqual(self.svc._style_exemplars('NEET', 'Physics', 'Optics', 'MCQ'), '')

    def test_exemplar_block_is_rendered_when_matches_exist(self):
        self._q('NEET 2024: a real question', is_pyq=True, year=2024)
        block = self.svc._style_exemplars('NEET', 'Physics', 'Laws of Motion', 'MCQ')
        self.assertIn('NEET 2024', block)
        self.assertIn('do not copy them', block)


class YearDetectionTests(TestCase):
    """The year orders the exemplars, so a wrong one silently mis-ranks every PYQ."""

    def test_year_is_read_from_the_title_first(self):
        from papers.service.aigeneratorservice import _detect_year
        self.assertEqual(_detect_year('NEET 2024 Question Paper', 'body from 1999'), 2024)

    def test_year_falls_back_to_the_body(self):
        from papers.service.aigeneratorservice import _detect_year
        self.assertEqual(_detect_year('', 'JEE Main 2023 — Session 1'), 2023)

    def test_a_number_that_is_not_a_year_is_ignored(self):
        """A physics paper is full of numbers. '2500 J' is not a year, and taking it as
        one would sort that paper above every real recent paper."""
        from papers.service.aigeneratorservice import _detect_year
        self.assertIsNone(_detect_year('', 'A body absorbs 2500 J of heat at 3000 K'))

    def test_no_year_anywhere_is_none_not_a_guess(self):
        from papers.service.aigeneratorservice import _detect_year
        self.assertIsNone(_detect_year('Question Paper', 'no dates here'))
