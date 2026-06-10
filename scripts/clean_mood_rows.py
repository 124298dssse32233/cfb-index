"""Clean fanbase_mood_weekly for the offseason weeks to ONLY the fresh football-only
computed rows (honest mood). Removes stale computed rows (teams that only qualified
on now-excluded city data) + editorial n=0 seed placeholders. Backs up first.
REVERSIBLE: restore from fanbase_mood_weekly_backup_preclean.
"""
import sqlite3, time
db = sqlite3.connect("cfb_rankings.db", timeout=60)
db.execute("pragma busy_timeout=60000")
MONDAYS = ('2026-01-12','2026-01-19','2026-01-26','2026-02-02','2026-02-09',
           '2026-02-23','2026-03-02','2026-03-09','2026-03-23','2026-04-06','2026-04-22')
FRESH_CUTOFF = '2026-06-09 20:00'
ph = ','.join('?'*len(MONDAYS))

# 1. backup (idempotent: replace)
db.execute("drop table if exists fanbase_mood_weekly_backup_preclean")
db.execute("create table fanbase_mood_weekly_backup_preclean as select * from fanbase_mood_weekly")
n_backup = db.execute("select count(*) from fanbase_mood_weekly_backup_preclean").fetchone()[0]

before = db.execute(f"select count(*) from fanbase_mood_weekly where week_start_date in ({ph})", MONDAYS).fetchone()[0]
# 2. delete stale-computed + editorial seeds for offseason weeks; keep fresh computed
cur = db.execute(
    f"""delete from fanbase_mood_weekly
        where week_start_date in ({ph})
          and not (source='computed' and ingested_at >= ?)""",
    (*MONDAYS, FRESH_CUTOFF))
db.commit()
after = db.execute(f"select count(*) from fanbase_mood_weekly where week_start_date in ({ph})", MONDAYS).fetchone()[0]
teams = db.execute(f"select count(distinct team_id) from fanbase_mood_weekly where week_start_date in ({ph})", MONDAYS).fetchone()[0]
print(f"backup rows: {n_backup} (fanbase_mood_weekly_backup_preclean)")
print(f"offseason mood rows: {before} -> {after}  (deleted {before-after})")
print(f"distinct teams now: {teams}")
db.close()
