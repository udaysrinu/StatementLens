"""Checks for cancelled-pair detection and person netting. Synthetic data only.

The risk this code carries is specific: a loose match silently DELETES real spending from every
total. So the tests lean on the false-positive side — what must NOT be paired matters more than what
must.
"""

from datetime import date

from statementlens.domain.models import Direction, Transaction
from statementlens.domain.money import Money
from statementlens.usecases.netting import (
    REVERSAL_WINDOW_DAYS, find_reversals, person_nets, reversed_refs,
)


def txn(day, amount, direction=Direction.DEBIT, merchant="", desc="", month=1, ref=None):
    return Transaction(
        txn_date=date(2026, month, day), description=desc or merchant,
        amount=Money.of(amount, "INR"), direction=direction,
        merchant=merchant, category=None, source_ref=ref or f"{month}-{day}-{amount}-{direction}")


def test_same_day_refund_is_a_reversal():
    out = txn(16, 1554, merchant="IRCTC", desc="UPI/DR/213242717832/IRCTC We/YESB/paytm-6515/Pay")
    back = txn(16, 1554, Direction.CREDIT, merchant="IRCTC",
               desc="UPI/CR/528901931014/IRCTC We/YESB/paytm-6515/expre")
    revs = find_reversals([out, back])
    assert len(revs) == 1
    assert revs[0].amount == 155400 and revs[0].same_day


def test_a_repayment_months_later_is_not_a_reversal():
    """The whole reason this is two features and not one.

    Money lent in January and repaid in June is two real transfers. Treating it as a cancellation
    would delete a genuine spend from the total, so only the opt-in person-netting may combine them.
    """
    lent = txn(5, 5000, merchant="Sam",
               desc="UPI/DR/111111111111/Sam Ja/SBIN/9000000001/Pay", month=1)
    back = txn(5, 5000, Direction.CREDIT, merchant="Sam",
               desc="UPI/CR/222222222222/Sam Ja/SBIN/9000000001/Pay", month=6)
    assert find_reversals([lent, back]) == []
    # but it IS a two-way counterparty
    people = person_nets([lent, back])
    assert len(people) == 1 and people[0].net == 0 and people[0].offset == 500000


def test_a_refund_cannot_precede_its_charge():
    back = txn(1, 900, Direction.CREDIT, merchant="Shop", desc="UPI/CR/1/Shop/SBIN/9/Pay")
    out = txn(9, 900, merchant="Shop", desc="UPI/DR/2/Shop/SBIN/9/Pay")
    assert find_reversals([back, out]) == []


def test_a_shared_bank_reference_pairs_beyond_the_window():
    """A bank reversing a failed transfer reuses its own reference on both legs.

    That is far harder evidence than amount+date — a friend repaying you never lands on the same
    12-digit number — so it is allowed to match outside the day window.
    """
    ref = "600000000001"
    out = txn(5, 212000, desc=f"IMPS/{ref}/IBKL-xx000-Payee/Loan Rep", month=1)
    back = txn(5, 212000, Direction.CREDIT,
               desc=f"IMPS/{ref}/IBKL-xx000-Payee/Loan Rep", month=3)
    revs = find_reversals([out, back])
    assert len(revs) == 1
    assert revs[0].bank_ref == ref and revs[0].confidence == "certain"
    assert revs[0].days > REVERSAL_WINDOW_DAYS      # only the shared reference got it here


def test_a_payees_phone_number_is_not_a_bank_reference():
    """A UPI VPA usually ENDS in the payee's 10-digit phone number, identical on every transfer.

    Reading the reference by "first long digit run" picked that up, so two same-amount payments to
    the same friend months apart matched as a bank reversal with "certain" confidence — silently
    deleting a real transfer. The reference is the field after the channel, and only that.
    """
    out = txn(5, 5000, merchant="Sam",
              desc="UPI/DR/111111111111/Sam Ja/SBIN/9000000001/Pay", month=1)
    back = txn(5, 5000, Direction.CREDIT, merchant="Sam",
               desc="UPI/CR/222222222222/Sam Ja/SBIN/9000000001/Pay", month=6)
    assert find_reversals([out, back]) == [], "the shared phone number must not pair these"


def test_amount_only_matches_are_labelled_less_confident():
    out = txn(1, 2500, merchant="Bob", desc="UPI/DR/111111111111/Bob/SBIN/9/Pay")
    back = txn(6, 2500, Direction.CREDIT, merchant="Bob", desc="UPI/CR/222222222222/Bob/SBIN/9/Pay")
    revs = find_reversals([out, back])
    assert len(revs) == 1 and revs[0].confidence == "likely"


def test_one_credit_cannot_cancel_three_debits():
    """Three ₹500 charges and one ₹500 refund is ONE reversal, not three.

    Without claiming, a single refund would wipe out every same-amount charge with the payee and
    remove ₹1,500 of real spending.
    """
    d = [txn(i, 500, merchant="Cafe", desc=f"UPI/DR/{i}/Cafe/SBIN/9/Pay") for i in (1, 2, 3)]
    c = [txn(3, 500, Direction.CREDIT, merchant="Cafe", desc="UPI/CR/9/Cafe/SBIN/9/Pay")]
    revs = find_reversals(d + c)
    assert len(revs) == 1
    refs, total = reversed_refs(d + c)
    assert total == 50000 and len(refs) == 2      # exactly one pair's worth


def test_different_counterparties_never_pair():
    out = txn(1, 800, merchant="Zomato", desc="UPI/DR/1/Zomato/YESB/zomato/Pay")
    back = txn(1, 800, Direction.CREDIT, merchant="Swiggy", desc="UPI/CR/2/Swiggy/ICIC/swiggy/Pay")
    assert find_reversals([out, back]) == []


def test_a_different_amount_is_not_a_reversal():
    # a partial refund is NOT a cancellation: real money was still spent
    out = txn(1, 1000, merchant="Shop", desc="UPI/DR/1/Shop/SBIN/9/Pay")
    back = txn(2, 400, Direction.CREDIT, merchant="Shop", desc="UPI/CR/2/Shop/SBIN/9/Pay")
    assert find_reversals([out, back]) == []


def test_one_way_payees_are_not_offered_for_netting():
    # a payee you have only ever paid has nothing to net; listing it would bury the real ones
    only_paid = [txn(i, 300, merchant="Metro", desc=f"UPI/DR/{i}/Metro/SBIN/9/Pay") for i in (1, 2)]
    assert person_nets(only_paid) == []


def test_person_net_direction_says_who_owes():
    paid = txn(1, 10000, merchant="Dinesh", desc="UPI/DR/1/Dinesh/SBIN/9/Pay")
    got = txn(20, 4000, Direction.CREDIT, merchant="Dinesh", desc="UPI/CR/2/Dinesh/SBIN/9/Pay")
    p = person_nets([paid, got])[0]
    assert p.paid == 1000000 and p.received == 400000
    assert p.net == 600000                        # positive: out of pocket
    assert p.offset == 400000                     # the part that cancels


def test_generic_narrations_are_never_paired():
    """merchant_key returns something too short to identify a payee -> no pairing.

    Pairing on a 2-character key would net unrelated people together.
    """
    out = txn(1, 700, merchant="A", desc="A")
    back = txn(1, 700, Direction.CREDIT, merchant="A", desc="A")
    assert find_reversals([out, back]) == []
