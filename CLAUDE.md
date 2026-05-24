# CFB Index — Agent Orientation

_Last refreshed 2026-05-24. If a number here looks wrong, trust `wc -l` and `ls | wc -l` over this doc._

## 🚨 Vercel alias rotation gotcha (2026-05-23)
- The user-facing alias `wonderful-margulis-8ec96b.vercel.app` did NOT auto-rotate when `vercel deploy --prod` created new deployments.
- Per-deploy URLs (e.g. `wonderful-margulis-8ec96b-h3ulpujuj-...vercel.app`) had the latest content. Short alias was pinned to an old deployment.
- Fix shipped 2026-05-23 in `publish_site.yml`: capture deploy URL via `vercel deploy` stdout, then explicitly run `vercel alias set <deploy-url> wonderful-margulis-8ec96b.vercel.app` after.
- If users report "page looks like before" after a deploy, check the per-deploy URL FIRST — content is almost always correct there.

## Chronicle eval gotcha (2026-05-24)
- Heuristic FActScore uses `_extract_key_terms()` which strips punctuation via `_tokenize()`: "43-41" → token "4341".
- `_verify_heuristic()` must also strip punctuation from `ev_text` before the `t in ev_text` substring check, otherwise "4341" never matches "43-41" in evidence strings. Fixed 2026-05-24.
- `OVERLAP_THRESHOLD = 0.2` (not 0.4) — game-evidence rows are sparse (short structured strings), prose cards contain many editorial terms not in evidence. 40% was too strict.
- Card-level reject gate: `factscore < 0.50` in `pipeline.py`. These two thresholds work together.
- Game evidence (`fetch_team_game_evidence()`) covers all 119 active FBS teams — evidence floor so T3 cards generate for everyone, not just Polymarket-covered teams (~24).

## AI Narratives on team pages (2026-05-24)
- `fetch_llm_chronicle_cards(db, slug, limit=6)` in `team_pages/data.py` — reads `chronicle_card_cache`, prefers `is_lkg=1`, orders by `season_year DESC, week_number DESC`.
- `_render_llm_chronicle_section()` + `_render_llm_card()` + `LLM_CHRONICLE_CSS` in `renderer.py` render an "AI Narratives" card grid below the Chronicle section.
- 88 FBS teams have AI cards (111 cards shipped, 12 failed eval, 42 suppressed for <3 evidence rows).
- 75 of 127 profiled teams (world-class renderer) now show AI Narratives live in `output/site/teams/`.
- Crosslinks: chronicle standalone pages link back to team pages and vice versa.

## Module inventory (2026-05-24)
- **Team pages** (`src/cfb_rankings/team_pages/`): 23 modules across the world-class chrome.
  - Above-the-fold: Page Tone Strip · Kickoff Countdown · Offseason Pulse · Top Commits · Recruiting Footprint · Top Players · NFL Draft Pipeline · Coaching Era Strip · Recent Form · Season Standing · Program Prestige · Trajectory chip
  - Mid-page: Peer Comparator · On This Day · Wrapped · Fanbase Health · Conference Standing · Ceiling/Floor · Home-Field Advantage · Moment of the Year · Schedule Strength · Statement Wins · Bowl History · AI Narratives (LLM)
- **Player pages** (`src/cfb_rankings/player_pages/`): 8 new v2 modules injected into legacy `reporting.py` render via `page_data["new_*_html"]` keys:
  - `standing_rail.py` (17-rung)
  - `mirror_match.py` (statistical fingerprint)
  - `coaching_lineage.py` (year-by-year HC)
  - `live_signal_flow.py` (placeholder)
  - `heisman_trajectory.py` (week-by-week or single-snapshot)
  - `career_arc.py` (HS → CFB → NFL)
  - `development_trajectory.py` (multi-season bars)
  - `selector_grid.py` (6-cell honors grid)
- Profile YAMLs: **127 hand-authored, 100% real-FBS coverage** (119/119 FBS slugs in `profiles/`).
- CFBD data feeds active (auto-ingested in publish_site enrich step): NFL Draft 2018-2025, Postseason games 2018-2024, Coaches 2018-2024, Returning Production / Talent / Recruiting Class / Transfer Portal / Recruit profiles 2018-2025.

