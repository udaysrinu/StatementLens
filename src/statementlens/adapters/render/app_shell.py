"""AppShellRenderer: the StatementLens dashboard on CRED's NeoPOP components.

The owner compared the plain-CSS build with CRED's real NeoPOP library screen by screen and chose NeoPOP.
The UI is a React app in `web/` (React 18 + styled-components 5 + @cred/neopop-web 1.0.0, Apache-2.0),
built to `web_dist/` and committed, so installing the package needs no Node. This renderer inlines that
bundle, the fonts and the data into ONE page: it still fetches nothing at runtime and still works when
the file is opened offline.

The dashboard's logic (money in paise, compute(), netting, periods, navigation) lives in web/src/core.js,
moved verbatim from the plain-CSS page, which is kept at /legacy (legacy_shell.py) until every screen
is rebuilt.
"""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any, Dict

from .legacy_shell import _ICON_SVG, _data_uri, _fill, _font_css

_DIST = Path(__file__).with_name("web_dist")


def _bundle() -> Dict[str, str]:
    """The built app. Read on every render, so a `npm run build` shows up on the next page load."""
    js, css = _DIST / "app.js", _DIST / "app.css"
    if not js.exists():
        raise RuntimeError("the dashboard is not built: run `npm install && npm run build` in web/")
    # a literal "</script" inside the bundle would end the inline <script> early
    return {"js": js.read_text(encoding="utf-8").replace("</script", "<\\/script"),
            "css": css.read_text(encoding="utf-8") if css.exists() else ""}


class AppShellRenderer:
    def render(self, dataset: Dict[str, Any]) -> str:
        raw_label = str(dataset.get("meta", {}).get("account", "Account"))
        label = html.escape(raw_label)
        payload = json.dumps(dataset, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/")
        icon = _data_uri("image/svg+xml", _ICON_SVG)
        manifest = _data_uri("application/manifest+json", json.dumps({
            "name": f"{raw_label} · Money", "short_name": raw_label,
            "display": "standalone", "orientation": "portrait",
            "background_color": "#efefee", "theme_color": "#efefee", "start_url": ".",
            "icons": [{"src": icon, "sizes": "512x512", "type": "image/svg+xml", "purpose": "any maskable"}],
        }, separators=(",", ":")))
        b = _bundle()
        return _fill(_PAGE, {"FONTS": _font_css(), "CSS": b["css"], "LABEL": label, "ICON": icon,
                             "MANIFEST": manifest, "DATA": payload, "JS": b["js"]})


_PAGE = """<!DOCTYPE html>
<html lang="en-IN" data-theme="light">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>__LABEL__ · Money</title>
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="__LABEL__">
<meta name="theme-color" content="#121212" media="(prefers-color-scheme: dark)">
<meta name="theme-color" content="#efefee" media="(prefers-color-scheme: light)">
<link rel="apple-touch-icon" href="__ICON__">
<link rel="icon" href="__ICON__">
<link rel="manifest" href="__MANIFEST__">
<style>
__FONTS__
</style>
<style>__CSS__</style>
<script>try{var th=new URLSearchParams(location.search).get('theme')||localStorage.getItem('sl-theme');if(th)document.documentElement.dataset.theme=th;}catch(_){}</script>
</head>
<body>
<div id="root"></div>
<script type="application/json" id="data">__DATA__</script>
<script>__JS__</script>
</body>
</html>
"""
