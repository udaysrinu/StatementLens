"""IngestStatements use-case — the pipeline from raw documents to stored, categorized transactions.

Depends only on ports (StatementSource, Decryptor, TextExtractor, ParserRegistry, Categorizer,
TransactionRepository), so every step is swappable and the use-case is unit-testable with fakes.
Orchestration only — no bank/format specifics live here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from ..domain.models import Statement
from ..domain.ports import (Categorizer, Decryptor, StatementSource,
                            TextExtractor, TransactionRepository)
from .diagnose import diagnose
from .account_id import account_label
from .supersede import coverage_blocks, merge_coverages


@dataclass
class IngestResult:
    statements: int = 0
    inserted: int = 0
    duplicate: int = 0
    failed: int = 0
    #: provisional alert rows removed because a statement now covers their period
    superseded: int = 0
    errors: List[str] = field(default_factory=list)
    #: Per-document explanations for anything that yielded no transactions. Never let a document
    #: disappear silently — an empty dashboard with no reason is the worst possible outcome.
    skipped: List[Dict[str, str]] = field(default_factory=list)
    #: Account labels this run wrote to, so the user learns their statements held several accounts.
    accounts: Dict[str, int] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.inserted > 0 or self.duplicate > 0


class IngestStatements:
    def __init__(self, *, source: StatementSource, decryptor: Decryptor,
                 extractor: TextExtractor, parser_registry, categorizer: Categorizer,
                 repository: TransactionRepository):
        self._source = source
        self._decryptor = decryptor
        self._extractor = extractor
        self._parsers = parser_registry
        self._categorizer = categorizer
        self._repo = repository

    def run(self, *, account: str, hints: Dict[str, Any], limit: int = 100,
            split_accounts: bool = True) -> IngestResult:
        """`split_accounts` derives each statement's own account label from the file.

        A folder usually holds several accounts. Filing them all under one `--account` name merges a
        savings account with its own credit cards, which double-counts every card-bill payment and
        picks the wrong presentation frame. Pass False to force one label.
        """
        result = IngestResult()
        raws = self._source.fetch(limit=limit)
        # A source that hit its own cap has MORE history than it returned. Reported through `skipped`
        # so it surfaces in the UI's "which?" panel rather than being a silently shorter ledger — the
        # failure mode here is that a truncated history looks exactly like a short one.
        if getattr(self._source, "truncated", False):
            result.skipped.append({
                "source": "mailbox",
                "problem": "truncated",
                "message": (f"Stopped after {limit} emails, and more statements exist further back. "
                            f"Re-run with a higher limit to reach them."),
                "detail": ""})
        for raw in raws:
            try:
                decrypted = self._decryptor.decrypt(raw.data, hints)
                text = self._extractor.extract(decrypted)
                label = (account_label(raw.source_name, text, fallback=account)
                         if split_accounts else account)
                # A file already in the store is skipped outright. Row-level dedup cannot be relied
                # on here: its hash includes the account label and a per-source id, so the same
                # statement seen from a different source (Gmail vs folder) or after a relabel would
                # insert every row again and double every total.
                seen = getattr(self._repo, "already_ingested", None)
                stmt = self._parsers.parse(text, account=label,
                                           source_id=raw.source_id, source_name=raw.source_name)
                if seen is not None and stmt.transactions and seen(stmt):
                    result.duplicate += len(stmt.transactions)
                    continue
                if not stmt.transactions:
                    # parsed "successfully" but empty — say why instead of counting a silent win
                    d = diagnose(text, source_name=raw.source_name)
                    if d:
                        result.skipped.append({"source": raw.source_name, "problem": d.problem,
                                               "message": d.message, "detail": d.detail})
                        continue
                stmt = self._categorize(stmt)
                counts = self._repo.save_statement(stmt)
                result.statements += 1
                result.inserted += counts["inserted"]
                result.duplicate += counts["duplicate"]
                # this statement is now the authoritative record for the period it covers, so any
                # provisional alert rows in that window would double-count
                result.superseded += self._supersede(stmt)
                result.accounts[stmt.account] = result.accounts.get(stmt.account, 0) + counts["inserted"]
            except Exception as e:  # one bad statement shouldn't abort the batch
                result.failed += 1
                result.errors.append(f"{raw.source_name}: {e}")
        return result

    def _supersede(self, stmt: Statement) -> int:
        """Remove provisional rows covered by this statement, if the repo supports it."""
        purge = getattr(self._repo, "purge_provisional", None)
        if purge is None:
            return 0
        # per-month blocks, not a min..max hull: one carry-forward row would otherwise stretch the
        # range back weeks and irreversibly delete alert rows for months this statement never covered
        ranges = merge_coverages(coverage_blocks(stmt.transactions, stmt.account)).get(stmt.account, [])
        if not ranges:
            return 0
        return purge(stmt.account, ranges)

    def _categorize(self, stmt: Statement) -> Statement:
        tagged = tuple(t.with_category(self._categorizer.categorize(t)) for t in stmt.transactions)
        return Statement(stmt.account, stmt.source_id, stmt.source_name, stmt.period_hint, tagged)
