# Claude Code — The Reaction Story (Sprint 15)

> **Inherits from `CLAUDE_CODE_AUTONOMY_AND_TOKEN_CONTRACT.md`.** Single sequential session. Concurrency-safe with Sprint 14 (Daily) and Sprint 16 (Mailbag) — disjoint module trees.

**Recommended model: Sonnet 4.6.**

**Target budget: ~50k tokens. Runtime: 1.5–2 hours.**

**Branch:** `sprint/15-reaction` (branch from current `master`).

**File ownership:**
- Create: `src/cfb_rankings/reactions/` (new module: `__init__.py`, `triggers.py`, `cohort_divergence.py`, `synthesizer.py`, `renderer.py`, `data.py`, `templates/reaction.html.j2`)
- Create: `migrations/20260426_15_reactions.sql` — schema for `reaction_stories` + `reaction_cohort_splits`
- Extend: `src/cfb_rankings/cli.py` at the documented merge zone (sprint 15 marker block) — register `reactions-check-triggers`, `generate-reaction`, `render-reactions`, `reactions-history`
- Read-only: every other sprint's module

---

## What this sprint ships

The Reaction Story — an **on-demand** content type that auto-fires when a Wire entry crosses a velocity threshold. It synthesizes the news event into a quantified reaction with **cohort divergence** as the proprietary spin.

The hook isn't "here's what happened." It's "here's what stat folks said vs casual fans vs die-hards — and what that split tells you about where the sport actually is on this." That divergence is the editorial product no one else has.

Lives at `/reactions/{slug}/index.html` per story + `/reactions/index.html` archive index.

---

## Phase 1 — Schema (~3k tokens)

`migrations/20260426_15_reactions.sql`:

```sql
-- Sprint 15: The Reaction Story — auto-triggered cohort divergence pieces

CREATE TABLE IF NOT EXISTS reaction_stories (
  slug              TEXT NOT NULL PRIMARY KEY,    -- e.g., 'arch-manning-leaves-texas'
  triggered_by_wire_id INTEGER NOT NULL,
  triggered_at_utc  TEXT NOT NULL,
  triggered_by_velocity REAL NOT NULL,
  primary_entity_slug TEXT NOT NULL,
  primary_entity_type TEXT NOT NULL CHECK(primary_entity_type IN ('team','player','coach','conference','event')),
  headline          TEXT NOT NULL,
  dek               TEXT NOT NULL,
  body              TEXT NOT NULL,
  surprise_index    REAL,                         -- 0–100
  status            TEXT NOT NULL CHECK(status IN ('draft','published','retired')),
  voice_validator_passed INTEGER NOT NULL DEFAULT 0,
  generation_model  TEXT,
  cited_sources_json TEXT NOT NULL,
  notes             TEXT,
  FOREIGN KEY (triggered_by_wire_id) REFERENCES wire_entries(id)
);

CREATE TABLE IF NOT EXISTS reaction_cohort_splits (
  story_slug   TEXT NOT NULL,
  cohort       TEXT NOT NULL CHECK(cohort IN ('stat_folks','casual_fans','die_hards')),
  stance       TEXT NOT NULL,                     -- one-line summary of cohort take
  representative_quotes_json TEXT NOT NULL,       -- 2–3 verbatim quotes with attribution
  sentiment_score REAL,                           -- -1..+1 cohort mean
  volume_share REAL,                              -- share of total mention volume
  PRIMARY KEY (story_slug, cohort),
  FOREIGN KEY (story_slug) REFERENCES reaction_stories(slug)
);

CREATE INDEX IF NOT EXISTS idx_reactions_entity
  ON reaction_stories(primary_entity_slug, primary_entity_type);
CREATE INDEX IF NOT EXISTS idx_reactions_published
  ON reaction_stories(status, triggered_at_utc DESC);
```

---

## Phase 2 — Trigger detection (Haiku, ~3k tokens)

`triggers.py` exposes `check_triggers(hours=24)`:

A Wire entry triggers a Reaction Story if any of:
1. `velocity_score >= 90` (top-decile of 30-day distribution)
2. Entity is a top-25 program / Heisman-tier player / power-conference coach AND velocity >= 75
3. Entity has 3+ Wire entries in last 6 hours (compounding signal)
4. Manual override via `--force-trigger <wire_id>`

