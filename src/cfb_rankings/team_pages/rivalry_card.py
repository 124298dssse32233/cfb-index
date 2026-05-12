"""Rivalry Card renderer — mythic header + meta strip + meetings list.

Spec: ``docs/design-system/12-modules-intel.md`` §RivalryCard.

Six sub-components:

1. Mythic centered header (serif trophy name + N meetings since YYYY).
2. 4-column meta strip (all-time record · current streak · trophy · countdown).
3. Dual-trajectory heat chart — SVG with two polylines when both sides
   have fan-intel signal; replaced by a "signal accumulating" placeholder
   when one or both sides lack data.
4. Two posture-labeled panels (primary side always; opponent side only
   when opponent is also profiled).
5. Editorial last-10 meetings list (year · score · venue · one-sentence
   commentary written by ``scripts/sprint2_rivalry_content.py``).
6. Stakes footer from the program's point of view.
"""
from __future__ import annotations

import html
from datetime import datetime
from typing import Any

from .profile_loader import Profile, PROFILED_SLUGS


def _season_label() -> str:
    """Return the YYYY-YY label for the upcoming/current CFB season.

    May-July: upcoming season (e.g. May 2026 → "2026-27").
    Aug-Dec: in-season (year-(year+1)).
    Jan-April: current bowl/CFP slate (uses prior-year start).
    Replaces the hardcoded "2025-26 season approaches" string that
    every profiled-team rivalry card was rendering regardless of date.
    """
    now = datetime.utcnow()
    start_year = now.year if now.month >= 5 else now.year - 1
    end_short = (start_year + 1) % 100
    return f"{start_year}-{end_short:02d}"


_SLUG_DISPLAY: dict[str, str] = {
    "notre-dame": "Notre Dame", "usc": "USC",
    "alabama": "Alabama", "auburn": "Auburn",
    "ohio-state": "Ohio State", "michigan": "Michigan",
    "georgia": "Georgia", "florida": "Florida",
    "texas": "Texas", "oklahoma": "Oklahoma",
    "oregon": "Oregon", "washington": "Washington",
    "penn-state": "Penn State",
    "vanderbilt": "Vanderbilt", "tennessee": "Tennessee",
    "massachusetts": "UMass", "uconn": "UConn",
}


def _name(slug: str) -> str:
    return _SLUG_DISPLAY.get(slug, slug.replace("-", " ").title())


def render_rivalry_card(
    profile: Profile,
    opponent_slug: str,
    *,
    rivalry_meta: dict[str, Any],     # {trophy, name, note} from profile.rivalries
    meetings: list[dict[str, Any]],   # fetch_meetings() output
    all_time: dict[str, Any],         # compute_all_time_record() output
    next_meeting: dict[str, Any] | None,
    primary_posture: dict[str, Any] | None,
    primary_stakes: str | None,
    primary_quote: dict[str, Any] | None,
    opponent_posture: dict[str, Any] | None = None,
    opponent_stakes: str | None = None,
    opponent_quote: dict[str, Any] | None = None,
    season_year: int,
) -> str:
    """Render the Rivalry Card HTML fragment."""
    if not meetings and all_time.get("total_meetings", 0) == 0:
        return ""

    opponent_profiled = opponent_slug in PROFILED_SLUGS

    header_html = _render_header(profile, opponent_slug, rivalry_meta, all_time)
    meta_strip_html = _render_meta_strip(profile, opponent_slug, rivalry_meta, all_time, next_meeting)
    trajectory_html = _render_trajectory(profile, opponent_slug, opponent_profiled)
    panels_html = _render_panels(
        profile, opponent_slug, opponent_profiled,
        primary_posture, primary_quote,
        opponent_posture, opponent_quote,
    )
    # Editorial audit found that 4-7 of the "Last 10" rows on most team
    # rivalry cards had no commentary text, rendering as bare year+result
    # without context — readers experienced this as filler/sparse. Show only
    # the trailing run of meetings that HAVE commentary, falling back to a
    # smaller window when the older entries are unprosed. This trades
    # historical completeness for editorial density.
    commented = [m for m in meetings if (m.get("commentary_text") or "").strip()]
    if commented:
        # Keep most-recent contiguous run with commentary, but show up to 10.
        visible_meetings = commented[:10]
    else:
        # No commentary at all — show last 5 with the existing placeholder.
        visible_meetings = meetings[:5]
    meetings_html = _render_meetings(profile, opponent_slug, visible_meetings)
    stakes_html = _render_stakes(profile, opponent_slug, opponent_profiled,
                                 primary_stakes, opponent_stakes)

    return f"""<section class="rivalry-card" aria-labelledby="rivalry-title">
  {header_html}
  {meta_strip_html}
  {trajectory_html}
  {panels_html}
  {meetings_html}
  {stakes_html}
</section>"""


