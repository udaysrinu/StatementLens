// The frame. The four tabs are SECTIONS of one scrolling page (the owner's call): tapping a tab scrolls
// to its section, and the pinned tab bar lights the section in view. Drilling into something (a
// breakdown, a transaction) still opens its own screen, and back returns to the same scroll position.
// Sections not yet rebuilt in NeoPOP say so and link to the same screen at /legacy.
import React, { useEffect, useLayoutEffect, useRef } from 'react';
import * as C from './core.js';
import { Icon, Money, Back } from './ui.jsx';
import { CashFlow } from './screens/CashFlow.jsx';
import { Accounts, AccountDetail } from './screens/Accounts.jsx';
import { Transactions, TxnDetail } from './screens/Transactions.jsx';
import { Recurring } from './screens/Recurring.jsx';
import { Breakdown } from './screens/Breakdown.jsx';
import { TagDetail, Search, Netting, Bills } from './screens/Ledger.jsx';

const SECTIONS = { accounts: Accounts, txns: Transactions, recurring: Recurring, cashflow: CashFlow };
const DETAILS = { txn: TxnDetail, account: AccountDetail, breakdown: Breakdown, tagdetail: TagDetail,
  search: Search, netting: Netting, bills: Bills };
const NAMES = { accounts: 'accounts', txns: 'transactions', recurring: 'recurring payments', cashflow: 'cash flow',
  breakdown: 'breakdown', tagdetail: 'category', txn: 'transaction', search: 'search', netting: 'netting',
  bills: 'card bills', account: 'account' };
const ORDER = C.MAIN.map((m) => m[0]);            // accounts, txns, recurring, cashflow
const secId = (k) => `sec-${k}`;

/* the classes the dock offers: only what the store actually tracks (MF / stocks arrive with the CAS reader) */
const ASSETS = [['all', 'apps', 'all'], ['bank', 'bank', 'bank'], ['fd', 'shield', 'fd'], ['nps', 'trend', 'nps'], ['loans', 'loan', 'loans']];
export function assetsAvailable() {
  const P = C.M.positions || [], has = (k) => P.some((p) => p.kind === k);
  return ASSETS.filter(([k]) => k === 'all' || k === 'bank' || (k === 'fd' && has('deposit')) || (k === 'nps' && has('nps')) || (k === 'loans' && has('loan')));
}

/* CRED Money's first page: whose money, how much, how current. The figure follows the dock. */
function Band() {
  const nw = C.netWorth(), who = C.M.owner ? `${C.M.owner}'s` : 'your';
  const [label, figure] = { all: [`${who} net worth`, nw.all], bank: [`${who} balance`, nw.bank], fd: ['fixed deposits', nw.fd],
    nps: ['nps', nw.nps], loans: ['loans owed', nw.loans] }[C.ASSET] || [`${who} balance`, nw.bank];
  /* the caption dates the FIGURE, not the feed: a bank balance is the newest printed running balance,
     and SMS carry none, so live rows after it are named separately rather than implied in the figure */
  const P = C.M.positions || [], live = C.ALL.filter((t) => t.p).map((t) => t.d).sort().pop();
  const balOn = (C.M.accounts || []).filter((a) => !a.is_card && a.balance_on).map((a) => a.balance_on).sort().pop();
  const asOf = (kind) => P.filter((p) => p.kind === kind).map((p) => p.as_of).sort().pop();
  const fresh = {
    bank: balOn ? `as of ${C.shortDate(balOn)}${live && live > balOn ? ` · live to ${C.shortDate(live)}` : ''}` : '',
    fd: asOf('deposit') ? `deposited by ${C.shortDate(asOf('deposit'))}` : '', nps: asOf('nps') ? `as of ${C.shortDate(asOf('nps'))}` : '',
    loans: asOf('loan') ? `as of ${C.shortDate(asOf('loan'))}` : '', all: 'each holding as of its latest statement',
  }[C.ASSET] || '';
  const initials = (C.M.owner || C.M.account || '?').split(/\s+/).map((w) => w[0]).join('').slice(0, 2).toUpperCase();
  return (
    <header className="band">
      <div className="btop">
        <button className="av" onClick={() => C.TT()} title="switch between light and dark" aria-label="switch between light and dark"><Icon n="theme" /></button>
        <span className="me" aria-hidden="true">{initials}</span>
        <button className={`lock ${C.HUSH ? 'on' : ''}`} onClick={() => C.toggleHush()} aria-pressed={C.HUSH}
          aria-label={C.HUSH ? 'show amounts' : 'hide amounts'} title={C.HUSH ? 'show amounts' : 'hide amounts'}><Icon n={C.HUSH ? 'lock' : 'unlock'} /></button>
      </div>
      <div className="bhero">
        <span className="l">{label}</span>
        <Money p={figure} className="v" />
        {fresh && <span className="f">{fresh}</span>}
      </div>
    </header>);
}

/* the one thing on the first page most worth a look, as CRED's dock shows "Investment liquidated" */
function topAlert() {
  const P = C.M.positions || [], today = new Date().toISOString().slice(0, 10);
  const loan = P.find((p) => p.kind === 'loan' && p.next_due && p.next_due < today && p.as_of < p.next_due);
  if (loan) return { text: `${C.shortDate(loan.next_due)} EMI isn't in a statement yet`, go: 'loans', tone: 'gold' };
  const U = C.M.unsettled || [];
  if (U.length) return { text: `${U.length} live payment${U.length > 1 ? 's' : ''} never reached a statement`, go: 'bank', tone: 'gold' };
  const fd = P.find((p) => p.kind === 'deposit' && p.renews && p.principal && p.maturity_amount * p.maturity_amount / p.principal > 50000000);
  if (fd) return { text: 'an FD will outgrow the ₹5L DICGC cover on renewal', go: 'fd', tone: 'gold' };
  return null;
}

