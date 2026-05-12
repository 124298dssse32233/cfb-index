# scripts/backfill_historical.ps1
#
# ONE-SHOT retroactive pipeline for 2022-01-03 -> today.
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\backfill_historical.ps1
#
# Two-phase:
#   PHASE 1 - Reddit historical pull (Arctic Shift, free). One season at a
#             time (2022..current). ~60-90 min total, mostly network I/O.
#   PHASE 2 - Aggregators for every Monday 2022-01-03 -> today (~210 weeks).
#             ~60 min of compute (many quick per-week aggregator calls).
#   PHASE 3 - Board + site rebuild once at the end.
#
# Safe to re-run: all ingestion + aggregation paths upsert on natural keys.
# Skip reddit by passing -SkipReddit. Limit seasons via -Seasons @(2024,2025,2026).

param(
    [int[]] $Seasons      = @(2022, 2023, 2024, 2025, 2026),
    [switch] $SkipReddit  = $false,
    [switch] $SkipBuild   = $false
)

$ErrorActionPreference = "Continue"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

if (Test-Path ".env") {
    Get-Content ".env" | ForEach-Object {
        if ($_ -match '^\s*([A-Z_][A-Z0-9_]*)\s*=\s*(.*)\s*$') {
            $name  = $matches[1]
            $value = $matches[2] -replace '^"(.*)"$', '$1' -replace "^'(.*)'$", '$1'
            [Environment]::SetEnvironmentVariable($name, $value, "Process")
        }
    }
}

$LogDir = Join-Path $RepoRoot "logs"
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }
$LogPath = Join-Path $LogDir ("backfill_historical_{0:yyyy-MM-dd_HHmm}.log" -f (Get-Date))

function Log([string]$msg) {
    $stamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ssK"
    "$stamp  $msg" | Tee-Object -FilePath $LogPath -Append
}
function Run([string]$label, [scriptblock]$block) {
    Log "== $label =="
    & $block *>&1 | Tee-Object -FilePath $LogPath -Append
}

Log "==== backfill_historical start ===="
Log "   seasons=$($Seasons -join ',')  SkipReddit=$SkipReddit  SkipBuild=$SkipBuild"

# -----------------------------------------------------------------------------
# PHASE 1 - Reddit historical pull, one season at a time.
# Arctic Shift is free; we cap queries per window to stay polite.
# -----------------------------------------------------------------------------
if (-not $SkipReddit) {
    foreach ($season in $Seasons) {
        # Season window: Aug 1 of $season  ->  Jan 31 of $season+1 ET
        $seasonStart = "{0}-08-01" -f $season
        $seasonEnd   = "{0}-01-31" -f ($season + 1)
        # If season end is future, clamp to today
        $today = (Get-Date).ToString("yyyy-MM-dd")
        if ($seasonEnd -gt $today) { $seasonEnd = $today }

        Run "reddit: backfill season=$season ($seasonStart..$seasonEnd)" {
            python manage.py backfill-offseason-conversation `
                --season $season `
                --through-date $seasonEnd `
                --provider arctic-shift `
                --days-per-window 7 `
                --limit-per-query 50 `
                --continue-on-error `
                --skip-build-features
        }
    }
} else {
    Log "   (SkipReddit=true; skipping Phase 1)"
}

# -----------------------------------------------------------------------------
# PHASE 2 - Aggregators for every Monday 2022-01-03 -> last completed Monday.
# -----------------------------------------------------------------------------
$Start  = Get-Date -Year 2022 -Month 1 -Day 3   # Mon Jan 3, 2022
$End    = (Get-Date).Date.AddDays(-(([int](Get-Date).DayOfWeek + 6) % 7))
$Mondays = @()
for ($d = $Start; $d -le $End; $d = $d.AddDays(7)) { $Mondays += $d }
Log "   Phase 2: $($Mondays.Count) Mondays  first=$($Mondays[0].ToString('yyyy-MM-dd'))  last=$($Mondays[-1].ToString('yyyy-MM-dd'))"

# Player tagging runs once per season (not per-week) - much faster.
foreach ($season in $Seasons) {
    Run "player: tag-player-mentions --season=$season --commit" {
        python manage.py tag-player-mentions --season $season --commit
    }
}

$i = 0
foreach ($monday in $Mondays) {
    $i++
    $dateStr = $monday.ToString("yyyy-MM-dd")
    $weekNum = [int]((Get-Culture).Calendar.GetWeekOfYear(
        $monday, [System.Globalization.CalendarWeekRule]::FirstFourDayWeek,
        [System.DayOfWeek]::Monday))
    $isoKey  = "{0}-{1:D2}" -f $monday.Year, $weekNum

    # Progress heartbeat every 20 weeks
    if ($i % 20 -eq 1) {
        Log "   ... progress: week $i of $($Mondays.Count) (processing $isoKey)"
    }

    Run "cohort-week $isoKey" {
        python manage.py compute-cohort-week --week $isoKey
    }
    Run "divergence $isoKey" {
        python manage.py compute-divergence --week $isoKey
    }
    Run "mood-week $dateStr" {
        python manage.py compute-mood-week --week $dateStr --no-from-seed
    }
    Run "rivalry $dateStr" {
        python manage.py compute-rivalry-ratios --week $dateStr --no-from-seed
    }
    Run "lexicon $dateStr" {
        python manage.py mine-lexicon --week $dateStr --no-from-seed
    }
    Run "player-mood $isoKey" {
        python manage.py compute-player-week-mood --week $isoKey
    }
}

# -----------------------------------------------------------------------------
# PHASE 3 - Final rebuild
# -----------------------------------------------------------------------------
if (-not $SkipBuild) {
    # Build conversation features across each covered season to refresh the
    # team_week_conversation_features rollup.
    foreach ($season in $Seasons) {
        Run "features: build-conversation-features --season=$season" {
            python manage.py build-conversation-features --season $season --week 1
        }
    }
    # Archetype re-classification for the most recent season
    $mostRecent = ($Seasons | Sort-Object -Descending)[0]
    Run "archetypes: classify-fanbases --season=$mostRecent" {
        python manage.py classify-fanbases --season $mostRecent
    }
    # Board + site rebuild (boards are season snapshots — pin to most recent)
    Run "board: build-the-room-board --season=$mostRecent" {
        python manage.py build-the-room-board --season $mostRecent
    }
    Run "board: build-players-landing --season=$mostRecent" {
        python manage.py build-players-landing --season $mostRecent
    }
    Run "board: build-signature-story-board --season=$mostRecent" {
        python manage.py build-signature-story-board --season $mostRecent
    }
    Run "board: build-methodology" { python manage.py build-methodology }
    Run "site: build-site" { python manage.py build-site }
    Run "site: build-editions-archive" { python manage.py build-editions-archive }
} else {
    Log "   (SkipBuild=true; skipping Phase 3)"
}

Run "status: fanintel-status" { python manage.py fanintel-status }

Log "==== backfill_historical end ===="
