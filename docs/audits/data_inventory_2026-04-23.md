# Data Inventory — 2026-04-23

**DB:** `cfb_rankings.db` · **Generated in:** 4.68s

This is the baseline snapshot taken at the start of the Autopilot v1 build. Every subsequent workstream should change these numbers. The "gap summary" at the bottom is the target list for the backfill work in W1 / W2 / W3 / W4.

## Per-table inventory

| Table | Rows | Date column | Min | Max | Season coverage | Top sources |
|---|---:|---|---|---|---|---|
| `players` | 46,668 | — | — | — | — | — |
| `player_aliases` | 0 | — | — | — | — | — |
| `player_game_stats` | 59,871 | season_year | 2025 | 2025 | 2022:0 · 2023:0 · 2024:0 · 2025:59,871 · 2026:0 | — |
| `player_honors` | 57 | season_year | 2014 | 2025 | 2022:5 · 2023:5 · 2024:5 · 2025:5 · 2026:0 · other:37 | official-heisman=57 |
| `player_recruiting_profiles` | 21,763 | season_year | 2019 | 2025 | 2022:2,368 · 2023:2,499 · 2024:2,745 · 2025:2,607 · 2026:0 · other:11,544 | — |
| `player_season_stats` | 165,999 | season_year | 2024 | 2025 | 2022:0 · 2023:0 · 2024:3,591 · 2025:162,408 · 2026:0 | — |
| `player_signal_events` | 0 | occurred_at | — | — | — | — |
| `player_source_ids` | 49,694 | — | — | — | — | cfbd=27,882, cfbd-recruit=21,812 |
| `player_usage_season` | 2,672 | season_year | 2025 | 2025 | 2022:0 · 2023:0 · 2024:0 · 2025:2,672 · 2026:0 | — |
| `player_value_metrics` | 683 | season_year | 2025 | 2025 | 2022:0 · 2023:0 · 2024:0 · 2025:683 · 2026:0 | — |
| `player_week_conversation_features` | 593 | season_year | 2025 | 2025 | 2022:0 · 2023:0 · 2024:0 · 2025:593 · 2026:0 | all=308, reddit=280, google_news_tulane=3, google_news_byu=1, google_news_boise-state=1 |
| `roster_entries` | 32,128 | season_year | 2024 | 2025 | 2022:0 · 2023:0 · 2024:16,221 · 2025:15,907 · 2026:0 | — |
| `roster_source_snapshots` | 31,822 | season_year | 2024 | 2025 | 2022:0 · 2023:0 · 2024:16,221 · 2025:15,601 · 2026:0 | cfbd=31,822 |
| `transfer_entries` | 14,422 | season_year | 2021 | 2025 | 2022:2,273 · 2023:2,502 · 2024:3,378 · 2025:4,499 · 2026:0 · other:1,770 | — |
| `portal_moves` | 0 | season_year | — | — | — | — |
| `teams` | 761 | — | — | — | — | — |
| `team_aliases` | 12,176 | — | — | — | 2022:3,044 · 2023:3,044 · 2024:3,044 · 2025:3,044 · 2026:0 | — |
| `team_brand` | 678 | — | — | — | — | — |
| `team_brand_assets` | 1,305 | — | — | — | — | cfbd=1,285, espn_cdn=20 |
| `team_cohort_divergence_week` | 1,822 | — | — | — | — | — |
| `team_cohort_week` | 21,864 | — | — | — | — | — |
| `team_conversation_daily` | 551 | observed_date | — | — | 2022:0 · 2023:0 · 2024:0 · 2025:551 · 2026:0 | reddit=551 |
| `team_game_advanced_stats` | 18,442 | season_year | — | — | — | — |
| `team_game_conversation_features` | 2 | season_year | 2025 | 2025 | 2022:0 · 2023:0 · 2024:0 · 2025:2 · 2026:0 | reddit=2 |
| `team_rating_deltas` | 271,924 | season_year | — | — | — | — |
| `team_seasons` | 4,648 | season_year | 2014 | 2025 | 2022:697 · 2023:703 · 2024:708 · 2025:699 · 2026:0 · other:1,841 | — |
| `team_talent_snapshots` | 960 | season_year | 2021 | 2025 | 2022:232 · 2023:237 · 2024:134 · 2025:134 · 2026:0 · other:223 | — |
| `team_week_conversation_features` | 100 | season_year | 2025 | 2025 | 2022:0 · 2023:0 · 2024:0 · 2025:100 · 2026:0 | reddit=100 |
| `team_week_rival_mentions` | 23 | season_year | 2025 | 2025 | 2022:0 · 2023:0 · 2024:0 · 2025:23 · 2026:0 | — |
| `conversation_collection_runs` | 268 | started_at | — | — | 2022:16 · 2023:16 · 2024:17 · 2025:219 · 2026:0 | reddit=268 |
| `conversation_document_targets` | 38,569 | season_year | 2016 | 2025 | 2022:4,104 · 2023:4,013 · 2024:5,797 · 2025:24,654 · 2026:0 · other:1 | — |
| `conversation_documents` | 21,188 | published_at_utc | — | — | — | reddit=11,762, locked_on_alabama=500, locked_on_byu=500, locked_on_florida-state=500, locked_on_georgia=500, locked_on_lsu=500, locked_on_miami=500, locked_on_michigan=500, locked_on_notre-dame=500, locked_on_ohio-state=500, locked_on_oregon=500, locked_on_penn-state=500, locked_on_tennessee=500, locked_on_texas=500, locked_on_kansas-state=427 |
| `conversation_raw_retention_audit` | 4 | checked_at | — | — | — | reddit=4 |
| `conversation_storylines` | 306 | season_year | 2025 | 2025 | 2022:0 · 2023:0 · 2024:0 · 2025:306 · 2026:0 | — |
| `game_line_snapshots` | 0 | snapshot_captured_at | — | — | — | — |
| `game_lines` | 10,252 | season_year | — | — | — | — |
| `game_predictions` | 26 | season_year | — | — | — | — |
| `heisman_market_odds_weekly` | 0 | — | — | — | — | — |
| `prediction_market_snapshots` | 0 | captured_at | — | — | — | — |
| `heisman_rankings_weekly` | 30,724 | — | — | — | 2022:0 · 2023:0 · 2024:0 · 2025:30,724 · 2026:0 | — |
| `heisman_vote_results` | 45 | season_year | 2014 | 2025 | 2022:4 · 2023:4 · 2024:4 · 2025:4 · 2026:0 · other:29 | — |
| `preseason_prior_components` | 4,039 | season_year | 2014 | 2025 | 2022:697 · 2023:703 · 2024:708 · 2025:699 · 2026:0 · other:1,232 | — |
| `opponent_adjusted_team_week` | 500,702 | season_year | 2014 | 2025 | 2022:80,668 · 2023:70,504 · 2024:86,674 · 2025:88,746 · 2026:0 · other:174,110 | — |
| `power_ratings_weekly` | 502,894 | season_year | 2014 | 2025 | 2022:62,101 · 2023:74,426 · 2024:78,105 · 2025:211,159 · 2026:0 · other:77,103 | — |
| `resume_ratings_weekly` | 452,883 | season_year | 2014 | 2025 | 2022:57,922 · 2023:69,513 · 2024:73,157 · 2025:181,171 · 2026:0 · other:71,120 | — |
| `strength_of_record_benchmarks` | 104,832 | season_year | — | — | — | — |
| `level_strength_weekly` | 244 | season_year | — | — | — | — |
| `conference_strength_weekly` | 3,789 | season_year | — | — | — | — |
| `returning_production` | 656 | season_year | 2021 | 2025 | 2022:130 · 2023:131 · 2024:133 · 2025:134 · 2026:0 · other:128 | — |
| `source_observations` | 41,092 | observed_at_utc | 2022-01-01T00:00:00Z | 2026-04-24T00:00:00Z | — | wiki_pv=33,033, wiki_edits=6,734, youtube_meta=1,147, gdelt_volume=168, polymarket=10 |
| `source_registry` | 209 | — | — | — | — | — |
| `scrape_health` | 178 | run_date | 2026-04-23 | 2026-04-24 | — | wiki_edits=2, wiki_pv=2, athletics_alabama=1, athletics_boise-state=1, athletics_byu=1, athletics_clemson=1, athletics_florida-state=1, athletics_georgia=1, athletics_howard=1, athletics_jackson-state=1, athletics_kansas-state=1, athletics_lsu=1, athletics_memphis=1, athletics_miami=1, athletics_michigan=1 |
| `fanbase_classification` | 2,592 | season_year | 2020 | 2026 | 2022:214 · 2023:214 · 2024:214 · 2025:761 · 2026:761 · other:428 | — |
| `fanbase_classification_history` | 2,592 | season_year | 2020 | 2026 | 2022:214 · 2023:214 · 2024:214 · 2025:761 · 2026:761 · other:428 | — |
| `fanbase_mood_weekly` | 62 | — | — | — | — | — |
| `hub_issue_metadata` | 10 | — | — | — | — | — |
| `hub_provenance_audit` | 181 | — | — | — | — | — |
| `lexicon_weekly` | 13 | — | — | — | — | — |
| `phrase_mentions_weekly` | 1 | — | — | — | 2022:0 · 2023:0 · 2024:0 · 2025:1 · 2026:0 | — |
| `rivalry_obsession_weekly` | 41 | — | — | — | — | — |
| `spring_events` | 0 | season_year | — | — | — | — |
| `games` | 23,185 | season_year | 2014 | 2025 | 2022:3,705 · 2023:3,733 · 2024:3,801 · 2025:3,830 · 2026:0 · other:8,116 | — |
| `drives` | 157,675 | season_year | — | — | — | — |
| `plays` | 1,142,755 | season_year | — | — | — | — |
| `game_source_ids` | 23,187 | — | — | — | — | cfbd=23,187 |
| `game_weather` | 14,711 | season_year | — | — | — | — |
| `coaching_changes` | 0 | announced_date | — | — | — | — |

