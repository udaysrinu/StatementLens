---
name: StatementLens
description: One honest picture of money in, money out and money invested, read from your own statements.
colors:
  page: "#e7e7e5"
  band: "#efefee"
  bg: "#ffffff"
  s2: "#f5f5f4"
  ink: "#0f0f0f"
  ink2: "#555555"
  ink3: "#6b6b6b"
  line: "#e7e7e7"
  line2: "#cfcfcf"
  edge: "#2b2b2b"
  sel: "rgba(15,15,15,.05)"
  np: "#0f0f0f"
  onnp: "#ffffff"
  npr: "#6f6f6f"
  npb: "#3b3b3b"
  up: "#077f47"
  down: "#c2352d"
  link: "#1f47d4"
  gold: "#8a5f0f"
  goldbg: "#fcf8ee"
  goldline: "#e8d6a4"
  ongold: "#ffffff"
  ray: "rgba(154,118,52,.22)"
  sunbg: "#f1ece3"
  inF: "#aac3f6"
  inL: "#7397ea"
  inS: "#0d2a8c"
  outF: "#e8b0f6"
  outL: "#c57de2"
  outS: "#3d1052"
  invF: "#f5ccb9"
  invL: "#df9d7f"
  invS: "#7c3518"
  page-dark: "#000000"
  band-dark: "#121212"
  bg-dark: "#0b0b0b"
  s2-dark: "#1d1d1d"
  ink-dark: "#f3f3f3"
  ink2-dark: "#bdbdbd"
  ink3-dark: "#959595"
  line-dark: "#262626"
  line2-dark: "#3d3d3d"
  edge-dark: "#2f2f2f"
  sel-dark: "rgba(255,255,255,.1)"
  np-dark: "#f3f3f3"
  onnp-dark: "#0b0b0b"
  npr-dark: "#9d9d9d"
  npb-dark: "#6a6a6a"
  up-dark: "#41d18f"
  down-dark: "#ff7a72"
  link-dark: "#98b5ff"
  gold-dark: "#e5c072"
  goldbg-dark: "#1c170b"
  goldline-dark: "#53431d"
  ongold-dark: "#1a1306"
  ray-dark: "rgba(229,192,114,.16)"
  sunbg-dark: "#17140e"
  inF-dark: "#5f86ea"
  inL-dark: "#a7bff7"
  inS-dark: "#2d50c6"
  outF-dark: "#c287de"
  outL-dark: "#e9c2f6"
  outS-dark: "#73348f"
  invF-dark: "#e3a083"
  invL-dark: "#f7d4c5"
  invS-dark: "#a1502c"
typography:
  hero:
    fontFamily: "Gloock, Georgia, 'Times New Roman', serif"
    fontSize: "2.75rem"
    fontWeight: 400
    lineHeight: 1.05
    fontFeature: "tnum"
  headline:
    fontFamily: "Gloock, Georgia, 'Times New Roman', serif"
    fontSize: "1.75rem"
    fontWeight: 400
    lineHeight: 1.12
    letterSpacing: "-0.015em"
  title:
    fontFamily: "Gloock, Georgia, 'Times New Roman', serif"
    fontSize: "1.5rem"
    fontWeight: 400
    lineHeight: 1.2
    letterSpacing: "-0.01em"
  body:
    fontFamily: "Figtree, -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif"
    fontSize: "0.9375rem"
    fontWeight: 400
    lineHeight: 1.5
  row:
    fontFamily: "Figtree, -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif"
    fontSize: "1.0625rem"
    fontWeight: 600
    lineHeight: 1.3
  figure:
    fontFamily: "Figtree, -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif"
    fontSize: "1.0625rem"
    fontWeight: 700
    lineHeight: 1.3
    fontFeature: "tnum"
  figure-large:
    fontFamily: "Figtree, -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif"
    fontSize: "3rem"
    fontWeight: 700
    lineHeight: 1
    fontFeature: "tnum"
  button:
    fontFamily: "Figtree, -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 600
    lineHeight: 1
  label:
    fontFamily: "Figtree, -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif"
    fontSize: "0.75rem"
    fontWeight: 600
    lineHeight: 1.3
    letterSpacing: "0.16em"
  label-pill:
    fontFamily: "Figtree, -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif"
    fontSize: "0.75rem"
    fontWeight: 700
    lineHeight: 1
    letterSpacing: "0.14em"
  tab:
    fontFamily: "Figtree, -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif"
    fontSize: "0.6875rem"
    fontWeight: 600
    lineHeight: 1
    letterSpacing: "0.12em"
