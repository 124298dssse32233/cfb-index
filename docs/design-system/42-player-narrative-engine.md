# 42 — Player Narrative Engine ("The Bible")

_Status: ARCHITECTURE SPEC (v2, critique-hardened). Created 2026-06-11; revised after Codex + Gemini adversarial review and the owner's editorial directive. The content brain behind the Player Story Card ([[41-player-story-card]]). Extends the Chronicle pipeline (CLAUDE.md "Chronicle LLM pipeline") with a structured-first Narrative Event Layer + persistent per-player state. Not yet implemented._

> **The CFB-specific domain layer this engine consumes — the fan ledgers, the two axes, the succession engine, the tribal lens, the offseason mode, and the temporal heartbeat — lives in [[43-cfb-native-content-model]].** This doc is the generation *machinery*; 43 is *what to say*.

---

## 0. The core problem — and the Nico proof

Structured stats answer **WHAT** happened. The narratives fans care about answer **WHY / HOW / what it meant** — and those live in fan discourse and the wider record, not in stat tables. A card that only recites WEPA percentiles has failed.

**Empirical finding (queried 2026-06-11, real DB):** Nico Iamaleava's (pid 5944) controversial 2025 exit from Tennessee — an NIL standoff that ended with a transfer home to UCLA — is the biggest story about him. In the data:

- `transfer_entries` has the **what** (Tennessee→UCLA, 2025-04-20), nothing about **why**.
- The corpus has the **why**: **8 of 27** tagged Nico docs touch the NIL/Tennessee split; **58** corpus-wide pair him with NIL/holdout; corpus spans **2014→2026**. The shape is unmistakable (Locked On Tennessee saturates Feb–Mar 2025, hard break at the April transfer, then aftermath).
- Yet the current `player_week_conversation_features` "top quote" for Nico is **Land Grant Trophy trivia** — the pipeline scores sentiment but does **no event/topic extraction.**

The drama is *recoverable but not extracted.* The engine's job: **structured-first event detection → discourse enrichment → multi-axis salience → independent completeness check**, in an explicit observer voice.

---

## 1. Editorial stance — THE organizing principle

**The site compiles the conversation; it does not adjudicate it.** "The narrative is the narrative — we don't get to choose it."

- The engine **never asserts the validity** of a discourse claim, and **never invents the site's own opinion** — but it states the dominant fan take with **conviction**, not a robotic hedge. **Decided 2026-06-11 (owner): a confident compiler voice** — _"Tennessee fans overwhelmingly call it a betrayal,"_ attributed to the fanbase, paired with a **confidence meter** and the dissent shown as a **labeled minority**. The confidence meter is the honesty mechanism: high → a clear story; low → "the room is split"; below the floor → no narrative at all (stats-only). _(Rejected: the neutral-observer hedge "some say X, others say Y" — it reads as a robot AND is a hidden adjudication, since choosing what's "representative" is itself an editorial act.)_
- Truth is not the gate, because truth is not ours to rule on. **The gate is REPRESENTATIVENESS:** present something as "the story" only when it genuinely is — cross-source, sustained, above a noise floor. The thing we DO assert ("this is what people are saying") must itself be true; that is the accuracy obligation, and it is fully enforceable.
- Three voices, kept visibly distinct:
  - **Fact** (structured rows, trusted-outlet canon): stated plainly. "Transferred to UCLA in April 2025."
  - **Discourse** (corpus): stated as observed conversation. "Fans cast it as an NIL divorce."
  - **Inference** (LLM connective tissue): minimal, never introduces a new claim.
- A **standing, unmissable compiler label** (the AI-narrative footer + a "what people are saying" framing on discourse beats) makes the compiler stance explicit on every card — the conviction is the *fanbase's*, surfaced confidently; it is never the site's own opinion.

**Residual-risk knob (the only carve-out):** unverified *criminal / legal / medical* accusations about a named person, sourced **only** to anonymous social posts, carry republication exposure even when attributed. This is a single **policy setting** — `HIGH_RISK_DISCOURSE = {include_attributed | hold_for_trusted_source}` — owner-set, default owner's call. Everything else: attribute and ship. (Public-figure status + widely-reported matters like the NIL dispute are low-risk and unaffected.)

---

## 2. Three evidence planes

