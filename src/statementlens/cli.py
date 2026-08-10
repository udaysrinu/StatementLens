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

    ing = sub.add_parser("ingest", help="fetch statements from Gmail, parse, categorize, store")
    ing.add_argument("--account", required=True)
    ing.add_argument("--name"); ing.add_argument("--dob"); ing.add_argument("--mobile")
    ing.add_argument("--card-last4", dest="card_last4"); ing.add_argument("--rule-text", dest="rule_text")
    ing.add_argument("--custom", nargs="*", help="explicit password(s) to try first")
    ing.add_argument("--limit", type=int, default=100)

    rnd = sub.add_parser("render", help="render the dashboard HTML from stored transactions")
    rnd.add_argument("--account", required=True)
    rnd.add_argument("--out", default="out/dashboard.html")
    rnd.add_argument("--currency", default="INR")

    sub.add_parser("stats", help="show what's stored")

    args = p.parse_args(argv)
    from .app import App

    if args.cmd == "ingest":
        from .adapters.sources.gmail_source import GmailStatementSource
        app = App(db_path=args.db, source=GmailStatementSource())
        r = app.ingest(account=args.account, hints=_hints(args), limit=args.limit)
        print(f"statements={r.statements} inserted={r.inserted} duplicate={r.duplicate} failed={r.failed}")
        for e in r.errors[:10]:
            print("  !", e)
        return 0
    if args.cmd == "render":
        app = App(db_path=args.db)
        path = app.render(args.account, args.out, args.currency)
        print("rendered ->", path)
        return 0
    if args.cmd == "stats":
        app = App(db_path=args.db)
        print(app.stats())
        return 0
    return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
