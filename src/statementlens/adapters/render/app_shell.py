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
.app{width:100%;max-width:460px;background:var(--bg);min-height:100vh;position:relative;
  background-image:radial-gradient(58% 34% at 50% 0%,rgba(var(--glow),.07),transparent 62%)}
.wrap{padding:20px 20px 108px;display:flex;flex-direction:column;gap:22px}

/* top */
.top{display:flex;justify-content:space-between;align-items:center;padding-top:8px}
.hi{font-size:13px;color:var(--ink2)}.nm{font:600 19px/1.15 var(--disp);margin-top:2px}
.av{width:40px;height:40px;border-radius:50%;background:linear-gradient(150deg,var(--acc),var(--acc2));display:grid;place-items:center;color:var(--onacc);font-weight:700;cursor:pointer}
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
.fc{flex:1;min-width:0;background:var(--s2);border-radius:14px;padding:12px 12px}
.fc .fl{font-size:10.5px;color:var(--ink3);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.fc .fv{font:500 17px/1 var(--disp);margin-top:6px}
.fin{color:var(--up)}.fout{color:var(--ink)}.finv{color:var(--ink2)}

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

/* monthly bars + avg reference line */
.chart{position:relative;display:flex;align-items:flex-end;gap:6px;height:132px;padding-top:6px}
.bcol{flex:1;min-width:0;display:flex;flex-direction:column;align-items:center;gap:5px;height:100%}
.bwrap{flex:1;width:100%;display:flex;align-items:flex-end}
.bwrap i{display:block;width:100%;border-radius:5px 5px 2px 2px;background:var(--s2)}
.bwrap i.on{background:var(--acc)}
.blab{font-size:9.5px;color:var(--ink3);letter-spacing:.04em}
.bval{font-size:9px;color:var(--ink3)}
.avgline{position:absolute;left:0;right:0;height:0;border-top:1px dashed var(--up);opacity:.55;z-index:1}
.avgt{font-size:11px;color:var(--ink3);font-family:var(--body);font-weight:400}

/* tag chips (correction UI) */
.tagwrap{display:flex;flex-wrap:wrap;gap:8px}
.tagchip{background:transparent;border:1px solid var(--line);color:var(--ink2);border-radius:8px;
  padding:9px 12px;font:600 11px var(--body);letter-spacing:.04em;text-transform:uppercase;cursor:pointer}
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
  padding:11px 16px;font-size:13px;opacity:0;pointer-events:none;transition:all .25s var(--ease)}
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
.crow .cr{text-align:right;flex:none}.crow .ca{font:500 15px/1 var(--disp)}.crow .cp{font-size:11.5px;color:var(--ink3);margin-top:3px}

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
.back{color:var(--acc);cursor:pointer;text-decoration:none}
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
  el.innerHTML=parts.join(' · ')+(API?' <button onclick="doRefresh(this)">refresh</button>':'');}
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
function fmtK(p){let r=Math.abs(p)/100,sym=CUR==='INR'?'₹':'',g=p<0?'-':'';
  if(r>=1e7)return g+sym+(r/1e7).toFixed(r>=1e8?0:1)+'Cr';if(r>=1e5)return g+sym+(r/1e5).toFixed(r>=1e6?0:1)+'L';
  if(r>=1e3)return g+sym+(r/1e3).toFixed(0)+'k';return g+sym+Math.round(r);}
