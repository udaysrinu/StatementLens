"""Checks for the cash-flow / period logic. Synthetic data only — no real statement values."""

from datetime import date

from statementlens.domain.models import Direction, Transaction
from statementlens.domain.money import Money
from statementlens.usecases.flows import (
    SELF_TRANSFER, SPEND, INVESTMENT, INCOMING,
    cash_flow, classify_flow, detect_salary_day, incoming_breakdown,
    monthly_series, recurring_payments, salary_cycle,
)


def txn(day, amount, direction=Direction.DEBIT, merchant="", desc="", cat=None, month=1):
    return Transaction(
        txn_date=date(2026, month, day), description=desc or merchant,
        amount=Money.of(amount, "INR"), direction=direction,
        merchant=merchant, category=cat)


def test_three_way_split_keeps_investments_out_of_spend():
    txns = [
        txn(1, 100000, Direction.CREDIT, "Employer", "SALARY CREDIT"),
        txn(2, 50000, merchant="ZERODHA"),          # investment, not a spend
        txn(3, 400, merchant="Swiggy", cat="Food & dining"),
    ]
    f = cash_flow(txns)
    assert f.incoming == 10000000
    assert f.investments == 5000000
    assert f.spends == 40000
    # net is honest: what came in minus BOTH outflows
    assert f.net == 10000000 - 5000000 - 40000


def test_self_transfers_excluded_from_both_sides():
    own = ["Gidijala Uday"]
    txns = [
        txn(1, 5000, Direction.DEBIT, "UPI GIDIJALA UDAY", "self move out"),
        txn(1, 5000, Direction.CREDIT, "UPI GIDIJALA UDAY", "self move in"),
        txn(2, 400, merchant="Swiggy", cat="Food & dining"),
    ]
    f = cash_flow(txns, own)
    assert f.incoming == 0 and f.spends == 40000     # both legs removed
    assert f.self_transfer_count == 2
    assert classify_flow(txns[0], own) == SELF_TRANSFER
    # without own_names, the same rows count normally
    assert cash_flow(txns).incoming == 500000


def test_short_names_do_not_trigger_self_transfer():
    # a 3-char name must NOT match — too collision-prone to erase real money
    t = txn(1, 900, merchant="RAJESH KUMAR")
    assert classify_flow(t, ["raj"]) == SPEND


def test_salary_cycle_clamps_short_months():
    # salary on the 31st: February has none, so the cycle must clamp, not crash
    start, end = salary_cycle(date(2026, 2, 10), 31)
    assert start == date(2026, 1, 31)
    assert end == date(2026, 2, 27)          # day before Feb 28 (clamped next start)
    # and the two halves must abut exactly, no gap and no overlap
    nxt_start, _ = salary_cycle(date(2026, 3, 1), 31)
    assert nxt_start == date(2026, 2, 28)
    assert end.toordinal() + 1 == nxt_start.toordinal()


def test_salary_cycle_before_anchor_day_uses_previous_cycle():
    start, end = salary_cycle(date(2026, 5, 3), 25)
    assert start == date(2026, 4, 25) and end == date(2026, 5, 24)


def test_detect_salary_day_needs_three_observations():
    two = [txn(5, 100000, Direction.CREDIT, desc="SALARY", month=m) for m in (1, 2)]
    assert detect_salary_day(two) is None
    three = two + [txn(5, 100000, Direction.CREDIT, desc="SALARY", month=3)]
    assert detect_salary_day(three) == 5


def test_incoming_breakdown_shares_sum_to_one():
    txns = [
        txn(1, 90000, Direction.CREDIT, desc="SALARY AUG"),
        txn(2, 10000, Direction.CREDIT, desc="UPI FROM FRIEND"),
    ]
    rows = incoming_breakdown(txns)
    assert rows[0]["source"] == "Salary"
    assert abs(sum(r["share"] for r in rows) - 1.0) < 1e-9


def test_income_rules_beat_the_spend_categorizer_label():
    # a spend categorizer has no notion of salary; its label must not win for credits
    t = txn(1, 190000, Direction.CREDIT, desc="SAL FOR SEP 2022", cat="professional services")
    rows = incoming_breakdown([t])
    assert rows[0]["source"] == "Salary"


def test_monthly_series_averages_only_months_with_data():
    txns = [txn(3, 1000, merchant="Shop", month=1), txn(4, 3000, merchant="Shop", month=2)]
    series = monthly_series(txns, months=6)
    assert len(series) == 2                    # not padded to 6
    assert series[0]["avg"] == (100000 + 300000) // 2


