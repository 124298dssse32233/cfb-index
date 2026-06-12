# Team Story Card ("The Marquee") — UI/UX Design Handoff

_Created 2026-06-11 via `/octo:design-ui-ux` from the locked spec [[50-team-story-card]] (critique-hardened v2) + the locked design system ([[00-tokens]], [[40-noir-subbrand]]). Companion to the working mockup `docs/octopus/mockups/team_story_card_mockup.html`. Design/handoff artifact — no live code changed._

---

## 0. The sub-brand reconciliation (the one design decision)

The repo has **two sibling dark sub-brands**, and the crown has to pick:

- **"Group Chat Noir"** ([[40-noir-subbrand]]) — the fan-conversation *share-card* suite: Anton + IBM Plex Mono, green/ember/violet **semantic** accents, `#101418` ground. Scope: Backometer / Aura / Rent Free / Delusion + share cards.
- **"Dossier Noir"** ([[41-player-story-card]] → [[50-team-story-card]]) — the *story-card* family: the **core 00-tokens type stack** (Bebas Neue + Source Serif 4 + Inter), a **gold** editorial accent, `#0A0A0D` ground.

**Decision:** the Team Story Card is a Profile/Tentpole *page* element on the team page (the light editorial shell), so it uses the **Dossier-Noir / 00-tokens** palette and type stack — and borrows **only Noir's semantic delta accents** (so-back green / cooked ember) for the belief/mood signal (the confidence meter, the Flip-Point shift line). It does **not** adopt Anton/Plex Mono. This keeps the crown consistent with the player Story Card and the locked core type tokens, while the Group-Chat-Noir share-card render of the same data stays a separate surface.

---

## 1. Design tokens (the crown's subset)

```css
/* ground + surface (Dossier Noir) */
--tsc-ink-900:#0A0A0D;  /* page ground */
--tsc-ink-850:#101015;  /* BAN well / inset */
--tsc-ink-800:#16161C;  /* card surface */
--tsc-hairline:#2A2A33;  --tsc-hairline-strong:#3A3A45;
/* text */
--tsc-text-hi:#F4EFE7;   /* logline, name      ~13.9:1 on surface */
--tsc-text-body:#DAD4C9; /* serif prose        ~10.4:1 */
--tsc-text-mut:#ABA59B;  /* meta, receipts     ~6.0:1 (AA at ≥12px) */
/* editorial accent */
--tsc-gold:#ECC15C;      /* BAN, confidence bars, buttons, focus ~9.7:1 */
/* borrowed Noir SEMANTIC deltas (mood/belief only, never decoration) */
--tsc-up:#2EE07C;        /* SO BACK / positive Flip Point */
--tsc-down:#FF4E42;      /* IT'S SO OVER / negative shift */
--tsc-neutral:#A8A294;
/* per-team identity color: ring + 1px rule ONLY, luminance-clamped */
--tsc-team:/* injected at render */;
```

**Contrast (verified, WCAG):** all text pairs ≥ AA (hi 13.9:1, body 10.4:1, muted 6.0:1 at ≥12px, gold 9.7:1). Text on a gold/accent chip is `#0A0A0D` near-black (chalk-on-gold fails AA — matches [[40-noir-subbrand]] §3.2). Team color is **identity only**, never a data value; clamp to a safe luminance band (some team navies/crimsons collide with `--tsc-up`/`--tsc-down`).

## 2. Typography (core 00-tokens stack)

| Layer | Face | Use |
|---|---|---|
| BAN (the one big number) | **Bebas Neue** | the stat object only — `tnum`, never a sentence |
| Logline · tension · quote · "PREVIOUSLY ON" beats | **Source Serif 4** (incl. italic) | mixed-case, novelistic |
| Identity · eyebrow · chips · meta · confidence label · buttons · receipts | **Inter** | `font-feature-settings:"tnum"` on all figures |

Self-host subset woff2, `font-display:swap`, preload the two content faces (mockup uses Google Fonts for convenience only).

## 3. Component inventory + state variants

