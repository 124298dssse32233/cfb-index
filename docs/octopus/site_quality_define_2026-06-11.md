# CFB Index — Site-Quality Define (Phase 0→4 Implementation Manifest)

**Date:** 2026-06-11
**Author:** Claude Code · `/octo:embrace` Define phase
**Upstream evidence:** [site_quality_discover_2026-06-11.md](site_quality_discover_2026-06-11.md) (every WP cites a verified finding)
**Pinned constraints:** isolated branch only · no prod deploy without explicit approval · no migration without approval · **no new recurring API/data-collection cost to the product** (council/Discover API spend is fine; the *site* must not gain recurring spend) · preserve design system, three-act team pages, Power-vs-Resume · never edit `output/site` · never hand-edit DB (migrations/CLI only) · no live-game UI.

---

## A. Confirmed problems (carried from Discover §2)

| ID | Problem | Severity | Discover ref |
|---|---|---|---|
| CP-1 | `/offseason/` + `/film-room/` 404 in prod (box build path omits them; full-snapshot deploy clobbers) | **P0** | #1,#2,#14 |
| CP-2 | No canonical build manifest; box vs cloud paths diverge | **P0** | #2 |
| CP-3 | Smoke suite omits nav targets (offseason/film-room) | **P0** | #3 |
| CP-4 | 77.7% conversation docs lack `source_id` | P1 | #4 |
| CP-5 | `source_registry.is_active` ≠ health (all 84 active; many collect 0) | P1 | #5 |
| CP-6 | `DATA_SOURCES_EXPLAINED.md` overstates active/daily sources | P1 | §10 |
| CP-7 | 266 predictive claims 100% unresolved; ledger/profiles empty | P2 | #8,#9 |
| CP-8 | Polymarket `prob_yes` 0% persisted (write-side JSON-string bug) | P2 | #13 |
| CP-9 | Team Savant never computed (`team_savant_weekly`=0) | P3 | #7 |
| CP-10 | Plays/drives/PBP empty → player-advanced/savant depth blocked | P3 | #6 |
| CP-11 | Advanced stats 2025-only; 2023 hole in games/player stats | P3 | #10 |
| CP-12 | 6 duplicated player modules (peer/narrative/scenario/splits/supporting-cast/standing) | P4 | #11 |
| CP-13 | Live Signal Flow placeholder ships in live experience | P4 | #12 |

## B. Preserved concepts (do NOT redesign or duplicate)

Power vs Resume · team-page three-act structure · Fan Intelligence · Backometer · fanbase taxonomy · Lexicon · Discourse Atlas · Recruiting Footprint · Program Prestige · Season Standing · Ceiling/Base/Floor · Chronicle · Player Standing · Career Arc · Mirror Match · Supporting Cast · The Room · Receipts · locked design tokens / 6-archetype IA / 6-chart vocabulary. **Tie goes to the existing implementation.**

## C. Explicit exclusions (out of scope, this program)

Live scores/polling/in-game prediction/win-probability/`games_live` · X/Twitter, private Discords, paywalled recruiting, FB/IG/TikTok scraping, unauthorized comments APIs, paid resellers · any new recurring product API spend · CFBD tier increase · new hubs/metrics/taxonomies that duplicate existing concepts · redesigning polished surfaces for implementation convenience.

---

## D. Work packages

Each WP: **change · depends on · blast radius · acceptance test · rollback.** Sequenced by the prompt's phase order; do not start a lower phase while a higher one is incomplete.

### PHASE 0 — Reliability & truth (do first)

**WP-0.1 — Generate offseason + film-room in the box build path** *(CP-1)*
- Change: add `python scripts/build_offseason_leaderboards.py` + `python scripts/build_film_room.py` to `scripts/build_publish.ps1` alongside the existing storylines/wire/anniversary post-build block. *(Verified 2026-06-11: offseason reads `transfer_entries`/`team_rating_deltas`/`heisman_rankings_weekly` — all populated — and **never** references `portal_moves`; film-room reads `team_rating_deltas`+`heisman_rankings_weekly`. Both produce non-stub output today when run. No phantom empty-table guard needed.)*
- Depends: none. Blast radius: one PS1 script; adds 2 dirs to the snapshot.
- Acceptance: after a local `build_publish.ps1`, `output/site/offseason/index.html` and `film-room/index.html` exist and are non-stub; post-deploy both routes → 200.
- Rollback: revert the two added lines.

