# 50 — Team Story Card ("The Marquee")

_Status: DESIGN SPEC (critique-hardened v2). Created 2026-06-11 via octopus Team-mode brainstorm (Codex feasibility · Gemini 2026-ecosystem · Claude pattern/paradox) + two adversarial passes (a deepening that red-teamed the lead resolver and the Tribal-Lens honesty line, then a full multi-AI review of the drafted set — Codex 19 findings, Gemini honesty/ecosystem, Claude set-coherence). The TEAM analog of the Player Story Card ([[41-player-story-card]]). The crown that turns a pile of ~24 excellent team-page modules into a story with a spine. Not yet implemented._

A top-of-page narrative module for every FBS team page that compiles **"here is the state of this program, as a story, as of today"** in the fanbase's own voice — a confident-compiler narrator that states the dominant fan take with conviction, attributed to the fanbase, carries a confidence meter, and is never the site's own opinion. Lives in the Noir fan sub-brand ([[40-noir-subbrand]]). Sits ABOVE the existing world-class team-page chrome ([[CLAUDE.md]] Team Pages module); it is the **lead**, and the ~24 modules below are the **evidence locker** that prove it.

> **The spine, not a 25th module.** The team page is already deep ([[54-integration-with-live-team-system]] inventory). This card does not summarize the modules — it *asserts a thesis* and points down at them. It is the only element on the page allowed to take a position.

---

## 1. Design principles

1. **Calm at rest, story on intent.** Collapsed by default. A standings/schedule-only fan must get real value (identity + record + next game) without expanding anything, and reach the schedule in one tap.
2. **One statistic, welded to its label** (the "BAN" — a single *stat object*: a record, percentile, count, or margin; not literally one digit, [[41-player-story-card]] §6) — honest (gated) and never bare.
3. **Every claim wears its receipt** ([[32-receipt-pattern]], ≥1 marker / 200 words). The trust moat.
4. **The fanbase narrates the fanbase.** Unlike the player card (where the *nation* narrates the player), here the *tribe* narrates *itself*. The voice is "we/us" in the Home lens — and the honesty mechanism is the confidence meter + the **half-life label** (§4), because a tribe lies to itself.
5. **Lead with what *moved*, anchored by what *is*.** The crown picks which of five timescales × six characters leads today by a Level-anchored, displacement-overthrown resolver ([[51-team-narrative-engine]] §3). It never flip-flops day to day (hysteresis), and it never goes silent on a blue blood just because nothing moved (the Standing Lead).
6. **Never manufacture a saga.** Below a data-confidence floor the crown collapses into a *different speech act* — not a quieter saga (§6, [[57-team-dependency-degradation-matrix]]). Confidently narrating **the Quiet State** ("A quiet June — the program's standing question is unchanged") is still a confident card.

---

## 2. Color tokens (Noir dark surface — WCAG-checked)

Inherit the locked Noir + design tokens ([[00-tokens]], [[40-noir-subbrand]]); the Team Story Card reuses the Player Story Card ramp ([[41-player-story-card]] §2) with one change: the left rail signals **program tier + page mode**, not Chronicle tier.

```css
--tsc-ink-900:#0A0A0D;   /* page */
--tsc-ink-850:#101015;   /* inset / BAN well */
--tsc-ink-800:#16161C;   /* card surface */
--tsc-hairline:#2A2A33; --tsc-hairline-strong:#3A3A45;
--tsc-gold:#ECC15C;      /* house accent: big number, button text, focus ring */
--tsc-text-hi:#F4EFE7; --tsc-text-body:#DAD4C9; --tsc-text-mut:#ABA59B;
--tsc-team:#9E1B32;      /* PER-TEAM color, injected at render; ring + rule ONLY, luminance-clamped */
```

**Rail = page mode, not just tier.** The accent keys off `state_resolver`'s `accent_key` / `copy_tone` ([[54-integration-with-live-team-system]] §2), so the rail color *already knows the mode* (RIVALRY PEAK, AUTOPSY, HYPE PEAK). The crown reads it; it does not recompute it. Team-color injection runs the same per-team contrast clamp/floor as the player card ([[41-player-story-card]] §2).

---

## 3. Typography

Identical contract to [[41-player-story-card]] §3: **Bebas Neue** for the BAN only · **Source Serif 4** (mixed-case) for the logline/prose/tension/quote · **Inter** (tabular-nums) for identity/chips/meta. Self-host subset woff2, `font-display:swap`, server-side char caps (§6).

---

## 4. Anatomy (collapsed → expanded), mobile-first

