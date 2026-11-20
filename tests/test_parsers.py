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


def test_an_emi_schedule_row_is_not_a_purchase():
    """Real ICICI layout: the EMI table sits among the transactions and matched the row pattern."""
    from statementlens.adapters.parsers.card_parser import CardStatementParser
    text = ("Statement period 08/11/2025 to 07/12/2025\n"
            "28/11/2025 12413112054 IBIBO GROUP PRIVATE LIM -227 11,357.00 CR\n"
            "28/11/2025 28/01/2026 3 11,357.00 1 3,887.00\n"
            "28/11/2025 12413112083 Principal Amount Amortization - <1/3>IBIBO 0 3,735.67\n")
    rows = CardStatementParser().parse(text, account="ICICI ••3456", source_id="s",
                                       source_name="x.pdf").transactions
    assert [round(t.amount.minor / 100, 2) for t in rows] == [11357.0, 3735.67]


def _rbl(extra_rows, credits, emi_out="0.00"):
    return ("Statement Period 21-07-2026 to 20-08-2026\n"
            f"- Payments & Credits {credits}\n- Transferred to EMI {emi_out}\n+ New Debits 0.00\n"
            + "\n".join(extra_rows) + "\n")


def test_rbl_credits_are_settled_from_the_printed_totals():
    """Real RBL layout: no Cr flag on any row; the refund reads exactly like a purchase."""
    from statementlens.adapters.parsers.card_parser import CardStatementParser
    text = _rbl(["Card Number XX20 5 Jul 2026 PYU*MYNTRA DESIGNS PRI Bangalore IND 6,925.00",
                 "Total Amount Due -6,335.10 21 Jul 2026 PAYMENT RECEIVED - BBPS 6,948.00",
                 "Min. Amt. Due 0.00 20 Aug 2026 MEMBERSHIP FEE 500.00"], "13,873.00")
    rows = CardStatementParser().parse(text, account="RBL ••7788", source_id="s",
                                       source_name="x.pdf").transactions
    got = {(round(t.amount.minor / 100), t.is_debit) for t in rows}
    assert got == {(6925, False), (6948, False), (500, True)}


def test_rbl_emi_transfer_is_a_credit():
    from statementlens.adapters.parsers.card_parser import CardStatementParser
    text = _rbl(["9 Feb 2026 AMAZON PAY INDIA Bangalore 10,843.22",
                 "Total Amount Due PAY NOW 3,906.00 9 Feb 2026 TRANSFERRED TO EMI(MERCHANT EMI - 3 MON- 10,843.22"],
                "0.00", emi_out="10,843.22")
    rows = CardStatementParser().parse(text, account="RBL ••7788", source_id="s",
                                       source_name="x.pdf").transactions
    assert sorted((t.is_debit, round(t.amount.minor / 100, 2)) for t in rows) == \
        [(False, 10843.22), (True, 10843.22)]


def test_an_ambiguous_remainder_is_left_alone():
    """Two rows could be the ₹500 credit: guessing one would be worse than the known gap."""
    from statementlens.adapters.parsers.card_parser import CardStatementParser
    text = _rbl(["5 Jul 2026 SWIGGY Bangalore 500.00", "6 Jul 2026 ZOMATO Gurgaon 500.00"], "500.00")
    rows = CardStatementParser().parse(text, account="RBL ••7788", source_id="s",
                                       source_name="x.pdf").transactions
    assert all(t.is_debit for t in rows)
