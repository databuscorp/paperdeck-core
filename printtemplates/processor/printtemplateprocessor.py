from dataclasses import dataclass
from typing import Optional

import marshmallow_dataclass
from dataclasses_json import dataclass_json


@dataclass
class PrintTemplateRequest:
    name:         str
    style_config: str = '{}'
    is_active:    bool = False
    id:           Optional[int] = None


print_template_req_schema = marshmallow_dataclass.class_schema(PrintTemplateRequest)()


@dataclass_json
@dataclass
class PrintTemplateResponse:
    id:           int
    org_id:       Optional[int]
    name:         str
    style_config: str
    is_active:    bool
    created_at:   str
