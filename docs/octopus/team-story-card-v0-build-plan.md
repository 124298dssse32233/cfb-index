# Team Story Card — v0 Build Plan (deterministic crown, no LLM)

_Created 2026-06-11. A zero-context implementation plan for the **smallest shippable slice** of the Team Story Card ([[50-team-story-card]] … [[58-team-build-philosophy]]), grounded in the live `team_pages` renderer + `cli.py` + `build_publish.ps1` + `verify_module_coverage.py`. Planning only — no code in this doc. Hand this to a build session. Another window may be editing the live site; this plan is engineered to touch `team_pages/renderer.py` in exactly **one** spot to minimize merge surface ([[55-team-rollout-infra-compat]] §8)._

> **Line numbers shift weekly — grep for the symbols named here, never trust a historical line number** ([[CLAUDE.md]]). Symbols confirmed live 2026-06-11: `render_team_page` (`team_pages/renderer.py:200`), `_render_page` (`:397`), the module-join at `:684` (`body = "".join(p for p in module_parts if p and p.strip())`); the `compute-backometer` CLI block (`cli.py:1515` parser, `:6555` dispatch); the coverage registry `SIGNALS` (`scripts/verify_module_coverage.py:62`).

---

## 0. Scope — what v0 IS and ISN'T

**v0 IS:** a deterministic crown that ships into the live team-page render today, reading **only existing signals** (`PageState` + `backometer_weekly` + standings/rankings) plus **one new signal** (`coach_pressure_weekly`, Levels 1–2 only). The lead is chosen by a deterministic resolver; the logline is **templated from the program's profile voice** (`narrative_generator.py` template mode is already publishable because the voice lives in `profiles/*.md`). No model in the loop → zero eval/GPU risk. Graceful `""` fallback.

**v0 is NOT:** the confident-compiler LLM voice, the full 4-ledger detectors, the Tribal-Lens 3-rhetoric payload, the `program_bible` snapshots/changelog, Level-3 hot seat (buyout/“names to watch”), the institution character, or the “PREVIOUSLY ON” recap. Those are post-v0 phases ([[54-integration-with-live-team-system]] §5). v0 ships the **spine + the lead resolver + the coach signal** and proves the consolidation on real pages.

**Acceptance:** every profiled FBS team renders a crown (or `""`), the lead is correct for at least the hand-checked sample (rivalry week → rivalry; offseason blue blood → Standing Lead; quiet mid-major → Quiet State), and the pipeline + coverage guard stay green.

---

## 1. The v0 data contract (`ProgramNarrativeState`, deterministic subset)

A plain dataclass the renderer computes once and passes down (mirrors how `PageState` is already threaded). Only the v0 fields:

```python
@dataclass
class ProgramNarrativeStateV0:
    program_slug: str
    season_year: int
    as_of: str                  # ISO; from build clock passed in (no Date.now in render)
    page_mode: str              # = PageState mode (RIVALRY_PEAK / AUTOPSY / ...)
    lead_character: str         # coach|rivalry|conference|fanbase|roster   (institution disabled in v0)
    lead_kind: str              # active | standing | quiet
    timescale: str              # this_week|this_season|this_era|generation|all_time
    logline: str                # templated from profile voice (or "" in quiet)
    ban: dict | None            # {number, label, gloss, receipt}  (stat object, may be a record)
    standard_gap: float         # actual_standing - self_conceived_standard
    confidence_band: str        # high | medium | low | none
    tension: str | None
    render_rung: int            # 1..4 (v0 caps at rung 2 — no LLM saga)
    freshness_class: str        # current | morning | stale
    fallback_reason: str | None
```

`lead_kind` is **separate** from `render_rung` ([[51-team-narrative-engine]] §3e): a hard structured event is always `active` even with thin discourse; only the prose richness drops.

---

## 2. The change set (the honest minimum — NOT "one file")

| # | File | Change |
|---|---|---|
| 1 | `migrations/20260612_01_coaching_tenure.sql` | NEW — one row per coaching tenure (§3) |
| 2 | `migrations/20260612_02_coach_pressure_weekly.sql` | NEW — append-only weekly coach pressure (§3) |
| 3 | `migrations/20260612_03_program_narrative_state.sql` | NEW — persisted crown lead per team-week (the v0 “bible-lite”) |
| 4 | `seeds/coaching_tenure.csv` (+ a `import-coaching-tenure` CLI) | NEW — hand-seed ~119 current + recent tenures |
| 5 | `src/cfb_rankings/team_pages/coach_pressure.py` | NEW — the detector (Levels 1–2), pure Python/SQL |
| 6 | `src/cfb_rankings/team_pages/story_card.py` | NEW — the resolver + `render_story_card_section(db, profile, state, snapshot, npstate) -> str` |
| 7 | `src/cfb_rankings/team_pages/renderer.py` | EDIT (1 spot) — build `npstate` in `_render_page`, prepend the crown to `module_parts` |
| 8 | `src/cfb_rankings/cli.py` | EDIT — register `compute-coach-pressure` (+ `import-coaching-tenure`) parser + dispatch, mirroring `compute-backometer` |
| 9 | `scripts/build_publish.ps1` | EDIT — add a NON-critical `Run` for `compute-coach-pressure` near `compute-backometer` |
| 10 | `scripts/verify_module_coverage.py` | EDIT — add 2 `SIGNALS` tuples (§8) |
| 11 | `tests/test_team_story_card.py` | NEW — resolver + detector + render-fallback unit tests |

