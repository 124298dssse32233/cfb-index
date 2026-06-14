# 73 — The Belief Visual Family (Chronicle Visuals, net-new)

_Status: DESIGN SPEC v1, 2026-06-13. **Not yet implemented.** Slots into the existing `src/cfb_rankings/chronicle/visuals/` engine as three new registered visuals — no engine changes, no migration (`chronicle_visual_cache` already exists). Companion to [CHRONICLE_QUALITY_PROPOSAL_v3.md](../../CHRONICLE_QUALITY_PROPOSAL_v3.md) §5/§6 and the narrative engine ([[51-team-narrative-engine]])._

---

## 0. Why this doc exists — the gap

The Chronicle Visuals engine is **built and wired** (pipeline → Visual Director rule-engine → SVG → 8-dim scorer → suppress<0.62 → anti-dup → cache → LKG → share PNG; rendered in `team_pages/renderer.py`). But the **9 registered visuals are all structural** — statement-win, returning-production, Heisman, roster-replacement, CFP-bubble, talent-yield, draft-conveyor, delta-DNA, continuity. **None chart belief.**

The v3 proposal already named the missing family — **"Fan Mood Braid"** (§5: *"are fans, market, and model aligned?"*) and **"Panic vs Proof Matrix"** (§5: *"is the fanbase right to panic?"*) — and §10 flags the binding: *"Fan-intel tables → Fan Mood Braid, Panic vs Proof Matrix — should be visualized against model/market, **not alone**."* They were scoped and skipped when the v1 wave shipped the structural set.

This doc specs that family. It is the **proprietary** half of the engine: every competitor can compile roster/recruiting/draft charts from CFBD; **only CFB Index has audience-tagged fan belief** (`backometer_weekly`, fan-vs-national `team_week_conversation_features`). This family is the moat made visible.

> Naming: the brainstorm (2026-06-13) coined **Phantom Delta** for the belief↔reality gap. This doc treats "Delusion Gap" / "Fan Mood Braid" / "Phantom Delta" as the same lineage and ships them as the three visuals below.

---

## 1. The live data substrate (verified populated)

**Belief side (proprietary, season_year=2025 = current offseason per [[pipeline-week-keys]]):**
- `backometer_weekly` — `score` (0–100), `zone`, `delta_wow` (100% populated), `sample_size`, `is_low_signal`, `is_offseason`, `components_json`, `annotations_json`. 294 rows / 102 teams.
- `team_week_conversation_features` — `audience_bucket ∈ {fan, national}`, `net_sentiment_score`, `mention_count`, `unique_author_count`, and the **emotion shares** `joy_/anger_/fear_/trust_/sadness_/surprise_share`, `attention_score`, `sample_quality_score`. 318 rows.
- `team_conversation_daily` — same shape at daily grain. 4,800 rows.

**Reality side (the "tape," 2020–2025, deep):**
- `power_ratings_weekly` (76k) — the **model** axis.
- `resume_ratings_weekly` (67k) — the **committee/résumé** axis.
- `official_rankings` (5,451) — the **poll/national-perception** axis.

**Not available:** no betting-odds table. The "reality" axis is **model/résumé/poll**, labeled as such. Never phrase belief-vs-reality as a market/$ claim (consistent with [[nil-valuation-not-a-hero-number]]).

---

## 2. The three visuals

Each is a standard engine visual: a `query_fn(db, *, slug, season_year, week_number=None) -> dict` (contract: `query_id, source_tables, rows, summary_stats, sample_n, confidence, limitations, as_of_utc`) and a `render_fn(query_result, spec_meta=None) -> {svg_html, headline_finding, annotations[], alt_text}`. Reuse `svg_helpers` + Noir tokens. All values originate in the query, never in prose (v3 §7).

### 2.1 `FAN_MOOD_BRAID` — "Does belief match the tape?" (the flagship / Phantom Delta)

- **Fan question:** Are the fans higher or lower on this team than the model is?
- **Chart family:** `ANNOTATED_LINE` (two series + shaded divergence wedge). Tier-0 family, already legible.
- **Encodings:** X = `week` (season arc). Y = normalized 0–100. Series A = **Belief** (`backometer_weekly.score`). Series B = **Reality** (`power_ratings_weekly` → team percentile that week; fallback `resume_ratings_weekly`). Shade the wedge between them:
  - Belief > Reality → **violet** ✦ ("**The Delusion Zone**" — fans believe more than the tape earns).
  - Reality > Belief → **blue** ("**The Paranoia Zone**" — fans are sleeping on a real riser).
