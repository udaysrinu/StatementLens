"""Transaction tagging — automatic by default, correctable by hand.

**Every transaction is tagged automatically.** Zero manual work is the baseline promise; the user
should never face a wall of untagged rows. Manual input exists only as the *correction* path:
re-tagging something the categorizer got wrong, and attaching a free-text note for context the
statement narration can't carry ("this was the fridge, not salary").

Three design choices, all taken from how CRED Money does it:

1. **The vocabulary is FIXED and FLAT.** 22 tags, no subcategories, no user-created tags. A closed
   set is what makes "grocery went up 12%" comparable across months. Free-form tags fragment into
   "food", "Food", "food delivery" and every aggregate silently degrades.
2. **A correction is remembered per merchant.** Fixing "Fresh N" to grocery once fixes every past
   and future "Fresh N" — otherwise the user re-corrects the same merchant forever and gives up.
3. **A correction outranks the categorizer permanently.** Re-running ingest must never silently
   revert a fix the user made; that is the fastest way to lose their trust in the numbers.

`SELF_TRANSFER` is a real tag, not a hack: it's how a row gets marked as the user's own money
moving, which removes it from both sides of the cash flow (see `flows.py`).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, replace
from typing import Dict, Iterable, List, Optional

from ..domain.models import Transaction

# ---------------------------------------------------------------------------
# The closed tag vocabulary
# ---------------------------------------------------------------------------

SELF_TRANSFER_TAG = "self transfer"
UNTAGGED = "untagged"

#: (tag, icon-key) — the flat set. Order is the display order: alphabetical, with `untagged` last,
#: matching CRED's picker so the position of a tag is stable and learnable.
TAGS: tuple[tuple[str, str], ...] = (
    ("apps and software", "apps"),
    ("bank charges", "bill"),
    ("bills", "bill"),
    ("cash transactions", "cash"),
    ("credit card bill", "card"),
    ("donations", "gift"),
    ("education", "edu"),
    ("entertainment", "play"),
    ("food and drinks", "food"),
    ("fund transfers", "transfer"),
    ("government and taxes", "gov"),
    ("grocery", "grocery"),
    ("health and wellness", "health"),
    ("insurance", "shield"),
    ("investment", "invest"),
    ("loans", "loan"),
    ("people", "person"),
    ("professional services", "work"),
    ("rent", "home"),
    (SELF_TRANSFER_TAG, "self"),
    ("shopping", "cart"),
    ("transportation", "car"),
    ("travel", "travel"),
    (UNTAGGED, "dots"),
)

TAG_NAMES: tuple[str, ...] = tuple(t for t, _ in TAGS)
TAG_ICONS: Dict[str, str] = dict(TAGS)

#: Maps our legacy internal category names onto the public tag vocabulary, so existing
#: keyword-categorizer output and user tags land in the same buckets.
_LEGACY_ALIASES = {
    "food & dining": "food and drinks",
    "food": "food and drinks",
    "groceries": "grocery",
    "bills & utilities": "bills",
    "card bills": "credit card bill",
    "investments": "investment",
    "transfers (people)": "people",
    "transfers (in)": "people",
    "cash/atm": "cash transactions",
    "salary/income": "professional services",
    "fees & charges": "bank charges",
    "other": UNTAGGED,
    "other income": UNTAGGED,
    "": UNTAGGED,
}


def normalize_tag(value: Optional[str]) -> str:
    """Map any category/tag string onto the closed vocabulary. Unknown values become `untagged`.

    Never invents a tag — an unrecognised label becoming `untagged` is honest, whereas keeping it
    would quietly grow the vocabulary and break cross-month comparability.
    """
    v = (value or "").strip().lower()
    if v in TAG_ICONS:
        return v
    return _LEGACY_ALIASES.get(v, UNTAGGED)


# ---------------------------------------------------------------------------
# User overrides
# ---------------------------------------------------------------------------

@dataclass
class TagStore:
    """User *corrections* layered over the automatic tags, plus free-text notes.

    Nothing here is required for the app to work — with an empty store every transaction still gets
    an automatic tag. This only records the places where the user disagreed with us, and any notes
    they attached.

    Merchant-level corrections are the important half: they are what stop the user re-fixing the
    same payee forever. Plain dicts, so any persistence adapter can serialize this as-is.
    """
    by_merchant: Dict[str, str] = None
    by_ref: Dict[str, str] = None
    notes: Dict[str, str] = None

    def __post_init__(self):
        self.by_merchant = self.by_merchant or {}
        self.by_ref = self.by_ref or {}
        self.notes = self.notes or {}

    def correct_merchant(self, merchant: str, tag: str,
                         member_refs: Optional[Iterable[str]] = None) -> None:
        """Fix this merchant's tag everywhere — past rows and future ingests alike.

        `member_refs` are the transaction refs belonging to this merchant; any single-row override
        among them is DROPPED. Without that, an older per-row correction keeps shadowing the new
        merchant-wide one (by_ref wins in `resolve`) and the user taps a tag to no visible effect.
        """
        t = normalize_tag(tag)
        key = merchant.strip().lower()
        if t == UNTAGGED:
            self.by_merchant.pop(key, None)
        else:
            self.by_merchant[key] = t
        for ref in (member_refs or ()):
            self.by_ref.pop(ref, None)

    def correct_one(self, source_ref: str, tag: str) -> None:
        """Fix a single transaction without creating a merchant-wide rule.

        Needed because one payee legitimately spans tags — the same person can be rent one month
        and people the next.
        """
        if not source_ref:
            raise ValueError("source_ref required to correct a single transaction")
        self.by_ref[source_ref] = normalize_tag(tag)

    def add_note(self, source_ref: str, note: str) -> None:
        """Attach (or clear) a free-text note on one transaction.

        Notes carry the context a bank narration never will — "this was the fridge, adjusted against
        salary". Free text on purpose: it feeds no aggregate, so it can't fragment one.
        """
        if not source_ref:
            raise ValueError("source_ref required to note a transaction")
        note = (note or "").strip()
        if note:
            self.notes[source_ref] = note
        else:
            self.notes.pop(source_ref, None)

    def note_for(self, txn: Transaction) -> str:
        return self.notes.get(txn.source_ref, "") if txn.source_ref else ""

    def resolve(self, txn: Transaction) -> Optional[str]:
        """The user's correction for this transaction, if any. One-off beats merchant rule."""
        if txn.source_ref and txn.source_ref in self.by_ref:
            return self.by_ref[txn.source_ref]
        return self.by_merchant.get((txn.merchant or "").strip().lower())