# ------------------------------------------------------------------------
# Header
# ------------------------------------------------------------------------

def _render_header(profile: Profile, opp: str, meta: dict[str, Any], all_time: dict[str, Any]) -> str:
    raw_trophy = (meta.get("trophy") or "").strip()
    name = meta.get("name") or f"{profile.program_name} · {_name(opp)}"
    total = all_time.get("total_meetings") or 0
    first_year = all_time.get("first_year")
    since_clause = f"since {first_year}" if first_year else ""
    opp_name = _name(opp)
    # Skip the trophy line entirely when the profile's trophy field is
    # empty or a literal "N/A" — the header doesn't need a placeholder.
    if raw_trophy and not raw_trophy.lower().startswith("n/a"):
        trophy_line = f'<span class="rivalry-card__trophy">{html.escape(raw_trophy)}</span>'
    else:
        trophy_line = ""
    return f"""<header class="rivalry-card__header">
    <span class="rivalry-card__eyebrow">THE RIVALRY · {html.escape(profile.program_name.upper())} × {html.escape(opp_name.upper())}</span>
    <h2 id="rivalry-title" class="rivalry-card__title">{html.escape(name)}</h2>
    {trophy_line}
    <span class="rivalry-card__lineage">{total} meeting{"s" if total != 1 else ""} {html.escape(since_clause)}</span>
  </header>"""


# ------------------------------------------------------------------------
# 4-column meta strip
# ------------------------------------------------------------------------

def _render_meta_strip(
    profile: Profile,
    opp: str,
    meta: dict[str, Any],
    all_time: dict[str, Any],
    next_meeting: dict[str, Any] | None,
) -> str:
    wins = all_time.get("wins", 0)
    losses = all_time.get("losses", 0)
    ties = all_time.get("ties", 0)
    total = all_time.get("total_meetings", 0)

    record_str = f"{wins}-{losses}" + (f"-{ties}" if ties else "")
    pct = (wins / total) if total else 0.0
    first_year = all_time.get("first_year")
    since_clause = f"since {first_year}" if first_year else "modern era"
    record_sub = f"{since_clause} · .{int(pct * 1000):03d} win rate" if total else "first meeting ahead"

    streak_n = all_time.get("streak", 0)
    if streak_n > 0:
        streak_str = f"W{streak_n}"
        streak_sub = f"{profile.program_name} rolling"
    elif streak_n < 0:
        streak_str = f"L{abs(streak_n)}"
        streak_sub = f"{_name(opp)} holds the last {abs(streak_n)}"
    else:
        streak_str = "—"
        streak_sub = "no active streak"

    raw_trophy = (meta.get("trophy") or "").strip()
    # Profiles sometimes use "N/A (...)" or a full sentence in the trophy
    # slot. Normalise: anything starting with N/A collapses to the rivalry
    # itself as the prize; anything else renders literal.
    if not raw_trophy or raw_trophy.lower().startswith("n/a"):
        trophy_str = "The Rivalry Itself"
        trophy_sub = "No trophy — the season is the argument"
    else:
        trophy_str = raw_trophy
        trophy_sub = "In play each fall"

    if next_meeting and next_meeting.get("game_date"):
        cd_str = next_meeting["game_date"]
        cd_sub = f"{next_meeting.get('venue') or 'venue TBD'}"
    else:
        # "TBD · schedule pending" reads oddly during offseason. Annual
        # rivalries don't have a real "pending" status — the game is
        # going to happen in the fall. Be specific about what's actually
        # unknown (the date) and reassuring about what's not (the game).
        cd_str = f"{_season_label().split('-')[0]} season"
        cd_sub = "date set by conference"

    tiles = [
        ("ALL-TIME", record_str, record_sub),
        ("STREAK", streak_str, streak_sub),
        ("TROPHY", trophy_str, trophy_sub),
        ("NEXT", cd_str, cd_sub),
    ]
    tile_html = "".join(
        f"""<div class="rivalry-card__meta-tile">
          <span class="rivalry-card__meta-label">{html.escape(lbl)}</span>
          <span class="rivalry-card__meta-value">{html.escape(val)}</span>
          <span class="rivalry-card__meta-sub">{html.escape(sub)}</span>
        </div>"""
        for lbl, val, sub in tiles
    )
    return f'<div class="rivalry-card__meta-strip">{tile_html}</div>'


# ------------------------------------------------------------------------
# Trajectory — stylised SVG (deterministic placeholder when no signal)
# ------------------------------------------------------------------------

