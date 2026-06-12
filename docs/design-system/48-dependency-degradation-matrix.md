# 48 — Module Dependency & Degradation Matrix

_Status: RELIABILITY SPEC (v1). Created 2026-06-11. For every Story-Card module: what it reads, what refreshes it, how fresh it must be, and exactly how it degrades when data is stale/empty/missing. The pipeline degrades SILENTLY by design ([[build-failure-philosophy]]), so every module needs a defined fallback — and the card needs a defined fallback ladder. Planning only._

---

## 0. The two rules

1. **A module never crashes a page.** Missing/empty data → the module returns `""` and is dropped from composition (salience-driven presence, [[42-player-narrative-engine]] §4b). Matches the ~30 existing `new_*_html` sections.
2. **The card never shows broken.** It degrades down a ladder (§3), never to a half-rendered or lying card.

---

## 1. The dependency matrix

| Card module | Reads (tables) | Refreshed by | Cadence | If STALE | If EMPTY/MISSING |
|---|---|---|---|---|---|
| Identity anchor | `players`, `roster_entries` | collect.ps1 (CFBD roster) | on roster change | use last-known | minimal name-only header |
| Key-stat chips / BAN | `player_season_stats`, `player_value_metrics`, `player_usage_season` | collect (CFBD week, in-season) | weekly in-season; frozen offseason | offseason: label "2025" (fine) | drop BAN; chips show what exists |
| Aura (perception↔production) | `player_aura_weekly` | build_publish **F.5** `compute-aura` | nightly | use latest week | drop the tension module |
| Succession (throne / shoes / clock) | `roster_entries`, `player_depth_chart_2026`, `transfer_entries`, `player_season_stats` + new `player_succession` | collect + new detector (enrich) | nightly; depth chart partial | confidence-gate the Clock | drop succession; keep identity |
| Fan ledgers | `conversation_document_targets`, `player_week_conversation_features`, new `player_ledger_scores` | build_publish **E** + **E.7–E.9** + new detector | nightly | use last fired week | below floor → low-data strip |
| Quote ("in their words") | `conversation_document_targets`/features | build_publish E | nightly | last good quote | drop quote block |
| Hope / recruiting / NIL | `player_recruiting_profiles`, `player_nil_valuations`, `player_award_watch_2026` | collect (recruiting) + **F.6** NIL scrape (non-critical) | recruiting on change; NIL nightly best-effort | NIL: keep last snapshot | drop NIL line; recruiting persists |
| Offseason / outlook | `player_depth_chart_2026`, `team_preview_snapshot`, `player_award_watch_2026` | `build-team-preview-layer` (step I) + `outlook_2026` | nightly | use latest | drop outlook cells that lack data |
| Why-now / temporal | `chronicle_calendar_pressure`, `fanbase_mood_weekly`, `player_bible_snapshots` | build_publish nightly | nightly | generic why-now | omit why-now (logline still shows) |
| Tribal lens | `conversation_document_targets.audience_bucket` | collect/enrich | nightly | last slices | single (national) POV only |
| LLM voice (logline/recap) | `player_signature_story`, `player_narrative_arc`, new `player_bible` | build_publish **H** + new gen (Ollama) | top-N nightly + content-hash regen | **serve LKG** ([[42]] §LKG) | deterministic-only card (no prose) |

---

## 2. Freshness budget (how stale is too stale)

- **In-season:** stats + discourse should be ≤ 1 week old. The "why-now" *demands* current-week data; if the newest data is > 1 week stale, the card **honestly labels "as of <date>"** (card spec §9 freshness state) rather than implying currency. A stale-but-labeled card beats a fresh-looking lie.
- **Offseason:** weekly-ish is fine — the card is projective ("days to kickoff"). Stale stats are expected (last season's) and correctly framed as history.
- **Live/game-day:** out of scope for v1 (the card is daily-batch). Flag the open mid-game-staleness item ([[41-player-story-card]] §9) — don't pretend to be live.

---

## 3. The card fallback ladder

The card always renders *something* true, never broken:

```
1. FULL        rich data + fresh LLM voice + tribal lens
2. REDUCED     deterministic modules only (LLM stale → LKG;
               low-salience modules dropped) — still bespoke by composition
3. LOW-DATA    factual bio strip (identity + one real stat),
               no drama (below ledger floor) — [[41-player-story-card]] §5
4. OMIT        "" graceful fallback (no data / render error) —
               the page renders without the card, never with a broken one
```

Composition picks the highest rung the data supports. The drop from 1→2 is invisible to the reader (it just looks like a different, simpler card); 2→3 is the long-tail honest path; 4 is the safety net.

---

## 4. Coverage-guard registration (so silent death is caught)

The new tables must be added to `verify_module_coverage.py` (player-count variant — it currently counts `team_id`):

- `player_ledger_scores` — distinct players with a fired ledger at latest week
- `player_succession` — distinct teams with a detected throne-line
- `player_bible` — distinct players with a current bible
- `narrative_beats` — distinct players with beats at latest week

Without this, the silent-degradation philosophy hides a dead engine for weeks ([[build-failure-philosophy]], the 2026-06-11 incident). New tables are "young" and unjudged until they establish a baseline — safe to register from day one.

---

## 5. Critical-path discipline (recap)

- Every new compute step = **non-critical** `Run` in build_publish.ps1 → a detector failure logs + continues, never blocks the deploy.
- `build-site` is `-Critical` and wipes `output/site`; the card renders inside it with `""` fallback, so a card bug degrades to "no card," not "no deploy" or "broken page."
- The full-snapshot deploy means the card must render across all player pages or risk clobber ([[deploy-clobber-root-cause]]) — the `""` fallback handles per-page gaps cleanly.

---

## 6. The single failure that would be invisible (and how we catch it)

The worst case isn't a crash — it's the engine **silently producing nothing** while the build stays green (sources fine, render fine, but `player_ledger_scores` quietly empty). The defense is the trio from [[46-rollout-and-infra-compat]] §7: non-critical Run (won't block) + `""` render fallback (won't break) + **coverage-guard entry (won't hide)**. The third is the one that's easy to forget and the only one that surfaces a dead engine.

## 7. Provenance

Derived from the live `build_publish.ps1` stage map, the table inventory, `verify_module_coverage.py`, and the graceful-degradation philosophy ([[build-failure-philosophy]]). Builds on [[42-player-narrative-engine]], [[45-integration-with-live-system]], [[46-rollout-and-infra-compat]], [[47-fan-ledger-detectors]].
