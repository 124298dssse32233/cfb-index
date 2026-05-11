# One-shot: register the Monday 10:00 "CFBIndex-FanintelWeekly" task.
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\register_weekly_task.ps1

$RepoRoot   = Split-Path -Parent $PSScriptRoot
$ScriptPath = Join-Path $RepoRoot "scripts\weekly_deep.ps1"
$TaskName   = "CFBIndex-FanintelWeekly"

if (-not (Test-Path $ScriptPath)) {
    throw "weekly_deep.ps1 not found at $ScriptPath"
}

$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$ScriptPath`"" `
    -WorkingDirectory $RepoRoot

$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At 10:00

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 5)
# 5h limit (was 3h). Weekly task runs the full daily ingest plus weekly-deep
# work; the 3h limit cut it short for the same reason daily_ingest was being
# killed at the 2h mark — see register_daily_task.ps1 for context.

$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Register-ScheduledTask `
    -TaskName  $TaskName `
    -Action    $action `
    -Trigger   $trigger `
    -Settings  $settings `
    -Principal $principal `
    -Description "CFB Index - weekly deep pass (Reddit backfill + audits)" `
    -Force | Out-Null

Write-Host "Registered scheduled task: $TaskName (Mondays 10:00)"
$info = Get-ScheduledTask -TaskName $TaskName | Get-ScheduledTaskInfo
Write-Host "Next run: $($info.NextRunTime)"
