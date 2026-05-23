"""Mirror Match module — Brief Signature Bet #4.

Finds the closest historical "fingerprint" match for a player based on
their per-season metric profile. Uses player_value_metrics + similarity
distance across the shared set of metrics.

For QBs we use:
  - wepa_passing_per_dropback
  - completion_percentage
  - yards_per_attempt
  - sacks_taken_pct

For RBs:
  - wepa_rushing_per_carry
  - yards_per_carry
  - rushing_touchdowns

The match returns a similarity percentage 0-100. Brief target: "Closest
historical match: Bo Nix, Oregon 2023 · 94% similar."

Falls back to "Awaiting Signal" when no metrics exist for the focal
player or no candidate pool exists.

Public API:
    render_mirror_match(db, player_id, season_year, position) -> str
    MIRROR_MATCH_CSS                                          -> str
"""
from __future__ import annotations

from html import escape
from typing import Any


MIRROR_MATCH_CSS = """
/* Mirror Match module */
.mirror-match {
  margin: var(--space-4, 1rem) 0 var(--space-6, 1.5rem) 0;
  padding: clamp(14px, 1.8vw, 20px) clamp(16px, 2.0vw, 24px);
  background: linear-gradient(
    135deg,
    rgba(255, 255, 255, 0.03) 0%,
    rgba(255, 255, 255, 0.015) 50%,
    rgba(0, 0, 0, 0.08) 100%
  );
  border: 1px solid var(--stroke-subtle, rgba(255,255,255,0.08));
  border-left: 3px solid var(--accent-primary, var(--accolade-gold-base, #d1a23a));
  border-radius: 12px;
  font-variant-numeric: tabular-nums;
}
.mirror-match__head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 12px;
  border-bottom: 1px dashed var(--stroke-subtle, rgba(255,255,255,0.07));
  padding-bottom: 8px;
  margin-bottom: 12px;
}
.mirror-match__eyebrow {
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--muted-foreground, var(--fg-muted, #666));
  margin: 0;
}
.mirror-match__similarity {
  font-family: var(--font-display, 'Bebas Neue', 'Inter Display', system-ui, sans-serif);
  font-size: clamp(36px, 3vw + 12px, 56px);
  font-weight: 400;
  line-height: 1;
  letter-spacing: 0.02em;
  color: var(--accent-primary, var(--accolade-gold-base, #d1a23a));
  margin: 0;
}
.mirror-match__match {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 14px 22px;
  align-items: center;
}
.mirror-match__name {
  font-family: var(--font-display, 'Bebas Neue', 'Inter Display', system-ui, sans-serif);
  font-size: clamp(22px, 1.6vw + 8px, 32px);
  font-weight: 400;
  letter-spacing: 0.02em;
  line-height: 1;
  color: var(--foreground, var(--fg-primary, #222));
  margin: 0 0 4px 0;
}
.mirror-match__meta {
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 12px;
  color: var(--muted-foreground, var(--fg-secondary, #666));
}
.mirror-match__story {
  font-family: var(--font-serif, 'Source Serif Pro', Georgia, serif);
  font-size: 13px;
  font-style: italic;
  line-height: 1.4;
  color: var(--muted-foreground, var(--fg-secondary, #666));
  margin: 8px 0 0 0;
  max-width: 56ch;
}
.mirror-match__sim-label {
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 10px;
  letter-spacing: 0.14em;
  color: var(--muted-foreground, var(--fg-muted, #666));
  text-transform: uppercase;
  text-align: right;
  display: block;
}
.mirror-match--empty {
  color: var(--muted-foreground, var(--fg-muted, #666));
  font-style: italic;
  font-size: var(--fs-meta, 0.78rem);
  font-family: var(--font-serif, 'Source Serif Pro', Georgia, serif);
}
"""


# Position → metric weighting. Currently only wepa_passing + wepa_rushing
# are populated in player_value_metrics. Expanded as more metrics are ingested.
_QB_METRICS = {
    "wepa_passing": 1.0,
    "wepa_rushing": 0.4,  # mobility component
}
_RB_METRICS = {
    "wepa_rushing": 1.0,
}
_WR_METRICS = {
    # Receiving WEPA not yet ingested; fall back to no metric set.
}


def _metric_set(position: str) -> dict[str, float]:
    pos = (position or "").upper()
    if pos in {"QB", "QUARTERBACK"}:
        return _QB_METRICS
    if pos in {"RB", "TB", "FB", "RUNNINGBACK", "RUNNING BACK"}:
        return _RB_METRICS
    if pos in {"WR", "TE", "WIDE RECEIVER", "TIGHT END"}:
        return _WR_METRICS
    # Default: try all
    return {**_QB_METRICS, **_RB_METRICS, **_WR_METRICS}


def _fetch_player_metric_profile(
    db, player_id: int, season_year: int, metrics: dict[str, float]
) -> dict[str, float]:
    rows = db.query_all(
        f"""
        select metric_name, avg(metric_value) as v
          from player_value_metrics
         where player_id = :pid and season_year = :s
           and metric_name in ({",".join("'" + k + "'" for k in metrics)})
         group by metric_name
        """,
        {"pid": player_id, "s": season_year},
    )
    return {str(r["metric_name"]): float(r["v"] or 0.0) for r in rows}


