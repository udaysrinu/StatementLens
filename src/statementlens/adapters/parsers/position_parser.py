"""Loans, deposits and pensions — POSITIONS, not transactions.

A loan statement and an FD advice describe a balance you hold or owe, not money you spent. Booking
them as transactions double-counts: every EMI is already a debit on the bank account it was collected
from, and the FD's funding already left that account too. So these parse into snapshots — what is
owed / held, as of a date — and the dashboard shows them beside the cash flow, never inside it.

Every parse checks its own arithmetic before returning, because a position is read once and trusted
for years: a loan's ledger must reconcile (opening + interest − collections = closing, and sanctioned
− principal recovered = outstanding), an FD's principal + interest must equal its maturity amount. A
document that fails its own sums is rejected, not stored with a plausible wrong number.
"""
from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any, Dict, List, Optional


class PositionParseError(ValueError):
    """The document looked like a position but its own figures do not add up."""


def _paise(s: str) -> int:
    return round(float(s.replace(",", "")) * 100)


def _date(s: str) -> Optional[date]:
    s = s.strip()
    for fmt in ("%d-%m-%Y", "%d-%b-%Y", "%b %d, %Y"):
        try:
            return datetime.strptime(s, fmt).date()      # %b matches NOV / Nov alike
        except ValueError:
            pass
    return None


def _last4(s: str) -> str:
    d = re.sub(r"\D", "", s)
    return d[-4:]


# --------------------------------------------------------------------------- Bank of Baroda loan

_BOB_LOAN = re.compile(r"LOAN ACCOUNT NO\s*-\s*(\d{6,})")
_BOB_PERIOD = re.compile(r"for the period (\w{3} \d{1,2}, \d{4}) - (\w{3} \d{1,2}, \d{4})")
_BOB_DETAIL = re.compile(
    r"(\d{2}-\d{2}-\d{4})\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})\s+(\d+)\s*M\s+([\d.]+)\s+"
    r"(\d{2}-\d{2}-\d{4})\s+(\d{2}-\d{2}-\d{4})")
_BOB_TOTALS = re.compile(r"No\.\s*of\s*EMI\s*left\s*\n\s*([\d,]+)\s+([\d,]+)\s+(\d+)\s+(\d+)")
_BOB_OPEN = re.compile(r"(\d{2}-\d{2}-\d{4})\s+Opening Balance\s+([\d,]+\.\d{2})\s*Dr")
_BOB_CLOSE = re.compile(r"(\d{2}-\d{2}-\d{4})\s+Closing Balance\s+([\d,]+\.\d{2})\s*Dr")
_BOB_INTEREST = re.compile(r"(\d{2}-\d{2}-\d{4})\s+\d+:Normal Int\.Coll:.*?\s([\d,]+\.\d{2})\s+[\d,]+\.\d{2}\s*Dr")
_BOB_COLLECT = re.compile(r"(\d{2}-\d{2}-\d{4})\s+COLLECTION/\d+\s+([\d,]+\.\d{2})\s+[\d,]+\.\d{2}\s*Dr")


def is_bob_loan(text: str) -> bool:
    return bool(_BOB_LOAN.search(text)) and "LOAN DETAIL" in text


def parse_bob_loan(text: str) -> Dict[str, Any]:
    """One monthly Bank of Baroda statement → a loan snapshot. Amounts in paise."""
    acct, detail = _BOB_LOAN.search(text), _BOB_DETAIL.search(text)
    tot, opening, closing = _BOB_TOTALS.search(text), _BOB_OPEN.search(text), _BOB_CLOSE.search(text)
    if not (acct and detail and opening and closing):
        raise PositionParseError("Bank of Baroda loan statement missing its detail or balance lines")
    period = _BOB_PERIOD.search(text)
    interest = [(_date(d), _paise(a)) for d, a in _BOB_INTEREST.findall(text)]
    collected = [(_date(d), _paise(a)) for d, a in _BOB_COLLECT.findall(text)]
    open_bal, close_bal = _paise(opening.group(2)), _paise(closing.group(2))
    snap = {
        "kind": "loan", "lender": "Bank of Baroda", "label": f"Bank of Baroda loan ••{_last4(acct.group(1))}",
        "as_of": _date(closing.group(1)).isoformat(),
        "period_from": _date(period.group(1)).isoformat() if period else None,
        "sanctioned_on": _date(detail.group(1)).isoformat(),
        "sanctioned": _paise(detail.group(2)), "emi": _paise(detail.group(3)),
        "tenure_months": int(detail.group(4)), "rate_pct": float(detail.group(5)),
        "last_emi_on": _date(detail.group(6)).isoformat(),
        "next_due": _date(detail.group(7)).isoformat(),
        "opening": open_bal, "outstanding": close_bal,
        "interest": [(d.isoformat(), a) for d, a in interest],
        "collections": [(d.isoformat(), a) for d, a in collected],
    }
    if tot:
        snap.update(principal_paid=int(tot.group(1).replace(",", "")) * 100,
                    interest_paid=int(tot.group(2).replace(",", "")) * 100,
                    emis_paid=int(tot.group(3)), emis_left=int(tot.group(4)))
    # the ledger must reconcile to the paisa, and so must the lifetime totals
    moved = open_bal + sum(a for _, a in interest) - sum(a for _, a in collected)
    if moved != close_bal:
        raise PositionParseError(f"loan ledger does not reconcile: {open_bal} + interest − "
                                 f"collections = {moved}, statement says {close_bal}")
    if tot and snap["sanctioned"] - snap["principal_paid"] != close_bal:
        raise PositionParseError("sanctioned − principal recovered ≠ outstanding")
    return snap


