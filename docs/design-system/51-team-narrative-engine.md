# 51 — Team Narrative Engine ("The Program Bible")

_Status: ARCHITECTURE SPEC (critique-hardened v2). Created 2026-06-11; the lead resolver and freshness model were red-teamed (five named failure cases, §3), then the whole set got a multi-AI review (Codex 19 findings, Gemini, Claude) — v2 folds in the per-character feature contract (§3g), the lead-kind/render-rung split (§3e), the resolver edge cases (§3h), the evaluation plan (§12), the failure-mode table (§13), and a worked end-to-end example (§14). The content brain behind the Team Story Card ([[50-team-story-card]]). Extends the Chronicle pipeline ([[CLAUDE.md]] Chronicle LLM pipeline) and the existing `state_resolver`/`PageState` into one immutable program-narrative state. This doc is the generation *machinery*; [[52-cfb-team-content-model]] is *what to say*. Not yet implemented._

> The CFB-team domain layer this engine consumes — the tribe-as-substrate, the Standard-Gap, the four ledgers, the six characters, the Tribal Lens, the Hope-Economy offseason mode, and the five-timescale heartbeat — lives in [[52-cfb-team-content-model]].

---

## 0. The core problem — the spine gap

The team page is not a greenfield. It already runs `pulse_lede.py` (an Opus-tier fan-voice editorial), `pulse_themes.py` (Haiku-scan → Opus-rank themes with quotes), `state_resolver.py` (a `PageState` that already knows the page is in RIVALRY PEAK or AUTOPSY mode), `narrative_generator.py` (state-of-team paragraphs in per-program voice), and `backometer_weekly` (a 0–100 fanbase-belief score with named zones, hysteresis, and a `delta_wow` week-over-week derivative — already computed nightly). **These are excellent organs with no spine.** The page knows its mode but narrates from that knowledge in a dozen scattered places, never once at the top, never picking a single lead.

The engine's job: **synthesize one ProgramNarrativeState (§9) per team per day — pick the lead (§3), detect the beats (§4), keep the program bible (§7) — and feed the crown ([[50-team-story-card]]).** It consolidates; it does not duplicate.

---

## 1. Editorial stance — THE organizing principle

Carried verbatim from the player engine ([[42-player-narrative-engine]] §1), with one team-specific twist.

**The site compiles the conversation; it does not adjudicate it.** A confident-compiler voice states the dominant fan take with conviction, **attributed to the fanbase** (or to the nation, in the National lens), paired with a **confidence meter** and dissent shown as a **labeled minority**. The gate is **REPRESENTATIVENESS** (is this genuinely the narrative?), not truth. Three voices kept visibly distinct — **Fact** (structured rows, trusted canon), **Discourse** (the corpus, "what people are saying"), **Inference** (minimal LLM connective tissue, never a new claim). Narrow do-not-amplify floor for unverified criminal/legal/medical allegations, pile-ons, doxxing ([[49-pragmatic-v1-critique-corrected]] C7).

**The Self-Narration twist (unique to teams).** For a player, the *nation* narrates the subject — speaker and subject are separate, so attribution is clean. For a team, the **tribe narrates the tribe** — speaker and subject collapse, and the tribe lies to itself (copium and doom are emotional weather, not the settled take). The honesty mechanism: **label every take's half-life.** Distinguish the **Settled Belief** (stable across weeks — the `backometer` sticky `zone`) from the **Reactive Surge** (spiked since Saturday — a large `delta_wow` that has not yet persisted). The card never adjudicates which is "true"; it shows both, labeled by freshness. A Reactive Surge can fill the *tension line* but cannot rewrite the *logline* until it persists into a Settled Belief or is a hard event.

---

## 2. Three evidence planes

| Plane | Holds | Asserted as | Role |
|---|---|---|---|
| **Structured** | results/standings, rankings (CFP/AP/SP+), coaching moves, recruiting/portal deltas, conference/realignment, betting/path odds, `backometer` belief | fact | skeleton (what is / what moved) |
| **Discourse** | doc-level: `conversation_documents` / `conversation_document_targets` (body, source origin, doc id, `audience_bucket`, `sarcasm_score`) for evidence + independence; aggregate: `team_conversation_daily` + `backometer` for mood/belief; `pulse_themes` + keyness for labels | observed conversation | drama + voice (why/how it feels) |

