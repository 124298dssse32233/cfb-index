# Era Context — algorithm spec (S1.3)

**Purpose.** For any (player, metric, season, value, cohort) tuple we render
an optional one-line historical hook — `Best by a ND QB since Brady Quinn
2006.` — beneath the stat. It gives every record-eligible number a sense
of scale without a click, and produces copy that screenshots well.

**Shape.** `compute_era_context(db, player_id, metric_id, season, value,
cohort) -> dict`:

```py
{
  "applicable": bool,            # False => caller renders nothing
  "text":       str,             # Render-ready sentence (escaped at callsite)
  "target_ref": {                # Source tuple for audit / hover reveal
    "player_id": int | None,
    "player_slug": str | None,
    "season": int | None,
    "metric_id": str,
    "cohort": str,               # "program-qb", "conference-qb", ...
    "rank_in_cohort": int,
    "era_start_season": int,
  }
}
```

The caller escapes `text` before rendering and can surface `target_ref`
behind a `?` methodology popover in a future iteration.

## Cohort resolution order

For a (metric, value, season) we try cohorts in this order and stop on
the first that produces an interesting comparable:

1. **program-position** — same school, same position ("ND QBs"). The
   strongest claim because readers already care about the program.
2. **conference-position** — same conference, same position ("Big Ten
   QBs this decade"). Used when the program cohort has too few prior
   comparables.
3. **level-position** — same subdivision (FBS / FCS), same position
   ("any P4+ND QB since 2020"). Fallback for thin-coverage programs.

We do NOT compare across positions or across levels — "best RB since
Reggie Bush" is correct, "best player since Reggie Bush" is not.

## Interestingness gate

An era-context string ships only if ALL of the following hold:

- **Coverage floor**: the cohort has ≥ 4 seasons of data under the same
  `stat_type`. With fewer, any "best since" claim is vacuous. Today's DB
  has 2024–2025 passing + 2025 rushing — so most stats return
  `applicable=False` until the historical backfill runs.
- **Rank gate**: the current value ranks in the top-3 of the cohort over
  its covered window. Records (rank 1) always ship; rank-2 / rank-3 ship
  only if the gap to #1 is < 10%.
- **Same-player-excluded**: if the current player is the #1, we name the
  #2 prior holder in the text ("Best ND QB passing efficiency since
  Everett Golson 2012 — Carr is #1, Golson was #2").
- **Named-predecessor**: the comparable row must resolve to a known
  `players.full_name`. An anonymous row drops to `applicable=False`.

## Text templates

Templates are chosen by `target_ref` shape. All end in a period, no
exclamation points (brief §2 voice #8 / §3 phase banner rules).

- **Program cohort, player sets a new mark**: `Best by a {program_short}
  {position} since {predecessor_name} {predecessor_season}.`
- **Program cohort, player ties / near-ties**: `Tied for best by a
  {program_short} {position} with {predecessor_name} {predecessor_season}.`
  if values are within 0.5% of each other.
- **Conference fallback**: `Top-{rank} among {conference_short}
  {position}s since {era_start_season}.`
- **Level fallback**: `Top-{rank} among {level_label} {position}s in the
  {era_label} era ({era_start_season}–present).`

## Data plumbing

Read from `player_season_stats` (stat_value_num for the metric), join to
`players` for `full_name` and `teams` for `school_name`, `short_name`,
and `current_conference_id`. Era boundaries:

- `era_start_season` = oldest season the cohort has under this metric.
- `era_label` = "modern" (2020+), "analytics" (2010–2019), "BCS-era"
  (2006–2009), "pre-BCS" (pre-2006).

Future iterations can introduce coach-tenure era boundaries (e.g.
"since the Freeman era began 2022") but that requires the coaching
lineage graph (S2.9). Start simple; upgrade when the graph lands.

## Graceful degradation

- No cohort match → `applicable=False`, caller renders nothing.
- Coverage floor failure → `applicable=False`.
- Named-predecessor missing → fall back to the next cohort.
- All cohorts exhausted → `applicable=False`.

`applicable=False` means "we didn't find a historical hook worth
showing" — never an error message. The caller must render the metric as
if the era context simply doesn't exist.

## Caching + performance

Era context is computed once per player-page build — read pattern is a
small indexed query. A per-player cache inside `compute_era_context`
with `(player_id, metric_id, season)` keys is acceptable; build-site
regenerates it fresh each run, so TTL doesn't matter.

## What this spec deliberately does NOT include

- **Cross-position comparables**. "Best WR since Randy Moss" stays in
  the WR cohort; no "best athlete" claims.
- **Career comparables vs single-season**. This spec handles single-
  season values only. Career aggregates need their own compute path.
- **Subjective records**. No "best clutch performance," "best under
  pressure," etc. — those need situational PBP data the cohort
  aggregator doesn't thread today.
- **Below-level claims**. "Best FBS QB since X" is fine. "Best quarterback
  since Peyton Manning" (cross-level) is not — conflates FBS with NFL.

## Acceptance criteria

- Given a player with a headline metric and ≥ 4 seasons of cohort
  coverage, `compute_era_context()` returns `applicable=True` with a
  verifiable text string.
- Given a player with zero historical comparables (walk-on, FCS, new
  program), returns `applicable=False` quietly — never a placeholder.
- Every era-context text string is empirically true: the named
  predecessor actually did hold the prior best mark at the specified
  season for the specified cohort.
- No exclamation points, no hype adjectives, no cross-position claims.
