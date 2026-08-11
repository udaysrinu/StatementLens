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

## Quick start

```bash
statementlens serve --account SBI
```

That's it. It opens in your browser. If you have no data yet you get a setup page — **drop your
statement PDFs on it** and the dashboard appears. Corrections you make (re-tagging a transaction,
adding a note) are saved locally and survive both a reload and a future statement refresh.

The server binds to `127.0.0.1` only and requires a per-run token, so nothing on your network — or
in another browser tab — can reach your transactions.

## Two ways to bring statements in

| | Works for | Setup |
|---|---|---|
| **Drop PDFs / pick a folder** | anyone, any bank, any country | none |
| **Connect Gmail** (read-only) | up to 100 users per OAuth client | a Google client, see below |

Gmail is the convenient path but a gated one: `gmail.readonly` is a Google **restricted scope**, so
an app using it shows an "unverified app" warning and is limited to 100 users until it passes a
[CASA security assessment](https://developers.google.com/workspace/guides/configure-oauth-consent).
Folder import has no such limit, which is why it's the default.

To enable Gmail in your own build: create a Google Cloud project, enable the Gmail API, make
**Desktop** OAuth credentials, then either drop the JSON at
`~/.statementlens/gmail_client_secret.json` or set `STATEMENTLENS_GOOGLE_CLIENT_ID` /
`STATEMENTLENS_GOOGLE_CLIENT_SECRET`. (See `adapters/sources/bundled_client.py` for why shipping an
installed-app client secret is expected rather than a leak.)

## CLI

```bash
# import from a folder — no Google account involved
statementlens ingest --account SBI --folder ~/Documents/Statements \
    --name "Full Name" --dob 12111998 --mobile 9999912345

# or from Gmail
statementlens ingest --account SBI --name "Full Name" --dob 12111998 --mobile 9999912345

statementlens serve  --account SBI          # browse it
statementlens render --account SBI --out out/sbi.html   # static export
statementlens stats
```

Identity hints only ever **derive** statement passwords in memory — they are never stored or sent.
`ingest` exits non-zero and explains itself if nothing was imported, so a broken import can't
masquerade as "no spending".

## Staying up to date

```bash
statementlens refresh --account SBI    # check for new statements
statementlens status                   # "updated 4 hours ago", or why not
```

The dashboard shows when it last synced and offers a refresh button, because a stale dashboard that
looks current is worse than one that admits it. Both commands **exit non-zero on failure**, so a
scheduled run surfaces a broken connector instead of hiding it.

To refresh automatically each morning (macOS):

```bash
cat > ~/Library/LaunchAgents/com.statementlens.refresh.plist <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.statementlens.refresh</string>
  <key>ProgramArguments</key>
  <array><string>/usr/local/bin/statementlens</string><string>refresh</string>
         <string>--account</string><string>SBI</string></array>
  <key>StartCalendarInterval</key><dict><key>Hour</key><integer>9</integer></dict>
  <key>StandardErrorPath</key><string>/tmp/statementlens.err</string>
</dict></plist>
PLIST
launchctl load ~/Library/LaunchAgents/com.statementlens.refresh.plist
```

Refresh is safe to run as often as you like — content-hash dedup makes re-import a no-op, and a
minimum interval stops it from hammering Gmail.

Library use:

```python
from statementlens.app import App

# folder import — no OAuth
app = App.from_folder("~/Documents/Statements")
app.ingest(account="SBI", hints={"name": "Full Name", "dob": "12111998", "mobile": "9999912345"})
app.render("SBI", "out/sbi.html")

# fix a wrong tag; the correction outlives future re-ingests
app.correct_tag(tag="grocery", merchant="Fresh N")
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
