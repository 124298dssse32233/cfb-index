# 53 — Program-Succession & Coaching-Carousel ("The Regime, the Reload, the Hot Seat")

_Status: SUBSYSTEM SPEC (critique-hardened v2). Created 2026-06-11. The team analog of the player Succession Engine ([[44-succession-engine]]). Builds the one character every Team-mode brainstorm named the protagonist — **the head coach** — for which the live DB has NO structured data (`team_seasons.head_coach` is a bare column; no tenure/hot-seat/buyout table). This doc specs that net-new source, plus the annual roster-reload succession. v2 hardens the speech-act language (no "consensus" overreach), adds phase hysteresis, and fixes the `coaching_tenure` schema to one-row-per-tenure. Owner greenlit "spec the new data source," 2026-06-11. Not yet implemented._

---

## 0. Two parallel succession stories

The player throne-line ([[44-succession-engine]]) replaced a legendary QB. The **program** has two succession stories at once, and the card compiles both:

- **The coaching carousel = the program's regime throne-line.** Coaches ARE the program's succession — the Saban → next-guy "filling impossible shoes" arc is the team-scale version of replacing a legendary QB. Hot-seat → search → hire → honeymoon → judgment. This is the protagonist of the in-season story.
- **The roster reload = annual succession across the whole roster.** "Who replaces the departed stars" every offseason — returning production, the portal haul, the recruiting class stepping up. The *team* filling the shoes, every single year, across the roster rather than one position.

Cross-link: a player's "filling the legend's shoes" arc ([[44-succession-engine]]) and the program's "who's our next QB1 / who replaces the stars" arc are **two views of the same event** — the coaching regime is the macro throne-line; the QB room is one micro throne-line inside it. The card links them.

---

## 1. The honest data gap (why this is net-new)

Every other character on the team card has a live table ([[52-cfb-team-content-model]] §8). The coach does not:

- `team_seasons.head_coach` — a bare name string. No start year, no contract, no buyout, no pressure.
- `coaching_era.py` renders a tenure strip from that column, falling back to "Awaiting Signal" when thin.

So the coach — named the protagonist by Codex, Gemini, and Claude alike — has **no structured pressure signal.** This is the single highest-leverage net-new build in the whole spec set, and the one that most needs the do-not-amplify guardrails (a coach is a named living person; "fire him" is the most volatile, most defamation-prone thing fans say).

---

## 2. The coaching throne-line (the regime arc)

Generalize the player throne-line ([[44-succession-engine]] §2) to the program's regimes. The **regime-line** = the ordered sequence of head coaches for a program, each node carrying: coach, tenure (start→end year), record, peak (best finish / titles), and **fate** (fired / left for a bigger job / retired / still here).

```
Alabama regime-line
2007-2023  Nick Saban    6 natties     → fate: RETIRED  ← the ghost
2024-      Kalen DeBoer  Year 3        ← the incumbent, narrated against the impossible shoes
```

The "Filling the Shoes" comparison ([[44-succession-engine]] §5) transposes directly: DeBoer-after-Saban is a regime-scale `shoes_delta` (pedigree, early record, fanbase expectation) — and the **Standard-Gap** ([[52-cfb-team-content-model]] §2) is the benchmark he's measured against. The phases:

```
HONEYMOON → SECURE → WARMING → CROSSROADS → HOT SEAT → SEARCH → (new) HONEYMOON
                                              └→ LAME DUCK (extension stalled / final year)
```

---

## 3. `coach_pressure_weekly` — the net-new source

Stable key `(program_slug, season_year, week)` (slug, never a re-ingesting id — [[55-team-rollout-infra-compat]] §0), **append-only with an `observed_at`** so nightly recompute does not overwrite the week's pressure history (review fix). A **NON-critical** nightly compute that degrades to tenure-only if discourse is thin.

