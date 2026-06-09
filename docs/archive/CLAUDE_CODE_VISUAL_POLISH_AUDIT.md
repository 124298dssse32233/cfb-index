# Claude Code — Visual Polish Audit + Fix

> **Inherits from `CLAUDE_CODE_AUTONOMY_AND_TOKEN_CONTRACT.md`.** Single sequential session. Audits rendered HTML for unstyled / stub-styled pages, applies the established design system, re-renders.

**Recommended model: Sonnet 4.6.**

**Target budget: ~30k tokens. Runtime: 1–1.5 hours.**

**Branch:** `polish/visual-audit-001` (branch from current `master`).

**File ownership:**
- Edit: any module's renderer template / Jinja file / inline-template Python
- Edit: shared CSS in `output/site/assets/` if a token/utility is missing
- Edit: any module's renderer.py to wire layout components
- Read-only: data layers (`*_state.py`, `data.py`, DB), reporting.py except documented hooks, voice_validator.py

---

## Why this sprint

The Room v2 page (`output/site/players/the-room.html`) renders with **zero styling** — raw browser defaults, no layout, no typography, no design tokens. Specifically:
- "Belief+81.5" with no space between label and value
- "Locked On Ducks, Spencer McLaughl" truncated mid-word
- Plain blue underlined links, no chrome
- No grid, no card structure, no breathing room

This means Sprint 8.5's `the_room_renderer.py` shipped with a stub template that was never wired to the Pulse v2 visual language other team pages use.

The risk: other Sprint 8.5 / Wave 1+2 surfaces may have shipped with the same gap. Conference Pulse, Canon, Wire, Receipts, Storylines, Editions — any of them could have unstyled or stub-styled pages.

This sprint audits every rendered surface, identifies stub-styled pages, applies the established design system, and re-renders.

---

## Phase 1 — Audit (Haiku, ~3k tokens)

### 1.1 Inventory all rendered HTML

```
find output/site -name "*.html" -type f | head -200
```

Group by surface:
- `output/site/index.html` (homepage)
- `output/site/teams/*.html` (team pages — Pulse v2 reference quality)
- `output/site/conferences/*.html` (conference pages with Pulse module)
- `output/site/players/the-room.html` (The Room v2 — KNOWN BROKEN)
- `output/site/players/<slug>.html` (player pages)
- `output/site/storylines/*.html` (Sprint 10)
- `output/site/canon/*.html` (Sprint 11)
- `output/site/wire/*.html` (Sprint 12)
- `output/site/receipts/*.html` (Sprint 13)
- `output/site/editions/*.html` (Sprint 9)

### 1.2 Detect stub-styled pages

For each surface group, sample 1–2 representative pages and check via grep + manual read:

```python
import re
from pathlib import Path

def style_audit(path: str) -> dict:
    """Score a rendered page on design-system adherence."""
    text = Path(path).read_text(encoding='utf-8')
    return {
        "path": path,
        "has_doctype": text.startswith("<!DOCTYPE"),
        "has_head_link_css": bool(re.search(r'<link[^>]+rel="stylesheet"', text, re.I)),
        "has_inline_style": "<style" in text.lower(),
        "has_design_token_class": bool(re.search(r'class="[^"]*(?:pulse__|edition__|chronicle__|nav__|module__)', text)),
        "has_tailwind_class": bool(re.search(r'class="[^"]*(?:flex|grid|max-w-|text-|bg-|p-|m-|rounded)', text)),
        "byte_count": len(text),
        "first_300": text[:300],
    }

for path in sample_paths:
    print(style_audit(path))
```

A page is **stub-styled** if:
- No CSS link AND no inline styles AND no Tailwind classes AND no design-token classes
- OR byte count is suspiciously small (< 5KB for a content page)
- OR the first-screen markup is just `<h1>` + `<p>` with no wrapping containers / nav / module structure

### 1.3 Output the audit

Write `output/sprint_reports/visual-audit-findings.md` with:
- Per surface: pass / stub / mixed
- For each stub: file path, byte count, what's missing
- Reference page per surface for "this is what good looks like" — usually the team page (`/teams/notre-dame.html`) or an Edition page

