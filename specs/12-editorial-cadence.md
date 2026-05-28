# WS-12 — Editorial Cadence

**Phase:** Continuous
**Owner:** Editorial + Claude assistance
**Status:** Partial (running but slipping)

## Goal

Sustained editorial cadence across all surfaces with voice enforcement and receipt discipline. Editorial output is the moat; cadence is the discipline.

## Definition of perfect

- Wire publishes daily, no skipped days in-season. Documented offseason cadence (e.g., M/W/F).
- Mailbag publishes weekly.
- Storyline chapters publish bi-weekly minimum during offseason, weekly in-season.
- Voice-validator passes on 100% of published copy. Per-team `never_use` lists enforced.
- Receipt density ≥1/200 words on 100% of editorial pages.
- Chronicle pipeline T0/T1/T2/T3/T-S tier cards generated weekly for all eligible entities (post-Phase 1 evidence diversification).
- Data-driven storyline candidate queue surfaces under-covered narratives for editor review weekly.
- Cadence dashboard surfaces "what's overdue" — chapters >14 days stale, Wires missed, Mailbag overdue.

## Current state

- Wire daily, Mailbag weekly, Daily — running on cron (verified live per LAUNCH_ROADMAP).
- 8 active storyline threads with 32 total chapters. Latest chapter additions 2026-04-21 through 2026-04-23 (over a month stale at time of writing).
- Voice-validator runs on Chronicle output. Doesn't run on other editorial surfaces.
- Receipt pattern enforced on Chronicle. Not consistently on Wire or Mailbag.
- No storyline candidate queue.

## Dependencies

- **Blocks:** Nothing technically; enables the "library not magazine" framing
- **Blocked by:** WS-02 (transition events → storyline candidates), WS-03 (profile expansion for voice consistency), Voice LoRA training (per D-014)

## Implementation approach

1. Build cadence dashboard: shows last-published timestamp per surface + threshold per surface. Flags stale items.
2. Add Wire + Mailbag + storyline chapters to voice_validator enforcement at write time.
3. Extend receipt-pattern enforcement to every editorial surface, not just Chronicle. Build-time check fails if density <1/200.
4. Build storyline candidate queue. Triggers: 3+ archetype transitions same week, season_narrative_arc opened without storyline coverage, coaching change at top-50 program, top-10 portal/recruiting class, etc.
5. Editorial review cadence: Sunday morning, editor reviews candidate queue + queues chapters for the week.
6. Closure mechanics for storyline threads: add `inactive` status + explicit "this thread is closed because X" final chapter when applicable.

## Running gate

- Wire publishes on schedule for 30 consecutive days.
- All 8 active storyline threads have had a chapter within the last 14 days.
- 100% of published copy passes voice_validator.
- 100% of editorial pages have ≥1/200 word receipt density.
- Storyline candidate queue has ≥3 candidates each Sunday.

## Decisions

- D-014 — Voice LoRA: how many adapters — OPEN

## Pointers

- `src/cfb_rankings/wire/` (Wire pipeline)
- `src/cfb_rankings/mailbag/` (Mailbag pipeline)
- `src/cfb_rankings/storylines/` (storyline system)
- `src/cfb_rankings/team_pages/state_resolver.py` — `_DOW_LABEL` + `_MONTH_TO_PHASE` enums driving rhythm
- VISION § 12 (Chronicle suppression + regeneration plan), § 16 (Cadence success metrics), § 17 (Editorial Rhythm), § 19 (Autonomous Operation)
- **[docs/editorial-rhythm.md](../docs/editorial-rhythm.md)** — detailed day-of-week + season-phase spec
- **[docs/signature-surfaces.md](../docs/signature-surfaces.md)** — the 12 unique publication targets the rhythm produces
- DECISIONS D-019 (rhythm lock), D-020 (autonomous operation), D-021 (hero design locks)
