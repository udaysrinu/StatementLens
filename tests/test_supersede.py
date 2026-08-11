"""Checks for provisional alert rows and statement supersession.

This is the correctness core: get it wrong and every total is inflated by double-counted swipes, or a
real settled transaction silently disappears. Both failures are tested for explicitly.
"""

import tempfile
from datetime import date
from pathlib import Path

from statementlens.adapters.persistence.sqlite_repo import SqliteTransactionRepository
from statementlens.domain.models import Direction, Statement, Transaction
from statementlens.domain.money import Money
from statementlens.usecases.supersede import (
    Coverage, coverage_from_transactions, is_covered, live_tail, merge_coverages, supersede,
)


def txn(day, rupees, *, provisional=False, merchant="Shop", month=7):
    return Transaction(txn_date=date(2026, month, day), description=f"{merchant} pay",
                       amount=Money.of(rupees, "INR"), direction=Direction.DEBIT,
                       merchant=merchant, raw_date=f"{day:02d}-0{month}-26",
                       source_ref=f"{'alert' if provisional else 'stmt'}-{month}-{day}-{rupees}",
                       provisional=provisional)


def test_provisional_rows_inside_statement_coverage_are_dropped():
    settled = [txn(1, 100), txn(28, 500)]                 # statement covers 1–28 Jul
    alerts = [txn(10, 250, provisional=True)]             # same swipe, already in the statement
    r = supersede(settled + alerts, account="A")
    assert len(r.kept) == 2 and len(r.dropped) == 1
    assert all(not t.provisional for t in r.kept)


def test_provisional_rows_after_the_last_statement_survive():
    """This is the whole feature: the live tail is what makes the dashboard current."""
    settled = [txn(1, 100), txn(28, 500)]
    alerts = [txn(30, 900, provisional=True), txn(31, 120, provisional=True)]
    r = supersede(settled + alerts, account="A")
    assert len(r.dropped) == 0
    assert len(live_tail(r.kept)) == 2


def test_nothing_is_dropped_when_no_statement_exists_yet():
    alerts = [txn(5, 100, provisional=True), txn(6, 200, provisional=True)]
    r = supersede(alerts, account="A")
    assert r.dropped == [] and len(r.kept) == 2


def test_a_settled_row_is_never_dropped():
    # the dangerous failure: deleting the bank's own record
    settled = [txn(10, 100)]
    r = supersede(settled, account="A")
    assert r.kept == settled and r.dropped == []


def test_totals_do_not_double_count_after_supersession():
    settled = [txn(11, 1508)]                              # statement row
    alert = [txn(11, 50, provisional=True)]                # the pre-auth for the same swipe
    r = supersede(settled + alert, account="A")
    assert sum(t.amount.minor for t in r.kept) == 150800    # not 150800 + 5000


def test_coverage_is_inferred_from_transaction_dates():
    cov = coverage_from_transactions([txn(3, 10), txn(27, 20)], "A")
    assert cov == Coverage("A", date(2026, 7, 3), date(2026, 7, 27))


def test_coverage_is_none_without_dated_rows():
    undated = Transaction(txn_date=None, description="x", amount=Money.of(1, "INR"),
                          direction=Direction.DEBIT)
    assert coverage_from_transactions([undated], "A") is None


def test_overlapping_coverages_merge():
    merged = merge_coverages([
        Coverage("A", date(2026, 1, 1), date(2026, 1, 31)),
        Coverage("A", date(2026, 1, 25), date(2026, 2, 28)),   # overlaps
        Coverage("A", date(2026, 6, 1), date(2026, 6, 30)),    # separate
    ])
    assert merged["A"] == [(date(2026, 1, 1), date(2026, 2, 28)),
                           (date(2026, 6, 1), date(2026, 6, 30))]


def test_coverage_is_per_account():
    merged = merge_coverages([
        Coverage("SBI", date(2026, 1, 1), date(2026, 1, 31)),
        Coverage("CARD", date(2026, 1, 1), date(2026, 1, 31)),
    ])
    assert set(merged) == {"SBI", "CARD"}
    # a card statement must not supersede a bank account's alerts
    alerts = [txn(10, 500, provisional=True)]
    r = supersede(alerts, coverage=merged, account="OTHER")
    assert r.dropped == []