/* floating asset dock, shown while the accounts section is in view */
function Dock() {
  if (C.DET || C.TAB !== 'accounts') return null;
  const items = assetsAvailable(), alert = topAlert();
  return (
    <div className="dock" role="toolbar" aria-label="what to show">
      {alert && <button className="dalert" onClick={() => C.setAsset(alert.go)}><i className={alert.tone} />{alert.text}<Icon n="chev" size={16} /></button>}
      <div className="ditems">{items.map(([k, ic, label]) => (
        <button key={k} className={`ditem ${C.ASSET === k ? 'on' : ''}`} aria-pressed={C.ASSET === k} onClick={() => C.setAsset(k)}>
          <Icon n={ic} size={22} /><span>{label}</span></button>))}</div>
    </div>);
}

function Tabs({ onTab }) {
  return (
    <nav className="tabs" aria-label="sections">
      {C.MAIN.map(([k, ic, label]) => (
        <button key={k} className={`tab ${!C.DET && C.TAB === k ? 'on' : ''}`} aria-current={!C.DET && C.TAB === k ? 'true' : undefined}
          onClick={() => onTab(k)}><Icon n={ic} size={24} /><span>{label}</span></button>))}
    </nav>);
}

/* a drilled-in screen that is still being rebuilt: back works, nothing pretends to be there */
function NotYet({ what }) {
  return (
    <div className="view notyet">
      <Back />
      <h1 className="h1">{what}</h1>
      <p className="sub">coming next in the NeoPOP rebuild.</p>
    </div>);
}

/* the one scrolling page: every tab's section, top to bottom in tab order */
function Sections() {
  return (<>{ORDER.map((k) => {
    const S = SECTIONS[k];
    return (<section key={k} id={secId(k)} className="section"><S /></section>);
  })}</>);
}

export function Shell() {
  const mainScroll = useRef(0), spyPaused = useRef(0), wasDetail = useRef(!!C.DET);

  // light the tab whose section is under the pinned bar; the last section wins at the very bottom
  useEffect(() => {
    let raf = 0;
    const spy = () => {
      raf = 0;
      if (C.DET) return;
      mainScroll.current = window.scrollY;
      if (Date.now() < spyPaused.current) return;
      const bar = (document.querySelector('.tabs')?.getBoundingClientRect().bottom || 0) + 8;
      const atEnd = window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 2;
      let cur = ORDER[0];
      for (const k of ORDER) { const el = document.getElementById(secId(k)); if (el && el.getBoundingClientRect().top <= bar) cur = k; }
      C.setTabInView(atEnd ? ORDER[ORDER.length - 1] : cur);
    };
    const onScroll = () => { if (!raf) raf = requestAnimationFrame(spy); };
    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', onScroll);
    // ?v=<tab> opens the page at that section
    const v = new URLSearchParams(location.search).get('v');
    if (C.DET) window.scrollTo(0, 0);
    else if (ORDER.includes(v) && v !== ORDER[0]) document.getElementById(secId(v))?.scrollIntoView();
    spy();
    return () => { window.removeEventListener('scroll', onScroll); window.removeEventListener('resize', onScroll); };
  }, []);

  // coming back from a drilled-in screen lands where you left the page; opening one starts at its top,
  // after any field that focuses itself on mount (NeoPOP's SearchBar does) has pulled the page down
  const lastDet = useRef(C.DET);
  useLayoutEffect(() => {
    if (wasDetail.current && !C.DET) window.scrollTo(0, mainScroll.current);
    else if (C.DET && C.DET !== lastDet.current) window.scrollTo(0, 0);
    wasDetail.current = !!C.DET; lastDet.current = C.DET;
  });

  const onTab = (k) => {
    const scrollTo = () => {
      spyPaused.current = Date.now() + 700;               // don't flicker through the sections passed on the way
      C.setTabInView(k);
      // the first section opens the page at its very top, header band included
      if (k === ORDER[0]) window.scrollTo({ top: 0, behavior: 'smooth' });
      else document.getElementById(secId(k))?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    };
    if (C.DET) { C.go(k); requestAnimationFrame(scrollTo); } else scrollTo();
  };

  const Detail = C.DET ? DETAILS[C.DET] : null;
  return (
    <div className={`app ${C.HUSH ? 'hush' : ''}`}>
      <WeaveDefs />
      <Band />
      <Tabs onTab={onTab} />
      <main className="sheet">
        {C.DET ? (Detail ? <Detail /> : <NotYet what={NAMES[C.DET] || C.DET} />) : <Sections />}
      </main>
      <Dock />
      {C.TOAST && <div className="toast on" role="status">{C.TOAST}</div>}
    </div>);
}

/* the banknote weave the cash-flow bars are printed with; one pattern per flow, coloured by token */
function WeaveDefs() {
  const p = (id, v) => (
    <pattern id={id} width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(-38)">
      <path d="M-1.25 2.5 Q0 .6 1.25 2.5 T3.75 2.5 T6.25 2.5" fill="none" style={{ stroke: `var(--${v})` }} strokeWidth=".7" />
    </pattern>);
  return (<svg width="0" height="0" style={{ position: 'absolute' }} aria-hidden="true" focusable="false">
    <defs>{p('wv-in', 'inL')}{p('wv-out', 'outL')}{p('wv-inv', 'invL')}</defs></svg>);
}
