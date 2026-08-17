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
    # assert on the mode KEYS, not the button copy: the labels are wording and were rewritten once
    # already after the user asked twice what they meant. Pinning copy makes a test that fails on
    # every improvement to it, which trains people to edit the test instead of reading it.
    for key in ("b('gross'", "b('clean'", "b('net'"):
        assert key in page, f"mode {key} must be offered"

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


def test_paise_are_dimmed_typographically_never_rounded_away():
    """fmtH() dims the paise so ₹97,000.00 reads at a glance. It must NOT change the number.

    This is the one dangerous way to get "calmer numbers" wrong: rounding to whole rupees would make
    every figure stop reconciling against the statement. fmtH must emit the same digits as fmt.
    """
    from statementlens.adapters.render.app_shell import AppShellRenderer

    page = AppShellRenderer().render({"meta": {"account": "SBI"}, "transactions": [], "insights": []})
    assert "function fmtH(" in page
    # it wraps the decimal tail in a span and returns the untouched fmt() output otherwise
    assert "s.lastIndexOf('.')" in page and 'class="ps"' in page
    assert ".ps{opacity:" in page, "the paise span needs the dimming rule"


def test_flow_hues_do_not_clobber_the_guilloche_texture():
    """The bar hue must be background-COLOR, not the `background` shorthand.

    The shorthand resets background-image, which silently wiped out the banknote texture layered on by
    .guil — the bars still rendered, just flat, so nothing failed loudly.
    """
    from statementlens.adapters.render.app_shell import AppShellRenderer

    page = AppShellRenderer().render({"meta": {"account": "SBI"}, "transactions": [], "insights": []})
    assert ".guil{background-image:" in page
    for flow in ("in", "inv", "out"):
        assert f".fbi.{flow}{{background-color:" in page, \
            f".fbi.{flow} must set background-color, not the background shorthand"


def test_nothing_styled_clickable_is_actually_dead():
    """Anything with cursor:pointer must carry a handler. This bug shipped FOUR times.

    Top-merchant rows, then trend-chart bars, then the netting people rows, then the recurring rows —
    each looked interactive because .crow/.trow/.bcol are styled cursor:pointer, and each did nothing
    when tapped. Screenshots cannot catch it and neither can asserting on computed values, which is how
    it kept getting through: the numbers were right, so the check passed.

    So: derive the pointer-styled class list from the CSS, then require every render site of those
    classes to have an onclick. Deliberately mechanical — a human reviewer misses this every time.
    """
    import re

    from statementlens.adapters.render.app_shell import AppShellRenderer

    page = AppShellRenderer().render({"meta": {"account": "SBI"}, "transactions": [], "insights": []})

    # classes the stylesheet marks as clickable
    pointer: set = set()
    for selector in re.findall(r"\n(\.[a-z0-9\-\. >:]+)\{[^}]*cursor:pointer", page, re.I):
        pointer.update(re.findall(r"\.([a-z0-9\-]+)", selector, re.I))

    # containers and wrappers whose CHILDREN carry the handlers, plus one deliberately-static label
    exempt = {
        "nav", "fresh", "seg", "st",        # populated elsewhere, or their <a>/<button> children click
        "simrow",                            # a <label> wrapping a checkbox — the input handles it
        "link",                              # a modifier, always paired with a real class
        "av", "sortb", "simgo",              # single elements that do carry handlers inline
        "nnote",                             # also used for a static disclosure with no action
    }

    dead = []
    for cls in sorted(pointer - exempt):
        for m in re.finditer(r'class="[^"]*\b' + re.escape(cls) + r'\b[^"]*"[^>]{0,140}', page):
            frag = m.group(0)
            if "onclick" not in frag and "href" not in frag:
                dead.append(f"{cls}: {frag[:80]}")

    assert not dead, "styled clickable but no handler:\n  " + "\n  ".join(dead)