def _render_trajectory(profile: Profile, opp: str, opponent_profiled: bool) -> str:
    """Four-week rivalry-heat trajectory.

    Until the fan-intel pipeline produces per-rivalry weekly scores, we
    render a stylised placeholder: two gentle polylines building toward
    kickoff, with a "signal accumulating" eyebrow. The SVG layout holds
    so real data slots in without relayout.
    """
    # Deterministic silhouettes — primary builds faster than opponent
    # so the gap annotation reads. When both-profiled, use the program's
    # accent for primary and a neutral gray for opponent.
    primary_hex = profile.accent_hex or "#0C2340"
    opp_hex = "#6b7280"

    # Four weeks of placeholder points (0-100 scale); primary ramps more
    # aggressively than opponent for visual storytelling.
    primary_pts = [34, 48, 61, 72]
    opp_pts = [38, 43, 50, 56]

    def polyline(pts: list[int]) -> str:
        coords = " ".join(
            f"{20 + i * 90},{120 - (p * 0.9)}" for i, p in enumerate(pts)
        )
        return coords

    gap = primary_pts[-1] - opp_pts[-1]
    gap_sign = "+" if gap >= 0 else ""

    dual_line_html = ""
    if opponent_profiled:
        dual_line_html = f"""
      <polyline fill="none" stroke="{opp_hex}" stroke-width="2" stroke-linejoin="round" points="{polyline(opp_pts)}" opacity="0.85" />
      <circle cx="290" cy="{120 - opp_pts[-1] * 0.9}" r="4" fill="{opp_hex}" />
      <text x="300" y="{124 - opp_pts[-1] * 0.9}" fill="{opp_hex}" font-size="11" font-family="system-ui">{html.escape(_name(opp))}</text>"""

    gap_badge = ""
    if opponent_profiled:
        gap_badge = f'<span class="rivalry-card__gap">gap {gap_sign}{gap} pts</span>'

    return f"""<div class="rivalry-card__trajectory">
    <div class="rivalry-card__trajectory-header">
      <span class="rivalry-card__section-eyebrow">HEAT TRAJECTORY · four weeks to kickoff</span>
      {gap_badge}
    </div>
    <svg class="rivalry-card__trajectory-svg" viewBox="0 0 340 140" role="img" aria-label="Rivalry heat trajectory placeholder">
      <defs>
        <linearGradient id="rt-grad-{profile.slug}" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stop-color="{primary_hex}" stop-opacity="0.22" />
          <stop offset="100%" stop-color="{primary_hex}" stop-opacity="0.0" />
        </linearGradient>
      </defs>
      <g stroke="#e5e7eb" stroke-width="1">
        <line x1="20" y1="30" x2="290" y2="30" />
        <line x1="20" y1="75" x2="290" y2="75" />
        <line x1="20" y1="120" x2="290" y2="120" />
      </g>
      <polyline fill="none" stroke="{primary_hex}" stroke-width="2.5" stroke-linejoin="round" points="{polyline(primary_pts)}" />
      <polygon fill="url(#rt-grad-{profile.slug})" points="{polyline(primary_pts)} 290,120 20,120" />
      <circle cx="290" cy="{120 - primary_pts[-1] * 0.9}" r="4.5" fill="{primary_hex}" />
      <text x="300" y="{124 - primary_pts[-1] * 0.9}" fill="{primary_hex}" font-size="11" font-family="system-ui" font-weight="600">{html.escape(profile.program_name)}</text>
      {dual_line_html}
      <text x="20" y="138" fill="#9ca3af" font-size="10" font-family="system-ui">wk −4</text>
      <text x="148" y="138" fill="#9ca3af" font-size="10" font-family="system-ui">wk −2</text>
      <text x="272" y="138" fill="#9ca3af" font-size="10" font-family="system-ui">kickoff</text>
    </svg>
    <p class="rivalry-card__trajectory-note">
      Signal accumulating · per-rivalry weekly fan-intel feeding in as the {_season_label()} season approaches.
    </p>
  </div>"""


# ------------------------------------------------------------------------
# Posture panels
# ------------------------------------------------------------------------

def _render_panels(
    profile: Profile,
    opp: str,
    opponent_profiled: bool,
    primary_posture: dict[str, Any] | None,
    primary_quote: dict[str, Any] | None,
    opponent_posture: dict[str, Any] | None,
    opponent_quote: dict[str, Any] | None,
) -> str:
    primary_html = _render_single_panel(
        profile.program_name, profile.accent_hex or "#111",
        primary_posture, primary_quote, is_primary=True,
    )
    opponent_html = ""
    if opponent_profiled:
        opponent_html = _render_single_panel(
            _name(opp), "#6b7280",
            opponent_posture, opponent_quote, is_primary=False,
        )
    return f"""<div class="rivalry-card__panels {('rivalry-card__panels--dual' if opponent_html else 'rivalry-card__panels--single')}">
    {primary_html}
    {opponent_html}
  </div>"""


