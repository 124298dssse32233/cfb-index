# CFB Index Site-Quality — Implementation Progress Log

**Branch:** `feature/site-quality-2026-06-11` · **Started:** 2026-06-11 · **Scope:** `/octo:embrace` Phase 0→4 (see [Define manifest](site_quality_define_2026-06-11.md), [Discover](site_quality_discover_2026-06-11.md)).
**Rules in force:** isolated branch · no prod deploy without explicit user approval · no DB hand-edits · no new recurring product cost · design tie → keep existing · small reviewable commits per WP · verify before claiming done.

> **Build-safety note:** `scripts/build_publish.ps1` deploys at line ~241 (`publish_to_vercel.ps1`). **Never run it whole** during dev — verify generators by invoking them directly (they only write gitignored `output/site`).

## Status board

| WP | Title | Status | Commit | Evidence |
|---|---|---|---|---|
| 0.1 | Box build generates /offseason/ + /film-room/ | ✅ done | `3647cdb` | hub scripts wired into build_publish.ps1 post-build block; both emit non-stub (offseason 90KB/125 rows/5 boards, film-room 13KB/4 boards); PS parses clean |
| 0.2 | Canonical build manifest (full command-set parity) | ✅ done (infra) | `622e548` | `build_manifest.py` (15 nav + 9 section routes + 15-command parity table) + `verify_build_manifest.py` (15/15 pass, redirect-aware) wired warn-only into box build; PS parses clean |
| 0.2b | Reconcile safe box-omitted RENDER gaps (render-daily/-edition; canon) | ⏳ follow-up | — | surfaced by 0.2: /canon/ + /daily/ frozen 2026-04-26; canon_lists/entries=0 (don't blind-add render-canon-all) |
| 0.3 | Smoke + build assertions on every nav target | ✅ done | `4ed8f28` | smoke now covers all 15 nav routes (+7 added); build-assertion side = WP-0.2 verifier (warn) → WP-0.6 (hard). Found 5 healthy-but-unmonitored routes (nfl-pipeline/archive/matchups/spotlight/the-room) |
| 0.6 | Pre-deploy snapshot-completeness guard (Gate B) | ✅ done | (this commit) | hard `--strict` route gate added to publish_to_vercel.ps1 before deploy; verified fail-closed (empty snapshot → 15 MISSING → exit 1/abort); PS parses clean |
| 0.5 | Correct DATA_SOURCES doc + refresh AGENTS.md | ✅ done | (this commit) | DATA_SOURCES cadence column now measured-from-scrape_health (Kalshi/SeatGeek "Not collecting", YT-comments/GDELT-tone flagged, Polymarket prob caveat); AGENTS.md gets a STALE→CLAUDE.md banner |
| 0.4 | Row-count/freshness/coverage/provenance guards | ✅ done | (this commit) | new `verify_data_floors.py`: provenance ratchet (source_id %, high-water 22.3%) + 7 factual-spine floors; verified positive (exit 0) + negative (breach→exit 1); wired non-critical into box build; complements (no dup of) module/source guards |
| 0.7 | Provenance labeling (legacy_unverified) | ✅ done | (this commit) | idempotent `backfill_provenance_status.py` (canonical 43,479 / legacy_unverified 151,493 via dry-run; write/idempotent/revert proven on synthetic DB; **live DB untouched**); wired non-critical into box build → labels post-merge |

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

### WP-0.3 — Smoke covers every nav target — ✅ 2026-06-11
**Problem (CP-3):** live smoke (`scripts/smoke_test_live.py`, `--fail-under 95`) omitted globally-linked routes → 404s never alarmed. Reconciling against `build_manifest.REQUIRED_NAV_ROUTES` showed it missed **7**, not just 2.
**Change:** added `/offseason/`, `/film-room/`, `/nfl-pipeline/`, `/archive/`, `/matchups/`, `/players/spotlight.html` (the real "Players" nav target — smoke only had the `/players/` dir), `/players/the-room.html`. (Build-time assertion side is covered by WP-0.2 verifier, hard-gated in WP-0.6.)
**Verification (2026-06-11, live prod):** `nfl-pipeline / archive / matchups / players-spotlight / the-room` → **200** (healthy but previously unmonitored). `offseason / film-room` → **404** (correctly broken until the WP-0.1 box deploy ships). `ast.parse` clean; 39 URLs total.
**Effect once merged + deployed:** all 39 pass. If merged before deploy, smoke correctly reports the 2 known 404s (honest — stops masking). No live effect yet (feature branch; workflow runs from master).
**Blast radius:** smoke URL list only. **Rollback:** remove the 7 entries.

### WP-0.6 — Pre-deploy snapshot-completeness guard (Gate B) — ✅ 2026-06-11
**Problem:** the clobber root cause — a full-snapshot deploy of an output/site missing a nav route silently removes that route from prod, with nothing to stop it.
**Change:** added gate **1c** to `scripts/publish_to_vercel.ps1` (the actual deploy step, runs before any Vercel interaction, independent of caller so manual publishes are gated too): `verify_build_manifest.py --strict --emit` against `$SITE`; on non-zero, `ABORT (exit 6)` — the previous good deploy stays live. Slots into the existing gate stack (file-count → verify-publish-readiness → manifest-freshness → **nav-completeness** → deploy → per-deploy smoke → alias).
**Verification (2026-06-11):**
- PS parses clean.
- Positive: real `output/site` `--strict` → exit 0 (deploy proceeds).
- Negative (fail-closed): empty dir `--strict` → "15 MISSING", exit 1 → would ABORT. Gate fails closed.
**Effect:** the offseason/film-room clobber class is now structurally impossible — any build that drops a nav route refuses to deploy rather than clobbering prod.
**Blast radius:** one gate block in publish_to_vercel.ps1. **Rollback:** remove gate 1c.

### WP-0.5 — Data-source docs reflect measured reality — ✅ 2026-06-11
**Problem (CP-6):** `DATA_SOURCES_EXPLAINED.md` listed Kalshi/SeatGeek/YouTube-comments/GDELT-tone as "Daily" though measured `scrape_health` shows them empty/stale; `AGENTS.md` was stale (17-slug, pre-cutover deploy text).
**Change:**
- `DATA_SOURCES_EXPLAINED.md`: renamed the at-a-glance table to "every **registered** source"; "How often" → "Cadence (measured 2026-06-11)"; split Polymarket/Kalshi into separate rows; flagged Kalshi+SeatGeek "Not collecting", YouTube-comments "Intermittent", GDELT-tone "stale", Polymarket "volume only"; added a ⚠️ measured-status note + link to Discover §10.
- `AGENTS.md`: added a STALE banner at top pointing to CLAUDE.md as canonical, naming the two wrong facts (17 vs 119/119 slugs; pre-2026-06-10-cutover deploy section).
**Verification (2026-06-11):** edits applied; table keeps 4-column structure; claims now match the `scrape_health` query in Discover §0/§1.
**Blast radius:** 2 docs. **Rollback:** revert the doc edits.

### WP-0.4 — Data-floor guard: provenance ratchet + factual-spine floors — ✅ 2026-06-11
**Problem (CP-4 + memory `build-failure-philosophy`):** existing guards watch raw-source ingestion (`verify_source_health_floors`) and computed-module tables (`verify_module_coverage`), but NOT (a) `conversation_documents` source_id provenance, or (b) the factual spine (games/players/ratings) going near-empty in a broken build.
**Change:** new `scripts/verify_data_floors.py` (read-only, stdlib) —
- **Provenance ratchet:** `source_id` coverage must stay within 0.5pp of its all-time high; the high-water mark only ratchets UP, so WP-0.7 progress becomes the new floor. State in gitignored `data/data_floors_baseline.json` (mirrors `module_coverage_history.json`).
- **Spine floors:** absolute conservative mins (~½ of healthy 2026-06-11 counts) for games/players/player_game_stats/power_ratings_weekly/resume_ratings_weekly/team_rating_deltas/roster_entries — fire only on catastrophic emptiness.
- Wired non-critical into `build_publish.ps1` verify cluster.
**Verification (2026-06-11):**
- Positive: exit 0; baseline initialized to 22.3%; spine all above floor (games 12,111 / players 61,381 / pgs 1,769,283 / power 47,617 / resume 40,667 / deltas 13,954 / rosters 33,765).
- Negative: baseline pinned to 99% → "provenance:source_id_pct breached", exit 1.
- `build_publish.ps1` parses clean.
**Blast radius:** 1 new stdlib script + 1 non-critical Run + 1 .gitignore line. **Rollback:** delete script + Run + gitignore line.

### WP-0.7 — Provenance labeling (canonical vs legacy_unverified) — ✅ 2026-06-11
**Problem (CP-4):** 78% of conversation_documents lack a canonical source_id (legacy reddit/youtube/board). Council ruling: **label legacy rows, do NOT infer an id** (inferring risks silent mis-attribution / corrupts the audit trail).
**Change:** `scripts/backfill_provenance_status.py` — idempotent, reversible, defensive (adds `provenance_status` column if missing). Sets `canonical` (source_id present) / `legacy_unverified` (source_id NULL). `--dry-run` (read-only report), `--revert` (rollback to NULL). Wired non-critical into `build_publish.ps1` so the box keeps provenance honest every build.
**Verification (2026-06-11):**
- Dry-run vs **live DB (read-only)**: total 194,972 / canonical 43,479 (22.3%) / legacy_unverified 151,493. **No mutation.**
- Synthetic 6-row DB: label → `{canonical:3, legacy_unverified:3}`; re-run idempotent (+0/+0); `--revert` → all NULL. Write path proven.
- Confirmed the **live `cfb_rankings.db` was NOT mutated** (no `provenance_status` column) — responsible-autonomy: no unsupervised production-DB write. The box labels at the next build post-merge (idempotent, .bak-protected by the deploy flow).
**Design note:** label-only, no inference (council). The deeper fix — legacy collectors (reddit_rss_*) still write NULL source_id, so the gap grows daily — is a separate collector change (flagged as a follow-up, not this WP).
**Blast radius:** 1 new stdlib script + 1 non-critical Run. **Rollback:** `--revert` or restore from .bak; remove the Run.

### Adversarial code review + hardening — ✅ 2026-06-11
An independent reviewer (full repo access) audited the Phase-0 diff. **Verdict: safe to keep, no blocking issues.** It empirically debunked the scariest risk — the `$LASTEXITCODE`/`Tee-Object` deploy-gate concern: Python's exit code DOES propagate through `Tee-Object` (cmdlets don't overwrite it), and gate 1c uses the same proven pattern as the production gate 1b, so the deploy gate is real and fail-safe (verified exit 0/1/2 → abort on any non-zero). Four findings; fixed 3, documented 1:
- **#2 (medium, fixed):** strict route gate was fail-OPEN on present-but-empty *stub* nav pages (a gutted 200 would clobber prod and pass). Now `--strict` FAILS on non-redirect nav stubs too. Verified: 17B rankings stub → FAIL/exit 1; real output still exit 0.
- **#3 (low, fixed):** redirect routes now verify their *target* exists (a redirect→404 would have passed). Verified: redirect→missing → FAIL.
- **#4 (low, fixed):** `verify_data_floors.py` baseline now read with `utf-8-sig` + logs on parse failure (a BOM'd hand-edit silently disabled the ratchet). Verified: BOM baseline now read → breach detected.
- **#1 (medium, documented):** live smoke now sits at its exact 2-failure budget (41 URLs @ --fail-under 95) because offseason/film-room 404 until deploy. Added a ⚠️ MERGE/DEPLOY-ORDER note in `smoke_test_live.py`: ship the WP-0.1 box deploy before/with merging the smoke change, or one transient flake opens spurious alerts.
**Files:** `verify_build_manifest.py`, `verify_data_floors.py`, `smoke_test_live.py`. All re-verified.
