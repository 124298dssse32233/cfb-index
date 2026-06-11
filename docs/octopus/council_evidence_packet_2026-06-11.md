# Council Evidence Packet — CFB Index Site-Quality Plan (2026-06-11)

**You (council models) have NO repository, DB, terminal, or live-site access.** Every fact below was verified first-party by Claude Code against the live repo/DB/production today. **Your job is adversarial:** challenge assumptions, find risks, propose better sequencing or alternatives, flag where the plan could corrupt data, regress UX, or violate constraints. **Do NOT assert new repository facts** — you can't see the repo. Consensus is not evidence; Claude re-verifies anything you raise.

## Product
CFB Index: Python static-site generator → SQLite (`cfb_rankings.db`, 192 tables) → ~69k HTML pages → Vercel. College-football analytics + fan-intelligence. Box-first deploy (nightly local build → **full-snapshot** Vercel deploy; cloud cron retiring). Locked design system; team pages have a three-act structure; rankings use a Power-vs-Resume distinction. Both must be preserved.

## Hard constraints (non-negotiable)
- No live-game UI (scores/polling/win-prob/`games_live`).
- **No new recurring API/data-collection cost to the product** (one-time analysis spend is fine).
- No CFBD tier increase. No X/Twitter, paywalled recruiting, FB/IG/TikTok scraping, paid resellers. Reddit only via compliant public access; no scraping prohibited endpoints; no training on Reddit text.
- Never edit generated `output/site`. Never hand-edit DB (migrations/CLI only). Isolated branch. No prod deploy / destructive migration without explicit user approval.
- Preserve concepts; don't duplicate hubs/metrics. Design tie → keep existing.

## VERIFIED confirmed problems (evidence in parentheses)
1. **P0 /offseason/ + /film-room/ 404 in production.** Box deploy script `build_publish.ps1` never generates them; the retiring cloud workflow does. Box deploys are full snapshots → missing dirs clobbered. (curl 404; `output/site` lacks both dirs; grep of both build paths.)
2. **P0 No canonical build manifest.** `_build_manifest.json` is a counts stub. Box vs cloud paths build different hub sets (box adds today-in-history + the-room; cloud adds offseason+film-room).
3. **P0 Live smoke suite (32 URLs, fail-under 95%) omits offseason/film-room** → 404s never alarm.
4. **P1 Provenance:** 22.3% of 194,972 `conversation_documents` have a canonical `source_id` (gap = legacy reddit/youtube/board collectors).
5. **P1 Registry health is fake:** all 84 `source_registry` rows `is_active=1`; many collect 0 rows today (Kalshi/SeatGeek/Spotify empty; YT-comments + GDELT-tone stale since 05-13).
6. **P2 Receipts loop open:** 266 `predictive_claims` are 100% unresolved; `prediction_ledger`/`source_profiles`/`prediction_market_snapshots` empty. Risk: presenting unresolved claims as a track record.
7. **P2 Polymarket write-side bug:** `outcomePrices` stored as JSON-string `'["0.125","0.875"]'`; adapter does `float(outcomes[0])`→`float('[')`→dropped, so `source_observations` has 300 polymarket rows, **0 prob_yes**. Mitigated downstream (delusion reads raw payload defensively → 10 weekly rows). Low user impact.
8. **P3 Team Savant never computed** (`team_savant_weekly`=0; `refresh-savant` CLI exists, never run; needs 2025 advanced stats). Renders hidden when empty.
9. **P3 PBP empty** (`plays`/`drives`/`cfbd_pbp_*`=0) → player-advanced + savant depth blocked.
10. **P3 Historical depth thin:** advanced team stats = 2025 only; games/player-stats miss 2023 entirely.
11. **P4 Player pages double-render 6 modules** (peer-comparator, narrative-arc, scenario-explorer, splits, supporting-cast, player-standing ×2) — verified in generated QB page.
12. **P4 Live Signal Flow placeholder** ("Live signal pipeline placeholder…") always ships on player pages.

## Proposed plan (summary — full WPs in site_quality_define_2026-06-11.md)
- Phase 0: add offseason/film-room to box build; canonical route manifest both paths iterate; smoke+build assertions on every nav target; row-count/freshness/coverage/provenance guards; correct DATA_SOURCES doc from scrape_health; supersede stale AGENTS.md.
- Phase 1: verify CFBD endpoint/season access live → idempotent resumable backfills (incl. plays/drives) → run+auto-refresh Team Savant → fix Polymarket prob_yes parse → operationalize receipts resolution (only resolved claims ever shown) → canonical identity + linkrot tests + provenance reconstruction.
- Phase 2: metric contracts; fact/model/market/fan/editorial separation; internal data-quality dashboard; sentiment/relevance eval sets.
- Phase 3: consolidate the 6 duplicate player modules (single-render `v2 or legacy`); hide Live Signal Flow; strengthen /offseason/ + /film-room/ (retrospective, never live); payload/perf reduction; WCAG 2.2 AA + no-JS.
- Phase 4 (last): harden existing sources, then evaluate zero-cost expansion in priority order.

## Challenge these (the open questions)
1. Fix box build path for offseason/film-room, OR promote them to first-class `build-site` subcommands? (consistency vs blast radius vs the "build EVERY section or clobber" rule).
2. Backfill order: front-load plays/drives (heaviest, enables most) vs advanced team stats (more value per call) first?
3. Receipts auto-resolution: defensible off existing results data, or require human-in-the-loop before any public exposure?
4. Provenance: reconstruct `source_id` from `source_name`+`source_channel`, or just label legacy rows without inferring an id?
5. Player-module consolidation: per-concept which renderer (legacy vs v2) is stronger — what's the safe default if unsure? (constraint: design tie → keep existing.)

Also attack: anything in the plan that could (a) corrupt the rolling DB artifact, (b) regress UX/accessibility, (c) introduce recurring product cost, (d) present unverified predictions as accuracy, or (e) be sequenced wrong.
