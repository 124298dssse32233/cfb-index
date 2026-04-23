param(
    [int]$StartSeason = 2014,
    [int]$EndSeason = 2025,
    [switch]$Force
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $repoRoot
$env:PYTHONUNBUFFERED = "1"

$logDir = Join-Path $repoRoot "output\logs"
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$logPath = Join-Path $logDir "history-load-$StartSeason-$EndSeason-$timestamp.log"
$statePath = Join-Path $logDir "history-load-state-$StartSeason-$EndSeason.json"
$stopwatch = [System.Diagnostics.Stopwatch]::StartNew()

function Get-HistoryState {
    if (-not (Test-Path $statePath)) {
        return @{
            startSeason = $StartSeason
            endSeason = $EndSeason
            updatedAt = (Get-Date).ToString("s")
            seasons = @{}
            globalStages = @{}
        }
    }

    $loaded = Get-Content $statePath -Raw | ConvertFrom-Json -AsHashtable
    if (-not $loaded.ContainsKey("seasons")) {
        $loaded["seasons"] = @{}
    }
    if (-not $loaded.ContainsKey("globalStages")) {
        $loaded["globalStages"] = @{}
    }
    return $loaded
}

function Save-HistoryState {
    param(
        [Parameter(Mandatory = $true)]
        [hashtable]$State
    )

    $State["updatedAt"] = (Get-Date).ToString("s")
    $State | ConvertTo-Json -Depth 8 | Set-Content -Path $statePath -Encoding utf8
}

function Ensure-SeasonState {
    param(
        [Parameter(Mandatory = $true)]
        [hashtable]$State,
        [Parameter(Mandatory = $true)]
        [int]$Season
    )

    $seasonKey = "$Season"
    if (-not $State["seasons"].ContainsKey($seasonKey)) {
        $State["seasons"][$seasonKey] = @{
            teamBackfill = $false
            teamSeasonSync = $false
            playerContext = $false
            gamePlayerStats = $false
        }
    }
}

function Test-SeasonStageComplete {
    param(
        [Parameter(Mandatory = $true)]
        [hashtable]$State,
        [Parameter(Mandatory = $true)]
        [int]$Season,
        [Parameter(Mandatory = $true)]
        [string]$Stage
    )

    Ensure-SeasonState -State $State -Season $Season
    return [bool]$State["seasons"]["$Season"][$Stage]
}

function Set-SeasonStageComplete {
    param(
        [Parameter(Mandatory = $true)]
        [hashtable]$State,
        [Parameter(Mandatory = $true)]
        [int]$Season,
        [Parameter(Mandatory = $true)]
        [string]$Stage
    )

    Ensure-SeasonState -State $State -Season $Season
    $State["seasons"]["$Season"][$Stage] = $true
    Save-HistoryState -State $State
}

function Test-GlobalStageComplete {
    param(
        [Parameter(Mandatory = $true)]
        [hashtable]$State,
        [Parameter(Mandatory = $true)]
        [string]$Stage
    )

    return [bool]$State["globalStages"][$Stage]
}

function Set-GlobalStageComplete {
    param(
        [Parameter(Mandatory = $true)]
        [hashtable]$State,
        [Parameter(Mandatory = $true)]
        [string]$Stage
    )

    $State["globalStages"][$Stage] = $true
    Save-HistoryState -State $State
}

function Invoke-And-Log {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Label,
        [Parameter(Mandatory = $true)]
        [scriptblock]$Script
    )

    Write-Host ""
    Write-Host "=== $Label ===" -ForegroundColor Cyan
    "=== $Label ===" | Tee-Object -FilePath $logPath -Append | Out-Null
    & $Script 2>&1 | Tee-Object -FilePath $logPath -Append
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) {
        throw "$Label failed with exit code $exitCode"
    }
}

$state = Get-HistoryState

Write-Host "Running resumable 2014-forward history load..." -ForegroundColor Cyan
Write-Host "Log file: $logPath" -ForegroundColor DarkGray
Write-Host "State file: $statePath" -ForegroundColor DarkGray
Write-Host "Started: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor DarkGray

Invoke-And-Log -Label "CFBD connectivity preflight" -Script {
    python -u manage.py check-cfbd-connectivity --season $StartSeason
}

