# Design polish — autonomous progress log

**Started:** 2026-05-22 (post-handoff)
**Audit source:** [docs/research/design-audit-2026-05-22-v2.md](design-audit-2026-05-22-v2.md)
**Production base URL:** https://wonderful-margulis-8ec96b-kevins-projects-9307a84f.vercel.app

## Done
(newest at top)

### [2026-05-22 evening] Session 5 extended — copy scrubs + Dashboard mobile strip + player page meta-footer
- Commits: e8827d844a9, 0ee77130e19, 1f1e5a88cf4, 32d50d14f20, 14b1ce2860f, eda166524be
- **Player pages meta-footer adoption (17,836 surfaces)** — closes the largest single Profile-archetype surface
- **Dashboard archetype mobile thumb-zone filter strip primitive** — closes the last unshipped Dashboard zone per `30-page-archetypes.md`. Wired to /heisman/ and /rankings/, mobile-only via @media, no-JS.
- **Homepage placeholder text purge** — replaced "Issue XIX placeholder. Pattern C cover essay generation fills this in on next world_class_enrich" + sibling leaks on editions XVIII/XIX. Also fixed the upsert logic so the DB-resident placeholder rows get overwritten on re-seed (the missing symmetric Hotfix-13 protection).
- **Live-audit dev-vocab purge** — surfaced via WebFetch on /methodology/, /rankings/, /teams/alabama.html, /players/<slug>.html, and /hub/vibe-shifts/. 9 distinct fixes across methodology page, power/resume chart placeholder, rivalry-card meeting fallback, vibe-shifts source attribution, player honors/signature-moment/scenario-explorer/the-room empty states.
- **Hero-title defensive fallback** — `editorial_context` no-active-phase fallback hardcoded "this week" tense. Reframed as season-neutral, using the brand tagline.
- See [SESSION_5_FINAL_WRAP.md](../../SESSION_5_FINAL_WRAP.md) for full detail.

### [2026-05-22 PM] Session 5 — Profile meta-footer extended to 3 detail-page renderers (commit 9862081d504)
- `render_conference_page_html` (~80 surfaces), `render_program_page_html` (665 surfaces), `render_team_page_html` (~662 unprofiled team surfaces) — each gets a `profile-meta-footer` block above the global footer with methodology link + updated timestamp + sample-size pill. Purely additive.
- These three surfaces are the Profile-archetype "feels different from team_pages/renderer.py" cluster. The methodology footer is the first cross-renderer convention they now share with the profiled pages.
- **C1 verification:** grep for any remaining `<h2>Board Controls</h2>` or `<h2>Filter…</h2>` patterns returned zero hits. The 6 other `board-utility` blocks the v2 audit pointed at don't have their own h2 — they sit nested under data-section h2s like "History Explorer", "Program Explorer", which is correct hierarchy. C1 is fully closed (audit was over-counting).

### [2026-05-22 PM] Session 5 — Profile-archetype primitives scaffold + receipt-density audit
- **Receipt-density measurement** on 3 recent edition essays (2026-w17, -w18, -w19): 0 citation markers across ~2,265 words. Hard violation of `docs/design-system/32-receipt-pattern.md` (spec floor: ≥1 per 200 words ≈ 11 expected). Documented in `docs/research/design-audit-2026-05-22-v2.md` §"Discovered during session 5 execution" — not renderer-fixable; needs the cover-essay LLM pipeline to start emitting `<sup>` markers + populate `editorial_citations`.
- **Profile primitives scaffold landed:** new `src/cfb_rankings/profile/__init__.py` module exposing `render_awaiting_module`, `render_profile_identity_strip`, `render_module_grid_open/close`, `render_profile_meta_footer`. Modeled on existing `cfb_rankings.dashboards` scaffold pattern.
- **CSS support:** `_PROFILE_PRIMITIVES_CSS_BLOCK` appended to the global stylesheet via `_compose_global_css()`. Adds `.profile-awaiting`, `.profile-identity-strip`, `.profile-module-grid`, `.profile-meta-footer` rules. Deliberately scoped to new class names so legacy `.team-shell` / `.premium-team-grid` styling is unaffected.
- **Initial adopters:** `render_conferences_index_html` and `render_programs_index_html` in `reporting.py` now render a `profile-meta-footer` block just above the global footer. Purely additive — no removal of existing content. Demonstrates the primitive working in the legacy renderer.
- **What's still owed:** full Profile-archetype consolidation across 17,836 player pages + 665 program pages + ~662 unprofiled team pages + conference detail pages. Genuinely multi-week. Primitives are now available for that work.
- **Files:** `src/cfb_rankings/profile/__init__.py` (NEW), `src/cfb_rankings/reporting.py` (CSS block + 2 call-sites), `docs/research/design-audit-2026-05-22-v2.md` (new §), `docs/research/design-polish-progress.md` (this entry).

