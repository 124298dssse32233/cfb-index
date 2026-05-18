# Claude Code — Hotfix: Stop `build-site` From Clobbering World-Class Team Pages

Paste this whole document into a fresh Claude Code session in the Sports Website directory. Execute autonomously. Report only at end. Target: Sonnet for all work. Budget: ~10k tokens.

---

## Problem

The new `team_pages` module renders 11 world-class HTML files to `output/site/teams/<slug>.html`. The legacy `reporting.py` pipeline writes to the **same paths** during `build-site`, so every `build-site` run silently overwrites the world-class pages with legacy output.

Evidence (confirmed via grep on disk just now):
- `output/site/teams/massachusetts.html` contains legacy markers (`Team Mood Card`, `NET POINTS`, `#268`) and zero world-class markers (`heritage-strip`, `team-identity-header`, `aspiration-ladder`, `scrappy-proud`, `UMass is playing`, `Rise as one`).
- All 11 sprint-1 programs are in the same state.

## Fix — two parts

### Part 1 — Guard `reporting.py` so it skips profiled slugs

1. Read `profiles/` directory. Build `PROFILED_SLUGS: set[str]` from the filenames (strip `.md`, normalize any underscores to hyphens for consistency). There should be ~11 today.

2. Open `src/cfb_rankings/reporting.py`. **Do not read it whole — it's 17.5k lines.** Use `grep -n` to find the function that renders an individual team page (likely named `render_team_page`, `build_team_page`, `write_team_page`, or inside `build_site`'s per-team loop). Search for `teams/` path writes and `f"teams/{...}.html"` patterns.

3. Add an early-return guard at the top of that function (or inside its per-team loop):

```python
# Profiled teams are rendered by src/cfb_rankings/team_pages/renderer.py (new module).
# Skip them here so build-site doesn't clobber the world-class output.
from cfb_rankings.team_pages.profile_loader import PROFILED_SLUGS  # or inline the set
if team_slug in PROFILED_SLUGS:
    return  # or: continue, depending on context
```

   If `PROFILED_SLUGS` isn't already exported from `profile_loader.py`, add it:
```python
# In src/cfb_rankings/team_pages/profile_loader.py
import os
PROFILES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "profiles")
PROFILED_SLUGS: set[str] = {
    f[:-3].replace("_", "-")
    for f in os.listdir(PROFILES_DIR)
    if f.endswith(".md") and not f.startswith("_")
}
```

4. Handle duplicate `notre_dame.md` / `notre-dame.md` — the set should contain `notre-dame` once. Confirm by printing the set during a dry run.

### Part 2 — Re-render the 11 world-class pages and verify

5. Run `python manage.py render-team --team <slug>` for each of: `notre-dame alabama ohio-state georgia michigan texas oregon usc penn-state vanderbilt massachusetts`. If any fail, fix and retry.

6. Verify: `grep -l "heritage-strip\|team-identity-header\|aspiration-ladder" output/site/teams/<slug>.html` should return the file for all 11.

7. **Regression test the guard:** run `python manage.py build-site`. Afterward, re-run the grep from step 6. All 11 world-class markers must still be present. If any are gone, the guard isn't firing — investigate and fix.

## Decision authority

Act autonomously on: exact guard placement, whether `PROFILED_SLUGS` lives in `profile_loader.py` or a new `constants.py`, whether to normalize slugs at load-time or at compare-time, how to resolve the `notre_dame.md` duplicate (delete one, or teach the loader to prefer one).

Only stop if: the per-team render logic in `reporting.py` is entangled with shared state that makes a clean early-return unsafe (in which case describe the entanglement and propose two options).

## Report back with

- The function + line number(s) where the guard was added.
- The contents of `PROFILED_SLUGS` (printed).
- Confirmation that step 7's regression test passed — grep counts for all 11 files before and after `build-site`.
- Token usage.

Do not touch the sprint 2 work in progress. This is a surgical hotfix. Under 10k tokens expected.
