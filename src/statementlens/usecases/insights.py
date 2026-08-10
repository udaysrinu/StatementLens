"""Insight engine — the product's crown jewel: surface the ONE thing you'd otherwise miss.

Each insight is a pure DETECTOR function: (context) -> Optional[Insight]. The engine runs all
detectors, ranks survivors by money-at-stake / urgency, caps the list, and always returns a
positive terminal card if nothing qualifies (no dead ends). Add an insight by writing another
detector and registering it — Open/Closed, no edits to the engine.

Copy follows the researched CRED voice: calm, confident, second-person, number-forward, lowercase,
never alarmist. Detectors are offline and deterministic (integer-paise Money throughout).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from enum import IntEnum
from typing import Callable, List, Optional

from ..domain.models import Direction, Transaction
from ..domain.money import Money


class Severity(IntEnum):
    POSITIVE = 0
    INFO = 1
    NOTICE = 2
    ALERT = 3


@dataclass(frozen=True)
class Insight:
    key: str
    severity: Severity
    icon: str
    title: str
    copy: str
    at_stake: int = 0  # minor units, for ranking
    cta: str = ""


@dataclass
class InsightContext:
    """Everything a detector might need — computed once, passed to all detectors."""
    txns: List[Transaction]
    currency: str = "INR"
    today: Optional[date] = None

    def debits(self) -> List[Transaction]:
        return [t for t in self.txns if t.is_debit]

    def credits(self) -> List[Transaction]:
        return [t for t in self.txns if not t.is_debit]


Detector = Callable[[InsightContext], Optional[Insight]]
_DETECTORS: List[Detector] = []


def detector(fn: Detector) -> Detector:
    _DETECTORS.append(fn)
    return fn


def _money(minor: int, cur: str) -> str:
    return Money(minor, cur).format()


def _months_span(txns: List[Transaction]) -> int:
    ms = {t.month for t in txns if t.month}
    return max(1, len(ms))


# --- detectors -------------------------------------------------------------

# categories that are transfers/moves, not discretionary "spending"
_NON_DISCRETIONARY = {"transfers (people)", "transfers (in)", "investments", "card bills",
                      "rent", "cash/atm", "salary/income", "other", "other income"}


@detector
def duplicate_charge(ctx: InsightContext) -> Optional[Insight]:
    """Same merchant + near-identical amount on DIFFERENT days within 72h — for real merchant spends.

    Skips transfers/investments/card-bills (people legitimately send a payee twice, and back-to-back
    investment buys are intentional), and requires the two dates to differ (same-day split payments
    to one merchant are normal), so this only flags a genuine looks-wrong double charge.
    """
    by_merchant = defaultdict(list)
    for t in ctx.debits():
        c = (t.category or "").lower()
        if t.merchant and t.txn_date and c not in _NON_DISCRETIONARY:
            by_merchant[t.merchant.lower()].append(t)
    best = None
    for _, items in by_merchant.items():
        items.sort(key=lambda t: t.txn_date)
        for i in range(len(items) - 1):
            a, b = items[i], items[i + 1]
            days = (b.txn_date - a.txn_date).days
            if 1 <= days <= 3 and abs(a.amount.minor - b.amount.minor) <= max(100, a.amount.minor // 200):
                if best is None or a.amount.minor > best[0].amount.minor:
                    best = (a, b)
    if not best:
        return None
    a, b = best
    return Insight("duplicate", Severity.ALERT, "copy",
                   "possible double charge",
                   f"looks like {a.merchant} was charged twice — "
                   f"{a.amount.format()} on {a.txn_date:%b %d} and again on {b.txn_date:%b %d}. worth a check.",
                   at_stake=a.amount.minor)


@detector
def hidden_fees(ctx: InsightContext) -> Optional[Insight]:
    total = sum((t.amount.minor for t in ctx.debits()
                 if (t.category or "").lower().startswith("fee")), 0)
    if total <= 0:
        return None
    return Insight("fees", Severity.NOTICE, "receipt",
                   "you paid fees this period",
                   f"you paid {_money(total, ctx.currency)} in fees & charges — "
                   "small amounts that add up. most banks will waive some if you ask.",
                   at_stake=total)


def spend_spike(ctx: InsightContext) -> Optional[Insight]:
    """A discretionary category's latest FULL month > 125% of its trailing 3-6 month average.

    Requires >=3 distinct months of history so it never fires on a single statement period, and
    ignores transfers/investments/rent (moves, not discretionary spend).
    """
    months = sorted({t.month for t in ctx.debits() if t.month})
    if len(months) < 4:  # need latest + >=3 baseline months
        return None
    latest = months[-1]
    baseline = set(months[-7:-1])  # trailing up to 6 months before latest
    if len(baseline) < 3:
        return None
    cat_latest = defaultdict(int)
    cat_base_total, cat_base_months = defaultdict(int), defaultdict(set)
    for t in ctx.debits():
        c = (t.category or "Other")
        if c.lower() in _NON_DISCRETIONARY:
            continue
        if t.month == latest:
            cat_latest[c] += t.amount.minor
        elif t.month in baseline:
            cat_base_total[c] += t.amount.minor
            cat_base_months[c].add(t.month)
    best = None
    for c, cur in cat_latest.items():
        bm = len(cat_base_months.get(c, ()))
        if bm < 3:  # need a stable baseline for THIS category
            continue
        avg = cat_base_total[c] / bm
        if avg > 0 and cur > avg * 1.25:
            pct = round((cur / avg - 1) * 100)
            if best is None or (cur - avg) > best[1]:
                best = (c, cur - avg, cur, pct)
    if not best:
        return None
    c, _, cur, pct = best
    return Insight("spike", Severity.NOTICE, "trend",
                   f"{c.lower()} is up",
                   f"you spent {_money(cur, ctx.currency)} on {c.lower()} recently — "
                   f"{pct}% more than your usual.",
                   at_stake=cur)


spend_spike = detector(spend_spike)


@detector
def new_recurring(ctx: InsightContext) -> Optional[Insight]:
    """Same merchant at monthly cadence over >=3 months."""
    by_m = defaultdict(lambda: {"months": set(), "amts": []})
    for t in ctx.debits():
        if t.merchant and t.month:
            by_m[t.merchant]["months"].add(t.month)
            by_m[t.merchant]["amts"].append(t.amount.minor)
    cand = [(m, len(d["months"]), sorted(d["amts"])[len(d["amts"]) // 2])
            for m, d in by_m.items() if len(d["months"]) >= 3]
    if not cand:
        return None
    cand.sort(key=lambda x: -x[1])
    m, months, med = cand[0]
    return Insight("recurring", Severity.INFO, "repeat",
                   "a recurring payment",
                   f"{m} looks like a monthly payment — about {_money(med, ctx.currency)} each, "
                   f"seen across {months} months.",
                   at_stake=med)


@detector
def top_payee(ctx: InsightContext) -> Optional[Insight]:
    tot = defaultdict(int)
    cnt = defaultdict(int)
    for t in ctx.debits():
        if t.merchant:
            tot[t.merchant] += t.amount.minor
            cnt[t.merchant] += 1
    if not tot:
        return None
    m = max(tot, key=tot.get)
    return Insight("top_payee", Severity.INFO, "crown",
                   "your biggest payee",
                   f"{m} was your biggest payee — {_money(tot[m], ctx.currency)} across {cnt[m]} payments.",
                   at_stake=tot[m])


@detector
def forgotten_credit(ctx: InsightContext) -> Optional[Insight]:
    refunds = [t for t in ctx.credits()
               if any(k in (t.description + " " + (t.category or "")).lower()
                      for k in ("refund", "reversal", "cashback"))]
    if not refunds:
        return None
    big = max(refunds, key=lambda t: t.amount.minor)
    return Insight("credit", Severity.POSITIVE, "gift",
                   "money came back to you",
                   f"{big.amount.format()} landed as a refund"
                   + (f" from {big.merchant}" if big.merchant else "")
                   + (f" on {big.txn_date:%b %d}" if big.txn_date else "") + " — easy to miss.",
                   at_stake=big.amount.minor)


def generate(ctx: InsightContext, limit: int = 4) -> List[Insight]:
    """Run all detectors, rank by (severity desc, money-at-stake desc), cap, and never dead-end."""
    found = [ins for ins in (d(ctx) for d in _DETECTORS) if ins is not None]
    found.sort(key=lambda i: (-int(i.severity), -i.at_stake))
    if not found:
        return [Insight("caught_up", Severity.POSITIVE, "check", "all caught up",
                        "nothing needs your attention right now.")]
    return found[:limit]
