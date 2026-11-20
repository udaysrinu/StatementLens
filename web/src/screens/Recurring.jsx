// Recurring section: outgoing / incoming, one detected payment at a time on a raised card, then all of them.
import React from 'react';
import { ElevatedCard } from '@cred/neopop-web/lib/components';
import * as C from '../core.js';
import { Icon, Money, NBtn } from '../ui.jsx';
import { IconDisc } from './parts.jsx';

export function Recurring() {
  const list = (C.RECDIR === 'out' ? (C.DATA.recurring || []) : C.incomingRecurring()).filter((r) => r.active);
  const n = list.length, i = ((C.RECI % Math.max(n, 1)) + Math.max(n, 1)) % Math.max(n, 1), r = list[i];
  const kv = r ? [[C.RECDIR === 'out' ? 'from' : 'into', C.M.account], [`usually ${C.RECDIR === 'out' ? 'paid' : 'arrives'} by`, C.ord(r.usual_day)],
    ['seen', `${r.months} months`]].concat(r.next_expected ? [['next', '~' + C.shortDate(r.next_expected)]] : []) : [];
  return (
    <div className="view">
      <div><h1 className="h1">recurring payments</h1><div className="cap" style={{ marginTop: 6 }}>{n} detected from your statements</div></div>
      <div className="chips">
        <NBtn variant={C.RECDIR === 'out' ? 'secondary' : 'primary'} onClick={() => C.setRecDir('out')}>outgoing</NBtn>
        <NBtn variant={C.RECDIR === 'in' ? 'secondary' : 'primary'} onClick={() => C.setRecDir('in')}>incoming</NBtn>
      </div>
      {r ? <>
        <ElevatedCard backgroundColor="var(--bg)" edgeColors={{ bottom: 'var(--edge)', right: 'var(--edge)' }} style={{ width: '100%' }}>
          <button className="rcard" onClick={() => C.openMerchant(r.merchant)}>
            <IconDisc icon={C.catIcon(C.rowCat(r.merchant))} />
            <span className="ramt"><Money p={r.median} /></span><span className="rnm2">{r.merchant}</span>
            {kv.map(([k, v]) => <span key={k} className="rkv"><span>{k}:</span><b>{v}</b></span>)}
          </button>
        </ElevatedCard>
        <div className="rpos">{i + 1} out of {n}</div>
        <div className="rnav">
          <NBtn size="medium" variant="primary" disabled={n < 2} onClick={() => C.recStep(-1)}>Previous</NBtn>
          <NBtn size="medium" disabled={n < 2} onClick={() => C.recStep(1)}>Next</NBtn>
        </div>
        <div className="st"><h2>all {n}</h2></div>
        <div className="rlist">{list.map((x) => (
          <button key={x.merchant} className="row" onClick={() => C.openMerchant(x.merchant)}>
            <IconDisc icon={C.catIcon(C.rowCat(x.merchant))} />
            <span className="rm"><span className="rn">{x.merchant}</span><span className="rs">{x.months} months · the {C.ord(x.usual_day)}</span></span>
            <span className="rr"><span className="ra"><Money p={x.median} /></span></span>
            <Icon n="chev" size={16} style={{ color: 'var(--ink3)', flex: 'none' }} />
          </button>))}</div>
      </> : <div className="empty">no recurring {C.RECDIR === 'out' ? 'payments' : 'credits'} detected yet</div>}
    </div>);
}