---

## Phase 2 — Design system reference extraction (~3k tokens)

Don't invent new styles. Extract what already exists:

### 2.1 Find the canonical templates

```
ls src/cfb_rankings/team_pages/templates/
ls src/cfb_rankings/editions/templates/
find . -name "*.html.j2" -not -path "./output/*" -not -path "./.worktrees/*" -not -path "./.git/*"
```

Look at:
- `team_pages/templates/team.html.j2` (Pulse v2 reference)
- `editions/templates/edition.html.j2` (Edition reference)
- `editions/templates/homepage.html.j2` (Homepage v4 reference)

### 2.2 Find the shared CSS

```
ls output/site/assets/
cat output/site/assets/*.css 2>/dev/null | head -200
find . -name "*.css" -not -path "./output/site/*" -not -path "./.git/*" -not -path "./.worktrees/*"
```

Identify:
- Design tokens (CSS variables for color / spacing / type)
- Module classes (`.pulse__*`, `.edition__*`, `.module__*`)
- Layout primitives (`.container`, `.grid`, `.stack`)
- Typography scale (display serif, body sans, mono for stats)

### 2.3 Document the design system contract

Write a short reference (`docs/design-system/visual-polish-contract.md`) summarizing:
- Required `<head>` block (charset, viewport, CSS link, font preconnect)
- Required wrapping structure (nav, main, footer)
- Module class naming convention
- Reference team page / edition page paths

This becomes the spec the polished templates conform to.

---

## Phase 3 — Fix The Room v2 (Sonnet, ~10k tokens)

`src/cfb_rankings/team_pages/the_room_renderer.py` (and any `the_room.html.j2` template it uses) needs the full Pulse v2 visual language.

### 3.1 Establish layout

Apply the team-page Pulse v2 chrome:
- Standard `<head>` block matching team.html.j2 exactly (font preconnect, CSS link, theme-color, viewport)
- Standard nav at top
- Page hero: "The Room — 2025" headline + subtitle (the "66 players with enough conversation signal..." dek)
- Each player as a **Pulse Card** (not a paragraph dump) with:
  - Header row: player name (display serif, link), position chip, team badge
  - Mood/Belief number prominent (display weight, large)
  - Archetype as a tag-pill
  - Stat strip: Mentions • Authors • Primary cohort • Confidence (mono numeric, label/value separated with proper spacing)
  - Quote excerpt (italic, max ~250 chars, truncated cleanly with ellipsis at word boundary — NOT mid-word like "McLaughl")
  - Source attribution (small caps, source name + handle, no bare email)
- Grid: 3-column desktop, 2-column tablet, 1-column mobile

### 3.2 Fix the truncation bug

Quote bodies are getting cut off mid-word. Add a clean-truncation helper:

```python
def clean_truncate(text: str, max_chars: int = 240) -> str:
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars]
    last_space = truncated.rfind(' ')
    if last_space > max_chars * 0.6:
        truncated = truncated[:last_space]
    return truncated.rstrip('.,;:') + '…'
```

Apply to every player's quote excerpt.

### 3.3 Fix the source attribution

The current render shows `lockedonpodcasts@gmail.com (Locked on Podcast Network)`. Fix the data-formatting layer (likely in `the_room_renderer.py` or a `data.py` helper) so it shows:
- "Locked on Podcast Network" as the displayed source
- Email kept in metadata only, NOT in the visible byline
- Multi-author quotes: "Locked on Podcast Network · LJ Martin, Jake Hatch" (NOT a duplicated email)

### 3.4 Re-render

```
python manage.py render-the-room --top 15
```

Verify `output/site/players/the-room.html` now has:
- `<head>` with CSS link
- Nav present
- Player cards in a grid, not a vertical text dump
- No mid-word truncation
- No bare email addresses in the visible text

---

## Phase 4 — Fix any other stub-styled surfaces flagged by Phase 1 (~10k tokens)

