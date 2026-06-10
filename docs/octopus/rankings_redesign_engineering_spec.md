# Rankings Redesign — Engineering Implementation Spec (build 1:1 into the generator)

**Authored 2026-06-08.** Translates the approved mockups into the existing Python static-site
generator so they build 1:1. Reference mockups: `docs/octopus/mockups/rankings-mobile.html` (v5,
mobile board) and `docs/octopus/mockups/desktop-board.html`. Design intent:
[`rankings_redesign_spec.md`](rankings_redesign_spec.md) (v4) · research
[`rankings_redesign_research.md`](rankings_redesign_research.md).

> **House rules (from CLAUDE.md):** edit the generator, never `output/site/**`. `reporting.py` is
> ~26.8k lines — grep for the symbols named below, do not trust line numbers. Build with
> `python -u manage.py build-site`. `programs/<slug>.html` is flat by design; `/assets/...` are
> absolute on purpose.

---

## ⚠️ AUDIT CORRECTIONS — authoritative (2026-06-08)
This spec's body was first drafted from a codebase *survey*; a direct code audit found breaking gaps.
**Where this section conflicts with the body below, THIS section wins.**

### The big one — design-system reality (a decision is required before building)
There is **no single `tokens.css`** matching this spec or the mockups. **Three systems coexist:**
- **Rankings page** (`reporting.py`) ships with legacy **`cfb-index.*.css` + `tokens-bridge.css`** — what the live `/rankings/` actually renders today.
- **Team pages** use `src/cfb_rankings/team_pages/assets/tokens.css` — **dark-mode default, "Inter Display" (NOT Bebas), `--bg-*/--fg-*/--stroke-*/--tone-*/--pct-*/--belief-*`** tokens.
- The **LOCKED doc** `docs/design-system/00-tokens.md` describes a **THIRD, unimplemented** system (Bebas Neue, light surface, `--color-*` 50–900 ramps, a `styles/tokens.css` path that doesn't exist). **The mockups follow the DOC** — i.e. they match no shipped CSS file.

→ **OWNER DECISION:** which token system does the redesign build on?
  - **A) Legacy rankings CSS** — fastest; but it's the old look and the mockups don't match it.
  - **B) Team-pages dark system** (Inter Display, `--tone-*`) — consistent with the world-class team pages; mockups would be re-skinned dark/Inter (lose Bebas).
  - **C) Implement the locked DOC** (Bebas/light/`--color-*`) as real tokens for the first time — matches the mockups + the locked doc, but it's net-new token infra and creates a 2nd identity vs the dark team pages.
  **DECIDED 2026-06-08 (owner): Option C — light + Bebas.** The mockups ARE the target design system.
  `docs/design-system/00-tokens.md` is the token source of truth — it already defines the full
  `--color-*` 50–900 ramps + Bebas `--font-display`; **materialize it into a real `tokens.css`** (it was
  never implemented) and build the redesign CSS on it. Team pages keep the dark/Inter system for now and
  **migrate to light/Bebas later** (separate effort). The redesign reuses team-page *data/loaders*
  (`fetch_savant_rows`, `fetch_arc_rows`, `fetch_team_mood_profile`) rendered in the new light/Bebas skin.

