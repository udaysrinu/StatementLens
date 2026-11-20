"""Each account's latest balance, signed, for other tools (`statementlens balances --json`, read by Netfolio).

Pure: rows in, figures out, integer paise. A row is (id, account, iso_date, minor, direction,
balance_minor, statement_id, description), one account's settled rows in ledger order.
"""
from __future__ import annotations

from datetime import date
from typing import List, Optional, Sequence, Tuple

#: A longer gap between two balance rows is a missing statement, not a misread row.
MISSING_STATEMENT_DAYS = 25


def _days(a: str, b: str) -> int:
    return (date.fromisoformat(b) - date.fromisoformat(a)).days


def walk(rows: Sequence[tuple]) -> Tuple[Optional[int], Optional[str], List[tuple]]:
    """(signed latest balance, its date, [(prev, row, off_by_minor)] breaks inside a statement period).

    Banks print an overdrawn balance as its magnitude (an overdraft of −₹1,234.50 prints as "1234.50"), so the
    printed figure alone has the wrong sign. A printed balance equal to |expected| while expected is
    negative reconciles, and the SIGNED value carries forward; that carried value is the balance
    reported, which is why this walks the chain instead of reading the last printed number.
    ponytail: an account whose very first balance row is already overdrawn reads positive until a
    later row reveals the sign.
    """
    bal = [r for r in rows if r[5] is not None]
    if not bal:
        return None, None, []
    signed, breaks = bal[0][5], []
    for prev, cur in zip(bal, bal[1:]):
        exp = signed + (cur[3] if cur[4] == "credit" else -cur[3])
        if exp == cur[5] or (exp < 0 and -exp == cur[5]):
            signed = exp
        else:
            if _days(prev[2], cur[2]) < MISSING_STATEMENT_DAYS:
                breaks.append((prev, cur, cur[5] - exp))
            signed = cur[5]                     # a missing statement: restart from what is printed
    return signed, bal[-1][2], breaks
