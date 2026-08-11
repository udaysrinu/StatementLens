"""Cash-flow classification and period logic — the CRED-Money feature delta.

Two ideas here change the NUMBERS (not just the pixels), which is why they live in a use-case and
not in the renderer:

1. **Three-way flow.** Money out is not one bucket. CRED splits incoming / investments / spends,
   because a ₹50k SIP is not "spending" — treating it as such makes every spend total a lie.
2. **Self-transfers are excluded.** Moving money between your own accounts is not income and not
   expenditure; counting both legs double-inflates in AND out. CRED shows a banner about this.

Plus the period model: a salary cycle ("cashflow starts from your salary date") beats a calendar
month, because that is the boundary your money actually resets on.

Everything is integer paise and pure — no I/O.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Dict, Iterable, List, Optional, Tuple

from ..domain.models import Transaction

# ---------------------------------------------------------------------------
# Flow buckets
# ---------------------------------------------------------------------------

INCOMING = "incoming"
INVESTMENT = "investment"
SPEND = "spend"
SELF_TRANSFER = "self"

#: Paying your credit-card bill moves money between two accounts you own. On the BANK statement it
#: looks like a debit; on the CARD statement the same money looks like a credit. Counting it as
#: spending on one side and income on the other double-counts it twice over — so it is classified as
#: a self-transfer and excluded from both, exactly like moving cash between your own accounts.
_CARD_BILL_PAYMENT = re.compile(
    r"""(?ix)
      \bpymt\s+rec(?:ei)?v?e?d\b | \bpayment\s+received\b | \bthank\s*you\b
    | \bbppy\s+cc\s+payment\b | \bcc\s+payment\b | \bcredit\s+card\s+payment\b
    | \btele\s+transfer\s+credit\b | \bonline\s+trf\s*-\s*pymt\b
    | \bautopay\b.*\bcard\b | \bneft\s+cr\b.*\bcard\b
    """)

#: Categories that represent moving money into an asset rather than consuming it.
_INVESTMENT_CATEGORIES = {"investments", "investment", "mutual funds", "stocks", "sip"}

#: Merchant fragments that are unambiguously brokers / fund platforms.
_INVESTMENT_MERCHANTS = re.compile(
    r"(?i)\b(zerodha|groww|upstox|smallcase|indianclearing|nse\s*clearing|bse|"
    r"iccl|nsccl|mf\s*utility|mfu|camsonline|kfintech|indmoney|coin|"
    r"sip|mutual\s*fund|elss|nps|ppf)\b"
)


def is_self_transfer(txn: Transaction, own_names: Iterable[str]) -> bool:
    """True when this line just shuffles money between the owner's own accounts.

    Detected by the owner's own name/handle appearing in the narration. Bank narrations for
    self-transfers carry the account holder's name on both legs (e.g. "UPI/GIDIJALA UDAY/..."),
    which is exactly what makes them distinguishable from a payment to someone else.

    Deliberately conservative: a false positive silently erases a real transaction from the
    totals, which is far worse than a false negative.
    """
    hay = f"{txn.merchant} {txn.description}".lower()
    for name in own_names:
        n = (name or "").strip().lower()
        if len(n) >= 4 and n in hay:
            return True
    return False


def is_card_bill_payment(txn: Transaction) -> bool:
    """True when this row is a credit-card bill payment (an internal transfer, not income/spend)."""
    return bool(_CARD_BILL_PAYMENT.search(f"{txn.merchant} {txn.description}"))


def classify_flow(txn: Transaction, own_names: Iterable[str] = ()) -> str:
    """Bucket one transaction into incoming / investment / spend / self."""
    if own_names and is_self_transfer(txn, own_names):
        return SELF_TRANSFER
    # checked before the debit/credit split, because the same payment appears as a credit on the card
    # statement and a debit on the bank statement — both legs must land in the same bucket
    if is_card_bill_payment(txn):
        return SELF_TRANSFER
    if not txn.is_debit:
        return INCOMING
    cat = (txn.category or "").strip().lower()
    if cat in _INVESTMENT_CATEGORIES or _INVESTMENT_MERCHANTS.search(
            f"{txn.merchant} {txn.description}"):
        return INVESTMENT
    return SPEND


@dataclass(frozen=True)
class CashFlow:
    """Honest three-way flow for a period. All amounts are positive integer paise."""
    incoming: int = 0
    investments: int = 0
    spends: int = 0
    self_transfers: int = 0        # reported, never folded into in/out
    self_transfer_count: int = 0

    @property
    def net(self) -> int:
        """What actually stayed. Never an invented 'money left to spend'."""
        return self.incoming - self.investments - self.spends


def cash_flow(txns: Iterable[Transaction], own_names: Iterable[str] = ()) -> CashFlow:
    """Aggregate a three-way cash flow, excluding self-transfers from both sides."""
    inc = inv = spd = slf = 0
    slf_n = 0
    for t in txns:
        bucket = classify_flow(t, own_names)
        minor = t.amount.minor
        if bucket == INCOMING:
            inc += minor
        elif bucket == INVESTMENT:
            inv += minor
        elif bucket == SPEND:
            spd += minor
        else:
            slf += minor
            slf_n += 1
    return CashFlow(inc, inv, spd, slf, slf_n)


def incoming_breakdown(txns: Iterable[Transaction], own_names: Iterable[str] = (),
                       limit: int = 6) -> List[Dict[str, object]]:
    """Where money came FROM, descending — the mirror of category spend.

    Our engine only ever aggregated debits; credits were a single lump. CRED breaks incoming into
    salary / people / loans with percentages, which is what makes "am I actually earning more?"
    answerable.
    """
    by_src: Dict[str, int] = defaultdict(int)
    counts: Dict[str, int] = defaultdict(int)
    total = 0
    for t in txns:
        if classify_flow(t, own_names) != INCOMING:
            continue
        # narration-based income rules take precedence: a spend categorizer has no notion of
        # "salary" vs "refund", so trusting its label here mislabels most credits
        src = _guess_income_source(t) or t.category or "Other income"
        by_src[src] += t.amount.minor
        counts[src] += 1
        total += t.amount.minor
    out = [{"source": s, "amount": a, "count": counts[s],
            "share": (a / total) if total else 0.0}
           for s, a in by_src.items()]
    out.sort(key=lambda r: -r["amount"])
    return out[:limit]


_SALARY_RE = re.compile(r"(?i)(\bsalary\b|\bsal\s+for\b|\bpayroll\b|\bneft.*\bsal\b)")
_REFUND_RE = re.compile(r"(?i)\b(refund|reversal|rev\b|chargeback)\b")
#: Card rewards are earnings of a sort but not a refund of anything — on a card statement they are
#: often the single most frequent credit, so lumping them into "Refunds" hides both.
_CASHBACK_RE = re.compile(r"(?i)(cashback|cash\s?back|reward\s?point|statement\s+credit|\bmilestone\b)")
_INTEREST_RE = re.compile(r"(?i)\b(int\.?\s*pd|interest|int\s*cr)\b")


def _guess_income_source(txn: Transaction) -> Optional[str]:
    """Classify a credit by its narration. None when no rule fires, so the caller can fall back."""
    hay = f"{txn.merchant} {txn.description}"
    if _SALARY_RE.search(hay):
        return "Salary"
    if _CASHBACK_RE.search(hay):
        return "Cashback & rewards"
    if _REFUND_RE.search(hay):
        return "Refunds"
    if _INTEREST_RE.search(hay):
        return "Interest"
    if _UPI_PERSON_RE.search(hay):
        return "People"
    return None


#: A credit arriving over UPI/IMPS/NEFT from a named individual — i.e. someone paying you back.
_UPI_PERSON_RE = re.compile(r"(?i)\b(upi|imps|neft|rtgs)\b")


# ---------------------------------------------------------------------------
# Salary-cycle periods
# ---------------------------------------------------------------------------

def detect_salary_day(txns: Iterable[Transaction]) -> Optional[int]:
    """Infer the day-of-month salary lands, from the modal day of salary-like credits.

    Requires 3+ observations so one stray credit can't define your financial month.
    """
    days: Dict[int, int] = defaultdict(int)
    n = 0
    for t in txns:
        if t.is_debit or not t.txn_date:
            continue
        if _SALARY_RE.search(f"{t.merchant} {t.description}"):
            days[t.txn_date.day] += 1
            n += 1
    if n < 3 or not days:
        return None
    return max(days.items(), key=lambda kv: (kv[1], -kv[0]))[0]


def salary_cycle(anchor: date, salary_day: int) -> Tuple[date, date]:
    """The salary-cycle window containing `anchor`, inclusive of both ends.

    A cycle runs from salary_day of one month to the day before salary_day of the next. Days past
    the end of a short month clamp to that month's last day (salary_day=31 in February).
    """
    if not 1 <= salary_day <= 31:
        raise ValueError(f"salary_day out of range: {salary_day}")

    def clamped(y: int, m: int) -> date:
        if m > 12:
            y, m = y + 1, m - 12
        elif m < 1:
            y, m = y - 1, m + 12
        d = salary_day
        while d > 1:
            try:
                return date(y, m, d)
            except ValueError:
                d -= 1
        return date(y, m, 1)

    start = clamped(anchor.year, anchor.month)
    if anchor < start:                      # still in the previous cycle
        start = clamped(anchor.year, anchor.month - 1)
        end = clamped(anchor.year, anchor.month) - timedelta(days=1)
    else:
        end = clamped(anchor.year, anchor.month + 1) - timedelta(days=1)
    return start, end


def monthly_series(txns: Iterable[Transaction], own_names: Iterable[str] = (),
                   months: int = 6) -> List[Dict[str, object]]:
    """Per-month spend totals + the average, for the bar chart with an AVG reference line.

    The average is over months that actually have data — dividing by a fixed 6 when you only hold
    3 months of statements would understate it badly.
    """
    by_month: Dict[str, int] = defaultdict(int)
    for t in txns:
        if classify_flow(t, own_names) == SPEND and t.month:
            by_month[t.month] += t.amount.minor
    keys = sorted(by_month)[-months:]
    vals = [by_month[k] for k in keys]
    avg = sum(vals) // len(vals) if vals else 0
    peak = max(vals) if vals else 0
    return [{"month": k, "amount": by_month[k], "avg": avg,
             "share_of_peak": (by_month[k] / peak) if peak else 0.0} for k in keys]


def recurring_payments(txns: Iterable[Transaction], own_names: Iterable[str] = (),
                       min_months: int = 3, *, as_of: Optional[date] = None,
                       stale_after_days: int = 75) -> List[Dict[str, object]]:
    """Detect recurring payees with their usual day-of-month and next expected date.

    CRED's "usually paid by: 3RD" is the useful half of recurring detection — knowing a payment
    repeats is far less actionable than knowing when it lands next.

    A payee last seen long ago is marked `active=False` and gets no next-expected date: predicting
    a future date for a subscription that stopped 18 months ago is worse than saying nothing.
    """
    # merchant keys are case-insensitive: "ZERODHA" and "Zerodha" are one payee, and splitting them
    # both halves the detected cadence and shows the user duplicate rows
    by_merchant: Dict[str, List[Transaction]] = defaultdict(list)
    for t in txns:
        if t.merchant and t.txn_date and classify_flow(t, own_names) in (SPEND, INVESTMENT):
            by_merchant[t.merchant.strip().lower()].append(t)

    latest = max((t.txn_date for t in txns if t.txn_date), default=None)
    as_of = as_of or latest

    out: List[Dict[str, object]] = []
    for _, items in by_merchant.items():
        months = {t.month for t in items}
        if len(months) < min_months:
            continue
        amounts = sorted(t.amount.minor for t in items)
        median = amounts[len(amounts) // 2] if len(amounts) % 2 else \
            (amounts[len(amounts) // 2 - 1] + amounts[len(amounts) // 2]) // 2
        days: Dict[int, int] = defaultdict(int)
        for t in items:
            days[t.txn_date.day] += 1
        usual_day = max(days.items(), key=lambda kv: (kv[1], -kv[0]))[0]
        last = max(t.txn_date for t in items)
        active = as_of is None or (as_of - last).days <= stale_after_days
        out.append({
            # display the most common spelling rather than the lowercased key
            "merchant": max(set(t.merchant for t in items),
                            key=lambda m: sum(1 for t in items if t.merchant == m)),
            "months": len(months),
            "median": median,
            "total": sum(t.amount.minor for t in items),
            "usual_day": usual_day,
            "last_seen": last.isoformat(),
            "active": active,
            "next_expected": _next_on_day(last, usual_day).isoformat() if active else None,
        })
    # active payees first, then by value — a live ₹3k subscription matters more than a dead ₹90k one
    out.sort(key=lambda r: (not r["active"], -r["total"]))
    return out


def _next_on_day(after: date, day: int) -> date:
    y, m = (after.year + 1, 1) if after.month == 12 else (after.year, after.month + 1)
    d = min(day, 28) if day > 28 else day
    while d > 1:
        try:
            return date(y, m, d)
        except ValueError:
            d -= 1
    return date(y, m, 1)


def per_month_average(total: int, months: int) -> int:
    """`AVG PER MONTH ₹2.36L` — the sub-line CRED puts under every total."""
    return total // months if months > 0 else 0
