"""A statement that arrives twice under different names must not double the store.

Real case: HDFC mailed the same card statements twice with different filenames, plus a consolidated
copy. The text extracted slightly differently each time, so every content hash differed, the filename
check did not apply, and 399 rows went in twice — HDFC spend read ₹10.3L against a real ₹5.2L.
"""
import tempfile
from datetime import date
from pathlib import Path

from statementlens.adapters.persistence.sqlite_repo import SqliteTransactionRepository
from statementlens.domain.models import Direction, Statement, Transaction
from statementlens.domain.money import Money
from statementlens.usecases.ingest import IngestStatements


def _t(day, rupees, desc, month=9, direction=Direction.DEBIT):
    return Transaction(txn_date=date(2025, month, day), description=desc, merchant=desc,
                       amount=Money(rupees * 100, "INR"), direction=direction)


def _ingest(repo, docs):
    """docs: [(filename, (txn, ...))] fed through the real use-case with stub I/O."""
    class Src:
        def fetch(self, limit=100):
            return [type("R", (), {"source_id": n, "source_name": n, "data": n.encode()})()
                    for n, _ in docs]

    class Pass:
        def decrypt(self, d, h): return d
        def extract(self, d): return d.decode()

    by_name = dict(docs)

    class Reg:
        def parse(self, text, *, account, source_id, source_name):
            return Statement(account, source_id, source_name, "p", tuple(by_name[source_name]))

    class Cat:
        def categorize(self, t): return "shopping"

    return IngestStatements(source=Src(), decryptor=Pass(), extractor=Pass(), parser_registry=Reg(),
                            categorizer=Cat(), repository=repo).run(account="HDFC ••42", hints={},
                                                                    split_accounts=False)


SEPT = (_t(1, 231, "PayU*Swiggy Limited Bangalore"), _t(2, 500, "Myntra Designs Pvt Ltd"),
        _t(2, 934, "1% Swiggy Cashback (Ref# ST2524600840)", direction=Direction.CREDIT))
# the same statement, re-sent under another name, its text extracted differently
SEPT_RESENT = (_t(1, 231, "PayU*Swiggy LimitedBangalore"), _t(2, 500, "Myntra Designs PvtLtd"),
               _t(2, 934, "1% Swiggy Cashback", direction=Direction.CREDIT))


def test_a_resent_statement_with_different_text_adds_nothing():
    with tempfile.TemporaryDirectory() as tmp:
        repo = SqliteTransactionRepository(str(Path(tmp) / "t.db"))
        _ingest(repo, [("x_01-10-2025.PDF", SEPT)])
        r = _ingest(repo, [("x_01-10-2025_93.pdf", SEPT_RESENT)])
        assert len(repo.all("HDFC ••42")) == 3
        assert r.inserted == 0 and r.duplicate == 3


def test_a_consolidated_file_contributes_only_its_new_months():
    october = (_t(3, 120, "BUNDL TECHNOLOGIES", month=10),)
    with tempfile.TemporaryDirectory() as tmp:
        repo = SqliteTransactionRepository(str(Path(tmp) / "t.db"))
        _ingest(repo, [("x_01-10-2025.PDF", SEPT)])
        _ingest(repo, [("x_consolidated.PDF", SEPT_RESENT + october)])
        rows = repo.all("HDFC ••42")
        assert len(rows) == 4
        assert sum(1 for t in rows if t.txn_date.month == 10) == 1


def test_two_genuine_identical_charges_on_one_day_both_survive():
    twice = (_t(5, 2, "IRCTC CONVENIENCE FEE"), _t(5, 2, "IRCTC CONVENIENCE FEE B"))
    with tempfile.TemporaryDirectory() as tmp:
        repo = SqliteTransactionRepository(str(Path(tmp) / "t.db"))
        _ingest(repo, [("a.PDF", twice)])
        assert len(repo.all("HDFC ••42")) == 2
        # and a re-sent copy of that statement still adds nothing
        _ingest(repo, [("a_2.PDF", twice)])
        assert len(repo.all("HDFC ••42")) == 2
