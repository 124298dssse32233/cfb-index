# CFB Index Site-Quality — Implementation Progress Log

**Branch:** `feature/site-quality-2026-06-11` · **Started:** 2026-06-11 · **Scope:** `/octo:embrace` Phase 0→4 (see [Define manifest](site_quality_define_2026-06-11.md), [Discover](site_quality_discover_2026-06-11.md)).
**Rules in force:** isolated branch · no prod deploy without explicit user approval · no DB hand-edits · no new recurring product cost · design tie → keep existing · small reviewable commits per WP · verify before claiming done.

> **Build-safety note:** `scripts/build_publish.ps1` deploys at line ~241 (`publish_to_vercel.ps1`). **Never run it whole** during dev — verify generators by invoking them directly (they only write gitignored `output/site`).

## Status board

| WP | Title | Status | Commit | Evidence |
|---|---|---|---|---|
| 0.1 | Box build generates /offseason/ + /film-room/ | ✅ done | (this commit) | hub scripts wired into build_publish.ps1 post-build block; both emit non-stub (offseason 90KB/125 rows/5 boards, film-room 13KB/4 boards); PS parses clean |
| 0.2 | Canonical build manifest (full command-set parity) | ⏳ next | — | — |
| 0.3 | Smoke + build assertions on every nav target | ⏳ | — | — |
| 0.6 | Pre-deploy snapshot-completeness guard (Gate B) | ⏳ | — | — |
| 0.5 | Correct DATA_SOURCES doc + refresh AGENTS.md | ⏳ | — | — |
| 0.4 | Row-count/freshness/coverage/provenance guards | ⏳ | — | — |
| 0.7 | Provenance labeling (legacy_unverified) | ⏳ (Phase 0, deferred edit) | — | — |

Legend: ✅ done · 🔄 in progress · ⏳ pending · ⚠️ blocked.

---

## Log

### WP-0.1 — Box build generates /offseason/ + /film-room/ — ✅ 2026-06-11
**Problem (CP-1):** both routes are globally nav-linked but 404 in prod; the box (only live deployer, full-snapshot) never generated them — only the retiring `publish_site.yml` did.
**Change:** added two non-Critical `Run` steps to `scripts/build_publish.ps1` post-build block (right after `render-today-in-history`), mirroring the existing storylines/wire/anniversary clobber-fix:
```
Run "site: build-offseason-leaderboards" { python scripts/build_offseason_leaderboards.py }
Run "site: build-film-room" { python scripts/build_film_room.py }
```
Extended the block comment to record offseason/film-room as the same clobber class.
**Verification (2026-06-11):**
- Ran both scripts directly via venv python → `output/site/offseason/index.html` (90,616 B / 551 lines / "5 national boards · 125 national rows") and `output/site/film-room/index.html` (13,583 B / 77 lines / "4 boards"). Non-stub.
- `[Parser]::ParseFile(build_publish.ps1)` → no errors (no execution).
- Did NOT run full `build_publish.ps1` (it deploys).
**Blast radius:** one PS1 file; adds 2 dirs to the snapshot. **Rollback:** revert the two `Run` lines.
**Note:** the actual 404 fix only lands in prod on the next approved box deploy (these are generated, gitignored). The wiring guarantees the box now ships them.
