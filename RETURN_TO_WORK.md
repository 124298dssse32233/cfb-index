# 🏈 RETURN TO WORK — CFB Index Site
**Session Date:** 2026-05-18
**Status:** READY TO RESUME
**Can shut down computer:** ✅ YES — All work saved

---

## 📋 QUICK START (When You Return)

1. Open Claude Code
2. Navigate to project: `C:\Users\kevin\Downloads\Sports Website`
3. Ask Claude: "Please continue from where we left off per RETURN_TO_WORK.md"

---

## ✅ WHAT WAS ACCOMPLISHED TODAY

### 1. World-Class Stats Display — DEPLOYED ✅
**Status:** LIVE on Vercel
**URL:** https://wonderful-margulis-8ec96b-kevins-projects-9307a84f.vercel.app

**Files Modified:**
- `src/cfb_rankings/config.py` — Set `USE_WORLD_CLASS_STATS = "true"` (line 346)
- `src/cfb_rankings/theme/player_stats.py` — Fixed import error
- `src/cfb_rankings/theme/__init__.py` — Updated exports

**What's Live:**
- ✅ Card-based percentile layout on player pages
- ✅ Sortable stat tables (click headers)
- ✅ Percentile rankings (e.g., "#13/193 94th percentile")
- ✅ Mobile-responsive tables
- ✅ Stat summary tiles
- ✅ 17,832 player pages built
- ✅ 17 profiled team pages with new design

**Example Player Page:** https://wonderful-margulis-8ec96b-kevins-projects-9307a84f.vercel.app/players/kevin-jennings-12879.html

---

### 2. Data Ingestion Completed ✅

| Season | Games | Game Stats | Season Stats | Rosters | Status |
|--------|-------|-----------|--------------|---------|--------|
| 2020 | 563 | 260,404 | 8,370 | 1,778 | ✅ COMPLETE |
| 2021 | 2,408 | 420,283 | **0** | **0** | ⚠️ NEEDS ROSTERS |
| 2022 | 957 | 93,243 | **0** | **0** | ⚠️ NEEDS ROSTERS |
| 2023 | 0 | 0 | **0** | **0** | ❌ EMPTY |
| 2024 | 3,747 | 429,338 | 44,147 | 16,221 | ✅ COMPLETE |

---

### 3. Deployments to Vercel ✅

**Production URL:** https://wonderful-margulis-8ec96b-kevins-projects-9307a84f.vercel.app

**Latest Deployment ID:** `dpl_G6mVf81FLMxSaeahVwV994yMUsnB`

---

## 🎯 WHAT'S LEFT TO DO

### Priority 1: Complete 2021-2023 Data (CRITICAL)

**Estimated Time:** 6-9 hours (can run overnight)

**Commands to Run (in order):**

```bash
# ===== 2021 SEASON =====
# Step 1: Load rosters (REQUIRED before season stats)
py manage.py ingest-cfbd-preseason --season 2021 --classification fbs

# Step 2: Run team models (REQUIRED before Heisman)
py manage.py run-models --season 2021 --through-week 16

# Step 3: Run Heisman model (computes player season stats)
py manage.py run-heisman-model --season 2021 --through-week 16

# ===== 2022 SEASON =====
# Step 1: Complete game stats backfill (only 93K loaded, should be ~400K+)
py manage.py backfill-game-player-stats --start-season 2022 --end-season 2022 --classification fbs

# Step 2: Load rosters
py manage.py ingest-cfbd-preseason --season 2022 --classification fbs

# Step 3: Run team models
py manage.py run-models --season 2022 --through-week 16

# Step 4: Run Heisman model
py manage.py run-heisman-model --season 2022 --through-week 16

# ===== 2023 SEASON =====
# Step 1: Load all game data
py manage.py backfill-game-player-stats --start-season 2023 --end-season 2023 --classification fbs

# Step 2: Load rosters
py manage.py ingest-cfbd-preseason --season 2023 --classification fbs

# Step 3: Run team models
py manage.py run-models --season 2023 --through-week 16

# Step 4: Run Heisman model
py manage.py run-heisman-model --season 2023 --through-week 16
```

