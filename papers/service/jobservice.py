"""
Background execution for AI generation jobs.

Generating a full paper is tens of LLM calls and minutes of wall-clock. Running
that inside the HTTP request holds a gunicorn worker open for the whole time and
loses everything to a proxy timeout, so generation is enqueued as a GenerationJob
and executed off-request; the client polls for progress.

This deliberately uses a plain daemon thread rather than Celery/Redis so it needs
no new infrastructure. The trade-off is explicit: a process restart abandons any
in-flight job (it is left RUNNING and can be retried), and work does not survive
across replicas. That is acceptable for the current single-node deployment — when
a broker is introduced, only `enqueue` needs to change; `run_job` is already a
pure, side-effect-complete unit of work and can be handed to a real worker as-is.
"""
from __future__ import annotations

import datetime
import logging
import threading
import traceback

from django.db import close_old_connections
from django.utils import timezone

from papers.models import GenerationJob, Paper
from papers.service.aigeneratorservice import AIGeneratorService

logger = logging.getLogger(__name__)

# Progress is written to the DB, so throttle it — one UPDATE per question would be
# a lot of writes for a 180-question paper and buys the user nothing.
_PROGRESS_STRIDE = 5

# A RUNNING job that hasn't reported progress in this long is presumed dead: its
# process was restarted, redeployed, or scaled away mid-run (routine on a PaaS host
# like Azure App Service). Without reaping, such a job sits at RUNNING forever and the
# user watches a spinner that will never finish. Comfortably longer than the slowest
# legitimate gap between progress writes (a batch + its inter-batch delay + backoff).
STALE_AFTER = datetime.timedelta(minutes=15)


def reap_stale_jobs() -> int:
    """Fail any RUNNING job whose worker died without recording an outcome.

    Background jobs live on threads inside the web process, so a restart, redeploy or
    scale-in takes them with it — routine on a PaaS host. The job row is left at
    RUNNING and the client polls it forever. This marks such jobs FAILED so the user
    gets a real error (and can retry) instead of an eternal spinner.

    Called on job polling, so it needs no scheduler. Cheap: one indexed UPDATE, and it
    matches nothing in the normal case.
    """
    cutoff = timezone.now() - STALE_AFTER
    stale = GenerationJob.objects.filter(
        status__in=[GenerationJob.STATUS_RUNNING, GenerationJob.STATUS_QUEUED],
        updated_at__lt=cutoff,
    )
    n = stale.update(
        status=GenerationJob.STATUS_FAILED,
        message="Generation was interrupted",
        error="The worker running this job stopped before it finished "
              "(the server was restarted, redeployed, or scaled). Please try again.",
        updated_at=timezone.now(),
    )
    if n:
        logger.warning("Reaped %d stale generation job(s) older than %s", n, STALE_AFTER)

    # Piggyback the rate-limit counter cleanup on the same poll-driven sweep, so it needs
    # no scheduler either. Without it the counter table grows one row per key per window,
    # forever. Never let it fail the reap — a bloated counter table is a slow problem, a
    # broken job poller is an immediate one.
    try:
        from utility.decorator.ratelimit import purge_old_counters
        purge_old_counters()
    except Exception:
        logger.exception("Rate-limit counter purge failed; continuing")

    return n


def enqueue(job: GenerationJob) -> None:
    """Start `job` on a background thread and return immediately."""
    t = threading.Thread(target=_thread_main, args=(job.id,), daemon=True,
                         name=f"genjob-{job.id}")
    t.start()


def _thread_main(job_id: int) -> None:
    """Thread entry point. The connection cleanup lives here, not in `_run_guarded`,
    because the worker thread owns its own DB connection — doing it in `_run_guarded`
    would close the *caller's* connection whenever a job is run inline (tests, a
    future synchronous retry path)."""
    try:
        _run_guarded(job_id)
    finally:
        close_old_connections()


def _run_guarded(job_id: int) -> None:
    """Run a job, recording any crash on the job itself.

    A job must never die silently — an unhandled escape here would leave the client
    polling a spinner forever, so every exception becomes a FAILED status the user
    can actually see. Safe to call inline.
    """
    try:
        run_job(job_id)
    except Exception:
        logger.exception("Generation job %s crashed", job_id)
        try:
            GenerationJob.objects.filter(id=job_id).update(
                status=GenerationJob.STATUS_FAILED,
                error=traceback.format_exc()[-4000:],
                message="Generation failed",
            )
        except Exception:
            logger.exception("Could not even record failure for job %s", job_id)


