"""SecretStore — keep OAuth tokens in the OS keychain instead of a plaintext file.

A Gmail refresh token is a long-lived key to the user's entire mailbox. In a file it is readable by
any process running as that user, survives in backups, and gets copied around by sync tools. The OS
keychain is encrypted at rest, gated by the login session, and is where users already expect
credentials to live.

Implemented with the tools each platform already ships — `security` on macOS, DPAPI via PowerShell on
Windows, `secret-tool` on Linux — rather than adding the `keyring` dependency. One less install step
matters for a local app people run themselves, and these are stable, well-documented interfaces.

Falls back to a 0600 file when no keychain is reachable (headless Linux, a container, a locked-down
box). The fallback is REPORTED, never silent: a user who thinks their token is in the keychain when it
is actually on disk has been misled about their own security posture.
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

SERVICE = "statementlens"


@dataclass(frozen=True)
class StoreResult:
    """Where a secret actually ended up, so callers can tell the user the truth."""
    backend: str          # "keychain" | "dpapi" | "secret-service" | "file"
    secure: bool
    detail: str = ""


class SecretStore:
    """Read/write small secrets (OAuth tokens) by name.

    `fallback_dir` holds the 0600 file used only when no OS keychain is available.
    """

    def __init__(self, service: str = SERVICE, fallback_dir: Optional[str] = None):
        self._service = service
        self._dir = Path(fallback_dir or (Path.home() / ".statementlens" / "secrets"))

    # -- public API --------------------------------------------------------
    def set(self, name: str, value: str) -> StoreResult:
        for backend in self._backends():
            try:
                if backend(name, value, write=True):
                    return StoreResult(self._backend_name(backend), True)
            except Exception:
                continue          # try the next backend rather than failing the whole flow
        return self._file_write(name, value)

    def get(self, name: str) -> Optional[str]:
        for backend in self._backends():
            try:
                got = backend(name, None, write=False)
                if got:
                    return got
            except Exception:
                continue
        return self._file_read(name)

    def delete(self, name: str) -> None:
        """Remove a secret everywhere it might live — used by "disconnect Gmail"."""
        system = platform.system()
        try:
            if system == "Darwin":
                subprocess.run(["security", "delete-generic-password",
                                "-s", self._service, "-a", name],
                               capture_output=True, check=False)
            elif shutil.which("secret-tool"):
                subprocess.run(["secret-tool", "clear", "service", self._service, "account", name],
                               capture_output=True, check=False)
        finally:
            # Remove EVERY on-disk form. The DPAPI blob uses a .dpapi suffix, so deleting only the
            # .json fallback left a working Gmail token on disk after "disconnect" on Windows.
            for path in (self._path(name), self._path(name).with_suffix(".dpapi")):
                try:
                    if path.exists():
                        path.unlink()
                except OSError:
                    pass

    def describe(self) -> StoreResult:
        """Which backend WOULD be used — for showing the user where their token lives."""
        probe = "__statementlens_probe__"
        result = self.set(probe, "x")
        self.delete(probe)
        return result

    # -- backends ----------------------------------------------------------
    def _backends(self):
        system = platform.system()
        if system == "Darwin":
            return [self._macos]
        if system == "Windows":
            return [self._windows]
        return [self._secret_service]

    @staticmethod
    def _backend_name(fn) -> str:
        return {"_macos": "keychain", "_windows": "dpapi",
                "_secret_service": "secret-service"}.get(fn.__name__, "unknown")

    def _macos(self, name: str, value: Optional[str], *, write: bool):
        if write:
            # -w with NO argument makes `security` read the secret from stdin instead of argv, so the
            # Gmail refresh token is never visible to `ps`. It prompts TWICE (enter + confirm), so the
            # value must be written twice; sending it once fails with "passwords don't match".
            # -U updates an existing item instead of erroring on a duplicate.
            secret = value or ""
            r = subprocess.run(
                ["security", "add-generic-password", "-U", "-s", self._service,
                 "-a", name, "-D", "statementlens token", "-w"],
                input=f"{secret}\n{secret}\n", capture_output=True, text=True)
            return r.returncode == 0
        r = subprocess.run(["security", "find-generic-password", "-s", self._service,
                            "-a", name, "-w"], capture_output=True, text=True)
        return r.stdout.strip() if r.returncode == 0 else None

    def _secret_service(self, name: str, value: Optional[str], *, write: bool):
        if not shutil.which("secret-tool"):
            raise RuntimeError("secret-tool not installed")
        if write:
            r = subprocess.run(["secret-tool", "store", "--label=statementlens",
                                "service", self._service, "account", name],
                               input=(value or ""), capture_output=True, text=True)
            return r.returncode == 0
        r = subprocess.run(["secret-tool", "lookup", "service", self._service, "account", name],
                           capture_output=True, text=True)
        return r.stdout.strip() if r.returncode == 0 and r.stdout.strip() else None

    def _windows(self, name: str, value: Optional[str], *, write: bool):
        """DPAPI via PowerShell — encrypts under the current user account."""
        blob = self._path(name).with_suffix(".dpapi")
        if write:
            blob.parent.mkdir(parents=True, exist_ok=True)
            script = (
                "$s = [Console]::In.ReadToEnd();"
                "Add-Type -AssemblyName System.Security;"
                "$b = [Text.Encoding]::UTF8.GetBytes($s);"
                "$e = [Security.Cryptography.ProtectedData]::Protect($b, $null, 'CurrentUser');"
                f"[IO.File]::WriteAllBytes('{blob}', $e)")
            r = subprocess.run(["powershell", "-NoProfile", "-Command", script],
                               input=(value or ""), capture_output=True, text=True)
            return r.returncode == 0
        if not blob.exists():
            return None
        script = (
            "Add-Type -AssemblyName System.Security;"
            f"$e = [IO.File]::ReadAllBytes('{blob}');"
            "$b = [Security.Cryptography.ProtectedData]::Unprotect($e, $null, 'CurrentUser');"
            "[Text.Encoding]::UTF8.GetString($b)")
        r = subprocess.run(["powershell", "-NoProfile", "-Command", script],
                           capture_output=True, text=True)
        return r.stdout.strip() if r.returncode == 0 else None

    # -- 0600 file fallback ------------------------------------------------
    def _path(self, name: str) -> Path:
        safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in name)
        return self._dir / f"{safe}.json"

    def _file_write(self, name: str, value: str) -> StoreResult:
        path = self._path(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        # create with 0600 from the start; writing then chmod-ing leaves a readable window
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(value)
        try:
            os.chmod(path.parent, 0o700)
        except OSError:
            pass
        return StoreResult("file", False,
                           f"no OS keychain available; stored with 0600 permissions at {path}")

    def _file_read(self, name: str) -> Optional[str]:
        path = self._path(name)
        if not path.exists():
            return None
        try:
            return path.read_text(encoding="utf-8")
        except OSError:
            return None


def migrate_file_secret(store: SecretStore, name: str, legacy_path: Path) -> Optional[StoreResult]:
    """Move an existing plaintext token file into the keychain, then delete the file.

    Returns None when there was nothing to migrate. The file is only removed after a successful
    read-back, so a failed migration can never lose the user's token.
    """
    if not legacy_path.exists():
        return None
    payload = legacy_path.read_text(encoding="utf-8").strip()
    if not payload:
        return None
    result = store.set(name, payload)
    if store.get(name) != payload:
        raise RuntimeError(f"failed to verify {name} in {result.backend}; left {legacy_path} in place")
    if result.secure:
        legacy_path.unlink()
    return result
