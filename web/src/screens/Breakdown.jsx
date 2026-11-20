// One flow broken down (CRED's spends / incoming screen): the headline figure, the ribbed 3D donut and
// a legend that sums to it, who you pay, and the month-by-month history. Every legend line opens its rows.
import React from 'react';
import * as C from '../core.js';
import { Icon, Money, NBtn, Back } from '../ui.jsx';
import { IconDisc } from './parts.jsx';
import { FilterChips, NetRow } from './period.jsx';
import { MonthChart } from './MonthChart.jsx';

const SIDE = { out: 'var(--outS)', in: 'var(--inS)', inv: 'var(--invS)' };
const PICK = { out: (t) => t.f === 's', in: (t) => t.f === 'i', inv: (t) => t.f === 'v' };

/* a drawn arrow in the app's icon family, not a text glyph */
const Arrow = ({ up }) => (
  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round"
    strokeLinejoin="round" aria-hidden="true" style={{ transform: up ? 'none' : 'rotate(180deg)', display: 'inline-block', verticalAlign: '-1px' }}>
    <path d="M12 19V5M5 12l7-7 7 7" /></svg>);

export function Donut({ rows, total }) {
  if (rows.length < 1 || total <= 0) return null;
  let acc = 0;
  const stops = rows.map((s, i) => {
    const from = acc / total * 100; acc += Math.max(0, s.a); const to = acc / total * 100;
    return `${C.tint(C.FLOW, i, rows.length)} ${from.toFixed(2)}% ${to.toFixed(2)}%`;
  }).join(',');
  const bg = { background: `conic-gradient(${stops})` };
  return (<div className="d3" aria-hidden="true"><div className="d3e" style={bg} /><div className="d3t" style={bg} /></div>);
}

/* `by` says what the keys ARE: income groups by source (a tag), investments by merchant */
function Legend({ rows, total, title, by }) {
  if (!rows.length) return <div className="empty">nothing in this period</div>;
  const open = by === 'merchant' ? C.openMerchant : C.openTag;
  return (<>
    <Donut rows={rows} total={total} />
    <section aria-label={title} className="rlist">{rows.map((s, i) => {
      const real = !/^Other \(\d+ sources\)$/.test(s.k);
      const body = (<>
        <span className="lsw" style={{ background: C.tint(C.FLOW, i, rows.length) }} />
        <span className="lm"><span className="ln">{s.k}</span><span className="lp">{(s.share * 100).toFixed(2)}%</span></span>
        <span className="la"><Money p={s.a} />{real && <Icon n="chev" size={16} style={{ color: 'var(--ink3)' }} />}</span></>);
      return real ? <button key={s.k} className="lrow" onClick={() => open(s.k)}>{body}</button> : <div key={s.k} className="lrow static">{body}</div>;
    })}</section>
  </>);
}

function TopSpends({ R }) {
  const top = R.mers.filter((m) => m.a > 0).slice(0, 6);
  if (top.length < 3) return null;
  return (<>
    <div className="st"><h2>top spends</h2></div>
    <div className="grid3">{top.map((m) => (
      <button key={m.name} className="gcell" onClick={() => C.openMerchant(m.name)}>
        <IconDisc icon={C.catIcon(C.rowCat(m.name))} />
        <span className="gamt"><Money p={m.a} /></span><span className="gnm">{m.name}</span>
      </button>))}</div>
    <div><NBtn size="medium" onClick={() => C.viewAllHigh()}>View all</NBtn></div>
  </>);
}

export function Breakdown() {
  const rows = C.rangeFilter(), R = C.compute(rows), hv = C.heroValue(R), d = C.heroDeltaData(R);
  const hist = C.byMonth(C.shareRows(C.netFilter(C.ALL)), PICK[C.FLOW]), hk = Object.keys(hist).sort();
  const hav = hk.length ? Math.round(hk.reduce((s, k) => s + hist[k], 0) / hk.length) : 0, latest = hk[hk.length - 1];
  const word = { out: 'spent', in: 'received', inv: 'invested' }[C.FLOW];
  return (
    <div className="view">
      <Back label="cash flow" />
      <FilterChips />
      <div className="heroc">
        <div className="cap">{hv.label}</div>
        <div className="hero"><Money p={hv.amount} /></div>
        {hv.avg > 0 && <div className="avg num">avg per month {C.fmtK(hv.avg)}</div>}
        {d && <div className="subd"><span className={d.good ? 'up' : 'down'}><Arrow up={d.up} /> {d.pc}%</span> vs previous {d.label} · <span className="num">{C.fmt(d.prev)}</span></div>}
      </div>
      <NetRow />
      {C.FLOW === 'inv' && R.invBack > 0 && (
        <div className="note bare"><Icon n="spark" /><div><Money p={R.invIn} /> went in · <Money p={R.invBack} /> came back from brokers · net <Money p={R.inv} /></div></div>)}
      {C.FLOW === 'in' && <Legend rows={R.srcs} total={R.inn} title="where it came from" by="tag" />}
      {C.FLOW === 'inv' && <Legend rows={R.invs} total={R.inv} title="what you put away" by="merchant" />}
      {C.FLOW === 'out' && <Legend rows={R.spends} total={R.out} title="where it went" by="tag" />}
      {C.FLOW === 'out' && <TopSpends R={R} />}
      {hk.length > 1 && <>
        <div><div className="cap">{hv.label} history</div>
          <div className="hero sm"><Money p={hav} /></div>
          <div className="sub">average amount {word} per month over the last {hk.length} months</div></div>
        <div className="tr"><span className="trl"><Icon n="bars" size={20} />past trends</span>
          <NBtn onClick={() => C.toggleTrend()}>{C.TREND === 'month' ? 'entire month' : 'till date'}</NBtn></div>
        <MonthChart rows={C.shareRows(C.netFilter(C.ALL))} pick={PICK[C.FLOW]} color={SIDE[C.FLOW]} />
        {latest && <div><NBtn size="medium" kind="elevated" onClick={() => C.viewMonthTxns(latest)}>View {C.MON[+latest.slice(5) - 1]} transactions</NBtn></div>}
      </>}
    </div>);
}
