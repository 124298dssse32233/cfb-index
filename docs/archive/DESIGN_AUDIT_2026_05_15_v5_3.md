# CFB Index — v5.3 Quality-Maximization Addendum

**Date:** 2026-05-15
**Author:** Claude (synthesis of 3 quality-maximization investigators)
**Status:** Supersedes v5.2 Parts 1.1, 2 (cost), 3 (roadmap), and adds Parts 11-13. All other v5.2 content remains canonical.
**Trigger:** Owner directive: "the most visible LLM writing and analysis has the absolute best highest quality LLM compute usage that I can handle for my 20x plan — i don't want anything anywhere to be low quality."

---

## TL;DR — What v5.3 changes from v5.2

| Dimension | v5.2 | **v5.3** |
|---|---|---|
| LLM surfaces audited | 12 | **37 (all call sites in codebase, no surface left low-tier)** |
| Wire factual restatement | Haiku 4.5 | **Sonnet 4.6** (most-visible recurring surface; quality > cost) |
| Chronicle profiled programs (top 2 cards/team) | Haiku 4.5 | **Opus 4.7 + 4K thinking + critique loop** |
| Storyline thread chapters (6-8/wk) | Sonnet 4.6 | **Opus 4.7 + 8K thinking + Pattern E continuity** |
| Daily edition lead (all 7/wk, not just tentpole) | Sonnet 4.6 / Opus tentpole-only | **Opus 4.7 + 8K thinking + critique loop, every day** |
| Mailbag standard (~8/wk) | Sonnet 4.6 | **Opus 4.7 + 4K thinking + critique** |
| Heisman weekly | Sonnet 4.6 | **Opus 4.7 + 8K thinking + critique** |
| Edition cover essay | Opus 4.7 single-shot | **Opus 4.7 + 16K thinking + Pattern D adversarial (2-pass critique)** |
| Multi-agent critique loops | none specified | **`quality_loop.py` module with 5 patterns + 5 critic roles** |
| Proprietary data integration | implicit | **Per-surface data manifests (12 surfaces) make outputs unfakeable** |
| Steady-state cost (API-rate equivalent) | ~$170/yr | **~$1,200-1,400/yr post-caching** (still inside $2,400/yr Agent SDK credit) |
| Agent SDK credit utilization | ~7% | **~50-60%** (leaves ~$1,000/yr spike headroom) |
| Incremental cash cost | $0 | **$0** (unchanged — Agent SDK credit covers all) |

**The thesis:** With Max 20x covering the workload, the constraint stops being cost and becomes "is the LLM call configured to produce world-class output?" Three levers matter — model selection, extended thinking budget, critique loops — and the proprietary data integration matters as much as any of them.

---

## Part 1 · The 37-Surface Quality Matrix (supersedes v5.2 Part 1.1)

Every Claude call in the codebase, ranked by reader visibility and routed for quality.

### Tier 1 — Opus 4.7 + extended thinking + critique loop (the signature surfaces)

| # | Surface | Volume | Model | Thinking | Critique | Current code |
|---|---|---|---|---|---|---|
| 1 | **Edition cover essay** (drop-cap longform) | 1/wk | Opus 4.7 | **16K** | **Pattern D adversarial** (voice + headline + factuality + engagement) | `editions/seeds.py:63` literal today |
| 2 | **Edition feature blocks** (5 slots × 1/wk) | 5/wk | Opus 4.7 | 8K | Pattern C (voice + headline + factuality) | `editions/cli.py:55-66` |
| 3 | **Daily edition lead essay (rank-1)** | 7/wk | Opus 4.7 | 8K | Pattern C | `daily/synthesizer.py:221` (currently tentpole-only Opus) |
| 4 | **Daily edition supporting takes (rank-2, rank-3)** | 14/wk | Opus 4.7 | 4K | Pattern C | `daily/synthesizer.py` |
| 5 | **Heisman weekly narrative** | 15/season | Opus 4.7 | 8K | Pattern C | new (not yet wired) |
| 6 | **Mailbag civic/format/realignment answers** | 1-2/wk | Opus 4.7 | 8K | Pattern C | `mailbag/synthesizer.py:55` (already Opus) |
| 7 | **Mailbag standard answers** | 8-9/wk | Opus 4.7 | 4K | Pattern C | `mailbag/synthesizer.py` (currently Sonnet) |
| 8 | **Reaction stories — surprise≥90 / blue-blood** | 1-2/wk | Opus 4.7 | 8K | Pattern C | `reactions/synthesizer.py:328` (already Opus) |
| 9 | **Reaction stories — standard** | 3-4/wk | Opus 4.7 | 4K | Pattern C | `reactions/synthesizer.py` (currently Sonnet) |
| 10 | **Storyline thread chapters** | 6-8/wk | Opus 4.7 | 8K | **Pattern E continuity** | `storylines/chapter_authoring.py` + `cli.py:1680` (currently Sonnet — **biggest upgrade in the table**) |
| 11 | **Canon entries — top-10 (× 3 lists)** | 30 one-time + refresh | Opus 4.7 | 16K | Pattern D | `canon/generator.py` |
| 12 | **Canon entries — ranks 11-100** | ~270 one-time + refresh | Opus 4.7 | 4K | Pattern C | `canon/generator.py` |
| 13 | **Team narratives — `generate_state_of_team`** | ~70/yr | Opus 4.7 | 8K | Pattern C | `narrative_generator.py:107` (currently Sonnet) |
| 14 | **Post-game state-of-team** (GameRecapHero ¶3) | ~30/wk | Opus 4.7 | 8K | Pattern C | `narrative_generator.py:155` (already Opus) |
| 15 | **Pulse lede (all entities)** | 15/wk | Opus 4.7 | 4K | Pattern C | `pulse_lede.py:27-28` (currently Opus blue-bloods, Sonnet others — upgrade all to Opus) |
| 16 | **Pulse themes — Stage 2 ranker/writer** | 45/wk (15 × 3 themes) | Opus 4.7 | 4K | Pattern C | `pulse_themes.py:27` (currently Sonnet) |
| 17 | **Receipts — Best Calls (both tiers)** | ~20/wk | Opus 4.7 | 4K | Pattern C | `receipts/best_calls.py:181-183` (currently Opus 4.5 / Sonnet 4.5 — **bump versions**) |
| 18 | **Chronicle cards — top 2 per profiled program** | 17 × 35 = 595/season | Opus 4.7 | 4K | Pattern E continuity | `chronicle_generator.py:223-224` (Opus only for blue-bloods today — extend to all profiled) |
| 19 | **Chronicle game-edition — anomaly card** | ~30/wk | Opus 4.7 | 4K | Pattern E | `chronicle_game_edition.py:88-90` (drop blue-blood-only restriction) |
| 20 | **Historical season — title/thesis/legacy** | 17 × 12 = 204 one-time | Opus 4.7 | 8K | Pattern C | `historical_season_content.py:11` (per docstring, stub today) |
| 21 | **Player season narrative** (Accolade Lens / Savant card) | ~50 surfaced players × refresh | Opus 4.7 | 8K | Pattern C | new (per `PLAYER_PAGE_WORLD_CLASS_BRIEF.md`) |
| 22 | **Wire "why it matters" sidebar** (when authored caption missing) | ~20/wk | Opus 4.7 | 0 | Pattern C (1-pass) | `wire/editorial.py:42` |
| 23 | **Trophy SVG glyph generation** | 25 one-time (Sprint v5-0) | Opus 4.7 | 8K | Pattern D (visual rubric) | one-time Sprint v5-0 |
| 24 | **Headline doctor** (rewrites failed §2.9 candidates) | ~10/wk depending on fail-rate | Opus 4.7 | 4K | (it IS the critique pass) | new module |

