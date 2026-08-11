"""Checks for SecretStore. Uses a throwaway service name so the user's real keychain is untouched.

The file fallback is exercised directly, since CI and containers have no keychain — and the important
property there is that it is 0600 and honestly REPORTED as insecure.
"""

import os
import platform
import stat
import tempfile
from pathlib import Path

from statementlens.adapters.crypto.secret_store import SecretStore, migrate_file_secret

SERVICE = "statementlens_pytest"


def _store(tmp) -> SecretStore:
    return SecretStore(service=SERVICE, fallback_dir=str(Path(tmp) / "secrets"))


def test_round_trip_and_delete():
    with tempfile.TemporaryDirectory() as tmp:
        s = _store(tmp)
        s.set("tok", '{"refresh_token":"abc"}')
        assert s.get("tok") == '{"refresh_token":"abc"}'
        s.delete("tok")
        assert s.get("tok") is None


def test_overwriting_a_secret_updates_it():
    # macOS `security add-generic-password` errors on duplicates without -U
    with tempfile.TemporaryDirectory() as tmp:
        s = _store(tmp)
        s.set("tok", "first")
        s.set("tok", "second")
        assert s.get("tok") == "second"
        s.delete("tok")


def test_missing_secret_returns_none():
    with tempfile.TemporaryDirectory() as tmp:
        assert _store(tmp).get("never_written_key") is None


def test_describe_reports_the_backend_honestly():
    with tempfile.TemporaryDirectory() as tmp:
        r = _store(tmp).describe()
        assert r.backend in ("keychain", "dpapi", "secret-service", "file")
        # a file backend must NEVER claim to be secure
        assert r.secure is (r.backend != "file")
        if r.backend == "file":
            assert r.detail, "the insecure fallback must explain itself"


def test_file_fallback_is_created_0600():
    with tempfile.TemporaryDirectory() as tmp:
        s = _store(tmp)
        r = s._file_write("tok", "secret-value")
        assert r.secure is False and r.backend == "file"
        path = s._path("tok")
        mode = stat.S_IMODE(os.stat(path).st_mode)
        assert mode == 0o600, oct(mode)
        assert s._file_read("tok") == "secret-value"


def test_key_names_cannot_escape_the_secrets_directory():
    with tempfile.TemporaryDirectory() as tmp:
        s = _store(tmp)
        p = s._path("../../evil")
        assert s._dir in p.parents, p


def test_migration_moves_the_file_and_deletes_it():
    with tempfile.TemporaryDirectory() as tmp:
        s = _store(tmp)
        legacy = Path(tmp) / "gmail_token.json"
        legacy.write_text('{"refresh_token":"xyz"}', encoding="utf-8")
        result = migrate_file_secret(s, "mig_tok", legacy)
        assert result is not None
        assert s.get("mig_tok") == '{"refresh_token":"xyz"}'
        if result.secure:
            assert not legacy.exists(), "the plaintext token must not be left behind"
        else:
            # with no keychain there is nowhere safer to put it, so it stays
            assert legacy.exists()
        s.delete("mig_tok")


def test_migration_is_a_noop_when_there_is_no_file():
    with tempfile.TemporaryDirectory() as tmp:
        assert migrate_file_secret(_store(tmp), "x", Path(tmp) / "absent.json") is None


def test_migration_ignores_an_empty_file():
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "empty.json"
        p.write_text("   ", encoding="utf-8")
        assert migrate_file_secret(_store(tmp), "x", p) is None
        assert p.exists()          # nothing was migrated, so nothing was deleted
