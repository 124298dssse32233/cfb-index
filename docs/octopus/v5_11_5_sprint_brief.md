# Sprint v5-11.5 Pre-Work Brief — Dark Mode + Command-K

**Status:** Pre-work audit. Sprint is week-14-15 in the v2-addendum sequencing; no commits to this sprint's deliverables yet.

**Spec:** [`IMPLEMENTATION_PLAN_v2_addendum.md` §"Sprint v5-11.5"](../../IMPLEMENTATION_PLAN_v2_addendum.md)

**Author:** Window B autonomous run (2026-05-18). Captured to give Window A or the next Window B sprint a head-start when v5-11.5 opens.

---

## Part 1 — Dark mode audit (the disconnect)

The site today has **three different theming conventions** in active production, which is the single biggest source of work in the sprint:

### Convention A — Team-pages dark-mode-default

Lives at `src/cfb_rankings/team_pages/assets/tokens.css`. Defines tokens like:

```css
--bg-0: #0b0d12;        /* near-black backdrop */
--bg-card: #171b24;     /* slightly raised card */
--fg-primary: #f5f6fa;  /* near-white text */
--fg-muted: #8a90a1;    /* muted gray */
--accent-primary: #c5b358;  /* per-team override */
```

Used by: `team_pages/`, `canon/`, `hero_findings/`, `mobile/saturday_strip`, `citations/`, `team_pages/rituals_module`. Every Sprint v5-7.5+ module Window B has shipped uses this token system.

**Light-mode override:** none. These pages are dark always.

### Convention B — Design-system mockup tokens

Lives at `docs/design-system/00-tokens.md` + `docs/mockups/_mockup_shared.css`. Defines tokens like:

```css
--color-surface: #faf8f3;       /* bone paper backdrop */
--color-ink: #1c1c1f;           /* near-black text */
--color-surface-card: #ffffff;  /* white card */
--color-line: #d8d3c5;          /* warm tan line */
--color-amber-50: #faeeda;      /* light heritage tint */
```

Used by: the 11 Sprint v5-5.4 mockups (visual reference set) + `mockup_shared.css`. **Not used by any production renderer.**

**Light-mode override:** these ARE the light mode.

### Convention C — Daily/Mailbag/Wire bespoke palette

Lives in `src/cfb_rankings/daily/templates/daily.html` + `src/cfb_rankings/mailbag/` + `src/cfb_rankings/wire/`. Defines tokens like:

```css
--navy: #1a1a2e;        /* navy backdrop */
--cream: #f5f1e8;       /* cream content surface */
--gold: #a8843c;        /* gold accent */
--sans: "Inter"...;     /* font */
```

Used by: Daily, Mailbag, Wire renderers. Half-light / half-dark — masthead is navy/dark, takes-column is cream/light. Distinct from both A and B.

### Convention D — reporting.py shadcn-style tokens

Lives in `src/cfb_rankings/reporting.py:_compose_global_css()`. Defines tokens like:

```css
--background: oklch(0.145 0.005 250);  /* dark */
--foreground: oklch(0.95 0.005 250);
--card: oklch(0.18 0.01 250);
--border: rgba(255, 255, 255, 0.08);
```

Plus a `@media (prefers-color-scheme: light)` override toggling to light values when `html.dark` is present.

Used by: every page rendered through `reporting.py` (rankings, hubs, players, programs not in PROFILED_SLUGS, etc.).

---

## Part 2 — The unification problem

Sprint v5-11.5 says "Full-page dark mode — invert bone paper to warm-ink-dark, keep accent palette." That assumes a single token system that can be inverted. We have four.

Practical paths:

### Path A — Unify on Convention A (dark-default) everywhere

Pros:
* Already the convention for every Sprint v5-7.5+ module
* Tokens are simple (--bg-0/1/2, --fg-primary/secondary/muted)
* Adding a light-mode override is a single `@media (prefers-color-scheme: light)` block

Cons:
* Daily/Mailbag/Wire need replumbed CSS (~6 templates)
* `reporting.py`'s shadcn token names propagate through hundreds of components — bulk rename is risky

