# 52 — CFB-Team Content Model ("The Tribe, the Standard, the Carousel")

_Status: CONTENT SPEC (critique-hardened v2). Created 2026-06-11 from a Team-mode multi-AI brainstorm (Codex + Gemini + Claude) cross-referenced against the live discourse corpus and the real team-page modules; v2 adds the Financial-Anchor gate on the institution character (§3.2), the Deprival read for realignment orphans (§3.1), and the anti-formula composition layer (§9.5). The DOMAIN layer — what to detect, track, and say about a college-football **program** — consumed by the engine ([[51-team-narrative-engine]]) and rendered by the card ([[50-team-story-card]]). The team analog of [[43-cfb-native-content-model]]._

---

## 0. Thesis — a team is five things at once

A pro franchise is evaluated in the present tense: are they good, right now? **A college-football program never is.** It is simultaneously:

- **the tribe** — belonging; the fan *is* the team ("we won," "we're back"), an identity inherited from family, state, school;
- **a franchise being run** — the coach, the AD, the boosters, the NIL collective, rev-share "are they willing to pay to win";
- **a campaign in progress** — the season as a path ("win and in," "control our destiny," "eliminated");
- **a multi-generational saga** — droughts, championship years, the Standard the fanbase believes it is owed;
- **a node in a web of enemies** — 2–4 named rivals, scrambled by realignment.

And the core engine is not performance — it is the **Standard-Gap** (§2): the distance between a program's actual standing and the standard its fanbase believes it is *owed*. The same 8-4 season is a coronation at Kansas and a fireable offense at Alabama. *"The NFL is a game of assets; college football is a game of birthrights."*

The card's CFB-native job: **locate a program in time (week/season/era/generation/all-time), against its Standard, across its four ledgers, rendered in a chosen tribe's POV.**

---

## 1. Belonging is the SUBSTRATE, not a ledger

The single biggest difference from the player model ([[43-cfb-native-content-model]] §1, five co-equal ledgers): for a team, **belonging is the camera, not a character.** It is *why* the tribe is in the room arguing, and it sets the **emotional gain** on every other signal. A blue-blood fan and a Group-of-5 fan can have identical 7-5 records and opposite moods because belonging assigns different *meaning* to the same fact.

**Implementation:** belonging is a per-program **multiplier on the Standard-Gap and on ledger intensity**, derived from program tier + fanbase size/intensity (profile `program_tier`, `cultural_anchors`, `fanbase_health.py` / `backometer` sample size) — not a fifth score competing for the lead.

---

## 2. The two axes (the salience backbone)

Every program resolves onto two axes pro sports lacks, which drive the lead and tone ([[51-team-narrative-engine]] §3):

- **The Standard axis (the Standard-Gap / Birthright Delta).** `standard_gap = actual_standing − self_conceived_standard`. The standard comes from `program_tier` + historical peak (`program_prestige_bar.py`, `ceiling_floor.py`, `aspiration_ladder.py` already encode it); actual standing from the current season + rankings. A large negative gap at a blue blood = crisis; near-zero at a riser = triumph. **This is Gemini's "Ghost Meter"** — a program "playing against its own history" — folded into a single named scalar, not a separate widget.
- **The Belonging axis (§1).** The gain. Sets whether the gap reads as heartbreak or as house money.

Archetypes are regions of this space (Blue Blood · Riser · Sleeping Giant · Perennial Almost · Have-Not), and they set the card's tone — the same record, narrated differently per region. Perturbing forces: the **coaching carousel, the portal, NIL/rev-share, and realignment**.

---

## 3. The four ledgers × the six characters

The ledgers are the **registers** the tribe argues in; the characters are the **subjects** the registers attach to. A claim = `(character, ledger, polarity)`. Belonging (§1) is the substrate beneath all of them.

### 3.1 The four ledgers (re-derived for teams)

