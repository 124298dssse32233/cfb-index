"""Sample-size confidence signaling — data-driven thresholds + chip helper.

Sprint v5-5.5 lock spec: ``docs/design-system/33-confidence-signaling.md``.
This module is the v5-7.5 foundation slice — pure new code, no renderer
touches. Window A's v5-7 work imports from here when it lands.

The "chip" is the visible primitive on every named metric: a colored pill
that says "we know how much data backed this number." Thresholds are NOT
hard-coded — they're computed quarterly from the actual per-team-week
distribution per domain. The locked decision (per the spec doc):

* HIGH         — sample above the p75 of the per-team-week distribution
* MEDIUM       — sample in the p25..p75 range
* LOW          — sample below p25
* UNSET / INSUFFICIENT — sample below p10 → suppress the metric AND show
  the unset chip in its place

Per-domain thresholds live in the ``confidence_calibration`` table (one
row per (domain, quarter)). The ``recompute-confidence-thresholds`` CLI
populates it from the live distribution.

Contracts:

1. ``band_for(sample_size, domain, *, db=None) -> Band`` — pure: given
   a sample size + domain, returns the band. Reads the latest
   ``confidence_calibration`` row for that domain. If no calibration row
   exists for the domain, falls back to the ``_FALLBACK_THRESHOLDS``
   below (loud-logged once).

2. ``render_confidence_chip(sample_size, domain, *, override_label=None,
   show_sample=True, db=None) -> str`` — emits HTML for the chip.
   ``override_label`` may soften the LABEL TEXT but never overrides the
   BAND (color); this is the editorial-honesty lock from the spec.

3. ``recompute_thresholds(db, domain) -> CalibrationResult`` — runs the
   per-team-week SQL aggregate, computes the four percentile cuts, and
   inserts a new ``confidence_calibration`` row tagged with the current
   quarter. Idempotent within a quarter (upserts).

4. ``Band`` enum has 4 values: HIGH / MEDIUM / LOW / UNSET. String form
   matches the CSS modifier (``confidence--high`` etc.).

5. ``Domain`` enum has 5 values matching the spec doc's "Per-domain
   thresholds" table.

This module does NOT decide whether to call the chip — that's the
renderer's job. It only computes "given this sample, what band, what HTML."
"""
from __future__ import annotations

import datetime as _dt
import enum as _enum
import html as _html
import logging as _log
from dataclasses import dataclass
from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from .db import Database


