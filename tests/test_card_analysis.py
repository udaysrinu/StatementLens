"""Checks that every analysis path is correct for CREDIT CARDS, not just bank accounts.

Cards break assumptions a savings account never does, and each of these was a real bug found by
auditing card-only data:

* A **card bill payment** appears as a credit on the card and a debit on the bank. Counted naively it
  is income on one statement and spending on the other — the same money booked twice, in opposite
  directions. It is an internal transfer.
* **Cashback** mentioning a merchant ("10% Swiggy CashBack") was filed under Food & Dining. It is
  money IN; putting it in a spend category both overstates food spend and hides the reward.
* Cards have **no running balance** and their rows include finance charges, IGST on those charges and
  split principal/interest EMI lines.
"""

from datetime import date

from statementlens.adapters.categorize.keyword_categorizer import KeywordCategorizer
from statementlens.domain.models import Direction, Transaction
from statementlens.domain.money import Money
from statementlens.usecases import flows
from statementlens.usecases.analytics import build_dataset
from statementlens.usecases.tagging import SELF_TRANSFER_TAG, normalize_tag


def card(desc, rupees, *, credit=False, day=11, month=7, merchant=""):
    return Transaction(txn_date=date(2026, month, day), description=desc,
                       amount=Money.of(rupees, "INR"),
                       direction=Direction.CREDIT if credit else Direction.DEBIT,
                       merchant=merchant or desc[:24], balance=None,     # cards carry no balance
                       raw_date=f"{day:02d}-0{month}-26",
                       source_ref=f"c-{month}-{day}-{rupees}")


# --- card bill payments ------------------------------------------------------

BILL_PAYMENT_WORDINGS = [
    "ONLINE TRF - PYMT RECD - THANK YOU",
    "BPPY CC PAYMENT DP0162030 (Ref# ST2620400)",
    "TELE TRANSFER CREDIT (Ref# ST2617700)",
    "PAYMENT RECEIVED - THANK YOU",
]


def test_card_bill_payments_are_internal_transfers_not_income():
    for wording in BILL_PAYMENT_WORDINGS:
        t = card(wording, 34175, credit=True)
        assert flows.is_card_bill_payment(t), wording
        assert flows.classify_flow(t) == flows.SELF_TRANSFER, wording


def test_card_bill_payment_is_excluded_from_both_sides_of_cash_flow():
    txns = [
        card("ONLINE TRF - PYMT RECD - THANK YOU", 50000, credit=True),
        card("SOME SHOP BENGALURU", 1500),
    ]
    f = flows.cash_flow(txns)
    assert f.incoming == 0, "a bill payment is not income"
    assert f.spends == 150000, "only the real purchase counts as spend"
    assert f.self_transfers == 5000000 and f.self_transfer_count == 1


def test_card_payment_tag_maps_to_self_transfer():
    assert normalize_tag("Card payment") == SELF_TRANSFER_TAG


def test_the_bank_side_of_the_same_payment_also_nets_out():
    """The debit leg on the bank statement must land in the same bucket as the credit leg."""
    bank_leg = card("CREDIT CARD PAYMENT to HDFC card", 50000)      # a debit
    assert flows.classify_flow(bank_leg) == flows.SELF_TRANSFER


# --- cashback ----------------------------------------------------------------

def test_cashback_is_not_filed_as_a_spend_category():
    t = card("10% Swiggy CashBack", 934, credit=True)
    assert KeywordCategorizer().categorize(t) == "Cashback & rewards"
    assert normalize_tag("Cashback & rewards") != "food and drinks"


def test_cashback_is_reported_separately_from_refunds():
    txns = [
        card("10% Sample CashBack", 934, credit=True),
        card("SAMPLE SHOP refund", 2150, credit=True),
    ]
    sources = {r["source"]: r["amount"] for r in flows.incoming_breakdown(txns)}
    assert sources.get("Cashback & rewards") == 93400
    assert sources.get("Refunds") == 215000


def test_cashback_does_not_inflate_food_spend():
    txns = [card("SWIGGY FOODBANGALORE", 326), card("10% Swiggy CashBack", 32, credit=True)]
    cat = KeywordCategorizer()
    tagged = [t.with_category(cat.categorize(t)) for t in txns]
    ds = build_dataset(tagged, account="CARD")
    food = next((r for r in ds["tags"] if r["tag"] == "food and drinks"), None)
    assert food is not None and food["amount"] == 32600      # the cashback is not added in


# --- card-specific row types -------------------------------------------------

def test_finance_charges_and_igst_are_fees():
    cat = KeywordCategorizer()
    for desc in ("FINANCE CHARGES (Ref# 1999)", "IGST-VPS2718-RATE 18.0 -36 (Ref# 0999)"):
        assert cat.categorize(card(desc, 1464)) == "Fees & Charges", desc


def test_emi_principal_and_interest_are_both_loans():
    cat = KeywordCategorizer()
    for desc in ("OFFUS EMI,PRIN NB:02,000001404", "OFFUS EMI,INT NBR:02,000001404"):
        assert cat.categorize(card(desc, 1841)) == "Loans & EMI", desc


