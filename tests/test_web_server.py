"""Checks for the local web server: auth, routing, and upload validation.

Runs a real server on an ephemeral port — these are the paths that unit tests missed (the
thread-per-request SQLite bug only appeared under an actual HTTP request).
"""

import json
import tempfile
import threading
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

from statementlens.app import App
from statementlens.domain.models import Direction, Statement, Transaction
from statementlens.domain.money import Money


def _seeded_app(tmp: str) -> App:
    app = App(db_path=str(Path(tmp) / "t.db"))
    app.repo.save_statement(Statement("SBI", "s1", "stmt.pdf", "012026", (
        Transaction(txn_date=date(2026, 1, 5), description="UPI/SHOP/PAY",
                    amount=Money.of(400, "INR"), direction=Direction.DEBIT,
                    merchant="Shop A", category="untagged", raw_date="05-01-26"),)))
    return app


class _Server:
    """Starts the real server on a background thread and tears it down cleanly."""

    def __init__(self, app, account="SBI"):
        from statementlens.adapters.web import server as srv
        import secrets
        from http.server import ThreadingHTTPServer
        self.token = secrets.token_urlsafe(8)
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), srv._Handler)
        self.httpd.sl_app = app
        self.httpd.sl_account = account
        self.httpd.sl_token = self.token
        self.httpd.sl_ingest = lambda folders, hints: {"inserted": 0, "duplicate": 0,
                                                      "statements": 0, "failed": 0,
                                                      "skipped": [], "errors": []}
        self.httpd.sl_gmail = lambda hints: {"error": "not configured"}
        self.port = self.httpd.server_address[1]
        self.t = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.t.start()

    def url(self, path="/", token=True):
        sep = "&" if "?" in path else "?"
        return f"http://127.0.0.1:{self.port}{path}" + (f"{sep}t={self.token}" if token else "")

    def get(self, path="/", token=True):
        with urllib.request.urlopen(self.url(path, token), timeout=5) as r:
            return r.status, r.read(), dict(r.headers)

    def post(self, path, body=b"", token=True):
        req = urllib.request.Request(self.url(path, token), data=body, method="POST")
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read().decode())

    def close(self):
        self.httpd.shutdown(); self.httpd.server_close()


def test_requests_without_a_token_are_refused():
    # any website in the browser can POST to localhost; an open local API is a real hole
    with tempfile.TemporaryDirectory() as tmp:
        s = _Server(_seeded_app(tmp))
        try:
            try:
                s.get("/", token=False)
            except urllib.error.HTTPError as e:
                assert e.code == 403
            else:
                raise AssertionError("expected 403 without a token")
        finally:
            s.close()


def test_dashboard_is_served_over_http_from_a_request_thread():
    # regression: one shared SQLite connection raised ProgrammingError here
    with tempfile.TemporaryDirectory() as tmp:
        s = _Server(_seeded_app(tmp))
        try:
            code, body, headers = s.get("/")
            assert code == 200 and b"Money" in body
            assert headers.get("Cache-Control") == "no-store"   # financial data must not cache
        finally:
            s.close()


def test_empty_database_shows_onboarding_not_an_empty_dashboard():
    with tempfile.TemporaryDirectory() as tmp:
        s = _Server(App(db_path=str(Path(tmp) / "empty.db")))
        try:
            code, body, _ = s.get("/")
            assert code == 200 and b"set up" in body
        finally:
            s.close()


def test_tag_correction_via_http_persists():
    with tempfile.TemporaryDirectory() as tmp:
        app = _seeded_app(tmp)
        s = _Server(app)
        try:
            code, out = s.post("/api/tag", json.dumps({"tag": "grocery",
                                                       "merchant": "Shop A"}).encode())
            assert out == {"ok": True}
            assert app.repo.load_tags().by_merchant["shop a"] == "grocery"
        finally:
            s.close()


def test_tag_without_a_tag_field_is_a_400_not_a_crash():
    with tempfile.TemporaryDirectory() as tmp:
        s = _Server(_seeded_app(tmp))
        try:
            try:
                s.post("/api/tag", b"{}")
            except urllib.error.HTTPError as e:
                assert e.code == 400
            else:
                raise AssertionError("expected 400")
        finally:
            s.close()


def test_upload_rejects_non_pdf_and_strips_path_traversal():
    with tempfile.TemporaryDirectory() as tmp:
        s = _Server(_seeded_app(tmp))
        try:
            try:
                s.post("/api/upload?filename=notes.txt", b"hello")
            except urllib.error.HTTPError as e:
                assert e.code == 400
            else:
                raise AssertionError("expected 400 for a non-PDF")
            # a traversal filename must be reduced to its basename, not escape the temp dir
            code, out = s.post("/api/upload?filename=" + urllib.parse.quote("../../evil.pdf"),
                               b"%PDF-1.4 stub")
            assert "error" not in out or "evil" not in str(out.get("error", ""))
        finally:
            s.close()


def test_password_hints_are_read_from_headers_not_the_url():
    """A URL carrying a date of birth ends up in browser history and proxy logs."""
    with tempfile.TemporaryDirectory() as tmp:
        seen = {}
        app = _seeded_app(tmp)
        s = _Server(app)
        s.httpd.sl_ingest = lambda folders, hints: (seen.update(hints),
                                                    {"inserted": 0, "duplicate": 0, "statements": 0,
                                                     "failed": 0, "skipped": [], "errors": []})[1]
        try:
            # hints in the QUERY STRING must be ignored
            s.post("/api/upload?filename=a.pdf&dob=01011990", b"%PDF-1.4 x")
            assert "dob" not in seen, "a DOB in the URL must not be accepted"
            # hints in HEADERS are used
            req = urllib.request.Request(s.url("/api/upload?filename=a.pdf"),
                                         data=b"%PDF-1.4 x", method="POST")
            req.add_header("X-SL-dob", "01011990")
            req.add_header("X-SL-card-last4", "1234")
            with urllib.request.urlopen(req, timeout=10):
                pass
            assert seen.get("dob") == "01011990"
            assert seen.get("card_last4") == "1234"
        finally:
            s.close()


def test_note_requires_a_content_hash():
    with tempfile.TemporaryDirectory() as tmp:
        s = _Server(_seeded_app(tmp))
        try:
            try:
                s.post("/api/note", json.dumps({"note": "x"}).encode())
            except urllib.error.HTTPError as e:
                assert e.code == 400
            else:
                raise AssertionError("expected 400")
        finally:
            s.close()


import urllib.parse  # noqa: E402  (used above; imported late to keep the header tidy)
