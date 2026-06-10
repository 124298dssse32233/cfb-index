# Rankings Redesign — Component, State & Accessibility Spec

**Authored 2026-06-08.** The build contract for every UI component in the redesign: anatomy, the full
state set, the DOM/class contract (matching the mockups in `docs/octopus/mockups/`), tokens, and the
keyboard/ARIA model. Pairs with the [data-viz standards](rankings_redesign_dataviz_standards.md), the
[engineering spec](rankings_redesign_engineering_spec.md), and `cfb-tokens.css`. Target: **WCAG 2.2 AA**.

> Convention: class names are the contract — the renderer must emit these so the CSS applies. Tokens are
> the `--color-*` / `--font-*` / `--sp-*` names from `cfb-tokens.css`.

---

## 0. Global state model (applies to every interactive element)

| State | Trigger | Visual treatment | Notes |
|---|---|---|---|
| **default** | — | base tokens | — |
| **hover** | pointer only | subtle surface/elevation lift | gate behind `@media (hover:hover)` so touch doesn't get stuck-hover |
| **focus-visible** | keyboard focus | **2px `--color-navy-600` ring, 2px offset** (`:focus-visible`) | NEVER remove outlines without a replacement; visible on every focusable control |
| **active / pressed** | pointerdown | `transform:scale(.97)` 120ms `--ease-emphasized` | fire on `pointerdown`, not click, for latency-free feedback |
| **selected / on** | chosen | filled/accent (per component) | mirror with `aria-selected`/`aria-pressed`/`aria-current` |
| **disabled** | — | 40% opacity, `cursor:not-allowed` | `disabled` attr (or `aria-disabled` for non-form), removed from tab order only if truly inert |
| **loading** | data pending | **skeleton** (see §18) | `aria-busy="true"` on the region |
| **empty / low-data** | no/under-threshold data | graceful copy, not blank (see §7 Awaiting Signal) | never render a broken/zero chart |
| **error** | fetch/render fail | inline message + retry affordance | `role="alert"` for the message |

