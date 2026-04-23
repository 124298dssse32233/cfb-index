# scripts/weekly_deep.ps1
#
# Monday 10:00 ET. The heavy pass that does not need daily cadence:
# Reddit comment-tree backfill for last week + fanbase-archetype refresh +
# data-integrity audits. Expected wall-clock: ~45 min.
#
# Driven by Windows Task Scheduler (see register_weekly_task.ps1).

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
$LogPath = Join-Path $LogDir ("fanintel_weekly_{0:yyyy-MM-dd}.log" -f (Get-Date))

function Log([string]$msg) {
    $stamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ssK"
    "$stamp  $msg" | Tee-Object -FilePath $LogPath -Append
}
function Run([string]$label, [scriptblock]$block) {
    Log "== $label =="
    & $block *>&1 | Tee-Object -FilePath $LogPath -Append
    if ($LASTEXITCODE -ne 0) { Log "   $label exited with code $LASTEXITCODE (continuing)" }
}

$Now        = Get-Date
$CurSeason  = if ($Now.Month -ge 7) { $Now.Year } else { $Now.Year - 1 }
# Last Monday as a YYYY-MM-DD
$LastMonday = $Now.AddDays(-(([int]$Now.DayOfWeek + 6) % 7) - 7).ToString("yyyy-MM-dd")

Log "==== weekly_deep start ===="
Log "   last_monday=$LastMonday  cur_season=$CurSeason"

# ------------------------------------------------------------------------
# 1. Reddit deep backfill: Monday..Sunday of the prior ET week, with comment
#    trees on high-signal posts. Free via Arctic Shift.
# ------------------------------------------------------------------------
$LastSunday = $Now.AddDays(-(([int]$Now.DayOfWeek + 6) % 7) - 1).ToString("yyyy-MM-dd")
Run "reddit: backfill-offseason-conversation (prior week w/ comments)" {
    python manage.py backfill-offseason-conversation `
        --season $CurSeason `
        --through-date $LastSunday `
        --provider arctic-shift `
        --days-per-window 7 `
        --limit-per-query 100 `
        --collect-comments `
        --comment-post-limit 20 `
        --comments-per-post 30 `
        --continue-on-error
}

# ------------------------------------------------------------------------
# 2. Fanbase archetype re-classification for the current season
# ------------------------------------------------------------------------
Run "archetypes: classify-fanbases --season=$CurSeason" {
    python manage.py classify-fanbases --season $CurSeason
}

# ------------------------------------------------------------------------
# 3. Data-integrity audits - write reports, do not fail the job
# ------------------------------------------------------------------------
Run "audit: audit-data-coverage" { python manage.py audit-data-coverage }
Run "audit: history-load-status" { python manage.py history-load-status }
Run "audit: refresh-local-health" { python manage.py refresh-local-health }
Run "audit: validate-maintenance" { python manage.py validate-maintenance }

# ------------------------------------------------------------------------
# 4. Final rebuild so any reclassified archetypes show up on the site
# ------------------------------------------------------------------------
Run "site: build-site" { python manage.py build-site }
Run "status: fanintel-status" { python manage.py fanintel-status }

Log "==== weekly_deep end ===="
