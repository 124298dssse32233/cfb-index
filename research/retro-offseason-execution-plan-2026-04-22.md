# Retroactive Offseason — Execution Plan (Third Pass)

Research date: 2026-04-22
Supersedes the formula and new-code sections of:

- `research/retro-offseason-content-plan-2026-04-22.md`
- `research/retro-offseason-accuracy-and-seeding-plan-2026-04-22.md`

Editorial voice (the ten issue scaffold, the seed-vs-compute matrix, the calibration gate) from the earlier memos still stands. This pass tightens the formulas against the actual schema, lists every new code module explicitly, and separates what can ship this week from what requires a real build.

## What changed from the previous passes

Three corrections after verifying against the live codebase:

1. **Sentiment is already VADER-compound**, not a regex bucket count. `score_sentiment()` at `conversation_utils.py:530` returns a compound score in `[-1, 1]` plus emotion scores, and `team_week_conversation_features` already persists `mean_sentiment_score`, `net_sentiment_score`, `positive_doc_count`, `neutral_doc_count`, `negative_doc_count`, and six emotion shares. All formulas become SQL over those columns. The regex sentiment lexicon from the accuracy memo is obsolete; we only need a tiny CFB-slang patch layer (`cooked`, `him`, `stock up`, `bag`, `trust me`) on top of what VADER + meme detection already cover.
2. **The three "compute-*" CLI commands currently only run the seed path.** `compute-mood-week`, `compute-rivalry-ratios`, and `mine-lexicon` all fall through to `seed_mood_week` / `seed_rivalry_week` / `seed_lexicon_week`. A comment at `cli.py:1283` even says *"When live signal returns, replace this branch with a query over team_week_conversation_features."* So the compute path isn't a stub waiting on data — it is unwritten. Adding it is the core P1 task.
3. **The Reddit client is public-JSON + RSS fallback, unauthenticated.** No pagination past 1000, no date-bounded search. A Pullpush adapter is not optional for a true retro backfill — it is the only way to reach Jan 19 from April.

## Two-phase shipping

There are two distinct products here and they ship on different clocks:

### Phase A — Seeded retro series (can ship this week)

Ten retro hub issues (N° 038 → N° 046) published with **editorial-seed numbers** drawn from the curated event ledgers plus the formula outputs we *would* expect the live system to produce, tagged `source='editorial'` or `source='curated'` on every stat. No new scraper code required.

What this gets us:

- The full ten-issue magazine runway from championship Monday to today, on the site, clickable, in voice.
- A pager that ties them together and a homepage "Road From The Title Game" rail.
- Every team page gets its Mood History backfill populated — from the seed — so team pages stop reading "Awaiting Signal" for the retro window.
- Zero risk of shipping fabricated-looking computed numbers, because every number carries its provenance badge.

What this doesn't get us:

- Defensible *computed* numbers. A Michigan fan asking "where did −15 come from?" gets pointed at the Moore-presser editorial seed, not a SQL query.
- Discovery of novel lexicon phrases — we can only show phrases we seed.
- A real calibration pass, because there are no computed numbers to calibrate against.

### Phase B — Computed retro series (ships after P1 backfill)

Same ten issues, but with every `source='editorial'` / `source='seed-as-compute'` stat replaced by a `source='computed'` value pulled from a Pullpush-backfilled `team_week_conversation_features` table via the new `compute-*-from-features` CLI branches. This is the version that passes the calibration gate from the accuracy memo.

Phase B does not block Phase A. The recommended cadence:

1. Ship Phase A this week. Retro series is live, visibly tagged as editorial-seed.
2. Build Phase B over the next 2–3 weeks. When it passes calibration, publish a single "Audited" update that overwrites Phase A seed numbers with computed numbers. Provenance badges update from `editorial` to `computed`. Editorial copy referencing specific numbers gets rewritten if the computed values disagree.

## Revised formulas — SQL against existing columns

All column references are to `team_week_conversation_features` unless noted.

### Mood Index `M(t, w)` ∈ [0, 100]

