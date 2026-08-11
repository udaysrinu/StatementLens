"""Checks for import diagnostics — the guard against a silent empty dashboard.

Text samples are hand-written to mimic real layouts; no real statement content.
"""

from statementlens.usecases.diagnose import ImportProblem, diagnose

# Mimics SBI's OnlineSBI "Find Transactions" printout: one amount per row, no balance,
# no debit/credit column (direction was column position, lost in text extraction).
_WEB_PRINTOUT = """State Bank of India
You are here: / Request & Enquiries / Find Transactions
Transaction Details Account Number 000000000000000
Date (Value Date) Narration Debit Credit
15-Sep-18 (15-Sep-2018) 382.48
INB SOME-MERCHANT NAME HERE
16-Sep-18 (16-Sep-2018) 2,000.00
ATM CASH 0000 SOMEWHERE
""" + ("filler line to clear the minimum text threshold\n" * 6)

_REAL_STATEMENT = """ACCOUNT STATEMENT
Txn Date Description Credit Debit Balance
01-06-26 UPI/CR/000000/SOMEONE/BANK 100.00 0 5,000.00
02-06-26 UPI/DR/000001/SHOP/BANK 0 250.00 4,750.00
""" + ("more statement text to exceed the threshold\n" * 6)


def test_scanned_image_is_detected_and_fatal():
    d = diagnose("\n\n\n\n", source_name="scan.pdf")
    assert d.problem == ImportProblem.NO_TEXT_LAYER
    assert d.is_fatal
    assert "scanned image" in d.message
    assert "scan.pdf" in d.message


def test_web_printout_is_rejected_rather_than_guessed():
    # importing this would invent directions and corrupt every total — refuse instead
    d = diagnose(_WEB_PRINTOUT, source_name="printout.pdf")
    assert d.problem == ImportProblem.WEB_PRINTOUT
    assert d.is_fatal
    assert "money in or money out" in d.message


def test_unknown_but_readable_layout_is_not_fatal():
    # plain text we simply don't have a parser for yet — fixable, so not fatal
    d = diagnose("Some bank statement text " * 40, source_name="mystery.pdf")
    assert d.problem == ImportProblem.NO_ROWS_MATCHED
    assert not d.is_fatal


def test_web_printout_needs_both_row_shape_and_marker():
    # dated rows alone must NOT be called a web printout; that would reject real statements
    rows_only = "\n".join(f"1{i}-Sep-18 (1{i}-Sep-2018) 100.00" for i in range(5)) + \
                "\n" + ("padding text here\n" * 10)
    d = diagnose(rows_only, source_name="x.pdf")
    assert d.problem == ImportProblem.NO_ROWS_MATCHED


def test_parseable_statement_text_still_gets_a_reason_not_a_crash():
    # diagnose() is only called when parsers found nothing, so even good-looking text
    # returns an explanation rather than None-crashing the caller
    d = diagnose(_REAL_STATEMENT, source_name="stmt.pdf")
    assert d is not None and d.problem == ImportProblem.NO_ROWS_MATCHED


def test_message_always_names_the_file_or_falls_back():
    assert "This PDF" in diagnose("\n").message
    assert "a.pdf" in diagnose("\n", source_name="a.pdf").message
