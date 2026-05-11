# One-time task registration. Run once:
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\register_daily_task.ps1
#
# Creates a Windows Task Scheduler entry named "CFBIndex-FanintelDaily"
# that fires every day at 09:00 local time and runs daily_ingest.ps1.
# Re-running with -Force replaces the existing registration.

$RepoRoot = Split-Path -Parent $PSScriptRoot
$ScriptPath = Join-Path $RepoRoot "scripts\daily_ingest.ps1"
$TaskName = "CFBIndex-FanintelDaily"

if (-not (Test-Path $ScriptPath)) {
    throw "daily_ingest.ps1 not found at $ScriptPath"
}

$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$ScriptPath`"" `
    -WorkingDirectory $RepoRoot

$trigger = New-ScheduledTaskTrigger -Daily -At 09:00

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 4)
# 4h limit (was 2h). The 2h limit was killing build-site mid-run at the
# player-pages stage every day — ingest+aggregators+models+boards alone
# consume ~1h50m on average, leaving <10m for build-site which needs ~30m.
# Symptom: output/site/index.html was stale for 7+ days in early May 2026
# because every daily run died before the homepage write step.

$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Register-ScheduledTask `
    -TaskName  $TaskName `
    -Action    $action `
    -Trigger   $trigger `
    -Settings  $settings `
    -Principal $principal `
    -Description "CFB Index - daily Fan Intelligence ingestion" `
    -Force | Out-Null

Write-Host "Registered scheduled task: $TaskName (daily 09:00)"
$info = Get-ScheduledTask -TaskName $TaskName | Get-ScheduledTaskInfo
Write-Host "Next run: $($info.NextRunTime)"
