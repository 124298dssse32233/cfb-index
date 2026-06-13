"""Pass Profile — depth-bucket completion view (Wave 11 v1).

Brief §8.6 calls for a field-oriented SVG pass chart (blue=completion,
grey=incomplete, gold=TD, red=INT, hex-bin on large samples). CFBD's
/plays endpoint exposes yards_gained but NOT lateral field position,
so a true field chart is impossible until we add a more granular feed.

What we CAN build from PBP: a depth-bucket view — short / mid / deep
completion %, TD/INT distribution, and yards-after-catch. This answers
the same "where is he winning?" question that a pass chart would.

Public API:
    render_pass_profile(db, player_id, season_year) -> str
    PASS_PROFILE_CSS                                -> str
"""
from __future__ import annotations

from html import escape
from typing import Any


PASS_PROFILE_CSS = """
/* Pass Profile (PBP depth buckets) */
.pass-profile {
  margin: var(--space-4, 1rem) 0 var(--space-6, 1.5rem) 0;
  padding: clamp(14px, 1.8vw, 20px) clamp(16px, 2.0vw, 24px);
  background: rgba(255, 255, 255, 0.025);
  border: 1px solid var(--stroke-subtle, rgba(255,255,255,0.08));
  border-left: 3px solid var(--accent-primary, var(--accolade-gold-base, #d1a23a));
  border-radius: 12px;
  font-variant-numeric: tabular-nums;
}
.pass-profile__head {
  display: flex; justify-content: space-between; align-items: baseline;
  gap: 12px; margin-bottom: 10px;
  border-bottom: 1px dashed var(--stroke-subtle, rgba(255,255,255,0.07));
  padding-bottom: 8px;
}
.pass-profile__eyebrow {
  font-size: 0.72rem; letter-spacing: 0.10em; text-transform: uppercase;
  color: var(--text-quiet, rgba(255,255,255,0.55)); margin: 0;
}
.pass-profile__title {
  font-size: 1.05rem; font-weight: 600; margin: 0;
  color: var(--text-bright, rgba(255,255,255,0.92));
}
.pass-profile__buckets {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}
@media (max-width: 720px) {
  .pass-profile__buckets { grid-template-columns: 1fr; }
}
.pass-profile__bucket {
  background: rgba(255,255,255,0.020);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 10px;
  padding: 12px 14px;
}
.pass-profile__bucket-label {
  font-size: 0.66rem; letter-spacing: 0.12em; text-transform: uppercase;
  color: var(--text-quiet, rgba(255,255,255,0.55));
  margin: 0 0 6px 0;
}
.pass-profile__bucket-range {
  font-size: 0.70rem;
  color: var(--text-quiet, rgba(255,255,255,0.45));
  display: block;
  margin-bottom: 6px;
}
.pass-profile__cmp {
  display: flex; align-items: baseline; gap: 6px;
  margin-bottom: 4px;
}
.pass-profile__cmp-pct {
  font-size: 1.4rem; font-weight: 700;
  color: var(--text-bright, rgba(255,255,255,0.92));
}
.pass-profile__cmp-sub {
  font-size: 0.74rem;
  color: var(--text-quiet, rgba(255,255,255,0.55));
}
.pass-profile__counts {
  display: flex; gap: 10px;
  font-size: 0.78rem;
  color: var(--text-soft, rgba(255,255,255,0.78));
  margin-top: 4px;
}
.pass-profile__count-td  { color: var(--accolade-gold-base, #d1a23a); }
.pass-profile__count-int { color: #ee8a92; }
.pass-profile__count-comp{ color: #4a78c4; }
.pass-profile__bar {
  height: 5px; border-radius: 3px; overflow: hidden;
  background: rgba(255,255,255,0.06);
  margin-top: 8px;
}
.pass-profile__bar > span {
  display: block; height: 100%;
  background: var(--pct-b0, #1e6fd9);
}
.pass-profile__lede {
  font-size: 0.86rem; line-height: 1.5;
  color: var(--text-soft, rgba(255,255,255,0.80));
  margin: 10px 0 0 0;
}
.pass-profile--empty {
  color: var(--text-quiet, rgba(255,255,255,0.55));
  font-style: italic;
  padding: 14px;
}
"""


# Depth buckets: (label, range_text, min_yards, max_yards)
_BUCKETS = [
    ("Short",  "0–9 yds",   -100, 9),
    ("Middle", "10–19 yds", 10,   19),
    ("Deep",   "20+ yds",   20,   200),
]


