// Past trends: one column per month with a dotted AVG line. Built from the whole history, not the
// selected period: the chart IS the month selector, so filtering it by its own selection is circular.
// Opens at the newest month, with columns sized so a whole number fill the width.
import React, { useLayoutEffect, useRef } from 'react';
import * as C from '../core.js';

export function MonthChart({ rows, pick, color }) {
  const wrap = useRef(null);
  const by = C.byMonth(rows, pick), keys = Object.keys(by).sort();
  useLayoutEffect(() => {
    const cw = wrap.current; if (!cw) return;
    const w = cw.getBoundingClientRect().width; if (!w) return;
    const colw = w / Math.max(1, Math.floor(w / 58));
    cw.style.setProperty('--colw', colw + 'px');
    // by column count, not scrollWidth: the newest bar's value tag overhangs the last column
    cw.scrollLeft = keys.length * colw - w;
  });
  if (keys.length < 2) return null;
  const vals = keys.map((k) => by[k]), peak = Math.max(...vals, 1), avg = Math.round(vals.reduce((s, v) => s + v, 0) / vals.length);
  const avgPct = Math.max(0, Math.min(100, avg / peak * 100));
  return (
    <div className="chartwrap" ref={wrap} style={{ '--hl': color }}>
      <div className="chart">
        <span className="avgzone"><span className="avgline" style={{ bottom: `${avgPct}%` }} />
          <span className="avgpill num" style={{ bottom: `${avgPct}%` }}>AVG {C.fmtK(avg)}</span></span>
        {keys.map((k, i) => {
          const h = Math.max(1.5, Math.max(0, by[k]) / peak * 100), last = i === keys.length - 1;
          const on = C.RANGE === 'C' && C.CF === C.monthStart(k) && C.CT === C.monthEnd(k);
          return (
            <button key={k} className={`bcol ${on ? 'sel' : ''}`} onClick={() => C.openMonth(k)} aria-label={`${k} · ${C.fmt(by[k])}, show this month`}>
              <span className="bwrap"><i className={last || on ? 'on' : ''} style={{ height: `${h}%` }}>
                {last && <span className="bcall num" style={{ bottom: `${h}%` }}>{C.fmtK(by[k])}</span>}</i></span>
              <span className="blab">{C.MON[+k.slice(5) - 1].toUpperCase()}</span><span className="bval num">{C.fmtK(by[k])}</span>
            </button>);
        })}
      </div>
    </div>);
}
