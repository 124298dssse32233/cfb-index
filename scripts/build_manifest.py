#!/usr/bin/env python3
"""Canonical build manifest — the single authoritative inventory of routes the
site MUST ship and the commands that produce site content across build paths.

WHY THIS EXISTS (WP-0.2, 2026-06-11)
------------------------------------
The box (``scripts/build_publish.ps1``) is the only live deployer and every
Vercel deploy is a FULL SNAPSHOT, so any route the box fails to generate is
clobbered off production. The box and the (retiring) cloud
``.github/workflows/publish_site.yml`` historically built DIFFERENT command
sets, which is how ``/offseason/`` and ``/film-room/`` ended up 404ing while
still linked in the global nav. This module is the one place that declares:

  * REQUIRED_NAV_ROUTES   — every global-nav / nav-action target (a 404 here is
                            a broken navigation promise → HARD requirement).
  * EXPECTED_SECTION_ROUTES — committed section pages the box renders (a miss is
                            a build gap → warn, then promote to hard once green).
  * COMMAND_PARITY        — the box-vs-cloud-vs-collect command classification,
                            so divergence is documented and can't silently drift.

``scripts/verify_build_manifest.py`` consumes REQUIRED_NAV_ROUTES /
EXPECTED_SECTION_ROUTES to assert the generated ``output/site`` is complete
before a deploy. Keep this file the source of truth — do not hardcode route
lists elsewhere.

Route paths are relative to the site root (``output/site``). Authoritative nav
list mirrors ``_site_nav()`` in ``src/cfb_rankings/reporting.py`` — keep in sync.
"""
from __future__ import annotations

# --- TIER 1: global-nav + nav-action targets (HARD requirement) -------------
# Mirrors reporting.py::_site_nav links + nav-actions. A 404 on any of these is
# a broken navigation promise visible on every page's header.
REQUIRED_NAV_ROUTES: list[tuple[str, str]] = [
    ("rankings", "rankings/index.html"),
    ("offseason", "offseason/index.html"),      # WP-0.1: now box-built
    ("film-room", "film-room/index.html"),      # WP-0.1: now box-built
    ("teams", "teams/index.html"),
    ("players", "players/spotlight.html"),
    ("heisman", "heisman/index.html"),
    ("vibe-shifts", "hub/vibe-shifts/index.html"),
    ("programs", "programs/index.html"),
    ("history", "history/index.html"),
    ("nfl-pipeline", "nfl-pipeline/index.html"),
    ("about-model", "about-model/index.html"),
    ("conferences", "conferences/index.html"),
    ("archive", "archive/index.html"),
    ("matchups", "matchups/index.html"),        # nav-action
    ("compare", "compare/index.html"),          # nav-action
]

# --- TIER 2: committed section pages the box renders (WARN, then promote) ----
EXPECTED_SECTION_ROUTES: list[tuple[str, str]] = [
    ("home", "index.html"),
    ("methodology", "methodology/index.html"),
    ("editions", "editions/index.html"),
    ("storylines", "storylines/index.html"),
    ("wire", "wire/index.html"),
    ("anniversary-today", "anniversary/today/index.html"),
    ("the-room", "players/the-room.html"),
    ("signature-stories", "players/signature-stories.html"),
    ("404", "404.html"),
]

# Bytes below which a generated index is treated as a likely empty stub (warn).
STUB_BYTE_THRESHOLD = 1500

