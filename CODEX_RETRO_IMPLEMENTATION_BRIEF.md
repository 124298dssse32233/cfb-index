# Codex — Retro Offseason Magazine Implementation Brief

## Who you are on this task

You are the implementer. You already reviewed the plan adversarially (see your own review in chat + the three planning memos in `research/`). This brief incorporates every blocker and major you raised. Your job now is to build Phase A end-to-end and land Phase B behind it.

**You are implementing.** Write production code. Edit files under `src/cfb_rankings/`. Add new modules where this brief says to. Ship migrations. Wire CLI subcommands.

**You are not re-planning.** The ten-issue scaffold (N° 038–047), the editorial voice, the date window (Jan 19 → Apr 22, 2026), and the two-phase split are settled. Don't relitigate them.

**Ground rule for the entire task:** every number that reaches a rendered HTML page must be either (a) computed from live data joined to a specific `model_run_id` / `source_name` / `audience_bucket`, or (b) visibly tagged editorial or curated in the DOM, in the methodology row, and in the source column of the underlying row. No exceptions.

---

## What changed since your review

You flagged six items that have been accepted and folded into this brief. None of them are being argued with. They are:

1. **`power_ratings_weekly.power_rating`** — column name corrected in every SQL formula below.
2. **Provenance moved into Phase A.** The `source`, `sample_authors`, and `confidence` columns must land in `migrations.py` before any seed write. `hub_page.py` must render methodology rows off row data, not hard-coded strings.
3. **Rival Obsession Ratio needs pair keying.** Drop the proposed single `rival_mention_count` column. Introduce `team_week_rival_mentions(team_id, rival_team_id, season_year, week, mention_count, source_name, audience_bucket)` that feeds `rivalry_obsession_weekly.a_mentions_b_count` / `b_mentions_a_count` directly.
4. **Reality Gap must select a single latest model run.** Mirror the CTE in `_build_watchlist` (`src/cfb_rankings/ingest/conversation.py:625-635`). Enforce `classification = 'fbs'` on the team join.
5. **Shock Index must be volume-weighted + timezone-anchored.** Use `sum(mean_sentiment_score * mention_count) / sum(mention_count)` over daily rows, and convert `as_of_date` to an America/New_York-anchored bucket before comparing to event dates.
6. **Calibrate window widens to weeks 21–30.** Indiana Week 22/21 delta needs Week 21 baseline. Phase B backfills 21–30, not 22–30.

Your Opus/Sonnet/Haiku recommendations are adopted verbatim. See routing table at the bottom of this brief.

---

## Files to read before you touch code

Read these in order. Do not read `src/cfb_rankings/reporting.py` whole — it is 17.5k lines. Line ranges below are sufficient.

- `CLAUDE.md` — project orientation.
- `research/retro-offseason-execution-plan-2026-04-22.md` — canonical plan. This brief supersedes §"Revised formulas" and the new-columns list, but the issue scaffold and the Phase A / B split carry over unchanged.
- `research/retro-offseason-content-plan-2026-04-22.md` — editorial voice and event ledger. Treat event dates and scores as source of truth.
- `research/retro-offseason-accuracy-and-seeding-plan-2026-04-22.md` — context only; superseded in formula specifics.
- `src/cfb_rankings/migrations.py:992-1098` — Hub v5 tables (fanbase_mood_weekly, rivalry_obsession_weekly, lexicon_weekly, hub_issue_metadata). **You are adding ALTERs here.**
- `src/cfb_rankings/hub_page.py:270` (render_methodology_row), `:417`, `:597-602`, `:632-633`, `:828-829`, `:1016` — every hard-coded methodology string. All five non-header call sites need to accept data from the issue row.
- `src/cfb_rankings/fan_intelligence.py` (full) — constants at lines 31-32; `_cohesion_from_row` at :441-473. Do not change cohesion; Phase A reuses it on seeded rows via the existing `positive_doc_count` / `negative_doc_count` / `neutral_doc_count` triple.
- `src/cfb_rankings/ingest/conversation.py` — `_build_watchlist` CTE pattern at :615-660; `_build_daily_rows` at :980-1008; `build_conversation_features` pregame/postgame window at :498-515 (the season/week filter is surgical; offseason weeks with zero games produce zero game rows but still produce team-week rows — your §Pass 1 Q5 is confirmed true).
- `src/cfb_rankings/clients/reddit.py` (full, 194 lines) — the interface your Pullpush adapter must match, plus extra `before` / `after` params on `search_posts` and `list_subreddit`.
- `src/cfb_rankings/conversation_utils.py:530` — `score_sentiment` returns VADER compound in [-1, 1]. Do not rebuild a sentiment layer.
- `src/cfb_rankings/ingest/hub_data.py` (full, ~614 lines) — the file `hub_data_retro.py` mirrors, plus the three existing seed loaders you'll call through to.
- `src/cfb_rankings/cli.py:1276-1302` — the three compute commands that currently only run the seed path. You replace the fall-through in Phase B.
- `research/cfb-data-schema-sqlite.sql` lines 730-788, 1000-1021 — conversation tables, daily table, power_ratings_weekly.

