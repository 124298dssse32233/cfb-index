# 59 — Player Evidence Packet Contract (API-Writer Architecture)

**Status:** LOCKED (design) — 2026-06-12. Implementation pending.
**Supersedes:** the evidence-assembly portions of `42-player-narrative-engine.md` (the
`assemble_evidence` top-12/400-char path) and extends `44-succession-engine.md`.
**Owner concept:** the writer was never the bottleneck — the *packet* is.

---

## 0. Why this doc exists

We proved (Nico Iamaleava, 2026-06-12) that a frontier writer handed the **complete**
data pile writes at the ceiling, and the same writer handed a thin/truncated pile writes
a thin card. The quality of a Story Card is **bounded by the completeness and honesty of
the evidence packet**, not by the cleverness of the model.

So the system we are locking is **not a writer** — it is a **Packet Builder**: the thing
that gathers, for one player, every available fact and every relevant fan voice, tags each
with a *valence* and a *suppression rule*, and hands the result to whichever writer is on
duty (Sonnet via API for the live top-50; the local model / deterministic template for the long
tail). If the packet is provably complete and faithful, the card is correct. The
machine-checkable proof is **coverage**: `capture ÷ availability`.

This doc is the contract for that packet. A future agent should be able to build the
Packet Builder from this doc alone.

---

## 1. Principles (LOCKED — do not relax without an ADR)

1. **Compile, don't manufacture** — enforced at the *data* layer, not hoped for at the
   *writing* layer.
2. **Every fact carries a valence and a suppression rule.** A fact is data; whether it
   becomes narrative is a gated decision.
3. **"The fans aren't talking about it" is a first-class reason to stay silent.** Absence
   of discourse is evidence, not a gap to paper over.
4. **Gather everything; let the writer select.** The packet is built for a big-context
   writer. Minimal truncation, no aggressive top-K. The writer does in-context what a
   small model needed the assembler to pre-chew.
5. **Faithfulness is non-negotiable.** Every asserted claim must trace to a packet row by
   `source_id`. The factscore/grounding gate stays in force *on top of* the API writer.
6. **Coverage is the contract.** For the golden set, `capture == availability`. CI ratchets
   it: the number can only go up.
7. **NIL: reported, not modeled.** Never emit our modeled valuation. NIL *narrative*
   (holdout, portal-for-money, reported figures with attribution) is kept and protected.
8. **Season clock.** Forward-frame to the upcoming season (`_upcoming_season`); stats are
   "last season" (`_last_completed_season`). June 2026 ⇒ preview **2026**, stats from **2025**.

---

## 2. The writer model

| Cohort | Selector | Writer | When |
|---|---|---|---|
| **Live top-50** ("most talked about") | `player_aura_weekly.mention_count DESC` (latest week) **∪** importance pool (`_llm_candidate_ids`), capped **50** | **Sonnet via API (`AnthropicBackend`)** | **Automated — D-1 LOCKED (revised 2026-06-12).** A box Task-Scheduler job at each editorial beat (§11); no human session |
| Mid (T1/T2 importance, not in top-50) | importance pool | Local model (`mistral-small3.2`) | Nightly box job |
| Long tail | roster | Deterministic template | Nightly box job |

- **D-1 (locked, revised 2026-06-12):** the **live top-50** are written by **Sonnet via the
  Anthropic API** (`AnthropicBackend`), run **automatically by the box** at each beat (§11).
  Kevin opted OUT of in-session ("can't be relied on to do it in a task window") **and chose
  Sonnet, not Opus** for the writer — its confident-compiler quality is more than enough at
  ~1/5 the cost. Three things in scope:
  - **(a) Cost** — small; ~$6–12/mo (estimate in §15 D-1).
  - **(b) Key handling** — `ANTHROPIC_API_KEY` as a box env var, **never committed or echoed**.
  - **(c) Graceful degradation is MANDATORY** — API down / rate-limited / over-budget ⇒ fall
    back to local `mistral` → deterministic → LKG, **never block the deploy**, and **emit a
    loud signal on fallback** (§12) so a silent full-batch degrade can't ship green
    ([[build-failure-philosophy]]).
- The **golden set = the top-50**, all written by Sonnet — the writer cohort and the
  coverage/eval set are the same 50. The box keeps running nightly for the mid/tail (local
  `mistral` / deterministic) + the LKG safety net.
