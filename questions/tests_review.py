"""Review queue + quality dashboard.

These drive the real HTTP endpoints with real JWTs (auth_required reads a Bearer
token), because two of the properties under test are transport-level: tenant
isolation, and the fact that a rejected question stops coming back from the bank
endpoint that papers are built from.

The arithmetic tests hand-compute every rate. That is deliberate — the whole point
of the dashboard is that a teacher trusts the number, so a rate that is quietly off
by a rounding step is a bug, not a detail.
"""
import json
from datetime import datetime, time, timedelta

from django.test import Client, TestCase
from django.utils import timezone
from rest_framework_simplejwt.tokens import AccessToken

from questions.models import Question
from questions.service.questionservice import MIN_SAMPLE_N
from users.models import Organization, User

OPTS = [
    {"text": "4.9 m/s^2", "correct": True},
    {"text": "9.8 m/s^2", "correct": False},
    {"text": "19.6 m/s^2", "correct": False},
]

CORRECTED_NOTE = (
    "Answer key corrected from option 2 ('19.6 m/s^2') to option 0 ('4.9 m/s^2'): "
    "the body starts from rest, so the average acceleration is half."
)


class ReviewTestBase(TestCase):
    """Two orgs, seeded across every verification state."""

    def setUp(self):
        self.client = Client()

        self.org_a = Organization.objects.create(name='Org A')
        self.org_b = Organization.objects.create(name='Org B')
        self.user_a = User.objects.create_user(
            username='a@x.com', email='a@x.com', password='pw', org=self.org_a)
        self.user_b = User.objects.create_user(
            username='b@x.com', email='b@x.com', password='pw', org=self.org_b)

    # ── helpers ───────────────────────────────────────────────────────────────

    def _q(self, user, verification='', subject='Physics', topic='Kinematics',
           exam='NEET', note='', text=None, created_at=None, options=None):
        q = Question.objects.create(
            owner=user,
            org=user.org,
            exam=exam,
            subject=subject,
            topic=topic,
            q_type='MCQ',
            difficulty='Medium',
            marks=4,
            text=text or f'Question {verification or "unverified"} in {subject}',
            options=options if options is not None else [dict(o) for o in OPTS],
            source='ai',
            verification=verification,
            verification_note=note,
        )
        if created_at is not None:
            # created_at is auto_now_add, so it can only be set behind the model's back.
            Question.objects.filter(id=q.id).update(created_at=created_at)
            q.refresh_from_db()
        return q

    def _auth(self, user):
        return {'HTTP_AUTHORIZATION': f'Bearer {AccessToken.for_user(user)}'}

    def _get(self, url, user, **params):
        return self.client.get(url, params, **self._auth(user))

    def _post(self, url, user, payload):
        return self.client.post(
            url, data=json.dumps(payload),
            content_type='application/json', **self._auth(user))


