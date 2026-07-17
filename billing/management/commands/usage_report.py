"""Print an AI-spend rollup from the CreditTxn ledger — cost visibility for operators.

    python manage.py usage_report                 # all orgs, last 30 days
    python manage.py usage_report --days 7
    python manage.py usage_report --org 12         # one org, with its reason breakdown
    python manage.py usage_report --json           # machine-readable

Complements the per-generation phase split (generation / answer-verify / diagram-verify)
that AIGeneratorService.usage_by_phase exposes at generation time: this is the durable,
after-the-fact view of what was actually billed.
"""
import json as _json

from django.core.management.base import BaseCommand

from billing.service.billingservice import usage_summary


class Command(BaseCommand):
    help = "Roll up recorded AI spend (credits, tokens, INR) from the billing ledger."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=30)
        parser.add_argument("--org", type=int, default=None, help="Restrict to one org id.")
        parser.add_argument("--json", action="store_true", help="Emit JSON instead of a table.")

    def handle(self, *args, **opts):
        summary = usage_summary(org_id=opts["org"], days=opts["days"])

        if opts["json"]:
            self.stdout.write(_json.dumps(summary, indent=2))
            return

        orgs = summary["orgs"]
        self.stdout.write(self.style.MIGRATE_HEADING(
            f"AI spend — last {summary['days']} days (since {summary['since'][:10]})"))
        if not orgs:
            self.stdout.write("  (no consumption recorded in this window)")
            return

        tot_credits = sum(o["credits"] for o in orgs)
        tot_inr = sum(o["inr_estimate"] for o in orgs)
        self.stdout.write(
            f"  {'org':>6}  {'credits':>9}  {'in-tok':>10}  {'out-tok':>10}  "
            f"{'~INR':>9}  {'gens':>5}")
        for o in orgs:
            self.stdout.write(
                f"  {o['org_id']:>6}  {o['credits']:>9}  {o['input_tokens']:>10}  "
                f"{o['output_tokens']:>10}  {o['inr_estimate']:>9.2f}  {o['generations']:>5}")
            # Show the reason breakdown when a single org was requested.
            if opts["org"] is not None:
                for r in o["by_reason"]:
                    self.stdout.write(
                        f"        └ {r['credits']:>6} cr  ×{r['generations']:<4}  {r['reason']}")
        self.stdout.write(self.style.SUCCESS(
            f"  {'TOTAL':>6}  {tot_credits:>9}  {'':>10}  {'':>10}  {tot_inr:>9.2f}  "
            f"{sum(o['generations'] for o in orgs):>5}"))