- The cohort for the API writer is the **union** of *talked-about* and *important* — so a breakout
  with no preseason pedigree (e.g. Joey Aguilar, 199 mentions, zero watch-list presence)
  still gets the frontier writer.
- The packet is **writer-agnostic**. The same packet feeds the API writer, the local model, or the
  template; only the *instruction* and the *truncation budget* differ by writer.
- Today only **79** players carry non-low-signal aura, so "top-50" is the upper ~63% of
  everyone with real discourse. The set **rotates weekly** during the season because
  `mention_count` is per-week.

---

## 3. The Fact envelope (universal)

The packet is a **structured object of typed fact-blocks**, never a pre-baked paragraph.
Every atomic fact is wrapped in this envelope:

```
Fact = {
  key:            str          # stable id, e.g. "before_after.passing_2025"
  value:          Any          # the machine value (numbers, names)
  display:        str          # short human string for the writer + the citation
  source_id:      str          # "row:player_season_stats:..." | "doc:<id>"  (citation anchor)
  source_kind:    str          # "structured" | "discourse"
  valence:        str | None   # the *direction* of the fact (see §5/§6); None = neutral
  evidence_bar:   str          # what must be true for this to become narrative
  suppress_when:  str | None   # the silence condition (machine-evaluable predicate)
  confidence:     float        # 0..1
}
```

Two rules that fall straight out of the envelope:

- **No fact is asserted as narrative unless it clears `evidence_bar`.**
- **If `suppress_when` evaluates true, the fact is dropped from the writer's "use these"
  set** (it may still appear in a "context only — do not assert" appendix so the writer
  understands the situation without claiming it).

---

## 4. The packet schema

One packet per `(player_external_id, season)`. `player_external_id` =
`player_source_ids.source_player_id WHERE source_name='cfbd'` (the linkrot-stable key).
Sections, with source table → columns, what they carry, and their gate.

### 4.1 Identity & Season Clock
- **Source:** `players`, `roster_entries`, `season_labels`.
- Carries: name, position, team, class year, `upcoming_season`, `last_completed_season`.
- Gate: always present. The season clock is a *hard* framing instruction, not a fact.

### 4.1.1 Eligibility gate — active for the UPCOMING season (LOCKED 2026-06-12)

The golden set is ranked by **last season's** discourse (`player_aura_weekly`,
`season_year = last_completed`), but every card **previews the upcoming season**. The set
must therefore be filtered to players **actually active for the upcoming season** — else a
player who blew up last year but has since left gets previewed as a returning starter.

> Found 2026-06-12 (Kevin flagged Carson Beck): **~10 of the live top-50 are gone** —
> Beck (2026 NFL draft rd3), Drew Allar, Garrett Nussmeier, et al. carry a
> `player_nfl_draft` row for the upcoming year.

**The catch-all is a roster; until it publishes, we infer.** The only signal that catches
*every* reason a player is gone (draft, graduation, flunk-out, quiet transfer, walk-on cut)
is a **2026 roster**. CFBD's ingester already exists (`ingest-cfbd-preseason --season 2026`,
`client.get_roster`), BUT **CFBD returned 0 players for 2026 as of 2026-06-12** (rosters
finalize ~August). So the gate is two-layered and time-evolving:

- **NOW (offseason, no roster) — infer from departure + positive signals:**
  - **DEPARTED** if a `player_nfl_draft` row with `draft_year >= upcoming_season` **OR** a
    `transfer_entries` row (`from_team` = their last team, in the upcoming cycle) **OR**
    eligibility exhausted. Catches the big three — drafted / transferred / graduated — i.e.
    **11 of the live top-50** (Beck, Allar, Nussmeier, Ty Simpson, Love, Mendoza, Singleton,
    Price, Kaytron Allen + 2 transfers-out: Grunkemeyer→VT, Raleek Brown→Texas).
  - **ACTIVE** if a positive upcoming-season row exists (`player_depth_chart_2026` /
    `player_award_watch_2026`) — even *with* a transfer (active on the *new* team, e.g.
    Justice Haynes → Georgia Tech) — **OR** an underclassman (class 1–3) with no departure
    signal (presumed returning).
  - **UNCERTAIN** = a senior (class 4) with no departure signal and no positive row (~5 of
    the top-50: Trinidad Chambliss, Ashton Daniels, Byrum Brown, Jamal Haynes, Jamarion
    Miller). Keep, but do NOT assert "returning starter" with confidence; resolve at roster.
