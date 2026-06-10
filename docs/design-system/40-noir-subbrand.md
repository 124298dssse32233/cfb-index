# 40 — "Group Chat Noir" Sub-Brand (Fan Conversation Suite)

_Drafted 2026-06-10 via three-provider design shotgun (Codex / Gemini / Claude) + three-way adversarial critique. Status: PROPOSED — requires Window A/B sign-off before implementation. This is an ADDITIVE sub-brand; it does not modify `00-tokens.md` or the locked archetypes._

## 1. Thesis

The real competitor isn't ESPN — it's the screenshot folder. Every Noir surface is a
self-sufficient screenshot designed to be cropped into a dark-mode group chat at 11:48pm
and win an argument without the sender typing a word. "Meme on top, receipt underneath"
is enforced *typographically*: the take is set in a display face, the evidence in mono.

## 2. Scope rule (the most important rule in this doc)

Noir applies ONLY to:
- The four fan-conversation stat surfaces: **Backometer, Aura/Him Watch, Rent Free, Delusion Premium** (hubs + team/player modules)
- **The Group Chat** daily digest
- Generated **share cards** (always forced-dark, every surface)
- Player-page **vibe modules** (fan-perception cells), embedded as full-bleed "night bands" inside otherwise-light pages

Noir does NOT apply to: rankings tables, methodology, long-form editorial, legacy team/player
chrome. The light editorial system remains the site shell. Rationale (unanimous across all
three critics): dark-first degrades long-form reading and dense tables, full migration of
~69k pages is a regression cliff, and meme packaging on the statistical encyclopedia
erodes data-journalism credibility. A site-wide migration is a separate future decision
with its own token-mapping + visual-regression plan.

Implementation: a scoped wrapper class (`.theme-noir`) carrying all tokens below.
Dense tables inside light pages never embed full SVG modules — CSS-only micro-bars
(single div, width %) + zone dot only. Full charts live on entity pages and hubs.

## 3. Tokens

### 3.1 Ground & text

| Token | Hex | Use |
|---|---|---|
| `--noir-ground` | `#101418` | page ground (never pure black — JPEG banding) |
| `--noir-surface` | `#1B2128` | card surface, one step lifted |
| `--noir-surface-2` | `#242C35` | nested chips, hover |
| `--noir-text` | `#EDE6D6` | primary text ("chalk") — 13.0:1 on surface |
| `--noir-receipt` | `#B8B2A4` | receipt/metadata text — 7.0:1 on surface, min 12px, weight 500, NEVER opacity-muted |
| `--noir-hairline` | `rgba(237,230,214,0.10)` | card borders, rules |

### 3.2 Semantic accents (color is semantics, never decoration)

| Token | Hex | Quarantine rule |
|---|---|---|
| `--noir-up` (So Back Green) | `#2EE07C` | euphoria, wins, positive deltas — events/production only |
| `--noir-down` (Cooked Ember) | `#FF4E42` | doom, losses, negative deltas — events/production only |
| `--noir-aura` (Aura Violet) | `#9D6BFF` | fan-PERCEPTION metrics only (graphic fills/strokes) |
| `--noir-aura-text` | `#B794FF` | violet at text sizes (graphic tier is only 4.6:1 on surface) |
| `--noir-market` (Sharp Blue) | `#3D91FF` | betting-market data only; market lines are ALWAYS dashed + square markers + direct label |
| `--noir-neutral` | `#A8A294` | stable / mixed / informational / UNEASY — the neutral state every accent system needs |

Glyph redundancy is mandatory: ▲ up, ▼ down, ✦ perception, ▪ market. Hue never works alone
(violet vs blue is ~1.1:1 luminance — indistinguishable for CVD users without shape/dash cues).

**Contrast matrix (checked):** chalk on ground 14.9:1 ✓ · chalk on surface 13.0:1 ✓ ·
receipt on surface 7.0:1 ✓ · accents on ground 5.3–10.6:1 ✓ as text, all ✓ as graphics.
**Text on accent-filled chips is `#101418` (near-black)** — chalk-on-accent FAILS AA.
Below 16px, accent colors are restricted to glyphs and numbers, never sentences (halation).
Large area fills use accents at ≤20% opacity with chalk strokes — bright color is reserved
for terminal marks so neon weight doesn't exaggerate movement.

### 3.3 Team colors

Team color is **identity only**: logo chip + optional ≤12% tint header band. It NEVER
encodes a data value. (Oregon green ≈ `--noir-up`, Alabama crimson ≈ `--noir-down`,
TCU purple ≈ `--noir-aura` — letting team palettes into data ink collapses the semantic system.)

### 3.4 Type

| Layer | Face | Rules |
|---|---|---|
| Verdict | **Anton** (1 weight, subset woff2, preload) | ≤3-word zone verdicts + single hero numbers ONLY. Never tables, never stats, never sources, never confidence labels. All-caps, tight tracking. |
| Body/UI | **Inter** (already shipped site-wide) | `font-feature-settings: "tnum"` for all numerals. Bold Inter for sub-headlines — not Anton. |
| Receipt | **IBM Plex Mono** (1–2 weights) | every sample size, timestamp, source, citation. Min 12px web / 16px-equivalent in share images, weight 500. |

The voice rule is typographic: if it's set in Anton it's a take; if it's set in mono it's evidence.

## 4. Card anatomy

Fixed three-zone grammar, with variants:

```
┌──────────────────────────────────────┐
│ VERDICT   zone word / take (Anton)   │  + team identity chip (logo, never color-coded)
│           hero number (Anton, tnum)  │
├──────────────────────────────────────┤
│ BODY      one chart or one quote     │  variants: trend / snapshot / comparison /
│                                      │  quote / LOW SIGNAL / methodology-warning
├──────────────────────────────────────┤
│ RECEIPT   n= · window · sources ·    │  Plex Mono, --noir-receipt,
│           method tag · cfbindex.com  │  corner stamp ALWAYS present
└──────────────────────────────────────┘
```