**WP-0.2 — Canonical build manifest** *(CP-2)*
- Change: a single `build_manifest` (JSON or Python module) listing **required routes + the command that produces each**. Both `build_publish.ps1` and `publish_site.yml` iterate it. Extend `_build_manifest.json` to record generated routes (not just counts).
- Depends: WP-0.1. Blast radius: build scripts + workflow; no page output change if list is correct.
- Acceptance: a `verify_build_manifest.py` asserts every required route has a file on disk post-build; box and workflow produce the identical route set.
- Rollback: keep manifest advisory (warn-only) until proven.

**WP-0.3 — Smoke + build assertions for nav targets** *(CP-3)*
- Change: add `/offseason/`, `/film-room/`, `/players/the-room.html` to `scripts/smoke_test_live.py`; add a build-time assertion that every `_site_nav()` target exists on disk before deploy.
- Depends: WP-0.1/0.2. Blast radius: smoke script + a build guard; could fail builds (intended).
- Acceptance: smoke list contains all nav targets; build aborts if a nav target is missing locally.
- Rollback: guard behind `--warn-only` flag.

**WP-0.4 — Build assertions: row-count / freshness / coverage / provenance regressions** *(CP-4,CP-5)*
- Change: extend the existing `verify_*` family with: required-table min-row baselines, freshness ceilings (e.g. conversation docs ≤ N days), expected team-coverage floor, and a provenance floor with a documented current baseline (22.3%, ratcheting up — never down).
- Depends: none. Blast radius: CI/build guards only.
- Acceptance: guards pass on current DB; deliberately stale/empty inputs fail them.
- Rollback: thresholds in one config; relax there.

**WP-0.5 — Correct `DATA_SOURCES_EXPLAINED.md` + supersede stale `AGENTS.md`** *(CP-6)*
- Change: regenerate the per-source status table from `scrape_health` (last run + rows>0) so it reflects measured reality (Kalshi/SeatGeek empty, YT-comments/GDELT-tone stale, Polymarket prob caveat). Refresh or explicitly supersede `AGENTS.md` (17-slug + pre-cutover deploy text).
- Depends: none. Blast radius: docs only.
- Acceptance: doc status matches a fresh `scrape_health` query; no "active/daily" claim contradicts measured 0-row/stale state.
- Rollback: docs revert.

### PHASE 1 — Maximize existing data

**WP-1.1 — CFBD endpoint + season access inventory** *(CP-11, gates all backfills)*
- Change: a read-only probe that enumerates which CFBD endpoints + seasons the current Patreon tier actually returns (fields included), written to `docs/octopus/cfbd_access_matrix_2026-06-11.md`. **No assumptions** — verify live before building any backfill.
- Depends: none. Blast radius: read-only API calls (existing key, no tier change).
- Acceptance: matrix lists per-endpoint status + sample fields; flags 2023 gap cause.
- Rollback: n/a (doc).

**WP-1.2 — Idempotent, resumable historical backfills** *(CP-10,CP-11)*
- Change: per-domain backfill scripts (advanced team stats, player game stats, rosters, recruiting, transfers, returning production, talent, betting lines, weather, coaches, draft, **plays/drives**) using `backfill_progress`/`collection_ledger` cursors; rate-limited; resumable. Build from the canonical box DB; **must not corrupt the rolling artifact.**
- Depends: WP-1.1. Blast radius: large (writes many rows) → behind migrations + dry-run + per-domain flags; run on a copy first.
- Acceptance: re-running is a no-op (idempotent); interrupt+resume completes; advanced stats gain ≥1 prior season; 2023 filled where CFBD allows.
- Rollback: each backfill writes to staged tables / is revertible via a documented `--revert`; DB `.bak` before each run (pattern already used: `*.pre-enrich.bak`).

