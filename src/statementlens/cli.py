"""Command-line interface for statementlens.

    statementlens ingest --account SBI --name "Full Name" --dob 12112000 --mobile 9999999999
    statementlens render --account SBI --out out/sbi.html
    statementlens stats

Hints (name/dob/mobile/card-last4/custom) are used only to DERIVE statement-PDF passwords locally;
they are never stored or transmitted. All data stays on your machine.
"""

from __future__ import annotations

import argparse
import sys
from typing import Any, Dict


def _app_password() -> str:
    """Read the mail app password without it landing in shell history.

    Env var first (for scripts and launchd), otherwise a no-echo prompt. Never a CLI flag: anything
    passed as an argument is visible in `ps` and saved to .bash_history / .zsh_history.
    """
    import getpass
    import os
    pw = os.getenv("STATEMENTLENS_APP_PASSWORD")
    if pw:
        return pw
    return getpass.getpass("Mail app password (not your normal password): ")


def _hints(args) -> Dict[str, Any]:
    h: Dict[str, Any] = {}
    for k in ("name", "dob", "mobile", "card_last4", "rule_text"):
        v = getattr(args, k, None)
        if v:
            h[k] = v
    if getattr(args, "custom", None):
        h["custom"] = args.custom
    return h


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="statementlens",
                                description="Local-first personal-finance engine from bank/card statements.")
    p.add_argument("--db", help="SQLite path (default ~/.statementlens/store.db)")
    sub = p.add_subparsers(dest="cmd", required=True)

    ing = sub.add_parser("ingest", help="fetch statements (folder or Gmail), parse, categorize, store")
    ing.add_argument("--account", required=True)
    ing.add_argument("--folder", nargs="*",
                     help="read PDFs from local folder(s) instead of Gmail (no OAuth needed)")
    ing.add_argument("--email", help="fetch over IMAP with an app password (any mail provider)")
    ing.add_argument("--imap-host", dest="imap_host", help="override the IMAP host")
    ing.add_argument("--no-recursive", action="store_true", help="with --folder: don't descend")
    ing.add_argument("--pattern", help="with --folder: filename filter, e.g. sbi")
    ing.add_argument("--name"); ing.add_argument("--dob"); ing.add_argument("--mobile")
    ing.add_argument("--card-last4", dest="card_last4"); ing.add_argument("--rule-text", dest="rule_text")
    ing.add_argument("--custom", nargs="*", help="explicit password(s) to try first")
    ing.add_argument("--limit", type=int, default=100)
    ing.add_argument("--single-account", dest="single_account", action="store_true",
                     help="file everything under --account instead of detecting each statement's own")

    rnd = sub.add_parser("render", help="render the dashboard HTML from stored transactions")
    rnd.add_argument("--account", required=True)
    rnd.add_argument("--out", default="out/dashboard.html")
    rnd.add_argument("--currency", default="INR")

    srv = sub.add_parser("serve", help="open the dashboard in your browser (local only)")
    # Optional: the dashboard has an account switcher, so the flag only picks which one opens first.
    # It used to be required with no switcher in the UI, which meant restarting the server to look at
    # a second account — cards were effectively invisible and went untagged as a result.
    srv.add_argument("--account", help="which account to open first (default: the busiest)")
    srv.add_argument("--port", type=int, default=8770)
    # Off by default: this serves your financial data, and 127.0.0.1 means only this machine can
    # reach it. --phone opts into the local network so an iPhone can install it to the home screen.
    srv.add_argument("--phone", action="store_true",
                     help="also serve on your local network so a phone can open it (prints a QR code)")
    srv.add_argument("--no-open", action="store_true", help="don't auto-open a browser")
    srv.add_argument("--own-name", dest="own_names", nargs="*",
                     help="your name(s) as they appear in narrations, to exclude self-transfers")
    srv.add_argument("--name"); srv.add_argument("--dob"); srv.add_argument("--mobile")
    srv.add_argument("--card-last4", dest="card_last4"); srv.add_argument("--rule-text", dest="rule_text")

    ref = sub.add_parser("refresh", help="check for new statements and record the outcome")
    ref.add_argument("--account", required=True)
    ref.add_argument("--folder", nargs="*", help="refresh from folder(s) instead of Gmail")
    ref.add_argument("--force", action="store_true", help="ignore the minimum interval")
    ref.add_argument("--name"); ref.add_argument("--dob"); ref.add_argument("--mobile")
    ref.add_argument("--card-last4", dest="card_last4"); ref.add_argument("--rule-text", dest="rule_text")

    sub.add_parser("status", help="when did it last sync, and did it work?")
    sub.add_parser("security", help="show where credentials and data are stored")
    dis = sub.add_parser("disconnect", help="forget the stored Gmail token")
    dis.add_argument("--yes", action="store_true", help="don't ask for confirmation")
    rel = sub.add_parser("relabel",
                         help="split a merged account into its real accounts (dry-run by default)")
    rel.add_argument("--apply", action="store_true",
                     help="actually write the changes (default is a preview)")
    sub.add_parser("stats", help="show what's stored")

    rec = sub.add_parser("recategorize",
                         help="re-tag stored rows with the current engine (shows a diff first)")
    rec.add_argument("--apply", action="store_true",
                     help="actually write the changes (default: dry run)")

    args = p.parse_args(argv)
    from .app import App

    if args.cmd == "ingest":
        if args.folder:
            app = App.from_folder(args.folder, db_path=args.db,
                                  recursive=not args.no_recursive, pattern=args.pattern)
            print("scanning:", app._source.describe())
        elif args.email:
            app = App.from_email(args.email, _app_password(), db_path=args.db,
                                 host=args.imap_host)
        else:
            from .adapters.sources.gmail_source import GmailStatementSource
            app = App(db_path=args.db, source=GmailStatementSource())
        r = app.ingest(account=args.account, hints=_hints(args), limit=args.limit,
                       split_accounts=not args.single_account)
        print(f"statements={r.statements} inserted={r.inserted} duplicate={r.duplicate} "
              f"failed={r.failed} skipped={len(r.skipped)}")
        if len(r.accounts) > 1:
            print("  accounts detected (use --single-account to merge them):")
            for label, n in sorted(r.accounts.items(), key=lambda kv: -kv[1]):
                print(f"    {label:24s} {n} transactions")
        for e in r.errors[:10]:
            print("  !", e)
        for s in r.skipped[:10]:
            print(f"  - {s['source']}: {s['message']}")
        if not r.ok:
            # never exit 0 on a silent no-op; onboarding and cron both need to see this
            print("\nNothing was imported. See the reasons above.", file=sys.stderr)
            return 2
        return 0
    if args.cmd == "render":
        app = App(db_path=args.db)
        path = app.render(args.account, args.out, args.currency)
        print("rendered ->", path)
        return 0
    if args.cmd == "serve":
        from .adapters.web.server import serve
        app = App(db_path=args.db, own_names=getattr(args, "own_names", None))
        account = args.account
        if not account:
            # busiest first: the account someone actually uses is the one worth opening on
            known = app.accounts()
            account = known[0]["account"] if known else "Account"
        serve(app, account=account, port=args.port,
              open_browser=not args.no_open, hints=_hints(args),
              host="0.0.0.0" if args.phone else "127.0.0.1", phone=args.phone)
        return 0
    if args.cmd == "refresh":
        if args.folder:
            app = App.from_folder(args.folder, db_path=args.db)
        else:
            from .adapters.sources.gmail_source import GmailStatementSource
            app = App(db_path=args.db, source=GmailStatementSource())
        a = app.refresh(account=args.account, hints=_hints(args), force=args.force)
        print(f"ok={a.ok} inserted={a.inserted} duplicate={a.duplicate} failed={a.failed}")
        if a.reason:
            print(" ", a.reason)
        # non-zero on failure so launchd/cron surfaces a broken connector instead of hiding it
        return 0 if a.ok else 2
    if args.cmd == "status":
        st = App(db_path=args.db).sync_status()
        if st.get("healthy"):
            print(st["label"] + ("  [STALE]" if st.get("stale") else ""))
        else:
            # lead with the problem; the last-success time is context, not the headline
            print(f"LAST SYNC FAILED: {st.get('reason') or 'unknown reason'}", file=sys.stderr)
            print(f"  last successful sync: {st['label']}", file=sys.stderr)
        return 0 if st.get("healthy") else 2
    if args.cmd == "security":
        from .adapters.crypto.secret_store import SecretStore
        from .adapters.sources.gmail_source import GmailStatementSource
        store = SecretStore()
        where = store.describe()
        app = App(db_path=args.db)
        print("StatementLens security posture\n")
        print(f"  credentials    {where.backend}"
              + ("  (encrypted by the OS)" if where.secure else "  ** NOT ENCRYPTED **"))
        if where.detail:
            print(f"                 {where.detail}")
        print(f"  gmail token    {'stored' if store.get(GmailStatementSource.TOKEN_KEY) else 'not connected'}")
        print(f"  transactions   {app.repo.path}")
        print("  network        none — statements are read locally and never uploaded")
        print("  passwords      derived in memory only; never written to disk or logs")
        return 0 if where.secure else 2
    if args.cmd == "disconnect":
        from .adapters.crypto.secret_store import SecretStore
        from .adapters.sources.gmail_source import GmailStatementSource
        if not args.yes:
            reply = input("Forget the stored Gmail token? Your transactions stay. [y/N] ")
            if reply.strip().lower() not in ("y", "yes"):
                print("cancelled")
                return 1
        SecretStore().delete(GmailStatementSource.TOKEN_KEY)
        print("Gmail token removed. Run `statementlens serve` to reconnect.")
        return 0
    if args.cmd == "relabel":
        # Existing stores may hold several accounts under one label, because a single --account flag
        # was applied to a whole folder. This re-derives each statement's own account from its
        # filename. DRY RUN by default: it rewrites rows in the user's financial store, so nothing
        # happens without --apply, and --apply takes a backup first.
        from .usecases.account_id import account_label
        app = App(db_path=args.db)
        plan = app.relabel_plan()
        if not plan:
            print("nothing to relabel — every statement already carries its own account")
            return 0
        print(f"{len(plan)} statement(s) would move:")
        totals: Dict[str, int] = {}
        for old, new, n in plan:
            totals[new] = totals.get(new, 0) + n
        for label, n in sorted(totals.items(), key=lambda kv: -kv[1]):
            print(f"    {label:24s} {n} transactions")
        if not args.apply:
            print("\npreview only — re-run with --apply to write it (a backup is taken first)")
            return 0
        backup = app.relabel_apply()
        print(f"\napplied. backup written to {backup}")
        return 0
    if args.cmd == "stats":
        app = App(db_path=args.db)
        print(app.stats())
        return 0
    if args.cmd == "recategorize":
        app = App(db_path=args.db, own_names=getattr(args, "own_names", None))
        r = app.recategorize(dry_run=not args.apply)
        print(f"examined {r['examined']} rows · {r['changed']} would change"
              if r["dry_run"] else
              f"examined {r['examined']} rows · {r['changed']} updated")
        for m in r["moves"]:
            print(f"   {m['count']:5}  {m['from'] or '(blank)'} -> {m['to']}")
        if r["dry_run"] and r["changed"]:
            print("\nnothing written. re-run with --apply to commit (a backup is taken first).")
        elif r.get("backup"):
            print(f"\nbackup: {r['backup']}")
        return 0
    return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
