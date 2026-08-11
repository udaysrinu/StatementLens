"""KeywordCategorizer — rule-based transaction categorization (Categorizer port, Strategy pattern).

Ordered keyword rules over "<description> <merchant>"; first match wins, so specific/high-signal
rules precede generic ones. Swap this whole strategy for an ML categorizer later without touching
callers. India-centric defaults (UPI/CRED/Zerodha/rent/utilities/…); rules are overridable.
"""

from __future__ import annotations

import re
from typing import List, Tuple

from ...domain.models import Direction, Transaction
from . import upi

DEFAULT_RULES: List[Tuple[str, str]] = [
    # Card-statement rows first: a cashback line mentioning "Swiggy" is money IN, not a Swiggy order,
    # and a bill payment is an internal transfer rather than a purchase. Both must win over the
    # merchant rules below, which would otherwise match on the brand name inside them.
    ("Card payment",   r"(?i)pymt\s+rec|payment\s+received|thank\s*you|bppy\s+cc\s+payment|"
                       r"tele\s+transfer\s+credit|online\s+trf\s*-\s*pymt"),
    ("Cashback & rewards", r"(?i)cash\s?back|cashback|reward\s?point|statement\s+credit|milestone\s+benefit"),
    ("Card bills",     r"(?i)cred\s?club|cred\.club|cred\s?ccbp|credit card|cc\s?payment|billdesk.*card|\bslice\b|onecard|jupiter|uni\s?card"),
    ("Investments",    r"(?i)zerodha|groww|kite|upstox|indiancl|bsestarmf|nse|bse|mutual fund|smallcase|coin\b|indmoney|paytm money|nsccl|iccl|sip\b|elss|\bnps\b|npscams|liquiloans|lendbox|ndxp2p|faircent|12%\s?club|wintwealth|jiraaf"),
    ("Loans & EMI",    r"(?i)loan\s?rep|\bemi\b|loan\s?emi|repayment|hdb\s?fin|bajaj\s?fin|nationalpe|home\s?loan|personal\s?loan"),
    ("Taxes",          r"(?i)sbitin@|income\s?tax|itns|gst\s?pay|tin2\.|cbdt|advance\s?tax|tds\b"),
    ("Rent",           r"(?i)\brent\b"),
    ("Salary/Income",  r"(?i)\bsalary\b|sal-a|pfs salary|payroll|stipend"),
    ("Interest",       r"(?i)interest credit|int\.pd|cr int|savings interest"),
    ("Dividends",      r"(?i)dividend|fnldiv|achcr.*div"),
    # Insurance before Bills: "LIFE INSURANCE CORPORAT" would otherwise fall through to untagged.
    ("Insurance",      r"(?i)insuranc|policybazaar|policy\s?bazaar|\blic\b|life\s+insurance|"
                       r"hdfc\s?life|icici\s?pru|max\s?life|star\s?health|niva\s?bupa|acko|digit\b|"
                       r"tata\s?aig|bajaj\s?allianz|sbi\s?life|term\s?plan|premium\b"),
    ("Fuel",           r"(?i)\bfuel\b|petrol|diesel|hpcl|iocl|bharat petro|indian oil|hp pay|shell"),
    ("Bills & Utilities", r"(?i)electric|airtel|jio|vodafone|\bvi\b|bescom|mygate|gas|cylinder|broadband|wifi|water bill|dth|recharge|postpaid|bbps"),
    ("Groceries",      r"(?i)fresh|grocer|\bveg\b|vegetable|blinkit|zepto|bigbasket|dmart|d-mart|instamart|jiomart|super\s?market|kirana|milk|dairy|amazon\s?f|licious|country\s?deli"),
    ("Food & Dining",  r"(?i)swiggy|bundl\s?tech|zomato|eternal\s?ltd|restaurant|cafe|hotel|biryani|biriyani|kfc|mcd|dominos|pizza|bakery|barbeque|\bfood\b|dhaba|shawarma|dosa|eatclub|smartq|chai|tea\b|juice|sweets|hotel"),
    ("Shopping",       r"(?i)amazon|flipkart|myntra|ajio|meesho|nykaa|reliance|lifestyle|decathlon|ikea|"
                       r"croma|\bstore\b|retail|hennes|maurit|aditya\s?birla|zudio|westside|trends|"
                       r"snitch|bewakoof|apparel|garment|fashion|clothing|footwear|jewel|tanishq|"
                       r"lenskart|titan\b|puma|adidas|nike|levi|uniqlo|shoppers\s?stop"),
    ("Health",         r"(?i)pharma|apollo|medplus|hospital|clinic|diagnostic|medical|1mg|pharmeasy|"
                       r"netmeds|health|aesthet|dental|\bdr\.?\s|lab\b|pathology|wellness|optical|"
                       r"physio|ayurved|nephro|cardio"),
    ("Travel",         r"(?i)irctc|uber|ola|rapido|redbus|make\s?my\s?trip|makemytrip|goibibo|flight|"
                       r"indigo|airlines|\btravel\b|metro|toll|fastag|airbnb|agoda|booking\.com|"
                       r"oyo\b|cleartrip|easemytrip|yatra|ixigo|goa\s?miles|vistara|air\s?india|"
                       r"spicejet|akasa|hotel|resort|\bstay\b|zoomcar|blusmart"),
    ("Entertainment",  r"(?i)bookmyshow|netflix|spotify|prime video|hotstar|pvr|inox|movie|\bgame\b|\bbar\b|\bpub\b|liquor|wine"),
    ("Cash/ATM",       r"(?i)\batm\b|cash wdl|cash withdrawal|by cash"),
    ("Fees & Charges", r"(?i)\bcharge|\bfee\b|gst|penalty|min bal|amc|annual fee|sms alert|igst|"
                       r"finance\s+charges?|late\s+payment|surcharge|interest\s+levied"),
    # A wallet/aggregator line hides the real merchant; naming the intermediary beats "untagged".
    ("Wallets & gateways", r"(?i)ppsl\*|paytm|phonepe|one\s?97|razorpay|\braz\*|payu|billdesk|"
                       r"mobikwik|freecharge|amazon\s?pay|\bcas\*|\brsp\*|\btps\*"),
]
_TRANSFER = re.compile(r"(?i)IMPS|NEFT|RTGS|^UPI/")

