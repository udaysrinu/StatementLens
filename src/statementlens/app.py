"""Composition root — wires adapters into use-cases (the only place that knows concrete classes).

Everything else in the package depends on ports/domain; App is where the hexagon is assembled.
Swap an adapter here (e.g. a folder source instead of Gmail) without touching any use-case.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .adapters.categorize.keyword_categorizer import KeywordCategorizer
from .adapters.crypto.pdf_decryptor import PdfDecryptor, PdfTextExtractor
from .adapters.parsers.bank_parser import SavingsStatementParser
from .adapters.parsers.card_parser import CardStatementParser
from .adapters.parsers.position_parser import parse_position
from .adapters.parsers.registry import ParserRegistry
from .adapters.persistence.sqlite_repo import SqliteTransactionRepository
from .adapters.render.app_shell import AppShellRenderer
from .usecases.analytics import build_dataset
from .usecases.ingest import IngestResult, IngestStatements


class App:
    @classmethod
    def from_folder(cls, folders, *, db_path: Optional[str] = None,
                    recursive: bool = True, pattern: Optional[str] = None) -> "App":
        """Wire the app to read statements from local folders — no Gmail, no OAuth, no approval gate.

        This is the ungated onboarding path: `gmail.readonly` is a Google *restricted* scope, so the
        Gmail adapter is capped at 100 users until a CASA assessment passes. Folder/upload import has
        no such limit and works for any bank in any country.
        """
        from .adapters.sources.folder_source import FolderStatementSource
        return cls(db_path=db_path,
                   source=FolderStatementSource(folders, recursive=recursive, pattern=pattern))

    @classmethod
    def from_email(cls, address: str, app_password: str, *, db_path: Optional[str] = None,
                   host: Optional[str] = None, months: int = 24,
                   own_names: Optional[list] = None) -> "App":
        """Wire the app to read statements over IMAP with an app-specific password.

        Works with any provider (Gmail, Outlook, Yahoo, Zoho, corporate) and needs no Google Cloud
        project, no OAuth client and no restricted-scope review — so unlike the Gmail adapter it has
        no 100-user cap.
        """
        from .adapters.sources.imap_source import ImapCredentials, ImapStatementSource
        creds = ImapCredentials(address, app_password, host=host)
        return cls(db_path=db_path, own_names=own_names,
                   source=ImapStatementSource(creds, months=months))

    def __init__(self, *, db_path: Optional[str] = None, source=None,
                 own_names: Optional[list] = None):
        # own_names drives self-transfer exclusion: money between the user's own accounts is
        # neither income nor spending, so counting both legs inflates every total
        self.own_names = own_names or []
        self.repo = SqliteTransactionRepository(db_path)
        # the categorizer needs the holder's name too, so self-transfers get their own tag rather
        # than inflating person-to-person spending
        # The sync log lives beside the database so it stays writable if the DB is the problem.
        # Derived from the db FILENAME, not just its folder — `with_name()` alone would give every
        # database in a directory the same log, so two accounts would clobber each other's history.
        from .usecases.refresh import SyncLog
        db = Path(self.repo.path)
        self.sync_log = SyncLog(str(db.with_name(f"{db.stem}.sync.json")))
        self.categorizer = KeywordCategorizer(own_names=self.own_names)
        self.parsers = (ParserRegistry()
                        .register(SavingsStatementParser())
                        .register(CardStatementParser()))
        self.decryptor = PdfDecryptor()
        self.extractor = PdfTextExtractor()
        self._source = source  # inject a StatementSource (e.g. GmailStatementSource) to ingest

    def ingest(self, *, account: str, hints: Dict[str, Any], limit: int = 100,
               split_accounts: bool = True) -> IngestResult:
        if self._source is None:
            raise RuntimeError("no StatementSource configured; pass source= to App(...)")
        self._remember_source()
        return IngestStatements(
            source=self._source, decryptor=self.decryptor, extractor=self.extractor,
            parser_registry=self.parsers, categorizer=self.categorizer,
            repository=self.repo, position_parser=parse_position).run(account=account, hints=hints, limit=limit,
                                      split_accounts=split_accounts)

    # ------------------------------------------------------------------
    # Remembering where statements came from
    #
    # `refresh` needs a source, but `serve` constructs the App with source=None — so the refresh
    # button in the dashboard could only ever answer "nothing to refresh from yet", and the freshness
    # banner had no way to clear. A source that only exists for the life of one CLI invocation cannot
    # back a button that lives in a long-running page.
    #
    # Only folder paths are persisted. A Gmail source needs no memo (its token is already in the
    # keychain and rebuilds itself), and IMAP would mean writing an app password to disk in plaintext,
    # which is not worth a convenience button.
    # ------------------------------------------------------------------

    @property
    def _source_memo(self) -> Path:
        db = Path(self.repo.path)
        return db.with_name(f"{db.stem}.source.json")

    def _remember_source(self) -> None:
        """Record folder sources so a later `serve` can rebuild one for refresh."""
        folders = [str(f) for f in getattr(self._source, "_folders", []) or []]
        if not folders:
            return
        try:
            self._source_memo.parent.mkdir(parents=True, exist_ok=True)
            self._source_memo.write_text(
                json.dumps({"kind": "folder", "folders": folders}), encoding="utf-8")
        except OSError:
            pass          # a memo is a convenience; failing to write one must not fail the import

    def restore_source(self) -> bool:
        """Re-attach a source so `refresh` can run. True when a source is now set.

        Gmail first: a stored OAuth token means the mailbox can be re-read with no user action, which
        is the only source that can genuinely find NEW statements. A folder memo is the fallback —
        re-scanning it picks up files dropped there since the last import.
        """
        if self._source is not None:
            return True

        try:
            from .adapters.crypto.secret_store import SecretStore
            from .adapters.sources.gmail_source import GmailStatementSource
            if SecretStore().get(GmailStatementSource.TOKEN_KEY):
                self._source = GmailStatementSource()
                return True
        except Exception:
            pass          # no token, or the optional Gmail deps are absent — fall through to folders

        try:
            memo = json.loads(self._source_memo.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return False
        folders = [f for f in memo.get("folders", []) if Path(f).exists()]
        if memo.get("kind") != "folder" or not folders:
            return False
        from .adapters.sources.folder_source import FolderStatementSource
        self._source = FolderStatementSource(folders)
        return True

    # Display preferences live in a memo beside the DB, like the source memo: they must survive a
    # restart (the dashboard is relaunched far more often than it is configured), and they are not
    # transaction data, so they do not belong in the store's tables.
    @property
    def _prefs_path(self) -> Path:
        db = Path(self.repo.path)
        return db.with_name(f"{db.stem}.prefs.json")

    def prefs(self) -> Dict[str, Any]:
        try:
            return json.loads(self._prefs_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def set_owner(self, name: str) -> None:
        """Remember whose dashboard this is, for the band's label ("Asha's balance")."""
        prefs = self.prefs()
        prefs["owner"] = name.strip()
        self._prefs_path.write_text(json.dumps(prefs), encoding="utf-8")

    def set_net_with(self, names: List[str]) -> None:
        """Remember names to net as ONE counterparty each (e.g. a family surname)."""
        prefs = self.prefs()
        prefs["net_with"] = [n.strip() for n in names if n and n.strip()]
        self._prefs_path.write_text(json.dumps(prefs), encoding="utf-8")

    def dataset(self, account: str, currency: str = "INR") -> Dict[str, Any]:
        txns = self.repo.all(account)
        # user corrections are loaded from the DB, so a fixed tag survives restarts and re-ingests
        ds = build_dataset(txns, account=account, currency=currency,
                           tags=self.repo.load_tags(), own_names=self.own_names,
                           sync=self.sync_log.status(), splits=self.repo.load_splits(),
                           accounts=self.repo.accounts(),
                           net_with=self.prefs().get("net_with"))
        # loans and deposits sit beside the cash flow, never inside it
        ds["meta"]["positions"] = getattr(self.repo, "positions", list)()
        # each monthly NPS value, for its history; only the figures the chart needs travel to the page
        ds["meta"]["nps_history"] = [{"as_of": p["as_of"], "value": p["value"], "contributed": p["contributed"],
                                      "label": p["label"]} for p in getattr(self.repo, "position_history", lambda k: [])("nps")]
        ds["meta"]["owner"] = self.prefs().get("owner")
        # live payments a statement covering their date did not confirm (failed, reversed)
        ds["meta"]["unsettled"] = getattr(self.repo, "unsettled", lambda a=None: [])(account)
        return ds

    def correct_tag(self, *, tag: str, merchant: Optional[str] = None,
                    content_hash: Optional[str] = None) -> None:
        """Persist a user tag correction (merchant-wide, or a single transaction)."""
        self.repo.correct_tag(tag=tag, merchant=merchant, content_hash=content_hash)

    def set_note(self, content_hash: str, note: str) -> None:
        """Persist a free-text note on one transaction."""
        self.repo.set_note(content_hash, note)

    def set_split(self, content_hash: str, mine_minor: int, with_whom: str = "") -> None:
        """Mark a shared charge: `mine_minor` is the user's own share of the billed amount."""
        self.repo.set_split(content_hash, mine_minor, with_whom)

    def clear_split(self, content_hash: str) -> None:
        self.repo.clear_split(content_hash)

    def accounts(self):
        """Every account in the store, busiest first — powers the dashboard switcher."""
        return self.repo.accounts()

    def similar_to(self, account: str, content_hash: str) -> Optional[Dict[str, Any]]:
        """Transactions that look like the same merchant as `content_hash`, for bulk retagging."""
        from .usecases.similar import find_similar
        txns = self.repo.all(account)
        target = next((t for t in txns if t.source_ref == content_hash), None)
        if target is None:
            return None
        group = find_similar(target, txns)
        return group.as_dict() if group else None

    def correct_many(self, *, tag: str, content_hashes) -> int:
        """Apply one tag to an explicit list of transactions (the multi-select path)."""
        return self.repo.correct_many(tag=tag, content_hashes=content_hashes)

    def tag_conflicts(self, account: str) -> list:
        """Merchant groups whose rows currently carry different tags — the best fixes available."""
        from .usecases.similar import disagreeing_groups
        return [g.as_dict() for g in disagreeing_groups(self.repo.all(account))]

    def render(self, account: str, out_path: str, currency: str = "INR") -> str:
        html = AppShellRenderer().render(self.dataset(account, currency))
        p = Path(out_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(html, encoding="utf-8")
        return str(p.resolve())

    #: opt-in (serve --sms): read bank SMS from macOS Messages before each page is built
    live_sms = False
    _live_at = 0.0

    def refresh_live(self, *, every: float = 60.0) -> Optional[Dict[str, Any]]:
        """Pull new bank SMS into the store before a page is built: at most once a minute, and never
        fatal, so a locked or missing Messages database can only make the page less fresh."""
        import time
        if not self.live_sms or time.time() - self._live_at < every:
            return None
        self._live_at = time.time()
        try:
            from .adapters.sources.sms_source import MacMessagesSource
            return self.ingest_alerts(sources=[MacMessagesSource()])
        except Exception as e:                              # pragma: no cover - environment-specific
            self.live_error = str(e)
            return None

    def ingest_alerts(self, *, sources, currency: str = "INR") -> Dict[str, Any]:
        """Read live alerts (bank SMS, alert emails), store them as provisional rows, reconcile.

        Each alert is routed to an account from the data, never a guess: (1) a label ending in its
        last-4, (2) the account whose settled rows already carry one of that last-4's references
        (an SMS's account digits need not match the label's), (3) the bank's only account.
        Anything unroutable is counted and skipped. Months a statement already covers are reconciled
        at once, so an alert that never settled is set aside instead of counted.
        """
        from .adapters.parsers.alert_parser import parse_alert
        from .domain.models import Statement, Transaction
        from .domain.money import Money
        from .usecases.supersede import coverage_blocks, merge_coverages

        msgs = [m for src in sources for m in src.messages()]
        parsed = [(m, p) for m in msgs for p in [parse_alert(m.body, subject=m.subject)]
                  if p is not None and p.txn_date is not None]
        labels = [a["account"] for a in self.repo.accounts()]
        banks = ("SBI", "HDFC", "ICICI", "RBL", "AXIS", "KOTAK", "SCAPIA", "FEDERAL", "IDFC", "YES")
        bank_of = lambda m: next((b for b in banks if b in f"{m.sender} {m.subject}".upper()), "")

        learned: Dict[tuple, str] = {}
        for m, p in parsed:                                 # (2) learn last-4 -> account from refs
            if p.ref and (bank_of(m), p.account_hint) not in learned:
                row = self.repo._conn.execute(
                    "SELECT account FROM txns WHERE provisional=0 AND description LIKE ? LIMIT 1",
                    (f"%{p.ref}%",)).fetchone()
                if row:
                    learned[(bank_of(m), p.account_hint)] = row[0]

        def route(m, p) -> Optional[str]:
            if p.account_hint:
                hit = [a for a in labels if a.endswith(p.account_hint)]
                if len(hit) == 1:
                    return hit[0]
            if (bank_of(m), p.account_hint) in learned:
                return learned[(bank_of(m), p.account_hint)]
            same = [a for a in labels if bank_of(m) and a.upper().startswith(bank_of(m))]
            return same[0] if len(same) == 1 else None

        # The same swipe often arrives twice (ICICI sends an SMS AND an email). Per (account, date,
        # amount, direction) keep as many as the busiest SINGLE source reported, SMS first because it
        # carries the reference: two genuine ₹20 coffees in one SMS feed stay two.
        from collections import Counter, defaultdict
        groups: Dict[tuple, list] = defaultdict(list)
        unrouted = 0
        for m, p in parsed:
            acct = route(m, p)
            if acct is None:
                unrouted += 1
                continue
            groups[(acct, p.txn_date, p.amount_minor, p.direction)].append((m, p))
        kept = []
        for key, items in groups.items():
            kind = lambda m: "sms" if m.message_id.startswith("sms:") else "email"
            n = max(Counter(kind(m) for m, _ in items).values())
            kept += [(key[0], m, p) for m, p in sorted(items, key=lambda x: kind(x[0]) != "sms")[:n]]

        by_acct: Dict[str, list] = {}
        nth: Counter = Counter()
        for acct, m, p in kept:
            desc = (p.merchant or "alert") + (f" · Ref {p.ref}" if p.ref else "")
            # Two genuinely identical alerts (same day, amount, payee, no ref) would hash to ONE row and
            # silently lose a real payment, so the second gets an ordinal. Stable across runs because the
            # message order is. ponytail: ordinal-by-order, a per-message time would be sturdier.
            k = nth[(acct, p.txn_date, p.amount_minor, p.direction, desc)]
            nth[(acct, p.txn_date, p.amount_minor, p.direction, desc)] += 1
            by_acct.setdefault(acct, []).append(Transaction(
                txn_date=p.txn_date,
                # the reference rides in the description: it is the key that pairs this row with its
                # statement line later, and it is what the bank prints there too
                description=desc,
                amount=Money(p.amount_minor, currency), direction=p.direction, merchant=p.merchant,
                raw_date=p.txn_date.isoformat() + (f" #{k + 1}" if k else ""),
                source_ref=f"alert:{m.message_id}", provisional=True))

        out = {"messages": len(msgs), "parsed": len(parsed), "unrouted": unrouted, "accounts": {}}
        for acct, txns in by_acct.items():
            # the messages read are the truth for their window: rebuild it, never append to it
            self.repo.clear_provisional_since(acct, min(t.txn_date for t in txns).isoformat())
            tagged = tuple(t.with_category(self.categorizer.categorize(t)) for t in txns)
            counts = self.repo.save_statement(Statement(acct, "alerts", "transaction alerts", "live", tagged))
            settled = [t for t in self.repo.all(acct) if not t.provisional]
            ranges = merge_coverages(coverage_blocks(settled, acct)).get(acct, [])
            rec = self.repo.reconcile_provisional(acct, ranges)
            live = sum(1 for t in self.repo.all(acct) if t.provisional)
            out["accounts"][acct] = {"alerts": len(txns), "new": counts["inserted"],
                                     "confirmed_by_statement": rec["matched"],
                                     "never_settled": rec["unsettled"], "live_now": live}
        return out

    def relabel_plan(self):
        """[(old_label, new_label, row_count)] for statements whose account can be derived.

        A preview, so the user sees what a migration of their own financial store would do before any
        row is written.
        """
        from .usecases.account_id import account_label
        out = []
        for sid, sname, acct, n in self.repo.statement_rows():
            label = account_label(sname, "", fallback=acct)
            if label != acct:
                out.append((acct, label, n))
        return out

    def relabel_apply(self) -> str:
        """Apply the plan after backing the database up. Returns the backup path."""
        from .usecases.account_id import account_label
        return self.repo.relabel_accounts(account_label)

    def stats(self) -> Dict[str, Any]:
        return self.repo.stats()

    def recategorize(self, *, dry_run: bool = True) -> Dict[str, Any]:
        """Re-derive stored categories with the CURRENT engine. Dry run unless told otherwise.

        Needed because categories are written at ingest, so every categorizer improvement previously
        applied only to statements imported after it. User corrections are applied at read time and are
        never touched by this.
        """
        return self.repo.recategorize(self.categorizer, dry_run=dry_run)

    def refresh(self, *, account: str, hints: Dict[str, Any], force: bool = False,
                limit: int = 100):
        """Re-run ingest and record the outcome so a broken connector is visible, not silent."""
        from .usecases.refresh import RefreshStatements
        return RefreshStatements(
            lambda: self.ingest(account=account, hints=hints, limit=limit),
            log=self.sync_log).run(force=force)

    def sync_status(self) -> Dict[str, Any]:
        """Freshness for the UI — "updated 36 mins ago", or why it hasn't."""
        return self.sync_log.status()