## CI guardrail
- `scripts/verify_world_class_team_pages.py` runs after build verification. Hard-fails the build if any real FBS team page ships `premium-team-hero` legacy chrome instead of `team-page` world-class chrome.

## Chronicle LLM pipeline (2026-05-24) — LIVE on Alienware via Ollama
- **Status: ACTIVATED 2026-05-24.** Both models pulled, real cards generating end-to-end.
- Ollama 0.24.0 daemon running at localhost:11434
- Pulled: `mistral-nemo:12b-instruct-2407-q4_K_M` (7.5GB, Writer) + `qwen3:8b` (5.2GB, Planner/Critic)
- Runtime auto-detects Ollama and uses OllamaBackend → /api/generate with native `format: <schema>` for structured output
- `OllamaBackend` strips Qwen3 `<think>...</think>` reasoning blocks before JSON parse
- Tier T3 throughput: ~15s/card on RTX 5070. Tier S (full 5-agent): ~30s/card.
- First production card (Alabama echo, 74 words): "Over 15 consecutive trading days in May, the market volume for Alabama to win the 2027 CFP National Championship stayed steady at $27.16 [src:polymarket_2026-05-21]."
- Override default models via env: `CHRONICLE_OLLAMA_WRITER` / `CHRONICLE_OLLAMA_PLANNER`

## Chronicle LLM pipeline (architecture)
- 14 modules in `src/cfb_rankings/chronicle/`: config, source_trust, retriever, evidence_sources, runtime, prompts, cache, eval, observability, lora_corpus, antislop, lkg, pipeline, run.
- 8 new DB tables (migrations `20260524_01..08`): `narrative_frame_stack`, `season_narrative_state`, `season_narrative_arc`, `chronicle_card_cache`, `pipeline_checkpoints`, `narrative_phrase_tokens`, `narrative_claim_stack`, `chronicle_slop_observations`, `calendar_pressure`, `chronicle_banlist` (seeded with 56 phrases).
- 287 tests pass via `python -m pytest tests/test_chronicle_*.py -v`.
- Voice corpus pre-built: `data/voice_corpus.jsonl` (329 passages, 305KB, includes `[CFB-INDEX-VOICE]` sentinel).
- Tier policy: S=top 25 players + top 10 teams (Best-of-3, full 5-agent); T1=top 50 teams + top 100 players (single-pass); T2=rank 51-100 (3-agent); T3=long tail (template-fill).
- CLI: `python -m cfb_rankings.chronicle.run generate --tier S --max-cards 1 --dry-run` works end-to-end without any LLM installed (NullBackend fallback).
- Health check: `python -m cfb_rankings.chronicle.run health`.
- Workflow: `.github/workflows/chronicle-weekly.yml` runs on `[self-hosted, alienware]` with 10 cron schedules + manual dispatch + emergency LKG fallback via `scripts/emergency_publish.ps1`.
- LKG (Last-Known-Good) cards live at `output/site/_cards_lkg/` and are committed to git on each successful run — guarantees fans never see broken pages on Sunday-night pipeline failures.
- **To activate**: install llama.cpp + Mistral Nemo Q5_K_M GGUF + Qwen3-8B-Thinking Q4_K_M GGUF on Alienware. Run two llama-server instances (ports 8001 + 8002). Optionally train Voice LoRA via `python scripts/train_voice_lora.py --corpus data/voice_corpus.jsonl`. Cloud fallback (DeepInfra Mistral Nemo at $0.02/$0.04 per M tokens) works for Tier 2/3 without any local install.

## What this is
Static-site CFB rankings + fan-intel product. Python generator → SQLite → ~69k HTML pages in `output/site/`.

