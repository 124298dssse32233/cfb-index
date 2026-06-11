"""The Rivalry Mirror team-page module — a Group Chat Noir "night band".

The fight card: what each fanbase's language does when it mentions the other.
For one rivalry pair, the most statistically distinctive terms inside
rival-mention windows (weighted log-odds, both directions, equal scales) are
rendered as a two-sided tug-of-war. The asymmetry is the finding — when one
side has no surviving terms, we say so instead of faking balance.

Reads team_discourse_mirror (written by ``manage.py compute-discourse-mirror``,
Language Layer Wave 2). Confidence floor: >= 3 surviving terms on at least one
side AND >= 80 total rival-mention docs across both sides — otherwise the
module returns "" and collapses out of the act (graceful-degradation contract).

Public API:
    render_mirror(db, profile, snapshot) -> str
    MIRROR_MODULE_CSS                    -> str
"""

from __future__ import annotations

from html import escape
from typing import Any

from cfb_rankings.fan_metrics.backometer_render import (
    CHALK,
    GROUND,
    HAIRLINE,
    RECEIPT,
    SURFACE,
    _DISPLAY_STACK,
    _MONO_STACK,
)

from .data import TeamSnapshot
from .profile_loader import Profile

_MAX_TERMS_PER_SIDE = 5
_MIN_SIDE_TERMS = 3
_MIN_TOTAL_DOCS = 80
_FALLBACK_LEFT = "#E8B84B"   # gold — readable on GROUND when accent is too dark
_FALLBACK_RIGHT = "#FF5A4E"  # signal red — mockup right-side default

_ROW_KEYS = (
    "rival_team_id", "term", "term_rank", "window_count", "z_score",
    "side_token_count", "rival_mention_doc_count",
    "sample_quote", "sample_quote_source", "side_team_id",
)


def _field(row: Any, key: str) -> Any:
    """Read a column from a dict-like or tuple row (defensive, chronicle-style)."""
    try:
        return row[key]
    except (TypeError, KeyError, IndexError):
        pass
    try:
        return row[_ROW_KEYS.index(key)]
    except (TypeError, ValueError, IndexError):
        return None


def _safe_band_color(hex_in: Any, fallback: str) -> str:
    """Accept only '#rrggbb' values bright enough to read on the night band.

    team_brand.primary_color holds the literal string '#null' for ~313 rows,
    and many real accents are near-black (unreadable on GROUND #101418).
    """
    if not isinstance(hex_in, str) or len(hex_in) != 7 or not hex_in.startswith("#"):
        return fallback
    try:
        r = int(hex_in[1:3], 16)
        g = int(hex_in[3:5], 16)
        b = int(hex_in[5:7], 16)
    except ValueError:
        return fallback
    # Perceived luminance floor — dark navy/black accents fall back.
    if (0.299 * r + 0.587 * g + 0.114 * b) < 60:
        return fallback
    return hex_in


def _tug_cell(side: str, term: str, z: float, max_z: float) -> str:
    """One half of a tug-of-war row. Stem/dot scaled by z within the pair's
    own max-z; printed z chip is the source of truth."""
    width = round(max(6.0, (z / max_z) * 88.0), 1) if max_z > 0 else 6.0
    term_html = escape(term)
    z_chip = f'<span class="mirror-band__tz">z {z:.1f}</span>'
    if side == "l":
        return (
            f'<div class="mirror-band__cell mirror-band__cell--l">'
            f'<div class="mirror-band__spine"></div>'
            f'<div class="mirror-band__stem" style="width:{width}%"></div>'
            f'<div class="mirror-band__tdot" style="right:calc({width}% - 6px)"></div>'
            f'<div class="mirror-band__tlabel" style="right:calc({width}% + 12px)">'
            f'{term_html}{z_chip}</div></div>'
        )
    return (
        f'<div class="mirror-band__cell mirror-band__cell--r">'
        f'<div class="mirror-band__spine"></div>'
        f'<div class="mirror-band__stem" style="width:{width}%"></div>'
        f'<div class="mirror-band__tdot" style="left:{width}%"></div>'
        f'<div class="mirror-band__tlabel" style="left:6px">'
        f'{term_html}{z_chip}</div></div>'
    )


def _empty_cell(side: str) -> str:
    return (
        f'<div class="mirror-band__cell mirror-band__cell--{side}">'
        f'<div class="mirror-band__spine"></div></div>'
    )


