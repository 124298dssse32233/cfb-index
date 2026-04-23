# scripts/backfill_reddit_history.ps1
#
# Historical Reddit pull via Arctic Shift (free, no auth). For each in-season
# week (weeks 1-16) of seasons 2022..2025, calls collect-reddit-watchlist with
# explicit --after / --before date bounds so we capture posts from that
# calendar week only.
#
# Wall-clock estimate: ~1-2 hrs. Arctic Shift is rate-limited to ~1-3 req/s;
# each (season, week) call hits r/CFB + ~20 team subreddits.
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\backfill_reddit_history.ps1
#
# Skip seasons via -Seasons @(2024,2025). Cap weeks via -MaxWeek 10.

param(
    [int[]] $Seasons  = @(2022, 2023, 2024, 2025),
    [int]   $MinWeek  = 1,
    [int]   $MaxWeek  = 16,
    [int]   $SearchLimit = 20,
    [int]   $LimitTeams  = 25
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
$LogPath = Join-Path $LogDir ("backfill_reddit_{0:yyyy-MM-dd_HHmm}.log" -f (Get-Date))

function Log([string]$msg) {
    $stamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ssK"
    "$stamp  $msg" | Tee-Object -FilePath $LogPath -Append
}
function Run([string]$label, [scriptblock]$block) {
    Log "== $label =="
    & $block *>&1 | Tee-Object -FilePath $LogPath -Append
}

Log "==== backfill_reddit_history start ===="
Log "   seasons=$($Seasons -join ',')  weeks=$MinWeek..$MaxWeek"

# Week 1 of each season starts roughly the last Sat of August.
# We compute a "week-N start date" as: last Saturday of August + 7*(N-1) days.
function Get-SeasonWeekStart([int]$season, [int]$week) {
    $aug31 = Get-Date -Year $season -Month 8 -Day 31
    # Find the last Saturday on or before Aug 31
    $dow = [int]$aug31.DayOfWeek  # Sunday=0..Saturday=6
    $offset = ($dow - 6 + 7) % 7
    $week1 = $aug31.AddDays(-$offset)
    return $week1.AddDays(7 * ($week - 1))
}

foreach ($season in $Seasons) {
    foreach ($week in $MinWeek..$MaxWeek) {
        $start = Get-SeasonWeekStart $season $week
        $end   = $start.AddDays(7)
        $after  = $start.ToString("yyyy-MM-dd")
        $before = $end.ToString("yyyy-MM-dd")

        # National r/CFB pull
        Run "reddit $season-W$week national ($after..$before)" {
            python manage.py collect-reddit-watchlist `
                --season $season --week $week `
                --subreddit CFB `
                --audience-bucket national `
                --provider arctic-shift `
                --search-limit $SearchLimit `
                --limit-teams $LimitTeams `
                --after $after --before $before `
                --no-replace-existing
        }
    }
}

# Aggregate every week we just populated so cohort/mood tables get new rows.
Log "==== aggregation pass ===="
foreach ($season in $Seasons) {
    foreach ($week in $MinWeek..$MaxWeek) {
        $start = Get-SeasonWeekStart $season $week
        $weekNum = [int]((Get-Culture).Calendar.GetWeekOfYear(
            $start, [System.Globalization.CalendarWeekRule]::FirstFourDayWeek,
            [System.DayOfWeek]::Monday))
        $isoKey = "{0}-{1:D2}" -f $start.Year, $weekNum
        $mondayStr = $start.AddDays(2).ToString("yyyy-MM-dd")  # Saturday + 2 = Monday of next week

        Run "cohort-week $isoKey" {
            python manage.py compute-cohort-week --week $isoKey
        }
        Run "divergence $isoKey" {
            python manage.py compute-divergence --week $isoKey
        }
    }
}

Run "status: fanintel-status" { python manage.py fanintel-status }
Log "==== backfill_reddit_history end ===="
