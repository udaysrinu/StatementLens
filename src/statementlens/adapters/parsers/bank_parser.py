"""SavingsStatementParser — parses savings/current-account statements (credit/debit/balance).

Handles the common Indian-bank layout `Date  Narration  Credit  Debit  Balance`, where empty
credit/debit columns print as either a literal 0 (newer SBI) or a dash '-' (older SBI), and long
narrations wrap onto the PREVIOUS line. Produces domain Statement/Transaction objects.

Implements the StatementParser port. Register it in the ParserRegistry to be auto-selected.
"""

from __future__ import annotations

import re
from datetime import date
from typing import List, Optional

from ...domain.models import Direction, Statement, Transaction
from ...domain.money import Money

_EMPTY = {"0", "0.00", "-", ""}
_ROW = re.compile(
    r"^(?P<date>\d{2}-\d{2}-\d{2,4})\s+(?P<desc>.*?)\s+"
    r"(?P<credit>[\d,]+\.\d{2}|0|-)\s+(?P<debit>[\d,]+\.\d{2}|0|-)\s+(?P<bal>[\d,]+\.\d{2})\s*$")
_HEADER = re.compile(r"(?i)date\s+transaction|balance|customer\s|welcome")
_UPI = re.compile(r"(?i)^UPI/")
_IMPS = re.compile(r"(?i)^IMPS")


def _to_date(s: str) -> Optional[date]:
    m = re.match(r"^(\d{2})-(\d{2})-(\d{2,4})$", s.strip())
    if not m:
        return None
    dd, mm, yy = m.groups()
    year = int(yy) if len(yy) == 4 else 2000 + int(yy)
    try:
        return date(year, int(mm), int(dd))
    except ValueError:
        return None


def _merchant(desc: str) -> str:
    parts = desc.split("/")
    if len(parts) >= 4 and _UPI.match(desc):
        return parts[3].strip()
    if _IMPS.match(desc) and len(parts) >= 3:
        return parts[2].strip()
    return desc.strip()[:40]


class SavingsStatementParser:
    """StatementParser for savings/current accounts (Credit/Debit/Balance columns)."""

    def can_parse(self, text: str) -> bool:
        return bool(re.search(r"(?i)date\s+transaction.*(debit|credit).*balance", text)) or \
            bool(_ROW.search(text))

    def parse(self, text: str, *, account: str, source_id: str,
              source_name: str) -> Statement:
        txns: List[Transaction] = []
        prev = ""  # wrapped-narration carry
        currency = "INR"
        for line in text.splitlines():
            s = line.strip()
            m = _ROW.match(s)
            if not m:
                if s and not _HEADER.search(s):
                    prev = s
                continue
            cr = m.group("credit").replace(",", "")
            dr = m.group("debit").replace(",", "")
            is_credit = cr not in _EMPTY
            amt = cr if is_credit else dr
            if amt in _EMPTY:
                prev = ""
                continue
            desc = m.group("desc").strip(" -") or prev
            bal = m.group("bal").replace(",", "")
            txns.append(Transaction(
                txn_date=_to_date(m.group("date")),
                description=desc,
                amount=Money.of(amt, currency),
                direction=Direction.CREDIT if is_credit else Direction.DEBIT,
                merchant=_merchant(desc),
                balance=Money.of(bal, currency),
                raw_date=m.group("date"),
                source_ref=source_id,
            ))
            prev = ""
        return Statement(account, source_id, source_name, source_name[-8:], tuple(txns))
