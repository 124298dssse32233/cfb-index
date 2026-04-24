# Claude Code Kickoff — Team-Page Signature Bets Port

**Context**: The player-page Signature Bets stack (Phases S1–S4) shipped
during the 2026-04-23 → 04-24 run. 17 live modules + 7 polish layers,
122 tests green, content seeds at 30 coaching programs / 10 narrative
arcs / 14 hot-take templates. In parallel, the autopilot track built
team-page infrastructure at `src/cfb_rankings/team_pages/` with its
own schema at `migrations/20260424_05_team_pages_schema.sql`. This
kickoff ports the reusable Signature Bets modules onto the team page.

**Source of truth**: `docs/specs/signature_bets/team_page_port_scoping.md`
— already classifies every player-page module by port cost (zero /
tiny / small / medium / don't-port). Read once at session start and
reference by § thereafter.

**How to use**: open a fresh Claude Code session, paste the block below
as your first message. Tasks run in the recommended port order; one
commit + SESSION_LOG entry per task. `/clear` is safe between tasks.

---

```
You are porting the CFB-nerd Signature Bets layer from the player page
to the team page. The infrastructure is already built — every bet
module renders via class-name-scoped CSS, slug-agnostic Alpine
components, and seed YAML files. The work is: (1) extend team-scope
data models where needed, (2) wire the existing renderers into the
team page template, (3) grow seed YAMLs for team-scope content.

## Read first, in this order (once per session)
1. CLAUDE.md
2. docs/specs/signature_bets/team_page_port_scoping.md — full read ONCE.
   Reference by § thereafter.
3. OVERNIGHT_SIGNATURE_BETS_SUMMARY.md — the state the player page
   shipped at; confirms what infrastructure exists.
4. SESSION_LOG.md — scan the "Signature Bets" + "Team Page" headers
   to see where the two tracks left off.
5. src/cfb_rankings/team_pages/__init__.py (+ grep the folder) —
   understand the autopilot-built team_pages structure, since your
   work attaches to it.

Do NOT read reporting.py whole. 16k+ lines. Grep for the specific
render function, then offset+limit read a tight range.
Do NOT duplicate renderers. If a module's renderer lives in
reporting.py (e.g. render_achievements_ribbon), call it from the
team-page template — import, don't copy-paste.

## Model routing — enforce per task
- Opus (rare, spec-only):
   * Team-scope achievement detector taxonomy (new catalog + rarity
     tuning against team-level data — distinct from per-player).
   * Team-scope Hot-Take template voice library (metrics are different:
     SP+ rank, recruiting class rank, explosive-play rate, opponent-
     adjusted efficiency — not YPA/TDs).
   These produce SPEC docs Kevin can review before Sonnet implements.

- Sonnet (default — the workhorse):
   * Implementing ported renderers (swap player_id → team_id, reuse
     existing Python render helpers wherever possible).
   * Data-fetch aggregators against team_* tables.
   * CLI commands + new seed YAMLs.
   * Regression tests mirroring tests/test_bets_regression.py for
     the team page.

- Haiku (via Task subagent only — verification, never main-thread):
   * 20-page team spot-check after each module ports (grep HTML for
     expected class names + data-state attributes).
   * Rarity distribution audits on team achievements.
   * Hot-Take defensibility spot-check: every team hot-take must
     have a resolvable (rank, cohort, sample, methodology) quadruple.

Opus tasks produce specs; Sonnet tasks produce code. Never let Sonnet
verify what Haiku can verify.

## Token discipline — the hard rules
- Read the port scoping doc ONCE per session; reference by §.
- Grep reporting.py first; Read by range. Never a whole-file read.
- At 60% context full: stop at the next task boundary, commit, log,
  hand back. `/clear` is safe between task boundaries.
- Every task ends with a Haiku subagent verification pass.
- Each task commits independently. Live site never breaks.

## Pre-flight defaults (already decided — do not re-litigate)
- The bets/ package is REUSABLE. `render_hot_take_card`, `render_
  anti_take_card`, `render_achievements_ribbon`, `render_coaching_
  lineage_card`, etc. all accept slug-agnostic inputs. You call them
  from the team-page renderer; do not fork them.
- CSS is class-name-scoped. Team pages inherit the visual system
  automatically by emitting the same class names.
- Alpine components (scenario-explorer.js, keyboard-shortcuts.js,
  glossary.js, context-menu.js, signal-flow.js, what-changed.js, the-
  room.js) are slug-agnostic. Do not fork them.
- New seed files use `team_` prefix: `seeds/team_achievement_catalog.
  yaml`, `seeds/team_narrative_arcs.yaml`, `seeds/team_hot_take_
  templates.yaml`. Player seeds stay untouched.
- Regression tests live in `tests/test_team_bets_regression.py`
  mirroring the player version.

## Repo conventions (for this track)
- Spec docs: docs/specs/signature_bets/team_{bet_name}_spec.md
- Team-scope data modules: src/cfb_rankings/bets/team_{bet_name}.py
  (keeps the package single-purpose; dispatch by scope within).
- Renderer wiring: call existing bets/ render_* functions from
  src/cfb_rankings/team_pages/ modules.
- New migrations: migrations/YYYYMMDD_NN_team_{name}.sql
- Fixtures: tests/fixtures/team_bets/{bet_name}/
- CLI: python manage.py team-{bet-name}-{subcommand}

## Phases (execute in order; each ends at a hand-back boundary)

═══════════════════════════════════════════════════════════════════════
  PHASE T1 — Zero-effort ports (2-3 tasks)
═══════════════════════════════════════════════════════════════════════

Port the three modules the scoping doc classifies as zero-effort. Pure
template wiring.

### TASK T1.1 — FI Glossary icons on team page (Sonnet)
Grep src/cfb_rankings/team_pages/ for FI-term eyebrow labels (Fan Pulse,
Respect Gap, Rival Heat, etc.); call render_glossary_icon(slug) next
to each. Same 12 terms the player page uses. Acceptance: team page
has ≥5 ? icons next to FI eyebrows, popover opens correctly.

### TASK T1.2 — Coaching Lineage on team page (Sonnet)
The module is already team-scope (fetch_coaching_lineage(team_slug)).
Import render_coaching_lineage_card into the team-page renderer and
slot it inline. Acceptance: Notre Dame team page shows the same
lineage card Carr's player page shows today.

### TASK T1.3 — This-day chip on team page (Sonnet)
fetch_this_day_moment() is player-keyed. Ship a team_this_day.py
mirror that matches games.start_time_utc month+day for the team
(any player). Wire into the team hero. Acceptance: chip renders on
teams with games on today's date; empty otherwise.

### PHASE T1 CLOSE — commit the 3 tasks, hand back.

═══════════════════════════════════════════════════════════════════════
  PHASE T2 — Data-swap ports (4 tasks)
═══════════════════════════════════════════════════════════════════════

Trivial team_* table swaps.

### TASK T2.1 — Era Context on team page (Sonnet)
compute_era_context already supports team cohorts. Wire into the team-
page renderer next to record-eligible team stats.

### TASK T2.2 — Cohort Divergence Map on team page (Sonnet)
team_week_conversation_features exists (fan-intel track). Ship a
team_cohort_divergence.py that mirrors the player version, reuse
render_cohort_divergence_map. Acceptance: team pages with ≥4 bucket
mentions render the scatter; others show empty-state.

### TASK T2.3 — Rival Radar on team page (Sonnet)
Same pattern as T2.2. Use team_week_conversation_features rival
rows. Reuse render_rival_radar_card.

### TASK T2.4 — Prediction Markets on team page (Sonnet)
prediction_market_snapshots already has team_id. Ship team_prediction_
markets.py fetching team futures (win total, CFP, conference). Reuse
render_prediction_markets_card or author a team variant if the
Heisman-specific copy doesn't fit.

### PHASE T2 CLOSE — commit the 4 tasks, hand back.

═══════════════════════════════════════════════════════════════════════
  PHASE T3 — Infrastructure ports (3 tasks)
═══════════════════════════════════════════════════════════════════════

New team-scope event + state machinery.

### TASK T3.1 — Team Signal Flow (Sonnet)
Migration adds team_signal_events table (mirror of player_signal_
events). Team event vocabulary: 'commitment', 'ranking_move',
'bowl_assignment', 'coach_change', 'recruiting_class_ranked',
'program_record'. Ship team_signal_flow.py with emit / fetch / prune.
CLI: team-signal-emit / team-signal-list / team-signal-prune. Reuse
render_signal_flow_bar.

### TASK T3.2 — Team What-Changed diff (Sonnet)
Team state blob fields: power_rating, conference_rank, sp_plus_delta,
recruiting_class_rank, plus a version hash. Reuse what-changed.js
client-side; emit a team-scoped <script id="page-state" data-team-
slug="..."> on the team page.

### TASK T3.3 — Team Page regression test suite (Sonnet)
Mirror tests/test_bets_regression.py → tests/test_team_bets_
regression.py with 20+ checks targeting output/site/teams/notre-dame.
html (or whichever team anchor Kevin picks). Catches any future
commit that drops a module.

### PHASE T3 CLOSE — commit, hand back.

═══════════════════════════════════════════════════════════════════════
  PHASE T4 — Content-heavy ports (3 tasks; Opus-assisted)
═══════════════════════════════════════════════════════════════════════

### TASK T4.1 — Team Hot-Take / Anti-Take (Opus spec + Sonnet impl)

Opus sub-task: docs/specs/signature_bets/team_hot_take_spec.md
  - Defensibility quadruple for teams (rank + cohort + sample +
    methodology, but metrics change).
  - Template library 15-25 entries across voice bands.
  - Metric whitelist: SP+ rank, offensive_efficiency, defensive_
    efficiency, explosive_play_rate, havoc_rate, red_zone_td_rate,
    recruiting_class_rank, transfer_net_rating. Higher-is-better
    only for v1.
  - Anti-Take caveat library — the caveat structure carries over;
    the metric-specific conditions don't.

Sonnet sub-task: src/cfb_rankings/bets/team_hot_take.py + team_anti_
take.py mirroring the player versions. New seed YAMLs. CLI: team-
hot-take <slug>, compute-daily-team-hot-takes. Reuse render_hot_
take_card + render_anti_take_card.

### TASK T4.2 — Team Achievements (Opus taxonomy + Sonnet impl)

Opus sub-task: docs/specs/signature_bets/team_achievements_spec.md
  - ~15 achievements drawn from team-scope data: Program Record,
    Conference Title, Undefeated Season, Top-10 SP+ Finish, Top-25
    Recruiting Class, Transfer Portal Winner, Upset of the Week, etc.
  - Rarity targets per achievement. Capped at 100%.

Sonnet sub-task: src/cfb_rankings/bets/team_achievements.py +
seeds/team_achievement_catalog.yaml. Reuse render_achievements_ribbon.

### TASK T4.3 — Team Narrative Arc (hand-authored for top-20 programs)

Seed file seeds/team_narrative_arcs.yaml. Keyed on team_slug, not
player_id. Same 3-act structure. Hand-author top-20 programs; auto-
draft (ported from S4.10) fills the long tail.

### PHASE T4 CLOSE — commit, hand back.

═══════════════════════════════════════════════════════════════════════
  STOP CONDITIONS
═══════════════════════════════════════════════════════════════════════

- End of any phase T1/T2/T3/T4 — commit, summarize, hand back.
- Context above 60% — stop at next task boundary.
- Haiku verification failure — never ship a task that failed
  verification. Fix or escalate.
- Any schema change not covered here — AskUserQuestion.

## Per-task protocol
1. Announce: "Starting TASK T{N}.{M} — {name}. Model: {Opus|Sonnet}."
2. Read only what the task requires.
3. Implement / design.
4. Haiku subagent verification.
5. git commit -m "bets: T{N}.{M} — {one-line summary}"
6. Append 3 lines to SESSION_LOG.md under a "Team-Page Signature
   Bets — Session Log" header.
7. Next task or stop per stop conditions.

## Begin
1. Verify src/cfb_rankings/team_pages/ exists (autopilot-track
   dependency). If not, hand back — we wait.
2. Confirm `python -m pytest tests/` runs green before you start.
3. Start with TASK T1.1 (FI Glossary icons — Sonnet).

If SESSION_LOG.md doesn't have a Team-Page Signature Bets section
yet, append header:

# Team-Page Signature Bets — Session Log

Then start logging T1.1.
```

---

## Operator notes (not part of the paste-in)

### Why this is the right next phase

- **Autopilot dependency met**: team_pages/ infrastructure is live.
- **Low effort per task**: every module's renderer + CSS is reusable.
  Most tasks are a 100-line wiring + a seed YAML edit.
- **High product leverage**: team pages are the navigation backbone
  (every player page links to its team page; every Heisman-board row
  links to a team). Putting the Signature Bets layer there means every
  entry point into the site has the CFB-nerd texture.
- **Content seed parallelism**: team_achievement_catalog can be
  authored by whoever (editorially) writes player achievements. The
  pipeline is content-hours, not eng-hours.

### Token estimate

- Phase T1 (3 tasks): ~80k tokens total. Sonnet-heavy.
- Phase T2 (4 tasks): ~120k tokens. Sonnet.
- Phase T3 (3 tasks): ~150k tokens. Sonnet + one small migration.
- Phase T4 (3 tasks, 2 Opus specs): ~250k tokens. Opus specs ~30k
  each, Sonnet impls ~60k each.

Total: ~600k tokens across ~13 tasks, one 4–6 hour working session if
run end-to-end with the model routing enforced. Individual tasks are
bite-size; /clear between phase boundaries.

### Deferred from player-page work (also worth picking up)

If team-page port runs short or a session has extra capacity, the
player-page follow-ups documented in `docs/specs/signature_bets/
phase_s5_roadmap.md` are also worth knocking out:

- Extend coaching_lineage.yaml to all 68 P4+ND programs (currently 30).
- Extend narrative_arcs.yaml to every returning Heisman-candidate
  QB (currently 10).
- Hot-Take flag aggregator (cron job writing into hot_take_template_
  holds based on flag rate).
- Narrative-arc editor workflow (promote auto-draft → manual).
- Hot-Take share-card PNG generator.

### The one sentence

Port the proven player-page Signature Bets layer to the team page —
reuse the renderers, mirror the data pipelines, grow the seed YAMLs,
ship 13 tasks across 4 phases, hand back per phase, one commit per
task.
