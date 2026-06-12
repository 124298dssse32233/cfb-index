# 43 — CFB-Native Content Model ("The Ledgers, the Ghosts, the Clock")

_Status: CONTENT SPEC (v1). Created 2026-06-11 from a multi-AI brainstorm (Codex + Gemini + Claude) cross-referenced against the real discourse corpus. This is the DOMAIN layer — what to actually detect, track, and say about a college-football player — consumed by the engine ([[42-player-narrative-engine]]) and rendered by the card ([[41-player-story-card]])._

---

## 0. Thesis — why CFB needs its own content model

A pro athlete is evaluated in the present tense: is he good, right now? **A college-football player never is.** He is always measured against three things a stat line can't hold:

- **the ghost before him** — the legend whose shoes he's filling,
- **the kid behind him** — the blue-chip recruit circling his job,
- **the season ahead** — because the offseason is forever looking forward.

And fans don't consume him as *performance* — they consume him as **moral and tribal drama**, scored across a set of ledgers (hope, grievance, belonging, judgment, grudge), and they render him differently depending on which tribe is looking. *"The NFL is a game of assets; college football is a game of ghosts."*

Empirical backing (this corpus, queried 2026-06-11): the #2 most-engaged post is *"Indiana just won the national championship with a roster that ranked 72nd"* (recruiting-vs-results); top posts include *"[Player] ruined his chance to be the most rooted-for"* (moral judgment) and *"[Thamel] transfer QB is checking into…"* (portal-via-insider). Fans are not discussing yards. They are keeping ledgers.

The card's CFB-native job: **locate a player in time (ghost / kid / season) and in the fan ledgers, rendered in a chosen tribe's POV.**

---

## 1. The Fan Ledgers — the five emotional registers

The content the card compiles. Each ledger has a definition, the data that feeds it, the surface it produces, and why it's more CFB than pro.

### 1.1 The Hope Ledger — *potential, not production*
- **Is:** recruiting pedigree, portal adds, NIL, watchlists, projected ceiling. Hope is undefeated; reality is 6-6.
- **Data:** `player_recruiting_profiles` (stars/rank), `transfer_entries`, `player_nil_valuations`, `player_award_watch_2026`, discourse anticipation/volume.
- **Surface:** "the case for," ceiling projection, the **Recruit Ghost** (the player his recruiting profile promised, measured against the real one).
- **Why CFB:** the offseason (recruiting, portal) is sometimes more beloved than the games.

### 1.2 The Grievance Ledger — *disrespect as renewable fuel*
- **Is:** "nobody believes in us," poll snubs, media under-coverage, refs, "they haven't played anybody." Even blue-bloods need a chip.
- **Data:** ranking position vs résumé (rankings vs WEPA/results), coverage volume vs performance, discourse keyness for `{disrespect, snub, overrated, underrated, robbed}`, strength-of-schedule.
- **Surface:** the **Respect Gap** (performance vs recognition), the named villain (committee / network / pollster).
- **Why CFB:** recognition literally shapes rankings, playoff access, recruiting, and regional pride.

### 1.3 The Belonging Ledger — *love is orthogonal to talent*
- **Is:** tenure, tribe-fit, hometown/in-state, lifer-vs-rental. A beloved 3-star senior outranks a 5-star one-year rental.
- **Data:** `roster_entries` (years on roster), recruiting city/state vs team state, `transfer_entries` (rental vs lifer), `player_week_conversation_features` + `fanbase_mood_weekly` (affection), is-he-"one-of-us".
- **Surface:** a **Belonging** read — Lifer / Hometown Hero / Mercenary / Rental. The card can make a beloved walk-on its emotional center and a stat-leader its villain.
- **Why CFB:** allegiance is inherited and regional; the portal made loyalty scarce and therefore sacred.

### 1.4 The Judgment Ledger — *fans as a jury litigating worthiness*
- **Is:** rankings, SOS, tier-status, the eye-test-vs-résumé war. Fans argue rank like scripture; the committee is a priesthood.
- **Data:** rankings, computed SOS, advanced stats vs qualitative discourse claims (`{system QB, looks unstoppable, empty stats, stat-padder}`), tier rhetoric (`{their Super Bowl, down year}`).
- **Surface:** the **Perception Split** (what the tape says vs what the eye-test says), the open argument itself — *compile the disagreement, don't resolve it.*
- **Why CFB:** uneven schedules + subjective rankings make worthiness permanently contestable.

### 1.5 The Grudge Ledger — *rooting against > rooting for*
- **Is:** rivalry, schadenfreude, the long memory, the flip wound. Fans derive more joy from a rival's loss than their own win.
- **Data:** rivalry results/margins (rivalry seed), rival-audience sentiment (`audience_bucket=rival`), decommit/flip history, rivalry-game discourse.
- **Surface:** the **Rivalry Memory** ledger, the **Flip Wound** (a fanbase never forgets a decommit), "days since."
- **Why CFB:** rivalries encode geography, class, family, and alumni identity; one loss can define a season.