| Component | States |
|---|---|
| **Mode rail** (4px) | rivalry-peak · standard/hype · autopsy · neutral/quiet — keyed off `state_resolver.accent_key` ([[54-integration-with-live-team-system]] §2) |
| **Identity anchor** | team-ring (clamped) · flat (Quiet State, no ring) |
| **Lens toggle** | Home (default) · National (indexed H1) · Rival — segmented, `aria-pressed`; absent when only one lens clears the floor |
| **Eyebrow + freshness** | lens-variant eyebrow · freshness stamp (`as of` / `snapshot from this morning` / `developing`) |
| **Logline** | present (`active`/`standing`) · absent (`quiet`) |
| **BAN** | present (gated stat object) · absent (no candidate clears the honesty gate) · cedes to utility number on a quiet day |
| **Tension / stakes** | present · absent |
| **Confidence meter** | high (4–5 bars) · medium (split) · low ("the fanbase is split") · absent (Quiet State — "Limited signal") |
| **Afford row** | Read ⌄ (expand) + Schedule ↓ |
| **Expanded** | "PREVIOUSLY ON" · supporting threads · quote · path/stakes · ↻ shifted · AI footer |
| **Quiet-State card** | flat rail · standing sentence · "Limited signal" · motionless |

The lead block is **moment-dependent**: which of the six characters fills logline + BAN is the resolver's call ([[51-team-narrative-engine]] §3). The mockup shows three: Michigan (rivalry leads, in-season), Alabama (era/Standard leads, offseason Standing Lead), Akron (Quiet State).

## 4. Responsive

Mobile-first single column, card width clamps 340–392px; collapsed card is a **content budget** (server-side char caps), not a CSS height — clears the fold on a 667px phone. Desktop: the crown sits in the team-page hero column at the same max width (it is a lead, not a full-bleed dashboard); the modules below it are the evidence locker. Touch targets ≥44px (Read / lens / Schedule). One DOM tree; the lens swaps `data-field` text only.

## 5. Motion budget (disciplined)

1–2 animated elements per view max. **The BAN is the single numeric hero** that animates (a 0.5s rise on entrance); everything else is static so it reads as fact. The expand uses `grid-rows 0fr→1fr` (intrinsic height). `prefers-reduced-motion: reduce` → snap instantly; the Quiet-State card is motionless always. No ambient loops, no glow.

## 6. Accessibility verification

- Contrast pairs all ≥ AA (§1); muted never below 12px.
- Lens = real `<button aria-pressed>` group; expand = `<button aria-expanded aria-controls>` (mockup; production uses `<details>/<summary>` SSR baseline, [[50-team-story-card]] §9).
- Visible 2px gold focus ring; icon-only buttons carry `aria-label`; an `sr-only` summary leads the widget.
- Color-never-alone: the Flip-Point shift uses ▲/▼ direction + the word (SO BACK / IT'S SO OVER), not hue alone — CVD-safe, per [[40-noir-subbrand]] §3.2.
- Receipt density ≥1 source marker / 200 words ([[32-receipt-pattern]]): quote attribution, "3 sources," BAN gloss, report-an-error.

## 7. Critique pass (adversarial — issues to resolve before build)

1. **The rivalry rail is a gradient** (gold→ember) in the mockup — that flirts with the "no gradients / color is semantics" Noir rule ([[40-noir-subbrand]] §3.2). **Fix:** ship a **solid** mode rail + a small mode glyph/word in the eyebrow (RIVALRY WEEK) carrying the semantics; keep gradient out of production.
2. **Lens discoverability** — a 3-segment toggle reads as a filter; a rival fan may not realize "Rival" shows their own gloat view. **Fix:** label the default state ("Home ▾") and consider a one-time affordance hint; confirm the indexed H1 is the National lens ([[50-team-story-card]] §10 owner call).
3. **BAN as a record (`58–52–6`)** is wider than a single digit — verify the Bebas line doesn't overflow on a 320px phone; the spec now permits a **stat object**, not one digit ([[50-team-story-card]] §7), so the renderer must wrap the gloss, not the number.
4. **Gold everywhere** — gold rail + gold BAN + gold buttons risks monotony across 119 cards; the **lexical-injection / archetype tone** layer ([[52-cfb-team-content-model]] §9.5) is what keeps them distinct, not color. The visual system is deliberately restrained; differentiation lives in the words.
5. **Two dark sub-brands on one page** — a Group-Chat-Noir share card and the Dossier-Noir crown can co-exist on the team page; confirm they read as a deliberate family, not a clash (different accent, same ground family).

## 8. Mockup

`docs/octopus/mockups/team_story_card_mockup.html` — standalone, three states, the Home/National/Rival lens toggle + expand, real token values, no build dependency. Open in a browser for full fidelity.

## 9. Provenance

Designed within the locked system ([[00-tokens]], [[40-noir-subbrand]], [[31-chart-vocabulary]], [[32-receipt-pattern]], [[33-confidence-signaling]]) from the v2 spec [[50-team-story-card]]. BM25 design-intelligence search was not used — the token system is locked, so this is design *within* fixed tokens, not discovery of new ones. Mirrors the player Story Card handoff intent.