```
┌─[mode rail 4px]──────────────────────────────────────┐
│ ⬢  Michigan Wolverines              [◐ lens] [↗] [ⓘ] │  identity anchor
│    11-1 · Big Ten · No.3 CFP        Home ▾             │  (team ring + lens toggle)
│                                                        │
│ RIVALRY WEEK · THE GAME            as of 8:42 AM ▸     │  mode chip + freshness
│                                                        │
│ The whole season walks into Columbus Saturday.        │  logline (mixed-case serif)
│                                                        │
│ ┌ THE GAME · all-time ───────────────────────────────┐│  BAN — number welded to label
│ │  58-52-6   Michigan leads the rivalry               ││
│ │            but has dropped 3 of the last 4          ││  receipt → games table
│ └─────────────────────────────────────────────────────┘│
│                                                        │
│ Beat Ohio State and a Big Ten title is back on the    │  tension / stakes (serif italic)
│ table; lose and the December questions start early.   │
│                                                        │
│ ▰▰▰▰▱ confidence: high · the fanbase is locked in     │  confidence meter + take half-life
│ ───────────────────────────────────────────────────── │
│ [ Read the state of the program  ⌄ ]   Schedule ↓     │  afford row (≥44px targets)
└────────────────────────────────────────────────────────┘
        ▼ expands (details / grid 0fr→1fr)
   "PREVIOUSLY ON…" — 3-4 season plot-points (the campaign so far)
   supporting threads: ◐ the coach · ◑ the portal class   (chips → modules below)
   ❝ pulled fan quote ❞ — r/MichiganWolverines · source
   WHAT'S AT STAKE — the path object (win-and-in / eliminated)
   ↻ this story shifted: <Timescale-Piercing Event + date>   (logline change; a Flip Point is one kind)
   AI narrative · compiled <date> · sources · report an error
```

**The lead block is moment-dependent.** Which of the six characters fills the logline + BAN is chosen per day by the resolver ([[51-team-narrative-engine]] §3): rivalry week → the rivalry leads (above); a Tuesday firing → the coach leads; June at a blue blood → the era/standard leads; a portal haul → the roster leads. **Collapsed height is a content budget, not a CSS height** ([[41-player-story-card]] §4) — cap copy server-side so the collapsed card clears the fold on a 667px phone.

**"PREVIOUSLY ON…"** is the crown's own expand affordance (the one Gemini idea that earns crown space, [[52-cfb-team-content-model]] §6) — the season as plot-points, not a score recap. It is NOT a separate module.

---

## 5. The Tribal Lens (Home / National / Rival)

Fans read their OWN page obsessively *and* hate-read RIVAL pages to gloat ([[52-cfb-team-content-model]] §4). The lens toggle re-renders rhetoric and emphasis from the **same facts and the same confidence** — claims are lens-invariant; only the framing verb changes ([[51-team-narrative-engine]] §5).

- **Home** (default human view) — the tribe's reading of true facts. Partisan in *emphasis*, never in fact. "We" voice.
- **National** (the crawlable / indexed H1) — the honest read; never an embarrassing search snippet. This is what a cold visitor and Googlebot see first; the client applies the reader's saved lens from `localStorage` on load.
- **Rival** — the confession laid bare, bounded by the **Home-Anchor Rule + Fact-Anchor exception** ([[56-team-fan-ledger-detectors]] §3): it may only re-frame anxieties the **home fanbase already expresses about itself** (plus objective stats, always), and may introduce **no claim the Home lens lacks**. Hard-blocked: medical/legal/personal/non-football. It echoes the tribe's own dread as ridicule; it never accuses.

