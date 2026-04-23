# CFB Index — How It Works (Beginner's One-Pager)

A plain-English explainer for what your system does, how the pieces fit, and where to look when something breaks. If you only read one doc, read this one.

---

## The 30-second version

Every night, a robot on your laptop wakes up, scrapes ~14 websites + APIs for anything new about college football, runs math on it, updates your website, and goes back to sleep. You do nothing.

That's it.

---

## The 3 jobs, by cadence

### 1. `CFBIndex-FanintelDaily` — every day at 09:00
**Script:** `scripts/daily_ingest.ps1`
**What it does:**
- Fetches today's data from Wikipedia, Google News, Kalshi, Polymarket, Bluesky, SeatGeek, YouTube, Spotify, beat-writer RSS feeds, campus newspaper RSS, school athletic RSS, Locked On podcasts, GDELT, and Google News per priority team (~14 total)
- Pulls Reddit r/CFB posts for the week (via Arctic Shift — free, no auth)
- **In-season only** (Aug 15 – Jan 20): also pulls fresh CFBD game + player data
- Runs the math: cohort sentiment, divergence, mood, rivalry ratios, lexicon trends, player mentions
- Regenerates the whole static site (~16,000 pages) so yours readers see today's numbers
**Runtime:** ~15 min
**Log:** `logs/fanintel_ingest_YYYY-MM-DD.log`

### 2. `CFBIndex-FanintelWeekly` — every Monday at 10:00
**Script:** `scripts/weekly_deep.ps1`
**What it does:**
- Deep Reddit pull for the prior week (pulls comment trees on the highest-signal posts)
- Re-classifies fanbase archetypes across the season
- Runs data-integrity audits
- Rebuilds the site
**Runtime:** ~45 min
**Log:** `logs/fanintel_weekly_YYYY-MM-DD.log`

### 3. `backfill_historical.ps1` — manual one-shot (you ran this once)
**What it did:** Walked every Monday from Jan 2022 → today, re-ran all aggregators against historical conversation data. Also pulled Reddit archives for each past season. Total ~2-4 hrs.
**When to re-run:** After any change to cohort weights, sentiment scoring, or anything else that retroactively changes what "the math" says. Safe to re-run anytime — everything upserts.

---

## What data is actually coming in

Think of three tiers based on how much we trust each source:

| Tier | Examples | What we can publish |
|---|---|---|
| **A** | Wikipedia pageviews, ticket prices, Kalshi prices, YouTube views, GDELT article counts | **Raw numbers OK** — these are facts |
| **B** | Reddit, Bluesky, beat-writer RSS, campus papers, boards (via Cowork) | **Aggregates with sample size** — never individual quotes as stats |
| **C** | Google Trends, TikTok observation, thin prediction markets | **Rank or trend only** — never a raw 0-100 number |
| **D** | Paul Finebaum, local sports radio, FB alumni pages | **Editorial citation only** — pull-quotes with a backlink |

There are 171 individual sources registered today (9 Tier A + 142 Tier B + 4 Tier C + 16 Tier D). You can see the full list on the live methodology page: `output/site/methodology/fan-intelligence.html`.

---

## The 4 key tables (where the interesting stuff lives)

| Table | What's in it |
|---|---|
| `conversation_documents` | Every post / article / tweet we've ever pulled. 7,000+ rows and growing. |
| `conversation_document_targets` | Which team each post is about + the VADER sentiment score |
| `source_observations` | Tier A numeric observations (Wikipedia views, Kalshi prices, etc.) |
| `team_cohort_week` | The big output: for each (team, cohort, week), effective sample size + sentiment + volume + confidence tier |
| `team_cohort_divergence_week` | How split a fanbase is this week across age/lens/geography cohorts |

---

## The critical floor rule

**Never publish a fake sentiment number.** Every cell in `team_cohort_week` follows this rule:

- `effective_n < 30` → UI shows "Awaiting Signal" (no number)
- `30 ≤ effective_n < 100` → publish with a small "thin sample" badge
- `effective_n ≥ 100` → publish with normal styling

The team-page "Cohort Signal" panel on every one of your 668 team pages reads from this table and honors this rule automatically. When you see an em-dash (—) instead of a number, it means there's enough volume but no sentiment data yet — we're being honest, not broken.

