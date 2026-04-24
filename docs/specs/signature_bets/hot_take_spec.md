# Hot-Take Engine — design spec (S2.1)

**Purpose.** Auto-generate one-liner statistical hot-takes that are
defensibly true, screenshot-worthy, and exactly surprising enough that
r/CFB power users retweet them. One take per player per day; rotated
nightly; always paired with an Anti-Take (S2.3).

## Defensibility quadruple

Every take ships with a resolved `(rank, cohort, sample, methodology)`
tuple. The take doesn't render without all four. The four are surfaced
in the UI via the "see the math" drawer (follow-up) and a `meta` block
inside the render payload:

```
meta = {
  "rank":         int,   # 1-based rank within the stated cohort
  "cohort":       str,   # cohort_id and human label, e.g. "p4_plus_nd_qbs (P4+ND QBs)"
  "sample":       int,   # rows / snaps / attempts contributing to the value
  "methodology":  str,   # 1-line description of how the stat was computed
}
```

A take that can't resolve all four is a bug, not a draft. We hold it.

## Candidate generation

For each player we pull the Signature Story evaluation cache
(`compute_signature_story_index`). Every metric the player qualified
for is a candidate take. We do NOT add a separate scoring pipeline
here — Signature Story already did the work of picking "interesting"
metrics with audit trails. Hot-Take reads from it directly.

For each candidate:

```
candidate = {
  "metric_id":        str,
  "value":            float,
  "rank":             int,
  "cohort_id":        str,
  "cohort_size":      int,
  "percentile":       float,
  "sample_size":      int,
  "higher_is_better": bool,
  "narrative_weight": float,   # from the metric seed
  "label":            str,
  "unit":             str,
  "position":         str,
}
```

## Defensibility gates

A candidate SHIPS only if all of these hold:

- `sample_size >= 40`                 — HIGH confidence band (S1.2 rule)
- `percentile >= 90`                  — interesting only when it's rare
- `rank <= 5`                         — top-5 or nothing; we don't ship "top-17"
- `cohort_size >= 20`                 — no microscopic cohorts
- `higher_is_better == True`          — negative-direction metrics (e.g. INT%)
                                        need hand-authored phrasing; skip for v1
- metric is registered in `_METRIC_TEMPLATES` — no template, no take

Failures are silent — candidates drop out; if none remain the player
has no hot-take today and renders nothing. Absence is acceptable.

## Novelty scoring

Ranking among candidates that cleared the gates:

```
score = percentile * log(max(sample_size, 2)) * narrative_weight * position_weight
```

- `narrative_weight` is the editorial lever already defined in
  `seeds/signature_story_metrics.yaml`; efficiency metrics score higher
  than volume metrics. Zero new knobs.
- `position_weight` is a small multiplier (QB 1.0, RB/WR 0.95, other
  0.9) that keeps the top-of-page real estate tilted toward
  headline-grabbing positions without blocking RB/WR stories.

The highest-scoring candidate wins. Ties break by lowest rank, then by
largest sample.

## Template library

Seed file: `seeds/hot_take_templates.yaml`. Each template has:

- `id`            — stable slug.
- `applies_to`    — list of metric_id(s) or `"*"` for wildcard.
- `text`          — Python .format()-ready with named placeholders.
- `voice`         — `"record" | "record_near" | "pace" | "cohort_top"`.
- `min_percentile` — override to the 90 default if the template needs
                     a stricter threshold (e.g. "record" voice wants 99+).

Available placeholders (verified at load time):

```
{value}            pre-formatted string w/ unit
{metric_label}     human label from seed
{rank}             int
{cohort_size}      int
{cohort_label}     human cohort label ("P4+ND QBs", "FBS RBs")
{position}         "QB" / "RB" / "WR"
{percentile}       int
{era_label}        "modern" / "analytics" / "BCS-era"
{program_short}    for program-scoped takes (future)
```

## Voice rules (§2 + §3 brief)

- Declarative, never hedged. Own the take.
- No exclamation points. No hype adjectives ("generational", "insane",
  "unreal"). Stat + cohort + era does the work.
- One sentence. Period. Two sentences only if the second is a
  falsification clause (handled by the Anti-Take, not the Hot-Take).
- No "technically" or "arguably". If it's technically-true-but-
  misleading, it fails the defensibility gate.

## Daily rotation

`select_daily_take(candidates, today)` picks deterministically per-day
so every reader across the world sees the same take on the same date,
and so a backfill of historical takes is reproducible.

Algorithm:

```
sort candidates by score DESC
daily_seed = hash(player_id || date.isoformat()) mod N
# N = 3 by default — rotate among top-3 to keep a day-to-day feel
# without drifting to weaker candidates. If fewer than 3 exist, rotate
# among what's there.
pick = candidates[daily_seed mod len(candidates[:3])]
```

This means a reader visiting Carr's page on three consecutive days
sees three different takes — each one passing the defensibility gate,
each scored near the top.

## QA + hold logic

- Every rendered take has a `flag this take` button (UI follow-up —
  not blocking for S2.2).
- Flags aggregate nightly into a `hot_take_flags` table.
- If a take accumulates a flag rate > 3% of its impression count over
  any rolling 7-day window, its template id is added to a deny-list and
  all takes using that template are held until the next editorial
  review. Deny-list lives in `hot_take_template_holds` — one row per
  held template with reason + held_at.

For S2.2 ship the writes + the deny-list read path; the flag button +
aggregation runner ship in S2 polish.

## Share-card generation

Punt to a static canvas-based helper. V1 emits an `<img>` placeholder
and the "share" CTA copies the take text + page URL to the clipboard.
V2 wires a headless-browser screenshot job that produces PNGs under
`output/site/assets/shares/player-{slug}-take-{id}.png`. Not blocking.

## Caching

A `player_daily_hot_take` table caches the selected take per (player,
date) so repeated build-site runs are idempotent and cheap:

```
CREATE TABLE IF NOT EXISTS player_daily_hot_take (
    player_id      INTEGER NOT NULL,
    as_of_date     TEXT    NOT NULL,   -- YYYY-MM-DD
    template_id    TEXT    NOT NULL,
    metric_id      TEXT    NOT NULL,
    rendered_text  TEXT    NOT NULL,
    meta_json      TEXT    NOT NULL,   -- defensibility quadruple
    score          REAL    NOT NULL,
    generated_at   TEXT    DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    PRIMARY KEY (player_id, as_of_date)
);
```

A nightly `compute_daily_hot_takes(db, date)` fills this; `build-site`
reads the cached row. If the row is missing the renderer falls back to
computing the take on the fly.

## What this spec deliberately does NOT include

- Cross-player ("Carr is better than any Heisman finalist since 2019")
  comparative takes — require the era-context backfill to land first.
- Situational takes (3rd-down, red-zone, under-pressure) — PBP
  situational data not threaded through signature_story today.
- Negative-framing takes ("Fewest INTs among …") — V1 sticks to
  higher-is-better metrics to keep the defensibility gate crisp.

## Acceptance criteria

- Carr page: one Hot-Take card above The Room with a defensibly-true
  one-liner, backed by a (rank, cohort, sample, methodology) quadruple
  verifiable against `player_season_stats` + signature_story output.
- Walk-on page: no Hot-Take card (gracefully absent — empty state hides
  the module entirely).
- `python manage.py player-hot-take <slug>` prints the take + the math
  trail (the resolved quadruple).
- A 30-take spot check across 30 players never surfaces a take that's
  technically-true-but-misleading (Haiku verification).
