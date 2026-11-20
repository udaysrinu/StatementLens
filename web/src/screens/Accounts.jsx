// Accounts section (bank accounts, credit cards, loans & deposits) and one account's screen.
import React from 'react';
import { ElevatedCard } from '@cred/neopop-web/lib/components';
import * as C from '../core.js';
import { Icon, Money, NBtn, Back } from '../ui.jsx';
import { BankDisc, Freshness, TxRow } from './parts.jsx';

const card = { bottom: 'var(--edge)', right: 'var(--edge)' };

/* Loans and deposits are positions: what is owed or held as of a statement date. Never in a total or
   the cash flow, because every EMI and the FD's funding are already debits on the paying account. */
function Position({ p }) {
  const today = new Date().toISOString().slice(0, 10);
  if (p.kind === 'loan') {
    const left = p.emis_left != null ? `${p.emis_left} of ${p.tenure_months} EMIs left` : `${p.tenure_months} months`;
    const unknown = p.next_due && p.next_due < today && p.as_of < p.next_due;   // statement predates the due date
    return (
      <div className="posrow">
        <span className="an">{p.label}</span><span className="abal"><Money p={p.outstanding} /></span>
        <span className="pmeta">owed on {C.shortDate(p.as_of)} · EMI <Money p={p.emi} /> · {left} · {p.rate_pct}%</span>
        {unknown ? <span className="pnote"><Icon n="clock" size={16} />the {C.shortDate(p.next_due)} EMI isn't in a statement yet. check it was collected</span>
          : p.next_due ? <span className="pmeta">next EMI {C.shortDate(p.next_due)}</span> : null}
      </div>);
  }
  // DICGC insures ₹5L per bank including interest; a renewing FD rolls interest into the next term
  const next = p.principal && p.renews ? Math.round(p.maturity_amount * p.maturity_amount / p.principal) : 0;
  return (
    <div className="posrow">
      <span className="an">{p.label}</span><span className="abal"><Money p={p.principal} /></span>
      <span className="pmeta">deposited {C.shortDate(p.value_date)} · {p.rate_pct}% · matures {C.shortDate(p.maturity_date)} at <Money p={p.maturity_amount} /></span>
      {next > 50000000 && <span className="pnote"><Icon n="shield" size={16} />renews automatically. at this rate the next term ends near {C.fmtK(next)}, past the ₹5L DICGC cover per bank</span>}
    </div>);
}

/* a bank account as CRED lists it: disc, name, how current, balance; tap for the account */
function AccountRow({ a }) {
  return (
    <button className="arow" onClick={() => C.openAccount(a.account)}>
      <BankDisc acc={a.account} />
      <span className="am"><span className="an">{a.account}<Icon n="chev" size={14} style={{ color: 'var(--ink3)' }} /></span>
        <span className="aa"><i />{a.count} transactions</span></span>
      <span className="ar">{a.balance != null
        ? <><span className="abal"><Money p={a.balance} /></span><span className="alink">as of {C.shortDate(a.balance_on)}</span></>
        : <span className="alink">to {C.shortDate(a.date_max)}</span>}</span>
    </button>);
}