def test_card_merchants_that_used_to_fall_through_now_categorize():
    """Card statements carry real merchant names, so keyword rules pay off — these were untagged."""
    cases = {
        "LIFE INSURANCE CORPORATNOIDA": "Insurance",
        "POLICYBAZAAR GURGAON": "Insurance",
        "Airbnb Payments India Gurgoan": "Travel",
        "Make My Trip Gurgaon": "Travel",
        "SNITCH VISAKHAPATNA": "Shopping",
        "Apollo Pharmacies Limi Chennai": "Health",
        "BUNDL TECHNOLOGIES BENGALURU": "Food & Dining",     # Swiggy's legal entity name
    }
    cat = KeywordCategorizer()
    for desc, expected in cases.items():
        assert cat.categorize(card(desc, 500)) == expected, desc


def test_missing_balance_does_not_break_the_dataset():
    """Every card row has balance=None; analytics must not assume a running balance exists."""
    cat = KeywordCategorizer()
    txns = [t.with_category(cat.categorize(t))
            for t in (card("SHOP A", 500, day=1), card("SHOP B", 700, day=2))]
    ds = build_dataset(txns, account="CARD")
    assert ds["meta"]["txn_count"] == 2
    assert all(r["b"] is None for r in ds["txns"])


def test_full_card_dataset_has_no_impossible_income():
    """End-to-end guard: on a card, bill payments must not appear as salary or as people transfers."""
    cat = KeywordCategorizer()
    raw = [
        card("ONLINE TRF - PYMT RECD - THANK YOU", 75200, credit=True, day=21, month=9),
        card("BPPY CC PAYMENT DP0162", 34175, credit=True, day=22),
        card("SWIGGY FOODBANGALORE", 326, day=26),
        card("10% Swiggy CashBack", 143, credit=True, day=26),
        card("LIFE INSURANCE CORPORATNOIDA", 38453, day=7),
        card("FINANCE CHARGES (Ref# 1999)", 1464, day=1),
    ]
    ds = build_dataset([t.with_category(cat.categorize(t)) for t in raw], account="CARD")
    tags = {r["tag"] for r in ds["tags"]}
    assert "people" not in tags, "a credit card cannot make person-to-person transfers"
    sources = {r["source"] for r in ds["incoming_sources"]}
    assert "Salary" not in sources, "salary is never credited to a credit card"
    # spend excludes both bill payments; it is the three real charges
    assert ds["flow"]["spends"] == 32600 + 3845300 + 146400


# --- card vs bank framing ----------------------------------------------------

def test_card_is_detected_structurally_not_by_label():
    """No running balance + a bill-payment row means card, whatever the user named the account."""
    card_rows = [card("SOME SHOP", 500), card("ONLINE TRF - PYMT RECD - THANK YOU", 5000, credit=True)]
    assert flows.looks_like_card(card_rows) is True


def test_a_bank_account_is_not_mistaken_for_a_card():
    with_balance = Transaction(txn_date=date(2026, 7, 1), description="UPI/DR/1/SHOP/YESB/x@y/pay",
                               amount=Money.of(500, "INR"), direction=Direction.DEBIT,
                               merchant="SHOP", balance=Money.of(10000, "INR"))
    assert flows.looks_like_card([with_balance]) is False
    assert flows.looks_like_card([]) is False


def test_card_flow_reports_charges_payments_refunds_and_fees_separately():
    rows = [
        card("SOME SHOP BENGALURU", 1000),
        card("FINANCE CHARGES (Ref# 199)", 150),
        card("IGST-VPS271-RATE 18.0", 27),
        card("ONLINE TRF - PYMT RECD - THANK YOU", 800, credit=True),
        card("SOME SHOP refund", 100, credit=True),
        card("10% Sample CashBack", 50, credit=True),
    ]
    f = flows.card_flow(rows)
    assert f.charges == 100000
    assert f.fees == 15000 + 2700
    assert f.payments == 80000
    assert f.refunds == 10000
    assert f.rewards == 5000


def test_card_flow_reconciles_to_the_raw_total():
    """Every rupee must land in exactly one bucket — no double counting, nothing dropped."""
    rows = [
        card("SHOP A", 1000), card("FINANCE CHARGES", 150),
        card("PYMT RECD - THANK YOU", 800, credit=True),
        card("refund from SHOP A", 100, credit=True),
        card("5% CashBack", 50, credit=True),
    ]
    f = flows.card_flow(rows)
    assert (f.charges + f.fees + f.payments + f.refunds + f.rewards
            == sum(r.amount.minor for r in rows))


def test_net_new_debt_is_negative_when_you_overpay():
    rows = [card("SHOP", 1000), card("PYMT RECD - THANK YOU", 1500, credit=True)]
    assert flows.card_flow(rows).net_new_debt == 100000 - 150000


def test_dataset_exposes_the_card_frame_only_for_cards():
    cat = KeywordCategorizer()
    card_rows = [card("SHOP", 500), card("PYMT RECD - THANK YOU", 400, credit=True)]
    ds = build_dataset([t.with_category(cat.categorize(t)) for t in card_rows], account="CARD")
    assert ds["meta"]["is_card"] is True and ds["card"] is not None

    bank_row = Transaction(txn_date=date(2026, 7, 1), description="UPI/DR/1/SHOP/YESB/x@y/pay",
                           amount=Money.of(500, "INR"), direction=Direction.DEBIT,
                           merchant="SHOP", balance=Money.of(9500, "INR"), category="shopping")
    ds2 = build_dataset([bank_row], account="SBI")
    assert ds2["meta"]["is_card"] is False and ds2["card"] is None
