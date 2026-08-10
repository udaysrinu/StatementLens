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
        "UPI/DR/361/NARAYANA/SBIN/x/Pay",
        "03-09-23 - - 3000.00 292702.98",
    ])
    stmt = _bank(text)
    assert stmt.count == 1
    t = stmt.transactions[0]
    assert t.amount.minor == 300000 and t.direction is Direction.DEBIT
    assert "NARAYANA" in t.merchant  # wrapped narration stitched


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
