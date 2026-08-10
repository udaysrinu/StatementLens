"""Categorizer strategy + password-rule derivation (synthetic hints only — no real secrets)."""
from datetime import date

from statementlens.adapters.categorize.keyword_categorizer import KeywordCategorizer
from statementlens.adapters.crypto import password_rules as pr
from statementlens.domain.models import Direction, Transaction
from statementlens.domain.money import Money


def _t(desc, merchant="", direction=Direction.DEBIT):
    return Transaction(date(2026, 1, 1), desc, Money.of(100), direction, merchant, raw_date="01-01-26")


def test_categorizer_rules():
    c = KeywordCategorizer()
    assert c.categorize(_t("UPI/DR/x/CRED Club/UTIB/cred.club@/pay", "CRED Club")) == "Card bills"
    assert c.categorize(_t("Zerodha", "Zerodha")) == "Investments"
    assert c.categorize(_t("SWIGGY order", "Swiggy")) == "Food & Dining"
    assert c.categorize(_t("UPI/DR/x/RAMESH/SBIN/y/pay", "RAMESH")) == "Transfers (people)"
    assert c.categorize(_t("Refund", "Amazon", Direction.CREDIT)) in {"Shopping", "Other income"}


def test_password_rule_sbi_text_synthetic():
    rule = "last five digits of registered mobile number and date of birth in DDMMYY format"
    pwds = pr.derive(pr.parse_rule(rule), {"mobile": "9990054321", "dob": "01011990"})
    assert pwds == ["54321010190"]


def test_password_rule_rbl_caps_name_synthetic():
    rule = "first four letters of your name in CAPITALS followed by date of birth in DDMMYY"
    pwds = pr.derive(pr.parse_rule(rule), {"name": "Sample Name", "dob": "01011990"})
    assert pwds == ["SAMP010190"]


def test_candidates_puts_rule_first_and_customs_before_that():
    hints = {"custom": ["explicit"], "mobile": "9990054321", "dob": "01011990",
             "rule_text": "last five digits of mobile and date of birth in DDMMYY"}
    c = pr.candidates(hints)
    assert c[0] == "explicit" and "54321010190" in c[:3]


def test_no_hints_no_candidates():
    assert pr.candidates({}) == []