```sql
select
  case
    when mention_count < 12 then null
    else round(50 + 50 * mean_sentiment_score * min(1.0, mention_count / 50.0))
  end as mood_score
from team_week_conversation_features
where season_year = :season and week = :week and team_id = :team
  and source_name = 'all' and audience_bucket = :bucket;
```

- `mean_sentiment_score` is already the mean VADER `compound` in `[-1, 1]`.
- `conf = min(1, mention_count / 50)` ramps the score toward 50 when the sample is thin — same effect as the accuracy memo, done with one column multiplication instead of a regex pipeline.
- Below the gate (`mention_count < 12`) returns NULL. The team renders "Awaiting Signal" exactly as the existing fallback path does.
- Clamp to `[10, 90]` in Python after the round (accuracy memo still holds — widen to `[5, 95]` for extreme-event weeks).

### Mood Delta `ΔM(t, w)`

```sql
select
  (this.mood_score - prev.mood_score) as mood_delta
from mood_scores this
join mood_scores prev
  on prev.team_id = this.team_id
  and prev.season_year = this.season_year
  and prev.week = this.week - 1
where this.team_id = :team and this.week = :week;
```

(where `mood_scores` is a CTE or view over the Mood Index formula above.)

### Reality Gap `RG(t, w)`

Percentile-rank of belief vs percentile-rank of power, within FBS, within the week:

```sql
with week_moods as (
  select team_id, mood_score,
    percent_rank() over (order by mood_score) as belief_pct
  from mood_scores where season_year = :season and week = :week
),
week_power as (
  select team_id, rating,
    percent_rank() over (order by rating) as power_pct
  from power_ratings_weekly prw
  join model_runs mr using (model_run_id)
  where mr.season_year = :season and prw.week = :week
)
select
  wm.team_id,
  100 * (wm.belief_pct - wp.power_pct) as gap
from week_moods wm join week_power wp on wp.team_id = wm.team_id;
```

Bucket by `gap` using the cutoffs already in `_reality_gap()` — no formula change there, just a new data source.

### Respect Gap `RSP(t, w)`

```sql
select
  fan.mood_score - nat.mood_score as respect_gap
from mood_scores fan
join mood_scores nat using (team_id, season_year, week)
where fan.audience_bucket = 'fan' and nat.audience_bucket = 'national'
  and fan.team_id = :team and fan.week = :week;
```

Requires both buckets above gate, NULL otherwise.

### Swing `SW(t, w)` — 8-week rolling σ

```sql
select team_id, week,
  stddev(mood_score) over (
    partition by team_id order by week rows between 7 preceding and current row
  ) as swing_sigma
from mood_scores
where season_year = :season;
```

SQLite doesn't expose `stddev` as a window function in all builds — implement in Python by pulling the 8-week series and computing `statistics.pstdev()`. Bucket thresholds unchanged from the accuracy memo.

### Cohesion `C(t, w)` — coach-attitude axis

Existing `_cohesion_from_row` already reads from a pro/anti-coach signal on the conversation row. The cleanest path is to add two new columns to `team_week_conversation_features` populated by a small regex pass inside `build_conversation_features`:

- `pro_coach_count INT` — docs matching a per-team pro-coach regex.
- `anti_coach_count INT` — docs matching a per-team anti-coach regex.

Then:

```sql
select team_id,
  case
    when (pro_coach_count + anti_coach_count) < 20 then null
    else case
      when min(pro_coach_count, anti_coach_count) * 1.0 /
           max(pro_coach_count, anti_coach_count) > 0.8 then 'Civil War'
      when ... > 0.5 then 'Split'
      when ... > 0.3 then 'Tense'
      else 'United'
    end
  end as cohesion_bucket
from team_week_conversation_features
where season_year = :season and week = :week and audience_bucket = 'fan';
```

The coach-alias regexes come from a new `data/coach_aliases.json` seeded per program per season.

### Rival Heat `RH(t, w)`

