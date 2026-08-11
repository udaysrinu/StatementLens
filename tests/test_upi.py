"""Checks for UPI narration decoding and the categorizer improvements it enables.

Narrations use the real bank format with synthetic names/refs. The bank truncates the payee name to
~8 characters, which is the whole reason the VPA handle has to be read.
"""

from statementlens.adapters.categorize import upi
from statementlens.adapters.categorize.keyword_categorizer import KeywordCategorizer
from statementlens.domain.models import Direction, Transaction
from statementlens.domain.money import Money


def txn(desc, merchant="", direction=Direction.DEBIT, amount=100):
    return Transaction(txn_date=None, description=desc, amount=Money.of(amount, "INR"),
                       direction=direction, merchant=merchant)


def test_parses_all_upi_fields():
    p = upi.parse_upi("UPI/DR/651819255369/CRED Club/UTIB/cred.club@/payment")
    assert p.direction == "DR"
    assert p.ref == "651819255369"
    assert p.payee_name == "CRED Club"
    assert p.vpa == "cred.club@"
    assert p.note == "payment"


def test_non_upi_narration_returns_none():
    assert upi.parse_upi("ATM CASH 1234 SOMEWHERE") is None
    assert upi.parse_upi("") is None


def test_short_narrations_do_not_crash():
    # banks sometimes print fewer fields; missing ones must be empty, not an IndexError
    p = upi.parse_upi("UPI/DR/12345")
    assert p is not None and p.payee_name == "" and p.vpa == ""


def test_searchable_includes_the_handle_not_just_the_truncated_name():
    # "Airtel P" is unmatchable; "AirtelPaym" is the signal
    p = upi.parse_upi("UPI/DR/994595552364/Airtel P/INDB/AirtelPaym/Vodafone")
    assert "AirtelPaym" in p.searchable and "Airtel P" in p.searchable


def test_counterparty_prefers_handle_over_truncated_name():
    got = upi.counterparty("UPI/DR/651819255369/CRED Clu/UTIB/cred.club@/payment")
    assert got == "cred.club"


def test_counterparty_unwraps_bank_account_handles():
    # "IBKL-xx802-Sample Name" is an account transfer, not a merchant called IBKL
    assert upi.counterparty("UPI/DR/1/IBKL-xx802-Sample Name/HDFC/x@y/note") == "Sample Name"


def test_counterparty_falls_back_to_merchant_for_non_upi():
    assert upi.counterparty("ATM CASH 1234", merchant="ATM_WDL") == "ATM_WDL"


def test_self_transfer_matches_on_the_truncated_payee_name():
    # the bank cuts the name at ~8 chars, so a prefix comparison is required
    desc = "UPI/DR/261722816074/SAMPLENA/SBIN/9999999999/Payment"
    assert upi.is_self_transfer_narration(desc, ["Samplename Person"]) is True


def test_self_transfer_only_looks_at_the_payee_field():
    # the holder's name in a REMARK must not make a real payment look like a self transfer
    desc = "UPI/DR/1/SOMESHOP/YESB/shop@ybl/paid by Samplename"
    assert upi.is_self_transfer_narration(desc, ["Samplename Person"]) is False


def test_self_transfer_ignores_short_name_tokens():
    # a 3-char token would collide with half of all payees
    desc = "UPI/DR/1/RAJESHKU/SBIN/9999999999/Payment"
    assert upi.is_self_transfer_narration(desc, ["Raj"]) is False


def test_categorizer_uses_the_vpa_handle():
    # name truncated beyond recognition, handle makes it obvious
    t = txn("UPI/DR/651819255369/CRED Clu/UTIB/cred.club@/payment")
    assert KeywordCategorizer().categorize(t) == "Card bills"


def test_self_transfer_gets_its_own_category():
    t = txn("UPI/DR/261722816074/SAMPLENA/SBIN/9999999999/Payment")
    c = KeywordCategorizer(own_names=["Samplename Person"])
    assert c.categorize(t) == "Self transfer"
    # without own_names it must NOT claim to know
    assert KeywordCategorizer().categorize(t) == "Transfers (people)"


def test_aggregator_handle_is_a_merchant_not_a_person():
    t = txn("UPI/DR/1/UNKNOWN/YESB/paytmqr2810/Payment")
    assert KeywordCategorizer().categorize(t) == "Merchants (uncategorized)"


def test_bank_account_handle_is_an_account_transfer():
    t = txn("UPI/DR/1/ICIC-xx859-Some Name/ICIC/9999999999/Transfer")
    assert KeywordCategorizer().categorize(t) == "Account transfer"


def test_p2p_payment_stays_in_the_people_bucket():
    t = txn("UPI/DR/1/SOMEONE/SBIN/someone@ybl/Payment")
    assert KeywordCategorizer().categorize(t) == "Transfers (people)"


def test_new_categories_catch_investments_and_loans():
    cases = {
        "UPI/DR/1/LIQUILOA/YESB/liquiloans@/invest": "Investments",
        "UPI/DR/1/LOANREPA/HDFC/nationalpe@/Loan Rep": "Loans & EMI",
        "UPI/DR/1/TAXPAYME/SBIN/sbitin@sbi/tax": "Taxes",
    }
    c = KeywordCategorizer()
    for desc, expected in cases.items():
        assert c.categorize(txn(desc)) == expected, desc


def test_credits_are_never_labelled_as_spending_categories():
    t = txn("UPI/CR/1/SOMEONE/SBIN/someone@ybl/refund", direction=Direction.CREDIT)
    assert KeywordCategorizer().categorize(t) == "Transfers (in)"
