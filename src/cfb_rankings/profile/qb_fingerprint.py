"""QB Fingerprint hero — Sprint A from WORLD_CLASS_GAP_AUDIT_2026_05_22.

Replaces the generic ``profile-identity-v2`` 4-tile strip on QB pages
with the 5-cell vibe-read hero described in
``PLAYER_PAGE_WORLD_CLASS_BRIEF.md §4.1``. Three-column desktop, single
column mobile.

Brief grammar (verbatim from §3 #4):
    Eyebrow → Number → Narrative
    "12px uppercase eyebrow ('Heisman Heat' / 'Fan Belief' / 'vs.
     Pressure'), big display-font number (Bebas Neue), one 14px
     sentence of plain-English read."

The five cells:
    1. CFB Index QB Score (0-100 composite)
    2. Heisman Heat       (current rank + ballot/finalist/win prob)
    3. Fan Belief         (Belief Dial + archetype, or 'Awaiting' if
                           the player-FI corpus is below floor)
    4. Respect Gap        (fan score - national score, signed)
    5. Reality Gap        (fan belief vs structural percentile)

Right column: accolade ribbon with top 3 live accolades (Heisman /
Davey O'Brien / Consensus All-American for QB).

Background: subtle diagonal gradient tinted in --team-accent at 6%.

Mobile: vertical stack; the five vibe cells become a horizontal
snap-scroll; accolade ribbon becomes a 3-chip row above the first fold.

Public API:
    render_qb_fingerprint_hero(...) -> str  # the HTML block
    QB_FINGERPRINT_CSS_BLOCK        -> str  # one-time site-CSS block

The caller in reporting.py inlines the CSS block via _site_css() and
invokes the hero renderer in place of render_profile_identity_strip_v2.
"""
from __future__ import annotations

from html import escape
from typing import Any


# ---------------------------------------------------------------------------
# CSS block (inlined once via _site_css in reporting.py)
# ---------------------------------------------------------------------------