---

## Revised formulas (implement exactly these)

All SQL is SQLite. Weekly queries assume `(season_year, week)` integer keys. Daily queries use the `team_conversation_daily.as_of_date` text column and must be timezone-normalized per Fix #5.

### Mood Index (`fanbase_mood_weekly.mood_score`)

```sql
case
  when twcf.mention_count < 12 then null
  when twcf.unique_author_count < 4 then null
  else cast(round(
    50 + 50 * twcf.mean_sentiment_score
       * min(1.0, twcf.mention_count / 50.0)
  ) as integer)
end as mood_score
```

Both gates are mandatory. The author gate mirrors `MIN_AUTHORS_FOR_SIGNAL = 4` from `fan_intelligence.py:32`. If either gate fails, write `source = 'editorial'` and fill `mood_score` from the seed dict; do not null-publish.

### Reality Gap (Belief − Power Rank percentile)

```sql
with latest_run as (
  select mr.model_run_id
  from model_runs mr
  where mr.season_year = :season
    and exists (select 1 from power_ratings_weekly pr where pr.model_run_id = mr.model_run_id)
  order by mr.week desc, mr.model_run_id desc
  limit 1
),
fbs_power as (
  select pr.team_id, pr.power_rating,
         percent_rank() over (order by pr.power_rating) as power_pct
  from power_ratings_weekly pr
  join teams t on t.team_id = pr.team_id
  where pr.model_run_id = (select model_run_id from latest_run)
    and t.classification = 'fbs'
)
-- join fbs_power to fanbase belief; gap = (belief_pct − power_pct)
```

FBS-only population. Single model run. Publish gap only when `count(fbs_power.*) >= 100`.

### Shock Index (volume-weighted window delta)

```sql
with window_rows as (
  -- daily rows in [event_date - 3, event_date - 1] vs [event_date, event_date + 3]
  -- as_of_date converted to America/New_York bucket before comparison
  select
    team_id,
    case when date_et < :event_date then 'pre' else 'post' end as phase,
    mean_sentiment_score,
    mention_count
  from team_conversation_daily_et  -- materialized view or subquery
  where team_id = :team_id
    and date_et between date(:event_date, '-3 days') and date(:event_date, '+3 days')
)
select
  phase,
  case when sum(mention_count) = 0 then null
       else sum(mean_sentiment_score * mention_count) / sum(mention_count)
  end as weighted_sentiment,
  sum(mention_count) as volume
from window_rows
group by phase
```

Publish Shock Index only when `pre.volume >= 20 AND post.volume >= 20`. The `date_et` conversion is a new helper in `src/cfb_rankings/ingest/conversation.py` (see Task B2).

### Rival Obsession Ratio

Produced by joining `team_week_rival_mentions` to itself on the inverse pair:

```sql
select
  a.team_id as team_a_id,
  b.team_id as team_b_id,
  a.mention_count as a_mentions_b_count,
  b.mention_count as b_mentions_a_count,
  cast(a.mention_count as real) / nullif(b.mention_count, 0) as ratio_a_over_b
from team_week_rival_mentions a
join team_week_rival_mentions b
  on a.team_id = b.rival_team_id
 and a.rival_team_id = b.team_id
 and a.season_year = b.season_year
 and a.week = b.week
where a.season_year = :season and a.week = :week
```

Publish only when both `mention_count` values ≥ 8. Below that, `source = 'editorial'`.

### Lexicon Spike

No change from the plan: week-over-week growth in `count(distinct conversation_document_id)` for the phrase, require prior 3 weeks of data with `≥ 5` mentions/wk baseline. Null the spike when rolling-window median volume drops ≥ 40% (Reddit outage guard).

---

## Phase A — seeded retro launch (ships this week)

### A1. Provenance migrations (**Opus**)

In `src/cfb_rankings/migrations.py`, add `migrate_vNN_retro_provenance()` that:

- `alter table fanbase_mood_weekly add column source text not null default 'computed'`
- `alter table fanbase_mood_weekly add column sample_authors integer not null default 0`
- `alter table fanbase_mood_weekly add column confidence real not null default 1.0`
- Same three ALTERs on `rivalry_obsession_weekly`, `lexicon_weekly`.
- `alter table hub_issue_metadata add column methodology_row_json text not null default '{}'` (stores the four parts that feed `render_methodology_row`).
- Create `team_week_rival_mentions` per §Revised formulas above, with unique index on `(team_id, rival_team_id, season_year, week, source_name, audience_bucket)`.
- Create retro-scope tables: `offseason_week_map`, `coaching_changes`, `portal_moves`, `spring_events`. Columns per the content plan.

