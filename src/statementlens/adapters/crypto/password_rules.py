"""Derive statement-PDF passwords from the rule a bank STATES in its email (text or image).

Banks publish the password formula in the statement email — as text (SBI: "last five digits of
mobile + DOB DDMMYY") or an image (RBL). Rather than hard-code each bank, we parse that stated rule
into ordered typed components and derive the exact password.

Design:
- A rule is an ordered list of typed COMPONENTS (mobile[-5:], name[:4].upper(), dob:ddmmyy, ...).
- `parse_rule(text)` is pure: rule-text -> [components] in the order they appear in the sentence.
- `derive(components, hints)` is pure: components + known facts -> ordered candidate passwords.
Open/Closed: support a new phrasing by adding a pattern, never by editing derivation.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

_NUMWORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
             "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}
_DOB_FORMATS = ["ddmmyyyy", "mmddyyyy", "ddmmyy", "mmddyy", "ddmm", "mmyy", "yyyy"]


def _num(word: str) -> Optional[int]:
    word = word.strip().lower()
    return int(word) if word.isdigit() else _NUMWORDS.get(word)


def parse_rule(text: str) -> List[Dict[str, Any]]:
    """Parse a stated password rule into ordered components. [] if none recognized."""
    if not text:
        return []
    tl = text.lower()
    found: List[tuple] = []
    for m in re.finditer(r"last\s+(\w+)\s+digits?\s+of\s+.{0,60}?mobile", tl):
        n = _num(m.group(1))
        if n:
            found.append((m.start(), {"kind": "mobile", "take": n}))
    for m in re.finditer(r"last\s+(\w+)\s+digits?\s+of\s+.{0,60}?card", tl):
        n = _num(m.group(1))
        if n:
            found.append((m.start(), {"kind": "card", "take": n}))
    for m in re.finditer(
        r"first\s+(\w+)\s+(?:letters?|characters?|chars?)\s+of\s+"
        r"(?:the\s+|your\s+|card\s?holder'?s?\s+|account\s?holder'?s?\s+)*name", tl):
        n = _num(m.group(1))
        if not n:
            continue
        window = tl[m.start(): m.end() + 40]
        case = ("upper" if re.search(r"capital|caps\b|block\s+letter|upper", window)
                else "lower" if ("lower" in window or "small" in window) else "any")
        found.append((m.start(), {"kind": "name", "take": n, "case": case}))
    dob_pos = dob_fmt = None
    for fmt in _DOB_FORMATS:
        m = re.search(r"\b" + fmt + r"\b", tl)
        if m and (dob_pos is None or m.start() < dob_pos):
            dob_pos, dob_fmt = m.start(), fmt
    if dob_fmt:
        found.append((dob_pos, {"kind": "dob", "fmt": dob_fmt}))
    found.sort(key=lambda x: x[0])
    return [c for _, c in found]


def _dob_part(dob_digits: str, fmt: str) -> str:
    if len(dob_digits) < 4:
        return ""
    dd, mm = dob_digits[:2], dob_digits[2:4]
    yyyy = dob_digits[4:8] if len(dob_digits) >= 8 else ""
    yy = yyyy[2:] if yyyy else ""
    return {"ddmm": dd + mm, "mmdd": mm + dd, "ddmmyy": dd + mm + yy, "mmddyy": mm + dd + yy,
            "ddmmyyyy": dd + mm + yyyy, "mmddyyyy": mm + dd + yyyy, "mmyy": mm + yy,
            "yyyy": yyyy}.get(fmt, "")


def derive(components: List[Dict[str, Any]], hints: Dict[str, Any]) -> List[str]:
    """Apply components to known facts -> ordered candidate passwords. [] if a fact is missing."""
    if not components:
        return []
    name = re.sub(r"[^A-Za-z]", "", str(hints.get("name") or ""))
    dob = re.sub(r"\D", "", str(hints.get("dob") or ""))
    mobile = re.sub(r"\D", "", str(hints.get("mobile") or ""))
    card = re.sub(r"\D", "", str(hints.get("card_last4") or ""))
    per_part: List[List[str]] = []
    for c in components:
        kind = c["kind"]
        if kind == "mobile":
            if len(mobile) < c["take"]:
                return []
            per_part.append([mobile[-c["take"]:]])
        elif kind == "card":
            if len(card) < c["take"]:
                return []
            per_part.append([card[-c["take"]:]])
        elif kind == "name":
            if len(name) < c["take"]:
                return []
            base = name[: c["take"]]
            if c["case"] == "upper":
                per_part.append([base.upper()])
            elif c["case"] == "lower":
                per_part.append([base.lower()])
            else:
                per_part.append([base.upper(), base.lower(), base.capitalize()])
        elif kind == "dob":
            part = _dob_part(dob, c["fmt"])
            if not part:
                return []
            per_part.append([part])
    out: List[str] = [""]
    for options in per_part:
        out = [prefix + opt for prefix in out for opt in options]
    seen, result = set(), []
    for pw in out:
        if pw and pw not in seen:
            seen.add(pw); result.append(pw)
    return result


def candidates(hints: Dict[str, Any]) -> List[str]:
    """Full candidate list, best-first: explicit customs, rule-derived, then brute-force name/DOB.

    hints: name, dob, mobile, card_last4, custom (explicit list), rule_text (bank-stated rule).
    """
    out: List[str] = []
    seen = set()

    def add(pw: Optional[str]) -> None:
        if pw and pw not in seen:
            seen.add(pw); out.append(pw)

    for pw in hints.get("custom") or []:
        add(str(pw))
    if hints.get("rule_text"):
        for pw in derive(parse_rule(str(hints["rule_text"])), hints):
            add(pw)

    name = (hints.get("name") or "").strip()
    slices = [re.sub(r"[^A-Za-z]", "", w)[:4] for w in re.split(r"\s+", name) if w]
    whole4 = re.sub(r"[^A-Za-z]", "", name)[:4]
    if whole4:
        slices.append(whole4)
    dob = re.sub(r"\D", "", str(hints.get("dob") or ""))
    ddmm = dob[:4] if len(dob) >= 4 else ""
    mmdd = (dob[2:4] + dob[:2]) if len(dob) >= 4 else ""
    ddmmyyyy = dob[:8] if len(dob) >= 8 else ""
    ddmmyy = (dob[:4] + dob[6:8]) if len(dob) >= 8 else ""
    yyyy = dob[4:8] if len(dob) >= 8 else ""
    yy = dob[6:8] if len(dob) >= 8 else ""
    card4 = re.sub(r"\D", "", str(hints.get("card_last4") or ""))[:4]
    mobile = re.sub(r"\D", "", str(hints.get("mobile") or ""))
    mob5 = mobile[-5:] if len(mobile) >= 5 else ""
    for s4 in [s for s in slices if s]:
        for part in (ddmm, ddmmyy, mmdd, ddmmyyyy, yyyy, yy):
            if part:
                add(s4.lower() + part); add(s4.upper() + part); add(s4.capitalize() + part)
    for part in (ddmm, mmdd, yyyy, ddmmyyyy):
        if card4 and part:
            add(card4 + part); add(part + card4)
    for part in (ddmmyy, ddmm, ddmmyyyy):
        if mob5 and part:
            add(mob5 + part); add(part + mob5)
    add(card4 or None)
    add(ddmmyyyy or None)
    return out
