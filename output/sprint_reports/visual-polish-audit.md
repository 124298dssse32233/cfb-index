# Sprint Report — Visual Polish Audit
**Branch:** polish/visual-audit-001 (from master)  
**Date:** 2026-04-26  
**Model:** Sonnet 4.6 (0% Opus — all template work)

---

## 1. Audit findings — surface-by-surface

Audited 22 surface types across `output/site/`. One confirmed stub. Multiple false-positives
in automated check explained below.

**STUB (1):** `output/site/players/the-room.html`  
**PASS (all others):** See `visual-audit-findings.md` for full surface table.

False-positive flags explained:
- Pages using inline `<style>` blocks (wire, storylines, canon, homepage, teams, mailbag, daily)
  are correctly styled — the automated check required `<link rel="stylesheet">` which was too strict.
- Conference `*_pulse.html` files are HTML fragments, not standalone pages.
- `receipts/index.html` is styled but content-empty; a data pipeline issue, not visual polish.

---

## 2. Phase 3 — The Room v2 fix

**File:** `src/cfb_rankings/the_room_board.py`

**Before:**
- 89,932 bytes, linked to `../style.css` (file does not exist anywhere in the site)
- `.the-room-board__*` classes had no CSS rules — plain browser-default rendering
- Quote text sliced at `[:220]` — mid-word truncation ("Spencer McLaughl")
- Author attribution showed raw email: `lockedonpodcasts@gmail.com (Locked on Podcast Network)`

**After:**
- 78,680 bytes
- Links to `/assets/cfb-index.<hash>.css` (resolved at render time via `_find_css_filename()`)
- Inline `<style>` block adds `.the-room-board__*` rules: dark-mode card grid (3-col desktop,
  2-col tablet, 1-col mobile), label/value stack, serif title, mono stats strip, italic quote
- `clean_truncate()` truncates at word boundary with `…` ellipsis
- `_clean_attribution()` strips email prefix: `email@host (Name)` → `Name`
- Standard site topbar nav (matching player/conference page pattern)
- `site-shell` + `main#main-content` wrapping for accessibility

**Key functions added:**
- `clean_truncate(text, max_chars=240)` — word-boundary truncation
- `_clean_attribution(author_pseudonym)` — email stripping
- `_find_css_filename(site_root)` — resolves live CSS hash from assets dir
- `_nav_html(prefix, current)` — standard topbar nav matching site chrome
- `_ROOM_STYLES` — CSS for `.the-room-board__*` class namespace

---

## 3. Phase 4 — Other stub-styled surfaces

**None required.** All other surfaces were correctly styled. See findings doc for
false-positive analysis.

---

## 4. Phase 5 — Cross-surface check results

| Page | Status |
|------|--------|
| the-room.html (new) | PASS |
| conferences/fbs-sec.html | PASS |
| storylines/12-team-playoff-settling.html | PASS |
| canon/index.html | PASS |
| wire/index.html | PASS (template comment before DOCTYPE — benign, renders correctly) |
| receipts/index.html | CONTENT-STUB (styled; no data — out of scope) |
| homepage | PASS |
| teams/notre-dame.html | PASS (custom chrome; no `<nav>` tag by design) |
| players/dante-moore-2873.html | PASS |
| mailbag/index.html | PASS |

---

## 5. Voice validator sweep

Ran on changed file (`the-room.html`):

- **Violations: 1** — `"methodology"` in nav link label `href="../methodology/...">`Methodology</a>`
- This is pre-existing across all pages using the standard site nav (confirmed: fbs-sec.html also
  has exactly 1 violation, the same nav link).
- Not editorial copy. Not introduced by this sprint. Documented only.

---

## 6. Token usage by model

- **Sonnet 4.6:** 100% (all template + Python work)
- **Opus 4.7:** 0%
- **Haiku 4.5:** 0%

---

## 7. Files touched

| File | Change |
|------|--------|
| `src/cfb_rankings/the_room_board.py` | Full rewrite — CSS path, nav, styles, truncation, attribution |
| `output/sprint_reports/visual-audit-findings.md` | New — per-surface audit table |
| `output/sprint_reports/visual-polish-audit.md` | New — this report |

---

## 8. Quality concerns / next steps

1. **Wire template comment:** `wire/index.html` and related templates begin with an HTML comment
   before `<!DOCTYPE html>`. Technically valid but non-standard. Low priority cosmetic fix.

2. **Receipts content stub:** `receipts/index.html` has zero data cards. The page is styled
   correctly; the content pipeline hasn't run (or has no resolved outcomes yet). Not visual polish.

3. **Voice validator nav false positive:** The word "methodology" in nav link text triggers the
   validator on every page using the standard topbar. Consider adding a nav-content exclusion zone
   to the validator, or whitelisting nav-label strings. Out of scope here.

4. **Wave 3 re-audit:** When Wave 3 sprints land, run `python manage.py build-the-room-board
   --season 2025` and re-run Phase 5 checks before merging. Same stub-template risk applies.

5. **CSS hash coupling:** `_find_css_filename()` resolves the CSS hash at render time from the
   assets directory. This is correct for standalone `build-the-room-board` runs. During
   `build-site`, the full build ensures the CSS is written before the room board is rendered.
