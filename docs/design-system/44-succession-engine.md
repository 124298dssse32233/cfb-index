# 44 — The Succession Engine ("The Ghost, the Clock, the Musical Chairs")

_Status: SUBSYSTEM SPEC (v1). Created 2026-06-11. Deep dive on the most novel, most buildable CFB-native module from [[43-cfb-native-content-model]] §3. Detects positional succession from roster + stats + recruiting + transfer data — almost entirely deterministic (no LLM). Not yet implemented._

---

## 0. Why this is the most CFB-native thing we can build

A pro roster turns over slowly and fans don't keep a "who plays QB" lineage in their heads. In college football, **succession is the obsession** — "who's QB1?", "can he replace the legend?", "when does the 5-star freshman take over?" are the loudest offseason questions a fanbase asks.

**Grounding (real, this DB, 2026-06-11):** of 71 teams with a detectable QB1 in both 2024 and 2025, **48 (68%) changed their QB1** — succession is now an *annual* event, not a generational one. And the handoffs expose **portal chains**: Carson Beck was Georgia's QB1 (2024) → Miami's QB1 (2025); Fernando Mendoza was Cal's QB1 (2024) → Indiana's QB1 (2025). A vacancy at one program is filled by a defector from another.

So the engine has two axes:
- **Vertical** — the within-program *throne-line* (legend → bridge → heir, across seasons).
- **Horizontal** — the *portal flow* between programs (who left, who arrived, the musical chairs).

---

## 1. How fans actually view succession (the emotional model — design from this, not from the depth chart)

Fans never read a depth chart neutrally. They read it as **inheritance, legacy, and dread.** The card's job is to speak in that register, not recite a roster.

- **Succession is inheritance, not roster management.** A new starter doesn't "take the job" — he *inherits the standard.* "QBU." "The room." A player joins a *lineage with a brand* (RBU, DBU, OL factory). The throne has ghosts.
- **The heir's recruiting stars are a promise.** A 5-star heir = "we're set at QB for years." A 3-star transfer bridge = "we're just surviving." Fans grade the *succession plan* as much as the player.
- **The clock behind him is suspense.** Every bridge starter has a freshman phenom whose hype grows with each of the starter's bad games. "Time for the kid" is a renewable open loop.
- **The portal made it musical chairs.** Fans now track *where the QB1 came from and where the old one went* like a transfer market — a stock exchange of starters.
- **Blocked talent is a debate.** A 5-star stuck behind a senior: should he stay or portal? Fans litigate it weekly.
- **The torch-passing is sacred.** The legend's last start and the heir's first start are emotional events, not stat lines.
- **Whiffing on succession is panic.** No QB recruited, forced to scramble the portal = "we HAVE to get a QB." Fans fear the *gap*, not just the player.

> Design rule: the Succession module's **tone is set by the fan's emotional position** — mourning a legend, dreaming on a phenom, dreading a downgrade, or bracing for a leap of faith (§7). The data picks the facts; the emotion picks the voice.

---

## 2. The throne-line (vertical) — role-holder detection

Generalize "QB1" to **the role-holder**: the player with the most position-defining usage in a team-season.

| Position | Role-holder signal | Source |
|---|---|---|
| QB | max pass attempts | `player_season_stats` ATT |
| RB | max carries | CAR |
| WR/TE | max targets/receptions | REC |
| DL/LB/DB | max tackles (proxy) / snaps if available | tackle stats |
| OL | starts/snaps (partial — confidence-gate) | roster/usage |

The **throne-line** = the ordered sequence of role-holders for (team, position) across seasons. Each node carries: player, recruiting stars/rank, class year, production, and **fate** (drafted / transferred-out / benched / graduated).

```
Tennessee QB throne-line
2024  Nico Iamaleava   5★#3   → fate: TRANSFERRED OUT (UCLA)
2025  Joey Aguilar     3★ SR  (portal arrival from App State)   ← current
       behind him: Jake Merklinger 4★#160, George MacIntyre 4★#151  ← the clock
```

---

## 3. The portal flow (horizontal) — musical chairs

A succession event is classified by **where the heir came from** and **where the predecessor went**, traced through `transfer_entries`:

- **Predecessor exit:** drafted (NFL draft data) · transferred-out (→ which program) · benched (still rostered, lost the role) · graduated.
- **Heir origin:** **internal** (was on last year's roster behind the legend — "the kid who waited") · **portal arrival** (transfer — "the import," with origin program) · **true freshman** (class=1 — "thrust in").

**The chain view:** link a program's vacancy to the destination of its departed starter and the origin of its replacement. Carson Beck: *Georgia's throne → Miami's throne.* This renders the portal as a **transfer market graph** — uniquely CFB, and a fan obsession.

---

## 4. The three roles (what the card narrates)

1. **The Predecessor (the ghost).** The departed role-holder. Carries the weight the heir must match.
2. **The Incumbent (him).** The current role-holder, narrated *against the ghost above and the threat below.*
3. **The Heir-Apparent (the clock).** The highest-upside young player not yet starting — by recruiting stars/rank + class year + practice/depth-chart signal.

---

## 5. "Filling the Shoes" — the comparison engine

Compare incumbent vs predecessor on four registers, then emit a **read** and a **tone**:

```
shoes_delta = f(
  pedigree   : heir stars/rank   vs predecessor stars/rank,
  production : heir output        vs predecessor output (same career stage where possible),
  hype       : heir discourse vol vs predecessor's,
  expectation: fanbase sentiment about the heir
)
```

| Read | Condition | Example (real) | Fan tone |
|---|---|---|---|
| **Downgrade** | heir less heralded/productive | Colorado: Shedeur Sanders 477att (NFL) → Kaidon Salter 204att | dread / "can we survive it?" |
| **Upgrade** | heir more heralded/productive | a 5-star replacing a game-manager | greed / "the leap we dreamed of" |
| **Continuity** | comparable | "the standard continues" | reverence |
| **Leap of faith** | freshman / no track record | a true-freshman QB1 | anticipation / hope |
| **Low bar** | predecessor was a disappointment | replacing a benched bust | relief / "anywhere but here" |

The read drives the lede and the BAN; the tone drives the voice. The comparison is **honest and attributed** — never "he's better than [legend]," but "fans are asking whether he can fill it; here's the gap the numbers show."

---

## 6. "The Clock Behind Him" — the heir-apparent open loop

For every role-holder, surface the **most threatening young talent below him**:

```
clock_score = recruiting_pedigree × youth × (latent_opportunity)
  where latent_opportunity rises when the incumbent struggles,
        is a bridge/senior, or is a portal flight risk
```

- For a **bridge starter** (3-star senior / stopgap): a high clock_score = live suspense — *"how many games until Merklinger (4★) takes the job?"*
- For a **star**: the clock is *who's being recruited to replace you* — the program's succession plan.
- **Blocked-talent flag:** a high-pedigree backup behind an entrenched starter → the "should he stay or portal?" debate, surfaced with the portal-risk read.

This is a renewable in-season open loop ([[41-player-story-card]] open-loop engine): each week the incumbent falters, the clock ticks louder.

---

## 7. Position-specific emotion (fans don't treat positions equally)

- **QB — existential.** The most emotional throne; succession dominates the offseason. Full treatment.
- **RB — "RBU churns."** Fans expect turnover; the narrative is "next man up" and the *factory's* reputation, not one legend. Lower mourning, higher "who's the next stud."
- **OL — continuity & development.** Fans value the unit and multi-year development; succession is about *cohesion*, not a single heir.
- **WR/DB/edge — the factory.** Programs branded as position factories (DBU, WRU) narrate a player as the *latest product of a pipeline to the NFL* — lineage as a draft-pipeline brand.

The engine keys the succession tone off position so a RB handoff doesn't get QB-grade melodrama.

---

## 8. Card surfaces (the modules)

- **Throne Lineage viz** — the chain of role-holders with stars + fate; the "ghosts in the rafters." (deterministic)
- **Filling-the-Shoes meter** — the §5 read + the gap, with the predecessor as the benchmark. (deterministic)
- **The Clock** — the heir-apparent + the suspense line. (deterministic; LLM polish)
- **Torch-Passing moment** — when detected (legend's last start / heir's first), a one-time commemorative beat. (deterministic trigger)
- **Portal Musical-Chairs** — the came-from / went-to chain for transfer-driven successions. (deterministic)

All deterministic — consistent with the layered build ([[42-player-narrative-engine]] §4b): determinism owns truth, the LLM only voices it.

---

## 9. Detection logic + honest gaps

**Deterministic pipeline:**
1. Compute role-holder per (team, position, season) from usage stats.
2. Diff consecutive seasons → succession events (68% of QB rooms in the real data).
3. Classify predecessor exit + heir origin via `transfer_entries` + NFL draft + roster presence.
4. Identify heir-apparent via recruiting pedigree + class + depth signal.
5. Run Filling-the-Shoes comparison; emit read + tone.
6. Trace portal chains across programs.

**Gaps / confidence:** OL/defense role-holder detection is weak without snap data (confidence-gate or skip); "games started" is partial (attempts/usage is the best proxy); spring/fall depth-chart battles before a season has stats need `player_depth_chart_2026` + practice-report discourse (lower confidence, mark as projection); true mid-season benchings need weekly usage, not season totals.

---

## 10. The tone guide (how the fan's position sets the voice)

| Fan emotional position | Trigger | Card voice |
|---|---|---|
| **Mourning** | a legend left (high-star/production exit) | elegiac — honor the ghost first |
| **Dread** | a downgrade succession | anxious — name the gap honestly |
| **Hope / dreaming** | a heralded heir or phenom | anticipatory — lean into ceiling |
| **Leap of faith** | unproven freshman QB1 | suspended — the unknown as the hook |
| **Relief** | replacing a bust | low-bar — "nowhere to go but up" |
| **Suspense** | bridge starter + loud clock | episodic — the open loop |

The succession facts are deterministic; this table picks the register the LLM writes in. *The data says what happened; the fan's heart says how to tell it.*

---

## 11. Provenance

Grounded in real DB queries (2026-06-11): 68% QB1-handoff rate (71 teams), portal chains (Beck GA→MIA, Mendoza CAL→IND), the Tennessee throne-line. Derived from the multi-AI brainstorm and the fan-ledger model ([[43-cfb-native-content-model]]). Builds on [[42-player-narrative-engine]], [[41-player-story-card]], [[player-narrative-engine]].
