# 60 — Player Page: Master Design & Format (LOCKED synthesis)

_Status: **LOCKED v1**, 2026-06-12. The single source of truth for the **overall** player-page
design and format. Synthesizes three streams that had drifted apart: (a) the Google Stitch
visual exploration (Jun 2026), (b) the locked Noir sub-brand + Story Card specs
([[40-noir-subbrand]], [[41-player-story-card]]), and (c) the live engine that already ships
(`story_card.py`, `story_card_renderer.py`, `succession.py`, `ledgers.py`, the
`player_story_card_cache`). Where those three conflicted, this doc **resolves** the conflict and
that resolution is binding. BAN-selection internals are deferred to a follow-up; this doc locks
everything around them._

> One line: **Stitch gave us the STRUCTURE; Noir gives us the SYSTEM. We keep Stitch's IA,
> hierarchy, de-cluttering, and the BAN-as-hero; we adopt Noir's palette, semantic-accent
> discipline, and type. The page SHAPE is data-driven (the engine's `composition` array), not
> hand-laid.**

---

## 1. The synthesis verdict

| Stream | KEEP | DROP |
|---|---|---|
| **Google Stitch** | full-page editorial IA · BAN as the hero moment · de-duplication + empty-state suppression · the single percentile-bar chart vocabulary · headshot in the hero · the magazine "one cohesive scroll" feel | maize/gold *everywhere* · Tailwind-CDN tokens (`#0E1216`/`#14191F`) · invented data · generic nav/footer · rounded radii |
| **Noir / Story Card specs** | the `--noir-*` palette · **semantic-accent discipline** (perception=violet, events=green/red, market=blue) · receipts in mono · the tier rail · motion discipline · confidence meter · "compile, don't adjudicate" voice | the all-cards-are-one-three-zone-grammar constraint (the page is richer than a single Backometer card) |
| **Live engine** | the **adaptive `composition` array** as the format contract · archetype-driven module presence · the real cached data | the templated BAN/tension prose (being fixed separately) |

---

## 2. Locked tokens (the player-page route is `.theme-noir`)

Base palette = Noir ([[40-noir-subbrand]] §3), unchanged. Restated here as the binding set:

```css
--noir-ground:#101418;    /* page ground — never pure black */
--noir-surface:#1B2128;   /* card surface */
--noir-surface-2:#242C35; /* nested chips / hover */
--noir-text:#EDE6D6;      /* chalk — primary text */
--noir-receipt:#B8B2A4;   /* metadata/receipts — min 12px, weight 500, NEVER opacity-muted */
--noir-hairline:rgba(237,230,214,0.10);
/* semantic accents — COLOR IS SEMANTICS, never decoration: */
--noir-up:#2EE07C;        /* wins / positive deltas — events & production ONLY */
--noir-down:#FF4E42;      /* losses / negative deltas — events & production ONLY */
--noir-aura:#9D6BFF;      /* fan-PERCEPTION graphics ONLY (✦) */
--noir-aura-text:#B794FF; /* perception at text size */
--noir-market:#3D91FF;    /* betting-market data ONLY — always dashed + square + label */
--noir-neutral:#A8A294;   /* stable / mixed / informational */
```

**Locked accent rules (resolves the Stitch "gold everywhere" drift):**
- **Perception / aura / hype-vs-tape data is VIOLET, not gold.** The −35/−59 perception-gap BAN, the aura bars, "In Their Words" — all `--noir-aura`. (Stitch and the earlier mockups wrongly used maize here.)
- Events & production (game results, deltas, WEPA value) use up/down green/red by sign.
- Betting/market = blue, always dashed + square markers + a direct label.
- **Glyph redundancy is mandatory** (▲ ▼ ✦ ▪) — hue never works alone (CVD).
- **Gold/silver/bronze are TIER TEXTURE only** (the rail, §5), never data ink. This is the one carve-out from "no gold," and it's allowed because the rail encodes stature, not a value.
- **Team color = identity only** (logo chip + ≤12% tint band). It never encodes data.

---

## 3. Locked typography (resolves Anton vs Bebas)

The specs disagreed: [[40-noir-subbrand]] §3.4 says **Anton** for verdict words + hero numbers;
[[41-player-story-card]] §3 + the live renderer (`--font-display`) say **Bebas Neue**. **Resolution: lock Anton.**
Rationale: §40 is the sub-brand authority and carries the load-bearing *voice rule*; Stitch
independently chose Anton; the owner preferred that hero. **Action required:** align
`story_card_renderer.py` `--font-display` (Bebas → Anton) and amend [[41-player-story-card]] §3.

| Layer | Face | Rule |
|---|---|---|
| Verdict / hero number (the BAN, the player name) | **Anton** (1 weight, subset, preload) | all-caps, tight tracking. ≤3-word takes + single big numbers ONLY — never tables, stats, sources, or confidence labels |
| Editorial — logline, tension, recap, quote | **Source Serif Pro** (+italic) | mixed-case, never all-caps. The "novelistic" layer |
| Body / UI / all stat numerals | **Inter** | `font-feature-settings:"tnum"`. Bold Inter for sub-headlines (not Anton) |
| Receipts — n=, window, source, citation, timestamps | **IBM Plex Mono** | min 12px, weight 500 |

**The voice rule is typographic and binding:** _Anton = a take · Serif = the narration · Mono = the evidence._

---

## 4. Scope (the one decision flagged for confirmation)

The player page renders inside a single **`.theme-noir`** wrapper — i.e. the **entire player-page
route is Noir, end-to-end** (hero → narrative → the stat Record → footer). This is consistent
with [[40-noir-subbrand]]'s "scoped wrapper, not a site-wide flip": it scopes Noir to *one route*
that is itself a fan/narrative surface, which is exactly what the rejected option ("flip the whole
site") was not. ⚑ **Confirm:** full-Noir player route (locked here) vs. main-site chrome with only
the narrative modules in Noir. Everything below assumes full-route Noir.

---

## 5. The format is adaptive — the `composition` array is the contract

The page SHAPE is **data-driven**, not hand-laid (the principle from [[42-player-narrative-engine]]
§4b, already shipping). Each player's cached card carries an ordered `composition` manifest +
`archetype_slug` + `tier_rail` + `ledger_lead` + `ban.kind` + `succession.shoes_read`. The renderer
**emits modules in that order, and only those present** — different archetype ⇒ different page.

Verified live (`player_story_card_cache`): Transfer-Saga (Nico) carries `dominant_take`+`tension`+
`succession`; Cornerstone (Arch) drops `dominant_take`; Quiet-Workhorse (Rocco) drops `succession`
and rails **bronze**; Filling-the-Shoes RB (Ahmad) flips the BAN to a rushing-WEPA value and lights
the **Clock**. The locked rule: **modules appear/vanish/reorder by salience; missing data hides a
module — it is never fabricated and never shown as `--`/"Awaiting".** (This is the Stitch
de-cluttering win and [[41-player-story-card]] §5/§6, unified.)

**Tier rail (texture, §2 carve-out):** S = gold `#ECC15C→#FFCB05` · T1 = silver `#C7CBD1` ·
T2 = bronze `#B08D57` · T3 = flat hairline (the low-data factual strip).

---

## 6. The spine — one tension carried top to bottom

The page is a story, not a gallery. The **BAN is the spine**: the single most surprising-yet-honest
number, stated once as the hero and echoed by the modules that prove or complicate it. BAN color
follows §2 by **kind**:
- **perception/aura gap** → `--noir-aura` violet (✦) — "the hype is ahead of the tape."
- **production value** (WEPA, a rate) → up/down by sign, or chalk if neutral.
- **rank / rarity** (leader stat, achievement) → chalk number + tier-gold accent.

**BAN enrichment — DONE (2026-06-12, `story_card._select_ban`).** Canonical algorithm spec is now
[[41-player-story-card]] §6.1 (this is the synthesis mirror; 41 §6.1 is authoritative — keep them in
sync). The candidate pool is tiered, so the BAN is the highest-priority *register* present, then the
top score within it — enforcing the brand hierarchy structurally instead of interleaving ad-hoc
float scores (which let pedigree outscore proprietary production):

| Tier | Register | Accent | Sources |
|---|---|---|---|
| 1 · NATIONAL | rarest, most legible national distinction | rank / aura | `money_efficiency` (#N YPA leaderboard) · `dual_threat` · **extreme** aura gap (≥25 pctl) |
| 2 · PRODUCTION | the proprietary moat metric + notable gaps | production / aura | **WEPA** · moderate aura gap (12–25) · `mirror_elite` |
| 3 · VOLUME | national counting-stat milestone (legible but vanilla) | rank | `volume_king` (cleared the 2,500/1,200/900-yd bar) |
| 4 · PEDIGREE | recruiting rank — honest hero **only for unproven players** | rank | `player_recruiting_profiles` |
| 5 · TEAM | last resort | rank | `program_benchmark` (team-relative leader) |

Achievement source of truth = `player_achievements` (real detectors in `bets/achievements.py`);
`rarity_pct` there is a pool **percentage** (0–100), so `rarity = 1 − rarity_pct/100`. **Honors
badges are excluded** — categorical, no honest single number; they live in the selector grid.

> **NIL valuation: never a hero/narrative number (owner rule, 2026-06-12).** The On3
> `valuation_usd` / `whisper_usd` is a *modeled estimate* (social reach, not paid $). It is fine as a
> clearly-LABELED stat (the live `nil_draft.py` card is ok'd), but it must NEVER be a BAN, a hero
> number, or a narrative "worth $X" claim — that reads as a salary it isn't. So
> `player_nil_valuations` is not a BAN candidate (a built-then-reverted MARKET tier is the record;
> do not re-add). The NIL *story from fan discourse* is the allowed register (see `packet.py`).

**Accent (`Ban.accent`)** makes §2 color-by-register real: `aura`→`--noir-aura` violet ·
`production`→up/down by sign · `rank`→chalk + tier-gold. The selection layer tags it; renderer
wiring is the remaining §9 reconciliation step.

**Effect on the 52 cached S/T1 cards:** every veteran-with-production shows production (Miller Moss
`No.76 4★ → +0.21 WEPA`; Diego Pavia `+0.60 WEPA → No.3 9.4 Y/A`); pedigree survives only on
genuinely unproven players. The BAN feeds `story_content_hash`, so a flipped BAN correctly marks
cached LLM prose stale → ships honest deterministic prose until nightly `compute-story-cards`
regrounds it. Tests: `tests/test_player_ban_selection.py` (17).

**Bespoke-concept verdict (2026-06-12 — pressure-tested vs real data, all REJECTED as BANs):**
the BAN candidate pool is **saturated**; the bespoke fan-discourse/succession moat belongs in the
MODULES below the BAN, not in the single hero number. Don't re-attempt these as BANs without the
noted data fix:
- **The Feeling** (dominant emotion share, `player_week_conversation_features`) — REJECTED: the
  emotion classifier is degenerate (dominant = JOY in 86/91 well-sampled players, median top-share
  0.94). "94% JOY" is an artifact, not a feeling. Needs a real multi-class emotion model first.
- **Villain Index** (rival-vs-own mention ratio) — REJECTED: only 5 players clear a both-buckets
  volume floor, all with rival < own; and mention_count is author-inflated (Arch's 159 own-fan
  mentions = 5 unique authors). Needs discourse BREADTH (unique-author floor + real rival coverage)
  — i.e. the in-flight source-expansion work. Confidence is `thin` on 2138/2334 rows.
- **The Inheritance** (predecessor workload, `player_succession`) — built + REJECTED: data is
  reliable (`predecessor_usage` verified = QB pass-att / RB carries / WR-TE receptions), but it
  fires for 0/94 notable-predecessor players — every successor who replaced a workhorse has already
  played, so their own tape (production tier) rightly leads. Also it's the *predecessor's* number,
  not the player's → wrong layer. The succession MODULE already tells this story; keep it there.

**Belief momentum** needs a weekly time series to accrue first (aura is single-snapshot today).
**Still untested-but-plausible:** `active streak` (`player_game_stats`) · `margin of leadership`
(gap-to-#2) · `position percentile`. **Net-new / do-NOT-fabricate:** PFF grades, forced missed
tackles, YAC, pressures, big-time throws, Total QBR (WEPA is the honest analog); **NIL valuation**
(modeled estimate — owner rule, see above).

---

## 7. Page scaffold + module catalog

Fixed page scaffold (the scaffold is constant; module *presence* inside it is by §5 salience):

```
NOIR ROUTE  (.theme-noir)
1  HERO            identity · headshot · eyebrow(pos·team·class·#) · scorecard(≤4 real stats)
2  THE DOSSIER     the Story Card — renders the composition array:
                   chapter · logline · BAN(spine) · chips · dominant_take · tension · recap ·
                   succession · why_now · kicker · receipts · AI disclosure
3  SHOWCASES       archetype-selected, by salience:
                   · THE THRONE (succession: lineage + Filling-the-Shoes + Clock + portal chains)
                   · THE TRIBUNAL (Home/Rival/National lens + the 5 fan ledgers + confidence)
                   · IN THEIR WORDS (fan-vocabulary fingerprint, violet)
4  THE HEARTBEAT   season-as-EKG (per-game pulse) · career arc spark · why-now · countdown
5  THE RECORD      traditional-first stat line (percentile bars) · game log (all rows) ·
                   splits · advanced savant · peer mirror
6  VERDICT         the kicker — pays off the spine
7  FOOTER          methodology · freshness · masthead
```

Per-module treatment (Noir grammar, [[40-noir-subbrand]] §4 — verdict/body/receipt; one emotion per card):
- **Receipts are mandatory and never decorative** — every dramatic claim carries `src · table` in mono.
- **Confidence meter** on every compiled fan take (the honesty mechanism); low confidence reads "the room is split," below the floor → no take.
- **Meters use the Backometer zones** (SO BACK / COOKING / UNEASY / COOKED / IT'S SO OVER, §40 §5) where a 0–100 belief/sentiment is shown.
- **Percentile bars are the only bar chart** (single rail + fill + pin); no pies, no radar (except a future QB fingerprint), no vertical bars ([[31-chart-vocabulary]]).

---

## 8. Motion (disciplined — [[41-player-story-card]] §8.5, binding)

**1–2 animated elements per viewport, max.** The BAN is the single thing that animates on entrance
(magnitude counts up ≤900ms; rank spring-settles); the S-tier rail does a one-time sweep;
everything else is **static** (static = reads as fact). Tribunal POV toggle cross-fades ≤300ms; the
Heartbeat EKG draws once. No ambient loops, no parallax. `prefers-reduced-motion` → everything snaps.

---

## 9. Build mapping (design ← data ← renderer) + reconciliation actions

| Surface | Renderer | Data |
|---|---|---|
| Story Card (Dossier) | `story_card_renderer.py` (`.psc-*`, `STORY_CARD_CSS`) | `player_story_card_cache.card_json` |
| Composition/archetype | `story_card.py` (`_classify_archetype`, `_composition_order`) | engine |
| Throne | `succession.py` | `player_succession` |
| Tribunal / ledgers | `ledgers.py` | `player_ledger_scores`, lenses |
| Record (stats/log/splits/savant/peers) | `reporting.py` player modules | `player_season_stats`, `player_game_stats`, `player_value_metrics`, … |

**Reconciliation actions this lock requires:**
1. `--font-display`: Bebas → **Anton** — **DEFERRED.** `--font-display` is a *global* token (the renderer only references it with a `'Bebas Neue'` fallback; no `@font-face` here). Switching it is a site-wide font-load change (Anton must be loaded globally) + visual sign-off — not a renderer-local edit. Hold until the global font system + a screenshot review are done together. Amend [[41-player-story-card]] §3 then.
2. **DONE (2026-06-12).** BAN ink is now **color-by-register** in `story_card_renderer.py` (`_render_ban` emits `data-ban-accent` + `data-ban-dir`; CSS maps `aura`→violet `#B794FF`, `production`→up `#2EE07C`/down `#FF4E42` by sign, `rank`/default→gold). Driven by `Ban.accent` from the selection layer. Verified by screenshot. (The broader aura *module* recolor + full `.theme-noir` token migration is action 3.)
3. Wrap the player-page route in `.theme-noir` and retire the ad-hoc inline-styled Aura block (the hardcoded `#101418/#B794FF` module) in favor of tokenized Noir.
4. Enforce empty-module suppression site-wide on the player page (no `--`/"Awaiting").

---

## 10. Locked vs. open

**Locked:** Noir palette + accent semantics · Anton/Serif/Inter/Mono voice rule · **`.theme-noir`
route scope — CONFIRMED 2026-06-12: the FULL player route is `.theme-noir`** (it scopes Noir to a
single already-narrative route, which is exactly the "scoped, not site-wide" intent — the rejected
option was flipping the *whole site*) · adaptive `composition`-array format · the BAN-as-spine + its
color-by-kind · the page scaffold · motion budget · receipts + confidence everywhere · empty-state
suppression.

**Done:** **BAN enrichment** (tiered candidate pool, §6) · **BAN accent color-by-register** in the
renderer (§9.2) · **tension de-templating** · **`dominant_take` de-templating** (2026-06-12: 3
attributed variants per ledger, per-player selection, grudge rival-voiced and free of the banned
"roots for theirs" stock phrase; `_TAKE_POOLS` in `story_card.py`, pinned by tests).

**Open (next), with judgment calls:**
- **`.theme-noir` route migration + Bebas→Anton font** (§9.1/§9.3) — DEFERRED on purpose: both are
  global/visual changes that need the font system touched + a screenshot-reviewed pass, and the box
  is staging a deploy. Do them together after the deploy settles, not piecemeal mid-flight.
- **Empty-state suppression** (§9.4) — already satisfied on the Story Card crown (the renderer drops
  empty modules). Remaining: a separate audit of the legacy "Record" modules in `reporting.py` for
  stray `--`/"Awaiting" (note: the fan-intel "Awaiting Signal" fallback is intentional, not a bug).
- **Home/Rival lenses** — BLOCKED on discourse breadth, not effort: the rival `audience_bucket` is
  too thin/author-inflated to generate an honest rival voice today (same data gap that vetoed the
  Villain Index, §6 roadmap). Unblocks with the source-expansion work.
- **High-risk-discourse gate scan** — parked by owner.

---

## 11. Provenance

Synthesis of the Stitch exploration (3-batch + adaptive engine renders on real
`player_story_card_cache` data, 2026-06-12), the locked Noir/Story Card/narrative specs
([[40-noir-subbrand]]–[[44-succession-engine]], [[47-fan-ledger-detectors]]), and the shipping
engine code. Resolves the Anton-vs-Bebas and gold-vs-violet cross-spec conflicts and the
full-route-Noir scope question. Tension de-templating landed in `story_card.py` the same day.