class ReviewQueueTests(ReviewTestBase):

    def setUp(self):
        super().setUp()
        self.flagged = self._q(self.user_a, 'flagged', note='Unresolved: needs human review.')
        self.corrected = self._q(self.user_a, 'corrected', note=CORRECTED_NOTE)
        self.verified = self._q(self.user_a, 'verified')
        self.skipped = self._q(self.user_a, 'skipped')
        self.unverified = self._q(self.user_a, '')
        # Org B's queue — must never leak into org A's.
        self.b_flagged = self._q(self.user_b, 'flagged')
        self.b_corrected = self._q(self.user_b, 'corrected')

    def test_queue_returns_only_flagged_and_corrected_by_default(self):
        """verified/skipped/unverified questions are not a teacher's problem."""
        body = self._get('/api/questions/review/', self.user_a).json()

        self.assertEqual(body['total'], 2)
        returned = {r['question']['id'] for r in body['data']}
        self.assertEqual(returned, {self.flagged.id, self.corrected.id})
        self.assertEqual(body['counts'], {'flagged': 1, 'corrected': 1})

    def test_queue_is_tenant_isolated(self):
        """THE security property. Org A's queue must not contain org B's questions —
        and vice versa — even though both orgs have flagged/corrected rows."""
        a_ids = {r['question']['id']
                 for r in self._get('/api/questions/review/', self.user_a).json()['data']}
        b_ids = {r['question']['id']
                 for r in self._get('/api/questions/review/', self.user_b).json()['data']}

        self.assertEqual(a_ids, {self.flagged.id, self.corrected.id})
        self.assertEqual(b_ids, {self.b_flagged.id, self.b_corrected.id})
        self.assertFalse(a_ids & b_ids)

    def test_queue_requires_authentication(self):
        self.assertEqual(self.client.get('/api/questions/review/').status_code, 401)

    def test_corrected_question_shows_what_changed(self):
        """A `corrected` row had its key silently changed by an AI. The teacher has to
        be able to see from-what/to-what without reading the raw note."""
        body = self._get('/api/questions/review/', self.user_a, status='corrected').json()
        row = body['data'][0]

        self.assertEqual(row['verification'], 'corrected')
        self.assertEqual(row['correction']['from_index'], 2)
        self.assertEqual(row['correction']['from_text'], '19.6 m/s^2')
        self.assertEqual(row['correction']['to_index'], 0)
        self.assertEqual(row['correction']['to_text'], '4.9 m/s^2')
        self.assertIn('starts from rest', row['correction']['reason'])
        # ...and the key as it now stands.
        self.assertEqual(row['current_answer_index'], 0)
        self.assertEqual(row['current_answer_text'], '4.9 m/s^2')
        self.assertIn('corrected from option 2', row['verification_note'])

    def test_flagged_question_carries_no_correction_block(self):
        body = self._get('/api/questions/review/', self.user_a, status='flagged').json()
        row = body['data'][0]
        self.assertIsNone(row['correction'])
        self.assertIn('needs human review', row['verification_note'])

    def test_queue_filters_by_subject_and_status(self):
        chem = self._q(self.user_a, 'flagged', subject='Chemistry')

        body = self._get('/api/questions/review/', self.user_a, subject='Chemistry').json()
        self.assertEqual([r['question']['id'] for r in body['data']], [chem.id])

        body = self._get('/api/questions/review/', self.user_a, status='verified').json()
        self.assertEqual([r['question']['id'] for r in body['data']], [self.verified.id])

    def test_queue_paginates(self):
        for _ in range(5):
            self._q(self.user_a, 'flagged')

        page1 = self._get('/api/questions/review/', self.user_a, page=1, limit=3).json()
        page2 = self._get('/api/questions/review/', self.user_a, page=2, limit=3).json()

        self.assertEqual(page1['total'], 7)          # 5 new + the 2 seeded
        self.assertEqual(len(page1['data']), 3)
        self.assertTrue(page1['pagination']['has_next'])
        self.assertFalse(page1['pagination']['has_previous'])
        self.assertEqual(len(page2['data']), 3)
        self.assertTrue(page2['pagination']['has_previous'])
        # No row appears on both pages.
        self.assertFalse({r['question']['id'] for r in page1['data']}
                         & {r['question']['id'] for r in page2['data']})


