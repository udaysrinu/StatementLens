"""Composition root — wires adapters into use-cases (the only place that knows concrete classes).

Everything else in the package depends on ports/domain; App is where the hexagon is assembled.
Swap an adapter here (e.g. a folder source instead of Gmail) without touching any use-case.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from .adapters.categorize.keyword_categorizer import KeywordCategorizer
from .adapters.crypto.pdf_decryptor import PdfDecryptor, PdfTextExtractor
from .adapters.parsers.bank_parser import SavingsStatementParser
from .adapters.parsers.card_parser import CardStatementParser
from .adapters.parsers.registry import ParserRegistry
from .adapters.persistence.sqlite_repo import SqliteTransactionRepository
from .adapters.render.app_shell import AppShellRenderer
from .usecases.analytics import build_dataset
from .usecases.ingest import IngestResult, IngestStatements


class App:
    @classmethod
    def from_folder(cls, folders, *, db_path: Optional[str] = None,
                    recursive: bool = True, pattern: Optional[str] = None) -> "App":
        """Wire the app to read statements from local folders — no Gmail, no OAuth, no approval gate.

        This is the ungated onboarding path: `gmail.readonly` is a Google *restricted* scope, so the
        Gmail adapter is capped at 100 users until a CASA assessment passes. Folder/upload import has
        no such limit and works for any bank in any country.
        """
        from .adapters.sources.folder_source import FolderStatementSource
        return cls(db_path=db_path,
                   source=FolderStatementSource(folders, recursive=recursive, pattern=pattern))

    def __init__(self, *, db_path: Optional[str] = None, source=None,
                 own_names: Optional[list] = None):
        # own_names drives self-transfer exclusion: money between the user's own accounts is
        # neither income nor spending, so counting both legs inflates every total
        self.own_names = own_names or []
        self.repo = SqliteTransactionRepository(db_path)
        # The sync log lives beside the database so it stays writable if the DB is the problem.
        # Derived from the db FILENAME, not just its folder — `with_name()` alone would give every
        # database in a directory the same log, so two accounts would clobber each other's history.
        from .usecases.refresh import SyncLog
        db = Path(self.repo.path)
        self.sync_log = SyncLog(str(db.with_name(f"{db.stem}.sync.json")))
        self.categorizer = KeywordCategorizer()
        self.parsers = (ParserRegistry()
                        .register(SavingsStatementParser())
                        .register(CardStatementParser()))
        self.decryptor = PdfDecryptor()
        self.extractor = PdfTextExtractor()
        self._source = source  # inject a StatementSource (e.g. GmailStatementSource) to ingest

    def ingest(self, *, account: str, hints: Dict[str, Any], limit: int = 100) -> IngestResult:
        if self._source is None:
            raise RuntimeError("no StatementSource configured; pass source= to App(...)")
        return IngestStatements(
            source=self._source, decryptor=self.decryptor, extractor=self.extractor,
            parser_registry=self.parsers, categorizer=self.categorizer,
            repository=self.repo).run(account=account, hints=hints, limit=limit)

    def dataset(self, account: str, currency: str = "INR") -> Dict[str, Any]:
        txns = self.repo.all(account)
        # user corrections are loaded from the DB, so a fixed tag survives restarts and re-ingests
        return build_dataset(txns, account=account, currency=currency,
                             tags=self.repo.load_tags(), own_names=self.own_names,
                             sync=self.sync_log.status())

    def correct_tag(self, *, tag: str, merchant: Optional[str] = None,
                    content_hash: Optional[str] = None) -> None:
        """Persist a user tag correction (merchant-wide, or a single transaction)."""
        self.repo.correct_tag(tag=tag, merchant=merchant, content_hash=content_hash)

    def set_note(self, content_hash: str, note: str) -> None:
        """Persist a free-text note on one transaction."""
        self.repo.set_note(content_hash, note)

    def render(self, account: str, out_path: str, currency: str = "INR") -> str:
        html = AppShellRenderer().render(self.dataset(account, currency))
        p = Path(out_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(html, encoding="utf-8")
        return str(p.resolve())

    def stats(self) -> Dict[str, Any]:
        return self.repo.stats()

    def refresh(self, *, account: str, hints: Dict[str, Any], force: bool = False,
                limit: int = 100):
        """Re-run ingest and record the outcome so a broken connector is visible, not silent."""
        from .usecases.refresh import RefreshStatements
        return RefreshStatements(
            lambda: self.ingest(account=account, hints=hints, limit=limit),
            log=self.sync_log).run(force=force)

    def sync_status(self) -> Dict[str, Any]:
        """Freshness for the UI — "updated 36 mins ago", or why it hasn't."""
        return self.sync_log.status()
