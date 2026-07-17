from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import marshmallow_dataclass
from dataclasses_json import dataclass_json
from marshmallow import EXCLUDE


# ── requests ──────────────────────────────────────────────────────────────────

@dataclass
class OMRSheetRequest:
    paper_id: int
    # Defaults to the number of questions actually in the paper.
    num_questions: Optional[int] = None
    options_per_question: Optional[int] = 4
    roll_digits: Optional[int] = 6
    # A sheet is immutable once printed — regenerating bumps sheet_version so an
    # already-distributed sheet keeps reading against the layout it was printed from.
    regenerate: Optional[bool] = False


omr_sheet_req_schema = marshmallow_dataclass.class_schema(OMRSheetRequest)(unknown=EXCLUDE)


# ── responses ─────────────────────────────────────────────────────────────────

@dataclass_json
@dataclass
class OMRSheetResponse:
    sheet_id: int
    paper_id: int
    sheet_version: int
    sheet_short_id: int
    num_questions: int
    options_per_question: int
    roll_digits: int
    num_pages: int
    pdf_url: Optional[str]
    layout: Dict[str, Any]
    created_at: Optional[str]


@dataclass_json
@dataclass
class OMRScanResponse:
    """The scan contract.

    responses[]  — one entry per question that was on a scanned page:
        question_number          1-based
        selected_option_index    0-based (0=A). NON-NULL ONLY WHEN status == 'ok'.
        selected_option          'A'/'B'/... mirror of the above, or null
        status                   ok | multiple_marks | blank | low_confidence
        confidence               0..1, confidence in the reported status+selection
        best_guess_option_index  a hint for the human reviewer on low_confidence.
                                 NEVER auto-grade this.
        scores                   per-option darkness, 0 (paper) .. 1 (printer ink)

    needs_review — every question_number whose status != 'ok'. A grading
    integration must route these to a human; it must not fill them in.
    """
    scan_id: Optional[int]
    sheet_id: int
    paper_id: int
    status: str
    roll_number: str
    roll: Optional[Dict[str, Any]]
    pages_scanned: List[int]
    responses: List[Dict[str, Any]]
    needs_review: List[int]
    missing_questions: List[int]
    warnings: List[str]
    diagnostics: Dict[str, Any]
