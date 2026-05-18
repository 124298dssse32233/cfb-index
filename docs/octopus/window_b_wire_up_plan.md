# Window B Wire-Up Plan (Window A's lane)

_Dated 2026-05-18. Pre-staged while Window B's PRs #122 + #130 are still DIRTY/CONFLICTING. The moment they merge, this doc becomes a mechanical execution checklist (~10 minutes per Window B's estimate). Captures exact code diffs against verified line numbers in current master._

## Pre-conditions (must hold before this PR ships)

- [ ] PR #122 (claude/window-b-phase3-citations) merged on master
- [ ] PR #130 (claude/window-b-theme-toggle) merged on master
- [ ] Verify `src/cfb_rankings/theme/render.py` exists on master with `render_theme_assets_head()` + `render_theme_toggle_button()` callable
- [ ] Verify `src/cfb_rankings/cmdk/index_builder.py` exists with `write_search_index(db, output_path, ...)` callable
- [ ] Verify `python manage.py build-search-index` CLI works against the in-repo DB

Run before starting:
```bash
python -c "from cfb_rankings.theme.render import render_theme_assets_head, render_theme_toggle_button; print('theme API ok')"
python -c "from cfb_rankings.cmdk import write_search_index; print('cmdk API ok')"
python manage.py build-search-index --output /tmp/test-search-index.json --players-max 100 --inspect
```

If any check fails, **STOP and inspect Window B's merged code** rather than proceeding.

## Window B's explicit hand-off (verbatim from review note)

> After merge, Window A needs to:
> 1. Add `render_theme_assets_head()` + `render_theme_toggle_button()` calls to the global head/nav template in `common/head_chrome.py` (or wherever — Window A knows the right slot)
> 2. Add `<link rel="stylesheet" href="/assets/cmdk.css">` + `<script defer src="/assets/cmdk.js">` to the global head
> 3. Add a `<button class="cmdk-trigger" data-cmdk-trigger>` to the global nav
> 4. Update the `output/site/assets/` copy list in `publish_site` to include `theme_toggle.{css,js}`, `cmdk.{css,js}`, `tokens-bridge.css`, and the `search-index.json` from `build-search-index`
> 5. Run `python manage.py build-search-index` as part of `publish_site.ps1`

## Where to wire — verified line numbers on master at 14:50 UTC 2026-05-18

The site has TWO global-head/nav surfaces, both need wiring:

### Surface 1: `src/cfb_rankings/reporting.py` (legacy renderer — homepage, rankings, players, programs, history, archive, matchups, compare, conferences, about-model, heisman, players-landing, etc.)

| Function | Line | Purpose |
|---|---|---|
| `_ensure_global_assets(site_root)` | 5218 | Copies vendored assets from `src/cfb_rankings/static_assets/` to `output/site/assets/`. Add theme + cmdk asset copies here. |
| `_global_link_tags()` | 5287 | Returns the `<link>` + `<script>` tags every page emits in `<head>`. Add theme + cmdk tags here. |
| `_site_nav(prefix, current)` | 20574 | Returns the topbar HTML. Add theme toggle + Cmd-K trigger button here. |

### Surface 2: `src/cfb_rankings/common/head_chrome.py` + `src/cfb_rankings/team_pages/renderer.py` (profiled-team renderer, daily, wire, mailbag — all use `render_head_chrome`)

The `team_pages/renderer.py` inlines its own CSS bundle (`tokens.css` + `styles.css` + savant + rivalry + arc). It uses `render_head_chrome` for OG meta but does NOT use `_global_link_tags()`. Theme toggle wire-up on profiled team pages needs separate treatment.

**Recommendation:** ship Surface 1 first as a contained PR. Surface 2 (profiled team pages) can be a follow-up so the visible change set is reviewable.

## Step 1 — Theme + Cmd-K asset copies

Edit `src/cfb_rankings/reporting.py` `_ensure_global_assets` (line 5236, the asset copy loop):

```python
# BEFORE
for rel_path in (
    "alpine.min.js",
    "js/url-state.js",
    ...
    "fonts/InterDisplay-Bold.woff2",
):
```

