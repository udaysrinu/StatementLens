"""Checks for shared-charge splits and the multi-account switcher. Synthetic data only.

The invariant that matters most: the BILLED amount is never modified. A card statement says ₹3,000
and must keep saying ₹3,000, or the ledger stops reconciling line-by-line against the PDF — which is
the whole reason anyone trusts these numbers. A split is an annotation on top, never an edit.
"""

import tempfile
from datetime import date
from pathlib import Path

from statementlens.app import App
from statementlens.domain.models import Direction, Statement, Transaction
from statementlens.domain.money import Money


def _app(tmp) -> App:
    app = App(db_path=str(Path(tmp) / "t.db"))
    app.repo.save_statement(Statement("HDFC Card", "s1", "card.pdf", "012026", (
        Transaction(txn_date=date(2026, 1, 5), description="DINNER PLACE",
                    amount=Money.of(3000, "INR"), direction=Direction.DEBIT,
                    merchant="Dinner Place", category="Food & dining", raw_date="05-01-26"),
        Transaction(txn_date=date(2026, 1, 6), description="SALARY",
                    amount=Money.of(50000, "INR"), direction=Direction.CREDIT,
                    merchant="Employer", category="income", raw_date="06-01-26"),)))
    return app


def _ref(app, merchant="Dinner Place") -> str:
    return next(t.source_ref for t in app.repo.all("HDFC Card") if t.merchant == merchant)


def test_a_split_never_changes_the_billed_amount():
    """The load-bearing invariant. Splitting must not touch `minor` on the txns row."""
    with tempfile.TemporaryDirectory() as tmp:
        app = _app(tmp)
        ref = _ref(app)
        app.set_split(ref, 100000, "Dinesh")           # ₹1,000 of ₹3,000 is mine
        row = next(t for t in app.repo.all("HDFC Card") if t.source_ref == ref)
        assert row.amount.minor == 300000, "the billed amount was mutated"
        assert app.repo.load_splits()[ref]["mine"] == 100000


def test_a_share_outside_the_billed_amount_is_refused():
    """Validated in the repo, not the UI: this is a money path.

    A share above the billed amount would make "my share" exceed the statement; a negative share
    would turn a spend into income.
    """
    with tempfile.TemporaryDirectory() as tmp:
        app = _app(tmp)
        ref = _ref(app)
        for bad in (300001, -1):
            try:
                app.set_split(ref, bad)
            except ValueError:
                pass
            else:
                raise AssertionError(f"accepted an invalid share: {bad}")
        assert app.repo.load_splits() == {}


def test_splitting_the_full_amount_clears_instead_of_storing_a_noop():
    # "split, then change your mind" should leave no trace rather than a row that means nothing
    with tempfile.TemporaryDirectory() as tmp:
        app = _app(tmp)
        ref = _ref(app)
        app.set_split(ref, 100000)
        app.set_split(ref, 300000)                     # the whole charge is mine after all
        assert ref not in app.repo.load_splits()


def test_a_split_survives_re_ingesting_the_statement():
    """Splits live in their own table for the same reason tag overrides do.

    Re-ingesting rewrites txns rows. If the split lived on txns, a refresh would silently revert the
    user's own annotation.
    """
    with tempfile.TemporaryDirectory() as tmp:
        app = _app(tmp)
        ref = _ref(app)
        app.set_split(ref, 100000, "Dinesh")
        # same statement again, as a re-import would
        app.repo.save_statement(Statement("HDFC Card", "s1", "card.pdf", "012026", (
            Transaction(txn_date=date(2026, 1, 5), description="DINNER PLACE",
                        amount=Money.of(3000, "INR"), direction=Direction.DEBIT,
                        merchant="Dinner Place", category="Food & dining", raw_date="05-01-26"),)))
        assert app.repo.load_splits()[ref]["mine"] == 100000


def test_the_dataset_carries_billed_and_mine_separately():
    with tempfile.TemporaryDirectory() as tmp:
        app = _app(tmp)
        ref = _ref(app)
        app.set_split(ref, 100000, "Dinesh")
        row = next(r for r in app.dataset("HDFC Card")["txns"] if r["ref"] == ref)
        assert row["a"] == 300000, "`a` must stay the billed amount"
        assert row["mine"] == 100000 and row["with"] == "Dinesh"
        # an unsplit row carries no split keys at all, keeping the payload small
        other = next(r for r in app.dataset("HDFC Card")["txns"] if r["ref"] != ref)
        assert "mine" not in other


def test_clearing_a_split_removes_it():
    with tempfile.TemporaryDirectory() as tmp:
        app = _app(tmp)
        ref = _ref(app)
        app.set_split(ref, 100000)
        app.clear_split(ref)
        assert app.repo.load_splits() == {}


def test_a_split_on_an_unknown_transaction_is_refused():
    with tempfile.TemporaryDirectory() as tmp:
        app = _app(tmp)
        try:
            app.set_split("no-such-hash", 100)
        except ValueError:
            return
        raise AssertionError("expected a ValueError for an unknown content_hash")


def test_accounts_lists_every_account_busiest_first_with_card_detection():
    """The switcher's data source. `is_card` must come from the real predicate, not the label.

    `--account` used to be required with no switcher in the UI, so a second account meant restarting
    the server. Cards were effectively invisible, which is why they accumulated far more untagged rows
    than the bank account did.
    """
    with tempfile.TemporaryDirectory() as tmp:
        app = _app(tmp)
        # a bank account with more rows, so ordering is observable
        app.repo.save_statement(Statement("SBI ••1111", "s2", "bank.pdf", "012026", tuple(
            Transaction(txn_date=date(2026, 1, d), description=f"UPI/DR/{d}/Shop/SBIN/9/Pay",
                        amount=Money.of(100 + d, "INR"), direction=Direction.DEBIT,
                        merchant="Shop", category="shopping", raw_date=f"{d:02d}-01-26",
                        balance=Money.of(9000, "INR"))
            for d in range(1, 6))))
        accts = {a["account"]: a for a in app.accounts()}
        assert accts["SBI ••1111"]["count"] == 5
        assert [a["account"] for a in app.accounts()][0] == "SBI ••1111", "busiest must come first"
        # the bank account carries balances and no card signals
        assert accts["SBI ••1111"]["is_card"] is False
