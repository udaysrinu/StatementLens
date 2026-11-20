# StatementLens architecture

StatementLens reads the bank, card, loan, deposit and pension documents you already receive (by email,
in a folder, or as bank SMS on a Mac), parses them on your machine, and serves one dashboard from a local
server. Nothing is sent anywhere. This document describes how the app works; it contains no real data.

Diagrams are Mermaid source, rendered by GitHub; the same diagrams are in [`docs/architecture/`](architecture/)
as SVG files. Node labels use the real module and function names, so a rename shows up here as a stale
label in review.

Reading order for an engineer: sections 1 and 2 for the shape, 10 for what runs where, 11 for the shared
Gmail/PDF layer, then 3 to 6 for the data path, and 7 for how every number is computed.

## 1. Context

```mermaid
flowchart LR
  you(["<b>You</b><br/>one browser, on this machine<br/>(or your phone on the LAN with --phone)"])
  sl["<b>StatementLens</b><br/>parse, reconcile, store,<br/>serve one dashboard"]
  gmail[("<b>Gmail</b><br/>statement PDFs, FD advices,<br/>NPS statements")]
  folder[("<b>A folder of PDFs</b><br/>for anyone not using Gmail")]
  imap[("<b>Any IMAP mailbox</b><br/>app password")]
  sms[("<b>macOS Messages</b><br/>bank SMS forwarded<br/>from the iPhone")]
  kc[("<b>OS keychain</b><br/>the Gmail OAuth token")]
  you -- "opens http://127.0.0.1 with a per-launch token" --> sl
  gmail -- "read-only Gmail API" --> sl
  imap -- "read-only IMAP" --> sl
  folder -- "reads files" --> sl
  sms -- "reads chat.db read-only" --> sl
  sl -- "stores / reads" --> kc
```

## 2. Containers

```mermaid
flowchart LR
  subgraph sources["Sources · adapters/sources"]
    G["<b>GmailStatementSource</b><br/>gmail_source.py"]
    F["<b>FolderStatementSource</b><br/>folder_source.py"]
    I["<b>ImapStatementSource</b><br/>imap_source.py"]
    S["<b>MacMessagesSource</b><br/>sms_source.py"]
    A["<b>GmailAlertSource · ImapAlertSource</b><br/>alert_email_source.py"]
  end
  D["<b>PdfDecryptor · PdfTextExtractor</b><br/>adapters/crypto<br/>password_rules.candidates()"]
  IN["<b>IngestStatements.run()</b><br/>usecases/ingest.py"]
  subgraph parse["Parsers · adapters/parsers"]
    R["<b>ParserRegistry</b><br/>bank_parser · card_parser"]
    P["<b>parse_position()</b><br/>loan · FD · NPS"]
  end
  L["<b>parse_alert()</b><br/>parsers/alert_parser.py"]
  AL["<b>App.ingest_alerts()</b><br/>app.py · route, dedupe, reconcile"]
  DB[("<b>SQLite store</b><br/>~/.statementlens/store.db")]
  DS["<b>build_dataset()</b><br/>usecases/analytics.py"]
  subgraph web["Serve · adapters/render, adapters/web"]
    RN["<b>AppShellRenderer</b><br/>inlines web_dist, fonts, data"]
    SV["<b>serve()</b><br/>server.py · token · /api/*"]
  end
  UI["<b>Dashboard</b><br/>web/ · React + NeoPOP<br/>core.js holds the logic"]
  G & F & I -- "PDF bytes" --> D -- "text" --> IN
  IN -- "parse(text)" --> R & P
  IN -- "rows, positions" --> DB
  S -- "AlertMessage" --> L -- "AlertTxn" --> AL -- "live rows" --> DB
  A -. "built, not wired in yet" .-> L
  DB --> DS -- "dataset" --> RN --> SV -- "one self-contained page" --> UI
  UI -- "POST corrections" --> SV -- "tags · notes · splits" --> DB
```

