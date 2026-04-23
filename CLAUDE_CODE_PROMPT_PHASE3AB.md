# Claude Code Prompt — Phase 3A + 3B (Team Identity Tie-Off & Registry Reach)

Paste this into Claude Code. It covers two work streams that should execute in sequence.

---

## Mission

You are continuing the CFB Index team-identity work. Phase 2 landed a DB-backed brand registry (`src/cfb_rankings/visual_assets.py`) and cached ~1,285 real logo files under `output/site/assets/team-art/`. This prompt finishes what Phase 2 deferred (3A) and extends the registry's reach so it becomes the single source of truth for every team-marker surface on the site (3B).

Do not re-derive strategy. Do not write exploratory docs. Ship code.

---

## Hard rules (read first, obey throughout)

1. **Token discipline.** `src/cfb_rankings/reporting.py` is ~17,500 lines. Never read it whole. Use targeted `offset` + `limit` reads, or grep for the symbol you need and read ±60 lines. Same for any file > 500 lines.
2. **Do not read** anything under `.deps/`, `.vendor/`, `design-ref/`, `tmp_*`, `_figma_*`, `output/site/**`, `output/debug*`, or `output/anthropic-team-identity-and-logos-review.md`. None of them are needed for this work.
3. **Model routing** (non-negotiable — route explicitly with the Task tool):
   - **Haiku**: pre-flight verification, grep sweeps, call-site inventories, post-change audits, renames.
   - **Sonnet**: default implementer. All edits to `reporting.py`, `hub_page.py`, `ingest/team_brand.py`, `visual_assets.py`.
   - **Opus**: only for cross-cutting design decisions if something non-obvious comes up (e.g., a signature change to `team_chit_svg`). Default to Sonnet; escalate only on true schema/contract calls.
4. **Idempotency.** Every ingest step must be safe to re-run. Every code path must tolerate a missing asset without 500'ing.
5. **Do not edit** `output/site/**` directly. Regenerate via the generator.
6. **Build targets:** `python -u manage.py build-site` for fast iteration. Full publish only when explicitly asked.
7. **No new top-level docs.** No README updates. No migration files beyond what already lives in `src/cfb_rankings/migrations.py`.
8. **Git:** this is not a git repo. Do not run `git`. Do not mention commits.

---

## Phase 3A — Close the two deferred items

### 3A.1 — ESPN-CDN backstop for the 18 edge-case 404s

**Goal.** When CFBD returns no logo for a team, fall back to `https://a.espncdn.com/i/teamlogos/ncaa/500/{espn_id}.png`. Most FBS teams have their ESPN ID on the CFBD team record; FCS/II/III schools frequently don't, and those are fine to leave unresolved.

**Steps (Sonnet):**

