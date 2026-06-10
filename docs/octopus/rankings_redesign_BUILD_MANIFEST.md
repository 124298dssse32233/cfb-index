# Rankings Redesign — BUILD MANIFEST · START HERE

**Authored 2026-06-08.** The front door for the build window. Everything needed to implement the rankings
redesign 1:1 lives in `docs/octopus/`; this file is the map, the build order, the **verified** data-readiness
ledger, and the open-decisions register. Read this first, then the docs in §1.

> **Coordination:** this folder is a **design + spec handoff** produced in a separate window. The build window
> owns the generator (`reporting.py` etc.). Nothing here has been built. The mockups are HTML prototypes, not
> production code — they are the **visual + behavioral contract**, not files to copy wholesale.

---

## 1. Read order (what each doc is for)

| # | Doc | Role |
|---|---|---|
| 1 | **this file** | map · build order · verified data ledger · open decisions |
| 2 | [`rankings_redesign_spec.md`](rankings_redesign_spec.md) (v4) | the design thesis — board-first IA, the 3 identity pillars, originality slate |
| 3 | [`rankings_redesign_engineering_spec.md`](rankings_redesign_engineering_spec.md) | mockup → generator mapping. **Its top "AUDIT CORRECTIONS" block is authoritative** over its own body |
| 4 | [`rankings_redesign_component_spec.md`](rankings_redesign_component_spec.md) | the 20 components: anatomy · state set · DOM/class contract · keyboard/ARIA |
| 5 | [`rankings_redesign_microcopy_spec.md`](rankings_redesign_microcopy_spec.md) | every string — voice, number formatting, lexicon, empty/error/loading copy, chart alt-text templates |
| 6 | [`rankings_redesign_dataviz_standards.md`](rankings_redesign_dataviz_standards.md) | the 5 chart standards + per-chart gold-standard ledger (build `charts/` to this) |
| 7 | [`rankings_redesign_responsive_spec.md`](rankings_redesign_responsive_spec.md) | 390/768/1280 reflow; the card-feed ↔ KenPom-table enhance-up |
| 8 | [`rankings_redesign_research.md`](rankings_redesign_research.md) | the why behind the craft (mobile UX, ratings presentation, near-zero-JS) |

**Mockups** (`docs/octopus/mockups/`): `index.html` (showcase entry) · `rankings-mobile.html` (v5 flagship
board) · `desktop-board.html` (KenPom table + bump + rail) · `team-detail.html` · `conference.html` ·
`cross-bridge.html` (signature) · `compare.html` · `the-room.html` · `report-card.html` · **`states.html`**
(every loading/empty/error/Awaiting-Signal state on the real classes).

**Run them:** `python -m http.server 4599 --directory docs/octopus/mockups` (registered as the `octo-mockup`
launch config) → http://localhost:4599/index.html.

---

## 2. Token & asset setup — the FIRST build step (Phase 0)

The redesign is **Option C: light surface + Bebas Neue** (owner decision 2026-06-08). The token file does not
exist in production yet — it must be materialized.

1. **Materialize `cfb-tokens.css`.** `docs/octopus/mockups/cfb-tokens.css` already materializes
   `docs/design-system/00-tokens.md` (the locked-but-never-built doc) into a real stylesheet — all six
   `--color-*` ramps (50–900), Bebas `--font-display`, motion tokens, the new `--color-line-strong`, tabular-
   numeral enforcement, optional dark mode, reduced-motion. **Promote it to a repo source** and emit it to
   `/assets/css/cfb-tokens.css` during asset assembly (alongside the existing `cfb-index.*.css`).
2. **Add two bundles:** `/assets/css/rankings-board.css` (port the mock CSS, token-mapped to `--color-*`) and
   `/assets/js/rankings-board.js` (sort, filter-count, `<details>` shim, view-transition). Keep JS < 50KB.