If multiple triggers fire on the same primary entity within 12h, they compound into one story (don't re-fire).

Returns a list of `TriggerEvent(wire_id, primary_entity_slug, primary_entity_type, suggested_slug)`.

---

## Phase 3 — Cohort divergence extraction (Haiku, ~6k tokens)

`cohort_divergence.py` queries the conversation corpus for the 24h window around the trigger, partitions mentions by cohort signal:

- **Stat folks**: mentions where the source/author is in the analytics cohort registry, OR the text contains analytics markers (efficiency, EPA, success rate, percentile rank, advanced metric)
- **Casual fans**: general fan corpus minus the above two; default bucket
- **Die-hards**: mentions from program-board sources, sustained-engagement signals, vocabulary markers (program-internal nicknames, decade-spanning context)

For each cohort, extract:
- Mean sentiment (Haiku batch classifier — reuse Sprint 8.5's `sentiment_classifier`)
- Volume share
- Top 3 representative quotes (most-upvoted / most-cited in source corpus)

Return a `CohortDivergence` struct feeding Phase 4.

---

## Phase 4 — Story synthesis (Sonnet, ~25k tokens)

`synthesizer.py` calls `llm_runtime.run_with_voice_validator()` with:

```
You are writing a Reaction Story for {primary_entity_name} after {wire_event_summary}.

This is a Reaction Story — the editorial product is the COHORT DIVERGENCE, not the event recap.
Open by acknowledging the event briefly, then pivot HARD to: stat folks said X, casual fans said Y, die-hards said Z. Show why the split matters.

Audience: college football fans who follow closely. Voice: warm-fan-positioned, knowledgeable, acknowledges CFB's absurdity.

Required:
- 350–500 words
- Headline + dek + body (markdown body)
- Cite ≥3 named sources verbatim across the 3 cohort sections
- Each cohort section = 1 paragraph with 2–3 verbatim quotes
- End with: "What we're watching" — what the next 72h will tell us
- No banned phrases
- Use cohort labels naturally ("stat folks", "regular fans", "the boards") — never the internal taxonomy ("die-hard cohort")

Cohort divergence data:
{cohort_struct_with_quotes_and_sentiment}

Wire event:
{wire_entry_full}

Voice register references:
{three_canonical_voice_examples}
```

**Surprise Index calculation**: a numerical 0–100 derived from how unlikely the event was given prior signals (cross-references `predictive_claims` for prior consensus). High surprise (>75) gets a "← unlikely" callout in the rendered template.

**Voice validator gate**: same retry-once pattern as The Daily.

**Model routing**: Sonnet for body. Opus only on stories with `surprise_index >= 90` AND entity is blue-blood program / Heisman-tier player. Track Opus < 15%.

---

## Phase 5 — Renderer (~8k tokens)

`renderer.py` writes:
- `output/site/reactions/{slug}/index.html` — the story page
- `output/site/reactions/index.html` — archive index, last 50 stories

Layout (story page):
- Eyebrow: "Reaction Story · triggered {when} by {wire_event_link}"
- Headline (display serif), dek (sans serif)
- Surprise Index callout (if >= 75) — small chip "Surprise Index 87 ← unlikely"
- Body in 3 sections with cohort labels as subheads ("Stat folks said…", "Regular fans said…", "Die-hards said…")
- Quote pills inline with each cohort section
- "What we're watching" footer
- Sidebar: cohort sentiment three-up viz (mean sentiment per cohort) + volume share donut

Uses existing Edition typography + Pulse v2 cohort viz components. No new design tokens.

---

## Phase 6 — CLI subcommands (~2k tokens)

Register at sprint 15 merge zone:
- `reactions-check-triggers [--hours N] [--force-trigger WIRE_ID]` — runs Phase 2, prints triggered candidates, optionally auto-generates if `--auto`
- `generate-reaction --slug SLUG --wire-id ID` — runs Phases 3+4 for a known trigger, persists to DB
- `render-reactions [--slug SLUG]` — renders one or all
- `reactions-history [--limit N]` — prints recent stories

---

## Phase 7 — Backfill 3 representative stories (~3k tokens)

Pick 3 high-velocity Wire entries from the existing 110-entry corpus. Force-trigger each, generate the full story, render. This proves the pipeline and seeds the archive.

If the existing Wire corpus has nothing high-velocity (slow window), generate 3 anyway from the highest-velocity entries available — flag in the report that the trigger threshold may need tuning once live volume increases.

---

## Phase 8 — Self-verification

- 3 backfilled stories render cleanly
- Voice validator passes on all 3
- Each story cites ≥3 named sources across cohort sections
- Cohort sections are tonally distinct (Haiku check: each section's vocabulary distinct from the others)
- Archive index lists the 3 in reverse-chronological order

No GitHub Actions workflow this sprint — Reactions are on-demand, not scheduled. Triggers are checked daily by the Wire ingest cron (which already exists; sprint 14's daily cron will also call `reactions-check-triggers --hours 24 --auto` as a hook).

Add a one-line hook into the daily cron workflow YAML draft (the file Sprint 14 creates — coordinate via merge zone, NOT by editing the file directly during this sprint). Document the hook in the report so the integration sprint can wire it.

---

## Phase 9 — Sprint report (~1k tokens)

`output/sprint_reports/sprint-15-reactions.md`:
1. Phases completed
2. Token usage by model (Opus < 15%)
3. 3 backfilled stories with headline + cohort split summary
4. Trigger threshold initial values + tuning notes
5. Daily-cron hook snippet for integration
6. Files touched
7. Quality concerns
8. Natural next: live trigger monitoring after Wave 3 lands

Commit + push to `sprint/15-reaction`. Open PR.

---

## Decision authority

Autonomous on: trigger threshold initial values, cohort partition heuristics, Surprise Index formula, render template details, archive limit (50), retry semantics on validator failures.

Stop and flag only on the four canonical hard-blocker conditions.

---

## Report back with

1. Phase 1–9 completion status
2. 3 backfilled stories with cohort split previews
3. Voice validator pass rate
4. Token usage by model
5. Files touched
6. Daily-cron hook snippet
7. PR URL

Session complete after PR opens.