rounded:
  none: "0px"
  selection: "12px"
  sheet: "18px"
  panel: "20px"
  pill: "999px"
  disc: "50%"
spacing:
  extrude: "4px"
  tight: "8px"
  gap: "12px"
  row-dense: "14px"
  row: "18px"
  gutter: "20px"
  row-open: "22px"
  pane-gap: "24px"
  section: "28px"
  pane-x: "40px"
components:
  button-primary:
    backgroundColor: "{colors.np}"
    textColor: "{colors.onnp}"
    rounded: "{rounded.none}"
    padding: "0 28px"
    height: "52px"
    typography: "{typography.button}"
  button-primary-disabled:
    backgroundColor: "{colors.line2}"
    textColor: "{colors.ink3}"
    rounded: "{rounded.none}"
  button-ghost:
    backgroundColor: "{colors.bg}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "0 28px"
    height: "52px"
    typography: "{typography.button}"
  pill:
    backgroundColor: "{colors.bg}"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
    padding: "0 16px"
    height: "44px"
    typography: "{typography.label-pill}"
  pill-gold:
    backgroundColor: "{colors.goldbg}"
    textColor: "{colors.gold}"
    rounded: "{rounded.pill}"
  pill-account:
    backgroundColor: "{colors.bg}"
    textColor: "{colors.link}"
    rounded: "{rounded.pill}"
  period-chip-selected:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.bg}"
    rounded: "{rounded.pill}"
    height: "36px"
  balance-pill:
    backgroundColor: "{colors.bg}"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
    padding: "0 16px 0 18px"
    height: "42px"
  tag-chip:
    backgroundColor: "{colors.bg}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "0 22px"
    height: "60px"
  tag-chip-selected:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.bg}"
    rounded: "{rounded.none}"
  tab:
    textColor: "{colors.ink2}"
    height: "72px"
    typography: "{typography.tab}"
  tab-active:
    textColor: "{colors.ink}"
  input-search:
    backgroundColor: "{colors.bg}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "0 18px"
    height: "56px"
  row-transaction:
    padding: "14px 0"
    typography: "{typography.row}"
  note:
    backgroundColor: "{colors.s2}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "18px 20px"
  note-gold:
    backgroundColor: "{colors.goldbg}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "18px 20px"
  bank-disc:
    backgroundColor: "{colors.bg}"
    rounded: "{rounded.disc}"
    size: "56px"
  sheet:
    backgroundColor: "{colors.bg}"
    rounded: "{rounded.sheet}"
    padding: "24px 20px 48px"
  toast:
    backgroundColor: "{colors.np}"
    textColor: "{colors.onnp}"
    rounded: "{rounded.none}"
    padding: "14px 18px"
---

# Design System: StatementLens

## Overview

**Creative North Star: "The Reconciling Sheet"**

StatementLens is a calm white sheet of large serif figures, tracked caps and dashed hairlines, laid over a cool grey band that holds identity and navigation. It follows CRED Money's structure and feel, which the owner pinned as the binding reference, rebuilt from scratch: Gloock and Figtree stand in for CRED's commercial faces, and the buttons follow CRED's open-source NeoPOP system (Apache-2.0). No CRED logo, mark or proprietary asset appears. Every total on the sheet is a door. Tap it and you land on the rows behind it. The visual system exists so that two numbers on screen never seem to disagree: the same figure is set the same way wherever it appears, and breakdowns visibly add up to their headline.

The surface is quiet so that a few physical materials can carry the character. Primary buttons are NeoPOP slabs: a flat face on a solid 3D edge that sinks into the edge when pressed. The three money flows are extruded bars printed with a banknote weave. The spend breakdown is a ring standing on a darker, ribbed coin edge. Account pages open under a gold sunburst. Depth is always a solid, blur-free edge, never a soft shadow. Colour is rationed: near-black ink does selection and action, and three flow hues (cobalt incoming, plum spends, peach investments) appear only where that flow is drawn.

It refuses the dashboard-of-cards default: no KPI tiles, no charts in boxes, no left rail of icons. Density is relaxed, at phone scale: 56px icon discs, rows padded 14–22px, a 28px gap between blocks. Motion is spent once. The cash-flow bars grow out of their baseline when the tab opens. Nothing fades in and no figure counts up.

