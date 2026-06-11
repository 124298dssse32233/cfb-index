"""Fanbase Voice team-page module — Language Layer Wave 2.

The fanbase personality card: five traits (Optimism / Joy / Anger / Doom /
Sarcasm) as Savant-style horizontal percentile bars vs the season's
highest-volume cohort, with a median tick at 50 and a deterministic headline
label derived from the percentiles themselves. No survey, no LLM — just how
they actually write.

Reads fanbase_voice_profile (written by ``manage.py compute-fanbase-voice``).
The engine only writes rows for cohort members (>= mention floor), so an
absent row IS the confidence floor — the module returns "" and collapses out
of the act (graceful-degradation contract).

Public API:
    render_voice_profile(db, profile, snapshot) -> str
    VOICE_PROFILE_CSS                           -> str
"""

from __future__ import annotations

from html import escape
from typing import Any

from .data import TeamSnapshot
from .profile_loader import Profile

_ROW_KEYS = (
    "season_year", "n_mentions", "optimism_pct", "joy_pct", "anger_pct",
    "doom_pct", "sarcasm_pct", "optimism_rank", "cohort_size",
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


def _ordinal(n: int) -> str:
    if 10 <= (n % 100) <= 13:
        return f"{n}th"
    return f"{n}{({1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th'))}"


def _headline(optimism_rank: int, optimism_pct: int, joy_pct: int,
              anger_pct: int, doom_pct: int, sarcasm_pct: int) -> str:
    """Deterministic personality label — rule order is the spec."""
    if optimism_rank == 1:
        return "The most optimistic fanbase we track"
    if optimism_pct >= 80:
        return "Believers"
    if sarcasm_pct >= 80 and joy_pct >= 80:
        return "Happy and insufferable"
    if anger_pct >= 80 or doom_pct >= 80:
        return "Doomers"
    return "Measured"


def _bar(label: str, pct: int) -> str:
    pct = max(0, min(100, int(pct)))
    return (
        f'<div class="voice-profile__row">'
        f'<span class="voice-profile__lbl">{escape(label)}</span>'
        f'<div class="voice-profile__track">'
        f'<div class="voice-profile__med"></div>'
        f'<div class="voice-profile__dot" style="left:{pct}%"></div>'
        f'</div>'
        f'<span class="voice-profile__pct">{_ordinal(pct)}</span>'
        f'</div>'
    )


def render_voice_profile(db, profile: Profile, snapshot: TeamSnapshot | None) -> str:
    if db is None or snapshot is None or not getattr(snapshot, "team_id", None):
        return ""
    team_id = int(snapshot.team_id)
    try:
        row = db.query_one(
            "SELECT season_year, n_mentions, optimism_pct, joy_pct, anger_pct, "
            "doom_pct, sarcasm_pct, optimism_rank, cohort_size "
            "FROM fanbase_voice_profile "
            "WHERE team_id = :team_id "
            "ORDER BY season_year DESC LIMIT 1",
            {"team_id": team_id},
        )
    except Exception:
        # Table may not exist yet (migration owned by another wave) — skip.
        return ""
    if row is None:
        # Below the cohort mention floor — honest empty.
        return ""

    try:
        season = int(_field(row, "season_year") or 0)
        n_mentions = int(_field(row, "n_mentions") or 0)
        optimism_pct = int(_field(row, "optimism_pct") or 0)
        joy_pct = int(_field(row, "joy_pct") or 0)
        anger_pct = int(_field(row, "anger_pct") or 0)
        doom_pct = int(_field(row, "doom_pct") or 0)
        sarcasm_pct = int(_field(row, "sarcasm_pct") or 0)
        optimism_rank = int(_field(row, "optimism_rank") or 0)
        cohort_size = int(_field(row, "cohort_size") or 0)
    except (TypeError, ValueError):
        return ""
    if not season or cohort_size <= 0:
        return ""

    headline = _headline(
        optimism_rank, optimism_pct, joy_pct, anger_pct, doom_pct, sarcasm_pct
    )
    bars = "".join([
        _bar("Optimism", optimism_pct),
        _bar("Joy", joy_pct),
        _bar("Anger", anger_pct),
        _bar("Doom", doom_pct),
        _bar("Sarcasm", sarcasm_pct),
    ])

    return f"""
<section class="voice-profile" aria-label="Fanbase Voice">
  <div class="voice-profile__head">
    <span class="voice-profile__eyebrow">Fanbase Voice</span>
    <span class="voice-profile__mentions">{n_mentions:,} fan mentions</span>
  </div>
  <div class="voice-profile__arch">{escape(headline)}</div>
  <div class="voice-profile__bars">{bars}</div>
  <div class="voice-profile__cohort">vs the {cohort_size} highest-volume fanbases - {season} season</div>
</section>"""


VOICE_PROFILE_CSS = """
/* Fanbase Voice — personality percentile card (Language Layer Wave 2) */
.voice-profile {
  display: grid;
  gap: clamp(10px, 1.2vw, 14px);
  padding: clamp(14px, 1.8vw, 20px) clamp(16px, 2.0vw, 24px);
  background: rgba(255, 255, 255, 0.025);
  border: 1px solid var(--stroke-subtle, rgba(255,255,255,0.08));
  border-radius: 12px;
  margin-bottom: clamp(20px, 3vw, 32px);
  font-variant-numeric: tabular-nums;
}
.voice-profile__head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}
.voice-profile__eyebrow {
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--accent-primary, #c9a24a);
}
.voice-profile__mentions {
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 10.5px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--fg-muted);
}
.voice-profile__arch {
  font-family: var(--font-display, 'Bebas Neue', Impact, sans-serif);
  font-size: clamp(22px, 1.8vw + 10px, 30px);
  line-height: 1.05;
  letter-spacing: 0.02em;
  text-transform: uppercase;
  color: var(--fg-primary);
}
.voice-profile__bars { display: grid; gap: 2px; }
.voice-profile__row {
  display: grid;
  grid-template-columns: 84px 1fr 44px;
  gap: 10px;
  align-items: center;
  padding: 5px 0;
}
.voice-profile__lbl {
  font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
  font-size: 12.5px;
  font-weight: 600;
  color: var(--fg-primary);
}
.voice-profile__track {
  position: relative;
  height: 8px;
  background: rgba(255, 255, 255, 0.06);
  border-radius: 4px;
}
.voice-profile__med {
  position: absolute;
  left: 50%;
  top: -3px;
  bottom: -3px;
  width: 1px;
  background: color-mix(in srgb, var(--accent-primary, #c9a24a) 45%, transparent);
}
.voice-profile__dot {
  position: absolute;
  top: 50%;
  transform: translate(-50%, -50%);
  width: 15px;
  height: 15px;
  border-radius: 50%;
  background: var(--accent-primary, #c9a24a);
  border: 2px solid var(--bg-primary, #101418);
}
.voice-profile__pct {
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 11.5px;
  text-align: right;
  color: var(--fg-primary);
}
.voice-profile__cohort {
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 10.5px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--fg-muted);
}
@media (max-width: 480px) {
  .voice-profile__row { grid-template-columns: 72px 1fr 40px; gap: 8px; }
  .voice-profile__lbl { font-size: 11.5px; }
}
"""


__all__ = ["render_voice_profile", "VOICE_PROFILE_CSS"]