## Deployment (UPDATED 2026-05-22)
- **Vercel git auto-deploy is DISCONNECTED.** Master pushes do NOT trigger Vercel deploys. (Reason: `output/` is gitignored, so git-triggered builds had zero player HTML files and 404'd `/players/*`.) Don't reconnect without a migration plan.
- **All production deploys flow through `vercel deploy --prod` inside cron workflows.** `publish-site.yml`, `the-daily-06am-et.yml`, `wire-daily-04am-et.yml`, `mailbag-friday-09am-et.yml` each call the Vercel CLI directly.
- **To force a fresh deploy:** trigger `publish-site` via `gh workflow run publish_site.yml`. Runs ~50 min.
- **CI guardrails:**
  - 19 workflows fail-loud if the rolling `cfb-rankings-db` artifact is missing or poisoned (Option B). Bypass via `--allow-empty` on `scripts/verify_db_artifact_healthy.py` if you legitimately need a fresh-DB start.
  - 7 workflows that call the `notify_failure.yml` reusable workflow have an explicit `permissions: { issues: write, contents: read }` on their notify job — don't strip it.
  - `live_smoke_test.yml` hits 28 representative URLs every 30 min and opens an automation-failure issue at < 95% pass rate.
- See [SESSION_3_AUTONOMOUS_WRAP.md](SESSION_3_AUTONOMOUS_WRAP.md) for the full structural-hardening pass on 2026-05-22.

## Do / Don't
- DO edit `src/cfb_rankings/reporting.py` (the generator) and `fan_intelligence.py`.
- DO use `python manage.py build-site` for fast iteration; `./publish_site.ps1` for full publish.
- DON'T edit `output/site/**` directly. Generated.
- DON'T hand-edit `cfb_rankings.db`. Write a CLI subcommand in `cli.py`.
- DON'T read `reporting.py` whole — it's ~26,800 lines as of 2026-05-16 and growing (was ~25.8k on 2026-05-12, +1k in four days; this growth is normal — surgical fixes add lines). Use `offset+limit` reads. Line numbers shift weekly — grep for symbols (e.g. `grep -n "_worst_result_text"`) and do not trust historical line numbers in any brief, including this one.

## Key files
- src/cfb_rankings/reporting.py — HTML monolith. Grep for symbols; do not trust historical line numbers.
- src/cfb_rankings/fan_intelligence.py — mood-card + belief computation. Owner of the "Awaiting Signal" fallback.
- src/cfb_rankings/ingest/honors.py — Heisman / award winner_flag source.
- src/cfb_rankings/cli.py — manage.py subcommands and dispatcher.
- src/cfb_rankings/config.py — model_version string and app config.

## Build targets
- Fast: `python -u manage.py build-site` (rebuilds site only)
- Full: `./publish_site.ps1` (full ingest + build + sync)
- Data refresh: `./safe_refresh_site.ps1`
- Methodology landing pages: `python manage.py build-methodology` (writes fan-intelligence.html, freshness.html, and the methodology index)
- Editions archive: `python manage.py build-editions-archive` (writes /editions/index.html)

## Section landing pages (writable post-build)
- /methodology/index.html — generated by `provenance/methodology_index_page.py`, invoked from `build-methodology`.
- /editions/index.html — generated by `editions/archive_renderer.py`, invoked from `build-editions-archive` and from `daily_ingest.ps1`, `backfill_historical.ps1`, and the publish/weekly workflows.

## Model routing
Sonnet = default. Opus = schema/data decisions, cross-cutting copy. Haiku = verification, renames, grep sweeps (via subagents).

## Brief / audit
- `docs/octopus/discover.md` — current-state audit dated 2026-05-12. **Read this first.** Supersedes most of `CFB_INDEX_AUDIT.md`, which is now historical.
- `docs/octopus/define.md` — fix charter derived from discover.md, with surgical/module/architectural triage.
- `CFB_INDEX_AUDIT.md` — 2026-04-22 audit; most P0 bugs flagged here have been fixed (see `docs/octopus/discover.md` §2 for the delta).
- `CLAUDE_CODE_FIX_PROMPT.md` — older prioritized fix brief; most items now executed.
- `PLAYER_PAGE_WORLD_CLASS_BRIEF.md` — QB-first player-page redesign strategy, UX principles, Accolade Lens spec, Figma handoff. Archive trail in `research/player-page-worldclass-brainstorm-2026-04-22.md`.

## Design system (LOCKED 2026-05-17 in Sprint v5-5.5 — Window B)
- `docs/design-system/00-tokens.md` — color ramps + typography stack (Bebas Neue + Source Serif Pro + Inter) + tabular numerals enforcement. Locked tokens; changes require Window A/B coordination.
- `docs/design-system/30-page-archetypes.md` — 6 IA archetypes (Article / Dashboard / Profile / Database / Tentpole / Anniversary) with allowed-module contracts per archetype.
- `docs/design-system/31-chart-vocabulary.md` — 6 allowed chart types (percentile bar / trajectory spark / bump chart / annotated line / small multiples / heatmap) + forbidden list (no pie, no vertical bar, no radar except player fingerprint).
- `docs/design-system/32-receipt-pattern.md` — citation wire format for Pattern C/D editorial, `editorial_citations` migration, citation_critic role, ≥1 marker per 200 words density rule.
- `docs/design-system/33-confidence-signaling.md` — 3 confidence bands (high/medium/low) + unset, data-driven thresholds from per-team-week distribution, `confidence_calibration` table, per-domain calibration.
- `docs/mockups/index.html` — Sprint v5-5.4 mockup set (11 surfaces, 33 polish rounds, signed off 2026-05-17). Visual reference for every archetype.

## Team Pages module
World-class team-page renderer at `src/cfb_rankings/team_pages/`. Disjoint from `reporting.py`. Profiled programs = every slug with a file in `profiles/*.md` (currently 17 slugs as of 2026-05-16, unchanged since 2026-05-12: alabama, auburn, florida, georgia, massachusetts, michigan, notre-dame, ohio-state, oklahoma, oregon, penn-state, tennessee, texas, uconn, usc, vanderbilt, washington — discovered at import time as `PROFILED_SLUGS`; `ls profiles/*.md` is the source of truth). During `build-site`, `reporting.py` short-circuits both the delete-sweep and the legacy HTML write for profiled slugs (grep `reporting.py` for `PROFILED_SLUGS`), then after the legacy loop calls `team_pages.render_all_profiled_pages(db, teams_dir)` to emit the world-class pages. Unprofiled programs (~662 slugs) keep legacy output. Standalone iteration: `python manage.py render-team-pages` (all profiled) or `python manage.py render-team <slug> [<slug> ...]`. Sprint-2 adds Savant + Rivalry modules; see `TEAM_PAGE_WORLD_CLASS_BRIEF.md` and `docs/design-system/12-modules-intel.md`.

## Fan Intelligence system (2026 buildout)
- FAN_INTEL_SOURCE_STRATEGY.md — canonical source + cohort reference. Read first before any fan-intel work.
- FAN_INTEL_BUILD_PLAN.md — 8-week task list with per-task model routing (Opus/Sonnet/Haiku).
- CLAUDE_CODE_KICKOFF_FAN_INTEL.md — paste-in prompt to start a build session.
- New code lives under src/cfb_rankings/ingest/sources/, src/cfb_rankings/cohorts/, src/cfb_rankings/provenance/.
- Cowork playbooks: docs/cowork_playbooks/.
- Schema migrations: migrations/.
- Per-session progress log: SESSION_LOG.md (created on first task).

## Known design choices that *look* like bugs
- `programs/<slug>.html` is **flat by design**, not `programs/<slug>/index.html`. Cross-links throughout reporting.py assume the flat form — do not "standardize" this.
- `/assets/...` absolute paths are correct for the deployed site (served at root). They render unstyled when opening HTML directly from disk via `file://`, but that's not the deployment target — don't rewrite to relative paths.
- "Awaiting Signal" fan-intel fallback fires for genuinely-no-signal programs (small DII/DIII/NAIA without measurable Reddit/news/betting volume). It's a graceful-degradation path, not a bug — fix the upstream signal collection, not the fallback string.

## Build-script parameter discipline
Several CLI subcommands take `--season` as `required=True` in cli.py. When adding a new caller in a script or workflow, grep for the existing `required=True` argument before assuming defaults exist:
- `build-the-room-board`, `build-players-landing`, `build-signature-story-board` — all need `--season`.
- `run-models`, `run-heisman-model` — need `--season`.
- `import-player-honors` — needs `--csv` (CSV-driven; not a daily-cadence command).
