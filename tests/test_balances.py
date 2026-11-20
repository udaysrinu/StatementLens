"""`statementlens balances`: the signed latest balance per account, as Netfolio reads it. Synthetic data."""
import tempfile
from datetime import date
from pathlib import Path

from statementlens.app import App
from statementlens.domain.models import Direction, Statement, Transaction
from statementlens.domain.money import Money
from statementlens.usecases.balances import walk

D, C = Direction.DEBIT, Direction.CREDIT


def _row(i, d, minor, direction, bal):
    return (i, "Bank ••1234", d, minor, direction, bal, 1, "x")


def test_an_overdrawn_balance_printed_unsigned_is_reported_negative():
    # 1,000 in the account, 1,500 out: the bank prints "500.00", the balance is −500
    signed, on, breaks = walk([_row(1, "2026-10-01", 0, "credit", 1000_00),
                               _row(2, "2026-10-02", 1500_00, "debit", 500_00)])
    assert (signed, on, breaks) == (-500_00, "2026-10-02", [])


def test_a_lost_row_breaks_the_chain_but_a_missing_month_does_not():
    rows = [_row(1, "2026-10-01", 0, "credit", 1000_00),
            _row(2, "2026-10-05", 100_00, "debit", 800_00),      # 100 out but 200 gone: a row is missing
            _row(3, "2026-12-01", 50_00, "debit", 700_00)]       # a statement-sized gap: not a break
    signed, _, breaks = walk(rows)
    assert [b[2] for b in breaks] == [-100_00] and signed == 700_00


def test_balances_has_netfolios_shape_and_never_guesses_a_card():
    with tempfile.TemporaryDirectory() as tmp:
        app = App(db_path=str(Path(tmp) / "t.db"))
        t = lambda d, amt, dr, bal=None: Transaction(date.fromisoformat(d), "UPI/demo", Money(amt, "INR"), dr,
                                                     balance=Money(bal, "INR") if bal is not None else None)
        app.repo.save_statement(Statement("Demo Bank ••1234", "s1", "bank.pdf", "Oct", (
            t("2026-10-01", 5_000_00, C, 5_000_00), t("2026-10-03", 1_200_00, D, 3_800_00))))
        app.repo.save_statement(Statement("Demo Card ••9876", "s2", "card.pdf", "Oct", (
            t("2026-10-04", 999_00, D), t("2026-10-20", 999_00, C))))
        b = app.balances()
        acc = {a["account"]: a for a in b["accounts"]}
        assert acc["Demo Bank ••1234"] == {"account": "Demo Bank ••1234", "institution": "Demo", "kind": "bank",
                                           "balance_paise": 3_800_00, "as_of": "2026-10-03", "source": "statement",
                                           "statement_period_to": "2026-10-03"}
        assert acc["Demo Card ••9876"]["kind"] == "card" and acc["Demo Card ••9876"]["balance_paise"] is None
        assert b["breaks"] == [] and b["generated_at"][:4].isdigit()
