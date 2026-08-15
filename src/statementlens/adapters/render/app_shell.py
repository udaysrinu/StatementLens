"""AppShellRenderer — self-contained, offline, CRED-Money-style app dashboard (Renderer port).

Built to the researched spec: mobile-first single column, ONE monumental hero number, insight
cards first, honest cash flow (in vs out, no invented "left"), top-5 single-hue category bars,
recurring, and recent — with the full ledger behind a "view all" tab. Charts-light, numbers-first,
one lime accent, serif display + grotesque body, one easing curve. Deterministic integer paise;
the client recomputes on the W/M/Y toggle and date range.
"""

from __future__ import annotations

import html
import json
from typing import Any, Dict


class AppShellRenderer:
    def render(self, dataset: Dict[str, Any]) -> str:
        label = html.escape(str(dataset.get("meta", {}).get("account", "Account")))
        payload = json.dumps(dataset, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/")
        return _PAGE.replace("__LABEL__", label).replace("__DATA__", payload)


_PAGE = r"""<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>__LABEL__ · Money</title><link rel="icon" href="data:,">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600&family=Instrument+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
:root{
  --bg:#08080a;--s1:#101013;--s2:#17171b;--ink:#f4f4f0;--ink2:#9a9aa2;--ink3:#5c5c64;
  --line:rgba(255,255,255,.07);--acc:#c6f24e;--up:#8fe08f;--down:#ff8f8f;
  --page:#050507;--onacc:#08080a;--glow:198,242,78;--navbg:rgba(8,8,10,.86);--acc2:#8fbf3a;
  --disp:'Fraunces',Georgia,serif;--body:'Instrument Sans',system-ui,sans-serif;--ease:cubic-bezier(.2,.7,.3,1);
}
/* Warm editorial (default) — the palette from the Stitch design system: parchment surfaces, a single
   terracotta accent, espresso ink. Amber reads as "considered" where lime-on-black reads as "app". */
[data-theme=light]{--bg:#efe7db;--s1:#faf8f2;--s2:#f2ede2;--ink:#241a12;--ink2:#5f584c;--ink3:#94816d;
  --line:rgba(36,26,18,.12);--acc:#b5702a;--up:#3f7d43;--down:#c0503a;
  --page:#e7dccb;--onacc:#fffaf2;--glow:181,112,42;--navbg:rgba(250,248,242,.92);--acc2:#8f5620;}
*{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}
body{background:var(--page);color:var(--ink);font-family:var(--body);font-size:15px;line-height:1.5;-webkit-font-smoothing:antialiased;min-height:100vh;display:flex;justify-content:center;padding:0}
.num{font-variant-numeric:tabular-nums;font-feature-settings:"tnum"}
/* paise, dimmed and slightly smaller — the rupees carry the meaning. Borrowed from CRED, which sets
   ₹97,000.00 with the ".00" recessive so a six-digit figure reads at a glance. */
.ps{opacity:.42;font-size:.62em}

/* Guilloché — the engraved lattice on a banknote. Three offset repeating gradients at coprime angles
   interfere into a woven moiré; it is the one texture that says "money" without a picture, and it
   costs nothing to ship because there is no image. Used INSIDE the flow bars. */
.guil{background-image:
  repeating-linear-gradient(58deg,rgba(255,255,255,.5) 0 1px,transparent 1px 5px),
  repeating-linear-gradient(-49deg,rgba(255,255,255,.42) 0 1px,transparent 1px 7px),
  repeating-linear-gradient(11deg,rgba(0,0,0,.05) 0 1px,transparent 1px 4px)}
/* Sunburst rays behind the header, CRED's account-screen device. A repeating-conic-gradient makes the
   engraved fan for free; kept to the top ~230px and very low contrast so it reads as watermarked
   stationery rather than as decoration competing with the numbers. */
.app{width:100%;max-width:460px;background:var(--bg);min-height:100vh;position:relative;
  background-image:radial-gradient(58% 34% at 50% 0%,rgba(var(--glow),.07),transparent 62%)}
.app::before{content:'';position:absolute;top:0;left:0;right:0;height:230px;
  pointer-events:none;z-index:0;
  background:repeating-conic-gradient(from 200deg at 50% 8%,
    rgba(var(--glow),.13) 0deg 1.1deg,transparent 1.1deg 5deg);
  mask:linear-gradient(#000,transparent 78%);-webkit-mask:linear-gradient(#000,transparent 78%)}
.wrap{position:relative;z-index:1}
.wrap{padding:20px 20px 108px;display:flex;flex-direction:column;gap:22px}

/* top */
.top{display:flex;justify-content:space-between;align-items:center;padding-top:8px}
.hi{font-size:13px;color:var(--ink2)}.nm{font:600 19px/1.15 var(--disp);margin-top:2px}
.av{width:40px;height:40px;border-radius:50%;background:linear-gradient(150deg,var(--acc),var(--acc2));display:grid;place-items:center;color:var(--onacc);font-weight:700;cursor:pointer}
/* account switcher — one chip per account, cards marked as cards. Horizontally scrollable: six
   accounts will not fit a phone, and wrapping to a second line pushes the hero below the fold. */
.accswitch{display:flex;gap:7px;overflow-x:auto;padding:2px 0 4px;scrollbar-width:none}
.accswitch::-webkit-scrollbar{display:none}
.achip{flex:0 0 auto;display:inline-flex;align-items:center;gap:7px;text-decoration:none;
  background:var(--s1);border:1px solid var(--line);border-radius:100px;padding:7px 13px;
  font:500 12px var(--body);color:var(--ink2);white-space:nowrap;
  transition:border-color .18s var(--ease),color .18s var(--ease),background .18s var(--ease)}
.achip svg{width:14px;height:14px;stroke:currentColor;fill:none;stroke-width:1.7;flex:none}
.achip:hover{color:var(--ink);border-color:var(--ink3)}
.achip.on{background:var(--acc);border-color:var(--acc);color:var(--onacc);font-weight:600}
.acctrow{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.acct{display:inline-flex;align-items:center;gap:7px;background:var(--s1);border:1px solid var(--line);border-radius:100px;padding:6px 13px;font-size:12.5px;color:var(--ink2)}
/* freshness stamp: an aggregator's credibility rests on how current the data is */
.fresh{font-size:12px;color:var(--ink3);display:inline-flex;align-items:center;gap:7px}
.fresh.stale{color:var(--down)}
.fresh button{background:none;border:none;color:var(--acc);font:600 12px var(--body);cursor:pointer;padding:0;text-decoration:underline}
.acct .d{width:7px;height:7px;border-radius:50%;background:var(--acc)}

/* hero */
.hero{display:flex;flex-direction:column;gap:5px;padding:6px 2px 2px}
.hero .l{font-size:11.5px;color:var(--ink3);letter-spacing:.08em;text-transform:uppercase}
.hero .big{font:500 50px/1 var(--disp);letter-spacing:-.02em}
.hero .sub{font-size:13.5px;color:var(--ink2);margin-top:5px}
.up{color:var(--up);font-weight:600}.down{color:var(--down);font-weight:600}

/* section title */
.st{display:flex;justify-content:space-between;align-items:baseline;padding:0 2px;margin-bottom:-6px}
.st h2{font:600 15px/1 var(--disp);font-style:italic;color:var(--ink)}
.st a{font-size:12.5px;color:var(--acc);text-decoration:none;cursor:pointer}

/* insights */
.insrow{display:flex;gap:12px;overflow-x:auto;padding:2px 2px 6px;scroll-snap-type:x mandatory;scrollbar-width:none}
.insrow::-webkit-scrollbar{display:none}
.ins{scroll-snap-align:start;flex:0 0 84%;background:linear-gradient(160deg,var(--s1),var(--s2));border:1px solid var(--line);border-radius:22px;padding:19px;animation:rise .5s var(--ease) both}
.ins .ic{width:34px;height:34px;border-radius:10px;background:rgba(var(--glow),.13);display:grid;place-items:center;margin-bottom:13px;color:var(--acc)}
.ins .ic svg{width:18px;height:18px}
.ins.alert .ic{background:rgba(255,143,143,.14);color:var(--down)}
.ins.positive .ic{background:rgba(143,224,143,.14);color:var(--up)}
.ins .it{font:600 12px/1 var(--body);letter-spacing:.06em;text-transform:uppercase;color:var(--ink3);margin-bottom:8px}
.ins .cp{font:500 16px/1.4 var(--disp)}
.ins .cp b{color:var(--acc);font-weight:600}

/* month */
.card{background:var(--s1);border:1px solid var(--line);border-radius:22px;padding:20px}
.mtop{display:flex;justify-content:space-between;align-items:center;margin-bottom:16px}
.mtop .l{font-size:11.5px;color:var(--ink3);text-transform:uppercase;letter-spacing:.06em}
.mtop .v{font:500 22px/1 var(--disp);margin-top:7px}
.seg{display:flex;background:var(--s2);border-radius:100px;padding:3px}
.seg button{border:none;background:transparent;color:var(--ink2);padding:6px 13px;border-radius:100px;font:600 12px var(--body);cursor:pointer}
.seg button.on{background:var(--acc);color:var(--onacc)}
.flow{display:flex;gap:8px;margin-bottom:14px}
/* the tiles are buttons: each promotes its figure into the hero */
.fc{flex:1;min-width:0;background:var(--s2);border:1px solid transparent;border-radius:14px;
  padding:12px;text-align:left;font:inherit;cursor:pointer;
  transition:border-color .18s var(--ease),background .18s var(--ease)}
.fc:hover{border-color:var(--line)}
.fc.on{border-color:var(--acc);background:rgba(var(--glow),.09)}
.fc .fl{font-size:10.5px;color:var(--ink3);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.fc .fv{font:500 17px/1 var(--disp);margin-top:6px}
.fc .fn{font-size:10px;color:var(--ink3);margin-top:4px}
.fin{color:var(--up)}.fout{color:var(--ink)}.finv{color:var(--ink2)}
.fhint{font-size:11px;color:var(--ink3);margin-top:10px;text-align:center}

/* ---- three-way flow bars (CRED's "your cash flow") ----
   Hue carries the FLOW, which the old flat two-colour ribbon could not do: incoming blue, investments
   tan, spends purple. Each bar is extruded with a darker right face, so three bars read as objects
   rather than as a chart — the thing that makes CRED's version feel built rather than plotted. */
.fbars{display:flex;align-items:flex-end;justify-content:space-around;gap:14px;height:172px;
  padding:22px 4px 0;margin-bottom:4px}
.fbar{flex:1;min-width:0;display:flex;flex-direction:column;align-items:center;height:100%;
  background:none;border:none;padding:0;cursor:pointer;font:inherit}
.fbcol{flex:1;width:100%;display:flex;align-items:flex-end;justify-content:center;position:relative}
/* the value floats ABOVE its own bar, not beside it — anchored to the bar's top edge */
.fbv{position:absolute;bottom:100%;left:50%;transform:translateX(-50%);margin-bottom:5px;
  font:600 11px var(--body);color:var(--ink2);white-space:nowrap}
/* the bar itself: front face + a 5px darker side face for the extrusion */
.fbi{position:relative;width:60%;max-width:58px;min-height:3px;border-radius:2px 2px 0 0;
  transition:height .5s var(--ease)}
.fbi::after{content:'';position:absolute;top:3px;right:-5px;width:5px;height:100%;
  background:var(--face);border-radius:0 2px 0 0}
.fbl{font:600 9.5px var(--body);letter-spacing:.09em;text-transform:uppercase;color:var(--ink3);
  margin-top:9px;white-space:nowrap}
.fbar.on .fbl{color:var(--ink)}
/* Flow hues — deliberately NOT the terracotta accent, because these three must be told apart.
   background-COLOR only: the `background` shorthand would reset background-image and wipe out the
   guilloché texture layered on by .guil. */
.fbi.in{background-color:#6f9ed8;--face:#3f6ba8}
.fbi.inv{background-color:#d8b98a;--face:#a8875a}
.fbi.out{background-color:#b98ad8;--face:#8a5aa8}
[data-theme=dark] .fbi.in{background-color:#5b86bd;--face:#33578c}
[data-theme=dark] .fbi.inv{background-color:#bda06f;--face:#8c7145}
[data-theme=dark] .fbi.out{background-color:#a06fbd;--face:#71458c}

/* ---- donut, one hue, tinted by rank ---- */
.donut{display:flex;justify-content:center;padding:6px 0 2px}
.dwrap{position:relative;width:186px;height:186px}
.dring{width:186px;height:186px;border-radius:50%;
  /* the hole; the conic ring itself is set inline from the data */
  mask:radial-gradient(circle,transparent 50%,#000 50.5%);
  -webkit-mask:radial-gradient(circle,transparent 50%,#000 50.5%)}
.dmid{position:absolute;inset:0;display:grid;place-items:center;text-align:center}
.dtot{font:500 21px/1 var(--disp)}.dlab{font-size:10px;color:var(--ink3);margin-top:5px;
  letter-spacing:.08em;text-transform:uppercase}
/* the legend swatch takes its colour inline, matching its arc. Boxed to the same width the icon disc
   occupied so the name column stays on the same left edge as every other list on the screen. */
.dsw{width:10px;height:10px;border-radius:3px;flex:none;margin:0 13px}

/* ---- top spends as an avatar grid (CRED's "TOP SPENDS") ---- */
.grid3{display:grid;grid-template-columns:repeat(3,1fr);gap:18px 10px;padding:4px 0}
.gcell{display:flex;flex-direction:column;align-items:center;gap:8px;background:none;border:none;
  cursor:pointer;font:inherit;padding:0}
.gav{width:58px;height:58px;border-radius:50%;display:grid;place-items:center;
  border:1px solid var(--line);background:var(--s2);color:var(--ink2);position:relative;
  transition:border-color .18s var(--ease),transform .18s var(--ease)}
.gcell:hover .gav{border-color:var(--acc);transform:translateY(-2px)}
.gav svg{width:22px;height:22px}
/* generated avatar: the payee's initial on a tinted disc, hue derived from the name so it is stable */
.gav.init{font:600 19px var(--disp);color:#4a3a2a}
.gamt{font:600 12.5px var(--body);color:var(--ink)}
.gnm{font-size:10.5px;color:var(--ink3);text-align:center;line-height:1.25;
  max-width:88px;overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical}

/* ---- receipt-style transaction detail ---- */
.rcpt{background:var(--s1);border:1px solid var(--line);border-radius:20px;padding:26px 20px 20px;
  display:flex;flex-direction:column;align-items:center;text-align:center;gap:0}
.rcpt .ravg{margin-bottom:14px}
.rnm{font:500 17px/1.3 var(--disp);margin-bottom:10px}
.ramt{font:500 38px/1 var(--disp);letter-spacing:-.02em}
.rdate{font-size:11.5px;color:var(--ink3);margin-top:9px;letter-spacing:.05em;text-transform:uppercase}
.rtag{margin-top:13px;border:1px solid var(--line);border-radius:6px;padding:5px 13px;
  font:600 10.5px var(--body);letter-spacing:.09em;text-transform:uppercase;color:var(--ink2)}
/* the tear-line: a receipt's perforation, and the boundary between "what" and "how" */
.rtear{width:calc(100% + 40px);margin:20px -20px;border-top:1.5px dashed var(--line)}
.rfrom,.rbal{width:100%;display:flex;justify-content:space-between;align-items:center;
  font-size:13px;padding:5px 2px}
.rfrom .l,.rbal .l{font-size:11px;letter-spacing:.07em;text-transform:uppercase;color:var(--ink3)}
.rbank{display:inline-flex;align-items:center;gap:7px;font-weight:500}
.rbank .d{width:7px;height:7px;border-radius:50%;background:var(--acc)}
.rnarr{margin-top:14px;font-size:11.5px;color:var(--ink3);word-break:break-all;line-height:1.45}

/* ---- chart callout + avg pill (CRED's past-trends chart) ---- */
.bcall{position:absolute;top:-4px;left:50%;transform:translate(-50%,-100%);
  background:var(--s1);border:1.5px solid var(--ink);border-radius:7px;padding:3px 7px;
  font:600 10.5px var(--body);white-space:nowrap;z-index:3}
.bcall::after{content:'';position:absolute;bottom:-5px;left:50%;transform:translateX(-50%);
  border-left:5px solid transparent;border-right:5px solid transparent;border-top:5px solid var(--ink)}
/* centred on the dashed average line: bottom positions it, translateY(50%) straddles it */
.avgpill{position:absolute;left:50%;transform:translate(-50%,50%);z-index:2;
  background:var(--bg);border:1px solid var(--up);border-radius:100px;padding:2px 9px;
  font:600 9.5px var(--body);letter-spacing:.05em;color:var(--up);white-space:nowrap}

/* hero avg sub-line + disclosure note */
.hero .avg{font-size:12px;color:var(--ink3);margin-top:3px}
.note{font-size:12px;color:var(--ink3);background:var(--s1);border:1px solid var(--line);
  border-radius:12px;padding:10px 13px;line-height:1.4}

/* period control — one segmented row, presets first, Custom last.
   Scrolls horizontally on a narrow phone instead of wrapping into a ragged second line. */
/* Presets scroll; Custom is pinned OUTSIDE the scroller so the escape hatch is never the thing that
   gets clipped off-screen. Nine chips do not fit 420px, and a hidden control is a missing control. */
.pwrap{display:flex;align-items:stretch;gap:6px}
.prow{flex:1;min-width:0;display:flex;gap:4px;padding:4px;background:var(--s2);
  border:1px solid var(--line);border-radius:100px;
  overflow-x:auto;scrollbar-width:none;-webkit-overflow-scrolling:touch}
.prow::-webkit-scrollbar{display:none}
.pchip{flex:1 1 auto;min-width:34px;background:transparent;border:none;color:var(--ink2);
  border-radius:100px;padding:8px 7px;font:600 12px var(--body);cursor:pointer;
  white-space:nowrap;transition:background .18s var(--ease),color .18s var(--ease)}
.pchip:hover{color:var(--ink)}
.pchip.on{background:var(--acc);color:var(--onacc)}
/* Custom is visually demoted: it is the escape hatch, not the primary choice */
.pcustom{flex:none;display:flex;align-items:center;gap:5px;background:var(--s2);
  border:1px solid var(--line);border-radius:100px;color:var(--ink3);padding:0 11px;
  font:500 12px var(--body);cursor:pointer;white-space:nowrap;
  transition:background .18s var(--ease),color .18s var(--ease),border-color .18s var(--ease)}
.pcustom:hover{color:var(--ink)}
.pcustom svg{width:14px;height:14px;stroke:currentColor;fill:none;stroke-width:1.8}
.pcustom.on{background:var(--acc);border-color:var(--acc);color:var(--onacc);font-weight:600}
.drow{display:flex;align-items:center;gap:8px;margin-top:10px;animation:rise .3s var(--ease) both}
.drow input[type=date]{flex:1;min-width:0;background:var(--s1);border:1px solid var(--line);
  color:var(--ink);border-radius:12px;padding:10px 12px;font:500 13px var(--body);
  font-variant-numeric:tabular-nums}
.drow input[type=date]:focus{outline:none;border-color:var(--acc)}
.drow .to{color:var(--ink3);font-size:13px;flex:none}

/* netting mode — quieter than the period row: it is a lens on the same period, not a second period */
.nrow{display:flex;align-items:center;gap:6px;margin-top:9px;flex-wrap:wrap}
.nchip{background:transparent;border:1px solid var(--line);border-radius:100px;color:var(--ink3);
  padding:5px 11px;font:500 11.5px var(--body);cursor:pointer;white-space:nowrap;
  transition:border-color .18s var(--ease),color .18s var(--ease),background .18s var(--ease)}
.nchip:hover{color:var(--ink2)}
.nchip.on{background:var(--s2);border-color:var(--acc);color:var(--acc);font-weight:600}
/* the disclosure of what the mode removed — never let a total shrink silently */
.nnote{font-size:11px;color:var(--ink3);margin-left:2px}
/* divider between the two independent axes: netting (drops rows) and share (rescales them) */
.nsep{width:1px;height:18px;background:var(--line);margin:0 3px}

/* ---- shared-charge editor ---- */
.swrap{display:flex;flex-wrap:wrap;gap:7px;align-items:center}
.schip{background:transparent;border:1px solid var(--line);color:var(--ink2);border-radius:8px;
  padding:9px 14px;font:600 12px var(--body);cursor:pointer;
  transition:border-color .16s var(--ease),background .16s var(--ease),color .16s var(--ease)}
.schip:hover{border-color:var(--ink3);color:var(--ink)}
.schip.on{background:var(--acc);border-color:var(--acc);color:var(--onacc)}
.schip.clear{color:var(--down);border-color:transparent;text-decoration:underline}
.sexact{flex:1;min-width:96px;background:var(--s2);border:1px solid var(--line);border-radius:8px;
  color:var(--ink);font:500 12.5px var(--body);padding:9px 11px;font-variant-numeric:tabular-nums}
.sexact:focus{outline:none;border-color:var(--acc)}
.srow{display:flex;justify-content:space-between;align-items:baseline;padding:6px 0;
  border-bottom:1px solid var(--line)}
.srow:last-of-type{border-bottom:none;margin-bottom:10px}
.srow .l{font-size:11px;letter-spacing:.07em;text-transform:uppercase;color:var(--ink3)}
.srow .sv{font:500 17px/1 var(--disp)}
.srow .sr{font:500 17px/1 var(--disp);color:var(--up)}
.shint{font-size:12px;color:var(--ink3);margin-bottom:12px}
.nnote.link{background:none;border:none;padding:0;cursor:pointer;text-decoration:underline;
  font-family:var(--body)}
.nnote.link:hover{color:var(--acc)}

/* monthly bars + avg reference line */
/* padding-top leaves room for the callout above the tallest bar, which would otherwise be clipped */
.chart{position:relative;display:flex;align-items:flex-end;gap:6px;height:150px;padding-top:24px}
.bcol{flex:1;min-width:0;display:flex;flex-direction:column;align-items:center;gap:5px;height:100%}
.bwrap{flex:1;width:100%;display:flex;align-items:flex-end;position:relative}
.bwrap i{display:block;width:100%;border-radius:5px 5px 2px 2px;background:var(--s2)}
.bwrap i.on{background:var(--acc)}
/* the newest bar takes the flow's colour, so the chart reads as the same figure as the hero */
.bwrap i.in.on{background:var(--up)}
.bwrap i.inv.on{background:var(--ink2)}
.blab{font-size:9.5px;color:var(--ink3);letter-spacing:.04em}
.bval{font-size:9px;color:var(--ink3)}
.avgline{position:absolute;left:0;right:0;height:0;border-top:1px dashed var(--up);opacity:.55;z-index:1}
.avgt{font-size:11px;color:var(--ink3);font-family:var(--body);font-weight:400}

/* tag chips (correction UI) */
.tagwrap{display:flex;flex-wrap:wrap;gap:8px}
.tagchip{display:inline-flex;align-items:center;gap:7px;
  background:transparent;border:1px solid var(--line);color:var(--ink2);border-radius:8px;
  padding:9px 12px;font:600 11px var(--body);letter-spacing:.04em;text-transform:uppercase;cursor:pointer;
  transition:border-color .16s var(--ease),background .16s var(--ease),color .16s var(--ease)}
.tagchip svg{width:14px;height:14px;flex:none}
.tagchip:hover{border-color:var(--ink3);color:var(--ink)}
.tagchip.on{background:var(--acc);color:var(--onacc);border-color:var(--acc)}
.notefield{width:100%;background:var(--s2);border:1px solid var(--line);border-radius:10px;
  color:var(--ink);font:400 13px var(--body);padding:10px 12px;margin-top:10px;resize:vertical}
.notefield:focus{outline:none;border-color:var(--acc)}
.sortb{background:var(--s1);border:1px solid var(--line);color:var(--ink2);border-radius:100px;
  padding:6px 13px;font:600 11px var(--body);letter-spacing:.04em;text-transform:uppercase;cursor:pointer}

.cardfee{font-size:12px;color:var(--ink3);margin-top:10px;line-height:1.4}

/* similar transactions + bulk retag */
.simrow{display:flex;align-items:center;gap:12px;padding:12px 0;border-bottom:1px solid var(--line);cursor:pointer}
.simrow:last-child{border-bottom:none}
.simrow input[type=checkbox]{width:18px;height:18px;accent-color:var(--acc);flex:none;cursor:pointer}
.simmain{flex:1;min-width:0;display:flex;flex-direction:column;gap:2px}
.simnm{font-weight:600;font-size:13.5px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.simsub{font-size:11.5px;color:var(--ink3)}
.simamt{font:500 14px/1 var(--disp);flex:none}
.simwarn{font-size:12px;color:var(--down);background:var(--s1);border:1px solid var(--line);
  border-left:2px solid var(--down);border-radius:10px;padding:10px 13px}
.simbar{display:flex;gap:10px;align-items:center;flex-wrap:wrap}
.simsel{flex:1;min-width:150px;background:var(--s2);border:1px solid var(--line);color:var(--ink);
  border-radius:10px;padding:10px 12px;font:500 13px var(--body)}
.simgo{background:var(--acc);color:var(--onacc);border:none;border-radius:100px;
  padding:11px 20px;font:600 13px var(--body);cursor:pointer}

/* save-failure toast: a correction that silently didn't persist is worse than an error */
.toast{position:fixed;left:50%;bottom:88px;transform:translate(-50%,14px);z-index:20;max-width:400px;
  background:var(--s2);color:var(--ink);border:1px solid var(--down);border-radius:12px;
  padding:11px 16px;font-size:13px;opacity:0;pointer-events:none;transition:all .25s var(--ease);
  /* multi-line: the skipped-file explanations are one paragraph per file */
  white-space:pre-line;text-align:left;max-height:60vh;overflow-y:auto}
.toast.on{opacity:1;transform:translate(-50%,0)}
.flowbar{height:9px;border-radius:6px;background:var(--s2);overflow:hidden;display:flex}
.flowbar .bin{background:var(--up);height:100%}.flowbar .bout{background:var(--down);height:100%;opacity:.8}

/* categories (dividers, single hue) */
.list{background:var(--s1);border:1px solid var(--line);border-radius:22px;padding:6px 18px}
.crow{display:flex;align-items:center;gap:14px;padding:14px 0;border-bottom:1px solid var(--line);cursor:pointer}
.crow:last-child{border-bottom:none}
.crow .ci{width:38px;height:38px;border-radius:11px;background:var(--s2);display:grid;place-items:center;color:var(--acc);flex:none}
.crow .ci svg{width:18px;height:18px}
.crow .cm{flex:1;min-width:0}.crow .cn{font-weight:600;font-size:14.5px}
.crow .cb{height:4px;border-radius:4px;background:var(--s2);margin-top:8px;overflow:hidden}
.crow .cb i{display:block;height:100%;border-radius:4px;background:var(--acc)}
/* incoming and investment bars are tinted to match their flow, so a breakdown is never mistaken
   for a spend list at a glance */
.crow .cb.in i{background:var(--up)}
.crow .cb.inv i{background:var(--ink2)}
.crow .cr{text-align:right;flex:none}.crow .ca{font:500 15px/1 var(--disp)}.crow .cp{font-size:11.5px;color:var(--ink3);margin-top:3px}
/* affordance: these rows drill down, so say so rather than relying on the cursor alone */
.crow .chev{color:var(--ink3);margin-left:3px}
.crow:hover .chev{color:var(--acc)}

/* recent + recurring rows */
.trow{display:flex;align-items:center;gap:13px;padding:13px 0;border-bottom:1px solid var(--line)}
.trow:last-child{border-bottom:none}
.trow .ti{width:38px;height:38px;border-radius:11px;background:var(--s2);display:grid;place-items:center;font-size:14px;color:var(--ink2);flex:none;font-weight:600}
.trow .tm{flex:1;min-width:0}.trow .tn{font-weight:600;font-size:14px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.trow .td{font-size:12px;color:var(--ink3);margin-top:2px}
.trow .tv{font:500 15px/1 var(--disp);flex:none}.trow .tv.in{color:var(--up)}
.pill{font-size:11px;color:var(--ink3);border:1px solid var(--line);border-radius:100px;padding:2px 8px}
.due{color:var(--acc);font-weight:600;font-size:12px}

/* tabs */
.nav{position:fixed;bottom:0;left:50%;transform:translateX(-50%);width:100%;max-width:460px;height:70px;z-index:5;background:var(--navbg);backdrop-filter:blur(20px);border-top:1px solid var(--line);display:flex;justify-content:space-around;align-items:center;padding-bottom:6px}
.nav button{background:none;border:none;display:flex;flex-direction:column;align-items:center;gap:4px;color:var(--ink3);font-size:10.5px;cursor:pointer;font-family:var(--body)}
.nav button.on{color:var(--acc)}.nav button svg{width:21px;height:21px}
.rise{animation:rise .5s var(--ease) both;animation-delay:calc(var(--i,0) * .06s)}
.insrow .ins{animation-delay:calc(var(--i,0) * .08s)}
@keyframes rise{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:none}}
@media(prefers-reduced-motion:reduce){.ins,.rise{animation:none}}
.search{width:100%;padding:12px 15px;background:var(--s2);border:1px solid var(--line);border-radius:12px;color:var(--ink);font-size:14px;font-family:var(--body);margin-bottom:12px}
.search:focus{outline:none;border-color:var(--acc)}
.empty{text-align:center;padding:40px;color:var(--ink3)}
.view{display:none}.view.on{display:flex;flex-direction:column;gap:22px}

/* sticky day headers on the ledger */
.dayh{position:sticky;top:0;z-index:2;background:var(--bg);padding:8px 2px 6px;
  font:600 11px var(--body);letter-spacing:.1em;text-transform:uppercase;color:var(--ink3)}
.trow{cursor:pointer}
/* Back — a real control, not a word inside a label.
   It used to be a bare <a> with one colour rule, so it inherited the hero label's 11.5px uppercase
   and rendered at caption size with a ~14px-tall tap target. Three things were wrong: it was the
   smallest text on a screen you reach by drilling down (so the way OUT was the least visible thing
   on it), it was under the 44px minimum touch target, and an <a> with no href is not focusable, so
   there was no keyboard path back at all. Now a button: 44px high, its own row, arrow in a bordered
   disc that shifts on hover. */
/* align-self keeps it to its content width: .view is a flex column, so a plain inline-flex child
   would still stretch to the full 420px and give a huge invisible click area. */
.back{display:inline-flex;align-self:flex-start;align-items:center;gap:9px;min-height:44px;
  padding:0 14px 0 4px;
  background:none;border:none;cursor:pointer;color:var(--ink2);
  font:600 12.5px var(--body);letter-spacing:.04em;text-transform:none;
  border-radius:100px;transition:color .18s var(--ease),background .18s var(--ease)}
.back:hover{color:var(--ink);background:var(--s2)}
.back:focus-visible{outline:2px solid var(--acc);outline-offset:2px}
.back .barrow{width:30px;height:30px;flex:none;border-radius:50%;border:1px solid var(--line);
  display:grid;place-items:center;background:var(--s1);
  transition:transform .18s var(--ease),border-color .18s var(--ease)}
.back:hover .barrow{transform:translateX(-2px);border-color:var(--acc)}
.back .barrow svg{width:15px;height:15px;stroke:currentColor;fill:none;stroke-width:2}
/* the destination name carries the weight — "back to people" beats a naked chevron */
.back b{font-weight:600;color:inherit}
.card .l{font-size:11.5px;color:var(--ink3);text-transform:uppercase;letter-spacing:.06em}
.card .dv{font:600 16px/1.3 var(--body);margin-top:7px}
.card .dsub{font-size:12px;color:var(--ink3);margin-top:5px;word-break:break-word}
</style>
</head>
<body>
<div class="app">
 <div class="wrap">
  <div class="top">
    <div><div class="hi" id="greet">welcome back,</div><div class="nm">__LABEL__</div></div>
    <button class="av" onclick="TT()" title="theme">◐</button>
  </div>
  <div class="accswitch" id="accswitch"></div>
  <div class="acctrow">
    <span class="acct"><span class="d"></span> <span id="acctlbl">account</span></span>
    <span class="fresh" id="fresh"></span>
  </div>
  <div id="views"></div>
 </div>
 <div class="nav" id="nav"></div>
</div>
<script type="application/json" id="data">__DATA__</script>
<script>
const DATA=JSON.parse(document.getElementById('data').textContent),M=DATA.meta,ALL=DATA.txns,CUR=M.currency;
document.getElementById('acctlbl').textContent=M.account+' · '+(M.txn_count)+' transactions';
/* freshness + refresh. A stale dashboard that looks current is worse than one that admits it.
   Defined as a function and called from draw() — running it inline here would touch `esc` and
   `API` before their `const` declarations are initialized. */
function showFreshness(){const s=M.sync||{},el=document.getElementById('fresh');if(!el)return;
  const parts=[];
  if(s.label)parts.push(esc(s.label));
  if(s.reason)parts.push(esc(s.reason));
  el.className='fresh'+(s.stale?' stale':'');
  // "5 files weren't statements" invites "which ones, and is my data missing?". The skip reasons are
  // already recorded per file, so name them on demand instead of leaving a count to worry about.
  const detail=(s.skipped_reasons||[]).filter(Boolean).length
      ? ' <button onclick="showSkipped()">which?</button>' : '';
  el.innerHTML=parts.join(' · ')+detail+(API?' <button onclick="doRefresh(this)">refresh</button>':'');}
function showSkipped(){toast((M.sync.skipped_reasons||[]).filter(Boolean).join('\n\n'));}

/* ---- account switcher ----
   Every account in the store as a chip, cards marked as cards. A full page load per switch, because
   each account is a different dataset with its own card-vs-bank framing, tag distribution and
   coverage — re-fetching is honest and costs nothing locally, where a stale client-side merge of six
   accounts would be a whole new class of bug. */
function accSwitch(){
  const el=document.getElementById('accswitch');if(!el)return;
  const list=M.accounts||[];
  if(list.length<2){el.style.display='none';return;}   // one account needs no switcher
  el.innerHTML=list.map(a=>{
    const on=a.account===M.account;
    return `<a class="achip ${on?'on':''}" href="?t=${encodeURIComponent(API||'')}&a=${encodeURIComponent(a.account)}"
        title="${esc(a.account)} · ${a.count} transactions">
        ${I(a.is_card?'card':'bank')}<span>${esc(a.account)}</span></a>`;}).join('');}
function doRefresh(b){if(!API)return;b.disabled=true;b.textContent='checking…';
  post('/api/refresh',{}).then(r=>{
    if(r&&r.error){b.disabled=false;b.textContent='refresh';return toast(r.error);}
    if(r&&r.reason&&!r.ok){b.disabled=false;b.textContent='refresh';return toast(r.reason);}
    if(r&&(r.inserted||r.duplicate))location.reload();
    else{b.textContent='up to date';setTimeout(()=>{b.disabled=false;b.textContent='refresh';},2200);}
  });}

function fmt(p,o){o=o||{};let neg=p<0;p=Math.abs(Math.round(p));let w=Math.floor(p/100),f=String(p%100).padStart(2,'0');
  let s=String(w),out;if(s.length>3){let h=s.slice(0,-3),t=s.slice(-3),ps=[];while(h.length>2){ps.unshift(h.slice(-2));h=h.slice(0,-2);}if(h)ps.unshift(h);out=ps.join(',')+','+t;}else out=s;
  let sym=CUR==='INR'?'₹':'';return (neg?'-':(o.sign?'+':''))+sym+out+(o.noP?'':'.'+f);}
/* Rupees at full weight, paise dimmed: ₹97,000.00 reads as "97 thousand" at a glance instead of
   forcing the eye through six equally-loud digits. The paise are still THERE — this is a typographic
   change, never a rounding one, so every figure still reconciles against the statement to the paisa.
   Returns HTML, so it must not be passed through esc(). */
function fmtH(p,o){const s=fmt(p,o),i=s.lastIndexOf('.');
  return i<0?esc(s):esc(s.slice(0,i))+'<span class="ps">'+esc(s.slice(i))+'</span>';}
function fmtK(p){let r=Math.abs(p)/100,sym=CUR==='INR'?'₹':'',g=p<0?'-':'';
  if(r>=1e7)return g+sym+(r/1e7).toFixed(r>=1e8?0:1)+'Cr';if(r>=1e5)return g+sym+(r/1e5).toFixed(r>=1e6?0:1)+'L';
  if(r>=1e3)return g+sym+(r/1e3).toFixed(0)+'k';return g+sym+Math.round(r);}
const esc=s=>String(s==null?'':s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
/* For a value going inside a single-quoted onclick argument. esc() leaves ' alone, so the existing
   call sites STRIP apostrophes to stay safe — which mutates the key they then look the rows up by,
   so a merchant like "DOMINO'S" would open an empty screen. Escaping keeps the key intact. */
const escArg=s=>esc(s).replace(/\\/g,'\\\\').replace(/'/g,"\\'");
function I(n){const S=p=>`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">${p}</svg>`;const m={
  copy:'<rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10"/>',
  receipt:'<path d="M5 3v18l2-1 2 1 2-1 2 1 2-1 2 1V3l-2 1-2-1-2 1-2-1-2 1z"/><path d="M9 8h6M9 12h6"/>',
  trend:'<path d="M3 17l6-6 4 4 8-8M21 7v5h-5"/>',repeat:'<path d="M17 2l4 4-4 4M3 11V9a4 4 0 0 1 4-4h14M7 22l-4-4 4-4M21 13v2a4 4 0 0 1-4 4H3"/>',
  crown:'<path d="M3 7l4 4 5-7 5 7 4-4v11H3z"/>',gift:'<rect x="3" y="8" width="18" height="4"/><path d="M12 8v13M5 12v9h14v-9M12 8a3 3 0 1 0-3-3c0 2 3 3 3 3zM12 8a3 3 0 1 1 3-3c0 2-3 3-3 3z"/>',
  check:'<circle cx="12" cy="12" r="9"/><path d="M8 12l3 3 5-6"/>',
  food:'<path d="M3 2v7a3 3 0 0 0 6 0V2M6 2v20M21 15V2a5 5 0 0 0-3 5v6h3v7"/>',grocery:'<path d="M3 3h2l2 12h11l2-8H6"/><circle cx="9" cy="20" r="1"/><circle cx="17" cy="20" r="1"/>',
  home:'<path d="M3 10 12 3l9 7v10a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z"/>',bill:'<path d="M13 2 3 14h7l-1 8 10-12h-7z"/>',
  invest:'<path d="M3 17l6-6 4 4 8-8M21 7v5h-5"/>',card:'<rect x="2" y="5" width="20" height="14" rx="2"/><path d="M2 10h20"/>',
  bank:'<path d="M3 10l9-6 9 6M5 10v9h14v-9M9 19v-5h6v5"/>',
  cash:'<rect x="3" y="6" width="18" height="12" rx="2"/><circle cx="12" cy="12" r="2.5"/>',transfer:'<path d="M7 17V7m0 0L3 11m4-4 4 4M17 7v10m0 0 4-4m-4 4-4-4"/>',
  dot:'<circle cx="12" cy="12" r="9"/>',srch:'<circle cx="11" cy="11" r="7"/><path d="M21 21l-4-4"/>',list:'<path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/>'};
  return S(m[n]||m.dot);}
function catIcon(c){c=(c||'').toLowerCase();if(/food|dining/.test(c))return'food';if(/grocer/.test(c))return'grocery';
  if(/rent|home/.test(c))return'home';if(/bill|utilit/.test(c))return'bill';if(/invest/.test(c))return'invest';
  if(/card/.test(c))return'card';if(/cash|atm/.test(c))return'cash';if(/transfer|people/.test(c))return'transfer';return'dot';}

/* ---- netting modes ----
   Two different things, deliberately NOT one switch:

   'gross'  — every row as the bank printed it. The default, and always available: it is the only
              view that reconciles line-by-line against a statement.
   'clean'  — drop CANCELLED pairs. A failed booking (₹1,554 out, ₹1,554 back the same hour, same
              bank reference) is not spending; leaving it in overstates the total. This is error
              CORRECTION, so it is safe to make prominent.
   'net'    — additionally net off everyone money moved both ways with. ₹5,000 lent in December and
              repaid in March are both REAL transfers; netting them answers "what am I actually out
              of pocket with this person?". That is a PREFERENCE, not a correction, which is why it
              is a separate mode and never the default.

   A pair is only dropped when BOTH legs are inside the selected period. Otherwise picking "last
   month" would remove a charge whose refund lands next month, and the month would under-report. */
let NET='gross';

/* ---- shared charges: billed vs my share ----
   A SEPARATE axis from netting, deliberately. Netting DROPS rows; this RESCALES them, so the two
   compose rather than compete (you can view your share of a cancelled-pairs-removed period).

   `billed` is the default and stays the default: it is the only view that reconciles line-by-line
   against the card statement. `mine` swaps every split row's amount for the user's own share, which
   answers "what did I actually spend" — the question a shared dinner makes unanswerable otherwise. */
let SHARE='billed';
function shareRows(rows){
  if(SHARE!=='mine')return rows;
  return rows.map(t=>t.mine==null?t:{...t,a:t.mine,split:1});}
function setShare(s){SHARE=s;draw();}
/* what the current period holds, so the toggle can describe itself and stay hidden when useless */
function splitInfo(rows){
  let n=0,billed=0,mine=0;
  for(const t of rows){if(t.mine==null)continue;n++;billed+=t.a;mine+=t.mine;}
  return {n,billed,mine,recoverable:billed-mine};}

function netFilter(rows){
  if(NET==='gross')return rows;
  const have=new Set(rows.map(t=>t.ref));
  // a reversal needs both halves present, else the surviving half stays and stays honest
  const drop=new Set();
  for(const t of rows)if(t.rev&&have.has(t.rev)){drop.add(t.ref);drop.add(t.rev);}
  let out=rows.filter(t=>!drop.has(t.ref));
  if(NET!=='net')return out;
  /* Person-netting: for each two-way counterparty keep only the NET direction, as one synthetic row
     per person. Shrinking individual rows would produce amounts that appear on no statement; one
     labelled row per person is auditable and its total is exact. */
  const by={};
  for(const t of out){if(!t.cp)continue;(by[t.cp]=by[t.cp]||[]).push(t);}
  const netted=[];const consumed=new Set();
  for(const cp in by){
    const rs=by[cp];
    const paid=rs.filter(t=>t.dir==='D').reduce((s,t)=>s+t.a,0);
    const got=rs.filter(t=>t.dir==='C').reduce((s,t)=>s+t.a,0);
    if(!paid||!got)continue;                       // one-way payee: nothing to net
    rs.forEach(t=>consumed.add(t.ref));
    const diff=paid-got;
    if(diff===0)continue;                           // fully settled: both sides vanish
    const last=rs.slice().sort((a,b)=>(a.d<b.d?-1:1)).slice(-1)[0];
    netted.push({...last,a:Math.abs(diff),dir:diff>0?'D':'C',
                 f:diff>0?(last.f==='v'?'v':'s'):'i',
                 m:(last.m||cp)+' (net)',synthetic:1});}
  return out.filter(t=>!consumed.has(t.ref)).concat(netted);}

/* ---- compute (integer paise) ----
   Three-way flow, mirroring the server: self-transfers ('x') are excluded from BOTH sides, and
   investments ('v') are kept out of `out` so "spent" never counts money you still own. */
function inRange(t,f,tt){return (!f||t.d>=f)&&(!tt||t.d<=tt);}
function compute(rows){let inn=0,out=0,inv=0,slf=0,slfN=0;
  const catT={},catC={},merT={},merC={},recMon={},recAmt={},moOut={},merName={};
  const srcT={},srcC={},moIn={},moInv={},invT={},invC={},invN={};  // by source / by holding / per month
  for(const t of rows){
    if(t.f==='x'){slf+=t.a;slfN++;continue;}
    if(t.f==='i'){inn+=t.a;
      const s=t.src||'Other income';srcT[s]=(srcT[s]||0)+t.a;srcC[s]=(srcC[s]||0)+1;
      if(t.mo)moIn[t.mo]=(moIn[t.mo]||0)+t.a;
      continue;}
    if(t.f==='v'){inv+=t.a;
      // case-fold the key so ZERODHA/Zerodha stay ONE holding, same rule as the merchant roll-up;
      // keep the first-seen spelling for display
      const raw=t.m||t.c||'Other',k=raw.trim().toLowerCase();
      invT[k]=(invT[k]||0)+t.a;invC[k]=(invC[k]||0)+1;invN[k]=invN[k]||raw;
      if(t.mo)moInv[t.mo]=(moInv[t.mo]||0)+t.a;}
    else{out+=t.a;if(t.mo)moOut[t.mo]=(moOut[t.mo]||0)+t.a;}
    catT[t.c]=(catT[t.c]||0)+t.a;catC[t.c]=(catC[t.c]||0)+1;
    // merchant keys are case-folded so "ZERODHA"/"Zerodha" stay one payee, as on the server
    if(t.m){const mk=t.m.trim().toLowerCase();
      merT[mk]=(merT[mk]||0)+t.a;merC[mk]=(merC[mk]||0)+1;merName[mk]=merName[mk]||t.m;
      (recMon[mk]=recMon[mk]||new Set()).add(t.mo);(recAmt[mk]=recAmt[mk]||[]).push(t.a);}}
  const cats=Object.keys(catT).map(c=>({c,a:catT[c],n:catC[c]})).sort((x,y)=>y.a-x.a);
  // denominator for category shares: everything the categories actually contain (spend+investment)
  const catTotal=cats.reduce((s,c)=>s+c.a,0);
  const med=a=>{const s=a.slice().sort((x,y)=>x-y),n=s.length;return n?(n%2?s[(n-1)/2]:(s[n/2-1]+s[n/2])/2):0;};
  const recurring=Object.keys(recMon).filter(m=>recMon[m].size>=3)
    .map(m=>({m:merName[m],months:recMon[m].size,med:med(recAmt[m]),total:merT[m]}))
    .sort((a,b)=>b.total-a.total).slice(0,6);
  const bal=rows.filter(t=>t.b!=null).slice(-1)[0];
  const nMo=Object.keys(moOut).length||1;
  /* Ranked breakdowns with an honest tail. Same rule as the server's incoming_breakdown: fold the
     remainder into a labelled "Other" row rather than slicing it off, so the parts still sum to the
     total. A list that looks complete but doesn't add up is worse than a longer list. */
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
  return {inn,out,inv,slf,slfN,cats,catTotal,recurring,closing:bal?bal.b:null,count:rows.length,
          moOut,moIn,moInv,months:nMo,avgOut:Math.round(out/nMo),avgIn:Math.round(inn/nMoIn),
          srcs:rank(srcT,srcC,inn,6),invs:rank(invT,invC,inv,6,invN),
          // top payees for the avatar grid; merT is already case-folded and keyed, so this is a sort
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
/* ONE control, presets first, custom LAST.
   Previously there were two: a "custom range" chip under the hero and a separate W/M/Y/All segment
   buried in the cash-flow card — two ways to set the same thing, with the rarest option (a manual
   date pair) given the most prominence. Presets answer almost every question; the date inputs only
   appear once someone explicitly asks for them. */
/* A preset is [key, label, span]. span is 'Nd' (days) or 'Nm' (calendar months), null = everything.
   Months are calendar months, not 30-day blocks, so "6M" lines up with statement periods. */
const PRESETS=[['W','1W','7d'],['M','1M','1m'],['3M','3M','3m'],['6M','6M','6m'],
               ['Y','1Y','12m'],['5Y','5Y','60m'],['all','All',null]];
function presetFrom(key){
  const p=PRESETS.find(x=>x[0]===key);
  if(!p||!p[2]||!M.max_date)return '';
  const n=parseInt(p[2],10);
  return p[2].slice(-1)==='d' ? shiftDays(M.max_date,-(n-1)) : monthsBack(n);}
/* Period first, THEN netting — netFilter needs to know which rows are in range to decide whether both
   legs of a pair are present. Every screen goes through here, so no view can disagree about the mode. */
/* period -> netting -> share. Share last: it only rewrites amounts, so it must see whichever rows
   survived netting rather than rescaling rows that are about to be dropped. */
function rangeFilter(){return shareRows(netFilter(periodRows()));}
function periodRows(){
  if(RANGE==='C')return ALL.filter(t=>t.d&&inRange(t,CF,CT));
  if(RANGE==='S'){const c=salaryCycle();return c?ALL.filter(t=>t.d&&inRange(t,c.f,c.t)):ALL;}
  const from=presetFrom(RANGE);
  if(!from)return ALL;                          // "All", unknown key, or no dates -> everything
  return ALL.filter(t=>t.d&&t.d>=from);}
function rangeLabel(){
  if(RANGE==='C')return (CF||'start')+' → '+(CT||'now');
  if(RANGE==='S'){const c=salaryCycle();return c?'salary cycle':'salary cycle';}
  return {W:'· last week',M:'· last month','3M':'· last 3 months','6M':'· last 6 months',
          Y:'· last year','5Y':'· last 5 years',all:'· all time'}[RANGE]||'';}
/* The whole period control: presets, then Cycle if a salary day was detected, then custom.
   Rendered ONCE per screen, right under the hero it modifies. */
function rangeRow(){
  const chips=PRESETS.map(([k,l])=>
      `<button class="pchip ${RANGE===k?'on':''}" onclick="setR('${k}')">${l}</button>`).join('');
  const cycle=M.salary_day
      ? `<button class="pchip ${RANGE==='S'?'on':''}" onclick="setR('S')" title="your salary cycle, not the calendar month">Cycle</button>` : '';
  const cal='<svg viewBox="0 0 24 24" stroke-linecap="round"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M8 3v4M16 3v4M3 10h18"/></svg>';
  const custom=`<button class="pcustom ${RANGE==='C'?'on':''}" onclick="setR('C')" title="pick exact dates">${cal}Custom</button>`;
  const dates=RANGE==='C'
      ? `<div class="drow"><input type="date" value="${CF}" max="${M.max_date||''}" onchange="setCF(this.value)">
         <span class="to">→</span>
         <input type="date" value="${CT}" max="${M.max_date||''}" onchange="setCT(this.value)"></div>` : '';
  return `<div class="pwrap"><div class="prow">${chips}${cycle}</div>${custom}</div>${dates}${netRow()}`;}

/* The netting control. Only rendered when the data HAS something to net — on an account with no
   cancelled pairs and no two-way counterparties this is three dead buttons, and a control that never
   does anything trains you to ignore controls. */
function netRow(){
  const c=countable();
  const sp=splitInfo(periodRows());
  if(!c.pairs&&!c.people&&!sp.n)return '';
  const b=(k,lbl,title)=>`<button class="nchip ${NET===k?'on':''}" onclick="setNet('${k}')" title="${title}">${lbl}</button>`;
  const chips=[b('gross','gross','every row exactly as the bank printed it')]
    .concat(c.pairs?[b('clean','hide cancelled',`${c.pairs} cancelled pair${c.pairs!==1?'s':''} — money that went out and came straight back`)]:[])
    .concat(c.people?[b('net','net per person',`${c.people} people money moved both ways with`)]:[]);
  /* The share toggle appears only once something IS split — before that it is a control that cannot
     change any number, and those teach you to ignore controls. */
  const share=sp.n?`<span class="nsep"></span>
    <button class="nchip ${SHARE==='billed'?'on':''}" onclick="setShare('billed')"
      title="the full amount the bank billed — what reconciles against your statement">billed</button>
    <button class="nchip ${SHARE==='mine'?'on':''}" onclick="setShare('mine')"
      title="${sp.n} shared charge${sp.n!==1?'s':''} · ${fmtK(sp.recoverable)} is someone else's">my share</button>`:'';
  return `<div class="nrow">${chips.join('')}${share}${netNote(c)}${shareNote(sp)}</div>`;}

/* Same rule as netNote: if a mode changes the headline, say by how much, in money, every time. */
function shareNote(sp){
  if(SHARE!=='mine'||!sp.n)return '';
  return `<span class="nnote">−${fmtK(sp.recoverable)} recoverable from others</span>`;}

/* What the current mode actually removed, in money. A mode that silently shrinks every total is the
   thing this whole codebase is most careful about — so it says so, every time, in the same place. */
function netNote(c){
  if(NET==='gross')return '';
  const amt=NET==='clean'?c.cancelledAmt:c.cancelledAmt+c.offsetAmt;
  const what=NET==='clean'?'cancelled':'cancelled &amp; settled';
  // clickable: a figure removed from every total must be inspectable, not asserted
  return `<button class="nnote link" onclick="go('netting')">−${fmtK(amt)} ${what} · what?</button>`;}

/* Counts for the CURRENT period, not all-time: the buttons must describe what they would do here. */
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

/* One back control, used by every drill-down screen. Naming the DESTINATION ("back to people") beats a
   naked chevron: it tells you where you land before you commit, which matters most on the one screen
   that has two possible parents (a merchant reached from a tag, or from the ledger). */
function backBtn(onclick,dest){
  const arrow='<span class="barrow"><svg viewBox="0 0 24 24" stroke-linecap="round" stroke-linejoin="round"><path d="M15 5l-7 7 7 7"/></svg></span>';
  return `<button class="back" onclick="${onclick}">${arrow}<span>${dest?`back to <b>${esc(dest)}</b>`:'back'}</span></button>`;}

/* ---- what got netted ----
   The audit trail. Netting removes money from every total on the home screen, so there has to be one
   place that lists exactly which rows and why — otherwise "hide cancelled" is an unverifiable claim
   about the user's own money. Reversals show BOTH legs and their bank reference; two-way people show
   paid / received / net so the arithmetic is checkable by eye. */
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
  const pairRows=pairs.map(([d,c])=>{
    const m=meta[d.ref]||{},days=m.days!=null?m.days:'';
    return `<div class="crow" onclick="openTxn('${esc(d.ref)}')">
      <div class="ci">${I('repeat')}</div>
      <div class="cm"><div class="cn">${esc(d.m||d.desc)}</div>
        <div class="td">${esc(dayLabel(d.d))} → ${esc(dayLabel(c.d))}${days!==''?` · ${days===0?'same day':days+'d'}`:''}${m.bank_ref?` · ref ${esc(m.bank_ref)}`:''}</div></div>
      <div class="cr"><div class="ca num">${fmtH(d.a)}</div>
        <div class="cp">${m.confidence==='certain'?'bank reference matches':'amount &amp; date'}</div></div></div>`;}).join('');

  const by={};rows.forEach(t=>{if(t.cp)(by[t.cp]=by[t.cp]||[]).push(t);});
  const ppl=[];
  for(const cp in by){
    const rs=by[cp];
    const paid=rs.filter(t=>t.dir==='D').reduce((s,t)=>s+t.a,0);
    const got=rs.filter(t=>t.dir==='C').reduce((s,t)=>s+t.a,0);
    if(paid&&got)ppl.push({cp,name:rs[0].m||cp,paid,got,net:paid-got,off:Math.min(paid,got),n:rs.length});}
  ppl.sort((a,b)=>b.off-a.off);
  const pplRows=ppl.map(p=>`<div class="crow">
      <div class="ci">${I('transfer')}</div>
      <div class="cm"><div class="cn">${esc(p.name)}</div>
        <div class="td">paid ${fmtK(p.paid)} · got back ${fmtK(p.got)} · ${p.n} rows</div></div>
      <div class="cr"><div class="ca num ${p.net<0?'in':''}">${p.net===0?'settled':fmt(Math.abs(p.net))}</div>
        <div class="cp">${p.net>0?'you are owed':p.net<0?'you owe':'square'}</div></div></div>`).join('');

  return `<div class="view on">
    ${backBtn("go('home')",'home')}
    <div class="hero rise"><div class="l">netting</div>
      <div class="big num">${fmt(pairs.reduce((s,p)=>s+p[0].a,0))}</div>
      <div class="avg">cancelled across ${pairs.length} pair${pairs.length!==1?'s':''} ${rangeLabel()}</div></div>
    <div class="note rise">a cancelled pair is money that left and came straight back — a failed
      booking or a bounced transfer. netting people off is different: both transfers were real, so
      "net per person" is a preference, not a correction.</div>
    <div class="st"><h2>cancelled pairs</h2></div>
    <div class="list rise">${pairRows||'<div class="empty">nothing cancelled in range</div>'}</div>
    <div class="st"><h2>money moved both ways</h2></div>
    <div class="list rise">${pplRows||'<div class="empty">no two-way counterparties in range</div>'}</div>
  </div>`;}

function home(){
  const rows=rangeFilter(),R=compute(rows);
  const deltaHtml=heroDelta(R);
  const hv=heroValue(R);
  // insights
  let ins='';DATA.insights.forEach(c=>{const cls=c.severity>=3?'alert':c.severity===0?'positive':'';
    ins+=`<div class="ins ${cls}"><div class="ic">${I(c.icon)}</div><div class="it">${esc(c.title)}</div><div class="cp">${hl(c.copy)}</div></div>`;});
  // cashflow bar
  const tot=R.inn+R.out||1,inW=Math.round(R.inn/tot*100);
  // categories top5
  let cats='';R.cats.slice(0,5).forEach(c=>{const f=c.a/(R.cats[0].a||1);
    cats+=`<div class="crow" onclick="openTag('${escArg(c.c)}')"><div class="ci">${I(catIcon(c.c))}</div><div class="cm"><div class="cn">${esc(c.c)}</div><div class="cb"><i style="width:${(f*100).toFixed(0)}%"></i></div></div><div class="cr"><div class="ca num">${fmtH(c.a)}</div><div class="cp">${(c.a/(R.catTotal||1)*100).toFixed(0)}%</div></div></div>`;});
  // recurring
  let rec='';R.recurring.slice(0,4).forEach(r=>{rec+=`<div class="trow"><div class="ti">${(r.m||'?').slice(0,2).toUpperCase()}</div><div class="tm"><div class="tn">${esc(r.m)}</div><div class="td">seen ${r.months} months</div></div><div class="tv num">${fmt(r.med)}</div></div>`;});
  // recent
  let rec2='';rows.slice().reverse().slice(0,4).forEach(t=>{rec2+=txRow(t,true);});

  // avg-per-month sub-line: the comparative CRED puts under every total
  const avgLine=hv.avg?`<div class="avg num">avg per month ${fmtK(hv.avg)}</div>`:'';
  // self-transfer disclosure — never silently drop money from the totals
  const slfNote=R.slfN?`<div class="note rise">self-transfers are excluded · ${fmtK(R.slf)} across ${R.slfN} transactions</div>`:'';
  // the breakdown that matches whichever side of the flow the hero is showing
  const detail=FLOW==='in'?sourceCard(R):FLOW==='inv'?investCard(R):
               `<div class="st"><h2>where it went</h2><a onclick="go('spends')">see all</a></div>
                <div class="list rise">${cats||'<div class="empty">no spends in range</div>'}</div>`;

  return `<div class="view on">
    <div class="hero rise"><div class="l">${hv.label} ${rangeLabel()}</div><div class="big num" id="hero" data-to="${hv.amount}">${fmtH(hv.amount)}</div>${deltaHtml}${avgLine}</div>
    ${rangeRow()}
    ${slfNote}
    ${DATA.insights.length?`<div class="st"><h2>for you</h2></div><div class="insrow">${ins}</div>`:''}
    ${M.is_card?cardFlowCard():bankFlowCard(R,inW)}
    ${monthChart(R)}
    ${FLOW==='out'?topSpendsGrid(R):''}
    ${detail}
    ${rec?`<div class="st"><h2>recurring</h2><a onclick="go('recurring')">see all</a></div><div class="list rise">${rec}</div>`:''}
    <div class="st"><h2>recent</h2><a onclick="go('search')">view all</a></div>
    <div class="list rise">${rec2||'<div class="empty">nothing here</div>'}</div>
  </div>`;
}

/* ---- which side of the flow the hero shows ----
   Three numbers were computed but only one was ever displayed at full precision: `spends`. Incoming
   and investments existed solely as abbreviated tiles ("₹73L"), so the answer to "what came in?" was
   rounded to two significant figures and had no breakdown behind it at all. The tiles are now the
   control that swaps the hero. Spends stays the default — overspending is the thing you act on. */
let FLOW='out';
const FLOWS={out:{label:'spent',key:'out',avg:'avgOut'},
             in:{label:'received',key:'inn',avg:'avgIn'},
             inv:{label:'invested',key:'inv',avg:null}};
function heroValue(R){
  const f=FLOWS[FLOW]||FLOWS.out;
  return {label:M.is_card&&FLOW==='out'?'charged':f.label,
          amount:R[f.key],
          avg:(f.avg&&R.months>1)?R[f.avg]:0};}
function setFlow(f){FLOW=f;draw();}

/* ---- flow cards ----
   A bank account and a credit card need different frames. On a bank account "net" is what stayed. On
   a card the spending IS the balance owed, so a net figure is computable but meaningless — the honest
   summary is charges, what you paid off, and what came back (refunds + rewards). */
function bankFlowCard(R,inW){
  /* Three extruded, banknote-textured bars — one per flow — replacing the flat in-vs-out ribbon.
     The ribbon could only ever show two quantities as a proportion; three bars on a shared scale show
     the actual SHAPE of the month (earned a lot, invested nothing, spent most of it), and each bar is
     still the button that promotes its figure into the hero. */
  const mx=Math.max(R.inn,R.inv,R.out,1);
  const bar=(k,label,cls,amt)=>{
    const h=Math.max(2,Math.round(amt/mx*100));
    return `<button class="fbar ${FLOW===k?'on':''}" onclick="setFlow('${k}')" aria-pressed="${FLOW===k}" title="${label}">
      <div class="fbcol">
        <div class="fbi ${cls} guil" style="height:${h}%"><span class="fbv">${fmtK(amt)}</span></div></div>
      <div class="fbl">${label}</div></button>`;};
  return `<div class="card rise"><div class="mtop"><div><div class="l">your cash flow</div>
      <div class="v num">${fmt(R.inn-R.out-R.inv,{sign:true})} net</div></div></div>
    <div class="fbars">${bar('in','incoming','in',R.inn)}
      ${bar('inv','investments','inv',R.inv)}
      ${bar('out','spends','out',R.out)}</div>
    <div class="fhint">tap a bar to see it broken down</div></div>`;}

/* ---- top spends as an avatar grid ----
   A 3-column grid of payee discs, borrowed from CRED. A ranked bar list answers "how do these compare"
   but a grid answers "who am I paying", which is the question you actually arrive with — and faces
   (or initials) are recognised far faster than left-aligned text. */
function topSpendsGrid(R){
  const top=R.mers.slice(0,6);
  if(top.length<3)return '';        // a grid of one or two is just a worse list
  const cells=top.map(m=>`<button class="gcell" onclick="openMerchant('${escArg(m.name)}')">
      ${avatar(m.name)}
      <div class="gamt num">${fmtH(m.a)}</div>
      <div class="gnm">${esc(m.name)}</div></button>`).join('');
  return `<div class="st"><h2>top spends</h2><a onclick="go('spends')">see all</a></div>
    <div class="grid3 rise">${cells}</div>`;}

/* A payee disc: the category glyph when we know the category, otherwise the initial on a tinted disc.
   The tint is derived from the NAME so it is stable across renders — the same payee is always the same
   colour, which is what makes a grid scannable at all. */
function avatar(name){
  const n=(name||'?').trim();
  let h=0;for(let i=0;i<n.length;i++)h=(h*31+n.charCodeAt(i))%360;
  const init=esc(n[0]?n[0].toUpperCase():'?');
  return `<div class="gav init" style="background:hsl(${h} 42% 88%);border-color:hsl(${h} 34% 78%)">${init}</div>`;}

/* ---- donut, one hue tinted by rank ----
   CRED uses a donut but never a rainbow: it is ONE hue stepped light-to-dark by rank, which keeps the
   ranking legible (darkest = biggest) instead of asking the eye to map arbitrary colours to names.
   Rendered as a conic-gradient with a mask for the hole — no SVG, no library, no arc arithmetic.
   Only worth drawing above ~2 slices; below that a bar list says the same thing with less ink. */
const FLOWHUE={out:[186,138,216],in:[111,158,216],inv:[216,185,138]};
function tint(flow,i,n){
  const [r,g,b]=FLOWHUE[flow]||FLOWHUE.out;
  // step toward the surface for smaller slices; never fully fade, or the tail vanishes
  const f=n<=1?0:(i/(n-1))*0.62;
  const m=v=>Math.round(v+(252-v)*f);
  return `rgb(${m(r)},${m(g)},${m(b)})`;}
function donut(rows,total,label){
  if(rows.length<2)return '';
  let acc=0;const stops=rows.map((s,i)=>{
    const from=acc/total*100;acc+=s.a;const to=acc/total*100;
    return `${tint(FLOW,i,rows.length)} ${from.toFixed(2)}% ${to.toFixed(2)}%`;}).join(',');
  return `<div class="donut rise"><div class="dwrap">
      <div class="dring" style="background:conic-gradient(${stops})"></div>
      <div class="dmid"><div><div class="dtot num">${fmtK(total)}</div>
      <div class="dlab">${esc(label)}</div></div></div></div></div>`;}

/* ---- incoming, broken down by source ----
   `incoming_sources` was computed on the server, embedded in the payload, and then never rendered —
   ₹72L of credits reduced to one tile. This recomputes it from the rows in the SELECTED period
   rather than reading the server's all-time summary, so it can't disagree with the hero above it. */
/* Donut + legend, where the legend swatch is the same tint as its arc — so identity is never carried
   by colour alone (each row still has its name, amount and share in text). */
function breakdownCard(rows,total,title,label,icon){
  if(!rows.length)return `<div class="st"><h2>${title}</h2></div><div class="empty">nothing in range</div>`;
  const n=rows.length;
  const list=rows.map((s,i)=>`<div class="crow">
      <div class="dsw" style="background:${tint(FLOW,i,n)}"></div>
      <div class="cm"><div class="cn">${esc(s.k)}</div></div>
      <div class="cr"><div class="ca num">${fmtH(s.a)}</div><div class="cp">${(s.share*100).toFixed(1)}% · ${s.n}×</div></div>
    </div>`).join('');
  return `${donut(rows,total,label)}<div class="st"><h2>${title}</h2></div>
    <div class="list rise">${list}</div>`;}

function sourceCard(R){return breakdownCard(R.srcs,R.inn,'where it came from','incoming');}
function investCard(R){return breakdownCard(R.invs,R.inv,'what you put away','invested');}

function srcIcon(s){const k=(s||'').toLowerCase();
  return k.includes('salary')?'cash':k.includes('people')?'home':k.includes('refund')?'repeat':
         k.includes('interest')?'trend':k.includes('cashback')||k.includes('reward')?'gift':'cash';}

function cardFlowCard(){
  const c=DATA.card;if(!c)return '';
  const owed=c.net_new_debt, paidOff=owed<0;
  const back=c.refunds+c.rewards;
  const total=c.charges+c.fees||1, payW=Math.min(100,Math.round(c.payments/total*100));
  return `<div class="card rise"><div class="mtop"><div><div class="l">this card</div>
      <div class="v num">${fmtK(Math.abs(owed))} <span class="avgt">${paidOff?'paid off beyond charges':'added to balance'}</span></div></div></div>
    <div class="flow">
      <div class="fc"><div class="fl">charges</div><div class="fv fout num">${fmtK(c.charges)}</div></div>
      <div class="fc"><div class="fl">you paid</div><div class="fv fin num">${fmtK(c.payments)}</div></div>
      <div class="fc"><div class="fl">back to you</div><div class="fv fin num">${fmtK(back)}</div></div></div>
    <div class="flowbar"><span class="bin" style="width:${payW}%"></span><span class="bout" style="width:${100-payW}%"></span></div>
    ${c.fees?`<div class="cardfee">${fmtK(c.fees)} of that was interest and fees — the avoidable part.</div>`:''}
    ${c.rewards?`<div class="cardfee">${fmtK(c.rewards)} came back as cashback and rewards.</div>`:''}
  </div>`;}

/* ---- hero comparison ----
   Compare LIKE WITH LIKE: the same span of days immediately before the selected range, using the
   same flow filter as the hero (so investments, card-bill payments and self-transfers are excluded
   from both sides). Three bugs this replaces:
     1. the delta always compared the last two calendar months even when the hero showed all-time,
        so an all-time total was captioned with a one-month change;
     2. it summed every debit, counting investments and card payments as spending;
     3. the newest month is usually partial, so a 3-day-old month vs a full one always looked like a
        collapse. A partial period is now compared against the SAME number of days. */
/* Sum the SAME flow bucket the hero is showing. Comparing "received this month" against "spent last
   month" would be a nonsense percentage, so the bucket is a parameter, not a constant. */
const FLOW_CODE={out:'s',in:'i',inv:'v'};
function flowBetween(from,to,code){
  // netFilter here too, or the comparison period would be gross while the hero is netted — the
  // percentage would then be measuring the mode change, not a change in behaviour
  return netFilter(ALL.filter(t=>t.d&&t.d>=from&&t.d<=to))
         .filter(t=>t.f===code).reduce((s,t)=>s+t.a,0);}
function shiftDays(iso,n){const d=new Date(iso+'T00:00:00Z');d.setUTCDate(d.getUTCDate()+n);
  return d.toISOString().slice(0,10);}
function currentWindow(){
  const dated=ALL.filter(t=>t.d).map(t=>t.d).sort();
  if(!dated.length)return null;
  const rows=rangeFilter().filter(t=>t.d).map(t=>t.d).sort();
  if(!rows.length)return null;
  return {from:rows[0], to:rows[rows.length-1], first:dated[0]};}
function heroDelta(R){
  const w=currentWindow();
  if(!w)return '';
  const days=Math.round((new Date(w.to)-new Date(w.from))/864e5)+1;
  const prevTo=shiftDays(w.from,-1), prevFrom=shiftDays(prevTo,-(days-1));
  // no comparable history -> say nothing rather than compare against a truncated period
  if(prevFrom<w.first)return '';
  const prev=flowBetween(prevFrom,prevTo,FLOW_CODE[FLOW]||'s');
  if(prev<=0)return '';
  const now=heroValue(R).amount;
  const pc=Math.round((now/prev-1)*100), up=pc>0;
  // more money in is GOOD, more money out is BAD — the same arrow must not carry the same colour
  const good=FLOW==='out'?!up:up;
  const label=days<=8?'week':days<=32?'month':days<=95?'quarter':days<=370?'year':`${days} days`;
  return `<div class="sub"><span class="${good?'up':'down'}">${up?'↑':'↓'} ${Math.abs(pc)}%</span>`
       + ` vs previous ${label} · ${fmt(prev)}</div>`;}

/* ---- monthly bars with an AVG reference line (CRED's "past trends") ---- */
/* Built from the CLIENT's per-month map, not the server's `DATA.monthly`.
   That field is a fixed 12-month, spend-only series, so the chart sat there unchanged while the hero
   above it switched to incoming or investments and while the period picker narrowed the range —
   a chart captioned "past trends" that silently answered a different question than the number above
   it. Same `moOut`/`moIn`/`moInv` maps compute() already builds, so nothing is derived twice. */
const MOKEY={out:'moOut',in:'moIn',inv:'moInv'};
function monthChart(R){
  const by=R[MOKEY[FLOW]||'moOut']||{};
  const keys=Object.keys(by).sort();
  if(keys.length<2)return'';                       // one bar is not a trend
  const shown=keys.slice(-12),hidden=keys.length-shown.length;
  const vals=shown.map(k=>by[k]);
  const peak=Math.max(...vals)||1,avg=Math.round(vals.reduce((s,v)=>s+v,0)/vals.length);
  const avgPct=Math.min(100,avg/peak*100);
  const cls=FLOW==='in'?'in':FLOW==='inv'?'inv':'';
  /* A callout pinned to the newest bar, plus the average written ON its own line. Previously the line
     was an unlabelled dash across the chart and the current month had no marker at all — so neither
     of the two numbers a trend chart exists to convey was actually stated. */
  const bars=shown.map((k,i)=>{const h=Math.max(2,by[k]/peak*100),last=i===shown.length-1;
    return `<div class="bcol"><div class="bwrap">${last?`<span class="bcall num">${fmtK(by[k])}</span>`:''}<i class="${cls} ${last?'on':''}" style="height:${h}%" title="${esc(k)} · ${fmt(by[k])}"></i></div>
      <div class="blab">${esc(k.slice(5))}</div><div class="bval num">${fmtK(by[k])}</div></div>`;}).join('');
  // say when the chart is a window over a longer history — an unlabelled 12-month chart next to an
  // all-time hero number reads as "this is everything", and its average as an all-time average
  const word={out:'spend',in:'income',inv:'investing'}[FLOW]||'spend';
  // "all time" is only true when the chart shows every month AND the picker isn't filtering. With a
  // range selected it was captioning six filtered bars as the whole history.
  const scope=hidden?`last ${shown.length} months`
             :(RANGE==='all'?'all time':`${shown.length} months`);
  return `<div class="card rise"><div class="mtop"><div><div class="l">${word} trends · ${scope}</div>
      <div class="v num">${fmtK(avg)} <span class="avgt">avg / month</span></div></div></div>
    <div class="chart"><span class="avgline" style="bottom:${avgPct}%"></span>
      <span class="avgpill num" style="bottom:${avgPct}%">AVG ${fmtK(avg)}</span>${bars}</div>
    ${hidden?`<div class="cardfee">${hidden} earlier month${hidden!==1?'s':''} not shown.</div>`:''}</div>`;}
function hl(s){return esc(s).replace(/(₹[\d,]+(?:\.\d+)?(?:Cr|L|k)?)/g,'<b>$1</b>');}

/* ---- spends view: tag-wise grouping, sortable ---- */
function spends(){const rows0=rangeFilter(),R=compute(rows0);
  let cats=R.cats.slice();
  if(SORT==='low')cats.reverse();
  else if(SORT==='count')cats.sort((a,b)=>b.n-a.n);
  const maxA=Math.max(...cats.map(c=>c.a),1);
  let rows='';cats.forEach(c=>{
    rows+=`<div class="crow" onclick="openTag('${escArg(c.c)}')"><div class="ci">${I(catIcon(c.c))}</div><div class="cm"><div class="cn">${esc(c.c)}</div><div class="cb"><i style="width:${(c.a/maxA*100).toFixed(0)}%"></i></div></div><div class="cr"><div class="ca num">${fmtH(c.a)}</div><div class="cp">${(c.a/(R.catTotal||1)*100).toFixed(1)}% · ${c.n}×</div></div></div>`;});
  const nextSort={high:'low',low:'count',count:'high'}[SORT],
        sortLbl={high:'high to low',low:'low to high',count:'most frequent'}[SORT];
  return `<div class="view on">
    <div class="hero rise"><div class="l">spent ${rangeLabel()}</div><div class="big num">${fmt(R.out)}</div>
      ${R.months>1?`<div class="avg num">avg per month ${fmtK(R.avgOut)}</div>`:''}</div>
    ${rangeRow()}
    <div class="st"><h2>by tag</h2><button class="sortb" onclick="setSort('${nextSort}')">${sortLbl} ⇅</button></div>
    <div class="list rise">${rows||'<div class="empty">no spends in range</div>'}</div>
    ${(DATA.review_queue||[]).length?`<div class="st"><h2>needs a tag</h2></div>
      <div class="note rise">${DATA.untagged} transactions couldn't be tagged automatically. fixing the biggest ones sharpens every number above.</div>
      <div class="list rise">${DATA.review_queue.slice(0,6).map(r=>`<div class="trow" onclick="openMerchant('${escArg(r.merchant)}')"><div class="ti">${esc((r.merchant||'?').slice(0,2)).toUpperCase()}</div><div class="tm"><div class="tn">${esc(r.merchant)}</div><div class="td">${r.count}× · untagged</div></div><div class="tv num">${fmt(r.amount)}</div></div>`).join('')}</div>`:''}
  </div>`;}

/* ---- one tag's transactions (drill-down from the tag list) ---- */
let TAGVIEW='',MERVIEW='';
/* One breadcrumb, because tag -> merchant -> back is a real path: without it, backing out of a
   merchant you reached FROM a tag dumps you at the tag list and you lose your place. */
let FROMTAG='';
function openTag(t){TAGVIEW=t;MERVIEW='';FROMTAG='';TAB='tagdetail';window.scrollTo(0,0);draw();}
function openMerchant(m){FROMTAG=TAGVIEW;MERVIEW=m;TAGVIEW='';TAB='tagdetail';window.scrollTo(0,0);draw();}
function backFromDetail(){
  if(FROMTAG){const t=FROMTAG;openTag(t);return;}   // merchant reached via a tag -> back to that tag
  go('spends');}
function tagDetail(){
  const key=TAGVIEW||MERVIEW,byTag=!!TAGVIEW;
  const rows=rangeFilter().filter(t=>byTag?t.c===key:(t.m||'')===key);
  const tot=rows.filter(t=>t.f!=='i'&&t.f!=='x').reduce((s,t)=>s+t.a,0);
  // merchant roll-up with count + average — merchant identity, not a flat list
  const byMer={},cnt={};rows.forEach(t=>{if(t.f==='i'||t.f==='x')return;const m=t.m||t.desc;byMer[m]=(byMer[m]||0)+t.a;cnt[m]=(cnt[m]||0)+1;});
  const mers=Object.keys(byMer).map(m=>({m,a:byMer[m],n:cnt[m]})).sort((a,b)=>b.a-a.a);
  const maxA=Math.max(...mers.map(m=>m.a),1);
  /* Each merchant row drills into that merchant's own transactions. These rows carry .crow, which is
     styled cursor:pointer, but had no onclick — so the whole "top merchants" list looked clickable
     and did nothing. Same drill-down the category rows already offer. */
  const merRows=mers.slice(0,12).map(m=>`<div class="crow" onclick="openMerchant('${escArg(m.m)}')"><div class="ci">${I(catIcon(key))}</div><div class="cm"><div class="cn">${esc(m.m)}</div><div class="cb"><i style="width:${(m.a/maxA*100).toFixed(0)}%"></i></div></div><div class="cr"><div class="ca num">${fmtH(m.a)}</div><div class="cp">${m.n}× · ~${fmtK(Math.round(m.a/m.n))} avg <span class="chev">›</span></div></div></div>`).join('');
  const txRows=dayGrouped(rows.slice().reverse().slice(0,60));
  return `<div class="view on">
    ${backBtn('backFromDetail()',FROMTAG||'spends')}
    <div class="hero rise"><div class="l">${esc(key)}</div>
      <div class="big num">${fmt(tot)}</div><div class="avg">${rows.length} transactions</div></div>
    ${byTag?`<div class="st"><h2>top merchants</h2></div>
    <div class="list rise">${merRows||'<div class="empty">nothing here</div>'}</div>`:''}
    <div class="st"><h2>transactions</h2></div>${txRows}
  </div>`;}

/* day-grouped ledger under sticky date headers */
function dayGrouped(rows){if(!rows.length)return'<div class="empty">nothing here</div>';
  let out='',day='';
  rows.forEach(t=>{if(t.d!==day){if(day)out+='</div>';day=t.d;out+=`<div class="dayh">${dayLabel(t.d)}</div><div class="list rise">`;}
    out+=txRow(t);});
  return out+'</div>';}
function dayLabel(d){if(!d||!M.max_date)return esc(d);
  const a=new Date(d+'T00:00:00Z'),b=new Date(M.max_date+'T00:00:00Z'),diff=Math.round((b-a)/864e5);
  if(diff===0)return'today';if(diff===1)return'yesterday';
  return a.toLocaleDateString('en-IN',{day:'numeric',month:'short',year:'numeric',timeZone:'UTC'});}
/* `withDate` is for lists with no day header of their own (e.g. home's "recent") */
function txRow(t,withDate){const isIn=t.f==='i';
  // a split row says so in the ledger: otherwise "billed" and "my share" differ by an amount the user
  // cannot locate without opening every transaction
  const split=t.mine!=null?`split · ${fmtK(t.mine)} mine`:null;
  const sub=[withDate?dayLabel(t.d):null,t.c,t.f==='x'?'self':null,split,t.note?'📝':null].filter(Boolean).join(' · ');
  return `<div class="trow" onclick="openTxn('${esc(t.ref)}')"><div class="ti">${esc((t.m||t.c||'?').slice(0,2)).toUpperCase()}</div>
    <div class="tm"><div class="tn">${esc(t.m||t.desc)}</div><div class="td">${esc(sub)}</div></div>
    <div class="tv num ${isIn?'in':''}">${isIn?'+':'−'}${fmtH(t.a).replace('-','')}</div></div>`;}

/* ---- search / ledger view ---- */
function search(){const rows=rangeFilter().slice().reverse().slice(0,600);
  return `<div class="view on"><div class="st"><h2>all transactions</h2></div>
    <input class="search" placeholder="search merchant or tag…" oninput="ft(this)">
    ${rangeRow()}
    <div id="led">${dayGrouped(rows)}</div></div>`;}
function ft(i){const q=i.value.toLowerCase();
  document.querySelectorAll('#led .trow').forEach(r=>{r.style.display=r.textContent.toLowerCase().includes(q)?'':'none';});
  // hide a day header whose rows are all filtered out, so no orphan dates remain
  document.querySelectorAll('#led .list').forEach(l=>{
    const any=[...l.querySelectorAll('.trow')].some(r=>r.style.display!=='none');
    l.style.display=any?'':'none';const h=l.previousElementSibling;
    if(h&&h.classList.contains('dayh'))h.style.display=any?'':'none';});}

/* ---- transaction detail: tag correction + note (the manual-fix path) ---- */
let TXNREF='';
function openTxn(ref){if(!ref)return;TXNREF=ref;TAB='txn';window.scrollTo(0,0);draw();}
function txnDetail(){
  const t=ALL.find(x=>x.ref===TXNREF);
  if(!t)return `<div class="view on"><div class="empty">transaction not found</div></div>`;
  const cur=OVERRIDE[t.ref]||t.c,isIn=t.f==='i';
  // icon + label, the way CRED's tag picker does it: the glyph is what you actually scan for, and the
  // vocab has carried an icon per tag all along without ever showing it
  const chips=(DATA.tag_vocab||[]).map(v=>`<button class="tagchip ${v.tag===cur?'on':''}" onclick="setTag('${escArg(t.ref)}','${escArg(v.tag)}')">${I(v.icon||catIcon(v.tag))}${esc(v.tag)}</button>`).join('');
  /* Centred like a receipt — glyph, payee, amount, tag, "paid from" — instead of a left-aligned stack
     of labelled cards. One transaction is a document, and this is what a document looks like. */
  return `<div class="view on">
    ${backBtn("go('search')",'transactions')}
    <div class="rcpt rise">
      <div class="ravg">${avatar(t.m||t.c||'?')}</div>
      <div class="rnm">${esc(t.m||t.desc)}</div>
      <div class="ramt num">${isIn?'+':''}${fmtH(t.a)}</div>
      <div class="rdate">${esc(dayLabel(t.d))}</div>
      <div class="rtag">${esc(cur)}</div>
      <div class="rtear"></div>
      <div class="rfrom"><span class="l">paid from</span>
        <span class="rbank"><span class="d"></span>${esc(M.account)}</span></div>
      ${t.b!=null?`<div class="rbal"><span class="l">balance after</span>
        <span class="num">${fmtH(t.b)}</span></div>`:''}
      ${t.desc&&t.m&&t.desc!==t.m?`<div class="rnarr">${esc(t.desc)}</div>`:''}
    </div>
    <div class="st"><h2>tag</h2></div>
    <div class="note rise">tagged automatically as <b>${esc(t.c)}</b>. tap another tag if that's wrong — we'll remember it for ${esc(t.m||'this merchant')}.</div>
    <div class="card rise"><div class="tagwrap">${chips}</div>
      <textarea class="notefield" rows="2" placeholder="add a note (why was this payment made?)" oninput="setNote('${escArg(t.ref)}',this.value)">${esc(NOTES[t.ref]||t.note||'')}</textarea></div>
    ${splitEditor(t)}
    <div id="simwrap"></div>
  </div>`;}

/* ---- shared-charge editor ----
   Only offered on money going OUT: splitting a credit you received is meaningless, and offering it
   would invite a nonsense entry. Presets cover the common cases (halves, thirds, quarters) and the
   exact field is there for the dinner that does not divide evenly. */
function splitEditor(t){
  if(t.f==='i'||t.f==='x')return '';
  const cur=SPLITS[t.ref]!==undefined?SPLITS[t.ref]:(t.mine!=null?t.mine:null);
  const isSplit=cur!=null&&cur!==t.a;
  const ways=[2,3,4].map(n=>{
    const share=Math.round(t.a/n);
    return `<button class="schip ${isSplit&&Math.abs(cur-share)<=1?'on':''}"
      onclick="applySplit('${escArg(t.ref)}',${share})" title="your share if ${n} people shared this">1/${n}</button>`;}).join('');
  const state=isSplit
    ? `<div class="srow"><span class="l">your share</span>
         <span class="num sv">${fmtH(cur)}</span></div>
       <div class="srow"><span class="l">recoverable</span>
         <span class="num sr">${fmtH(t.a-cur)}</span></div>`
    : `<div class="shint">all ${fmt(t.a)} counts as yours</div>`;
  return `<div class="st"><h2>shared?</h2></div>
    <div class="card rise">
      <div class="note" style="margin-bottom:12px">split a charge someone else owes you for. the
        billed amount never changes — your card statement still says ${fmt(t.a)} — only what counts as
        <b>your</b> spending does.</div>
      ${state}
      <div class="swrap">${ways}
        <input class="sexact num" type="text" inputmode="decimal" placeholder="exact ₹"
          value="${isSplit?(cur/100).toFixed(2):''}"
          onchange="applySplit('${escArg(t.ref)}',Math.round(parseFloat(this.value||'0')*100))">
        ${isSplit?`<button class="schip clear" onclick="applySplit('${escArg(t.ref)}',null)">clear</button>`:''}
      </div>
      <input class="notefield" style="margin-top:10px" placeholder="with whom? (for your reference)"
        value="${esc(t.with||'')}" onchange="setSplitWith('${escArg(t.ref)}',this.value)">
    </div>`;}

/* Optimistic local state so the screen responds immediately; the server is the source of truth and a
   rejected write is surfaced rather than swallowed. */
let SPLITS={},SPLITWITH={};
function applySplit(ref,mine){
  const t=ALL.find(x=>x.ref===ref);if(!t)return;
  if(mine!=null&&(isNaN(mine)||mine<0||mine>t.a))
    return toast(`your share must be between ₹0 and ${fmt(t.a)}`);
  SPLITS[ref]=mine;
  if(mine==null)delete SPLITS[ref];
  // keep the in-memory row in step, so every total recomputes without a round trip
  t.mine=mine==null?undefined:mine;
  if(mine==null)delete t.mine;
  draw();
  if(!API)return;
  post('/api/split',{content_hash:ref,mine_minor:mine,with_whom:SPLITWITH[ref]||t.with||''})
    .then(r=>{if(r&&r.error)toast(r.error);});}
function setSplitWith(ref,who){
  SPLITWITH[ref]=who;const t=ALL.find(x=>x.ref===ref);if(t)t.with=who;
  if(!API||t.mine==null)return;
  post('/api/split',{content_hash:ref,mine_minor:t.mine,with_whom:who})
    .then(r=>{if(r&&r.error)toast(r.error);});}

/* ---- similar transactions + multi-select bulk retag ---- */
let SIM=null, SIMSEL=new Set();
function loadSimilar(ref){
  const wrap=document.getElementById('simwrap');
  if(!wrap||!API)return;
  fetch('/api/similar?t='+encodeURIComponent(API)+'&ref='+encodeURIComponent(ref))
    .then(r=>r.json()).then(g=>{
      if(!g||!g.count){SIM=null;return;}
      SIM=g;
      // pre-select every match: the common case is "yes, all of these" — but each row can be
      // unticked, so nothing is applied that the user did not confirm
      SIMSEL=new Set(g.sample.map(s=>s.ref));
      renderSimilar();
    }).catch(()=>{});
}
function renderSimilar(){
  const wrap=document.getElementById('simwrap');if(!wrap||!SIM)return;
  const rows=SIM.sample.map(s=>`
    <label class="simrow">
      <input type="checkbox" ${SIMSEL.has(s.ref)?'checked':''} onchange="toggleSim('${esc(s.ref)}')">
      <span class="simmain"><span class="simnm">${esc(s.desc)}</span>
        <span class="simsub">${dayLabel(s.date)} · ${esc(s.tag||'untagged')}</span></span>
      <span class="simamt num">${s.dir==='C'?'+':'−'}${fmt(s.amount).replace('-','')}</span>
    </label>`).join('');
  const conflict=(SIM.current_tags||[]).length>1
    ? `<div class="simwarn">these are tagged inconsistently right now: ${SIM.current_tags.map(esc).join(', ')}</div>` : '';
  wrap.innerHTML=`
    <div class="st"><h2>similar transactions</h2>
      <a onclick="simAll(${SIMSEL.size!==SIM.sample.length})">${SIMSEL.size===SIM.sample.length?'clear all':'select all'}</a></div>
    <div class="note rise">${esc(SIM.reason)}. tick the ones that belong together, pick a tag, and they all update.</div>
    ${conflict}
    <div class="list rise">${rows}</div>
    <div class="simbar">
      <select id="simtag" class="simsel">${(DATA.tag_vocab||[]).map(v=>`<option value="${esc(v.tag)}">${esc(v.tag)}</option>`).join('')}</select>
      <button class="simgo" onclick="applySim()">tag <span id="simn">${SIMSEL.size}</span> selected</button>
    </div>`;
}
function toggleSim(ref){SIMSEL.has(ref)?SIMSEL.delete(ref):SIMSEL.add(ref);
  const n=document.getElementById('simn');if(n)n.textContent=SIMSEL.size;
  const link=document.querySelector('#simwrap .st a');
  if(link)link.textContent=SIMSEL.size===SIM.sample.length?'clear all':'select all';}
function simAll(on){SIMSEL=on?new Set(SIM.sample.map(s=>s.ref)):new Set();renderSimilar();}
function applySim(){
  if(!SIM||!SIMSEL.size)return toast('nothing selected');
  const tag=document.getElementById('simtag').value;
  const refs=[...SIMSEL];
  post('/api/tag-many',{tag,refs}).then(r=>{
    if(r&&r.error)return toast('could not save: '+r.error);
    // reflect it locally so the change is visible without a reload
    refs.forEach(ref=>{const row=ALL.find(x=>x.ref===ref);if(row)row.c=tag;});
    toast(`tagged ${r.tagged||refs.length} transactions as ${tag}`);
    draw();
  });
}

/* Corrections POST to the local server so they survive reload and re-ingest. When the page is
   opened as a static file (no server) the optimistic local update still applies — the UI stays
   usable, it just can't persist. */
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
  // persist merchant-wide when we know the merchant, else pin to this one row
  post('/api/tag',t&&t.m?{tag,merchant:t.m}:{tag,content_hash:ref})
    .then(r=>{if(r&&r.error)toast('could not save tag: '+r.error);});}
function setNote(ref,v){NOTES[ref]=v;const t=ALL.find(x=>x.ref===ref);if(t)t.note=v;
  clearTimeout(setNote._d);                     // debounce: don't POST on every keystroke
  setNote._d=setTimeout(()=>post('/api/note',{content_hash:ref,note:v})
    .then(r=>{if(r&&r.error)toast('could not save note: '+r.error);}),500);}
function toast(msg){let el=document.getElementById('toast');
  if(!el){el=document.createElement('div');el.id='toast';el.className='toast';document.body.appendChild(el);}
  el.textContent=msg;el.classList.add('on');clearTimeout(toast._t);
  // scale the dwell time to the message: a five-paragraph explanation cannot be read in 3.2s
  toast._t=setTimeout(()=>el.classList.remove('on'),Math.min(20000,3200+msg.length*22));}

/* ---- recurring view ---- */
function recurringV(){const R=DATA.recurring||[];
  const live=R.filter(r=>r.active),dead=R.filter(r=>!r.active);
  const row=r=>`<div class="trow"><div class="ti">${esc((r.merchant||'?').slice(0,2)).toUpperCase()}</div>
    <div class="tm"><div class="tn">${esc(r.merchant)}</div>
      <div class="td">seen ${r.months} months · usually the ${ord(r.usual_day)}${r.next_expected?` · next ~${dayLabel(r.next_expected)}`:' · stopped'}</div></div>
    <div class="tv num">${fmt(r.median)}</div></div>`;
  return `<div class="view on">
    <div class="st"><h2>recurring payments</h2></div>
    <div class="note rise">detected from your statements — ${live.length} still active.</div>
    <div class="list rise">${live.map(row).join('')||'<div class="empty">none detected</div>'}</div>
    ${dead.length?`<div class="st"><h2>stopped</h2></div><div class="list rise">${dead.slice(0,8).map(row).join('')}</div>`:''}
  </div>`;}
function ord(n){const s=['th','st','nd','rd'],v=n%100;return n+(s[(v-20)%10]||s[v]||s[0]);}

/* ---- insights view ---- */
function insightsV(){let ins='';DATA.insights.forEach(c=>{const cls=c.severity>=3?'alert':c.severity===0?'positive':'';
  ins+=`<div class="ins ${cls}" style="flex:none"><div class="ic">${I(c.icon)}</div><div class="it">${esc(c.title)}</div><div class="cp">${hl(c.copy)}</div></div>`;});
  return `<div class="view on"><div class="st"><h2>insights for you</h2></div><div style="display:flex;flex-direction:column;gap:12px">${ins}</div></div>`;}

/* ---- nav + routing ---- */
let TAB='home';
const TABS=[['home','home','Home'],['spends','invest','Spends'],['recurring','repeat','Recurring'],['search','srch','Search']];
function nav(){document.getElementById('nav').innerHTML=TABS.map(([k,ic,lbl])=>`<button class="${TAB===k?'on':''}" onclick="go('${k}')">${I(ic)}${lbl}</button>`).join('');}
function countUp(){
  const el=document.getElementById('hero');if(!el)return;
  if(window.matchMedia&&window.matchMedia('(prefers-reduced-motion: reduce)').matches)return;
  const to=+el.dataset.to;if(!to)return;const dur=650,t0=performance.now();
  const ease=x=>1-Math.pow(1-x,3);
  function step(now){const p=Math.min(1,(now-t0)/dur);el.textContent=fmt(Math.round(to*ease(p)));if(p<1)requestAnimationFrame(step);}
  requestAnimationFrame(step);
}
const VIEWS={home:home,spends:spends,insights:insightsV,search:search,
             recurring:recurringV,tagdetail:tagDetail,txn:txnDetail,netting:nettingV};
function draw(){const v=document.getElementById('views');v.innerHTML=(VIEWS[TAB]||home)();
  let i=0;v.querySelectorAll('.rise').forEach(el=>el.style.setProperty('--i',i++));
  v.querySelectorAll('.insrow .ins').forEach((el,j)=>el.style.setProperty('--i',j));
  nav();showFreshness();accSwitch();if(TAB==='home')countUp();
  // the similar-transactions list is fetched, so it renders after the view paints
  if(TAB==='txn'&&TXNREF)loadSimilar(TXNREF);}
function go(t){TAB=t;window.scrollTo(0,0);draw();}
function setR(r){RANGE=r;draw();}
function setCF(v){CF=v;RANGE='C';draw();}
function setCT(v){CT=v;RANGE='C';draw();}
function setSort(s){SORT=s;draw();}
function TT(){const h=document.documentElement;h.dataset.theme=h.dataset.theme==='dark'?'light':'dark';}
draw();
</script>
</body></html>"""
