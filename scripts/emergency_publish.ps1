<#
.SYNOPSIS
  Emergency LKG-only ship path for the Chronicle pipeline.

.DESCRIPTION
  Called from chronicle-weekly.yml failure handler (or triggered manually when
  the chronicle pipeline crashes overnight). Performs a no-LLM build using only
  Last-Known-Good cards from disk + DB, then ships via Vercel CLI.

  Fans see slightly-stale cards with an "Awaiting refresh" badge — but no
  broken pages and no human required at 3 AM.

.NOTES
  Idempotent: safe to run multiple times. Each run produces its own timestamped
  log under logs/emergency_publish_{ts}.log and a separate recovery branch so
  reruns never clobber a prior successful artifact.

  --no-verify on the git commit is intentional here and is the ONLY place in
  the project that bypasses pre-commit hooks. Rationale: this script runs inside
  a GitHub Actions emergency handler where hooks may depend on Python environment
  state that is unavailable (e.g. dev-mode lint deps not installed on the runner).
  The hook bypass is documented here and must not be replicated elsewhere.

  Alias rotation (wonderful-margulis-8ec96b.vercel.app) is explicit per the
  Vercel gotcha documented in CLAUDE.md §Vercel alias rotation gotcha.
#>
param(
    [string]$DbPath       = "cfb_rankings.db",
    [string]$DumpDir      = "output/site/_cards_lkg",
    [string]$SiteDir      = "output/site",
    [int]   $MinHtmlFiles = 1000,
    [string]$VercelAlias  = "wonderful-margulis-8ec96b.vercel.app"
)

$ErrorActionPreference = "Stop"
$ts = Get-Date -Format "yyyyMMdd-HHmmss"
$logDir = "logs"
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
$logFile = Join-Path $logDir "emergency_publish_$ts.log"
Start-Transcript -Path $logFile -Append

try {
    Write-Host "====================================================="
    Write-Host "EMERGENCY: Chronicle pipeline failure detected."
    Write-Host "Falling back to LKG-only ship at $ts UTC"
    Write-Host "====================================================="

    # ------------------------------------------------------------------
    # 1. Verify DB exists — hard requirement even in LKG mode because
    #    build-site needs the teams/players metadata tables.
    # ------------------------------------------------------------------
    if (-not (Test-Path $DbPath)) {
        throw "cfb_rankings.db not found at '$DbPath' — cannot proceed even with LKG. Restore the DB artifact before retrying."
    }
    Write-Host "[1/8] DB found at $DbPath"

    # ------------------------------------------------------------------
    # 2. Import LKG from disk dump (covers fresh-clone / missing-artifact case).
    #    Non-fatal: if the dump dir is empty or absent the DB-resident LKG
    #    cards are still used.
    # ------------------------------------------------------------------
    Write-Host "[2/8] Importing LKG cards from disk dump at $DumpDir ..."
    python -m cfb_rankings.chronicle.lkg --import-from-disk --dump-dir $DumpDir --db $DbPath
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "LKG import from disk exited $LASTEXITCODE — continuing with DB-resident LKG cards only."
    } else {
        Write-Host "LKG import complete."
    }

    # ------------------------------------------------------------------
    # 3. Build site in LKG-only + no-LLM mode.
    # ------------------------------------------------------------------
    Write-Host "[3/8] Running build-site --use-lkg-only --no-llm ..."
    python manage.py build-site --use-lkg-only --no-llm
    if ($LASTEXITCODE -ne 0) {
        throw "build-site failed even in LKG-only mode (exit $LASTEXITCODE). Check the build log above."
    }
    Write-Host "build-site complete."

    # ------------------------------------------------------------------
    # 4. Smoke-check: refuse to ship a half-empty site.
    # ------------------------------------------------------------------
    Write-Host "[4/8] Counting HTML files in $SiteDir ..."
    $htmlCount = (Get-ChildItem -Path $SiteDir -Recurse -Filter "*.html" -ErrorAction SilentlyContinue | Measure-Object).Count
    if ($htmlCount -lt $MinHtmlFiles) {
        throw "Emergency build produced only $htmlCount HTML files (threshold: $MinHtmlFiles) — refusing to ship a half-empty site."
    }
    Write-Host "Build produced $htmlCount HTML files. Threshold met."

    # ------------------------------------------------------------------
    # 5. Commit the rebuilt site to a timestamped recovery branch.
    #    --no-verify is intentional here (see .NOTES above).
    #    We exclude the _chronicle_drafts scratch dir to avoid committing
    #    in-progress draft blobs.
    # ------------------------------------------------------------------
    Write-Host "[5/8] Committing rebuilt site to recovery branch ..."
    $branch = "recovery/emergency-lkg-$ts"
    git checkout -b $branch
    if ($LASTEXITCODE -ne 0) { throw "git checkout -b $branch failed." }

    # Stage output/ excluding in-progress draft blobs
    git add output/
    git reset HEAD -- output/site/_chronicle_drafts/ 2>$null

    $staged = git diff --cached --name-only
    if (-not $staged) {
        Write-Host "Nothing new to commit — output already current on this branch."
    } else {
        # --no-verify: intentional for emergency path only (see .NOTES)
        git commit -m "emergency: LKG-only ship $ts [skip ci]" --no-verify
        if ($LASTEXITCODE -ne 0) { throw "git commit failed." }
        Write-Host "Committed recovery output to branch $branch."
    }

    # ------------------------------------------------------------------
    # 6. Deploy via Vercel CLI.
    #    Capture the per-deploy URL from stdout (the URL is the only
    #    https:// line emitted on success).
    # ------------------------------------------------------------------
    Write-Host "[6/8] Deploying to Vercel (--prod) ..."
    $vercelOutput = vercel deploy --prod 2>&1
    $deployUrl = ($vercelOutput | Select-String -Pattern "https://[^\s]+" | ForEach-Object { $_.Matches[0].Value } | Select-Object -First 1)
    if (-not $deployUrl) {
        throw "Vercel deploy produced no deployment URL. Output:`n$vercelOutput"
    }
    Write-Host "Deployed to: $deployUrl"

    # ------------------------------------------------------------------
    # 7. Alias rotation — explicit per CLAUDE.md Vercel gotcha.
    #    Without this the short alias stays pinned to the old deployment.
    # ------------------------------------------------------------------
    Write-Host "[7/8] Setting Vercel alias $VercelAlias -> $deployUrl ..."
    vercel alias set $deployUrl $VercelAlias
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "vercel alias set exited non-zero — alias may not have rotated. Check Vercel dashboard."
    } else {
        Write-Host "Alias set: $VercelAlias -> $deployUrl"
    }

    # ------------------------------------------------------------------
    # 8. Open a GitHub issue so humans know to investigate Monday morning.
    # ------------------------------------------------------------------
    Write-Host "[8/8] Opening GitHub issue for human review ..."
    $issueBody = @"