class ReviewActionTests(ReviewTestBase):

    def setUp(self):
        super().setUp()
        self.flagged = self._q(self.user_a, 'flagged', note='Unresolved: needs human review.')
        self.corrected = self._q(self.user_a, 'corrected', note=CORRECTED_NOTE)

    def _queue_ids(self, user):
        return {r['question']['id']
                for r in self._get('/api/questions/review/', user).json()['data']}

    def test_approve_marks_it_and_clears_it_from_the_queue(self):
        resp = self._post('/api/questions/review/', self.user_a,
                          {'question_id': self.flagged.id, 'action': 'approve',
                           'note': 'Checked against NCERT.'})
        self.assertEqual(resp.status_code, 200)

        self.flagged.refresh_from_db()
        self.assertEqual(self.flagged.verification, 'approved')
        # who/when/from-what, since there are no columns for it yet.
        self.assertIn(f'user_id={self.user_a.id}', self.flagged.verification_note)
        self.assertIn('(was: flagged)', self.flagged.verification_note)
        self.assertIn('Checked against NCERT.', self.flagged.verification_note)
        # The AI's original explanation survives underneath.
        self.assertIn('needs human review', self.flagged.verification_note)

        self.assertNotIn(self.flagged.id, self._queue_ids(self.user_a))

    def test_reject_soft_deletes_and_clears_it_from_the_queue(self):
        resp = self._post('/api/questions/review/', self.user_a,
                          {'question_id': self.corrected.id, 'action': 'reject',
                           'note': 'Both options are defensible.'})
        self.assertEqual(resp.status_code, 200)

        self.corrected.refresh_from_db()
        self.assertEqual(self.corrected.verification, 'rejected')
        self.assertIn('(was: corrected)', self.corrected.verification_note)
        self.assertNotIn(self.corrected.id, self._queue_ids(self.user_a))
        # Soft, not hard: the row is still there for the teacher to look at.
        self.assertTrue(Question.objects.filter(id=self.corrected.id).exists())

    def test_a_rejection_is_reversible(self):
        self._post('/api/questions/review/', self.user_a,
                   {'question_id': self.flagged.id, 'action': 'reject'})
        self._post('/api/questions/review/', self.user_a,
                   {'question_id': self.flagged.id, 'action': 'approve'})

        self.flagged.refresh_from_db()
        self.assertEqual(self.flagged.verification, 'approved')

    def test_edit_that_changes_the_text_reopens_verification(self):
        """An old verdict only applies to the exact text that was solved. Editing the
        question invalidates it — a stale 'verified' badge is worse than none."""
        resp = self._post('/api/questions/review/', self.user_a,
                          {'question_id': self.flagged.id, 'action': 'edit',
                           'text': 'A body starts from rest. What is its acceleration?'})
        self.assertEqual(resp.status_code, 200)

        self.flagged.refresh_from_db()
        self.assertEqual(self.flagged.verification, '')
        self.assertEqual(self.flagged.text,
                         'A body starts from rest. What is its acceleration?')
        self.assertNotIn(self.flagged.id, self._queue_ids(self.user_a))

    def test_edit_that_changes_the_options_reopens_verification(self):
        new_opts = [{"text": "1 m/s^2", "correct": True},
                    {"text": "2 m/s^2", "correct": False}]
        self._post('/api/questions/review/', self.user_a,
                   {'question_id': self.corrected.id, 'action': 'edit', 'options': new_opts})

        self.corrected.refresh_from_db()
        self.assertEqual(self.corrected.verification, '')
        self.assertEqual(self.corrected.options, new_opts)

    def test_edit_that_leaves_the_content_alone_keeps_the_question_in_the_queue(self):
        """Fixing only the explanation doesn't re-solve the question, so the flag stands."""
        self._post('/api/questions/review/', self.user_a,
                   {'question_id': self.flagged.id, 'action': 'edit',
                    'explanation': 'Use v = u + at with u = 0.'})

        self.flagged.refresh_from_db()
        self.assertEqual(self.flagged.verification, 'flagged')
        self.assertEqual(self.flagged.explanation, 'Use v = u + at with u = 0.')
        self.assertIn(self.flagged.id, self._queue_ids(self.user_a))

    def test_cannot_act_on_another_orgs_question(self):
        """Tenant isolation on the write path: org B's question is simply not there."""
        b_q = self._q(self.user_b, 'flagged')

        resp = self._post('/api/questions/review/', self.user_a,
                          {'question_id': b_q.id, 'action': 'reject'})

        self.assertEqual(resp.status_code, 404)
        b_q.refresh_from_db()
        self.assertEqual(b_q.verification, 'flagged')

    def test_unknown_action_is_rejected(self):
        resp = self._post('/api/questions/review/', self.user_a,
                          {'question_id': self.flagged.id, 'action': 'delete'})
        self.assertEqual(resp.status_code, 400)

    def test_missing_question_is_404(self):
        resp = self._post('/api/questions/review/', self.user_a,
                          {'question_id': 999999, 'action': 'approve'})
        self.assertEqual(resp.status_code, 404)