| Input | Source | Net-new? |
|---|---|---|
| Tenure / contract / buyout | **`coaching_tenure`** — hand-seeded, **one row per TENURE** (slug, coach, start_date, end_date, fate, record_provenance, plus dated contract observations for contract_through/buyout_usd/source_url so volatile money data isn't overwritten). Covers the current coach + enough history to draw the regime-line (§2). More than 119 rows (multiple tenures per program), still tractable like the 127 `profiles/*.md` | **YES — new table + seed** |
| Performance Anchor | actual wins vs model-expected (SP+ / preseason projection); SP+ rank drop since preseason | reuse rankings/SP+ |
| Hot-seat discourse | "fire/buyout/extension" keyness as a % of program mentions, 14-day rolling | reuse `team_conversation_daily` + [[56-team-fan-ledger-detectors]] |
| Economic confirmation | buyout-math terms ("affordable," "donors," dollar figures) in Tier-A sources | reuse Chronicle `source_trust` |

**Output:** `pressure ∈ [0,1]` + a `phase` label (§2) + an `evidence_level ∈ {1,2,3}` that gates the speech act (§5).

---

## 4. The three gates (the honesty firewall)

A discourse-derived hot seat must clear all three before the card may escalate beyond "audible discontent." Fan discourse screams "fire him" every Saturday night and forgets by Tuesday — these gates are a low-pass filter on that volatility (Gemini stress-test, 2026-06-11):

1. **The Stability Window (persistence).** "Fire/buyout" volume must exceed ~15% of total program mentions over a **rolling 14-day window**. A single-game spike is labeled *Reactive Surge* / "immediate reaction," never Hot Seat ([[51-team-narrative-engine]] §1 settled-vs-surge).
2. **The Performance Anchor (reality check).** The seat is only "hot" if the program is **underperforming its model-expected win total by ≥1.5 games OR has dropped ≥20 SP+ spots since preseason.** If the team is winning, fan anger is **"high expectations / friction," not a hot seat.** This is the gate that protects a *winning* coach from a loud-but-irrational fanbase.
3. **The Economic Signal (the carousel is real).** Buyout-math terms in **Tier-A sources** (beat writers / national reporters) before the top level — fans pricing the buyout is the tell that the search is genuinely live, not venting.

**Hard safety gate:** `HOT SEAT` / `SEARCH` require **≥2 source classes including ≥1 non-discourse** (Performance Anchor or Tier-A reporting) **AND ≥2 distinct platforms** in the discourse signal (one Reddit cluster + one Tier-A beat ≠ one brigade — review fix; raises the brigade floor above `MIN_SOURCES=2`, [[56-team-fan-ledger-detectors]] §4). **The tribe alone can never seat a coach.** This is the team-scale version of the player anti-fabrication floor ([[42-player-narrative-engine]] §6).

**Phase hysteresis (review fix — no nightly flip-flop).** The phase (§2) has **separate enter/exit thresholds** and a **minimum hold**, so a coach does not oscillate `CROSSROADS ⇄ HOT SEAT` on a one-game swing across the 15% / 1.5-game / 20-SP+ cliffs: enter `HOT SEAT` at ≥15% sustained 14 days; exit only below ~10% sustained 10 days; minimum phase hold 14 days unless a hard event (firing/hire) forces it. Same family as the `backometer` sticky-zone hysteresis, applied to the phase machine.

---

## 5. Speech acts by evidence level (the defamation discipline)

The card's vocabulary is strictly gated by corroboration — the same compile-don't-adjudicate stance ([[51-team-narrative-engine]] §1):

| Level | Condition | Speech act | Register |
|---|---|---|---|
| **1** | Discourse spike, low persistence | "audible discontent" / "the fanbase is processing a setback" | about the *fans'* mood, not the coach's job |
| **2** | Persistent discourse + Performance Anchor | "**persistent calls for a change**" / "a program at a crossroads" — with the **cohort size + % published** | crisis named, *unadjudicated*; NOT "consensus" |
| **3** | Level 2 + **independent Tier-A reporting** | "a tenure under intense scrutiny" / "the seat has become a decision point" | canonical Hot Seat; may surface buyout figures + "names to watch" only when *reporting* (not discourse) has pivoted to candidates |

**The language discipline (review fix — 15% is not consensus).** The card never says *"the coach should be fired."* Below independent reporting it says *"persistent calls for a change,"* always with the published cohort size and percentage — it does **not** call 15% of mentions a "consensus." The word "consensus" is reserved for a genuine strong majority of the qualifying cohort; "hot seat / search" is reserved for when **independent Tier-A reporting** corroborates (the non-discourse leg of the hard gate, §4). Attributing the *observed* sentiment to the cohort, sized and dated, keeps the site a compiler of tribal truth, never an adjudicator of professional competence and never an accelerant manufacturing a revolt that isn't there.

---

## 6. The roster reload (annual succession)

The offseason "who replaces the departed stars" story, at team scale. Reuses the player succession data ([[44-succession-engine]]) aggregated to the program:

- **Departures ledger** — drafted / transferred-out / graduated stars (NFL draft data, `transfer_position_snapshots` outflow).
- **The reload** — returning production %, the portal **influx** (`transfer_position_snapshots`), the recruiting class (`recruiting_footprint`, `top_commits`).
- **The verdict** — "did the program reload or rebuild?" — a Hope-Ledger read ([[52-cfb-team-content-model]] §3.4) keyed off net talent flow. The 2026 framing: **Tenure Equity** (homegrown anchors vs one-year portal rentals) is a first-class axis — "we're trusting a hired gun to protect a legacy he didn't build" (Gemini, 2026-06-11).

The reload feeds the `roster` character in the resolver; the coaching carousel feeds the `coach` character. In the offseason both compete with Hope for the Standing Lead ([[51-team-narrative-engine]] §3e).

---

## 7. Card surfaces (the modules)

Each is classified ABSORB / ORCHESTRATE / NEW against the spine discipline ([[54-integration-with-live-team-system]] §2 — these are not free-standing widgets):

- **Regime-line viz** — the chain of head coaches with record + fate; the team-scale "ghosts in the rafters." **ORCHESTRATE** (extends the existing `coaching_era.py` strip; the crown *characterizes* the regime, the strip owns the chronology). Deterministic.
- **The Hot-Seat read** — phase + the gated speech act + buyout context (L3 only). **NEW signal, surfaced BY the crown** (it is the `coach` character's claim in `ProgramNarrativeState`, not a separate module). Deterministic + LLM voice.
- **Filling-the-Regime-Shoes** — incumbent vs predecessor, benchmarked against the Standard-Gap. **ABSORB into the crown's lead** when the coach leads; otherwise a line in the regime strip. Deterministic.
- **The Reload card** — departures vs the portal/recruiting haul, the Tenure-Equity read. **ORCHESTRATE** the existing `roster_reload.py` / `recruiting_footprint`; the crown asserts the verdict, the module is the evidence. Deterministic.
- **The carousel chain (later)** — where the departed coach went / where the new one came from. **NEW** (small), the macro analog of player portal chains ([[44-succession-engine]] §3) — a deferred enhancement, not a v0 surface.

---

## 8. Detection logic + honest gaps

**Deterministic pipeline:** seed `coaching_tenure` → compute Performance Anchor (wins vs expected, SP+ delta) → mine hot-seat keyness % over the 14-day window → apply the three gates → emit `pressure` + `phase` + `evidence_level`. **Gaps / confidence:** `coaching_tenure` is hand-seeded (like the profiles) so coverage is bounded by the seed effort — confidence-gate any program without a seeded row to tenure-only ("Year 3 of the era"); buyout figures are public for major programs, thin for G5 (omit honestly); the institution/NIL-collective signal (the rev-share "are they paying to win" audit) is the thinnest data and ships discourse-only first ([[52-cfb-team-content-model]] §8).

---

## 9. The tone guide (the fan's position sets the voice)

| Fan position | Trigger | Card voice |
|---|---|---|
| **Reverence** | a legend retired/left on top | elegiac — honor the regime first |
| **Faith** | honeymoon / strong start | hopeful — "the right hire" |
| **Friction** | winning but underwhelming the Standard | impatient — "high expectations, not a hot seat" |
| **Crisis** | persistent discourse + Performance Anchor | anxious — "a crossroads," unadjudicated |
| **Reckoning** | Level 3 hot seat / search | grave — the cohort's consensus, attributed, never adjudicated |
| **Dread / hope** | a downgrade / upgrade reload | the Tenure-Equity read |

The facts are deterministic and gated; this table picks the register the LLM writes in.

## 10. Provenance

Grounded in the real gap (`team_seasons.head_coach` is a bare column; no hot-seat table — [[CLAUDE.md]]). The three gates + the speech-act ladder are from the Gemini honesty stress-test (2026-06-11). Mirrors [[44-succession-engine]]; cross-links the player throne-line to the regime throne-line. Feeds the `coach`/`roster` characters in [[51-team-narrative-engine]] §3–4; detector lexicons in [[56-team-fan-ledger-detectors]]; rollout in [[55-team-rollout-infra-compat]].
