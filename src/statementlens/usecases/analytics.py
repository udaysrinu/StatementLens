"""Analytics use-case — turn categorized Transactions into the dashboard dataset.

Pure and deterministic (integer paise). Produces the compact structure the renderer embeds:
hero metrics, cash flow by month, top categories, recurring, recent, and the insight cards.
No I/O — the app wires a repository + categorizer + this builder together.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List

from ..domain.models import Direction, Transaction
from . import insights as insight_engine


def _median(xs: List[int]) -> int:
    s = sorted(xs)
    n = len(s)
    return 0 if not n else (s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) // 2)


def build_dataset(txns: List[Transaction], *, account: str = "Account",
                  currency: str = "INR") -> Dict[str, Any]:
    """Transaction list -> embeddable dataset for the app-shell renderer."""
    txns = sorted(txns, key=lambda t: (t.txn_date or __import__("datetime").date.min, t.raw_date))
    rows: List[Dict[str, Any]] = []
    debit_total = credit_total = 0
    for t in txns:
        if t.is_debit:
            debit_total += t.amount.minor
        else:
            credit_total += t.amount.minor
        rows.append({
            "d": t.txn_date.isoformat() if t.txn_date else "",
            "mo": t.month,
            "m": t.merchant,
            "desc": t.description,
            "c": t.category or "Other",
            "a": t.amount.minor,
            "dir": "C" if not t.is_debit else "D",
            "b": t.balance.minor if t.balance is not None else None,
        })

    # insight cards (crown jewel)
    ctx = insight_engine.InsightContext(txns=txns, currency=currency)
    cards = [{"key": i.key, "severity": int(i.severity), "icon": i.icon,
              "title": i.title, "copy": i.copy, "cta": i.cta}
             for i in insight_engine.generate(ctx)]

    dates = [r["d"] for r in rows if r["d"]]
    return {
        "meta": {
            "account": account,
            "currency": currency,
            "txn_count": len(rows),
            "verify_debit": debit_total,
            "verify_credit": credit_total,
            "min_date": dates[0] if dates else None,
            "max_date": dates[-1] if dates else None,
        },
        "insights": cards,
        "txns": rows,
    }
