# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users
Two audiences, weighted equally (confirmed):
- **The owner** — an Indian salaried professional with several bank accounts and credit cards, using
  it on his own real statements to answer "how am I doing, where did it go, what did I miss".
- **Self-hosters** — anyone who clones the public repo and points it at their own mailbox or a folder
  of statement PDFs, arriving cold with banks the owner does not use.

Every screen must work for both: driven by real multi-account data, but legible to a first-time user.

## Product Purpose
Reads bank and credit-card statements the user already receives by email (or from a folder),
parses and categorises them locally, and shows one honest picture of money in, money out and money
invested, across every account and as many years as statements exist. Success is an answer the user
trusts without re-checking against the bank.

## Positioning
Reaches the outcome CRED Money reaches, without the RBI Account Aggregator licence that CRED Money
depends on: it works from statement PDFs, so it covers credit cards alongside bank accounts, keeps
full multi-year history instead of a rolling window, and never sends data off the machine.

## Operating Context
- Runs as a local Python server (`statementlens serve`) opened in a browser on the same machine, behind
  a per-launch token; an optional `--phone` mode serves it on the LAN.
- Viewed on **both phone and desktop, adaptively** (confirmed): a phone layout at CRED Money's scale,
  and a genuinely wider layout on desktop rather than a centred phone column.
- Data arrives in monthly/quarterly statement cycles, plus loan statements and deposit advices that
  are positions, not transactions.

## Capabilities and Constraints
- Accounts: savings accounts and credit cards (SBI, HDFC, ICICI, RBL, Bank of Baroda and Scapia formats are
  supported); loan statements and fixed-deposit advices are read as positions, not transactions.
- Views today: home hero + insights, money in / out / invested with per-period breakdowns, spends by
  tag, merchants, recurring payments, cancelled-pair and per-person netting, card bill cycles,
  transaction detail with tag correction, notes and splits.
- The whole UI is one HTML/CSS/JS document generated from Python (`adapters/render/app_shell.py`),
  served by the stdlib; no frontend build step.
- Money is integer paise end to end. Totals are recomputed in the browser and must equal the server's
  (a parity test enforces it), and every breakdown must sum to its headline.
- The repository is public: no real figures, names, account numbers or screenshots of real data may be
  committed. Screenshots use synthetic data (`docs/make_screenshots.py`).

## Brand Commitments
- Name: **StatementLens**.
- The owner has made **CRED Money's features and feel a binding reference** for this interface, and
  judges the current UI against it. CRED's own logos, marks and proprietary assets are not used;
  CRED's open-source design system **NeoPOP** (Apache-2.0, `CRED-CLUB/neopop-web`) may be, with its
  licence notice retained.

## Evidence on Hand
- The owner's real store (local only, never committed): 5 accounts, ~4,600 transactions, 2022→2026.
- 15 CRED Money reference screenshots from the owner's phone:
  `/Volumes/workplace/claude-code/splitwise/Cred money screenshots/` (reference only, never shipped).
- Prior research: `docs/DESIGN_PRINCIPLES.md`, `docs/cred-money-research-spec.json`.
- No testimonials, users, benchmarks or press exist; none may be invented.

## Product Principles
1. **Honest numbers only.** Show what came in, went out and was invested; never invent a "money left".
   A figure shown in two places must be the same figure.
2. **Every number is inspectable.** Anything removed from or added to a total can be opened to the rows
   behind it.
3. **Zero manual work.** Categorisation, netting and account detection are automatic; corrections are
   one tap and stick.
4. **Insight before data.** Surface the one thing the user would miss before the passive totals.
5. **Local and private by construction.** Nothing leaves the machine; passwords are derived in memory.
