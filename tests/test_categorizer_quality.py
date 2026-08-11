"""A quality FLOOR for the categorizer, measured on a synthetic-but-realistic transaction mix.

Rule sets rot: someone adds a keyword, an earlier rule starts shadowing a later one, and the
catch-all quietly grows again. Asserting on distribution — not just on individual rows — is what
catches that. The real 45-statement corpus is private, so this mirrors its SHAPE (mostly UPI, a few
big investments, a long tail of small merchant payments) with invented names.

Thresholds are set with headroom: they exist to catch regressions, not to freeze today's numbers.
"""

from collections import Counter

from statementlens.adapters.categorize.keyword_categorizer import KeywordCategorizer
from statementlens.domain.models import Direction, Transaction
from statementlens.domain.money import Money

OWN = ["Samplename Person"]


def _t(desc, rupees, direction=Direction.DEBIT, merchant=""):
    return Transaction(txn_date=None, description=desc, amount=Money.of(rupees, "INR"),
                       direction=direction, merchant=merchant)


def _corpus():
    """~100 transactions shaped like a real Indian bank statement."""
    rows = []
    # recognisable merchants over UPI, name truncated by the bank
    for i in range(20):
        rows.append(_t(f"UPI/DR/{i:012d}/Swiggy I/YESB/swiggy@ybl/Payment", 400))
    for i in range(12):
        rows.append(_t(f"UPI/DR/{i:012d}/Fresh N /YESB/mab0450001/Payment", 250))
    for i in range(8):
        rows.append(_t(f"UPI/DR/{i:012d}/Airtel P/INDB/AirtelPaym/Recharge", 500))
    # investments / card bills / rent — few rows, large value
    for i in range(6):
        rows.append(_t(f"UPI/DR/{i:012d}/ZERODHA /HDFC/zerodha@hd/invest", 50000))
    for i in range(5):
        rows.append(_t(f"UPI/DR/{i:012d}/CRED Clu/UTIB/cred.club@/payment", 20000))
    for i in range(3):
        rows.append(_t(f"UPI/DR/{i:012d}/LANDLORD/SBIN/owner@ybl/rent payment", 30000))
    # self transfers
    for i in range(10):
        rows.append(_t(f"UPI/DR/{i:012d}/SAMPLENA/SBIN/9999999999/Payment", 15000))
    # aggregator-handled merchants whose display name is useless
    for i in range(15):
        rows.append(_t(f"UPI/DR/{i:012d}/UNKNOWN{i}/YESB/paytmqr{i:04d}/Payment", 300))
    # genuine person-to-person
    for i in range(12):
        rows.append(_t(f"UPI/DR/{i:012d}/FRIEND{i:02d}/SBIN/friend{i}@ybl/Payment", 800))
    # non-UPI
    for i in range(5):
        rows.append(_t(f"ATM CASH {i} SOMEWHERE by debit card", 5000))
    for i in range(4):
        rows.append(_t(f"UPI/CR/{i:012d}/EMPLOYER/HDFC/pay@corp/SALARY", 100000,
                       direction=Direction.CREDIT))
    return rows


def _distribution(own_names=OWN):
    cat = KeywordCategorizer(own_names=own_names)
    amt = Counter()
    for t in _corpus():
        if t.is_debit:
            amt[cat.categorize(t)] += t.amount.minor
    total = sum(amt.values())
    return {k: v / total for k, v in amt.items()}, amt


def test_no_single_bucket_dominates_spending():
    """The old failure mode: one catch-all held 50% of spend and told the user nothing."""
    share, _ = _distribution()
    biggest, biggest_share = max(share.items(), key=lambda kv: kv[1])
    assert biggest_share < 0.45, f"{biggest} holds {biggest_share:.0%} of spend"


def test_person_transfer_catch_all_stays_bounded():
    share, _ = _distribution()
    assert share.get("Transfers (people)", 0) < 0.20, share


def test_almost_everything_is_categorized():
    """"Other" means we gave up; it must stay tiny."""
    share, _ = _distribution()
    assert share.get("Other", 0) < 0.05, share


def test_self_transfers_are_separated_when_the_name_is_known():
    share, _ = _distribution()
    assert share.get("Self transfer", 0) > 0, "self transfers were not detected"
    # and they must NOT be silently invented when we don't know the user's name
    no_name, _ = _distribution(own_names=None)
    assert "Self transfer" not in no_name


def test_high_value_categories_are_recognised_not_dumped():
    _, amt = _distribution()
    for expected in ("Investments", "Card bills", "Rent"):
        assert amt.get(expected, 0) > 0, f"{expected} was not detected"


def test_recognisable_merchants_are_not_in_a_transfer_bucket():
    cat = KeywordCategorizer(own_names=OWN)
    assert cat.categorize(_t("UPI/DR/1/Swiggy I/YESB/swiggy@ybl/Payment", 400)) == "Food & Dining"
    assert cat.categorize(_t("UPI/DR/1/Fresh N /YESB/mab0450001/Pay", 250)) == "Groceries"
    assert cat.categorize(
        _t("UPI/DR/1/Airtel P/INDB/AirtelPaym/Recharge", 500)) == "Bills & Utilities"
