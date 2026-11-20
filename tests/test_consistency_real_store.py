"""Consistency on the REAL store: nothing lost on the way in, and every figure agrees wherever shown.

Not a regression test — nothing here pins a value. Each test states an invariant that must hold for
ANY correct store, and is run against the user's actual data because synthetic rows never contain
the shapes that broke things: a statement filed under the wrong account, a quarterly re-issue parsed
with its balance read as the amount, a reward table parsed as 2018 purchases, an overdrawn balance
printed without its sign. Every one of those passed the unit tests.

Two layers:
  * INGEST — nothing left unparsed or misread. The running balance is the strongest check available:
    on an account that prints one, `previous ± amount == balance` for every row, so a missing, extra
    or misread line breaks the chain at exactly that point.
  * DISPLAY — the dashboard computes its totals in the browser. The SHIPPED JavaScript is executed in
    node over the same rows the server sends and compared with the server's own figures, and every
    breakdown must sum to the headline it explains. Nothing is re-implemented here, so the test cannot
    drift from what the user sees.

No store on this machine (CI, a fresh clone) → every test is a no-op. No values are committed; the
repo is public and these are the user's real finances.
"""
import json
import os
import re
import shutil
import sqlite3
import subprocess
from collections import defaultdict
from pathlib import Path

STORE = Path(os.getenv("STATEMENTLENS_DB", Path.home() / ".statementlens" / "store.db"))

#: A balance chain may legitimately break across a statement the bank never sent: the rows on either
#: side are both right, the month between is simply absent. Shorter breaks are a lost or misread row.
MISSING_STATEMENT_DAYS = 25


def _have_store() -> bool:
    return STORE.exists()


def _rows():
    db = sqlite3.connect(str(STORE))
    return db.execute(
        "SELECT id, account, iso_date, minor, direction, balance_minor, statement_id, description "
        "FROM txns WHERE provisional = 0 ORDER BY account, iso_date, id").fetchall()


def _by_account():
    out = defaultdict(list)
    for r in _rows():
        out[r[1]].append(r)
    return out


def _days(a: str, b: str) -> int:
    from datetime import date
    return (date.fromisoformat(b) - date.fromisoformat(a)).days


# ---------------------------------------------------------------------------------------- INGEST

def balance_chain_breaks():
    """[(account, prev_row, row, off_by_minor)] for every link that does not reconcile.

    Banks print an overdrawn balance as its magnitude — SBI shows −₹78,628.35 as "78628.35" — so a
    printed balance equal to |expected| while expected is negative reconciles, and the SIGNED value is
    carried forward, or the next link would break on the bank's formatting rather than on data.
    """
    breaks = []
    for acct, rs in _by_account().items():
        bal = [r for r in rs if r[5] is not None]
        carried = None
        for prev, cur in zip(bal, bal[1:]):
            base = carried if carried is not None else prev[5]
            exp = base + (cur[3] if cur[4] == "credit" else -cur[3])
            if exp == cur[5]:
                carried = None
            elif exp < 0 and -exp == cur[5]:
                carried = exp                       # overdrawn, printed unsigned
            else:
                breaks.append((acct, prev, cur, cur[5] - exp))
                carried = None
    return breaks


def test_balance_chain_has_no_unexplained_break():
    if not _have_store():
        return
    bad = [b for b in balance_chain_breaks() if _days(b[1][2], b[2][2]) < MISSING_STATEMENT_DAYS]
    assert not bad, "rows lost or misread (balance chain broken inside a statement period):\n" + \
        "\n".join(f"  {a}: {p[2]} → {c[2]} off by ₹{off / 100:,.2f}  row {c[0]} | {c[7][:60]}"
                  for a, p, c, off in bad)


def test_an_account_that_prints_balances_has_one_on_every_row():
    """A balance-less row in a balance-printing account came from somewhere else — a card statement
    filed under the bank, which is exactly how ₹5,000 of RBL card spend ended up counted as SBI."""
    if not _have_store():
        return
    bad = []
    for acct, rs in _by_account().items():
        with_bal = sum(1 for r in rs if r[5] is not None)
        if with_bal > len(rs) * 0.9:                # this account prints a running balance
            bad += [(acct, r) for r in rs if r[5] is None]
    assert not bad, "rows that do not belong to the account they are filed under:\n" + \
        "\n".join(f"  {a}: row {r[0]} {r[2]} ₹{r[3] / 100:,.2f} stmt {r[6]} | {r[7][:50]}"
                  for a, r in bad)