**WP-1.3 — Populate + auto-refresh Team Savant** *(CP-9)*
- Change: run `refresh-savant --season 2025` (and prior seasons once WP-1.2 lands advanced stats); wire it into `build_publish.ps1` so it refreshes automatically. If inputs insufficient for a team, the card already hides — keep that.
- Depends: WP-1.2 (for historical), else runs on 2025 now. Blast radius: one table + one team-page module that's currently hidden.
- Acceptance: `team_savant_weekly` > 0 for profiled FBS teams; Savant card renders with real percentiles + sample sizes; teams below sample threshold stay hidden.
- Rollback: truncate `team_savant_weekly` → card auto-hides.

**WP-1.4 — Fix Polymarket `prob_yes` write-side parsing** *(CP-8)*
- Change: in `prediction_markets.py`, `json.loads` `outcomePrices` when it's a `str` before indexing (mirror `delusion.py`'s defensive parse). Add a unit test with the real string payload `'["0.125","0.875"]'`.
- Depends: none. Blast radius: one adapter; adds `prob_yes` rows to `source_observations` going forward (read side already robust → no regression).
- Acceptance: after a collect, `source_observations` has `prob_yes` rows; delusion output unchanged or improved; test passes.
- Rollback: revert adapter (read side keeps working off raw payload).

**WP-1.5 — Operationalize the receipts/calibration loop** *(CP-7)*
- Change: a claim-resolution job that resolves `predictive_claims` whose `outcome_window_end` has passed (using games/results), writes `prediction_ledger` + `source_profiles`, and computes calibration. **Gate:** never render an unresolved claim as a track record; only resolved+scored claims feed any public "accuracy" surface. Market signals require liquidity/freshness/sample gates before influencing public metrics.
- Depends: WP-1.2 (results data). Blast radius: new derived tables → new/optional Receipts surface; conditional render.
- Acceptance: resolved-claim count > 0; ledger populated; any receipts UI shows only resolved claims with confidence; unresolved claims never labeled "hit/miss".
- Rollback: leave tables empty → receipts surface stays hidden (current behavior).

**WP-1.6 — Canonical identity + linkrot tests** *(provenance integrity)*
- Change: tests asserting stable team/player/game/source identities across re-ingest (the player_id instability noted in memory `deploy-clobber-root-cause` is the linkrot risk); reconstruct `source_id` for reconstructable legacy docs (reddit/youtube/board via `source_name`+`source_channel`), label the rest.
- Depends: none. Blast radius: backfill UPDATEs on `conversation_documents` → migration + `.bak`.
- Acceptance: provenance coverage rises above the WP-0.4 baseline; identity tests green; no cross-source mis-attribution.
- Rollback: migration revert from `.bak`.

### PHASE 2 — Processing & methodology

**WP-2.1 — Metric contracts** — explicit contract (grain, population, denominator, season, freshness, min-sample, missing-data rule, confidence) per public metric; "Why this number" + freshness + receipt + confidence chips reusing the **existing** confidence-signaling system (`docs/design-system/33`). No academic bloat.
**WP-2.2 — Fact / model / market / fan / editorial separation** — structural + visual separation reusing existing tokens.
**WP-2.3 — Internal data-quality dashboard** — coverage, staleness, attribution, classifier drift, source failures, unresolved claims, derived-table regressions (internal route, not public).
**WP-2.4 — Model eval sets** — validate sentiment + relevance against maintained human-labeled sets (relevance soak already in flight per memory `relevance-status`); distinguish offseason baseline vs in-season.
(Phase 2 WPs depend on Phase 0/1 truth landing; specced now, sequenced later.)

### PHASE 3 — Product / dataviz / frontend

**WP-3.1 — Consolidate the 6 duplicated player modules** *(CP-12)* — apply the `new_*_html or legacy` single-render pattern (already used for mirror-match/coaching-lineage) to peer-comparator, narrative-arc, scenario-explorer, splits, supporting-cast, player-standing. Keep the stronger renderer per concept; verify side-by-side desktop/tablet/mobile before/after; reduces DOM + duplicate empty-states.
- Acceptance: each concept renders once; no visual regression vs current at 3 widths; payload shrinks; tests assert single `data-module` per concept.
- Rollback: revert template concatenation.

**WP-3.2 — Hide/remove Live Signal Flow placeholder** *(CP-13)* — gate `render_live_signal_flow` to emit nothing when no real signal (no live UI). Acceptance: placeholder absent from generated pages; layout intact. Rollback: restore call.

