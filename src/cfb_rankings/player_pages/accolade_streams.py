"""Accolade Streams — per-award projection tabs nested inside Player Standing.

Each stream is one tab body: probability tile + trajectory spark +
"what needs to happen" copy + (for the All-America tab) the Selector Grid.

Per PLAYER_PAGE_WORLD_CLASS_BRIEF.md §7, the position-specific award set
changes but the grammar doesn't. The tab catalog below maps each FBS
position bucket to its relevant national awards.

Data sources:
    - Heisman:        heisman_rankings_weekly (real data, 99k rows)
    - All-America:    player_honors (real data, 2k rows)
    - Position awards (Davey O'Brien, Manning, Maxwell, Biletnikoff, ...)
                      no dedicated tracker tables yet — honest "awaiting
                      tracker" empty state; the framework is ready when
                      per-award scrapers ship.

Public API:
    build_accolade_streams_for_position(db, player_id, season_year, position)
        -> list[dict]   # one dict per tab, in display order
    render_accolade_tabs_html(streams, active_idx=0) -> str

Each stream dict shape:
    {
        "award_name": str,            # display label
        "award_key": str,             # slug (heisman | all_america | davey_obrien | ...)
        "probability_pct": float | None,
        "current_rank": int | None,
        "trajectory": list[float],    # weekly value series, oldest -> newest
        "what_needs_to_happen": str,
        "data_state": "ready" | "awaiting" | "empty",
        "selector_breakdown": dict | None,   # only for all_america tab
    }
"""
from __future__ import annotations

import logging
from html import escape
from typing import Any

log = logging.getLogger("cfb_rankings.player_pages.accolade_streams")


# ---------------------------------------------------------------------------
# DB compat shim — work with both project Database wrapper and raw sqlite3
# ---------------------------------------------------------------------------


def _query_all(db: Any, sql: str, params) -> list[dict]:
    if hasattr(db, "query_all"):
        return db.query_all(sql, params)
    # Raw sqlite3 — convert named params dict to qmark-style by re-binding
    cur = db.execute(sql, params) if isinstance(params, dict) else db.execute(sql, params)
    cols = [d[0] for d in cur.description] if cur.description else []
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def _query_one(db: Any, sql: str, params) -> dict | None:
    rows = _query_all(db, sql, params)
    return rows[0] if rows else None


# ---------------------------------------------------------------------------
# Per-position award catalog
# ---------------------------------------------------------------------------

# Canonical position-bucket -> ordered list of (award_key, display_name).
POSITION_AWARDS: dict[str, list[tuple[str, str]]] = {
    "QB": [
        ("heisman", "Heisman"),
        ("davey_obrien", "Davey O'Brien"),
        ("manning", "Manning"),
        ("unitas", "Unitas"),
        ("all_america", "All-America"),
    ],
    "RB": [
        ("heisman", "Heisman"),
        ("doak_walker", "Doak Walker"),
        ("maxwell", "Maxwell"),
        ("all_america", "All-America"),
    ],
    "WR": [
        ("heisman", "Heisman"),
        ("biletnikoff", "Biletnikoff"),
        ("maxwell", "Maxwell"),
        ("all_america", "All-America"),
    ],
    "TE": [
        ("mackey", "Mackey"),
        ("all_america", "All-America"),
    ],
    "OL": [
        ("outland", "Outland"),
        ("rimington", "Rimington"),
        ("all_america", "All-America"),
    ],
    "DL": [
        ("lombardi", "Lombardi"),
        ("bednarik", "Bednarik"),
        ("all_america", "All-America"),
    ],
    "EDGE": [
        ("lombardi", "Lombardi"),
        ("bednarik", "Bednarik"),
        ("all_america", "All-America"),
    ],
    "LB": [
        ("butkus", "Butkus"),
        ("bednarik", "Bednarik"),
        ("all_america", "All-America"),
    ],
    "DB": [
        ("thorpe", "Thorpe"),
        ("nagurski", "Nagurski"),
        ("all_america", "All-America"),
    ],
    "K": [
        ("groza", "Groza"),
        ("all_america", "All-America"),
    ],
    "P": [
        ("ray_guy", "Ray Guy"),
        ("all_america", "All-America"),
    ],
    "ATH": [
        ("heisman", "Heisman"),
        ("all_america", "All-America"),
    ],
}

# Default fallback if position isn't matched
_DEFAULT_AWARDS: list[tuple[str, str]] = [
    ("heisman", "Heisman"),
    ("all_america", "All-America"),
]


