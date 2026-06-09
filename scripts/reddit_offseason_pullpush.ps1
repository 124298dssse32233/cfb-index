# scripts/reddit_offseason_pullpush.ps1
#
# Re-collect offseason Reddit conversation via PullPush, then re-tag, re-run local
# sentiment, and rebuild. Needed because Arctic Shift's text-search (`query=`)
# parameter now returns HTTP 422 — every per-team search failed. PullPush still
# supports text search (`q=`), verified working. Continue-on-error; logs to logs/.

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
$LogPath = Join-Path $LogDir ("reddit_pullpush_{0:yyyy-MM-dd_HHmmss}.log" -f (Get-Date))
$Today = (Get-Date -Format 'yyyy-MM-dd')

function Log([string]$m) { $s = Get-Date -Format "yyyy-MM-ddTHH:mm:ssK"; "$s  $m" | Tee-Object -FilePath $LogPath -Append }
function Run([string]$label, [string[]]$a) {
    Log "== $label =="
    & python -u manage.py @a *>&1 | Tee-Object -FilePath $LogPath -Append
    if ($LASTEXITCODE -ne 0) { Log "   $label exited $LASTEXITCODE (continuing)" } else { Log "   $label OK" }
}

$sw = [System.Diagnostics.Stopwatch]::StartNew()
Log "==== reddit_offseason_pullpush START (through $Today) ===="

# 1. Historical offseason Reddit conversation Jan -> today, via PullPush (text search works here)
Run "offseason-conversation pullpush through $Today" @("backfill-offseason-conversation", "--provider", "pullpush", "--through-date", $Today, "--continue-on-error")

# 2. Re-tag players against the freshly collected conversation
Run "tag-player-mentions 2025" @("tag-player-mentions", "--season", "2025", "--commit")

# 3. Player sentiment via LOCAL Ollama on the new player targets
Run "classify-player-sentiment (local Ollama)" @("classify-player-sentiment")

# 4. Rebuild boards + site so the new chatter/mood/sentiment shows up
Run "board the-room 2025" @("build-the-room-board", "--season", "2025")
Run "board players-landing 2025" @("build-players-landing", "--season", "2025")
Run "board signature-story 2025" @("build-signature-story-board", "--season", "2025")
Run "build-site" @("build-site")

$sw.Stop()
Log ("==== reddit_offseason_pullpush END (elapsed {0:N1} min) ====" -f $sw.Elapsed.TotalMinutes)
