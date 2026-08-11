"""ImapStatementSource — fetch statement PDFs over IMAP (StatementSource port).

Why this exists alongside the Gmail adapter: `gmail.readonly` is a Google *restricted* scope, so an
OAuth client is capped at 100 hand-allow-listed users until it passes a CASA security assessment.
IMAP has **no such gate** — the user creates an app-specific password in their own account settings
and pastes it in. One code path then covers Gmail, Outlook, Yahoo, Zoho, iCloud and corporate mail,
with no Google Cloud project, no OAuth client and no review queue.

The tradeoff, stated plainly because the user deserves to know: an app password grants access to the
whole mailbox, whereas the OAuth scope is read-only. This adapter therefore never issues a write
command — no STORE, no flag changes, no deletes — and opens the mailbox READ-ONLY so the server itself
enforces it. Messages are not even marked as read.

Uses stdlib `imaplib` and `email`; no new dependencies.
"""

from __future__ import annotations

import email
import imaplib
import re
from dataclasses import dataclass
from email.header import decode_header, make_header
from email.message import Message
from typing import Dict, List, Optional, Sequence

#: Well-known IMAP hosts, so onboarding can ask for an address and password only.
KNOWN_HOSTS: Dict[str, str] = {
    "gmail.com": "imap.gmail.com",
    "googlemail.com": "imap.gmail.com",
    "outlook.com": "outlook.office365.com",
    "hotmail.com": "outlook.office365.com",
    "live.com": "outlook.office365.com",
    "office365.com": "outlook.office365.com",
    "yahoo.com": "imap.mail.yahoo.com",
    "yahoo.in": "imap.mail.yahoo.com",
    "zoho.com": "imap.zoho.com",
    "zohomail.com": "imap.zoho.com",
    "icloud.com": "imap.mail.me.com",
    "me.com": "imap.mail.me.com",
    "proton.me": "127.0.0.1",          # requires the local Proton Bridge
    "protonmail.com": "127.0.0.1",
}

#: IMAP SEARCH is far cruder than Gmail's query language: no OR across different keys in one pass,
#: so we run several narrow searches and merge the UIDs.
_SEARCH_TERMS: Sequence[str] = (
    'SUBJECT "statement"',
    'SUBJECT "e-statement"',
    'SUBJECT "account statement"',
    'SUBJECT "credit card"',
    'SUBJECT "estatement"',
)

_BANKISH = re.compile(
    r"(?i)(sbi|hdfc|icici|axis|kotak|idfc|rbl|yes\s?bank|federal|indusind|amex|"
    r"american\s?express|citi|hsbc|standard\s?chartered|scapia|onecard|slice|jupiter|"
    r"bob|baroda|canara|pnb|union\s?bank|indian\s?bank|au\s?small|bandhan|"
    r"statement|bank)")


@dataclass
class _RawStatement:
    source_id: str
    source_name: str
    data: bytes


class ImapCredentials:
    """Connection details. The password is an APP password, never the account password."""

    def __init__(self, address: str, app_password: str, host: Optional[str] = None,
                 port: int = 993, mailbox: str = "INBOX"):
        if "@" not in address:
            raise ValueError("address must be a full email address")
        self.address = address.strip()
        self.app_password = app_password.strip().replace(" ", "")   # Google shows it in 4-char groups
        self.host = host or self.guess_host(self.address)
        self.port = port
        self.mailbox = mailbox

    @staticmethod
    def guess_host(address: str) -> str:
        domain = address.rsplit("@", 1)[-1].lower()
        if domain in KNOWN_HOSTS:
            return KNOWN_HOSTS[domain]
        # a sensible guess for corporate mail; the user can override
        return f"imap.{domain}"


