// Transactions section (latest rows, live tags, payments a statement never confirmed) and the
// transaction screen (tag it, note it). Tag changes go through core.setTag, which saves to the server.
import React, { useMemo, useState } from 'react';
import { ElevatedCard, SearchBar } from '@cred/neopop-web/lib/components';
import * as C from '../core.js';
import { Icon, Money, NBtn, Back } from '../ui.jsx';
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
      <NBtn key={a.account} variant={a.account === C.M.account ? 'primary' : 'secondary'}
        onClick={() => { if (a.account !== C.M.account) location.href = C.accHref(a.account, 'txns'); }}>{a.account}</NBtn>))}
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
        <NBtn key={v.tag} variant={v.tag === sel ? 'primary' : 'secondary'} onClick={() => C.pickTag(v.tag)} aria-pressed={v.tag === sel}>{v.tag}</NBtn>))}
      </div>
      <textarea className="notefield" rows="2" placeholder="add a note: why was this payment made?" aria-label="note"
        defaultValue={C.NOTES[t.ref] || t.note || ''} onChange={(e) => C.setNote(t.ref, e.target.value)} />
      <div className="actbar">
        <NBtn size="big" variant="primary" fullWidth onClick={() => C.backFromDetail()}>Skip</NBtn>
        <NBtn size="big" fullWidth disabled={!C.TAGPICK || C.TAGPICK === cur} onClick={() => C.confirmTag()}>Confirm</NBtn>
      </div>
    </div>);
}
