"""Checks for bank transaction-alert parsing.

Bodies are the REAL wording from HDFC InstaAlerts / SBI CBS / ICICI cards emails, with account
numbers and merchant names replaced by synthetic values.
"""

from datetime import date

from statementlens.adapters.parsers.alert_parser import parse_alert
from statementlens.domain.models import Direction

HDFC = ("Dear Customer, Greetings from HDFC Bank. We would like to inform you that "
        "Rs. 465.00 has been debited from your HDFC Bank Credit Card ending 1234 towards "
        "SAMPLE MERCHANT FOOD2 on 09 Aug, 2026 at 13:22:07 . To check your available balance…")

SBI = ("Greetings from SBI ! Your AC XXXXX000000 Debited INR 59.00 on 07/07/26 -ACH CHARGES. "
       "Avl Bal INR 1,00,000.00.-SBI Please do not reply to this auto generated email.")

SBI_CREDIT = ("Greetings from SBI ! Your AC XXXXX000000 Credited INR 1,50,000.00 on 30/06/26 "
              "-SALARY JUN. Avl Bal INR 3,10,000.00.-SBI")

# --- things that must NOT be booked as transactions ---
REWARDS = ("E-statement: You have 40 Points worth Rs.10 as on 30 Jun. SBI awards 2 Reward Points "
           "per Rs.200 spent on SBI Debit Card at POS and these points will be credited monthly.")

STANDING_INSTRUCTION = ("Dear Customer, Your payment of INR 5000.00 towards Sample Insurer through "
                        "Standing Instruction ABC123 is due on 15/03/2026 and will be debited from "
                        "your ICICI Bank Credit Card 0000.")

OTP = "Dear Customer, 987654 is the OTP for your transaction of Rs. 2,500.00. Do not share it."

DECLINED = ("We would like to inform you that Rs. 999.00 has been debited from your HDFC Bank "
            "Credit Card ending 1234 towards SOME MERCHANT on 09 Aug, 2026 but the transaction "
            "was declined.")


def test_hdfc_credit_card_alert():
    a = parse_alert(HDFC, subject="A payment was made using your Credit Card")
    assert a is not None
    assert a.amount_minor == 46500                 # integer paise, no float
    assert a.direction is Direction.DEBIT
    assert a.txn_date == date(2026, 8, 9)
    assert a.merchant == "SAMPLE MERCHANT FOOD2"
    assert a.account_hint == "1234"
    assert a.provisional is True                   # statements are authoritative, alerts are not


def test_sbi_debit_alert_with_trailing_balance():
    a = parse_alert(SBI, subject="CBSSBI ALERT")
    assert a.amount_minor == 5900
    assert a.direction is Direction.DEBIT
    assert a.txn_date == date(2026, 7, 7)
    # the running balance must not leak into the merchant name
    assert a.merchant == "ACH CHARGES"


def test_sbi_credit_alert_direction():
    a = parse_alert(SBI_CREDIT)
    assert a.direction is Direction.CREDIT
    assert a.amount_minor == 15000000              # 1,50,000.00 lakh grouping parsed
    assert a.txn_date == date(2026, 6, 30)


def test_reward_points_email_is_not_a_transaction():
    # contains "Rs.10", "spent" and "credited" — a naive amount regex would book it
    assert parse_alert(REWARDS, subject="E-statement: You have 40 Points worth Rs.10") is None


def test_future_standing_instruction_is_not_a_transaction():
    # "will be debited ... is due on" — hasn't happened yet
    assert parse_alert(STANDING_INSTRUCTION,
                       subject="Upcoming payment notification: Standing Instructions") is None


def test_otp_email_is_not_a_transaction():
    assert parse_alert(OTP) is None


def test_declined_transaction_is_not_booked():
    assert parse_alert(DECLINED) is None


def test_html_markup_is_stripped_before_matching():
    html = ("<html><body><p>We would like to inform you that <b>Rs. 100.50</b> has been debited "
            "from your HDFC Bank Credit Card ending 9999 towards <span>TEST SHOP</span> "
            "on 01 Jan, 2026 at 10:00:00</p></body></html>")
    a = parse_alert(html)
    assert a.amount_minor == 10050 and a.merchant == "TEST SHOP"


def test_amounts_with_lakh_grouping_and_no_decimals():
    body = ("We would like to inform you that Rs. 1,25,000 has been debited from your HDFC Bank "
            "Credit Card ending 1111 towards BIG PURCHASE on 15 Mar, 2026 at 09:00:00")
    assert parse_alert(body).amount_minor == 12500000


HDFC_AT = ("Bank Credit Card ending in 1234 .You made a transaction of Rs. 1508.00 at "
           "SAMPLE SHOP on 11-07-2026 20:36:23 . Authorization code: 053966 Important Note: "
           "If you did not do this transaction, please act immediately")

SBI_FOR = ("Greetings from SBI ! Your A/C XXXXX000000 has credit for C0000000000000000000000 "
           "of Rs 460.00 on 13/07/26. Avl Bal Rs 1,00,000.00.-SBI")

