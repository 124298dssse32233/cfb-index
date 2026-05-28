# WS-01 — Foundation Unblock

**Phase:** 1 (Jun–Jul 2026)
**Owner:** Claude execution
**Status:** Ready to start

## Goal

Ship the mechanical fixes that gate every downstream workstream. None of WS-02 through WS-12 can proceed cleanly until these land.

## Definition of perfect

- Every `|| echo "skipped"` pattern in `.github/workflows/ingest_*.yml` replaced with loud-fail (adapter either reports `ok`/`empty`/`skipped` with surfaced reason, or fails the step with `error`).
- Bucket label fix in `reddit_deep_2026_offseason.yml` merged + verified (one-token change: `"audience_bucket": "team"` → `"audience_bucket": "fan"`).
- `cohort_divergence` wired into `build_player_page_data_map` at `src/cfb_rankings/reporting.py:8198` mirroring the team-side call at `prompt_context/builders.py:1152`.
- ~~`numeric_observations` table created via migration~~ → **CORRECTED 2026-05-28:** `source_observations` (migration `20260423_01_source_observations.sql`) already IS this table. Its docstring names exactly the 7 adapters we need to write here, and all 7 already subclass `NumericSourceAdapter` (`src/cfb_rankings/ingest/sources/numeric_base.py`). The real gap: 6 of 7 wrote 0 rows historically because `set +e` + `echo "done"` in workflow steps swallowed failures. Action becomes: refactor `tools/run_adapter.py` to honor `AdapterRunResult.status` as a real exit code + drop `set +e` + run each adapter as its own step.
- `team_coverage` table consolidates 6 cohort sources (PROFILED_SLUGS, priority_teams.yaml, TOP_ENTITIES_FULL/PARTIAL, BLUEBLOOD_PROGRAMS, STRUCTURAL_PRIMARIES) with publish_site producing byte-identical output before/after.
- All uncommitted Wave 25 + Milestone A+B + Player Wave-1 work committed in 2-3 logical PRs.

## Current state

- Bucket labels: every one of 8,005 `conversation_document_targets` rows is `audience_bucket='national'` (the default in `collect_reddit_watchlist`).
- `cohort_divergence`: never called from player builder; player chips render "Awaiting" even when data exists.
- `source_observations`: table exists; only `polymarket` (160 rows) is writing. wiki_pv, wiki_edits, gdelt_volume, seatgeek, youtube_meta, spotify_charts, kalshi, bluesky_curated, bluesky_feeds all silently no-op or crash under `set +e`. Root cause TBD per adapter — likely a mix of (a) auth-gated adapters skipping when secret absent, (b) actual code/upstream bugs hidden by the swallow.
- `team_coverage`: doesn't exist; 6 overlapping cohort sources scattered across YAML/Python/Markdown.
- Uncommitted work: Wave 25 perf, team-preview Milestone A+B, player-pages Wave-1 modules — all in working tree per memory notes.

## Dependencies

- **Blocks:** WS-02 (classification populators need clean cohort table), WS-05 (adapter target tables), WS-09 (calibration ledger needs cohort grouping)
- **Blocked by:** Nothing — Tier S work

## Implementation approach

1. **Commit uncommitted work first** — biggest risk to the project. Two PRs: (a) perf + data work, (b) UI work.
2. **Bucket label fix** — one-line YAML change + a migration to backfill 8,005 historical rows to their correct bucket (keyed on `source_name + source_channel`).
3. **`cohort_divergence` wiring** — ~30 lines added to `build_player_page_data_map` mirroring team-side pattern.
4. ~~**`numeric_observations` migration**~~ — **CORRECTED 2026-05-28:** unnecessary; `source_observations` already exists and is wired. Step replaced by adapter triage (find why each of the 6 zero-row adapters is silent — secret absent vs. crash vs. upstream-empty).
5. **Loud-fail pattern** — refactor `tools/run_adapter.py` to honor `AdapterRunResult.status` as a real exit code (ok|empty→0, skipped→0+warn, error→1, config-missing→2). Then refactor the 3 ingest workflows: drop `set +e`, separate steps per adapter, `continue-on-error: true` only on auth-gated adapters that may legitimately skip without a secret.
6. **`team_coverage` migration** — new table + one-time backfill script + 6-file cleanup to query the table.

## Running gate

- Maiava's player page renders something non-"Awaiting" in at least 1 chip (Respect Gap or Reality Gap).
- `numeric_observations` has ≥100 rows from at least 4 distinct adapters within 24h of deploy.
- Freshness page shows every adapter's last-success timestamp.
- `team_coverage` is the only place teams get added; no Python file imports from the 6 old cohort sources.

## Decisions

- D-016 — `team_coverage` migration timing — OPEN. Recommendation: start in week 1.
- D-013 — Refuse list lock — OPEN. Doesn't block this WS but should be locked before scope creep starts.

## Pointers

- VISION § 8 (workstream table), § 11 (LLM stack)
- DECISIONS D-006 (6-bucket taxonomy), D-008 (doc structure)
- Memory: `project_team_preview_milestone_a.md`, `project_player_pages_wave_2026_05_27.md`