Everything except #7–#10 is net-new files. The `renderer.py` edit is one block (a `npstate = ...` build + a `module_parts.insert(0, crown_html)`), keeping merge surface tiny.

---

## 3. Migrations (idempotent, live convention)

`BEGIN TRANSACTION; CREATE TABLE IF NOT EXISTS …; COMMIT;`. All carry `program_slug` (canonical) + `team_id` (denormalized for joins; the coverage guard can count either — see §8).

```sql
-- 20260612_01_coaching_tenure.sql  (one row per TENURE, not per current coach)
CREATE TABLE IF NOT EXISTS coaching_tenure (
  coaching_tenure_id INTEGER PRIMARY KEY AUTOINCREMENT,
  program_slug TEXT NOT NULL, team_id INTEGER,
  coach_name TEXT NOT NULL,
  start_date TEXT, end_date TEXT,           -- end_date NULL = current
  fate TEXT,                                -- fired|left|retired|current
  record_w INTEGER, record_l INTEGER, best_finish TEXT,
  contract_through INTEGER, buyout_usd INTEGER, source_url TEXT,
  observed_at_utc TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_coaching_tenure_slug ON coaching_tenure(program_slug);

-- 20260612_02_coach_pressure_weekly.sql  (append-only; observed_at, no overwrite)
CREATE TABLE IF NOT EXISTS coach_pressure_weekly (
  coach_pressure_id INTEGER PRIMARY KEY AUTOINCREMENT,
  program_slug TEXT NOT NULL, team_id INTEGER,
  season_year INTEGER NOT NULL, week INTEGER NOT NULL,
  pressure REAL NOT NULL,                   -- 0..1
  phase TEXT NOT NULL,                      -- HONEYMOON|SECURE|WARMING|CROSSROADS|HOT_SEAT|SEARCH|LAME_DUCK
  evidence_level INTEGER NOT NULL,          -- 1|2 in v0 (3 needs Tier-A reporting, post-v0)
  perf_anchor_met INTEGER NOT NULL DEFAULT 0,
  discourse_pct REAL,                       -- 14-day rolling fire/buyout share
  components_json TEXT,
  observed_at_utc TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_coach_pressure_week ON coach_pressure_weekly(season_year, week);

-- 20260612_03_program_narrative_state.sql  (the persisted crown lead — v0 bible-lite)
CREATE TABLE IF NOT EXISTS program_narrative_state (
  pns_id INTEGER PRIMARY KEY AUTOINCREMENT,
  program_slug TEXT NOT NULL, team_id INTEGER,
  season_year INTEGER NOT NULL, week INTEGER NOT NULL,
  lead_character TEXT, lead_kind TEXT, timescale TEXT,
  logline TEXT, ban_json TEXT, standard_gap REAL,
  confidence_band TEXT, render_rung INTEGER,
  state_signature TEXT,                     -- regen-skip hash (mirrors team_season_narratives.state_signature)
  minimum_hold_until TEXT,                  -- the resolver hysteresis hold
  observed_at_utc TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_pns_unique ON program_narrative_state(program_slug, season_year, week);
```

