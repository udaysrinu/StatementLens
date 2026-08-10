"""Money value object — the single source of truth for monetary values.

Money is stored as an integer number of the currency's minor unit (paise for INR, cents for USD),
so arithmetic is exact. Floats are never used for money anywhere in the codebase; this class is the
only sanctioned way to construct a monetary value, which keeps the "never float" invariant local.

Immutable, hashable, and totally ordered so it can be used as a dict key or sorted directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Union

Number = Union[int, float, str, Decimal]


@dataclass(frozen=True, order=True)
class Money:
    """An exact monetary amount in integer minor units (e.g. paise). Immutable."""

    minor: int  # integer minor units; may be negative
    currency: str = "INR"

    # --- construction -----------------------------------------------------
    @classmethod
    def of(cls, major: Number, currency: str = "INR") -> "Money":
        """Build from a major-unit value (rupees), rounding half-up to the minor unit.

        Accepts str/int/Decimal (exact) or float (tolerated but converted via str to limit drift).
        """
        d = major if isinstance(major, Decimal) else Decimal(str(major))
        minor = int((d * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        return cls(minor, currency)

    @classmethod
    def zero(cls, currency: str = "INR") -> "Money":
        return cls(0, currency)

    # --- arithmetic (currency-checked) ------------------------------------
    def _check(self, other: "Money") -> None:
        if self.currency != other.currency:
            raise ValueError(f"currency mismatch: {self.currency} vs {other.currency}")

    def __add__(self, other: "Money") -> "Money":
        self._check(other)
        return Money(self.minor + other.minor, self.currency)

    def __sub__(self, other: "Money") -> "Money":
        self._check(other)
        return Money(self.minor - other.minor, self.currency)

    def __neg__(self) -> "Money":
        return Money(-self.minor, self.currency)

    @property
    def is_zero(self) -> bool:
        return self.minor == 0

    @property
    def is_negative(self) -> bool:
        return self.minor < 0

    # --- presentation -----------------------------------------------------
    @property
    def major(self) -> Decimal:
        """Exact major-unit (rupee) value as a Decimal — for display/serialization only."""
        return (Decimal(self.minor) / 100).quantize(Decimal("0.01"))

    def format(self, symbol: str = "₹", grouping: str = "lakh") -> str:
        """Human string, e.g. '₹1,23,456.78' (Indian lakh grouping) or '₹123,456.78'."""
        neg = self.minor < 0
        whole, frac = divmod(abs(self.minor), 100)
        s = str(whole)
        if grouping == "lakh" and len(s) > 3:
            head, tail = s[:-3], s[-3:]
            parts = []
            while len(head) > 2:
                parts.insert(0, head[-2:]); head = head[:-2]
            if head:
                parts.insert(0, head)
            grouped = ",".join(parts) + "," + tail
        elif len(s) > 3:
            grouped = f"{whole:,}"
        else:
            grouped = s
        return f"{'-' if neg else ''}{symbol}{grouped}.{frac:02d}"

    def __str__(self) -> str:
        return self.format()
