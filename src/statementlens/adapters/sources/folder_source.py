"""FolderStatementSource — read statement PDFs from a local folder (StatementSource port).

The zero-setup onboarding path, and the one that works for everyone: no Google Cloud project, no
OAuth consent screen, no restricted-scope verification, no per-bank email templates. Drop PDFs in a
folder (or drag them onto the app) and they ingest.

That matters for distribution: `gmail.readonly` is a Google *restricted* scope, so the Gmail adapter
is capped at 100 test users until a CASA security assessment is passed. This adapter has no such
gate, so it is the shippable default with Gmail as an opt-in convenience on top.

Provenance: `source_id` is a content hash of the file, NOT the path. Two copies of the same statement
in different folders must dedupe to one, and renaming a file must not create a duplicate ingest.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

_PDF_SUFFIXES = {".pdf"}
#: Skip macOS resource forks, Windows thumbs, and partially-downloaded files.
_IGNORED_PREFIXES = ("._", "~$", ".")
_IGNORED_SUFFIXES = (".crdownload", ".part", ".tmp")


@dataclass
class _RawStatement:
    source_id: str
    source_name: str
    data: bytes


class FolderStatementSource:
    """Yields statement PDFs found in one or more local folders.

    Args:
        folders: folder path(s) to scan. A single string is accepted for convenience.
        recursive: descend into subfolders (default True — people file statements by year/bank).
        pattern: optional filename substring filter, case-insensitive (e.g. "sbi").
    """

    def __init__(self, folders, *, recursive: bool = True, pattern: Optional[str] = None):
        if isinstance(folders, (str, Path)):
            folders = [folders]
        self._folders: Sequence[Path] = [Path(f).expanduser() for f in folders]
        self._recursive = recursive
        self._pattern = (pattern or "").lower()

    # -- port method -------------------------------------------------------
    def fetch(self, limit: int = 100) -> List[_RawStatement]:
        out: List[_RawStatement] = []
        seen: set[str] = set()
        for path in self._candidates():
            if len(out) >= limit:
                break
            try:
                data = path.read_bytes()
            except OSError:
                # an unreadable file must not abort the whole import
                continue
            if not data:
                continue
            digest = hashlib.sha256(data).hexdigest()
            if digest in seen:          # same bytes seen twice (duplicate copies) -> ingest once
                continue
            seen.add(digest)
            out.append(_RawStatement(source_id=digest[:16], source_name=path.name, data=data))
        return out

    # -- helpers -----------------------------------------------------------
    def _candidates(self) -> Iterable[Path]:
        """Sorted, filtered PDF paths. Sorted so ingest order is deterministic across runs."""
        found: List[Path] = []
        for folder in self._folders:
            if not folder.is_dir():
                continue
            it = folder.rglob("*") if self._recursive else folder.glob("*")
            for p in it:
                if self._is_statement_file(p):
                    found.append(p)
        return sorted(found)

    def _is_statement_file(self, p: Path) -> bool:
        if not p.is_file() or p.suffix.lower() not in _PDF_SUFFIXES:
            return False
        name = p.name
        if name.startswith(_IGNORED_PREFIXES) or name.lower().endswith(_IGNORED_SUFFIXES):
            return False
        return self._pattern in name.lower() if self._pattern else True

    def describe(self) -> str:
        """Human-readable summary for the onboarding UI ("found 12 PDFs in ~/Statements")."""
        n = len(list(self._candidates()))
        where = ", ".join(str(f) for f in self._folders)
        return f"{n} PDF{'s' if n != 1 else ''} in {where}"
