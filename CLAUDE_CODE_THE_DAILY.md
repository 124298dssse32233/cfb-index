# Claude Code — The Daily (Sprint 14)

> **Inherits from `CLAUDE_CODE_AUTONOMY_AND_TOKEN_CONTRACT.md`.** Single sequential session. Concurrency-safe with Sprint 15 (Reaction) and Sprint 16 (Mailbag) — disjoint module trees.

**Recommended model: Sonnet 4.6.**

**Target budget: ~55k tokens. Runtime: 1.5–2 hours.**

**Branch:** `sprint/14-daily` (branch from current `master`).

**File ownership:**
- Create: `src/cfb_rankings/daily/` (new module: `__init__.py`, `selector.py`, `synthesizer.py`, `renderer.py`, `data.py`, `templates/daily.html.j2`)
- Create: `migrations/20260426_14_daily.sql` — schema for `daily_editions` + `daily_takes` + `daily_inputs_snapshot`
- Extend: `src/cfb_rankings/cli.py` at the documented merge zone (sprint 14 marker block) — register `generate-daily`, `render-daily`, `daily-history`
- Read-only: every other sprint's module (storylines, canon, wire, receipts, team_pages, editions, conferences_pulse, the_room_renderer, llm_runtime)

---

## What this sprint ships

The Daily — a weekday morning digest published at 06:00 ET that synthesizes the prior 24 hours into **3 ranked takes**. Each take cites ≥2 named sources verbatim, runs through the voice validator, and lives at `/daily/index.html` (current) + `/daily/YYYY-MM-DD/` (archive).

The Daily is the **fan's first read of the day**. Voice register: warm-fan-positioned, knowledgeable, acknowledges CFB's absurdity. Not aloof-magazine. Not summary-roundup. Three opinionated takes ranked by *what fans actually moved on overnight*.

---

## Phase 1 — Schema + module scaffold (~5k tokens)

### 1.1 Migration

`migrations/20260426_14_daily.sql`:

```sql
-- Sprint 14: The Daily — morning digest tables

CREATE TABLE IF NOT EXISTS daily_editions (
  edition_date     TEXT NOT NULL PRIMARY KEY,  -- 'YYYY-MM-DD' ET
  generated_at_utc TEXT NOT NULL DEFAULT (datetime('now')),
  status           TEXT NOT NULL CHECK(status IN ('draft','published','retired')),
  voice_validator_passed INTEGER NOT NULL DEFAULT 0,
  generation_model TEXT,
  notes            TEXT
);

CREATE TABLE IF NOT EXISTS daily_takes (
  edition_date  TEXT NOT NULL,
  rank_position INTEGER NOT NULL CHECK(rank_position IN (1,2,3)),
  headline      TEXT NOT NULL,
  body          TEXT NOT NULL,
  primary_entity_slug TEXT,           -- e.g., 'alabama' or 'caleb-williams'
  primary_entity_type TEXT,           -- 'team' | 'player' | 'conference' | 'event'
  source_count  INTEGER NOT NULL,
  cited_sources_json TEXT NOT NULL,   -- ["The Athletic — Stewart Mandel", ...]
  fueled_by_json TEXT NOT NULL,       -- {"wire_ids":[...], "thread_ids":[...], "pulse_spikes":[...]}
  voice_validator_passed INTEGER NOT NULL DEFAULT 0,
  generation_model TEXT,
  PRIMARY KEY (edition_date, rank_position),
  FOREIGN KEY (edition_date) REFERENCES daily_editions(edition_date)
);

CREATE TABLE IF NOT EXISTS daily_inputs_snapshot (
  edition_date    TEXT NOT NULL PRIMARY KEY,
  wire_count      INTEGER NOT NULL,
  active_thread_count INTEGER NOT NULL,
  pulse_spike_count INTEGER NOT NULL,
  receipt_resolution_count INTEGER NOT NULL,
  inputs_json     TEXT NOT NULL,
  FOREIGN KEY (edition_date) REFERENCES daily_editions(edition_date)
);

CREATE INDEX IF NOT EXISTS idx_daily_takes_entity
  ON daily_takes(primary_entity_slug, primary_entity_type);
```

### 1.2 Module scaffold

`src/cfb_rankings/daily/__init__.py` exports: `select_inputs`, `synthesize_takes`, `render_daily`, `fetch_recent_editions`.

---

## Phase 2 — Input selector (Haiku, ~3k tokens)

`selector.py` reads the last 24h of:
- `wire_entries` ordered by `velocity_score DESC` — top 20
- `storyline_chapters` published in last 24h, plus `storyline_threads` with `last_chapter_at < 7d` and high engagement
- `team_pulse_cache` rows where mood delta vs 7d-trailing > 15 points OR volume spike > 2σ
- `predictive_claims` resolved in last 24h with `outcome_verdict='hit'` and `surprise_index >= 75`
- `conference_pulse_state` rows with theme volume change > 30%

Selector returns a structured `DailyInputBundle` with the candidates ranked by **fan-resonance score** = (velocity × recency_decay × cohort_breadth). Cohort breadth = does this affect stat folks AND casual fans AND die-hards, or is it niche?

Output: top 12 candidates feeding into Phase 3.

---

## Phase 3 — Take synthesis (Sonnet, ~30k tokens)

`synthesizer.py` calls `llm_runtime.run_with_voice_validator()` with:

