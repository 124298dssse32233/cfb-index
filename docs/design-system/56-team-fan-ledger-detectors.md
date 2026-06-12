# 56 — Team Fan-Ledger Detectors (Lexicons + Tribal Directionality + Hot-Seat Gates)

_Status: DETECTOR SPEC (critique-hardened v2). Created 2026-06-11. Turns the four team ledgers + the coach character ([[52-cfb-team-content-model]] §3) into buildable detectors. Lexicons are grounded in real corpus doc-frequencies (165,507 non-empty docs of 194,972, queried 2026-06-11), not guessed. **Method is HYBRID** — a target-based stance/emotion classifier (the CardiffNLP + Qwen3 stack already in the repo) with the lexicons as the interpretable feature/seed/explanation layer, per 2026 best practice. v2 adds the Sensitive-Topic Override (§3.2) and a cross-platform `MIN_SOURCES` (§4). The team analog of [[47-fan-ledger-detectors]]. Not yet implemented._

---

## 0. Why grounded lexicons (the team register is its own dialect)

Team discourse is not player discourse. In this corpus the loudest team-scale terms are `program`(6111), `conference`(4992), `transfer`(4813), **`pay`(4517)**, `recruiting`(4286), `portal`(2907), `nil`(2787) — i.e. fans talk about a program as a **roster-construction + money + realignment** entity far more than about any single game. The rev-share "are they paying to win" register (`pay`+`nil`+`collective`) is a real 2026 signal, not a hypothesis. The lexicons below are pulled from actual frequencies so detectors fire on words these fans really use.

---

## 1. Method — 2026 best practice (hybrid stance, NOT a pure-lexicon counter)

Identical to the player method ([[47-fan-ledger-detectors]] §1): a ledger is a **target-based stance/emotion classification** (*does this doc express Standard / Grievance / Grudge / Hope toward THIS program?*) run on the repo's encoder/LLM stack, with the grounded lexicons as the **hybrid interpretable layer** (features + weak-supervision seeds + the human-readable "why this ledger fired" trace), never the sole signal. Per doc, per team-target:

```
1. docs = team-tagged conversation_documents (relevance-filtered), window W, audience_bucket known.
2. TARGET-STANCE classify toward the program, per ledger (encoder/Qwen3 zero-shot);
   features += lexicon hits (§2) + directionality (§3) + sarcasm_score.
3. Aggregate to a RATE per ledger (hits/mentions) vs the program's rolling baseline + cohort prior
   (empirical-Bayes shrinkage — cold-start safe).
4. FIRE only above the noise floor AND representativeness met (>= MIN_DOCS from >= MIN_SOURCES).
5. confidence = model agreement x source diversity x (1 - sarcasm risk).
6. Write team_ledger_scores(program_slug, week, ledger, score, direction, confidence,
   evidence_doc_ids, top_lexical_trace).
```

Output feeds the resolver ([[51-team-narrative-engine]] §3) and the confidence meter ([[33-confidence-signaling]]). The `backometer_weekly` belief score is the *aggregate* mood; these ledgers are the *decomposed* registers beneath it.

---

## 2. The lexicons (grounded; corpus doc-frequencies in parentheses)

> Counts are corpus-wide doc-frequency; directional/contextual gating (§3) refines them. Curate to word-boundary + lemma + team-target proximity at build time.

### 2.1 The Standard Ledger — *worthiness vs birthright* (direction: US, inward)
Core: `deserve`(2484) · `elite`(1411) · `standard`(690) · `identity`(374) · `rebuild`(360) · `blue blood`(109) · `drought`(69) · `sleeping giant`(12).
Variants/phrases: `living up to`, `who we are`, `same old`, `back to`, `down year`, `our standard`, `championship or bust`, `should be`, `embarrassing`.
**Structured anchor:** the Standard-Gap (record/rankings vs `program_tier` + historical peak — [[52-cfb-team-content-model]] §2). The keystone ledger.

### 2.2 The Grievance Ledger — *disrespect as fuel* (direction: US vs the nation)
Core: `committee`(496) · `snub`(130) · `disrespect`(127) · `overrated`→them(78) · `left behind`(55) · `robbed`(39).
Variants: `no respect`, `nobody believes`, `slept on`, `count us out`, `haven't played anyone`, `bulletin board`, `screwed`, `biased`.
Villain-tag: `committee`, `espn`, `media`, `pollsters`, `the narrative`.
**Realignment-grievance** (`left behind`, `realignment`(665), `conference`(4992)) is a live 2026 sub-register — "did we get left behind" ([[52-cfb-team-content-model]] §3.2).