- **The Standard Ledger** (*judgment turned inward — worthiness vs birthright*). "Are we who we say we are?" Feeds: the Standard-Gap, "this is a fireable season," "best stretch since the dynasty." Data: record/rankings vs `program_tier` + historical peak.
- **The Grievance Ledger** (*disrespect as fuel — outward*). "Nobody respects us," committee screwed us, "we haven't played anybody," bulletin-board material, national-perception-vs-fanbase-perception. Data: ranking vs résumé (SP+/results), coverage volume, keyness `{disrespect, snub, robbed, overrated→us}`, schedule strength.
- **The Grudge Ledger** (*rooting against > rooting for*). Rivalry, schadenfreude, rent-free, the realignment wound (a killed/scrambled rivalry). Data: `rivalry_pairs`, `rivalry_obsession_weekly`, `rent_free_module`, rival-`audience_bucket` sentiment, "days since" beating the rival.
  - **Deprival sub-read (2026, review fix):** for programs *orphaned* by realignment (Oregon State, Washington State — left out of the superconferences), the live emotion is not Grudge against an enemy they no longer play, it is **Deprival** — the quiet grief of lost relevance/media value. Detect the "left behind / forgotten / irrelevant" signal (corpus: `left behind`(55), `realignment`(665)) and narrate Deprival honestly rather than manufacturing a Grudge against a vanished rival.
- **The Hope Ledger** (*the offseason Hope Economy — relentlessly forward*). Recruiting class, the portal (in AND out), returning production, spring ball, NIL-collective health, "are they willing to pay to win." Data: `recruiting_footprint`, `top_commits`, `transfer_position_snapshots`, `offseason_pulse`, `roster_reload`, `delusion_premium_weekly`.

> The Standard Ledger is the keystone — it is the inward judgment that gives every other ledger its emotional weight. Grievance is the Standard pointed outward at the nation; the Grudge is the Standard measured against a specific enemy; Hope is the Standard projected forward.

### 3.2 The six characters (the subjects)

The card models these as first-class entities — **(a)** the head coach (era, hot seat, honeymoon, identity, buyout/search — [[53-program-succession-coaching-carousel]], NO structured source today, the highest-leverage net-new build); **(b)** the rivalry web (2–4 enemies, stakes, realignment wounds — `rivalry_card.py`); **(c)** the conference / realignment context (peer set, "did we belong" — `conference_standing.py`); **(d)** the institution (AD, boosters, NIL collective, rev-share willingness — the 2026 "Shadow-GM audit," largely net-new data). **Financial-Anchor Gate (review fix):** fan guessing about NIL-collective health is ~99% misinformation, so the institution character may **never assert a "pay-to-win" claim as fact from discourse alone.** It is gated to verified cap-spend data or Tier-A investigative reporting; absent that, it may only *report the discourse as discourse* ("the fanbase is debating whether the administration will pay") or stay silent — never "they aren't paying to win." See [[51-team-narrative-engine]] §3g (institution disabled without a Financial Anchor); **(e)** the fanbase-as-collective (mood, faith, revolt — `fanbase_health.py`, `backometer`, `delusion_module`); **(f)** the recruiting/portal class (the incoming cast — `recruiting_footprint`, `top_commits`, `roster_reload`).

**Coach-as-protagonist without becoming a coach page (the resolved paradox):** the coach is **the lens the fanbase looks *through*, never the subject the card looks *at*.** The card narrates the *program's* state; the coach appears as the fanbase's current *explanation* for it ("they believe the ceiling is the staff"). The instant the subject becomes the man rather than the tribe's relationship to the man, it has failed.

---

## 4. The Tribal Lens — render the disagreement

The same program is a different story to its own tribe, the nation, and its rivals ([[50-team-story-card]] §5; [[51-team-narrative-engine]] §5). Home (default human, partisan in emphasis) / National (honest, the indexed H1) / Rival (the confession, bounded by the **Home-Anchor Rule** — [[56-team-fan-ledger-detectors]] §3). Data: `audience_bucket` (home/rival) + per-slice sentiment/keyness. Guardrail: minimum source diversity per slice + cohort size shown, so a small hostile community can't masquerade as "the narrative." **Why singular to teams:** rival hate-reading is a *primary* use case for teams (more than for players) — schadenfreude as a feature, kept honest by only echoing what the tribe already confesses about itself.

