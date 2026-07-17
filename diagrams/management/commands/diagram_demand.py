"""Rank the diagrams the engine was asked for but could not draw.

Turns the durable DiagramDemand tally into a prioritised backlog: the top rows are the
renderers worth building (unknown subtypes) or fixing (render errors) next, ordered by how
often real generations actually asked for them.

    python manage.py diagram_demand                 # top 30, all categories
    python manage.py diagram_demand --limit 50
    python manage.py diagram_demand --category unknown_subtype   # only "build me" gaps
    python manage.py diagram_demand --json
"""
import json as _json

from django.core.management.base import BaseCommand

from diagrams.models import DiagramDemand


class Command(BaseCommand):
    help = "Rank unrenderable-diagram demand so missing/broken renderers can be prioritised."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=30)
        parser.add_argument("--category", default="",
                            help="Filter: unknown_subtype | unknown_type | render_error | other")
        parser.add_argument("--json", action="store_true")

    def handle(self, *args, **opts):
        qs = DiagramDemand.objects.all()
        if opts["category"]:
            qs = qs.filter(category=opts["category"])
        rows = list(qs.order_by("-count")[: opts["limit"]])

        if opts["json"]:
            self.stdout.write(_json.dumps([{
                "diagram_type": r.diagram_type, "subtype": r.subtype,
                "category": r.category, "count": r.count,
                "sample_reason": r.sample_reason,
                "last_seen": r.last_seen.isoformat(),
            } for r in rows], indent=2))
            return

        if not rows:
            self.stdout.write("No unrenderable-diagram demand recorded yet.")
            return

        self.stdout.write(self.style.MIGRATE_HEADING(
            "Unrenderable-diagram demand (build/fix these, most-requested first)"))
        self.stdout.write(f"  {'count':>6}  {'category':<16}  {'type/subtype'}")
        for r in rows:
            self.stdout.write(
                f"  {r.count:>6}  {r.category:<16}  {r.diagram_type}/{r.subtype}")
            if r.sample_reason:
                self.stdout.write(self.style.HTTP_INFO(
                    f"         e.g. {r.sample_reason.splitlines()[0][:120]}"))
