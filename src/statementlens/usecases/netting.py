"""Cancelled transactions and person-level netting.

Two DIFFERENT things hide in the same shape (money out, then money back from the same
counterparty), and conflating them would be wrong:

1. **Reversals.** A failed booking or a bounced payment: ₹1,554 to IRCTC and ₹1,554 back the SAME
   day. That money never actually left the account. Counting it as a spend overstates spending — it
   is an error in the ledger, not a decision, so this is a *correction*.

2. **Settling up.** ₹5,000 lent to a friend in December, ₹5,000 back in March. Both legs are real
   money that really moved. Netting them is a *preference* — "what did I end up out of pocket with
   this person?" — not a correction. Gross is equally valid: you really did transfer ₹5,000.

So reversals are matched narrowly (exact amount, same counterparty, short window) and can be
excluded by default, while person-netting is a view you opt into. The evidence for the window came
from real data: exact-amount reversal pairs cluster at a same-day gap and then jump to 46+ days,
with almost nothing in between. 46 days apart is a friend paying you back, not a cancellation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from typing import Dict, Iterable, List, Optional, Tuple

from ..domain.models import Transaction
from .similar import merchant_key

#: The bank's own transaction reference (RRN / UTR), which must be read POSITIONALLY — it is the
#: numeric field straight after the channel, optionally after a DR/CR marker:
#:     IMPS/600000000001/IBKL-xx000-Payee/Loan Rep
#:     UPI/DR/440000000001/PAYEE/SBIN/9000000002/Rent
#:
#: A plain "first 10+ digit run" search is WRONG here, and dangerously so: a UPI VPA often ends in the
#: payee's 10-digit phone number (".../SBIN/9000000002/Rent"), which is IDENTICAL on every transfer
#: with that person. Matching on it made every same-amount payment to a friend look like a bank
#: reversal with "certain" confidence — i.e. it would have deleted real transfers from the totals.
#:
#: Not taken from upi.parse_upi(): that decoder expects a DR/CR segment, and an IMPS narration has
#: none, so its `ref` field holds the payee name instead. Fixing the shared decoder would ripple into
#: the categorizer for no gain here.
_REF_RE = re.compile(r"^(?:UPI|IMPS|NEFT|RTGS)/(?:(?:DR|CR)/)?(\d{8,})/", re.IGNORECASE)


def _ref_of(txn: Transaction) -> str:
    """The bank's transaction reference for this row, or "" when the narration has none."""
    m = _REF_RE.match((txn.description or "").strip())
    return m.group(1) if m else ""


#: Longest gap between a debit and its refund for the pair to read as a cancellation rather than a
#: repayment. Real data: same-day reversals, then a cliff to 46+ days. Two weeks is comfortably
#: inside the gap and still covers a bank taking a few days to reverse a failed transfer.
REVERSAL_WINDOW_DAYS = 14


@dataclass(frozen=True)
class Reversal:
    """One debit cancelled by a matching credit from the same counterparty."""

    counterparty: str
    amount: int                      # minor units, the amount that went out and came back
    out_ref: str                     # content hash of the debit
    back_ref: str                    # content hash of the credit
    out_date: Optional[date]
    back_date: Optional[date]
    days: int
    bank_ref: str = ""               # the shared RRN/UTR, when both legs carry one

    @property
    def same_day(self) -> bool:
        return self.days == 0

    @property
    def confidence(self) -> str:
        """"certain" when the bank's own reference matches on both legs, else "likely"."""
        return "certain" if self.bank_ref else "likely"

    def as_dict(self) -> Dict[str, object]:
        return {"counterparty": self.counterparty, "amount": self.amount,
                "out_ref": self.out_ref, "back_ref": self.back_ref,
                "out_date": self.out_date.isoformat() if self.out_date else None,
                "back_date": self.back_date.isoformat() if self.back_date else None,
                "days": self.days, "same_day": self.same_day,
                "bank_ref": self.bank_ref, "confidence": self.confidence}


@dataclass
class PersonNet:
    """Everything that moved both ways with one counterparty."""

    counterparty: str
    display: str
    paid: int = 0                    # minor units you sent
    received: int = 0                # minor units they sent
    n_paid: int = 0
    n_received: int = 0
    refs: List[str] = field(default_factory=list)

    @property
    def net(self) -> int:
        """Positive = you are out of pocket with this person."""
        return self.paid - self.received

    @property
    def offset(self) -> int:
        """How much cancels out — the part that disappears in a netted view."""
        return min(self.paid, self.received)

    def as_dict(self) -> Dict[str, object]:
        return {"counterparty": self.counterparty, "display": self.display,
                "paid": self.paid, "received": self.received,
                "n_paid": self.n_paid, "n_received": self.n_received,
                "net": self.net, "offset": self.offset, "refs": self.refs}


