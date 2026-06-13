"""Freshness / source-instance inventory pillar.

The spec's hardest-won refinement (codex): ``scrape_health`` is NOT the source
inventory — it is an *observation log* (443 instances ever seen, including dead /
historical ones). ``source_registry`` is the *class catalog* (79 classes). This
pillar reconciles the two:

  * take the **latest run per instance** (per ``source_id``) from ``scrape_health``,
  * classify each instance onto a registry **source class** (exact match, then a
    reviewed single-class prefix auto-map, else ``unclassified`` — never guessed
    into a multi-class parent), and
  * derive a freshness **state** from the latest status (+ a cadence-overdue check
    for instances with enough ok-run history to establish a rhythm).

It returns one summary ``CheckResult`` per source class (rolling up that class's
instances) plus a single overall counts result. Severity is ``warning`` across
the board: a stale / erroring collector is a schedule miss (YELLOW), not a
corrupt-DB critical (RED) — that distinction is what keeps the gate trusted.

Verified live picture this MUST reproduce (read-only against ``cfb_rankings.db``,
2026-06-11): 443 instances; latest status ok=304, error=80, empty=56, skipped=3
=> **136 unhealthy** (80 error + 56 empty); ``athletics_template`` = **19/21
error**; ~180 instances ``unclassified`` (the reddit/substack/beat/youtube/board
multi-class prefixes that require reviewed config, not a guess).

Stdlib + raw sqlite3 only; strictly read-only.
"""
from __future__ import annotations

import sqlite3
import statistics
from collections import defaultdict
from datetime import datetime

from .base import CheckResult
from ..source_prefix_map import classify_instance

name = "freshness"

# --- Prefix-mapping policy (from the spec's reconciliation algorithm) ------
#
# Single-class prefixes auto-map cleanly to their one registry class. These four
# are the ONLY prefixes the spec authorises to auto-map by string prefix, because
# each has exactly one class in ``source_registry`` and a stable naming scheme:
#   athletics_* -> athletics_template ; campus_* -> campus_template ;
#   locked_*    -> locked_on_template ; google_* -> google_trends_dma
SINGLE_CLASS_PREFIXES: dict[str, str] = {
    "athletics": "athletics_template",
    "campus": "campus_template",
    "locked": "locked_on_template",
    "google": "google_trends_dma",
}

# Multi-class prefixes fan out to several registry classes (reddit->4, substack->10,
# beat->13, youtube->3, board->3). The spec is explicit: do NOT auto-parent these
# by string prefix. An instance that does not match a class exactly is handed to the
# reviewable name-based HEURISTIC in ``source_prefix_map.classify_instance`` (e.g.
# ``reddit_rss_<known-team-slug>`` -> ``reddit_team``); only if THAT also declines
# does the instance stay ``unclassified`` and visible for human review — never
# silently mis-attributed.
MULTI_CLASS_PREFIXES: frozenset[str] = frozenset(
    {"reddit", "substack", "beat", "youtube", "board"}
)

UNCLASSIFIED = "unclassified"

# Reddit registry classes whose PRIMARY collector is the Arctic Shift / pullpush
# archive path (~96% of reddit docs), which logs to ``conversation_collection_runs``
# — a table this scrape_health-based reconciliation is otherwise BLIND to. Their
# ``scrape_health`` rows are the vestigial ``reddit_backfill_*`` RSS instances
# (~3% superseded path) that read "stale" even while the archive collector is live.
_REDDIT_ARCHIVE_CLASSES: frozenset[str] = frozenset(
    {"reddit_team", "reddit_city", "reddit_alumni", "reddit_cfb"}
)
# How recently (vs the scrape_health "now" anchor) the archive collector must have
# run for us to treat those superseded RSS instances as live-via-archive, not stale.
_ARCHIVE_LIVE_MAX_AGE_DAYS = 3.0

# An ok instance is "overdue" when the gap since its last ok run exceeds this
# multiple of its own historical median ok-to-ok gap. Only applied when we have
# >= MIN_OK_RUNS_FOR_CADENCE ok runs to establish a rhythm (else "never
# established" — reported as a pass with a note, never silently fresh).
OVERDUE_MEDIAN_MULTIPLE = 2.0
MIN_OK_RUNS_FOR_CADENCE = 3

# Statuses we treat as unhealthy at the latest observation.
_UNHEALTHY_STATUSES = ("error", "empty")


# === reconciliation helpers ===============================================


def _registry_classes(conn: sqlite3.Connection) -> set[str]:
    """The set of known source classes (``source_registry.source_id`` values).

    Returns an empty set if the table / column is absent — callers then treat
    every instance as unclassifiable (UNKNOWN-ish), never silently healthy.
    """
    try:
        rows = conn.execute(
            "SELECT DISTINCT source_id FROM source_registry "
            "WHERE source_id IS NOT NULL"
        ).fetchall()
    except sqlite3.Error:
        return set()
    return {str(r[0]) for r in rows if r and r[0] is not None}


