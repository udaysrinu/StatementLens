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
from dataclasses import dataclass, field
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
#:
#: INDmoney (legal entity FINZOOM Insurance Brokers, VPA `indmoney*`) is deliberately NOT here. It is
#: a RAIL, not an activity: the same handle carries investment orders AND credit-card bill payments,
#: and this user confirmed they only ever use it to pay card bills. Listing it as a broker booked
#: ₹2.71L of bill payments as investments — money that had already been counted as card charges, so it
#: was double-counted across the two accounts. A platform that does several things cannot be
#: classified by its name alone; see _CARD_RAIL below.
_INVESTMENT_MERCHANTS = re.compile(
    r"(?i)\b(zerodha|groww|upstox|smallcase|indianclearing|nse\s*clearing|bse|"
    r"iccl|nsccl|mf\s*utility|mfu|camsonline|kfintech|coin|"
    r"sip|mutual\s*fund|elss|nps|ppf)\b"
)

#: Third-party rails used to PAY a credit-card bill from a bank account. The bank side of such a
#: payment names the rail, not the card, so nothing in the narration says "card" — which is why these
#: need naming explicitly. Both legs must land in SELF_TRANSFER or the money counts twice: once as the
#: bank debit and again as the card charges it settled.
_CARD_RAIL = re.compile(r"(?i)\b(finzoom|indmoney|cred(?:club)?|paytm\s*cc|mobikwik\s*cc)\b")


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
    hay = f"{txn.merchant} {txn.description}"
    # a debit to a card-payment rail is the bank side of a bill payment, even though the narration
    # never mentions a card — it names the rail (INDmoney, CRED) instead
    if txn.is_debit and _CARD_RAIL.search(hay):
        return True
    return bool(_CARD_BILL_PAYMENT.search(hay))


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


def looks_like_card(txns: Sequence[Transaction], account: str = "") -> bool:
    """True when these transactions come from a CREDIT CARD rather than a bank account.

    A running balance on ANY row rules a card out — bank statements carry one, card statements do not.
    Beyond that, any ONE of these confirms a card:
      * a bill-payment row ("PYMT RECD - THANK YOU"), which only appears on a card statement;
      * a finance-charge / IGST / late-fee row, which banks do not levy this way;
      * a masked card number in the account label (e.g. "ICICI ••4007").

    Requiring a bill-payment row was wrong: a card paid by autopay from another bank shows no payment
    line on its OWN statement, so two real ICICI cards were being presented as bank accounts — with
    income/investments/net headings that mean nothing for a card. That only became visible once
    accounts were split; while everything was merged, one card's payment rows covered for the others.

    This matters because the honest way to present a card is different: a card has charges, payments
    and refunds — not income, investments and a net. "Net" on a card is arithmetically computable and
    semantically meaningless, since the spending IS the balance owed.
    """
    rows = list(txns)
    if not rows:
        return False
    if any(t.balance is not None for t in rows):
        return False
    if _CARD_LABEL.search(account or ""):
        return True
    return any(is_card_bill_payment(t) or _CARD_FEE_RE.search(f"{t.merchant} {t.description}")
               for t in rows)


#: A masked card tail in an account label, as `account_id.account_label` produces for cards.
_CARD_LABEL = re.compile(r"••\s*\d{2,4}\s*$")


@dataclass(frozen=True)
class CardFlow:
    """A credit card's honest summary. All amounts are positive integer paise."""
    charges: int = 0          # what you spent on the card
    payments: int = 0         # what you paid the card from a bank account
    refunds: int = 0          # merchant refunds and reversals
    rewards: int = 0          # cashback and statement credits
    fees: int = 0             # finance charges, GST on them, late fees

    @property
    def net_new_debt(self) -> int:
        """Charges and fees minus what you paid off — the figure that actually moves your balance."""
        return self.charges + self.fees - self.payments - self.refunds - self.rewards


#: Narrations a card issuer uses for "you paid your bill". Several appear for the SAME payment: HDFC
#: prints a customer-facing line ("ONLINE TRF - PYMT RECD - THANK YOU") alongside the payment rail's
#: own entry ("BPPY CC PAYMENT ..."), and sometimes a third ("TELE TRANSFER CREDIT").
_PAYMENT_LIKE = re.compile(
    r"(?i)pymt\s*recd|payment\s*received|cc\s*payment|\bbppy\b|tele\s*transfer\s*credit|"
    r"online\s*trf|\bbbps\b|autopay|thank\s*you")


