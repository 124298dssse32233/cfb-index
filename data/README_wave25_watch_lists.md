# Wave 25 — 2026 Offseason Watch Lists

How to edit and refresh the 2026 award watch + depth chart data that
powers the Player Outlook module.

## Files

- `data/award_watch_2026.csv` — preseason award candidates (Heisman,
  Maxwell, Davey O'Brien, Doak Walker, Biletnikoff, Mackey, Outland,
  Bednarik, Nagurski, Butkus, Thorpe, Walter Camp, Manning, Lou Groza,
  Ray Guy, Hornung, Lott IMPACT).
- `data/depth_chart_2026.csv` — projected 2026 starters by position.

Both are CSV with `#` for comment lines. The first non-comment line is
the header. The loaders ignore comments + blank lines so feel free to
group rows by award/position with section headings.

## Editing workflow

1. **Find the player's `player_id`** — query the DB:
   ```bash
   python -c "import sqlite3; print(sqlite3.connect('cfb_rankings.db').execute(\"SELECT player_id, full_name FROM players WHERE full_name LIKE '%Manning%'\").fetchall())"
   ```
2. **Add the row** with both `player_id` AND `full_name_for_audit`. The
   loader cross-checks the audit name against `players.full_name` and
   refuses to load mismatched rows. This prevents typos from creating
   ghost rows that don't render.
3. **Set `as_of`** to the date you sourced the data. This shows up as
   "Updated MMM DD" in the Outlook pill — keep it recent so the freshness
   signal stays honest.
4. **Use `priority`** (1 = top tier, 3+ = depth) — the outlook module
   shows max 3 awards per player, ordered by priority.
5. **Run the loader:**
   ```bash
   python manage.py refresh-award-watch
   python manage.py refresh-depth-chart
   ```

## Auto-skip of ineligible players

Both loaders query `player_current_status_cache` and skip any pid whose
status is `NFL_DRAFTED_*`, `EXHAUSTED_ELIGIBILITY`, `MEDICAL_RETIREMENT`,
or `HISTORICAL_ALUM`. This is a safety net — if you add a player to the
CSV who later gets drafted, the loader drops the row with a warning
listing the pid + name.

`TRANSFERRED_COLLEGE` is **not** ineligible — transferred players are
still on a 2026 college roster.

To purge stale rows from CSV (one-shot cleanup):
```bash
python scripts/clean_watch_csvs.py [--dry-run]
```

## Source-of-truth rebuild

After editing CSVs, also rebuild the status cache so any newly
overridden players propagate:
```bash
# Done automatically by manage.py build-site, but to do it standalone:
python -c "
import sqlite3
con = sqlite3.connect('cfb_rankings.db', timeout=300)
con.executescript('''
DROP TABLE IF EXISTS player_current_status_cache;
CREATE TABLE player_current_status_cache AS
SELECT * FROM (
    SELECT v.*,
           ROW_NUMBER() OVER (PARTITION BY player_id ORDER BY
               CASE WHEN current_team_id IS NULL THEN 1 ELSE 0 END,
               CASE WHEN status_code='TRANSFERRED_COLLEGE' THEN 0
                    WHEN status_code='RETURNING_2026' THEN 1
                    ELSE 2 END
           ) AS rn
    FROM player_current_status_view v
) WHERE rn = 1;
ALTER TABLE player_current_status_cache DROP COLUMN rn;
CREATE UNIQUE INDEX idx_player_current_status_cache_pid
    ON player_current_status_cache(player_id);
''')
con.commit()
"
```

## Verify everything

```bash
python -X utf8 manage.py verify-wave25
```

Should print `Wave 25 verify: 27 PASS / 0 FAIL`.

## Auto-refresh cadence

`.github/workflows/offseason-watch-refresh.yml` re-runs the loaders
twice a week (Mon 11am ET + Sun 3am ET during peak watch-list season).
After each refresh, the workflow:

1. Reloads both CSVs into the DB
2. Rebuilds the status cache
3. Runs `verify-wave25`
4. Uploads the refreshed DB artifact
5. Triggers `publish-site.yml` to rebuild + deploy

Manual trigger: `gh workflow run offseason-watch-refresh.yml`

## Source provenance

The `source` column on each row identifies where the entry came from:
- `consensus_may_2026` — ESPN/On3/247/Phil Steele/PFF May 2026 lists
- `watchlist_official` — official watch list from the award foundation
- `manual_editorial` — editor judgment (use sparingly)

Use `--prune-source=<source>` on the loader to drop any DB rows from a
specific source that are no longer in the CSV — keeps the table clean
when you swap consensus for official watch lists in mid-July.

## Adding a new award

1. Add rows to `award_watch_2026.csv` with the new `award_slug`.
2. Add display name to `_award_display_name()` in
   `src/cfb_rankings/player_pages/outlook_2026.py` so the badge label
   isn't title-cased machine output.
3. Run `refresh-award-watch` + rebuild.
