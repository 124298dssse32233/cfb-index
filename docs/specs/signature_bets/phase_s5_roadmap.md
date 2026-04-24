# Signature Bets — Phase S5 roadmap

**Status**: Phases S1–S4 closed. Everything in the kickoff doc has
either shipped (with ready + empty states) or is documented as data-
ingestion-dependent. The player page is a mature canvas with 6 S1
texture modules + 13 S2 signature modules + 4 S3 engagement modules
+ 7 S4 polish layers.

This doc is the honest next-step map — what to pick up when Kevin
gets back.

## Quick-wins (each ≤ 1 session)

1. **Extend seeds/coaching_lineage.yaml** to every P4+ND program
   (currently 15; target 68). Pure YAML, no code. Template in place.
2. **Extend seeds/narrative_arcs.yaml** to cover every returning QB
   of Heisman interest (currently 5). Same pattern.
3. **Extend seeds/hot_take_templates.yaml** with position-specific
   voices. 14 templates today; 25 is the spec target.
4. **Hero fingerprint data-metric attrs** — add `data-metric="..."` to
   every Hero stat tile so the S4.12 right-click menu triggers on
   more surfaces. No new logic.
5. **FI Glossary term sweep** — scan reporting.py for every
   still-non-glossaried FI term in renders (missed any beyond the 12
   already wired). Check `fan_intelligence.py` too.

## Data-ingestion-dependent (wait for the pipeline)

Each of these has working infrastructure and renders an honest empty
state today. When the upstream data lands, zero code changes are
needed.

1. **Rival Radar** — today 14 rival-bucket mentions across 7 players.
   Module lights up as the fan-intel ingestion thickens the rival
   audience_bucket in `player_week_conversation_features`.
2. **Signature Moment** — `player_game_stats` has 2025 W1 only.
   Module requires ≥ 2 games per player. Lights up when week-2+
   game data lands.
3. **Era Context** (S1.3 primitive) — requires ≥ 4 seasons of cohort
   coverage per stat_type. Today: 2024-2025 passing only. Lights up
   on historical backfill (CFBD 2010+).
4. **Prediction Markets** — both tables currently empty. Seeded
   adapters (Kalshi / PolyMarket) need their pull runs to populate.
5. **Mirror Match** — feature vectors operate, but the cohort pool
   is 2024-2025 only. Lights up with historical backfill; today's
   matches are all same-season-heavy.
6. **Cohort Divergence Map** — sparse per-player audience_bucket
   today. Thickens with fan-intel ingestion.
7. **Historical "this day" chip** — off-season date coincidence with
   games history is rare. Lights up in-season.

## Deferred (needed design / scope)

1. **S4.8 Cohort-match sparks** — requires peer data threading
   through signature_story.py's render payload (currently only cohort
   size surfaces). Best done as part of a signature_story.py
   refactor that the autopilot track is already modifying.
2. **S4.9 "Only X in history" detector** — vacuous at 1-2 seasons of
   cohort coverage. Rebuild when historical backfill lands; needs a
   multi-metric joint-constraint query design.
3. **Hot-Take share-card PNG** — kickoff mentioned a headless-browser
   or canvas-based image generator. V1 ships text-to-clipboard via
   the context menu. PNG version is a follow-up.
4. **Share-card overall** — applies to Achievements + Hot-Take +
   Narrative Arc. Right-click "copy as tweet" gets the text case;
   PNG case is a renderer design problem.
5. **Play-level attribution (Signature Play V2)** — `plays` table
   has EPA / PPA / garbage_time but no play ↔ player mapping. When
   a bridge table lands, upgrade Signature Moment → Signature Play
   (per-play).
6. **Narrative-arc editor workflow** — auto-drafts ship with
   `flag_for_review=True` and a dashed border. An actual review UI
   (promote / edit / reject) is a CLI + mini-admin-page task.
7. **Hot-Take flag aggregation** — S2.1 spec mentions flag rate > 3%
   holding a template. The flag button renders today; the nightly
   aggregator + write into `hot_take_template_holds` is a cron job
   (small).

## Ongoing observational tasks

1. **Rarity drift** — achievements rarity target is ≤ 10% of cohort.
   Re-run compute-achievements weekly; if any inflates > 15%,
   tighten criteria in `seeds/achievement_catalog.yaml`.
2. **Hot-Take defensibility spot-checks** — pick 30 random players
   weekly; read the daily take + verify against raw stats. Haiku
   subagent is the right tool.
3. **Narrative-arc voice drift** — if auto-draft templates start
   reading the same across players, that's a hint the draft rule
   needs more templates.

## Phase S5 theme candidates

If we go past polish into a new phase, the most product-positive
directions:

- **Team page signature bets** — the autopilot track is doing team-
  page work. Signature Bets would translate ~70% cleanly: Hot-Take
  on teams, Rival Radar, Coaching Lineage, Achievement tiles, Program
  Arc. The bets/ package is reusable.
- **Comparison tool** — two-player side-by-side view that reuses the
  modules. Useful for "Carr vs Mendoza" debates.
- **Heisman-board layer** — rank-aware narrative that cites the
  Hot-Take + Anti-Take for each candidate inline. Editorial product.
- **Beginner-guided tour** — a first-time-visit overlay that cites
  the voice principles and walks a reader through the page. Kickoff
  §11 beginner gateway taken further.

## Acceptance bar for "Phase done"

- ✅ 95/95 tests green (+ 27 bet-regression tests)
- ✅ All 4 kickoff phases closed (S1, S2, S3, S4)
- ✅ Every module has ready + honest-empty state
- ✅ No bet-module depends on another non-shipped bet-module
- ✅ Every data gap is documented with a "lights up when …" note
- ✅ Content seed files (coaching_lineage, narrative_arcs, hot_take_
  templates) are extensible via YAML edits
- ✅ Progressive enhancement preserved — every interactive surface
  works (or gracefully degrades) without JS
