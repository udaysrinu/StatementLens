# StatementLens — design system

**Source of truth: the shipped code**, specifically the `_PAGE` literal in
`src/statementlens/adapters/render/app_shell.py`. Not the Stitch project.

That direction matters and is not the usual convention, so here is the evidence. The Stitch project
(`8266188680731936574`, 11 screens) is a **stale snapshot**:

| | Stitch | Shipped |
|---|---|---|
| Screens | 6 unique | 9 (`home` `spends` `insights` `search` `recurring` `tagdetail` `txn` `netting` `bills`) |
| `--ink3` | `#94816d` | `#6b5a4a` |
| `--acc` | `#b5702a` | `#875017` |

Those two Stitch colours are not a style difference — they are the exact values a WCAG audit of the
live page measured at **3.05:1** and **3.80:1**, both under AA, and `--ink3` carries load-bearing text
(`spent · all time`, `avg per month`, every chart month label, every row subtitle). Regenerating this
document *from* Stitch would reintroduce them. Stitch is useful for exploring new screens; it is not
the record of what the product is.

Anything below that a Stitch prompt contradicts: the code wins.

---

## Platform

Mobile-first, single column, `max-width:460px`, centred. No build step: HTML + CSS + vanilla JS
emitted as one Python string, so the whole dashboard is a single self-contained file that opens
offline with the data embedded. **This is a distribution property, not an implementation detail** — it
is why `pipx`/`brew` install with no security warning and why nothing can leak to a network.

Do not introduce React, Tailwind, a component library, or any bundler. Suggestions that require
`npm install` are out of scope for this surface.

## Themes

Two, both audited against **every** surface. Light is the default.

`[data-theme=light]` — warm editorial. Parchment surfaces, espresso ink, one terracotta accent.

| Token | Value | Role |
|---|---|---|
| `--page` | `#e7dccb` | outside the app frame; the DARKEST light surface |
| `--bg` | `#efe7db` | app ground |
| `--s1` | `#faf8f2` | card surface |
| `--s2` | `#f2ede2` | raised / inside-pill |
| `--ink` | `#241a12` | primary text |
| `--ink2` | `#5f584c` | secondary |
| `--ink3` | `#6b5a4a` | tertiary — **load-bearing, not decoration** |
| `--acc` | `#875017` | accent + selected state |
| `--acc2` | `#6d3f11` | accent gradient end (avatar, toggle) |
| `--onacc` | `#fffaf2` | text on accent |
| `--up` / `--down` | `#2f6b34` / `#a83c28` | money in / money out |

Plus two non-colour tokens per theme: `--line` (hairline dividers) and `--glow` (an `r,g,b` triplet
for `rgba()` tints, kept unbracketed so it can be interpolated).

`:root` (dark) — Tickertape. Cool near-black ground, three tight surface steps, green as the primary
accent. `--acc` **equals** `--up` deliberately: on a finance screen green is the resting state of a
good number, so a selected filter and a positive figure sharing one green is what makes the palette
read as financial rather than as "an app that happens to be dark".

| Token | Value |
|---|---|
| `--page` `--bg` `--s1` `--s2` | `#080b10` `#0e1219` `#161b24` `#1f2632` |
| `--ink` `--ink2` `--ink3` | `#eaeff6` `#93a1b5` `#8593a7` |
| `--acc` `--acc2` `--onacc` | `#00c07f` `#009966` `#04120c` |
| `--up` `--down` | `#00c07f` `#f0616d` |

### Contrast rule (the one that keeps being got wrong)

**The worst-case surface inverts between themes.** Light's hardest case is its *darkest* ground
(`--page`), because darker text on a lighter field scores higher. Dark's hardest case is its
*lightest* surface (`--s2`). A palette tuned against `--s1` alone passes and still ships AA failures.

Check every token against all four surfaces, computed on the **rendered page**, not from the
declarations. Both themes are currently at zero real failures; `--ink3` in dark sits at 4.87:1 on
`--s2`, which is the tightest margin in the system.

## Typography

- Display: **Fraunces** (400/500/600) — hero figures, section headings, card values.
- Body: **Instrument Sans** (400–700) — everything else.
- Every money value carries `font-variant-numeric:tabular-nums`, so digits do not jitter as figures
  change.
