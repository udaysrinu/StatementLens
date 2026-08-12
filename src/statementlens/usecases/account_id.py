"""Work out WHICH account a statement belongs to, instead of trusting one CLI flag.

Ingesting a folder with `--account SBI` labels every file `SBI`, so a savings account and three
credit cards end up merged into one ledger. That is not cosmetic: the card frame
(charges/payments/refunds) is chosen per account, self-transfer detection compares legs across
accounts, and "spent" totals mix a card's charges with the bank debit that paid that card's bill —
counting the same money twice.

Statement filenames and their text carry the account identity reliably enough to split them:

    8959894511130062026.pdf                        -> SBI savings, account tail 0062026
    5268XXXXXXXX85_01-07-2026.PDF                  -> card ending 85
    4315XXXXXXXX4007_..._Retail_Amazon_NORM.pdf    -> card ending 4007, "Amazon" variant
    6530XXXXXXXX4001_..._Retail_Sapphiro_NORM.pdf  -> card ending 4001, "Sapphiro" variant

The masked card number is the strongest signal — it is stable across months and unique per card. A
label is only ever derived, never invented: with nothing to go on, the caller's account name is kept,
so behaviour is unchanged for anyone passing a single real account.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Optional

#: A masked card number: 4-6 leading digits, X/x/* masking, then the last 3-4 digits.
_MASKED_CARD = re.compile(r"(?P<bin>\d{4,6})[Xx*]{4,}(?P<last4>\d{2,4})")

#: A bare long account number, as SBI e-statements use for the filename.
_LONG_ACCOUNT = re.compile(r"^(?P<acct>\d{12,20})(?:[_.-]|$)")

#: Card-programme names issuers put in the filename. Useful because one issuer can have several cards.
_PROGRAMME = re.compile(
    r"(?i)\b(amazon|sapphiro|coral|rubyx|platinum|millennia|regalia|infinia|moneyback|"
    r"swiggy|flipkart|tata\s?neu|simplyclick|simplysave|cashback|smartbuy|marriott|"
    r"emeralde|times|makemytrip|indianoil|bpcl|vistara|atlas|magnus|select|reserve)\b")

#: Issuer hints from the statement TEXT, checked only in the first page or so.
_ISSUERS = (
    ("HDFC", r"(?i)\bhdfc\s*bank\b"),
    # A bare "SBI" counts, but only near account/branch wording — the token also appears inside
    # merchant narrations ("SBIPG", "SBI COLLECT") on OTHER banks' statements, and matching those
    # would mislabel the account.
    ("SBI", r"(?i)\bstate\s+bank\s+of\s+india\b|\bsbi\s*card\b|\bonlinesbi\b|"
            r"\bsbi\b(?=[\s\S]{0,400}?(?:home\s+branch|ifsc|account\s+statement|customer))|"
            r"(?:home\s+branch|ifsc|customer)[\s\S]{0,400}?\bsbi\b"),
    ("ICICI", r"(?i)\bicici\s*bank\b"),
    ("Axis", r"(?i)\baxis\s*bank\b"),
    ("Kotak", r"(?i)\bkotak\b"),
    ("IDFC", r"(?i)\bidfc\s*first\b"),
    ("RBL", r"(?i)\brbl\s*bank\b"),
    ("Amex", r"(?i)american\s+express"),
    ("Scapia", r"(?i)\bscapia\b|\bfederal\s+bank\b"),
    ("OneCard", r"(?i)\bonecard\b"),
)


def account_label(source_name: str, text: str = "", *, fallback: str = "Account") -> str:
    """A stable, human-readable account label for one statement.

    `fallback` is returned unchanged when nothing identifying is found — the label is never guessed
    from thin air, because a wrong split is as damaging as a wrong merge.
    """
    name = source_name or ""
    issuer = _issuer_from_text(text)
    programme = _programme(name) or _programme(text[:2000])

    card = _MASKED_CARD.search(name) or _MASKED_CARD.search(text[:2000])
    if card:
        issuer = issuer or _issuer_from_bin(card.group("bin"))
        # The programme name is NOT part of the identity: the same card's statements do not all
        # mention it, so including it would file January and February as different accounts. The
        # masked tail alone identifies the card.
        return f"{issuer or 'Card'} ••{card.group('last4')}"

    acct = _LONG_ACCOUNT.match(name)
    if acct:
        stable = _strip_trailing_period(acct.group("acct"))
        # SBI e-statement filenames start with a 5-digit product prefix; recovering the issuer from it
        # keeps `relabel` (which has only the filename) as informative as a fresh ingest.
        issuer = issuer or _ACCOUNT_PREFIX_ISSUERS.get(stable[:5])
        return f"{issuer or 'Bank'} ••{stable[-4:]}"

    if issuer:
        return issuer
    return fallback


def _strip_trailing_period(digits: str) -> str:
    """Remove a trailing statement date so every month of one account yields the same label.

    SBI e-statement filenames are `<11-digit account><DDMMYYYY>`. Rather than assume a fixed width,
    the trailing 8 or 6 digits are removed only if they PARSE as a real date — otherwise they are part
    of the account number and must be kept.
    """
    for width, fmt in ((8, "%d%m%Y"), (6, "%m%Y"), (6, "%d%m%y")):
        if len(digits) > width + 6:
            tail = digits[-width:]
            try:
                datetime.strptime(tail, fmt)
            except ValueError:
                continue
            return digits[:-width]
    return digits


#: Card BINs (first 6 digits) seen in real statement filenames, so the issuer can be recovered when
#: only the filename is available — e.g. when relabelling an existing store without re-reading PDFs.
#: Leading digits of bank e-statement account numbers, per issuer.
_ACCOUNT_PREFIX_ISSUERS = {"89598": "SBI", "20000": "SBI", "30772": "SBI"}

#: Keyed on FOUR digits: statements mask everything after the first four, so a 6-digit BIN is never
#: available from a filename. This is what lets `relabel` name the issuer without re-decrypting
#: every PDF. Text-derived detection still wins when the statement body is available.
_BIN_ISSUERS = {
    "5268": "HDFC", "4315": "ICICI", "6530": "ICICI",
    "4218": "SBI", "6528": "SBI", "4555": "Axis", "4147": "Axis",
}


def _issuer_from_bin(bin_digits: str) -> Optional[str]:
    return _BIN_ISSUERS.get((bin_digits or "")[:4])


def _issuer_from_text(text: str) -> Optional[str]:
    head = (text or "")[:3000]
    for label, pattern in _ISSUERS:
        if re.search(pattern, head):
            return label
    return None


def _programme(s: str) -> Optional[str]:
    m = _PROGRAMME.search(s or "")
    if not m:
        return None
    return m.group(1).title()


def is_same_account(a: str, b: str) -> bool:
    """Whether two labels denote the same account, comparing the masked tail when both have one."""
    ta, tb = _tail(a), _tail(b)
    if ta and tb:
        return ta == tb
    return a.strip().lower() == b.strip().lower()


def _tail(label: str) -> Optional[str]:
    m = re.search(r"••\s*(\d{2,4})", label or "")
    return m.group(1) if m else None