### A2. Hub renderer honesty (**Opus**)

`src/cfb_rankings/hub_page.py` — replace the hard-coded string pairs at lines 417, 597-602, 632-633, 828-829, 1016 with `render_methodology_row(*issue["methodology"][section_key])`. `methodology` is loaded from `hub_issue_metadata.methodology_row_json`. Seeded rows pass strings like `"curated — 9 editorial sources"`, `"sample withheld"`, etc. Add a `data-provenance="editorial"` attribute on the section wrapper when any contributing row has `source != 'computed'`; CSS paints a pale-gold rule under the methodology row for editorial sections.

Also: edit the `hub-dek` string at `:608` (`"Confidence scores derived from 2.4M fan conversations..."`) to read off the issue metadata too. For retro issues the dek says `"Confidence scores curated from the official Jan-Apr event record."`.

### A3. Retro seed module (**Opus** — cross-cutting copy)

Create `src/cfb_rankings/ingest/hub_data_retro.py`. Mirrors `hub_data.py` structure. Nine `ISSUE_0XX` dicts (038–046) + reuses the existing 047. Each dict carries its own `methodology_row_json` payload stamped `source="editorial"`. Expose `seed_retro_mood_week`, `seed_retro_rivalry_week`, `seed_retro_lexicon_week`, `seed_retro_issue_metadata`. These call through to the existing loaders in `hub_data.py` but override the `source` column to `'editorial'`.

### A4. Retro render module (**Sonnet**)

Create `src/cfb_rankings/retro_render.py`. Thin wrapper over the existing Hub v5 renderers. Adds the retro-only nav element and the `data-retro="true"` class. Does not duplicate chart code.

### A5. Retro JSON ledgers (**Opus — copy; Sonnet — file scaffolding**)

Create `data/offseason/2026/events.json`, `coaching.json`, `portal.json`, `spring.json`. Schemas in the content plan. Every row carries a `sources[]` array of URLs. No event is added without at least one citation. Opus writes the row content; Sonnet does the scaffolding + JSON-schema lint.

### A6. CLI subcommands (**Sonnet**)

In `src/cfb_rankings/cli.py`, add:

- `seed-retro-issue --issue 038..047` — dispatches to the right `hub_data_retro.seed_*` calls for that issue.
- `seed-retro-all` — runs all ten in order.
- `build-retro-pages` — renders the ten retro issue URLs.

Do not change the existing `compute-mood-week` / `compute-rivalry-ratios` / `mine-lexicon` commands in Phase A. They remain seed-only until B2 lands.

### A7. SEO + indexing policy (**Sonnet**)

Add `<meta name="robots" content="noindex,follow">` to every retro issue page head until Phase B flips it. Add `<link rel="canonical">` pointing to the retro archive index, and a visible dateline banner reading `RETROACTIVE — reconstructed from the public record. See methodology.` on every retro page.

### Phase A acceptance criteria

- `pytest` passes.
- `python manage.py build-site` produces ten new issue pages with zero hard-coded `2.4M conversations` / `340K` strings surviving in the retro DOM (grep the output).
- Every `mood_score` / `delta_from_prev_week` / `ratio_dominant` in the ten retro issue rows has `source = 'editorial'`.
- `hub_issue_metadata.methodology_row_json` populated for all ten.

---

## Phase B — computed replacement (2–3 weeks out)

### B1. Pullpush adapter (**Sonnet**)

Create `src/cfb_rankings/clients/reddit_pullpush.py`. Class `PullpushClient` with the **same method signatures** as `RedditPublicClient`, plus explicit `after: int | None` and `before: int | None` Unix-second params on `search_posts` and `list_subreddit`. Backoff on 429. Log partial-window errors with subreddit + date range. No hidden state.

### B2. Compute-from-features branches (**Opus — SQL; Sonnet — Python glue**)

Replace the fall-through comment at `cli.py:1295-1302` with real queries against `team_week_conversation_features`. Create `src/cfb_rankings/ingest/hub_data_compute.py` with `compute_mood_week_from_features(db, week_start)`, `compute_rivalry_ratios_from_features(...)`, `compute_lexicon_spikes_from_features(...)`. Each writes to the same Hub v5 tables Phase A wrote to, with `source = 'computed'` and `sample_authors` populated from `twcf.unique_author_count`.

Add the ET timezone helper: `date_et(timestamp)` as a Python function that localizes UTC to `America/New_York` then ISO-formats the date. Expose a view `team_conversation_daily_et` (or compute the bucket inline in SQL).

