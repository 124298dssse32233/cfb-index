# Tomorrow's Implementation Plan — CFB Index
**Date:** 2026-05-19 (upon waking)
**Status:** Workflows triggered and running on GitHub!

---

## 🎉 EXCELLENT NEWS — 3 Workflows Already Running!

**Started at:** 2026-05-19 04:08 UTC
**Your computer can be OFF — GitHub runs these!**

### Active Workflow Runs:

| Workflow | Run ID | Est. Time | Status |
|----------|--------|-----------|--------|
| **Backfill 2021-2023 + Reddit** | [26075592697](https://github.com/124298dssse32233/cfb-index/actions/runs/26075592697) | 4-7 hours | 🔄 Running |
| **World-Class Enrich** | [26075598980](https://github.com/124298dssse32233/cfb-index/actions/runs/26075598980) | 2-4 hours | 🔄 Running |
| **Reddit Deep 2026 Offseason** | [26075605485](https://github.com/124298dssse32233/cfb-index/actions/runs/26075605485) | 2-5 hours | 🔄 Running |

**Total estimated time:** 8-16 hours (they run in parallel on GitHub's servers)

---

## WHAT THESE WORKFLOWS DO:

### 1. Backfill 2021-2023 + Reddit (Overnight)
- ✅ Load rosters for 2021, 2022, 2023
- ✅ Backfill all games and player stats
- ✅ Run team models (required for Heisman)
- ✅ Run Heisman model (computes player season stats!)
- ✅ Game-level player stats
- ✅ Reddit offseason conversations (weeks 21-31)
- ✅ Fan intelligence (classification, mood, cohorts)
- ✅ Auto-triggers site build + deploy when complete

### 2. World-Class Enrich
- ✅ Wire: ingest → editorial → render
- ✅ Daily edition: generate + render
- ✅ Mailbag: curate → generate answers → render
- ✅ Reactions: auto-generate + render
- ✅ Team page AI: narratives, chronicle, savant, rivalry
- ✅ Render all 17 profiled team pages
- ✅ Retro offseason pages
- ✅ Player mood (weekly + season)
- ✅ Wiki awards scrape + import (2014-2025)
- ✅ Canon lists: 100 Best Players, 50 Defining Games, 25 Best Coaches
- ✅ Best Calls weekly editorial
- ✅ Hub intelligence + pulse themes
- ✅ Editions cover essays (Pattern C)
- ✅ Site refresh: storylines, methodology, homepage
- ✅ World-Class enhancement layer (CSS+JS+HTML inject)
- ✅ Push to published branch (auto-deploys to Vercel)

### 3. Reddit Deep 2026 Offseason
- ✅ Deep Reddit collection across /r/CFB + team subs + city subs
- ✅ Comments on every post with ≥1 reply
- ✅ Fan-intelligence bridge tables
- ✅ Weekly mood + cohort computation
- ✅ Fanbase classification
- ✅ Triggers publish-site when complete

---

## FIRST THING TOMORROW: Check Status

### Option A: Via Browser
1. Go to: https://github.com/124298dssse32233/cfb-index/actions
2. Look for the 3 runs at the top
3. Click each to see detailed logs

### Option B: Via Command Line
```bash
# Check status
gh run list --limit 10

# Watch a specific run
gh run watch 26075592697  # backfill
# or
gh run watch 26075598980  # enrich
# or
gh run watch 26075605485  # reddit
```

---

## AFTER WORKFLOWS COMPLETE:

### 1. Verify Database Coverage

```bash
cd "C:\Users\kevin\Downloads\Sports Website"
python manage.py audit-data-coverage
```

**Expected Results:**
| Season | Games | Rosters | Season Stats | Game Stats |
|--------|-------|---------|--------------|------------|
| 2020 | 563 | 1,778 | 8,370 | 260,404 |
| 2021 | 2,408 | ~5,000+ | ~10,000+ | 420,283 |
| 2022 | ~1,000 | ~5,000+ | ~10,000+ | ~400,000 |
| 2023 | ~1,000 | ~5,000+ | ~10,000+ | ~400,000 |
| 2024 | 3,747 | 16,221 | 44,147 | 429,338 |

### 2. Verify Live Site

**Production URL:** https://wonderful-margulis-8ec96b-kevins-projects-9307a84f.vercel.app

**Test Player Pages:**
- https://wonderful-margulis-8ec96b-kevins-projects-9307a84f.vercel.app/players/caleb-williams-12879.html
  - Should show 2021, 2022, 2023, 2024 stats
  - Percentile bars for all seasons
  - Sortable stat tables

**Test Team Pages:**
- https://wonderful-margulis-8ec96b-kevins-projects-9307a84f.vercel.app/programs/alabama.html
  - AI narratives
  - Chronicle cards
  - Season arc
  - Rivalry head-to-head

**Test New Surfaces:**
- /wire/ — Daily wire with editorial
- /mailbag/ — Mailbag Q&A
- /editions/ — Daily editions
- /canon/ — Canon lists (100 Best Players, etc.)
- /best-calls/ — Weekly editorial
- /retro/ — Retro offseason pages

---

## IF ANY WORKFLOW FAILED:

### Check Logs for Errors
1. Go to the failed workflow run
2. Click on the failed step
3. Read the error message

### Common Issues + Fixes:

**"CFBD_API_KEY not found"**
- Add secret in GitHub repo Settings → Secrets → Actions
- Name: `CFBD_API_KEY`
- Value: Your CollegeFootballData.com API key

**"ANTHROPIC_API_KEY not found"**
- Add secret: `ANTHROPIC_API_KEY`
- Value: Your Anthropic API key

**"REDDIT_CLIENT_ID not found"**
- Add secrets: `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USER_AGENT`
- Get from: https://www.reddit.com/prefs/apps

**Database lock / timeout**
- Usually transient, retry the workflow
- Check for concurrent runs (cancel conflicting runs)

**Out of memory / timeout**
- GitHub Actions has 6-hour timeout per job
- If hit, split the workload (e.g., run one season at a time)

---

## FALLBACK: Manual Ingestion (If GitHub Actions Completely Failed)

If GitHub Actions aren't working at all, run locally:

```bash
cd "C:\Users\kevin\Downloads\Sports Website"

# 2021 season
python manage.py ingest-cfbd-preseason --season 2021 --classification fbs
python manage.py run-models --season 2021 --through-week 16
python manage.py run-heisman-model --season 2021 --through-week 16

# 2022 season
python manage.py backfill-game-player-stats --start-season 2022 --end-season 2022 --classification fbs
python manage.py ingest-cfbd-preseason --season 2022 --classification fbs
python manage.py run-models --season 2022 --through-week 16
python manage.py run-heisman-model --season 2022 --through-week 16

# 2023 season
python manage.py backfill-game-player-stats --start-season 2023 --end-season 2023 --classification fbs
python manage.py ingest-cfbd-preseason --season 2023 --classification fbs
python manage.py run-models --season 2023 --through-week 16
python manage.py run-heisman-model --season 2023 --through-week 16

# Build and deploy
python manage.py build-site
vercel --prod
```

---

## OPTIONAL: Additional Workflows Available

These run on schedules but can be triggered manually:

| Workflow | What It Does | When to Run |
|----------|--------------|-------------|
| `ingest_weekly` | Spotify charts, cohort aggregation, rebuild site | Weekly (Mondays) |
| `recruiting_pulse` | Refresh Recruit Watch board | Daily (May-Aug only) |
| `monday_mood_map` | Generate weekly mood map | Weekly (Mondays) |
| `digest_weekly` | Weekly digest | Weekly |
| `publish_edition_weekly` | Publish weekly edition | Weekly |
| `compute_full_pass` | Full fan intel computation | As needed |
| `kickoff_countdown` | Countdown to kickoff season | Daily (Aug-Dec) |
| `mailbag-friday-09am-et` | Generate mailbag | Fridays |

**To trigger any:**
```bash
gh workflow run <workflow_name>.yml
```

---

## DATA COVERAGE SUMMARY (After Workflows Complete)

### Core Stats (Player/Team)
- ✅ 2020-2024 games: ~8,600+ total
- ✅ 2020-2024 player game stats: ~1.5M+ total
- ✅ 2020-2024 player season stats: ~120K+ total
- ✅ 2020-2024 rosters: ~45K+ total entries

### Fan Intelligence
- ✅ Reddit conversations (2021-2024)
- ✅ Fanbase mood (weekly, 8-week rolling)
- ✅ Fanbase cohorts (weekly)
- ✅ Player sentiment
- ✅ Predictive claims + outcomes

### AI-Generated Content
- ✅ Team narratives (17 profiled programs)
- ✅ Chronicle cards
- ✅ Season arcs
- ✅ Rivalry head-to-head
- ✅ Daily editions
- ✅ Mailbag Q&A
- ✅ Reactions
- ✅ Wire editorial
- ✅ Best Calls
- ✅ Canon lists

### Awards + Honors
- ✅ Wikipedia awards scrape (2014-2025)
- ✅ Heisman winners
- ✅ All-Americans
- ✅ All-Conference

---

## CHECKLIST FOR TOMORROW

- [ ] Check GitHub Actions status
- [ ] Verify all 3 workflows completed successfully
- [ ] Run `python manage.py audit-data-coverage`
- [ ] Test live player pages (2021-2023 stats visible)
- [ ] Test live team pages (AI narratives visible)
- [ ] Browse new surfaces (/wire/, /mailbag/, /editions/, /canon/)
- [ ] Confirm Vercel deployed latest version

---

## SUCCESS CRITERIA

**Complete when:**
1. ✅ All 3 workflows show "success" status
2. ✅ 2020-2024 all have season stats > 0
3. ✅ Player pages show percentile bars for all seasons
4. ✅ Team pages show AI-generated content
5. ✅ New editorial surfaces are live
6. ✅ Vercel shows latest deployment

---

## LIVE LINKS TO CHECK TOMORROW:

**Player Pages:**
- https://wonderful-margulis-8ec96b-kevins-projects-9307a84f.vercel.app/players/caleb-williams-12879.html
- https://wonderful-margulis-8ec96b-kevins-projects-9307a84f.vercel.app/players/bryce-young-12880.html
- https://wonderful-margulis-8ec96b-kevins-projects-9307a84f.vercel.app/players/stetson-bennett-12881.html

**Team Pages:**
- https://wonderful-margulis-8ec96b-kevins-projects-9307a84f.vercel.app/programs/alabama.html
- https://wonderful-margulis-8ec96b-kevins-projects-9307a84f.vercel.app/programs/georgia.html
- https://wonderful-margulis-8ec96b-kevins-projects-9307a84f.vercel.app/programs/ohio-state.html

**Editorial:**
- https://wonderful-margulis-8ec96b-kevins-projects-9307a84f.vercel.app/wire/
- https://wonderful-margulis-8ec96b-kevins-projects-9307a84f.vercel.app/editions/
- https://wonderful-margulis-8ec96b-kevins-projects-9307a84f.vercel.app/canon/

---

**Good luck! See you in the morning. 🏈💤**

All workflows are running autonomously on GitHub. Your computer can be OFF.
Total estimated time: 8-16 hours (parallel execution).