---

## 5. The Offseason Engine — the Hope Economy (always forward-looking)

The offseason is not dead time; it is roster-construction theater, and the card runs in a **projective mode** keyed off `backometer_weekly.is_offseason` and an internal calendar:

```
bowl afterglow/grief → early portal → Signing Day → spring ball
   → spring portal → summer hype/watchlists → fall camp → kickoff countdown
```

Mechanics: **Case For / Case Against next season** (compile the bull and bear from the corpus); **the portal ledger** (net talent flow in AND out — "who replaces the departed star," `transfer_position_snapshots`); **the recruiting-class verdict** (rank + the Hope it buys); **the rev-share audit** (NIL-collective health, "are they paying to win" — the 2026 character); **the Countdown** (reuse the existing kickoff-countdown module). National Signing Day and the portal windows are high-holy-days — `calendar_pressure` spikes the lead's eligibility.

---

## 6. The Temporal Heartbeat — five nested timescales

The program runs on five timescales at once, and they are **nested and interrupt each other** — most days only the top layer (week-mood) moves; a **Timescale-Piercing Event** drops the shockwave all the way down (a rivalry loss dents the week, indicts the coach/era, and reopens an all-time wound). The resolver leads with the layer that *moved* ([[51-team-narrative-engine]] §3); the layer that *frames* is set by the era (recency is the headline, the arc is the gravity — "another November collapse" vs "a stumble," same result, different adjective).

Unifying mechanics:
- **The "PREVIOUSLY ON…" recap** — the season as plot-points, the crown's expand affordance ([[50-team-story-card]] §4). The one Gemini-widget idea that earns crown space because it *is* the campaign's heartbeat, not a separate module.
- **The Flip Point** — the moment a fanbase flips "it's over" → "we're so back," detected as a `backometer` sticky-zone crossing; the card names it and dates it ("↻ this story shifted").
- **The changelog = the season's emotional EKG** — `team_season_narratives` snapshots scrubbed across the year (the Bible's history, [[51-team-narrative-engine]] §7).

---

## 7. CFB-team module catalog (what feeds what)

| Surface | Ledger / engine | Primary data (live module/table) | LLM? |
|---|---|---|---|
| Standard-Gap / Ghost Meter | Standard | `program_prestige_bar`, `ceiling_floor`, `aspiration_ladder`, rankings | no |
| Respect Gap (rank vs résumé) | Grievance | rankings + SP+ + coverage volume | no |
| Rivalry Memory + realignment wound | Grudge | `rivalry_card`, `rivalry_obsession_weekly`, `rent_free_module` | no |
| Hope Economy (recruiting/portal/NIL) | Hope | `recruiting_footprint`, `top_commits`, `transfer_position_snapshots`, `offseason_pulse` | no |
| Coach state (era / hot seat) | character (a) | `coach_pressure_weekly` (NEW, [[53-program-succession-coaching-carousel]]) | light |
| Fanbase mood / Flip Point | character (e) | `backometer_weekly`, `fanbase_health`, `delusion_premium_weekly` | no |
| Conference / realignment context | character (c) | `conference_standing`, realignment seed | no |
| Institution / rev-share audit | character (d) | NEW (NIL-collective/booster signal), profile fields | light |
| Tribal Lens (Home/National/Rival) | rendering | `audience_bucket` + per-slice keyness | yes (voice) |
| Path object (win-and-in / eliminated) | Standard/season | standings + CFP/bowl math | no |
| "PREVIOUSLY ON…" recap | Temporal | bible snapshots | light |

Most are **deterministic** — consistent with the layered build ([[58-team-build-philosophy]]): determinism owns truth, the LLM owns voice + composition.

---

## 8. Honest data inventory

