# Design principles — StatementLens (and the ExpensifyAI money views)

Distilled from CRED-Money research (75 findings / 54 sources) + the frontend-design method.
The rule that governs all others: **intentionality, not intensity.** Every screen answers ONE question.

## The ten

1. **One monumental number, not a chart.** The hero is a single 46–56px display figure that answers
   "how am I doing?" in under 5 seconds. A chart only earns its place if it answers something the
   number can't.
2. **Insight-first, data-second.** The product's job is to surface the ONE thing you'd miss (a
   duplicate charge, a fee, an upcoming debit). Passive stats sit *below* insights.
3. **Progressive disclosure via depth, not density.** Home shows top-3/4 summaries; everything else
   is one tap away. Never dump the 500-row ledger or every category on the first screen.
4. **Restraint in colour: monochrome surfaces + exactly ONE accent.** Green is reserved for
   money-in/positive; red only for genuine alerts. No per-category rainbow.
5. **Pick at most TWO of {fills, dividers, strokes, shadows}.** Lists use hairline dividers, not
   nested bordered cards. Three nested surface layers = "busy dashboard."
6. **Priority is encoded in contrast, not layout.** The one urgent action gets the filled accent
   button; everything routine recedes to muted text. Don't add a section to signal importance.
7. **Zero manual work.** Auto-categorize into a flat ~12–15 set (no subcategories). Simplicity of
   the taxonomy is itself a feature.
8. **Calm, confident, second-person copy.** "you were charged ₹590 in fees last month." Never
   "ALERT!! save now 🔥". Tone = anxiety reduction. No dead-end empty states ("you're all caught up").
9. **Honest numbers only.** Show gross money-in vs money-out; never invent a "money left" figure —
   the real leftover is your balance.
10. **One easing curve, tabular numerals, a tight type scale.** Reuse `cubic-bezier(.2,.7,.3,1)`
    everywhere; `font-variant-numeric:tabular-nums` on every money value; a distinctive display
    serif for the hero + one clean sans for body. Too many font sizes is the un-designed tell.

## Applying them (per surface)

| Surface | Principle in action |
|---|---|
| Hero | #1 #9 — one big spent/balance number + one quiet delta line, no chart |
| Insights | #2 #8 — 2–4 ranked cards, number bolded in accent, calm copy |
| Cash flow | #9 #4 — two honest numbers + one comparative bar, green=in |
| Categories | #3 #4 #5 — top-5 single-hue bars, "see all" behind a tap, dividers |
| Recurring | #6 — most-urgent gets filled CTA, rest muted |
| Transactions | #3 — top few on home; full searchable list behind "view all" |
| Global | #5 #10 — dividers over nested cards, one accent, one curve, tabular nums |

## The frontend-design overlay

- Distinctive type (Fraunces / Bricolage display + Instrument Sans / Hanken body — never Inter/Roboto).
- Atmosphere via a single subtle radial glow behind the hero — nothing more.
- One orchestrated load (staggered rise-in), not scattered micro-animations. Respect
  `prefers-reduced-motion`.
- Commit fully to ONE aesthetic; mixing themes reads as AI slop.
