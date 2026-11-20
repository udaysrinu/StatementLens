// The screens behind the totals: one tag / merchant / person, the full searchable ledger, what got
// netted, and what each card bill paid for. Each is the rows a figure elsewhere was built from.
import React, { useMemo, useState } from 'react';
import { ElevatedCard, SearchBar } from '@cred/neopop-web/lib/components';
import * as C from '../core.js';
import { Icon, Money, NBtn, Back } from '../ui.jsx';
import { IconDisc, TxRow } from './parts.jsx';
import { PeriodPanel } from './period.jsx';
import { MonthChart } from './MonthChart.jsx';

/** one tag, merchant or person: its months, its total, its top merchants, its rows */
export function TagDetail() {
  const key = C.TAGVIEW || C.MERVIEW, byTag = !!C.TAGVIEW;
  const match = (t) => (byTag ? t.c === key : C.PERVIEW ? t.cp === C.PERVIEW : (t.m || '') === key);
  const rows = C.rangeFilter().filter(match);
  const tot = rows.filter((t) => t.f !== 'i' && t.f !== 'x').reduce((s, t) => s + C.sa(t), 0);
  const inTot = rows.filter((t) => t.f === 'i').reduce((s, t) => s + t.a, 0);
  const byMer = {}, cnt = {};
  rows.forEach((t) => { if (t.f === 'i' || t.f === 'x') return; const m = t.m || t.desc; byMer[m] = (byMer[m] || 0) + C.sa(t); cnt[m] = (cnt[m] || 0) + 1; });
  const mers = Object.keys(byMer).map((m) => ({ m, a: byMer[m], n: cnt[m] })).sort((a, b) => b.a - a.a);
  const maxA = Math.max(...mers.map((m) => m.a), 1);
  const sorted = rows.slice().sort(C.SORT === 'high' ? (a, b) => b.a - a.a : (a, b) => (a.d < b.d ? 1 : -1)).slice(0, 80);
  return (
    <div className="view">
      <Back label={C.FROMTAG || 'back'} />
      <div className="tr"><h1 className="h1">{key}</h1>
        <NBtn onClick={() => C.toggleTrend()}>{C.TREND === 'month' ? 'entire month' : 'till date'}</NBtn></div>
      {/* a tag's or merchant's history belongs to no single flow, so it highlights in ink */}
      <MonthChart rows={C.shareRows(C.netFilter(C.ALL)).filter(match)} pick={(t) => t.f !== 'x'} color="var(--ink)" />
      <div className="tr"><div><div className="cap">total amount</div><div className="hero sm"><Money p={tot || inTot} /></div>
        <div className="sub">{rows.length} transactions {C.rangeLabel()}</div></div>
        <NBtn onClick={() => C.setSort(C.SORT === 'high' ? 'recent' : 'high')}>{C.SORT === 'high' ? 'high to low' : 'most recent'}</NBtn></div>
      {byTag && mers.length > 1 && <>
        <div className="st"><h2>top merchants</h2></div>
        <div className="rlist">{mers.slice(0, 12).map((m) => (
          <button key={m.m} className="row" onClick={() => C.openMerchant(m.m)}>
            <IconDisc icon={C.catIcon(key)} />
            <span className="rm"><span className="rn">{m.m}</span><span className="rs">{m.n}× · ~{C.fmtK(Math.round(m.a / m.n))} each</span>
              <span className="bar"><i style={{ width: `${(m.a / maxA * 100).toFixed(0)}%` }} /></span></span>
            <span className="rr"><span className="ra"><Money p={m.a} /></span></span>
            <Icon n="chev" size={16} style={{ color: 'var(--ink3)', flex: 'none' }} />
          </button>))}</div></>}
      <div className="st"><h2>transactions</h2></div>
      <div className="rlist">{sorted.length ? sorted.map((t) => <TxRow key={t.ref} t={t} />) : <div className="empty">nothing in this period</div>}</div>
    </div>);
}

