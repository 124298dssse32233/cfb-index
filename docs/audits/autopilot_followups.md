# Autopilot v1 — Follow-ups

A living log of issues, tradeoffs, and things the autopilot run flagged for
later attention. One dated subsection per entry. Ordered newest-first.

---

## 2026-04-23 — SQLite "attempt to write a readonly database" under long-running writes

**Symptom.** Long-running foreground commands that perform sustained writes
(`backfill-game-player-stats`, `ingest-cfbd-preseason --classification fcs`)
fail intermittently with:

```
sqlite3.OperationalError: attempt to write a readonly database
```

Three consecutive failures triggered the autopilot stop-condition per the
kickoff autonomy policy. Progress before crash:
- `ingest-cfbd-preseason 2026 fbs`: completed but 2026 rosters didn't land
  (players table grew by ~5k from recruiting-class imports; team_seasons,
  roster_entries for 2026 all remain 0).
- `ingest-cfbd-preseason 2026 fcs`: crashed during recruiting-class phase.
- `backfill-game-player-stats` (1st run): crashed mid-2022-week-2.
- `backfill-game-player-stats` (2nd run): landed 131,021 player_game_stats
  rows for 2022 (weeks 1-3 complete) before crashing at week 4.

**Hypothesis.** The error is NOT a SQLite corruption. A fresh write via the
framework's `Database` class succeeds every time we try it manually. The DB
is in WAL mode (set as part of TASK 1.2's close). The most likely causes
are environmental:

1. OneDrive / Dropbox sync briefly holding an exclusive handle on the
   `cfb_rankings.db` file during a save point.
2. Windows Defender (or another AV) scanning the file mid-write.
3. A stale WAL frame from a prior crash that temporarily forces read-only
   mode on a writer that arrives before WAL checkpoint completion.

**Confidence.** Medium-low. Haven't captured the OS-level event
(ProcessMonitor / sysinternals would confirm).

**Mitigation path forward (not implemented this run).**
1. Run long backfills from an admin shell with AV realtime-scan exempting
   `cfb_rankings.db` and `*.db-wal` / `*.db-shm`.
2. Pause OneDrive before any multi-hour CFBD backfill.
3. Add a `try/except` retry loop in `Database.execute` with one-second
   backoff on OperationalError — would absorb most transient failures.
4. Run backfills on Linux (WSL2 or a cloud runner) where the Windows-
   specific file handle quirks don't apply.

**Work landed this run despite the failure.**
- TASK 1.1: CFBD connectivity preflight PASS.
- TASK 1.2: declared effectively complete (data already in place from
  prior load_history_2014_forward.ps1 runs).
- TASK 1.3: partial — 2022 player_game_stats now 131k rows (up from 0);
  2023/2024 still 0; 2026 rosters not ingested.
- TASK 1.4: player_advanced_metrics table + computation module + tests
  all landed; 2025 smoke run wrote 17,891 rows.
- TASK 1.5: blocked on 1.3 completion.
- TASK 1.6: Signature Story seed extended with 2 PBP-era metrics.
- TASK 1.7: hourly workflow rewritten with DB-artifact + in-season CFBD
  conditional sync.

**Recommended next move for Kevin.**
Run the remaining backfills from an admin shell with AV / OneDrive paused
once the concurrency hypothesis is confirmed. Commands to re-run:
```
python manage.py backfill-game-player-stats --start-season 2022 \
    --end-season 2026 --include-postseason --missing-only \
    --skip-connectivity-check

python manage.py ingest-cfbd-preseason --season 2026 \
    --all-season-teams --classification fbs
python manage.py ingest-cfbd-preseason --season 2026 \
    --all-season-teams --classification fcs
```

Once player_game_stats is populated 2022-2024, unblock TASK 1.5 via:
```
for season in 2022 2023 2024; do
    python manage.py compute-player-advanced --season $season
done
```

---