`program_narrative_state` carries `minimum_hold_until` so the lead hysteresis ([[51-team-narrative-engine]] §3e) survives across nightly runs (read last week's row to enforce the 48-hour hold / 12-pt margin).

---

## 4. The coach detector (`coach_pressure.py`, Levels 1–2)

`compute_coach_pressure(db, season, weeks=None)` — mirrors `compute_backometer`. For each profiled team-week:

1. **Tenure context** from `coaching_tenure` (current row). No row → emit `phase=SECURE`/tenure-only, `evidence_level=1` (never disabled silently — record the fact).
2. **Performance Anchor:** wins-vs-expected (SP+/preseason) underperformance ≥1.5 games OR SP+ drop ≥20 since preseason → `perf_anchor_met=1`. *Winning teams can never be HOT (high-expectation friction only).*
3. **Discourse share:** `fire|buyout|extension` keyness as a % of the program's mentions, **14-day rolling**, from doc-level `conversation_documents`/`team_discourse_terms` ([[56-team-fan-ledger-detectors]] §2.5) — **not** `team_conversation_daily` (aggregate).
4. **Phase** via enter/exit thresholds + a minimum 14-day hold (no nightly flip-flop, [[53-program-succession-coaching-carousel]] §4): `CROSSROADS` needs persistent discourse **and** `perf_anchor_met`; `HOT_SEAT` additionally needs ≥2 platforms — **v0 caps escalation at the discourse level and does not assert Level-3 “consensus”/buyout** (that needs Tier-A reporting, post-v0). Speech-act language is the softened set ("persistent calls for a change," sized + dated).

Append a row with `observed_at_utc`; never overwrite the week.

---

## 5. The deterministic resolver (`story_card.py`)

`resolve_lead(db, profile, state, snapshot) -> ProgramNarrativeStateV0`:

1. Build the candidate set from the **enabled** characters (§3g feature contract): `fanbase` (backometer), `rivalry` (calendar proximity + result), `roster` (recruiting/portal deltas), `conference` (standing/realignment), `coach` (`coach_pressure_weekly`). **`institution` is disabled in v0** (no Financial Anchor — [[52-cfb-team-content-model]] §3.2).
2. Score each: `Final = 0.60·EffectiveLevel + 0.40·D` with `D = max(D1, 0.75·D7, 0.50·D42)`; fanbase `D7 = backometer.delta_wow`, `D1` from daily belief delta; the other characters' `D` from their structured deltas. Cold start / no backometer history → `Final = EffectiveLevel` ([[51-team-narrative-engine]] §3e/§3h).
3. **Hard events** (a result, firing, official conference move, rivalry result) → `lead_kind=active`, bypass hysteresis, win by magnitude → evidence → fixed priority `coach>conference>rivalry>roster>fanbase` (§3h).
4. Apply hysteresis vs last week's `program_narrative_state` row (12-pt margin / 48-h hold).
5. `lead_kind`: `quiet` only if `EffectiveLevel<45 AND D<15` AND no active beat; else `standing` (continuing state) or `active`.
6. Compute `standard_gap` (actual standing vs `profile.program_tier` + historical peak). Pick the **BAN** stat object (rivalry record / Standard-Gap / class rank / drought) through the honesty gate ([[50-team-story-card]] §7).
7. **Logline** = template-fill from profile voice (`identity_phrase`, `mantra`, `vocab`) keyed by `(lead_character, timescale, archetype)` — the lexical-injection rule ([[52-cfb-team-content-model]] §9.5), deterministic in v0.
8. `confidence_band` from `backometer.is_low_signal` + the lead's evidence count; `render_rung` capped at 2 (no LLM saga in v0); `quiet` → no logline/BAN, standings sentence only.

Persist to `program_narrative_state` (with `state_signature` for regen-skip).

---

## 6. Render + injection (the one `renderer.py` edit)

`render_story_card_section(db, profile, state, snapshot, npstate) -> str` in `story_card.py`:
- Returns the crown HTML (the mockup markup, [[team-story-card-ui-handoff]]) or `""` on any missing input / exception (wrap the body in try/except → `""`).
- **CSS is a RAW constant** (no `<style>` tags inside it — the ERA_CHAPTER_CSS gotcha, [[55-team-rollout-infra-compat]] §4); the renderer injects it into the page's existing `<style>`.
- v0 ships **Home lens only** (single DOM tree); the National/Rival payload + toggle is a post-v0 phase.

In `renderer.py::_render_page` (the **only** edit):
```python
npstate = build_program_narrative_state(db, profile, state, snapshot, today)   # from story_card.py
crown_html = render_story_card_section(db, profile, state, snapshot, npstate)   # "" on failure
...
module_parts.insert(0, crown_html)   # crown leads; existing modules become the evidence locker
```
Place the `insert(0, …)` immediately before the existing `body = "".join(p for p in module_parts if p and p.strip())` join (`renderer.py:684`). The empty-string filter already drops a `""` crown cleanly.

---

## 7. Pipeline wiring

- **CLI** (`cli.py`, mirror the `compute-backometer` block at `:1515` + dispatch at `:6555`):
  - `compute-coach-pressure --season YYYY [--weeks ...]` → `from cfb_rankings.team_pages.coach_pressure import compute_coach_pressure`.
  - `import-coaching-tenure --csv seeds/coaching_tenure.csv` (CSV-driven seed; like `import-player-honors`, [[CLAUDE.md]] build-script discipline).
- **`build_publish.ps1`:** add a **NON-critical** `Run` for `compute-coach-pressure` near `compute-backometer` (failures must not abort the publish — [[build-failure-philosophy]]). The crown renders inside `build-site` (the `-Critical` step) via the `renderer.py` injection, so it ships in the full snapshot — no post-build patch.
- The resolver + render read the cache tables at render time (no heavy compute in `build-site`).

## 8. Coverage-guard registration (exact)

`SIGNALS` is `list[tuple[slug, label, count_sql]]` (`verify_module_coverage.py:62`); `chronicle_cards` already counts `DISTINCT slug`, so **slug-keyed tables register cleanly — no `team_id` needed** (the doc-55 "both keys" note is belt-and-suspenders, not a requirement). Add:

```python
("coach_pressure", "Coach state (Team Story Card crown)",
 "SELECT COUNT(DISTINCT program_slug) FROM coach_pressure_weekly "
 "WHERE season_year=(SELECT MAX(season_year) FROM coach_pressure_weekly)"),
("story_card_lead", "Team Story Card crown lead",
 "SELECT COUNT(DISTINCT program_slug) FROM program_narrative_state "
 "WHERE season_year=(SELECT MAX(season_year) FROM program_narrative_state)"),
```

New tables are "young," so the guard won't judge them until they establish a baseline — safe to register day one.

## 9. Tests (`tests/test_team_story_card.py`, chronicle/pytest pattern)

- Resolver: rivalry-week → rivalry leads; offseason blue blood, no movement → `standing` (not `quiet`); thin-discourse firing → `active` at rung 2 (the `lead_kind`≠`render_rung` split); two hard events same day → magnitude+priority tiebreak; cold start → `Final=EffectiveLevel`.
- Coach detector: winning team + loud "fire him" → `phase` stays below CROSSROADS (Performance Anchor holds); no `coaching_tenure` row → tenure-only, never crashes.
- Render: missing inputs / raised exception → `render_story_card_section` returns `""` (page renders without the crown).

## 10. Verification / acceptance

1. `python manage.py migrate` applies the 3 migrations idempotently.
2. `python manage.py import-coaching-tenure --csv seeds/coaching_tenure.csv` seeds tenures.
3. `python manage.py compute-coach-pressure --season 2026` populates rows (check `is_low_signal`-style sanity).
4. `python manage.py render-team alabama michigan akron` → inspect the three states (Standing Lead / rivalry / Quiet State) in `output/site/teams/`.
5. `python -m pytest tests/test_team_story_card.py -v` green.
6. `python scripts/verify_module_coverage.py` reports the two new signals.
7. `verify_world_class_team_pages.py` still passes (the crown is **additive** to `team-page` chrome, never reintroduces `premium-team-hero`).

## 11. Out of scope for v0 (explicit, so nothing is silently dropped)

LLM confident-compiler voice · the 4 fan-ledger detectors · the Tribal-Lens National/Rival payload + toggle · "PREVIOUSLY ON" recap · `program_bible` snapshots/changelog · Level-3 hot seat (buyout figures / "names to watch") · the institution character · the carousel chain. Each is a later phase ([[54-integration-with-live-team-system]] §5); v0 logs what it omits via the degradation rung, never fakes it.

## 12. Concurrent-edit safety + gotchas

- **One `renderer.py` edit** (§6); everything else is new files → minimal merge surface vs the live-site window.
- Resolve `team_id` from the snapshot/slug, never stale profile YAML (the live bug).
- Raw-CSS injection (no nested `<style>`).
- This plan writes **no** code/DB/`output/` and runs **no** build/deploy/git — it is the spec for a future build session.

## 13. Sequencing (bite-sized, each ships green)

1. Migrations (1–3) + `migrate`.
2. `coaching_tenure` seed CSV + `import-coaching-tenure`.
3. `coach_pressure.py` + `compute-coach-pressure` CLI + tests.
4. `story_card.py` resolver (reads existing signals + coach pressure) + tests.
5. `render_story_card_section` + the one `renderer.py` injection + render-fallback test.
6. `build_publish.ps1` non-critical Run + coverage-guard tuples.
7. Render-verify the three archetypes; confirm guardrails green.

## 14. Provenance

Grounded 2026-06-11 in `team_pages/renderer.py` (`render_team_page`/`_render_page`/the `module_parts` join), `cli.py` (`compute-backometer` parser+dispatch), `scripts/verify_module_coverage.py` (`SIGNALS` 3-tuple format, `chronicle_cards` counts `DISTINCT slug`), `backometer.py`, and `build_publish.ps1`. Implements the v0 slice of [[54-integration-with-live-team-system]] §4 within the locked specs [[50-team-story-card]]–[[58-team-build-philosophy]] and the UI handoff [[team-story-card-ui-handoff]].