---

## Where each output lives

| You want | Open this |
|---|---|
| The published website | `output/site/index.html` |
| The methodology page | `output/site/methodology/fan-intelligence.html` |
| A team's cohort panel | `output/site/teams/<slug>.html` (scroll past mood card) |
| Recent ingestion stats | `python manage.py fanintel-status` |
| "Which feeds are broken" | `python manage.py scrape-health` |
| "Which URLs 403'd today" | `docs/audits/feed_validation_report.md` |

---

## When something goes wrong — 4 things to check in order

1. **Was the task triggered?** — Task Scheduler → "CFBIndex-FanintelDaily" → LastRunTime should be today.
2. **Did the script complete?** — `logs/fanintel_ingest_<today>.log` last line should be `==== daily_ingest end ====`. If it's cut off mid-run, the laptop probably slept.
3. **Did an adapter fail?** — `python manage.py scrape-health` surfaces error rows sorted worst-first.
4. **Did the site build?** — `output/site/` should have a fresh modified-time. If not, scroll the log for `build-site` errors.

### Common fixes
- **"No such table: games"** in Actions → your runner needs a DB; the CI workflow uses `init-db` first. On local runs this shouldn't happen.
- **HTTP 403 on a feed** → the outlet blocks our User-Agent. Leave it or find the real URL and update the seed YAML.
- **HTTP 404 on a feed** → URL is wrong. Update seed YAML, then run `python manage.py seed-feed-instances` + `python manage.py validate-feed-urls`.
- **A cohort cell shows em-dash (—)** → this is correct, not a bug. It means we have volume but no sentiment for that cell yet.

---

## How you'd change things

| I want to… | Edit this |
|---|---|
| Add a new priority team | `seeds/priority_teams.yaml` → `python manage.py seed-priority-teams && python manage.py seed-source-instances` |
| Fix a broken beat-writer URL | `seeds/beat_writer_feeds.yaml` → `python manage.py seed-feed-instances` |
| Add a new data source | `seeds/source_registry.yaml` + a new adapter in `src/cfb_rankings/ingest/sources/` → see `campus_news.py` as reference |
| Change cohort weights | `seeds/source_registry.yaml` → `python manage.py seed-source-registry` (reviewed annually per STRATEGY §4) |
| Run the daily job right now | `powershell -File scripts/daily_ingest.ps1` |
| Stop the daily robot | `powershell -Command "Unregister-ScheduledTask -TaskName CFBIndex-FanintelDaily -Confirm:$false"` |

---

## Rules of the road

1. **Never hand-edit `cfb_rankings.db`.** Write a CLI subcommand in `src/cfb_rankings/cli.py` instead.
2. **Never edit `output/site/*` by hand.** It's regenerated every night; your changes will vanish.
3. **Never commit `.env`.** It's gitignored for a reason. Your keys go in GitHub Secrets for anything CI-side.
4. **Don't publish a number below the floor.** The aggregator enforces this; don't go around it.
5. **Editorial is visibly editorial.** When something is a human pull-quote or a judgment call, the UI labels it.

---

## The strategic docs (if you want to go deeper)

- `FAN_INTEL_SOURCE_STRATEGY.md` — canonical source catalog + cohort weights + tier rules
- `FAN_INTEL_BUILD_PLAN.md` — the 8-week build plan (now mostly checked off)
- `docs/audits/fanintel_v1_audit.md` — full audit of what's live vs. deferred
- `docs/cowork_playbooks/` — the 5 weekly human-in-the-loop playbooks (Monday board sweep, TikTok, Google Trends, FB alumni glance, Thursday pulse + Sunday recap)
- `docs/editorial/monday_brief_template.md` — the prompt template for drafting weekly briefs
- `SESSION_LOG.md` — chronological log of every task that's ever shipped, with what changed and why

---

## TL;DR for someone who just opened this repo

> It's a college football rankings website. A cron job on Kevin's laptop runs every morning, pulls fresh data from ~14 places, does sentiment + cohort math on it, and rebuilds 16,000 HTML pages. The clever bit is honest sample sizes — every number has an effective-N floor, and if there isn't enough data, the UI says "Awaiting Signal" instead of making one up.