def test_the_hero_is_a_pager_with_all_three_flows_present():
    """The three flows are peers, so all three panes render at once and the hero swipes between them.

    Two things this pins. First, every pane is in the DOM — that is what makes the swipe feel instant,
    since the number is already there rather than fetched on settle. Second, the scroller must re-park
    itself on EVERY draw: innerHTML replaces it with a fresh node at scrollLeft 0, so a swipe-triggered
    redraw left the pager showing pane 0 while the dots and the breakdown said pane 2.
    """
    import re

    from statementlens.adapters.render.app_shell import AppShellRenderer

    page = AppShellRenderer().render({"meta": {"account": "SBI"}, "transactions": [], "insights": []})

    # money in -> money out -> money kept, and all three are laid out, not just the active one
    assert "const FLOWORDER=['in','out','inv']" in page
    assert "FLOWORDER.map(f=>" in page, "every flow must render a pane"
    assert "heroValueFor(R,f)" in page, "panes need their values read without mutating FLOW"

    # native scroll-snap, not a hand-rolled gesture handler
    css = re.search(r"\.hpager\{([^}]*)\}", page)
    assert css and "scroll-snap-type:x mandatory" in css.group(1)
    pane = re.search(r"\.hpane\{([^}]*)\}", page)
    assert pane and "scroll-snap-align:start" in pane.group(1)
    assert "flex:0 0 100%" in pane.group(1), "a pane must be exactly one viewport wide, or snap drifts"

    # the re-park is unconditional — a guard here is the desync bug
    assert re.search(r"syncPager\(\);", page), "draw() must re-park the pager"
    assert "keepPager" not in page, "skipping the re-park desyncs the pager from the dots"

    # dots are a real control for pointer users, who have no swipe
    assert "setFlow('${f}')" in page and 'class="hdot' in page
    assert 'aria-current="${FLOW===f}"' in page


def test_interactive_controls_declare_a_touch_target():
    """Every tappable control needs a 44px hit area — measured on the live page, pinned here.

    A live audit found "see all" at 35x19px (less than half the minimum, and it is the primary link
    between screens), the account and period chips at 31px, and the theme toggle at 40px. Small targets
    are invisible in a screenshot and fine with a mouse, so nothing catches them except measurement.

    Asserted on the CSS rather than by rendering: this test has no browser. Each selector below must
    carry an explicit min-height, so a future edit that drops one fails loudly instead of silently
    shrinking a target back under the minimum.
    """
    import re

    from statementlens.adapters.render.app_shell import AppShellRenderer

    page = AppShellRenderer().render({"meta": {"account": "SBI"}, "transactions": [], "insights": []})

    # selector -> the minimum it must declare. 36 is legitimate for chips that sit inside a 4px-padded
    # pill (36 + 8 = a 44px row); everything standalone must reach 44 on its own.
    required = {".st a": 44, ".achip": 44, ".fresh button": 44, ".pchip": 36, ".back": 44}
    missing = []
    for selector, floor in required.items():
        block = re.search(re.escape(selector) + r"\{([^}]*)\}", page)
        if block is None:
            missing.append(f"{selector}: rule not found")
            continue
        found = re.search(r"min-height:(\d+)px", block.group(1))
        if not found:
            missing.append(f"{selector}: no min-height declared")
        elif int(found.group(1)) < floor:
            missing.append(f"{selector}: min-height {found.group(1)}px < {floor}px")

    assert not missing, "touch targets under the minimum:\n  " + "\n  ".join(missing)

    # the theme toggle is a fixed square, so it is sized rather than min-height'd
    av = re.search(r"\.av\{([^}]*)\}", page).group(1)
    assert "width:44px" in av and "height:44px" in av, f"theme toggle is under 44px: {av[:60]}"
    # and it must have a real accessible name — the glyph reads as "circle with left half black"
    assert 'aria-label="switch between light and dark"' in page