def dedupe_bill_payments(txns: Iterable[Transaction]) -> List[Transaction]:
    """Collapse the same bill payment printed under several narrations.

    HDFC lists one payment two or three times — the customer-facing line, the rail's entry, and
    occasionally a transfer-credit line. Content-hash dedup cannot catch it: the narrations differ, so
    the hashes differ, and every leg was counted. On the real card this inflated `payments` by
    ₹4,20,230 across 9 clusters (₹8.33L reported against ~₹4.1L actually paid).

    The rule is deliberately narrow: same date, same amount, and EVERY row in the group reads as a
    payment. Ordinary same-day same-amount duplicates are left alone — two ₹2 charges at one merchant
    on one day are usually real, and silently deleting a charge is worse than showing two.

    Returns a new list; the first row of each group survives so its narration stays inspectable.
    """
    rows = list(txns)
    groups: Dict[tuple, List[Transaction]] = defaultdict(list)
    for t in rows:
        if t.is_debit or t.txn_date is None:
            continue
        groups[(t.txn_date, t.amount.minor)].append(t)

    drop: set = set()
    for members in groups.values():
        if len(members) < 2:
            continue
        if all(_PAYMENT_LIKE.search(f"{m.merchant} {m.description}") for m in members):
            for extra in members[1:]:
                drop.add(id(extra))
    return [t for t in rows if id(t) not in drop]


@dataclass
class BillCycle:
    """One bill payment and the charges it settled.

    A bank statement shows a card payment as a single opaque line — "₹47,000 to HDFC". That figure is
    unanalysable on its own: it is not a purchase, it has no merchant and no category. What it really
    is, is the sum of everything charged to the card in the preceding cycle. This pairs the two so the
    lump can be opened up.
    """
    paid_on: Optional[date]
    paid: int                              # minor units actually paid
    charges: int = 0                       # minor units charged in the cycle it settled
    fees: int = 0
    refunds: int = 0
    rows: List[Transaction] = field(default_factory=list)
    from_date: Optional[date] = None
    to_date: Optional[date] = None

    @property
    def count(self) -> int:
        return len(self.rows)

    @property
    def unpaid(self) -> int:
        """Charged but not covered by this payment — a partial payment leaves a balance."""
        return self.charges + self.fees - self.refunds - self.paid

    def as_dict(self) -> Dict[str, object]:
        return {"paid_on": self.paid_on.isoformat() if self.paid_on else None,
                "paid": self.paid, "charges": self.charges, "fees": self.fees,
                "refunds": self.refunds, "count": self.count, "unpaid": self.unpaid,
                "from_date": self.from_date.isoformat() if self.from_date else None,
                "to_date": self.to_date.isoformat() if self.to_date else None,
                "refs": [t.source_ref for t in self.rows]}


def bill_cycles(txns: Iterable[Transaction]) -> List[BillCycle]:
    """Group a card's charges into the billing cycles its payments settled, newest first.

    Cycles are derived from PAYMENT DATES rather than from the statement's own period, because
    `period_hint` is unreliable — it currently holds filename fragments for this issuer. Payment dates
    are directly observable and land on a clean monthly cadence.

    Two things the naive version got wrong, both visible in real data:
      * charges predating the FIRST payment were all swept into cycle one (163 rows in one bucket).
        Those were never settled by a payment we hold, so they belong to an explicit opening bucket.
      * two payments on the same date each claimed the whole cycle, double-attributing every charge.
        Same-date payments are merged into one settlement event, which is what they are.
    """
    rows = dedupe_bill_payments(txns)
    pay_by_date: Dict[date, int] = defaultdict(int)
    for t in rows:
        if is_card_bill_payment(t) and t.txn_date:
            pay_by_date[t.txn_date] += t.amount.minor
    dates = sorted(pay_by_date)

    cycles = [BillCycle(paid_on=d, paid=pay_by_date[d]) for d in dates]
    # an explicit bucket for charges older than the first payment, so nothing is silently attributed
    opening = BillCycle(paid_on=None, paid=0)

    for t in rows:
        if not t.txn_date or is_card_bill_payment(t):
            continue
        idx = next((i for i, d in enumerate(dates) if d >= t.txn_date), None)
        target = cycles[idx] if idx is not None else None
        if target is None:
            continue                       # charged after the last payment: not yet settled
        if idx == 0 and dates and t.txn_date < dates[0] - timedelta(days=45):
            target = opening               # far older than the first bill we hold
        hay = f"{t.merchant} {t.description}"
        if not t.is_debit:
            target.refunds += t.amount.minor
        elif _CARD_FEE_RE.search(hay):
            target.fees += t.amount.minor
        else:
            target.charges += t.amount.minor
        target.rows.append(t)

    for c in cycles + [opening]:
        dated = [r.txn_date for r in c.rows if r.txn_date]
        if dated:
            c.from_date, c.to_date = min(dated), max(dated)

    out = [c for c in cycles if c.rows or c.paid]
    if opening.rows:
        out.append(opening)
    out.sort(key=lambda c: (c.paid_on is None, c.paid_on or date.min), reverse=True)
    return out


