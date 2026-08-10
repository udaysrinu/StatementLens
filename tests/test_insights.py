"""Insight engine — detectors fire correctly and the engine never dead-ends."""
from datetime import date

from statementlens.domain.models import Direction, Transaction
from statementlens.domain.money import Money
from statementlens.usecases import insights as ie


def _t(d, desc, minor, direction=Direction.DEBIT, merchant="", category="Other", bal=None):
    return Transaction(txn_date=d, description=desc, amount=Money(minor), direction=direction,
                       merchant=merchant, category=category,
                       balance=Money(bal) if bal is not None else None,
                       raw_date=d.isoformat() if d else "")


def test_duplicate_charge_flags_real_double():
    txns = [
        _t(date(2026, 3, 10), "IRCTC", 79360, merchant="IRCTC", category="Travel"),
        _t(date(2026, 3, 12), "IRCTC", 79360, merchant="IRCTC", category="Travel"),
    ]
    ins = ie.generate(ie.InsightContext(txns))
    assert any(i.key == "duplicate" for i in ins)


def test_duplicate_ignores_same_day_and_investments():
    # same-day split payments and investment buys must NOT flag
    txns = [
        _t(date(2026, 2, 15), "Zerodha", 10000000, merchant="Zerodha", category="Investments"),
        _t(date(2026, 2, 15), "Zerodha", 10000000, merchant="Zerodha", category="Investments"),
    ]
    ins = ie.generate(ie.InsightContext(txns))
    assert not any(i.key == "duplicate" for i in ins)


def test_fees_detector_sums_fee_category():
    txns = [_t(date(2026, 1, 1), "SMS ALERT CHG", 5900, category="Fees & Charges")]
    ins = ie.generate(ie.InsightContext(txns))
    assert any(i.key == "fees" for i in ins)


def test_engine_never_dead_ends():
    txns = [_t(date(2026, 1, 1), "random", 100, category="Other")]
    ins = ie.generate(ie.InsightContext(txns))
    assert ins and ins[0].key in {"caught_up", "top_payee"}  # always at least one card


def test_forgotten_credit_surfaces_refund():
    txns = [_t(date(2026, 1, 5), "Amazon refund", 215000, direction=Direction.CREDIT,
               merchant="Amazon", category="Other income")]
    ins = ie.generate(ie.InsightContext(txns))
    assert any(i.key == "credit" for i in ins)


def test_caps_at_four():
    txns = []
    for i in range(6):
        d = date(2026, 1, i + 1)
        txns.append(_t(d, f"m{i}", 1000 * (i + 1), merchant=f"M{i}", category="Fees & Charges"))
        txns.append(_t(d, f"m{i}", 1000 * (i + 1), category="Fees & Charges"))
    ins = ie.generate(ie.InsightContext(txns), limit=4)
    assert len(ins) <= 4
