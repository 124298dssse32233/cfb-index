# Activate the DECOUPLED pipeline cadence (cadence architecture, 2026-06).
# Run once, consciously, when you want to switch from the monolith daily_ingest.ps1
# to the two-job collect + build_publish design:
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\register_split_tasks.ps1
#
# It registers:
#   CFBIndex-FanintelCollect       -> collect.ps1        daily 05:00 (sources -> SQLite)
#   CFBIndex-FanintelBuildPublish  -> build_publish.ps1  daily 09:00 (SQLite -> build -> deploy)
# and DISABLES the monolith CFBIndex-FanintelDaily so nothing double-runs.
#
# Why decoupled: build_publish reads SQLite as-of-now and never fetches, so a slow
# or failed collect can't block the site from shipping. The 05:00 collect finishes
# well before the 09:00 build. To revert: Enable-ScheduledTask CFBIndex-FanintelDaily
# and disable the two split tasks. -WhatIf previews without changing anything.
[CmdletBinding(SupportsShouldProcess = $true)]
param()

$RepoRoot = Split-Path -Parent $PSScriptRoot
$Collect  = Join-Path $RepoRoot "scripts\collect.ps1"
$Build    = Join-Path $RepoRoot "scripts\build_publish.ps1"
foreach ($p in @($Collect, $Build)) { if (-not (Test-Path $p)) { throw "missing: $p" } }

$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 4)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

function Register-Half([string]$Name, [string]$Script, [string]$At, [string]$Desc) {
    $action = New-ScheduledTaskAction -Execute "powershell.exe" `
        -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$Script`"" -WorkingDirectory $RepoRoot
    $trigger = New-ScheduledTaskTrigger -Daily -At $At
    if ($PSCmdlet.ShouldProcess($Name, "Register scheduled task ($At -> $Script)")) {
        Register-ScheduledTask -TaskName $Name -Action $action -Trigger $trigger `
            -Settings $settings -Principal $principal -Description $Desc -Force | Out-Null
        $next = (Get-ScheduledTask -TaskName $Name | Get-ScheduledTaskInfo).NextRunTime
        Write-Host "Registered $Name ($At). Next run: $next"
    }
}

Register-Half "CFBIndex-FanintelCollect" $Collect "05:00" "CFB Index - source collection (decoupled)"
Register-Half "CFBIndex-FanintelBuildPublish" $Build "09:00" "CFB Index - build + publish (decoupled)"

if (Get-ScheduledTask -TaskName "CFBIndex-FanintelDaily" -ErrorAction SilentlyContinue) {
    if ($PSCmdlet.ShouldProcess("CFBIndex-FanintelDaily", "Disable monolith (replaced by split tasks)")) {
        Disable-ScheduledTask -TaskName "CFBIndex-FanintelDaily" | Out-Null
        Write-Host "Disabled monolith CFBIndex-FanintelDaily (the two split tasks replace it)."
    }
}
Write-Host "`nDone. Optional: add HEALTHCHECK_URL_COLLECT=... to .env to monitor the collect job separately."