for ($season = $StartSeason; $season -le $EndSeason; $season++) {
    if ($Force) {
        Ensure-SeasonState -State $state -Season $season
        $state["seasons"]["$season"]["teamBackfill"] = $false
        $state["seasons"]["$season"]["teamSeasonSync"] = $false
        $state["seasons"]["$season"]["playerContext"] = $false
        $state["seasons"]["$season"]["gamePlayerStats"] = $false
        Save-HistoryState -State $state
    }

    if (-not (Test-SeasonStageComplete -State $state -Season $season -Stage "teamBackfill")) {
        Invoke-And-Log -Label "Season $season team/game/postseason backfill" -Script {
            powershell -ExecutionPolicy Bypass -File scripts\backfill_cfbd_logged.ps1 `
                -StartSeason $season `
                -EndSeason $season `
                -IncludePostseason `
                -RunModels
        }
        Set-SeasonStageComplete -State $state -Season $season -Stage "teamBackfill"
    }

    if (-not (Test-SeasonStageComplete -State $state -Season $season -Stage "teamSeasonSync")) {
        Invoke-And-Log -Label "Season $season team/conference sync" -Script {
            python -u manage.py sync-team-seasons --season $season
        }
        Set-SeasonStageComplete -State $state -Season $season -Stage "teamSeasonSync"
    }

    if (-not (Test-SeasonStageComplete -State $state -Season $season -Stage "playerContext")) {
        Invoke-And-Log -Label "Season $season player context" -Script {
            powershell -ExecutionPolicy Bypass -File scripts\backfill_player_context_logged.ps1 `
                -StartSeason $season `
                -EndSeason $season `
                -ChunkSize 1
        }
        Set-SeasonStageComplete -State $state -Season $season -Stage "playerContext"
    }

    if (-not (Test-SeasonStageComplete -State $state -Season $season -Stage "gamePlayerStats")) {
        Invoke-And-Log -Label "Season $season game-player stats" -Script {
            powershell -ExecutionPolicy Bypass -File scripts\backfill_game_player_stats_logged.ps1 `
                -StartSeason $season `
                -EndSeason $season `
                -IncludePostseason
        }
        Set-SeasonStageComplete -State $state -Season $season -Stage "gamePlayerStats"
    }
}

if ($Force) {
    $state["globalStages"]["honorsImport"] = $false
    $state["globalStages"]["publishedBuild"] = $false
    $state["globalStages"]["coverageAudit"] = $false
    $state["globalStages"]["playerArchiveAudit"] = $false
    $state["globalStages"]["awardsArchiveAudit"] = $false
    $state["globalStages"]["historyStatus"] = $false
    Save-HistoryState -State $state
}

$honorsCsv = Join-Path $repoRoot "docs\heisman_honors_2014_2025.csv"
if ((-not (Test-GlobalStageComplete -State $state -Stage "honorsImport")) -and (Test-Path $honorsCsv)) {
    Invoke-And-Log -Label "Historical honors import" -Script {
        python -u manage.py import-player-honors --csv $honorsCsv --source-name official-heisman
    }
    Set-GlobalStageComplete -State $state -Stage "honorsImport"
}
elseif (-not (Test-Path $honorsCsv)) {
    Write-Host ""
    Write-Host "Skipping honors import because $honorsCsv does not exist yet." -ForegroundColor Yellow
    "Skipping honors import because $honorsCsv does not exist yet." | Tee-Object -FilePath $logPath -Append | Out-Null
}

if (-not (Test-GlobalStageComplete -State $state -Stage "publishedBuild")) {
    Invoke-And-Log -Label "Published rebuild" -Script {
        python -u manage.py build-published
    }
    Set-GlobalStageComplete -State $state -Stage "publishedBuild"
}

if (-not (Test-GlobalStageComplete -State $state -Stage "coverageAudit")) {
    Invoke-And-Log -Label "Coverage audit" -Script {
        python -u manage.py audit-data-coverage --output output\data-coverage-audit.md
    }
    Set-GlobalStageComplete -State $state -Stage "coverageAudit"
}

if (-not (Test-GlobalStageComplete -State $state -Stage "playerArchiveAudit")) {
    Invoke-And-Log -Label "Player archive audit" -Script {
        python -u manage.py audit-player-archive --output output\player-archive-audit.md
    }
    Set-GlobalStageComplete -State $state -Stage "playerArchiveAudit"
}

if (-not (Test-GlobalStageComplete -State $state -Stage "awardsArchiveAudit")) {
    Invoke-And-Log -Label "Awards archive audit" -Script {
        python -u manage.py audit-awards-archive --output output\awards-archive-audit.md
    }
    Set-GlobalStageComplete -State $state -Stage "awardsArchiveAudit"
}

if (-not (Test-GlobalStageComplete -State $state -Stage "historyStatus")) {
    Invoke-And-Log -Label "History load status refresh" -Script {
        python -u manage.py history-load-status --start-season $StartSeason --end-season $EndSeason --output output\history-load-status.md
    }
    Set-GlobalStageComplete -State $state -Stage "historyStatus"
}

$stopwatch.Stop()
Write-Host ""
Write-Host "History load finished successfully." -ForegroundColor Green
Write-Host "Elapsed: $([math]::Round($stopwatch.Elapsed.TotalMinutes, 1)) minutes" -ForegroundColor Green
Write-Host "Log file: $logPath" -ForegroundColor Green
Write-Host "State file: $statePath" -ForegroundColor Green