def _normalize_position(pos: str | None) -> str:
    """Map raw position strings to canonical buckets in POSITION_AWARDS."""
    if not pos:
        return ""
    p = pos.strip().upper()
    # Common aliases
    if p in ("CB", "S", "SAF", "DB", "NB", "FS", "SS"):
        return "DB"
    if p in ("DT", "DE", "NT", "DL"):
        # Heuristic: treat outside DEs as EDGE when name implies so,
        # but without that signal default to DL
        return "DL"
    if p in ("OG", "OT", "C", "OL", "G", "T"):
        return "OL"
    if p in ("ILB", "OLB", "MLB", "LB"):
        return "LB"
    if p in ("WR", "FL"):
        return "WR"
    if p in ("RB", "HB", "FB", "TB"):
        return "RB"
    if p in ("QB",):
        return "QB"
    if p in ("TE",):
        return "TE"
    if p == "K" or p == "PK":
        return "K"
    if p == "P":
        return "P"
    return "ATH"


def awards_for_position(position: str | None) -> list[tuple[str, str]]:
    bucket = _normalize_position(position)
    return POSITION_AWARDS.get(bucket, _DEFAULT_AWARDS)


# ---------------------------------------------------------------------------
# Per-award stream builders
# ---------------------------------------------------------------------------


def _empty_stream(award_key: str, award_name: str, reason: str) -> dict[str, Any]:
    return {
        "award_name": award_name,
        "award_key": award_key,
        "probability_pct": None,
        "current_rank": None,
        "trajectory": [],
        "what_needs_to_happen": reason,
        "data_state": "empty" if reason else "awaiting",
        "selector_breakdown": None,
    }


def build_heisman_stream(
    db: Any, player_id: int, season_year: int, award_name: str = "Heisman",
) -> dict[str, Any]:
    try:
        rows = _query_all(db,
            """
            SELECT week, rank_overall, latent_score, finalist_probability,
                   win_probability
            FROM heisman_rankings_weekly
            WHERE player_id = :pid AND season_year = :s
              AND rank_overall IS NOT NULL
            ORDER BY week ASC
            """,
            {"pid": player_id, "s": season_year},
        )
    except Exception as exc:
        log.debug("heisman stream query failed: %s", exc)
        rows = []

    if not rows:
        return _empty_stream("heisman", award_name,
                             "Heisman model tracks the top FBS contenders weekly; "
                             "this player hasn't entered the watch list yet.")

    latest = rows[-1]
    rank = latest.get("rank_overall")
    finalist_p = latest.get("finalist_probability") or 0
    trajectory = [
        # We track rank inversely (lower rank = better). Convert to a
        # 0..1 trajectory where 1.0 = #1 overall and 0 = off the list (rank >= 50).
        max(0.0, min(1.0, 1.0 - (float(r["rank_overall"]) - 1) / 49.0))
        for r in rows
        if r.get("rank_overall") is not None
    ]

    if rank and rank <= 5:
        copy = (
            f"Finalist tier. Currently #{int(rank)} in the ballot. "
            "A signature November win cements the closing-weekend invite."
        )
    elif rank and rank <= 15:
        copy = (
            f"Watch-list rung at #{int(rank)}. The path is sustained per-game "
            "production + a marquee statement game."
        )
    elif rank:
        copy = (
            f"Outside the contender bubble at #{int(rank)}. Climb requires a "
            "stat-leap stretch in October/November."
        )
    else:
        copy = "Heisman trajectory populates as the season progresses."

    return {
        "award_name": award_name,
        "award_key": "heisman",
        "probability_pct": round(float(finalist_p) * 100, 1) if finalist_p else None,
        "current_rank": int(rank) if rank else None,
        "trajectory": trajectory,
        "what_needs_to_happen": copy,
        "data_state": "ready",
        "selector_breakdown": None,
    }


