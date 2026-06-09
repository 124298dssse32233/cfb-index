# scripts/fanintel_offseason_collect.ps1
#
# One-shot: collect REAL offseason fan-intel (Jan 2026 -> today) and refresh the
# fan-intelligence surfaces. Run AFTER the 2025 backfill so only one job writes
# the SQLite DB at a time. Continue-on-error; logs to logs/.
#
#   1. Historical offseason Reddit conversation, Jan -> today, via FREE arctic-shift
#   2. Full daily fan-intel pipeline (Apify adapters now enabled + tagging + features + boards + build)
#   3. Player sentiment via LOCAL Ollama (now that 2025 player targets exist)
#   4. Rebuild boards + site so sentiment/mood show up

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
$LogPath = Join-Path $LogDir ("fanintel_offseason_{0:yyyy-MM-dd_HHmmss}.log" -f (Get-Date))
$Today = (Get-Date -Format 'yyyy-MM-dd')

function Log([string]$m) { $s = Get-Date -Format "yyyy-MM-ddTHH:mm:ssK"; "$s  $m" | Tee-Object -FilePath $LogPath -Append }
function Run([string]$label, [string[]]$a) {
    Log "== $label =="
    & python -u manage.py @a *>&1 | Tee-Object -FilePath $LogPath -Append
    if ($LASTEXITCODE -ne 0) { Log "   $label exited $LASTEXITCODE (continuing)" } else { Log "   $label OK" }
}

$sw = [System.Diagnostics.Stopwatch]::StartNew()
Log "==== fanintel_offseason_collect START (through $Today) ===="

# 1. Historical offseason Reddit conversation (Jan -> today), free provider, no Apify needed
Run "offseason-conversation pullpush through $Today" @("backfill-offseason-conversation", "--provider", "pullpush", "--through-date", $Today, "--continue-on-error")

# 2. Full daily fan-intel pipeline: recent adapters (Apify now enabled) + reddit watchlist +
#    aggregation + tag-player-mentions + conversation features + boards + build-site
Log "== daily_ingest.ps1 (recent fan-intel + tagging + features + boards + build) =="
& (Join-Path $RepoRoot "scripts\daily_ingest.ps1")
Log "   daily_ingest.ps1 returned (exit $LASTEXITCODE)"

# 3. Player sentiment via LOCAL Ollama (2025 player targets now exist post-tagging)
Run "classify-player-sentiment (local Ollama)" @("classify-player-sentiment")

# 4. Rebuild boards + site so sentiment/mood are reflected
Run "board the-room 2025" @("build-the-room-board", "--season", "2025")
Run "board players-landing 2025" @("build-players-landing", "--season", "2025")
Run "board signature-story 2025" @("build-signature-story-board", "--season", "2025")
Run "build-site" @("build-site")

$sw.Stop()
Log ("==== fanintel_offseason_collect END (elapsed {0:N1} min) ====" -f $sw.Elapsed.TotalMinutes)
