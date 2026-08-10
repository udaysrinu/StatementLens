# StatementLens

**A local-first personal-finance engine.** Point it at your bank & credit-card statement emails and
it reads them, categorizes every transaction, and renders a calm, CRED-Money-style dashboard —
**fully offline, on your machine, no cloud, no account-aggregator licence.**

> Your statements, your data. Nothing is uploaded. Passwords are derived locally and never stored.

---

## Why

India's affluent have ~200 transactions/month scattered across banks and cards. CRED Money solved
this with the RBI Account Aggregator framework — which needs a regulated licence. **StatementLens
reaches the same "understand my money" outcome from the statements you already receive by email**,
so anyone can run it.

## What it does

- **Reads statements from Gmail** (read-only) — PDF attachments from Indian banks/cards.
- **Unlocks password-protected PDFs** by *deriving* the password from the rule the bank states in
  its email (e.g. SBI "last 5 of mobile + DOB DDMMYY", RBL "first 4 of name CAPS + DDMMYY").
- **Parses** savings/current and credit-card layouts into a clean transaction model.
- **Categorizes** every transaction (keyword strategy; swappable for ML).
- **Surfaces insights** — the crown jewel: duplicate charges, hidden fees, spend spikes vs your own
  baseline, new recurring payments, forgotten refunds, biggest payee. Calm, second-person copy.
- **Renders** a self-contained, offline HTML dashboard — one hero number, insight cards first,
  honest cash-flow, top categories, recurring, and a searchable ledger behind a tap.

## Money math

Every monetary value is an integer number of minor units (paise) inside a `Money` value object —
**never a float.** `0.1 + 0.2` equals `0.3` exactly. The dashboard recomputes in integer paise too.

## Architecture (Ports & Adapters / Hexagonal)

The domain and use-cases depend only on **interfaces** (`domain/ports.py`); concrete Gmail / PDF /
SQLite / HTML implementations are swappable adapters. Add a bank format or a new data source by
writing an adapter — never by editing the core.

```
        ┌────────────────── use-cases ──────────────────┐
        │  IngestStatements · Analytics · Insights       │
        └───────────────┬───────────────┬────────────────┘
                        │ depends on ports (interfaces) │
   ┌────────────────────┴───────────────┴───────────────────────┐
   │ domain:  Money · Transaction · Statement · ports · (no I/O) │
   └────────────────────┬───────────────┬───────────────────────┘
                        │  implemented by adapters              │
   sources/GmailSource · crypto/PdfDecryptor · parsers/{Savings,Card}
   categorize/Keyword · persistence/SqliteRepo · render/AppShell
```

`app.py` is the composition root — the one place that wires adapters into use-cases.

## Install

```bash
pip install -e ".[all]"        # gmail + pdf + ocr extras
# or pick extras: .[gmail] .[pdf] .[ocr] .[dev]
```

## Usage

```bash
# 1) fetch + parse + store (hints derive PDF passwords locally; never stored)
statementlens ingest --account SBI --name "Full Name" --dob 12111998 --mobile 9999912345

# 2) render the dashboard
statementlens render --account SBI --out out/sbi.html && open out/sbi.html

statementlens stats
```

One-time Gmail setup: a Google Cloud project with the Gmail API enabled and OAuth *Desktop*
credentials saved to `~/.statementlens/gmail_client_secret.json`. First run opens a consent screen.

Library use:

```python
from statementlens.app import App
from statementlens.adapters.sources.gmail_source import GmailStatementSource

app = App(source=GmailStatementSource())
app.ingest(account="SBI", hints={"name": "Full Name", "dob": "12111998", "mobile": "9999912345"})
app.render("SBI", "out/sbi.html")
```

## Privacy

- Runs entirely on your machine. Statements are read; nothing is sent anywhere.
- The local store lives in `~/.statementlens/` and is never committed.
- Password hints derive candidates in memory only.

## Development

```bash
pip install -e ".[dev]"
pytest -q
```

## License

MIT — see [LICENSE](LICENSE).
