"""ParserRegistry — picks the right StatementParser for a document (Open/Closed).

Register parsers once; `parse()` asks each `can_parse()` in priority order and delegates to the
first match. Add a new bank/format by registering another parser — no edits to existing code.
"""

from __future__ import annotations

from typing import List

from ...domain.models import Statement
from ...domain.ports import StatementParser


class ParserRegistry:
    def __init__(self, parsers: List[StatementParser] | None = None):
        self._parsers: List[StatementParser] = list(parsers or [])

    def register(self, parser: StatementParser) -> "ParserRegistry":
        self._parsers.append(parser)
        return self

    def parse(self, text: str, *, account: str, source_id: str, source_name: str) -> Statement:
        for p in self._parsers:
            if p.can_parse(text):
                return p.parse(text, account=account, source_id=source_id, source_name=source_name)
        # nothing matched -> empty statement (caller can inspect count)
        return Statement(account, source_id, source_name, source_name[-8:], tuple())
