# Figma Reference — Player Page (v5 locked system)

This folder is the **design canon** for the CFB Index player page. It is a working React/Tailwind/Vite prototype produced by Figma Make across Stages 1–3 (Apr 22–23 2026). It is **not production code**. Production is the Python static-site generator in `src/cfb_rankings/reporting.py`.

## What this is FOR

- **Visual reference.** When porting a module to the Python generator, open the matching `.tsx` file and `src/styles/theme.css` to see exactly what the production HTML + CSS should look and feel like.
- **Token canon.** `src/styles/theme.css` contains the exact OKLCH ramps, fluid `clamp()` type scale, motion tokens, radius, elevation, and spacing that production uses. If Python and this file disagree, this file wins.
- **Interaction spec.** Component files show the exact React state pattern, keyboard handling, aria attributes, and motion-role assignments for each interactive surface.
- **Design review tool.** You can run this locally (`pnpm install && pnpm dev`) to open the prototype in a browser for side-by-side comparison with the live site.

## What this is NOT

- Not deployed. Not shipped to users.
- Not a component library. Nothing here imports into production Python.
- Not authoritative over the brief when the brief is stricter — `PLAYER_PAGE_WORLD_CLASS_BRIEF.md` is the higher-level spec; this is the visual realization.

## Contents

- `src/styles/theme.css` — the token canon (copy tokens verbatim into production CSS)
- `src/app/pages/PlayerPage.tsx` — the page assembly (10 modules in order, sticky subnav, URL state hookup)
- `src/app/components/*.tsx` — the 10 module components + `StandingVariants.tsx` showing 5 rung extremes
- `src/app/components/ui/*.tsx` — shadcn UI primitives (reference for stateful bits like `<Input>`, `<Tabs>`, `<Drawer>`)
- `src/app/components/ui/subnav.tsx` — the custom Subnav primitive (sticky behavior, IntersectionObserver, aria)

## Running locally for design review

```
cd figma-reference/player-page
pnpm install
pnpm dev
# opens at http://localhost:5173
```

## Stages shipped

- **Stage 1** (Hero Fingerprint, Player Standing, Standing Variants, tokens, primitives, states) — locked v4/v5.
- **Stage 2** (The Room, Signature Story, Current Season, Savant, Splits, Peer Comparator, Supporting Cast, Bio/Recruiting/Transfer/Roster) — locked.
- **Stage 3** (full page assembly, sticky Subnav primitive, Savant cohort filter P4/G5/All-FBS, sub-route URL states via `useURLState` hook, page-level loading/partial/error) — locked.

## Deviations production takes from this reference (intentional)

- **URL state** — production uses `history.pushState` so browser back/forward works; this prototype uses `history.replaceState` for a simpler demo. Port as `pushState`.
- **Runtime** — production is Python + vanilla HTML + Alpine.js. The React pattern is the design contract; Alpine is the runtime.
- **CSS delivery** — production uses one external stylesheet with content-hashed filename (`/assets/cfb-index.<hash>.css`); this prototype inlines Tailwind via Vite.

## How to refresh this folder

When Figma Make produces a new iteration (e.g., Stage 4 polymorphism work for WR/DB/OL/K/P), drop the zip at `uploads/`, extract into a new `figma-reference/player-page-vNN/`, audit against prior, then replace this folder when locked. Keep one copy as the current canon; archive prior versions under `figma-reference/_archive/` if you want history.