| Container | Does | Its data comes from |
|---|---|---|
| Sources | Fetch documents: statement PDFs (Gmail, folder, IMAP) and bank SMS; alert-email readers are built but not called yet | the mailbox, a folder, `chat.db` |
| Unlock | Opens password-protected PDFs by trying candidates derived in memory from your hints (name, date of birth, mobile, card last 4, PAN) | hints passed at run time, never written to disk |
| Parse | Bank and card statements become transactions; loan, FD and NPS documents become positions; alerts become live rows | the unlocked text |
| Use-cases | Ingest with duplicate protection; live alerts routed, de-duplicated and reconciled; the dataset the page needs | the store |
| Store | SQLite: statements, transactions, corrections, positions, unreconciled live rows | written by the use-cases |
| Serve | A stdlib HTTP server on 127.0.0.1 behind a per-launch token; renders the page and takes corrections | the dataset |
| Dashboard | One React app on CRED's NeoPOP components, built once and committed, so installing needs no Node | the page's embedded JSON |

The **Unlock** box, the password rules, the keychain store and the Gmail fetch are generic, so they are
moving into [inboxkit](https://github.com/udaysrinu/inboxkit), a library shared with other apps
(section 11). The switch is on branch `chore/inboxkit`; on this branch StatementLens still carries its
own copies. Loan, FD and NPS parsing moves the same way.

### What lives where

| Place | Holds |
|---|---|
| `store.db` | everything parsed, plus your tag corrections, notes and splits (kept separate so a re-import never undoes them) |
| `store.sync.json` | when the last sync ran and what it skipped |
| `store.prefs.json` | small preferences: who to net with, your name for the header |
| OS keychain | the Gmail OAuth token |
| browser `localStorage` | the theme and the privacy lock, nothing else |

## 3. Ingesting a statement

```mermaid
flowchart TB
  raw["raw document<br/>(bytes + filename)"] --> dec["PdfDecryptor.decrypt()<br/>tries password_rules.candidates(hints)"]
  dec --> ext["PdfTextExtractor.extract()"]
  ext --> pos{"parse_position(text)<br/>a loan, FD or NPS document?"}
  pos -- "yes, and its own sums hold" --> savep[("positions<br/>(label, as_of)")]
  pos -- "yes, but a sum fails:<br/>PositionParseError" --> err["counted as failed,<br/>with the reason"]
  pos -- "no" --> lab["account_label()<br/>which account the file is for"]
  lab --> reg["ParserRegistry.parse()"]
  reg --> seen{"already_ingested()<br/>this filename stored before?"}
  seen -- "yes" --> dup["counted as duplicate"]
  seen -- "no" --> empty{"any rows?"}
  empty -- "no" --> diag["diagnose(): skipped,<br/>with why"]
  empty -- "yes" --> cat["categorize each row"]
  cat --> mv["_drop_stored_movements()<br/>(date, amount, direction) multiset"]
  mv --> save[("txns<br/>content_hash UNIQUE")]
  save --> rec["_supersede() → reconcile_provisional()<br/>per covered month: pair live rows<br/>with statement lines"]
```

A position (loan, deposit, pension) is never booked as transactions: every EMI and every FD funding is
already a debit on the account that paid it, so booking the document as well would count it twice.

## 4. Live rows and reconciliation

```mermaid
flowchart TB
  chat[("chat.db<br/>bank senders only")] --> mm["MacMessagesSource.messages()"]
  mail[("alert emails")] -.-> ga["GmailAlertSource<br/>(built, not wired in yet)"]
  ga -.-> pa
  mm --> pa["parse_alert()<br/>amount · date · direction · last-4 · ref"]
  pa --> route["route to an account:<br/>1 label ends in last-4<br/>2 a stored row carries the ref<br/>3 the bank's only account"]
  route -- "no rule matches" --> unr["counted as unrouted,<br/>skipped, never guessed"]
  route -- "routed" --> dd["one row per swipe across sources<br/>(busiest single source wins, SMS first)"]
  dd --> clear["clear_provisional_since()<br/>rebuild the window, never append"]
  clear --> live[("txns, provisional = 1")]
  live --> stmt{"a statement now<br/>covers the date?"}
  stmt -- "no" --> show["shown with a 'live' tag,<br/>counted in totals"]
  stmt -- "yes" --> pair{"paired by ref,<br/>else date ±2d + amount"}
  pair -- "paired" --> drop["live row removed;<br/>the statement line stands"]
  pair -- "unpaired" --> un[("unsettled<br/>out of every total, listed")]
```

## 5. Serving the dashboard

```mermaid
sequenceDiagram
  participant B as Browser
  participant S as serve() (server.py)
  participant A as App
  participant M as MacMessagesSource
  participant DB as store.db
  B->>S: GET /?t=<token>
  S->>A: refresh_live()  (only with --sms, at most once a minute)
  A->>M: messages()
  M-->>A: bank SMS from the last 45 days
  A->>DB: ingest_alerts(): store live rows, reconcile
  S->>A: dataset(account)
  A->>DB: transactions, accounts, positions, unsettled
  A-->>S: dataset (JSON)
  S->>S: AppShellRenderer.render(): one pass fills fonts, CSS, data, JS
  S-->>B: one self-contained HTML page
  B->>B: core.js computes every total from the rows
  B->>S: POST /api/tag {merchant, tag}  (a correction)
  S->>DB: tag_merchant upsert
```

### The page

```mermaid
flowchart TB
  page["the page<br/>&lt;script id=data&gt; + inline bundle"] --> core["<b>core.js</b><br/>DATA · compute() · rangeFilter()<br/>netFilter() · netWorth() · navigation"]
  core -- "draw() → re-render" --> shell["<b>Shell.jsx</b><br/>band hero · pinned tabs · dock"]
  shell --> secs["one scroll page:<br/>Accounts · Transactions · Recurring · Cash flow"]
  shell --> det["drilled-in screens:<br/>breakdown · category · search · transaction<br/>netting · bills · account"]
  secs & det --> np["NeoPOP components<br/>Button · ElevatedCard · SearchBar"]
```

## 6. The store

```mermaid
erDiagram
  statements ||--o{ txns : "statement_id"
  txns ||--o| tag_txn : "content_hash"
  txns ||--o| txn_note : "content_hash"
  txns ||--o| txn_split : "content_hash"
  statements {
    int id PK
    text account
    text source_id
    text source_name "filename, the duplicate key"
    text period_hint
    int txn_count
  }
  txns {
    int id PK
    text account
    text iso_date
    text description
    text merchant
    int minor "paise"
    text direction "debit | credit"
    int balance_minor "printed running balance"
    text category
    int statement_id FK
    text content_hash UK
    int provisional "1 = live row"
  }
  tag_merchant {
    text merchant_key PK
    text tag
  }
  tag_txn {
    text content_hash PK
    text tag
  }
  txn_note {
    text content_hash PK
    text note
  }
  txn_split {
    text content_hash PK
    int mine_minor
    text with_whom
  }
  unsettled {
    text content_hash PK
    text account
    text iso_date
    int minor
    text direction
    text description
    text noticed_on
  }
  positions {
    text label PK
    text as_of PK
    text kind "loan | deposit | nps"
    text data "JSON snapshot"
  }
```

Corrections (`tag_*`, `txn_note`, `txn_split`) key on `content_hash`, not on `txns.id`, so they survive a
statement being re-imported.

## 7. How the numbers are calculated

| Number | Rule |
|---|---|
| Every amount | integer paise end to end; never a float |
| Money in / out / invested | `compute()` over the period's rows; self-transfers and card bill payments are left out of both sides |
| A breakdown's lines | sum exactly to its headline; small sources fold into "Other (N sources)" |
| "Skip refunded" | drops cancelled pairs (left and came straight back), only when both legs are in the period |
| "Settle up friends" | additionally nets people money moved both ways with; a preference, never the default |
| "My share" | uses your share of split charges; the billed amount itself never changes |
| Total balance | the newest printed running balance of each bank account; cards print none |
| Net worth | bank balances + deposits (principal) + NPS value − loans outstanding, from what is tracked. Moving to Netfolio (section 10); StatementLens will hand it balances |
| NPS | value, contributed and gain as the statement prints them, after checking gain = value − contributed + withdrawn |
| Live rows | counted until a statement covers their date, then replaced by it; unpaired ones leave the totals |

The browser recomputes every total from the rows; a parity test runs the same `compute()` from
`web/src/core.js` against the server's figures.

## 8. Refresh: automatic vs manual

| What | How it refreshes |
|---|---|
| Bank SMS (live rows) | automatic on each page load when served with `--sms` (at most once a minute), or `statementlens alerts --days N` |
| Alert emails | not yet: the readers exist but nothing calls them |
| Statements, FD advices, NPS statements | `statementlens refresh`, the dashboard's "refresh", or `statementlens ingest` |
| A folder of PDFs | `statementlens ingest --folder <path>` |
| Corrections (tags, notes, splits) | saved immediately on each tap |

## 9. Security notes

- The server listens on `127.0.0.1` only (LAN only with `--phone`) and every request needs the per-launch token.
- The page fetches nothing at runtime: code, fonts, icons and data are inline.
- Placeholders in the page template are filled in one pass, so text from a statement can never inject code
  or data into the page.
- Statement passwords are derived in memory from hints and never stored. The Gmail token lives in the OS
  keychain.
- Gmail and IMAP access is read-only; `chat.db` is opened read-only and only bank senders are read.
- The public repository holds no real statements, figures, names or account numbers; screenshots use the
  synthetic demo store.

## 10. What runs where: website, local process, library

One rule decides it: **anything that touches someone's money data or credentials runs on their own
device; anything public and stateless can be a website; shared code is a library, never a service.**

```mermaid
flowchart LR
  subgraph device["<b>Your computer</b> · your data stays here"]
    SL["<b>StatementLens</b><br/>local process on 127.0.0.1<br/>bank + card statements, spending"]
    NF["<b>Netfolio</b><br/>local scripts + a localhost page<br/>what you own and owe, net worth<br/>public code, private data"]
    IK[["<b>inboxkit</b><br/>library inside both:<br/>Gmail fetch, PDF unlock, keychain"]]
    DB[("store.db<br/>+ OS keychain")]
    MSG[("macOS Messages<br/>chat.db")]
    UI["your browser<br/>the self-contained page"]
  end
  subgraph web["<b>Public web</b> · no personal data"]
    SC["<b>sharecase</b><br/>static site: build and share<br/>stock baskets"]
    PX["<b>/api/price</b><br/>stateless serverless proxy<br/>for Yahoo's chart API"]
    DEMO["StatementLens demo<br/>static page, synthetic data<br/>(proposed)"]
  end
  G[("<b>Gmail API</b><br/>read-only OAuth")]
  Y[("<b>Yahoo Finance</b><br/>chart API")]
  SL --- IK
  NF --- IK
  IK -- "HTTPS, your token" --> G
  SL --> DB
  SL -- "reads, read-only" --> MSG
  SL -- "one page, data inline" --> UI
  SL -. "statementlens balances --json<br/>same machine (planned)" .-> NF
  NF -- "tickers only, server-side" --> Y
  SC --> PX -- "tickers only" --> Y
```

| Piece | Runs as | Why there | As a generic product |
|---|---|---|---|
| StatementLens | a local process (Python, stdlib HTTP server on 127.0.0.1) plus a page in your browser | it holds your Gmail token, statement PDFs and every transaction; the bank SMS feed is a file only your Mac can read | an installable desktop app (pip / pipx today; a signed app with its own window later). Same code, same local store |
| The dashboard page | a static bundle (React + NeoPOP), served by the local process with the data inlined | needs no server of its own, so it works offline and fetches nothing | the same bundle can also run as a **website demo** on synthetic data, or on PDFs a visitor drops in, processed in their browser only |
| [inboxkit](https://github.com/udaysrinu/inboxkit) | a Python library, pinned by tag | fetching and unlocking documents is the same job for every app; a library keeps it on the user's machine | stays a library. Making it a hosted service would collect everyone's mail in one place |
| [Netfolio](https://github.com/udaysrinu/netfolio) (public code, private data) | scripts run in order on your machine (contract notes, then the snapshot, the daily series and the page build) plus a localhost-only page server | holdings and trades now, and it will hold PAN-unlocked documents and the identifiers you want in one place (PRAN, policy and FD numbers): the most sensitive data of all | the same desktop pattern as StatementLens; it is to read StatementLens's balances through the CLI (planned) |
| sharecase | a public website (static pages + one serverless function) | building and sharing a basket needs no personal data | stays a website. The private tracking of your own holdings moves to Netfolio |
| /api/price | a stateless serverless function that proxies Yahoo's chart API; quotes cached 60 s, history 1 h | Yahoo sends no CORS header, so a browser page cannot call it directly. Netfolio calls Yahoo itself, server-side, and its local page server runs its own copy of this function, so it never touches the public one | stays a public, stateless service. It sees tickers and an IP address, never holdings or amounts |

Why not one hosted web app with accounts? Three costs, all avoidable by staying local:
- **Custody.** A server holding users' statements and mailbox tokens makes the operator responsible for
  everyone's financial data, under India's data-protection law (the DPDP Act).
- **Google's restricted-scope review.** Gmail read access is a *restricted* scope. Any app used by more
  than 100 people must pass Google's OAuth verification, and an app that moves that data through its own
  servers must also pass a recurring third-party security assessment. Check Google's current policy
  before launch; it changes.
- **Live SMS can't be hosted at all.** Bank SMS arrive on the phone, iOS lets no app read them, and the
  only readable copy is the Messages database on a Mac.

How products talk to each other: through files and commands on the same machine (`statementlens balances
--json`), never through network APIs between them, so there is no login, port or token to protect. If
sync across devices is ever needed, it should be end-to-end encrypted with a key only the user holds, so a
sync server never sees the data.

The phone today: open the dashboard over the home network (`serve --phone`), or carry a static snapshot
(`statementlens render --out file.html`), which is one self-contained file.

### The contract StatementLens offers other apps

`statementlens balances --json` prints each account's latest balance and exits non-zero if an account's
balance chain breaks, so a misread figure never travels silently:

```json
{"generated_at": "2026-11-20T15:30:00+05:30",
 "accounts": [{"account": "Demo Bank ••1234", "institution": "Demo", "kind": "bank",
               "balance_paise": 380000, "as_of": "2026-10-03", "source": "statement",
               "statement_period_to": "2026-10-03"}]}
```

`balance_paise` is signed: banks print an overdraft without its minus sign, so it is read from the
balance chain, not the last printed number. Cards report `null` until their "Total Amount Due" is parsed.

## 11. How inboxkit works

inboxkit is **not** an AI connector and does not go through Claude or any MCP server. It is ordinary
Python that calls Google's Gmail REST API with Google's own client library (`google-api-python-client`),
on your machine, with a token that only your machine holds. "The Gmail connector" in this README means
this optional piece (`pip install "statementlens[gmail]"`).

```mermaid
sequenceDiagram
  participant App as StatementLens (or another app)
  participant GD as GmailDocuments (inboxkit.inbox)
  participant KC as SecretStore (inboxkit.secrets)
  participant G as Gmail API
  participant PDF as PdfDecryptor · PdfTextExtractor
  App->>GD: fetch(query) with app="statementlens"
  GD->>KC: get("gmail_token")  (macOS keychain, service "statementlens")
  alt no token yet
    GD->>G: OAuth consent in your browser, scope gmail.readonly
    G-->>GD: refresh token
    GD->>KC: set("gmail_token")  (over stdin, never on a command line)
  else token expired
    GD->>G: refresh the access token
  end
  loop every page of results (retries on rate limits)
    GD->>G: messages.list(q=query)
    loop each message
      GD->>G: messages.get(format=full)
      G-->>GD: headers + MIME tree
      GD->>G: attachments.get for each .pdf part
    end
  end
  GD-->>App: Document(filename, bytes, headers, labels)
  App->>App: doc.authenticated("bank.example")  (DKIM / DMARC verdict Gmail recorded)
  App->>PDF: decrypt(bytes, hints) tries passwords.candidates(hints)
  PDF-->>App: text
  App->>App: parse: bank/card parser, or inboxkit.positions for loan, FD, NPS
```

| Module | Does | Worth knowing |
|---|---|---|
| `inboxkit.inbox` | `GmailDocuments(query, app=…)` returns the PDF attachments of matching mail as `Document`s | read-only scope; pages through every result; sets `truncated` instead of silently returning less; `skip_ids` makes a daily sync cheap |
| `Document.authenticated(domain)` | proves a mail really came from `domain`, from the verdict Gmail's own server prepended (DKIM, DMARC) | fails closed. Planned for StatementLens's ingest: measured against 182 real statement emails, all pass with one domain per bank |
| `inboxkit.pdf` | unlocks a password-protected PDF, then reads its text | passwords are derived in memory from hints and never stored |
| `inboxkit.passwords` | turns hints (name, date of birth, mobile, card last 4, PAN) or a bank's stated rule ("first 4 letters of your name + DDMM") into candidates | a password you give explicitly is tried first, then the bank's stated rule, then the usual formats |
| `inboxkit.secrets` | small secrets in the OS keychain (macOS, Windows, Linux); a 0600 file only when there is no keychain, and it says so | each app has its own namespace (`service`) |
| `inboxkit.positions` | a loan statement, FD advice or NPS statement becomes a snapshot in paise | checks the document's own sums and refuses one that does not add up |

Who owns what: Google Cloud holds the OAuth *client* (the app's identity). Your keychain holds the
*token* (your consent). The documents and everything parsed from them stay on your disk.

