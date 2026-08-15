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


def test_delete_removes_the_dpapi_blob_too():
    """"Disconnect Gmail" must leave nothing usable behind on ANY platform.

    The Windows DPAPI backend writes a .dpapi file while the plaintext fallback writes .json, and
    delete() only unlinked the .json — so on Windows the encrypted-but-usable token survived a
    disconnect.
    """
    with tempfile.TemporaryDirectory() as tmp:
        s = _store(tmp)
        json_path = s._path("tok")
        dpapi_path = json_path.with_suffix(".dpapi")
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text("plaintext", encoding="utf-8")
        dpapi_path.write_bytes(b"encrypted-blob")
        s.delete("tok")
        assert not json_path.exists()
        assert not dpapi_path.exists(), "the DPAPI blob was left on disk"


def test_macos_write_hex_encodes_and_never_sends_plaintext_argv():
    """The secret goes to `security` as HEX on argv — a deliberate, documented tradeoff.

    It used to travel via stdin (`-w`), which keeps it out of `ps` entirely. But `-w` from stdin
    TRUNCATES AT 128 CHARACTERS and returns success, so every ~500-byte Gmail token was silently
    stored corrupt. A credential you cannot read back is a worse failure than one briefly visible to a
    local process, so -X won.

    What must stay true: the plaintext never appears in argv, and the hex round-trips.
    """
    import platform
    if platform.system() != "Darwin":
        return
    import subprocess
    seen = {}
    real_run = subprocess.run

    def spy(cmd, *a, **kw):
        if isinstance(cmd, list) and "add-generic-password" in cmd:
            seen["argv"] = list(cmd)
        return real_run(cmd, *a, **kw)

    subprocess.run = spy
    try:
        with tempfile.TemporaryDirectory() as tmp:
            SecretStore(service=SERVICE + "_argv", fallback_dir=str(Path(tmp))).set("k", "S3CRET")
    finally:
        subprocess.run = real_run

    assert "argv" in seen, "expected a keychain write"
    joined = " ".join(seen["argv"])
    assert "S3CRET" not in joined, "plaintext secret leaked into argv"
    assert "S3CRET".encode().hex() in joined, "secret should be hex-encoded on argv"


def test_a_long_secret_survives_the_keychain_intact():
    """The bug this pins: `security -w` from stdin kept only the first 128 bytes, silently.

    A Gmail OAuth token is ~500 bytes, so it came back as JSON cut mid-string, parsed as None, and
    surfaced as "Gmail isn't set up in this build" — a corruption bug wearing a config error's
    message. Any secret store that truncates is useless, so this asserts an exact round-trip well past
    the old ceiling.
    """
    import platform
    if platform.system() != "Darwin":
        return
    long_secret = "T" * 700 + '{"refresh_token":"tail-must-survive"}'
    with tempfile.TemporaryDirectory() as tmp:
        store = SecretStore(service=SERVICE + "_long", fallback_dir=str(Path(tmp)))
        store.set("tok", long_secret)
        try:
            got = store.get("tok")
            assert got == long_secret, f"kept {len(got or '')} of {len(long_secret)} bytes"
        finally:
            store.delete("tok")