def render_mirror(db, profile: Profile, snapshot: TeamSnapshot | None) -> str:
    if db is None or snapshot is None or not getattr(snapshot, "team_id", None):
        return ""
    team_id = int(snapshot.team_id)
    try:
        season_row = db.query_one(
            "SELECT MAX(season_year) AS season FROM team_discourse_mirror "
            "WHERE team_id = :team_id OR rival_team_id = :team_id",
            {"team_id": team_id},
        )
        if season_row is None:
            return ""
        try:
            season = season_row["season"]
        except (TypeError, KeyError, IndexError):
            season = season_row[0]
        if season is None:
            return ""
        season = int(season)
        # Our side: this team's fans talking about each rival.
        our_rows = db.query_all(
            "SELECT rival_team_id, term, term_rank, window_count, z_score, "
            "side_token_count, rival_mention_doc_count, "
            "sample_quote, sample_quote_source, team_id AS side_team_id "
            "FROM team_discourse_mirror "
            "WHERE team_id = :team_id AND season_year = :season "
            "ORDER BY term_rank ASC",
            {"team_id": team_id, "season": season},
        )
        # Their side: each rival's fans talking about this team.
        their_rows = db.query_all(
            "SELECT team_id AS rival_team_id, term, term_rank, window_count, "
            "z_score, side_token_count, rival_mention_doc_count, "
            "sample_quote, sample_quote_source, team_id AS side_team_id "
            "FROM team_discourse_mirror "
            "WHERE rival_team_id = :team_id AND season_year = :season "
            "ORDER BY term_rank ASC",
            {"team_id": team_id, "season": season},
        )
    except Exception:
        # Table may not exist yet (migration owned by another wave) — skip.
        return ""

    by_rival: dict[int, dict[str, list[Any]]] = {}
    for row in our_rows:
        rid = _field(row, "rival_team_id")
        if rid is None:
            continue
        by_rival.setdefault(int(rid), {"ours": [], "theirs": []})["ours"].append(row)
    for row in their_rows:
        rid = _field(row, "rival_team_id")
        if rid is None:
            continue
        by_rival.setdefault(int(rid), {"ours": [], "theirs": []})["theirs"].append(row)
    if not by_rival:
        return ""

    def _side_docs(rows: list[Any]) -> int:
        return int(_field(rows[0], "rival_mention_doc_count") or 0) if rows else 0

    # Pick the rival with the highest combined rival-mention volume.
    rival_id = max(
        by_rival,
        key=lambda rid: _side_docs(by_rival[rid]["ours"]) + _side_docs(by_rival[rid]["theirs"]),
    )
    ours = by_rival[rival_id]["ours"][:_MAX_TERMS_PER_SIDE]
    theirs = by_rival[rival_id]["theirs"][:_MAX_TERMS_PER_SIDE]
    our_docs = _side_docs(by_rival[rival_id]["ours"])
    their_docs = _side_docs(by_rival[rival_id]["theirs"])

    # Confidence floor: real signal on at least one side, real volume overall.
    if max(len(ours), len(theirs)) < _MIN_SIDE_TERMS:
        return ""
    if (our_docs + their_docs) < _MIN_TOTAL_DOCS:
        return ""

    team_name = str(getattr(snapshot, "canonical_name", None) or profile.program_name or "This team")
    rival_name = None
    rival_color_raw = None
    try:
        rival_row = db.query_one(
            "SELECT t.short_name, t.canonical_name, tb.primary_color "
            "FROM teams t LEFT JOIN team_brand tb ON tb.team_id = t.team_id "
            "WHERE t.team_id = :rid",
            {"rid": rival_id},
        )
        if rival_row is not None:
            try:
                rival_name = rival_row["short_name"] or rival_row["canonical_name"]
                rival_color_raw = rival_row["primary_color"]
            except (TypeError, KeyError, IndexError):
                rival_name = rival_row[0] or rival_row[1]
                rival_color_raw = rival_row[2]
    except Exception:
        pass
    if not rival_name:
        return ""
    rival_name = str(rival_name)

    left_color = _safe_band_color(getattr(profile, "accent_hex", None), _FALLBACK_LEFT)
    right_color = _safe_band_color(rival_color_raw, _FALLBACK_RIGHT)
    if right_color == left_color:
        right_color = _FALLBACK_RIGHT if left_color != _FALLBACK_RIGHT else _FALLBACK_LEFT

    z_values = [float(_field(r, "z_score") or 0.0) for r in ours + theirs]
    max_z = max(z_values) if z_values else 1.0

    sparse_line = "their {who} talk is indistinguishable from their everyday talk"
    left_sparse = len(ours) < _MIN_SIDE_TERMS
    right_sparse = len(theirs) < _MIN_SIDE_TERMS

    rows_html: list[str] = []
    for i in range(max(len(ours), len(theirs), _MIN_SIDE_TERMS if (left_sparse or right_sparse) else 0)):
        left = (
            _tug_cell("l", str(_field(ours[i], "term") or ""), float(_field(ours[i], "z_score") or 0.0), max_z)
            if i < len(ours) else _empty_cell("l")
        )
        right = (
            _tug_cell("r", str(_field(theirs[i], "term") or ""), float(_field(theirs[i], "z_score") or 0.0), max_z)
            if i < len(theirs) else _empty_cell("r")
        )
        rows_html.append(f'<div class="mirror-band__row">{left}{right}</div>')

    left_head = f"← {escape(team_name)} fans, on {escape(rival_name)}"
    right_head = f"{escape(rival_name)} fans, on {escape(team_name)} →"
    asym_html = ""
    if left_sparse:
        asym_html = (
            f'<div class="mirror-band__asym mirror-band__asym--l">'
            f'{escape(sparse_line.format(who=rival_name))}</div>'
        )
    elif right_sparse:
        asym_html = (
            f'<div class="mirror-band__asym mirror-band__asym--r">'
            f'{escape(sparse_line.format(who=team_name))}</div>'
        )

    # Receipt: prefer the higher-z side's top quote.
    receipt_html = ""
    candidates: list[Any] = []
    left_top_z = float(_field(ours[0], "z_score") or 0.0) if ours else -1.0
    right_top_z = float(_field(theirs[0], "z_score") or 0.0) if theirs else -1.0
    ordered = (theirs + ours) if right_top_z >= left_top_z else (ours + theirs)
    for row in ordered:
        if _field(row, "sample_quote"):
            candidates.append(row)
            break
    if candidates:
        q_row = candidates[0]
        quote = escape(str(_field(q_row, "sample_quote") or ""))
        source = escape(str(_field(q_row, "sample_quote_source") or "fan post"))
        receipt_html = (
            f'<div class="mirror-band__receipt">'
            f'<p class="mirror-band__quote">&ldquo;{quote}&rdquo;</p>'
            f'<div class="mirror-band__prov">{source} · fan post, verbatim</div>'
            f'</div>'
        )

    # Volume disclosure — only sides with measured rows. A side with no
    # surviving terms has UNKNOWN volume (the engine writes volume on term
    # rows), and "0 posts mention them" would contradict the asymmetry line.
    vol_parts = []
    if their_docs > 0:
        vol_parts.append(f"{their_docs:,} {escape(rival_name)} fan posts mention us")
    if our_docs > 0:
        vol_parts.append(f"{our_docs:,} {escape(team_name)} fan posts mention them")
    vol_line = " · ".join(vol_parts)

    return f"""
<section class="mirror-band" aria-label="The Rivalry Mirror" style="--mirror-l:{left_color};--mirror-r:{right_color}">
  <div class="mirror-band__inner">
    <div class="mirror-band__head">
      <span class="mirror-band__eyebrow">The Rivalry Mirror</span>
      <span class="mirror-band__season">{season} season</span>
    </div>
    <div class="mirror-band__tape">
      <div class="mirror-band__name mirror-band__name--l">{escape(team_name)}</div>
      <div class="mirror-band__x">×</div>
      <div class="mirror-band__name mirror-band__name--r">{escape(rival_name)}</div>
    </div>
    <div class="mirror-band__sub">{vol_line}</div>
    <div class="mirror-band__tug">
      <div class="mirror-band__tug-head"><div>{left_head}</div><div>{right_head}</div></div>
      {"".join(rows_html)}
    </div>
    {asym_html}
    {receipt_html}
    <div class="mirror-band__foot">rival-mention windows, weighted log-odds · printed z is the truth — geometry only dramatizes it</div>
  </div>
</section>"""


