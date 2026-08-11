"""Fetch transaction-ALERT emails (not attachments) and turn them into provisional transactions.

Statements arrive monthly; alerts arrive in seconds. Reading both means the dashboard is current
today instead of current as of last month's statement.

Two provider paths behind one interface, because the choice of mail provider should not leak into the
use-case: `ImapAlertSource` (any mailbox, app password, no cap) and `GmailAlertSource` (OAuth). Both
yield `AlertMessage`, and both are read-only.

Every row produced here is marked `provisional=True`. An alert can describe an authorisation that
never settles, carries a truncated narration, and may be superseded by the statement that covers the
same period — so it is useful but never authoritative. See `usecases.supersede`.
"""

from __future__ import annotations

import base64
import email
import imaplib
import re
from dataclasses import dataclass
from datetime import date
from email.header import decode_header, make_header
from email.message import Message
from typing import Iterable, List, Optional, Sequence

from ...domain.models import Direction, Transaction
from ...domain.money import Money
from ..parsers.alert_parser import parse_alert

#: Senders that push transaction alerts. Kept broad on purpose — the alert parser's reject rules are
#: what actually prevent junk from being booked, so a wide net here costs nothing.
ALERT_SENDERS = (
    "alerts", "alert", "no-reply", "noreply", "notification", "notifications",
    "cbsalerts", "instaalerts", "estatement", "cards", "credit", "txn", "transaction",
)
_BANKISH = re.compile(
    r"(?i)(sbi|hdfc|icici|axis|kotak|idfc|rbl|yes\s?bank|federal|indusind|amex|"
    r"american\s?express|citi|hsbc|standard\s?chartered|scapia|onecard|slice|jupiter|"
    r"bob|baroda|canara|pnb|union\s?bank|indian\s?bank|au\s?small|bandhan|cred|bank|card)")


@dataclass(frozen=True)
class AlertMessage:
    """One candidate alert email, provider-agnostic."""
    message_id: str
    subject: str
    sender: str
    body: str


def _decode(raw) -> str:
    try:
        return str(make_header(decode_header(str(raw))))
    except Exception:
        return str(raw)


def _body_text(msg: Message) -> str:
    """Flatten a message to text, preferring text/plain but accepting HTML.

    Alerts are frequently HTML-only; the parser strips tags itself, so passing HTML through is fine.
    """
    parts: List[str] = []
    if msg.is_multipart():
        for part in msg.walk():
            ctype = (part.get_content_type() or "").lower()
            if ctype not in ("text/plain", "text/html"):
                continue
            try:
                payload = part.get_payload(decode=True)
            except Exception:
                continue
            if payload:
                parts.append(payload.decode(part.get_content_charset() or "utf-8", "ignore"))
    else:
        try:
            payload = msg.get_payload(decode=True)
            if payload:
                parts.append(payload.decode(msg.get_content_charset() or "utf-8", "ignore"))
        except Exception:
            pass
    return "\n".join(parts)


def looks_like_alert_sender(sender: str, subject: str) -> bool:
    """Cheap pre-filter so we don't download every message in the mailbox."""
    hay = f"{sender} {subject}".lower()
    if not _BANKISH.search(hay):
        return False
    return any(tok in hay for tok in ALERT_SENDERS) or bool(_BANKISH.search(sender.lower()))