### Breaking data/code corrections
1. **`charts/` module does NOT exist** (no "six type" exports, no CI gate). Every chart (bump, quantile dotplot, calibration curve, spark) is **net-new from scratch**. The only existing chart renderer is `theme/percentile_bar.py` → `render_percentile_bar(label, value, raw_value, peer_group="vs FBS", sample_size=None, sample_label="snaps")` (+ `render_percentile_bars_grid/_card/_sample_badge`) — use it for the fingerprint.
2. **Model accountability has NO backing tables.** `games_predictive_claims`, `claim_outcomes`, `ranking_snapshots` **do not exist**. `confidence_calibration` exists but stores **per-domain percentile thresholds for confidence chips**, not Brier/outcomes. → The **Model Report Card + "did we call it" is fully net-new schema + ingest** — a *prerequisite build*, NOT the "existing tables (Phase 2)" the body claims.
3. **Rank-Δ / momentum / bump have no snapshots table** — Δ is re-derived at runtime from **`power_ratings_weekly` across `model_runs`** (`_attach_rank_changes`). Weekly bump history must query `power_ratings_weekly`.
4. **`tokens.css` path is `team_pages/assets/tokens.css`** (not `styles/`). **Motion tokens already exist** (`--motion-reveal` 240ms / `--motion-state` 180ms / `--motion-data` 420ms / `--motion-delight` 800ms, reduced-motion-aware) — reuse them; don't invent `--ease-*`/`--dur-*`.
5. **`RankingRow` also has `team_id` and `level_code`** (body missed both — load-bearing: `team_id` is the mood/savant join key, `level_code` drives the level filter chip). The display/percentile fields are `None` until `_attach_public_metric_context()` runs.
6. **`fetch_fan_intel_board(db, season_year, week, team_index)` needs a 4th arg** (`team_id → {slug, team_name, level_code, power_percentile}`) and returns **leaderboard lists** (`vibe_shifts`, `respect_gap_leaders/doubters`, `rival_heat_leaders`, `main_characters`, `panicked_fanbases`, `polarized`), ≤6 each — no scalar `respect_gap`, no "claims" source.
7. **`fetch_team_mood_profile(db, team_id, season_year, week, context)`** — `belief` is a sub-dict (`['belief']['score']`); it **early-returns `has_data=False` below `MIN_MENTIONS_FOR_SIGNAL`** → `compute_implied_ranks` (Tri-Rank) must guard the empty shape.
8. **Read-path loaders are `fetch_savant_rows(...)` and `fetch_arc_rows(db, team_id)`.** **Logos:** build on existing **`resolve_team_brand(slug) → logo_local_path`** (`visual_assets.py`), not a new `espn_id` column.
9. **No CI gate on chart vocabulary** (the "PRs fail on undefined chart imports" claim is false) — build the guard if wanted.
10. **`render_rankings_page_html(summary, rankings, latest_local_week, featured_team_pages=None, history_hub=None)`** — `latest_local_week` is a **required positional** the body omitted.