def _team_slugs(conn: sqlite3.Connection) -> set[str]:
    """Known team slugs (``teams.slug``) — the evidence the reddit_rss heuristic
    uses to confirm a ``reddit_rss_<slug>`` instance is a real team subreddit.

    Returns an empty set if the table/column is absent, in which case the
    heuristic simply declines to map reddit_rss instances (stays conservative).
    """
    try:
        rows = conn.execute(
            "SELECT DISTINCT slug FROM teams WHERE slug IS NOT NULL"
        ).fetchall()
    except sqlite3.Error:
        return set()
    return {str(r[0]) for r in rows if r and r[0] is not None}


def _classify(
    instance_id: str,
    registry: set[str],
    team_slugs: set[str] | None = None,
) -> str:
    """Map a scrape_health instance id onto a registry source class.

    Order (most to least certain):
      1. exact match — the instance id IS a registry class (e.g. ``cfbd``,
         ``polymarket``, the ``*_template`` rows).
      2. reviewed single-class prefix auto-map (athletics/campus/locked/google).
      3. multi-class prefix (reddit/substack/beat/youtube/board): consult the
         reviewable name-based heuristic in ``source_prefix_map``. It returns a
         registry class only when the instance NAME unambiguously implies one
         (e.g. ``reddit_rss_<known-team-slug>`` -> ``reddit_team``), else None ->
         ``unclassified``. Never guessed into a multi-class parent.
      4. a non-multi prefix that resolves to exactly ONE registry class is a safe
         single-class map (covers other single-class prefixes without guessing).
      5. otherwise ``unclassified`` (anything unrecognised).
    """
    if instance_id in registry:
        return instance_id

    prefix = instance_id.split("_", 1)[0]
    if prefix in SINGLE_CLASS_PREFIXES:
        return SINGLE_CLASS_PREFIXES[prefix]
    if prefix in MULTI_CLASS_PREFIXES:
        # Heuristic, conservative name-based map; returns a registry class only
        # when the instance name unambiguously implies exactly one, else None.
        heur = classify_instance(instance_id, registry, team_slugs)
        return heur if heur is not None else UNCLASSIFIED

    # A prefix that maps to exactly one registry class is unambiguous -> safe to
    # auto-map. More than one (or zero) -> leave unclassified for human review.
    candidates = [cls for cls in registry if cls.split("_", 1)[0] == prefix]
    if len(candidates) == 1:
        return candidates[0]
    return UNCLASSIFIED


def _parse_ts(value: str | None) -> datetime | None:
    """Best-effort parse of a scrape_health timestamp / date string.

    Handles ISO-8601 (with or without ``Z`` / fractional seconds / ``T`` vs space
    separator) and a bare ``YYYY-MM-DD``. Returns None on anything unparseable so
    cadence math simply skips it rather than crashing the pillar.
    """
    if not value:
        return None
    text = str(value).strip().replace("Z", "")
    # Drop fractional seconds if present.
    if "." in text:
        text = text.split(".", 1)[0]
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _ok_run_timestamps(conn: sqlite3.Connection) -> dict[str, list[datetime]]:
    """Per-instance sorted list of ok-run timestamps (for cadence inference)."""
    try:
        rows = conn.execute(
            "SELECT source_id, run_finished_at_utc, run_date "
            "FROM scrape_health WHERE status='ok'"
        ).fetchall()
    except sqlite3.Error:
        return {}
    out: dict[str, list[datetime]] = defaultdict(list)
    for source_id, finished, run_date in rows:
        ts = _parse_ts(finished) or _parse_ts(run_date)
        if ts is not None:
            out[str(source_id)].append(ts)
    for key in out:
        out[key].sort()
    return out


def _latest_per_instance(
    conn: sqlite3.Connection,
) -> dict[str, tuple[str, datetime | None]]:
    """Latest (status, timestamp) per instance — the reconciliation grain.

    "Latest" = max ``run_date`` then max ``run_finished_at_utc`` (a window-free
    aggregation that is robust to ties and works on the live data).
    """
    try:
        rows = conn.execute(
            "SELECT source_id, status, run_date, run_finished_at_utc "
            "FROM scrape_health"
        ).fetchall()
    except sqlite3.Error:
        return {}

    # Reduce to the latest observation per source_id without relying on window
    # functions (keeps this portable across sqlite builds).
    best: dict[str, tuple[str, str, str]] = {}
    for source_id, status, run_date, finished in rows:
        sid = str(source_id)
        key = (run_date or "", finished or "")
        prev = best.get(sid)
        if prev is None or key > (prev[1] or "", prev[2] or ""):
            best[sid] = (status, run_date, finished)

    out: dict[str, tuple[str, datetime | None]] = {}
    for sid, (status, run_date, finished) in best.items():
        out[sid] = (status, _parse_ts(finished) or _parse_ts(run_date))
    return out