def run_job(job_id: int) -> None:
    """Execute a generation job to completion, recording progress as it goes."""
    job = GenerationJob.objects.get(id=job_id)
    job.status = GenerationJob.STATUS_RUNNING
    job.message = "Starting"
    job.save(update_fields=["status", "message", "updated_at"])

    params = job.params or {}
    generator = AIGeneratorService()

    last_written = [-1]

    def progress(done: int, total: int, message: str) -> None:
        # Always write the first and last tick, plus every _PROGRESS_STRIDE questions.
        if done != last_written[0] and (
            done % _PROGRESS_STRIDE == 0 or done in (0, total) or done < last_written[0]
        ):
            last_written[0] = done
            GenerationJob.objects.filter(id=job.id).update(
                done_steps=done, total_steps=total, message=message[:300],
                # QuerySet.update() bypasses Model.save(), so `auto_now` does NOT fire
                # here. Without setting it explicitly, updated_at would never advance
                # during a run and the stale-job reaper would kill healthy long jobs.
                updated_at=timezone.now(),
            )

    if job.kind == GenerationJob.KIND_QUESTIONS:
        result = generator.generate_questions(
            exam=params.get("exam", ""),
            subject=params.get("subject", ""),
            topic=params.get("topic", ""),
            q_type=params.get("q_type", "MCQ"),
            difficulty=params.get("difficulty", "Mixed"),
            bloom=params.get("bloom", "Mixed"),
            count=int(params.get("count") or 10),
            language=params.get("language") or "English",
        )
        payload = {"questions": result}
    else:
        content = generator.generate_paper(
            exam_type=params.get("exam_type", ""),
            subjects=params.get("subjects") or [],
            difficulty=params.get("difficulty", "medium"),
            total_marks=int(params.get("total_marks") or 0),
            blueprint=params.get("blueprint"),
            progress=progress,
            language=params.get("language") or "English",
        )
        payload = content
        # Persist onto the Paper row the request already created, so the paper is
        # complete the moment the job reports done.
        if job.paper_id:
            from papers.service.paperservice import finalize_generated_paper
            finalize_generated_paper(job.paper_id, content, params)

    job.refresh_from_db()
    job.result = payload
    job.usage = generator.last_usage
    job.status = GenerationJob.STATUS_DONE
    job.message = "Complete"
    job.save(update_fields=["result", "usage", "status", "message", "updated_at"])
    logger.info("Generation job %s done (usage=%s)", job.id, generator.last_usage)

    _charge_for_job(job, generator.last_usage)


def _charge_for_job(job: GenerationJob, usage: dict) -> None:
    """Bill the org for the AI spend this job just incurred.

    The usage used to be handed to the client, which was trusted to call
    POST /api/billing/charge/ itself — so a client that never made that call was never
    billed. The debit now happens here, where the tokens were actually spent.

    Keyed on `job:<id>`, which is unique on the ledger, so a re-run or retry of this job
    cannot debit twice. A billing failure never fails the job: the paper exists and the
    user must get it — we log loudly instead.
    """
    from billing.service.billingservice import BillingService

    try:
        title = (job.params or {}).get("title") or ""
        label = "Paper generation" if job.kind == GenerationJob.KIND_PAPER else "Question generation"
        result = BillingService({}).charge_usage(
            job.org_id,
            input_tokens=(usage or {}).get("input_tokens", 0),
            output_tokens=(usage or {}).get("output_tokens", 0),
            # Cached prompt tokens are NOT in input_tokens, and they are not free —
            # a cache write costs 1.25x an input token. Dropping these under-bills.
            cache_read_tokens=(usage or {}).get("cache_read_input_tokens", 0),
            cache_write_tokens=(usage or {}).get("cache_creation_input_tokens", 0),
            reason=f"{label}: {title}" if title else label,
            ref=f"job:{job.id}",
        )
        logger.info("Billing for job %s: %s", job.id, result)
    except Exception:
        logger.exception("Could not charge org %s for generation job %s (usage=%s)",
                         job.org_id, job.id, usage)
