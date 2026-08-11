"""Generate README screenshots from SYNTHETIC data.

Never screenshot a real account for public docs: the dashboard shows lifetime spend, income,
individual trades, EMI account numbers and payee names. This builds a plausible-looking demo profile
instead — same code paths, invented money.

    python docs/make_screenshots.py            # writes docs/screenshots/demo.db
    statementlens --db docs/screenshots/demo.db serve --account "HDFC Bank"
"""

from __future__ import annotations

import random
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from statementlens.adapters.categorize.keyword_categorizer import KeywordCategorizer  # noqa: E402
from statementlens.adapters.persistence.sqlite_repo import SqliteTransactionRepository  # noqa: E402
from statementlens.domain.models import Direction, Statement, Transaction  # noqa: E402
from statementlens.domain.money import Money  # noqa: E402

OWN = "Demo User"

# (merchant, narration template, low, high, per-month frequency)
RECURRING = [
    ("Zerodha", "UPI/DR/{ref}/ZERODHA /HDFC/zerodha@hdfcbank/SIP", 25000, 25000, 1),
    ("Netflix", "UPI/DR/{ref}/NETFLIX /HDFC/netflix@razorpay/subscription", 649, 649, 1),
    ("MyGate", "UPI/DR/{ref}/MYGATE  /HDFC/mygate.rzp@icici/maintenance", 3100, 3100, 1),
    ("Airtel", "UPI/DR/{ref}/Airtel P/INDB/AirtelPaym@axis/postpaid", 999, 999, 1),
    ("Landlord", "UPI/DR/{ref}/RENT PAY/SBIN/landlord@ybl/rent", 32000, 32000, 1),
    ("CRED Club", "UPI/DR/{ref}/CRED Clu/UTIB/cred.club@axisb/card payment", 18000, 42000, 1),
]
FREQUENT = [
    ("Swiggy", "UPI/DR/{ref}/Swiggy I/YESB/swiggy@ybl/order", 180, 900, 9),
    ("Blinkit", "UPI/DR/{ref}/Blinkit /YESB/blinkit.rzp@hdfc/groceries", 150, 1200, 6),
    ("Uber", "UPI/DR/{ref}/UBER IND/HDFC/uber.rzp@icici/ride", 90, 480, 5),
    ("Amazon", "UPI/DR/{ref}/AMAZON  /YESB/amazon.pay@apl/order", 300, 4500, 3),
    ("BookMyShow", "UPI/DR/{ref}/BOOKMYSH/HDFC/bms.rzp@axis/tickets", 400, 1400, 1),
    ("Apollo Pharmacy", "UPI/DR/{ref}/APOLLO P/HDFC/apollo.rzp@hdfc/medicines", 200, 1800, 1),
    ("Indian Oil", "UPI/DR/{ref}/INDIANOI/HDFC/iocl.rzp@sbi/fuel", 1500, 3000, 2),
]
PEOPLE = ["Rahul S", "Priya M", "Arjun K", "Neha R", "Vikram T"]


def build(months: int = 20, seed: int = 7) -> list[Transaction]:
    rng = random.Random(seed)
    rows: list[Transaction] = []
    ref = iter(range(100_000_000_000, 999_999_999_999))
    balance = 24_00_000  # rupees

    end = date(2026, 8, 1)
    start = date(end.year - (months // 12), end.month, 1)
    day = start
    while day <= end:
        first_of_month = day.day == 1
        if first_of_month:
            # salary
            rows.append(_txn(day, "Acme Corp", f"UPI/CR/{next(ref)}/ACMECORP/HDFC/pay@acmecorp/SALARY AUG",
                             2_65_000, Direction.CREDIT))
            for merchant, tpl, lo, hi, _ in RECURRING:
                amt = lo if lo == hi else rng.randint(lo, hi)
                when = day + timedelta(days=rng.randint(0, 4))
                rows.append(_txn(when, merchant, tpl.format(ref=next(ref)), amt))
            # a self transfer, so the Self-transfer category has something to show
            rows.append(_txn(day + timedelta(days=2), OWN,
                             f"UPI/DR/{next(ref)}/DEMO USE/SBIN/9999999999/to savings", 40_000))

        for merchant, tpl, lo, hi, per_month in FREQUENT:
            if rng.random() < per_month / 30:
                rows.append(_txn(day, merchant, tpl.format(ref=next(ref)), rng.randint(lo, hi)))

        if rng.random() < 0.12:
            who = rng.choice(PEOPLE)
            handle = who.split()[0].lower()
            rows.append(_txn(day, who, f"UPI/DR/{next(ref)}/{who[:8].upper()}/SBIN/{handle}@ybl/split",
                             rng.randint(150, 2500)))
        if rng.random() < 0.05:
            rows.append(_txn(day, "ATM_WDL", "ATM CASH 1234 DEMO BRANCH by debit card",
                             rng.choice([2000, 5000, 10000])))
        day += timedelta(days=1)

    # one duplicate charge so the insight engine has something real to find
    dup_day = date(2026, 7, 11)
    for _ in range(2):
        rows.append(_txn(dup_day, "Swiggy",
                         f"UPI/DR/{next(ref)}/Swiggy I/YESB/swiggy@ybl/order", 1508))
        dup_day += timedelta(days=2)
    # a forgotten refund
    rows.append(_txn(date(2026, 7, 18), "Amazon",
                     f"UPI/CR/{next(ref)}/AMAZON  /YESB/amazon.pay@apl/refund", 2150,
                     Direction.CREDIT))

    rows.sort(key=lambda t: t.txn_date or date.min)
    # running balance, so the ledger looks like a real statement
    out = []
    for t in rows:
        balance += (t.amount.minor // 100) * (1 if not t.is_debit else -1)
        out.append(Transaction(t.txn_date, t.description, t.amount, t.direction, t.merchant,
                               Money.of(balance, "INR"), t.category, t.raw_date, t.source_ref))
    return out


def _txn(when: date, merchant: str, desc: str, rupees: int,
         direction: Direction = Direction.DEBIT) -> Transaction:
    return Transaction(txn_date=when, description=desc, amount=Money.of(rupees, "INR"),
                       direction=direction, merchant=merchant,
                       raw_date=when.strftime("%d-%m-%y"))


def main() -> None:
    out_dir = Path(__file__).resolve().parent / "screenshots"
    out_dir.mkdir(parents=True, exist_ok=True)
    db = out_dir / "demo.db"
    if db.exists():
        db.unlink()

    cat = KeywordCategorizer(own_names=[OWN])
    txns = [t.with_category(cat.categorize(t)) for t in build()]
    repo = SqliteTransactionRepository(str(db))
    repo.save_statement(Statement("HDFC Bank", "demo", "demo.pdf", "2026", tuple(txns)))
    print(f"{len(txns)} synthetic transactions -> {db}")
    print(f'Now run:  statementlens --db {db} serve --account "HDFC Bank" --own-name "{OWN}"')


if __name__ == "__main__":
    main()