> **Source-grain rule (review fix):** `team_conversation_daily` is a daily *aggregate* — it gives mood/volume, never doc-level evidence or source independence. Anything that needs a quote, an evidence id, or a `MIN_SOURCES` count reads the **doc-level** tables (`conversation_documents`/`_targets`), exactly as the player detectors do ([[47-fan-ledger-detectors]]).
| **Canon** | program history, droughts, championship years, profile `cultural_anchors`, news + Wikipedia w/ trust tier | reported fact ("per [outlet]") / program lore | the era/generation/all-time spine |

Source-trust tiering + independence dedup as in [[42-player-narrative-engine]] §2 — N reposts of one thread = 1 source. Trusted outlet > aggregator > named account > anonymous.

---

## 3. The Lead Resolver — Level-anchored, displacement-overthrown (THE centerpiece)

Five timescales (week / season / era / generation / all-time) × six characters (coach · rivalry · conference · institution · fanbase · roster) compete for the top line. Two rival doctrines were red-teamed and **both fail alone**: pure *salience* (weighted level) deadlocks on a Stale Giant and over-indexes a manufactured recruiting spike; pure *displacement* (lead with what moved) goes silent on a blue blood in June and misses the slow burn. The synthesis survives all five attacks.

### 3a. The scoring function (per candidate character)

```
EffectiveLevel = salience score (§3b) with an age rule (§3c)
D              = max(D1, 0.75·D7, 0.50·D42)        # multi-window belief displacement
Final          = 0.60 · EffectiveLevel + 0.40 · D
```

`D1/D7/D42` = **absolute** cumulative change in fanbase belief over 1 / 7 / 42 days, normalized 0–100 — used for *magnitude*. The **sign** is retained separately as `D_dir ∈ {+,−}` (a collapse and a surge both displace, but they tell opposite stories — the framing verb keys off `D_dir`). The 42-day window catches the **slow burn** (a coach's seat heating ~2 pts/day → `D42≈30`, which beats a one-day +8 rivalry blip). **Grounded:** for the *fanbase* character, `D7 ≈ backometer_weekly.delta_wow` (already computed, already hysteresis'd); `D1` comes from `team_conversation_daily` day-over-day belief deltas. The other five characters get their displacement from their own structured deltas via the **per-character feature contract (§3g)** — and a character with no qualifying source is **disabled, not zero-scored** (§3g).

### 3b. EffectiveLevel features (the salience layer)

```
level = 0.24·recency + 0.22·magnitude + 0.15·discourse_volume
      + 0.14·calendar_pressure + 0.10·volatility + 0.10·evidence + 0.05·profile_relevance
```

- `magnitude` — deterministic lookup (coach fired 100 · conference move official 95 · rivalry upset 75–95 by spread/rank · 5★ commit 70 · routine win 25).
- `discourse_volume` — percentile vs the **program's own** trailing-90-day baseline (not national volume), and **capped at 10 pts unless ≥10 pts of belief displacement back it** — this kills the manufactured recruiting spike (3 commits make noise, not narrative).
- `calendar_pressure` — rises near signing day, rivalry week, kickoff, selection day, buyout dates, portal windows (reuse `chronicle_calendar_pressure`).
- `profile_relevance` — program identity affinity from `profiles/*.md` (Alabama weights titles; Vanderbilt weights sustainable progress).

### 3c. The age rule (breaks the Stale-Giant deadlock)

- **Event** stories decay on a 7-day half-life after their last meaningful development.
- **Continuing states** (a coaching era, the Standard-Gap) retain their level while current evidence supports them.
- **Repeat penalty:** −10 after 3 consecutive days with no new evidence, **applied once and ONLY to event candidates** — a 3-week-old marquee win stops being crowned every morning. **Continuing states (a coaching era, the Standard-Gap, an offseason Standing Lead) are exempt** — they are *supposed* to persist unchanged, so they never decay into the Quiet State merely because nothing moved (review fix; "new evidence" = a fresh beat on that character, not the mere passage of time).