class ImapStatementSource:
    """Fetches statement PDFs over IMAP. `connection` is injectable for testing."""

    def __init__(self, credentials: Optional[ImapCredentials] = None, *,
                 connection=None, months: int = 24, mailbox: Optional[str] = None):
        if credentials is None and connection is None:
            raise ValueError("provide credentials or an injected connection")
        self._creds = credentials
        self._conn = connection
        self._months = months
        self._mailbox = mailbox or (credentials.mailbox if credentials else "INBOX")

    # -- port method -------------------------------------------------------
    def fetch(self, limit: int = 100) -> List[_RawStatement]:
        conn = self._conn or self._connect()
        try:
            # readonly=True: the server refuses writes, so we cannot alter the user's mailbox even
            # by accident, and messages are not marked as read.
            conn.select(self._mailbox, readonly=True)
            uids = self._search(conn)
            out: List[_RawStatement] = []
            seen: set[str] = set()
            for uid in uids:
                if len(out) >= limit:
                    break
                msg = self._fetch_message(conn, uid)
                if msg is None:
                    continue
                sender = str(msg.get("From", ""))
                subject = _decode(msg.get("Subject", ""))
                if not _BANKISH.search(f"{sender} {subject}"):
                    continue
                # decode the UID: str(b"3") is "b'3'", which would poison every provenance id
                uid_text = uid.decode() if isinstance(uid, (bytes, bytearray)) else str(uid)
                for name, payload in _pdf_attachments(msg):
                    key = f"{uid_text}:{name}"
                    if key in seen:
                        continue
                    seen.add(key)
                    out.append(_RawStatement(source_id=uid_text, source_name=name, data=payload))
            return out
        finally:
            if self._conn is None:
                _close_quietly(conn)

    def check(self) -> str:
        """Verify credentials without importing anything. Returns a human-readable status.

        Onboarding needs to distinguish "wrong password" from "IMAP disabled" from "no statements
        found" — three problems with completely different fixes.
        """
        try:
            conn = self._conn or self._connect()
        except imaplib.IMAP4.error as e:
            raise RuntimeError(_friendly_login_error(str(e))) from e
        try:
            conn.select(self._mailbox, readonly=True)
            found = len(self._search(conn))
            return f"connected — {found} candidate statement email(s) in {self._mailbox}"
        finally:
            if self._conn is None:
                _close_quietly(conn)

    # -- helpers -----------------------------------------------------------
    def _connect(self):
        c = self._creds
        conn = imaplib.IMAP4_SSL(c.host, c.port)
        try:
            conn.login(c.address, c.app_password)
        except imaplib.IMAP4.error as e:
            _close_quietly(conn)
            raise RuntimeError(_friendly_login_error(str(e))) from e
        return conn

    def _search(self, conn) -> List[bytes]:
        """Union of several narrow searches, newest first."""
        since = _since_date(self._months)
        uids: List[bytes] = []
        for term in _SEARCH_TERMS:
            try:
                typ, data = conn.search(None, f'(SINCE {since} {term})')
            except imaplib.IMAP4.error:
                continue
            if typ == "OK" and data and data[0]:
                uids.extend(data[0].split())
        # de-duplicate while keeping newest-first order
        ordered = sorted({int(u) for u in uids}, reverse=True)
        return [str(u).encode() for u in ordered]

    @staticmethod
    def _fetch_message(conn, uid: bytes) -> Optional[Message]:
        typ, data = conn.fetch(uid, "(RFC822)")
        if typ != "OK" or not data:
            return None
        for part in data:
            if isinstance(part, tuple) and len(part) > 1 and isinstance(part[1], (bytes, bytearray)):
                return email.message_from_bytes(part[1])
        return None


# --------------------------------------------------------------------------
# module helpers
# --------------------------------------------------------------------------

def _decode(raw) -> str:
    try:
        return str(make_header(decode_header(str(raw))))
    except Exception:
        return str(raw)


def _pdf_attachments(msg: Message):
    """Yield (filename, bytes) for every PDF attachment."""
    for part in msg.walk():
        name = _decode(part.get_filename() or "")
        ctype = (part.get_content_type() or "").lower()
        if not name.lower().endswith(".pdf") and ctype != "application/pdf":
            continue
        try:
            payload = part.get_payload(decode=True)
        except Exception:
            continue
        if payload:
            yield (name or "statement.pdf"), payload


def _since_date(months: int) -> str:
    """IMAP wants DD-Mon-YYYY. Approximating a month as 31 days is fine for a lower bound."""
    from datetime import date, timedelta
    d = date.today() - timedelta(days=31 * max(1, months))
    return d.strftime("%d-%b-%Y")


def _close_quietly(conn) -> None:
    try:
        conn.close()
    except Exception:
        pass
    try:
        conn.logout()
    except Exception:
        pass


def _friendly_login_error(msg: str) -> str:
    """IMAP login failures are cryptic; each cause has a different fix."""
    low = msg.lower()
    if "application-specific" in low or "app password" in low or "invalid credentials" in low:
        return ("Login rejected. Use an APP PASSWORD, not your normal password — create one at "
                "myaccount.google.com/apppasswords (Google) or your provider's security settings.")
    if "imap" in low and ("disabled" in low or "not enabled" in low):
        return "IMAP is turned off for this mailbox. Enable it in your mail provider's settings."
    if "authenticationfailed" in low.replace(" ", "") or "auth" in low:
        return "Email address or app password is wrong."
    return f"Could not sign in over IMAP: {msg}"