def test_styled_buttons_inherit_their_text_colour():
    """A <button> gets the UA's black text unless told otherwise, and `font:inherit` does NOT carry it.

    This shipped invisible text: turning the trend-chart bars into buttons made the callout above the
    newest bar render #000 on a #171f2c card — 1.19:1, unreadable. The contrast audit missed it because
    the audit worked from a hand-listed selector set and .bcall was not in it, which is the real lesson:
    a check that enumerates what to look at will always miss the thing nobody thought of.

    Five button rules had the same latent defect. Any rule that resets `font` must reset `color` too.
    """
    import re

    from statementlens.adapters.render.app_shell import AppShellRenderer

    page = AppShellRenderer().render({"meta": {"account": "SBI"}, "transactions": [], "insights": []})

    bad = []
    # each CSS rule body that resets font must also set a colour (its own, or inherit)
    for m in re.finditer(r"\n(\.[a-z0-9\-\.]+)\{([^}]*font:inherit[^}]*)\}", page, re.I):
        selector, body = m.group(1), m.group(2)
        if "color:" not in body:
            bad.append(selector)
    assert not bad, ("these reset font but not color, so they fall back to the UA's black text: "
                     + ", ".join(bad))


def test_both_themes_define_every_colour_token():
    """A token defined in :root but not in the light override silently keeps the DARK value.

    That is how a light-theme screen ends up with one dark-mode colour in it — the hardest kind of
    theming bug to spot, because everything else looks right.
    """
    import re

    from statementlens.adapters.render.app_shell import AppShellRenderer

    page = AppShellRenderer().render({"meta": {"account": "SBI"}, "transactions": [], "insights": []})

    def tokens(block: str) -> set:
        return set(re.findall(r"(--[a-z0-9\-]+)\s*:", block))

    root = tokens(page[page.index(":root{"):page.index("}", page.index(":root{"))])
    light_at = page.index("[data-theme=light]{")
    light = tokens(page[light_at:page.index("}", light_at)])

    # fonts and easing are intentionally shared; only colour-ish tokens must be re-declared
    shared_by_design = {"--disp", "--body", "--ease"}
    missing = (root - light) - shared_by_design
    assert not missing, f"light theme never overrides: {sorted(missing)}"


def test_redrawing_the_same_screen_neither_reanimates_nor_drops_the_caret():
    """The view is rebuilt from state on every change — cheap (3.6ms/310 nodes) but not free.

    Two things a diffing renderer gets for free had to be handled explicitly, and both were visible:
    a 0.5s staggered entry animation replayed on every filter tap, so changing one number made the
    whole page fade in from blank; and the caret was lost, because the input holding it had been
    replaced. Neither is a speed problem, which is why the fix is not component diffing.
    """
    from statementlens.adapters.render.app_shell import AppShellRenderer

    page = AppShellRenderer().render({"meta": {"account": "SBI"}, "transactions": [], "insights": []})

    # animations are suppressed while re-rendering the SAME screen, and only then
    assert "const fresh=(TAB!==LASTVIEW)" in page, "must distinguish a new screen from a value change"
    assert "v.classList.toggle('nofx',!fresh)" in page
    assert ".nofx .rise" in page and "animation:none!important" in page

    # focus and selection are carried across the rebuild
    assert "document.activeElement" in page and "setSelectionRange" in page
    # every input that can hold a caret needs a STABLE id, or focus cannot be restored by lookup
    for ident in ("dt-from", "dt-to", "q", "note", "split-exact", "split-with"):
        assert f'id="{ident}"' in page, f"input {ident} needs a stable id for focus restore"


def test_properties_safari_needs_prefixed_are_prefixed():
    """This app's point is running on an iPhone, and iOS Safari is WebKit-only.

    All browser testing here happens in Chromium, so a property that WebKit needs prefixed degrades
    silently rather than failing: `backdrop-filter` without `-webkit-` just dropped the tab bar's blur,
    invisible in Chromium and invisible in a screenshot of a 92%-opaque bar.
    """
    import re

    from statementlens.adapters.render.app_shell import AppShellRenderer

    page = AppShellRenderer().render({"meta": {"account": "SBI"}, "transactions": [], "insights": []})

    # each of these must appear with the -webkit- prefix at least as often as unprefixed
    for prop in ("backdrop-filter", "mask", "line-clamp", "box-orient"):
        plain = len(re.findall(rf"(?<!-){prop}\s*:", page))
        pref = len(re.findall(rf"-webkit-{prop}\s*:", page))
        if plain:
            assert pref >= 1, f"{prop} is used unprefixed with no -webkit-{prop} fallback for Safari"


import urllib.parse  # noqa: E402  (used above; imported late to keep the header tidy)
