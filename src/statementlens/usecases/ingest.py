"""IngestStatements use-case — the pipeline from raw documents to stored, categorized transactions.

Depends only on ports (StatementSource, Decryptor, TextExtractor, ParserRegistry, Categorizer,
TransactionRepository), so every step is swappable and the use-case is unit-testable with fakes.
Orchestration only — no bank/format specifics live here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

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
    #: loan / deposit snapshots stored (positions, never transactions)
    positions: int = 0

    @property
    def ok(self) -> bool:
        return self.inserted > 0 or self.duplicate > 0 or self.positions > 0


class IngestStatements:
    def __init__(self, *, source: StatementSource, decryptor: Decryptor,
                 extractor: TextExtractor, parser_registry, categorizer: Categorizer,
                 repository: TransactionRepository,
                 position_parser: Optional[Callable[[str], Optional[Dict[str, Any]]]] = None):
        self._source = source
        self._decryptor = decryptor
        self._extractor = extractor
        self._parsers = parser_registry
        self._categorizer = categorizer
        self._repo = repository
        #: text -> loan/deposit snapshot or None. Injected, so no bank format lives in this use-case.
        self._position = position_parser

    def run(self, *, account: str, hints: Dict[str, Any], limit: int = 100,
            split_accounts: bool = True) -> IngestResult:
        """`split_accounts` derives each statement's own account label from the file.

        A folder usually holds several accounts. Filing them all under one `--account` name merges a
        savings account with its own credit cards, which double-counts every card-bill payment and
        picks the wrong presentation frame. Pass False to force one label.
        """
        result = IngestResult()
        raws = self._source.fetch(limit=limit)
        # mail the source refused to open (sender not proven) is listed, never silently dropped
        result.skipped += getattr(self._source, "refused", [])
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
                # A loan statement or FD advice is a position. It must never reach the transaction
                # parsers: its EMIs are already debits on the paying account, so rows from it would
                # count every EMI twice. A document failing its own arithmetic raises and lands in
                # `errors` rather than being stored with a plausible wrong number.
                snap = self._position(text) if self._position else None
                if snap is not None:
                    save = getattr(self._repo, "save_position", None)
                    if save is not None:
                        save(snap)
                        result.positions += 1
                    continue
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
                stmt, already = self._drop_stored_movements(stmt)
                if already and not stmt.transactions:
                    result.duplicate += already      # every movement in it is already stored
                    continue
                counts = self._repo.save_statement(stmt)
                counts["duplicate"] += already
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
        """Reconcile live rows this statement covers: paired ones go, unpaired ones are set aside.

        Returns the live rows the statement confirmed. Falls back to a plain purge for a repo that
        cannot reconcile."""
        recon = getattr(self._repo, "reconcile_provisional", None)
        purge = getattr(self._repo, "purge_provisional", None)
        if recon is None and purge is None:
            return 0
        # per-month blocks, not a min..max hull: one carry-forward row would otherwise stretch the
        # range back weeks and irreversibly delete alert rows for months this statement never covered
        ranges = merge_coverages(coverage_blocks(stmt.transactions, stmt.account)).get(stmt.account, [])
        if not ranges:
            return 0
        if recon is not None:
            return recon(stmt.account, ranges)["matched"]
        return purge(stmt.account, ranges)

    def _drop_stored_movements(self, stmt: Statement):
        """Remove rows whose movement of money is already in the store; return (stmt, n_removed).

        The filename check above misses a statement that arrives twice under DIFFERENT names — HDFC
        mailed one card's Jul/Sep/Oct statements twice (`…_01-10-2025.PDF` and `…_01-10-2025_93.pdf`)
        plus a consolidated Aug–Mar file. Each copy's text came out slightly differently ("Limited
        Bangalore" vs "LimitedBangalore", a Ref# dropped), so the content hash differed and 399 rows
        went in twice: HDFC spend read ₹10.3L against a real ₹5.2L.

        A movement is (date, amount, direction) within the account, matched as a MULTISET: two genuine
        ₹2 charges on one day are both kept unless the store already holds two. A consolidated file
        that overlaps some months contributes only the months that are new.
        """
        counts = getattr(self._repo, "movement_counts", None)
        if counts is None or not stmt.transactions:
            return stmt, 0
        have = counts(stmt.account)
        keep, dropped = [], 0
        for t in stmt.transactions:
            k = (t.txn_date.isoformat() if t.txn_date else None, t.amount.minor, t.direction.value)
            if have[k] > 0 and not t.provisional:
                have[k] -= 1
                dropped += 1
            else:
                keep.append(t)
        if not dropped:
            return stmt, 0
        import dataclasses
        return dataclasses.replace(stmt, transactions=tuple(keep)), dropped

    def _categorize(self, stmt: Statement) -> Statement:
        tagged = tuple(t.with_category(self._categorizer.categorize(t)) for t in stmt.transactions)
        return Statement(stmt.account, stmt.source_id, stmt.source_name, stmt.period_hint, tagged)
