# Visual Polish Audit — Surface Findings
**Branch:** polish/visual-audit-001  
**Date:** 2026-04-26

## Surface-by-surface verdict

| Surface | Sample file | Status | Notes |
|---------|------------|--------|-------|
| players/the-room.html | the-room.html | **STUB → FIXED** | See Phase 3 |
| teams/*.html | notre-dame.html | PASS | Inline `<style>` design system; custom chrome |
| conferences/*.html | fbs-sec.html | PASS | External CSS + full topbar nav |
| conferences/*_pulse.html | acc_pulse.html | N/A | HTML fragments for embedding, not standalone pages |
| players/*.html | dante-moore-2873.html | PASS | External CSS + full topbar nav |
| storylines/*.html | 12-team-playoff-settling.html | PASS | Inline `<style>`; full nav |
| canon/*.html | index.html | PASS | Inline `<style>`; canonical masthead nav |
| wire/*.html | index.html | PASS | Inline `<style>`; starts with template comment (benign) |
| receipts/index.html | index.html | CONTENT-STUB | Styled with inline CSS; no data cards (data issue, not visual) |
| editions/ | 2026-w14/..., 2026-w15/... | PASS | Week-based subdirs; no root index by design |
| homepage (index.html) | index.html | PASS | Inline `<style>` + full nav |
| mailbag/*.html | index.html | PASS | Inline `<style>` + nav |
| daily/*.html | index.html | PASS | Inline `<style>` with design tokens |
| attributions/index.html | index.html | PASS | External CSS; colophon page, small by design |
| hub/*.html | — | PASS | External CSS + nav |

## Confirmed stub-styled page
**output/site/players/the-room.html** — three distinct bugs:
1. CSS link pointed to `../style.css` (file does not exist)
2. `.the-room-board__*` CSS classes had no corresponding rules in any loaded stylesheet
3. Quote text truncated at character boundary (mid-word), not word boundary
4. Author attribution exposed raw email `lockedonpodcasts@gmail.com (...)` in visible byline

## False-positive stubs (flagged by automated check, no fix needed)
- `attributions/index.html` — 2904B is correct for a colophon page; has external CSS
- `conferences/*_pulse.html` (358–1644B) — HTML fragment partials, not standalone pages
- `daily/archive.html` — small archive table, inline `<style>`, correct by design
- `receipts/index.html` — correctly styled with inline CSS; content-empty due to data pipeline, not a visual polish issue
- `teams/notre-dame.html` — custom chrome without standard `<nav>` tag; world-class team-page design by design
