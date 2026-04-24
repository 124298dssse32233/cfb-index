# Achievements — taxonomy + rarity spec (S2.6)

**Purpose.** Video-game-style statistical achievements for the page.
Gold medallions near the Hero; hover reveals criteria + rarity + unlock
context. Power users collect, share, compare.

## Rarity discipline

- Most achievements should be held by < 10% of the qualifying cohort.
- Rarity is computed nightly and stored alongside the unlock row so
  the UI shows it without a second query.
- If an achievement's rarity inflates above 15%, we re-tune its
  criteria or hold it until the next editorial review.

## Taxonomy (v1 — derived from today's data)

The brief names ~12 achievements. Most need PBP / situational data we
don't carry. The v1 taxonomy below is everything we can verify against
`player_season_stats` / `player_value_metrics` / `player_honors` /
`player_mirror_matches`.

### 1. Dual Threat  ·  `achievement_dual_threat`

**Criteria**: QB with a top-50 WEPA passing-per-dropback AND a top-50
WEPA rushing-per-carry in the same season. Both cohorts drawn from
`p4_plus_nd_qbs`.

**Volume floor**: min 150 dropbacks + min 30 rushing attempts.

**Target rarity**: 3–7% of qualifying QBs.

### 2. Money Efficiency  ·  `achievement_money_efficiency`

**Criteria**: top-5 in the season's signature-story YPA metric, min 150
attempts. (Rename follow-up when PBP lands: "Money Down" — top-3 in
3rd-down EPA.)

**Target rarity**: ~5% of starters.

### 3. Program Benchmark  ·  `achievement_program_benchmark`

**Criteria**: #1 in the program-position cohort for a headline metric
(passing yards, rushing yards, receiving yards) within the current season.

**Target rarity**: variable — one per program-position-season.

### 4. Mirror-Match Elite  ·  `achievement_mirror_elite`

**Criteria**: Top Mirror Match similarity ≥ 95 AND that match's player
holds a Heisman-finalist or All-American honor (from
`player_honors`).

**Target rarity**: < 2% of pool. Until the historical backfill lands
this mostly sits dormant.

### 5. The Volume King  ·  `achievement_volume_king`

**Criteria**: 2,500+ passing yards OR 1,200+ rushing yards OR 900+
receiving yards in a single season (position-appropriate).

**Target rarity**: ~10% of qualifying starters.

### 6. Honors Badge  ·  `achievement_honors_badge`

**Criteria**: any row in `player_honors` with `honor_type` containing
"All-American", "Heisman", "Davey O'Brien", "Maxwell", "Camp", "Nagurski",
or "Biletnikoff".

**Target rarity**: varies by honor tier; rarer honors (Heisman)
auto-amplify.

## Data model

```
CREATE TABLE IF NOT EXISTS player_achievements (
    player_id         INTEGER NOT NULL,
    achievement_id    TEXT    NOT NULL,
    season_year       INTEGER NOT NULL,
    unlocked_at       TEXT    DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    unlock_context    TEXT,                  -- "5th in YPA among 73 P4+ND QBs"
    rarity_pct        REAL,                  -- % of pool that holds this
    meta_json         TEXT,
    PRIMARY KEY (player_id, achievement_id, season_year)
);

CREATE TABLE IF NOT EXISTS achievement_catalog (
    achievement_id   TEXT PRIMARY KEY,
    display_name     TEXT NOT NULL,
    icon_slug        TEXT NOT NULL,          -- maps to a medallion style
    description      TEXT NOT NULL,
    target_rarity    REAL,
    position_filter  TEXT,                   -- NULL / 'QB' / 'RB' / 'WR'
    is_active        INTEGER DEFAULT 1
);
```

The catalog is seeded from `seeds/achievement_catalog.yaml` at build
time so adding / holding achievements is a YAML edit.

## Detection + rarity pipeline

`compute_achievements(db, season)`:
1. Pulls every qualifying player-pool per catalog row.
2. Runs the achievement's detector.
3. Writes one `player_achievements` row per (player, achievement,
   season).
4. Recomputes `rarity_pct` after all unlocks land.

Idempotent via the primary key. Intended as a nightly CLI subcommand:
`python manage.py compute-achievements [--season]`.

## Renderer

A ribbon of gold medallions near the Hero on every player page:

```
<article class="achievements" data-module="achievements">
  <p class="achievements__eyebrow">Achievements</p>
  <ul class="achievements__ribbon">
    <li class="achievement" data-rarity="…">
      <span class="achievement__medallion" aria-hidden="true">…</span>
      <div class="achievement__tooltip">
        <strong>Dual Threat</strong>
        <p>Top-50 in both passing and rushing WEPA.</p>
        <p>Held by 4% of P4+ND QBs. Unlocked Week 9 2025 vs Stanford.</p>
      </div>
    </li>
    …
  </ul>
</article>
```

Empty state: `data-state="empty"` with a single muted line
("No achievements unlocked yet this season") — never hidden, so it's
clear the module exists.

## What this spec deliberately does NOT include

- PBP-derived achievements (Red Zone Surgeon, Clutch Gene, Money Down,
  Elite Pocket, Gunslinger, Cold-Weather, Road Warrior) — ship when
  situational data plumbs through.
- Share-card PNG generation — static canvas v1 is copy-to-clipboard
  text + page URL.
- Cross-season career achievements — single-season only for v1.

## Acceptance criteria

- Carr page renders ≥ 2 medallions (expected: Volume King + Honors
  Badge at minimum; Dual Threat and Program Benchmark if criteria
  clear).
- Walk-on page renders the empty-state ribbon.
- Rarity shown on hover matches the actual pool share.
- `compute-achievements --season 2025` runs without errors.