| Plane | Holds | Asserted as | Role |
|---|---|---|---|
| **Structured** | stats, transfers, recruiting, NIL, awards, aura, WEPA | fact | skeleton (what) |
| **Discourse** | conversation_documents/targets/features: volume, sentiment, keyness, quotes | observed conversation | drama + voice (why/how) |
| **Canon** | news + Wikipedia, each with source URL + trust tier | reported fact ("per [outlet]") | verified spine for events partly outside the dense corpus window |

**Source-trust tiering** (not truth-judging — credibility weighting for the *meta*-claim): trusted outlet > aggregator > named account > anonymous. **Independence dedup:** corroboration counts only across genuinely independent origins; N reposts of one thread = 1 source.

---

## 3. Narrative Event Layer (NEL) — structured-first

**v1 mistake (per critique): discourse-led detection erases every zero-spike event.** v2 inverts it.

### 3a. Structured event ontology (fires with ZERO discourse required)
Deterministic beats off data deltas — this is the net that catches the quiet-but-decisive:
- **Roster/status:** transfer/portal, depth-chart move, **role lost/won**, redshirt, **disappeared from roster** (absence-as-story), eligibility/class change.
- **Availability:** missing games vs expected (proxy for injury/suspension when not directly tracked) — flagged as *availability gap*, framed carefully (see §5).
- **Performance:** stat milestones, **collapses** (production fell off a cliff), usage trend up/down, **expectation gap** (ranked/hyped player who stopped producing).
- **Career frame:** recruiting events, awards, NIL jumps, draft.
- **Team→player propagation:** coaching change, coordinator/**scheme change**, a new QB/transfer arriving — team events that reframe THIS player's arc. (Cross-player causality, which v1 missed.)
- **Gradual arcs:** multi-season development, declining usage, leadership growth — detected by trend, not spike.

### 3b. Discourse enrichment (adds drama, voice, salience — never required for a beat to exist)
For each structured beat and for any standalone discourse pattern:
- volume vs the player's **shrinkage/empirical-Bayes baseline** (cold-start-safe — see §7);
- sentiment/valence; **keyness** topic label (existing log-odds engine at player grain, min-mention gated, same-name disambiguated);
- **representative** quote (salience-weighted, audience-balanced — not raw max-sentiment).

### 3c. Fusion
Align a structured event with its co-temporal discourse + canon → one beat with all three planes' evidence. Transfer row + April spike + trusted news = beat `transfer_controversy`, framing `attributed`, evidence = [row + 8 docs + 2 quotes + news url].

---

## 4. Salience — DECOMPOSED (never one collapsed score)

v1's single score misranked (recency buried legacy; volume = attention not importance; durability filter deleted real one-day events; quota forced fake drama). v2 scores **five orthogonal axes**, stored per beat so misses are auditable:

1. **career_impact** — does this define the player long-term? (event-type weighted; a season-ending injury scores high with zero volume)
2. **current_relevance** — recency/decay (applies to the *current* register only — see below)
3. **narrative_distinctiveness** — is it singular vs generic?
4. **discourse_intensity** — volume_z × |valence|, **after** bot/rivalry/astroturf discounting
5. **confidence** — evidence strength + source independence (the meta-claim's reliability)

**Two registers:** the bible keeps **permanent canon beats** (career-defining; never decayed) separate from a **current-arc layer** (decays). Recency only touches the current layer, so a legacy game is never buried.

**Importance ≠ volume.** Structural beats carry their own weight; volume is a *bonus*, not the basis. **Structural one-day events are never durability-filtered** (durability only drops *discourse-only* blips). **Astroturf/bot/rival discount:** source-trust weighting, author diversity, `audience_bucket` (rival down-weight), NIL-volume skepticism — reframed under §1 as *accuracy of the meta-claim*, not censorship.

**No quota.** Top-K is a ceiling, not a fill target. A quiet-excellence player gets a quiet, true card (or the factual strip) — the engine **never manufactures drama** to fill space. Beats below a quality floor are dropped, not inflated.

---

## 4b. Anti-formula — bespoke by COMPOSITION, not by template

Formula fatigue ("5 pages, same skeleton") is a STRUCTURE + VOICE problem, not a determinism problem. Determinism guarantees TRUTH; it must never dictate SHAPE or VOICE. With free local inference (3090, ~13s/card) the model can run rich. Three levers, biggest first:

1. **Compositional variety — the page SHAPE differs per player.** The card is assembled from a module palette; a **narrative archetype** (classified from the beats; the standard PCG approach for coherent-but-distinct output) sets which modules appear, their order, the lead, the chapter framing, and the tone. Archetype set (extensible): Phenom · Transfer Saga · Comeback · Quiet Workhorse · What-If (injury) · Position Battle · System Product · Late-Career Legacy · Bust-Watch · Breakout · Cornerstone · Journeyman. Nico = Transfer Saga (lead with the controversy + perception/production gap). A reliable center = Quiet Workhorse (lead with a rarity stat + reliability; NO drama module). Different skeletons, not different mad-libs.
2. **Salience-driven module presence** — modules appear/vanish/reorder by the 5 salience axes (§4); never a fixed skeleton. No discourse → no "what people are saying." Huge recruiting saga → it leads. The first thing the eye hits differs per player.
3. **Voice keyed to archetype + fanbase** — per-archetype tone (bust-watch wry, comeback earnest, phenom breathless-but-grounded), keyed to the emotional arc. **Fanbase-keyed vocabulary:** the writer borrows the words this fanbase actually uses for this player (existing keyness/language-layer engine) — deeply bespoke and grounded. Anti-repetition: cross-player phrase dedup + Chronicle banlist/antislop so no sentence pattern recurs.

**Corrected LLM role (vs §1 of the card spec's earlier "thin layer").** The "LLM = garnish" framing was a cost argument that does not apply to a free 3090. Reframe: **determinism owns TRUTH (facts, numbers, gates, coverage); the LLM owns EXPRESSION + COMPOSITION (voice, shape, angle).** Orthogonal axes — so the model runs rich and bespoke (best-of-3 multi-agent on stars, generous tokens) BECAUSE every fact it touches is deterministic and every claim is gated. Grounded, not garnished.

## 4c. Content craft — how the words are structured + when the card changes shape

The card is a **micro-feature** and obeys feature-writing craft (lede → nut graf → body → kicker), not stat-blurb convention.

- **Lede (hook).** Open on the single most telling, specific thing about THIS player — a detail, scene, or number that captures who he is. Never a formula opener; in a profile the who/why beats the what. Fanbase-keyed vocabulary + archetype tone live here.
- **Nut graf / "why now" — REQUIRED (missing in v1).** Every card answers *why tell this story today?* (the transfer just happened · he's on Heisman watch · the model just re-ranked him). It ties the timeless story to the moment, is exactly what changes each regeneration, and drives the changelog. Without it the card is timeless = stale.
- **Body (the arc).** Beats built from scene + quote + context, ordered by archetype, not a flat recitation. Every featured stat carries its "so what" — **data as narrative context, never a bare number.**
- **Kicker (an ending that lingers).** Vary the TYPE per card (another anti-formula lever): circular callback to the lede · a forward-looking open question · a quote kicker · a factual gut-punch. "What he needs now" is one kicker, not the only one.

**The open-loop engine.** The collapsed card deliberately opens a **curiosity gap** — the tension line is a question in disguise ("fans see a star; the tape says 24th-percentile — why?") — and the expand pays it off. Progressive disclosure (card spec §4) isn't just space-saving; it's the open-loop → payoff structure that pulls readers in. The hero fact (BAN) must **land in under a second**; everything else is the pull-deeper. Surface the fact, then reward the curious.

**State-dependent composition (the temporal axis).** Beyond per-player archetype (§4b), the card recomposes by MOMENT (NFL.com "transforms on game day"): `offseason` (story + projection) · `game-week` (stakes + matchup) · `live/post-game` (what just happened leads) · `breaking` (the new beat + "why now" front-and-center). Same player, different shape by *when* you look — an anti-staleness lever and the answer to the mid-game-freshness open item (§9).

**New module — the Arc spark.** A tiny career-trajectory sparkline with the inflection marked (Nico's Tennessee→UCLA turn + production drop). Research: a single "when it turned" timeline holds attention longer than 800 words. Data-driven, no LLM; pairs with the chapter + changelog. Added to the module palette ([[41-player-story-card]] §4).

## 5. Completeness — INDEPENDENT coverage (not a circular self-check)

v1's "ask the same LLM if it missed anything" was a filter, not a net. v2 checks against a **superset** of the writer's evidence:

- **Deterministic structural checklist:** every structured event above a career_impact threshold (season-ending availability gap, transfer, role lost, award…) MUST be represented or explicitly, justifiably skipped. This is non-LLM — it cannot "forget."
- **Full-corpus topic scan:** independently re-rank the player's top keyness topics over the *entire* corpus (not the filtered writer package); each high-salience topic must be addressed. Catches what the writer's context dropped.
- **Bounded forcing:** a missing high-salience beat is **injected as required input** to a single regeneration (not "re-ask and hope"). Max 2 retries; still failing → fall back to LKG + flag for review. No infinite loop, no checklist-prose.

---

## 6. Anti-fabrication (distinct from the editorial stance)

The observer stance permits *reporting* contested discourse; it does NOT permit *inventing* it. Guards:
- **Representativeness floor:** a discourse beat ships only if cross-source + sustained + above the noise floor. One post ≠ a narrative.
- **Entity resolution:** quotes/keyness must actually be about *this* player (same-name + nickname disambiguation), event-date matched.
- **Quote integrity:** sarcasm/irony flag (existing sarcasm_score), no decontextualized splicing, verbatim + linked.
- **Keyness ≠ fact:** a cluster containing "arrest"/"injury" establishes *that people discussed it*, framed as such — never that the event occurred.
- **No parametric claims:** the LLM may propose, but a beat dies without plane evidence + citation.
- **High-risk band:** routed by the §1 policy knob.

---

## 7. The persistent Character Bible (with correction semantics)

Per-player evolving canon — long-term memory that keeps the divorce in the story at week 10 and stops logline whiplash.

```
bible = {
  identity{},                         # stable
  permanent_beats[], current_beats[], # two registers (§4)
  canon_events[],                     # with supersession, NOT pure append-only
  arc_state{chapter, tensions[], trajectory},
  logline, logline_locked_event_id,   # changes only on a new inflection
  data_coverage_flag                  # "no story" vs "no data" — never conflated (cold start)
}
```

Each regen **updates** the bible (LLM as state-transition fn). **Correction/supersession/retraction** semantics (an event can be corrected or superseded with provenance — append-only would fossilize mistakes). Every update writes a **snapshot** → the "scrub the story across the season" changelog, for free.

---

## 8. Pipeline (per player, per trigger)

```
1  assemble evidence (3 planes, trust-tiered, independence-deduped)
2  NEL-A: structured event ontology (zero-discourse beats)
3  NEL-B: discourse enrichment (baseline-z, keyness, representative quote)
4  fuse + score 5 salience axes (bot/rival-discounted)
5  bible update (two registers, supersession, logline stability, coverage flag)
6  BAN select (honesty-gated, §6 of card spec)
7  ARCHETYPE + PLAN (planner LLM): classify narrative archetype → compose modules (which / order / lead / tone, §4b); map beats → structure; set tension; pick quote; assign voice (fact/discourse/inference)
8  WRITE (writer LLM = mistral-small3.2): observer voice for discourse, word caps, receipt markers
9  GROUND (every claim → row OR independent discourse evidence OR trusted canon; high-risk → policy knob)
10 COVERAGE (deterministic checklist + full-corpus topic scan; bounded forcing ≤2)
11 SAFETY/VOICE (attribution audit, compiler label, banlist, allegation≠finding)
12 EVAL + LKG (factscore + slop + coverage score; pass → cache+LKG; fail → keep LKG)
```

Stages 7–8, 12 reuse the Chronicle runtime. Net-new: 2–5, 10, and the voice/coverage logic.

---

## 9. Triggering — event-driven

Regenerate on any structured event (transfer/role/availability/award/NIL) **or** a discourse spike/sentiment swing; else reuse. Structured triggers mean zero-spike events still fire (fixes the v1 blind spot at the trigger layer too).

## 10. Tiering + cold start

- **S/T1** full pipeline; **T2** lighter; **T3** long tail = deterministic factual strip, no LLM.
- **Cold start / sparse:** `data_coverage_flag` distinguishes **"no story"** from **"no data."** A brand-new freshman with no baseline gets the factual strip, NOT manufactured significance from noise. Empirical-Bayes shrinkage toward a cohort prior prevents "every mention is a spike."

---

## 11. Evaluation — or the coverage critic is theater

Automatic checks can't *prove* "didn't miss the obvious" without ground truth. Build a tractable benchmark (not 23k — the players + cases that matter):

- **Gold must-mention set:** ~50–100 notable players, human-labeled top-3 narratives. Measure **miss-rate.**
- **Adversarial rumor set:** seeded fake/satire/rival posts. Measure **false-amplification rate** (did a non-narrative get presented as the narrative?) and **mis-framing rate** (discourse asserted as fact).
- **Temporal holdout:** hide a known event's evidence; confirm the engine omits honestly rather than inventing.
- **Feedback loop:** the card's "report an error" (card spec §8) feeds labels back → the living benchmark.

Targets gate promotion of a tier from shadow to live.

---

## 12. Build gap list (honest)

| Component | Status |
|---|---|
| structured event ontology (NEL-A) | NEW — the core unlock |
| `narrative_beats` table (5 salience axes, evidence_json, framing) | NEW |
| discourse baseline-z + player-grain keyness (shrinkage, disambiguation) | PARTIAL (keyness engine exists) |
| `player_bible` + snapshots + supersession | NEW |
| independent coverage (checklist + full-corpus scan, bounded forcing) | NEW |
| observer-voice + framing classifier + compiler label | NEW |
| narrative archetype classifier + module composition rules | NEW — the anti-formula core (§4b) |
| fanbase-keyed voice (keyness vocabulary fed into the writer) | NEW (keyness engine exists) |
| canon acquisition (Wikipedia CC-BY-SA + existing google_news, **top-N only**) | NEW, scoped |
| gold/adversarial benchmark + report-an-error loop | NEW |
| Chronicle runtime (planner/writer/eval/LKG/banlist) | REUSE |

> Canon is not a turnkey dataset (licensing/paywall/dedup/entity-resolution/correction). Scope it to Wikipedia + the existing news adapter for top-N players; accept partial; when an event predates coverage and no trusted source exists, **omit honestly.**

---

## 13. Failure modes & guardrails

- **Zero-spike event** → caught by structured ontology (§3a), not discourse.
- **Gossip/rumor IS the story** → reported in observer voice with attribution + representativeness floor (§1, §6); high-risk band → policy knob.
- **Fake/troll/bot amplification** → representativeness + independence + bot/rival discount; it never becomes "the narrative."
- **Quiet excellence / no story** → quiet true card or factual strip; never manufactured drama.
- **Career-defining old event buried** → permanent register, no decay.
- **Cold start** → data_coverage_flag; factual strip, not noise.
- **Regen loop** → bounded forcing ≤2 → LKG + review flag.
- **Bible fossilizes a mistake** → supersession/correction semantics + report-an-error.
- **Logline whiplash** → locked to inflection events.
- **Cherry-picked BAN** → honesty gate.

---

## 14. Sequencing

1. Structured event ontology + `narrative_beats` (NEL-A) — catches the obvious, no LLM needed.
2. Discourse enrichment + 5-axis salience (NEL-B) — adds drama + the representativeness gate.
3. `player_bible` + snapshots + supersession — continuity + changelog.
4. Independent coverage + observer-voice writer + compiler label.
5. Canon backfill (top-N) + gold/adversarial benchmark.
6. Wire into Chronicle; ship S/T1 in shadow, gate on benchmark, then live; T2 next; T3 strip-only.

---

## 15. Worked example — Nico, end to end

1. **NEL-A** fires `transfer_controversy` from the transfer row + an `availability/role` shift (Aguilar arrives at Tennessee → team→player propagation) — **before any discourse**.
2. **NEL-B** enriches: April volume break + negative valence + keyness {nil, holdout, tennessee, money, portal} + a representative quote; trusted-news canon supplies the reported spine.
3. **Salience:** career_impact HIGH, confidence HIGH (trusted news + cross-source corpus), discourse_intensity HIGH (bot/rival-discounted) → top beat. Framing `attributed`.
4. **Bible:** permanent canon event, `is_inflection` → Chapter 2→3; logline locks "the five-star who went home."
5. **Write (observer voice):** _"After a public standoff at Tennessee that reporters framed as an NIL dispute, he went home to UCLA."_ — compiled, attributed, not adjudicated.
6. **Coverage:** the structural checklist lists the transfer as career_impact-high → the card MUST address why he left, or it's rejected. No more narrating around the elephant.

---

## 16. Provenance

Built on the real DB state (queried 2026-06-11), the Chronicle architecture, the existing keyness engine, and the Story Card spec ([[41-player-story-card]]). v2 incorporates Codex + Gemini adversarial review (structured-first detection, independent coverage, decomposed salience, feasibility) and the owner's editorial stance (compile the conversation, gate on representativeness not truth, observer voice, residual-risk policy knob).
