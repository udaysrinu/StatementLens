"""Find transactions that are probably the same merchant, so one correction can fix them all.

On real card data a single merchant appeared under **54 distinct narration strings** — payment
gateway prefixes (`RAZ*`, `PYU*`, `PPSL*`, `CAS*`), legal entity names (`BUNDL TECHNOLOGIES` for
Swiggy), city suffixes glued on with and without a space, reward-programme wording, reference numbers,
and case variants. Asking the user to re-tag each of those is asking them to give up.

The approach: reduce a narration to a **merchant key** by stripping the parts that vary and keeping
the part that identifies, then group by that key. Every suggestion carries a `reason` so the UI can
say *why* two rows are grouped — a silent "we think these match" invites mistrust, and the user is
the one who decides via multi-select.

Deliberately conservative: it is far better to under-group (user corrects two groups) than to
over-group (user's correction lands on unrelated transactions they now have to undo).
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence

from ..domain.models import Transaction
from ..adapters.categorize import upi

# --------------------------------------------------------------------------
# narration -> merchant key
# --------------------------------------------------------------------------

#: Payment-gateway / aggregator prefixes. These identify who PROCESSED the payment, not who was paid,
#: so they must come off before comparing. Seen on real statements as RAZ*, PYU*, PPSL*, CAS*, RSP*…
_GATEWAY_PREFIX = re.compile(
    r"""(?ix)^\s*(?:
        raz(?:orpay)? | pyu | payu | ppsl | cas | rsp | tps | ptm | pay | bppy | upi | ecom |
        pos | nfs | ach | ins | mmt | ibl | inb | neft | imps | rtgs | emi
    )\s*\*+\s*""")

#: Any leftover `WORD*` token at the start (a gateway we don't have listed).
_ANY_STAR_PREFIX = re.compile(r"^\s*[A-Za-z0-9]{2,10}\s*\*+\s*")

#: Leading transaction-TYPE words that sit in front of the gateway prefix, e.g. "EMI RAZ*SWIGGY".
#: Stripped repeatedly with the gateway prefix so any order of the two resolves.
_LEADING_TYPE = re.compile(r"(?ix)^\s*(?:emi|pos|ecom|inb|ins|adj|int|chq|nfs|atw|vps)\b[\s*]*")

#: Reference/authorisation numbers, dates and long digit runs — pure noise for identity.
_REFERENCE = re.compile(r"""(?ix)
      \(\s*ref\#?[^)]*\) | \bref\#?\s*[a-z0-9]{6,} | \bauthorization\s+code:?\s*\d+
    | \b[a-z]{0,3}\d{9,}\b | \b\d{2}[/-]\d{2}[/-]\d{2,4}\b | \b\d{2}:\d{2}(:\d{2})?\b
""")

#: Reward-programme and adjustment wording wrapped around a merchant name.
_PROGRAMME = re.compile(r"""(?ix)
      ^\s*adj\b | \b\d{1,2}\s*%\s* | cash\s?back
    # underscore is a word char, so \b never fires in "Cashback_Reversal"; and banks truncate
    # mid-word, so match a PREFIX of "reversal" rather than requiring the whole word
    | _* reversa\w* | reversl
    | \bblck\b | \bornge\b | \bcb\b | \bmilestone\b | \bstatement\s+credit\b
""")

#: Corporate suffixes that differ between a card statement and a UPI narration for the same payee.
_CORPORATE = re.compile(r"""(?ix)
    \b(?:pvt|private|ltd|limited|limite|llp|inc|corp|corporat(?:ion)?|technologies|technology|
        tech|india|indi|services|service|solutions|solutio|payments|payment|enterprises|
        retail|company|co)\b\.?
""")

#: Indian city / place names that get appended, often without a separating space.
_CITIES = (
    "bengaluru", "bangalore", "hyderabad", "hyderaba", "mumbai", "delhi", "new delhi", "gurgaon",
    "gurgoan", "gurugram", "noida", "chennai", "kolkata", "pune", "ahmedabad", "jaipur", "lucknow",
    "visakhapatnam", "visakhapatna", "vizag", "kochi", "chandigarh", "indore", "bhopal", "nagpur",
    "surat", "patna", "thane", "faridabad", "ghaziabad", "rangareddy", "ranga red", "fatorda", "goa",
    "anand", "chenna", "mumba", "banglore",
)
_CITY_RE = re.compile(r"(?i)(" + "|".join(sorted(_CITIES, key=len, reverse=True)) + r")\s*$")

#: Brands whose legal entity name differs from the consumer name. Small and explicit on purpose —
#: an alias table that guesses would silently merge unrelated merchants.
_ENTITY_ALIASES = {
    "bundl": "swiggy",
    "eternal": "zomato",
    "one97": "paytm",
    "onecommunicat": "paytm",
    "aditya birla lifestyle": "abfrl",
    "hennes n mauritz": "h&m",
    "hennes mauritz": "h&m",
}

#: Web-checkout wrappers: "WWW SWIGGY IN BANGALORE" is the same payee as "SWIGGY".
_WEB_WRAPPER = re.compile(r"(?ix) ^\s*w{3}[\s.]* | [\s.]*\b(?:in|com|co\.?in|net|org)\b\s*$")

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def group_key(txn: Transaction) -> str:
    """Merchant identity PLUS direction.

    A merchant's purchases and its refunds/cashbacks are the same payee but must not be bulk-retagged
    together: applying "food and drinks" to a cashback row would put money-in into a spend category,
    which is one of the bugs this whole area exists to prevent. Splitting by direction keeps the
    convenience without the footgun.
    """
    key = merchant_key(txn)
    if not key:
        return ""
    return f"{key}|{'C' if not txn.is_debit else 'D'}"


def merchant_key(txn: Transaction) -> str:
    """A stable identity for the payee behind a narration, or "" when nothing usable remains.

    Runs the strips in order — gateway prefix, references, programme wording, corporate suffixes,
    trailing city — then collapses to lowercase alphanumerics so spacing variants converge
    ("BUNDL TECHNOLOGIESBENGALURU" and "BUNDL TECHNOLOGIES BENGALURU" become one key).
    """
    # a UPI narration has a dedicated payee field; use the decoder rather than guessing
    parts = upi.parse_upi(txn.description)
    if parts and (parts.payee_name or parts.vpa):
        raw = upi.counterparty(txn.description, txn.merchant)
    else:
        raw = txn.merchant or txn.description

    s = str(raw or "")
    s = _REFERENCE.sub(" ", s)
    # a type word and a gateway prefix can appear in either order, so alternate until neither matches
    for _ in range(3):
        before = s
        s = _LEADING_TYPE.sub("", s)
        s = _GATEWAY_PREFIX.sub("", s)
        s = _ANY_STAR_PREFIX.sub("", s)
        if s == before:
            break
    s = _PROGRAMME.sub(" ", s)
    for _ in range(2):                   # "www … in" needs both ends stripped
        s = _WEB_WRAPPER.sub(" ", s).strip()
    s = _CITY_RE.sub("", s.strip())
    s = _CORPORATE.sub(" ", s)
    s = _CITY_RE.sub("", s.strip())      # a city can sit behind a corporate suffix
    key = _NON_ALNUM.sub("", s.lower())

    # collapse a known legal-entity name onto the consumer brand
    for entity, brand in _ENTITY_ALIASES.items():
        e = _NON_ALNUM.sub("", entity)
        if key.startswith(e):
            return brand
    # a key that is only digits identifies nothing
    return "" if key.isdigit() else key


def display_name(txn: Transaction) -> str:
    """The nicest human label available for a transaction."""
    return (txn.merchant or txn.description or "").strip()[:60]


# --------------------------------------------------------------------------
# similarity
# --------------------------------------------------------------------------

@dataclass
class SimilarGroup:
    """Transactions that probably share a merchant, with the reason they were grouped."""
    key: str
    label: str
    reason: str
    transactions: List[Transaction] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.transactions)

    @property
    def total_minor(self) -> int:
        return sum(t.amount.minor for t in self.transactions)

    @property
    def current_tags(self) -> List[str]:
        """Distinct tags currently on these rows — more than one means they disagree today."""
        return sorted({(t.category or "").strip() for t in self.transactions if t.category})

    def as_dict(self) -> Dict[str, object]:
        return {
            "key": self.key,
            "label": self.label,
            "reason": self.reason,
            "count": self.count,
            "total": self.total_minor,
            "current_tags": self.current_tags,
            "refs": [t.source_ref for t in self.transactions if t.source_ref],
            "sample": [
                {"ref": t.source_ref,
                 "date": t.txn_date.isoformat() if t.txn_date else "",
                 "desc": display_name(t),
                 "amount": t.amount.minor,
                 "tag": t.category or "",
                 "dir": "C" if not t.is_debit else "D"}
                for t in sorted(self.transactions,
                                key=lambda x: (x.txn_date is None, x.txn_date), reverse=True)
            ],
        }


def find_similar(target: Transaction, universe: Iterable[Transaction], *,
                 limit: int = 200) -> Optional[SimilarGroup]:
    """Rows in `universe` that share `target`'s merchant identity, excluding `target` itself.

    Returns None when nothing else matches, so the UI can skip the multi-select entirely rather than
    showing an empty list.
    """
    key = group_key(target)
    if not key or len(merchant_key(target)) < 3:      # too generic to group safely
        return None

    matches = [t for t in universe
               if t.source_ref != target.source_ref and group_key(t) == key]
    if not matches:
        return None

    variants = {display_name(t) for t in matches} | {display_name(target)}
    reason = _explain(target, matches, variants)
    return SimilarGroup(key=key, label=display_name(target), reason=reason,
                        transactions=matches[:limit])


def _explain(target: Transaction, matches: Sequence[Transaction], variants: set) -> str:
    """Say WHY these were grouped, in the user's terms. Trust needs a visible reason."""
    n = len(matches)
    if len(variants) > 1:
        return (f"{n} more transaction{'s' if n != 1 else ''} look like the same merchant, "
                f"written {len(variants)} different ways on your statements")
    return f"{n} more transaction{'s' if n != 1 else ''} from the same merchant"


def group_all(txns: Iterable[Transaction], *, min_size: int = 2,
              only_tag: Optional[str] = None) -> List[SimilarGroup]:
    """Every multi-row merchant group, largest money first — the "clean up my tags" view.

    `only_tag` restricts to groups whose rows carry that tag, which is how the review queue offers
    "here are the untagged merchants worth fixing".
    """
    buckets: Dict[str, List[Transaction]] = defaultdict(list)
    for t in txns:
        key = group_key(t)
        if key and len(merchant_key(t)) >= 3:
            buckets[key].append(t)

    out: List[SimilarGroup] = []
    for key, rows in buckets.items():
        if len(rows) < min_size:
            continue
        if only_tag and not any((t.category or "") == only_tag for t in rows):
            continue
        variants = {display_name(t) for t in rows}
        label = max(variants, key=len)          # the longest variant is usually the most readable
        out.append(SimilarGroup(key=key, label=label,
                                reason=_explain(rows[0], rows[1:], variants),
                                transactions=rows))
    out.sort(key=lambda g: -g.total_minor)
    return out


def disagreeing_groups(txns: Iterable[Transaction]) -> List[SimilarGroup]:
    """Merchant groups whose rows currently carry DIFFERENT tags.

    These are the highest-value corrections available: the same merchant filed inconsistently means
    at least one of the tags is wrong, and every aggregate built on them is off.
    """
    return [g for g in group_all(txns) if len(g.current_tags) > 1]