1. Pre-flight (Haiku): read `src/cfb_rankings/ingest/team_brand.py` end-to-end (it's only ~243 lines) and report the exact function name, input args, and local variable that currently holds the CFBD team dict inside the per-team loop. Also report the exact call-site that downloads + caches the primary logo. Return <150 words.
2. In `ingest/team_brand.py`, inside the per-team resolution loop:
   - If CFBD `logos` is empty or download fails, check the team dict for any field that looks like an ESPN id (commonly `id`, but name it defensively — use whichever integer id field CFBD actually provides on the team record; verify from the Haiku pre-flight).
   - Construct `https://a.espncdn.com/i/teamlogos/ncaa/500/{id}.png`, attempt to GET it with a 5s timeout and a descriptive `User-Agent: cfb-index-ingest/1.0`.
   - On 200, cache to the same `assets/team-art/{slug}/logo_primary.png` path as the CFBD path, and record `source='espn_cdn'` in `team_brand_assets`.
   - On non-200 or exception: log the team slug + HTTP status, continue. No raise.
3. Persist a `source` value per asset row so attribution stays truthful. If the column doesn't exist yet, add it via `_ensure_column` in `migrations.py::apply_runtime_migrations`.
4. Update `output/site/attributions/index.html` generator (`_write_attributions_page` in `reporting.py`) to list ESPN as a backstop logo source when any row has `source='espn_cdn'`. One sentence added, not a rewrite.

**Acceptance (Haiku audit):**
- Re-run `python manage.py sync-team-brand-assets` and report: total teams synced, CFBD-sourced count, ESPN-sourced count, still-missing count.
- Confirm `source` column exists and is populated for every row written this run.
- Confirm no stack traces in stderr.

### 3A.2 — OG share-card logo embedding

**Goal.** The social share card is currently typography-only. Embed the team's primary logo as an inline base64 `<image>` element inside the SVG at `reporting.py:7718` (`_render_og_image_svg`).

**Steps (Sonnet):**

1. Pre-flight (Haiku): read `reporting.py` lines 7680–7820 and report (a) `_render_og_image_svg`'s signature and what slug/team context it receives, (b) the SVG's viewBox, (c) where the team name or abbr is currently rendered so we know where to place the mark. Return <200 words.
2. Add a module-level cache at the top of `reporting.py` (near other build-time caches): `_OG_LOGO_B64_CACHE: dict[str, Optional[str]] = {}`. Keyed by team slug. Value is the base64 data URL or `None` if no asset exists.
3. Add a helper `_og_logo_data_url(slug: str) -> Optional[str]` that:
   - Returns cached value if present.
   - Resolves the team brand via `visual_assets.resolve_team_brand(slug)`.
   - If `logo_primary_path` exists on disk, reads it, base64-encodes, prepends `data:image/png;base64,`, caches, returns.
   - Otherwise caches `None` and returns `None`.
4. Inside `_render_og_image_svg`, if the data URL is non-None, emit `<image href="{data_url}" x="…" y="…" width="…" height="…" preserveAspectRatio="xMidYMid meet"/>`. Placement: left of the headline, square, ~96px at 1200×630 canvas. If None, render the existing typographic fallback unchanged.
5. Rebuild: `python -u manage.py build-site`. Spot-check three rendered OG cards (pick Georgia, Nebraska, a mid-tier school with a resolved logo) by inspecting the emitted SVG string in the generated HTML head or in `output/site/assets/og/`. The `<image>` tag must be present.

**Acceptance (Haiku audit):**
- Grep count of `<image href="data:image/png` in `output/site/**` should equal the number of teams with a cached `logo_primary.png` (or very close — missing = non-FBS with no logo, which is expected).
- No new Python traceback lines in the build log.
- Build time regression vs. prior build is < 20%. (Base64 reads are cheap; the cache should keep it flat.)

---

## Phase 3B — Route all team markers through the registry

**Goal.** `visual_assets.team_chit_svg()` and `visual_assets.resolve_team_brand()` exist. Today only the Hype vs Reality scatter and the team-page hero use them. Five more surfaces still read `TEAM_COLOR_BY_SLUG` or hand-roll color/abbr lookup. Unify them. After this lands, Nebraska's houndstooth and every texture override propagate everywhere automatically.

### 3B.1 — Call-site inventory (Haiku, first step, non-negotiable)

Before any edits, grep the codebase for these patterns and produce a single markdown table with file, line, context (1 line), and which registry call should replace it:

- `TEAM_COLOR_BY_SLUG[`
- `TEAM_COLOR_BY_SLUG.get(`
- `render_team_chip(`
- `_team_mark(`
- `_team_theme(`
- Any hand-rolled team abbreviation mapping (search for dict literals that look like `{"alabama": "BAMA"` or similar)

Exclude call sites inside `visual_assets.py` itself and inside the texture/manual-override dicts at the top of `hub_page.py`. Those are the source of truth and stay.

Target surfaces (the inventory should confirm each):
1. `_render_hype_scatter_svg` in `hub_page.py` — scatter markers.
2. Rivalry matrix (N° 05) in `hub_page.py` — cell fills / abbreviations.
3. Taxonomy sparkline (N° 04) in `hub_page.py` — inline marks.
4. Matchup page team blocks in `reporting.py` — header tiles on each matchup HTML.
5. Player page team pill in `reporting.py` — the small team tag above the player name.

Return the table plus a 3-line plan per surface. No edits yet.

### 3B.2 — Implementation (Sonnet, one surface at a time)

For each of the five surfaces, in this order:

**Work unit template (apply to every surface):**
1. Read the ±60 lines around the call site only.
2. Replace the direct `TEAM_COLOR_BY_SLUG` / ad-hoc lookup with `resolve_team_brand(slug)` → use `.primary_color`, `.secondary_color`, `.abbreviation`, `.logo_primary_path`.
3. For markers (scatter, rivalry cells, sparkline, matchup tiles, player pill), call `team_chit_svg(slug, size=...)` instead of inlining SVG.
4. Preserve the manual texture-override behavior already encoded in `hub_page.py` — `team_chit_svg` already consults it, so no work here as long as the call goes through the registry.
5. Do not change visual output on teams that had no manual override. Pixel drift on the overridden teams (Nebraska, Michigan, etc.) is expected and desired: their textures now propagate.

**Surface-specific notes:**

- **Scatter (`_render_hype_scatter_svg`)**: already partly migrated. Finish the job — the dot-draw loop should be a single `team_chit_svg` call per team, no local color fetch. Keep the hype/reality axis logic untouched.
- **Rivalry matrix**: each cell currently likely fills with one team's primary color. Replace with a compact chit (abbr only, no helmet) sized for matrix density — if `team_chit_svg` doesn't support an "abbr-only" mode, add a `variant: Literal["full", "abbr"]` parameter with default `"full"`. This is the only acceptable signature change; escalate to Opus before adding it.
- **Taxonomy sparkline**: inline abbr chits at category endpoints. Use `variant="abbr"`, size=18.
- **Matchup page team blocks**: two large blocks per matchup, left/right. Use hero-size chit (size=72) + logo `<img>` from `logo_primary_path` if present. Same layout rules as the team-page hero.
- **Player page team pill**: small pill next to player name. `variant="abbr"`, size=22. Link to `/teams/{slug}.html`.

After each surface: run `python -u manage.py build-site` and spot-check one generated page for that surface. Do not proceed to the next surface until the current one renders.

### 3B.3 — Audit (Haiku, final step)

After all five surfaces land:

1. Re-run the grep from 3B.1. The only remaining `TEAM_COLOR_BY_SLUG` references must be (a) the dict definition itself, (b) the texture-override layer, (c) inside `visual_assets.py`.
2. Run `python -u manage.py build-site` clean. Report: total files built, Python errors, warnings, any unresolved team slugs.
3. Smoke test three pages by reading their rendered HTML and confirming the logo `<img>` or chit SVG is present:
   - One matchup page (any).
   - One player page (any player on a team with a cached logo).
   - `/hub/` page — confirm scatter + rivalry + taxonomy all render chits.

---

## Deliverable

A single short status report at the end, in this shape:

```
Phase 3A
  ESPN backstop: {before 404 count} → {after}, added {N} ESPN-sourced logos
  OG embed: {N} cards with embedded logos, build time {before}s → {after}s
Phase 3B
  Call sites migrated: scatter ✓ rivalry ✓ taxonomy ✓ matchup ✓ player ✓
  Remaining TEAM_COLOR_BY_SLUG direct reads: {N} (must be ≤ 3 — the dict, the override layer, visual_assets.py)
  Build clean: {pages} pages, 0 tracebacks
Files touched: {list}
Deferred / follow-ups: {anything you couldn't land}
```

No narrative. Don't re-explain what you did. The report is the only output.

---

## One last thing

If at any point the plan collides with reality — e.g., `_render_hype_scatter_svg` doesn't look how I described, or `team_chit_svg` needs a second signature change — stop, surface the conflict in a 3-line note, and wait for direction. Do not improvise on contracts.
