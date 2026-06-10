# Implementation kickoff prompt (paste into the build window)

Copy everything in the block below into the task window that owns the generator.

---

```
You are implementing the CFB Index RANKINGS REDESIGN into the static-site generator. The complete
design + spec package is finished and frozen in docs/octopus/ — your job is to BUILD it 1:1, not to
redesign it. The design window that produced the package is done and will NOT touch reporting.py; you
own the generator.

START HERE
- Read docs/octopus/rankings_redesign_BUILD_MANIFEST.md in full, then the docs in its §1 read-order.
  The manifest is the source of truth: verified data-readiness ledger (§3), phased build sequence (§4),
  Definition of Done (§5), open-decisions register (§6), and the OD-1 token-scoping recipe (§2a).
- Preview the target: python -m http.server 4599 --directory docs/octopus/mockups → open index.html.
  rankings-mobile.html and desktop-board.html are the board; states.html shows every loading / empty /
  error / Awaiting-Signal state you must implement.

HOUSE RULES (from CLAUDE.md — non-negotiable)
- Edit the generator (src/cfb_rankings/…). NEVER edit output/site/** (generated).
- reporting.py is ~26.8k lines — grep for the symbols named below; do NOT trust line numbers, they drift.
- Build with: python -u manage.py build-site. Don't hand-edit the DB.
- programs/<slug>.html is flat by design; /assets/... paths are absolute on purpose. Don't "fix" either.
- Work on a feature branch; commit incrementally; keep the build green at every commit.

SCOPE THIS PASS = PHASE 0 + PHASE 1 ONLY (the board, on data that already exists).
Do NOT start the net-new modeling workstreams — Model Report Card schema/ingest, the playoff-odds
engine, and numeric Tri-Rank are flagged ⛔ in manifest §3/§6 as prerequisites with their own owner
decisions. Build the board with the existing-data fallbacks, then STOP and propose Phase 2.

PHASE 0 — foundations (do first)
1. Materialize docs/octopus/mockups/cfb-tokens.css into a production source and emit it to
   /assets/css/cfb-tokens.css. Add /assets/css/rankings-board.css (port the mock CSS, mapped to the
   --color-* tokens) and /assets/js/rankings-board.js (keep JS < 50KB total).
2. APPLY THE OD-1 SCOPING RECIPE EXACTLY (manifest §2a). This is the #1 risk — it protects the
   dark/Inter team pages:
     - Load these page-scoped INSIDE render_rankings_page_html / render_conference_page_html /
       render_archive_snapshot_html — NOT in the global _global_link_tags().
     - Scope ALL tokens + base styles under a .cfb-rkx wrapper; emit <body class="cfb-rkx"> on those
       three surfaces only; re-scope the tabular-nums and dark-mode blocks under .cfb-rkx.
     - Do NOT use @layer (unlayered legacy CSS would beat it). Rely on the wrapper's specificity.
     - Verify the command palette (cmdk.css) still themes correctly on the rankings page, and that a
       team page (e.g. /teams/alabama) is visually UNCHANGED.
3. team_logo_url(slug) via resolve_team_brand(slug).logo_local_path; emit the monogram (.fb) fallback.

PHASE 1 — the board (surgical in reporting.py; follow manifest §4 Phase-1 checklist)
- Rewrite _render_rankings_row() to the v5 .row DOM (component spec §6): .tcr · .rk+.mom · .logo(.fb) ·
  .nm(.star) · .meta(.conf,.bchip) · .pow(.v + inline #rank) · .chev, plus a <details name> drawer stub.
- .bchip = archetype belief label, and "Awaiting signal" (gray) below MIN_MENTIONS_FOR_SIGNAL — never a
  0/blank (component spec §7, microcopy §5.3).
- _render_finding_banner(); CFP .cutline after rank 12; provenance footer.
- Lens tabs (Power/Résumé/Bettor/Belief) + filter chips in _rankings_board_script(): :has() filtering,
  result-count aria-live, roving-tabindex tablist, server-rendered default sort.
- SEO: schema.org ItemList JSON-LD for the Top 25; content-visibility chunking + lazy deep board.
- Loading / empty / error states exactly as states.html shows them; EVERY string comes from the
  microcopy spec — do not ad-lib copy.
- P0 spike (parallel, optional): compute_implied_ranks() to upgrade .bchip to numeric "Fans +N" and add
  the inline Tri-Rank m·r·n cell on desktop. The board MUST ship with the archetype-label fallback if the
  spike isn't ready.

VERIFIED ANCHORS (don't re-audit — grep to confirm current lines)
- RankingRow @ reporting.py (~line 131): has rank, team_id, slug, team_name, level_code,
  conference_name, power_rating, resume_score, cross_level_confidence, schedule_connectivity,
  previous_rank, rank_change, power_display, resume_display, power_percentile, resume_percentile,
  resume_rank. (tier is only available via getattr(row,'tier','all').)
- CSS/JS registration: _global_link_tags() @ ~6279 (GLOBAL — do NOT add redesign CSS here; see OD-1).
- Loaders: resolve_team_brand (visual_assets.py), render_percentile_bar (theme/percentile_bar.py),
  fetch_team_mood_profile / fetch_fan_intel_board (fan_intelligence.py; the board loader needs the 4th
  team_index arg), fetch_savant_rows / fetch_arc_rows (team_pages). MIN_MENTIONS_FOR_SIGNAL=12 @
  fan_intelligence.py:33.
- Δ / momentum / bump re-derive from power_ratings_weekly × model_runs (there is NO ranking_snapshots
  table). Off/Def efficiency does NOT exist — omit those desktop KenPom columns this pass.
- compute_implied_ranks does NOT exist yet (net-new P0). Playoff odds are net-new — only the
  deterministic compute_season_path_projections() (team_preview/__init__.py) exists; omit the playoff
  dotplot/CFP% column until a probabilistic layer is built.

DEFINITION OF DONE (manifest §5 — gate every commit)
- Matches the mockup at 390 / 768 / 1280 (responsive spec). --color-* tokens only — no literal hex/px
  outside var(--…).
- Every value comes from a real loader or its specified empty state — never 0, blank, or "N/A".
- WCAG 2.2 AA: focus-visible 2px navy ring on every control; ≥48px targets; nothing color-only; every
  chart role="img" + finding-stating aria-label (microcopy §6) + a visually-hidden data-table fallback;
  aria-sort/aria-live on sortable headers.
- Perf: FCP<1.5s, INP<200ms, JS<50KB, critical CSS<10KB, Lighthouse ≥95, no CLS.
- SEO/no-JS: Top 25 server-rendered and crawlable with JS disabled (curl + grep the team names proves it).
- Regression: python -u manage.py build-site green; tests/integration/test_cross_links.py passes.

WORKING STYLE
- Do Phase 0, then verify the scoping isolation (rankings page styled, a team page UNCHANGED) before
  moving on. Commit.
- Phase 1 in small commits; verify after each (build green + a quick render check).
- When Phase 1 is done and green, STOP and report: what shipped, the no-JS + Lighthouse results, and a
  proposed Phase 2 plan for the net-new workstreams (Tri-Rank numerics, playoff projection, Model Report
  Card). Do not auto-start the net-new modeling.
```

---

*Notes for Kevin (don't paste): the package is design-only and frozen; this prompt keeps the build window
to the existing-data board first (low risk, ~70% of the visual leap) and makes it stop before the four
net-new modeling builds so you can sequence those deliberately. The OD-1 scoping step is the one that
protects your live team pages — it's called out as the #1 risk on purpose.*
