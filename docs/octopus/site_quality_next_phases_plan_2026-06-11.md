# CFB Index — Next-Phases Plan (post-Session-2)

_Authored 2026-06-11 after Deploy 1 + Deploy 2 shipped. Planning only — no code changes._
_Companion to `site_quality_discover_2026-06-11.md`, `..._define_..md`, `..._progress_log.md`._

## Where we are (verified 2026-06-11)
**Live & done:** Phase 0 (reliability/truth), WP-0.2b (search wired + 2 indexer bugs), WP-1.4
(Polymarket), WP-3.2 (placeholder), WP-1.3 (Savant), WP-3.1 (player de-dup). All on `master`,
both deploys verified live.

**Remaining, grounded in the current DB (not stale notes):**
| Area | Verified state | 
|---|---|
| CFBD games | **2023 MISSING entirely**; 2020 (563) + 2022 (1,563) partial; 2024/2025 full; pre-2020 absent |
| player_game_stats | same gap — no 2023; 2022 partial |
| Play-by-play | `plays`=0, `drives`=0 — never ingested |
| Advanced stats | `team_game_advanced_stats` = **2025 only** (3,314); 3 metrics NULL at source |
| Receipts | `predictive_claims`=266 (no resolver, no `resolution_status` col); `prediction_ledger`=0; `editorial_citations`=0 |
| Identity/linkrot | `player_source_ids`=75,588 EXISTS; `_player_slug` supports `stable_id` but call sites don't pass it |
| Provenance | 22.3% canonical; legacy collectors still write NULL `source_id` (gap grows daily) |
| Frozen sections | `/canon/`, `/daily/` frozen 2026-04-26 — blocked on empty source tables |

## Prioritization principles (carried from the mission)
1. Exploit existing data before adding feeds; no new paid APIs / no CFBD-tier increase.
2. No live-game/scores/in-game work. **Finalized PBP retrospectively is allowed.**
3. Every DB-writing backfill runs **validate-on-copy first**, then merges supervised; never blind-mutate the live DB.
4. Receipts must be **human-in-the-loop** before any public exposure.
5. Design-quality floor for any UI: equal-or-better, reuse locked tokens/archetypes, a tie keeps the existing.
6. Each wave ends with a verified box build (`build_publish.ps1`) + deploy + live check.

## Sequenced plan

### Wave 0 — Data Health Spine (the assurance layer — DO FIRST)
**Kevin's ask (2026-06-12):** ongoing certainty that data is filled, healthy, gap-free, updating at the
desired cadence, and that the system reflects sources being added/removed.

**Why first:** the signal already exists but is scattered and un-surfaced — and recon found LIVE problems
nobody is being told about: `athletics_*` board sources erroring today, `gdelt_volume` failing, `podcast_asr`
not due until 2027, and three disagreeing source inventories (`scrape_health`=443, `source_registry`=84 active,
`collection_ledger`=10). This layer also *guides* Wave A (it names every gap) and *verifies* it (turns green
when 2023 lands). It's the meta-capability that would have caught the 2023 gap, dead search, offseason 404,
and empty Savant table automatically.

**Build on what exists — unify, don't duplicate:** `source_registry` (catalog + `is_active`), `scrape_health`
(per-run log), `collection_ledger` (`next_due_at`/failures), `audit-data-coverage`, `team_coverage`, and the
Session-2 guards (`verify_data_floors`, `verify_module_coverage`, `verify_build_manifest`).

**Components:**
1. **One declarative health spec** (`data_health_spec`), two parts:
   - *Sources* — DERIVED from `source_registry` (is_active=1) + a per-source **cadence SLA Kevin sets**
     (daily/weekly/monthly/seasonal). Auto-adapts: add a source → monitored; deactivate → shown "retired,"
     not "failing." No hand-maintained list.
   - *Datasets* — a small explicit list of spine datasets (games, player_game_stats, advanced_stats, ratings,
     PBP) with expected **season × team** coverage → gap detection (catches "games missing 2023; 2022 partial").
2. **One checker** (`manage.py data-health` / `verify_data_health.py`) — evaluates actual-vs-spec on 4
   dimensions, each green/yellow/red, writing a `data_health_report` JSON + a dated `data_health_snapshot`
   row for trends:
   - **Completeness** — expected seasons/teams present? (gap list)
   - **Freshness/Cadence** — each active source's last success within its SLA? (overdue/erroring list — would
     flag the `athletics_*` errors + `gdelt` failures TODAY)
   - **Volume/Integrity** — row floors held, no sudden drops (extends the ratchet)
   - **Provenance** — % canonical + trend
3. **One dashboard** — a Data Health page (internal methodology surface; reuse tokens + chart vocab):
   source status grid (ok / stale / error / retired), a **season × dataset coverage heatmap** (gaps pop
   visually), provenance trend, cadence adherence. Plus the CLI for the box. One page = the whole answer.
4. **Alerting** — on red, open a GitHub issue / push notification (reuse `notify_failure` + the
   `live_smoke_test` issue pattern). "Source X overdue," "games missing 2023," "provenance dropped 4pts."
5. **Source-change log** — when `source_registry.is_active` flips or a new `source_id` appears in
   `scrape_health`, log + surface the event ("+ Added X 2026-06-12 · − Retired Y"). Because the spec derives
   from the registry, add/remove flows through automatically.