```python
# AFTER — add theme + cmdk assets (read from theme/ and cmdk/ packages)
for rel_path in (
    "alpine.min.js",
    "js/url-state.js",
    ...
    "fonts/InterDisplay-Bold.woff2",
):
    ...

# Copy theme + cmdk assets from their package dirs (different source root)
import shutil as _shutil
for pkg_name, asset_files in (
    ("theme", ("theme_init.js", "theme_toggle.css", "theme_toggle.js")),
    ("cmdk",  ("cmdk.css", "cmdk.js")),
):
    pkg_assets = Path(__file__).parent / pkg_name / "assets"
    for fname in asset_files:
        src_path = pkg_assets / fname
        if not src_path.exists():
            continue
        dst_path = assets_dir / fname
        if not dst_path.exists() or dst_path.stat().st_mtime < src_path.stat().st_mtime:
            _shutil.copy2(src_path, dst_path)

# Copy tokens-bridge.css from docs/design-system/assets/
tokens_bridge_src = Path(__file__).resolve().parents[2] / "docs" / "design-system" / "assets" / "tokens-bridge.css"
if tokens_bridge_src.exists():
    tokens_bridge_dst = assets_dir / "tokens-bridge.css"
    if not tokens_bridge_dst.exists() or tokens_bridge_dst.stat().st_mtime < tokens_bridge_src.stat().st_mtime:
        _shutil.copy2(tokens_bridge_src, tokens_bridge_dst)
```

## Step 2 — Theme + Cmd-K `<head>` injection

Edit `src/cfb_rankings/reporting.py` `_global_link_tags()` (line 5287). The current function returns one f-string with `<link>` + multiple `<script defer>`:

```python
# BEFORE (line 5295-5309 approx)
def _global_link_tags() -> str:
    filename = _global_css_filename or "cfb-index.css"
    return (
        f'<link rel="stylesheet" href="/assets/{filename}">\n'
        f'<script src="/assets/js/url-state.js" defer></script>\n'
        ...
        f'<script src="/assets/{_ALPINE_ASSET_NAME}" defer></script>'
    )
```

```python
# AFTER — inject theme assets (must include FOUC-prevention init INLINE)
def _global_link_tags() -> str:
    from cfb_rankings.theme.render import render_theme_assets_head

    filename = _global_css_filename or "cfb-index.css"
    theme_head = render_theme_assets_head()  # inlines theme_init.js + link + script
    return (
        # tokens-bridge MUST load before component CSS so [data-theme] cascades win
        f'<link rel="stylesheet" href="/assets/tokens-bridge.css">\n'
        f'{theme_head}\n'
        f'<link rel="stylesheet" href="/assets/{filename}">\n'
        f'<link rel="stylesheet" href="/assets/cmdk.css">\n'
        f'<script src="/assets/js/url-state.js" defer></script>\n'
        ...
        f'<script src="/assets/{_ALPINE_ASSET_NAME}" defer></script>\n'
        f'<script src="/assets/cmdk.js" defer></script>'
    )
```

