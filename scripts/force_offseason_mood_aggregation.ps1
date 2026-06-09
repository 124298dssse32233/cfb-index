# scripts/force_offseason_mood_aggregation.ps1
#
# Force the deeper PER-WEEK fan-intelligence aggregation across the 2026 offseason
# (season ended ~mid-Jan -> today): cohort, divergence, team mood, rivalry ratios,
# lexicon, and player-week mood for EACH week, then rebuild boards + site so the
# mood/vibe surfaces (fanbase_mood_weekly, etc.) populate.
#
# Run AFTER the Reddit backfill so it aggregates the COMPLETE corpus. Continue-on-
# error; logs to logs/. compute-cohort/divergence/player-mood take an ISO week key
# (YYYY-WW); compute-mood/rivalry/lexicon take a Monday date (YYYY-MM-DD).

$ErrorActionPreference = "Continue"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$env:PYTHONUTF8 = "1"
$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (Test-Path $VenvPython) { $env:Path = (Split-Path -Parent $VenvPython) + ";" + $env:Path }

if (Test-Path ".env") {
    Get-Content ".env" | ForEach-Object {
        if ($_ -match '^\s*([A-Z_][A-Z0-9_]*)\s*=\s*(.*)\s*$') {
            $n = $matches[1]; $v = $matches[2] -replace '^"(.*)"$', '$1' -replace "^'(.*)'$", '$1'
            [Environment]::SetEnvironmentVariable($n, $v, "Process")
        }
    }
}

$LogDir = Join-Path $RepoRoot "logs"
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory $LogDir | Out-Null }
$LogPath = Join-Path $LogDir ("mood_aggregation_{0:yyyy-MM-dd_HHmmss}.log" -f (Get-Date))

function Log([string]$m) { $s = Get-Date -Format "yyyy-MM-ddTHH:mm:ssK"; "$s  $m" | Tee-Object -FilePath $LogPath -Append }
function Run([string]$label, [string[]]$a) {
    Log "== $label =="
    & python -u manage.py @a *>&1 | Tee-Object -FilePath $LogPath -Append
    if ($LASTEXITCODE -ne 0) { Log "   $label exited $LASTEXITCODE (continuing)" }
}

$sw = [System.Diagnostics.Stopwatch]::StartNew()
Log "==== force_offseason_mood_aggregation START ===="

$cur = Get-Date "2026-01-05"   # first Monday after the 2025 season ended
$end = Get-Date
$weeks = 0
while ($cur -le $end) {
    $monday = $cur.ToString("yyyy-MM-dd")
    $wk = [int]((Get-Culture).Calendar.GetWeekOfYear($cur, [System.Globalization.CalendarWeekRule]::FirstFourDayWeek, [System.DayOfWeek]::Monday))
    $iso = "{0}-{1:D2}" -f $cur.Year, $wk
    Log "---- week $iso (Monday $monday) ----"
    Run "cohort $iso"      @("compute-cohort-week", "--week", $iso)
    Run "divergence $iso"  @("compute-divergence", "--week", $iso)
    Run "mood $monday"     @("compute-mood-week", "--week", $monday, "--no-from-seed")
    Run "rivalry $monday"  @("compute-rivalry-ratios", "--week", $monday, "--no-from-seed")
    Run "lexicon $monday"  @("mine-lexicon", "--week", $monday, "--no-from-seed")
    Run "player-mood $iso" @("compute-player-week-mood", "--week", $iso)
    $weeks++
    $cur = $cur.AddDays(7)
}
Log "aggregated $weeks offseason weeks"

# Rebuild the surfaces that read the weekly mood tables
Run "board the-room 2025"        @("build-the-room-board", "--season", "2025")
Run "board players-landing 2025" @("build-players-landing", "--season", "2025")
Run "board signature-story 2025" @("build-signature-story-board", "--season", "2025")
Run "build-site"                 @("build-site")

$sw.Stop()
Log ("==== force_offseason_mood_aggregation END ({0} weeks, {1:N1} min) ====" -f $weeks, $sw.Elapsed.TotalMinutes)
