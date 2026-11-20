"""LegacyShellRenderer — the plain-CSS dashboard, served at /legacy while the NeoPOP rebuild lands.

It was the default until the owner chose CRED's real NeoPOP components (see app_shell.py). Kept whole so
every screen stays reachable during the migration; delete it once the NeoPOP build covers them all.

Original notes: the StatementLens dashboard, built to CRED Money's structure and feel.

The owner pinned CRED Money as the reference ("build exactly the same"), so the information
architecture is CRED's: a header band with the balance, four tabs (accounts · transactions ·
recurring · cash flow) over a white sheet, and every total opening into the rows behind it. On a wide
screen the drilled-into screen opens in a pane beside the tabs instead of replacing them.

The look is CRED's visual language rebuilt from scratch, not lifted: Gloock (display serif) and
Figtree (UI sans) stand in for CRED's commercial faces, both OFL and embedded so the page fetches
nothing; buttons follow CRED's open-source NeoPOP system (Apache-2.0) — a flat face sitting on a 3D
edge that it sinks into when pressed. No CRED logo, mark or asset is used.

Money stays integer paise end to end and the browser recomputes every total from the rows, so the
consistency suite can compare it against the server (tests/test_consistency_real_store.py).
"""

from __future__ import annotations

import base64
import html
import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict


#: App icon, as an inline SVG so the page fetches nothing and stays one self-contained file — the
#: property that lets it be emailed, put in iCloud, or opened years later with no server.
_ICON_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">'
    '<rect width="512" height="512" rx="112" fill="#0f0f0f"/>'
    '<path d="M150 360V250m106 110V170m106 190V214" stroke="#fff" stroke-width="40"'
    ' stroke-linecap="square" fill="none"/></svg>'
)

_FONT_DIR = Path(__file__).with_name("fonts")


def _data_uri(mime: str, text: str) -> str:
    """A percent-encoded data: URI. Used for the icon and manifest.

    Kept as text rather than base64 so the payload stays greppable, and percent-encoded rather than
    raw because a data URI in an href cannot contain '#' or unescaped quotes.
    """
    from urllib.parse import quote
    return f"data:{mime},{quote(text, safe='')}"


@lru_cache(maxsize=1)
def _font_css() -> str:
    """@font-face rules with the woff2 files inlined.

    Inlined rather than linked so the page keeps working offline and never tells a font CDN that
    someone opened their finances. Each family ships its `latin` and `latin-ext` subsets: the rupee
    sign (U+20B9) lives in latin-ext, so dropping that file would render every ₹ in a fallback face.
    """
    ranges = json.loads((_FONT_DIR / "ranges.json").read_text(encoding="utf-8"))
    rules = []
    for family, key, weight in (("Gloock", "gloock", "400"), ("Figtree", "figtree", "400 700")):
        for subset in ("latin-ext", "latin"):
            path = _FONT_DIR / f"{key}-{subset}.woff2"
            if not path.exists():
                continue
            b64 = base64.b64encode(path.read_bytes()).decode("ascii")
            rules.append(
                f"@font-face{{font-family:'{family}';font-style:normal;font-weight:{weight};"
                f"font-display:swap;src:url(data:font/woff2;base64,{b64}) format('woff2');"
                f"unicode-range:{ranges[f'{key}-{subset}']}}}")
    return "\n".join(rules)


_SLOT = __import__("re").compile(r"__(FONTS|CSS|LABEL|ICON|MANIFEST|DATA|JS)__")


def _fill(page: str, values: Dict[str, str]) -> str:
    """Fill every __SLOT__ in ONE pass. Chained str.replace() would re-scan inserted values, so a
    statement narration containing "__JS__" would have the whole bundle pasted into the data."""
    return _SLOT.sub(lambda m: values[m.group(1)] if m.group(1) in values else m.group(0), page)


