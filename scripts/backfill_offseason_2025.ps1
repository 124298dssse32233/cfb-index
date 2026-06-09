# scripts/backfill_offseason_2025.ps1
#
# One-shot comprehensive backfill to bring the site current for the 2026 offseason:
#   2025 season (games / rankings / models / Heisman / player stats / context) +
#   NFL draft (2024-26) + award winners + recruiting + coaching + boards + build.
#
# Continue-on-error: one failed step never aborts the rest. Logs to logs/.
# Self-contained for Task Scheduler / background runs (venv-prepend + UTF-8 + .env).
# Heavy: expect a few hours. Re-runnable (ingests upsert; --missing-only on stats).

$ErrorActionPreference = "Continue"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

# venv + UTF-8 so bare `python` is the project interpreter and logs don't crash
$env:PYTHONUTF8 = "1"
$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (Test-Path $VenvPython) { $env:Path = (Split-Path -Parent $VenvPython) + ";" + $env:Path }

# Load .env (CFBD key etc.) into the process
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
$LogPath = Join-Path $LogDir ("backfill_offseason_{0:yyyy-MM-dd_HHmmss}.log" -f (Get-Date))

function Log([string]$m) { $s = Get-Date -Format "yyyy-MM-ddTHH:mm:ssK"; "$s  $m" | Tee-Object -FilePath $LogPath -Append }
function Run([string]$label, [string[]]$cmdArgs) {
    Log "== $label =="
    & python -u manage.py @cmdArgs *>&1 | Tee-Object -FilePath $LogPath -Append
    if ($LASTEXITCODE -ne 0) { Log "   $label exited $LASTEXITCODE (continuing)" } else { Log "   $label OK" }
}

$sw = [System.Diagnostics.Stopwatch]::StartNew()
Log "==== backfill_offseason_2025 START ===="

# Phase 0 - connectivity preflight (informational; continue regardless)
Run "cfbd connectivity 2025" @("check-cfbd-connectivity", "--season", "2025")

# Phase 1 - 2025 core: games, rankings, team models, Heisman (play-level skipped for tractability)
Run "cfbd-history 2025 (+models +heisman)" @("backfill-cfbd-history", "--start-season", "2025", "--end-season", "2025", "--include-postseason", "--run-models", "--skip-play-level")

# Phase 2 - 2025 game-level player stats (only weeks still missing stats)
Run "game-player-stats 2025" @("backfill-game-player-stats", "--start-season", "2025", "--end-season", "2025", "--include-postseason", "--missing-only")

# Phase 3 - 2025 player context: roster + recruiting + transfer + usage + value metrics
Run "player-context 2025" @("backfill-player-context", "--start-season", "2025", "--end-season", "2025")

# Phase 4 - offseason events
Run "nfl-draft 2024-2026" @("ingest-nfl-draft", "--start-year", "2024", "--end-year", "2026")
Run "wiki-awards 2024-2025 (+import)" @("scrape-wiki-awards", "--start-year", "2024", "--end-year", "2025", "--auto-import")
Run "coaching news (365d)" @("coaching-fetch-news", "--days", "365")
Run "recruiting-pulse 2026" @("refresh-recruiting-pulse", "--class-year", "2026")
Run "recruiting-pulse 2027" @("refresh-recruiting-pulse", "--class-year", "2027")

# Phase 5 - boards + landing pages for 2025
Run "board the-room 2025" @("build-the-room-board", "--season", "2025")
Run "board players-landing 2025" @("build-players-landing", "--season", "2025")
Run "board signature-story 2025" @("build-signature-story-board", "--season", "2025")
Run "methodology" @("build-methodology")
Run "editions-archive" @("build-editions-archive")

# Phase 6 - final full site build
Run "build-site" @("build-site")

$sw.Stop()
Log ("==== backfill_offseason_2025 END  (elapsed {0:N1} min) ====" -f $sw.Elapsed.TotalMinutes)
