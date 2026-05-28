# WS-01 — Foundation Unblock

**Phase:** 1 (Jun–Jul 2026)
**Owner:** Claude execution
**Status:** Ready to start

## Goal

Ship the mechanical fixes that gate every downstream workstream. None of WS-02 through WS-12 can proceed cleanly until these land.

## Definition of perfect

- Every `|| echo "skipped"` pattern in `.github/workflows/ingest_*.yml` replaced with loud-fail (adapter either writes ≥1 row or fails the workflow).
- Bucket label fix in `reddit_deep_2026_offseason.yml` merged + verified (one-token change: `"audience_bucket": "team"` → `"audience_bucket": "fan"`).
- `cohort_divergence` wired into `build_player_page_data_map` at `src/cfb_rankings/reporting.py:8198` mirroring the team-side call at `prompt_context/builders.py:1152`.
- `numeric_observations` table created via migration; 7 silent adapters (Wikipedia pageviews, Wikipedia edits, GDELT, SeatGeek, YouTube, Spotify, Kalshi, Bluesky) redirected to write to it.
- `team_coverage` table consolidates 6 cohort sources (PROFILED_SLUGS, priority_teams.yaml, TOP_ENTITIES_FULL/PARTIAL, BLUEBLOOD_PROGRAMS, STRUCTURAL_PRIMARIES) with publish_site producing byte-identical output before/after.
- All uncommitted Wave 25 + Milestone A+B + Player Wave-1 work committed in 2-3 logical PRs.

## Current state

- Bucket labels: every one of 8,005 `conversation_document_targets` rows is `audience_bucket='national'` (the default in `collect_reddit_watchlist`).
- `cohort_divergence`: never called from player builder; player chips render "Awaiting" even when data exists.
- `numeric_observations`: table doesn't exist; 7 adapters configured but silently failing.
- `team_coverage`: doesn't exist; 6 overlapping cohort sources scattered across YAML/Python/Markdown.
- Uncommitted work: Wave 25 perf, team-preview Milestone A+B, player-pages Wave-1 modules — all in working tree per memory notes.

## Dependencies

- **Blocks:** WS-02 (classification populators need clean cohort table), WS-05 (adapter target tables), WS-09 (calibration ledger needs cohort grouping)
- **Blocked by:** Nothing — Tier S work

## Implementation approach

1. **Commit uncommitted work first** — biggest risk to the project. Two PRs: (a) perf + data work, (b) UI work.
2. **Bucket label fix** — one-line YAML change + a migration to backfill 8,005 historical rows to their correct bucket (keyed on `source_name + source_channel`).
3. **`cohort_divergence` wiring** — ~30 lines added to `build_player_page_data_map` mirroring team-side pattern.
4. **`numeric_observations` migration** — single new table; 7 adapter files updated to use it.
5. **Loud-fail pattern** — refactor 8 workflow steps to capture adapter exit codes properly.
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