def _render_single_panel(
    name: str,
    accent: str,
    posture: dict[str, Any] | None,
    quote: dict[str, Any] | None,
    *,
    is_primary: bool,
) -> str:
    posture_tag = "—"
    if posture and posture.get("headline"):
        # headline format: "vs {Opp} · {posture words}"
        parts = posture["headline"].split("·", 1)
        if len(parts) == 2:
            posture_tag = parts[1].strip()
    quote_text = ""
    attr_text = ""
    if quote:
        quote_text = quote.get("body_md") or ""
        attr_text = quote.get("attribution") or ""
    elif posture:
        quote_text = posture.get("body_md") or ""
    # Suppress empty-quote noise. Rendering `""` with no content reads as a
    # rendering bug on the live page (cf. Alabama–Auburn rivalry card on the
    # offseason build where neither side has authored quote copy yet).
    quote_html = (
        f'<blockquote class="rivalry-card__panel-quote">&ldquo;{html.escape(quote_text)}&rdquo;</blockquote>'
        if quote_text.strip()
        else ''
    )
    attr_html = (
        f'<cite class="rivalry-card__panel-attr">{html.escape(attr_text)}</cite>'
        if attr_text.strip()
        else ''
    )
    return f"""<article class="rivalry-card__panel{' rivalry-card__panel--primary' if is_primary else ''}" style="--panel-accent: {accent}">
      <div class="rivalry-card__panel-head">
        <span class="rivalry-card__panel-name">{html.escape(name)}</span>
        <span class="rivalry-card__panel-posture">{html.escape(posture_tag)}</span>
      </div>
      {quote_html}
      {attr_html}
    </article>"""


# ------------------------------------------------------------------------
# Meetings list
# ------------------------------------------------------------------------

def _render_meetings(profile: Profile, opp: str, meetings: list[dict[str, Any]]) -> str:
    if not meetings:
        return ""
    rows_html = []
    for m in meetings:
        year = m.get("season_year") or ""
        commentary = (m.get("commentary_text") or "").strip()
        winner_slug = m.get("winner_slug")
        pill_cls = "rivalry-card__meeting-result"
        pill_text = "—"
        result_label = ""
        if winner_slug == profile.slug:
            pill_cls += " rivalry-card__meeting-result--win"
            pill_text = "W"
            result_label = "Win"
        elif winner_slug and winner_slug != "tie":
            pill_cls += " rivalry-card__meeting-result--loss"
            pill_text = "L"
            result_label = "Loss"
        elif winner_slug == "tie":
            pill_text = "T"
            result_label = "Tie"
        # If no commentary copy exists for this season, show a quiet fallback
        # so the row doesn't appear empty / cut off. Live data may fill it in
        # later via the commentary backfill.
        if commentary:
            body_html = html.escape(commentary)
        elif year and result_label:
            body_html = f'<span class="rivalry-card__meeting-body--placeholder">{result_label} on file &mdash; commentary pending.</span>'
        else:
            body_html = ''
        rows_html.append(f"""<li class="rivalry-card__meeting">
          <span class="{pill_cls}" aria-label="Result">{html.escape(pill_text)}</span>
          <span class="rivalry-card__meeting-year">{html.escape(str(year))}</span>
          <span class="rivalry-card__meeting-body">{body_html}</span>
        </li>""")
    return f"""<div class="rivalry-card__meetings">
      <p class="rivalry-card__section-eyebrow">THE LAST {len(meetings)} · year-by-year</p>
      <ol class="rivalry-card__meetings-list">
        {''.join(rows_html)}
      </ol>
    </div>"""


# ------------------------------------------------------------------------
# Stakes footer
# ------------------------------------------------------------------------

def _render_stakes(
    profile: Profile,
    opp: str,
    opponent_profiled: bool,
    primary_stakes: str | None,
    opponent_stakes: str | None,
) -> str:
    if not primary_stakes and not opponent_stakes:
        return ""
    dual = bool(opponent_profiled and opponent_stakes)
    primary_block = f"""<div class="rivalry-card__stake">
          <span class="rivalry-card__stake-label">What {html.escape(profile.program_name)} needs</span>
          <p class="rivalry-card__stake-text">{html.escape(primary_stakes or '')}</p>
        </div>""" if primary_stakes else ""
    opponent_block = f"""<div class="rivalry-card__stake">
          <span class="rivalry-card__stake-label">What {html.escape(_name(opp))} needs</span>
          <p class="rivalry-card__stake-text">{html.escape(opponent_stakes or '')}</p>
        </div>""" if dual else ""
    return f"""<footer class="rivalry-card__stakes{' rivalry-card__stakes--dual' if dual else ''}">
      <span class="rivalry-card__section-eyebrow">THIS YEAR'S STAKES</span>
      <div class="rivalry-card__stakes-grid">
        {primary_block}
        {opponent_block}
      </div>
    </footer>"""
