"""Import diagnostics — explain WHY a statement produced no transactions.

The worst failure mode for a personal-finance app is a confident empty dashboard: the import
"succeeded", zero rows appeared, and the user has no idea whether they have no spending or a broken
importer. Silence reads as "you're all caught up" when it actually means "we couldn't read this".

Every unparseable document gets a specific, actionable reason instead. These reasons are surfaced in
the CLI and are what onboarding shows the user.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

#: Text layer this short means there is effectively no text — the page is an image.
_MIN_TEXT_CHARS = 200

#: SBI's OnlineSBI "Find Transactions" web printout. Rows look like
#: `15-Sep-18 (15-Sep-2018) 382.48` — a single amount, no balance and no debit/credit column,
#: because direction was conveyed by column POSITION which text extraction discards.
_WEB_PRINTOUT_ROW = re.compile(r"\d{1,2}-[A-Za-z]{3}-\d{2}\s+\(\d{1,2}-[A-Za-z]{3}-\d{4}\)")
_WEB_PRINTOUT_MARKERS = ("find transactions", "onlinesbi", "you are here:")


class ImportProblem:
    """Reason codes. Stable strings so the UI can map them to help text."""
    NO_TEXT_LAYER = "no_text_layer"
    WEB_PRINTOUT = "web_printout"
    NO_ROWS_MATCHED = "no_rows_matched"
    ENCRYPTED = "encrypted"


@dataclass(frozen=True)
class Diagnosis:
    problem: str
    message: str          # user-facing, plain language, says what to DO
    detail: str = ""      # technical note for logs/bug reports

    @property
    def is_fatal(self) -> bool:
        """True when no amount of retrying helps — the document itself can't be used as-is."""
        return self.problem in (ImportProblem.NO_TEXT_LAYER, ImportProblem.WEB_PRINTOUT)


def diagnose(text: str, *, source_name: str = "") -> Optional[Diagnosis]:
    """Explain why `text` yielded no transactions, or None if the text looks parseable.

    Called only after every registered parser has declined, so a None here means "the text looks
    fine, the parsers just don't know this bank yet" — a different and more fixable problem.
    """
    stripped = (text or "").strip()

    if len(stripped) < _MIN_TEXT_CHARS:
        return Diagnosis(
            ImportProblem.NO_TEXT_LAYER,
            f"{source_name or 'This PDF'} is a scanned image, not a text statement, so there is "
            "nothing to read. Download the original e-statement from your bank's site or email "
            "instead of a scan or photo.",
            detail=f"extracted {len(stripped)} chars of text")

    low = stripped.lower()
    if (_WEB_PRINTOUT_ROW.search(stripped)
            and any(m in low for m in _WEB_PRINTOUT_MARKERS)):
        return Diagnosis(
            ImportProblem.WEB_PRINTOUT,
            f"{source_name or 'This PDF'} is a printout of the bank's website, not a real "
            "statement. It lists amounts but not whether each one was money in or money out, so "
            "importing it would produce wrong totals. Please use the official e-statement PDF.",
            detail="matched OnlineSBI 'Find Transactions' layout: single amount column, "
                   "no balance and no debit/credit indicator")

    return Diagnosis(
        ImportProblem.NO_ROWS_MATCHED,
        f"No transactions were recognised in {source_name or 'this PDF'}. The layout may be from a "
        "bank we don't support yet.",
        detail=f"{len(stripped)} chars of text extracted but no parser matched")