**Delivery (static-site).** All available lenses ship as one small inline JSON payload (~2–4 KB/team, <1.5 KB Brotli; it lives only on that team's page, so 119 teams do not multiply client weight) + a sub-1 KB generic toggle script that swaps text through fixed `data-story-field` targets. **Only one card DOM tree** — mutate text, never render three hidden trees. CSS is injected RAW (no `<style>` tags — [[55-team-rollout-infra-compat]] §4). Full data shape in [[51-team-narrative-engine]] §5. If a lens's discourse is below floor, render only the lenses that clear it (often just National) — graceful, not 3× always.

---

## 6. Low-data / Quiet-State fallback — REQUIRED

The card always renders something true ([[57-team-dependency-degradation-matrix]] §3 ladder). Confidence collapses into a different **speech act**, not a quieter saga:

- **High confidence** → a claim ("Tennessee fans have decided the staff has earned another year").
- **Low confidence** → a report of division ("The fanbase is split between patience and panic").
- **Below the floor** → the **Quiet State**: no narrative, just the standing. Confidently stated, not blank.

```
┌─[flat rail]─────────────────────────────────────┐
│ ⬡  Akron Zips                                     │
│    5-7 · MAC · 4th East                           │
│ A quiet season. 5-7, two one-score losses,        │
│ next up: the December recruiting window.          │  Standing-led, no manufactured saga
│                       Limited signal              │
└───────────────────────────────────────────────────┘
```

No logline, no confidence-meter-implying-sophistication. The floor reconciles with the **real, already-computed** signal gates: `backometer_weekly.is_low_signal` / `is_offseason` and `MIN_SAMPLE=200`, and the pulse `SENTIMENT_FLOOR=100` ([[57-team-dependency-degradation-matrix]] §1). Honest > dramatic.

---

## 7. BAN-selection logic (welded to its label)

Same honesty-gated machinery as the player card ([[41-player-story-card]] §6). The BAN is a single **statistic object** (`{number, label, receipt}`, sometimes a record like `58-52-6` with a one-line gloss), not literally one digit. Team candidate pool: rivalry all-time record, the Standard-Gap number ([[52-cfb-team-content-model]] §2), playoff/bowl path odds, a coaching-era win rate, a recruiting-class rank, a drought count ("26 years since the last title"). `honesty_gate = 0` disqualifies (not down-weights) a cherry-pick (gerrymandered split, sub-`MIN_SAMPLE` cohort). If nothing clears the gate, the card has no BAN — drop the block, never fabricate one. **The BAN earns its pixels against the game** (Gemini): in the collapsed view it is a *story* number only when a Timescale-Piercing Event is active; on a quiet day it cedes to the utilitarian number (next kickoff / last result), honoring "calm at rest" (§1).

---

## 8. Logline & lead stability (anti-whiplash)

**Two layers, two lifetimes** (resolving the lead-vs-logline desync the review caught). The crown separates a durable **program thesis** from the **current lead**:

- **The program thesis (the logline)** persists across regenerations and changes only on a **Timescale-Piercing Event** ([[52-cfb-team-content-model]] §3) — a result, firing, hire, rivalry outcome, conference move, or a Flip Point (a `backometer` sticky-zone crossing). It is the season-scale headline ("This is a fireable year / the best stretch since the dynasty").
- **The current lead (the eyebrow + tension + BAN)** is the *today* layer; the resolver may move it character-to-character daily ([[51-team-narrative-engine]] §3). When the lead character diverges from the thesis (the coach leads under a rivalry-era logline), the eyebrow carries the lead and the logline carries the thesis — they are allowed to differ, and the divergence is itself legible.

The lead is held by the **resolver's** hysteresis ([[51-team-narrative-engine]] §3e): a challenger must beat the incumbent by **12 pts** (20 during a 48-hour hold); a hard event bypasses the hold. **This is the lead-resolver's own state machine — distinct from `backometer`'s belief-*zone* hysteresis (`HYSTERESIS_PTS=3` / 2-week hold), which governs the mood SCORE, not the lead.** The two never share thresholds; see [[51-team-narrative-engine]] §3e for the single canonical definition.

---

## 9. Interaction, motion & a11y

Inherits the Player Story Card contract verbatim ([[41-player-story-card]] §8–8.5): native `<details>/<summary>` baseline (SSR, zero-JS), JS `grid-template-rows:0fr→1fr` enhancement, ≥44px targets, 2px gold focus ring, **1–2 animated elements per view max** (the BAN is the single numeric hero; everything else is static so it reads as fact), `prefers-reduced-motion` snaps instantly, the Quiet-State card is motionless always. The lens toggle is a third control (after expand + "Schedule"); unequal goals get unequal weight. AI disclosure footer is persistent: "AI narrative · compiled <date> · sources · report an error."

---

## 10. Open coordination

- The world-class team-page hero (`hero_arc_stripe.py` / `page_tone_strip.py`) and this card must not both own the mode signal — the card **reads** `PageState`, the strip stays as the wide visual ([[54-integration-with-live-team-system]] §2). Decide which owns the identity row.
- **Indexed lens.** National-as-crawlable-H1 vs Home-as-crawlable is the one call flagged for owner sign-off (§5). Recommendation: index National (honest, defensible snippet), default human view Home.
- Live/in-game freshness (suppress or flag) reuses the player open item ([[41-player-story-card]] §9); v1 is daily-batch with explicit "as of" labeling ([[51-team-narrative-engine]] §6).

## 11. Sources

Team-mode multi-AI brainstorm 2026-06-11 (Codex implementation · Gemini 2026 ecosystem · Claude pattern/paradox) + adversarial deepening (red-team of the resolver and the Rival-lens honesty line), grounded in the live `team_pages/` renderer, `backometer_weekly`, `team_conversation_daily`, `state_resolver`/`PageState`, and the Chronicle runtime. Mirrors [[41-player-story-card]]. Within the locked design system ([[00-tokens]], [[30-page-archetypes]] Profile/Tentpole, [[31-chart-vocabulary]], [[32-receipt-pattern]], [[33-confidence-signaling]], [[40-noir-subbrand]]).