class RejectedExclusionTests(ReviewTestBase):
    """A rejected question must not find its way into a paper. The bank listing is
    where papers pick questions from, so that is where it has to disappear."""

    def setUp(self):
        super().setUp()
        self.good = self._q(self.user_a, 'verified')
        self.bad = self._q(self.user_a, 'flagged')
        self._post('/api/questions/review/', self.user_a,
                   {'question_id': self.bad.id, 'action': 'reject'})

    def test_rejected_questions_are_excluded_from_the_default_bank_listing(self):
        ids = {q['id'] for q in self._get('/api/questions/', self.user_a).json()}
        self.assertIn(self.good.id, ids)
        self.assertNotIn(self.bad.id, ids)

    def test_rejected_questions_are_still_fetchable_on_request(self):
        """The teacher wants to see what the AI got wrong."""
        ids = {q['id'] for q in
               self._get('/api/questions/', self.user_a, verification='rejected').json()}
        self.assertEqual(ids, {self.bad.id})

        ids = {q['id'] for q in
               self._get('/api/questions/', self.user_a, include_rejected='true').json()}
        self.assertEqual(ids, {self.good.id, self.bad.id})

    def test_rejected_question_is_reachable_through_the_review_queue(self):
        body = self._get('/api/questions/review/', self.user_a, status='rejected').json()
        self.assertEqual([r['question']['id'] for r in body['data']], [self.bad.id])

    def test_a_rejected_question_is_never_hard_deleted(self):
        self.assertTrue(Question.objects.filter(id=self.bad.id).exists())


