# 61 — Player Page → Noir Dossier: Migration Plan

_Status: SCOPING (2026-06-13). No live code changed yet. Synthesizes the current-state map, the target spec ([[60-player-page-master]] §7), and two octopus expert passes (frontend-architecture + ui-ux module-mapping). Approve before any build._

---

## 0. The problem (verified)

The live player page **does not match the spec design** — and not subtly. Evidence:
- `.psc-card` (Noir Story Card module): on **37,111 / 37,116** live pages ✓
- `.theme-noir` (the Noir route): on **0 / 37,116** ✗

What's live is the legacy `render_player_page_html` (`reporting.py:19495`, ~850 lines) — a **~45-section module dump**. It is *dark-mode already* (`--pp-*` oklch tokens, L≈0.18) but **NOT the Noir token/scaffold system**, and the Noir Story Card is one dark island injected among ~40 other modules. The spec ([[60-player-page-master]] §7) is a disciplined **7-section Noir Dossier** wrapped in `.theme-noir`. So the gap is a *reorganization + retokenization*, not a re-skin.

> Nuance: "wrap in `.theme-noir`" is **not** light→dark (the page is already dark). It's adopting the Noir **semantic-accent token system** (violet=perception, green/red=production, blue=market, gold/silver/bronze=tier texture) + the 7-section scaffold + the Anton/Serif/Inter/Mono voice rule, in place of the current `--pp-*` percentile/belief ramps.

---

## 1. Architecture — parallel renderer (the team-pages pattern). DO NOT edit `render_player_page_html`.

In-place conversion of the 850-line monolith is a rewrite disguised as an edit (high blast radius, no clean rollback). The **team pages already proved the safe pattern** at this exact seam. Reuse it 1:1.

- **New package** `src/cfb_rankings/player_pages_noir/`: `render_noir_player_page(summary, player_data) -> str | None`, `layout.py` (the 7-section `.theme-noir` shell + adaptive composer), `sections/`, `css.py` (`_noir_player_css()`, fully `.theme-noir`-scoped), `eligibility.py` (rollout gate). Returns `None` (never raises) when a player isn't Noir-eligible → caller falls back to legacy.
- **Short-circuit** inside the existing render loop (`reporting.py:7090`, already per-slug try/except at 7094):
  ```python
  html = None
  if _noir_enabled(player_slug, player_data):
      html = render_noir_player_page(summary, player_data)   # None => not eligible
  if html is None:
      html = render_player_page_html(summary, player_data)   # legacy, untouched
  (players_dir / f"{player_slug}.html").write_text(html, encoding="utf-8")
  ```
- The delete-sweep at `reporting.py:7082` already clears every player's HTML each build → **no stale-legacy-file hazard** (unlike the team migration's Cincinnati incident). Both renderers write the same flat path `players/<slug>.html` — cross-links and canonical URLs are invariant.
- The Noir primitives **already exist** as a package (`player_pages/`: story_card, story_card_renderer, in_their_words, ledgers, succession, standing_rail, mirror_match). The Noir renderer is mostly *composition + chrome*, not net-new module logic.

---

## 2. The 45 → 7 mapping (consolidated)

> **PRESERVATION RULE (owner, 2026-06-13) — binding.** This migration **reorganizes; it does not delete.**
> The legacy renderer (every one of the 45 modules) stays the **default + a permanent fallback** behind the
> `NOIR_ROLLOUT_TIER` kill-switch. **No module is retired or merged-away without explicit, per-module owner
> sign-off.** The "retire/merge" dispositions below are a *proposal to review*, not decisions. Default
> posture = **keep everything, just place it well**. In particular, everything built in this session — the
> BAN tier model, the streak, the color-by-register accent, the de-templated tension + dominant-take — is
> the **Dossier spine (Section 2)**, the centerpiece of the design, never a cut candidate.

Target scaffold ([[60-player-page-master]] §7): **Hero · Dossier · Showcases · Heartbeat · Record · Verdict · Footer.**