### 2.3 The Grudge Ledger — *rooting against > for* (direction: THEM / rival audience)
Core: `rival`(2370) · `hate`(2154) · `rivalry`(696) · `cope`(184) · `fraud`(92) · `choke`(56) · `rent free`(17).
Variants: `seething`, `clown`, `bust`, `owned`, `down bad`, `L`, `gets exposed`, `cooked`(132).
**Direction is everything:** `overrated` is Standard/Grievance when local fans defend "us," Grudge when rivals mock "them" (§3). Realignment **killed/scrambled rivalries** are a Grudge wound the card surfaces honestly.

### 2.4 The Hope Ledger — *the offseason Hope Economy* (the dominant offseason register)
Core: `recruiting`(4286) · `transfer`(4813) · `portal`(2907) · `nil`(2787) · `pay`(4517) · `collective`(274) · `culture`(982).
Variants: `next year`, `wait till`, `reload`, `class`, `commit`, `flip`, `war chest`, `pay to win`, `returning production`, `spring`.
**The rev-share / institution sub-register** (`pay`+`nil`+`collective`+`buyout`) = the 2026 "Shadow-GM audit": *are they willing to pay to win.* Pairs with the institution character ([[52-cfb-team-content-model]] §3.2d).

### 2.5 The Coach signal — *the protagonist* (direction: US about the regime)
Core (gated): `fire`(noisy — 1304 raw, mostly "fired up"/"firepower"; require `fire him/coach/[name]` + word boundary → 22 for `fire him`) · `hot seat`(99) · `buyout`(134) · `extension`(233).
Variants: `should be fired`, `on the hot seat`, `program killer`, `right hire`, `honeymoon`, `lame duck`, `names to watch`, `affordable`, `donors`.
**This signal is NEVER a standalone detector** — it feeds `coach_pressure_weekly` only through the three gates ([[53-program-succession-coaching-carousel]] §4): the Stability Window, the Performance Anchor, and the Economic Signal. The tribe alone can never seat a coach.

---

## 3. Directionality + the Tribal Lens (the polysemy fix)

Several terms cross ledgers; **`audience_bucket` (home/rival) + first/third person** disambiguate:

| Term | home + "we/us" | rival + "they/he" |
|---|---|---|
| overrated / fraud | (rare, self-doubt → Standard) | Grudge |
| deserve | Standard / Grievance (we deserve better) | Judgment (do they deserve it?) |
| cooked / it's over | Standard (self-doom, a Reactive Surge) | Grudge (rival gloat) |

No direction signal → assign to the Standard ledger (the neutral "are they good / worthy" argument).

### 3.1 The Home-Anchor Rule (the Rival lens honesty firewall)

The Rival lens ([[50-team-story-card]] §5; [[52-cfb-team-content-model]] §4) is schadenfreude-as-a-feature, kept honest by a precise bright line (Gemini stress-test, 2026-06-11):

> **The Rival lens may amplify a narrative ONLY if it is simultaneously a source of high anxiety in the HOME discourse and high mockery in the RIVAL discourse. It is a *reframed truth*, never a *new claim* — it may introduce no claim the Home lens lacks.**

- **Fact-Anchor exception (the denial leak):** objective stats (record, rankings, turnovers) are public domain — the Rival lens may use them even when the home fanbase is in collective denial (0-5, "everything's fine").
- **PASS:** home fans debate whether the 5★ QB is a bust → Rival: "the most expensive backup in the league." · home fans post the buyout table → Rival: "a $40M parachute for 7-5." · home fans complain about the O-line → Rival: "zero havoc, zero heart."
- **BLOCK:** an unverified medical/legal rumor (do-not-amplify floor) · a coach's divorce / any non-football personal attack · "frauds" said about a 10-0 team while home fans are euphoric (no home anchor → noise, not a confession).
- **The defamation line:** never "the coach should be fired" — and not "consensus" for a 15% signal; only "persistent calls for a change," sized and dated ([[53-program-succession-coaching-carousel]] §5).

### 3.2 The Sensitive-Topic Override (the anxiety-laundering firewall)