# --------------------------------------------------------------------------- Fixed deposit advice

_FD_FIELDS = {
    "principal": r"Principal Amount:\s*Rs\.\s*([\d,]+(?:\.\d+)?)",
    "maturity_amount": r"Maturity Amount:\s*Rs\.\s*([\d,]+(?:\.\d+)?)",
    "interest_total": r"Total Interest Amt:\s*Rs\.\s*([\d,]+(?:\.\d+)?)",
    "value_date": r"Value Date\s*:\s*(\d{2}-[A-Za-z]{3}-\d{4})",
    "maturity_date": r"Maturity Date:\s*(\d{2}-[A-Za-z]{3}-\d{4})",
    "rate_pct": r"Rate of Interest:\s*([\d.]+)\s*%",
    "months": r"Period of Deposit:\s*(\d+)\s*M",
    "account": r"Account\s*:\s*(\d{6,})",
    "repayment_account": r"Repayment Account:\s*(\d{6,})",
    "on_maturity": r"Maturity Instructions:\s*(.+?)\s+Interest Payment:",
    "payout": r"Interest Payment:\s*([A-Za-z ]+?)\s*$",
    "nominee": r"Nominee Registered:\s*([YN])",
}


def is_fd_advice(text: str) -> bool:
    return "Fixed Deposit Advice" in text and "Maturity Amount" in text


def parse_fd_advice(text: str) -> Dict[str, Any]:
    """A bank's FD advice → a deposit snapshot. Amounts in paise."""
    got = {}
    for k, pat in _FD_FIELDS.items():
        m = re.search(pat, text, re.M)
        got[k] = m.group(1).strip() if m else None
    need = ("principal", "maturity_amount", "value_date", "maturity_date", "rate_pct", "account")
    if not all(got[k] for k in need):
        raise PositionParseError(f"FD advice missing {[k for k in need if not got[k]]}")
    bank = (re.search(r"^\s*([A-Z][A-Z ]+BANK)\b", text, re.M) or re.search(r"(\w+ Bank)", text))
    snap = {
        "kind": "deposit", "bank": bank.group(1).title().replace("Limited", "").strip() if bank else "Bank",
        "principal": _paise(got["principal"]), "maturity_amount": _paise(got["maturity_amount"]),
        "interest_total": _paise(got["interest_total"]) if got["interest_total"] else None,
        "value_date": _date(got["value_date"]).isoformat(),
        "maturity_date": _date(got["maturity_date"]).isoformat(),
        "rate_pct": float(got["rate_pct"]), "months": int(got["months"]) if got["months"] else None,
        "compounding": "quarterly" if "quarter" in (got["payout"] or "").lower() else (got["payout"] or "").lower(),
        "renews": "renew" in (got["on_maturity"] or "").lower(),
        "nominee": got["nominee"] == "Y",
        "repayment_last4": _last4(got["repayment_account"]) if got["repayment_account"] else None,
    }
    snap["label"] = f"{snap['bank']} FD ••{_last4(got['account'])}"
    snap["as_of"] = snap["value_date"]
    if snap["interest_total"] is not None and \
            snap["principal"] + snap["interest_total"] != snap["maturity_amount"]:
        raise PositionParseError("FD principal + interest ≠ maturity amount")
    return snap


# --------------------------------------------------------------------------- NPS (Protean CRA)

_NPS_PERIOD = re.compile(r"(\w{3} \d{1,2}, \d{4}) To (\w{3} \d{1,2}, \d{4})")
_NPS_PRAN = re.compile(r"PRAN\s+(\d{12})")
_NPS_TIER = re.compile(r"Transaction Statement for Tier (I{1,2})\b")
_NPS_XIRR = re.compile(r"(?:Return on Investment|\(XIRR\))\s+(-?[\d.]+)%")
# the summary's figures row: value (A), number of contributions, contributed (B), withdrawn (C),
# notional gain D=(A-B)+C, intermediary charges in units (E)
# Older statements print no (E) column, and some print amounts without thousands separators
_NPS_SUMMARY = re.compile(r"\(A\)\s*\(B\)\s*\(C\)\s*D=\(A-B\)\+C(?:\s*\(E\))?\s*\n\s*"
                          r"([\d,]+\.\d{2})\s+(\d+)\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})\s+(-?[\d,]+\.\d{2})(?:\s+([\d.]+))?")