def build_all_america_stream(
    db: Any, player_id: int, season_year: int, award_name: str = "All-America",
) -> dict[str, Any]:
    """Selector grid + consensus detection from player_honors."""
    try:
        rows = _query_all(db,
            """
            SELECT selector, placement, honor_team, honor_scope, consensus_flag
            FROM player_honors
            WHERE player_id = :pid AND season_year = :s
              AND honor_scope = 'all_america'
            """,
            {"pid": player_id, "s": season_year},
        )
    except Exception as exc:
        log.debug("all_america stream query failed: %s", exc)
        rows = []

    selector_breakdown: dict[str, str] = {}
    is_consensus = False
    n_first = 0
    n_second = 0
    n_third = 0

    for r in rows or []:
        sel = str(r.get("selector") or "").strip().upper()
        # placement is sometimes int (1/2/3) and sometimes string ('first', '1st team').
        raw_placement = r.get("placement")
        if raw_placement is None or (isinstance(raw_placement, str) and not raw_placement.strip()):
            raw_placement = r.get("honor_team")
        if raw_placement is None:
            placement = ""
        elif isinstance(raw_placement, int):
            placement = {1: "1st team", 2: "2nd team", 3: "3rd team"}.get(raw_placement, str(raw_placement))
        else:
            placement = str(raw_placement).strip()
        if not sel:
            continue
        if "CONSENSUS" in sel or r.get("consensus_flag"):
            is_consensus = True
            continue
        # Prefer the first non-empty placement; don't downgrade by overwrite
        prev = selector_breakdown.get(sel)
        if prev and placement and not _is_higher_placement(placement, prev):
            continue
        selector_breakdown[sel] = placement
        low = placement.lower()
        if "1st" in low or "first" in low:
            n_first += 1
        elif "2nd" in low or "second" in low:
            n_second += 1
        elif "3rd" in low or "third" in low:
            n_third += 1

    if not selector_breakdown and not is_consensus:
        return _empty_stream(
            "all_america", award_name,
            "All-America selectors (AP, FWAA, AFCA, Walter Camp, Sporting News, SI) "
            "publish in December. This grid lights up once the selectors release "
            "their teams for the season.",
        )

    if is_consensus:
        copy = (
            "Named Consensus All-American — recognized on 3+ of the 5 "
            "NCAA-recognized selector lists."
        )
    elif n_first >= 3:
        copy = (
            f"Listed 1st-team by {n_first} selectors — on the doorstep of "
            "Consensus All-American."
        )
    elif n_first >= 1:
        copy = f"First-team selections from {n_first} selectors."
    elif n_second >= 1:
        copy = f"Second-team selections from {n_second} selectors."
    else:
        copy = f"Third-team selections from {n_third} selectors."

    return {
        "award_name": award_name,
        "award_key": "all_america",
        "probability_pct": None,
        "current_rank": None,
        "trajectory": [],
        "what_needs_to_happen": copy,
        "data_state": "ready",
        "selector_breakdown": selector_breakdown,
        "is_consensus": is_consensus,
    }


def _is_higher_placement(a: str, b: str) -> bool:
    rank = {"first": 3, "1st": 3, "second": 2, "2nd": 2, "third": 1, "3rd": 1}
    return rank.get(a.lower().split()[0] if a else "", 0) > rank.get(
        b.lower().split()[0] if b else "", 0
    )


def build_position_award_stream(
    db: Any,
    player_id: int,
    season_year: int,
    award_key: str,
    award_name: str,
) -> dict[str, Any]:
    """Generic position-award stream — checks player_honors for any matching
    honor_name. No dedicated trackers yet for these awards; if there's a
    confirmed past honor we surface it, otherwise honest 'awaiting' state.
    """
    try:
        rows = _query_all(db,
            """
            SELECT placement, honor_team, honor_name
            FROM player_honors
            WHERE player_id = :pid AND season_year = :s
              AND lower(honor_name) LIKE :name_lk
            """,
            {
                "pid": player_id,
                "s": season_year,
                "name_lk": f"%{award_key.replace('_', ' ').lower()}%",
            },
        )
    except Exception:
        rows = []

    if not rows:
        return _empty_stream(
            award_key, award_name,
            f"The {award_name} award tracker integrates per-week probability "
            "once a dedicated scraper for this award lands. Confirmed past "
            "winners and finalists for this player will surface here.",
        )

    row = rows[0]
    placement = str(row.get("placement") or row.get("honor_team") or "").lower()
    name = (row.get("honor_name") or "").lower()
    if "winner" in name or placement == "winner":
        copy = f"Won the {award_name} award this season."
    elif "finalist" in name:
        copy = f"{award_name} finalist — top three nationally."
    elif "watch" in name:
        copy = f"On the {award_name} watch list — the recognition has started."
    else:
        copy = f"Recognized on the {award_name} list ({placement or 'see notes'})."

    return {
        "award_name": award_name,
        "award_key": award_key,
        "probability_pct": None,
        "current_rank": None,
        "trajectory": [],
        "what_needs_to_happen": copy,
        "data_state": "ready",
        "selector_breakdown": None,
    }


