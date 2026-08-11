"""Core domain entities: Transaction, Statement, and supporting enums.

These are plain, framework-agnostic data structures — no I/O, no persistence, no rendering. Every
adapter (parsers, repositories, renderers) speaks in terms of these, which keeps the domain the
stable center of the hexagon.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional

from .money import Money


class Direction(str, Enum):
    """Which way money moved relative to the account owner."""
    DEBIT = "debit"    # money out
    CREDIT = "credit"  # money in


@dataclass(frozen=True)
class Transaction:
    """One statement line item. `amount` is always a positive Money; `direction` gives the sign."""
    txn_date: Optional[date]
    description: str
    amount: Money
    direction: Direction
    merchant: str = ""
    balance: Optional[Money] = None
    category: Optional[str] = None
    raw_date: str = ""            # the date exactly as printed, for provenance
    source_ref: str = ""          # statement id / hash for traceability
    #: True when this row came from a transaction-ALERT email rather than a statement. Alerts arrive
    #: instantly but are lossy and can describe an authorisation that never settles, so the statement
    #: covering the same period always wins. See `usecases.supersede`.
    provisional: bool = False

    @property
    def is_debit(self) -> bool:
        return self.direction is Direction.DEBIT

    @property
    def month(self) -> str:
        return self.txn_date.strftime("%Y-%m") if self.txn_date else ""

    def with_category(self, category: str) -> "Transaction":
        """Return a copy tagged with a category (frozen -> return new instance)."""
        return Transaction(
            self.txn_date, self.description, self.amount, self.direction, self.merchant,
            self.balance, category, self.raw_date, self.source_ref, self.provisional)


@dataclass(frozen=True)
class Statement:
    """A parsed statement: provenance metadata plus its transactions."""
    account: str
    source_id: str                # e.g. gmail message id
    source_name: str              # e.g. pdf filename
    period_hint: str              # best-effort period label
    transactions: tuple[Transaction, ...] = field(default_factory=tuple)

    @property
    def count(self) -> int:
        return len(self.transactions)
