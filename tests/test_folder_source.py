"""Checks for FolderStatementSource. Uses a temp folder — no real statements involved."""

import tempfile
from pathlib import Path

from statementlens.adapters.sources.folder_source import FolderStatementSource


def _mk(root: Path, name: str, body: bytes = b"%PDF-1.4 fake") -> Path:
    p = root / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(body)
    return p


def test_finds_pdfs_recursively_and_ignores_other_files():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        _mk(root, "sbi_jan.pdf", b"a")
        _mk(root, "2025/hdfc_feb.pdf", b"b")
        _mk(root, "notes.txt", b"c")
        _mk(root, "image.png", b"d")
        got = {r.source_name for r in FolderStatementSource(root).fetch()}
        assert got == {"sbi_jan.pdf", "hdfc_feb.pdf"}


def test_non_recursive_stays_in_top_folder():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        _mk(root, "top.pdf", b"a")
        _mk(root, "sub/deep.pdf", b"b")
        got = {r.source_name for r in FolderStatementSource(root, recursive=False).fetch()}
        assert got == {"top.pdf"}


def test_identical_copies_dedupe_to_one():
    # the same statement filed twice must ingest once — source_id is content, not path
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        _mk(root, "a/stmt.pdf", b"same bytes")
        _mk(root, "b/stmt_copy.pdf", b"same bytes")
        out = FolderStatementSource(root).fetch()
        assert len(out) == 1


def test_source_id_is_stable_across_renames():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        p = _mk(root, "original.pdf", b"payload")
        first = FolderStatementSource(root).fetch()[0].source_id
        p.rename(root / "renamed.pdf")
        second = FolderStatementSource(root).fetch()[0].source_id
        assert first == second      # renaming must not look like a new statement


def test_skips_junk_and_partial_downloads():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        _mk(root, "real.pdf", b"a")
        _mk(root, "._resourcefork.pdf", b"b")
        _mk(root, "half.pdf.crdownload", b"c")
        _mk(root, "empty.pdf", b"")
        got = {r.source_name for r in FolderStatementSource(root).fetch()}
        assert got == {"real.pdf"}


def test_pattern_filters_by_filename():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        _mk(root, "SBI_march.pdf", b"a")
        _mk(root, "hdfc_march.pdf", b"b")
        got = {r.source_name for r in FolderStatementSource(root, pattern="sbi").fetch()}
        assert got == {"SBI_march.pdf"}


def test_limit_is_respected():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        for i in range(5):
            _mk(root, f"s{i}.pdf", f"body{i}".encode())
        assert len(FolderStatementSource(root).fetch(limit=2)) == 2


def test_missing_folder_yields_nothing_rather_than_crashing():
    # onboarding must survive a path the user typed wrong
    assert FolderStatementSource("/definitely/not/a/real/path").fetch() == []


def test_accepts_multiple_folders_and_describe_reports_count():
    with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
        _mk(Path(d1), "one.pdf", b"a")
        _mk(Path(d2), "two.pdf", b"b")
        src = FolderStatementSource([d1, d2])
        assert len(src.fetch()) == 2
        assert "2 PDFs" in src.describe()


def test_ingest_order_is_deterministic():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        for n in ("c.pdf", "a.pdf", "b.pdf"):
            _mk(root, n, n.encode())
        names = [r.source_name for r in FolderStatementSource(root).fetch()]
        assert names == sorted(names)