def resolve_player_position(db: Any, player_id: int, season_year: int, hint: str | None) -> str:
    """Resolve a clean position for a player.

    Prefers the caller's hint when it maps to a known bucket. Otherwise falls
    back to player_honors.position from the All-America scope — which is the
    clean source (the all_conference scrape historically corrupted
    players.position with month names / opponent fragments; see
    migrations/20260526_02). Returns "" if nothing resolves (-> ATH bucket).
    """
    if hint and _normalize_position(hint) in POSITION_AWARDS:
        return hint
    try:
        rows = _query_all(
            db,
            """
            SELECT position FROM player_honors
            WHERE player_id = :pid AND season_year = :s
              AND honor_scope = 'all_america'
              AND position IS NOT NULL AND position != ''
            """,
            {"pid": player_id, "s": season_year},
        )
        for r in rows or []:
            cand = (r.get("position") or "").strip()
            if cand and _normalize_position(cand) in POSITION_AWARDS:
                return cand
    except Exception:
        pass
    return hint or ""


def build_accolade_streams_for_position(
    db: Any,
    player_id: int,
    season_year: int,
    position: str | None,
) -> list[dict[str, Any]]:
    position = resolve_player_position(db, player_id, season_year, position)
    awards = awards_for_position(position)
    streams: list[dict[str, Any]] = []
    for award_key, award_name in awards:
        if award_key == "heisman":
            streams.append(build_heisman_stream(db, player_id, season_year, award_name))
        elif award_key == "all_america":
            streams.append(build_all_america_stream(db, player_id, season_year, award_name))
        else:
            streams.append(
                build_position_award_stream(db, player_id, season_year, award_key, award_name)
            )
    return streams


# ---------------------------------------------------------------------------
# Renderer — tabs + active body
# ---------------------------------------------------------------------------


def _render_trajectory_spark(values: list[float], width: int = 160, height: int = 40) -> str:
    """Inline SVG sparkline. values in [0, 1]; dotted baseline at v=0."""
    if not values:
        return ""
    if len(values) == 1:
        values = values + values  # dup so we draw something
    pad = 4
    chart_w = width - 2 * pad
    chart_h = height - 2 * pad
    n = len(values)
    pts: list[str] = []
    for i, v in enumerate(values):
        x = pad + (chart_w * i / (n - 1))
        y = pad + chart_h * (1 - max(0.0, min(1.0, v)))
        pts.append(f"{x:.1f},{y:.1f}")
    d = "M" + " L".join(pts)
    # Baseline (start) and current dot
    start_y = pad + chart_h * (1 - max(0.0, min(1.0, values[0])))
    end_x = pad + chart_w
    end_y = pad + chart_h * (1 - max(0.0, min(1.0, values[-1])))
    return (
        f'<svg class="acc-spark" viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
        f'role="img" aria-label="Trajectory sparkline ({n} points)" '
        f'style="vertical-align:middle">'
        f'<line x1="{pad}" y1="{start_y:.1f}" x2="{end_x:.1f}" y2="{start_y:.1f}" '
        f'stroke="currentColor" stroke-opacity="0.25" stroke-dasharray="2,3" stroke-width="1"/>'
        f'<path d="{d}" fill="none" stroke="currentColor" stroke-width="1.6" '
        f'stroke-linejoin="round"/>'
        f'<circle cx="{end_x:.1f}" cy="{end_y:.1f}" r="3" fill="currentColor"/>'
        f'</svg>'
    )


def _render_selector_grid_inline(breakdown: dict[str, str], is_consensus: bool) -> str:
    """Mini selector grid — 6 NCAA-recognized selectors."""
    selectors = [
        ("AP", "Associated Press"),
        ("FWAA", "Football Writers"),
        ("AFCA", "Coaches"),
        ("WCFF", "Walter Camp"),
        ("SN", "Sporting News"),
        ("SI", "Sports Illustrated"),
    ]
    cells = []
    for key, _ in selectors:
        placement = breakdown.get(key, "")
        if is_consensus and not placement:
            placement = "1st team"
        low = placement.lower()
        if "1st" in low or "first" in low:
            cls, medal = "acc-sel--gold", "1st"
        elif "2nd" in low or "second" in low:
            cls, medal = "acc-sel--silver", "2nd"
        elif "3rd" in low or "third" in low:
            cls, medal = "acc-sel--bronze", "3rd"
        else:
            cls, medal = "", "—"
        cells.append(
            f'<div class="acc-sel-cell {cls}">'
            f'<span class="acc-sel-key">{escape(key)}</span>'
            f'<span class="acc-sel-medal">{escape(medal)}</span>'
            f'</div>'
        )
    return f'<div class="acc-sel-grid">{"".join(cells)}</div>'


