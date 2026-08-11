"""Checks for merchant-similarity grouping and bulk retagging.

The measured problem: on real card data one merchant appeared under 54 distinct narration strings.
The risk in fixing it is over-grouping — a bulk correction landing on unrelated transactions — so
these tests pin both directions: variants of one merchant DO group, and different merchants DON'T.
"""

import tempfile
from datetime import date
from pathlib import Path

from statementlens.adapters.persistence.sqlite_repo import SqliteTransactionRepository
from statementlens.domain.models import Direction, Statement, Transaction
from statementlens.domain.money import Money
from statementlens.usecases.similar import (
    disagreeing_groups, find_similar, group_all, group_key, merchant_key,
)


def txn(desc, rupees=100, *, day=11, credit=False, tag=None, ref=None):
    return Transaction(txn_date=date(2026, 7, day), description=desc,
                       amount=Money.of(rupees, "INR"),
                       direction=Direction.CREDIT if credit else Direction.DEBIT,
                       merchant=desc[:40], category=tag,
                       raw_date=f"{day:02d}-07-26",
                       source_ref=ref or f"r-{desc[:12]}-{rupees}-{day}")


# --- normalization -----------------------------------------------------------

def test_gateway_prefixes_and_cities_collapse_to_one_key():
    """All of these were separate strings on a real statement for the same merchant."""
    variants = [
        "BUNDL TECHNOLOGIES BENGALURU",     # legal entity name
        "BUNDL TECHNOLOGIESBENGALURU",      # no space before the city
        "CAS*Swiggy Bengaluru",             # gateway prefix
        "RAZ*SWIGGYBengaluru",
        "Razorpay*Swiggy Limite Bengaluru",  # corporate suffix, truncated
        "SWIGGY LIMITED BANGALORE",
        "EMI RAZ*SWIGGYBengaluru",          # type word in front of the gateway
        "10% Swiggy CashBack",              # reward wording (a credit, see direction test)
        "ADJ 1% Swiggy BLCK Cashback Reversa",
    ]
    keys = {merchant_key(txn(v)) for v in variants}
    assert keys == {"swiggy"}, keys


def test_reference_numbers_do_not_create_new_keys():
    a = merchant_key(txn("10% Swiggy CashBack (Ref# ST2617000840000)"))
    b = merchant_key(txn("10% Swiggy CashBack (Ref# ST2618100840000)"))
    assert a == b == "swiggy"


def test_different_merchants_stay_apart():
    """Over-grouping is the dangerous failure: a bulk retag would hit unrelated rows."""
    keys = {merchant_key(txn(d)) for d in (
        "POLICYBAZAAR GURGAON", "Airbnb Payments India Gurgoan",
        "LIFE INSURANCE CORPORATNOIDA", "SNITCH VISAKHAPATNA")}
    assert len(keys) == 4, keys


def test_swiggy_sub_brands_are_not_merged():
    """Instamart is groceries and Dineout is a restaurant — merging them destroys real signal."""
    assert len({merchant_key(txn(d)) for d in (
        "PAY*SWIGGY INSTAMART GURGAON", "RSP*SWIGGY DINEOUT BENGALURU")}) == 2


def test_purchases_and_credits_are_grouped_separately():
    """A cashback must not be bulk-tagged into a spend category alongside purchases."""
    purchase = txn("RAZ*SWIGGY Bengaluru", 500)
    cashback = txn("10% Swiggy CashBack", 50, credit=True)
    assert merchant_key(purchase) == merchant_key(cashback)      # same merchant…
    assert group_key(purchase) != group_key(cashback)            # …different group


def test_upi_narrations_use_the_decoded_payee():
    a = merchant_key(txn("UPI/DR/1/Swiggy I/YESB/swiggy@ybl/order"))
    b = merchant_key(txn("UPI/DR/2/Swiggy I/YESB/swiggy@ybl/order"))
    assert a == b and a != ""


def test_unusable_narrations_yield_no_key():
    assert merchant_key(txn("12345678901234")) == ""
    assert group_key(txn("12345678901234")) == ""


# --- grouping ----------------------------------------------------------------

