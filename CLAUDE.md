# CFB Index — Agent Orientation

## What this is
Static-site CFB rankings + fan-intel product. Python generator → SQLite → ~17k HTML pages in output/site/.

## Do / Don't
- DO edit src/cfb_rankings/reporting.py (the generator) and fan_intelligence.py.
- DO use `python manage.py build-site` for fast iteration; `./publish_site.ps1` for full publish.
- DON'T edit output/site/** directly. Generated.
- DON'T hand-edit cfb_rankings.db. Write a CLI subcommand in cli.py.
- DON'T read reporting.py whole — it's 17.5k lines. Use offset+limit reads.

## Key line numbers (reporting.py)
- fetch_site_pulse: ~4087; counter bug at 4123-4124.
- "72 NCAA-eligible team records" copy: 5784, 10769.
- Empty-slug program link: 1131 (+ downstream consumer of program_url).
- Heisman winner render: 3935-3957.
- Nav tuples: 11717-11723.
- Fan intel fallback "Awaiting Signal": ~14830.
- Internal card labels to rename: 13116 (Stress Point), 13465 (Offensive Reminiscence), 13483 (Defensive Reminiscence), 9821 (Player Card Blueprint).

## Key files
- src/cfb_rankings/reporting.py — HTML monolith.
- src/cfb_rankings/fan_intelligence.py:833-838 — Mood Card default dict.
- src/cfb_rankings/ingest/honors.py — Heisman winner_flag source.
- src/cfb_rankings/cli.py — manage.py subcommands.
- src/cfb_rankings/config.py:43 — model_version string.

## Model routing
Sonnet = default. Opus = schema/data decisions, cross-cutting copy. Haiku = verification, renames, grep sweeps (via subagents).

## Build targets
- Fast: python -u manage.py build-site
- Full: ./publish_site.ps1
- Data refresh: ./safe_refresh_site.ps1

## Brief / audit
- CLAUDE_CODE_FIX_PROMPT.md — prioritized fix brief (P0-P3).
- CFB_INDEX_AUDIT.md — full product+UX audit this brief is derived from.
- PLAYER_PAGE_WORLD_CLASS_BRIEF.md — QB-first player-page redesign strategy, UX principles, Accolade Lens spec, Figma handoff. Archive trail in research/player-page-worldclass-brainstorm-2026-04-22.md.

## Fan Intelligence system (2026 buildout)
- FAN_INTEL_SOURCE_STRATEGY.md — canonical source + cohort reference. Read first before any fan-intel work.
- FAN_INTEL_BUILD_PLAN.md — 8-week task list with per-task model routing (Opus/Sonnet/Haiku).
- CLAUDE_CODE_KICKOFF_FAN_INTEL.md — paste-in prompt to start a build session.
- New code lives under src/cfb_rankings/ingest/sources/, src/cfb_rankings/cohorts/, src/cfb_rankings/provenance/.
- Cowork playbooks: docs/cowork_playbooks/.
- Schema migrations: migrations/.
- Per-session progress log: SESSION_LOG.md (created on first task).
