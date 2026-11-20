---
version: 1
slug: "src-statementlens-adapters-render-app-shell-py"
primary_target: "src/statementlens/adapters/render/app_shell.py"
related_targets: []
---

# Surface: StatementLens dashboard (app shell)

Mode: Operate. Audience: the owner and cold self-hosters (PRODUCT.md). Job: answer "how am I doing,
where did it go, what did I miss" across accounts, then fix a tag or a split in one tap.
Constraints: one HTML/CSS/JS document from Python; integer paise; browser totals must equal the
server's; public repo, synthetic screenshots only. Answers: CRED Money's 4 tabs; desktop = list + detail.

## Direction contract

THESIS: A money app that feels like CRED Money: a calm white sheet of large serif figures, tracked
caps and hairlines, where every total opens into the rows behind it. Refuses the dashboard-of-cards
default (KPI tiles, charts in boxes, a left nav of icons).

OWN-WORLD: White sheet over a cool grey header band; ink near-black, two greys, dashed hairlines. Gloock
serif for headings and hero figures, Figtree for everything else; labels in caps tracked wide; paise
recessive. Flow hues: incoming cobalt, spends plum, investments peach, each a textured face with a darker
side face. NeoPOP elevated black buttons; sharp-cornered tags and outlined buttons; full pills for sort.

STORY: The visitor reads the balance, picks a tab, sees one honest figure, taps it, and lands on the
rows behind it; corrects a tag; never wonders whether two numbers on screen disagree.

FIRST VIEWPORT: Phone: header band with close/theme, a balance pill, four icon tabs with an underline;
under it the white sheet with the tab's serif heading and its primary figure. Desktop: the same column
fixed at 440px on the left, the drilled screen in a wider pane on the right.

FORM: CRED Money's own structure and look, pinned by the user. seed: none (pinned) — "get the
screenshots for it and then build exactly the same, cause i like the features and feel of the app".
Signature move: the NeoPOP press (buttons sink into their 3D edge) and the extruded, textured cash-flow
bars and 3D donut.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