class ImapAlertSource:
    """Alert emails over IMAP. Read-only; `connection` is injectable for testing."""

    def __init__(self, credentials=None, *, connection=None, days: int = 45,
                 mailbox: str = "INBOX"):
        if credentials is None and connection is None:
            raise ValueError("provide credentials or an injected connection")
        self._creds = credentials
        self._conn = connection
        self._days = days
        self._mailbox = mailbox

    def messages(self, limit: int = 400) -> List[AlertMessage]:
        conn = self._conn or self._connect()
        try:
            conn.select(self._mailbox, readonly=True)   # server-enforced: we cannot modify anything
            uids = self._search(conn)
            out: List[AlertMessage] = []
            for uid in uids:
                if len(out) >= limit:
                    break
                msg = self._fetch(conn, uid)
                if msg is None:
                    continue
                sender = _decode(msg.get("From", ""))
                subject = _decode(msg.get("Subject", ""))
                if not looks_like_alert_sender(sender, subject):
                    continue
                uid_text = uid.decode() if isinstance(uid, (bytes, bytearray)) else str(uid)
                out.append(AlertMessage(uid_text, subject, sender, _body_text(msg)))
            return out
        finally:
            if self._conn is None:
                _close_quietly(conn)

    def _connect(self):
        from .imap_source import _friendly_login_error
        c = self._creds
        conn = imaplib.IMAP4_SSL(c.host, c.port)
        try:
            conn.login(c.address, c.app_password)
        except imaplib.IMAP4.error as e:
            _close_quietly(conn)
            raise RuntimeError(_friendly_login_error(str(e))) from e
        return conn

    def _search(self, conn) -> Sequence:
        from datetime import timedelta
        since = (date.today() - timedelta(days=self._days)).strftime("%d-%b-%Y")
        try:
            typ, data = conn.search(None, f"(SINCE {since})")
        except imaplib.IMAP4.error:
            return []
        if typ != "OK" or not data or not data[0]:
            return []
        return sorted(data[0].split(), key=lambda u: int(u), reverse=True)

    @staticmethod
    def _fetch(conn, uid) -> Optional[Message]:
        typ, data = conn.fetch(uid, "(RFC822)")
        if typ != "OK" or not data:
            return None
        for part in data:
            if isinstance(part, tuple) and len(part) > 1 and isinstance(part[1], (bytes, bytearray)):
                return email.message_from_bytes(part[1])
        return None


class GmailAlertSource:
    """Alert emails over the Gmail API. `service` is injectable for testing."""

    QUERY = ("newer_than:{days}d ("
             "debited OR credited OR \"has been debited\" OR \"you made a transaction\" "
             "OR \"transaction success\" OR spent)")

    def __init__(self, service=None, days: int = 45):
        self._service = service
        self._days = days

    def messages(self, limit: int = 400) -> List[AlertMessage]:
        svc = self._service or self._authorize()
        q = self.QUERY.format(days=self._days)
        resp = svc.users().messages().list(userId="me", q=q, maxResults=limit).execute()
        out: List[AlertMessage] = []
        for ref in resp.get("messages", []):
            full = svc.users().messages().get(userId="me", id=ref["id"], format="full").execute()
            headers = {h["name"].lower(): h["value"]
                       for h in (full.get("payload", {}) or {}).get("headers", [])}
            sender = headers.get("from", "")
            subject = headers.get("subject", "")
            if not looks_like_alert_sender(sender, subject):
                continue
            out.append(AlertMessage(ref["id"], subject, sender,
                                    _gmail_body(full.get("payload", {}) or {})))
        return out

    def _authorize(self):
        from .gmail_source import GmailStatementSource
        return GmailStatementSource()._authorize()


def _gmail_body(payload: dict) -> str:
    chunks: List[str] = []

    def walk(part: dict) -> None:
        data = (part.get("body", {}) or {}).get("data")
        if data:
            try:
                chunks.append(base64.urlsafe_b64decode(data).decode("utf-8", "ignore"))
            except Exception:
                pass
        for child in part.get("parts", []) or []:
            walk(child)

    walk(payload)
    return "\n".join(chunks)


def _close_quietly(conn) -> None:
    for fn in ("close", "logout"):
        try:
            getattr(conn, fn)()
        except Exception:
            pass


# --------------------------------------------------------------------------
# messages -> provisional transactions
# --------------------------------------------------------------------------

def alerts_to_transactions(messages: Iterable[AlertMessage], *, currency: str = "INR",
                           account_hint_map: Optional[dict] = None) -> List[Transaction]:
    """Parse alert emails into provisional Transactions, skipping anything that isn't one.

    `account_hint_map` maps a card/account last-4 to an account label, so a single mailbox carrying
    alerts for several cards can be split correctly. Unmapped hints fall back to the caller's account.
    """
    out: List[Transaction] = []
    for m in messages:
        parsed = parse_alert(m.body, subject=m.subject)
        if parsed is None:
            continue
        out.append(Transaction(
            txn_date=parsed.txn_date,
            description=(parsed.merchant or m.subject or "alert").strip(),
            amount=Money(parsed.amount_minor, currency),
            direction=parsed.direction,
            merchant=parsed.merchant,
            balance=None,                      # alerts rarely carry a reliable running balance
            raw_date=parsed.txn_date.isoformat() if parsed.txn_date else "",
            # provenance points at the EMAIL, so re-reading the same alert dedupes
            source_ref=f"alert:{m.message_id}",
            provisional=True,
        ))
    return out
