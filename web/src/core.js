// core.js — the dashboard's logic and state, moved VERBATIM from the plain-CSS app_shell.py script.
// Only three things changed: draw() now tells React to re-render (it no longer builds HTML), toast() is
// state React renders, and the back-stack wrappers are explicit instead of patching window[fn].
// Money stays integer paise; compute() is the same function the consistency suite checks against.
/* eslint-disable */
let __V = 0; const __subs = new Set();
export function subscribe(f) { __subs.add(f); return () => __subs.delete(f); }
export function version() { return __V; }
function draw() { __V++; __subs.forEach((f) => f()); }
let TOAST = '';
function toast(msg) { TOAST = msg; draw(); clearTimeout(toast._t);
  toast._t = setTimeout(() => { TOAST = ''; draw(); }, Math.min(20000, 3200 + String(msg).length * 22)); }

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

/* ---- month picker: the statement app's real unit is the MONTH ---- */
let PICKYEAR=null, PICKANCHOR=null;

const MONTHNAMES=MON;

function monthsWithData(){
  if(!monthsWithData._c)monthsWithData._c=new Set(ALL.map(t=>t.mo).filter(Boolean));
  return monthsWithData._c;}

function pickYears(){
  const ys=[...new Set([...monthsWithData()].map(m=>m.slice(0,4)))].sort();
  return ys.length?ys:[String(new Date().getUTCFullYear())];}

let EXACT=false;

function toggleExact(){EXACT=!EXACT;draw();}

function setPickYear(y){PICKYEAR=y;draw();}

function pickMonth(mo){
  if(!PICKANCHOR){PICKANCHOR=mo;CF=monthStart(mo);CT=monthEnd(mo);RANGE='C';draw();return;}
  const [a,b]=[PICKANCHOR,mo].sort();
  CF=monthStart(a);CT=monthEnd(b);PICKANCHOR=null;RANGE='C';draw();}

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

/* ---- account switching: each account is its own dataset, so switching is a page load ---- */
function accHref(acc,view){return `?t=${encodeURIComponent(API||'')}&a=${encodeURIComponent(acc)}${view?'&v='+view:''}`;}

function stashScroll(){try{sessionStorage.setItem('sl-scroll',window.scrollY)}catch(_){}}

function openAccount(acc){if(acc===M.account){openDetail('account');return;}
  stashScroll();location.href=accHref(acc,'account');}

function restoreScroll(){
  let y=null;
  try{y=sessionStorage.getItem('sl-scroll');sessionStorage.removeItem('sl-scroll');}catch(_){}
  if(y==null)return;
  const target=Math.min(+y, document.body.scrollHeight-window.innerHeight);
  if(target>0)window.scrollTo(0,target);}

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

/* one account: CRED's account page — sunburst header, balance, what it earned, how it moved */
let BALMODE='close';

function toggleBalMode(){BALMODE=BALMODE==='close'?'peak':'close';draw();}

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

/* ---- cash flow ---- */
let CYCLENOTE=true;
try{CYCLENOTE=localStorage.getItem('sl-cyclenote')!=='seen';}catch(_){}

function dismissCycle(){CYCLENOTE=false;try{localStorage.setItem('sl-cyclenote','seen');}catch(_){}draw();}

function sixMonthTotal(code){const from=monthsBack(6);
  return netFilter(ALL.filter(t=>t.d&&t.d>=from)).filter(t=>t.f===code).reduce((s,t)=>s+sa(t),0);}

/* ---- one tag, merchant or person ---- */
let TAGVIEW='',MERVIEW='',PERVIEW='';

/* one breadcrumb: tag -> merchant -> back is a real path, and backing out must land on the tag */
let FROMTAG='';

function openTag(t){TAGVIEW=t;MERVIEW='';PERVIEW='';FROMTAG='';openDetail('tagdetail');}

function openMerchant(m){FROMTAG=TAGVIEW;MERVIEW=m;PERVIEW='';TAGVIEW='';openDetail('tagdetail');}

