// Transactions section (latest rows, live tags, payments a statement never confirmed) and the
// transaction screen (tag it, note it). Tag changes go through core.setTag, which saves to the server.
import React, { useEffect, useMemo, useState } from 'react';
import { ElevatedCard, SearchBar } from '@cred/neopop-web/lib/components';
import * as C from '../core.js';
import { Icon, Money, NBtn, Pill, Back } from '../ui.jsx';
import { IconDisc, TxRow } from './parts.jsx';

function Unsettled() {
  const U = C.M.unsettled || [];
  if (!U.length) return null;
  return (
    <ElevatedCard backgroundColor="var(--goldbg)" edgeColors={{ bottom: 'var(--goldline)', right: 'var(--goldline)' }} style={{ width: '100%' }}>
      <div className="note"><Icon n="clock" />
        <div><b>{U.length} live {U.length > 1 ? 'payments' : 'payment'} never reached a statement.</b> a failed or reversed payment looks
          like this, so {U.length > 1 ? 'they are' : 'it is'} left out of your totals:
          {U.map((u, i) => <span key={i} className="unrow">{u.direction === 'credit' ? '+' : ''}<Money p={u.minor} /> · {C.shortDate(u.date)} · {u.description}</span>)}
        </div></div>
    </ElevatedCard>);
}

/* other accounts' transactions live on their own dataset, so switching reloads with that account */
function AccountChips() {
  const list = C.M.accounts || [];
  if (list.length < 2) return null;
  return (
    <div className="chips">{list.map((a) => (
      <Pill key={a.account} on={a.account === C.M.account}
        onClick={() => { if (a.account !== C.M.account) location.href = C.accHref(a.account, 'txns'); }}>{a.account}</Pill>))}
    </div>);
}

export function Transactions() {
  const rows = C.rangeFilter().slice().reverse();
  return (
    <div className="view">
      <div className="thead"><h1 className="h1">your transactions</h1>
        <NBtn onClick={() => C.openDetail('search')}>search</NBtn></div>
      <Unsettled />
      <AccountChips />
      <div className="rlist">{rows.length ? rows.slice(0, 8).map((t) => <TxRow key={t.ref} t={t} />) : <div className="empty">no transactions yet</div>}</div>
      {rows.length > 8 && <div><NBtn size="medium" onClick={() => C.openDetail('search')}>view all {rows.length}</NBtn></div>}
    </div>);
}

/* A shared charge: only on money going OUT. The billed amount never changes (the statement still says
   it); only what counts as YOUR spending does. */
function SplitEditor({ t }) {
  if (t.f === 'i' || t.f === 'x') return null;
  const cur = C.SPLITS[t.ref] !== undefined ? C.SPLITS[t.ref] : (t.mine != null ? t.mine : null);
  const isSplit = cur != null && cur !== t.a;
  return (<>
    <div className="st"><h2>shared?</h2></div>
    <div className="split">
      <div className="sub">split a charge someone owes you for. your statement still says <span className="num">{C.fmt(t.a)}</span>; only what counts as <b>your</b> spending changes.</div>
      {isSplit ? <>
        <div className="srow"><span className="l">your share</span><span className="sv"><Money p={cur} /></span></div>
        <div className="srow"><span className="l">recoverable</span><span className="sr"><Money p={t.a - cur} /></span></div></>
        : <div className="sub">all <span className="num">{C.fmt(t.a)}</span> counts as yours</div>}
      <div className="chips">
        {[2, 3, 4].map((n) => { const share = Math.round(t.a / n);
          return <Pill key={n} on={isSplit && Math.abs(cur - share) <= 1} title={`your share if ${n} people shared this`}
            onClick={() => C.applySplit(t.ref, share)}>1/{n}</Pill>; })}
        {isSplit && <NBtn kind="link" onClick={() => C.applySplit(t.ref, null)}>clear</NBtn>}
      </div>
      <div className="sfields">
        <input className="field num" type="text" inputMode="decimal" placeholder="exact ₹ share" aria-label="your exact share"
          key={`x${t.ref}${cur}`} defaultValue={isSplit ? (cur / 100).toFixed(2) : ''}
          onBlur={(e) => { const v = e.target.value.trim(); if (v) C.applySplit(t.ref, Math.round(parseFloat(v) * 100)); }} />
        <input className="field" placeholder="with whom? (for your reference)" aria-label="split with whom"
          defaultValue={t.with || ''} onBlur={(e) => C.setSplitWith(t.ref, e.target.value)} />
      </div>
    </div></>);
}

