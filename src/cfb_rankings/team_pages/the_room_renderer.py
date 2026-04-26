"""Player Pulse v2 — 'The Room' renderer.

Generates and stores LLM-backed Pulse content for the top-N players by
30-day mention velocity. All other players get the floor-rule graceful
degradation (sparse Pulse with stock-phrase fallback).

Top-N players: sourced from player_week_conversation_features, summed over
the last 4 weekly rows per player. Falls back to conversation_document_targets
raw mention counts if player_week_conversation_features is empty.

Model routing for player ledes: Sonnet for all 15 (individual players are
not entity-tier enough for Opus — Opus reserved for blue-blood programs).

Public API:
    get_top_players_by_velocity(db_conn, n=15) → list[dict]
    generate_player_room_state(player_id, db_conn) → PulseState
    generate_all_player_rooms(db_conn, top_n=15) → dict  (summary)
    render_player_room_html(player_id, db_conn) → str  (HTML fragment)
"""
from __future__ import annotations

import html as _html
import json
import logging
from typing import Any

from cfb_rankings.team_pages.pulse_state import PulseState, compute_sentiment_distribution

log = logging.getLogger(__name__)

_FLOOR_SAMPLE = 20     # below this: floor-rule fallback, no LLM
_PLAYER_MODEL = "sonnet"


# ---------------------------------------------------------------------------
# Player selection
# ---------------------------------------------------------------------------

def get_top_players_by_velocity(db_conn: Any, n: int = 15) -> list[dict]:
    """Return top-N players sorted by total mention_count over last 4 weeks.

    Tries player_week_conversation_features first (pre-aggregated, fast).
    Falls back to conversation_document_targets if result set is empty.
    """
    cur = db_conn.cursor()

    # Primary path: player_week_conversation_features
    cur.execute(
        """
        SELECT f.player_id,
               p.first_name || ' ' || p.last_name AS player_name,
               SUM(f.mention_count) AS total_mentions
        FROM player_week_conversation_features f
        JOIN players p ON p.player_id = f.player_id
        GROUP BY f.player_id
        ORDER BY total_mentions DESC
        LIMIT ?
        """,
        (n,),
    )
    rows = cur.fetchall()
    if rows:
        log.info("get_top_players_by_velocity: using player_week_conversation_features (%d rows)", len(rows))
        return [{"player_id": r[0], "player_name": r[1], "total_mentions": r[2]} for r in rows]

    # Fallback path: conversation_document_targets raw mention counts
    log.info("get_top_players_by_velocity: falling back to conversation_document_targets")
    cur.execute(
        """
        SELECT cdt.player_id,
               p.first_name || ' ' || p.last_name AS player_name,
               COUNT(*) AS total_mentions
        FROM conversation_document_targets cdt
        JOIN players p ON p.player_id = cdt.player_id
        JOIN conversation_documents cd ON cd.conversation_document_id = cdt.conversation_document_id
        WHERE cdt.player_id IS NOT NULL
          AND cd.collected_at_utc >= datetime('now', '-30 days')
        GROUP BY cdt.player_id
        ORDER BY total_mentions DESC
        LIMIT ?
        """,
        (n,),
    )
    rows = cur.fetchall()
    return [{"player_id": r[0], "player_name": r[1], "total_mentions": r[2]} for r in rows]


# ---------------------------------------------------------------------------
# State builder
# ---------------------------------------------------------------------------

def _player_total_mentions(player_id: int, db_conn: Any) -> int:
    """Total mention count from player_week_conversation_features."""
    cur = db_conn.cursor()
    cur.execute(
        "SELECT SUM(mention_count) FROM player_week_conversation_features WHERE player_id = ?",
        (player_id,),
    )
    row = cur.fetchone()
    return int(row[0] or 0) if row else 0


def generate_player_room_state(
    player_id: int,
    player_name: str,
    db_conn: Any,
) -> PulseState:
    """Build PulseState for a single player.

    Floor check uses total mention count from player_week_conversation_features,
    NOT the sentiment-labelled count (player targets are classified in a separate
    async step and may not be done yet). Theme extraction runs on raw body_text.
    """
    from cfb_rankings.team_pages import pulse_themes, pulse_lede

    entity_slug = str(player_id)
    entity_type = "player"

    total_mentions = _player_total_mentions(player_id, db_conn)
    dist, mean_sent, sent_sample = compute_sentiment_distribution(
        entity_slug, entity_type, db_conn
    )

    state = PulseState(
        entity_slug=entity_slug,
        entity_type=entity_type,
        week=None,
        sentiment_distribution=dist,
        mean_sentiment=mean_sent,
        sample_size=total_mentions,
    )

    if total_mentions < _FLOOR_SAMPLE:
        log.info("player %s (%s): below floor (%d mentions), using fallback", player_id, player_name, total_mentions)
        return state  # is_live = False

    # Run theme extraction — always 1 theme per player (partial tier)
    themes = pulse_themes.extract_entity_themes(
        entity_slug, entity_type, "partial", db_conn, entity_name=player_name
    )
    lede_result = pulse_lede.generate_entity_lede(
        entity_slug, entity_type, themes, _PLAYER_MODEL, db_conn,
        entity_name=player_name,
    )

    state.themes = themes
    state.lede = lede_result.get("text")
    state.lede_model = _PLAYER_MODEL
    state.is_live = bool(state.lede or state.themes)

    return state