3. **Registration point (verified):** stylesheets/scripts are emitted by **`_global_link_tags()` at
   `reporting.py:6279`** (it already emits `/assets/tokens-bridge.css`, the hashed `cfb-index.*.css`,
   `cmdk.css`, `stats_table.css`, `/assets/js/url-state.js`). ⚠️ **`_global_link_tags()` is GLOBAL** — see
   Open Decision **OD-1**: scope the light/Bebas tokens to the rankings/conference/archive surfaces so they
   don't clobber the **dark/Inter** team-page system during the migration period (inject the new `<link>`s in
   `render_rankings_page_html`'s own `<head>`, or gate with a body class / `@scope`, not globally).
4. **Logos (verified loader):** build on **`resolve_team_brand(slug) → TeamBrand`** (`visual_assets.py:183`,
   carries `logo_local_path`). The mocks hotlink the ESPN CDN for personal-use preview only; production serves
   local `/assets/logos/...`. Emit the mock's monogram fallback (`.fb`) so a missing logo degrades, not breaks.
5. **Fonts:** Bebas Neue + Source Serif 4 + Inter — add to the font pipeline if not already preloaded.

### 2a. Token-scoping recipe — resolves OD-1 (do this from line 1)

**The hazard:** `_global_link_tags()` is global and team pages render in the **dark/Inter** system
(`team_pages/assets/tokens.css`, `--bg-*/--fg-*/--tone-*`). If the light/Bebas system leaks site-wide it
clobbers them. Three rules keep it surgical:

**1 — Load page-scoped, not global.** Do **not** add the redesign CSS to `_global_link_tags()`. Append the
`<link>`s inside the three redesign renderers' own `<head>` (`render_rankings_page_html`,
`render_conference_page_html`, `render_archive_snapshot_html`) — after the `_global_link_tags()` output so the
shared chrome (nav, `cmdk.css`, `tokens-bridge.css`) still loads:
```python
head = _global_link_tags()                      # shared nav / command palette / global bundle
head += (
    '<link rel="stylesheet" href="/assets/css/cfb-tokens.css">\n'
    '<link rel="stylesheet" href="/assets/css/rankings-board.css">\n'
    '<script src="/assets/js/rankings-board.js" defer></script>\n'
)
```

**2 — Scope tokens + base under a skin class, never bare `:root`/`body`.** In the **production**
`cfb-tokens.css`, hang the ramps and base surface/type off a wrapper (the mockups keep `:root` because they're
standalone — re-scope on promotion):
```css
.cfb-rkx{
  --color-navy-600:#185FA5; /* …all six ramps + semantic aliases + --font-display:'Bebas Neue' … */
  background:var(--color-surface); color:var(--color-text); font-family:var(--font-sans);
}
.cfb-rkx .row-main{ … }     /* every redesign selector descends from .cfb-rkx */
```
Emit `<body class="cfb-rkx">` (or a top-level wrapper) on the three redesign surfaces **only**.