def _bucket_stats(
    db, player_id: int, season_year: int,
) -> list[dict[str, Any]]:
    """Per-bucket stats.

    Important: CFBD play data doesn't expose intended pass depth, only
    yards_gained on completions. So we can only bucket *completions* by
    depth. Incompletes are pooled separately (cmp% is computed only at
    the all-attempts level, not per bucket).
    """
    rows = db.query_all(
        """
        select
          p.yards_gained, a.is_complete, a.is_touchdown,
          a.is_interception, a.is_sack
        from cfbd_pbp_play_actors a
        join cfbd_pbp_plays p on p.play_id = a.play_id
        where p.season_year = :s
          and a.role = 'passer'
          and a.actor_player_id = :pid
          and a.is_sack = 0
        """,
        {"pid": player_id, "s": season_year},
    )
    if not rows:
        return []

    completions = [r for r in rows if r.get("is_complete") == 1]
    if not completions:
        return []

    total_attempts = len(rows)
    total_completions = len(completions)

    out: list[dict[str, Any]] = []
    for label, range_text, ymin, ymax in _BUCKETS:
        bucket_rows = [
            r for r in completions
            if r.get("yards_gained") is not None
            and ymin <= int(r["yards_gained"]) <= ymax
        ]
        n = len(bucket_rows)
        if n == 0:
            continue
        tds = sum(1 for r in bucket_rows if r.get("is_touchdown") == 1)
        # Avg yards in this bucket
        avg_yds = sum(int(r["yards_gained"]) for r in bucket_rows) / n
        # Share of overall completions in this depth
        share = (100.0 * n / total_completions) if total_completions else 0.0
        out.append({
            "label": label, "range_text": range_text,
            "completions": n, "tds": tds, "ints": 0,
            "avg_yds": avg_yds, "share_pct": share,
            "total_attempts": total_attempts,
            "total_completions": total_completions,
        })
    # Add a synthetic "overall" entry for header context
    out.append({
        "label": "_overall_meta",
        "total_attempts": total_attempts,
        "total_completions": total_completions,
        "cmp_pct_overall": (100.0 * total_completions / total_attempts) if total_attempts else 0.0,
        "total_ints": sum(1 for r in rows if r.get("is_interception") == 1),
        "total_tds":  sum(1 for r in rows if r.get("is_touchdown") == 1),
    })
    return out


def render_pass_profile(
    db, player_id: int | None, season_year: int | None,
) -> str:
    if db is None or player_id is None or season_year is None:
        return ""
    buckets = _bucket_stats(db, int(player_id), int(season_year))
    if not buckets:
        return ""

    overall = next((b for b in buckets if b["label"] == "_overall_meta"), None)
    if overall is None or overall["total_attempts"] < 50:
        return ""
    depth_buckets = [b for b in buckets if b["label"] != "_overall_meta"]
    if not depth_buckets:
        return ""

    cards: list[str] = []
    for b in depth_buckets:
        td_str = (f'<span class="pass-profile__count-td">{b["tds"]} TD</span>'
                  if b["tds"] else "")
        comp_str = (
            f'<span class="pass-profile__count-comp">{b["completions"]} comp</span>'
        )
        avg_str = (
            f'<span class="pass-profile__count-comp">{b["avg_yds"]:.1f} yds avg</span>'
        )
        cards.append(
            '<div class="pass-profile__bucket">'
            f'<p class="pass-profile__bucket-label">{escape(b["label"])}</p>'
            f'<span class="pass-profile__bucket-range">{escape(b["range_text"])}</span>'
            '<div class="pass-profile__cmp">'
            f'<span class="pass-profile__cmp-pct">{b["share_pct"]:.0f}%</span>'
            '<span class="pass-profile__cmp-sub">of completions</span>'
            '</div>'
            f'<div class="pass-profile__bar"><span style="width:{b["share_pct"]:.1f}%"></span></div>'
            f'<div class="pass-profile__counts">{comp_str}{avg_str}{td_str}</div>'
            '</div>'
        )

    total_att = overall["total_attempts"]
    total_comp = overall["total_completions"]
    cmp_pct = overall["cmp_pct_overall"]
    total_tds = overall["total_tds"]
    total_ints = overall["total_ints"]

    # Find best bucket (by yards-per-completion, more meaningful than share)
    best_avg = max(depth_buckets, key=lambda b: b["avg_yds"])
    # Lede
    lede_parts: list[str] = []
    lede_parts.append(
        f"Overall {cmp_pct:.1f}% completion on {total_att} attempts"
    )
    if best_avg["label"] == "Deep":
        if best_avg["completions"] >= 8:
            lede_parts.append(
                f"{best_avg['completions']} deep completions averaging {best_avg['avg_yds']:.1f} yds"
            )
    else:
        # Where most of the work happened
        biggest = max(depth_buckets, key=lambda b: b["completions"])
        lede_parts.append(
            f"{biggest['share_pct']:.0f}% of completions came in the {biggest['label'].lower()} bucket"
        )

    return (
        '<section class="pass-profile" '
        f'data-module="pass-profile" data-state="ready" '
        f'data-attempts="{total_att}">'
        '<header class="pass-profile__head">'
        '<div>'
        '<p class="pass-profile__eyebrow">Pass Profile &middot; Completion depth (PBP)</p>'
        '<p class="pass-profile__title">Where the throws are landing</p>'
        '</div>'
        f'<span class="pass-profile__meta">{total_comp}/{total_att} ({cmp_pct:.1f}%) &middot; '
        f'{total_tds} TD &middot; {total_ints} INT</span>'
        '</header>'
        f'<div class="pass-profile__buckets">{"".join(cards)}</div>'
        f'<p class="pass-profile__lede">{escape(" · ".join(lede_parts))}.</p>'
        '</section>'
    )