### 3d. Timescale selection (after character)

```
this_week    event score ≥ 75 and age ≤ 10 days
this_season  season-state delta ≥ 15 percentile points (path/standing moved)
this_era     coach/roster regime evidence ≥ 3 seasons, or a regime change
generation   sustained structural shift ≥ 8 seasons / a drought threshold crossing
all_time     records, anniversaries, historic threshold crossings only
```

Never let an all-time anecdote displace an active firing, rivalry game, or season inflection.

### 3e. Cold start, Quiet State vs Standing Lead, hysteresis

- **Cold start** (week 1, or a team with no `backometer` history) → `D` is **undefined, not zero** (never synthesize a prior). The candidate's `Final` falls back to `EffectiveLevel` alone (i.e. `Final = EffectiveLevel` until ≥7 days of belief history exist), so the resolver is always evaluable; the `D<15` Quiet-State test is **skipped** while `D` is undefined and the team uses the `EffectiveLevel < 45` arm only.
- **`lead_kind` is separate from `render_rung` (review fix).** The resolver decides *whether there is a lead and what it is* (`lead_kind ∈ {active, standing, quiet}`); the degradation ladder ([[57-team-dependency-degradation-matrix]] §3) decides *how richly it is written* (`render_rung ∈ {1..4}`). They are orthogonal: **a hard structured event (§4) is always an `active` lead even with zero discourse** — it is never demoted to `quiet`; thin discourse only lowers its `render_rung` and strips fanbase-attribution language ("the fanbase believes…"), leaving the factual lead intact ("Tennessee fired its head coach Tuesday").
- **Quiet State** (`lead_kind=quiet`) **only** when `EffectiveLevel < 45 AND D < 15` **and no active structured beat exists**. Otherwise a quiet week leads with the **Standing Lead** (`lead_kind=standing`) — the strongest *continuing state*. This is why June-Alabama leads with "the DeBoer era enters Year 3 under championship expectations," not silence. The `backometer_weekly.is_offseason` flag is the literal branch into Hope-Economy / Standing-Lead mode ([[52-cfb-team-content-model]] §5).
- **Hysteresis** (anti-whiplash): a normal challenger must beat the incumbent by 12 pts; during a 48-hour minimum hold, by 20; a **hard event** (firing, hire, playoff selection, conference move, rivalry result) bypasses the hold; once a held lead falls below 45 it is no longer protected; same-character updates *modify* the current story rather than count as a lead change. Reuses the `backometer` sticky-zone pattern, not a new mechanism.

**The doctrine (one line):** *displacement can overthrow the standing story, but absence of displacement cannot erase a strong standing story.*

### 3f. Worked examples

```
Michigan, rivalry week        rivalry  Final≈92  → leads ("The Game walks into Columbus")
  ↑ coach fired Wednesday      coach    Final≈100 → hard event bypasses hysteresis, takes the lead
Slow-burn coach, week 6        coach    level 68, D=max(2,10.5,30)=30 → 0.60·68+0.40·30 = 52.8 → leads
  vs a static rivalry          rivalry  level 54, D=0               → 0.60·54           = 32.4
Alabama, dead June             era      level 82, D=0 → 49.2 → Standing Lead (no silence)
  vs a recruiting blip         roster   level 42, D=8 → 28.4 (discourse capped — blip loses)
```

**LLM-as-ranker is bounded:** the model may re-rank narrative angles only among candidates **within 5 points** of each other; it may never override eligibility, hard-event priority, hysteresis, or the Quiet-State floor.

### 3g. Per-character feature contract (the resolver is only as real as its inputs)

The fanbase character has a concrete displacement source (`backometer.delta_wow`); the other five must each declare a **feature contract** or be **disabled** for that team-week (review fix — "disable unsupported characters rather than inventing scores"). Each character supplies: a Level source, a Displacement source, a normalization, and a null policy.