Every card is self-sufficient: crops don't carry context, so nothing on the page may be
required to interpret a card. Single-column feed on suite pages — one emotion per viewport.
(Trade-off logged: desktop width underused in v1; audience is phone-first at night.)

## 5. Zones (Backometer vocabulary)

| Zone | Range | Color |
|---|---|---|
| SO BACK | 80–100 | `--noir-up` |
| COOKING | 60–79 | `#8FD14F` |
| UNEASY | 40–59 | `--noir-neutral` |
| COOKED | 20–39 | `#F0883E` |
| IT'S SO OVER | 0–19 | `--noir-down` |

- Numeric boundaries are architecture; **zone WORDS are a versioned copy config**
  (`seeds/noir_zone_labels.yaml`), renamable per season via lexicon-tracker review —
  the product literally measures slang lifecycle, so it tells us when "cooked" dies.
- **Hysteresis:** a zone label changes only after the score crosses the boundary by ≥3 pts
  or holds across 2 consecutive weeks — no flip-flopping screenshots at 79↔80.
- Score, n, and distance-from-threshold always appear in the receipt.

## 6. Honest-uncertainty layer (non-negotiable)

Conversation mining is episodic and sample-skewed; the design must not overstate precision:
- **Publication floor:** n < 200 weekly mentions → card renders the designed **LOW SIGNAL**
  state (hatched body, neutral verdict, receipt explains the floor). Never a confident
  verdict on n=12.
- **Uncertainty band** (±1σ chalk @ ~6% opacity) behind the Backometer trace.
- **Visible breaks** in the trace across insufficient-data weeks — never interpolate
  through a gap.
- **Calendar-aware calibration:** offseason weeks are labeled as such; thresholds are
  calibrated per calendar state (talking season ≠ game week).
- **Confidence-gated badges:** emotion/sarcasm badges render only above threshold
  confidence; otherwise absent. Never wrong in public.

## 7. Signature components

1. **Backometer** — "fanbase on a heart monitor." Center-baseline oscillator; green mass
   above / ember mass below (≤20% fills, chalk trace); chyron event pins in mono caps
   (`▼ OCT 11 · LOST RED RIVER`) sourced from wire_entries/calendar_pressure; terminal
   dot; verdict = zone word + score. 5-second read: zone word → season shape as colored
   weight → pins explain why → receipt makes it safe to send.
2. **Rent Free** — two-sided depth/butterfly chart (Polymarket order-book steal):
   mirrored horizontal wings per period, both in violet family (it's perception data);
   asymmetry reads as lopsided wings; verdict states the direction
   ("X LIVES RENT FREE IN ...") + asymmetry chip (3.2×).
3. **Aura gap card** — violet AURA percentile bar vs chalk PRODUCTION percentile bar;
   delta chip = "AURA TAX +23" (violet fill, near-black text). Him Watch = leaderboard
   of deltas with ▲▼ weekly movement.
4. **Delusion Premium** — violet solid line + circle markers (FANS) vs blue dashed line +
   square markers (MARKET), violet gap shading, direct labels at line ends — no legend.
   December payoff: Sharpest Fanbase calibration table.
5. **Group Chat quote card** — StatMuse steal: the card reads as a complete tweet.
   Take headline, real quote, mono attribution. Safety gates: username redaction,
   toxicity/banlist filter, confidence-gated emotion badge, link to context,
   representative-vs-illustrative marking.

## 8. Share-card system

- **One data contract, two render templates** (NOT naive crops): portrait/square web
  module + 1200×675 landscape OG asset with platform-safe margins (≥64px), larger type
  (receipt ≥16px-equivalent), and a baked-in 1px chalk hairline + corner radius so dark
  cards read as intentional objects against white chat bubbles.
- **PNG, never JPEG** (dark gradients band under JPEG).
- Renderer: Python + cairosvg (vibe-shifts precedent), fonts bundled locally (no CDN
  fetch at render time), pinned renderer version, pixel-diff tests on goldens.
- Scope: suite entities only (~130 teams + tracked players, weekly) — never per-page
  for 69k pages; generation stays out of the page-build critical path.

## 9. Accessibility & robustness commitments

- WCAG AA verified per token pair (matrix in §3.2); re-verify on any token change.
- Color-never-alone: glyphs + dash patterns + direct labels everywhere.
- `@media print`: light overrides; charts must survive background suppression.
- Post-v1: `prefers-color-scheme: light` variant for hub pages (tailgate glare);
  share cards remain forced-dark for brand consistency.
- Mobile: minimum chart height, annotation collision rules (pins alternate above/below),
  reduced-detail variants under 480px, native share/download action per card.

## 10. Critique log (what was rejected/kept and why)

- Rejected: site-wide dark flip (all 3 critics — credibility, migration cliff, readability).
- Rejected: IBM Plex Sans as body (Codex — Inter already ships; cuts font bill to 2 files).
- Rejected: literal "share cards are crops" (Codex — safe areas/type sizes differ).
- Kept: forced-dark suite despite tailgate-glare critique (nighttime product; core site
  stays light for daytime) — revisit with analytics.
- Kept: heart-monitor metaphor WITH the §6 honesty layer (uncertainty, gaps, hysteresis).
- Kept: slang zone names, BUT moved to versioned copy config (aging risk is managed by
  the lexicon tracker itself).

## 11. Mockup

Working static mockup: `docs/octopus/mockups/noir_fan_suite_mockup.html`
(all five signature components + LOW SIGNAL state, real token values, inline SVG only).
