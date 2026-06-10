# GDELT via BigQuery — one-time setup (plain-language, copy-paste)

_Written for Kevin, 2026-06-10. Goal: replace 138 rate-limited GDELT API calls
with **one** cheap BigQuery query per day. Cost stays **$0** on Google's free
BigQuery sandbox (no credit card, 1 TB of free queries/month — we use a tiny
fraction of that)._

## What you're setting up and why

GDELT (a free global news database) is also published on Google BigQuery. Instead
of asking GDELT's website 138 times a day (one per team — which got us rate-limited
with HTTP 429 errors), we ask BigQuery **once** and get every team's daily news
volume in a single query. BigQuery's free "sandbox" tier gives you 1 TB of query
scanning per month for free; our daily query scans well under 2 GB, so we'll use
maybe ~60 GB/month — comfortably free, forever.

The code is already written and **safe**: until you finish the steps below, the
adapter just skips itself (no errors, nothing breaks). It also has a hard
"max bytes billed" cap, so even a bug can never run up a bill.

---

## Step 1 — Create a free Google Cloud project

1. Go to **https://console.cloud.google.com/** and sign in with your Google account
   (kevinsherrin@gmail.com is fine).
2. If it asks you to agree to the Terms of Service, accept them. **Do NOT** set up
   a billing account — we want the free sandbox. If it ever pushes you toward
   "enable billing", just close that prompt; BigQuery sandbox works without it.
3. At the top, click the project dropdown → **New Project**.
   - Name it something like `cfb-index-gdelt`.
   - Click **Create**. Wait ~20 seconds.
4. Make sure the new project is selected in the top dropdown.
5. **Copy the Project ID** (it looks like `cfb-index-gdelt-462318` — NOT the display
   name). You'll paste it into `.env` later. To find it: project dropdown →
   it's the gray text under the project name, or Console home → "Project ID".

## Step 2 — Turn on the BigQuery API

1. In the search bar at the top, type **BigQuery API** and click it.
2. Click **Enable**. (If it says "Manage", it's already on — good.)

## Step 3 — Create a service account (a robot login for the box)

A service account is a non-human login our Windows box uses to run queries.

1. Search bar → **Service Accounts** (under "IAM & Admin").
2. Click **+ Create Service Account**.
   - Name: `cfb-gdelt-runner`
   - Click **Create and Continue**.
3. **Grant roles** (this is the permissions step). Add these two roles:
   - `BigQuery Job User`  (lets it run queries)
   - `BigQuery Data Viewer`  (lets it read the public GDELT data)
   Click **Continue**, then **Done**.

## Step 4 — Download the key file (the password, as a JSON file)

1. On the Service Accounts list, click the `cfb-gdelt-runner@...` account you just made.
2. Go to the **Keys** tab → **Add Key** → **Create new key** → choose **JSON** → **Create**.
3. Your browser downloads a file like `cfb-index-gdelt-462318-abc123.json`.
   This file is a password — treat it like one.
4. Move it into the repo under a **gitignored** folder so it never gets committed:
   - Create the folder `secrets\` in the repo root if it doesn't exist.
   - Move the downloaded `.json` into it and rename it to `gdelt-bq-key.json`, so the
     full path is:
     `C:\Users\User 1\Downloads\Sports Website\secrets\gdelt-bq-key.json`

   > `secrets/` is already in `.gitignore` (verified) so the key will not be committed.
   > Double-check with: `git status --porcelain secrets` returns nothing.

## Step 5 — Tell the box where the key + project are

Open the repo's `.env` file and add these two lines (use YOUR project id from Step 1):

```
GOOGLE_APPLICATION_CREDENTIALS=secrets/gdelt-bq-key.json
GDELT_BQ_PROJECT=cfb-index-gdelt-462318
```

(`.env` is already loaded by every pipeline script, so nothing else to wire.)

## Step 6 — Install the BigQuery Python library (one command)

In a terminal in the repo root:

```powershell
.\.venv\Scripts\python.exe -m pip install google-cloud-bigquery
```

## Step 7 — Validate with a $0 dry run (no data written, no cost)

This checks auth + estimates how many bytes the real query would scan, **without
running it for real or writing anything**:

```powershell
$env:GDELT_BQ_DRY_RUN = "1"
.\.venv\Scripts\python.exe tools\run_adapter.py gdelt_volume_bq
Remove-Item Env:\GDELT_BQ_DRY_RUN
```

You want to see a log line like:
`gdelt_bq DRY RUN: would scan 0.4xx GB (cap 2.0 GB), window=3d, NNN aliases. No rows written.`

- If the GB number is **under 2.0**, you're good — run it for real (Step 8).
- If it's **over 2.0**, lower the window: `$env:GDELT_BQ_WINDOW_DAYS = "1"` and re-dry-run.
- If you see "skipped" / "credentials" / "not installed", re-check Steps 4–6.

## Step 8 — Run it for real once

```powershell
.\.venv\Scripts\python.exe tools\run_adapter.py gdelt_volume_bq
```

Expect: `gdelt_volume: status=ok rows=NNN` and a log line `gdelt_bq: NNN (team,day)
rows over 3d window; billed 0.4xx GB.`

That's the whole setup — **no script edits needed**. The daily `collect` job calls
`gdelt_volume`, which now auto-routes: the moment `GOOGLE_APPLICATION_CREDENTIALS`
is set it uses this fast BigQuery query for all 138 teams; before that it silently
used the old slow per-team API. So you don't have to touch `collect.ps1` at all.

---

## How to watch your free-tier usage (optional peace of mind)

- BigQuery Console → **left menu → Monitoring**, or the project's
  **BigQuery → Query history**, shows bytes processed. The free tier is 1 TiB/month.
- Our daily run is ≤ ~2 GB, so ≈ 60 GB/month worst case — about 6% of the free tier.

## Knobs (env vars, all optional)

| Env var | Default | What it does |
|---|---|---|
| `GOOGLE_APPLICATION_CREDENTIALS` | (unset → adapter skips) | Path to the service-account JSON |
| `GDELT_BQ_PROJECT` | (from key file) | Your GCP project id |
| `GDELT_BQ_WINDOW_DAYS` | `3` | Rolling window of days to (re)pull. Smaller = fewer bytes |
| `GDELT_BQ_MAX_GB` | `2.0` | Hard cap on bytes billed. Query ERRORS rather than exceeding it |
| `GDELT_BQ_DRY_RUN` | (unset) | `1` = estimate bytes only, write nothing, $0 |

## Matching quality (where to tune later)

Per-team matching uses lowercase substring aliases against GDELT's organization
field. Curated, precise aliases live in `data/seeds/gdelt_team_aliases.json`
(nicknames + "university of X", with homonym guards so "Miami" doesn't match the
Dolphins). Teams not in that file fall back to their canonical name, and bare
ambiguous one-word names are skipped (logged) until you add a precise alias.
To improve a team's coverage, add an entry to that JSON — no code change needed.

## If you ever want to turn it off

Remove the two `.env` lines (or just `GOOGLE_APPLICATION_CREDENTIALS`). The adapter
goes back to skipping itself. The old per-team API adapter (`gdelt_volume`) still
exists as a manual fallback (`python tools\run_adapter.py gdelt_volume`).