| Character | Level source | Displacement (Δ over window) | Null policy |
|---|---|---|---|
| fanbase | `backometer.score` vs 50/Standard | `delta_wow` (D7) + daily belief Δ (D1) | `is_low_signal` → fanbase-attribution disabled, not the character |
| coach | `coach_pressure_weekly.pressure` | Δpressure + a phase transition (hard event) | no `coaching_tenure` row → **disabled** (tenure-only fact may still appear as canon) |
| rivalry | rivalry proximity (calendar) + stakes | a played/announced rivalry result (hard event); else 0 | no rival in profile → disabled |
| roster | recruiting-class rank + net portal flow | Δclass-rank, a top commit/decommit, portal influx Δ | offseason-only signal; in-season → low Level, not disabled |
| conference | realignment status + standing | a move becoming official (hard event); else 0 | no realignment activity → Level from standing only |
| institution | **verified** cap-spend / Tier-A reporting only | a reported NIL/booster event from a trusted source | **discourse-derived "NIL health" is NEVER a fact** — disabled unless a Financial Anchor clears ([[52-cfb-team-content-model]] §3.2, [[56-team-fan-ledger-detectors]]) |

A **disabled** character is omitted from the candidate set entirely (it cannot lead, cannot be a supporting thread). The exact per-character normalization (z vs the program's own baseline) and window aggregation are specified at build time against the real columns; until then a character without a validated source ships disabled, not guessed.

### 3h. Resolver edge cases (deterministic, no ambiguity)

- **Two hard events the same day** (e.g. a firing AND a rivalry result): order by `magnitude` (firing 100 > rivalry 92), then by `evidence_quality`, then by a fixed character priority `coach > conference > rivalry > roster > institution > fanbase` (an institutional/coaching rupture outranks a game). The loser becomes the top **supporting thread**, never dropped.
- **No-history team** (cold start, §3e): `D` undefined → `Final = EffectiveLevel`; the `D<15` arm of the Quiet-State test is skipped.
- **Signed displacement** (§3a): magnitude ranks; `D_dir` sets the framing verb. A `+` surge to "we're so back" and a `−` collapse to "it's over" can have identical magnitude and must never be narrated alike.
- **Worked — simultaneous hard events:** Penn State fires its coach Sunday (magnitude 100) the morning after losing to Ohio State (rivalry result, magnitude 90). Lead = **coach** (firing, by magnitude + the `coach > rivalry` tiebreak); the rivalry loss becomes the supporting thread and the *cause* the logline names ("a November loss in Columbus ended the era").

---

## 4. Structured-first event detection (beats fire with ZERO discourse)

As in the player NEL ([[42-player-narrative-engine]] §3), invert v1's discourse-led detection — structured deltas are the net that catches the quiet-but-decisive. Each beat attaches to one of the six characters and carries its own displacement signal:

- **Result / standing** — win/loss, margin, the path object (win-and-in / control-your-destiny / eliminated), bowl/CFP math.
- **Ranking** — CFP/AP/SP+ moves, the Respect Gap (rank vs résumé).
- **Coaching** — hire/fire/extension/hot-seat (from `coach_pressure_weekly`, [[53-program-succession-coaching-carousel]]) — the character with **no structured source today** ([[CLAUDE.md]]: `head_coach` is a bare column), the highest-leverage net-new beat.
- **Recruiting / portal** — class-rank delta, a top commit/decommit, net portal flow ([[52-cfb-team-content-model]] §5 Hope Economy).
- **Conference / realignment** — a move becoming official, a peer-set shift.
- **Fanbase** — a `backometer` zone crossing = a **Flip Point** ("it's over" → "we're so back").

Discourse **enriches** each beat (volume-z vs the program baseline, `pulse_themes` label, a representative `audience_bucket`-balanced quote) but is never required for a beat to exist.

---

## 5. The Tribal Lens — one fact-set, three rhetorics

POV changes rhetoric and emphasis, never facts or confidence ([[50-team-story-card]] §5; [[52-cfb-team-content-model]] §4). Ship as one inline payload; store shared facts once.

```json
{
  "v": 1, "default": "home",
  "shared": { "leadCharacter": "coach", "confidence": 0.78,
              "asOf": "2026-10-12T16:00:00Z", "evidence": ["coach-22","game-441"] },
  "lenses": {
    "home":     { "eyebrow": "THE QUESTION IN COLUMBUS",
                  "headline": "Winning is no longer the whole argument.",
                  "body": "The fanbase is measuring this era against Michigan and January." },
    "national": { "eyebrow": "NATIONAL READ",
                  "headline": "An elite record with one argument left to settle.",
                  "body": "The program's standing now turns on its highest-leverage games." },
    "rival":    { "eyebrow": "WHAT RIVALS SEE",
                  "headline": "The standard has become the pressure point.",
                  "body": "A contender whose defining tests remain unresolved." }
  }
}
```

Each `body` ≤ 450 chars. No per-lens duplication of evidence/confidence/timestamps. The Rival lens is generated under the Home-Anchor Rule ([[56-team-fan-ledger-detectors]] §3) — it may only echo home-fan anxieties + objective stats, never introduce a claim the Home lens lacks. Render the National lens in crawlable HTML (indexing + an honest snippet); the client applies the saved lens from `localStorage`.

---

## 6. Freshness — the stale-lead problem

The site deploys as a 9 AM full snapshot; a coach can be fired at 2 PM. The static card cannot truthfully fold that in — so it labels honestly and never lies with present tense.

```json
{ "built_at": "...", "facts_through": "...", "lead_event_at": "...",
  "freshness_class": "current", "freshness_budget_hours": 12 }
```

Budgets by calendar state: **4h** on game day / coaching carousel / signing day / portal deadline · **12h** in-season weekday · **24h** offseason · **72h** for a historical/all-time lead. Client-side relabel (never rewrite): within budget → "as of 8:42 AM"; 1–2 budgets old → "snapshot from this morning"; older → "last compiled Oct 12"; high-volatility + stale → "developing — snapshot from 8:42 AM." Generated prose avoids "today / currently / right now" unless the budget outlasts the next deploy.

**Two operational fixes the review demanded (because relabeling only *advertises* staleness, it doesn't fix it):** (1) **Event-triggered rebuild** — a hard event (firing/hire/result) during high-volatility windows triggers an out-of-cycle rebuild of just the affected team's crown rather than waiting for the 9 AM snapshot (the box can render one page cheaply). (2) **Predates-a-known-event suppression** — if `facts_through` predates an event the system already knows happened (e.g. a firing ingested at 2 PM but the card built at 9 AM), the stale claim is **suppressed**, not shown with a timestamp: the card drops to the last safe lead + a "developing" banner rather than confidently narrating a superseded state.

---

## 7. The persistent Program Bible (with correction semantics)

Per-program evolving canon — the long-term memory that keeps the drought in the story and stops logline whiplash. **Keyed on the stable program slug** (never a re-ingesting id — the team-side analog of the player `external_id` linkrot fix, [[deploy-clobber-root-cause]], [[46-rollout-and-infra-compat]] §0).

```
program_bible = {
  identity{slug, tier, standard},                 # stable; standard from profile + history
  permanent_beats[], current_beats[],             # two registers: canon never decays
  lead_state{character, timescale, event_id, minimum_hold_until},
  logline, logline_locked_event_id,               # changes only on a Timescale-Piercing Event
  standard_gap, backometer_zone, settled_vs_surge,
  data_coverage_flag                              # "quiet" vs "no data" — never conflated
}
```

The existing `team_season_narratives.state_signature` column gives the **regen-trigger hash** (same-signature → skip), but it is *only* a hash — **the bible itself (the lead-state, the two beat registers, supersession history, the snapshot changelog) is net-new persistent storage**, not something `team_season_narratives` already holds (review correction; the storage table is reconciled in [[55-team-rollout-infra-compat]] §9). Each regen **updates** the bible (supersession, not pure append) and writes a **snapshot** → the season's emotional changelog.

---

## 8. Pipeline (per team, per trigger)

```
1  assemble evidence (3 planes, trust-tiered, independence-deduped)
2  structured event detection (beats fire with zero discourse, §4)
3  discourse enrichment (backometer delta, pulse_themes, representative quote, audience split)
4  LEAD RESOLVER (§3): EffectiveLevel + displacement → character + timescale, hysteresis-guarded
5  bible update (two registers, logline stability, coverage flag, snapshot)
6  BAN select (honesty-gated, [[50-team-story-card]] §7)
7  build typed CLAIMS + ProgramNarrativeState (§9)
8  WRITE (writer LLM): confident-compiler voice, 3 lenses, word caps, receipt markers
9  GROUND (every sentence → claim id → row / discourse evidence / canon; high-risk → policy knob)
10 VALIDATE (contradiction check §9; coverage check; representativeness floor)
11 EVAL + LKG (factscore + slop + coverage; pass → cache+LKG; fail → keep LKG)
```

Stages 8, 11 reuse the Chronicle runtime + `output/site/_cards_lkg/`. Net-new: 2–7, 10, and the resolver.

---

## 9. ProgramNarrativeState + typed claims (the contradiction firewall)

The crown does **not** generate an independent interpretation. The engine emits one immutable build artifact that the crown renders and every downstream module reads ([[54-integration-with-live-team-system]] §2). Important statements are **typed claims** before any prose:

```json
{ "team_slug": "michigan", "as_of": "...", "season": 2026, "page_mode": "RIVALRY_PEAK",
  "lead": { "character": "rivalry", "timescale": "this_week", "event_id": "mich-osu-2026",
            "score": 92.4, "confidence": 0.91 },
  "supporting_threads": [ {"character":"coach","score":78.2}, {"character":"roster","score":65.0} ],
  "claims": [ { "id":"c17", "predicate":"rivalry_control", "value":"at_stake",
                "polarity":1, "evidence_ids":["game-441","ranking-88"] } ],
  "standard_gap": -0.3, "aspiration": {"current":"conf_contender","next":"playoff_control"},
  "tone": {"voice":"guarded_confidence","pressure":0.74,"swagger":0.68},
  "freshness": {...}, "render_tier": "rich" }
```

Every generated sentence maps to claim ids. A **deterministic validator** rejects: opposite polarity for one predicate; a "hot seat" sentence when `coach_pressure` is below threshold; "momentum" when the trend is negative; rivalry leadership when another character won the resolver; an aspiration rung the ladder disagrees with. **The crown is authoritative for interpretation; lower modules add detail but can never introduce a competing program thesis.**

---

## 10. Anti-fabrication

The observer stance permits *reporting* contested discourse; it does NOT permit *inventing* it. Representativeness floor (cross-source + sustained + above noise — one post ≠ a narrative); entity resolution (the take is about *this* program); keyness ≠ fact (a "fire him" cluster establishes *that people said it*, not that he should be); no parametric claims (a beat dies without plane evidence + citation); the Quiet State is a legitimate output, never a gap to fill ([[57-team-dependency-degradation-matrix]]).

---

## 12. Evaluation — or the eval gate is theater

Automatic checks can't prove the resolver leads correctly without ground truth. Build a tractable team benchmark (119 programs is small enough to cover well) and **gate shadow→live promotion** on it:

- **Lead gold set:** ~40 program-weeks across all archetypes (blue blood / riser / sleeping giant / perennial almost / have-not) × all states (in-season game-week, offseason, a firing week, a rivalry week, a quiet 6-6 mid-major), human-labeled with the correct lead character + timescale. Measure **lead-accuracy** and **whiplash rate** (lead flips with no qualifying event).
- **Lens-invariance check:** the three lenses must share identical claims + confidence (only rhetoric differs); a diff in any claim id across lenses is a hard fail.
- **Hot-seat adversarial set:** seeded Saturday-night "fire him" surges over *winning* coaches → measure the **false-hot-seat rate** (the Performance Anchor must hold them at "friction," [[53-program-succession-coaching-carousel]] §4). And seeded brigades → **false-consensus rate**.
- **Quiet-State calibration:** a set of genuinely-quiet programs that MUST land at `lead_kind=quiet` (no manufactured saga) and a set of low-discourse-but-real-event programs that MUST stay `active` (the §3e split).
- **Contradiction rate:** sample rendered pages; count crown↔module thesis conflicts on the shared predicates (§9, [[54-integration-with-live-team-system]] §2) — target 0.
- **Feedback loop:** the card's "report an error" feeds labels back into the living benchmark.

Targets gate each tier from shadow to live ([[58-team-build-philosophy]] §2 promotion).

## 13. Failure modes & guardrails

| Failure | Guard |
|---|---|
| Stale Giant (old win crowned daily) | event 7-day half-life + repeat penalty (§3c) |
| Manufactured recruiting spike | discourse capped ≤10 unless ≥10 belief displacement (§3b) |
| Slow burn missed | multi-window `D42` (§3a) |
| Two hard events same day | magnitude → evidence → character-priority tiebreak (§3h) |
| Cold start / no `backometer` history | `Final = EffectiveLevel`; skip `D<15` arm (§3e/§3h) |
| Hard event with thin discourse demoted to "quiet" | `lead_kind` ≠ `render_rung` — hard event stays `active` (§3e) |
| Lead/logline desync | thesis (logline) vs current lead (eyebrow), allowed to differ ([[50-team-story-card]] §8) |
| Coach defamation / Saturday-night flip-flop | three gates + phase hysteresis + softened speech acts ([[53-program-succession-coaching-carousel]] §4–5) |
| Rival-lens laundering a do-not-amplify topic | Sensitive-Topic Override ([[56-team-fan-ledger-detectors]] §3.2) |
| Institution "pay-to-win" from rumor | Financial-Anchor Gate — discourse never asserted as fact (§3g, [[52-cfb-team-content-model]] §3.2) |
| Every team falls to Quiet State (dead detector) | coverage guard + distribution monitor ([[57-team-dependency-degradation-matrix]] §5–6) |
| Bible fossilizes a mistake | supersession + report-an-error (§7) |
| Stale snapshot vs a known later hard event | freshness suppression + event-trigger option (§6) |

## 14. Worked example — a Tuesday firing, end to end

1. **Beat (§4):** `coach_pressure_weekly` flips to `SEARCH` on an official school announcement → a hard `coach` beat, magnitude 100, evidence = [school PR + 2 Tier-A reports]. Fires with zero discourse required.
2. **Resolver (§3):** coach `Final≈100` bypasses hysteresis → lead = `coach`, timescale `this_era`, `lead_kind=active`. Prior rivalry logline is the *thesis*; the new lead takes the *eyebrow*.
3. **Claims (§9):** `{predicate: regime_end, value: fired, polarity:−1, evidence:[pr-1, report-2,3]}` + `{predicate: standard_gap, value:−0.4}`. Contradiction validator confirms no module asserts "secure."
4. **Render rung (§3e, [[57]] §3):** firing has E≥3, S≥3 → Rung 1 if discourse is rich, Rung 2 if thin — either way the factual lead renders.
5. **Write (3 lenses):** Home — "The era is over; the search the fanbase has wanted is here." National — "[School] parts with its coach after [n] seasons." Rival — bounded by the Home-Anchor Rule: "the buyout they swore they'd never pay." Same claims, three rhetorics.
6. **Ground + validate + eval + LKG:** every sentence → claim id → row/report; factscore + slop pass → cache + LKG. A coach beat **invalidates** any cached recruiting prose ([[58-team-build-philosophy]] §3 — fluent stale prose never survives a lead-character change).

---

## 15. Provenance

Team-mode brainstorm + Codex red-team of the resolver (five failure cases: cold start, blue-blood-in-June, slow burn, manufactured spike, stale giant) 2026-06-11; v2 folds in the full multi-AI set review (Codex 19 findings, Gemini honesty/ecosystem, Claude set-coherence). Grounded in the live `state_resolver`/`PageState`, `backometer_weekly` (score/zone/delta_wow/is_low_signal/is_offseason), `team_conversation_daily`, `team_season_narratives` (state_signature), `chronicle_calendar_pressure`, and the Chronicle runtime. Mirrors [[42-player-narrative-engine]]. Consumes [[52-cfb-team-content-model]]; rendered by [[50-team-story-card]]; coach data from [[53-program-succession-coaching-carousel]]; detectors in [[56-team-fan-ledger-detectors]].