MIRROR_MODULE_CSS = f"""
/* Rivalry Mirror night band (Group Chat Noir, Language Layer Wave 2) */
.mirror-band {{
  margin: clamp(20px, 3vw, 32px) 0; border-radius: 16px;
  background: {GROUND}; border: 1px solid {HAIRLINE}; overflow: hidden;
}}
.mirror-band__inner {{ padding: clamp(18px, 2.6vw, 30px) clamp(18px, 2.8vw, 32px); }}
.mirror-band__head {{
  display: flex; align-items: baseline; justify-content: space-between;
  gap: 12px; flex-wrap: wrap; margin-bottom: 8px;
}}
.mirror-band__eyebrow {{
  font-family: {_MONO_STACK}; font-size: 12px; font-weight: 500;
  letter-spacing: .14em; text-transform: uppercase; color: {RECEIPT};
}}
.mirror-band__season {{
  font-family: {_MONO_STACK}; font-size: 11px; color: {RECEIPT};
  font-variant-numeric: tabular-nums;
}}
.mirror-band__tape {{
  display: grid; grid-template-columns: 1fr 56px 1fr; align-items: center;
  padding: 14px 0 8px; gap: 6px;
}}
.mirror-band__name {{
  font-family: {_DISPLAY_STACK}; text-transform: uppercase; line-height: .95;
  letter-spacing: .01em; font-size: clamp(24px, 5vw, 44px);
}}
.mirror-band__name--l {{ text-align: right; color: var(--mirror-l, {CHALK}); }}
.mirror-band__name--r {{ text-align: left; color: var(--mirror-r, {CHALK}); }}
.mirror-band__x {{
  font-family: {_DISPLAY_STACK}; font-size: clamp(18px, 3.6vw, 30px);
  color: {RECEIPT}; text-align: center;
}}
.mirror-band__sub {{
  text-align: center; font-family: {_MONO_STACK}; font-size: 10.5px;
  color: {RECEIPT}; letter-spacing: .10em; text-transform: uppercase;
  padding: 0 0 16px; font-variant-numeric: tabular-nums;
}}
.mirror-band__tug {{ padding: 6px 0; }}
.mirror-band__tug-head {{
  display: grid; grid-template-columns: 1fr 1fr; padding: 0 0 10px; gap: 12px;
}}
.mirror-band__tug-head div {{
  font-family: {_MONO_STACK}; font-size: 10px; letter-spacing: .10em;
  text-transform: uppercase; color: {RECEIPT};
}}
.mirror-band__tug-head div:last-child {{ text-align: right; }}
.mirror-band__row {{
  display: grid; grid-template-columns: 1fr 1fr; align-items: center; min-height: 30px;
}}
.mirror-band__cell {{ position: relative; height: 24px; }}
.mirror-band__spine {{
  position: absolute; top: -4px; bottom: -4px; width: 1px;
  background: rgba(237, 230, 214, 0.18);
}}
.mirror-band__cell--l .mirror-band__spine {{ right: 0; }}
.mirror-band__cell--r .mirror-band__spine {{ left: 0; }}
.mirror-band__stem {{
  position: absolute; top: 50%; height: 2px; transform: translateY(-50%);
}}
.mirror-band__cell--l .mirror-band__stem {{
  right: 0;
  background: linear-gradient(270deg, color-mix(in srgb, var(--mirror-l, {CHALK}) 60%, transparent), color-mix(in srgb, var(--mirror-l, {CHALK}) 10%, transparent));
}}
.mirror-band__cell--r .mirror-band__stem {{
  left: 0;
  background: linear-gradient(90deg, color-mix(in srgb, var(--mirror-r, {CHALK}) 60%, transparent), color-mix(in srgb, var(--mirror-r, {CHALK}) 10%, transparent));
}}
.mirror-band__tdot {{
  position: absolute; top: 50%; transform: translate(-50%, -50%);
  width: 11px; height: 11px; border-radius: 50%; border: 2px solid {GROUND};
}}
.mirror-band__cell--l .mirror-band__tdot {{ background: var(--mirror-l, {CHALK}); }}
.mirror-band__cell--r .mirror-band__tdot {{ background: var(--mirror-r, {CHALK}); }}
.mirror-band__tlabel {{
  position: absolute; top: 50%; transform: translateY(-50%);
  font-size: 12.5px; font-weight: 600; white-space: nowrap; color: {CHALK};
  background: {SURFACE}; padding: 0 6px; border-radius: 3px;
}}
.mirror-band__tz {{
  font-family: {_MONO_STACK}; font-size: 9.5px; color: {RECEIPT};
  font-weight: 400; margin-left: 6px; font-variant-numeric: tabular-nums;
}}
.mirror-band__asym {{
  font-family: {_MONO_STACK}; font-size: 11px; color: {RECEIPT};
  padding: 10px 0 4px; letter-spacing: .04em;
}}
.mirror-band__asym--l {{ text-align: left; }}
.mirror-band__asym--r {{ text-align: right; }}
.mirror-band__receipt {{
  border-top: 1px dashed {HAIRLINE}; margin-top: 14px; padding-top: 12px;
}}
.mirror-band__quote {{
  font-family: var(--font-serif, 'Source Serif Pro', Georgia, serif);
  font-size: 15px; line-height: 1.55; color: {CHALK}; margin: 0;
}}
.mirror-band__prov {{
  font-family: {_MONO_STACK}; font-size: 10.5px; letter-spacing: .08em;
  text-transform: uppercase; color: {RECEIPT}; margin-top: 8px;
}}
.mirror-band__foot {{
  font-family: {_MONO_STACK}; font-size: 10px; color: {RECEIPT}; margin-top: 14px;
  letter-spacing: .06em;
}}
@media (max-width: 540px) {{
  .mirror-band__tlabel {{ font-size: 11px; }}
  .mirror-band__tug-head div {{ font-size: 9px; }}
}}
"""


__all__ = ["render_mirror", "MIRROR_MODULE_CSS"]