> The ledgers are not all shown at once. The dominant ledger(s) for a given player at a given moment drive the card's lead and tone (see [[42-player-narrative-engine]] §4b composition).

---

## 2. The two axes (the salience backbone)

The ledgers resolve onto two axes pro sports lacks, which drive archetype + salience:

- **Expectation axis** — promise (stars/NIL/projection = Hope) vs delivery (production/judgment). *Because CFB writes the legend before the snap.*
- **Belonging axis** — love/tenure/tribe-fit, orthogonal to talent. *Because a beloved 3-star senior beats a 5-star rental.*

Every archetype ([[42-player-narrative-engine]] §4b) is a **region** of this space: Bust-Watch = high-expectation/low-delivery; Quiet Workhorse = the Belonging corner; Transfer Saga = a *trajectory across* the space. Perturbing forces: the **portal, NIL, and coaching carousel**.

---

## 3. The Succession Engine — the ghosts and the clock

A CFB player lives in a **positional throne-line**. Three roles, all buildable from roster + recruiting data. **Full subsystem spec: [[44-succession-engine]]** (role-holder detection, portal chains, Filling-the-Shoes math, the Clock open-loop, position-specific emotion, tone guide).

**Grounding (real, this DB):** Tennessee QB room —
```
2024  Nico Iamaleava   5★ #3              ← the ghost (the legend who left)
2025  Joey Aguilar     3★ transfer, SR    ← the bridge (filling the shoes)
      Jake Merklinger  4★ #160            ← the clock (heir-apparent)
      George MacIntyre 4★ #151            ← the clock
```

- **The Predecessor (the ghost).** Mechanic: **"Filling the Shoes"** — compare the heir to the departed legend *at the same career point* (stars, hype, early production). Aguilar-for-Nico = a 3-star transfer replacing a 5-star #3. The gap is the story.
- **The Incumbent (him).** Measured against the ghost above and the threat below.
- **The Heir-Apparent (the kid behind him).** Mechanic: **"The Clock Behind Him"** — surface the blue-chip freshman waiting (Merklinger/MacIntyre). For a bridge starter it's a live open loop (*how many games until the kid takes over?*); for a star it's *who's being recruited to replace you.*
- **The Throne (lineage viz).** The chain of who held the position across years, each with stars + fate (drafted/transferred/benched). The "ghosts in the rafters," rendered. A new QB at a blue-blood is narrated *against the line he's joining.*
- **Predecessor comparison.** Mirror-match *across time within a program*: "at this point, [heir] vs [legend]." Fans do this constantly ("he's no [legend]" / "better than [legend] was as a frosh").

**Data:** `roster_entries` (position lineage by season), `player_recruiting_profiles` (incoming stars), `player_depth_chart_2026`, `transfer_entries`, `player_season_stats`.
**Constraints:** historical starter/snap data is partial — use confidence; don't assert a depth-chart battle the data can't support.
**Why singular:** exploits recruiting-rank-as-identity + the short window + the portal at once. No pro sport's fans obsess over "the next [Legend]" and "the kid coming for your job."

---

## 4. The Tribal Lens — render the disagreement

The same player is a different story to each fanbase. Mechanic: a **Home / Rival / National** POV toggle that re-renders the narrative voice from the corresponding corpus slice — hometown hero vs mercenary snake — without changing facts. This is the editorial stance ([[42-player-narrative-engine]] §1) made interactive: **compile the disagreement, don't crown a winner.**

- **Data:** `conversation_document_targets.audience_bucket` (local/rival), `affiliation_team_id`, per-slice sentiment + keyness.
- **Guardrail:** require minimum source diversity per slice; show cohort size + window so a small hostile community can't masquerade as "the narrative."
- **Why singular:** pro fandom isn't tribal enough to sustain a hate-watch lens; CFB is.

---

## 5. The Offseason Engine — the Hope Economy, always forward-looking

The offseason is not dead time; it is the Hope Economy, and the card runs in a **projective mode** with its own internal calendar that the "why-now" tracks:

```
bowl afterglow/grief → early portal → Signing Day → spring ball / QB battle
   → spring portal → summer hype / watchlists → fall camp → kickoff
```

Offseason-native mechanics:
- **Case For / Case Against next season** — compile the bull and bear takes from the corpus (offseason discourse *is* this argument).
- **The QB1 / position battle** — the depth-chart competition as the headline open loop, fed by the succession data (§3).
- **Way-too-early projection** — leaned into honestly, with the receipt that it's projection (fans *want* premature hope).
- **The Countdown** — the card tightens toward kickoff ("87 days"): hope → anticipation → "prove it." Reuse the existing team-page kickoff-countdown module.