def generate_all_player_rooms(
    db_conn: Any,
    top_n: int = 15,
) -> dict[str, Any]:
    """Generate Room v2 states for top-N players. Returns summary dict."""
    players = get_top_players_by_velocity(db_conn, n=top_n)
    processed = 0
    live = 0
    fallback = 0

    for p in players:
        pid = p["player_id"]
        name = p["player_name"]
        log.info("the_room: processing player %d (%s)", pid, name)
        state = generate_player_room_state(pid, name, db_conn)
        processed += 1
        if state.is_live:
            live += 1
        else:
            fallback += 1
        _print_progress(p, state)

    return {"processed": processed, "live": live, "fallback": fallback, "top_n": top_n}


def _print_progress(player: dict, state: PulseState) -> None:
    status = "LIVE" if state.is_live else "FALLBACK"
    themes_n = len(state.themes)
    lede_preview = (state.lede or "")[:60] if state.lede else "(none)"
    print(
        f"  [{status}] {player['player_name']} (id={player['player_id']}) "
        f"vel={player.get('total_mentions','?')} "
        f"themes={themes_n} lede={repr(lede_preview)}",
        flush=True,
    )


# ---------------------------------------------------------------------------
# HTML renderer
# ---------------------------------------------------------------------------

def render_player_room_html(player_id: int, db_conn: Any) -> str:
    """Load cached PulseState from DB and render HTML fragment for The Room."""
    from cfb_rankings.team_pages.pulse_themes import load_themes
    from cfb_rankings.team_pages.pulse_lede import load_lede

    entity_slug = str(player_id)
    themes = load_themes(entity_slug, "player", db_conn) or []
    lede = load_lede(entity_slug, "player", db_conn)
    is_live = bool(themes or lede)

    dist, mean_sent, sample = compute_sentiment_distribution(
        entity_slug, "player", db_conn
    )

    lede_html = (
        f'<p class="room__lede">{_html.escape(lede)}</p>'
        if lede
        else '<p class="room__lede room__lede--fallback">Signal building. Check back soon.</p>'
    )

    theme_items = []
    for t in themes[:2]:
        label = _html.escape(t.get("label", ""))
        summary = _html.escape(t.get("summary", ""))
        quote = t.get("representative_quote", "").strip()
        quote_html = (
            f'<blockquote class="room__theme-quote">"{_html.escape(quote)}"</blockquote>'
        ) if quote else ""
        theme_items.append(
            f'<div class="room__theme">'
            f'<strong class="room__theme-label">{label}</strong>'
            f'<span class="room__theme-summary">{summary}</span>'
            f'{quote_html}</div>'
        )
    themes_html = "\n".join(theme_items)

    sent_html = ""
    if dist and sample >= 100:
        total = dist["positive"] + dist["neutral"] + dist["negative"]
        p_pct = round(100 * dist["positive"] / max(1, total))
        n_pct = round(100 * dist["neutral"] / max(1, total))
        neg_pct = 100 - p_pct - n_pct
        mean_sign = "+" if (mean_sent or 0) >= 0 else ""
        sent_html = (
            f'<div class="room__sentiment">'
            f'<div class="room__sentiment-bar room__sentiment-bar--pos" style="width:{p_pct}%"></div>'
            f'<div class="room__sentiment-bar room__sentiment-bar--neu" style="width:{n_pct}%"></div>'
            f'<div class="room__sentiment-bar room__sentiment-bar--neg" style="width:{neg_pct}%"></div>'
            f'</div>'
            f'<div class="room__sentiment-meta">{sample:,} mentions · '
            f'{mean_sign}{(mean_sent or 0):.2f} net sentiment</div>'
        )

    live_cls = "room--live" if is_live else "room--fallback"

    return f"""<section class="the-room {live_cls}" aria-labelledby="room-pulse-{player_id}">
  <h3 id="room-pulse-{player_id}" class="room__title">The Room</h3>
  {lede_html}
  {themes_html}
  {sent_html}
</section>"""
