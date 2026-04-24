"""Savant Card renderer — 13 percentile bars with four-peer-set toggle.

Spec: ``docs/design-system/12-modules-intel.md`` §SavantCard.

Output is a single ``<section class="savant-card">`` fragment composed of:

1. Narrative header (LLM-written one-sentence summary, fallback to
   deterministic "band-summary" if no narrative cached).
2. Peer-set toggle chips (FBS / Power-4 / Conference / Program 2014+).
3. Offense section — 5 bars, best-to-concern ordering.
4. Defense section — 5 bars, already inverted (higher pct = elite defense).
5. Special-situations section — 3 bars.
6. Echo callout inside defense section when cached.
7. Source attribution footer.

Peer-set swap is CSS-custom-property-driven, with four percentile values
baked into each bar as data-attributes. Tiny inline JS (~25 LOC) rewrites
``--pct-fill`` when a chip is clicked. No chart library. No client-side
computation. No flicker.
"""
from __future__ import annotations

import html
import json
from typing import Any

from .profile_loader import Profile


_PEER_SETS: tuple[tuple[str, str, str], ...] = (
    # (key, short_label, data_attr_suffix)
    ("fbs",     "FBS",            "fbs"),
    ("p4",      "Power-4",        "p4"),
    ("conf",    "Conference",     "conf"),
    ("alltime", "Program 2014+",  "alltime"),
)


def render_savant_card(
    profile: Profile,
    rows: list[dict[str, Any]],
    *,
    narrative: str | None = None,
    echo: dict[str, Any] | None = None,
    season_year: int,
) -> str:
    """Render the Savant Card HTML fragment.

    ``rows`` is the output of ``data.fetch_savant_rows`` — already ordered
    offense → defense → special. Empty list returns "" so the card is
    simply omitted from the page rather than showing an empty frame.
    """
    if not rows:
        return ""

    narrative_html = _render_narrative(narrative, rows, profile)
    toggle_html = _render_toggle()
    offense = [r for r in rows if r["metric_group"] == "offense"]
    defense = [r for r in rows if r["metric_group"] == "defense"]
    special = [r for r in rows if r["metric_group"] == "special"]

    offense_html = _render_section("offense · strengths lead", offense, None)
    defense_html = _render_section(
        "defense · higher bar = harder to play against",
        defense,
        _render_echo(echo) if echo else None,
    )
    special_html = _render_section(
        "hidden math · special situations",
        special,
        None,
    )
    legend_html = _render_legend()
    sample_size = rows[0].get("sample_size") or 0
    peer_fbs = rows[0].get("peer_set_size_fbs") or 0

    return f"""<section class="savant-card" aria-labelledby="savant-title">
  <header class="savant-card__header">
    <span class="savant-card__eyebrow">THE SAVANT CARD · {html.escape(profile.program_name)} · {season_year}</span>
    {toggle_html}
  </header>
  {narrative_html}
  {offense_html}
  {defense_html}
  {special_html}
  {legend_html}
  <footer class="savant-card__source">
    <span>Sources · CFBD tier-2 advanced stats · opponent-adjusted · {sample_size} games this season · percentiles vs. up to {peer_fbs} FBS peers</span>
  </footer>
</section>
{_SAVANT_TOGGLE_JS}
"""


# ------------------------------------------------------------------------
# Sub-renderers
# ------------------------------------------------------------------------

def _render_narrative(narrative: str | None, rows: list[dict[str, Any]], profile: Profile) -> str:
    if narrative:
        return f'<p class="savant-card__narrative">{html.escape(narrative)}</p>'
    # Deterministic fallback — read the four highest and lowest FBS-percentile
    # metrics and describe the shape in one on-voice sentence.
    with_pct = [(r["metric_label"], r["pct_vs_fbs"]) for r in rows if r.get("pct_vs_fbs") is not None]
    if not with_pct:
        return ""
    ranked = sorted(with_pct, key=lambda x: -x[1])
    top = ranked[:2]
    bottom = ranked[-1]
    top_txt = " and ".join(f"{lbl.lower()} (top {100 - int(p):d}%)" for lbl, p in top)
    bot_lbl, bot_p = bottom
    crux = f"the crux lives in {bot_lbl.lower()}, where {profile.program_name} sits at the {int(bot_p):d}th percentile."
    text = f"{profile.program_name} reads strongest in {top_txt}; {crux}"
    return f'<p class="savant-card__narrative savant-card__narrative--fallback">{html.escape(text)}</p>'


def _render_toggle() -> str:
    chips = []
    for i, (key, label, _) in enumerate(_PEER_SETS):
        cls = "savant-card__chip"
        if i == 0:
            cls += " savant-card__chip--active"
        chips.append(
            f'<button type="button" class="{cls}" data-peer="{key}" aria-pressed="{"true" if i == 0 else "false"}">{html.escape(label)}</button>'
        )
    return f'<div class="savant-card__toggle" role="tablist" aria-label="Peer set">{"".join(chips)}</div>'