ACCOLADE_TABS_CSS = """
.acc-tabs { display: flex; gap: 8px; flex-wrap: wrap; margin: 12px 0 10px 0; }
.acc-tab {
  background: transparent;
  border: 1px solid color-mix(in srgb, var(--accolade-gold-base, #c9a227) 30%, transparent);
  color: var(--foreground, #ddd);
  font-family: var(--font-sans, Inter, system-ui, sans-serif);
  font-size: 11px; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase;
  padding: 6px 12px; border-radius: 999px; cursor: pointer;
  transition: background 0.15s, color 0.15s, border-color 0.15s;
}
.acc-tab.is-active, .acc-tab[aria-pressed="true"] {
  background: color-mix(in srgb, var(--accolade-gold-base, #c9a227) 22%, transparent);
  border-color: var(--accolade-gold-base, #c9a227);
  color: var(--accolade-gold-highlight, #e4c76b);
}
.acc-tab[data-state="empty"] { opacity: 0.55; }
.acc-body {
  display: grid; grid-template-columns: minmax(120px, 200px) 1fr; gap: 18px;
  padding: 14px 16px;
  background: rgba(255,255,255,0.02);
  border: 1px solid color-mix(in srgb, var(--accolade-gold-base, #c9a227) 18%, transparent);
  border-radius: 10px;
}
@media (max-width: 640px) {
  .acc-body { grid-template-columns: 1fr; }
}
.acc-tile { display: flex; flex-direction: column; gap: 4px; }
.acc-tile-label {
  font-family: var(--font-sans, Inter, system-ui, sans-serif);
  font-size: 10px; font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase;
  color: var(--muted-foreground, #888);
}
.acc-tile-value {
  font-family: var(--font-display, 'Bebas Neue', Impact, sans-serif);
  font-size: clamp(28px, 4vw, 42px); letter-spacing: 0.02em; line-height: 1;
  color: var(--accolade-gold-highlight, #e4c76b);
}
.acc-tile-sub {
  font-family: var(--font-sans, Inter, system-ui, sans-serif);
  font-size: 11px; color: var(--muted-foreground, #888); margin-top: 4px;
}
.acc-spark { color: var(--accolade-gold-base, #c9a227); margin-top: 6px; }
.acc-copy {
  font-family: var(--font-serif, 'Source Serif Pro', Georgia, serif);
  font-size: 13px; line-height: 1.45; color: var(--foreground, #ccc);
}
.acc-sel-grid {
  display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 6px; margin-top: 8px;
}
@media (max-width: 520px) { .acc-sel-grid { grid-template-columns: repeat(3, 1fr); } }
.acc-sel-cell {
  display: grid; gap: 2px; text-align: center; padding: 6px 4px;
  background: rgba(255,255,255,0.02);
  border: 1px solid rgba(255,255,255,0.07); border-radius: 6px;
}
.acc-sel--gold {
  background: color-mix(in srgb, var(--accolade-gold-base, #c9a227) 18%, transparent);
  border-color: var(--accolade-gold-base, #c9a227);
}
.acc-sel--silver { background: rgba(192,192,200,0.10); border-color: rgba(192,192,200,0.40); }
.acc-sel--bronze { background: rgba(176,132,95,0.10); border-color: rgba(176,132,95,0.40); }
.acc-sel-key {
  font-family: var(--font-sans, Inter, system-ui, sans-serif);
  font-size: 10px; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase;
}
.acc-sel-medal {
  font-family: var(--font-display, 'Bebas Neue', Impact, sans-serif);
  font-size: 13px; letter-spacing: 0.04em;
}
.acc-sel--gold .acc-sel-medal { color: var(--accolade-gold-base, #c9a227); }
.acc-sel--silver .acc-sel-medal { color: #c0c0c8; }
.acc-sel--bronze .acc-sel-medal { color: #b0845f; }
"""