def test_every_account_label_names_its_last_digits():
    """A bare "SBI" or "RBL" label means account detection failed and the rows are unattributed."""
    if not _have_store():
        return
    bad = sorted({r[1] for r in _rows() if not re.search(r"••\s*\d{2,4}$", r[1] or "")})
    assert not bad, f"accounts with no identifying digits: {bad}"


def test_no_row_sits_a_year_away_from_the_rest_of_its_account():
    """A reward or EMI table parsed as transactions lands years off — the 2018 rows on a 2026 card."""
    if not _have_store():
        return
    bad = []
    for acct, rs in _by_account().items():
        ds = sorted(r[2] for r in rs if r[2])
        for i, d in enumerate(ds):
            near = min((abs(_days(d, ds[j])) for j in (i - 1, i + 1) if 0 <= j < len(ds)),
                       default=0)
            if len(ds) > 1 and near > 365:
                bad.append((acct, d))
    assert not bad, f"isolated rows (likely a non-transaction table parsed as rows): {bad}"


#: A statement's own summary lines. Parsed as transactions they book the whole balance as one movement
#: — the Bank of Baroda misparse turned "Opening Balance 10,00,000" into a ₹10L transaction.
_SUMMARY_LINE = re.compile(
    r"(?i)^\s*(opening|closing)\s+balance\b|^\s*balance\s+(b/?f|c/?f|brought|carried)\b|"
    r"^\s*(grand\s+)?total\b|^\s*total\s+(premium|amount|due|debits?|credits?)\b")


def test_no_statement_summary_line_is_stored_as_a_transaction():
    if not _have_store():
        return
    bad = [r for r in _rows() if _SUMMARY_LINE.search(r[7] or "")]
    assert not bad, "summary lines stored as transactions:\n" + \
        "\n".join(f"  {r[1]}: row {r[0]} {r[2]} ₹{r[3] / 100:,.2f} | {r[7][:50]}" for r in bad)


def test_no_bank_reference_is_stored_twice():
    """One UPI/IMPS/NEFT reference is one movement of money; two rows for it double-count."""
    if not _have_store():
        return
    seen = defaultdict(list)
    for r in _rows():
        m = re.match(r"(?:UPI|IMPS|NEFT|RTGS)/(?:(?:DR|CR)/)?(\d{9,})/", r[7] or "")
        if m:
            seen[(r[1], m.group(1), r[4], r[3])].append(r[0])
    dups = {k: v for k, v in seen.items() if len(v) > 1}
    assert not dups, f"bank references stored more than once: {dups}"


def test_no_movement_of_money_is_stored_by_two_statements():
    """Statement periods do not overlap, so one (date, amount, direction) belongs to ONE statement.

    The same movement under two statements means a statement was imported twice under different
    names (HDFC: 399 duplicate rows, spend doubled), or a non-transaction table that repeats across
    statements was parsed as a purchase (ICICI: an EMI schedule line booked in two months).
    """
    if not _have_store():
        return
    db = sqlite3.connect(str(STORE))
    where = defaultdict(set)
    for acct, sid, d, m, dr in db.execute(
            "SELECT account, statement_id, iso_date, minor, direction FROM txns WHERE provisional=0"):
        where[(acct, d, m, dr)].add(sid)
    shared = defaultdict(int)
    for (acct, *_), sids in where.items():
        if len(sids) > 1:
            shared[(acct, tuple(sorted(sids)))] += 1
    assert not shared, "movements stored under more than one statement (account, statements: n):\n" + \
        "\n".join(f"  {a} {s}: {n}" for (a, s), n in sorted(shared.items(), key=lambda kv: -kv[1]))


# --------------------------------------------------------------------------------------- DISPLAY

def _shipped_compute_js() -> str:
    """The dashboard's own `sa` + `compute`, cut from the page it ships — not a copy."""
    # compute() lives in web/src/core.js now (moved verbatim from the plain-CSS page)
    src = (Path(__file__).resolve().parent.parent / "web" / "src" / "core.js").read_text(encoding="utf-8")
    start = src.index("const sa=")
    end = src.index("/* ---- period control ----", start)
    return src[start:end]


