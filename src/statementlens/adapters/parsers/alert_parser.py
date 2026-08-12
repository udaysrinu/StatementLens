"""Parse bank transaction-ALERT emails into provisional transactions.

Alerts arrive within seconds of a swipe, so they keep the dashboard live between monthly statements.
They are also lossy and chatty, which shapes the whole design here:

* **Provisional, never authoritative.** An alert can be for a pending authorisation that later drops
  off, and it lacks the statement's canonical narration. Alert-derived rows are marked provisional so
  the month-end statement supersedes them instead of double-counting.
* **Rejecting non-transactions matters more than parsing.** Banks send reward-point summaries,
  standing-instruction *reminders*, OTPs and statement notices from the same address, all containing
  a rupee amount and the word "debited". Booking those as spending is worse than missing a real
  transaction, so anything not clearly a completed movement of money is dropped.

Patterns below were written against real emails from HDFC InstaAlerts, SBI CBS alerts and ICICI
cards; each has a test with the actual wording.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

from ...domain.models import Direction

# --------------------------------------------------------------------------
# Rejection rules — checked FIRST, because a false positive invents spending
# --------------------------------------------------------------------------

# Rejection is split into two scopes, because getting this wrong costs real money in both
# directions: too eager and a genuine transaction vanishes; too lax and marketing copy becomes
# spending. A footer mentioning "OTP" once rejected a real ₹97,000 transfer.

#: Checked against the WHOLE email. These describe a document or a future event, so their presence
#: anywhere means the message as a whole is not a completed transaction.
_NEVER_A_TXN = re.compile(r"""(?ix)
      \breward\s*point | \bpoints?\s+worth | \breward[sz]\b            # loyalty summaries
    | \bis\s+due\s+on\b | \bupcoming\s+payment | \bwill\s+be\s+debited # future / reminder
    | \bdue\s+date\b | \bminimum\s+amount\s+due | \btotal\s+amount\s+due
    | \bstatement\s+is\s+ready | \be-?account\s+statement\b | \bstatement\s+for\s+your\b
    | \bone[\s-]time\s+password
    | \bbeneficiary\s+addition\b
    | \bcredit\s+limit\s+(?:is|has) | \bavailable\s+limit\s+is\b
""")

#: Checked only in the SENTENCE around the amount. These are qualifiers on *this* transaction, so
#: they must be adjacent to it — the same words in a footer or a help link mean nothing.
_QUALIFIED_OUT = re.compile(r"""(?ix)
      \bdeclined\b | \bunsuccessful\b | \bfailed\b | \bnot\s+successful\b
    | \bhas\s+been\s+reversed\b | \bin\s+progress\b