Same path: add `rival_mention_count INT` column populated at feature-build time by per-team rival-regex matching. Formula unchanged.

### Rivalry Obsession Ratio

Normalized by each side's volume, as in the accuracy memo. Implementation needs the new `rival_mention_count` column from Cohesion/Rival Heat plus a directional join per rivalry pair. Fully SQL; no new sentiment pass.

### Shock Index `S(event)`

Event-anchored mood delta using 3-day pre/post windows. The windows are computed over `team_conversation_daily` (which is already keyed by `as_of_date`):

```sql
with pre as (
  select avg(mean_sentiment_score) as pre_s, sum(mention_count) as pre_v
  from team_conversation_daily
  where team_id = :team
    and as_of_date between date(:event_date, '-3 days') and date(:event_date, '-1 day')
),
post as (
  select avg(mean_sentiment_score) as post_s, sum(mention_count) as post_v
  from team_conversation_daily
  where team_id = :team
    and as_of_date between :event_date and date(:event_date, '+2 days')
)
select
  round(40 * (post.post_s - pre.pre_s) *
        min(log(post.post_v * 1.0 / max(pre.pre_v, 1) + 1) / log(2), 3)) as shock_score
from pre, post;
```

Cap at ±30 in the Python wrapper.

### Lexicon Spike `spike_pct_wow`

For featured/tracked phrases, a new `phrase_mentions_weekly` table:

```
(season_year, week, phrase, subreddit, mention_count, ingested_at)
```

Populated at ingest time by a single regex scan over docs, keyed by a canonical phrase list. Spike% is a window function over weeks. Discovery pass (novel n-grams) is a separate job that surfaces candidates for editorial review — *not* auto-publish.

## New code map — every file and function

This is the full list of what needs to exist for both phases. Items marked **[A]** are Phase A only; **[B]** are Phase B only; **[A+B]** are shared.

### New files

| Path | Purpose | Phase |
|---|---|---|
| `data/offseason/2026/coaching_changes.json` | Curated carousel ledger, ~40 rows | A+B |
| `data/offseason/2026/portal_moves.json` | Top 75 portal moves | A+B |
| `data/offseason/2026/nfl_declarations.json` | Declare/return ledger, ~40 rows | A+B |
| `data/offseason/2026/spring_events.json` | Practice opens, pressers, spring games, ~30 rows | A+B |
| `data/offseason/2026/offseason_weeks.json` | 9-row week map (022→030, slugs, Monday anchors) | A+B |
| `data/coach_aliases.json` | Per-team HC regex + pro/anti coach tokens | B |
| `data/tracked_lexicon_phrases.json` | Seed phrase list for `phrase_mentions_weekly` | B |
| `src/cfb_rankings/ingest/hub_data_retro.py` | Nine `ISSUE_038..046` editorial seed dicts + `seed_retro_issue(db, week)` function | A |
| `src/cfb_rankings/ingest/offseason_events.py` | Loaders that read the four JSON ledgers into the new tables | A+B |
| `src/cfb_rankings/ingest/reddit_pullpush.py` | Pullpush.io adapter matching `RedditPublicClient` interface + `--from/--to` epoch bounds | B |
| `src/cfb_rankings/ingest/hub_data_compute.py` | `compute_mood_week_from_features`, `compute_rivalry_from_features`, `mine_lexicon_from_features` | B |
| `src/cfb_rankings/ingest/lexicon_discovery.py` | N-gram novelty pass over conversation_documents, writes to review queue | B |
| `src/cfb_rankings/retro_render.py` | `render_offseason_week(db, season, offseason_week)` + nav/pager helpers | A |

### New schema (one migration)

Append to `research/cfb-data-schema-sqlite.sql` and add to `migrations.py`:

```sql
-- A+B
create table if not exists offseason_week_map (
  season_year int not null,
  offseason_week int not null,
  week_start_date text not null,
  slug text not null,
  label text not null,
  model_week int,
  primary key (season_year, offseason_week)
);

create table if not exists coaching_changes (
  change_id integer primary key autoincrement,
  season_year int not null,
  change_date text not null,
  program_team_id int not null references teams(team_id),
  outgoing_coach text,
  incoming_coach text,
  change_type text not null,
  grade text,
  notes text,
  source_url text
);

create table if not exists portal_moves (
  move_id integer primary key autoincrement,
  season_year int not null,
  move_date text not null,
  player_name text not null,
  position text,
  from_team_id int references teams(team_id),
  to_team_id int references teams(team_id),
  composite_stars real,
  notes text,
  source_url text
);

create table if not exists nfl_declarations (
  declaration_id integer primary key autoincrement,
  season_year int not null,
  announce_date text not null,
  player_name text not null,
  team_id int not null references teams(team_id),
  decision text not null,
  projected_round int,
  source_url text
);

create table if not exists spring_events (
  spring_event_id integer primary key autoincrement,
  season_year int not null,
  event_date text not null,
  team_id int not null references teams(team_id),
  event_type text not null,
  headline text,
  qb1_read text,
  source_url text
);

-- B only (provenance + new compute columns)
alter table fanbase_mood_weekly       add column source text default 'editorial';
alter table fanbase_mood_weekly       add column bucket_used text default 'national';
alter table fanbase_mood_weekly       add column confidence real;
alter table rivalry_obsession_weekly  add column source text default 'editorial';
alter table lexicon_weekly            add column source text default 'editorial';
alter table team_week_conversation_features add column pro_coach_count int default 0;
alter table team_week_conversation_features add column anti_coach_count int default 0;
alter table team_week_conversation_features add column rival_mention_count int default 0;

create table if not exists phrase_mentions_weekly (
  id integer primary key autoincrement,
  season_year int not null,
  week int not null,
  week_start_date text not null,
  phrase text not null,
  subreddit text not null,
  mention_count int not null default 0,
  unique_author_count int,
  ingested_at text not null default current_timestamp,
  unique (season_year, week, phrase, subreddit)
);
```

### New CLI subcommands

Append to `cli.py`:

```
seed-offseason-weeks            --season 2025                                [A+B]
seed-offseason-events           --season 2025 --kind {carousel|portal|nfl|spring}  [A+B]
seed-hub-issue-retro            --season 2025 --week 22..30                  [A]
render-offseason-week           --season 2025 --week 22..30                  [A]
backfill-offseason-conversation --season 2025 --week 22 --from YYYY-MM-DD --to YYYY-MM-DD --subs ...  [B]
compute-mood-week               --week YYYY-MM-DD --from-features            [B] (extends existing)
compute-rivalry-ratios          --week YYYY-MM-DD --from-features            [B] (extends existing)
mine-lexicon                    --week YYYY-MM-DD --from-features            [B] (extends existing)
retro-calibrate                 --season 2025 --weeks 22..30                 [B]
```

### Modifications to existing files

| File | Change | Phase |
|---|---|---|
| `cli.py` | Add 7 new subparsers + dispatch arms; extend 3 existing to honor `--from-features` | A+B |
| `migrations.py` | Add the migration above to the ordered list | A+B |
| `reporting.py` | Add `render_offseason_week()` dispatch; nav tuple at 11717 adds "Offseason Archive"; homepage gets `The Road From The Title Game` rail | A |
| `fan_intelligence.py` | Extend `fetch_team_mood_profile` to pull offseason-week rows into the mood history timeline | A |
| `ingest/conversation.py` | Extend `build_conversation_features` to populate the three new count columns (`pro_coach_count`, `anti_coach_count`, `rival_mention_count`) via regex pass | B |
| `conversation_utils.py` | Add a small CFB-slang patch dict that augments `score_sentiment` output for tokens VADER misses (`cooked`, `him`, `stock up`, `bag`, `trust me`) | B |
| `hub_page.py` | Respect the `source` provenance column by rendering a badge ("Live" / "Seed" / "Editor") on every stat cell | A+B |

## Sequenced work plan

### Phase A (this week, ~1 engineering day)

