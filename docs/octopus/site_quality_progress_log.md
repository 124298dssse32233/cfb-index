# CFB Index Site-Quality — Implementation Progress Log

**Branch:** `feature/site-quality-2026-06-11` · **Started:** 2026-06-11 · **Scope:** `/octo:embrace` Phase 0→4 (see [Define manifest](site_quality_define_2026-06-11.md), [Discover](site_quality_discover_2026-06-11.md)).
**Rules in force:** isolated branch · no prod deploy without explicit user approval · no DB hand-edits · no new recurring product cost · design tie → keep existing · small reviewable commits per WP · verify before claiming done.

> **Build-safety note:** `scripts/build_publish.ps1` deploys at line ~241 (`publish_to_vercel.ps1`). **Never run it whole** during dev — verify generators by invoking them directly (they only write gitignored `output/site`).

## Status board

| WP | Title | Status | Commit | Evidence |
|---|---|---|---|---|
| 0.1 | Box build generates /offseason/ + /film-room/ | ✅ done | (this commit) | hub scripts wired into build_publish.ps1 post-build block; both emit non-stub (offseason 90KB/125 rows/5 boards, film-room 13KB/4 boards); PS parses clean |
| 0.2 | Canonical build manifest (full command-set parity) | ✅ done (infra) | (this commit) | `build_manifest.py` (15 nav + 9 section routes + 15-command parity table) + `verify_build_manifest.py` (15/15 pass, redirect-aware) wired warn-only into box build; PS parses clean |
| 0.2b | Reconcile safe box-omitted RENDER gaps (render-daily/-edition; canon) | ⏳ follow-up | — | surfaced by 0.2: /canon/ + /daily/ frozen 2026-04-26; canon_lists/entries=0 (don't blind-add render-canon-all) |
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

### WP-0.2 — Canonical build manifest + route verifier — ✅ 2026-06-11 (infrastructure)
**Problem (CP-2):** no canonical manifest; box vs cloud build different command sets; `_build_manifest.json` was a counts stub.
**Change:**
- `scripts/build_manifest.py` — single source of truth: 15 `REQUIRED_NAV_ROUTES` (mirrors `reporting.py::_site_nav`), 9 `EXPECTED_SECTION_ROUTES`, and a `COMMAND_PARITY` table classifying all box/cloud/collect commands (15 gaps: 4 render, 8 derive, 3 ingest).
- `scripts/verify_build_manifest.py` — asserts every nav route exists + non-stub (redirect-aware so meta-refresh hubs like vibe-shifts don't false-warn); `--strict` for hard gate, `--emit` writes `_build_manifest_routes.json`.
- Wired into `build_publish.ps1` (warn-only, non-Critical) before the publish step.
**Verification (2026-06-11):** `verify_build_manifest.py --strict` → **15/15 nav ok, 0 missing, 0 stub**, exit 0; `build_publish.ps1` parses clean.
**Findings surfaced (documented in COMMAND_PARITY, NOT blind-fixed):**
- `/canon/` + `/daily/` output **frozen 2026-04-26** (box omits `render-canon-all`/`render-daily`/`render-edition`) while editions/storylines/wire are fresh → real staleness. **But** `canon_lists`/`canon_entries`=0 rows, so adding `render-canon-all` could clobber stale-but-present content with empty — deferred to WP-0.2b for data-safe handling.
- Box omits `build-search-index` (Cmd-K search may be stale) — verify consumer first.
- Box (collect+build) omits CFBD `ingest-cfbd-coaches`/`ingest-nfl-draft`/`scrape-wiki-awards` entirely — these are network ingestion and belong in `collect.ps1` (build is no-network by design), not here.
- `prediction-ledger`/`backfill-edition-citations` (populate the empty ledger/citations tables) routed to WP-1.5 receipts (council requires human-in-the-loop before public exposure).
**Blast radius:** 2 new stdlib scripts + one warn-only Run in build_publish.ps1. **Rollback:** delete the scripts + the Run block.
**Vibe-shifts note:** `/hub/vibe-shifts/index.html` is a 213B meta-refresh redirect to the latest dated ledger — intentional, not a stub (verifier now recognizes redirects).
