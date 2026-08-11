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

    rnd = sub.add_parser("render", help="render the dashboard HTML from stored transactions")
    rnd.add_argument("--account", required=True)
    rnd.add_argument("--out", default="out/dashboard.html")
    rnd.add_argument("--currency", default="INR")

    srv = sub.add_parser("serve", help="open the dashboard in your browser (local only)")
    srv.add_argument("--account", required=True)
    srv.add_argument("--port", type=int, default=8770)
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
    sub.add_parser("stats", help="show what's stored")

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
        r = app.ingest(account=args.account, hints=_hints(args), limit=args.limit)
        print(f"statements={r.statements} inserted={r.inserted} duplicate={r.duplicate} "
              f"failed={r.failed} skipped={len(r.skipped)}")
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
        serve(app, account=args.account, port=args.port,
              open_browser=not args.no_open, hints=_hints(args))
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
    if args.cmd == "stats":
        app = App(db_path=args.db)
        print(app.stats())
        return 0
    return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
