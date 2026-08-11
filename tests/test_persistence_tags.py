"""Checks that user tag corrections and notes persist — and survive a statement re-ingest.

The re-ingest case is the important one: if refreshing statements silently reverts a fix the user
made, they stop trusting every number in the app.
"""

import tempfile
from datetime import date
from pathlib import Path

from statementlens.adapters.persistence.sqlite_repo import SqliteTransactionRepository
from statementlens.domain.models import Direction, Statement, Transaction
from statementlens.domain.money import Money


def _stmt(account="SBI", n=2):
    txns = tuple(
        Transaction(txn_date=date(2026, 1, i + 1), description=f"UPI/SHOP{i}/PAY",
                    amount=Money.of(100 * (i + 1), "INR"), direction=Direction.DEBIT,
                    merchant="Shop A" if i == 0 else "Shop B",
                    category="untagged", raw_date=f"0{i+1}-01-26")
        for i in range(n))
    return Statement(account, "src1", "stmt.pdf", "012026", txns)


def _repo(tmp):
    return SqliteTransactionRepository(str(Path(tmp) / "t.db"))


def test_source_ref_is_populated_so_corrections_can_be_keyed():
    with tempfile.TemporaryDirectory() as tmp:
        r = _repo(tmp)
        r.save_statement(_stmt())
        refs = [t.source_ref for t in r.all()]
        assert all(refs) and len(set(refs)) == 2   # present and unique per row


def test_merchant_correction_persists_across_new_connections():
    with tempfile.TemporaryDirectory() as tmp:
        db = str(Path(tmp) / "t.db")
        r1 = SqliteTransactionRepository(db)
        r1.save_statement(_stmt())
        r1.correct_tag(tag="grocery", merchant="Shop A")
        # a brand-new connection must see the correction
        r2 = SqliteTransactionRepository(db)
        assert r2.load_tags().by_merchant["shop a"] == "grocery"


def test_correction_survives_reingest_of_the_same_statement():
    with tempfile.TemporaryDirectory() as tmp:
        r = _repo(tmp)
        r.save_statement(_stmt())
        target = r.all()[0]
        r.correct_tag(tag="rent", content_hash=target.source_ref)
        r.set_note(target.source_ref, "january rent")
        # re-ingest: rows are re-offered, dedup keeps them, corrections must NOT be lost
        counts = r.save_statement(_stmt())
        assert counts["duplicate"] == 2 and counts["inserted"] == 0
        store = r.load_tags()
        assert store.by_ref[target.source_ref] == "rent"
        assert store.notes[target.source_ref] == "january rent"


def test_notes_can_be_cleared():
    with tempfile.TemporaryDirectory() as tmp:
        r = _repo(tmp)
        r.save_statement(_stmt())
        ref = r.all()[0].source_ref
        r.set_note(ref, "temp")
        assert r.load_tags().notes.get(ref) == "temp"
        r.set_note(ref, "")
        assert ref not in r.load_tags().notes


def test_correct_tag_requires_a_target():
    with tempfile.TemporaryDirectory() as tmp:
        r = _repo(tmp)
        try:
            r.correct_tag(tag="grocery")
        except ValueError:
            return
        raise AssertionError("expected ValueError when neither merchant nor hash is given")


def test_dataset_applies_persisted_corrections():
    from statementlens.usecases.analytics import build_dataset
    with tempfile.TemporaryDirectory() as tmp:
        r = _repo(tmp)
        r.save_statement(_stmt())
        r.correct_tag(tag="grocery", merchant="Shop A")
        ds = build_dataset(r.all(), account="SBI", tags=r.load_tags())
        tags = {row["m"]: row["c"] for row in ds["txns"]}
        assert tags["Shop A"] == "grocery"
        assert tags["Shop B"] == "untagged"      # untouched merchants stay auto-tagged