**Have (live):** `backometer_weekly` (belief 0–100, zones, delta_wow, is_offseason, is_low_signal), `team_conversation_daily` (sentiment), `pulse_themes`/`pulse_state`, `state_resolver`/`PageState` (mode/tone/accent), `team_season_narratives` (+state_signature), `rivalry_pairs`/`rivalry_obsession_weekly`/`rent_free`, `delusion_premium_weekly`, `recruiting_footprint`/`top_commits`/`transfer_position_snapshots`, `conference_standing`, rankings/SP+, `audience_bucket`, `profiles/*.md` (127, full FBS voice), `chronicle_calendar_pressure`.

**Need / net-new:** the **coach** character (`coach_pressure_weekly` + a hand-seeded `coaching_tenure` table — [[53-program-succession-coaching-carousel]]); the **institution** character (NIL-collective / booster / rev-share signal — partial, scope to discourse + profile fields first); team-grain Grievance/Standard keyness lexicons ([[56-team-fan-ledger-detectors]]); realignment "did we belong" as a first-class signal.

---

## 9. How the engine consumes this

- Ledgers + characters → the structured **beats** + claims ([[51-team-narrative-engine]] §4, §9).
- Two axes (Standard-Gap × Belonging) → the **lead resolver** weighting + the **tone** ([[51-team-narrative-engine]] §3).
- Tribal Lens → the three-rhetoric payload ([[51-team-narrative-engine]] §5).
- Offseason mode + calendar → the **Hope-Economy** branch + `calendar_pressure` eligibility.
- Bible snapshots → the **emotional-EKG changelog**.

## 9.5 The anti-formula layer — bespoke by composition + lexical injection

The deepest risk the review flagged: a single confident-compiler voice across 119 programs **converges in texture** — the *reasoning* differs (the Standard-Gap), but the *cards read interchangeably*. The player engine solved this with composition variety + fanbase-keyed voice ([[42-player-narrative-engine]] §4b); the team engine needs the same three levers, biggest first:

1. **Compositional variety — the card SHAPE differs by archetype.** A **Blue Blood** leads with the Standard-Gap and the era; a **Have-Not** leads with the single game that defined the year; a **Riser** leads with the proof-of-legitimacy question; a **Sleeping Giant** leads with the dormant ceiling; a **Perennial Almost** leads with the hump it can't clear. Archetype (from §2's Standard×Belonging space) sets which threads appear, their order, and the lead framing — different skeletons, not different mad-libs.
2. **Lexical injection — forced per-team vocabulary (review fix).** The writer is **passed and required to use** the program's own words from `profiles/*.md` (`identity_phrase`, `mantra`, `vocab.selfname`, `rituals`, `cultural_anchors`). Michigan must reach for "The Standard" / "The Game"; Georgia for "Hunker Down"; Alabama avoids `never_use` terms. Without per-team token injection, the Noir voice collapses into generic corporate AI. The 127 hand-authored profiles already hold this vocabulary — this is why template mode is publishable.
3. **Archetype-gated shift vocabulary.** The **Flip Point** (§6) must not render the same "we're so back / it's over" binary on all 119 pages. A Blue Blood says "the Standard has been restored," a Have-Not says "we've arrived," a Riser says "the breakthrough" — `program_tier` gates the vocabulary of the shift so the site reads like a program bible, not a meme aggregator.

Determinism owns TRUTH (facts, gates, the resolver); the LLM owns EXPRESSION + COMPOSITION (shape, voice, the program's own words) — orthogonal axes, so the model runs rich *because* every fact it touches is gated ([[58-team-build-philosophy]]).

## 10. Provenance

Team-mode multi-AI brainstorm (Codex feasibility · Gemini 2026 cultural/ecosystem — Tenure Equity, the Schedule-Victim complex, the rev-share Shadow-GM audit, the Ghost Meter, Deprival · Claude pattern/paradox — belonging-as-substrate, the Standard-Gap, coach-as-lens), 2026-06-11; v2 hardened by the multi-AI set review (lexical injection, Financial-Anchor gate, Deprival). Cross-referenced against the live discourse corpus and the real `team_pages/` modules + `backometer_weekly`. Builds on [[43-cfb-native-content-model]], [[51-team-narrative-engine]], [[50-team-story-card]].
