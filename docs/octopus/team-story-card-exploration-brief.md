# Octopus Exploration Brief — The Team Story Card

_Paste this into `/octo:brainstorm` (choose **Team** mode) to kick off, then carry the
output into `/octo:design-ui-ux` for the card surface. Created 2026-06-11. This is the
team-page analog of the player-narrative work in `docs/design-system/41–49`. It is an
EXPLORATION + SPEC brief — **plan and spec only, do not implement** (a separate task window
is editing the live site; stay read-only on code)._

---

## 0. Mission

We built a "Player Story Card" — a top-of-page module that narrates each **player** like a
character in an ongoing TV series, compiled from fan discourse + stats + canon, in a
confident-compiler voice ("Tennessee fans overwhelmingly call it a betrayal" — attributed to
the fanbase, with a confidence meter, never the site's own opinion). Specs live in
`docs/design-system/41–49`.

**Now do the same for every TEAM page.** But a team is not a player, and the whole point of
this brief is: **reason from scratch about how college-football fans actually view, feel
about, and want to engage with their TEAMS** — then design the crown that compiles that.

Produce the team equivalent of the 9 player docs. The deliverable target is §7.

---

## 1. The honest starting point: the team page already has ~60–70% of an engine

Unlike the player page, the team page is **already deep** — but the narrative is **scattered
across a dozen modules with no unifying crown.** Before designing anything new, audit and
plan to CONSOLIDATE these (all real, all in `src/cfb_rankings/team_pages/`):

**Existing narrative machinery (reuse, don't reinvent):**
- **Pulse system** — `pulse_lede.py` (the 2–3 sentence fan-voice editorial at the top of
  every team page, already Opus-tier), `pulse_themes.py` (Haiku-scan → Opus rank/write 3
  themes w/ representative quotes), `pulse_state.py` (sentiment distribution from
  `team_conversation_daily`). **This is already a primitive team story card.**
- **Seasonal sentience** — `state_resolver.py` (date + last-game outcome + tier + profile →
  `PageState` with hero_priority / copy_tone / accent_color), surfaced by `page_tone_strip.py`
  ("RIVALRY PEAK · HYPE PEAKS · THURSDAY", "AUTOPSY · LICKING WOUNDS"). The page already
  *knows what mode it's in*; it just doesn't narrate from that knowledge in one place.
- **`narrative_generator.py`** — state-of-team paragraphs in per-program voice (LLM +
  template modes), persisted to `team_season_narratives`.
- **Arc / identity** — `hero_arc_stripe.py` (13-brick CFP-era identity strip),
  `season_arc_card.py`, `trajectory_chip.py`, `program_prestige_bar.py`.
- **Aspiration / ceiling** — `aspiration_ladder.py` (3–5 rungs, tier-aware, dimmed "locked"
  dreams), `ceiling_floor.py`.
- **Fanbase mood / meme layer** — `fanbase_health.py`, `delusion_module.py`,
  `rent_free_module.py` (schadenfreude / living-in-rivals'-heads), `backometer_module.py`
  ("are we so back / is it over"), `mirror_module.py`, `voice_profile_module.py`,
  `story_words_module.py`, `lexicon_module.py`, `rituals_module.py`.
- **Rivalry / coaching / context** — `rivalry_card.py` + `rivalry_data_loader.py`,
  `coaching_era.py`, `conference_standing.py`, `schedule_strength.py`,
  `home_field_advantage.py`, `statement_wins.py`.
- **Recruiting / roster / future** — `recruiting_footprint.py`, `top_commits.py`,
  `roster_reload.py`, `offseason_pulse.py`, `nfl_draft_pipeline.py`.
- **History / canon** — `on_this_day.py`, `moment_of_year.py`, `bowl_history.py`,
  `wrapped_stack.py`, the `historical_season_*` family.
- **Per-program voice** — `profiles/*.md` (127 hand-authored, ~45–50 fields each; the voice
  lives in the profile, which is why template mode is publishable).
- **Chronicle** — `chronicle_generator.py` / `chronicle_streams.py` (the same local-LLM
  pipeline the player work reuses: writer=mistral-small3.2, planner=qwen3.6:27b, eval/LKG/
  banlist, RTX 3090 + Ollama).

**The gap is the same gap the player work found:** no single, top-of-page, compiled,
character-driven, time-aware **crown** that synthesizes all of this into "here is the state
of this program, as a story, as of today." The team page is a pile of excellent organs with
no spine. **The Team Story Card is the spine.**

---

## 2. The core question: how do CFB fans actually view TEAMS? (the seed)

This is the heart of the exploration. A player is *a character*. A team is something bigger
and stranger — and CFB makes it stranger than any pro sport. Reason hard about each of these;
they are the content model the card must compile. (These are my seed assessments — pressure-
test, extend, reorder, and ground them in the corpus.)

1. **The team is the tribe; the fan IS the team.** "We won." "We're back." A fan never says
   "we" about a *player* the way they say it about the *program*. Players are transient
   (doubly so in the portal era); the team is the eternal vessel you inherit from your family,
   your state, your school. **Belonging is not one ledger among five — for a team it is the
   substrate.** The card speaks to an in-group that experiences the team's fate as its own.

2. **The team narrative runs on FIVE timescales at once.** This week ("we lost a heartbreaker
   Saturday") · this season ("win-and-in for the conference title") · this era ("is this the
   best stretch since the dynasty / is the coach's honeymoon over") · this generation ("we
   haven't won it all since 1998") · all-time ("blue blood / sleeping giant / perennial
   almost"). The player card holds maybe two timescales; the team card must hold all five and
   pick which one *leads* based on the moment. (The `state_resolver` already gestures at this.)

3. **The head coach is usually the PROTAGONIST of the team's current story** — more than any
   player. "The Saban era." "Is he on the hot seat." "Did we hire the right guy." "Program
   builder vs. recruiter vs. retainer." The coaching hot-seat / search / buyout-math /
   honeymoon / regime-identity drama is one of the single most-discussed things in CFB and has
   **no equivalent on the player page.** The coach is a character the team card must carry.

4. **A team is defined by its ENEMIES.** Identity is constructed in opposition to 2–4 specific
   rivals (The Game, the Iron Bowl, Red River, Bedlam-RIP). "Beat [rival] and the season's a
   success" can override record. Rivalry is more central to team identity than almost anything
   — and realignment has scrambled or killed rivalries, a live 2026 wound. (`rivalry_card`,
   `rent_free_module` already exist; the card must elevate this.)

5. **Every team has a self-conceived STANDARD / ceiling, and is always measured against it.**
   Blue bloods ("are we living up to who we are") vs. risers ("are we a real program now or a
   fraud") vs. sleeping giants ("when do we finally wake up") vs. perennial almost-theres ("the
   team that can't get over the hump") vs. have-nots ("just want to be relevant / make a
   bowl"). The SAME 8-4 season is triumph for one program and a fireable offense for another.
   The card's tone must be **tier- and self-image-aware** (`aspiration_ladder` / `ceiling_floor`
   are the seeds).

6. **Conference & realignment = "where do we belong, who are our peers, did this help or screw
   us."** The 2024–2026 superconference era, the Pac-12 collapse, the expanded playoff
   reshaped every team's context and peer set. Fans obsess over "are we in the right league,"
   "did we get left behind."

7. **The season is a CAMPAIGN with a path.** Preseason expectation → the gauntlet → where we
   are now → what's still mathematically/realistically achievable. "Win and in," "control our
   own destiny," "eliminated," bowl/playoff math. This is the in-season heartbeat (parallels
   the player "why-now," but at team scale it's a *standings/path* object).

8. **The offseason is roster-construction theater, and it is relentlessly FORWARD-looking.**
   Recruiting class rank, the portal (incoming AND outgoing — "who replaces the departed
   star"), spring game, returning production, NIL-collective health, the new revenue-sharing
   reality (House settlement). The team-scale "Hope Economy." National Signing Day and portal
   windows are high holy days. (`offseason_pulse`, `recruiting_footprint`, `top_commits`,
   `roster_reload` already feed this.)

9. **The fanbase itself is a CHARACTER with a swinging mood.** Euphoria → doom → apathy →
   restlessness ("fire the coach") → faith. The "we're so back / it's over" meme cycle, the
   misery index, the barometer. The team card should have a **fanbase-mood read** as a first-
   class element — the team analog of the player's dominant-take line, but it's the tribe
   talking about *itself*, not the nation talking about a player. (`fanbase_health`,
   `backometer`, `delusion` are the seeds.)

10. **History and ghosts have WEIGHT.** Championship years, program-defining heartbreaks (The
    Kick, the Bush Push, 4th-and-26), the legends (players AND coaches), the curse/drought
    narratives, "on this day." Tradition is a live force a team page can lean on that a player
    page (one career long) cannot. (`on_this_day`, `moment_of_year`, `bowl_history`,
    `historical_season_*`.)

11. **The institution is now in the story: money, AD, boosters, NIL, facilities, "commitment
    to winning."** In the rev-share era fans openly debate whether the administration is
    *willing to pay to win* — a front-of-mind 2026 topic that barely existed five years ago.

12. **Stylistic identity / brand of football.** "We're smashmouth / Air Raid / we play
    defense / we're a track meet" — and whether the current coach is honoring or betraying the
    program's aesthetic soul. A subtle but real identity axis.

**Synthesis to land:** a team is simultaneously *the tribe* (belonging), *a franchise being
run* (coach + institution + money), *a campaign in progress* (the path), *a multi-generational
saga* (history + ceiling), and *a node in a web of enemies* (rivalry + conference). The card
must compress all of that into a glanceable, mobile-friendly crown that picks the RIGHT lead
for the moment.

---

## 3. How do fans want to ENGAGE with a team page?

1. **It's home base.** Fans visit their OWN team's page obsessively — they want "where do we
   stand right now, what's the current storyline, what's the mood, what's next / what's at
   stake." Recency bias is enormous (last game dominates the mood) but the page must still
   hold the long arc.
2. **They visit RIVAL pages to gloat and to scout.** Schadenfreude is a primary use case — the
   Tribal Lens (Home / Rival / National POV) matters *more* for teams than players. A rival
   reading your page should get the honest "what the nation/your enemies are saying" view.
3. **They want the disrespect engine.** "Nobody respects us," bulletin-board material, national
   perception vs. fanbase perception, "we're underrated / the committee screwed us." Grievance
   is huge at team scale.
4. **They oscillate "are we back / is it over"** and want the page to reflect *today's* answer
   honestly (the backometer instinct), not a stale take.
5. **Stats-only / schedule-only users must be able to skip the narrative instantly** — same as
   the player card. Compact, collapsible, mobile-first.

---

## 4. The team's new "characters" (things players don't have)

The card/engine must model these as first-class entities, none of which exist on the player
side: **(a) the head coach** (era, hot seat, honeymoon, identity, buyout/search drama);
**(b) the rivalry web** (2–4 named enemies, stakes, realignment wounds); **(c) the conference
/ realignment context** (peer set, "did we belong"); **(d) the institution** (AD, boosters,
NIL collective, rev-share willingness); **(e) the fanbase-as-collective** (mood, faith,
revolt); **(f) the recruiting class / portal haul** (the incoming cast, the team-scale future).

---

## 5. Program succession — the team analog of the player succession engine (doc 44)

The player work built a positional "throne-line" succession engine (predecessor=ghost /
incumbent / heir-apparent=the clock; "can the new starter fill the legend's shoes"). The
**team** has two parallel succession stories the card should compile:

- **The coaching carousel = the program's throne-line.** Coaches ARE the team's regime
  succession (the Saban → next-guy "filling impossible shoes" story is the team-scale version
  of replacing a legendary QB). Hot-seat → search → hire → honeymoon → judgment. `coaching_era`
  is the seed; this deserves a real spec.
- **The roster reload as annual succession.** "Who replaces the departed stars" each offseason
  — returning production, the portal haul, the recruiting class stepping up. `roster_reload` +
  `recruiting_footprint` feed this. This is the *team* "filling the shoes," every single year,
  across the whole roster rather than one position.

Connect this to the **player** succession engine: a player's "filling the legend's shoes" arc
and the team's "who's our next QB1" arc are two views of the same event — cross-link them.

---

## 6. Constraints & locked decisions (carry over from the player work — do NOT relitigate)

- **Full vision, rig-bounded.** Build the whole vision; the ONLY legitimate dial-back is when
  the single RTX 3090 + Ollama physically can't finish nightly — then tier the LLM *prose*
  (reuse the Chronicle tier policy), never cut features for product-uncertainty. (`docs/design-
  system/49`.) Note: there are ~119 FBS team pages — orders of magnitude fewer than the ~69k
  player pages, so the GPU budget is FAR less of a constraint here. The team card can likely
  afford richer per-page LLM generation than the player card.
- **Confident-compiler narrator + confidence meter.** State the dominant take with conviction,
  **attributed to the fanbase** (or to the nation, in National lens), dissent as a labeled
  minority; the confidence meter is the honesty mechanism (high → a clear story; low → "the
  fanbase is split"; below the floor → no narrative, stats/standings only). Never the site's
  own opinion. (`docs/design-system/42 §1`, `49 C1`.)
- **Compile, don't adjudicate.** The gate is REPRESENTATIVENESS (is this genuinely the
  narrative?), not validity. We surface what the room says, attributed; we don't rule on truth.
  Narrow do-not-amplify floor for unverified criminal/legal/medical allegations, pile-ons,
  doxxing.
- **Mobile + desktop, compact, collapsible**, fits a page the user will overhaul later, lets
  stats/standings-only viewers skip it instantly.
- **Static-site delivery.** No server. Tribal-Lens POVs ship as a small inline JSON payload +
  client toggle (no extra pages). Injected CSS must be RAW (no `<style>` tags — they close the
  renderer block early). Card renders inside the tree-wiping build step with `""` fallback.
- **Design system is LOCKED** — `docs/design-system/00-tokens.md`, `30-page-archetypes.md`
  (team page = **Profile/Tentpole** archetype), `31-chart-vocabulary.md` (6 allowed charts,
  forbidden list), `32-receipt-pattern.md` (citation density ≥1 marker / 200 words),
  `33-confidence-signaling.md`. The Noir sub-brand (`40-noir-subbrand.md`) is the fan-suite
  visual key. Work WITHIN these; don't invent new tokens/charts.
- **Stable keys.** Key narrative state on stable program slug (not anything that re-ingests),
  mirroring the player work's `player_external_id` linkrot fix; register new tables in the
  `verify_module_coverage.py` silent-dark guard; new compute = NON-critical pipeline steps
  (graceful degradation, never block the deploy).
- **Read-only / no-ship NOW.** Another window is editing the site. Produce specs + mockups
  only; touch no live code, no DB, no `output/site/**`.

---

## 7. What we want Octopus to produce (the deliverables)

Mirror the player doc set (`41–49`) for teams. Target new docs `docs/design-system/50–58`:

| New doc | Mirrors | Content |
|---|---|---|
| **50 — Team Story Card (UI)** | 41 | The crown's anatomy: identity/standard anchor, the lead-narrative logline, the one big number ("BAN") welded to its label, fanbase-mood read + confidence meter, the live path/stakes chip, rivalry/coach chips, collapsed→expand, motion budget, low-data fallback, Noir tokens, mobile-first. Pick which timescale LEADS per moment. |
| **51 — Team Narrative Engine** | 42 | Evidence planes (structured/discourse/canon) at team scale; structured-FIRST event detection (results, rankings, coaching moves, portal/recruiting deltas, realignment fire the beats; discourse enriches); salience across the 5 timescales; the persistent program "bible" + snapshots/changelog; content craft; reuse the Chronicle runtime. |
| **52 — CFB-Team Content Model** | 43 | The §2 truths turned into a buildable content model: the team ledgers (Belonging-as-substrate + Grievance/Judgment/Grudge/Hope), the axes, the Tribal Lens (Home/Rival/National), the offseason Hope-Economy mode, the 5-timescale temporal heartbeat, the coach/institution/rivalry/conference characters. |
| **53 — Program-Succession & Coaching-Carousel** | 44 | The coaching throne-line (hot-seat→search→hire→honeymoon→judgment) + the annual roster-reload succession; cross-link to the player succession engine. |
| **54 — Integration with the live team_pages system** | 45 | The consolidation map: how the crown ABSORBS / orchestrates pulse + state_resolver + aspiration_ladder + hero_arc + rivalry + coaching_era rather than duplicating them. What's net-new vs. reused. v0 deterministic slice. |
| **55 — Rollout & infra compat** | 46 | Pipeline insertion (non-critical Run blocks), stable keys, coverage-guard registration, CSS gotcha, concurrent-edit safety. |
| **56 — Team Fan-Ledger detectors** | 47 | Team-scale ledger detection (hybrid transformer+lexicon, 2026 best practice — reuse the CardiffNLP + Qwen3 stack), the Tribal-Lens directionality (us vs. them vs. nation), thresholds, grounded in the real corpus. |
| **57 — Dependency / degradation matrix** | 48 | Per-module dependency table + 4-rung fallback ladder + freshness budget, so a team with thin discourse still gets an honest standings-led card. |
| **58 — Build philosophy (rig-bounded)** | 49 | The team version of "full vision, dial back only for the rig" — noting the GPU budget is far looser here (~119 pages). |

**Process Octopus should run:** Team-mode multi-AI brainstorm on §2/§3 first (diverge on how
fans view teams — pull in Codex for feasibility, Gemini for ecosystem/2026 trends), then an
adversarial critique pass (find the contradictions/gaps/over-engineering BETWEEN the docs, as
the player critique did), then write the specs. Ground every claim in the live DB and the
existing modules — query, don't guess (the player work grounded lexicons in 194,967 real docs).

---

## 8. Open questions for Octopus to wrestle with (don't paper over)

1. **What LEADS the card?** A team has 5 timescales and 6 characters competing for the top
   line. What's the resolver that picks "this week's heartbreak" vs. "the coach is cooked" vs.
   "we haven't won since '98" vs. "the portal class is loaded"? (Extend `state_resolver`.)
2. **Belonging is the substrate, not a ledger — so how do the ledgers re-map for teams?** The
   player's 5 ledgers may not transpose 1:1. Re-derive the team ledger set from the corpus.
3. **Coach-as-protagonist vs. team-as-protagonist** — when the story is really about the coach
   (hot seat) vs. the program, how does the card frame it without becoming a coach page?
4. **Rivalry/Tribal Lens at team scale** — is the National lens the default, with Home/Rival
   as toggles? How do you keep the Rival lens honest (real schadenfreude) without it being
   mean-spirited or a do-not-amplify problem?
5. **The uncanny-middle risk** — smooth confident prose over a boring 6-6 mid-major with thin
   discourse. Where's the floor where the card honestly says "quiet season, here's the
   standing" instead of manufacturing a saga? (Same anti-fabrication rule as the player work.)
6. **Consolidation vs. addition** — the real danger is ADDING a 25th module instead of building
   the spine that makes the other 24 cohere. How aggressively should the crown subsume the
   pulse lede, the tone strip, the aspiration ladder?
7. **Does v0 mirror the player v0?** (deterministic crown + coaching-carousel detector, LLM
   prose on top) — or does the team page's existing pulse system change the right first slice?

---

## 9. North star

A fan opens their team's page on a Tuesday in November and the crown tells them, in their own
tribe's voice, exactly where the program stands today — the wound from Saturday, what's still
on the table, whether the coach is safe, what the rivals are saying — and a fan opens a blue
blood's page in June and gets the forward-looking offseason hope and the weight of the standard.
Same card, different moment, never formulaic, always compiled-not-invented, glanceable on a
phone. The team page stops being a pile of great modules and becomes a story with a spine.
