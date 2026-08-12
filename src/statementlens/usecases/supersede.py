"""Statements supersede provisional alert rows.

The whole point of alerts is a dashboard that is current *today*. The whole point of statements is a
record that is *correct*. Both being present means the same swipe can appear twice, so one has to win:

    statement  >  alert          always, for any period a statement covers

Why the statement wins even when the alert is "the same": the statement is the bank's settled record.
An alert may describe an authorisation that never captured, a pre-auth hold (hotels, fuel pumps) that
settles at a different amount, or a transaction later reversed. Its narration is also truncated.

Why period-based and not amount-matching: matching alert↔statement rows pairwise looks appealing but
fails exactly where it matters. A ₹50 pre-auth that settles at ₹1,508 has no matching amount; two
identical ₹50 Swiggy orders on one day are indistinguishable; and a merchant name in an alert
("RAZ*SWIGGY") often differs from the statement's ("Payu*Swiggy Food"). So instead: **once a statement
covers a date range, every provisional row inside that range is dropped.** Coarser, but it cannot
double-count and it cannot silently delete a real settled transaction.

Alerts OUTSIDE any statement's coverage survive — that's the live tail, which is the feature.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from ..domain.models import Transaction


@dataclass(frozen=True)
class Coverage:
    """The inclusive date range a statement is authoritative for, per account."""
    account: str
    start: date
    end: date

    def contains(self, when: Optional[date]) -> bool:
        return when is not None and self.start <= when <= self.end


def coverage_from_transactions(txns: Sequence[Transaction], account: str) -> Optional[Coverage]:
    """The single hull min(date)..max(date) over these transactions.

    Kept for callers that genuinely want one span, but **prefer `coverage_blocks`**: a hull claims
    every gap inside it. Two statements for January and March produce a hull covering February, and
    February's provisional rows then get deleted although no statement covers them.
    """
    dates = [t.txn_date for t in txns if t.txn_date]
    if not dates:
        return None
    return Coverage(account, min(dates), max(dates))


def coverage_blocks(txns: Sequence[Transaction], account: str) -> List[Coverage]:
    """Coverage as one block per CALENDAR MONTH that actually has rows.

    A month with at least one transaction is treated as covered end-to-end — a statement covers its
    whole cycle even on days with no activity, so this is the intended slight over-claim within a
    month. What it will not do is claim a month with NO rows: that is the case that silently deleted
    alert-derived rows, because
      * `min..max` over two non-adjacent statements swallows the months between them, and
      * one carry-forward or late-posted row stretches a single statement's hull backwards by weeks.

    The NEWEST month is clamped to its last settled date instead of the month end. Anything after
    that date is the live tail — spending that happened since the statement closed — and claiming to
    the month end would delete exactly the rows alerts exist to provide.

    Adjacent months merge naturally in `merge_coverages`, so a contiguous run still behaves as one
    range and nothing about the common case changes.
    """
    dates = sorted({t.txn_date for t in txns if t.txn_date})
    if not dates:
        return []
    last = dates[-1]
    months = sorted({(d.year, d.month) for d in dates})
    out: List[Coverage] = []
    for y, m in months:
        end = last if (y, m) == (last.year, last.month) else _month_end(y, m)
        out.append(Coverage(account, date(y, m, 1), end))
    return out


def _month_end(year: int, month: int) -> date:
    if month == 12:
        return date(year, 12, 31)
    return date(year, month + 1, 1) - timedelta(days=1)


def merge_coverages(coverages: Iterable[Coverage]) -> Dict[str, List[Tuple[date, date]]]:
    """Collapse per-account coverage into sorted, merged ranges."""
    by_account: Dict[str, List[Tuple[date, date]]] = {}
    for c in coverages:
        by_account.setdefault(c.account, []).append((c.start, c.end))
    out: Dict[str, List[Tuple[date, date]]] = {}
    for account, ranges in by_account.items():
        ranges.sort()
        merged: List[Tuple[date, date]] = []
        for start, end in ranges:
            # `<= prev_end + 1 day` so ADJOINING ranges join too: consecutive month blocks abut
            # (Jan 31 -> Feb 1) without overlapping, and testing only for overlap left a contiguous
            # run of months as separate ranges.
            if merged and start <= merged[-1][1] + timedelta(days=1):
                merged[-1] = (merged[-1][0], max(merged[-1][1], end))
            else:
                merged.append((start, end))
        out[account] = merged
    return out


def is_covered(when: Optional[date], ranges: Sequence[Tuple[date, date]]) -> bool:
    return when is not None and any(s <= when <= e for s, e in ranges)


@dataclass
class SupersedeResult:
    kept: List[Transaction]
    dropped: List[Transaction]

    @property
    def dropped_minor(self) -> int:
        return sum(t.amount.minor for t in self.dropped)

    def summary(self) -> str:
        if not self.dropped:
            return "no provisional rows superseded"
        return (f"{len(self.dropped)} provisional row(s) superseded by statements "
                f"({self.dropped_minor / 100:,.2f} of alert-derived value replaced)")


def supersede(txns: Sequence[Transaction], *,
              coverage: Optional[Dict[str, List[Tuple[date, date]]]] = None,
              account: str = "") -> SupersedeResult:
    """Drop provisional rows that fall inside a statement-covered period.

    `coverage` may be supplied explicitly; otherwise it is derived from the NON-provisional rows
    present, which is the common case (everything for one account read from the store).
    """
    settled = [t for t in txns if not t.provisional]
    provisional = [t for t in txns if t.provisional]

    if coverage is None:
        # per-month blocks, never the min..max hull: a hull claims gap months and would delete
        # alert rows for periods no statement covers
        coverage = merge_coverages(coverage_blocks(settled, account or ""))

    ranges = coverage.get(account or "", [])
    if not ranges:
        # nothing settled yet -> every alert is still the best information we have
        return SupersedeResult(kept=list(txns), dropped=[])

    kept: List[Transaction] = list(settled)
    dropped: List[Transaction] = []
    for t in provisional:
        (dropped if is_covered(t.txn_date, ranges) else kept).append(t)

    kept.sort(key=lambda t: (t.txn_date or date.min, t.raw_date))
    return SupersedeResult(kept=kept, dropped=dropped)


def live_tail(txns: Sequence[Transaction]) -> List[Transaction]:
    """The provisional rows that survived — i.e. activity newer than the last statement."""
    return [t for t in txns if t.provisional]
