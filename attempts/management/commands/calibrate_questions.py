"""Recalibrate empirical question difficulty from graded attempts.

Aggregates every graded QuestionResponse per question and writes the measured p_value and
Easy/Medium/Hard/HOTS label back onto the bank, so assembly can balance by what students
actually did instead of the LLM's guess. Cheap and idempotent — safe to run on a schedule.

    python manage.py calibrate_questions
    python manage.py calibrate_questions --org 12
    python manage.py calibrate_questions --min-students 10
"""
from django.core.management.base import BaseCommand

from attempts.service.calibrationservice import recalibrate


class Command(BaseCommand):
    help = "Recalibrate empirical question difficulty (p_value) from graded attempts."

    def add_arguments(self, parser):
        parser.add_argument("--org", type=int, default=None,
                            help="Restrict to one org's attempts (writes to the questions they reference).")
        parser.add_argument("--min-students", type=int, default=None,
                            help="Minimum graded responses before a question is calibrated (default: MIN_STUDENTS).")

    def handle(self, *args, **opts):
        summary = recalibrate(org_id=opts["org"], min_students=opts["min_students"])
        self.stdout.write(self.style.MIGRATE_HEADING(
            "Empirical difficulty recalibration"))
        self.stdout.write(f"  calibrated:              {summary['calibrated']}")
        self.stdout.write(f"  skipped_below_threshold: {summary['skipped_below_threshold']}")
        self.stdout.write(f"  min_students:            {summary['min_students']}")
