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

    @classmethod
    def from_email(cls, address: str, app_password: str, *, db_path: Optional[str] = None,
                   host: Optional[str] = None, months: int = 24,
                   own_names: Optional[list] = None) -> "App":
        """Wire the app to read statements over IMAP with an app-specific password.

        Works with any provider (Gmail, Outlook, Yahoo, Zoho, corporate) and needs no Google Cloud
        project, no OAuth client and no restricted-scope review — so unlike the Gmail adapter it has
        no 100-user cap.
        """
        from .adapters.sources.imap_source import ImapCredentials, ImapStatementSource
        creds = ImapCredentials(address, app_password, host=host)
        return cls(db_path=db_path, own_names=own_names,
                   source=ImapStatementSource(creds, months=months))

    def __init__(self, *, db_path: Optional[str] = None, source=None,
                 own_names: Optional[list] = None):
        # own_names drives self-transfer exclusion: money between the user's own accounts is
        # neither income nor spending, so counting both legs inflates every total
        self.own_names = own_names or []
        self.repo = SqliteTransactionRepository(db_path)
        # the categorizer needs the holder's name too, so self-transfers get their own tag rather
        # than inflating person-to-person spending
        # The sync log lives beside the database so it stays writable if the DB is the problem.
        # Derived from the db FILENAME, not just its folder — `with_name()` alone would give every
        # database in a directory the same log, so two accounts would clobber each other's history.
        from .usecases.refresh import SyncLog
        db = Path(self.repo.path)
        self.sync_log = SyncLog(str(db.with_name(f"{db.stem}.sync.json")))
        self.categorizer = KeywordCategorizer(own_names=self.own_names)
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

    def ingest_alerts(self, *, account: str, source=None, currency: str = "INR",
                      days: int = 45) -> Dict[str, Any]:
        """Read transaction-ALERT emails and store them as provisional rows.

        Rows landing inside a period an existing statement already covers are discarded immediately —
        the settled record wins, so a swipe is never counted twice.
        """
        from .adapters.sources.alert_email_source import alerts_to_transactions
        from .domain.models import Statement
        from .usecases.supersede import coverage_from_transactions, is_covered

        if source is None:
            raise RuntimeError("pass an alert source (ImapAlertSource or GmailAlertSource)")
        messages = source.messages()
        txns = alerts_to_transactions(messages, currency=currency)

        settled = [t for t in self.repo.all(account) if not t.provisional]
        cov = coverage_from_transactions(settled, account)
        ranges = [(cov.start, cov.end)] if cov else []
        fresh = [t for t in txns if not is_covered(t.txn_date, ranges)]
        skipped = len(txns) - len(fresh)

        tagged = tuple(t.with_category(self.categorizer.categorize(t)) for t in fresh)
        counts = self.repo.save_statement(
            Statement(account, "alerts", "transaction alerts", "live", tagged))
        return {"emails": len(messages), "parsed": len(txns), "inserted": counts["inserted"],
                "duplicate": counts["duplicate"], "already_in_statement": skipped}

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