- **AUGUST+ (roster published) — roster presence is GROUND TRUTH.** Schedule
  `ingest-cfbd-preseason --season 2026` to retry through the offseason; once it returns data,
  **absence-from-roster overrides the inferred signals** and cards self-correct on the next
  cadence beat — catching the quiet exits the signals miss.
- **A departed player is EXCLUDED from the forward top-50** — the next-most-talked-about
  *active* player takes the slot. The selector (§2/§8) applies this filter.
- **The departure is still a story:** the departed player is **recast as the GHOST
  (predecessor)** in their successor's succession block (§5). Beck gets no 2026 preview card;
  Beck-the-ghost anchors Miami's *new* 2026-QB1 succession read.
- **Coverage note:** the §14.1 baseline (0.50) was computed on the unfiltered 2025-discourse
  top-50; it will be **re-baselined on the active-2026 set** when the selector gains this gate
  (a selector change bundled with §14.3). The number may shift — that's expected and correct.

### 4.2 Discourse stream — the firehose
- **Source:** `conversation_document_targets cdt` ⋈ `conversation_documents cd`
  on `conversation_document_id`, filtered `is_deleted=0 AND is_removed=0`,
  `relevance_ml_score >= RELEVANCE_GATE`, `toxicity_score <= TOXICITY_CEILING`.
- Columns: `title_text`, `body_text` (**untruncated for the API writer** — see §9 budget),
  `audience_bucket` (home/rival/national/beat), `sentiment_label`, `sarcasm_score`,
  `source_name`, `source_author_name`, `source_url`, `like_count`, `relevance_ml_score`.
- Shaping:
  - **Tribe-tagged, not top-K.** Carry *all* docs that clear the gates, grouped by
    `audience_bucket`, deduped by independent origin (author/source) so N reposts of one
    thread count once (representativeness of the meta-claim).
  - **MMR de-dup within a tribe** so six near-identical takes don't crowd out the lone
    NFL-draft or upset doc — but for the API writer this is a *soft* ordering, not a hard cull.
  - **C7 phrase guard** drops docs that read as unverified criminal/medical claims —
    **but legal/betting/suspension PUBLIC news stays** (Sorsby rule; see §7/§9).
  - **NIL/money/holdout docs are flagged high-salience and never truncated** (§7).
- Valence: each doc's `sentiment_label` + `audience_bucket` *is* its valence.
- Gate: a take only becomes the *dominant* take if it clears representativeness
  (≥ N independent origins) — a single loud doc is a minority take, never the headline.

### 4.3 Production & Before/After
- **Source:** `player_season_stats` (raw lines: `category`, `stat_type`, `stat_value_num`,
  aggregated `MAX(stat_value_num)` per player/team/season — never SUM the cumulative rows),
  `player_value_metrics` (`metric_name` e.g. `wepa_passing`, `metric_value`, `plays`).
- Carries: **current** season line **and** the **prior** season line when the player
  changed team/role (the transfer/bench delta). Example: 2024 Tennessee 2,616/19/5 →
  2025 UCLA 1,928/13/7.
- Valence: `improved | declined | steady` from the delta.
- Gate: the before/after is only a *story* with context (injury / scheme / level-of-comp).
  A bare decline is shipped as a fact with `valence=declined`; the writer decides whether
  the discourse supports framing it as a knock.

### 4.4 Recruiting profile
- **Source:** `player_recruiting_profiles` — `stars`, `rating`, `national_rank`,
  `committed_team`, `city`, `state_province`, `position`, `season_year`.
- Carries: stars, national rank, **hometown** (the "comes home" angle — Downey, CA), the
  original commit (the "left X for Y" arc).
- Gate: always available; valence neutral.

### 4.5 Honors
- **Source:** `player_honors` — `honor_name`, `honor_scope`, `selector`, `honor_team`,
  `placement`, `consensus_flag`, `unanimous_flag`, `season_year`, `conference_name`.
- Carries: current + prior honors (e.g. All-Big Ten 2025).
- Valence: positive, **scaled by context** — consensus/unanimous All-American ≫ a
  third-team all-conference nod. The packet carries the scope so the writer doesn't
  overweight a thin honor.
- Gate: an honor is assertable; its *weight* is governed by scope/selector.