- **The single number (Phantom Delta):** `phantom_delta = belief_pctile − reality_pctile` at the latest week. Signed. This is the headline metric.
- **Annotation / receipt anchor:** drop a marker at the week where the wedge **most violently closes or opens** (max |Δ phantom_delta| week-over-week) — cite the `backometer.delta_wow` and the rating move that quarter. Receipt: `n=<sample_size>`, source = `backometer_weekly + power_ratings_weekly`, confidence from §3.
- **Headline grammar (LLM phrases, values injected):** `"<Team> fans are priced <N> points above the model — the widest gap since Week <k>."` / inverse for paranoia.
- **Posture:** RETROSPECTIVE in-season (full arc); in offseason, single-snapshot variant (see §2.4 Phantom-Delta-offseason).

### 2.2 `HOME_AWAY_MIND` — "Your fanbase vs the room" (the fan-vs-national split)

- **Fan question:** Does your own fanbase feel differently about you than the national conversation does?
- **Chart family:** `SLOPEGRAPH` (two checkpoints) or `ANNOTATED_LINE` if ≥4 weeks. The cleanest use of the audience-tagged moat.
- **Encodings:** two anchored points/lines — `net_sentiment_score` for `audience_bucket='fan'` vs `audience_bucket='national'`, over the available weeks. The **gap** is the story.
- **The number:** `belonging_gap = fan_net_sentiment − national_net_sentiment`. Large positive = "the world doubts us, we don't" (Grievance fuel — ties [[56-team-fan-ledger-detectors]] Grievance ledger). Large negative = "even we've turned" (a real internal-fracture signal).
- **Receipt anchor:** the week of widest divergence; cite both bucket `mention_count`/`unique_author_count` so a thin national sample can't fake a gap.
- **Honesty gate:** require **both** buckets ≥ MIN floor (see §3); national bucket is frequently thin — suppress rather than narrate a one-author "national" read.
- **Posture:** RETROSPECTIVE/year-round.

### 2.3 `MOOD_SPECTRUM` — "What is the fanbase actually feeling?" (emotion decomposition)

- **Fan question:** Is this hope, fear, anger, or trust — and which is rising?
- **Chart family:** `RIDGELINE` or small-multiples stacked band of the six emotion shares (`joy/anger/fear/trust/sadness/surprise`) over weeks; highlight the dominant + fastest-rising emotion. Genuinely novel — no competitor exposes emotion shares.
- **Encodings:** X = week, bands = emotion shares (normalized to 1.0), color = semantic emotion ramp (NOT team color). Label only the **dominant** band + the band with the steepest positive slope ("**rising: fear**").
- **The number:** `dominant_emotion` + `mood_velocity` (Δ share of the fastest-moving emotion). Pairs with `backometer.zone` for a cross-check ("zone COOKING but fear rising = a fragile high").
- **Receipt anchor:** the week emotion flipped (e.g. trust→fear crossover); cite `attention_score` so a low-attention week isn't over-read.
- **Posture:** RETROSPECTIVE/year-round.

### 2.4 Offseason variant — Phantom-Delta-as-stillness (where we are now, June)

In the offseason there is no week-to-week tape. The honest offseason reading (brainstorm coinage): **the belief swing that *should* have happened and didn't.** `FAN_MOOD_BRAID` in offseason posture renders a **single dumbbell**: belief vs model percentile *as of the offseason snapshot*, annotated with "belief hasn't moved despite <portal/recruiting event>" when `delta_wow ≈ 0` against a structural event. This is the Director's-Playbook "The Long Wait" act ([[69-living-team-page-directors-playbook]]) made visual. Guardrail: **no manufactured saga** — if belief is genuinely flat and nothing moved, the headline says so ("Belief is parked — the model and the fans agree, for once").

---

## 3. Honesty & suppression (belief-specific gates)

Belief is the easiest signal to lie with, so these gates are stricter than the structural visuals:

- **Signal floor:** skip (return `sample_n=0` → engine retires the card) when `backometer_weekly.is_low_signal=1` OR `sample_size < 200` (the backometer's own MIN_SAMPLE). For `HOME_AWAY_MIND`, require both buckets ≥ MIN_DOCS.
- **Confidence band** (drives the scorer + the on-card meter): `high` if `sample_quality_score ≥ 0.8` AND `sample_size ≥ 300`; `medium` if `≥ 0.6 / ≥ 200`; else `low`. Surface `n=` + confidence on every card (v3 §12 data gates).
- **Reality-axis labeling:** the non-belief series is always labeled **model** or **committee résumé** or **poll** — never "reality" unqualified, never "market."
- **No mind-reading below Rung 2** ([[57-team-dependency-degradation-matrix]]): thin data → render the dumbbell/number with deterministic copy, strip the "fans believe…" attribution.
- **`delusion_premium_weekly` (10 rows)** is contender-only; do NOT gate the family on it — these visuals must generate for all 102 belief-covered teams, not just title contenders. (That table is the old narrow belief-vs-reality; this family generalizes it.)

---

## 4. Integration (exact, additive — no engine edits beyond registration)

1. **`models.py`** — add to `VisualId`: `FAN_MOOD_BRAID`, `HOME_AWAY_MIND`, `MOOD_SPECTRUM`. (Chart families `ANNOTATED_LINE`, `SLOPEGRAPH`, `RIDGELINE` already enumerated.)
2. **`queries.py`** — add `query_fan_mood_braid`, `query_home_away_mind`, `query_mood_spectrum` following the `query_continuity_stress_test` shape (helpers `_team_id_for_slug`, `_query_one`, `_empty_result` already exist).
3. **`families/`** — add `mood.py` with `render_fan_mood_braid`, `render_home_away_mind`, `render_mood_spectrum` (reuse `svg_helpers`; `ANNOTATED_LINE` + dumbbell geometry mirror `signals.render_delta_dna`).
4. **`registry.py`** — add the three `_REGISTRY` entries + `VISUAL_POSTURE` (RETROSPECTIVE; offseason snapshot handled in-query) + `VISUAL_DISPLAY_ORDER` (place the braid first — it's the lead belief visual).
5. **`scorer.py`** — add the three ids to the `high_impact` set in `score_fan_relevance` (they answer the realest fan argument). This is the only scorer change; it does **not** yet make selection narrative-conditioned (see §5).
6. **No migration** — `chronicle_visual_cache` already stores any `visual_id`. Run `generate_visuals_for_team` for a spike team (e.g. `alabama`) to validate, then `generate_all_visuals` in the nightly build.

**Build order:** `FAN_MOOD_BRAID` first (flagship, single-team validate), then `MOOD_SPECTRUM` (novel, same data), then `HOME_AWAY_MIND` (needs the both-buckets floor tuned).

---

## 5. The seam to narrative-conditioning (deliberately deferred, not blocked)

This family is buildable and shippable **today** under the existing availability-election (a belief visual ships if data passes the floor and it scores ≥0.62). It does **not** require the unbuilt LLM Visual Director.

But it is designed to become the *lead* visual once narrative-election lands ([[51-team-narrative-engine]] §3). The hook: when `ProgramNarrativeState` exists, `score_fan_relevance` (or a successor election function) keys the belief family's boost off the **current narrative**:
- `lead.character == 'fanbase'` OR `|backometer.delta_wow|` large → promote `FAN_MOOD_BRAID` to the lead slot (it *proves* the belief story).
- Director's-Playbook act = "Hope-Doping" / "Permission Slip" → promote `HOME_AWAY_MIND` (the disrespect/permission read).
- `MOOD_SPECTRUM` rises when a single emotion (fear/anger) spikes — the "is the fanbase right to panic?" moment.

Until then, the family ships on quality+availability and quietly waits for the director. Same function, richer input — no rework.

---

## 6. Acceptance

- Three visuals registered; `generate_visuals_for_team('alabama', 2025)` emits all three with `suppressed=False`, score ≥0.62, valid receipts, alt text, 360px-legible SVG.
- `FAN_MOOD_BRAID` shows a signed Phantom Delta and a wedge; `HOME_AWAY_MIND` suppresses cleanly when the national bucket is thin; `MOOD_SPECTRUM` labels the dominant + rising emotion.
- Fleet run (`generate_all_visuals`) produces belief cards for the ~102 belief-covered teams, suppressing low-signal programs honestly (the Awaiting-Signal path, not a fabricated chart).
- Reviewed against §3 honesty gates before flipping live on team pages.
