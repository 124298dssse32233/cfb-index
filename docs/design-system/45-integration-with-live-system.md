# 45 — Integration: How the Story Card Fits the Live System

_Status: INTEGRATION MAP (v1). Created 2026-06-11 from a real audit of the running code + pipeline. Answers "how does all of this (docs 41–44) fit into what we already collect, generate, and render?" The headline: **~60% already exists and runs nightly.** The Story Card is a consolidation + elevation, not a greenfield build._

---

## 0. The big realization

The narrative engine is **not** a from-scratch project. The box already:
- generates grounded LLM prose per player via local Ollama, cached + idempotent (`signature_story_generator.py`, `narrative_arc_generator.py`);
- runs a full evidence/eval/trust/LKG pipeline (`chronicle/`, 16 modules);
- projects the 2026 depth chart, supporting cast, and award watch (`outlook_2026.py`);
- renders ~30 modular player-page sections via a proven injection pattern;
- collects the discourse corpus + sentiment + keyness + audience tags nightly.

The Story Card (docs 41–44) is: **(a)** unify the scattered narrative modules into one top-of-page card, **(b)** add the CFB-native deterministic detectors (Succession §44, Fan Ledgers §43), **(c)** add the composition/archetype + persistent-bible layer (§42). Most of the hard infrastructure is done.

---

## 1. The live pipeline (where everything runs)

```
collect.ps1   (Task Scheduler, ~5:00 AM)
  → CFBD pulls (stats, transfers, recruiting, NIL, awards, draft, depth charts)
  → discourse pulls (Reddit 146k, Bluesky, YouTube, podcasts, news, Wikipedia)
  → enrich: relevance ML, CardiffNLP sentiment, player-name tagging, keyness

build_publish.ps1   (Task Scheduler, ~9:00 AM)
  → GENERATE step: local-Ollama generators write to cache tables
      (build-signature-story-board, narrative-arc, generate-chronicle/-visuals)
  → RENDER step: reporting.py + team_pages emit ~69k HTML pages
  → DEPLOY: full-snapshot publish to Vercel (publish_to_vercel.ps1)
```

The Story Card slots in at the **GENERATE** step (its detectors + LLM voice write to cache tables) and the **RENDER** step (a new top-of-page section). The deterministic CFB detectors can also live in the **enrich** stage of `collect.ps1`.

---

## 2. What already exists → what we reuse (the inventory)

| Spec concept (docs 41–44) | Already live | Reuse / extend |
|---|---|---|
| LLM voice, grounded, cached, idempotent ([[42]] writer + event-trigger) | `signature_story_generator.py` (→ `player_signature_story`), `narrative_arc_generator.py` (→ `player_narrative_arc`); Ollama mistral-nemo; content-hash regen | **Extend** — the card's prose is this pattern with the CFB content model fed in |
| Evidence / source-trust / FActScore / LKG / antislop / banlist ([[42]] §4–10) | `chronicle/`: `source_trust.py`, `evidence_sources.py`, `retriever.py`, `eval.py`, `lkg.py`, `antislop.py` | **Reuse** — point the engine's grounding/eval at these |
| Offseason / forward-looking ([[43]] §5) | `outlook_2026.py` (depth chart, supporting cast, award watch; reads `player_depth_chart_2026`, `team_preview_snapshot`, `player_award_watch_2026`) | **Extend** into the Hope-Economy offseason mode |
| Succession data ([[44]]) | `player_depth_chart_2026`, `roster_entries`, `transfer_entries`; `generate-chronicle-visuals` already builds a **"Roster Replacement Grid"** | **Build on** — the throne-line/Filling-the-Shoes detector |
| Discourse plane + ledgers ([[42]] §1, [[43]] §1) | `conversation_documents/_targets`, `player_week_conversation_features`, `fanbase_mood_weekly`, `team_discourse_era_terms/_clusters`, keyness engine, `audience_bucket` (local/rival) | **Reuse** — the ledger detectors read these |
| Perception vs production ([[43]] §1.4) | `aura_module.py` (`player_aura_weekly`) | **Reuse** — it IS the Judgment/Expectation surface |
| Real fan quotes ([[41]] card) | `in_their_words.py` | **Reuse** as the quote module |
| Career destination / draft / portal | `where_ended_up.py`, `status_strip.py` | **Reuse** in the bible's fate fields |
| Comparison | `peer_comparator.py`, `mirror_match.py` | **Reuse / extend** for predecessor comparison |
| Trajectories | `career_arc.py`, `development_trajectory.py`, `heisman_trajectory.py`, `sparklines.py` | **Reuse** for the Arc Spark |
| Render injection ([[41]]) | `page_data["new_*_html"]` keys in `reporting.py` (~L9310–9450), graceful `""` fallback | **Add** `new_story_card_html` at the top of the player template |

