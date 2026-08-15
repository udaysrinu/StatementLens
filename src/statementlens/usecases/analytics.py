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
from .similar import merchant_key


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
                  tags: "tag_engine.TagStore" = None,
                  sync: Dict[str, Any] = None) -> Dict[str, Any]:
    """Transaction list -> embeddable dataset for the app-shell renderer.

    `own_names` enables self-transfer exclusion: money moved between the owner's own accounts is
    neither income nor expenditure, so counting both legs double-inflates every total.
    `tags` carries the user's tag corrections and notes, which override the automatic tags.
    """
    own_names = own_names or []
    tags = tags or tag_engine.TagStore()
    # Pairing is stamped onto ROWS (not shipped as another all-time summary) so the client can honour
    # the period picker: a reversal whose refund leg falls outside the selected range must not silently
    # remove the charge leg from that range's total.
    from .netting import find_reversals
    from .netting import person_nets as _person_nets
    rev_by_ref: Dict[str, str] = {}
    for _r in find_reversals(txns):
        rev_by_ref[_r.out_ref] = _r.back_ref
        rev_by_ref[_r.back_ref] = _r.out_ref
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
        bucket = flow_engine.classify_flow(t, own_names)
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
            "f": _FLOW_CODE[bucket],
            "ref": t.source_ref,
            "note": tags.note_for(t),
            # unsettled alert rows must be distinguishable downstream; omitted when false to keep
            # the embedded payload small
            "p": 1 if t.provisional else None,
            # Income source per ROW, so the client can rebuild the breakdown for the selected period.
            # The `incoming_sources` summary below is all-time only; a dashboard that showed it beside
            # a 1M hero would repeat the "always versus last month" mismatch. Carried only on credits
            # — on a debit it is dead weight in the payload.
            **({"src": flow_engine.income_source(t)} if bucket == flow_engine.INCOMING else {}),
            # the OTHER leg of a reversal, so the client can drop a pair only when it holds both
            **({"rev": rev_by_ref[t.source_ref]} if t.source_ref in rev_by_ref else {}),
            # counterparty identity, for person-level netting without re-deriving the key in JS
            **({"cp": _key} if (_key := merchant_key(t)) and len(_key) >= 3 else {}),
        })

    # insight cards (crown jewel)
    ctx = insight_engine.InsightContext(txns=txns, currency=currency)
    cards = [{"key": i.key, "severity": int(i.severity), "icon": i.icon,
              "title": i.title, "copy": i.copy, "cta": i.cta}
             for i in insight_engine.generate(ctx)]

    # honest three-way flow + the CRED-style comparatives
    flow = flow_engine.cash_flow(txns, own_names)
    # a credit card needs its own frame: charges/payments/refunds, not income/investments/net
    # Only SETTLED rows feed the card heuristic: alert rows always carry balance=None, which is the
    # first signal looks_like_card() tests, so a handful of alerts on a bank account would flip the
    # whole dashboard into credit-card framing.
    is_card = flow_engine.looks_like_card([t for t in txns if not t.provisional], account)
    card = flow_engine.card_flow(txns) if is_card else None
    months = len({t.month for t in txns if t.month}) or 1
    salary_day = flow_engine.detect_salary_day(txns)

    dates = [r["d"] for r in rows if r["d"]]
    return {
        "meta": {
            "account": account,
            "currency": currency,
            "sync": sync or {},
            "txn_count": len(rows),
            "verify_debit": debit_total,
            "verify_credit": credit_total,
            "min_date": dates[0] if dates else None,
            "max_date": dates[-1] if dates else None,
            "months": months,
            "salary_day": salary_day,
            "is_card": is_card,
        },
        "card": ({"charges": card.charges, "fees": card.fees, "payments": card.payments,
                  "refunds": card.refunds, "rewards": card.rewards,
                  "net_new_debt": card.net_new_debt} if card else None),
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
        # Both of these are ALL-TIME summaries for dataset consumers (JSON export, scripts).
        # The dashboard deliberately does NOT render them: it re-aggregates per selected period and
        # per selected flow, because an all-time breakdown beside a 1M hero contradicts it.
        "incoming_sources": flow_engine.incoming_breakdown(txns, own_names),
        "monthly": flow_engine.monthly_series(txns, own_names, months=12),
        # cancelled pairs and two-way counterparties, for the "net" toggles
        "reversals": [r.as_dict() for r in find_reversals(txns)],
        "person_nets": [p.as_dict() for p in _person_nets(txns)],
        "recurring": flow_engine.recurring_payments(txns, own_names),
        # Same predicate as the cash flow: group_by_tag only drops rows literally tagged
        # "self transfer", while classify_flow also routes card-bill payments and own-name matches
        # there. Using the raw list made tag shares disagree with the spend/investment totals
        # printed beside them.
        "tags": tag_engine.group_by_tag(
            [t for t in txns
             if flow_engine.classify_flow(t, own_names) in (flow_engine.SPEND,
                                                            flow_engine.INVESTMENT)]),
        "tag_vocab": [{"tag": t, "icon": i} for t, i in tag_engine.TAGS],
        "review_queue": tag_engine.review_queue(txns, tags),
        "untagged": tag_engine.untagged_count(txns),
        "insights": cards,
        "txns": rows,
    }