**Verification:**
```bash
py manage.py audit-data-coverage
# Check that 2021-2023 have >0 in "Player Season Stats" column
```

---

### Priority 2: Fix Database Issues

**Issue 1: Recruiting Data FOREIGN KEY Constraint**
- **Error:** `sqlite3.IntegrityError: FOREIGN KEY constraint failed`
- **Location:** `src/cfb_rankings/ingest/cfbd.py` line 868
- **Impact:** Cannot load recruiting data
- **Fix:** Add player record creation before recruiting insert, or use `INSERT OR IGNORE`

**Issue 2: Database Locking During Concurrent Writes**
- **Error:** `database is locked` / `attempt to write a readonly database`
- **Current State:** Retry logic works (6 attempts), but causes delays
- **Fix:** Run ingestions sequentially, not in parallel

---

### Priority 3: Advanced Metrics (Future Enhancement)

**NOT IMPLEMENTED:**
- EPA/Play (Expected Points Added)
- Success Rate (% positive EPA plays)
- CPOE (Completion Percentage Over Expected)
- AY/A (Air Yards per Attempt)

**Implementation Required:**
1. Create `src/cfb_rankings/ingest/cfbd_advanced.py` client module
2. Ingest from CFBD `/player/advanced` endpoint
3. Calculate percentiles against FBS QB peer group
4. Wire into player page rendering

**Reference:** `WORLD_CLASS_STATS_IMPLEMENTATION_PLAN.md` Phase 1A2

---

## 🔧 HOW TO VERIFY SUCCESS

### Check 1: Data Coverage
```bash
py manage.py audit-data-coverage
```
**Expected Result:** 2021-2023 should show >0 in "Player Season Stats"

### Check 2: Player Page Test
```bash
py manage.py build-site
# Then open: output/site/players/caleb-williams-12879.html
```
**Expected Result:** Player page shows 2021-2023 stats with percentile bars

### Check 3: Deploy to Vercel
```bash
vercel --prod
```
**Expected Result:** Site deploys successfully

---

## 📜 FULL OVERNIGHT SCRIPT

Save as `overnight_ingest.bat` and run before bed:

```bat
@echo off
echo ===================================================
echo CFB INDEX OVERNIGHT DATA INGESTION
echo Started: %date% %time%
echo ===================================================
echo.
echo IMPORTANT: Do NOT close this window or put computer to sleep!
echo Set Power Settings to: Sleep = NEVER
echo ===================================================
echo.

cd /d "C:\Users\kevin\Downloads\Sports Website"

echo.
echo [%TIME%] ========== 2021 SEASON ==========
echo.
echo [%TIME%] Loading 2021 rosters...
py manage.py ingest-cfbd-preseason --season 2021 --classification fbs
if %ERRORLEVEL% NEQ 0 echo [%TIME%] ERROR: 2021 rosters failed!

echo.
echo [%TIME%] Running 2021 team models...
py manage.py run-models --season 2021 --through-week 16
if %ERRORLEVEL% NEQ 0 echo [%TIME%] ERROR: 2021 team models failed!

echo.
echo [%TIME%] Running 2021 Heisman model...
py manage.py run-heisman-model --season 2021 --through-week 16
if %ERRORLEVEL% NEQ 0 echo [%TIME%] ERROR: 2021 Heisman failed!

echo.
echo [%TIME%] ========== 2022 SEASON ==========
echo.
echo [%TIME%] Backfilling 2022 game stats...
py manage.py backfill-game-player-stats --start-season 2022 --end-season 2022 --classification fbs
if %ERRORLEVEL% NEQ 0 echo [%TIME%] ERROR: 2022 game stats failed!

echo.
echo [%TIME%] Loading 2022 rosters...
py manage.py ingest-cfbd-preseason --season 2022 --classification fbs
if %ERRORLEVEL% NEQ 0 echo [%TIME%] ERROR: 2022 rosters failed!

echo.
echo [%TIME%] Running 2022 team models...
py manage.py run-models --season 2022 --through-week 16
if %ERRORLEVEL% NEQ 0 echo [%TIME%] ERROR: 2022 team models failed!

echo.
echo [%TIME%] Running 2022 Heisman model...
py manage.py run-heisman-model --season 2022 --through-week 16
if %ERRORLEVEL% NEQ 0 echo [%TIME%] ERROR: 2022 Heisman failed!

echo.
echo [%TIME%] ========== 2023 SEASON ==========
echo.
echo [%TIME%] Backfilling 2023 game stats...
py manage.py backfill-game-player-stats --start-season 2023 --end-season 2023 --classification fbs
if %ERRORLEVEL% NEQ 0 echo [%TIME%] ERROR: 2023 game stats failed!

echo.
echo [%TIME%] Loading 2023 rosters...
py manage.py ingest-cfbd-preseason --season 2023 --classification fbs
if %ERRORLEVEL% NEQ 0 echo [%TIME%] ERROR: 2023 rosters failed!

echo.
echo [%TIME%] Running 2023 team models...
py manage.py run-models --season 2023 --through-week 16
if %ERRORLEVEL% NEQ 0 echo [%TIME%] ERROR: 2023 team models failed!

echo.
echo [%TIME%] Running 2023 Heisman model...
py manage.py run-heisman-model --season 2023 --through-week 16
if %ERRORLEVEL% NEQ 0 echo [%TIME%] ERROR: 2023 Heisman failed!

echo.
echo [%TIME%] ========== BUILD AND DEPLOY ==========
echo.
echo [%TIME%] Building site...
py manage.py build-site
if %ERRORLEVEL% NEQ 0 echo [%TIME%] ERROR: Build failed!

echo.
echo [%TIME%] Deploying to Vercel...
vercel --prod
if %ERRORLEVEL% NEQ 0 echo [%TIME%] ERROR: Deploy failed!

echo.
echo ===================================================
echo INGESTION COMPLETE: %date% %time%
echo ===================================================
echo.
echo Check data coverage with: py manage.py audit-data-coverage
echo.
pause
```