def test_is_covered_boundaries_are_inclusive():
    ranges = [(date(2026, 7, 1), date(2026, 7, 31))]
    assert is_covered(date(2026, 7, 1), ranges)
    assert is_covered(date(2026, 7, 31), ranges)
    assert not is_covered(date(2026, 8, 1), ranges)
    assert not is_covered(None, ranges)


# --- persistence + end-to-end ------------------------------------------------

def _repo(tmp):
    return SqliteTransactionRepository(str(Path(tmp) / "t.db"))


def test_provisional_flag_round_trips_through_sqlite():
    with tempfile.TemporaryDirectory() as tmp:
        r = _repo(tmp)
        r.save_statement(Statement("A", "s", "f.pdf", "p",
                                   (txn(5, 100), txn(6, 200, provisional=True))))
        loaded = {t.amount.minor: t.provisional for t in r.all("A")}
        assert loaded == {10000: False, 20000: True}


def test_purge_provisional_removes_only_covered_alert_rows():
    with tempfile.TemporaryDirectory() as tmp:
        r = _repo(tmp)
        r.save_statement(Statement("A", "s", "f.pdf", "p", (
            txn(10, 100, provisional=True),      # inside the purge range
            txn(30, 200, provisional=True),      # outside it
            txn(10, 300),                        # settled, inside — must survive
        )))
        removed = r.purge_provisional("A", [(date(2026, 7, 1), date(2026, 7, 28))])
        assert removed == 1
        left = r.all("A")
        assert sorted(t.amount.minor for t in left) == [20000, 30000]


def test_older_databases_gain_the_provisional_column():
    """A user must never have to delete their store for a schema change."""
    import sqlite3
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "legacy.db"
        con = sqlite3.connect(db)
        con.executescript("""
            CREATE TABLE statements(id INTEGER PRIMARY KEY AUTOINCREMENT, account TEXT,
                source_id TEXT, source_name TEXT, period_hint TEXT, txn_count INTEGER,
                UNIQUE(account, source_id, source_name));
            CREATE TABLE txns(id INTEGER PRIMARY KEY AUTOINCREMENT, account TEXT, iso_date TEXT,
                raw_date TEXT, description TEXT, merchant TEXT, minor INTEGER, currency TEXT,
                direction TEXT, balance_minor INTEGER, category TEXT, statement_id INTEGER,
                content_hash TEXT UNIQUE);
            INSERT INTO txns(account,iso_date,minor,currency,direction,content_hash)
                VALUES('A','2026-07-01',5000,'INR','debit','h1');
        """)
        con.commit(); con.close()

        repo = SqliteTransactionRepository(str(db))      # must migrate, not crash
        rows = repo.all("A")
        assert len(rows) == 1 and rows[0].provisional is False


def test_statement_ingest_supersedes_stored_alerts_end_to_end():
    """The real flow: alerts arrive first, the statement lands later and clears them."""
    from statementlens.usecases.ingest import IngestStatements

    class FakeSource:
        def fetch(self, limit=100):
            return [type("R", (), {"source_id": "s1", "source_name": "stmt.pdf",
                                   "data": b"x"})()]

    class Passthrough:
        def decrypt(self, data, hints):
            return data

        def extract(self, data):
            return "text"

    class OneRowParser:
        def can_parse(self, text):
            return True

        def parse(self, text, *, account, source_id, source_name):
            return Statement(account, source_id, source_name, "p", (txn(11, 1508),))

    class Registry:
        def parse(self, text, **kw):
            return OneRowParser().parse(text, **kw)

    class Cat:
        def categorize(self, t):
            return "shopping"

    with tempfile.TemporaryDirectory() as tmp:
        repo = _repo(tmp)
        # alerts land first — the pre-auth and an unrelated later swipe
        repo.save_statement(Statement("A", "alerts", "alerts", "live", (
            txn(11, 50, provisional=True), txn(30, 700, provisional=True))))
        assert len(repo.all("A")) == 2

        result = IngestStatements(source=FakeSource(), decryptor=Passthrough(),
                                  extractor=Passthrough(), parser_registry=Registry(),
                                  categorizer=Cat(), repository=repo).run(account="A", hints={})
        assert result.inserted == 1
        assert result.superseded == 1                     # the 11 Jul pre-auth was cleared
        left = repo.all("A")
        assert sorted(t.amount.minor for t in left) == [70000, 150800]
        assert sum(t.amount.minor for t in left) == 220800   # no double count
