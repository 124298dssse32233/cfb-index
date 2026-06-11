from __future__ import annotations

import json
from typing import Any

ATLAS_CHIP_CSS: str = """
.atlas-chip {
    display: inline-flex;
    flex-direction: column;
    gap: 6px;
    border: 1px solid var(--color-border, #2a2a2a);
    border-radius: 8px;
    padding: 12px 16px;
    background: var(--color-surface, #111);
    min-width: 200px;
    max-width: 100%;
}

.atlas-chip__label {
    font-family: Inter, sans-serif;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--color-muted, #666);
    line-height: 1;
}

.atlas-chip__name {
    font-family: "Bebas Neue", Impact, sans-serif;
    font-size: 22px;
    font-weight: 700;
    letter-spacing: 0.04em;
    color: var(--color-text-primary, #f0f0f0);
    line-height: 1.1;
}

.atlas-chip__terms {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    margin-top: 2px;
}

.atlas-chip__term-pill {
    font-family: Inter, sans-serif;
    font-size: 11px;
    font-weight: 500;
    color: var(--color-accent, #e8a400);
    background: var(--color-accent-subtle, rgba(232, 164, 0, 0.12));
    border: 1px solid var(--color-accent-border, rgba(232, 164, 0, 0.25));
    border-radius: 4px;
    padding: 2px 7px;
    line-height: 1.5;
    white-space: nowrap;
}

.atlas-chip__count {
    font-family: Inter, sans-serif;
    font-size: 11px;
    color: var(--color-muted, #666);
    margin-top: 2px;
}

@media (max-width: 600px) {
    .atlas-chip {
        width: 100%;
        box-sizing: border-box;
    }
}
"""


def _fetch_one(db: Any, sql: str, params: Any):
    """One row as a dict for either connection type. The production render passes
    the Database wrapper (execute() returns None -> use query_one); tests pass a
    raw sqlite3.Connection (cursor -> normalize to a dict by column name). Without
    this, the wrapper path silently returned '' for every team."""
    cur = db.execute(sql, params)
    if cur is None:
        return db.query_one(sql, params)
    row = cur.fetchone()
    if row is None:
        return None
    cols = [c[0] for c in cur.description] if cur.description else []
    return {cols[i]: row[i] for i in range(len(cols))}


def render_atlas_chip(db: Any, profile: Any, snapshot: Any) -> str:
    if db is None or profile is None:
        return ""

    # Prefer the snapshot's team_id: it is resolved by slug from the teams table
    # (canonical), whereas profile.team_id comes from hand-authored YAML that goes
    # stale when team_ids are reassigned on re-ingest (29 profiles were stale on
    # 2026-06-11 -- e.g. texas profile said 170, which is now Clark Atlanta).
    tid = 0
    try:
        tid = int(snapshot.team_id)
    except (AttributeError, TypeError, ValueError):
        tid = 0
    if not tid:
        try:
            tid = int(profile.team_id)
        except (AttributeError, TypeError, ValueError):
            tid = 0
    if not tid:
        return ""

    # Query most recent cluster row for this team
    try:
        row = _fetch_one(
            db,
            """
            SELECT cluster_name, cluster_size, shared_terms
            FROM team_discourse_clusters
            WHERE team_id = :tid
            ORDER BY season_year DESC
            LIMIT 1
            """,
            {"tid": tid},
        )
    except Exception:
        return ""

    if row is None:
        return ""

    cluster_name = row.get("cluster_name") or ""
    cluster_size = row.get("cluster_size") or 0
    raw_terms = row.get("shared_terms")

    if cluster_size < 2:
        return ""

    # Parse shared_terms JSON safely
    shared_terms: list[str] = []
    if raw_terms:
        try:
            parsed = json.loads(raw_terms)
            if isinstance(parsed, list):
                shared_terms = [str(t) for t in parsed if t]
        except (json.JSONDecodeError, TypeError, ValueError):
            shared_terms = []

    terms_display = shared_terms[:4]

    companion_count = cluster_size - 1

    # Build pill HTML for each term
    pills_html = "".join(
        f'<span class="atlas-chip__term-pill">{_esc(term)}</span>'
        for term in terms_display
    )

    terms_section = (
        f'<div class="atlas-chip__terms">{pills_html}</div>'
        if pills_html
        else '<div class="atlas-chip__terms"></div>'
    )

    html = (
        '<div class="atlas-chip">'
        '<span class="atlas-chip__label">Your Vocabulary Cluster</span>'
        f'<span class="atlas-chip__name">{_esc(cluster_name)}</span>'
        f"{terms_section}"
        f'<span class="atlas-chip__count">with {companion_count} other fanbases</span>'
        "</div>"
    )
    return html


def _esc(text: str) -> str:
    """Minimal HTML escaping for inline text."""
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
    )