## Gap summary — seasons missing per table

- `player_game_stats`: no rows for 2022, 2023, 2024, 2026
- `player_honors`: no rows for 2026
- `player_recruiting_profiles`: no rows for 2026
- `player_season_stats`: no rows for 2022, 2023, 2026
- `player_usage_season`: no rows for 2022, 2023, 2024, 2026
- `player_value_metrics`: no rows for 2022, 2023, 2024, 2026
- `player_week_conversation_features`: no rows for 2022, 2023, 2024, 2026
- `roster_entries`: no rows for 2022, 2023, 2026
- `roster_source_snapshots`: no rows for 2022, 2023, 2026
- `transfer_entries`: no rows for 2026
- `team_aliases`: no rows for 2026
- `team_conversation_daily`: no rows for 2022, 2023, 2024, 2026
- `team_game_conversation_features`: no rows for 2022, 2023, 2024, 2026
- `team_seasons`: no rows for 2026
- `team_talent_snapshots`: no rows for 2026
- `team_week_conversation_features`: no rows for 2022, 2023, 2024, 2026
- `team_week_rival_mentions`: no rows for 2022, 2023, 2024, 2026
- `conversation_collection_runs`: no rows for 2026
- `conversation_document_targets`: no rows for 2026
- `conversation_storylines`: no rows for 2022, 2023, 2024, 2026
- `heisman_rankings_weekly`: no rows for 2022, 2023, 2024, 2026
- `heisman_vote_results`: no rows for 2026
- `preseason_prior_components`: no rows for 2026
- `opponent_adjusted_team_week`: no rows for 2026
- `power_ratings_weekly`: no rows for 2026
- `resume_ratings_weekly`: no rows for 2026
- `returning_production`: no rows for 2026
- `phrase_mentions_weekly`: no rows for 2022, 2023, 2024, 2026
- `games`: no rows for 2026

## Autopilot backfill targets (derived from gaps)

- **W1 (CFBD deep backfill)** must fill: `player_game_stats`, `player_season_stats`, `player_value_metrics`, `player_usage_season`, `games`, `drives`, `plays`, `game_lines`, `game_predictions`, `opponent_adjusted_team_week`, `power_ratings_weekly`, `resume_ratings_weekly`, `returning_production`, `team_game_advanced_stats`, `team_talent_snapshots` for seasons missing rows above.
- **W2 (conversation corpus)** must fill `conversation_documents` and downstream `conversation_document_targets` + weekly features for 2022 / 2023 / 2024 / 2025 (offseason + in-season).
- **W3 (Tier-A numeric)** must fill `source_observations` with historical pageviews / market prices / article volumes for 2022-2025 where the API allows.
- **W4 (honors / awards / draft / NIL)** must fill `player_honors` for every honor scope 2022-2025, plus new tables `player_nfl_draft`, `player_draft_projection`, `player_nil_snapshot`.
