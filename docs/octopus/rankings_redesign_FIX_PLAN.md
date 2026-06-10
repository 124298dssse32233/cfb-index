# Rankings Redesign — Phase 1.1 Fix Plan

**Authored 2026-06-09.** Root-caused remediation for the live `/rankings/` board (deploy
`wonderful-margulis-8ec96b.vercel.app`). Every root cause below was verified against the shipped HTML/CSS/JS
and `reporting.py` source — file:line evidence included. **Plan only — not yet implemented.** The build window
owns the generator.

> **Verdict:** Phase 1 landed well — the light/Bebas system, the board DOM, lens tabs, filter facets, CFP
> cutline, finding banner, SEO `ItemList`, and (critically) the `.cfb-rkx` scoping that left team pages 100%
> untouched. Six issues make it read as unfinished. Two are P0. None are architectural — all are surgical.

## Diagnostics already run (so you can trust the root causes)
- Deployed server HTML, the shipped `cfb-tokens.css` / `rankings-board.css` / `rankings-board.js` (identical to repo source), and `reporting.py` source were all read directly.
- Team-page isolation **verified**: `/programs/alabama.html` → HTTP 200 with **zero** redesign CSS. Scoping is correct; don't touch it.
- Corrected two earlier guesses: `[data-board]` **does** match (it's on `<main class="sheet" data-board>`, reporting.py:16605), and Top-25 **filtering works** once JS runs — the visible failure is the **count**, not the filter.

---

## P0-A · Result count shows "Showing 0 of 0 teams"

- **Symptom:** the count reads "Showing 0 of 0 teams" although the board renders teams. Server HTML rendered the span as `668 teams` (`<span class="result-count" data-result-count>668 teams</span>`); the JS overwrote it with zeros.
- **Root cause (verified):** in `apply()` (`static_assets/js/rankings-board.js:215-241`), `shown`/`total` are computed **inside** the `transition(fn)` callback (226-239), but `transition()` calls `document.startViewTransition(fn)` (52-57), which runs `fn` **asynchronously**. `updateCount(shown, total)` is called **synchronously** right after (240) — before `fn` executes — so it reads `shown=total=0`. The format "Showing 0 of 0 teams" matches `updateCount`'s own template exactly (248), proving the JS ran with zeros. **The bug only appears in browsers with View Transitions (Chrome/Edge);** the no-VT fallback path runs `fn()` synchronously and counts correctly — consistent with you seeing it on desktop Chrome.
- **Fix (minimal, correct):** move `updateCount(shown, total)` to the **end of the `fn` callback** (after the loop + `toggleStructural`), so it runs after the counters are set.
- **Fix (better — also helps P1-E):** filtering visibility + counting are *state*, not animation. Do the `row.hidden`/count pass **synchronously**, and reserve `transition()` for the lens **reorder** only. Running a full View Transition over a 668-row board on every chip toggle is needless jank.
- **Acceptance:** initial load shows the real Top-25 count; every chip toggle updates "Showing N of M teams" correctly; verified in Chrome (VT on) and Firefox (VT off).
- **Effort:** ~10 min.

## P0-B · Every belief chip says "Awaiting signal" (the signature layer is dead)

- **Symptom:** all 668 chips render `bchip awaiting` "Awaiting signal", including blue-bloods. The masthead promises "what every fanbase thinks" and delivers the empty state everywhere.
- **Root cause (verified — it's an intentional stub, not a crash):** `render_rankings_page_html` sets `mood_index = mood_index or {}` (`reporting.py:16686`) and the build-site caller passes nothing, so `_mood_for(row)` returns `None` for every team and `_belief_chip(None)` emits the "Awaiting signal" fallback (`reporting.py:23183-23191`). The shipped comment says so verbatim: *"mood_index defaults to None → every belief chip reads 'Awaiting signal' for Phase 1"* (16684-16685). Note `_belief_chip` only emits `bchip align`+label or `awaiting` — never the `hot`/`cold` "Fans +N" variants (those need the net-new implied-rank spike).
- **Diagnose FIRST (one query):** does the deployed DB have 2025 fan-intel mention rows for a blue-blood (Alabama `team_id`)? ⚠️ A live check found `/hub/vibe-shifts` shows **no** belief signals either — the fan-intel data may be sparse/unpopulated in this snapshot.
  - **If data exists →** it's pure wiring (below).
  - **If absent →** run the fan-intel ingest for the 2025 season first; the wiring is moot until the data is there.
- **Fix (two parts):**
  1. **Populate `mood_index = {slug: mood}`** in the build-site caller and pass it into `render_rankings_page_html`. Build it from fan-intel keyed by team (RankingRow has both `team_id` and `slug`; `_mood_for` keys on `slug`). **Use a season-aggregate or the final in-season week of 2025 — not the offseason current week** (which is empty for everyone, the very reason all chips are awaiting). Loader: `fetch_team_mood_profile(db, team_id, season_year, week, context)` (`fan_intelligence.py:53`); floor `MIN_MENTIONS_FOR_SIGNAL=12` (`:33`).
  2. **Map mood → chip variant** in `_belief_chip`: emit the **archetype label** for teams with data (eng-spec's Phase-1 fallback), reserving "Awaiting signal" for genuinely sub-floor programs (small DII/DIII/NAIA — the *designed* use of that state).
- **Graceful-degradation guard:** if the whole board is signal-less (offseason with no data), **suppress the chip** or show a single board-level note rather than stamping 668 alarming "Awaiting signal" pills.
- **Acceptance:** Alabama / Ohio State / Georgia show a real archetype/belief; "Awaiting signal" appears only on true no-signal programs, not the Top 25.
- **Effort:** medium (data wiring + week/aggregate decision + DB verification). This is the highest-value UX fix.

## P1-C · No real team logos — every team is a 2-letter monogram

- **Symptom:** 0 `<img>` on the board, 1,336 `.fb` monograms; rows render `<span class="fb" style="…display:grid">IN</span>`.
- **Root cause (verified):** the renderer is **correct** — `_rankings_logo_markup` (`reporting.py:23136-23155`) emits `<img src="../{logo_path}" … onerror=show-monogram>` **when `team_logo_src(slug)` returns a path**. But `resolve_team_brand('alabama').logo_local_path` returns **`None`** and `output/site/assets/logos/` is **empty (0 files)** — the logo-localization step (manifest §2.4 / eng-spec §2, `import-team-logos` from CFBD) was **never run**. The `display:grid` inline style in the shipped HTML confirms the `logo_path`-is-empty branch fired for every team.
- **Fix:** run/implement logo localization so logos land in `output/site/assets/logos/<slug>.png` and `resolve_team_brand().logo_local_path` resolves. **No renderer change needed** — the `<img onerror=monogram>` fallback is already wired.
- **Acceptance:** `team_logo_src('alabama')` returns a path; the board shows real logos with the monogram only as the error fallback; `<img … loading="lazy">` already set, so no CLS once width/height are present.
- **Effort:** ops/data (download + slug mapping).

## P1-D · Sticky column header floats mid-list, overlapping row 3

- **Symptom:** the "RK · TEAM · CONF · POWER · BELIEF" header strip crashes through the Miami (#3) row.
- **Root cause (verified):** the sticky offsets were calibrated for the redesign's **own slim masthead** — `.cfb-rkx .lens{position:sticky;top:55px}` (`rankings-board.css:46`) and `.cfb-rkx .board-table thead th{position:sticky;top:104px}` (`:258`) assume a 55px masthead **inside** `.cfb-rkx`. But the page renders the **legacy global nav** above `.cfb-rkx` (the `.cfb-rkx .masthead` rule at `:28` is defined but never emitted), and that nav is a different (taller, two-tier) height — so the lens/colhead stick at the wrong viewport offset and overlap the list.
- **Fix:** tie the offsets to the real nav. Set a `--nav-h` (measured/known height of the legacy sticky header) and use `top:var(--nav-h)` for `.lens`, `top:calc(var(--nav-h) + var(--lens-h))` for `.colhead` and the table `thead`. **First confirm whether the legacy nav is itself `position:sticky`** — if it scrolls away, the board chrome should stick at `top:0`, not a fixed offset. (Alternative: adopt the slim `.cfb-rkx .masthead` and suppress the legacy nav on rankings — fixes this and P1-F together; see decision below.)
- **Acceptance:** the column header pins cleanly at the top edge at every scroll position and width (390/768/1280), never overlapping a row.
- **Effort:** small-medium.

## P1-E · Deep board not lazy — 1.75 MB, both representations fully inline

- **Symptom:** 1.75 MB HTML; **both** the card-feed (`.sheet` `.row` ×668) **and** the desktop `.board-table` are fully in the DOM; **no** `content-visibility`, no lazy deep board (all `0` in the markup).
- **Root cause:** the renderer emits all 668 rows in **two** representations and applies no `content-visibility` chunking / lazy deep board (manifest §6/§10 not implemented). ~20k+ nodes, all laid out.
- **Fix:** (a) add `content-visibility:auto; contain-intrinsic-size:<row-h>` to off-screen row chunks (per-conference `<tbody>` or rows beyond N); (b) reconsider shipping **both** card-feed and full table for all 668 — gate by media so only one set is in the DOM, or lazy-inject the table/deep board (rows 26→). Note this compounds P1-D (the dual render doubles `rowsFor()` and the count logic already has a half-written "de-dupe by halving" comment at js:245).
- **Acceptance:** lighter initial DOM; Lighthouse ≥95, INP<200ms, no CLS on the board.
- **Effort:** medium.

## P1-F · Masthead clutter + a malformed "·" button; redesign masthead absent

- **Symptom:** a two-tier legacy global nav + a floating "MENU" + a small black icon button rendering only a "·" (looks broken). The mockup's slim masthead/dateline didn't ship.
- **Root cause:** the redesign was scoped to `.cfb-rkx` (the board), so the page keeps the legacy global nav above it; the "·" is a global control rendering without its glyph/label.
- **Decision (resolves D + F together):**
  - **Option 1 — keep global nav:** fix the "·" button (missing icon/aria-label), tighten the nav, and recompute the sticky offsets (P1-D) to the nav height. Lower blast radius.
  - **Option 2 — adopt the slim `.cfb-rkx .masthead`** (brand + dateline, already in the CSS) and suppress the legacy nav on rankings. Matches the mockup, auto-fixes the sticky offsets, adds the missing dateline. Larger change.
  - **Recommendation:** Option 1 now (fast, unblocks D), Option 2 as a follow-up once the board is otherwise correct.
- **Acceptance:** one clean masthead, no broken button, dateline present (microcopy §5.6), sticky offsets correct.
- **Effort:** small (Option 1) / medium (Option 2).

## P2 · Polish (after the above)
- **#1 lead-row tint** renders as an odd band over the power/belief cells — verify `.cfb-rkx .row.lead .row-main` gradient (`rankings-board.css:80`) and the table variant (`:264`) against the grid columns.
- **Chip class drift:** shipped `.bchip.awaiting`; the component spec + `states.html` use `.bchip.signal`. I'll align the **spec** to the shipped `.awaiting` (doc-side) so they match — no code change.
- **Dateline/freshness** line absent — folds into the P1-F masthead decision.

---

## Recommended execution order
1. **P0-A** (count) — ~10-min JS fix, immediate visible win.
2. **P0-B** (belief) — diagnose the DB first, then wire `mood_index` with a season-aggregate. Biggest UX payoff.
3. **P1-C** (logos) — run localization; large visual lift, no renderer change.
4. **P1-D + P1-F** (sticky + masthead) — decide masthead ownership; the decision fixes both.
5. **P1-E** (perf/lazy) — `content-visibility` + stop dual-rendering all 668 rows.
6. **P2** polish.

Items 1, 3, 5, and the P1-D offset tweak are surgical (JS/CSS/ops). Item 2 is the only one needing model/data
work, and it's gated on the DB check. None require touching the `.cfb-rkx` scoping — that part is right.

## Verification (after fixes)
- Chrome + Firefox: count updates correctly on filter; Top-25 vs All divisions both correct.
- Alabama/Ohio State show a real belief, not "Awaiting signal."
- Real logos visible; monogram only on genuine error.
- Column header never overlaps a row at 390/768/1280; scroll tested.
- `python -u manage.py build-site` green; `tests/integration/test_cross_links.py` passes; Lighthouse ≥95, no CLS.