### 4.6 Award watch (upcoming season)
- **Source:** `player_award_watch_2026` — `award_slug`, `list_type`, `position_rank`,
  `priority`, `as_of`. Slug→name map: `heisman`=Heisman, `davey_obrien`=Davey O'Brien (QB),
  `maxwell`=Maxwell, `manning`=Manning, `biletnikoff`=Biletnikoff (WR), `butkus`=Butkus (LB),
  `bednarik`=Bednarik, `doak_walker`=Doak Walker (RB), `lombardi`=Lombardi,
  `lou_groza`=Lou Groza (K), `mackey`=Mackey (TE), `hornung`=Paul Hornung.
- Carries: the upcoming-season watch lines (Heisman #13, Davey O'Brien #12).
- Valence: positive (forward-looking credibility — complicates an "all hype" take).
- Gate: always assertable when present; it *is* a forward signal, season-clock safe.

### 4.7 Depth chart / starter status (upcoming)
- **Source:** `player_depth_chart_2026` — `position_group`, `slot_rank`,
  `starter_status`, `confidence`.
- Carries: confirmed/projected starter status for the upcoming season.
- Gate: `confidence` text gates assertion ('confirmed' > 'projected'); feeds §5 entrenchment.

### 4.8 Transfer / portal history
- **Source:** `transfer_entries` — `from_team_name`, `to_team_name`, `transfer_date`,
  `from_team_id`, `to_team_id`; `player_nfl_draft` for the drafted fate.
- Carries: the portal arc (Tennessee → UCLA, 2025), the musical-chairs context.
- Gate: factual; the *why* (NIL) comes from discourse, never our valuation (§7).

### 4.9 Aura — the hype-vs-tape signal
- **Source:** `player_aura_weekly` — `mention_count`, `perception_pctl`, `production_pctl`,
  `aura_score`, `aura_tax`, `verdict`, `is_low_signal`.
- Carries: the BAN (perception-above-tape gap), the "most talked about" rank.
- Valence: the `verdict` (`aura_tax` / `matched`) IS the valence.
- Gate: the BAN is asserted only when the gap is real **and** the buzz exists
  (`mention_count` above floor). A big gap with tiny buzz is not a story.

### 4.10 Succession block — REDESIGNED (see §5)
- **Source:** `player_succession` (+ live recompute per §5).
- Carries: predecessor (production-banded), incumbent entrenchment, heir threat
  (relative + discourse-gated), `suggested_frame`, `suppress_when`.

### 4.11 NIL — narrative only (see §7)
- **Source:** discourse docs only (§4.2) + `transfer_entries` for the portal event.
- **Excluded:** `player_nil_valuations` (the modeled number) — never in the packet.

### 4.12 Fired ledger leads / takes
- **Source:** `fetch_ledger_lead` / `player_ledger_scores`, `evidence_doc_ids_json`.
- Carries: the dominant-take candidate + its pinned evidence docs (so the prose anchors
  to the same docs the take fired on).
- Gate: representativeness (§4.2).

---

## 5. Succession block — the locked redesign

Fixes the three cracks identified 2026-06-12:

**(A) Threat is relative, and the discourse is the truth test.**
Replace heir-absolute `clock_score` with:
```
threat = heir_strength ÷ incumbent_entrenchment
incumbent_entrenchment = f(production_pctl, experience/class, returning_starter_status)
```
Assert a clock **only if** `threat ≥ floor` **OR** the player's own discourse contains
QB-competition language ("battle", "QB1 race", "pushing for the job"). An entrenched,
productive, returning starter with a quiet backup ⇒ **no clock, no heir named.**

**(B) Predecessor quality is production-based, not recruiting-based.**
Add `predecessor_band ∈ {elite, solid, poor}` from production percentile + fate
(`drafted`=elite, `benched`/bottom-third=poor) + honors — **independent of recruiting
stars**. This separates "live up to a legend" (reverence) from "escape a guy who
underwhelmed" (relief/upgrade). The current `star_delta`-only read is retired.

**(C) Valence must reach the writer.**
`_structured_fact_strings` must stop flattening succession to bare
`"inherited the QB job from X"`. The packet carries the structured block:

```
succession = {
  predecessor: {name, line:"2,616 yds / 19 TD (2025)", band: solid|elite|poor, fate},
  incumbent_entrenchment: high|medium|low  (+ the "why")
  heir: {name, stars, class, threat: real|nominal|none, discourse_competition: bool}
  suggested_frame: one of the taxonomy below
  suppress_when: "threat in (none, nominal) AND NOT discourse_competition"
  confidence: 0..1
}
```

**Frame taxonomy** (`suggested_frame`):
`live-up-to-a-legend` · `escape-a-bust` · `upgrade` · `open-competition` ·
`entrenched-no-clock` · `first-time-starter` · `continuity`.

**D-2 — threshold judgment (LOCKED, "what CFB fans actually want").** The honest CFB read:
*nobody debates a backup when the starter is balling, and everybody debates a real QB
battle.* So **discourse is the primary gate, data is the qualifier** — not the reverse.

- `incumbent_entrenchment`:
  - **HIGH** — returning starter with `production_pctl ≥ 70` (top third) **or** a
    `confirmed` 2026 starter with real prior usage.
  - **MEDIUM** — a starter, but new/unproven or mid production (`30 ≤ pctl < 70`).
  - **LOW** — unproven / true-or-redshirt freshman / genuinely open job (`pctl < 30` or none).
- **Assert a clock only when BOTH:**
  1. the heir is a *real* talent — `stars ≥ 4` **or** a notable transfer/Top-class recruit
     (an unranked walk-on never starts a clock), **and**
  2. entrenchment is **not HIGH**, **OR** the player's own discourse carries competition
     language (`discourse_competition = true`) regardless of entrenchment.
- **Suppress the clock** (the default for most stars) when entrenchment is HIGH and there is
  no competition chatter. *No one in Athens asks when the backup takes Carson Beck's job.*
- These constants (70 / 30, `stars ≥ 4`) are seeded from the live percentile distribution
  and may be retuned per §15 D-2, but the **discourse-first ordering is locked.**

### 5.1 Implementation notes (grounded against live data 2026-06-12)

Three findings from probing the live `player_succession` table + discourse — these are
**locked build constraints**, not suggestions:

- **Predecessor band comes from the ghost's FINAL-SEASON stats/WEPA, NOT aura.** A departed
  predecessor (transferred/graduated/drafted) has no current `player_aura_weekly` row, so
  aura's `production_pctl` is null for most ghosts. Grade the predecessor from their last
  `player_season_stats` line + `player_value_metrics` (wepa) + fate. (Confirmed: a query for
  reverence-bug cases via aura returned **empty** purely because of this join sparsity — the
  bug is real but aura is the wrong source to detect it.)
- **The discourse-competition gate must NOT be a keyword count.** A naive scan
  ("battle/competition/QB1/depth chart/backup") gave **41 false hits for Carson Beck** from
  generic spring-ball / national-championship-recap boilerplate, and the player-mention
  tagger has cross-team false positives (Ty Simpson's tagged docs pulled Miami content;
  Keelon Russell's pulled Georgia). Use instead:
  - **heir buzz** — the heir's own `mention_count` / discourse-doc count (a real threat
    generates real conversation), and
  - **incumbent↔heir co-mention** — docs that name BOTH, relevance-gated to the incumbent
    (fans writing about the two names together = a genuine QB-room story).
  Keyword terms may *seed* the co-mention scan but never gate it alone.
- **Concrete regression fixtures (real rows today):**
  - **Carson Beck** (prod_pctl 91.9, returning starter) — engine fires clock for heir Luke
    Nickel (16 docs vs Beck's 141). **Expected after fix: SUPPRESS → `entrenched-no-clock`.**
  - **Trinidad Chambliss** (prod_pctl 93.1) — heir Shawqi Itraish (3★, weak buzz).
    **Expected: SUPPRESS.**
  - **Ty Simpson** (prod_pctl 91.9) — heir Keelon Russell (5★, 46 docs, hyped). **Expected:
    clock fires ONLY if real incumbent↔heir co-mention competition exists** — the test that
    the gate isn't a blanket "good starters never have a clock" rule.

The writer gets the facts, the valence, **and explicit permission to drop the whole
block** when `suppress_when` is true. A real competition → it writes the clock; a phantom
one → silence.

---

## 6. Suppression catalog

| Fact | Evidence bar (assert only if…) | Silence when |
|---|---|---|
| Heir / clock | threat ≥ floor **or** competition chatter in discourse | entrenched starter + quiet backup |
| Predecessor "ghost" | the delta is *interesting* (legend to follow **or** bust to escape) | bland same-caliber handoff, no discourse interest |
| BAN (perception-above-tape) | gap is real **and** `mention_count` above floor | big gap, tiny buzz |
| Honor | present | (never silenced, but weight scaled by scope) |
| Before/after decline | present | (shipped as fact; writer gates the *knock* framing on discourse) |
| Dominant take | ≥ N independent origins | single loud doc → demote to minority take |
| NIL figure | the number is **reported by a source doc** (attributed) | our modeled valuation — always |

---

## 7. NIL rule (LOCKED)

- **DROP** `player_nil_valuations` from the packet entirely. The modeled estimate never
  reaches a card.
- **KEEP** NIL as narrative. The NIL story comes from **discourse** (the holdout, the
  portal-for-money snark, "the Joey Aguilar situation") and **structured portal events**.
- **Reported dollar figures are quotable *with attribution*** ("reportedly sought a raise
  to ~$X, per a March report") because they are facts *about the discourse*, anchored to a
  `doc:` source_id. **Modeled figures are never emitted.**
- The Packet Builder flags NIL/money/holdout discourse docs as **high-salience,
  never-truncate** so reported figures survive into the writer's view.

---

## 8. Coverage contract & the ratchet

- **availability(player)** = the set of §4 sources that *exist* in the DB for this player.
- **capture(player)** = the subset that actually made it into the packet.
- **coverage = |capture| ÷ |availability|.** Deterministic, zero-LLM.
- **CI ratchet:** for the live top-50, coverage can only go **up** between builds. A drop
  fails the build. This is the regression guard and the machine-checkable definition of
  "given all our data."
- The golden set IS the live top-50 by `mention_count` (rotates weekly) — so the eval
  needs no hand-authored answer key (see §10).

---

## 9. The writer instruction (prompt contract)

What the API writer (and the local model, abridged) is told, on top of the packet:

1. **Voice:** confident compiler — state the fanbase's take with conviction *and
   attribution*; dissent as a labeled minority; a confidence meter.
2. **Season clock:** forward-frame to `upcoming_season`; stats are "last season".
3. **Compile-don't-adjudicate:** the gate is *representativeness*, not truth. Surface what
   the room says; never render the site's verdict on a person.
4. **Honor suppression:** if a fact's `suppress_when` is true, do **not** assert it.
   Silence on a phantom backup is correct, not a coverage miss.
5. **Faithfulness:** every claim must trace to a packet `source_id`. No invented names,
   numbers, or events. (Hard gate downstream; instruction upstream.)
6. **C7 floor (Sorsby rule):** legal/betting/suspension **public news is KEPT** and
   may be compiled with attribution. Only *unverified* criminal/medical claims are barred.
7. **Output:** structured five fields — `logline` / `dominant_take` (+ `minority_take`) /
   `body` / `kicker`. Banlist phrases enforced.
8. **Truncation budget:** API writer = full discourse bodies, pool-wide ~3k-token budget,
   salient-sentence extraction over raw head-truncation. Local model = the legacy
   tighter pack.

---

## 10. The eval contract

Three layers, all reference-free so they scale to a rotating top-50:

1. **Coverage ratchet** (§8) — deterministic, every build, CI-gated.
2. **Missed-Gold critic** — an LLM judge sees the finished card **plus the full packet**
   and answers one question: *"what is the single best fact or quote in this packet the
   card left out?"* Whatever it names becomes the next ticket. **Respects suppression:** an
   omission whose `suppress_when` was true is **not** counted as missed gold.
3. **Faithfulness gate** — every claim in the card maps to a packet `source_id`; unmapped
   claims fail. (Existing factscore gate, retained.)

---

## 11. Cadence integration

- **Evidence fingerprint:** the Packet Builder emits `hash(selected doc_ids + structured
  fact keys)`. The regen trigger fires when **either** the deterministic spine **or** the
  fingerprint moves. This is the keystone — it makes in-season freshness automatic (new
  discourse forces a rewrite even when BAN/chips are unchanged) while unchanged players
  still skip.

**In-season editorial beats — D-3 LOCKED.** The full **live top-50** is rewritten by the
**automated Sonnet API job** at each beat (the fingerprint means most are no-ops, so cost
stays tiny):

| Beat | Local time | Editorial frame |
|---|---|---|
| **Sunday** | ~02:00 (after Saturday discourse settles) | the **Saturday recap** — who rose/fell, the new takes |
| **Monday** | morning | **week-ahead** — looking forward to the coming games |
| **Thu/Fri** | pre-game | **pre-game** — sharpen the matchup-relevant cards |

The 02:00 Sunday job runs **fully autonomously** — the overnight **collect** lands the
settled Saturday discourse, then the API beat job writes from complete data. No human in the
loop (the reason D-1 moved to the API path).

| | Offseason (now → late Aug) | In-season (Sep–Dec) |
|---|---|---|
| Cadence | weekly API beat, top-50 | **3 API beats/wk** (Sun / Mon / Thu-Fri), top-50 each |
| Between beats | structured-fact refresh (box) | box refreshes data + tail; top-50 await the next beat |
| Event | portal / depth-chart / watch-list lands | injury / suspension / benching / Heisman moment |
| Evidence mix | lean **structured** (discourse thin) | lean **discourse** (game reaction firehose) |

Plugs into the existing box jobs: `CFBIndex-FanintelCollect` lands discourse (overnight,
incl. the post-Saturday settle) → the nightly box `compute-story-cards` keeps the
local/deterministic tail fresh → **a new Task-Scheduler beat job calls the Sonnet API for
the top-50** at each beat and deploys via the normal full snapshot. The fingerprint tells
the job which of the 50 actually changed, so a beat usually rewrites only the handful that
moved — keeping the API bill at single-digit dollars/mo (§15 D-1). New infra = the beat
Task-Scheduler entries + the `AnthropicBackend`; everything else is existing.

---

## 12. Failure & degradation

- The Packet Builder **never raises** into the render path. Missing source → empty section
  + `availability` reflects it (so coverage doesn't punish a player for data we don't have).
- **Thin packet → deterministic fallback.** If the packet lacks the substance for a real
  narrative (offseason long-tail), the card falls back to the deterministic spine. **The
  writer is never asked to write from nothing** — that's how hallucination happens.
- **API fallback ladder (D-1 API path).** Anthropic API down / rate-limited / over a
  configured monthly budget cap ⇒ fall back to local `mistral` → deterministic → LKG. The
  deploy is **never** blocked.
- **Loud-on-fallback (anti-silent-degrade).** Per [[build-failure-philosophy]], silent
  graceful-degrade is the real hazard — a beat where the API failed for all 50 must NOT ship
  green and quiet. The beat job records `prose_source` per card and **fails loudly (issue /
  alert) if the API-written share of the top-50 falls below a floor** (e.g. < 60%) for a
  non-thin-packet reason. Degrading one card is fine; degrading the whole marquee silently is not.
- LKG: the last-known-good card survives a pipeline failure (existing mechanism).

---

## 13. Data-source map (table → packet field)

| Table | Key columns | Packet section |
|---|---|---|
| `player_source_ids` | `source_player_id` (cfbd) | identity key |
| `conversation_documents` ⋈ `_targets` | `body_text`, `audience_bucket`, `sentiment_label`, `source_*`, `like_count`, `relevance_ml_score` | §4.2 discourse |
| `player_season_stats` | `category`, `stat_type`, `MAX(stat_value_num)`, `season_year` | §4.3 before/after |
| `player_value_metrics` | `metric_name`, `metric_value`, `plays` | §4.3 production |
| `player_recruiting_profiles` | `stars`, `national_rank`, `city`, `state_province`, `committed_team` | §4.4 recruiting |
| `player_honors` | `honor_name`, `honor_scope`, `selector`, `placement`, `consensus_flag` | §4.5 honors |
| `player_award_watch_2026` | `award_slug`, `list_type`, `position_rank` | §4.6 watch |
| `player_depth_chart_2026` | `starter_status`, `confidence`, `slot_rank` | §4.7 + §5 entrenchment |
| `transfer_entries` | `from_team_name`, `to_team_name`, `transfer_date`, `season_year` | §4.8 + §7 NIL arc + §4.1.1 departure |
| `player_nfl_draft` | `draft_year`, `round`, `overall` | §4.8 fate + §4.1.1 departure |
| `roster_entries` | `season_year`, `team_id`, `class_year`, `is_returning_player` | §4.1.1 eligibility (2026 = ground truth when published) |
| `player_aura_weekly` | `mention_count`, `perception_pctl`, `production_pctl`, `verdict` | §4.9 BAN + cohort |
| `player_succession` | predecessor/heir/`shoes_read` + live recompute | §5 |
| `player_ledger_scores` | `evidence_doc_ids_json` | §4.12 takes |
| ~~`player_nil_valuations`~~ | — | **EXCLUDED (§7)** |

---

## 14. Build order (implementation sequence — not yet started)

1. **Coverage ratchet** on the live top-50 (deterministic) → baseline today's number. ✅ done.
2. **Eligibility gate** (§4.1.1) — the active-for-2026 classifier (departure signals now,
   roster ground-truth when CFBD publishes) + a scheduled `ingest-cfbd-preseason --season 2026`
   retry. Feeds the selector (drop departed from top-50) AND succession roll-forward.
3. **`succession.py` redesign** — `predecessor_band` (final-season stats, §5.1), relative
   threat, discourse-competition gate (heir-buzz + co-mention), **season roll-forward** (last
   year's departed incumbent → this year's ghost), valence-to-writer (§5). Unit-test the
   false-clock (Beck/Chambliss suppress, Simpson gated) cases.
4. **Packet Builder** — `build_packet(db, player_external_id, season) -> Packet` implementing
   §3/§4 with the Fact envelope + `suppress_when` evaluation. Emits the evidence fingerprint
   (§11). Re-baseline coverage on the active-2026 set.
5. **NIL exclusion + narrative protection** (§7).
6. **Writer instruction** update (§9) + **`AnthropicBackend`** (D-1: **Sonnet** via API,
   automated, top-50). `ANTHROPIC_API_KEY` already present on the box; monthly budget cap;
   fallback ladder API→`mistral`→deterministic→LKG (§12); `prose_source` recorded per card.
7. **Missed-Gold critic + faithfulness gate** wired to respect suppression (§10).
8. **Cadence wiring** — fingerprint trigger + `--select hot-list|sweep` modes (§11).

Gate each step; run nothing against prod until §14.1–§14.4 pass on the golden set.

---

## 15. Decisions (RESOLVED 2026-06-12)

- **D-1 — RESOLVED (revised 2026-06-12):** the **live top-50** are written by **Sonnet via
  the Anthropic API** (`AnthropicBackend`), **automated** in the box at each beat — no human
  session. The writer cohort and the golden/coverage set are the same 50. (See §2/§11/§12.)
  - **Cost estimate (rough, verify before launch):** ~50 cards × (~5k input + ~0.5k output)
    per full sweep. At Sonnet list (~$3/M in, ~$15/M out): **~$0.022/card → ~$1.10 per full
    sweep**. With the fingerprint, most beats rewrite only the handful that moved, so realistic
    spend is **~$6–12/mo** — well inside budget. A hard **monthly budget cap** in the backend
    enforces it (over cap ⇒ fall back to local `mistral`).
  - **Opus intentionally NOT used (Kevin's call):** Sonnet's confident-compiler quality is
    more than enough and the bill is ~5× lower.
- **D-2 — RESOLVED:** thresholds reflect "what CFB fans actually want" — **discourse-first,
  data-as-qualifier**, with HIGH entrenchment + no competition chatter suppressing the clock.
  Constants (70/30 pctl, `stars ≥ 4`) seeded from the live distribution and retunable; the
  discourse-first ordering is locked. (See §5.)
- **D-3 — RESOLVED:** in-season cadence is the full **live top-50** (not 25) at **3 beats/wk**
  — Sunday ~02:00 (post-Saturday recap), Monday (week-ahead), Thu/Fri (pre-game). (See §11.)
- **D-4 — RESOLVED (Kevin flagged 2026-06-12):** the top-50 must be filtered to players
  **active for the upcoming season** — departed players (drafted / transferred / graduated /
  flunked / any reason) get no forward preview; they recast as ghosts in successors' cards.
  The only catch-all is a **2026 roster**, which CFBD has NOT published yet (0 players as of
  2026-06-12). Resolution: **infer from departure signals now** (NFL draft + portal + eligibility
  — catches 11 of the live top-50), **schedule the `ingest-cfbd-preseason --season 2026` retry**,
  and let **roster presence become ground truth at ~August** (self-correcting on the next beat).
  Underclassman-drafted edge cases (Ty Simpson, class 3) trusted from the draft table for now;
  re-verified at roster. (See §4.1.1 / §14.2.)
  - **Side-find:** `ANTHROPIC_API_KEY` is **already set on the box** — D-1's key-handling
    concern is moot; the Sonnet path needs no new credential.
