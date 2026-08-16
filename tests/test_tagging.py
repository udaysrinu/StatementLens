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


def test_newer_merchant_correction_clears_stale_row_override():
    # a stale per-row override must not shadow a NEW merchant-wide fix forever, or the user taps
    # a tag chip and nothing visibly changes
    s = TagStore()
    s.correct_one("ref-1", "travel")
    s.correct_merchant("Swiggy", "grocery", member_refs=["ref-1"])
    row = apply_tags([txn(400, "Swiggy", ref="ref-1")], s)[0]
    assert row.category == "grocery"
    assert "ref-1" not in s.by_ref


def test_merchant_correction_leaves_other_merchants_row_overrides_alone():
    s = TagStore()
    s.correct_one("ref-other", "rent")
    s.correct_merchant("Swiggy", "grocery", member_refs=["ref-1"])
    assert s.by_ref["ref-other"] == "rent"


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


def test_recategorize_is_a_dry_run_by_default_and_conserves_money():
    """Categories are written at INGEST, so engine fixes never reached rows already imported.

    On the real store that left 407 of 3,510 rows (12%) stale — including 117 cashback rows still filed
    as "Food & Dining" from a bug fixed months earlier, so a reward was still inflating food spending.
    There was no way to re-derive them.

    Two invariants: it must not write unless asked, and it must only MOVE money between categories,
    never change the total.
    """
    import tempfile
    from datetime import date
    from pathlib import Path

    from statementlens.app import App
    from statementlens.domain.models import Direction, Statement, Transaction
    from statementlens.domain.money import Money

    with tempfile.TemporaryDirectory() as tmp:
        app = App(db_path=str(Path(tmp) / "t.db"))
        # stored with a deliberately wrong category, as an older engine would have written it
        app.repo.save_statement(Statement("HDFC", "s1", "c.pdf", "012026", (
            Transaction(txn_date=date(2026, 1, 5), description="BUNDL TECHNOLOGIES BENGALURU",
                        amount=Money.of(500, "INR"), direction=Direction.DEBIT,
                        merchant="BUNDL TECHNOLOGIES", category="Other", raw_date="05-01-26"),)))

        def total():
            return sum(t.amount.minor for t in app.repo.all())

        before = total()
        dry = app.recategorize()                      # default must not write
        assert dry["dry_run"] is True and dry["changed"] >= 1
        assert (app.repo.all()[0].category or "") == "Other", "a dry run must not write"

        done = app.recategorize(dry_run=False)
        assert done["changed"] >= 1 and "backup" in done
        assert app.repo.all()[0].category != "Other", "the fresh category was not applied"
        assert total() == before, "recategorising must never change the money, only its label"