class QualityDashboardTests(ReviewTestBase):
    """Physics: 12 verified + 4 corrected + 3 flagged + 1 skipped (n = 19 rated).
    Botany:  1 verified + 1 flagged  (n = 2 — below min_n, must not report rates).
    Org B holds a pile of flagged Physics questions that must not touch org A's numbers.
    """

    def setUp(self):
        super().setUp()
        for _ in range(12):
            self._q(self.user_a, 'verified')
        for _ in range(4):
            self._q(self.user_a, 'corrected', note=CORRECTED_NOTE)
        for _ in range(3):
            self._q(self.user_a, 'flagged')
        self._q(self.user_a, 'skipped')

        self._q(self.user_a, 'verified', subject='Botany', topic='Cells')
        self._q(self.user_a, 'flagged', subject='Botany', topic='Cells')

        for _ in range(8):
            self._q(self.user_b, 'flagged')

    def _quality(self, user=None, **params):
        return self._get('/api/questions/quality/', user or self.user_a, **params).json()

    def _subject(self, body, name):
        return next(g for g in body['by_subject'] if g['key'] == name)

    def test_overall_rates_are_arithmetically_correct(self):
        body = self._quality()
        overall = body['overall']

        self.assertEqual(overall['total'], 22)   # 20 Physics + 2 Botany
        self.assertEqual(overall['n'], 21)       # rated = 13 verified + 4 corrected + 4 flagged
        self.assertEqual(overall['counts']['verified'], 13)
        self.assertEqual(overall['counts']['corrected'], 4)
        self.assertEqual(overall['counts']['flagged'], 4)
        self.assertEqual(overall['counts']['skipped'], 1)

        # Hand-computed over n = 21: skipped is NOT in the denominator.
        self.assertEqual(overall['rates']['verified'], 0.619)      # 13/21
        self.assertEqual(overall['rates']['corrected'], 0.1905)    # 4/21
        self.assertEqual(overall['rates']['flagged'], 0.1905)      # 4/21
        self.assertEqual(overall['rates']['needs_review'], 0.381)  # 8/21
        self.assertTrue(overall['enough_data'])

    def test_subject_breakdown_rates_are_arithmetically_correct(self):
        physics = self._subject(self._quality(), 'Physics')

        self.assertEqual(physics['total'], 20)
        self.assertEqual(physics['n'], 19)                       # 12 + 4 + 3
        self.assertEqual(physics['rates']['verified'], 0.6316)   # 12/19
        self.assertEqual(physics['rates']['corrected'], 0.2105)  # 4/19
        self.assertEqual(physics['rates']['flagged'], 0.1579)    # 3/19
        self.assertEqual(physics['rates']['needs_review'], 0.3684)  # 7/19

    def test_min_n_guard_suppresses_rates_for_a_tiny_sample(self):
        """Botany is 1 flagged out of 2. Reporting "50% flagged" off two questions is
        a lie dressed up as data, so the rates are withheld — the counts are not."""
        botany = self._subject(self._quality(), 'Botany')

        self.assertEqual(botany['n'], 2)
        self.assertLess(botany['n'], MIN_SAMPLE_N)
        self.assertIsNone(botany['rates'])
        self.assertFalse(botany['enough_data'])
        self.assertEqual(botany['counts']['flagged'], 1)

    def test_min_n_guard_keeps_a_tiny_sample_off_the_worst_offenders_chart(self):
        """Botany's raw 50% needs-review beats Physics' 36.8%. Without the guard it
        would top the chart on the strength of one question."""
        body = self._quality()
        worst = body['worst_subjects']

        self.assertEqual(body['min_n'], MIN_SAMPLE_N)
        self.assertEqual([h['key'] for h in worst], ['Physics'])
        self.assertEqual(worst[0]['n'], 19)
        self.assertEqual(worst[0]['corrected'], 4)
        self.assertEqual(worst[0]['flagged'], 3)
        self.assertEqual(worst[0]['needs_review_rate'], 0.3684)

    def test_lowering_min_n_lets_the_tiny_sample_back_in(self):
        """Proves the suppression above is the guard doing its job, not a lost row."""
        body = self._quality(min_n=2)
        worst = body['worst_subjects']

        self.assertEqual([h['key'] for h in worst], ['Botany', 'Physics'])
        self.assertEqual(worst[0]['needs_review_rate'], 0.5)     # 1/2
        self.assertEqual(self._subject(body, 'Botany')['rates']['flagged'], 0.5)

    def test_quality_is_tenant_isolated(self):
        """Org B's 8 flagged questions must not appear in org A's numbers, and org B
        must see only its own."""
        a = self._quality()
        b = self._quality(self.user_b)

        self.assertEqual(a['overall']['counts']['flagged'], 4)   # not 12
        self.assertEqual(a['overall']['total'], 22)

        self.assertEqual(b['overall']['total'], 8)
        self.assertEqual(b['overall']['counts']['flagged'], 8)
        # 8 questions is below min_n, so org B gets counts but no rates.
        self.assertIsNone(b['overall']['rates'])
        self.assertEqual(
            self._quality(self.user_b, min_n=8)['overall']['rates']['flagged'], 1.0)

    def test_worst_topics_are_ranked_too(self):
        body = self._quality()
        self.assertEqual([h['key'] for h in body['worst_topics']], ['Kinematics'])
        self.assertEqual(body['worst_topics'][0]['scope'], 'topic')

    def test_human_review_does_not_erase_the_generation_signal(self):
        """The dashboard measures the GENERATOR, so a teacher working the queue must not
        flatter it. Approving a flagged question still leaves it counted as flagged —
        the machine verdict is recovered from the note (see _ai_state)."""
        flagged = Question.objects.filter(org=self.org_a, verification='flagged',
                                          subject='Physics').first()
        self._post('/api/questions/review/', self.user_a,
                   {'question_id': flagged.id, 'action': 'approve'})

        physics = self._subject(self._quality(), 'Physics')

        self.assertEqual(physics['n'], 19)                       # unchanged
        self.assertEqual(physics['counts']['flagged'], 3)        # still counted as flagged
        self.assertEqual(physics['counts']['approved'], 1)       # and now also approved
        self.assertEqual(physics['rates']['flagged'], 0.1579)    # rate did not move

    def test_rejected_questions_still_count_against_quality(self):
        """Rejecting the generator's worst output must not make the generator look good."""
        flagged = Question.objects.filter(org=self.org_a, verification='flagged',
                                          subject='Physics').first()
        self._post('/api/questions/review/', self.user_a,
                   {'question_id': flagged.id, 'action': 'reject'})

        physics = self._subject(self._quality(), 'Physics')
        self.assertEqual(physics['counts']['flagged'], 3)
        self.assertEqual(physics['counts']['rejected'], 1)
        self.assertEqual(physics['rates']['needs_review'], 0.3684)