def _is_overdue(
    last_ok: datetime | None,
    ok_history: list[datetime],
    now: datetime,
) -> tuple[bool, str]:
    """Decide whether an ok instance is cadence-overdue.

    Only fires when there are >= MIN_OK_RUNS_FOR_CADENCE ok runs to establish a
    rhythm. Returns (overdue, note). With too little history we return
    (False, 'never_established') — reported, but never a fail.
    """
    if len(ok_history) < MIN_OK_RUNS_FOR_CADENCE:
        return False, "never_established"
    gaps = [
        (ok_history[i + 1] - ok_history[i]).total_seconds() / 86400.0
        for i in range(len(ok_history) - 1)
    ]
    gaps = [g for g in gaps if g > 0]
    if not gaps:
        return False, "never_established"
    median_gap = statistics.median(gaps)
    reference = last_ok or ok_history[-1]
    days_since = (now - reference).total_seconds() / 86400.0
    if median_gap > 0 and days_since > OVERDUE_MEDIAN_MULTIPLE * median_gap:
        return True, (
            f"last ok {days_since:.0f}d ago vs ~{median_gap:.0f}d cadence"
        )
    return False, f"fresh (~{median_gap:.0f}d cadence)"


def _reddit_archive_newest(conn: sqlite3.Connection) -> datetime | None:
    """Newest Arctic Shift / pullpush reddit collection run as a datetime, or None.

    The reddit archive collectors are the PRIMARY reddit path (~96% of reddit docs)
    and they log to ``conversation_collection_runs`` — NOT ``scrape_health`` — so
    the reconciliation above cannot see them and reports reddit "stale" off the
    vestigial ``reddit_backfill_*`` RSS rows. Reading the table the archive really
    writes lets a live run clear that false signal. Strictly read-only; any error
    or missing table degrades to ``None`` (fall back to the scrape_health verdict).
    """
    try:
        row = conn.execute(
            "SELECT MAX(started_at_utc) FROM conversation_collection_runs "
            "WHERE json_extract(raw_config_json, '$.provider') IN ('arctic_shift', 'pullpush')"
        ).fetchone()
    except sqlite3.Error:
        return None
    if not row or not row[0]:
        return None
    return _parse_ts(str(row[0]))


# === pillar entrypoint =====================================================