#: A UPI handle belonging to a payment aggregator means the counterparty is a BUSINESS even when the
#: truncated name is unrecognisable — "paytm.s1c3", "razorpay", "mab0450001".
_MERCHANT_HANDLE = re.compile(
    r"(?i)razorpay|\brzp\b|payu|paytm\.|paytmqr|billdesk|ccavenue|cashfree|phonepe\.|\bpg\b|"
    r"mab\d{5,}|instamojo|easebuzz|juspay|pinelabs|bharatpe|okbizaxis|\.ifsc|\bmerchant\b|"
    r"\bqr\d{3,}|zomato|swiggy|\bstore@|shop@|retail")


class KeywordCategorizer:
    """Rule-based categorizer that reads decoded UPI fields, not just the raw narration.

    `own_names` enables a distinct "Self transfer" category. Without it, money the user moves between
    their own accounts lands in the person-to-person bucket and inflates apparent spending — on a real
    45-statement set that was ₹11.7L of the largest category.
    """

    def __init__(self, rules: List[Tuple[str, str]] | None = None,
                 own_names: List[str] | None = None):
        self._rules = [(cat, re.compile(pat)) for cat, pat in (rules or DEFAULT_RULES)]
        self._own = list(own_names or [])

    def categorize(self, txn: Transaction) -> str:
        parts = upi.parse_upi(txn.description)
        # The bank truncates the payee name to ~8 chars, so include the VPA handle and note —
        # "cred.club@" is matchable where "CRED Clu" is not.
        blob = f"{txn.description} {txn.merchant}"
        if parts:
            blob = f"{blob} {parts.searchable}"

        if self._own and upi.is_self_transfer_narration(txn.description, self._own):
            return "Self transfer"

        for cat, pat in self._rules:
            if pat.search(blob):
                return cat

        if _TRANSFER.search(txn.description):
            if txn.direction is Direction.CREDIT:
                return "Transfers (in)"
            # split the old catch-all: an aggregator handle or a bank-account handle is not a person
            if parts and (_MERCHANT_HANDLE.search(parts.vpa) or _MERCHANT_HANDLE.search(parts.note)):
                return "Merchants (uncategorized)"
            if parts and parts.is_bank_transfer:
                return "Account transfer"
            return "Transfers (people)"
        return "Other income" if txn.direction is Direction.CREDIT else "Other"
