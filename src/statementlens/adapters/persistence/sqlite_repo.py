"""SqliteTransactionRepository — idempotent local persistence (TransactionRepository port).

Stores statements + transactions in SQLite (default ~/.statementlens/store.db, overridable). Money
is stored as integer minor units. Each transaction has a content hash (account|date|minor|dir|
balance|desc) with a UNIQUE constraint, so re-ingesting the same or overlapping statements never
double-stores. Reconstructs domain Transactions on read.
"""

from __future__ import annotations

import hashlib
import os
import sqlite3
import threading
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

from ...domain.models import Direction, Statement, Transaction
from ...domain.money import Money


def _default_path() -> str:
    return os.getenv("STATEMENTLENS_DB") or str(Path.home() / ".statementlens" / "store.db")


class SqliteTransactionRepository:
    """Thread-safe by giving each thread its own connection.

    SQLite connection objects may only be used on the thread that created them, and the local web
    server handles every request on a fresh thread — so a single shared connection raises
    ProgrammingError on the first HTTP request. One connection per thread (WAL mode makes concurrent
    readers cheap) is simpler and safer than serializing everything behind a lock.
    """

    def __init__(self, path: Optional[str] = None):
        self.path = path or _default_path()
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._init()

    @property
    def _conn(self) -> sqlite3.Connection:
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(self.path)
            conn.execute("PRAGMA journal_mode=WAL")
            # wait rather than fail if another thread holds a write lock
            conn.execute("PRAGMA busy_timeout=5000")
            self._local.conn = conn
        return conn

    def _init(self) -> None:
        self._conn.executescript("""
        CREATE TABLE IF NOT EXISTS statements(
            id INTEGER PRIMARY KEY AUTOINCREMENT, account TEXT, source_id TEXT, source_name TEXT,
            period_hint TEXT, txn_count INTEGER, UNIQUE(account, source_id, source_name));
        CREATE TABLE IF NOT EXISTS txns(
            id INTEGER PRIMARY KEY AUTOINCREMENT, account TEXT, iso_date TEXT, raw_date TEXT,
            description TEXT, merchant TEXT, minor INTEGER, currency TEXT, direction TEXT,
            balance_minor INTEGER, category TEXT, statement_id INTEGER, content_hash TEXT UNIQUE,
            provisional INTEGER DEFAULT 0);
        CREATE INDEX IF NOT EXISTS idx_txn_date ON txns(iso_date);
        CREATE INDEX IF NOT EXISTS idx_txn_merchant ON txns(merchant);

        -- User tag corrections and notes, kept SEPARATE from txns on purpose: re-ingesting a
        -- statement rewrites txns rows, and a correction must survive that. Storing the override
        -- inside txns would let a refresh silently revert the user's fix.
        CREATE TABLE IF NOT EXISTS tag_merchant(
            merchant_key TEXT PRIMARY KEY, tag TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS tag_txn(
            content_hash TEXT PRIMARY KEY, tag TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS txn_note(
            content_hash TEXT PRIMARY KEY, note TEXT NOT NULL);
        """)
        self._migrate()
        self._conn.commit()

    def _migrate(self) -> None:
        """Add columns that older databases predate. Users must not have to delete their store."""
        have = {r[1] for r in self._conn.execute("PRAGMA table_info(txns)")}
        if "provisional" not in have:
            self._conn.execute("ALTER TABLE txns ADD COLUMN provisional INTEGER DEFAULT 0")

    @staticmethod
    def _hash(t: Transaction, account: str) -> str:
        bal = t.balance.minor if t.balance is not None else None
        key = f"{account}|{t.raw_date}|{t.amount.minor}|{t.direction.value}|{bal}|{t.description.strip()}"
        return hashlib.sha256(key.encode()).hexdigest()

    def save_statement(self, statement: Statement) -> Dict[str, int]:
        cur = self._conn.execute(
            "INSERT OR IGNORE INTO statements(account,source_id,source_name,period_hint,txn_count)"
            " VALUES(?,?,?,?,?)",
            (statement.account, statement.source_id, statement.source_name,
             statement.period_hint, statement.count))
        row = self._conn.execute(
            "SELECT id FROM statements WHERE account=? AND source_id=? AND source_name=?",
            (statement.account, statement.source_id, statement.source_name)).fetchone()
        sid = row[0]
        inserted = duplicate = 0
        for t in statement.transactions:
            h = self._hash(t, statement.account)
            try:
                self._conn.execute(
                    "INSERT INTO txns(account,iso_date,raw_date,description,merchant,minor,currency,"
                    "direction,balance_minor,category,statement_id,content_hash,provisional)"
                    " VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (statement.account, t.txn_date.isoformat() if t.txn_date else None, t.raw_date,
                     t.description, t.merchant, t.amount.minor, t.amount.currency, t.direction.value,
                     t.balance.minor if t.balance is not None else None, t.category, sid, h,
                     1 if t.provisional else 0))
                inserted += 1
            except sqlite3.IntegrityError:
                duplicate += 1
        self._conn.commit()
        return {"inserted": inserted, "duplicate": duplicate}

    def all(self, account: Optional[str] = None) -> List[Transaction]:
        q = ("SELECT iso_date,raw_date,description,merchant,minor,currency,direction,"
             "balance_minor,category,content_hash,COALESCE(provisional,0) FROM txns")
        params: tuple = ()
        if account:
            q += " WHERE account=?"; params = (account,)
        q += " ORDER BY iso_date, id"
        out: List[Transaction] = []
        for r in self._conn.execute(q, params).fetchall():
            iso, raw, desc, merch, minor, cur, dirn, bal, cat, chash, prov = r
            out.append(Transaction(
                txn_date=date.fromisoformat(iso) if iso else None,
                description=desc or "", amount=Money(minor, cur or "INR"),
                direction=Direction(dirn), merchant=merch or "",
                balance=Money(bal, cur or "INR") if bal is not None else None,
                category=cat, raw_date=raw or "",
                # the content hash IS the stable row identity: it survives re-ingest, so a tag
                # correction keyed to it survives a statement refresh
                source_ref=chash or "",
                provisional=bool(prov)))
        return out

    def purge_provisional(self, account: str, ranges) -> int:
        """Delete provisional rows inside statement-covered date ranges. Returns rows removed.

        Called after a statement import: once the bank's settled record covers a period, the
        alert-derived rows for that period are noise that would double-count.
        """
        removed = 0
        for start, end in ranges:
            cur = self._conn.execute(
                "DELETE FROM txns WHERE account=? AND COALESCE(provisional,0)=1"
                " AND iso_date IS NOT NULL AND iso_date BETWEEN ? AND ?",
                (account, start.isoformat(), end.isoformat()))
            removed += cur.rowcount or 0
        self._conn.commit()
        return removed

    # -- tag corrections + notes -------------------------------------------
    def load_tags(self):
        """Rehydrate the user's corrections and notes into a TagStore."""
        from ...usecases.tagging import TagStore
        return TagStore(
            by_merchant=dict(self._conn.execute("SELECT merchant_key,tag FROM tag_merchant")),
            by_ref=dict(self._conn.execute("SELECT content_hash,tag FROM tag_txn")),
            notes=dict(self._conn.execute("SELECT content_hash,note FROM txn_note")))

    def save_tags(self, store) -> Dict[str, int]:
        """Persist a TagStore. Full replace — the store is the source of truth for corrections."""
        c = self._conn
        c.execute("DELETE FROM tag_merchant"); c.execute("DELETE FROM tag_txn")
        c.execute("DELETE FROM txn_note")
        c.executemany("INSERT INTO tag_merchant(merchant_key,tag) VALUES(?,?)",
                      list(store.by_merchant.items()))
        c.executemany("INSERT INTO tag_txn(content_hash,tag) VALUES(?,?)", list(store.by_ref.items()))
        c.executemany("INSERT INTO txn_note(content_hash,note) VALUES(?,?)", list(store.notes.items()))
        c.commit()
        return {"merchants": len(store.by_merchant), "txns": len(store.by_ref),
                "notes": len(store.notes)}

    def correct_tag(self, *, tag: str, merchant: Optional[str] = None,
                    content_hash: Optional[str] = None) -> None:
        """Apply and persist one correction. Merchant-wide unless a content_hash is given."""
        store = self.load_tags()
        if content_hash:
            store.correct_one(content_hash, tag)
        elif merchant:
            # pass the merchant's rows so a stale single-row override can't shadow this fix
            refs = [r[0] for r in self._conn.execute(
                "SELECT content_hash FROM txns WHERE LOWER(TRIM(merchant))=?",
                (merchant.strip().lower(),))]
            store.correct_merchant(merchant, tag, member_refs=refs)
        else:
            raise ValueError("correct_tag needs either merchant= or content_hash=")
        self.save_tags(store)

    def correct_many(self, *, tag: str, content_hashes) -> int:
        """Apply one tag to an explicit set of transactions in a single write.

        Per-row rather than merchant-wide on purpose: the user picked exactly these rows in the
        multi-select, so we honour that selection instead of inferring a broader rule they did not
        ask for. Returns the number of rows tagged.
        """
        refs = [h for h in content_hashes if h]
        if not refs:
            return 0
        store = self.load_tags()
        for ref in refs:
            store.correct_one(ref, tag)
        self.save_tags(store)
        return len(refs)

    def set_note(self, content_hash: str, note: str) -> None:
        store = self.load_tags()
        store.add_note(content_hash, note)
        self.save_tags(store)

    def stats(self) -> Dict[str, Any]:
        s = self._conn.execute("SELECT COUNT(*) FROM statements").fetchone()[0]
        n = self._conn.execute("SELECT COUNT(*) FROM txns").fetchone()[0]
        span = self._conn.execute(
            "SELECT MIN(iso_date),MAX(iso_date) FROM txns WHERE iso_date IS NOT NULL").fetchone()
        return {"statements": s, "transactions": n, "date_min": span[0], "date_max": span[1]}