def _browser_compute(rows):
    node = shutil.which("node")
    if not node:
        return None
    prog = _shipped_compute_js() + (
        "\nlet s='';process.stdin.on('data',c=>s+=c).on('end',()=>{"
        "const R=compute(JSON.parse(s));"
        "const sum=a=>a.reduce((x,y)=>x+y,0),vals=o=>Object.values(o);"
        "console.log(JSON.stringify({inn:R.inn,out:R.out,inv:R.inv,invIn:R.invIn,invBack:R.invBack,"
        "srcs:sum(R.srcs.map(r=>r.a)),invs:sum(R.invs.map(r=>r.a)),cats:R.catTotal,"
        "moIn:sum(vals(R.moIn)),moOut:sum(vals(R.moOut)),moInv:sum(vals(R.moInv)),"
        "count:R.count}));});")
    res = subprocess.run([node, "-e", prog], input=json.dumps(rows), capture_output=True,
                         text=True, timeout=60)
    assert res.returncode == 0, res.stderr
    return json.loads(res.stdout)


def _datasets():
    from statementlens.app import App
    app = App(db_path=str(STORE))
    return [(a["account"], app.dataset(a["account"])) for a in app.repo.accounts()]


def test_browser_totals_equal_server_totals():
    """The hero is computed in the browser; insights and the API use the server's cash_flow. Two
    implementations of one rule drift — the ₹8.33L vs ₹4.13L bill-payment bug was exactly that."""
    if not (_have_store() and shutil.which("node")):
        return
    bad = []
    for acct, ds in _datasets():
        r, f = _browser_compute(ds["txns"]), ds["flow"]
        for js, py in (("inn", "incoming"), ("out", "spends"), ("inv", "investments")):
            if r[js] != f[py]:
                bad.append(f"{acct}: browser {js}={r[js] / 100:,.2f} vs server {py}={f[py] / 100:,.2f}")
        if r["invBack"] != f["redeemed"]:
            bad.append(f"{acct}: browser redeemed={r['invBack'] / 100:,.2f} "
                       f"vs server {f['redeemed'] / 100:,.2f}")
    assert not bad, "server and browser disagree:\n  " + "\n  ".join(bad)


def test_every_breakdown_sums_to_the_headline_it_explains():
    """Each breakdown card sits beside a headline; if its parts do not add up to it, one is wrong."""
    if not (_have_store() and shutil.which("node")):
        return
    bad = []
    for acct, ds in _datasets():
        r = _browser_compute(ds["txns"])
        checks = [
            ("income sources", r["srcs"], r["inn"]),
            ("investment holdings", r["invs"], r["inv"]),
            ("categories (spend + invested)", r["cats"], r["out"] + r["inv"]),
            ("monthly money-in bars", r["moIn"], r["inn"]),
            ("monthly money-out bars", r["moOut"], r["out"]),
            ("monthly invested bars", r["moInv"], r["inv"]),
            ("invested = in − back", r["invIn"] - r["invBack"], r["inv"]),
            ("every row sent is counted", r["count"], len(ds["txns"])),
        ]
        bad += [f"{acct}: {name} = {got / 100 if 'row' not in name else got:,} "
                f"but headline = {want / 100 if 'row' not in name else want:,}"
                for name, got, want in checks if got != want]
    assert not bad, "breakdowns that do not add up:\n  " + "\n  ".join(bad)


def test_the_server_person_summary_matches_the_rows_the_screen_nets():
    """`person_nets` and the netting screen (which sums rows by `cp`) must describe the same people."""
    if not _have_store():
        return
    bad = []
    for acct, ds in _datasets():
        by = defaultdict(lambda: [0, 0])
        for r in ds["txns"]:
            if r.get("cp"):
                by[r["cp"]][0 if r["dir"] == "D" else 1] += r["a"]
        for p in ds["person_nets"]:
            got = by.get(p["counterparty"])
            if got is None or (got[0], got[1]) != (p["paid"], p["received"]):
                bad.append(f"{acct} {p['counterparty']}: summary paid/received "
                           f"{p['paid'] / 100:,.0f}/{p['received'] / 100:,.0f} vs rows "
                           f"{(got or [0, 0])[0] / 100:,.0f}/{(got or [0, 0])[1] / 100:,.0f}")
    assert not bad, "person summary disagrees with the rows:\n  " + "\n  ".join(bad[:15])
