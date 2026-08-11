"""UPI narration decoding — recover the signal the bank truncated away.

Indian bank statements render UPI transactions as pipe-ish slash-delimited narrations:

    UPI/DR/651819255369/CRED Club/UTIB/cred.club@/payment
    UPI/DR/994595552364/Airtel P/INDB/AirtelPaym/Vodafone
     │   │      │           │      │        │        └ note / remark
     │   │      │           │      │        └ VPA handle (truncated)
     │   │      │           │      └ payee bank IFSC prefix
     │   │      │           └ payee NAME, truncated to ~8 characters
     │   │      └ UPI reference number
     │   └ CR / DR
     └ channel

The counterparty **name is truncated to 8 characters** ("Airtel P", "CRED Clu"), which destroys most
keyword matching. The **VPA handle is the better signal** — `cred.club@`, `AirtelPaym` — because it
encodes the actual payee identity even when the display name is cut off.

So categorization should read BOTH fields, and self-transfers need the account-holder's own name
compared against the payee name, which is exactly what field 4 gives us.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional

#: Channels that appear as the first narration field.
_UPI_PREFIX = re.compile(r"^(?:UPI|IMPS|NEFT|RTGS)\b", re.IGNORECASE)

#: Handles that identify a person-to-person wallet rather than a business.
_P2P_HANDLES = re.compile(r"(?i)@(?:ok|ybl|axl|ibl|paytm|apl|upi|oksbi|okhdfcbank|okicici|okaxis)\b")

#: Bank-account transfer handles: "ICIC-xx123-Some Payee", "IBKL-xx456-Other Name".
_BANK_HANDLE = re.compile(r"^(?P<ifsc>[A-Z]{4})-x+(?P<last3>\d{2,4})-(?P<name>.*)$")


@dataclass(frozen=True)
class UpiParts:
    """Decoded UPI narration. Empty strings where a field is absent."""
    channel: str = ""
    direction: str = ""      # "CR" / "DR" as printed
    ref: str = ""
    payee_name: str = ""     # truncated by the bank to ~8 chars
    payee_bank: str = ""
    vpa: str = ""            # the high-signal field
    note: str = ""

    @property
    def searchable(self) -> str:
        """Everything worth keyword-matching, name and handle together."""
        return " ".join(p for p in (self.payee_name, self.vpa, self.note) if p)

    @property
    def is_bank_transfer(self) -> bool:
        return bool(_BANK_HANDLE.match(self.payee_name))


def parse_upi(description: str) -> Optional[UpiParts]:
    """Split a UPI/IMPS/NEFT narration into fields, or None if it isn't one."""
    if not description or not _UPI_PREFIX.match(description.strip()):
        return None
    f: List[str] = [p.strip() for p in description.strip().split("/")]
    # pad so field access is uniform regardless of how many segments the bank printed
    f += [""] * (7 - len(f)) if len(f) < 7 else []
    return UpiParts(channel=f[0], direction=f[1] if len(f) > 1 else "",
                    ref=f[2] if len(f) > 2 else "", payee_name=f[3] if len(f) > 3 else "",
                    payee_bank=f[4] if len(f) > 4 else "", vpa=f[5] if len(f) > 5 else "",
                    note=f[6] if len(f) > 6 else "")


def counterparty(description: str, merchant: str = "") -> str:
    """Best available name for the other side of a transaction.

    Prefers the VPA handle when the display name looks truncated, since `cred.club@` beats
    `CRED Clu` for both display and matching.
    """
    parts = parse_upi(description)
    if not parts:
        return merchant or ""
    m = _BANK_HANDLE.match(parts.payee_name)
    if m:                                       # "IBKL-xx456-Some Name" -> "Some Name"
        return m.group("name").strip() or parts.payee_name
    name = parts.payee_name or merchant
    # a handle with real words in it is more informative than an 8-char stub
    if parts.vpa and len(name) <= 8 and re.search(r"[A-Za-z]{4}", parts.vpa):
        return parts.vpa.rstrip("@")
    return name


def is_self_transfer_narration(description: str, own_names: List[str]) -> bool:
    """True when the UPI payee name matches the account holder — money moving between own accounts.

    Checked against the payee NAME field only, never the whole narration: the holder's name also
    appears in unrelated positions (remarks, the payer side), which would sweep in real payments.
    Because the bank truncates to 8 characters, comparison is on a prefix.
    """
    parts = parse_upi(description)
    if not parts:
        return False
    target = parts.payee_name.strip().lower()
    m = _BANK_HANDLE.match(parts.payee_name)
    if m:
        target = m.group("name").strip().lower()
    if len(target) < 4:
        return False
    for raw in own_names:
        for token in re.split(r"\s+", (raw or "").strip().lower()):
            if len(token) < 4:
                continue
            # the bank cuts names at ~8 chars, so compare on the shorter of the two
            n = min(len(token), len(target), 8)
            if token[:n] == target[:n]:
                return True
    return False