SBI_BY = ("Greetings from SBI ! Dear Customer, Your A/C XXXXX000000 has a debit by NACH of "
          "Rs 10,000.00 on 10/07/26. Avl Bal Rs 1,00,000.00.")

YONO = ("Dear SAMPLE USER Thank you for using YONO SBI for Fund Transfer The transaction details "
        "are as follows: Description Details Transaction Status Successful Amount Rs.97,000.00 "
        "Transaction Number 000000000000 Date of Transaction 03.08.26 Debit account x0000 "
        "Beneficiary Name Sample Payee Beneficiary Account Number x0000 Reach Us at: "
        "For OTP related queries call our helpline. Terms apply.")


def test_hdfc_you_made_a_transaction_wording():
    # a second HDFC format used interchangeably with the "towards" one; has no direction word
    a = parse_alert(HDFC_AT, subject="We noticed a transaction on your Credit Card")
    assert a is not None and a.direction is Direction.DEBIT
    assert a.amount_minor == 150800
    assert a.txn_date == date(2026, 7, 11)
    assert a.merchant == "SAMPLE SHOP"


def test_declined_wording_still_rejected_in_that_format():
    # the qualifier must sit in the SAME sentence as the amount, which is how real alerts word it
    declined = HDFC_AT.replace("on 11-07-2026 20:36:23 .",
                               "on 11-07-2026 20:36:23 was declined.")
    assert parse_alert(declined) is None


def test_sbi_reference_number_credit_form():
    a = parse_alert(SBI_FOR, subject="CBSSBI ALERT")
    assert a.direction is Direction.CREDIT and a.amount_minor == 46000
    assert a.txn_date == date(2026, 7, 13)


def test_sbi_debit_by_channel_form():
    a = parse_alert(SBI_BY, subject="CBSSBI ALERT")
    assert a.direction is Direction.DEBIT and a.amount_minor == 1000000
    assert a.merchant == "NACH"


def test_yono_fund_transfer_table_layout():
    a = parse_alert(YONO, subject="Transaction success")
    assert a is not None, "a real fund transfer must not be dropped"
    assert a.amount_minor == 9700000
    assert a.direction is Direction.DEBIT
    assert a.txn_date == date(2026, 8, 3)
    assert a.merchant == "Sample Payee"


def test_footer_boilerplate_cannot_veto_a_real_transaction():
    # regression: the word "OTP" in a footer link rejected a genuine transfer, because exclusions
    # were matched against the whole flattened page instead of the text around the amount
    assert parse_alert(YONO, subject="Transaction success") is not None


def test_failed_transfer_receipt_is_not_booked():
    assert parse_alert(YONO.replace("Successful", "Unsuccessful"),
                       subject="Transaction failed") is None


def test_banks_with_no_dedicated_pattern_still_parse():
    """The bank-agnostic fallback is what stops this being an SBI/HDFC-only tool.

    None of these banks has a pattern written for it; each must still yield the right amount,
    direction and date.
    """
    cases = [
        ("INR 1250.75 debited from A/c no. XX9012 on 14-08-26 towards BIG BAZAAR.",
         Direction.DEBIT, 125075, date(2026, 8, 14)),
        ("Rs 899.00 has been debited from your Kotak Bank Account XX3344 on 02 Sep, 2026 "
         "towards SAMPLE SUBSCRIPTION.", Direction.DEBIT, 89900, date(2026, 9, 2)),
        ("Thank you. Amount Rs.5,600.00 credited to your account 7788 on 22.07.26 "
         "from SALARY CREDIT.", Direction.CREDIT, 560000, date(2026, 7, 22)),
    ]
    for body, direction, minor, when in cases:
        a = parse_alert(body)
        assert a is not None, f"failed to parse: {body[:40]}"
        assert a.direction is direction and a.amount_minor == minor and a.txn_date == when


def test_non_rupee_currencies_parse():
    # nothing about the money extraction is India-specific
    usd = parse_alert("Your card ending 4321 was credited USD 45.20 on 09/12/2026 from A REFUND.")
    gbp = parse_alert("Dear Customer, GBP 12.50 debited on 03/04/2026 at A SHOP. Thanks.")
    assert usd.amount_minor == 4520 and usd.direction is Direction.CREDIT
    assert gbp.amount_minor == 1250 and gbp.direction is Direction.DEBIT


def test_bank_specific_patterns_win_over_the_fallback():
    # the named patterns extract merchant/account more reliably, so they must be tried first
    assert parse_alert(HDFC).source == "hdfc"
    assert parse_alert(SBI).source == "sbi"


def test_unparseable_text_returns_none_not_a_guess():
    assert parse_alert("Hello, your account is doing fine.") is None
    assert parse_alert("") is None
    assert parse_alert(None) is None


def test_impossible_date_does_not_crash():
    body = ("We would like to inform you that Rs. 10.00 has been debited from your HDFC Bank "
            "Credit Card ending 1111 towards X on 31 Feb, 2026 at 09:00:00")
    a = parse_alert(body)
    assert a is not None and a.txn_date is None     # amount kept, bogus date dropped
