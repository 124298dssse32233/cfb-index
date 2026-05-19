# Missing Data Report — CFB Index Site
**Generated:** 2026-05-18
**Current Live URL:** https://wonderful-margulis-8ec96b-kevins-projects-9307a84f.vercel.app

---

## Executive Summary

| Data Type | Status | Coverage |
|-----------|--------|----------|
| **2020 Season** | 🟡 Partial | 563 games, 260K game stats, 8K season stats |
| **2021 Season** | 🔴 Incomplete | 2,408 games, 420K game stats, **0 season stats** |
| **2022 Season** | 🔴 Missing | 332 games, **0 player stats** |
| **2023 Season** | 🔴 Missing | No game data, only 2.5K transfer entries |
| **2024 Season** | 🟢 Good | 3,747 games, 429K game stats, 44K season stats |

---

## Critical Gaps (Blocker for User Experience)

### 1. 2021-2023 Player Season Stats (HIGH PRIORITY)
**Impact:** Player pages show "No season stats available" for 2021-2023

| Season | Games Loaded | Game Stats | Rosters | Season Stats | Issue |
|--------|--------------|-----------|---------|--------------|-------|
| 2021 | 2,408 ✓ | 420,283 ✓ | **0 ❌** | 0 ❌ | No rosters = can't compute season stats |
| 2022 | 332 (partial) | 0 ❌ | 0 ❌ | 0 ❌ | Game stats not loaded, no rosters |
| 2023 | 0 ❌ | 0 ❌ | 0 ❌ | 0 ❌ | No data loaded |

**Fix Required:**
```bash
# Load rosters first (enables player matching)
python manage.py ingest-cfbd-preseason --season 2021 --classification fbs
python manage.py ingest-cfbd-preseason --season 2022 --classification fbs
python manage.py ingest-cfbd-preseason --season 2023 --classification fbs

# Then run team models (required for Heisman model)
python manage.py run-models --season 2021 --through-week 16
python manage.py run-models --season 2022 --through-week 16
python manage.py run-models --season 2023 --through-week 16

# Then run Heisman model (computes player season stats)
python manage.py run-heisman-model --season 2021 --through-week 16
python manage.py run-heisman-model --season 2022 --through-week 16
python manage.py run-heisman-model --season 2023 --through-week 16
```

### 2. 2022 Game Player Stats (HIGH PRIORITY)
**Impact:** No week-by-week stats for 2022 season

**Fix Required:**
```bash
python manage.py backfill-game-player-stats --start-season 2022 --end-season 2022 --classification fbs
```

---

## Advanced Metrics (NOT IMPLEMENTED)

### 3. CFBD Tier 2 Advanced Stats (MEDIUM PRIORITY)
**Impact:** No EPA, Success Rate, CPOE, AY/A on player pages

**Missing Features:**
- EPA/Play (Expected Points Added)
- Success Rate (% positive EPA plays)
- CPOE (Completion Percentage Over Expected)
- AY/A (Air Yards per Attempt)

**Implementation Required:**
1. Create `src/cfb_rankings/ingest/cfbd_advanced.py` client module
2. Ingest from CFBD `/player/advanced` endpoint
3. Calculate percentiles against FBS QB peer group
4. Wire into player page rendering

**Estimated Effort:** 4-6 hours development + 2-3 hours ingestion time

---

## Missing Ancillary Data

### 4. Player Honors (LOW PRIORITY)
**Impact:** No award badges (All-American, All-Conference, etc.)

| Season | Honors Status |
|--------|---------------|
| 2020 | ❌ Not loaded |
| 2021 | ❌ Not loaded |
| 2022 | ❌ Not loaded |
| 2023 | ❌ Not loaded |
| 2024 | ❌ Not loaded |

**Fix Required:**
```bash
python manage.py import-player-honors --csv data/player_honors.csv
```

### 5. Heisman Votes (LOW PRIORITY)
**Impact:** No Heisman trophy voting data on player pages

**Status:** Not loaded for any season (requires manual data source)

---

## Database Issues to Fix

### 6. Recruiting Data FOREIGN KEY Constraint
**Error:** `sqlite3.IntegrityError: FOREIGN KEY constraint failed`

**Impact:** Cannot load recruiting data for 2020-2024

**Root Cause:** `player_recruiting_profiles` table references `players` table, but recruiting records reference player IDs that don't exist yet.

**Fix Required:** Modify `_ingest_player_recruiting()` in `src/cfb_rankings/ingest/cfbd.py` to insert missing player records first, or use `INSERT OR IGNORE` for foreign key violations.

### 7. Database Locking During Concurrent Writes
**Error:** `database is locked` / `attempt to write a readonly database`

**Impact:** Slow ingestion when multiple commands run simultaneously

**Current Mitigation:** Retry logic works (6 attempts with exponential backoff), but causes delays

**Fix Required:** Run ingestions sequentially, not in parallel

---

## Data Quality Issues

### 8. 2022 Incomplete Game Data
**Status:** Only 332 games loaded (should be ~1,000+ for full FBS season)

**Fix Required:** Run full CFBD week ingestion for 2022

---

## Historical Data (2014-2019)
**Status:** Not loaded

**Priority:** LOW (outside current 5-year window)

