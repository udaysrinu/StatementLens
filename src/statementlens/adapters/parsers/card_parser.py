"""CardStatementParser — parses credit-card statements (single trailing amount per row).

Card statements list one amount per line (trailing), optionally flagged 'Cr' for a credit/refund.
Simpler than savings statements (no running balance). Implements the StatementParser port.
"""

from __future__ import annotations

import re
from datetime import date
from typing import List, Optional

from ...domain.models import Direction, Statement, Transaction
from ...domain.money import Money

_MONTHS = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
           "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}
_PATTERNS = [
    # "07-Aug-2025 MERCHANT CITY 5,000.00 DR 526873XXXXXX1234" — hyphenated month, and the amount is
    # followed by an explicit DR/CR flag plus the masked card number, so it is NOT trailing. Listed
    # first: the flag makes direction explicit, which the trailing-amount patterns have to guess.
    re.compile(r"(?P<date>\d{1,2}-[A-Za-z]{3}-\d{4})\s+(?P<desc>.+?)\s+(?P<amt>[\d,]+\.\d{2})"
               r"\s+(?P<flag>DR|CR)\b(?:\s+[\dX*]{6,})?\s*$", re.IGNORECASE),
    # "01/07/2026| 07:59 RSP*MERCHANT C 192.00 l" — date+time, then the rupee glyph mis-extracted as
    # a stray letter, then the amount, then a trailing glyph. A leading "+" before the currency marks
    # a credit (payment/cashback); its absence means a purchase.
    re.compile(r"(?P<date>\d{2}/\d{2}/\d{4})\s*\|\s*\d{2}:\d{2}\s+(?P<desc>.+?)\s+"
               r"(?P<plus>\+\s*)?[A-Za-z₹]\s*(?P<amt>[\d,]+\.\d{2})(?:\s+\S{1,3})?\s*$"),
    # Every trailing-amount layout accepts an optional DR/CR flag and a case-insensitive "Cr".
    # Previously only the hyphenated-month pattern took a flag, and "Cr" was matched
    # case-sensitively, so a numeric-date row ending in "DR"/"cr" matched NOTHING and the
    # transaction silently vanished from the statement.
    re.compile(r"(?P<date>\d{2}[/-]\d{2}[/-]\d{4})\s+(?P<desc>.+?)\s+(?P<amt>[\d,]+\.\d{2})"
               r"(?:\s*(?P<flag>DR|CR))?(?:\s*(?P<cr>Cr))?\s*$", re.IGNORECASE),
    re.compile(r"(?P<date>\d{1,2}\s+[A-Za-z]{3}\s+\d{4})\s+(?P<desc>.+?)\s+(?P<amt>[\d,]+\.\d{2})"
               r"(?:\s*(?P<flag>DR|CR))?(?:\s*(?P<cr>Cr))?\s*$", re.IGNORECASE),
    re.compile(r"(?P<date>\d{1,2}-[A-Za-z]{3}-\d{4})\s+(?P<desc>.+?)\s+(?P<amt>[\d,]+\.\d{2})"
               r"(?:\s*(?P<flag>DR|CR))?(?:\s*(?P<cr>Cr))?\s*$", re.IGNORECASE),
]


def _to_date(s: str) -> Optional[date]:
    s = s.strip()
    m = re.match(r"^(\d{2})[/-](\d{2})[/-](\d{4})$", s)
    if m:
        dd, mm, yyyy = m.groups()
        try:
            return date(int(yyyy), int(mm), int(dd))
        except ValueError:
            return None
    # accepts both "7 Aug 2025" and "07-Aug-2025"
    m = re.match(r"^(\d{1,2})[\s-]([A-Za-z]{3})[\s-](\d{4})$", s)
    if m:
        dd, mon, yyyy = m.groups()
        mm = _MONTHS.get(mon.lower())
        if mm:
            try:
                return date(int(yyyy), mm, int(dd))
            except ValueError:
                return None
    return None


class CardStatementParser:
    """StatementParser for credit-card statements (trailing single amount)."""

    def can_parse(self, text: str) -> bool:
        # card statements rarely have the savings "Credit Debit Balance" header;
        # match if we see trailing-amount rows but not the tri-column bank layout
        if re.search(r"(?i)date\s+transaction.*(debit|credit).*balance", text):
            return False
        return any(p.search(line.strip()) for p in _PATTERNS for line in text.splitlines()[:200])

    def parse(self, text: str, *, account: str, source_id: str, source_name: str) -> Statement:
        rows: List[Transaction] = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            for pat in _PATTERNS:
                m = pat.search(line)
                if not m:
                    continue
                desc = m.group("desc").strip()
                if len(desc) < 2 or re.fullmatch(r"[\d,.\s]+", desc):
                    break
                g = m.groupdict()
                # an explicit DR/CR flag is authoritative; then a leading "+" (payment/cashback);
                # otherwise fall back to a trailing "Cr"
                flag = (g.get("flag") or "").upper()
                is_credit = (flag == "CR" if flag
                             else bool(g.get("plus")) or bool(g.get("cr")))
                rows.append(Transaction(
                    txn_date=_to_date(m.group("date")),
                    description=desc,
                    amount=Money.of(m.group("amt").replace(",", ""), "INR"),
                    direction=Direction.CREDIT if is_credit else Direction.DEBIT,
                    merchant=desc[:40],
                    raw_date=m.group("date"),
                    source_ref=source_id,
                ))
                break
        return Statement(account, source_id, source_name, source_name[-8:], tuple(rows))