def find_reversals(txns: Iterable[Transaction], *,
                   window_days: int = REVERSAL_WINDOW_DAYS) -> List[Reversal]:
    """Debit/credit pairs that cancel each other out — same counterparty, same amount, close in time.

    Matching is deliberately strict. A loose rule here silently deletes real spending from the
    totals, which is worse than showing a reversal as two rows: the user can see two rows and reason
    about them, but cannot see money that was quietly removed.

    Each credit is consumed by at most one debit, so three ₹500 debits and one ₹500 credit produce
    exactly one reversal, not three.
    """
    by_key: Dict[str, List[Transaction]] = {}
    for t in txns:
        key = merchant_key(t)
        if not key or len(key) < 3:      # too generic to pair safely
            continue
        by_key.setdefault(key, []).append(t)

    out: List[Reversal] = []
    for key, rows in by_key.items():
        debits = sorted((t for t in rows if t.is_debit and t.txn_date),
                        key=lambda t: t.txn_date)
        credits = sorted((t for t in rows if not t.is_debit and t.txn_date),
                         key=lambda t: t.txn_date)
        if not debits or not credits:
            continue
        claimed: set = set()
        for d in debits:
            d_ref = _ref_of(d)
            # Prefer a bank-reference match over a merely plausible one: scan for a shared RRN first,
            # then fall back to amount+window. Without this ordering a same-amount coincidence
            # earlier in the list could claim the credit that the reference proves belongs elsewhere.
            best: Optional[Tuple[int, int, str]] = None      # (index, gap, bank_ref)
            for i, c in enumerate(credits):
                if i in claimed or c.amount.minor != d.amount.minor:
                    continue
                gap = (c.txn_date - d.txn_date).days
                if gap < 0:                                  # a refund cannot precede its charge
                    continue
                shared = d_ref if (d_ref and _ref_of(c) == d_ref) else ""
                if not shared and gap > window_days:
                    continue
                if best is None or (shared and not best[2]) or (
                        bool(shared) == bool(best[2]) and gap < best[1]):
                    best = (i, gap, shared)
                if shared and gap == 0:
                    break                                    # cannot do better than this
            if best is None:
                continue
            i, gap, shared = best
            claimed.add(i)
            c = credits[i]
            out.append(Reversal(counterparty=key, amount=d.amount.minor,
                                out_ref=d.source_ref, back_ref=c.source_ref,
                                out_date=d.txn_date, back_date=c.txn_date, days=gap,
                                bank_ref=shared))
    out.sort(key=lambda r: -r.amount)
    return out


def reversed_refs(txns: Iterable[Transaction], *,
                  window_days: int = REVERSAL_WINDOW_DAYS) -> Tuple[set, int]:
    """The content hashes on both legs of every reversal, plus the total cancelled.

    Returned as a set so the caller can filter rows in one pass, and as a total so the UI can say
    how much it removed instead of silently shrinking the numbers.
    """
    revs = find_reversals(txns, window_days=window_days)
    refs = set()
    for r in revs:
        refs.add(r.out_ref)
        refs.add(r.back_ref)
    return refs, sum(r.amount for r in revs)


def person_nets(txns: Iterable[Transaction], *, min_offset: int = 0) -> List[PersonNet]:
    """Counterparties money moved BOTH ways with, ranked by how much cancels out.

    Only two-way counterparties are returned: a payee you have only ever paid has nothing to net, so
    listing it would bury the handful of rows where netting actually changes the answer.
    """
    acc: Dict[str, PersonNet] = {}
    for t in txns:
        key = merchant_key(t)
        if not key or len(key) < 3:
            continue
        p = acc.get(key)
        if p is None:
            p = acc[key] = PersonNet(counterparty=key,
                                     display=(t.merchant or t.description or key).strip())
        if t.is_debit:
            p.paid += t.amount.minor
            p.n_paid += 1
        else:
            p.received += t.amount.minor
            p.n_received += 1
        p.refs.append(t.source_ref)

    two_way = [p for p in acc.values()
               if p.n_paid and p.n_received and p.offset >= min_offset]
    two_way.sort(key=lambda p: -p.offset)
    return two_way