**3 — Re-scope the file's two global blocks.** `cfb-tokens.css` currently has a global tabular-numeral block
(`.stat,.num,…`) and dark-mode on `:root[data-theme="dark"]`/`.dark`. Move both under the wrapper so the file
is inert even if it ever loads globally:
```css
.cfb-rkx :is(.stat,.num,.tabular,td.numeric,.data-table td,.delta,.rank-value){ font-variant-numeric:tabular-nums; }
.cfb-rkx[data-theme="dark"], .cfb-rkx.dark{ --color-surface:#1A1A18; /* …flip surfaces… */ }
```
(The reduced-motion `*{}` block may stay global — it's harmless.)

**Why not `@layer`:** legacy `cfb-index.css` is **unlayered**, and unlayered styles **beat** `@layer` rules —
layering the redesign would make it *lose*. The `.cfb-rkx` wrapper instead gives redesign selectors higher
specificity than bare legacy element/class selectors, with no `!important` wars. The collision surface is tiny:
the redesign's class names (`.row-main`, `.bchip`, `.sv-bar`, …) don't exist in `cfb-index.css`; only base
element styles (`body`, `a`, `table`, headings) could clash, and scoping base under `.cfb-rkx` neutralizes them.
**Verify** the command palette (`cmdk.css`, different classes) still themes correctly on the rankings page.

**Migration exit:** when team pages adopt light/Bebas later (deferred), promote the tokens from `.cfb-rkx` to
`:root`, drop the wrapper, and route the CSS through `_global_link_tags()`.

---

## 3. Data-readiness ledger — VERIFIED against the codebase (2026-06-08)

The single most important table for estimation. **EXISTS** = wire it; **NET-NEW** = build it first (modeling
or schema work, not a render tweak). Verified by direct audit — paths/line numbers may drift, grep the symbol.

| Feature (surface) | Backing data | Status | Where (verified) |
|---|---|---|---|
| Board: **Power** + rank | `RankingRow.power_rating` / `power_percentile` | ✅ EXISTS | `reporting.py:131` (dataclass) |
| Board: **Résumé** + rank | `RankingRow.resume_score` / `resume_rank` / `resume_percentile` | ✅ EXISTS | same |
| Board: **SoS** | `RankingRow.schedule_connectivity` | ✅ EXISTS | same |
| Board: **Δ / momentum** | `_attach_rank_changes()` — re-derived from `power_ratings_weekly` × `model_runs` | ✅ EXISTS (no `ranking_snapshots` table) | `reporting.py:356`, queries at `:245/:262/:315` |
| **Confidence** dot/band | `RankingRow.cross_level_confidence` + `confidence_calibration` thresholds; fan floors `MIN_MENTIONS_FOR_HIGH_CONFIDENCE=40` / authors 12 | ✅ EXISTS | `migrations/20260531_03`; `fan_intelligence.py:33` |
| **Logos** | `resolve_team_brand(slug).logo_local_path` | ✅ EXISTS | `visual_assets.py:183` |
| **Belief chip** — archetype label (Phase-1 fallback) | `fetch_team_mood_profile()` archetype; floor `MIN_MENTIONS_FOR_SIGNAL=12` → else **Awaiting signal** | ✅ EXISTS | `fan_intelligence.py:53`, `:33` |
| **Belief chip** — numeric "Fans +N" | `compute_implied_ranks()` (Tri-Rank gap) | ⛔ NET-NEW (P0 spike) | does **not** exist |
| **Tri-Rank** full viz | implied-rank derivation (model = `rank`; room = belief-score ordinal; nation = poll/respect ordinal) | ⛔ NET-NEW | — |
| **Fingerprint** sliders | `fetch_savant_rows()` + `render_percentile_bar()` | ✅ EXISTS | `savant_data_loader.py:309` (takes a `sqlite3.Connection`); `theme/percentile_bar.py:195` |
| **Season arc** | `fetch_arc_rows(db, team_id)` | ✅ EXISTS | `season_arc_loader.py:419` |
| **The Room** modules | `fetch_fan_intel_board(db, season, week, team_index)` → leaderboard lists | ✅ EXISTS (needs the 4th `team_index` arg) | `fan_intelligence.py:529` |
| **CFP %** / playoff **dotplot** | per-team P(make 12-team field) | ⛔ NET-NEW probabilistic layer — **build on** the deterministic `compute_season_path_projections()` (floor/base/ceiling, NOT odds) | `team_preview/__init__.py:69` |
| **What-If sim** | same probabilistic engine | ⛔ NET-NEW | — |
| Desktop **Off/Def** columns | adjusted offensive/defensive efficiency + ranks | ⛔ DOES NOT EXIST → **omit in Phase 1**, net-new later | confirmed absent |
| **Bump chart** weekly history | `power_ratings_weekly` (weekly rows) | ✅ EXISTS | `reporting.py:245` |
| **CFP cutline** | constant (after rank 12) | ✅ EXISTS | inline |
| **Finding banner** | top mover / consensus from `rankings` + board | ✅ EXISTS | derive in renderer |
| **Lens:** Power / Résumé / Belief sorts | re-sort existing columns | ✅ EXISTS | `_rankings_board_script:25447` |
| **Lens:** Bettor | betting-market columns | 🟡 PARTIAL (conference betting data) | — |
| **Filter chips** (level / conference / tier) | `RankingRow.level_code` / `conference_name`; `tier` via `getattr(row,'tier','all')` | ✅ EXISTS (tier is a soft attr) | `_render_rankings_row:22917` |
| **Model Report Card** / calibration | `predictive_claims` + `claim_outcomes` (**net-new**) + `confidence_calibration` (exists) | ⛔ NET-NEW schema + ingest — **prerequisite**, multi-season sample + CIs | tables absent |

**Phase-1 thesis (verified):** everything tagged ✅ above is the board-first sheet — Power/Résumé/SoS inline
ranks, Δ, confidence, logos, archetype belief (with Awaiting-Signal), CFP cutline, filters, lenses, finding,
SEO — ~70% of the perceived leap, low risk. The four ⛔ items are the moat and are real work; don't promise
them as quick wins.

---

## 4. Build sequence (each phase = an independently shippable slice)

### Phase 0 — Foundations (prerequisite for everything)
- [ ] Materialize `cfb-tokens.css` → `/assets/css/` (§2.1); add `rankings-board.css` + `.js` (§2.2); register
      **scoped** to rankings surfaces (§2.3, **OD-1**).
- [ ] `team_logo_url(slug)` via `resolve_team_brand` (§2.4); monogram fallback.

### Phase 1 — The board (surgical, inside `reporting.py`; all ✅ data)
- [ ] Rewrite `_render_rankings_row()` → the v5 `.row` DOM (component spec §6): `.tcr · .rk+.mom · .logo(.fb) ·
      .nm(.star) · .meta(.conf,.bchip) · .pow(.v + inline #rank) · .chev` + a `<details name>` drawer stub.
- [ ] `.bchip` = archetype label + **Awaiting signal** below the floor (component spec §7, microcopy §5.3).
- [ ] `_render_finding_banner()`; CFP `.cutline` after rank 12; provenance footer.
- [ ] Lens tabs (§4) + filter chips (§5) in `_rankings_board_script()` — `:has()` filter, result-count
      `aria-live`, roving-tabindex tablist, default server-render sort.
- [ ] SEO: `ItemList` JSON-LD for the Top 25; Top 25 present with **JS disabled**.
- [ ] `content-visibility` chunking + lazy deep board (rows 26→).
- [ ] Loading / empty / error states per `states.html` + microcopy §5.2–5.4.
- [ ] **P0 spike (parallel):** `compute_implied_ranks()` → upgrade `.bchip` to numeric "Fans +N"; add the
      inline Tri-Rank `m·r·n` cell on desktop.

### Phase 2 — Drawer & modules (mix of ✅ loaders + ⛔ net-new)
- [ ] Row drawer content: `render_tri_rank()` (net-new derivation) · fingerprint (`fetch_savant_rows` +
      `render_percentile_bar`) · season arc (`fetch_arc_rows`) · momentum spark (`power_ratings_weekly`).
- [ ] The Room right-rail module (`fetch_fan_intel_board`).
- [ ] **Playoff projection** probabilistic layer → dotplot + CFP% column (build on
      `compute_season_path_projections`).
- [ ] **Model Report Card**: net-new `predictive_claims`/`claim_outcomes` schema + ingest, then
      `render_report_card()` + `render_calibration_curve()` (charts/ to data-viz standards).
- [ ] Compare tray (dumbbell, sim bar).

### Phase 3 — Tentpole & extraction
- [ ] The Bridge (cross-division) · desktop bump scrollyteller · Rankings Wrapped / Program Stripes ·
      What-If sim · extract `dashboards/renderer.py` (do NOT lead with the extraction).

Per-surface deltas (conference native columns, archive = frozen/retrospective): engineering spec §9.

---

## 5. Definition of Done (gates every surface's PR)

- **Visual:** matches the mockup at **390 / 768 / 1280** (responsive spec); uses `--color-*` tokens only — no
  literal hex/px outside `var(--…)`.
- **Data:** every value comes from a real loader (§3) or its specified empty state — never a 0, blank, or
  "N/A" (microcopy §5.3). Awaiting-Signal renders below the mention floor.
- **A11y (WCAG 2.2 AA):** focus-visible 2px navy ring on every control; ≥48px targets; nothing color-only;
  every chart `role="img"` + finding-stating `aria-label` (microcopy §6) **and** a visually-hidden data-table
  fallback; `aria-sort`/`aria-live` on sortable headers; `<details>` exclusivity (+ shim).
- **Perf:** FCP < 1.5s · INP < 200ms · **JS < 50KB** · critical CSS < 10KB · Lighthouse ≥ 95 · **no CLS**
  (every `content-visibility` chunk + SVG has explicit intrinsic size).
- **SEO/no-JS:** Top 25 server-rendered and crawlable with JS disabled; `ItemList` JSON-LD present.
- **Regression:** `python -u manage.py build-site` green; `tests/integration/test_cross_links.py` passes (flat
  `programs/<slug>.html`, `/assets/...` absolute).

---

## 6. Open decisions & risks (resolve before/early in the build)

| ID | Decision / risk | Recommendation |
|---|---|---|
| **OD-1** | `_global_link_tags()` is global; light/Bebas tokens would collide with the **dark/Inter team-page** system. | **Resolved — see the §2a recipe:** page-scoped load + `.cfb-rkx` wrapper + re-scoped dark/tnum blocks (NOT cascade layers, which would invert vs unlayered legacy CSS). Team pages migrate to light/Bebas later as a separate effort. |
| **OD-2** | **Model Report Card** needs net-new `predictive_claims`/`claim_outcomes` schema + a season of ingest. | Ship Phase 1 **without** the Report Card; build the claims ledger as its own workstream. The mock shows the target; don't block the board on it. |
| **OD-3** | **Playoff odds** are net-new (only a deterministic path engine exists). | Build a probabilistic layer on `compute_season_path_projections()`; until then, **omit the dotplot/CFP% column** (the cutline divider needs no data). |
| **OD-4** | **Tri-Rank numeric gap** depends on `compute_implied_ranks()` (net-new) + belief-score stability. | Validate the implied-rank ordering before Phase 1 consumes it; **fallback = archetype label** in `.bchip`. |
| **OD-5** | **Off/Def** desktop columns don't exist. | Phase-1 desktop ships **Power/Résumé/SoS** inline-rank only; add Off/Def if/when adjusted efficiency is modeled. |
| **OD-6** | `power_ratings_weekly` / `model_runs` are queried in `reporting.py` but no `CREATE TABLE` is in `migrations/`. | They resolve at runtime (live queries succeed), so treat as available; if a fresh-DB build fails, trace where they're seeded (`storage.py`) — don't assume a missing migration blocks the board. |
| **OD-7** | Two `fetch_savant_rows` exist (`data.py:797` takes `db`; `savant_data_loader.py:309` takes a `sqlite3.Connection`). | Use the one matching your connection handle; don't cross the wires. |

---

## 7. The honest delta (one paragraph)

Phase 1 is **more than a reskin**: it ships the board-first IA + the light/Bebas system + the data we already
compute (Power/Résumé/SoS inline ranks, Δ, confidence, logos, archetype belief with Awaiting-Signal, CFP
cutline, lenses, filters, SEO) on a **near-zero-JS** sheet — most of the perceived leap, low risk. The
**moat** — numeric Tri-Rank, playoff projection, the Model Report Card, the cross-division Bridge — is gated
behind the four ⛔ net-new builds, named in §3 so they're never mistaken for render tweaks. Build the board
first; earn the moat in Phases 2–3.
