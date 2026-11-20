// "your cash flow": three extruded bars on one scale (NeoPOP ElevatedCards printed with the banknote
// weave), the three flows as rows, then the self-transfer note and the insights. Same content as the
// plain-CSS cashflowV(); every figure comes from core.compute(), unchanged.
import React from 'react';
import { ElevatedCard } from '@cred/neopop-web/lib/components';
import * as C from '../core.js';
import { Icon, Money, Highlighted, NBtn } from '../ui.jsx';
import { PeriodPanel } from './period.jsx';

const BAR = { in: { cls: 'in', code: 'i' }, inv: { cls: 'inv', code: 'v' }, out: { cls: 'out', code: 's' } };
const edge = (cls) => ({ bottom: `var(--${cls}S)`, right: `var(--${cls}S)` });

function Bars({ R }) {
  const mx = Math.max(R.inn, R.inv, R.out, 1);
  const amt = { in: R.inn, inv: R.inv, out: R.out };
  return (
    <div>
      <div className="cfchart">
        {C.FLOWORDER.map((k) => {
          const h = Math.max(1.5, Math.max(0, amt[k]) / mx * 100), cls = BAR[k].cls;
          return (
            <button key={k} className="cfbar" onClick={() => C.setFlow(k)}
              aria-label={`${C.FLOWS[k].label} ${C.fmt(amt[k])}, open the breakdown`}>
              <span className="cfv num">{C.fmtK(amt[k])}</span>
              <span className="cfgrow" style={{ height: `${h}%` }}>
                <ElevatedCard backgroundColor={`var(--${cls}F)`} edgeColors={edge(cls)} style={{ width: '100%', height: '100%' }}>
                  <svg className="weave" aria-hidden="true"><rect width="100%" height="100%" fill={`url(#wv-${cls})`} /></svg>
                </ElevatedCard>
              </span>
            </button>);
        })}
      </div>
      <div className="cfl"><span>{C.M.is_card ? 'paid off' : 'incoming'}</span><span>investments</span><span>{C.M.is_card ? 'charged' : 'spends'}</span></div>
    </div>);
}

function FlowRows({ R }) {
  const rows = [['in', C.M.is_card ? 'paid off' : 'incoming', R.inn], ['inv', 'investments', R.inv], ['out', C.M.is_card ? 'charged' : 'spends', R.out]];
  return (
    <div className="rlist">
      {rows.map(([k, label, amt]) => (
        <button key={k} className="frow" onClick={() => C.setFlow(k)}>
          <span className="fn">{label}</span>
          <span className="fr">
            <span className="fa"><Money p={amt} /><Icon n="chev" size={16} /></span>
            <span className="avg num">6 months total {C.fmtK(C.sixMonthTotal(BAR[k].code))}</span>
          </span>
        </button>))}
    </div>);
}

function Note({ icon = 'spark', children, gold }) {
  return (
    <ElevatedCard backgroundColor={gold ? 'var(--goldbg)' : 'var(--s2)'} edgeColors={{ bottom: gold ? 'var(--goldline)' : 'var(--line2)', right: gold ? 'var(--goldline)' : 'var(--line2)' }}
      style={{ width: '100%' }}>
      <div className="note"><Icon n={icon} size={20} /><div>{children}</div></div>
    </ElevatedCard>);
}

export function CashFlow() {
  const rows = C.rangeFilter(), R = C.compute(rows);
  return (
    <div className="view">
      <h1 className="h1">your cash flow</h1>
      <div className="chips">
        <NBtn onClick={() => C.go('accounts')}>{C.M.account || 'account'}</NBtn>
        <NBtn onClick={() => C.togglePeriod()} aria-expanded={C.PERIODOPEN}>{C.periodText()}</NBtn>
      </div>
      {C.PERIODOPEN && <PeriodPanel />}
      {C.M.salary_day > 1 && C.CYCLENOTE && (
        <Note icon="star" gold>
          introducing salary cycle. your cash flow can start from your salary date, the {C.ord(C.M.salary_day)}, instead of the calendar month.
          <div className="noteacts">
            <NBtn kind="link" onClick={() => { C.setR('S'); C.dismissCycle(); }}>use salary cycle</NBtn>
            <NBtn kind="link" onClick={() => C.dismissCycle()}>understood</NBtn>
          </div>
        </Note>)}
      <Bars R={R} />
      <FlowRows R={R} />
      {R.slfN > 0 && <Note>self-transfers and card bill payments are left out of both sides · <span className="num">{C.fmtK(R.slf)}</span> across {R.slfN} transactions</Note>}
      {C.DATA.insights.length > 0 && <div className="st"><h2>for you</h2></div>}
      {C.DATA.insights.map((c, i) => (
        <Note key={i} icon={c.icon}><b>{c.title}.</b> <Highlighted text={c.copy} /></Note>))}
    </div>);
}
