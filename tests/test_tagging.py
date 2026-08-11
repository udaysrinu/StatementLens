"""Checks for auto-tagging + the manual correction/notes path. Synthetic data only."""

from datetime import date

from statementlens.domain.models import Direction, Transaction
from statementlens.domain.money import Money
from statementlens.usecases.tagging import (
    SELF_TRANSFER_TAG, TAG_NAMES, UNTAGGED,
    TagStore, apply_tags, group_by_tag, normalize_tag, review_queue, untagged_count,
)


def txn(amount, merchant="", cat=None, ref="", direction=Direction.DEBIT):
    return Transaction(txn_date=date(2026, 1, 5), description=merchant,
                       amount=Money.of(amount, "INR"), direction=direction,
                       merchant=merchant, category=cat, source_ref=ref)


def test_everything_gets_a_tag_with_no_user_input():
    # the core promise: zero manual work still yields a full tag on every row
    rows = apply_tags([txn(400, "Swiggy", "Food & dining"), txn(900, "Mystery Co")])
    assert [r.category for r in rows] == ["food and drinks", UNTAGGED]
    assert all(r.category in TAG_NAMES for r in rows)


def test_legacy_categories_map_onto_the_closed_vocabulary():
    assert normalize_tag("Food & dining") == "food and drinks"
    assert normalize_tag("Card bills") == "credit card bill"
    assert normalize_tag("Transfers (people)") == "people"
    # unknown labels must NOT silently join the vocabulary
    assert normalize_tag("artisanal cheese club") == UNTAGGED
    assert normalize_tag(None) == UNTAGGED


def test_merchant_correction_fixes_past_and_future_rows():
    s = TagStore()
    s.correct_merchant("Fresh N", "grocery")
    rows = apply_tags([txn(84, "Fresh N"), txn(120, "Fresh N")], s)
    assert [r.category for r in rows] == ["grocery", "grocery"]


def test_correction_survives_reingest_beating_the_categorizer():
    # re-running ingest must not revert a fix — the categorizer says people, the user said rent
    s = TagStore()
    s.correct_merchant("Landlord", "rent")
    row = apply_tags([txn(30000, "Landlord", "Transfers (people)")], s)[0]
    assert row.category == "rent"


def test_single_row_correction_beats_merchant_rule():
    s = TagStore()
    s.correct_merchant("Ashu", "people")
    s.correct_one("ref-9", "rent")
    rows = apply_tags([txn(500, "Ashu", ref="ref-1"), txn(30000, "Ashu", ref="ref-9")], s)
    assert [r.category for r in rows] == ["people", "rent"]


def test_notes_round_trip_and_clear():
    s = TagStore()
    t = txn(13394, "Appliance Co", ref="ref-fridge")
    s.add_note("ref-fridge", "  fridge, adjusted against salary  ")
    assert s.note_for(t) == "fridge, adjusted against salary"
    s.add_note("ref-fridge", "")
    assert s.note_for(t) == ""


def test_self_transfer_excluded_from_tag_breakdown():
    rows = [txn(5000, "Own Acct", SELF_TRANSFER_TAG), txn(400, "Swiggy", "food and drinks")]
    groups = group_by_tag(rows)
    assert [g["tag"] for g in groups] == ["food and drinks"]
    assert abs(groups[0]["share"] - 1.0) < 1e-9      # share is of real spend, not inflated


def test_group_by_tag_sorted_by_amount_with_shares():
    rows = [txn(1000, "A", "grocery"), txn(3000, "B", "rent"), txn(1000, "C", "grocery")]
    groups = group_by_tag(rows)
    assert groups[0]["tag"] == "rent" and groups[0]["count"] == 1
    assert groups[1]["tag"] == "grocery" and groups[1]["count"] == 2
    assert abs(sum(g["share"] for g in groups) - 1.0) < 1e-9


def test_review_queue_only_surfaces_unplaced_rows_biggest_first():
    rows = [txn(97000, "Big Unknown"), txn(84, "Small Unknown"), txn(400, "Swiggy", "food and drinks")]
    q = review_queue(rows)
    assert [r["merchant"] for r in q] == ["Big Unknown", "Small Unknown"]   # Swiggy not nagged


def test_review_queue_skips_already_corrected_merchants():
    s = TagStore()
    s.correct_merchant("Big Unknown", "loans")
    assert review_queue([txn(97000, "Big Unknown")], s) == []


def test_review_queue_excludes_credits():
    # salary credits are income, not untagged spending — they belong in no spend-tag queue
    rows = [txn(190000, "SAL FOR SEP 2022", direction=Direction.CREDIT),
            txn(900, "Real Unknown Spend")]
    assert [r["merchant"] for r in review_queue(rows)] == ["Real Unknown Spend"]


def test_untagged_count_measures_categorizer_quality():
    assert untagged_count([txn(1, "A"), txn(1, "B", "grocery")]) == 1
