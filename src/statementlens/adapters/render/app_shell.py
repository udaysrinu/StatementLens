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
<html lang="en" data-theme="dark">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>__LABEL__ · Money</title><link rel="icon" href="data:,">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600&family=Instrument+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
:root{
  --bg:#08080a;--s1:#101013;--s2:#17171b;--ink:#f4f4f0;--ink2:#9a9aa2;--ink3:#5c5c64;
  --line:rgba(255,255,255,.07);--acc:#c6f24e;--up:#8fe08f;--down:#ff8f8f;
  --disp:'Fraunces',Georgia,serif;--body:'Instrument Sans',system-ui,sans-serif;--ease:cubic-bezier(.2,.7,.3,1);
}
[data-theme=light]{--bg:#f1ede4;--s1:#faf8f2;--s2:#efe9dd;--ink:#1a1712;--ink2:#5f584c;--ink3:#9a917f;
  --line:rgba(40,30,15,.1);--acc:#5c8a1f;--up:#3f7d43;--down:#c0503a;}
*{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}
body{background:#050507;color:var(--ink);font-family:var(--body);font-size:15px;line-height:1.5;-webkit-font-smoothing:antialiased;min-height:100vh;display:flex;justify-content:center;padding:0}
[data-theme=light] body{background:#e6ddcd}
.num{font-variant-numeric:tabular-nums;font-feature-settings:"tnum"}
.app{width:100%;max-width:460px;background:var(--bg);min-height:100vh;position:relative;
  background-image:radial-gradient(58% 34% at 50% 0%,rgba(198,242,78,.06),transparent 62%)}
.wrap{padding:20px 20px 108px;display:flex;flex-direction:column;gap:22px}

/* top */
.top{display:flex;justify-content:space-between;align-items:center;padding-top:8px}
.hi{font-size:13px;color:var(--ink2)}.nm{font:600 19px/1.15 var(--disp);margin-top:2px}
.av{width:40px;height:40px;border-radius:50%;background:linear-gradient(150deg,var(--acc),#8fbf3a);display:grid;place-items:center;color:#08080a;font-weight:700;cursor:pointer}
.acct{display:inline-flex;align-items:center;gap:7px;background:var(--s1);border:1px solid var(--line);border-radius:100px;padding:6px 13px;font-size:12.5px;color:var(--ink2);align-self:flex-start}
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
.ins .ic{width:34px;height:34px;border-radius:10px;background:rgba(198,242,78,.13);display:grid;place-items:center;margin-bottom:13px;color:var(--acc)}
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
.seg button.on{background:var(--acc);color:#08080a}
.flow{display:flex;gap:10px;margin-bottom:14px}
.fc{flex:1;background:var(--s2);border-radius:14px;padding:13px 15px}
.fc .fl{font-size:11.5px;color:var(--ink3)}.fc .fv{font:500 19px/1 var(--disp);margin-top:6px}
.fin{color:var(--up)}.fout{color:var(--ink)}
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
.nav{position:fixed;bottom:0;width:100%;max-width:460px;height:70px;background:rgba(8,8,10,.86);backdrop-filter:blur(20px);border-top:1px solid var(--line);display:flex;justify-content:space-around;align-items:center;padding-bottom:6px}
[data-theme=light] .nav{background:rgba(241,237,228,.9)}
.nav button{background:none;border:none;display:flex;flex-direction:column;align-items:center;gap:4px;color:var(--ink3);font-size:10.5px;cursor:pointer;font-family:var(--body)}
.nav button.on{color:var(--acc)}.nav button svg{width:21px;height:21px}
.rise{animation:rise .5s var(--ease) both}
@keyframes rise{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:none}}
@media(prefers-reduced-motion:reduce){.ins,.rise{animation:none}}
.search{width:100%;padding:12px 15px;background:var(--s2);border:1px solid var(--line);border-radius:12px;color:var(--ink);font-size:14px;font-family:var(--body);margin-bottom:12px}
.search:focus{outline:none;border-color:var(--acc)}
.empty{text-align:center;padding:40px;color:var(--ink3)}
.view{display:none}.view.on{display:flex;flex-direction:column;gap:22px}
</style>
</head>
<body>
<div class="app">
 <div class="wrap">
  <div class="top">
    <div><div class="hi" id="greet">welcome back,</div><div class="nm">__LABEL__</div></div>
    <button class="av" onclick="TT()" title="theme">◐</button>
  </div>
  <span class="acct"><span class="d"></span> <span id="acctlbl">account</span></span>
  <div id="views"></div>
 </div>
 <div class="nav" id="nav"></div>
</div>
<script type="application/json" id="data">__DATA__</script>
<script>
const DATA=JSON.parse(document.getElementById('data').textContent),M=DATA.meta,ALL=DATA.txns,CUR=M.currency;
document.getElementById('acctlbl').textContent=M.account+' · '+(M.txn_count)+' transactions';

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

/* ---- compute (integer paise) ---- */
function inRange(t,f,tt){return (!f||t.d>=f)&&(!tt||t.d<=tt);}
function compute(rows){let inn=0,out=0;const catT={},catC={},merT={},merC={},recMon={},recAmt={},moOut={};
  for(const t of rows){if(t.dir==='C')inn+=t.a;else{out+=t.a;catT[t.c]=(catT[t.c]||0)+t.a;catC[t.c]=(catC[t.c]||0)+1;
    if(t.mo)moOut[t.mo]=(moOut[t.mo]||0)+t.a;
    if(t.m){merT[t.m]=(merT[t.m]||0)+t.a;merC[t.m]=(merC[t.m]||0)+1;(recMon[t.m]=recMon[t.m]||new Set()).add(t.mo);(recAmt[t.m]=recAmt[t.m]||[]).push(t.a);}}}
  const cats=Object.keys(catT).map(c=>({c,a:catT[c],n:catC[c]})).sort((x,y)=>y.a-x.a);
  const med=a=>{const s=a.slice().sort((x,y)=>x-y),n=s.length;return n?(n%2?s[(n-1)/2]:(s[n/2-1]+s[n/2])/2):0;};
  const recurring=Object.keys(recMon).filter(m=>recMon[m].size>=3).map(m=>({m,months:recMon[m].size,med:med(recAmt[m]),total:merT[m]})).sort((a,b)=>b.total-a.total).slice(0,6);
  const bal=rows.filter(t=>t.b!=null).slice(-1)[0];
  return {inn,out,cats,recurring,closing:bal?bal.b:null,count:rows.length};}

/* ---- home view ---- */
let RANGE='all';
function monthsBack(n){if(!M.max_date)return'';const d=new Date(M.max_date+'T00:00:00Z');d.setUTCMonth(d.getUTCMonth()-n);return d.toISOString().slice(0,10);}
function rangeFilter(){if(RANGE==='all')return ALL;const map={W:0.25,M:1,Y:12};const f=RANGE==='M'?monthsBack(1):RANGE==='Y'?monthsBack(12):monthsBack(0.25);return ALL.filter(t=>t.d&&t.d>=f);}

function home(){
  const rows=rangeFilter(),R=compute(rows);
  // hero = spent in range
  const lastMo=[...new Set(ALL.filter(t=>t.dir==='D'&&t.mo).map(t=>t.mo))].sort();
  let deltaHtml='';
  if(lastMo.length>=2){const cur=ALL.filter(t=>t.dir==='D'&&t.mo===lastMo[lastMo.length-1]).reduce((s,t)=>s+t.a,0),
    prev=ALL.filter(t=>t.dir==='D'&&t.mo===lastMo[lastMo.length-2]).reduce((s,t)=>s+t.a,0);
    if(prev>0){const pc=Math.round((cur/prev-1)*100),up=pc>0;deltaHtml=`<div class="sub"><span class="${up?'down':'up'}">${up?'↑':'↓'} ${Math.abs(pc)}%</span> vs last month · ${fmt(prev)}</div>`;}}
  // insights
  let ins='';DATA.insights.forEach(c=>{const cls=c.severity>=3?'alert':c.severity===0?'positive':'';
    ins+=`<div class="ins ${cls}"><div class="ic">${I(c.icon)}</div><div class="it">${esc(c.title)}</div><div class="cp">${hl(c.copy)}</div></div>`;});
  // cashflow bar
  const tot=R.inn+R.out||1,inW=Math.round(R.inn/tot*100);
  // categories top5
  let cats='';R.cats.slice(0,5).forEach(c=>{const f=c.a/(R.cats[0].a||1);
    cats+=`<div class="crow"><div class="ci">${I(catIcon(c.c))}</div><div class="cm"><div class="cn">${esc(c.c)}</div><div class="cb"><i style="width:${(f*100).toFixed(0)}%"></i></div></div><div class="cr"><div class="ca num">${fmt(c.a)}</div><div class="cp">${(c.a/R.out*100).toFixed(0)}%</div></div></div>`;});
  // recurring
  let rec='';R.recurring.slice(0,4).forEach(r=>{rec+=`<div class="trow"><div class="ti">${(r.m||'?').slice(0,2).toUpperCase()}</div><div class="tm"><div class="tn">${esc(r.m)}</div><div class="td">seen ${r.months} months</div></div><div class="tv num">${fmt(r.med)}</div></div>`;});
  // recent
  let rec2='';rows.slice().reverse().slice(0,4).forEach(t=>{rec2+=`<div class="trow"><div class="ti">${(t.m||t.c||'?').slice(0,2).toUpperCase()}</div><div class="tm"><div class="tn">${esc(t.m||t.desc)}</div><div class="td">${esc(t.d)} · ${esc(t.c)}</div></div><div class="tv num ${t.dir==='C'?'in':''}">${t.dir==='C'?'+':'−'}${fmt(t.a).replace('-','')}</div></div>`;});

  return `<div class="view on">
    <div class="hero rise"><div class="l">spent ${RANGE==='all'?'· all time':'this '+({W:'week',M:'month',Y:'year'}[RANGE])}</div><div class="big num">${fmt(R.out)}</div>${deltaHtml}</div>
    ${DATA.insights.length?`<div class="st"><h2>for you</h2></div><div class="insrow">${ins}</div>`:''}
    <div class="card rise"><div class="mtop"><div><div class="l">cash flow</div><div class="v num">${fmt(R.inn-R.out,{sign:true})} net</div></div>
      <div class="seg">${['W','M','Y','all'].map(r=>`<button class="${RANGE===r?'on':''}" onclick="setR('${r}')">${r==='all'?'All':r}</button>`).join('')}</div></div>
      <div class="flow"><div class="fc"><div class="fl">money in</div><div class="fv fin num">${fmtK(R.inn)}</div></div><div class="fc"><div class="fl">money out</div><div class="fv fout num">${fmtK(R.out)}</div></div></div>
      <div class="flowbar"><span class="bin" style="width:${inW}%"></span><span class="bout" style="width:${100-inW}%"></span></div></div>
    <div class="st"><h2>where it went</h2><a onclick="go('spends')">see all</a></div>
    <div class="list rise">${cats||'<div class="empty">no spends in range</div>'}</div>
    ${rec?`<div class="st"><h2>recurring</h2></div><div class="list rise">${rec}</div>`:''}
    <div class="st"><h2>recent</h2><a onclick="go('search')">view all</a></div>
    <div class="list rise">${rec2||'<div class="empty">nothing here</div>'}</div>
  </div>`;
}
function hl(s){return esc(s).replace(/(₹[\d,]+(?:\.\d+)?(?:Cr|L|k)?)/g,'<b>$1</b>');}

/* ---- spends view (all categories) ---- */
function spends(){const R=compute(ALL);let rows='';R.cats.forEach(c=>{const f=c.a/(R.cats[0].a||1);
  rows+=`<div class="crow"><div class="ci">${I(catIcon(c.c))}</div><div class="cm"><div class="cn">${esc(c.c)}</div><div class="cb"><i style="width:${(f*100).toFixed(0)}%"></i></div></div><div class="cr"><div class="ca num">${fmt(c.a)}</div><div class="cp">${(c.a/R.out*100).toFixed(0)}% · ${c.n}×</div></div></div>`;});
  return `<div class="view on"><div class="hero rise"><div class="l">total spent · all time</div><div class="big num">${fmt(R.out)}</div></div><div class="st"><h2>all categories</h2></div><div class="list rise">${rows}</div></div>`;}

/* ---- search / ledger view ---- */
function search(){let rows='';ALL.slice().reverse().slice(0,600).forEach(t=>{
  rows+=`<div class="trow"><div class="ti">${(t.m||t.c||'?').slice(0,2).toUpperCase()}</div><div class="tm"><div class="tn">${esc(t.m||t.desc)}</div><div class="td">${esc(t.d)} · ${esc(t.c)}</div></div><div class="tv num ${t.dir==='C'?'in':''}">${t.dir==='C'?'+':'−'}${fmt(t.a).replace('-','')}</div></div>`;});
  return `<div class="view on"><div class="st"><h2>all transactions</h2></div><input class="search" placeholder="search merchant or category…" oninput="ft(this)"><div class="list rise" id="led">${rows}</div></div>`;}
function ft(i){const q=i.value.toLowerCase();document.querySelectorAll('#led .trow').forEach(r=>{r.style.display=r.textContent.toLowerCase().includes(q)?'':'none';});}

/* ---- insights view ---- */
function insightsV(){let ins='';DATA.insights.forEach(c=>{const cls=c.severity>=3?'alert':c.severity===0?'positive':'';
  ins+=`<div class="ins ${cls}" style="flex:none"><div class="ic">${I(c.icon)}</div><div class="it">${esc(c.title)}</div><div class="cp">${hl(c.copy)}</div></div>`;});
  return `<div class="view on"><div class="st"><h2>insights for you</h2></div><div style="display:flex;flex-direction:column;gap:12px">${ins}</div></div>`;}

/* ---- nav + routing ---- */
let TAB='home';
const TABS=[['home','home','Home'],['spends','invest','Spends'],['insights','trend','Insights'],['search','srch','Search']];
function nav(){document.getElementById('nav').innerHTML=TABS.map(([k,ic,lbl])=>`<button class="${TAB===k?'on':''}" onclick="go('${k}')">${I(ic)}${lbl}</button>`).join('');}
function draw(){const v=document.getElementById('views');v.innerHTML={home:home,spends:spends,insights:insightsV,search:search}[TAB]();nav();}
function go(t){TAB=t;window.scrollTo(0,0);draw();}
function setR(r){RANGE=r;draw();}
function TT(){const h=document.documentElement;h.dataset.theme=h.dataset.theme==='dark'?'light':'dark';}
draw();
</script>
</body></html>"""