def _fetch_candidate_pool(
    db, exclude_player_id: int, exclude_season: int, position: str,
    metrics: dict[str, float],
) -> list[dict[str, Any]]:
    pos = (position or "").upper()
    pos_filter = ""
    pos_params: dict[str, Any] = {}
    if pos in {"QB", "RB", "WR", "TE"}:
        pos_filter = "and (p.position = :pos or p.position is null)"
        pos_params["pos"] = pos
    rows = db.query_all(
        f"""
        select
          pvm.player_id, pvm.season_year, pvm.metric_name, pvm.metric_value,
          p.full_name, p.position, t.canonical_name as team_name
          from player_value_metrics pvm
          left join players p on p.player_id = pvm.player_id
          left join teams t on t.team_id = pvm.team_id
         where pvm.player_id is not null
           and pvm.metric_name in ({",".join("'" + k + "'" for k in metrics)})
           and not (pvm.player_id = :pid and pvm.season_year = :s)
           {pos_filter}
        """,
        {"pid": exclude_player_id, "s": exclude_season, **pos_params},
    )
    # Group by (player_id, season_year) → metrics dict
    bucket: dict[tuple[int, int], dict[str, Any]] = {}
    for r in rows:
        key = (int(r["player_id"]), int(r["season_year"]))
        if key not in bucket:
            bucket[key] = {
                "player_id": key[0],
                "season_year": key[1],
                "full_name": r.get("full_name"),
                "position": r.get("position"),
                "team_name": r.get("team_name"),
                "metrics": {},
            }
        bucket[key]["metrics"][r["metric_name"]] = float(r.get("metric_value") or 0.0)
    return list(bucket.values())


def _similarity_score(focal: dict[str, float], cand: dict[str, float],
                      metrics: dict[str, float]) -> float | None:
    """Compute weighted similarity 0-100 over the shared metric set.

    Uses normalized absolute difference scaled by metric weight.
    Returns None if fewer than 2 shared metrics.
    """
    shared = [k for k in metrics if k in focal and k in cand]
    if len(shared) < 2:
        return None
    total_weight = 0.0
    total_dist = 0.0
    for k in shared:
        weight = metrics[k]
        # Normalize: max-known typical range per metric. Use abs(f-c) / max(|f|,|c|,0.5).
        f, c = focal[k], cand[k]
        denom = max(abs(f), abs(c), 0.5)
        d = min(1.0, abs(f - c) / denom)
        total_weight += weight
        total_dist += d * weight
    if total_weight == 0:
        return None
    avg_dist = total_dist / total_weight
    return max(0.0, min(100.0, 100.0 * (1.0 - avg_dist)))


def render_mirror_match(
    db, player_id: int | None, season_year: int | None,
    position: str | None = None,
) -> str:
    if db is None or player_id is None or season_year is None:
        return ""
    metrics = _metric_set(position or "")
    focal = _fetch_player_metric_profile(db, int(player_id), int(season_year), metrics)
    if not focal:
        return (
            '<section class="mirror-match mirror-match--empty" '
            'data-module="mirror-match" data-state="empty">'
            'Mirror Match needs at least one Savant-style metric (passing efficiency, '
            'rushing per carry, etc.) for this player. Awaiting signal.'
            '</section>'
        )
    candidates = _fetch_candidate_pool(
        db, int(player_id), int(season_year), position or "", metrics,
    )
    if not candidates:
        return (
            '<section class="mirror-match mirror-match--empty" '
            'data-module="mirror-match" data-state="empty">'
            'Mirror Match candidate pool empty for this position. Awaiting more data.'
            '</section>'
        )

    best: tuple[float, dict[str, Any]] | None = None
    for cand in candidates:
        sim = _similarity_score(focal, cand["metrics"], metrics)
        if sim is None:
            continue
        if best is None or sim > best[0]:
            best = (sim, cand)

    if best is None:
        return (
            '<section class="mirror-match mirror-match--empty" '
            'data-module="mirror-match" data-state="empty">'
            'Mirror Match needs more overlapping Savant metrics to converge. Awaiting signal.'
            '</section>'
        )

    sim, cand = best
    name = cand.get("full_name") or "Unknown"
    team = cand.get("team_name") or "—"
    cand_year = cand.get("season_year")

    if sim >= 95:
        story = f"Statistically near-identical profile to {name} ({team}, {cand_year})."
    elif sim >= 90:
        story = f"Very close fingerprint match with {name} ({team}, {cand_year})."
    elif sim >= 80:
        story = f"Strong similarity to {name} ({team}, {cand_year}) across {len(metrics)} metrics."
    else:
        story = f"Closest historical match is {name} ({team}, {cand_year}) — moderate similarity."

    return f"""
<section class="mirror-match" data-module="mirror-match" data-state="ready"
         data-similarity="{sim:.1f}">
  <div class="mirror-match__head">
    <p class="mirror-match__eyebrow">Mirror Match · Statistical fingerprint</p>
  </div>
  <div class="mirror-match__match">
    <div>
      <h3 class="mirror-match__name">{escape(str(name))}</h3>
      <div class="mirror-match__meta">{escape(str(team))} · {escape(str(cand_year))}</div>
      <p class="mirror-match__story">{escape(story)}</p>
    </div>
    <div>
      <span class="mirror-match__similarity">{sim:.0f}%</span>
      <span class="mirror-match__sim-label">similar</span>
    </div>
  </div>
</section>"""


__all__ = ["render_mirror_match", "MIRROR_MATCH_CSS"]
