"""Live transactions from bank SMS / alert emails, reconciled by the monthly statement.

SBI sends no email for UPI, so its SMS (forwarded to macOS Messages) is the only live feed. Each live
row is provisional; when the statement for its month lands it is PAIRED with the statement line
(by the UPI reference where there is one, else date ±2 days + amount + direction). A paired row is
replaced by the statement line; an unpaired one never settled and is set aside, out of every total.
All wordings below are the banks' real formats with made-up numbers.
"""
import tempfile
from datetime import date
from pathlib import Path

from statementlens.adapters.parsers.alert_parser import parse_alert
from statementlens.adapters.persistence.sqlite_repo import SqliteTransactionRepository
from statementlens.adapters.sources.alert_email_source import AlertMessage
from statementlens.adapters.sources.sms_source import body_text
from statementlens.app import App
from statementlens.domain.models import Direction, Statement, Transaction
from statementlens.domain.money import Money

UPI = ("Dear UPI user A/C X1234 debited by {amt} on date {d}Nov26 trf to SAMPLE CAFE HOUS Refno {ref} "
       "If not u? call-1800111109 for other services-18001234-SBI")


def test_attributed_body_decodes_short_and_long_strings():
    short = b"\x04\x0bstreamtyped\x81\xe8\x03\x84\x01@\x84\x84\x84\x12NSAttributedString\x00\x84\x84\x08NSObject\x00\x85\x92\x84\x84\x84\x08NSString\x01\x94\x84\x01+\x05hello\x86"
    assert body_text(short) == "hello"
    text = "x" * 300
    long = b"..NSString\x01\x94\x84\x01+\x81" + len(text).to_bytes(2, "little") + text.encode() + b"\x86"
    assert body_text(long) == text and body_text(None) is None


def test_sbi_upi_debit_reversal_and_dividend_parse():
    a = parse_alert(UPI.format(amt="20.00", d="15", ref="111122223333"))
    assert (a.amount_minor, a.direction, a.txn_date, a.account_hint, a.ref) == \
           (2000, Direction.DEBIT, date(2026, 11, 15), "1234", "111122223333")
    r = parse_alert("Dear SBI UPI User, ur A/cX1234 credited with Rs190 on 09Oct26 against reversal of txn (Ref no 444455556666)")
    assert (r.direction, r.amount_minor, r.ref) == (Direction.CREDIT, 19000, "444455556666")
    n = parse_alert("Dear Customer,Your A/C XXXXX11234 has a credit by NACH- SAMPLE INDUSTRIES of Rs 12.50 on 10/11/26 Avl Bal Rs 1,000.00")
    assert (n.direction, n.amount_minor, n.account_hint) == (Direction.CREDIT, 1250, "1234")


def test_icici_card_email_parses_and_otp_and_mandate_do_not():
    i = parse_alert("Your ICICI Bank Credit Card XX3456 has been used for a transaction of INR 1230.00 on Nov 18, 2026 "
                    "at 11:47:33. Info: AmazonSellerServices. The Available Credit Limit on your card is INR 1,00,000.00",
                    subject="Transaction alert for your ICICI Bank Credit Card")
    assert (i.amount_minor, i.direction, i.txn_date, i.account_hint) == (123000, Direction.DEBIT, date(2026, 11, 18), "3456")
    assert parse_alert("1234 is OTP. Thanks for using SBI Fastag Service. Do not share this OTP with anyone. -SBI") is None
    sms = parse_alert("Rs 8,970.00 spent on ICICI Bank Card XX9012 on 16-Nov-26 at CITY CLINIC . Avl Lmt: Rs 1,00,000.00. "
                      "To dispute, call 18000000/SMS BLOCK 9012 to 9000000000.")
    assert (sms.amount_minor, sms.txn_date, sms.merchant, sms.account_hint) == (897000, date(2026, 11, 16), "CITY CLINIC", "9012")


def _settled(day, rupees, desc):
    return Transaction(txn_date=date(2026, 11, day), description=desc, amount=Money(rupees * 100, "INR"),
                       direction=Direction.DEBIT, raw_date=f"{day:02d}/11/26", source_ref=f"s{day}{rupees}")


class _Src:
    def __init__(self, msgs): self.msgs = msgs
    def messages(self): return self.msgs