**WP-3.3 — `/offseason/` as the national discovery hub** — strengthen (not replace) using roster/recruiting/portal/returning-production/roster-reload data; reuse archetype + chart vocabulary. Depends WP-0.1.
**WP-3.4 — `/film-room/` as retrospective model-analysis + receipts** — never live UI; reuse receipt pattern. **Corrected 2026-06-11:** `build_film_room.py` reads `team_rating_deltas`+`heisman_rankings_weekly` and has **zero PBP dependency**, so the hub ships in **Gate A** (WP-0.1) today; a finalized-PBP retrospective is a *later enhancement*, not a precondition. Depends WP-0.1 only (PBP enhancement later depends WP-1.2).
**WP-3.5 — Payload/perf reduction** — dedupe inline CSS/JS, drop empty-module DOM, keep primary content server-rendered/crawlable; measure before/after on homepage, rankings, team, player, offseason, film-room. WCAG 2.2 AA / keyboard / focus / reduced-motion / honest empty states are release-blocking.

### PHASE 4 — Zero-cost source expansion (LAST)

Only after 0–3. First harden existing pipelines (Kalshi/SeatGeek empty, YT-comments/GDELT-tone stale). Then evaluate candidates by legal/ToS, unique gain, coverage, yield, signal quality, provenance, maintenance, processing cost, destination — in the prompt's priority order (YouTube Data API comments → per-team podcast RSS+local ASR → verified board RSS → expanded Bluesky → SB Nation RSS → Threads only post-approval → Reddit only with documented compliant basis). All must respect the **no recurring product spend** rule and the Reddit compliance rules. **Do not start until Phase 0–3 reliability/provenance/frontend work is complete.**

---

## E. Dependencies (critical path)

```
WP-0.1 ─┬─ WP-0.2 ─ WP-0.3 ─ WP-0.4 ─ WP-0.5         (Phase 0, unblocks deploy honesty)
        └─ WP-3.3 / WP-3.4 (hubs strengthen)
WP-1.1 ─ WP-1.2 ─┬─ WP-1.3 (savant historical)
                 ├─ WP-1.5 (predictive_claims resolver needs results)
                 └─ WP-3.4 PBP-retrospective ENHANCEMENT only (base film-room ships in Gate A)
WP-1.4 (independent)   WP-1.6 (independent)
Phase 2 ← needs Phase 0/1 truth   Phase 3 frontend ← independent of data except 3.3/3.4
Phase 4 ← ALL of 0–3
```

## F. Global acceptance gates (Deliver)

Focused + full test suites pass · clean canonical build with no manual patching · every nav target 200 in generated + live smoke · required modules have current data or hide honestly · no duplicate player modules / no live placeholders · backfills resumable+idempotent, artifact uncorrupted · coverage/module baselines enforceable · **no new product API spend** · user-facing changes pass side-by-side visual review at desktop/tablet/mobile (tie → keep existing) · before/after perf for homepage/rankings/team/player/offseason/film-room · a11y + no-JS primary-content checks · every shipped finding cites repo evidence (not model consensus).

## G. Rollback plan (program-level)

All work on `feature/site-quality-2026-06-11`; small reviewable commits per WP. DB-mutating WPs take a `.bak` first (existing `*.pre-*.bak` pattern) and ship a documented `--revert`. No prod deploy until explicit approval; deploys are full snapshots, so a bad build is rolled back by re-running the prior-good build or `vercel alias set` to the last good deploy. Build/smoke assertions are introduced warn-only first, then promoted to hard-fail once green.

## H. Open questions for the council (challenge these)

1. Is fixing the box build path (WP-0.1) the right move, or should offseason/film-room move into `build-site` proper as first-class `manage.py` subcommands (consistency vs blast radius)?
2. Backfill order — is plays/drives (heaviest, enables most) worth front-loading, or do advanced team stats give more value per API call first?
3. Receipts loop (WP-1.5): is auto-resolution defensible off the existing results data, or does it need a human-in-the-loop verdict step before any public exposure?
4. Provenance reconstruction (WP-1.6): is `source_name`+`source_channel`→`source_id` mapping defensible, or should legacy rows simply be labeled "legacy provenance" without backfilling an inferred id?
5. Player-module consolidation (WP-3.1): for each of the 6, which renderer (legacy vs v2) is actually stronger — needs a per-concept visual call, not a blanket rule.

