"""Coverage Ratchet — Step 14.1 of docs/design-system/59-player-evidence-packet-contract.md.

DETERMINISTIC, ZERO-LLM, ZERO-NETWORK, ZERO-WRITES to output/site/ or the DB.

For the LIVE TOP-50 most-talked-about players, measures:
  coverage = captured_sources / available_sources
where AVAILABLE = evidence sources (doc 59 §13 map) that actually have rows for
the player, and CAPTURED = the subset the CURRENT live system already feeds the
writer.

Run:
    $env:PYTHONUTF8=1; python scripts/coverage_ratchet_story_cards.py
or just:
    python scripts/coverage_ratchet_story_cards.py   (with PYTHONUTF8=1 in env)

Outputs:
  - Human report to stdout.
  - scripts/coverage_baseline_story_cards.json (the committable machine baseline).
"""
from __future__ import annotations

import json
import os
import re
import sys

# Force UTF-8 on Windows Python 3.12 to prevent codec crashes on non-ASCII output.
os.environ.setdefault("PYTHONUTF8", "1")

# ---------------------------------------------------------------------------
# Path setup — must be first so cfb_rankings imports resolve.
# ---------------------------------------------------------------------------
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if os.path.join(_REPO_ROOT, "src") not in sys.path:
    sys.path.insert(0, os.path.join(_REPO_ROOT, "src"))

from cfb_rankings.config import AppConfig
from cfb_rankings.db import Database
from cfb_rankings import reporting as R
from cfb_rankings.player_pages.story_card import (
    build_card_payload,
    _llm_candidate_ids,
    resolve_external_id,
)
from cfb_rankings.player_pages.story_card_narrator import (
    assemble_evidence,
    _structured_fact_strings,
    _discourse_rows,
    _RELEVANCE_GATE,
    _TOXICITY_CEILING,
)
from cfb_rankings.player_pages.ledgers import fetch_ledger_lead

# ---------------------------------------------------------------------------
# Constants matching doc 59 §13 source map.
# ---------------------------------------------------------------------------
_SOURCE_NAMES = [
    "discourse",
    "before_after",
    "production",
    "recruiting",
    "honors",
    "award_watch",
    "depth_chart",
    "transfer",
    "aura",
    "succession",
    "ledger_take",
    "nil_narrative",
]