6. **Cadence control** — Kevin sets desired cadence per source/dataset (config or `source_registry` field);
   the SLA check enforces it. "Updated at the pace I want" = configurable + enforced + alerted.

**Maps to the four asks:** filled/no-gaps → Completeness + coverage heatmap; healthy → Freshness +
Volume/Integrity (surfaces the live errors); cadence-you-want → per-source SLA + overdue alerts;
add/remove awareness → registry-derived spec + source-change log.

**Effort:** mostly unification + the spec/dashboard/alerting — 1–2 sessions. Reconcile the 3 source
inventories first (one authoritative list), then the checker, then the dashboard + alerts.

### Wave A — Data foundation (highest value: "use what we already pay for")
**A1. Backfill the 2023 season + patch 2020/2022** (games + player_game_stats).
- Commands exist: `backfill-cfbd-history`, `backfill-game-player-stats`, `ingest-cfbd-week`.
- Why first: a whole missing year silently weakens rankings, player careers, trajectories, "this day".
- Method: run against a DB copy → diff row counts + spot-check pages → merge → rebuild → deploy.
- Risk: medium (volume); fully reversible (additive rows by season).

**A2. Backfill `team_game_advanced_stats` for 2022–2024.**
- Synergy: ≥3 seasons → the Savant "Program history" peer set I gated **auto-returns** (no code change — the `_ALLTIME_MIN_SEASONS=3` threshold already handles it). Each team's card gains the 4th lens.
- Also re-check the 3 NULL metrics (finishing drives O/D, field position) — confirm CFBD genuinely omits them vs. an ingest-mapping gap; only then decide to add or leave at 10/13.

**A3. (Scoped) Play-by-play for 1–2 recent complete seasons.**
- `ingest-cfbd-pbp` + `compute-player-pbp-metrics` exist; `plays`/`drives` are empty.
- PBP is large — scope to 2024–2025 first, measure size/time, decide whether to go deeper.
- Payoff: deeper film-room retrospectives + richer player advanced metrics. **Retrospective only** (allowed).

**Cross-cutting (do alongside A): collect-path provenance fix** — make the legacy reddit/youtube/board
collectors stamp `source_id` so the 22.3% canonical share stops drifting down. Small, separate from build.

### Wave B — Identity & credibility
**B1. Canonical player identity / linkrot (WP-1.6).** Flip `_player_slug` call sites to prefer the
`stable_id` from `player_source_ids` (75,588 rows already present), and **write redirect files at the
legacy URLs** so existing bookmarks/search/Google entries don't break. Infra exists; this is wiring + a
migration + redirect emission. Removes the "player link 404s after re-ingest" class.

**B2. Receipts / predictions loop (WP-1.5).** Build a resolver matching the actual `predictive_claims`
schema (no `resolution_status` col today), populate `prediction_ledger`, render a "what we called / how it
turned out" surface. **Gate: human review of resolutions before anything public** (council ruling). Wire
the existing `prediction-ledger`/`resolve-outcomes`/`generate-best-calls`/`render-receipts` commands into
the box build only after the review gate is in place.

### Wave C — Transparency & polish
**C1. Data-quality dashboard (Phase 2).** Build on today's provenance labeling — a surface showing
per-source freshness, team coverage, historical depth, and provenance %. Reuse existing chart vocabulary;
honest "stale/insufficient" labels (no fake confidence).
**C2. Metric contracts / methodology pass (Phase 2).** Confirm every displayed metric is defensible +
documented; tighten any that aren't (the mission's "defensible, reproducible, qualified" bar).
**C3. Frontend polish (Phase 3 remainder).** Richer `/offseason/` + `/film-room/` content (they build now
but are thin); perf + a11y pass; **settle `player-standing`** (keep the deliberate dual presentation or drop
the mid-page card — a quick, isolated visual decision).

### Wave D — Source expansion (Phase 4, LAST per mission)
Only after existing data is fully exploited: the $0 four-pillar portfolio (Reddit RSS/archive, YouTube
comments, podcast ASR, boards/Bluesky/Threads) per `source-expansion-plan`. Ad-free Reddit rule, 138-team
seeds. Explicitly deferred until Waves A–C land.

## Recommended order & rough effort
1. **Wave 0 (Data Health Spine)** — 1–2 sessions. *Start here: the assurance layer Kevin asked for; surfaces live failures, names every gap, and verifies the backfills that follow.*
2. **Wave A1 (2023 backfill)** — 1 focused session. Biggest visible gap; the health spine confirms it goes green.
3. **Wave A2 (advanced-stats backfill)** — same/next session; lights up Savant all-time for free.
4. **Wave A3 (PBP, scoped)** + collect-path provenance — 1 session.
5. **Wave B1 (linkrot)** — 1 session (migration + redirects).
6. **Wave B2 (receipts)** — 1–2 sessions incl. the review gate.
7. **Wave C** — 1–2 sessions.
8. **Wave D** — separate initiative.

## Open decisions for Kevin (before Wave A)
- **PBP scope** (A3): just 2024–2025, or go deeper (storage/time tradeoff)?
- **Receipts exposure** (B2): internal-only first, or public "track record" surface once reviewed?
- **`player-standing`** (C3): keep both presentations or drop the mid-page card?
- **Backfill cadence**: one-time historical fill, or also wire a recurring "fill any missing season" guard?
