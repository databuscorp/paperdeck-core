"""Run the vision verifier over every catalog example — a visual-regression grader.

The unit suite proves each catalog diagram *renders*; this command proves each one is
*visually correct*, using the same vision verifier that guards live generation. It is the
CI/pre-release counterpart to the render-parity tests: run it after any renderer change and
it flags figures that regressed into something the model judges wrong (blank, tofu, mangled
labels, reversed arrows) — defects a byte-diff of the SVG would never surface.

    python manage.py verify_catalog_diagrams                 # grade all, print a summary
    python manage.py verify_catalog_diagrams --only physics  # one domain
    python manage.py verify_catalog_diagrams --fail-on major  # non-zero exit on any major

Needs ANTHROPIC_API_KEY (it makes one vision call per example). Cost is bounded: one Haiku
call per catalog example, no repair loop.
"""
import json
import os
import re

from django.core.management.base import BaseCommand, CommandError

from diagrams.service.dispatcher import dispatch_render
from papers.service.aigeneratorservice import HAIKU_MODEL, _DIAGRAM_SCHEMA_HINT
from papers.service.diagramverifier import CLEAN, MAJOR, MINOR, SKIPPED, DiagramVerifier

_LINE_RE = re.compile(r'^\s*(\{"diagram_type".*\})\s*$', re.M)


def _catalog_examples():
    for raw in _LINE_RE.findall(_DIAGRAM_SCHEMA_HINT):
        try:
            yield json.loads(raw)
        except Exception:
            continue


class Command(BaseCommand):
    help = "Visually verify every catalog diagram example with the vision verifier."

    def add_arguments(self, parser):
        parser.add_argument("--only", default="", help="Restrict to one diagram_type (e.g. physics).")
        parser.add_argument("--fail-on", choices=[MINOR, MAJOR], default=MAJOR,
                            help="Exit non-zero if any figure reaches this severity (default: major).")
        parser.add_argument("--limit", type=int, default=0, help="Grade at most N examples (0 = all).")

    def handle(self, *args, **opts):
        try:
            import anthropic
        except Exception as exc:  # pragma: no cover
            raise CommandError(f"anthropic SDK unavailable: {exc}")

        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise CommandError("ANTHROPIC_API_KEY is not set — the grader needs a vision call per example.")

        client = anthropic.Anthropic(api_key=api_key)
        verifier = DiagramVerifier(client, HAIKU_MODEL)

        examples = list(_catalog_examples())
        if opts["only"]:
            examples = [e for e in examples if e.get("diagram_type") == opts["only"]]
        if opts["limit"]:
            examples = examples[: opts["limit"]]
        if not examples:
            raise CommandError("No catalog examples matched.")

        counts = {CLEAN: 0, MINOR: 0, MAJOR: 0, SKIPPED: 0, "render_failed": 0}
        offenders = []

        for ex in examples:
            key = f"{ex.get('diagram_type')}/{ex.get('subtype')}"
            _, result = dispatch_render(ex, save_files=False)
            if not result.success:
                counts["render_failed"] += 1
                offenders.append((key, "render_failed", [result.error.splitlines()[0] if result.error else ""]))
                self.stdout.write(self.style.ERROR(f"  RENDER FAIL  {key}"))
                continue

            # Judge the figure against a description synthesised from the subtype — there is no
            # student question here, so the bar is "is this a correct, clean depiction of X".
            question = {
                "image_svg": result.svg_content,
                "text": f"A {ex.get('subtype', '').replace('_', ' ')} diagram.",
            }
            verdict = verifier.verify(question, subject=ex.get("diagram_type", ""))
            sev = verdict.get("severity", SKIPPED)
            counts[sev] = counts.get(sev, 0) + 1
            if sev == MAJOR:
                offenders.append((key, sev, verdict.get("defects", [])))
                self.stdout.write(self.style.ERROR(f"  MAJOR  {key}: {'; '.join(verdict.get('defects') or [])}"))
            elif sev == MINOR:
                offenders.append((key, sev, verdict.get("defects", [])))
                self.stdout.write(self.style.WARNING(f"  minor  {key}: {'; '.join(verdict.get('defects') or [])}"))
            else:
                self.stdout.write(f"  {sev:<7}{key}")

        total = len(examples)
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING(
            f"Graded {total} figures: "
            f"{counts[CLEAN]} clean, {counts[MINOR]} minor, {counts[MAJOR]} major, "
            f"{counts[SKIPPED]} skipped, {counts['render_failed']} render-failed."))

        fail_on = opts["fail_on"]
        breached = counts[MAJOR] + counts["render_failed"]
        if fail_on == MINOR:
            breached += counts[MINOR]
        if breached:
            raise CommandError(f"{breached} figure(s) at or above severity '{fail_on}'.")
