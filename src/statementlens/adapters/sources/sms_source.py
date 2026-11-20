"""Bank SMS from macOS Messages — the only live feed for SBI UPI, which sends no email for it.

With iPhone "Text Message Forwarding" on, every SMS lands in ~/Library/Messages/chat.db within
seconds, over iCloud (no LAN needed). This reads that database READ-ONLY and yields the same
`AlertMessage` the email sources do, so one parser and one reconcile path serve both.

Recent macOS stores the text in `attributedBody`, an archived NSAttributedString, with `text` NULL.
The plain string sits after the `NSString` class marker as a length-prefixed UTF-8 run; that is all
that is decoded here (stdlib only, no PyObjC).
"""
from __future__ import annotations

import os
import re
import sqlite3
import time
from typing import List, Optional

from .alert_email_source import AlertMessage

#: Indian bank SMS come from DLT headers like "SBIUPI-S", "CBSSBI-S", "AD-HDFCBK". Only senders whose
#: header names a bank are read — never personal threads.
_BANK_HEADER = re.compile(
    r"(?i)^(?:[A-Z]{2}-)?(?:SBI|CBSSBI|HDFC|ICICI|IPAY|AXIS|KOTAK|RBL|IDFC|YES|INDUS|BOB|BARODA|"
    r"FEDBNK|FEDERAL|SCAPIA|ONECARD|AMEX|CITI|HSBC|SLICE)[A-Z0-9]*(?:-[A-Z])?$")

#: Messages stores dates as nanoseconds since 2001-01-01.
_APPLE_EPOCH = 978307200


def body_text(blob: Optional[bytes]) -> Optional[str]:
    """The plain string inside an archived NSAttributedString, or None."""
    if not blob:
        return None
    i = blob.find(b"NSString")
    if i < 0:
        return None
    j = blob.find(b"+", i) + 1
    if j <= 0 or j >= len(blob):
        return None
    n = blob[j]; j += 1
    if n == 0x81:                       # lengths over 127 bytes take a 2-byte little-endian field
        n = int.from_bytes(blob[j:j + 2], "little"); j += 2
    elif n == 0x82:
        n = int.from_bytes(blob[j:j + 3], "little"); j += 3
    return blob[j:j + n].decode("utf-8", "replace")


class MacMessagesSource:
    """`messages()` → bank SMS from the last `days` days, newest first."""

    def __init__(self, path: Optional[str] = None, days: int = 45):
        self.path = os.path.expanduser(path or "~/Library/Messages/chat.db")
        self.days = days

    def messages(self) -> List[AlertMessage]:
        if not os.path.exists(self.path):
            return []
        since_ns = int((time.time() - _APPLE_EPOCH - self.days * 86400) * 1e9)
        db = sqlite3.connect(f"file:{self.path}?mode=ro", uri=True)
        try:
            rows = db.execute(
                "SELECT m.guid, h.id, m.text, m.attributedBody FROM message m"
                " JOIN handle h ON m.handle_id=h.ROWID"
                " WHERE m.is_from_me=0 AND m.date > ? ORDER BY m.date DESC", (since_ns,)).fetchall()
        finally:
            db.close()
        out = []
        for guid, sender, text, blob in rows:
            if not _BANK_HEADER.match(sender or ""):
                continue
            body = text or body_text(blob)
            if body:
                out.append(AlertMessage(message_id=f"sms:{guid}", subject="", sender=sender, body=body))
        return out