def run(conn: sqlite3.Connection) -> list[CheckResult]:
    """Reconcile source instances vs registry and report freshness per class."""
    results: list[CheckResult] = []

    registry = _registry_classes(conn)
    team_slugs = _team_slugs(conn)
    latest = _latest_per_instance(conn)

    if not latest:
        # No observation log at all -> we genuinely cannot assert source freshness.
        results.append(
            CheckResult(
                check_id="freshness.inventory.unavailable",
                pillar=name,
                dataset="scrape_health",
                season=None,
                status="unknown",
                severity="warning",
                detail=(
                    "scrape_health has no observable rows; source-instance "
                    "freshness cannot be evaluated."
                ),
                evidence_sql="SELECT COUNT(*) FROM scrape_health",
            )
        )
        return results

    ok_history = _ok_run_timestamps(conn)
    # "Now" anchors on the newest observation in the log (deterministic + avoids a
    # wall-clock dependence that would make the check non-reproducible).
    now = max((ts for _, ts in latest.values() if ts is not None), default=None)
    if now is None:
        now = datetime.utcnow()

    # The reddit archive collector (Arctic Shift / pullpush) is the PRIMARY reddit
    # path but logs to conversation_collection_runs, which the scrape_health
    # reconciliation cannot see. If it ran within the freshness window, the reddit_*
    # classes' stale RSS backfill instances are SUPERSEDED, not unhealthy — so we
    # read the real signal instead of false-alarming on a ~3% vestigial path.
    _archive_dt = _reddit_archive_newest(conn)
    reddit_archive_live = (
        _archive_dt is not None
        and (now - _archive_dt).total_seconds() / 86400.0 <= _ARCHIVE_LIVE_MAX_AGE_DAYS
    )

    # Per-class accumulators.
    per_class: dict[str, dict[str, int]] = defaultdict(
        lambda: {
            "instances": 0,
            "ok": 0,
            "error": 0,
            "empty": 0,
            "skipped": 0,
            "other": 0,
            "overdue": 0,
            "unhealthy": 0,
            "superseded": 0,
        }
    )

    overall = {
        "instances": 0,
        "registry_classes": len(registry),
        "ok": 0,
        "error": 0,
        "empty": 0,
        "skipped": 0,
        "other": 0,
        "overdue": 0,
        "unhealthy": 0,
        "superseded": 0,
        "unclassified_instances": 0,
        # Multi-class-prefix instances the name-based heuristic recovered (would
        # otherwise be unclassified). Reported so the heuristic's reach is visible.
        "heuristic_classified": 0,
    }

    for instance_id, (status, ts) in latest.items():
        cls = _classify(instance_id, registry, team_slugs)
        bucket = per_class[cls]
        bucket["instances"] += 1
        overall["instances"] += 1
        if cls == UNCLASSIFIED:
            overall["unclassified_instances"] += 1
        elif (
            instance_id not in registry
            and instance_id.split("_", 1)[0] in MULTI_CLASS_PREFIXES
        ):
            # A multi-class-prefix instance that did NOT exact-match but the
            # heuristic still placed onto a class -> a recovered classification.
            overall["heuristic_classified"] += 1

        st = (status or "").lower()
        if st in ("error", "empty", "skipped", "ok"):
            bucket[st] += 1
            overall[st] += 1
        else:
            bucket["other"] += 1
            overall["other"] += 1

        # A reddit archive class is live via Arctic Shift / pullpush (tracked in
        # conversation_collection_runs) even when its vestigial RSS scrape_health
        # instances read stale -> count those as superseded, not unhealthy.
        _superseded = reddit_archive_live and cls in _REDDIT_ARCHIVE_CLASSES
        if st in _UNHEALTHY_STATUSES:
            if _superseded:
                bucket["superseded"] += 1
                overall["superseded"] += 1
            else:
                bucket["unhealthy"] += 1
                overall["unhealthy"] += 1
        elif st == "ok":
            overdue, _note = _is_overdue(ts, ok_history.get(instance_id, []), now)
            if overdue:
                bucket["overdue"] += 1
                overall["overdue"] += 1
                # An overdue ok instance is a soft-unhealthy schedule miss.
                if _superseded:
                    bucket["superseded"] += 1
                    overall["superseded"] += 1
                else:
                    bucket["unhealthy"] += 1
                    overall["unhealthy"] += 1

    # --- one summary CheckResult per source class ---
    latest_sql = (
        "WITH latest AS (SELECT source_id, status, "
        "ROW_NUMBER() OVER (PARTITION BY source_id "
        "ORDER BY run_date DESC, run_finished_at_utc DESC) rn FROM scrape_health) "
        "SELECT status, COUNT(*) FROM latest WHERE rn=1 GROUP BY status"
    )
    for cls in sorted(per_class):
        b = per_class[cls]
        unhealthy = b["unhealthy"]
        status = "fail" if unhealthy > 0 else "pass"
        # An all-unclassified bucket is reported as unknown: we cannot assert the
        # health of instances we could not even attribute to a contract.
        if cls == UNCLASSIFIED:
            status = "unknown"
        superseded_note = (
            f" ({b['superseded']} superseded — live via Arctic Shift/pullpush, "
            f"tracked in conversation_collection_runs not scrape_health)"
            if b["superseded"] else ""
        )
        detail = (
            f"{cls}: {b['instances']} instance(s) — "
            f"ok={b['ok']} error={b['error']} empty={b['empty']} "
            f"skipped={b['skipped']} overdue={b['overdue']}; "
            f"{unhealthy} unhealthy.{superseded_note}"
        )
        results.append(
            CheckResult(
                check_id=f"freshness.source_class.{cls}",
                pillar=name,
                dataset=cls,
                season=None,
                status=status,
                severity="warning",
                detail=detail,
                evidence_sql=latest_sql,
            )
        )

    # --- one overall counts result ---
    healthy = overall["instances"] - overall["unhealthy"]
    superseded_clause = (
        f" Plus {overall['superseded']} reddit instance(s) SUPERSEDED — live via "
        f"Arctic Shift (conversation_collection_runs, ~96% of reddit docs), so the "
        f"vestigial RSS rows are not counted unhealthy."
        if overall["superseded"] else ""
    )
    overall_detail = (
        f"{overall['instances']} source instances reconciled vs "
        f"{overall['registry_classes']} registry classes: "
        f"{overall['error']} error + {overall['empty']} empty + "
        f"{overall['overdue']} overdue across latest runs -> "
        f"{overall['unhealthy']} unhealthy, {healthy} healthy; "
        f"{overall['unclassified_instances']} unclassified "
        f"({overall['heuristic_classified']} recovered by name heuristic).{superseded_clause}"
    )
    results.append(
        CheckResult(
            check_id="freshness.inventory.overall",
            pillar=name,
            dataset="scrape_health",
            season=None,
            status="fail" if overall["unhealthy"] > 0 else "pass",
            severity="warning",
            detail=overall_detail,
            evidence_sql=latest_sql,
        )
    )

    return results