**Before Running:**
1. Set Power & Sleep settings → Sleep = "Never"
2. Keep laptop plugged in
3. Close browser, IDE, other apps
4. Run as Administrator if needed

**In Morning:**
1. Check Command Prompt for errors
2. Run `py manage.py audit-data-coverage`
3. Verify 2021-2023 have season stats
4. Visit live site to confirm

---

## 📊 CURRENT LIVE SITE DATA

**URL:** https://wonderful-margulis-8ec96b-kevins-projects-9307a84f.vercel.app

**Available Now:**
- ✅ 2020: 563 games, 260K game stats, 8K season stats
- ✅ 2024: 3,747 games, 429K game stats, 44K season stats
- ✅ World-class stats UI (percentile bars, sortable tables)
- ✅ 17,832 player pages
- ✅ 17 profiled team pages

**Missing (will add tonight):**
- ❌ 2021 season stats (game stats exist, needs rosters)
- ❌ 2022 season stats (partial game stats, needs rosters)
- ❌ 2023 everything (empty)

---

## 🗂️ FILES MODIFIED TODAY (Git Status)

**Modified:**
- `src/cfb_rankings/config.py` — USE_WORLD_CLASS_STATS = "true"
- `src/cfb_rankings/theme/player_stats.py` — Fixed import
- `src/cfb_rankings/theme/__init__.py` — Updated exports
- `src/cfb_rankings/reporting.py` — World-class stats integration