### Tier 2 — Sonnet 4.6 + voice-validator (the consistent-quality bulk)

| # | Surface | Volume | Model | Critique | Current code |
|---|---|---|---|---|---|
| 25 | **Wire factual restatement** | 420/wk in-season | **Sonnet 4.6** | Pattern A (regex only) | `wire/editorial.py:37-48` (v5.2 said Haiku — overruled here for visibility) |
| 26 | **Chronicle cards — ranks 3-5 per profiled program** | ~17 × ~3 × 35 = 1,785/season | Sonnet 4.6 | Pattern B | `chronicle_generator.py` |
| 27 | **Chronicle game-edition — moment / flashpoint** | ~60/wk | Sonnet 4.6 | Pattern B | `chronicle_game_edition.py` |
| 28 | **Historical season — defining moments** | ~600 one-time | Sonnet 4.6 | Pattern A | `historical_season_content.py` |
| 29 | **Receipts — source voice summary** | ~50 × quarterly | Sonnet 4.6 | Pattern A | `receipts/source_profiles.py:198` (currently Sonnet 4.5 — bump version) |
| 30 | **Game recap diagnosis stat-card labels** (4 cards × ~30/wk) | ~120/wk | Sonnet 4.6 | Pattern A | currently template — promote when LLM path lands |

### Tier 3 — Haiku 4.5 (narrow factual/judge tasks only)

