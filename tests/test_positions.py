"""Loans and deposits are positions: parsed, self-checked, stored apart from transactions.

A Bank of Baroda car-loan statement booked as transactions would count every EMI twice (each one is
already a debit on the paying savings account), and an FD advice would book its principal as spend.
Synthetic documents shaped like the real ones; every figure below is made up but reconciles.
"""
import tempfile
from pathlib import Path

from statementlens.adapters.parsers.position_parser import (PositionParseError, parse_position)
from statementlens.adapters.persistence.sqlite_repo import SqliteTransactionRepository
from statementlens.usecases.ingest import IngestStatements

LOAN = """LOAN ACCOUNT NO - 99990000001234
Statement for the period Oct 01, 2026 - Oct 31, 2026
LOAN DETAIL
04-06-2026 10,00,000.00 30,000.00 36 M 9.15 10-10-2026 10-11-2026
Principal Recovered Interest Recovered No. of EMI paid No. of EMI left
73,000 20,000 4 32
01-10-2026 Opening Balance 9,50,000.00 Dr
05-10-2026 1:Normal Int.Coll:Oct 7,000.00 9,57,000.00 Dr
10-10-2026 COLLECTION/123456 30,000.00 9,27,000.00 Dr
31-10-2026 Closing Balance 9,27,000.00 Dr
"""

FD = """DEMO SMALL FINANCE BANK
Fixed Deposit Advice
Account : 123456789012
Principal Amount: Rs. 1,00,000
Maturity Amount: Rs. 1,50,000
Total Interest Amt: Rs. 50,000
Value Date : 09-Nov-2026
Maturity Date: 09-Nov-2031
Rate of Interest: 8.25 %
Period of Deposit: 60 M
Repayment Account: 987654321098
Maturity Instructions: Renew Principal and Interest Interest Payment: Quarterly Compounding
Nominee Registered: Y
"""


def test_loan_statement_parses_and_reconciles():
    s = parse_position(LOAN)
    assert s["kind"] == "loan" and s["label"] == "Bank of Baroda loan ••1234"
    assert s["outstanding"] == 927_000_00 and s["emi"] == 30_000_00
    assert s["next_due"] == "2026-11-10" and s["emis_left"] == 32 and s["as_of"] == "2026-10-31"


def test_loan_statement_that_does_not_add_up_is_rejected():
    broken = LOAN.replace("31-10-2026 Closing Balance 9,27,000.00", "31-10-2026 Closing Balance 9,20,000.00")
    try:
        parse_position(broken)
    except PositionParseError:
        return
    raise AssertionError("a ledger that does not reconcile must not be stored")


def test_fd_advice_parses():
    s = parse_position(FD)
    assert s["kind"] == "deposit" and s["principal"] == 1_00_000_00 and s["maturity_amount"] == 1_50_000_00
    assert s["maturity_date"] == "2031-11-09" and s["renews"] is True


def test_ingest_stores_positions_and_never_reaches_the_transaction_parsers():
    docs = {"loan.pdf": LOAN, "fd.pdf": FD}

    class Src:
        def fetch(self, limit=100):
            return [type("R", (), {"source_id": n, "source_name": n, "data": t.encode()})()
                    for n, t in docs.items()]

    class Pass:
        def decrypt(self, d, h): return d
        def extract(self, d): return d.decode()

    class Reg:
        def parse(self, *a, **k): raise AssertionError("a position document reached the txn parser")

    with tempfile.TemporaryDirectory() as tmp:
        repo = SqliteTransactionRepository(str(Path(tmp) / "t.db"))
        run = lambda: IngestStatements(source=Src(), decryptor=Pass(), extractor=Pass(),
                                       parser_registry=Reg(), categorizer=None, repository=repo,
                                       position_parser=parse_position).run(account="x", hints={})
        r = run()
        assert r.positions == 2 and r.failed == 0 and r.inserted == 0 and r.ok
        run()                                   # the same documents again replace, never duplicate
        got = repo.positions()
        assert [p["kind"] for p in got] == ["loan", "deposit"]
        assert got[0]["outstanding"] == 927_000_00
        assert repo.all("x") == []              # nothing landed in transactions
