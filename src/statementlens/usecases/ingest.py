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


@dataclass
class IngestResult:
    statements: int = 0
    inserted: int = 0
    duplicate: int = 0
    failed: int = 0
    errors: List[str] = field(default_factory=list)
    #: Per-document explanations for anything that yielded no transactions. Never let a document
    #: disappear silently — an empty dashboard with no reason is the worst possible outcome.
    skipped: List[Dict[str, str]] = field(default_factory=list)

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

    def run(self, *, account: str, hints: Dict[str, Any], limit: int = 100) -> IngestResult:
        result = IngestResult()
        for raw in self._source.fetch(limit=limit):
            try:
                decrypted = self._decryptor.decrypt(raw.data, hints)
                text = self._extractor.extract(decrypted)
                stmt = self._parsers.parse(text, account=account,
                                           source_id=raw.source_id, source_name=raw.source_name)
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
            except Exception as e:  # one bad statement shouldn't abort the batch
                result.failed += 1
                result.errors.append(f"{raw.source_name}: {e}")
        return result

    def _categorize(self, stmt: Statement) -> Statement:
        tagged = tuple(t.with_category(self._categorizer.categorize(t)) for t in stmt.transactions)
        return Statement(stmt.account, stmt.source_id, stmt.source_name, stmt.period_hint, tagged)