### B3. Rival mentions pipeline (**Sonnet**)

Extend `build_conversation_features` to emit a second row set into `team_week_rival_mentions` whenever a post targets team A and mentions team B's regex (coach/QB/city/nickname aliases). Use the existing `conversation_document_targets` join; do not add a second pass over the raw Reddit JSON.

### B4. `retro-calibrate` subcommand (**Opus — thresholds; Sonnet — scaffolding**)

In `cli.py`, add `retro-calibrate --window 21..30`. Runs the ten directional checks from the execution plan. Each check prints `PASS` / `FAIL` / `INSUFFICIENT DATA` with the observed vs expected direction. Exit code 0 only if all ten are PASS or INSUFFICIENT DATA; any FAIL → exit 1.

### B5. Row-level provenance flip (**Opus**)

New helper `promote_row_to_computed(db, table, row_key, computed_value, confidence)` that:

- Writes the new value.
- Sets `source = 'computed'`.
- Writes an audit row into a new `hub_provenance_audit(audit_id, table_name, row_key_json, old_value_json, new_value_json, old_source, new_source, run_id, reason, changed_at)` table.
- Is reversible: `revert_row_to_editorial(...)` restores the last audit row's `old_value_json`.

Phase B promotion is per-row, not per-issue. If Indiana fails calibration but nine others pass, Indiana stays `editorial` and the other nine flip.

### B6. Cache / CDN invalidation (**Sonnet**)

Add a `--bust-cache` flag to `build-retro-pages` that writes a fingerprint (git sha + run id) into the page `<head>` and into `output/site/retro-manifest.json`. Downstream CDN purge is out of scope but the manifest is what the purge script will read.

### Phase B acceptance criteria

- `python manage.py compute-mood-week --week 2026-01-19 --no-from-seed` produces rows with `source = 'computed'`.
- `python manage.py retro-calibrate --window 21..30` exits 0.
- Indiana Week 22 Mood Index ≥ Indiana Week 21 Mood Index by ≥ 8 points (the ledger-anchored directional check).
- `hub_provenance_audit` has one row per flipped stat.
- Re-running `seed-retro-issue --issue 040` reverts that row via `revert_row_to_editorial`.

---

## Model routing

| Task | Model | Reason |
|---|---|---|
| A1 provenance migrations | Opus | Schema + data integrity; cross-table contract. |
| A2 hub renderer honesty | Opus | Cross-cutting copy + render contract. |
| A3 retro seed dicts | Opus | Editorial voice, must not imply computed backing. |
| A4 retro render module | Sonnet | Thin wrapper; boilerplate-heavy. |
| A5 JSON ledgers | Opus (copy) / Sonnet (scaffolding) | Factual copy needs Opus care; JSON schema is Sonnet-fine. |
| A6 CLI subcommands | Sonnet | Routine dispatch glue. |
| A7 SEO/robots | Sonnet | Mechanical. |
| B1 Pullpush adapter | Sonnet | Interface-matched HTTP client. |
| B2 compute branches | Opus (SQL) / Sonnet (Python) | SQL produces the numbers — Opus owns formula correctness. |
| B3 rival mentions pipeline | Sonnet | Extension of existing loop. |
| B4 retro-calibrate | Opus (thresholds) / Sonnet (scaffold) | Thresholds are where false PASS/FAIL hides. |
| B5 provenance flip | Opus | Reversibility + audit contract. |
| B6 cache manifest | Sonnet | Mechanical. |
| Verification sweeps | Haiku | Grep, file-existence, migration-up checks. |

---

## What you must not do

- Do not remove the `n = 2.4M conversations` string from non-retro issue code paths. Only the retro path reads methodology from row data; the live Issue N° 047 pipeline stays as-is this sprint.
- Do not change the `(season_year, week)` integer keying for conversation features or the `week_start_date` string keying for hub tables. The split is intentional.
- Do not touch `fan_intelligence.py` constants (`MIN_MENTIONS_FOR_SIGNAL`, `MIN_AUTHORS_FOR_SIGNAL`). Read from them.
- Do not rewrite `score_sentiment`. Consume its compound score.
- Do not commit a single retro page without `data-provenance` and the retro banner.

## Definition of done

Phase A ships when the ten retro issue URLs render under `output/site/hub/retro/`, every stat on every page has a visible provenance badge reading "Editorial" or "Curated", and `grep -r "2.4M conversations" output/site/hub/retro/` returns zero results. Phase B ships when `retro-calibrate --window 21..30` exits 0 and the provenance badges flip row-by-row to "Live" under audit.

---

*This brief incorporates the review by Codex dated 2026-04-22. Blockers and majors from that review are treated as accepted premises. If you find new blockers during implementation, stop and flag them in chat before writing more code.*
