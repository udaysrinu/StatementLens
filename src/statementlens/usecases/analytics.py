"""Analytics use-case — turn categorized Transactions into the dashboard dataset.

Pure and deterministic (integer paise). Produces the compact structure the renderer embeds:
hero metrics, cash flow by month, top categories, recurring, recent, and the insight cards.
No I/O — the app wires a repository + categorizer + this builder together.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List

from ..domain.models import Direction, Transaction
from . import flows as flow_engine
from . import insights as insight_engine
from . import tagging as tag_engine


def _median(xs: List[int]) -> int:
    s = sorted(xs)
    n = len(s)
    return 0 if not n else (s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) // 2)


#: Compact wire codes for flow buckets. Explicit, not first-letter — "incoming"/"investment" and
#: "spend"/"self" collide on their first character.
_FLOW_CODE = {
    flow_engine.INCOMING: "i",
    flow_engine.INVESTMENT: "v",
    flow_engine.SPEND: "s",
    flow_engine.SELF_TRANSFER: "x",
}


def build_dataset(txns: List[Transaction], *, account: str = "Account",
                  currency: str = "INR", own_names: List[str] = None,
                  tags: "tag_engine.TagStore" = None) -> Dict[str, Any]:
    """Transaction list -> embeddable dataset for the app-shell renderer.

    `own_names` enables self-transfer exclusion: money moved between the owner's own accounts is
    neither income nor expenditure, so counting both legs double-inflates every total.
    `tags` carries the user's tag corrections and notes, which override the automatic tags.
    """
    own_names = own_names or []
    tags = tags or tag_engine.TagStore()
    # normalize onto the closed tag vocabulary and apply user corrections BEFORE any aggregation,
    # so every downstream total, insight and grouping speaks the same vocabulary
    txns = tag_engine.apply_tags(txns, tags)
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
            # flow bucket, so the client can re-slice without re-deriving the rules
            "f": _FLOW_CODE[flow_engine.classify_flow(t, own_names)],
            "ref": t.source_ref,
            "note": tags.note_for(t),
        })

    # insight cards (crown jewel)
    ctx = insight_engine.InsightContext(txns=txns, currency=currency)
    cards = [{"key": i.key, "severity": int(i.severity), "icon": i.icon,
              "title": i.title, "copy": i.copy, "cta": i.cta}
             for i in insight_engine.generate(ctx)]

    # honest three-way flow + the CRED-style comparatives
    flow = flow_engine.cash_flow(txns, own_names)
    months = len({t.month for t in txns if t.month}) or 1
    salary_day = flow_engine.detect_salary_day(txns)

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
            "months": months,
            "salary_day": salary_day,
        },
        "flow": {
            "incoming": flow.incoming,
            "investments": flow.investments,
            "spends": flow.spends,
            "net": flow.net,
            "self_transfers": flow.self_transfers,
            "self_transfer_count": flow.self_transfer_count,
            "avg_spend_per_month": flow_engine.per_month_average(flow.spends, months),
            "avg_incoming_per_month": flow_engine.per_month_average(flow.incoming, months),
        },
        "incoming_sources": flow_engine.incoming_breakdown(txns, own_names),
        "monthly": flow_engine.monthly_series(txns, own_names, months=12),
        "recurring": flow_engine.recurring_payments(txns, own_names),
        "tags": tag_engine.group_by_tag(txns),
        "tag_vocab": [{"tag": t, "icon": i} for t, i in tag_engine.TAGS],
        "review_queue": tag_engine.review_queue(txns, tags),
        "untagged": tag_engine.untagged_count(txns),
        "insights": cards,
        "txns": rows,
    }