**Cross-cutting a11y rules:** touch targets **≥48px** (hit area, glyph may be smaller); `prefers-reduced-motion:reduce`
disables transforms/auto-play and keeps opacity/instant states (press feedback may stay — it's not vestibular);
all text meets **AA contrast (4.5:1 body, 3:1 large/UI)**; nothing conveyed by color alone (pair with icon/label/text).

---

## 1. Masthead `.masthead`
- **Anatomy:** dark `--color-ink` bar w/ gridiron `repeating-linear-gradient` · `.mh-brand` (Bebas wordmark + `.g` football glyph) · `.mh-btn` actions (⌘K/search) · optional `.dateline` (live pulse) or `.crumbs` (breadcrumb) or desktop `.nav`.
- **States:** sticky (`position:sticky;top:0`); the `.dateline .pulse` animates only with motion allowed.
- **A11y:** `<header>` landmark; brand is an `<a href="/">`; `.mh-btn` are `<button>` with `aria-label` ("Search"); breadcrumb is `<nav aria-label="Breadcrumb"><ol>`; desktop nav is `<nav aria-label="Primary">` with `aria-current="page"` on the active link. The live "Updated …" pulse: `aria-hidden` on the dot, the text is real.
- **Responsive:** mobile = brand + 1–2 icon actions; desktop (≥1024) = brand + horizontal `.nav` + ⌘K. Safe-area: `padding-top:max(env(safe-area-inset-top),8px)`.

## 2. Bottom tab bar `.tabbar`
- **Anatomy:** fixed bottom, 4 `.tab` (icon `.ti` + text label). `padding-bottom:env(safe-area-inset-bottom)`.
- **States:** active tab `.tab[aria-selected]` → `--color-ink`; others `--color-gray-400`.
- **A11y:** `<nav aria-label="Primary">`; each tab a `<button>`/`<a>` with **visible text label** (never icon-only) + `aria-current="page"` for the active. Height ≥56px content.
- **Responsive:** mobile/tablet only; hidden ≥1024 (desktop uses the masthead `.nav`).

## 3. Finding banner `.finding`
- **Anatomy:** `.kick` (coral eyebrow + glyph) + serif sentence. One line, dismissible.
- **States:** default; dismissed (removed). Optional `[hidden]` after dismiss.
- **A11y:** the dismiss control is a `<button aria-label="Dismiss finding">`; the banner is not a live region (static). Color: coral kick has text, not color-only meaning.

## 4. Lens tabs `.lens` (Power / Résumé / Bettor / Belief)
- **Anatomy:** underlined text tabs; selected gets a 2px coral underline.
- **States:** default / hover (pointer) / focus-visible / selected (`[aria-selected=true]`, ink + underline).
- **A11y:** `role="tablist"`, each `<button role="tab" aria-selected aria-controls="board">`; **arrow-key navigation** between tabs (Left/Right moves selection), `tabindex="0"` on the selected tab and `-1` on others (roving tabindex); the board is the `role="tabpanel"`. Selecting a lens re-sorts/re-keys the board and announces via `aria-live="polite"` ("Sorted by résumé").
- **Responsive:** identical; may scroll-x if cramped.

## 5. Filter chips `.fchip`
- **Anatomy:** pill, 30–32px tall, optional check/× ; selected = `--color-ink` fill (or `--color-navy-50` tonal).
- **States:** default / hover / focus-visible / pressed / **selected** (`aria-pressed=true`, + checkmark) / disabled.
- **A11y:** each a `<button aria-pressed>`; the active-filter row uses a visible "×" per chip (`aria-label="Remove SEC filter"`) + a "Clear all"; result count announced via `aria-live="polite"` ("42 teams"). Don't hide controls with the `hidden` attr (kills AT) — use a visually-hidden utility that stays focusable.
- **Responsive:** horizontal scroll on mobile; wrap on desktop. On mobile, the full filter set opens in a **Popover** sheet (`popover` attr → free focus-return + Esc/light-dismiss).

## 6. Board row `.row` / `.row-main` (+ drawer)
- **Anatomy (mobile card-feed):** `.tcr` team-color rule · `.rk` rank numeral + `.mom` momentum tick · `.idb` (logo `.logo` w/ `.fb` monogram fallback · `.nm` name w/ `.star` for #1 · `.meta` = `.conf` + `.bchip`) · `.pow` (value + inline `#rank`) · `.chev`. Tap → `<details>` `.detail` drawer.
- **Anatomy (desktop):** a `<tr>` in a KenPom table; cells carry value + inline rank (`.rk2`).
- **States:** default / hover (`--color-gray-50` desktop) / active (scale .985) / **open** (drawer expanded, chevron rotated) / **lead** (#1 — faint team-color `--tc` tint on `.row-main`) / loading (skeleton row) / empty (see belief chip empty).
- **A11y:** mobile row = `<article>`; the expand control is a `<button aria-expanded aria-controls="drawer-id">` (or native `<details><summary>`); **drawer content is lazy but stays in the a11y tree when open**; logo `<img alt="">` (decorative — team name is text); the inline `#rank` superscript reads "Power 19.7, rank 4" via `aria-label` on the cell. Desktop table: semantic `<table>` in a `<div role="region" aria-labelledby tabindex="0">` (never `display:block` a table); `<th scope>`; sortable headers per §4-style `aria-sort`.
- **Responsive:** see [responsive spec](rankings_redesign_responsive_spec.md) — card-feed <768, dense table ≥768/1280.

## 7. Belief chip `.bchip` (+ **Awaiting Signal** empty state)
- **Anatomy:** pill — `.hot` (coral, "▲ Fans +N"), `.cold` (navy, "▼ Fans −N"), `.align` (gray, "Aligned").
- **States:** the three above + **empty/low-data**: when mentions < `MIN_MENTIONS_FOR_SIGNAL`, render an `.bchip.signal` gray chip reading **"Awaiting signal"** with a `title`/tooltip "Not enough fan conversation yet." NEVER render a 0 or blank — this is the brief's graceful-degradation path.
- **A11y:** direction is in the **text** ("Fans +2"), not color-only; the arrow glyph is `aria-hidden`; "Awaiting signal" is real text.

## 8. Rank numeral `.rk` + momentum `.mom`
- **Anatomy:** Bebas display number; `.mom` 2px tick under it tinted green/red/gray by Δ.
- **States:** `.lead .rk` → `--color-amber-600` (contrast-safe; NOT amber-400 on white). On poll-update, number **rolls** (≤600ms, tabular-nums) — motion-gated.
- **A11y:** the momentum tick is decorative (`aria-hidden`); the Δ is also given as text/aria where it matters.

## 9. Inline-rank stat cell `.pow .v` / `.v .rk2` (KenPom)
- **Anatomy:** value (tabular) + small muted rank ("92.4 ·4").
- **A11y:** cell `aria-label="Power 92.4, ranked 4th"` so SR doesn't read "92.4 dot 4".

## 10. CFP cutline `.cutline`
- **Anatomy:** amber strip after rank 12, bracket glyph + "College Football Playoff cutline · top 12 in". Solid 1px amber borders (no dashed vibration).
- **A11y:** a `<tr>`/separator with text; conveys meaning in words, not just position.

## 11. Quantile dotplot `.dotplot` / `.dp`
- **States:** default; **legend required** ("makes it · bubble seeds 9–12 · out"); empty = "Not simulated yet".
- **A11y:** `role="img"` + `aria-label="18 of 20 simulations make the field, 90 percent"`; the amber "bubble" cells must be in the legend (color-only meaning is forbidden).

## 12. Tri-Rank (inline chip §7 + full viz `#triviz`)
- **Anatomy (viz):** 1→16 rank axis · three colored pips (navy model / coral room / amber USA) · the span **shaded** ("N-rank gap") · a legend naming each pip with its rank.
- **A11y:** `role="img"` + `aria-label="Model 3, room 2, country 4 — a two-rank disagreement"`; the legend is real text (the pips aren't decoded by color alone).

## 13. Fingerprint slider `.sv` + peer toggle `.peer` + scale `.fpscale`
- **Anatomy:** per metric — label + percentile value + a red→grey→navy `.sv-bar` with a fixed **50th-pct `::before` tick** + `.sv-dot`. One-time `.fpscale` legend ("0·worse — 50=average — elite·100"). `.peer` = peer-set toggle (FBS/P4/Conf).
- **States:** the peer toggle: default/hover/focus/selected (`.on`); switching re-renders the dots (`transition:left` motion-gated).
- **A11y:** `.peer` = `role="tablist"` (roving tabindex, arrow keys); each `.sv-bar` `role="img" aria-label="Pass efficiency: 90th percentile vs FBS"`; the gradient + tick are decorative.

## 14. Drawer `<details name>` (exclusive accordion)
- **States:** closed/open; exclusive (one open per `name` group); lazy content loads on open.
- **A11y:** native `<details>/<summary>` gives expand semantics free; a ~0.5KB JS shim enforces single-open on pre-Sept-2025 Safari/Android (degrades to multi-open, not broken). Focus stays on the summary; content is reachable in tab order when open.

## 15. Compare — vs-header `.vshead` · stat row `.st` · **dumbbell** `.fp` · sim bar `.sim`
- **Anatomy:** two team columns split by team color · winner-per-row stat table (`.st .v.win` highlighted toward the leader's color) · fingerprint **dumbbell** (two team-color dots + a connector colored toward the leader + numeric gap) · sim bar (split fill + **50% midline**).
- **A11y:** the winner highlight is paired with the value (not color-only); the dumbbell `role="img" aria-label="Pass efficiency: Georgia 80, Texas 90, edge Texas by 10"`; sim bar `role="img" aria-label="Texas 52%, Georgia 48%, near coin flip"`.

## 16. The Bridge — division selector `.divs` · spectrum `#spec` · spotlight `.spot`
- **Anatomy:** `.divs` = 5 division buttons (selected = filled team color) · the spectrum SVG (FBS lane doubles as rank scale, overlap band, haloed bridge line) · `.spot` card (computed FBS-equiv + "beats N").
- **States:** `.divs button.on` selected; selecting moves the bridge + updates spotlight (motion-gated `transition`).
- **A11y:** `.divs` = `role="tablist"` (roving tabindex, Left/Right keys, `aria-selected`); spectrum `role="img"` with a `aria-label` that states the computed finding ("Ferris State, power 54, equals FBS #102, ahead of 32 teams"); the spotlight updates `aria-live="polite"`.

## 17. The Room modules
- **Mood gauge `.meter`:** center "Mixed" tick + value shown; `role="img" aria-label="National mood: anxious optimism, 62 of 100, up 6"`.
- **Vibe row `.vs`:** logo + name + archetype + **shared-scale** spark + Δ number; spark `aria-hidden` (the Δ number carries it).
- **Respect gap / rival heat / civil war:** values shown; rival-heat single color + number; civil-war 50% midline + cohesion number. Each entry's meaning is in text.

## 18. Charts — loading, empty, table-fallback (general rule)
- **Loading:** a **skeleton** matching the chart's footprint (reserve `contain-intrinsic-size`/explicit width-height to avoid CLS); `aria-busy="true"` on the container.
- **Empty:** a one-line "Not enough data yet" in the chart's frame — never a zero-axis or blank box.
- **Table-fallback (required for AA):** every chart ships a visually-hidden `<table>` of the same series (USWDS `usa-sr-only` pattern) so SR users get the numbers, not the geometry; a visible "View as table" toggle is a plus.

## 19. Skeleton spec
- Gray (`--color-gray-100`) blocks matching final geometry (row height, column count, chart box). No shimmer by default (NN/g: distraction + a11y risk); if used, gate behind `prefers-reduced-motion:no-preference`. Show for waits >300ms; swap without layout shift.

## 20. Movers / Stories / Report-card cards
- **Anatomy:** card = eyebrow + Bebas figure + one sentence (+ optional spark). One tap target, one metric, one sentence (Dashboard-archetype rule).
- **A11y:** whole card is one link/button (`aria-label` = the full finding); the spark is `aria-hidden`.

---

## Build order note
Per the engineering spec, Phase 1 needs: masthead, finding, board row + belief chip (archetype label) + inline-rank cell + CFP cutline + lens tabs + filter chips + tab bar + skeleton/empty states. The drawer, Tri-Rank viz, fingerprint, dotplot, Compare, Bridge, Room, and Report-card charts are Phase 2–3. Each component above is independently buildable to this spec.