def card_flow(txns: Iterable[Transaction]) -> CardFlow:
    """Summarize a credit card in its own terms rather than a bank account's."""
    charges = payments = refunds = rewards = fees = 0
    for t in dedupe_bill_payments(txns):
        hay = f"{t.merchant} {t.description}"
        if is_card_bill_payment(t):
            payments += t.amount.minor
        elif not t.is_debit:
            if _CASHBACK_RE.search(hay):
                rewards += t.amount.minor
            else:
                refunds += t.amount.minor
        elif _CARD_FEE_RE.search(hay):
            fees += t.amount.minor
        else:
            charges += t.amount.minor
    return CardFlow(charges, payments, refunds, rewards, fees)


#: Card-issued costs rather than purchases — worth separating because they are avoidable.
_CARD_FEE_RE = re.compile(
    r"(?i)finance\s+charges?|\bigst\b|\bgst\b|late\s+payment|surcharge|annual\s+fee|"
    r"joining\s+fee|over\s?limit|interest\s+levied|cash\s+advance\s+fee")


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
        src = income_source(t)
        by_src[src] += t.amount.minor
        counts[src] += 1
        total += t.amount.minor
    out = [{"source": s, "amount": a, "count": counts[s],
            "share": (a / total) if total else 0.0}
           for s, a in by_src.items()]
    out.sort(key=lambda r: -r["amount"])
    if len(out) <= limit:
        return out
    # Fold the tail into an explicit "Other" row rather than dropping it. Truncating silently leaves
    # a breakdown that LOOKS complete but doesn't add up to the incoming total — the reader has no way
    # to know money is missing. An honest remainder row costs one line and keeps the sum exact.
    head, tail = out[:limit - 1], out[limit - 1:]
    head.append({"source": f"Other ({len(tail)} sources)",
                 "amount": sum(r["amount"] for r in tail),
                 "count": sum(r["count"] for r in tail),
                 "share": sum(r["share"] for r in tail)})
    return head


_SALARY_RE = re.compile(r"(?i)(\bsalary\b|\bsal\s+for\b|\bpayroll\b|\bneft.*\bsal\b)")
_REFUND_RE = re.compile(r"(?i)\b(refund|reversal|rev\b|chargeback)\b")
#: Card rewards are earnings of a sort but not a refund of anything — on a card statement they are
#: often the single most frequent credit, so lumping them into "Refunds" hides both.
_CASHBACK_RE = re.compile(r"(?i)(cashback|cash\s?back|reward\s?point|statement\s+credit|\bmilestone\b)")
_INTEREST_RE = re.compile(r"(?i)\b(int\.?\s*pd|interest|int\s*cr)\b")


def income_source(txn: Transaction) -> str:
    """The income-source label for one credit — the resolved answer, never None.

    Narration rules take precedence over the tag: a spend categorizer has no notion of "salary" vs
    "refund", so trusting its label here mislabels most credits. Public because the renderer stamps
    this onto every credit row and must arrive at the same label the summary does — two independent
    implementations of "what kind of income is this" would drift apart.
    """
    guess = _guess_income_source(txn)
    if guess:
        return guess
    # "untagged" is the SPEND categorizer admitting it has no rule; surfacing it as an income source
    # reads as a real category next to Salary and People when it means the opposite.
    tag = (txn.category or "").strip()
    return tag if tag and tag.lower() not in ("untagged", "other") else "Other income"


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
    all_keys = sorted(by_month)
    keys = all_keys[-months:]
    vals = [by_month[k] for k in keys]
    avg = sum(vals) // len(vals) if vals else 0
    peak = max(vals) if vals else 0
    # `truncated` tells the caller the chart is a WINDOW, not the whole history — otherwise a 12-month
    # chart over 7 years of statements reads as "this is everything", and its average silently means
    # "average of the last 12 months" while sitting next to an all-time hero number.
    truncated = len(all_keys) - len(keys)
    return [{"month": k, "amount": by_month[k], "avg": avg,
             "months_shown": len(keys), "months_hidden": truncated,
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
    # No pre-clamp to 28: the loop below already backs off to the real month length, so clamping
    # first predicted the 28th for every 29/30/31 payee even in months that have those days.
    d = day
    while d > 1:
        try:
            return date(y, m, d)
        except ValueError:
            d -= 1
    return date(y, m, 1)


def per_month_average(total: int, months: int) -> int:
    """`AVG PER MONTH ₹2.36L` — the sub-line CRED puts under every total."""
    return total // months if months > 0 else 0
