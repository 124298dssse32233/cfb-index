# Design polish — autonomous progress log

**Started:** 2026-05-22 (post-handoff)
**Audit source:** [docs/research/design-audit-2026-05-22-v2.md](design-audit-2026-05-22-v2.md)
**Production base URL:** https://wonderful-margulis-8ec96b-kevins-projects-9307a84f.vercel.app

## Done
(newest at top)

## In progress
- Phase A3 + A4 (the actually-broken Tier -1 items)

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
