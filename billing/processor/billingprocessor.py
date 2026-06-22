from dataclasses import dataclass

import marshmallow_dataclass
from marshmallow import EXCLUDE


@dataclass
class ChargeRequest:
    # Token-based (preferred): credits are derived from real Claude usage.
    input_tokens:    int = 0
    output_tokens:   int = 0
    # Legacy tier fallback (used only when no tokens are supplied).
    question_count:  int = 0
    with_answer_key: bool = False
    versions:        int = 1
    title:           str = ''


@dataclass
class BuyRequest:
    pack: str


charge_req_schema = marshmallow_dataclass.class_schema(ChargeRequest)(unknown=EXCLUDE)
buy_req_schema    = marshmallow_dataclass.class_schema(BuyRequest)(unknown=EXCLUDE)