**Key Characteristics:**
- Grey header band over a white sheet with 18px top corners; on desktop, a 448px list column beside a detail pane.
- Gloock for headings and the hero figure, Figtree for everything else. Labels are tracked uppercase Figtree.
- Paise stay on every exact figure but recede, through a solid colour mix rather than opacity.
- Dashed hairlines separate rows. Solid lines are reserved for structure and chart baselines.
- NeoPOP press, extruded banknote bars, a ribbed 3D donut, a gold sunburst. Depth is always solid.
- Light (CRED's palette) is the default. Dark is the same structure on near-black, toggled from the band.

## Colors

The palette is monochrome ink on white and grey, plus three flow hues used only for their flows and a gold the app reserves for speaking up.

### Primary
- **NeoPOP Ink** (light #0f0f0f, dark #f3f3f3; `--ink`, `--np`): text, the NeoPOP button face, every selected state (period chip, tag chip, split chip, month cell), the active tab underline, the chart baseline and the outline of callouts. On the dark theme it inverts to near-white and the button text goes near-black (`--onnp`).
- **NeoPOP Edge Faces** (`--npr` right face #6f6f6f, `--npb` bottom face #3b3b3b; dark #9d9d9d / #6a6a6a): the two skewed side faces of a NeoPOP slab. The right face is lighter than the bottom face.

### Secondary: the three flows
Each flow has a **Face** (the bar's front, `F`), a **Line** (the banknote weave printed on the face, `L`) and a **Side** (the extruded side face, the bar's 1px border, and the month-chart highlight, `S`).
- **Incoming Cobalt** (face #aac3f6, line #7397ea, side #0d2a8c; dark #5f86ea / #a7bff7 / #2d50c6): money that came in.
- **Spends Plum** (face #e8b0f6, line #c57de2, side #3d1052; dark #c287de / #e9c2f6 / #73348f): money that went out.
- **Investments Peach** (face #f5ccb9, line #df9d7f, side #7c3518; dark #e3a083 / #f7d4c5 / #a1502c): money put away.

The donut and its legend swatches are one flow hue stepped by rank. On light, the ramp starts at the flow's Side colour for the largest share and walks 92% of the way to a pale tint. On dark it runs pale-first and stops at a mid tone, so the largest slice is never the one lost in the background. The ramp is computed in script, which is why switching theme triggers a redraw.

### Tertiary
- **Ledger Gold** (light #8a5f0f on cream #fcf8ee with a #e8d6a4 rule; dark #e5c072 on #1c170b with #53431d): the app's own voice. It marks the salary-cycle note and its star, the period pill on Cash Flow, cautions on loan and deposit rows, the dot before each account's count, the privacy lock when it is on (`--ongold` text), and the sunburst's rays (`--ray`) and rim.

### Signals
- **Ledger Green** (`--up` #077f47, dark #41d18f): incoming amounts (with a leading +), favourable deltas, and the averages you compare against: the dotted AVG line and its pill, the "avg per month" and "6 months total" captions.
- **Debit Red** (`--down` #c2352d, dark #ff7a72): unfavourable deltas, stale-sync text, bill warnings, the clear-split action.
- **Account Blue** (`--link` #1f47d4, dark #98b5ff): account-scoped markers, such as the "as of" stamp on account rows and the account pill on Cash Flow.

### Neutral
- **Sheet White** (`--bg` #ffffff, dark #0b0b0b): the sheet, the desktop pane, and the fill of every pill, input and disc.
- **Cool Band Grey** (`--band` #efefee, dark #121212): the header band and the phone frame behind the sheet. It doubles as the PWA theme colour.
- **Desk Grey** (`--page` #e7e7e5, dark #000000): the backdrop around the two desktop panels.
- **Wash** (`--s2` #f5f5f4, dark #1d1d1d): neutral note fill, resting month bars, merchant-bar tracks, the area under the balance line.
- **Ink 2** (`--ink2` #555555, dark #bdbdbd): secondary text, inactive tabs, chevrons, bar value labels.
- **Ink 3** (`--ink3` #6b6b6b, dark #959595): caps labels, subtitles, row metadata, placeholders. It was darkened from #767676 to clear 4.5:1 on the band.
- **Hairline** (`--line` #e7e7e7, dark #262626): solid structural rules (filter bar, chart gridlines, icon-disc rings). **Hairline 2** (`--line2` #cfcfcf, dark #3d3d3d): dashed row separators, control borders, the drop under pills and the recurring card.
- **Disc Edge** (`--edge` #2b2b2b, dark #2f2f2f): the ring and solid drop under bank discs, and the donut's rim.
- **Selection Wash** (`--sel`): the current list row on desktop and hover on the band's icon button.
- **Sun Ground** (`--sunbg` #f1ece3, dark #17140e): the field behind the account sunburst.

### Named Rules
**The Flow Hue Rule.** Cobalt is incoming, plum is spends, peach is investments, everywhere a flow is drawn: bar, donut ramp, legend swatch, month-chart highlight. A flow hue never decorates anything that is not that flow. Charts with no single flow (a tag's or merchant's history) highlight in ink.

**The Ink Selects Rule.** A selected or primary thing is ink-on-sheet inverted: near-black fill with white text in light, the reverse in dark. Selection is never a hue.

**The Gold Speaks Rule.** Gold means the app noticed something or a mode is on, such as a detected salary cycle, a caution, or privacy. It is never used for ordinary emphasis.

**The Measured Ink Rule.** Every text colour is checked against the darkest surface it sits on in its theme, and has to clear 4.5:1 there. A failing token gets darkened. It is not tolerated.

## Typography

**Display Font:** Gloock (with Georgia, 'Times New Roman', serif)
**Body Font:** Figtree (with -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif)

**Character:** Gloock is a high-contrast serif that makes a single large figure feel like a printed statement. Figtree is a plain, friendly grotesque that carries everything you read or tap. Both are OFL and inlined into the page as woff2 in `latin` and `latin-ext` subsets. The rupee sign (U+20B9) lives in `latin-ext`, so both subsets ship and no font is fetched.

### Hierarchy
- **Hero** (Gloock 400, 2.75rem, 1.05, tabular): the figure a screen exists to show, such as a flow's total, an account's balance, or a tag's total. It is centred under its caps label on breakdowns and accounts. The band's total balance on Accounts uses the same face at 1.625rem.
- **Headline** (Gloock 400, 1.75rem, 1.12, −0.015em, balanced wrap): the tab's screen title ("your cash flow"). A transaction's merchant name uses the same size.
- **Title** (Gloock 400, 1.5rem, 1.2, −0.01em): sub-screen titles, the empty-pane prompt, the card-summary figure.
- **Body** (Figtree 400, 0.9375rem, 1.5): prose, notes, subtitles (`--ink3`). Notes are set at 1rem.
- **Row** (Figtree 600, 1.0625rem, 1.3): row names, single-line with ellipsis. Metadata below sits at 0.9375rem in `--ink3`.
- **Figure** (Figtree 700, 1.0625rem, 1.3, tabular): row amounts, grid amounts, legend amounts. **Figure Large** (Figtree 700, 3rem, 1) is a single transaction's amount. The recurring card uses 2.25rem.
- **Label** (Figtree 600, 0.75rem, 0.16em, uppercase, `--ink3`): section headings, figure labels, day headers, key/value keys. Pills use the 700-weight variant at 0.14em. Tabs use 0.6875rem at 0.12em.
- **Button** (Figtree 600, 1rem, 1): NeoPOP labels, in sentence case.

### Named Rules
**The One Serif Figure Rule.** Gloock sets headings and the hero figure that headlines a screen. Every other amount, however large, is Figtree 700 with tabular figures.

**The Recessive Paise Rule.** Every exact figure keeps its paise, but they are set in `color-mix(in oklab, currentColor 35%, var(--ink3))`. This is a solid colour, never opacity. Both ends of the mix clear 4.5:1 in both themes, so a green or red figure keeps its hue and its paise stay legible. The change is typographic only. Figures are never rounded.

**The Exact-or-Compact Rule.** Wherever a figure belongs to a sum that has to reconcile (hero, row, legend line, balance pill), it is exact, with Indian grouping and recessive paise (an illustrative ₹1,23,456.78). Compact two-decimal figures (₹12.40K, ₹3.20L, ₹1.05Cr) appear only on chart labels, averages and prose notes. A figure shown in two places is the same figure in the same form.

**The Caps Name Things Rule.** Tracked caps name a figure or a section. They never sit over a heading that already says the same thing. Screen headings and copy are written lowercase ("all transactions"). Only button labels start with a capital ("View all", "Confirm").

## Layout

**Phone (default):** one column, centred, up to 480px wide. The band has a 20px gutter and safe-area top padding. It holds the theme button, the balance pill and the lock on one row, then four equal tabs. The sheet (`--bg`) follows, with 18px top corners and 24px/20px padding plus safe-area at the bottom. Inside the sheet, blocks stack with a 28px gap. Filter bars, the dashed divider on transaction detail, and the account sunburst bleed to the sheet's edges (−20px). Below 360px the tabs size to their labels, the pill drops its caption, and the band total shrinks to 1.25rem.

**Desktop (1100px and up):** the frame widens to 1360px with 24px padding and a 24px gap on the Desk Grey backdrop. On the left is a 448px column, sticky at 24px and scrolling on its own, with 20px corners, holding the band and the list. On the right is the detail pane: Sheet White, 20px corners, 28px/40px/56px padding, content capped at 720px. Whatever the pane is showing gets marked in the list by a Selection Wash at 12px radius, extended 12px either side. The pane's Back button appears only once you have drilled past its first screen. (The direction contract said 440px. The build ships 448px, and that is the recorded value.)

**Rhythm:** rows use 14px (transactions), 18px (legend lines) or 22px (accounts, flows, positions) of vertical padding, separated by dashed hairlines. Every control is at least 44px tall. NeoPOP buttons are 52px, the transaction action bar's buttons 60px, tag chips 60px.

**Charts:** the cash-flow chart is 300px tall. Three equal columns sit 12px apart over four 1px gridlines and a 1.5px ink baseline. The monthly trend scrolls horizontally, opens at the newest month, and resizes its columns (at least 62px) so that a whole number of them fills the width.

### Named Rules
**The Sheet Over Band Rule.** Identity and navigation live on the band. Content lives on the sheet. A chart, the donut or a hero figure sits directly on the sheet, never inside a box of its own.

**The Dashed Row Rule.** Rows within a list are split by 1px dashed `--line2`. Solid rules mark structure only: the filter bar, chart baselines, gridlines.

## Elevation & Depth

Depth is extrusion. Surfaces are flat at rest, and anything raised stands on a solid, blur-free edge in a darker tone of its face. The NeoPOP button and the cash-flow bars build that edge out of skewed pseudo-element faces. Pills, discs and the recurring card drop a solid band straight down. No element in the system casts a blurred shadow. The only blur is privacy mode, which blurs every figure by 8px and leaves everything else readable.

### Shadow Vocabulary
- **NeoPOP edge** (right face `--npr`, `skewY(45deg)`; bottom face `--npb`, `skewX(45deg)`; depth 4px): primary and ghost buttons. On press the face translates 4px down-right and both faces hide (0.12s).
- **Bar side face** (`--{flow}S`, 12px wide, `skewY(45deg)`): the extruded right side of each cash-flow bar.
- **Pill drop** (`box-shadow: 0 3px 0 var(--line2)`): the balance pill.
- **Disc drop** (`box-shadow: 0 4px 0 var(--edge)` with a 1.5px `--edge` ring): bank discs.
- **Card drop** (`box-shadow: 0 6px 0 var(--line2)` with a 1.5px ink border): the recurring card and the three ghost cards fanned behind it.
- **Inset rings** (`inset 0 0 0 2px var(--ink)` ghost button; `inset 0 0 0 1px var(--ink)` selected pill): outline emphasis without changing size.
- **Coin edge** (a second copy of the donut 14px lower, at `brightness(.42) saturate(1.2)`, ribbed with a repeating conic of white at 18% alpha, 0.45° in every 2.4°): the donut's side.

### Named Rules
**The Solid Edge Rule.** If it is raised, it stands on a solid edge. The edge is a darker face, offset down or down-right, with zero blur.

**The Press Rule.** A NeoPOP slab sinks by exactly its edge depth and its edges vanish. The press is the only feedback a primary button gives.

## Shapes

Rectangles you act on or read as one unit have sharp corners (0px). That covers NeoPOP buttons, tag chips and the tag box, notes, inputs, bills, key/value blocks, month cells, the trend callout and the toast. Choices and readouts are full pills (999px): sort, filter, period and direction pills, the period segment track, year and netting chips, the search pill, the AVG marker and the balance pill. Identity is a circle: bank discs, category icon discs (56px, 1px `--line` ring, with a 22px bank-hue badge at the lower right), and avatars in the top-spends grid. Beyond the tab underline's 2px ends, rounded rectangles appear only on the sheet's top corners (18px), the desktop column and pane (20px), and the desktop selection wash (12px).

Pointers are squares rotated 45° with two borders drawn. The gold note's tip (16px, positioned per note with `--tip`) and the trend callout's tail (9px) are both built this way. Legend swatches are 14px squares with a 25%-black hairline.

**The Two Conics.** Repeating conic gradients appear twice, both as the world's own materials (a coin's milled edge, a sunburst) and nowhere else. One is the ribbing on the donut's coin edge. The other is the account sunburst: gold rays 0.6° wide every 6°, fanning from the bottom centre over Sun Ground, behind a 220px sheet-white circle with a 1.5px gold rim that holds the 96px bank disc.

## Components

### Buttons
Tactile, heavy and few. The primary action on a screen is a NeoPOP slab.
- **Shape:** sharp (0px), 52px tall, 28px side padding, a 12px icon gap, Figtree 600 1rem. It reserves 4px right and bottom margin for its edge.
- **Primary:** ink face (`--np`) with white text (`--onnp`), on the NeoPOP edge described above.
- **Ghost:** a sheet-coloured face with a 2px inset ink ring and ink edges. It is used for the secondary choice in a pair (Skip / Confirm, Previous / Next) and for "View all".
- **Press / Focus:** the press sinks the face 4px and hides the edges, over 0.12s on `cubic-bezier(.2,.7,.3,1)`. Focus is the global 2px ink outline at a 2px offset. There is no hover state.
- **Disabled:** a `--line2` face with `--ink3` text and no edges.
- **Text actions:** "View all" and "See all transactions" links, the actions on notes, and "refresh" are underlined ink text (1.5px, 4–6px offset), at least 44px tall.

### Chips and Pills
- **Pills** (sort, filter, direction): 44px, full radius, a 1px `--line2` border on the sheet, 700 0.75rem tracked caps. On hover the border darkens to `--ink3`. When selected they gain a 1px inset ink ring and an ink border. Variants: account blue text, and gold (cream fill, gold rule, gold text) for the period on Cash Flow.
- **Period segment:** a full-radius track with a 1px `--line2` border and 4px padding, holding 36px pills. The selected pill is filled ink. A custom-range pill sits beside the track, and month cells in the picker are sharp 44px cells. A month with no statements is shown struck through at half strength, never hidden.
- **Tag chips:** sharp, 60px, a 1.5px `--line2` border, an icon, then 700 0.8125rem caps at 0.2em. The selected chip is filled ink.
- **Account chips:** 52px pills, each holding a 36px bank disc and the account's name in caps. The current account gets a 2px ink border.

### Rows
- **Transaction row:** a 56px icon disc with a bank-hue badge, then the name (Row) with metadata below, then the amount (Figure, green with + if incoming) above a date, then a 16px chevron. Hovering underlines the name. Rows sit under sticky day headers in caps.
- **Legend row:** a 14px swatch, the name (500 1.0625rem) above its share (700, `--ink3`, two decimals), then the exact amount and a chevron. An aggregated "Other (N sources)" line is static and has no chevron.
- **Flow row:** the flow's name at 1.25rem, then the exact amount and a chevron, above a green "6 months total" caption.

### Inputs / Fields
- **Style:** sharp, 1.5px `--line2` border, sheet fill, ink text, `--ink3` placeholder. The search field is 56px tall, the tag search 60px with a 26px icon, the date and amount fields 44px with tabular figures.
- **Focus:** the border turns ink. Fields replace the outline with that border change. Every other control keeps the 2px ink focus outline.

### Navigation
- **Tabs:** four equal columns on the band, each a 30px outline icon (1.35 stroke) over an 11px caps label. Inactive tabs show the icon at 50% opacity and the label in `--ink2`, rising to 80% on hover. The active tab shows the icon at full strength, an ink label, and a 24×3px ink underline with 2px corners.
- **Band controls:** the theme button is a 44px square with a 1px `--line2` outline. The privacy lock is a 44px ink square that turns gold when on. On Accounts the balance pill gives way to the band total in Gloock, since the sheet's hero would only repeat it.
- **Back:** a 44×24px long-arrow icon followed by the destination in caps. The arrow nudges 3px left on hover.

### Cards and Notes
- **Notes:** sharp, 1.5px `--line2` border, Wash fill, a 26px icon, 1rem text. Compact figures inside are bolded. The gold variant (cream, gold rule, a pointer tip) is reserved for detected suggestions such as the salary cycle.
- **Recurring deck:** a single sharp card (1.5px ink border, 6px solid drop) over three ghost cards rotated −4°, 3° and −1.5°. It shows a 76px icon disc, the median in Figtree 700 2.25rem, the merchant in caps, and dashed key/value lines. Below it sit a "1 out of N" counter and a Previous / Next NeoPOP pair.
- **Key/value block:** a two-column grid inside a 1.5px gold rule (`--goldline`), with caps keys over 1rem values.

### Cash-Flow Bars (signature)
Three extruded bars on one scale: incoming, investments, spends. Each bar is the button that opens its breakdown. A bar is 56% of its column (at most 84px) and at least 6px tall, with a 1px border in the flow's Side colour and a 12px skewed side face. Its face is printed with a banknote weave: an SVG pattern on a 5px tile rotated −38°, a wavy 0.7-stroke path in the flow's Line colour. A compact value (600 0.8125rem, `--ink2`) sits above each bar, and tracked caps labels sit below the baseline. **The one motion moment:** opening the tab grows each bar from `scaleY(0)` over 0.7s on `cubic-bezier(.16,1,.3,1)`, staggered 0.07s. A value change on the same screen does not replay it, and under reduced motion it never plays.

### 3D Donut (signature)
A 260px ring (the mask goes transparent to opaque at 56%/56.6%) built from the flow's ranked ramp as a conic gradient. A thin rim (1.5px white over a 2.5px `--edge` line) runs around its outer edge. It stands on the coin edge (see Elevation). It is decorative (`aria-hidden`); the legend rows below it carry the data and sum to the hero.

### Monthly Trend
Columns are divided by dashed `--line2` lines. Bars are 52% width in Wash, and the newest or selected month is filled with the flow's Side colour (ink for tags and merchants). Each column carries a caps month label and a compact value. The newest bar wears a sharp ink-bordered callout with a tail. A dotted green AVG line runs across the chart, with a green outlined pill. Tapping a bar selects that month.

### Bank Disc
A 56px circle on the sheet colour with a 1.5px `--edge` ring and a 4px solid drop. It holds a monogram of up to four letters (800 0.75rem) in the bank's brand hue. In dark mode that hue is mixed 45% toward white so it stays readable. No bank logos are used: the colour is the recognisable part. A bank without a known hue gets one derived from its name.

### Toast
An ink slab with no radius, centred 28px from the bottom, at most 420px wide, 0.9375rem text. It rises 16px and fades in over 0.25s.

## Do's and Don'ts

### Do:
- **Do** put a screen's one answer in a Gloock hero (2.75rem) under a tracked caps label, and make it tappable through to its rows.
- **Do** make every breakdown visibly sum to its headline. Use exact figures with recessive paise for anything that reconciles, and compact K/L/Cr only on chart labels, averages and notes.
- **Do** give primary actions the NeoPOP press: an ink face, a 4px solid edge, and a sink of exactly that depth.
- **Do** draw a flow only in its hue triplet (Face, Line, Side), and print the banknote weave on any extruded flow bar.
- **Do** separate list rows with 1px dashed `--line2`, and keep every control at least 44px tall.
- **Do** check each new text colour against the darkest surface it sits on in both themes, and darken it until it clears 4.5:1.
- **Do** inline fonts (both `latin` and `latin-ext`, for ₹), icons and patterns. The page fetches nothing.
- **Do** draw new icons in the app's own outline family: 24px grid, 1.6 stroke, round caps and joins, inline SVG.

### Don't:
- **Don't** build KPI tiles, boxed charts, or a left rail of icons.
- **Don't** fade paise or any figure with opacity. Mix colours toward `--ink3` instead.
- **Don't** use a blurred `box-shadow`. Depth is a solid edge.
- **Don't** use a flow hue for decoration, or a hue of any kind for selection.
- **Don't** add entrance fades, count-up figures, or a second motion moment beyond the cash-flow bars' growth.
- **Don't** use repeating conic ribbing or rays outside the donut's edge and the account sunburst.
- **Don't** round a rectangle you act on. Corners are 0px, pills are full, identity is a circle.
- **Don't** use CRED's logos, marks, proprietary faces or assets, or any bank's logo.
