"""Live Signal Flow placeholder — Brief Signature Bet #13.

Top-of-page bar that surfaces real-time fan-conversation signal volume
for this player. Currently empty (no live conversation pipeline yet),
but the placeholder reserves the visual + a/b layout slot for when the
pipeline ships.

Renders 3 timing-based bands (last hour / last 24h / last week) using
the player_signal_events table. Falls back to a tasteful "Awaiting Signal"
panel when the table is empty.

Public API:
    render_live_signal_flow(db, player_id) -> str
    LIVE_SIGNAL_FLOW_CSS                    -> str
"""
from __future__ import annotations

from html import escape


LIVE_SIGNAL_FLOW_CSS = """
/* Live Signal Flow placeholder */
.live-signal-flow {
  margin: var(--space-3, 0.75rem) 0 var(--space-4, 1rem) 0;
  padding: clamp(10px, 1.4vw, 14px) clamp(14px, 1.8vw, 20px);
  background: rgba(255, 255, 255, 0.02);
  border: 1px dashed var(--stroke-subtle, rgba(255,255,255,0.10));
  border-radius: 10px;
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}
.live-signal-flow__eyebrow {
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--muted-foreground, var(--fg-muted, #666));
  margin: 0;
}
.live-signal-flow__bands {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  flex: 1;
}
.live-signal-flow__band {
  display: inline-flex;
  align-items: baseline;
  gap: 6px;
  padding: 3px 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid var(--stroke-subtle, rgba(255,255,255,0.06));
}
.live-signal-flow__band-label {
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.10em;
  text-transform: uppercase;
  color: var(--muted-foreground, var(--fg-muted, #666));
}
.live-signal-flow__band-value {
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 11px;
  color: var(--foreground, var(--fg-secondary, #999));
}
.live-signal-flow__band-value--awaiting {
  font-style: italic;
  color: var(--muted-foreground, var(--fg-muted, #666));
}
.live-signal-flow__status {
  font-family: var(--font-serif, 'Source Serif Pro', Georgia, serif);
  font-size: 11px;
  font-style: italic;
  color: var(--muted-foreground, var(--fg-muted, #666));
}
"""


def _fetch_signal_bands(db, player_id: int) -> dict[str, int | None]:
    """Return signal counts for last_hour, last_24h, last_week.

    Returns None for any band when the table is empty (placeholder mode).
    """
    try:
        rows = db.query_all(
            """
            select
              sum(case when event_at_utc >= datetime('now', '-1 hour') then 1 else 0 end) as h,
              sum(case when event_at_utc >= datetime('now', '-1 day') then 1 else 0 end) as d,
              sum(case when event_at_utc >= datetime('now', '-7 days') then 1 else 0 end) as w
              from player_signal_events
             where player_id = :pid
            """,
            {"pid": player_id},
        )
    except Exception:
        return {"hour": None, "day": None, "week": None}
    if not rows or all(rows[0].get(k) is None for k in ("h", "d", "w")):
        return {"hour": None, "day": None, "week": None}
    r = rows[0]
    return {
        "hour": int(r.get("h") or 0),
        "day": int(r.get("d") or 0),
        "week": int(r.get("w") or 0),
    }


def render_live_signal_flow(db, player_id: int | None) -> str:
    if db is None or player_id is None:
        return ""
    bands = _fetch_signal_bands(db, int(player_id))
    any_value = any(v is not None and v > 0 for v in bands.values())

    band_html: list[str] = []
    for label, key in [("Last hr", "hour"), ("Last 24h", "day"), ("Last 7d", "week")]:
        val = bands.get(key)
        if val is None or val == 0:
            value_html = (
                '<span class="live-signal-flow__band-value '
                'live-signal-flow__band-value--awaiting">awaiting</span>'
            )
        else:
            value_html = f'<span class="live-signal-flow__band-value">{val}</span>'
        band_html.append(
            '<span class="live-signal-flow__band">'
            f'<span class="live-signal-flow__band-label">{label}</span>'
            f'{value_html}'
            '</span>'
        )

    status = (
        'Live signal collection active — refresh every 30 min during season.'
        if any_value
        else 'Live signal pipeline placeholder. Activates during season once conversation tracking lands.'
    )

    return f"""
<section class="live-signal-flow" data-module="live-signal-flow"
         data-state="{'ready' if any_value else 'awaiting'}">
  <p class="live-signal-flow__eyebrow">Live Signal Flow</p>
  <div class="live-signal-flow__bands">{''.join(band_html)}</div>
  <span class="live-signal-flow__status">{escape(status)}</span>
</section>"""


__all__ = ["render_live_signal_flow", "LIVE_SIGNAL_FLOW_CSS"]