1. Write the four JSON ledgers (`coaching_changes`, `portal_moves`, `nfl_declarations`, `spring_events`) + the week map. ~6 hours of manual curation against the cited sources.
2. Add the migration for the five new tables (`offseason_week_map`, `coaching_changes`, `portal_moves`, `nfl_declarations`, `spring_events`). No provenance or compute columns yet.
3. Write `ingest/offseason_events.py` loaders + `seed-offseason-weeks` / `seed-offseason-events` CLI arms.
4. Write `ingest/hub_data_retro.py` — nine `ISSUE_0XX` dicts modeled on the existing `ISSUE_047`. One-time editorial pass; use the cadence tables from `retro-offseason-content-plan-2026-04-22.md` as the cover-copy brief.
5. Write `retro_render.py` + the `render-offseason-week` CLI + nav tuple update + homepage rail. Reuse `hub_page.py` shell.
6. Run: `build-site`. Verify the ten issues render and the homepage rail appears.
7. Ship Phase A. Visible provenance badge on every stat: "Editor" for now.

### Phase B (next 2–3 weeks)

1. Build `reddit_pullpush.py` against Pullpush.io. Unit-test against known post IDs. Confirm rate-limit behavior.
2. Add the migration for the provenance columns + three count columns + `phrase_mentions_weekly`.
3. Extend `build_conversation_features` to populate `pro_coach_count`, `anti_coach_count`, `rival_mention_count`. Populate `coach_aliases.json` for the top ~60 FBS programs.
4. Extend `conversation_utils.score_sentiment` with the CFB-slang patch layer.
5. Write `backfill-offseason-conversation` — date-bounded Pullpush collection + existing feature-builder invocation.
6. Write `hub_data_compute.py` with the three `*_from_features` functions matching the SQL above. Wire up `--from-features` flags on the three existing `compute-*` CLI commands.
7. Write `retro-calibrate` with the 10 directional checks from the accuracy memo. This gate must pass before Phase B goes live.
8. Run the backfill for weeks 22–30. Run the three compute commands. Run calibrate. Iterate on regex / formula if any check fails.
9. Ship Phase B: replace seed rows with computed rows where available, keeping seed rows only where the computed path falls below the gate. Provenance badge flips from "Editor" to "Live" on every stat that clears the gate.

### Estimated budget

- Phase A: ~1 engineering day + ~6 hours of editorial curation.
- Phase B: ~2–3 engineering days + ~45 minutes wall-clock Pullpush backfill + ~$2 in Haiku (if the slang patch doesn't cover the last 5%).

## Explicit gate conditions

Phase A ships when:

- `python manage.py build-site` completes without errors.
- `output/site/offseason/2026/week-22-perfect-hoosiers.html` (through week-30) all exist.
- Homepage renders "The Road From The Title Game" rail with 9 cards.
- Every stat on every retro page has a visible provenance badge.
- No page renders a stat without a source tag.

Phase B ships when all of Phase A holds plus:

- `python manage.py retro-calibrate --season 2025 --weeks 22..30` passes all 10 directional checks.
- `sqlite3 cfb_rankings.db "select count(*) from team_week_conversation_features where season_year=2025 and week between 22 and 30 and mention_count >= 12;"` returns ≥ 200 (rough: 10 weeks × 25 teams clearing gate).
- `sqlite3 cfb_rankings.db "select count(*) from fanbase_mood_weekly where source='computed' and week_start_date between '2026-01-19' and '2026-04-13';"` ≥ 90 (nine retro weeks × ≥10 teams/week).
- The Issue 047 cover numbers (47,392, 2.6×, 94, −15) either verify against computed equivalents or get rewritten.

## One-line summary

**Phase A ships this week with ten fully-voiced retro issues in editorial-seed mode, honestly tagged. Phase B replaces the seeds with SQL-backed computed numbers once the Pullpush adapter and three `*_from_features` compute branches are built. Nothing hand-waved; every stat on every page has a provenance label users can see.**