**Prompt skeleton** (per take):
```
You are writing take #{rank} of 3 for The Daily, published {edition_date} at 06:00 ET.

The audience is college football fans who follow the sport closely — they read The Athletic, listen to Solid Verbal, lurk on the boards. They want fan-voice, not aloof-magazine voice.

The take must:
- Synthesize what fans moved on overnight in {focus_area}
- Cite ≥2 named sources verbatim with attribution
- Be 150–200 words
- Open with the take, not the setup
- End with a forward look (what to watch today/this week)
- Avoid banned phrases (validator will gate output)
- Acknowledge CFB's absurdity where warranted (no false-gravitas)

Inputs (last 24h):
{wire_excerpts_with_velocity}
{thread_chapter_excerpts}
{pulse_spikes}
{resolved_receipts}

Voice register references:
{three_canonical_voice_examples_from_prior_editions_or_briefs}
```

**Ranking logic**: take #1 = highest fan-resonance candidate. Take #2 = second-highest with cohort-divergence twist. Take #3 = "buried lede" — something quietly important the casual reader will miss without help.

**Tentpole-day escalation**: if `edition_date` is in `tentpole_calendar` (championship Saturday, signing day, Heisman week, CFP selection day, NFL Draft week 1), route take #1 to Opus. Otherwise all 3 = Sonnet. Keep Opus < 15% of total spend.

**Voice validator gate**: each take re-runs through `team_pages.voice_validator.validate_fan_voice`. If it fails, retry once with the violation noted in the prompt. If it fails twice, mark `voice_validator_passed=0` and persist anyway with a `notes` flag for review (per autonomy contract — don't loop indefinitely).

---

## Phase 4 — Renderer (~8k tokens)

`renderer.py` writes `output/site/daily/index.html` (today) and `output/site/daily/{date}/index.html` (archive).

Layout per the homepage v4 + Edition typographic system:
- Masthead: "The Daily — {long_date} — published 06:00 ET"
- Three takes stacked, each with: rank numeral, headline (display serif), 150–200 word body, source pills (chip per cited source), entity link (team/player/conference page)
- Footer: "Yesterday's takes" → links to last 5 daily editions
- Sidebar (desktop only): "What we're watching today" — 3 calendar bullets pulled from `tentpole_calendar`

Use the same Tailwind/CSS variables as Edition pages. No new design tokens.

The archive index at `output/site/daily/index.html` shows the most recent edition; a separate `output/site/daily/archive.html` lists last 30.

---

## Phase 5 — CLI subcommands (~2k tokens)

Register at the documented merge zone in `cli.py` under `# ---- sprint 14: daily ----`:

- `generate-daily [--date YYYY-MM-DD]` — defaults to today ET. Runs Phases 2+3, persists to DB.
- `render-daily [--date YYYY-MM-DD]` — renders HTML from persisted DB rows.
- `daily-history [--limit N]` — prints last N editions with status + take count.

Each subcommand registers alphabetically inside the sprint-14 marker block.

---

## Phase 6 — GitHub Actions workflow (~2k tokens)

Create `.github/workflows/the-daily-06am-et.yml`:

```yaml
name: The Daily — weekday 06:00 ET

on:
  schedule:
    - cron: '0 10 * * 1-5'  # 06:00 ET = 10:00 UTC (no DST handling for now)
  workflow_dispatch: {}

jobs:
  publish:
    if: false  # GUARD — disabled until first-live-cycle verification flips this
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -e .
      - run: python manage.py generate-daily
      - run: python manage.py render-daily
      - run: python manage.py build-site
        env: { ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }} }
      - run: |
          git config user.name "daily-cron"
          git config user.email "daily-cron@cfbindex.local"
          git add output/site/daily/
          git diff --cached --quiet || git commit -m "daily: $(date -u +%Y-%m-%d)"
          git push origin master
```

The `if: false` guard is critical — the cron is dormant until the first-live-cycle sprint flips it.

---

## Phase 7 — Backfill 5 representative editions (~5k tokens)

To prove the pipeline end-to-end, generate 5 historical editions for the past 5 weekdays. This populates the archive so the homepage Daily widget has something to link to.

```
python manage.py generate-daily --date 2026-04-21
python manage.py render-daily --date 2026-04-21
# repeat for 04-22, 04-23, 04-24, 04-25
```

If a date has thin inputs (slow news day), the Daily falls back to **3 takes anyway** — pulled from longer-arc threads, recent Pulse shifts, or aged-well receipts. The Daily never publishes empty.

---

## Phase 8 — Self-verification (no new tokens)

- All 5 backfilled editions render
- Voice validator passes on all 15 takes (5 editions × 3 takes)
- Each take cites ≥2 named sources
- No banned phrases in any rendered HTML
- Homepage's "From The Daily" widget (if present) reads from `daily_takes` not stub data
- `python manage.py daily-history --limit 10` prints clean

---

## Phase 9 — Sprint report (~1k tokens)

Write `output/sprint_reports/sprint-14-daily.md`:
1. Phases completed
2. Token usage by model (verify Opus < 15%)
3. Voice validator pass rate per edition
4. 5 backfilled editions list with take headlines
5. Workflow YAML path + guard status (should remain `if: false`)
6. Files touched
7. Quality concerns
8. Natural next: first-live-cycle verification will flip the cron guard

Commit + push to `sprint/14-daily`. Open PR `sprint/14-daily → master` with body summarizing the above.

---

## Decision authority

Autonomous on: input-bundle scoring weights, take ranking heuristic, tentpole-calendar membership, render template details, fallback logic when inputs are thin, GitHub Actions cron timezone choice (UTC, no DST for now).

Stop and flag only on the four canonical hard-blocker conditions.

---

## Report back with

1. Phases 1–9 completion status
2. 5 backfilled editions with take headlines
3. Voice validator pass rate
4. Token usage by model
5. Files touched
6. PR URL opened
7. Quality concerns

Session complete after PR opens. Kevin merges via UI.