# --- COMMAND PARITY: box vs cloud vs collect (documentation + drift guard) ----
# Classification of every site-producing command, so build-path divergence is
# explicit. "box" = scripts/build_publish.ps1 ; "cloud" = publish_site.yml
# (retiring) ; "collect" = scripts/collect.ps1.
#   status values:
#     "box"              - runs on the box (canonical) — good.
#     "collect"          - network ingestion; correctly lives in collect.ps1.
#     "cloud-setup-only" - DB init/seed/artifact-health; cloud-artifact specific,
#                          NOT appropriate for the box's canonical local DB.
#     "GAP-render"       - network-free RENDER the box omits → site content goes
#                          stale/missing. Candidate to add to the box (verify
#                          data first — see notes).
#     "GAP-derive"       - network-free DERIVED-table refresh the box omits →
#                          handle via the relevant Phase-1 WP (some are gated,
#                          e.g. receipts need human-in-the-loop per council).
#     "GAP-ingest"       - network ingestion the box pipeline omits entirely;
#                          belongs in collect.ps1, NOT build (no-network rule).
COMMAND_PARITY: list[dict[str, str]] = [
    # --- network-free RENDER gaps (box-omitted; cause stale/missing content) ---
    {"cmd": "render-canon-all", "status": "GAP-render",
     "note": "/canon/ frozen 2026-04-26. BUT canon_lists/canon_entries=0 rows — adding "
             "this could clobber stale-but-present content with empty. Verify canon "
             "data before wiring. Do NOT blind-add."},
    {"cmd": "render-daily", "status": "GAP-render",
     "note": "/daily/ frozen 2026-04-26. daily_editions=2 rows. Verify render is non-empty before wiring."},
    {"cmd": "render-edition", "status": "GAP-render",
     "note": "Per-edition pages. editions=4 rows. Box runs build-editions-archive (index) but not per-edition render."},
    {"cmd": "build-search-index", "status": "GAP-render",
     "note": "Cmd-K search index. Box omits → search may be stale. Verify consumer before wiring."},
    # --- network-free DERIVED gaps (route through Phase-1 WPs, not here) --------
    {"cmd": "prediction-ledger", "status": "GAP-derive",
     "note": "resolve_due_predictions (cli.py:7543) populates prediction_ledger (=0). "
             "Handle in WP-1.5 (receipts) — council requires human-in-the-loop before any public exposure."},
    {"cmd": "backfill-edition-citations", "status": "GAP-derive",
     "note": "Populates editorial_citations (=0). Same CP-1 class (cloud-only). Handle in WP-1.5/Phase-2 receipts."},
    {"cmd": "refresh-award-watch", "status": "GAP-derive", "note": "Offseason derived; player_award_watch_2026=160. Phase-1."},
    {"cmd": "refresh-depth-chart", "status": "GAP-derive", "note": "player_depth_chart_2026=513. Phase-1."},
    {"cmd": "refresh-portal-heat", "status": "GAP-derive", "note": "team_transfer_position_snapshot. Phase-1."},
    {"cmd": "refresh-recruiting-pulse", "status": "GAP-derive", "note": "recruiting derived. Phase-1."},
    # --- network INGESTION the box pipeline omits entirely (belongs in collect) -
    {"cmd": "ingest-cfbd-coaches", "status": "GAP-ingest", "note": "CFBD coaches. Not in collect.ps1 either → coaches go stale on the box. Add to collect, not build."},
    {"cmd": "ingest-nfl-draft", "status": "GAP-ingest", "note": "NFL draft. Same — belongs in collect.ps1."},
    {"cmd": "scrape-wiki-awards", "status": "GAP-ingest", "note": "Honors. Belongs in collect.ps1."},
    # --- cloud-artifact-specific setup (NOT for the box) ------------------------
    {"cmd": "init-db", "status": "cloud-setup-only", "note": "Cloud fresh-artifact bootstrap."},
    {"cmd": "apply-migrations", "status": "cloud-setup-only", "note": "Box DB already migrated; migrations applied out-of-band."},
    {"cmd": "seed-editions", "status": "cloud-setup-only", "note": "Seed."},
    {"cmd": "seed-feed-instances", "status": "cloud-setup-only", "note": "Seed."},
    {"cmd": "seed-player-id-anchor", "status": "cloud-setup-only", "note": "Seed."},
    {"cmd": "seed-priority-teams", "status": "cloud-setup-only", "note": "Seed."},
    {"cmd": "seed-source-registry", "status": "cloud-setup-only", "note": "Seed."},
    {"cmd": "force-reseed-feature", "status": "cloud-setup-only", "note": "Cloud reseed."},
    {"cmd": "repair-team-current-identity", "status": "GAP-derive", "note": "Identity maintenance — relevant to linkrot (WP-1.6). Phase-1."},
    {"cmd": "sync-team-locations", "status": "GAP-derive", "note": "Location maintenance. Phase-1."},
]


def gaps(kind: str | None = None) -> list[dict[str, str]]:
    """Return COMMAND_PARITY entries, optionally filtered to a status kind."""
    if kind is None:
        return [c for c in COMMAND_PARITY if c["status"].startswith("GAP")]
    return [c for c in COMMAND_PARITY if c["status"] == kind]


if __name__ == "__main__":
    print(f"REQUIRED_NAV_ROUTES: {len(REQUIRED_NAV_ROUTES)}")
    for k, p in REQUIRED_NAV_ROUTES:
        print(f"  [nav]     {k:16} -> {p}")
    print(f"EXPECTED_SECTION_ROUTES: {len(EXPECTED_SECTION_ROUTES)}")
    for k, p in EXPECTED_SECTION_ROUTES:
        print(f"  [section] {k:18} -> {p}")
    print(f"COMMAND_PARITY gaps: {len(gaps())} "
          f"(render={len(gaps('GAP-render'))} derive={len(gaps('GAP-derive'))} ingest={len(gaps('GAP-ingest'))})")
    for c in gaps():
        print(f"  [{c['status']}] {c['cmd']}: {c['note']}")