class LegacyShellRenderer:
    def render(self, dataset: Dict[str, Any]) -> str:
        label = html.escape(str(dataset.get("meta", {}).get("account", "Account")))
        payload = json.dumps(dataset, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/")
        icon = _data_uri("image/svg+xml", _ICON_SVG)
        raw_label = str(dataset.get("meta", {}).get("account", "Account"))
        manifest = _data_uri("application/manifest+json", json.dumps({
            "name": f"{raw_label} · Money", "short_name": raw_label,
            "display": "standalone", "orientation": "portrait",
            "background_color": "#efefee", "theme_color": "#efefee",
            "start_url": ".",
            "icons": [{"src": icon, "sizes": "512x512", "type": "image/svg+xml",
                       "purpose": "any maskable"}],
        }, separators=(",", ":")))
        return _fill(_PAGE, {"FONTS": _font_css(), "LABEL": label, "ICON": icon,
                             "MANIFEST": manifest, "DATA": payload})


_PAGE = r"""<!DOCTYPE html>
<html lang="en-IN" data-theme="light">
<head>
<meta charset="utf-8">
<!-- viewport-fit=cover + the safe-area padding below is what makes this fill an iPhone screen
     properly once installed: without it the status bar overlays the header band. -->
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>__LABEL__ · Money</title>
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="__LABEL__">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="theme-color" content="#121212" media="(prefers-color-scheme: dark)">
<meta name="theme-color" content="#efefee" media="(prefers-color-scheme: light)">
<link rel="apple-touch-icon" href="__ICON__">
<link rel="icon" href="__ICON__">
<link rel="manifest" href="__MANIFEST__">
<style>
__FONTS__
/* ---- tokens ----
   Light is CRED's own palette and the default: a cool grey header band over a pure white sheet,
   near-black ink, two greys, hairlines. Dark is the same structure on near-black.
   Every text colour is checked against the darkest surface it sits on in its theme: --ink3 is
   #6b6b6b because #767676 measured 4.27:1 on the band — under AA — and it carries real labels. --up is
   #077f47 because CRED's brighter green measured 4.42:1 on white at 12px. Gold (the salary-cycle and
   "detected" accents) is #8a5f0f on the cream note for 5.3:1. */
:root{
  --page:#000000;--band:#121212;--bg:#0b0b0b;--s1:#141414;--s2:#1d1d1d;
  --ink:#f3f3f3;--ink2:#bdbdbd;--ink3:#959595;--line:#262626;--line2:#3d3d3d;
  --up:#41d18f;--down:#ff7a72;--link:#98b5ff;
  --gold:#e5c072;--goldbg:#1c170b;--goldline:#53431d;--goldfill:#dcab4c;--ongold:#1a1306;
  --np:#f3f3f3;--onnp:#0b0b0b;--npr:#9d9d9d;--npb:#6a6a6a;
  --inF:#5f86ea;--inL:#a7bff7;--inS:#2d50c6;--outF:#c287de;--outL:#e9c2f6;--outS:#73348f;
  --invF:#e3a083;--invL:#f7d4c5;--invS:#a1502c;
  --sel:rgba(255,255,255,.1);--edge:#2f2f2f;--ray:rgba(229,192,114,.16);--sunbg:#17140e;
  --disp:'Gloock',Georgia,'Times New Roman',serif;
  --body:'Figtree',-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif;
  --ease:cubic-bezier(.2,.7,.3,1)
}
[data-theme=light]{
  --page:#e7e7e5;--band:#efefee;--bg:#ffffff;--s1:#ffffff;--s2:#f5f5f4;
  --ink:#0f0f0f;--ink2:#555555;--ink3:#6b6b6b;--line:#e7e7e7;--line2:#cfcfcf;
  --up:#077f47;--down:#c2352d;--link:#1f47d4;
  --gold:#8a5f0f;--goldbg:#fcf8ee;--goldline:#e8d6a4;--goldfill:#93671b;--ongold:#ffffff;
  --np:#0f0f0f;--onnp:#ffffff;--npr:#6f6f6f;--npb:#3b3b3b;
  --inF:#aac3f6;--inL:#7397ea;--inS:#0d2a8c;--outF:#e8b0f6;--outL:#c57de2;--outS:#3d1052;
  --invF:#f5ccb9;--invL:#df9d7f;--invS:#7c3518;
  --sel:rgba(15,15,15,.05);--edge:#2b2b2b;--ray:rgba(154,118,52,.22);--sunbg:#f1ece3
}
*{box-sizing:border-box;margin:0;padding:0}
html{-webkit-text-size-adjust:100%;text-size-adjust:100%}
body{background:var(--page);color:var(--ink);font:400 .9375rem/1.5 var(--body);
  -webkit-font-smoothing:antialiased;-moz-osx-font-smoothing:grayscale;min-height:100vh}
::selection{background:var(--ink);color:var(--bg)}
:focus-visible{outline:2px solid var(--ink);outline-offset:2px}
button,input,select,textarea{font-family:inherit}
svg{display:block}
.num{font-variant-numeric:tabular-nums}
/* paise recessive: the rupees carry the meaning, the paise are still there to reconcile against.
   Mixed toward --ink3 rather than faded toward the page: both ends pass 4.5:1 in both themes, so the
   mix does too, and a green or red figure keeps its hue (opacity left coloured paise at ~2.6:1) */
.ps{color:color-mix(in oklab,currentColor 35%,var(--ink3))}
.vh{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}
/* privacy mode (the lock): every figure blurs, nothing else changes, so the screen can be shown */
.hush .num,.hush .fig{filter:blur(8px);transition:filter .2s var(--ease)}

/* ---- frame: one column on a phone, column + detail pane on a wide screen ---- */
.app{max-width:480px;margin:0 auto;min-height:100vh;background:var(--band);display:flex;flex-direction:column}
.col{display:flex;flex-direction:column;flex:1;min-width:0;background:var(--band)}
.pane{display:none}
@media (min-width:1100px){
  .app{max-width:1360px;flex-direction:row;align-items:flex-start;background:transparent;
    padding:24px;gap:24px}
  .col{flex:0 0 448px;position:sticky;top:24px;height:calc(100vh - 48px);overflow-y:auto;
    border-radius:20px;scrollbar-width:thin}
  .pane{display:block;flex:1;min-width:0;min-height:calc(100vh - 48px);background:var(--bg);
    border-radius:20px;padding:28px 40px 56px}
  .pane .view{max-width:720px;margin:0 auto}
  .pane.root .back{display:none}
  .row.cur,.frow.cur{background:var(--sel);border-radius:12px;margin-inline:-12px;padding-inline:12px;width:calc(100% + 24px)}
  .cfbar.cur .cfv{color:var(--ink);font-weight:700}
}

/* ---- header band ---- */
.band{padding:calc(14px + env(safe-area-inset-top,0px)) 20px 0}
.btop{display:flex;align-items:center;justify-content:space-between;gap:14px}
.av{width:44px;height:44px;flex:none;display:grid;place-items:center;background:transparent;
  border:1px solid var(--line2);color:var(--ink);cursor:pointer;transition:background .18s var(--ease)}
.av:hover{background:var(--sel)}
.av svg,.lock svg{width:20px;height:20px}
.lock{width:44px;height:44px;flex:none;display:grid;place-items:center;background:var(--np);
  color:var(--onnp);border:none;cursor:pointer}
.lock.on{background:var(--gold);color:var(--ongold)}
.balpill{flex:1;min-width:0;max-width:300px;display:flex;align-items:center;justify-content:space-between;gap:10px;
  min-height:42px;padding:0 16px 0 18px;border-radius:999px;background:var(--bg);border:1px solid var(--line2);
  box-shadow:0 3px 0 var(--line2)}
.balpill .l{font:600 .625rem/1 var(--body);letter-spacing:.14em;white-space:nowrap;text-transform:uppercase;color:var(--ink2)}
.balpill .v{font:700 .875rem/1 var(--body);white-space:nowrap}
/* on Accounts the band itself carries the total, in the display face, where the pill sits elsewhere */
.bandtot{flex:1;min-width:0;display:flex;flex-direction:column;align-items:center;gap:6px}
.bandtot .l{font:600 .625rem/1 var(--body);letter-spacing:.14em;text-transform:uppercase;color:var(--ink2)}
.bandtot .v{font:400 1.625rem/1 var(--disp);white-space:nowrap}
.tabs{display:grid;grid-template-columns:repeat(4,1fr);margin:20px -8px 0}
.tab{position:relative;display:flex;flex-direction:column;align-items:center;gap:9px;min-height:72px;
  padding:4px 2px 16px;background:none;border:none;color:var(--ink2);cursor:pointer;
  font:600 .6875rem/1 var(--body);letter-spacing:.12em;text-transform:uppercase;white-space:nowrap}
.tab svg{width:30px;height:30px;stroke-width:1.35;opacity:.5;transition:opacity .18s var(--ease)}
.tab:hover svg{opacity:.8}
.tab.on{color:var(--ink)}
.tab.on svg{opacity:1}
.tab.on::after{content:'';position:absolute;bottom:6px;left:50%;width:24px;height:3px;border-radius:2px;
  background:var(--ink);transform:translateX(-50%)}
/* below 360px "TRANSACTIONS" can't fit a quarter of the bar: columns size to their labels instead */
@media (max-width:359px){
  .tabs{grid-template-columns:repeat(4,auto);justify-content:space-between;margin:20px -12px 0}
  .tab{font-size:.625rem;letter-spacing:.06em}
  .balpill{justify-content:center}.balpill .l{display:none}
  .bandtot .v{font-size:1.25rem}
}

/* ---- the sheet ---- */
.sheet{flex:1;background:var(--bg);border-radius:18px 18px 0 0;padding:24px 20px calc(48px + env(safe-area-inset-bottom,0px))}
.view{display:flex;flex-direction:column;gap:28px}

/* ---- type ---- */
.h1{font:400 1.75rem/1.12 var(--disp);letter-spacing:-.015em;text-wrap:balance}
.h2{font:400 1.5rem/1.2 var(--disp);letter-spacing:-.01em;text-wrap:balance}
.cap{font:600 .75rem/1.3 var(--body);letter-spacing:.16em;text-transform:uppercase;color:var(--ink3)}
.capk{color:var(--ink)}
.hero{font:400 2.75rem/1.05 var(--disp)}
.heroc{text-align:center;display:flex;flex-direction:column;align-items:center;gap:10px}
.avg{font:700 .75rem/1.3 var(--body);letter-spacing:.14em;text-transform:uppercase;color:var(--up)}
.sub{font:400 .9375rem/1.5 var(--body);color:var(--ink3)}
.subd{font:500 .875rem/1.4 var(--body);color:var(--ink2)}
.up{color:var(--up);font-weight:700}.down{color:var(--down);font-weight:700}
.st{display:flex;justify-content:space-between;align-items:center;gap:12px}
.st h2{font:600 .75rem/1.3 var(--body);letter-spacing:.16em;text-transform:uppercase;color:var(--ink3)}
.st a{display:inline-flex;align-items:center;min-height:44px;padding:0 4px;margin:-10px -4px;
  font:600 .875rem/1 var(--body);color:var(--ink);text-decoration:underline;text-underline-offset:5px;
  text-decoration-thickness:1.5px;cursor:pointer}
.ulink{align-self:center;display:inline-flex;align-items:center;min-height:44px;background:none;border:none;
  font:600 1rem/1 var(--body);color:var(--ink);text-decoration:underline;text-underline-offset:6px;
  text-decoration-thickness:1.5px;cursor:pointer}

/* ---- NeoPOP buttons: a flat face on a 3D edge; pressing sinks the face into the edge ---- */
.np{--d:4px;position:relative;display:inline-flex;align-items:center;justify-content:center;gap:12px;
  min-height:52px;padding:0 28px;margin:0 var(--d) var(--d) 0;background:var(--np);color:var(--onnp);
  border:none;cursor:pointer;font:600 1rem/1 var(--body);transition:transform .12s var(--ease)}
.np::before,.np::after{content:'';position:absolute;transition:opacity .12s var(--ease)}
.np::before{top:0;right:calc(var(--d) * -1);width:var(--d);height:100%;background:var(--npr);
  transform-origin:left top;transform:skewY(45deg)}
.np::after{left:0;bottom:calc(var(--d) * -1);width:100%;height:var(--d);background:var(--npb);
  transform-origin:left top;transform:skewX(45deg)}
.np:active{transform:translate(var(--d),var(--d))}
.np:active::before,.np:active::after{opacity:0}
.np svg{width:22px;height:22px}
.np.ghost{background:var(--bg);color:var(--ink);box-shadow:inset 0 0 0 2px var(--ink);--npr:var(--ink);--npb:var(--ink)}
.np:disabled{background:var(--line2);color:var(--ink3);cursor:not-allowed;transform:none}
.np:disabled::before,.np:disabled::after{display:none}
.npwide{width:calc(100% - 4px)}
.vall{align-self:flex-start}

/* ---- pills and chips ---- */
.pillb{display:inline-flex;align-items:center;gap:8px;min-height:44px;padding:0 16px;border-radius:999px;
  border:1px solid var(--line2);background:var(--bg);color:var(--ink);cursor:pointer;
  font:700 .75rem/1 var(--body);letter-spacing:.14em;text-transform:uppercase;white-space:nowrap;
  transition:border-color .18s var(--ease),background .18s var(--ease)}
.pillb:hover{border-color:var(--ink3)}
.pillb svg{width:16px;height:16px}
.pillb.blue{color:var(--link)}
.pillb.gold{color:var(--gold);border-color:var(--goldline);background:var(--goldbg)}
.pillb.on{box-shadow:inset 0 0 0 1px var(--ink);border-color:var(--ink)}
.chips{display:flex;flex-wrap:wrap;gap:10px}
.chiprow{display:flex;gap:12px;overflow-x:auto;scrollbar-width:none;padding:2px 2px 4px;margin:0 -2px}
.chiprow::-webkit-scrollbar{display:none}
/* account chips: the current account in a heavy pill, the others as discs, CRED's account row */
.achip{flex:none;display:inline-flex;align-items:center;gap:10px;min-height:52px;padding:0 18px 0 8px;
  border-radius:999px;border:1px solid var(--line2);background:var(--bg);color:var(--ink);
  text-decoration:none;font:700 .8125rem/1 var(--body);letter-spacing:.14em;text-transform:uppercase;
  white-space:nowrap;transition:border-color .18s var(--ease)}
.achip:hover{border-color:var(--ink3)}
.achip.on{border:2px solid var(--ink)}
.achip .bm{width:36px;height:36px;font-size:.625rem}

/* ---- notes ---- */
.note{display:flex;gap:16px;align-items:flex-start;padding:18px 20px;border:1.5px solid var(--line2);
  background:var(--s2);font:400 1rem/1.5 var(--body);color:var(--ink)}
.note svg{width:26px;height:26px;flex:none;margin-top:1px}
.note.gold{background:var(--goldbg);border-color:var(--goldline);position:relative}
.note.gold::before{content:'';position:absolute;top:-9px;left:var(--tip,120px);width:16px;height:16px;
  background:var(--goldbg);border-left:1.5px solid var(--goldline);border-top:1.5px solid var(--goldline);
  transform:rotate(45deg)}
.noteacts{display:flex;flex-wrap:wrap;gap:4px 18px;margin:6px 0 -12px}
.notebtn{display:inline-flex;align-items:center;min-height:44px;background:none;border:none;
  color:var(--ink);font:700 .8125rem/1 var(--body);letter-spacing:.08em;text-transform:uppercase;
  text-decoration:underline;text-underline-offset:6px;text-decoration-thickness:1.5px;cursor:pointer}
.nmore{font:400 .9375rem/1.5 var(--body);color:var(--ink2)}

/* ---- rows ---- */
.rlist{display:flex;flex-direction:column}
.row{display:flex;align-items:center;gap:16px;width:100%;padding:14px 0;background:none;border:none;
  text-align:left;cursor:pointer;font:inherit;color:inherit}
.row:hover .rn{text-decoration:underline;text-underline-offset:4px}
.ic{position:relative;width:56px;height:56px;flex:none;border-radius:50%;border:1px solid var(--line);
  display:grid;place-items:center;color:var(--ink);background:var(--bg)}
.ic svg{width:26px;height:26px}
.ic.init{font:400 1.25rem/1 var(--disp)}
.ic .bb{position:absolute;right:-3px;bottom:-1px;width:22px;height:22px;border-radius:50%;
  background:var(--bg);display:grid;place-items:center}
.ic .bb i{width:16px;height:16px;border-radius:50%;background:var(--bk,#2a7fd4)}
.rm{flex:1;min-width:0;display:flex;flex-direction:column;gap:3px}
.rn{font:600 1.0625rem/1.3 var(--body);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.rs{font:400 .9375rem/1.35 var(--body);color:var(--ink3);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.rr{flex:none;display:flex;flex-direction:column;align-items:flex-end;gap:3px}
.ra{font:700 1.0625rem/1.3 var(--body)}
.ra.in{color:var(--up)}
.rd{font:400 .9375rem/1.35 var(--body);color:var(--ink3)}
.chev{display:inline-grid;color:var(--ink2)}
.chev svg{width:16px;height:16px}
/* legend rows: square swatch, dashed separators — CRED's breakdown list */
.lrow{display:flex;align-items:flex-start;gap:18px;width:100%;padding:18px 0;background:none;border:none;
  border-top:1px dashed var(--line2);text-align:left;cursor:pointer;font:inherit;color:inherit}
.lrow:first-child{border-top:none}
.lsw{width:14px;height:14px;flex:none;margin-top:5px;border:1px solid rgba(0,0,0,.25)}
.lm{flex:1;min-width:0}
.ln{display:block;font:500 1.0625rem/1.35 var(--body)}
.lp{display:block;font:700 .9375rem/1.35 var(--body);color:var(--ink3);margin-top:4px}
.la{display:flex;align-items:center;gap:10px;font:600 1.0625rem/1.35 var(--body)}
.lstatic{display:flex;align-items:flex-start;gap:18px;width:100%;padding:18px 0;border-top:1px dashed var(--line2)}
/* merchant bars inside a category */
.bar{height:4px;background:var(--s2);margin-top:9px}
.bar i{display:block;height:100%;background:var(--ink)}

/* ---- three-way cash flow: extruded, banknote-textured bars ---- */
.cfchart{position:relative;height:300px;display:grid;grid-template-columns:repeat(3,1fr);align-items:end;
  gap:12px;padding:40px 6px 0;border-bottom:1.5px solid var(--ink);
  background:linear-gradient(var(--line),var(--line)) 0 40px/100% 1px no-repeat,
    linear-gradient(var(--line),var(--line)) 0 105px/100% 1px no-repeat,
    linear-gradient(var(--line),var(--line)) 0 170px/100% 1px no-repeat,
    linear-gradient(var(--line),var(--line)) 0 235px/100% 1px no-repeat}
.cfbar{display:flex;flex-direction:column;align-items:center;justify-content:flex-end;height:100%;
  background:none;border:none;padding:0;cursor:pointer;font:inherit;color:inherit}
.cfv{font:600 .8125rem/1 var(--body);letter-spacing:.06em;color:var(--ink2);margin-bottom:14px}
.cff{--d:12px;position:relative;width:56%;max-width:84px;min-height:6px;margin-right:var(--d);
  border:1px solid var(--s);transform-origin:50% 100%;animation:grow .7s cubic-bezier(.16,1,.3,1) both}
/* the screen's one motion: each flow rises out of the baseline to its height, a beat apart. Opening a
   tab plays it; a value change on the same tab (.nofx) does not, and reduced motion never does */
@keyframes grow{from{transform:scaleY(0)}}
.cfbar:nth-child(2) .cff{animation-delay:.07s}.cfbar:nth-child(3) .cff{animation-delay:.14s}
.nofx .cff{animation:none!important}
@media (prefers-reduced-motion:reduce){.cff{animation:none}}
.cff svg{position:absolute;inset:0;width:100%;height:100%}
.cff::after{content:'';position:absolute;top:-1px;right:calc(var(--d) * -1 - 1px);width:var(--d);
  height:calc(100% + 1px);background:var(--s);transform-origin:left top;transform:skewY(45deg)}
.cff.in{background-color:var(--inF);--s:var(--inS)}
.cff.inv{background-color:var(--invF);--s:var(--invS)}
.cff.out{background-color:var(--outF);--s:var(--outS)}
.cfl{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:-10px}
.cfl span{text-align:center;font:600 .75rem/1 var(--body);letter-spacing:.2em;text-transform:uppercase;color:var(--ink3)}
.frow{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;width:100%;padding:22px 0;
  background:none;border:none;border-top:1px dashed var(--line2);text-align:left;cursor:pointer;
  font:inherit;color:inherit}
.frow:first-child{border-top:none}
.fn{font:500 1.25rem/1.3 var(--body)}
.fr{display:flex;flex-direction:column;align-items:flex-end;gap:8px}
.fa{display:flex;align-items:center;gap:12px;font:700 1.25rem/1.2 var(--body)}

/* ---- 3D donut: a ring on its own darker, ribbed edge ---- */
.d3{position:relative;width:260px;height:274px;margin:6px auto 0}
.d3e,.d3t{position:absolute;left:0;width:260px;height:260px;border-radius:50%;
  -webkit-mask:radial-gradient(circle,transparent 56%,#000 56.6%);mask:radial-gradient(circle,transparent 56%,#000 56.6%)}
.d3e{top:14px;filter:brightness(.42) saturate(1.2)}
.d3e::after{content:'';position:absolute;inset:0;border-radius:50%;
  background:repeating-conic-gradient(rgba(255,255,255,.18) 0 .45deg,transparent .45deg 2.4deg)}
.d3t{top:0;box-shadow:inset 0 0 0 1.5px var(--edge)}
.d3t::after{content:'';position:absolute;inset:0;border-radius:50%;box-shadow:inset 0 0 0 1.5px rgba(255,255,255,.9),inset 0 0 0 2.5px var(--edge)}

/* ---- top spends: avatar grid ---- */
.grid3{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:28px 12px}
.gcell{display:flex;flex-direction:column;align-items:center;gap:12px;background:none;border:none;
  padding:0;cursor:pointer;font:inherit;color:inherit;text-align:center}
.gcell .ic{width:min(84px,100%);height:auto;aspect-ratio:1}
.gcell .ic svg{width:32px;height:32px}
.gamt{font:700 1.0625rem/1.2 var(--body)}
.gnm{font:400 1rem/1.3 var(--body);color:var(--ink3);max-width:100%;overflow:hidden;
  display:-webkit-box;-webkit-line-clamp:2;line-clamp:2;-webkit-box-orient:vertical;box-orient:vertical}

/* ---- monthly bars with an AVG line (CRED's "past trends") ---- */
.tr{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px}
.tr>*{min-width:0}
.trl{display:flex;align-items:center;gap:12px;font:500 1.0625rem/1 var(--body);color:var(--ink2)}
.trl svg{width:24px;height:24px}
.chartwrap{overflow-x:auto;scrollbar-width:none;-webkit-overflow-scrolling:touch;margin:0 -4px}
.chartwrap::-webkit-scrollbar{display:none}
.chart{position:relative;display:flex;align-items:stretch;height:300px;padding-top:44px;min-width:max-content}
.bcol{position:relative;display:flex;flex-direction:column;align-items:center;width:var(--colw,62px);flex:none;height:100%;
  background:none;border:none;border-left:1px dashed var(--line2);padding:0;cursor:pointer;
  font:inherit;color:inherit}
.bcol:last-child{border-right:1px dashed var(--line2)}
.bwrap{position:relative;flex:1;width:100%;display:flex;align-items:flex-end;justify-content:center;
  border-bottom:1.5px solid var(--line2)}
.bwrap i{display:block;width:52%;background:var(--s2);transition:height .4s var(--ease)}
.bwrap i.on{background:var(--hl,var(--outS))}
.bcol:hover .bwrap i{background:var(--line2)}
.bcol:hover .bwrap i.on{background:var(--hl,var(--outS))}
.blab{font:600 .8125rem/1 var(--body);letter-spacing:.16em;color:var(--ink3);margin-top:14px}
.bval{font:700 .6875rem/1 var(--body);letter-spacing:.06em;color:var(--ink2);margin:8px 0 6px}
.bcol.sel .blab{color:var(--ink)}
/* the callout pinned to the newest bar */
.bcall{position:absolute;left:50%;transform:translate(-50%,-12px);background:var(--bg);
  border:1.5px solid var(--ink);padding:5px 9px;font:700 .8125rem/1 var(--body);letter-spacing:.1em;
  white-space:nowrap;z-index:3;color:var(--ink)}
.bcall::after{content:'';position:absolute;left:50%;bottom:-6px;width:9px;height:9px;background:var(--bg);
  border-right:1.5px solid var(--ink);border-bottom:1.5px solid var(--ink);transform:translateX(-50%) rotate(45deg)}
.avgzone{position:absolute;left:0;right:0;top:44px;bottom:53px;pointer-events:none;z-index:2}
.avgline{position:absolute;left:0;right:0;height:0;border-top:1.5px dotted var(--up);z-index:1;pointer-events:none}
.avgpill{position:absolute;right:96px;transform:translateY(50%);z-index:2;background:var(--bg);
  border:1.5px solid var(--up);border-radius:999px;padding:5px 14px;font:700 .75rem/1 var(--body);
  letter-spacing:.14em;color:var(--up);white-space:nowrap;pointer-events:none}

/* ---- filter bar on breakdown screens ---- */
.fbar{display:grid;grid-template-columns:1fr 1fr;border-top:1px solid var(--line);border-bottom:1px solid var(--line);
  margin:0 -20px}
.fsel{display:flex;align-items:center;justify-content:center;gap:8px;min-height:68px;padding:0 10px;
  background:none;border:none;color:var(--ink);cursor:pointer;font:600 1rem/1.2 var(--body);text-align:center}
.fsel+.fsel{border-left:1px solid var(--line)}
.fsel svg{width:16px;height:16px;flex:none}
@media (min-width:1100px){.fbar{margin:0}}

/* ---- period panel ---- */
.ppanel{display:flex;flex-direction:column;gap:12px}
.pwrap{display:flex;align-items:stretch;gap:8px}
.prow{flex:1;min-width:0;display:flex;gap:4px;padding:4px;border:1px solid var(--line2);border-radius:999px;
  overflow-x:auto;scrollbar-width:none;-webkit-overflow-scrolling:touch}
.prow::-webkit-scrollbar{display:none}
.pchip{flex:1 1 auto;min-width:42px;min-height:36px;padding:0 10px;border:none;border-radius:999px;
  background:transparent;color:var(--ink2);cursor:pointer;font:700 .75rem/1 var(--body);letter-spacing:.1em;
  text-transform:uppercase;white-space:nowrap;transition:background .16s var(--ease),color .16s var(--ease)}
.pchip:hover{color:var(--ink)}
.pchip.on{background:var(--ink);color:var(--bg)}
.pcustom{flex:none;display:flex;align-items:center;gap:6px;min-height:44px;padding:0 14px;border:1px solid var(--line2);
  border-radius:999px;background:transparent;color:var(--ink2);cursor:pointer;font:700 .75rem/1 var(--body);
  letter-spacing:.1em;text-transform:uppercase}
.pcustom svg{width:15px;height:15px}
.pcustom.on{background:var(--ink);border-color:var(--ink);color:var(--bg)}
.mpick{border:1px solid var(--line2);padding:14px}
.yrow{display:flex;gap:6px;overflow-x:auto;scrollbar-width:none;margin-bottom:12px}
.yrow::-webkit-scrollbar{display:none}
.ychip{flex:none;min-height:36px;padding:0 14px;border:1px solid var(--line2);border-radius:999px;background:transparent;
  color:var(--ink2);cursor:pointer;font:700 .75rem/1 var(--body);letter-spacing:.06em}
.ychip.on{background:var(--ink);border-color:var(--ink);color:var(--bg)}
.mgrid{display:grid;grid-template-columns:repeat(4,1fr);gap:6px}
.mcell{min-height:44px;border:1px solid var(--line);background:transparent;color:var(--ink);cursor:pointer;
  font:700 .75rem/1 var(--body);letter-spacing:.14em;text-transform:uppercase}
.mcell:hover{border-color:var(--ink3)}
/* a month with no statements is shown, not hidden: a gap in coverage is information */
.mcell.off{color:var(--ink3);opacity:.5;cursor:not-allowed;text-decoration:line-through}
.mcell.in{background:var(--sel)}
.mcell.end{background:var(--ink);color:var(--bg);border-color:var(--ink)}
.mfoot{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-top:12px}
.mhint{font:400 .8125rem/1.4 var(--body);color:var(--ink3)}
.mexact{flex:none;min-height:44px;background:none;border:none;color:var(--ink);cursor:pointer;
  font:700 .75rem/1 var(--body);letter-spacing:.12em;text-transform:uppercase;text-decoration:underline;text-underline-offset:5px}
.drow{display:flex;align-items:center;gap:8px;margin-top:10px}
.drow input[type=date]{flex:1;min-width:0;min-height:44px;padding:0 12px;border:1px solid var(--line2);background:var(--bg);
  color:var(--ink);font:500 1rem/1 var(--body);font-variant-numeric:tabular-nums}
.drow .to{color:var(--ink3)}
.nrow{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.nlbl{font:600 .6875rem/1 var(--body);letter-spacing:.16em;text-transform:uppercase;color:var(--ink3);margin-right:2px}
.nchip{min-height:36px;padding:0 14px;border:1px solid var(--line2);border-radius:999px;background:transparent;
  color:var(--ink2);cursor:pointer;font:600 .8125rem/1 var(--body);white-space:nowrap}
.nchip.on{border:2px solid var(--ink);color:var(--ink)}
.nsep{width:1px;height:20px;background:var(--line2);margin:0 2px}
.nnote{font:500 .8125rem/1.4 var(--body);color:var(--ink3)}
.nlink{display:inline-flex;align-items:center;min-height:36px;background:none;border:none;padding:0;cursor:pointer;
  font:500 .8125rem/1.4 var(--body);color:var(--ink);text-decoration:underline;text-underline-offset:4px}

/* ---- accounts ---- */
.acchead{display:flex;flex-direction:column;align-items:center;gap:12px;text-align:center;padding:4px 0}
.bm{width:56px;height:56px;flex:none;border-radius:50%;display:grid;place-items:center;background:var(--bg);
  border:1.5px solid var(--edge);box-shadow:0 4px 0 var(--edge);color:var(--bk,#2a7fd4);
  font:800 .75rem/1 var(--body);letter-spacing:.04em}
/* a bank's brand ink is chosen for white; on the dark disc it is lifted toward white or it can't be read */
[data-theme=dark] .bm{color:color-mix(in oklab,var(--bk,#2a7fd4) 45%,#fff)}
.arow{display:flex;align-items:center;gap:18px;width:100%;padding:22px 0;background:none;border:none;
  border-top:1px dashed var(--line2);text-align:left;cursor:pointer;font:inherit;color:inherit}
.arow:first-child{border-top:none}
.am{flex:1;min-width:0;display:flex;flex-direction:column;gap:8px}
.an{display:flex;align-items:center;gap:8px;font:700 1.0625rem/1.2 var(--body)}
.aa{display:flex;align-items:center;gap:8px;font:600 .75rem/1.2 var(--body);letter-spacing:.14em;text-transform:uppercase;color:var(--ink3)}
.aa i{flex:none;width:8px;height:8px;border-radius:50%;background:var(--gold)}
.ar{flex:none;display:flex;flex-direction:column;align-items:flex-end;gap:8px}
.abal{font:700 1.125rem/1.2 var(--body)}
.alink{font:700 .75rem/1.2 var(--body);letter-spacing:.14em;text-transform:uppercase;color:var(--link)}
/* loan / deposit rows: the account row's layout, but static (no detail screen yet), so no pointer */
.posrow{display:grid;grid-template-columns:auto minmax(0,1fr) auto;gap:6px 18px;align-items:baseline;
  padding:22px 0;border-top:1px dashed var(--line2)}
.posrow:first-child{border-top:none}
/* ?density=compact: NeoPOP's tighter scale, on trial against the default. Figures and headings about a
   quarter smaller, rows tighter; touch targets keep their 44px. */
[data-density=compact] .hero{font-size:2rem}
[data-density=compact] .txamt{font-size:2.25rem}
[data-density=compact] .ramt{font-size:1.625rem}
[data-density=compact] .h1,[data-density=compact] .txnm{font-size:1.375rem}
[data-density=compact] .h2{font-size:1.1875rem}
[data-density=compact] .fa,[data-density=compact] .fn{font-size:1.0625rem}
[data-density=compact] .abal{font-size:1rem}
[data-density=compact] .ra,[data-density=compact] .rn,[data-density=compact] .an,[data-density=compact] .gamt{font-size:.9375rem}
[data-density=compact] .bandtot .v{font-size:1.25rem}
[data-density=compact] .view{gap:20px}
[data-density=compact] .sheet{padding-top:18px}
[data-density=compact] .row{padding:10px 0}
[data-density=compact] .arow,[data-density=compact] .frow,[data-density=compact] .posrow{padding:14px 0}
[data-density=compact] .cfchart{height:220px}
[data-density=compact] .txh .ic,[data-density=compact] .gcell .ic{width:64px;height:64px}
[data-density=compact] .rcard .ic{width:60px;height:60px}
[data-density=compact] .rkv{padding:8px 24px}
/* buttons at NeoPOP's measured scale: 32px category buttons (11px bold, lowercase, 0.4px tracking,
   12px apart), 50px primary buttons, a 3px edge. Each small button keeps a 44px tap area by reaching
   6px into the gap around it, so it looks compact without becoming a smaller target. */
[data-density=compact] .tagwrap,[data-density=compact] .chips{gap:12px}
[data-density=compact] .tagchip,[data-density=compact] .pillb{position:relative;min-height:32px;padding:0 14px;gap:8px;
  font:700 .6875rem/1 var(--body);letter-spacing:.03em;text-transform:none}
[data-density=compact] .tagchip::after,[data-density=compact] .pillb::after{content:'';position:absolute;inset:-6px}
[data-density=compact] .tagchip svg,[data-density=compact] .pillb svg{width:14px;height:14px}
[data-density=compact] .tagbox{min-height:28px;padding:0 12px;font-size:.6875rem;letter-spacing:.08em}
[data-density=compact] .tsrch{min-height:44px;gap:12px;padding:0 14px}
[data-density=compact] .tsrch svg{width:18px;height:18px}
[data-density=compact] .np{--d:3px;min-height:50px;padding:0 24px;font-size:.875rem}
[data-density=compact] .actbar .np{min-height:50px}
.posrow>.ic{grid-row:1/span 3;align-self:start}
.posrow>.pmeta,.posrow>.pnote{grid-column:2/-1}
.pmeta{font:600 .75rem/1.5 var(--body);letter-spacing:.1em;text-transform:uppercase;color:var(--ink3)}
/* a caution on a loan or deposit row: sentence case, so it reads as a remark rather than a label */
.pnote{display:flex;gap:8px;align-items:flex-start;font:600 .875rem/1.4 var(--body);color:var(--gold)}
.pnote svg{width:16px;height:16px;flex:none;margin-top:2px}
/* a row read from a bank SMS / alert: real, but the monthly statement has not confirmed it yet */
.live{margin-left:8px;font:700 .625rem/1 var(--body);letter-spacing:.14em;text-transform:uppercase;color:var(--gold)}
.unrow{display:block;margin-top:6px;font-size:.875rem;color:var(--ink2)}
.sun{position:relative;margin:-24px -20px 0;height:150px;background:var(--sunbg);overflow:hidden;
  border-radius:18px 18px 0 0}
.sun::before{content:'';position:absolute;inset:-60% -10% 0;
  background:repeating-conic-gradient(from 0deg at 50% 100%,var(--ray) 0 .6deg,transparent .6deg 6deg)}
.sun::after{content:'';position:absolute;left:50%;bottom:-84px;width:220px;height:220px;border-radius:50%;
  transform:translateX(-50%);background:var(--bg);border:1.5px solid var(--goldline)}
.sun .bm{position:absolute;left:50%;bottom:4px;transform:translateX(-50%);z-index:2;width:96px;height:96px;font-size:1.125rem}
@media (min-width:1100px){.pane .sun{margin:-28px -40px 0;border-radius:20px 20px 0 0}}
.kv{display:grid;grid-template-columns:1fr 1fr;gap:18px 20px;padding:22px 24px;border:1.5px solid var(--goldline)}
.kv .k{font:600 .6875rem/1.3 var(--body);letter-spacing:.16em;text-transform:uppercase;color:var(--ink3)}
.kv .v{font:600 1rem/1.35 var(--body);margin-top:6px}
.kvline{display:flex;justify-content:space-between;align-items:flex-end;gap:12px;padding:18px 0;border-top:1px dashed var(--line2)}
.kvline:first-child{border-top:none}
.kvbig{font:700 1.5rem/1.1 var(--body);margin-top:8px}
.balbox{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:12px}
.balplot svg{display:block;width:100%;height:220px}
.balx{display:flex;justify-content:space-between;margin-top:12px}
.balx span{border:1.5px solid var(--ink);padding:6px 10px;font:700 .75rem/1 var(--body);letter-spacing:.16em;text-transform:uppercase}
.baly{display:flex;flex-direction:column;justify-content:space-between;height:220px;margin-top:-6px}
.baly span{font:600 .75rem/1 var(--body);letter-spacing:.08em;color:var(--ink3);text-align:right}

/* ---- recurring: a stacked deck ---- */
.deck{position:relative;margin:18px 22px 10px}
.deck .ghostc{position:absolute;inset:0;background:var(--bg);border:1.5px solid var(--ink);box-shadow:0 6px 0 var(--line2)}
.deck .g1{transform:rotate(-4deg) translate(-8px,6px)}
.deck .g2{transform:rotate(3deg) translate(10px,8px)}
.deck .g3{transform:rotate(-1.5deg) translate(-2px,12px)}
.rcard{position:relative;display:flex;flex-direction:column;align-items:center;gap:8px;width:100%;
  padding:18px 0 4px;background:var(--bg);border:1.5px solid var(--ink);box-shadow:0 6px 0 var(--line2);
  cursor:pointer;font:inherit;color:inherit}
.rcard .ic{width:76px;height:76px}
.rcard .ic svg{width:32px;height:32px}
.ramt{font:700 2.25rem/1.05 var(--body)}
.rnm2{font:700 .875rem/1.3 var(--body);letter-spacing:.2em;text-transform:uppercase;color:var(--ink3)}
.rkv{display:flex;justify-content:space-between;width:100%;padding:10px 28px;border-top:1px dashed var(--line2);
  font:700 .875rem/1.2 var(--body);letter-spacing:.18em;text-transform:uppercase;color:var(--ink3)}
.rkv b{color:var(--ink2);font-weight:700}
.rnav{display:flex;justify-content:center;align-items:center;gap:16px}
.rpos{text-align:center;font:700 .75rem/1 var(--body);letter-spacing:.16em;text-transform:uppercase;color:var(--ink2)}

/* ---- transaction detail ---- */
.txh{display:flex;flex-direction:column;align-items:center;gap:12px;text-align:center}
.txh .ic{width:84px;height:84px}
.txh .ic svg{width:34px;height:34px}
.txnm{font:400 1.75rem/1.15 var(--disp);letter-spacing:-.01em;text-wrap:balance;overflow-wrap:anywhere}
.txamt{font:700 3rem/1 var(--body)}
.txamt.in{color:var(--up)}
.tagbox{display:inline-flex;align-items:center;min-height:44px;padding:0 20px;border:1.5px solid var(--ink);
  font:700 .8125rem/1 var(--body);letter-spacing:.2em;text-transform:uppercase}
.from{display:flex;align-items:center;gap:10px;font:600 1.125rem/1.2 var(--body)}
.from i{width:28px;height:28px;border-radius:50%;background:var(--bk,#2a7fd4)}
.dash{border:none;border-top:1.5px dashed var(--line2);margin:0 -20px}
.narr{font:400 .875rem/1.45 var(--body);color:var(--ink3);overflow-wrap:anywhere;text-align:center}
.tsrch{display:flex;align-items:center;gap:16px;min-height:60px;padding:0 20px;border:1.5px solid var(--line2)}
.tsrch svg{width:26px;height:26px;color:var(--ink2);flex:none}
.tsrch input{flex:1;min-width:0;border:none;background:transparent;color:var(--ink);font:400 1rem/1 var(--body);outline:none}
.tsrch input::placeholder{color:var(--ink3)}
.tagwrap{display:flex;flex-wrap:wrap;gap:14px}
.tagchip{display:inline-flex;align-items:center;gap:16px;min-height:60px;padding:0 22px;border:1.5px solid var(--line2);
  background:var(--bg);color:var(--ink);cursor:pointer;font:700 .8125rem/1 var(--body);letter-spacing:.2em;
  text-transform:uppercase;transition:border-color .16s var(--ease),background .16s var(--ease)}
.tagchip svg{width:24px;height:24px;flex:none}
.tagchip:hover{border-color:var(--ink3)}
.tagchip.on{background:var(--ink);color:var(--bg);border-color:var(--ink)}
.actbar{position:sticky;bottom:0;z-index:4;display:grid;grid-template-columns:1fr 1fr;gap:16px;
  padding:16px 0 calc(16px + env(safe-area-inset-bottom,0px));background:var(--bg)}
.actbar .np{min-height:60px;width:calc(100% - 4px)}
.notefield{width:100%;min-height:96px;padding:14px 16px;border:1.5px solid var(--line2);background:var(--bg);color:var(--ink);
  font:400 1rem/1.5 var(--body);resize:vertical}
.notefield:focus,.sexact:focus,.search:focus,.simsel:focus{outline:none;border-color:var(--ink)}
.swrap{display:flex;flex-wrap:wrap;gap:10px;align-items:center}
.schip{min-height:44px;padding:0 18px;border:1.5px solid var(--line2);background:transparent;color:var(--ink);cursor:pointer;
  font:700 .875rem/1 var(--body);letter-spacing:.06em}
.schip.on{background:var(--ink);color:var(--bg);border-color:var(--ink)}
.schip.clear{border-color:transparent;color:var(--down);text-decoration:underline}
.sexact{flex:1;min-width:110px;min-height:44px;padding:0 14px;border:1.5px solid var(--line2);background:var(--bg);color:var(--ink);
  font:500 1rem/1 var(--body);font-variant-numeric:tabular-nums}
.srow{display:flex;justify-content:space-between;align-items:baseline;padding:10px 0;border-bottom:1px dashed var(--line2)}
.srow .l{font:600 .75rem/1 var(--body);letter-spacing:.16em;text-transform:uppercase;color:var(--ink3)}
.srow .sv{font:700 1.125rem/1 var(--body)}.srow .sr{font:700 1.125rem/1 var(--body);color:var(--up)}

/* ---- similar + bulk retag ---- */
.simrow{display:flex;align-items:center;gap:14px;padding:14px 0;border-top:1px dashed var(--line2);cursor:pointer}
.simrow:first-child{border-top:none}
.simrow input[type=checkbox]{width:20px;height:20px;accent-color:var(--ink);flex:none;cursor:pointer}
.simmain{flex:1;min-width:0;display:flex;flex-direction:column;gap:2px}
.simnm{font:600 .9375rem/1.3 var(--body);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.simsub{font:400 .8125rem/1.3 var(--body);color:var(--ink3)}
.simamt{font:700 .9375rem/1 var(--body);flex:none}
.simbar{display:flex;gap:12px;align-items:center;flex-wrap:wrap}
.simsel{flex:1;min-width:160px;min-height:52px;padding:0 14px;border:1.5px solid var(--line2);background:var(--bg);color:var(--ink);
  font:500 1rem/1 var(--body)}

/* ---- ledger + search ---- */
.thead{display:flex;justify-content:space-between;align-items:center;gap:12px}
.thead .h1{min-width:0}
.srchp{flex:none;display:inline-flex;align-items:center;gap:8px;min-height:48px;padding:0 18px 0 14px;border-radius:999px;
  border:1px solid var(--line2);background:var(--bg);color:var(--ink2);cursor:pointer;font:500 1rem/1 var(--body)}
.srchp svg{width:22px;height:22px;color:var(--ink)}
.search{width:100%;min-height:56px;padding:0 18px;border:1.5px solid var(--line2);background:var(--bg);color:var(--ink);
  font:400 1rem/1 var(--body)}
.dayh{position:sticky;top:0;z-index:2;background:var(--bg);padding:14px 0 6px;font:600 .75rem/1 var(--body);
  letter-spacing:.16em;text-transform:uppercase;color:var(--ink3)}
.fresh{display:flex;align-items:center;flex-wrap:wrap;gap:8px;font:400 1rem/1.3 var(--body);color:var(--ink2)}
.fresh svg{width:22px;height:22px}
.fresh.stale{color:var(--down)}
.fresh button{display:inline-flex;align-items:center;justify-content:center;min-height:44px;min-width:44px;margin:-10px 0;
  padding:0 6px;background:none;border:none;color:var(--ink);cursor:pointer;font:600 .875rem/1 var(--body);
  text-decoration:underline;text-underline-offset:4px}
.fresh .skipdot{text-decoration:none;color:var(--ink3);letter-spacing:2px}

/* ---- back ---- */
.back{display:inline-flex;align-self:flex-start;align-items:center;gap:12px;min-height:44px;padding:0 8px 0 0;margin:-6px 0 -10px;
  background:none;border:none;color:var(--ink);cursor:pointer;font:600 .75rem/1 var(--body);letter-spacing:.16em;
  text-transform:uppercase}
.back svg{width:44px;height:24px;stroke-width:1.5;transition:transform .18s var(--ease)}
.back:hover svg{transform:translateX(-3px)}

/* ---- bills ---- */
.bill{border:1.5px solid var(--line2);transition:border-color .18s var(--ease)}
.bill.open{border-color:var(--ink)}
.billhead{display:flex;flex-direction:column;gap:6px;width:100%;padding:18px 20px;background:none;border:none;
  text-align:left;cursor:pointer;font:inherit;color:inherit}
.bh1{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap}
.bpaid{font:700 1.375rem/1 var(--body)}
.bwhen{font:600 .75rem/1 var(--body);letter-spacing:.16em;text-transform:uppercase;color:var(--ink3)}
.bh2{font:400 .875rem/1.4 var(--body);color:var(--ink2)}
.bh3{display:flex;justify-content:space-between;align-items:center;font:600 .8125rem/1.3 var(--body);color:var(--ink3)}
.bh3.warn{color:var(--down)}
.billkids{border-top:1px dashed var(--line2);padding:4px 20px 10px}
.empty{padding:36px 0;text-align:center;font:400 1rem/1.5 var(--body);color:var(--ink3)}
.card2{border:1.5px solid var(--line2);padding:20px}
.flowbar{height:10px;background:var(--s2);display:flex;margin-top:12px}
.flowbar .bin{background:var(--up)}.flowbar .bout{background:var(--down);opacity:.8}
.cfee{font:400 .875rem/1.45 var(--body);color:var(--ink3);margin-top:10px}
.toast{position:fixed;left:50%;bottom:28px;transform:translate(-50%,16px);z-index:20;max-width:min(420px,calc(100vw - 32px));
  background:var(--np);color:var(--onnp);padding:14px 18px;font:500 .9375rem/1.45 var(--body);opacity:0;pointer-events:none;
  transition:opacity .25s var(--ease),transform .25s var(--ease);white-space:pre-line;max-height:60vh;overflow-y:auto}
.toast.on{opacity:1;transform:translate(-50%,0)}
.paneempty{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:12px;min-height:60vh;text-align:center}
</style>
</head>
<body>
<!-- the banknote weave the cash-flow bars are printed with; one pattern per flow so each takes its
     own line colour, and the colours are CSS variables so the weave follows the theme -->
<svg width="0" height="0" style="position:absolute" aria-hidden="true" focusable="false"><defs>
  <pattern id="wv-in" width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(-38)">
    <path d="M-1.25 2.5 Q0 .6 1.25 2.5 T3.75 2.5 T6.25 2.5" fill="none" style="stroke:var(--inL)" stroke-width=".7"/></pattern>
  <pattern id="wv-out" width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(-38)">
    <path d="M-1.25 2.5 Q0 .6 1.25 2.5 T3.75 2.5 T6.25 2.5" fill="none" style="stroke:var(--outL)" stroke-width=".7"/></pattern>
  <pattern id="wv-inv" width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(-38)">
    <path d="M-1.25 2.5 Q0 .6 1.25 2.5 T3.75 2.5 T6.25 2.5" fill="none" style="stroke:var(--invL)" stroke-width=".7"/></pattern>
</defs></svg>
<div class="app" id="app">
  <div class="col">
    <header class="band" id="band"></header>
    <main class="sheet" id="views"></main>
  </div>
  <aside class="pane" id="pane" aria-label="details"></aside>
</div>
<script type="application/json" id="data">__DATA__</script>
<script>
const DATA=JSON.parse(document.getElementById('data').textContent),M=DATA.meta||{},ALL=DATA.txns||[],CUR=M.currency||'INR';
DATA.insights=DATA.insights||[];

/* ---- formatting ---- */
function fmt(p,o){o=o||{};let neg=p<0;p=Math.abs(Math.round(p||0));let w=Math.floor(p/100),f=String(p%100).padStart(2,'0');
  let s=String(w),out;if(s.length>3){let h=s.slice(0,-3),t=s.slice(-3),ps=[];while(h.length>2){ps.unshift(h.slice(-2));h=h.slice(0,-2);}if(h)ps.unshift(h);out=ps.join(',')+','+t;}else out=s;
  let sym=CUR==='INR'?'₹':'';return (neg?'−':(o.sign?'+':''))+sym+out+(o.noP?'':'.'+f);}
/* Rupees at full weight, paise dimmed: ₹97,000.00 reads as "97 thousand" at a glance. The paise are
   still there — a typographic change, never a rounding one, so every figure reconciles to the paisa.
   Returns HTML, so it must not be passed through esc(). */
function fmtH(p,o){const s=fmt(p,o),i=s.lastIndexOf('.');
  return i<0?esc(s):esc(s.slice(0,i))+'<span class="ps">'+esc(s.slice(i))+'</span>';}
function fmtK(p){let r=Math.abs(p||0)/100,sym=CUR==='INR'?'₹':'',g=p<0?'−':'';
  if(r>=1e7)return g+sym+(r/1e7).toFixed(2)+'Cr';if(r>=1e5)return g+sym+(r/1e5).toFixed(2)+'L';
  if(r>=1e3)return g+sym+(r/1e3).toFixed(2)+'K';return g+sym+Math.round(r);}
const esc=s=>String(s==null?'':s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
/* For a value going inside a single-quoted onclick argument: escaping keeps the key intact, where
   stripping an apostrophe would mutate it and "DOMINO'S" would open an empty screen. */
const escArg=s=>esc(s).replace(/\\/g,'\\\\').replace(/'/g,"\\'");
const MON=['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec'];
function shortDate(d){if(!d)return'';const [y,m,dd]=d.split('-');return `${+dd} ${MON[+m-1]} '${y.slice(2)}`;}
function dayLabel(d){if(!d||!M.max_date)return esc(d);
  const a=new Date(d+'T00:00:00Z'),b=new Date(M.max_date+'T00:00:00Z'),diff=Math.round((b-a)/864e5);
  if(diff===0)return'today';if(diff===1)return'yesterday';
  return a.toLocaleDateString('en-IN',{day:'numeric',month:'short',year:'numeric',timeZone:'UTC'});}
function ord(n){const s=['th','st','nd','rd'],v=n%100;return n+(s[(v-20)%10]||s[v]||s[0]);}
function hl(s){return esc(s).replace(/(₹[\d,]+(?:\.\d+)?(?:Cr|L|k|K)?)/g,'<b>$1</b>');}

/* ---- icons: one outline family, 1.6 stroke, drawn for this app ---- */
const IC={
  bank:'<path d="M3 9.5 12 4l9 5.5"/><path d="M4 9.5h16"/><path d="M5.5 10.5v6.5M9.5 10.5v6.5M14.5 10.5v6.5M18.5 10.5v6.5"/><path d="M3.5 17.5h17M3 20.5h18"/>',
  txns:'<path d="M4 9V5.5A1.5 1.5 0 0 1 5.5 4h13A1.5 1.5 0 0 1 20 5.5V12"/><path d="M20 15.5v3A1.5 1.5 0 0 1 18.5 20h-13A1.5 1.5 0 0 1 4 18.5V12.5"/><path d="M2.5 10.5 4 9l1.5 1.5M21.5 14 20 15.5 18.5 14"/><path d="M9 8h6M9 10.5h6M9.8 8c3 0 3 4.5 0 4.5H9l4.2 4"/>',
  recur:'<rect x="3.5" y="5" width="13" height="13" rx="1.5"/><path d="M3.5 9h13M7 3v4M13 3v4"/><circle cx="17" cy="16.5" r="4.2"/><path d="M17 14.7v2l1.3.9"/>',
  flow:'<rect x="3.5" y="13" width="4" height="7"/><rect x="10" y="8.5" width="4" height="11.5"/><rect x="16.5" y="4" width="4" height="16"/>',
  lock:'<rect x="5" y="11" width="14" height="9.5" rx="1.5"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/><path d="M12 14.5v2.5"/>',
  unlock:'<rect x="5" y="11" width="14" height="9.5" rx="1.5"/><path d="M8 11V8a4 4 0 0 1 7.6-1.7"/><path d="M12 14.5v2.5"/>',
  theme:'<circle cx="12" cy="12" r="8.5"/><path d="M12 3.5a8.5 8.5 0 0 1 0 17z" fill="currentColor" stroke="none"/>',
  chev:'<path d="M9 5.5 15.5 12 9 18.5"/>',chevd:'<path d="M5.5 9 12 15.5 18.5 9"/>',
  back:'<path d="M42 12H3M9 6l-6 6 6 6"/>',
  star:'<path d="M12 3.5l2.6 5.4 5.9.8-4.3 4.2 1 5.8L12 17l-5.2 2.7 1-5.8-4.3-4.2 5.9-.8z" fill="currentColor"/>',
  srch:'<circle cx="10.5" cy="10.5" r="6.5"/><path d="M20 20l-4.8-4.8"/>',
  spark:'<circle cx="12" cy="12" r="8.5"/><path d="M13 6.5 9 12.8h3l-1 4.7 4-6.3h-3z" fill="currentColor" stroke="none"/>',
  clock:'<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/>',
  refresh:'<path d="M19.5 12a7.5 7.5 0 1 1-2.2-5.3"/><path d="M19.5 4v4.5H15"/>',
  cal:'<rect x="3.5" y="5" width="17" height="15.5" rx="1.5"/><path d="M3.5 9.5h17M8 3v4M16 3v4"/>',
  bars:'<rect x="3.5" y="3.5" width="17" height="17" rx="1"/><path d="M8 16.5V11M12 16.5V8M16 16.5v-4"/>',
  apps:'<rect x="4" y="4" width="6.5" height="6.5" rx="1"/><rect x="13.5" y="4" width="6.5" height="6.5" rx="1"/><rect x="4" y="13.5" width="6.5" height="6.5" rx="1"/><path d="M16.75 13.5v6.5M13.5 16.75H20"/>',
  bill:'<path d="M6 3.5h12v17l-2-1.3-2 1.3-2-1.3-2 1.3-2-1.3-2 1.3z"/><path d="M9 8h6M9 11h6M9 14h4"/>',
  cash:'<rect x="3.5" y="4" width="17" height="10" rx="1.5"/><rect x="7.5" y="9" width="9" height="11" rx="1"/><circle cx="12" cy="14.5" r="2"/>',
  card:'<rect x="3" y="5.5" width="18" height="13" rx="1.5"/><path d="M3 9.5h18M6.5 14.5h4"/>',
  gift:'<path d="M4 9.5 12 4l8 5.5V19a1.5 1.5 0 0 1-1.5 1.5h-13A1.5 1.5 0 0 1 4 19z"/><path d="M4 10.5l8 5.5 8-5.5"/>',
  edu:'<path d="M4 5.5C6.5 4.5 9.5 4.5 12 6c2.5-1.5 5.5-1.5 8-.5v13c-2.5-1-5.5-1-8 .5-2.5-1.5-5.5-1.5-8-.5z"/><path d="M12 6v13"/>',
  play:'<rect x="3.5" y="4.5" width="17" height="11.5" rx="1.5"/><path d="M8 20h8M12 16v4"/><path d="M10.5 7.8v5l4-2.5z"/>',
  food:'<path d="M4.5 11a7.5 4.5 0 0 1 15 0z"/><path d="M4 14h16"/><path d="M5 17h14a1.5 1.5 0 0 1-1.5 2.5h-11A1.5 1.5 0 0 1 5 17z"/>',
  transfer:'<rect x="6" y="3.5" width="11" height="17" rx="1.5"/><path d="M10 17.5h3"/><rect x="11.5" y="7.5" width="8.5" height="6" rx="1"/>',
  gov:'<path d="M6 3.5h12v17l-2-1.3-2 1.3-2-1.3-2 1.3-2-1.3-2 1.3z"/><path d="M9.5 8h5M9.5 10.5h5M10.2 8c2.5 0 2.5 3.6 0 3.6h-.6l3.2 3.2"/>',
  grocery:'<path d="M4 10h16l-1.6 8.6a1.5 1.5 0 0 1-1.5 1.2H7.1a1.5 1.5 0 0 1-1.5-1.2z"/><path d="M8.5 10l2.5-5.5M15.5 10 13 4.5"/><path d="M9 13.5v3M12 13.5v3M15 13.5v3"/>',
  health:'<path d="M12 20s-7.5-4.4-7.5-10A4.3 4.3 0 0 1 12 7.3 4.3 4.3 0 0 1 19.5 10c0 5.6-7.5 10-7.5 10z"/><path d="M6.5 12h3l1.5-2.5 2 5 1.5-2.5h3"/>',
  shield:'<path d="M12 3.5l7 2.5v5.5c0 4.5-3 7.8-7 9-4-1.2-7-4.5-7-9V6z"/><path d="M12 8.5l1.2 2.4 2.6.4-1.9 1.8.5 2.6-2.4-1.3-2.4 1.3.5-2.6-1.9-1.8 2.6-.4z"/>',
  invest:'<path d="M3.5 20.5h17"/><rect x="5" y="13" width="3.5" height="5"/><rect x="10.25" y="9" width="3.5" height="9"/><rect x="15.5" y="5" width="3.5" height="13"/>',
  loan:'<path d="M9.5 3.5h5l-1.4 3h-2.2z"/><path d="M10.9 6.5h2.2c3.9 2 6.4 5.7 6.4 9 0 3-2.5 5-7.5 5s-7.5-2-7.5-5c0-3.3 2.5-7 6.4-9z"/><path d="M10 16.4l4-4.6"/><circle cx="10.2" cy="12.3" r=".9"/><circle cx="13.8" cy="16" r=".9"/>',
  person:'<circle cx="12" cy="12" r="8.5"/><circle cx="12" cy="10" r="3"/><path d="M6.9 18.2c1.2-2.1 3-3.2 5.1-3.2s3.9 1.1 5.1 3.2"/>',
  work:'<rect x="3.5" y="7.5" width="17" height="12" rx="1.5"/><path d="M9 7.5v-2h6v2M3.5 12.5h17M10.5 12.5v2h3v-2"/>',
  home:'<path d="M4 10.5 12 4l8 6.5V20H4z"/><path d="M9.5 20v-5h5v5"/>',
  self:'<circle cx="12" cy="7.5" r="3.5"/><path d="M5 20c.8-3.8 3.5-6 7-6s6.2 2.2 7 6"/><path d="M12 21v-4.5M10.2 18.3l1.8-1.8 1.8 1.8"/>',
  cart:'<path d="M3 4.5h2.5l2 10.5h10l2-7.5H6.5"/><circle cx="9" cy="19" r="1.3"/><circle cx="16.5" cy="19" r="1.3"/>',
  car:'<path d="M5.5 16.5v2.5M18.5 16.5v2.5"/><path d="M4 16.5V12l1.8-5A1.5 1.5 0 0 1 7.2 6h9.6a1.5 1.5 0 0 1 1.4 1l1.8 5v4.5z"/><path d="M4 12h16"/><circle cx="7.5" cy="14.2" r=".8"/><circle cx="16.5" cy="14.2" r=".8"/>',
  travel:'<rect x="5" y="3.5" width="14" height="17" rx="1.5"/><circle cx="12" cy="10.5" r="3.5"/><path d="M8.5 10.5h7M12 7c-1.4 1-1.4 6 0 7M12 7c1.4 1 1.4 6 0 7M9 17h6"/>',
  dots:'<circle cx="8" cy="8" r="3"/><circle cx="16" cy="8" r="3"/><circle cx="8" cy="16" r="3"/><circle cx="16" cy="16" r="3"/>',
  repeat:'<path d="M17 3l3.5 3.5L17 10"/><path d="M3.5 11V9.5a3 3 0 0 1 3-3h14"/><path d="M7 21l-3.5-3.5L7 14"/><path d="M20.5 13v1.5a3 3 0 0 1-3 3h-14"/>',
  trend:'<path d="M3 17l6-6 4 4 8-8"/><path d="M21 7v5h-5"/>',
  receipt:'<path d="M6 3.5h12v17l-2-1.3-2 1.3-2-1.3-2 1.3-2-1.3-2 1.3z"/><path d="M9 8h6M9 12h6"/>',
  crown:'<path d="M3.5 8l4 4 4.5-6.5 4.5 6.5 4-4v10.5h-17z"/>',
  check:'<circle cx="12" cy="12" r="8.5"/><path d="M8 12.3l2.7 2.7L16 9.5"/>',
  copy:'<rect x="9" y="9" width="11" height="11" rx="1.5"/><path d="M5 15V5.5A1.5 1.5 0 0 1 6.5 4H15"/>',
  dot:'<circle cx="12" cy="12" r="8.5"/>'};
function I(n){return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${IC[n]||IC.dot}</svg>`;}
/* the tag vocabulary carries an icon per tag; fall back to keyword guesses for anything legacy */
const TAGICON=Object.fromEntries((DATA.tag_vocab||[]).map(v=>[v.tag,v.icon]));
function catIcon(c){if(TAGICON[c])return TAGICON[c];c=(c||'').toLowerCase();
  if(/food|dining/.test(c))return'food';if(/grocer/.test(c))return'grocery';if(/rent|home/.test(c))return'home';
  if(/bill|utilit/.test(c))return'bill';if(/invest/.test(c))return'invest';if(/card/.test(c))return'card';
  if(/cash|atm/.test(c))return'cash';if(/loan|emi/.test(c))return'loan';if(/salary/.test(c))return'cash';
  if(/people|transfer/.test(c))return'person';if(/interest/.test(c))return'trend';if(/refund/.test(c))return'repeat';
  if(/cashback|reward/.test(c))return'gift';return'dots';}

/* Banks are identified by a monogram on a coloured disc rather than their logos: the colour is the
   recognisable part, and the repo ships no third-party marks. */
const BANKHUE={sbi:'#2a7fd4',hdfc:'#0f3c8c',icici:'#a8322d',rbl:'#1b2d6e',bob:'#e2571e',baroda:'#e2571e',axis:'#97144d',
  kotak:'#d71920',scapia:'#5b3fd6',yes:'#0060a9',idfc:'#9c1d26',federal:'#1d4f91',au:'#e0711b'};
function bankKey(acc){return String(acc||'').toLowerCase().split(/[\s•]+/)[0]||'';}
function bankHue(acc){const k=bankKey(acc);if(BANKHUE[k])return BANKHUE[k];
  let h=0;for(const c of k)h=(h*31+c.charCodeAt(0))%360;return `hsl(${h} 55% 40%)`;}
function bankMono(acc){return esc((String(acc||'?').split(/[\s•]+/)[0]||'?').slice(0,4).toUpperCase());}
function bankDisc(acc,cls){return `<span class="bm ${cls||''}" style="--bk:${bankHue(acc)}" aria-hidden="true">${bankMono(acc)}</span>`;}
function iconDisc(icon,acc,init){
  const badge=`<span class="bb"><i style="--bk:${bankHue(acc||M.account)}"></i></span>`;
  return init?`<span class="ic init" aria-hidden="true">${esc(init)}${badge}</span>`
             :`<span class="ic" aria-hidden="true">${I(icon)}${badge}</span>`;}

/* ---- netting modes ----
   'gross' — every row as the bank printed it; the only view that reconciles line by line.
   'clean' — drop CANCELLED pairs (money that left and came straight back: error correction).
   'net'   — additionally net off everyone money moved both ways with. Both transfers were real, so this
             is a preference, not a correction, and never the default.
   A pair is only dropped when BOTH legs are inside the selected period. */
let NET='gross';
let SHARE='billed';
function shareRows(rows){if(SHARE!=='mine')return rows;return rows.map(t=>t.mine==null?t:{...t,a:t.mine,split:1});}
function setShare(s){SHARE=s;draw();}
function splitInfo(rows){let n=0,billed=0,mine=0;for(const t of rows){if(t.mine==null)continue;n++;billed+=t.a;mine+=t.mine;}
  return {n,billed,mine,recoverable:billed-mine};}
function netFilter(rows){
  if(NET==='gross')return rows;
  const have=new Set(rows.map(t=>t.ref));
  const drop=new Set();
  for(const t of rows)if(t.rev&&have.has(t.rev)){drop.add(t.ref);drop.add(t.rev);}
  let out=rows.filter(t=>!drop.has(t.ref));
  if(NET!=='net')return out;
  /* one synthetic row per two-way person carrying only the NET direction: shrinking individual rows
     would produce amounts that appear on no statement */
  const by={};
  for(const t of out){if(!t.cp)continue;(by[t.cp]=by[t.cp]||[]).push(t);}
  const netted=[];const consumed=new Set();
  for(const cp in by){
    const rs=by[cp];
    const paid=rs.filter(t=>t.dir==='D').reduce((s,t)=>s+t.a,0);
    const got=rs.filter(t=>t.dir==='C').reduce((s,t)=>s+t.a,0);
    if(!paid||!got)continue;
    rs.forEach(t=>consumed.add(t.ref));
    const diff=paid-got;
    if(diff===0)continue;
    const last=rs.slice().sort((a,b)=>(a.d<b.d?-1:1)).slice(-1)[0];
    netted.push({...last,a:Math.abs(diff),dir:diff>0?'D':'C',
                 f:last.f==='v'?'v':(diff>0?'s':'i'),
                 m:(last.cpn||last.m||cp)+' (net)',synthetic:1});}
  return out.filter(t=>!consumed.has(t.ref)).concat(netted);}

/* ---- compute (integer paise) ----
   Three-way flow, mirroring the server: self-transfers ('x') are excluded from BOTH sides, and
   investments ('v') are kept out of `out` so "spent" never counts money you still own. An investment
   row is signed: money back FROM a broker nets against what went in. */
const sa=t=>t.f==='v'&&t.dir==='C'?-t.a:t.a;
function inRange(t,f,tt){return (!f||t.d>=f)&&(!tt||t.d<=tt);}
function compute(rows){let inn=0,out=0,inv=0,slf=0,slfN=0,invIn=0,invBack=0;
  const catT={},catC={},merT={},merC={},recMon={},recAmt={},moOut={},merName={};
  const srcT={},srcC={},moIn={},moInv={},invT={},invC={},invN={},spT={},spC={};
  for(const t of rows){
    if(t.f==='x'){slf+=t.a;slfN++;continue;}
    if(t.f==='i'){inn+=t.a;
      const s=t.src||'Other income';srcT[s]=(srcT[s]||0)+t.a;srcC[s]=(srcC[s]||0)+1;
      if(t.mo)moIn[t.mo]=(moIn[t.mo]||0)+t.a;
      continue;}
    if(t.f==='v'){const v=sa(t);inv+=v;if(v<0)invBack-=v;else invIn+=v;
      const raw=t.m||t.c||'Other',k=raw.trim().toLowerCase();
      invT[k]=(invT[k]||0)+v;invC[k]=(invC[k]||0)+1;invN[k]=invN[k]||raw;
      if(t.mo)moInv[t.mo]=(moInv[t.mo]||0)+v;}
    else{out+=t.a;if(t.mo)moOut[t.mo]=(moOut[t.mo]||0)+t.a;spT[t.c]=(spT[t.c]||0)+t.a;spC[t.c]=(spC[t.c]||0)+1;}
    catT[t.c]=(catT[t.c]||0)+sa(t);catC[t.c]=(catC[t.c]||0)+1;
    if(t.m){const mk=t.m.trim().toLowerCase();
      merT[mk]=(merT[mk]||0)+sa(t);merC[mk]=(merC[mk]||0)+1;merName[mk]=merName[mk]||t.m;
      (recMon[mk]=recMon[mk]||new Set()).add(t.mo);(recAmt[mk]=recAmt[mk]||[]).push(t.a);}}
  const cats=Object.keys(catT).map(c=>({c,a:catT[c],n:catC[c]})).sort((x,y)=>y.a-x.a);
  const catTotal=cats.reduce((s,c)=>s+c.a,0);
  const med=a=>{const s=a.slice().sort((x,y)=>x-y),n=s.length;return n?(n%2?s[(n-1)/2]:(s[n/2-1]+s[n/2])/2):0;};
  const recurring=Object.keys(recMon).filter(m=>recMon[m].size>=3)
    .map(m=>({m:merName[m],months:recMon[m].size,med:med(recAmt[m]),total:merT[m]}))
    .sort((a,b)=>b.total-a.total).slice(0,6);
  const bal=rows.filter(t=>t.b!=null).slice(-1)[0];
  const nMo=Object.keys(moOut).length||1;
  /* Ranked breakdowns with an honest tail: the remainder folds into a labelled "Other" row rather than
     being sliced off, so the parts still sum to the total. */
  const rank=(tot,cnt,total,limit,names)=>{
    const out=Object.keys(tot).map(k=>({k:(names&&names[k])||k,a:tot[k],n:cnt[k],
                                        share:total?tot[k]/total:0}))
                              .sort((x,y)=>y.a-x.a);
    if(out.length<=limit)return out;
    const tail=out.slice(limit-1);
    return out.slice(0,limit-1).concat([{k:`Other (${tail.length} sources)`,
      a:tail.reduce((s,r)=>s+r.a,0),n:tail.reduce((s,r)=>s+r.n,0),
      share:tail.reduce((s,r)=>s+r.share,0)}]);};
  const nMoIn=Object.keys(moIn).length||1;
  return {inn,out,inv,invIn,invBack,slf,slfN,cats,catTotal,recurring,closing:bal?bal.b:null,count:rows.length,
          moOut,moIn,moInv,months:nMo,avgOut:Math.round(out/nMo),avgIn:Math.round(inn/nMoIn),
          srcs:rank(srcT,srcC,inn,6),invs:rank(invT,invC,inv,6,invN),spends:rank(spT,spC,out,7),
          mers:Object.keys(merT).map(k=>({k,name:merName[k],a:merT[k],n:merC[k]}))
                     .sort((x,y)=>y.a-x.a)};}

/* ---- period control ---- */
let RANGE='all',CF='',CT='',SORT='high';
function monthsBack(n){if(!M.max_date)return'';const d=new Date(M.max_date+'T00:00:00Z');d.setUTCMonth(d.getUTCMonth()-n);return d.toISOString().slice(0,10);}
/* salary cycle: the window your money actually resets on, not the calendar month */
function salaryCycle(){if(!M.salary_day||!M.max_date)return null;
  const d=new Date(M.max_date+'T00:00:00Z'),day=M.salary_day;
  const clamp=(y,m)=>{let dd=Math.min(day,new Date(Date.UTC(y,m+1,0)).getUTCDate());return new Date(Date.UTC(y,m,dd));};
  let s=clamp(d.getUTCFullYear(),d.getUTCMonth());
  if(d<s)s=clamp(d.getUTCFullYear(),d.getUTCMonth()-1);
  const iso=x=>x.toISOString().slice(0,10);return {f:iso(s),t:M.max_date};}
/* A preset is [key, label, span]. span is 'Nd' (days) or 'Nm' (calendar months), null = everything. */
const PRESETS=[['W','1W','7d'],['M','1M','1m'],['3M','3M','3m'],['6M','6M','6m'],
               ['Y','1Y','12m'],['5Y','5Y','60m'],['all','All',null]];
function presetFrom(key){
  const p=PRESETS.find(x=>x[0]===key);
  if(!p||!p[2]||!M.max_date)return '';
  const n=parseInt(p[2],10);
  return p[2].slice(-1)==='d' ? shiftDays(M.max_date,-(n-1)) : monthsBack(n);}
/* period -> netting -> share. Every screen goes through here, so no view can disagree about the mode. */
function rangeFilter(){return shareRows(netFilter(periodRows()));}
function periodRows(){
  if(RANGE==='C')return ALL.filter(t=>t.d&&inRange(t,CF,CT));
  if(RANGE==='S'){const c=salaryCycle();return c?ALL.filter(t=>t.d&&inRange(t,c.f,c.t)):ALL;}
  const from=presetFrom(RANGE);
  if(!from)return ALL;
  return ALL.filter(t=>t.d&&t.d>=from);}
/* the period in CRED's chip wording: "30 jul '26 – 11 aug '26", or the preset's name */
function periodText(){
  if(RANGE==='S'){const c=salaryCycle();return c?`${shortDate(c.f)} – ${shortDate(c.t)}`:'salary cycle';}
  if(RANGE==='C'){if(!CF&&!CT)return 'all time';
    if(CF&&CT)return `${shortDate(CF)} – ${shortDate(CT)}`;return CF?`since ${shortDate(CF)}`:`up to ${shortDate(CT)}`;}
  return {W:'last 7 days',M:'last month','3M':'last 3 months','6M':'last 6 months',Y:'last year','5Y':'last 5 years',all:'all time'}[RANGE]||'';}
function rangeLabel(){return '· '+periodText();}
let PERIODOPEN=false;
function togglePeriod(){PERIODOPEN=!PERIODOPEN;draw();}
/* The whole period control: presets, then Cycle if a salary day was detected, then custom. */
function rangeRow(){
  const chips=PRESETS.map(([k,l])=>
      `<button class="pchip ${RANGE===k?'on':''}" onclick="setR('${k}')">${l}</button>`).join('');
  const cycle=M.salary_day
      ? `<button class="pchip ${RANGE==='S'?'on':''}" onclick="setR('S')" title="your salary cycle, not the calendar month">Cycle</button>` : '';
  const custom=`<button class="pcustom ${RANGE==='C'?'on':''}" onclick="setR('C')" title="pick months or exact dates">${I('cal')}Custom</button>`;
  return `<div class="ppanel"><div class="pwrap"><div class="prow">${chips}${cycle}</div>${custom}</div>
    ${RANGE==='C'?monthPicker():''}${netRow()}</div>`;}

/* ---- month picker: the statement app's real unit is the MONTH ---- */
let PICKYEAR=null, PICKANCHOR=null;
const MONTHNAMES=MON;
function monthsWithData(){
  if(!monthsWithData._c)monthsWithData._c=new Set(ALL.map(t=>t.mo).filter(Boolean));
  return monthsWithData._c;}
function pickYears(){
  const ys=[...new Set([...monthsWithData()].map(m=>m.slice(0,4)))].sort();
  return ys.length?ys:[String(new Date().getUTCFullYear())];}
function monthPicker(){
  const have=monthsWithData(), years=pickYears();
  if(PICKYEAR===null||!years.includes(PICKYEAR))
    PICKYEAR=(CF&&years.includes(CF.slice(0,4)))?CF.slice(0,4):years[years.length-1];
  const yTabs=years.map(y=>
    `<button class="ychip ${y===PICKYEAR?'on':''}" onclick="setPickYear('${y}')">${y}</button>`).join('');
  const cells=MONTHNAMES.map((nm,i)=>{
    const mo=`${PICKYEAR}-${String(i+1).padStart(2,'0')}`;
    const has=have.has(mo);
    const inR=CF&&CT&&mo>=CF.slice(0,7)&&mo<=CT.slice(0,7);
    const isEnd=(CF&&mo===CF.slice(0,7))||(CT&&mo===CT.slice(0,7));
    return `<button class="mcell ${has?'':'off'} ${inR?'in':''} ${isEnd?'end':''}"
       ${has?`onclick="pickMonth('${mo}')"`:'disabled aria-disabled="true"'}
       title="${has?mo:mo+' — no transactions'}">${nm}</button>`;}).join('');
  const hint=PICKANCHOR
      ? `<span class="mhint">tap another month to end the range, or the same one again for just ${esc(PICKANCHOR)}</span>`
      : '<span class="mhint">tap a month, or two to span a range</span>';
  return `<div class="mpick">
    <div class="yrow">${yTabs}</div>
    <div class="mgrid">${cells}</div>
    <div class="mfoot">${hint}<button class="mexact" onclick="toggleExact()">exact dates</button></div>
    ${EXACT?`<div class="drow">
      <input id="dt-from" type="date" value="${CF}" max="${M.max_date||''}" onchange="setCF(this.value)" aria-label="from">
      <span class="to">→</span>
      <input id="dt-to" type="date" value="${CT}" max="${M.max_date||''}" onchange="setCT(this.value)" aria-label="to">
    </div>`:''}
  </div>`;}
let EXACT=false;
function toggleExact(){EXACT=!EXACT;draw();}
function setPickYear(y){PICKYEAR=y;draw();}
function pickMonth(mo){
  if(!PICKANCHOR){PICKANCHOR=mo;CF=monthStart(mo);CT=monthEnd(mo);RANGE='C';draw();return;}
  const [a,b]=[PICKANCHOR,mo].sort();
  CF=monthStart(a);CT=monthEnd(b);PICKANCHOR=null;RANGE='C';draw();}

/* The netting control — rendered only when the data HAS something to net. */
function netRow(){
  const c=countable();
  const sp=splitInfo(periodRows());
  if(!c.pairs&&!c.people&&!sp.n)return '';
  const b=(k,lbl,title)=>`<button class="nchip ${NET===k?'on':''}" onclick="setNet('${k}')" title="${title}">${lbl}</button>`;
  const chips=[b('gross','everything','every row exactly as the bank printed it — the only view that reconciles line by line')]
    .concat(c.pairs?[b('clean','skip refunded',`${c.pairs} charge${c.pairs!==1?'s':''} that came straight back`)]:[])
    .concat(c.people?[b('net','settle up friends',`${c.people} people you both paid and got money back from`)]:[]);
  const share=sp.n?`<span class="nsep"></span>
    <button class="nchip ${SHARE==='billed'?'on':''}" onclick="setShare('billed')" title="the full amount the bank billed">billed</button>
    <button class="nchip ${SHARE==='mine'?'on':''}" onclick="setShare('mine')" title="${sp.n} shared charge${sp.n!==1?'s':''} · ${fmtK(sp.recoverable)} is someone else's">my share</button>`:'';
  return `<div class="nrow"><span class="nlbl">counting</span>${chips.join('')}${share}${netNote(c)}${shareNote(sp)}</div>`;}
function shareNote(sp){if(SHARE!=='mine'||!sp.n)return '';
  return `<span class="nnote">−${fmtK(sp.recoverable)} recoverable from others</span>`;}
/* what the current mode removed, in money — a mode that silently shrinks every total is the thing
   this codebase is most careful about, and the figure is inspectable, not asserted */
function netNote(c){
  if(NET==='gross')return '';
  const amt=NET==='clean'?c.cancelledAmt:c.cancelledAmt+c.offsetAmt;
  const what=NET==='clean'?'cancelled':'cancelled &amp; settled';
  return `<button class="nlink" onclick="openDetail('netting')">−${fmtK(amt)} ${what} · what?</button>`;}
function countable(){
  const rows=periodRows(),have=new Set(rows.map(t=>t.ref));
  let pairs=0,cancelledAmt=0;const seen=new Set();
  for(const t of rows){
    if(!t.rev||!have.has(t.rev)||seen.has(t.ref))continue;
    seen.add(t.ref);seen.add(t.rev);pairs++;cancelledAmt+=t.a;}
  const by={};
  for(const t of rows){if(t.cp)(by[t.cp]=by[t.cp]||[]).push(t);}
  let people=0,offsetAmt=0;
  for(const cp in by){
    const paid=by[cp].filter(t=>t.dir==='D').reduce((s,t)=>s+t.a,0);
    const got=by[cp].filter(t=>t.dir==='C').reduce((s,t)=>s+t.a,0);
    if(paid&&got){people++;offsetAmt+=Math.min(paid,got);}}
  return {pairs,cancelledAmt,people,offsetAmt};}
function setNet(m){NET=m;draw();}

/* ---- which side of the flow a breakdown shows ---- */
let FLOW='out';
const FLOWS={out:{label:'spends',key:'out',avg:'avgOut'},
             in:{label:'incoming',key:'inn',avg:'avgIn'},
             inv:{label:'investments',key:'inv',avg:null}};
const FLOWORDER=['in','inv','out'];      // CRED's order: incoming, investments, spends
function heroValue(R){
  const f=FLOWS[FLOW]||FLOWS.out;
  return {label:M.is_card&&FLOW==='out'?'charged':f.label,amount:R[f.key],avg:(f.avg&&R.months>1)?R[f.avg]:0};}
/* Every bar and row on the cash-flow tab is the control that opens that flow's breakdown. */
function setFlow(f){FLOW=f;openDetail('breakdown');}
/* a card is charged and paid off; money does not flow "out" of it */
function tabLabel(f){
  if(M.is_card)return {in:'paid off',out:'charged',inv:'invested'}[f]||f;
  return {in:'money in',out:'money out',inv:'invested'}[f]||f;}

/* ---- comparisons ---- */
const FLOW_CODE={out:'s',in:'i',inv:'v'};
function flowBetween(from,to,code){
  return netFilter(ALL.filter(t=>t.d&&t.d>=from&&t.d<=to))
         .filter(t=>t.f===code).reduce((s,t)=>s+sa(t),0);}
function shiftDays(iso,n){const d=new Date(iso+'T00:00:00Z');d.setUTCDate(d.getUTCDate()+n);
  return d.toISOString().slice(0,10);}
function currentWindow(){
  const dated=ALL.filter(t=>t.d).map(t=>t.d).sort();
  if(!dated.length)return null;
  const rows=rangeFilter().filter(t=>t.d).map(t=>t.d).sort();
  if(!rows.length)return null;
  return {from:rows[0], to:rows[rows.length-1], first:dated[0]};}
/* Compare like with like: the same span of days immediately before the selected range, same flow. */
function heroDelta(R){
  const w=currentWindow();
  if(!w)return '';
  const days=Math.round((new Date(w.to)-new Date(w.from))/864e5)+1;
  const prevTo=shiftDays(w.from,-1), prevFrom=shiftDays(prevTo,-(days-1));
  if(prevFrom<w.first)return '';
  const prev=flowBetween(prevFrom,prevTo,FLOW_CODE[FLOW]||'s');
  if(prev<=0)return '';
  const now=heroValue(R).amount;
  const pc=Math.round((now/prev-1)*100), up=pc>0;
  const good=FLOW==='out'?!up:up;
  const label=days<=8?'week':days<=32?'month':days<=95?'quarter':days<=370?'year':`${days} days`;
  return `<div class="subd"><span class="${good?'up':'down'}">${up?'↑':'↓'} ${Math.abs(pc)}%</span> vs previous ${label} · <span class="num">${fmt(prev)}</span></div>`;}

/* "2026-07" -> the first and last day of that month, computed, since month lengths differ */
function monthStart(mo){return mo+'-01';}
function monthEnd(mo){const [y,m]=mo.split('-').map(Number);
  return `${mo}-${String(new Date(Date.UTC(y,m,0)).getUTCDate()).padStart(2,'0')}`;}
function openMonth(mo){
  const f=monthStart(mo),t=monthEnd(mo);
  if(RANGE==='C'&&CF===f&&CT===t){RANGE='all';}
  else{CF=f;CT=t;RANGE='C';}
  draw();}

/* ---- the header band ---- */
let HUSH=false;
try{HUSH=localStorage.getItem('sl-hush')==='1';}catch(_){}
function toggleHush(){HUSH=!HUSH;try{localStorage.setItem('sl-hush',HUSH?'1':'0');}catch(_){}draw();}
const MAIN=[['accounts','bank','accounts'],['txns','txns','transactions'],['recurring','recur','recurring'],['cashflow','flow','cash flow']];
function totalBalance(){return (M.accounts||[]).filter(a=>!a.is_card&&a.balance!=null).reduce((s,a)=>s+a.balance,0);}
function band(){
  const el=document.getElementById('band');if(!el)return;
  const tot=totalBalance();
  const pill=(M.accounts||[]).some(a=>a.balance!=null)
    ? `<div class="balpill"><span class="l">total balance</span><span class="v num">${fmtH(tot)}</span></div>`
    : `<div class="balpill"><span class="l">${esc(M.account||'')}</span><span class="v num">${(M.txn_count||0)} rows</span></div>`;
  /* on the Accounts list the sheet's hero is the total balance, so the pill would only repeat it */
  const heroIsTotal=TAB==='accounts'&&(WIDE.matches||!DET)&&(M.accounts||[]).some(a=>a.balance!=null);
  el.innerHTML=`<div class="btop">
      <button class="av" onclick="TT()" title="switch between light and dark" aria-label="switch between light and dark">${I('theme')}</button>
      ${heroIsTotal?`<div class="bandtot"><span class="l">total balance</span><span class="v fig num">${fmtH(tot)}</span></div>`:pill}
      <button class="lock ${HUSH?'on':''}" onclick="toggleHush()" aria-pressed="${HUSH}"
        aria-label="${HUSH?'show amounts':'hide amounts'}" title="${HUSH?'show amounts':'hide amounts'}">${I(HUSH?'lock':'unlock')}</button>
    </div>
    <nav class="tabs" role="tablist" aria-label="sections">${MAIN.map(([k,ic,lbl])=>
      `<button class="tab ${TAB===k?'on':''}" role="tab" aria-selected="${TAB===k}" onclick="go('${k}')">${I(ic)}<span>${lbl}</span></button>`).join('')}</nav>`;
  document.getElementById('app').classList.toggle('hush',HUSH);}

/* freshness — an aggregator's credibility rests on how current its data is */
function showFreshness(){const s=M.sync||{},el=document.getElementById('fresh');if(!el)return;
  const parts=[];
  /* a store filled from a folder has statements but no mail-sync record: say how current the data
     is rather than "never synced" in red over rows that are plainly there */
  const last=(M.accounts||[]).map(a=>a.date_max).filter(Boolean).sort().pop();
  const imported=s.label==='never synced'&&last;
  if(imported)parts.push('statements to '+esc(shortDate(last)));
  else{if(s.label)parts.push(esc(s.label));if(s.reason)parts.push(esc(s.reason));}
  el.className='fresh'+(s.stale&&!imported?' stale':'');
  const detail=(s.skipped_reasons||[]).filter(Boolean).length
      ? ' <button class="skipdot" onclick="showSkipped()" title="some files in the mailbox aren\'t statements — tap to see which">·&#8202;·&#8202;·</button>' : '';
  el.innerHTML=I('bank')+(parts.join(' · ')||'synced from your statements')+detail+(API?' <button onclick="doRefresh(this)">refresh</button>':'');}
function showSkipped(){toast((M.sync.skipped_reasons||[]).filter(Boolean).join('\n\n'));}
function doRefresh(b){if(!API)return;b.disabled=true;b.textContent='checking…';
  post('/api/refresh',{}).then(r=>{
    if(r&&r.error){b.disabled=false;b.textContent='refresh';return toast(r.error);}
    if(r&&r.reason&&!r.ok){b.disabled=false;b.textContent='refresh';return toast(r.reason);}
    if(r&&(r.inserted||r.duplicate))location.reload();
    else{b.textContent='up to date';setTimeout(()=>{b.disabled=false;b.textContent='refresh';},2200);}
  });}

/* ---- account switching: each account is its own dataset, so switching is a page load ---- */
function accHref(acc,view){return `?t=${encodeURIComponent(API||'')}&a=${encodeURIComponent(acc)}${view?'&v='+view:''}`;}
function stashScroll(){try{sessionStorage.setItem('sl-scroll',window.scrollY)}catch(_){}}
function accChips(){
  const list=M.accounts||[];
  if(list.length<2)return '';
  return `<div class="chiprow">${list.map(a=>{const on=a.account===M.account;
    return `<a class="achip ${on?'on':''}" href="${accHref(a.account,'txns')}" onclick="stashScroll()"
        title="${esc(a.account)} · ${a.count} transactions">${bankDisc(a.account)}<span>${esc(a.account)}</span></a>`;}).join('')}</div>`;}
function openAccount(acc){if(acc===M.account){openDetail('account');return;}
  stashScroll();location.href=accHref(acc,'account');}
function restoreScroll(){
  let y=null;
  try{y=sessionStorage.getItem('sl-scroll');sessionStorage.removeItem('sl-scroll');}catch(_){}
  if(y==null)return;
  const target=Math.min(+y, document.body.scrollHeight-window.innerHeight);
  if(target>0)window.scrollTo(0,target);}

/* ---- shared pieces ---- */
function backBtn(onclick,dest){
  return `<button class="back" onclick="${onclick}" aria-label="${dest?'back to '+esc(dest):'back'}">${I('back')}<span>${dest?esc(dest):''}</span></button>`;}
/* a breakdown screen's two filters: which account, which period — CRED's split bar */
function filterBar(){
  return `<div class="fbar">
    <button class="fsel" onclick="go('accounts')">${esc(M.account||'account')} ${I('chevd')}</button>
    <button class="fsel" onclick="togglePeriod()">${RANGE==='S'?`<span style="color:var(--gold)">${I('star')}</span>`:''}${esc(periodText())} ${I('chevd')}</button></div>
    ${PERIODOPEN?rangeRow():''}`;}
function txRow(t,withDate){const isIn=t.f==='i';
  const split=t.mine!=null?`split · ${fmtK(t.mine)} mine`:null;
  const sub=[t.c,t.f==='x'?'self':null,split,t.note?'note':null].filter(Boolean).join(' · ');
  return `<button class="row" onclick="openTxn('${escArg(t.ref)}')">${iconDisc(catIcon(t.c))}
    <span class="rm"><span class="rn">${esc(t.m||t.desc)}</span><span class="rs">${esc(sub)}${t.p?'<span class="live" title="from a bank SMS or alert; the monthly statement will confirm it">live</span>':''}</span></span>
    <span class="rr"><span class="ra num ${isIn?'in':''}">${isIn?'+':''}${fmtH(t.a)}</span>${withDate?`<span class="rd">${esc(shortDate(t.d))}</span>`:''}</span>
    <span class="chev">${I('chev')}</span></button>`;}
function dayGrouped(rows){if(!rows.length)return'<div class="empty">nothing in this period</div>';
  let out='',day='';
  rows.forEach(t=>{if(t.d!==day){if(day)out+='</div>';day=t.d;out+=`<div class="dayh">${dayLabel(t.d)}</div><div class="rlist">`;}
    out+=txRow(t);});
  return out+'</div>';}
function slfNote(R){return R.slfN?`<div class="note">${I('spark')}<span>self-transfers and card bill payments are left out of both sides · <span class="num">${fmtK(R.slf)}</span> across ${R.slfN} transactions</span></div>`:'';}

/* ---- donut: one hue stepped by rank, standing on a darker ribbed edge ---- */
function isDark(){return document.documentElement.dataset.theme!=='light';}
const HUE={out:[61,16,82],in:[13,42,140],inv:[124,53,24]};
const HUE_TO={out:[233,196,247],in:[198,213,250],inv:[247,214,200]};
function tint(flow,i,n){
  const a=HUE[flow]||HUE.out,b=HUE_TO[flow]||HUE_TO.out;
  const f=n<=1?0:i/(n-1);
  /* on the dark sheet the biggest share takes the brightest step and the ramp stops at a mid tone;
     run dark-first there and the largest slice is the one that vanishes into the background */
  const [lo,hi]=isDark()?[b,a.map((v,k)=>v+(b[k]-v)*.45)]:[a,b];
  const m=k=>Math.round(lo[k]+(hi[k]-lo[k])*f*.92);
  return `rgb(${m(0)},${m(1)},${m(2)})`;}
function donut(rows,total){
  if(rows.length<1||total<=0)return '';
  let acc=0;const stops=rows.map((s,i)=>{
    const from=acc/total*100;acc+=Math.max(0,s.a);const to=acc/total*100;
    return `${tint(FLOW,i,rows.length)} ${from.toFixed(2)}% ${to.toFixed(2)}%`;}).join(',');
  return `<div class="d3" aria-hidden="true"><div class="d3e" style="background:conic-gradient(${stops})"></div>
    <div class="d3t" style="background:conic-gradient(${stops})"></div></div>`;}
/* `by` says what the keys ARE: income groups by SOURCE (a tag), investments by MERCHANT — sending a
   merchant to openTag() lands on an empty screen, clickable but broken. */
function breakdownCard(rows,total,title,label,by){
  if(!rows.length)return `<div class="empty">nothing in this period</div>`;
  const n=rows.length;
  const open=by==='merchant'?'openMerchant':'openTag';
  const list=rows.map((s,i)=>{
    const real=!/^Other \(\d+ sources\)$/.test(s.k);
    const sw=`<span class="lsw" style="background:${tint(FLOW,i,n)}"></span>`;
    const body=`${sw}<span class="lm"><span class="ln">${esc(s.k)}</span><span class="lp">${(s.share*100).toFixed(2)}%</span></span>
      <span class="la num"><span>${fmtH(s.a)}</span>${real?`<span class="chev">${I('chev')}</span>`:''}</span>`;
    return real?`<button class="lrow" onclick="${open}('${escArg(s.k)}')">${body}</button>`
               :`<div class="lstatic">${body}</div>`;}).join('');
  return `${donut(rows,total)}<section aria-label="${esc(title)}" class="rlist">${list}</section>`;}
function sourceCard(R){return breakdownCard(R.srcs,R.inn,'where it came from','incoming','tag');}
function investCard(R){
  const back=R.invBack?`<div class="note">${I('spark')}<span><span class="num">${fmtH(R.invIn)}</span> went in · <span class="num">${fmtH(R.invBack)}</span> came back from brokers · net <span class="num">${fmtH(R.inv)}</span></span></div>`:'';
  return back+breakdownCard(R.invs,R.inv,'what you put away','invested','merchant');}
function spendCard(R){return breakdownCard(R.spends,R.out,'where it went','spends','tag');}

/* ---- top spends: who you are paying ---- */
function topSpendsGrid(R){
  const top=R.mers.filter(m=>m.a>0).slice(0,6);
  if(top.length<3)return '';
  const cells=top.map(m=>`<button class="gcell" onclick="openMerchant('${escArg(m.name)}')">
      ${iconDisc(catIcon(rowCat(m.name)))}
      <span class="gamt num">${fmtH(m.a)}</span><span class="gnm">${esc(m.name)}</span></button>`).join('');
  return `<div class="st"><h2>top spends</h2></div><div class="grid3">${cells}</div>
    <button class="ulink" onclick="SORT='high';openDetail('search')">View all</button>`;}
function rowCat(merchant){const t=ALL.find(x=>x.m===merchant);return t?t.c:'';}

/* ---- past trends: monthly bars with an AVG line ----
   Built from the whole history, not the selected period: the chart is the SELECTOR, so filtering it
   by its own selection is circular (a selected month left one bar, which hid the chart, which hid the
   only control that could undo the click). It follows the flow; the selected month is highlighted. */
const MOKEY={out:'moOut',in:'moIn',inv:'moInv'};
let TREND='month';
function toggleTrend(){TREND=TREND==='month'?'todate':'month';draw();}
function byMonth(rows,pick){
  /* "till date" compares each month only up to the same day of the month as the newest data, so a
     partial current month is weighed against equal partial months instead of looking like a collapse */
  const cut=M.max_date?+M.max_date.slice(8,10):31,out={};
  for(const t of rows){if(!t.mo||!pick(t))continue;if(TREND==='todate'&&+t.d.slice(8,10)>cut)continue;
    out[t.mo]=(out[t.mo]||0)+sa(t);}
  return out;}
function monthChart(rows,pick,hlColor){
  const by=byMonth(rows,pick),keys=Object.keys(by).sort();
  if(keys.length<2)return '';
  const vals=keys.map(k=>by[k]),peak=Math.max(...vals,1),avg=Math.round(vals.reduce((s,v)=>s+v,0)/vals.length);
  const avgPct=Math.max(0,Math.min(100,avg/peak*100));
  const bars=keys.map((k,i)=>{const h=Math.max(1.5,Math.max(0,by[k])/peak*100),last=i===keys.length-1;
    const on=RANGE==='C'&&CF===monthStart(k)&&CT===monthEnd(k);
    return `<button class="bcol ${on?'sel':''}" onclick="openMonth('${escArg(k)}')" aria-label="${esc(k)} · ${esc(fmt(by[k]))} — show this month">
      <span class="bwrap"><i class="${last||on?'on':''}" style="height:${h}%">${last?`<span class="bcall num" style="bottom:${h}%">${fmtK(by[k])}</span>`:''}</i></span>
      <span class="blab">${MON[+k.slice(5)-1].toUpperCase()}</span><span class="bval num">${fmtK(by[k])}</span></button>`;}).join('');
  return `<div class="chartwrap" id="chartwrap" style="--hl:${hlColor}"><div class="chart">
      <span class="avgzone"><span class="avgline" style="bottom:${avgPct}%"></span>
      <span class="avgpill num" style="bottom:${avgPct}%">AVG ${fmtK(avg)}</span></span>${bars}</div></div>`;}

/* ================= the four tabs ================= */

/* ---- accounts ---- */
function accountsV(){
  const accs=M.accounts&&M.accounts.length?M.accounts:[{account:M.account,count:M.txn_count,is_card:M.is_card,balance:null,date_max:M.max_date}];
  const banks=accs.filter(a=>!a.is_card),cards=accs.filter(a=>a.is_card);
  const row=a=>`<button class="arow" onclick="openAccount('${escArg(a.account)}')">${bankDisc(a.account)}
     <span class="am"><span class="an">${esc(a.account)}<span class="chev">${I('chev')}</span></span>
       <span class="aa"><i></i>${a.count} transactions</span></span>
     <span class="ar">${a.balance!=null?`<span class="abal num">${fmtH(a.balance)}</span><span class="alink">as of ${esc(shortDate(a.balance_on))}</span>`
                                       :`<span class="alink">to ${esc(shortDate(a.date_max))}</span>`}</span></button>`;
  return `<div class="view">
    <div class="acchead"><div class="fresh" id="fresh"></div></div>
    ${banks.length?`<div class="st"><h2>bank accounts</h2></div><div class="rlist">${banks.map(row).join('')}</div>`:''}
    ${cards.length?`<div class="st"><h2>credit cards</h2></div><div class="rlist">${cards.map(row).join('')}</div>`:''}
    ${(M.positions||[]).length?`<div class="st"><h2>loans &amp; deposits</h2></div><div class="rlist">${M.positions.map(posRow).join('')}</div>`:''}
  </div>`;}

/* Loans and deposits are positions: what is owed or held as of a statement date. They sit beside the
   balances and never enter the total or the cash flow, because every EMI and the FD's funding are
   already debits on the account that paid them. */
function posRow(p){
  const today=new Date().toISOString().slice(0,10);
  if(p.kind==='loan'){
    const left=p.emis_left!=null?`${p.emis_left} of ${p.tenure_months} EMIs left`:`${p.tenure_months} months`;
    /* the newest statement predates the due date, so whether that EMI was collected is unknown here:
       say so, rather than implying it was paid */
    const due=p.next_due&&p.next_due<today&&p.as_of<p.next_due
      ?`<span class="pnote">${I('clock')}<span>the ${esc(shortDate(p.next_due))} EMI isn't in a statement yet. check it was collected</span></span>`
      :p.next_due?`<span class="pmeta">next EMI ${esc(shortDate(p.next_due))}</span>`:'';
    return `<div class="posrow">${iconDisc('loan',p.lender)}<span class="an">${esc(p.label)}</span><span class="abal num">${fmtH(p.outstanding)}</span>
      <span class="pmeta">owed on ${esc(shortDate(p.as_of))} · EMI <span class="num">${fmtH(p.emi)}</span> · ${left} · ${p.rate_pct}%</span>${due}</div>`;}
  /* DICGC insures ₹5L per bank, interest included. A renewing FD rolls principal + interest into the
     next term, so project that term at the same growth and say when it would outgrow the cover */
  const next=p.principal&&p.renews?Math.round(p.maturity_amount*p.maturity_amount/p.principal):0;
  const cover=next>50000000?`<span class="pnote">${I('shield')}<span>renews automatically. at this rate the next term ends near ${fmtK(next)}, past the ₹5L DICGC cover per bank</span></span>`:'';
  return `<div class="posrow">${iconDisc('invest',p.bank)}<span class="an">${esc(p.label)}</span><span class="abal num">${fmtH(p.principal)}</span>
    <span class="pmeta">deposited ${esc(shortDate(p.value_date))} · ${p.rate_pct}% · matures ${esc(shortDate(p.maturity_date))} at <span class="num">${fmtH(p.maturity_amount)}</span></span>${cover}</div>`;}

/* one account: CRED's account page — sunburst header, balance, what it earned, how it moved */
let BALMODE='close';
function toggleBalMode(){BALMODE=BALMODE==='close'?'peak':'close';draw();}
function accountV(){
  const a=(M.accounts||[]).find(x=>x.account===M.account)||{account:M.account};
  const yr=M.max_date?M.max_date.slice(0,4):'';
  const interest=ALL.filter(t=>t.f==='i'&&/interest/i.test(t.src||t.c||'')&&t.d&&t.d.startsWith(yr)).reduce((s,t)=>s+t.a,0);
  const R=compute(ALL);
  const recent=ALL.slice().reverse().slice(0,3).map(t=>txRow(t,true)).join('');
  const figure=a.balance!=null?a.balance:(M.is_card&&DATA.card?DATA.card.charges:R.out);
  return `<div class="view">
    <div class="sun">${bankDisc(M.account)}</div>
    <div class="heroc"><div class="cap capk">${esc(M.account)}</div>
      <div class="hero fig num">${fmtH(figure)}</div>
      <div class="cap">${a.balance!=null?`balance on ${esc(shortDate(a.balance_on))}`:(M.is_card?'charged · all time':'spent · all time')}</div>
      ${API?`<button class="np ghost" onclick="doRefresh(this)">${I('refresh')}Check for new statements</button>`:''}</div>
    <div class="kv"><div><div class="k">statements from</div><div class="v">${esc(shortDate(M.min_date))}</div></div>
      <div><div class="k">through</div><div class="v">${esc(shortDate(M.max_date))}</div></div>
      <div><div class="k">transactions</div><div class="v num">${M.txn_count||ALL.length}</div></div>
      <div><div class="k">kind</div><div class="v">${M.is_card?'credit card':'savings account'}</div></div></div>
    ${!M.is_card?`<div class="st"><h2>interest summary</h2></div>
      <div class="rlist"><div class="kvline"><div><div class="sub">total interest earned in ${esc(yr)}</div>
        <div class="kvbig num">${fmtH(interest)}</div></div></div></div>`:''}
    ${!M.is_card?balanceHistory():''}
    ${M.is_card&&(DATA.bill_cycles||[]).length?`<button class="np" onclick="openDetail('bills')">See what each bill paid for</button>`:''}
    <div class="st"><h2>recent transactions</h2></div><div class="rlist">${recent||'<div class="empty">no transactions yet</div>'}</div>
    <button class="ulink" onclick="openDetail('search')">See all transactions</button>
  </div>`;}

/* balance history: month-end (or monthly peak) balances as a smooth line over a soft fill. The line is
   SVG stretched to the box; the axis labels are HTML so they keep their size at any width — SVG text
   scales with the viewBox and came out at 7px on a phone. */
function balanceHistory(){
  const by={};
  for(const t of ALL){if(t.b==null||!t.mo)continue;const k=t.mo;
    if(BALMODE==='peak')by[k]=Math.max(by[k]==null?-Infinity:by[k],t.b);else by[k]=t.b;}
  const keys=Object.keys(by).sort().slice(-13);
  if(keys.length<2)return '';
  const vals=keys.map(k=>by[k]),top=Math.max(...vals)*1.15||1;
  const W=1000,H=400,x=i=>i*W/(keys.length-1),y=v=>H-(v/top)*H;
  const pts=vals.map((v,i)=>[x(i),y(v)]);
  /* Catmull-Rom through the points as cubic Béziers: smooth, and still through every month's value */
  let d=`M${pts[0][0].toFixed(1)} ${pts[0][1].toFixed(1)}`;
  for(let i=0;i<pts.length-1;i++){const p0=pts[i-1]||pts[i],p1=pts[i],p2=pts[i+1],p3=pts[i+2]||p2;
    const c1=[p1[0]+(p2[0]-p0[0])/6,p1[1]+(p2[1]-p0[1])/6],c2=[p2[0]-(p3[0]-p1[0])/6,p2[1]-(p3[1]-p1[1])/6];
    d+=` C${c1[0].toFixed(1)} ${c1[1].toFixed(1)},${c2[0].toFixed(1)} ${c2[1].toFixed(1)},${p2[0].toFixed(1)} ${p2[1].toFixed(1)}`;}
  const area=`${d} L${W} ${H} L0 ${H} Z`;
  const grid=keys.map((_,i)=>`<line x1="${x(i).toFixed(1)}" x2="${x(i).toFixed(1)}" y1="0" y2="${H}" vector-effect="non-scaling-stroke" style="stroke:var(--line);stroke-width:1"/>`).join('');
  const ticks=[1,.75,.5,.25,0].map(f=>`<span class="num">${fmtK(Math.round(top*f))}</span>`).join('');
  return `<div class="st"><h2>balance history</h2><button class="pillb" onclick="toggleBalMode()">${BALMODE==='close'?'month end':'monthly peaks'} ${I('chev')}</button></div>
    <div class="balbox"><div class="balplot">
      <svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" role="img" aria-label="${BALMODE==='close'?'month-end':'peak'} balance, ${esc(shortDate(monthStart(keys[0])))} to ${esc(shortDate(monthStart(keys[keys.length-1])))}">
        ${grid}<path d="${area}" style="fill:var(--s2)"/><path d="${d}" vector-effect="non-scaling-stroke" style="fill:none;stroke:var(--ink);stroke-width:2"/></svg>
      <div class="balx"><span>${esc(shortDate(monthStart(keys[0])))}</span><span>${esc(shortDate(monthStart(keys[keys.length-1])))}</span></div></div>
      <div class="baly">${ticks}</div></div>`;}

/* ---- transactions ---- */
/* live payments the statement for their month did not confirm: kept out of every total, shown here */
function unsettledNote(){const U=M.unsettled||[];if(!U.length)return '';
  return `<div class="note">${I('clock')}<span><b>${U.length} live ${U.length>1?'payments':'payment'} never reached a statement.</b>
    a failed or reversed payment looks like this, so ${U.length>1?'they are':'it is'} left out of your totals. check ${U.length>1?'each one':'it'}:
    ${U.map(u=>`<span class="unrow"><span class="num">${u.direction==='credit'?'+':''}${fmtH(u.minor)}</span> · ${esc(shortDate(u.date))} · ${esc(u.description)}</span>`).join('')}</span></div>`;}
function txnsV(){
  const rows=rangeFilter().slice().reverse();
  const c=countable();
  return `<div class="view">
    <div class="thead"><h1 class="h1">your transactions</h1>
      <button class="srchp" onclick="openDetail('search')">${I('srch')}search</button></div>
    <div class="fresh" id="fresh"></div>
    ${unsettledNote()}
    ${accChips()}
    <div class="rlist">${rows.slice(0,8).map(t=>txRow(t,true)).join('')||'<div class="empty">no transactions yet</div>'}</div>
    <button class="np ghost vall" onclick="openDetail('search')">View all</button>
    ${M.is_card&&(DATA.bill_cycles||[]).length?`<div class="st"><h2>card bills</h2></div>
      <button class="row" onclick="openDetail('bills')">${iconDisc('card')}<span class="rm"><span class="rn">what each bill paid for</span>
        <span class="rs">${(DATA.bill_cycles||[]).filter(b=>b.paid).length} payments, opened into their charges</span></span><span class="chev">${I('chev')}</span></button>`:''}
    ${c.pairs||c.people?`<div class="st"><h2>netting</h2></div>
      <button class="row" onclick="openDetail('netting')">${iconDisc('repeat')}<span class="rm"><span class="rn">cancelled &amp; two-way money</span>
        <span class="rs">${c.pairs} cancelled pair${c.pairs!==1?'s':''} · ${c.people} ${c.people===1?'person':'people'} both ways</span></span><span class="chev">${I('chev')}</span></button>`:''}
  </div>`;}

/* ---- recurring: a deck, one detected payment at a time ---- */
let RECDIR='out',RECI=0;
function setRecDir(d){RECDIR=d;RECI=0;draw();}
function recStep(n){RECI=RECI+n;draw();}
function incomingRecurring(){
  const by={};
  for(const t of ALL){if(t.f!=='i'||!t.m)continue;const k=(t.cp||t.m).toLowerCase();(by[k]=by[k]||[]).push(t);}
  const med=a=>{const s=a.slice().sort((x,y)=>x-y),n=s.length;return n?(n%2?s[(n-1)/2]:Math.round((s[n/2-1]+s[n/2])/2)):0;};
  return Object.values(by).map(rs=>{const months=new Set(rs.map(t=>t.mo));if(months.size<3)return null;
      const days=rs.map(t=>+t.d.slice(8,10)).sort((a,b)=>a-b);
      return {merchant:rs[0].cpn||rs[0].m,months:months.size,median:med(rs.map(t=>t.a)),usual_day:days[Math.floor(days.length/2)],
              active:rs.some(t=>t.d>=monthsBack(2)),next_expected:null};})
    .filter(Boolean).sort((a,b)=>b.median*b.months-a.median*a.months);}
function recurringV(){
  const list=(RECDIR==='out'?(DATA.recurring||[]):incomingRecurring()).filter(r=>r.active);
  const n=list.length;RECI=((RECI%Math.max(n,1))+Math.max(n,1))%Math.max(n,1);
  const r=list[RECI];
  const deck=r?`<div class="deck"><span class="ghostc g1"></span><span class="ghostc g2"></span><span class="ghostc g3"></span>
      <button class="rcard" onclick="openMerchant('${escArg(r.merchant)}')">${iconDisc(catIcon(rowCat(r.merchant)))}
        <span class="ramt num">${fmtH(r.median)}</span><span class="rnm2">${esc(r.merchant)}</span>
        <span class="rkv"><span>${RECDIR==='out'?'from':'into'}:</span><b>${esc(M.account)}</b></span>
        <span class="rkv"><span>usually ${RECDIR==='out'?'paid':'arrives'} by:</span><b>${ord(r.usual_day)}</b></span>
        <span class="rkv"><span>seen:</span><b>${r.months} months</b></span>
        ${r.next_expected?`<span class="rkv"><span>next:</span><b>~${esc(shortDate(r.next_expected))}</b></span>`:''}</button></div>
    <div class="rpos">${RECI+1} out of ${n}</div>
    <div class="rnav"><button class="np ghost" onclick="recStep(-1)" ${n<2?'disabled':''}>Previous</button>
      <button class="np" onclick="recStep(1)" ${n<2?'disabled':''}>Next</button></div>`
    :`<div class="empty">no recurring ${RECDIR==='out'?'payments':'credits'} detected yet</div>`;
  const all=list.map(x=>`<button class="row" onclick="openMerchant('${escArg(x.merchant)}')">${iconDisc(catIcon(rowCat(x.merchant)))}
      <span class="rm"><span class="rn">${esc(x.merchant)}</span><span class="rs">${x.months} months · the ${ord(x.usual_day)}</span></span>
      <span class="rr"><span class="ra num">${fmtH(x.median)}</span></span><span class="chev">${I('chev')}</span></button>`).join('');
  return `<div class="view">
    <div><h1 class="h1">recurring payments</h1><div class="cap" style="margin-top:10px"><span class="num">${n}</span> detected from your statements</div></div>
    <div class="chips"><button class="pillb ${RECDIR==='out'?'on':''}" onclick="setRecDir('out')">outgoing</button>
      <button class="pillb ${RECDIR==='in'?'on':''}" onclick="setRecDir('in')">incoming</button>
</div>
    ${deck}
    ${n?`<div class="st"><h2>all ${RECDIR==='out'?'outgoing':'incoming'}</h2></div><div class="rlist">${all}</div>`:''}
  </div>`;}

/* ---- cash flow ---- */
let CYCLENOTE=true;
try{CYCLENOTE=localStorage.getItem('sl-cyclenote')!=='seen';}catch(_){}
function dismissCycle(){CYCLENOTE=false;try{localStorage.setItem('sl-cyclenote','seen');}catch(_){}draw();}
function sixMonthTotal(code){const from=monthsBack(6);
  return netFilter(ALL.filter(t=>t.d&&t.d>=from)).filter(t=>t.f===code).reduce((s,t)=>s+sa(t),0);}
function cashflowV(){
  const rows=rangeFilter(),R=compute(rows);
  /* three extruded, banknote-textured bars on one scale, CRED's "your cash flow": the shape of the
     period at a glance, and each bar is the button that opens its breakdown */
  const mx=Math.max(R.inn,R.inv,R.out,1);
  const bar=(k,label,cls,amt)=>{const h=Math.max(1.5,Math.max(0,amt)/mx*100);
    return `<button class="cfbar" onclick="setFlow('${k}')" aria-label="${label} ${esc(fmt(amt))} — open the breakdown">
      <span class="cfv num">${fmtK(amt)}</span>
      <span class="cff ${cls}" style="height:${h}%"><svg aria-hidden="true"><rect width="100%" height="100%" fill="url(#wv-${cls})"/></svg></span></button>`;};
  const frow=(k,label,amt,code)=>`<button class="frow" onclick="setFlow('${k}')"><span class="fn">${label}</span>
      <span class="fr"><span class="fa num"><span>${fmtH(amt)}</span><span class="chev">${I('chev')}</span></span>
        <span class="avg num">6 months total ${fmtK(sixMonthTotal(code))}</span></span></button>`;
  const ins=DATA.insights.map(c=>`<div class="note">${I(c.icon in IC?c.icon:'spark')}<span><b>${esc(c.title)}.</b> ${hl(c.copy)}</span></div>`).join('');
  return `<div class="view">
    <h1 class="h1">your cash flow</h1>
    <div class="chips"><button class="pillb blue" onclick="go('accounts')">${esc(M.account||'account')}</button>
      <button class="pillb gold" onclick="togglePeriod()" aria-expanded="${PERIODOPEN}">${RANGE==='S'?I('star'):I('cal')}${esc(periodText())} ${I('chevd')}</button></div>
    ${PERIODOPEN?rangeRow():''}
    ${M.salary_day>1&&CYCLENOTE?`<div class="note gold" style="--tip:150px">${I('star')}<span>introducing salary cycle. your cash flow can start from your
      salary date, the ${ord(M.salary_day)}, instead of the calendar month.<span class="noteacts"><button class="notebtn" onclick="setR('S');dismissCycle()">use salary cycle</button>
      <button class="notebtn" onclick="dismissCycle()">understood</button></span></span></div>`:''}
    ${M.is_card?cardFlowCard():''}
    <div><div class="cfchart">${bar('in','incoming','in',R.inn)}
      ${bar('inv','investments','inv',R.inv)}
      ${bar('out','spends','out',R.out)}</div>
      <div class="cfl" style="margin-top:14px"><span>${esc(tabLabel('in')==='paid off'?'paid off':'incoming')}</span><span>investments</span><span>${M.is_card?'charged':'spends'}</span></div></div>
    <div class="rlist">${frow('in',M.is_card?'paid off':'incoming',R.inn,'i')}${frow('inv','investments',R.inv,'v')}${frow('out',M.is_card?'charged':'spends',R.out,'s')}</div>
    ${slfNote(R)}
    ${ins?`<div class="st"><h2>for you</h2></div>${ins}`:''}
  </div>`;}

/* a card: charges, what you paid off, and what came back — a net figure would be meaningless */
function cardFlowCard(){
  const c=DATA.card;if(!c)return '';
  const owed=c.net_new_debt, paidOff=owed<0;
  const back=c.refunds+c.rewards;
  const total=c.charges+c.fees||1, payW=Math.min(100,Math.round(c.payments/total*100));
  return `<div class="card2"><div class="cap">this card · all time</div>
    <div class="h2 num" style="margin-top:8px">${fmtK(Math.abs(owed))} <span class="sub">${paidOff?'paid off beyond charges':'added to balance'}</span></div>
    <div class="flowbar"><span class="bin" style="width:${payW}%"></span><span class="bout" style="width:${100-payW}%"></span></div>
    <div class="cfee">charged <span class="num">${fmtK(c.charges)}</span> · paid <span class="num">${fmtK(c.payments)}</span> · back to you <span class="num">${fmtK(back)}</span></div>
    ${c.fees?`<div class="cfee"><span class="num">${fmtK(c.fees)}</span> of that was interest and fees — the avoidable part.</div>`:''}
    ${(DATA.bill_cycles||[]).length?`<button class="nlink" onclick="openDetail('bills')">see what each bill paid for</button>`:''}
  </div>`;}

/* ================= detail screens ================= */

/* ---- one flow, broken down: CRED's spends / incoming screen ---- */
function breakdownV(){
  const rows=rangeFilter(),R=compute(rows),hv=heroValue(R);
  const card=FLOW==='in'?sourceCard(R):FLOW==='inv'?investCard(R):spendCard(R);
  const pick={out:t=>t.f==='s',in:t=>t.f==='i',inv:t=>t.f==='v'}[FLOW];
  const color={out:'var(--outS)',in:'var(--inS)',inv:'var(--invS)'}[FLOW];
  const hist=byMonth(shareRows(netFilter(ALL)),pick),hk=Object.keys(hist).sort(),hav=hk.length?Math.round(hk.reduce((s,k)=>s+hist[k],0)/hk.length):0;
  const latest=hk[hk.length-1];
  const word={out:'spent',in:'received',inv:'invested'}[FLOW];
  return `<div class="view">
    ${backBtn('backFromDetail()','cash flow')}
    ${filterBar()}
    <div class="heroc"><div class="cap capk">${esc(hv.label)}</div>
      <div class="hero fig num" id="hero" data-to="${hv.amount}">${fmtH(hv.amount)}</div>
      ${hv.avg?`<div class="avg num">avg per month ${fmtK(hv.avg)}</div>`:''}${heroDelta(R)}</div>
    ${netRowInline()}
    ${card}
    ${FLOW==='out'?topSpendsGrid(R):''}
    ${hk.length>1?`<div><div class="cap">${esc(hv.label)} history</div>
      <div class="hero fig num" style="margin-top:14px">${fmtH(hav)}</div>
      <div class="sub" style="margin-top:8px">average amount ${word} per month over the last ${hk.length} months</div></div>
      <div class="tr"><span class="trl">${I('bars')}Past trends</span>
        <button class="pillb" onclick="toggleTrend()">${TREND==='month'?'entire month':'till date'} ${I('chev')}</button></div>
      ${monthChart(shareRows(netFilter(ALL)),pick,color)}
      ${latest?`<button class="ulink" onclick="CF=monthStart('${latest}');CT=monthEnd('${latest}');RANGE='C';openDetail('search')">View ${MON[+latest.slice(5)-1]} transactions</button>`:''}`:''}
  </div>`;}
function netRowInline(){const n=netRow();return n?`<div>${n}</div>`:'';}

/* ---- one tag, merchant or person ---- */
let TAGVIEW='',MERVIEW='',PERVIEW='';
/* one breadcrumb: tag -> merchant -> back is a real path, and backing out must land on the tag */
let FROMTAG='';
function openTag(t){TAGVIEW=t;MERVIEW='';PERVIEW='';FROMTAG='';openDetail('tagdetail');}
function openMerchant(m){FROMTAG=TAGVIEW;MERVIEW=m;PERVIEW='';TAGVIEW='';openDetail('tagdetail');}
/* a person can span several merchant spellings, so filter by counterparty, not by one name */
function openPerson(cp,name){FROMTAG=TAGVIEW;MERVIEW=name;PERVIEW=cp;TAGVIEW='';openDetail('tagdetail');}
function tagDetail(){
  const key=TAGVIEW||MERVIEW,byTag=!!TAGVIEW;
  const match=t=>byTag?t.c===key:PERVIEW?t.cp===PERVIEW:(t.m||'')===key;
  const rows=rangeFilter().filter(match);
  const tot=rows.filter(t=>t.f!=='i'&&t.f!=='x').reduce((s,t)=>s+sa(t),0);
  const inTot=rows.filter(t=>t.f==='i').reduce((s,t)=>s+t.a,0);
  const byMer={},cnt={};rows.forEach(t=>{if(t.f==='i'||t.f==='x')return;const m=t.m||t.desc;byMer[m]=(byMer[m]||0)+sa(t);cnt[m]=(cnt[m]||0)+1;});
  const mers=Object.keys(byMer).map(m=>({m,a:byMer[m],n:cnt[m]})).sort((a,b)=>b.a-a.a);
  const maxA=Math.max(...mers.map(m=>m.a),1);
  const merRows=mers.slice(0,12).map(m=>`<button class="row" onclick="openMerchant('${escArg(m.m)}')">${iconDisc(catIcon(key))}<span class="rm"><span class="rn">${esc(m.m)}</span><span class="rs">${m.n}× · ~${fmtK(Math.round(m.a/m.n))} each</span><span class="bar"><i style="width:${(m.a/maxA*100).toFixed(0)}%"></i></span></span><span class="rr"><span class="ra num">${fmtH(m.a)}</span></span><span class="chev">${I('chev')}</span></button>`).join('');
  const sorted=rows.slice().sort(SORT==='high'?(a,b)=>b.a-a.a:(a,b)=>(a.d<b.d?1:-1)).slice(0,80);
  const big=tot||inTot;
  return `<div class="view">
    ${backBtn('backFromDetail()',FROMTAG||'back')}
    <div class="tr"><span class="cap capk">${esc(key)}</span>
      <button class="pillb" onclick="toggleTrend()">${TREND==='month'?'entire month':'till date'} ${I('chev')}</button></div>
    ${monthChart(shareRows(netFilter(ALL)).filter(match),t=>t.f!=='x','var(--ink)')}
    <div class="tr"><div><div class="cap">total amount</div><div class="hero fig num" style="margin-top:10px">${fmtH(big)}</div>
      <div class="sub" style="margin-top:6px">${rows.length} transactions ${esc(rangeLabel())}</div></div>
      <button class="pillb" onclick="setSort('${SORT==='high'?'recent':'high'}')">${SORT==='high'?'high to low':'most recent'}</button></div>
    ${byTag&&mers.length>1?`<div class="st"><h2>top merchants</h2></div><div class="rlist">${merRows}</div>`:''}
    <div class="st"><h2>transactions</h2></div>
    <div class="rlist">${sorted.map(t=>txRow(t,true)).join('')||'<div class="empty">nothing in this period</div>'}</div>
  </div>`;}

/* ---- the full ledger, searchable ---- */
function search(){const rows=rangeFilter().slice().reverse().slice(0,800);
  return `<div class="view">
    ${backBtn('backFromDetail()','transactions')}
    <h1 class="h1">all transactions</h1>
    <input id="q" class="search" placeholder="search a merchant, tag or amount…" oninput="ft(this)" aria-label="search transactions">
    ${rangeRow()}
    <div id="led">${dayGrouped(rows)}</div></div>`;}
function ft(i){const q=i.value.toLowerCase();
  document.querySelectorAll('#led .row').forEach(r=>{r.style.display=r.textContent.toLowerCase().includes(q)?'':'none';});
  document.querySelectorAll('#led .rlist').forEach(l=>{
    const any=[...l.querySelectorAll('.row')].some(r=>r.style.display!=='none');
    l.style.display=any?'':'none';const h=l.previousElementSibling;
    if(h&&h.classList.contains('dayh'))h.style.display=any?'':'none';});}

/* ---- one transaction: tag it, note it, split it ---- */
let TXNREF='',TAGPICK=null,TAGQ='';
function openTxn(ref){if(!ref)return;TXNREF=ref;TAGPICK=null;TAGQ='';openDetail('txn');}
function pickTag(t){TAGPICK=t;draw();}
function filterTags(v){TAGQ=v.toLowerCase();
  document.querySelectorAll('.tagchip').forEach(b=>{b.style.display=b.textContent.toLowerCase().includes(TAGQ)?'':'none';});}
function confirmTag(){if(!TAGPICK)return;const t=ALL.find(x=>x.ref===TXNREF);if(!t)return;setTag(t.ref,TAGPICK);TAGPICK=null;
  toast(`tagged ${t.m||'this'} as ${OVERRIDE[t.ref]||t.c}`);}
function txnDetail(){
  const t=ALL.find(x=>x.ref===TXNREF);
  if(!t)return `<div class="view">${backBtn('backFromDetail()','back')}<div class="empty">transaction not found</div></div>`;
  const cur=OVERRIDE[t.ref]||t.c,isIn=t.f==='i',sel=TAGPICK||cur;
  const chips=(DATA.tag_vocab||[]).map(v=>`<button class="tagchip ${v.tag===sel?'on':''}" onclick="pickTag('${escArg(v.tag)}')" aria-pressed="${v.tag===sel}">${I(v.icon||catIcon(v.tag))}${esc(v.tag)}</button>`).join('');
  return `<div class="view">
    ${backBtn('backFromDetail()','back')}
    <div class="txh">${iconDisc(catIcon(cur))}
      <div class="txnm">${esc(t.m||t.desc)}</div>
      <div class="txamt num ${isIn?'in':''}">${isIn?'+':''}${fmtH(t.a)}</div>
      <div class="cap">${esc(shortDate(t.d))}</div>
      <div class="tagbox">${esc(cur)}</div>
      <div class="cap">${isIn?'received into':'paid from'}</div>
      <div class="from"><i style="--bk:${bankHue(M.account)}"></i>${esc(M.account)}</div>
      ${t.b!=null?`<div class="cap">balance after · <span class="num">${fmt(t.b)}</span></div>`:''}
      ${t.desc&&t.m&&t.desc!==t.m?`<div class="narr">${esc(t.desc)}</div>`:''}</div>
    <hr class="dash">
    <div><h2 class="h2">tag this transaction for better insights</h2>
      <div class="sub" style="margin-top:8px">the right tag sharpens every number. we'll remember it for ${esc(t.m||'this merchant')}.</div></div>
    <label class="tsrch">${I('srch')}<input id="tagq" placeholder="search for category" value="${esc(TAGQ)}" oninput="filterTags(this.value)" aria-label="search for category"></label>
    <div class="cap">tag your transaction</div>
    <div class="tagwrap">${chips}</div>
    <textarea id="note" class="notefield" rows="2" placeholder="add a note — why was this payment made?" oninput="setNote('${escArg(t.ref)}',this.value)" aria-label="note">${esc(NOTES[t.ref]||t.note||'')}</textarea>
    ${splitEditor(t)}
    <div id="simwrap"></div>
    <div class="actbar"><button class="np ghost" onclick="backFromDetail()">Skip</button>
      <button class="np" onclick="confirmTag()" ${TAGPICK&&TAGPICK!==cur?'':'disabled'}>Confirm</button></div>
  </div>`;}

/* ---- shared-charge editor: only on money going OUT ---- */
function splitEditor(t){
  if(t.f==='i'||t.f==='x')return '';
  const cur=SPLITS[t.ref]!==undefined?SPLITS[t.ref]:(t.mine!=null?t.mine:null);
  const isSplit=cur!=null&&cur!==t.a;
  const ways=[2,3,4].map(n=>{const share=Math.round(t.a/n);
    return `<button class="schip ${isSplit&&Math.abs(cur-share)<=1?'on':''}" onclick="applySplit('${escArg(t.ref)}',${share})" title="your share if ${n} people shared this">1/${n}</button>`;}).join('');
  const state=isSplit
    ? `<div class="srow"><span class="l">your share</span><span class="num sv">${fmtH(cur)}</span></div>
       <div class="srow"><span class="l">recoverable</span><span class="num sr">${fmtH(t.a-cur)}</span></div>`
    : `<div class="sub">all <span class="num">${fmt(t.a)}</span> counts as yours</div>`;
  return `<div class="st"><h2>shared?</h2></div>
    <div class="card2" style="display:flex;flex-direction:column;gap:14px">
      <div class="sub">split a charge someone else owes you for. the billed amount never changes — your statement still says <span class="num">${fmt(t.a)}</span> — only what counts as <b>your</b> spending does.</div>
      ${state}
      <div class="swrap">${ways}
        <input id="split-exact" class="sexact num" type="text" inputmode="decimal" placeholder="exact ₹" aria-label="your exact share"
          value="${isSplit?(cur/100).toFixed(2):''}" onchange="applySplit('${escArg(t.ref)}',Math.round(parseFloat(this.value||'0')*100))">
        ${isSplit?`<button class="schip clear" onclick="applySplit('${escArg(t.ref)}',null)">clear</button>`:''}</div>
      <input id="split-with" class="sexact" placeholder="with whom? (for your reference)" aria-label="split with whom"
        value="${esc(t.with||'')}" onchange="setSplitWith('${escArg(t.ref)}',this.value)">
    </div>`;}
let SPLITS={},SPLITWITH={};
function applySplit(ref,mine){
  const t=ALL.find(x=>x.ref===ref);if(!t)return;
  if(mine!=null&&(isNaN(mine)||mine<0||mine>t.a))return toast(`your share must be between ₹0 and ${fmt(t.a)}`);
  SPLITS[ref]=mine;if(mine==null)delete SPLITS[ref];
  t.mine=mine==null?undefined:mine;if(mine==null)delete t.mine;
  draw();
  if(!API)return;
  post('/api/split',{content_hash:ref,mine_minor:mine,with_whom:SPLITWITH[ref]||t.with||''}).then(r=>{if(r&&r.error)toast(r.error);});}
function setSplitWith(ref,who){
  SPLITWITH[ref]=who;const t=ALL.find(x=>x.ref===ref);if(t)t.with=who;
  if(!API||!t||t.mine==null)return;
  post('/api/split',{content_hash:ref,mine_minor:t.mine,with_whom:who}).then(r=>{if(r&&r.error)toast(r.error);});}

/* ---- similar transactions + multi-select bulk retag ---- */
let SIM=null, SIMSEL=new Set();
function loadSimilar(ref){
  const wrap=document.getElementById('simwrap');
  if(!wrap||!API)return;
  fetch('/api/similar?t='+encodeURIComponent(API)+'&ref='+encodeURIComponent(ref))
    .then(r=>r.json()).then(g=>{if(!g||!g.count){SIM=null;return;}
      SIM=g;SIMSEL=new Set(g.sample.map(s=>s.ref));renderSimilar();}).catch(()=>{});}
function renderSimilar(){
  const wrap=document.getElementById('simwrap');if(!wrap||!SIM)return;
  const rows=SIM.sample.map(s=>`<label class="simrow">
      <input type="checkbox" ${SIMSEL.has(s.ref)?'checked':''} onchange="toggleSim('${escArg(s.ref)}')">
      <span class="simmain"><span class="simnm">${esc(s.desc)}</span><span class="simsub">${dayLabel(s.date)} · ${esc(s.tag||'untagged')}</span></span>
      <span class="simamt num">${s.dir==='C'?'+':'−'}${fmt(s.amount).replace('−','')}</span></label>`).join('');
  const conflict=(SIM.current_tags||[]).length>1
    ? `<div class="note">${I('spark')}<span>these are tagged inconsistently right now: ${SIM.current_tags.map(esc).join(', ')}</span></div>` : '';
  wrap.innerHTML=`<div class="view" style="gap:18px">
    <div class="st"><h2>similar transactions</h2><a onclick="simAll(${SIMSEL.size!==SIM.sample.length})">${SIMSEL.size===SIM.sample.length?'clear all':'select all'}</a></div>
    <div class="sub">${esc(SIM.reason)}. tick the ones that belong together, pick a tag, and they all update.</div>
    ${conflict}<div class="rlist">${rows}</div>
    <div class="simbar"><select id="simtag" class="simsel" aria-label="tag for the selected">${(DATA.tag_vocab||[]).map(v=>`<option value="${esc(v.tag)}">${esc(v.tag)}</option>`).join('')}</select>
      <button class="np" onclick="applySim()">Tag <span id="simn">${SIMSEL.size}</span> selected</button></div></div>`;}
function toggleSim(ref){SIMSEL.has(ref)?SIMSEL.delete(ref):SIMSEL.add(ref);
  const n=document.getElementById('simn');if(n)n.textContent=SIMSEL.size;
  const link=document.querySelector('#simwrap .st a');
  if(link)link.textContent=SIMSEL.size===SIM.sample.length?'clear all':'select all';}
function simAll(on){SIMSEL=on?new Set(SIM.sample.map(s=>s.ref)):new Set();renderSimilar();}
function applySim(){
  if(!SIM||!SIMSEL.size)return toast('nothing selected');
  const tag=document.getElementById('simtag').value,refs=[...SIMSEL];
  post('/api/tag-many',{tag,refs}).then(r=>{
    if(r&&r.error)return toast('could not save: '+r.error);
    refs.forEach(ref=>{const row=ALL.find(x=>x.ref===ref);if(row)row.c=tag;});
    toast(`tagged ${r.tagged||refs.length} transactions as ${tag}`);draw();});}

/* ---- what got netted: the audit trail behind every netted total ---- */
function nettingV(){
  const rows=periodRows(),have=new Set(rows.map(t=>t.ref));
  const byRef={};rows.forEach(t=>byRef[t.ref]=t);
  const seen=new Set();const pairs=[];
  for(const t of rows){
    if(!t.rev||!have.has(t.rev)||seen.has(t.ref))continue;
    seen.add(t.ref);seen.add(t.rev);
    const other=byRef[t.rev];
    pairs.push(t.dir==='D'?[t,other]:[other,t]);}
  pairs.sort((a,b)=>b[0].a-a[0].a);
  const meta=Object.fromEntries((DATA.reversals||[]).map(r=>[r.out_ref,r]));
  const pairRows=pairs.map(([d,c])=>{const m=meta[d.ref]||{},days=m.days!=null?m.days:'';
    return `<button class="row" onclick="openTxn('${escArg(d.ref)}')">${iconDisc('repeat')}
      <span class="rm"><span class="rn">${esc(d.m||d.desc)}</span><span class="rs">${esc(shortDate(d.d))} → ${esc(shortDate(c.d))}${days!==''?` · ${days===0?'same day':days+'d'}`:''}${m.confidence==='certain'?' · bank reference matches':''}</span></span>
      <span class="rr"><span class="ra num">${fmtH(d.a)}</span></span><span class="chev">${I('chev')}</span></button>`;}).join('');
  const by={};rows.forEach(t=>{if(t.cp)(by[t.cp]=by[t.cp]||[]).push(t);});
  const ppl=[];
  for(const cp in by){const rs=by[cp];
    const paid=rs.filter(t=>t.dir==='D').reduce((s,t)=>s+t.a,0);
    const got=rs.filter(t=>t.dir==='C').reduce((s,t)=>s+t.a,0);
    if(paid&&got)ppl.push({cp,name:rs[0].cpn||rs[0].m||cp,paid,got,net:paid-got,off:Math.min(paid,got),n:rs.length});}
  ppl.sort((a,b)=>b.off-a.off);
  const pplRows=ppl.map(p=>`<button class="row" onclick="openPerson('${escArg(p.cp)}','${escArg(p.name)}')">${iconDisc('person')}
      <span class="rm"><span class="rn">${esc(p.name)}</span><span class="rs">paid ${fmtK(p.paid)} · got back ${fmtK(p.got)} · ${p.n} rows</span></span>
      <span class="rr"><span class="ra num ${p.net<0?'in':''}">${p.net===0?'settled':fmtH(Math.abs(p.net))}</span><span class="rd">${p.net>0?'you sent more':p.net<0?'you got more':'square'}</span></span>
      <span class="chev">${I('chev')}</span></button>`).join('');
  return `<div class="view">
    ${backBtn('backFromDetail()','transactions')}
    <div><div class="cap">cancelled ${esc(rangeLabel())}</div>
      <div class="hero fig num" style="margin-top:10px">${fmtH(pairs.reduce((s,p)=>s+p[0].a,0))}</div>
      <div class="sub" style="margin-top:6px">across ${pairs.length} pair${pairs.length!==1?'s':''}</div></div>
    <div class="note">${I('spark')}<span>a cancelled pair is money that left and came straight back — a failed booking or a bounced
      transfer. netting people off is different: both transfers were real, so it is a preference, not a correction.</span></div>
    <div class="st"><h2>cancelled pairs</h2></div>
    <div class="rlist">${pairRows||'<div class="empty">nothing cancelled in this period</div>'}</div>
    <div class="st"><h2>money moved both ways</h2></div>
    <div class="rlist">${pplRows||'<div class="empty">no two-way counterparties in this period</div>'}</div>
  </div>`;}

/* ---- what each card payment paid for ---- */
let BILLOPEN=null;
function billsV(){
  const cs=DATA.bill_cycles||[];
  if(!cs.length)return `<div class="view">${backBtn('backFromDetail()','back')}<div class="empty">no bill payments found on this card yet</div></div>`;
  const paidTot=cs.reduce((s,c)=>s+c.paid,0);
  const rows=cs.map((c,i)=>{const open=BILLOPEN===i;
    const label=c.paid_on?shortDate(c.paid_on):'not yet billed';
    const window=c.from_date?`${esc(shortDate(c.from_date))} → ${esc(shortDate(c.to_date))}`:'';
    const kids=open?(c.refs||[]).map(r=>ALL.find(x=>x.ref===r)).filter(Boolean).sort((a,b)=>b.a-a.a).slice(0,40).map(t=>txRow(t,true)).join(''):'';
    const short=c.paid?(c.unpaid>0?`${fmtK(c.unpaid)} rolled over`:c.unpaid<0?`${fmtK(-c.unpaid)} paid ahead`:'settled in full'):'awaiting a bill';
    return `<div class="bill ${open?'open':''}">
      <button class="billhead" onclick="toggleBill(${i})" aria-expanded="${open}">
        <span class="bh1"><span class="bpaid num">${c.paid?fmtH(c.paid):'—'}</span><span class="bwhen">${esc(label)}</span></span>
        <span class="bh2">${c.count} charge${c.count!==1?'s':''} · ${fmtK(c.charges)}${c.fees?` · ${fmtK(c.fees)} fees`:''}${window?` · ${window}`:''}</span>
        <span class="bh3 ${c.unpaid>0?'warn':''}">${short}<span class="chev">${I(open?'chevd':'chev')}</span></span></button>
      ${open?`<div class="billkids"><div class="rlist">${kids||'<div class="empty">no charges in this cycle</div>'}</div></div>`:''}</div>`;}).join('');
  return `<div class="view">
    ${backBtn('backFromDetail()','back')}
    <div><div class="cap">bills paid · ${esc(M.account)}</div><div class="hero fig num" style="margin-top:10px">${fmtH(paidTot)}</div>
      <div class="sub" style="margin-top:6px">across ${cs.filter(c=>c.paid).length} payments</div></div>
    <div class="note">${I('spark')}<span>a card payment on your bank statement is one line. these are the transactions behind each one — tap a bill to see what it paid for.</span></div>
    <div class="view" style="gap:12px">${rows}</div></div>`;}
function toggleBill(i){BILLOPEN=BILLOPEN===i?null:i;draw();}

/* ---- persistence: corrections POST to the local server so they survive reload and re-ingest ---- */
const OVERRIDE={},NOTES={};
const API=(()=>{const t=new URLSearchParams(location.search).get('t');
  return t&&location.protocol.startsWith('http')?t:null;})();
function post(path,body){if(!API)return Promise.resolve({offline:true});
  return fetch(path+'?t='+encodeURIComponent(API),{method:'POST',body:JSON.stringify(body)})
    .then(r=>r.json()).catch(e=>({error:String(e)}));}
function setTag(ref,tag){
  OVERRIDE[ref]=tag;const t=ALL.find(x=>x.ref===ref);
  if(t){t.c=tag;ALL.forEach(o=>{if(t.m&&o.m===t.m)o.c=tag;});}   // merchant-wide, mirroring TagStore
  draw();
  post('/api/tag',t&&t.m?{tag,merchant:t.m}:{tag,content_hash:ref}).then(r=>{if(r&&r.error)toast('could not save tag: '+r.error);});}
function setNote(ref,v){NOTES[ref]=v;const t=ALL.find(x=>x.ref===ref);if(t)t.note=v;
  clearTimeout(setNote._d);
  setNote._d=setTimeout(()=>post('/api/note',{content_hash:ref,note:v}).then(r=>{if(r&&r.error)toast('could not save note: '+r.error);}),500);}
function toast(msg){let el=document.getElementById('toast');
  if(!el){el=document.createElement('div');el.id='toast';el.className='toast';el.setAttribute('role','status');document.body.appendChild(el);}
  el.textContent=msg;el.classList.add('on');clearTimeout(toast._t);
  toast._t=setTimeout(()=>el.classList.remove('on'),Math.min(20000,3200+msg.length*22));}

/* ================= navigation ================= */
/* TAB is the open tab; DET is a drilled-in screen. On a phone a detail replaces the tab; on a wide
   screen it opens in the pane beside it. DSTACK remembers the details you came through, so back
   walks the same path in reverse rather than dumping you at the tab. */
let TAB='cashflow',DET='',DSTACK=[];
const WIDE=window.matchMedia('(min-width:1100px)');
function snap(){return {DET,TAGVIEW,MERVIEW,PERVIEW,FROMTAG,TXNREF,FLOW};}
function openDetail(k){
  if(DET&&(DET!==k||k==='tagdetail'||k==='txn'))DSTACK.push(prevSnap||snap());
  prevSnap=null;DET=k;window.scrollTo(0,0);
  draw();}
let prevSnap=null;
/* openTag/openMerchant mutate the view keys BEFORE calling openDetail, so take the snapshot of the
   screen being left first — otherwise "back" would restore the screen you are already on */
['openTag','openMerchant','openPerson','openTxn'].forEach(fn=>{const f=window[fn];
  window[fn]=function(){prevSnap=DET?snap():null;return f.apply(this,arguments);};});
function backFromDetail(){
  const s=DSTACK.pop();
  if(s){({DET,TAGVIEW,MERVIEW,PERVIEW,FROMTAG,TXNREF,FLOW}=s);}
  else{DET='';}
  draw();}
function go(t){
  if(t==='home')t='cashflow';
  if(t==='spends'){FLOW='out';return openDetail('breakdown');}
  if(MAIN.some(m=>m[0]===t)){TAB=t;DET='';DSTACK=[];PERIODOPEN=false;window.scrollTo(0,0);draw();return;}
  openDetail(t);}
/* On a wide screen the pane is never empty: each tab names the detail that answers its first question. */
function defaultDetail(){
  if(TAB==='cashflow'){return breakdownV();}
  if(TAB==='accounts')return accountV();
  if(TAB==='txns'){const last=rangeFilter().slice(-1)[0];if(last&&!TXNREF){TXNREF=last.ref;}return TXNREF?txnDetail():'';}
  if(TAB==='recurring'){const r=(DATA.recurring||[]).filter(x=>x.active)[0];
    if(r&&!MERVIEW){MERVIEW=r.merchant;}return MERVIEW?tagDetail():'';}
  return '';}
/* the list control whose onclick opens what the pane shows. Compared with getAttribute, which returns
   the HTML-decoded text, so only escArg's JS-escaping half applies here */
function curOpen(){
  if(TAB==='cashflow'&&(!DET||DET==='breakdown'))return `setFlow('${FLOW}')`;
  if(TAB==='txns'&&(!DET||DET==='txn')&&TXNREF)return `openTxn('${String(TXNREF).replace(/\\/g,'\\\\').replace(/'/g,"\\'")}')`;
  return '';}
const VIEWS={accounts:accountsV,txns:txnsV,recurring:recurringV,cashflow:cashflowV,
             breakdown:breakdownV,tagdetail:tagDetail,txn:txnDetail,search:search,
             netting:nettingV,bills:billsV,account:accountV};
/* ---- redraw ----
   The view is rebuilt from state on every change (measured at a few ms over thousands of rows). Two
   things a diffing renderer gets for free are handled here: entrance animations run only when the
   SCREEN changes, not when a value on it does, and focus plus the caret survive the rebuild by id. */
let LASTVIEW='';
function draw(){
  const v=document.getElementById('views'),p=document.getElementById('pane');
  const act=document.activeElement;
  const keep=act&&act.id&&(v.contains(act)||p.contains(act))?{id:act.id,s:act.selectionStart,e:act.selectionEnd}:null;
  /* the moving part lives in the list, so on a wide screen the list's screen is the tab alone:
     opening a detail in the pane must not replay it */
  const KEY=WIDE.matches?TAB:(DET||TAB);
  const fresh=(KEY!==LASTVIEW);LASTVIEW=KEY;
  v.classList.toggle('nofx',!fresh);
  if(WIDE.matches){
    v.innerHTML=VIEWS[TAB]();
    const det=DET?(VIEWS[DET]||(()=>''))():defaultDetail();
    p.innerHTML=det||`<div class="paneempty"><div class="h2">pick anything on the left</div><div class="sub">its detail opens here</div></div>`;
    /* the list is already beside the pane, so back only appears once you drill past its first screen */
    p.classList.toggle('root',!DSTACK.length);
    const cur=curOpen();
    if(cur)v.querySelectorAll('[onclick]').forEach(el=>{if(el.getAttribute('onclick')===cur){el.classList.add('cur');el.setAttribute('aria-current','true');}});
  }else{
    v.innerHTML=(DET&&VIEWS[DET]?VIEWS[DET]:VIEWS[TAB])();p.innerHTML='';}
  if(keep){const el=document.getElementById(keep.id);
    if(el){el.focus({preventScroll:true});try{el.setSelectionRange(keep.s,keep.e);}catch(_){}}}
  band();showFreshness();
  /* open the trend chart at the NEWEST month: left-aligned it lands on the oldest year */
  /* columns are resized so a whole number fill the visible width, else the oldest one shows sliced */
  document.querySelectorAll('.chartwrap').forEach(cw=>{const w=cw.getBoundingClientRect().width;
    if(!w)return;const cw2=w/Math.max(1,Math.floor(w/62));cw.style.setProperty('--colw',cw2+'px');
    /* by column count, not scrollWidth: the newest bar's value tag overhangs the last column */
    cw.scrollLeft=cw.querySelectorAll('.bcol').length*cw2-w;});
  if(DET==='txn'&&TXNREF||(WIDE.matches&&TAB==='txns'&&!DET&&TXNREF))loadSimilar(TXNREF);}
WIDE.addEventListener('change',()=>{LASTVIEW='';draw();});
function setR(r){RANGE=r;draw();}
function setCF(v){CF=v;RANGE='C';draw();}
function setCT(v){CT=v;RANGE='C';draw();}
function setSort(s){SORT=s;draw();}
/* the donut ramp and avatar tints compute in JS, so a CSS swap alone would leave them on the old theme */
function TT(){const h=document.documentElement;h.dataset.theme=h.dataset.theme==='dark'?'light':'dark';
  try{localStorage.setItem('sl-theme',h.dataset.theme);}catch(_){}draw();}
try{const th=localStorage.getItem('sl-theme');if(th)document.documentElement.dataset.theme=th;}catch(_){}
/* ?v=account opens a screen directly — used when the accounts list switches to another account */
(()=>{const v=new URLSearchParams(location.search).get('v');
  if(v==='account'){TAB='accounts';DET='account';}else if(v==='txns'){TAB='txns';}
  /* ?v=txn[&ref=..] opens one transaction (default: the newest spend) */
  else if(v==='txn'){TAB='txns';DET='txn';TXNREF=new URLSearchParams(location.search).get('ref')||((ALL.filter(x=>x.f==='s').slice(-1)[0])||{}).ref;}
  else if(MAIN.some(m=>m[0]===v)){TAB=v;}
  const dn=new URLSearchParams(location.search).get('density');if(dn)document.documentElement.dataset.density=dn;})();
draw();
restoreScroll();
</script>
</body></html>"""