def test_find_similar_returns_the_other_rows_with_a_reason():
    target = txn("RAZ*SWIGGY Bengaluru", 300, ref="target")
    universe = [target, txn("BUNDL TECHNOLOGIES BENGALURU", 400, ref="a"),
                txn("CAS*Swiggy Bengaluru", 500, ref="b"),
                txn("POLICYBAZAAR GURGAON", 5000, ref="c")]
    g = find_similar(target, universe)
    assert g is not None
    assert {t.source_ref for t in g.transactions} == {"a", "b"}   # target and unrelated excluded
    assert "same merchant" in g.reason
    assert g.count == 2 and g.total_minor == 90000


def test_find_similar_is_none_when_nothing_matches():
    target = txn("ONE OFF SHOP", 100, ref="t")
    assert find_similar(target, [target, txn("OTHER SHOP", 200)]) is None


def test_group_all_orders_by_value_and_skips_singletons():
    txns = [txn("SHOP A", 100), txn("SHOP A", 200),          # group, 300
            txn("BIG B", 5000), txn("BIG B", 6000),           # group, 11000
            txn("LONELY C", 900)]                             # singleton -> skipped
    groups = group_all(txns)
    assert [g.count for g in groups] == [2, 2]
    assert groups[0].total_minor > groups[1].total_minor


def test_disagreeing_groups_surfaces_inconsistent_tags():
    txns = [txn("RAZ*SWIGGY Bengaluru", 100, tag="food and drinks", ref="1"),
            txn("BUNDL TECHNOLOGIES BENGALURU", 200, tag="loans", ref="2"),
            txn("POLICYBAZAAR GURGAON", 300, tag="insurance", ref="3"),
            txn("POLICYBAZAAR GURGAON", 400, tag="insurance", ref="4")]
    conflicts = disagreeing_groups(txns)
    assert len(conflicts) == 1
    assert conflicts[0].current_tags == ["food and drinks", "loans"]


def test_group_as_dict_carries_everything_the_ui_needs():
    target = txn("RAZ*SWIGGY Bengaluru", 300, ref="t")
    g = find_similar(target, [target, txn("CAS*Swiggy Bengaluru", 500, ref="b")])
    d = g.as_dict()
    assert d["count"] == 1 and d["refs"] == ["b"]
    assert d["sample"][0]["desc"] and d["sample"][0]["amount"] == 50000
    assert "reason" in d and "label" in d


# --- bulk correction ---------------------------------------------------------

def test_correct_many_tags_exactly_the_selected_rows():
    with tempfile.TemporaryDirectory() as tmp:
        repo = SqliteTransactionRepository(str(Path(tmp) / "t.db"))
        repo.save_statement(Statement("A", "s", "f.pdf", "p", (
            txn("RAZ*SWIGGY Bengaluru", 100, ref=None),
            txn("BUNDL TECHNOLOGIES BENGALURU", 200),
            txn("POLICYBAZAAR GURGAON", 300))))
        rows = repo.all("A")
        chosen = [t.source_ref for t in rows if "SWIGGY" in t.description.upper()
                  or "BUNDL" in t.description.upper()]
        assert len(chosen) == 2
        n = repo.correct_many(tag="food and drinks", content_hashes=chosen)
        assert n == 2
        after = {t.description[:12]: t.category for t in repo.all("A")}
        store = repo.load_tags()
        assert all(store.by_ref[c] == "food and drinks" for c in chosen)
        # the untouched row keeps whatever it had
        assert len(store.by_ref) == 2


def test_correct_many_with_no_refs_is_a_noop():
    with tempfile.TemporaryDirectory() as tmp:
        repo = SqliteTransactionRepository(str(Path(tmp) / "t.db"))
        assert repo.correct_many(tag="grocery", content_hashes=[]) == 0
        assert repo.correct_many(tag="grocery", content_hashes=[""]) == 0


def test_bulk_corrections_survive_a_reload_and_apply_to_the_dataset():
    from statementlens.usecases.analytics import build_dataset
    with tempfile.TemporaryDirectory() as tmp:
        db = str(Path(tmp) / "t.db")
        repo = SqliteTransactionRepository(db)
        repo.save_statement(Statement("A", "s", "f.pdf", "p", (
            txn("RAZ*SWIGGY Bengaluru", 100), txn("BUNDL TECHNOLOGIES BENGALURU", 200))))
        refs = [t.source_ref for t in repo.all("A")]
        repo.correct_many(tag="grocery", content_hashes=refs)

        fresh = SqliteTransactionRepository(db)          # new connection
        ds = build_dataset(fresh.all("A"), account="A", tags=fresh.load_tags())
        assert {r["c"] for r in ds["txns"]} == {"grocery"}