def test_live_rows_route_reconcile_and_never_double_count():
    with tempfile.TemporaryDirectory() as tmp:
        app = App(db_path=str(Path(tmp) / "t.db"))
        # the statement for 1-30 Nov: the coffee (its narration carries the UPI ref) and the bakery
        # (no ref in the SMS's statement line; pairs on date + amount). The ₹99 SMS has no line: it failed.
        app.repo.save_statement(Statement("SBI ••5678", "s1", "nov.pdf", "p", (
            _settled(1, 500, "opening"), _settled(15, 20, "UPI/DR/111122223333/SAMPLE CAFE"),
            _settled(10, 190, "UPI/DR/SAMPLE BAKERY"), _settled(30, 10, "charges"))))
        sms = [AlertMessage("sms:1", "", "SBIUPI-S", UPI.format(amt="20.00", d="15", ref="111122223333")),
               AlertMessage("sms:2", "", "SBIUPI-S", UPI.format(amt="190.00", d="09", ref="777788889999")),
               AlertMessage("sms:3", "", "SBIUPI-S", UPI.format(amt="99.00", d="12", ref="222222222222"))]
        r = app.ingest_alerts(sources=[_Src(sms)])
        # X1234 is not in any label: routed to the bank's only account
        s = r["accounts"]["SBI ••5678"]
        assert (s["confirmed_by_statement"], s["never_settled"], s["live_now"]) == (2, 1, 0)
        assert [u["minor"] for u in app.repo.unsettled("SBI ••5678")] == [9900]
        # totals are exactly the statement: nothing doubled, the failed ₹99 not counted
        assert sum(t.amount.minor for t in app.repo.all("SBI ••5678")) == (500 + 20 + 190 + 10) * 100
        # re-reading the same SMS changes nothing
        app.ingest_alerts(sources=[_Src(sms)])
        assert sum(t.amount.minor for t in app.repo.all("SBI ••5678")) == 72000
        assert len(app.repo.unsettled()) == 1


def test_a_reread_rebuilds_live_rows_instead_of_adding_renamed_copies():
    with tempfile.TemporaryDirectory() as tmp:
        app = App(db_path=str(Path(tmp) / "t.db"))
        app.repo.save_statement(Statement("SBI ••5678", "s1", "oct.pdf", "p", (
            Transaction(txn_date=date(2026, 10, 1), description="old", amount=Money(100, "INR"),
                        direction=Direction.DEBIT, raw_date="01/10/26", source_ref="o"),)))
        neft = AlertMessage("sms:n", "", "SBIPSG-S", "Dear Customer, Your A/c XX1234 has been debited with INR 15,000.00 on "
                            "17/11/26 towards NEFT with UTR SBIN000000000001 sent to Some Payee BARB0ABCDEF-SBI")
        app.ingest_alerts(sources=[_Src([neft])])
        # an older build stored it under a worse name; a re-read must REPLACE that row
        app.repo._conn.execute("UPDATE txns SET description='alert', content_hash='stale' WHERE provisional=1")
        app.ingest_alerts(sources=[_Src([neft])])
        live = [(t.amount.minor, t.description) for t in app.repo.all("SBI ••5678") if t.provisional]
        assert live == [(1500000, "Some Payee")]


def test_same_swipe_by_sms_and_email_is_kept_once_but_two_real_coffees_stay_two():
    with tempfile.TemporaryDirectory() as tmp:
        app = App(db_path=str(Path(tmp) / "t.db"))
        app.repo.save_statement(Statement("ICICI ••3456", "s1", "oct.pdf", "p", (
            Transaction(txn_date=date(2026, 10, 1), description="old", amount=Money(100, "INR"),
                        direction=Direction.DEBIT, raw_date="01/10/26", source_ref="o"),)))
        card = ("Your ICICI Bank Credit Card XX3456 has been used for a transaction of INR {a} on Nov 18, 2026 "
                "at 11:47:33. Info: {m}. The Available Credit Limit on your card is INR 1,00,000.00")
        msgs = [AlertMessage("sms:a", "", "ICICIT-S", card.format(a="1230.00", m="AMAZON")),
                AlertMessage("gm:1", "Transaction alert for your ICICI Bank Credit Card", "credit_cards@icici.bank.in",
                             card.format(a="1230.00", m="AmazonSellerServices")),
                AlertMessage("sms:b", "", "ICICIT-S", card.format(a="20.00", m="CAFE")),
                AlertMessage("sms:c", "", "ICICIT-S", card.format(a="20.00", m="CAFE"))]
        app.ingest_alerts(sources=[_Src(msgs)])
        live = sorted(t.amount.minor for t in app.repo.all("ICICI ••3456") if t.provisional)
        assert live == [2000, 2000, 123000]
