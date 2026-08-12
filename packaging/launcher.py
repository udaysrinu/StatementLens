"""Double-click entry point for the packaged app.

Someone who downloads a binary has no terminal, no flags and no database yet. They should get a
browser tab, not a usage message. So this launcher:

  * picks the account with the most transactions, or drops into onboarding when the store is empty;
  * finds a free port instead of failing when 8770 is taken;
  * keeps the console window open on error, because a packaged app that vanishes on a traceback gives
    the user nothing to report.

`statementlens` the CLI is still the full interface — this is only the zero-argument path.
"""

from __future__ import annotations

import socket
import sys
import traceback


def _free_port(preferred: int = 8770) -> int:
    for port in (preferred, 0):
        try:
            with socket.socket() as s:
                s.bind(("127.0.0.1", port))
                return s.getsockname()[1]
        except OSError:
            continue
    return preferred


def _busiest_account(app) -> str:
    """The account with the most rows, so the first screen is the interesting one."""
    rows = app.repo._conn.execute(
        "SELECT account, COUNT(*) c FROM txns GROUP BY account ORDER BY c DESC LIMIT 1").fetchone()
    return rows[0] if rows else "My account"


def main() -> int:
    # PyInstaller buffers stdout, so a double-clicking user would never see the URL (and would have
    # no way to reach the dashboard if the browser failed to open). Flush eagerly.
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except Exception:
        pass
    from statementlens.app import App
    from statementlens.adapters.web.server import serve

    app = App()
    account = _busiest_account(app)
    port = _free_port()
    print(f"StatementLens — account: {account}")
    # open_browser=True: a double-clicked app must land the user somewhere visible
    serve(app, account=account, port=port, open_browser=True)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception:
        traceback.print_exc()
        # a packaged app closes its window instantly on exit; hold it so the error is readable
        try:
            input("\nSomething went wrong. Press Enter to close…")
        except EOFError:
            pass
        sys.exit(1)