/* a person can span several merchant spellings, so filter by counterparty, not by one name */
function openPerson(cp,name){FROMTAG=TAGVIEW;MERVIEW=name;PERVIEW=cp;TAGVIEW='';openDetail('tagdetail');}

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

function confirmTag(){if(!TAGPICK)return;const t=ALL.find(x=>x.ref===TXNREF);if(!t)return;setTag(t.ref,TAGPICK);TAGPICK=null;
  toast(`tagged ${t.m||'this'} as ${OVERRIDE[t.ref]||t.c}`);}

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

/* ---- what each card payment paid for ---- */
let BILLOPEN=null;

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

function setR(r){RANGE=r;draw();}

function setCF(v){CF=v;RANGE='C';draw();}

function setCT(v){CT=v;RANGE='C';draw();}

function setSort(s){SORT=s;draw();}

/* the donut ramp and avatar tints compute in JS, so a CSS swap alone would leave them on the old theme */
function TT(){const h=document.documentElement;h.dataset.theme=h.dataset.theme==='dark'?'light':'dark';
  try{localStorage.setItem('sl-theme',h.dataset.theme);}catch(_){}draw();}
try{const th=localStorage.getItem('sl-theme');if(th)document.documentElement.dataset.theme=th;}catch(_){}

/* The four tabs are sections of ONE scrolling page (the owner's call): the tab bar follows the section
   in view without the go() side effects (closing details, scrolling to the top). */
function setTabInView(t) { if (TAB !== t) { TAB = t; draw(); } }

/* ---- helpers for the NeoPOP screens: the same actions the plain-CSS page did inline or through the
   DOM, now as functions, because a React component cannot assign this module's state ---- */
function viewMonthTxns(mo) { CF = monthStart(mo); CT = monthEnd(mo); RANGE = 'C'; openDetail('search'); }
function viewAllHigh() { SORT = 'high'; openDetail('search'); }
/* heroDelta() as data: the same comparison (same span of days just before the range, same flow) */
function heroDeltaData(R) {
  const w = currentWindow(); if (!w) return null;
  const days = Math.round((new Date(w.to) - new Date(w.from)) / 864e5) + 1;
  const prevTo = shiftDays(w.from, -1), prevFrom = shiftDays(prevTo, -(days - 1));
  if (prevFrom < w.first) return null;
  const prev = flowBetween(prevFrom, prevTo, FLOW_CODE[FLOW] || 's'); if (prev <= 0) return null;
  const pc = Math.round((heroValue(R).amount / prev - 1) * 100), up = pc > 0;
  const label = days <= 8 ? 'week' : days <= 32 ? 'month' : days <= 95 ? 'quarter' : days <= 370 ? 'year' : `${days} days`;
  return { pc: Math.abs(pc), up, good: FLOW === 'out' ? !up : up, label, prev };
}
/* similar transactions for bulk retagging (server-side grouping), and the bulk retag itself */
function similarFor(ref) {
  if (!API) return Promise.resolve(null);
  return fetch('/api/similar?t=' + encodeURIComponent(API) + '&ref=' + encodeURIComponent(ref))
    .then((r) => r.json()).then((g) => (g && g.count ? g : null)).catch(() => null);
}
function tagMany(tag, refs) {
  if (!refs.length) { toast('nothing selected'); return Promise.resolve(false); }
  return post('/api/tag-many', { tag, refs }).then((r) => {
    if (r && r.error) { toast('could not save: ' + r.error); return false; }
    refs.forEach((ref) => { const row = ALL.find((x) => x.ref === ref); if (row) row.c = tag; });
    toast(`tagged ${r.tagged || refs.length} transactions as ${tag}`); draw(); return true;
  });
}

/* openTag/openMerchant/openPerson/openTxn mutate the view keys BEFORE calling openDetail, so take the
   snapshot of the screen being left first, or "back" would restore the screen you are already on */
const __wrapBack = (f) => function () { prevSnap = DET ? snap() : null; return f.apply(this, arguments); };
openTag = __wrapBack(openTag); openMerchant = __wrapBack(openMerchant); openPerson = __wrapBack(openPerson); openTxn = __wrapBack(openTxn);

