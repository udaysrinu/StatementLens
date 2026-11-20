// Small shared pieces: icons, money, NeoPOP-themed text. Everything colour-related reads the same CSS
// tokens as before (tokens.css), so light/dark stay one system.
import React from 'react';
import { Button } from '@cred/neopop-web/lib/components';
import { IC } from './icons.js';
import * as C from './core.js';

export const Icon = ({ n, size = 20, style }) => (
  <svg viewBox="0 0 24 24" width={size} height={size} fill="none" stroke="currentColor" strokeWidth="1.6"
    strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" style={style}
    dangerouslySetInnerHTML={{ __html: IC[n] || IC.dot }} />
);

/** ₹ rupees at full weight, paise recessive: the same figure as fmt(), split for typography only. */
export function Money({ p, sign, className = '' }) {
  const s = C.fmt(p, sign ? { sign: true } : undefined), i = s.lastIndexOf('.');
  return (<span className={`num fig ${className}`}>{i < 0 ? s : <>{s.slice(0, i)}<span className="ps">{s.slice(i)}</span></>}</span>);
}

/** Insight copy with every ₹ figure in bold (the old hl()). */
export function Highlighted({ text }) {
  const parts = String(text || '').split(/(₹[\d,]+(?:\.\d+)?(?:Cr|L|k|K)?)/g);
  return <>{parts.map((s, i) => (i % 2 ? <b key={i}>{s}</b> : s))}</>;
}

export const dark = () => C.isDark();

/** A NeoPOP button in the current theme.

 NeoPOP's colorMode names the BUTTON's colour, not the page's: on our light page its "secondary" is the
 solid ink button and "primary" the white one (dark theme: the reverse). So: actions default to
 'secondary' (ink, the owner's choice); a toggle is 'secondary' when ON and 'primary' when off, so the
 picked chip fills with ink, as in CRED Money; the lesser action of a pair (Skip, Previous) is 'primary'. */
export function NBtn({ children, variant = 'secondary', size = 'small', kind = 'elevated', onClick, disabled, fullWidth, ...rest }) {
  return (
    <Button variant={variant} kind={kind} size={size} colorMode={dark() ? 'dark' : 'light'}
      onClick={onClick} disabled={disabled} fullWidth={fullWidth} {...rest}>{children}</Button>
  );
}

/** Back control at the top of a drilled-in screen. */
export const Back = ({ label = 'back' }) => (
  <button className="back" onClick={() => C.backFromDetail()} aria-label={`back to ${label}`}>
    <Icon n="back" size={22} /><span>{label}</span>
  </button>
);