| # | Surface | Volume | Model | Critique | Current code |
|---|---|---|---|---|---|
| 31 | **Pulse themes — Stage 1 Haiku scan** (JSON candidate extraction) | 15/wk | Haiku 4.5 | none | `pulse_themes.py:26` |
| 32 | **Player-target sentiment classifier** (positive/neutral/negative) | one-time + refresh | Haiku 4.5 | none | `sentiment_classifier.py:28` |
| 33 | **Receipts Stage 1 — claim classifier (JSON batch)** | ongoing | Haiku 4.5 | none | `receipts/extract.py:162` |
| 34 | **Voice-validator advisory layer** (over regex) | every output ~1,300/wk | Haiku 4.5 | n/a | new — supplements regex gate |
| 35 | **Headline-quality judge** (5-question rubric → JSON) | every headline ~1,300/wk | Haiku 4.5 | n/a | new — feeds the Headline Doctor (#24) |
| 36 | **Voice critic** (used inside Pattern B/C loops) | inside loops | Haiku 4.5 (Sonnet for Tier-1) | n/a | new module |
| 37 | **Storyline thread offline-stub / draft scaffold** | fallback path only | (no LLM) | n/a | `chapter_authoring.py:377` |

### Diff vs current code state

Six existing call sites pin to outdated model versions and need bumping in Sprint v5-1:
- `pulse_lede.py:27` — Opus 4.5 → Opus 4.7
- `pulse_lede.py:28` — Sonnet 4.5 → Opus 4.7 (tier upgrade, see #15)
- `pulse_themes.py:26` — Haiku 4.5 (keep, but update class binding)
- `pulse_themes.py:27` — Sonnet 4.5 → Opus 4.7 (tier upgrade, see #16)
- `receipts/best_calls.py:181` — Opus 4.5 → Opus 4.7
- `receipts/best_calls.py:183` — Sonnet 4.5 → Opus 4.7 (tier upgrade, see #17)
- `receipts/source_profiles.py:198` — Sonnet 4.5 → Sonnet 4.6
- `chronicle_generator.py:223-224` — Sonnet → Opus 4.7 for top 2 cards per profiled program
- `chronicle_game_edition.py:88-90` — drop blue-blood-only Opus restriction
- `narrative_generator.py:107` — Sonnet → Opus 4.7
- `reactions/synthesizer.py` — Sonnet → Opus 4.7 for standard reactions
- `mailbag/synthesizer.py` — Sonnet → Opus 4.7 for standard answers

This is the single largest model-routing pass in the codebase. **Lands as a single PR in Sprint v5-1.**

---

## Part 2 · Cost Architecture (supersedes v5.2 Part 2)

### Steady-state workload at v5.3 routing

Token assumptions (per Investigator C): 2K input + 1K output per gen call; 1.5K input + 300 output per critic call; extended thinking budgets billed at output rate.

| Pattern | Volume share | Annual API-equivalent cost |
|---|---|---|
| Pattern A (single-shot) — Wire, Canon tail, judges | ~70% of calls | ~$185/yr |
| Pattern B (single critic) — Tier-2 narratives, Chronicle 3-5 | ~25% of calls | ~$1,200/yr |
| Pattern C (critic-revise) — Tier-1 standard | ~4% of calls | ~$470/yr |
| Pattern D (adversarial) — Edition cover only | <0.1% of calls | ~$31/yr |
| Pattern E (continuity) — Storylines + Chronicle profiled | ~1% of calls | ~$195/yr |
| **Total (no caching)** | | **~$2,025/yr** |
| **Total (post-caching, 30-40% reduction)** | | **~$1,215-1,420/yr** |

### Against the Agent SDK credit

| Line | Annual |
|---|---|
| Max 20x Agent SDK credit | $2,400/yr ($200/mo × 12) |
| v5.3 workload at API rates | $1,200-1,400/yr (post-caching) |
| Headroom | **$1,000-1,200/yr (~50% of monthly credit unused)** |

The headroom matters:
- Backfill enrichment passes (full regenerate): ~$30-50 per run. Affordable monthly.
- Trial-and-error during prompt iteration: free (development happens against the same credit pool).
- Critic-loop escalation paths (Rung 1 model-tier escalation): rare but bounded.
- Spike weeks (CFP, transfer portal frenzy): 2-3× normal load fits.

**Net incremental cost: $0/yr (unchanged from v5.2).** Agent SDK credit covers the entire program at ~50-60% utilization.

### Why not push utilization higher?

Three reasons to leave the 40-50% headroom unused:
1. **Spike resilience.** December (CFP) and January (transfer portal + bowl reactions) easily 2-3× normal load.
2. **Critic-loop circuit breaker.** When Rung 1 escalates Sonnet → Opus on a failed critic, that call costs 4-5× the baseline. The budget envelope must absorb this without weekly halts.
3. **Iteration freedom.** As prompts get tuned across the season, regenerating affected surfaces (e.g., re-run all 595/season Chronicle cards under a new prompt template) needs to be a free operation, not a budget-blocking decision.

### `quality_gates.llm_weekly_spend_ceiling_usd` — the safety net

Default to **$50/wk** in the migrations table. This is a circuit breaker, not an operational target. v5.3's steady-state weekly is ~$25-27/wk after caching; the $50 ceiling means a runaway prompt loop or unexpected workload spike trips the brake before the Agent SDK monthly is dented.

Per-surface ceilings (more granular, applied inside `quality_loop.py`):

```python
WEEKLY_CEILINGS_CENTS = {
    "tier1.edition_cover":      1000,   # $10/wk (Pattern D headroom)
    "tier1.daily_lead":          500,
    "tier1.heisman_weekly":      300,
    "tier1.mailbag":             800,
    "tier1.reaction_story":      500,
    "tier1.storyline_chapter":   400,
    "tier1.canon_top10":         200,
    "tier1.chronicle_profiled":  500,
    "tier2.team_narrative":      200,
    "tier2.pulse_state":         200,
    "tier2.chronicle_unprofiled":1500,
    "tier3.wire":                200,
    "tier3.canon_tail":          200,
}
```

---

## Part 3 · The `quality_loop.py` Architecture

Net-new module landing in Sprint v5-1. Peer of `llm_runtime.py`, not a replacement. Eight existing `generate_with_voice_check` call sites stay on contract; quality_loop.py wraps them.

### Five loop patterns

**Pattern A — Single-shot + regex voice validation.**
For Wire factual, Canon tail, all Tier-3 judges. Output → existing `generate_with_voice_check` → regex gate → emit. Cost: ~$0.006/call.

**Pattern B — Single-critic loop.**
Generate (Sonnet 4.6) → Haiku critic on one role (voice OR headline OR factuality) → regenerate once if score < 7 → emit. For Tier-2 narratives, Chronicle ranks 3-5, source-voice summaries. Cost: ~$0.04/call.

**Pattern C — Critic-revise (default Tier-1 loop).**
Generate (Opus 4.7 + extended thinking) → Opus critics on voice + headline + factuality (3 critic calls) → revise pass incorporating all critiques → re-critique → emit. Cost: ~$0.40/call. **This is the dominant Tier-1 surface pattern.**

**Pattern D — Adversarial (Edition cover only).**
Generate (Opus 4.7 + 16K thinking) → Critic Group A (voice + headline + factuality, structural rubric) + Critic B (engagement, "would a sophisticated CFB reader linger?") → revise satisfying both critic groups → re-score → emit. Cost: ~$0.60/call.

**Pattern E — Continuity-grounded (Storylines + Chronicle profiled).**
Pre-pass: load last 3 chapters/cards for this thread. Inject as system-prompt "THREAD HISTORY" block + "NAMED-ENTITY LEDGER" (preserves recurring phrasing — "the standard" stays "the standard", not "the bar"). Then Pattern C with continuity-critic added. Cost: ~$0.15/call.

### Five critic roles (each returns JSON `{passed, score 0-10, issues[], suggested_revisions}`)

1. **Voice critic** (Haiku for Tier-2, Sonnet for Tier-1) — banned-phrase + register fit. Strict; auto-fail on banned-phrase hit.
2. **Headline critic** (Haiku) — 5-question rubric from v4 §2.9. Strict; 2 points per YES, fail < 8.
3. **Factuality critic** (Sonnet) — given source observations, every numeric/dated claim must be traceable. Mild paraphrase OK; wholesale invention not.
4. **Engagement critic** (Opus, Pattern D only) — "would a sophisticated CFB reader stop scrolling?" Most subjective, used only on Edition cover.
5. **Continuity critic** (Sonnet, Pattern E only) — does this chapter advance the thread? Contradict prior? Rename existing entities?

Each critic has a full system prompt template (~30-50 lines each); see Sprint v5-1 task list below for delivery. Investigator C's report contains the verbatim drafts; they go directly into `quality_loop.py` constants.

### Circuit breakers (3-rung escalation)

- **Rung 1** — Consecutive critic failures ≥ 2: Escalate gen-model one tier (Sonnet → Opus, Haiku → Sonnet) and retry once.
- **Rung 2** — Consecutive critic failures ≥ 3 after escalation: Fall back to seeds.py / human-authored alternative. Write to `editorial_overrides` with `override_kind='circuit'`. Surface renders seed; telemetry marks `fell_back=true`.
- **Rung 3** — `weekly_spend_cents > ceiling[surface]`: Halt loop for the rest of the week. Subsequent calls return immediately with `reason='weekly_ceiling'`. Weekly digest issue surfaces the trip.

### Telemetry — extends existing `llm_usage_log.append_llm_usage()`

New fields on every loop call: `loop_pattern`, `critic_roles_used`, `critic_scores`, `revise_count`, `fell_back`, `fallback_reason`.

Weekly digest reads `output/_logs/llm_usage_*.jsonl` and reports per-surface fall-back rates, average critic scores, revise counts. Surfaces a quality regression before readers notice.

---

## Part 4 · Proprietary Data Integration Manifest (NEW — supersedes v5.2 §1.1 prompt-context discussion)

Generic Opus output isn't world-class. **Opus with 6 years of contextualized proprietary data is world-class.** Every visible surface's prompt context must pull from specific tables to be unfakeable.

### Cross-cutting rules (apply to all 24 Tier-1 surfaces)

1. **Always inject prior-N continuity rows.** Query `editions/edition_features/team_chronicle_observations/storyline_chapters` for last 30-90 days of coverage of the same entity. Prevents restating.
2. **Always inject 6-year same-week comparator.** `fanbase_mood_weekly`, `power_ratings_weekly`, `heisman_rankings_weekly`, `lexicon_weekly` carry 6+ years of history. Surface "this week N years ago" reachable in every Tier-1 prompt.
3. **Always inject cohort transitions, not static values.** The *delta* in `fanbase_cohort_weekly` ("Smug → Unhinged 0.6") is the story.
4. **Always include verbatim source quotes** from `conversation_documents` + `source_observations`. Enables the "≥N cited sources verbatim" requirement that voice_validator gates. Prevents hallucinated attribution.
5. **For 17 profiled programs**, always inject `team_profile.signature_metrics_ladder` *current values* (not just metric names). The program speaks in its own units.

### Per-surface manifests (12 priority surfaces)

#### Edition cover essay (1/wk, Pattern D)

| Table | Pull |
|---|---|
| `editions` + `edition_features` | Prior 4 weeks' cover essays (title, dek, body excerpt, theme_tag) |
| `fanbase_mood_weekly` ⋈ `fanbase_cohort_weekly` | Per-conference cohort-mood dumbbell (Δ this week vs trailing 4w) |
| `power_ratings_weekly` (latest `model_runs`) | Top-25 + biggest week-over-week movers, BT vs SP+ vs FPI disagreements |
| `storyline_threads` + `storyline_chapters` | Active arcs (slug, title, dek, last_chapter_at) — the in-flight threads to weave |
| `wire_entries` last 7d, `impact_label='MAJOR'` | Top transactions/news with pre-authored `why_it_matters` |
| `receipts` resolved this week | High `surprise_index` calls to re-cite |
| `team_chronicle_observations` last 14d (all 17 programs) | Top 8-10 by `evidence_strength × resonance_score` for verbatim moments |
| `season_phase` table + `offseason_week_map` | Calendar frame (NSD / spring / dead / bowls / regular) |

**Unique edge:** No competitor has per-conference cohort-mood dumbbell going back 6 years. Combined with prior-cover continuity + storyline-arc awareness, every cover reads like Week N of a serialized magazine.

#### Daily edition lead essay (rank-1, 7/wk, Pattern C)

| Table | Pull |
|---|---|
| Existing `daily/synthesizer.py` bundle | wire_candidates, thread_candidates, pulse_spikes, resolved_receipts |
| `fanbase_mood_weekly` Δ7d **AND same week last year** | "Where are fans today vs 365 days ago" hook |
| `fanbase_cohort_weekly` | Cohort transition deltas (>0.3 threshold) |
| `team_cohort_divergence_week` | Stat-folks vs casuals vs die-hards split for headline entity |
| `archive_threads` (Arctic Shift) | Top Reddit thread from same calendar week N years ago |
| `daily_editions` last 14d | Yesterday's headlines — non-repetition enforcement |
| `power_ratings_weekly` 7d Δ | For the take-1 entity |

#### Heisman weekly narrative (1/wk × 15 wks, Pattern C)

| Table | Pull |
|---|---|
| `heisman_rankings_weekly` | Top-10 with vote-share Δ vs last week |
| `heisman_market_odds_weekly` | Market vs model implied-probability deltas |
| `heisman_vote_results` (1935-present) | **Full ballot history for archetype comps** ("the last QB to win after a Week-10 4-INT game was…") |
| `player_game_stats` last 4 games | PPA, attempts, yards, TDs for top-5 candidates |
| `player_season_context` | Usage rate, value score, recruiting ranking |
| `player_honors` | All-American selections + prior preseason honors |
| `conversation_documents` + `source_observations` (filtered to candidate name) | Reddit/podcast volume + sentiment Δ7d per candidate |
| `power_ratings_weekly` | Candidate's team SOS + remaining schedule difficulty |
| `archive_threads` | Historical Heisman-race threads from prior years' Week-N |

**Unique edge:** "Beck is in the position Bo Jackson was in Week 9 1985 by ballot-share rank, but the buzz volume is closer to 2018 Tua than 2017 Mayfield." Nothing else can write this.

#### Storyline thread chapter (6-8/wk, Pattern E)

| Table | Pull |
|---|---|
| `storyline_chapters` last 3 | Continuity context (HISTORY block + entity ledger) |
| Program voice excerpt (existing) | Voice register for primary program |
| `wire_entries` last 14d for primary_program_slugs | New facts this chapter is processing |
| `conversation_documents` tagged to thread slug | Verbatim quote sources for ≥3 cited sources requirement |
| `source_observations` | Boards, podcasts (named hosts), beat-writer names with `published_at` |
| `storyline_chapters.referenced_sources_json` | Prior chapters' citations (avoid double-quoting same writer) |
| `archive_threads` | Historical board threads on same topic from prior seasons |

**Unique edge:** Citing real beat writers actually publishing this week with real timestamps. The ≥3 named-sources constraint is *not bluffable* without `conversation_documents`.

#### Mailbag answer (10/wk, Pattern C)

| Table | Pull |
|---|---|
| Existing bundle | wire_excerpts, receipt_excerpts, pulse_excerpts |
| `conversation_documents` filtered to question's `topic_tags_json` | Verbatim board/podcast quotes |
| `fanbase_classification_history` for programs in question | "What kind of fanbase is asking this" context |
| `archive_threads` matching topic tag from prior seasons | Historical comp ("this came up before, here's how it resolved") |
| `editions` + `edition_features` `feature_kind='mailbag_answer'` | Past answers on adjacent topics — non-repetition |
| `storyline_threads` matching tags | Point reader to the live arc |

#### Reaction story (5/wk, Pattern C)

| Table | Pull |
|---|---|
| `wire_entries` triggering row | + `historical_comp` + `impact_label` |
| `team_cohort_divergence_week` | Three-cohort sentiment split + verbatim quotes (existing `CohortDivergence`) |
| `archive_threads` | Prior board reactions to similar moves by this program ("the last time Alabama landed a 5⭐ portal QB the board went here…") |
| `fanbase_mood_weekly` 7d Δ | Affected program + opponent (for transfer-from comp) |
| `recruiting_rankings` | Where the player ranked coming out of HS / portal class |
| `player_season_context` | Previous-season usage at prior school |
| `player_honors` | Any All-Conf/All-America honors carried in |

#### Chronicle card (595/wk profiled, Pattern E)

| Table | Pull |
|---|---|
| Existing `CandidateObservation` evidence blob | savant, fanintel, archive, rivalry, retroactive, player_arc streams |
| `team_chronicle_observations` last 12 weeks for this program | Headlines only — prevents re-covering same beat |
| `fanbase_classification_history` | "What kind of fanbase is this becoming" arc for `fanintel_stream` |
| `power_ratings_weekly` 6-year sparkline | Comparative markers ("hasn't been ranked this high since 2019") |
| `game_player_stats` 6-year peer-archetype lookup | For `player_arc_stream`: "this player's PPA progression matches 2021 archetype: [name]" |

**Unique edge:** "Since" / "first time since" / "hasn't been Y since X" becomes hard-grounded comparative, not LLM date invention.

#### Team narrative — `generate_state_of_team` (~70/yr, Pattern C)

| Table | Pull |
|---|---|
| `signature_metrics_ladder` from `team_profile` | **Current values** (not just metric names) |
| `fanbase_mood_weekly` last 12 weeks | Mood arc, not current point |
| `nfl_pipeline` | Alumni in NFL this season |
| `recruiting_rankings` | Class score trajectory last 5 years |
| `editions` + `edition_features` last 6 mentions of this program | Non-repetition + continuity |
| `team_chronicle_observations` top-5 last 90d | 1-2 specific moments to anchor |

#### Pulse state-of-team / lede (15/wk, Pattern C)

| Table | Pull |
|---|---|
| Existing themes[:3] | Label + summary |
| `fanbase_cohort_weekly` | Dominant cohort *transition* this week ("Smug → Tortured 0.6") |
| `fanbase_mood_weekly` | 4w trend + 1y same-week comp |
| `team_cohort_divergence_week` | Three-cohort sentiment split |
| `lexicon_weekly` | Phrases that spiked this week on this program's boards (**vocabulary fingerprint**) |
| `wire_entries` last 7d | Filtered to entity |
| `rivalry_obsession_weekly` | If rival mentions are spiking |
| `power_ratings_weekly` 7d Δ | |

**Unique edge:** Lexicon spikes name what fans are *actually* saying this week, by phrase. No competitor has weekly-spiking-phrase signals per fanbase.

#### Wire "why it matters" sidebar (~20/wk LLM-path, Pattern C 1-pass)

| Table | Pull |
|---|---|
| Wire row | action, actor_kind, program_slug, occurred_at |
| `wire_entries` matching `(actor_kind, action_type)` over prior 5 years | Historical comp ("4th May portal QB; last 3 went 2-1") |
| `recruiting_rankings` | For the player |
| `nfl_pipeline` | Does this program produce this archetype at the next level? |
| `team_brand` | Accent color / mantra — voice on-brand |
| `fanbase_mood_weekly` Δ7d | "Hungry room or quiet one?" |
| `prediction_market_snapshots` | Market reaction to similar prior moves |

#### Canon entry top-10 (30 entries, Pattern D)

| Table | Pull |
|---|---|
| `canon_entries` prior-year row | Full body — continuity |
| `cohorts.compute_cohort_split` | Stat-folks rank vs casuals rank divergence |
| `power_ratings_weekly` | Final-season BT/SP+/FPI rank |
| `nfl_pipeline` | Players drafted from entry's season |
| `team_chronicle_observations` | Top 3 moments tagged to entry's season+team |
| `archive_threads` | Top-upvoted historical thread referencing entry |
| `editions` mentioning entry previously | Continuity |

**Unique edge:** "Stats people put this at #4, the boards have it at #11 — that gap is the entire post-CFP era." Unfakeable.

#### Player season narrative (Accolade Lens, ~50/wk, Pattern C)

| Table | Pull |
|---|---|
| `game_player_stats` (6-year) | Full season + game-by-game arc |
| `player_season_context` | usage_rate, value_score, snap_share, recruiting rank |
| `player_usage_season` | How usage compares to peers |
| `player_value_metrics` | PPA percentile vs position cohort |
| `player_honors` | All selections + ballot history |
| `heisman_rankings_weekly` | If applicable |
| **Archetype peers** `game_player_stats` filtered to prior seasons where players within ±5% PPA at same week share | "This season's arc tracks 2019 [name]" — proprietary archetype-comp engine |
| `nfl_pipeline` | For prior players from same program at same position |
| `conversation_documents` filtered to player name | Conversation volume Δ7d, dominant quote pill |
| `team_brand_assets` | Page colors |
| `team_chronicle_observations` referencing player | Recent tie-ins |

**Unique edge:** "Beck's PPA-by-week curve is the closest 2026 match to Hurts-2017, not Burrow-2019 like the consensus thinks." Generic LLM can list stats; only this DB can claim archetype peerage.

### Implementation cost — context-builder utility module

A new module `src/cfb_rankings/prompt_context/builders.py` (Sprint v5-1):

```python
def build_edition_cover_context(season: int, week: int, db: sqlite3.Connection) -> dict:
    """Pull all proprietary data for edition cover essay prompt."""
    return {
        "prior_4_covers": _q_prior_covers(db, season, week, limit=4),
        "cohort_mood_dumbbell": _q_dumbbell(db, season, week),
        "rank_disagreements": _q_rank_disagreements(db, week),
        "active_storylines": _q_active_storylines(db),
        "major_wire": _q_wire(db, days=7, impact="MAJOR"),
        "resolved_receipts": _q_resolved_receipts(db, week, min_surprise=80),
        "top_chronicle_moments": _q_top_chronicle(db, days=14, limit=10),
        "season_phase": _q_season_phase(db, season, week),
    }

# ... similar builders for the other 11 priority surfaces
```

Each builder ~50-80 lines of SQL + dict shaping. Total module ~700 lines, lands Sprint v5-1 as part of the prompt-context overhaul.

---

## Part 5 · Revised Sprint Roadmap (supersedes v5.2 Part 3)

No new weeks added. The quality_loop module + per-surface model upgrades fit within Sprints v5-1 through v5-6. Pattern roll-out is feature-flag-driven; each sprint flips one or two flags.

| Week | Sprint | v5.2 deliverable | **v5.3 additions** |
|---|---|---|---|
| **0** | v5-0 Procurement | API keys, repo-public, prompt templates, profile schemas, fallback editions, **25 trophy SVGs (Pattern D 2-pass critique applied during generation)** | (unchanged) |
| **1** | v5-1 Foundation | 15 migrations, `llm_runtime.py` prompt caching, `BASE_URL` pattern, backfill→enrich rewire | **+ `quality_loop.py` module (5 patterns + 5 critic prompt templates + circuit breakers + telemetry)** **+ `prompt_context/builders.py` module (12 priority surfaces)** **+ model-version bump PR (10 call sites: pulse_lede, pulse_themes, best_calls, source_profiles, chronicle_generator, chronicle_game_edition, narrative_generator, reactions, mailbag)** **+ flags dict empty (no behavior change yet)** |
| **2** | v5-2 Editorial gen | Edition cover essay generation, factual restatement → Haiku swap, publish-edition into site-deploy | **Edition cover essay uses Pattern C (not D yet) — flag-enabled.** **Wire factual → Sonnet 4.6 (NOT Haiku as v5.2 said)** **Headline-quality judge + Headline Doctor land alongside Edition flow** |
| **3** | v5-3 Reactions + storylines | reactions-check-triggers --auto, auto-promote-storyline-drafts | **Daily lead → Pattern C flag-enabled. Heisman weekly → Pattern C. Mailbag → Pattern C. Reactions standard → Pattern C.** All upgraded from Sonnet to Opus 4.7. |
| **4** | v5-4 Mailbag + Chronicle | mailbag-mine-questions, Chronicle approval_state filter | **Storyline thread chapters → Pattern E flag-enabled (continuity-grounded).** **Chronicle profiled programs (top 2 cards/team) → Pattern E flag-enabled.** |
| **5** | v5-5 Heisman + Canon | generate-heisman-narrative, Canon nightly regeneration | **Canon top-10 → Pattern C (lock in Opus 4.7 + 16K thinking). Canon 11-100 → Pattern C with 4K thinking. Pulse themes Stage 2 → Pattern C. Receipts Best Calls (both tiers) → Pattern C.** |
| **6** | v5-6a R2 + Pillow OG | R2 verification, share_cards/, OG meta wiring | **Pattern D for Edition cover (replaces Pattern C wired in v5-2). Engagement critic enabled.** Compare against v5-2 Pattern C baseline for 4 weeks before declaring win. |
| **7** | v5-6b Visual assets | visual_assets.asset_for(), typographic helmet stripes | (unchanged) |
| **8-9** | v5-7 + v5-8 | Imagery + Zero-Touch UI | **Team narratives + Pulse state-of-team + Historical season → Pattern B/C as each surface's renderer ships.** |
| **10-14** | v5-9 through v5-10d | Programs, sources, players, rivalries, conferences, Reddit archive | **Player season narratives → Pattern C (using archetype-peer engine).** **Chronicle for unprofiled programs → Pattern B (high volume, Sonnet-default).** |
| **15-17** | v5-11 + v5-12 | Polish + Launch | **Critic prompt regression suite: stored baselines per surface; CI checks no surface's avg critic score drops below 7.0 across rolling 4 weeks.** |

### Feature-flag rollout per surface (sequenced for safety)

```python
# config.py — flags get flipped one at a time across sprints
QUALITY_LOOP_FLAGS = {
    # Sprint v5-2:
    "tier1.edition_cover":         LoopPattern.C_CRITIC_REVISE,
    "tier3.wire":                  LoopPattern.A_SINGLE_SHOT,  # but model upgraded to Sonnet
    "tier3.headline_judge":        LoopPattern.A_SINGLE_SHOT,
    "tier1.headline_doctor":       LoopPattern.A_SINGLE_SHOT,

    # Sprint v5-3:
    "tier1.daily_lead":            LoopPattern.C_CRITIC_REVISE,
    "tier1.daily_supporting":      LoopPattern.C_CRITIC_REVISE,
    "tier1.heisman_weekly":        LoopPattern.C_CRITIC_REVISE,
    "tier1.mailbag":               LoopPattern.C_CRITIC_REVISE,
    "tier1.reaction_story":        LoopPattern.C_CRITIC_REVISE,

    # Sprint v5-4:
    "tier1.storyline_chapter":     LoopPattern.E_CONTINUITY,
    "tier1.chronicle_profiled":    LoopPattern.E_CONTINUITY,

    # Sprint v5-5:
    "tier1.canon_top10":           LoopPattern.C_CRITIC_REVISE,
    "tier1.canon_tail":            LoopPattern.C_CRITIC_REVISE,
    "tier1.pulse_themes_writer":   LoopPattern.C_CRITIC_REVISE,
    "tier1.best_calls":            LoopPattern.C_CRITIC_REVISE,
    "tier1.pulse_lede":            LoopPattern.C_CRITIC_REVISE,

    # Sprint v5-6a:
    "tier1.edition_cover":         LoopPattern.D_ADVERSARIAL,  # upgraded from C

    # Sprint v5-8:
    "tier1.team_narrative":        LoopPattern.C_CRITIC_REVISE,
    "tier1.pulse_state_of_team":   LoopPattern.C_CRITIC_REVISE,
    "tier1.historical_season":     LoopPattern.C_CRITIC_REVISE,

    # Sprint v5-10a:
    "tier1.player_narrative":      LoopPattern.C_CRITIC_REVISE,

    # Sprint v5-9 / v5-10:
    "tier2.chronicle_unprofiled":  LoopPattern.B_SINGLE_CRITIC,
    "tier2.historical_moments":    LoopPattern.A_SINGLE_SHOT,
    "tier2.game_diagnosis":        LoopPattern.A_SINGLE_SHOT,
}
```

---

## Part 6 · Revised Sprint v5-1 Day-1 Brief (supersedes v5.2 Part 10)

The very first commits after Sprint v5-0 closes. **Half a day for patches; the rest of the week for `quality_loop.py` + `prompt_context/builders.py` + model-version bumps.**

### Day 1 Morning — Four patches (already-listed three + one new)

1. **`llm_runtime.py` prompt caching** (90 min, v5.2)
2. **`backfill_full_history.yml` route fix** (5 min, v5.2)
3. **`publish_site.yml` failure propagation** (30 min, v5.2)
4. **🆕 Model-version bump PR** (45 min) — single PR touching:
   - `pulse_lede.py:27-28`: 4-5 → 4-7
   - `pulse_themes.py:27`: 4-5 → 4-7 (also tier-upgrade Sonnet → Opus)
   - `receipts/best_calls.py:181-183`: 4-5 → 4-7 (both)
   - `receipts/source_profiles.py:198`: 4-5 → 4-6
   - `team_pages/chronicle_generator.py:223-224`: extend Opus to all profiled top-2
   - `team_pages/chronicle_game_edition.py:88-90`: drop blue-blood-only restriction
   - `team_pages/narrative_generator.py:107`: Sonnet → Opus 4.7
   - `reactions/synthesizer.py`: Sonnet → Opus 4.7 for standard reactions
   - `mailbag/synthesizer.py`: Sonnet → Opus 4.7 for standard answers

Net behavior change: production gets immediate quality lift from model version bumps even before quality_loop lands. No flag, no toggle — just better defaults.

### Day 1 Afternoon — Trigger world_class_enrich

After patches merge, manually trigger `world_class_enrich.yml` (same dispatch as you'll do today before reading further). Now produces post-backfill output that includes the model-version uplift on Chronicle/Narratives/Reactions/Mailbag. First clear win to see in production.

### Week 1 Days 2-3 — `quality_loop.py` module

- Copy/refine the 5 loop functions from Investigator C's spec (Pattern A through E)
- Copy/refine the 5 critic prompt templates verbatim from the Investigator C spec
- Wire to `llm_usage_log.append_llm_usage()` with new fields
- Wire to existing `voice_validator.validate_fan_voice()` (regex gate stays as floor)
- Add unit tests: `test_quality_loop.py` with mocked SDK responses for each pattern

Verification: pytest suite passes; no behavior change in production yet (flags dict empty).

### Week 1 Days 3-4 — `prompt_context/builders.py` module

- 12 priority-surface builders per Part 4 manifests
- Each builder ~50-80 lines of SQL + dict shaping
- Add unit tests against test fixtures (small SQLite snapshot with known data)
- Verify each builder against current schema (some tables may not yet have data — that's fine; manifests target post-backfill state which is now live)

### Week 1 Day 5 — Migration files (per v5.1 Review Correction #8)

15 migrations land. Specific to v5.3:
- `migrations/20260520_15_llm_usage_log.sql` — schema for the extended JSONL audit columns (loop_pattern, critic_role, critic_score, revise_count, fell_back, fallback_reason). Optional if telemetry stays JSONL-only; useful for SQL aggregation in admin dashboard.
- `migrations/20260520_16_circuit_state.sql` — `circuit_state` table for per-surface failure tracking + weekly spend counters (per `quality_loop.py` Rung 3).

### Sprint v5-1 close criteria

- `quality_loop.py` exists, tested, but `QUALITY_LOOP_FLAGS = {}` so no production behavior change
- `prompt_context/builders.py` exists, all 12 builders implemented
- Model version bumps in production
- `BASE_URL` env-var pattern landed (from v5.2)
- `backfill→world_class_enrich` rewire landed (from v5.2)
- Sanity gate freshness check landed (from v5.2)
- All 15 migrations applied in CI

Sprint v5-2 can start flipping flags on Day 1 of its week.

---

## Part 7 · Open Items After v5.3

### Decisions locked in v5.3

1. **Every visible surface uses Opus 4.7 + extended thinking + critique loop.** No "low-quality" surface exists. Tier-3 Haiku surfaces are narrow factual/judge tasks only.
2. **Wire factual restatement is Sonnet 4.6, not Haiku.** v5.2's Haiku call was cost-driven; v5.3 overrules on quality grounds.
3. **Storyline thread chapters use Pattern E (continuity-grounded).** Biggest single quality lift in the matrix (from Sonnet single-shot to Opus + thread history + continuity critic).
4. **Chronicle profiled programs use Pattern E for top 2 cards/team.** Same continuity reasoning; ranks 3-5 stay Pattern B (Sonnet).
5. **Edition cover essay uses Pattern D (adversarial).** 5× single-shot cost, 1/wk volume = ~$31/yr at API rates. Top-of-homepage signature surface earns the budget.
6. **Proprietary data manifests are mandatory.** A surface running through Pattern C without its data manifest is no better than generic Opus; with the manifest it's unfakeable.
7. **Migration is feature-flag-driven**, one surface per sprint, with `editions/seeds.py` (924 lines) as the safety net all the way down.

### Open items requiring user judgment (not blockers)

1. **Pattern D scope creep.** Currently only Edition cover. Candidates for promotion to Pattern D if quality bar lifts further: Canon top-10, Daily lead on tentpole dates. Recommend: ship D on Edition cover first, evaluate after 4-week A/B (Sprint v5-6a).
2. **Engagement critic threshold.** Default `pass_threshold_b=7.5`. May tune up to 8.0 if early outputs feel too easy on the critic. Tune via `config.py` constant, no code change.
3. **Continuity critic scope.** Currently fires on Storylines + Chronicle profiled. Could extend to Editions (continuity across weekly covers). Recommend: defer to v5.4 evaluation; covers naturally pull prior-cover context already.
4. **Headline doctor cadence.** Could run as gate (block emit until §2.9 passes) OR background-rewrite (emit + offer alternates in admin queue). Recommend: gate for Tier-1 surfaces, background for Tier-2.
5. **Voice-validator advisory layer (Haiku over regex).** Default-on adds ~$50/yr but catches the "passes regex but reads as AI" failure mode. Recommend: enable from Sprint v5-2.

### What v5.3 does NOT change from v5.2

- $0 incremental cash cost (Agent SDK credit covers everything)
- No custom domain
- No commissioned art
- 17-week roadmap
- Repo public posture
- GitHub Issue digest + reject-reaction workflow
- BASE_URL env-var pattern
- Backfill→enrich auto-trigger fix
- Workflow failure propagation fix

### Updated canonical reading order

| Doc | Read for |
|---|---|
| v1–v3 | Problem inventory, architecture, visual identity |
| **v4** | Build spec (13 atoms, voice stylebook, mobile, motion, share cards, governance) |
| v5 | Bespokeness + automation (per-program, per-player, per-rivalry, per-conference, per-phase) |
| v5.1 Review | Verification corrections to v5 (file paths, schema, sprint scope) |
| **v5.2** | **Architectural reset** — $0 cost via Agent SDK credit, no domain, no commissions, workflow chaining fixes |
| **v5.3 (this doc)** | **Quality maximization** — 37-surface matrix, `quality_loop.py` architecture, proprietary data manifests |

**Single-source-of-truth updates from v5.2:**

| Dimension | Canonical |
|---|---|
| LLM model routing | **v5.3 Part 1 (37-surface matrix)** |
| LLM cost projection | **v5.3 Part 2 (~$1,200-1,400/yr post-caching, inside $2,400/yr credit)** |
| Critique loop architecture | **v5.3 Part 3 (`quality_loop.py` module spec)** |
| Prompt context construction | **v5.3 Part 4 (per-surface proprietary data manifests)** |
| Sprint roadmap | **v5.3 Part 5 (flag-driven enablement schedule)** |
| Sprint v5-1 Day-1 brief | **v5.3 Part 6** |

All other v5.2 canonical claims (no domain, no commissions, 17-week timeline, workflow chaining, repo public) carry forward unchanged.

---

## Closing summary

**v5.3 routes every visible LLM writing surface through Opus 4.7 + extended thinking + critique loops, grounded in proprietary 6-year-deep data manifests, at $0 incremental cost.**

Three forces make this possible:

1. **Max 20x Agent SDK credit** ($2,400/yr) absorbs the ~$1,200-1,400/yr API-equivalent workload with ~50% headroom.
2. **The `quality_loop.py` architecture** (5 patterns + 5 critic roles + 3-rung circuit breakers) wraps existing `generate_with_voice_check` without breaking contracts.
3. **The proprietary data manifests** make every surface's prompt unfakeable — generic Opus output is no better than generic Sonnet; with 6 years of mood/cohort/stat/archive context the output is something no LLM-with-web-search can match.

**Three things that distinguish v5.3 from "use Opus everywhere":**

1. **It's a 37-surface audit, not 12.** Surfaces I missed in v5.2 (Pulse themes Stage 1/2, sentiment classifier, Receipts Stage 1, source_voice, historical_season, game-edition Chronicle, game-recap diagnosis labels) are all explicitly routed.
2. **It's pattern-aware.** Storylines + Chronicle profiled use Pattern E (continuity), Edition cover uses Pattern D (adversarial), Tier-2 narratives use Pattern B (single critic). The right model and the right loop together.
3. **It's data-aware.** Every Tier-1 surface has a specific proprietary data manifest. The 5 cross-cutting rules (prior-N continuity, 6-year same-week comp, cohort transitions, verbatim quotes, signature metrics ladder) apply to all of them.

**Immediate action (unchanged from v5.2):** Trigger `world_class_enrich.yml` from GitHub Actions tab. Then Sprint v5-0.

**First v5.3-specific action:** When Sprint v5-1 starts, the Day-1 model-version-bump PR (10 call sites, 45 minutes) lands immediate quality uplift before quality_loop ships. That's the cheapest visible quality win in the entire plan.
