"""Statement parsers — savings (both SBI layouts) and card."""
from statementlens.adapters.parsers.bank_parser import SavingsStatementParser
from statementlens.adapters.parsers.card_parser import CardStatementParser
from statementlens.adapters.parsers.registry import ParserRegistry
from statementlens.domain.models import Direction


def _bank(text):
    return SavingsStatementParser().parse(text, account="X", source_id="s", source_name="f.pdf")


def test_savings_newer_layout_zero_columns():
    text = "\n".join([
        "Date Transaction Reference Credit Debit Balance",
        "01-06-26 UPI/DR/1/J VIJAY/SBIN/x/Pay - 0 123.00 501608.97",
        "05-06-26 INTEREST CREDIT - 1897.00 0 632458.32",
    ])
    stmt = _bank(text)
    debit = next(t for t in stmt.transactions if t.amount.minor == 12300)
    assert debit.direction is Direction.DEBIT and "J VIJAY" in debit.merchant
    credit = next(t for t in stmt.transactions if t.amount.minor == 189700)
    assert credit.direction is Direction.CREDIT


def test_savings_older_layout_dash_columns():
    # empty columns are '-' (older SBI), narration wraps to previous line
    text = "\n".join([
        "Date Transaction Reference Credit Debit Balance",
        "UPI/DR/361/SAMPLEPY/SBIN/x/Pay",
        "03-09-23 - - 3000.00 292702.98",
    ])
    stmt = _bank(text)
    assert stmt.count == 1
    t = stmt.transactions[0]
    assert t.amount.minor == 300000 and t.direction is Direction.DEBIT
    assert "SAMPLEPY" in t.merchant  # wrapped narration stitched


def test_card_parser_trailing_amount_and_cr():
    text = "\n".join([
        "11/07/2026  RAZ*SWIGGY BANGALORE  1,508.00",
        "15/07/2026  PAYMENT RECEIVED  5,000.00 Cr",
    ])
    stmt = CardStatementParser().parse(text, account="C", source_id="s", source_name="c.pdf")
    swiggy = next(t for t in stmt.transactions if t.amount.minor == 150800)
    assert swiggy.direction is Direction.DEBIT
    pay = next(t for t in stmt.transactions if t.amount.minor == 500000)
    assert pay.direction is Direction.CREDIT


def test_registry_picks_savings_over_card():
    text = "Date Transaction Reference Credit Debit Balance\n01-06-26 X - 0 10.00 100.00"
    reg = ParserRegistry().register(SavingsStatementParser()).register(CardStatementParser())
    stmt = reg.parse(text, account="X", source_id="s", source_name="f.pdf")
    assert stmt.count == 1 and stmt.transactions[0].balance is not None


def test_card_parser_hyphenated_month_with_dr_cr_flag():
    """Layout: "07-Aug-2025 MERCHANT CITY 5,000.00 DR 526873XXXXXX1234".

    The amount is NOT trailing (a DR/CR flag and the masked card follow it), and the flag is
    authoritative for direction rather than something to infer.
    """
    text = "\n".join([
        "07-Aug-2025 SAMPLE INSURER GURGAON 5,000.00 DR 526873XXXXXX1234",
        "17-Aug-2025 SAMPLE INSURER GURGAON 2.00 CR 526873XXXXXX1234",
        "02-Sep-2025 10% Sample Cashback 934.30 CR",
    ])
    stmt = CardStatementParser().parse(text, account="C", source_id="s", source_name="c.pdf")
    assert stmt.count == 3
    debit = next(t for t in stmt.transactions if t.amount.minor == 500000)
    assert debit.direction is Direction.DEBIT
    assert debit.txn_date.isoformat() == "2025-08-07"
    for t in stmt.transactions:
        if t.amount.minor in (200, 93430):
            assert t.direction is Direction.CREDIT


def test_card_parser_date_time_rows_with_plus_for_credits():
    """Layout: "01/07/2026| 07:59 MERCHANT C 192.00 l".

    The rupee glyph extracts as a stray letter, and a leading "+" marks a payment/cashback. Without
    reading the "+" every credit would be booked as spending.
    """
    text = "\n".join([
        "01/07/2026| 07:59 RSP*SAMPLEMARTBANGALORE C 192.00 l",
        "11/07/2026| 20:36 RAZ*SAMPLESHOPBengaluru C 1,508.00 l",
        "04/07/2026| 00:00 10% Sample CashBack + C 25.00 l",
        "22/07/2026| 01:45 BPPY CC PAYMENT DP0162 (Ref# ST2620) + C 6,802.00",
    ])
    stmt = CardStatementParser().parse(text, account="C", source_id="s", source_name="c.pdf")
    assert stmt.count == 4
    purchases = [t for t in stmt.transactions if t.direction is Direction.DEBIT]
    credits = [t for t in stmt.transactions if t.direction is Direction.CREDIT]
    assert {t.amount.minor for t in purchases} == {19200, 150800}
    assert {t.amount.minor for t in credits} == {2500, 680200}
    assert purchases[0].txn_date.isoformat() == "2026-07-01"