log = _log.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Band(str, _enum.Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNSET = "unset"


class Domain(str, _enum.Enum):
    """Confidence calibration domains.

    Each domain has its own per-team-week distribution and therefore its
    own thresholds. Adding a new domain requires:
      1. Add the enum value here.
      2. Add a row to _DOMAIN_SAMPLE_SQL with the SQL that produces a
         per-team-week count for the domain.
      3. Run ``manage.py recompute-confidence-thresholds --domain <name>``.
    """
    FAN_INTEL = "fan_intel"
    HISTORICAL = "historical"
    MODEL = "model"
    MARKET = "market"
    PREDICTION = "prediction"


# ---------------------------------------------------------------------------
# Fallback thresholds (used when confidence_calibration table is empty)
# Approximate p10/p25/p75 today per the spec doc Per-domain thresholds table.
# These are intentionally conservative — first run of recompute_thresholds
# replaces them with the real distribution.
# ---------------------------------------------------------------------------

_FALLBACK_THRESHOLDS: dict[Domain, tuple[int, int, int]] = {
    # (p10, p25, p75) — sample counts per the unit per the domain
    Domain.FAN_INTEL:   (4, 8, 35),       # docs per team-week
    Domain.HISTORICAL:  (4, 8, 12),       # games per team-season
    Domain.MODEL:       (10, 50, 200),    # schedule-connectivity edges
    Domain.MARKET:      (2, 4, 8),        # sportsbooks reporting
    Domain.PREDICTION:  (2, 5, 15),       # resolved claims per source-slug
}

_FALLBACK_WARNED: set[Domain] = set()


# ---------------------------------------------------------------------------
# Per-domain SQL — used by recompute_thresholds() to build the per-team-week
# distribution. Each query returns a single column ``sample_count``.
# ---------------------------------------------------------------------------

_DOMAIN_SAMPLE_SQL: dict[Domain, str] = {
    Domain.FAN_INTEL: """
        SELECT COUNT(*) AS sample_count
        FROM conversation_documents cd
        JOIN conversation_document_targets cdt
          ON cd.conversation_document_id = cdt.conversation_document_id
        WHERE COALESCE(cd.external_created_at_utc, cd.collected_at_utc)
              > datetime('now', '-90 days')
        GROUP BY cdt.team_id,
                 strftime('%Y-%W',
                          COALESCE(cd.external_created_at_utc, cd.collected_at_utc))
    """,
    Domain.HISTORICAL: """
        SELECT COUNT(*) AS sample_count
        FROM games
        WHERE season_year >= (CAST(strftime('%Y','now') AS INTEGER) - 12)
        GROUP BY home_team_id, season_year
    """,
    Domain.MODEL: """
        SELECT MAX(schedule_connectivity) AS sample_count
        FROM power_ratings_weekly
        WHERE schedule_connectivity IS NOT NULL
        GROUP BY team_id, season_year, week
    """,
    Domain.MARKET: """
        SELECT COUNT(DISTINCT provider) AS sample_count
        FROM heisman_market_odds_weekly
        GROUP BY player_id, season_year, week
    """,
    Domain.PREDICTION: """
        SELECT COUNT(*) AS sample_count
        FROM predictive_claims
        WHERE outcome_resolved = 1
        GROUP BY source_slug
    """,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CalibrationThresholds:
    """The three cut points + the sample size at calibration time."""
    p10: int
    p25: int
    p75: int
    sample_size_at_calibration: int

    def band(self, sample_size: int) -> Band:
        """Pure function — sample → band."""
        if sample_size < self.p10:
            return Band.UNSET
        if sample_size < self.p25:
            return Band.LOW
        if sample_size < self.p75:
            return Band.MEDIUM
        return Band.HIGH


class CalibrationResult(NamedTuple):
    """Returned by recompute_thresholds()."""
    domain: Domain
    quarter: str
    thresholds: CalibrationThresholds
    inserted: bool   # True if a new row was inserted; False if an existing
                     # row for (domain, quarter) was updated


_DEFAULT_BAND_LABELS: dict[Band, str] = {
    Band.HIGH: "High confidence",
    Band.MEDIUM: "Medium confidence",
    Band.LOW: "Low confidence",
    Band.UNSET: "Awaiting signal",
}


def current_quarter(now: _dt.datetime | None = None) -> str:
    """Return the current quarter as 'YYYYQN' (e.g. '2026Q2')."""
    now = now or _dt.datetime.now(_dt.timezone.utc)
    return f"{now.year}Q{(now.month - 1) // 3 + 1}"


def get_calibration(
    domain: Domain,
    *,
    db: "Database | None" = None,
) -> CalibrationThresholds:
    """Read the latest calibration row for the domain, or fall back.

    If ``db`` is None or no row exists for the domain, returns the
    fallback thresholds and warn-logs once per process per domain.
    """
    if db is not None:
        row = db.query_one(
            """
            SELECT p10_threshold, p25_threshold, p75_threshold,
                   sample_size_at_calibration
            FROM confidence_calibration
            WHERE domain = ?
            ORDER BY computed_at_utc DESC
            LIMIT 1
            """,
            (domain.value,),
        )
        if row is not None:
            return CalibrationThresholds(
                p10=row["p10_threshold"],
                p25=row["p25_threshold"],
                p75=row["p75_threshold"],
                sample_size_at_calibration=row["sample_size_at_calibration"],
            )

    if domain not in _FALLBACK_WARNED:
        log.warning(
            "confidence: no calibration row for domain=%s; "
            "using fallback thresholds (run recompute-confidence-thresholds)",
            domain.value,
        )
        _FALLBACK_WARNED.add(domain)
    p10, p25, p75 = _FALLBACK_THRESHOLDS[domain]
    return CalibrationThresholds(p10=p10, p25=p25, p75=p75,
                                 sample_size_at_calibration=0)


def band_for(
    sample_size: int,
    domain: Domain | str,
    *,
    db: "Database | None" = None,
) -> Band:
    """Pure: given a sample size and a domain, return the band.

    ``domain`` accepts either the enum or the string form ('fan_intel').
    Raises ValueError if the string form is unknown.
    """
    if isinstance(domain, str):
        try:
            domain = Domain(domain)
        except ValueError as e:
            raise ValueError(
                f"unknown confidence domain: {domain!r} "
                f"(valid: {[d.value for d in Domain]})"
            ) from e
    if sample_size < 0:
        raise ValueError(f"sample_size must be >= 0, got {sample_size}")
    thresholds = get_calibration(domain, db=db)
    return thresholds.band(sample_size)


def render_confidence_chip(
    sample_size: int,
    domain: Domain | str,
    *,
    override_label: str | None = None,
    show_sample: bool = True,
    db: "Database | None" = None,
) -> str:
    """Return the HTML for a confidence chip.

    Locked editorial-honesty rule: ``override_label`` overrides the
    LABEL TEXT but NEVER overrides the BAND (color). The chip's color
    is always derived from the sample-derived band.

    Examples (using fallback fan_intel thresholds 4 / 8 / 35):
      render_confidence_chip(42, "fan_intel")
        → '<span class="confidence confidence--high">● High confidence · n=42</span>'

      render_confidence_chip(12, "fan_intel", override_label="Moderate")
        → '<span class="confidence confidence--medium">● Moderate · n=12</span>'

      render_confidence_chip(2, "fan_intel", show_sample=False)
        → '<span class="confidence confidence--unset">● Awaiting signal</span>'
    """
    band = band_for(sample_size, domain, db=db)
    label = override_label or _DEFAULT_BAND_LABELS[band]
    label = _html.escape(label)
    body = label
    if show_sample and band is not Band.UNSET:
        body += f" · n={sample_size}"
    return (
        f'<span class="confidence confidence--{band.value}">'
        f'{body}</span>'
    )


def recompute_thresholds(
    db: "Database",
    domain: Domain | str,
    *,
    now: _dt.datetime | None = None,
) -> CalibrationResult:
    """Compute fresh percentile cuts for the domain and upsert the row.

    Reads the domain's per-team-week (or per-team-season etc.) sample-
    count distribution via _DOMAIN_SAMPLE_SQL, computes p10 / p25 / p75
    via Python (SQLite doesn't have PERCENTILE_CONT), and writes a
    ``confidence_calibration`` row tagged with the current quarter.

    Idempotent within a quarter — repeated calls UPDATE the existing
    (domain, quarter) row rather than appending.
    """
    if isinstance(domain, str):
        domain = Domain(domain)
    rows = db.query_all(_DOMAIN_SAMPLE_SQL[domain])
    samples: list[int] = [int(r["sample_count"]) for r in rows
                          if r["sample_count"] is not None]
    samples.sort()
    n = len(samples)
    if n == 0:
        # No data — write a row anyway so we don't keep falling back forever
        # but with the fallback thresholds. The presence of the row
        # documents that the calibration was attempted.
        p10, p25, p75 = _FALLBACK_THRESHOLDS[domain]
        log.warning(
            "confidence.recompute_thresholds: domain=%s has 0 rows; "
            "writing fallback thresholds with sample_size=0",
            domain.value,
        )
    else:
        # Linear-interpolation percentile (matches NumPy's 'linear' method).
        def _pct(p: float) -> int:
            if n == 1:
                return samples[0]
            k = p * (n - 1)
            lo = int(k)
            hi = min(lo + 1, n - 1)
            frac = k - lo
            return int(round(samples[lo] * (1 - frac) + samples[hi] * frac))
        p10 = _pct(0.10)
        p25 = _pct(0.25)
        p75 = _pct(0.75)

    quarter = current_quarter(now)
    thresholds = CalibrationThresholds(
        p10=p10, p25=p25, p75=p75,
        sample_size_at_calibration=n,
    )
    # Upsert on (domain, quarter) — see confidence_calibration migration
    inserted = db.execute(
        """
        INSERT INTO confidence_calibration
          (domain, quarter, p10_threshold, p25_threshold, p75_threshold,
           sample_size_at_calibration, computed_at_utc)
        VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
        ON CONFLICT(domain, quarter) DO UPDATE SET
          p10_threshold = excluded.p10_threshold,
          p25_threshold = excluded.p25_threshold,
          p75_threshold = excluded.p75_threshold,
          sample_size_at_calibration = excluded.sample_size_at_calibration,
          computed_at_utc = excluded.computed_at_utc
        """,
        (domain.value, quarter, p10, p25, p75, n),
    )
    # ``inserted`` from execute() may not distinguish INSERT vs UPDATE; the
    # rowcount semantics differ by SQLite version. Treat it as "was upserted".
    return CalibrationResult(
        domain=domain,
        quarter=quarter,
        thresholds=thresholds,
        inserted=bool(inserted),
    )


__all__ = [
    "Band",
    "Domain",
    "CalibrationThresholds",
    "CalibrationResult",
    "current_quarter",
    "get_calibration",
    "band_for",
    "render_confidence_chip",
    "recompute_thresholds",
]