/* ?v=account opens a screen directly — used when the accounts list switches to another account */
(()=>{const v=new URLSearchParams(location.search).get('v');
  if(v==='account'){TAB='accounts';DET='account';}else if(v==='txns'){TAB='txns';}
  /* ?v=txn[&ref=..] opens one transaction (default: the newest spend) */
  else if(v==='txn'){TAB='txns';DET='txn';TXNREF=new URLSearchParams(location.search).get('ref')||((ALL.filter(x=>x.f==='s').slice(-1)[0])||{}).ref;}
  else if(MAIN.some(m=>m[0]===v)){TAB=v;}
  /* drilled-in screens, so a view can be bookmarked or captured: ?v=breakdown&flow=in, ?v=tag&tag=rent,
     ?v=search, ?v=netting */
  else if(v==='breakdown'){const q=new URLSearchParams(location.search);FLOW=q.get('flow')||'out';DET='breakdown';}
  else if(v==='tag'){TAGVIEW=new URLSearchParams(location.search).get('tag')||'';DET=TAGVIEW?'tagdetail':'';}
  else if(v==='search'||v==='netting'){DET=v;if(new URLSearchParams(location.search).get('range'))RANGE=new URLSearchParams(location.search).get('range');}
  const dn=new URLSearchParams(location.search).get('density');if(dn)document.documentElement.dataset.density=dn;})();
draw();
restoreScroll();

export {
  viewMonthTxns,
  viewAllHigh,
  heroDeltaData,
  similarFor,
  tagMany,
  setTabInView,
  ALL,
  API,
  BALMODE,
  BANKHUE,
  BILLOPEN,
  CF,
  CT,
  CUR,
  CYCLENOTE,
  DATA,
  DET,
  DSTACK,
  EXACT,
  FLOW,
  FLOWORDER,
  FLOWS,
  FLOW_CODE,
  FROMTAG,
  HUE,
  HUE_TO,
  HUSH,
  I,
  IC,
  M,
  MAIN,
  MERVIEW,
  MOKEY,
  MON,
  MONTHNAMES,
  NET,
  NOTES,
  OVERRIDE,
  PERIODOPEN,
  PERVIEW,
  PICKANCHOR,
  PICKYEAR,
  PRESETS,
  RANGE,
  RECDIR,
  RECI,
  SHARE,
  SIM,
  SIMSEL,
  SORT,
  SPLITS,
  SPLITWITH,
  TAB,
  TAGICON,
  TAGPICK,
  TAGQ,
  TAGVIEW,
  TOAST,
  TREND,
  TT,
  TXNREF,
  WIDE,
  accHref,
  applySplit,
  backFromDetail,
  bankHue,
  bankKey,
  bankMono,
  byMonth,
  catIcon,
  compute,
  confirmTag,
  countable,
  currentWindow,
  dayLabel,
  dismissCycle,
  draw,
  flowBetween,
  fmt,
  fmtH,
  fmtK,
  ft,
  go,
  heroDelta,
  heroValue,
  inRange,
  incomingRecurring,
  isDark,
  monthEnd,
  monthStart,
  monthsBack,
  monthsWithData,
  netFilter,
  openAccount,
  openDetail,
  openMerchant,
  openMonth,
  openPerson,
  openTag,
  openTxn,
  ord,
  periodRows,
  periodText,
  pickMonth,
  pickTag,
  pickYears,
  post,
  presetFrom,
  prevSnap,
  rangeFilter,
  rangeLabel,
  recStep,
  restoreScroll,
  rowCat,
  sa,
  salaryCycle,
  setCF,
  setCT,
  setFlow,
  setNet,
  setNote,
  setPickYear,
  setR,
  setRecDir,
  setShare,
  setSort,
  setSplitWith,
  setTag,
  shareRows,
  shiftDays,
  shortDate,
  sixMonthTotal,
  snap,
  splitInfo,
  stashScroll,
  tabLabel,
  tint,
  toast,
  toggleBalMode,
  toggleBill,
  toggleExact,
  toggleHush,
  togglePeriod,
  toggleTrend,
  totalBalance,
};