- Hero is 50px/1 with `letter-spacing:-.02em`. Paise are dimmed via `.ps` (`opacity:.42`,
  `font-size:.62em`) — **typographic only, never rounding**: every figure still reconciles to the
  paisa against the statement.

## Motion

One easing curve everywhere: `cubic-bezier(.2,.7,.3,1)`. Honoured in both CSS
(`@media(prefers-reduced-motion:reduce)`) and the hero count-up JS. A `.nofx` class suppresses entry
animation when re-rendering the *same* screen, so changing one filter does not replay a full page fade.

## Touch targets

44px minimum, asserted by `test_interactive_controls_declare_a_touch_target`. Where a control sits in
a tight row, the hit area is grown with **negative margins** so the target reaches 44px while the row
keeps its height — raising a target must not push the hero down the page.

Two deliberate exemptions, encoded in that test: period chips are 36px inside a 4px-padded pill (a
44px row), and chart bars are 26px wide but 126px tall, since the rule is about reachability.

## Signature graphics

Borrowed from CRED Money, all pure CSS — no images, no libraries:

- **Guilloché** — three offset `repeating-linear-gradient`s at coprime angles interfering into the
  engraved lattice of a banknote. Applied inside the flow bars via `.guil`. Set the bar hue with
  `background-color`, never the `background` shorthand: the shorthand resets `background-image` and
  silently flattens the texture.
- **Three-way flow bars** — extruded, one hue per flow, darker right face. Incoming takes the accent
  green in dark mode.
- **Single-hue donut** — `conic-gradient` + a radial mask for the hole, stepped light-to-dark **by
  rank** so darkest reads as biggest. Never a rainbow. `FLOWHUE` is per-theme; a theme-independent
  table left the donut blue while its bar was green.
- **Sunburst** — `repeating-conic-gradient` behind the header, masked out by 78%, so it reads as
  watermarked stationery rather than decoration.

## Non-negotiables

These are each a real bug that shipped, not preferences.

1. **Anything styled `cursor:pointer` must have a handler.** Six dead clickables shipped because
   screenshots and computed-value checks both prove the *numbers* are right and neither can see a
   missing `onclick`. Pinned by `test_nothing_styled_clickable_is_actually_dead`.
2. **A handler is not enough — it must go somewhere real.** The investment breakdown called
   `openTag()` while its rows are keyed by *merchant*, so every click landed on an empty screen.
   Clickable-but-broken passes the test above.
3. **Never mutate a billed amount.** A split is an annotation; the statement says ₹3,000 and must keep
   saying ₹3,000 or the ledger stops reconciling line-by-line against the PDF.
4. **Any mode that shrinks a total must say so, in money, in the same place** — "−₹3.2L cancelled ·
   what?" — and link to an audit screen. Never silently smaller.
5. **Escape hatches out first, presets first.** Custom date range is last and visually demoted; a
   control that scrolls off-screen is a missing control.
6. **No emoji as icons.** SVG only, from the inline `I()` set.
7. **A status line that always complains becomes wallpaper.** A successful sync says nothing; only a
   run that imported *nothing* reports failure.

## Verifying a change

```bash
# 290 tests, no pytest dependency — the same loop packaging/release.sh runs
PYTHONPATH=src python3 - <<'PY'
import importlib, os, sys, traceback
bad = 0
for mod in (f[:-3] for f in sorted(os.listdir("tests"))
            if f.startswith("test_") and f.endswith(".py")):
    m = importlib.import_module("tests." + mod)
    for name in sorted(d for d in dir(m) if d.startswith("test_")):
        fn = getattr(m, name)
        if not callable(fn):
            continue
        try:
            fn()
        except Exception:
            bad += 1
            print("FAIL", mod, name)
            traceback.print_exc()
sys.exit(1 if bad else 0)
PY
```

Then, on the rendered page, in **both** themes: measure contrast against all four surfaces, enumerate
every `cursor:pointer` element and confirm it has a handler, and check tap targets at 375×812 as well
as desktop. A screenshot alone has never caught any of the seven bug classes listed above.