---

## I. Council review & accepted revisions (2026-06-11)

Adversarial council run via `orchestrate.sh embrace-gate`. **Codex** (full review, artifact `embrace-gate-define-develop-1781210595.md`) + direct **Gemini** + **Qwen** passes (`_council_extra/`). Gate-internal Gemini/Claude failed (Windows wrapper). All three reviewers were given no repo access and **asserted no new repo facts** — so nothing required repo re-verification except the two override cases below, which I verified first-party.

### Tri-model consensus → ACCEPTED (folds into the WPs)

1. **Provenance: label, don't infer** *(amends WP-1.6)* — all three: inferring `source_id` from `source_name`+`source_channel` risks silent mis-attribution and would "permanently corrupt the audit trail." **Revision:** default = explicit `legacy_unverified` label; any inferred id is quarantined + confidence-scored, **never** written to the canonical `source_id` column without verification. Move the cheap **labeling** step into Phase 0 (truth), keep heavy reconstruction deferred.
2. **Backfill order: advanced team stats BEFORE plays/drives** *(amends WP-1.2)* — all three: prove the idempotent/resumable harness on lighter, higher-value-per-call data before the heaviest, corruption-prone PBP backfill. **Revision:** WP-1.2 runs advanced team stats first as the harness proof; plays/drives last.
3. **Receipts: human-in-the-loop before any public exposure** *(amends WP-1.5)* — all three. **Revision:** auto-resolution is **internal-only**; first ~100 resolutions manually audited to build a golden set; no public accuracy framing until claim→outcome matching is auditable + sampled. **Qwen cost catch:** resolution must use already-collected results data only — must **not** reactivate a paid/recurring collector (e.g. Kalshi) as a dependency (honors the no-recurring-cost rule).
4. **Module consolidation: metric-parity gate** *(amends WP-3.1)* — Codex "keep existing if unsure"; Gemini "v2 only if it has every field v1 has"; Qwen "v2 only on clear win." **Revision:** per concept, adopt v2 **only** if it passes a parity checklist (every legacy data field present + heading structure + duplicate-ID check + no-JS output + mobile reading order + WCAG 2.2 AA); otherwise keep legacy. Design tie → keep existing. *(Repo note: mirror-match/coaching-lineage already use the `v2 or legacy` single-render pattern — this extends a proven pattern, not a new renderer system, lowering Codex's stated risk.)*
5. **Build path: fix the box path + authoritative manifest; do NOT proliferate subcommands** *(confirms WP-0.1/0.2)* — Gemini "fix box path, consistency beats granularity"; Qwen "retain box parity, avoid new subcommands"; Codex "force both entrypoints through one route contract." **Revision:** WP-0.2 manifest is the **single authoritative** route inventory; divergent hardcoded hub calls are **replaced** by manifest iteration (not supplemented), and both paths **fail hard on drift**.

### New structural changes → ACCEPTED

6. **Split Phase 0 into Gate A + Gate B** *(Codex)* —
   - **Gate A — route parity:** WP-0.1 (box builds offseason/film-room) + WP-0.2 (authoritative manifest) + WP-0.3 (smoke + build assertion on every nav target).
   - **Gate B — deploy safety (NEW WP-0.6):** a **pre-deploy snapshot-completeness guard** that aborts the full-snapshot Vercel deploy if any manifest route/dir is absent. Directly addresses the clobber root cause; depends WP-0.2.
7. **Move provenance-labeling + registry-health semantics EARLIER** *(Gemini/Qwen)* — registry-health (WP-0.4/0.5) is already Phase 0. **Add WP-0.7 (provenance labeling)** to Phase 0: stamp legacy reddit/youtube/board rows `legacy_unverified` so backfills don't pump into a "leaky bucket." Define the `source_registry` status vocabulary (active / healthy / configured / temporarily-empty) as a product decision before any health dashboard (WP-2.3).
8. **Accessibility is cross-cutting, not Phase 3** *(Gemini/Qwen)* — WCAG 2.2 AA / keyboard / no-JS becomes a **release-blocking acceptance criterion on every frontend WP whenever it is touched** (WP-3.1, WP-3.2 especially), not a deferred phase.

### Repository verification OVERRIDES council caution

9. **Polymarket write-side fix (WP-1.4) — KEEP, do not freeze.** Codex urged freezing the write side; Gemini/Qwen cited the `prob_yes` bug as proof "your data is often wrong." **Verified override:** `source_observations` has **zero** `prob_yes` rows today (nothing to corrupt), and the only consumer (`delusion.py`) reads `raw_payload_json`, **not** the `value_numeric`/`prob_yes` column — so adding `prob_yes` rows is **purely additive and cannot affect any current surface**. The council's caution doesn't apply to the actual code path. WP-1.4 proceeds (with the real-string unit test). *Evidence: `SELECT metric,count(*) FROM source_observations WHERE source_id='polymarket'` → volume_usd only; `delusion.py:76-93` reads raw_payload_json.*

### Net council verdict
Codex = `REVISE` (not block); Gemini/Qwen = revise sequencing/guardrails. **No reviewer rejected a confirmed problem or a preserved concept.** All revisions tighten safety and reorder for failure-containment — none expand scope or add product cost. Plan is **GO with the §I revisions applied**, pending user approval to begin Phase 0 implementation.

---

## J. Independent Claude review (repo-grounded) — corrections folded in (2026-06-11)

Unlike the external council (no repo access), an **independent Claude reviewer with full repo/DB/live access** re-ran every headline query first-party. **It could not falsify a single confirmed finding** — all counts (194,972 / 22.3%; 84/84 active; 266 / 100% unresolved; adv-stats 2025-only; 300 polymarket / 0 prob_yes; team_savant=0; 6 duplicate modules; 350 ran / 118 zero) reproduced **exactly**. The Polymarket override was independently re-verified and **upheld** (0 existing prob_yes rows; `delusion.py:80` reads `raw_payload_json`, not `value_numeric`). It also empirically ran both hub scripts (gitignored output) → both produce non-stub HTML, confirming WP-0.1 is a clean two-line fix.

Two repo-verified corrections (I re-confirmed both myself before accepting):

- **J-1 — Build-path divergence is far broader than 3 hubs** *(amends WP-0.2; updates Discover §6).* The box omits ~15 cloud commands, incl. `prediction-ledger --action resolve` (`cli.py:7543`, `publish_site.yml:402-404`) and `backfill-edition-citations` (`publish_site.yml:441-443`). So `prediction_ledger`=0 and `editorial_citations`=0 share **CP-1's root cause** (producer exists, runs in cloud, box omits) — not "never built." **Revision:** WP-0.2's manifest must reconcile the **entire box-vs-cloud command set** (not just routes); add a build-command parity audit. Without it, Gate A/B fixes the visible 404s but leaves ledger/citations/award-watch/depth-chart un-refreshed on every box deploy.
- **J-2 — `/film-room/` has no PBP dependency** *(amends WP-3.4 + §E).* `build_film_room.py` reads `team_rating_deltas`+`heisman_rankings_weekly`; it ships in **Gate A**, not gated on WP-1.2. (Fixed above.)

Two clarifications:
- **J-3 — WP-1.5 resolver nuance:** for `prediction_ledger` (model calibration: archetypes/season-wins/Heisman) a resolver **already exists** (`resolve_due_predictions`, `cli.py:7543`) — it's a *wiring* problem (J-1), not a build-from-scratch. Only **`predictive_claims`** (266, LLM-extracted) genuinely needs a new resolver. WP-1.5 acceptance must name **which** claim space it measures (don't conflate).
- **J-4 — phantom guard removed:** WP-0.1's old `portal_moves` caution targeted code that doesn't reference that table (fixed above).

**Independent reviewer bottom line:** *"The Discover is accurate — I could not break any confirmed finding. The Define is safe to start at Gate A+B"* (WP-0.1 clean two-line fix, one-PS1 blast radius, trivial rollback, snapshot guard WP-0.6 addresses the clobber class), pending the J-1/J-2 corrections (now folded) and user approval.

— End of Define manifest (rev. 2 — council + independent-review folded) —