**Estimated Effort:** 8-10 hours ingestion time per season

---

## Can This Run Overnight With Computer Off?

### ❌ NO — Your computer must stay ON

**Why:**
- All ingestion scripts run **locally** on your machine
- CFBD API calls are made from `manage.py` running locally
- SQLite database writes happen locally
- No cloud/CI/CD pipeline exists for data ingestion

**If you close your laptop:**
- Python process stops
- Ingestion halts
- Partial data may be lost

### Overnight Run Checklist

If you want to run ingestions overnight:

1. **Keep computer awake:**
   - Windows: Set "Sleep" to "Never" in Power Settings
   - Keep laptop plugged in
   - Disable screen saver or set to long timeout

2. **Close other applications:**
   - Close browser, IDE, other memory-intensive apps
   - This prevents resource conflicts

3. **Run commands in sequence:**
   ```bash
   # 2021 season (2-3 hours)
   python manage.py ingest-cfbd-preseason --season 2021 --classification fbs
   python manage.py run-models --season 2021 --through-week 16
   python manage.py run-heisman-model --season 2021 --through-week 16

   # 2022 season (2-3 hours)
   python manage.py backfill-game-player-stats --start-season 2022 --end-season 2022 --classification fbs
   python manage.py ingest-cfbd-preseason --season 2022 --classification fbs
   python manage.py run-models --season 2022 --through-week 16
   python manage.py run-heisman-model --season 2022 --through-week 16

   # 2023 season (2-3 hours)
   python manage.py backfill-game-player-stats --start-season 2023 --end-season 2023 --classification fbs
   python manage.py ingest-cfbd-preseason --season 2023 --classification fbs
   python manage.py run-models --season 2023 --through-week 16
   python manage.py run-heisman-model --season 2023 --through-week 16
   ```

4. **Next morning:**
   ```bash
   # Rebuild and deploy
   python manage.py build-site
   vercel --prod
   ```

---

## Priority Order for Completion

### Phase 1 (Complete 2021-2023) — 6-9 hours overnight
1. Load 2021-2023 rosters
2. Complete 2022-2023 game stats backfill
3. Run team models for 2021-2023
4. Run Heisman model for 2021-2023
5. Rebuild and deploy

### Phase 2 (Advanced Metrics) — 4-6 hours development
1. Implement CFBD Tier 2 client
2. Ingest advanced stats
3. Wire into player pages
4. Deploy

### Phase 3 (Polish) — 2-4 hours
1. Import player honors
2. Fix recruiting FOREIGN KEY issue
3. Add stat definitions UI
4. Final deployment

---

## Estimated Total Time to Complete

| Task | Time | Can Run Overnight? |
|------|------|-------------------|
| 2021-2023 rosters + models | 6-9 hours | ✓ |
| 2022-2023 game stats | 3-4 hours | ✓ |
| Advanced metrics implementation | 4-6 hours | ❌ (dev work) |
| Advanced metrics ingestion | 2-3 hours | ✓ |
| Honors + bug fixes | 2-4 hours | Partial |

**Total:** ~21-32 hours of work/ingestion time
**Overnight-friendly:** ~15-20 hours (ingestion only)
**Dev-required:** ~6-12 hours

---

## Quick-Start Overnight Script

Save as `overnight_ingest.bat`:
```bat
@echo off
echo Starting overnight data ingestion...
echo DO NOT close this window or put computer to sleep!

cd /d "C:\Users\kevin\Downloads\Sports Website"

echo.
echo [%TIME%] Loading 2021 rosters...
py manage.py ingest-cfbd-preseason --season 2021 --classification fbs

echo.
echo [%TIME%] Running 2021 team models...
py manage.py run-models --season 2021 --through-week 16

echo.
echo [%TIME%] Running 2021 Heisman model...
py manage.py run-heisman-model --season 2021 --through-week 16

echo.
echo [%TIME%] Backfilling 2022 game stats...
py manage.py backfill-game-player-stats --start-season 2022 --end-season 2022 --classification fbs

echo.
echo [%TIME%] Loading 2022 rosters...
py manage.py ingest-cfbd-preseason --season 2022 --classification fbs

echo.
echo [%TIME%] Running 2022 team models...
py manage.py run-models --season 2022 --through-week 16

echo.
echo [%TIME%] Running 2022 Heisman model...
py manage.py run-heisman-model --season 2022 --through-week 16

echo.
echo [%TIME%] Backfilling 2023 game stats...
py manage.py backfill-game-player-stats --start-season 2023 --end-season 2023 --classification fbs

echo.
echo [%TIME%] Loading 2023 rosters...
py manage.py ingest-cfbd-preseason --season 2023 --classification fbs

echo.
echo [%TIME%] Running 2023 team models...
py manage.py run-models --season 2023 --through-week 16

echo.
echo [%TIME%] Running 2023 Heisman model...
py manage.py run-heisman-model --season 2023 --through-week 16

echo.
echo [%TIME%] Ingestion complete! Building site...
py manage.py build-site

echo.
echo [%TIME%] Deploying to Vercel...
vercel --prod

echo.
echo [%TIME%] ALL DONE!
pause
```

**To use:**
1. Save file in project directory
2. Right-click → "Run as administrator"
3. Keep computer awake all night
4. Check results in morning