def apply_tags(txns: Iterable[Transaction], store: Optional[TagStore] = None) -> List[Transaction]:
    """Auto-tag everything, then let user corrections override.

    Order matters: the automatic tag is always computed, so a transaction is never left untagged
    just because the user hasn't looked at it.
    """
    store = store or TagStore()
    out: List[Transaction] = []
    for t in txns:
        tag = store.resolve(t) or normalize_tag(t.category)
        out.append(t if t.category == tag else t.with_category(tag))
    return out


def group_by_tag(txns: Iterable[Transaction], *, debits_only: bool = True) -> List[Dict[str, object]]:
    """Tag-wise grouping with share-of-total — the "spends by tag" view.

    Excludes `self transfer` from the total, since your own money moving is not spending; leaving it
    in would make one meaningless row dominate the breakdown.
    """
    totals: Dict[str, int] = defaultdict(int)
    counts: Dict[str, int] = defaultdict(int)
    grand = 0
    for t in txns:
        if debits_only and not t.is_debit:
            continue
        tag = normalize_tag(t.category)
        if tag == SELF_TRANSFER_TAG:
            continue
        totals[tag] += t.amount.minor
        counts[tag] += 1
        grand += t.amount.minor

    rows = [{"tag": tag, "icon": TAG_ICONS.get(tag, "dots"), "amount": amt,
             "count": counts[tag], "share": (amt / grand) if grand else 0.0}
            for tag, amt in totals.items()]
    rows.sort(key=lambda r: -r["amount"])
    return rows


def untagged_count(txns: Iterable[Transaction]) -> int:
    """Rows the auto-tagger couldn't place — a measure of categorizer quality, not user homework."""
    return sum(1 for t in txns if normalize_tag(t.category) == UNTAGGED)


def review_queue(txns: Iterable[Transaction], store: Optional[TagStore] = None,
                 limit: int = 20) -> List[Dict[str, object]]:
    """Merchants whose automatic tag is worth a human glance, biggest money first.

    Only surfaces what the auto-tagger could NOT confidently place (`untagged`), and skips anything
    the user already corrected. Ordered by total value, not recency: confirming one ₹97k payee fixes
    more of the breakdown than twenty ₹84 ones. This is a short, finite queue — not an inbox.
    """
    store = store or TagStore()
    agg: Dict[str, Dict[str, object]] = {}
    for t in txns:
        if not t.merchant or store.resolve(t):          # already corrected → leave it alone
            continue
        if not t.is_debit:                              # credits aren't spends; wrong queue
            continue
        if normalize_tag(t.category) != UNTAGGED:       # confidently auto-tagged → don't nag
            continue
        key = t.merchant.strip().lower()
        row = agg.setdefault(key, {"merchant": t.merchant, "amount": 0, "count": 0,
                                   "suggested": UNTAGGED})
        row["amount"] += t.amount.minor
        row["count"] += 1
    out = sorted(agg.values(), key=lambda r: -r["amount"])
    return out[:limit]
