"""Ports — the abstract boundaries of the hexagon (Dependency Inversion).

Use-cases depend on these Protocols, never on concrete adapters. Any Gmail/PDF/SQLite/HTML
implementation that satisfies the shape is swappable (Liskov). New sources or renderers are added
by writing a new adapter, not by editing the core (Open/Closed).

Protocols (structural typing) are used instead of ABCs so adapters need not inherit anything —
they just have to match the signatures, which keeps coupling minimal.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Protocol, runtime_checkable

from .models import Statement, Transaction


@runtime_checkable
class RawStatement(Protocol):
    """A fetched-but-unparsed statement document (bytes + provenance)."""
    source_id: str
    source_name: str
    data: bytes


@runtime_checkable
class StatementSource(Protocol):
    """Fetches raw statement documents from somewhere (email, folder, upload)."""
    def fetch(self, limit: int = 100) -> List[RawStatement]: ...


@runtime_checkable
class Decryptor(Protocol):
    """Turns a possibly-password-protected document into readable bytes."""
    def decrypt(self, data: bytes, hints: Dict[str, Any]) -> bytes: ...


@runtime_checkable
class StatementParser(Protocol):
    """Parses decrypted document bytes into a Statement of Transactions.

    `can_parse` lets a registry pick the right parser (Open/Closed: add formats without editing
    existing parsers).
    """
    def can_parse(self, text: str) -> bool: ...
    def parse(self, text: str, *, account: str, source_id: str,
              source_name: str) -> Statement: ...


@runtime_checkable
class TextExtractor(Protocol):
    """Extracts plain text from decrypted document bytes (e.g. PDF -> text)."""
    def extract(self, data: bytes) -> str: ...


@runtime_checkable
class Categorizer(Protocol):
    """Assigns a category to a transaction (Strategy pattern — swap rule sets / ML models)."""
    def categorize(self, txn: Transaction) -> str: ...


@runtime_checkable
class TransactionRepository(Protocol):
    """Persists and queries transactions idempotently."""
    def save_statement(self, statement: Statement) -> Dict[str, int]: ...
    def all(self, account: Optional[str] = None) -> List[Transaction]: ...
    def stats(self) -> Dict[str, Any]: ...


@runtime_checkable
class Renderer(Protocol):
    """Renders an analytics dataset into an output artifact (HTML, JSON, …)."""
    def render(self, dataset: Dict[str, Any]) -> str: ...