The Home-Anchor Rule has a leak the review found: a do-not-amplify topic (a coach's legal/medical/family matter) creates a real *mood shift* in the home discourse, and the Rival lens could then launder the blocked topic by reframing the **mood shift** it caused ("the program is drifting under a distracted leader"). The fix:

> **If the underlying cause of a belief-delta (a `backometer` swing, a ledger spike) is adjacent to a protected category — criminal/legal/medical/family/identity — the RIVAL lens is hard-blocked from reframing that delta at all, even though the Home/National lenses may report general "discontent."** The override traces the *cause* of the mood, not just the surface claim: a blocked topic cannot re-enter through the side door of "the vibes it created."

This sits on top of the do-not-amplify floor ([[51-team-narrative-engine]] §1) and the institution Financial-Anchor gate ([[52-cfb-team-content-model]] §3.2) as the third honesty firewall.

---

## 4. Thresholds (start here, tune against labels)

| Param | Default | Why |
|---|---|---|
| `MIN_DOCS` | 8 distinct team-tagged docs in window | representativeness (teams have more volume than players) |
| `MIN_SOURCES` | 2 independent origins; **≥2 distinct platforms for any HOT SEAT / revolt / "consensus" claim** | one platform's brigade ≠ a narrative (review fix — 8 docs from 2 accounts on one board is not consensus) |
| `FIRE_THRESHOLD` | rate > program 75th pct **or** z > 1.0 | above the program's own noise |
| `LEAD_THRESHOLD` | z > 2.0 (or a hard structured event) | strong enough to lead the card |
| `HOT_SEAT window` | ≥15% of program mentions, 14-day rolling | the Stability Window ([[53-program-succession-coaching-carousel]] §4) |
| `sarcasm guard` | down-weight when `sarcasm_score` high | CFB discourse *is* sarcasm; surface in confidence, don't strip |

Programs below `MIN_DOCS` get **no ledger** → the Quiet State / standings-led card ([[57-team-dependency-degradation-matrix]]), distinguishing "quiet" from "no data."

---

## 5. Structured pairing (ledgers aren't discourse-only)

Each ledger fuses discourse with a structured anchor so it fires even when chatter is thin and grounds the claim:

| Ledger | Structured anchor |
|---|---|
| Standard | record/rankings vs `program_tier` + historical peak (the Standard-Gap) |
| Grievance | ranking position vs SP+/résumé (the measurable Respect Gap); realignment status |
| Grudge | `rivalry_pairs` / `rivalry_obsession_weekly` results + margins + rival-audience sentiment |
| Hope | `recruiting_footprint`, `top_commits`, `transfer_position_snapshots`, NIL-collective signal |
| Coach | `coach_pressure_weekly` Performance Anchor (wins vs expected, SP+ delta) |

The structured anchor is **fact**; the lexicon hit is **observed conversation**, always attributed ([[51-team-narrative-engine]] §1).

---

## 6. Honest limits

- Lexicons need iteration against a small labeled set (the team gold benchmark) — these are v1 seeds.
- `fire`, `pay`, `elite`, `program` are **noisy** — require word-boundary + team-target proximity + (for `fire`) the coach-target check; never count corpus-wide.
- Sarcasm/irony: do NOT strip it — handle it the 2026 way (context model + `sarcasm_score` as a feature + surface residual uncertainty in the confidence meter).
- Slang drifts ("cooked," "so back," "rent free") — schedule a periodic keyness re-mine from the live corpus.
- Same-name / shared-mascot programs need entity resolution before counting (the team tagger handles this).

## 7. Provenance

Lexicons grounded in real corpus doc-frequencies (165,507 non-empty docs, queried 2026-06-11 against `conversation_documents.body_text`). Method validated against 2026 best practice (hybrid transformer+lexicon, target-based stance, zero-shot > few-shot, topic-guided sarcasm handling — [[47-fan-ledger-detectors]] §7). The Home-Anchor Rule + the hot-seat gates are from the Gemini honesty stress-test (2026-06-11). Reuses CardiffNLP encoders + Qwen3 ABSA + `sarcasm_score` + `audience_bucket`. Detection design from [[51-team-narrative-engine]] §1/§3/§10 + [[52-cfb-team-content-model]] §3; coach gates in [[53-program-succession-coaching-carousel]] §4.