Estimate: 5-7 days. The Daily/Mailbag/Wire replumbing is mechanical but touches every rendered template. `reporting.py` is the long pole — its tokens drive hundreds of inline-CSS components.

### Path B — Unify on Convention D (shadcn-style) everywhere

Pros:
* `reporting.py` is the largest renderer surface — keeping its tokens means the smallest rewrite footprint
* Already has the `prefers-color-scheme` switching wired
* shadcn-style tokens (--background/--foreground/--card/--border) are the most-portable naming

Cons:
* Every Sprint v5-7.5+ Window B module needs token renames
* Mockup CSS needs re-derivation from these tokens

Estimate: 7-10 days. Window B's 6 new modules (confidence/hero_findings/mobile/citations/team_pages-rituals/auto_summary) are all freshly built; touching them now is cheap. The bigger cost is mockup-CSS re-derivation + verifying the mockup→prod parity audit still holds.

### Path C — Token-bridge layer (recommended)

Don't unify under one name set. Instead, ship a `tokens-bridge.css` that maps every legacy token to a single semantic token:

```css
/* tokens-bridge.css — readable by every surface */
:root {
  --semantic-bg: var(--bg-0, var(--background, var(--cream, #0b0d12)));
  --semantic-fg: var(--fg-primary, var(--foreground, var(--navy, #f5f6fa)));
  /* ... */
}

@media (prefers-color-scheme: light) {
  :root {
    --semantic-bg: var(--color-surface, #faf8f3);
    --semantic-fg: var(--color-ink, #1c1c1f);
    /* ... */
  }
}
```

Pros:
* No token renames in any existing renderer
* `prefers-color-scheme` handles the switch automatically
* User-preference override hook lives in one place
* Backwards-compatible

Cons:
* Adds an indirection layer
* Components still reference legacy tokens; the bridge doesn't fix the per-renderer divergence — it just makes the dark/light swap work uniformly

Estimate: 3-4 days for the bridge + comprehensive light-mode test pass on all archetypes.

**Recommendation: Path C** for v5-11.5 minimum-viable; defer A/B token-rename to a v5-12 cleanup sprint after launch retro.

---

## Part 3 — Command-K spec

Spec: "search bar overlay (Cmd-K on desktop, dedicated icon on mobile), indexes teams + players + editions + methodology, jump-to-result."

### Search index — what to index

| Category | Source | Approx. count |
|---|---|---|
| Teams | `teams` table (FBS + FCS) | ~700 |
| Profiled programs | `profiles/*.md` | 17 |
| Players | `players` table (active rosters) | ~14,000 |
| Editions | `daily_editions` + `mailbag_issues` + `wire_entries` | ~variable |
| Methodology pages | `/methodology/**/*.html` | ~10 |
| Conferences | `conferences` table | ~32 |

Total searchable items ≈ 15,000. Manageable as a single JSON payload (~500KB-1MB minified).

### Build pipeline

```python
# scripts/build_search_index.py
def build():
    items = []
    items += _index_teams()        # title, url, kind="team"
    items += _index_profiles()     # title, url, kind="profile", tier
    items += _index_players()      # title (last, first), url, team, kind="player"
    items += _index_editions()     # title (long_date), url, kind="edition", date
    items += _index_methodology()  # title, url, kind="methodology"
    items += _index_conferences()  # title, url, kind="conference"
    out_path = "output/site/search-index.json"
    Path(out_path).write_text(json.dumps(items))
```

Output served from `/search-index.json` (HTTP cache-friendly; rebuild on every site build).

### Client component (vanilla JS, no framework dep)

```js
// /assets/cmdk.js
// 1. Cmd-K (or Ctrl-K on Win/Linux) opens a fixed-position overlay
// 2. Fetches /search-index.json once, caches in sessionStorage
// 3. Fuzzy-matches input against item.title (substring + token-prefix)
// 4. Renders top 10 results grouped by kind
// 5. Enter or click navigates to item.url
// 6. Esc closes
```

