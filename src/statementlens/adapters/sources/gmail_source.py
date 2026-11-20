"""GmailStatementSource — fetch statement-PDF attachments from Gmail (StatementSource port).

Read-only Gmail (scope gmail.readonly). It only READS: it returns RawStatement documents (bytes +
provenance); it never writes anything. Google libraries are imported lazily so the package imports
without them (install the [gmail] extra to use this adapter).

Setup: none with a bundled OAuth client (bundled_client.py); otherwise Desktop OAuth credentials at
~/.statementlens/gmail_client_secret.json. The first fetch opens a browser consent; the token is then
kept in the OS keychain (service "statementlens"), never in a plain file.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

# Paging, the truncation flag, the MIME walk and keychain token storage live in inboxkit (shared with
# sharecase). DEFAULT_LIMIT is 1000 there too: the old 100 cut a real mailbox's oldest months silently.
from inboxkit.inbox import DEFAULT_LIMIT, SCOPES, GmailDocuments, _MAX_PAGE  # noqa: F401

# Bank names WITHOUT a domain suffix, so each matches whatever TLD the bank currently sends from.
#
# Indian banks migrated to `.bank.in` in 2025-26 (RBI's exclusive banking domain), and the old list
# said `icicibank`, which Gmail tokenises as one word. It matches `icicibank.com` but NOT
# `credit_cards@icici.bank.in`, because there the tokens are `icici` and `bank`. Ten ICICI statements —
# every one from Mar to Aug 2026 — stopped matching the moment they switched, and the sync reported a
# clean run each time because nothing it *did* find had changed. `hdfcbank.bank.in` and
# `alerts.sbi.bank.in` kept working purely by luck: they still contain `hdfcbank` and `sbi`.
#
# So: match the bare bank name and let Gmail's tokeniser do the rest. `icici` matches both domains;
# `icicibank` matches only the old one.
_BANK_SENDERS = (
    # split form, matching the new `<bank>.bank.in` domains. Only names distinctive enough to stand
    # alone — bare "yes" and "au" would match half the mailbox, so those use the full domain below.
    "sbi", "hdfc", "icici", "axis", "kotak", "rbl", "idfcfirst", "indusind",
    "yes.bank.in", "au.bank.in",
    # joined form, matching the legacy `<bank>bank.com` / `.co.in` domains. BOTH are needed:
    # Gmail tokenises the address, so `icici` does not match the token `icicibank` and vice versa.
    # Listing only the joined form lost every ICICI statement after their migration; listing only the
    # split form lost every one before it. Verified by match count against the live mailbox.
    "icicibank", "hdfcbank", "axisbank", "rblbank", "yesbank", "idfcfirstbank", "aubank",
    # card-only and non-bank issuers
    "sbicard", "onecard", "amex", "citibank", "hsbc", "scapia", "federal", "federalbank",
    # loan, deposit and pension documents (stored as positions, not transactions)
    "bankofbaroda", "suryoday", "suryodaybank", "proteantech")

DEFAULT_QUERY = (
    'has:attachment filename:pdf newer_than:5y '
    'subject:(statement OR "e-statement" OR "account statement" OR "credit card" OR bill OR "fixed deposit") '
    'from:(' + ' OR '.join(_BANK_SENDERS) + ')')



#: Where a sibling ExpensifyAI / splitwise-mcp install already keeps its Google credentials. Read as a
#: FALLBACK so someone who has already authorised Gmail for that tool is not made to create a second
#: Google Cloud project and consent again: same user, same mailbox, same read-only scope. Only ever
#: read, never written or moved (inboxkit treats a fallback dir's token as borrowed).
_SIBLING_DIR = Path.home() / ".expensifyai"


def _bundled_client() -> Optional[dict]:
    """The app's bundled OAuth client, used only when the user has no client file of their own.

    Shipping the client id/secret is the normal pattern for *installed* apps: the "secret" cannot be
    kept confidential in a distributed binary, which is why the loopback flow does not rely on it.
    """
    from .bundled_client import bundled_client_config
    return bundled_client_config()


class GmailStatementSource(GmailDocuments):
    """Statement PDFs from Gmail: inboxkit's GmailDocuments with StatementLens's bank query, keychain
    namespace and bundled client. `service` is injectable for testing (no creds needed)."""

    def __init__(self, service=None, query: Optional[str] = None,
                 client_secret_path: Optional[str] = None, token_path: Optional[str] = None):
        super().__init__(query or DEFAULT_QUERY, app="statementlens", service=service,
                         client_config=_bundled_client, client_secret_path=client_secret_path,
                         token_path=token_path, fallback_dirs=[str(_SIBLING_DIR)])