/* transactions that look like the same merchant, ticked by default, retagged together */
function Similar({ t }) {
  const [g, setG] = useState(null), [sel, setSel] = useState(new Set()), [tag, setTag] = useState('');
  useEffect(() => { let live = true;
    C.similarFor(t.ref).then((r) => { if (!live) return; setG(r); setSel(new Set(r ? r.sample.map((s) => s.ref) : [])); setTag(t.c || ''); });
    return () => { live = false; }; }, [t.ref]);
  if (!g) return null;
  const all = sel.size === g.sample.length;
  const flip = (ref) => { const n = new Set(sel); n.has(ref) ? n.delete(ref) : n.add(ref); setSel(n); };
  return (<>
    <div className="tr"><div className="st"><h2>similar transactions</h2></div>
      <NBtn kind="link" onClick={() => setSel(all ? new Set() : new Set(g.sample.map((s) => s.ref)))}>{all ? 'clear all' : 'select all'}</NBtn></div>
    <div className="sub">{g.reason}. tick the ones that belong together, pick a tag, and they all update.</div>
    {(g.current_tags || []).length > 1 && <div className="note bare"><Icon n="spark" /><div>these are tagged inconsistently right now: {g.current_tags.join(', ')}</div></div>}
    <div className="rlist">{g.sample.map((s) => (
      <label key={s.ref} className="simrow"><input type="checkbox" checked={sel.has(s.ref)} onChange={() => flip(s.ref)} />
        <span className="simmain"><span className="simnm">{s.desc}</span><span className="simsub">{C.dayLabel(s.date)} · {s.tag || 'untagged'}</span></span>
        <span className="simamt num">{s.dir === 'C' ? '+' : '−'}{C.fmt(s.amount).replace('−', '')}</span></label>))}</div>
    <div className="simbar">
      <select className="field" value={tag} onChange={(e) => setTag(e.target.value)} aria-label="tag for the selected">
        {(C.DATA.tag_vocab || []).map((v) => <option key={v.tag} value={v.tag}>{v.tag}</option>)}</select>
      <NBtn size="medium" disabled={!sel.size || !tag} onClick={() => C.tagMany(tag, [...sel])}>Tag {sel.size} selected</NBtn>
    </div></>);
}

/** One transaction: the receipt, then the tag grid; Confirm saves merchant-wide. */
export function TxnDetail() {
  const t = C.ALL.find((x) => x.ref === C.TXNREF);
  const [q, setQ] = useState('');
  const vocab = useMemo(() => (C.DATA.tag_vocab || []).filter((v) => v.tag.includes(q.toLowerCase())), [q]);
  if (!t) return <div className="view"><Back /><div className="empty">transaction not found</div></div>;
  const cur = C.OVERRIDE[t.ref] || t.c, isIn = t.f === 'i', sel = C.TAGPICK || cur;
  return (
    <div className="view txv">
      <Back label="transactions" />
      <ElevatedCard backgroundColor="var(--bg)" edgeColors={{ bottom: 'var(--edge)', right: 'var(--edge)' }} style={{ width: '100%' }}>
        <div className="txh">
          <IconDisc icon={C.catIcon(cur)} />
          <div className="txnm">{t.m || t.desc}</div>
          <div className={`txamt ${isIn ? 'in' : ''}`}>{isIn ? '+' : ''}<Money p={t.a} /></div>
          <div className="cap">{C.shortDate(t.d)}{t.p ? ' · live' : ''}</div>
          <div className="tagbox">{cur}</div>
          <div className="cap">{isIn ? 'received into' : 'paid from'}</div>
          <div className="from"><i style={{ '--bk': C.bankHue(C.M.account) }} />{C.M.account}</div>
          {t.b != null && <div className="cap">balance after · <span className="num">{C.fmt(t.b)}</span></div>}
          {t.desc && t.m && t.desc !== t.m && <div className="narr">{t.desc}</div>}
        </div>
      </ElevatedCard>
      <div><h2 className="h2">tag this transaction for better insights</h2>
        <div className="sub" style={{ marginTop: 6 }}>the right tag sharpens every number. we'll remember it for {t.m || 'this merchant'}.</div></div>
      <SearchBar placeholder="search for category" handleSearchInput={(v) => setQ(v || '')} colorMode={C.isDark() ? 'dark' : 'light'} />
      <div className="tagwrap">{vocab.map((v) => (
        <Pill key={v.tag} className="tagpill" on={v.tag === sel} onClick={() => C.pickTag(v.tag)}>{v.tag}</Pill>))}
      </div>
      <textarea className="notefield" rows="2" placeholder="add a note: why was this payment made?" aria-label="note"
        defaultValue={C.NOTES[t.ref] || t.note || ''} onChange={(e) => C.setNote(t.ref, e.target.value)} />
      <SplitEditor t={t} />
      <Similar t={t} />
      <div className="actbar">
        <NBtn size="big" variant="primary" fullWidth onClick={() => C.backFromDetail()}>Skip</NBtn>
        <NBtn size="big" fullWidth disabled={!C.TAGPICK || C.TAGPICK === cur} onClick={() => C.confirmTag()}>Confirm</NBtn>
      </div>
    </div>);
}
