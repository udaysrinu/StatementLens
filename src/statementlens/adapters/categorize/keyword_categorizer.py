"""KeywordCategorizer — rule-based transaction categorization (Categorizer port, Strategy pattern).

Ordered keyword rules over "<description> <merchant>"; first match wins, so specific/high-signal
rules precede generic ones. Swap this whole strategy for an ML categorizer later without touching
callers. India-centric defaults (UPI/CRED/Zerodha/rent/utilities/…); rules are overridable.
"""

from __future__ import annotations

import re
from typing import List, Tuple

from ...domain.models import Direction, Transaction

DEFAULT_RULES: List[Tuple[str, str]] = [
    ("Card bills",     r"(?i)cred\s?club|cred\.club|credit card|cc\s?payment|billdesk.*card"),
    ("Investments",    r"(?i)zerodha|groww|kite|upstox|indiancl|bsestarmf|nse|bse|mutual fund|smallcase|coin\b|indmoney|paytm money"),
    ("Rent",           r"(?i)\brent\b"),
    ("Salary/Income",  r"(?i)\bsalary\b|sal-a|pfs salary|payroll|stipend"),
    ("Interest",       r"(?i)interest credit|int\.pd|cr int|savings interest"),
    ("Dividends",      r"(?i)dividend|fnldiv|achcr.*div"),
    ("Fuel",           r"(?i)\bfuel\b|petrol|diesel|hpcl|iocl|bharat petro|indian oil|hp pay|shell"),
    ("Bills & Utilities", r"(?i)electric|airtel|jio|vodafone|\bvi\b|bescom|mygate|gas|cylinder|broadband|wifi|water bill|dth|recharge|postpaid|bbps"),
    ("Groceries",      r"(?i)fresh|grocer|\bveg\b|vegetable|blinkit|zepto|bigbasket|dmart|d-mart|instamart|jiomart|super\s?market|kirana|milk|dairy"),
    ("Food & Dining",  r"(?i)swiggy|zomato|restaurant|cafe|hotel|biryani|biriyani|kfc|mcd|dominos|pizza|bakery|barbeque|\bfood\b|dhaba|shawarma|dosa|eatclub|smartq"),
    ("Shopping",       r"(?i)amazon|flipkart|myntra|ajio|meesho|nykaa|reliance|lifestyle|decathlon|ikea|croma|\bstore\b|retail"),
    ("Health",         r"(?i)pharma|apollo|medplus|hospital|clinic|diagnostic|medical|1mg|pharmeasy|netmeds|health|aesthet"),
    ("Travel",         r"(?i)irctc|uber|ola|rapido|redbus|makemytrip|goibibo|flight|indigo|airlines|\btravel\b|metro|toll|fastag"),
    ("Entertainment",  r"(?i)bookmyshow|netflix|spotify|prime video|hotstar|pvr|inox|movie|\bgame\b|\bbar\b|\bpub\b|liquor|wine"),
    ("Cash/ATM",       r"(?i)\batm\b|cash wdl|cash withdrawal|by cash"),
    ("Fees & Charges", r"(?i)\bcharge|\bfee\b|gst|penalty|min bal|amc|annual fee|sms alert"),
]
_TRANSFER = re.compile(r"(?i)IMPS|NEFT|RTGS|^UPI/")


class KeywordCategorizer:
    def __init__(self, rules: List[Tuple[str, str]] | None = None):
        self._rules = [(cat, re.compile(pat)) for cat, pat in (rules or DEFAULT_RULES)]

    def categorize(self, txn: Transaction) -> str:
        blob = f"{txn.description} {txn.merchant}"
        for cat, pat in self._rules:
            if pat.search(blob):
                return cat
        if _TRANSFER.search(txn.description):
            return "Transfers (in)" if txn.direction is Direction.CREDIT else "Transfers (people)"
        return "Other income" if txn.direction is Direction.CREDIT else "Other"