def render_accolade_tab_body(stream: dict[str, Any]) -> str:
    """Render the active-tab body for a single stream."""
    state = stream.get("data_state", "awaiting")
    if state in ("empty", "awaiting"):
        return (
            f'<div class="acc-body" data-state="{escape(state)}">'
            f'<div class="acc-tile">'
            f'<span class="acc-tile-label">Status</span>'
            f'<span class="acc-tile-value">—</span>'
            f'<span class="acc-tile-sub">Awaiting tracker</span>'
            f'</div>'
            f'<p class="acc-copy">{escape(stream.get("what_needs_to_happen") or "")}</p>'
            f'</div>'
        )

    # Probability + rank tile
    prob = stream.get("probability_pct")
    rank = stream.get("current_rank")
    if prob is not None:
        value_text = f"{prob:.1f}%"
        label_text = "Finalist probability"
    elif rank is not None:
        value_text = f"#{int(rank)}"
        label_text = "National rank"
    elif stream.get("award_key") == "all_america" and stream.get("is_consensus"):
        value_text = "CONSENSUS"
        label_text = "All-America status"
    elif stream.get("award_key") == "all_america":
        breakdown = stream.get("selector_breakdown") or {}
        n_first = sum(1 for v in breakdown.values() if "1st" in v.lower() or "first" in v.lower())
        if n_first:
            value_text = f"{n_first}×1ST"
            label_text = "1st-team selections"
        else:
            value_text = "LISTED"
            label_text = "All-America status"
    else:
        value_text = "—"
        label_text = "Status"

    sub_text = ""
    if rank is not None and prob is not None:
        sub_text = f"Currently #{int(rank)} overall"

    spark = _render_trajectory_spark(stream.get("trajectory") or [])
    selector_grid = ""
    if stream.get("award_key") == "all_america" and stream.get("selector_breakdown"):
        selector_grid = _render_selector_grid_inline(
            stream["selector_breakdown"], bool(stream.get("is_consensus"))
        )

    return (
        f'<div class="acc-body" data-state="ready">'
        f'<div class="acc-tile">'
        f'<span class="acc-tile-label">{escape(label_text)}</span>'
        f'<span class="acc-tile-value">{escape(value_text)}</span>'
        f'{f"<span class=\"acc-tile-sub\">{escape(sub_text)}</span>" if sub_text else ""}'
        f'{spark}'
        f'</div>'
        f'<div>'
        f'<p class="acc-copy">{escape(stream.get("what_needs_to_happen") or "")}</p>'
        f'{selector_grid}'
        f'</div>'
        f'</div>'
    )


def render_accolade_tabs_html(
    streams: list[dict[str, Any]], active_idx: int = 0
) -> str:
    """Render the full tabs row + active-tab body.

    Replaces the hardcoded 4-tab block in reporting.py:21120-21155.
    """
    if not streams:
        return (
            '<div class="acc-tabs-wrap" data-state="empty">'
            '<p class="acc-copy">Accolade streams populate once the position-award trackers run.</p>'
            '</div>'
        )

    # Clamp active_idx
    active_idx = max(0, min(int(active_idx), len(streams) - 1))
    # If the chosen active is empty, prefer the first 'ready' tab
    if streams[active_idx].get("data_state") != "ready":
        for i, s in enumerate(streams):
            if s.get("data_state") == "ready":
                active_idx = i
                break

    tabs_html: list[str] = []
    for i, s in enumerate(streams):
        is_active = (i == active_idx)
        cls = "acc-tab is-active" if is_active else "acc-tab"
        aria = "true" if is_active else "false"
        state = s.get("data_state", "awaiting")
        tabs_html.append(
            f'<button type="button" class="{cls}" aria-pressed="{aria}" '
            f'data-state="{escape(state)}" data-award="{escape(s["award_key"])}" '
            f'data-tab-index="{i}">{escape(s["award_name"])}</button>'
        )

    body_html = render_accolade_tab_body(streams[active_idx])
    return (
        '<div class="acc-tabs-wrap" data-state="ready">'
        f'<div class="acc-tabs" role="tablist">{"".join(tabs_html)}</div>'
        f'{body_html}'
        '</div>'
    )


__all__ = [
    "POSITION_AWARDS",
    "awards_for_position",
    "build_accolade_streams_for_position",
    "build_heisman_stream",
    "build_all_america_stream",
    "build_position_award_stream",
    "render_accolade_tabs_html",
    "render_accolade_tab_body",
    "ACCOLADE_TABS_CSS",
]
