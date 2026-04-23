# Fan Intelligence Build — Session Log

2026-04-22 | TASK 1.1 | Schema migration landed: `migrations/20260422_01_fanintel_schema.sql` creates `team_cohort_week`, `team_cohort_divergence_week`, `scrape_health`, `priority_teams`, `schema_migrations`; Python column additions in `cfb_rankings.migrations` extend `source_registry` (source_id/tier/cohort_weights/max_publication_form/etc.), add 10 provenance cols to `conversation_documents`, and add `sample_n/sample_window/confidence_floor/model_version` to the four named aggregates. New CLI `python manage.py apply-migrations`. `build-site` passes (668 team + 15939 player pages). | Repo is not a git repo — per-task commits blocked; awaiting Kevin's call on `git init` vs. skip-commits workflow.

---

# Player Page Data — Session Log

2026-04-22 | Git baseline | `git init` + expanded `.gitignore` (added `output/`, `*.db*`, `*.zip`, tmp_*/, _figma_v5_*/, .vendor/, backups/, etc.); initial commit `9d8250e` "initial: pre-player-data baseline" with 340 files, ~96MB .git pack (bulk = `design-ref/` 13MB + `assets/` 60MB binaries — acceptable). | None.
2026-04-22 | TASK A.0 | Data probe complete: `research/signature_story_data_inventory_2026-04-22.md`. **Key finding: no PBP tables exist in cfb_rankings.db** — kickoff's named metrics (EPA/dropback-under-pressure, CPOE, pressure-to-sack, 3rd-down EPA, red-zone TD%) are NOT computable. Achievable QB v1 pool: 10 metrics centered on CFBD WEPA (`player_value_metrics.wepa_passing`, 191 QBs in 2025) + QBR + traditional passing rates + usage splits. CJ Carr fixture confirmed (player_id=4788, wepa_passing=0.41 / 307 plays). Haiku verification: all quantitative claims correct; clarified walk-on fixture text after Haiku flagged ambiguity. | Follow-up ticket: "Ingest CFBD pbp_data to enable situational Signature Story v2." A.1 seed file will use achievable pool only.
