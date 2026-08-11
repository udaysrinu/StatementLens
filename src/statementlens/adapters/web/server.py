"""Local web server — serves the dashboard and persists user corrections.

Deliberately built on `http.server` from the stdlib: no Flask, no FastAPI, no uvicorn. This is a
single-user local app, so the concurrency ceiling of a threaded stdlib server is irrelevant, and a
zero-dependency server is one less thing to install for someone who just wants to see their
statements. (ponytail: stdlib server; move to ASGI only if this ever becomes multi-user.)

Binds to 127.0.0.1 only — never 0.0.0.0. The dashboard contains full bank transaction history, so it
must not be reachable from the local network.

Endpoints:
    GET  /                      the dashboard (rendered from stored transactions)
    GET  /api/dataset           dataset JSON
    POST /api/tag               {"tag","merchant"|"content_hash"} -> persist a tag correction
    POST /api/note              {"content_hash","note"}           -> persist a note
    POST /api/ingest            {"folder":[...]}                  -> import PDFs from folder(s)
    POST /api/upload            raw PDF body, ?filename=…&name=…  -> import one uploaded PDF
                                (`filename` = the file; `name` = account holder, for passwords)
    POST /api/gmail             run OAuth consent, then import
"""

from __future__ import annotations

import json
import secrets
import tempfile
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlparse

from ..render.app_shell import AppShellRenderer
from .onboarding import render_onboarding

_MAX_UPLOAD_BYTES = 25 * 1024 * 1024   # a statement PDF is well under this; refuse anything larger


class _Handler(BaseHTTPRequestHandler):
    server_version = "statementlens"

    # -- plumbing ----------------------------------------------------------
    @property
    def app(self):
        return self.server.sl_app          # type: ignore[attr-defined]

    @property
    def account(self) -> str:
        return self.server.sl_account      # type: ignore[attr-defined]

    def log_message(self, fmt, *args):     # keep the console clean; this is a desktop app
        pass

    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        # this page holds financial data: never let a browser or proxy cache it
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj: Any, code: int = 200) -> None:
        self._send(code, json.dumps(obj).encode("utf-8"), "application/json; charset=utf-8")

    def _read_json(self) -> Dict[str, Any]:
        n = int(self.headers.get("Content-Length") or 0)
        if n <= 0 or n > _MAX_UPLOAD_BYTES:
            raise ValueError("missing or oversized request body")
        return json.loads(self.rfile.read(n).decode("utf-8"))

    def _authorized(self) -> bool:
        """Single-user token check.

        Any page in the browser can POST to 127.0.0.1, so an unauthenticated local API would let a
        random website rewrite the user's tags. The token is in the URL the app opens.
        """
        want = self.server.sl_token                     # type: ignore[attr-defined]
        got = parse_qs(urlparse(self.path).query).get("t", [""])[0]
        return secrets.compare_digest(got, want)

    # -- routes ------------------------------------------------------------
    def do_GET(self) -> None:                                   # noqa: N802
        route = urlparse(self.path).path
        if not self._authorized():
            return self._send(403, b"forbidden", "text/plain")
        if route == "/":
            # first run (nothing stored yet) -> onboarding instead of an empty dashboard
            if self.app.stats().get("transactions", 0) == 0:
                return self._send(200, self._onboarding().encode("utf-8"),
                                  "text/html; charset=utf-8")
            html = AppShellRenderer().render(self.app.dataset(self.account))
            return self._send(200, html.encode("utf-8"), "text/html; charset=utf-8")
        if route == "/setup":
            return self._send(200, self._onboarding().encode("utf-8"),
                              "text/html; charset=utf-8")
        if route == "/api/dataset":
            return self._json(self.app.dataset(self.account))
        if route == "/api/health":
            return self._json({"ok": True, **self.app.stats()})
        self._send(404, b"not found", "text/plain")

    def do_POST(self) -> None:                                  # noqa: N802
        route = urlparse(self.path).path
        if not self._authorized():
            return self._send(403, b"forbidden", "text/plain")
        try:
            if route == "/api/tag":
                body = self._read_json()
                tag = body.get("tag")
                if not tag:
                    return self._json({"error": "tag required"}, 400)
                self.app.correct_tag(tag=tag, merchant=body.get("merchant"),
                                     content_hash=body.get("content_hash"))
                return self._json({"ok": True})

            if route == "/api/note":
                body = self._read_json()
                ref = body.get("content_hash")
                if not ref:
                    return self._json({"error": "content_hash required"}, 400)
                self.app.set_note(ref, body.get("note", ""))
                return self._json({"ok": True})

            if route == "/api/ingest":
                body = self._read_json()
                folders = body.get("folder") or []
                if not folders:
                    return self._json({"error": "folder required"}, 400)
                r = self.server.sl_ingest(folders, body.get("hints") or {})   # type: ignore
                return self._json(r)

            if route == "/api/upload":
                return self._json(self._handle_upload())

            if route == "/api/refresh":
                r = self.server.sl_refresh()            # type: ignore[attr-defined]
                return self._json(r)

            if route == "/api/gmail":
                body = self._read_json() if int(self.headers.get("Content-Length") or 0) else {}
                r = self.server.sl_gmail(body.get("hints") or {})   # type: ignore[attr-defined]
                return self._json(r)
        except ValueError as e:
            return self._json({"error": str(e)}, 400)
        except Exception as e:                       # a bad request must not kill the server
            return self._json({"error": f"{type(e).__name__}: {e}"}, 500)
        self._send(404, b"not found", "text/plain")

    def _onboarding(self) -> str:
        from ..sources.bundled_client import gmail_available
        return render_onboarding(gmail_available=gmail_available())

    def _handle_upload(self) -> Dict[str, Any]:
        """Accept one PDF as a raw body and ingest it from a temp dir (drag-and-drop path).

        Password-derivation hints come from HEADERS, not the query string: a URL carrying someone's
        date of birth ends up in browser history, in the referrer, and in any proxy log.
        """
        n = int(self.headers.get("Content-Length") or 0)
        if n <= 0:
            raise ValueError("empty upload")
        if n > _MAX_UPLOAD_BYTES:
            raise ValueError(f"file too large (max {_MAX_UPLOAD_BYTES // 1024 // 1024} MB)")
        qs = parse_qs(urlparse(self.path).query)
        raw_name = (qs.get("filename") or ["upload.pdf"])[0]
        # keep only the basename: an uploaded "../../x.pdf" must not escape the temp dir
        safe = Path(raw_name).name or "upload.pdf"
        if not safe.lower().endswith(".pdf"):
            raise ValueError("only PDF files are supported")
        hints = {k: self.headers.get(f"X-SL-{k.replace('_', '-')}", "")
                 for k in ("name", "dob", "mobile", "card_last4", "rule_text")}
        hints = {k: v for k, v in hints.items() if v}
        data = self.rfile.read(n)
        # TemporaryDirectory is created 0700, so the statement is not readable by other users, and
        # it is removed on the way out — the PDF never persists.
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / safe).write_bytes(data)
            return self.server.sl_ingest([tmp], hints)   # type: ignore[attr-defined]


