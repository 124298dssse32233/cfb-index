# worktree-auto-publish.ps1
# Called by the Claude Code Stop hook in every session.
# Guards ensure it only acts when running inside a worktree on a claude/* branch
# that has commits not yet merged to master. Merges those commits and publishes.

Set-StrictMode -Off
$ErrorActionPreference = "Stop"

# Guard 1: Only run in worktrees (.git is a file, not a directory)
$gitMarker = Join-Path $PWD ".git"
if (-not (Test-Path $gitMarker -PathType Leaf)) { exit 0 }

# Guard 2: Get current branch — must start with claude/
$branch = (git rev-parse --abbrev-ref HEAD 2>$null).Trim()
if ($LASTEXITCODE -ne 0 -or -not $branch -or $branch -notlike "claude/*") { exit 0 }

# Guard 3: Only proceed if this branch has commits not yet on master
$ahead = (git rev-list --count "master..$branch" 2>$null).Trim()
if ($LASTEXITCODE -ne 0 -or -not $ahead -or [int]$ahead -eq 0) { exit 0 }

# Find main repo path from the .git file pointer.
# .git file content: "gitdir: <path>/Sports Website/.git/worktrees/<name>"
# Main repo = three levels up from that gitdir.
$gitContent = (Get-Content $gitMarker -Raw).Trim()
if ($gitContent -notmatch "gitdir:\s*(.+)") { exit 0 }
$gitDir = $matches[1].Trim()
$mainRepo = [IO.Path]::GetFullPath([IO.Path]::Combine($gitDir, "../../.."))
if (-not (Test-Path $mainRepo -PathType Container)) { exit 0 }

Push-Location $mainRepo
try {
    Write-Host "[auto-publish] Merging $branch -> master and publishing..." -ForegroundColor Cyan

    git checkout master 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "[auto-publish] Could not checkout master; skipping publish."
        exit 0
    }

    git merge $branch --no-edit 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "[auto-publish] Merge of $branch failed; resolve conflicts manually."
        exit 0
    }

    Write-Host "[auto-publish] Merge done. Running publish_site.ps1..." -ForegroundColor Cyan
    & ".\publish_site.ps1"
    $publishExit = $LASTEXITCODE

    if ($publishExit -eq 0) {
        Write-Host "[auto-publish] Live site updated from $branch." -ForegroundColor Green
    } else {
        Write-Warning "[auto-publish] publish_site.ps1 exited $publishExit — check output above."
    }
} finally {
    Pop-Location
}