# NIL narrative keyword pattern (doc 59 §4.11 / §7).
_NIL_PATTERN = re.compile(
    r"\b(nil|collective|revenue[ -]?share|rev[ -]?share|holdout|buyout"
    r"|wanted more money|more money)\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Safe DB helpers — never raise into the coverage loop.
# ---------------------------------------------------------------------------
def _q1(db, sql: str, params: dict):
    try:
        return db.query_one(sql, params)
    except Exception:
        return None


def _qa(db, sql: str, params: dict):
    try:
        return db.query_all(sql, params) or []
    except Exception:
        return []


def _int(v):
    try:
        return int(v) if v is not None and v != "" else None
    except (TypeError, ValueError):
        return None


def _float(v):
    try:
        return float(v) if v is not None and v != "" else None
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Player-id resolution helpers.
# ---------------------------------------------------------------------------
def _pid_from_ext(db, external_id: str):
    row = _q1(
        db,
        "SELECT player_id FROM player_source_ids "
        "WHERE source_player_id=:ext AND source_name='cfbd' LIMIT 1",
        {"ext": str(external_id)},
    )
    return _int((row or {}).get("player_id"))


def _ext_from_pid(db, player_id: int):
    return resolve_external_id(db, player_id)


def _player_name(db, player_id: int) -> str:
    row = _q1(db, "SELECT full_name FROM players WHERE player_id=:pid", {"pid": player_id})
    return str((row or {}).get("full_name") or f"player:{player_id}")


# ---------------------------------------------------------------------------
# TOP-50 SELECTOR
# Order: aura mention_count DESC (non-low-signal, latest week, season),
# UNION _llm_candidate_ids importance pool, deduplicated, cap 50.
# ---------------------------------------------------------------------------
def build_top50(db, season: int) -> list[dict]:
    """Return list of {player_id, external_id, name, mention_count}."""

    # 1. Aura-first set: pick each player's latest week row.
    aura_rows = _qa(
        db,
        """
        SELECT paw.player_id,
               paw.mention_count
          FROM player_aura_weekly paw
         INNER JOIN (
               SELECT player_id, MAX(week) AS max_week
                 FROM player_aura_weekly
                WHERE season_year=:s
                  AND COALESCE(is_low_signal,0)=0
                GROUP BY player_id
         ) latest ON latest.player_id=paw.player_id
                 AND latest.max_week=paw.week
         WHERE paw.season_year=:s
           AND COALESCE(paw.is_low_signal,0)=0
         ORDER BY paw.mention_count DESC
        """,
        {"s": season},
    )

    ordered_pids: list[int] = []
    mention_map: dict[int, int] = {}
    seen: set[int] = set()

    for r in aura_rows:
        pid = _int(r.get("player_id"))
        if pid is None:
            continue
        if pid not in seen:
            ordered_pids.append(pid)
            seen.add(pid)
            mention_map[pid] = _int(r.get("mention_count")) or 0

    # 2. Importance pool (_llm_candidate_ids) — append any not already in set.
    try:
        importance_pids = _llm_candidate_ids(db, season)
    except Exception:
        importance_pids = []

    for pid in importance_pids:
        if pid not in seen:
            ordered_pids.append(pid)
            seen.add(pid)
            mention_map.setdefault(pid, 0)

    # 3. Cap at 50.
    ordered_pids = ordered_pids[:50]

    result = []
    for pid in ordered_pids:
        ext = _ext_from_pid(db, pid)
        name = _player_name(db, pid)
        result.append({
            "player_id": pid,
            "external_id": ext,
            "name": name,
            "mention_count": mention_map.get(pid, 0),
        })
    return result


# ---------------------------------------------------------------------------
# AVAILABILITY PROBES — one bool per source (doc 59 §13).
# Returns dict[source_name -> bool].
# ---------------------------------------------------------------------------
def probe_availability(db, player_id: int, external_id: str, season: int) -> dict[str, bool]:
    avail: dict[str, bool] = {}

    # --- discourse ---
    disc_rows = _discourse_rows(db, player_id, season)
    avail["discourse"] = len(disc_rows) > 0

    # --- before_after: current AND prior season stats row ---
    cur = _q1(
        db,
        "SELECT 1 AS ok FROM player_season_stats WHERE player_id=:pid AND season_year=:s LIMIT 1",
        {"pid": player_id, "s": season},
    )
    prior = _q1(
        db,
        "SELECT 1 AS ok FROM player_season_stats WHERE player_id=:pid AND season_year=:s LIMIT 1",
        {"pid": player_id, "s": season - 1},
    )
    avail["before_after"] = bool(cur) and bool(prior)

    # --- production: any wepa_* row for the season ---
    prod = _q1(
        db,
        "SELECT 1 AS ok FROM player_value_metrics WHERE player_id=:pid AND season_year=:s "
        "AND metric_name IN ('wepa_passing','wepa_rushing') LIMIT 1",
        {"pid": player_id, "s": season},
    )
    avail["production"] = bool(prod)

    # --- recruiting ---
    rec = _q1(
        db,
        "SELECT 1 AS ok FROM player_recruiting_profiles WHERE player_id=:pid LIMIT 1",
        {"pid": player_id},
    )
    avail["recruiting"] = bool(rec)

    # --- honors ---
    hon = _q1(
        db,
        "SELECT 1 AS ok FROM player_honors WHERE player_id=:pid LIMIT 1",
        {"pid": player_id},
    )
    avail["honors"] = bool(hon)

    # --- award_watch ---
    aw = _q1(
        db,
        "SELECT 1 AS ok FROM player_award_watch_2026 WHERE player_id=:pid LIMIT 1",
        {"pid": player_id},
    )
    avail["award_watch"] = bool(aw)

    # --- depth_chart ---
    dc = _q1(
        db,
        "SELECT 1 AS ok FROM player_depth_chart_2026 WHERE player_id=:pid LIMIT 1",
        {"pid": player_id},
    )
    avail["depth_chart"] = bool(dc)

    # --- transfer: any transfer_entries row (player_id = this player) ---
    te = _q1(
        db,
        "SELECT 1 AS ok FROM transfer_entries WHERE player_id=:pid LIMIT 1",
        {"pid": player_id},
    )
    avail["transfer"] = bool(te)

    # --- aura: any non-low-signal player_aura_weekly row ---
    au = _q1(
        db,
        "SELECT 1 AS ok FROM player_aura_weekly WHERE player_id=:pid AND season_year=:s "
        "AND COALESCE(is_low_signal,0)=0 LIMIT 1",
        {"pid": player_id, "s": season},
    )
    avail["aura"] = bool(au)

    # --- succession: any row where this player is the incumbent (player_external_id) ---
    succ = _q1(
        db,
        "SELECT 1 AS ok FROM player_succession WHERE player_external_id=:ext LIMIT 1",
        {"ext": str(external_id)},
    )
    avail["succession"] = bool(succ)

    # --- ledger_take: fetch_ledger_lead non-null ---
    try:
        lead = fetch_ledger_lead(db, external_id, season, None)
        avail["ledger_take"] = lead is not None
    except Exception:
        avail["ledger_take"] = False

    # --- nil_narrative: any discourse doc whose text matches NIL/money keywords ---
    nil_found = False
    if disc_rows:
        for r in disc_rows:
            body = (str(r.get("body_text") or "") + " " + str(r.get("title_text") or "")).strip()
            if body and _NIL_PATTERN.search(body):
                nil_found = True
                break
    avail["nil_narrative"] = nil_found

    return avail


# ---------------------------------------------------------------------------
# CAPTURE PROBES — what the CURRENT system actually surfaces.
# Builds the payload and evidence pool, then inspects what made it through.
# Returns dict[source_name -> bool].
# ---------------------------------------------------------------------------
def probe_capture(
    db,
    player_id: int,
    external_id: str,
    season: int,
    avail: dict[str, bool],
) -> dict[str, bool]:
    cap: dict[str, bool] = {k: False for k in _SOURCE_NAMES}

    payload = build_card_payload(db, player_id, season)
    if payload is None:
        return cap

    pool = assemble_evidence(db, payload, audience="national")
    facts = _structured_fact_strings(payload)
    facts_text = " ".join(facts)

    # MEASURE WHAT THE WRITER ACTUALLY RECEIVES (doc 59 step 14.4). The Packet
    # Builder now lifts the §4 structured spine + the high-salience NIL discourse
    # into assemble_evidence's pool, each carrying a stable ``source_id`` whose
    # prefix names the source table. CAPTURED = a non-empty evidence entry with
    # that prefix is in the pool the writer + grounding gate see. This is NOT a
    # count of DB rows (the availability probe owns that) — it counts only what
    # survived suppression, C7, de-dup, and the cap and reached the writer.
    def _pool_has_prefix(prefix: str) -> bool:
        for e in pool:
            sid = str(e.get("source_id") or "")
            if sid.startswith(prefix) and str(e.get("text") or "").strip():
                return True
        return False

    # --- discourse captured: pool has any kind=='discourse' ---
    cap["discourse"] = any(e.get("kind") == "discourse" for e in pool)

    # --- aura captured: the aura/BAN row reached the writer (packet aura fact in
    #     the pool) OR the deterministic BAN fired on the card. ---
    cap["aura"] = _pool_has_prefix("row:player_aura_weekly:") or payload.ban is not None

    # --- before_after captured: a genuine prior-season delta or WEPA envelope from
    #     the packet's player_season_stats / player_value_metrics facts. ---
    cap["before_after"] = (
        _pool_has_prefix("row:player_season_stats:")
        or _pool_has_prefix("row:player_value_metrics:")
    )

    # --- production captured: the WEPA durable signal reached the writer (packet
    #     value-metrics fact) OR the BAN/facts carry a WEPA value. ---
    wepa_in_ban = False
    if payload.ban is not None:
        wepa_in_ban = "WEPA" in str(getattr(payload.ban, "label", "") or "")
    wepa_in_facts = "WEPA" in facts_text.upper() or "wepa" in facts_text.lower()
    cap["production"] = (
        _pool_has_prefix("row:player_value_metrics:") or wepa_in_ban or wepa_in_facts
    )

    # --- succession captured: the packet succession frame reached the pool OR the
    #     card's structured spine emitted a succession line. ---
    succ_captured = (
        payload.succession is not None
        and (
            getattr(payload.succession, "predecessor_name", None)
            or getattr(payload.succession, "heir_name", None)
            or getattr(payload.succession, "clock_line", None)
        )
    )
    cap["succession"] = _pool_has_prefix("row:player_succession:") or bool(succ_captured)

    # --- ledger_take captured: the packet ledger fact reached the pool OR the card's
    #     dominant_take fired. ---
    cap["ledger_take"] = (
        _pool_has_prefix("row:player_ledger_scores:")
        or payload.dominant_take is not None
    )

    # --- recruiting / honors / award_watch / depth_chart: the Packet Builder lifts
    #     each as a structured fact into the pool with a table-named source_id. A
    #     source is captured only when a non-empty fact with that prefix survived to
    #     the writer (suppressed facts were already dropped by the adapter). ---
    cap["recruiting"] = _pool_has_prefix("row:player_recruiting_profiles:")
    cap["honors"] = _pool_has_prefix("row:player_honors:")
    cap["award_watch"] = _pool_has_prefix("row:player_award_watch_2026:")
    cap["depth_chart"] = _pool_has_prefix("row:player_depth_chart_2026:")

    # --- transfer captured: the packet portal/draft fact reached the pool OR the
    #     card's why_now/facts mention a transfer. ---
    transfer_in_facts = "changed programs" in facts_text.lower() or "transfer" in facts_text.lower()
    transfer_why_now = "changed programs" in (payload.why_now or "").lower()
    cap["transfer"] = (
        _pool_has_prefix("row:transfer_entries:")
        or _pool_has_prefix("row:player_nfl_draft:")
        or transfer_in_facts
        or transfer_why_now
    )

    # NIL narrative: captured only if a discourse doc with NIL keywords made it
    # into the pool (the pool is C7-filtered and de-duped, but NIL/money docs
    # are never-truncate per §7 — the packet lifts the high-salience NIL doc and
    # assemble_evidence keeps a keyword-anchored window so the money language
    # survives). Detected by scanning the discourse-kind pool text for the keywords.
    nil_in_pool = False
    for e in pool:
        if e.get("kind") == "discourse":
            text = e.get("text", "")
            if _NIL_PATTERN.search(text):
                nil_in_pool = True
                break
    cap["nil_narrative"] = nil_in_pool

    return cap


# ---------------------------------------------------------------------------
# PER-PLAYER COVERAGE
# ---------------------------------------------------------------------------
def measure_player(db, p: dict, season: int) -> dict:
    """Measure one player. Returns a row dict with avail/cap bools + coverage float."""
    pid = p["player_id"]
    ext = p["external_id"]
    name = p["name"]

    if ext is None:
        return {
            "player_id": pid,
            "external_id": None,
            "name": name,
            "mention_count": p.get("mention_count", 0),
            "available": {},
            "captured": {},
            "available_count": 0,
            "captured_count": 0,
            "coverage": 0.0,
            "error": "no_external_id",
        }

    avail = probe_availability(db, pid, ext, season)
    cap = probe_capture(db, pid, ext, season, avail)

    avail_count = sum(1 for v in avail.values() if v)
    # Only count captured where available.
    cap_count = sum(1 for k in _SOURCE_NAMES if avail.get(k) and cap.get(k))
    coverage = cap_count / avail_count if avail_count > 0 else 0.0

    return {
        "player_id": pid,
        "external_id": ext,
        "name": name,
        "mention_count": p.get("mention_count", 0),
        "available": avail,
        "captured": cap,
        "available_count": avail_count,
        "captured_count": cap_count,
        "coverage": round(coverage, 4),
        "error": None,
    }


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def run():
    db = Database(AppConfig.from_env().database_url)
    summary, _ = R.fetch_latest_rankings(db, limit=1000)
    season = int(summary["season_year"])

    print(f"Coverage Ratchet — Season {season}")
    print(f"{'='*60}")

    top50 = build_top50(db, season)
    print(f"Top-50 pool resolved: {len(top50)} players")

    rows = []
    errors = 0
    for i, p in enumerate(top50, 1):
        pid = p["player_id"]
        name = p["name"]
        try:
            row = measure_player(db, p, season)
        except Exception as exc:
            row = {
                "player_id": pid,
                "external_id": p.get("external_id"),
                "name": name,
                "mention_count": p.get("mention_count", 0),
                "available": {},
                "captured": {},
                "available_count": 0,
                "captured_count": 0,
                "coverage": 0.0,
                "error": str(exc),
            }
            errors += 1
        rows.append(row)

    # Aggregate per-source stats.
    source_avail_counts = {s: 0 for s in _SOURCE_NAMES}
    source_cap_counts = {s: 0 for s in _SOURCE_NAMES}
    total_players_with_avail = 0

    for r in rows:
        if r.get("error"):
            continue
        has_any = r["available_count"] > 0
        if has_any:
            total_players_with_avail += 1
        for s in _SOURCE_NAMES:
            if r["available"].get(s):
                source_avail_counts[s] += 1
                if r["captured"].get(s):
                    source_cap_counts[s] += 1

    # Aggregate mean coverage (across players with at least one available source).
    valid_rows = [r for r in rows if not r.get("error") and r["available_count"] > 0]
    aggregate_coverage = (
        sum(r["coverage"] for r in valid_rows) / len(valid_rows) if valid_rows else 0.0
    )

    # Per-source available% and captured% (as % of players in the top-50 set).
    n = len(top50)
    per_source = {}
    for s in _SOURCE_NAMES:
        avail_pct = round(100.0 * source_avail_counts[s] / n, 1) if n else 0.0
        # captured% = captured / available (not / n)
        cap_pct = (
            round(100.0 * source_cap_counts[s] / source_avail_counts[s], 1)
            if source_avail_counts[s] > 0
            else 0.0
        )
        per_source[s] = {"available_pct": avail_pct, "captured_pct": cap_pct}

    # 5 lowest-coverage players (valid only).
    lowest = sorted(valid_rows, key=lambda r: r["coverage"])[:5]

    # ---------------------------------------------------------------------------
    # Human report
    # ---------------------------------------------------------------------------
    print(f"\nPer-source coverage (available% = fraction of top-50 that have the data;")
    print(f"captured% = fraction of those that the current system surfaces):")
    print(f"{'Source':<20} {'Available%':>12} {'Captured%':>12}")
    print(f"{'-'*46}")
    for s in _SOURCE_NAMES:
        ps = per_source[s]
        print(f"{s:<20} {ps['available_pct']:>11.1f}% {ps['captured_pct']:>11.1f}%")

    print(f"\nAggregate mean coverage across {len(valid_rows)} valid players: {aggregate_coverage:.1%}")
    print(f"Errors: {errors}")

    print(f"\n5 lowest-coverage players:")
    for r in lowest:
        avail_sources = [s for s in _SOURCE_NAMES if r["available"].get(s)]
        cap_sources = [s for s in _SOURCE_NAMES if r["available"].get(s) and r["captured"].get(s)]
        print(
            f"  {r['name']!r:<40} cov={r['coverage']:.1%}  "
            f"avail={r['available_count']}({','.join(avail_sources)})  "
            f"cap={r['captured_count']}({','.join(cap_sources)})"
        )

    # ---------------------------------------------------------------------------
    # Machine baseline JSON
    # ---------------------------------------------------------------------------
    baseline = {
        "season": season,
        "top50_player_ids": [p["player_id"] for p in top50],
        "top50_names": [p["name"] for p in top50],
        "aggregate_coverage": round(aggregate_coverage, 4),
        "per_source": per_source,
        "lowest_5_players": [
            {
                "player_id": r["player_id"],
                "name": r["name"],
                "coverage": r["coverage"],
                "available_count": r["available_count"],
                "captured_count": r["captured_count"],
            }
            for r in lowest
        ],
        "per_player": [
            {
                "player_id": r["player_id"],
                "external_id": r["external_id"],
                "name": r["name"],
                "mention_count": r["mention_count"],
                "available": r["available"],
                "captured": r["captured"],
                "available_count": r["available_count"],
                "captured_count": r["captured_count"],
                "coverage": r["coverage"],
                "error": r.get("error"),
            }
            for r in rows
        ],
        "errors": errors,
        "note": (
            "Baseline generated by scripts/coverage_ratchet_story_cards.py "
            "(doc 59 step 14.1). Coverage can only go UP from here — CI ratchet."
        ),
    }

    out_path = os.path.join(_REPO_ROOT, "scripts", "coverage_baseline_story_cards.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(baseline, f, indent=2, ensure_ascii=False)

    print(f"\nBaseline written to: {out_path}")
    print(f"Top-50 count: {len(top50)}")
    return baseline


if __name__ == "__main__":
    run()
