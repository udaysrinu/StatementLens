// The period control (presets, salary cycle, custom months or exact dates) and the "counting" row that
// says what a total includes. Both only call core.js setters; no money logic lives here.
import React from 'react';
import * as C from '../core.js';
import { Icon, NBtn, Pill } from '../ui.jsx';

/* rendered only when the data HAS something to net: cancelled pairs, two-way people, or splits */
export function NetRow() {
  const c = C.countable(), sp = C.splitInfo(C.periodRows());
  if (!c.pairs && !c.people && !sp.n) return null;
  const chip = (k, label, title) => (
    <Pill key={k} on={C.NET === k} onClick={() => C.setNet(k)} title={title}>{label}</Pill>);
  const removed = C.NET === 'clean' ? c.cancelledAmt : c.cancelledAmt + c.offsetAmt;
  return (
    <div className="nrow">
      <span className="nlbl">counting</span>
      {chip('gross', 'everything', 'every row exactly as the bank printed it, the only view that reconciles line by line')}
      {c.pairs > 0 && chip('clean', 'skip refunded', `${c.pairs} charge${c.pairs !== 1 ? 's' : ''} that came straight back`)}
      {c.people > 0 && chip('net', 'settle up friends', `${c.people} people you both paid and got money back from`)}
      {sp.n > 0 && <>
        <span className="nsep" />
        <Pill on={C.SHARE === 'billed'} onClick={() => C.setShare('billed')} title="the full amount the bank billed">billed</Pill>
        <Pill on={C.SHARE === 'mine'} onClick={() => C.setShare('mine')}
          title={`${sp.n} shared charge${sp.n !== 1 ? 's' : ''} · ${C.fmtK(sp.recoverable)} is someone else's`}>my share</Pill></>}
      {/* what the mode removed, in money, and a door to the rows behind it */}
      {C.NET !== 'gross' && <button className="nlink" onClick={() => C.openDetail('netting')}>
        −{C.fmtK(removed)} {C.NET === 'clean' ? 'cancelled' : 'cancelled & settled'} · what?</button>}
      {C.SHARE === 'mine' && sp.n > 0 && <span className="nnote">−{C.fmtK(sp.recoverable)} recoverable from others</span>}
    </div>);
}

function MonthPicker() {
  const have = C.monthsWithData(), years = C.pickYears();
  const year = C.PICKYEAR && years.includes(C.PICKYEAR) ? C.PICKYEAR
    : (C.CF && years.includes(C.CF.slice(0, 4)) ? C.CF.slice(0, 4) : years[years.length - 1]);
  return (
    <div className="mpick">
      <div className="yrow">{years.map((y) => (
        <Pill key={y} on={y === year} onClick={() => C.setPickYear(y)}>{y}</Pill>))}</div>
      <div className="mgrid">{C.MONTHNAMES.map((nm, i) => {
        const mo = `${year}-${String(i + 1).padStart(2, '0')}`, has = have.has(mo);
        const inR = C.CF && C.CT && mo >= C.CF.slice(0, 7) && mo <= C.CT.slice(0, 7);
        const isEnd = (C.CF && mo === C.CF.slice(0, 7)) || (C.CT && mo === C.CT.slice(0, 7));
        // a month with no statements stays visible, struck through, never hidden
        return (<button key={mo} className={`mcell ${has ? '' : 'off'} ${inR ? 'in' : ''} ${isEnd ? 'end' : ''}`}
          disabled={!has} aria-disabled={!has} title={has ? mo : `${mo}, no transactions`}
          onClick={() => has && C.pickMonth(mo)}>{nm}</button>);
      })}</div>
      <div className="mfoot">
        <span className="mhint">{C.PICKANCHOR ? `tap another month to end the range, or ${C.PICKANCHOR} again for just that month` : 'tap a month, or two to span a range'}</span>
        <NBtn kind="link" onClick={() => C.toggleExact()}>exact dates</NBtn>
      </div>
      {C.EXACT && (
        <div className="drow">
          <input type="date" value={C.CF} max={C.M.max_date || ''} onChange={(e) => C.setCF(e.target.value)} aria-label="from" />
          <Icon n="chev" size={16} />
          <input type="date" value={C.CT} max={C.M.max_date || ''} onChange={(e) => C.setCT(e.target.value)} aria-label="to" />
        </div>)}
    </div>);
}

/** presets, then the salary cycle when one was detected, then custom (months or exact dates) */
export function PeriodPanel() {
  return (
    <div className="ppanel">
      <div className="chips">
        {C.PRESETS.map(([k, label]) => (
          <Pill key={k} on={C.RANGE === k} onClick={() => C.setR(k)}>{label}</Pill>))}
        {C.M.salary_day > 0 && <Pill on={C.RANGE === 'S'} onClick={() => C.setR('S')}
          title="your salary cycle, not the calendar month">cycle</Pill>}
        <Pill on={C.RANGE === 'C'} onClick={() => C.setR('C')} title="pick months or exact dates">custom</Pill>
      </div>
      {C.RANGE === 'C' && <MonthPicker />}
      <NetRow />
    </div>);
}

/** the account and period chips a screen is filtered by; the period chip opens the panel */
export function FilterChips() {
  return (<>
    <div className="chips">
      <NBtn onClick={() => C.go('accounts')}>{C.M.account || 'account'}</NBtn>
      <NBtn onClick={() => C.togglePeriod()} aria-expanded={C.PERIODOPEN}>{C.periodText()}</NBtn>
    </div>
    {C.PERIODOPEN && <PeriodPanel />}
  </>);
}