---

## 3. What is genuinely net-new (the build list)

1. **The unified Story Card renderer** — one top-of-page section + the composition/archetype logic ([[41]] §4, [[42]] §4b). Consolidates aura + in_their_words + outlook + where_ended_up + a lede into one card.
2. **The Succession Engine** ([[44]]) — deterministic throne-line detection, Filling-the-Shoes comparison, the Clock. Pure Python over `roster_entries`/`player_season_stats`/`transfer_entries`/`player_depth_chart_2026`.
3. **The Fan Ledger detectors** ([[43]] §1) — keyness lexicons + thresholds that fire Hope/Grievance/Belonging/Judgment/Grudge. Reads the discourse plane.
4. **The two-axis classifier + archetype** ([[43]] §2, [[42]] §4b) — maps a player to Expectation×Belonging → archetype → card composition.
5. **`narrative_beats` + `player_bible` tables** ([[42]] §5,7) — the persistent state + snapshots (the changelog). Extends the existing per-module cache tables into a unified state object.
6. **The independent coverage check + the why-now heartbeat + state-composition** ([[42]] §4c,5).
7. **The Tribal Lens** ([[43]] §4) — POV rendering off `audience_bucket` (already collected).

Net-new is mostly **deterministic Python** + new tables. The LLM layer is already proven; it just gets richer inputs.

---

## 4. The smallest shippable slice (v0 — no new LLM, no risk)

A deterministic Story Card that ships into the live render today:
- a new `player_pages/story_card.py` → `page_data["new_story_card_html"]`, injected at the top of the player template;
- composed from **existing** modules (aura + outlook + where_ended_up + a real quote) + **one new** deterministic detector: the **Succession throne-line + Filling-the-Shoes read** (68%-of-rooms data proves it works);
- archetype/composition picks the shape; no model in the loop;
- graceful `""` fallback (matches the existing pattern) so it can't break a page.

This proves the bespoke-composition thesis on real pages with zero LLM/eval risk. The LLM voice (extending `signature_story_generator`) and the ledgers layer on after.

---

## 5. Phased build, mapped to the pipeline

| Phase | What | Where it runs |
|---|---|---|
| **0** | `story_card.py` renderer + composition skeleton; reuse existing modules | RENDER (reporting.py injection) |
| **1** | Succession Engine (throne-line, Filling-the-Shoes, the Clock) → `throne_line`/`succession` tables | enrich (collect.ps1) |
| **2** | Fan Ledger detectors (keyness lexicons) → ledger scores on `narrative_beats` | enrich |
| **3** | two-axis classifier + archetype → drives composition | GENERATE |
| **4** | `player_bible` + snapshots (changelog) + why-now heartbeat | GENERATE |
| **5** | rich LLM voice (extend `signature_story_generator` with the CFB content model + tribal lens) | GENERATE (Ollama) |
| **6** | independent coverage check + eval gate (reuse `chronicle/eval.py`, `lkg.py`) | GENERATE |

Each phase ships standalone and degrades gracefully.

---

## 6. Honest risks / watch-items

- **`player_id` instability across re-ingest** = linkrot (known issue, [[deploy-clobber-root-cause]]). The bible must key on a stable anchor, not raw `player_id`, or the changelog breaks on re-ingest.
- **Relevance gate matters** — top-engagement corpus posts include off-topic community/political content; the ledger detectors must run on relevance-filtered docs.
- **Depth-chart seeding is partial** — `player_depth_chart_2026` isn't fully seeded for all teams; confidence-gate the Clock/heir-apparent where it's thin.
- **Full-snapshot deploys** — the story card must render for every player section or risk clobbering ([[deploy-clobber-root-cause]]); ship behind the graceful-`""` pattern.
- **Ollama throughput** — 23k players can't all get fresh LLM voice nightly; the tier policy ([[42]] §10) + content-hash regen (already the pattern) keep it to top-N + changed.

---

## 7. Bottom line

The vision in docs 41–44 lands on a system that already has the LLM generation loop, the eval/trust/LKG machinery, the offseason projector, the discourse corpus, and the render injection. **The first real build is one deterministic module** (`story_card.py` + the Succession detector) that consolidates what's there and proves the composition — everything else layers onto proven infrastructure.

## 8. Provenance

Audited 2026-06-11 against live `src/cfb_rankings/{chronicle,player_pages}/`, `reporting.py` injection points, `cli.py` generation subcommands, and `scripts/build_publish.ps1`. Builds on [[41-player-story-card]], [[42-player-narrative-engine]], [[43-cfb-native-content-model]], [[44-succession-engine]].
