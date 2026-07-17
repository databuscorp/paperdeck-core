"""End-to-end tests for the hardened AI generation pipeline.

These run against a real test DB with a fake Anthropic client, so they cover the
parts that only break in integration: the background job, blueprint-driven planning,
persistence of a generated paper, and verification metadata surviving the round trip.
"""
import datetime
import json
import re

from django.test import TestCase
from django.utils import timezone

import papers.service.aigeneratorservice as ai
from blueprints.models import Blueprint, BlueprintSection
from papers.models import GenerationJob, Paper
from papers.service import jobservice
from papers.service.aigeneratorservice import AIGeneratorService
from papers.service.paperservice import load_blueprint_spec
from users.models import User


def _msg(blocks, tokens=(10, 20)):
    m = type('M', (), {})()
    m.content = blocks
    m.usage = type('U', (), {'input_tokens': tokens[0], 'output_tokens': tokens[1]})()
    m.stop_reason = 'end_turn'
    return m


def _tool_block(questions):
    b = type('B', (), {})()
    b.type = 'tool_use'
    b.input = {"questions": questions}
    return b


def _text_block(text):
    b = type('B', (), {})()
    b.type = 'text'
    b.text = text
    return b


class FakeAnthropic:
    """Stands in for the Anthropic client: emits schema-shaped questions via tool-use,
    and solves every question as option 0 (which is the key we generate)."""

    def __init__(self):
        self.gen_calls = 0
        outer = self

        class Messages:
            # `system` carries the frozen, cacheable half of the generation prompt
            # (see _generation_system). It is accepted and ignored here — what it
            # contains, and that the volatile half stays out of it, is pinned in
            # papers/tests_prompt_caching.py.
            def create(self, model, max_tokens, messages, tools=None, tool_choice=None,
                       system=None):
                p = messages[0]['content']
                if p.startswith(('You are an expert', 'You are a senior')):
                    idx = [int(n) for n in re.findall(r'"index":\s*(\d+)', p)]
                    return _msg([_text_block(json.dumps(
                        [{"index": i, "option_index": 0, "final_answer": "",
                          "confidence": "high"} for i in idx]))])
                outer.gen_calls += 1
                n = int(re.search(r'Generate exactly (\d+)', p).group(1))
                seq = outer.gen_calls * 100
                return _msg([_tool_block([{
                    "text": f"Unique question {seq + i} concerning angular momentum and torque",
                    "difficulty": "Hard", "bloom": "Apply", "marks": 4,
                    "explanation": "because",
                    "options": [{"text": f"opt{j}", "correct": j == 0} for j in range(4)],
                } for i in range(n)])])

        self.messages = Messages()


class GenerationPipelineTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(username='t@example.com', email='t@example.com')

    def setUp(self):
        # Don't burn real seconds waiting between batches in tests.
        self._delay = AIGeneratorService._INTER_BATCH_DELAY
        AIGeneratorService._INTER_BATCH_DELAY = 0

    def tearDown(self):
        AIGeneratorService._INTER_BATCH_DELAY = self._delay

    def _service(self):
        svc = AIGeneratorService.__new__(AIGeneratorService)
        svc._client = FakeAnthropic()
        svc.last_usage = {'input_tokens': 0, 'output_tokens': 0}
        return svc

    # ── blueprint ────────────────────────────────────────────────────────────

    def test_blueprint_drives_generation(self):
        bp = Blueprint.objects.create(total_marks=100, duration='3 Hours',
                                      neg_marking_enabled=True, neg_marking_value=1)
        BlueprintSection.objects.create(
            blueprint=bp, name='Section A', subject='Physics', topics='Rotational Motion',
            q_type='MCQ', count=6, marks_per_q=4, difficulty='Hard', bloom='Analyze', order=0)
        BlueprintSection.objects.create(
            blueprint=bp, name='Section B', subject='Chemistry', topics='Thermodynamics',
            q_type='MCQ', count=4, marks_per_q=2, difficulty='Easy', bloom='Remember', order=1)

        spec = load_blueprint_spec(bp.id)
        self.assertEqual(len(spec['sections']), 2)
        self.assertEqual(spec['sections'][0]['topic'], 'Rotational Motion')
        # Negative marking comes from the blueprint's global setting.
        self.assertEqual(spec['sections'][0]['negative_marks'], -1.0)

        svc = self._service()
        # The blueprint must win over the request's exam defaults and difficulty.
        paper = svc.generate_paper(exam_type='NEET', subjects=[], difficulty='Medium',
                                   total_marks=100, blueprint=spec, verify=False)

        names = [s['subject'] for s in paper['sections']]
        counts = [len(s['questions']) for s in paper['sections']]
        self.assertEqual(names, ['Section A', 'Section B'])
        self.assertEqual(counts, [6, 4])          # blueprint counts, not NEET's 45s
        self.assertEqual(paper['sections'][0]['questions'][0]['marks'], 4)
        self.assertEqual(paper['sections'][1]['questions'][0]['marks'], 2)
        self.assertEqual(paper['sections'][0]['questions'][0]['negative_marks'], -1.0)

    # ── batching ─────────────────────────────────────────────────────────────

    def test_large_paper_is_batched_not_truncated(self):
        svc = self._service()
        paper = svc.generate_paper(exam_type='NEET', subjects=['Physics'],
                                   difficulty='Hard', total_marks=180, verify=False)
        qs = paper['sections'][0]['questions']
        # 45 questions is impossible in one 8192-token call — it must have batched.
        self.assertEqual(len(qs), 45)
        self.assertEqual(svc._client.gen_calls, 5)     # ceil(45 / _BATCH_SIZE)
        self.assertEqual([q['number'] for q in qs], list(range(1, 46)))

    # ── background job ───────────────────────────────────────────────────────

    def test_job_runs_paper_to_completion_and_persists_it(self):
        paper = Paper.objects.create(
            owner=self.user, title='Mock Test 1', exam_type='JEE Mains',
            subjects=['Physics'], difficulty='Hard', total_marks=120,
            status=Paper.STATUS_DRAFT, source='ai')
        job = GenerationJob.objects.create(
            owner=self.user, paper=paper, kind=GenerationJob.KIND_PAPER,
            params={'exam_type': 'JEE Mains', 'subjects': ['Physics'], 'difficulty': 'Hard',
                    'total_marks': 120, 'title': 'Mock Test 1', 'duration_minutes': 180},
            status=GenerationJob.STATUS_QUEUED)

        # Run inline (not threaded) so the assertions are deterministic.
        real_client = ai.AIGeneratorService.__init__

        def fake_init(self):
            self._client = FakeAnthropic()
            self.last_usage = {'input_tokens': 0, 'output_tokens': 0}

        ai.AIGeneratorService.__init__ = fake_init
        try:
            jobservice.run_job(job.id)
        finally:
            ai.AIGeneratorService.__init__ = real_client

        job.refresh_from_db()
        paper.refresh_from_db()

        self.assertEqual(job.status, GenerationJob.STATUS_DONE)
        self.assertEqual(job.percent, 100)
        self.assertEqual(job.message, 'Complete')
        self.assertGreater(job.usage.get('output_tokens', 0), 0)   # metered for billing

        # The paper itself is finished, not just the job.
        self.assertEqual(paper.status, Paper.STATUS_GENERATED)
        self.assertEqual(len(paper.content['sections'][0]['questions']), 30)
        self.assertTrue(paper.sections.exists())

    def test_job_records_failure_instead_of_hanging(self):
        job = GenerationJob.objects.create(
            owner=self.user, kind=GenerationJob.KIND_QUESTIONS,
            params={'count': 5}, status=GenerationJob.STATUS_QUEUED)

        def boom(self):
            raise RuntimeError("anthropic exploded")

        real_init = ai.AIGeneratorService.__init__
        ai.AIGeneratorService.__init__ = boom
        try:
            jobservice._run_guarded(job.id)
        finally:
            ai.AIGeneratorService.__init__ = real_init

        job.refresh_from_db()
        self.assertEqual(job.status, GenerationJob.STATUS_FAILED)
        self.assertIn('anthropic exploded', job.error)

    # ── stale-job reaping (PaaS restarts kill background threads) ────────────

    def test_stale_running_job_is_reaped_not_left_spinning(self):
        job = GenerationJob.objects.create(
            owner=self.user, kind=GenerationJob.KIND_PAPER, params={},
            status=GenerationJob.STATUS_RUNNING, message='Generating')
        # Simulate a worker that died 30 minutes ago mid-run.
        GenerationJob.objects.filter(id=job.id).update(
            updated_at=timezone.now() - datetime.timedelta(minutes=30))

        self.assertEqual(jobservice.reap_stale_jobs(), 1)

        job.refresh_from_db()
        self.assertEqual(job.status, GenerationJob.STATUS_FAILED)
        self.assertIn('restarted', job.error)

    def test_healthy_long_job_is_not_reaped(self):
        job = GenerationJob.objects.create(
            owner=self.user, kind=GenerationJob.KIND_PAPER, params={},
            status=GenerationJob.STATUS_RUNNING)
        # Reported progress a minute ago — slow, but alive.
        GenerationJob.objects.filter(id=job.id).update(
            updated_at=timezone.now() - datetime.timedelta(minutes=1))

        self.assertEqual(jobservice.reap_stale_jobs(), 0)
        job.refresh_from_db()
        self.assertEqual(job.status, GenerationJob.STATUS_RUNNING)

    def test_progress_writes_advance_updated_at(self):
        """QuerySet.update() skips auto_now, so progress must set updated_at itself —
        otherwise a healthy long-running job goes stale and gets reaped mid-run."""
        paper = Paper.objects.create(
            owner=self.user, title='P', exam_type='JEE Mains', subjects=['Physics'],
            difficulty='Hard', total_marks=120, status=Paper.STATUS_DRAFT, source='ai')
        job = GenerationJob.objects.create(
            owner=self.user, paper=paper, kind=GenerationJob.KIND_PAPER,
            params={'exam_type': 'JEE Mains', 'subjects': ['Physics'],
                    'difficulty': 'Hard', 'total_marks': 120, 'title': 'P'},
            status=GenerationJob.STATUS_QUEUED)
        GenerationJob.objects.filter(id=job.id).update(
            updated_at=timezone.now() - datetime.timedelta(hours=1))

        real_init = ai.AIGeneratorService.__init__

        def fake_init(self):
            self._client = FakeAnthropic()
            self.last_usage = {'input_tokens': 0, 'output_tokens': 0}

        ai.AIGeneratorService.__init__ = fake_init
        try:
            jobservice.run_job(job.id)
        finally:
            ai.AIGeneratorService.__init__ = real_init

        job.refresh_from_db()
        # The run must have refreshed updated_at, so the reaper leaves it alone.
        self.assertGreater(job.updated_at, timezone.now() - datetime.timedelta(minutes=1))
        self.assertEqual(jobservice.reap_stale_jobs(), 0)

    # ── verification metadata ────────────────────────────────────────────────

    def test_generated_questions_carry_verification(self):
        svc = self._service()
        qs = svc.generate_questions('JEE Mains', 'Physics', 'Rotation', 'MCQ',
                                    'Hard', 'Apply', count=3, dedupe=False)
        self.assertEqual(len(qs), 3)
        self.assertTrue(all(q['verification'] == 'verified' for q in qs))
        self.assertTrue(all(sum(1 for o in q['options'] if o['correct']) == 1 for q in qs))
