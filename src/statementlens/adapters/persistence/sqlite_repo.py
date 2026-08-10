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
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

from ...domain.models import Direction, Statement, Transaction
from ...domain.money import Money


def _default_path() -> str:
    return os.getenv("STATEMENTLENS_DB") or str(Path.home() / ".statementlens" / "store.db")


class SqliteTransactionRepository:
    def __init__(self, path: Optional[str] = None):
        self.path = path or _default_path()
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._init()

    def _init(self) -> None:
        self._conn.executescript("""
        CREATE TABLE IF NOT EXISTS statements(
            id INTEGER PRIMARY KEY AUTOINCREMENT, account TEXT, source_id TEXT, source_name TEXT,
            period_hint TEXT, txn_count INTEGER, UNIQUE(account, source_id, source_name));
        CREATE TABLE IF NOT EXISTS txns(
            id INTEGER PRIMARY KEY AUTOINCREMENT, account TEXT, iso_date TEXT, raw_date TEXT,
            description TEXT, merchant TEXT, minor INTEGER, currency TEXT, direction TEXT,
            balance_minor INTEGER, category TEXT, statement_id INTEGER, content_hash TEXT UNIQUE);
        CREATE INDEX IF NOT EXISTS idx_txn_date ON txns(iso_date);
        CREATE INDEX IF NOT EXISTS idx_txn_merchant ON txns(merchant);
        """)
        self._conn.commit()

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
                    "direction,balance_minor,category,statement_id,content_hash) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                    (statement.account, t.txn_date.isoformat() if t.txn_date else None, t.raw_date,
                     t.description, t.merchant, t.amount.minor, t.amount.currency, t.direction.value,
                     t.balance.minor if t.balance is not None else None, t.category, sid, h))
                inserted += 1
            except sqlite3.IntegrityError:
                duplicate += 1
        self._conn.commit()
        return {"inserted": inserted, "duplicate": duplicate}

    def all(self, account: Optional[str] = None) -> List[Transaction]:
        q = ("SELECT iso_date,raw_date,description,merchant,minor,currency,direction,"
             "balance_minor,category FROM txns")
        params: tuple = ()
        if account:
            q += " WHERE account=?"; params = (account,)
        q += " ORDER BY iso_date, id"
        out: List[Transaction] = []
        for r in self._conn.execute(q, params).fetchall():
            iso, raw, desc, merch, minor, cur, dirn, bal, cat = r
            out.append(Transaction(
                txn_date=date.fromisoformat(iso) if iso else None,
                description=desc or "", amount=Money(minor, cur or "INR"),
                direction=Direction(dirn), merchant=merch or "",
                balance=Money(bal, cur or "INR") if bal is not None else None,
                category=cat, raw_date=raw or ""))
        return out

    def stats(self) -> Dict[str, Any]:
        s = self._conn.execute("SELECT COUNT(*) FROM statements").fetchone()[0]
        n = self._conn.execute("SELECT COUNT(*) FROM txns").fetchone()[0]
        span = self._conn.execute(
            "SELECT MIN(iso_date),MAX(iso_date) FROM txns WHERE iso_date IS NOT NULL").fetchone()
        return {"statements": s, "transactions": n, "date_min": span[0], "date_max": span[1]}
