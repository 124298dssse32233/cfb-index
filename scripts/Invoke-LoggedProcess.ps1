function Write-LoggedProcessLines {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Lines,
        [Parameter(Mandatory = $true)]
        [string]$LogPath
    )

    foreach ($line in $Lines) {
        Write-Host $line
        Add-Content -Path $LogPath -Value $line
    }
}

function ConvertTo-LoggedProcessArgumentString {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$ArgumentList
    )

    $quoted = foreach ($argument in $ArgumentList) {
        if ($argument -match '[\s"]') {
            '"' + ($argument -replace '(\\*)"', '$1$1\"' -replace '(\\+)$', '$1$1') + '"'
        }
        else {
            $argument
        }
    }
    return ($quoted -join " ")
}

function Invoke-LoggedProcess {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Label,
        [Parameter(Mandatory = $true)]
        [string]$FilePath,
        [Parameter(Mandatory = $true)]
        [string[]]$ArgumentList,
        [Parameter(Mandatory = $true)]
        [string]$LogPath,
        [int]$HeartbeatSeconds = 45,
        [int]$PollSeconds = 2
    )

    $logDir = Split-Path -Parent $LogPath
    if ($logDir -and -not (Test-Path $logDir)) {
        New-Item -ItemType Directory -Path $logDir -Force | Out-Null
    }

    $commandLine = "$FilePath $($ArgumentList -join ' ')"
    Add-Content -Path $LogPath -Value ""
    Add-Content -Path $LogPath -Value ">>> $Label"
    Add-Content -Path $LogPath -Value $commandLine

    $startInfo = [System.Diagnostics.ProcessStartInfo]::new()
    $startInfo.FileName = $FilePath
    $startInfo.UseShellExecute = $false
    $startInfo.CreateNoWindow = $true
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true
    $startInfo.Arguments = ConvertTo-LoggedProcessArgumentString -ArgumentList $ArgumentList

    $process = [System.Diagnostics.Process]::new()
    $process.StartInfo = $startInfo
    [void]$process.Start()

    $startedAt = Get-Date
    $lastHeartbeatAt = $startedAt
    $lastOutputAt = $startedAt

    while (-not $process.HasExited -or -not $process.StandardOutput.EndOfStream -or -not $process.StandardError.EndOfStream) {
        $outputLines = New-Object System.Collections.Generic.List[string]
        while (-not $process.StandardOutput.EndOfStream -and $process.StandardOutput.Peek() -ge 0) {
            $outputLines.Add($process.StandardOutput.ReadLine())
        }
        if ($outputLines.Count -gt 0) {
            Write-LoggedProcessLines -Lines $outputLines.ToArray() -LogPath $LogPath
            $lastOutputAt = Get-Date
        }

        $errorLines = New-Object System.Collections.Generic.List[string]
        while (-not $process.StandardError.EndOfStream -and $process.StandardError.Peek() -ge 0) {
            $errorLines.Add($process.StandardError.ReadLine())
        }
        if ($errorLines.Count -gt 0) {
            Write-LoggedProcessLines -Lines $errorLines.ToArray() -LogPath $LogPath
            $lastOutputAt = Get-Date
        }

        $now = Get-Date
        if (($now - $lastHeartbeatAt).TotalSeconds -ge $HeartbeatSeconds) {
            $elapsedMinutes = [math]::Round(($now - $startedAt).TotalMinutes, 1)
            $idleSeconds = [int]($now - $lastOutputAt).TotalSeconds
            $heartbeat = "[heartbeat] $Label still running ($elapsedMinutes min elapsed, $idleSeconds sec since last output)"
            Write-Host $heartbeat -ForegroundColor DarkGray
            Add-Content -Path $LogPath -Value $heartbeat
            $lastHeartbeatAt = $now
        }

        if (-not $process.HasExited -or -not $process.StandardOutput.EndOfStream -or -not $process.StandardError.EndOfStream) {
            Start-Sleep -Seconds $PollSeconds
            $process.Refresh()
        }
    }

    return [int]$process.ExitCode
}