## Emergency LKG ship completed

- **Timestamp:** $ts UTC
- **Deploy URL:** $deployUrl
- **Alias:** https://$VercelAlias
- **Mode:** LKG-only (no fresh LLM generation)
- **Log:** logs/emergency_publish_$ts.log

### What happened
The Chronicle pipeline failed overnight. This emergency script served
Last-Known-Good cards (with "Awaiting refresh" badges) so fans saw a
functioning site rather than broken pages.

### Action required before next scheduled run
1. Review logs/emergency_publish_$ts.log for the root cause.
2. Fix and re-validate the chronicle pipeline.
3. Trigger a normal publish-site run to replace stale LKG cards.
"@

    gh issue create `
        --title "Emergency LKG ship $ts — chronicle pipeline failure" `
        --label "automation-failure,chronicle,priority-high" `
        --body $issueBody
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "gh issue create failed — issue was not opened. Create manually."
    }

    Write-Host "====================================================="
    Write-Host "EMERGENCY PUBLISH COMPLETE."
    Write-Host "Live URL : $deployUrl"
    Write-Host "Alias    : https://$VercelAlias"
    Write-Host "Log      : $logFile"
    Write-Host "====================================================="
    exit 0

} catch {
    $errMsg = $_.ToString()
    Write-Error "EMERGENCY PUBLISH FAILED: $errMsg"

    # Best-effort: try to open a critical alert issue even when the script fails.
    try {
        $failBody = @"
## CRITICAL: Emergency LKG ship FAILED

The emergency publish script itself crashed at $ts UTC.

**Error:** $errMsg

**Log:** logs/emergency_publish_$ts.log

Manual intervention required immediately.
"@
        gh issue create `
            --title "CRITICAL: Emergency LKG ship FAILED $ts" `
            --label "automation-failure,chronicle,priority-critical" `
            --body $failBody
    } catch {
        Write-Warning "Also failed to open GitHub issue: $_"
    }

    exit 1

} finally {
    Stop-Transcript
}
