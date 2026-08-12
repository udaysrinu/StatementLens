"""Checks for deriving the account a statement belongs to.

Why this matters beyond tidiness: filing a savings account and its own credit cards under one label
double-counts every card-bill payment (a debit on the bank, a credit on the card) and picks one
presentation frame for both. On the real corpus a single `--account SBI` merged FIVE accounts.

The two failure modes are opposite and both bad:
  * splitting one account across months (a per-statement date in the label) fragments the history;
  * merging two accounts loses the distinction entirely.
Both are pinned below.
"""

from statementlens.usecases.account_id import account_label, is_same_account

SBI_TEXT = ("Welcome Mr SAMPLE USER Customer XXXXXXX5111 As on 28-02-25 Balance Summary "
            "MY HOME BRANCH INFORMATION SBI ITI JUNCTION Email ID sample@example.com")
HDFC_TEXT = "HDFC Bank Credit Card Statement HSN Code 997113 HDFC Bank Credit Cards GSTIN"
ICICI_TEXT = "ICICI Bank Limited credit card statement Retail"


def test_all_months_of_one_bank_account_share_a_label():
    """SBI filenames are <11-digit account><DDMMYYYY>; the date must not enter the label."""
    labels = {account_label(n, SBI_TEXT, fallback="X") for n in (
        "8959894511130062026.pdf", "8959894511131052026.pdf",
        "8959894511128022025.pdf", "8959894511131102025.pdf")}
    assert len(labels) == 1, labels
    assert labels == {"SBI ••5111"}


def test_the_trailing_period_is_only_stripped_when_it_parses_as_a_date():
    # a long account number whose tail is NOT a valid date must be kept intact
    label = account_label("99999999999999999999.pdf", "", fallback="X")
    assert label.endswith("9999")


def test_all_months_of_one_card_share_a_label():
    labels = {account_label(n, HDFC_TEXT, fallback="X") for n in (
        "5268XXXXXXXXXX85.PDF", "5268XXXXXXXXXX85_01-07-2026.PDF",
        "5268XXXXXXXXXX85_01-08-2026_559.pdf")}
    assert len(labels) == 1, labels
    assert labels == {"HDFC ••85"}


def test_a_programme_name_does_not_split_one_card():
    """Not every statement of a card mentions its programme, so it cannot be part of the identity."""
    with_programme = account_label("5268XXXXXXXXXX85_01-07-2026.PDF",
                                   HDFC_TEXT + " Swiggy HDFC Bank Credit Card", fallback="X")
    without = account_label("5268XXXXXXXXXX85.PDF", HDFC_TEXT, fallback="X")
    assert with_programme == without


def test_two_cards_from_one_issuer_stay_separate():
    a = account_label("4315XXXXXXXX4007_1908940_Retail_Amazon_NORM.pdf", ICICI_TEXT, fallback="X")
    b = account_label("6530XXXXXXXX4001_215128_Retail_Sapphiro_NORM.pdf", ICICI_TEXT, fallback="X")
    assert a != b
    assert a == "ICICI ••4007" and b == "ICICI ••4001"


def test_a_merchant_named_sbi_on_another_banks_statement_does_not_relabel_it():
    """"SBIPG" appears in narrations on HDFC statements; matching it would mislabel the account."""
    text = HDFC_TEXT + " SBIPG 826070079130One97Comm PayTM Mumbai 1,234.00"
    assert account_label("5268XXXXXXXXXX85.PDF", text, fallback="X") == "HDFC ••85"


def test_nothing_identifying_keeps_the_callers_label():
    """A label is derived, never invented — a wrong split is as damaging as a wrong merge."""
    assert account_label("random.pdf", "", fallback="MyAccount") == "MyAccount"
    assert account_label("", "", fallback="MyAccount") == "MyAccount"


def test_issuer_alone_is_used_when_there_is_no_number():
    assert account_label("Scapia_July_2026_150542724.pdf", "Scapia Federal Bank",
                         fallback="X") == "Scapia"


def test_is_same_account_compares_the_masked_tail():
    assert is_same_account("HDFC ••85", "Card ••85")            # same card, different issuer text
    assert not is_same_account("ICICI ••4007", "ICICI ••4001")
    # with no tail on either side it falls back to a name comparison
    assert is_same_account("Scapia", "scapia")
    assert not is_same_account("Scapia", "RBL")


