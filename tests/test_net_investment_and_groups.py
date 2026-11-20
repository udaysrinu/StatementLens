"""Money back from a broker, IMPS field alignment, and netting a family surname as one party.

Each test pins a failure that was live on a real store:
- ₹5.55L of Zerodha payouts were counted as INCOME while "invested" stayed gross;
- IMPS narrations were read with the UPI layout, so remarks ("Loan Rep", "Rent") became payees and one
  person's transfers split across keys;
- relatives sharing a surname each pay from their own UPI handle, so no single net ever appeared.
"""
from datetime import date

from statementlens.adapters.categorize import upi
from statementlens.domain.models import Direction, Transaction
from statementlens.domain.money import Money
from statementlens.usecases import flows
from statementlens.usecases.analytics import build_dataset, net_group


def _t(desc, rupees, direction, merchant="", category="", day=1):
    return Transaction(txn_date=date(2026, 8, day), raw_date="", description=desc, merchant=merchant,
                       amount=Money(round(rupees * 100), "INR"), direction=direction,
                       category=category)


D, C = Direction.DEBIT, Direction.CREDIT


# ---- redemptions --------------------------------------------------------------------------------

def test_broker_payout_is_a_redemption_not_income():
    payout = _t("NEFT*YESB0000001*N1*ZERODHA", 5000, C, merchant="ZERODHA", category="Investments")
    assert flows.classify_flow(payout) == flows.INVESTMENT


def test_invested_is_net_of_payouts_and_money_in_excludes_them():
    rows = [
        _t("NEFT/ZERODHA BROKING", 24_000, D, merchant="ZERODHA", category="Investments"),
        _t("NEFT*YESB*ZERODHA", 5_500, C, merchant="ZERODHA", category="Investments", day=2),
        _t("NEFT/ACME SALARY AUG", 100_000, C, merchant="ACME", category="Salary", day=3),
    ]
    cf = flows.cash_flow(rows)
    assert cf.investments == 18_500_00        # 24,000 in − 5,500 back
    assert cf.redeemed == 5_500_00
    assert cf.incoming == 100_000_00          # the payout is NOT income


def test_dividend_is_income_even_when_categorized_investment():
    # 38 real dividends (TCS, NTPC, Tata Steel...) carry category "investment"; they are returns, not
    # capital coming back, so they must stay in money-in and never shrink "invested"
    div = _t("ACHCr SBIN00882000011904 TCS3RDINTDIV05", 54, C,
             merchant="ACHCr SBIN00882000011904 TCS3RDINTDIV05", category="investment")
    assert flows.classify_flow(div) == flows.INCOMING


def test_ordinary_credit_is_still_income():
    refund = _t("UPI/CR/123456789012/SWIGGY/YESB/swiggy@/refund", 300, C, merchant="SWIGGY")
    assert flows.classify_flow(refund) == flows.INCOMING


# ---- IMPS alignment -----------------------------------------------------------------------------

def test_imps_payee_is_the_name_not_the_remark():
    p = upi.parse_upi("IMPS/333333333333/IBKL-xx802-Sharma/Loan Rep")
    assert p.ref == "333333333333"
    assert upi.payee_name("IMPS/333333333333/IBKL-xx802-Sharma/Loan Rep") == "Sharma"
    # the remark must stay searchable for categorization
    assert p.note == "Loan Rep" and "Loan Rep" in p.searchable


def test_upi_layout_is_untouched():
    p = upi.parse_upi("UPI/DR/656309069917/AMAZON F/YESB/mab04500/Pay")
    assert (p.direction, p.ref, p.payee_name, p.vpa) == ("DR", "656309069917", "AMAZON F", "mab04500")
    # a direction-less UPI line has no payee; it must not gain a date as one
    assert upi.parse_upi("UPI/303631055413/05022023").payee_name == ""


# ---- net a surname as one party -----------------------------------------------------------------

_FAMILY = [
    _t("UPI/DR/111111111111/SHARMA/ANDB/9000000001/Payme", 10_000, D, merchant="SHARMA"),
    _t("UPI/CR/222222222222/SHARMA/SBIN/rakesh./UPI", 4_000, C, merchant="SHARMA", day=2),
    _t("IMPS/333333333333/IBKL-xx802-Sharma/Loan Rep", 2_000, D,
       merchant="IBKL-xx802-Sharma", day=3),
    _t("UPI/DR/111111111111/SHISHIR/SBIN/shishir@/x", 500, D, merchant="SHISHIR", day=4),
]


def test_every_spelling_and_handle_groups_under_the_surname():
    keys = {net_group(t, ["SHARMA"]) for t in _FAMILY[:3]}
    assert keys == {("sharma", "Sharma (all)")}
    assert net_group(_FAMILY[3], ["SHARMA"]) is None


def test_name_in_a_remark_does_not_group_a_stranger():
    # the holder's surname in the REMARK of someone else's payment must not pull it into the group
    t = _t("UPI/DR/222222222222/SHISHIR/SBIN/shishir@/for sharma", 700, D, merchant="SHISHIR")
    assert net_group(t, ["SHARMA"]) is None


def test_dataset_rows_carry_one_counterparty_for_the_group():
    ds = build_dataset(_FAMILY, net_with=["SHARMA"])
    fam = [r for r in ds["txns"] if r.get("cp") == "sharma"]
    assert len(fam) == 3 and all(r["cpn"] == "Sharma (all)" for r in fam)
    paid = sum(r["a"] for r in fam if r["dir"] == "D")
    got = sum(r["a"] for r in fam if r["dir"] == "C")
    assert (paid - got) == 8_000_00           # 10,000 + 2,000 out − 4,000 back


def test_without_the_preference_relatives_stay_apart():
    ds = build_dataset(_FAMILY)
    assert not any(r.get("cpn") for r in ds["txns"])


# ---- CRED is a rail, a shop and a FASTag channel -----------------------------------------------

def test_cred_bill_payment_is_still_a_self_transfer():
    t = _t("UPI/DR/232173317707/CredClub/ICIC/credclub@i/Payme", 20_000, D, merchant="CredClub")
    assert flows.classify_flow(t) == flows.SELF_TRANSFER


def test_a_purchase_at_creds_store_is_spending():
    t = _t("11578869125 CRED ECOM GURGAON IN 1", 699, D, merchant="CRED ECOM GURGAON")
    assert flows.classify_flow(t) == flows.SPEND


def test_a_fastag_topup_through_cred_is_spending():
    t = _t("UPI/DR/660210080327/Dreamplu/UTIB/cred.fasta/payme", 502, D, merchant="Dreamplu")
    assert flows.classify_flow(t) == flows.SPEND


# ---- INDmoney: a card-bill rail AND a US-stocks broker -------------------------------------------

def test_indmoney_card_bill_payment_is_a_self_transfer():
    t = _t("UPI/DR/526439386967/FINZOOM /UTIB/indmoney3./UPIIn", 75_001, D, merchant="FINZOOM")
    assert flows.classify_flow(t) == flows.SELF_TRANSFER


def test_indmoney_us_stock_funding_is_an_investment():
    t = _t("UPI/DR/660911223344/INDMoney/YESB/finzoomers/Pay20", 100_000, D, merchant="INDMoney",
           category="Investments")
    assert flows.classify_flow(t) == flows.INVESTMENT


def test_money_back_from_indmoney_is_a_redemption():
    t = _t("UPI/CR/660911223399/INDMoney/YESB/finzoomers/Withdr", 20_000, C, merchant="INDMoney")
    assert flows.classify_flow(t) == flows.INVESTMENT