/** the full ledger: period, a search over merchant / tag / amount, rows under day headers */
export function Search() {
  const [q, setQ] = useState('');
  const rows = C.rangeFilter().slice().reverse().slice(0, 800);
  const hits = useMemo(() => {
    const s = q.trim().toLowerCase(); if (!s) return rows;
    return rows.filter((t) => `${t.m || ''} ${t.desc || ''} ${t.c || ''} ${C.fmt(t.a)} ${(t.a / 100).toFixed(2)}`.toLowerCase().includes(s));
  }, [q, rows]);
  const days = [];
  hits.forEach((t) => { if (!days.length || days[days.length - 1].d !== t.d) days.push({ d: t.d, rows: [] }); days[days.length - 1].rows.push(t); });
  return (
    <div className="view">
      <Back label="transactions" />
      <h1 className="h1">all transactions</h1>
      <SearchBar placeholder="search a merchant, tag or amount" handleSearchInput={(v) => setQ(v || '')} colorMode={C.isDark() ? 'dark' : 'light'} />
      <PeriodPanel />
      <div className="sub">{hits.length} of {rows.length} {C.rangeLabel()}</div>
      {days.length ? days.map((g) => (
        <div key={g.d}><div className="dayh">{C.dayLabel(g.d)}</div>
          <div className="rlist">{g.rows.map((t) => <TxRow key={t.ref} t={t} withDate={false} />)}</div></div>))
        : <div className="empty">nothing matches</div>}
    </div>);
}

/** what got netted: the audit trail behind every netted total */
export function Netting() {
  const rows = C.periodRows(), have = new Set(rows.map((t) => t.ref)), byRef = {};
  rows.forEach((t) => { byRef[t.ref] = t; });
  const seen = new Set(), pairs = [];
  for (const t of rows) {
    if (!t.rev || !have.has(t.rev) || seen.has(t.ref)) continue;
    seen.add(t.ref); seen.add(t.rev); const other = byRef[t.rev];
    pairs.push(t.dir === 'D' ? [t, other] : [other, t]);
  }
  pairs.sort((a, b) => b[0].a - a[0].a);
  const meta = Object.fromEntries((C.DATA.reversals || []).map((r) => [r.out_ref, r]));
  const by = {}; rows.forEach((t) => { if (t.cp) (by[t.cp] = by[t.cp] || []).push(t); });
  const ppl = [];
  for (const cp in by) {
    const rs = by[cp], paid = rs.filter((t) => t.dir === 'D').reduce((s, t) => s + t.a, 0), got = rs.filter((t) => t.dir === 'C').reduce((s, t) => s + t.a, 0);
    if (paid && got) ppl.push({ cp, name: rs[0].cpn || rs[0].m || cp, paid, got, net: paid - got, off: Math.min(paid, got), n: rs.length });
  }
  ppl.sort((a, b) => b.off - a.off);
  return (
    <div className="view">
      <Back label="back" />
      <div><div className="cap">cancelled {C.rangeLabel()}</div><div className="hero sm"><Money p={pairs.reduce((s, p) => s + p[0].a, 0)} /></div>
        <div className="sub">across {pairs.length} pair{pairs.length !== 1 ? 's' : ''}</div></div>
      <div className="note bare"><Icon n="spark" /><div>a cancelled pair is money that left and came straight back: a failed booking or a bounced
        transfer. netting people off is different. both transfers were real, so it is a preference, not a correction.</div></div>
      <div className="st"><h2>cancelled pairs</h2></div>
      <div className="rlist">{pairs.length ? pairs.map(([d, c]) => {
        const m = meta[d.ref] || {}, days = m.days != null ? m.days : '';
        return (<button key={d.ref} className="row" onClick={() => C.openTxn(d.ref)}><IconDisc icon="repeat" />
          <span className="rm"><span className="rn">{d.m || d.desc}</span><span className="rs">{C.shortDate(d.d)} to {C.shortDate(c.d)}{days !== '' ? ` · ${days === 0 ? 'same day' : days + 'd'}` : ''}{m.confidence === 'certain' ? ' · bank reference matches' : ''}</span></span>
          <span className="rr"><span className="ra"><Money p={d.a} /></span></span><Icon n="chev" size={16} style={{ color: 'var(--ink3)', flex: 'none' }} /></button>);
      }) : <div className="empty">nothing cancelled in this period</div>}</div>
      <div className="st"><h2>money moved both ways</h2></div>
      <div className="rlist">{ppl.length ? ppl.map((p) => (
        <button key={p.cp} className="row" onClick={() => C.openPerson(p.cp, p.name)}><IconDisc icon="person" />
          <span className="rm"><span className="rn">{p.name}</span><span className="rs">paid {C.fmtK(p.paid)} · got back {C.fmtK(p.got)} · {p.n} rows</span></span>
          <span className="rr"><span className={`ra ${p.net < 0 ? 'in' : ''}`}>{p.net === 0 ? 'settled' : <Money p={Math.abs(p.net)} />}</span>
            <span className="rd">{p.net > 0 ? 'you sent more' : p.net < 0 ? 'you got more' : 'square'}</span></span>
          <Icon n="chev" size={16} style={{ color: 'var(--ink3)', flex: 'none' }} /></button>)) : <div className="empty">no two-way counterparties in this period</div>}</div>
    </div>);
}

