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


# --- coverage must never claim a month with no statement rows -----------------

def test_a_gap_month_between_two_statements_is_not_claimed():
    """The data-loss bug: coverage was min(date)..max(date), one hull over everything.

    With statements for January and March, the hull covered February too, so February's alert row —
    the ONLY record of that spend — was deleted as "superseded" by statements that never covered it.
    """
    settled = [txn(10, 100, month=1), txn(20, 100, month=1),
               txn(5, 100, month=3), txn(25, 100, month=3)]
    feb_alert = txn(14, 500, provisional=True, month=2)
    r = supersede(settled + [feb_alert], account="A")
    assert r.dropped == [], "February had no statement, so its alert must survive"
    assert feb_alert in r.kept


def test_a_carry_forward_row_does_not_stretch_coverage_backwards():
    """One out-of-cycle row used to drag the hull back weeks and delete alerts in between."""
    stmt = [txn(2, 100, month=4),            # a carry-forward / late-posted line
            txn(3, 100, month=6), txn(17, 100, month=6), txn(28, 100, month=6)]
    may_alert = txn(9, 700, provisional=True, month=5)
    apr_alert = txn(20, 300, provisional=True, month=4)
    r = supersede(stmt + [may_alert, apr_alert], account="A")
    kept_refs = {t.source_ref for t in r.kept}
    assert may_alert.source_ref in kept_refs, "May has no statement rows at all"
    # April DOES have a row, so that month is legitimately covered
    assert apr_alert.source_ref not in kept_refs


def test_adjacent_months_still_merge_into_one_range():
    from statementlens.usecases.supersede import coverage_blocks, merge_coverages
    rows = [txn(15, 100, month=1), txn(15, 100, month=2), txn(15, 100, month=3)]
    ranges = merge_coverages(coverage_blocks(rows, "A"))["A"]
    assert len(ranges) == 1, "a contiguous run must behave as one range"
    # the newest month stops at its last settled row, so later activity stays the live tail
    assert ranges[0][0] == date(2026, 1, 1) and ranges[0][1] == date(2026, 3, 15)


def test_earlier_months_cover_their_quiet_days_but_the_newest_stops_at_its_last_row():
    from statementlens.usecases.supersede import coverage_blocks
    blocks = coverage_blocks([txn(15, 100, month=2), txn(10, 100, month=4)], "A")
    assert len(blocks) == 2
    # February is not the newest month, so it is covered end-to-end including quiet days
    assert blocks[0].start == date(2026, 2, 1) and blocks[0].end == date(2026, 2, 28)
    assert blocks[0].contains(date(2026, 2, 3))
    # April IS the newest, so coverage stops at the last settled row — the rest is the live tail
    assert blocks[1].end == date(2026, 4, 10)
    assert not blocks[1].contains(date(2026, 4, 25))


def test_december_month_end_does_not_roll_into_next_year():
    from statementlens.usecases.supersede import coverage_blocks
    rows = [Transaction(txn_date=date(2025, 12, 5), description="x",
                        amount=Money.of(100, "INR"), direction=Direction.DEBIT)]
    # December as the ONLY (and newest) month clamps to its last row, not the 31st
    assert coverage_blocks(rows, "A")[0].end == date(2025, 12, 5)
    # as an earlier month it covers to the 31st without rolling into January
    rows2 = rows + [Transaction(txn_date=date(2026, 2, 3), description="x",
                               amount=Money.of(100, "INR"), direction=Direction.DEBIT)]
    assert coverage_blocks(rows2, "A")[0].end == date(2025, 12, 31)


def test_ingest_purge_uses_month_blocks_not_the_hull():
    """End-to-end: a statement with a carry-forward row must not purge the gap month from the store."""
    from statementlens.usecases.ingest import IngestStatements

    class Src:
        def fetch(self, limit=100):
            return [type("R", (), {"source_id": "s1", "source_name": "s.pdf", "data": b"x"})()]

    class Pass:
        def decrypt(self, d, h): return d
        def extract(self, d): return "t"

    class Reg:
        def parse(self, text, *, account, source_id, source_name):
            return Statement(account, source_id, source_name, "p",
                             (txn(2, 100, month=4), txn(10, 100, month=6)))

    class Cat:
        def categorize(self, t): return "shopping"

    with tempfile.TemporaryDirectory() as tmp:
        repo = _repo(tmp)
        repo.save_statement(Statement("A", "alerts", "alerts", "live",
                                      (txn(9, 700, provisional=True, month=5),)))
        IngestStatements(source=Src(), decryptor=Pass(), extractor=Pass(),
                         parser_registry=Reg(), categorizer=Cat(),
                         repository=repo).run(account="A", hints={})
        left = {(t.txn_date.month, t.provisional) for t in repo.all("A")}
        assert (5, True) in left, "the May alert was in no statement's month and must survive"


def test_reingesting_the_same_file_after_a_relabel_does_not_double_the_store():
    """The bug that doubled a real 2,216-row store to 5,183.

    Row-level dedup hashes the ACCOUNT label and a per-source id. Gmail uses the message id while the
    folder source uses a content hash, and `relabel` changes the label — so the same statement seen
    from a different source, or after a relabel, hashed differently and every row was inserted again.
    Statement-level dedup on the filename is what actually stops it.
    """
    from statementlens.usecases.ingest import IngestStatements

    class Src:
        """Same FILE, but a different source_id each run — as Gmail vs folder would give."""
        def __init__(self, sid):
            self.sid = sid

        def fetch(self, limit=100):
            return [type("R", (), {"source_id": self.sid, "source_name": "stmt.pdf",
                                   "data": b"x"})()]

    class Pass:
        def decrypt(self, d, h): return d
        def extract(self, d): return "text"

    class Reg:
        def __init__(self, account):
            self.account = account

        def parse(self, text, *, account, source_id, source_name):
            return Statement(self.account, source_id, source_name, "p",
                             (txn(11, 1508), txn(12, 200)))

    class Cat:
        def categorize(self, t): return "shopping"

    def run(repo, sid, account):
        return IngestStatements(source=Src(sid), decryptor=Pass(), extractor=Pass(),
                                parser_registry=Reg(account), categorizer=Cat(),
                                repository=repo).run(account=account, hints={},
                                                     split_accounts=False)

    with tempfile.TemporaryDirectory() as tmp:
        repo = _repo(tmp)
        first = run(repo, "gmail-msg-id", "Merged")
        assert first.inserted == 2
        # a different source_id AND a different account label — previously inserted 2 more rows
        second = run(repo, "folder-content-hash", "SBI ••5111")
        assert second.inserted == 0, "the same file must never be stored twice"
        assert second.duplicate == 2
        assert len(repo.all()) == 2
