# World-Class CFB Index — Enhancement Layer

Decorator-style enhancement bundle that ships through the publish workflow.
Lives entirely in `tools/wcfb_enhancements/` so it doesn't entangle with the
core Python renderers (`reporting.py`, `team_pages/`, etc).

## Pipeline integration

In `.github/workflows/publish_site.yml`, **after** all renderer steps:

```
Refresh methodology + freshness pages
Refresh editions archive
Refresh backfilled edition pages           # rewrites output/site/index.html
Refresh storylines index
        ↓
Inject team logos into rankings            # post-process — must run last
Build /compare/ landing page
Install World-Class enhancement layer
Write .vercelignore for published branch
        ↓
Upload artifact → Push to published branch → Vercel auto-deploys
```

The ordering is critical: anything that writes to `output/site/` must run
**before** the post-process steps, otherwise the renderer will silently erase
the injected markers.

## Files

| File | Purpose |
|---|---|
| `wcfb-enhancements.css` | All Phase 1/3/4/6/7 visual classes, namespaced `wcfb-` |
| `wcfb-enhancements.js`  | Behavior layer — tooltips, reveals, dials, mobile nav |
| `install.py`            | Copies CSS/JS into site, injects `<link>+<script>` into every HTML |
| `build_compare.py`      | Writes self-contained `output/site/compare/index.html` |

## Master Plan coverage

From `WORLD_CLASS_CFB_INDEX_MASTER_PLAN.md`:

### ✅ Shipped — visible on the live site today

| Phase | Item | Status |
|---|---|---|
| 1.1 | Team logos in rankings rows | Already shipped (pre-session, `tools/inject_rankings_logos.py`) |
| 1.2 | Progressive disclosure CSS (`details.wcfb-disclosure`, `.wcfb-stat-cluster`, `.wcfb-stat-tile`) | CSS active site-wide; opt-in via class |
| 1.3 | Emoji signposts (`.wcfb-sign-up/down/elite/warn/fire/cold/clutch`) | CSS + auto-tagger active |
| 3.1 | Interactive tooltips (`[data-wcfb-tip]`) | CSS + JS active; auto-glossary binds Power/Resume/SOS/EPA/Belief |
| 3.2 | Comparison page (`/compare/`) | NEW — full 17-program picker with URL state |
| 3.3 | Scenario explorer | Already exists at `assets/js/bets/scenario-explorer.js` |
| 4.1 | Skeleton screens (`.wcfb-skeleton`) | CSS active; opt-in |
| 4.2 | Micro-interactions (`.wcfb-lift`, `.wcfb-press`, link grow) | CSS active site-wide |
| 4.3 | Scroll-based reveals (`.wcfb-reveal`) | CSS + IntersectionObserver active |
| 5.2 | Image optimization (lazy loading) | Already used on logos via `loading="lazy"` |
| 5.3 | Incremental builds | Already shipped (`sync-site-incremental`) |
| 6.1 | Mobile bottom navigation | NEW — auto-injected on every page, visible ≤720px |
| 6.2 | Table → Card transformation (`table[data-wcfb-card-mobile]`) | CSS active; opt-in via attribute |
| 7.4 | Probability dials (`[data-wcfb-dial="0.74"]`) | CSS + JS active; opt-in via attribute |

### ⚠️ Framework-only — usable but not yet visible

These features have full CSS+JS support shipped, but won't render until
Kevin (or a future agent) opts a specific template element in by adding
the relevant class/attribute. Suggestions:

- `data-wcfb-card-mobile` on the `<table>` in `rankings/index.html` will make
  rankings rows transform into stacked cards on mobile.
- `data-wcfb-dial="0.74"` on a `<span>` next to any probability number
  renders a colored conic-ring dial.
- `class="wcfb-lift"` on team-page hero cards lifts on hover.
- `class="wcfb-reveal"` on below-fold sections fades-in on scroll.

### ❌ Deferred — require real model data in CI artifact DB

These can't ship visibly until the `cfb-rankings-db` GitHub Actions
artifact has populated `model_runs`, `power_ratings_weekly`, `games`,
`teams`, and `players`:

| Phase | Item | Why deferred |
|---|---|---|
| 2.1 | Auto-generated stat summaries | Needs current/historical stats per team |
| 2.2 | "Why This Matters" framework | Needs narrative templates + stat triggers |
| 2.3 | Narrative-driven analytics | Same |
| 7.1 | Fan Intelligence Bridge   | Needs `fanbase_mood_weekly` / sentiment data |
| 7.2 | Rivalry Intelligence Dashboard | Needs dual-fanbase signal |
| 7.3 | Cross-Era Intelligence    | Needs historical comparable data |
| 5.1 | Critical CSS extraction   | Requires build-system change (Vite/PostCSS) — not yet worth the complexity |
| 6.3 | Pull-to-refresh           | Marginal value for a static site; pinch zoom is fine |

## Verification (post-deploy)

Smoke tests run by hand after every publish:

```js
// In browser console at https://wonderful-margulis-8ec96b.vercel.app/<any-page>
window.wcfb.__initialised        // → true (JS layer loaded)
getComputedStyle(document.documentElement).getPropertyValue('--wcfb-accent')  // → "#c9a24a" (CSS layer loaded)
document.querySelector('.wcfb-bottom-nav') !== null                            // → true (mobile nav injected)
document.documentElement.getAttribute('data-wcfb-theme')                       // → "dark" on team/player, null on light
```

For `/compare/`:

```js
document.querySelectorAll('#wcfb-pick-a option').length    // → 18 (17 programs + placeholder)
JSON.parse(document.getElementById('wcfb-program-data').textContent).length  // → 17
```

## Why post-process instead of editing templates

Three reasons:

1. **The DB is empty in CI.** `build-site` can't regenerate pages from
   `reporting.py` because `model_runs` is empty. Template-level changes
   would not surface on the live site.
2. **Decorator-style is safer.** Modifying `reporting.py` (~25,800 lines)
   carries high regression risk; the CSS/JS layer is additive and namespaced
   so it can't break existing styles.
3. **Easy to revert.** Removing the post-process step removes all the
   enhancements cleanly.

When the data pipeline is back online, future work should migrate these
classes into the Python templates so the enhancement layer becomes
permanent and the post-process step becomes redundant.
