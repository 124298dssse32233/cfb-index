# Statistical Mirror Match — algorithm spec (S2.5)

**Purpose.** For any qualifying player, surface the historical player
whose statistical fingerprint is most similar. Rabbit-hole mechanic
("this Carr season feels like Bo Nix 2023") that rewards lingering.

## Feature vector per position

A player's fingerprint is a fixed-length vector of percentile-normalized
stat values in their position's feature set. Percentiles are computed
against each stat's season-specific cohort so a 2025 value and a 2020
value compare on the same axis.

- **QB features**: `passing_yds`, `passing_tds`, `passing_pct`,
  `passing_ypa`, `rushing_yds_qb`, `rushing_ypc_qb`.
- **RB features**: `rushing_yds`, `rushing_ypc`, `rushing_tds`,
  `receiving_yds`, `receiving_ypr`.
- **WR features**: `receiving_yds`, `receiving_ypr`, `receiving_tds`,
  `receiving_rec`.

Each feature value is clipped to 0..100 (the percentile band) before
similarity. Missing values for a given feature are filled with the
cohort median (50) to avoid penalizing a player for a stat the DB
doesn't carry in their season; a counter is kept per match to disclose
how many features were median-filled ("thin match" badge when ≥ 40%).

## Similarity metric

**Cosine similarity** on the feature vector — simple, scale-free, and
compatible with missing-value median-fill. Range: -1..1; we report it
as an integer 0..100 (linearly mapped from 0..1 after clamping the
negative tail).

Mahalanobis and Euclidean are out of scope for v1 — cosine is close
enough for the "does this feel right" smell test and faster.

## Cohort weighting

Similarity is computed pairwise against every **same-position** player
in the last 15 seasons (or whatever data exists today — currently
2024–2025 passing, 2025 rushing / receiving). We do NOT bias toward
same-era matches; the reader already knows the era and we want honest
cross-era matches where they exist.

Guardrail: matches with similarity < 75 are dropped. Better to show
zero matches than a weak one.

## Sample-size guardrails

A candidate match must satisfy:

- Candidate's season had ≥ 50% of the feature coverage of the target's
  season (otherwise the median-fill share explodes).
- Candidate's sample on the dominant feature (e.g. QB: passing
  attempts) ≥ 150.

Both guardrails silently drop candidates from the match pool.

## Nightly batch

`compute_mirror_matches(db, season, k=10)` writes one `player_mirror_
matches` row per (player, season, match-slot) with similarity score +
feature-coverage fraction + match_player_id + match_season. Idempotent
via `ON CONFLICT(player_id, season_year, match_slot) UPDATE`.

Build-site calls `compute_mirror_matches` as a pre-step (like the
Hot-Take cache in S2.2) so page renders only read the cache.

## Renderer

Small card nested in the Peer Comparator section:

```
Statistical mirror — Closest historical fingerprint
<name>, <team> <year>  ·  <similarity>% similar
Why: <similarity drivers as "+passing_ypa, −rushing_ypc"-style chips>
See top 10 →   (drawer; progressive-disclosure)
```

Empty state when no match clears the 75 floor:

```
Awaiting historical backfill — the 15-year cohort
is thin for this player's position today.
```

## Data reality disclosure

Current `player_season_stats` coverage (per S1.3 era_context audit):
passing YDS/TDs/PCT/YPA available 2024–2025, rushing / receiving
available 2025 only. That means the Mirror Match pool today is
`position=QB, season ∈ {2024}` for a 2025 QB target. One-season
cohort, high collision rate on similar programs, and the 75-similarity
floor will drop most pairs. Mirror matches surface organically as a
historical backfill lands; until then the card renders empty-state on
almost every page.

## What this spec deliberately does NOT include

- **Trajectory matching** (through-week-N vs through-week-N). Requires
  per-week cumulative feature vectors; season-level is v1.
- **Cross-position matching**. A QB's mirror is always a QB.
- **Narrative generation** ("...Finished 3rd in Heisman, 1st-round NFL
  pick"). Requires honors + draft tables threaded in; v1 surfaces the
  (name, team, year, similarity) quadruple only.

## Acceptance criteria

- `compute_mirror_matches(db, season)` completes without errors on the
  live DB.
- `python manage.py player-mirror-match <slug>` prints top-k.
- Carr page: renders the card with either a real match (≥ 75 sim) or
  the Awaiting-Signal empty state.
- Walk-on page: renders empty state.
- 20-player spot check: every real match passes a "does this feel
  comparable" smell test (Haiku verification in a future task).
