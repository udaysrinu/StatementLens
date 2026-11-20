// Accounts section (bank accounts, credit cards, loans & deposits) and one account's screen.
import React from 'react';
import { ElevatedCard } from '@cred/neopop-web/lib/components';
import * as C from '../core.js';
import { Icon, Money, NBtn, Back } from '../ui.jsx';
import { BankDisc, Freshness, TxRow } from './parts.jsx';

const card = { bottom: 'var(--edge)', right: 'var(--edge)' };

function AccountCard({ a }) {
  return (
    <ElevatedCard backgroundColor="var(--bg)" edgeColors={card} style={{ width: '100%' }}>
      <button className="arow" onClick={() => C.openAccount(a.account)}>
        <BankDisc acc={a.account} />
        <span className="am"><span className="an">{a.account}</span><span className="aa"><i />{a.count} transactions</span></span>
        <span className="ar">{a.balance != null
          ? <><span className="abal"><Money p={a.balance} /></span><span className="alink">as of {C.shortDate(a.balance_on)}</span></>
          : <span className="alink">to {C.shortDate(a.date_max)}</span>}</span>
        <Icon n="chev" size={16} style={{ color: 'var(--ink3)', flex: 'none' }} />
      </button>
    </ElevatedCard>);
}

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

export function Accounts() {
  const accs = C.M.accounts && C.M.accounts.length ? C.M.accounts
    : [{ account: C.M.account, count: C.M.txn_count, is_card: C.M.is_card, balance: null, date_max: C.M.max_date }];
  const banks = accs.filter((a) => !a.is_card), cards = accs.filter((a) => a.is_card), pos = C.M.positions || [];
  return (
    <div className="view">
      <h1 className="h1">your accounts</h1>
      <Freshness />
      {banks.length > 0 && <><div className="st"><h2>bank accounts</h2></div><div className="cards">{banks.map((a) => <AccountCard key={a.account} a={a} />)}</div></>}
      {cards.length > 0 && <><div className="st"><h2>credit cards</h2></div><div className="cards">{cards.map((a) => <AccountCard key={a.account} a={a} />)}</div></>}
      {pos.length > 0 && <><div className="st"><h2>loans &amp; deposits</h2></div><div className="rlist">{pos.map((p) => <Position key={p.label} p={p} />)}</div></>}
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