Per Phase 1's audit findings, fix each stub-styled surface using the same pattern:
1. Locate the renderer + template
2. Apply the standard `<head>` + nav + main + footer chrome
3. Rebuild the body content with appropriate module classes
4. Re-render via the surface's CLI subcommand

Common likely candidates:
- **Conference Pulse pages** (`output/site/conferences/*.html`) — Sprint 8.5 module, may have shipped with partial chrome only
- **Storyline reader pages** (`output/site/storylines/*.html`) — Sprint 10 may have similar gap
- **Canon entry pages** (`output/site/canon/*.html`) — Sprint 11
- **Wire entry pages** (`output/site/wire/*.html`) — Sprint 12
- **Receipts source-bio pages** (`output/site/receipts/*.html`) — Sprint 13

For each:
- Diff against the closest reference template (team page, edition page, homepage)
- Match the head + nav + footer exactly
- Body uses surface-appropriate module classes (don't reuse team_pages classes for storylines — each surface has its own namespace)

If a surface ALREADY uses the design system properly, skip it. Don't over-edit.

---

## Phase 5 — Cross-surface checks (~2k tokens)

After each fix, run:

```python
import re
from pathlib import Path

def quick_style_check(path: str) -> bool:
    text = Path(path).read_text(encoding='utf-8')
    return all([
        text.startswith("<!DOCTYPE"),
        '<link' in text and 'stylesheet' in text,
        '<nav' in text or 'role="navigation"' in text,
        len(text) > 5000,  # has real content + chrome
    ])

paths_to_verify = [
    "output/site/players/the-room.html",
    "output/site/conferences/fbs-sec.html",
    "output/site/storylines/the-12-team-playoff-settling.html",
    "output/site/canon/100-players/index.html",
    "output/site/wire/index.html",
    "output/site/receipts/index.html",
]
for p in paths_to_verify:
    print(p, quick_style_check(p))
```

Expected: every path returns True. If any returns False, fix it.

---

## Phase 6 — Voice validator sweep (no new tokens)

The chrome / structure changes shouldn't introduce banned phrases, but run the sweep across the changed files anyway:

```python
import glob
from cfb_rankings.team_pages.voice_validator import validate_fan_voice

violations = []
for path in glob.glob("output/site/**/*.html", recursive=True):
    with open(path, encoding='utf-8') as f:
        text = f.read()
    passed, vs = validate_fan_voice(text, source=path)
    if not passed:
        violations.extend(vs)
print(f"Violations: {len(violations)}")
```

Report violation count. If > 0 on editorial-content samples, document — don't auto-fix copy in this sprint (that's a separate concern).

---

## Phase 7 — Sprint report (~1k tokens)

`output/sprint_reports/visual-polish-audit.md`:
1. Audit findings — which surfaces were stub-styled
2. Fixes applied per surface (file paths + summary)
3. Before/after byte count per fixed page
4. Voice validator sweep result
5. Files touched
6. Quality concerns
7. Natural next: when Wave 3 sprints land, run this audit again before merging — same stub-template risk applies

Commit + push to `polish/visual-audit-001`. Open PR.

---

## Decision authority

Autonomous on: which design-token classes to apply where, truncation length thresholds, grid breakpoints, source-attribution display format, audit threshold for "stub-styled" classification.

Stop and flag only on:
- A surface's renderer requires structural rework that exceeds 30 minutes of edits — flag, document, don't try to over-rewrite in one session
- Design system tokens / classes don't exist for a needed pattern — flag, propose addition, don't invent inline styles silently
- The four canonical hard-blocker conditions

---

## Report back with

1. Phase 1 audit findings — surface-by-surface pass/stub
2. Phase 3 The Room v2 before/after (file path + byte count + 3-line description of fix)
3. Phase 4 other surfaces fixed (one paragraph per)
4. Phase 5 cross-surface check results
5. Voice validator sweep count
6. Token usage by model (Opus should be 0% — this is all template work)
7. Files touched
8. PR URL

Session complete after PR opens. Kevin merges via UI.