# a scheme line: "...SCHEME 3,75,220.41 7,314.8228 51.2959" with its asset class ("E - TIER I") on the next line
_NPS_SCHEME = re.compile(r"MANAGEMENT LIMITED SCHEME\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{4})\s+([\d.]+)\s*\n\s*([A-Z]{1,2})\s*-\s*TIER")
# older statements lay the scheme summary out as COLUMNS: one row each for value, units and NAV
_NPS_COLS = re.compile(r"E=U\*N\s+([\d,. ]+?)\s*\nTotal Units U\s+([\d,. ]+?)\s*\nNAV as on \S+ N\s+([\d,. ]+?)\s*\n")
_NPS_CONTRIB = re.compile(r"(\d{2}-[A-Za-z]{3}-\d{2})\s+For\s+(\w+),?\s+(\d{4}).*?\s([\d,]+\.\d{2})\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})\s*$", re.M)
_NPS_PREF = re.compile(r"Scheme Choice\s*:\s*(.+)")


def is_nps_statement(text: str) -> bool:
    return "NPS TRANSACTION STATEMENT" in text and bool(_NPS_PRAN.search(text))


def parse_nps_statement(text: str) -> Dict[str, Any]:
    """A Protean CRA monthly NPS transaction statement -> a pension position. Amounts in paise.

    The statement prints its own arithmetic, and all of it must hold: gain D = A - B + C to the paisa,
    the scheme values add up to A, each scheme value is units x NAV (to within a rupee of rounding),
    and each contribution's employee + employer share equals its total.
    """
    pran, summ = _NPS_PRAN.search(text), _NPS_SUMMARY.search(text)
    period = _NPS_PERIOD.search(text)
    if not (pran and summ and period):
        raise PositionParseError("NPS statement missing its PRAN, period or investment summary")
    value, n, contributed, withdrawn, gain = (_paise(summ.group(1)), int(summ.group(2)), _paise(summ.group(3)),
                                             _paise(summ.group(4)), _paise(summ.group(5)))
    if value - contributed + withdrawn != gain:
        raise PositionParseError(f"NPS summary does not reconcile: {value} - {contributed} + {withdrawn} != {gain}")
    schemes = []
    for v, u, nav, cls in _NPS_SCHEME.findall(text):
        sv, units, navf = _paise(v), float(u.replace(",", "")), float(nav)
        if abs(units * navf * 100 - sv) > 100:
            raise PositionParseError(f"NPS scheme {cls}: units x NAV != value")
        schemes.append({"scheme": cls, "value": sv, "units": units, "nav": navf})
    cols = _NPS_COLS.search(text) if not schemes else None
    if cols:
        block = text[text.find("Scheme Wise Summary"):cols.start()]
        classes = re.findall(r"SCHEME ([A-Z]{1,2}) - TIER", block)
        vals, units, navs = (c.split() for c in cols.groups())
        if not (len(classes) == len(vals) == len(units) == len(navs)):
            raise PositionParseError("NPS scheme columns do not line up")
        for cls, v, u, nav in zip(classes, vals, units, navs):
            sv, uf, nf = _paise(v), float(u.replace(",", "")), float(nav)
            if abs(uf * nf * 100 - sv) > 100:
                raise PositionParseError(f"NPS scheme {cls}: units x NAV != value")
            schemes.append({"scheme": cls, "value": sv, "units": uf, "nav": nf})
    if schemes and sum(x["value"] for x in schemes) != value:
        raise PositionParseError("NPS scheme values do not add up to the holdings value")
    contributions = []
    for d, mon, yr, emp, er, tot in _NPS_CONTRIB.findall(text):
        e, r, t = _paise(emp), _paise(er), _paise(tot)
        if e + r != t:
            raise PositionParseError("NPS contribution: employee + employer != total")
        contributions.append({"date": datetime.strptime(d, "%d-%b-%y").date().isoformat(), "for": f"{mon} {yr}",
                              "employee": e, "employer": r, "total": t})
    tier = (_NPS_TIER.search(text) or [None, "I"])[1]
    xirr = _NPS_XIRR.search(text)
    pref = _NPS_PREF.search(text)
    return {
        "kind": "nps", "label": f"NPS Tier {tier} ••{pran.group(1)[-4:]}",
        "as_of": _date(period.group(2)).isoformat(), "period_from": _date(period.group(1)).isoformat(),
        "value": value, "contributed": contributed, "withdrawn": withdrawn, "gain": gain,
        "contributions_count": n, "xirr_pct": float(xirr.group(1)) if xirr else None,
        "schemes": schemes, "contributions": contributions,
        "preference": pref.group(1).strip() if pref else None,
    }


def parse_position(text: str) -> Optional[Dict[str, Any]]:
    """The snapshot this document describes, or None when it is not a loan, deposit or pension document."""
    if is_bob_loan(text):
        return parse_bob_loan(text)
    if is_fd_advice(text):
        return parse_fd_advice(text)
    if is_nps_statement(text):
        return parse_nps_statement(text)
    return None