### What survives intact
All 10 render functions + signatures, the `RankingRow` scaffolding (modulo #5), `manage.py build-site`,
`render_percentile_bar`, `power_ratings_weekly`/`resume_ratings_weekly`, and the Phase-1
"data we already compute" thesis — **but ONLY for Power / Résumé / SoS / Δ** (RankingRow + runtime
snapshot re-derivation). Everything tagged "existing tables (Phase 2)" for claims/snapshots is net-new schema.

---

## 0. Build path & where the code goes
- **Renderer (main board):** `render_rankings_page_html()` in `src/cfb_rankings/reporting.py`
  → `output/site/rankings/index.html`. Grep: `grep -n "def render_rankings_page_html" src/cfb_rankings/reporting.py`.
- **Conference / archive:** `render_conference_page_html()`, `render_conferences_index_html()`,
  `render_archive_snapshot_html()` (same file).
- **Row + client script:** `_render_rankings_row()`, `_rankings_board_script()`.
- **Data:** `fetch_latest_rankings()` → `_fetch_rankings_for_summary()` →
  `_attach_rank_changes()`, `_attach_public_metric_context()`; dataclass `RankingRow`.
- **Fan intel:** `src/cfb_rankings/fan_intelligence.py` — `fetch_team_mood_profile()`, `fetch_fan_intel_board()`.
- **Team modules (Phase 2 drawer):** `src/cfb_rankings/team_pages/savant_data_loader.py`,
  `season_arc_loader.py`, plus `fetch_team_mood_profile`.
- **Tokens/CSS home:** ⚠️ Audit #4 — the existing file is `src/cfb_rankings/team_pages/assets/tokens.css` (NOT `styles/`), and it's the **dark/Inter** system. The redesign's **light/Bebas** tokens are net-new: materialize `docs/design-system/00-tokens.md` (the mockups' `cfb-tokens.css` already does) into a production token file — see `rankings_redesign_BUILD_MANIFEST.md` § "Token & asset setup".
- **Charts vocabulary:** ⚠️ Audit #1 — `src/cfb_rankings/charts/` does **NOT exist** (no six-type export, no CI gate). Every chart is net-new — create `src/cfb_rankings/charts/` to the [data-viz standards](rankings_redesign_dataviz_standards.md). The only existing renderer is `theme/percentile_bar.py`.
- **Architectural target (Phase 3):** seed `src/cfb_rankings/dashboards/renderer.py` (planned
  consolidation of home/hub/heisman/rankings — see `docs/design-system/30-page-archetypes.md` mapping table).

**Recommended sequencing:** ship **Phase 1 surgically inside `reporting.py`** (the board-first sheet
on near-zero-JS), then Phase 2 modules, then extract to `dashboards/renderer.py`. Do NOT lead with the
extraction.

---

## 1. Token mapping (mockup → `tokens.css`)
The mockups use two token conventions: the canonical **`--color-*`** names (in `cfb-tokens.css`, loaded by
`rankings-mobile.html` / `states.html` / `index.html`) and a legacy **`--navy-*` / `--ink` / `--disp`
shorthand** (inlined in `desktop-board.html` / `conference.html` / `cross-bridge.html`). **Production
standardizes on the `--color-*` names** from the materialized `cfb-tokens.css` (Option C — NOT the existing
dark `team_pages/assets/tokens.css`). Map any shorthand 1:1 and DELETE it:

| Mockup var | Production token (`tokens.css`) |
|---|---|
| `--navy-600` … | `--color-navy-600` … (all ramps) |
| `--ink` | `--color-ink` |
| `--muted` / `--subtle` | `--color-text-muted` / `--color-text-subtle` |
| `--surface` / `--card` / `--line` / `--line-strong` | `--color-surface` / `--color-surface-card` / `--color-line` / new `--color-line-strong` |
| `--sans` / `--serif` / `--disp` | `--font-sans` / `--font-serif` / `--font-display` |

**ADD to `tokens.css`** (new, used by the redesign):
```css
:root{
  --color-line-strong:#CFCCC4;            /* table rules, chip borders */
  /* motion tokens (M3) — research §F */
  --ease-emphasized:cubic-bezier(0.2,0,0,1);
  --ease-decelerate:cubic-bezier(0.05,0.7,0.1,1);
  --ease-accelerate:cubic-bezier(0.3,0,0.8,0.15);
  --dur-1:150ms; --dur-2:300ms; --dur-3:450ms;
}
```
All redesign CSS reads tokens only — zero literal colors/sizes (design-system rule).

---

## 2. Asset pipeline
**Team logos.** Mock hotlinks ESPN CDN (`https://a.espncdn.com/i/teamlogos/ncaa/500/{espn_id}.png`).
For the generator, **localize** to avoid an external dependency on the published site:
1. Add an `espn_id` (or reuse existing external id) column on `teams`, or a `data/logos_manifest.json`
   keyed by slug. CFBD `/teams` already returns logo URLs — backfill via a one-off CLI subcommand
   (`manage.py import-team-logos`), download into `output/site/assets/logos/<slug>.png` during build.
2. Helper: `team_logo_url(slug) -> "/assets/logos/<slug>.png"` (absolute path, per house rule).
3. Renderer emits the mock's fallback monogram so a missing logo degrades, not breaks:
   `<span class="logo"><img src="{url}" alt="" loading="lazy" onerror="…show .fb…"><span class="fb" style="background:{accent}">{INI}</span></span>`.
- **Conference logos:** dropped from the board per the v5 visual critique (raster noise). Keep text
  `confShort`. (Available if ever needed: `/i/teamlogos/ncaa_conf/500/{conf_id}.png`.)
- **Fonts:** already in the pipeline (Bebas Neue + Source Serif Pro + Inter, preloaded — see tokens.css
  preload note). No change.
- **New bundles:** `assets/css/rankings-board.css` and `assets/js/rankings-board.js` (small). Register
  in the rankings `<head>` exactly like the existing `cfb-index.*.css` / `bets/*.js` deferred assets.

---

## 3. The board is server-rendered & no-JS (SEO/casual pillar, spec §4)
Non-negotiable: the **Top 25 renders as semantic HTML with zero JS** and is crawlable.
- Mobile: an ordered list / table of rows; Desktop: a real `<table>` (see §5 M2).
- Emit **schema.org `ItemList`** JSON-LD for the Top 25 (rank + team + url) in `<head>`.
- JS only *enhances*: sort, filter-count, compare, drawer exclusivity shim, view-transition re-sort.
- Wrap any `<table>` in `<div role="region" aria-labelledby tabindex="0">` — never `display:block` a
  table (research §D-1).

---

## 4. Component → renderer map (the 1:1 contract)
Each row: **mock class/DOM → owning Python fn → data source → existing? / net-new**. The DOM the
renderer emits MUST match the mock class names (they are the CSS contract).

| Module | Mock DOM (contract) | Owner fn (new or modify) | Data source | Status |
|---|---|---|---|---|
| **Masthead + dateline** | `.masthead` / `.dateline` (gridiron via CSS) | modify page header in `render_rankings_page_html` | `summary` (season/week/updated, source count) | **existing** |
| **Finding banner (1 line)** | `.finding` `.kick`+serif `p` | new `_render_finding_banner(summary, rankings, board)` | top mover / consensus from `rankings` + `fetch_fan_intel_board` | existing data |
| **Lens tabs** | `.lens` Power/Résumé/Bettor/Belief | `_rankings_board_script` (re-sort/re-key) | sorts existing columns; Bettor needs betting cols (conf data) | partial |
| **Filter chips** | `.filterbar` `.fchip` | `_rankings_board_script` (`:has()`/checkbox) | level/conference/tier facets on the row | **existing** |
| **M2 Board row** | `.row`/`.row-main`: `.tcr` `.rk`+`.mom` `.logo` `.nm` `.meta(.conf,.bchip)` `.pow(.v,.l)` `.chev` | **modify `_render_rankings_row`** | `RankingRow` (below) | mostly existing |
| **Tri-Rank belief chip (inline)** | `.bchip hot/cold/align` | new `belief_chip(profile, model_rank)` | `fetch_team_mood_profile` archetype (P1) → numeric gap (P0 spike) | **P1 label existing / gap net-new** |
| **CFP cutline** | `.cutline` after rank 12 | inline in board loop | constant (rank==12) | **existing** |
| **Row drawer** | `<details name>` `.detail`→`.dpad` | new `_render_row_drawer(row)` | loaders below | **Phase 2** |
| **Tri-Rank scale (full)** | `.tri`/`.tri-scale`/`.tri-tick m/r/n` | new `render_tri_rank(model,room,nation)` | implied ranks | **net-new derivation** |
| **Playoff dotplot** | `.dp`/`.dp-dots i.on/.bub` | new `render_quantile_dotplot(p, n=20)` → `charts/` | season-sim playoff% | **net-new (projection)** |
| **Fingerprint (3 + link)** | `.sv`/`.sv-bar`/`.sv-dot` | reuse `theme/percentile_bar.py` + `savant_data_loader` | savant percentiles | **existing loader (Phase 2)** |
| **Key players (text line)** | `.kpline` (no avatar) | new `render_key_players(team)` | roster/usage table | optional (Phase 2) |
| **Momentum** | `.trend` + spark SVG | new trajectory-spark in `charts/` | Δ re-derived from `power_ratings_weekly` across `model_runs` (no `ranking_snapshots` table — Audit #3) | existing data |
| **Stories strip** | `.stories`/`.story` | reuse `fetch_fan_intel_board` board | vibe_shifts / respect_gap / claims | **existing** |
| **Desktop bump (primary viz)** | `#bump svg` | new `render_bump_chart(top_n)` → `charts/` (overtake variant) | weekly history from `power_ratings_weekly` (Audit #3) | **existing data** |
| **Desktop table** | `<table>` inline-rank cells `.v .rk2` | new `render_kenpom_table(rows)` | `RankingRow` + off/def | partial |
| **Right rail: The Room** | `.mod` `.room-row` `.bchip` | reuse `fetch_fan_intel_board` | board leaderboards | **existing** |
| **Right rail: Model Report Card** | `.report` big% + `calib()` curve | new `render_report_card()` + `render_calibration_curve()` → `charts/` | ⚠️ net-new `predictive_claims`+`claim_outcomes` schema (only `confidence_calibration` exists) | **NET-NEW schema+ingest (Audit #2) — prerequisite, not wiring** |
| **Methodology footer** | `.foot` provenance | modify existing footer | sample-size + provenance | **existing** |

---

## 5. Data wiring — existing vs net-new (read this before estimating)
**`RankingRow` already carries** (grep `class RankingRow`): `rank, rank_change, slug, team_name,
level_code, conference_name, power_rating, resume_score, power_display, resume_display, power_percentile,
resume_percentile, resume_rank, cross_level_confidence, schedule_connectivity, previous_rank`.
→ Phase 1 board uses ALL of these directly (Power+rank, Résumé+rank, SoS=`schedule_connectivity` rank,
confidence dot=`cross_level_confidence`, Δ=`rank_change`).

**Net-new data (do NOT under-estimate — these are modeling tasks, not render tweaks):**
1. **Tri-Rank implied ranks (P0 spike).** `model_rank` = published `rank`. `room_rank` = rank teams by
   `fetch_team_mood_profile().belief.score` percentile → ordinal. `nation_rank` = rank by national
   belief / `respect_gap`. Build `compute_implied_ranks(db, season, week) -> {team_id:(room,nation)}`;
   validate stability before Phase 1 consumes it. **Phase 1 fallback:** show the existing archetype
   label in `.bchip` (e.g., "Hype Train"), swap to the numeric "Fans +N" once the spike lands.
2. **Playoff odds (projection engine).** A season Monte-Carlo producing per-team P(make 12-team field).
   Feeds the dotplot + the What-If sim. **Net-new** (or wire an existing forecast if one exists). Until
   then, omit the dotplot column on Phase 1 (cutline divider needs no data).
3. **Off/Def efficiency + ranks** (desktop KenPom columns). If the model doesn't expose adjusted
   off/def, that's net-new computation; **Phase 1 desktop ships Power/Résumé/SoS inline-rank only**, add
   Off/Def in a later pass.
4. **Model Report Card** (Phase 2): aggregate over `games_predictive_claims`/`claim_outcomes` with
   **multi-season sample + confidence intervals** (critique fix); never cherry-pick a single "we called
   it." Brier + calibration via `confidence_calibration`.

---

## 6. Near-zero-JS interaction stack (research §D → implementation)
Target stays JS < 50KB. Map each interaction:
- **Expandable rows →** `<details name="board-row">` exclusive accordions (Baseline Sep-2025) + a ~0.5KB
  shim in `rankings-board.js` to enforce single-open on pre-2025 Safari/Android.
- **Filter →** hidden `<input type=checkbox>` + `:has()` CSS row visibility, guarded by
  `@supports(selector(:has(*)))`. JS only for the live result count + `aria-live`.
- **Sort →** server-render default sort; ~1KB handler reorders `<tr>` (or toggles pre-sorted variants)
  and sets `aria-sort` + an `aria-live` status (research §D-5).
- **Long board →** `content-visibility:auto; contain-intrinsic-size:auto Npx` on per-conference
  `<tbody>` / row chunks (≈7× render win). Deep board (rows 26-668) lazy-injected on "Load deep board".
- **Filter sheet (mobile) →** Popover API (`popover` attr) — free top-layer + light-dismiss + implicit
  `aria-expanded`; anchor-positioned with a static fallback.
- **Re-sort animation (poll drop) →** `document.startViewTransition()` with `view-transition-name` per
  row (stable per team slug); reduced-motion skips it. Enhancement only.
- **Focus management is budgeted JS** (drawers/popover/compare): focus trap + return + `aria-live`.
  "No-JS" applies to *render*, not a11y.

---

## 7. Motion (research §F)
Use the tokens from §1. Pairings: small in-place ≈ `--dur-1` emphasized; card/row enter ≈ `--dur-2`
**decelerate**; exits **accelerate**. Number roll on Δ/rank ≤600ms tabular-nums. Stagger row entrance
40–60ms (visible viewport only). Everything wrapped in `@media (prefers-reduced-motion:no-preference)`;
animate `transform`/`opacity` only.

---

## 8. Accessibility & performance acceptance criteria (gate the PR)
- WCAG 2.2 AA. Every chart (`bump`, `calib`, dotplot, spark, fingerprint) ships `role="img"` +
  finding-stating `aria-label` **and** a visually-hidden data-table fallback.
- Touch targets ≥48px; `aria-sort` + `aria-live` on sortable headers; filter state announced.
- Budgets: FCP<1.5s, INP<200ms, **JS<50KB**, critical CSS<10KB inlined, **Lighthouse ≥95**. Renders at
  390/768/1280. No CLS (every `content-visibility` chunk + SVG has explicit intrinsic size).
- Contrast fixes already in the mock: rank #1 is ink/`amber-600` (not `amber-400` on white); cutline is
  solid 1px (no dashed "vibration").

---

## 9. Per-surface deltas
- **Conference** (`render_conference_page_html`): same board-first sheet, pre-filtered to the
  conference; keep its richer native columns (Record · ATS · Wins-vs-Market · Recent Form); finding +
  The Room scoped to members; reflect the rebuilt **9-team 2026 Pac-12 / thinned Mountain West** in
  filters + `confShort`.
- **Archive** (`render_archive_snapshot_html`): RETROSPECTIVE — no live signals/pulse; the overtake-bump
  scrollyteller + Model Report Card ("said vs happened") are the stars; mood renders as it stood that
  week.

---

## 10. Phase 1 build checklist (surgical, `reporting.py`)
1. `tokens.css`: add `--color-line-strong` + motion tokens (§1). New `assets/css/rankings-board.css`
   (port the mock CSS, token-mapped) + `assets/js/rankings-board.js` (sort, filter-count, details-shim,
   view-transition). Register in the rankings `<head>`.
2. `team_logo_url(slug)` helper + `manage.py import-team-logos` (CFBD) → `assets/logos/`.
3. Rewrite `_render_rankings_row()` to emit the v5 `.row` DOM (ledger rule, hero rank + momentum tick,
   logo, name, `.conf`, `.bchip` [archetype label fallback], `.pow .v`+inline `#rank`, chevron) + a
   `<details name>` drawer stub.
4. `_render_finding_banner()`; CFP `.cutline` after rank 12; provenance/liveness footer; SEO `ItemList`
   JSON-LD; `content-visibility` chunking + lazy deep board.
5. `_rankings_board_script()`: lens re-sort + `:has()` filter wiring + result count + reduced-motion.
6. **P0 spike (parallel):** `compute_implied_ranks()` → upgrade `.bchip` from archetype label to the
   numeric "Fans +N" gap; add the inline Tri-Rank `m·r·n` cell on desktop.
7. Verify (`§11`).

**Phase 2:** drawer (`render_tri_rank`, fingerprint via `savant_data_loader`, `season_arc_loader`,
momentum spark), `render_report_card`+`render_calibration_curve`, The Room module, dotplot+projection,
Compare tray, receipts. **Phase 3:** extract `dashboards/renderer.py`; bump scrollyteller; Rankings
Wrapped / Program Stripes; What-If sim.

---

## 11. Verification plan
- `python -u manage.py build-site` is green; `output/site/rankings/index.html` diff sane.
- Smoke: Top 25 present with **JS disabled** (curl + grep the team names) — proves SEO/no-JS.
- Lighthouse CI ≥95 on `/rankings/`; assert JS<50KB, no CLS.
- Grep guard: no literal hex/px in `rankings-board.css` outside `var(--…)`; no undefined chart import
  (CI already fails on non-vocabulary charts).
- Cross-link tests still pass (`tests/integration/test_cross_links.py`): flat `programs/<slug>.html`,
  `/assets/...` absolute.
- Visual: render at 390/768/1280; confirm `<details name>` exclusivity + shim path; confirm
  view-transition re-sort + reduced-motion no-op.

---

## 12. The honest delta (what makes this more than a reskin)
Phase 1 ships the **look + the board-first IA + the data we already compute** (Power/Résumé/SoS inline
ranks, Δ, logos, archetype belief, CFP cutline, SEO) on a **near-zero-JS** sheet — ~70% of the perceived
leap, low risk. The **moat** (numeric Tri-Rank, playoff projection, Model Report Card, fingerprint
drawer) is gated behind the P0 implied-rank spike and the projection/claims wiring — real work, named
here so it isn't mistaken for a render tweak.
