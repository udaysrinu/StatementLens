"""The NeoPOP dashboard page: one self-contained file built from the committed bundle.

The two properties that matter: it carries its own code, fonts and data (it fetches nothing, so it works
offline and tells no CDN that someone opened their finances), and the data is embedded where core.js
reads it.
"""
import json
import re

from statementlens.adapters.render.app_shell import AppShellRenderer, _DIST

DATASET = {"meta": {"account": "Demo <Bank>"}, "txns": [{"ref": "a", "d": "2026-07-01", "a": 100, "dir": "D", "f": "s"}],
           "insights": []}


def test_the_bundle_is_built_and_committed():
    assert (_DIST / "app.js").stat().st_size > 50_000, "run `npm run build` in web/ and commit web_dist/"


def test_page_is_self_contained_and_fetches_nothing():
    page = AppShellRenderer().render(DATASET)
    assert '<div id="root"></div>' in page
    assert not re.search(r'<script[^>]+src=', page), "the bundle must be inline, not linked"
    assert not re.search(r'(?:src|href)="https?://', page), "nothing may load from the network"
    assert "@font-face" in page and "data:font/woff2;base64," in page


def test_data_is_embedded_where_core_reads_it_and_cannot_break_out():
    page = AppShellRenderer().render({**DATASET, "meta": {"account": "</script><b>x"}})
    raw = page.split('<script type="application/json" id="data">', 1)[1].split("</script>", 1)[0]
    assert json.loads(raw.replace("<\\/", "</"))["meta"]["account"] == "</script><b>x"
    assert "<title>&lt;/script&gt;&lt;b&gt;x · Money</title>" in page


def test_placeholders_inside_the_data_are_never_filled():
    """A narration is untrusted text. "__JS__" in it must stay text, not pull the bundle into the data."""
    from statementlens.adapters.render.legacy_shell import LegacyShellRenderer
    ds = {**DATASET, "meta": {"account": "__DATA__ __JS__"},
          "txns": [{"ref": "a", "d": "2026-07-01", "a": 1, "dir": "D", "f": "s", "m": "__JS__ __FONTS__"}]}
    for page in (AppShellRenderer().render(ds), LegacyShellRenderer().render(ds)):
        raw = page.split('<script type="application/json" id="data">', 1)[1].split("</script>", 1)[0]
        data = json.loads(raw.replace("<\\/", "</"))
        assert data["txns"][0]["m"] == "__JS__ __FONTS__" and data["meta"]["account"] == "__DATA__ __JS__"
        assert page.count('<script type="application/json" id="data">') == 1