def _render_section(
    eyebrow: str,
    metric_rows: list[dict[str, Any]],
    extra_html: str | None,
) -> str:
    if not metric_rows:
        return ""
    bars = "".join(_render_metric_bar(r) for r in metric_rows)
    extra = extra_html or ""
    return f"""<div class="savant-card__section">
    <p class="savant-card__section-eyebrow">{html.escape(eyebrow)}</p>
    {bars}
    {extra}
  </div>"""


def _render_metric_bar(row: dict[str, Any]) -> str:
    label = row["metric_label"]
    pct_fbs = row.get("pct_vs_fbs")
    pct_p4 = row.get("pct_vs_p4")
    pct_conf = row.get("pct_vs_conf")
    pct_alltime = row.get("pct_vs_alltime")
    raw = row.get("raw_value")

    # Primary (visible) percentile defaults to FBS
    pct_main = pct_fbs if pct_fbs is not None else 50.0
    band = _percentile_band(pct_main)

    # Attrs — numeric strings for each peer set, default "—" if null
    def _attr(v: float | None) -> str:
        return f"{v:.1f}" if v is not None else ""

    raw_str = f"{raw:+.2f}" if isinstance(raw, (int, float)) else "—"

    return f"""<div class="savant-bar" data-band="{band}"
      data-pct-fbs="{_attr(pct_fbs)}"
      data-pct-p4="{_attr(pct_p4)}"
      data-pct-conf="{_attr(pct_conf)}"
      data-pct-alltime="{_attr(pct_alltime)}">
      <div class="savant-bar__label">
        <span class="savant-bar__label-text">{html.escape(label)}</span>
        <span class="savant-bar__raw">{html.escape(raw_str)}</span>
      </div>
      <div class="savant-bar__track">
        <div class="savant-bar__fill" style="width: {pct_main:.1f}%"></div>
        <div class="savant-bar__midline" aria-hidden="true"></div>
      </div>
      <div class="savant-bar__value" aria-label="Percentile">
        <span class="savant-bar__pct">{int(round(pct_main))}</span><span class="savant-bar__pct-sup">th</span>
      </div>
    </div>"""


def _render_echo(echo: dict[str, Any]) -> str:
    headline = echo.get("headline") or "Defensive echo"
    body = echo.get("body_md") or ""
    return f"""<div class="savant-card__echo">
      <span class="savant-card__echo-eyebrow">ECHO · cross-era defensive match</span>
      <p class="savant-card__echo-body"><strong>{html.escape(headline)}</strong> — {html.escape(body)}</p>
    </div>"""


def _render_legend() -> str:
    bands = (
        ("elite",    90, "ELITE · 90+"),
        ("strong",   70, "STRONG · 70+"),
        ("average",  40, "AVERAGE · 40-70"),
        ("concern",  10, "CONCERN · 10-40"),
        ("bottom",    0, "BOTTOM · <10"),
    )
    chips = "".join(
        f'<span class="savant-card__legend-chip savant-card__legend-chip--{key}">{html.escape(label)}</span>'
        for key, _, label in bands
    )
    return f'<div class="savant-card__legend">{chips}</div>'


def _percentile_band(pct: float) -> str:
    if pct >= 90: return "elite"
    if pct >= 70: return "strong"
    if pct >= 40: return "average"
    if pct >= 10: return "concern"
    return "bottom"


# ------------------------------------------------------------------------
# Peer-set toggle — tiny vanilla JS, inlined at render time.
# ------------------------------------------------------------------------

_SAVANT_TOGGLE_JS = """<script>
(function(){
  var cards = document.querySelectorAll('.savant-card');
  cards.forEach(function(card){
    var chips = card.querySelectorAll('.savant-card__chip');
    var bars = card.querySelectorAll('.savant-bar');
    function applyPeer(peer){
      bars.forEach(function(bar){
        var v = bar.getAttribute('data-pct-' + peer);
        var fill = bar.querySelector('.savant-bar__fill');
        var pct = bar.querySelector('.savant-bar__pct');
        var num = v && v.length ? parseFloat(v) : null;
        if (num === null || isNaN(num)) {
          if (fill) fill.style.width = '0%';
          if (pct) pct.textContent = '—';
          bar.setAttribute('data-band','missing');
        } else {
          if (fill) fill.style.width = num.toFixed(1) + '%';
          if (pct) pct.textContent = Math.round(num);
          var band = num >= 90 ? 'elite' : num >= 70 ? 'strong' : num >= 40 ? 'average' : num >= 10 ? 'concern' : 'bottom';
          bar.setAttribute('data-band', band);
        }
      });
    }
    chips.forEach(function(chip){
      chip.addEventListener('click', function(){
        chips.forEach(function(c){
          c.classList.remove('savant-card__chip--active');
          c.setAttribute('aria-pressed','false');
        });
        chip.classList.add('savant-card__chip--active');
        chip.setAttribute('aria-pressed','true');
        applyPeer(chip.getAttribute('data-peer'));
      });
    });
  });
})();
</script>"""