class QualityTimeSeriesTests(ReviewTestBase):
    """Drift over time: a corrected-rate that climbs day over day means generation
    quality is degrading, and that is the whole point of the series."""

    def _on(self, days_ago):
        d = timezone.localtime(timezone.now()).date() - timedelta(days=days_ago)
        # Midday local, so the bucket a row lands in is unambiguous.
        return timezone.make_aware(datetime.combine(d, time(12, 0)),
                                   timezone.get_current_timezone())

    def _key(self, days_ago):
        return (timezone.localtime(timezone.now()).date() - timedelta(days=days_ago)).isoformat()

    def setUp(self):
        super().setUp()
        # Two days ago: 4 verified, 0 corrected → corrected rate 0.0
        for _ in range(4):
            self._q(self.user_a, 'verified', created_at=self._on(2))
        # Yesterday: 2 verified, 2 corrected → corrected rate 0.5. Quality is drifting.
        for _ in range(2):
            self._q(self.user_a, 'verified', created_at=self._on(1))
        for _ in range(2):
            self._q(self.user_a, 'corrected', note=CORRECTED_NOTE, created_at=self._on(1))
        # Well outside a 30-day window.
        self._q(self.user_a, 'flagged', created_at=self._on(90))

    def test_series_buckets_by_day_and_the_rates_are_correct(self):
        body = self._get('/api/questions/quality/', self.user_a,
                         days=30, bucket='day', min_n=1).json()
        series = {b['bucket']: b for b in body['series']}

        self.assertEqual(set(series), {self._key(2), self._key(1)})

        older = series[self._key(2)]
        self.assertEqual(older['n'], 4)
        self.assertEqual(older['rates']['corrected'], 0.0)
        self.assertEqual(older['rates']['verified'], 1.0)

        newer = series[self._key(1)]
        self.assertEqual(newer['n'], 4)
        self.assertEqual(newer['rates']['corrected'], 0.5)    # 2/4 — the early warning
        self.assertEqual(newer['rates']['needs_review'], 0.5)

    def test_series_window_excludes_old_questions(self):
        body = self._get('/api/questions/quality/', self.user_a,
                         days=30, bucket='day', min_n=1).json()
        self.assertNotIn(self._key(90), {b['bucket'] for b in body['series']})
        # ...but it is still in the overall totals, which are not windowed.
        self.assertEqual(body['overall']['total'], 9)

        wide = self._get('/api/questions/quality/', self.user_a,
                         days=120, bucket='day', min_n=1).json()
        self.assertIn(self._key(90), {b['bucket'] for b in wide['series']})

    def test_min_n_guard_applies_to_the_series_too(self):
        """4 questions in a day is not enough to call the day's quality."""
        body = self._get('/api/questions/quality/', self.user_a,
                         days=30, bucket='day').json()   # default min_n = 10
        for bucket in body['series']:
            self.assertIsNone(bucket['rates'])
            self.assertFalse(bucket['enough_data'])
            self.assertGreater(bucket['total'], 0)       # counts still reported

    def test_weekly_buckets_collapse_the_days(self):
        body = self._get('/api/questions/quality/', self.user_a,
                         days=30, bucket='week', min_n=1).json()
        self.assertEqual(body['bucket'], 'week')
        # Every bucket key is an ISO Monday.
        for b in body['series']:
            self.assertEqual(datetime.fromisoformat(b['bucket']).weekday(), 0)
        self.assertEqual(sum(b['total'] for b in body['series']), 8)
