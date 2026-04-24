# Team-page Signature Bets — port scoping

**Audience**: the autopilot-track work on `src/cfb_rankings/team_pages/`
and/or a future session that translates Signature Bets from the player
page to the team page.

**Purpose**: document which player-page bet modules translate cleanly,
which need reshaping, and which don't apply.

## Direct translation (minimal rework)

Each of these reads team-scoped data that already exists; porting is
a renderer + data-fetch swap.

### 1. FI Glossary (S1.1)

The `render_glossary_icon(slug)` helper is team/player agnostic. The
seed file + client-side popover are unchanged. **Port cost**: zero —
reuse as-is.

### 2. Live Signal Flow (S1.6)

`player_signal_events` has `player_id`; team analogue is trivial:

```sql
CREATE TABLE team_signal_events (
  team_signal_event_id INTEGER PRIMARY KEY AUTOINCREMENT,
  team_id INTEGER NOT NULL,
  event_type TEXT NOT NULL,   -- 'commitment', 'ranking_move',
                              -- 'bowl_assignment', 'coach_change',
                              -- 'recruiting_class_ranked'
  headline TEXT NOT NULL, ...
);
```

`emit_signal_event` + `fetch_active_signals` + `render_signal_flow_bar`
reuse verbatim with `player_id → team_id` swap. **Port cost**: small.

### 3. What-Changed diff (S1.4)

Client side is slug-agnostic (reads `localStorage[cfb:last-visit:
${slug}]`). Team pages get the same treatment — the state blob shape
just needs team-level fields (power rating, conference rank, SP+
delta, recruiting class rank). **Port cost**: small.

### 4. Rival Radar (S2.4)

Currently aggregates `player_week_conversation_features` → belief /
sentiment shares / obsession score. Team-scope analogue already exists
in `team_week_conversation_features` (fan-intel pipeline). Renderer
reuses; just swap the fetch. **Port cost**: tiny.

### 5. Achievements ribbon (S2.7)

Detectors are per-player today; team analogues are data-available
(program records, conference titles, undefeated seasons). New detector
list in `seeds/team_achievement_catalog.yaml`. Render helper is
identical. **Port cost**: medium (new detector set).

### 6. Coaching Lineage (S2.9)

Team-scope by design — already keyed on `team_slug`. Zero changes.

## Reshape for team scope

### 7. Hot-Take / Anti-Take (S2.1-S2.3)

Templates need a team-specific library. Defensibility quadruple stays
the same shape; template placeholders shift to team metrics (SP+ rank,
recruiting class rank, explosive-play rate, etc.). New seed file +
new detector rule. **Port cost**: medium.

### 8. Narrative Arc Board (S3.4)

3-act structure adapts well to team seasons (Opening / Midseason /
Stretch). Hand-authored seeds go in `seeds/team_narrative_arcs.yaml`.
Auto-draft from team-scope signature metric + achievements + hot-take.
**Port cost**: small-medium.

### 9. Prediction Markets (S2.8)

Team-level futures are more plentiful than player-level; `prediction_
market_snapshots` table already has `team_id`. The renderer + fetch
are mechanical reuse. **Port cost**: tiny.

## Don't port (player-centric concepts)

### 10. Mirror Match (S2.5)

Per-position feature vectors; teams don't have a natural analogue.
The "closest historical fingerprint" for a team season could exist
as a separate feature but should get its own spec, not a direct port.

### 11. Scenario Explorer (S3.3)

Per-player projection model. Team-level equivalent would be a win-
total / SP+-rank projector — related but distinct product.

### 12. This-day chip (S4.3)

Team history has plenty of game dates — actually translates well. Port
it.

### 13. Era Context (S1.3)

Already team-scoped in its cohort chain. Drop-in reuse.

### 14. Cohort Divergence Map (S3.1)

Reads `player_week_conversation_features`; team analogue reads
`team_week_conversation_features`. Direct swap. Port cost: tiny.

## Infrastructure that reuses

- `_compose_global_css()` — all CSS component blocks are class-name
  scoped (`.hot-take`, `.rival-radar`, `.cohort-divergence`, etc.) so
  team pages inherit the visual system just by emitting the same
  class names.
- Alpine modules (`the-room.js`, `scenario-explorer.js`, `glossary.js`,
  `keyboard-shortcuts.js`, `context-menu.js`, `signal-flow.js`, `what-
  changed.js`) are slug- / page-agnostic.
- The 27-check regression test pattern (`tests/test_bets_regression.
  py`) is easy to extend to team pages; add parallel test cases for
  `output/site/teams/<slug>.html`.

## Recommended port order

1. FI Glossary + Coaching Lineage + This-day chip (zero-effort ports).
2. Era Context + Cohort Divergence + Rival Radar (trivial data-fetch swap).
3. Signal Flow + Prediction Markets + What-Changed diff (small).
4. Hot-Take / Anti-Take (template library work; medium).
5. Achievements (detector catalog work; medium).
6. Narrative Arc (editorial seed work + auto-draft; medium).

Estimated total port: ~5-7 focused sessions, with the bulk being
editorial work on seed files and detector rules, not infrastructure.

## Don't do

- Don't copy renderer functions wholesale into team_pages/. Extract
  shared helpers (`render_achievements_ribbon`, `render_hot_take_card`,
  etc.) into `src/cfb_rankings/bets/renderers.py` if needed and import
  from both page modules.
- Don't duplicate detector logic. Keep achievement detectors in one
  module; dispatch on (scope, subject_id).
- Don't fork the seed YAML files per page. Each seed file serves one
  scope; team YAMLs live next to player YAMLs with `team_` prefixes.