| Target section | Absorbs (current modules) | Retires / merges |
|---|---|---|
| **1 HERO** (identity · tier rail · ≤4 real stats) | phase-banner, status-strip, bio-tabs, standing-rail→tier texture | Profile archetype forbids dashboard-density hero — outlook/qb-fingerprint grids leave the hero |
| **2 THE DOSSIER** (the Story Card) | story_card (IS the section), signature-story, narrative-arc, outlook-2026→`why_now` | the "quadruple narrative surface" collapses into the composition array |
| **3 SHOWCASES** | THE THRONE (succession, where-ended-up, recruiting, transfer, coaching-lineage, roster-timeline) · THE TRIBUNAL (the Room, aura→violet, rival-radar, heisman-lens→market-blue) · IN THEIR WORDS | the Room/ledgers consolidate; rival lens = LOW-SIGNAL until discourse breadth (§ blocked) |
| **4 THE HEARTBEAT** (season EKG) | career-arc + dev-trajectory → one career spark; heisman-trajectory → EKG sub-trace; this-day, season-context → why-now pins | the "triple trajectory cluster" consolidates |
| **5 THE RECORD** (traditional-first) | current-season production, game-log, splits, season tables, advanced metrics, box-savant, pass-profile, qb-fingerprint (the one allowed radar), peer-comparator + mirror-match → one peer-mirror, selector-grid + trophy-case + honors-timeline → one honors shelf, nil-draft (labeled estimate) | the "honors triple" + "peer/mirror pair" consolidate |
| **6 VERDICT** (the kicker) | Story Card `kicker` slot, pulled to a full-bleed section | suppressed for T3 factual-strip cards |
| **7 FOOTER** | change-log, profile-meta | — |
| **PROPOSED to retire — needs owner sign-off** | only true placeholders/duplicates/empties: signal-flow bar (placeholder, no data source), live-signal-flow (placeholder), Player Standing Detail (#34 = literal duplicate render of the hero rail #10), supporting-cast (no data today), scenario-explorer (→ keep as a conditional QB/in-season sub-panel, not removed) | NOT a decision. Each requires explicit approval. Anything not approved is **kept** and placed in a section. |

Net result if approved: **45 sprawling sections → 7 sections / ~15 distinct zones**, all adaptive (a module with no data **hides** — no `--`/"Awaiting"). **No module's CODE is deleted** — the legacy renderer retains all of it as the fallback. "Merge" means *render in the same Noir section*, not *delete the module*.

---

## 3. Net-new vs reusable

**Net-new** (don't exist today): the **Season EKG** (center-baseline per-game oscillator + event pins + Heisman sub-trace — the marquee Heartbeat viz); the **tier-rail-into-hero** integration; the **`.theme-noir` full-route wrapper + Anton load**; the **Home/Rival/National POV toggle** (TRIBUNAL); the **LOW-SIGNAL designed state**; the **VERDICT** full-bleed section.

**Reusable as-is / minor recolor:** story_card(+renderer) — the Dossier core, BAN accent already wired (2026-06-12); succession → Throne; ledgers → Tribunal; standing_rail → hero tier; coaching_lineage, career_arc, heisman_trajectory, selector_grid, mirror_match, box_savant, splits, game-log, percentile bars, change_log.

---

## 4. Rollout (each gate passes before advancing)

| Phase | Cohort | Gate |
|---|---|---|
| **0 Spike** | 1 hand-picked player, **local scratch dir only** | visual sign-off · `<head>` (canonical/title/OG) byte-identical to legacy · renders under both `is_offseason()` states · both required markers present |
| **1 Alpha** | the ~52 `player_story_card_cache` players, **full local build** | new guard green · zero hollow pages · build-time delta in budget · no legacy/Noir CSS cross-contamination |
| **2 Beta** | top ~100 by Heisman rank, **first prod deploy via normal full `build_publish.ps1`** | 48h clean `live_smoke_test` (add 2–3 Noir URLs) · SEO/OG spot-check 5 pages |
| **3 GA-FBS** | all FBS-rostered | full build green · smoke green · no render-error spike |
| **4 GA-all** | 37,116 · legacy decommission as a separate later PR | ≥2 weeks GA-clean · kill-switch tested once |

**Gate mechanism:** one `_noir_enabled(slug, player_data)` = env control (`NOIR_ROLLOUT_TIER`, `NOIR_PLAYER_SLUGS` allowlist) **AND** `is_noir_eligible(player_data)` (a **minimum-viable-section floor** — if hiding empty modules would leave a hollow page, render legacy instead). Cohort for the guard is resolved by the **same** function (single source of truth). Kill-switch: `NOIR_ROLLOUT_TIER=off` → next full build is 100% legacy, no code revert.

---

## 5. CSS / tokens / fonts

- New `_noir_player_css()`, **every selector nested under `.theme-noir`**; `--noir-*` declared on `.theme-noir`, never `:root` → no leakage into the other ~69k pages. `_player_pages_v2_css()` stays **untouched** (legacy pages still use it; the two never co-occur).
- Reused primitives stay theme-agnostic; the wrapper repaints them via aliases (`.theme-noir { --pp-accent: var(--noir-aura); }`).
- **Anton**: `.theme-noir { --font-display:'Anton',… }` — overrides global Bebas **only in the Noir subtree**; the global token is not touched ([[60]] §9.1 stays "no global swap").
- Motion: `@media (prefers-reduced-motion: no-preference)`, structurally capped to 1–2/viewport (hero element + EKG one-time draw).

---

## 6. Guardrails

- **Keep `verify_world_class_player_pages.py` green:** Noir must still emit `data-module="player-standing"` + `data-module="mirror-match"` (reuse `standing_rail.py`/`mirror_match.py` verbatim → markers guaranteed). The guard is marker-based and renderer-agnostic — no change needed.
- **Add `scripts/verify_noir_player_pages.py`** (mirror of `verify_world_class_team_pages.py`): for the active Noir cohort assert the page is `.theme-noir` + a `data-noir-route` sentinel + has NO legacy-only shell marker + still has the required markers (defense in depth). Fail loud on a cohort slug that shipped legacy or is missing. Wire into the same post-build verify step as the team guard.

---

## 7. Risk register (top items)

R1 **Full-snapshot box deploy clobbers partial renders** → Noir ONLY rides the normal full `build_publish.ps1`; spike/alpha verified on a **local scratch build**, never `publish_to_vercel`.
R2 **Build-time at 37k** → Noir renders from precomputed `player_data` only; **zero LLM/DB calls** inside `render_noir_player_page`; benchmark on the 100-page beta.
R3 **Hollow adaptive pages** (the dominant Noir-specific risk) → `is_noir_eligible` minimum-section floor; below it, render legacy; guard asserts ≥N `data-module` markers.
R4 **Offseason reorder divergence** → bake `is_offseason()` into the composer's salience from Phase 0; test the spike under both states.
R5 **Required-marker regression** → reuse the exact standing_rail/mirror_match renderers; both guards assert presence.
R6 **`new_*_html` contract drift** → Noir consumes the same `… or legacy_fallback()` contract; missing key hides a section, never crashes (per-slug try/except contains stragglers).
R7 **`--noir-*` leakage** → tokens on `.theme-noir` only; separate stylesheet; guard greps for no cross-contamination.
R8 **SEO/canonical churn** → Noir `<head>` copies legacy canonical/title/description/OG verbatim; path unchanged; diff `<head>` on the spike.
R9/R10 **Flat path + `player_id`/slug instability** → path invariant; resolve cohort by the live-DB slug construction at build time, never a persisted allowlist (except spike).
R11 **Rollback** → `NOIR_ROLLOUT_TIER=off` kill-switch; keep legacy renderer in-tree through GA+N.

---

## 8. Recommendation + next step

Proceed in **Phase 0 (Spike) only**, local scratch dir, **no live changes** — build the `player_pages_noir/` skeleton + the 7-section `.theme-noir` shell, render ONE real marquee player, screenshot, and review against this plan + the spec. Everything past Phase 0 gates on that sign-off. Legacy stays the default until Phase 4, behind a kill-switch the whole way.

**Owner decisions before Phase 1:** (a) the Anton font swap (deferred [[60]] §9.1) — Noir-scoped only, so lower risk than a global swap, but still wants a screenshot review; (b) the rollout cohort order above; (c) whether the legacy renderer is retired (Phase 4) or kept as a permanent fallback.