""")

#: Widest window considered when isolating the amount's sentence.
_CONTEXT_CHARS = 220

_AMOUNT = r"(?:Rs\.?|INR|₹)\s*(?P<amt>[\d,]+(?:\.\d{1,2})?)"

# HDFC InstaAlerts:
#   "Rs. 465.00 has been debited from your HDFC Bank Credit Card ending 1234
#    towards SWIGGY PVT LTD FOOD2 on 09 Aug, 2026 at 13:22:07"
_HDFC = re.compile(
    _AMOUNT + r"\s+has\s+been\s+(?P<dir>debited|credited)\s+(?:from|to)\s+your\s+"
    r"(?P<acct>.{0,60}?)(?:ending\s+(?P<last4>\d{4}))?\s*"
    r"towards\s+(?P<merchant>.+?)\s+on\s+(?P<day>\d{1,2})\s+(?P<mon>[A-Za-z]{3,9}),?\s+(?P<year>\d{4})",
    re.IGNORECASE | re.DOTALL)

# SBI CBS alerts:
#   "Your AC XXXXX000000 Debited INR 59.00 on 07/07/26 -ACH CHARGES. Avl Bal INR 1,00,000.00."
_SBI = re.compile(
    r"your\s+A/?C\s*(?P<acct>X*\d{3,})\s+(?P<dir>debited|credited)\s+" + _AMOUNT +
    r"\s+on\s+(?P<d>\d{1,2})[/-](?P<m>\d{1,2})[/-](?P<y>\d{2,4})"
    r"\s*[-–]?\s*(?P<merchant>[^.]{0,80})?",
    re.IGNORECASE | re.DOTALL)

# HDFC's other credit-card wording (used interchangeably with the "towards" form above):
#   "Credit Card ending in 1234 .You made a transaction of Rs. 1508.00 at SOME MERCHANT
#    on 11-07-2026 20:36:23 . Authorization code: 053966"
_HDFC_TXN_AT = re.compile(
    r"(?:ending\s+in\s+(?P<last4>\d{4}).{0,20}?)?you\s+made\s+a\s+transaction\s+of\s+" + _AMOUNT +
    r"\s+at\s+(?P<merchant>.+?)\s+on\s+(?P<d>\d{1,2})[/-](?P<m>\d{1,2})[/-](?P<y>\d{2,4})",
    re.IGNORECASE | re.DOTALL)

# SBI's reference-number form:
#   "Your A/C XXXXX000000 has credit for C0000000000000000000000 of Rs 460.00 on 13/07/26"
_SBI_HAS_FOR = re.compile(
    r"your\s+A/?C\s*(?P<acct>X*\d{3,})\s+has\s+(?P<dir>credit|debit)\s+for\s+"
    r"(?P<merchant>\S+)\s+of\s+" + _AMOUNT +
    r"\s+on\s+(?P<d>\d{1,2})[/-](?P<m>\d{1,2})[/-](?P<y>\d{2,4})",
    re.IGNORECASE | re.DOTALL)

# SBI's "by <channel>" form:
#   "Your A/C XXXXX000000 has a debit by NACH of Rs 10,000.00 on 10/07/26"
_SBI_HAS_BY = re.compile(
    r"your\s+A/?C\s*(?P<acct>X*\d{3,})\s+has\s+a?\s*(?P<dir>credit|debit)\s+by\s+"
    r"(?P<merchant>[A-Za-z ]{2,20}?)\s+of\s+" + _AMOUNT +
    r"\s+on\s+(?P<d>\d{1,2})[/-](?P<m>\d{1,2})[/-](?P<y>\d{2,4})",
    re.IGNORECASE | re.DOTALL)

# SBI YONO fund-transfer receipt — a flattened HTML table rather than a sentence:
#   "Transaction Status Successful Amount Rs.97,000.00 Transaction Number 000000000000
#    Date of Transaction 03.08.26 Debit account x0000 Beneficiary Name SOME PERSON"
# Requires "Successful" so a failed transfer receipt is not booked.
_YONO_TRANSFER = re.compile(
    r"transaction\s+status\s+successful\s+amount\s+" + _AMOUNT +
    r".{0,80}?date\s+of\s+transaction\s+(?P<d>\d{1,2})[.\-/](?P<m>\d{1,2})[.\-/](?P<y>\d{2,4})"
    r"(?:.{0,60}?beneficiary\s+name\s+(?P<merchant>[A-Za-z .]{2,40}?)\s+(?:beneficiary|account|$))?",
    re.IGNORECASE | re.DOTALL)

# Generic UPI/debit-card wording used by several banks:
#   "INR 250.00 debited from A/c XX1234 on 05-08-26 to VPA someone@upi"
_GENERIC = re.compile(
    _AMOUNT + r"\s+(?P<dir>debited|credited)\s+(?:from|to)\s+(?:your\s+)?A/?c[^0-9]{0,10}"
    r"(?P<last4>[X*]*\d{3,})\s+on\s+(?P<d>\d{1,2})[/-](?P<m>[A-Za-z0-9]{2,3})[/-](?P<y>\d{2,4})"
    r"(?:\s+(?:to|at|towards)\s+(?P<merchant>.{0,60}?))?(?:\.|$)",
    re.IGNORECASE | re.DOTALL)

# LAST-RESORT, bank-agnostic shape: <amount> … debited/credited … <date>, in either order, with an
# optional merchant after to/at/towards/from. Deliberately last in the chain so a bank-specific
# pattern always wins. This is what lets a bank nobody has written a rule for still work — the named
# patterns above only exist because they extract merchant/account more reliably.
_CCY = r"(?:Rs\.?|INR|₹|USD|GBP|EUR|AED|\$|£|€)"
#: Only the PAST-PARTICIPLE forms count as a direction word here. The bare nouns "debit"/"credit"
#: appear inside "Credit Card", "Debit Card", "credit limit" and "credit score", so accepting them
#: made "Rs. 2,500 was spent on your Credit Card" parse as INCOME — a spend booked the wrong way,
#: which is the worst error this parser can make. A card noun is explicitly excluded below.
_DIRWORD = r"(?:debited|credited)"
_ANY_BANK = re.compile(
    r"(?:(?P<dir>" + _DIRWORD + r")\b.{0,60}?" + _CCY + r"\s*(?P<amt>[\d,]+(?:\.\d{1,2})?)"
    r"|" + _CCY + r"\s*(?P<amt2>[\d,]+(?:\.\d{1,2})?).{0,60}?\b(?P<dir2>" + _DIRWORD + r")\b)"
    r".{0,120}?\b(?:on|dated)\s+(?P<d>\d{1,2})[\s./-](?P<m>[A-Za-z]{3,9}|\d{1,2})[\s./,-]+(?P<y>\d{2,4})"
    r"(?:.{0,40}?\b(?:to|at|towards|from)\s+(?P<merchant>[A-Za-z0-9*@.& -]{2,45}?)\s*(?:\.|,|$))?",
    re.IGNORECASE | re.DOTALL)

#: Wording that means money LEFT the account even though no "debited" appears — common on card alerts
#: ("was spent on your Credit Card", "charged to your card"). Without this, such alerts either fall
#: through unparsed or, worse, match a stray "credit" from the card noun.
_SPENT_WORDING = re.compile(
    r"(?i)\b(?:was\s+)?(?:spent|charged|purchase[d]?|swiped|paid)\b")

#: A figure introduced by one of these is a BALANCE or a LIMIT, not the transaction amount. The
#: bank-agnostic pattern uses re.search, which returns the EARLIEST match — so "Avl Bal Rs 1,00,000.
#: Rs 250 debited..." captured the balance and booked a ₹1,00,000 transaction.
_BALANCE_CONTEXT = re.compile(
    r"(?i)(?:avl\.?\s*bal|available\s+balance|balance\s+(?:is|:)|closing\s+balance|"
    r"a/?c\s+bal|bal\s*:|credit\s+limit|available\s+limit|total\s+limit)"
    r"[^\d]{0,12}$")

#: The spend-wording shape itself, so these alerts parse instead of being dropped:
#:   "Rs. 2500.00 was spent on your HDFC Bank Credit Card ending 1234 at SOME SHOP on 05/08/2026"
#:   "INR 899.00 charged to your Credit Card 5678 at A SHOP on 06/08/2026"
#: Always a debit — the direction is in the verb, not in a participle.
_SPENT_ON = re.compile(
    _AMOUNT + r"\s+(?:was\s+)?(?:spent|charged|swiped|debited)\s+(?:on|to|at|from)\s+"
    r"(?:your\s+)?(?P<acct>.{0,50}?)(?:ending\s+)?(?P<last4>\d{4})?\s*"
    r"(?:\s+(?:at|towards|to)\s+(?P<merchant>.+?))?"
    r"\s+on\s+(?P<d>\d{1,2})[\s./-](?P<m>[A-Za-z]{3,9}|\d{1,2})[\s./,-]+(?P<y>\d{2,4})",
    re.IGNORECASE | re.DOTALL)

_MONTHS = {m.lower(): i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}
_MONTHS.update({m.lower(): i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July", "August",
     "September", "October", "November", "December"], 1)})

#: Trailing noise that shows up glued to the merchant in SBI narrations.
_MERCHANT_TAIL = re.compile(r"(?i)\s*(avl\s*bal.*|available\s*balance.*|-SBI\b.*)$")


@dataclass(frozen=True)
class AlertTxn:
    """One parsed alert. Deliberately not a domain Transaction — the caller decides account/currency."""
    amount_minor: int
    direction: Direction
    txn_date: Optional[date]
    merchant: str
    account_hint: str
    provisional: bool = True
    source: str = ""          # which pattern matched, for debugging


def _minor(raw: str) -> int:
    """Rupees string -> integer paise. Never float arithmetic on money."""
    clean = raw.replace(",", "").strip()
    if "." in clean:
        whole, frac = clean.split(".", 1)
        frac = (frac + "00")[:2]
    else:
        whole, frac = clean, "00"
    return int(whole or 0) * 100 + int(frac)


def _clean_merchant(raw: Optional[str]) -> str:
    if not raw:
        return ""
    m = _MERCHANT_TAIL.sub("", raw).strip(" .-–\t")
    return re.sub(r"\s+", " ", m)[:80]


def _date_dmy(d: str, m: str, y: str) -> Optional[date]:
    year = int(y)
    if year < 100:
        year += 2000
    month = int(m) if m.isdigit() else _MONTHS.get(m.lower(), 0)
    if not month:
        return None
    try:
        return date(year, month, int(d))
    except ValueError:
        return None


_AMOUNT_ANY = re.compile(r"(?:Rs\.?|INR|₹)\s*[\d,]+(?:\.\d{1,2})?", re.IGNORECASE)


def _amount_context(body: str) -> str:
    """The sentence containing the FIRST money figure — the text that describes the event itself.

    Bounded by sentence punctuation rather than a character count, so an unrelated footer ("For OTP
    related queries…") a couple of hundred characters later cannot veto a genuine transaction, while
    a qualifier in the same sentence ("…but the transaction was declined") still does.
    """
    m = _AMOUNT_ANY.search(body)
    if not m:
        return body[:_CONTEXT_CHARS]
    lo = max(0, m.start() - _CONTEXT_CHARS)
    start = max((body.rfind(p, lo, m.start()) for p in (". ", "! ", "? ", ": ")), default=-1)
    end_candidates = [body.find(p, m.end()) for p in (". ", "! ", "? ")]
    end_candidates = [e for e in end_candidates if e != -1]
    end = min(end_candidates) if end_candidates else min(len(body), m.end() + _CONTEXT_CHARS)
    return body[(start + 1) if start != -1 else lo:end]


def _first_real_match(rx: "re.Pattern[str]", body: str):
    """First match whose amount is not a balance or a credit limit.

    `re.search` returns the EARLIEST match, and banks print the running balance or the credit limit
    before the transaction sentence often enough that the earliest money figure is frequently the
    wrong one. Iterating and skipping balance-introduced amounts costs nothing and stops a
    ₹1,00,000 balance being booked as a ₹1,00,000 transaction.
    """
    pos = 0
    for _ in range(6):                      # bounded: a few balance figures at most
        m = rx.search(body, pos)
        if not m:
            return None
        g = m.groupdict()
        start = m.start("amt2") if g.get("amt2") else (
            m.start("amt") if g.get("amt") else m.start())
        if not _BALANCE_CONTEXT.search(body[max(0, start - 40):start]):
            return m
        # this amount was a balance/limit — resume the search AFTER it so a later, real amount
        # can still match. Advancing only past the amount (not the whole match) matters because the
        # match may span the rest of the sentence.
        pos = start + 1
    return None


def parse_alert(text: str, *, subject: str = "") -> Optional[AlertTxn]:
    """Extract one transaction from an alert email, or None if it isn't one.

    Returns None generously: reward-point mails, standing-instruction reminders and statement
    notices all look superficially like transactions, and inventing spending from them is a worse
    failure than missing a swipe that the monthly statement will pick up anyway.
    """
    if not text:
        return None
    body = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text))
    if _NEVER_A_TXN.search(f"{subject} {body}"):
        return None
    if _QUALIFIED_OUT.search(f"{subject} {_amount_context(body)}"):
        return None

    for name, rx in (("hdfc", _HDFC), ("hdfc_at", _HDFC_TXN_AT),
                     ("sbi", _SBI), ("sbi_for", _SBI_HAS_FOR), ("sbi_by", _SBI_HAS_BY),
                     ("yono", _YONO_TRANSFER), ("spent_on", _SPENT_ON), ("generic", _GENERIC),
                     ("any_bank", _ANY_BANK)):
        m = _first_real_match(rx, body)
        if not m:
            continue
        g = m.groupdict()
        if name == "hdfc":
            when = _date_dmy(g["day"], g["mon"], g["year"])
        else:
            when = _date_dmy(g["d"], g["m"], g["y"])
        # Some formats carry no direction word: a card purchase and an outgoing fund transfer are
        # both always debits. The bank-agnostic pattern may capture the word in either of two spots.
        word = (g.get("dir") or g.get("dir2") or "")
        if name in ("hdfc_at", "yono", "spent_on"):
            direction = Direction.DEBIT
        elif _SPENT_WORDING.search(body):
            # "was spent on" / "charged to" states the direction in plain words; trust it over a
            # participle that might have come from elsewhere in the sentence
            direction = Direction.DEBIT
        else:
            direction = (Direction.CREDIT if word.lower().startswith("credit")
                         else Direction.DEBIT)
        amount = _minor(g.get("amt") or g.get("amt2") or "0")
        if amount <= 0:
            return None
        return AlertTxn(
            amount_minor=amount,
            direction=direction,
            txn_date=when,
            merchant=_clean_merchant(g.get("merchant")),
            account_hint=(g.get("last4") or g.get("acct") or "").strip()[-4:],
            source=name)
    return None