/** a card payment on the bank statement is one line; these are the charges behind each one */
export function Bills() {
  const cs = C.DATA.bill_cycles || [];
  if (!cs.length) return <div className="view"><Back /><div className="empty">no bill payments found on this card yet</div></div>;
  const paidTot = cs.reduce((s, c) => s + c.paid, 0);
  return (
    <div className="view">
      <Back />
      <div><div className="cap">bills paid · {C.M.account}</div><div className="hero sm"><Money p={paidTot} /></div>
        <div className="sub">across {cs.filter((c) => c.paid).length} payments</div></div>
      <div className="cards">{cs.map((c, i) => {
        const open = C.BILLOPEN === i;
        const kids = open ? (c.refs || []).map((r) => C.ALL.find((x) => x.ref === r)).filter(Boolean).sort((a, b) => b.a - a.a).slice(0, 40) : [];
        const short = c.paid ? (c.unpaid > 0 ? `${C.fmtK(c.unpaid)} rolled over` : c.unpaid < 0 ? `${C.fmtK(-c.unpaid)} paid ahead` : 'settled in full') : 'awaiting a bill';
        return (
          <ElevatedCard key={i} backgroundColor="var(--bg)" edgeColors={{ bottom: open ? 'var(--ink)' : 'var(--line2)', right: open ? 'var(--ink)' : 'var(--line2)' }} style={{ width: '100%' }}>
            <button className="billhead" onClick={() => C.toggleBill(i)} aria-expanded={open}>
              <span className="bh1"><span className="bpaid">{c.paid ? <Money p={c.paid} /> : 'not paid'}</span><span className="bwhen">{c.paid_on ? C.shortDate(c.paid_on) : 'not yet billed'}</span></span>
              <span className="bh2">{c.count} charge{c.count !== 1 ? 's' : ''} · {C.fmtK(c.charges)}{c.fees ? ` · ${C.fmtK(c.fees)} fees` : ''}{c.from_date ? ` · ${C.shortDate(c.from_date)} to ${C.shortDate(c.to_date)}` : ''}</span>
              <span className={`bh3 ${c.unpaid > 0 ? 'warn' : ''}`}>{short}<Icon n={open ? 'chevd' : 'chev'} size={16} /></span>
            </button>
            {open && <div className="billkids"><div className="rlist">{kids.length ? kids.map((t) => <TxRow key={t.ref} t={t} />) : <div className="empty">no charges in this cycle</div>}</div></div>}
          </ElevatedCard>);
      })}</div>
    </div>);
}