def test_ingest_splits_a_mixed_folder_into_separate_accounts():
    """End-to-end: one --account flag must not merge a bank account with its own cards."""
    from statementlens.domain.models import Direction, Statement, Transaction
    from statementlens.domain.money import Money
    from statementlens.usecases.ingest import IngestStatements
    from datetime import date
    import tempfile
    from pathlib import Path
    from statementlens.adapters.persistence.sqlite_repo import SqliteTransactionRepository

    files = {"8959894511130062026.pdf": SBI_TEXT,
             "5268XXXXXXXXXX85_01-07-2026.PDF": HDFC_TEXT}

    class Src:
        def fetch(self, limit=100):
            return [type("R", (), {"source_id": n, "source_name": n, "data": n.encode()})()
                    for n in files]

    class Dec:
        def decrypt(self, data, hints): return data

    class Ext:
        def extract(self, data): return files[data.decode()]

    class Reg:
        def parse(self, text, *, account, source_id, source_name):
            return Statement(account, source_id, source_name, "p", (
                Transaction(txn_date=date(2026, 7, 1), description="ROW",
                            amount=Money.of(100, "INR"), direction=Direction.DEBIT,
                            merchant="ROW", raw_date="01-07-26"),))

    class Cat:
        def categorize(self, t): return "shopping"

    with tempfile.TemporaryDirectory() as tmp:
        repo = SqliteTransactionRepository(str(Path(tmp) / "t.db"))
        r = IngestStatements(source=Src(), decryptor=Dec(), extractor=Ext(),
                             parser_registry=Reg(), categorizer=Cat(),
                             repository=repo).run(account="Unknown", hints={})
        assert set(r.accounts) == {"SBI ••5111", "HDFC ••85"}, r.accounts
        # and opting out puts everything back under one label
        repo2 = SqliteTransactionRepository(str(Path(tmp) / "t2.db"))
        r2 = IngestStatements(source=Src(), decryptor=Dec(), extractor=Ext(),
                              parser_registry=Reg(), categorizer=Cat(),
                              repository=repo2).run(account="Merged", hints={},
                                                    split_accounts=False)
        assert set(r2.accounts) == {"Merged"}


def test_issuer_is_recovered_from_the_filename_alone():
    """`relabel` has only filenames — re-decrypting every PDF to name an issuer is not acceptable."""
    assert account_label("5268XXXXXXXXXX85.PDF", "", fallback="X") == "HDFC ••85"
    assert account_label("4315XXXXXXXX4007_x_Retail_Amazon_NORM.pdf", "", fallback="X") == "ICICI ••4007"
    assert account_label("8959894511130062026.pdf", "", fallback="X") == "SBI ••5111"


def test_statement_text_still_wins_over_the_filename_prefix():
    # an unknown prefix must not stop text detection working
    assert account_label("9999XXXXXXXX1234.pdf", "HDFC Bank Credit Card", fallback="X") == "HDFC ••1234"


def test_relabel_preserves_every_row_and_writes_a_backup():
    import tempfile
    from pathlib import Path
    from datetime import date
    from statementlens.adapters.persistence.sqlite_repo import SqliteTransactionRepository
    from statementlens.domain.models import Direction, Statement, Transaction
    from statementlens.domain.money import Money

    def row(desc, day):
        return Transaction(txn_date=date(2026, 7, day), description=desc,
                           amount=Money.of(100, "INR"), direction=Direction.DEBIT,
                           merchant=desc, raw_date=f"{day:02d}-07-26")

    with tempfile.TemporaryDirectory() as tmp:
        repo = SqliteTransactionRepository(str(Path(tmp) / "t.db"))
        repo.save_statement(Statement("Merged", "a", "8959894511130062026.pdf", "p",
                                      (row("BANKROW", 1),)))
        repo.save_statement(Statement("Merged", "b", "5268XXXXXXXXXX85.PDF", "p",
                                      (row("CARDROW", 2),)))
        before = len(repo.all())
        backup = repo.relabel_accounts(account_label)
        assert Path(backup).exists(), "a migration with no way back is not a migration"
        assert len(repo.all()) == before, "no row may be lost"
        assert {a for a, in repo._conn.execute("SELECT DISTINCT account FROM txns")} == {
            "SBI ••5111", "HDFC ••85"}
