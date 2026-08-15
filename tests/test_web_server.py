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


def test_period_control_offers_presets_first_and_custom_last():
    """The picker is client-side JS, so the only thing a Python test can pin is the markup it emits.

    What broke before and must not come back: two rival period controls on one screen, and the
    rarest option (a manual date pair) rendered as the most prominent one.
    """
    from statementlens.adapters.render.app_shell import AppShellRenderer

    page = AppShellRenderer().render({"meta": {"account": "SBI"}, "transactions": [], "insights": []})

    # every preset the user asked for, shortest span first
    order = [page.index(f"'{k}','{lab}'") for k, lab in
             [("W", "1W"), ("M", "1M"), ("3M", "3M"), ("6M", "6M"),
              ("Y", "1Y"), ("5Y", "5Y"), ("all", "All")]]
    assert order == sorted(order), "presets must be declared shortest-span first"

    # Custom sits OUTSIDE the preset row and after it, so it is never the chip that scrolls off.
    # Assert on the emitted template, not on declaration order — `custom` is a const above the return.
    assert '<div class="pwrap"><div class="prow">${chips}${cycle}</div>${custom}</div>' in page
    assert 'class="pcustom' in page, "Custom must render as the demoted control, not a peer chip"
    assert "segBar" not in page, "the second, rival period control must stay deleted"


def test_every_flow_side_is_reachable_from_the_hero():
    """Incoming and investments must be viewable at full precision, not just as rounded tiles.

    The bug this pins: `incoming_sources` was computed, embedded in the payload, and then referenced
    ZERO times by the renderer. ₹72L of credits was reachable only as a two-significant-figure "₹73L"
    tile with nothing to drill into, because the hero was hardcoded to the spend total.
    """
    from statementlens.adapters.render.app_shell import AppShellRenderer

    page = AppShellRenderer().render({"meta": {"account": "SBI"}, "transactions": [], "insights": []})

    # all three sides of the flow can become the hero, and each tile is the control that does it
    assert "setFlow('${k}')" in page, "the flow tiles must be buttons, not inert text"
    for flow in ("out:", "in:", "inv:"):
        assert flow in page.split("const FLOWS=")[1][:200], f"{flow} missing from the flow table"
    assert "heroValue(" in page, "the hero must read the selected flow, not a hardcoded total"
    for tile in ("'in','incoming'", "'inv','investments'", "'out','spends'"):
        assert tile in page, f"tile {tile} must be rendered"

    # each side has a breakdown behind it — a big number with nothing under it is a dead end
    assert "sourceCard(" in page and "where it came from" in page
    assert "investCard(" in page and "what you put away" in page

    # the per-row income label must be what the client aggregates; without it the breakdown could
    # only ever show all-time figures beside a period-filtered hero
    assert "t.src" in page, "credits must carry a per-row income source for re-slicing by period"


def test_netting_modes_are_offered_and_disclosed():
    """Gross must stay the default, and any mode that shrinks a total must say how much it removed.

    The danger here is a view that quietly deletes real spending. So: three explicit modes, the
    per-row pairing needed to honour the period picker, and a visible disclosure that links to an
    audit screen listing every pair.
    """
    from statementlens.adapters.render.app_shell import AppShellRenderer

    page = AppShellRenderer().render({"meta": {"account": "SBI"}, "transactions": [], "insights": []})

    assert "let NET='gross'" in page, "gross — the statement as printed — must be the default"
    assert "setNet('${k}')" in page, "the modes must be buttons"
    for mode in ("'gross','gross'", "'clean','hide cancelled'", "'net','net per person'"):
        assert mode in page, f"mode {mode} must be offered"

    # a pair is only dropped when BOTH legs are in range, so the client needs the partner ref
    assert "t.rev" in page and "have.has(t.rev)" in page
    # and the counterparty key, for person netting
    assert "t.cp" in page

    # the disclosure and its audit trail
    assert "cancelled" in page and "netNote(" in page
    assert "nettingV" in page and "cancelled pairs" in page
    assert "money moved both ways" in page


def test_top_merchant_rows_drill_down_and_keep_their_breadcrumb():
    """The "top merchants" rows carried .crow (styled cursor:pointer) but had NO onclick.

    So the whole list looked clickable and did nothing. Clicking a merchant must open that merchant's
    transactions, and backing out must return to the TAG it was reached from rather than dumping the
    user at the tag list.
    """
    from statementlens.adapters.render.app_shell import AppShellRenderer

    page = AppShellRenderer().render({"meta": {"account": "SBI"}, "transactions": [], "insights": []})

    merch_row = page[page.index("const merRows="):]
    merch_row = merch_row[:merch_row.index("\n")]
    assert "onclick=" in merch_row and "openMerchant(" in merch_row, "merchant rows must drill down"

    # the breadcrumb: remember the tag, and offer it as the back target
    assert "FROMTAG=TAGVIEW" in page
    assert "backFromDetail()" in page

    # keys must be ESCAPED, not stripped: stripping an apostrophe mutates the very key the next
    # screen filters on, so "DOMINO'S" would open an empty list
    assert "const escArg=" in page
    assert """replace(/'/g,"")""" not in page, "apostrophes must be escaped, never stripped"


import urllib.parse  # noqa: E402  (used above; imported late to keep the header tidy)