### [2026-05-22 04:55 UTC] commit 814e2d77178
- **Phase C partial:** filter-strip h2→h3 (Heisman + Rankings), Heisman hero finding zone, stale absolute Vercel URL fix in common/head_chrome.py
- **Files:** src/cfb_rankings/reporting.py, src/cfb_rankings/common/head_chrome.py
- **Deferred:** C3 (Dashboard methodology footers), H1 (brand tagline + /about/ page) — visual-judgment calls

### [2026-05-22 04:35 UTC] commit b54fcd3e3bb
- **Phase B:** 22+ offseason copy bugs gated on is_offseason() across 4 files
- **Clusters closed:** B1 (rankings), B2 (players ×17,836), B3 (hub vibe-shifts), B4 (conferences/compare/heisman), B5 (methodology/about-model), B6 (shared power-resume gap footer), B7 (homepage scenarios + players landing)
- **Files:** reporting.py, hub_page.py, players_landing.py, provenance/methodology_page.py

### [2026-05-22 04:15 UTC] commit ec29e3f1899
- **Phase A4:** add render_global_footer() to nav.py + wire into all reporting.py page wraps
- **Files:** src/cfb_rankings/nav.py (NEW helper), src/cfb_rankings/reporting.py (17 sites patched)
- **Affects:** 17,836 player pages, /rankings/, /teams/<unprofiled>, /programs/, /conferences/, /heisman/, /history/ all now have footer

## In progress
- Awaiting publish-site validation (run 26268986578 on commit 814e2d77178)

## Blocked / deferred
(items where I investigated and decided NOT to fix autonomously, with reasoning)

### A3 — Vercel empty 404 body — DEFERRED
Tried adding `routes` config to vercel.json, but Vercel rejects mixing `routes` (legacy v1) with `rewrites` (v2). Direct `/404.html` returns 200 with content, but unknown URLs return 404 + 0 bytes. This is a Vercel-platform behavior quirk that needs deeper investigation — possibly the `trailingSlash: true` interaction with auto-404. Reverted vercel.json to pre-attempt state.

**Fix path for a future session:** experimentally test (a) removing `trailingSlash: true`, (b) adding `cleanUrls: true`, or (c) migrating fully to legacy `routes` config. Each requires a publish-site cycle + verification, so out of scope for this autonomous pass.

### A1 + A2 — FALSE ALARMS in v2 audit (no fix needed, audit doc corrected)
- **A1 — `/conferences/<slug>`:** I probed `/conferences/sec.html`, `/conferences/big-ten.html` etc. and saw 404s. The real slug pattern from [reporting.py:12202 `_conference_slug`](src/cfb_rankings/reporting.py) is `{level_code}-{conference_name}`, so the actual URL is `/conferences/fbs-sec.html`. I verified 5 of these and they all return 200 with real content. The conferences index correctly links to these slugs (72 distinct hrefs on /conferences/). **No fix needed. Audit doc §D1 was wrong.**
- **A2 — `/players/nfl-pipeline/`:** I probed under `/players/` but the real URL is `/nfl-pipeline/` at root level. Verified 200. **No fix needed. Audit doc §D2 was wrong.**
- **Possible UX follow-up (separate, low priority):** add redirects from natural-guess URLs (`/conferences/sec.html`, `/players/nfl-pipeline/`) to the canonical ones. Not autonomous-grade work; defer.

## Smoke history
(append `python scripts/smoke_test_live.py` results after every push)