**Generated (don't commit):**
- `output/site/` — Entire built site
- `.vercel/` — Vercel deployment files
- `.claude-octopus/` — Octopus workflow files

---

## 🚨 KNOWN ISSUES

### Issue 1: Recruiting Data Blocked
- **Symptom:** FOREIGN KEY constraint failed
- **Impact:** No recruiting data loaded
- **Fix Needed:** Modify `cfbd.py` line 868

### Issue 2: 2021-2023 No Season Stats
- **Symptom:** Player pages show "No stats available"
- **Cause:** No rosters loaded → can't match players
- **Fix:** Run `ingest-cfbd-preseason` for each season

### Issue 3: 2022 Incomplete Game Stats
- **Symptom:** Only 93K game stats (should be 400K+)
- **Cause:** Backfill didn't complete
- **Fix:** Re-run `backfill-game-player-stats` for 2022

---

## 📝 CHECKLIST FOR NEXT SESSION

- [ ] Run overnight ingest script OR complete 2021-2023 manually
- [ ] Verify data coverage: `py manage.py audit-data-coverage`
- [ ] Check player pages show 2021-2023 stats
- [ ] Build site: `py manage.py build-site`
- [ ] Deploy to Vercel: `vercel --prod`
- [ ] Test live site with multiple player pages
- [ ] (Optional) Fix recruiting FOREIGN KEY issue
- [ ] (Optional) Implement advanced metrics (EPA, CPOE, etc.)

---

## 🎯 SUCCESS CRITERIA

**Completed When:**
1. ✅ World-class stats UI is live (DONE)
2. ✅ 2020 & 2024 have full data (DONE)
3. ⬜ 2021 has season stats (TONIGHT)
4. ⬜ 2022 has season stats (TONIGHT)
5. ⬜ 2023 has season stats (TONIGHT)
6. ⬜ All seasons deployed to Vercel (TONIGHT)

---

## 🚀 NEW: GitHub Actions Option (Run While You Sleep!)

**⭐ RECOMMENDED:** Use GitHub Actions instead of running locally!

### Why Use GitHub Actions?
- ✅ Runs on GitHub's servers (FREE)
- ✅ Your computer can be OFF
- ✅ Does everything: rosters, stats, models, deploy
- ✅ Takes 3-6 hours automatically
- ✅ Uploads database artifact when done

### How to Trigger (Easy Method):

1. **Go to GitHub:** https://github.com/your-username/your-repo/actions

2. **Find workflow:** "backfill-full-history"

3. **Click "Run workflow"**

4. **Configure:**
   - start_season: `2021` (or `2020` for more history)
   - end_season: `2023`
   - skip_reddit: ✅ checked (saves 2 hours)
   - skip_player_stats: ☐ unchecked
   - skip_models: ☐ unchecked

5. **Click "Run workflow"**

6. **Go to sleep!** ☁️

7. **Morning:** Check Actions tab for completion

### Alternative: Command Line

```bash
# Install GitHub CLI if needed
winget install GitHub.cli

# Trigger the workflow
gh workflow run backfill_full_history.yml \
  -f start_season=2021 \
  -f end_season=2023 \
  -f skip_reddit=true
```

### What Happens Automatically:

1. Downloads latest database
2. Loads rosters for 2021-2023
3. Backfills all games and stats
4. Runs team models
5. Runs Heisman model (computes season stats)
6. Builds site
7. Triggers deploy to Vercel
8. Uploads database artifact

### Monitor Progress:

```bash
# Watch the workflow run
gh run list --workflow=backfill_full_history.yml

# Watch live logs
gh run watch
```

---

## 💡 TIPS FOR CLAUDE NEXT SESSION

**When you return, say:**
> "Please continue from where we left off per RETURN_TO_WORK.md. I need to complete the 2021-2023 data ingestion."

**Claude will:**
1. Read this file
2. Check current data coverage
3. Resume ingestion commands
4. Verify and deploy

**If something breaks:**
> "Check the overnight ingest log and tell me what failed. Fix it and continue."

---

## 📞 EMERGENCY ROLLOVER

**If live site is broken:**
```bash
# Check current deployment
vercel ls

# Rollback to previous working deployment
vercel rollback <deployment-id>
```

**If database is corrupted:**
```bash
# Database is at: cfb_rankings.db
# Backup is: cfb_rankings.db.backup (if exists)
# Restore: cp cfb_rankings.db.backup cfb_rankings.db
```

---

## ✅ YOU ARE SAFE TO SHUT DOWN

**All work is saved:**
- ✅ Code changes in git
- ✅ Database commits are atomic
- ✅ Live site is deployed on Vercel
- ✅ This document has all context

**When you return:**
1. Open Claude Code
2. Navigate to project folder
3. Ask Claude to continue from RETURN_TO_WORK.md

**Good luck! 🏈**
