# scripts/_pipeline_common.ps1
#
# Shared preamble for the DECOUPLED pipeline (collect.ps1 + build_publish.ps1).
# Dot-source it AFTER setting $PipelineName, e.g.:
#     $PipelineName = "collect"
#     . "$PSScriptRoot\_pipeline_common.ps1"
#     ... run sections via Run / Run-Adapter, using $global:CurSeason etc. ...
#     Complete-Pipeline "HEALTHCHECK_URL_COLLECT"
#
# Provides: venv+UTF-8 runtime, .env load, Log, Run/Run-Adapter (+ $global:FailedSteps),
# the canonical resolve-week vars ($global:CurSeason/SeasonWeek/PrevMonday/IsoWeekKey/
# IsInSeason), and Complete-Pipeline (Healthchecks ping + exit). Uses $global: scope
# so the dot-sourcing script and these helpers share one set of state.
#
# daily_ingest.ps1 (the monolith) does NOT use this file and stays the active,
# behavior-unchanged path until the decoupled tasks are activated via
# register_split_tasks.ps1.

$ErrorActionPreference = "Continue"
if (-not $PipelineName) { $PipelineName = "pipeline" }
$global:RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $global:RepoRoot

# venv + UTF-8 (Task Scheduler launches a bare shell; bare `python` must hit .venv)
$env:PYTHONUTF8 = "1"
$VenvPython = Join-Path $global:RepoRoot ".venv\Scripts\python.exe"
if (Test-Path $VenvPython) { $env:Path = (Split-Path -Parent $VenvPython) + ";" + $env:Path }

# .env -> process env (API keys, VERCEL_TOKEN, HEALTHCHECK_URL*)
if (Test-Path ".env") {
    Get-Content ".env" | ForEach-Object {
        if ($_ -match '^\s*([A-Z_][A-Z0-9_]*)\s*=\s*(.*)\s*$') {
            $value = $matches[2] -replace '^"(.*)"$', '$1' -replace "^'(.*)'$", '$1'
            [Environment]::SetEnvironmentVariable($matches[1], $value, "Process")
        }
    }
}

$LogDir = Join-Path $global:RepoRoot "logs"
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }
$global:LogPath = Join-Path $LogDir ("fanintel_{0}_{1:yyyy-MM-dd}.log" -f $PipelineName, (Get-Date))

function Log([string]$msg) {
    $stamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ssK"
    "$stamp  $msg" | Tee-Object -FilePath $global:LogPath -Append
}

# Steps marked -Critical accumulate; a non-empty list -> non-zero exit + Healthcheck /fail.
$global:FailedSteps = @()
function Run([string]$label, [scriptblock]$block, [switch]$Critical) {
    Log "== $label =="
    & $block *>&1 | Tee-Object -FilePath $global:LogPath -Append
    if ($LASTEXITCODE -ne 0) {
        Log "   $label exited with code $LASTEXITCODE (continuing)"
        if ($Critical) { $global:FailedSteps += $label }
    }
}
function Run-Adapter([string]$id) { Run "adapter: $id" { python tools/run_adapter.py $id } }

# --- Canonical week (single source of truth; see src/cfb_rankings/common/week.py) ---
$global:Now = Get-Date
$WkLines = (python manage.py resolve-week --json)
$WkLine  = ($WkLines -split "`n" | Where-Object { $_ -match '^\s*\{.*\}\s*$' } | Select-Object -Last 1)
try {
    $Wk = $WkLine | ConvertFrom-Json
    if (-not $Wk.iso_key) { throw "no iso_key" }
} catch {
    Log "FATAL: resolve-week did not return parseable JSON (got: '$WkLine'). Aborting before any data mutation."
    exit 1
}
$global:CurSeason  = [int]$Wk.season_year
$global:SeasonWeek = [int]$Wk.week
$global:PrevMonday = [string]$Wk.week_start
$global:IsoWeekKey = [string]$Wk.iso_key
$global:IsInSeason = [bool]$Wk.in_season

Log "==== $PipelineName start ===="
Log "   today=$($global:Now.ToString('yyyy-MM-dd'))  iso_week=$($global:IsoWeekKey)  prev_monday=$($global:PrevMonday)"
Log "   in_season=$($global:IsInSeason)  cur_season=$($global:CurSeason)  season_week=$($global:SeasonWeek)"

# Healthchecks.io dead-man's-switch + final exit. $hcEnvName lets collect vs
# build_publish ping different checks (build_publish should own the main URL since
# it is the must-publish path).
function Complete-Pipeline([string]$hcEnvName) {
    $HcUrl = [Environment]::GetEnvironmentVariable($hcEnvName)
    if ([string]::IsNullOrWhiteSpace($HcUrl)) {
        Log "   ($hcEnvName not set -- skipping dead-man's-switch ping)"
    } elseif ($global:FailedSteps.Count -eq 0) {
        try { Invoke-WebRequest -Uri $HcUrl -Method Get -TimeoutSec 15 -UseBasicParsing | Out-Null; Log "   healthcheck: success ping sent" }
        catch { Log "   healthcheck ping error: $($_.Exception.Message)" }
    } else {
        try { Invoke-WebRequest -Uri ($HcUrl.TrimEnd('/') + '/fail') -Method Get -TimeoutSec 15 -UseBasicParsing | Out-Null; Log "   healthcheck: FAIL ping sent" }
        catch { Log "   healthcheck fail-ping error: $($_.Exception.Message)" }
    }
    if ($global:FailedSteps.Count -gt 0) {
        Log "==== $PipelineName end (FAILED: $($global:FailedSteps -join ', ')) ===="
        exit 1
    }
    Log "==== $PipelineName end (clean) ===="
    exit 0
}
