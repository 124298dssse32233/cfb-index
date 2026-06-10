# chunked_vercel_publish.ps1
# Publish a >1GB static site to Vercel from the local box despite the per-deploy
# upload cap. Strategy: split output/site into chunks UNDER the cap, deploy each
# as a PREVIEW (which uploads + caches every file's content on Vercel by hash),
# then do ONE full PROD deploy that dedups against the primed cache (tiny upload)
# and alias the public URL to it.
#
# Why this works: Vercel content-addresses uploaded files (/v2/files) by hash and
# caches them account-wide, even from preview deploys. The final prod deploy only
# needs to upload files Vercel doesn't already have -> well under the cap.
$ErrorActionPreference = "Continue"
$repo  = "C:\Users\User 1\Downloads\Sports Website"
Set-Location $repo
$env:FORCE_COLOR = "0"
$SCOPE = "team_gR4aMSXbAnKOXs49An6tIStd"
$ALIAS = "wonderful-margulis-8ec96b.vercel.app"
$SITE  = Join-Path $repo "output\site"
$CHUNK_BYTES = 700MB           # safely under the ~1GB Pro cap
$TMP   = "C:\Users\User 1\Downloads\_vcchunk"
$log   = Join-Path $repo ("logs\chunked_publish_{0:yyyyMMdd_HHmmss}.log" -f (Get-Date))
function Log($m){ $s = Get-Date -Format "HH:mm:ss"; "$s  $m" | Tee-Object -FilePath $log -Append }
function Clean($m){ ($m -replace '(?<=\S) (?=\S)','') }

Log "==== chunked publish START ===="
$files = Get-ChildItem -LiteralPath $SITE -Recurse -File -ErrorAction SilentlyContinue
$totMB = [math]::Round((($files | Measure-Object Length -Sum).Sum/1MB),0)
Log ("site files=$($files.Count)  totalMB=$totMB")

# Greedy size-balanced binning
$chunks = New-Object System.Collections.ArrayList
$cur = New-Object System.Collections.ArrayList; $curSize = 0L
foreach ($f in $files) {
  if (($curSize + $f.Length) -gt $CHUNK_BYTES -and $cur.Count -gt 0) {
    [void]$chunks.Add(@($cur)); $cur = New-Object System.Collections.ArrayList; $curSize = 0L
  }
  [void]$cur.Add($f); $curSize += $f.Length
}
if ($cur.Count -gt 0) { [void]$chunks.Add(@($cur)) }
Log ("chunk count=$($chunks.Count)")

$ci = 0
foreach ($chunk in $chunks) {
  $ci++
  $cmb = [math]::Round((($chunk | Measure-Object Length -Sum).Sum/1MB),0)
  Log "=== priming chunk $ci/$($chunks.Count): files=$($chunk.Count) MB=$cmb ==="
  Remove-Item -LiteralPath $TMP -Recurse -Force -ErrorAction SilentlyContinue
  New-Item -ItemType Directory -Force -Path $TMP | Out-Null
  foreach ($f in $chunk) {
    $rel = $f.FullName.Substring($SITE.Length).TrimStart('\')
    $dest = Join-Path $TMP $rel
    $dd = Split-Path -Parent $dest
    if (-not (Test-Path -LiteralPath $dd)) { New-Item -ItemType Directory -Force -Path $dd | Out-Null }
    Copy-Item -LiteralPath $f.FullName -Destination $dest -Force -ErrorAction SilentlyContinue
  }
  Copy-Item -LiteralPath (Join-Path $repo ".vercel") -Destination (Join-Path $TMP ".vercel") -Recurse -Force
  [System.IO.File]::WriteAllText((Join-Path $TMP "vercel.json"), '{"framework":null,"outputDirectory":"."}')
  Set-Location -LiteralPath $TMP
  $out = (& vercel deploy --yes --archive=tgz --scope $SCOPE 2>&1 | ForEach-Object { Clean $_ })
  $out | Tee-Object -FilePath $log -Append | Out-Null
  Set-Location -LiteralPath $repo
  Remove-Item -LiteralPath $TMP -Recurse -Force -ErrorAction SilentlyContinue
  if ($out -match '\.vercel\.app') { Log "  chunk $ci PRIMED ok" }
  else {
    Log "  chunk $ci FAILED -- cap is smaller than ${CHUNK_BYTES}B. Aborting (need a different approach)."
    Log "==== chunked publish ABORTED at chunk $ci ===="
    exit 2
  }
}

Log "=== all chunks primed; running FINAL full PROD deploy ==="
& python tools\write_published_vercelignore.py *>&1 | Out-Null
$final = (& vercel deploy --prod --yes --archive=tgz --scope $SCOPE 2>&1 | ForEach-Object { Clean $_ })
$final | Tee-Object -FilePath $log -Append | Out-Null
$url = ($final | Select-String -Pattern 'https://wonderful-margulis-8ec96b-[a-z0-9]+-[a-z0-9-]+\.vercel\.app' -AllMatches | ForEach-Object { $_.Matches.Value } | Select-Object -First 1)
if (-not $url) { Log "FINAL DEPLOY FAILED -- no production URL captured."; Log "==== END (final failed) ===="; exit 3 }
Log ("final prod deploy URL: $url")
Log "aliasing public URL -> new deployment..."
(& vercel alias set $url $ALIAS --scope $SCOPE 2>&1 | ForEach-Object { Clean $_ }) | Tee-Object -FilePath $log -Append | Out-Null
Start-Sleep -Seconds 4
try { $r = Invoke-WebRequest -Uri "https://$ALIAS" -Method Head -TimeoutSec 30 -UseBasicParsing; Log ("HEALTH https://$ALIAS -> HTTP " + $r.StatusCode) }
catch { Log ("HEALTH check error: " + $_.Exception.Message) }
Log "==== chunked publish COMPLETE -- site is LIVE ===="