const esc=s=>String(s==null?'':s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
function I(n){const S=p=>`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">${p}</svg>`;const m={
  copy:'<rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10"/>',
  receipt:'<path d="M5 3v18l2-1 2 1 2-1 2 1 2-1 2 1V3l-2 1-2-1-2 1-2-1-2 1z"/><path d="M9 8h6M9 12h6"/>',
  trend:'<path d="M3 17l6-6 4 4 8-8M21 7v5h-5"/>',repeat:'<path d="M17 2l4 4-4 4M3 11V9a4 4 0 0 1 4-4h14M7 22l-4-4 4-4M21 13v2a4 4 0 0 1-4 4H3"/>',
  crown:'<path d="M3 7l4 4 5-7 5 7 4-4v11H3z"/>',gift:'<rect x="3" y="8" width="18" height="4"/><path d="M12 8v13M5 12v9h14v-9M12 8a3 3 0 1 0-3-3c0 2 3 3 3 3zM12 8a3 3 0 1 1 3-3c0 2-3 3-3 3z"/>',
  check:'<circle cx="12" cy="12" r="9"/><path d="M8 12l3 3 5-6"/>',
  food:'<path d="M3 2v7a3 3 0 0 0 6 0V2M6 2v20M21 15V2a5 5 0 0 0-3 5v6h3v7"/>',grocery:'<path d="M3 3h2l2 12h11l2-8H6"/><circle cx="9" cy="20" r="1"/><circle cx="17" cy="20" r="1"/>',
  home:'<path d="M3 10 12 3l9 7v10a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z"/>',bill:'<path d="M13 2 3 14h7l-1 8 10-12h-7z"/>',
  invest:'<path d="M3 17l6-6 4 4 8-8M21 7v5h-5"/>',card:'<rect x="2" y="5" width="20" height="14" rx="2"/><path d="M2 10h20"/>',
  cash:'<rect x="3" y="6" width="18" height="12" rx="2"/><circle cx="12" cy="12" r="2.5"/>',transfer:'<path d="M7 17V7m0 0L3 11m4-4 4 4M17 7v10m0 0 4-4m-4 4-4-4"/>',
  dot:'<circle cx="12" cy="12" r="9"/>',srch:'<circle cx="11" cy="11" r="7"/><path d="M21 21l-4-4"/>',list:'<path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/>'};
  return S(m[n]||m.dot);}
function catIcon(c){c=(c||'').toLowerCase();if(/food|dining/.test(c))return'food';if(/grocer/.test(c))return'grocery';
  if(/rent|home/.test(c))return'home';if(/bill|utilit/.test(c))return'bill';if(/invest/.test(c))return'invest';
  if(/card/.test(c))return'card';if(/cash|atm/.test(c))return'cash';if(/transfer|people/.test(c))return'transfer';return'dot';}

/* ---- compute (integer paise) ----
   Three-way flow, mirroring the server: self-transfers ('x') are excluded from BOTH sides, and
   investments ('v') are kept out of `out` so "spent" never counts money you still own. */
function inRange(t,f,tt){return (!f||t.d>=f)&&(!tt||t.d<=tt);}
function compute(rows){let inn=0,out=0,inv=0,slf=0,slfN=0;
  const catT={},catC={},merT={},merC={},recMon={},recAmt={},moOut={},merName={};
  for(const t of rows){
    if(t.f==='x'){slf+=t.a;slfN++;continue;}
    if(t.f==='i'){inn+=t.a;continue;}
    if(t.f==='v')inv+=t.a;
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
  return {inn,out,inv,slf,slfN,cats,catTotal,recurring,closing:bal?bal.b:null,count:rows.length,
          moOut,months:nMo,avgOut:Math.round(out/nMo),avgIn:Math.round(inn/nMo)};}

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
function rangeFilter(){
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
  return `<div class="pwrap"><div class="prow">${chips}${cycle}</div>${custom}</div>${dates}`;}

function home(){
  const rows=rangeFilter(),R=compute(rows);
  const deltaHtml=heroDelta(R);
  // insights
  let ins='';DATA.insights.forEach(c=>{const cls=c.severity>=3?'alert':c.severity===0?'positive':'';
    ins+=`<div class="ins ${cls}"><div class="ic">${I(c.icon)}</div><div class="it">${esc(c.title)}</div><div class="cp">${hl(c.copy)}</div></div>`;});
  // cashflow bar
  const tot=R.inn+R.out||1,inW=Math.round(R.inn/tot*100);
  // categories top5
  let cats='';R.cats.slice(0,5).forEach(c=>{const f=c.a/(R.cats[0].a||1);
    cats+=`<div class="crow" onclick="openTag('${esc(c.c).replace(/'/g,"")}')"><div class="ci">${I(catIcon(c.c))}</div><div class="cm"><div class="cn">${esc(c.c)}</div><div class="cb"><i style="width:${(f*100).toFixed(0)}%"></i></div></div><div class="cr"><div class="ca num">${fmt(c.a)}</div><div class="cp">${(c.a/(R.catTotal||1)*100).toFixed(0)}%</div></div></div>`;});
  // recurring
  let rec='';R.recurring.slice(0,4).forEach(r=>{rec+=`<div class="trow"><div class="ti">${(r.m||'?').slice(0,2).toUpperCase()}</div><div class="tm"><div class="tn">${esc(r.m)}</div><div class="td">seen ${r.months} months</div></div><div class="tv num">${fmt(r.med)}</div></div>`;});
  // recent
  let rec2='';rows.slice().reverse().slice(0,4).forEach(t=>{rec2+=txRow(t,true);});

  // avg-per-month sub-line: the comparative CRED puts under every total
  const avgLine=R.months>1?`<div class="avg num">avg per month ${fmtK(R.avgOut)}</div>`:'';
  // self-transfer disclosure — never silently drop money from the totals
  const slfNote=R.slfN?`<div class="note rise">self-transfers are excluded · ${fmtK(R.slf)} across ${R.slfN} transactions</div>`:'';

  return `<div class="view on">
    <div class="hero rise"><div class="l">${M.is_card?'charged':'spent'} ${rangeLabel()}</div><div class="big num" id="hero" data-to="${R.out}">${fmt(R.out)}</div>${deltaHtml}${avgLine}</div>
    ${rangeRow()}
    ${slfNote}
    ${DATA.insights.length?`<div class="st"><h2>for you</h2></div><div class="insrow">${ins}</div>`:''}
    ${M.is_card?cardFlowCard():bankFlowCard(R,inW)}
    ${monthChart()}
    <div class="st"><h2>where it went</h2><a onclick="go('spends')">see all</a></div>
    <div class="list rise">${cats||'<div class="empty">no spends in range</div>'}</div>
    ${rec?`<div class="st"><h2>recurring</h2><a onclick="go('recurring')">see all</a></div><div class="list rise">${rec}</div>`:''}
    <div class="st"><h2>recent</h2><a onclick="go('search')">view all</a></div>
    <div class="list rise">${rec2||'<div class="empty">nothing here</div>'}</div>
  </div>`;
}

/* ---- flow cards ----
   A bank account and a credit card need different frames. On a bank account "net" is what stayed. On
   a card the spending IS the balance owed, so a net figure is computable but meaningless — the honest
   summary is charges, what you paid off, and what came back (refunds + rewards). */
function bankFlowCard(R,inW){
  return `<div class="card rise"><div class="mtop"><div><div class="l">cash flow</div>
      <div class="v num">${fmt(R.inn-R.out-R.inv,{sign:true})} net</div></div></div>
    <div class="flow"><div class="fc"><div class="fl">incoming</div><div class="fv fin num">${fmtK(R.inn)}</div></div>
      <div class="fc"><div class="fl">investments</div><div class="fv finv num">${fmtK(R.inv)}</div></div>
      <div class="fc"><div class="fl">spends</div><div class="fv fout num">${fmtK(R.out)}</div></div></div>
    <div class="flowbar"><span class="bin" style="width:${inW}%"></span><span class="bout" style="width:${100-inW}%"></span></div></div>`;}

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
function spendBetween(from,to){
  return ALL.filter(t=>t.d&&t.f==='s'&&t.d>=from&&t.d<=to).reduce((s,t)=>s+t.a,0);}
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
  const prev=spendBetween(prevFrom,prevTo);
  if(prev<=0)return '';
  const pc=Math.round((R.out/prev-1)*100), up=pc>0;
  const label=days<=8?'week':days<=32?'month':days<=95?'quarter':days<=370?'year':`${days} days`;
  return `<div class="sub"><span class="${up?'down':'up'}">${up?'↑':'↓'} ${Math.abs(pc)}%</span>`
       + ` vs previous ${label} · ${fmt(prev)}</div>`;}

/* ---- monthly bars with an AVG reference line (CRED's "past trends") ---- */
function monthChart(){const S=DATA.monthly||[];if(S.length<2)return'';
  const peak=Math.max(...S.map(m=>m.amount))||1,avg=S[0].avg||0,avgPct=Math.min(100,avg/peak*100);
  const bars=S.map(m=>{const h=Math.max(2,m.amount/peak*100),on=m.month===S[S.length-1].month;
    return `<div class="bcol"><div class="bwrap"><i class="${on?'on':''}" style="height:${h}%" title="${esc(m.month)} · ${fmt(m.amount)}"></i></div>
      <div class="blab">${esc(m.month.slice(5))}</div><div class="bval num">${fmtK(m.amount)}</div></div>`;}).join('');
  // say when the chart is a window over a longer history — an unlabelled 12-month chart next to an
  // all-time hero number reads as "this is everything", and its average as an all-time average
  const hidden=S[0].months_hidden||0;
  const scope=hidden?`last ${S.length} months`:'all time';
  return `<div class="card rise"><div class="mtop"><div><div class="l">past trends · ${scope}</div>
      <div class="v num">${fmtK(avg)} <span class="avgt">avg / month</span></div></div></div>
    <div class="chart"><span class="avgline" style="bottom:${avgPct}%"></span>${bars}</div>
    ${hidden?`<div class="cardfee">${hidden} earlier month${hidden!==1?'s':''} not shown.</div>`:''}</div>`;}
function hl(s){return esc(s).replace(/(₹[\d,]+(?:\.\d+)?(?:Cr|L|k)?)/g,'<b>$1</b>');}

/* ---- spends view: tag-wise grouping, sortable ---- */
function spends(){const rows0=rangeFilter(),R=compute(rows0);
  let cats=R.cats.slice();
  if(SORT==='low')cats.reverse();
  else if(SORT==='count')cats.sort((a,b)=>b.n-a.n);
  const maxA=Math.max(...cats.map(c=>c.a),1);
  let rows='';cats.forEach(c=>{
    rows+=`<div class="crow" onclick="openTag('${esc(c.c).replace(/'/g,"")}')"><div class="ci">${I(catIcon(c.c))}</div><div class="cm"><div class="cn">${esc(c.c)}</div><div class="cb"><i style="width:${(c.a/maxA*100).toFixed(0)}%"></i></div></div><div class="cr"><div class="ca num">${fmt(c.a)}</div><div class="cp">${(c.a/(R.catTotal||1)*100).toFixed(1)}% · ${c.n}×</div></div></div>`;});
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
      <div class="list rise">${DATA.review_queue.slice(0,6).map(r=>`<div class="trow" onclick="openMerchant('${esc(r.merchant).replace(/'/g,"")}')"><div class="ti">${esc((r.merchant||'?').slice(0,2)).toUpperCase()}</div><div class="tm"><div class="tn">${esc(r.merchant)}</div><div class="td">${r.count}× · untagged</div></div><div class="tv num">${fmt(r.amount)}</div></div>`).join('')}</div>`:''}
  </div>`;}

/* ---- one tag's transactions (drill-down from the tag list) ---- */
let TAGVIEW='',MERVIEW='';
function openTag(t){TAGVIEW=t;MERVIEW='';TAB='tagdetail';window.scrollTo(0,0);draw();}
function openMerchant(m){MERVIEW=m;TAGVIEW='';TAB='tagdetail';window.scrollTo(0,0);draw();}
function tagDetail(){
  const key=TAGVIEW||MERVIEW,byTag=!!TAGVIEW;
  const rows=rangeFilter().filter(t=>byTag?t.c===key:(t.m||'')===key);
  const tot=rows.filter(t=>t.f!=='i'&&t.f!=='x').reduce((s,t)=>s+t.a,0);
  // merchant roll-up with count + average — merchant identity, not a flat list
  const byMer={},cnt={};rows.forEach(t=>{if(t.f==='i'||t.f==='x')return;const m=t.m||t.desc;byMer[m]=(byMer[m]||0)+t.a;cnt[m]=(cnt[m]||0)+1;});
  const mers=Object.keys(byMer).map(m=>({m,a:byMer[m],n:cnt[m]})).sort((a,b)=>b.a-a.a);
  const maxA=Math.max(...mers.map(m=>m.a),1);
  const merRows=mers.slice(0,12).map(m=>`<div class="crow"><div class="ci">${I(catIcon(key))}</div><div class="cm"><div class="cn">${esc(m.m)}</div><div class="cb"><i style="width:${(m.a/maxA*100).toFixed(0)}%"></i></div></div><div class="cr"><div class="ca num">${fmt(m.a)}</div><div class="cp">${m.n}× · ~${fmtK(Math.round(m.a/m.n))} avg</div></div></div>`).join('');
  const txRows=dayGrouped(rows.slice().reverse().slice(0,60));
  return `<div class="view on">
    <div class="hero rise"><div class="l"><a class="back" onclick="go('spends')">‹ back</a> · ${esc(key)}</div>
      <div class="big num">${fmt(tot)}</div><div class="avg">${rows.length} transactions</div></div>
    <div class="st"><h2>top ${byTag?'merchants':'activity'}</h2></div>
    <div class="list rise">${merRows||'<div class="empty">nothing here</div>'}</div>
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
  const sub=[withDate?dayLabel(t.d):null,t.c,t.f==='x'?'self':null,t.note?'📝':null].filter(Boolean).join(' · ');
  return `<div class="trow" onclick="openTxn('${esc(t.ref)}')"><div class="ti">${esc((t.m||t.c||'?').slice(0,2)).toUpperCase()}</div>
    <div class="tm"><div class="tn">${esc(t.m||t.desc)}</div><div class="td">${esc(sub)}</div></div>
    <div class="tv num ${isIn?'in':''}">${isIn?'+':'−'}${fmt(t.a).replace('-','')}</div></div>`;}

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
  const chips=(DATA.tag_vocab||[]).map(v=>`<button class="tagchip ${v.tag===cur?'on':''}" onclick="setTag('${esc(t.ref)}','${esc(v.tag)}')">${esc(v.tag)}</button>`).join('');
  return `<div class="view on">
    <div class="hero rise"><div class="l"><a class="back" onclick="go('search')">‹ back</a></div>
      <div class="big num">${isIn?'+':''}${fmt(t.a)}</div>
      <div class="avg">${isIn?'credit':'debit'} · ${dayLabel(t.d)}</div></div>
    <div class="card rise"><div class="l">merchant</div><div class="dv">${esc(t.m||'—')}</div>
      <div class="dsub">${esc(t.desc)}</div></div>
    ${t.b!=null?`<div class="card rise"><div class="mtop"><div class="l">balance after</div><div class="v num">${fmt(t.b)}</div></div></div>`:''}
    <div class="st"><h2>tag</h2></div>
    <div class="note rise">tagged automatically as <b>${esc(t.c)}</b>. tap another tag if that's wrong — we'll remember it for ${esc(t.m||'this merchant')}.</div>
    <div class="card rise"><div class="tagwrap">${chips}</div>
      <textarea class="notefield" rows="2" placeholder="add a note (why was this payment made?)" oninput="setNote('${esc(t.ref)}',this.value)">${esc(NOTES[t.ref]||t.note||'')}</textarea></div>
    <div id="simwrap"></div>
  </div>`;}

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
  toast._t=setTimeout(()=>el.classList.remove('on'),3200);}

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
             recurring:recurringV,tagdetail:tagDetail,txn:txnDetail};
function draw(){const v=document.getElementById('views');v.innerHTML=(VIEWS[TAB]||home)();
  let i=0;v.querySelectorAll('.rise').forEach(el=>el.style.setProperty('--i',i++));
  v.querySelectorAll('.insrow .ins').forEach((el,j)=>el.style.setProperty('--i',j));
  nav();showFreshness();if(TAB==='home')countUp();
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