**Order matters:**
- `tokens-bridge.css` BEFORE the cfb-index stylesheet (per Window B's note — the `:where()` neutralizer needs to load before component styles so `[data-theme]` selectors win the cascade).
- `theme_init.js` inlined synchronously (FOUC prevention) — `render_theme_assets_head()` handles this; the script runs before first paint.
- `cmdk.js` deferred is fine — overlay only opens on user interaction.

## Step 3 — Toggle button + Cmd-K trigger in nav

Edit `src/cfb_rankings/reporting.py` `_site_nav()` (line 20620 area — inside `nav-actions`):

```python
# BEFORE (line 20622-20625)
f'<div class="nav-actions">'
f'<a class="nav-action{" is-current" if active_key == "matchups" else ""}" href="{prefix}matchups/index.html">Matchup Simulator</a>'
f'<a class="nav-action{" is-current" if active_key == "compare" else ""}" href="{prefix}compare/index.html">Compare Teams</a>'
f"</div>"
```

```python
# AFTER — add Cmd-K trigger + theme toggle to nav-actions (rightmost)
from cfb_rankings.theme.render import render_theme_toggle_button

f'<div class="nav-actions">'
f'<a class="nav-action{" is-current" if active_key == "matchups" else ""}" href="{prefix}matchups/index.html">Matchup Simulator</a>'
f'<a class="nav-action{" is-current" if active_key == "compare" else ""}" href="{prefix}compare/index.html">Compare Teams</a>'
f'<button class="cmdk-trigger nav-action" data-cmdk-trigger type="button" aria-label="Search (Cmd-K)" title="Search (Ctrl-K / Cmd-K)">⌘K</button>'
f'{render_theme_toggle_button(css_class="theme-toggle nav-action")}'
f"</div>"
```

The `nav-action` class on both buttons makes them inherit the same spacing/padding as the existing nav links. Visual harmony.

## Step 4 — `build-search-index` in publish workflow

Edit `.github/workflows/publish_site.yml`. Insert a step between "Apply migrations + seed" (around line 188) and "Build or incrementally sync" (around line 159 — `python manage.py build-site`):

```yaml
- name: Build Cmd-K search index
  # Ships output/site/search-index.json so the overlay's client-side
  # search has a real dataset. ~500KB-1MB depending on player count.
  # Falls through with a warning if the cmdk module is missing
  # (e.g. mid-merge with Window B's branch not yet on master).
  run: |
    python manage.py build-search-index --output output/site/search-index.json || echo "::warning::build-search-index unavailable; continuing without search index"
  continue-on-error: true
```

Use `continue-on-error: true` so a transient failure (missing migration, etc.) doesn't sink the whole publish.

## Step 5 — verification

Local smoke test before committing:
```bash
python manage.py build-site
# Verify the new artifacts landed:
ls -la output/site/assets/theme_init.js output/site/assets/theme_toggle.css output/site/assets/theme_toggle.js
ls -la output/site/assets/cmdk.css output/site/assets/cmdk.js
ls -la output/site/assets/tokens-bridge.css
# Verify head injection:
grep -c "theme_init\|theme_toggle.css\|cmdk.css" output/site/rankings/index.html
# Expected: at least 3 (theme_init inlined + link to theme_toggle.css + link to cmdk.css)
# Verify nav button:
grep "data-cmdk-trigger" output/site/rankings/index.html
grep "data-theme-toggle" output/site/rankings/index.html
# Build search index manually:
python manage.py build-search-index --output output/site/search-index.json --inspect
```

Open a built page in browser:
- Cmd-K should open the search overlay
- Click the theme toggle — should cycle through sun/moon/auto
- Background should re-color (this is the bug Window B's `:where()` fix addresses)

## Acceptance criteria

After PR ships and publish drains:

- [ ] `/assets/theme_init.js`, `/assets/theme_toggle.{css,js}`, `/assets/cmdk.{css,js}`, `/assets/tokens-bridge.css` all present on `origin/published`
- [ ] `/search-index.json` present at site root on `origin/published` with >100 items
- [ ] `view-source:/rankings/index.html` shows `data-theme-toggle` + `data-cmdk-trigger` buttons in topbar
- [ ] Pressing `Cmd-K` (Mac) / `Ctrl-K` (Win) on any page opens the search overlay
- [ ] Clicking the theme toggle cycles theme; background re-colors
- [ ] No JS errors in browser console on rankings, teams, players, heisman, daily pages

## Known limitations carried forward from Window B

- Theme toggle ONLY affects pages that load `tokens-bridge.css`. Profiled-team pages (`team_pages/renderer.py`) currently load their own CSS bundle; they need a Step 6 follow-up.
- `theme_toggle.css` uses `var()` fallback chains so the toggle button still renders if tokens-bridge fails to load — but the colors won't flip.
- `search-index.json` is regenerated every publish but the file is large. If `players_max` exceeds 15000, the JSON gets big enough to slow first-paint. Default is fine.

## Estimated effort

Per Window B: ~10 minutes mechanical wire-up + ~10 minutes local verification + ~10 minutes for the PR description + smoke-test of the live deploy. **Total: ~30 minutes.**

## Why this is a plan doc rather than pre-staged code

Pre-staging the code would require:
- Importing from `cfb_rankings.theme` and `cfb_rankings.cmdk` (modules that don't exist on master yet → fails CI)
- Reading from `docs/design-system/assets/tokens-bridge.css` (file that doesn't exist on master yet)
- Calling `python manage.py build-search-index` (CLI subcommand not yet registered)

Any of those would break the build. A doc has zero risk and is fully executable mechanically once Window B's PRs land.

This doc itself can ship now as a tracking artifact.
