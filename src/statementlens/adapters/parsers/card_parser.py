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
                # A transaction always names something. A "description" with no letters is a row of
                # some other table — ICICI's EMI schedule ("28/01/2026 3 11,357.00 1 3,887.00") was
                # booked as a ₹3,887 purchase in two statements. Digits-only was the old test, and the
                # slashes in that schedule's date slipped past it.
                if len(desc) < 2 or not re.search(r"[A-Za-z]", desc):
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
        return Statement(account, source_id, source_name, source_name[-8:],
                         tuple(_settle_directions_from_totals(text, rows)))


#: The reconciliation block some issuers print instead of marking each row (RBL):
#:   - Payments & Credits 13,873.00 / - Transferred to EMI 0.00 / + New Debits ... / + Fees & Charges
_PRINTED_CREDITS = re.compile(r"-\s*Payments\s*&\s*Credits\s+([\d,]+\.\d{2})", re.I)
_PRINTED_EMI_OUT = re.compile(r"-\s*Transferred\s+to\s+EMI\s+([\d,]+\.\d{2})", re.I)
_SAYS_CREDIT = re.compile(r"(?i)payment\s+received|transferred\s+to\s+emi|refund|reversal|cash\s*back")


def _paise(s: str) -> int:
    return round(float(s.replace(",", "")) * 100)


def _settle_directions_from_totals(text: str, rows: List[Transaction]) -> List[Transaction]:
    """Mark credits on a statement that prints no per-row credit marker, using its own totals.

    RBL's extracted text carries no Cr flag, so EVERY row went in as a debit: bill payments, a
    ₹10,843 EMI conversion and a ₹6,925 Myntra refund were all counted as spending. The statement
    does say how much came IN ("Payments & Credits" + "Transferred to EMI"), so: rows whose narration
    says payment/refund/EMI-transfer are credits, and if a remainder is left, the one row that
    exactly makes it up is a credit too (a refund reads like the purchase it reverses).

    Only acts when no row is already a credit (an issuer that marks rows is never second-guessed),
    and only on an unambiguous remainder — if two rows could fill it, it leaves both as they are,
    because guessing the wrong one would be worse than the known gap.
    """
    m = _PRINTED_CREDITS.search(text)
    if not m or not rows or any(not r.is_debit for r in rows):
        return rows
    e = _PRINTED_EMI_OUT.search(text)
    want = _paise(m.group(1)) + (_paise(e.group(1)) if e else 0)
    credit = {i for i, r in enumerate(rows) if _SAYS_CREDIT.search(r.description)}
    rest = want - sum(rows[i].amount.minor for i in credit)
    if rest > 0:
        fits = [i for i, r in enumerate(rows) if i not in credit and r.amount.minor == rest]
        if len(fits) == 1:
            credit.add(fits[0])
    if not credit:
        return rows
    import dataclasses
    return [dataclasses.replace(r, direction=Direction.CREDIT) if i in credit else r
            for i, r in enumerate(rows)]