Foundation work (renderer-only, Window B's lane):
* `scripts/build_search_index.py` — the index builder + CLI subcommand
* `src/cfb_rankings/cmdk/` — overlay HTML/CSS/JS as a static asset module
* Tests for the index builder (counts, shape, no PII leakage)

Integration work (Window A's lane):
* Wire `cmdk.js` + `cmdk.css` into the global header template
* Add the `Cmd-K` icon button on mobile
* Verify the overlay works on every archetype

Estimate: foundation 1-2 days, integration 1 day.

---

## Part 4 — Acceptance criteria for v5-11.5

Per the spec:
* Dark mode on all archetypes — every page archetype (Hub/Article/Profile/Database/Tentpole/Anniversary + Daily/Mailbag/Wire) renders cleanly in light AND dark mode
* Cmd-K indexed across teams/players/editions
* Both pass accessibility (WCAG 2.2 AA minimum) — contrast ratios verified in both modes

Test infrastructure recommendations:
* Add a `scripts/_dark_mode_audit.py` that loads every archetype mockup + flips the theme + screenshots both. Should be a no-regression smoke run before each release.
* Add a `scripts/_cmdk_index_audit.py` that loads the JSON + verifies no PII, no broken URLs, sane counts.

## Part 5 — Risks

* **CSS specificity explosion** — Path A and B both risk cascading-specificity bugs as old token names linger. Path C avoids this.
* **Per-team accent colors in dark mode** — Alabama's crimson (#9e1b32) on a dark backdrop is fine; Vanderbilt's black (#000000) on a dark backdrop disappears. Need a per-team light-on-dark fallback. (Already addressed in `team_pages/profile_loader.py::accent_hex_secondary` — verify it covers every profiled team.)
* **Chart legibility** — the 6 allowed chart types (percentile bar, trajectory spark, bump chart, annotated line, small multiples, heatmap) all need both-mode test. Per the chart-vocabulary spec, this is already on the v5-11.5 acceptance criteria.
* **Daily/Mailbag/Wire's bespoke palette** — these surfaces explicitly chose a print-feel cream/navy aesthetic. The sprint should explicitly decide whether to preserve that ("Daily stays warm-cream regardless of theme") or unify ("Daily flips to dark like everything else"). The mockup set doesn't currently lock either.

## Part 6 — Sequencing recommendation

Week 14:
* Day 1-2: ship Path-C tokens-bridge.css + light-mode override block
* Day 3: per-archetype dark/light audit script + screenshot baseline
* Day 4-5: Command-K index builder + tests

Week 15:
* Day 6-7: Command-K overlay + integration into global header
* Day 8: accessibility verification (WCAG 2.2 AA in both modes)
* Day 9: chart legibility audit + per-team accent fallback verification
* Day 10: launch + monitor for the 10-regression kill criteria

---

## Status of Window B foundation work at brief-publication time

Already shipped + LIVE (no v5-11.5 dependency):
* `rituals_module` — Tier-aware rituals strip on all 17 profiled team pages
* `auto_summary` — 30-second TL;DR on every Daily edition (Pattern 7 wire-up live in PR #122)
* `confidence.py` + `hero_findings/` — calibrated chip + finding system, all 4 generators wired
* `citations/` — receipt pattern foundation + critic + render (Pattern 8 wire-up pending Window A)
* `mobile/saturday_strip` — 44px sticky primitive (wire-up pending Window A)
* `viral/` — 5 share-card renderers + DB-backed builders (CLI works against real DB)

These all use Convention A (dark-default tokens). When v5-11.5 lands the tokens-bridge, no changes needed on these surfaces — they will inherit the light-mode override automatically.

Pending Window A wiring (independent of v5-11.5):
* `CitationCritic` into `quality_loop.py`'s Pattern C/D revise loop
* `render_auto_summary_html` into Mailbag + Reactions + Edition-feature renderers (Daily is done in PR #122)
* `Saturday Strip` into mobile-header template
* `render_rituals_strip` is LIVE on team pages (PR #122)

---

This brief is a pre-work artifact. The actual v5-11.5 sprint opens when Window A ships v5-11; nothing here gates earlier work.