---

## 6. The Temporal Heartbeat — narratives change week to week, ebb and flow in the offseason

The card is a living thing with two regimes:

- **In-season = a reactive ticker.** It lurches each game — one great Saturday is "Heisman buzz," one bad one is "is he the problem?" High-variance, recency-driven. The **tension, BAN, and why-now update weekly; the logline holds** (stability rule). "Story shifted this week" is the heartbeat.
- **Offseason = a slow projective build** toward kickoff, punctuated by events (a transfer, a spring-game flash). Less "what happened," more "what's coming."

Unifying mechanics:
- **The why-now IS the heartbeat** — in-season *"coming off 3 picks at Alabama"*; offseason *"QB1 still open, 87 days to kickoff."* The thing that changes most; what makes the card feel alive.
- **The changelog = the season's emotional EKG** — scrub a player's narrative across the year and *see* the ebb and flow (the Heisman spike, the crash, the redemption). The Bible's snapshots ([[42-player-narrative-engine]] §7) given CFB meaning.
- **State-dependent composition** ([[42-player-narrative-engine]] §4c) keys off the calendar phase (`resolve_week` / `calendar_pressure`): offseason-projective vs game-week-stakes vs live/post-game vs breaking.

---

## 7. CFB-native module catalog (buildable)

| Module | Ledger / engine | Primary data | LLM? |
|---|---|---|---|
| Talent-Expectation Index (recruiting vs results) | Hope / Judgment | recruiting + stats | no |
| Recruit Ghost (promised vs real) | Hope | recruiting + production | no |
| Respect Gap (performance vs recognition) | Grievance | rankings + coverage volume + stats | no |
| Poll/SOS grievance tracker | Grievance / Judgment | rankings + schedules + discourse | no |
| Perception Split (eye-test vs résumé) | Judgment | advanced stats + discourse claims | light |
| Belonging read (lifer/hometown/rental) | Belonging | roster tenure + recruiting geo + transfers | no |
| Rivalry Memory + Flip Wound | Grudge | rivalry results + decommit history + rival sentiment | no |
| Filling the Shoes / The Clock / Throne lineage | Succession | roster + recruiting + depth chart | no |
| Tribal Lens (Home/Rival/National) | rendering | audience_bucket + per-slice keyness | yes (voice) |
| Case For / Against + QB1 Battle | Offseason | depth chart + corpus bull/bear | yes (voice) |
| Kickoff Countdown | Offseason | calendar | no |
| Coachspeak Decoder (later) | Judgment | press/news + later roster reality | light |
| Arc Spark / Emotional EKG changelog | Temporal | bible snapshots + weekly mood | no |

Most are **deterministic** (no LLM) — consistent with the layered build ([[42-player-narrative-engine]] §4b): determinism owns truth, the LLM owns voice.

---

## 8. Honest data inventory

**Have:** roster lineage by season (`roster_entries`), recruiting stars/rank/geo (`player_recruiting_profiles`), transfers (`transfer_entries`), NIL (`player_nil_valuations`), awards/watchlists (`player_award_watch_2026`), WEPA/usage (`player_value_metrics`/`player_usage_season`), aura perception-vs-production (`player_aura_weekly`), weekly discourse features + audience_bucket (`player_week_conversation_features`, `conversation_document_targets`), fanbase mood (`fanbase_mood_weekly`), rivalry seed, calendar (`resolve_week`/`calendar_pressure`).

**Need / partial:** player-grain keyness (engine exists; needs player grain + baseline), computed SOS, starter/snap history (partial — confidence-gate it), "disrespect" keyness lexicon, coachspeak corpus (press conferences), the throne-lineage joins as a first-class view.

---

## 9. How the engine consumes this

- Ledgers → the **NEL** detects ledger-typed beats ([[42-player-narrative-engine]] §3).
- Two axes → feed **decomposed salience** ([[42-player-narrative-engine]] §4) and **archetype** classification (§4b).
- Succession + offseason + tribal → **modules** in the composition palette (card spec §4).
- Calendar phase → **state-dependent composition** + the **why-now** heartbeat (§4c).
- Bible snapshots → the **emotional-EKG changelog**.

## 10. Provenance

Multi-AI brainstorm (Codex feasibility · Gemini cultural/lateral · Claude pattern/paradox), 2026-06-11, cross-referenced against the live discourse corpus (Reddit-dominant, 146k docs) and real roster/recruiting data (the Tennessee QB room). Builds on [[player-narrative-engine]], [[41-player-story-card]], [[42-player-narrative-engine]].
