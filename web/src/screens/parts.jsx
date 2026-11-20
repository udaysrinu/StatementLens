// Pieces several sections share: icon/bank discs, the transaction row, the freshness line.
import React, { useState } from 'react';
import * as C from '../core.js';
import { Icon, Money, NBtn } from '../ui.jsx';

/** A category icon on a disc, with a dot in the bank's colour. */
export const IconDisc = ({ icon, acc }) => (
  <span className="ic" aria-hidden="true"><Icon n={icon} size={20} /><span className="bb"><i style={{ '--bk': C.bankHue(acc || C.M.account) }} /></span></span>
);

/** A bank as a monogram on a disc in its colour (no third-party logos ship with the repo). */
export const BankDisc = ({ acc, big }) => (
  <span className={`bm ${big ? 'big' : ''}`} style={{ '--bk': C.bankHue(acc) }} aria-hidden="true">{C.bankMono(acc)}</span>
);

/** One transaction row; taps open its screen. */
export function TxRow({ t, withDate = true }) {
  const isIn = t.f === 'i';
  const split = t.mine != null ? `split · ${C.fmtK(t.mine)} mine` : null;
  const sub = [t.c, t.f === 'x' ? 'self' : null, split, t.note ? 'note' : null].filter(Boolean).join(' · ');
  return (
    <button className="row" onClick={() => C.openTxn(t.ref)}>
      <IconDisc icon={C.catIcon(t.c)} />
      <span className="rm"><span className="rn">{t.m || t.desc}</span>
        <span className="rs">{sub}{t.p ? <span className="live" title="from a bank SMS or alert; the monthly statement will confirm it">live</span> : null}</span></span>
      <span className="rr"><span className={`ra ${isIn ? 'in' : ''}`}>{isIn ? '+' : ''}<Money p={t.a} /></span>
        {withDate && <span className="rd">{C.shortDate(t.d)}</span>}</span>
      <Icon n="chev" size={16} style={{ color: 'var(--ink3)', flex: 'none' }} />
    </button>);
}

/** How current the data is, plus a refresh that checks the mailbox (only when served, not opened as a file). */
export function Freshness() {
  const s = C.M.sync || {}, [busy, setBusy] = useState('');
  const last = (C.M.accounts || []).map((a) => a.date_max).filter(Boolean).sort().pop();
  const imported = s.label === 'never synced' && last;     // a folder import has data but no mail-sync record
  const text = imported ? `statements to ${C.shortDate(last)}` : [s.label, s.reason].filter(Boolean).join(' · ') || 'synced from your statements';
  const refresh = () => {
    setBusy('checking…');
    C.post('/api/refresh', {}).then((r) => {
      if (r && (r.error || (r.reason && !r.ok))) { setBusy(''); return C.toast(r.error || r.reason); }
      if (r && (r.inserted || r.duplicate)) location.reload();
      else { setBusy('up to date'); setTimeout(() => setBusy(''), 2200); }
    });
  };
  return (
    <div className={`fresh ${s.stale && !imported ? 'stale' : ''}`}>
      <Icon n="bank" size={18} /><span>{text}</span>
      {C.API && <NBtn kind="link" onClick={refresh} disabled={!!busy}>{busy || 'refresh'}</NBtn>}
    </div>);
}
