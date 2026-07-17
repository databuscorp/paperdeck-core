from dataclasses import dataclass

import marshmallow_dataclass
from marshmallow import EXCLUDE


@dataclass
class ChargeRequest:
    """DEPRECATED — generations are charged server-side now. See BillingService.charge."""
    # Token-based (preferred): credits are derived from real Claude usage.
    input_tokens:    int = 0
    output_tokens:   int = 0
    # Legacy tier fallback (used only when no tokens are supplied).
    question_count:  int = 0
    with_answer_key: bool = False
    versions:        int = 1
    title:           str = ''
    # Optional idempotency key. A client that charges for a generation job can send its
    # id; the server already billed `job:<id>`, so the charge collapses to a no-op.
    job_id:          int = 0


@dataclass
class BuyRequest:
    pack: str


charge_req_schema = marshmallow_dataclass.class_schema(ChargeRequest)(unknown=EXCLUDE)
buy_req_schema    = marshmallow_dataclass.class_schema(BuyRequest)(unknown=EXCLUDE)