def serve(app, *, account: str, host: str = "127.0.0.1", port: int = 8770,
          open_browser: bool = True, hints: Optional[Dict[str, Any]] = None) -> str:
    """Run the local dashboard server. Returns the tokenized URL.

    `app` is a composed `App`; `hints` are the password-derivation hints reused for later imports.
    """
    token = secrets.token_urlsafe(16)
    httpd = ThreadingHTTPServer((host, port), _Handler)
    httpd.sl_app = app                      # type: ignore[attr-defined]
    httpd.sl_account = account              # type: ignore[attr-defined]
    httpd.sl_token = token                  # type: ignore[attr-defined]
    base_hints = dict(hints or {})

    def _ingest(folders, extra_hints) -> Dict[str, Any]:
        from ..sources.folder_source import FolderStatementSource
        merged = {**base_hints, **(extra_hints or {})}
        app._source = FolderStatementSource(folders)
        r = app.ingest(account=account, hints=merged)
        return {"statements": r.statements, "inserted": r.inserted, "duplicate": r.duplicate,
                "failed": r.failed, "skipped": r.skipped, "errors": r.errors[:5]}

    httpd.sl_ingest = _ingest               # type: ignore[attr-defined]

    def _gmail(extra_hints) -> Dict[str, Any]:
        """Run the OAuth loopback flow and import. Blocks on the user's browser consent."""
        try:
            from ..sources.gmail_source import GmailStatementSource
        except Exception as e:
            return {"error": f"Gmail support not installed: {e}"}
        try:
            app._source = GmailStatementSource()
            r = app.ingest(account=account, hints={**base_hints, **(extra_hints or {})})
        except Exception as e:
            # surface the real reason (missing client secret, denied consent, offline)
            return {"error": f"{type(e).__name__}: {e}"}
        return {"statements": r.statements, "inserted": r.inserted, "duplicate": r.duplicate,
                "failed": r.failed, "skipped": r.skipped, "errors": r.errors[:5]}

    httpd.sl_gmail = _gmail                 # type: ignore[attr-defined]

    def _refresh() -> Dict[str, Any]:
        """Re-check the last-used source. Only Gmail can self-refresh; folders need a re-import."""
        if app._source is None:
            return {"ok": False, "reason": "Nothing to refresh from yet — import statements first."}
        a = app.refresh(account=account, hints=base_hints, force=True)
        return {"ok": a.ok, "inserted": a.inserted, "duplicate": a.duplicate,
                "failed": a.failed, "reason": a.reason}

    httpd.sl_refresh = _refresh             # type: ignore[attr-defined]

    url = f"http://{host}:{port}/?t={token}"
    if open_browser:
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    print(f"StatementLens -> {url}\n(local only; Ctrl-C to stop)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
    return url