def test_recurring_reports_usual_day_and_next_date():
    txns = [txn(3, 3000, merchant="Landlord", month=m) for m in (1, 2, 3)]
    rec = recurring_payments(txns, as_of=date(2026, 3, 20))
    assert rec[0]["usual_day"] == 3
    assert rec[0]["months"] == 3
    assert rec[0]["active"] is True
    assert rec[0]["next_expected"] == "2026-04-03"


def test_recurring_merges_case_variant_merchant_names():
    # "ZERODHA" and "Zerodha" are one payee; splitting them halves the cadence and duplicates rows
    txns = ([txn(2, 5000, merchant="ZERODHA", month=m) for m in (1, 2)] +
            [txn(2, 5000, merchant="Zerodha", month=m) for m in (3, 4)])
    rec = recurring_payments(txns, as_of=date(2026, 4, 20))
    assert len(rec) == 1
    assert rec[0]["months"] == 4


def test_stale_recurring_gets_no_predicted_date():
    # a subscription last seen 18 months ago must not claim a future date
    txns = [txn(3, 3000, merchant="DeadSub", month=m) for m in (1, 2, 3)]
    rec = recurring_payments(txns, as_of=date(2027, 9, 1))
    assert rec[0]["active"] is False
    assert rec[0]["next_expected"] is None


def test_salary_regex_does_not_swallow_unrelated_words():
    # "SAL FOR SEP 2022" is salary; a word merely containing "sal" is not
    from statementlens.usecases.flows import _SALARY_RE
    assert _SALARY_RE.search("SAL FOR SEP 2022 109797303")
    assert _SALARY_RE.search("SALARY AUG")
    assert not _SALARY_RE.search("WHOLESALE MART")
    assert not _SALARY_RE.search("SALON VISIT")


def test_investment_detected_by_merchant_without_category():
    assert classify_flow(txn(1, 5000, merchant="GROWW SIP")) == INVESTMENT
    assert classify_flow(txn(1, 5000, merchant="Swiggy")) == SPEND
    assert classify_flow(txn(1, 5000, Direction.CREDIT, merchant="Anyone")) == INCOMING


def test_incoming_breakdown_never_hides_money():
    """A breakdown that looks complete must BE complete.

    Truncating to the top N silently left the shares summing to less than 1.0, so a reader had no way
    to know income was missing from the list. The tail folds into an explicit "Other" row instead.
    """
    # incoming_breakdown groups by SOURCE TYPE, not by payer, so the fixture needs distinct types.
    # Uncategorized credits fall back to their category, which is what produces many small sources.
    # Narrations with no salary/refund/interest/channel keyword fall through to the row's category,
    # which is how many distinct sources arise in practice.
    txns = [txn(1, 1000 * (i + 1), Direction.CREDIT, f"PAYER{i:02d}",
                f"credit entry {i}", cat=f"source-{i:02d}")
            for i in range(12)]
    rows = incoming_breakdown(txns, limit=6)
    assert len(rows) == 6
    assert abs(sum(r["share"] for r in rows) - 1.0) < 1e-9
    assert sum(r["amount"] for r in rows) == sum(t.amount.minor for t in txns)
    assert "Other" in rows[-1]["source"]


def test_incoming_breakdown_adds_no_other_row_when_it_fits():
    txns = [txn(1, 5000, Direction.CREDIT, desc="SALARY AUG"),
            txn(2, 100, Direction.CREDIT, desc="UPI FROM FRIEND")]
    rows = incoming_breakdown(txns, limit=6)
    assert not any("Other" in r["source"] for r in rows)


def test_monthly_series_reports_how_much_history_it_hides():
    """A 12-month chart over years of data must not read as the whole history."""
    txns = [txn(3, 1000, merchant="Shop", month=m) for m in range(1, 13)]
    series = monthly_series(txns, months=6)
    assert len(series) == 6
    assert series[0]["months_shown"] == 6
    assert series[0]["months_hidden"] == 6
    full = monthly_series(txns, months=24)
    assert full[0]["months_hidden"] == 0


def test_next_expected_uses_the_real_month_length():
    """A 29/30/31 payee was always predicted for the 28th.

    `min(day, 28)` ran before the loop that already backs off to the real month length, so the
    pre-clamp was dead weight that made every month-end payee 1-3 days early.
    """
    from statementlens.usecases.flows import _next_on_day
    assert _next_on_day(date(2024, 7, 30), 30) == date(2024, 8, 30)
    assert _next_on_day(date(2024, 5, 31), 31) == date(2024, 6, 30)   # June has 30
    assert _next_on_day(date(2024, 1, 31), 31) == date(2024, 2, 29)   # 2024 is a leap year
    assert _next_on_day(date(2025, 1, 31), 31) == date(2025, 2, 28)   # 2025 is not