QB_FINGERPRINT_CSS_BLOCK = """
/* QB Fingerprint hero — Sprint A
 * PLAYER_PAGE_WORLD_CLASS_BRIEF.md §4.1
 *
 * Custom properties consumed (set by enclosing .team-shell):
 *   --team-accent       primary brand color
 *   --team-accent-soft  secondary brand color
 *
 * Layout:
 *   Desktop  ≥860px: 3-column grid [identity | fingerprint | accolades]
 *   Tablet   <860px: stacked. Fingerprint cells become snap-scroll row.
 *   Mobile   <540px: snap-scroll cells single-line, accolade chips inline.
 *
 * Every number is tabular-nums + Bebas Neue at hero scale.
 */

.qb-fingerprint {
  --qb-accent:        var(--team-accent, #c9a24a);
  --qb-accent-soft:   var(--team-accent-soft, #c9a24a);
  --qb-bg-card:       rgba(255, 255, 255, 0.02);
  --qb-stroke:        rgba(255, 255, 255, 0.08);
  --qb-fg-primary:    var(--fg-primary, #1a1a1a);
  --qb-fg-secondary:  var(--fg-secondary, #4a4a4a);
  --qb-fg-muted:      var(--fg-muted, #6f6f6f);

  position: relative;
  display: grid;
  grid-template-columns: minmax(220px, 280px) 1fr minmax(180px, 260px);
  gap: clamp(20px, 2.4vw, 32px);
  padding: clamp(24px, 3vw, 40px) clamp(20px, 2.6vw, 36px);
  border-left: 6px solid var(--qb-accent);
  border-bottom: 1px solid var(--qb-stroke);
  background:
    linear-gradient(
      135deg,
      color-mix(in oklab, var(--qb-accent) 7%, transparent) 0%,
      color-mix(in oklab, var(--qb-accent-soft) 5%, transparent) 55%,
      transparent 100%
    );
  margin-bottom: clamp(20px, 3vw, 32px);
  overflow: hidden;
}

@media (max-width: 860px) {
  .qb-fingerprint { grid-template-columns: 1fr; }
}

/* === Left column: identity === */

.qb-fingerprint__identity {
  display: flex;
  flex-direction: column;
  gap: clamp(10px, 1.2vw, 16px);
  min-width: 0;
}

.qb-fingerprint__team-mark {
  width: clamp(64px, 6vw, 88px);
  height: clamp(64px, 6vw, 88px);
  border-radius: 12px;
  background: var(--qb-accent);
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: 'Bebas Neue', 'Inter Display', 'Inter', system-ui, sans-serif;
  font-size: clamp(26px, 2.4vw + 10px, 36px);
  font-weight: 400;
  letter-spacing: 0.02em;
  flex-shrink: 0;
  overflow: hidden;
}
.qb-fingerprint__team-mark img,
.qb-fingerprint__team-mark svg {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.qb-fingerprint__eyebrow {
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--qb-fg-muted);
  margin: 0;
}

.qb-fingerprint__name {
  font-family: 'Bebas Neue', 'Inter Display', 'Inter', system-ui, sans-serif;
  font-size: clamp(36px, 3.6vw + 14px, 64px);
  font-weight: 400;
  line-height: 0.95;
  letter-spacing: 0.006em;
  text-transform: uppercase;
  color: var(--qb-fg-primary);
  margin: 0;
}

.qb-fingerprint__sub-meta {
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 13px;
  color: var(--qb-fg-secondary);
  margin: 0;
}

.qb-fingerprint__facts {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 10px;
  margin: 0;
  padding: 0;
  list-style: none;
}
.qb-fingerprint__fact {
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--qb-fg-secondary);
  padding: 4px 10px;
  background: var(--qb-bg-card);
  border: 1px solid var(--qb-stroke);
  border-radius: 999px;
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
}

/* === Middle column: 5 vibe cells === */

.qb-fingerprint__cells {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 8px;
  align-content: start;
  min-width: 0;
}

@media (max-width: 1180px) {
  .qb-fingerprint__cells {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .qb-fingerprint__cells {
    display: flex;
    flex-wrap: nowrap;
    overflow-x: auto;
    scroll-snap-type: x mandatory;
    gap: 10px;
    margin: 0 calc(-1 * clamp(20px, 2.6vw, 36px));
    padding: 0 clamp(20px, 2.6vw, 36px);
    scrollbar-width: none;
  }
  .qb-fingerprint__cells::-webkit-scrollbar { display: none; }
  .qb-fingerprint__cell {
    flex: 0 0 70%;
    min-width: 220px;
    scroll-snap-align: start;
  }
}

.qb-fingerprint__cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: clamp(10px, 1vw, 14px) clamp(10px, 1vw, 14px);
  background: var(--qb-bg-card);
  border: 1px solid var(--qb-stroke);
  border-radius: 10px;
  min-width: 0;
  font-variant-numeric: tabular-nums;
}

.qb-fingerprint__cell-eyebrow {
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--qb-fg-muted);
  margin: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.qb-fingerprint__cell-value {
  font-family: 'Bebas Neue', 'Inter Display', 'Inter', system-ui, sans-serif;
  font-size: clamp(30px, 2.6vw + 14px, 46px);
  font-weight: 400;
  line-height: 1;
  letter-spacing: 0.01em;
  color: var(--qb-fg-primary);
  margin: 0;
}

.qb-fingerprint__cell-narrative {
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 13px;
  line-height: 1.35;
  color: var(--qb-fg-secondary);
  margin: 0;
}

.qb-fingerprint__spark {
  display: block;
  width: 100%;
  height: 20px;
  color: var(--qb-accent);
  margin: 4px 0 2px;
}

.qb-fingerprint__cell-value--awaiting {
  color: var(--qb-fg-muted);
  font-size: clamp(20px, 1.6vw + 10px, 28px);
  letter-spacing: 0.04em;
}
.qb-fingerprint__cell-value--gap-pos { color: #3ea073; }
.qb-fingerprint__cell-value--gap-neg { color: #c04a4a; }
.qb-fingerprint__cell-value--gap-zero { color: var(--qb-fg-secondary); }

/* === Right column: accolade ribbon === */

.qb-fingerprint__accolades {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
}

.qb-fingerprint__accolade {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 6px 12px;
  align-items: baseline;
  padding: 10px 14px;
  background: color-mix(in oklab, var(--qb-accent) 8%, transparent);
  border: 1px solid color-mix(in oklab, var(--qb-accent) 30%, transparent);
  border-radius: 10px;
  font-variant-numeric: tabular-nums;
}

.qb-fingerprint__accolade-eyebrow {
  grid-column: 1 / -1;
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--qb-fg-muted);
  margin: 0;
}
.qb-fingerprint__accolade-label {
  font-family: 'Source Serif Pro', Georgia, serif;
  font-size: 15px;
  font-weight: 600;
  color: var(--qb-fg-primary);
  margin: 0;
  line-height: 1.2;
}
.qb-fingerprint__accolade-value {
  font-family: 'Bebas Neue', 'Inter Display', 'Inter', system-ui, sans-serif;
  font-size: 22px;
  color: var(--qb-accent);
  line-height: 1;
  letter-spacing: 0.01em;
}

@media (max-width: 860px) {
  .qb-fingerprint__accolades {
    flex-direction: row;
    flex-wrap: wrap;
    gap: 6px;
  }
  /* Override desktop's 2-column grid layout — at ~33% width the label
   * column collides with the value column, causing the overlap users
   * saw on Mendoza's page (Heisman over 14.3%, Consensus over
   * All-American). Mobile uses a vertical stack: eyebrow → label →
   * value. */
  .qb-fingerprint__accolade {
    flex: 1 1 calc(33% - 6px);
    padding: 8px 10px;
    display: flex;
    flex-direction: column;
    gap: 2px;
    align-items: flex-start;
  }
  .qb-fingerprint__accolade-eyebrow { grid-column: auto; }
  .qb-fingerprint__accolade-label { font-size: 13px; line-height: 1.25; }
  .qb-fingerprint__accolade-value { font-size: 18px; line-height: 1.1; }
}
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _signed_int(v: Any) -> str | None:
    try:
        i = int(float(v))
    except (TypeError, ValueError):
        return None
    return f"+{i}" if i > 0 else (str(i) if i < 0 else "0")


def _pct(v: Any) -> str | None:
    """Format a probability as a percentage string.

    Accepts 0..1 (probability) or 0..100 (already-percentage) and emits
    "14.3%" / "14%" / "<1%". Previously this used a broken rstrip chain
    that always concatenated a second "%" (producing "14.3%%") because
    the conditional check ran against the unsuffixed format string.
    """
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if f <= 1.0 + 1e-9:
        f *= 100.0
    if f < 0.05:
        return "<1%"
    # Drop the decimal when value is a whole number; otherwise 1 decimal.
    if abs(f - round(f)) < 0.05:
        return f"{int(round(f))}%"
    return f"{f:.1f}%"


def _rank_text(v: Any) -> str | None:
    try:
        n = int(float(v))
    except (TypeError, ValueError):
        return None
    return f"#{n}"


def _sparkline_svg(points: list[float], *, width: int = 100, height: int = 20) -> str:
    """Render a tiny SVG sparkline. Returns "" when <2 points.

    Brief §3 #3 — Trajectory Spark primitive: 160x40 desktop, smaller
    on the cell scale. Dotted baseline = start of season, solid line =
    current.
    """
    pts: list[float] = []
    for p in points:
        try:
            pts.append(float(p))
        except (TypeError, ValueError):
            continue
    if len(pts) < 2:
        return ""
    pmin = min(pts)
    pmax = max(pts)
    span = pmax - pmin if pmax > pmin else 1.0
    n = len(pts)
    coords: list[str] = []
    for i, v in enumerate(pts):
        x = (i / max(1, n - 1)) * (width - 2) + 1
        # Higher value = lower y (top of svg)
        y = height - (((v - pmin) / span) * (height - 2) + 1)
        coords.append(f"{x:.1f},{y:.1f}")
    path_d = "M " + " L ".join(coords)
    last_x, last_y = coords[-1].split(",")
    baseline_y = height - 1
    return (
        f'<svg class="qb-fingerprint__spark" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}" aria-hidden="true" preserveAspectRatio="none">'
        f'<line x1="1" y1="{baseline_y}" x2="{width-1}" y2="{baseline_y}" '
        f'stroke="currentColor" stroke-width="1" stroke-dasharray="2 2" opacity="0.25"/>'
        f'<polyline points="{" ".join(coords)}" fill="none" '
        f'stroke="currentColor" stroke-width="1.5" stroke-linejoin="round" stroke-linecap="round"/>'
        f'<circle cx="{last_x}" cy="{last_y}" r="2" fill="currentColor"/>'
        '</svg>'
    )


def _cell(
    eyebrow: str,
    value: str | None,
    narrative: str | None = "",
    *,
    value_class: str | None = None,
    awaiting: bool = False,
    sparkline: list[float] | None = None,
) -> str:
    """Render one of the 5 vibe cells.

    `awaiting=True` displays a small italicized 'Awaiting Signal' that
    matches the brief's honest-empty-state rule (§8.8).

    `sparkline` if provided renders a tiny SVG trajectory above the
    narrative (brief §3 #3 Trajectory Spark primitive).
    """
    eyebrow_html = escape(eyebrow)
    if awaiting or not value:
        value_html = "Awaiting"
        cls = "qb-fingerprint__cell-value qb-fingerprint__cell-value--awaiting"
    else:
        value_html = escape(str(value))
        cls = "qb-fingerprint__cell-value"
        if value_class:
            cls = f"{cls} {value_class}"
    narrative_html = escape(narrative or "")
    narrative_block = (
        f'<p class="qb-fingerprint__cell-narrative">{narrative_html}</p>'
        if narrative_html else ""
    )
    spark_block = _sparkline_svg(sparkline) if sparkline else ""
    return (
        '<article class="qb-fingerprint__cell">'
        f'<p class="qb-fingerprint__cell-eyebrow">{eyebrow_html}</p>'
        f'<p class="{cls}">{value_html}</p>'
        f'{spark_block}'
        f'{narrative_block}'
        '</article>'
    )


def _accolade(eyebrow: str, label: str, value: str | None) -> str:
    value_html = escape(value or "—")
    return (
        '<article class="qb-fingerprint__accolade">'
        f'<p class="qb-fingerprint__accolade-eyebrow">{escape(eyebrow)}</p>'
        f'<p class="qb-fingerprint__accolade-label">{escape(label)}</p>'
        f'<p class="qb-fingerprint__accolade-value">{value_html}</p>'
        '</article>'
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_POSITION_TOP_AWARD = {
    "QB":   ("TOP QB AWARD",     "Davey O'Brien"),
    "RB":   ("TOP RB AWARD",     "Doak Walker"),
    "TB":   ("TOP RB AWARD",     "Doak Walker"),
    "FB":   ("TOP RB AWARD",     "Doak Walker"),
    "WR":   ("TOP WR AWARD",     "Biletnikoff"),
    "TE":   ("TOP TE AWARD",     "Mackey"),
    "DE":   ("TOP DEFENSE AWARD","Nagurski"),
    "EDGE": ("TOP DEFENSE AWARD","Nagurski"),
    "DT":   ("TOP DEFENSE AWARD","Nagurski"),
    "DL":   ("TOP DEFENSE AWARD","Nagurski"),
    "NT":   ("TOP DEFENSE AWARD","Nagurski"),
    "LB":   ("TOP LB AWARD",     "Butkus"),
    "ILB":  ("TOP LB AWARD",     "Butkus"),
    "OLB":  ("TOP LB AWARD",     "Butkus"),
    "MLB":  ("TOP LB AWARD",     "Butkus"),
    "CB":   ("TOP DB AWARD",     "Jim Thorpe"),
    "S":    ("TOP DB AWARD",     "Jim Thorpe"),
    "DB":   ("TOP DB AWARD",     "Jim Thorpe"),
    "OT":   ("TOP OL AWARD",     "Outland"),
    "OG":   ("TOP OL AWARD",     "Outland"),
    "OL":   ("TOP OL AWARD",     "Outland"),
    "IOL":  ("TOP OL AWARD",     "Outland"),
    "C":    ("TOP OL AWARD",     "Rimington"),
    "K":    ("TOP K AWARD",      "Lou Groza"),
    "PK":   ("TOP K AWARD",      "Lou Groza"),
    "P":    ("TOP P AWARD",      "Ray Guy"),
    "ATH":  ("TOP AWARD",        "Position award"),
}


def render_qb_fingerprint_hero(
    *,
    player_name: str,
    eyebrow: str,
    team_mark_html: str,
    facts: list[str],
    sub_meta: str = "",
    current_snapshot: dict[str, Any] | None = None,
    signature_story: dict[str, Any] | None = None,
    the_room: dict[str, Any] | None = None,
    cohort_divergence: dict[str, Any] | None = None,
    cfb_index_score: dict[str, Any] | None = None,
    position: str = "",
    aria_label: str = "",
) -> str:
    """Render the QB Fingerprint hero block.

    Pulls vibe-cell values from the existing player_data structures the
    legacy renderer already computes. Where a value is missing, the cell
    degrades to an 'Awaiting' state per the brief's empty-state rule.
    """
    current_snapshot = current_snapshot or {}
    signature_story = signature_story or {}
    the_room = the_room or {}
    cohort_divergence = cohort_divergence or {}
    # cohort_divergence can be a dataclass (bets.cohort_divergence.
    # CohortDivergenceMap) or a dict. Normalize to dict access.
    def _cd_get(key: str) -> Any:
        if isinstance(cohort_divergence, dict):
            return cohort_divergence.get(key)
        return getattr(cohort_divergence, key, None)

    # === Cell 1: CFB Index QB Score (composite 0-100) ===
    # Source priority: cfb_index_score payload (Wave 1c composite), then
    # signature_story.percentile, then None ("Awaiting").
    qb_score = None
    qb_score_narr = ""
    cis = cfb_index_score or {}
    if cis and cis.get("score") is not None:
        try:
            qb_score = f"{int(round(float(cis['score'])))}"
            qb_score_narr = str(cis.get("narrative") or "")
        except (TypeError, ValueError):
            qb_score = None
    if qb_score is None:
        pct = signature_story.get("percentile")
        if pct is not None:
            try:
                pct_f = float(pct)
                if pct_f <= 1.0 + 1e-9:
                    pct_f *= 100.0
                qb_score = f"{int(round(pct_f))}"
                qb_score_narr = (
                    f"{signature_story.get('metric_label') or 'Headline metric'} "
                    f"at the {int(round(pct_f))}th percentile."
                )
            except (TypeError, ValueError):
                pass
    # Score label uses the position-aware composite name when supplied.
    score_label = "CFB Index Score" if cis else "CFB Index QB Score"
    cell_score = _cell(score_label, qb_score, qb_score_narr,
                       awaiting=qb_score is None)

    # === Cell 2: Heisman Heat ===
    nowcast_rank = _rank_text(current_snapshot.get("nowcast_rank"))
    win_prob = _pct(current_snapshot.get("win_probability"))
    # Trajectory: try the snapshot's weekly_history if present
    heisman_trajectory: list[float] | None = None
    weekly = current_snapshot.get("weekly_history") or current_snapshot.get("nowcast_history")
    if isinstance(weekly, list) and weekly:
        # Could be [{"rank":n}, ...] or [rank, ...]; invert ranks so higher
        # on the sparkline = better Heisman position.
        ranks: list[float] = []
        for w in weekly[-8:]:
            r = w.get("rank") if isinstance(w, dict) else w
            try:
                ranks.append(-float(r))
            except (TypeError, ValueError):
                pass
        if len(ranks) >= 2:
            heisman_trajectory = ranks
    if nowcast_rank:
        narr_bits: list[str] = []
        if win_prob:
            narr_bits.append(f"{win_prob} win probability")
        finalist_prob = _pct(current_snapshot.get("finalist_probability"))
        if finalist_prob and not win_prob:
            narr_bits.append(f"{finalist_prob} to make the finalist tier")
        heisman_narr = "; ".join(narr_bits) if narr_bits else "Live model ranking."
        cell_heisman = _cell("Heisman Heat", nowcast_rank, heisman_narr,
                             sparkline=heisman_trajectory)
    else:
        cell_heisman = _cell("Heisman Heat", None,
                             "Not on the live Heisman board this week.",
                             awaiting=True)

    # === Cell 3: Fan Belief ===
    belief_score = the_room.get("belief_score")
    belief_archetype = the_room.get("archetype")
    if belief_score is not None:
        try:
            bs = float(belief_score)
            sign = "+" if bs > 0 else ""
            belief_val = f"{sign}{bs:.2f}"
            belief_narr = (
                belief_archetype if belief_archetype
                else "Fan-corpus belief score."
            )
            cell_belief = _cell("Fan Belief", belief_val, belief_narr)
        except (TypeError, ValueError):
            cell_belief = _cell("Fan Belief", None,
                                "Player-specific belief corpus not yet built.",
                                awaiting=True)
    else:
        cell_belief = _cell(
            "Fan Belief", None,
            "Player-specific FI not yet ingested. Falls back to team mood below.",
            awaiting=True,
        )

    # === Cell 4: Respect Gap (fan score - national score) ===
    respect_gap = _cd_get("respect_gap")
    if respect_gap is None and signature_story.get("respect_gap") is not None:
        respect_gap = signature_story.get("respect_gap")
    if respect_gap is not None:
        try:
            rg = float(respect_gap)
            value_class = (
                "qb-fingerprint__cell-value--gap-pos" if rg > 0
                else ("qb-fingerprint__cell-value--gap-neg" if rg < 0
                      else "qb-fingerprint__cell-value--gap-zero")
            )
            cell_respect = _cell(
                "Respect Gap",
                _signed_int(rg),
                "Fan score minus national score.",
                value_class=value_class,
            )
        except (TypeError, ValueError):
            cell_respect = _cell("Respect Gap", None,
                                 "Coming online with player-level FI.",
                                 awaiting=True)
    else:
        cell_respect = _cell(
            "Respect Gap", None,
            "Coming online with player-level FI.",
            awaiting=True,
        )

    # === Cell 5: Reality Gap (belief vs structural percentile) ===
    reality_gap = _cd_get("reality_gap")
    if reality_gap is None and signature_story.get("reality_gap") is not None:
        reality_gap = signature_story.get("reality_gap")
    if reality_gap is not None:
        try:
            rg = float(reality_gap)
            value_class = (
                "qb-fingerprint__cell-value--gap-pos" if rg > 0
                else ("qb-fingerprint__cell-value--gap-neg" if rg < 0
                      else "qb-fingerprint__cell-value--gap-zero")
            )
            cell_reality = _cell(
                "Reality Gap",
                _signed_int(rg),
                "Belief minus structural percentile.",
                value_class=value_class,
            )
        except (TypeError, ValueError):
            cell_reality = _cell("Reality Gap", None,
                                 "Coming online with player-level FI.",
                                 awaiting=True)
    else:
        cell_reality = _cell(
            "Reality Gap", None,
            "Coming online with player-level FI.",
            awaiting=True,
        )

    cells_html = "\n".join([
        cell_score, cell_heisman, cell_belief, cell_respect, cell_reality
    ])

    # === Accolade ribbon (right column) — 3 cards ===
    heisman_win = _pct(current_snapshot.get("win_probability"))
    heisman_finalist = _pct(current_snapshot.get("finalist_probability"))
    heisman_ballot = _pct(current_snapshot.get("any_ballot_probability"))

    # Davey O'Brien: per-award model isn't built yet. If the player is in
    # the top 10 of the Heisman nowcast we can show a derived "in
    # consideration" pill — honest empty otherwise.
    davey_value: str | None = None
    try:
        rk = current_snapshot.get("nowcast_rank")
        if rk is not None and int(rk) <= 10:
            davey_value = "In contention"
    except (TypeError, ValueError):
        pass

    # Consensus All-American: derived signal from honors history's
    # all-american flag, if present anywhere.
    consensus_value: str | None = None  # placeholder — wired from
    # honors_history in caller when available

    # Position-aware top award label for cell #2.
    _pos_key = (position or "").upper().strip()
    top_eyebrow, top_award = _POSITION_TOP_AWARD.get(
        _pos_key, ("TOP POSITION AWARD", "Position award")
    )

    accolades_html = "\n".join([
        _accolade(
            "ACCOLADE PROBABILITY",
            "Heisman",
            heisman_win or heisman_finalist or heisman_ballot or None,
        ),
        _accolade(
            top_eyebrow,
            top_award,
            davey_value,
        ),
        _accolade(
            "CONSENSUS",
            "All-American",
            consensus_value,
        ),
    ])

    # === Identity column ===
    fact_chips = "".join(
        f'<li class="qb-fingerprint__fact">{escape(str(f))}</li>'
        for f in facts if str(f or "").strip() and str(f or "").strip() != "--"
    )
    facts_block = (
        f'<ul class="qb-fingerprint__facts">{fact_chips}</ul>'
        if fact_chips else ""
    )

    sub_meta_block = (
        f'<p class="qb-fingerprint__sub-meta">{escape(sub_meta)}</p>'
        if sub_meta else ""
    )

    aria_attr = f' aria-label="{escape(aria_label)}"' if aria_label else ""

    return f"""
<section class="qb-fingerprint"{aria_attr}>
  <div class="qb-fingerprint__identity">
    <div class="qb-fingerprint__team-mark" aria-hidden="true">{team_mark_html}</div>
    <p class="qb-fingerprint__eyebrow">{escape(eyebrow)}</p>
    <h1 class="qb-fingerprint__name">{escape(player_name)}</h1>
    {sub_meta_block}
    {facts_block}
  </div>
  <div class="qb-fingerprint__cells">
    {cells_html}
  </div>
  <div class="qb-fingerprint__accolades">
    {accolades_html}
  </div>
</section>
"""


__all__ = [
    "render_qb_fingerprint_hero",
    "QB_FINGERPRINT_CSS_BLOCK",
]
