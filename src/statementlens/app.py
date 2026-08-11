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

    def __init__(self, *, db_path: Optional[str] = None, source=None):
        self.repo = SqliteTransactionRepository(db_path)
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
        return build_dataset(txns, account=account, currency=currency)

    def render(self, account: str, out_path: str, currency: str = "INR") -> str:
        html = AppShellRenderer().render(self.dataset(account, currency))
        p = Path(out_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(html, encoding="utf-8")
        return str(p.resolve())

    def stats(self) -> Dict[str, Any]:
        return self.repo.stats()