/* NPS: what it is worth, what went in, what it earned, and how it grew month by month */
function NpsView({ p }) {
  const hist = (C.M.nps_history || []).filter((h) => h.label === p.label).slice(-12);
  const peak = Math.max(...hist.map((h) => h.value), 1);
  const last = (p.contributions || []).slice(-1)[0];
  return (<>
    <div className="posrow">
      <span className="an">{p.label}</span><span className="abal"><Money p={p.value} /></span>
      <span className="pmeta">value on {C.shortDate(p.as_of)}{p.xirr_pct != null ? ` · ${p.xirr_pct}% a year (xirr)` : ''}</span>
      <span className="pmeta">contributed <Money p={p.contributed} /> · <span className={p.gain >= 0 ? 'up' : 'down'}>{p.gain >= 0 ? '+' : ''}<Money p={p.gain} /></span> {p.gain >= 0 ? 'gain' : 'loss'}</span>
      {last && <span className="pmeta">latest <Money p={last.total} /> on {C.shortDate(last.date)} for {last.for.toLowerCase()}{last.employer && !last.employee ? ' · employer' : ''}</span>}
    </div>
    {p.schemes && p.schemes.length > 0 && <>
      <div className="st"><h2>where it sits</h2></div>
      <div className="split3" aria-label="scheme split">{p.schemes.map((x) => (
        <span key={x.scheme} style={{ flexGrow: x.value }} className={`seg s${x.scheme}`}><b>{x.scheme}</b>{(x.value / p.value * 100).toFixed(1)}%</span>))}</div>
      <div className="rlist">{p.schemes.map((x) => (
        <div key={x.scheme} className="lrow static"><span className={`lsw s${x.scheme}`} />
          <span className="lm"><span className="ln">{{ E: 'equity', C: 'corporate bonds', G: 'government bonds', A: 'alternatives' }[x.scheme] || x.scheme} · scheme {x.scheme}</span>
            <span className="lp">{x.units.toLocaleString('en-IN', { maximumFractionDigits: 4 })} units at ₹{x.nav}</span></span>
          <span className="la"><Money p={x.value} /></span></div>))}</div>
      {p.preference && <div className="sub">{p.preference.toLowerCase()}</div>}
    </>}
    {hist.length > 1 && <>
      <div className="st"><h2>value, last {hist.length} months</h2></div>
      <div className="npsh">{hist.map((h) => (
        <div key={h.as_of} className="npsc" title={`${C.shortDate(h.as_of)} · ${C.fmt(h.value)}`}>
          <span className="npsb"><i style={{ height: `${h.value / peak * 100}%` }} /><s style={{ height: `${h.contributed / peak * 100}%` }} /></span>
          <span className="blab">{C.MON[+h.as_of.slice(5, 7) - 1].toUpperCase()}<small>'{h.as_of.slice(2, 4)}</small></span></div>))}</div>
      <div className="sub"><span className="key kv1" /> value <span className="key kv2" /> contributed</div>
    </>}
  </>);
}

const NOT_TRACKED = 'mutual funds and stocks arrive with the CDSL statement reader; EPF needs its passbook PDF';

export function Accounts() {
  const accs = C.M.accounts && C.M.accounts.length ? C.M.accounts
    : [{ account: C.M.account, count: C.M.txn_count, is_card: C.M.is_card, balance: null, date_max: C.M.max_date }];
  const banks = accs.filter((a) => !a.is_card), cards = accs.filter((a) => a.is_card), P = C.M.positions || [];
  const nw = C.netWorth(), k = C.ASSET;
  const part = (key, label, amt, sign = '') => (
    <button key={key} className="arow" onClick={() => C.setAsset(key)}>
      <span className="am"><span className="an">{label}<Icon n="chev" size={14} style={{ color: 'var(--ink3)' }} /></span></span>
      <span className="ar"><span className="abal">{sign}<Money p={amt} /></span></span></button>);
  return (
    <div className="view">
      <h1 className="h1">{{ all: 'your net worth', bank: 'your accounts', fd: 'fixed deposits', nps: 'national pension system', loans: 'loans' }[k]}</h1>
      {k === 'all' && <>
        <div className="rlist">
          {part('bank', 'bank balances', nw.bank)}
          {nw.fd > 0 && part('fd', 'fixed deposits', nw.fd)}
          {nw.nps > 0 && part('nps', 'nps', nw.nps)}
          {nw.loans > 0 && part('loans', 'loans owed', nw.loans, '−')}
        </div>
        <div className="note bare"><Icon n="spark" /><div>this is net worth from what is tracked. {NOT_TRACKED}.</div></div>
      </>}
      {k === 'bank' && <>
        <Freshness />
        {banks.length > 0 && <div className="rlist">{banks.map((a) => <AccountRow key={a.account} a={a} />)}</div>}
        {cards.length > 0 && <><div className="st"><h2>credit cards</h2></div><div className="rlist">{cards.map((a) => <AccountRow key={a.account} a={a} />)}</div></>}
      </>}
      {k === 'fd' && <div className="rlist">{P.filter((p) => p.kind === 'deposit').map((p) => <Position key={p.label} p={p} />)}</div>}
      {k === 'nps' && P.filter((p) => p.kind === 'nps').map((p) => <NpsView key={p.label} p={p} />)}
      {k === 'loans' && <div className="rlist">{P.filter((p) => p.kind === 'loan').map((p) => <Position key={p.label} p={p} />)}</div>}
    </div>);
}

/** One account: balance, what it covers, interest, latest rows. */
export function AccountDetail() {
  const a = (C.M.accounts || []).find((x) => x.account === C.M.account) || { account: C.M.account };
  const yr = C.M.max_date ? C.M.max_date.slice(0, 4) : '';
  const interest = C.ALL.filter((t) => t.f === 'i' && /interest/i.test(t.src || t.c || '') && t.d && t.d.startsWith(yr)).reduce((s, t) => s + t.a, 0);
  const R = C.compute(C.ALL);
  const figure = a.balance != null ? a.balance : (C.M.is_card && C.DATA.card ? C.DATA.card.charges : R.out);
  const kv = [['statements from', C.shortDate(C.M.min_date)], ['through', C.shortDate(C.M.max_date)],
    ['transactions', String(C.M.txn_count || C.ALL.length)], ['kind', C.M.is_card ? 'credit card' : 'savings account']];
  return (
    <div className="view">
      <Back label="accounts" />
      <div className="heroc"><BankDisc acc={C.M.account} big />
        <div className="cap">{C.M.account}</div>
        <div className="hero"><Money p={figure} /></div>
        <div className="cap">{a.balance != null ? `balance on ${C.shortDate(a.balance_on)}` : (C.M.is_card ? 'charged · all time' : 'spent · all time')}</div>
      </div>
      <ElevatedCard backgroundColor="var(--goldbg)" edgeColors={{ bottom: 'var(--goldline)', right: 'var(--goldline)' }} style={{ width: '100%' }}>
        <div className="kv">{kv.map(([k, v]) => <div key={k}><div className="k">{k}</div><div className="v">{v}</div></div>)}</div>
      </ElevatedCard>
      {!C.M.is_card && <><div className="st"><h2>interest earned in {yr}</h2></div><div className="kvbig"><Money p={interest} /></div></>}
      <div className="st"><h2>latest</h2></div>
      <div className="rlist">{C.ALL.slice().reverse().slice(0, 5).map((t) => <TxRow key={t.ref} t={t} />)}</div>
      <Freshness />
    </div>);
}
