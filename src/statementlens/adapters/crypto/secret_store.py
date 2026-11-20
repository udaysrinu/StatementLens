"""SecretStore: tokens in the OS keychain, using inboxkit's implementation (shared with sharecase).

This module only pins StatementLens's keychain namespace. The service name and the 0600 fallback
directory (~/.statementlens/secrets) are the ones used before the switch, so a token stored by an
older build is the one read now: no new Gmail consent.
"""
from typing import Optional

from inboxkit.secrets import SecretStore as _SecretStore, StoreResult, migrate_file_secret  # noqa: F401

SERVICE = "statementlens"


class SecretStore(_SecretStore):
    def __init__(self, service: str = SERVICE, fallback_dir: Optional[str] = None):
        super().__init__(service, fallback_dir)
