# Design polish — autonomous progress log

**Started:** 2026-05-22 (post-handoff)
**Audit source:** [docs/research/design-audit-2026-05-22-v2.md](design-audit-2026-05-22-v2.md)
**Production base URL:** https://wonderful-margulis-8ec96b-kevins-projects-9307a84f.vercel.app

## Done
(newest at top)

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
